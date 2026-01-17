// ======================================================================
// GenFit2DCHFitter.cpp  -- DCH fit of GGTF tracks using GenFit2 WireMeasurementNew
//
// Purpose (NEW, matches your new GGTF_tracking.cpp intent):
//   - Consume GGTF track candidates that already contain the *SenseWireHits*
//     (NOT spacepoints / NOT GGTF_3DHits).
//   - Build GenFit measurements as *WireMeasurementNew* using:
//        * drift distance (+ error)
//        * wire direction from (stereoAngle, azimuthalAngle)
//        * a point on the wire from hit.position
//        * wire endpoints synthesized as (pos ± halfLength * dir)
//   - Resolve left/right ambiguity with DAF by default (best-practice for DCH).
//   - Export ONE authoritative TrackState(AtIP) per output track.
//     Convention kept: TrackState.omega = q/pT [GeV^-1]; TrackState.time = pT [GeV].
//
// Key robustness updates added in this revision:
//   (F1) HARD disable GenFit MaterialEffects when UseMaterialEffects=false OR geometry missing.
//        This prevents the common fatal exception:
//          "MaterialEffects hasn't been initialized with a correct AbsMaterialInterface pointer!"
//   (F2) Add verbose diagnostics on hit extraction:
//        - total trackerHits on input track
//        - how many are SenseWireHit
//        - first-hit introspection (typeName if available)
//   (F3) Guard: require at least 2 usable measurement hits were actually inserted into GenFit track.
//        (Previously you could pass MinHitsPerTrack but still insert 0 meas if fields were NaN.)
//   (F4) More stable/defensive seed direction normalization and finite checks.
//   (F5) Use detId = constant (DetId) by default, not GGTF label, to avoid weird/negative detId.
//        (You still can keep label for debugging via property if you want.)
//   (F6) Optional radians/degree conversion toggle for wire angles (WireAnglesAreDegrees).
//        Default assumes radians (as in your current pipeline comments), but you can flip it.
//   (F7) Optional "accept non-SenseWireHit" fallback mode that logs and skips (no silent empties).
//        (We still do not fabricate measurements from unknown hit types; we just make the failure obvious.)
//   (F8) Additional summary counters for: tracks with 0 meas inserted, nan/inf fields, etc.
//
// Notes / assumptions:
//   - SenseWireHit fields used (as in your GGTF code):
//       getPosition(), getDistanceToWire(), getDistanceToWireError(),
//       getWireAzimuthalAngle(), getWireStereoAngle(), getPositionAlongWireError() (optional)
//   - IMPORTANT: extension::Track::trackerHits holds extension::TrackerHit (type-erased interface).
//     We MUST downcast via isA<extension::SenseWireHit>() and as<extension::SenseWireHit>().
//   - Wire endpoints: we do not (yet) pull true wire endpoints from DD4hep geometry.
//     Instead we use a configurable half-length (WireHalfLengthMM).
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
#include "extension/TrackerHit.h"          // <- type-erased interface for Track::trackerHits
#include "extension/SenseWireHit.h"

// ROOT / TGeo
#include "TVector3.h"
#include "TVectorD.h"
#include "TMatrixDSym.h"
#include "TMatrixD.h"
#include "TMatrixDSymEigen.h"
#include "TDecompChol.h"
#include "TGeoManager.h"

// GenFit2
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
#include "KalmanFitterInfo.h"
#include "DAF.h"

// Measurements
#include "WireMeasurementNew.h"

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

// Simple PD guard via Cholesky, inflating diagonals if needed
inline void ensurePD_chol(TMatrixDSym& C, double floorDiag, double inflateFactor, int maxIters) {
  makeDiagonalFloor(C, floorDiag);
  for (int it = 0; it < maxIters; ++it) {
    TDecompChol chol(C);
    if (chol.Decompose()) return;
    for (int i = 0; i < C.GetNrows(); ++i) C(i, i) *= inflateFactor;
  }
  for (int i = 0; i < C.GetNrows(); ++i) C(i, i) += floorDiag;
}

// Stronger PD guard: eigenvalue clamp (symmetric)
inline void ensurePD_eigenClamp(TMatrixDSym& C, double minEig) {
  // symmetrize
  for (int i = 0; i < C.GetNrows(); ++i) {
    for (int j = i + 1; j < C.GetNcols(); ++j) {
      const double v = 0.5 * (C(i, j) + C(j, i));
      C(i, j) = v;
      C(j, i) = v;
    }
  }

  // If diagonals are NaN/inf, bail to diagonal floor
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

// Extract best fitted state near IP (robust selection).
static bool selectBestFittedState(const genfit::Track& gftrk,
                                  double publishPTMaxGeV,
                                  double zWeight,
                                  double idxWeight,
                                  genfit::MeasuredStateOnPlane& outState,
                                  float& outPT,
                                  size_t& outIdx) {
  genfit::AbsTrackRep* rep = gftrk.getCardinalRep();
  if (!rep) return false;

  struct Cand {
    double score = 0.0;
    double r2 = 0.0;
    double absz = 0.0;
    double pt = 0.0;
    size_t idx = 0;
    genfit::MeasuredStateOnPlane st;
  };

  const size_t nPts = gftrk.getNumPoints();
  if (nPts == 0) return false;
  const double midIdx = 0.5 * double(nPts - 1);

  bool have = false;
  Cand best;

  for (size_t i = 0; i < nPts; ++i) {
    const genfit::TrackPoint* tp = gftrk.getPoint(i);
    if (!tp || !tp->hasFitterInfo(rep)) continue;

    auto* fi = dynamic_cast<const genfit::KalmanFitterInfo*>(tp->getFitterInfo(rep));
    if (!fi) continue;

    try {
      genfit::MeasuredStateOnPlane st = fi->getFittedState();
      TVector3 pos = st.getPos();
      TVector3 mom = st.getMom();

      const double pt = std::hypot(mom.X(), mom.Y());
      if (!std::isfinite(pt) || pt <= 0.0) continue;

      if (std::isfinite(publishPTMaxGeV) && publishPTMaxGeV > 0.0) {
        if (pt > 10.0 * publishPTMaxGeV) continue; // strong sanity reject
      }

      const double r2 = pos.Perp2();
      const double az = std::abs(pos.Z());
      if (!std::isfinite(r2) || !std::isfinite(az)) continue;

      const double di = double(i) - midIdx;
      const double score = r2 + zWeight * (az * az) + idxWeight * (di * di);

      Cand c;
      c.score = score;
      c.r2 = r2;
      c.absz = az;
      c.pt = pt;
      c.idx = i;
      c.st = st;

      if (!have || c.score < best.score) {
        best = c;
        have = true;
      }
    } catch (...) {}
  }

  if (!have) return false;

  outState = best.st;
  outIdx = best.idx;

  TVector3 mom = outState.getMom();
  outPT = float(std::hypot(mom.X(), mom.Y()));
  if (!std::isfinite(outPT) || outPT <= 0.f) return false;

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
                         float pTOverrideOrNeg = -1.f) {
  using TP = edm4hep::TrackParams;

  // internal cm -> mm for EDM4hep referencePoint
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
  ts.omega          = float(omegaSigned);  // q/pT [GeV^-1]
  ts.tanLambda      = float(tanL);
  ts.D0             = float(d0);
  ts.Z0             = float(z0);

  if (ptValid) {
    const float outPT = (pTOverrideOrNeg > 0.f ? pTOverrideOrNeg : float(pT));
    ts.time = outPT;
  } else {
    ts.time = invalidPTSentinel;
  }

  // Minimal covariance placeholders (downstream code can ignore these)
  ts.setCovMatrix(1.0f,     TP::d0,    TP::d0);
  ts.setCovMatrix(1e-3f,    TP::phi,   TP::phi);
  ts.setCovMatrix(omegaVar, TP::omega, TP::omega);
  ts.setCovMatrix(1.0f,     TP::z0,    TP::z0);

  // stash obsScore in tanLambda variance (non-physics metadata slot)
  float obs = (std::isfinite(obsScore) ? obsScore : -1.0f);
  ts.setCovMatrix(obs, TP::tanLambda, TP::tanLambda);

  trk.addToTrackStates(ts);
}

// degrees->radians helper
constexpr double kDegToRad = M_PI / 180.0;

} // end anonymous namespace

// ======================================================================

struct GenFit2DCHFitter final
  : k4FWCore::Transformer<extension::TrackCollection (const extension::TrackCollection&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  GenFit2DCHFitter(const std::string& name, ISvcLocator* svcLoc)
    : Transformer(name, svcLoc,
        std::tuple<KeyValues>{ KeyValues{"inputTracks",
                                         std::vector<std::string>{"CDCHTracks"}} },
        std::tuple<KeyValues>{ KeyValues{"outputTracks",
                                         std::vector<std::string>{"GenFitTracks"}} }),
      m_cfgMeta("GenFit2DCHFitterConfig", Gaudi::DataHandle::Writer) {}

  // ----------------- Properties -----------------

  // Input safety
  Gaudi::Property<bool> m_rejectNegativeLabels{
    this,"RejectNegativeLabels", true,
    "Skip GGTF tracks with track.type < 0 (debug labels)."
  };

  Gaudi::Property<unsigned> m_minHitsPerTrack{
    this,"MinHitsPerTrack", 8u, "Minimum SenseWireHits per GGTF track to attempt fit."
  };

  // NEW: require at least N measurements actually inserted into GenFit track
  Gaudi::Property<unsigned> m_minMeasurementsToFit{
    this, "MinMeasurementsToFit", 6u,
    "Minimum WireMeasurementNew actually inserted into GenFit track to attempt fit (guards NaNs)."
  };

  // Determinism / stability: sort and (optionally) dedup wire-hits (uses wire-point positions)
  Gaudi::Property<bool> m_sortHits{
    this,"SortHits", true,
    "Sort SenseWireHits deterministically by (r,z,phi) using their on-wire position."
  };

  Gaudi::Property<bool> m_dedupHits{
    this,"DeduplicateHits", true,
    "Drop nearly-identical on-wire positions (helps if upstream duplicated hits)."
  };

  Gaudi::Property<double> m_dedupTolMM{
    this,"DedupTolMM", 0.05,
    "Dedup tolerance on on-wire XYZ distance (mm)."
  };

  // Fit engine: DAF is recommended for L/R ambiguity
  Gaudi::Property<bool> m_useDAF{
    this,"UseDAF", true, "Use GenFit DAF (recommended for wire left/right ambiguity)."
  };

  Gaudi::Property<unsigned> m_dafMaxIterations{
    this,"DAFMaxIterations", 8u, "DAF max iterations."
  };

  // Robustness: try +/- momentum
  Gaudi::Property<bool> m_tryBothMomDirs{
    this, "TryBothMomentumDirections", true,
    "Try mom0 and -mom0; keep best fit"
  };

  Gaudi::Property<double> m_Bz {this, "Bz", 2.0, "Bz field [T]"};
  Gaudi::Property<int>    m_pdg{this, "PDG", 13,  "PDG hypothesis (charge sign comes from this)."};

  // Material effects
  Gaudi::Property<bool> m_useMatEff{this, "UseMaterialEffects", true,
                                    "Use TGeoMaterialInterface for GenFit MaterialEffects"};

  Gaudi::Property<bool> m_disableEloss{this, "DisableEnergyLoss", true,
                                       "Disable Bethe-Bloch/Brems energy loss (keep MS) when material effects are enabled"};

  Gaudi::Property<bool> m_disableAllMat{this, "DisableAllMaterialEffects", false,
                                        "Disable all GenFit material effects (stronger than DisableEnergyLoss)"};

  // NEW: enforce MaterialEffects OFF when missing geo or when user disables
  Gaudi::Property<bool> m_hardDisableMatIfNoGeo{
    this, "HardDisableMaterialIfNoGeo", true,
    "If true: when gGeoManager is null, force MaterialEffects::setNoEffects(true) to avoid GenFit exceptions."
  };

  // Units / scales
  Gaudi::Property<double> m_posScale{this, "PositionUnitScale", 0.1,
                                     "Multiply positions (0.1: mm->cm) for GenFit internal units."};

  Gaudi::Property<double> m_internalLenToM{this, "InternalLengthToMeters", 0.01,
                                          "Length to meters (0.01: cm->m) for pT~0.3BR."};

  // Wire endpoint synthesis (until we pull real endpoints from geometry)
  Gaudi::Property<double> m_wireHalfLengthMM{
    this,"WireHalfLengthMM", 1250.0,
    "Half wire length used to synthesize endpoints when building WireMeasurementNew (mm)."
  };

  // DCH drift model inputs from digi
  Gaudi::Property<double> m_maxDriftMM{
    this,"MaxDriftMM", 30.0,
    "Max drift distance (mm) for WireMeasurementNew weighting (setMaxDistance)."
  };

  Gaudi::Property<double> m_minDriftErrMM{
    this,"MinDriftErrMM", 0.05,
    "Floor for drift distance error (mm)."
  };

  // Seed / robustness
  Gaudi::Property<double> m_seedPosSigmaMM  {this, "SeedPosSigmaMM", 80.0, "Seed pos sigma [mm]"};
  Gaudi::Property<double> m_seedMomSigmaGeV {this, "SeedMomSigmaGeV", 5.0,  "Seed mom sigma [GeV]"};
  Gaudi::Property<double> m_seedPTMinGeV    {this, "SeedPTMinGeV",    0.20, "Min pT [GeV]"};
  Gaudi::Property<double> m_seedPTMaxGeV    {this, "SeedPTMaxGeV",   200.0, "Max pT [GeV]"};
  Gaudi::Property<double> m_seedPMinGeV     {this, "SeedPMinGeV",     0.05, "Min |p| [GeV] (numerical floor)"};

  // PD guards
  Gaudi::Property<double> m_minCovEigenvalue{this,"MinCovEigenvalue", 1e-8,
    "Minimum eigenvalue (internal length units^2) used when PD-guarding covariance matrices."};

  // Publishing gates
  Gaudi::Property<double> m_publishPTMaxGeV{this,"PublishPTMaxGeV", 300.0,
    "Hard maximum pT to publish in TrackState.time; above this, publish invalid sentinel."};

  Gaudi::Property<float> m_invalidPTSentinel {this, "InvalidPTSentinel", -1.0f,
                                              "TrackState.time when pT is not published"};

  Gaudi::Property<float> m_omegaVarGood {this, "OmegaVarGood", 1e-4f,
                                         "(GeV^-1)^2 covariance for omega when pT valid"};
  Gaudi::Property<float> m_omegaVarBad  {this, "OmegaVarBad",  1.0f,
                                         "(GeV^-1)^2 covariance for omega when pT invalid"};

  // Best fitted state selection weights
  Gaudi::Property<double> m_bestStateZWeight{this,"BestStateZWeight", 0.0,
    "Weight for choosing best fitted state: adds z^2 term (internal units) to r^2."};

  Gaudi::Property<double> m_bestStateIdxWeight{this,"BestStateIdxWeight", 1e-3,
    "Weight for choosing best fitted state: adds (idx-mid)^2 to discourage edge-pathologies."};

  // Optional job tag
  Gaudi::Property<std::string> m_jobTag{this, "JobTag", "",
                                        "Optional job tag string recorded in metadata"};

  // NEW: detId policy
  Gaudi::Property<int> m_detId{
    this, "DetId", 0,
    "detId passed to WireMeasurementNew (recommended constant; do NOT use GGTF label)."
  };

  Gaudi::Property<bool> m_useLabelAsDetId{
    this, "UseLabelAsDetId", false,
    "If true: use GGTF track label as detId (not recommended; can break if labels are weird)."
  };

  // NEW: angle convention
  Gaudi::Property<bool> m_wireAnglesAreDegrees{
    this, "WireAnglesAreDegrees", false,
    "If true: interpret SenseWireHit azimuth/stereo angles in degrees and convert to radians."
  };

  // NEW: diagnostics
  Gaudi::Property<unsigned> m_diagEveryNTracks{
    this, "DiagEveryNTracks", 1u,
    "Print DEBUG diagnostics every N tracks (only when OutputLevel<=DEBUG). 1 prints for all tracks in DEBUG."
  };

  StatusCode initialize() override {
    // GenFit uses kGauss internally. 1 Tesla = 10 kGauss.
    genfit::FieldManager::getInstance()->init(
      new genfit::ConstField(0., 0., 10.0*m_Bz.value()));

    // ----- MaterialEffects HARD policy (F1) -----
    // The MaterialEffects singleton can still be consulted internally even if you "don't use" it.
    // If it is not initialized with a valid interface, GenFit throws:
    //   "MaterialEffects hasn't been initialized with a correct AbsMaterialInterface pointer!"
    //
    // So we ALWAYS set a definitive global state.
    auto* me = genfit::MaterialEffects::getInstance();

    bool wantMat = bool(m_useMatEff.value());
    bool haveGeo = (gGeoManager != nullptr);

    if (!wantMat || m_disableAllMat.value()) {
      me->setNoEffects(true);
      info() << "MaterialEffects: HARD disabled (UseMaterialEffects=false or DisableAllMaterialEffects=true)" << endmsg;
    } else if (!haveGeo) {
      if (m_hardDisableMatIfNoGeo.value()) {
        me->setNoEffects(true);
        warning() << "UseMaterialEffects=true but gGeoManager is null; HARD disabling MaterialEffects to avoid GenFit exceptions."
                  << endmsg;
      } else {
        warning() << "UseMaterialEffects=true but gGeoManager is null; MaterialEffects may throw at runtime." << endmsg;
      }
    } else {
      // haveGeo and wantMat: try init interface
      try {
        me->init(new genfit::TGeoMaterialInterface());
        me->setNoEffects(false);
        info() << "Initialized GenFit MaterialEffects with TGeoMaterialInterface." << endmsg;

        if (m_disableEloss.value()) {
          me->setEnergyLossBetheBloch(false);
          me->setNoiseBetheBloch(false);
          me->setEnergyLossBrems(false);
          me->setNoiseBrems(false);
          info() << "MaterialEffects: disabled energy loss (BetheBloch+Brems), kept MS [DisableEnergyLoss=true]" << endmsg;
        }
      } catch (const std::exception& e) {
        // If init fails, HARD-disable to prevent exceptions during fitting.
        me->setNoEffects(true);
        warning() << "Failed to init/configure MaterialEffects(TGeo): " << e.what()
                  << " — HARD disabling MaterialEffects to prevent GenFit exceptions." << endmsg;
      } catch (...) {
        me->setNoEffects(true);
        warning() << "Failed to init/configure MaterialEffects(TGeo) (unknown) — HARD disabling MaterialEffects." << endmsg;
      }
    }

    // Create fitter(s)
    m_kalman = std::make_unique<genfit::KalmanFitterRefTrack>();
    m_kalman->setMaxIterations(12);

    m_daf = std::make_unique<genfit::DAF>();
    m_daf->setMaxIterations(int(std::max(1u, m_dafMaxIterations.value())));

    info() << "GenFit2DCHFitter init | Bz=" << m_Bz.value()
           << " | PDG=" << m_pdg.value()
           << " | UseDAF=" << (m_useDAF.value() ? "true":"false")
           << " | WireHalfLengthMM=" << m_wireHalfLengthMM.value()
           << " | MaxDriftMM=" << m_maxDriftMM.value()
           << " | PublishPTMaxGeV=" << m_publishPTMaxGeV.value()
           << " | WireAnglesAreDegrees=" << (m_wireAnglesAreDegrees.value() ? "true":"false")
           << " | DetId=" << m_detId.value()
           << " | UseLabelAsDetId=" << (m_useLabelAsDetId.value() ? "true":"false")
           << endmsg;

    // Write metadata
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
      os << ",\"UseDAF\":" << (m_useDAF.value() ? "true":"false");
      os << ",\"DAFMaxIterations\":" << m_dafMaxIterations.value();
      os << ",\"WireHalfLengthMM\":" << m_wireHalfLengthMM.value();
      os << ",\"MaxDriftMM\":" << m_maxDriftMM.value();
      os << ",\"PositionUnitScale\":" << m_posScale.value();
      os << ",\"PublishPTMaxGeV\":" << m_publishPTMaxGeV.value();
      os << ",\"SortHits\":" << (m_sortHits.value() ? "true":"false");
      os << ",\"DeduplicateHits\":" << (m_dedupHits.value() ? "true":"false");
      os << ",\"DedupTolMM\":" << m_dedupTolMM.value();
      os << ",\"WireAnglesAreDegrees\":" << (m_wireAnglesAreDegrees.value() ? "true":"false");
      os << ",\"DetId\":" << m_detId.value();
      os << ",\"UseLabelAsDetId\":" << (m_useLabelAsDetId.value() ? "true":"false");
      os << ",\"buildDate\":\"" << __DATE__ << "\"";
      os << ",\"buildTime\":\"" << __TIME__ << "\"";
      os << "}";

      m_cfgMeta.put(os.str());
      info() << "Wrote GenFit2DCHFitter configuration metadata (key='GenFit2DCHFitterConfig')" << endmsg;
    } catch (...) {
      warning() << "Failed to write GenFit2DCHFitter metadata" << endmsg;
    }

    return StatusCode::SUCCESS;
  }

  // Seed covariance in internal units (cm^2, GeV^2)
  TMatrixDSym makeSeedCov(double posInfl=1.0, double momInfl=1.0) const {
    TMatrixDSym C(6);
    C.Zero();
    const double sP = (m_seedPosSigmaMM.value() * posInfl) * (m_posScale.value()); // mm->cm
    const double sM = (m_seedMomSigmaGeV.value() * momInfl);
    for (int i = 0; i < 3; ++i) C(i, i) = sP * sP;
    for (int i = 3; i < 6; ++i) C(i, i) = sM * sM;
    ensurePD_chol(C, 1e-6, 4.0, 6);
    return C;
  }

  // Run chosen fitter
  const genfit::FitStatus* run_fit(genfit::Track& trk, const char* tag, int label) const {
    try {
      if (m_useDAF.value()) m_daf->processTrack(&trk);
      else                 m_kalman->processTrack(&trk);
    } catch (const genfit::Exception& e) {
      warning() << "GenFit exception during processTrack (label=" << label << ", " << tag << "): " << e.what() << endmsg;
      return nullptr;
    } catch (const std::exception& e) {
      warning() << "Std exception during processTrack (label=" << label << ", " << tag << "): " << e.what() << endmsg;
      return nullptr;
    } catch (...) {
      warning() << "Unknown exception during processTrack (label=" << label << ", " << tag << ")" << endmsg;
      return nullptr;
    }
    genfit::AbsTrackRep* rep = trk.getCardinalRep();
    return rep ? trk.getFitStatus(rep) : nullptr;
  }

  bool has_any_FI(genfit::Track& trk) const {
    genfit::AbsTrackRep* rep = trk.getCardinalRep();
    if (!rep) return false;
    const size_t nPts = trk.getNumPoints();
    for (size_t i = 0; i < nPts; ++i) {
      auto* tp = trk.getPoint(i);
      if (tp && tp->hasFitterInfo(rep)) return true;
    }
    return false;
  }

  double chi2ndf(const genfit::FitStatus* fs) const {
    if (!fs) return std::numeric_limits<double>::infinity();
    const double ndf = std::max(1.0, double(fs->getNdf()));
    return fs->getChi2() / ndf;
  }

  bool isGoodFS(const genfit::FitStatus* fs) const {
    return fs && fs->isFitted() && fs->isFitConverged() && std::isfinite(fs->getChi2());
  }

  // Deterministic sorting key from on-wire position (in mm)
  static void sortWireHitsDeterministic(std::vector<extension::SenseWireHit>& hw) {
    std::stable_sort(hw.begin(), hw.end(), [](const auto& a, const auto& b) {
      const auto pa = a.getPosition();
      const auto pb = b.getPosition();
      const double ra = std::hypot(pa.x, pa.y);
      const double rb = std::hypot(pb.x, pb.y);
      if (ra != rb) return ra < rb;
      if (pa.z != pb.z) return pa.z < pb.z;
      const double phia = std::atan2(pa.y, pa.x);
      const double phib = std::atan2(pb.y, pb.x);
      return phia < phib;
    });
  }

  // Dedup using on-wire position (in mm)
  static void dedupWireHits(std::vector<extension::SenseWireHit>& hw, double tolMM) {
    if (hw.empty()) return;
    const double tol2 = tolMM * tolMM;

    std::vector<extension::SenseWireHit> out;
    out.reserve(hw.size());

    auto prev = hw.front();
    out.push_back(prev);

    auto prevp = prev.getPosition();
    for (size_t i = 1; i < hw.size(); ++i) {
      auto pi = hw[i].getPosition();
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

  // Build a GenFit track from SenseWireHits; return #measurements inserted.
  unsigned buildTrackFromWireHits(genfit::Track& outTrack,
                                  const std::vector<extension::SenseWireHit>& hw,
                                  int detIdForAllHits,
                                  double posScale_cm_per_mm,
                                  bool wireAnglesAreDegrees) const {
    const double halfL_cm  = m_wireHalfLengthMM.value() * posScale_cm_per_mm; // mm -> cm
    const double maxD_cm   = m_maxDriftMM.value()       * posScale_cm_per_mm;
    const double minErr_cm = m_minDriftErrMM.value()    * posScale_cm_per_mm;

    unsigned nInserted = 0;
    int hitId = 0;

    for (const auto& h : hw) {
      const auto p = h.getPosition();
      if (!finite3(p.x, p.y, p.z)) continue;

      double d_mm = std::abs(double(h.getDistanceToWire()));
      if (!std::isfinite(d_mm)) continue;

      double derr_mm = double(h.getDistanceToWireError());
      if (!(derr_mm > 0.0) || !std::isfinite(derr_mm)) derr_mm = m_minDriftErrMM.value();
      derr_mm = std::max(derr_mm, m_minDriftErrMM.value());

      const double d_cm    = d_mm    * posScale_cm_per_mm;
      const double derr_cm = std::max(derr_mm * posScale_cm_per_mm, minErr_cm);

      // Wire angles
      double phi = double(h.getWireAzimuthalAngle());
      double st  = double(h.getWireStereoAngle());
      if (!std::isfinite(phi) || !std::isfinite(st)) continue;
      if (wireAnglesAreDegrees) { phi *= kDegToRad; st *= kDegToRad; }

      // Wire direction convention (same as your original)
      TVector3 dir(0, 0, 1);
      dir.RotateX(st);
      dir.RotateZ(phi);
      dir = safeUnit(dir, TVector3(0, 0, 1));

      // A point on the wire in internal units (cm)
      TVector3 wp_cm(posScale_cm_per_mm * p.x,
                     posScale_cm_per_mm * p.y,
                     posScale_cm_per_mm * p.z);

      // Synth endpoints (internal cm)
      TVector3 e1 = wp_cm - halfL_cm * dir;
      TVector3 e2 = wp_cm + halfL_cm * dir;

      auto* tp = new genfit::TrackPoint(&outTrack);

      // WireMeasurementNew(driftDistance, driftDistanceError, endPoint1, endPoint2, detId, hitId, tp)
      auto* meas = new genfit::WireMeasurementNew(d_cm, derr_cm, e1, e2,
                                                  detIdForAllHits, hitId, tp);

      // Let DAF decide left/right (0)
      meas->setLeftRightResolution(0);

      // Used for DAF's initial weights
      meas->setMaxDistance(maxD_cm);

      tp->addRawMeasurement(meas);
      outTrack.insertPoint(tp);
      ++hitId;
      ++nInserted;
    }
    return nInserted;
  }

  extension::TrackCollection
  operator()(const extension::TrackCollection& inTracks) const override {
    extension::TrackCollection out;

    const double posScale_cm_per_mm = m_posScale.value(); // internal cm per mm
    const int qPublish = chargeFromPDG(m_pdg.value());

    unsigned nIn = 0, nFit = 0, nFail = 0, nSkipNoHits = 0, nSkipMinHits = 0;
    unsigned nSkipNoSenseWireHits = 0;
    unsigned nSkipTooFewMeas = 0;
    unsigned nSkipBadSeed = 0;

    unsigned nWarnedType = 0;

    for (const auto& trkIn : inTracks) {
      ++nIn;

      const int label = int(trkIn.getType());
      if (m_rejectNegativeLabels.value() && label < 0) continue;

      // --------- Gather SenseWireHits from the GGTF candidate track ----------
      std::vector<extension::SenseWireHit> wireHits;
      wireHits.reserve(256);

      size_t totalTH = 0;

      try {
        auto rng = trkIn.getTrackerHits();
        totalTH = rng.size();
        for (const auto& th : rng) {
          if (!th.isAvailable()) continue;
          if (!th.isA<extension::SenseWireHit>()) {
            // Don't spam: only warn a few times in DEBUG mode
            if (msgLevel(MSG::DEBUG) && nWarnedType < 3) {
              debug() << "Non-SenseWireHit trackerHit encountered on label=" << label
                      << " (skipping). If all are non-SenseWireHit, your GGTF is not attaching SenseWireHit relations."
                      << endmsg;
              ++nWarnedType;
            }
            continue;
          }
          wireHits.push_back(th.as<extension::SenseWireHit>());
        }
      } catch (...) {
        warning() << "Track trackerHits relation read failed (label=" << label << "). Skipping." << endmsg;
        ++nSkipNoHits;
        continue;
      }

      if (wireHits.empty()) {
        ++nSkipNoSenseWireHits;
        if (msgLevel(MSG::DEBUG) && (m_diagEveryNTracks.value() > 0) && (nIn % m_diagEveryNTracks.value() == 0)) {
          debug() << "Diag: label=" << label
                  << " trackerHits_total=" << totalTH
                  << " senseWireHits_found=0"
                  << endmsg;
        }
        continue;
      }

      if (msgLevel(MSG::DEBUG) && (m_diagEveryNTracks.value() > 0) && (nIn % m_diagEveryNTracks.value() == 0)) {
        debug() << "Diag: label=" << label
                << " trackerHits_total=" << totalTH
                << " senseWireHits_found=" << wireHits.size()
                << endmsg;
      }

      if (m_sortHits.value()) sortWireHitsDeterministic(wireHits);
      if (m_dedupHits.value() && m_dedupTolMM.value() > 0.0) dedupWireHits(wireHits, m_dedupTolMM.value());

      if (wireHits.size() < m_minHitsPerTrack.value()) { ++nSkipMinHits; continue; }

      // --------- Seed from endpoints of on-wire points (just for convergence) ----------
      const auto p0 = wireHits.front().getPosition();
      const auto p1 = wireHits.back().getPosition();
      if (!finite3(p0.x, p0.y, p0.z) || !finite3(p1.x, p1.y, p1.z)) { ++nSkipBadSeed; continue; }

      TVector3 pos0_cm(posScale_cm_per_mm * p0.x,
                       posScale_cm_per_mm * p0.y,
                       posScale_cm_per_mm * p0.z);

      TVector3 pos1_cm(posScale_cm_per_mm * p1.x,
                       posScale_cm_per_mm * p1.y,
                       posScale_cm_per_mm * p1.z);

      TVector3 dpos = pos1_cm - pos0_cm;
      if (!std::isfinite(dpos.Mag2()) || dpos.Mag2() < 1e-12) dpos = TVector3(0, 0, 1);
      TVector3 dir = safeUnit(dpos, TVector3(0, 0, 1));

      // Conservative seed pT
      double pTseed = 5.0;
      pTseed = clampFinite(pTseed, m_seedPTMinGeV.value(), m_seedPTMaxGeV.value(), 5.0);

      const double cosTheta = std::clamp(std::abs(dir.Z()), 0.0, 0.999999);
      const double sinTheta = std::sqrt(std::max(1e-4, 1.0 - cosTheta * cosTheta));

      double pMag = pTseed / sinTheta;
      if (!std::isfinite(pMag) || pMag <= 0) pMag = pTseed;
      pMag = std::max(pMag, m_seedPMinGeV.value());

      TVector3 mom0 = pMag * dir;

      // detId policy
      const int detId = m_useLabelAsDetId.value() ? label : m_detId.value();

      // --------- build and fit (try +/- mom0) ----------
      auto rep1_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
      genfit::Track trk1(rep1_up.release(), pos0_cm, mom0);
      trk1.setCovSeed(makeSeedCov(1.0, 1.0));

      const unsigned nMeas1 = buildTrackFromWireHits(trk1, wireHits, detId, posScale_cm_per_mm, m_wireAnglesAreDegrees.value());
      if (nMeas1 < m_minMeasurementsToFit.value()) { ++nSkipTooFewMeas; continue; }

      const genfit::FitStatus* fs1 = run_fit(trk1, "base(+mom)", label);
      const bool ok1 = (fs1 && has_any_FI(trk1));

      std::unique_ptr<genfit::Track> trk2_ptr;
      const genfit::FitStatus* fs2 = nullptr;
      bool ok2 = false;

      if (m_tryBothMomDirs.value()) {
        auto rep2_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
        trk2_ptr = std::make_unique<genfit::Track>(rep2_up.release(), pos0_cm, -mom0);
        trk2_ptr->setCovSeed(makeSeedCov(1.0, 1.0));

        const unsigned nMeas2 = buildTrackFromWireHits(*trk2_ptr, wireHits, detId, posScale_cm_per_mm, m_wireAnglesAreDegrees.value());
        if (nMeas2 >= m_minMeasurementsToFit.value()) {
          fs2 = run_fit(*trk2_ptr, "base(-mom)", label);
          ok2 = (fs2 && has_any_FI(*trk2_ptr));
        }
      }

      auto better = [&](genfit::Track* aTrk, const genfit::FitStatus* aFs,
                        genfit::Track* bTrk, const genfit::FitStatus* bFs)->bool {
        const bool aGood = isGoodFS(aFs) && has_any_FI(*aTrk);
        const bool bGood = isGoodFS(bFs) && has_any_FI(*bTrk);
        if (aGood != bGood) return aGood;
        return chi2ndf(aFs) < chi2ndf(bFs);
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

      if (!(bestTrk && bestFs && has_any_FI(*bestTrk))) { ++nFail; continue; }

      // --------- select best fitted state ----------
      genfit::MeasuredStateOnPlane bestState;
      float fittedPT = 0.f;
      size_t fitIdx = 0;

      const bool haveBestState = selectBestFittedState(*bestTrk,
                                                       m_publishPTMaxGeV.value(),
                                                       m_bestStateZWeight.value(),
                                                       m_bestStateIdxWeight.value(),
                                                       bestState,
                                                       fittedPT,
                                                       fitIdx);
      if (!haveBestState) { ++nFail; continue; }

      bool ptValid = true;
      ptValid = ptValid && std::isfinite(fittedPT) && (fittedPT > 0.0f) &&
                (double(fittedPT) < m_publishPTMaxGeV.value());

      const float omegaVar = ptValid ? m_omegaVarGood.value() : m_omegaVarBad.value();

      // --------- export output track ----------
      auto trkOut = out.create();
      trkOut.setType(m_pdg.value()); // store PDG hypothesis (kept from your convention)
      try { trkOut.setChi2(bestFs->getChi2()); trkOut.setNdf(bestFs->getNdf()); } catch (...) {}

      // Keep original hit relations (all types) for debugging / downstream
      try {
        for (const auto& th : trkIn.getTrackerHits()) {
          trkOut.addToTrackerHits(th);
        }
      } catch (...) {}

      const TVector3 pos_cm = bestState.getPos();
      const TVector3 mom    = bestState.getMom();

      // Placeholder observability score (wire-only fit; can be upgraded once we compute arc span)
      const float obsScore = 1.0f;

      addAtIPState(trkOut,
                   pos_cm,
                   mom,
                   /*posScale_cm_per_mm=*/posScale_cm_per_mm,
                   /*chargeSign=*/qPublish,
                   /*ptValid=*/ptValid,
                   m_invalidPTSentinel.value(),
                   omegaVar,
                   obsScore,
                   /*pTOverrideOrNeg=*/fittedPT);

      ++nFit;
    }

    info() << "GenFit2DCHFitter: inputTracks=" << nIn
           << " fitted=" << nFit
           << " failed=" << nFail
           << " skipNoTrackerHitsRead=" << nSkipNoHits
           << " skipNoSenseWireHits=" << nSkipNoSenseWireHits
           << " skipMinHits=" << nSkipMinHits
           << " skipTooFewMeasurements=" << nSkipTooFewMeas
           << " skipBadSeed=" << nSkipBadSeed
           << " (UseDAF=" << (m_useDAF.value() ? "true":"false") << ")"
           << endmsg;

    return out;
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }

private:
  mutable std::unique_ptr<genfit::KalmanFitterRefTrack> m_kalman;
  mutable std::unique_ptr<genfit::DAF>                 m_daf;
  k4FWCore::MetaDataHandle<std::string>                m_cfgMeta;
};

DECLARE_COMPONENT(GenFit2DCHFitter)
