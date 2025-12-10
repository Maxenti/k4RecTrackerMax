//======================================================================
// GGTF_tracking.cpp  (tracks + optional 3D hits output)  [with label-0 guards]
//======================================================================

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <limits>
#include <memory>
#include <numeric>
#include <string>
#include <tuple>
#include <vector>
#include <sstream>  // <--- added

#include <ATen/ATen.h>
#include <torch/torch.h>
#include "onnxruntime_cxx_api.h"

#include "TVector3.h"

// Gaudi + k4FWCore
#include "Gaudi/Algorithm.h"
#include "Gaudi/Property.h"
#include "GaudiKernel/ISvcLocator.h"
#include "GaudiKernel/SmartIF.h"
#include "k4FWCore/Transformer.h"
#include "k4FWCore/MetaDataHandle.h"  // <--- added
#include "k4Interface/IGeoSvc.h"
#include "k4Interface/IUniqueIDGenSvc.h"

// EDM4hep & extensions
#include "edm4hep/TrackerHitPlaneCollection.h"
#include "edm4hep/TrackerHit3DCollection.h"
#include "extension/SenseWireHitCollection.h"
#include "extension/TrackCollection.h"

// DD4hep (optional)
#include "DD4hep/Detector.h"
#include "DDSegmentation/BitFieldCoder.h"

// Local
#include "utils.hpp"

// ---------- helpers ----------
namespace {

inline edm4hep::CovMatrix3f diag_cov_3d(float sx_mm, float sy_mm, float sz_mm) {
  edm4hep::CovMatrix3f C;
  C[0] = sx_mm * sx_mm;  // xx
  C[1] = 0.f;            // xy
  C[2] = 0.f;            // xz
  C[3] = sy_mm * sy_mm;  // yy
  C[4] = 0.f;            // yz
  C[5] = sz_mm * sz_mm;  // zz
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
  std::chrono::steady_clock::time_point t0{std::chrono::steady_clock::now()};
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

/**
 * GGTF_tracking
 *
 * Inputs:
 *   - vector<TrackerHitPlaneCollection*>  (planar/vtx/silicon)   [may be empty]
 *   - vector<SenseWireHitCollection*>     (drift chamber wires)
 *
 * Outputs:
 *   - extension::TrackCollection          (as upstream)
 *   - edm4hep::TrackerHit3DCollection     ("GGTF_3DHits") optional via Produce3DHits
 */
struct GGTF_tracking final
  : k4FWCore::MultiTransformer<
      std::tuple<extension::TrackCollection, edm4hep::TrackerHit3DCollection>(
        const std::vector<const edm4hep::TrackerHitPlaneCollection*>&,
        const std::vector<const extension::SenseWireHitCollection*>&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  GGTF_tracking(const std::string& name, ISvcLocator* svcLoc)
      : MultiTransformer(
          name, svcLoc,
          // Inputs (match upstream names)
          {
            KeyValues("InputPlanarHitCollections", std::vector<std::string>{"InputPlanarHitCollections"}),
            KeyValues("InputWireHitCollections",   std::vector<std::string>{"InputWireHitCollections"})
          },
          // Outputs (match upstream names)
          {
            KeyValues("OutputTracksGGTF", std::vector<std::string>{"OutputTracksGGTF"}),
            KeyValues("Output3DHits",     std::vector<std::string>{"GGTF_3DHits"})
          }),
        m_meta("GGTF_trackingConfig", Gaudi::DataHandle::Writer)  // <--- added
  {
    m_geoSvc = serviceLocator()->service(m_geoSvcName);
  }

  // ---------- properties ----------
  // ONNX / clustering
  Gaudi::Property<std::string> m_modelPath{this, "ModelPath", "", "Path to ONNX model"};
  Gaudi::Property<double>      m_tbeta    {this, "Tbeta", 0.6, "clustering beta threshold"};
  Gaudi::Property<double>      m_td       {this, "Td",    0.3, "clustering distance threshold"};

  // Safety + performance
  Gaudi::Property<int>         m_maxHitsPerEvent{this, "MaxHitsPerEvent", 0, "Cap input hits per event (0=off)"};
  Gaudi::Property<int>         m_onnxChunk{this, "OnnxChunk", 4096, "Chunk size for ONNX inference"};

  // 3D hits controls
  Gaudi::Property<bool>        m_produce3DHits{this, "Produce3DHits", true, "Emit GGTF_3DHits"};
  Gaudi::Property<int>         m_max3DHitsPerEvent{this, "Max3DHitsPerEvent", 200000, "Cap 3D hits per event"};
  Gaudi::Property<int>         m_max3DPerTrack{this, "Max3DPerTrack", 20000, "Cap 3D hits per track"};

  // Wire projection tuning
  Gaudi::Property<double>      m_wireGateMM{this, "WireGateMM", 12.0, "XY residual gate / clamp for wires [mm]"};

  // Scalar propagation + default covariances for 3D hits
  Gaudi::Property<bool>        m_propagateScalars{this, "PropagateScalars", true,
                                                  "Copy cellID/time/quality/EDep/EDepError into 3D hits"};
  Gaudi::Property<double>      m_defaultSigmaXYMM{this, "DefaultSigmaXYMM", 0.10, "Fallback σX/Y [mm]"};
  Gaudi::Property<double>      m_defaultSigmaZMM {this, "DefaultSigmaZMM",  1.00, "Fallback σZ [mm]"};

  // Services / detector
  Gaudi::Property<std::string> m_geoSvcName{this, "GeoSvcName", "GeoSvc", "GeoSvc name"};
  Gaudi::Property<std::string> m_uidSvcName{this, "UidSvcName", "uidSvc", "UniqueIDGenSvc name"};
  Gaudi::Property<std::string> m_dchName   {this, "DchName", "DCH_v2", "Drift chamber detector name"};

  // Optional external job tag (e.g. input file, steering script name)
  Gaudi::Property<std::string> m_jobTag{
      this, "JobTag", "",
      "Optional free-form tag (e.g. steering script name, input file, run label) to store in metadata"};

  // --- label-0 handling (NEW) ---
  Gaudi::Property<int>    m_zeroMinSizeKeep{this, "ZeroMinSizeKeep", 8,
    "Min hits for a label=0 group to be considered (else dropped)"};
  Gaudi::Property<double> m_minWireFracKeep{this, "MinWireFracKeep", 0.60,
    "Min fraction of wire hits to keep a zero-label group"};
  Gaudi::Property<bool>   m_promoteZeroIfGood{this, "PromoteZeroIfGood", true,
    "If a zero-label group passes checks, treat it as a normal cluster"};
  Gaudi::Property<bool>   m_skipZeroIfSmall{this, "SkipZeroIfSmall", true,
    "If label=0 group smaller than ZeroMinSizeKeep, drop it"};
  Gaudi::Property<bool>   m_skipZeroAlways{this, "SkipZeroAlways", false,
    "If true, never build tracks from label=0 (debug mode)"};

  // ---------- state ----------
  std::unique_ptr<Ort::Env>          m_fEnv;
  std::unique_ptr<Ort::Session>      m_fSession;
  Ort::SessionOptions                m_fSessionOptions;
  std::unique_ptr<Ort::MemoryInfo>   m_fInfo;
  std::vector<std::string>           m_inNamesStr, m_outNamesStr;
  std::vector<const char*>           m_inNames, m_outNames;

  SmartIF<IGeoSvc>                   m_geoSvc;
  dd4hep::DDSegmentation::BitFieldCoder* m_dchDecoder{nullptr};

  mutable int m_evt{0};

  // Metadata handle for this stage
  k4FWCore::MetaDataHandle<std::string> m_meta;  // <--- added

  // ---------- init ----------
  StatusCode initialize() override {
    at::set_num_threads(1);
    at::set_num_interop_threads(1);

    // ONNX
    m_fInfo = std::make_unique<Ort::MemoryInfo>(
        Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault));
    m_fEnv = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "ONNX_Runtime");
    m_fSessionOptions.SetIntraOpNumThreads(1);
    m_fSessionOptions.SetInterOpNumThreads(1);
    m_fSessionOptions.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_DISABLE_ALL);
    m_fSessionOptions.DisableMemPattern();
    m_fSessionOptions.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);

    m_fSession = std::make_unique<Ort::Session>(*m_fEnv, m_modelPath.value().c_str(), m_fSessionOptions);
    {
      Ort::AllocatorWithDefaultOptions alloc;
      const std::size_t i = 0;
      m_inNamesStr.emplace_back(m_fSession->GetInputNameAllocated(i,  alloc).get());
      m_outNamesStr.emplace_back(m_fSession->GetOutputNameAllocated(i, alloc).get());
      m_inNames  = { m_inNamesStr.back().c_str() };
      m_outNames = { m_outNamesStr.back().c_str() };
    }

    // Optional decoder
    if (m_geoSvc && m_geoSvc->getDetector()) {
      try {
        auto sd = m_geoSvc->getDetector()->sensitiveDetector(m_dchName.value());
        if (sd.isValid()) {
          auto ro = sd.readout();
          if (ro.isValid()) m_dchDecoder = ro.idSpec().decoder();
        }
      } catch (...) {}
    }

    auto [rss,hwm] = readRSSkB();
    info() << "GGTF_tracking init | model=" << m_modelPath.value()
           << " | Tbeta=" << m_tbeta.value()
           << " | Td=" << m_td.value()
           << " | Produce3DHits=" << (m_produce3DHits.value()?"true":"false")
           << " | OnnxChunk=" << m_onnxChunk.value()
           << " | MaxHitsPerEvent=" << m_maxHitsPerEvent.value()
           << " | ZeroMinSizeKeep=" << m_zeroMinSizeKeep.value()
           << " | MinWireFracKeep=" << m_minWireFracKeep.value()
           << " | PromoteZeroIfGood=" << (m_promoteZeroIfGood.value()?"true":"false")
           << " | SkipZeroIfSmall=" << (m_skipZeroIfSmall.value()?"true":"false")
           << " | SkipZeroAlways=" << (m_skipZeroAlways.value()?"true":"false")
           << " | RSS=" << rss/1024.0 << "MB, Peak=" << hwm/1024.0 << "MB"
           << endmsg;

    // ---- write metadata for this component ----
    try {
      std::ostringstream cfg;
      cfg << "{"
          << "\"component\":\"GGTF_tracking\","
          << "\"modelPath\":\"" << m_modelPath.value() << "\","
          << "\"Tbeta\":" << m_tbeta.value() << ","
          << "\"Td\":" << m_td.value() << ","
          << "\"Produce3DHits\":" << (m_produce3DHits.value() ? "true" : "false") << ","
          << "\"OnnxChunk\":" << m_onnxChunk.value() << ","
          << "\"MaxHitsPerEvent\":" << m_maxHitsPerEvent.value() << ","
          << "\"Max3DHitsPerEvent\":" << m_max3DHitsPerEvent.value() << ","
          << "\"Max3DPerTrack\":" << m_max3DPerTrack.value() << ","
          << "\"WireGateMM\":" << m_wireGateMM.value() << ","
          << "\"DefaultSigmaXYMM\":" << m_defaultSigmaXYMM.value() << ","
          << "\"DefaultSigmaZMM\":" << m_defaultSigmaZMM.value() << ","
          << "\"DchName\":\"" << m_dchName.value() << "\","
          << "\"JobTag\":\"" << m_jobTag.value() << "\","
          << "\"ZeroMinSizeKeep\":" << m_zeroMinSizeKeep.value() << ","
          << "\"MinWireFracKeep\":" << m_minWireFracKeep.value() << ","
          << "\"PromoteZeroIfGood\":" << (m_promoteZeroIfGood.value() ? "true" : "false") << ","
          << "\"SkipZeroIfSmall\":" << (m_skipZeroIfSmall.value() ? "true" : "false") << ","
          << "\"SkipZeroAlways\":" << (m_skipZeroAlways.value() ? "true" : "false")
          << "}";

      m_meta.put(cfg.str());
      info() << "GGTF_tracking metadata written under key 'GGTF_trackingConfig'" << endmsg;
    } catch (const std::exception& e) {
      warning() << "Failed to write GGTF_tracking metadata: " << e.what() << endmsg;
    } catch (...) {
      warning() << "Failed to write GGTF_tracking metadata (unknown exception)" << endmsg;
    }

    return StatusCode::SUCCESS;
  }

  // ---------- main ----------
  std::tuple<extension::TrackCollection, edm4hep::TrackerHit3DCollection>
  operator()(const std::vector<const edm4hep::TrackerHitPlaneCollection*>& inputPlanarHitCollections,
             const std::vector<const extension::SenseWireHitCollection*>&   inputWireHitCollections) const override
  {
    torch::NoGradGuard _nograd;
    ++m_evt;
    StepTimer t_all;

    extension::TrackCollection      outputTracks;
    edm4hep::TrackerHit3DCollection output3D;

    auto logMem = [&](const char* tag) {
      auto [rss,hwm] = readRSSkB();
      info() << "[evt " << m_evt << "] " << tag
             << " | RSS=" << rss/1024.0 << "MB, Peak=" << hwm/1024.0 << "MB" << endmsg;
    };

    // -------- flatten inputs --------
    int64_t nPlanar=0, nWire=0;
    for (auto c : inputPlanarHitCollections) nPlanar += c ? c->size() : 0;
    for (auto c : inputWireHitCollections)   nWire   += c ? c->size() : 0;
    int64_t nEst = nPlanar + nWire;

    if (m_maxHitsPerEvent > 0 && nEst > m_maxHitsPerEvent) {
      warning() << "[evt " << m_evt << "] capping hits " << nEst
                << " -> " << int(m_maxHitsPerEvent) << endmsg;
      nEst = m_maxHitsPerEvent;
    }

    std::vector<float>    gInputs;   gInputs.reserve(std::max<int64_t>(nEst*7, 128));
    std::vector<int64_t>  tagType;   tagType.reserve(std::max<int64_t>(nEst, 128));   // 0=planar, 1=wire
    std::vector<int64_t>  tagA, tagB; // collection idx, hit idx
    std::vector<TVector3> posCache;  posCache.reserve(tagType.capacity());  // for seeding/projecting

    auto push_planar = [&](int ic, int ih, const edm4hep::TrackerHitPlane& h) {
      const auto p = h.getPosition();
      gInputs.insert(gInputs.end(), {float(p.x), float(p.y), float(p.z), 1.f, 0.f, 0.f, 0.f});
      tagType.push_back(0); tagA.push_back(ic); tagB.push_back(ih);
      posCache.emplace_back(p.x, p.y, p.z);
    };

    auto push_wire = [&](int ic, int ih, const extension::SenseWireHit& h) {
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
      tagType.push_back(1); tagA.push_back(ic); tagB.push_back(ih);
      posCache.emplace_back(wp.x, wp.y, wp.z); // store wire center (mm)
    };

    {
      StepTimer t_flat;
      int ic=0;
      for (auto c : inputPlanarHitCollections) {
        if (!c) { ++ic; continue; }
        for (int i=0, n=c->size(); i<n; ++i) {
          if (m_maxHitsPerEvent>0 && (int)tagType.size()>=m_maxHitsPerEvent) break;
          push_planar(ic, i, (*c)[i]);
        }
        ++ic;
        if (m_maxHitsPerEvent>0 && (int)tagType.size()>=m_maxHitsPerEvent) break;
      }
      ic=0;
      for (auto c : inputWireHitCollections) {
        if (!c) { ++ic; continue; }
        for (int i=0, n=c->size(); i<n; ++i) {
          if (m_maxHitsPerEvent>0 && (int)tagType.size()>=m_maxHitsPerEvent) break;
          push_wire(ic, i, (*c)[i]);
        }
        ++ic;
        if (m_maxHitsPerEvent>0 && (int)tagType.size()>=m_maxHitsPerEvent) break;
      }
      info() << "[evt " << m_evt << "] flatten: planar=" << nPlanar
             << " wire=" << nWire << " -> used=" << tagType.size()
             << " in " << t_flat.ms() << " ms" << endmsg;
    }

    const int64_t nHits = (int64_t)tagType.size();
    if (nHits == 0) {
      return std::make_tuple(std::move(outputTracks), std::move(output3D));
    }
    logMem("after-flatten");

    // -------- ONNX (chunked) --------
    std::vector<float> embed; embed.resize(4 * nHits);
    {
      StepTimer t_onnx;
      const int64_t CH = std::max<int>(1, m_onnxChunk.value());
      int64_t done = 0;
      while (done < nHits) {
        const int64_t take = std::min<int64_t>(CH, nHits - done);
        const std::vector<int64_t> shape{take, 7};
        Ort::Value in = Ort::Value::CreateTensor<float>(
            *m_fInfo, const_cast<float*>(gInputs.data() + done*7), take*7, shape.data(), shape.size());
        auto outs = m_fSession->Run(Ort::RunOptions{nullptr},
                                    m_inNames.data(), &in, 1,
                                    m_outNames.data(), m_outNames.size());
        float* outptr = outs.front().GetTensorMutableData<float>();
        std::copy(outptr, outptr + 4*take, embed.data() + 4*done);
        done += take;
      }
      std::vector<float>().swap(gInputs); // free
      info() << "[evt " << m_evt << "] onnx: nHits=" << nHits
             << " in " << t_onnx.ms() << " ms" << endmsg;
    }
    logMem("after-onnx");

    // -------- clustering --------
    torch::Tensor clustering;
    {
      StepTimer t_cluster;
      clustering = get_clustering(embed, nHits, m_tbeta.value(), m_td.value());
      info() << "[evt " << m_evt << "] clustering in " << t_cluster.ms() << " ms" << endmsg;
    }
    std::vector<float>().swap(embed);
    logMem("after-clustering");

    // Unique labels + inverse index
    torch::Tensor uniques, invIdx;
    {
      StepTimer t_uni;
      std::tie(uniques, invIdx) = at::_unique(clustering, /*sorted=*/true, /*return_inverse=*/true);
      info() << "[evt " << m_evt << "] unique: nLabels=" << uniques.size(0)
             << " in " << t_uni.ms() << " ms" << endmsg;
    }

    // Build groups via inverse index
    std::vector<std::vector<int64_t>> groups;

    torch::Tensor uniques_cpu;
    {
      StepTimer t_bucket;
      uniques_cpu = uniques.to(torch::kCPU);
      auto inv_cpu = invIdx.to(torch::kCPU).contiguous();
      const int64_t nLabels = uniques_cpu.size(0);
      groups.resize(nLabels);



      auto acc = inv_cpu.accessor<int64_t,1>();
      for (int64_t i=0; i<nHits; ++i) {
        const int64_t pos = acc[i];
        if (pos>=0 && pos<nLabels) groups[pos].push_back(i);
      }
      info() << "[evt " << m_evt << "] bucket in " << t_bucket.ms() << " ms" << endmsg;
    }
    clustering = torch::Tensor(); invIdx = torch::Tensor();
    logMem("after-bucket");

    // Helper lambdas to create 3D hits
    int total3D = 0;

    auto add_planar_3d = [&](const edm4hep::TrackerHitPlane& hp,
                             int labelValue,
                             edm4hep::TrackerHit3DCollection& out3Dcoll) -> bool {
      if (!m_produce3DHits.value()) return false;
      auto h = out3Dcoll.create();

      const auto p = hp.getPosition();
      h.setPosition(edm4hep::Vector3d{p.x, p.y, p.z});

      if (m_propagateScalars.value()) {
        try { h.setCellID(hp.getCellID()); } catch (...) {}
        try { h.setTime(hp.getTime()); } catch (...) { h.setTime(0.f); }
        try { h.setQuality(hp.getQuality()); } catch (...) {}
        try { h.setEDep(hp.getEDep()); } catch (...) { h.setEDep(0.f); }
        try { h.setEDepError(hp.getEDepError()); } catch (...) { h.setEDepError(0.f); }
      }
      try { h.setType(labelValue); } catch (...) {}

      const float sx = std::max<float>(1e-6f, float(m_defaultSigmaXYMM.value()));
      const float sz = std::max<float>(1e-6f, float(m_defaultSigmaZMM.value()));
      h.setCovMatrix(diag_cov_3d(sx, sx, sz));
      return true;
    };

    auto add_wire_3d = [&](const extension::SenseWireHit& hw,
                           const TVector3& M,
                           int labelValue,
                           edm4hep::TrackerHit3DCollection& out3Dcol) -> bool {
      if (!m_produce3DHits.value()) return false;
      auto h = out3Dcol.create();
      h.setPosition(edm4hep::Vector3d{double(M.X()), double(M.Y()), double(M.Z())});

      if (m_propagateScalars.value()) {
        h.setCellID(hw.getCellID());
        h.setTime(hw.getTime());
        h.setQuality(hw.getQuality());
        h.setEDep(hw.getEDep());
        h.setEDepError(hw.getEDepError());
      }
      try { h.setType(labelValue); } catch (...) {}

      double sXY = double(hw.getDistanceToWireError());
      double sZ  = double(hw.getPositionAlongWireError());
      if (!(sXY > 0.0)) sXY = m_defaultSigmaXYMM.value();
      if (!(sZ  > 0.0)) sZ  = m_defaultSigmaZMM.value();
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
      const int64_t ia = tagA[flatIdx];
      const int64_t ib = tagB[flatIdx];

      if (t == 0) {
        const auto& hp = (*inputPlanarHitCollections[ia])[int(ib)];
        if (m_produce3DHits.value()
            && (m_max3DHitsPerEvent.value()==0 || total3D < m_max3DHitsPerEvent.value())
            && (m_max3DPerTrack.value()==0     || made3D_for_track < m_max3DPerTrack.value())) {
          if (add_planar_3d(hp, labelValue, output3D)) { ++total3D; ++made3D_for_track; }
        }
        trk.addToTrackerHits(hp);
        return;
      }

      // Wire: project onto drift circle in XY
      const auto& hw = (*inputWireHitCollections[ia])[int(ib)];
      const auto wp  = hw.getPosition();
      double d = std::abs((double)hw.getDistanceToWire()); // mm
      if (d > m_wireGateMM.value()) d = m_wireGateMM.value(); // clamp absurd

      TVector3 wxy(wp.x, wp.y, 0.0);
      TVector3 u = (wxy - Cxy);
      const double r0 = u.Perp();
      if (u.Perp2() > 0) u *= (1.0 / u.Perp()); else u = TVector3(1,0,0);

      const double s = (R > r0 ? +1.0 : -1.0);
      TVector3 M(wxy.X() + s*d*u.X(),
                 wxy.Y() + s*d*u.Y(),
                 wp.z); // keep Z from wire center

      // residual gate: ||wxy-C|-R| ≈ d
      const double e = std::fabs(std::fabs(r0 - R) - d);
      const bool passGate = (e <= m_wireGateMM.value());

      if (passGate && m_produce3DHits.value()
          && (m_max3DHitsPerEvent.value()==0 || total3D < m_max3DHitsPerEvent.value())
          && (m_max3DPerTrack.value()==0     || made3D_for_track < m_max3DPerTrack.value())) {
        if (add_wire_3d(hw, M, labelValue, output3D)) { ++total3D; ++made3D_for_track; }
      }
      trk.addToTrackerHits(hw); // always keep original relation
    };

    // -------- assemble tracks from groups --------
    {
      StepTimer t_build;
      const int64_t nLabels = (int64_t)groups.size();
      int nTracks = 0;

      for (int64_t li = 0; li < nLabels; ++li) {
        if (groups[li].empty()) continue;

        int labelValue = uniques_cpu[li].item<int>();
        const auto& vec = groups[li];

        // --- label-0 guards (NEW) ---
        if (labelValue == 0) {
          if (m_skipZeroAlways.value()) continue;

          const int size = (int)vec.size();
          if (m_skipZeroIfSmall.value() && size < m_zeroMinSizeKeep.value()) {
            // too small to be meaningful
            continue;
          }

          int nWireInGroup = 0;
          for (auto k : vec) if (tagType[k] == 1) ++nWireInGroup;
          const double wireFrac = (size > 0) ? double(nWireInGroup)/double(size) : 0.0;

          bool good = (wireFrac >= m_minWireFracKeep.value());

          // quick circle sanity if we have ≥3 wire points
          if (good && nWire >= 3) {
            std::vector<int64_t> wires; wires.reserve(nWire);
            for (auto k: vec) if (tagType[k]==1) wires.push_back(k);
            auto pick3 = [&](const std::vector<int64_t>& v)
                -> std::tuple<TVector3,TVector3,TVector3,bool> {
              if (v.size() < 3) return {{},{},{},false};
              const TVector3 A = posCache[v.front()];
              const TVector3 B = posCache[v[v.size()/2]];
              const TVector3 C = posCache[v.back()];
              return {A,B,C,true};
            };
            TVector3 Cxy0; double R0=0;
            auto [A,B,C,have] = pick3(wires);
            bool ok = have && circle_from_3pts_xy(A,B,C,Cxy0,R0);
            if (!ok) good = false;
          }

          if (!good) {
            // reject low-quality zero-label group
            continue;
          }
          (void)m_promoteZeroIfGood;
        }

        auto trk = outputTracks.create();
        trk.setType(labelValue);

        // Seed circle: prefer wires if >=3; else any 3 points
        TVector3 Cxy(0,0,0); double R = 1e9;
        std::vector<int64_t> wireIdx; wireIdx.reserve(vec.size());
        for (auto k : vec) if (tagType[k] == 1) wireIdx.push_back(k);

        auto pick3_any = [&](const std::vector<int64_t>& v)
            -> std::tuple<TVector3,TVector3,TVector3,bool> {
          if (v.size() < 3) return {{},{},{},false};
          const TVector3 A = posCache[v.front()];
          const TVector3 B = posCache[v[v.size()/2]];
          const TVector3 C = posCache[v.back()];
          return {A,B,C,true};
        };

        bool ok=false;
        if (wireIdx.size() >= 3) {
          auto [A,B,C,have] = pick3_any(wireIdx);
          if (have) ok = circle_from_3pts_xy(A,B,C,Cxy,R);
        }
        if (!ok && vec.size() >= 3) {
          auto [A,B,C,have] = pick3_any(vec);
          if (have) ok = circle_from_3pts_xy(A,B,C,Cxy,R);
        }
        if (!ok) { Cxy = TVector3(0,0,0); R = 1e9; }

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

    return std::make_tuple(std::move(outputTracks), std::move(output3D));
  }

  // ---------- finalize ----------
  StatusCode finalize() override {
    auto [rss,hwm] = readRSSkB();
    info() << "GGTF_tracking finalize | events=" << m_evt
           << " | RSS=" << rss/1024.0 << "MB, Peak=" << hwm/1024.0 << "MB"
           << endmsg;
    return StatusCode::SUCCESS;
  }

private:
  // (no extra private fields beyond m_meta)
};

DECLARE_COMPONENT(GGTF_tracking)
