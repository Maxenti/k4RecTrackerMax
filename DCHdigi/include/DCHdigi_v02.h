#pragma once

// STL
#include <string>
#include <cmath>
#include <tuple>

// Gaudi
#include "Gaudi/Accumulators.h"
#include <GaudiKernel/ISvcLocator.h>
#include <GaudiKernel/SmartIF.h>

// k4FWCore
#include "k4FWCore/Transformer.h"
#include "k4FWCore/MetaDataHandle.h"

// k4Interface
#include <k4Interface/IGeoSvc.h>
#include <k4Interface/IUniqueIDGenSvc.h>

// edm4hep
#include "edm4hep/EventHeaderCollection.h"
#include "edm4hep/SimTrackerHitCollection.h"

// extension types
#include "extension/SenseWireHitCollection.h"
#include "extension/SenseWireHitSimTrackerHitLinkCollection.h"

// DD4hep
#include "DDSegmentation/BitFieldCoder.h"

// DDRec
#include "DDRec/DCH_info.h"

// delphes
#include "TrackCovariance/TrkUtil.h"

// ROOT
#include "TRandom3.h"
#include "TVector3.h"

// podio
#include "podio/GenericParameters.h"

class DCHdigi_v02 final
    : public k4FWCore::MultiTransformer<
          std::tuple<
              extension::SenseWireHitCollection,
              extension::SenseWireHitSimTrackerHitLinkCollection>(
              const edm4hep::SimTrackerHitCollection&,
              const edm4hep::EventHeaderCollection&)> {

public:
  DCHdigi_v02(const std::string& name, ISvcLocator* svcLoc);

  std::tuple<
      extension::SenseWireHitCollection,
      extension::SenseWireHitSimTrackerHitLinkCollection>
  operator()(const edm4hep::SimTrackerHitCollection& input,
             const edm4hep::EventHeaderCollection& header) const override;

  StatusCode initialize() override final;

private:
  SmartIF<IUniqueIDGenSvc> m_uniqueIDSvc{nullptr};
  Gaudi::Property<std::string> m_uidSvcName{
      this, "uidSvcName", "UniqueIDGenSvc",
      "The name of the UniqueIDGenSvc instance"};

  SmartIF<IGeoSvc> m_geoSvc{nullptr};
  Gaudi::Property<std::string> m_geoSvcName{
      this, "GeoSvcName", "GeoSvc",
      "The name of the GeoSvc instance"};

  mutable Gaudi::Accumulators::Counter<
      Gaudi::Accumulators::atomicity::full, unsigned int> m_event_counter;

  TrkUtil m_delphesTrkUtil;

  dd4hep::DDSegmentation::BitFieldCoder* m_decoder{nullptr};

  // Detector name
  Gaudi::Property<std::string> m_dch_name{
      this, "DCH_name", "DCH_v2",
      "Name of the Drift Chamber detector"};

  // Drift chamber info extension for geometry calculations
  dd4hep::rec::DCH_info* m_dch_info{nullptr};

  // z resolution in mm
  Gaudi::Property<double> m_z_resolution_mm{
      this, "zResolution_mm", 1.0,
      "Spatial resolution along the wire, in mm."};

  // xy resolution in mm
  Gaudi::Property<double> m_xy_resolution_mm{
      this, "xyResolution_mm", 0.1,
      "Spatial resolution perpendicular to the wire, in mm."};

  // Optional extra time jitter (geo-focused knob)
  Gaudi::Property<double> m_time_resolution_ns{
      this, "timeResolution_ns", 0.0,
      "Additional Gaussian time jitter applied to hit time [ns]. (0 disables)"};

  // Deadtime of a cell in ns
  Gaudi::Property<double> m_deadtime_ns{
      this, "Deadtime_ns", 400.0, "Deadtime of a cell in ns."};

  // If true, a train includes hits within deadtime of the FIRST hit (true deadtime model).
  // If false, uses the original 'chain' model (each hit within deadtime of previous).
  Gaudi::Property<bool> m_deadtimeFromFirstHit{
      this, "DeadtimeFromFirstHit", true,
      "If true: group hits into a train if (t - t0) < deadtime. If false: compare to previous hit."};

  // Gas drift velocity in um/ns
  Gaudi::Property<double> m_drift_velocity_um_per_ns{
      this, "DriftVelocity_um_per_ns", -1.0,
      "Gas drift velocity in um/ns. If negative, auto-chosen based on GasType."};

  // Signal velocity in the wire in mm/ns
  // c = 299.792458 mm/ns; (2/3)*c = 199.86163866666667 mm/ns
  Gaudi::Property<double> m_signal_velocity_mm_per_ns{
      this, "SignalVelocity_mm_per_ns",
      199.86163866666667,
      "Signal velocity in the wire in mm/ns (default = (2/3)*c)."};

  // Guard against cos(stereo) ~ 0
  Gaudi::Property<double> m_minAbsCosStereo{
      this, "MinAbsCosStereo", 1e-3,
      "Minimum |cos(stereoAngle)| allowed to compute readout distance. Below -> skip."};

  // Gas mixture
  Gaudi::Property<int> m_GasType{
      this, "GasType", {0},
      "0: He(90%)-Isobutane(10%), 1: pure He, 2: Ar(50%)-Ethane(50%), 3: pure Ar."};

  // Cluster model (pseudo-physical) toggle
  Gaudi::Property<bool> m_useClusterModel{
      this, "UseClusterModel", false,
      "If true, estimate clusters from beta*gamma and path length. If false, store zero clusters (geo-only digitizer)."};

  // Readout window
  Gaudi::Property<double> m_ReadoutWindowStartTime_ns{
      this, "ReadoutWindowStartTime_ns", 1.0,
      "Start time of readout window (ns)."};

  Gaudi::Property<double> m_ReadoutWindowDuration_ns{
      this, "ReadoutWindowDuration_ns", 450.0,
      "Duration of readout window (ns)."};

  // Optional freeform tag (e.g. input file name, job label)
  Gaudi::Property<std::string> m_jobTag{
      this, "JobTag", "",
      "Optional external tag (e.g. input file name or run label)"};

  // Metadata handle
  k4FWCore::MetaDataHandle<std::string> m_digiMeta;

  /// Convert EDM4hep Vector3d to TVector3
  TVector3 toTVector3(const edm4hep::Vector3d& v) const { return {v[0], v[1], v[2]}; }
  /// Convert TVector3 to EDM4hep Vector3d
  edm4hep::Vector3d toEDM4hepVector(const TVector3& v) const { return {v.X(), v.Y(), v.Z()}; }

  // Sampling helpers
  inline unsigned sample_poisson_nonnegative(double mean, TRandom3& gen) const {
    if (!(mean > 0.0) || !std::isfinite(mean)) return 0u;
    return static_cast<unsigned>(gen.Poisson(mean));
  }

  double get_drift_time_ns(double distance_to_wire_mm) const;
  double get_signal_travel_time_ns(double distance_to_readout_mm) const;
  double get_default_drift_velocity_um_per_ns() const;
};

DECLARE_COMPONENT(DCHdigi_v02);
