# Workflow

## Scope

This document describes the current authoritative workflow for the IDEA DCH track-finder / fitter chain under:

```text
Tracking/test/testTrackFinder/
```

The intended use is to support:

- runtime bundle creation for Condor jobs
- reco submission over EOS input campaigns
- pT-resolution analysis over reco outputs
- CF-vs-W and similar closeout comparisons
- plot export and summary-statistics generation

This document is intentionally operational rather than historical.

---

## Workflow overview

The current workflow has five main phases.

1. **Prepare geometry inputs**
2. **Build / rebuild the Condor runtime bundle**
3. **Submit reco jobs**
4. **Analyze reco outputs into summary ROOT files**
5. **Compare and summarize variants**

A sixth optional phase exports plots to PNG/PDF for notes or closeout packaging.

---

## Phase 1 — geometry inputs

## Inputs

Each geometry / material variant typically needs:

- a compact DD4hep XML file
- a matching TGeo `.root` file

The compact XML is passed to the reco steering file, while the TGeo ROOT file is used by the GenFit2 material-aware fitting path.

## XML to TGeo conversion

Use the conversion utility when a geometry ROOT file is not already available.

Typical pattern:

```bash
cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder

python3 dd4hep2root.py \
  -c /eos/.../IDEA_variant.xml \
  -o /eos/.../IDEA_variant.root
```

## Notes

- XML and TGeo should always be matched to the same detector/material variant.
- For closeout comparisons, keep the XML and TGeo pair fixed per variant and document the exact paths used.

---

## Phase 2 — runtime bundle creation

Condor reco jobs use a self-contained runtime tarball so that the worker nodes can load:

- `libTracking.so`
- `libDCHdigi.so`
- required catalogs (`.components`, `.confdb`, `.confdb2`)
- GenFit2 libraries
- steering/runtime helper files
- the model file

## Authoritative script

```text
scripts/make_runtime.sh
```

## Typical command

```bash
cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/scripts
bash make_runtime.sh
```

## Expected output

```text
scripts/runtime.tgz
```

## Required checks

The runtime build should pass all of the following before reco submission:

- `libTracking` loads
- `libDCHdigi` loads
- component catalogs contain `GenFit2DCHFitter` (or whichever fitter path is intended)
- runtime sanity check passes
- `runtime.tgz` is successfully written

## Operational rule

Rebuild `runtime.tgz` whenever one of the following changes:

- tracking plugins or their dependencies
- worker-side wrapper scripts
- runtime shims / import logic
- steering files that are packaged into the runtime
- ONNX/model content used by the chain

---

## Phase 3 — reco submission

Reco submission is performed from one level above `scripts/` to keep relative path behavior stable.

## Authoritative files

- `scripts/submit_reco.sh`
- `scripts/reco_job.sh`
- `scripts/reco.condor`
- `scripts/make_filelist.sh`

## Input assumptions

Each campaign uses:

- `IN_DIR`
  - base reco input directory containing `eta_*` subdirectories and gun/reco input ROOT files
- `OUT_DIR`
  - base EOS output directory where reco outputs will be written
- `COMPACT_XML`
  - detector XML for the chosen variant
- `TGEOFILE`
  - matching TGeo ROOT for material-aware fitting

## Reco environment assumptions

The current intended nightly is:

```text
2026-04-22
```

and the worker-side flow is designed around that nightly.

## Typical submission pattern

```bash
cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder

IN_DIR=/eos/.../gun_samples/<variant> \
OUT_DIR=/eos/.../reco_samples2/<variant> \
COMPACT_XML=/eos/.../<variant>.xml \
TGEOFILE=/eos/.../<variant>.root \
FITTER=genfit2 \
FIT_OUT=auto \
GF_USE_MAT=1 \
STAGE=fit \
K4REL=2026-04-22 \
bash scripts/submit_reco.sh
```

## Output pattern

Reco outputs are written per eta slice under the output base directory, typically with names like:

```text
<OUT_DIR>/eta_+0.10/reco_<input_basename>.root
```

## Monitoring

Use:

```bash
condor_q "$USER"
```

and submit-side logs under:

```text
scripts/logs/reco/
```

Typical quick failure scan:

```bash
grep -RInE 'ERROR|FATAL|Exception|Traceback|failed|not found|verify' scripts/logs/reco
```

## Recommended practice

Always run a **tiny test submission** after changing:

- runtime bundle contents
- worker-side scripts
- steering file paths
- key environment setup logic

before launching a full CF/W campaign.

---

## Phase 4 — pT-resolution analysis

Once reco outputs exist, reduce them into one summary ROOT file per variant.

## Authoritative script

```text
scripts/analyze_pt_resolution_grid.py
```

## Direct local usage

```bash
python3 scripts/analyze_pt_resolution_grid.py \
  --inputDir /eos/.../reco_samples2/<variant> \
  --outRoot /eos/.../final_analysis/<variant>_ptres.root
```

## Condor-backed usage

If the analysis is large enough to warrant batch execution, use:

- `scripts/analyze_job.sh`
- dedicated `.condor` submission files for each target analysis

The Condor analysis job should:

- source the same intended nightly
- stage the needed analysis scripts and runtime tarball
- write one output ROOT file to EOS

## Current defaults

Typical analysis defaults currently used for closeout comparisons:

- `trackCollection = GenFitTracks`
- `hitCollection = OutputWireHitsGGTF`
- `qualityCut = none`
- `minPhiSpan = 0.06`
- `minChordXY = 500.0`
- `maxCircleCond = 1e6`
- `centralFrac = 0.95`

These should be kept identical between variants when doing a closeout comparison.

---

## Phase 5 — compare two summary outputs

Once both variant summary ROOT files exist, compare them.

## Authoritative script

```text
scripts/compare_pt_resolution_grid.py
```

## Typical command

```bash
python3 scripts/compare_pt_resolution_grid.py \
  --a /eos/.../final_analysis/CF_variant_ptres.root \
  --b /eos/.../final_analysis/W_variant_ptres.root \
  --out /eos/.../final_analysis/compare_CF_vs_W.root \
  --tagA CF_variant \
  --tagB W_variant
```

## Interpretation rule

For the closeout comparison, ensure that:

- the same reco chain was used
- the same analysis settings were used
- only the intended detector/material difference changes between A and B

That makes the comparison defensible.

---

## Phase 6 — closeout summaries and plot export

After the summary ROOT files and comparison ROOT file exist, generate closeout-friendly products.

## Improvement summary

Use:

```text
scripts/summarize_ptres_improvement.py
```

Typical command:

```bash
python3 scripts/summarize_ptres_improvement.py \
  --new /eos/.../final_analysis/CF_variant_ptres.root \
  --old /eos/.../final_analysis/W_variant_ptres.root \
  --outdir /eos/.../final_analysis/improvement_CF_vs_W \
  --newLabel CF_variant \
  --oldLabel W_variant
```

This produces:

- per-point improvement CSV
- per-eta improvement CSV
- global-by-method summary CSV
- text summary
- summary ROOT file

## Plot export

Use:

```text
scripts/export_root_plots.py
```

Typical command:

```bash
python3 scripts/export_root_plots.py \
  --input /eos/.../final_analysis/compare_CF_vs_W.root \
  --outdir /eos/.../final_analysis/compare_CF_vs_W_plots
```

This mirrors the ROOT file directory structure and exports PNG/PDF versions of supported drawable objects.

---

## Expected artifact locations

A recommended output pattern is:

```text
/eos/.../cf_vs_w_closeout/
  W20_Au0p3_defaultlike/
    eta_.../
      reco_*.root
  CF25_Au2p227matched/
    eta_.../
      reco_*.root
  final_analysis/
    W20_Au0p3_defaultlike_ptres.root
    CF25_Au2p227matched_ptres.root
    compare_CF25_Au2p227matched_vs_W20_Au0p3_defaultlike.root
    improvement_CF_vs_W/
    ..._plots/
```

That layout keeps reco outputs, summary outputs, and exported plots conceptually separated.

---

## Common failure modes

## Runtime bundle problems

Symptoms:

- worker jobs fail before steering runs
- missing `.so` dependencies
- missing steering file inside Condor scratch
- failed plugin usability checks

Typical fixes:

- rebuild `runtime.tgz`
- verify packaged steering file paths
- verify catalogs contain intended fitter registration
- verify worker-side setup is using the correct nightly

## Path-contract problems

Symptoms:

- job can start but cannot find
  - steering file
  - XML
  - TGeo
  - analysis script

Typical fixes:

- move only after documenting paths
- use absolute paths in Condor files where practical
- keep active scripts path-stable until cleanup is complete

## False-negative import checks

Symptoms:

- plugin `.so` loads and catalogs look correct, but Python import sanity checks fail

Typical fix:

- trust library load + catalog registration over brittle legacy configurable-import assumptions

## Missing output ROOT file after job failure

Symptoms:

- verify step fails because no output ROOT file exists

Interpretation:

- that is usually secondary; inspect the first upstream failure in the full log instead

---

## Operational policy for this area

Until the cleanup is finished:

- do not casually move active scripts around
- prefer freezing active path contracts first
- move generated artifacts out of the workflow root before reorganizing source/config files
- update docs immediately when an authoritative command changes

That keeps the workflow usable while organization work proceeds.
