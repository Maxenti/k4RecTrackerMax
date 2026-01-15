// ======================================================================
// GenFit2DCHFitter.cpp  -- fit GGTF 3D hits with GenFit2 (more robust)
//
// Key principle for “nearly straight” segments:
//   If curvature is not observable (tiny φ-span / tiny XY chord / ill-conditioned circle),
//   you CANNOT “accurately calculate pT” from geometry. The correct behavior is:
//
//     - still fit (to get direction / associations / z behavior),
//     - but DO NOT publish pT as a measured quantity.
//       -> we set TrackState.time = InvalidPTSentinel (default -1)
//       -> we set omega covariance huge (q/pT unconstrained)
//
// This version implements the corrections discussed:
//
//  1) Never export seed-based pT as if it were measured.
//     - If no fitted state is available, we export a TrackState with time=-1.
//  2) For low-curvature-observability tracks, we either:
//       - skip exporting entirely (SkipLowCurvObs=true), OR
//       - export track but mark pT invalid (time=-1) + huge cov(omega,omega).
//  3) Add additional “observability” gating using XY chord length (MinChordXYMM).
//  4) TrackState covariance: omega variance is SMALL for good tracks, HUGE for low-observable.
//  5) Optional: write an observability score to edm4hep::Track::quality IF available.
//
// Notes / conventions (kept from your code):
//   - internal positions are cm (PositionUnitScale=0.1 for mm->cm).
//   - you store q/pT in TrackState.omega [GeV^-1] and store pT [GeV] in TrackState.time.
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
#include <type_traits>

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
#include "TMatrixD.h"
#include "TMatrixDSym.h"
#include "TMatrixDSymEigen.h"
#include "TDecompSVD.h"
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

template <typename, typename = void> struct has_getType : std::false_type {};
template <typename T>
struct has_getType<T, std::void_t<decltype(std::declval<T>().getType())>> : std::true_type {};

// Prefer getType() (GGTF_tracking sets Type) over getQuality()
template <typename HitT>
inline int hitLabel(const HitT& h) {
  if constexpr (has_getType<HitT>::value) return static_cast<int>(h.getType());
  else return 0;
}

// Optional: detect edm4hep::MutableTrack::setQuality
template <typename, typename = void> struct has_setQuality : std::false_type {};
template <typename T>
struct has_setQuality<T, std::void_t<decltype(std::declval<T>().setQuality(float(0.f)))>> : std::true_type {};

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

// ---------- robust circle fit in XY (linear LS with SVD) ----------
// Fit x^2 + y^2 + D x + E y + F = 0  -> center = (mx - D/2, my - E/2)
static bool fitCircleLS_SVD_XY(const std::vector<TVector3>& P,
                              TVector3& centerXY,
                              double& R,
                              double& condEst,
                              double& rmsResidual) {
  const int N = static_cast<int>(P.size());
  centerXY.SetXYZ(0.,0.,0.);
  R = 1e9;
  condEst = std::numeric_limits<double>::infinity();
  rmsResidual = std::numeric_limits<double>::infinity();
  if (N < 3) return false;

  TMatrixD A(N, 3);
  TVectorD b(N);

  double mx = 0., my = 0.;
  for (const auto& v : P) { mx += v.X(); my += v.Y(); }
  mx /= double(N); my /= double(N);

  double scale = 0.;
  for (const auto& v : P) scale = std::max(scale, std::hypot(v.X()-mx, v.Y()-my));
  if (!(scale > 0.0) || !std::isfinite(scale)) scale = 1.0;

  for (int i = 0; i < N; ++i) {
    const double x = (P[i].X() - mx) / scale;
    const double y = (P[i].Y() - my) / scale;
    A(i,0) = x;
    A(i,1) = y;
    A(i,2) = 1.0;
    b(i)   = -(x*x + y*y);
  }

  TDecompSVD svd(A);
  Bool_t ok = svd.Decompose();
  if (!ok) return false;

  TVectorD s = svd.GetSig();
  double smax = 0., smin = std::numeric_limits<double>::infinity();
  for (int i = 0; i < s.GetNrows(); ++i) {
    if (s(i) > smax) smax = s(i);
    if (s(i) > 0 && s(i) < smin) smin = s(i);
  }
  if (!(smax > 0.0) || !(smin > 0.0)) return false;
  condEst = smax / smin;

  TVectorD u = svd.Solve(b, ok);
  if (!ok) return false;

  const double Dn = u(0);
  const double En = u(1);
  const double Fn = u(2);

  const double D = Dn * scale;
  const double E = En * scale;
  const double F = Fn * scale * scale;

  const double cx = mx - 0.5 * D;
  const double cy = my - 0.5 * E;
  const double R2 = cx*cx + cy*cy - F;

  if (!std::isfinite(cx) || !std::isfinite(cy) || !std::isfinite(R2) || R2 <= 1e-18) {
    return false;
  }

  const double Rloc = std::sqrt(R2);
  if (!std::isfinite(Rloc) || Rloc <= 1e-9) return false;

  centerXY.SetXYZ(cx, cy, 0.0);
  R = Rloc;

  double ss = 0.;
  for (const auto& v : P) {
    const double x = v.X();
    const double y = v.Y();
    const double r = (x*x + y*y) + D*x + E*y + F;
    ss += r*r;
  }
  rmsResidual = std::sqrt(ss / double(N));
  return true;
}

static bool computePhiSpanUnwrapped(const std::vector<TVector3>& P,
                                   const TVector3& centerXY,
                                   double& phiMin,
                                   double& phiMax,
                                   double& phiSpan) {
  phiMin = +1e9; phiMax = -1e9; phiSpan = 0.0;
  if (!std::isfinite(centerXY.X()) || !std::isfinite(centerXY.Y())) return false;
  if (P.size() < 2) return false;

  std::vector<double> phi(P.size(), 0.0);
  for (size_t i = 0; i < P.size(); ++i) {
    const double dx = P[i].X() - centerXY.X();
    const double dy = P[i].Y() - centerXY.Y();
    phi[i] = std::atan2(dy, dx);
  }
  for (size_t i = 1; i < phi.size(); ++i) {
    double d = phi[i] - phi[i-1];
    while (d >  M_PI) { phi[i] -= 2.0*M_PI; d -= 2.0*M_PI; }
    while (d < -M_PI) { phi[i] += 2.0*M_PI; d += 2.0*M_PI; }
  }
  for (double p : phi) { phiMin = std::min(phiMin, p); phiMax = std::max(phiMax, p); }
  phiSpan = phiMax - phiMin;
  return std::isfinite(phiSpan);
}

static bool sortByUnwrappedPhi(std::vector<TVector3>& P,
                               std::vector<size_t>& idxs,
                               const TVector3& centerXY,
                               bool preferIncreasingPhi = true) {
  const size_t N = P.size();
  if (N < 3) return false;
  if (!std::isfinite(centerXY.X()) || !std::isfinite(centerXY.Y())) return false;

  std::vector<double> phi(N);
  for (size_t i = 0; i < N; ++i) {
    const double dx = P[i].X() - centerXY.X();
    const double dy = P[i].Y() - centerXY.Y();
    phi[i] = std::atan2(dy, dx);
  }
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

// PCA/chord sort fallback: sort by projection on the principal axis (3D).
static bool sortByPCAProjection(std::vector<TVector3>& P, std::vector<size_t>& idxs) {
  const size_t N = P.size();
  if (N < 2) return false;

  TVector3 mu(0,0,0);
  for (const auto& v : P) mu += v;
  mu *= (1.0 / double(N));

  TMatrixDSym C(3); C.Zero();
  for (const auto& v : P) {
    const TVector3 d = v - mu;
    C(0,0) += d.X()*d.X(); C(0,1) += d.X()*d.Y(); C(0,2) += d.X()*d.Z();
    C(1,1) += d.Y()*d.Y(); C(1,2) += d.Y()*d.Z();
    C(2,2) += d.Z()*d.Z();
  }
  C(1,0) = C(0,1);
  C(2,0) = C(0,2);
  C(2,1) = C(1,2);

  TMatrixDSymEigen eig(C);
  TVectorD eval = eig.GetEigenValues();
  TMatrixD evec = eig.GetEigenVectors(); // columns are eigenvectors

  int imax = 0;
  double vmax = eval(0);
  for (int i = 1; i < 3; ++i) {
    if (eval(i) > vmax) { vmax = eval(i); imax = i; }
  }

  TVector3 axis(evec(0,imax), evec(1,imax), evec(2,imax));
  if (axis.Mag2() < 1e-18) return false;
  axis = axis.Unit();

  std::vector<double> t(N, 0.0);
  for (size_t i = 0; i < N; ++i) t[i] = (P[i] - mu).Dot(axis);

  std::vector<size_t> order(N);
  std::iota(order.begin(), order.end(), 0);
  std::sort(order.begin(), order.end(), [&](size_t a, size_t b){ return t[a] < t[b]; });

  std::vector<TVector3> P2; P2.reserve(N);
  std::vector<size_t>   I2; I2.reserve(N);
  for (auto k : order) { P2.push_back(P[k]); I2.push_back(idxs[k]); }
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
// Conventions: omega = q/pT [GeV^-1], time = pT [GeV] (if valid), else time = InvalidPTSentinel.
static void addAtIPState(edm4hep::MutableTrack& trk,
                         const TVector3& pos_internal,
                         const TVector3& mom_GeV,
                         double posScale,
                         int chargeSign,
                         bool ptValid,
                         float invalidPTSentinel,
                         float omegaVar,
                         float pTOverrideOrNeg = -1.f) {
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

  if (ptValid) {
    const float outPT = (pTOverrideOrNeg > 0.f ? pTOverrideOrNeg : float(pT));
    ts.time = outPT;
  } else {
    ts.time = invalidPTSentinel;
  }

  // covariance (diagonal placeholders)
  ts.setCovMatrix(1.0f,   TP::d0,        TP::d0);
  ts.setCovMatrix(1e-3f,  TP::phi,       TP::phi);
  ts.setCovMatrix(omegaVar, TP::omega,   TP::omega);  // IMPORTANT: reflect unconstrained q/pT
  ts.setCovMatrix(1.0f,   TP::z0,        TP::z0);
  ts.setCovMatrix(1e-2f,  TP::tanLambda, TP::tanLambda);

  trk.addToTrackStates(ts);
}

// Extract best fitted state near IP.
// Returns true if we successfully exported a TrackState based on a fitted state.
// Also returns fitted pT in outPT (if ptValid==true), otherwise outPT is undefined.
static bool addBestFittedAtIPState(edm4hep::MutableTrack& trk,
                                   const genfit::Track& gftrk,
                                   double posScale,
                                   int fallbackCharge,
                                   bool ptValid,
                                   float invalidPTSentinel,
                                   float omegaVar,
                                   float& outPT) {
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

  outPT = float(std::hypot(mom.X(), mom.Y()));
  addAtIPState(trk, pos_cm, mom, posScale, q, ptValid, invalidPTSentinel, omegaVar, outPT);
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
      m_cfgMeta("GenFit2DCHFitterConfig", Gaudi::DataHandle::Writer) {}

  // ----------------- Properties -----------------

  // Physics knobs
  Gaudi::Property<double>  m_Bz {this, "Bz", 2.0, "Bz field [T]"};
  Gaudi::Property<int>     m_pdg{this, "PDG", 13,  "PDG hypothesis"};

  // Material effects
  Gaudi::Property<bool>    m_useMatEff{this, "UseMaterialEffects", true,
                                       "Use TGeoMaterialInterface for GenFit MaterialEffects"};

  // Optional material-effects suppression knobs
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

  // Seed / robustness (seed is only for convergence; we do not “publish” it as pT)
  Gaudi::Property<double>  m_seedPosSigmaMM  {this, "SeedPosSigmaMM", 80.0, "Seed pos sigma [mm]"};
  Gaudi::Property<double>  m_seedMomSigmaGeV {this, "SeedMomSigmaGeV", 5.0,  "Seed mom sigma [GeV]"};
  Gaudi::Property<double>  m_seedPTMinGeV    {this, "SeedPTMinGeV",    0.20, "Min pT [GeV]"};
  Gaudi::Property<double>  m_seedPTMaxGeV    {this, "SeedPTMaxGeV",   200.0, "Max pT [GeV]"};
  Gaudi::Property<double>  m_seedPMinGeV     {this, "SeedPMinGeV",     0.05, "Min |p| [GeV] (numerical floor; not physics clamp)"};

  // Circle-fit quality / curvature observability
  Gaudi::Property<double>  m_minPhiSpanRad   {this, "MinPhiSpanRad", 0.03, "Minimum unwrapped φ-span (rad) to trust curvature"};
  Gaudi::Property<double>  m_maxCircleCond   {this, "MaxCircleCond", 1e6,  "Maximum acceptable condition estimate for circle LS solve"};

  // NEW: chord-length observability (additional sanity gate)
  Gaudi::Property<double>  m_minChordXYMM    {this, "MinChordXYMM", 50.0, "Minimum XY chord length [mm] to treat curvature as observable"};

  // If true: skip exporting low-curvature-observability tracks entirely
  Gaudi::Property<bool>    m_skipLowCurvObs  {this, "SkipLowCurvObs", true,
                                              "If true: do not export tracks where curvature is unobservable (tiny φ-span/chord or ill-conditioned circle)"};

  // Seed pT used ONLY to stabilize the fitter when curvature is unobservable
  Gaudi::Property<double>  m_lowCurvSeedPTGeV{this, "LowCurvSeedPTGeV", 30.0,
                                              "Seed pT [GeV] used when curvature is unobservable (stability only; not meaningful)"};

  // Export policy
  Gaudi::Property<float>   m_invalidPTSentinel {this, "InvalidPTSentinel", -1.0f, "TrackState.time value when pT is not published"};
  Gaudi::Property<bool>    m_publishPTOnlyIfCurvObservable {this, "PublishPTOnlyIfCurvObservable", true,
                                                            "If true: even if GenFit returns a pT, do not publish it unless curvature is observable"};
  Gaudi::Property<bool>    m_requireFittedStateForPT {this, "RequireFittedStateForPT", true,
                                                      "If true: never publish pT unless it comes from a fitted GenFit state"};
  Gaudi::Property<float>   m_omegaVarGood {this, "OmegaVarGood", 1e-4f, "(GeV^-1)^2 covariance for omega when curvature is observable"};
  Gaudi::Property<float>   m_omegaVarBad  {this, "OmegaVarBad",  1.0f,  "(GeV^-1)^2 covariance for omega when curvature is NOT observable"};

  // Sorting / dedup
  Gaudi::Property<bool>    m_sortHits        {this, "SortHits", true, "Sort hits (φ order when possible; PCA fallback)"};
  Gaudi::Property<bool>    m_dedup           {this, "DeduplicateHits", true, "Drop nearly-identical hits (after sorting)"};
  Gaudi::Property<double>  m_dedupTolMM      {this, "DedupTolMM", 0.25, "Dedup tol [mm]"};

  // Grouping
  Gaudi::Property<unsigned> m_minGroupSize     {this, "MinGroupSize", 6u, "Minimum hits per group"};
  Gaudi::Property<bool>     m_useFallbackClust {this, "UseFallbackClustering", true, "Enable DBSCAN fallback when all labels are 0"};
  Gaudi::Property<double>   m_fallbackEpsCM    {this, "FallbackEpsCM", 2.0, "DBSCAN epsilon in cm"};
  Gaudi::Property<unsigned> m_fallbackMinPts   {this, "FallbackMinPts", 6u, "DBSCAN minPts"};

  // Retry
  Gaudi::Property<bool>     m_retryIfNoFI      {this, "RetryIfNoFitterInfo", true, "Retry if no FitterInfo"};
  Gaudi::Property<double>   m_retryMeasInfl    {this, "RetryMeasInfl", 4.0, "Measurement variance inflation factor"};
  Gaudi::Property<double>   m_retrySeedPosInfl {this, "RetrySeedPosInfl", 3.0, "Seed position sigma inflation factor"};
  Gaudi::Property<double>   m_retrySeedMomInfl {this, "RetrySeedMomInfl", 3.0, "Seed momentum sigma inflation factor"};

  // Optional cap
  Gaudi::Property<unsigned> m_maxMeasPerGroup  {this, "MaxMeasPerGroup", 0u, "If >0, downsample measurements per group"};

  // Robustness: try both momentum directions and keep best
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

          if (m_disableAllMat.value()) {
            genfit::MaterialEffects::getInstance()->setNoEffects(true);
            info() << "MaterialEffects: setNoEffects(true) [DisableAllMaterialEffects=true]" << endmsg;
          } else if (m_disableEloss.value()) {
            auto* me = genfit::MaterialEffects::getInstance();
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
           << " | MinPhiSpanRad=" << m_minPhiSpanRad.value()
           << " | MinChordXYMM=" << m_minChordXYMM.value()
           << " | MaxCircleCond=" << m_maxCircleCond.value()
           << " | SkipLowCurvObs=" << (m_skipLowCurvObs.value() ? "true" : "false")
           << " | PublishPTOnlyIfCurvObservable=" << (m_publishPTOnlyIfCurvObservable.value() ? "true" : "false")
           << " | RequireFittedStateForPT=" << (m_requireFittedStateForPT.value() ? "true" : "false")
           << " | InvalidPTSentinel=" << m_invalidPTSentinel.value()
           << " | OmegaVarGood=" << m_omegaVarGood.value()
           << " | OmegaVarBad=" << m_omegaVarBad.value()
           << " | LowCurvSeedPTGeV=" << m_lowCurvSeedPTGeV.value()
           << " | SortHits=" << (m_sortHits.value() ? "true":"false")
           << " | DeduplicateHits=" << (m_dedup.value() ? "true":"false")
           << " | TryBothMomentumDirections=" << (m_tryBothMomDirs.value() ? "true":"false")
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
      os << ",\"MinPhiSpanRad\":" << m_minPhiSpanRad.value();
      os << ",\"MinChordXYMM\":" << m_minChordXYMM.value();
      os << ",\"MaxCircleCond\":" << m_maxCircleCond.value();
      os << ",\"SkipLowCurvObs\":" << (m_skipLowCurvObs.value() ? "true" : "false");
      os << ",\"LowCurvSeedPTGeV\":" << m_lowCurvSeedPTGeV.value();
      os << ",\"PublishPTOnlyIfCurvObservable\":" << (m_publishPTOnlyIfCurvObservable.value() ? "true" : "false");
      os << ",\"RequireFittedStateForPT\":" << (m_requireFittedStateForPT.value() ? "true" : "false");
      os << ",\"InvalidPTSentinel\":" << m_invalidPTSentinel.value();
      os << ",\"OmegaVarGood\":" << m_omegaVarGood.value();
      os << ",\"OmegaVarBad\":" << m_omegaVarBad.value();
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

    // fallback only if ALL labels are 0 and enabled
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

      // --- downsample early (preserves raw order) ---
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

      // --- robust circle fit (all hits) ---
      TVector3 centerXY(0.,0.,0.);
      double R_int = 1e9;
      double cond  = 1e99;
      double rmsRes= 1e99;
      const bool circleOK = fitCircleLS_SVD_XY(P, centerXY, R_int, cond, rmsRes);

      double phiMin=0., phiMax=0., phiSpan=0.;
      bool phiOK = false;
      if (circleOK) phiOK = computePhiSpanUnwrapped(P, centerXY, phiMin, phiMax, phiSpan);

      const bool circleTrusted = circleOK && std::isfinite(cond) && (cond <= m_maxCircleCond.value());

      // --- sorting ---
      if (m_sortHits.value()) {
        bool sorted = false;
        if (circleTrusted && phiOK && std::isfinite(phiSpan) && (phiSpan >= m_minPhiSpanRad.value())) {
          sorted = sortByUnwrappedPhi(P, idxs, centerXY, true);
        }
        if (!sorted) {
          (void)sortByPCAProjection(P, idxs);
        }
      }

      // --- dedup AFTER sorting ---
      if (m_dedup.value() && !P.empty()) {
        const double tol2 = std::pow(m_dedupTolMM.value() * m_posScale.value(), 2);
        dedupSorted(P, idxs, tol2);
      }
      if (P.size() < m_minGroupSize.value()) continue;

      // --- chord length (XY) after sorting ---
      const TVector3 pos0 = P.front();
      const TVector3 posL = P.back();
      const double chordXY_internal = std::hypot(posL.X()-pos0.X(), posL.Y()-pos0.Y());  // internal units (cm)
      const double chordXY_mm = chordXY_internal / m_posScale.value();                   // convert cm -> mm (posScale=0.1)

      // recompute phiSpan with sorted points if circleTrusted
      if (circleTrusted) {
        phiOK = computePhiSpanUnwrapped(P, centerXY, phiMin, phiMax, phiSpan);
      } else {
        phiOK = false;
        phiSpan = 0.0;
      }

      const bool phiObservable   = circleTrusted && phiOK && std::isfinite(phiSpan) && (phiSpan >= m_minPhiSpanRad.value());
      const bool chordObservable = std::isfinite(chordXY_mm) && (chordXY_mm >= m_minChordXYMM.value());
      const bool curvObservable  = phiObservable && chordObservable;

      // Observability score (1.0 = at threshold, >1 good). Used only for logging / optional Track::quality.
      const double scorePhi   = (m_minPhiSpanRad.value() > 0 ? (phiSpan / m_minPhiSpanRad.value()) : 0.0);
      const double scoreChord = (m_minChordXYMM.value() > 0 ? (chordXY_mm / m_minChordXYMM.value()) : 0.0);
      const float obsScore = float(std::max(0.0, std::min(scorePhi, scoreChord)));

      debug() << "Group[label=" << label << "] n=" << P.size()
              << " circleOK=" << (circleOK ? "true":"false")
              << " cond=" << cond
              << " rmsAlgRes=" << rmsRes
              << " phiSpan=" << phiSpan
              << " chordXY_mm=" << chordXY_mm
              << " circleTrusted=" << (circleTrusted ? "true":"false")
              << " curvObservable=" << (curvObservable ? "true":"false")
              << " obsScore=" << obsScore
              << endmsg;

      if (!curvObservable && m_skipLowCurvObs.value()) {
        debug() << "Skipping export for label=" << label
                << " because curvature unobservable (phiSpan=" << phiSpan
                << ", chordXY_mm=" << chordXY_mm
                << ", cond=" << cond << ")." << endmsg;
        continue;
      }

      // --- Seed pT (for convergence only) ---
      double pTseed = 0.0;
      if (curvObservable) {
        const double R_m = R_int * m_internalLenToM.value();      // m
        pTseed = 0.3 * m_Bz.value() * R_m;                        // GeV
        if (!std::isfinite(pTseed) || pTseed <= 0) pTseed = m_lowCurvSeedPTGeV.value();
      } else {
        pTseed = m_lowCurvSeedPTGeV.value();
      }
      pTseed = std::clamp(pTseed, m_seedPTMinGeV.value(), m_seedPTMaxGeV.value());

      // direction from sorted endpoints
      TVector3 dir  = (posL - pos0);
      if (dir.Mag2() < 1e-12) dir = TVector3(0,0,1);
      dir = dir.Unit();

      const double cosTheta = std::clamp(std::abs(dir.Z()), 0.0, 0.999999);
      const double sinTheta = std::sqrt(std::max(1e-4, 1.0 - cosTheta*cosTheta));

      double pMag = pTseed / sinTheta;
      if (!std::isfinite(pMag) || pMag <= 0) pMag = pTseed;
      pMag = std::max(pMag, m_seedPMinGeV.value());

      TVector3 mom0 = pMag * dir;

      info() << "Seed[label=" << label << "] n=" << P.size()
             << " curvObs=" << (curvObservable ? "true":"false")
             << " obsScore=" << obsScore
             << " phiSpan=" << phiSpan
             << " chordXY_mm=" << chordXY_mm
             << " cond=" << cond
             << " pTseed=" << pTseed
             << " pMag=" << pMag
             << endmsg;

      // Build a track from points
      auto buildTrackFromSeed = [&](genfit::Track& outTrack, const TMatrixDSym& measCov) -> void {
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
      };

      // Fit candidate #1
      auto rep1_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
      genfit::Track trk1(rep1_up.release(), pos0, mom0);
      trk1.setCovSeed(makeSeedCov(1.0, 1.0));
      buildTrackFromSeed(trk1, Cmeas);

      const genfit::FitStatus* fs1 = run_fit(trk1, "base(+mom)", label);
      const bool ok1 = (fs1 && has_any_FI(trk1));

      if (fs1) {
        info() << "FitStatus[label=" << label << "][+mom] fitted=" << fs1->isFitted()
               << " conv=" << fs1->isFitConverged()
               << " ndf=" << fs1->getNdf()
               << " chi2=" << fs1->getChi2()
               << " chi2/ndf=" << chi2ndf(fs1)
               << " pval=" << fs1->getPVal()
               << endmsg;
      }

      // Fit candidate #2: -mom0
      std::unique_ptr<genfit::Track> trk2_ptr;
      const genfit::FitStatus* fs2 = nullptr;
      bool ok2 = false;

      if (m_tryBothMomDirs.value()) {
        auto rep2_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
        trk2_ptr = std::make_unique<genfit::Track>(rep2_up.release(), pos0, -mom0);
        trk2_ptr->setCovSeed(makeSeedCov(1.0, 1.0));
        buildTrackFromSeed(*trk2_ptr, Cmeas);

        fs2 = run_fit(*trk2_ptr, "base(-mom)", label);
        ok2 = (fs2 && has_any_FI(*trk2_ptr));

        if (fs2) {
          info() << "FitStatus[label=" << label << "][-mom] fitted=" << fs2->isFitted()
                 << " conv=" << fs2->isFitConverged()
                 << " ndf=" << fs2->getNdf()
                 << " chi2=" << fs2->getChi2()
                 << " chi2/ndf=" << chi2ndf(fs2)
                 << " pval=" << fs2->getPVal()
                 << endmsg;
        }
      }

      // Choose best between candidates
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

      // Retry if no FI
      if (!ok && m_retryIfNoFI.value()) {
        warning() << "No TrackPoint has FitterInfo (label=" << label
                  << ", base) — retry with inflated covariances." << endmsg;

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

        buildTrackFromSeed(trkR, Cmeas_retry);

        const genfit::FitStatus* fsR = run_fit(trkR, "retry(inflated)", label);
        const bool okR = (fsR && has_any_FI(trkR));

        if (fsR) {
          info() << "FitStatus[label=" << label << "][retry] fitted=" << fsR->isFitted()
                 << " conv=" << fsR->isFitConverged()
                 << " ndf=" << fsR->getNdf()
                 << " chi2=" << fsR->getChi2()
                 << " chi2/ndf=" << chi2ndf(fsR)
                 << " pval=" << fsR->getPVal()
                 << endmsg;
        }

        if (okR) {
          auto trk = out.create();
          trk.setType(m_pdg.value());
          try { trk.setChi2(fsR->getChi2()); trk.setNdf(fsR->getNdf()); } catch (...) {}
          for (auto i : idxs) trk.addToTrackerHits(hits[i]);

          const int qSeed = chargeFromPDG(m_pdg.value());
          const bool ptAllowed = (!m_requireFittedStateForPT.value()) ? true
                               : (m_publishPTOnlyIfCurvObservable.value() ? curvObservable : true);
          const float omegaVar = (curvObservable ? m_omegaVarGood.value() : m_omegaVarBad.value());

          float fittedPT = 0.f;
          const bool exportedFit = addBestFittedAtIPState(trk, trkR,
                                                          m_posScale.value(), qSeed,
                                                          ptAllowed, m_invalidPTSentinel.value(),
                                                          omegaVar, fittedPT);

          // If we cannot export a fitted state, NEVER export seed pT as measured.
          if (!exportedFit) {
            addAtIPState(trk, pos0, retryMom,
                         m_posScale.value(), qSeed,
                         /*ptValid=*/false,
                         m_invalidPTSentinel.value(),
                         omegaVar);
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

      const bool ptAllowed = (!m_requireFittedStateForPT.value()) ? true
                           : (m_publishPTOnlyIfCurvObservable.value() ? curvObservable : true);

      const float omegaVar = (curvObservable ? m_omegaVarGood.value() : m_omegaVarBad.value());

      float fittedPT = 0.f;
      const bool exportedFit = addBestFittedAtIPState(trk, *bestTrk,
                                                      m_posScale.value(), qSeed,
                                                      ptAllowed, m_invalidPTSentinel.value(),
                                                      omegaVar, fittedPT);

      // If we cannot export a fitted state, NEVER publish seed pT as measured.
      if (!exportedFit) {
        addAtIPState(trk, pos0, mom0,
                     m_posScale.value(), qSeed,
                     /*ptValid=*/false,
                     m_invalidPTSentinel.value(),
                     omegaVar);
      }
    }

    return out;
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }

private:
  std::unique_ptr<genfit::KalmanFitterRefTrack> m_fitter;
  k4FWCore::MetaDataHandle<std::string> m_cfgMeta;
};

DECLARE_COMPONENT(GenFit2DCHFitter)
