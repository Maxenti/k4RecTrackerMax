# test/testTrackFinder

This README is auto-generated from per-file `DOC:` blocks (preferred) plus heuristics.
Improve accuracy by adding a `DOC:` header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `cglenn.cc` |  |  |  |  |
| ⚠️ `compare_pt_trackstate_vs_hitcircle.py` | !/usr/bin/env python3 |  |  | gaudi:topalg:GenFitTracks<br>import:ROOT<br>import:argparse |
| ⚠️ `ddsim_local.sh` | !/usr/bin/env bash |  |  | import:math<br>import:numpy |
| ⚠️ `debug_z_spur_event.py` | debug_z_spur_event.py |  |  | gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:DCHDigi2SimLinkCollection<br>gaudi:topalg:DCHDigiCollection<br>gaudi:topalg:DCHDigiSimLinkCollection<br>gaudi:topalg:DCH_DigiCollection<br>import:argparse<br>import:matplotlib.pyplot<br>import:os<br>import:podio |
| ⚠️ `docker_stderror` |  |  |  |  |
| ⚠️ `filelist.txt` |  |  |  |  |
| ⚠️ `generate_joblist.py` |  |  |  |  |
| ⚠️ `inspect_events_pt_pathology.py` | !/usr/bin/env python3 |  |  | gaudi:topalg:GenFitTracks<br>import:ROOT<br>import:argparse |
| ⚠️ `k4rt_env.sh` |  |  |  |  |
| ⚠️ `local_chain.sh` | !/bin/bash |  |  | calls:runDCHTestTrackFinder.py<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:SimpleFitTracks<br>gaudi:topalg:ThreePointTracks<br>gaudi:topalg:Tracks<br>import:sys<br>uses:k4run |
| ⚠️ `local_chain_all.sh` | !/usr/bin/env bash |  |  |  |
| ⚠️ `make_ptres.py` | !/usr/bin/env python3 |  |  | gaudi:topalg:CDCHTracks<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:SimpleFitTracks<br>gaudi:topalg:SimpleTracks<br>gaudi:topalg:ThreePointTracks<br>gaudi:topalg:Tracks<br>gaudi:topalg:genfit2<br>import:ROOT<br>import:argparse<br>import:matplotlib.pyplot |
| ⚠️ `Noddsim_track_test.sh` | !/usr/bin/env bash |  |  | uses:k4run |
| ⚠️ `pack_k4rt_runtime.sh` | !/usr/bin/env bash |  |  |  |
| ⚠️ `print_metadata.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:os<br>import:sys |
| ⚠️ `pt_resolution_plot_pyroot.py` | Pick best index given optional std::vector<int> (or float/bool) branches. |  |  | gaudi:topalg:GenFitTracks<br>import:ROOT<br>import:csv<br>import:matplotlib.pyplot<br>import:numpy<br>import:os<br>import:pathlib |
| ⚠️ `ptres_from_edm4hep.py` | Returns (eta, E_GeV or None, pt_GeV or None) parsed from the path. |  |  | gaudi:topalg:GenFitTracks<br>gaudi:topalg:n_tracks<br>import:argparse<br>import:collections<br>import:edm4hep<br>import:math<br>import:matplotlib<br>import:matplotlib.pyplot<br>import:numpy<br>import:os |
| ⚠️ `reco_all.sh` | !/usr/bin/env bash |  |  | gaudi:topalg:genfit2 |
| ⚠️ `reco_filelist.txt` |  |  |  |  |
| ⚠️ `reco_scan.sh` | !/usr/bin/env bash |  |  | calls:/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/runDCHTestTrackFinder.py<br>gaudi:topalg:genfit2 |
| ⚠️ `run_dch_chain.sh` | !/bin/bash |  |  | import:TrackingConf<br>import:sys<br>uses:k4run |
| ⚠️ `runDCHTestTrackFinder.py` | Best-effort: fetch a Configurable class by name from Configurables. |  |  | gaudi:imports:Configurables<br>gaudi:topalg:CDCHTracks<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:DCHDigi2SimLink<br>gaudi:topalg:DCHDigi2SimLinkCollection<br>gaudi:topalg:DCHDigiSimLink<br>gaudi:topalg:DCHDigiSimLinkCollection<br>gaudi:topalg:DCHLooperEventFilter<br>gaudi:topalg:DCH_DigiCollection |
| ⚠️ `runTestTrackFinder.py` | ################# Parser |  |  | gaudi:imports:Configurables<br>gaudi:topalg:CDCHTracks<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_DigiCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:DCHdigi<br>gaudi:topalg:GGTF_tracking<br>import:Configurables<br>import:Gaudi.Configuration<br>import:k4FWCore |
| ⚠️ `scan_pt_resolution.py` | filename pattern |  |  | gaudi:topalg:FittedTracks<br>gaudi:topalg:TrackStates_time<br>import:glob<br>import:matplotlib.pyplot |
| ⚠️ `scan_pt_time_by_event.py` | scan_pt_time_by_event.py |  |  | calls:scan_pt_time_by_event.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:trackStates_begin<br>gaudi:topalg:trackStates_end<br>import:ROOT<br>import:argparse<br>import:csv<br>import:math |
| ⚠️ `simple_local_chain.sh` | !/bin/bash |  |  | calls:SimplerunDCHTestTrackFinder.py<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_v2<br>uses:k4run |
| ⚠️ `SimplerunDCHTestTrackFinder.py` | Return a local .onnx path for ONNXRuntime. |  |  | gaudi:imports:Configurables<br>gaudi:topalg:CDCHTracks<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_DigiCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:DCHdigi<br>gaudi:topalg:GGTF_tracking<br>gaudi:topalg:GenFit2DCHFitter<br>gaudi:topalg:GenFitFieldSvc<br>gaudi:topalg:GenFitMaterialSvc |
| ⚠️ `skim_edm4hep.py` | !/usr/bin/env python3 |  |  | gaudi:topalg:DCHCollection<br>import:ROOT<br>import:argparse<br>import:os<br>import:podio<br>import:sys |
| ⚠️ `SteeringFile_IDEA_o1_v03.py` | # The compact XML file, or multiple compact files, if the last one is the closer. |  |  | gaudi:topalg:Geant4TestTrackAction<br>gaudi:topalg:Geant4TrackerWeightedAction<br>gaudi:topalg:tracker<br>import:DDG4<br>import:DDSim.DD4hepSimulation<br>import:g4units |
| ⚠️ `SteeringFile_IDEA_o1_v03DCH.py` | dch_only_steer.py  — DCH-only DDSim steering (truth-friendly, robust) |  |  | gaudi:topalg:DCH_ID_Encoding<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:Geant4SimpleTrackerAction<br>gaudi:topalg:Geant4TrackerWeightedAction<br>gaudi:topalg:tracker<br>import:DDSim.DD4hepSimulation<br>import:g4units<br>import:types |
| ⚠️ `test_trackFinder.sh` | !/bin/bash |  |  | uses:k4run |
| ⚠️ `test_trackFinder_1.sh` | !/usr/bin/env bash |  |  | uses:k4run |
| ⚠️ `testcondor.sh` |  |  |  |  |
| ⚠️ `view_simhits_event.py` | view_simhits_event.py |  |  | gaudi:topalg:DCHCollection<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:dch_rin_m<br>gaudi:topalg:dch_ring_z_mm<br>gaudi:topalg:dch_rout_m<br>gaudi:topalg:track_collection<br>gaudi:topalg:track_style<br>gaudi:topalg:view_tracks_metadata<br>import:ROOT<br>import:argparse |
| ⚠️ `view_tracks_event.py` | view_tracks_event.py |  |  | gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:n_states_in_track<br>gaudi:topalg:trackStates_begin<br>gaudi:topalg:trackStates_end<br>gaudi:topalg:track_collection<br>gaudi:topalg:track_index<br>gaudi:topalg:track_style |
