//======================================================================
// GGTF_tracking.cpp  (tracks + optional 3D hits output)  [ROBUST / PHYSICS-SAFE]
//   - Designed for DCH-only workflows (no planar hits required)
//   - Produces per-track GGTF_3DHits suitable for fitting
//   - Optional debug “ALL input hits -> 3D hits” goes to a SEPARATE collection
//     to avoid contaminating physics fit groups.
//
// Key robustness fixes vs your previous file:
//   (R1) Debug “all-input” 3D hits are written to OutputAll3DHits (default "GGTF_All3DHits").
//        They NEVER mix into GGTF_3DHits. (No -777 mega-group accidental fit.)
//   (R2) Wire 3D hits default to ONNX midpoint (Mmid) for stability.
//   (R3) Wire covariances are ANISOTROPIC in the local (xprime,yprime,dir) basis:
//        sigma_xprime ~ sigma_drift (measured), sigma_yprime inflated (unmeasured), sigma_dir ~ sigma_along_wire.
//        Covariance is rotated into global XYZ and scaled consistently with ThreeDHitPosScale.
//   (R4) No “forcing” via distance clamp in physics path. Optional outlier rejection uses |d| threshold.
//   (R5) Defensive guards: missing collections, bad errors, NaNs, excessive sizes.
//   (R6) Since you have DCH-only, planar-related code remains safe if empty (no special logic required).
//
// Notes:
//   - Track-building (ONNX + clustering) still uses the flattened inputs.
//   - 3DHits are for downstream visualization and fitting. With anisotropic cov, the fitter can
//     downweight the unmeasured tangential direction properly.
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
#include "edm4hep/TrackerHit3DCollection.h"
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

// EDM4hep CovMatrix3f is packed (xx,xy,xz,yy,yz,zz)
inline edm4hep::CovMatrix3f pack_cov3f(double xx, double xy, double xz, double yy, double yz, double zz) {
  edm4hep::CovMatrix3f C;
  C[0] = float(xx);
  C[1] = float(xy);
  C[2] = float(xz);
  C[3] = float(yy);
  C[4] = float(yz);
  C[5] = float(zz);
  return C;
}

// Build global covariance from local orthonormal basis {e0,e1,e2} and diagonal variances.
// C = sum_i (sigma_i^2) * (e_i e_i^T)
inline edm4hep::CovMatrix3f cov_from_basis_diag(const TVector3& e0,
                                               const TVector3& e1,
                                               const TVector3& e2,
                                               double s0_mm,
                                               double s1_mm,
                                               double s2_mm) {
  const double v0 = s0_mm * s0_mm;
  const double v1 = s1_mm * s1_mm;
  const double v2 = s2_mm * s2_mm;

  const double ex0 = e0.X(), ey0 = e0.Y(), ez0 = e0.Z();
  const double ex1 = e1.X(), ey1 = e1.Y(), ez1 = e1.Z();
  const double ex2 = e2.X(), ey2 = e2.Y(), ez2 = e2.Z();

  const double xx = v0*ex0*ex0 + v1*ex1*ex1 + v2*ex2*ex2;
  const double xy = v0*ex0*ey0 + v1*ex1*ey1 + v2*ex2*ey2;
  const double xz = v0*ex0*ez0 + v1*ex1*ez1 + v2*ex2*ez2;
  const double yy = v0*ey0*ey0 + v1*ey1*ey1 + v2*ey2*ey2;
  const double yz = v0*ey0*ez0 + v1*ey1*ez1 + v2*ey2*ez2;
  const double zz = v0*ez0*ez0 + v1*ez1*ez1 + v2*ez2*ez2;

  return pack_cov3f(xx, xy, xz, yy, yz, zz);
}

inline bool finite_vec3(const TVector3& v) {
  return std::isfinite(v.X()) && std::isfinite(v.Y()) && std::isfinite(v.Z());
}

inline TVector3 safe_unit(const TVector3& v, const TVector3& fallback) {
  const double m2 = v.Mag2();
  if (!(m2 > 0.0) || !std::isfinite(m2)) return fallback;
  return (1.0 / std::sqrt(m2)) * v;
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
 *   - edm4hep::TrackerHit3DCollection     ("GGTF_3DHits") per-track physics 3D hits
 *   - edm4hep::TrackerHit3DCollection     ("GGTF_All3DHits") debug-only (optional)
 */
struct GGTF_tracking final
    : k4FWCore::MultiTransformer<std::tuple<extension::TrackCollection,
                                           edm4hep::TrackerHit3DCollection,
                                           edm4hep::TrackerHit3DCollection>(
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
             KeyValues("Output3DHits", std::vector<std::string>{"GGTF_3DHits"}),
             KeyValues("OutputAll3DHits", std::vector<std::string>{"GGTF_All3DHits"})}),
        m_cfgMeta("GGTF_trackingConfig", Gaudi::DataHandle::Writer) {

    m_geoSvc = serviceLocator()->service(m_geoSvcName);
  }

  // ---------- properties ----------
  Gaudi::Property<std::string> m_modelPath{this, "ModelPath", "", "Path to ONNX model"};
  Gaudi::Property<double>      m_tbeta{this, "Tbeta", 0.6, "clustering beta threshold"};
  Gaudi::Property<double>      m_td{this, "Td", 0.3, "clustering distance threshold"};

  Gaudi::Property<int> m_maxHitsPerEvent{this, "MaxHitsPerEvent", 0, "Cap input hits per event (0=off)"};
  Gaudi::Property<int> m_onnxChunk{this, "OnnxChunk", 4096, "Chunk size for ONNX inference"};

  // Physics 3D hits (per-track)
  Gaudi::Property<bool> m_produce3DHits{this, "Produce3DHits", true, "Emit per-track GGTF_3DHits"};
  Gaudi::Property<int>  m_max3DHitsPerEvent{this, "Max3DHitsPerEvent", 200000, "Cap per-track 3D hits per event"};
  Gaudi::Property<int>  m_max3DPerTrack{this, "Max3DPerTrack", 20000, "Cap per-track 3D hits per track"};

  // Debug all-input 3D hits (separate collection)
  Gaudi::Property<bool> m_produceAll3DHits{this, "ProduceAll3DHits", false,
                                          "If true, create GGTF_All3DHits for ALL flattened inputs (debug/coverage)."};
  Gaudi::Property<int>  m_all3DHitsTypeValue{this, "All3DHitsTypeValue", -777,
                                            "Type value for GGTF_All3DHits points (debug-only)."};
  Gaudi::Property<int>  m_maxAll3DHitsPerEvent{this, "MaxAll3DHitsPerEvent", 300000,
                                              "Cap debug all-input 3D hits per event"};

  // Units / diagnostics
  Gaudi::Property<double> m_threeDHitPosScale{
      this, "ThreeDHitPosScale", 1.0,
      "Scale applied to all written 3D hit positions. Covariances are scaled by scale^2 accordingly."};
  Gaudi::Property<bool> m_debugPrint3DHitR{
      this, "DebugPrint3DHitR", false,
      "Print a few sample r=sqrt(x^2+y^2) values of produced 3D hits early in event"};

  // Scalars propagation into 3D hits
  Gaudi::Property<bool> m_propagateScalars{this, "PropagateScalars", true,
                                          "Copy cellID/time/quality/EDep/EDepError into 3D hits (best effort)"};

  // Fallback sigmas if errors are missing/bad
  Gaudi::Property<double> m_defaultSigmaXYMM{this, "DefaultSigmaXYMM", 0.15, "Fallback sigma for planar-like XY [mm]"};
  Gaudi::Property<double> m_defaultSigmaZMM{this, "DefaultSigmaZMM", 2.0, "Fallback sigma for Z / along-wire [mm]"};

  // Wire handling robustness
  Gaudi::Property<bool>   m_dropWireIfAbsDTooLarge{this, "DropWireIfAbsDTooLarge", true,
                                                   "Drop wire digi from GGTF processing if |d| > MaxAbsDMM"};
  Gaudi::Property<double> m_maxAbsDMM{this, "MaxAbsDMM", 30.0,
                                      "Maximum allowed |distanceToWire| [mm] before dropping (if enabled)"};

  // Wire covariance model: anisotropy in local basis
  Gaudi::Property<double> m_wireSigmaTScale{this, "WireSigmaTScale", 10.0,
                                            "Tangential sigma multiplier: sigma_t = max(WireSigmaTMinMM, WireSigmaTScale*sigma_r)"};
  Gaudi::Property<double> m_wireSigmaTMinMM{this, "WireSigmaTMinMM", 2.0,
                                            "Minimum tangential sigma [mm] for wire 3D hits"};
  Gaudi::Property<double> m_wireSigmaTMaxMM{this, "WireSigmaTMaxMM", 100.0,
                                            "Maximum tangential sigma [mm] for wire 3D hits (safety cap)"};

  // Choose wire 3D point position mode (default midpoint for stability)
  // 0 = midpoint (recommended), 1 = wire center (wp), 2 = legacy projected (NOT recommended; not implemented here)
  Gaudi::Property<int> m_wire3DMode{this, "Wire3DMode", 0,
                                    "Wire 3D hit position: 0=midpoint (recommended), 1=wire center (wp)."};

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
           << " | Produce3DHits=" << (m_produce3DHits.value() ? "true" : "false")
           << " | ProduceAll3DHits=" << (m_produceAll3DHits.value() ? "true" : "false")
           << " | Wire3DMode=" << m_wire3DMode.value()
           << " | ThreeDHitPosScale=" << m_threeDHitPosScale.value()
           << " | MaxAbsDMM=" << m_maxAbsDMM.value()
           << " | DropWireIfAbsDTooLarge=" << (m_dropWireIfAbsDTooLarge.value() ? "true" : "false")
           << " | WireSigmaTScale=" << m_wireSigmaTScale.value()
           << " | WireSigmaTMinMM=" << m_wireSigmaTMinMM.value()
           << " | WireSigmaTMaxMM=" << m_wireSigmaTMaxMM.value()
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
      cfg << ",\"Produce3DHits\":" << (m_produce3DHits.value() ? "true" : "false");
      cfg << ",\"ProduceAll3DHits\":" << (m_produceAll3DHits.value() ? "true" : "false");
      cfg << ",\"All3DHitsTypeValue\":" << m_all3DHitsTypeValue.value();
      cfg << ",\"ThreeDHitPosScale\":" << m_threeDHitPosScale.value();
      cfg << ",\"Wire3DMode\":" << m_wire3DMode.value();
      cfg << ",\"DropWireIfAbsDTooLarge\":" << (m_dropWireIfAbsDTooLarge.value() ? "true" : "false");
      cfg << ",\"MaxAbsDMM\":" << m_maxAbsDMM.value();
      cfg << ",\"WireSigmaTScale\":" << m_wireSigmaTScale.value();
      cfg << ",\"WireSigmaTMinMM\":" << m_wireSigmaTMinMM.value();
      cfg << ",\"WireSigmaTMaxMM\":" << m_wireSigmaTMaxMM.value();
      cfg << ",\"OnnxChunk\":" << m_onnxChunk.value();
      cfg << ",\"MaxHitsPerEvent\":" << m_maxHitsPerEvent.value();
      cfg << ",\"Max3DHitsPerEvent\":" << m_max3DHitsPerEvent.value();
      cfg << ",\"Max3DPerTrack\":" << m_max3DPerTrack.value();
      cfg << ",\"MaxAll3DHitsPerEvent\":" << m_maxAll3DHitsPerEvent.value();
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
  std::tuple<extension::TrackCollection, edm4hep::TrackerHit3DCollection, edm4hep::TrackerHit3DCollection>
  operator()(const std::vector<const edm4hep::TrackerHitPlaneCollection*>& inputPlanarHitCollections,
             const std::vector<const extension::SenseWireHitCollection*>& inputWireHitCollections,
             const std::vector<const extension::SenseWireHitSimTrackerHitLinkCollection*>& inputWireSimLinkCollections) const override {
    torch::NoGradGuard _nograd;
    ++m_evt;
    StepTimer t_all;

    extension::TrackCollection      outputTracks;
    edm4hep::TrackerHit3DCollection output3D;      // per-track physics hits
    edm4hep::TrackerHit3DCollection outputAll3D;   // debug all-input hits

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

    std::vector<float>   gInputs;
    std::vector<int64_t> tagType, tagA, tagB;   // type: 0=planar, 1=wire; A=collection index, B=hit index
    gInputs.reserve(std::max<int64_t>(nEst * 7, 128));
    tagType.reserve(std::max<int64_t>(nEst, 128));
    tagA.reserve(tagType.capacity());
    tagB.reserve(tagType.capacity());

    // midCache: the ONNX position used for embedding (planar: pos, wire: Mmid)
    std::vector<TVector3> midCache;
    midCache.reserve(tagType.capacity());

    // For wires: store local orthonormal basis (xprime,yprime,dir) and errors.
    // Vectors aligned with flatIdx; for non-wire entries, we store defaults.
    std::vector<TVector3> basis0, basis1, basis2;
    std::vector<float>    wireSigmaR_mm, wireSigmaZ_mm;
    std::vector<float>    wireAbsD_mm;
    basis0.reserve(tagType.capacity());
    basis1.reserve(tagType.capacity());
    basis2.reserve(tagType.capacity());
    wireSigmaR_mm.reserve(tagType.capacity());
    wireSigmaZ_mm.reserve(tagType.capacity());
    wireAbsD_mm.reserve(tagType.capacity());

    // counters
    int64_t droppedTruth = 0, droppedAbsD = 0;

    auto push_planar = [&](int ic, int ih, const edm4hep::TrackerHitPlane& h) {
      const auto p = h.getPosition();
      gInputs.insert(gInputs.end(), {float(p.x), float(p.y), float(p.z), 1.f, 0.f, 0.f, 0.f});
      tagType.push_back(0);
      tagA.push_back(ic);
      tagB.push_back(ih);

      TVector3 v(p.x, p.y, p.z);
      midCache.emplace_back(v);

      // Default basis for planar-like: use global axes
      basis0.emplace_back(1, 0, 0);
      basis1.emplace_back(0, 1, 0);
      basis2.emplace_back(0, 0, 1);
      wireSigmaR_mm.emplace_back(float(m_defaultSigmaXYMM.value()));
      wireSigmaZ_mm.emplace_back(float(m_defaultSigmaZMM.value()));
      wireAbsD_mm.emplace_back(0.f);
    };

    auto push_wire = [&](int ic, int ih, const extension::SenseWireHit& h) {
      // Truth gate
      if (!keep_wire_truth(h)) {
        ++droppedTruth;
        return;
      }

      const auto  wp   = h.getPosition();
      const double d   = double(h.getDistanceToWire());
      const double absd = std::abs(d);

      // Optional drop on absurd |d| (avoid forcing/clamping)
      if (m_dropWireIfAbsDTooLarge.value() && (absd > m_maxAbsDMM.value())) {
        ++droppedAbsD;
        return;
      }

      const double phi = double(h.getWireAzimuthalAngle());
      const double st  = double(h.getWireStereoAngle());

      // Wire direction
      TVector3 dir(0, 0, 1);
      dir.RotateX(st);
      dir.RotateZ(phi);
      dir = safe_unit(dir, TVector3(0,0,1));

      // Local basis in plane perpendicular-ish to wire:
      // xprime is chosen so that z component cancels to keep it numerically stable;
      // yprime completes right-handed system.
      TVector3 xprime(1.0, 0.0, -dir.X() / std::max(1e-12, dir.Z()));
      xprime = safe_unit(xprime, TVector3(1,0,0));
      TVector3 yprime = dir.Cross(xprime);
      yprime = safe_unit(yprime, TVector3(0,1,0));
      // Re-orthonormalize xprime to be safe
      xprime = safe_unit(yprime.Cross(dir), TVector3(1,0,0));

      // Compute endpoints in the local xprime direction at +/- d (as originally done)
      const TVector3 wpos(wp.x, wp.y, wp.z);
      const TVector3 L = wpos + xprime * (-d);
      const TVector3 R = wpos + xprime * (+d);
      const TVector3 Mmid = 0.5 * (L + R);

      if (!finite_vec3(Mmid)) return;

      // ONNX input: position = Mmid, and wire direction vector = (R-L)
      const TVector3 dvec = (R - L);
      gInputs.insert(gInputs.end(),
                     {float(Mmid.X()), float(Mmid.Y()), float(Mmid.Z()),
                      0.f,
                      float(dvec.X()),
                      float(dvec.Y()),
                      float(dvec.Z())});
      tagType.push_back(1);
      tagA.push_back(ic);
      tagB.push_back(ih);

      midCache.emplace_back(Mmid);

      // store basis and errors
      basis0.emplace_back(xprime);
      basis1.emplace_back(yprime);
      basis2.emplace_back(dir);

      double sR = double(h.getDistanceToWireError());
      double sZ = double(h.getPositionAlongWireError());
      if (!(sR > 0.0) || !std::isfinite(sR)) sR = m_defaultSigmaXYMM.value();
      if (!(sZ > 0.0) || !std::isfinite(sZ)) sZ = m_defaultSigmaZMM.value();

      wireSigmaR_mm.emplace_back(float(sR));
      wireSigmaZ_mm.emplace_back(float(sZ));
      wireAbsD_mm.emplace_back(float(absd));
    };

    {
      StepTimer t_flat;
      int ic = 0;

      // Planar (safe if empty — you said you have none)
      for (auto c : inputPlanarHitCollections) {
        if (!c) { ++ic; continue; }
        for (int i = 0, n = c->size(); i < n; ++i) {
          if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
          push_planar(ic, i, (*c)[i]);
        }
        ++ic;
        if (m_maxHitsPerEvent > 0 && (int)tagType.size() >= m_maxHitsPerEvent) break;
      }

      // Wires (your main case)
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
      return std::make_tuple(std::move(outputTracks), std::move(output3D), std::move(outputAll3D));
    }
    logMem("after-flatten");

    // -------- 3D hit helpers (positions + cov scaling) --------
    const double posScale = m_threeDHitPosScale.value();
    const double covScale = posScale * posScale;

    int dbgPrinted = 0;
    auto maybe_dbg_print_r = [&](const edm4hep::Vector3d& p, const char* tag) {
      if (!m_debugPrint3DHitR.value()) return;
      if (dbgPrinted >= 6) return;
      const double r = std::sqrt(p.x * p.x + p.y * p.y);
      info() << "[evt " << m_evt << "] DBG3D(" << tag << "): x=" << p.x << " y=" << p.y << " z=" << p.z
             << " r=" << r << " (ThreeDHitPosScale=" << posScale << ")" << endmsg;
      ++dbgPrinted;
    };

    auto make_position = [&](double x, double y, double z) -> edm4hep::Vector3d {
      return edm4hep::Vector3d{posScale * x, posScale * y, posScale * z};
    };

    // Planar 3D (rare/none for you) — keep safe/fallback
    auto add_planar_3d = [&](const edm4hep::TrackerHitPlane& hp,
                             int typeValue,
                             edm4hep::TrackerHit3DCollection& out) -> bool {
      if (!m_produce3DHits.value()) return false;
      auto h = out.create();
      const auto p = hp.getPosition();
      const auto sp = make_position(p.x, p.y, p.z);
      h.setPosition(sp);
      maybe_dbg_print_r(sp, "planar");

      if (m_propagateScalars.value()) {
        try { h.setCellID(hp.getCellID()); } catch (...) {}
        try { h.setTime(hp.getTime()); } catch (...) { h.setTime(0.f); }
        try { h.setQuality(hp.getQuality()); } catch (...) {}
        try { h.setEDep(hp.getEDep()); } catch (...) { h.setEDep(0.f); }
        try { h.setEDepError(hp.getEDepError()); } catch (...) { h.setEDepError(0.f); }
      }
      try { h.setType(typeValue); } catch (...) {}

      const double sx = std::max(1e-6, m_defaultSigmaXYMM.value());
      const double sz = std::max(1e-6, m_defaultSigmaZMM.value());
      // isotropic fallback
      h.setCovMatrix(pack_cov3f(covScale*sx*sx, 0, 0, covScale*sx*sx, 0, covScale*sz*sz));
      return true;
    };

    // Wire 3D (physics): midpoint by default + anisotropic covariance in local basis
    auto add_wire_3d = [&](const extension::SenseWireHit& hw,
                           int64_t flatIdx,
                           int typeValue,
                           edm4hep::TrackerHit3DCollection& out) -> bool {
      if (!m_produce3DHits.value()) return false;

      auto h = out.create();

      // Choose position mode
      TVector3 P;
      if (m_wire3DMode.value() == 1) {
        const auto wp = hw.getPosition();
        P = TVector3(wp.x, wp.y, wp.z);
      } else {
        // recommended: midpoint used for ONNX
        P = midCache[flatIdx];
      }
      if (!finite_vec3(P)) return false;

      const auto sp = make_position(P.X(), P.Y(), P.Z());
      h.setPosition(sp);
      maybe_dbg_print_r(sp, "wire");

      if (m_propagateScalars.value()) {
        try { h.setCellID(hw.getCellID()); } catch (...) {}
        try { h.setTime(hw.getTime()); } catch (...) { h.setTime(0.f); }
        try { h.setQuality(hw.getQuality()); } catch (...) {}
        try { h.setEDep(hw.getEDep()); } catch (...) { h.setEDep(0.f); }
        try { h.setEDepError(hw.getEDepError()); } catch (...) { h.setEDepError(0.f); }
      }
      try { h.setType(typeValue); } catch (...) {}

      // Local basis (xprime,yprime,dir)
      const TVector3 e0 = safe_unit(basis0[flatIdx], TVector3(1,0,0)); // measured drift direction
      const TVector3 e1 = safe_unit(basis1[flatIdx], TVector3(0,1,0)); // unmeasured tangential
      const TVector3 e2 = safe_unit(basis2[flatIdx], TVector3(0,0,1)); // along-wire

      double sR = double(wireSigmaR_mm[flatIdx]);
      double sZ = double(wireSigmaZ_mm[flatIdx]);
      if (!(sR > 0.0) || !std::isfinite(sR)) sR = m_defaultSigmaXYMM.value();
      if (!(sZ > 0.0) || !std::isfinite(sZ)) sZ = m_defaultSigmaZMM.value();

      // Inflate tangential uncertainty (unmeasured by drift)
      double sT = m_wireSigmaTScale.value() * sR;
      sT = std::max(sT, m_wireSigmaTMinMM.value());
      sT = std::min(sT, m_wireSigmaTMaxMM.value());
      sT = std::max(1e-6, sT);
      sR = std::max(1e-6, sR);
      sZ = std::max(1e-6, sZ);

      auto Cmm = cov_from_basis_diag(e0, e1, e2, sR, sT, sZ);

      // Apply position scaling to covariance (units consistency)
      Cmm[0] *= float(covScale);
      Cmm[1] *= float(covScale);
      Cmm[2] *= float(covScale);
      Cmm[3] *= float(covScale);
      Cmm[4] *= float(covScale);
      Cmm[5] *= float(covScale);

      h.setCovMatrix(Cmm);
      return true;
    };

    // Debug “all-input” 3D hits (separate collection; never pollutes physics)
    if (m_produceAll3DHits.value()) {
      StepTimer t_dbg3d;
      int made = 0;
      const int typeValue = m_all3DHitsTypeValue.value();

      for (int64_t flatIdx = 0; flatIdx < nHits; ++flatIdx) {
        if (m_maxAll3DHitsPerEvent.value() > 0 && made >= m_maxAll3DHitsPerEvent.value()) break;

        const int64_t t  = tagType[flatIdx];
        const int64_t ia = tagA[flatIdx];
        const int64_t ib = tagB[flatIdx];

        if (t == 0) {
          // planar
          const auto& hp = (*inputPlanarHitCollections[ia])[int(ib)];
          if (add_planar_3d(hp, typeValue, outputAll3D)) ++made;
        } else {
          // wire (use midpoint for debug dots)
          const auto& hw = (*inputWireHitCollections[ia])[int(ib)];
          // Make a 3D hit at midpoint, with the same covariance logic (fine for debug)
          if (!m_produce3DHits.value()) continue;
          auto h = outputAll3D.create();
          const TVector3 P = midCache[flatIdx];
          if (!finite_vec3(P)) continue;
          const auto sp = make_position(P.X(), P.Y(), P.Z());
          h.setPosition(sp);
          maybe_dbg_print_r(sp, "all-wire");

          if (m_propagateScalars.value()) {
            try { h.setCellID(hw.getCellID()); } catch (...) {}
            try { h.setTime(hw.getTime()); } catch (...) { h.setTime(0.f); }
            try { h.setQuality(hw.getQuality()); } catch (...) {}
            try { h.setEDep(hw.getEDep()); } catch (...) { h.setEDep(0.f); }
            try { h.setEDepError(hw.getEDepError()); } catch (...) { h.setEDepError(0.f); }
          }
          try { h.setType(typeValue); } catch (...) {}

          // reuse anisotropic cov (scaled)
          const TVector3 e0 = safe_unit(basis0[flatIdx], TVector3(1,0,0));
          const TVector3 e1 = safe_unit(basis1[flatIdx], TVector3(0,1,0));
          const TVector3 e2 = safe_unit(basis2[flatIdx], TVector3(0,0,1));
          double sR = double(wireSigmaR_mm[flatIdx]); if (!(sR > 0.0)) sR = m_defaultSigmaXYMM.value();
          double sZ = double(wireSigmaZ_mm[flatIdx]); if (!(sZ > 0.0)) sZ = m_defaultSigmaZMM.value();
          double sT = std::min(std::max(m_wireSigmaTScale.value()*sR, m_wireSigmaTMinMM.value()), m_wireSigmaTMaxMM.value());
          sR = std::max(1e-6, sR); sT = std::max(1e-6, sT); sZ = std::max(1e-6, sZ);
          auto Cmm = cov_from_basis_diag(e0, e1, e2, sR, sT, sZ);
          Cmm[0] *= float(covScale); Cmm[1] *= float(covScale); Cmm[2] *= float(covScale);
          Cmm[3] *= float(covScale); Cmm[4] *= float(covScale); Cmm[5] *= float(covScale);
          h.setCovMatrix(Cmm);

          ++made;
        }
      }

      info() << "[evt " << m_evt << "] ProduceAll3DHits: created3D=" << made
             << " (collection=GGTF_All3DHits, type=" << typeValue << ")"
             << " in " << t_dbg3d.ms() << " ms" << endmsg;
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

    // -------- assemble tracks + per-track 3D hits --------
    int total3D = 0;

    auto add_hit_to_track = [&](extension::MutableTrack& trk,
                                int64_t flatIdx,
                                int labelValue,
                                int& made3D_for_track) {
      const int64_t t  = tagType[flatIdx];
      const int64_t ia = tagA[flatIdx];
      const int64_t ib = tagB[flatIdx];

      if (t == 0) {
        // planar (likely none)
        const auto& hp = (*inputPlanarHitCollections[ia])[int(ib)];
        if (m_produce3DHits.value() &&
            (m_max3DHitsPerEvent.value() == 0 || total3D < m_max3DHitsPerEvent.value()) &&
            (m_max3DPerTrack.value() == 0 || made3D_for_track < m_max3DPerTrack.value())) {
          if (add_planar_3d(hp, labelValue, output3D)) {
            ++total3D;
            ++made3D_for_track;
          }
        }
        trk.addToTrackerHits(hp);
        return;
      }

      // wire
      const auto& hw = (*inputWireHitCollections[ia])[int(ib)];

      // per-track 3D hit for fitter/visualization
      if (m_produce3DHits.value() &&
          (m_max3DHitsPerEvent.value() == 0 || total3D < m_max3DHitsPerEvent.value()) &&
          (m_max3DPerTrack.value() == 0 || made3D_for_track < m_max3DPerTrack.value())) {
        if (add_wire_3d(hw, flatIdx, labelValue, output3D)) {
          ++total3D;
          ++made3D_for_track;
        }
      }

      // always attach original wire hit to track (as upstream expects)
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

        // label-0 guards as before (still useful if ONNX produces zeros)
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

        int made3D_for_track = 0;
        for (int64_t k : vec) add_hit_to_track(trk, k, labelValue, made3D_for_track);
        ++nTracks;
      }

      info() << "[evt " << m_evt << "] build: tracks=" << nTracks
             << " physics3D=" << total3D
             << " in " << t_build.ms() << " ms" << endmsg;
    }

    logMem("after-build");
    info() << "[evt " << m_evt << "] TOTAL " << t_all.ms() << " ms" << endmsg;
    return std::make_tuple(std::move(outputTracks), std::move(output3D), std::move(outputAll3D));
  }

  StatusCode finalize() override {
    auto [rss, hwm] = readRSSkB();
    info() << "GGTF_tracking finalize | events=" << m_evt
           << " | RSS=" << rss / 1024.0 << "MB, Peak=" << hwm / 1024.0 << "MB" << endmsg;
    return StatusCode::SUCCESS;
  }
};

DECLARE_COMPONENT(GGTF_tracking)
