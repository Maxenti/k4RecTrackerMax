# test/testTrackFinder

This README is auto-generated from per-file DOC blocks (preferred) plus heuristics.
Improve accuracy by adding a DOC header to important glue files, then re-run:

```bash
python3 scripts/autoreadme.py --root . --write
```

Accepted DOC start markers include `DOC`, `DOC:`, `DOC_START`, `DOC_BEGIN` (and similar); end markers include `DOC_END`, `END_DOC` (and similar).

## Files
| File | Summary | Usage | Connects-To | Inferred |
|---|---|---|---|---|
| ⚠️ `.__afs724E` |  |  |  |  |
| ⚠️ `cglenn.cc` |  |  |  |  |
| ⚠️ `dd4hep2root.py` | !/usr/bin/env python3 |  |  | import:ROOT<br>import:argparse<br>import:sys |
| ⚠️ `filelist.txt` |  |  |  |  |
| ✅ `local_chain.sh` |  | ./local_chain.sh [INPUT] [OUTPUT] [MODEL_SPEC] [COMPACT_XML] [DCH_SIMHITS] [DCH_NAME] [TGEO_FILE] |  | calls:runDCHTestTrackFinder.py<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:GenFitTracks<br>gaudi:topalg:Tracks<br>import:sys<br>uses:k4run |
| ✅ `runDCHTestTrackFinder.py` |  |  |  | gaudi:imports:Configurables<br>gaudi:topalg:CDCHTracks<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCHDigi2Collection<br>gaudi:topalg:DCHDigi2SimLink<br>gaudi:topalg:DCHDigi2SimLinkCollection<br>gaudi:topalg:DCHDigiSimLink<br>gaudi:topalg:DCHDigiSimLinkCollection<br>gaudi:topalg:DCHName<br>gaudi:topalg:DCHSimHits |
| ⚠️ `runTestTrackFinder.py` | ################# Parser |  |  | gaudi:imports:Configurables<br>gaudi:topalg:CDCHTracks<br>gaudi:topalg:DCHCollection<br>gaudi:topalg:DCH_DigiCollection<br>gaudi:topalg:DCH_v2<br>gaudi:topalg:DCHdigi<br>gaudi:topalg:GGTF_tracking<br>import:Configurables<br>import:Gaudi.Configuration<br>import:k4FWCore |
| ⚠️ `test_trackFinder.sh` | !/bin/bash |  |  | uses:k4run |
| ⚠️ `tracker_params.json` |  |  |  | gaudi:topalg:GenFitTracks<br>gaudi:topalg:fit_mode<br>gaudi:topalg:n_points_fit<br>gaudi:topalg:per_eta_fits<br>gaudi:topalg:trackCollection<br>gaudi:topalg:track_eta_max_inferred |

## Details

### `dd4hep2root.py`
- **Arguments / Properties (inferred):**
  - -c
  - -o \| default='detector.root' \| Converted file path

### `runDCHTestTrackFinder.py`
- **Arguments / Properties (inferred):**
  - --inputFile \| default="ddsim_output_edm4hep.root"
  - --outputFile \| default="output_digi_ggtf_fit.root" \| Output EDM4hep file
  - --compactXML \| default=""
  - --tgeoFile \| default="/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03CF.root"
  - --dchSimHits \| default="DCHCollection" \| Name of DCH SimTrackerHit collection in the input file
  - --dchName \| default="DCH_v2"
  - --modelPath \| default=""
  - --stage \| default="fit"
  - --skipDigi \| default=False
  - --jobTag \| default="" \| Optional free-form tag stored in metadata. If empty, auto-generated.
  - --dchDigiVersion \| default="v02" \| Choose DCH digitizer implementation
  - --xyResolution_mm \| default=0.10
  - --zResolution_mm \| default=30.0
  - --dch-deadtime-ns \| default=450.0
  - --dch-drift-vel-um-ns \| default=-1.0
  - --dch-signal-vel-mm-ns \| default=2.0/3.0*299792458.0*1e-6
  - --dch-gas-type \| default=0
  - --rw-start-ns \| default=1.0
  - --rw-duration-ns \| default=900.0
  - --tbeta \| default=0.6 \| GGTF beta threshold
  - --td \| default=0.3 \| GGTF distance threshold
  - --onnxChunk \| default=4096 \| ONNX hits per slice
  - --maxHitsPerEvent \| default=0
  - --ggtf-dropWireIfAbsDTooLarge \| default=True
  - --no-ggtf-dropWireIfAbsDTooLarge

### `runTestTrackFinder.py`
- **Arguments / Properties (inferred):**
  - --inputFile \| default="ddsim_output_edm4hep.root" \| InputFile
  - --outputFile \| default="output_digi.root" \| OutputFile
  - --modelPath \| default="" \| model path for the track finder
  - --tbeta \| default=0.6 \| tbeta clustering parameter
  - --td \| default=0.3 \| td clustering parameter
