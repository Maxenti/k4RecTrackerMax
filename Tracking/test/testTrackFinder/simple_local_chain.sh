#!/bin/bash
# simple_local_chain.sh — run DCHdigi + GGTF + SimpleFit
set -euo pipefail

DEFAULT_INPUT="sim_local.root"
DEFAULT_OUTPUT="reco_simple.root"
DEFAULT_MODEL_SPEC="/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/model.onnx"
DEFAULT_COMPACT_XML="/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml"
DEFAULT_DCH_SIMHITS="DCHCollection"
DEFAULT_DCH_NAME="DCH_v2"

INPUT="${1:-$DEFAULT_INPUT}"
OUTPUT="${2:-$DEFAULT_OUTPUT}"
MODEL_SPEC="${3:-$DEFAULT_MODEL_SPEC}"
COMPACT_XML="${4:-$DEFAULT_COMPACT_XML}"
DCH_SIMHITS="${5:-$DEFAULT_DCH_SIMHITS}"
DCH_NAME="${6:-$DEFAULT_DCH_NAME}"

# GGTF
: "${GGTF_LOG:=INFO}"
: "${TBETA:=0.06}"
: "${TD:=0.06}"
: "${ONNX_CHUNK:=4096}"
: "${WIRE_GATE_MM:=12.0}"
: "${MAX_3D_PER_EVT:=100000}"
: "${MAX_3D_PER_TRK:=10000}"
: "${MAX_HITS:=8000}"

# Simple fitter
: "${SF_BZ:=2.0}"
: "${SF_PDG:=13}"
: "${SF_MIN_GROUP:=6}"
: "${SF_EPS_MM:=20.0}"
: "${SF_MIN_PTS:=6}"
: "${SF_DEDUP:=1}"
: "${SF_DEDUP_TOL:=0.25}"
: "${FIT_OUT:=SimpleTracks}"
: "${FITTER_LOG:=INFO}"

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TORCH_NUM_THREADS=1
export MALLOC_ARENA_MAX=2
export ORT_DISABLE_MEMORY_ARENA=1
export ORT_ENABLE_MEM_PATTERN=0

echo "[cfg] INPUT=$INPUT OUTPUT=$OUTPUT MODEL=$MODEL_SPEC COMPACT=$COMPACT_XML DCH_NAME=$DCH_NAME"

K4_ARGS=(
  ./SimplerunDCHTestTrackFinder.py
  --inputFile  "$INPUT"
  --outputFile "$OUTPUT"
  --modelPath  "$MODEL_SPEC"
  --compactXML "$COMPACT_XML"
  --dchName    "$DCH_NAME"
  --dchSimHits "$DCH_SIMHITS"
  --ggtfLog    "$GGTF_LOG"
  --tbeta      "$TBETA"
  --td         "$TD"
  --onnxChunk  "$ONNX_CHUNK"
  --wireGateMM "$WIRE_GATE_MM"
  --max3DHitsPerEvent "$MAX_3D_PER_EVT"
  --max3DPerTrack     "$MAX_3D_PER_TRK"
  --produce3DHits
  --maxHitsPerEvent "$MAX_HITS"
  --fitter simple
  --fitOut "$FIT_OUT"
  --fitterLog "$FITTER_LOG"
  --sf-bz "$SF_BZ"
  --sf-pdg "$SF_PDG"
  --sf-minGroup "$SF_MIN_GROUP"
  --sf-epsMM "$SF_EPS_MM"
  --sf-minPts "$SF_MIN_PTS"
  --sf-dedupTol "$SF_DEDUP_TOL"
)
[[ "$SF_DEDUP" == "1" ]] && K4_ARGS+=( --sf-dedup )

echo "[k4run] args: ${K4_ARGS[*]}"
k4run "${K4_ARGS[@]}"
