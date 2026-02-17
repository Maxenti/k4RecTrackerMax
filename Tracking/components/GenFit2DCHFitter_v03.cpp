// ======================================================================

// DOC:
// Summary: Gaudi/k4FWCore Transformer that fits IDEA drift-chamber GGTF track candidates using GenFit2 wire measurements (WireMeasurementNew), producing physics-clean EDM4hep TrackStates at the IP with robust publish-state selection, observability gating, optional TGeo material effects, and per-event robust pT summary metadata.
// Usage:
//   - As a Gaudi component in a k4run job (Key4HEP / k4RecTracker):
//       from Configurables import GenFit2DCHFitter
//       fitter = GenFit2DCHFitter(
//         inputTracks   = ["OutputTracksGGTF"],
//         outputTracks  = ["GenFitTracks"],
//         Bz            = 2.0,
//         PDG           = 13,
//         UseDAF        = True,
//         UseMaterialEffects = True,
//         PositionUnitScale  = 0.1,      # mm->cm for GenFit internal units
//       )
//       ApplicationMgr(TopAlg=[fitter], EvtSel="NONE", EvtMax=-1)
//   - Typical CLI wrapper is your existing reco pipeline (e.g., scripts/reco_job.sh + options.py) that runs k4run with this component in TopAlg.
// Inputs:
//   - EDM4hep/extension TrackCollection: GGTF-produced track candidates (default: "OutputTracksGGTF").
//   - Each input extension::Track is expected to have trackerHits relations containing extension::SenseWireHit objects (SenseWireHits).
//   - For material effects (optional): ROOT TGeo geometry available via gGeoManager (loaded by framework) OR imported from a ROOT file via:
//       TGeoFile="<detector.root>" (optional), and optionally TGeoTopVolume="<volName>".
// Outputs:
//   - EDM4hep/extension TrackCollection: fitted tracks (default: "GenFitTracks").
//   - Each output track has:
//       * type set to PDG hypothesis (PDG property, default 13).
//       * chi2/ndf filled from GenFit FitStatus.
//       * trackerHits relation propagated from input (same hits, for traceability).
//       * an EDM4hep TrackState with location=AtIP added via addAtIPState():
//           - TrackState.time = pT [GeV] when pT is considered valid, else InvalidPTSentinel (default -1).
//           - TrackState.omega = q/pT [GeV^-1] (signed curvature convention).
//           - referencePoint = (x,y,z) at IP (or publish state if IP extrap fails), in mm.
//           - covariance: either full 5x5 perigee covariance (d0,phi,omega,z0,tanLambda) from FD Jacobian,
//             or fallback placeholder diagonal entries.
//   - k4FWCore MetaDataHandle<string> written:
//       * cfgMeta: JSON blob of fitter configuration (written at initialize()).
//       * evtMeta: JSON blob of per-event summary counts + robust pT stats (written each event).
// Connects-To:
//   - Upstream: GGTF_tracking.cpp (or equivalent) that produces inputTracks and attaches SenseWireHits via trackerHits relation.
//   - Downstream:
//       * analysis scripts reading GenFitTracks TrackStates (AtIP) to compute pT resolution vs pT/eta.
//       * compare/diagnostic scripts comparing TrackState pT to hit-based curvature observability metrics.
//   - Geometry/material pipeline:
//       * ddsim/DD4hep -> ROOT TGeo export (optional) -> this fitter via gGeoManager or TGeoFile import.
// Collections:
//   - inputTracks (vector<string>): default ["OutputTracksGGTF"]
//   - outputTracks (vector<string>): default ["GenFitTracks"]
//   - Metadata keys (k4FWCore::MetaDataHandle<string>):
//       * "cfgMeta" (Writer) : job-level JSON config snapshot
//       * "evtMeta" (Writer) : event-level JSON summary + robust pT stats
// Algorithm-Flow:
//   1) Read each input track; collect SenseWireHits from trackerHits; optionally reject negative labels (debug groups).
//   2) Optional hit preprocessing:
//       - SortHits: stable PCA-based ordering along principal axis of on-wire positions.
//       - DeduplicateHits: drop nearly-identical positions within DedupTolMM.
//       - PreFitOutlierVeto: deterministic XY outlier pruning using Kåsa circle fit + chord-perp fallback.
//   3) Compute curvature observability metrics in XY (phiSpan, chord, sagitta, obsScore=sagitta/sigmaEff).
//       - If SkipIfObsTooLow=true and cuts fail, drop the track;
//         else keep the track but mark pT invalid for publishing.
//   4) Build GenFit2 Track:
//       - Seed endpoints from mean of first/last SeedEndpointK hits.
//       - Seed direction from combined end-window PCA tangents (SeedTangentK), sign-aligned to chord.
//       - Seed pT from sagitta when available (UseSagittaSeed), else SeedPTFallbackGeV; clamp to [SeedPTMinGeV, SeedPTMaxGeV].
//       - Convert mm->cm with PositionUnitScale for GenFit internal length units.
//       - Convert each SenseWireHit to WireMeasurementNew using drift distance (+error), synthesized wire endpoints from
//         wire position ± WireHalfLengthMM * wireDir(stereo,phi), with MaxDriftMM and drift-error clamps.
//   5) Fit strategy:
//       - Optional KalmanFitterRefTrack prefit (UseKFPreFit) then DAF refine (UseDAF) to resolve left/right ambiguity.
//       - Optional TryBothMomentumDirections: fit with +mom and -mom seed; keep best by goodness + chi2/ndf + FI points.
//       - NEW (catastrophic-outlier protection): PostFitOutlierRefit loop:
//           * if fit is unstable / has large localized residuals, iteratively drop up to PostFitMaxDrop worst points
//             using circle residuals computed from FITTED states (DAF-safe) and refit by rebuilding track.
//       - NEW (low-pT & MS): Optional GBL refinement stage (UseGBLRefit) after successful KF/DAF,
//           * only compiled/enabled when GenFit GBL headers are available in your build.
//   6) Acceptance/publishing:
//       - Require >= MinFittedPointsWithFI TrackPoints having AbsFitterInfo and chi2/ndf < MaxChi2Ndf.
//       - Select publish state deterministically from central window of track points (PublishStateCentralFrac),
//         extracting a DAF-safe fitted state via AbsFitterInfo::getFittedState(biased/unbiased).
//       - NEW (smoothing): If available in your GenFit build, optionally publish a smoothed state instead of a filtered state.
//         (Controlled by PreferSmoothedState; compile-time guarded).
//       - Extrapolate publish state to IP; compute perigee covariance via finite-difference Jacobian from rep-state covariance
//         (works even without getPosMomCov ABI).
//       - Add a single authoritative TrackState(AtIP) with time=pT and omega=q/pT; if obs fails or pT out of range,
//         publish InvalidPTSentinel instead.
//   7) Per-event robust pT summary:
//       - Collect valid published pT values and compute median, MAD, MADsigma (~1.4826*MAD), and truncated RMS over central fraction.
//       - Store in evtMeta JSON and print summary counters.
// Key-Properties:
//   - I/O: inputTracks, outputTracks
//   - Field/hypothesis: Bz [T], PDG
//   - Fit: UseKFPreFit, KFMaxIters, UseDAF, DAFMaxIters, FallbackToKFIfDAFFails, TryBothMomentumDirections
//   - NEW (robustness): PostFitOutlierRefit, PostFitMaxDrop, PostFitCircleResidualMM, PostFitMinKeep
//   - NEW (GBL): UseGBLRefit, GBLMaxIters, GBLOnlyIfImprovesChi2Ndf (compile-time guarded)
//   - NEW (smoothing): PreferSmoothedState (compile-time guarded)
//   - Preprocessing: SortHits, DeduplicateHits, DedupTolMM, PreFitOutlierVeto (+ Outlier* controls)
//   - Wire modeling: WireHalfLengthMM, MaxDriftMM, MaxDriftMMForHit, MinDriftErrMM, MaxDriftErrMM, WireAnglesAreDegrees, DetId/UseLabelAsDetId
//   - Seeding: SeedEndpointK, SeedTangentK, UseSagittaSeed (+ MinSagittaForSeedMM), SeedPTFallbackGeV, SeedPTMin/MaxGeV, SeedPMinGeV
//   - Observability gating: MinHitsForObs, ObsSigmaEffMM, ObsMinPhiSpanRad, ObsMinChordMM, ObsMinSagittaMM, ObsMinScore, SkipIfObsTooLow
//   - Acceptance/publishing: MinHitsPerTrack, MinMeasurementsToFit, MinFittedPointsWithFI, MaxChi2Ndf,
//       PublishStateCentralFrac, UseBiasedStateForPublish, PublishPTMaxGeV, InvalidPTSentinel
//   - Material effects: UseMaterialEffects, TGeoFile, TGeoTopVolume, DisableEnergyLoss, DisableAllMaterialEffects, HardDisableMaterialIfNoGeo
//   - Reporting: StatsTruncCentralFrac, JobTag, DiagEveryNTracks
// Physics-Notes:
//   - Intended for drift-chamber (wire) tracking where left/right drift ambiguity is best handled by DAF.
//   - Material effects (multiple scattering; optional energy loss) require a valid TGeo geometry; otherwise material effects are disabled.
//   - pT publication is intentionally “physics-clean”: no truth or SimLinks required, and no cuts on reconstructed pT vs expectation;
//     only geometric observability + fit quality cuts.
//   - TrackState.time is used as the authoritative stored pT in downstream analysis; omega retains the standard q/pT convention.
// Caveats:
//   - Requires input trackerHits to actually be extension::SenseWireHit; if GGTF is not attaching SenseWireHit relations,
//     this fitter will skip tracks.
//   - GenFit ABI variations: helper stubs exist for alternative covariance APIs; current implementation uses FD Jacobian
//     on rep-state covariance to avoid fork-specific getPosMomCov signatures.
//   - Units: positions are assumed to be in mm at I/O boundaries; GenFit internal length unit is cm via PositionUnitScale.
// Tags:
//   tracking, drift-chamber, IDEA, FCCee, key4hep, k4FWCore, Gaudi, GenFit2, DAF, Kalman, WireMeasurementNew, TGeo, material-effects, pT-resolution, robust-stats, metadata
// DOC_END




// GenFit2DCHFitter.cpp  -- DCH fit of GGTF tracks using GenFit2 WireMeasurementNew
//
// Purpose (Option A, matches your GGTF_tracking.cpp intent):
//   - Consume GGTF track candidates that already contain the *SenseWireHits*
//     attached to each extension::Track via trackerHits relation.
//   - Build GenFit measurements as *WireMeasurementNew* using:
//        * drift distance (+ error)
//        * wire direction from (stereoAngle, azimuthalAngle)
//        * a point on the wire from hit.position
//        * wire endpoints synthesized as (pos ± halfLength * dir)
//   - Resolve left/right ambiguity with DAF by default (best-practice for DCH).
//   - Export ONE authoritative TrackState(AtIP) per output track.
//     Convention kept: TrackState.omega = q/pT [GeV^-1]; TrackState.time = pT [GeV].
//
// Implemented robustness upgrades (NO TRUTH / NO SimLinks):
//   1) Publish-state choice fixed:
//        - Deterministic selection near the track "middle", avoiding edge pathologies.
//        - Does NOT hunt for a minimum of an arbitrary score over all points.
//   2) Seed direction improved using local tangents:
//        - PCA line direction from first Ktan hits and last Ktan hits.
//        - Combine tangents, sign-aligned with chord direction.
//   3) Sagitta seed made robust:
//        - Pre-fit outlier pruning (below) applied BEFORE observability/sagitta.
//        - Seed pT from sagitta uses robust sagitta (after pruning) and clamps hard.
//   4) Pre-fit geometric outlier veto (geometry-only):
//        - Deterministic iterative circle fit in XY (Kåsa) removing up to N worst hits,
//          based on radial residual threshold.
//        - Straight-track fallback: remove worst chord-perpendicular outlier if needed.
//   5) Tightened accept/reject based on quality (physics-clean):
//        - Require min FI points and chi2/ndf < MaxChi2Ndf.
//        - Never cut on reconstructed pT vs expected.
//   6) Robust "resolution metrics" reporting (summary-level, no truth needed):
//        - End-of-event robust stats over published pT values: median, MAD, and
//          truncated RMS (central fraction). Logged and optionally stashed in metadata.
//
// NEW (Catastrophic outliers / fit failures focus):
//   7) Post-fit outlier refit loop (DAF-safe; still physics-clean):
//        - If a track is "almost good" but has a localized point that blows up χ² or causes divergence,
//          we identify the worst point using CIRCLE residuals built from *fitted states* (AbsFitterInfo)
//          and rebuild+refit after removing up to PostFitMaxDrop hits.
//        - This is deterministic and does not require truth.
//   8) Optional GBL refinement (low-pT / MS):
//        - After successful KF/DAF, optionally run GBL as a final refit if available in your GenFit build.
//        - If the headers are missing in this nightly/build, the code compiles without GBL and logs once.
//   9) Publish smoothed state when available:
//        - If your GenFit build provides smoothed states via fitter info, we prefer them (optional).
//        - Helps both tails and low-pT stability when multiple scattering is significant.
//
// Notes on W vs CF comparisons:
//   - If you want W vs CF to show up in pT resolution, GenFit must actually apply
//     material effects. This file supports TGeo material effects when gGeoManager exists.
//   - You do NOT need SimLinks for this comparison; you need geometry/materials.
//
// Tested-for-ABI intent: Key4HEP nightly 2026-01-11 + local GenFit2 built
// against the same nightly.
//
// ======================================================================

#include <memory>
#include <vector>
#include <string>
#include <cmath>
#include <exception>
#include <algorithm>
#include <limits>
#include <sstream>
#include <ctime>
#include <numeric>
#include <cstdint>
#include <mutex>
#include <atomic>

// Gaudi
#include "Gaudi/Algorithm.h"
#include "Gaudi/Property.h"
#include "GaudiKernel/ISvcLocator.h"

// k4FWCore
#include "k4FWCore/Transformer.h"
#include "k4FWCore/MetaDataHandle.h"

// EDM4hep / extension
#include "edm4hep/TrackState.h"
#include "extension/TrackCollection.h"
#include "extension/TrackerHit.h"
#include "extension/SenseWireHit.h"

// ROOT / TGeo
#include "TVector3.h"
#include "TVectorD.h"
#include "TMatrixDSym.h"
#include "TMatrixD.h"
#include "TMatrixDSymEigen.h"
#include "TDecompChol.h"
#include "TDecompSVD.h"
#include "TGeoManager.h"

// GenFit2 core
#include "RKTrackRep.h"
#include "Track.h"
#include "TrackPoint.h"
#include "MeasuredStateOnPlane.h"
#include "Exception.h"
#include "FieldManager.h"
#include "ConstField.h"
#include "MaterialEffects.h"
#include "TGeoMaterialInterface.h"

// Fitters / infos
#include "KalmanFitterRefTrack.h"
#include "FitStatus.h"
#include "AbsFitterInfo.h"     // CRITICAL for DAF-safe state extraction
#include "DAF.h"

// Measurements
#include "WireMeasurementNew.h"

// -----------------------------
// Optional compile-time hooks
// -----------------------------
#if defined(__has_include)
  #if __has_include("KalmanFitterInfo.h")
    #include "KalmanFitterInfo.h"
    #define GF_HAVE_KALMAN_FITTERINFO 1
  #endif

  // ---- GBL header detection (multiple forks) ----
  // We *must* know both the header and the class name; we choose a variant
  // based on which header is found, and then instantiate the matching class.
  //
  // If your nightly uses a different header/class name, add a new block here.
  //
  #if __has_include("GBLFitter2.h")
    #include "GBLFitter2.h"
    #define GF_HAVE_GBL 1
    #define GF_GBL_VARIANT_GBLFITTER2 1
  #elif __has_include("GblFitter2.h")
    #include "GblFitter2.h"
    #define GF_HAVE_GBL 1
    #define GF_GBL_VARIANT_GBLFITTER2 2
  #elif __has_include("GBLFitter.h")
    #include "GBLFitter.h"
    #define GF_HAVE_GBL 1
    #define GF_GBL_VARIANT_GBLFITTER  3
  #elif __has_include("GblFitter.h")
    #include "GblFitter.h"
    #define GF_HAVE_GBL 1
    #define GF_GBL_VARIANT_GBLFITTER  4
  #endif
#endif

namespace {

// ---- small helpers ----
inline bool finite3(double a, double b, double c) {
  return std::isfinite(a) && std::isfinite(b) && std::isfinite(c);
}

inline TVector3 safeUnit(const TVector3& v, const TVector3& fallback) {
  const double m2 = v.Mag2();
  if (!(m2 > 0.0) || !std::isfinite(m2)) return fallback;
  return v * (1.0 / std::sqrt(m2));
}

inline double clampFinite(double x, double lo, double hi, double fallback) {
  if (!std::isfinite(x)) return fallback;
  if (x < lo) return lo;
  if (x > hi) return hi;
  return x;
}

// ----------------- covariance guards -----------------
inline void makeDiagonalFloor(TMatrixDSym& C, double eps) {
  for (int i = 0; i < C.GetNrows(); ++i) C(i, i) = std::max(C(i, i), eps);
}

inline void ensurePD_chol(TMatrixDSym& C, double floorDiag, double inflateFactor, int maxIters) {
  makeDiagonalFloor(C, floorDiag);
  for (int it = 0; it < maxIters; ++it) {
    TDecompChol chol(C);
    if (chol.Decompose()) return;
    for (int i = 0; i < C.GetNrows(); ++i) C(i, i) *= inflateFactor;
  }
  for (int i = 0; i < C.GetNrows(); ++i) C(i, i) += floorDiag;
}

inline void ensurePD_eigenClamp(TMatrixDSym& C, double minEig) {
  // symmetrize
  for (int i = 0; i < C.GetNrows(); ++i) {
    for (int j = i + 1; j < C.GetNcols(); ++j) {
      const double v = 0.5 * (C(i, j) + C(j, i));
      C(i, j) = v;
      C(j, i) = v;
    }
  }

  for (int i = 0; i < C.GetNrows(); ++i) {
    if (!std::isfinite(C(i, i))) {
      C.Zero();
      for (int k = 0; k < C.GetNrows(); ++k) C(k, k) = std::max(minEig, 1e-12);
      return;
    }
  }

  TMatrixDSymEigen eig(C);
  TVectorD eval = eig.GetEigenValues();
  TMatrixD evec = eig.GetEigenVectors();

  bool changed = false;
  for (int i = 0; i < eval.GetNrows(); ++i) {
    if (!std::isfinite(eval(i)) || eval(i) < minEig) {
      eval(i) = minEig;
      changed = true;
    }
  }
  if (!changed) return;

  TMatrixD D(C.GetNrows(), C.GetNcols());
  D.Zero();
  for (int i = 0; i < eval.GetNrows(); ++i) D(i, i) = eval(i);

  TMatrixD V(evec);
  TMatrixD tmp = V * D * TMatrixD(TMatrixD::kTransposed, V);

  for (int i = 0; i < C.GetNrows(); ++i)
    for (int j = 0; j < C.GetNcols(); ++j)
      C(i, j) = tmp(i, j);

  makeDiagonalFloor(C, minEig);
}

static int chargeFromPDG(int pdg) {
  const int a = std::abs(pdg);
  if (a == 11 || a == 13 || a == 15) return (pdg > 0 ? -1 : +1);
  if (a == 211 || a == 321 || a == 2212) return (pdg > 0 ? +1 : -1);
  return (pdg >= 0 ? +1 : -1);
}

// degrees->radians helper
constexpr double kDegToRad = M_PI / 180.0;

// ---------- PCA ordering helpers ----------
static TVector3 principalAxisFromPositionsMM(const std::vector<extension::SenseWireHit>& hw,
                                             size_t i0 = 0,
                                             size_t i1 = std::numeric_limits<size_t>::max()) {
  if (hw.size() < 3) return TVector3(0, 0, 1);
  i1 = std::min(i1, hw.size());
  if (i1 <= i0 + 2) return TVector3(0, 0, 1);

  double mx = 0, my = 0, mz = 0;
  int n = 0;
  for (size_t i = i0; i < i1; ++i) {
    const auto p = hw[i].getPosition();
    if (!finite3(p.x, p.y, p.z)) continue;
    mx += p.x; my += p.y; mz += p.z; ++n;
  }
  if (n < 3) return TVector3(0, 0, 1);
  mx /= n; my /= n; mz /= n;

  TMatrixDSym C(3); C.Zero();
  for (size_t i = i0; i < i1; ++i) {
    const auto p = hw[i].getPosition();
    if (!finite3(p.x, p.y, p.z)) continue;
    const double x = p.x - mx;
    const double y = p.y - my;
    const double z = p.z - mz;
    C(0,0) += x*x; C(0,1) += x*y; C(0,2) += x*z;
    C(1,1) += y*y; C(1,2) += y*z;
    C(2,2) += z*z;
  }
  C(1,0) = C(0,1);
  C(2,0) = C(0,2);
  C(2,1) = C(1,2);

  TMatrixDSymEigen eig(C);
  const TVectorD eval = eig.GetEigenValues();
  const TMatrixD evec = eig.GetEigenVectors(); // columns

  int imax = 0;
  if (eval(1) > eval(imax)) imax = 1;
  if (eval(2) > eval(imax)) imax = 2;

  TVector3 axis(evec(0, imax), evec(1, imax), evec(2, imax));
  if (!std::isfinite(axis.Mag2()) || axis.Mag2() < 1e-12) return TVector3(0, 0, 1);
  axis *= (1.0 / axis.Mag());

  // deterministic sign preference
  if (axis.Z() < 0) axis *= -1.0;
  else if (std::abs(axis.Z()) < 1e-6 && axis.Y() < 0) axis *= -1.0;
  else if (std::abs(axis.Z()) < 1e-6 && std::abs(axis.Y()) < 1e-6 && axis.X() < 0) axis *= -1.0;

  return axis;
}

static void sortWireHitsAlongPCA(std::vector<extension::SenseWireHit>& hw) {
  if (hw.size() < 2) return;

  double mx = 0, my = 0, mz = 0;
  int n = 0;
  for (const auto& h : hw) {
    const auto p = h.getPosition();
    if (!finite3(p.x, p.y, p.z)) continue;
    mx += p.x; my += p.y; mz += p.z; ++n;
  }
  if (n == 0) return;
  mx /= n; my /= n; mz /= n;

  const TVector3 axis = principalAxisFromPositionsMM(hw);

  std::stable_sort(hw.begin(), hw.end(), [&](const auto& a, const auto& b) {
    const auto pa = a.getPosition();
    const auto pb = b.getPosition();
    const TVector3 va(pa.x - mx, pa.y - my, pa.z - mz);
    const TVector3 vb(pb.x - mx, pb.y - my, pb.z - mz);
    const double sa = va.Dot(axis);
    const double sb = vb.Dot(axis);
    if (sa != sb) return sa < sb;

    // deterministic tie-breakers
    const double ra = std::hypot(pa.x, pa.y);
    const double rb = std::hypot(pb.x, pb.y);
    if (ra != rb) return ra < rb;
    if (pa.z != pb.z) return pa.z < pb.z;
    const double phia = std::atan2(pa.y, pa.x);
    const double phib = std::atan2(pb.y, pb.x);
    return phia < phib;
  });
}

// ---------- simple XY observability metrics ----------
struct ObsMetrics {
  double phiSpanRad = 0.0;
  double chordMM = 0.0;
  double sagittaMM = 0.0;
  double obsScore = 0.0;
  bool   ok = false;
};

static double unwrapDeltaPhi(double dphi) {
  while (dphi >  M_PI) dphi -= 2.0*M_PI;
  while (dphi < -M_PI) dphi += 2.0*M_PI;
  return dphi;
}

static ObsMetrics computeObsMetricsXY(const std::vector<extension::SenseWireHit>& hw,
                                     double sigmaEffMM,
                                     unsigned minHitsForObs) {
  ObsMetrics m;
  if (hw.size() < std::max<size_t>(3, minHitsForObs)) return m;

  std::vector<double> phi;
  phi.reserve(hw.size());

  std::vector<TVector3> pxy;
  pxy.reserve(hw.size());

  for (const auto& h : hw) {
    const auto p = h.getPosition();
    if (!finite3(p.x, p.y, p.z)) continue;
    phi.push_back(std::atan2(p.y, p.x));
    pxy.emplace_back(p.x, p.y, 0.0);
  }

  if (phi.size() < std::max<size_t>(3, minHitsForObs)) return m;

  // unwrap phi along the sequence
  double phiMin = phi[0];
  double phiMax = phi[0];
  double accum = phi[0];
  double prev = phi[0];

  for (size_t i = 1; i < phi.size(); ++i) {
    const double d = unwrapDeltaPhi(phi[i] - prev);
    accum += d;
    phiMin = std::min(phiMin, accum);
    phiMax = std::max(phiMax, accum);
    prev = prev + d;
  }
  m.phiSpanRad = std::abs(phiMax - phiMin);

  // chord in XY between endpoints
  const TVector3 A = pxy.front();
  const TVector3 B = pxy.back();
  const TVector3 AB = B - A;
  m.chordMM = std::hypot(AB.X(), AB.Y());

  // sagitta: max perpendicular distance to chord line in XY
  double smax = 0.0;
  const double denom = std::max(1e-12, m.chordMM);
  for (size_t i = 1; i + 1 < pxy.size(); ++i) {
    const TVector3 P = pxy[i];
    const double crossZ =
      std::abs((P.X()-A.X())*(B.Y()-A.Y()) - (P.Y()-A.Y())*(B.X()-A.X()));
    const double dperp = crossZ / denom;
    if (std::isfinite(dperp)) smax = std::max(smax, dperp);
  }
  m.sagittaMM = smax;

  const double sig = (std::isfinite(sigmaEffMM) && sigmaEffMM > 0.0) ? sigmaEffMM : 1.0;
  m.obsScore = smax / sig;

  m.ok = std::isfinite(m.phiSpanRad) && std::isfinite(m.chordMM) && std::isfinite(m.sagittaMM);
  return m;
}

// Count TrackPoints with any FitterInfo for cardinal rep.
static unsigned countFIPoints(genfit::Track& trk) {
  genfit::AbsTrackRep* rep = trk.getCardinalRep();
  if (!rep) return 0;
  const size_t nPts = trk.getNumPoints();
  unsigned n = 0;
  for (size_t i = 0; i < nPts; ++i) {
    const auto* tp = trk.getPoint(i);
    if (tp && tp->hasFitterInfo(rep)) ++n;
  }
  return n;
}

// Robust stats: median, MAD (median absolute deviation), truncated RMS.
struct RobustStats {
  double median = std::numeric_limits<double>::quiet_NaN();
  double mad = std::numeric_limits<double>::quiet_NaN();          // unscaled
  double madSigma = std::numeric_limits<double>::quiet_NaN();     // ~1.4826 * MAD for normal
  double trRms = std::numeric_limits<double>::quiet_NaN();        // truncated RMS (central fraction)
  size_t n = 0;
};

static double medianInPlace(std::vector<double>& v) {
  if (v.empty()) return std::numeric_limits<double>::quiet_NaN();
  const size_t n = v.size();
  const size_t mid = n / 2;
  std::nth_element(v.begin(), v.begin() + mid, v.end());
  double m = v[mid];
  if (n % 2 == 0) {
    std::nth_element(v.begin(), v.begin() + (mid - 1), v.end());
    m = 0.5 * (m + v[mid - 1]);
  }
  return m;
}

static RobustStats robustStats(const std::vector<double>& xin, double truncCentralFrac = 0.95) {
  RobustStats s;
  std::vector<double> x;
  x.reserve(xin.size());
  for (double v : xin) if (std::isfinite(v)) x.push_back(v);
  s.n = x.size();
  if (x.empty()) return s;

  s.median = medianInPlace(x);

  // MAD
  std::vector<double> absdev;
  absdev.reserve(x.size());
  for (double v : x) absdev.push_back(std::abs(v - s.median));
  s.mad = medianInPlace(absdev);
  s.madSigma = 1.4826 * s.mad;

  // truncated RMS around median: keep central frac by |x-median|
  if (truncCentralFrac > 0.0 && truncCentralFrac <= 1.0) {
    std::vector<double> dist;
    dist.reserve(x.size());
    for (double v : x) dist.push_back(std::abs(v - s.median));
    const size_t keepN = std::max<size_t>(1, size_t(std::floor(truncCentralFrac * double(dist.size()))));
    std::nth_element(dist.begin(), dist.begin() + (keepN - 1), dist.end());
    const double thr = dist[keepN - 1];

    double sum2 = 0.0;
    size_t nk = 0;
    for (double v : x) {
      const double d = std::abs(v - s.median);
      if (d <= thr) {
        const double dv = v - s.median;
        sum2 += dv * dv;
        ++nk;
      }
    }
    if (nk > 0) s.trRms = std::sqrt(sum2 / double(nk));
  }

  return s;
}

// ----------------------------------------------------------------------
// Pre-fit geometry-only outlier pruning in XY.
// ----------------------------------------------------------------------

struct CircleFitXY {
  bool ok = false;
  double xc = 0, yc = 0, R = 0;
};

static CircleFitXY fitCircleKasaXY_fromXY(const std::vector<TVector3>& pxy_mm) {
  CircleFitXY res;
  if (pxy_mm.size() < 3) return res;

  // Build normal equations for [A,B,C]:
  // A x + B y + C = -(x^2 + y^2)
  double Sxx=0,Sxy=0,Sx=0,Syy=0,Sy=0,S1=0;
  double Tx=0,Ty=0,T1=0;

  size_t n=0;
  for (const auto& P : pxy_mm) {
    const double x = P.X();
    const double y = P.Y();
    if (!std::isfinite(x) || !std::isfinite(y)) continue;
    const double z = -(x*x + y*y);
    Sxx += x*x;
    Sxy += x*y;
    Sx  += x;
    Syy += y*y;
    Sy  += y;
    S1  += 1.0;

    Tx  += x*z;
    Ty  += y*z;
    T1  += z;
    ++n;
  }
  if (n < 3) return res;

  TMatrixD M(3,3);
  M(0,0)=Sxx; M(0,1)=Sxy; M(0,2)=Sx;
  M(1,0)=Sxy; M(1,1)=Syy; M(1,2)=Sy;
  M(2,0)=Sx;  M(2,1)=Sy;  M(2,2)=S1;

  TVectorD rhs(3);
  rhs(0)=Tx; rhs(1)=Ty; rhs(2)=T1;

  const double det = M.Determinant();
  if (!std::isfinite(det) || std::abs(det) < 1e-12) return res;

  TDecompSVD svd(M);
  Bool_t ok = kFALSE;
  TVectorD sol = svd.Solve(rhs, ok);
  if (!ok) return res;

  const double A = sol(0);
  const double B = sol(1);
  const double C = sol(2);

  const double xc = -A/2.0;
  const double yc = -B/2.0;
  const double rad2 = (A*A + B*B)/4.0 - C;
  if (!std::isfinite(rad2) || rad2 <= 0.0) return res;

  res.ok = true;
  res.xc = xc;
  res.yc = yc;
  res.R  = std::sqrt(rad2);
  return res;
}

static CircleFitXY fitCircleKasaXY(const std::vector<extension::SenseWireHit>& hw) {
  std::vector<TVector3> pxy;
  pxy.reserve(hw.size());
  for (const auto& h : hw) {
    const auto p = h.getPosition();
    if (!finite3(p.x,p.y,p.z)) continue;
    pxy.emplace_back(p.x, p.y, 0.0);
  }
  return fitCircleKasaXY_fromXY(pxy);
}

static double chordPerpDistMM(const TVector3& A, const TVector3& B, const TVector3& P) {
  const double dx = B.X() - A.X();
  const double dy = B.Y() - A.Y();
  const double denom = std::max(1e-12, std::hypot(dx,dy));
  const double cross = std::abs((P.X()-A.X())*dy - (P.Y()-A.Y())*dx);
  return cross / denom;
}

static unsigned pruneOutliersXY(std::vector<extension::SenseWireHit>& hw,
                               unsigned maxDrop,
                               double circleResMM,
                               double chordResMM,
                               unsigned minKeep = 8) {
  if (maxDrop == 0 || hw.size() <= minKeep) return 0;
  unsigned dropped = 0;

  auto eraseIndex = [&](size_t idx) {
    hw.erase(hw.begin() + idx);
  };

  // --- circle-fit based pruning ---
  for (unsigned it = 0; it < maxDrop; ++it) {
    if (hw.size() <= minKeep) break;
    CircleFitXY cf = fitCircleKasaXY(hw);
    if (!cf.ok) break;

    double worst = -1.0;
    size_t worstIdx = 0;
    for (size_t i = 0; i < hw.size(); ++i) {
      const auto p = hw[i].getPosition();
      if (!finite3(p.x,p.y,p.z)) continue;
      const double r = std::hypot(p.x - cf.xc, p.y - cf.yc);
      const double resi = std::abs(r - cf.R);
      if (!std::isfinite(resi)) continue;
      if (resi > worst) { worst = resi; worstIdx = i; }
    }

    if (!(worst > circleResMM)) break;
    eraseIndex(worstIdx);
    ++dropped;
  }

  if (dropped > 0) return dropped;

  // --- fallback: chord-perp pruning for near-straight / ill-conditioned circle ---
  for (unsigned it = 0; it < maxDrop; ++it) {
    if (hw.size() <= minKeep) break;
    const auto pA = hw.front().getPosition();
    const auto pB = hw.back().getPosition();
    if (!finite3(pA.x,pA.y,pA.z) || !finite3(pB.x,pB.y,pB.z)) break;

    const TVector3 A(pA.x,pA.y,0.0);
    const TVector3 B(pB.x,pB.y,0.0);

    double worst = -1.0;
    size_t worstIdx = 0;
    for (size_t i = 1; i + 1 < hw.size(); ++i) {
      const auto p = hw[i].getPosition();
      if (!finite3(p.x,p.y,p.z)) continue;
      const TVector3 P(p.x,p.y,0.0);
      const double d = chordPerpDistMM(A,B,P);
      if (!std::isfinite(d)) continue;
      if (d > worst) { worst = d; worstIdx = i; }
    }

    if (!(worst > chordResMM)) break;
    eraseIndex(worstIdx);
    ++dropped;
  }

  return dropped;
}

// ----------------------------------------------------------------------
// Post-fit outlier discovery using FITTED states (DAF-safe).
// NOTE: positions returned by MeasuredStateOnPlane::getPos() are in GenFit internal length units.
// ----------------------------------------------------------------------
struct PostFitWorstPoint {
  bool ok = false;
  size_t idxPoint = 0;   // TrackPoint index (maps to insertion order here)
  double residInternal = 0.0;  // |r-R| in internal length units (typically cm)
};

static PostFitWorstPoint findWorstPointByFittedCircleResidual(const genfit::Track& gftrk,
                                                             bool useBiased,
                                                             bool preferSmoothedIfAvail) {
  PostFitWorstPoint out;
  genfit::AbsTrackRep* rep = gftrk.getCardinalRep();
  if (!rep) return out;

  const size_t nPts = gftrk.getNumPoints();
  if (nPts < 6) return out;

  std::vector<TVector3> pxy;
  pxy.reserve(nPts);
  std::vector<size_t> idxMap;
  idxMap.reserve(nPts);

  for (size_t i = 0; i < nPts; ++i) {
    const genfit::TrackPoint* tp = gftrk.getPoint(i);
    if (!tp || !tp->hasFitterInfo(rep)) continue;
    const genfit::AbsFitterInfo* fi = tp->getFitterInfo(rep);
    if (!fi) continue;

    try {
      genfit::MeasuredStateOnPlane st = fi->getFittedState(useBiased);

#if defined(GF_HAVE_KALMAN_FITTERINFO)
      if (preferSmoothedIfAvail) {
        if (const auto* kfi = dynamic_cast<const genfit::KalmanFitterInfo*>(fi)) {
          try { st = kfi->getSmoothedState(); } catch (...) {}
        }
      }
#else
      (void)preferSmoothedIfAvail;
#endif

      const TVector3 pos = st.getPos();
      if (!std::isfinite(pos.X()) || !std::isfinite(pos.Y())) continue;

      pxy.emplace_back(pos.X(), pos.Y(), 0.0);
      idxMap.push_back(i);
    } catch (...) {
      continue;
    }
  }

  if (pxy.size() < 6) return out;

  CircleFitXY cf = fitCircleKasaXY_fromXY(pxy);
  if (!cf.ok) return out;

  double worst = -1.0;
  size_t worstLocal = 0;
  for (size_t j = 0; j < pxy.size(); ++j) {
    const double x = pxy[j].X();
    const double y = pxy[j].Y();
    const double r = std::hypot(x - cf.xc, y - cf.yc);
    const double resi = std::abs(r - cf.R);
    if (!std::isfinite(resi)) continue;
    if (resi > worst) { worst = resi; worstLocal = j; }
  }
  if (!(worst > 0.0)) return out;

  out.ok = true;
  out.idxPoint = idxMap[worstLocal];
  out.residInternal = worst;
  return out;
}

// ----------------------------------------------------------------------
// Publish-state selection (DAF-safe, robust).
// ----------------------------------------------------------------------
static bool selectPublishStateCentral(const genfit::Track& gftrk,
                                     bool useBiasedState,
                                     double centralFrac,        // e.g. 0.6 => keep middle 60%
                                     bool preferSmoothedIfAvail,
                                     genfit::MeasuredStateOnPlane& outState,
                                     size_t& outIdx) {
  genfit::AbsTrackRep* rep = gftrk.getCardinalRep();
  if (!rep) return false;
  const size_t nPts = gftrk.getNumPoints();
  if (nPts == 0) return false;

  centralFrac = std::clamp(centralFrac, 0.0, 1.0);
  const double mid = 0.5 * double(nPts - 1);
  const double halfWin = 0.5 * centralFrac * double(nPts);
  const double lo = std::max(0.0, mid - halfWin);
  const double hi = std::min(double(nPts - 1), mid + halfWin);

  bool have = false;
  double bestKey1 = 0.0; // |i-mid|
  double bestKey2 = 0.0; // r
  size_t bestI = 0;
  genfit::MeasuredStateOnPlane bestSt;

  for (size_t i = 0; i < nPts; ++i) {
    if (double(i) < lo || double(i) > hi) continue;
    const genfit::TrackPoint* tp = gftrk.getPoint(i);
    if (!tp || !tp->hasFitterInfo(rep)) continue;

    const genfit::AbsFitterInfo* fi = tp->getFitterInfo(rep);
    if (!fi) continue;

    try {
      genfit::MeasuredStateOnPlane st = fi->getFittedState(useBiasedState);

#if defined(GF_HAVE_KALMAN_FITTERINFO)
      if (preferSmoothedIfAvail) {
        if (const auto* kfi = dynamic_cast<const genfit::KalmanFitterInfo*>(fi)) {
          try { st = kfi->getSmoothedState(); } catch (...) {}
        }
      }
#else
      (void)preferSmoothedIfAvail;
#endif

      const TVector3 pos = st.getPos();
      const double r = std::hypot(pos.X(), pos.Y());
      if (!std::isfinite(r)) continue;

      const double key1 = std::abs(double(i) - mid);
      const double key2 = r;

      if (!have || key1 < bestKey1 || (key1 == bestKey1 && key2 < bestKey2)) {
        have = true;
        bestKey1 = key1;
        bestKey2 = key2;
        bestI = i;
        bestSt = st;
      }
    } catch (...) {
      continue;
    }
  }

  if (!have) {
    // As last resort, fall back to ANY point with fitter info (still deterministic).
    for (size_t i = 0; i < nPts; ++i) {
      const genfit::TrackPoint* tp = gftrk.getPoint(i);
      if (!tp || !tp->hasFitterInfo(rep)) continue;
      const genfit::AbsFitterInfo* fi = tp->getFitterInfo(rep);
      if (!fi) continue;
      try {
        genfit::MeasuredStateOnPlane st = fi->getFittedState(useBiasedState);
#if defined(GF_HAVE_KALMAN_FITTERINFO)
        if (preferSmoothedIfAvail) {
          if (const auto* kfi = dynamic_cast<const genfit::KalmanFitterInfo*>(fi)) {
            try { st = kfi->getSmoothedState(); } catch (...) {}
          }
        }
#endif
        outState = st;
        outIdx = i;
        return true;
      } catch (...) {}
    }
    return false;
  }

  outState = bestSt;
  outIdx = bestI;
  return true;
}

// ----------------------------------------------------------------------
// Perigee params (EDM4hep-style) from (pos,mom) + numerical Jacobian for cov.
// ----------------------------------------------------------------------

static void perigeeFromPosMom(const TVector3& pos_mm,
                             const TVector3& mom_GeV,
                             int q,
                             TVectorD& a5 /*size 5*/) {
  const double x = pos_mm.X();
  const double y = pos_mm.Y();
  const double z = pos_mm.Z();

  const double px = mom_GeV.X();
  const double py = mom_GeV.Y();
  const double pz = mom_GeV.Z();

  const double pT  = std::hypot(px, py);
  const double phi = std::atan2(py, px);
  const double tanL = (pT > 1e-12) ? (pz / pT) : 0.0;
  const double omega = (pT > 1e-12) ? (double(q) / pT) : std::numeric_limits<double>::quiet_NaN();

  const double d0 = - (x * std::sin(phi) - y * std::cos(phi));
  const double z0 =   z - (x * std::cos(phi) + y * std::sin(phi)) * tanL;

  a5.ResizeTo(5);
  a5(0) = d0;
  a5(1) = phi;
  a5(2) = omega;
  a5(3) = z0;
  a5(4) = tanL;
}

static bool covPerigeeFromRepStateFD(genfit::AbsTrackRep* rep,
                                    const genfit::MeasuredStateOnPlane& stIP,
                                    int q,
                                    double posScale_cm_per_mm,
                                    TMatrixDSym& cov5_out) {
  (void)rep;

  const TVectorD s0 = stIP.getState();
  const TMatrixDSym C0 = stIP.getCov();

  const int n = int(s0.GetNrows());
  if (n <= 0) return false;
  if (C0.GetNrows() != n) return false;

  const double inv_ps = (posScale_cm_per_mm > 0 ? 1.0 / posScale_cm_per_mm : 10.0);
  const TVector3 pos0_mm(stIP.getPos().X() * inv_ps,
                         stIP.getPos().Y() * inv_ps,
                         stIP.getPos().Z() * inv_ps);
  const TVector3 mom0 = stIP.getMom();

  TVectorD a0(5);
  perigeeFromPosMom(pos0_mm, mom0, q, a0);
  for (int i = 0; i < 5; ++i) if (!std::isfinite(a0(i))) return false;

  TMatrixD J(5, n);
  J.Zero();

  auto stepFor = [&](int k) -> double {
    const double x = s0(k);
    const double rel = 1e-5;
    const double abs0 = 1e-6;
    return std::max(abs0, rel * std::max(1.0, std::abs(x)));
  };

  for (int k = 0; k < n; ++k) {
    const double d = stepFor(k);

    genfit::MeasuredStateOnPlane stP = stIP;
    genfit::MeasuredStateOnPlane stM = stIP;

    TVectorD sP = s0; sP(k) += d;
    TVectorD sM = s0; sM(k) -= d;

    stP.setState(sP);
    stM.setState(sM);

    const TVector3 posP_mm(stP.getPos().X() * inv_ps,
                           stP.getPos().Y() * inv_ps,
                           stP.getPos().Z() * inv_ps);
    const TVector3 momP = stP.getMom();

    const TVector3 posM_mm(stM.getPos().X() * inv_ps,
                           stM.getPos().Y() * inv_ps,
                           stM.getPos().Z() * inv_ps);
    const TVector3 momM = stM.getMom();

    TVectorD aP(5), aM(5);
    perigeeFromPosMom(posP_mm, momP, q, aP);
    perigeeFromPosMom(posM_mm, momM, q, aM);

    for (int i = 0; i < 5; ++i) {
      if (!std::isfinite(aP(i)) || !std::isfinite(aM(i))) return false;

      double num = aP(i) - aM(i);
      if (i == 1) num = unwrapDeltaPhi(num);

      J(i, k) = num / (2.0 * d);
      if (!std::isfinite(J(i, k))) return false;
    }
  }

  TMatrixD C0d(C0);
  TMatrixD tmp = J * C0d * TMatrixD(TMatrixD::kTransposed, J);

  cov5_out.ResizeTo(5, 5);
  for (int i = 0; i < 5; ++i) {
    for (int j = 0; j < 5; ++j) cov5_out(i, j) = tmp(i, j);
  }

  for (int i = 0; i < 5; ++i) {
    for (int j = i + 1; j < 5; ++j) {
      const double v = 0.5 * (cov5_out(i, j) + cov5_out(j, i));
      cov5_out(i, j) = v;
      cov5_out(j, i) = v;
    }
  }
  ensurePD_eigenClamp(cov5_out, 1e-12);
  return true;
}

// Fill TrackState(AtIP). pos_internal is in internal length units (cm).
static void addAtIPState(extension::MutableTrack& trk,
                         const TVector3& pos_internal_cm,
                         const TVector3& mom_GeV,
                         double posScale_cm_per_mm,
                         int chargeSign,
                         bool ptValid,
                         float invalidPTSentinel,
                         float omegaVar,
                         float obsScore,
                         float extra0 = -1.f,
                         float extra1 = -1.f,
                         const TMatrixDSym* cov5 = nullptr) {

  using TP = edm4hep::TrackParams;

  const double inv_ps = (posScale_cm_per_mm > 0 ? 1.0 / posScale_cm_per_mm : 10.0);
  const double x = pos_internal_cm.X() * inv_ps;
  const double y = pos_internal_cm.Y() * inv_ps;
  const double z = pos_internal_cm.Z() * inv_ps;

  const double px = mom_GeV.X();
  const double py = mom_GeV.Y();
  const double pz = mom_GeV.Z();

  const double pT = std::hypot(px, py);
  const double phi = std::atan2(py, px);
  const double tanL = (pT > 1e-12) ? (pz / pT) : 0.0;

  const double omegaSigned =
      (ptValid && std::isfinite(pT) && pT > 1e-12) ? (double(chargeSign) / pT)
                                                   : std::numeric_limits<double>::quiet_NaN();

  const double d0 = - (x * std::sin(phi) - y * std::cos(phi));
  const double z0 =   z - (x * std::cos(phi) + y * std::sin(phi)) * tanL;

  edm4hep::TrackState ts;
  ts.location       = edm4hep::TrackState::AtIP;
  ts.referencePoint = { float(x), float(y), float(z) };
  ts.phi            = float(phi);
  ts.omega          = float(omegaSigned);
  ts.tanLambda      = float(tanL);
  ts.D0             = float(d0);
  ts.Z0             = float(z0);

  if (ptValid) ts.time = float(pT);
  else         ts.time = invalidPTSentinel;

  if (cov5 && cov5->GetNrows() == 5) {
    const edm4hep::TrackParams idx[5] = {TP::d0, TP::phi, TP::omega, TP::z0, TP::tanLambda};
    for (int i=0;i<5;++i) {
      for (int j=i;j<5;++j) {
        const double v = (*cov5)(i,j);
        if (std::isfinite(v)) ts.setCovMatrix(float(v), idx[i], idx[j]);
      }
    }
  } else {
    ts.setCovMatrix(std::isfinite(extra0) ? extra0 : 1.0f, TP::d0,       TP::d0);
    ts.setCovMatrix(1e-3f,                                TP::phi,      TP::phi);
    ts.setCovMatrix(omegaVar,                             TP::omega,    TP::omega);
    ts.setCovMatrix(std::isfinite(extra1) ? extra1 : 1.0f, TP::z0,      TP::z0);
    ts.setCovMatrix(std::isfinite(obsScore) ? obsScore : -1.0f, TP::tanLambda, TP::tanLambda);
  }

  trk.addToTrackStates(ts);
}

} // end anonymous namespace

// ======================================================================

struct GenFit2DCHFitter final
  : k4FWCore::Transformer<extension::TrackCollection (const extension::TrackCollection&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  GenFit2DCHFitter(const std::string& name, ISvcLocator* svcLoc)
    : Transformer(name, svcLoc,
        std::tuple<KeyValues>{
          KeyValues{"inputTracks", std::vector<std::string>{"OutputTracksGGTF"}}
        },
        std::tuple<KeyValues>{
          KeyValues{"outputTracks", std::vector<std::string>{"GenFitTracks"}}
        }),
      m_cfgMeta("cfgMeta", Gaudi::DataHandle::Writer),
      m_evtMeta("evtMeta", Gaudi::DataHandle::Writer) {}

  // ----------------- Properties -----------------

  Gaudi::Property<bool> m_rejectNegativeLabels{
    this,"RejectNegativeLabels", true,
    "Skip GGTF tracks with track.type < 0 (debug labels)."
  };

  Gaudi::Property<unsigned> m_minHitsPerTrack{
    this,"MinHitsPerTrack", 8u,
    "Minimum SenseWireHits per GGTF track to attempt fit (after pruning/dedup)."
  };

  Gaudi::Property<unsigned> m_minMeasurementsToFit{
    this, "MinMeasurementsToFit", 6u,
    "Minimum WireMeasurementNew inserted into GenFit track to attempt fit."
  };

  Gaudi::Property<unsigned> m_minFittedPointsWithFI{
    this, "MinFittedPointsWithFI", 10u,
    "Minimum number of TrackPoints with FitterInfo before accepting/publishing."
  };

  Gaudi::Property<bool> m_sortHits{
    this,"SortHits", true,
    "Sort SenseWireHits along PCA axis computed from on-wire positions."
  };

  Gaudi::Property<bool> m_dedupHits{
    this,"DeduplicateHits", true,
    "Drop nearly-identical on-wire positions."
  };

  Gaudi::Property<double> m_dedupTolMM{
    this,"DedupTolMM", 0.05,
    "Dedup tolerance on on-wire XYZ distance (mm)."
  };

  Gaudi::Property<bool> m_prefitOutlierVeto{
    this, "PreFitOutlierVeto", true,
    "Deterministic pre-fit outlier veto (circle-fit in XY + chord fallback)."
  };

  Gaudi::Property<unsigned> m_outlierMaxDrop{
    this, "OutlierMaxDrop", 2u,
    "Max number of hits to drop in pre-fit outlier veto."
  };

  Gaudi::Property<double> m_outlierCircleResMM{
    this, "OutlierCircleResidualMM", 8.0,
    "Drop worst hit if |r-R| exceeds this in circle-fit pruning (mm)."
  };

  Gaudi::Property<double> m_outlierChordResMM{
    this, "OutlierChordResidualMM", 20.0,
    "Fallback drop worst hit if chord-perp distance exceeds this (mm)."
  };

  Gaudi::Property<unsigned> m_outlierMinKeep{
    this, "OutlierMinKeep", 10u,
    "Never prune below this number of hits."
  };

  Gaudi::Property<bool> m_postFitOutlierRefit{
    this, "PostFitOutlierRefit", true,
    "If a fit is borderline / unstable: iteratively remove worst point by fitted-circle residual and refit."
  };

  Gaudi::Property<unsigned> m_postFitMaxDrop{
    this, "PostFitMaxDrop", 2u,
    "Max points to drop in post-fit outlier refit loop."
  };

  Gaudi::Property<double> m_postFitCircleResidualInternal{
    this, "PostFitCircleResidualInternal", 0.25,
    "Threshold for |r-R| in fitted-state coordinates (GenFit internal length units; typically cm)."
  };

  Gaudi::Property<unsigned> m_postFitMinKeep{
    this, "PostFitMinKeep", 10u,
    "Never post-fit prune below this many hits."
  };

  Gaudi::Property<bool> m_preferSmoothedState{
    this, "PreferSmoothedState", true,
    "If supported in your GenFit build, prefer a smoothed state for publishing and post-fit diagnostics."
  };

  Gaudi::Property<unsigned> m_seedEndpointK{
    this, "SeedEndpointK", 6u,
    "Mean of first/last K hits (after sorting/pruning) used as seed endpoints."
  };

  Gaudi::Property<unsigned> m_seedTangentK{
    this, "SeedTangentK", 10u,
    "Window size for tangent estimation at each end (PCA direction over first/last K hits)."
  };

  Gaudi::Property<bool> m_useKFPreFit{
    this, "UseKFPreFit", true,
    "If true: run KalmanFitterRefTrack first as a prefit, then run DAF (if enabled)."
  };

  Gaudi::Property<bool> m_useDAF{
    this,"UseDAF", true,
    "If true: run DAF after prefit (recommended for wire left/right ambiguity)."
  };

  Gaudi::Property<bool> m_fallbackToKFIfDAFFails{
    this, "FallbackToKFIfDAFFails", true,
    "If true and UseDAF=true: if DAF throws/fails, keep KF result (if good)."
  };

  Gaudi::Property<unsigned> m_kfMaxIterations{
    this,"KFMaxIters", 12u, "KF max iterations."
  };

  Gaudi::Property<unsigned> m_dafMaxIterations{
    this,"DAFMaxIters", 8u, "DAF max iterations."
  };

  Gaudi::Property<bool> m_tryBothMomDirs{
    this, "TryBothMomentumDirections", true,
    "Try mom0 and -mom0; keep best fit."
  };

  // ----------------- GBL (real implementation) -----------------
  Gaudi::Property<bool> m_useGBLRefit{
    this, "UseGBLRefit", true,
    "If GBL fitter exists in this GenFit build: run GBL as final refit after KF/DAF."
  };

  Gaudi::Property<unsigned> m_gblMaxIters{
    this, "GBLMaxIters", 6u,
    "GBL max iterations (if available)."
  };

  Gaudi::Property<bool> m_gblOnlyIfImprovesChi2Ndf{
    this, "GBLOnlyIfImprovesChi2Ndf", true,
    "If true: accept GBL only if it improves chi2/ndf (and keeps FI points)."
  };

  // Field / hypothesis
  Gaudi::Property<double> m_Bz {this, "Bz", 2.0, "Bz field [T]"};
  Gaudi::Property<int>    m_pdg{this, "PDG", 13,  "PDG hypothesis."};

  Gaudi::Property<bool> m_useBiasedStateForPublish{
    this, "UseBiasedStateForPublish", true,
    "Use AbsFitterInfo::getFittedState(biased=true) for publishing. If false, use unbiased."
  };

  Gaudi::Property<double> m_publishStateCentralFrac{
    this, "PublishStateCentralFrac", 0.60,
    "Fraction of track points (by index) to consider around the middle for publish-state selection."
  };

  // Material effects
  Gaudi::Property<bool> m_useMatEff{this, "UseMaterialEffects", true,
                                    "Use TGeoMaterialInterface for GenFit MaterialEffects"};

  Gaudi::Property<std::string> m_tgeoFile{
    this, "TGeoFile", "",
    "Optional ROOT geometry file to import if gGeoManager is null (e.g. detector.root)."
  };
  Gaudi::Property<std::string> m_tgeoTopVolume{
    this, "TGeoTopVolume", "",
    "Optional: if importing, set a specific top volume name (usually leave empty)."
  };

  Gaudi::Property<bool> m_disableEloss{this, "DisableEnergyLoss", true,
                                       "Disable energy loss (keep MS) when material effects enabled"};
  Gaudi::Property<bool> m_disableAllMat{this, "DisableAllMaterialEffects", false,
                                        "Disable all GenFit material effects"};
  Gaudi::Property<bool> m_hardDisableMatIfNoGeo{
    this, "HardDisableMaterialIfNoGeo", true,
    "If true and gGeoManager is null: force MaterialEffects::setNoEffects(true)."
  };

  // Units / scales
  Gaudi::Property<double> m_posScale{this, "PositionUnitScale", 0.1,
                                     "Multiply positions (0.1: mm->cm) for GenFit internal units."};

  // Wire endpoint synthesis
  Gaudi::Property<double> m_wireHalfLengthMM{
    this,"WireHalfLengthMM", 2250.0,
    "Half wire length used to synthesize endpoints (mm)."
  };

  // DCH drift model inputs
  Gaudi::Property<double> m_maxDriftMM{
    this,"MaxDriftMM", 30.0,
    "Max drift distance (mm) used for WireMeasurementNew setMaxDistance."
  };

  Gaudi::Property<double> m_maxDriftMMForHit{
    this,"MaxDriftMMForHit", 35.0,
    "Hard hit-level cut: drop hits with |drift| > this (mm). (Should be >= MaxDriftMM)."
  };

  Gaudi::Property<double> m_minDriftErrMM{
    this,"MinDriftErrMM", 0.10,
    "Floor for drift distance error (mm)."
  };

  Gaudi::Property<double> m_maxDriftErrMM{
    this,"MaxDriftErrMM", 5.0,
    "Ceiling for drift distance error (mm). Hits above are clamped (not dropped)."
  };

  Gaudi::Property<double> m_minCovEigenvalue{
    this,"MinCovEigenvalue", 1e-8,
    "Minimum eigenvalue for PD-guarding covariance matrices."
  };

  Gaudi::Property<double> m_seedPosSigmaMM  {this, "SeedPosSigmaMM", 80.0, "Seed pos sigma [mm]"};
  Gaudi::Property<double> m_seedMomSigmaGeV {this, "SeedMomSigmaGeV", 5.0,  "Seed mom sigma [GeV]"};

  Gaudi::Property<double> m_seedPTFallbackGeV{
    this, "SeedPTFallbackGeV", 50.0,
    "Fallback seed pT when curvature is unobservable (GeV)."
  };

  Gaudi::Property<double> m_seedPTMinGeV    {this, "SeedPTMinGeV", 0.20, "Min seed pT [GeV]"};
  Gaudi::Property<double> m_seedPTMaxGeV    {this, "SeedPTMaxGeV", 200.0, "Max seed pT [GeV]"};
  Gaudi::Property<double> m_seedPMinGeV     {this, "SeedPMinGeV",  0.05, "Min |p| [GeV] floor"};

  // Observability / straightness gating
  Gaudi::Property<unsigned> m_minHitsForObs{
    this, "MinHitsForObs", 10u,
    "Minimum hits to compute observability metrics (phiSpan/chord/sagitta)."
  };

  Gaudi::Property<double> m_obsSigmaEffMM{
    this, "ObsSigmaEffMM", 0.25,
    "Effective transverse sigma (mm) used to convert sagitta->dimensionless obsScore."
  };

  Gaudi::Property<double> m_obsMinPhiSpanRad{
    this, "ObsMinPhiSpanRad", 0.06,
    "Require phi-span >= this for curvature observability (rad)."
  };

  Gaudi::Property<double> m_obsMinChordMM{
    this, "ObsMinChordMM", 200.0,
    "Require chord length >= this for observability (mm)."
  };

  Gaudi::Property<double> m_obsMinSagittaMM{
    this, "ObsMinSagittaMM", 0.15,
    "Require sagitta >= this for observability (mm)."
  };

  Gaudi::Property<double> m_obsMinScore{
    this, "ObsMinScore", 1.0,
    "Require obsScore = sagitta/sigmaEff >= this for publishing pT (dimensionless)."
  };

  Gaudi::Property<bool> m_skipIfObsTooLow{
    this, "SkipIfObsTooLow", false,
    "If true: drop tracks that fail observability cuts. If false: keep track but publish invalid pT."
  };

  // Sagitta-based seed
  Gaudi::Property<bool> m_useSagittaSeed{
    this, "UseSagittaSeed", true,
    "If true: compute a sagitta-based pT seed when sagitta is measurable."
  };

  Gaudi::Property<double> m_minSagittaForSeedMM{
    this, "MinSagittaForSeedMM", 0.20,
    "Only use sagitta-based pT seed if sagitta >= this (mm)."
  };

  // Fit-quality / acceptance
  Gaudi::Property<double> m_maxChi2Ndf{
    this, "MaxChi2Ndf", 20.0,
    "Hard cut on chi2/ndf for accepting/publishing a track."
  };

  Gaudi::Property<double> m_publishPTMaxGeV{
    this,"PublishPTMaxGeV", 300.0,
    "Hard maximum pT to publish in TrackState.time. Above: invalid."
  };

  Gaudi::Property<float> m_invalidPTSentinel{
    this, "InvalidPTSentinel", -1.0f,
    "TrackState.time when pT is not published."
  };

  Gaudi::Property<float> m_omegaVarGood{
    this, "OmegaVarGood", 1e-4f,
    "(GeV^-1)^2 covariance for omega when pT valid."
  };

  Gaudi::Property<float> m_omegaVarBad{
    this, "OmegaVarBad", 1.0f,
    "(GeV^-1)^2 covariance for omega when pT invalid."
  };

  Gaudi::Property<double> m_statsTruncCentralFrac{
    this, "StatsTruncCentralFrac", 0.95,
    "Central fraction for truncated RMS over published pT values (robust metric)."
  };

  // detId policy
  Gaudi::Property<int> m_detId{
    this, "DetId", 0,
    "detId passed to WireMeasurementNew (recommended constant)."
  };

  Gaudi::Property<bool> m_useLabelAsDetId{
    this, "UseLabelAsDetId", false,
    "If true: use GGTF input track label as detId (not recommended)."
  };

  // angle convention
  Gaudi::Property<bool> m_wireAnglesAreDegrees{
    this, "WireAnglesAreDegrees", false,
    "If true: interpret SenseWireHit angles in degrees and convert to radians."
  };

  // Optional job tag
  Gaudi::Property<std::string> m_jobTag{
    this, "JobTag", "",
    "Optional job tag string recorded in metadata."
  };

  // diagnostics
  Gaudi::Property<unsigned> m_diagEveryNTracks{
    this, "DiagEveryNTracks", 1u,
    "Print DEBUG diagnostics every N tracks when OutputLevel<=DEBUG."
  };

  // ----------------- lifecycle -----------------

  StatusCode initialize() override {
    genfit::FieldManager::getInstance()->init(
      new genfit::ConstField(0., 0., 10.0*m_Bz.value()));

    (void)ensureGeometryLoaded();

    std::call_once(m_matOnce, [&]() {
      auto* me = genfit::MaterialEffects::getInstance();

      const bool wantMat = bool(m_useMatEff.value());
      const bool hardOff = bool(m_disableAllMat.value());
      const bool haveGeo = (gGeoManager != nullptr);

      if (!wantMat || hardOff) {
        me->setNoEffects(true);
        info() << "MaterialEffects: DISABLED (UseMaterialEffects=false or DisableAllMaterialEffects=true)" << endmsg;
        return;
      }

      if (!haveGeo) {
        if (m_hardDisableMatIfNoGeo.value()) {
          me->setNoEffects(true);
          warning() << "MaterialEffects requested but gGeoManager==null; HARD disabling material effects." << endmsg;
        } else {
          warning() << "MaterialEffects requested but gGeoManager==null; leaving MaterialEffects as-is (may throw later)." << endmsg;
        }
        return;
      }

      try {
        me->init(new genfit::TGeoMaterialInterface());
        me->setNoEffects(false);
        info() << "MaterialEffects: ENABLED with TGeoMaterialInterface (gGeoManager present)." << endmsg;

        if (m_disableEloss.value()) {
          me->setEnergyLossBetheBloch(false);
          me->setNoiseBetheBloch(false);
          me->setEnergyLossBrems(false);
          me->setNoiseBrems(false);
          info() << "MaterialEffects: energy loss DISABLED, multiple scattering kept." << endmsg;
        } else {
          me->setEnergyLossBetheBloch(true);
          me->setNoiseBetheBloch(true);
          me->setEnergyLossBrems(true);
          me->setNoiseBrems(true);
          info() << "MaterialEffects: energy loss ENABLED." << endmsg;
        }

      } catch (const std::exception& e) {
        me->setNoEffects(true);
        warning() << "MaterialEffects init failed: " << e.what() << " -> disabling material effects." << endmsg;
      } catch (...) {
        me->setNoEffects(true);
        warning() << "MaterialEffects init failed (unknown) -> disabling material effects." << endmsg;
      }
    });

    {
      auto* me = genfit::MaterialEffects::getInstance();
      info() << "MaterialEffects status: initialized="
             << (me->isInitialized() ? "true" : "false")
             << " gGeoManager=" << (gGeoManager ? "present" : "null")
             << " wantMat=" << (m_useMatEff.value() ? "true" : "false")
             << " hardOff=" << (m_disableAllMat.value() ? "true" : "false")
             << endmsg;
    }

    m_kalman = std::make_unique<genfit::KalmanFitterRefTrack>();
    m_kalman->setMaxIterations(int(std::max(1u, m_kfMaxIterations.value())));

    m_daf = std::make_unique<genfit::DAF>();
    m_daf->setMaxIterations(int(std::max(1u, m_dafMaxIterations.value())));

#if defined(GF_HAVE_GBL)
    info() << "GBL compile-time support: YES (headers found). UseGBLRefit=" << (m_useGBLRefit.value() ? "true":"false") << endmsg;
#else
    info() << "GBL compile-time support: NO (headers not found in this build). UseGBLRefit will be ignored." << endmsg;
#endif

#if defined(GF_HAVE_KALMAN_FITTERINFO)
    info() << "Smoothed-state compile-time support: YES (KalmanFitterInfo.h found). PreferSmoothedState="
           << (m_preferSmoothedState.value() ? "true":"false") << endmsg;
#else
    info() << "Smoothed-state compile-time support: NO (KalmanFitterInfo.h not found). PreferSmoothedState ignored." << endmsg;
#endif

    info() << "GenFit2DCHFitter init | Bz=" << m_Bz.value()
           << " | PDG=" << m_pdg.value()
           << " | UseKFPreFit=" << (m_useKFPreFit.value() ? "true":"false")
           << " | UseDAF=" << (m_useDAF.value() ? "true":"false")
           << " | KFMaxIters=" << m_kfMaxIterations.value()
           << " | DAFMaxIters=" << m_dafMaxIterations.value()
           << " | TryBothMomDirs=" << (m_tryBothMomDirs.value() ? "true":"false")
           << " | UseBiasedStateForPublish=" << (m_useBiasedStateForPublish.value() ? "true":"false")
           << " | PublishStateCentralFrac=" << m_publishStateCentralFrac.value()
           << " | PreferSmoothedState=" << (m_preferSmoothedState.value() ? "true":"false")
           << " | PostFitOutlierRefit=" << (m_postFitOutlierRefit.value() ? "true":"false")
           << " | PostFitMaxDrop=" << m_postFitMaxDrop.value()
           << " | UseGBLRefit=" << (m_useGBLRefit.value() ? "true":"false")
           << endmsg;

    // Write static config metadata
    try {
      std::ostringstream os;
      std::time_t now = std::time(nullptr);
      char tbuf[64] = {0};
      std::strftime(tbuf, sizeof(tbuf), "%Y-%m-%dT%H:%M:%SZ", std::gmtime(&now));

      os << "{";
      os << "\"component\":\"" << name() << "\"";
      os << ",\"timestamp_utc\":\"" << tbuf << "\"";
      os << ",\"JobTag\":\"" << m_jobTag.value() << "\"";
      os << ",\"Bz_T\":" << m_Bz.value();
      os << ",\"PDG\":" << m_pdg.value();
      os << ",\"UseKFPreFit\":" << (m_useKFPreFit.value() ? "true":"false");
      os << ",\"UseDAF\":" << (m_useDAF.value() ? "true":"false");
      os << ",\"FallbackToKFIfDAFFails\":" << (m_fallbackToKFIfDAFFails.value() ? "true":"false");
      os << ",\"KFMaxIters\":" << m_kfMaxIterations.value();
      os << ",\"DAFMaxIters\":" << m_dafMaxIterations.value();
      os << ",\"UseBiasedStateForPublish\":" << (m_useBiasedStateForPublish.value() ? "true":"false");
      os << ",\"PublishStateCentralFrac\":" << m_publishStateCentralFrac.value();
      os << ",\"PreferSmoothedState\":" << (m_preferSmoothedState.value() ? "true":"false");
      os << ",\"PostFitOutlierRefit\":" << (m_postFitOutlierRefit.value() ? "true":"false");
      os << ",\"PostFitMaxDrop\":" << m_postFitMaxDrop.value();
      os << ",\"PostFitCircleResidualInternal\":" << m_postFitCircleResidualInternal.value();
      os << ",\"PostFitMinKeep\":" << m_postFitMinKeep.value();
      os << ",\"UseGBLRefit\":" << (m_useGBLRefit.value() ? "true":"false");
      os << ",\"GBLMaxIters\":" << m_gblMaxIters.value();
      os << ",\"GBLOnlyIfImprovesChi2Ndf\":" << (m_gblOnlyIfImprovesChi2Ndf.value() ? "true":"false");
      os << ",\"WireHalfLengthMM\":" << m_wireHalfLengthMM.value();
      os << ",\"MaxDriftMM\":" << m_maxDriftMM.value();
      os << ",\"MaxDriftMMForHit\":" << m_maxDriftMMForHit.value();
      os << ",\"MinDriftErrMM\":" << m_minDriftErrMM.value();
      os << ",\"MaxDriftErrMM\":" << m_maxDriftErrMM.value();
      os << ",\"PositionUnitScale\":" << m_posScale.value();
      os << ",\"SortHits\":" << (m_sortHits.value() ? "true":"false");
      os << ",\"DeduplicateHits\":" << (m_dedupHits.value() ? "true":"false");
      os << ",\"DedupTolMM\":" << m_dedupTolMM.value();
      os << ",\"PreFitOutlierVeto\":" << (m_prefitOutlierVeto.value() ? "true":"false");
      os << ",\"OutlierMaxDrop\":" << m_outlierMaxDrop.value();
      os << ",\"OutlierCircleResidualMM\":" << m_outlierCircleResMM.value();
      os << ",\"OutlierChordResidualMM\":" << m_outlierChordResMM.value();
      os << ",\"OutlierMinKeep\":" << m_outlierMinKeep.value();
      os << ",\"SeedEndpointK\":" << m_seedEndpointK.value();
      os << ",\"SeedTangentK\":" << m_seedTangentK.value();
      os << ",\"UseSagittaSeed\":" << (m_useSagittaSeed.value() ? "true":"false");
      os << ",\"MinSagittaForSeedMM\":" << m_minSagittaForSeedMM.value();
      os << ",\"SeedPTFallbackGeV\":" << m_seedPTFallbackGeV.value();
      os << ",\"SeedPTMinGeV\":" << m_seedPTMinGeV.value();
      os << ",\"SeedPTMaxGeV\":" << m_seedPTMaxGeV.value();
      os << ",\"MinFittedPointsWithFI\":" << m_minFittedPointsWithFI.value();
      os << ",\"MaxChi2Ndf\":" << m_maxChi2Ndf.value();
      os << ",\"PublishPTMaxGeV\":" << m_publishPTMaxGeV.value();
      os << ",\"ObsMinPhiSpanRad\":" << m_obsMinPhiSpanRad.value();
      os << ",\"ObsMinChordMM\":" << m_obsMinChordMM.value();
      os << ",\"ObsMinSagittaMM\":" << m_obsMinSagittaMM.value();
      os << ",\"ObsMinScore\":" << m_obsMinScore.value();
      os << ",\"SkipIfObsTooLow\":" << (m_skipIfObsTooLow.value() ? "true":"false");
      os << ",\"StatsTruncCentralFrac\":" << m_statsTruncCentralFrac.value();
      os << ",\"DetId\":" << m_detId.value();
      os << ",\"UseLabelAsDetId\":" << (m_useLabelAsDetId.value() ? "true":"false");
      os << ",\"WireAnglesAreDegrees\":" << (m_wireAnglesAreDegrees.value() ? "true":"false");
      os << ",\"buildDate\":\"" << __DATE__ << "\"";
      os << ",\"buildTime\":\"" << __TIME__ << "\"";
      os << "}";

      m_cfgMeta.put(os.str());
      info() << "Wrote GenFit2DCHFitter configuration metadata (key='cfgMeta')" << endmsg;
    } catch (...) {
      warning() << "Failed to write GenFit2DCHFitter metadata" << endmsg;
    }

    return StatusCode::SUCCESS;
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }

  // ----------------- internal helpers -----------------

  bool ensureGeometryLoaded() const {
    if (gGeoManager) return true;
    if (m_tgeoFile.value().empty()) return false;

    info() << "gGeoManager is null. Importing TGeo from file: " << m_tgeoFile.value() << endmsg;

    TGeoManager* gm = TGeoManager::Import(m_tgeoFile.value().c_str());
    if (!gm) {
      warning() << "TGeoManager::Import failed for " << m_tgeoFile.value() << endmsg;
      return false;
    }
    gGeoManager = gm;

    if (!m_tgeoTopVolume.value().empty()) {
      auto* top = gGeoManager->GetVolume(m_tgeoTopVolume.value().c_str());
      if (top) gGeoManager->SetTopVolume(top);
    }

    if (!gGeoManager->GetTopVolume()) {
      warning() << "Imported geometry has no top volume set." << endmsg;
      return false;
    }

    info() << "Imported TGeo geometry. TopVolume=" << gGeoManager->GetTopVolume()->GetName()
           << " nMaterials=" << (gGeoManager->GetListOfMaterials() ? gGeoManager->GetListOfMaterials()->GetEntries() : -1)
           << " nMedia=" << (gGeoManager->GetListOfMedia() ? gGeoManager->GetListOfMedia()->GetEntries() : -1)
           << endmsg;

    return true;
  }

  TMatrixDSym makeSeedCov(double posInfl=1.0, double momInfl=1.0) const {
    TMatrixDSym C(6);
    C.Zero();
    const double sP = (m_seedPosSigmaMM.value() * posInfl) * (m_posScale.value()); // mm->cm
    const double sM = (m_seedMomSigmaGeV.value() * momInfl);
    for (int i = 0; i < 3; ++i) C(i, i) = sP * sP;
    for (int i = 3; i < 6; ++i) C(i, i) = sM * sM;
    ensurePD_chol(C, 1e-6, 4.0, 6);
    ensurePD_eigenClamp(C, std::max(1e-12, m_minCovEigenvalue.value()));
    return C;
  }

  double chi2ndf(const genfit::FitStatus* fs) const {
    if (!fs) return std::numeric_limits<double>::infinity();
    const double ndf = std::max(1.0, double(fs->getNdf()));
    return fs->getChi2() / ndf;
  }

  bool isGoodFS(const genfit::FitStatus* fs) const {
    if (!fs) return false;
    if (!fs->isFitted()) return false;
    if (!std::isfinite(fs->getChi2())) return false;
    if (fs->getNdf() <= 0) return false;
    return true;
  }

  const genfit::FitStatus* run_fit_kf_then_daf(genfit::Track& trk, const char* tag, int label,
                                               bool& outUsedDAF) const {
    outUsedDAF = false;

    genfit::AbsTrackRep* rep0 = trk.getCardinalRep();
    if (!rep0) return nullptr;

    const genfit::FitStatus* fsKF = nullptr;

    if (m_useKFPreFit.value()) {
      try {
        m_kalman->processTrack(&trk);
      } catch (const genfit::Exception& e) {
        warning() << "GenFit KF exception (label=" << label << ", " << tag << "): " << e.what() << endmsg;
      } catch (const std::exception& e) {
        warning() << "KF std exception (label=" << label << ", " << tag << "): " << e.what() << endmsg;
      } catch (...) {
        warning() << "KF unknown exception (label=" << label << ", " << tag << ")" << endmsg;
      }
      rep0 = trk.getCardinalRep();
      fsKF = rep0 ? trk.getFitStatus(rep0) : nullptr;
    }

    if (m_useDAF.value()) {
      try {
        m_daf->processTrack(&trk);
        outUsedDAF = true;
      } catch (const genfit::Exception& e) {
        warning() << "GenFit DAF exception (label=" << label << ", " << tag << "): " << e.what() << endmsg;
        outUsedDAF = false;
        if (!m_fallbackToKFIfDAFFails.value()) return nullptr;
        rep0 = trk.getCardinalRep();
        const genfit::FitStatus* fs = rep0 ? trk.getFitStatus(rep0) : nullptr;
        if (isGoodFS(fs)) return fs;
        if (isGoodFS(fsKF)) return fsKF;
        return nullptr;
      } catch (const std::exception& e) {
        warning() << "DAF std exception (label=" << label << ", " << tag << "): " << e.what() << endmsg;
        outUsedDAF = false;
        if (!m_fallbackToKFIfDAFFails.value()) return nullptr;
        rep0 = trk.getCardinalRep();
        const genfit::FitStatus* fs = rep0 ? trk.getFitStatus(rep0) : nullptr;
        if (isGoodFS(fs)) return fs;
        if (isGoodFS(fsKF)) return fsKF;
        return nullptr;
      } catch (...) {
        warning() << "DAF unknown exception (label=" << label << ", " << tag << ")" << endmsg;
        outUsedDAF = false;
        if (!m_fallbackToKFIfDAFFails.value()) return nullptr;
        rep0 = trk.getCardinalRep();
        const genfit::FitStatus* fs = rep0 ? trk.getFitStatus(rep0) : nullptr;
        if (isGoodFS(fs)) return fs;
        if (isGoodFS(fsKF)) return fsKF;
        return nullptr;
      }
    }

    rep0 = trk.getCardinalRep();
    const genfit::FitStatus* fs = rep0 ? trk.getFitStatus(rep0) : nullptr;
    if (isGoodFS(fs)) return fs;
    if (isGoodFS(fsKF)) return fsKF;
    return fs;
  }

  // ----------------- GBL stage (real) -----------------
  //
  // Policy:
  //   - Only attempt if compile-time support exists AND UseGBLRefit==true
  //   - Run on a copy of the already fitted track (KF/DAF output)
  //   - Accept if it improves chi2/ndf (and doesn't reduce FI points) when requested
  //   - Otherwise keep original
  //
  const genfit::FitStatus* run_optional_gbl_refit(genfit::Track& trk,
                                                  int label,
                                                  const genfit::FitStatus* fsIn) const {
#if defined(GF_HAVE_GBL)
    if (!m_useGBLRefit.value()) return fsIn;

    genfit::AbsTrackRep* repIn = trk.getCardinalRep();
    if (!repIn) return fsIn;

    if (!isGoodFS(fsIn)) return fsIn;

    const double chiIn = chi2ndf(fsIn);
    const unsigned fiIn = countFIPoints(trk);

    // Defensive: don't even try if material is disabled (GBL is mostly valuable with MS scatterers).
    // Still allow if user explicitly wants it; but warn once per job.
    static std::atomic<bool> warnedNoMat{false};
    if (genfit::MaterialEffects::getInstance()->isNoEffects() && !warnedNoMat.exchange(true)) {
      // Not fatal: sometimes people want “GBL-like” smoothing even without scatterers in some forks.
      // But typically this is not beneficial.
      // We keep going.
    }

    genfit::Track trkCopy = trk;

    try {
      const int maxIts = int(std::max(1u, m_gblMaxIters.value()));

      // Instantiate the correct GBL fitter class for the detected header.
      // Different forks place these in namespace genfit; if yours differs, adjust the type below.

      #if defined(GF_GBL_VARIANT_GBLFITTER2)
        #if (GF_GBL_VARIANT_GBLFITTER2 == 1)
          genfit::GBLFitter2 gbl;
        #else
          genfit::GblFitter2 gbl;
        #endif
        gbl.setMaxIterations(maxIts);
        gbl.processTrack(&trkCopy);

      #elif defined(GF_GBL_VARIANT_GBLFITTER)
        #if (GF_GBL_VARIANT_GBLFITTER == 3)
          genfit::GBLFitter gbl;
        #else
          genfit::GblFitter gbl;
        #endif
        gbl.setMaxIterations(maxIts);
        gbl.processTrack(&trkCopy);

      #else
        // Header detected but no known mapping: no-op
        return fsIn;
      #endif

    } catch (const genfit::Exception& e) {
      warning() << "GBL refit GenFit exception (label=" << label << "): " << e.what() << endmsg;
      return fsIn;
    } catch (const std::exception& e) {
      warning() << "GBL refit std exception (label=" << label << "): " << e.what() << endmsg;
      return fsIn;
    } catch (...) {
      warning() << "GBL refit unknown exception (label=" << label << ")" << endmsg;
      return fsIn;
    }

    genfit::AbsTrackRep* repOut = trkCopy.getCardinalRep();
    const genfit::FitStatus* fsOut = repOut ? trkCopy.getFitStatus(repOut) : nullptr;
    if (!isGoodFS(fsOut)) return fsIn;

    const double chiOut = chi2ndf(fsOut);
    const unsigned fiOut = countFIPoints(trkCopy);

    if (m_gblOnlyIfImprovesChi2Ndf.value()) {
      if (!(std::isfinite(chiOut) && std::isfinite(chiIn))) return fsIn;
      if (chiOut > chiIn) return fsIn;
      if (fiOut < fiIn) return fsIn;
    }

    // Accept: overwrite track with GBL result
    trk = std::move(trkCopy);
    repOut = trk.getCardinalRep();
    return repOut ? trk.getFitStatus(repOut) : fsIn;
#else
    (void)trk; (void)label; (void)fsIn;
    return fsIn;
#endif
  }

  // Dedup using on-wire position (in mm); requires sorted order first.
  static void dedupWireHits(std::vector<extension::SenseWireHit>& hw, double tolMM) {
    if (hw.empty()) return;
    const double tol2 = tolMM * tolMM;

    std::vector<extension::SenseWireHit> out;
    out.reserve(hw.size());

    auto prevp = hw.front().getPosition();
    out.push_back(hw.front());

    for (size_t i = 1; i < hw.size(); ++i) {
      const auto pi = hw[i].getPosition();
      const double dx = pi.x - prevp.x;
      const double dy = pi.y - prevp.y;
      const double dz = pi.z - prevp.z;
      const double d2 = dx*dx + dy*dy + dz*dz;
      if (std::isfinite(d2) && d2 < tol2) continue;
      out.push_back(hw[i]);
      prevp = pi;
    }
    hw.swap(out);
  }

  unsigned buildTrackFromWireHits(genfit::Track& outTrack,
                                  const std::vector<extension::SenseWireHit>& hw,
                                  int detIdForAllHits,
                                  double posScale_cm_per_mm,
                                  bool wireAnglesAreDegrees,
                                  unsigned& nHitDropped) const {
    const double halfL_cm  = m_wireHalfLengthMM.value() * posScale_cm_per_mm; // mm -> cm
    const double maxD_cm   = m_maxDriftMM.value()       * posScale_cm_per_mm;
    const double minErr_cm = m_minDriftErrMM.value()    * posScale_cm_per_mm;

    unsigned nInserted = 0;
    nHitDropped = 0;
    int hitId = 0;

    for (const auto& h : hw) {
      const auto p = h.getPosition();
      if (!finite3(p.x, p.y, p.z)) { ++nHitDropped; continue; }

      const double d_raw = double(h.getDistanceToWire());
      if (!std::isfinite(d_raw)) { ++nHitDropped; continue; }
      const double d_mm = std::abs(d_raw);

      if (d_mm > m_maxDriftMMForHit.value()) { ++nHitDropped; continue; }

      double derr_mm = double(h.getDistanceToWireError());
      if (!(derr_mm > 0.0) || !std::isfinite(derr_mm)) derr_mm = m_minDriftErrMM.value();
      derr_mm = std::max(derr_mm, m_minDriftErrMM.value());
      if (std::isfinite(m_maxDriftErrMM.value()) && m_maxDriftErrMM.value() > 0.0) {
        derr_mm = std::min(derr_mm, m_maxDriftErrMM.value());
      }

      const double d_cm    = d_mm    * posScale_cm_per_mm;
      const double derr_cm = std::max(derr_mm * posScale_cm_per_mm, minErr_cm);

      double phi = double(h.getWireAzimuthalAngle());
      double st  = double(h.getWireStereoAngle());
      if (!std::isfinite(phi) || !std::isfinite(st)) { ++nHitDropped; continue; }
      if (wireAnglesAreDegrees) { phi *= kDegToRad; st *= kDegToRad; }

      TVector3 dir(0, 0, 1);
      dir.RotateX(st);
      dir.RotateZ(phi);
      dir = safeUnit(dir, TVector3(0, 0, 1));

      TVector3 wp_cm(posScale_cm_per_mm * p.x,
                     posScale_cm_per_mm * p.y,
                     posScale_cm_per_mm * p.z);

      const TVector3 e1 = wp_cm - halfL_cm * dir;
      const TVector3 e2 = wp_cm + halfL_cm * dir;

      auto* tp = new genfit::TrackPoint(&outTrack);

      auto* meas = new genfit::WireMeasurementNew(d_cm, derr_cm, e1, e2,
                                                  detIdForAllHits, hitId, tp);

      meas->setLeftRightResolution(0);
      meas->setMaxDistance(maxD_cm);

      tp->addRawMeasurement(meas);
      outTrack.insertPoint(tp);

      ++hitId;
      ++nInserted;
    }
    return nInserted;
  }

  double seedPTFromSagitta(const ObsMetrics& obs) const {
    if (!obs.ok) return std::numeric_limits<double>::quiet_NaN();
    if (!(obs.chordMM > 0.0) || !(obs.sagittaMM > 0.0)) return std::numeric_limits<double>::quiet_NaN();

    const double L = obs.chordMM;     // mm
    const double s = obs.sagittaMM;   // mm
    if (s < m_minSagittaForSeedMM.value()) return std::numeric_limits<double>::quiet_NaN();

    const double R_mm = (L*L) / (8.0 * s);
    if (!std::isfinite(R_mm) || R_mm <= 0.0) return std::numeric_limits<double>::quiet_NaN();

    const double R_m = R_mm * 1e-3;
    return 0.3 * m_Bz.value() * R_m;
  }

  static TVector3 tangentDirFromWindowMM(const std::vector<extension::SenseWireHit>& hw,
                                         size_t i0, size_t i1,
                                         const TVector3& chordDirMM_unit) {
    if (hw.size() < 3) return chordDirMM_unit;
    i1 = std::min(i1, hw.size());
    if (i1 <= i0 + 2) return chordDirMM_unit;

    TVector3 ax = principalAxisFromPositionsMM(hw, i0, i1);
    if (ax.Dot(chordDirMM_unit) < 0) ax *= -1.0;
    return safeUnit(ax, chordDirMM_unit);
  }

  bool build_and_fit_from_hits(genfit::Track& outTrk,
                               const std::vector<extension::SenseWireHit>& hits,
                               const TVector3& seedPos_cm,
                               const TVector3& seedMom,
                               int detId,
                               bool& outUsedDAF,
                               const genfit::FitStatus*& outFS) const {
    auto rep_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
    outTrk = genfit::Track(rep_up.release(), seedPos_cm, seedMom);
    outTrk.setCovSeed(makeSeedCov(1.0, 1.0));

    unsigned nDrop = 0;
    const unsigned nMeas = buildTrackFromWireHits(outTrk, hits, detId,
                                                  m_posScale.value(),
                                                  m_wireAnglesAreDegrees.value(),
                                                  nDrop);
    if (nMeas < m_minMeasurementsToFit.value()) {
      outFS = nullptr;
      outUsedDAF = false;
      return false;
    }

    outFS = run_fit_kf_then_daf(outTrk, "build_and_fit", detId, outUsedDAF);
    if (!isGoodFS(outFS)) return false;

    // Optional: apply GBL here too (rarely needed; main path does it once after picking best sign)
    outFS = run_optional_gbl_refit(outTrk, detId, outFS);

    if (countFIPoints(outTrk) < m_minFittedPointsWithFI.value()) return false;
    if (!std::isfinite(chi2ndf(outFS))) return false;
    return true;
  }

  extension::TrackCollection
  operator()(const extension::TrackCollection& inTracks) const override {
    extension::TrackCollection out;

    const double posScale_cm_per_mm = m_posScale.value();
    const int qPublish = chargeFromPDG(m_pdg.value());

    unsigned nIn = 0, nFit = 0, nFail = 0;
    unsigned nSkipNoHitsRead = 0, nSkipNoSenseWireHits = 0, nSkipMinHits = 0;
    unsigned nSkipTooFewMeas = 0, nSkipBadSeed = 0, nSkipFewFI = 0;
    unsigned nSkipChi2 = 0, nSkipObs = 0;
    unsigned nWarnedType = 0;
    unsigned nPrunedTotal = 0;
    unsigned nPostFitDroppedTotal = 0;
    unsigned nPostFitRecovered = 0;

    std::vector<double> publishedPTs;
    publishedPTs.reserve(inTracks.size());

    for (const auto& trkIn : inTracks) {
      ++nIn;

      const int label = int(trkIn.getType());
      if (m_rejectNegativeLabels.value() && label < 0) continue;

      std::vector<extension::SenseWireHit> wireHits;
      wireHits.reserve(256);

      size_t totalTH = 0;

      try {
        auto rng = trkIn.getTrackerHits();
        totalTH = rng.size();
        for (const auto& th : rng) {
          if (!th.isAvailable()) continue;
          if (!th.isA<extension::SenseWireHit>()) {
            if (msgLevel(MSG::DEBUG) && nWarnedType < 3) {
              debug() << "Non-SenseWireHit trackerHit on label=" << label
                      << " (skipping). If all are non-SenseWireHit, GGTF is not attaching SenseWireHit relations."
                      << endmsg;
              ++nWarnedType;
            }
            continue;
          }
          wireHits.push_back(th.as<extension::SenseWireHit>());
        }
      } catch (...) {
        warning() << "Track trackerHits relation read failed (label=" << label << "). Skipping." << endmsg;
        ++nSkipNoHitsRead;
        continue;
      }

      if (wireHits.empty()) {
        ++nSkipNoSenseWireHits;
        if (msgLevel(MSG::DEBUG) && m_diagEveryNTracks.value() > 0 && (nIn % m_diagEveryNTracks.value() == 0)) {
          debug() << "Diag: label=" << label
                  << " trackerHits_total=" << totalTH
                  << " senseWireHits_found=0"
                  << endmsg;
        }
        continue;
      }

      if (m_sortHits.value()) sortWireHitsAlongPCA(wireHits);
      if (m_dedupHits.value() && m_dedupTolMM.value() > 0.0) dedupWireHits(wireHits, m_dedupTolMM.value());

      if (m_prefitOutlierVeto.value()) {
        const unsigned dropped = pruneOutliersXY(
          wireHits,
          m_outlierMaxDrop.value(),
          m_outlierCircleResMM.value(),
          m_outlierChordResMM.value(),
          std::max<unsigned>(m_outlierMinKeep.value(), m_minHitsPerTrack.value())
        );
        nPrunedTotal += dropped;
      }

      if (wireHits.size() < m_minHitsPerTrack.value()) { ++nSkipMinHits; continue; }

      const ObsMetrics obs = computeObsMetricsXY(wireHits, m_obsSigmaEffMM.value(), m_minHitsForObs.value());

      const bool obsPass =
        obs.ok &&
        (obs.phiSpanRad >= m_obsMinPhiSpanRad.value()) &&
        (obs.chordMM    >= m_obsMinChordMM.value()) &&
        (obs.sagittaMM  >= m_obsMinSagittaMM.value()) &&
        (obs.obsScore   >= m_obsMinScore.value());

      if (!obsPass && m_skipIfObsTooLow.value()) {
        ++nSkipObs;
        continue;
      }

      const unsigned Kprop = std::max(1u, m_seedEndpointK.value());
      const unsigned K = std::min<unsigned>(Kprop, unsigned(wireHits.size() / 2));

      auto meanPosMM = [&](size_t i0, size_t i1) -> TVector3 {
        double sx = 0, sy = 0, sz = 0;
        size_t n = 0;
        for (size_t i = i0; i < i1; ++i) {
          const auto p = wireHits[i].getPosition();
          if (!finite3(p.x, p.y, p.z)) continue;
          sx += p.x; sy += p.y; sz += p.z; ++n;
        }
        if (n == 0) return TVector3(0, 0, 0);
        return TVector3(sx / double(n), sy / double(n), sz / double(n));
      };

      const TVector3 pStartMM = meanPosMM(0, K);
      const TVector3 pEndMM   = meanPosMM(wireHits.size() - K, wireHits.size());

      if (!finite3(pStartMM.X(), pStartMM.Y(), pStartMM.Z()) ||
          !finite3(pEndMM.X(),   pEndMM.Y(),   pEndMM.Z())) {
        ++nSkipBadSeed;
        continue;
      }

      TVector3 chordDirMM = pEndMM - pStartMM;
      if (!std::isfinite(chordDirMM.Mag2()) || chordDirMM.Mag2() < 1e-12) chordDirMM = TVector3(0,0,1);
      chordDirMM = safeUnit(chordDirMM, TVector3(0,0,1));

      const unsigned KtanProp = std::max(3u, m_seedTangentK.value());
      const unsigned Ktan = std::min<unsigned>(KtanProp, unsigned(wireHits.size() / 2));

      const TVector3 t1 = tangentDirFromWindowMM(wireHits, 0, Ktan, chordDirMM);
      const TVector3 t2 = tangentDirFromWindowMM(wireHits, wireHits.size() - Ktan, wireHits.size(), chordDirMM);

      TVector3 dirMM = safeUnit(t1 + t2, chordDirMM);
      if (!std::isfinite(dirMM.Mag2()) || dirMM.Mag2() < 1e-12) dirMM = chordDirMM;

      const TVector3 pos0_cm(posScale_cm_per_mm * pStartMM.X(),
                             posScale_cm_per_mm * pStartMM.Y(),
                             posScale_cm_per_mm * pStartMM.Z());

      TVector3 dir = safeUnit(dirMM, TVector3(0,0,1));

      double pTseed = m_seedPTFallbackGeV.value();
      if (m_useSagittaSeed.value()) {
        const double ptSag = seedPTFromSagitta(obs);
        if (std::isfinite(ptSag) && ptSag > 0.0) pTseed = ptSag;
      }
      pTseed = clampFinite(pTseed, m_seedPTMinGeV.value(), m_seedPTMaxGeV.value(), m_seedPTFallbackGeV.value());

      const double cosTheta = std::clamp(std::abs(dir.Z()), 0.0, 0.999999);
      const double sinTheta = std::sqrt(std::max(1e-4, 1.0 - cosTheta * cosTheta));

      double pMag = pTseed / sinTheta;
      if (!std::isfinite(pMag) || pMag <= 0) pMag = pTseed;
      pMag = std::max(pMag, m_seedPMinGeV.value());

      const TVector3 mom0 = pMag * dir;

      const int detId = m_useLabelAsDetId.value() ? label : m_detId.value();

      // ----------------- Initial build & fit, both momentum directions optional -----------------
      auto rep1_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
      genfit::Track trk1(rep1_up.release(), pos0_cm, mom0);
      trk1.setCovSeed(makeSeedCov(1.0, 1.0));

      unsigned nDrop1 = 0;
      const unsigned nMeas1 = buildTrackFromWireHits(trk1, wireHits, detId,
                                                     posScale_cm_per_mm,
                                                     m_wireAnglesAreDegrees.value(),
                                                     nDrop1);
      if (nMeas1 < m_minMeasurementsToFit.value()) { ++nSkipTooFewMeas; continue; }

      bool usedDAF1 = false;
      const genfit::FitStatus* fs1 = run_fit_kf_then_daf(trk1, "fit(+mom)", label, usedDAF1);
      fs1 = run_optional_gbl_refit(trk1, label, fs1);

      const bool ok1 = isGoodFS(fs1) && (countFIPoints(trk1) >= m_minFittedPointsWithFI.value());

      std::unique_ptr<genfit::Track> trk2_ptr;
      const genfit::FitStatus* fs2 = nullptr;
      bool ok2 = false;
      bool usedDAF2 = false;

      if (m_tryBothMomDirs.value()) {
        auto rep2_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
        trk2_ptr = std::make_unique<genfit::Track>(rep2_up.release(), pos0_cm, -mom0);
        trk2_ptr->setCovSeed(makeSeedCov(1.0, 1.0));

        unsigned nDrop2 = 0;
        const unsigned nMeas2 = buildTrackFromWireHits(*trk2_ptr, wireHits, detId,
                                                       posScale_cm_per_mm,
                                                       m_wireAnglesAreDegrees.value(),
                                                       nDrop2);
        if (nMeas2 >= m_minMeasurementsToFit.value()) {
          fs2 = run_fit_kf_then_daf(*trk2_ptr, "fit(-mom)", label, usedDAF2);
          fs2 = run_optional_gbl_refit(*trk2_ptr, label, fs2);
          ok2 = isGoodFS(fs2) && (countFIPoints(*trk2_ptr) >= m_minFittedPointsWithFI.value());
        }
      }

      auto better = [&](genfit::Track* aTrk, const genfit::FitStatus* aFs,
                        genfit::Track* bTrk, const genfit::FitStatus* bFs)->bool {
        const bool aGood = isGoodFS(aFs) && (countFIPoints(*aTrk) >= m_minFittedPointsWithFI.value());
        const bool bGood = isGoodFS(bFs) && (countFIPoints(*bTrk) >= m_minFittedPointsWithFI.value());
        if (aGood != bGood) return aGood;
        const double ca = chi2ndf(aFs);
        const double cb = chi2ndf(bFs);
        if (ca != cb) return ca < cb;
        return countFIPoints(*aTrk) > countFIPoints(*bTrk);
      };

      genfit::Track* bestTrk = nullptr;
      const genfit::FitStatus* bestFs = nullptr;

      if (ok1) { bestTrk = &trk1; bestFs = fs1; }
      if (ok2) {
        if (!bestTrk) { bestTrk = trk2_ptr.get(); bestFs = fs2; }
        else if (better(trk2_ptr.get(), fs2, bestTrk, bestFs)) {
          bestTrk = trk2_ptr.get();
          bestFs = fs2;
        }
      }

      if (!(bestTrk && bestFs)) { ++nFail; continue; }

      // ----------------- Post-fit outlier refit loop -----------------
      std::vector<extension::SenseWireHit> hitsForRefit = wireHits;
      bool recovered = false;

      if (m_postFitOutlierRefit.value()) {
        for (unsigned it = 0; it < m_postFitMaxDrop.value(); ++it) {
          if (hitsForRefit.size() <= std::max<unsigned>(m_postFitMinKeep.value(), m_minHitsPerTrack.value())) break;

          const double c2now = chi2ndf(bestFs);
          if (std::isfinite(c2now) && c2now < std::max(2.0, 0.3*m_maxChi2Ndf.value())) break;

          const PostFitWorstPoint worst = findWorstPointByFittedCircleResidual(
            *bestTrk, m_useBiasedStateForPublish.value(), m_preferSmoothedState.value()
          );
          if (!worst.ok) break;
          if (!(worst.residInternal > m_postFitCircleResidualInternal.value())) break;

          const size_t idxHit = worst.idxPoint;
          if (idxHit >= hitsForRefit.size()) break;

          hitsForRefit.erase(hitsForRefit.begin() + idxHit);
          ++nPostFitDroppedTotal;

          const bool usePlus = (bestTrk == &trk1);
          const TVector3 momSeed = usePlus ? mom0 : (-mom0);

          genfit::Track tmpTrk;
          bool usedDAFtmp = false;
          const genfit::FitStatus* fstmp = nullptr;
          const bool ok = build_and_fit_from_hits(tmpTrk, hitsForRefit, pos0_cm, momSeed, detId, usedDAFtmp, fstmp);
          if (!ok || !fstmp) break;

          const double c2new = chi2ndf(fstmp);
          const unsigned fiNew = countFIPoints(tmpTrk);
          const double c2old = chi2ndf(bestFs);
          const unsigned fiOld = countFIPoints(*bestTrk);

          bool take = false;
          if (isGoodFS(fstmp) && fiNew >= m_minFittedPointsWithFI.value()) {
            if (!std::isfinite(c2old)) take = true;
            else if (std::isfinite(c2new) && c2new <= c2old) take = true;
            else if (fiNew > fiOld) take = true;
          }

          if (take) {
            if (bestTrk == &trk1) {
              trk1 = std::move(tmpTrk);
              bestTrk = &trk1;
              bestFs = trk1.getFitStatus(trk1.getCardinalRep());
            } else if (trk2_ptr && bestTrk == trk2_ptr.get()) {
              *trk2_ptr = std::move(tmpTrk);
              bestTrk = trk2_ptr.get();
              bestFs = bestTrk->getFitStatus(bestTrk->getCardinalRep());
            } else {
              break;
            }
            recovered = true;
          } else {
            break;
          }
        }
      }

      if (recovered) ++nPostFitRecovered;

      // ----------------- Acceptance -----------------
      const unsigned nFI = countFIPoints(*bestTrk);
      if (nFI < m_minFittedPointsWithFI.value()) { ++nSkipFewFI; continue; }

      const double c2 = chi2ndf(bestFs);
      if (!std::isfinite(c2) || c2 > m_maxChi2Ndf.value()) { ++nSkipChi2; continue; }

      // ----------------- Publish-state selection -----------------
      genfit::MeasuredStateOnPlane pubState;
      size_t pubIdx = 0;
      const bool havePubState = selectPublishStateCentral(*bestTrk,
                                                          m_useBiasedStateForPublish.value(),
                                                          m_publishStateCentralFrac.value(),
                                                          m_preferSmoothedState.value(),
                                                          pubState,
                                                          pubIdx);
      if (!havePubState) { ++nFail; continue; }

      const TVector3 pos_cm = pubState.getPos();
      const TVector3 mom    = pubState.getMom();

      bool haveCov5 = false;
      TMatrixDSym cov5(5);

      TVector3 pos_used_cm = pos_cm;
      TVector3 mom_used    = mom;
      const float fittedPT = float(std::hypot(mom_used.X(), mom_used.Y()));

      try {
        genfit::AbsTrackRep* rep = bestTrk->getCardinalRep();
        if (rep) {
          genfit::MeasuredStateOnPlane stAtIP = pubState;
          rep->extrapolateToPoint(stAtIP, TVector3(0.,0.,0.));
          haveCov5 = covPerigeeFromRepStateFD(rep, stAtIP, qPublish, posScale_cm_per_mm, cov5);
          if (haveCov5) {
            pos_used_cm = stAtIP.getPos();
            mom_used    = stAtIP.getMom();
          }
        }
      } catch (...) {
        haveCov5 = false;
      }

      bool ptValid = true;
      ptValid = ptValid && std::isfinite(fittedPT) && (fittedPT > 0.0f) &&
                (double(fittedPT) < m_publishPTMaxGeV.value());
      if (!obsPass) ptValid = false;

      const float omegaVar = ptValid ? m_omegaVarGood.value() : m_omegaVarBad.value();

      auto trkOut = out.create();
      trkOut.setType(m_pdg.value());

      try {
        trkOut.setChi2(bestFs->getChi2());
        trkOut.setNdf(bestFs->getNdf());
      } catch (...) {}

      try {
        for (const auto& th : trkIn.getTrackerHits()) trkOut.addToTrackerHits(th);
      } catch (...) {}

      const float obsScoreF = float(std::isfinite(obs.obsScore) ? obs.obsScore : -1.0);
      const float c2f = float(std::isfinite(c2) ? std::min(c2, 1e6) : -1.0);
      const float nFIf = float(nFI);

      addAtIPState(trkOut,
                   pos_used_cm,
                   mom_used,
                   posScale_cm_per_mm,
                   qPublish,
                   ptValid,
                   m_invalidPTSentinel.value(),
                   omegaVar,
                   obsScoreF,
                   c2f,
                   nFIf,
                   haveCov5 ? &cov5 : nullptr);

      if (ptValid) publishedPTs.push_back(double(fittedPT));
      ++nFit;
    }

    RobustStats rs = robustStats(publishedPTs, m_statsTruncCentralFrac.value());

    try {
      std::ostringstream os;
      os << "{";
      os << "\"nInputTracks\":" << nIn;
      os << ",\"nFitted\":" << nFit;
      os << ",\"nFailed\":" << nFail;
      os << ",\"skipNoTrackerHitsRead\":" << nSkipNoHitsRead;
      os << ",\"skipNoSenseWireHits\":" << nSkipNoSenseWireHits;
      os << ",\"skipMinHits\":" << nSkipMinHits;
      os << ",\"skipTooFewMeasurements\":" << nSkipTooFewMeas;
      os << ",\"skipBadSeed\":" << nSkipBadSeed;
      os << ",\"skipFewFIPoints\":" << nSkipFewFI;
      os << ",\"skipObs\":" << nSkipObs;
      os << ",\"skipChi2\":" << nSkipChi2;
      os << ",\"nPrunedHitsTotal\":" << nPrunedTotal;
      os << ",\"nPostFitDroppedTotal\":" << nPostFitDroppedTotal;
      os << ",\"nPostFitRecovered\":" << nPostFitRecovered;
      os << ",\"pTStats_n\":" << rs.n;
      os << ",\"pTStats_median\":" << (std::isfinite(rs.median) ? rs.median : -1.0);
      os << ",\"pTStats_mad\":" << (std::isfinite(rs.mad) ? rs.mad : -1.0);
      os << ",\"pTStats_madSigma\":" << (std::isfinite(rs.madSigma) ? rs.madSigma : -1.0);
      os << ",\"pTStats_truncRms\":" << (std::isfinite(rs.trRms) ? rs.trRms : -1.0);
      os << "}";
      m_evtMeta.put(os.str());
    } catch (...) {}

    info() << "GenFit2DCHFitter summary: inputTracks=" << nIn
           << " fitted=" << nFit
           << " failed=" << nFail
           << " skipNoTrackerHitsRead=" << nSkipNoHitsRead
           << " skipNoSenseWireHits=" << nSkipNoSenseWireHits
           << " skipMinHits=" << nSkipMinHits
           << " skipTooFewMeasurements=" << nSkipTooFewMeas
           << " skipBadSeed=" << nSkipBadSeed
           << " skipFewFIPoints=" << nSkipFewFI
           << " skipObs=" << nSkipObs
           << " skipChi2=" << nSkipChi2
           << " prunedHitsTotal=" << nPrunedTotal
           << " postFitDroppedTotal=" << nPostFitDroppedTotal
           << " postFitRecovered=" << nPostFitRecovered
           << " | pT(robust): n=" << rs.n
           << " median=" << (std::isfinite(rs.median) ? rs.median : -1.0)
           << " MAD=" << (std::isfinite(rs.mad) ? rs.mad : -1.0)
           << " MADsigma~=" << (std::isfinite(rs.madSigma) ? rs.madSigma : -1.0)
           << " truncRMS=" << (std::isfinite(rs.trRms) ? rs.trRms : -1.0)
           << " (centralFrac=" << m_statsTruncCentralFrac.value() << ")"
           << endmsg;

    return out;
  }

private:
  mutable std::unique_ptr<genfit::KalmanFitterRefTrack> m_kalman;
  mutable std::unique_ptr<genfit::DAF>                 m_daf;
  mutable std::once_flag m_matOnce;
  mutable std::atomic<bool> m_matInitDone{false};
  mutable std::mutex        m_matInitMutex;

  mutable k4FWCore::MetaDataHandle<std::string> m_cfgMeta;
  mutable k4FWCore::MetaDataHandle<std::string> m_evtMeta;
};

DECLARE_COMPONENT(GenFit2DCHFitter)
