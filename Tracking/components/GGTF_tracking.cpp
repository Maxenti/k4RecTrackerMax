//======================================================================
// GGTF_tracking.cpp  (tracks + optional 3D hits output)  [OOM-safe-ish]
//  * Produces extension::TrackCollection and optional GGTF_3DHits
//  * Projects wire hits onto an XY drift circle per group (seeded from 3 pts)
//  * Light outlier gate in XY to avoid poisoning first fitter updates
//  * Chunks ONNX inference; caps hits and optional 3D creation
//  * Propagates scalars (cellID/time/quality/eDep/err) into 3D hits
//  * Sets 3D covariances: wires use digi errors, planar use defaults
//======================================================================

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <memory>
#include <numeric>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>
#include <limits>

#include <ATen/ATen.h>
#include <ATen/Parallel.h>
#include <torch/torch.h>
#include "onnxruntime_cxx_api.h"

#include "TVector3.h"

// Gaudi + k4FWCore
#include "Gaudi/Algorithm.h"
#include "Gaudi/Property.h"
#include "GaudiKernel/ISvcLocator.h"
#include "GaudiKernel/SmartIF.h"
#include "k4FWCore/Transformer.h"
#include "k4Interface/IGeoSvc.h"

// EDM4hep & extensions
#include "edm4hep/TrackerHitPlaneCollection.h"
#include "edm4hep/TrackerHit3DCollection.h"
#include "edm4hep/MutableTrackerHit3D.h"
#include "extension/SenseWireHitCollection.h"
#include "extension/TrackCollection.h"

// DD4hep (optional)
#include "DD4hep/Detector.h"
#include "DDSegmentation/BitFieldCoder.h"

// Local
#include "utils.hpp"

namespace {

inline edm4hep::CovMatrix3f diag_cov_3d(float sx_mm, float sy_mm, float sz_mm) {
  // Packed order in EDM4hep: [ xx, xy, xz, yy, yz, zz ]
  edm4hep::CovMatrix3f C;
  C[0] = sx_mm * sx_mm;  // var(x)
  C[1] = 0.f;            // cov(x,y)
  C[2] = 0.f;            // cov(x,z)
  C[3] = sy_mm * sy_mm;  // var(y)
  C[4] = 0.f;            // cov(y,z)
  C[5] = sz_mm * sz_mm;  // var(z)
  return C;
}

inline std::pair<long,long> readRSSkB() {
  std::ifstream f("/proc/self/status");
  std::string key; long rss=0, hwm=0, val=0; std::string unit;
  while (f >> key) {
    if (key == "VmRSS:") { f >> val >> unit; rss = val; }
    else if (key == "VmHWM:") { f >> val >> unit; hwm = val; }
    f.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
  }
  return {rss,hwm};
}

struct StepTimer {
  std::chrono::steady_clock::time_point t0;
  StepTimer() : t0(std::chrono::steady_clock::now()) {}
  double ms() const {
    auto dt = std::chrono::steady_clock::now() - t0;
    return std::chrono::duration_cast<std::chrono::milliseconds>(dt).count();
  }
};

// 3-point circle in XY; returns false if nearly colinear
inline bool circle_from_3pts_xy(const TVector3& A, const TVector3& B, const TVector3& C,
                                TVector3& center_xy, double& R) {
  const double x1=A.X(), y1=A.Y(), x2=B.X(), y2=B.Y(), x3=C.X(), y3=C.Y();
  const double a = x1*(y2 - y3) - y1*(x2 - x3) + x2*y3 - x3*y2;
  const double d = 2.0 * a;
  if (std::abs(d) < 1e-9) return false;
  const double x1s=x1*x1, y1s=y1*y1, x2s=x2*x2, y2s=y2*y2, x3s=x3*x3, y3s=y3*y3;
  const double cx = ((x1s+y1s)*(y2-y3) + (x2s+y2s)*(y3-y1) + (x3s+y3s)*(y1-y2)) / d;
  const double cy = ((x1s+y1s)*(x3-x2) + (x2s+y2s)*(x1-x3) + (x3s+y3s)*(x2-x1)) / d;
  center_xy = TVector3(cx, cy, 0.0);
  R = std::hypot(x1-cx, y1-cy);
  return std::isfinite(R) && R > 1e-6;
}

} // namespace

struct GGTF_tracking final
  : k4FWCore::MultiTransformer<
        std::tuple<extension::TrackCollection, edm4hep::TrackerHit3DCollection>(
            const std::vector<const edm4hep::TrackerHitPlaneCollection*>&,
            const std::vector<const extension::SenseWireHitCollection*>&)> {

  GGTF_tracking(const std::string& name, ISvcLocator* svcLoc)
      : MultiTransformer(name, svcLoc,
                         // inputs
                         {
                           KeyValues("inputPlanarHits", {"inputPlanarHits"}),
                           KeyValues("inputWireHits",   {"inputWireHits"}),
                         },
                         // outputs
                         {
                           KeyValues("outputTracks", {"outputTracks"}),
                           KeyValues("output3DHits", {"GGTF_3DHits"}),
                         }) {
    m_geoSvc = serviceLocator()->service(m_geoSvcName.value());
  }

  // ---- properties ----
  Gaudi::Property<std::string> modelPath{this, "modelPath", "", "Path to ONNX model"};
  Gaudi::Property<double>      tbeta{this, "tbeta", 0.6, "clustering beta threshold"};
  Gaudi::Property<double>      td{this, "td", 0.3, "clustering distance threshold"};

  Gaudi::Property<bool>        produce3DHits{this, "produce3DHits", true,
                                            "If false, do not create GGTF_3DHits (returns empty collection)"};

  Gaudi::Property<std::string> m_geoSvcName{this, "GeoSvcName", "GeoSvc", "GeoSvc instance name"};
  Gaudi::Property<std::string> m_DCH_name{this, "DCH_name", "DCH_v2", "Drift chamber name"};

  // Safety: cap hits per event (0 = unlimited)
  Gaudi::Property<int>  maxHitsPerEvent{this, "maxHitsPerEvent", 0,
                                       "If >0, hard-limit number of input hits per event (prevents OOM)"};

  // ONNX chunk size (process in slices to avoid large allocations)
  Gaudi::Property<int>  onnxChunk{this, "onnxChunk", 4096,
                                  "Chunk size for ONNX inference (nHits per slice)"};

  // Wire 3D placement / outlier gate
  Gaudi::Property<double> wireGateMM{this, "wireGateMM", 3.0,
                                     "XY residual gate for wire projection (mm)"};

  // Optional: cap number of 3D hits we actually produce (relations still attached)
  Gaudi::Property<int>  max3DHitsPerEvent{this, "max3DHitsPerEvent", 100000,
                                          "Hard cap on number of 3D hits created per event"};
  Gaudi::Property<int>  max3DPerTrack{this, "max3DPerTrack", 10000,
                                      "Hard cap on number of 3D hits created per track"};

  // ---- NEW: scalar propagation & covariance defaults ----
  Gaudi::Property<bool>   propagateScalars{this, "propagateScalars", true,
                                           "Copy cellID/time/quality/EDep/EDepError into 3D hits"};
  Gaudi::Property<double> defaultSigmaXYMM{this, "defaultSigmaXYMM", 0.10,
                                           "Fallback σX/Y [mm] for planar (and wires without error)"};
  Gaudi::Property<double> defaultSigmaZMM {this, "defaultSigmaZMM",  1.00,
                                           "Fallback σZ [mm] for planar (and wires without error)"};

  StatusCode initialize() override {
    // Torch threading (be conservative)
    at::set_num_threads(1);
    at::set_num_interop_threads(1);

    // ONNX init (lean settings)
    fInfo = std::make_unique<Ort::MemoryInfo>(
        Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault));
    fEnv = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "ONNX_Runtime");
    fSessionOptions.SetIntraOpNumThreads(1);
    fSessionOptions.SetInterOpNumThreads(1);
    fSessionOptions.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_DISABLE_ALL);
    fSessionOptions.DisableMemPattern();
    fSessionOptions.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);

    fSession = std::make_unique<Ort::Session>(*fEnv, modelPath.value().c_str(), fSessionOptions);

    {
      Ort::AllocatorWithDefaultOptions alloc;
      const std::size_t i = 0;
      fInamesStr.emplace_back(fSession->GetInputNameAllocated(i,  alloc).get());
      fOnamesStr.emplace_back(fSession->GetOutputNameAllocated(i, alloc).get());
      fInames   = { fInamesStr.back().c_str() };
      fOnames   = { fOnamesStr.back().c_str() };
    }

    // Optional: geometry decoder (safe if absent)
    if (m_geoSvc && m_geoSvc->getDetector()) {
      try {
        auto* det = m_geoSvc->getDetector();
        auto sd   = det->sensitiveDetector(m_DCH_name.value());
        if (sd.isValid()) {
          auto ro = sd.readout();
          if (ro.isValid()) {
            dc_decoder = ro.idSpec().decoder();
          }
        }
      } catch (...) { /* continue without decoder */ }
    }

    auto [rss,hwm] = readRSSkB();
    info() << "GGTF_tracking init | modelPath=" << modelPath.value()
           << " | DCH=" << m_DCH_name.value()
           << " | decoder=" << (dc_decoder ? "OK" : "null")
           << " | produce3DHits=" << (produce3DHits.value() ? "true" : "false")
           << " | onnxChunk=" << onnxChunk.value()
           << " | RSS=" << rss/1024.0 << "MB, Peak=" << hwm/1024.0 << "MB"
           << endmsg;
    return StatusCode::SUCCESS;
  }

  std::tuple<extension::TrackCollection, edm4hep::TrackerHit3DCollection>
  operator()(const std::vector<const edm4hep::TrackerHitPlaneCollection*>& inputPlanar,
             const std::vector<const extension::SenseWireHitCollection*>&   inputWire) const override {
    torch::NoGradGuard nograd;
    ++m_evt;

    extension::TrackCollection      outTracks;
    edm4hep::TrackerHit3DCollection out3D;

    auto logMem = [&](const char* tag) {
      auto [rss,hwm] = readRSSkB();
      info() << "[evt " << m_evt << "] " << tag
             << " | RSS=" << rss/1024.0 << "MB, Peak=" << hwm/1024.0 << "MB" << endmsg;
    };

    StepTimer t_all;

    // ------- flatten inputs + remember (type, coll, idx) -------
    int64_t nPlanar=0, nWire=0;
    for (auto c : inputPlanar) nPlanar += c ? c->size() : 0;
    for (auto c : inputWire)   nWire   += c ? c->size() : 0;
    int64_t nHitsEst = nPlanar + nWire;

    if (maxHitsPerEvent > 0 && nHitsEst > maxHitsPerEvent) {
      warning() << "[evt " << m_evt << "] capping hits " << nHitsEst
                << " -> " << int(maxHitsPerEvent) << endmsg;
      nHitsEst = maxHitsPerEvent;
    }

    std::vector<float>    gInputs;   gInputs.reserve(std::max<int64_t>(nHitsEst*7, 128));
    std::vector<int64_t>  tagType;   tagType.reserve(std::max<int64_t>(nHitsEst, 128));   // 0=planar, 1=wire
    std::vector<int64_t>  tagIndexA; tagIndexA.reserve(tagType.capacity()); // collection id
    std::vector<int64_t>  tagIndexB; tagIndexB.reserve(tagType.capacity()); // hit index
    std::vector<TVector3> posCache;  posCache.reserve(tagType.capacity());  // positions (mm)

    auto push_planar = [&](int icoll, int ihit, const edm4hep::TrackerHitPlane& h) {
      const auto p = h.getPosition();
      gInputs.insert(gInputs.end(), {float(p.x), float(p.y), float(p.z), 1.f, 0.f, 0.f, 0.f});
      tagType.push_back(0); tagIndexA.push_back(icoll); tagIndexB.push_back(ihit);
      posCache.emplace_back(p.x, p.y, p.z);
    };

    auto push_wire = [&](int icoll, int ihit, const extension::SenseWireHit& h) {
      const auto wp = h.getPosition();
      const double d   = h.getDistanceToWire();
      const double phi = h.getWireAzimuthalAngle();
      const double st  = h.getWireStereoAngle();

      TVector3 wpos(wp.x, wp.y, wp.z);
      TVector3 dir(0,0,1); dir.RotateX(st); dir.RotateZ(phi); dir = dir.Unit();

      TVector3 xprime(1.0, 0.0, -dir.X()/std::max(1e-9, dir.Z())); xprime = xprime.Unit();
      TVector3 yprime = dir.Cross(xprime).Unit();

      const TVector3 l(-d,0,0), r(+d,0,0);
      const auto L = xprime*l.X() + yprime*l.Y() + dir*l.Z() + wpos;
      const auto R = xprime*r.X() + yprime*r.Y() + dir*r.Z() + wpos;
      const auto M = 0.5*(L+R);

      gInputs.insert(gInputs.end(),
                     {float(M.X()), float(M.Y()), float(M.Z()),
                      0.f, float(R.X()-L.X()), float(R.Y()-L.Y()), float(R.Z()-L.Z())});
      tagType.push_back(1); tagIndexA.push_back(icoll); tagIndexB.push_back(ihit);
      posCache.emplace_back(wp.x, wp.y, wp.z); // store wire center (mm)
    };

    {
      StepTimer t_flat;
      int ic = 0;
      for (auto coll : inputPlanar) {
        if (!coll) { ++ic; continue; }
        for (int i=0, n=coll->size(); i<n; ++i) {
          if (maxHitsPerEvent>0 && (int)tagType.size()>=maxHitsPerEvent) break;
          push_planar(ic, i, (*coll)[i]);
        }
        ++ic;
        if (maxHitsPerEvent>0 && (int)tagType.size()>=maxHitsPerEvent) break;
      }
      ic = 0;
      for (auto coll : inputWire) {
        if (!coll) { ++ic; continue; }
        for (int i=0, n=coll->size(); i<n; ++i) {
          if (maxHitsPerEvent>0 && (int)tagType.size()>=maxHitsPerEvent) break;
          push_wire(ic, i, (*coll)[i]);
        }
        ++ic;
        if (maxHitsPerEvent>0 && (int)tagType.size()>=maxHitsPerEvent) break;
      }
      info() << "[evt " << m_evt << "] flatten: "
             << "planar=" << nPlanar << " wire=" << nWire
             << " -> used=" << tagType.size()
             << " in " << t_flat.ms() << " ms" << endmsg;
    }

    const int64_t nHits = static_cast<int64_t>(tagType.size());
    if (nHits == 0) {
      logMem("no-hits (early return)");
      return {std::move(outTracks), std::move(out3D)};
    }
    logMem("after-flatten");

    // ------- ONNX run (chunked) -------
    std::vector<float> embed; embed.resize(4 * nHits);
    {
      StepTimer t_onnx;
      const int64_t CH = std::max<int64_t>(1, onnxChunk.value());
      int64_t done = 0;
      while (done < nHits) {
        const int64_t take = std::min<int64_t>(CH, nHits - done);
        const std::vector<int64_t> shape{take, 7};
        Ort::Value in = Ort::Value::CreateTensor<float>(
            *fInfo, const_cast<float*>(gInputs.data() + done*7), take*7, shape.data(), shape.size());
        auto outs = fSession->Run(Ort::RunOptions{nullptr},
                                  fInames.data(), &in, 1,
                                  fOnames.data(), fOnames.size());
        float* outptr = outs.front().GetTensorMutableData<float>();
        std::copy(outptr, outptr + 4*take, embed.data() + 4*done);
        done += take;
      }
      // free input buffer ASAP
      gInputs.clear(); gInputs.shrink_to_fit();
      info() << "[evt " << m_evt << "] onnx: nHits=" << nHits
             << " in " << t_onnx.ms() << " ms" << endmsg;
    }
    logMem("after-onnx");

    // ------- clustering -------
    torch::Tensor clustering;
    {
      StepTimer t_cluster;
      clustering = get_clustering(embed, nHits, tbeta.value(), td.value()); // int64 labels, len=nHits
      info() << "[evt " << m_evt << "] clustering: "
             << " in " << t_cluster.ms() << " ms" << endmsg;
    }
    embed.clear(); embed.shrink_to_fit();
    logMem("after-clustering");

    // Unique labels and inverse index
    torch::Tensor uniques, invIdx;
    {
      StepTimer t_uni;
      std::tie(uniques, invIdx) = at::_unique(clustering, /*sorted=*/true, /*return_inverse=*/true);
      info() << "[evt " << m_evt << "] unique: nLabels=" << uniques.size(0)
             << " in " << t_uni.ms() << " ms" << endmsg;
    }

    // Build groups via inverse index
    std::vector<std::vector<int64_t>> groups;
    int64_t zeroLabelPos = -1;
    torch::Tensor uniques_cpu;
    {
      StepTimer t_bucket;
      uniques_cpu = uniques.to(torch::kCPU);
      auto inv_cpu = invIdx.to(torch::kCPU).contiguous();
      const int64_t nLabels = uniques_cpu.size(0);
      groups.resize(nLabels);

      for (int64_t i=0; i<nLabels; ++i) {
        if (uniques_cpu[i].item<int64_t>() == 0) { zeroLabelPos = i; break; }
      }

      auto invAcc = inv_cpu.accessor<int64_t,1>();
      for (int64_t idx=0; idx<nHits; ++idx) {
        const int64_t pos = invAcc[idx];
        if (pos>=0 && pos<nLabels) groups[pos].push_back(idx);
      }
      info() << "[evt " << m_evt << "] bucket: labels=" << nLabels
             << " in " << t_bucket.ms() << " ms" << endmsg;
    }
    clustering = torch::Tensor(); invIdx = torch::Tensor();
    logMem("after-bucket");

    // ------- helpers to emit 3D hits (scalar propagation & covariances) -------
    int total3D = 0;

    auto add_planar_3d = [&](const edm4hep::TrackerHitPlane& hp,
                             int labelValue,
                             edm4hep::TrackerHit3DCollection& out3Dcoll) -> bool {
      if (!produce3DHits.value()) return false;
      auto h = out3Dcoll.create();

      // Position
      const auto p = hp.getPosition();
      h.setPosition(edm4hep::Vector3d{p.x, p.y, p.z});

      // Scalars
      if (propagateScalars.value()) {
        try { h.setCellID(hp.getCellID()); } catch (...) {}
        try { h.setTime(hp.getTime());     } catch (...) { h.setTime(0.f); }
        try { h.setQuality(hp.getQuality()); } catch (...) {}
        try { h.setEDep(hp.getEDep()); } catch (...) { h.setEDep(0.f); }
        try { h.setEDepError(hp.getEDepError()); } catch (...) { h.setEDepError(0.f); }
      }
      // Group label in 'type'
      try { h.setType(labelValue); } catch (...) {}

      // Covariance (defaults)
      const float sx = std::max<float>(1e-6f, float(defaultSigmaXYMM.value()));
      const float sy = sx;
      const float sz = std::max<float>(1e-6f, float(defaultSigmaZMM.value()));
      h.setCovMatrix(diag_cov_3d(sx,sy,sz));
      return true;
    };

    auto add_wire_3d = [&](const extension::SenseWireHit& hw,
                           const TVector3& M,
                           int labelValue,
                           edm4hep::TrackerHit3DCollection& out3Dcol) -> bool {
      if (!produce3DHits.value()) return false;
      auto h = out3Dcol.create();

      // Position (projected)
      h.setPosition(edm4hep::Vector3d{float(M.X()), float(M.Y()), float(M.Z())});

      // Scalars
      if (propagateScalars.value()) {
        h.setCellID(hw.getCellID());
        h.setTime(hw.getTime());
        h.setQuality(hw.getQuality());
        h.setEDep(hw.getEDep());
        h.setEDepError(hw.getEDepError());
      }
      // Group label in 'type'
      try { h.setType(labelValue); } catch (...) {}

      // Covariance: prefer digi’s per-hit errors, else defaults
      double sXY = double(hw.getDistanceToWireError());     // mm
      double sZ  = double(hw.getPositionAlongWireError());  // mm
      if (!(sXY > 0.0)) sXY = defaultSigmaXYMM.value();
      if (!(sZ  > 0.0)) sZ  = defaultSigmaZMM.value();
      const float sx = std::max<float>(1e-6f, float(sXY));
      const float sz = std::max<float>(1e-6f, float(sZ));
      h.setCovMatrix(diag_cov_3d(sx, sx, sz));
      return true;
    };

    auto add_hit_to_track = [&](extension::MutableTrack& trk,
                                int64_t flatIdx,
                                const TVector3& Cxy, double R,
                                int labelValue,
                                int& made3D_for_track) {
      const int64_t t  = tagType[flatIdx];
      const int64_t ia = tagIndexA[flatIdx];
      const int64_t ib = tagIndexB[flatIdx];

      if (t == 0) {
        const auto& hp = (*inputPlanar[ia])[int(ib)];
        if (total3D < max3DHitsPerEvent && made3D_for_track < max3DPerTrack) {
          if (add_planar_3d(hp, labelValue, out3D)) { ++total3D; ++made3D_for_track; }
        }
        trk.addToTrackerHits(hp);
        return;
      }

      // Wire hit: project onto drift circle in XY
      const auto& hw = (*inputWire[ia])[int(ib)];
      const auto wp  = hw.getPosition();
      const double d = std::max(0.0, (double)hw.getDistanceToWire()); // mm

      TVector3 wxy(wp.x, wp.y, 0.0);
      TVector3 u = (wxy - Cxy);
      const double r0 = u.Perp();
      if (u.Perp2() > 0) u *= (1.0 / u.Perp()); else u = TVector3(1,0,0);

      const double s = (R > r0 ? +1.0 : -1.0);
      TVector3 M(wxy.X() + s * d * u.X(),
                 wxy.Y() + s * d * u.Y(),
                 wp.z); // keep Z from wire center

      // outlier gate (| |wxy-C| - R | ≈ d)
      const double e = std::fabs(std::fabs(r0 - R) - d);
      const bool passGate = (e <= wireGateMM.value());

      if (passGate && total3D < max3DHitsPerEvent && made3D_for_track < max3DPerTrack) {
        if (add_wire_3d(hw, M, labelValue, out3D)) { ++total3D; ++made3D_for_track; }
      }
      // Always attach the original relation
      trk.addToTrackerHits(hw);
    };

    // ------- assemble tracks from groups -------
    {
      StepTimer t_build;
      const int64_t nLabels = static_cast<int64_t>(groups.size());
      int nTracks = 0;

      for (int64_t li = 0; li < nLabels; ++li) {
        if (zeroLabelPos == li) continue;           // skip noise label "0"
        if (groups[li].empty()) continue;

        auto trk = outTracks.create();
        const int labelValue = uniques_cpu[li].item<int>();
        trk.setType(labelValue);

        // Seed circle using wires when possible
        TVector3 Cxy(0,0,0); double R = 1e9;
        const auto& vec = groups[li];
        std::vector<int64_t> wireIdx; wireIdx.reserve(vec.size());
        for (auto k : vec) if (tagType[k] == 1) wireIdx.push_back(k);

        auto pick = [&](const std::vector<int64_t>& v)->std::tuple<TVector3,TVector3,TVector3,bool>{
          if (v.size() < 3) return {{}, {}, {}, false};
          const TVector3 A = posCache[v.front()];
          const TVector3 B = posCache[v[v.size()/2]];
          const TVector3 C = posCache[v.back()];
          return {A,B,C,true};
        };

        bool ok=false;
        if (wireIdx.size() >= 3) {
          auto [A,B,C,have] = pick(wireIdx);
          if (have) ok = circle_from_3pts_xy(A,B,C,Cxy,R);
        }
        if (!ok && vec.size() >= 3) {
          const TVector3 A = posCache[vec.front()];
          const TVector3 B = posCache[vec[vec.size()/2]];
          const TVector3 C = posCache[vec.back()];
          ok = circle_from_3pts_xy(A,B,C,Cxy,R);
        }
        if (!ok) { Cxy = TVector3(0,0,0); R = 1e9; } // fallback

        int made3D_for_track = 0;
        for (int64_t k : vec) add_hit_to_track(trk, k, Cxy, R, labelValue, made3D_for_track);
        ++nTracks;
      }

      info() << "[evt " << m_evt << "] build: tracks=" << nTracks
             << " created3D=" << total3D
             << " in " << t_build.ms() << " ms" << endmsg;
    }
    logMem("after-build");

    info() << "[evt " << m_evt << "] TOTAL " << t_all.ms() << " ms" << endmsg;
    return std::make_tuple(std::move(outTracks), std::move(out3D));
  }

  StatusCode finalize() override {
    auto [rss,hwm] = readRSSkB();
    info() << "GGTF_tracking finalize | events=" << m_evt
           << " | RSS=" << rss/1024.0 << "MB, Peak=" << hwm/1024.0 << "MB"
           << endmsg;
    return StatusCode::SUCCESS;
  }

private:
  // ONNX
  std::unique_ptr<Ort::Env>          fEnv;
  std::unique_ptr<Ort::Session>      fSession;
  Ort::SessionOptions                fSessionOptions;
  std::unique_ptr<Ort::MemoryInfo>   fInfo;
  std::vector<std::string>           fInamesStr, fOnamesStr;
  std::vector<const char*>           fInames, fOnames;

  // Geometry (optional)
  SmartIF<IGeoSvc> m_geoSvc;
  dd4hep::DDSegmentation::BitFieldCoder* dc_decoder{nullptr};

  // stats
  mutable int m_evt{0};
};

DECLARE_COMPONENT(GGTF_tracking)