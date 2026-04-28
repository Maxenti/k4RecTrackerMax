#!/usr/bin/env bash
set -euo pipefail

IN_DIR="${IN_DIR:-/eos/user/c/cglenn/gun_samples}"
OUT_DIR="${OUT_DIR:-/eos/user/c/cglenn/reco_samples}"
COMPACT_XML="${COMPACT_XML:-/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml}"
MODEL_PATH="${MODEL_PATH:-/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/model.onnx}"

FITTER="${FITTER:-genfit2}"           # genfit2 | simple | threepoint
FIT_OUT="${FIT_OUT:-GenFitTracks}"
GF_USE_MAT="${GF_USE_MAT:-1}"         # 1=use material, 0=off (genfit2 only)
JOBS="${JOBS:-4}"
EXTRA_ARGS="${EXTRA_ARGS:-}"          # e.g. '--gf-seedPTMin 0.2 --gf-maxMeasPerGroup 120'
LOG_DIR="${LOG_DIR:-$OUT_DIR/logs}"   # per-file logs (optional)

echo "[reco] IN_DIR=$IN_DIR"
echo "[reco] OUT_DIR=$OUT_DIR"
echo "[reco] COMPACT_XML=$COMPACT_XML"
echo "[reco] MODEL_PATH=$MODEL_PATH"
echo "[reco] FITTER=$FITTER  FIT_OUT=$FIT_OUT  GF_USE_MAT=$GF_USE_MAT  JOBS=$JOBS"

mkdir -p "$OUT_DIR" "$LOG_DIR"

run_one() {
  local in="$1"
  local rel="${in#$IN_DIR/}"
  local subdir="$(dirname "$rel")"
  local base="$(basename "$rel")"
  local out_sub="$OUT_DIR/$subdir"
  mkdir -p "$out_sub"

  # just prefix "reco_" reliably
  local out="${out_sub}/reco_${base}"
  local log="${LOG_DIR}/${rel//\//_}.log"
  mkdir -p "$(dirname "$log")" || true

  echo "[reco] $in -> $out"
  echo "[reco] log: $log"

  local useMatArg=""
  if [[ "$FITTER" == "genfit2" ]]; then
    if [[ "$GF_USE_MAT" == "1" ]]; then
      useMatArg="--gf-useMat"
    else
      useMatArg="--no-gf-useMat"
    fi
  fi

  # show the exact command (goes to log as well)
  {
    echo "CMD: python3 runDCHTestTrackFinder.py \
      --inputFile '$in' --outputFile '$out' \
      --compactXML '$COMPACT_XML' --modelPath '$MODEL_PATH' \
      --stage fit --fitter '$FITTER' --fitOut '$FIT_OUT' \
      --fitterLog INFO $useMatArg $EXTRA_ARGS"
  } >>"$log"

  # run and tee the output
  ( set -x
    python3 /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/runDCHTestTrackFinder.py \
      --inputFile  "$in" \
      --outputFile "$out" \
      --compactXML "$COMPACT_XML" \
      --modelPath  "$MODEL_PATH" \
      --stage fit \
      --fitter "$FITTER" \
      --fitOut "$FIT_OUT" \
      --fitterLog INFO \
      $useMatArg \
      $EXTRA_ARGS
  ) &>>"$log"

  # basic sanity check
  if [[ ! -s "$out" ]]; then
    echo "[reco][WARN] output not created or empty: $out (see $log)"
    return 1
  fi

  echo "[reco] done: $out"
}

export -f run_one
export IN_DIR OUT_DIR COMPACT_XML MODEL_PATH FITTER FIT_OUT GF_USE_MAT EXTRA_ARGS LOG_DIR

mapfile -t inputs < <(find "$IN_DIR" -type f -name '*.root' | sort)
echo "[reco] found ${#inputs[@]} ROOT files under $IN_DIR"

if command -v parallel >/dev/null 2>&1; then
  parallel -j "$JOBS" run_one ::: "${inputs[@]}"
else
  echo "[reco] GNU parallel not found; running serially."
  for f in "${inputs[@]}"; do run_one "$f"; done
fi

echo "[reco] all done. Outputs in $OUT_DIR"
