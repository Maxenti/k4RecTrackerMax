#include "DCHdigi_v02.h"

// Gaudi
#include <GaudiKernel/MsgStream.h>

// edm4hep
#include "edm4hep/utils/vector_utils.h"

// DD4hep
#include "DD4hep/Detector.h"

// STL
#include <algorithm>
#include <unordered_map>
#include <sstream>
#include <limits>
#include <utility>

namespace {

struct ParticleClusterInfo {
  double beta_gamma     = 0.0;
  double path_length_mm = 0.0;
};

struct HitInfo {
  size_t      simhit_index{0};        // index into original input collection
  double      arrival_time_ns     = 0.0;
  edm4hep::Vector3d position_mm   {};
  double      distance_to_wire_mm = 0.0;
};

} // namespace

DCHdigi_v02::DCHdigi_v02(const std::string& name, ISvcLocator* svcLoc)
  : MultiTransformer(
      name, svcLoc,
      // inputs
      { KeyValues("InputSimHitCollection", {""}),
        KeyValues("HeaderName", {"EventHeader"}) },
      // outputs
      { KeyValues("OutputDigihitCollection", {"DCHDigi2Collection"}),
        KeyValues("OutputLinkCollection",   {"DCHDigi2SimLinkCollection"}) }),
    m_digiMeta("DCHdigi_v02Config", Gaudi::DataHandle::Writer)
{
}

StatusCode DCHdigi_v02::initialize() {

  m_uniqueIDSvc = serviceLocator()->service(m_uidSvcName);
  if (!m_uniqueIDSvc) {
    error() << "Unable to locate UniqueIDGenSvc with name: " << m_uidSvcName << endmsg;
    return StatusCode::FAILURE;
  }

  m_geoSvc = serviceLocator()->service(m_geoSvcName);
  if (!m_geoSvc) {
    error() << "Unable to locate GeoSvc with name: " << m_geoSvcName << endmsg;
    return StatusCode::FAILURE;
  }

  // Retrieve the subdetector
  const std::string dch_name(m_dch_name.value());
  if (m_geoSvc->getDetector()->detectors().count(dch_name) == 0) {
    error() << "Detector <<" << dch_name << ">> does not exist." << endmsg;
    return StatusCode::FAILURE;
  }

  // DetElement & extension
  dd4hep::DetElement dch_detelem = m_geoSvc->getDetector()->detectors().at(dch_name);
  m_dch_info = dch_detelem.extension<dd4hep::rec::DCH_info>();
  if (!m_dch_info || !m_dch_info->IsValid()) {
    error() << "No valid DCH_info extension found for <<" << dch_name << ">>." << endmsg;
    return StatusCode::FAILURE;
  }

  // Decoder
  dd4hep::SensitiveDetector dch_sd = m_geoSvc->getDetector()->sensitiveDetector(dch_name);
  if (!dch_sd.isValid()) {
    error() << "No valid SensitiveDetector for <<" << dch_name << ">>." << endmsg;
    return StatusCode::FAILURE;
  }
  m_decoder = dch_sd.readout().idSpec().decoder();

  if (!(m_drift_velocity_um_per_ns.value() > 0.0)) {
    m_drift_velocity_um_per_ns.setValue(get_default_drift_velocity_um_per_ns());
    info() << "Drift velocity auto-set to " << m_drift_velocity_um_per_ns.value()
           << " um/ns for GasType=" << m_GasType.value() << endmsg;
  } else {
    info() << "Using user drift velocity: " << m_drift_velocity_um_per_ns.value() << " um/ns" << endmsg;
  }

  if (!(m_signal_velocity_mm_per_ns.value() > 0.0)) {
    error() << "Signal velocity must be positive!" << endmsg;
    return StatusCode::FAILURE;
  }

  if (!(m_deadtime_ns.value() >= 0.0)) {
    error() << "Deadtime_ns must be >= 0" << endmsg;
    return StatusCode::FAILURE;
  }

  if (!(m_minAbsCosStereo.value() > 0.0)) {
    error() << "MinAbsCosStereo must be > 0" << endmsg;
    return StatusCode::FAILURE;
  }

  m_event_counter.reset();

  // ---------------------------
  // Write configuration metadata (JSON string)
  // ---------------------------
  try {
    std::ostringstream os;
    os << "{";
    os << "\"component\":\"DCHdigi_v02\"";
    os << ",\"DCH_name\":\"" << m_dch_name.value() << "\"";
    os << ",\"GasType\":" << m_GasType.value();
    os << ",\"xyResolution_mm\":" << m_xy_resolution_mm.value();
    os << ",\"zResolution_mm\":" << m_z_resolution_mm.value();
    os << ",\"timeResolution_ns\":" << m_time_resolution_ns.value();
    os << ",\"Deadtime_ns\":" << m_deadtime_ns.value();
    os << ",\"DeadtimeFromFirstHit\":" << (m_deadtimeFromFirstHit.value() ? "true" : "false");
    os << ",\"DriftVelocity_um_per_ns\":" << m_drift_velocity_um_per_ns.value();
    os << ",\"SignalVelocity_mm_per_ns\":" << m_signal_velocity_mm_per_ns.value();
    os << ",\"MinAbsCosStereo\":" << m_minAbsCosStereo.value();
    os << ",\"UseClusterModel\":" << (m_useClusterModel.value() ? "true" : "false");
    os << ",\"ReadoutWindowStart_ns\":" << m_ReadoutWindowStartTime_ns.value();
    os << ",\"ReadoutWindowDuration_ns\":" << m_ReadoutWindowDuration_ns.value();
    if (!m_jobTag.value().empty()) {
      os << ",\"JobTag\":\"" << m_jobTag.value() << "\"";
    }
    os << "}";

    m_digiMeta.put(os.str());
    info() << "DCHdigi_v02 metadata written under key 'DCHdigi_v02Config'" << endmsg;
  } catch (const std::exception& e) {
    warning() << "Failed to write DCHdigi_v02 metadata: " << e.what() << endmsg;
  } catch (...) {
    warning() << "Failed to write DCHdigi_v02 metadata (unknown exception)" << endmsg;
  }

  info() << "DCHdigi_v02 init:"
         << " geo-only=" << (m_useClusterModel.value() ? "false" : "true")
         << " xyRes=" << m_xy_resolution_mm.value() << "mm"
         << " zRes="  << m_z_resolution_mm.value()  << "mm"
         << " timeRes=" << m_time_resolution_ns.value() << "ns"
         << " deadtime=" << m_deadtime_ns.value() << "ns"
         << " deadtimeFromFirst=" << (m_deadtimeFromFirstHit.value() ? "true" : "false")
         << endmsg;

  return StatusCode::SUCCESS;
}

std::tuple<
    extension::SenseWireHitCollection,
    extension::SenseWireHitSimTrackerHitLinkCollection>
DCHdigi_v02::operator()(const edm4hep::SimTrackerHitCollection& input,
                        const edm4hep::EventHeaderCollection& header) const {

  extension::SenseWireHitCollection               output;
  extension::SenseWireHitSimTrackerHitLinkCollection links;

  const auto engine_seed = m_uniqueIDSvc->getUniqueID(header, this->name());
  TRandom3 random_engine(engine_seed);

  debug() << "Processing event " << m_event_counter.value() << endmsg;
  m_event_counter += 1;

  // Group by cellID without copying SimTrackerHits: store indices into `input`.
  std::unordered_map<uint64_t, std::vector<size_t>> cell_map;
  cell_map.reserve(input.size());

  for (size_t i = 0; i < input.size(); ++i) {
    const auto& simhit = input[i];
    cell_map[simhit.getCellID()].push_back(i);
  }

  const double tStart = m_ReadoutWindowStartTime_ns.value();
  const double tEnd   = m_ReadoutWindowStartTime_ns.value() + m_ReadoutWindowDuration_ns.value();

  for (const auto& kv : cell_map) {
    const uint64_t cellID = kv.first;
    const auto&    idxs   = kv.second;

    const int layer = m_dch_info->CalculateILayerFromCellIDFields(
        m_decoder->get(cellID, "layer"),
        m_decoder->get(cellID, "superlayer"));
    const int nphi  = m_decoder->get(cellID, "nphi");

    const auto WireAzimuthalAngle = m_dch_info->Get_cell_phi_angle(layer, nphi);

    float WireStereoAngle = 0.f;
    {
      auto l = m_dch_info->database.at(layer);
      const auto cell_rave_z0 = 0.5 * (l.radius_fdw_z0 + l.radius_fuw_z0);
      WireStereoAngle = (-1.f) * l.StereoSign() * m_dch_info->stereoangle_z0(cell_rave_z0);
    }

    const double cosStereo = std::cos(static_cast<double>(WireStereoAngle));
    if (std::abs(cosStereo) < m_minAbsCosStereo.value()) {
      // Extremely pathological geometry; skip safely.
      continue;
    }

    std::vector<HitInfo> hit_info_vector;
    hit_info_vector.reserve(idxs.size());

    for (const auto idx : idxs) {
      const auto& simhit = input[idx];

      const auto pos_ddu = toTVector3(simhit.getPosition()) * dd4hep::mm;

      const auto hit_to_wire_vec_ddu   = m_dch_info->Calculate_hitpos_to_wire_vector(layer, nphi, pos_ddu);
      auto       proj_on_wire_ddu      = pos_ddu + hit_to_wire_vec_ddu;
      const double distance_to_wire_mm = hit_to_wire_vec_ddu.Mag() / dd4hep::mm;

      // Smear transverse distance (simple model). Clamp to non-negative.
      const double smear_xy_mm = random_engine.Gaus(0.0, m_xy_resolution_mm.value());
      const double digi_d2w_mm = std::max(0.0, distance_to_wire_mm + smear_xy_mm);

      const double drift_time_ns  = get_drift_time_ns(digi_d2w_mm);

      // Smear along-wire position (Gaussian along wire direction)
      const double smear_z_ddu = random_engine.Gaus(0.0, m_z_resolution_mm.value() * dd4hep::mm);
      const TVector3 wire_dir_ez_ddu = (m_dch_info->Calculate_wire_vector_ez(layer, nphi)).Unit();
      proj_on_wire_ddu += smear_z_ddu * wire_dir_ez_ddu;

      // Clamp to physical z-extent
      proj_on_wire_ddu.SetZ(std::clamp(proj_on_wire_ddu.Z(), -m_dch_info->Lhalf, m_dch_info->Lhalf));

      const edm4hep::Vector3d digi_pos_mm = toEDM4hepVector(proj_on_wire_ddu) * (1.0 / dd4hep::mm);

      // Signal travel along wire to readout end: guard cosStereo already applied.
      const double dist_to_readout_mm =
          (m_dch_info->Lhalf / dd4hep::mm - std::abs(digi_pos_mm.z)) / cosStereo;

      const double travel_time_ns = get_signal_travel_time_ns(dist_to_readout_mm);

      // Optional extra time jitter
      const double extra_time_jitter_ns =
          (m_time_resolution_ns.value() > 0.0) ? random_engine.Gaus(0.0, m_time_resolution_ns.value()) : 0.0;

      HitInfo info;
      info.simhit_index        = idx;
      info.arrival_time_ns     = simhit.getTime() + drift_time_ns + travel_time_ns + extra_time_jitter_ns;
      info.position_mm         = digi_pos_mm;
      info.distance_to_wire_mm = digi_d2w_mm;

      hit_info_vector.push_back(info);
    }

    if (hit_info_vector.empty()) continue;

    std::sort(hit_info_vector.begin(), hit_info_vector.end(),
              [](const HitInfo& a, const HitInfo& b){ return a.arrival_time_ns < b.arrival_time_ns; });

    // Build hit trains with configurable semantics
    std::vector<std::vector<HitInfo>> hit_trains;
    hit_trains.reserve(hit_info_vector.size());

    hit_trains.push_back({hit_info_vector.front()});
    for (size_t i = 1; i < hit_info_vector.size(); ++i) {
      const auto& cur = hit_info_vector[i];

      const auto& train = hit_trains.back();
      const double tref = m_deadtimeFromFirstHit.value()
                        ? train.front().arrival_time_ns
                        : train.back().arrival_time_ns;

      if (cur.arrival_time_ns - tref < m_deadtime_ns.value()) {
        hit_trains.back().push_back(cur);
      } else {
        hit_trains.emplace_back(1, cur);
      }
    }

    for (const auto& train : hit_trains) {
      if (train.empty()) continue;

      const double t0 = train.front().arrival_time_ns;

      // Readout window: half-open [start, end)
      if (t0 < tStart || t0 >= tEnd) continue;

      double edep_sum_GeV = 0.0;

      unsigned int total_nclusters = 0;

      if (m_useClusterModel.value()) {
        // Pseudo-physical cluster model (optional): accumulate per-particle beta*gamma and path length
        std::unordered_map<podio::ObjectID, ParticleClusterInfo> cluster_info_map;
        cluster_info_map.reserve(train.size());

        for (const auto& hi : train) {
          const auto& sh = input[hi.simhit_index];
          edep_sum_GeV += sh.getEDep();

          const auto mcp = sh.getParticle();
          const auto oid = mcp.getObjectID();

          auto [it, inserted] = cluster_info_map.try_emplace(oid, ParticleClusterInfo{});
          auto& pci = it->second;

          // Path length accumulation
          if (inserted) {
            const double m = std::max(1e-9, static_cast<double>(mcp.getMass())); // assume GeV
            const double p = edm4hep::utils::magnitude(mcp.getMomentum());       // assume GeV
            const double bg = (m > 0.0) ? (p / m) : 0.0;
            pci.beta_gamma     = std::clamp(bg, 0.1, 20000.0);
            pci.path_length_mm = sh.getPathLength();
          } else {
            pci.path_length_mm += sh.getPathLength();
          }
        }

        // Sample clusters
        for (const auto& kv2 : cluster_info_map) {
          const auto& pci = kv2.second;
          const double n_per_mm = m_delphesTrkUtil.Nclusters(pci.beta_gamma, m_GasType.value()) / 1000.0;
          const double mean     = n_per_mm * pci.path_length_mm;

          // IMPORTANT FIX:
          // Use ordinary Poisson, do NOT force >=1 cluster when mean is tiny.
          total_nclusters += sample_poisson_nonnegative(mean, random_engine);
        }
      } else {
        // Geo-only mode: still sum EDep for bookkeeping, but do not model clusters
        for (const auto& hi : train) {
          const auto& sh = input[hi.simhit_index];
          edep_sum_GeV += sh.getEDep();
        }
        total_nclusters = 0;
      }

      const auto& first = train.front();
      const auto& first_simhit = input[first.simhit_index];

      auto sw = output.create();
      sw.setCellID(cellID);
      sw.setType(0);
      sw.setQuality(0);
      sw.setTime(static_cast<float>(t0));
      sw.setEDep(static_cast<float>(edep_sum_GeV));
      sw.setEDepError(0.0f);
      sw.setPosition(first.position_mm);
      sw.setPositionAlongWireError(m_z_resolution_mm.value());
      sw.setWireAzimuthalAngle(static_cast<float>(WireAzimuthalAngle));
      sw.setWireStereoAngle(WireStereoAngle);
      sw.setDistanceToWire(static_cast<float>(first.distance_to_wire_mm));
      sw.setDistanceToWireError(static_cast<float>(m_xy_resolution_mm.value()));

      // nElectrons is a vector<uint16_t>. Use it as "clusters" with value=1 each.
      // (SenseWireHit::getNClusters() is defined as size of this vector.)
      for (unsigned int i = 0; i < total_nclusters; ++i) {
        sw.addToNElectrons(static_cast<std::uint16_t>(1));
      }

      auto link = links.create();
      link.setFrom(sw);
      link.setTo(first_simhit);
    }
  }

  return std::make_tuple(std::move(output), std::move(links));
}

double DCHdigi_v02::get_drift_time_ns(double distance_to_wire_mm) const {
  const double distance_um = distance_to_wire_mm * 1000.0;
  return distance_um / m_drift_velocity_um_per_ns.value();
}

double DCHdigi_v02::get_signal_travel_time_ns(double distance_to_readout_mm) const {
  return distance_to_readout_mm / m_signal_velocity_mm_per_ns.value();
}

double DCHdigi_v02::get_default_drift_velocity_um_per_ns() const {
  switch (m_GasType.value()) {
    case 0: return 25.0;
    case 1: warning() << "GasType=1 (He) not tuned; using 25 um/ns." << endmsg; return 25.0;
    case 2: warning() << "GasType=2 (Ar-Ethane) not tuned; using 25 um/ns." << endmsg; return 25.0;
    case 3: warning() << "GasType=3 (Ar) not tuned; using 25 um/ns." << endmsg; return 25.0;
    default:
      warning() << "Unknown GasType=" << m_GasType.value()
                << "; using 25 um/ns (He-Iso default)" << endmsg;
      return 25.0;
  }
}
