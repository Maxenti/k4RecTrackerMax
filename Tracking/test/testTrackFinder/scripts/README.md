# test/testTrackFinder/scripts

This README is auto-generated from per-file `DOC:` blocks (preferred) plus heuristics.
Improve accuracy by adding a `DOC:` header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `analyze_pt_resolution.py` | tracks: dict of arrays ('px','py','pz'), shape per event: variable-length list |  |  | gaudi:topalg:GenFitTracks<br>import:argparse<br>import:awkward<br>import:csv<br>import:matplotlib.pyplot<br>import:uproot |
| ✅ `autoreadme.py` | ... | ... | ... | gaudi:topalg:track<br>import:__future__<br>import:argparse<br>import:dataclasses<br>import:pathlib<br>import:re<br>import:typing<br>uses:k4run |
| ⚠️ `compact_path.txt` |  |  |  |  |
| ⚠️ `condor_ddsim.sh` | !/usr/bin/env bash |  |  | import:math<br>import:sys |
| ⚠️ `condor_reco.sh` | !/usr/bin/env bash |  |  | calls:runDCHTestTrackFinder.py<br>gaudi:topalg:genfit2 |
| ⚠️ `filelist.txt` |  |  |  |  |
| ⚠️ `filetest.sh` | PODIO “split” layout usually has: |  |  | gaudi:topalg:GenFitTracks_trackStates_<br>gaudi:topalg:GenFitTracks_trackStates_omega<br>gaudi:topalg:GenFitTracks_trackStates_phi<br>gaudi:topalg:GenFitTracks_trackStates_qOverP<br>gaudi:topalg:GenFitTracks_trackStates_tanLambda<br>gaudi:topalg:GenFitTracks_trackStates_theta<br>gaudi:topalg:GenFitTracks_tracks_omega<br>gaudi:topalg:GenFitTracks_tracks_qOverP<br>gaudi:topalg:GenFitTracks_tracks_theta<br>gaudi:topalg:_GenFitTracks_trackStates |
| ⚠️ `make_filelist.sh` | !/usr/bin/env bash |  |  |  |
| ⚠️ `make_runtime.sh` | !/usr/bin/env bash |  |  | gaudi:imports:Configurables<br>gaudi:topalg:GenFit2DCHFitter<br>gaudi:topalg:HelixFitter<br>gaudi:topalg:SimpleFitDCHFitter<br>gaudi:topalg:SimpleFitterAlg<br>gaudi:topalg:SimpleTrackFitterAlg<br>gaudi:topalg:TrackingConf<br>gaudi:topalg:libDCHdigi<br>gaudi:topalg:libTracking<br>import:Configurables |
| ⚠️ `make_sigma_pt_plot.py` | Try binding ROOT TTreeReaderValue('vector<type>') for the given branch. |  |  | gaudi:topalg:GenFitTracks<br>import:matplotlib.pyplot<br>import:os |
| ⚠️ `mk_ddsim_grid.py` | !/usr/bin/env python3 |  |  | import:os |
| ⚠️ `out_dir.txt` |  |  |  |  |
| ⚠️ `prepare_and_submit.sh` | !/usr/bin/env bash |  |  | calls:scripts/mk_ddsim_grid.py<br>uses:condor |
| ⚠️ `queue_items.txt` |  |  |  |  |
| ⚠️ `reco_inputs.txt` |  |  |  |  |
| ⚠️ `reco_job.sh` | !/usr/bin/env bash |  |  | gaudi:imports:Configurables<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:SimpleFitTracks<br>gaudi:topalg:ThreePointTracks<br>gaudi:topalg:Tracks<br>gaudi:topalg:genfit2<br>gaudi:topalg:libDCHdigi<br>gaudi:topalg:libTracking<br>import:Configurables<br>import:os |
| ⚠️ `reco_queue.txt` |  |  |  |  |
| ⚠️ `stamp_ddsim_metadata.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:argparse |
| ⚠️ `stamp_pipeline_metadata.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:argparse<br>uses:k4run |
| ⚠️ `submit_reco.sh` | !/usr/bin/env bash |  |  | uses:condor |
| ⚠️ `sweep_pt.sh` | !/usr/bin/env bash |  |  | calls:local_chain.sh |

## Inputs / Outputs / Collections
### `autoreadme.py`
- **Inputs:** ...
- **Outputs:** ...
- **Collections:** ...
