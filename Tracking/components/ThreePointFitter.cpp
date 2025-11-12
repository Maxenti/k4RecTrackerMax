// ThreePointFitter.cpp
// Ultra-minimal, trigger-style 3-point fitter for GGTF 3D hits.
// - One track per label/type group
// - Pick 3 points: inner (min R), middle (median R), outer (max R)
// - Parabola in local XY (s: along A→C; u: ⟂) and z line fit
// - Exports an EDM4hep Track with one TrackState (AtIP)
// - Pure-geometry (no Kalman). Material effects knob is informational only.

#include <vector>
#include <unordered_map>
#include <algorithm>
#include <cmath>
#include <limits>
#include <string>
#include <type_traits>  // <-- added for void_t/true_type/false_type

#include "Gaudi/Algorithm.h"
#include "Gaudi/Property.h"
#include "GaudiKernel/ISvcLocator.h"

#include "k4FWCore/Transformer.h"

#include "edm4hep/TrackerHit3DCollection.h"
#include "edm4hep/TrackCollection.h"
#include "edm4hep/TrackState.h"

#include "TVector3.h"
#include "TGeoManager.h"

namespace {

// trait helpers to read label from EDM4hep variations
template <typename, typename = void> struct has_getQuality : std::false_type {};
template <typename T> struct has_getQuality<T, std::void_t<decltype(std::declval<T>().getQuality())>> : std::true_type {};
template <typename, typename = void> struct has_getType    : std::false_type {};
template <typename T> struct has_getType<T, std::void_t<decltype(std::declval<T>().getType())>>       : std::true_type {};

template <typename HitT>
inline int hitLabel(const HitT& h) {
  if constexpr (has_getQuality<HitT>::value) return int(h.getQuality());
  else if constexpr (has_getType<HitT>::value) return int(h.getType());
  else return 0;
}

struct Group { std::vector<size_t> idx; };

// Accept both float and double EDM4hep vectors (different EDM4hep versions)
inline TVector3 toV3(const edm4hep::Vector3f& p, double scale) {
  return TVector3(scale*p.x, scale*p.y, scale*p.z);
}
inline TVector3 toV3(const edm4hep::Vector3d& p, double scale) {
  return TVector3(scale*p.x, scale*p.y, scale*p.z);
}

// solve 2x2: [a b; c d] [x;y] = [e;f]
inline bool solve2x2(double a,double b,double c,double d,double e,double f,double& x,double& y){
  const double det = a*d - b*c;
  if (std::abs(det) < 1e-12) return false;
  x = ( e*d - b*f)/det;
  y = (-e*c + a*f)/det;
  return true;
}

// fill TrackState (approximate perigee from position+direction)
inline void fillTrackState(edm4hep::MutableTrack& trk,
                           const TVector3& pos_mm,    // mm
                           const TVector3& dir_xy,    // XY direction (not necessarily unit)
                           double omega_1_per_mm,
                           double tanL)
{
  using TP = edm4hep::TrackParams;
  TVector3 txy = dir_xy;
  if (txy.Perp2() < 1e-24) txy = TVector3(1,0,0);
  const double norm = std::sqrt(txy.X()*txy.X() + txy.Y()*txy.Y());
  const double tx = txy.X()/norm, ty = txy.Y()/norm;

  const double phi = std::atan2(ty, tx);

  const double x = pos_mm.X(), y = pos_mm.Y(), z = pos_mm.Z();
  const double d0 = -( x*std::sin(phi) - y*std::cos(phi) );
  const double z0 =   z - ( x*std::cos(phi) + y*std::sin(phi) ) * tanL;

  edm4hep::TrackState ts;
  ts.location = edm4hep::TrackState::AtIP;
  ts.referencePoint = {0.f,0.f,0.f};
  ts.phi = float(phi);
  ts.omega = float(omega_1_per_mm);
  ts.tanLambda = float(tanL);
  ts.D0 = float(d0);
  ts.Z0 = float(z0);

  // loose diagonal covariances
  ts.setCovMatrix(1.0f,   TP::d0,        TP::d0);
  ts.setCovMatrix(1e-3f,  TP::phi,       TP::phi);
  ts.setCovMatrix(1e-8f,  TP::omega,     TP::omega);
  ts.setCovMatrix(1.0f,   TP::z0,        TP::z0);
  ts.setCovMatrix(1e-2f,  TP::tanLambda, TP::tanLambda);

  trk.addToTrackStates(ts);
}

} // namespace

struct ThreePointFitter final
 : k4FWCore::Transformer<edm4hep::TrackCollection (const edm4hep::TrackerHit3DCollection&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  ThreePointFitter(const std::string& name, ISvcLocator* svcLoc)
  : Transformer(name, svcLoc,
      std::tuple<KeyValues>{ KeyValues{"inputHits",  std::vector<std::string>{"GGTF_3DHits"}} },
      std::tuple<KeyValues>{ KeyValues{"outputTracks", std::vector<std::string>{"ThreePointTracks"}} }) {}

  // Knobs (no declareProperty calls; only Gaudi::Property)
  Gaudi::Property<double> m_posScale {this, "PositionUnitScale", 0.1, "Multiply EDM positions (0.1: mm->cm)."};
  Gaudi::Property<int>    m_pdg      {this, "PDG", 13,           "PDG hypothesis (charge sign)."};
  Gaudi::Property<double> m_Bz       {this, "Bz",  2.0,          "Magnetic field Bz [T] (sign convention only)."};
  Gaudi::Property<bool>   m_useMat   {this, "UseMaterialEffects", true,
                                      "Informational: checks TGeo presence for consistency with other fitters."};

  StatusCode initialize() override {
    info() << "ThreePointFitter init | posScale=" << m_posScale.value()
           << " | PDG=" << m_pdg.value()
           << " | Bz=" << m_Bz.value()
           << " | UseMaterialEffects=" << (m_useMat.value() ? "true":"false")
           << endmsg;

    if (m_useMat.value()) {
      if (!gGeoManager) {
        warning() << "UseMaterialEffects=True but gGeoManager is null — continuing (no MS/dE/dx applied in this fitter)." << endmsg;
      } else {
        info() << "TGeo detected (UseMaterialEffects=True). Note: ThreePointFitter is geometric-only; no MS/dE/dx used." << endmsg;
      }
    }
    return StatusCode::SUCCESS;
  }

  edm4hep::TrackCollection operator()(const edm4hep::TrackerHit3DCollection& hits) const override {
    edm4hep::TrackCollection out;
    if (hits.empty()) return out;

    // 1) group by label (quality/type)
    std::unordered_map<int, Group> groups;
    groups.reserve(hits.size()/8 + 1);
    for (size_t i=0;i<hits.size();++i) {
      groups[ hitLabel(hits[i]) ].idx.push_back(i);
    }

    // 2) per group, build one track from 3 points (inner/middle/outer)
    for (auto& kv : groups) {
      const auto& idx = kv.second.idx;
      if (idx.size() < 3) continue;

      struct Item{ size_t i; double R2; };
      std::vector<Item> order; order.reserve(idx.size());
      for (auto i : idx) {
        const auto p = hits[i].getPosition();
        const double x = p.x, y = p.y;
        order.push_back({i, x*x + y*y});
      }
      std::sort(order.begin(), order.end(), [](const Item& a, const Item& b){ return a.R2 < b.R2; });

      const size_t iA = order.front().i;
      const size_t iC = order.back().i;
      const size_t iB = order[ order.size()/2 ].i;

      const auto pA = toV3(hits[iA].getPosition(), m_posScale.value()); // internal cm
      const auto pB = toV3(hits[iB].getPosition(), m_posScale.value());
      const auto pC = toV3(hits[iC].getPosition(), m_posScale.value());

      // 2D frame in XY: e_s along chord A->C, e_u perpendicular in XY
      TVector3 AC = pC - pA;
      TVector3 e_s(AC.X(), AC.Y(), 0.0);    // XY projection
      if (e_s.Mag2() < 1e-12) e_s = TVector3(1,0,0);
      e_s = e_s.Unit();
      TVector3 zhat(0,0,1);
      TVector3 e_u = zhat.Cross(e_s);       // in XY, perpendicular
      e_u = TVector3(e_u.X(), e_u.Y(), 0.0).Unit();

      auto projXY = [](const TVector3& v){ return TVector3(v.X(), v.Y(), 0.0); };
      const TVector3 rA = projXY(pA), rB = projXY(pB), rC = projXY(pC);

      // set s=0 at projection of B on the chord line, u towards e_u
      const TVector3 rAtoB = rB - rA;
      const double sB_on_line = rAtoB.X()*e_s.X() + rAtoB.Y()*e_s.Y();
      const TVector3 r0 = rA + sB_on_line*e_s;     // (s,u) origin
      auto su = [&](const TVector3& r)->std::pair<double,double>{
        TVector3 d = r - r0;
        double s = d.X()*e_s.X() + d.Y()*e_s.Y();
        double u = d.X()*e_u.X() + d.Y()*e_u.Y();
        return {s,u};
      };
      const auto [sA,uA] = su(rA);
      const auto [sB,uB] = su(rB);
      const auto [sC,uC] = su(rC);

      // Fit u(s) = α s^2 + β s + γ; since sB≈0 => γ = uB.
      double alpha=0, beta=0;
      {
        const double rhsA = uA - uB;
        const double rhsC = uC - uB;
        if (!solve2x2(sA*sA, sA, sC*sC, sC, rhsA, rhsC, alpha, beta)) {
          alpha = 0.0; beta = 0.0;
        }
      }

      // tangent in XY at s=0 is: e_s + β e_u  (not normalized)
      TVector3 tXY = e_s + beta*e_u;

      // curvature at s=0: κ = 2α / (1+β^2)^(3/2)   [1/cm]
      const double denom = std::pow(1.0 + beta*beta, 1.5);
      const double kappa_cm = (denom > 0.0) ? (2.0*alpha / denom) : 0.0;

      // sign convention: area orientation (A,B,C) and Bz sign
      const double orient = ( (rC - rA).X()*(rB - rA).Y() - (rC - rA).Y()*(rB - rA).X() );
      const int signGeom = (orient >= 0 ? +1 : -1);
      const int absPDG = std::abs(m_pdg.value());
      const int qSign = (m_pdg.value() > 0 ? ((absPDG==11||absPDG==13||absPDG==15)? -1:+1)
                                           : ((absPDG==11||absPDG==13||absPDG==15)? +1:-1));
      const int bzSign = (m_Bz.value() >= 0 ? +1 : -1);
      const double omega_1_per_mm = 0.1 * kappa_cm * double(signGeom * qSign * bzSign); // cm^-1 -> mm^-1

      // z(s): simple line using A and C
      double slope_z = 0.0;
      {
        const double sAC = sC - sA;
        if (std::abs(sAC) > 1e-9) slope_z = (pC.Z() - pA.Z()) / sAC; // unitless
      }
      // tanLambda ~ (dz/ds)/|dXY/ds| ; |dXY/ds| = |e_s + β e_u| = sqrt(1+β^2)
      const double tanL = slope_z / std::sqrt(1.0 + beta*beta);

      // perigee approximation at middle point (convert back to mm)
      const TVector3 rB_cm = r0 + uB*e_u;       // middle in XY (cm)
      const TVector3 pos_mid_mm( 10.0*rB_cm.X(), 10.0*rB_cm.Y(), 10.0*pB.Z() );
      const TVector3 dir_xy_mm(tXY.X(), tXY.Y(), 0.0);

      // export
      auto trk = out.create();
      trk.setType(m_pdg.value());
      try { trk.setChi2(0.0f); trk.setNdf(2); } catch (...) {}

      for (auto i : idx) trk.addToTrackerHits( hits[i] );
      fillTrackState(trk, pos_mid_mm, dir_xy_mm, omega_1_per_mm, tanL);
    }

    return out;
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }
};

DECLARE_COMPONENT(ThreePointFitter)
