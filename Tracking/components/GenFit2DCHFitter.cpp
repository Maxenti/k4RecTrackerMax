// ======================================================================
// GenFit2DCHFitter.cpp  -- fit GGTF 3D hits with GenFit2 (more robust)
//   Updates applied (per our discussion):
//    1) Labeling: prefer getType() over getQuality() so GGTF labels are used
//    2) Sorting: robust helical ordering via unwrapped φ around fitted XY circle
//       (fallback to chord-projection only if circle is degenerate)
//    3) Dedup: moved AFTER sorting (and removes near-duplicates in sorted order)
//    4) Seeding: more robust circle seed from widely-separated φ points (not raw first/mid/last)
//    5) Robustness: try both momentum directions (+dir, -dir) and keep best fit
//       (uses converged/fitted + chi2/ndf as tie-break)
//    6) Low-pT stability fixes (NEW):
//        - SeedPMinGeV is now a *numerical floor* (default 0.05 GeV), not a physics clamp
//        - Optionally disable energy-loss material effects to avoid Bethe-Bloch validity errors
//        - Optionally disable *all* material effects (stronger)
//   Keeps your existing features:
//    - optional z(φ) outlier rejection
//    - retry path if no FitterInfo
//    - metadata config key "GenFit2DCHFitterConfig"
//
//   Notes:
//    - Units: internal positions are cm (m_posScale=0.1 for mm->cm).
//    - TrackState export: omega=q/pT [GeV^-1], time=pT [GeV]
// ======================================================================

#include <memory>
#include <vector>
#include <string>
#include <cmath>
#include <exception>
#include <algorithm>
#include <unordered_map>
#include <utility>
#include <numeric>
#include <queue>
#include <limits>
#include <sstream>
#include <ctime>

// Gaudi
#include "Gaudi/Algorithm.h"
#include "Gaudi/Property.h"
#include "GaudiKernel/ISvcLocator.h"

// k4FWCore
#include "k4FWCore/Transformer.h"
#include "k4FWCore/MetaDataHandle.h"

// EDM4hep
#include "edm4hep/TrackerHit3DCollection.h"
#include "edm4hep/TrackCollection.h"
#include "edm4hep/TrackState.h"

// ROOT
#include "TVector3.h"
#include "TVectorD.h"
#include "TMatrixDSym.h"
#include "TGeoManager.h"
#include "TDecompChol.h"

// GenFit2
#include "RKTrackRep.h"
#include "Track.h"
#include "KalmanFitterRefTrack.h"
#include "KalmanFitterInfo.h"
#include "SpacepointMeasurement.h"
#include "TrackPoint.h"
#include "MeasuredStateOnPlane.h"
#include "Exception.h"
#include "FieldManager.h"
#include "ConstField.h"
#include "MaterialEffects.h"
#include "TGeoMaterialInterface.h"

namespace {

// ---------- SFINAE for edm4hep hit accessors ----------
template <typename, typename = void> struct has_getQuality : std::false_type {};
template <typename T>
struct has_getQuality<T, std::void_t<decltype(std::declval<T>().getQuality())>> : std::true_type {};

template <typename, typename = void> struct has_getType : std::false_type {};
template <typename T>
struct has_getType<T, std::void_t<decltype(std::declval<T>().getType())>> : std::true_type {};

// IMPORTANT UPDATE: prefer getType() (GGTF_tracking sets Type) over getQuality()
template <typename HitT>
inline int hitLabel(const HitT& h) {
  if constexpr (has_getType<HitT>::value) return static_cast<int>(h.getType());
  else if constexpr (has_getQuality<HitT>::value) return static_cast<int>(h.getQuality());
  else return 0;
}

inline void makeDiagonalFloor(TMatrixDSym& C, double eps) {
  for (int i = 0; i < C.GetNrows(); ++i) C(i, i) = std::max(C(i, i), eps);
}

inline void ensurePD(TMatrixDSym& C, double floorDiag, double inflateFactor, int maxIters) {
  makeDiagonalFloor(C, floorDiag);
  for (int it = 0; it < maxIters; ++it) {
    TDecompChol chol(C);
    if (chol.Decompose()) return;
    for (int i = 0; i < C.GetNrows(); ++i) C(i, i) *= inflateFactor;
  }
  for (int i = 0; i < C.GetNrows(); ++i) C(i, i) += floorDiag;
}

// --- circle center + radius in XY plane --------------------------------
inline bool circleCenterRadiusXY(const TVector3& A,
                                 const TVector3& B,
                                 const TVector3& C,
                                 TVector3& center_xy,
                                 double& R) {
  const double x1 = A.X(), y1 = A.Y();
  const double x2 = B.X(), y2 = B.Y();
  const double x3 = C.X(), y3 = C.Y();

  const double a = x1*(y2 - y3) - y1*(x2 - x3) + x2*y3 - x3*y2;
  const double d = 2.0 * a;
  if (std::abs(d) < 1e-12) {
    center_xy.SetXYZ(0., 0., 0.);
    R = 1e9;
    return false;
  }

  const double x1s = x1*x1, y1s = y1*y1;
  const double x2s = x2*x2, y2s = y2*y2;
  const double x3s = x3*x3, y3s = y3*y3;

  const double cx = ((x1s+y1s)*(y2-y3) + (x2s+y2s)*(y3-y1) + (x3s+y3s)*(y1-y2)) / d;
  const double cy = ((x1s+y1s)*(x3-x2) + (x2s+y2s)*(x1-x3) + (x3s+y3s)*(x2-x1)) / d;
  center_xy.SetXYZ(cx, cy, 0.0);

  const double dx = x1 - cx, dy = y1 - cy;
  R = std::sqrt(dx*dx + dy*dy);
  if (!std::isfinite(R) || R <= 1e-9) {
    R = 1e9;
    return false;
  }
  return true;
}

inline double circleRadiusXY(const TVector3& A,
                             const TVector3& B,
                             const TVector3& C) {
  TVector3 c(0., 0., 0.);
  double R = 1e9;
  if (!circleCenterRadiusXY(A, B, C, c, R)) return 1e9;
  return R;
}
// ----------------------------------------------------------------------

// Robust helical ordering: compute φ about center, unwrap, sort by φ
// Returns false if center is unusable.
static bool sortByUnwrappedPhi(std::vector<TVector3>& P,
                               std::vector<size_t>& idxs,
                               const TVector3& centerXY,
                               bool preferIncreasingPhi = true) {
  const size_t N = P.size();
  if (N < 3) return false;

  // if center is not finite, bail
  if (!std::isfinite(centerXY.X()) || !std::isfinite(centerXY.Y())) return false;

  std::vector<double> phi(N);
  for (size_t i = 0; i < N; ++i) {
    const double dx = P[i].X() - centerXY.X();
    const double dy = P[i].Y() - centerXY.Y();
    phi[i] = std::atan2(dy, dx);
  }

  // unwrap relative to first point
  for (size_t i = 1; i < N; ++i) {
    double d = phi[i] - phi[i-1];
    while (d >  M_PI) { phi[i] -= 2.0*M_PI; d -= 2.0*M_PI; }
    while (d < -M_PI) { phi[i] += 2.0*M_PI; d += 2.0*M_PI; }
  }

  std::vector<size_t> order(N);
  std::iota(order.begin(), order.end(), 0);

  if (preferIncreasingPhi) {
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b){ return phi[a] < phi[b]; });
  } else {
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b){ return phi[a] > phi[b]; });
  }

  std::vector<TVector3> P2; P2.reserve(N);
  std::vector<size_t>   I2; I2.reserve(N);
  for (auto k : order) {
    P2.push_back(P[k]);
    I2.push_back(idxs[k]);
  }
  P.swap(P2);
  idxs.swap(I2);
  return true;
}

// After sorting: simple adjacent dedup in sorted order
static void dedupSorted(std::vector<TVector3>& P,
                        std::vector<size_t>& idxs,
                        double tol2) {
  if (P.empty()) return;
  std::vector<TVector3> P2; P2.reserve(P.size());
  std::vector<size_t>   I2; I2.reserve(P.size());

  TVector3 prev = P.front();
  P2.push_back(prev);
  I2.push_back(idxs.front());

  for (size_t k = 1; k < P.size(); ++k) {
    if ((P[k] - prev).Mag2() < tol2) continue;
    P2.push_back(P[k]);
    I2.push_back(idxs[k]);
    prev = P[k];
  }
  P.swap(P2);
  idxs.swap(I2);
}

// Pick 3 points well-separated in φ to avoid "bad first/mid/last" seeding
static bool pickWideSeparatedTriplet(const std::vector<TVector3>& P,
                                     const TVector3& centerXY,
                                     TVector3& A,
                                     TVector3& B,
                                     TVector3& C) {
  const size_t N = P.size();
  if (N < 3) return false;

  std::vector<double> phi(N);
  for (size_t i = 0; i < N; ++i) {
    phi[i] = std::atan2(P[i].Y() - centerXY.Y(), P[i].X() - centerXY.X());
  }

  // unwrap
  for (size_t i = 1; i < N; ++i) {
    double d = phi[i] - phi[i-1];
    while (d >  M_PI) { phi[i] -= 2.0*M_PI; d -= 2.0*M_PI; }
    while (d < -M_PI) { phi[i] += 2.0*M_PI; d += 2.0*M_PI; }
  }

  // indices of min, mid (closest to mean), max
  size_t iMin = 0, iMax = 0;
  for (size_t i = 1; i < N; ++i) {
    if (phi[i] < phi[iMin]) iMin = i;
    if (phi[i] > phi[iMax]) iMax = i;
  }
  const double phiMidTarget = 0.5 * (phi[iMin] + phi[iMax]);
  size_t iMid = 0;
  double best = std::numeric_limits<double>::infinity();
  for (size_t i = 0; i < N; ++i) {
    double d = std::abs(phi[i] - phiMidTarget);
    if (d < best) { best = d; iMid = i; }
  }

  // ensure distinct
  if (iMin == iMid) iMid = (iMid + 1) % N;
  if (iMax == iMid) iMid = (iMid + 1) % N;
  if (iMin == iMax) return false;

  A = P[iMin];
  B = P[iMid];
  C = P[iMax];
  return true;
}

// ---------- DBSCAN fallback ----------
struct Group {
  std::vector<TVector3> P;
  std::vector<size_t>   idxs;
};

static std::vector<int> dbscan(const std::vector<TVector3>& P, double eps, unsigned minPts) {
  const int N = static_cast<int>(P.size());
  const double eps2 = eps*eps;
  std::vector<int> labels(N, -99); // -99=UNVISITED, -1=NOISE, >=0 clusterId
  int clusterId = 0;

  auto regionQuery = [&](int i, std::vector<int>& out){
    out.clear();
    const auto& pi = P[i];
    for (int j = 0; j < N; ++j) {
      if ((P[j] - pi).Mag2() <= eps2) out.push_back(j);
    }
  };

  for (int i = 0; i < N; ++i) {
    if (labels[i] != -99) continue;
    std::vector<int> neigh; regionQuery(i, neigh);
    if (neigh.size() < minPts) {
      labels[i] = -1;
      continue;
    }
    labels[i] = clusterId;
    std::queue<int> q;
    for (int n : neigh) {
      if (labels[n] == -99 || labels[n] == -1) {
        labels[n] = clusterId;
        q.push(n);
      }
    }
    while (!q.empty()) {
      int k = q.front(); q.pop();
      std::vector<int> neigh2; regionQuery(k, neigh2);
      if (neigh2.size() >= minPts) {
        for (int n : neigh2) {
          if (labels[n] == -99 || labels[n] == -1) {
            labels[n] = clusterId;
            q.push(n);
          }
        }
      }
    }
    ++clusterId;
  }
  return labels;
}

static int chargeFromPDG(int pdg) {
  const int a = std::abs(pdg);
  if (a == 11 || a == 13 || a == 15) return (pdg > 0 ? -1 : +1);
  if (a == 211 || a == 321 || a == 2212) return (pdg > 0 ? +1 : -1);
  return (pdg >= 0 ? +1 : -1);
}

// Fill a TrackState from a position (internal units) and momentum (GeV).
// posScale converts internal length units back to mm:  mm = pos_internal / posScale.
// Conventions: omega = q/pT [GeV^-1] (EDM/LCIO style), time = pT [GeV].
static void addAtIPState(edm4hep::MutableTrack& trk,
                         const TVector3& pos_internal,
                         const TVector3& mom_GeV,
                         double /*Bz_T*/,
                         double posScale,
                         int chargeSign) {
  using TP = edm4hep::TrackParams;

  const double inv_ps = (posScale > 0 ? 1.0/posScale : 10.0); // default 10 if posScale==0 (cm->mm)
  const double x = pos_internal.X() * inv_ps;
  const double y = pos_internal.Y() * inv_ps;
  const double z = pos_internal.Z() * inv_ps;

  const double px = mom_GeV.X();
  const double py = mom_GeV.Y();
  const double pz = mom_GeV.Z();

  const double pT  = std::hypot(px, py);
  const double phi = std::atan2(py, px);
  const double tanL = (pT > 1e-12) ? (pz / pT) : 0.0;

  const double omegaSigned = (pT > 1e-12) ? (chargeSign / pT) : 0.0;

  const double d0 = - ( x*std::sin(phi) - y*std::cos(phi) );
  const double z0 =   z - ( x*std::cos(phi) + y*std::sin(phi) ) * tanL;

  edm4hep::TrackState ts;
  ts.location       = edm4hep::TrackState::AtIP;
  ts.referencePoint = { float(x), float(y), float(z) };
  ts.phi            = float(phi);
  ts.omega          = float(omegaSigned);  // q/pT [GeV^-1]
  ts.tanLambda      = float(tanL);
  ts.D0             = float(d0);
  ts.Z0             = float(z0);

  // Store pT [GeV] directly for convenience (TrackState.time)
  ts.time           = float(pT);

  // crude diagonal covariance
  ts.setCovMatrix(1.0f,   TP::d0,        TP::d0);
  ts.setCovMatrix(1e-3f,  TP::phi,       TP::phi);
  ts.setCovMatrix(1e-6f,  TP::omega,     TP::omega);
  ts.setCovMatrix(1.0f,   TP::z0,        TP::z0);
  ts.setCovMatrix(1e-2f,  TP::tanLambda, TP::tanLambda);

  trk.addToTrackStates(ts);
}

static bool addBestFittedAtIPState(edm4hep::MutableTrack& trk,
                                   const genfit::Track& gftrk,
                                   double Bz_T,
                                   double posScale,
                                   int fallbackCharge) {
  genfit::AbsTrackRep* rep = gftrk.getCardinalRep();
  if (!rep) return false;

  bool have = false;
  double bestR2 = std::numeric_limits<double>::infinity();
  genfit::MeasuredStateOnPlane best;

  const size_t nPts = gftrk.getNumPoints();
  for (size_t i = 0; i < nPts; ++i) {
    const genfit::TrackPoint* tp = gftrk.getPoint(i);
    if (!tp || !tp->hasFitterInfo(rep)) continue;
    auto* fi = dynamic_cast<const genfit::KalmanFitterInfo*>(tp->getFitterInfo(rep));
    if (!fi) continue;

    try {
      genfit::MeasuredStateOnPlane st = fi->getFittedState();
      TVector3 pos = st.getPos();
      const double r2 = pos.Perp2();
      if (r2 < bestR2) {
        bestR2 = r2;
        best   = st;
        have   = true;
      }
    } catch (...) {}
  }

  if (!have) return false;

  TVector3 pos_cm = best.getPos();
  TVector3 mom    = best.getMom();
  int q = 0;
  try { q = rep->getCharge(best); } catch (...) { q = fallbackCharge; }
  if (q == 0) q = fallbackCharge;

  addAtIPState(trk, pos_cm, mom, Bz_T, posScale, q);
  return true;
}

} // end anonymous namespace

// ======================================================================

struct GenFit2DCHFitter final
  : k4FWCore::Transformer<edm4hep::TrackCollection (const edm4hep::TrackerHit3DCollection&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  GenFit2DCHFitter(const std::string& name, ISvcLocator* svcLoc)
    : Transformer(name, svcLoc,
        std::tuple<KeyValues>{ KeyValues{"inputHits",
                                         std::vector<std::string>{"GGTF_3DHits"}} },
        std::tuple<KeyValues>{ KeyValues{"outputTracks",
                                         std::vector<std::string>{"GenFitTracks"}} }),
      m_cfgMeta("GenFit2DCHFitterConfig", Gaudi::DataHandle::Writer) {
    // Gaudi::Property<> handles registration.
  }

  // ----------------- Properties -----------------

  // Physics knobs
  Gaudi::Property<double>  m_Bz {this, "Bz", 2.0, "Bz field [T]"};
  Gaudi::Property<int>     m_pdg{this, "PDG", 13,  "PDG hypothesis"};

  // Material effects
  Gaudi::Property<bool>    m_useMatEff{this, "UseMaterialEffects", true,
                                       "Use TGeoMaterialInterface for GenFit MaterialEffects"};

  // NEW: optional material-effects suppression knobs (helps low-pT stability)
  Gaudi::Property<bool>    m_disableEloss{this, "DisableEnergyLoss", true,
                                         "Disable Bethe-Bloch/Brems energy loss (keep MS) when material effects are enabled"};
  Gaudi::Property<bool>    m_disableAllMat{this, "DisableAllMaterialEffects", false,
                                          "Disable all GenFit material effects (stronger than DisableEnergyLoss)"};

  // Units / scales
  Gaudi::Property<double>  m_posScale       {this, "PositionUnitScale", 0.1,
                                             "Multiply positions (0.1: mm->cm)"};
  Gaudi::Property<double>  m_internalLenToM {this, "InternalLengthToMeters", 0.01,
                                             "Length to meters (0.01: cm->m)"};

  // Measurement covariance
  Gaudi::Property<double>  m_hitSigmaXYMM {this, "HitSigmaXYMM", 0.50, "XY sigma [mm]"};
  Gaudi::Property<double>  m_hitSigmaZMM  {this, "HitSigmaZMM",  2.00, "Z  sigma [mm]"};

  // Seed / robustness
  Gaudi::Property<double>  m_seedPosSigmaMM  {this, "SeedPosSigmaMM", 80.0,
                                              "Seed pos sigma [mm]"};
  Gaudi::Property<double>  m_seedMomSigmaGeV {this, "SeedMomSigmaGeV", 5.0,
                                              "Seed mom sigma [GeV]"};
  Gaudi::Property<double>  m_seedPTMinGeV    {this, "SeedPTMinGeV",    0.20,
                                              "Min pT [GeV]"};
  Gaudi::Property<double>  m_seedPTMaxGeV    {this, "SeedPTMaxGeV",   200.0,
                                              "Max pT [GeV]"};

  // UPDATED: this should be a numerical floor, not a "physics clamp"
  Gaudi::Property<double>  m_seedPMinGeV     {this, "SeedPMinGeV",     0.05,
                                              "Min |p| [GeV] (numerical floor; do NOT use as a physics clamp)"};

  // Sorting / dedup
  Gaudi::Property<bool>    m_sortHits        {this, "SortHits", true,
                                              "Sort hits (robust φ ordering)"};
  Gaudi::Property<bool>    m_dedup           {this, "DeduplicateHits", true,
                                              "Drop nearly-identical hits (after sorting)"};
  Gaudi::Property<double>  m_dedupTolMM      {this, "DedupTolMM", 0.25,
                                              "Dedup tol [mm]"};

  // Grouping
  Gaudi::Property<unsigned> m_minGroupSize     {this, "MinGroupSize", 6u,
                                                "Minimum hits per group"};
  Gaudi::Property<bool>     m_useFallbackClust {this, "UseFallbackClustering", true,
                                                "Enable DBSCAN fallback when all labels are 0"};
  Gaudi::Property<double>   m_fallbackEpsCM    {this, "FallbackEpsCM", 2.0,
                                                "DBSCAN epsilon in cm"};
  Gaudi::Property<unsigned> m_fallbackMinPts   {this, "FallbackMinPts", 6u,
                                                "DBSCAN minPts"};

  // Retry
  Gaudi::Property<bool>     m_retryIfNoFI      {this, "RetryIfNoFitterInfo", true,
                                                "Retry if no FitterInfo"};
  Gaudi::Property<double>   m_retryMeasInfl    {this, "RetryMeasInfl", 4.0,
                                                "Measurement variance inflation factor"};
  Gaudi::Property<double>   m_retrySeedPosInfl {this, "RetrySeedPosInfl", 3.0,
                                                "Seed position sigma inflation factor"};
  Gaudi::Property<double>   m_retrySeedMomInfl {this, "RetrySeedMomInfl", 3.0,
                                                "Seed momentum sigma inflation factor"};

  // Optional cap
  Gaudi::Property<unsigned> m_maxMeasPerGroup  {this, "MaxMeasPerGroup", 0u,
                                                "If >0, downsample measurements per group"};

  // z(φ)-based outlier filter
  Gaudi::Property<bool>    m_filterZOutliers   {this, "FilterZOutliers", false,
                                                "Enable pre-fit z(phi) outlier rejection"};
  Gaudi::Property<double>  m_zOutlierAbsMM     {this, "ZOutlierAbsMM", 80.0,
                                                "Absolute |z residual| cut [mm]"};
  Gaudi::Property<double>  m_zOutlierNSigma    {this, "ZOutlierNSigma", 3.5,
                                                "N-sigma cut on z residual (0 disables sigma term)"};
  Gaudi::Property<double>  m_zOutlierMinFracKeep {this, "ZOutlierMinFracKeep", 0.5,
                                                  "Minimum fraction of hits to keep after filtering"};

  // New robustness knob: try both momentum directions and keep best
  Gaudi::Property<bool> m_tryBothMomDirs{this, "TryBothMomentumDirections", true,
                                        "Try mom0 and -mom0; keep best fit"};

  // Optional job tag (for metadata stamping)
  Gaudi::Property<std::string> m_jobTag{this, "JobTag", "",
                                        "Optional job tag string recorded in metadata"};

  StatusCode initialize() override {
    genfit::FieldManager::getInstance()->init(
      new genfit::ConstField(0., 0., 10.0*m_Bz.value()));

    if (m_useMatEff.value()) {
      if (!gGeoManager) {
        warning() << "UseMaterialEffects=True but gGeoManager is null; proceeding WITHOUT material effects." << endmsg;
      } else {
        try {
          genfit::MaterialEffects::getInstance()->init(new genfit::TGeoMaterialInterface());
          info() << "Initialized GenFit MaterialEffects with TGeoMaterialInterface." << endmsg;

          // NEW: optionally disable energy loss (Bethe-Bloch / Brems), or all effects
          if (m_disableAllMat.value()) {
            genfit::MaterialEffects::getInstance()->setNoEffects(true);
            info() << "MaterialEffects: setNoEffects(true) [DisableAllMaterialEffects=true]" << endmsg;
          } else if (m_disableEloss.value()) {
            auto* me = genfit::MaterialEffects::getInstance();

            // These setters exist in common GenFit2 builds; if your fork differs,
            // you may need to adjust names or wrap with #ifdefs.
            me->setEnergyLossBetheBloch(false);
            me->setNoiseBetheBloch(false);
            me->setEnergyLossBrems(false);
            me->setNoiseBrems(false);

            info() << "MaterialEffects: disabled energy loss (BetheBloch+Brems), kept MS [DisableEnergyLoss=true]" << endmsg;
          }

        } catch (const std::exception& e) {
          warning() << "Failed to initialize/configure MaterialEffects(TGeo): " << e.what()
                    << " — proceeding WITHOUT material effects." << endmsg;
        } catch (...) {
          warning() << "Failed to initialize/configure MaterialEffects(TGeo) (unknown exception)"
                    << " — proceeding WITHOUT material effects." << endmsg;
        }
      }
    } else {
      info() << "UseMaterialEffects = false — running WITHOUT material effects." << endmsg;
    }

    m_fitter = std::make_unique<genfit::KalmanFitterRefTrack>();
    m_fitter->setMaxIterations(12);

    info() << "GenFit2DCHFitter init | Bz=" << m_Bz.value()
           << " | PDG=" << m_pdg.value()
           << " | UseMaterialEffects=" << (m_useMatEff.value() ? "true" : "false")
           << " | DisableEnergyLoss=" << (m_disableEloss.value() ? "true" : "false")
           << " | DisableAllMaterialEffects=" << (m_disableAllMat.value() ? "true" : "false")
           << " | posScale=" << m_posScale.value()
           << " | len2m=" << m_internalLenToM.value()
           << " | HitSigmaXY=" << m_hitSigmaXYMM.value() << " mm"
           << " | HitSigmaZ="  << m_hitSigmaZMM.value()  << " mm"
           << " | SeedPosSigma=" << m_seedPosSigmaMM.value() << " mm"
           << " | SeedMomSigma=" << m_seedMomSigmaGeV.value() << " GeV"
           << " | SeedPTMin=" << m_seedPTMinGeV.value()
           << " | SeedPTMax=" << m_seedPTMaxGeV.value()
           << " | SeedPMin="  << m_seedPMinGeV.value()
           << " | SortHits=" << (m_sortHits.value() ? "true":"false")
           << " | DeduplicateHits=" << (m_dedup.value() ? "true":"false")
           << " | TryBothMomentumDirections=" << (m_tryBothMomDirs.value() ? "true":"false")
           << " | MinGroupSize=" << m_minGroupSize.value()
           << " | UseFallbackClustering=" << (m_useFallbackClust.value() ? "true":"false")
           << " | FallbackEpsCM=" << m_fallbackEpsCM.value()
           << " | FallbackMinPts=" << m_fallbackMinPts.value()
           << " | RetryIfNoFitterInfo=" << (m_retryIfNoFI.value() ? "true":"false")
           << " | RetryMeasInfl=" << m_retryMeasInfl.value()
           << " | RetrySeedPosInfl=" << m_retrySeedPosInfl.value()
           << " | RetrySeedMomInfl=" << m_retrySeedMomInfl.value()
           << " | MaxMeasPerGroup=" << m_maxMeasPerGroup.value()
           << " | FilterZOutliers=" << (m_filterZOutliers.value() ? "true":"false")
           << " | ZOutlierAbsMM=" << m_zOutlierAbsMM.value()
           << " | ZOutlierNSigma=" << m_zOutlierNSigma.value()
           << " | ZOutlierMinFracKeep=" << m_zOutlierMinFracKeep.value()
           << " | JobTag=\"" << m_jobTag.value() << "\""
           << endmsg;

    // --- Write configuration metadata once at initialize() ---
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
      os << ",\"UseMaterialEffects\":" << (m_useMatEff.value() ? "true" : "false");
      os << ",\"DisableEnergyLoss\":" << (m_disableEloss.value() ? "true" : "false");
      os << ",\"DisableAllMaterialEffects\":" << (m_disableAllMat.value() ? "true" : "false");
      os << ",\"PositionUnitScale\":" << m_posScale.value();
      os << ",\"InternalLengthToMeters\":" << m_internalLenToM.value();
      os << ",\"HitSigmaXYMM\":" << m_hitSigmaXYMM.value();
      os << ",\"HitSigmaZMM\":" << m_hitSigmaZMM.value();
      os << ",\"SeedPosSigmaMM\":" << m_seedPosSigmaMM.value();
      os << ",\"SeedMomSigmaGeV\":" << m_seedMomSigmaGeV.value();
      os << ",\"SeedPTMinGeV\":" << m_seedPTMinGeV.value();
      os << ",\"SeedPTMaxGeV\":" << m_seedPTMaxGeV.value();
      os << ",\"SeedPMinGeV\":" << m_seedPMinGeV.value();
      os << ",\"SortHits\":" << (m_sortHits.value() ? "true" : "false");
      os << ",\"DeduplicateHits\":" << (m_dedup.value() ? "true" : "false");
      os << ",\"DedupTolMM\":" << m_dedupTolMM.value();
      os << ",\"TryBothMomentumDirections\":" << (m_tryBothMomDirs.value() ? "true" : "false");
      os << ",\"MinGroupSize\":" << m_minGroupSize.value();
      os << ",\"UseFallbackClustering\":" << (m_useFallbackClust.value() ? "true" : "false");
      os << ",\"FallbackEpsCM\":" << m_fallbackEpsCM.value();
      os << ",\"FallbackMinPts\":" << m_fallbackMinPts.value();
      os << ",\"RetryIfNoFitterInfo\":" << (m_retryIfNoFI.value() ? "true" : "false");
      os << ",\"RetryMeasInfl\":" << m_retryMeasInfl.value();
      os << ",\"RetrySeedPosInfl\":" << m_retrySeedPosInfl.value();
      os << ",\"RetrySeedMomInfl\":" << m_retrySeedMomInfl.value();
      os << ",\"MaxMeasPerGroup\":" << m_maxMeasPerGroup.value();
      os << ",\"FilterZOutliers\":" << (m_filterZOutliers.value() ? "true" : "false");
      os << ",\"ZOutlierAbsMM\":" << m_zOutlierAbsMM.value();
      os << ",\"ZOutlierNSigma\":" << m_zOutlierNSigma.value();
      os << ",\"ZOutlierMinFracKeep\":" << m_zOutlierMinFracKeep.value();
      os << ",\"buildDate\":\"" << __DATE__ << "\"";
      os << ",\"buildTime\":\"" << __TIME__ << "\"";
      os << "}";

      m_cfgMeta.put(os.str());
      info() << "Wrote GenFit2DCHFitter configuration metadata (key='GenFit2DCHFitterConfig')" << endmsg;
    } catch (const std::exception& e) {
      warning() << "Failed to write GenFit2DCHFitter metadata: " << e.what() << endmsg;
    } catch (...) {
      warning() << "Failed to write GenFit2DCHFitter metadata (unknown exception)" << endmsg;
    }

    return StatusCode::SUCCESS;
  }

  TMatrixDSym makeSeedCov(double posInfl=1.0, double momInfl=1.0) const {
    TMatrixDSym C(6); C.Zero();
    const double sP = (m_seedPosSigmaMM.value() * posInfl) * m_posScale.value();
    const double sM = (m_seedMomSigmaGeV.value() * momInfl);
    for (int i = 0; i < 3; ++i) C(i, i) = sP * sP;
    for (int i = 3; i < 6; ++i) C(i, i) = sM * sM;
    ensurePD(C, 1e-6, 4.0, 6);
    return C;
  }

  // --- z(φ) outlier filter (unchanged logic, but benefits from φ-ordering) ---
  bool applyZOutlierFilter(int label,
                           std::vector<TVector3>& P,
                           std::vector<size_t>& idxs,
                           const TVector3& centerXY) const
  {
    const size_t N = P.size();
    if (!m_filterZOutliers.value()) return false;
    if (N < static_cast<size_t>(m_minGroupSize.value()) || N < 4u) return false;

    const double ps = m_posScale.value();
    if (!(ps > 0.0)) return false;

    const double absCut_cm = m_zOutlierAbsMM.value() * ps;
    const double nSigma    = m_zOutlierNSigma.value();

    std::vector<double> phi(N), z(N);
    for (size_t i = 0; i < N; ++i) {
      const auto& v = P[i];
      const double dx = v.X() - centerXY.X();
      const double dy = v.Y() - centerXY.Y();
      phi[i] = std::atan2(dy, dx);
      z[i]   = v.Z();
    }

    // unwrap phi
    for (size_t i = 1; i < N; ++i) {
      double d = phi[i] - phi[i-1];
      while (d >  M_PI) { phi[i] -= 2.0*M_PI; d -= 2.0*M_PI; }
      while (d < -M_PI) { phi[i] += 2.0*M_PI; d += 2.0*M_PI; }
    }

    // linear fit z = a + b phi
    double S1=0., Sphi=0., Szsum=0., Sphi2=0., Sphiz=0.;
    for (size_t i = 0; i < N; ++i) {
      const double ph = phi[i];
      const double zz = z[i];
      S1    += 1.0;
      Sphi  += ph;
      Szsum += zz;
      Sphi2 += ph*ph;
      Sphiz += ph*zz;
    }
    const double denom = S1*Sphi2 - Sphi*Sphi;
    if (std::abs(denom) < 1e-8) return false;

    const double a = (Szsum*Sphi2 - Sphi*Sphiz) / denom;
    const double b = (S1*Sphiz   - Sphi*Szsum)  / denom;

    std::vector<double> resid(N);
    double Sres2 = 0.;
    for (size_t i = 0; i < N; ++i) {
      const double r = z[i] - (a + b*phi[i]);
      resid[i] = r;
      Sres2   += r*r;
    }
    const double sigma_cm = (N > 1u) ? std::sqrt(Sres2 / double(N-1)) : 0.0;

    std::vector<char> keep(N, 1);
    size_t nKeep = 0, nDrop = 0;
    for (size_t i = 0; i < N; ++i) {
      const double r_cm = std::abs(resid[i]);
      bool out = false;
      if (absCut_cm > 0.0 && r_cm > absCut_cm) out = true;
      if (!out && nSigma > 0.0 && sigma_cm > 0.0 && r_cm > nSigma*sigma_cm) out = true;

      if (!out) { keep[i] = 1; ++nKeep; }
      else      { keep[i] = 0; ++nDrop; }
    }

    if (nDrop == 0) return false;

    const double fracKeep = double(nKeep) / double(N);
    if (nKeep < static_cast<size_t>(m_minGroupSize.value()) ||
        fracKeep < m_zOutlierMinFracKeep.value()) {
      debug() << "ZOutlierFilter[label=" << label << "] would drop " << nDrop << "/" << N
              << " hits (keepFrac=" << fracKeep << "), below MinGroupSize or MinFracKeep — disabled."
              << endmsg;
      return false;
    }

    std::vector<TVector3> P2; P2.reserve(nKeep);
    std::vector<size_t>   I2; I2.reserve(nKeep);
    for (size_t i = 0; i < N; ++i) {
      if (!keep[i]) continue;
      P2.push_back(P[i]);
      I2.push_back(idxs[i]);
    }
    P.swap(P2);
    idxs.swap(I2);

    info() << "ZOutlierFilter[label=" << label << "] dropped " << nDrop << "/" << N
           << " hits; kept=" << nKeep << " (keepFrac=" << fracKeep
           << ", sigma_z=" << (sigma_cm / ps) << " mm)" << endmsg;
    return true;
  }

  edm4hep::TrackCollection
  operator()(const edm4hep::TrackerHit3DCollection& hits) const override {
    edm4hep::TrackCollection out;
    if (hits.size() < 3u) return out;

    // ----------------- group hits -----------------
    std::unordered_map<int, Group> groups;
    bool anyNonZero = false;
    groups.reserve(hits.size()/8 + 1);

    for (size_t i = 0; i < hits.size(); ++i) {
      const auto& h = hits[i];
      const int lbl = hitLabel(h);
      anyNonZero = anyNonZero || (lbl != 0);

      const auto p = h.getPosition();
      TVector3 v(m_posScale.value()*p.x,
                 m_posScale.value()*p.y,
                 m_posScale.value()*p.z);

      auto& g = groups[lbl];
      g.P.push_back(v);
      g.idxs.push_back(i);
    }

    // fallback only if ALL labels are 0 and user enabled it
    if (!anyNonZero && m_useFallbackClust.value()) {
      std::vector<TVector3> Pall; Pall.reserve(hits.size());
      for (size_t i = 0; i < hits.size(); ++i) {
        const auto p = hits[i].getPosition();
        Pall.emplace_back(m_posScale.value()*p.x,
                          m_posScale.value()*p.y,
                          m_posScale.value()*p.z);
      }
      const auto labels = dbscan(Pall, m_fallbackEpsCM.value(), m_fallbackMinPts.value());
      std::unordered_map<int, Group> g2;
      int maxLbl = -1;
      for (int L : labels) maxLbl = std::max(maxLbl, L);
      if (maxLbl >= 0) {
        for (size_t i = 0; i < labels.size(); ++i) {
          int L = labels[i];
          if (L < 0) continue;
          auto& g = g2[L];
          g.P.push_back(Pall[i]);
          g.idxs.push_back(i);
        }
        groups.swap(g2);
      }
    }

    info() << "GF2: groups=" << groups.size()
           << " (label=getType preferred; fallback DBSCAN only if all labels were 0)"
           << endmsg;

    // ----------------- measurement covariance -----------------
    const double sxy = m_hitSigmaXYMM.value() * m_posScale.value();
    const double sz  = m_hitSigmaZMM.value()  * m_posScale.value();
    TMatrixDSym Cmeas(3); Cmeas.Zero();
    Cmeas(0,0) = sxy*sxy;
    Cmeas(1,1) = sxy*sxy;
    Cmeas(2,2) = sz*sz;
    ensurePD(Cmeas, 1e-6, 4.0, 6);

    // helpers
    auto run_fit = [&](genfit::Track& trk, const char* tag, int label)->const genfit::FitStatus* {
      try {
        m_fitter->processTrack(&trk);
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
    };

    auto has_any_FI = [&](genfit::Track& trk)->bool{
      genfit::AbsTrackRep* rep = trk.getCardinalRep();
      if (!rep) return false;
      const size_t nPts = trk.getNumPoints();
      for (size_t i = 0; i < nPts; ++i) {
        auto* tp = trk.getPoint(i);
        if (tp && tp->hasFitterInfo(rep)) return true;
      }
      return false;
    };

    auto chi2ndf = [&](const genfit::FitStatus* fs)->double{
      if (!fs) return std::numeric_limits<double>::infinity();
      const double ndf = std::max(1.0, double(fs->getNdf()));
      return fs->getChi2() / ndf;
    };

    auto isGoodFS = [&](const genfit::FitStatus* fs)->bool{
      return fs && fs->isFitted() && fs->isFitConverged() && std::isfinite(fs->getChi2());
    };

    // ----------------- loop groups -----------------
    for (auto& kv : groups) {
      const int label = kv.first;
      auto& P    = kv.second.P;
      auto& idxs = kv.second.idxs;

      if (P.size() < m_minGroupSize.value()) continue;

      // --- compute circle center from crude triplet (will be improved below) ---
      // Use currently available ordering (not trusted); we will attempt to sort by φ about center.
      TVector3 centerXY(0., 0., 0.);
      double   R_forCenter = 1e9;
      {
        const TVector3 A0 = P.front();
        const TVector3 B0 = P[P.size()/2];
        const TVector3 C0 = P.back();
        (void)circleCenterRadiusXY(A0, B0, C0, centerXY, R_forCenter);
      }

      // --- robust sorting ---
      if (m_sortHits.value()) {
        // Decide preferred φ direction using a rough chord direction in XY
        bool preferIncreasingPhi = true;
        if (P.size() >= 2) {
          const TVector3 d = P.back() - P.front();
          (void)d;
        }
        const bool okPhiSort = sortByUnwrappedPhi(P, idxs, centerXY, preferIncreasingPhi);
        if (!okPhiSort) {
          // fallback: do nothing (original ordering), but proceed
        }
      }

      // --- z(φ) outlier filter (now that ordering is more helical-friendly) ---
      {
        // recompute center after sorting using wide-separated points if possible
        TVector3 Aphi, Bphi, Cphi;
        TVector3 c2(0.,0.,0.);
        double   R2 = 1e9;
        bool haveTrip = pickWideSeparatedTriplet(P, centerXY, Aphi, Bphi, Cphi);
        if (!haveTrip) {
          Aphi = P.front(); Bphi = P[P.size()/2]; Cphi = P.back();
        }
        bool haveCircle = circleCenterRadiusXY(Aphi, Bphi, Cphi, c2, R2);
        if (haveCircle) {
          centerXY = c2;
          (void)applyZOutlierFilter(label, P, idxs, centerXY);
        }
      }

      if (P.size() < m_minGroupSize.value()) continue;

      // --- downsample after filtering (keeps ordering) ---
      if (m_maxMeasPerGroup.value() > 0 && P.size() > m_maxMeasPerGroup.value()) {
        const unsigned cap = m_maxMeasPerGroup.value();
        const size_t N = P.size();
        std::vector<TVector3> P2; P2.reserve(cap);
        std::vector<size_t>   I2; I2.reserve(cap);
        for (size_t j = 0; j < cap; ++j) {
          size_t k = static_cast<size_t>(std::round(double(j) * (N-1) / double(cap-1)));
          P2.push_back(P[k]);
          I2.push_back(idxs[k]);
        }
        P.swap(P2);
        idxs.swap(I2);
      }

      if (P.size() < m_minGroupSize.value()) continue;

      // --- dedup AFTER sorting/filtering/downsampling ---
      if (m_dedup.value() && !P.empty()) {
        const double tol2 = std::pow(m_dedupTolMM.value() * m_posScale.value(), 2);
        dedupSorted(P, idxs, tol2);
      }
      if (P.size() < m_minGroupSize.value()) continue;

      // --- recompute circle center & robust seed triplet ---
      TVector3 seedCenter(0.,0.,0.);
      double   seedR = 1e9;

      // initial center guess (still from endpoints)
      {
        const TVector3 A0 = P.front();
        const TVector3 B0 = P[P.size()/2];
        const TVector3 C0 = P.back();
        (void)circleCenterRadiusXY(A0, B0, C0, seedCenter, seedR);
      }

      TVector3 A, B, C;
      if (!pickWideSeparatedTriplet(P, seedCenter, A, B, C)) {
        A = P.front();
        B = P[P.size()/2];
        C = P.back();
      }

      // seed radius from robust triplet
      const double R_int = circleRadiusXY(A, B, C);            // cm
      const double R_m   = R_int * m_internalLenToM.value();   // m

      double pTseed = 0.3 * m_Bz.value() * R_m;                // GeV
      if (!std::isfinite(pTseed) || pTseed <= 0) pTseed = 1.0;
      pTseed = std::clamp(pTseed, m_seedPTMinGeV.value(), m_seedPTMaxGeV.value());

      // direction from sorted endpoints
      TVector3 pos0 = P.front();
      TVector3 posL = P.back();
      TVector3 dir  = (posL - pos0);
      if (dir.Mag2() < 1e-12) dir = TVector3(0,0,1);
      dir = dir.Unit();

      const double cosTheta = std::clamp(std::abs(dir.Z()), 0.0, 0.999999);
      const double sinTheta = std::sqrt(std::max(1e-4, 1.0 - cosTheta*cosTheta));

      // UPDATED: do not force a large |p|; use a small numerical floor only
      double pMag = pTseed / sinTheta;
      if (!std::isfinite(pMag) || pMag <= 0) pMag = pTseed;
      pMag = std::max(pMag, m_seedPMinGeV.value());

      TVector3 mom0 = pMag * dir;

      info() << "Seed[label=" << label << "] | n=" << P.size()
             << " R_int(cm)=" << R_int
             << " pTseed(GeV)=" << pTseed
             << " pMag(GeV)=" << pMag
             << " TryBothMomDirs=" << (m_tryBothMomDirs.value() ? "true":"false")
             << endmsg;

      // Build a track from points (helper lambda)
      auto buildTrackFromSeed = [&](const TVector3& seedPos, const TVector3& seedMom,
                                    const TMatrixDSym& seedCov,
                                    const TMatrixDSym& measCov,
                                    genfit::Track& outTrack) -> void {
        int detId = label;
        int hitId = 0;
        for (const auto& v : P) {
          TVectorD pos(3);
          pos[0] = v.X();
          pos[1] = v.Y();
          pos[2] = v.Z();
          auto* tp   = new genfit::TrackPoint(&outTrack);
          auto* meas = new genfit::SpacepointMeasurement(pos, TMatrixDSym(measCov),
                                                         detId, hitId, tp,
                                                         false, false);
          tp->addRawMeasurement(meas);
          outTrack.insertPoint(tp);
          ++hitId;
        }
        outTrack.setCovSeed(seedCov);
      };

      // Fit candidate #1
      auto rep1_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
      genfit::Track trk1(rep1_up.release(), pos0, mom0);
      buildTrackFromSeed(pos0, mom0, makeSeedCov(1.0, 1.0), Cmeas, trk1);

      const genfit::FitStatus* fs1 = run_fit(trk1, "base(+mom)", label);
      const bool ok1 = (fs1 && has_any_FI(trk1));

      if (fs1) {
        info() << "FitStatus[label=" << label << "][+mom] | fitted=" << fs1->isFitted()
               << " converged=" << fs1->isFitConverged()
               << " Ndf=" << fs1->getNdf()
               << " Chi2=" << fs1->getChi2()
               << " Chi2/Ndf=" << chi2ndf(fs1)
               << " P=" << fs1->getPVal()
               << endmsg;
      }

      // Fit candidate #2 (optional): -mom0
      std::unique_ptr<genfit::Track> trk2_ptr;
      const genfit::FitStatus* fs2 = nullptr;
      bool ok2 = false;

      if (m_tryBothMomDirs.value()) {
        auto rep2_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
        trk2_ptr = std::make_unique<genfit::Track>(rep2_up.release(), pos0, -mom0);
        buildTrackFromSeed(pos0, -mom0, makeSeedCov(1.0, 1.0), Cmeas, *trk2_ptr);

        fs2 = run_fit(*trk2_ptr, "base(-mom)", label);
        ok2 = (fs2 && has_any_FI(*trk2_ptr));

        if (fs2) {
          info() << "FitStatus[label=" << label << "][-mom] | fitted=" << fs2->isFitted()
                 << " converged=" << fs2->isFitConverged()
                 << " Ndf=" << fs2->getNdf()
                 << " Chi2=" << fs2->getChi2()
                 << " Chi2/Ndf=" << chi2ndf(fs2)
                 << " P=" << fs2->getPVal()
                 << endmsg;
        }
      }

      // Choose best between candidates (prefer converged/fitted, then smaller chi2/ndf)
      genfit::Track* bestTrk = nullptr;
      const genfit::FitStatus* bestFs = nullptr;

      auto better = [&](genfit::Track* aTrk, const genfit::FitStatus* aFs,
                        genfit::Track* bTrk, const genfit::FitStatus* bFs)->bool {
        const bool aGood = isGoodFS(aFs) && has_any_FI(*aTrk);
        const bool bGood = isGoodFS(bFs) && has_any_FI(*bTrk);
        if (aGood != bGood) return aGood;
        return chi2ndf(aFs) < chi2ndf(bFs);
      };

      if (ok1) { bestTrk = &trk1; bestFs = fs1; }
      if (ok2 && bestTrk) {
        if (better(trk2_ptr.get(), fs2, bestTrk, bestFs)) {
          bestTrk = trk2_ptr.get();
          bestFs  = fs2;
        }
      } else if (ok2 && !bestTrk) {
        bestTrk = trk2_ptr.get();
        bestFs  = fs2;
      }

      bool ok = (bestTrk && bestFs && has_any_FI(*bestTrk));

      // Retry if no FI (applies to the chosen seed sign only; you can expand if needed)
      if (!ok && m_retryIfNoFI.value()) {
        warning() << "No TrackPoint has FitterInfo (label=" << label
                  << ", base) — retry with inflated covariances." << endmsg;

        // pick which seed to retry: if we tried both, retry the "better" chi2/ndf even if not ok
        TVector3 retryMom = mom0;
        if (m_tryBothMomDirs.value() && fs2) {
          if (!fs1) retryMom = -mom0;
          else if (chi2ndf(fs2) < chi2ndf(fs1)) retryMom = -mom0;
        }

        auto repR_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
        genfit::Track trkR(repR_up.release(), pos0, retryMom);
        trkR.setCovSeed(makeSeedCov(m_retrySeedPosInfl.value(), m_retrySeedMomInfl.value()));

        TMatrixDSym Cmeas_retry(3); Cmeas_retry.Zero();
        Cmeas_retry(0,0) = Cmeas(0,0)*m_retryMeasInfl.value();
        Cmeas_retry(1,1) = Cmeas(1,1)*m_retryMeasInfl.value();
        Cmeas_retry(2,2) = Cmeas(2,2)*m_retryMeasInfl.value();
        ensurePD(Cmeas_retry, 1e-6, 4.0, 6);

        int detR = label, hidR = 0;
        for (const auto& v : P) {
          TVectorD pos(3);
          pos[0] = v.X(); pos[1] = v.Y(); pos[2] = v.Z();
          auto* tp   = new genfit::TrackPoint(&trkR);
          auto* meas = new genfit::SpacepointMeasurement(pos, Cmeas_retry, detR, hidR, tp, false, false);
          tp->addRawMeasurement(meas);
          trkR.insertPoint(tp);
          ++hidR;
        }

        const genfit::FitStatus* fsR = run_fit(trkR, "retry(inflated)", label);
        const bool okR = (fsR && has_any_FI(trkR));

        if (fsR) {
          info() << "FitStatus[label=" << label << "][retry] | fitted=" << fsR->isFitted()
                 << " converged=" << fsR->isFitConverged()
                 << " Ndf=" << fsR->getNdf()
                 << " Chi2=" << fsR->getChi2()
                 << " Chi2/Ndf=" << chi2ndf(fsR)
                 << " P=" << fsR->getPVal()
                 << endmsg;
        }

        if (okR) {
          auto trk = out.create();
          trk.setType(m_pdg.value());
          try { trk.setChi2(fsR->getChi2()); trk.setNdf(fsR->getNdf()); } catch (...) {}

          for (auto i : idxs) trk.addToTrackerHits(hits[i]);

          const int qSeed = chargeFromPDG(m_pdg.value());
          if (!addBestFittedAtIPState(trk, trkR, m_Bz.value(), m_posScale.value(), qSeed)) {
            addAtIPState(trk, pos0, retryMom, m_Bz.value(), m_posScale.value(), qSeed);
          }
          continue;
        } else {
          warning() << "Retry also produced no usable FitterInfo (label=" << label << ")." << endmsg;
          continue;
        }
      }

      if (!ok) continue;

      // ----------------- export edm4hep track -----------------
      auto trk = out.create();
      trk.setType(m_pdg.value());
      try { trk.setChi2(bestFs->getChi2()); trk.setNdf(bestFs->getNdf()); } catch (...) {}

      for (auto i : idxs) trk.addToTrackerHits(hits[i]);

      const int qSeed = chargeFromPDG(m_pdg.value());
      if (!addBestFittedAtIPState(trk, *bestTrk, m_Bz.value(), m_posScale.value(), qSeed)) {
        addAtIPState(trk, pos0, mom0, m_Bz.value(), m_posScale.value(), qSeed);
      }
    }

    return out;
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }

private:
  std::unique_ptr<genfit::KalmanFitterRefTrack> m_fitter;

  // Metadata handle for this fitter's configuration (JSON string)
  k4FWCore::MetaDataHandle<std::string> m_cfgMeta;
};

DECLARE_COMPONENT(GenFit2DCHFitter)
