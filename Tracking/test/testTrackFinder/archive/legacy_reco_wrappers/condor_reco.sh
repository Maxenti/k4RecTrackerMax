#!/usr/bin/env bash
# scripts/reco_runner.sh


#DOC:
#Summary: Legacy reco worker wrapper that directly runs runDCHTestTrackFinder.py after sourcing a setup.rc environment.
#Status: legacy
#Usage:
#  ./condor_reco.sh SETUP_RC INFILE OUT_DIR COMPACT_XML MODEL_PATH [FITTER] [GF_USE_MAT]
#Examples:
#  ./condor_reco.sh setup.rc input.root /eos/.../reco IDEA.xml model.onnx genfit2 1
#Inputs: setup.rc environment file, one input ROOT file, output directory, compact DD4hep XML, GGTF ONNX model, optional fitter/material flags.
#Outputs: reco_<input>.root written directly under OUT_DIR.
#Collections: Runs steering/runDCHTestTrackFinder.py with stage=fit and fitOut=GenFitTracks; expected chain is DCHCollection -> DCH digi -> CDCHTracks -> GenFitTracks.
#Connects-To: steering/runDCHTestTrackFinder.py, scripts/submit_reco.sh, configs/condor/reco.condor, scripts/reco_job.sh
#Arguments:
#  SETUP_RC: shell setup file sourced before running reco.
#  INFILE: input EDM4hep ROOT file.
#  OUT_DIR: output directory for reco_<input>.root.
#  COMPACT_XML: compact DD4hep XML passed to steering.
#  MODEL_PATH: GGTF ONNX model path.
#  FITTER: fitter mode, default genfit2.
#  GF_USE_MAT: material-effects toggle for GenFit2, default 1.
#Notes:
#  Superseded by the maintained Condor reco pipeline: scripts/submit_reco.sh -> configs/condor/reco.condor -> scripts/reco_job.sh.
#  Does not expose the full current reco knob surface and does not pass the current TGeo geometry argument.
#  Should not be used for production CF-vs-W or pT-resolution closeout campaigns.
#  Keep only as historical reference if needed; otherwise archive under archive/legacy_reco_wrappers/.
#Tags: legacy, reco, condor, superseded, genfit2, ggtf
#DOC_END



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
