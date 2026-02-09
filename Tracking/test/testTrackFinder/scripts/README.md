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
