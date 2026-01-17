//======================================================================
// GGTF_tracking.cpp  (tracks + optional labeled SenseWireHits output)  [ROBUST / PHYSICS-SAFE]
//   - Designed for DCH-only workflows (no planar hits required)
//   - Runs ONNX embedding + clustering to build extension::TrackCollection (unchanged behavior)
//   - Outputs per-track *labeled* SenseWireHits (wire+drift info) for the fitter to consume
//       * OutputSenseWireHits default: "GGTF_SenseWireHits"
//       * Each output SenseWireHit has .type = cluster label (same as Track.type)
//   - Optional debug output: ALL used wire inputs copied to a separate SenseWireHit collection
//       * OutputAllSenseWireHits default: "GGTF_AllSenseWireHits"
//       * Each debug hit has .type = AllSenseWireHitsTypeValue (default -777)
//   - Keeps robust guards: truth PDG gating, absurd |d| dropping, missing collections, etc.
//
// Notes:
//   - We do NOT output 3D spacepoints anymore. The fitter should build WireMeasurementNew directly
//     from the (wire position, phi, stereo, drift distance+error, along-wire error) stored in SenseWireHit.
//   - Track-building (ONNX + clustering) still uses flattened inputs (including a derived midpoint Mmid).
//======================================================================

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <limits>
#include <memory>
#include <numeric>
#include <sstream>
#include <string>
#include <tuple>
#include <unordered_map>
#include <utility>
#include <vector>

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
#include "k4FWCore/MetaDataHandle.h"
#include "k4Interface/IGeoSvc.h"

// PODIO
#include "podio/ObjectID.h"

// EDM4hep & extensions
#include "edm4hep/TrackerHitPlaneCollection.h"
#include "edm4hep/SimTrackerHit.h"
#include "edm4hep/MCParticle.h"

#include "extension/SenseWireHitCollection.h"
#include "extension/TrackCollection.h"

// --- MC truth link: SenseWireHit -> SimTrackerHit
// Adjust include/type if your build uses a different name.
#include "extension/SenseWireHitSimTrackerHitLinkCollection.h"

// DD4hep (optional)
#include "DD4hep/Detector.h"
#include "DDSegmentation/BitFieldCoder.h"

// Local
#include "utils.hpp"

// ---------- helpers ----------
namespace {

inline std::pair<long, long> readRSSkB() {
  std::ifstream f("/proc/self/status");
  std::string key;
  long rss = 0, hwm = 0, val = 0;
  std::string unit;
  while (f >> key) {
    if (key == "VmRSS:") {
      f >> val >> unit;
      rss = val;
    } else if (key == "VmHWM:") {
      f >> val >> unit;
      hwm = val;
    }
    f.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
  }
  return {rss, hwm};
}

struct StepTimer {
  std::chrono::steady_clock::time_point t0{std::chrono::steady_clock::now()};
  double ms() const {
    auto dt = std::chrono::steady_clock::now() - t0;
    return std::chrono::duration_cast<std::chrono::milliseconds>(dt).count();
  }
};

// Pack podio::ObjectID (collectionID,index) into a stable 64-bit key
inline uint64_t oid_key(const podio::ObjectID& oid) {
  return (uint64_t(uint32_t(oid.collectionID)) << 32) | uint64_t(uint32_t(oid.index));
}

inline bool finite_vec3(const TVector3& v) {
  return std::isfinite(v.X()) && std::isfinite(v.Y()) && std::isfinite(v.Z());
}

inline TVector3 safe_unit(const TVector3& v, const TVector3& fallback) {
  const double m2 = v.Mag2();
  if (!(m2 > 0.0) || !std::isfinite(m2)) return fallback;
  return (1.0 / std::sqrt(m2)) * v;
}

// Copy a SenseWireHit (best effort; includes common fields used by digitizer + fitter)
inline void copy_sensewirehit(const extension::SenseWireHit& in, extension::MutableSenseWireHit& out) {
  // Core scalar fields
  try { out.setCellID(in.getCellID()); } catch (...) {}
  try { out.setTime(in.getTime()); } catch (...) {}
  try { out.setEDep(in.getEDep()); } catch (...) {}
  try { out.setEDepError(in.getEDepError()); } catch (...) {}
  try { out.setQuality(in.getQuality()); } catch (...) {}

  // Geometry / measurement fields
  try { out.setWireStereoAngle(in.getWireStereoAngle()); } catch (...) {}
  try { out.setWireAzimuthalAngle(in.getWireAzimuthalAngle()); } catch (...) {}
  try { out.setPosition(in.getPosition()); } catch (...) {}
  try { out.setPositionAlongWireError(in.getPositionAlongWireError()); } catch (...) {}
  try { out.setDistanceToWire(in.getDistanceToWire()); } catch (...) {}
  try { out.setDistanceToWireError(in.getDistanceToWireError()); } catch (...) {}

  // If your EDM extension has electron clusters stored
  try {
    for (auto e : in.getNElectrons()) out.addToNElectrons(e);
  } catch (...) {
    // ignore if not present in this build
  }
}

}  // namespace

/**
 * GGTF_tracking
 *
 * Inputs:
 *   - vector<TrackerHitPlaneCollection*>                 (planar/vtx/silicon)   [may be empty]
 *   - vector<SenseWireHitCollection*>                    (drift chamber wires)
 *   - vector<SenseWireHitSimTrackerHitLinkCollection*>   (MC-truth link)        [may be empty]
 *
 * Outputs:
 *   - extension::TrackCollection              (as upstream)
 *   - extension::SenseWireHitCollection       ("GGTF_SenseWireHits") per-track labeled wires (type=cluster label)
 *   - extension::SenseWireHitCollection       ("GGTF_AllSenseWireHits") debug-only (optional; type=AllSenseWireHitsTypeValue)
 */
struct GGTF_tracking final
    : k4FWCore::MultiTransformer<std::tuple<extension::TrackCollection,
                                           extension::SenseWireHitCollection,
                                           extension::SenseWireHitCollection>(
          const std::vector<const edm4hep::TrackerHitPlaneCollection*>&,
          const std::vector<const extension::SenseWireHitCollection*>&,
          const std::vector<const extension::SenseWireHitSimTrackerHitLinkCollection*>&)> {
  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<std::tuple<>, std::tuple<>, Traits>::KeyValues;

  GGTF_tracking(const std::string& name, ISvcLocator* svcLoc)
      : MultiTransformer(
            name,
            svcLoc,
            {KeyValues("InputPlanarHitCollections", std::vector<std::string>{"InputPlanarHitCollections"}),
             KeyValues("InputWireHitCollections", std::vector<std::string>{"InputWireHitCollections"}),
             KeyValues("InputWireSimLinkCollections", std::vector<std::string>{"InputWireSimLinkCollections"})},
            {KeyValues("OutputTracksGGTF", std::vector<std::string>{"OutputTracksGGTF"}),
             KeyValues("OutputSenseWireHits", std::vector<std::string>{"GGTF_SenseWireHits"}),
             KeyValues("OutputAllSenseWireHits", std::vector<std::string>{"GGTF_AllSenseWireHits"})}),
        m_cfgMeta("GGTF_trackingConfig", Gaudi::DataHandle::Writer) {
    m_geoSvc = serviceLocator()->service(m_geoSvcName);
  }

  // ---------- properties ----------
  Gaudi::Property<std::string> m_modelPath{this, "ModelPath", "", "Path to ONNX model"};
  Gaudi::Property<double>      m_tbeta{this, "Tbeta", 0.6, "clustering beta threshold"};
  Gaudi::Property<double>      m_td{this, "Td", 0.3, "clustering distance threshold"};

  Gaudi::Property<int> m_maxHitsPerEvent{this, "MaxHitsPerEvent", 0, "Cap input hits per event (0=off)"};
  Gaudi::Property<int> m_onnxChunk{this, "OnnxChunk", 4096, "Chunk size for ONNX inference"};

  // Output wires for fitter
  Gaudi::Property<bool> m_produceSenseWireHits{this, "ProduceSenseWireHits", true,
                                               "Emit per-track labeled SenseWireHits (GGTF_SenseWireHits)"};

  // Debug all-input wires (separate collection)
  Gaudi::Property<bool> m_produceAllSenseWireHits{this, "ProduceAllSenseWireHits", false,
                                                  "If true, create GGTF_AllSenseWireHits for ALL used wire inputs (debug)."};
  Gaudi::Property<int> m_allSenseWireHitsTypeValue{this, "AllSenseWireHitsTypeValue", -777,
                                                   "Type value for GGTF_AllSenseWireHits hits (debug-only)."};

  // Wire handling robustness
  Gaudi::Property<bool>   m_dropWireIfAbsDTooLarge{this, "DropWireIfAbsDTooLarge", true,
                                                   "Drop wire digi from GGTF processing if |d| > MaxAbsDMM"};
  Gaudi::Property<double> m_maxAbsDMM{this, "MaxAbsDMM", 30.0,
                                      "Maximum allowed |distanceToWire| [mm] before dropping (if enabled)"};

  // Label-0 guards (unchanged)
  Gaudi::Property<int> m_zeroMinSizeKeep{
      this, "ZeroMinSizeKeep", 8, "Min hits for a label=0 group to be considered (else dropped)"};
  Gaudi::Property<double> m_minWireFracKeep{
      this, "MinWireFracKeep", 0.60, "Min fraction of wire hits to keep a zero-label group"};
  Gaudi::Property<bool> m_promoteZeroIfGood{
      this, "PromoteZeroIfGood", true, "If a zero-label group passes checks, treat it as a normal cluster"};
  Gaudi::Property<bool> m_skipZeroIfSmall{
      this, "SkipZeroIfSmall", true, "If label=0 group smaller than ZeroMinSizeKeep, drop it"};
  Gaudi::Property<bool> m_skipZeroAlways{this, "SkipZeroAlways", false, "If true, never build tracks from label=0"};

  // Optional MC-truth PDG gate (diagnostic)
  Gaudi::Property<bool> m_filterInputWiresByTruthPdg{
      this, "FilterInputWiresByTruthPdg", true,
      "If true, exclude wire digis whose linked MCParticle PDG != KeepTruthPdg from GGTF processing."};
  Gaudi::Property<int> m_keepTruthPdg{
      this, "KeepTruthPdg", 13,
      "PDG code to keep when FilterInputWiresByTruthPdg is enabled (default 13=mu)."};
  Gaudi::Property<bool> m_dropWireIfUnlinked{
      this, "DropWireIfUnlinked", true,
      "When filtering enabled: if a wire digi has no truth link, drop it (true) or keep it (false)."};

  // Services
  Gaudi::Property<std::string> m_geoSvcName{this, "GeoSvcName", "GeoSvc", "GeoSvc name"};
  Gaudi::Property<std::string> m_dchName{this, "DchName", "DCH_v2", "Drift chamber detector name"};

  Gaudi::Property<std::string> m_jobTag{
      this, "JobTag", "",
      "Optional free-form tag (e.g. steering script name, input file, run label) stored in metadata"};

  // ---------- state ----------
  std::unique_ptr<Ort::Env>        m_fEnv;
  std::unique_ptr<Ort::Session>    m_fSession;
  Ort::SessionOptions              m_fSessionOptions;
  std::unique_ptr<Ort::MemoryInfo> m_fInfo;
  std::vector<std::string>         m_inNamesStr, m_outNamesStr;
  std::vector<const char*>         m_inNames, m_outNames;

  SmartIF<IGeoSvc> m_geoSvc;

  mutable int m_evt{0};
  k4FWCore::MetaDataHandle<std::string> m_cfgMeta;

  // ---------- init ----------
  StatusCode initialize() override {
    at::set_num_threads(1);
    at::set_num_interop_threads(1);

    m_fInfo = std::make_unique<Ort::MemoryInfo>(Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault));
    m_fEnv  = std::make_unique<Ort::Env>(ORT_LOGGING_LEVEL_WARNING, "ONNX_Runtime");
    m_fSessionOptions.SetIntraOpNumThreads(1);
    m_fSessionOptions.SetInterOpNumThreads(1);
    m_fSessionOptions.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_DISABLE_ALL);
    m_fSessionOptions.DisableMemPattern();
    m_fSessionOptions.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);

    m_fSession = std::make_unique<Ort::Session>(*m_fEnv, m_modelPath.value().c_str(), m_fSessionOptions);
    {
      Ort::AllocatorWithDefaultOptions alloc;
      const std::size_t i = 0;
      m_inNamesStr.emplace_back(m_fSession->GetInputNameAllocated(i, alloc).get());
      m_outNamesStr.emplace_back(m_fSession->GetOutputNameAllocated(i, alloc).get());
      m_inNames  = {m_inNamesStr.back().c_str()};
      m_outNames = {m_outNamesStr.back().c_str()};
    }

    auto [rss, hwm] = readRSSkB();
    info() << "GGTF_tracking init | model=" << m_modelPath.value()
           << " | Tbeta=" << m_tbeta.value() << " | Td=" << m_td.value()
           << " | ProduceSenseWireHits=" << (m_produceSenseWireHits.value() ? "true" : "false")
           << " | ProduceAllSenseWireHits=" << (m_produceAllSenseWireHits.value() ? "true" : "false")
           << " | AllSenseWireHitsTypeValue=" << m_allSenseWireHitsTypeValue.value()
           << " | MaxAbsDMM=" << m_maxAbsDMM.value()
           << " | DropWireIfAbsDTooLarge=" << (m_dropWireIfAbsDTooLarge.value() ? "true" : "false")
           << " | OnnxChunk=" << m_onnxChunk.value()
           << " | MaxHitsPerEvent=" << m_maxHitsPerEvent.value()
           << " | ZeroMinSizeKeep=" << m_zeroMinSizeKeep.value()
           << " | MinWireFracKeep=" << m_minWireFracKeep.value()
           << " | SkipZeroIfSmall=" << (m_skipZeroIfSmall.value() ? "true" : "false")
           << " | SkipZeroAlways=" << (m_skipZeroAlways.value() ? "true" : "false")
           << " | FilterInputWiresByTruthPdg=" << (m_filterInputWiresByTruthPdg.value() ? "true" : "false")
           << " | KeepTruthPdg=" << m_keepTruthPdg.value()
           << " | DropWireIfUnlinked=" << (m_dropWireIfUnlinked.value() ? "true" : "false")
           << " | JobTag=\"" << m_jobTag.value() << "\""
           << " | RSS=" << rss / 1024.0 << "MB, Peak=" << hwm / 1024.0 << "MB" << endmsg;

    // ---- write metadata (JSON string) ----
    try {
      std::ostringstream cfg;
      std::time_t now = std::time(nullptr);
      char tbuf[64] = {0};
      std::strftime(tbuf, sizeof(tbuf), "%Y-%m-%dT%H:%M:%SZ", std::gmtime(&now));

      cfg << "{";
      cfg << "\"component\":\"GGTF_tracking\"";
      cfg << ",\"timestamp_utc\":\"" << tbuf << "\"";
      cfg << ",\"JobTag\":\"" << m_jobTag.value() << "\"";
      cfg << ",\"ModelPath\":\"" << m_modelPath.value() << "\"";
      cfg << ",\"Tbeta\":" << m_tbeta.value();
      cfg << ",\"Td\":" << m_td.value();
      cfg << ",\"ProduceSenseWireHits\":" << (m_produceSenseWireHits.value() ? "true" : "false");
      cfg << ",\"ProduceAllSenseWireHits\":" << (m_produceAllSenseWireHits.value() ? "true" : "false");
      cfg << ",\"AllSenseWireHitsTypeValue\":" << m_allSenseWireHitsTypeValue.value();
      cfg << ",\"DropWireIfAbsDTooLarge\":" << (m_dropWireIfAbsDTooLarge.value() ? "true" : "false");
      cfg << ",\"MaxAbsDMM\":" << m_maxAbsDMM.value();
      cfg << ",\"OnnxChunk\":" << m_onnxChunk.value();
      cfg << ",\"MaxHitsPerEvent\":" << m_maxHitsPerEvent.value();
      cfg << ",\"DchName\":\"" << m_dchName.value() << "\"";
      cfg << ",\"ZeroMinSizeKeep\":" << m_zeroMinSizeKeep.value();
      cfg << ",\"MinWireFracKeep\":" << m_minWireFracKeep.value();
      cfg << ",\"PromoteZeroIfGood\":" << (m_promoteZeroIfGood.value() ? "true" : "false");
      cfg << ",\"SkipZeroIfSmall\":" << (m_skipZeroIfSmall.value() ? "true" : "false");
      cfg << ",\"SkipZeroAlways\":" << (m_skipZeroAlways.value() ? "true" : "false");
      cfg << ",\"FilterInputWiresByTruthPdg\":" << (m_filterInputWiresByTruthPdg.value() ? "true" : "false");
      cfg << ",\"KeepTruthPdg\":" << m_keepTruthPdg.value();
      cfg << ",\"DropWireIfUnlinked\":" << (m_dropWireIfUnlinked.value() ? "true" : "false");
      cfg << ",\"buildDate\":\"" << __DATE__ << "\"";
      cfg << ",\"buildTime\":\"" << __TIME__ << "\"";
      cfg << "}";

      m_cfgMeta.put(cfg.str());
      info() << "Wrote GGTF_tracking configuration metadata (key='GGTF_trackingConfig')" << endmsg;
    } catch (const std::exception& e) {
      warning() << "Failed to write GGTF_tracking metadata: " << e.what() << endmsg;
    } catch (...) {
      warning() << "Failed to write GGTF_tracking metadata (unknown exception)" << endmsg;
    }

    return StatusCode::SUCCESS;
  }

  // ---------- main ----------
  std::tuple<extension::TrackCollection, extension::SenseWireHitCollection, extension::SenseWireHitCollection>
  operator()(const std::vector<const edm4hep::TrackerHitPlaneCollection*>& inputPlanarHitCollections,
             const std::vector<const extension::SenseWireHitCollection*>& inputWireHitCollections,
             const std::vector<const extension::SenseWireHitSimTrackerHitLinkCollection*>& inputWireSimLinkCollections) const override {
    torch::NoGradGuard _nograd;
    ++m_evt;
    StepTimer t_all;

    extension::TrackCollection         outputTracks;
    extension::SenseWireHitCollection  outputWires;     // per-track labeled wires for fitter
    extension::SenseWireHitCollection  outputAllWires;  // debug all-input wires (optional)

    auto logMem = [&](const char* tag) {
      auto [rss, hwm] = readRSSkB();
      info() << "[evt " << m_evt << "] " << tag << " | RSS=" << rss / 1024.0
             << "MB, Peak=" << hwm / 1024.0 << "MB" << endmsg;
    };

    // -------- optional: build wire->PDG map for truth gating --------
    std::unordered_map<uint64_t, int> sw_pdg;
    bool doTruthGate = m_filterInputWiresByTruthPdg.value();
    if (doTruthGate) {
      StepTimer t_map;
      for (auto lcoll : inputWireSimLinkCollections) {
        if (!lcoll) continue;
        for (const auto& link : *lcoll) {
          const auto sw = link.getFrom();
          const auto sh = link.getTo();

          int pdg = 0;
          try {
            const auto mcp = sh.getParticle();
            pdg = mcp.getPDG();
          } catch (...) {
            pdg = 0;
          }

          const uint64_t key = oid_key(sw.getObjectID());
          if (sw_pdg.find(key) == sw_pdg.end()) sw_pdg.emplace(key, pdg);
        }
      }

      if (sw_pdg.empty()) {
        warning() << "[evt " << m_evt
                  << "] FilterInputWiresByTruthPdg=true but no wire->PDG links found "
                     "(InputWireSimLinkCollections empty/missing?). Disabling truth gate for this event."
                  << endmsg;
        doTruthGate = false;
      } else {
        info() << "[evt " << m_evt << "] truth gate map: wire->PDG entries=" << sw_pdg.size()
               << " in " << t_map.ms() << " ms" << endmsg;
      }
    }

    auto keep_wire_truth = [&](const extension::SenseWireHit& hw) -> bool {
      if (!doTruthGate) return true;
      const uint64_t key = oid_key(hw.getObjectID());
      auto it = sw_pdg.find(key);
      if (it == sw_pdg.end()) return !m_dropWireIfUnlinked.value();
      return (it->second == m_keepTruthPdg.value());
    };

    // -------- count inputs --------
    int64_t nPlanar = 0, nWire = 0;
    for (auto c : inputPlanarHitCollections) nPlanar += c ? c->size() : 0;
    for (auto c : inputWireHitCollections) nWire += c ? c->size() : 0;

    // -------- flatten inputs for ONNX --------
    int64_t nEst = nPlanar + nWire;
    if (m_maxHitsPerEvent > 0 && nEst > m_maxHitsPerEvent) {
      warning() << "[evt " << m_evt << "] capping hits " << nEst << " -> " << int(m_maxHitsPerEvent) << endmsg;
      nEst = m_maxHitsPerEvent;
    }

    std::vector<float>   gInputs;                 // (N,7)
    std::vector<int64_t> tagType, tagA, tagB;     // type: 0=planar, 1=wire; A=collection index, B=hit index
    gInputs.reserve(std::max<int64_t>(nEst * 7, 128));
    tagType.reserve(std::max<int64_t>(nEst, 128));
    tagA.reserve(tagType.capacity());
    tagB.reserve(tagType.capacity());

    int64_t droppedTruth = 0, droppedAbsD = 0;

    auto push_planar = [&](int ic, int ih, const edm4hep::TrackerHitPlane& h) {
      const auto p = h.getPosition();
      gInputs.insert(gInputs.end(), {float(p.x), float(p.y), float(p.z), 1.f, 0.f, 0.f, 0.f});
      tagType.push_back(0);
      tagA.push_back(ic);
      tagB.push_back(ih);
    };

    auto push_wire = [&](int ic, int ih, const extension::SenseWireHit& h) {
      // Truth gate
      if (!keep_wire_truth(h)) {
        ++droppedTruth;
        return;
      }

      const auto  wp    = h.getPosition();
      const double d    = double(h.getDistanceToWire());
      const double absd = std::abs(d);

      // Optional drop on absurd |d| (avoid forcing/clamping)
      if (m_dropWireIfAbsDTooLarge.value() && (absd > m_maxAbsDMM.value())) {
        ++droppedAbsD;
        return;
      }

      const double phi = double(h.getWireAzimuthalAngle());
      const double st  = double(h.getWireStereoAngle());

      // Wire direction (unit)
      TVector3 dir(0, 0, 1);
      dir.RotateX(st);
      dir.RotateZ(phi);
      dir = safe_unit(dir, TVector3(0, 0, 1));

      // Local xprime (stable), then yprime
      TVector3 xprime(1.0, 0.0, -dir.X() / std::max(1e-12, dir.Z()));
      xprime = safe_unit(xprime, TVector3(1, 0, 0));
      TVector3 yprime = dir.Cross(xprime);
      yprime = safe_unit(yprime, TVector3(0, 1, 0));
      xprime = safe_unit(yprime.Cross(dir), TVector3(1, 0, 0));

      // Build a derived midpoint Mmid for ONNX embedding using +/-d along xprime around the wire point.
      const TVector3 wpos(wp.x, wp.y, wp.z);
      const TVector3 L = wpos + xprime * (-d);
      const TVector3 R = wpos + xprime * (+d);
      const TVector3 Mmid = 0.5 * (L + R);
      if (!finite_vec3(Mmid)) return;

      // ONNX input: [x,y,z, isPlanar(0), wireDirVec(x,y,z)]
      const TVector3 dvec = (R - L);
      gInputs.insert(gInputs.end(),
                     {float(Mmid.X()), float(Mmid.Y()), float(Mmid.Z()),
                      0.f,
                      float(dvec.X()), float(dvec.Y()), float(dvec.Z())});
      tagType.push_back(1);
      tagA.push_back(ic);
      tagB.push_back(ih);
    };

    {
      StepTimer t_flat;
      int ic = 0;

      // Planar (safe if empty)
      for (auto c : inputPlanarHitCollections) {
        if (!c) { ++ic; continue; }
        for (int i = 0, n = c->size(); i < n; ++i) {
          if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
          push_planar(ic, i, (*c)[i]);
        }
        ++ic;
        if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
      }

      // Wires (main case)
      ic = 0;
      for (auto c : inputWireHitCollections) {
        if (!c) { ++ic; continue; }
        for (int i = 0, n = c->size(); i < n; ++i) {
          if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
          push_wire(ic, i, (*c)[i]);
        }
        ++ic;
        if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
      }

      info() << "[evt " << m_evt << "] flatten: planar=" << nPlanar << " wire=" << nWire
             << " -> used=" << tagType.size()
             << " (droppedTruth=" << droppedTruth << ", droppedAbsD=" << droppedAbsD << ")"
             << " in " << t_flat.ms() << " ms" << endmsg;
    }

    const int64_t nHits = (int64_t)tagType.size();
    if (nHits == 0) {
      return std::make_tuple(std::move(outputTracks), std::move(outputWires), std::move(outputAllWires));
    }
    logMem("after-flatten");

    // -------- optional debug: ALL used wire inputs -> outputAllWires --------
    if (m_produceAllSenseWireHits.value()) {
      StepTimer t_dbg;
      int made = 0;
      const int typeValue = m_allSenseWireHitsTypeValue.value();

      for (int64_t flatIdx = 0; flatIdx < nHits; ++flatIdx) {
        if (tagType[flatIdx] != 1) continue; // wires only
        const int64_t ia = tagA[flatIdx];
        const int64_t ib = tagB[flatIdx];

        if (ia < 0 || ia >= (int64_t)inputWireHitCollections.size()) continue;
        const auto* coll = inputWireHitCollections[ia];
        if (!coll) continue;
        if (ib < 0 || ib >= (int64_t)coll->size()) continue;

        const auto& hw = (*coll)[int(ib)];
        auto out = outputAllWires.create();
        copy_sensewirehit(hw, out);
        out.setType(typeValue);
        ++made;
      }

      info() << "[evt " << m_evt << "] ProduceAllSenseWireHits: created=" << made
             << " (collection=GGTF_AllSenseWireHits, type=" << typeValue << ")"
             << " in " << t_dbg.ms() << " ms" << endmsg;
    }

    // -------- ONNX (chunked) --------
    std::vector<float> embed;
    embed.resize(4 * nHits);
    {
      StepTimer t_onnx;
      const int64_t CH = std::max<int>(1, m_onnxChunk.value());
      int64_t done = 0;
      while (done < nHits) {
        const int64_t take = std::min<int64_t>(CH, nHits - done);
        const std::vector<int64_t> shape{take, 7};

        Ort::Value in = Ort::Value::CreateTensor<float>(
            *m_fInfo,
            const_cast<float*>(gInputs.data() + done * 7),
            take * 7,
            shape.data(),
            shape.size());

        auto outs = m_fSession->Run(Ort::RunOptions{nullptr},
                                    m_inNames.data(),
                                    &in,
                                    1,
                                    m_outNames.data(),
                                    m_outNames.size());
        float* outptr = outs.front().GetTensorMutableData<float>();
        std::copy(outptr, outptr + 4 * take, embed.data() + 4 * done);
        done += take;
      }

      std::vector<float>().swap(gInputs);
      info() << "[evt " << m_evt << "] onnx: nHits=" << nHits << " in " << t_onnx.ms() << " ms" << endmsg;
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

    // Bucket hits by label
    std::vector<std::vector<int64_t>> groups;
    torch::Tensor uniques_cpu;
    {
      StepTimer t_bucket;
      uniques_cpu = uniques.to(torch::kCPU);
      auto inv_cpu = invIdx.to(torch::kCPU).contiguous();
      const int64_t nLabels = uniques_cpu.size(0);
      groups.resize(nLabels);

      auto acc = inv_cpu.accessor<int64_t, 1>();
      for (int64_t i = 0; i < nHits; ++i) {
        const int64_t pos = acc[i];
        if (pos >= 0 && pos < nLabels) groups[pos].push_back(i);
      }
      info() << "[evt " << m_evt << "] bucket in " << t_bucket.ms() << " ms" << endmsg;
    }
    clustering = torch::Tensor();
    invIdx = torch::Tensor();
    logMem("after-bucket");

    // -------- assemble tracks + per-track labeled SenseWireHits --------
    auto add_hit_to_track = [&](extension::MutableTrack& trk,
                                int64_t flatIdx,
                                int labelValue) {
      const int64_t t  = tagType[flatIdx];
      const int64_t ia = tagA[flatIdx];
      const int64_t ib = tagB[flatIdx];

      if (t == 0) {
        // planar (likely none) - keep attaching to Track for completeness
        if (ia < 0 || ia >= (int64_t)inputPlanarHitCollections.size()) return;
        const auto* coll = inputPlanarHitCollections[ia];
        if (!coll) return;
        if (ib < 0 || ib >= (int64_t)coll->size()) return;
        const auto& hp = (*coll)[int(ib)];
        trk.addToTrackerHits(hp);
        return;
      }

      // wire
      if (ia < 0 || ia >= (int64_t)inputWireHitCollections.size()) return;
      const auto* coll = inputWireHitCollections[ia];
      if (!coll) return;
      if (ib < 0 || ib >= (int64_t)coll->size()) return;

      const auto& hw = (*coll)[int(ib)];

      // Output labeled wire hit (for fitter), if enabled
      if (m_produceSenseWireHits.value()) {
        auto out = outputWires.create();
        copy_sensewirehit(hw, out);
        out.setType(labelValue); // IMPORTANT: cluster label for grouping in fitter
      }

      // Always attach original wire hit to track (as upstream expects)
      trk.addToTrackerHits(hw);
    };

    {
      StepTimer t_build;
      const int64_t nLabels = (int64_t)groups.size();
      int nTracks = 0;

      for (int64_t li = 0; li < nLabels; ++li) {
        if (groups[li].empty()) continue;

        const int labelValue = uniques_cpu[li].item<int>();
        const auto& vec = groups[li];

        // label-0 guards as before
        if (labelValue == 0) {
          if (m_skipZeroAlways.value()) continue;

          const int size = (int)vec.size();
          if (m_skipZeroIfSmall.value() && size < m_zeroMinSizeKeep.value()) continue;

          int nWireInGroup = 0;
          for (auto k : vec) if (tagType[k] == 1) ++nWireInGroup;
          const double wireFrac = (size > 0) ? double(nWireInGroup) / double(size) : 0.0;

          bool good = (wireFrac >= m_minWireFracKeep.value());
          if (!good) continue;
          (void)m_promoteZeroIfGood;
        }

        auto trk = outputTracks.create();
        trk.setType(labelValue);

        for (int64_t k : vec) add_hit_to_track(trk, k, labelValue);
        ++nTracks;
      }

      info() << "[evt " << m_evt << "] build: tracks=" << nTracks
             << " | outSenseWireHits=" << (int)outputWires.size()
             << " in " << t_build.ms() << " ms" << endmsg;
    }

    logMem("after-build");
    info() << "[evt " << m_evt << "] TOTAL " << t_all.ms() << " ms" << endmsg;
    return std::make_tuple(std::move(outputTracks), std::move(outputWires), std::move(outputAllWires));
  }

  StatusCode finalize() override {
    auto [rss, hwm] = readRSSkB();
    info() << "GGTF_tracking finalize | events=" << m_evt
           << " | RSS=" << rss / 1024.0 << "MB, Peak=" << hwm / 1024.0 << "MB" << endmsg;
    return StatusCode::SUCCESS;
  }
};

DECLARE_COMPONENT(GGTF_tracking)
