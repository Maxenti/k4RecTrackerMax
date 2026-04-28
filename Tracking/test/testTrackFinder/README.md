# testTrackFinder

## Purpose

`Tracking/test/testTrackFinder/` is the active workflow area for the IDEA DCH reconstruction and closeout studies built around the `k4RecTracker` tracking stack. In its current state, this area is used for:

- running the authoritative IDEA DCH reco chain with
  - `DCHdigi`
  - `GGTF_tracking`
  - `GenFit2DCHFitter`
- building a Condor-safe runtime bundle for lxplus/HTCondor jobs
- submitting large reco campaigns over EOS input trees
- analyzing the resulting reco outputs into pT-resolution summary ROOT files
- comparing CF-vs-W and related material / geometry variants for closeout plots and notes

This directory is **not** just a scratch test area anymore. It has become the practical workflow root for the current IDEA DCH track-finder / fitter studies, so the goal of the cleanup is to make the active workflow clear, reproducible, and maintainable.

---

## Current authoritative workflow entrypoints

These are the files that should currently be treated as the main maintained workflow entrypoints.

### Reco submission and runtime

- `scripts/make_runtime.sh`
  - builds `runtime.tgz` for Condor jobs
- `scripts/submit_reco.sh`
  - prepares file list and submits one Condor job per reco input file
- `scripts/reco_job.sh`
  - worker-node wrapper for one reco file
- `scripts/reco.condor`
  - Condor submit description for reco jobs
- `scripts/make_filelist.sh`
  - enumerates reco inputs under an EOS/local input base directory

### Steering

- `runDCHTestTrackFinder.py`
  - main steering file used by the current reco chain
- `runTestTrackFinder.py`
  - older or alternate steering entrypoint; keep only if still actively needed
- `local_chain.sh`
  - local end-to-end driver for non-Condor testing
- `dd4hep2root.py`
  - utility to convert compact XML detector descriptions into TGeo `.root` files

### Analysis and closeout

- `scripts/analyze_pt_resolution_grid.py`
  - reduces reco outputs into one summary ROOT file over eta / pT
- `scripts/compare_pt_resolution_grid.py`
  - compares two summary ROOT outputs and writes comparison plots/objects
- `scripts/summarize_ptres_improvement.py`
  - summarizes percent improvement between “new” and “old” analysis ROOT outputs
- `scripts/export_root_plots.py`
  - exports all drawable objects from a ROOT file to mirrored PNG/PDF outputs
- `scripts/analyze_job.sh`
  - Condor worker wrapper for long-running analysis jobs

### Useful diagnostics / support utilities

Some utilities are still valuable, but should be treated as secondary helpers rather than core workflow entrypoints unless explicitly promoted:

- `scripts/view_tracks_event.py`
- `scripts/view_simhits_event.py`
- `scripts/debug_z_spur_event.py`
- `scripts/dump_covmatrix_one_event.py`
- `scripts/inspect_events_pt_pathology.py`
- `scripts/scan_pt_time_by_event.py`
- `scripts/plot_mcparticles_pt.py`
- `scripts/plot_pt_from_trackstate_time.py`

---

## Recommended directory contract

The cleanup goal is to make the top-level purpose of each subarea obvious.

### Active maintained content

- `scripts/`
  - maintained operational scripts and wrappers
- `steering/`
  - authoritative steering files used by active workflows
- `configs/`
  - static configuration files, cards, condor templates, geometry/config pointers
- `docs/`
  - workflow notes, directory contracts, and closeout instructions

### Generated content

- `artifacts/analysis/`
  - generated summary ROOT files, PNG/PDF plots, CSVs, comparison outputs
- `artifacts/geometry/`
  - generated TGeo / geometry ROOT outputs from XML conversion
- `artifacts/logs/`
  - non-authoritative logs from local tests / Condor submissions / analyses
- `artifacts/params/`
  - generated JSON or JSONL job-parameter payloads
- `artifacts/runtime/`
  - `runtime.tgz` and backup runtime tarballs

### Historical content

- `archive/`
  - old scripts, legacy steering, obsolete helper workflows, stale historical material retained only for reference

---

## What belongs in Git vs what does not

### Should remain as maintained repository content

- C++ source under `Tracking/components/`, `Tracking/src/`, `Tracking/include/`
- active workflow scripts
- active steering files
- static configs/cards
- documentation

### Should be treated as generated artifacts

- `runtime.tgz`
- `.root` outputs from reco, analysis, plotting, or geometry conversion
- `.png`, `.pdf`, `.csv`, `.log`
- generated `params/job_*.json`
- temporary file lists and queue lists

Generated products may still be kept for reproducibility or closeout, but they should not live next to maintained source files without a clear artifact boundary.

---

## Typical workflows

### 1. Rebuild runtime bundle

Use after changing:

- tracking plugins
- reco worker scripts
- runtime shims
- steering/runtime dependencies

Typical command:

```bash
cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/scripts
bash make_runtime.sh
```

Expected output:

- `runtime.tgz`
- runtime sanity checks passing

### 2. Submit reco campaign

Run from one level above `scripts/` so relative submission paths remain consistent.

Typical pattern:

```bash
cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder

IN_DIR=/eos/.../gun_samples/... \
OUT_DIR=/eos/.../reco_samples2/... \
COMPACT_XML=/eos/.../IDEA_variant.xml \
TGEOFILE=/eos/.../IDEA_variant.root \
FITTER=genfit2 \
FIT_OUT=auto \
GF_USE_MAT=1 \
STAGE=fit \
K4REL=2026-04-22 \
bash scripts/submit_reco.sh
```

### 3. Analyze reco outputs into summary ROOT files

Typical direct local command:

```bash
python3 scripts/analyze_pt_resolution_grid.py \
  --inputDir /eos/.../reco_samples2/<variant> \
  --outRoot /eos/.../final_analysis/<variant>_ptres.root
```

Condor analysis is also supported through `scripts/analyze_job.sh` and dedicated `.condor` submit files.

### 4. Compare two summary outputs

Typical command:

```bash
python3 scripts/compare_pt_resolution_grid.py \
  --a /eos/.../final_analysis/CF_variant_ptres.root \
  --b /eos/.../final_analysis/W_variant_ptres.root \
  --out /eos/.../final_analysis/compare_CF_vs_W.root \
  --tagA CF_variant \
  --tagB W_variant
```

### 5. Summarize percent improvement

Typical command:

```bash
python3 scripts/summarize_ptres_improvement.py \
  --new /eos/.../final_analysis/CF_variant_ptres.root \
  --old /eos/.../final_analysis/W_variant_ptres.root \
  --outdir /eos/.../final_analysis/improvement_CF_vs_W \
  --newLabel CF_variant \
  --oldLabel W_variant
```

### 6. Export ROOT plots to PNG/PDF

Typical command:

```bash
python3 scripts/export_root_plots.py \
  --input /eos/.../final_analysis/compare_CF_vs_W.root \
  --outdir /eos/.../final_analysis/compare_CF_vs_W_plots
```

---

## Current cleanup priorities

The cleanup should proceed in this order.

### Stage 1 — isolate generated artifacts

Move obviously generated files out of the active root into `artifacts/` first:

- analysis ROOT outputs
- PNG/PDF/CSV/logs
- geometry ROOTs
- runtime tarballs
- generated params JSONs

This gives immediate clarity without breaking path-sensitive scripts.

### Stage 2 — document the authoritative workflow

Write and maintain:

- `README.md`
- `docs/workflow.md`
- `docs/directory_layout.md`

before doing larger path refactors.

### Stage 3 — separate steering and configs cleanly

Only after the docs are in place, move:

- steering files to `steering/`
- static cards/configs to `configs/`

and then patch the scripts that depend on those paths.

### Stage 4 — unify archival policy

Anything historical but non-authoritative should move into `archive/` with a short note on why it is retained.

---

## Current closeout status

As of the current closeout phase, the project has:

- a working rebuilt `k4RecTracker` install in the active `install/` tree
- a rebuilt and passing `runtime.tgz`
- working Condor reco submission for CF/W campaigns
- working pT-resolution analysis and comparison scripts
- utility scripts for summary improvement statistics and ROOT plot export

That means this is the right moment to freeze workflow/documentation assumptions and clean the directory structure before the next development cycle.

---

## Archive policy

A file or directory should go to `archive/` if:

- it is no longer part of the current authoritative workflow,
- it is being kept only for historical reference,
- it has been superseded by a newer script or steering file,
- or it reflects an older campaign structure that should not be reused by default.

Archive material should stay readable, but should not be allowed to masquerade as active workflow content.

---

## Notes for future maintainers

When in doubt:

- prefer **fewer authoritative entrypoints**, not more
- keep generated outputs physically separated from maintained source
- do not let one-off campaign products accumulate in the active workflow root
- document the canonical path contracts before moving active scripts
- preserve reproducibility, but do not confuse reproducibility with keeping every generated file in the same directory as the workflow logic
