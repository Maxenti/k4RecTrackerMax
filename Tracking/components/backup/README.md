# components/backup

This README is auto-generated from per-file DOC blocks (preferred) plus heuristics.
Improve accuracy by adding a DOC header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

Accepted DOC start markers include `DOC`, `DOC:`, `DOC_START`, `DOC_BEGIN` (and similar); end markers include `DOC_END`, `END_DOC` (and similar).

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `GenFit2DCHFitter.txt` | ====================================================================== |  |  | gaudi:topalg:GenFitTracks<br>gaudi:topalg:RetryIfNoFitterInfo<br>gaudi:topalg:outputTracks<br>include:ConstField.h<br>include:Exception.h<br>include:FieldManager.h<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h<br>include:GaudiKernel/ISvcLocator.h<br>include:KalmanFitterInfo.h |
| ⚠️ `GGTF_Tracking.txt` | ====================================================================== |  |  | gaudi:topalg:DCH_name<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:max3DPerTrack<br>gaudi:topalg:outputTracks<br>include:ATen/ATen.h<br>include:ATen/Parallel.h<br>include:DD4hep/Detector.h<br>include:DDSegmentation/BitFieldCoder.h<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h |
| ⚠️ `GGTF_Tracking__12_3_25.txt` | ====================================================================== |  |  | gaudi:topalg:DCH_v2<br>gaudi:topalg:DchName<br>gaudi:topalg:Max3DPerTrack<br>gaudi:topalg:OutputTracksGGTF<br>include:ATen/ATen.h<br>include:DD4hep/Detector.h<br>include:DDSegmentation/BitFieldCoder.h<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h<br>include:GaudiKernel/ISvcLocator.h |
| ⚠️ `SimpleFitDCHFitter.txt` | ====================================================================== |  |  | gaudi:topalg:SimpleTracks<br>gaudi:topalg:nTracksPerEvent<br>gaudi:topalg:outputTracks<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h<br>include:GaudiKernel/ISvcLocator.h<br>include:GaudiKernel/ITHistSvc.h<br>include:GaudiKernel/ServiceHandle.h<br>include:TGeoManager.h<br>include:TH1F.h |
| ⚠️ `ThreePointFitter.txt` | ====================================================================== |  |  | gaudi:topalg:ThreePointTracks<br>gaudi:topalg:outputTracks<br>include:Gaudi/Algorithm.h<br>include:Gaudi/Property.h<br>include:GaudiKernel/ISvcLocator.h<br>include:TVector3.h<br>include:algorithm<br>include:cmath<br>include:edm4hep/TrackCollection.h<br>include:edm4hep/TrackState.h |
