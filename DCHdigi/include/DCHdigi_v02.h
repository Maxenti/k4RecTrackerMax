#pragma once

// STL
#include <string>  // NEW

// Gaudi
#include "Gaudi/Accumulators.h"
#include <GaudiKernel/ISvcLocator.h>
#include <GaudiKernel/SmartIF.h>

// k4FWCore
#include "k4FWCore/Transformer.h"
#include "k4FWCore/MetaDataHandle.h"   // NEW

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

  // Fast zero-truncated Poisson sampler
  inline int sample_zero_truncated_poisson(double lambda, TRandom3& gen) const {
    double u = gen.Uniform(std::exp(-lambda), 1.0);
    double t = -std::log(u);
    int k = gen.Poisson(lambda - t);
    return 1 + k;
  }

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
      "Spatial resolution in the direction along the wire, in mm."};

  // xy resolution in mm
  Gaudi::Property<double> m_xy_resolution_mm{
      this, "xyResolution_mm", 0.1,
      "Spatial resolution in the direction perpendicular to the wire, in mm."};

  // Deadtime of a cell in ns
  Gaudi::Property<double> m_deadtime_ns{
      this, "Deadtime_ns", 400.0, "Deadtime of a cell in ns."};

  // Gas drift velocity in um/ns
  Gaudi::Property<double> m_drift_velocity_um_per_ns{
      this, "DriftVelocity_um_per_ns", -1.0,
      "Gas drift velocity in um/ns. If negative, automatically chosen based on GasType."};

  // Signal velocity in the wire in mm/ns
  Gaudi::Property<double> m_signal_velocity_mm_per_ns{
      this, "SignalVelocity_mm_per_ns",
      TMath::C() * 1e-6 * 2.0 / 3.0, // 2/3 c in mm/ns
      "Signal velocity in the wire in mm/ns."};

  // Gas mixture
  Gaudi::Property<int> m_GasType{
      this, "GasType", {0},
      "0: He(90%)-Isobutane(10%), 1: pure He, 2: Ar(50%)-Ethane(50%), 3: pure Ar."};

  // Readout window
  Gaudi::Property<double> m_ReadoutWindowStartTime_ns{
      this, "ReadoutWindowStartTime_ns", 1.0,
      "Start time of readout window (ns)."};

  Gaudi::Property<double> m_ReadoutWindowDuration_ns{
      this, "ReadoutWindowDuration_ns", 450.0,
      "Duration of readout window (ns)."};

  // --------- NEW: metadata + external tag ---------

  // Optional freeform tag (e.g. input file name, job label)
  Gaudi::Property<std::string> m_jobTag{
      this, "JobTag", "",
      "Optional external tag (e.g. input file name or run label)"};

  // Metadata handle: writes a JSON-ish config blob once per file
  k4FWCore::MetaDataHandle<std::string> m_digiMeta;

  /// Convert EDM4hep Vector3d to TVector3
  TVector3 toTVector3(const edm4hep::Vector3d& v) const { return {v[0], v[1], v[2]}; };
  /// Convert TVector3 to EDM4hep Vector3d
  edm4hep::Vector3d toEDM4hepVector(const TVector3& v) const { return {v.X(), v.Y(), v.Z()}; };

  double get_drift_time_ns(double distance_to_wire_mm) const;
  double get_signal_travel_time_ns(double distance_to_readout_mm) const;
  double get_default_drift_velocity_um_per_ns() const;
};

DECLARE_COMPONENT(DCHdigi_v02);
