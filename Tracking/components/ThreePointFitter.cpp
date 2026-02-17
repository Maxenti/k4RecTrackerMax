/*
DOC:
Title: ThreePointFitterFromGGTFTracks (Ultra-simple 3-point pT fitter from GGTF_tracking output)
Summary:
  Gaudi/k4FWCore Transformer that consumes GGTF_tracking’s clustered DCH track candidates
  (extension::TrackCollection) together with the persisted GGTF wire-hit collection
  (extension::SenseWireHitCollection). For each GGTF candidate, it reconstructs a minimal
  set of 3D proxy points from the referenced SenseWireHits, selects three points in XY
  (min-φ, median-φ, max-φ), fits a circle through those 3 points, and converts the fitted
  radius to pT using pT[GeV] = 0.0003 * Bz[T] * R[mm]. Optionally estimates tanLambda via
  a crude z(phi) linear regression.

  Outputs one edm4hep::Track per GGTF candidate, filling TrackState(AtIP) with a minimal
  helix parameterization:
    - omega = q/pT  [GeV^-1] (EDM/LCIO convention)
    - time  = pT    [GeV]   (convenience)
  and attaches a per-track derived edm4hep::TrackerHit3DCollection (fit points) to the
  output tracks via Track.trackerHits relations.

Primary Use Cases:
  - Fast “smoke test” of GGTF clustering quality and basic curvature scale.
  - Quick pT sanity checks without GenFit2/ACTS/Kalman dependencies.
  - Debugging sign conventions (Bz, charge sign, phi ordering) and lever-arm issues.
  - Producing self-contained edm4hep tracks and attached 3D points for ROOT/PODIO QA.

Not Intended For:
  - Precision fitting (only 3-point circle; very sensitive to outliers and noise).
  - Drift-chamber physics modeling (no left/right resolution, no drift-time residuals).
  - Comparable performance evaluation vs GenFit2/ACTS fits.

Algorithm Behavior:
  For each candidate in inputGGTFTracks:
    1) Identify referenced wire hits via Track.trackerHits ObjectID matching the
       inputWireHits collectionID.
    2) Convert each SenseWireHit -> 3D point:
         - Build wire direction from (wireAzimuthalAngle, wireStereoAngle).
         - Compute local xprime and construct Mmid using distanceToWire (default),
           or optionally use the wire position directly.
    3) Compute φ about origin for each point; choose:
         - A = min φ, B = max φ, C = median φ (by φ ordering)
       and require φ span >= MinDeltaPhi.
    4) Fit circle through (A,B,C) in XY; reject if nearly colinear or R < MinRadiusMM.
    5) pT = 0.0003 * Bz[T] * R[mm].
    6) Optional tanLambda via z(phi) regression using φ about fitted circle center.
    7) Create edm4hep::Track with TrackState(AtIP), attach outputFitHits (TrackerHit3D)
       to the track via relations.

Inputs:
  - inputGGTFTracks (extension::TrackCollection)
      Default: "CDCHTracks"
      Description: Track candidates from GGTF_tracking; each track’s trackerHits relation
      includes (among other things) wire hits that refer to the persisted output wire-hit collection.
  - inputWireHits (extension::SenseWireHitCollection)
      Default: "GGTF_SenseWireHits"
      Description: Persisted wire hits produced by GGTF_tracking. Used to rebuild 3D proxy
      points for this 3-point fit.

Outputs:
  - outputTracks (edm4hep::TrackCollection)
      Default: "ThreePointTracks"
      Description: One fitted edm4hep track per accepted GGTF candidate.
      TrackState(AtIP):
        * phi, D0, Z0, tanLambda (optional), omega=q/pT, time=pT.
      Track.trackerHits:
        * points from outputFitHits attached (self-contained for downstream QA).
  - outputFitHits (edm4hep::TrackerHit3DCollection)
      Default: "ThreePointFitHits"
      Description: Derived 3D proxy points (Mmid or wire position) used to select A/B/C
      and (optionally) tanLambda. These are not physical drift measurements.

Collections:
  - Consumes:
      * extension::TrackCollection
      * extension::SenseWireHitCollection
  - Produces:
      * edm4hep::TrackCollection
      * edm4hep::TrackerHit3DCollection

Connects-To:
  - Upstream: GGTF_tracking
  - Downstream:
      * ROOT/PODIO QA scripts reading edm4hep tracks and their attached hits
      * quick curvature/pT sanity plots
      * diagnostic comparisons vs full fitters (GenFit2/ACTS)

Key Properties / Arguments:
  - Bz (double, default=2.0):
      Uniform Bz [Tesla] for pT conversion: pT = 0.0003 * Bz * R_mm.
  - PDG (int, default=13):
      Sets charge sign used for omega=q/pT only.
  - MinHitsPerTrack (unsigned, default=3):
      Minimum referenced wire hits required to attempt a 3-point fit.
  - UseMmidPoint (bool, default=true):
      Use GGTF-style Mmid point from (distanceToWire, xprime). If false, uses wire position.
  - MinChordMM (double, default=5.0):
      Require minimum chord length among (A,B,C) to avoid degeneracy.
  - MinRadiusMM (double, default=100.0):
      Reject tiny circles R < this threshold.
  - MinDeltaPhi (double, default=0.10):
      Require φ_max - φ_min about origin >= this lever-arm.
  - FitTanLambda (bool, default=true):
      Estimate tanLambda via linear fit z(phi) (very crude).
  - PrintDiagnostics (bool, default=true), DiagEveryN (int, default=1):
      Verbose per-track geometry diagnostics.

Notes:
  - This fitter is intentionally fragile and diagnostic-oriented.
  - Best used as a quick check that GGTF groups correspond to sensible curvature.
  - For physics-quality results, prefer GenFit2DCHFitter or ACTS-based fitting.

Example Usage:
  - Gaudi options snippet (Python):
      from Configurables import GGTF_tracking, ThreePointFitterFromGGTFTracks, ApplicationMgr
      ggtf = GGTF_tracking("GGTF_tracking",
                           OutputTracksGGTF=["CDCHTracks"],
                           OutputWireHitsGGTF=["GGTF_SenseWireHits"])
      tp   = ThreePointFitterFromGGTFTracks("ThreePointFitterFromGGTFTracks",
                                           inputGGTFTracks=["CDCHTracks"],
                                           inputWireHits=["GGTF_SenseWireHits"],
                                           outputTracks=["ThreePointTracks"],
                                           outputFitHits=["ThreePointFitHits"],
                                           Bz=2.0, PDG=13,
                                           MinDeltaPhi=0.15,
                                           PrintDiagnostics=True)
      ApplicationMgr(TopAlg=[ggtf, tp], EvtMax=-1)

Tags:
  tracking, drift-chamber, DCH, GGTF, three-point-fit, circle-fit, helix, diagnostics, gaudi, k4run, edm4hep, podio
DOC_END
*/

// ======================================================================
// ThreePointFitterFromGGTFTracks.cpp  -- ultra-simple 3-point pT fitter
//   * Input: extension::TrackCollection (GGTF candidates)
//   * Input: extension::SenseWireHitCollection (persisted GGTF wire hits)
//   * For each GGTF candidate:
//       - build 3D proxy points from referenced SenseWireHits (Mmid by default)
//       - pick three XY points by φ about origin: min-φ, median-φ, max-φ
//       - fit circle through 3 points -> R_mm -> pT
//       - optional tanLambda via z(phi) regression about fitted circle center
//   * Output: edm4hep::TrackCollection with TrackState(AtIP)
//       - ts.time  = pT [GeV]
//       - ts.omega = q/pT [GeV^-1]
//   * Output: edm4hep::TrackerHit3DCollection with derived fit points
//       - output tracks attach these hits via Track.trackerHits relations
// ======================================================================

#include <vector>
#include <cmath>
#include <limits>
#include <algorithm>
#include <numeric>
#include <string>

#include "Gaudi/Property.h"
#include "GaudiKernel/ISvcLocator.h"

#include "k4FWCore/Transformer.h"

#include "edm4hep/TrackCollection.h"
#include "edm4hep/TrackState.h"
#include "edm4hep/TrackerHit3DCollection.h"

#include "TVector3.h"

// GGTF EDM extensions
#include "extension/TrackCollection.h"
#include "extension/SenseWireHitCollection.h"

namespace {

inline int chargeFromPDG(int pdg) {
  const int a = std::abs(pdg);
  if (a==11||a==13||a==15) return (pdg>0?-1:+1);
  if (a==211||a==321||a==2212) return (pdg>0?+1:-1);
  return (pdg>=0?+1:-1);
}

static TVector3 safe_unit(const TVector3& v, const TVector3& fallback) {
  const double m2 = v.Mag2();
  if (!(m2 > 0.0) || !std::isfinite(m2)) return fallback;
  return (1.0 / std::sqrt(m2)) * v;
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
  ts.time           = float(pT_GeV);

  // simple diagonal covariances (placeholders)
  ts.setCovMatrix(1.0f,   TP::d0,        TP::d0);
  ts.setCovMatrix(1e-3f,  TP::phi,       TP::phi);
  ts.setCovMatrix(1e-6f,  TP::omega,     TP::omega);
  ts.setCovMatrix(1.0f,   TP::z0,        TP::z0);
  ts.setCovMatrix(1e-2f,  TP::tanLambda, TP::tanLambda);

  trk.addToTrackStates(ts);
}

} // namespace

// ----------------- Algorithm -----------------
// MultiTransformer because we output both tracks and a hit collection that the tracks reference.
struct ThreePointFitterFromGGTFTracks final
  : k4FWCore::MultiTransformer<std::tuple<edm4hep::TrackCollection, edm4hep::TrackerHit3DCollection>(
        const extension::TrackCollection&,
        const extension::SenseWireHitCollection&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  ThreePointFitterFromGGTFTracks(const std::string& name, ISvcLocator* svcLoc)
  : MultiTransformer(name, svcLoc,
      { KeyValues{"inputGGTFTracks", std::vector<std::string>{"CDCHTracks"}},
        KeyValues{"inputWireHits",   std::vector<std::string>{"GGTF_SenseWireHits"}} },
      { KeyValues{"outputTracks",    std::vector<std::string>{"ThreePointTracks"}},
        KeyValues{"outputFitHits",   std::vector<std::string>{"ThreePointFitHits"}} })
  {}

  // ---- knobs ----
  Gaudi::Property<double>   m_Bz        {this, "Bz", 2.0, "Uniform B [Tesla] for pT conversion"};
  Gaudi::Property<int>      m_pdg       {this, "PDG", 13, "PDG hypothesis (charge sign only)"};

  Gaudi::Property<unsigned> m_minHits   {this, "MinHitsPerTrack", 3u, "Minimum referenced wire hits to fit"};
  Gaudi::Property<double>   m_minChord  {this, "MinChordMM", 5.0, "Min chord length among the 3 picked points [mm]"};
  Gaudi::Property<double>   m_minRmm    {this, "MinRadiusMM", 100.0, "Reject tiny circles R < this [mm]"};
  Gaudi::Property<double>   m_minDeltaPhi {this, "MinDeltaPhi", 0.10, "Require φ_max-φ_min >= this [rad] (about origin)"};
  Gaudi::Property<bool>     m_doTanL    {this, "FitTanLambda", true, "Estimate tanLambda from z(phi) linear fit"};

  // Convert SenseWireHit -> point
  Gaudi::Property<bool>     m_useMmid   {this, "UseMmidPoint", true, "Use GGTF-style Mmid points (recommended)"};

  // Output hit covariance (diagonal) for TrackerHit3D (mm^2)
  Gaudi::Property<float>    m_hitVarXY  {this, "HitVarXY",  1.0f, "var(x)=var(y) for output fit hits [mm^2]"};
  Gaudi::Property<float>    m_hitVarZ   {this, "HitVarZ",   1.0f, "var(z) for output fit hits [mm^2]"};

  // Diagnostics
  Gaudi::Property<bool>     m_printDiag {this, "PrintDiagnostics", true, "Print per-track geometry diagnostics"};
  Gaudi::Property<int>      m_diagEvery {this, "DiagEveryN", 1, "Print every N-th track"};

  StatusCode initialize() override {
    info() << "ThreePointFitterFromGGTFTracks init | Bz[T]=" << m_Bz.value()
           << " | PDG=" << m_pdg.value()
           << " | MinHitsPerTrack=" << m_minHits.value()
           << " | MinChordMM=" << m_minChord.value()
           << " | MinRadiusMM=" << m_minRmm.value()
           << " | MinDeltaPhi=" << m_minDeltaPhi.value()
           << " | FitTanLambda=" << (m_doTanL.value()?"true":"false")
           << " | UseMmidPoint=" << (m_useMmid.value()?"true":"false")
           << " | PrintDiagnostics=" << (m_printDiag.value()?"true":"false")
           << " | DiagEveryN=" << m_diagEvery.value()
           << endmsg;
    return StatusCode::SUCCESS;
  }

  std::tuple<edm4hep::TrackCollection, edm4hep::TrackerHit3DCollection>
  operator()(const extension::TrackCollection& ggtfTracks,
             const extension::SenseWireHitCollection& wireHits) const override {

    edm4hep::TrackCollection outTracks;
    edm4hep::TrackerHit3DCollection outFitHits;

    if (ggtfTracks.empty() || wireHits.empty()) {
      return std::make_tuple(std::move(outTracks), std::move(outFitHits));
    }

    const auto wireCollID = wireHits[0].getObjectID().collectionID;
    const int  qSign      = chargeFromPDG(m_pdg.value());

    int trkCount = 0;

    for (const auto& cand : ggtfTracks) {

      // Extract indices of wire hits referenced by this GGTF candidate
      std::vector<int> wireIdx;
      wireIdx.reserve(64);

      for (const auto& rel : cand.getTrackerHits()) {
        const auto oid = rel.getObjectID();
        if (oid.collectionID != wireCollID) continue;
        if (oid.index < 0 || oid.index >= (int)wireHits.size()) continue;
        wireIdx.push_back(oid.index);
      }

      if (wireIdx.size() < std::max<unsigned>(m_minHits.value(), 3u)) continue;

      // Build 3D proxy points from wire hits
      std::vector<TVector3> P;
      P.reserve(wireIdx.size());

      for (int idx : wireIdx) {
        const auto& h  = wireHits[idx];
        const auto  wp = h.getPosition();

        const double d   = double(h.getDistanceToWire());
        const double phi = double(h.getWireAzimuthalAngle());
        const double st  = double(h.getWireStereoAngle());

        TVector3 wpos(wp.x, wp.y, wp.z);

        // wire direction
        TVector3 dir(0,0,1);
        dir.RotateX(st);
        dir.RotateZ(phi);
        dir = safe_unit(dir, TVector3(0,0,1));

        // local xprime basis
        TVector3 xprime(1.0, 0.0, -dir.X() / std::max(1e-12, dir.Z()));
        xprime = safe_unit(xprime, TVector3(1,0,0));
        TVector3 yprime = dir.Cross(xprime);
        yprime = safe_unit(yprime, TVector3(0,1,0));
        xprime = safe_unit(yprime.Cross(dir), TVector3(1,0,0));

        TVector3 point = wpos;
        if (m_useMmid.value()) {
          const TVector3 L = wpos + xprime * (-d);
          const TVector3 R = wpos + xprime * (+d);
          point = 0.5 * (L + R);
        }
        P.push_back(point);
      }

      if (P.size() < 3) continue;

      // φ about origin; choose min, median, max
      std::vector<double> PHI(P.size());
      for (size_t i=0;i<P.size();++i) PHI[i] = std::atan2(P[i].Y(), P[i].X());

      std::vector<size_t> ord(P.size()); std::iota(ord.begin(), ord.end(), 0);
      std::sort(ord.begin(), ord.end(), [&](size_t a, size_t b){ return PHI[a] < PHI[b]; });

      const size_t iMin = ord.front();
      const size_t iMax = ord.back();
      const size_t iMed = ord[ord.size()/2];

      const TVector3 A = P[iMin];
      const TVector3 B = P[iMax];
      const TVector3 C = P[iMed];

      const double dPhi = PHI[iMax] - PHI[iMin];
      if (dPhi < m_minDeltaPhi.value()) continue;

      // chord guards
      const double L_AB = (A-B).Mag();
      const double L_BC = (B-C).Mag();
      const double L_CA = (C-A).Mag();
      const double minChord = std::min({L_AB, L_BC, L_CA});
      if (!(minChord >= m_minChord.value())) continue;

      // 3-point circle
      CircRes cir = circle_from_3pts_xy(A,B,C);
      if (!cir.ok) continue;
      const double R_mm = cir.R;
      if (R_mm < m_minRmm.value()) continue;

      // pT
      const double pT = 0.0003 * m_Bz.value() * R_mm; // GeV

      // perigee-like point (closest to origin)
      size_t iPmin = 0; double r2Pmin = std::numeric_limits<double>::infinity();
      for (size_t i=0;i<P.size();++i){ const double r2=P[i].Perp2(); if (r2<r2Pmin){r2Pmin=r2; iPmin=i;} }
      const TVector3 Pmin = P[iPmin];

      // tangent at Pmin
      TVector3 rvec(Pmin.X()-cir.C.X(), Pmin.Y()-cir.C.Y(), 0.0);
      if (rvec.Perp2() == 0) rvec = TVector3(1,0,0);
      const TVector3 rhat = rvec.Unit();
      TVector3 that(-rhat.Y(), rhat.X(), 0.0);
      that = that.Unit();

      // tanLambda via z(phi) about center (optional)
      double tanL = 0.0;
      if (m_doTanL.value() && R_mm > 1e-6) {
        std::vector<double> phiC(P.size());
        for (size_t j=0;j<P.size();++j) phiC[j] = std::atan2(P[j].Y()-cir.C.Y(), P[j].X()-cir.C.X());
        for (size_t j=1;j<P.size();++j) phiC[j] = unwrap_to_ref(phiC[j], phiC[j-1]);

        double S1=0, Sph=0, Sz=0, Sphp=0, Sphz=0;
        for (size_t j=0;j<P.size();++j) {
          const double ph = phiC[j];
          const double z  = P[j].Z();
          S1+=1; Sph+=ph; Sz+=z; Sphp+=ph*ph; Sphz+=ph*z;
        }
        const double det = S1*Sphp - Sph*Sph;
        if (std::fabs(det) > 1e-12) {
          const double b = (S1*Sphz - Sph*Sz)/det; // dz/dphi
          tanL = b / R_mm;
        }
      }

      // Create output edm4hep track
      auto trk = outTracks.create();
      trk.setType(cand.getType()); // preserve GGTF label by default

      // Attach derived fit hits to this track (self-contained hit relations)
      for (const auto& v : P) {
        auto oh = outFitHits.create();
        oh.setPosition({float(v.X()), float(v.Y()), float(v.Z())});
        oh.setCovMatrix({
          m_hitVarXY.value(), 0.f, 0.f,
          m_hitVarXY.value(), 0.f,
          m_hitVarZ.value()
        });
        trk.addToTrackerHits(oh);
      }

      // Fill AtIP state (omega=q/pT, time=pT)
      addAtIPState(trk, Pmin, that, pT, tanL, qSign);

      // Diagnostics
      if (m_printDiag.value()) {
        const bool doPrint = (m_diagEvery.value() <= 1) ? true : ((trkCount % m_diagEvery.value()) == 0);
        if (doPrint) {
          const double sag_signed = signed_dist_to_chord_xy(A, B, C);
          const double sag = std::fabs(sag_signed);
          info()
            << "[TPFit] label=" << cand.getType()
            << "  Nwire=" << wireIdx.size()
            << "  dPhi=" << dPhi
            << "  minChord=" << minChord << "mm"
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

    return std::make_tuple(std::move(outTracks), std::move(outFitHits));
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }
};

DECLARE_COMPONENT(ThreePointFitterFromGGTFTracks)
