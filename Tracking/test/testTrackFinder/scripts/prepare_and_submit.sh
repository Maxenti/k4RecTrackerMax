#!/usr/bin/env bash
set -euo pipefail

#DOC
#Summary: Authoritative DDSim gun-production submission wrapper that generates a pT/eta job grid, splits it into per-job JSON parameter files, builds the Condor queue list, and submits the DDSim campaign.
#Status: authoritative
#Usage:
#  bash scripts/prepare_and_submit.sh
#  TRANSFER_COMPACT=1 bash scripts/prepare_and_submit.sh
#Examples:
#  cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder
#  bash scripts/prepare_and_submit.sh
#  Expected result: params/job_*.json and scripts/queue_items.txt are created, then condor_submit launches the DDSim gun-production campaign.
#Inputs: Hard-coded COMPACT_XML detector variant, hard-coded OUT_DIR EOS campaign destination, scripts/mk_ddsim_grid.py, configs/condor/ddsim.condor or scripts/ddsim.condor depending on local layout, and scripts/condor_ddsim.sh through the Condor submit file.
#Outputs: params/job_*.json per-job parameter files, params_ddsim.jsonl grid file, scripts/queue_items.txt Condor queue list, HTCondor DDSim jobs, and generated gun-sample ROOT files under OUT_DIR/eta_<eta>/.
#Collections: None directly; submitted DDSim jobs produce EDM4hep ROOT files whose downstream reco expects DCHCollection and related SimTrackerHit collections from the configured compact geometry.
#Connects-To: scripts/mk_ddsim_grid.py, configs/condor/ddsim.condor, scripts/condor_ddsim.sh, scripts/make_filelist.sh, scripts/submit_reco.sh
#Arguments:
#  COMPACT_XML: compact DD4hep XML detector/material variant used for the DDSim gun campaign; currently edited inside this script.
#  OUT_DIR: EOS output directory for generated gun samples; currently edited inside this script.
#  GRID_JSON: JSONL grid filename written by mk_ddsim_grid.py; default params_ddsim.jsonl.
#  TRANSFER_COMPACT: if 1, transfer the compact XML with each Condor job; if 0, workers read the XML from its EOS path. Default 0.
#  mk_ddsim_grid.py knobs: pt range, eta list, events per point, particle species, and theta smearing are currently fixed in the command inside this script.
#Notes:
#  This is the authoritative high-level submission entry point for DDSim gun-sample production in the current testTrackFinder workflow.
#  Update COMPACT_XML and OUT_DIR together for each detector/material variant so produced gun samples are clearly tied to the intended geometry.
#  The eta and pT grid here must remain synchronized with downstream make_filelist.sh, reco submission, analysis, and comparison expectations.
#  The script clears params/job_*.json and scripts/queue_items.txt before regenerating them, so do not store hand-written files there.
#  TRANSFER_COMPACT=0 is preferred when the worker can read the EOS XML reliably; TRANSFER_COMPACT=1 is useful when Condor file transfer is safer for a specific campaign.
#  The printed condor_submit command appends submit-time variables such as OUT_DIR, COMPACT_XML_ARG, and TRANSFER_COMPACT to the DDSim submit description.
#  Generated gun samples are upstream inputs to the reco pipeline: scripts/submit_reco.sh -> configs/condor/reco.condor -> scripts/reco_job.sh.
#Tags: authoritative, ddsim, gun-production, condor, eos, parameter-grid, submission, upstream
#DOC_END


# ---- EDIT THESE ----
COMPACT_XML="/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03_25umCF_0.2umNiP_1.2umAu.xml"
OUT_DIR="/eos/user/c/cglenn/gun_samples/1_29_2026/25umCF_0.2umNiP_1.2umAu"
GRID_JSON="params_ddsim.jsonl"
TRANSFER_COMPACT="${TRANSFER_COMPACT:-0}"   # 0: use EOS path on worker, 1: ship the XML file with each job
# --------------------

# Basic sanity
[[ -n "$COMPACT_XML" ]] || { echo "FATAL: COMPACT_XML empty" >&2; exit 2; }
[[ -n "$OUT_DIR"     ]] || { echo "FATAL: OUT_DIR empty" >&2; exit 3; }

# Local folders (these are local to the submission directory)
mkdir -p logs scripts params

# Ensure EOS output dir exists (important if you're writing new campaign dirs)
mkdir -p "$OUT_DIR"

echo "[prep] COMPACT_XML=$COMPACT_XML"
echo "[prep] OUT_DIR=$OUT_DIR"
echo "[prep] GRID_JSON=$GRID_JSON"
echo "[prep] TRANSFER_COMPACT=$TRANSFER_COMPACT"
echo

# --- Generate grid JSONL ---
echo "[prep] Generating grid -> $GRID_JSON"
python3 scripts/mk_ddsim_grid.py \
  --out "$GRID_JSON" \
  --pt-min 0.5 --pt-max 100 --pt-n 20 \
  --etas "0, 0.1, 0.5, 1.0, 1.5, 2.0" \
  --nev 5000 --particle mu- --theta-smear 0.0
echo "[prep] Wrote $(wc -l < "$GRID_JSON") lines to $GRID_JSON"
echo


echo "[prep] Clearing old params/ and queue_items.txt"
mkdir -p params
rm -f params/job_*.json
rm -f scripts/queue_items.txt

# --- Split into per-job JSON files + queue list ---
echo "[prep] Splitting JSONL into per-job files under params/"
: > scripts/queue_items.txt
job=0
while IFS= read -r line; do
  jf="params/job_${job}.json"
  printf '%s\n' "$line" > "$jf"
  echo "$(basename "$jf")" >> scripts/queue_items.txt
  job=$((job+1))
done < "$GRID_JSON"

echo "[prep] Prepared $job job files."
echo "[prep] First queue item: $(head -n1 scripts/queue_items.txt || true)"
echo

# --- Build submit-time -a options ---
# COMPACT_XML_ARG is argv[2] to condor_ddsim.sh
#  - TRANSFER_COMPACT=1: pass basename and transfer the XML
#  - TRANSFER_COMPACT=0: pass absolute EOS path (worker reads from EOS)
COMPACT_BASENAME="$(basename "$COMPACT_XML")"

SUBMIT_ARGS=(
  -a "OUT_DIR=$OUT_DIR"
)

if [[ "$TRANSFER_COMPACT" == "1" ]]; then
  echo "[prep] TRANSFER_COMPACT=1 -> will ship compact XML with each job"
  SUBMIT_ARGS+=(
    -a "COMPACT_XML_ARG=$COMPACT_BASENAME"
    -a "transfer_input_files=\$(transfer_input_files), $COMPACT_XML"
  )
else
  echo "[prep] TRANSFER_COMPACT=0 -> workers will read compact from EOS path"
  SUBMIT_ARGS+=(
    -a "COMPACT_XML_ARG=$COMPACT_XML"
  )
fi

# Extra: record the knob in the job environment for metadata stamping/debug prints
SUBMIT_ARGS+=( -a "TRANSFER_COMPACT=$TRANSFER_COMPACT" )

echo
echo "[prep] Submitting: condor_submit ${SUBMIT_ARGS[*]} scripts/ddsim.condor"
condor_submit "${SUBMIT_ARGS[@]}" scripts/ddsim.condor
