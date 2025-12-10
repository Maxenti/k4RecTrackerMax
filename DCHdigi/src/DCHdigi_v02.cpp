#include "DCHdigi_v02.h"

// Gaudi
#include <GaudiKernel/MsgStream.h>

// edm4hep
#include "edm4hep/utils/vector_utils.h"

// DD4hep
#include "DD4hep/Detector.h"

// k4FWCore
#include "k4FWCore/MetaDataHandle.h"   // NEW

// STL
#include <algorithm>
#include <unordered_map>
#include <sstream>                      // NEW

namespace {

struct ParticleClusterInfo {
  double beta_gamma     = 0.0;
  double path_length_mm = 0.0;
};

struct HitInfo {
  const edm4hep::SimTrackerHit* simhit{nullptr};
  double       arrival_time_ns    = 0.0;
  edm4hep::Vector3d position_mm   {};
  double       distance_to_wire_mm = 0.0;
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
    m_digiMeta("DCHdigi_v02Config", Gaudi::DataHandle::Writer)  // NEW
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

  m_event_counter.reset();

  // ---------------------------
  // Write configuration metadata
  // ---------------------------
  try {
    std::ostringstream os;
    os << "{";
    os << "\"component\":\"DCHdigi_v02\"";
    os << ",\"DCH_name\":\"" << m_dch_name.value() << "\"";
    os << ",\"GasType\":" << m_GasType.value();
    os << ",\"xyResolution_mm\":" << m_xy_resolution_mm.value();
    os << ",\"zResolution_mm\":" << m_z_resolution_mm.value();
    os << ",\"Deadtime_ns\":" << m_deadtime_ns.value();
    os << ",\"DriftVelocity_um_per_ns\":" << m_drift_velocity_um_per_ns.value();
    os << ",\"SignalVelocity_mm_per_ns\":" << m_signal_velocity_mm_per_ns.value();
    os << ",\"ReadoutWindowStart_ns\":" << m_ReadoutWindowStartTime_ns.value();
    os << ",\"ReadoutWindowDuration_ns\":" << m_ReadoutWindowDuration_ns.value();

    // Optional external tag (e.g. input file name) – can be set from Python
    if (!m_jobTag.value().empty()) {
      os << ",\"JobTag\":\"" << m_jobTag.value() << "\"";
    }

    os << "}";

    const std::string payload = os.str();
    m_digiMeta.put(payload);
    info() << "DCHdigi_v02 metadata written: " << payload << endmsg;
  } catch (const std::exception& e) {
    warning() << "Failed to write DCHdigi_v02 metadata: " << e.what() << endmsg;
  }

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
  debug() << "SimTrackerHitCollection size = " << input.size() << endmsg;

  std::unordered_map<uint64_t, std::vector<edm4hep::SimTrackerHit>> cell_map;
  cell_map.reserve(input.size());

  for (const auto& simhit : input) {
    cell_map[simhit.getCellID()].push_back(simhit);
  }

  debug() << "Unique cellIDs = " << cell_map.size() << endmsg;

  // Loop over cells
  for (const auto& [cellID, simhits] : cell_map) {

    // Geometry bits
    const int layer = m_dch_info->CalculateILayerFromCellIDFields(
        m_decoder->get(cellID, "layer"),
        m_decoder->get(cellID, "superlayer"));
    const int nphi = m_decoder->get(cellID, "nphi");

    // Angles (copied from v01)
    const auto WireAzimuthalAngle = m_dch_info->Get_cell_phi_angle(layer, nphi);
    float WireStereoAngle = 0.f;
    {
      auto l = m_dch_info->database.at(layer);
      const auto cell_rave_z0 = 0.5 * (l.radius_fdw_z0 + l.radius_fuw_z0);
      WireStereoAngle = (-1.f) * l.StereoSign() * m_dch_info->stereoangle_z0(cell_rave_z0);
    }

    // Collect hit infos (position/time/distance)
    std::vector<HitInfo> hit_info_vector;
    hit_info_vector.reserve(simhits.size());

    for (const auto& simhit : simhits) {
      // Position → TVector3 in dd4hep units
      const auto pos_ddu = toTVector3(simhit.getPosition()) * dd4hep::mm;

      const auto hit_to_wire_vec_ddu       = m_dch_info->Calculate_hitpos_to_wire_vector(layer, nphi, pos_ddu);
      auto       proj_on_wire_ddu          = pos_ddu + hit_to_wire_vec_ddu;
      const double distance_to_wire_mm     = hit_to_wire_vec_ddu.Mag() / dd4hep::mm;

      // XY smearing
      const double smear_xy_mm = random_engine.Gaus(0.0, m_xy_resolution_mm.value());
      const double digi_d2w_mm = std::max(0.0, distance_to_wire_mm + smear_xy_mm);
      const double drift_time  = get_drift_time_ns(digi_d2w_mm);

      // Z smearing along wire
      const double smear_z_ddu = random_engine.Gaus(0.0, m_z_resolution_mm.value() * dd4hep::mm);
      const TVector3 wire_dir_ez_ddu = (m_dch_info->Calculate_wire_vector_ez(layer, nphi)).Unit();
      proj_on_wire_ddu += smear_z_ddu * wire_dir_ez_ddu;

      // Limit |z| inside chamber
      proj_on_wire_ddu.SetZ(std::clamp(proj_on_wire_ddu.Z(), -m_dch_info->Lhalf, m_dch_info->Lhalf));

      // Back to mm
      const edm4hep::Vector3d digi_pos_mm = toEDM4hepVector(proj_on_wire_ddu) * (1.0 / dd4hep::mm);

      // Time to readout
      const double dist_to_readout_mm =
          (m_dch_info->Lhalf / dd4hep::mm - std::abs(digi_pos_mm.z)) / std::cos(WireStereoAngle);
      const double travel_time = get_signal_travel_time_ns(dist_to_readout_mm);

      HitInfo info;
      info.simhit             = &simhits.front() + (&simhit - &simhits.front()); // address-safe
      info.arrival_time_ns    = simhit.getTime() + drift_time + travel_time;
      info.position_mm        = digi_pos_mm;
      info.distance_to_wire_mm= digi_d2w_mm;

      hit_info_vector.push_back(info);
    }

    // Sort by time (C++17)
    std::sort(hit_info_vector.begin(), hit_info_vector.end(),
              [](const HitInfo& a, const HitInfo& b){ return a.arrival_time_ns < b.arrival_time_ns; });

    // Build trains separated by Deadtime
    std::vector<std::vector<HitInfo>> hit_trains;
    hit_trains.reserve(hit_info_vector.size());
    if (!hit_info_vector.empty()) {
      hit_trains.push_back({hit_info_vector.front()});
      for (size_t i = 1; i < hit_info_vector.size(); ++i) {
        const auto& cur  = hit_info_vector[i];
        const auto& last = hit_trains.back().back();
        if (cur.arrival_time_ns - last.arrival_time_ns < m_deadtime_ns.value()) {
          hit_trains.back().push_back(cur);
        } else {
          hit_trains.emplace_back(1, cur);
        }
      }
    }

    // Emit one digi per train
    for (const auto& train : hit_trains) {
      if (train.empty()) continue;

      const double t0 = train.front().arrival_time_ns;
      if (t0 < m_ReadoutWindowStartTime_ns.value() ||
          t0 > m_ReadoutWindowStartTime_ns.value() + m_ReadoutWindowDuration_ns.value()) {
        continue;
      }

      // Sum Edep
      double edep_sum_GeV = 0.0;

      // Per-particle cluster info
      std::unordered_map<podio::ObjectID, ParticleClusterInfo> cluster_info_map;
      cluster_info_map.reserve(train.size());

      for (const auto& hi : train) {
        const auto& sh = *hi.simhit;
        edep_sum_GeV += sh.getEDep();

        const auto mcp = sh.getParticle();
        const auto oid = mcp.getObjectID();

        auto [it, inserted] = cluster_info_map.try_emplace(oid, ParticleClusterInfo{});
        auto& pci = it->second;
        if (inserted) {
          double m = mcp.getMass();
          double p = edm4hep::utils::magnitude(mcp.getMomentum());
          if (m < 1e-9 * dd4hep::GeV) m = 0.000511; // fallback: electron mass
          pci.beta_gamma     = std::clamp(p / m, 0.5, 20000.0);
          pci.path_length_mm = sh.getPathLength();
        } else {
          pci.path_length_mm += sh.getPathLength();
        }
      }

      // Total clusters
      unsigned int total_nclusters = 0;
      for (const auto& kv : cluster_info_map) {
        const auto& pci = kv.second;
        const double n_per_mm = m_delphesTrkUtil.Nclusters(pci.beta_gamma, m_GasType.value()) / 1000.0;
        const double mean     = n_per_mm * pci.path_length_mm;
        total_nclusters      += sample_zero_truncated_poisson(mean, random_engine);
      }

      // Create digi from first hit in train
      const auto& first = train.front();

      auto sw = output.create();
      sw.setCellID(cellID);
      sw.setType(0);
      sw.setQuality(0);
      sw.setTime(t0);
      sw.setEDep(edep_sum_GeV);
      sw.setEDepError(0.0);
      sw.setPosition(first.position_mm);
      sw.setPositionAlongWireError(m_z_resolution_mm.value());
      sw.setWireAzimuthalAngle(WireAzimuthalAngle);
      sw.setWireStereoAngle(WireStereoAngle);
      sw.setDistanceToWire(first.distance_to_wire_mm);
      sw.setDistanceToWireError(m_xy_resolution_mm.value());
      for (unsigned int i = 0; i < total_nclusters; ++i) sw.addToNElectrons(-1);

      // Link: SenseWireHit ↔ SimTrackerHit
      auto link = links.create();
      link.setFrom(sw);                // OK: link type is SenseWireHitSimTrackerHitLink
      link.setTo(*first.simhit);
    }
  }

  return std::make_tuple(std::move(output), std::move(links));
}

double DCHdigi_v02::get_drift_time_ns(double distance_to_wire_mm) const {
  // simple linear model
  const double distance_um = distance_to_wire_mm * 1000.0;
  return distance_um / m_drift_velocity_um_per_ns.value();
}

double DCHdigi_v02::get_signal_travel_time_ns(double distance_to_readout_mm) const {
  return distance_to_readout_mm / m_signal_velocity_mm_per_ns.value();
}

double DCHdigi_v02::get_default_drift_velocity_um_per_ns() const {
  switch (m_GasType.value()) {
    case 0: return 25.0; // He-Isobutane(90/10)
    case 1: warning() << "GasType=1 (He) not tuned; using 25 um/ns." << endmsg; return 25.0;
    case 2: warning() << "GasType=2 (Ar-Ethane) not tuned; using 25 um/ns." << endmsg; return 25.0;
    case 3: warning() << "GasType=3 (Ar) not tuned; using 25 um/ns." << endmsg; return 25.0;
    default:
      warning() << "Unknown GasType=" << m_GasType.value()
                << "; using 25 um/ns (He-Iso default)" << endmsg;
      return 25.0;
  }
}
