# components

This README is auto-generated from per-file DOC blocks (preferred) plus heuristics.
Improve accuracy by adding a DOC header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

Accepted DOC start markers include `DOC`, `DOC:`, `DOC_START`, `DOC_BEGIN` (and similar); end markers include `DOC_END`, `END_DOC` (and similar).

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `DCHLooperEventFilter.cpp` | include "GaudiKernel/Algorithm.h" |  |  | gaudi:declares_component<br>gaudi:topalg:DCHCollection<br>include:Gaudi/Property.h<br>include:GaudiKernel/Algorithm.h<br>include:algorithm<br>include:edm4hep/SimTrackerHitCollection.h<br>include:k4FWCore/DataHandle.h<br>include:limits |
| ⚠️ `fit_ggtf_tracks.cpp` | fit_ggtf_tracks.cpp — Podio Frames (ROOTReader) backend |  |  | gaudi:topalg:CDCHTracks<br>include:TFile.h<br>include:TH1F.h<br>include:TTree.h<br>include:algorithm<br>include:array<br>include:cmath<br>include:extension/TrackCollection.h<br>include:extension/TrackerHit.h<br>include:iostream |
| ✅ `GenFit2DCHFitter.cpp` | Gaudi/k4FWCore Transformer that fits IDEA drift-chamber GGTF track candidates using GenFit2 wire measurements (WireMeasurementNew), producing physics-clean EDM4hep TrackStates at the IP with robust publish-state selection, observability gating, optional TGeo material effects, and per-event robust pT summary metadata. | - As a Gaudi component in a k4run job (Key4HEP / k4RecTracker):<br>from Configurables import GenFit2DCHFitter<br>fitter = GenFit2DCHFitter( |  | gaudi:declares_component<br>gaudi:topalg:DiagEveryNTracks<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:MinFittedPointsWithFI<br>gaudi:topalg:MinHitsPerTrack<br>gaudi:topalg:MinMeasurementsToFit<br>gaudi:topalg:OutputTracksGGTF<br>gaudi:topalg:PreFitOutlierVeto<br>gaudi:topalg:UseKFPreFit<br>gaudi:topalg:inputTracks |
| ⚠️ `GGTF_tracking.cpp` | ====================================================================== |  |  | gaudi:declares_component<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:DchName<br>gaudi:topalg:GGTF_trackingConfig<br>gaudi:topalg:OutputTracksGGTF<br>include:ATen/ATen.h<br>include:DD4hep/Detector.h<br>include:DDSegmentation/BitFieldCoder.h<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h |
| ⚠️ `PlotTrackHitResiduals.cpp` | Gaudi |  |  | gaudi:declares_component<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:InputSimTrackerHits<br>gaudi:topalg:InputTracksFromGenParticlesAssociation<br>gaudi:topalg:TracksFromGenParticlesAssociation<br>gaudi:topalg:track_hits_distance_closest_approach<br>include:GAUDI_VERSION.h<br>include:Gaudi/Accumulators/RootHistogram.h<br>include:Gaudi/Histograming/Sink/Utils.h<br>include:Gaudi/Property.h |
| ⚠️ `SimpleFitDCHFitter.cpp` | ====================================================================== |  |  | gaudi:declares_component<br>gaudi:topalg:SimpleTracks<br>gaudi:topalg:nTracksPerEvent<br>gaudi:topalg:outputTracks<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h<br>include:GaudiKernel/ISvcLocator.h<br>include:GaudiKernel/ITHistSvc.h<br>include:GaudiKernel/ServiceHandle.h<br>include:TGeoManager.h |
| ⚠️ `ThreePointFitter.cpp` | ====================================================================== |  |  | gaudi:declares_component<br>gaudi:topalg:FitTanLambda<br>gaudi:topalg:ThreePointTracks<br>gaudi:topalg:outputTracks<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h<br>include:GaudiKernel/ISvcLocator.h<br>include:TVector3.h<br>include:algorithm<br>include:cmath |
| ⚠️ `TrackdNdxDelphesBased.cpp` | include "TrackdNdxDelphesBased.h" |  |  | gaudi:declares_component<br>gaudi:topalg:TrackMCParticleLinks<br>include:DD4hep/DD4hepUnits.h<br>include:DD4hep/Detector.h<br>include:GaudiKernel/MsgStream.h<br>include:TVectorD.h<br>include:TrackdNdxDelphesBased.h<br>include:edm4hep/Quantity.h<br>include:edm4hep/utils/vector_utils.h<br>include:limits |
| ⚠️ `TrackdNdxDelphesBased.h` | pragma once |  |  | gaudi:topalg:DCH_gas_Lhalf<br>gaudi:topalg:DCH_gas_inner_cyl_R<br>gaudi:topalg:DCH_gas_outer_cyl_R<br>include:GaudiKernel/ISvcLocator.h<br>include:GaudiKernel/SmartIF.h<br>include:TrackCovariance/TrkUtil.h<br>include:edm4hep/EventHeaderCollection.h<br>include:edm4hep/RecDqdxCollection.h<br>include:edm4hep/TrackMCParticleLinkCollection.h<br>include:k4FWCore/Transformer.h |
| ⚠️ `TracksFromGenParticles.cpp` | include "Gaudi/Property.h" |  |  | gaudi:declares_component<br>gaudi:topalg:InputSimTrackerHits<br>gaudi:topalg:OutputMCRecoTrackParticleAssociation<br>gaudi:topalg:OutputTracks<br>gaudi:topalg:SimTrackerHits<br>gaudi:topalg:TrackerIDs<br>gaudi:topalg:TracksFromGenParticles<br>gaudi:topalg:TracksFromGenParticlesAssociation<br>include:DD4hep/DD4hepUnits.h<br>include:DD4hep/DetType.h |

## Details

### `DCHLooperEventFilter.cpp`
- **Arguments / Properties (inferred):**
  - TmaxNs (double) default=450.0 (member=m_tmaxNs)
  - NHitsMax (int) default=30000 (member=m_nHitsMax)
  - KeepEmpty (bool) default=false (member=m_keepEmpty)

### `GenFit2DCHFitter.cpp`
- **Inputs:** - EDM4hep/extension TrackCollection: GGTF-produced track candidates (default: "OutputTracksGGTF").
- **Outputs:** - EDM4hep/extension TrackCollection: fitted tracks (default: "GenFitTracks").
- **Collections:** - inputTracks (vector<string>): default ["OutputTracksGGTF"] - outputTracks (vector<string>): default ["GenFitTracks"] - Metadata keys (k4FWCore::MetaDataHandle<string>): * "cfgMeta" (Writer) : job-level JSON config snapshot * "evtMeta" (Writer) : event-level JSON summary + robust pT stats
- **Arguments / Properties (inferred):**
  - RejectNegativeLabels (bool) default=true (member=m_rejectNegativeLabels)
  - MinHitsPerTrack (unsigned) default=8u (member=m_minHitsPerTrack)
  - MinMeasurementsToFit (unsigned) default=6u (member=m_minMeasurementsToFit)
  - MinFittedPointsWithFI (unsigned) default=10u (member=m_minFittedPointsWithFI)
  - SortHits (bool) default=true (member=m_sortHits)
  - DeduplicateHits (bool) default=true (member=m_dedupHits)
  - DedupTolMM (double) default=0.05 (member=m_dedupTolMM)
  - PreFitOutlierVeto (bool) default=true (member=m_prefitOutlierVeto)
  - OutlierMaxDrop (unsigned) default=2u (member=m_outlierMaxDrop)
  - OutlierCircleResidualMM (double) default=8.0 (member=m_outlierCircleResMM)
  - OutlierChordResidualMM (double) default=20.0 (member=m_outlierChordResMM)
  - OutlierMinKeep (unsigned) default=10u (member=m_outlierMinKeep)
  - SeedEndpointK (unsigned) default=6u (member=m_seedEndpointK)
  - SeedTangentK (unsigned) default=10u (member=m_seedTangentK)
  - UseKFPreFit (bool) default=true (member=m_useKFPreFit)
  - UseDAF (bool) default=true (member=m_useDAF)
  - FallbackToKFIfDAFFails (bool) default=true (member=m_fallbackToKFIfDAFFails)
  - KFMaxIters (unsigned) default=12u (member=m_kfMaxIterations)
  - DAFMaxIters (unsigned) default=8u (member=m_dafMaxIterations)
  - TryBothMomentumDirections (bool) default=true (member=m_tryBothMomDirs)
  - Bz (double) default=2.0 : Bz field [T]
  - PDG (int) default=13 : PDG hypothesis.
  - UseBiasedStateForPublish (bool) default=true (member=m_useBiasedStateForPublish)
  - PublishStateCentralFrac (double) default=0.60 (member=m_publishStateCentralFrac)
  - UseMaterialEffects (bool) default=true (member=m_useMatEff)

### `GGTF_tracking.cpp`
- **Arguments / Properties (inferred):**
  - ModelPath (std::string) default="" : Path to ONNX model
  - Tbeta (double) default=0.6 : clustering beta threshold
  - Td (double) default=0.3 : clustering distance threshold
  - MaxHitsPerEvent (int) default=0 : Cap input hits per event (0=off)
  - OnnxChunk (int) default=4096 : Chunk size for ONNX inference
  - DropWireIfAbsDTooLarge (bool) default=true (member=m_dropWireIfAbsDTooLarge)
  - MaxAbsDMM (double) default=30.0 (member=m_maxAbsDMM)
  - ZeroMinSizeKeep (int) default=8 : Min hits for a label=0 group to be considered (else dropped)
  - MinWireFracKeep (double) default=0.60 : Min fraction of wire hits to keep a zero-label group
  - PromoteZeroIfGood (bool) default=true : If a zero-label group passes checks, treat it as a normal cluster
  - SkipZeroIfSmall (bool) default=true : If label=0 group smaller than ZeroMinSizeKeep, drop it
  - SkipZeroAlways (bool) default=false : If true, never build tracks from label=0
  - FilterInputWiresByTruthPdg (bool) default=true (member=m_filterInputWiresByTruthPdg)
  - KeepTruthPdg (int) default=13 (member=m_keepTruthPdg)
  - DropWireIfUnlinked (bool) default=true (member=m_dropWireIfUnlinked)
  - GeoSvcName (std::string) default="GeoSvc" : GeoSvc name
  - DchName (std::string) default="DCH_v2" : Drift chamber detector name
  - JobTag (std::string) default="" (member=m_jobTag)

### `PlotTrackHitResiduals.cpp`
- **Arguments / Properties (inferred):**
  - Bz (float) default=2. : Z component of the (assumed constant) magnetic field in Tesla.

### `SimpleFitDCHFitter.cpp`
- **Arguments / Properties (inferred):**
  - Bz (double) default=2.0 : Uniform Bz [T] (for pT conversion/logging)
  - PDG (int) default=13 : PDG hypothesis (charge sign)
  - MinGroupSize (unsigned) default=6u : Minimum hits per cluster to fit
  - DBSCAN_EpsMM (double) default=20.0 : DBSCAN epsilon [mm]
  - DBSCAN_MinPts (unsigned) default=6u : DBSCAN minPts
  - DeduplicateHits (bool) default=true : Drop consecutive near-duplicates
  - DedupTolMM (double) default=0.25 : Dedup tolerance [mm]
  - HistStream (std::string) default="simple" : THistSvc stream (file logical name)
  - MaxEventsY (int) default=2000 : Y span for 2D 'vs event' plots
  - PtBins (unsigned) default=100u : pT bins
  - PtMax (double) default=100.0 : pT max [GeV]
  - EtaMax (double) default=3.0 : \|eta\| max
  - UseMaterialEffects (bool) default=false (member=m_useMatEff)
  - UseTGeoPath (bool) default=true (member=m_useTGeoPath)
  - FallbackXOverX0 (double) default=0.02 (member=m_fallbackXOverX0)
  - MS_K_GeV (double) default=0.0136 (member=m_msK_GeV)
  - MS_Scale (double) default=1.0 (member=m_msScale)
  - BaseVar_d0 (float) default=1.0f : base var(d0) [mm^2]
  - BaseVar_phi (float) default=1e-3f : base var(phi) [rad^2]
  - BaseVar_omega (float) default=1e-8f : base var(omega) [(GeV^-1)^2] (placeholder)
  - BaseVar_z0 (float) default=1.0f : base var(z0) [mm^2]
  - BaseVar_tanLambda (float) default=1e-2f : base var(tanLambda) [1]

### `ThreePointFitter.cpp`
- **Arguments / Properties (inferred):**
  - Bz (double) default=2.0 : Uniform B [Tesla] for pT conversion
  - PDG (int) default=13 : PDG hypothesis (charge sign only)
  - MinHitsPerGroup (unsigned) default=3u : Minimum hits per GGTF label to fit
  - MinChordMM (double) default=5.0 : Min chord length among the 3 picked points [mm]
  - MinRadiusMM (double) default=100.0 : Reject tiny circles R < this [mm]
  - MinDeltaPhi (double) default=0.10 : Require φ_max-φ_min >= this [rad] (about origin)
  - FitTanLambda (bool) default=true : Estimate tanLambda from z(phi) linear fit
  - PrintDiagnostics (bool) default=true : Print per-track geometry diagnostics
  - DiagEveryN (int) default=1 : Print every N-th track (per event grouping)

### `TrackdNdxDelphesBased.h`
- **Arguments / Properties (inferred):**
  - ZmaxParameterName (std::string) default={"DCH_gas_Lhalf" (member=m_Zmax_parameter_name)
  - ZminParameterName (std::string) default={"DCH_gas_Lhalf" (member=m_Zmin_parameter_name)
  - RminParameterName (std::string) default={"DCH_gas_inner_cyl_R" (member=m_Rmin_parameter_name)
  - RmaxParameterName (std::string) default={"DCH_gas_outer_cyl_R" (member=m_Rmax_parameter_name)
  - GasSel (int) default={0 : Gas selection: 0: He(90%)-Isobutane(10%), 1: pure He, 2: Ar(50%)-Ethane(50%), 3: pure Ar.
  - FillFactor (double) default={1.0 (member=m_fill_factor)

### `TracksFromGenParticles.cpp`
- **Arguments / Properties (inferred):**
  - ExtrapolateToECal (bool) default=false (member=m_extrapolateToECal)
  - KeepOnlyBestExtrapolation (bool) default=true (member=m_keepOnlyBestExtrapolation)
  - MinimumParticleMomentum (float) default=0.010 (member=m_minParticleMomentum)
  - SystemEncoding (std::string) default="system:5" : System encoding string
