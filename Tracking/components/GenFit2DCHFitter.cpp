// ======================================================================
// GenFit2DCHFitter.cpp  -- fit GGTF 3D hits with GenFit2 (robust, GGTF-aware)
//
// Key upgrades (requested):
//  - Use per-hit TrackerHit3D.covMatrix (anisotropic) with unit conversion + PD guard
//  - Reject negative-type “debug” labels by default (belt-and-suspenders)
//  - Deterministic hit ordering heuristic (R/Z span) before any φ-unwrapping
//  - Strong publish gates to prevent runaway huge-pT exports
//  - More robust “best fitted state” selection (not just smallest r²), with sanity filtering
//  - Optional dedup in 3D with tight epsilon to avoid near-duplicate points destabilizing fits
//  - IMPORTANT FIXES APPLIED:
//      * Correct position scale used when exporting TrackState (use posScale*inputHitPosScale)
//      * Export EXACTLY ONE authoritative TrackState per edm4hep::Track (no duplicate TrackStates)
//
// Conventions kept from your code:
//  - internal positions are cm (PositionUnitScale=0.1 for mm->cm).
//  - TrackState.omega = q/pT [GeV^-1], TrackState.time = pT [GeV] if valid else sentinel.
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

// ---- sign helpers ----
inline int sgn(double x) {
  if (!std::isfinite(x) || x == 0.0) return 0;
  return (x > 0.0) ? +1 : -1;
}
inline const char* sgnstr(int s) {
  return (s > 0) ? "+" : (s < 0 ? "-" : "0");
}

// ---- hit label helpers ----
template <typename, typename = void> struct has_getType : std::false_type {};
template <typename T>
struct has_getType<T, std::void_t<decltype(std::declval<T>().getType())>> : std::true_type {};

template <typename HitT>
inline int hitLabel(const HitT& h) {
  if constexpr (has_getType<HitT>::value) return static_cast<int>(h.getType());
  else return 0;
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

  // Eigen decomposition and clamp
  TMatrixDSymEigen eig(C);
  TVectorD eval = eig.GetEigenValues();
  TMatrixD evec = eig.GetEigenVectors(); // columns

  bool changed = false;
  for (int i = 0; i < eval.GetNrows(); ++i) {
    if (!std::isfinite(eval(i)) || eval(i) < minEig) {
      eval(i) = minEig;
      changed = true;
    }
  }
  if (!changed) return;

  // Reconstruct: C = V diag(eval) V^T
  TMatrixD D(C.GetNrows(), C.GetNcols()); D.Zero();
  for (int i = 0; i < eval.GetNrows(); ++i) D(i, i) = eval(i);
  TMatrixD V(evec);
  TMatrixD tmp = V * D * TMatrixD(TMatrixD::kTransposed, V);

  for (int i = 0; i < C.GetNrows(); ++i) {
    for (int j = 0; j < C.GetNcols(); ++j) C(i, j) = tmp(i, j);
  }
  makeDiagonalFloor(C, minEig);
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

  // NOTE: keep this overload; in C++ this is fine.
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

// NEW: robust deterministic order heuristic before any φ-unwrapping
static void sortByRZHeuristic(std::vector<TVector3>& P, std::vector<size_t>& idxs) {
  if (P.size() < 2) return;

  double rmin = +1e99, rmax = -1e99;
  double zmin = +1e99, zmax = -1e99;
  for (const auto& v : P) {
    const double r = std::hypot(v.X(), v.Y());
    rmin = std::min(rmin, r); rmax = std::max(rmax, r);
    zmin = std::min(zmin, v.Z()); zmax = std::max(zmax, v.Z());
  }
  const double rSpan = rmax - rmin;
  const double zSpan = zmax - zmin;

  std::vector<size_t> order(P.size());
  std::iota(order.begin(), order.end(), 0);

  if (zSpan > rSpan) {
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b){
      if (P[a].Z() == P[b].Z()) return std::hypot(P[a].X(),P[a].Y()) < std::hypot(P[b].X(),P[b].Y());
      return P[a].Z() < P[b].Z();
    });
  } else {
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b){
      const double ra = std::hypot(P[a].X(),P[a].Y());
      const double rb = std::hypot(P[b].X(),P[b].Y());
      if (ra == rb) return P[a].Z() < P[b].Z();
      return ra < rb;
    });
  }

  std::vector<TVector3> P2; P2.reserve(P.size());
  std::vector<size_t>   I2; I2.reserve(idxs.size());
  for (auto k : order) { P2.push_back(P[k]); I2.push_back(idxs[k]); }
  P.swap(P2);
  idxs.swap(I2);
}

// 3D dedup (XYZ) after deterministic ordering
static void dedupSorted3D(std::vector<TVector3>& P,
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

// ---------- chord+sagitta diagnostics in XY ----------
static bool computeChordAndSagittaXY(const std::vector<TVector3>& P,
                                    double posScale_cm_per_mm,
                                    double& chordXY_internal_cm,
                                    double& chordXY_mm,
                                    double& sagitta_internal_cm_abs,
                                    double& sagitta_mm_abs,
                                    double& sagitta_internal_cm_signed,
                                    double& sagitta_mm_signed) {
  chordXY_internal_cm = 0.0;
  chordXY_mm = 0.0;
  sagitta_internal_cm_abs = 0.0;
  sagitta_mm_abs = 0.0;
  sagitta_internal_cm_signed = 0.0;
  sagitta_mm_signed = 0.0;

  const size_t N = P.size();
  if (N < 3) return false;

  const TVector3 A = P.front();
  const TVector3 B = P.back();
  const TVector3 M = P[N/2];

  const double dx = (B.X() - A.X());
  const double dy = (B.Y() - A.Y());
  const double L  = std::hypot(dx, dy);
  if (!(L > 1e-12) || !std::isfinite(L)) return false;

  chordXY_internal_cm = L;
  if (posScale_cm_per_mm > 0.0) chordXY_mm = chordXY_internal_cm / posScale_cm_per_mm;

  const double mx = (M.X() - A.X());
  const double my = (M.Y() - A.Y());
  const double crossz = dx*my - dy*mx;

  const double s_signed = crossz / L;
  const double s_abs    = std::abs(s_signed);

  if (!std::isfinite(s_abs)) return false;

  sagitta_internal_cm_signed = s_signed;
  sagitta_internal_cm_abs    = s_abs;

  if (posScale_cm_per_mm > 0.0) {
    sagitta_mm_signed = sagitta_internal_cm_signed / posScale_cm_per_mm;
    sagitta_mm_abs    = sagitta_internal_cm_abs    / posScale_cm_per_mm;
  }
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
// NOTE: posScale_cm_per_mm MUST be the TOTAL scale used to convert mm->cm in this component,
// i.e. PositionUnitScale * InputHitPosScale.
static void addAtIPState(edm4hep::MutableTrack& trk,
                         const TVector3& pos_internal,
                         const TVector3& mom_GeV,
                         double posScale_cm_per_mm,
                         int chargeSign,
                         bool ptValid,
                         float invalidPTSentinel,
                         float omegaVar,
                         float pTOverrideOrNeg = -1.f) {
  using TP = edm4hep::TrackParams;

  const double inv_ps = (posScale_cm_per_mm > 0 ? 1.0/posScale_cm_per_mm : 10.0); // cm->mm
  const double x = pos_internal.X() * inv_ps;
  const double y = pos_internal.Y() * inv_ps;
  const double z = pos_internal.Z() * inv_ps;

  const double px = mom_GeV.X();
  const double py = mom_GeV.Y();
  const double pz = mom_GeV.Z();

  const double pT  = std::hypot(px, py);
  const double phi = std::atan2(py, px);
  const double tanL = (pT > 1e-12) ? (pz / pT) : 0.0;

  const double omegaSigned = (pT > 1e-12) ? (double(chargeSign) / pT) : 0.0;

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
  ts.setCovMatrix(1.0f,     TP::d0,        TP::d0);
  ts.setCovMatrix(1e-3f,    TP::phi,       TP::phi);
  ts.setCovMatrix(omegaVar, TP::omega,     TP::omega);
  ts.setCovMatrix(1.0f,     TP::z0,        TP::z0);
  ts.setCovMatrix(1e-2f,    TP::tanLambda, TP::tanLambda);

  trk.addToTrackStates(ts);
}

// Extract best fitted state near IP (robust selection).
// DOES NOT write to edm4hep. Returns selected state and q/pT etc.
// outPT is always computed from the selected fitted momentum.
// outIdx is the TrackPoint index chosen (for debugging).
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

      // sanity reject totally insane candidates early
      if (std::isfinite(publishPTMaxGeV) && publishPTMaxGeV > 0.0) {
        if (pt > 10.0 * publishPTMaxGeV) continue;
      }

      const double r2 = pos.Perp2();
      const double az = std::abs(pos.Z());
      if (!std::isfinite(r2) || !std::isfinite(az)) continue;

      const double di = double(i) - midIdx;
      const double score = r2 + zWeight*(az*az) + idxWeight*(di*di);

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

  // charge from rep: DEBUG ONLY (do not use for published omega)
  //int qrep = 0;
  //try { qrep = rep->getCharge(outState); } catch (...) { qrep = 0; }
  //if (qrep == 0) qrep = fallbackCharge;
  //outCharge = qrep; // <-- keep if you want to print it, but DO NOT use it for publishing


  TVector3 mom = outState.getMom();
  outPT = float(std::hypot(mom.X(), mom.Y()));
  if (!std::isfinite(outPT) || outPT <= 0.f) return false;

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

  // Safety: skip negative-type debug hit groups
  Gaudi::Property<bool> m_rejectNegativeTypeLabels{
    this,"RejectNegativeTypeLabels", true,
    "Skip hit groups with type(label) < 0 (e.g. debug types)."
  };

  // Use per-hit covariance from input hits
  Gaudi::Property<bool>   m_useInputHitCovariance{this,"UseInputHitCovariance", true,
    "Use TrackerHit3D.covMatrix for each measurement if available; otherwise use HitSigmaXYMM/HitSigmaZMM."};

  Gaudi::Property<double> m_inputHitPosScale{this,"InputHitPosScale", 1.0,
    "Scale factor applied to input hit positions (and covariances) if upstream wrote positions in scaled units (GGTF ThreeDHitPosScale)."};

  Gaudi::Property<double> m_minCovEigenvalue{this,"MinCovEigenvalue", 1e-8,
    "Minimum eigenvalue (in internal length units^2) used when PD-guarding measurement covariance."};

  // Publishing gates (prevents runaway pT)
  Gaudi::Property<double> m_publishPTMaxGeV{this,"PublishPTMaxGeV", 300.0,
    "Hard maximum pT to publish in TrackState.time; above this, publish invalid sentinel."};

  Gaudi::Property<double> m_publishPTMaxRatioToSeed{this,"PublishPTMaxRatioToSeed", 5.0,
    "Reject fitted pT if fitted pT > ratio * pTseed (only if seed is finite and >0)."};

  Gaudi::Property<double> m_publishPTMaxRatioToGeom{this,"PublishPTMaxRatioToGeom", 10.0,
    "Reject fitted pT if wildly inconsistent with geometry estimate (circle/sagitta) when available."};

  // Best fitted state selection weights
  Gaudi::Property<double> m_bestStateZWeight{this,"BestStateZWeight", 0.0,
    "Weight for choosing best fitted state: adds z^2 term (internal units) to r^2."};

  Gaudi::Property<double> m_bestStateIdxWeight{this,"BestStateIdxWeight", 1e-3,
    "Weight for choosing best fitted state: adds (idx-mid)^2 to discourage edge-pathologies."};

  // Hit ordering heuristic
  Gaudi::Property<bool> m_sortHitsByRZHeuristic{this,"SortHitsByRZHeuristic", true,
    "Sort hit order by robust heuristic using r and z spans BEFORE any phi-unwrapping."};

  // Tight 3D dedup to remove near-identical points (mm)
  Gaudi::Property<double> m_dedupEpsMM{this,"DedupEpsMM", 0.05,
    "If >0, drop hits closer than this in XYZ (mm) to avoid duplicates."};

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

  // Fallback measurement covariance (used if input cov not used or invalid)
  Gaudi::Property<double>  m_hitSigmaXYMM {this, "HitSigmaXYMM", 0.50, "XY sigma [mm]"};
  Gaudi::Property<double>  m_hitSigmaZMM  {this, "HitSigmaZMM",  2.00, "Z  sigma [mm]"};

  // Seed / robustness
  Gaudi::Property<double>  m_seedPosSigmaMM  {this, "SeedPosSigmaMM", 80.0, "Seed pos sigma [mm]"};
  Gaudi::Property<double>  m_seedMomSigmaGeV {this, "SeedMomSigmaGeV", 5.0,  "Seed mom sigma [GeV]"};
  Gaudi::Property<double>  m_seedPTMinGeV    {this, "SeedPTMinGeV",    0.20, "Min pT [GeV]"};
  Gaudi::Property<double>  m_seedPTMaxGeV    {this, "SeedPTMaxGeV",   200.0, "Max pT [GeV]"};
  Gaudi::Property<double>  m_seedPMinGeV     {this, "SeedPMinGeV",     0.05, "Min |p| [GeV] (numerical floor; not physics clamp)"};

  // Circle-fit quality / curvature observability
  Gaudi::Property<double>  m_minPhiSpanRad   {this, "MinPhiSpanRad", 0.03, "Minimum unwrapped φ-span (rad) to trust curvature"};
  Gaudi::Property<double>  m_maxCircleCond   {this, "MaxCircleCond", 1e6,  "Maximum acceptable condition estimate for circle LS solve"};
  Gaudi::Property<double>  m_minChordXYMM    {this, "MinChordXYMM", 50.0, "Minimum XY chord length [mm] to treat curvature as observable"};

  // Export policy
  Gaudi::Property<bool>    m_skipLowCurvObs  {this, "SkipLowCurvObs", true,
                                              "If true: do not export tracks where curvature is unobservable"};
  Gaudi::Property<double>  m_lowCurvSeedPTGeV{this, "LowCurvSeedPTGeV", 30.0,
                                              "Seed pT [GeV] used when curvature is unobservable (stability only)"};
  Gaudi::Property<float>   m_invalidPTSentinel {this, "InvalidPTSentinel", -1.0f, "TrackState.time when pT is not published"};
  Gaudi::Property<bool>    m_publishPTOnlyIfCurvObservable {this, "PublishPTOnlyIfCurvObservable", true,
                                                            "Only publish pT if curvature is observable"};
  Gaudi::Property<bool>    m_requireFittedStateForPT {this, "RequireFittedStateForPT", true,
                                                      "Never publish pT unless it comes from a fitted GenFit state"};
  Gaudi::Property<float>   m_omegaVarGood {this, "OmegaVarGood", 1e-4f, "(GeV^-1)^2 covariance for omega when curvature is observable and pT valid"};
  Gaudi::Property<float>   m_omegaVarBad  {this, "OmegaVarBad",  1.0f,  "(GeV^-1)^2 covariance for omega when pT invalid/unobservable"};

  // Sorting / dedup options (kept)
  Gaudi::Property<bool>    m_sortHits        {this, "SortHits", true, "Sort hits (φ order when possible; PCA fallback)"};
  Gaudi::Property<bool>    m_dedup           {this, "DeduplicateHits", true, "Drop nearly-identical hits (after sorting)"};
  Gaudi::Property<double>  m_dedupTolMM      {this, "DedupTolMM", 0.25, "Legacy dedup tol [mm] (used if DedupEpsMM<=0)"};

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
           << " | UseInputHitCovariance=" << (m_useInputHitCovariance.value() ? "true":"false")
           << " | InputHitPosScale=" << m_inputHitPosScale.value()
           << " | posScale=" << m_posScale.value()
           << " | MinCovEigenvalue=" << m_minCovEigenvalue.value()
           << " | PublishPTMaxGeV=" << m_publishPTMaxGeV.value()
           << " | PublishPTMaxRatioToSeed=" << m_publishPTMaxRatioToSeed.value()
           << " | PublishPTMaxRatioToGeom=" << m_publishPTMaxRatioToGeom.value()
           << " | BestStateZWeight=" << m_bestStateZWeight.value()
           << " | BestStateIdxWeight=" << m_bestStateIdxWeight.value()
           << " | SortHitsByRZHeuristic=" << (m_sortHitsByRZHeuristic.value() ? "true":"false")
           << " | DedupEpsMM=" << m_dedupEpsMM.value()
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
      os << ",\"UseInputHitCovariance\":" << (m_useInputHitCovariance.value() ? "true":"false");
      os << ",\"InputHitPosScale\":" << m_inputHitPosScale.value();
      os << ",\"MinCovEigenvalue\":" << m_minCovEigenvalue.value();
      os << ",\"PublishPTMaxGeV\":" << m_publishPTMaxGeV.value();
      os << ",\"PublishPTMaxRatioToSeed\":" << m_publishPTMaxRatioToSeed.value();
      os << ",\"PublishPTMaxRatioToGeom\":" << m_publishPTMaxRatioToGeom.value();
      os << ",\"BestStateZWeight\":" << m_bestStateZWeight.value();
      os << ",\"BestStateIdxWeight\":" << m_bestStateIdxWeight.value();
      os << ",\"RejectNegativeTypeLabels\":" << (m_rejectNegativeTypeLabels.value() ? "true":"false");
      os << ",\"SortHitsByRZHeuristic\":" << (m_sortHitsByRZHeuristic.value() ? "true":"false");
      os << ",\"DedupEpsMM\":" << m_dedupEpsMM.value();
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

  // Seed covariance in internal units
  TMatrixDSym makeSeedCov(double posInfl=1.0, double momInfl=1.0) const {
    TMatrixDSym C(6); C.Zero();
    const double sP = (m_seedPosSigmaMM.value() * posInfl) * (m_posScale.value() * m_inputHitPosScale.value()); // mm->cm with input scale
    const double sM = (m_seedMomSigmaGeV.value() * momInfl);
    for (int i = 0; i < 3; ++i) C(i, i) = sP * sP;
    for (int i = 3; i < 6; ++i) C(i, i) = sM * sM;
    ensurePD_chol(C, 1e-6, 4.0, 6);
    return C;
  }

  // Fallback measurement covariance in internal units (cm^2)
  TMatrixDSym fallbackMeasCovInternal() const {
    const double s = (m_posScale.value() * m_inputHitPosScale.value()); // mm -> cm (with input scale)
    const double sxy = m_hitSigmaXYMM.value() * s;
    const double sz  = m_hitSigmaZMM.value()  * s;
    TMatrixDSym C(3); C.Zero();
    C(0,0) = sxy*sxy;
    C(1,1) = sxy*sxy;
    C(2,2) = sz*sz;
    ensurePD_eigenClamp(C, m_minCovEigenvalue.value());
    return C;
  }

  // Build per-hit covariance from TrackerHit3D covMatrix with unit conversion and PD guard
  TMatrixDSym buildMeasCovFromHit(const edm4hep::TrackerHit3D& hit) const {
    // covMatrix is packed: (xx,xy,xz,yy,yz,zz) in stored units^2
    const auto C = hit.getCovMatrix();

    // total scaling from "stored position units" to internal cm:
    // internal = (stored * InputHitPosScale) * PositionUnitScale
    const double s = (m_posScale.value() * m_inputHitPosScale.value());
    const double k = s*s;

    TMatrixDSym cov(3); cov.Zero();
    cov(0,0) = k * double(C[0]);
    cov(0,1) = k * double(C[1]);
    cov(0,2) = k * double(C[2]);
    cov(1,1) = k * double(C[3]);
    cov(1,2) = k * double(C[4]);
    cov(2,2) = k * double(C[5]);
    cov(1,0) = cov(0,1);
    cov(2,0) = cov(0,2);
    cov(2,1) = cov(1,2);

    if (!(std::isfinite(cov(0,0)) && std::isfinite(cov(1,1)) && std::isfinite(cov(2,2)))) {
      return fallbackMeasCovInternal();
    }
    ensurePD_eigenClamp(cov, m_minCovEigenvalue.value());
    return cov;
  }

  edm4hep::TrackCollection
  operator()(const edm4hep::TrackerHit3DCollection& hits) const override {
    edm4hep::TrackCollection out;
    if (hits.size() < 3u) return out;

    // total scale used for mm->cm conversion in this component
    const double posScale_cm_per_mm = (m_posScale.value() * m_inputHitPosScale.value());

    // ----------------- group hits -----------------
    std::unordered_map<int, Group> groups;
    bool anyNonZero = false;
    groups.reserve(hits.size()/8 + 1);

    for (size_t i = 0; i < hits.size(); ++i) {
      const auto& h = hits[i];
      const int lbl = hitLabel(h);

      if (m_rejectNegativeTypeLabels.value() && lbl < 0) continue;

      anyNonZero = anyNonZero || (lbl != 0);

      const auto p = h.getPosition();

      // positions in mm (possibly scaled upstream), convert to internal cm
      const double s = posScale_cm_per_mm;
      TVector3 v(s*p.x, s*p.y, s*p.z);

      auto& g = groups[lbl];
      g.P.push_back(v);
      g.idxs.push_back(i);
    }

    // fallback only if ALL labels are 0 and enabled
    if (!anyNonZero && m_useFallbackClust.value()) {
      std::vector<TVector3> Pall; Pall.reserve(hits.size());
      std::vector<size_t>   Iall; Iall.reserve(hits.size());

      const double s = posScale_cm_per_mm;
      for (size_t i = 0; i < hits.size(); ++i) {
        const auto p = hits[i].getPosition();
        Pall.emplace_back(s*p.x, s*p.y, s*p.z);
        Iall.push_back(i);
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
          g.idxs.push_back(Iall[i]);
        }
        groups.swap(g2);
      }
    }

    // ----------------- fit helpers -----------------
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

      // --- downsample early (preserves current order) ---
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

      // --- deterministic ordering before any φ-unwrapping ---
      if (m_sortHitsByRZHeuristic.value()) sortByRZHeuristic(P, idxs);

      // --- 3D dedup (very tight) after deterministic ordering ---
      if (m_dedupEpsMM.value() > 0.0) {
        const double tol_cm = m_dedupEpsMM.value() * posScale_cm_per_mm; // mm -> cm
        dedupSorted3D(P, idxs, tol_cm*tol_cm);
      } else if (m_dedup.value() && !P.empty()) {
        const double tol2 = std::pow(m_dedupTolMM.value() * posScale_cm_per_mm, 2);
        dedupSorted3D(P, idxs, tol2);
      }
      if (P.size() < m_minGroupSize.value()) continue;

      // --- robust circle fit (order independent) ---
      TVector3 centerXY(0.,0.,0.);
      double R_int = 1e9;
      double cond  = 1e99;
      double rmsRes= 1e99;
      const bool circleOK = fitCircleLS_SVD_XY(P, centerXY, R_int, cond, rmsRes);

      double phiMin=0., phiMax=0., phiSpan=0.;
      bool phiOK = false;
      if (circleOK) phiOK = computePhiSpanUnwrapped(P, centerXY, phiMin, phiMax, phiSpan);

      const bool circleTrusted = circleOK && std::isfinite(cond) && (cond <= m_maxCircleCond.value());

      // --- sorting refinement (φ order when curvature looks meaningful; PCA fallback) ---
      if (m_sortHits.value()) {
        bool sorted = false;
        if (circleTrusted && phiOK && std::isfinite(phiSpan) && (phiSpan >= m_minPhiSpanRad.value())) {
          sorted = sortByUnwrappedPhi(P, idxs, centerXY, true);
        }
        if (!sorted) {
          (void)sortByPCAProjection(P, idxs);
        }
      }

      // --- chord + sagitta diagnostics (XY) after sorting ---
      double chordXY_internal_cm = 0.0;
      double chordXY_mm = 0.0;
      double sagitta_internal_cm_abs = 0.0;
      double sagitta_mm_abs = 0.0;
      double sagitta_internal_cm_signed = 0.0;
      double sagitta_mm_signed = 0.0;

      const bool sagOK = computeChordAndSagittaXY(
        P, posScale_cm_per_mm,
        chordXY_internal_cm, chordXY_mm,
        sagitta_internal_cm_abs, sagitta_mm_abs,
        sagitta_internal_cm_signed, sagitta_mm_signed
      );

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

      // Observability score (optional quality)
      const double scorePhi   = (m_minPhiSpanRad.value() > 0 ? (phiSpan / m_minPhiSpanRad.value()) : 0.0);
      const double scoreChord = (m_minChordXYMM.value() > 0 ? (chordXY_mm / m_minChordXYMM.value()) : 0.0);
      const float obsScore = float(std::max(0.0, std::min(scorePhi, scoreChord)));

      // --- diagnostic pT estimates from geometry ---
      double pT_circle = std::numeric_limits<double>::quiet_NaN();
      if (circleTrusted && std::isfinite(R_int) && (R_int > 0.0)) {
        const double R_m = R_int * m_internalLenToM.value();
        pT_circle = 0.3 * m_Bz.value() * R_m;
        if (!std::isfinite(pT_circle) || pT_circle <= 0.0) pT_circle = std::numeric_limits<double>::quiet_NaN();
      }

      double pT_sag = std::numeric_limits<double>::quiet_NaN();
      if (sagOK) {
        const double L_m = chordXY_internal_cm * m_internalLenToM.value();
        const double s_m = sagitta_internal_cm_abs * m_internalLenToM.value();
        if (std::isfinite(L_m) && std::isfinite(s_m) && (L_m > 1e-6) && (s_m > 1e-12)) {
          const double R_m = (L_m*L_m) / (8.0*s_m);
          if (std::isfinite(R_m) && (R_m > 0.0)) pT_sag = 0.3 * m_Bz.value() * R_m;
        }
      }

      const double pT_geom = std::isfinite(pT_circle) ? pT_circle : pT_sag;

      debug() << "Group[label=" << label << "] n=" << P.size()
              << " circleOK=" << (circleOK ? "true":"false")
              << " cond=" << cond
              << " phiSpan=" << phiSpan
              << " chordXY_mm=" << chordXY_mm
              << " sagitta_mm_abs=" << (sagOK ? sagitta_mm_abs : -999.0)
              << " pT_circle=" << (std::isfinite(pT_circle) ? pT_circle : -999.0)
              << " pT_sag=" << (std::isfinite(pT_sag) ? pT_sag : -999.0)
              << " curvObservable=" << (curvObservable ? "true":"false")
              << " obsScore=" << obsScore
              << endmsg;

      if (!curvObservable && m_skipLowCurvObs.value()) continue;

      // --- Seed pT (for convergence only) ---
      double pTseed = 0.0;
      if (curvObservable) {
        if (std::isfinite(pT_circle) && pT_circle > 0.0) pTseed = pT_circle;
        else if (std::isfinite(pT_sag) && pT_sag > 0.0) pTseed = pT_sag;
        else pTseed = m_lowCurvSeedPTGeV.value();
      } else {
        pTseed = m_lowCurvSeedPTGeV.value();
      }
      if (!std::isfinite(pTseed) || pTseed <= 0.0) pTseed = m_lowCurvSeedPTGeV.value();
      pTseed = std::clamp(pTseed, m_seedPTMinGeV.value(), m_seedPTMaxGeV.value());

      // ---- curvature sign diagnostics (geometry vs q*B) ----
      const int qSeed = chargeFromPDG(m_pdg.value());
      const int qPublish = qSeed;  // ALWAYS publish PDG-hypothesis charge sign

      const int sign_qB = sgn(double(qSeed) * m_Bz.value());
      int sign_geom = 0;
      if (sagOK) sign_geom = sgn(sagitta_internal_cm_signed);

      const double omega_seed = (std::isfinite(pTseed) && pTseed > 0.0) ? (double(qSeed) / pTseed) : 0.0;

      debug() << "CURV-SIGN[label=" << label << "] "
              << "qSeed=" << qSeed
              << " Bz=" << m_Bz.value()
              << " sign(qB)=" << sgnstr(sign_qB)
              << " sagSign(geom)=" << sgnstr(sign_geom)
              << " omega_seed(q/pT)=" << omega_seed
              << " curvObs=" << (curvObservable ? "true":"false")
              << " (note: sagSign depends on hit order)"
              << endmsg;

      // direction from sorted endpoints
      const TVector3 pos0 = P.front();
      const TVector3 posL = P.back();

      TVector3 dir  = (posL - pos0);
      if (dir.Mag2() < 1e-12) dir = TVector3(0,0,1);
      dir = dir.Unit();

      const double cosTheta = std::clamp(std::abs(dir.Z()), 0.0, 0.999999);
      const double sinTheta = std::sqrt(std::max(1e-4, 1.0 - cosTheta*cosTheta));

      double pMag = pTseed / sinTheta;
      if (!std::isfinite(pMag) || pMag <= 0) pMag = pTseed;
      pMag = std::max(pMag, m_seedPMinGeV.value());

      TVector3 mom0 = pMag * dir;

      // Build a track from points using per-hit covariances where possible
      auto buildTrackFromSeed = [&](genfit::Track& outTrack) -> void {
        int detId = label;
        int hitId = 0;
        for (size_t j = 0; j < P.size(); ++j) {
          const auto& v = P[j];
          const size_t idx = idxs[j];

          TVectorD pos(3);
          pos[0] = v.X();
          pos[1] = v.Y();
          pos[2] = v.Z();

          TMatrixDSym cov = fallbackMeasCovInternal();
          if (m_useInputHitCovariance.value()) {
            cov = buildMeasCovFromHit(hits[idx]);
          }

          auto* tp   = new genfit::TrackPoint(&outTrack);
          auto* meas = new genfit::SpacepointMeasurement(pos, TMatrixDSym(cov),
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
      buildTrackFromSeed(trk1);

      const genfit::FitStatus* fs1 = run_fit(trk1, "base(+mom)", label);
      const bool ok1 = (fs1 && has_any_FI(trk1));

      // Fit candidate #2: -mom0
      std::unique_ptr<genfit::Track> trk2_ptr;
      const genfit::FitStatus* fs2 = nullptr;
      bool ok2 = false;

      if (m_tryBothMomDirs.value()) {
        auto rep2_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
        trk2_ptr = std::make_unique<genfit::Track>(rep2_up.release(), pos0, -mom0);
        trk2_ptr->setCovSeed(makeSeedCov(1.0, 1.0));
        buildTrackFromSeed(*trk2_ptr);

        fs2 = run_fit(*trk2_ptr, "base(-mom)", label);
        ok2 = (fs2 && has_any_FI(*trk2_ptr));
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
      genfit::Track trkR_dummy;
      const genfit::FitStatus* fsR = nullptr;
      bool usedRetry = false;

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

        auto buildTrackRetry = [&](genfit::Track& outTrack)->void{
          int detId = label;
          int hitId = 0;
          for (size_t j = 0; j < P.size(); ++j) {
            const auto& v = P[j];
            const size_t idx = idxs[j];

            TVectorD pos(3);
            pos[0]=v.X(); pos[1]=v.Y(); pos[2]=v.Z();

            TMatrixDSym cov = fallbackMeasCovInternal();
            if (m_useInputHitCovariance.value()) cov = buildMeasCovFromHit(hits[idx]);

            // inflate diag
            cov(0,0) *= m_retryMeasInfl.value();
            cov(1,1) *= m_retryMeasInfl.value();
            cov(2,2) *= m_retryMeasInfl.value();
            ensurePD_eigenClamp(cov, m_minCovEigenvalue.value());

            auto* tp   = new genfit::TrackPoint(&outTrack);
            auto* meas = new genfit::SpacepointMeasurement(pos, TMatrixDSym(cov),
                                                           detId, hitId, tp,
                                                           false, false);
            tp->addRawMeasurement(meas);
            outTrack.insertPoint(tp);
            ++hitId;
          }
        };
        buildTrackRetry(trkR);

        fsR = run_fit(trkR, "retry(inflated)", label);
        const bool okR = (fsR && has_any_FI(trkR));

        if (okR) {
          // stash retry track by moving into dummy (keeps scope lifetime for pointer use below)
          trkR_dummy = std::move(trkR);
          bestTrk = &trkR_dummy;
          bestFs  = fsR;
          ok = true;
          usedRetry = true;
        } else {
          continue;
        }
      }

      if (!ok) continue;

      // ----------------- choose fitted state + compute pt validity -----------------
      genfit::MeasuredStateOnPlane bestState;
      int q_fit = qSeed;
      float fittedPT = 0.f;
      size_t fitIdx = 0;

      const bool haveBestState = selectBestFittedState(*bestTrk,
                                                       m_publishPTMaxGeV.value(),
                                                       m_bestStateZWeight.value(),
                                                       m_bestStateIdxWeight.value(),
                                                       bestState,
                                                       fittedPT,
                                                       fitIdx);
      if (!haveBestState) continue;

      const double omega_fit = (std::isfinite(double(fittedPT)) && fittedPT > 0.f) ? (double(qPublish)/double(fittedPT)) : 0.0;

      debug() << "FIT-SIGN[label=" << label << "] "
              << "fitIdx=" << fitIdx
              << " usedRetry=" << (usedRetry ? "true":"false")
              << " q_pub=" << qPublish
              << " pt_fit=" << fittedPT
              << " omega_fit(q/pT)=" << omega_fit
              << " seedPt=" << pTseed
              << " geomPt=" << (std::isfinite(pT_geom) ? pT_geom : -999.0)
              << endmsg;

      bool ptValid = true;
      if (m_publishPTOnlyIfCurvObservable.value()) ptValid = ptValid && curvObservable;
      if (m_requireFittedStateForPT.value()) ptValid = ptValid && true;

      ptValid = ptValid && std::isfinite(fittedPT) && (fittedPT > 0.0f) && (double(fittedPT) < m_publishPTMaxGeV.value());

      if (ptValid && std::isfinite(pTseed) && pTseed > 0.0) {
        if (double(fittedPT) > m_publishPTMaxRatioToSeed.value() * pTseed) ptValid = false;
      }
      if (ptValid && std::isfinite(pT_geom) && pT_geom > 0.0) {
        const double r = double(fittedPT) / pT_geom;
        if (!std::isfinite(r) || r > m_publishPTMaxRatioToGeom.value() || r < 1.0/m_publishPTMaxRatioToGeom.value())
          ptValid = false;
      }

      const float omegaVar = ptValid ? m_omegaVarGood.value() : m_omegaVarBad.value();

      if (!ptValid) {
        info() << "pT REJECTED[label=" << label << "]"
               << " pT_fit=" << fittedPT
               << " pTseed=" << pTseed
               << " pT_geom=" << (std::isfinite(pT_geom) ? pT_geom : -999.0)
               << " omega_fit=" << omega_fit
               << " omega_seed=" << omega_seed
               << " sign(qB)=" << sgnstr(sign_qB)
               << " sagSign=" << sgnstr(sign_geom)
               << " phiSpan=" << phiSpan
               << " chordXY_mm=" << chordXY_mm
               << " sagitta_mm_abs=" << (sagOK ? sagitta_mm_abs : -999.0)
               << endmsg;
      }

      // ----------------- export edm4hep track -----------------
      auto trk = out.create();
      trk.setType(m_pdg.value());
      try { trk.setChi2(bestFs->getChi2()); trk.setNdf(bestFs->getNdf()); } catch (...) {}

      for (auto i : idxs) trk.addToTrackerHits(hits[i]);

      // Export EXACTLY ONE authoritative state (AtIP) based on selected fitted state.
      const TVector3 pos_cm = bestState.getPos();
      const TVector3 mom    = bestState.getMom();

      addAtIPState(trk,
                   pos_cm,
                   mom,
                   /*posScale_cm_per_mm=*/posScale_cm_per_mm,
                   /*chargeSign=*/qPublish,
                   /*ptValid=*/ptValid,
                   m_invalidPTSentinel.value(),
                   omegaVar,
                   /*pTOverrideOrNeg=*/fittedPT);

    } // groups loop

    return out;
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }

private:
  mutable std::unique_ptr<genfit::KalmanFitterRefTrack> m_fitter;
  k4FWCore::MetaDataHandle<std::string> m_cfgMeta;
};

DECLARE_COMPONENT(GenFit2DCHFitter)
