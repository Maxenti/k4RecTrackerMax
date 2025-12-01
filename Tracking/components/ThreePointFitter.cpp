// ======================================================================
// ThreePointFitter.cpp  -- ultra-simple 3-point pT fitter for GGTF 3D hits
//   * Groups by GGTF label stored in TrackerHit3D::type
//   * For each group: pick three XY points (min-φ, median-φ, max-φ) about origin
//   * Circle from 3 points (XY) -> R_mm -> pT = 0.0003 * B[T] * R[mm]
//   * Optional crude tanLambda via linear z(phi) regression
//   * Writes one EDM4hep Track per group with TrackState(AtIP):
//       - ts.time  = pT [GeV]   (for easy downstream pT use)
//       - ts.omega = q / pT     [GeV^-1] (EDM/LCIO convention)
//   * Verbose diagnostics (toggleable) dump the chosen points and geometry
// ======================================================================

#include <vector>
#include <cmath>
#include <limits>
#include <algorithm>
#include <unordered_map>
#include <numeric>
#include <string>
#include <tuple>

#include "Gaudi/Algorithm.h"
#include "Gaudi/Property.h"
#include "GaudiKernel/ISvcLocator.h"

#include "k4FWCore/Transformer.h"

#include "edm4hep/TrackerHit3DCollection.h"
#include "edm4hep/TrackCollection.h"
#include "edm4hep/TrackState.h"

#include "TVector3.h"

namespace {

inline int chargeFromPDG(int pdg) {
  const int a = std::abs(pdg);
  if (a==11||a==13||a==15) return (pdg>0?-1:+1);
  if (a==211||a==321||a==2212) return (pdg>0?+1:-1);
  return (pdg>=0?+1:-1);
}

struct CircRes { TVector3 C; double R{1e12}; bool ok{false}; };

// 3-point circle in XY; returns false if nearly colinear
inline CircRes circle_from_3pts_xy(const TVector3& A, const TVector3& B, const TVector3& C) {
  const double x1=A.X(), y1=A.Y(), x2=B.X(), y2=B.Y(), x3=C.X(), y3=C.Y();
  const double a = x1*(y2 - y3) - y1*(x2 - x3) + x2*y3 - x3*y2;
  const double d = 2.0 * a;
  CircRes r;
  if (std::abs(d) < 1e-9) return r;
  const double x1s=x1*x1, y1s=y1*y1, x2s=x2*x2, y2s=y2*y2, x3s=x3*x3, y3s=y3*y3;
  const double cx = ((x1s+y1s)*(y2-y3) + (x2s+y2s)*(y3-y1) + (x3s+y3s)*(y1-y2)) / d;
  const double cy = ((x1s+y1s)*(x3-x2) + (x2s+y2s)*(x1-x3) + (x3s+y3s)*(x2-x1)) / d;
  const double R  = std::hypot(x1-cx, y1-cy);
  if (!(std::isfinite(R) && R>1e-6)) return r;
  r.C = TVector3(cx, cy, 0.0);
  r.R = R;
  r.ok = true;
  return r;
}

inline double unwrap_to_ref(double a, double ref) {
  double d = a - ref;
  while (d >  M_PI) d -= 2*M_PI;
  while (d < -M_PI) d += 2*M_PI;
  return ref + d;
}

// signed distance of point P to line AB in XY (mm)
inline double signed_dist_to_chord_xy(const TVector3& A, const TVector3& B, const TVector3& P) {
  const TVector3 AB = B - A;
  const TVector3 AP = P - A;
  const double   L  = std::hypot(AB.X(), AB.Y());
  if (L < 1e-12) return 0.0;
  // 2D cross product magnitude divided by |AB|
  const double cross = AB.X()*AP.Y() - AB.Y()*AP.X();
  return cross / L;
}

// Fill an EDM4hep TrackState at IP using perigee-like definitions.
// Convention: omega = q/pT [GeV^-1]; time = pT [GeV]
inline void addAtIPState(edm4hep::MutableTrack& trk,
                         const TVector3& Pmin,
                         const TVector3& tangentUnit,
                         double pT_GeV,
                         double tanL,
                         int qSign)
{
  using TP = edm4hep::TrackParams;

  const double phi = std::atan2(tangentUnit.Y(), tangentUnit.X());
  const double d0  = -( Pmin.X()*std::sin(phi) - Pmin.Y()*std::cos(phi) );
  const double z0  =   Pmin.Z() - ( Pmin.X()*std::cos(phi) + Pmin.Y()*std::sin(phi) ) * tanL;
  const double omega = (pT_GeV>1e-12 ? (qSign / pT_GeV) : 0.0); // GeV^-1

  edm4hep::TrackState ts;
  ts.location       = edm4hep::TrackState::AtIP;
  ts.referencePoint = {0.f,0.f,0.f};
  ts.phi            = float(phi);
  ts.tanLambda      = float(tanL);
  ts.D0             = float(d0);
  ts.Z0             = float(z0);
  ts.omega          = float(omega);
  ts.time           = float(pT_GeV); // store pT directly for convenience

  // simple diagonal covariances (placeholders; tune if desired)
  ts.setCovMatrix(1.0f,   TP::d0,        TP::d0);
  ts.setCovMatrix(1e-3f,  TP::phi,       TP::phi);
  ts.setCovMatrix(1e-6f,  TP::omega,     TP::omega); // GeV^-2
  ts.setCovMatrix(1.0f,   TP::z0,        TP::z0);
  ts.setCovMatrix(1e-2f,  TP::tanLambda, TP::tanLambda);

  trk.addToTrackStates(ts);
}

} // namespace

// ----------------- Algorithm -----------------
struct ThreePointFitter final
  : k4FWCore::Transformer<edm4hep::TrackCollection (const edm4hep::TrackerHit3DCollection&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  ThreePointFitter(const std::string& name, ISvcLocator* svcLoc)
  : Transformer(name, svcLoc,
      std::tuple<KeyValues>{ KeyValues{"inputHits",  std::vector<std::string>{"GGTF_3DHits"}} },
      std::tuple<KeyValues>{ KeyValues{"outputTracks", std::vector<std::string>{"ThreePointTracks"}} })
  {}

  // ---- knobs ----
  Gaudi::Property<double>   m_Bz        {this, "Bz", 2.0, "Uniform B [Tesla] for pT conversion"};
  Gaudi::Property<int>      m_pdg       {this, "PDG", 13, "PDG hypothesis (charge sign only)"};
  Gaudi::Property<unsigned> m_minHits   {this, "MinHitsPerGroup", 3u, "Minimum hits per GGTF label to fit"};
  Gaudi::Property<double>   m_minChord  {this, "MinChordMM", 5.0, "Min chord length among the 3 picked points [mm]"};
  Gaudi::Property<double>   m_minRmm    {this, "MinRadiusMM", 100.0, "Reject tiny circles R < this [mm]"};
  Gaudi::Property<double>   m_minDeltaPhi {this, "MinDeltaPhi", 0.10, "Require φ_max-φ_min >= this [rad] (about origin)"};
  Gaudi::Property<bool>     m_doTanL    {this, "FitTanLambda", true, "Estimate tanLambda from z(phi) linear fit"};

  // Diagnostics
  Gaudi::Property<bool>     m_printDiag {this, "PrintDiagnostics", true, "Print per-track geometry diagnostics"};
  Gaudi::Property<int>      m_diagEvery {this, "DiagEveryN", 1, "Print every N-th track (per event grouping)"};

  StatusCode initialize() override {
    info() << "ThreePointFitter init | Bz[T]=" << m_Bz.value()
           << " | PDG=" << m_pdg.value()
           << " | MinHitsPerGroup=" << m_minHits.value()
           << " | MinChordMM=" << m_minChord.value()
           << " | MinRadiusMM=" << m_minRmm.value()
           << " | MinDeltaPhi=" << m_minDeltaPhi.value()
           << " | FitTanLambda=" << (m_doTanL.value()?"true":"false")
           << " | PrintDiagnostics=" << (m_printDiag.value()?"true":"false")
           << " | DiagEveryN=" << m_diagEvery.value()
           << endmsg;
    return StatusCode::SUCCESS;
  }

  edm4hep::TrackCollection operator()(const edm4hep::TrackerHit3DCollection& hits) const override {
    edm4hep::TrackCollection out;
    if (hits.empty()) return out;

    // 1) Bucket hits by their GGTF label stored in 'type'.
    std::unordered_map<int, std::vector<size_t>> groups;
    groups.reserve(hits.size()/6 + 1);
    bool anyNonZero = false;

    for (size_t i=0;i<hits.size();++i) {
      int label = 0;
      try { label = int(hits[i].getType()); } catch (...) { label = 0; }
      if (label != 0) anyNonZero = true;
      groups[label].push_back(i);
    }

    // If we have any non-zero labels, drop the 0/noise bucket.
    if (anyNonZero && groups.count(0)) groups.erase(0);

    const int qSign = chargeFromPDG(m_pdg.value());
    int trkCount = 0;

    // 2) Per-group 3-point fit
    for (auto& kv : groups) {
      auto& idxs = kv.second;
      if (idxs.size() < m_minHits.value()) continue;

      // Build a local array of points (mm) and angles about the origin
      std::vector<TVector3> P; P.reserve(idxs.size());
      std::vector<double>   PHI; PHI.reserve(idxs.size());
      for (auto k : idxs) {
        const auto p = hits[k].getPosition();
        P.emplace_back(p.x, p.y, p.z); // mm
        PHI.emplace_back(std::atan2(p.y, p.x));     // about origin
      }

      // Order by φ and choose min-φ, median-φ, max-φ
      std::vector<size_t> ord(P.size()); std::iota(ord.begin(), ord.end(), 0);
      std::sort(ord.begin(), ord.end(), [&](size_t a, size_t b){ return PHI[a] < PHI[b]; });

      const size_t iMinPhi = ord.front();
      const size_t iMaxPhi = ord.back();
      const size_t iMedPhi = ord[ord.size()/2];

      const TVector3 A = P[iMinPhi];
      const TVector3 C = P[iMedPhi];
      const TVector3 B = P[iMaxPhi];

      const double dPhi = PHI[iMaxPhi] - PHI[iMinPhi];
      if (dPhi < m_minDeltaPhi.value()) continue; // too little lever arm in φ

      // Guard: min chord lengths
      const double L_AB = (A-B).Mag();
      const double L_BC = (B-C).Mag();
      const double L_CA = (C-A).Mag();
      const double minChord = std::min({L_AB, L_BC, L_CA});
      if (!(minChord >= m_minChord.value())) continue;

      // Circle from these 3 points
      CircRes cir = circle_from_3pts_xy(A,B,C);
      if (!cir.ok) continue;
      const double R_mm = cir.R;
      if (R_mm < m_minRmm.value()) continue; // reject tiny R (degenerate)

      // Choose a "perigee-like" point as Pmin (closest to origin)
      size_t iPmin = 0; double r2Pmin = std::numeric_limits<double>::infinity();
      for (size_t i=0;i<P.size();++i){ const double r2=P[i].Perp2(); if (r2<r2Pmin){r2Pmin=r2; iPmin=i;} }
      const TVector3 Pmin = P[iPmin];

      // Tangent at Pmin: perpendicular to the radius vector from center
      TVector3 rvec(Pmin.X()-cir.C.X(), Pmin.Y()-cir.C.Y(), 0.0);
      if (rvec.Perp2() == 0) rvec = TVector3(1,0,0);
      const TVector3 rhat = rvec.Unit();
      TVector3 that(-rhat.Y(), rhat.X(), 0.0); // 90° CCW
      that = that.Unit();

      // crude tanLambda: linear fit z(phi) across all points using this center
      double tanL = 0.0;
      if (m_doTanL.value() && R_mm > 1e-6) {
        std::vector<double> phi(P.size());
        for (size_t j=0;j<P.size();++j) phi[j]=std::atan2(P[j].Y()-cir.C.Y(), P[j].X()-cir.C.X());
        for (size_t j=1;j<P.size();++j) phi[j]=unwrap_to_ref(phi[j], phi[j-1]);
        double S1=0, Sph=0, Sz=0, Sphp=0, Sphz=0;
        for (size_t j=0;j<P.size();++j) {
          const double ph = phi[j];
          const double z  = P[j].Z();
          S1+=1; Sph+=ph; Sz+=z; Sphp+=ph*ph; Sphz+=ph*z;
        }
        const double det = S1*Sphp - Sph*Sph;
        if (std::fabs(det) > 1e-12) {
          const double b = (S1*Sphz - Sph*Sz)/det; // dz/dphi
          tanL = b / R_mm;
        }
      }

      // pT from radius (R in mm, B in Tesla)
      const double pT = 0.0003 * m_Bz.value() * R_mm; // GeV

      // Geometric sagitta (middle point C relative to chord AB)
      const double sag_signed = signed_dist_to_chord_xy(A, B, C);
      const double sag = std::fabs(sag_signed);

      // Emit track
      auto trk = out.create();
      trk.setType(m_pdg.value());
      for (auto k : idxs) trk.addToTrackerHits(hits[k]);

      addAtIPState(trk, Pmin, that, pT, tanL, qSign);

      // Diagnostics
      if (m_printDiag.value()) {
        const bool doPrint = (m_diagEvery.value() <= 1) ? true : ((trkCount % m_diagEvery.value()) == 0);
        if (doPrint) {
          info()
            << "[TPFit] label=" << kv.first
            << "  N=" << idxs.size()
            << "  dPhi=" << dPhi
            << "  L_AB=" << L_AB << "mm"
            << "  sag=" << sag << "mm"
            << "  R=" << R_mm << "mm"
            << "  pT=" << pT << " GeV"
            << " | A(" << A.X() << "," << A.Y() << ")"
            << "  C(" << C.X() << "," << C.Y() << ")"
            << "  B(" << B.X() << "," << B.Y() << ")"
            << endmsg;
        }
      }

      ++trkCount;
    }

    if (m_printDiag.value()) {
      info() << "[TPFit] tracks emitted: " << trkCount << endmsg;
    }
    return out;
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }
};

DECLARE_COMPONENT(ThreePointFitter)
