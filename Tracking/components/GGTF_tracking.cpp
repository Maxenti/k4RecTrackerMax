//======================================================================
// GGTF_tracking.cpp  (tracks + optional 3D hits output)  [with label-0 guards]
//   + OPTIONAL MC-truth PDG gating for *wire* hits (diagnostic mode)
//
//   CHANGES I MADE (search for "CHG:" in the file):
//    CHG-1) Add configurable position scaling for GGTF_3DHits:
//           - Property: ThreeDHitPosScale (default 1.0)
//           - Applied to BOTH planar and wire 3D hit positions at setPosition()
//           -> This directly addresses the “tiny radius helix” symptom if your 3DHits were
//              being written in cm but treated as mm (or vice versa). You can set:
//                 ThreeDHitPosScale = 10.0  (if your inputs are cm and you want mm)
//                 ThreeDHitPosScale = 0.1   (if your inputs are mm and you want cm)
//           (Keep your fitter PositionUnitScale as-is; fix the source here.)
//
//    CHG-2) Add an “ALL input hits -> 3DHits” debug mode (so viewtracks shows ~100% 3D dots):
//           - Property: ProduceAll3DHits (default false)
//           - Property: All3DHitsTypeValue (default -777)  (written to hit.getType())
//           - Property: All3DHitsOnly (default true)
//             *If true*: we create 3D hits for ALL flattened inputs right after flatten,
//                        and we DO NOT create per-track 3D hits later (avoids doubling).
//             *If false*: we create ALL-input 3D hits AND still also create per-track 3D hits.
//
//           For wires, “all-input 3D hits” use the same midpoint M that you feed to ONNX,
//           not the circle-projected point. This is purely to visualize coverage/debug.
//           Track-building is unchanged.
//
//    CHG-3) Allow disabling the wire gate specifically for 3D hit creation (NOT for tracking):
//           - Property: ApplyWireGateTo3DHits (default true)
//           If false, wire 3D hits get created even if passGate fails (using clamped d).
//
//    CHG-4) Extra debug print (optional) to quickly spot unit scale:
//           - Property: DebugPrint3DHitR (default false)
//           Prints a few sample radii of written 3D hits early in the event.
//
//======================================================================
//
// Notes on the PDG gate:
//  - This is MC-truth dependent and requires the wire->SimTrackerHit link collection.
//  - When enabled, non-matching wire digis are excluded from GGTF processing
//    (they do not go into ONNX, clustering, tracks, or GGTF_3DHits).
//  - If the link collection is missing/empty, the gate auto-disables for that event
//    to avoid dropping all wires by accident.
//
// IMPORTANT: The include/type name for the link collection may differ across builds.
// If your build doesn't have "extension/SenseWireHitSimTrackerHitLinkCollection.h",
// adjust that include + type accordingly (e.g. whatever produces DCHDigi2SimLinkCollection).
//

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
#include "k4Interface/IUniqueIDGenSvc.h"

// PODIO
#include "podio/ObjectID.h"

// EDM4hep & extensions
#include "edm4hep/TrackerHitPlaneCollection.h"
#include "edm4hep/TrackerHit3DCollection.h"
#include "edm4hep/SimTrackerHit.h"
#include "edm4hep/MCParticle.h"

#include "extension/SenseWireHitCollection.h"
#include "extension/TrackCollection.h"

// --- MC truth link: SenseWireHit -> SimTrackerHit
// Adjust this include/type if your build uses a different header/type name.
#include "extension/SenseWireHitSimTrackerHitLinkCollection.h"

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

// 3-point circle in XY; returns false if nearly colinear
inline bool circle_from_3pts_xy(const TVector3& A,
                                const TVector3& B,
                                const TVector3& C,
                                TVector3& center_xy,
                                double& R) {
  const double x1 = A.X(), y1 = A.Y(), x2 = B.X(), y2 = B.Y(), x3 = C.X(), y3 = C.Y();
  const double a  = x1 * (y2 - y3) - y1 * (x2 - x3) + x2 * y3 - x3 * y2;
  const double d  = 2.0 * a;
  if (std::abs(d) < 1e-9) return false;
  const double x1s = x1 * x1, y1s = y1 * y1, x2s = x2 * x2, y2s = y2 * y2, x3s = x3 * x3,
               y3s = y3 * y3;
  const double cx =
      ((x1s + y1s) * (y2 - y3) + (x2s + y2s) * (y3 - y1) + (x3s + y3s) * (y1 - y2)) / d;
  const double cy =
      ((x1s + y1s) * (x3 - x2) + (x2s + y2s) * (x1 - x3) + (x3s + y3s) * (x2 - x1)) / d;
  center_xy = TVector3(cx, cy, 0.0);
  R         = std::hypot(x1 - cx, y1 - cy);
  return std::isfinite(R) && R > 1e-6;
}

// Pack podio::ObjectID (collectionID,index) into a stable 64-bit key
inline uint64_t oid_key(const podio::ObjectID& oid) {
  return (uint64_t(uint32_t(oid.collectionID)) << 32) | uint64_t(uint32_t(oid.index));
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
 *   - extension::TrackCollection          (as upstream)
 *   - edm4hep::TrackerHit3DCollection     ("GGTF_3DHits") optional via Produce3DHits
 */
struct GGTF_tracking final
    : k4FWCore::MultiTransformer<std::tuple<extension::TrackCollection, edm4hep::TrackerHit3DCollection>(
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
             KeyValues("Output3DHits", std::vector<std::string>{"GGTF_3DHits"})}),
        // ✅ MetaDataHandle in your build: (descriptor, mode)
        m_cfgMeta("GGTF_trackingConfig", Gaudi::DataHandle::Writer) {

    m_geoSvc = serviceLocator()->service(m_geoSvcName);
  }

  // ---------- properties ----------
  Gaudi::Property<std::string> m_modelPath{this, "ModelPath", "", "Path to ONNX model"};
  Gaudi::Property<double>      m_tbeta{this, "Tbeta", 0.6, "clustering beta threshold"};
  Gaudi::Property<double>      m_td{this, "Td", 0.3, "clustering distance threshold"};

  Gaudi::Property<int> m_maxHitsPerEvent{this, "MaxHitsPerEvent", 0, "Cap input hits per event (0=off)"};
  Gaudi::Property<int> m_onnxChunk{this, "OnnxChunk", 4096, "Chunk size for ONNX inference"};

  Gaudi::Property<bool> m_produce3DHits{this, "Produce3DHits", true, "Emit GGTF_3DHits"};
  Gaudi::Property<int>  m_max3DHitsPerEvent{this, "Max3DHitsPerEvent", 200000, "Cap 3D hits per event"};
  Gaudi::Property<int>  m_max3DPerTrack{this, "Max3DPerTrack", 20000, "Cap 3D hits per track"};

  Gaudi::Property<double> m_wireGateMM{this, "WireGateMM", 12.0, "XY residual gate / clamp for wires [mm]"};

  Gaudi::Property<bool>   m_propagateScalars{this, "PropagateScalars", true,
                                            "Copy cellID/time/quality/EDep/EDepError into 3D hits"};
  Gaudi::Property<double> m_defaultSigmaXYMM{this, "DefaultSigmaXYMM", 0.10, "Fallback σX/Y [mm]"};
  Gaudi::Property<double> m_defaultSigmaZMM{this, "DefaultSigmaZMM", 1.00, "Fallback σZ [mm]"};

  Gaudi::Property<std::string> m_geoSvcName{this, "GeoSvcName", "GeoSvc", "GeoSvc name"};
  Gaudi::Property<std::string> m_uidSvcName{this, "UidSvcName", "uidSvc", "UniqueIDGenSvc name"};
  Gaudi::Property<std::string> m_dchName{this, "DchName", "DCH_v2", "Drift chamber detector name"};

  Gaudi::Property<std::string> m_jobTag{
      this, "JobTag", "",
      "Optional free-form tag (e.g. steering script name, input file, run label) to store in metadata"};

  Gaudi::Property<int> m_zeroMinSizeKeep{
      this, "ZeroMinSizeKeep", 8, "Min hits for a label=0 group to be considered (else dropped)"};
  Gaudi::Property<double> m_minWireFracKeep{
      this, "MinWireFracKeep", 0.60, "Min fraction of wire hits to keep a zero-label group"};
  Gaudi::Property<bool> m_promoteZeroIfGood{
      this, "PromoteZeroIfGood", true, "If a zero-label group passes checks, treat it as a normal cluster"};
  Gaudi::Property<bool> m_skipZeroIfSmall{
      this, "SkipZeroIfSmall", true, "If label=0 group smaller than ZeroMinSizeKeep, drop it"};
  Gaudi::Property<bool> m_skipZeroAlways{this, "SkipZeroAlways", false, "If true, never build tracks from label=0"};

  Gaudi::Property<bool> m_filterInputWiresByTruthPdg{
      this, "FilterInputWiresByTruthPdg", false,
      "If true, exclude wire digis whose linked MCParticle PDG != KeepTruthPdg from GGTF processing "
      "(ONNX + clustering + tracks + 3DHits)."};
  Gaudi::Property<int> m_keepTruthPdg{
      this, "KeepTruthPdg", 13,
      "PDG code to keep when FilterInputWiresByTruthPdg is enabled (default 13=mu)."};
  Gaudi::Property<bool> m_dropWireIfUnlinked{
      this, "DropWireIfUnlinked", true,
      "When filtering enabled: if a wire digi has no truth link, drop it (true) or keep it (false)."};

  // ---------------- CHG-1 / CHG-2 / CHG-3 / CHG-4 knobs ----------------
  // CHG-1: scale applied when writing 3D hit positions (unit-fix knob)
  Gaudi::Property<double> m_threeDHitPosScale{
      this, "ThreeDHitPosScale", 1.0,
      "Scale factor applied to GGTF_3DHits positions at write-out (diagnostic unit fix). "
      "Example: 10.0 converts cm->mm; 0.1 converts mm->cm."};

  // CHG-2: create 3D hits for ALL flattened inputs (debug coverage)
  Gaudi::Property<bool> m_produceAll3DHits{
      this, "ProduceAll3DHits", false,
      "If true, create GGTF_3DHits for ALL flattened input hits immediately after flatten (debug)."};
  Gaudi::Property<int> m_all3DHitsTypeValue{
      this, "All3DHitsTypeValue", -777,
      "Value written to TrackerHit3D.type for 3D hits produced by ProduceAll3DHits mode."};
  Gaudi::Property<bool> m_all3DHitsOnly{
      this, "All3DHitsOnly", true,
      "If ProduceAll3DHits=true and All3DHitsOnly=true, skip per-track 3D hit creation later "
      "(avoids double-counting / duplication)."};

  // CHG-3: optionally ignore wire gate when deciding whether to emit 3D hits
  Gaudi::Property<bool> m_applyWireGateTo3DHits{
      this, "ApplyWireGateTo3DHits", true,
      "If false, wire 3D hits are emitted even when passGate fails (still uses clamped d)."};

  // CHG-4: print a few sample radii of written 3D hits (helps spot unit scale)
  Gaudi::Property<bool> m_debugPrint3DHitR{
      this, "DebugPrint3DHitR", true,
      "If true, print a few sample r=sqrt(x^2+y^2) values of produced 3D hits early in event."};

  // ---------- state ----------
  std::unique_ptr<Ort::Env>        m_fEnv;
  std::unique_ptr<Ort::Session>    m_fSession;
  Ort::SessionOptions              m_fSessionOptions;
  std::unique_ptr<Ort::MemoryInfo> m_fInfo;
  std::vector<std::string>         m_inNamesStr, m_outNamesStr;
  std::vector<const char*>         m_inNames, m_outNames;

  SmartIF<IGeoSvc>                       m_geoSvc;
  dd4hep::DDSegmentation::BitFieldCoder* m_dchDecoder{nullptr};

  mutable int m_evt{0};

  // ✅ Plain MetaDataHandle, not pointer, not DataHandle-backed
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

    if (m_geoSvc && m_geoSvc->getDetector()) {
      try {
        auto sd = m_geoSvc->getDetector()->sensitiveDetector(m_dchName.value());
        if (sd.isValid()) {
          auto ro = sd.readout();
          if (ro.isValid()) m_dchDecoder = ro.idSpec().decoder();
        }
      } catch (...) {}
    }

    auto [rss, hwm] = readRSSkB();
    info() << "GGTF_tracking init | model=" << m_modelPath.value() << " | Tbeta=" << m_tbeta.value()
           << " | Td=" << m_td.value() << " | Produce3DHits=" << (m_produce3DHits.value() ? "true" : "false")
           << " | ProduceAll3DHits=" << (m_produceAll3DHits.value() ? "true" : "false")   // CHG
           << " | All3DHitsOnly=" << (m_all3DHitsOnly.value() ? "true" : "false")         // CHG
           << " | ThreeDHitPosScale=" << m_threeDHitPosScale.value()                      // CHG
           << " | ApplyWireGateTo3DHits=" << (m_applyWireGateTo3DHits.value() ? "true" : "false") // CHG
           << " | OnnxChunk=" << m_onnxChunk.value() << " | MaxHitsPerEvent=" << m_maxHitsPerEvent.value()
           << " | ZeroMinSizeKeep=" << m_zeroMinSizeKeep.value() << " | MinWireFracKeep=" << m_minWireFracKeep.value()
           << " | PromoteZeroIfGood=" << (m_promoteZeroIfGood.value() ? "true" : "false")
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
      cfg << ",\"Produce3DHits\":" << (m_produce3DHits.value() ? "true" : "false");
      cfg << ",\"ProduceAll3DHits\":" << (m_produceAll3DHits.value() ? "true" : "false");     // CHG
      cfg << ",\"All3DHitsOnly\":" << (m_all3DHitsOnly.value() ? "true" : "false");           // CHG
      cfg << ",\"All3DHitsTypeValue\":" << m_all3DHitsTypeValue.value();                      // CHG
      cfg << ",\"ThreeDHitPosScale\":" << m_threeDHitPosScale.value();                        // CHG
      cfg << ",\"ApplyWireGateTo3DHits\":" << (m_applyWireGateTo3DHits.value() ? "true" : "false"); // CHG
      cfg << ",\"OnnxChunk\":" << m_onnxChunk.value();
      cfg << ",\"MaxHitsPerEvent\":" << m_maxHitsPerEvent.value();
      cfg << ",\"Max3DHitsPerEvent\":" << m_max3DHitsPerEvent.value();
      cfg << ",\"Max3DPerTrack\":" << m_max3DPerTrack.value();
      cfg << ",\"WireGateMM\":" << m_wireGateMM.value();
      cfg << ",\"DefaultSigmaXYMM\":" << m_defaultSigmaXYMM.value();
      cfg << ",\"DefaultSigmaZMM\":" << m_defaultSigmaZMM.value();
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
  std::tuple<extension::TrackCollection, edm4hep::TrackerHit3DCollection>
  operator()(const std::vector<const edm4hep::TrackerHitPlaneCollection*>& inputPlanarHitCollections,
             const std::vector<const extension::SenseWireHitCollection*>& inputWireHitCollections,
             const std::vector<const extension::SenseWireHitSimTrackerHitLinkCollection*>&
                 inputWireSimLinkCollections) const override {
    torch::NoGradGuard _nograd;
    ++m_evt;
    StepTimer t_all;

    extension::TrackCollection      outputTracks;
    edm4hep::TrackerHit3DCollection output3D;

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

    auto keep_wire = [&](const extension::SenseWireHit& hw) -> bool {
      if (!doTruthGate) return true;
      const uint64_t key = oid_key(hw.getObjectID());
      auto it = sw_pdg.find(key);
      if (it == sw_pdg.end()) return !m_dropWireIfUnlinked.value();
      return (it->second == m_keepTruthPdg.value());
    };

    // -------- flatten inputs --------
    int64_t nPlanar = 0, nWire = 0;
    for (auto c : inputPlanarHitCollections) nPlanar += c ? c->size() : 0;
    for (auto c : inputWireHitCollections) nWire += c ? c->size() : 0;
    int64_t nEst = nPlanar + nWire;

    if (m_maxHitsPerEvent > 0 && nEst > m_maxHitsPerEvent) {
      warning() << "[evt " << m_evt << "] capping hits " << nEst << " -> " << int(m_maxHitsPerEvent) << endmsg;
      nEst = m_maxHitsPerEvent;
    }

    std::vector<float> gInputs;
    gInputs.reserve(std::max<int64_t>(nEst * 7, 128));
    std::vector<int64_t> tagType;
    tagType.reserve(std::max<int64_t>(nEst, 128));
    std::vector<int64_t> tagA, tagB;

    // posCache: used by circle estimation (wire uses raw wire position)
    std::vector<TVector3> posCache;
    posCache.reserve(tagType.capacity());

    // CHG-2: midCache stores the actual ONNX position (planar: pos, wire: M midpoint)
    std::vector<TVector3> midCache;
    midCache.reserve(tagType.capacity());

    auto push_planar = [&](int ic, int ih, const edm4hep::TrackerHitPlane& h) {
      const auto p = h.getPosition();
      gInputs.insert(gInputs.end(), {float(p.x), float(p.y), float(p.z), 1.f, 0.f, 0.f, 0.f});
      tagType.push_back(0);
      tagA.push_back(ic);
      tagB.push_back(ih);

      TVector3 v(p.x, p.y, p.z);
      posCache.emplace_back(v);
      midCache.emplace_back(v);  // CHG-2
    };

    auto push_wire = [&](int ic, int ih, const extension::SenseWireHit& h) {
      const auto  wp   = h.getPosition();
      const double d   = h.getDistanceToWire();
      const double phi = h.getWireAzimuthalAngle();
      const double st  = h.getWireStereoAngle();

      TVector3 wpos(wp.x, wp.y, wp.z);
      TVector3 dir(0, 0, 1);
      dir.RotateX(st);
      dir.RotateZ(phi);
      dir = dir.Unit();

      TVector3 xprime(1.0, 0.0, -dir.X() / std::max(1e-9, dir.Z()));
      xprime = xprime.Unit();
      TVector3 yprime = dir.Cross(xprime).Unit();

      const TVector3 l(-d, 0, 0), r(+d, 0, 0);
      const auto L = xprime * l.X() + yprime * l.Y() + dir * l.Z() + wpos;
      const auto R = xprime * r.X() + yprime * r.Y() + dir * r.Z() + wpos;
      const auto M = 0.5 * (L + R);

      gInputs.insert(gInputs.end(),
                     {float(M.X()), float(M.Y()), float(M.Z()),
                      0.f,
                      float(R.X() - L.X()),
                      float(R.Y() - L.Y()),
                      float(R.Z() - L.Z())});
      tagType.push_back(1);
      tagA.push_back(ic);
      tagB.push_back(ih);

      posCache.emplace_back(wp.x, wp.y, wp.z);
      midCache.emplace_back(M);  // CHG-2: store ONNX midpoint for “all 3D hits” mode
    };

    {
      StepTimer t_flat;
      int ic = 0;

      for (auto c : inputPlanarHitCollections) {
        if (!c) { ++ic; continue; }
        for (int i = 0, n = c->size(); i < n; ++i) {
          if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
          push_planar(ic, i, (*c)[i]);
        }
        ++ic;
        if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
      }

      ic = 0;
      for (auto c : inputWireHitCollections) {
        if (!c) { ++ic; continue; }
        for (int i = 0, n = c->size(); i < n; ++i) {
          if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
          const auto& hw = (*c)[i];
          if (!keep_wire(hw)) continue;
          push_wire(ic, i, hw);
        }
        ++ic;
        if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
      }

      info() << "[evt " << m_evt << "] flatten: planar=" << nPlanar << " wire=" << nWire
             << " -> used=" << tagType.size()
             << " in " << t_flat.ms() << " ms" << endmsg;
    }

    const int64_t nHits = (int64_t)tagType.size();
    if (nHits == 0) {
      return std::make_tuple(std::move(outputTracks), std::move(output3D));
    }
    logMem("after-flatten");

    // -------- 3D hit helpers (now include pos scale) --------
    // CHG-1: apply m_threeDHitPosScale at write-out
    auto scaled_pos = [&](double x, double y, double z) -> edm4hep::Vector3d {
      const double s = m_threeDHitPosScale.value();
      return edm4hep::Vector3d{s * x, s * y, s * z};
    };

    // Helper lambdas to create 3D hits
    int total3D = 0;
    int dbgPrinted = 0;

    auto maybe_dbg_print_r = [&](const edm4hep::Vector3d& p, const char* tag) {
      if (!m_debugPrint3DHitR.value()) return;
      if (dbgPrinted >= 6) return;
      const double r = std::sqrt(p.x * p.x + p.y * p.y);
      info() << "[evt " << m_evt << "] DBG3D(" << tag << "): x=" << p.x << " y=" << p.y << " z=" << p.z
             << " r=" << r << " (ThreeDHitPosScale=" << m_threeDHitPosScale.value() << ")" << endmsg;
      ++dbgPrinted;
    };

    auto add_planar_3d = [&](const edm4hep::TrackerHitPlane& hp,
                             int labelValue,
                             edm4hep::TrackerHit3DCollection& out3Dcoll) -> bool {
      if (!m_produce3DHits.value()) return false;
      auto h = out3Dcoll.create();

      const auto p = hp.getPosition();
      auto sp = scaled_pos(p.x, p.y, p.z);     // CHG-1
      h.setPosition(sp);
      maybe_dbg_print_r(sp, "planar");         // CHG-4

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

      auto sp = scaled_pos(double(M.X()), double(M.Y()), double(M.Z())); // CHG-1
      h.setPosition(sp);
      maybe_dbg_print_r(sp, "wire");                                     // CHG-4

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
      if (!(sZ > 0.0))  sZ  = m_defaultSigmaZMM.value();
      const float sx = std::max<float>(1e-6f, float(sXY));
      const float sz = std::max<float>(1e-6f, float(sZ));
      h.setCovMatrix(diag_cov_3d(sx, sx, sz));
      return true;
    };

    // CHG-2: create a wire 3D hit at the ONNX midpoint (no circle projection)
    auto add_wire_mid_3d = [&](const extension::SenseWireHit& hw,
                               const TVector3& Mmid,
                               int typeValue,
                               edm4hep::TrackerHit3DCollection& out3Dcol) -> bool {
      if (!m_produce3DHits.value()) return false;
      auto h = out3Dcol.create();

      auto sp = scaled_pos(double(Mmid.X()), double(Mmid.Y()), double(Mmid.Z())); // CHG-1
      h.setPosition(sp);
      maybe_dbg_print_r(sp, "wireMid");                                           // CHG-4

      if (m_propagateScalars.value()) {
        h.setCellID(hw.getCellID());
        h.setTime(hw.getTime());
        h.setQuality(hw.getQuality());
        h.setEDep(hw.getEDep());
        h.setEDepError(hw.getEDepError());
      }
      try { h.setType(typeValue); } catch (...) {}

      double sXY = double(hw.getDistanceToWireError());
      double sZ  = double(hw.getPositionAlongWireError());
      if (!(sXY > 0.0)) sXY = m_defaultSigmaXYMM.value();
      if (!(sZ > 0.0))  sZ  = m_defaultSigmaZMM.value();
      const float sx = std::max<float>(1e-6f, float(sXY));
      const float sz = std::max<float>(1e-6f, float(sZ));
      h.setCovMatrix(diag_cov_3d(sx, sx, sz));
      return true;
    };

    // CHG-2: ProduceAll3DHits right after flatten (coverage/debug)
    if (m_produce3DHits.value() && m_produceAll3DHits.value()) {
      StepTimer t_all3d;
      const int typeValue = m_all3DHitsTypeValue.value();

      int made = 0;
      for (int64_t flatIdx = 0; flatIdx < nHits; ++flatIdx) {
        if (m_max3DHitsPerEvent.value() > 0 && total3D >= m_max3DHitsPerEvent.value()) break;

        const int64_t t  = tagType[flatIdx];
        const int64_t ia = tagA[flatIdx];
        const int64_t ib = tagB[flatIdx];

        if (t == 0) {
          const auto& hp = (*inputPlanarHitCollections[ia])[int(ib)];
          if (add_planar_3d(hp, typeValue, output3D)) {
            ++total3D;
            ++made;
          }
        } else {
          const auto& hw = (*inputWireHitCollections[ia])[int(ib)];
          const TVector3& Mmid = midCache[flatIdx];
          if (add_wire_mid_3d(hw, Mmid, typeValue, output3D)) {
            ++total3D;
            ++made;
          }
        }
      }

      info() << "[evt " << m_evt << "] ProduceAll3DHits: created3D=" << made
             << " (type=" << typeValue << ") in " << t_all3d.ms() << " ms" << endmsg;
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
        Ort::Value in = Ort::Value::CreateTensor<float>(*m_fInfo,
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

    auto add_hit_to_track = [&](extension::MutableTrack& trk,
                                int64_t flatIdx,
                                const TVector3& Cxy,
                                double R,
                                int labelValue,
                                int& made3D_for_track) {
      const int64_t t  = tagType[flatIdx];
      const int64_t ia = tagA[flatIdx];
      const int64_t ib = tagB[flatIdx];

      if (t == 0) {
        const auto& hp = (*inputPlanarHitCollections[ia])[int(ib)];

        // CHG-2: if "all 3D hits only" mode, don't add per-track 3D hits
        if (!(m_produceAll3DHits.value() && m_all3DHitsOnly.value())) {
          if (m_produce3DHits.value() &&
              (m_max3DHitsPerEvent.value() == 0 || total3D < m_max3DHitsPerEvent.value()) &&
              (m_max3DPerTrack.value() == 0 || made3D_for_track < m_max3DPerTrack.value())) {
            if (add_planar_3d(hp, labelValue, output3D)) {
              ++total3D;
              ++made3D_for_track;
            }
          }
        }

        trk.addToTrackerHits(hp);
        return;
      }

      const auto& hw = (*inputWireHitCollections[ia])[int(ib)];
      const auto wp  = hw.getPosition();
      double d = std::abs((double)hw.getDistanceToWire());
      if (d > m_wireGateMM.value()) d = m_wireGateMM.value();

      TVector3 wxy(wp.x, wp.y, 0.0);
      TVector3 u = (wxy - Cxy);
      const double r0 = u.Perp();
      if (u.Perp2() > 0) u *= (1.0 / u.Perp());
      else u = TVector3(1, 0, 0);

      const double s = (R > r0 ? +1.0 : -1.0);
      TVector3 M(wxy.X() + s * d * u.X(), wxy.Y() + s * d * u.Y(), wp.z);

      const double e = std::fabs(std::fabs(r0 - R) - d);
      const bool passGate = (e <= m_wireGateMM.value());

      // CHG-3: ApplyWireGateTo3DHits controls whether passGate is required to emit 3D hits
      const bool allow3D = passGate || (!m_applyWireGateTo3DHits.value());

      // CHG-2: if "all 3D hits only" mode, don't add per-track 3D hits
      if (!(m_produceAll3DHits.value() && m_all3DHitsOnly.value())) {
        if (allow3D && m_produce3DHits.value() &&
            (m_max3DHitsPerEvent.value() == 0 || total3D < m_max3DHitsPerEvent.value()) &&
            (m_max3DPerTrack.value() == 0 || made3D_for_track < m_max3DPerTrack.value())) {
          if (add_wire_3d(hw, M, labelValue, output3D)) {
            ++total3D;
            ++made3D_for_track;
          }
        }
      }

      trk.addToTrackerHits(hw);
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

        if (labelValue == 0) {
          if (m_skipZeroAlways.value()) continue;

          const int size = (int)vec.size();
          if (m_skipZeroIfSmall.value() && size < m_zeroMinSizeKeep.value()) continue;

          int nWireInGroup = 0;
          for (auto k : vec) if (tagType[k] == 1) ++nWireInGroup;
          const double wireFrac = (size > 0) ? double(nWireInGroup) / double(size) : 0.0;

          bool good = (wireFrac >= m_minWireFracKeep.value());

          if (good && nWire >= 3) {
            std::vector<int64_t> wires;
            wires.reserve(nWire);
            for (auto k : vec) if (tagType[k] == 1) wires.push_back(k);

            auto pick3 = [&](const std::vector<int64_t>& v) -> std::tuple<TVector3, TVector3, TVector3, bool> {
              if (v.size() < 3) return {{}, {}, {}, false};
              const TVector3 A = posCache[v.front()];
              const TVector3 B = posCache[v[v.size() / 2]];
              const TVector3 C = posCache[v.back()];
              return {A, B, C, true};
            };

            TVector3 Cxy0;
            double R0 = 0;
            auto [A, B, C, have] = pick3(wires);
            bool ok = have && circle_from_3pts_xy(A, B, C, Cxy0, R0);
            if (!ok) good = false;
          }

          if (!good) continue;
          (void)m_promoteZeroIfGood;
        }

        auto trk = outputTracks.create();
        trk.setType(labelValue);

        TVector3 Cxy(0, 0, 0);
        double R = 1e9;
        std::vector<int64_t> wireIdx;
        wireIdx.reserve(vec.size());
        for (auto k : vec) if (tagType[k] == 1) wireIdx.push_back(k);

        auto pick3_any = [&](const std::vector<int64_t>& v) -> std::tuple<TVector3, TVector3, TVector3, bool> {
          if (v.size() < 3) return {{}, {}, {}, false};
          const TVector3 A = posCache[v.front()];
          const TVector3 B = posCache[v[v.size() / 2]];
          const TVector3 C = posCache[v.back()];
          return {A, B, C, true};
        };

        bool ok = false;
        if (wireIdx.size() >= 3) {
          auto [A, B, C, have] = pick3_any(wireIdx);
          if (have) ok = circle_from_3pts_xy(A, B, C, Cxy, R);
        }
        if (!ok && vec.size() >= 3) {
          auto [A, B, C, have] = pick3_any(vec);
          if (have) ok = circle_from_3pts_xy(A, B, C, Cxy, R);
        }
        if (!ok) { Cxy = TVector3(0, 0, 0); R = 1e9; }

        int made3D_for_track = 0;
        for (int64_t k : vec) add_hit_to_track(trk, k, Cxy, R, labelValue, made3D_for_track);
        ++nTracks;
      }

      info() << "[evt " << m_evt << "] build: tracks=" << nTracks << " created3D=" << total3D
             << " in " << t_build.ms() << " ms" << endmsg;
    }

    logMem("after-build");
    info() << "[evt " << m_evt << "] TOTAL " << t_all.ms() << " ms" << endmsg;
    return std::make_tuple(std::move(outputTracks), std::move(output3D));
  }

  StatusCode finalize() override {
    auto [rss, hwm] = readRSSkB();
    info() << "GGTF_tracking finalize | events=" << m_evt
           << " | RSS=" << rss / 1024.0 << "MB, Peak=" << hwm / 1024.0 << "MB" << endmsg;
    return StatusCode::SUCCESS;
  }
};

DECLARE_COMPONENT(GGTF_tracking)
