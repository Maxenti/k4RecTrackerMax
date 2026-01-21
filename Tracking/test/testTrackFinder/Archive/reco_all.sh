#!/usr/bin/env bash
set -euo pipefail

# ---- EDIT or override via env ----
IN_DIR="${IN_DIR:-/eos/user/c/cglenn/gun_samples}"
OUT_DIR="${OUT_DIR:-/eos/user/c/cglenn/reco_samples}"
COMPACT_XML="${COMPACT_XML:-/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml}"
MODEL_PATH="${MODEL_PATH:-/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/model.onnx}"

FITTER="${FITTER:-genfit2}"       # genfit2 | simple | threepoint
FIT_OUT="${FIT_OUT:-GenFitTracks}"
GF_USE_MAT="${GF_USE_MAT:-1}"     # only used for genfit2 (1=on, 0=off)
JOBS="${JOBS:-8}"                 # change to taste
EXTRA_ARGS="${EXTRA_ARGS:-}"      # e.g. "--fitterLog DEBUG --gf-seedPTMin 0.05"

# ----------------------------------

echo "[reco] IN_DIR=$IN_DIR"
echo "[reco] OUT_DIR=$OUT_DIR"
echo "[reco] COMPACT_XML=$COMPACT_XML"
echo "[reco] MODEL_PATH=$MODEL_PATH"
echo "[reco] FITTER=$FITTER  FIT_OUT=$FIT_OUT  GF_USE_MAT=$GF_USE_MAT  JOBS=$JOBS"

# Quick sanity
[[ -d "$IN_DIR" ]] || { echo "FATAL: IN_DIR not found: $IN_DIR" >&2; exit 2; }
[[ -s "$MODEL_PATH" ]] || { echo "FATAL: MODEL_PATH not found/empty: $MODEL_PATH" >&2; exit 3; }
if [[ "$FITTER" == "genfit2" && "$GF_USE_MAT" == "1" ]]; then
  [[ -s "$COMPACT_XML" ]] || { echo "FATAL: COMPACT_XML not found/empty: $COMPACT_XML" >&2; exit 4; }
fi

mkdir -p "$OUT_DIR" "$OUT_DIR/logs"

run_one() {
  local in="$1"

  # Recreate input subdir structure under OUT_DIR
  local rel="${in#$IN_DIR/}"                 # e.g. eta_+0.00/gun_eta+0.00_pt0.10.root
  local subdir="$(dirname "$rel")"           # e.g. eta_+0.00
  local base="$(basename "$rel")"            # e.g. gun_eta+0.00_pt0.10.root
  local out_sub="$OUT_DIR/$subdir"
  mkdir -p "$out_sub"

  # Output name: prefix with reco_
  local out="${out_sub}/reco_${base}"
  local log="$OUT_DIR/logs/${base}.log"

  # Material flag mapping (only for genfit2)
  local useMatArg=""
  if [[ "$FITTER" == "genfit2" ]]; then
    if [[ "$GF_USE_MAT" == "1" ]]; then
      useMatArg="--gf-useMat"
    else
      useMatArg="--no-gf-useMat"
    fi
  fi

  echo "[reco] $(date +%H:%M:%S)  $in  ->  $out"
  echo "CMD: python3 runDCHTestTrackFinder.py --inputFile '$in' --outputFile '$out' --compactXML '$COMPACT_XML' --modelPath '$MODEL_PATH' --stage fit --fitter '$FITTER' --fitOut '$FIT_OUT' --fitterLog INFO $useMatArg $EXTRA_ARGS" > "$log"

  # Run and tee log
  if ! python3 runDCHTestTrackFinder.py \
      --inputFile  "$in" \
      --outputFile "$out" \
      --compactXML "$COMPACT_XML" \
      --modelPath  "$MODEL_PATH" \
      --stage fit \
      --fitter "$FITTER" \
      --fitOut "$FIT_OUT" \
      --fitterLog INFO \
      $useMatArg \
      $EXTRA_ARGS \
      >> "$log" 2>&1; then
    echo "[reco][FAIL] $in (see $log)"
    return 1
  fi

  # Sanity check
  if [[ ! -s "$out" ]]; then
    echo "[reco][WARN] output not created or empty: $out (see $log)"
    return 1
  fi
  echo "[reco][OK] $out"
}

export -f run_one
export IN_DIR OUT_DIR COMPACT_XML MODEL_PATH FITTER FIT_OUT GF_USE_MAT EXTRA_ARGS

# Gather inputs (all .root files under IN_DIR)
mapfile -t inputs < <(find "$IN_DIR" -type f -name '*.root' | sort)
echo "[reco] found ${#inputs[@]} ROOT files under $IN_DIR"

# Run in parallel if available
if command -v parallel >/dev/null 2>&1; then
  parallel --halt now,fail=1 -j "$JOBS" run_one ::: "${inputs[@]}"
else
  echo "[reco] GNU parallel not found; running serially."
  for f in "${inputs[@]}"; do run_one "$f"; done
fi

echo "[reco] done. Outputs -> $OUT_DIR"
