/*
DOC:
Title: PlotTrackHitDistances (Gaudi Consumer)
Summary:
  Gaudi k4FWCore::Consumer that produces a 1D diagnostic histogram of the closest-approach
  distance between a track helix (built from the TrackState at IP) and truth SimTrackerHits
  belonging to the same MCParticle. Intended primarily as a sanity-check / QA tool.

Primary Use Cases:
  - Smoke-test that TrackState(AtIP) helix parameters (phi, D0, Z0, omega, tanLambda) are
    consistent with the underlying truth trajectory in a constant Bz field.
  - Quick regression check after changes to track-state filling, parameter conventions,
    B-field configuration, or truth-linking/associations.
  - Debugging gross failures (wrong sign conventions, missing AtIP state, wrong Bz) via a
    shifted/broad residual distribution.

Not Intended For:
  - True detector-measurement residuals (wire DOCA/drift-time residuals, pulls, chi2).
  - Precision performance metrics (pT resolution, efficiency/fake rates) by itself.
  - Workflows without truth associations (requires Track<->MCParticle links).

Algorithm Behavior:
  - Iterates over edm4hep::TrackMCParticleLink entries.
  - For each linked track, finds the TrackState with location == edm4hep::TrackState::AtIP.
    If missing, throws a runtime_error and stops the job.
  - Builds a canonical helix (marlinutil::HelixClass_double) from the AtIP parameters and
    constant Bz.
  - Loops over input SimTrackerHits and selects hits whose MCParticle matches the link target.
  - For each matching hit, computes helix distance-to-point and fills a histogram with the
    3D distance component (distances[2]) in mm.

Inputs:
  - InputSimTrackerHits (edm4hep::SimTrackerHitCollection)
      Default: "DCHCollection"
      Description: Truth SimTrackerHits (e.g., from DDG4) used as reference points.
  - InputTracksFromGenParticlesAssociation (edm4hep::TrackMCParticleLinkCollection)
      Default: "TracksFromGenParticlesAssociation"
      Description: Associations linking reconstructed (or gen-seeded) tracks to MCParticles.
      Required: Each associated track must contain a TrackState with location=AtIP.

Outputs:
  - ROOT histogram (Gaudi accumulator):
      Name:  track_hits_distance_closest_approach
      Title: Track-hit Distances
      Binning: 100 bins from 0 to 1 mm
      Quantity: 3D closest-approach distance between helix and SimTrackerHit point [mm]
      Notes: If distances frequently exceed 1 mm, the distribution will saturate at the
             histogram max (values above range are not represented).

Key Properties:
  - Bz (float, Tesla)
      Default: 2.0
      Description: Constant magnetic field Z component used to build the helix.

Assumptions / Requirements:
  - TrackState(AtIP) parameters use a convention compatible with HelixClass_double
    Initialize_Canonical(phi, D0, Z0, omega, tanLambda, Bz) and consistent units.
  - Truth linking is correct: SimTrackerHit.getParticle() matches the MCParticle in the link.
  - Performance note: The naive nested loop is O(N_links * N_hits); consider indexing hits
    by MCParticle if used on large samples.

Failure Modes / Diagnostics:
  - Throws if no TrackState with location=AtIP exists on an associated track.
  - A very broad/flat distribution or heavy saturation at the upper edge often indicates:
      * wrong Bz, wrong parameter conventions/signs, or mismatched truth associations.

Example Usage (Gaudi/python options sketch):
  from Configurables import PlotTrackHitDistances
  alg = PlotTrackHitDistances("PlotTrackHitDistances")
  alg.InputSimTrackerHits = "DCHCollection"
  alg.InputTracksFromGenParticlesAssociation = "TracksFromGenParticlesAssociation"
  alg.Bz = 2.0
  # Add alg to ApplicationMgr.TopAlg

Collections:
  - Consumes: edm4hep::SimTrackerHitCollection   ("DCHCollection" by default)
  - Consumes: edm4hep::TrackMCParticleLinkCollection ("TracksFromGenParticlesAssociation" by default)
  - Produces: Histogram "track_hits_distance_closest_approach" (in output ROOT hist sink)

Tags:
  - QA
  - diagnostics
  - truth-matching
  - helix
DOC_END
*/


// Gaudi
#include "Gaudi/Accumulators/RootHistogram.h"
#include "Gaudi/Histograming/Sink/Utils.h"
#include "Gaudi/Property.h"

// edm4hep
#include "edm4hep/MCParticleCollection.h"
#include "edm4hep/SimTrackerHitCollection.h"
#include "edm4hep/TrackCollection.h"
#include "edm4hep/TrackMCParticleLinkCollection.h"

// marlin
#include <marlinutil/HelixClass_double.h>

// ROOT
#include "TH1D.h"

// k4FWCore
#include "k4FWCore/Consumer.h"

#include "GAUDI_VERSION.h"

#if GAUDI_MAJOR_VERSION < 39
namespace Gaudi::Accumulators {
template <unsigned int ND, atomicity Atomicity = atomicity::full, typename Arithmetic = double>
using StaticHistogram = Gaudi::Accumulators::HistogramingCounterBase<ND, Atomicity, Arithmetic, naming::histogramString,
                                                                     HistogramingAccumulator>;
}
#endif

#include <string>

/** @class PlotTrackHitDistances
 *
 *  Gaudi consumer that generates a residual distribution (mm) by comparing the helix from Track AtIP and simHit
 * position. This is intended to be used on tracks produced from gen particles i.e. which do not have real hits attached
 * to them.
 *
 *  @author Brieuc Francois
 */

struct PlotTrackHitDistances final
    : k4FWCore::Consumer<void(const edm4hep::SimTrackerHitCollection&, const edm4hep::TrackMCParticleLinkCollection&)> {
  PlotTrackHitDistances(const std::string& name, ISvcLocator* svcLoc)
      : Consumer(name, svcLoc,
                 {
                     KeyValues("InputSimTrackerHits", {"DCHCollection"}),
                     KeyValues("InputTracksFromGenParticlesAssociation", {"TracksFromGenParticlesAssociation"}),
                 }) {}

  void operator()(const edm4hep::SimTrackerHitCollection& simTrackerHits,
                  const edm4hep::TrackMCParticleLinkCollection& trackParticleAssociations) const override {

    for (const auto& trackParticleAssociation : trackParticleAssociations) {
      auto genParticle = trackParticleAssociation.getTo();
      auto track = trackParticleAssociation.getFrom();
      edm4hep::TrackState trackStateAtIP;
      bool found_trackStateAtIP = false;
      for (const auto& trackState : track.getTrackStates()) {
        if (trackState.location == edm4hep::TrackState::AtIP) {
          trackStateAtIP = trackState;
          found_trackStateAtIP = true;
          break;
        }
      }
      if (!found_trackStateAtIP)
        throw std::runtime_error("No track state defined AtIP, exiting!");

      // Build an helix out of the trackState
      auto helixFromTrack = HelixClass_double();
      helixFromTrack.Initialize_Canonical(trackStateAtIP.phi, trackStateAtIP.D0, trackStateAtIP.Z0,
                                          trackStateAtIP.omega, trackStateAtIP.tanLambda, m_Bz);

      // Fill the histogram with residuals for hits attached to the same gen particle
      for (const auto& simTrackerHit : simTrackerHits) {
        auto simTrackerHitgenParticle = simTrackerHit.getParticle();
        if (simTrackerHitgenParticle.getObjectID() == genParticle.getObjectID()) {
          double simTrackerHitPosition[] = {simTrackerHit.x(), simTrackerHit.y(), simTrackerHit.z()};
          double distances[3];
          helixFromTrack.getDistanceToPoint(simTrackerHitPosition, distances);
          // Distance[0] - distance in R-Phi plane, Distance[1] - distance along Z axis, Distance[2] - 3D distance
          ++m_residualHist[distances[2]];
        }
      }
    }
    return;
  }
  Gaudi::Property<float> m_Bz{this, "Bz", 2., "Z component of the (assumed constant) magnetic field in Tesla."};
  mutable Gaudi::Accumulators::StaticHistogram<1> m_residualHist{
      this, "track_hits_distance_closest_approach", "Track-hit Distances", {100, 0, 1, "Distance [mm];Entries"}};
};

DECLARE_COMPONENT(PlotTrackHitDistances)
