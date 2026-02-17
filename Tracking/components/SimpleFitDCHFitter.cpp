/*
DOC:
Title: SimpleFitFromGGTFTracks (Ultra-light DCH helix fitter from GGTF tracks)
Summary:
  Gaudi/k4FWCore MultiTransformer that takes clustered DCH-centric GGTF track candidates
  (extension::TrackCollection) plus the persisted GGTF wire-hit collection
  (extension::SenseWireHitCollection), builds simple 3D “fit points” from the wire hits,
  performs a lightweight circle+helix-style fit (circle in XY + linear z(phi)),
  and outputs an edm4hep::TrackCollection with TrackState(AtIP).
  It ALSO writes an edm4hep::TrackerHit3DCollection containing the derived fit points,
  and attaches these hits to each output track via the edm4hep Track.trackerHits relation.

Primary Use Cases:
  - Fast, dependency-minimal “sanity fit” downstream of GGTF_tracking without GenFit2/ACTS.
  - Quick regression checks on GGTF clustering / hit ordering / coordinate conventions.
  - Producing self-contained edm4hep tracks that carry their own attached 3D hit points
    (SimpleFitHits) for ROOT/PODIO-level diagnostics and plotting.
  - Debugging gross issues (sign conventions, B-field mismatch, pathological clustering)
    via simple fitted pT/helix parameter distributions.

Not Intended For:
  - Precision drift-chamber fitting (no left/right ambiguity resolution, no DAF/Kalman).
  - Using true drift-time residuals or DOCA likelihoods (fit points are geometric proxies).
  - Providing unbiased physics performance metrics comparable to full GenFit2/ACTS fits.

Algorithm Behavior:
  For each candidate in inputGGTFTracks:
    1) Identify which trackerHits relations belong to the persisted GGTF wire-hit collection
       by comparing ObjectID.collectionID to the wire-hits collection ID.
    2) For each referenced SenseWireHit:
         - Build a wire direction from (wireAzimuthalAngle, wireStereoAngle).
         - Construct a local xprime basis and compute a 3D point:
             * If UseMmidPoint=true (default): Mmid = 0.5*(wpos - d*xprime + wpos + d*xprime)
               where d = distanceToWire (same “Mmid” concept used by GGTF flattening).
             * Else: use the wire hit position directly.
    3) Optional deduplication: drops consecutive near-identical points within DedupTolMM.
    4) Fit circle in XY using an algebraic Kåsa method -> radius R_mm and center (cx,cy).
    5) Compute phi around circle center for all points, unwrap, sort by phi.
       Fit z(phi) = a + b*phi -> tanLambda ≈ (b / R_mm).
    6) Build an approximate tangent direction at a “perigee-like” point (smallest rT).
    7) Create an edm4hep Track:
         - Copy Track.type from the GGTF candidate (preserves label if desired).
         - Add TrackState at IP (AtIP) with parameters (phi, D0, Z0, omega, tanLambda),
           with omega stored as q/pT [GeV^-1] using pT = 0.0003 * Bz[T] * R[mm].
         - Store pT [GeV] in TrackState.time for convenience.
    8) Create one edm4hep::TrackerHit3D per fitted point and attach them to the output track.

Inputs:
  - inputGGTFTracks (extension::TrackCollection)
      Default: "CDCHTracks"
      Description: GGTF track candidates produced by GGTF_tracking. Each candidate’s
      trackerHits relation may include:
        * Persisted wire hits from OutputWireHitsGGTF (extension::SenseWireHitCollection)
        * Optional planar hits (ignored by this fitter; only wire hits are used here)
  - inputWireHits (extension::SenseWireHitCollection)
      Default: "GGTF_SenseWireHits"
      Description: Persisted copy of the exact SenseWireHits used by GGTF_tracking.
      This fitter matches candidate relations back to this collection by ObjectID.

Outputs:
  - outputTracks (edm4hep::TrackCollection)
      Default: "SimpleTracks"
      Contents:
        * One edm4hep track per successfully-fitted GGTF candidate
        * TrackState(AtIP) filled with:
            - phi, D0, Z0, omega=q/pT [GeV^-1], tanLambda
            - TrackState.time stores pT [GeV] (convenience)
        * Track.trackerHits relation points to hits in outputFitHits (below)
  - outputFitHits (edm4hep::TrackerHit3DCollection)
      Default: "SimpleFitHits"
      Contents:
        * 3D proxy points derived from wire hits (Mmid or wire position)
        * Covariance set as diagonal packed symmetric:
            (xx, xy, xz, yy, yz, zz) with (HitVarXY, 0, 0, HitVarXY, 0, HitVarZ)
      Notes:
        * These hits are “fit points”, not physical drift-time measurements.

Collections:
  - Consumes:
      * extension::TrackCollection ("CDCHTracks" default)
      * extension::SenseWireHitCollection ("GGTF_SenseWireHits" default)
  - Produces:
      * edm4hep::TrackCollection ("SimpleTracks" default)
      * edm4hep::TrackerHit3DCollection ("SimpleFitHits" default)

Connects-To:
  - Upstream:
      * GGTF_tracking (produces clustered extension::TrackCollection and persisted SenseWireHitCollection)
  - Downstream:
      * ROOT/PODIO analysis scripts that expect edm4hep tracks and want attached hit points
      * Lightweight resolution/QA plots (pT, curvature, helix params) without GenFit2/ACTS
      * Optional: further processing stages that consume edm4hep::TrackCollection

Key Properties / Arguments:
  - Bz (double, default=2.0):
      Uniform magnetic field Bz [Tesla] used for pT conversion:
        pT[GeV] = 0.0003 * Bz[T] * R[mm]
  - PDG (int, default=13):
      PDG hypothesis used only to set charge sign q for omega=q/pT.
      (No particle-ID inference is performed.)
  - MinHitsPerTrack (unsigned, default=6):
      Minimum number of wire-derived points required to fit a GGTF candidate.
  - UseMmidPoint (bool, default=true):
      If true, use GGTF-style Mmid points computed from distanceToWire and xprime basis.
      If false, use SenseWireHit position directly.
  - DeduplicateHits (bool, default=true) and DedupTolMM (double, default=0.25):
      Removes consecutive near-duplicate points to stabilize the circle fit.
  - HitVarXY (float, default=1.0) and HitVarZ (float, default=1.0):
      Diagonal variances [mm^2] assigned to output TrackerHit3D covariances.
  - BaseVar_d0, BaseVar_phi, BaseVar_omega, BaseVar_z0, BaseVar_tanLambda:
      Diagonal variances used for the output TrackState covariance matrix.
  - FillSummaryHisto (bool, default=false), HistStream, PtBins, PtMax:
      Optional minimal pT histogram via THistSvc.

Assumptions / Conventions:
  - SenseWireHit fields are in consistent units with mm for position and distanceToWire.
  - wireAzimuthalAngle and wireStereoAngle are in radians.
  - Candidate track relations include ObjectIDs that correctly refer to the persisted
    inputWireHits collection (OutputWireHitsGGTF from GGTF_tracking).
  - The circle+z(phi) model is an approximation; it ignores detailed DCH measurement physics.

Failure Modes / Diagnostics:
  - Skips candidates with < MinHitsPerTrack matching wire hits.
  - Skips candidates where Kåsa circle fit is ill-conditioned (det ~ 0).
  - Pathological distributions (very large R, wild tanLambda) may indicate:
      * broken clustering (mixed tracks), inconsistent coordinates, or incorrect Bz.

Example Usage:
  - Gaudi options snippet (Python):
      from Configurables import GGTF_tracking, SimpleFitFromGGTFTracks, ApplicationMgr
      ggtf = GGTF_tracking("GGTF_tracking",
                           OutputTracksGGTF=["CDCHTracks"],
                           OutputWireHitsGGTF=["GGTF_SenseWireHits"])
      fit  = SimpleFitFromGGTFTracks("SimpleFitFromGGTFTracks",
                                     inputGGTFTracks=["CDCHTracks"],
                                     inputWireHits=["GGTF_SenseWireHits"],
                                     outputTracks=["SimpleTracks"],
                                     outputFitHits=["SimpleFitHits"],
                                     Bz=2.0, PDG=13,
                                     MinHitsPerTrack=6,
                                     UseMmidPoint=True)
      ApplicationMgr(TopAlg=[ggtf, fit], EvtMax=-1)

Tags:
  tracking
  drift-chamber
  DCH
  GGTF
  helix
  circle-fit
  diagnostics
  gaudi
  k4run
  edm4hep
  podio
DOC_END
*/

#include <vector>
#include <cmath>
#include <limits>
#include <algorithm>
#include <numeric>
#include <string>

#include "Gaudi/Property.h"
#include "GaudiKernel/ISvcLocator.h"
#include "GaudiKernel/ITHistSvc.h"
#include "GaudiKernel/ServiceHandle.h"

#include "k4FWCore/Transformer.h"

#include "edm4hep/TrackCollection.h"
#include "edm4hep/TrackState.h"
#include "edm4hep/TrackerHit3DCollection.h"

#include "TVector3.h"
#include "TH1F.h"

#include "podio/ObjectID.h"

// GGTF EDM extensions
#include "extension/TrackCollection.h"
#include "extension/SenseWireHitCollection.h"

namespace {

inline double PI() { return std::acos(-1.0); }

struct CircleXY { double cx{0}, cy{0}, R{1e9}; bool ok{false}; };

// Kåsa algebraic circle fit in XY
static CircleXY kasa_circle_xy(const std::vector<TVector3>& P) {
  const size_t N = P.size();
  if (N < 3) return {};
  double Sx=0, Sy=0, Sxx=0, Syy=0, Sxy=0, Sz=0, Sxz=0, Syz=0;
  for (const auto& v : P) {
    const double x=v.X(), y=v.Y(), z=x*x+y*y;
    Sx+=x; Sy+=y; Sxx+=x*x; Syy+=y*y; Sxy+=x*y; Sz+=z; Sxz+=x*z; Syz+=y*z;
  }
  const double M11=Sxx, M12=Sxy, M13=Sx;
  const double M21=Sxy, M22=Syy, M23=Sy;
  const double M31=Sx,  M32=Sy,  M33=double(N);
  const double B1=Sxz,  B2=Syz,  B3=Sz;

  const double det =
      M11*(M22*M33 - M23*M32)
    - M12*(M21*M33 - M23*M31)
    + M13*(M21*M32 - M22*M31);

  CircleXY res;
  if (std::fabs(det) < 1e-12) return res;

  auto det3=[&](double a11,double a12,double a13,double a21,double a22,double a23,double a31,double a32,double a33){
    return a11*(a22*a33-a23*a32) - a12*(a21*a33-a23*a31) + a13*(a21*a32-a22*a31);
  };
  const double detA = det3(B1,M12,M13,  B2,M22,M23,  B3,M32,M33);
  const double detB = det3(M11,B1,M13,  M21,B2,M23,  M31,B3,M33);
  const double detC = det3(M11,M12,B1,  M21,M22,B2,  M31,M32,B3);

  const double A = detA/det, B = detB/det, C = detC/det;
  const double cx = 0.5*A, cy = 0.5*B;
  const double R2 = C + cx*cx + cy*cy;
  if (!(R2>0 && std::isfinite(R2))) return res;

  res.cx=cx; res.cy=cy; res.R=std::sqrt(R2);
  res.ok = std::isfinite(res.R) && res.R > 1e-6;
  return res;
}

static double unwrap(double a, double ref) {
  double d = a - ref;
  while (d >  PI()) d -= 2*PI();
  while (d < -PI()) d += 2*PI();
  return ref + d;
}

static TVector3 safe_unit(const TVector3& v, const TVector3& fallback) {
  const double m2 = v.Mag2();
  if (!(m2 > 0.0) || !std::isfinite(m2)) return fallback;
  return (1.0 / std::sqrt(m2)) * v;
}

static int chargeFromPDG(int pdg) {
  const int a=std::abs(pdg);
  if (a==11||a==13||a==15) return (pdg>0?-1:+1);
  if (a==211||a==321||a==2212) return (pdg>0?+1:-1);
  return (pdg>=0?+1:-1);
}

static void addAtIPStateWithCov(edm4hep::MutableTrack& trk,
                                const TVector3& Pmin, const TVector3& tangentUnit,
                                double R_mm, double tanL, int qSign,
                                double Bz_T,
                                float cov_d0, float cov_phi, float cov_omega, float cov_z0, float cov_tanL)
{
  using TP = edm4hep::TrackParams;

  const double phi   = std::atan2(tangentUnit.Y(), tangentUnit.X());
  const double ptGeV = 0.0003 * Bz_T * R_mm;               // GeV  (R in mm)
  const double d0    = -( Pmin.X()*std::sin(phi) - Pmin.Y()*std::cos(phi) );
  const double z0    =   Pmin.Z() - ( Pmin.X()*std::cos(phi) + Pmin.Y()*std::sin(phi) ) * tanL;

  edm4hep::TrackState ts;
  ts.location        = edm4hep::TrackState::AtIP;
  ts.referencePoint  = {0.f,0.f,0.f};
  ts.phi             = float(phi);
  ts.tanLambda       = float(tanL);
  ts.D0              = float(d0);
  ts.Z0              = float(z0);

  const double omega_qOverPt = (ptGeV > 1e-12) ? (qSign / ptGeV) : 0.0; // GeV^-1
  ts.omega = float(omega_qOverPt);
  ts.time  = float(ptGeV); // convenience pT [GeV]

  ts.setCovMatrix(std::max(1e-12f, cov_d0),    TP::d0,        TP::d0);
  ts.setCovMatrix(std::max(1e-12f, cov_phi),   TP::phi,       TP::phi);
  ts.setCovMatrix(std::max(1e-12f, cov_omega), TP::omega,     TP::omega);
  ts.setCovMatrix(std::max(1e-12f, cov_z0),    TP::z0,        TP::z0);
  ts.setCovMatrix(std::max(1e-12f, cov_tanL),  TP::tanLambda, TP::tanLambda);

  trk.addToTrackStates(ts);
}

} // namespace

// ----------------- Algorithm -----------------
struct SimpleFitFromGGTFTracks final
  : k4FWCore::MultiTransformer<std::tuple<edm4hep::TrackCollection, edm4hep::TrackerHit3DCollection>(
        const extension::TrackCollection&,
        const extension::SenseWireHitCollection&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  SimpleFitFromGGTFTracks(const std::string& name, ISvcLocator* svcLoc)
  : MultiTransformer(name, svcLoc,
      { KeyValues{"inputGGTFTracks", std::vector<std::string>{"CDCHTracks"}},
        KeyValues{"inputWireHits",   std::vector<std::string>{"GGTF_SenseWireHits"}} },
      { KeyValues{"outputTracks",    std::vector<std::string>{"SimpleTracks"}},
        KeyValues{"outputFitHits",   std::vector<std::string>{"SimpleFitHits"}} })
  {}

  // -------- knobs --------
  Gaudi::Property<double>   m_Bz       {this, "Bz", 2.0,  "Uniform Bz [T] (for pT conversion)"};
  Gaudi::Property<int>      m_pdg      {this, "PDG", 13,  "PDG hypothesis (sets charge sign)"};
  Gaudi::Property<unsigned> m_minHits  {this, "MinHitsPerTrack", 6u, "Min wire hits to fit a GGTF track"};

  // When converting SenseWireHit -> 3D point:
  Gaudi::Property<bool>     m_useMmid  {this, "UseMmidPoint", true, "Use GGTF Mmid point (recommended)"};

  // Dedup consecutive near-duplicates
  Gaudi::Property<bool>     m_dedup     {this, "DeduplicateHits", true, "Drop consecutive near-duplicates"};
  Gaudi::Property<double>   m_dedupTolMM{this, "DedupTolMM", 0.25, "Dedup tolerance [mm]"};

  // Output hit covariance (diagonal) for TrackerHit3D (mm^2)
  Gaudi::Property<float>    m_hitVarXY {this, "HitVarXY",  1.0f, "var(x)=var(y) for output fit hits [mm^2]"};
  Gaudi::Property<float>    m_hitVarZ  {this, "HitVarZ",   1.0f, "var(z) for output fit hits [mm^2]"};

  // base diagonal covariances for exported TrackState
  Gaudi::Property<float>  m_cov_d0     {this, "BaseVar_d0",        1.0f,   "base var(d0) [mm^2]"};
  Gaudi::Property<float>  m_cov_phi    {this, "BaseVar_phi",       1e-3f,  "base var(phi) [rad^2]"};
  Gaudi::Property<float>  m_cov_omega  {this, "BaseVar_omega",     1e-8f,  "base var(omega) [(GeV^-1)^2]"};
  Gaudi::Property<float>  m_cov_z0     {this, "BaseVar_z0",        1.0f,   "base var(z0) [mm^2]"};
  Gaudi::Property<float>  m_cov_tanL   {this, "BaseVar_tanLambda", 1e-2f,  "base var(tanLambda) [1]"};

  // quick sanity hist (optional; harmless if THistSvc absent in job)
  Gaudi::Property<bool> m_fillSummaryHisto {this, "FillSummaryHisto", false, "Fill minimal pT histo via THistSvc"};
  Gaudi::Property<std::string> m_histStream {this, "HistStream", "simple", "THistSvc stream (file logical name)"};
  Gaudi::Property<unsigned>    m_ptBins     {this, "PtBins", 100u, "pT bins"};
  Gaudi::Property<double>      m_ptMax      {this, "PtMax", 100.0, "pT max [GeV]"};

  ServiceHandle<ITHistSvc> m_histSvc{"THistSvc", this->name()};
  mutable TH1F* h_pt{nullptr};

  StatusCode initialize() override {
    if (!m_fillSummaryHisto.value()) return StatusCode::SUCCESS;
    if (!m_histSvc.retrieve().isSuccess()) {
      warning() << "THistSvc NOT available; summary histo disabled." << endmsg;
      return StatusCode::SUCCESS;
    }
    const std::string base = "/" + m_histStream.value() + "/";
    h_pt = new TH1F("pt", "p_{T} [GeV]", m_ptBins.value(), 0.0, m_ptMax.value());
    h_pt->Sumw2();
    m_histSvc->regHist(base + "pt", h_pt).ignore();
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

    // collectionID for the persisted wire hits (all entries share it)
    const auto wireCollID = wireHits[0].getObjectID().collectionID;

    const int qSign = chargeFromPDG(m_pdg.value());

    for (const auto& cand : ggtfTracks) {

      // Gather the indices of wire hits referenced by this GGTF track
      std::vector<int> wireIdx;
      wireIdx.reserve(64);

      for (const auto& rel : cand.getTrackerHits()) {
        const auto oid = rel.getObjectID();
        if (oid.collectionID != wireCollID) continue;
        if (oid.index < 0 || oid.index >= (int)wireHits.size()) continue;
        wireIdx.push_back(oid.index);
      }

      if (wireIdx.size() < std::max<unsigned>(m_minHits.value(), 3u)) continue;

      // Convert each SenseWireHit -> a 3D point (and keep the points for fitting)
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

      // optional dedup
      if (m_dedup.value() && P.size() >= 2) {
        std::vector<TVector3> P2; P2.reserve(P.size());
        const double tol2 = m_dedupTolMM.value() * m_dedupTolMM.value();
        TVector3 prev(1e99,1e99,1e99);
        for (const auto& v : P) {
          if ((v - prev).Mag2() >= tol2) { P2.push_back(v); prev = v; }
        }
        if (P2.size() >= 3) P.swap(P2);
      }
      if (P.size() < 3) continue;

      // circle fit
      CircleXY cir = kasa_circle_xy(P);
      if (!cir.ok) continue;
      const double R_mm = cir.R;

      // pick perigee-like point (smallest transverse radius)
      size_t imin=0; double r2min=std::numeric_limits<double>::infinity();
      for (size_t j=0;j<P.size();++j){ const double r2=P[j].Perp2(); if (r2<r2min){r2min=r2; imin=j;} }
      const TVector3 Pmin = P[imin];

      // unwrap phi around center; fit z(phi)
      std::vector<double> ph(P.size());
      for (size_t j=0;j<P.size();++j) ph[j] = std::atan2(P[j].Y()-cir.cy, P[j].X()-cir.cx);
      for (size_t j=1;j<P.size();++j) ph[j] = unwrap(ph[j], ph[j-1]);

      std::vector<size_t> ord(P.size()); std::iota(ord.begin(), ord.end(), 0);
      std::sort(ord.begin(), ord.end(), [&](size_t a,size_t b){ return ph[a] < ph[b]; });

      double S1=0, Sph=0, Sz=0, Sphp=0, Sphz=0;
      for (auto j : ord) {
        const double pphi = ph[j];
        const double z    = P[j].Z();
        S1 += 1; Sph += pphi; Sz += z; Sphp += pphi*pphi; Sphz += pphi*z;
      }
      const double det = S1*Sphp - Sph*Sph;
      double b = 0.0;
      if (std::fabs(det) > 1e-12) b = (S1*Sphz - Sph*Sz) / det;

      const double tanL = (R_mm > 1e-9) ? (b / R_mm) : 0.0;

      // tangent at Pmin
      TVector3 rvec(Pmin.X()-cir.cx, Pmin.Y()-cir.cy, 0.0);
      if (rvec.Perp2()==0) rvec = TVector3(1,0,0);
      const TVector3 rhat = rvec.Unit();
      TVector3 that(-rhat.Y(), rhat.X(), 0.0);
      TVector3 tangent = TVector3(that.X(), that.Y(), tanL).Unit();

      // ---- create output track ----
      auto trk = outTracks.create();
      trk.setType(cand.getType()); // preserve GGTF label if desired

      addAtIPStateWithCov(trk, Pmin, tangent, R_mm, tanL, qSign, m_Bz.value(),
                          m_cov_d0.value(), m_cov_phi.value(), m_cov_omega.value(),
                          m_cov_z0.value(), m_cov_tanL.value());

      // ---- create output fit hits and attach them to the edm4hep track ----
      // One output hit per point used in fit (in the same order as P)
      for (const auto& v : P) {
        auto oh = outFitHits.create();
        oh.setPosition({float(v.X()), float(v.Y()), float(v.Z())});

        // Minimal diagonal covariance; edm4hep TrackerHit3D stores a 6-element packed symmetric cov
        // ordering: (xx, xy, xz, yy, yz, zz)
        oh.setCovMatrix({
          m_hitVarXY.value(), 0.f, 0.f,
          m_hitVarXY.value(), 0.f,
          m_hitVarZ.value()
        });

        // Optional: store a “time” — leave at 0 unless you want something meaningful
        // oh.setTime(0.f);

        trk.addToTrackerHits(oh);
      }

      // summary histo
      if (h_pt) {
        const double pt = 0.0003 * m_Bz.value() * R_mm;
        h_pt->Fill(pt);
      }
    }

    return std::make_tuple(std::move(outTracks), std::move(outFitHits));
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }
};

DECLARE_COMPONENT(SimpleFitFromGGTFTracks)
