# Archive

This README is auto-generated from per-file `DOC:` blocks (preferred) plus heuristics.
Improve accuracy by adding a `DOC:` header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `compare_pt_trackstate_vs_hitcircle.py` | compare_pt_trackstate_vs_hitcircle.py |  |  | calls:compare_pt_trackstate_vs_hitcircle.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:trackStates_begin<br>gaudi:topalg:trackStates_end<br>import:ROOT<br>import:argparse<br>import:csv<br>import:math |
| ⚠️ `ddsim_local.sh` | !/usr/bin/env bash |  |  | import:math<br>import:numpy |
| ⚠️ `filetest.sh` | PODIO “split” layout usually has: |  |  | gaudi:topalg:GenFitTracks_trackStates_<br>gaudi:topalg:GenFitTracks_trackStates_omega<br>gaudi:topalg:GenFitTracks_trackStates_phi<br>gaudi:topalg:GenFitTracks_trackStates_qOverP<br>gaudi:topalg:GenFitTracks_trackStates_tanLambda<br>gaudi:topalg:GenFitTracks_trackStates_theta<br>gaudi:topalg:GenFitTracks_tracks_omega<br>gaudi:topalg:GenFitTracks_tracks_qOverP<br>gaudi:topalg:GenFitTracks_tracks_theta<br>gaudi:topalg:_GenFitTracks_trackStates |
| ⚠️ `generate_joblist.py` |  |  |  |  |
| ⚠️ `local_chain_all.sh` | !/usr/bin/env bash |  |  |  |
| ⚠️ `make_ptres.py` | !/usr/bin/env python3 |  |  | gaudi:topalg:CDCHTracks<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:SimpleFitTracks<br>gaudi:topalg:SimpleTracks<br>gaudi:topalg:ThreePointTracks<br>gaudi:topalg:Tracks<br>gaudi:topalg:genfit2<br>import:ROOT<br>import:argparse<br>import:matplotlib.pyplot |
| ⚠️ `make_sigma_pt_plot.py` | Try binding ROOT TTreeReaderValue('vector<type>') for the given branch. |  |  | gaudi:topalg:GenFitTracks<br>import:matplotlib.pyplot<br>import:os |
| ⚠️ `pt_resolution_plot_pyroot.py` | Pick best index given optional std::vector<int> (or float/bool) branches. |  |  | gaudi:topalg:GenFitTracks<br>import:ROOT<br>import:csv<br>import:matplotlib.pyplot<br>import:numpy<br>import:os<br>import:pathlib |
| ⚠️ `ptres_from_edm4hep.py` | Returns (eta, E_GeV or None, pt_GeV or None) parsed from the path. |  |  | gaudi:topalg:GenFitTracks<br>gaudi:topalg:n_tracks<br>import:argparse<br>import:collections<br>import:edm4hep<br>import:math<br>import:matplotlib<br>import:matplotlib.pyplot<br>import:numpy<br>import:os |
| ⚠️ `reco_all.sh` | !/usr/bin/env bash |  |  | gaudi:topalg:genfit2 |
| ⚠️ `reco_scan.sh` | !/usr/bin/env bash |  |  | calls:/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/runDCHTestTrackFinder.py<br>gaudi:topalg:genfit2 |
| ⚠️ `run_dch_chain.sh` | !/bin/bash |  |  | import:TrackingConf<br>import:sys<br>uses:k4run |
| ⚠️ `simple_local_chain.sh` | !/bin/bash |  |  | calls:SimplerunDCHTestTrackFinder.py<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_v2<br>uses:k4run |
| ⚠️ `SimplerunDCHTestTrackFinder.py` | Return a local .onnx path for ONNXRuntime. |  |  | gaudi:imports:Configurables<br>gaudi:topalg:CDCHTracks<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_DigiCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:DCHdigi<br>gaudi:topalg:GGTF_tracking<br>gaudi:topalg:GenFit2DCHFitter<br>gaudi:topalg:GenFitFieldSvc<br>gaudi:topalg:GenFitMaterialSvc |
| ⚠️ `skim_edm4hep.py` | !/usr/bin/env python3 |  |  | gaudi:topalg:DCHCollection<br>import:ROOT<br>import:argparse<br>import:os<br>import:podio<br>import:sys |
| ⚠️ `SteeringFile_IDEA_o1_v03.py` | # The compact XML file, or multiple compact files, if the last one is the closer. |  |  | gaudi:topalg:Geant4TestTrackAction<br>gaudi:topalg:Geant4TrackerWeightedAction<br>gaudi:topalg:tracker<br>import:DDG4<br>import:DDSim.DD4hepSimulation<br>import:g4units |
| ⚠️ `SteeringFile_IDEA_o1_v03DCH.py` | dch_only_steer.py  — DCH-only DDSim steering (truth-friendly, robust) |  |  | gaudi:topalg:DCH_ID_Encoding<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:Geant4SimpleTrackerAction<br>gaudi:topalg:Geant4TrackerWeightedAction<br>gaudi:topalg:tracker<br>import:DDSim.DD4hepSimulation<br>import:g4units<br>import:types |
| ⚠️ `test_trackFinder_1.sh` | !/usr/bin/env bash |  |  | uses:k4run |
| ⚠️ `testcondor.sh` |  |  |  |  |
