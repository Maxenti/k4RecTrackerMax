# components

This README is auto-generated from per-file `DOC:` blocks (preferred) plus heuristics.
Improve accuracy by adding a `DOC:` header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `DCHLooperEventFilter.cpp` | include "GaudiKernel/Algorithm.h" |  |  | gaudi:declares_component<br>gaudi:topalg:DCHCollection<br>include:Gaudi/Property.h<br>include:GaudiKernel/Algorithm.h<br>include:algorithm<br>include:edm4hep/SimTrackerHitCollection.h<br>include:k4FWCore/DataHandle.h<br>include:limits |
| ⚠️ `fit_ggtf_tracks.cpp` | fit_ggtf_tracks.cpp — Podio Frames (ROOTReader) backend |  |  | gaudi:topalg:CDCHTracks<br>include:TFile.h<br>include:TH1F.h<br>include:TTree.h<br>include:algorithm<br>include:array<br>include:cmath<br>include:extension/TrackCollection.h<br>include:extension/TrackerHit.h<br>include:iostream |
| ⚠️ `GenFit2DCHFitter.cpp` | ====================================================================== |  |  | gaudi:declares_component<br>gaudi:topalg:DiagEveryNTracks<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:MinFittedPointsWithFI<br>gaudi:topalg:MinHitsPerTrack<br>gaudi:topalg:MinMeasurementsToFit<br>gaudi:topalg:OutputTracksGGTF<br>gaudi:topalg:PreFitOutlierVeto<br>gaudi:topalg:UseKFPreFit<br>gaudi:topalg:inputTracks |
| ⚠️ `GGTF_tracking.cpp` | ====================================================================== |  |  | gaudi:declares_component<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:DchName<br>gaudi:topalg:GGTF_trackingConfig<br>gaudi:topalg:OutputTracksGGTF<br>include:ATen/ATen.h<br>include:DD4hep/Detector.h<br>include:DDSegmentation/BitFieldCoder.h<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h |
| ⚠️ `PlotTrackHitResiduals.cpp` | Gaudi |  |  | gaudi:declares_component<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:InputSimTrackerHits<br>gaudi:topalg:InputTracksFromGenParticlesAssociation<br>gaudi:topalg:TracksFromGenParticlesAssociation<br>gaudi:topalg:track_hits_distance_closest_approach<br>include:GAUDI_VERSION.h<br>include:Gaudi/Accumulators/RootHistogram.h<br>include:Gaudi/Histograming/Sink/Utils.h<br>include:Gaudi/Property.h |
| ⚠️ `SimpleFitDCHFitter.cpp` | ====================================================================== |  |  | gaudi:declares_component<br>gaudi:topalg:SimpleTracks<br>gaudi:topalg:nTracksPerEvent<br>gaudi:topalg:outputTracks<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h<br>include:GaudiKernel/ISvcLocator.h<br>include:GaudiKernel/ITHistSvc.h<br>include:GaudiKernel/ServiceHandle.h<br>include:TGeoManager.h |
| ⚠️ `ThreePointFitter.cpp` | ====================================================================== |  |  | gaudi:declares_component<br>gaudi:topalg:FitTanLambda<br>gaudi:topalg:ThreePointTracks<br>gaudi:topalg:outputTracks<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h<br>include:GaudiKernel/ISvcLocator.h<br>include:TVector3.h<br>include:algorithm<br>include:cmath |
| ⚠️ `TrackdNdxDelphesBased.cpp` | include "TrackdNdxDelphesBased.h" |  |  | gaudi:declares_component<br>gaudi:topalg:TrackMCParticleLinks<br>include:DD4hep/DD4hepUnits.h<br>include:DD4hep/Detector.h<br>include:GaudiKernel/MsgStream.h<br>include:TVectorD.h<br>include:TrackdNdxDelphesBased.h<br>include:edm4hep/Quantity.h<br>include:edm4hep/utils/vector_utils.h<br>include:limits |
| ⚠️ `TrackdNdxDelphesBased.h` | pragma once |  |  | gaudi:topalg:DCH_gas_Lhalf<br>gaudi:topalg:DCH_gas_inner_cyl_R<br>gaudi:topalg:DCH_gas_outer_cyl_R<br>include:GaudiKernel/ISvcLocator.h<br>include:GaudiKernel/SmartIF.h<br>include:TrackCovariance/TrkUtil.h<br>include:edm4hep/EventHeaderCollection.h<br>include:edm4hep/RecDqdxCollection.h<br>include:edm4hep/TrackMCParticleLinkCollection.h<br>include:k4FWCore/Transformer.h |
| ⚠️ `TracksFromGenParticles.cpp` | include "Gaudi/Property.h" |  |  | gaudi:declares_component<br>gaudi:topalg:InputSimTrackerHits<br>gaudi:topalg:OutputMCRecoTrackParticleAssociation<br>gaudi:topalg:OutputTracks<br>gaudi:topalg:SimTrackerHits<br>gaudi:topalg:TrackerIDs<br>gaudi:topalg:TracksFromGenParticles<br>gaudi:topalg:TracksFromGenParticlesAssociation<br>include:DD4hep/DD4hepUnits.h<br>include:DD4hep/DetType.h |
