#!/usr/bin/env bash
set -euo pipefail

# -------- EDIT THESE --------
IN_DIR="${IN_DIR:-/eos/user/c/cglenn/gun_samples/1_14_2026}"   # where DDSim gun files live
OUT_DIR="${OUT_DIR:-/eos/user/c/cglenn/reco_samples2/1_14_2026}"
COMPACT_XML="${COMPACT_XML:-/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml}"
MODEL_PATH="${MODEL_PATH:-/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/model.onnx}"

FITTER="${FITTER:-genfit2}"             # genfit2 | simple | threepoint
FIT_OUT="${FIT_OUT:-GenFitTracks}"
GF_USE_MAT="${GF_USE_MAT:-1}"           # 1=use material (genfit2), 0=off
EXTRA="${EXTRA:---fitterLog INFO}"       # any additional flags (quotes OK)
# ----------------------------

cd "$(dirname "$0")"   # scripts/
mkdir -p logs

# Ensure submit file exists
if [[ ! -s reco.condor ]]; then
  echo "FATAL: scripts/reco.condor missing. Create it first." >&2
  exit 2
fi

# Build queue file
QUEUE="reco_queue.txt"
rm -f "$QUEUE"

echo "[prep] Scanning $IN_DIR for .root files..."
mapfile -t files < <(find "$IN_DIR" -type f -name '*.root' | sort)

echo "[prep] Found ${#files[@]} files."
if (( ${#files[@]} == 0 )); then
  echo "No inputs found under $IN_DIR" >&2
  exit 3
fi

for f in "${files[@]}"; do
  # Quote EXTRA to pass as a single field
  echo "in=$f outdir=$OUT_DIR compact=$COMPACT_XML model=$MODEL_PATH fitter=$FITTER fitout=$FIT_OUT usemat=$GF_USE_MAT extra=\"$EXTRA\"" >> "$QUEUE"
done

echo "[prep] Sample queue line:"
head -n1 "$QUEUE" || true

# Submit
echo "[prep] Submitting $(wc -l < "$QUEUE") reco jobs to Condor..."
condor_submit reco.condor
