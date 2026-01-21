#!/usr/bin/env bash
# reco_job.sh — HTCondor wrapper for ONE input file/job.
# Goal: pass EXACTLY the same knobs and defaults as local_chain.sh (Jan 18 2026)
# while still being Condor/EOS-safe (xrootd staging, idempotent output, pinned Key4hep nightly via arg).
#
# Wrapper args (from reco.condor):
#   1 infile  2 outdir  3 compact  4 fitter  5 usemat  6 stage  7 fitout  8 extraargs  9 k4rel
#
set -euo pipefail

# ---------------- Key4HEP env ----------------
if [[ ! -r /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh ]]; then
  echo "[env][FATAL] /cvmfs/sw-nightlies.hsf.org not readable inside this job."
  exit 12
fi
K4SETUP="$(/bin/readlink -f /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh || echo /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh)"

# ---------------- Arguments ----------------
INFILE="${1:?need INFILE}"            # /eos/... or root://...
OUTDIR="${2:?need OUTDIR}"            # /eos/...
COMPACT_XML="${3:?need COMPACT_XML}"  # /eos/... or root://... or /cvmfs...
FITTER="${4:-genfit2}"                # genfit2|none
GF_USE_MAT_ARG="${5:-1}"              # 0/1 (match local_chain default: 0)
STAGE="${6:-fit}"                     # digi|ggtf|fit
FIT_OUT="${7:-auto}"                  # auto|<name>
K4REL="${8:-2026-01-11}"              # key4hep nightly tag


TGEO_FILE="${9:-/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03CF.root}"   # /eos/... or root://... or local
LOCAL_TGEO=""

if [[ -n "$TGEO_FILE" ]]; then
  if [[ "$TGEO_FILE" == root://* ]]; then
    LOCAL_TGEO="$PWD/$(basename "$TGEO_FILE")"
    xrdcp -f "$TGEO_FILE" "$LOCAL_TGEO"
  elif [[ "$TGEO_FILE" == /eos/* ]]; then
    LOCAL_TGEO="$PWD/$(basename "$TGEO_FILE")"
    xrdcp -f "root://eosuser.cern.ch//${TGEO_FILE#/}" "$LOCAL_TGEO"
  else
    LOCAL_TGEO="$TGEO_FILE"
  fi
  [[ -s "$LOCAL_TGEO" ]] || { echo "[env][FATAL] TGeo file missing: $LOCAL_TGEO"; exit 32; }
  echo "[env] Using TGeo: $LOCAL_TGEO"
fi



echo "[args] INFILE=$INFILE"
echo "[args] OUTDIR=$OUTDIR"
echo "[args] COMPACT_XML=$COMPACT_XML"
echo "[args] FITTER=$FITTER GF_USE_MAT_ARG=$GF_USE_MAT_ARG STAGE=$STAGE FIT_OUT=$FIT_OUT"
echo "[args] K4REL=$K4REL"

# ---------------- Source pinned nightly inside job (idempotent) ----------------
echo "[env] K4SETUP=$K4SETUP"

if command -v k4run >/dev/null 2>&1; then
  echo "[env] k4run already in PATH; not re-sourcing Key4hep."
  echo "[env] k4run=$(command -v k4run)"
else
  echo "[env] Sourcing Key4hep nightly $K4REL ..."
  __orig_args=("$@")
  set +u; set -- ; source "$K4SETUP" -r "$K4REL"; set -- "${__orig_args[@]}"; set -u 2>/dev/null || true
  command -v k4run >/dev/null || { echo "[env][FATAL] k4run not in PATH after setup"; exit 10; }
  echo "[env] k4run=$(command -v k4run)"
fi

echo "[env] ROOT version: $(root-config --version 2>/dev/null || true)"


# ---------------- Helpers ----------------
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

# root://eosuser.cern.ch///eos/user/...  -> /eos/user/...
to_eos_posix() {
  local p="$1"
  if [[ "$p" == root://eosuser.cern.ch//* ]]; then
    echo "/${p#root://eosuser.cern.ch//}"
  else
    echo "$p"
  fi
}

eos_path_from_xrd() { echo "$1" | sed -E 's#^root://eosuser\.cern\.ch##'; }

# Extract eta directory name as "eta_+X.XX" from path or filename.
extract_eta_dir() {
  local eos_path="$1"
  local eta=""
  # Prefer explicit directory segment "eta_+0.00"
  eta="$(echo "$eos_path" | grep -oE 'eta_[+-][0-9]+(\.[0-9]+)?' | head -n1 || true)"
  if [[ -n "$eta" ]]; then
    echo "$eta"
    return 0
  fi
  # Fallback: filename token like "gun_eta+2.50_pt..."
  local tok
  tok="$(basename "$eos_path" | grep -oE 'eta[+-][0-9]+(\.[0-9]+)?' | head -n1 || true)"
  if [[ -n "$tok" ]]; then
    echo "eta_${tok#eta}"
    return 0
  fi
  echo "eta_unknown"
}

# ---------------- Runtime bundle ----------------
[[ -s runtime.tgz ]] || { echo "FATAL: runtime.tgz missing"; exit 4; }
tar -xzf runtime.tgz
RTPFX="$PWD/runtime"

# Env for bundled libs/plugins/python
export LD_LIBRARY_PATH="$RTPFX/lib64:$RTPFX/lib:${LD_LIBRARY_PATH:-}"
export GAUDI_PLUGIN_PATH="$RTPFX/lib64:$RTPFX/lib:${GAUDI_PLUGIN_PATH:-}"
export PYTHONPATH="$RTPFX/python:${PYTHONPATH:-}"

# Build GAUDI_COMPONENT_PATH from catalogs (incl. confdb if present)
COMP_BASE="$RTPFX/share"
COMP_DIRS=("$COMP_BASE" "$RTPFX/share/k4rt-lib-catalogs")
if [[ -d "$COMP_BASE" ]]; then
  while IFS= read -r -d '' f; do
    d="$(dirname "$f")"
    [[ " ${COMP_DIRS[*]-} " == *" $d "* ]] || COMP_DIRS+=("$d")
  done < <(find "$COMP_BASE" -type f \( -name '*.components*' -o -name 'components*.*' -o -name '*.confdb' \) -print0 2>/dev/null || true)
fi
export GAUDI_COMPONENT_PATH="$(IFS=:; echo "${COMP_DIRS[*]}"):${GAUDI_COMPONENT_PATH:-}"
export GAUDI_COMPONENTS_PATH="$GAUDI_COMPONENT_PATH"
export GAUDI_CONFIGURABLE_DB_PATH="$GAUDI_COMPONENT_PATH"
export GAUDI_USE_CONFIGURATION_DB=1

echo "[env] GAUDI_PLUGIN_PATH=$GAUDI_PLUGIN_PATH"
echo "[env] GAUDI_COMPONENT_PATH=$GAUDI_COMPONENT_PATH"

# ---------------- Stage compact geometry (XML + all includes) ----------------
# The compact XML typically includes other XMLs via relative paths (elements/materials/etc),
# so we must stage the whole directory, not just the single compact.xml.
LOCAL_GEOM_BASE="$PWD/geom"
mkdir -p "$LOCAL_GEOM_BASE"

# Resolve COMPACT_XML to a local file
LOCAL_COMPACT_XML="$COMPACT_XML"

if [[ "$COMPACT_XML" == root://* ]]; then
  # Strip the eosuser prefix and recover a /eos/... POSIX path to find the directory name
  EOS_COMPACT_PATH="$(echo "$COMPACT_XML" | sed -E 's#^root://eosuser\.cern\.ch/+##')"
  EOS_COMPACT_PATH="/${EOS_COMPACT_PATH#"/"}"   # ensure leading /
  EOS_COMPACT_DIR="$(dirname "$EOS_COMPACT_PATH")"
  COMPACT_DIR_BASENAME="$(basename "$EOS_COMPACT_DIR")"

  echo "[stage] geometry dir xrdcp -r -> $LOCAL_GEOM_BASE/"
  xrdcp -r -f "root://eosuser.cern.ch//${EOS_COMPACT_DIR#/}" "$LOCAL_GEOM_BASE/"

  LOCAL_COMPACT_XML="$LOCAL_GEOM_BASE/$COMPACT_DIR_BASENAME/$(basename "$EOS_COMPACT_PATH")"

elif [[ "$COMPACT_XML" == /eos/* ]]; then
  EOS_COMPACT_DIR="$(dirname "$COMPACT_XML")"
  COMPACT_DIR_BASENAME="$(basename "$EOS_COMPACT_DIR")"

  echo "[stage] geometry dir xrdcp -r -> $LOCAL_GEOM_BASE/"
  xrdcp -r -f "root://eosuser.cern.ch//${EOS_COMPACT_DIR#/}" "$LOCAL_GEOM_BASE/"

  LOCAL_COMPACT_XML="$LOCAL_GEOM_BASE/$COMPACT_DIR_BASENAME/$(basename "$COMPACT_XML")"
else
  # Already local (e.g. shipped in tarball)
  LOCAL_COMPACT_XML="$COMPACT_XML"
fi

[[ -s "$LOCAL_COMPACT_XML" ]] || { echo "[env][FATAL] staged compact not found: $LOCAL_COMPACT_XML"; exit 31; }

# Make sure DD4hep can resolve relative include files
export DD4hep_XMLPATH="$(dirname "$LOCAL_COMPACT_XML"):${DD4hep_XMLPATH:-}"

echo "[env] Using compact: $LOCAL_COMPACT_XML"
echo "[env] DD4hep_XMLPATH=$DD4hep_XMLPATH"
# ---------------------------------------------------------------------------

# ---------------- Model resolution (same as before) ----------------
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

# ---------------- I/O naming + idempotence ----------------
INFILE_XRD="$(to_xrd "$INFILE")"

# Normalize to EOS-style path so we can reliably extract eta
INFILE_EOS="$(to_eos_posix "$INFILE")"
ETA_DIR="$(extract_eta_dir "$INFILE_EOS")"

base="$(basename "$INFILE_EOS")"
OUT_LOCAL="$PWD/reco_${base}"

# *** KEY CHANGE: always write under OUTDIR/<eta_dir>/reco_<inputfile> ***
OUT_EOS_POSIX="${OUTDIR%/}/${ETA_DIR}/reco_${base}"
OUT_EOS_XRD="$(to_xrd "$OUT_EOS_POSIX")"
OUT_EOS_PATH_ON_EOS="$(eos_path_from_xrd "$OUT_EOS_XRD")"

echo "[io] input:   $INFILE_XRD"
echo "[io] eta_dir: $ETA_DIR"
echo "[io] output:  $OUT_EOS_XRD"
echo "[io] local:   $OUT_LOCAL"



# ---------------- Full log policy (keep only on failure) ----------------
# Full logs go to scratch (TMPDIR) and are copied to EOS only if something looks bad.
TMPDIR="${_CONDOR_SCRATCH_DIR:-${TMPDIR:-$PWD}}"

FULLLOG="${TMPDIR}/reco_${ETA_DIR}_${base}.full.log"

# Where to store logs on EOS (alongside outputs, but in a logs/ subdir)
LOG_EOS_POSIX="${OUTDIR%/}/${ETA_DIR}/logs/reco_${base}.log"
LOG_EOS_XRD="$(to_xrd "$LOG_EOS_POSIX")"
LOG_EOS_PATH_ON_EOS="$(eos_path_from_xrd "$LOG_EOS_XRD")"

# Ensure EOS logs dir exists
if command -v xrdfs >/dev/null 2>&1; then
  xrdfs eosuser.cern.ch mkdir -p "$(dirname "$LOG_EOS_PATH_ON_EOS")" >/dev/null 2>&1 || true
fi

echo "[log] full log (scratch): $FULLLOG"
echo "[log] eos log (on fail):  $LOG_EOS_XRD"






# Skip if output already exists (idempotent)
if command -v xrdfs >/dev/null 2>&1; then
  if xrdfs eosuser.cern.ch stat "$OUT_EOS_PATH_ON_EOS" >/dev/null 2>&1; then
    echo "[skip] Output already exists: $OUT_EOS_XRD"
    exit 0
  fi
fi

# Ensure EOS parent exists
if command -v xrdfs >/dev/null 2>&1; then
  xrdfs eosuser.cern.ch mkdir -p "$(dirname "$OUT_EOS_PATH_ON_EOS")" >/dev/null 2>&1 || true
fi

# ======================================================================
#  KNOBS: MATCH local_chain.sh DEFAULTS (unless overridden via env)
# ======================================================================

# Pipeline controls
: "${SKIP_DIGI:=0}"
: "${FIT_OUT:=$FIT_OUT}"             # allow condor arg to win unless overridden
: "${FITTER:=$FITTER}"               # condor arg is base default
: "${STAGE:=$STAGE}"

# Logging/runtime
: "${GGTF_LOG:=DEBUG}"
: "${FITTER_LOG:=DEBUG}"
: "${TIMEOUT_K4RUN:=0}"
: "${MAX_HITS:=0}"

# GGTF clustering thresholds
: "${TBETA:=0.6}"
: "${TD:=0.3}"

# ONNX slicing
: "${ONNX_CHUNK:=4096}"

# Wire hygiene / safety
: "${GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE:=1}"
: "${GGTF_MAX_ABS_D_MM:=30.0}"

# Label-0 handling
: "${GGTF_ZERO_MIN:=8}"
: "${GGTF_WIRE_FRAC:=0.60}"
: "${GGTF_PROMOTE_ZERO:=1}"
: "${GGTF_SKIP_ZERO_SMALL:=1}"
: "${GGTF_SKIP_ZERO_ALWAYS:=0}"

# Truth-PDG wire gating
: "${GGTF_TRUTH_GATE:=0}"
: "${GGTF_KEEP_PDG:=13}"
: "${GGTF_DROP_UNLINKED:=1}"
: "${GGTF_WIRE_SIMLINK_COLL:=DCHDigi2SimLinkCollection}"

# GGTF tracks out collection name
: "${GGTF_TRACKS_OUT:=CDCHTracks}"

# GenFit2 knobs (match local_chain.sh)
# NOTE: local_chain default GF_USE_MAT=0, but condor submit passed usemat. Respect condor arg unless env overrides.
: "${GF_USE_MAT:=$GF_USE_MAT_ARG}"
: "${GF_DISABLE_ELOSS:=1}"
: "${GF_DISABLE_ALL_MAT:=0}"
: "${GF_HARD_DISABLE_MAT_IF_NO_GEO:=1}"

: "${GF_BZ:=2.0}"
: "${GF_PDG:=13}"

: "${GF_REJECT_NEGATIVE_LABELS:=1}"
: "${GF_SORT_HITS:=1}"
: "${GF_DEDUP:=1}"
: "${GF_DEDUP_TOL:=0.010}"   # mm

: "${GF_MIN_HITS_PER_TRACK:=8}"
: "${GF_MIN_MEASUREMENTS_TO_FIT:=6}"
: "${GF_MIN_FITTED_POINTS_WITH_FI:=0}"
: "${GF_MAX_CHI2_NDF:=10.0}"

: "${GF_USE_KF_PREFIT:=1}"
: "${GF_KF_MAX_ITERS:=16}"
: "${GF_TRY_BOTH_MOM_DIRS:=1}"

: "${GF_USE_DAF:=1}"
: "${GF_DAF_MAX_ITERS:=12}"
: "${GF_FALLBACK_TO_KF_IF_DAF_FAILS:=1}"

# publish controls
: "${GF_USE_BIASED_STATE_FOR_PUBLISH:=1}"
: "${GF_PUBLISH_STATE_CENTRAL_FRAC:=0.30}"
: "${GF_PUBLISH_PT_MAX_GEV:=300.0}"

: "${GF_INVALID_PT_SENTINEL:=-1.0}"
: "${GF_OMEGA_VAR_GOOD:=1e-4}"
: "${GF_OMEGA_VAR_BAD:=1.0}"

# Units / wire model
: "${GF_POSITION_UNIT_SCALE:=0.1}"
: "${GF_WIRE_HALF_LENGTH_MM:=2250.0}"
: "${GF_MAX_DRIFT_MM:=7.0}"
: "${GF_MAX_DRIFT_MM_FOR_HIT:=8.0}"
: "${GF_MIN_DRIFT_ERR_MM:=0.10}"
: "${GF_MAX_DRIFT_ERR_MM:=1.0}"
: "${GF_WIRE_ANGLES_DEGREES:=0}"  # 0=radians

# Observability gating
: "${GF_SKIP_IF_OBS_TOO_LOW:=0}"
: "${GF_MIN_HITS_FOR_OBS:=10}"
: "${GF_OBS_SIGMA_EFF_MM:=0.025}"
: "${GF_OBS_MIN_PHISPAN_RAD:=0.006}"
: "${GF_OBS_MIN_CHORD_MM:=20.0}"
: "${GF_OBS_MIN_SAGITTA_MM:=0.015}"
: "${GF_OBS_SCORE_MIN:=1.0}"

# Seed discipline
: "${GF_SEED_ENDPOINT_K:=6}"
: "${GF_SEED_TANGENT_K:=10}"
: "${GF_SEED_POS_SIGMA_MM:=80.0}"
: "${GF_SEED_MOM_SIGMA_GEV:=10.0}"
: "${GF_USE_SAGITTA_SEED:=1}"
: "${GF_MIN_SAGITTA_FOR_SEED_MM:=0.20}"
: "${GF_SEED_PT_FALLBACK_GEV:=50.0}"
: "${GF_SEED_PT_MIN_GEV:=0.20}"
: "${GF_SEED_PT_MAX_GEV:=200.0}"
: "${GF_SEED_P_MIN_GEV:=0.05}"

# Pre-fit outlier veto
: "${GF_PREFIT_OUTLIER_VETO:=0}"
: "${GF_OUTLIER_MAX_DROP:=1}"
: "${GF_OUTLIER_CIRCLE_RESIDUAL_MM:=0.8}"
: "${GF_OUTLIER_CHORD_RESIDUAL_MM:=2.0}"
: "${GF_OUTLIER_MIN_KEEP:=10}"

# PD guards / stats / diagnostics
: "${GF_MIN_COV_EIGENVALUE:=0}"
: "${GF_STATS_TRUNC_CENTRAL_FRAC:=0.80}"
: "${GF_DIAG_EVERY_N_TRACKS:=1}"

# Digi settings (match local_chain.sh defaults)
: "${DCH_DIGI_VERSION:=v02}"
: "${DCH_DEADTIME_NS:=450.0}"
: "${DCH_XY_MM:=0.10}"
: "${DCH_Z_MM:=30.0}"
: "${DCH_GAS_TYPE:=0}"
: "${DCH_DRIFT_VEL_UM_NS:=-1.0}"
# Drift signal velocity along wire (mm/ns): (2/3)*c
: "${DCH_SIGNAL_VEL_MM_NS:=199.86163866666666}"

: "${DCH_READOUT_START_NS:=1.0}"
: "${DCH_READOUT_DUR_NS:=900.0}"

# Keep memory tame (same spirit as local_chain)
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TORCH_NUM_THREADS=1
export MALLOC_ARENA_MAX=2
export ORT_DISABLE_MEMORY_ARENA=1
export ORT_ENABLE_MEM_PATTERN=0

# ---------------- Choose FIT_OUT automatically when requested ----------------
if [[ "${FIT_OUT}" == "auto" ]]; then
  case "${FITTER}" in
    genfit2) FIT_OUT="GenFitTracks" ;;
    none|*)  FIT_OUT="Tracks" ;;
  esac
fi

# ---------------- Build python args EXACTLY like local_chain.sh ----------------
K4_ARGS=(
  "$RTPFX/runDCHTestTrackFinder.py"
  --inputFile  "$INFILE_XRD"
  --outputFile "$OUT_LOCAL"
  --modelPath  "$MODEL"
  --compactXML "$LOCAL_COMPACT_XML"
  --dchName    "DCH_v2"
  --dchSimHits "DCHCollection"
  --ggtfLog    "$GGTF_LOG"
  --tbeta      "$TBETA"
  --td         "$TD"
  --onnxChunk  "$ONNX_CHUNK"
  --fitter     "$FITTER"
  --fitterLog  "$FITTER_LOG"
  --fitOut     "$FIT_OUT"
  --stage      "$STAGE"
  --ggtfTracksOut "$GGTF_TRACKS_OUT"
  --dchDigiVersion   "$DCH_DIGI_VERSION"
  --dch-deadtime-ns  "$DCH_DEADTIME_NS"
  --xyResolution_mm  "$DCH_XY_MM"
  --zResolution_mm   "$DCH_Z_MM"
  --dch-gas-type     "$DCH_GAS_TYPE"
  --dch-drift-vel-um-ns   "$DCH_DRIFT_VEL_UM_NS"
  --dch-signal-vel-mm-ns  "$DCH_SIGNAL_VEL_MM_NS"
  --rw-start-ns      "$DCH_READOUT_START_NS"
  --rw-duration-ns   "$DCH_READOUT_DUR_NS"

  # ---- GenFit2DCHFitter core ----
  --gf-bz           "$GF_BZ"
  --gf-pdg          "$GF_PDG"

  --gf-minHitsPerTrack        "$GF_MIN_HITS_PER_TRACK"
  --gf-minMeasurementsToFit   "$GF_MIN_MEASUREMENTS_TO_FIT"
  --gf-minFittedPointsWithFI  "$GF_MIN_FITTED_POINTS_WITH_FI"

  --gf-dedupTolMM   "$GF_DEDUP_TOL"
  --gf-kfMaxIters   "$GF_KF_MAX_ITERS"
  --gf-dafMaxIters  "$GF_DAF_MAX_ITERS"

  --gf-publishStateCentralFrac "$GF_PUBLISH_STATE_CENTRAL_FRAC"
  --gf-publishPTMaxGeV         "$GF_PUBLISH_PT_MAX_GEV"
  --gf-maxChi2Ndf              "$GF_MAX_CHI2_NDF"

  --gf-invalidPTSentinel "$GF_INVALID_PT_SENTINEL"
  --gf-omegaVarGood      "$GF_OMEGA_VAR_GOOD"
  --gf-omegaVarBad       "$GF_OMEGA_VAR_BAD"

  --gf-positionUnitScale "$GF_POSITION_UNIT_SCALE"
  --gf-wireHalfLengthMM  "$GF_WIRE_HALF_LENGTH_MM"
  --gf-maxDriftMM         "$GF_MAX_DRIFT_MM"
  --gf-maxDriftMMForHit   "$GF_MAX_DRIFT_MM_FOR_HIT"
  --gf-minDriftErrMM      "$GF_MIN_DRIFT_ERR_MM"
  --gf-maxDriftErrMM      "$GF_MAX_DRIFT_ERR_MM"

  --gf-minHitsForObs     "$GF_MIN_HITS_FOR_OBS"
  --gf-obsSigmaEffMM     "$GF_OBS_SIGMA_EFF_MM"
  --gf-obsMinPhiSpanRad  "$GF_OBS_MIN_PHISPAN_RAD"
  --gf-obsMinChordMM     "$GF_OBS_MIN_CHORD_MM"
  --gf-obsMinSagittaMM   "$GF_OBS_MIN_SAGITTA_MM"
  --gf-obsMinScore       "$GF_OBS_SCORE_MIN"

  --gf-seedEndpointK      "$GF_SEED_ENDPOINT_K"
  --gf-seedTangentK       "$GF_SEED_TANGENT_K"
  --gf-seedPosSigmaMM     "$GF_SEED_POS_SIGMA_MM"
  --gf-seedMomSigmaGeV    "$GF_SEED_MOM_SIGMA_GEV"
  --gf-seedPTFallbackGeV  "$GF_SEED_PT_FALLBACK_GEV"
  --gf-seedPTMinGeV       "$GF_SEED_PT_MIN_GEV"
  --gf-seedPTMaxGeV       "$GF_SEED_PT_MAX_GEV"
  --gf-seedPMinGeV        "$GF_SEED_P_MIN_GEV"
  --gf-minSagittaForSeedMM "$GF_MIN_SAGITTA_FOR_SEED_MM"

  --gf-outlierMaxDrop          "$GF_OUTLIER_MAX_DROP"
  --gf-outlierCircleResidualMM "$GF_OUTLIER_CIRCLE_RESIDUAL_MM"
  --gf-outlierChordResidualMM  "$GF_OUTLIER_CHORD_RESIDUAL_MM"
  --gf-outlierMinKeep          "$GF_OUTLIER_MIN_KEEP"

  --gf-minCovEigenvalue        "$GF_MIN_COV_EIGENVALUE"
  --gf-statsTruncCentralFrac   "$GF_STATS_TRUNC_CENTRAL_FRAC"
  --gf-diagEveryNTracks        "$GF_DIAG_EVERY_N_TRACKS"
)

# --skipDigi
if [[ "$SKIP_DIGI" == "1" ]]; then
  K4_ARGS+=( --skipDigi )
fi

# Max hits cap only if >0
[[ "$MAX_HITS" -gt 0 ]] && K4_ARGS+=( --maxHitsPerEvent "$MAX_HITS" )

# Wire hygiene
if [[ "$GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE" == "1" ]]; then
  K4_ARGS+=( --ggtf-dropWireIfAbsDTooLarge )
else
  K4_ARGS+=( --no-ggtf-dropWireIfAbsDTooLarge )
fi
K4_ARGS+=( --ggtf-maxAbsDMM "$GGTF_MAX_ABS_D_MM" )

# Truth gating
if [[ "$GGTF_TRUTH_GATE" == "1" ]]; then
  K4_ARGS+=( --ggtf-filterInputWiresByTruthPdg )
else
  K4_ARGS+=( --no-ggtf-filterInputWiresByTruthPdg )
fi
K4_ARGS+=( --ggtf-keepTruthPdg "$GGTF_KEEP_PDG" )
if [[ "$GGTF_DROP_UNLINKED" == "1" ]]; then
  K4_ARGS+=( --ggtf-dropWireIfUnlinked )
else
  K4_ARGS+=( --no-ggtf-dropWireIfUnlinked )
fi
if [[ -n "${GGTF_WIRE_SIMLINK_COLL}" ]]; then
  K4_ARGS+=( --ggtf-wireSimLinkColl "$GGTF_WIRE_SIMLINK_COLL" )
fi

# Label-0 handling
K4_ARGS+=( --ggtf-zeroMinSizeKeep "$GGTF_ZERO_MIN" )
K4_ARGS+=( --ggtf-minWireFracKeep "$GGTF_WIRE_FRAC" )
[[ "$GGTF_PROMOTE_ZERO" -eq 1 ]] && K4_ARGS+=( --ggtf-promoteZeroIfGood ) || K4_ARGS+=( --no-ggtf-promoteZeroIfGood )
[[ "$GGTF_SKIP_ZERO_SMALL" -eq 1 ]] && K4_ARGS+=( --ggtf-skipZeroIfSmall ) || K4_ARGS+=( --no-ggtf-skipZeroIfSmall )
[[ "$GGTF_SKIP_ZERO_ALWAYS" -eq 1 ]] && K4_ARGS+=( --ggtf-skipZeroAlways ) || K4_ARGS+=( --no-ggtf-skipZeroAlways )

# GenFit2 switches
if [[ "$GF_USE_MAT" == "1" ]]; then
  K4_ARGS+=( --gf-useMat )
else
  K4_ARGS+=( --no-gf-useMat )
fi
if [[ "$GF_DISABLE_ELOSS" == "1" ]]; then
  K4_ARGS+=( --gf-disableEloss )
else
  K4_ARGS+=( --no-gf-disableEloss )
fi
if [[ "$GF_DISABLE_ALL_MAT" == "1" ]]; then
  K4_ARGS+=( --gf-disableAllMat )
else
  K4_ARGS+=( --no-gf-disableAllMat )
fi
if [[ "$GF_HARD_DISABLE_MAT_IF_NO_GEO" == "1" ]]; then
  K4_ARGS+=( --gf-hardDisableMatIfNoGeo )
else
  K4_ARGS+=( --no-gf-hardDisableMatIfNoGeo )
fi
if [[ "$GF_REJECT_NEGATIVE_LABELS" == "1" ]]; then
  K4_ARGS+=( --gf-rejectNegativeLabels )
else
  K4_ARGS+=( --no-gf-rejectNegativeLabels )
fi
if [[ "$GF_SORT_HITS" == "1" ]]; then
  K4_ARGS+=( --gf-sortHits )
else
  K4_ARGS+=( --no-gf-sortHits )
fi
if [[ "$GF_DEDUP" == "1" ]]; then
  K4_ARGS+=( --gf-dedup )
else
  K4_ARGS+=( --no-gf-dedup )
fi
if [[ "$GF_USE_KF_PREFIT" == "1" ]]; then
  K4_ARGS+=( --gf-useKFPreFit )
else
  K4_ARGS+=( --no-gf-useKFPreFit )
fi
if [[ "$GF_TRY_BOTH_MOM_DIRS" == "1" ]]; then
  K4_ARGS+=( --gf-tryBothMomDirs )
else
  K4_ARGS+=( --no-gf-tryBothMomDirs )
fi
if [[ "$GF_USE_DAF" == "1" ]]; then
  K4_ARGS+=( --gf-useDAF )
else
  K4_ARGS+=( --no-gf-useDAF )
fi
if [[ "$GF_FALLBACK_TO_KF_IF_DAF_FAILS" == "1" ]]; then
  K4_ARGS+=( --gf-fallbackToKFIfDAFFails )
else
  K4_ARGS+=( --no-gf-fallbackToKFIfDAFFails )
fi



if [[ "$GF_USE_MAT" == "1" ]]; then
  [[ -n "$LOCAL_TGEO" ]] || { echo "[env][FATAL] GF_USE_MAT=1 but no TGeo file provided"; exit 33; }
  K4_ARGS+=( --tgeoFile "$LOCAL_TGEO" )
fi




# Observability skip toggle
if [[ "$GF_SKIP_IF_OBS_TOO_LOW" == "1" ]]; then
  K4_ARGS+=( --gf-skipIfObsTooLow )
else
  K4_ARGS+=( --no-gf-skipIfObsTooLow )
fi

# Sagitta seed toggle
if [[ "$GF_USE_SAGITTA_SEED" == "1" ]]; then
  K4_ARGS+=( --gf-useSagittaSeed )
else
  K4_ARGS+=( --no-gf-useSagittaSeed )
fi

# publish state choice
if [[ "$GF_USE_BIASED_STATE_FOR_PUBLISH" == "1" ]]; then
  K4_ARGS+=( --gf-useBiasedStateForPublish )
else
  K4_ARGS+=( --no-gf-useBiasedStateForPublish )
fi

# prefit outlier veto toggle
if [[ "$GF_PREFIT_OUTLIER_VETO" == "1" ]]; then
  K4_ARGS+=( --gf-prefitOutlierVeto )
else
  K4_ARGS+=( --no-gf-prefitOutlierVeto )
fi

# Angle units toggle (explicit)
if [[ "$GF_WIRE_ANGLES_DEGREES" == "1" ]]; then
  K4_ARGS+=( --gf-wireAnglesAreDegrees )
else
  K4_ARGS+=( --gf-wireAnglesAreRadians )
fi

# ---------------- Run (capture full output to scratch; keep only if bad) ----------------
echo "[k4run] args: ${K4_ARGS[*]}" > "$FULLLOG"

run_cmd() {
  if [[ "$TIMEOUT_K4RUN" -gt 0 ]]; then
    timeout --signal=TERM --kill-after=30 "$TIMEOUT_K4RUN" "$@"
  else
    "$@"
  fi
}

set +e
run_cmd /usr/bin/time -v stdbuf -oL -eL k4run "${K4_ARGS[@]}" >>"$FULLLOG" 2>&1
K4_RC=$?
set -e

# If k4run failed but output is usable, override rc to 0 (same philosophy as local_chain)
check_edm_root() {
  python3 - "$1" <<'PY'
import sys, ROOT
f = ROOT.TFile.Open(sys.argv[1])
ok = bool(f and not f.IsZombie())
nev = 0
if ok:
    t = f.Get("events")
    nev = int(t.GetEntries()) if t else 0
if f:
    f.Close()
print("[verify] %s OK=%s NEV=%d" % (sys.argv[1], ok, nev))
sys.exit(0 if ok and nev>0 else 1)
PY
}

if [[ $K4_RC -ne 0 ]]; then
  if check_edm_root "$OUT_LOCAL"; then
    echo "[note] k4run rc=$K4_RC but output looks fine; overriding to 0."
    echo "[note] k4run rc=$K4_RC but output looks fine; overriding to 0." >>"$FULLLOG"
    K4_RC=0
  fi
fi

# Decide whether to keep/copy the full log
NEED_LOG=0
if [[ $K4_RC -ne 0 ]]; then
  NEED_LOG=1
fi
if grep -Eqi '(FATAL|Segmentation|Traceback|Exception thrown|ill-conditioned covariance|not positive definite|ERROR)' "$FULLLOG"; then
  NEED_LOG=1
fi

if [[ $NEED_LOG -eq 1 ]]; then
  echo "[log] issues detected -> copying full log to EOS: $LOG_EOS_XRD"
  # show a short tail in the condor .out for quick triage
  echo "---- tail(full log) ----"
  tail -n 120 "$FULLLOG" || true
  xrdcp -f "$FULLLOG" "$LOG_EOS_XRD" || true
else
  # keep condor .out small; delete full log
  rm -f "$FULLLOG" || true
fi


# Verify required collection exists (match your older reco_job behavior)
set +e
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
VER_RC=$?
set -e

if [[ $VER_RC -ne 0 ]]; then
  echo "[verify] collection check failed rc=$VER_RC (coll=$FIT_OUT)."
  echo "[verify] collection check failed rc=$VER_RC (coll=$FIT_OUT)." >>"$FULLLOG"
  echo "[log] copying full log to EOS due to verify failure: $LOG_EOS_XRD"
  xrdcp -f "$FULLLOG" "$LOG_EOS_XRD" || true
  exit $VER_RC
fi


echo "[stage] xrdcp -> $OUT_EOS_XRD"
xrdcp -f "$OUT_LOCAL" "$OUT_EOS_XRD"
echo "[ok] wrote $OUT_EOS_XRD"

# Keep submit host clean: remove local output after successful stage
rm -f "$OUT_LOCAL" || true

exit $K4_RC
