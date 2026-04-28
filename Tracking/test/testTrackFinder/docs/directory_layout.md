# Directory Layout

## Goal

This document defines the intended directory contract for:

```text
Tracking/test/testTrackFinder/
```

The purpose is to stop the area from acting simultaneously as:

- an active workflow root
- a scratch directory
- an output dump
- a historical archive
- a config store
- a runtime-packaging area

The cleanup should separate those roles physically.

---

## High-level layout

The intended medium-term structure is:

```text
testTrackFinder/
  README.md
  DOCS_INDEX.md

  scripts/
  steering/
  configs/
  docs/
  artifacts/
  archive/
```

Each of those directories has a distinct meaning.

---

## `scripts/`

## Meaning

Maintained operational scripts and workflow utilities.

## What belongs here

- Condor submission wrappers
- worker-node wrappers
- runtime builders
- file-list builders
- analysis utilities
- comparison utilities
- plotting/export utilities
- metadata stamping utilities
- targeted debug helpers that are still actively used

## Examples

- `submit_reco.sh`
- `reco_job.sh`
- `reco.condor`
- `make_runtime.sh`
- `make_filelist.sh`
- `analyze_pt_resolution_grid.py`
- `compare_pt_resolution_grid.py`
- `summarize_ptres_improvement.py`
- `export_root_plots.py`

## What should not live here

- runtime tarballs
- large generated logs
- generated ROOT outputs
- stale backups that are no longer authoritative

Those should go under `artifacts/` or `archive/`.

---

## `steering/`

## Meaning

Authoritative steering files and directly run workflow entrypoints.

## What belongs here

- main k4run steering files
- local end-to-end chain scripts
- geometry conversion utilities that act as steering-like workflow entrypoints

## Examples

- `runDCHTestTrackFinder.py`
- `runTestTrackFinder.py` if still active
- `local_chain.sh`
- `dd4hep2root.py`

## Why separate this from `scripts/`

`steering/` files define the actual physics/reco job composition, while `scripts/` mostly define operational wrappers and submission logic. That distinction is worth making explicit.

---

## `configs/`

## Meaning

Static configuration payloads that are maintained by hand and consumed by the workflow.

## Suggested substructure

```text
configs/
  condor/
  delphes/
  geom/
```

## What belongs here

- `.condor` templates or fixed submit descriptions
- Delphes `.tcl` cards
- geometry/config references
- workflow YAML/JSON configs that are hand-maintained

## Examples

- `tracker_params.json`
- `test.yaml`
- Delphes cards
- geometry pointer/config files

## What should not live here

- generated `job_*.json` payloads
- runtime tarballs
- logs

Generated parameter sweeps belong in `artifacts/params/`.

---

## `docs/`

## Meaning

Human-facing documentation for the active workflow.

## What belongs here

- workflow instructions
- directory contracts
- short closeout notes
- Mermaid diagrams / workflow diagrams
- notes on authoritative commands

## Minimum expected docs

- `workflow.md`
- `directory_layout.md`
- optional `chain.mmd`

## Documentation rule

If a script becomes authoritative, it should be mentioned in `README.md` and in the workflow docs.

---

## `artifacts/`

## Meaning

Generated products that are reproducible outputs of the workflow.

This directory exists so the active workflow root is not polluted by outputs.

## Suggested substructure

```text
artifacts/
  analysis/
  geometry/
  logs/
  params/
  runtime/
```

---

## `artifacts/analysis/`

## Meaning

Generated analysis products.

## What belongs here

- summary ROOT files
- comparison ROOT files
- PNG/PDF plot exports
- CSV summaries
- improvement summaries
- ad hoc generated analysis logs that are worth keeping

## Examples

- `*_ptres.root`
- `compare_*.root`
- exported plot directories
- `improvement_CF_vs_W/`

---

## `artifacts/geometry/`

## Meaning

Generated geometry products.

## What belongs here

- TGeo ROOT files produced from compact XMLs
- auxiliary geometry conversion outputs

## Examples

- `IDEA_*.root`

---

## `artifacts/logs/`

## Meaning

Generated logs that are not part of the maintained workflow logic.

## Suggested substructure

```text
artifacts/logs/
  condor/
  reco/
  analysis/
  historical/
```

## What belongs here

- local test logs
- Condor stdout/stderr logs
- batch log collections
- large job-log trees

## Important note

Some submit-time log directories may temporarily remain under `scripts/logs/` until path contracts are stabilized. Long term, those should either migrate into `artifacts/logs/` or be clearly documented as the canonical log sink.

---

## `artifacts/params/`

## Meaning

Generated parameter payloads for campaigns.

## What belongs here

- `job_*.json`
- generated JSONL parameter tables
- campaign sweep parameter manifests

## Why this is first-class

These are reproducible generated inputs to campaigns, not handwritten configs. They should not be confused with curated maintained configs.

---

## `artifacts/runtime/`

## Meaning

Generated runtime packages for Condor execution.

## What belongs here

- `runtime.tgz`
- `runtime.tgz.bak.*`
- optional unpacked runtime validation snapshots if retained

## Why separate this

`runtime.tgz` is a generated deployment artifact, not source code. Keeping it out of `scripts/` reduces confusion.

---

## `archive/`

## Meaning

Historical material retained for reference but not part of the active authoritative workflow.

## Suggested substructure

```text
archive/
  old_scripts/
  old_steering/
  old_condor/
  old_outputs/
  notes/
```

## What belongs here

- superseded scripts
- retired steering files
- older campaign wrappers
- old one-off testing material
- backups currently stored as `.txt` or ad hoc references

## Archive rule

Archive material may still be useful, but it should never be mistaken for the preferred workflow path.

---

## What should remain outside `testTrackFinder/`

The larger `Tracking/` tree still has its own intended contract.

### `Tracking/components/`

Compiled algorithm/plugin code only.

Examples:

- `GGTF_tracking.cpp`
- `GenFit2DCHFitter.cpp`
- `SimpleFitDCHFitter.cpp`
- `ThreePointFitter.cpp`

Historical source backups currently under `Tracking/components/backup/` should eventually be folded into a clearer archive location, but that is a second-order cleanup after the `testTrackFinder` area is stabilized.

### `Tracking/src/` and `Tracking/include/`

Core library implementation and headers. These are not workflow directories and should remain relatively stable.

---

## Move policy

The cleanup should follow this order.

## Phase A — safe moves only

Move obviously generated content into `artifacts/` first:

- `.root`
- `.png`
- `.pdf`
- `.csv`
- `.log`
- `runtime.tgz`
- generated job params

This phase should not require changing active code paths.

## Phase B — document active paths

Write/update:

- `README.md`
- `docs/workflow.md`
- `docs/directory_layout.md`

Only after the authoritative path assumptions are documented should active maintained files be moved.

## Phase C — move active maintained files

Move steering and config files into `steering/` and `configs/`, then patch active scripts accordingly.

## Phase D — normalize archive policy

Move stale historical material into `archive/` and add short notes for anything non-obvious.

---

## Anti-patterns to avoid

These are the patterns that created the current sprawl and should not be repeated.

### 1. Generated outputs at the workflow root

Do not leave generated ROOT/PNG/CSV/log files directly in `testTrackFinder/` unless there is a very temporary reason.

### 2. Multiple copies of active scripts without a documented authoritative one

If two scripts do the same thing, one should be declared authoritative and the other archived or deleted.

### 3. Hidden path contracts

If `make_runtime.sh` depends on a steering file at a particular relative path, that contract must be documented before further moves.

### 4. Archive mixed with active content

Old material should live in `archive/`, not side-by-side with active maintained files unless there is a very strong reason.

---

## Intended end state

At the end of the cleanup, a new person should be able to answer these questions immediately:

### What do I edit to change the active reco workflow?

- `steering/`
- `scripts/`
- `configs/`

### Where do generated outputs go?

- `artifacts/`

### Where do I find the authoritative instructions?

- `README.md`
- `docs/workflow.md`
- `docs/directory_layout.md`

### Where do I look for historical or superseded material?

- `archive/`

That is the standard the cleanup should aim for.
