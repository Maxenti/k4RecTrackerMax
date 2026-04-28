# testTrackFinder File Classification Audit

This document classifies the important files under `Tracking/test/testTrackFinder/` by purpose, current status, and documentation priority.

## Status legend

- **Authoritative**: part of the current preferred workflow
- **Secondary**: useful and maintained, but not central to the main workflow path
- **Legacy**: older or transitional path kept for reference or compatibility
- **Archive candidate**: likely should move to archive unless still actively used

## Classification table

| File | Purpose | Status | Document where | Notes |
|---|---|---:|---|---|
| `steering/runDCHTestTrackFinder.py` | Main authoritative k4run steering for DCH digi → GGTF → GenFit2 fitting | Authoritative | `README.md`, `docs/workflow.md` | Primary physics/reco composition file |
| `steering/local_chain.sh` | Local end-to-end wrapper around the main steering with environment knobs and metadata stamping | Authoritative | `README.md`, `docs/workflow.md` | Operator-facing local validation path |
| `steering/dd4hep2root.py` | Convert compact DD4hep XML into TGeo ROOT geometry | Authoritative | `docs/workflow.md` | Needed for matched XML/TGeo material-aware fitting |
| `steering/runTestTrackFinder.py` | Older broader test steering with planar + DCH digi + GGTF | Legacy | brief note in `docs/workflow.md` or archive note | Keep as reference, but not the default workflow |
| `scripts/make_runtime.sh` | Build worker-node runtime bundle and validate plugin usability | Authoritative | `README.md`, `docs/workflow.md` | Canonical Condor runtime packaging step |
| `scripts/submit_reco.sh` | Main reco campaign submission wrapper | Authoritative | `README.md`, `docs/workflow.md` | User-facing submission entrypoint |
| `scripts/reco_job.sh` | Condor worker wrapper for one reco job | Authoritative | `docs/workflow.md` | Core batch infrastructure |
| `configs/condor/reco.condor` | Fixed submit description for reco jobs | Authoritative | `docs/workflow.md`, `docs/directory_layout.md` | Static maintained Condor config |
| `scripts/make_filelist.sh` | Discover eta-organized input ROOT files and build submission file lists | Authoritative | `docs/workflow.md` | Required by batch reco path |
| `scripts/analyze_pt_resolution_grid.py` | Reduce reco outputs into summary ROOT with by-eta, by-method, and diagnostic products | Authoritative | `README.md`, `docs/workflow.md` | Main analysis reduction step |
| `scripts/analyze_job.sh` | Condor worker wrapper for pT-resolution analysis | Authoritative | `docs/workflow.md` | Batch-backed analysis path |
| `configs/condor/analyze_CF25_Au2p227matched.condor` | Campaign-specific Condor submission for CF analysis ROOT output | Authoritative (campaign-specific) | `docs/workflow.md` | Useful for current closeout campaign |
| `configs/condor/analyze_W20_Au0p3_defaultlike.condor` | Campaign-specific Condor submission for W analysis ROOT output | Authoritative (campaign-specific) | `docs/workflow.md` | Useful for current closeout campaign |
| `configs/condor/analyze.condor` | Generic/shared analysis Condor template | Secondary | `docs/workflow.md` if still used | Keep only if still part of the active path |
| `scripts/compare_pt_resolution_grid.py` | Compare two summary ROOT outputs with overlays, ratios, and diagnostic comparisons | Authoritative | `README.md`, `docs/workflow.md` | Main variant-comparison step |
| `scripts/summarize_ptres_improvement.py` | Build closeout improvement summaries and CSV/text/ROOT products | Authoritative | `docs/workflow.md` | Closeout-focused summary utility |
| `scripts/export_root_plots.py` | Recursively export ROOT objects to PNG/PDF | Authoritative | `docs/workflow.md` | Closeout/note packaging utility |
| `configs/geom/compact.xml` | Maintained geometry/config reference used by workflow | Authoritative | `docs/workflow.md`, `docs/directory_layout.md` | Static maintained config |
| `configs/tracker_params.json` | Maintained tracking parameter config | Authoritative | `docs/workflow.md` or config section | Important config payload |
| `configs/test.yaml` | Maintained workflow/config file | Authoritative | `docs/workflow.md` or config section | Important config payload |
| `configs/delphes/*.tcl` | Delphes cards and IDEA DCH card variants | Secondary | `scripts/README.md` or auxiliary config section | Keep, but not central to current reco closeout path |
| `scripts/scan_pt_time_by_event.py` | Per-event scanner used by analysis code | Secondary but operationally important | `scripts/README.md` | Imported by `analyze_pt_resolution_grid.py` |
| `scripts/debug_z_spur_event.py` | Debug a suspicious z-spur or event-level pathology | Secondary | `scripts/README.md` | Diagnostic utility |
| `scripts/dump_covmatrix_one_event.py` | Dump one-event covariance information for debugging | Secondary | `scripts/README.md` | Diagnostic utility |
| `scripts/inspect_events_pt_pathology.py` | Inspect events with pathological pT behavior | Secondary | `scripts/README.md` | Diagnostic utility |
| `scripts/view_simhits_event.py` | Event display / inspection utility for sim hits | Secondary | `scripts/README.md` | Visualization utility |
| `scripts/view_tracks_event.py` | Event display / inspection utility for tracks | Secondary | `scripts/README.md` | Visualization utility |
| `scripts/plot_mcparticles_pt.py` | Plot MC-particle pT distributions | Secondary | `scripts/README.md` | Utility plotter |
| `scripts/plot_pt_from_trackstate_time.py` | Inspect pT encoded in `trackStates.time` | Secondary | `scripts/README.md` | Helpful for validation of current representation |
| `scripts/stamp_pipeline_metadata.py` | Stamp provenance metadata into ROOT outputs | Secondary | `scripts/README.md`, maybe workflow appendix | Reproducibility infrastructure |
| `scripts/stamp_ddsim_metadata.py` | Stamp DDsim-related metadata | Secondary | `scripts/README.md` | Reproducibility infrastructure |
| `scripts/print_metadata.py` | Read/display stamped metadata | Secondary | `scripts/README.md` | Utility for provenance inspection |
| `scripts/autoreadme.py` | Auto-generate README content from DOC blocks and heuristics | Secondary | `scripts/README.md` | Maintenance helper; not a replacement for curated docs |
| `scripts/prepare_and_submit.sh` | Older campaign wrapper for preparing/submitting jobs | Legacy | `scripts/README.md` or archive note | Likely superseded by `submit_reco.sh` |
| `scripts/prepare_and_submit_CF25_Au2p227matched.sh` | Variant-specific older wrapper | Legacy | archive note | Keep only if useful campaign history remains |
| `scripts/prepare_and_submit_W20_Au0p3_defaultlike.sh` | Variant-specific older wrapper | Legacy | archive note | Keep only if useful campaign history remains |
| `scripts/condor_ddsim.sh` | Older lower-level Condor wrapper for DDsim-related work | Legacy | archive note or `scripts/README.md` | Likely transitional |
| `scripts/condor_reco.sh` | Older lower-level Condor reco wrapper | Legacy | archive note or `scripts/README.md` | Likely superseded |
| `scripts/sweep_pt.sh` | Convenience helper for pT sweeps | Secondary / Legacy | `scripts/README.md` | Keep only if still used |
| `test_trackFinder.sh` | Older local test runner | Legacy | archive note | Not part of current authoritative path |
| `scripts/Calculate_Aucoating_thickness.py` | Side-study / materials utility | Secondary | `scripts/README.md` | Not central to main reco chain |
| `scripts/patch_trkCov_match_dch_material.py` | Side-study / materials/config patch helper | Secondary | `scripts/README.md` | Auxiliary study utility |
| `scripts/dch_x0_per_layer.py` | Material-budget / per-layer utility | Secondary | `scripts/README.md` | Auxiliary analysis |
| `scripts/DelphesParamsOutput.py` | Delphes-related helper | Secondary | `scripts/README.md` | Outside the main authoritative reco closeout path |
| `scripts/mk_ddsim_grid.py` | Campaign/grid-generation helper | Secondary | `scripts/README.md` | Useful but not central |
| `scripts/collect_knobs.py` | Knob/config collection helper | Secondary | `scripts/README.md` | Support utility |
| `scripts/cglenn.cc` | Unclear workflow role | Archive candidate | none unless still active | Archive unless demonstrably used |
| top-level `cglenn.cc` | Unclear workflow role | Archive candidate | none unless still active | Archive unless demonstrably used |
| `docs/README.md` | Docs navigation/index, if distinct from top-level README | Secondary | docs only | Keep only if it has a clearly different scope |
| `scripts/README.md` | Inventory for scripts/utilities | Secondary | scripts only | Good place for utilities and legacy wrappers |
| top-level `README.md` | Main authoritative entry for this workflow area | Authoritative | itself | Should stay concise and current |

## Recommended documentation priority

### Put in top-level `README.md`
Only the main path:

- `steering/runDCHTestTrackFinder.py`
- `steering/local_chain.sh`
- `steering/dd4hep2root.py`
- `scripts/make_runtime.sh`
- `scripts/submit_reco.sh`
- `scripts/analyze_pt_resolution_grid.py`
- `scripts/compare_pt_resolution_grid.py`
- `scripts/summarize_ptres_improvement.py`
- `scripts/export_root_plots.py`

### Put in `docs/workflow.md`
Everything in the top-level README plus:

- `scripts/reco_job.sh`
- `configs/condor/reco.condor`
- `scripts/make_filelist.sh`
- `scripts/analyze_job.sh`
- campaign-specific analysis condor files
- artifact and output path conventions

### Put in `scripts/README.md`
Secondary utilities and non-mainline helpers:

- event viewers
- pathology inspectors
- metadata tools
- side-study helpers
- legacy wrappers clearly marked as legacy

## Recommended next cleanup after documentation

1. Move likely legacy wrappers into `archive/` once you are confident they are no longer needed.
2. Keep only one authoritative path for reco submission and one for analysis submission.
3. Leave secondary utilities in `scripts/`, but do not let them dominate the main workflow docs.
4. Treat `components/backup/` as a later cleanup target outside the immediate `testTrackFinder` scope.
