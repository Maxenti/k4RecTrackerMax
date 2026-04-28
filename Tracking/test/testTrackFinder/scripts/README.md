# test/testTrackFinder/scripts

This README is auto-generated from per-file DOC blocks (preferred) plus heuristics.
Improve accuracy by adding a DOC header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

Accepted DOC start markers include `DOC`, `DOC:`, `DOC_START`, `DOC_BEGIN` (and similar); end markers include `DOC_END`, `END_DOC` (and similar).

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `analyze_job.sh` | !/usr/bin/env bash |  |  | calls:analyze_pt_resolution_grid.py<br>gaudi:topalg:GenFitTracks |
| ✅ `analyze_pt_resolution_grid.py` |  |  |  | gaudi:topalg:GenFitTracks<br>import:ROOT<br>import:argparse<br>import:array<br>import:ctypes<br>import:math<br>import:os<br>import:random<br>import:re<br>import:scan_pt_time_by_event |
| ✅ `autoreadme.py` |  |  |  | gaudi:topalg:genfit<br>gaudi:topalg:track<br>import:__future__<br>import:argparse<br>import:dataclasses<br>import:pathlib<br>import:re<br>import:typing<br>uses:k4run |
| ⚠️ `Calculate_Aucoating_thickness.py` | Calculate_Aucoating_thickness.py |  |  | calls:Calculate_Aucoating_thickness.py<br>import:argparse<br>import:math |
| ⚠️ `cglenn.cc` |  |  |  |  |
| ⚠️ `compact_path.txt` |  |  |  |  |
| ✅ `compare_pt_resolution_grid.py` |  | python3 compare_pt_resolution_outputs.py \<br>a CF_out.root --b W_out.root \<br>out compare_CF_vs_W.root \ |  | calls:compare_pt_resolution_outputs.py<br>import:ROOT<br>import:argparse<br>import:ctypes<br>import:math |
| ⚠️ `condor_ddsim.sh` | !/usr/bin/env bash |  |  | import:math<br>import:sys |
| ⚠️ `condor_reco.sh` | !/usr/bin/env bash |  |  | calls:runDCHTestTrackFinder.py<br>gaudi:topalg:genfit2 |
| ⚠️ `debug_z_spur_event.py` | DOC |  |  | gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:DCHDigi2SimLinkCollection<br>gaudi:topalg:DCHDigiCollection<br>gaudi:topalg:DCHDigiSimLinkCollection<br>gaudi:topalg:DCH_DigiCollection<br>import:argparse<br>import:matplotlib.pyplot<br>import:os<br>import:podio |
| ⚠️ `DelphesParamsOutput.py` | extract_delphes_tracker_params.py |  |  | calls:extract_delphes_tracker_params.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:fit_mode<br>gaudi:topalg:n_points_fit<br>gaudi:topalg:per_eta_fits<br>gaudi:topalg:trackCollection<br>gaudi:topalg:track_eta_max_inferred<br>import:argparse<br>import:collections<br>import:csv |
| ✅ `dump_covmatrix_one_event.py` |  | python3 scripts/dump_covmatrix_one_event.py /eos/user/c/cglenn/reco_samples2/Debugging/1_20_2026/CF/eta_+1.00/reco_eta+1.00_pt14.142.root --event 0 --raw<br>python3 scripts/dump_covmatrix_one_event.py file.root --event 0<br>python3 scripts/dump_covmatrix_one_event.py file.root --event 0 --prefix _GenFitTracks_trackStates. |  | calls:scripts/dump_covmatrix_one_event.py<br>import:ROOT<br>import:argparse<br>import:math |
| ⚠️ `filelist.txt` |  |  |  |  |
| ⚠️ `inspect_events_pt_pathology.py` | !/usr/bin/env python3 |  |  | gaudi:topalg:GenFitTracks<br>import:ROOT<br>import:argparse |
| ⚠️ `make_filelist.sh` | !/usr/bin/env bash |  |  |  |
| ⚠️ `make_runtime.sh` | !/usr/bin/env bash |  |  | gaudi:imports:Configurables<br>gaudi:topalg:GenFit2DCHFitter<br>gaudi:topalg:HelixFitter<br>gaudi:topalg:SimpleFitDCHFitter<br>gaudi:topalg:SimpleFitterAlg<br>gaudi:topalg:SimpleTrackFitterAlg<br>gaudi:topalg:TrackingConf<br>gaudi:topalg:libDCHdigi<br>gaudi:topalg:libTracking<br>import:Configurables |
| ⚠️ `mk_ddsim_grid.py` | !/usr/bin/env python3 |  |  | import:os |
| ⚠️ `patch_trkCov_match_dch_material.py` | Example: |  |  | calls:patch_trkCov_match_dch_material.py<br>calls:scripts/patch_trkCov_match_dch_material.py<br>gaudi:topalg:IDEA_DCH<br>import:ROOT<br>import:argparse<br>import:numpy<br>import:uproot |
| ✅ `plot_mcparticles_pt.py` |  |  |  | gaudi:topalg:GenFit<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates<br>gaudi:topalg:trackState<br>gaudi:topalg:trackStates<br>import:argparse<br>import:awkward<br>import:numpy<br>import:uproot |
| ✅ `plot_pt_from_trackstate_time.py` |  |  |  | calls:plot_pt_from_trackstate_time.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates<br>gaudi:topalg:trackStates<br>import:ROOT<br>import:argparse<br>import:math<br>import:matplotlib<br>import:matplotlib.pyplot<br>import:numpy |
| ⚠️ `prepare_and_submit.sh` | !/usr/bin/env bash |  |  | calls:scripts/mk_ddsim_grid.py<br>uses:condor |
| ⚠️ `print_metadata.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:os<br>import:sys |
| ⚠️ `queue_items.txt` |  |  |  |  |
| ⚠️ `reco_job.sh` | !/usr/bin/env bash |  |  | gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:Tracks<br>uses:k4run |
| ✅ `scan_pt_time_by_event.py` |  | python3 scan_pt_time_by_event.py --input reco.root --expectedPt 53.183 --stdout |  | calls:scan_pt_time_by_event.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:n_tracks_evt<br>gaudi:topalg:nstates_per_track_max<br>gaudi:topalg:nstates_per_track_med<br>gaudi:topalg:nstates_per_track_min<br>gaudi:topalg:primary_track_index<br>gaudi:topalg:primary_track_nstates |
| ⚠️ `stamp_ddsim_metadata.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:argparse |
| ⚠️ `stamp_pipeline_metadata.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:argparse<br>uses:k4run |
| ⚠️ `submit_reco.sh` | !/usr/bin/env bash |  |  | calls:make_filelist.sh<br>uses:condor |
| ⚠️ `sweep_pt.sh` | !/usr/bin/env bash |  |  | calls:local_chain.sh |
| ✅ `view_simhits_event.py` |  |  |  | gaudi:topalg:DCHCollection<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:n_states_in_track<br>gaudi:topalg:no_trackstate_prefix<br>gaudi:topalg:no_trackstates<br>gaudi:topalg:trackStates_begin<br>gaudi:topalg:trackStates_end<br>gaudi:topalg:track_collection |
| ✅ `view_tracks_event.py` |  |  |  | calls:view_tracks_event.py<br>gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:n_states_in_track<br>gaudi:topalg:trackStates_begin<br>gaudi:topalg:trackStates_end<br>gaudi:topalg:track_collection<br>gaudi:topalg:track_index |

## Details

### `analyze_pt_resolution_grid.py`
- **Arguments / Properties (inferred):**
  - --inputDir \| Reco base dir containing eta_* subdirs
  - --outRoot \| Output ROOT file
  - --trackCollection \| default="GenFitTracks"
  - --hitCollection \| default="OutputWireHitsGGTF"
  - --minPhiSpan \| default=0.06
  - --minChordXY \| default=500.0
  - --maxCircleCond \| default=1e6
  - --centralFrac \| default=0.95
  - --qualityCut \| default="none"
  - --maxFilesPerEta \| default=0
  - --diagBootstrap \| default=200 \| Bootstrap samples for median-type error bars
  - --diagBootstrapSeed \| default=12345 \| Seed base for diagnostic bootstrap RNG
  - --methodBootstrap \| default=300
  - --methodBootstrapSeed \| default=54321 \| Seed base for method bootstrap RNG
  - --methodBootstrapCap \| default=5000
  - --maxRelErrWarn \| default=0.5

### `autoreadme.py`
- **Arguments / Properties (inferred):**
  - ...
  - --root
  - --write \| Write README.md / DOCS_INDEX.md / docs/chain.mmd
  - --no-graph \| Skip writing docs/chain.mmd
  - --check \| Exit non-zero if important files are missing DOC blocks
  - --inject-stubs

### `Calculate_Aucoating_thickness.py`
- **Arguments / Properties (inferred):**
  - --cf_d_um \| Carbon fiber core diameter [µm]
  - --cf_r_um \| Carbon fiber core radius [µm]
  - --sigma_au \| default=4.10e7
  - --sigma_w \| default=1.79e7
  - --sigma_cf \| default=4.00e4
  - --sigma_nip \| default=1.5e6
  - --w_d_um \| default=20.0
  - --au_ref_t_um \| default=0.3
  - --f_max_GHz \| default=2.0
  - --k_skin \| default=3.0
  - --mu_r_au \| default=1.0
  - --mu_r_w \| default=1.0
  - --mu_r_cf \| default=1.0
  - --mu_r_nip \| default=1.0
  - --use_nip
  - --t_nip_um \| default=0.10
  - --tmax_factor \| default=50.0

### `compare_pt_resolution_grid.py`
- **Arguments / Properties (inferred):**
  - --a
  - --b
  - --out \| Output ROOT comparison file
  - --tagA \| default="A"
  - --tagB \| default="B"
  - --xRound \| default=6 \| Rounding digits for matching pT points
  - --diagAbsTolPassFrac \| default=0.05
  - --diagRelTolPassFrac \| default=0.10
  - --diagAbsTolFrac \| default=0.05 \| Abs tolerance for frac_* diagnostic differences.
  - --diagRelTolMed \| default=0.25 \| Rel tolerance for med_* diagnostic ratios deviation \|A/B - 1\|.

### `debug_z_spur_event.py`
- **Arguments / Properties (inferred):**
  - --input
  - --event
  - --wire-coll \| default="" \| SenseWireHit collection name
  - --link-coll \| default="" \| SenseWireHitSimTrackerHitLink collection name
  - --mc-coll \| default=""
  - --z-min \| default=None \| Optional z-min mm for focusing on spur region
  - --z-max \| default=None \| Optional z-max mm for focusing on spur region
  - --png \| default="" \| Output PNG for time-vs-z plot

### `DelphesParamsOutput.py`
- **Arguments / Properties (inferred):**
  - --inputDir \| Reco base dir containing eta_* subdirs
  - --outJson \| default="tracker_params.json" \| JSON report output
  - --outCsv \| default="tracker_points.csv" \| CSV table output
  - --trackCollection \| default="GenFitTracks"
  - --hitCollection \| default="OutputWireHitsGGTF"
  - --minPhiSpan \| default=0.06
  - --minChordXY \| default=500.0
  - --maxCircleCond \| default=1e6
  - --centralFrac \| default=0.95
  - --qualityCut \| default="none"
  - --method \| default="truncrms68" \| Which resolution estimator becomes dpT/pT used for the Delphes fit.
  - --ptPlateauMin \| default=5.0 \| pT threshold used to estimate plateau tracking efficiency
  - --effTurnonFrac \| default=0.5 \| Threshold fraction of plateau used to estimate TRACK_PT_MIN
  - --overrideEtaMax \| default=float("nan"
  - --fitMode \| default="global"
  - --minFitPt \| default=0.2

### `dump_covmatrix_one_event.py`
- **Arguments / Properties (inferred):**
  - "file"
  - --event \| default=0
  - --prefix \| default="AUTO"
  - --raw \| Print raw packed values with indices
  - --max-states \| default=50 \| Safety cap if something looks weird

### `inspect_events_pt_pathology.py`
- **Arguments / Properties (inferred):**
  - --input
  - --events \| Comma-separated event indices, e.g. 718,838,302
  - --hits \| default="GGTF_3DHits"
  - --track \| default="GenFitTracks"

### `mk_ddsim_grid.py`
- **Arguments / Properties (inferred):**
  - --out \| default="params_ddsim.jsonl" \| Output JSONL of job params
  - --pt-min \| default=0.01 \| min pT [GeV]
  - --pt-max \| default=200.0 \| max pT [GeV]
  - --pt-n \| default=30
  - --etas \| default="0.0 \| comma list of eta values
  - --nev \| default=1000 \| events per point
  - --particle \| default="mu-" \| gun particle PDG name
  - --phi-uniform \| default=True
  - --theta-smear \| default=0.0
  - --seed0 \| default=1_000_000 \| base RNG seed

### `patch_trkCov_match_dch_material.py`
- **Arguments / Properties (inferred):**
  - --base-card
  - --g4-cf
  - --g4-w
  - --outdir
  - --npart \| default=12
  - --hist \| default=None
  - --tag \| default="IDEA_DCH"

### `plot_mcparticles_pt.py`
- **Arguments / Properties (inferred):**
  - --input \| Input ROOT file
  - --out \| default="pt_diagnostics.root" \| Output ROOT file
  - --tree \| default="events"
  - --mc-prefix \| default="MCParticles/MCParticles"
  - --max-events \| default=-1
  - --pdg \| default=13
  - --pdg-abs
  - --no-pdg-abs \| Match PDG with sign.
  - --trackstate-prefix \| default=""
  - --assume-q \| default=-1 \| Charge sign used for pT=\|q/omega\| if you don

### `plot_pt_from_trackstate_time.py`
- **Arguments / Properties (inferred):**
  - -i
  - --tree \| default="events"
  - --coll \| default="GenFitTracks"
  - --leaf \| default=None
  - --invalid-sentinel \| default=-1.0
  - --include-invalid
  - --min \| default=None
  - --max \| default=None
  - --per-event \| default="all" \| How to reduce multiple TrackState.time values per event.
  - --max-events \| default=None \| Only process first N events.
  - --events \| default=None
  - --bins \| default="80" \| Binning:
  - --bin-edges \| default=None \| Comma-separated custom bin edges, e.g.
  - --logy \| Log scale on y-axis.
  - --title \| default=None \| Plot title.
  - -o \| default="pt_hist.png"
  - --dpi \| default=160
  - --show
  - --verbose \| Verbose diagnostics.

### `scan_pt_time_by_event.py`
- **Arguments / Properties (inferred):**
  - --input \| Input EDM4hep ROOT file
  - --trackCollection \| default="GenFitTracks"
  - --hitCollection \| default="OutputWireHitsGGTF" \| SenseWireHit collection name
  - --expectedPt \| Expected pT for this sample [GeV]
  - --top \| default=30
  - --event \| default=None
  - --csv \| default=None
  - --verbose
  - --invalidTime \| default=-1.0
  - --minPhiSpan \| default=0.06
  - --minChordXY \| default=500.0
  - --maxCircleCond \| default=1e6
  - --centralFrac \| default=0.95
  - --type \| default="bad"
  - --metric \| default="abs"
  - --log \| default=""
  - --stdout

### `stamp_ddsim_metadata.py`
- **Arguments / Properties (inferred):**
  - --root
  - --params-json \| Per-job params JSON
  - --compact-xml \| Compact XML path/file actually used on worker
  - --cmd
  - --theta-min
  - --theta-max
  - --phi-opts \| default=""
  - --out-eos \| default="" \| EOS_POSIX target
  - --out-url \| default="" \| EOS_URL target
  - --k4-release \| default="" \| Key4HEP release tag you sourced
  - --job-extra \| default=[]

### `stamp_pipeline_metadata.py`
- **Arguments / Properties (inferred):**
  - --root
  - --stage \| stage name: ddsim\|digi\|ggtf\|fit\|analysis\|...
  - --cmd
  - --config \| default=[]
  - --input \| default=[]
  - --extra \| default=[]
  - --workdir \| default="." \| directory to use for git info
  - --key \| default="pipeline_metadata_json" \| ROOT key name

### `view_simhits_event.py`
- **Arguments / Properties (inferred):**
  - --input
  - --tree \| default="events"
  - --event \| default=-1
  - --hitsCollection \| default="OutputWireHitsGGTF" \| Hit collection with position.{x,y,z}. If not found, auto-detect a likely GGTF hit collection.
  - --autoDetectHits \| If set, auto-detect hits collection even if --hitsCollection is provided.
  - --simhitCollection \| default="DCHCollection"
  - --trackCollection \| default="GenFitTracks"
  - --trackStyle \| default="helix"
  - --Bz \| default=2.0
  - --assumeQ \| default=-1
  - --topN \| default=10
  - --expectedPt \| default=float("2.5897"
  - --scanMaxEvents \| default=-1
  - --rankOrder \| default="largest"
  - --hitMatchTopK \| default=25
  - --outRoot \| default="tracks_display_simhits_multi.root"

### `view_tracks_event.py`
- **Examples:**
  - python3 view_tracks_event.py --input reco.root
  - python3 view_tracks_event.py --input reco.root --event 12
  - python3 view_tracks_event.py --input reco.root --hitsCollection GGTF_SenseWireHits
  - python3 view_tracks_event.py --input reco.root --hitsCollection OutputTracksGGTF --hitSource trackhits
- **Arguments / Properties (inferred):**
  - --input
  - --tree \| default="events"
  - --event \| default=-1
  - --hitsCollection \| default="OutputWireHitsGGTF"
  - --autoDetectHits \| If set, auto-detect hits collection even if --hitsCollection is provided.
  - --digiCollection \| default="DCHDigi2Collection"
  - --trackCollection \| default="GenFitTracks"
  - --trackStyle \| default="helix"
  - --Bz \| default=2.0 \| B-field along z [T] for helix drawing (default: 2.0;
  - --assumeQ \| default=-1
  - --outRoot \| default="tracks_display.root" \| Output ROOT file for histos + canvases

<!-- BEGIN AUTOREADME GENERATED -->
<!-- Generated by testTrackFinder-autoreadme-v4. Do not hand-edit inside this block. -->

# scripts/ generated file inventory

This section is auto-generated from project classification, per-file DOC blocks, and conservative heuristics.

Project rule: curated workflow docs remain authoritative. This generated content is an inventory and maintenance aid.

## Regenerate

```bash
python3 scripts/autoreadme.py --root . --write
```

DOC blocks are preferred over heuristics. Use `Status:` and `Tags:` fields for classification.

## ✅ Authoritative

| File | Summary / purpose | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| `analyze_job.sh`<br><sub>DOC</sub> | Condor worker wrapper that runs pT-resolution grid analysis on a reco-output campaign and copies the summary ROOT file to EOS.<br><sub>Doc: docs/workflow.md</sub> | ./analyze_job.sh INPUT_DIR EOS_OUT [TRACK_COLL] [HIT_COLL] [QUALITY_CUT] [MIN_PHISPAN] [MIN_CHORDXY] [MAX_CIRCLECOND] [CENTRAL_FRAC]<br>./analyze_job.sh --inputDir INPUT_DIR --eosOut EOS_OUT --trackCollection GenFitTracks --hitCollection OutputWireHitsGGTF --qualityCut none --minPhiSpan 0.06 --minChordXY 500.0 --maxCircleCond 1e6 --centralFrac 0.95 | scripts/analyze_pt_resolution_grid.py, configs/condor/analyze.condor, configs/condor/analyze_CF25_Au2p227matched.condor, configs/condor/analyze_W20_Au0p3_defaultlike.condor, scripts/compare_pt_resolution_grid.py, scripts/summarize_ptres_improvement.py | calls:analyze_pt_resolution_grid.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:OutputWireHitsGGTF<br>uses:eos<br>uses:xrootd |
| `analyze_pt_resolution_grid.py`<br><sub>DOC</sub> | Reduce eta- and pT-organized reco ROOT outputs into a single pT-resolution summary ROOT file with resolution graphs, diagnostics, and a summary TTree.<br><sub>Doc: README.md, docs/workflow.md</sub> | python3 scripts/analyze_pt_resolution_grid.py --inputDir RECO_DIR --outRoot PTRES.root<br>python3 scripts/analyze_pt_resolution_grid.py --inputDir RECO_DIR --outRoot PTRES.root --trackCollection GenFitTracks --hitCollection OutputWireHitsGGTF --qualityCut none --minPhiSpan 0.06 --minChordXY 500.0 --maxCircleCond 1e6 --centralFrac 0.95 | scripts/scan_pt_time_by_event.py, scripts/analyze_job.sh, scripts/compare_pt_resolution_grid.py, scripts/summarize_ptres_improvement.py, scripts/export_root_plots.py | calls:scripts/analyze_pt_resolution_grid.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:OutputWireHitsGGTF<br>import:ROOT<br>import:argparse<br>import:array<br>import:ctypes<br>import:math<br>import:os<br>import:random |
| `compare_pt_resolution_grid.py`<br><sub>DOC</sub> | Compare two pT-resolution summary ROOT files, such as CF vs W variants, by producing overlay, ratio, and diagnostic representativeness products.<br><sub>Doc: README.md, docs/workflow.md</sub> | python3 scripts/compare_pt_resolution_grid.py --a A_ptres.root --b B_ptres.root --out compare_A_vs_B.root --tagA A --tagB B<br>python3 scripts/compare_pt_resolution_grid.py --a CF_ptres.root --b W_ptres.root --out compare_CF_vs_W.root --tagA CF --tagB W | scripts/analyze_pt_resolution_grid.py, scripts/analyze_job.sh, scripts/summarize_ptres_improvement.py, scripts/export_root_plots.py | calls:scripts/compare_pt_resolution_grid.py<br>import:ROOT<br>import:argparse<br>import:ctypes<br>import:math<br>uses:eos |
| `export_root_plots.py`<br><sub>DOC</sub> | Recursively export plottable ROOT objects from analysis/comparison ROOT files to PNG and PDF while preserving the ROOT directory structure.<br><sub>Doc: docs/workflow.md</sub> | python3 scripts/export_root_plots.py --input INPUT.root --outdir OUTDIR<br>python3 scripts/export_root_plots.py --input INPUT.root --outdir OUTDIR --logy --logz --width 1200 --height 900 | scripts/analyze_pt_resolution_grid.py, scripts/compare_pt_resolution_grid.py, scripts/summarize_ptres_improvement.py, artifacts/analysis/ | import:ROOT<br>import:__future__<br>import:argparse<br>import:os<br>import:pathlib<br>import:re<br>import:sys<br>uses:eos |
| `make_filelist.sh`<br><sub>DOC</sub> | Build the XRootD input file list for reco Condor submission by scanning selected eta directories under a gun-sample campaign.<br><sub>Doc: docs/workflow.md</sub> | bash scripts/make_filelist.sh [BASE_DIR] [OUT_FILE] | scripts/submit_reco.sh, configs/condor/reco.condor, scripts/reco_job.sh, scripts/condor_ddsim.sh, configs/condor/ddsim.condor | uses:condor<br>uses:eos |
| `make_runtime.sh`<br><sub>DOC</sub> | Build and validate the self-contained runtime.tgz bundle used by Condor reco jobs, including k4RecTracker libraries, Gaudi catalogs, Python config, GenFit2 libraries, steering files, and the GGTF ONNX model.<br><sub>Doc: README.md, docs/workflow.md</sub> | bash scripts/make_runtime.sh<br>K4RT_PREFIX=/afs/.../k4RecTracker GENFIT_LIB_DIR=/afs/.../genfit2/install/lib64 MODEL_PATH=/afs/.../model.onnx bash scripts/make_runtime.sh | scripts/submit_reco.sh, configs/condor/reco.condor, scripts/reco_job.sh, steering/runDCHTestTrackFinder.py, steering/local_chain.sh | gaudi:imports:Configurables<br>gaudi:topalg:GenFit2DCHFitter<br>gaudi:topalg:HelixFitter<br>gaudi:topalg:SHELL_CATALOG_HAS_GENFIT<br>gaudi:topalg:SimpleFitDCHFitter<br>gaudi:topalg:SimpleFitterAlg<br>gaudi:topalg:SimpleTrackFitterAlg<br>gaudi:topalg:TrackingConf<br>gaudi:topalg:libDCHdigi<br>gaudi:topalg:libTracking |
| `prepare_and_submit.sh`<br><sub>DOC</sub> | Authoritative DDSim gun-production submission wrapper that generates a pT/eta job grid, splits it into per-job JSON parameter files, builds the Condor queue list, and submits the DDSim campaign.<br><sub>Doc: README.md, docs/workflow.md</sub> | bash scripts/prepare_and_submit.sh<br>TRANSFER_COMPACT=1 bash scripts/prepare_and_submit.sh | scripts/mk_ddsim_grid.py, configs/condor/ddsim.condor, scripts/condor_ddsim.sh, scripts/make_filelist.sh, scripts/submit_reco.sh | calls:scripts/mk_ddsim_grid.py<br>uses:condor<br>uses:eos |
| `reco_job.sh`<br><sub>DOC</sub> | Authoritative HTCondor worker wrapper for one DCH reco job, staging geometry/runtime/model inputs, running k4run, validating GenFit/GGTF output, stamping provenance, and copying the final ROOT file to EOS.<br><sub>Doc: docs/workflow.md</sub> | ./reco_job.sh INFILE OUTDIR COMPACT_XML [FITTER] [GF_USE_MAT_ARG] [STAGE] [FIT_OUT] [K4REL] [TGEO_FILE] | configs/condor/reco.condor, scripts/submit_reco.sh, scripts/make_runtime.sh, steering/runDCHTestTrackFinder.py, scripts/stamp_pipeline_metadata.py, scripts/analyze_pt_resolution_grid.py | gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:Tracks<br>gaudi:topalg:digi<br>gaudi:topalg:ggtf<br>import:sys<br>uses:eos<br>uses:k4run<br>uses:xrootd |
| `submit_reco.sh`<br><sub>DOC</sub> | Authoritative reco campaign submission wrapper that builds the gun-sample input file list and submits one Condor reco job per input ROOT file.<br><sub>Doc: README.md, docs/workflow.md</sub> | bash scripts/submit_reco.sh<br>IN_DIR=/eos/.../gun_samples/VARIANT OUT_DIR=/eos/.../reco_samples/VARIANT COMPACT_XML=/eos/.../VARIANT.xml TGEOFILE=/eos/.../VARIANT.root bash scripts/submit_reco.sh | scripts/make_filelist.sh, configs/condor/reco.condor, scripts/reco_job.sh, scripts/make_runtime.sh, steering/runDCHTestTrackFinder.py, scripts/analyze_job.sh | calls:make_filelist.sh<br>uses:condor<br>uses:eos |
| `summarize_ptres_improvement.py`<br><sub>DOC</sub> | Summarize pT-resolution improvement between two analysis ROOT files by matching eta/pT graph points and writing per-point, per-eta, global, text, and ROOT summary products.<br><sub>Doc: docs/workflow.md</sub> | python3 scripts/summarize_ptres_improvement.py --new NEW.root --old OLD.root --outdir OUTDIR --newLabel NEW --oldLabel OLD<br>python3 scripts/summarize_ptres_improvement.py --new CF_ptres.root --old W_ptres.root --outdir OUTDIR --newLabel CF --oldLabel W --methods central68,truncrms68,rms,mad | scripts/analyze_pt_resolution_grid.py, scripts/compare_pt_resolution_grid.py, scripts/export_root_plots.py, artifacts/analysis/ | import:ROOT<br>import:__future__<br>import:argparse<br>import:array<br>import:csv<br>import:ctypes<br>import:dataclasses<br>import:math<br>import:pathlib<br>import:re |

## 🛠️ Secondary

| File | Summary / purpose | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| `autoreadme.py`<br><sub>DOC</sub> | Project-aware README/index generator for testTrackFinder cleanup docs.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/autoreadme.py --root . --write<br>python3 scripts/autoreadme.py --root . --write --include-archive<br>python3 scripts/autoreadme.py --root . --check |  | calls:scripts/autoreadme.py<br>gaudi:topalg:acts<br>gaudi:topalg:artifacts<br>gaudi:topalg:digi<br>gaudi:topalg:genfit<br>gaudi:topalg:ggtf<br>gaudi:topalg:track<br>import:__future__<br>import:argparse<br>import:csv |
| `Calculate_Aucoating_thickness.py`<br><sub>DOC</sub> | Compute the gold coating thickness needed for a carbon-fiber wire, optionally with a Ni(P) underlayer, to match the AC resistance per unit length of a reference W+Au wire.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/Calculate_Aucoating_thickness.py --cf_d_um CF_DIAMETER_UM [--use_nip --t_nip_um NIP_THICKNESS_UM] [--f_max_GHz FREQ] [--k_skin K]<br>python3 scripts/Calculate_Aucoating_thickness.py --cf_r_um CF_RADIUS_UM [conductivity/material options] | material-budget closeout studies, CF-vs-W wire-variant design choices, geometry/material variant preparation, scripts/dch_x0_per_layer.py | calls:scripts/Calculate_Aucoating_thickness.py<br>import:argparse<br>import:math |
| `collect_knobs.py`<br><sub>DOC</sub> | WIP utility that scans Python argparse knobs and C++ Gaudi::Property declarations and exports a normalized knob inventory for future pipeline/config automation.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/collect_knobs.py --root . --out configs/auto_knobs.yaml --format yaml --verbose<br>python3 scripts/collect_knobs.py --root . --out configs/auto_knobs.json --format json --include-ext .py .cpp .h .hpp | steering/runDCHTestTrackFinder.py, steering/local_chain.sh, scripts/reco_job.sh, Tracking/components/GGTF_tracking.cpp, Tracking/components/GenFit2DCHFitter.cpp, configs/auto_knobs.yaml | calls:scripts/collect_knobs.py<br>gaudi:topalg:dchDigiVersion<br>gaudi:topalg:dchName<br>gaudi:topalg:dchSimHits<br>gaudi:topalg:dch_<br>gaudi:topalg:digitizer<br>gaudi:topalg:fitOut<br>gaudi:topalg:fitter<br>gaudi:topalg:genfit2<br>gaudi:topalg:ggtf |
| `condor_ddsim.sh`<br><sub>DOC</sub> | HTCondor worker wrapper for DDSim single-particle gun production, writing locally, validating, stamping metadata, and staging output ROOT files to EOS.<br><sub>Doc: README.md, docs/workflow.md</sub> | ./condor_ddsim.sh PARAMS_JSON COMPACT_XML EOS_OUT_DIR | scripts/stamp_ddsim_metadata.py, configs/condor/ddsim.condor, scripts/reco_job.sh, scripts/submit_reco.sh, steering/runDCHTestTrackFinder.py | import:math<br>import:sys<br>uses:eos<br>uses:xrootd |
| `dch_x0_per_layer.py`<br><sub>DOC</sub> | Compute an effective IDEA DCH radiation length for Delphes TrackCovariance cards from gas, field/guard wires, and configurable W-or-CF sense-wire material assumptions.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/dch_x0_per_layer.py --sense-core CF --sense-d-um 25 --au-um 1.4 --ag-um 0.3<br>python3 scripts/dch_x0_per_layer.py --sense-core W --sense-d-um 25 --au-um 0.3 --ag-um 0.3 --print-layers 112 | configs/delphes/*.tcl, scripts/Calculate_Aucoating_thickness.py, scripts/patch_trkCov_match_dch_material.py, material-budget closeout studies, CF-vs-W wire-variant studies | calls:scripts/dch_x0_per_layer.py<br>import:argparse |
| `debug_z_spur_event.py`<br><sub>DOC</sub> | Inspect one EDM4hep event for DCH z-spur pathologies by plotting wire-hit time versus z and grouping hits by linked MCParticle.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/debug_z_spur_event.py --input RECO_OR_DIGI.root --event EVENT_INDEX<br>python3 scripts/debug_z_spur_event.py --input RECO_OR_DIGI.root --event EVENT_INDEX --z-min ZMIN_MM --z-max ZMAX_MM --png OUT.png | scripts/view_tracks_event.py, scripts/view_simhits_event.py, scripts/inspect_events_pt_pathology.py, scripts/scan_pt_time_by_event.py | calls:scripts/debug_z_spur_event.py<br>gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:DCHDigi2SimLinkCollection<br>gaudi:topalg:DCHDigiCollection<br>gaudi:topalg:DCHDigiSimLinkCollection<br>gaudi:topalg:DCH_DigiCollection<br>import:argparse<br>import:matplotlib.pyplot<br>import:os<br>import:podio |
| `DelphesParamsOutput.py`<br><sub>DOC</sub> | Extract Delphes-style tracker efficiency and pT-resolution parameters from reco gun-sample grids by scanning GenFit/GGTF outputs and fitting a compact dpT/pT model.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/extract_delphes_tracker_params.py --inputDir RECO_DIR --outJson tracker_params.json --outCsv tracker_points.csv<br>python3 scripts/extract_delphes_tracker_params.py --inputDir RECO_DIR --trackCollection GenFitTracks --hitCollection OutputWireHitsGGTF --method truncrms68 --qualityCut none | scripts/scan_pt_time_by_event.py, configs/delphes/*.tcl, configs/tracker_params.json, scripts/patch_trkCov_match_dch_material.py, scripts/analyze_pt_resolution_grid.py | calls:scripts/extract_delphes_tracker_params.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:OutputWireHitsGGTF<br>gaudi:topalg:fit_mode<br>gaudi:topalg:n_points_fit<br>gaudi:topalg:per_eta_fits<br>gaudi:topalg:trackCollection<br>gaudi:topalg:track_eta_max_inferred<br>import:argparse<br>import:collections |
| `dump_covmatrix_one_event.py`<br><sub>DOC</sub> | Dump and reconstruct packed EDM4hep TrackState covariance matrices for one event, with special attention to correct CovMatrix6f lower-triangle ordering and Var(omega).<br><sub>Doc: scripts/README.md</sub> | python3 scripts/dump_covmatrix_one_event.py FILE.root --event EVENT_INDEX<br>python3 scripts/dump_covmatrix_one_event.py FILE.root --event EVENT_INDEX --prefix _GenFitTracks_trackStates. --raw | scripts/inspect_events_pt_pathology.py, scripts/scan_pt_time_by_event.py, scripts/debug_z_spur_event.py, steering/runDCHTestTrackFinder.py, Tracking/components/GenFit2DCHFitter.cpp | calls:scripts/dump_covmatrix_one_event.py<br>import:ROOT<br>import:argparse<br>import:math<br>uses:eos |
| `inspect_events_pt_pathology.py`<br><sub>DOC</sub> | Inspect selected reco events for pT/pathology debugging by printing GGTF 3D-hit spatial spans and GenFit TrackState parameters.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/inspect_events_pt_pathology.py --input RECO.root --events EVENT1,EVENT2,EVENT3<br>python3 scripts/inspect_events_pt_pathology.py --input RECO.root --events 718,838,302 --hits GGTF_3DHits --track GenFitTracks | scripts/scan_pt_time_by_event.py, scripts/dump_covmatrix_one_event.py, scripts/debug_z_spur_event.py, scripts/view_tracks_event.py, Tracking/components/GenFit2DCHFitter.cpp | calls:scripts/inspect_events_pt_pathology.py<br>gaudi:topalg:GGTF_3DHits<br>gaudi:topalg:GenFitTracks<br>import:ROOT<br>import:argparse<br>uses:eos |
| `mk_ddsim_grid.py`<br><sub>DOC</sub> | Generate a JSONL pT–eta parameter grid for DDSim single-particle gun Condor production.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/mk_ddsim_grid.py --out params_ddsim.jsonl<br>python3 scripts/mk_ddsim_grid.py --out params_ddsim.jsonl --pt-min 0.01 --pt-max 200 --pt-n 30 --etas "0.0,0.1,0.5,1.0,1.5,2.0" --nev 1000 --particle mu- | scripts/prepare_and_submit.sh, configs/condor/ddsim.condor, scripts/condor_ddsim.sh, scripts/make_filelist.sh | calls:scripts/mk_ddsim_grid.py<br>import:os |
| `patch_trkCov_match_dch_material.py`<br><sub>DOC</sub> | Patch Delphes TrackCovariance cards so DCH DetectorGeometry X0 values reproduce Geant4 DCH material-budget x/X0 versus \|eta\| for CF and W variants.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/patch_trkCov_match_dch_material.py --base-card BASE.tcl --g4-cf CF.root --g4-w W.root --outdir OUTDIR --npart 12 --hist hMatVsAbsEta_total | configs/delphes/*.tcl, scripts/dch_x0_per_layer.py, material-budget closeout ROOT outputs, Delphes TrackCovariance studies | calls:scripts/patch_trkCov_match_dch_material.py<br>gaudi:topalg:IDEA_DCH<br>import:ROOT<br>import:argparse<br>import:numpy<br>import:uproot<br>uses:eos |
| `plot_mcparticles_pt.py`<br><sub>DOC</sub> | Convert selected MCParticle truth momentum and reconstructed TrackState curvature information into compact ROOT diagnostic TTrees for pT/source debugging.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/pt_diagnostics_to_root.py --input RECO.root --out pt_diagnostics.root<br>python3 scripts/pt_diagnostics_to_root.py --input RECO.root --out pt_diagnostics.root --pdg 13 --pdg-abs --trackstate-prefix _GenFitTracks_TrackStates | scripts/scan_pt_time_by_event.py, scripts/inspect_events_pt_pathology.py, scripts/dump_covmatrix_one_event.py, scripts/plot_pt_from_trackstate_time.py, steering/runDCHTestTrackFinder.py | calls:scripts/pt_diagnostics_to_root.py<br>gaudi:topalg:GenFit<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates<br>gaudi:topalg:trackState<br>gaudi:topalg:trackStates<br>import:argparse<br>import:awkward<br>import:numpy<br>import:uproot |
| `plot_pt_from_trackstate_time.py`<br><sub>DOC</sub> | Plot pT values stored in EDM4hep TrackState.time for a selected track collection, with flexible event selection, filtering, and histogram binning.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/plot_pt_from_trackstate_time.py -i RECO.root --coll GenFitTracks --bins 80 -o pt.png<br>python3 scripts/plot_pt_from_trackstate_time.py -i RECO.root --coll GenFitTracks --bins 0:200:200 --logy -o pt_0_200_logy.png | scripts/pt_diagnostics_to_root.py, scripts/inspect_events_pt_pathology.py, scripts/scan_pt_time_by_event.py, scripts/dump_covmatrix_one_event.py, steering/runDCHTestTrackFinder.py | calls:scripts/plot_pt_from_trackstate_time.py<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:TrackStates<br>gaudi:topalg:trackStates<br>import:ROOT<br>import:argparse<br>import:math<br>import:matplotlib<br>import:matplotlib.pyplot<br>import:numpy |
| `print_metadata.py`<br><sub>DOC</sub> | Print metadata-like ROOT trees from an EDM4hep/PODIO ROOT file for quick provenance inspection.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/print_metadata.py FILE.root | scripts/stamp_pipeline_metadata.py, scripts/stamp_ddsim_metadata.py, scripts/reco_job.sh, scripts/condor_ddsim.sh, steering/local_chain.sh | calls:scripts/print_metadata.py<br>import:ROOT<br>import:os<br>import:sys<br>uses:eos |
| `scan_pt_time_by_event.py`<br><sub>DOC</sub> | Scan one reco ROOT file event-by-event to extract pT from TrackState.time/omega, compute signed pT errors, and derive curvature-observability diagnostics from SenseWireHit geometry.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/scan_pt_time_by_event.py --input RECO.root --expectedPt PT_TRUE --stdout<br>python3 scripts/scan_pt_time_by_event.py --input RECO.root --expectedPt PT_TRUE --csv scan.csv --top 30 --type bad --metric rel | scripts/analyze_pt_resolution_grid.py, scripts/extract_delphes_tracker_params.py, scripts/inspect_events_pt_pathology.py, scripts/debug_z_spur_event.py, scripts/dump_covmatrix_one_event.py, Tracking/components/GGTF_tracking.cpp, Tracking/components/GenFit2DCHFitter.cpp | calls:scripts/scan_pt_time_by_event.py<br>gaudi:topalg:GGTF_SenseWireHits<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:OutputWireHitsGGTF<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:n_tracks_evt<br>gaudi:topalg:nstates_per_track_max<br>gaudi:topalg:nstates_per_track_med<br>gaudi:topalg:nstates_per_track_min |
| `stamp_ddsim_metadata.py`<br><sub>DOC</sub> | Stamp DDSim gun-production provenance into a generated EDM4hep ROOT file as JSON plus convenience ROOT keys.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/stamp_ddsim_metadata.py --root GUN.root --params-json JOB.json --compact-xml COMPACT.xml --cmd "ddsim ..." --theta-min THETA_MIN --theta-max THETA_MAX | scripts/condor_ddsim.sh, scripts/prepare_and_submit.sh, scripts/mk_ddsim_grid.py, scripts/print_metadata.py, downstream reco provenance checks | calls:scripts/stamp_ddsim_metadata.py<br>import:ROOT<br>import:argparse<br>uses:eos |
| `stamp_pipeline_metadata.py`<br><sub>DOC</sub> | Stamp general pipeline-stage provenance into a ROOT output file as a JSON payload plus convenience ROOT keys.<br><sub>Doc: scripts/README.md, workflow appendix</sub> | python3 scripts/stamp_pipeline_metadata.py --root OUTPUT.root --stage fit --cmd "k4run ..." --input INPUT.root --config CONFIG.xml --config model.onnx | scripts/reco_job.sh, steering/local_chain.sh, scripts/print_metadata.py, scripts/analyze_pt_resolution_grid.py, downstream closeout/reproducibility checks | calls:scripts/stamp_pipeline_metadata.py<br>import:ROOT<br>import:argparse<br>uses:eos<br>uses:k4run |
| `sweep_pt.sh`<br><sub>DOC</sub> | Legacy/secondary local pT-sweep helper that runs local_chain.sh over a small hand-coded eta≈0 gun-sample pT list.<br><sub>Doc: scripts/README.md</sub> | bash scripts/sweep_pt.sh | steering/local_chain.sh, steering/runDCHTestTrackFinder.py, scripts/submit_reco.sh, scripts/reco_job.sh, scripts/analyze_pt_resolution_grid.py | calls:local_chain.sh<br>uses:eos |
| `view_simhits_event.py`<br><sub>DOC</sub> | Create multi-event ROOT event-display products for GGTF/GenFit DCH reco events, with optional simhit overlays, helix/straight track drawing, sigma(pT)-ranked event selection, and nearest-simhit hit-matching diagnostics.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/view_tracks_event.py --input RECO.root --event EVENT_INDEX --outRoot tracks_display.root<br>python3 scripts/view_tracks_event.py --input RECO.root --topN 10 --expectedPt PT_TRUE --rankOrder largest --outRoot tracks_display_topN.root | scripts/debug_z_spur_event.py, scripts/inspect_events_pt_pathology.py, scripts/dump_covmatrix_one_event.py, scripts/scan_pt_time_by_event.py, Tracking/components/GGTF_tracking.cpp, Tracking/components/GenFit2DCHFitter.cpp | calls:scripts/view_tracks_event.py<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:GGTF<br>gaudi:topalg:GGTF_SenseWireHits<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:OutputWireHitsGGTF<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:n_states_in_track<br>gaudi:topalg:no_trackstate_prefix |
| `view_tracks_event.py`<br><sub>DOC</sub> | Build a single-event ROOT display for DCH reco debugging, showing GGTF/SenseWire-like hits, optional raw DCH digis, and GenFit track-state helix or straight-line overlays.<br><sub>Doc: scripts/README.md</sub> | python3 scripts/view_tracks_event.py --input RECO.root<br>python3 scripts/view_tracks_event.py --input RECO.root --event EVENT_INDEX --outRoot tracks_display.root<br>python3 scripts/view_tracks_event.py --input RECO.root --hitsCollection OutputWireHitsGGTF --digiCollection DCHDigi2Collection --trackCollection GenFitTracks --trackStyle helix --Bz 2.0 | scripts/view_tracks_event_simhits.py, scripts/debug_z_spur_event.py, scripts/inspect_events_pt_pathology.py, scripts/dump_covmatrix_one_event.py, scripts/scan_pt_time_by_event.py, Tracking/components/GGTF_tracking.cpp, Tracking/components/GenFit2DCHFitter.cpp | calls:scripts/view_tracks_event.py<br>gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:GGTF<br>gaudi:topalg:GGTF_SenseWireHits<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:OutputWireHitsGGTF<br>gaudi:topalg:TrackStates_begin<br>gaudi:topalg:TrackStates_end<br>gaudi:topalg:digi_collection<br>gaudi:topalg:n_states_in_track |

## 🕰️ Legacy

| File | Summary / purpose | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| `prepare_and_submit_CF25_Au2p227matched.sh`<br><sub>heuristic</sub> | Variant-specific older wrapper.<br><sub>Doc: archive note</sub> |  |  | calls:scripts/mk_ddsim_grid.py<br>uses:condor<br>uses:eos |
| `prepare_and_submit_W20_Au0p3_defaultlike.sh`<br><sub>heuristic</sub> | Variant-specific older wrapper.<br><sub>Doc: archive note</sub> |  |  | calls:scripts/mk_ddsim_grid.py<br>uses:condor<br>uses:eos |

## 📦 Archive candidate

| File | Summary / purpose | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| `cglenn.cc`<br><sub>heuristic</sub> | Unclear workflow role; archive unless demonstrably active.<br><sub>Doc: none unless still active</sub> |  |  |  |

## ⚠️ Unknown / needs classification

| File | Summary / purpose | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| `condor_submit_logs_summary.txt`<br><sub>heuristic</sub> |  |  |  |  |

## Details

### `analyze_job.sh`

- **Status:** Authoritative
- **Purpose:** Condor worker wrapper for pT-resolution analysis.
- **Inputs:** Reco campaign directory containing eta_* subdirectories with reco_*.root files; analyze_pt_resolution_grid.py staged in the worker directory; optional runtime.tgz; Key4HEP/ROOT environment.
- **Outputs:** Local ptres_<cluster>_<process>.root summary file copied to EOS_OUT with xrdcp.
- **Collections:** Reads TRACK_COLL, normally GenFitTracks; reads HIT_COLL, normally OutputWireHitsGGTF; writes analysis ROOT objects produced by scripts/analyze_pt_resolution_grid.py.
- **Tags:** analysis, authoritative, closeout, condor, eos, genfittracks, pt-resolution, root
- **Notes:** This is the batch-side analysis wrapper, not the reco job wrapper., Keep the analysis cuts identical between detector/material variants when producing CF-vs-W closeout comparisons., The script accepts both positional arguments and explicit flags so campaign-specific Condor files can remain readable., If runtime.tgz is present, it is unpacked before analysis, but the analysis script must still be available as analyze_pt_resolution_grid.py in the worker directory or staged runtime., The output ROOT file is first written locally, checked for nonzero size, then copied to EOS using xrdcp., This script intentionally sources the same Key4HEP nightly family used by reco so ROOT/EDM dictionary behavior stays consistent.

**Examples**

- ./analyze_job.sh \
- /eos/.../reco_samples2/CF25_Au2p227matched \
- /eos/.../final_analysis/CF25_Au2p227matched_ptres.root \
- GenFitTracks OutputWireHitsGGTF none 0.06 500.0 1e6 0.95

**Arguments / properties from DOC block**

- INPUT_DIR / --inputDir: reco output campaign directory to analyze; expected to contain eta_* folders.
- EOS_OUT / --eosOut: final EOS ROOT output path for the pT-resolution summary.
- TRACK_COLL / --trackCollection: reconstructed track collection to analyze; default GenFitTracks.
- HIT_COLL / --hitCollection: hit collection used by the analysis scanner; default OutputWireHitsGGTF.
- QUALITY_CUT / --qualityCut: event/track quality mode passed to analysis; allowed values are none, curv, curv_circle.
- MIN_PHISPAN / --minPhiSpan: minimum phi span used by curvature-observability diagnostics; default 0.06.
- MIN_CHORDXY / --minChordXY: minimum transverse chord length in mm used by diagnostics; default 500.0.
- MAX_CIRCLECOND / --maxCircleCond: maximum accepted circle-fit condition number for diagnostics; default 1e6.
- CENTRAL_FRAC / --centralFrac: central fraction used for robust/truncated statistics; default 0.95.

**Environment knobs inferred**

  - K4REL \| default=2026-04-22
  - TRACK_COLL \| default=${TRACK_COLL
  - HIT_COLL \| default=${HIT_COLL
  - QUALITY_CUT \| default=${QUALITY_CUT
  - MIN_PHISPAN \| default=${MIN_PHISPAN
  - MIN_CHORDXY \| default=${MIN_CHORDXY
  - MAX_CIRCLECOND \| default=${MAX_CIRCLECOND
  - CENTRAL_FRAC \| default=${CENTRAL_FRAC

### `analyze_pt_resolution_grid.py`

- **Status:** Authoritative
- **Purpose:** Reduce reco outputs into summary ROOT with by-eta, by-method, and diagnostics.
- **Inputs:** Reco campaign directory containing eta_* subdirectories with reco_*.root files whose filenames encode true pT as _pt<value>; each file is scanned by scan_pt_time_by_event.scan_file().
- **Outputs:** ROOT summary file containing byEta graphs, byMethod graphs, diagnostics graphs, log-scale canvases, relative-error graphs, and a summary TTree.
- **Collections:** Reads trackCollection, normally GenFitTracks; reads hitCollection, normally OutputWireHitsGGTF; writes ROOT objects under byEta/, byMethod/, diagnostics/, plus TTree summary.
- **Tags:** analysis, authoritative, closeout, diagnostics, eta-grid, genfittracks, pt-resolution, reco-summary, root
- **Notes:** Expected input layout is RECO_DIR/eta_+X.XX/reco_*.root. Directories not matching eta_<signed number> are ignored., True pT is parsed from the reco filename using the _pt<value> token, so campaign naming must preserve that token.

**Examples**

- python3 scripts/analyze_pt_resolution_grid.py \
- inputDir /eos/.../reco_samples2/CF25_Au2p227matched \
- outRoot /eos/.../final_analysis/CF25_Au2p227matched_ptres.root \
- trackCollection GenFitTracks \
- hitCollection OutputWireHitsGGTF \
- qualityCut none \
- minPhiSpan 0.06 \
- minChordXY 500.0 \
- maxCircleCond 1e6 \
- centralFrac 0.95

**Arguments / properties inferred**

  - --inputDir \| Reco base dir containing eta_* subdirs
  - --outRoot \| Output ROOT file
  - --trackCollection \| default="GenFitTracks"
  - --hitCollection \| default="OutputWireHitsGGTF"
  - --minPhiSpan \| default=0.06
  - --minChordXY \| default=500.0
  - --maxCircleCond \| default=1e6
  - --centralFrac \| default=0.95
  - --qualityCut \| default="none"
  - --maxFilesPerEta \| default=0
  - --diagBootstrap \| default=200 \| Bootstrap samples for median-type error bars
  - --diagBootstrapSeed \| default=12345 \| Seed base for diagnostic bootstrap RNG
  - --methodBootstrap \| default=300
  - --methodBootstrapSeed \| default=54321 \| Seed base for method bootstrap RNG
  - --methodBootstrapCap \| default=5000
  - --maxRelErrWarn \| default=0.5

### `compare_pt_resolution_grid.py`

- **Status:** Authoritative
- **Purpose:** Compare two pT-resolution summary ROOT outputs.
- **Inputs:** Two ROOT files produced by scripts/analyze_pt_resolution_grid.py, each containing byEta/, byMethod/, diagnostics/, and summary TTree products.
- **Outputs:** ROOT comparison file containing compare/byEta overlays and ratios, compare/byMethod overlays and per-eta ratios, diagnostic overlays, diagnostic ratios, pass-fraction comparisons, and a diag_compare TTree.
- **Collections:** None; reads ROOT analysis products rather than EDM4hep event collections. Expected graph names include byEta/<eta>/gr_rms, gr_madsigma, gr_central68, gr_truncrms68, gr_meanAbs, and gr_medianAbs.
- **Tags:** authoritative, cf-vs-w, closeout, comparison, diagnostics, material-variants, pt-resolution, ratio-plots, root
- **Notes:** Ratio graphs are A/B and are filled only where both files contain finite values at matching pT points and the B value is nonzero., The comparison is only physically meaningful when A and B were produced with the same reco knobs, same analysis quality cuts, same eta/pT grid, and comparable event statistics., For CF-vs-W closeout plots, use the CF material variant as A and the W/default-like variant as B if you want ratios below one to mean improved pT resolution., The diagnostic section is designed to distinguish representative detector/material effects from changes driven by selection survivorship or algorithmic acceptance differences., The derived passFrac is n_quality/n_usable from the summary TTree and is compared separately from the resolution estimators., The diag_compare TTree stores per-(eta,pT) diagnostic A/B values, differences, ratios, and a simple suspect flag based on configurable tolerances., Missing eta directories, missing methods, or missing pT points are handled gracefully; the script writes comparisons only for objects that exist., The output ROOT file is intended as the main input to closeout plotting/export via scripts/export_root_plots.py and to numerical summaries via scripts/summarize_ptres_improvement.py.

**Examples**

- python3 scripts/compare_pt_resolution_grid.py \
- a /eos/.../CF25_Au2p227matched_ptres.root \
- b /eos/.../W20_Au0p3_defaultlike_ptres.root \
- out /eos/.../compare_CF25_Au2p227matched_vs_W20_Au0p3_defaultlike.root \
- tagA CF25_Au2p227matched \
- tagB W20_Au0p3_defaultlike

**Arguments / properties inferred**

  - --a
  - --b
  - --out \| Output ROOT comparison file
  - --tagA \| default="A"
  - --tagB \| default="B"
  - --xRound \| default=6 \| Rounding digits for matching pT points
  - --diagAbsTolPassFrac \| default=0.05
  - --diagRelTolPassFrac \| default=0.10
  - --diagAbsTolFrac \| default=0.05 \| Abs tolerance for frac_* diagnostic differences.
  - --diagRelTolMed \| default=0.25 \| Rel tolerance for med_* diagnostic ratios deviation \|A/B - 1\|.

### `export_root_plots.py`

- **Status:** Authoritative
- **Purpose:** Recursively export ROOT objects to PNG/PDF.
- **Inputs:** ROOT file containing canvases, histograms, profiles, graphs, multigraphs, efficiencies, stacks, or other drawable ROOT objects.
- **Outputs:** PNG and PDF files for each rendered object, written under OUTDIR with subdirectories mirroring the input ROOT directory layout.
- **Collections:** None; reads ROOT analysis objects rather than EDM4hep collections. TTree and TNtuple objects are intentionally skipped.
- **Tags:** analysis, authoritative, closeout, export, pdf, plotting, png, root
- **Notes:** Existing TCanvas objects are saved directly; other supported objects are drawn on a fresh batch-mode canvas., The script supports TH1/TH2/TH3, TProfile/TProfile2D/TProfile3D, TGraph, TMultiGraph, TEfficiency, THStack, and generic objects with a Draw method., TTree and TNtuple objects are skipped because they are data containers, not directly meaningful static plots., Output filenames are sanitized from ROOT object names to avoid filesystem-problematic characters., Use this after pT-resolution analysis or CF-vs-W comparison ROOT production to create reviewable closeout plot directories., Generated PNG/PDF outputs should live under artifacts/analysis/ or another generated-output area, not active source directories.

**Examples**

- python3 scripts/export_root_plots.py \
- --input /eos/.../compare_CF_vs_W.root \
- --outdir artifacts/analysis/compare_CF_vs_W_plots \
- --logy

**Arguments / properties inferred**

  - --input \| Input ROOT file
  - --outdir \| Output directory
  - --logy \| Use log-y for 1D histograms/graphs where sensible
  - --logz \| Use log-z for 2D/profile2D histograms where sensible
  - --width \| default=1000 \| Canvas width
  - --height \| default=800 \| Canvas height

### `make_filelist.sh`

- **Status:** Authoritative
- **Purpose:** Discover eta-organized input ROOT files and build submission file list.
- **Inputs:** EOS or local gun-sample campaign directory containing eta_<+X.XX> or eta<+X.XX> subdirectories with ROOT files.
- **Outputs:** Sorted unique text file containing one ROOT input path per line, converted to root://eosuser.cern.ch// URLs for EOS paths.
- **Collections:** None; this is a file-discovery helper and does not inspect EDM4hep collections.
- **Tags:** authoritative, condor, eos, filelist, gun-samples, reco, submission, xrootd
- **Notes:** This script is authoritative for preparing the reco Condor queue input list, but it is campaign-specific in the sense that the ETAS array is currently hard-coded., It checks both eta_<tag> and eta<tag> directory naming conventions, where tag is formatted as %+0.2f, such as +1.00., EOS POSIX paths are converted to XRootD URLs so worker nodes can read inputs robustly., Missing eta directories are warnings, not fatal errors, so always check the final path count before submitting reco., If a campaign uses a different eta grid, update ETAS or replace this script with a flag-driven eta-list version before production submission.

**Examples**

- bash scripts/make_filelist.sh \
- /eos/user/c/cglenn/gun_samples/1_29_2026/100umCF_0.313474umAu \
- filelist.txt

**Environment knobs inferred**

  - BASE_DIR \| default=/eos/user/c/cglenn/gun_samples/1_29_2026/100umCF_0.313474umAu
  - OUT_FILE \| default=filelist.txt

### `make_runtime.sh`

- **Status:** Authoritative
- **Purpose:** Build worker-node runtime bundle and validate plugin usability.
- **Inputs:** Built/installed k4RecTracker tree, k4RecTracker plugin libraries, Gaudi component catalogs, Tracking Python configuration, GenFit2 shared libraries, runDCHTestTrackFinder.py, optional local_chain.sh, and model.onnx.
- **Outputs:** runtime.tgz containing runtime/lib64, runtime/lib, runtime/share, runtime/python, runtime/models/model.onnx, runtime/runDCHTestTrackFinder.py, and optionally runtime/local_chain.sh.
- **Collections:** None; this is a runtime packaging/validation script and does not inspect EDM4hep collections.
- **Tags:** authoritative, condor, gaudi, genfit2, ggtf, k4rectracker, onnx, packaging, reco, runtime
- **Notes:** This is the authoritative runtime-packaging step for the maintained reco Condor pipeline., Run this after rebuilding k4RecTracker, updating GenFit2, changing the GGTF model, or changing the steering that must be staged to worker nodes., The script prefers installed libraries but falls back to build-tree libraries for required plugins such as libTracking.so and libDCHdigi.so., Gaudi catalogs, *.components*, *.confdb, PCM/rootmap files, and relevant XML/conf plugin metadata are harvested because worker-node component discovery is otherwise fragile., A Python sitecustomize shim is bundled only to avoid import-time crashes from missing dynamic Configurables; real plugin/library/catalog availability is still checked separately., The runtime usability check requires core plugin libraries to load and at least one fitter path to be evidenced by catalogs or Python-level importability., If this script fails, do not submit reco jobs; fix the library/catalog/model/steering problem first.

**Examples**

- cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder
- bash scripts/make_runtime.sh

**Environment knobs inferred**

  - K4RT_PREFIX \| default=/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker
  - K4RT_INSTALL_DIR \| default=$K4RT_PREFIX/install
  - K4RT_BUILD_DIR \| default=$K4RT_PREFIX/build
  - K4RT_PY_INSTALL \| default=$K4RT_INSTALL_DIR/python
  - K4RT_PY_SRC_FALLBACK \| default=$K4RT_PREFIX/Tracking
  - GENFIT_LIB_DIR \| default=/afs/cern.ch/user/c/cglenn/FCCWork/genfit2/install/lib64
  - MODEL_PATH \| default=$K4RT_PREFIX/Tracking/test/testTrackFinder/model.onnx
  - TESTTRACKFINDER_DIR \| default=$K4RT_PREFIX/Tracking/test/testTrackFinder
  - RUN_STEERING \| default=$TESTTRACKFINDER_DIR/runDCHTestTrackFinder.py
  - LOCAL_CHAIN_SRC \| default=$TESTTRACKFINDER_DIR/local_chain.sh

### `prepare_and_submit.sh`

- **Status:** Authoritative
- **Purpose:** Submission wrapper for DDSim gun-production campaigns.
- **Inputs:** Hard-coded COMPACT_XML detector variant, hard-coded OUT_DIR EOS campaign destination, scripts/mk_ddsim_grid.py, configs/condor/ddsim.condor or scripts/ddsim.condor depending on local layout, and scripts/condor_ddsim.sh through the Condor submit file.
- **Outputs:** params/job_*.json per-job parameter files, params_ddsim.jsonl grid file, scripts/queue_items.txt Condor queue list, HTCondor DDSim jobs, and generated gun-sample ROOT files under OUT_DIR/eta_<eta>/.
- **Collections:** None directly; submitted DDSim jobs produce EDM4hep ROOT files whose downstream reco expects DCHCollection and related SimTrackerHit collections from the configured compact geometry.
- **Tags:** authoritative, condor, ddsim, eos, gun-production, parameter-grid, submission, upstream
- **Notes:** This is the authoritative high-level submission entry point for DDSim gun-sample production in the current testTrackFinder workflow., Update COMPACT_XML and OUT_DIR together for each detector/material variant so produced gun samples are clearly tied to the intended geometry., The eta and pT grid here must remain synchronized with downstream make_filelist.sh, reco submission, analysis, and comparison expectations., The script clears params/job_*.json and scripts/queue_items.txt before regenerating them, so do not store hand-written files there., TRANSFER_COMPACT=0 is preferred when the worker can read the EOS XML reliably; TRANSFER_COMPACT=1 is useful when Condor file transfer is safer for a specific campaign., The printed condor_submit command appends submit-time variables such as OUT_DIR, COMPACT_XML_ARG, and TRANSFER_COMPACT to the DDSim submit description.

**Examples**

- cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder
- bash scripts/prepare_and_submit.sh

**Environment knobs inferred**

  - TRANSFER_COMPACT \| default=0

### `reco_job.sh`

- **Status:** Authoritative
- **Purpose:** Condor worker wrapper for one reco job.
- **Inputs:** One DDSim gun-sample EDM4hep ROOT file, EOS reco output directory, compact DD4hep XML, runtime.tgz, bundled GGTF model.onnx, optional matching TGeo ROOT geometry, and a pinned Key4HEP nightly release.
- **Outputs:** Local reco_<input>.root copied to OUTDIR/<eta_dir>/reco_<input>.root on EOS; optional failure log under OUTDIR/<eta_dir>/logs/; provenance metadata stamped into final and any intermediate stage outputs when available.
- **Collections:** Reads DCHCollection by default; writes the cumulative requested stage output, normally DCHDigi2Collection/DCH_DigiCollection, CDCHTracks/GGTF output, OutputWireHitsGGTF/GGTF_3DHits where configured by steering, and GenFitTracks when FITTER=genfit2 and STAGE=fit.
- **Tags:** authoritative, condor, dch, eos, genfit2, ggtf, k4run, key4hep, metadata, reco, worker, xrootd
- **Notes:** This is the authoritative worker-side reco job used by the maintained Condor reco pipeline., It is intended to match the local_chain.sh physics/reco knob surface while adding Condor-safe staging, XRootD/EOS I/O, idempotent output checks, and failure-log preservation., runtime.tgz must be produced by scripts/make_runtime.sh before submission and must contain the steering file, libraries, catalogs, Python config, and model.onnx., For material-aware CF-vs-W comparisons, COMPACT_XML and TGEO_FILE must correspond to the same detector/material variant, and all reco knobs should remain fixed between variants., The script skips work if the expected EOS output already exists, so remove stale outputs explicitly before rerunning a changed configuration., A nonzero k4run return code is overridden only when the output ROOT file opens and contains events; inspect copied logs before trusting such cases., Full logs are copied to EOS when fatal/error patterns are detected or validation fails., The final collection check only verifies that the requested FIT_OUT appears among output branches; downstream pT analysis is still needed for physics validation.

**Examples**

- ./reco_job.sh \

**Environment knobs inferred**

  - FITTER \| default=genfit2
  - GF_USE_MAT_ARG \| default=1
  - STAGE \| default=fit
  - FIT_OUT \| default=auto
  - K4REL \| default=2026-01-11
  - TGEO_FILE \| default=/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03_100umCF_0.313474umAu.root
  - HOME \| default=$PWD
  - USER \| default=condor
  - LOGNAME \| default=condor
  - TERM \| default=xterm
  - STAMP_KEY \| default=pipeline_metadata_json
  - STAMP_CONFIGS \| default=1
  - TMPDIR \| default=${TMPDIR:-$PWD
  - SKIP_DIGI \| default=0
  - FIT_OUT \| default=$FIT_OUT
  - FITTER \| default=$FITTER
  - STAGE \| default=$STAGE
  - GGTF_LOG \| default=DEBUG
  - FITTER_LOG \| default=DEBUG
  - TIMEOUT_K4RUN \| default=0
  - MAX_HITS \| default=0
  - TBETA \| default=0.6
  - TD \| default=0.3
  - ONNX_CHUNK \| default=4096
  - GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE \| default=1
  - GGTF_MAX_ABS_D_MM \| default=30.0
  - GGTF_ZERO_MIN \| default=8
  - GGTF_WIRE_FRAC \| default=0.60
  - GGTF_PROMOTE_ZERO \| default=1
  - GGTF_SKIP_ZERO_SMALL \| default=1
  - GGTF_SKIP_ZERO_ALWAYS \| default=0
  - GGTF_TRUTH_GATE \| default=0
  - GGTF_KEEP_PDG \| default=13
  - GGTF_DROP_UNLINKED \| default=1
  - GGTF_WIRE_SIMLINK_COLL \| default=DCHDigi2SimLinkCollection
  - GGTF_TRACKS_OUT \| default=CDCHTracks
  - GF_USE_MAT \| default=$GF_USE_MAT_ARG
  - GF_DISABLE_ELOSS \| default=1
  - GF_DISABLE_ALL_MAT \| default=0
  - GF_HARD_DISABLE_MAT_IF_NO_GEO \| default=1
  - GF_BZ \| default=2.0
  - GF_PDG \| default=13
  - GF_REJECT_NEGATIVE_LABELS \| default=1
  - GF_SORT_HITS \| default=1
  - GF_DEDUP \| default=1
  - GF_DEDUP_TOL \| default=0.010
  - GF_MIN_HITS_PER_TRACK \| default=8
  - GF_MIN_MEASUREMENTS_TO_FIT \| default=6
  - GF_MIN_FITTED_POINTS_WITH_FI \| default=0
  - GF_MAX_CHI2_NDF \| default=10.0
  - GF_USE_KF_PREFIT \| default=1
  - GF_KF_MAX_ITERS \| default=16
  - GF_TRY_BOTH_MOM_DIRS \| default=1
  - GF_USE_DAF \| default=1
  - GF_DAF_MAX_ITERS \| default=12
  - GF_FALLBACK_TO_KF_IF_DAF_FAILS \| default=1
  - GF_USE_BIASED_STATE_FOR_PUBLISH \| default=1
  - GF_PUBLISH_STATE_CENTRAL_FRAC \| default=0.30
  - GF_PUBLISH_PT_MAX_GEV \| default=300.0
  - GF_INVALID_PT_SENTINEL \| default=-1.0
  - GF_OMEGA_VAR_GOOD \| default=1e-4
  - GF_OMEGA_VAR_BAD \| default=1.0
  - GF_POSITION_UNIT_SCALE \| default=0.1
  - GF_WIRE_HALF_LENGTH_MM \| default=2250.0
  - GF_MAX_DRIFT_MM \| default=7.0
  - GF_MAX_DRIFT_MM_FOR_HIT \| default=8.0
  - GF_MIN_DRIFT_ERR_MM \| default=0.10
  - GF_MAX_DRIFT_ERR_MM \| default=1.0
  - GF_WIRE_ANGLES_DEGREES \| default=0
  - GF_SKIP_IF_OBS_TOO_LOW \| default=0
  - GF_MIN_HITS_FOR_OBS \| default=10
  - GF_OBS_SIGMA_EFF_MM \| default=0.025
  - GF_OBS_MIN_PHISPAN_RAD \| default=0.006
  - GF_OBS_MIN_CHORD_MM \| default=20.0
  - GF_OBS_MIN_SAGITTA_MM \| default=0.015
  - GF_OBS_SCORE_MIN \| default=1.0
  - GF_SEED_ENDPOINT_K \| default=6
  - GF_SEED_TANGENT_K \| default=10
  - GF_SEED_POS_SIGMA_MM \| default=80.0
  - GF_SEED_MOM_SIGMA_GEV \| default=10.0

### `submit_reco.sh`

- **Status:** Authoritative
- **Purpose:** Main reco campaign submission wrapper.
- **Inputs:** Gun-sample campaign directory with eta_* ROOT files, compact DD4hep XML, matching TGeo ROOT geometry for material-aware GenFit, runtime.tgz in the Condor transfer context, reco.condor, reco_job.sh, and make_filelist.sh.
- **Outputs:** scripts/filelist.txt containing XRootD input paths, HTCondor reco jobs, logs under scripts/logs/reco, and final reco ROOT outputs under OUT_DIR/<eta_dir>/reco_<input>.root.
- **Collections:** Does not read collections directly; submitted jobs normally run DCHCollection -> DCHDigi2Collection/DCH_DigiCollection -> CDCHTracks -> GenFitTracks through steering/runDCHTestTrackFinder.py.
- **Tags:** authoritative, condor, dch, eos, genfit2, ggtf, key4hep, reco, submission, xrootd
- **Notes:** This is the authoritative high-level entry point for the maintained Condor reco pipeline., Run scripts/make_runtime.sh before submitting if k4RecTracker, GenFit2, steering, or the ONNX model changed., The script cd's into scripts/, expects reco.condor and make_filelist.sh there, and writes filelist.txt in that directory., The input list is built from IN_DIR by make_filelist.sh, so its internal eta list must match the gun campaign coverage., For CF-vs-W or other material comparisons, COMPACT_XML and TGEOFILE must match the same detector/material variant while all non-geometry reco knobs remain fixed., The submitted worker jobs are idempotent at the expected EOS output path; stale outputs must be removed manually before rerunning changed configurations., Check the printed sample inputs and final job count before trusting a large submission.

**Examples**

- IN_DIR=/eos/user/c/cglenn/gun_samples/1_29_2026/100umCF_0.313474umAu \
- OUT_DIR=/eos/user/c/cglenn/reco_samples2/1_29_2026/100umCF_0.313474umAu \
- COMPACT_XML=/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03_100umCF_0.313474umAu.xml \
- TGEOFILE=/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03_100umCF_0.313474umAu.root \
- FITTER=genfit2 GF_USE_MAT=1 STAGE=fit FIT_OUT=auto K4REL=2026-04-22 \
- bash scripts/submit_reco.sh

**Environment knobs inferred**

  - IN_DIR \| default=/eos/user/c/cglenn/gun_samples/1_29_2026/100umCF_0.313474umAu
  - OUT_DIR \| default=/eos/user/c/cglenn/reco_samples2/1_29_2026/100umCF_0.313474umAu
  - COMPACT_XML \| default=/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03_100umCF_0.313474umAu.xml
  - FITTER \| default=genfit2
  - FIT_OUT \| default=auto
  - GF_USE_MAT \| default=1
  - STAGE \| default=fit
  - EXTRA \| default=--fitterLog INFO
  - K4REL \| default=2026-04-22
  - TGEOFILE \| default=/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03_100umCF_0.313474umAu.root

### `summarize_ptres_improvement.py`

- **Status:** Authoritative
- **Purpose:** Build closeout improvement summaries and CSV/text/ROOT products.
- **Inputs:** Two pT-resolution analysis ROOT files, normally produced by scripts/analyze_pt_resolution_grid.py, containing eta-sliced TGraph/TGraphErrors/TGraphAsymmErrors objects with pT on the x-axis and resolution-like quantities on the y-axis.
- **Outputs:** improvement_per_point.csv, improvement_per_eta.csv, improvement_global_by_method.csv, summary.txt, and improvement_summary.root under OUTDIR.
- **Collections:** None; reads ROOT analysis graph objects rather than EDM4hep collections.
- **Tags:** analysis, authoritative, cf-vs-w, closeout, csv, improvement-summary, pt-resolution, root
- **Notes:** Improvement is defined as 100*(old-new)/old for metrics where smaller is better, so positive values mean the new/test file has smaller pT-resolution metric than the old/reference file., The script recursively reads all graph-like objects and infers the method name from the graph path/name using canonical substrings such as truncrms68, central68, meanabs, medianabs, mad, and rms., Eta is inferred from graph paths/names; graphs without an identifiable eta token are skipped., Matching is done by rounded eta and rounded pT keys, so etaRound/ptRound should be kept stable across closeout summaries., Per-point CSV rows preserve old/new values, errors, improvement percent, and source graph names for traceability., Per-eta summaries aggregate improvement distributions and also report net improvement from mean and median metric values., The ROOT output contains per-method improvement graphs/histograms versus eta plus a method_summary TTree., Use this after producing variant-specific pT-resolution summary ROOT files; use compare_pt_resolution_grid.py when you also need overlay/ratio plot products.

**Examples**

- python3 scripts/summarize_ptres_improvement.py \
- --new /eos/.../CF25_Au2p227matched_ptres.root \
- --old /eos/.../W20_Au0p3_defaultlike_ptres.root \
- --outdir artifacts/analysis/CF25_Au2p227matched_vs_W20_Au0p3_defaultlike_improvement \
- --newLabel CF25_Au2p227matched \
- --oldLabel W20_Au0p3_defaultlike \
- --methods central68,truncrms68,rms,madsigma

**Arguments / properties inferred**

  - --new \| New analysis ROOT file
  - --old \| Old analysis ROOT file
  - --outdir \| Output directory
  - --newLabel \| default="new" \| Label for new file
  - --oldLabel \| default="old" \| Label for old file
  - --etaRound \| default=3 \| Rounding digits for eta matching
  - --ptRound \| default=6 \| Rounding digits for pt matching
  - --methods \| default="" \| Comma-separated list of methods to keep, e.g. central68,truncrms68,rms,mad

### `autoreadme.py`

- **Status:** Secondary
- **Purpose:** Generate directory READMEs, DOCS_INDEX.md, and docs/chain.mmd from DOC blocks and heuristics.
- **Outputs:** Per-directory generated README files, DOCS_INDEX.md, and docs/chain.mmd.
- **Tags:** autoreadme, documentation, maintenance, testTrackFinder

**Arguments / properties inferred**

  - --root \| Path to Tracking/test/testTrackFinder root.
  - --write \| Actually write files.
  - --no-graph \| Skip docs/chain.mmd.
  - --check \| Validate DOC/status coverage.
  - --inject-stubs \| Insert DOC stubs into important files missing them.
  - --include-archive \| Include archive/ in scan.
  - --include-artifacts \| Include artifacts/ in scan.
  - --overwrite-curated \| Allow generated block insertion into curated/protected docs.
  - --all-dirs \| Generate README.md in every scanned directory, not only configured dirs.
  - --generated-readme-dir \| default=[] \| Directory where README.md generation is allowed. Can be repeated.
  - --classification-file \| default="" \| Optional external JSON/CSV classification file overriding built-ins.
  - --strict-status \| In --check mode, fail if any scanned file has unknown status.

### `Calculate_Aucoating_thickness.py`

- **Status:** Secondary
- **Purpose:** Side-study / materials utility.
- **Inputs:** Carbon-fiber core radius or diameter; material conductivities for Au, W, CF, and optional Ni(P); reference W+Au wire dimensions; frequency/skin-depth model parameters.
- **Outputs:** Printed engineering estimate of required Au coating thickness, total wire radius, skin depths, target and achieved AC resistance per length, and diminishing-returns warnings.
- **Collections:** None; this is a standalone wire-material calculation utility, not an EDM4hep/ROOT event processor.
- **Tags:** ac-resistance, carbon-fiber, gold-coating, material-budget, nickel-phosphorus, secondary, skin-depth, wire-materials
- **Notes:** This is a simplified AC-resistance matching model for wire-design studies, not a detailed electromagnetic field solver., The model approximates skin effect with t_eff = min(t, k_skin * skin_depth) and thin-shell effective area A_eff ≈ 2π R_outer t_eff.

**Examples**

- python3 scripts/Calculate_Aucoating_thickness.py --cf_d_um 25 --use_nip --t_nip_um 0.10 --f_max_GHz 2.0
- python3 scripts/Calculate_Aucoating_thickness.py --cf_d_um 100 --sigma_cf 4.0e4 --use_nip --t_nip_um 0.10 --f_max_GHz 2.0 --k_skin 3.0

**Arguments / properties inferred**

  - --cf_d_um \| Carbon fiber core diameter [µm]
  - --cf_r_um \| Carbon fiber core radius [µm]
  - --sigma_au \| default=4.10e7
  - --sigma_w \| default=1.79e7
  - --sigma_cf \| default=4.00e4
  - --sigma_nip \| default=1.5e6
  - --w_d_um \| default=20.0
  - --au_ref_t_um \| default=0.3
  - --f_max_GHz \| default=2.0
  - --k_skin \| default=3.0
  - --mu_r_au \| default=1.0
  - --mu_r_w \| default=1.0
  - --mu_r_cf \| default=1.0
  - --mu_r_nip \| default=1.0
  - --use_nip
  - --t_nip_um \| default=0.10
  - --tmax_factor \| default=50.0

### `collect_knobs.py`

- **Status:** Secondary
- **Purpose:** Knob/config collection helper.
- **Inputs:** Repository or workflow subtree containing Python scripts with parser.add_argument(...) calls and C++ headers/sources with Gaudi::Property<T> declarations.
- **Outputs:** YAML or JSON knob inventory with flat and grouped views; optional exports.sh file containing environment-variable defaults for selected knob prefixes.
- **Collections:** None; this is a static source/config introspection utility, not an EDM4hep/ROOT event processor.
- **Tags:** argparse, automation, config-audit, gaudi-property, knob-inventory, maintenance, secondary, wip
- **Notes:** This script is explicitly WIP and should be treated as an exploratory maintenance helper, not an authoritative pipeline runner., The intended long-term use is to help audit and eventually unify knob surfaces across ddsim, DCH digitization, GGTF_tracking, GenFit2DCHFitter, local wrappers, and Condor wrappers., Python parsing is regex-based and intentionally limited to common parser.add_argument(...) patterns; it will not safely understand arbitrary AST/metaprogramming., C++ parsing is regex-based and focused on Gaudi::Property<T> declarations; custom property wrappers may require new patterns., Duplicate knob names are expected in this project because the same concept can appear in steering, local wrappers, worker wrappers, and C++ components. Review duplicate warnings before trusting generated configs., Generated auto_knobs.yaml/json should be considered a diagnostic inventory until the project explicitly adopts it as a config contract., Do not use this script to silently overwrite hand-maintained configs for production CF-vs-W or pT-resolution closeout campaigns.

**Examples**

- python3 scripts/collect_knobs.py \
- root . \
- include-ext .py .cpp .h .hpp \
- out configs/auto_knobs.yaml \
- format yaml \
- exports configs/auto_knob_exports.sh \
- export-prefix gf_ ggtf_ dch_ \
- verbose

**Arguments / properties inferred**

  - ...
  - ...
  - ...
  - "..."/'...', ...
  - <args...>
  - {body}
  - --root \| Root directory to scan
  - --out
  - --format \| default=None
  - --include-ext \| default=[".py" \| File extensions to scan
  - --exclude-dir \| default=[".git" \| Directory names to exclude
  - --keep-first \| default=True
  - --keep-last \| On duplicate knob names: keep the last encountered.
  - --exports \| default=""
  - --export-prefix \| default=[]
  - --verbose \| default=False

### `condor_ddsim.sh`

- **Status:** Secondary
- **Purpose:** Condor worker wrapper for DDSim gun production, validation, metadata stamping, and EOS staging.
- **Inputs:** Per-job JSON parameter file containing pt, eta, p, theta, nev, particle, seed, phi_uniform, and theta_smear; compact DD4hep XML; EOS output directory base.
- **Outputs:** DDSim EDM4hep ROOT file named gun_eta<SIGNETA>_pt<PT>.root under EOS_OUT_DIR/eta_<SIGNETA>/, plus stamped DDsim provenance metadata when stamp_ddsim_metadata.py is available.
- **Collections:** Produces standard DDSim EDM4hep event content, including events and podio_metadata trees; downstream reco expects DCHCollection and other detector SimTrackerHit collections according to the compact geometry.
- **Tags:** condor, ddsim, edm4hep, eos, gun-production, metadata, secondary, xrootd
- **Notes:** This is a DDSim production wrapper, not the current authoritative reco wrapper., The script configures a particle gun using fixed momentum magnitude p, not energy; p should satisfy p/cosh(eta) ≈ pt., Output is first written to local worker scratch, then validated, optionally metadata-stamped, copied to EOS with xrdcp, and validated remotely., The filename tag uses pT, not energy: gun_eta<eta>_pt<pt>.root., If local or remote validation fails, the job retries once with the random seed incremented by 12345., Validation requires the output ROOT file to contain events and podio_metadata trees with at least one event branch., This script is useful historical infrastructure for gun-sample production, but should be kept separate from the current authoritative DCH reco/analysis closeout path.

**Examples**

- ./condor_ddsim.sh \
- params_eta+1.00_pt14.142.json \
- /eos/.../IDEA_o1_v03CF_2umAu.xml \
- /eos/user/c/cglenn/gun_samples/CF25_Au2p227matched

**Environment knobs inferred**

  - SCRATCH \| default=$PWD

### `dch_x0_per_layer.py`

- **Status:** Secondary
- **Purpose:** Material-budget / per-layer utility.
- **Inputs:** DCH radial bounds, He/isobutane gas fractions, total field/guard/sense wire counts, field/guard wire diameters, Ag coating thickness, sense-wire core material/diameter, and Au coating thickness.
- **Outputs:** Printed effective radiation length in meters, mixture X0 in g/cm^2, average density, per-component mass fractions, and optional identical per-layer X0 values.
- **Collections:** None; this is a standalone material-parameter utility, not an EDM4hep/ROOT event processor.
- **Tags:** carbon-fiber, dch, delphes, material-budget, radiation-length, secondary, track-covariance, tungsten, wire-materials, x0

**Examples**

- python3 scripts/dch_x0_per_layer.py \
- sense-core CF \
- sense-d-um 25 \
- au-um 1.4 \
- ag-um 0.3 \
- print-layers 112

**Arguments / properties inferred**

  - --rin-cm \| default=35.0
  - --rout-cm \| default=200.0
  - --f-he \| default=0.9
  - --f-iso \| default=0.1
  - --n-field \| default=229056
  - --n-guard \| default=58464
  - --n-sense \| default=56448
  - --field-d-um \| default=40.0
  - --guard-d-um \| default=50.0
  - --sense-core \| default="CF"
  - --sense-d-um \| default=25.0
  - --ag-um \| default=0.3
  - --au-um \| default=1.4
  - --no-displacement
  - --print-layers \| default=0

### `debug_z_spur_event.py`

- **Status:** Secondary
- **Purpose:** Debug suspicious z-spur or event-level pathology.
- **Inputs:** EDM4hep ROOT file readable by podio.root_io.Reader, one event index, DCH SenseWireHit collection, SenseWireHit-to-SimTrackerHit link collection, and optional MCParticles collection.
- **Outputs:** Terminal summary of wire-hit and link counts plus MCParticle-linked z/time ranges; PNG scatter plot of hit time versus z.
- **Collections:** Reads DCHDigi2Collection, DCH_DigiCollection, or DCHDigiCollection; reads DCHDigi2SimLinkCollection or DCHDigiSimLinkCollection; optionally reads MCParticles or MCParticle.
- **Tags:** dch, diagnostics, edm4hep, event-inspection, mc-links, plotting, podio, secondary, wire-hits, z-spur
- **Notes:** This is a diagnostic utility, not part of the production reco or pT-resolution reduction chain., Use it when an event display or pT scan suggests suspicious large-z structures, unusual timing, or multiple MCParticle contributions to one DCH event., The MC association is built through SenseWireHitSimTrackerHit links by mapping each wire hit object ID to the linked SimTrackerHit particle., If MCParticles is unavailable, the script still reports linked SimTrackerHit particle object IDs where possible, but PDG labels may be missing., The z cut is applied only to the plotted and summarized points after collection/link loading., Auto-detection supports both newer v02-style DCHDigi2Collection/DCHDigi2SimLinkCollection and older v01-style DCH_DigiCollection/DCHDigiSimLinkCollection., The output scatter uses color groups for linked MCParticle IDs, with a compact legend capped to avoid unreadable plots.

**Examples**

- python3 scripts/debug_z_spur_event.py \
- input /eos/.../reco_eta+1.00_pt14.142.root \
- event 37 \
- wire-coll DCHDigi2Collection \
- link-coll DCHDigi2SimLinkCollection \
- z-min -2500 \
- z-max 2500 \
- png debug_evt37_time_vs_z.png

**Arguments / properties inferred**

  - --input
  - --event
  - --wire-coll \| default="" \| SenseWireHit collection name
  - --link-coll \| default="" \| SenseWireHitSimTrackerHitLink collection name
  - --mc-coll \| default=""
  - --z-min \| default=None \| Optional z-min mm for focusing on spur region
  - --z-max \| default=None \| Optional z-max mm for focusing on spur region
  - --png \| default="" \| Output PNG for time-vs-z plot

### `DelphesParamsOutput.py`

- **Status:** Secondary
- **Purpose:** Delphes-related helper outside main reco closeout path.
- **Inputs:** Reco campaign directory with eta_* subdirectories and reco_*.root files whose names encode true pT as _pt<value>; each file is scanned with scan_pt_time_by_event.scan_file().
- **Outputs:** JSON report with inferred Delphes tracker parameters and fit diagnostics; CSV table of per-(eta,pT) efficiency/resolution/bias points; printed Tcl snippet with TRACK_ETA_MAX, TRACK_PT_MIN, TRACK_EFF_PLATEAU, RES_A, RES_B, and RES_C.
- **Collections:** Reads trackCollection, normally GenFitTracks; reads hitCollection, normally OutputWireHitsGGTF; does not write EDM4hep collections.
- **Tags:** delphes, efficiency, fastsim, genfittracks, ggtf, parameter-extraction, pt-resolution, secondary, tracker-params
- **Notes:** This is a Delphes/fastsim parameter-extraction helper, not the authoritative pT-resolution closeout reducer., The fitted model is dpT/pT = sqrt(A^2 + B^2*pt + (C*pt)^2), obtained by linearized weighted least squares on (dpT/pT)^2., Efficiency is defined as usable scanned results divided by n_scanned or n_ev for single-particle gun files; this is suitable for gun-grid studies but not a full physics-event tracking efficiency definition., True pT is parsed from the reco filename using the _pt<value> token, so campaign naming must preserve that token., Eta acceptance is inferred from eta_* directory names unless --overrideEtaMax is supplied., Use the same scanner cuts, qualityCut, method, and fit settings when comparing CF and W parameterizations., The printed Tcl snippet is intended for manual review before pasting into Delphes cards; do not blindly overwrite production cards without checking fit quality and point coverage., If --fitMode perEta is used, per-eta fits are diagnostic extras; the global fit remains the compact card-friendly parameterization.

**Examples**

- python3 scripts/extract_delphes_tracker_params.py \
- inputDir /eos/.../reco_samples2/CF25_Au2p227matched \
- outJson configs/tracker_params_CF25_Au2p227matched.json \
- outCsv artifacts/analysis/tracker_points_CF25_Au2p227matched.csv \
- trackCollection GenFitTracks \
- hitCollection OutputWireHitsGGTF \
- method truncrms68 \
- qualityCut none \
- fitMode global

**Arguments / properties inferred**

  - --inputDir \| Reco base dir containing eta_* subdirs
  - --outJson \| default="tracker_params.json" \| JSON report output
  - --outCsv \| default="tracker_points.csv" \| CSV table output
  - --trackCollection \| default="GenFitTracks"
  - --hitCollection \| default="OutputWireHitsGGTF"
  - --minPhiSpan \| default=0.06
  - --minChordXY \| default=500.0
  - --maxCircleCond \| default=1e6
  - --centralFrac \| default=0.95
  - --qualityCut \| default="none"
  - --method \| default="truncrms68" \| Which resolution estimator becomes dpT/pT used for the Delphes fit.
  - --ptPlateauMin \| default=5.0 \| pT threshold used to estimate plateau tracking efficiency
  - --effTurnonFrac \| default=0.5 \| Threshold fraction of plateau used to estimate TRACK_PT_MIN
  - --overrideEtaMax \| default=float("nan"
  - --fitMode \| default="global"
  - --minFitPt \| default=0.2

### `dump_covmatrix_one_event.py`

- **Status:** Secondary
- **Purpose:** Dump one-event covariance information for debugging.
- **Inputs:** EDM4hep/ROOT reco output file containing an events TTree and a TrackState covariance leaf such as _GenFitTracks_trackStates.covMatrix.values.
- **Outputs:** Terminal dump of detected tree/prefix/leaf metadata, inferred TrackState count, optional raw packed covariance values, reconstructed covariance matrix, and Var(omega).
- **Collections:** Reads GenFitTracks TrackState covariance leaves; common prefixes include _GenFitTracks_trackStates., GenFitTracks.trackStates., and AtIP variants.
- **Tags:** covariance, diagnostics, edm4hep, genfittracks, omega, pt-resolution, root, secondary, trackstate
- **Notes:** EDM4hep CovMatrix6f stores 21 values using packed lower-triangle ordering, not a flat row-major 6x6 matrix., The standard TrackState parameter order used here is d0, phi, omega, z0, tanLambda, time., Var(omega) is reconstructed as matrix element [2][2], which is important for checking pT/curvature uncertainty propagation., The script also supports 15-value packed 5x5 covariance blocks and attempts single-state triangular-size inference for unusual layouts., Use this for debugging suspicious covariance values, invalid pT states, bad omega uncertainties, or TrackState branch interpretation issues., This is a read-only diagnostic utility and should not modify reco outputs.

**Examples**

- python3 scripts/dump_covmatrix_one_event.py \
- /eos/.../reco_eta+1.00_pt14.142.root \
- event 0 \
- raw

**Arguments / properties inferred**

  - "file"
  - --event \| default=0
  - --prefix \| default="AUTO"
  - --raw \| Print raw packed values with indices
  - --max-states \| default=50 \| Safety cap if something looks weird

### `inspect_events_pt_pathology.py`

- **Status:** Secondary
- **Purpose:** Inspect events with pathological pT behavior.
- **Inputs:** Reco ROOT file containing an events TTree, a 3D hit collection with position leaves, and a reconstructed track collection with TrackState leaves.
- **Outputs:** Terminal report for each requested event showing hit count, r/z min/max/span, TrackState count, pT from TrackState.time, pT from 1/\|omega\|, omega, phi, tanLambda, D0, and Z0.
- **Collections:** Reads GGTF_3DHits by default; reads GenFitTracks TrackStates by default; auto-detects common TrackState branch prefixes for the selected track collection.
- **Tags:** diagnostics, event-inspection, genfittracks, ggtf, pt-pathology, root, secondary, trackstate
- **Notes:** This is a read-only event-level diagnostic utility for investigating suspicious pT estimates, large geometry spans, bad curvature values, or track-state publication issues., The script compares pT encoded in TrackState.time with pT inferred as 1/\|omega\|, which is useful for checking the project convention where pT may be stored in the time field.

**Examples**

- python3 scripts/inspect_events_pt_pathology.py \
- input /eos/.../reco_eta+1.00_pt14.142.root \
- events 718,838,302 \
- hits GGTF_3DHits \
- track GenFitTracks

**Arguments / properties inferred**

  - --input
  - --events \| Comma-separated event indices, e.g. 718,838,302
  - --hits \| default="GGTF_3DHits"
  - --track \| default="GenFitTracks"

### `mk_ddsim_grid.py`

- **Status:** Secondary
- **Purpose:** Campaign/grid-generation helper.
- **Inputs:** pT range, number of pT points, comma-separated eta list, event count per grid point, particle name, theta-smearing setting, and base random seed.
- **Outputs:** JSONL file with one DDSim job record per pT/eta point.
- **Collections:** None; this is a job-parameter generation utility and does not read or write EDM4hep collections.
- **Tags:** condor, ddsim, eta-grid, gun-production, jsonl, parameter-grid, pt-grid, secondary
- **Notes:** Each JSONL record contains pt, eta, p, theta, nev, particle, phi_uniform, theta_smear, seed, and job_id., Momentum magnitude is computed as p = pT*cosh(eta), and polar angle is computed as theta = 2*atan(exp(-eta))., The output is intended to be consumed by the DDSim Condor production pipeline, especially prepare_and_submit.sh, ddsim.condor, and condor_ddsim.sh., Keep the eta grid synchronized with make_filelist.sh and downstream reco/analysis expectations before launching a production campaign., Because pT spacing is logarithmic, pt-min must be positive and pt-n should be greater than one for normal production grids., This script defines upstream gun-sample coverage; changing it can invalidate direct comparisons unless reco and analysis are regenerated consistently.

**Examples**

- python3 scripts/mk_ddsim_grid.py \
- out configs/params/params_ddsim_CF25_Au2p227matched.jsonl \
- pt-min 0.01 \
- pt-max 200.0 \
- pt-n 30 \
- etas "0.0,0.1,0.5,1.0,1.5,2.0" \
- nev 1000 \
- particle mu- \
- seed0 1000000

**Arguments / properties inferred**

  - --out \| default="params_ddsim.jsonl" \| Output JSONL of job params
  - --pt-min \| default=0.01 \| min pT [GeV]
  - --pt-max \| default=200.0 \| max pT [GeV]
  - --pt-n \| default=30
  - --etas \| default="0.0 \| comma list of eta values
  - --nev \| default=1000 \| events per point
  - --particle \| default="mu-" \| gun particle PDG name
  - --phi-uniform \| default=True
  - --theta-smear \| default=0.0
  - --seed0 \| default=1_000_000 \| base RNG seed

### `patch_trkCov_match_dch_material.py`

- **Status:** Secondary
- **Purpose:** Side-study / materials/config patch helper.
- **Inputs:** Base Delphes Tcl card containing module TrackCovariance TrackSmearing with a DetectorGeometry block; Geant4 material-budget ROOT files for CF and W variants; optional histogram name.
- **Outputs:** Two patched Delphes Tcl cards, <tag>_CF.tcl and <tag>_W.tcl, with DCH X0 columns adjusted by radial partition.
- **Collections:** None; reads ROOT material-budget histograms and edits Delphes Tcl card geometry lines.
- **Tags:** cf-vs-w, dch, delphes, fastsim, geant4, material-budget, secondary, tcl, track-covariance, x0
- **Notes:** This script patches only the X0 column of existing "1 DCH ..." DetectorGeometry lines., It does not slice in z, does not duplicate DCH geometry lines, and does not change zmin/zmax/radius/thickness values., The fitted model approximates x/X0(\|eta\|) as cosh(\|eta\|) times the sum over crossed DCH layer thicknesses divided by effective partition X0., A layer is considered crossed when r_i*sinh(\|eta\|) < zmax_i., The fitted parameters are one effective X0 per contiguous radial partition, then each DCH line inherits the X0 value of its partition., Use DCH-only or appropriately isolated material-budget histograms; fitting total-detector material can incorrectly absorb non-DCH material into DCH X0., The output cards are generated artifacts and should be reviewed before being treated as maintained Delphes configs., This is a fastsim/material-matching helper and does not replace DD4hep/Geant4 material-budget validation.

**Examples**

- python3 scripts/patch_trkCov_match_dch_material.py \
- base-card configs/delphes/delphes_card_IDEAtrkCov.tcl \
- g4-cf /eos/.../output_eta_folded_CF_E15000MeV.root \
- g4-w  /eos/.../output_eta_folded_W_E15000MeV.root \
- outdir configs/delphes/generated \
- npart 12 \
- hist hMatVsAbsEta_total \
- tag IDEA_DCH

**Arguments / properties inferred**

  - --base-card
  - --g4-cf
  - --g4-w
  - --outdir
  - --npart \| default=12
  - --hist \| default=None
  - --tag \| default="IDEA_DCH"

### `plot_mcparticles_pt.py`

- **Status:** Secondary
- **Purpose:** Plot MC-particle pT distributions.
- **Inputs:** EDM4hep/ROOT file readable by uproot, containing MCParticles momentum branches and optionally reconstructed TrackState branches with omega/time/phi/tanLambda/D0/Z0.
- **Outputs:** ROOT diagnostics file with TTrees named mc, ts when TrackStates are found, and evt.
- **Collections:** Reads flattened MCParticles branches under MCParticles/MCParticles by default; auto-detects TrackState omega branches, preferably GenFitTracks-related prefixes.
- **Tags:** awkward, diagnostics, genfittracks, mcparticles, omega, pt, root, secondary, trackstate, uproot
- **Notes:** The mc tree contains one row per selected MCParticle with event, particle index, momentum components, pT, p, eta, phi, PDG, and inferred charge., The ts tree, when available, contains one row per TrackState with event, TrackState index, omega, pT from omega, and optional time/phi/tanLambda/d0/z0., The evt tree contains one row per event with selected-truth count, TrackState count, first selected truth pT, first TrackState omega, and first TrackState pT from omega., TrackState prefix resolution scans for omega branches and prefers GenFitTracks/TrackStates-like layouts., This script is useful when validating whether pT is being carried through TrackState.time, TrackState.omega, or both consistently., It depends on uproot and awkward rather than PyROOT for fast branch-level extraction., This is a diagnostic conversion utility, not part of the production reco or closeout summary chain.

**Examples**

- python3 scripts/pt_diagnostics_to_root.py \
- input /eos/.../reco_eta+1.00_pt14.142.root \
- out artifacts/analysis/pt_diagnostics_eta+1.00_pt14.142.root \
- pdg 13 \
- pdg-abs

**Arguments / properties inferred**

  - --input \| Input ROOT file
  - --out \| default="pt_diagnostics.root" \| Output ROOT file
  - --tree \| default="events"
  - --mc-prefix \| default="MCParticles/MCParticles"
  - --max-events \| default=-1
  - --pdg \| default=13
  - --pdg-abs
  - --no-pdg-abs \| Match PDG with sign.
  - --trackstate-prefix \| default=""
  - --assume-q \| default=-1 \| Charge sign used for pT=\|q/omega\| if you don

### `plot_pt_from_trackstate_time.py`

- **Status:** Secondary
- **Purpose:** Inspect pT encoded in trackStates.time.
- **Inputs:** EDM4hep/ROOT reco file containing an events TTree and TrackState.time leaf for the selected track collection.
- **Outputs:** Histogram image file, usually PNG or PDF, showing pT values read from TrackState.time.
- **Collections:** Reads TrackState.time from GenFitTracks by default; supports common branch layouts such as GenFitTracks.trackStates.time, GenFitTracks.TrackStates.time, _GenFitTracks_trackStates.time, and _GenFitTracks_TrackStates.time.
- **Tags:** diagnostics, edm4hep, genfittracks, matplotlib, plotting, pt, root, secondary, trackstate
- **Notes:** This script assumes the project convention that TrackState.time may carry reconstructed pT in GeV for diagnostic/publication purposes., Auto-detection tries several common EDM4hep/k4 branch naming patterns and falls back to scanning all leaves for collection/time matches., Use --per-event median or --per-event first when you want one pT entry per event instead of one entry per TrackState., Invalid sentinel values are dropped by default so failed fits do not dominate the histogram., This is a diagnostic plotting utility, not a replacement for the full pT-resolution analysis chain., Pair this with pt_diagnostics_to_root.py, inspect_events_pt_pathology.py, or dump_covmatrix_one_event.py when debugging TrackState.time versus omega behavior.

**Examples**

- python3 scripts/plot_pt_from_trackstate_time.py \
- -i /eos/.../reco_eta+1.00_pt14.142.root \
- coll GenFitTracks \

**Arguments / properties from DOC block**

- -i, --input: input EDM4hep ROOT reco file.

**Arguments / properties inferred**

  - -i, --input
  - --tree \| default="events"
  - --coll \| default="GenFitTracks"
  - --leaf \| default=None
  - --invalid-sentinel \| default=-1.0
  - --include-invalid
  - --min \| default=None
  - --max \| default=None
  - --per-event \| default="all" \| How to reduce multiple TrackState.time values per event.
  - --max-events \| default=None \| Only process first N events.
  - --events \| default=None
  - --bins \| default="80" \| Binning:
  - --bin-edges \| default=None \| Comma-separated custom bin edges, e.g.
  - --logy \| Log scale on y-axis.
  - --title \| default=None \| Plot title.
  - -o, --out \| default="pt_hist.png"
  - --dpi \| default=160
  - --show
  - --verbose \| Verbose diagnostics.

### `print_metadata.py`

- **Status:** Secondary
- **Purpose:** Read/display stamped metadata.
- **Inputs:** ROOT file containing optional metadata-like TTrees.
- **Outputs:** Terminal dump of metadata tree structure and the first few entries from each detected metadata-like tree.
- **Collections:** None; reads metadata-style ROOT TTrees, not EDM4hep event collections.
- **Tags:** diagnostics, edm4hep, metadata, podio, provenance, root, secondary

**Examples**

- python3 scripts/print_metadata.py /eos/.../reco_eta+1.00_pt14.142.root
- python3 scripts/print_metadata.py /eos/.../gun_eta+1.00_pt14.142.root

**Arguments / properties from DOC block**

- file.root: input ROOT file to inspect.

### `scan_pt_time_by_event.py`

- **Status:** Secondary
- **Purpose:** Per-event scanner used by pT-resolution analysis.
- **Inputs:** One EDM4hep/ROOT reco output file containing an events TTree, reconstructed TrackState leaves, track-to-hit relations, and SenseWireHit fields.
- **Outputs:** Log file with global pT/error/observability statistics and ranked best/worst events; optional CSV with one row per usable event.
- **Collections:** Reads GenFitTracks by default; reads OutputWireHitsGGTF by default; uses TrackState time/omega leaves, trackStates_begin/end, trackerHits_begin/end, trackerHits relation index/collectionID leaves, and SenseWireHit wire-position/drift-distance/angle leaves.
- **Tags:** diagnostics, edm4hep, genfittracks, ggtf, pt-resolution, root, scanner, secondary, sensewirehit, trackstate
- **Notes:** This script is the per-file scanner used by higher-level pT-resolution reducers and Delphes-parameter extraction helpers., The preferred pT source is TrackState.time when it is finite, positive, and not equal to invalidTime; otherwise the script falls back to pT inferred from TrackState.omega as 1/\|omega\|., For each event, the primary track is chosen as the track whose pT estimate is closest to expectedPt., Observability points are reconstructed from SenseWireHit wire position, drift distance, wire azimuthal angle, and stereo angle rather than relying on generic position.x/y/z leaves., Track-to-hit relations are decoded using trackerHits_begin/end plus trackerHits.index and trackerHits.collectionID; the target hit collection ID is inferred per track from the mode of collectionID values., Curvature observability combines phi-span, transverse chord, and circle-condition diagnostics; circleCond deliberately preserves finite, inf, and nan values rather than forcing inf to nan., The returned Python API scan_file(...) is used by analyze_pt_resolution_grid.py and extract_delphes_tracker_params.py, so interface changes can affect closeout analyses., Keep diagnostic thresholds fixed across CF-vs-W or other detector/material comparisons unless the threshold change itself is the object of study.

**Examples**

- python3 scripts/scan_pt_time_by_event.py \
- input /eos/.../reco_eta+1.00_pt14.142.root \
- trackCollection GenFitTracks \
- hitCollection OutputWireHitsGGTF \
- expectedPt 14.142 \
- csv artifacts/analysis/scan_eta+1.00_pt14.142.csv \
- stdout \
- verbose

**Arguments / properties inferred**

  - --input \| Input EDM4hep ROOT file
  - --trackCollection \| default="GenFitTracks"
  - --hitCollection \| default="OutputWireHitsGGTF" \| SenseWireHit collection name
  - --expectedPt \| Expected pT for this sample [GeV]
  - --top \| default=30
  - --event \| default=None
  - --csv \| default=None
  - --verbose
  - --invalidTime \| default=-1.0
  - --minPhiSpan \| default=0.06
  - --minChordXY \| default=500.0
  - --maxCircleCond \| default=1e6
  - --centralFrac \| default=0.95
  - --type \| default="bad"
  - --metric \| default="abs"
  - --log \| default=""
  - --stdout

### `stamp_ddsim_metadata.py`

- **Status:** Secondary
- **Purpose:** Stamp DDsim-related metadata.
- **Inputs:** Local DDSim output ROOT file opened in UPDATE mode, per-job JSON parameters, compact XML used by the job, full DDSim command string, resolved theta/phi gun settings, optional EOS targets, Key4HEP release label, and repeated key=value job extras.
- **Outputs:** ROOT keys ddsim_metadata_json, ddsim_cmd, and compact_xml_sha256 written into the input ROOT file.
- **Collections:** None; writes top-level ROOT metadata objects rather than EDM4hep event collections.
- **Tags:** condor, ddsim, eos, gun-production, key4hep, metadata, provenance, root, secondary
- **Notes:** This script is called by condor_ddsim.sh after local DDSim output validation and before staging the file to EOS., The metadata payload includes DDSim command provenance, grid parameters, resolved runtime gun angles, compact XML path/hash/content head, output targets, environment breadcrumbs, and tool versions., The compact XML contents are stored only up to a size limit and accompanied by a SHA256 hash so large geometry files do not make the ROOT file unreasonably large., Stamping is intended to be non-fatal in the worker wrapper; a failed stamp should not hide a DDSim generation failure or success., Use print_metadata.py or ROOT key inspection to verify the stored ddsim_metadata_json object.

**Examples**

- python3 scripts/stamp_ddsim_metadata.py \
- root gun_eta+1.00_pt14.142.root \
- params-json params/job_17.json \
- compact-xml IDEA_variant.xml \
- cmd "ddsim --compactFile IDEA_variant.xml --numberOfEvents 5000 ..." \
- theta-min 0.705 \
- theta-max 0.705 \
- phi-opts "--gun.phiMin 0*deg --gun.phiMax 360*deg --gun.distribution uniform" \
- out-eos /eos/.../gun_eta+1.00_pt14.142.root \

**Arguments / properties inferred**

  - --root
  - --params-json \| Per-job params JSON
  - --compact-xml \| Compact XML path/file actually used on worker
  - --cmd
  - --theta-min
  - --theta-max
  - --phi-opts \| default=""
  - --out-eos \| default="" \| EOS_POSIX target
  - --out-url \| default="" \| EOS_URL target
  - --k4-release \| default="" \| Key4HEP release tag you sourced
  - --job-extra \| default=[]

### `stamp_pipeline_metadata.py`

- **Status:** Secondary
- **Purpose:** Stamp provenance metadata into ROOT outputs.
- **Inputs:** ROOT file opened in UPDATE mode, stage label, command string, optional input paths, optional config paths, optional extra key=value metadata, and a working directory for git context.
- **Outputs:** ROOT key pipeline_metadata_json or the requested --key containing full JSON provenance; convenience keys pipeline_stage and pipeline_cmd.
- **Collections:** None; writes top-level ROOT metadata objects rather than EDM4hep event collections.
- **Tags:** condor, k4run, key4hep, metadata, provenance, reco, reproducibility, root, secondary
- **Notes:** This script is the general reco/pipeline provenance stamper, complementary to stamp_ddsim_metadata.py for DDSim gun production., The JSON payload records stage, command, input file hashes/sizes, config file hashes/content heads, environment breadcrumbs, tool versions, git branch/commit/status/remote, and arbitrary extras., Config contents are stored only up to a size limit and accompanied by SHA256 hashes to keep the ROOT file size controlled., Input paths that are not local files may have null size/hash values; the path is still recorded for reproducibility., Worker wrappers treat stamping as non-fatal so provenance failures do not hide actual reco success/failure., Use print_metadata.py or ROOT key inspection to verify the stored payload.

**Examples**

- python3 scripts/stamp_pipeline_metadata.py \
- root reco_gun_eta+1.00_pt14.142.root \
- stage final \
- cmd "k4run runtime/runDCHTestTrackFinder.py --inputFile ... --stage fit ..." \

**Arguments / properties inferred**

  - --root
  - --stage \| stage name: ddsim\|digi\|ggtf\|fit\|analysis\|...
  - --cmd
  - --config \| default=[]
  - --input \| default=[]
  - --extra \| default=[]
  - --workdir \| default="." \| directory to use for git info
  - --key \| default="pipeline_metadata_json" \| ROOT key name

### `sweep_pt.sh`

- **Status:** Secondary
- **Purpose:** Convenience helper for pT sweeps; confirm whether still active.
- **Inputs:** Hand-edited INPUT_DIR, OUTPUT_DIR, MODEL, XML, and PTS array; input gun ROOT files matching either gun_eta+0.00_E<PT>GeV.root or gun_eta+0.00_E<PT*1000>MeV.root.
- **Outputs:** Reco ROOT files named reco_eta+0.00_pT<PT>GeV.root under OUTPUT_DIR.
- **Collections:** Does not inspect collections directly; local_chain.sh normally runs DCHCollection -> DCH digi -> GGTF tracks -> GenFitTracks.
- **Tags:** genfit2, ggtf, legacy-helper, local-test, pt-sweep, reco, secondary, smoke-test
- **Notes:** This is not the authoritative production campaign submission path. Production reco should use scripts/submit_reco.sh -> configs/condor/reco.condor -> scripts/reco_job.sh., This helper is still useful for quick local smoke tests over a few pT points when debugging steering or fitter behavior before Condor submission., Several exported knobs appear to come from an older local-chain/fitter era and may be ignored by the current runDCHTestTrackFinder.py interface., The input filename pattern is older and energy-like, not the newer gun_eta<eta>_pt<pt>.root naming used by the DDSim Condor pipeline., If this script is kept, treat it as a small manual diagnostic wrapper; do not rely on it for CF-vs-W closeout production., Before using it, verify that ./local_chain.sh resolves correctly from the working directory; in the current layout the maintained wrapper may live under steering/local_chain.sh.

**Examples**

- cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder
- bash scripts/sweep_pt.sh

### `view_simhits_event.py`

- **Status:** Secondary
- **Purpose:** Event display / inspection utility for sim hits.
- **Inputs:** EDM4hep/ROOT reco file containing an events TTree, a hit collection with position.x/y/z leaves, optional DCH SimTrackerHit position leaves, and optional GenFitTracks TrackState/covariance leaves.
- **Outputs:** ROOT file containing per-event directories with XY, RZ, and 3D canvases/histograms; GenFit track overlays; optional simhit overlays; per-event metadata; hit_match TTree; hit-match histograms; and JSON summaries of nearest-simhit residuals.
- **Collections:** Reads OutputWireHitsGGTF by default for reco/digihit display; reads DCHCollection by default for simhit overlay; reads GenFitTracks by default for TrackState helix drawing and sigma(pT) ranking.
- **Tags:** covariance, diagnostics, event-display, genfittracks, ggtf, hit-matching, root, secondary, sigma-pt, simhits
- **Notes:** This is a visual/debug diagnostic utility, not part of the production reco or pT-resolution summary chain., It is useful for investigating suspicious tracks, large sigma(pT), z-spurs, bad hit geometry, or disagreement between reconstructed hit positions and truth simhits., Top-N ranking estimates sigma(pT) from TrackState covariance using sigma(pT)/pT ≈ sigma(omega)/\|omega\| and sigma(pT) ≈ expectedPt^2*sqrt(Var(omega))/\|q\|., TrackState covariance is interpreted as packed lower-triangle EDM4hep covariance, with Var(omega) taken from parameter index 2., For each displayed event, nearest-simhit diagnostics are computed by brute-force matching every reco/digihit point to the closest simhit in 3D., The hit_match TTree stores vector branches with one vector element per digihit; h_minDist3D, h_minDistXY, h_dZ summarize residuals., Helix drawing assumes a uniform Bz field and uses TrackState omega/phi/tanLambda plus reference point or D0/Z0 fallback., Auto-detected hit collections are scored to prefer GGTF/SenseWire-like collections with position.x/y/z and optional type labels., Because nearest-simhit matching is O(N_hits*N_simhits), very high-occupancy events may be slow.

**Examples**

- python3 scripts/view_tracks_event.py \
- input /eos/.../reco_eta+1.00_pt14.142.root \
- topN 10 \
- expectedPt 14.142 \
- hitsCollection OutputWireHitsGGTF \
- simhitCollection DCHCollection \
- trackCollection GenFitTracks \
- trackStyle helix \
- Bz 2.0 \
- assumeQ -1 \
- outRoot artifacts/analysis/view_tracks_eta+1.00_pt14.142_topSigma.root

**Arguments / properties inferred**

  - --input
  - --tree \| default="events"
  - --event \| default=-1
  - --hitsCollection \| default="OutputWireHitsGGTF" \| Hit collection with position.{x,y,z}. If not found, auto-detect a likely GGTF hit collection.
  - --autoDetectHits \| If set, auto-detect hits collection even if --hitsCollection is provided.
  - --simhitCollection \| default="DCHCollection"
  - --trackCollection \| default="GenFitTracks"
  - --trackStyle \| default="helix"
  - --Bz \| default=2.0
  - --assumeQ \| default=-1
  - --topN \| default=10
  - --expectedPt \| default=float("2.5897"
  - --scanMaxEvents \| default=-1
  - --rankOrder \| default="largest"
  - --hitMatchTopK \| default=25
  - --outRoot \| default="tracks_display_simhits_multi.root"

### `view_tracks_event.py`

- **Status:** Secondary
- **Purpose:** Event display / inspection utility for tracks.
- **Inputs:** EDM4hep/ROOT reco file containing an events TTree, a hit collection with position.x/y/z leaves, optional DCH digi position leaves, and optional GenFitTracks TrackState leaves.
- **Outputs:** ROOT file containing XY and RZ hit histograms, a 3D event display canvas, optional digi overlay markers, optional GenFit track overlays, and metadata describing the input/event/collections/command.
- **Collections:** Reads OutputWireHitsGGTF by default as the main reco hit display collection; optionally reads DCHDigi2Collection as raw digi overlay; reads GenFitTracks TrackStates by default for fitted-track overlays.
- **Tags:** dch, diagnostics, digis, event-display, genfittracks, ggtf, helix, root, secondary, sensewirehit, trackstate
- **Notes:** This is a diagnostic/event-display utility, not part of the production reco or pT-resolution summary chain., It is useful for quickly checking whether GGTF hit positions, raw DCH digis, and GenFit fitted tracks are geometrically consistent in a selected event., The script supports the newer pipeline where GGTF no longer emits separate GGTF_3DHits spacepoints and GenFit2DCHFitter consumes SenseWireHit-style candidate hits., Hit labels are read from <hitsCollection>.type when present and used to color/group the displayed hit markers., Track-to-TrackState association uses trackStates_begin/end when available; the displayed state is chosen as the AtIP-like state with smallest reference-point r² for each track., TrackState branch discovery handles common EDM4hep/PODIO naming variants such as GenFitTracks.trackStates., GenFitTracks.TrackStates., and underscore-prefixed forms., The pT(time) versus pT(\|q/omega\|) printout is a sanity diagnostic for the project convention where TrackState.time may encode pT; ignore the comparison if time is no longer used that way., Helix drawing assumes a uniform Bz field and uses TrackState referencePoint or D0/Z0 fallback together with phi, tanLambda, and omega., For truth/simhit overlay and nearest-simhit residual diagnostics, use view_tracks_event_simhits.py instead.

**Examples**

- python3 scripts/view_tracks_event.py \
- input /eos/.../reco_eta+1.00_pt14.142.root \
- event 12 \
- hitsCollection OutputWireHitsGGTF \
- digiCollection DCHDigi2Collection \
- trackCollection GenFitTracks \
- trackStyle helix \
- Bz 2.0 \
- assumeQ -1 \
- outRoot artifacts/analysis/view_tracks_eta+1.00_pt14.142_evt12.root

**Arguments / properties inferred**

  - --input
  - --tree \| default="events"
  - --event \| default=-1
  - --hitsCollection \| default="OutputWireHitsGGTF"
  - --autoDetectHits \| If set, auto-detect hits collection even if --hitsCollection is provided.
  - --digiCollection \| default="DCHDigi2Collection"
  - --trackCollection \| default="GenFitTracks"
  - --trackStyle \| default="helix"
  - --Bz \| default=2.0 \| B-field along z [T] for helix drawing (default: 2.0;
  - --assumeQ \| default=-1
  - --outRoot \| default="tracks_display.root" \| Output ROOT file for histos + canvases

### `prepare_and_submit_CF25_Au2p227matched.sh`

- **Status:** Legacy
- **Notes:** no_doc_block

**Environment knobs inferred**

  - TRANSFER_COMPACT \| default=0

### `prepare_and_submit_W20_Au0p3_defaultlike.sh`

- **Status:** Legacy
- **Notes:** no_doc_block

**Environment knobs inferred**

  - TRANSFER_COMPACT \| default=0

### `cglenn.cc`

- **Status:** Archive candidate
- **Notes:** no_doc_block

### `condor_submit_logs_summary.txt`

- **Status:** Unknown / needs classification
- **Notes:** missing_summary, no_doc_block, unknown_status

<!-- END AUTOREADME GENERATED -->
