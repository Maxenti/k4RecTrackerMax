#!/usr/bin/env bash
set -euo pipefail

echo "[env] hostname=$(hostname)"
echo "[env] pwd=$(pwd)"
echo "[env] date=$(date -Is)"

usage() {
  cat <<EOF
Usage:
  $0 INPUT_DIR EOS_OUT [TRACK_COLL] [HIT_COLL] [QUALITY_CUT] [MIN_PHISPAN] [MIN_CHORDXY] [MAX_CIRCLECOND] [CENTRAL_FRAC]

Or using flags:
  $0 --inputDir DIR --eosOut /eos/.../out.root [--trackCollection GenFitTracks] [--hitCollection OutputWireHitsGGTF]
     [--qualityCut none|curv|curv_circle] [--minPhiSpan 0.06] [--minChordXY 500] [--maxCircleCond 1e6] [--centralFrac 0.95]
EOF
}

# -----------------------
# Defaults
# -----------------------
INPUT_DIR=""
EOS_OUT=""
TRACK_COLL="GenFitTracks"
HIT_COLL="OutputWireHitsGGTF"
QUALITY_CUT="none"
MIN_PHISPAN="0.06"
MIN_CHORDXY="500.0"
MAX_CIRCLECOND="1e6"
CENTRAL_FRAC="0.95"

# -----------------------
# Parse args (flags or positional)
# -----------------------
if [[ $# -eq 0 ]]; then
  usage
  exit 2
fi

# If first arg starts with --, parse flags. Else parse positional.
if [[ "${1}" == --* ]]; then
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --inputDir)        INPUT_DIR="${2:?}"; shift 2 ;;
      --eosOut)          EOS_OUT="${2:?}"; shift 2 ;;
      --trackCollection) TRACK_COLL="${2:?}"; shift 2 ;;
      --hitCollection)   HIT_COLL="${2:?}"; shift 2 ;;
      --qualityCut)      QUALITY_CUT="${2:?}"; shift 2 ;;
      --minPhiSpan)      MIN_PHISPAN="${2:?}"; shift 2 ;;
      --minChordXY)      MIN_CHORDXY="${2:?}"; shift 2 ;;
      --maxCircleCond)   MAX_CIRCLECOND="${2:?}"; shift 2 ;;
      --centralFrac)     CENTRAL_FRAC="${2:?}"; shift 2 ;;
      -h|--help)         usage; exit 0 ;;
      *)
        echo "[err] Unknown option: $1"
        usage
        exit 2
        ;;
    esac
  done
else
  INPUT_DIR="${1:?need input dir}"
  EOS_OUT="${2:?need EOS output .root path}"
  TRACK_COLL="${3:-${TRACK_COLL}}"
  HIT_COLL="${4:-${HIT_COLL}}"
  QUALITY_CUT="${5:-${QUALITY_CUT}}"
  MIN_PHISPAN="${6:-${MIN_PHISPAN}}"
  MIN_CHORDXY="${7:-${MIN_CHORDXY}}"
  MAX_CIRCLECOND="${8:-${MAX_CIRCLECOND}}"
  CENTRAL_FRAC="${9:-${CENTRAL_FRAC}}"
fi

# -----------------------
# Validate quality cut
# -----------------------
case "${QUALITY_CUT}" in
  none|curv|curv_circle) ;;
  *)
    echo "[err] QUALITY_CUT='${QUALITY_CUT}' is invalid. Must be one of: none, curv, curv_circle"
    echo "      (This usually means your 5th positional argument is wrong.)"
    exit 2
    ;;
esac

echo "[cfg] INPUT_DIR=${INPUT_DIR}"
echo "[cfg] EOS_OUT=${EOS_OUT}"
echo "[cfg] TRACK_COLL=${TRACK_COLL}"
echo "[cfg] HIT_COLL=${HIT_COLL}"
echo "[cfg] QUALITY_CUT=${QUALITY_CUT}"
echo "[cfg] MIN_PHISPAN=${MIN_PHISPAN}"
echo "[cfg] MIN_CHORDXY=${MIN_CHORDXY}"
echo "[cfg] MAX_CIRCLECOND=${MAX_CIRCLECOND}"
echo "[cfg] CENTRAL_FRAC=${CENTRAL_FRAC}"

# ---- Setup Key4HEP / ROOT ----
if [[ -f "runtime.tgz" ]]; then
  echo "[env] extracting runtime.tgz"
  tar -xzf runtime.tgz
fi

source_key4hep() {
  local setup_path="${1:?need setup path}"
  echo "[env] sourcing ${setup_path} (temporarily disabling nounset)"
  set +u
  # shellcheck disable=SC1090
  source "${setup_path}"
  set -u
}

if [[ -n "${KEY4HEP_SETUP:-}" && -f "${KEY4HEP_SETUP}" ]]; then
  source_key4hep "${KEY4HEP_SETUP}"
elif [[ -f /cvmfs/sw.hsf.org/key4hep/setup.sh ]]; then
  source_key4hep /cvmfs/sw.hsf.org/key4hep/setup.sh
else
  echo "[env] ERROR: no Key4HEP setup found (set KEY4HEP_SETUP or ship env in runtime.tgz)"
  exit 2
fi

python3 -V
python3 -c "import ROOT; print('PyROOT OK:', ROOT.gROOT.GetVersion())"
export PYTHONPATH="${PWD}:${PYTHONPATH:-}"

# ---- Run analysis ----
OUT_LOCAL="ptres_${CLUSTER:-${CONDOR_CLUSTER_ID:-0}}_${PROCESS:-${CONDOR_PROC_ID:-0}}.root"

echo "[run] OUT_LOCAL=${OUT_LOCAL}"

python3 analyze_pt_resolution_grid.py \
  --inputDir "${INPUT_DIR}" \
  --outRoot "${OUT_LOCAL}" \
  --trackCollection "${TRACK_COLL}" \
  --hitCollection "${HIT_COLL}" \
  --qualityCut "${QUALITY_CUT}" \
  --minPhiSpan "${MIN_PHISPAN}" \
  --minChordXY "${MIN_CHORDXY}" \
  --maxCircleCond "${MAX_CIRCLECOND}" \
  --centralFrac "${CENTRAL_FRAC}"

ls -lh "${OUT_LOCAL}"

# ---- Copy output to EOS ----
EOS_DIR="$(dirname "${EOS_OUT}")"

if [[ "${EOS_DIR}" == /eos/* ]]; then
  if [[ -d /eos ]]; then
    echo "[copy] ensuring EOS dir exists via local mount: ${EOS_DIR}"
    mkdir -p "${EOS_DIR}" || true
  else
    echo "[copy] /eos not mounted on this node; assuming EOS_DIR already exists: ${EOS_DIR}"
  fi
else
  echo "[copy] EOS_OUT is not under /eos; using local mkdir -p: ${EOS_DIR}"
  mkdir -p "${EOS_DIR}" || true
fi

echo "[copy] xrdcp -> ${EOS_OUT}"
xrdcp -f "${OUT_LOCAL}" "${EOS_OUT}"

echo "[ok] done"
