#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# prepare_and_submit.sh
# - Generates a JSONL grid of (pt, eta) points
# - Splits into per-job JSON files under params/
# - Writes queue file scripts/queue_items.txt
# - Submits HTCondor jobs, optionally transferring the compact XML
#
# Notes / fixes vs old:
# - Ensures OUT_DIR exists on EOS (mkdir -p)
# - Uses a stable tag for this production (date or custom) without changing behavior
# - Keeps TRANSFER_COMPACT logic, but avoids relying on "scripts/" being in transfer list
# - No behavior changes to mk_ddsim_grid.py usage; just safer plumbing + clearer logging
# -----------------------------------------------------------------------------

# ---- EDIT THESE ----
COMPACT_XML="/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml"
OUT_DIR="/eos/user/c/cglenn/gun_samples/1_18_2026"
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
  --pt-min 0.5 --pt-max 50 --pt-n 15 \
  --etas "0, 0.1, 0.5, 1.0, 1.5, 2.0, 2.5" \
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
