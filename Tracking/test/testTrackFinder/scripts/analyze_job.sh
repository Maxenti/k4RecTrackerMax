#!/usr/bin/env bash
set -euo pipefail

echo "[env] hostname=$(hostname)"
echo "[env] pwd=$(pwd)"
echo "[env] date=$(date -Is)"

INPUT_DIR="${1:?need input dir}"
EOS_OUT="${2:?need EOS output .root path}"
TRACK_COLL="${3:-GenFitTracks}"
HIT_COLL="${4:-OutputWireHitsGGTF}"

# Optional overrides (you can add more if you want)
QUALITY_CUT="${5:-none}"
MIN_PHISPAN="${6:-0.06}"
MIN_CHORDXY="${7:-500.0}"
MAX_CIRCLECOND="${8:-1e6}"
CENTRAL_FRAC="${9:-0.95}"

# ---- Setup Key4HEP / ROOT ----
# If you already use runtime.tgz with a pinned env, keep that pattern:
if [[ -f "runtime.tgz" ]]; then
  echo "[env] extracting runtime.tgz"
  tar -xzf runtime.tgz
fi

# Prefer an explicit setup path if you have one, otherwise try a common CVMFS entry.
# You can also hardcode your known-good setup script here.
if [[ -n "${KEY4HEP_SETUP:-}" && -f "${KEY4HEP_SETUP}" ]]; then
  echo "[env] sourcing KEY4HEP_SETUP=${KEY4HEP_SETUP}"
  source "${KEY4HEP_SETUP}"
else
  if [[ -f /cvmfs/sw.hsf.org/key4hep/setup.sh ]]; then
    echo "[env] sourcing /cvmfs/sw.hsf.org/key4hep/setup.sh"
    source /cvmfs/sw.hsf.org/key4hep/setup.sh
  else
    echo "[env] ERROR: no Key4HEP setup found (set KEY4HEP_SETUP or ship env in runtime.tgz)"
    exit 2
  fi
fi

python3 -V
python3 -c "import ROOT; print('PyROOT OK:', ROOT.gROOT.GetVersion())"

# Make sure local imports work (scan_pt_time_by_event.py next to your analyzer)
export PYTHONPATH="${PWD}:${PYTHONPATH:-}"

# ---- Run analysis ----
OUT_LOCAL="ptres_${CLUSTER:-${CONDOR_CLUSTER_ID:-0}}_${PROCESS:-${CONDOR_PROC_ID:-0}}.root"

echo "[run] INPUT_DIR=${INPUT_DIR}"
echo "[run] OUT_LOCAL=${OUT_LOCAL}"
echo "[run] EOS_OUT=${EOS_OUT}"

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
# Use xrdcp for reliability.
# EOS_OUT should be like: /eos/user/c/cglenn/.../out.root
EOS_DIR="$(dirname "${EOS_OUT}")"
mkdir -p "${EOS_DIR}" || true

echo "[copy] xrdcp -> ${EOS_OUT}"
xrdcp -f "${OUT_LOCAL}" "${EOS_OUT}"

echo "[ok] done"
