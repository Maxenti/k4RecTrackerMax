# test/testTrackFinder/scripts

This README is auto-generated from per-file `DOC:` blocks (preferred) plus heuristics.
Improve accuracy by adding a `DOC:` header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `analyze_job.sh` | !/usr/bin/env bash |  |  | calls:analyze_pt_resolution_grid.py<br>gaudi:topalg:GenFitTracks |
| ⚠️ `analyze_pt_resolution_grid.py` | DOC |  |  | gaudi:topalg:GenFitTracks<br>import:ROOT<br>import:argparse<br>import:array<br>import:ctypes<br>import:math<br>import:os<br>import:random<br>import:re<br>import:scan_pt_time_by_event |
| ✅ `autoreadme.py` | ... | ... | ... | gaudi:topalg:track<br>import:__future__<br>import:argparse<br>import:dataclasses<br>import:pathlib<br>import:re<br>import:typing<br>uses:k4run |
| ⚠️ `cglenn.cc` |  |  |  |  |
| ⚠️ `compact_path.txt` |  |  |  |  |
| ⚠️ `compare_pt_resolution_grid.py` | DOC |  |  | calls:compare_pt_resolution_outputs.py<br>import:ROOT<br>import:argparse<br>import:ctypes<br>import:math |
| ⚠️ `condor_ddsim.sh` | !/usr/bin/env bash |  |  | import:math<br>import:sys |
| ⚠️ `condor_reco.sh` | !/usr/bin/env bash |  |  | calls:runDCHTestTrackFinder.py<br>gaudi:topalg:genfit2 |
| ⚠️ `debug_z_spur_event.py` | DOC |  |  | gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:DCHDigi2SimLinkCollection<br>gaudi:topalg:DCHDigiCollection<br>gaudi:topalg:DCHDigiSimLinkCollection<br>gaudi:topalg:DCH_DigiCollection<br>import:argparse<br>import:matplotlib.pyplot<br>import:os<br>import:podio |
| ⚠️ `dump_covmatrix_one_event.py` | DOC |  |  | calls:scripts/dump_covmatrix_one_event.py<br>import:ROOT<br>import:argparse<br>import:math |
| ⚠️ `filelist.txt` |  |  |  |  |
| ⚠️ `inspect_events_pt_pathology.py` | !/usr/bin/env python3 |  |  | gaudi:topalg:GenFitTracks<br>import:ROOT<br>import:argparse |
| ⚠️ `make_filelist.sh` | !/usr/bin/env bash |  |  |  |
| ⚠️ `make_runtime.sh` | !/usr/bin/env bash |  |  | gaudi:imports:Configurables<br>gaudi:topalg:GenFit2DCHFitter<br>gaudi:topalg:HelixFitter<br>gaudi:topalg:SimpleFitDCHFitter<br>gaudi:topalg:SimpleFitterAlg<br>gaudi:topalg:SimpleTrackFitterAlg<br>gaudi:topalg:TrackingConf<br>gaudi:topalg:libDCHdigi<br>gaudi:topalg:libTracking<br>import:Configurables |
| ⚠️ `mk_ddsim_grid.py` | !/usr/bin/env python3 |  |  | import:os |
| ⚠️ `plot_mcparticles_pt.py` | DOC |  |  | gaudi:topalg:GenFit<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates<br>gaudi:topalg:trackState<br>gaudi:topalg:trackStates<br>import:argparse<br>import:awkward<br>import:numpy<br>import:uproot |
| ⚠️ `plot_pt_from_trackstate_time.py` | DOC |  |  | calls:plot_pt_from_trackstate_time.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates<br>gaudi:topalg:trackStates<br>import:ROOT<br>import:argparse<br>import:math<br>import:matplotlib<br>import:matplotlib.pyplot<br>import:numpy |
| ⚠️ `prepare_and_submit.sh` | !/usr/bin/env bash |  |  | calls:scripts/mk_ddsim_grid.py<br>uses:condor |
| ⚠️ `print_metadata.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:os<br>import:sys |
| ⚠️ `queue_items.txt` |  |  |  |  |
| ⚠️ `reco_job.sh` | !/usr/bin/env bash |  |  | gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:Tracks<br>uses:k4run |
| ⚠️ `scan_pt_time_by_event.py` | DOC |  |  | calls:scan_pt_time_by_event.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:n_tracks_evt<br>gaudi:topalg:nstates_per_track_max<br>gaudi:topalg:nstates_per_track_med<br>gaudi:topalg:nstates_per_track_min<br>gaudi:topalg:primary_track_index<br>gaudi:topalg:primary_track_nstates |
| ⚠️ `stamp_ddsim_metadata.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:argparse |
| ⚠️ `stamp_pipeline_metadata.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:argparse<br>uses:k4run |
| ⚠️ `submit_reco.sh` | !/usr/bin/env bash |  |  | calls:make_filelist.sh<br>uses:condor |
| ⚠️ `sweep_pt.sh` | !/usr/bin/env bash |  |  | calls:local_chain.sh |
| ⚠️ `view_simhits_event.py` | DOC |  |  | gaudi:topalg:DCHCollection<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:n_states_in_track<br>gaudi:topalg:no_trackstate_prefix<br>gaudi:topalg:no_trackstates<br>gaudi:topalg:trackStates_begin<br>gaudi:topalg:trackStates_end<br>gaudi:topalg:track_collection |
| ⚠️ `view_tracks_event.py` | DOC |  |  | calls:view_tracks_event.py<br>gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:n_states_in_track<br>gaudi:topalg:trackStates_begin<br>gaudi:topalg:trackStates_end<br>gaudi:topalg:track_collection<br>gaudi:topalg:track_index |

## Inputs / Outputs / Collections
### `autoreadme.py`
- **Inputs:** ...
- **Outputs:** ...
- **Collections:** ...
