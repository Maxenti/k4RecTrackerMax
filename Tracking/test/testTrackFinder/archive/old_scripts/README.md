# test/testTrackFinder/Archive

This README is auto-generated from per-file DOC blocks (preferred) plus heuristics.
Improve accuracy by adding a DOC header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

Accepted DOC start markers include `DOC`, `DOC:`, `DOC_START`, `DOC_BEGIN` (and similar); end markers include `DOC_END`, `END_DOC` (and similar).

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

## Details

### `compare_pt_trackstate_vs_hitcircle.py`
- **Arguments / Properties (inferred):**
  - --input \| Input EDM4hep ROOT file
  - --events \| Comma-separated event indices, e.g. 718,838,96
  - --hits \| default="GGTF_3DHits"
  - --track \| default="GenFitTracks"
  - --Bz \| default=2.0
  - --expectedPt \| default=None
  - --sigmaXY \| default=0.5
  - --out \| default="pt_diagnostic.csv"

### `make_ptres.py`
- **Arguments / Properties (inferred):**
  - --input
  - --tree \| default="events"
  - --fitter \| default="auto"
  - --Bz \| default=2.0
  - --allow-any-location \| Use any TrackState location, not just AtIP
  - --emin \| default=0.5
  - --emax \| default=20.0
  - --nbins \| default=10
  - --out \| default=""
  - --csv \| default=""

### `pt_resolution_plot_pyroot.py`
- **Arguments / Properties (inferred):**
  - --reco-root \| Root folder containing reco outputs grouped by eta±X.XX
  - --pdg \| default=13
  - --out-png \| default="pt_resolution_vs_pt.png"
  - --out-csv \| default="" \| Optional CSV with binned results
  - --nbins \| default=12
  - --pt-min \| default=0.05
  - --pt-max \| default=20.0
  - --tracks-prefix \| default="GenFitTracks"

### `ptres_from_edm4hep.py`
- **Arguments / Properties (inferred):**
  - "inputs", nargs="+", help="One or more EDM4hep reco ROOT files (single-pT gun per file
  - --tracks \| default="GenFitTracks" \| Track collection name.
  - --bz \| default=2.0 \| Magnetic field [T] used in fit.
  - --speciesMass \| default=0.10566
  - --png \| default="ptres_vs_pt.png" \| Output PNG filename.
  - --requireAtIP \| default=False \| Only accept tracks that have an AtIP state.
  - --bootstrap \| default=0

### `SimplerunDCHTestTrackFinder.py`
- **Arguments / Properties (inferred):**
  - --inputFile \| default="ddsim_output_edm4hep.root"
  - --outputFile \| default="output_digi_tracks.root" \| Output EDM4hep file
  - --modelPath \| default=""
  - --tbeta \| default=0.05 \| GGTF beta threshold
  - --td \| default=0.05 \| GGTF distance threshold
  - --dchSimHits \| default="DCHCollection" \| Name of DCH sim-hit collection in the input file
  - --compactXML \| default=""
  - --dchName \| default="DCH_v2"
  - --produce3DHits \| default=False
  - --ggtfLog \| default="INFO" \| GGTF_tracking OutputLevel.
  - --maxHitsPerEvent \| default=0
  - --wireGateMM \| default=3.0
  - --onnxChunk \| default=4096
  - --max3DHitsPerEvent \| default=1000000 \| Hard cap for number of 3D hits created per event.
  - --max3DPerTrack \| default=100000 \| Hard cap for number of 3D hits created per reconstructed track.
  - --stage \| default="ggtf"
  - --fitter \| default="none" \| Optionally run a fitter after GGTF.
  - --fitOut \| default="GenFitTracks"
  - --fitterLog \| default="INFO" \| GenFit2DCHFitter OutputLevel.
  - --gf-useMat \| default=True
  - --no-gf-useMat \| Disable material effects in GenFit.
  - --gf-sortHits \| default=True
  - --no-gf-sortHits \| Do not sort hits.
  - --gf-dedup \| default=True
  - --no-gf-dedup \| Do not deduplicate hits.

### `skim_edm4hep.py`
- **Arguments / Properties (inferred):**
  - --input
  - --output
  - --coll \| default="DCHCollection"
  - --tmax \| default=450.0
  - --nhits-max \| default=30000
  - --keep-empty \| default=False
  - --force-mode \| default="auto" \| auto: try ROOT leaves then PODIO. root: only ROOT leaves. podio: only PODIO.
