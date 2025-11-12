// ======================================================================
// SimpleFitDCHFitter.cpp  -- ultra-light DCH track fitter + ROOT histos
//   * Input: GGTF_3DHits (edm4hep::TrackerHit3DCollection)
//   * Cluster (tiny DBSCAN in mm)  -> circle in XY (Kåsa) -> z(phi) slope
//   * Export one EDM4hep Track/cluster with TrackState(AtIP) (omega set)
//   * Book/fill ROOT histograms via THistSvc (1D + 2D vs event index)
//   * OPTIONAL: lightweight "material effects" covariance inflation
//     - Estimate X/X0 per cluster (TGeo midpoint sampling or fallback)
//     - Inflate phi/d0/z0 variances using Highland formula
// ======================================================================

#include <vector>
#include <cmath>
#include <limits>
#include <queue>
#include <algorithm>
#include <unordered_map>
#include <numeric>
#include <string>

#include "Gaudi/Algorithm.h"
#include "Gaudi/Property.h"
#include "GaudiKernel/ISvcLocator.h"
#include "GaudiKernel/ITHistSvc.h"
#include "GaudiKernel/ServiceHandle.h"

#include "k4FWCore/Transformer.h"

#include "edm4hep/TrackerHit3DCollection.h"
#include "edm4hep/TrackCollection.h"
#include "edm4hep/TrackState.h"

#include "TVector3.h"
#include "TH1F.h"
#include "TH2F.h"

// TGeo (optional; for material estimate)
#include "TGeoManager.h"

namespace {

struct CircleXY { double cx{0}, cy{0}, R{1e9}; bool ok{false}; };

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
  res.cx=cx; res.cy=cy; res.R=std::sqrt(R2); res.ok=std::isfinite(res.R) && res.R>1e-6;
  return res;
}

static double unwrap(double a, double ref) {
  double d = a - ref;
  while (d >  M_PI) d -= 2*M_PI;
  while (d < -M_PI) d += 2*M_PI;
  return ref + d;
}

static std::vector<int> dbscan_mm(const std::vector<TVector3>& P, double eps_mm, unsigned minPts) {
  const int N = (int)P.size(); const double e2 = eps_mm*eps_mm;
  std::vector<int> label(N, -99); int cid=0;
  auto region = [&](int i, std::vector<int>& out){ out.clear(); for (int j=0;j<N;++j) if ((P[j]-P[i]).Mag2()<=e2) out.push_back(j); };
  for (int i=0;i<N;++i) {
    if (label[i]!=-99) continue;
    std::vector<int> neigh; region(i, neigh);
    if (neigh.size()<minPts){ label[i]=-1; continue; }
    label[i]=cid; std::queue<int> q;
    for (int n:neigh) if (label[n]==-99 || label[n]==-1){ label[n]=cid; q.push(n); }
    while(!q.empty()){
      int k=q.front(); q.pop();
      std::vector<int> n2; region(k,n2);
      if (n2.size()>=minPts){
        for (int n:n2) if (label[n]==-99 || label[n]==-1){ label[n]=cid; q.push(n); }
      }
    }
    ++cid;
  }
  return label;
}

static int chargeFromPDG(int pdg) {
  const int a=std::abs(pdg);
  if (a==11||a==13||a==15) return (pdg>0?-1:+1);
  if (a==211||a==321||a==2212) return (pdg>0?+1:-1);
  return (pdg>=0?+1:-1);
}

// --- tiny helper to estimate X/X0 along a polyline of points in mm ---
// Strategy: for each consecutive pair, sample the material at the midpoint
// (in TGeo coordinates, i.e. cm), get X0, and add |dl|/X0. If TGeo missing,
// or X0 invalid, fall back to provided constant.
static double estimate_x_over_x0_midpoint(const std::vector<TVector3>& P_mm, double fallbackXOverX0) {
  if (!gGeoManager || P_mm.size() < 2) return fallbackXOverX0;
  double x_over_x0 = 0.0;
  for (size_t i=1; i<P_mm.size(); ++i) {
    const TVector3& a = P_mm[i-1];
    const TVector3& b = P_mm[i];
    const TVector3  mid = 0.5*(a+b);
    const double    dl_mm = (b-a).Mag();
    if (dl_mm <= 0) continue;

    const double x_cm = mid.X() * 0.1;
    const double y_cm = mid.Y() * 0.1;
    const double z_cm = mid.Z() * 0.1;

    TGeoNode* node = gGeoManager->FindNode(x_cm, y_cm, z_cm);
    if (!node) { x_over_x0 += dl_mm / (100.0 * 1000.0); continue; } // wildly small X0 → almost zero add
    const TGeoMaterial* mat = node->GetMedium() ? node->GetMedium()->GetMaterial() : nullptr;
    const double X0_cm = (mat ? mat->GetRadLen() : 0.0);
    if (X0_cm <= 0 || !std::isfinite(X0_cm)) {
      // fall back contribution for this segment only
      x_over_x0 += (dl_mm * fallbackXOverX0) / std::max(1.0, (double)P_mm.size());
    } else {
      const double X0_mm = 10.0 * X0_cm;
      x_over_x0 += dl_mm / X0_mm;
    }
  }
  // If TGeo sampling found nothing meaningful, use global fallback
  if (!(x_over_x0 > 0.0)) x_over_x0 = fallbackXOverX0;
  return x_over_x0;
}

static void addAtIPStateWithCov(edm4hep::MutableTrack& trk,
                                const TVector3& Pmin, const TVector3& tangentUnit,
                                double R_mm, double tanL, int qSign,
                                // base cov (diagonal) and optional smearing additions
                                float cov_d0, float cov_phi, float cov_omega, float cov_z0, float cov_tanL,
                                float add_var_phi = 0.f, float add_var_d0 = 0.f, float add_var_z0 = 0.f)
{
  using TP = edm4hep::TrackParams;
  const double phi   = std::atan2(tangentUnit.Y(), tangentUnit.X());
  const double omega = (R_mm>1e-6 ? (qSign / R_mm) : 0.0); // 1/mm
  const double d0    = -( Pmin.X()*std::sin(phi) - Pmin.Y()*std::cos(phi) );
  const double z0    =   Pmin.Z() - ( Pmin.X()*std::cos(phi) + Pmin.Y()*std::sin(phi) ) * tanL;

  edm4hep::TrackState ts;
  ts.location        = edm4hep::TrackState::AtIP;
  ts.referencePoint  = {0.f,0.f,0.f};
  ts.phi             = float(phi);
  ts.omega           = float(omega);
  ts.tanLambda       = float(tanL);
  ts.D0              = float(d0);
  ts.Z0              = float(z0);
  ts.time            = 0.f;

  // base diagonal covariances
  float v_phi = cov_phi + add_var_phi;
  float v_d0  = cov_d0  + add_var_d0;
  float v_z0  = cov_z0  + add_var_z0;

  ts.setCovMatrix(std::max(1e-12f, v_d0),   TP::d0,        TP::d0);
  ts.setCovMatrix(std::max(1e-12f, v_phi),  TP::phi,       TP::phi);
  ts.setCovMatrix(std::max(1e-12f, cov_omega), TP::omega,  TP::omega);
  ts.setCovMatrix(std::max(1e-12f, v_z0),   TP::z0,        TP::z0);
  ts.setCovMatrix(std::max(1e-12f, cov_tanL), TP::tanLambda, TP::tanLambda);

  trk.addToTrackStates(ts);
}

} // namespace

// ----------------- Algorithm -----------------
struct SimpleFitDCHFitter final
  : k4FWCore::Transformer<edm4hep::TrackCollection (const edm4hep::TrackerHit3DCollection&)> {

  using Traits    = Gaudi::Functional::Traits::use_<>;
  using KeyValues = Gaudi::Functional::details::DataHandleMixin<
                      std::tuple<>, std::tuple<>, Traits>::KeyValues;

  SimpleFitDCHFitter(const std::string& name, ISvcLocator* svcLoc)
  : Transformer(name, svcLoc,
      std::tuple<KeyValues>{ KeyValues{"inputHits",  std::vector<std::string>{"GGTF_3DHits"}} },
      std::tuple<KeyValues>{ KeyValues{"outputTracks", std::vector<std::string>{"SimpleTracks"}} }),
    m_histSvc("THistSvc", name)
  {
    // NOTE: No declareProperty(...) — all config via Gaudi::Property below.
  }

  // --------------- knobs (Gaudi::Property only — no declareProperty) ---------------

  // physics / clustering
  Gaudi::Property<double>   m_Bz        {this, "Bz", 2.0,  "Uniform Bz [T] (for pT conversion/logging)"};
  Gaudi::Property<int>      m_pdg       {this, "PDG", 13,   "PDG hypothesis (charge sign)"};
  Gaudi::Property<unsigned> m_minGroup  {this, "MinGroupSize", 6u, "Minimum hits per cluster to fit"};
  Gaudi::Property<double>   m_epsMM     {this, "DBSCAN_EpsMM", 20.0, "DBSCAN epsilon [mm]"};
  Gaudi::Property<unsigned> m_minPts    {this, "DBSCAN_MinPts", 6u, "DBSCAN minPts"};
  Gaudi::Property<bool>     m_dedup     {this, "DeduplicateHits", true, "Drop consecutive near-duplicates"};
  Gaudi::Property<double>   m_dedupTolMM{this, "DedupTolMM", 0.25, "Dedup tolerance [mm]"};

  // histogram controls
  Gaudi::Property<std::string> m_histStream {this, "HistStream", "simple", "THistSvc stream (file logical name)"};
  Gaudi::Property<int>         m_maxEvtY    {this, "MaxEventsY", 2000, "Y span for 2D 'vs event' plots"};
  Gaudi::Property<unsigned>    m_ptBins     {this, "PtBins", 100u, "pT bins"};
  Gaudi::Property<double>      m_ptMax      {this, "PtMax", 100.0, "pT max [GeV]"};
  Gaudi::Property<double>      m_etaMax     {this, "EtaMax", 3.0,   "|eta| max"};

  // "Material effects" (covariance inflation) — lightweight
  Gaudi::Property<bool>   m_useMatEff     {this, "UseMaterialEffects", false,
                                           "If true, estimate X/X0 per cluster and inflate covariances"};
  Gaudi::Property<bool>   m_useTGeoPath   {this, "UseTGeoPath", true,
                                           "If true and gGeoManager present, estimate X/X0 via TGeo midpoints"};
  Gaudi::Property<double> m_fallbackXOverX0 {this, "FallbackXOverX0", 0.02,
                                             "Fallback integrated material (X/X0) if TGeo not available"};
  Gaudi::Property<double> m_msK_GeV       {this, "MS_K_GeV", 0.0136,
                                           "Highland constant (13.6 MeV) in GeV"};
  Gaudi::Property<double> m_msScale       {this, "MS_Scale", 1.0,
                                           "Extra scale factor on MS variance additions"};

  // base covariances for exported TrackState (diagonal)
  Gaudi::Property<float>  m_cov_d0     {this, "BaseVar_d0",        1.0f,   "base var(d0) [mm^2]"};
  Gaudi::Property<float>  m_cov_phi    {this, "BaseVar_phi",       1e-3f,  "base var(phi) [rad^2]"};
  Gaudi::Property<float>  m_cov_omega  {this, "BaseVar_omega",     1e-8f,  "base var(omega) [(1/mm)^2]"};
  Gaudi::Property<float>  m_cov_z0     {this, "BaseVar_z0",        1.0f,   "base var(z0) [mm^2]"};
  Gaudi::Property<float>  m_cov_tanL   {this, "BaseVar_tanLambda", 1e-2f,  "base var(tanLambda) [1]"};

  // state
  ServiceHandle<ITHistSvc> m_histSvc;
  mutable unsigned long long m_evtCounter{0};

  // histos
  mutable TH1F* h_pt{nullptr};
  mutable TH1F* h_phi{nullptr};
  mutable TH1F* h_theta{nullptr};
  mutable TH1F* h_eta{nullptr};
  mutable TH1F* h_omega{nullptr};
  mutable TH1F* h_radius{nullptr};
  mutable TH1F* h_tanL{nullptr};
  mutable TH1F* h_nTrk{nullptr};

  mutable TH2F* h_pt_vs_evt{nullptr};
  mutable TH2F* h_phi_vs_evt{nullptr};
  mutable TH2F* h_theta_vs_evt{nullptr};
  mutable TH2F* h_eta_vs_evt{nullptr};
  mutable TH2F* h_omega_vs_evt{nullptr};

  StatusCode initialize() override {
    info() << "SimpleFitDCHFitter init | Bz=" << m_Bz.value()
           << " | PDG=" << m_pdg.value()
           << " | epsMM=" << m_epsMM.value()
           << " | minPts=" << m_minPts.value()
           << " | minGroup=" << m_minGroup.value()
           << " | HistStream=" << m_histStream.value()
           << " | UseMaterialEffects=" << (m_useMatEff.value() ? "true":"false")
           << " | UseTGeoPath=" << (m_useTGeoPath.value() ? "true":"false")
           << " | FallbackXOverX0=" << m_fallbackXOverX0.value()
           << endmsg;

    if (!m_histSvc.retrieve().isSuccess()) {
      warning() << "THistSvc NOT available; histograms will not be written." << endmsg;
    } else {
      const std::string base = "/" + m_histStream.value() + "/";

      auto mk1 = [&](const char* n, const char* t, int nb, double lo, double hi)->TH1F* {
        TH1F* h = new TH1F(n,t,nb,lo,hi); h->Sumw2();
        m_histSvc->regHist(base + n, h).ignore(); return h;
      };
      auto mk2 = [&](const char* n, const char* t,
                     int nbx,double xlo,double xhi, int nby,double ylo,double yhi)->TH2F* {
        TH2F* h = new TH2F(n,t,nbx,xlo,xhi,nby,ylo,yhi);
        m_histSvc->regHist(base + n, h).ignore(); return h;
      };

      const int   nEvtY   = std::max(1, m_maxEvtY.value());
      const double yMin   = 0.0, yMax = double(nEvtY);

      h_pt     = mk1("pt",     "p_{T} [GeV]",          m_ptBins.value(), 0.0, m_ptMax.value());
      h_phi    = mk1("phi",    "#phi [rad]",           72, -M_PI, M_PI);
      h_theta  = mk1("theta",  "#theta [rad]",         90, 0.0, M_PI);
      h_eta    = mk1("eta",    "#eta",                 60, -m_etaMax.value(), m_etaMax.value());
      h_omega  = mk1("omega",  "#omega [1/mm]",       200, -0.02, 0.02);
      h_radius = mk1("radius_mm", "R [mm]",           150, 0.0, m_ptMax.value() * 1000.0/(0.3*m_Bz.value()));
      h_tanL   = mk1("tanLambda", "tan#lambda",       120, -6.0, 6.0);
      h_nTrk   = mk1("nTracksPerEvent", "tracks / event", 51, -0.5, 50.5);

      h_pt_vs_evt    = mk2("pt_vs_evt",    "p_{T} vs event; p_{T} [GeV]; event index",
                           m_ptBins.value(), 0.0, m_ptMax.value(), nEvtY, yMin, yMax);
      h_phi_vs_evt   = mk2("phi_vs_evt",   "#phi vs event; #phi [rad]; event index",
                           72, -M_PI, M_PI, nEvtY, yMin, yMax);
      h_theta_vs_evt = mk2("theta_vs_evt", "#theta vs event; #theta [rad]; event index",
                           90, 0.0, M_PI, nEvtY, yMin, yMax);
      h_eta_vs_evt   = mk2("eta_vs_evt",   "#eta vs event; #eta; event index",
                           60, -m_etaMax.value(), m_etaMax.value(), nEvtY, yMin, yMax);
      h_omega_vs_evt = mk2("omega_vs_evt", "#omega vs event; #omega [1/mm]; event index",
                           200, -0.02, 0.02, nEvtY, yMin, yMax);
    }

    return StatusCode::SUCCESS;
  }

  edm4hep::TrackCollection operator()(const edm4hep::TrackerHit3DCollection& hits) const override {
    edm4hep::TrackCollection out;
    const unsigned long long evtIdx = m_evtCounter++;  // monotonically increasing
    if (hits.empty()) { if (h_nTrk) h_nTrk->Fill(0); return out; }

    // 1) collect positions (mm) by index
    std::vector<TVector3> P; P.reserve(hits.size());
    for (size_t i=0;i<hits.size();++i) {
      const auto p = hits[i].getPosition();
      P.emplace_back(p.x, p.y, p.z);
    }

    // 2) cluster
    const auto labels = dbscan_mm(P, m_epsMM.value(), m_minPts.value());
    int maxLbl = -1; for (int L: labels) maxLbl = std::max(maxLbl, L);
    if (maxLbl < 0) { if (h_nTrk) h_nTrk->Fill(0); return out; }

    const int qSign = chargeFromPDG(m_pdg.value());
    int nTrkThisEvent = 0;

    // 3) per-cluster fit & export
    for (int L=0; L<=maxLbl; ++L) {
      std::vector<size_t> idx;
      idx.reserve(P.size());
      for (size_t i=0;i<labels.size();++i) if (labels[i]==L) idx.push_back(i);
      if (idx.size() < std::max<size_t>(m_minGroup.value(), 3u)) continue;

      if (m_dedup.value() && idx.size()>=2) {
        std::vector<size_t> idx2; idx2.reserve(idx.size());
        TVector3 prev(1e99,1e99,1e99);
        const double tol2 = m_dedupTolMM.value()*m_dedupTolMM.value();
        for (size_t k : idx) { if ((P[k]-prev).Mag2() >= tol2) { idx2.push_back(k); prev = P[k]; } }
        if (idx2.size() >= 3) idx.swap(idx2);
      }
      if (idx.size() < 3) continue;

      std::vector<TVector3> Pc; Pc.reserve(idx.size());
      for (auto k: idx) Pc.push_back(P[k]);

      // circle in XY
      CircleXY cir = kasa_circle_xy(Pc);
      if (!cir.ok) continue;
      const double R_mm = cir.R;

      // pick a reference point near origin as "perigee-like"
      size_t imin=0; double r2min=std::numeric_limits<double>::infinity();
      for (size_t j=0;j<Pc.size();++j){ const double r2=Pc[j].Perp2(); if (r2<r2min){r2min=r2; imin=j;} }
      const TVector3 Pmin = Pc[imin];

      // angular coordinate about center
      std::vector<double> phi(Pc.size());
      for (size_t j=0;j<Pc.size();++j) phi[j]=std::atan2(Pc[j].Y()-cir.cy, Pc[j].X()-cir.cx);
      for (size_t j=1;j<Pc.size();++j) phi[j]=unwrap(phi[j], phi[j-1]);

      // sort by angle
      std::vector<size_t> ord(Pc.size()); std::iota(ord.begin(),ord.end(),0);
      std::sort(ord.begin(),ord.end(),[&](size_t a,size_t b){return phi[a] < phi[b];});

      // z(phi) = a + b*phi  -> tanL = b / R
      double S1=0,Sph=0,Sz=0,Sphp=0,Sphz=0;
      for (auto j: ord){ const double ph=phi[j]; const double z=Pc[j].Z(); S1+=1; Sph+=ph; Sz+=z; Sphp+=ph*ph; Sphz+=ph*z; }
      const double det = S1*Sphp - Sph*Sph;
      double b=0;
      if (std::fabs(det) > 1e-12) b = (S1*Sphz - Sph*Sz)/det;
      const double tanL = (R_mm>1e-9) ? (b / R_mm) : 0.0;

      // tangent direction at Pmin
      TVector3 rvec(Pmin.X()-cir.cx, Pmin.Y()-cir.cy, 0.0);
      if (rvec.Perp2()==0) rvec=TVector3(1,0,0);
      const TVector3 rhat = rvec.Unit();
      TVector3 that(-rhat.Y(), rhat.X(), 0.0);  // 90° CCW
      TVector3 tangent = TVector3(that.X(), that.Y(), tanL).Unit();

      // basic kinematics
      const double pt = 0.0003 * m_Bz.value() * R_mm;              // GeV (R in mm)
      const double p  = pt * std::sqrt(1.0 + tanL*tanL);           // GeV (beta≈1)
      const double theta = std::atan2(1.0, tanL);                  // 0..pi
      const double eta   = -std::log(std::tan(0.5*theta));

      // --- lightweight material effects: add MS to phi/d0/z0 variances
      float add_var_phi = 0.f, add_var_d0 = 0.f, add_var_z0 = 0.f;
      if (m_useMatEff.value()) {
        double XoX0 = m_fallbackXOverX0.value();
        if (m_useTGeoPath.value() && gGeoManager) {
          XoX0 = estimate_x_over_x0_midpoint(Pc, m_fallbackXOverX0.value());
        }
        XoX0 = std::max(0.0, XoX0);

        // Highland: theta0 ≈ (13.6 MeV / p) sqrt(X/X0) * [1 + 0.038 ln(X/X0)]
        // Use p in GeV; msK in GeV.
        const double msK = m_msK_GeV.value();
        double theta0 = 0.0;
        if (p > 1e-6 && XoX0 > 0.0) {
          const double corr = 1.0 + 0.038 * std::log(std::max(1e-6, XoX0));
          theta0 = (msK / p) * std::sqrt(XoX0) * corr;
        }
        theta0 *= m_msScale.value();

        const double Lchar_mm = R_mm; // a crude length scale for transverse blow-up
        add_var_phi = float(theta0*theta0);                 // rad^2
        add_var_d0  = float((Lchar_mm*theta0)*(Lchar_mm*theta0)); // mm^2
        add_var_z0  = float((Lchar_mm*theta0*tanL)*(Lchar_mm*theta0*tanL)); // mm^2
      }

      // export track
      auto trk = out.create();
      trk.setType(m_pdg.value());
      for (auto k: idx) trk.addToTrackerHits(hits[k]);

      addAtIPStateWithCov(trk, Pmin, tangent, R_mm, tanL, qSign,
                          m_cov_d0.value(), m_cov_phi.value(), m_cov_omega.value(),
                          m_cov_z0.value(), m_cov_tanL.value(),
                          add_var_phi, add_var_d0, add_var_z0);

      // fill histos
      const double phi_xy= std::atan2(tangent.Y(), tangent.X());
      const double omega = (R_mm>1e-6 ? (qSign / R_mm) : 0.0);       // 1/mm
      if (h_pt)     h_pt->Fill(pt);
      if (h_phi)    h_phi->Fill(phi_xy);
      if (h_theta)  h_theta->Fill(theta);
      if (h_eta)    h_eta->Fill(eta);
      if (h_omega)  h_omega->Fill(omega);
      if (h_radius) h_radius->Fill(R_mm);
      if (h_tanL)   h_tanL->Fill(tanL);

      const double yevt = std::min<double>(evtIdx + 0.5, double(std::max(1,m_maxEvtY.value())) - 1e-3);
      if (h_pt_vs_evt)    h_pt_vs_evt->Fill(pt,    yevt);
      if (h_phi_vs_evt)   h_phi_vs_evt->Fill(phi_xy, yevt);
      if (h_theta_vs_evt) h_theta_vs_evt->Fill(theta, yevt);
      if (h_eta_vs_evt)   h_eta_vs_evt->Fill(eta,   yevt);
      if (h_omega_vs_evt) h_omega_vs_evt->Fill(omega, yevt);

      ++nTrkThisEvent;
    }

    if (h_nTrk) h_nTrk->Fill(nTrkThisEvent);
    return out;
  }

  StatusCode finalize() override { return StatusCode::SUCCESS; }
};

DECLARE_COMPONENT(SimpleFitDCHFitter)
