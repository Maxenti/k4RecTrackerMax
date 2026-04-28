# DOC:
# Summary: Condor worker wrapper that runs pT-resolution grid analysis on a reco-output campaign and copies the summary ROOT file to EOS.
# Status: authoritative
# Usage:
#   ./analyze_job.sh INPUT_DIR EOS_OUT [TRACK_COLL] [HIT_COLL] [QUALITY_CUT] [MIN_PHISPAN] [MIN_CHORDXY] [MAX_CIRCLECOND] [CENTRAL_FRAC]
#   ./analyze_job.sh --inputDir INPUT_DIR --eosOut EOS_OUT --trackCollection GenFitTracks --hitCollection OutputWireHitsGGTF --qualityCut none --minPhiSpan 0.06 --minChordXY 500.0 --maxCircleCond 1e6 --centralFrac 0.95
# Examples:
#   ./analyze_job.sh \
#     /eos/.../reco_samples2/CF25_Au2p227matched \
#     /eos/.../final_analysis/CF25_Au2p227matched_ptres.root \
#     GenFitTracks OutputWireHitsGGTF none 0.06 500.0 1e6 0.95
# Inputs: Reco campaign directory containing eta_* subdirectories with reco_*.root files; analyze_pt_resolution_grid.py staged in the worker directory; optional runtime.tgz; Key4HEP/ROOT environment.
# Outputs: Local ptres_<cluster>_<process>.root summary file copied to EOS_OUT with xrdcp.
# Collections: Reads TRACK_COLL, normally GenFitTracks; reads HIT_COLL, normally OutputWireHitsGGTF; writes analysis ROOT objects produced by scripts/analyze_pt_resolution_grid.py.
# Connects-To: scripts/analyze_pt_resolution_grid.py, configs/condor/analyze.condor, configs/condor/analyze_CF25_Au2p227matched.condor, configs/condor/analyze_W20_Au0p3_defaultlike.condor, scripts/compare_pt_resolution_grid.py, scripts/summarize_ptres_improvement.py
# Arguments:
#   INPUT_DIR / --inputDir: reco output campaign directory to analyze; expected to contain eta_* folders.
#   EOS_OUT / --eosOut: final EOS ROOT output path for the pT-resolution summary.
#   TRACK_COLL / --trackCollection: reconstructed track collection to analyze; default GenFitTracks.
#   HIT_COLL / --hitCollection: hit collection used by the analysis scanner; default OutputWireHitsGGTF.
#   QUALITY_CUT / --qualityCut: event/track quality mode passed to analysis; allowed values are none, curv, curv_circle.
#   MIN_PHISPAN / --minPhiSpan: minimum phi span used by curvature-observability diagnostics; default 0.06.
#   MIN_CHORDXY / --minChordXY: minimum transverse chord length in mm used by diagnostics; default 500.0.
#   MAX_CIRCLECOND / --maxCircleCond: maximum accepted circle-fit condition number for diagnostics; default 1e6.
#   CENTRAL_FRAC / --centralFrac: central fraction used for robust/truncated statistics; default 0.95.
#   K4REL: Key4HEP nightly release sourced on the worker node; default 2026-04-22.
#   KEY4HEP_SETUP: optional override for the Key4HEP setup.sh path.
# Notes:
#   This is the batch-side analysis wrapper, not the reco job wrapper.
#   Keep the analysis cuts identical between detector/material variants when producing CF-vs-W closeout comparisons.
#   The script accepts both positional arguments and explicit flags so campaign-specific Condor files can remain readable.
#   If runtime.tgz is present, it is unpacked before analysis, but the analysis script must still be available as analyze_pt_resolution_grid.py in the worker directory or staged runtime.
#   The output ROOT file is first written locally, checked for nonzero size, then copied to EOS using xrdcp.
#   This script intentionally sources the same Key4HEP nightly family used by reco so ROOT/EDM dictionary behavior stays consistent.
# Tags: authoritative, analysis, condor, pt-resolution, eos, root, closeout, genfittracks
# DOC_END

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

# Pin to the same nightly used for reco
K4REL="${K4REL:-2026-04-22}"

# -----------------------
# Parse args (flags or positional)
# -----------------------
if [[ $# -eq 0 ]]; then
  usage
  exit 2
fi

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
echo "[cfg] K4REL=${K4REL}"

# -----------------------
# Helpers
# -----------------------
to_xrd() {
  local p="$1"
  if [[ "$p" == root://* ]]; then
    echo "$p"
  elif [[ "$p" == /eos/* ]]; then
    echo "root://eosuser.cern.ch//${p}"
  else
    echo "$p"
  fi
}

eos_path_from_xrd() {
  echo "$1" | sed -E 's#^root://eosuser\.cern\.ch##'
}

# -----------------------
# Optional runtime unpack
# -----------------------
if [[ -f "runtime.tgz" ]]; then
  echo "[env] extracting runtime.tgz"
  tar -xzf runtime.tgz
fi

# -----------------------
# Setup Key4HEP / ROOT
# -----------------------
source_key4hep() {
  local setup_path="${1:?need setup path}"
  echo "[env] sourcing ${setup_path} -r ${K4REL} (temporarily disabling nounset)"
  set +u
  # shellcheck disable=SC1090
  source "${setup_path}" -r "${K4REL}"
  set -u
}

if [[ -n "${KEY4HEP_SETUP:-}" && -f "${KEY4HEP_SETUP}" ]]; then
  source_key4hep "${KEY4HEP_SETUP}"
elif [[ -f /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh ]]; then
  source_key4hep /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh
else
  echo "[env] ERROR: no Key4HEP nightly setup found"
  exit 2
fi

python3 -V
python3 -c "import ROOT; print('PyROOT OK:', ROOT.gROOT.GetVersion())"

# Make current worker directory importable
export PYTHONPATH="${PWD}:${PYTHONPATH:-}"

# -----------------------
# Run analysis
# -----------------------
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

[[ -s "${OUT_LOCAL}" ]] || { echo "[err] missing or empty output: ${OUT_LOCAL}"; exit 5; }

ls -lh "${OUT_LOCAL}"

# -----------------------
# Copy output to EOS
# -----------------------
EOS_OUT_XRD="$(to_xrd "${EOS_OUT}")"
EOS_OUT_PATH_ON_EOS="$(eos_path_from_xrd "${EOS_OUT_XRD}")"

echo "[copy] EOS_OUT_XRD=${EOS_OUT_XRD}"

if command -v xrdfs >/dev/null 2>&1; then
  xrdfs eosuser.cern.ch mkdir -p "$(dirname "${EOS_OUT_PATH_ON_EOS}")" >/dev/null 2>&1 || true
fi

echo "[copy] xrdcp -> ${EOS_OUT_XRD}"
xrdcp -f "${OUT_LOCAL}" "${EOS_OUT_XRD}"

echo "[ok] done"