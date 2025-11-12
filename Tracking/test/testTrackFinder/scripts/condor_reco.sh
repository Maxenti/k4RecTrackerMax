#!/usr/bin/env bash
# scripts/reco_runner.sh
set -eo pipefail

SETUP_RC="${1:?need setup.rc}"; shift
INFILE="${1:?need input ROOT file}"; shift
OUT_DIR="${1:?need out dir}"; shift
COMPACT_XML="${1:?need compact XML}"; shift
MODEL_PATH="${1:?need model.onnx}"; shift
FITTER="${1:-genfit2}"; shift || true
GF_USE_MAT="${1:-1}"; shift || true

echo "[runner] setup=$SETUP_RC"
echo "[runner] in=$INFILE"
echo "[runner] out_dir=$OUT_DIR"

# --- source user env with nounset OFF and args hidden ---
__saved_args=("$@")
set +u
set --
# shellcheck source=/dev/null
source "$SETUP_RC"
set -- "${__saved_args[@]}"
# keep nounset off for the rest of the script
# set -u 2>/dev/null || true

echo "[runner] python=$(command -v python3)"
echo "[runner] PWD=$PWD"

# material flag only matters for genfit2
useMatArg=""
if [[ "$FITTER" == "genfit2" ]]; then
  [[ "$GF_USE_MAT" == "1" ]] && useMatArg="--gf-useMat" || useMatArg="--no-gf-useMat"
fi

base="$(basename "$INFILE")"
OUT_FILE="$OUT_DIR/reco_${base}"
mkdir -p "$OUT_DIR"

set -x
python3 runDCHTestTrackFinder.py \
  --inputFile  "$INFILE" \
  --outputFile "$OUT_FILE" \
  --compactXML "$COMPACT_XML" \
  --modelPath  "$MODEL_PATH" \
  --stage fit \
  --fitter "$FITTER" \
  --fitOut GenFitTracks \
  --fitterLog INFO \
  $useMatArg
set +x

[[ -s "$OUT_FILE" ]] || { echo "FATAL: missing output $OUT_FILE"; exit 10; }
echo "[runner] done -> $OUT_FILE"
