#!/usr/bin/env bash
set -euo pipefail

# ---- EDIT THESE ----
COMPACT_XML="/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml"
OUT_DIR="/eos/user/c/cglenn/gun_samples/1_13_2026"
GRID_JSON="params_ddsim.jsonl"
TRANSFER_COMPACT="${TRANSFER_COMPACT:-0}"   # 0: use EOS path on worker, 1: ship the XML file with each job
# --------------------

mkdir -p logs scripts params "$OUT_DIR"

echo "[prep] Generating grid -> $GRID_JSON"
python3 scripts/mk_ddsim_grid.py \
  --out "$GRID_JSON" \
  --pt-min 0.1 --pt-max 200 --pt-n 5 \
  --etas "0, 0.1, 0.5, 1.0, 1.5, 2.0" \
  --nev 50 --particle mu- --theta-smear 0.0
echo "Wrote $(wc -l < "$GRID_JSON") lines to $GRID_JSON"

echo "[prep] Splitting JSONL into per-job files under params/"
: > scripts/queue_items.txt
job=0
while IFS= read -r line; do
  jf="params/job_${job}.json"
  echo "$line" > "$jf"
  echo "$(basename "$jf")" >> scripts/queue_items.txt
  job=$((job+1))
done < "$GRID_JSON"
echo "[prep] Prepared $job job files."
echo "[prep] First queue item: $(head -n1 scripts/queue_items.txt)"

# Build submit-time -a options
# COMPACT_XML_ARG is what the job will receive as argv[2]:
#  - if TRANSFER_COMPACT=1 we pass just the BASENAME and add the file to transfer list
#  - else we pass the ABSOLUTE PATH (EOS-visible) and do not transfer
COMPACT_BASENAME="$(basename "$COMPACT_XML")"

SUBMIT_ARGS=(-a "OUT_DIR=$OUT_DIR")
if [[ "$TRANSFER_COMPACT" == "1" ]]; then
  echo "[prep] TRANSFER_COMPACT=1 -> will ship compact XML with each job"
  SUBMIT_ARGS+=(
    -a "COMPACT_XML_ARG=$COMPACT_BASENAME"
    -a "transfer_input_files=\$(transfer_input_files), $COMPACT_XML"
  )
else
  echo "[prep] TRANSFER_COMPACT=0 -> workers will read compact from EOS path"
  SUBMIT_ARGS+=(-a "COMPACT_XML_ARG=$COMPACT_XML")
fi

echo "[prep] Submitting: condor_submit ${SUBMIT_ARGS[*]} scripts/ddsim.condor"
condor_submit "${SUBMIT_ARGS[@]}" scripts/ddsim.condor
