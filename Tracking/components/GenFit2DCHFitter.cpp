// ======================================================================
// GenFit2DCHFitter.cpp  -- fit GGTF 3D hits with GenFit2 (robust)
//   - TGeo material effects (cm units internally) [optional]
//   - Group hits per GGTF label (quality/type); DBSCAN fallback if all zero
//   - Diagonal anisotropic measurement covariance (XY/Z) + PD guards
//   - XY-circle pT seeding with guards; per-group sort + optional dedup
//   - Clamp on pT AND |p| to avoid βγ→0 failures
//   - Optional cap on measurements per group (for conditioning)
//   - Retry path: inflate covariances if no FitterInfo after base fit
//   - Canonical SpacepointMeasurement attach (7-arg ABI)
//   - Exports an EDM4hep TrackState(AtIP) per track:
//        * omega = q/pT [GeV^-1]   (EDM/LCIO convention)
//        * time  = pT  [GeV]       (direct pT export; read this for pT)
//   - Optional pre-fit z(φ) outlier rejection to kill z-spurs
//   - Writes JSON config into metadata store key "GenFit2DCHFitterConfig"
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

template <typename, typename = void> struct has_getQuality : std::false_type {};
template <typename T>
struct has_getQuality<T, std::void_t<decltype(std::declval<T>().getQuality())>>
  : std::true_type {};

template <typename, typename = void> struct has_getType : std::false_type {};
template <typename T>
struct has_getType<T, std::void_t<decltype(std::declval<T>().getType())>>
  : std::true_type {};

template <typename HitT>
inline int hitLabel(const HitT& h) {
  if constexpr (has_getQuality<HitT>::value) return static_cast<int>(h.getQuality());
  else if constexpr (has_getType<HitT>::value) return static_cast<int>(h.getType());
  else return 0;
}

inline void makeDiagonalFloor(TMatrixDSym& C, double eps) {
  for (int i = 0; i < C.GetNrows(); ++i)
    C(i, i) = std::max(C(i, i), eps);
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

inline double projS(const TVector3& origin, const TVector3& dirUnit, const TVector3& p) {
  return dirUnit.Dot(p - origin);
}

// --- circle center + radius in XY plane --------------------------------
inline bool circleCenterRadiusXY(const TVector3& A,
                                 const TVector3& B,
                                 const TVector3& C,
                                 TVector3& center_xy,
                                 double& R)
{
  const double x1 = A.X(), y1 = A.Y();
  const double x2 = B.X(), y2 = B.Y();
  const double x3 = C.X(), y3 = C.Y();

  const double a = x1*(y2 - y3) - y1*(x2 - x3) + x2*y3 - x3*y2;
  const double d = 2.0 * a;
  if (std::abs(d) < 1e-9) {
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
                             const TVector3& C)
{
  TVector3 c(0., 0., 0.);
  double R = 1e9;
  if (!circleCenterRadiusXY(A, B, C, c, R)) return 1e9;
  return R;
}
// ----------------------------------------------------------------------

struct Group {
  std::vector<TVector3> P;
  std::vector<size_t>   idxs;
};

static std::vector<int> dbscan(
  const std::vector<TVector3>& P,
  double eps, unsigned minPts)
{
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
                         int chargeSign)
{
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
                                   int fallbackCharge)
{
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
      m_cfgMeta("GenFit2DCHFitterConfig", Gaudi::DataHandle::Writer)
  {
    // Gaudi::Property<> handles registration; no declareProperty needed.
  }

  // ----------------- Properties -----------------

  // Physics knobs
  Gaudi::Property<double>  m_Bz {this, "Bz", 2.0, "Bz field [T]"};
  Gaudi::Property<int>     m_pdg{this, "PDG", 13,  "PDG hypothesis"};

  // Material effects
  Gaudi::Property<bool>    m_useMatEff{this, "UseMaterialEffects", true,
                                       "Use TGeoMaterialInterface for GenFit MaterialEffects"};

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
  Gaudi::Property<double>  m_seedPMinGeV     {this, "SeedPMinGeV",     0.80,
                                              "Min |p| [GeV]"};
  Gaudi::Property<bool>    m_sortHits        {this, "SortHits", true,
                                              "Sort hits along seed direction"};
  Gaudi::Property<bool>    m_dedup           {this, "DeduplicateHits", true,
                                              "Drop nearly-identical hits"};
  Gaudi::Property<double>  m_dedupTolMM      {this, "DedupTolMM", 0.25,
                                              "Dedup tol [mm]"};

  // Grouping
  Gaudi::Property<unsigned> m_minGroupSize     {this, "MinGroupSize", 6u,
                                                "Minimum hits per group"};
  Gaudi::Property<bool>     m_useFallbackClust {this, "UseFallbackClustering", true,
                                                "Enable DBSCAN fallback"};
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

  // Optional job tag (for metadata stamping)
  Gaudi::Property<std::string> m_jobTag{this, "JobTag", "",
                                        "Optional job tag string recorded in metadata"};

  StatusCode initialize() override {
    genfit::FieldManager::getInstance()->init(
      new genfit::ConstField(0., 0., 10.0*m_Bz.value()));

    if (m_useMatEff.value()) {
      if (!gGeoManager) {
        warning() << "UseMaterialEffects=True but gGeoManager is null; "
                  << "proceeding WITHOUT material effects."
                  << endmsg;
      } else {
        try {
          genfit::MaterialEffects::getInstance()->init(
            new genfit::TGeoMaterialInterface());
          info() << "Initialized GenFit MaterialEffects with TGeoMaterialInterface."
                 << endmsg;
        } catch (const std::exception& e) {
          warning() << "Failed to initialize MaterialEffects(TGeo): " << e.what()
                    << " — proceeding WITHOUT material effects."
                    << endmsg;
        }
      }
    } else {
      info() << "UseMaterialEffects = false — running WITHOUT material effects."
             << endmsg;
    }

    m_fitter = std::make_unique<genfit::KalmanFitterRefTrack>();
    m_fitter->setMaxIterations(12);

    info() << "GenFit2DCHFitter init | Bz=" << m_Bz.value()
           << " | PDG=" << m_pdg.value()
           << " | UseMaterialEffects=" << (m_useMatEff.value() ? "true" : "false")
           << " | posScale=" << m_posScale.value()
           << " | len2m=" << m_internalLenToM.value()
           << " | HitSigmaXY=" << m_hitSigmaXYMM.value() << " mm"
           << " | HitSigmaZ="  << m_hitSigmaZMM.value()  << " mm"
           << " | SeedPosSigma=" << m_seedPosSigmaMM.value() << " mm"
           << " | SeedMomSigma=" << m_seedMomSigmaGeV.value() << " GeV"
           << " | SeedPTMin=" << m_seedPTMinGeV.value()
           << " | SeedPTMax=" << m_seedPTMaxGeV.value()
           << " | SeedPMin="  << m_seedPMinGeV.value()
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
      std::strftime(tbuf, sizeof(tbuf), "%Y-%m-%dT%H:%M:%SZ",
                    std::gmtime(&now));

      os << "{";
      os << "\"component\":\"" << name() << "\"";
      os << ",\"timestamp_utc\":\"" << tbuf << "\"";
      os << ",\"JobTag\":\"" << m_jobTag.value() << "\"";
      os << ",\"Bz_T\":" << m_Bz.value();
      os << ",\"PDG\":" << m_pdg.value();
      os << ",\"UseMaterialEffects\":" << (m_useMatEff.value() ? "true" : "false");
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

      const std::string json = os.str();
      m_cfgMeta.put(json);

      info() << "Wrote GenFit2DCHFitter configuration metadata "
             << "(key='GenFit2DCHFitterConfig')" << endmsg;
    } catch (const std::exception& e) {
      warning() << "Failed to write GenFit2DCHFitter metadata: " << e.what()
                << endmsg;
    } catch (...) {
      warning() << "Failed to write GenFit2DCHFitter metadata (unknown exception)"
                << endmsg;
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

  // --- z(φ) outlier filter ---------------------------------------------
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
    if (std::abs(denom) < 1e-8) {
      return false;
    }
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
      if (!out && nSigma > 0.0 && sigma_cm > 0.0 && r_cm > nSigma*sigma_cm)
        out = true;

      if (!out) {
        keep[i] = 1;
        ++nKeep;
      } else {
        keep[i] = 0;
        ++nDrop;
      }
    }

    if (nDrop == 0) return false;

    const double fracKeep = double(nKeep) / double(N);
    if (nKeep < static_cast<size_t>(m_minGroupSize.value()) ||
        fracKeep < m_zOutlierMinFracKeep.value()) {
      debug() << "ZOutlierFilter[label=" << label << "] would drop "
              << nDrop << "/" << N << " hits (keepFrac=" << fracKeep
              << "), below MinGroupSize or MinFracKeep — disabled."
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

    info() << "ZOutlierFilter[label=" << label << "] dropped "
           << nDrop << "/" << N << " hits; kept=" << nKeep
           << " (keepFrac=" << fracKeep
           << ", sigma_z=" << (sigma_cm / ps) << " mm)"
           << endmsg;

    return true;
  }
  // --------------------------------------------------------------------

  edm4hep::TrackCollection
  operator()(const edm4hep::TrackerHit3DCollection& hits) const override {
    edm4hep::TrackCollection out;
    if (hits.size() < 3u) return out;

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

    if (!anyNonZero && m_useFallbackClust.value()) {
      std::vector<TVector3> Pall; Pall.reserve(hits.size());
      for (size_t i = 0; i < hits.size(); ++i) {
        const auto p = hits[i].getPosition();
        Pall.emplace_back(m_posScale.value()*p.x,
                          m_posScale.value()*p.y,
                          m_posScale.value()*p.z);
      }
      const auto labels = dbscan(Pall, m_fallbackEpsCM.value(),
                                 m_fallbackMinPts.value());
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
           << " (label=quality/type or DBSCAN; 0 means unlabeled)"
           << endmsg;

    const double sxy = m_hitSigmaXYMM.value() * m_posScale.value();
    const double sz  = m_hitSigmaZMM.value()  * m_posScale.value();
    TMatrixDSym Cmeas(3); Cmeas.Zero();
    Cmeas(0,0) = sxy*sxy;
    Cmeas(1,1) = sxy*sxy;
    Cmeas(2,2) = sz*sz;
    ensurePD(Cmeas, 1e-6, 4.0, 6);

    for (auto& kv : groups) {
      const int label = kv.first;
      auto& P    = kv.second.P;
      auto& idxs = kv.second.idxs;

      if (m_dedup.value() && !P.empty()) {
        const double tol2 = std::pow(m_dedupTolMM.value() * m_posScale.value(), 2);
        std::vector<TVector3> P2; P2.reserve(P.size());
        std::vector<size_t>   I2; I2.reserve(idxs.size());
        TVector3 prev(1e99,1e99,1e99);
        for (size_t k = 0; k < P.size(); ++k) {
          if ((P[k] - prev).Mag2() < tol2) continue;
          P2.push_back(P[k]);
          I2.push_back(idxs[k]);
          prev = P[k];
        }
        P.swap(P2);
        idxs.swap(I2);
      }

      if (P.size() < m_minGroupSize.value()) continue;

      TVector3 pos0 = P.front();
      TVector3 posL = P.back();
      TVector3 dir  = (posL - pos0);
      if (dir.Mag2() < 1e-12) dir = TVector3(0,0,1);
      dir = dir.Unit();

      if (m_sortHits.value()) {
        std::vector<size_t> order(P.size());
        std::iota(order.begin(), order.end(), 0);
        std::sort(order.begin(), order.end(),
                  [&](size_t a, size_t b){
                    return projS(pos0, dir, P[a]) < projS(pos0, dir, P[b]);
                  });
        std::vector<TVector3> Psorted; Psorted.reserve(P.size());
        std::vector<size_t>   Isorted; Isorted.reserve(idxs.size());
        for (auto k : order) {
          Psorted.push_back(P[k]);
          Isorted.push_back(idxs[k]);
        }
        P.swap(Psorted);
        idxs.swap(Isorted);
        pos0 = P.front();
        posL = P.back();
        dir  = (posL - pos0).Mag2() < 1e-12 ? TVector3(0,0,1)
                                            : (posL - pos0).Unit();
      }

      if (m_maxMeasPerGroup.value() > 0 &&
          P.size() > m_maxMeasPerGroup.value()) {
        const unsigned cap = m_maxMeasPerGroup.value();
        const size_t N = P.size();
        std::vector<TVector3> P2; P2.reserve(cap);
        std::vector<size_t>   I2; I2.reserve(cap);
        for (size_t j = 0; j < cap; ++j) {
          size_t k = static_cast<size_t>(
            std::round(double(j) * (N-1) / double(cap-1)));
          P2.push_back(P[k]);
          I2.push_back(idxs[k]);
        }
        P.swap(P2);
        idxs.swap(I2);
      }

      if (P.size() < m_minGroupSize.value()) continue;

      // z(φ) filter: estimate circle center, then apply filter
      TVector3 centerXY(0., 0., 0.);
      double   R_forFilter = 1e9;
      {
        const TVector3 A0 = P.front();
        const TVector3 B0 = P[P.size()/2];
        const TVector3 C0 = P.back();
        bool haveCircle = circleCenterRadiusXY(A0, B0, C0, centerXY, R_forFilter);
        if (haveCircle) {
          (void)applyZOutlierFilter(label, P, idxs, centerXY);
        }
      }
      if (P.size() < m_minGroupSize.value()) continue;

      // Helical seed from (possibly filtered) hits
      const TVector3 A = P.front();
      const TVector3 B = P[P.size()/2];
      const TVector3 C = P.back();
      const double R_int = circleRadiusXY(A,B,C);            // cm
      const double R_m   = R_int * m_internalLenToM.value(); // m
      double pTseed = 0.3 * m_Bz.value() * R_m;              // GeV
      if (!std::isfinite(pTseed) || pTseed <= 0) pTseed = 1.0;
      pTseed = std::clamp(pTseed,
                          m_seedPTMinGeV.value(),
                          m_seedPTMaxGeV.value());

      pos0 = P.front();
      posL = P.back();
      dir  = (posL - pos0);
      if (dir.Mag2() < 1e-12) dir = TVector3(0,0,1);
      dir = dir.Unit();

      const double cosTheta = std::clamp(std::abs(dir.Z()), 0.0, 0.999999);
      const double sinTheta = std::sqrt(std::max(1e-4, 1.0 - cosTheta*cosTheta));

      double pMag = pTseed / sinTheta;
      if (!std::isfinite(pMag) || pMag <= 0) pMag = m_seedPMinGeV.value();
      pMag = std::max(pMag, m_seedPMinGeV.value());

      TVector3 mom0 = pMag * dir;

      info() << "Seed[label=" << label << "] | n=" << P.size()
             << " R_int(cm)=" << R_int
             << " pTseed(GeV)=" << pTseed
             << " pMag(GeV)=" << pMag
             << endmsg;

      auto rep_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
      genfit::Track fitTrack(rep_up.release(), pos0, mom0);
      fitTrack.setCovSeed(makeSeedCov(/*posInfl*/1.0, /*momInfl*/1.0));

      int detId = label;
      int hitId = 0;
      for (const auto& v : P) {
        TVectorD pos(3);
        pos[0] = v.X();
        pos[1] = v.Y();
        pos[2] = v.Z();
        auto* tp   = new genfit::TrackPoint(&fitTrack);
        auto* meas = new genfit::SpacepointMeasurement(
                        pos, TMatrixDSym(Cmeas),
                        detId, hitId, tp,
                        false, false);
        tp->addRawMeasurement(meas);
        fitTrack.insertPoint(tp);
        ++hitId;
      }
      if (fitTrack.getNumPointsWithMeasurement() == 0) continue;

      auto run_fit = [&](genfit::Track& trk,
                         const char* tag)->const genfit::FitStatus* {
        try {
          m_fitter->processTrack(&trk);
        } catch (const genfit::Exception& e) {
          warning() << "GenFit exception during processTrack (label=" << label
                    << ", " << tag << "): " << e.what() << endmsg;
          return nullptr;
        } catch (const std::exception& e) {
          warning() << "Std exception during processTrack (label=" << label
                    << ", " << tag << "): " << e.what() << endmsg;
          return nullptr;
        } catch (...) {
          warning() << "Unknown exception during processTrack (label="
                    << label << ", " << tag << ")" << endmsg;
          return nullptr;
        }
        genfit::AbsTrackRep* rep = trk.getCardinalRep();
        return rep ? trk.getFitStatus(rep) : nullptr;
      };

      const genfit::FitStatus* fs_base = run_fit(fitTrack, "base");
      if (fs_base) {
        info() << "FitStatus[label=" << label << "][base] | fitted="
               << fs_base->isFitted()
               << " converged=" << fs_base->isFitConverged()
               << " Ndf=" << fs_base->getNdf()
               << " Chi2=" << fs_base->getChi2()
               << " P=" << fs_base->getPVal()
               << endmsg;
      }

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

      bool ok = (fs_base && has_any_FI(fitTrack));

      if (!ok && m_retryIfNoFI.value()) {
        warning() << "No TrackPoint has FitterInfo (label=" << label
                  << ", base) — retry with inflated covariances."
                  << endmsg;

        auto rep2_up = std::make_unique<genfit::RKTrackRep>(m_pdg.value());
        genfit::Track fitTrack2(rep2_up.release(), pos0, mom0);

        fitTrack2.setCovSeed(
          makeSeedCov(m_retrySeedPosInfl.value(),
                      m_retrySeedMomInfl.value()));

        TMatrixDSym Cmeas_retry(3); Cmeas_retry.Zero();
        Cmeas_retry(0,0) = Cmeas(0,0)*m_retryMeasInfl.value();
        Cmeas_retry(1,1) = Cmeas(1,1)*m_retryMeasInfl.value();
        Cmeas_retry(2,2) = Cmeas(2,2)*m_retryMeasInfl.value();
        ensurePD(Cmeas_retry, 1e-6, 4.0, 6);

        int det2 = label, hid2 = 0;
        for (const auto& v : P) {
          TVectorD pos(3);
          pos[0] = v.X();
          pos[1] = v.Y();
          pos[2] = v.Z();
          auto* tp   = new genfit::TrackPoint(&fitTrack2);
          auto* meas = new genfit::SpacepointMeasurement(
                          pos, Cmeas_retry,
                          det2, hid2, tp,
                          false, false);
          tp->addRawMeasurement(meas);
          fitTrack2.insertPoint(tp);
          ++hid2;
        }

        const genfit::FitStatus* fs_retry = run_fit(fitTrack2, "retry");
        if (fs_retry) {
          info() << "FitStatus[label=" << label << "][retry] | fitted="
                 << fs_retry->isFitted()
                 << " converged=" << fs_retry->isFitConverged()
                 << " Ndf=" << fs_retry->getNdf()
                 << " Chi2=" << fs_retry->getChi2()
                 << " P=" << fs_retry->getPVal()
                 << endmsg;
        }

        if (fs_retry && has_any_FI(fitTrack2)) {
          auto trk = out.create();
          trk.setType(m_pdg.value());
          try {
            trk.setChi2(fs_retry->getChi2());
            trk.setNdf(fs_retry->getNdf());
          } catch (...) {}
          for (auto i : idxs) trk.addToTrackerHits(hits[i]);

          const int qSeed = chargeFromPDG(m_pdg.value());
          if (!addBestFittedAtIPState(trk, fitTrack2,
                                      m_Bz.value(),
                                      m_posScale.value(),
                                      qSeed)) {
            addAtIPState(trk, pos0, mom0,
                         m_Bz.value(),
                         m_posScale.value(),
                         qSeed);
          }
          continue;
        } else {
          warning() << "No TrackPoint has FitterInfo (label=" << label
                    << ", retry)." << endmsg;
        }
      }

      if (ok) {
        auto trk = out.create();
        trk.setType(m_pdg.value());
        if (fs_base) {
          try {
            trk.setChi2(fs_base->getChi2());
            trk.setNdf(fs_base->getNdf());
          } catch (...) {}
        }
        for (auto i : idxs) trk.addToTrackerHits(hits[i]);

        const int qSeed = chargeFromPDG(m_pdg.value());
        if (!addBestFittedAtIPState(trk, fitTrack,
                                    m_Bz.value(),
                                    m_posScale.value(),
                                    qSeed)) {
          addAtIPState(trk, pos0, mom0,
                       m_Bz.value(),
                       m_posScale.value(),
                       qSeed);
        }
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
