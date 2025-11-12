#!/usr/bin/env bash
set -euo pipefail

# ----------------------------------------------------------------------
# Use the SAME Key4hep release/nightly you built the runtime with
# ----------------------------------------------------------------------

# ---------------- Key4HEP env (pinned) ----------------
if [[ ! -r /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh ]]; then
  echo "[env][FATAL] /cvmfs/sw-nightlies.hsf.org not readable inside this job."
  exit 12
fi
K4SETUP="$(/bin/readlink -f /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh || echo /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh)"

__orig_args=("$@")
set +u; set -- ; source "$K4SETUP" -r 2025-09-21; set -- "${__orig_args[@]}"; set -u 2>/dev/null || true
echo "[env] Using Key4hep release:" 
command -v k4run >/dev/null || { echo "FATAL: k4run not in PATH"; exit 10; }

# ---------------- Arguments: ONE FILE PER JOB ----------------
INFILE="${1:?need INFILE}"
OUTDIR="${2:?need OUTDIR}"
COMPACT_XML="${3:?need COMPACT_XML}"
FITTER="${4:-simple}"         # genfit2|simple|threepoint|none
GF_USE_MAT="${5:-1}"           # 1/0
STAGE="${6:-fit}"              # digi|ggtf|fit
FIT_OUT="${7:-auto}"           # auto|<name>
EXTRA_ARGS="${8-}"             # optional extra CLI flags

echo "[args] INFILE=$INFILE"
echo "[args] OUTDIR=$OUTDIR"
echo "[args] COMPACT_XML=$COMPACT_XML  FITTER=$FITTER GF_USE_MAT=$GF_USE_MAT STAGE=$STAGE FIT_OUT=$FIT_OUT"
[[ -n "${EXTRA_ARGS}" ]] && echo "[args] EXTRA_ARGS=${EXTRA_ARGS}"

[[ -s runtime.tgz    ]] || { echo "FATAL: runtime.tgz missing"; exit 4; }
[[ -s "$COMPACT_XML" ]] || { echo "FATAL: compact missing: $COMPACT_XML"; exit 3; }

# If the input is on EOS POSIX, switch to XRootD for reading.
if [[ "$INFILE" == /eos/* ]]; then
  INFILE_XRD="root://eosuser.cern.ch//${INFILE#/}"
else
  INFILE_XRD="$INFILE"
fi
echo "[io] will read input: $INFILE_XRD"

# ---------------- Unpack runtime bundle ----------------
tar -xzf runtime.tgz
RTPFX="$PWD/runtime"

# --- Env for the bundled libs/plugins/python -----------------
export LD_LIBRARY_PATH="$RTPFX/lib64:$RTPFX/lib:${LD_LIBRARY_PATH:-}"
export GAUDI_PLUGIN_PATH="$RTPFX/lib64:$RTPFX/lib:${GAUDI_PLUGIN_PATH:-}"

# Build GAUDI_COMPONENT_PATH from catalogs (incl. confdb if present)
COMP_BASE="$RTPFX/share"
COMP_DIRS=("$COMP_BASE" "$RTPFX/share/k4rt-lib-catalogs")
if [[ -d "$COMP_BASE" ]]; then
  while IFS= read -r -d '' f; do
    d="$(dirname "$f")"
    [[ " ${COMP_DIRS[*]-} " == *" $d "* ]] || COMP_DIRS+=("$d")
  done < <(find "$COMP_BASE" -type f \( -name '*.components*' -o -name 'components*.*' -o -name '*.confdb' \) -print0 || true)
fi
export GAUDI_COMPONENT_PATH="$(IFS=:; echo "${COMP_DIRS[*]}"):${GAUDI_COMPONENT_PATH:-}"
export GAUDI_COMPONENTS_PATH="$GAUDI_COMPONENT_PATH"
export GAUDI_CONFIGURABLE_DB_PATH="$GAUDI_COMPONENT_PATH"
export GAUDI_USE_CONFIGURATION_DB=1
export PYTHONPATH="$RTPFX/python:${PYTHONPATH:-}"

# Strongly hint Gaudi to load these plugins at startup (colon- or space-separated is ok)
export GAUDI_PLUGINS="libTracking:libDCHdigi:libDDRec:libk4FWCorePlugins${GAUDI_PLUGINS:+:$GAUDI_PLUGINS}"

# Helpful diagnostics
echo "[env] GAUDI_PLUGIN_PATH=$GAUDI_PLUGIN_PATH"
echo "[env] GAUDI_COMPONENT_PATH=$GAUDI_COMPONENT_PATH"
echo "[env] GAUDI_PLUGINS=$GAUDI_PLUGINS"


# DD4hep include path for the compact
export DD4hep_XMLPATH="$(dirname "$COMPACT_XML"):${DD4hep_XMLPATH:-}"

# --- Preload a few libs & sanity-check fitter is visible
python3 - <<'PY'
import os, ROOT, sys
for lib in ("libTracking","libDCHdigi","libDDRec","libk4FWCorePlugins"):
    rc = ROOT.gSystem.Load(lib)
    print(f"[check] ROOT Load {lib}: rc={rc}")
try:
    from Configurables import GenFit2DCHFitter
    print("[check] OK: GenFit2DCHFitter importable")
except Exception as e:
    print("[check][WARN] GenFit2DCHFitter not importable:", e)
PY

# ---------------- Model path resolution ----------------
MODEL="${MODEL:-}"
if [[ -z "${MODEL}" ]]; then
  if [[ -s "$RTPFX/models/model.onnx" ]]; then
    MODEL="$RTPFX/models/model.onnx"
  else
    _cand="$(find "$RTPFX" -maxdepth 3 -type f -name 'model.onnx' 2>/dev/null | head -n1 || true)"
    MODEL="${_cand:-}"
  fi
fi
[[ -s "$MODEL" ]] || { echo "FATAL: ONNX model not found in runtime"; exit 5; }
echo "[env] Using ONNX model: $MODEL"

# ---------------- Output naming ----------------
rel="${INFILE#/eos/user/c/cglenn/gun_samples/}"
# If the input wasn't under /eos/user/c/cglenn/gun_samples, keep flat
if [[ "$rel" == "$INFILE" ]]; then rel="$(basename "$INFILE")"; fi
subdir="$(dirname "$rel")"
base="$(basename "$rel")"
OUT_LOCAL="$PWD/reco_${base}"
OUT_EOS="${OUTDIR%/}/$subdir/reco_${base}"
echo "[run] local_out=$OUT_LOCAL"
echo "[run] eos_out  =$OUT_EOS"

# Ensure EOS parent exists (best-effort)
if [[ "$OUT_EOS" == /eos/* ]]; then
  command -v xrdfs >/dev/null 2>&1 && xrdfs eosuser.cern.ch mkdir -p "//${OUT_EOS#/}/../" >/dev/null 2>&1 || true
fi
mkdir -p "$(dirname "$OUT_LOCAL")"

# ===================== KNOBS =====================
: "${GGTF_LOG:=INFO}"
: "${PRODUCE_3DHITS:=1}"
: "${MAX_HITS:=15000}"
: "${TIMEOUT_K4RUN:=0}"

: "${TBETA:=0.08}"
: "${TD:=0.18}"

: "${ONNX_CHUNK:=2048}"
: "${WIRE_GATE_MM:=16.0}"
: "${MAX_3D_PER_EVT:=200000}"
: "${MAX_3D_PER_TRK:=20000}"

: "${GF_POS_SCALE:=0.1}"
: "${GF_LEN2M:=0.01}"
: "${GF_HIT_SIGMA_XY:=1.5}"
: "${GF_HIT_SIGMA_Z:=7.0}"
: "${GF_SEED_POS_SIGMA:=800}"
: "${GF_SEED_MOM_SIGMA:=40.0}"
: "${GF_DEDUP_TOL:=0.80}"
: "${GF_SEED_PT_MIN:=0.1}"
: "${GF_SEED_PT_MAX:=300.0}"
: "${GF_SEED_P_MIN:=0.3}"

: "${GF_MIN_GROUP:=2}"
: "${GF_USE_FALLBACK:=1}"
: "${GF_FALLBACK_EPS_CM:=6}"
: "${GF_FALLBACK_MINPTS:=3}"
: "${GF_RETRY:=1}"
: "${GF_RETRY_MEAS_INFL:=12.0}"
: "${GF_RETRY_SEED_POS:=7.0}"
: "${GF_RETRY_SEED_MOM:=7.0}"
: "${GF_MAX_MEAS_PER_GROUP:=0}"

: "${GF_BZ:=2.0}"
: "${GF_PDG:=13}"

# Auto FIT_OUT
if [[ "$FIT_OUT" == "auto" ]]; then
  case "$FITTER" in
    genfit2)    FIT_OUT="GenFitTracks" ;;
    simple)     FIT_OUT="SimpleFitTracks" ;;
    threepoint) FIT_OUT="ThreePointTracks" ;;
    *)          FIT_OUT="Tracks" ;;
  esac
fi

# Material flag
MAT_FLAG=()
if [[ "$FITTER" == "genfit2" ]]; then
  if [[ "$GF_USE_MAT" == "1" ]]; then MAT_FLAG+=( --gf-useMat ); else MAT_FLAG+=( --no-gf-useMat ); fi
fi

# Tame thread use
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 TORCH_NUM_THREADS=1
export MALLOC_ARENA_MAX=2 ORT_DISABLE_MEMORY_ARENA=1 ORT_ENABLE_MEM_PATTERN=0

# ---------------- Build k4run command ----------------
K4_ARGS=(
  "$RTPFX/runDCHTestTrackFinder.py"
  --inputFile  "$INFILE_XRD"
  --outputFile "$OUT_LOCAL"
  --modelPath  "$MODEL"
  --compactXML "$COMPACT_XML"
  --dchName    DCH_v2
  --dchSimHits DCHCollection
  --ggtfLog    "$GGTF_LOG"
  --tbeta      "$TBETA"
  --td         "$TD"
  --fitter     "$FITTER"
  --fitOut     "$FIT_OUT"
  --stage      "$STAGE"
  --onnxChunk  "$ONNX_CHUNK"
  --wireGateMM "$WIRE_GATE_MM"
  --max3DHitsPerEvent "$MAX_3D_PER_EVT"
  --max3DPerTrack     "$MAX_3D_PER_TRK"
  --fitterLog  DEBUG
)
[[ "$PRODUCE_3DHITS" == "1" ]] && K4_ARGS+=( --produce3DHits )
[[ "$MAX_HITS" -gt 0 ]]        && K4_ARGS+=( --maxHitsPerEvent "$MAX_HITS" )

# GenFit2 extras
K4_ARGS+=(
  --gf-posScale     "$GF_POS_SCALE"
  --gf-len2m        "$GF_LEN2M"
  --gf-hitSigmaXY   "$GF_HIT_SIGMA_XY"
  --gf-hitSigmaZ    "$GF_HIT_SIGMA_Z"
  --gf-seedPosSigma "$GF_SEED_POS_SIGMA"
  --gf-seedMomSigma "$GF_SEED_MOM_SIGMA"
  --gf-dedupTol     "$GF_DEDUP_TOL"
  --gf-seedPTMin    "$GF_SEED_PT_MIN"
  --gf-seedPTMax    "$GF_SEED_PT_MAX"
  --gf-seedPMin     "$GF_SEED_P_MIN"
  --gf-bz           "$GF_BZ"
  --gf-pdg          "$GF_PDG"
  --gf-minGroup     "$GF_MIN_GROUP"
  --gf-fallbackEpsCM "$GF_FALLBACK_EPS_CM"
  --gf-fallbackMinPts "$GF_FALLBACK_MINPTS"
  --gf-retryMeasInfl "$GF_RETRY_MEAS_INFL"
  --gf-retrySeedPos  "$GF_RETRY_SEED_POS"
  --gf-retrySeedMom  "$GF_RETRY_SEED_MOM"
  --gf-maxMeasPerGroup "$GF_MAX_MEAS_PER_GROUP"
)
[[ "$GF_USE_FALLBACK" == "1" ]] && K4_ARGS+=( --gf-useFallback ) || K4_ARGS+=( --no-gf-useFallback )
[[ "$GF_RETRY" == "1" ]]        && K4_ARGS+=( --gf-retry )        || K4_ARGS+=( --no-gf-retry )

# Late override flags
if [[ -n "${EXTRA_ARGS}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARR=( $EXTRA_ARGS )
  K4_ARGS+=( "${EXTRA_ARR[@]}" )
fi

# ---------------- Run ----------------
LOG="job.log"
echo "[k4run] args: ${K4_ARGS[*]}" | tee "$LOG"
( /usr/bin/time -v stdbuf -oL -eL k4run "${K4_ARGS[@]}" ) 2>&1 | tee -a "$LOG"

# ---------------- Verify output & stage to EOS ----------------
python3 - <<PY "$OUT_LOCAL" "$FIT_OUT"
import sys, ROOT
out = sys.argv[1]; coll = sys.argv[2]
f = ROOT.TFile.Open(out)
if not f or f.IsZombie():
    print(f"[verify] FATAL: cannot open output: {out}"); sys.exit(2)
t = f.Get("events")
if not t:
    print("[verify] FATAL: no 'events' tree"); sys.exit(3)
names = [b.GetName() for b in t.GetListOfBranches()]
present = any(coll in n for n in names)
print("[verify] first branches:", ",".join(names[:12]), "..." if len(names)>12 else "")
print(f"[verify] looking for '{coll}' -> present={present}")
f.Close()
sys.exit(0 if present else 4)
PY

# If OUTDIR is on EOS, copy via XRootD; else move locally.
if [[ "$OUT_EOS" == /eos/* ]]; then
  echo "[stage] xrdcp -> $OUT_EOS"
  dest_url="root://eosuser.cern.ch//${OUT_EOS#/}"
  xrdcp -f "$OUT_LOCAL" "$dest_url"
  echo "[ok] wrote $dest_url"
else
  mkdir -p "$(dirname "$OUT_EOS")"
  mv -f "$OUT_LOCAL" "$OUT_EOS"
  echo "[ok] wrote $OUT_EOS"
fi
