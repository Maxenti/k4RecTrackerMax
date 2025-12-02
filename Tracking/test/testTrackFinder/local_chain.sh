#!/bin/bash
# local_chain.sh — run the k4run stage locally (digi → ggtf → fit)
set -euo pipefail

########## defaults  ##########
DEFAULT_INPUT="/eos/user/c/cglenn/gun_samples2/gun_eta+0.1+E300MeV.root"
DEFAULT_OUTPUT="/eos/user/c/cglenn/gun_samples2/reco_eta+0.1_E300MeV.root"
# Model unchanged; use local file directly
DEFAULT_MODEL_SPEC="/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/model.onnx"
DEFAULT_COMPACT_XML="/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml"
DEFAULT_DCH_SIMHITS="DCHCollection"
DEFAULT_DCH_NAME="DCH_v2"
###########################################

# CLI overrides (optional)
INPUT="${1:-$DEFAULT_INPUT}"
OUTPUT="${2:-$DEFAULT_OUTPUT}"
MODEL_SPEC="${3:-$DEFAULT_MODEL_SPEC}"
COMPACT_XML="${4:-$DEFAULT_COMPACT_XML}"
DCH_SIMHITS="${5:-$DEFAULT_DCH_SIMHITS}"
DCH_NAME="${6:-$DEFAULT_DCH_NAME}"

# ----------------- pipeline controls -----------------
: "${STAGE:=fit}"              # digi|ggtf|fit

# Fitter choice:
: "${FITTER:=genfit2}"      # genfit2|simple|threepoint|none

# Output collection name from fitter
: "${FIT_OUT:=auto}"

# ----------------- logging & runtime -----------------
: "${GGTF_LOG:=DEBUG}"           # INFO|DEBUG
: "${PRODUCE_3DHITS:=1}"         # 0|1
: "${MAX_HITS:=100000}"          # cap input hits/event (0=off)
: "${TIMEOUT_K4RUN:=0}"          # seconds (0=off)

# GGTF clustering thresholds
: "${TBETA:=0.6}"
: "${TD:=0.3}"

# GGTF runtime
: "${ONNX_CHUNK:=4096}"          # hits per ONNX slice
: "${WIRE_GATE_MM:=12.0}"       # wire→circle gate [mm]
: "${MAX_3D_PER_EVT:=200000}"    # cap spacepoints per event
: "${MAX_3D_PER_TRK:=20000}"     # cap spacepoints per track

# GenFit2 “stability profile” (used when FITTER=genfit2)
: "${GF_POS_SCALE:=0.1}"           # mm→cm internally
: "${GF_LEN2M:=0.01}"           # cm→m
: "${GF_HIT_SIGMA_XY:=0.8}"      # mm
: "${GF_HIT_SIGMA_Z:=6.0}"       # mm
: "${GF_SEED_POS_SIGMA:=100}"    # mm
: "${GF_SEED_MOM_SIGMA:=10.0}"   # GeV
: "${GF_DEDUP_TOL:=0.50}"        # mm
: "${GF_USE_MAT:=1}"             # 0/1
: "${GF_SEED_PT_MIN:=0.2}"
: "${GF_SEED_PT_MAX:=200.0}"
: "${GF_SEED_P_MIN:=1.2}"        # GeV

# Fitter grouping / fallback / retry (GenFit2)
: "${GF_MIN_GROUP:=6}"
: "${GF_USE_FALLBACK:=1}"
: "${GF_FALLBACK_EPS_CM:=4}"
: "${GF_FALLBACK_MINPTS:=4}"
: "${GF_RETRY:=1}"
: "${GF_RETRY_MEAS_INFL:=5.0}"
: "${GF_RETRY_SEED_POS:=5.0}"
: "${GF_RETRY_SEED_MOM:=5.0}"
: "${GF_MAX_MEAS_PER_GROUP:=0}"

# ThreePointFitter args (match new tp-* names in Python)
: "${FITTER_LOG:=DEBUG}"
: "${TP_MIN_DELTA_PHI:=0.10}"     # rad
: "${TP_MIN_CHORD_MM:=10}"         # mm
: "${TP_MIN_HITS:=6}"
: "${TP_MIN_RADIUS_MM:=50}"      # mm
: "${TP_FIT_TANLAMBDA:=true}"     # true|false
: "${TP_PRINT_DIAG:=false}"       # true|false
: "${TP_DIAG_EVERY_N:=100}"

# Field / PDG (used generally)
: "${GF_BZ:=2.0}"
: "${GF_PDG:=13}"

#New Digi_v02 settings
: "${DCH_DIGI_VERSION:=v02}"       # v01|v02
: "${DCH_DEADTIME_NS:=400.0}"
: "${DCH_XY_MM:=0.10}"
: "${DCH_Z_MM:=1.0}"
: "${DCH_GAS_TYPE:=0}"             # 0 HeIso(90/10)
: "${DCH_DRIFT_VEL_UM_NS:=-1.0}"   # <0 -> auto by gas
: "${DCH_SIGNAL_VEL_MM_NS:=$(python3 - <<'PY'
print((2.0/3.0)*299792458e-6)
PY
)}"
: "${DCH_READOUT_START_NS:=1.0}"
: "${DCH_READOUT_DUR_NS:=450.0}"

# ----------------- choose FIT_OUT automatically when requested -----------------
if [[ "${FIT_OUT}" == "auto" ]]; then
  case "${FITTER}" in
    genfit2)    FIT_OUT="GenFitTracks" ;;
    simple)     FIT_OUT="SimpleFitTracks" ;;
    threepoint) FIT_OUT="ThreePointTracks" ;;
    none|*)     FIT_OUT="Tracks" ;;
  esac
fi

echo "[cfg] INPUT=$INPUT"
echo "[cfg] OUTPUT=$OUTPUT"
echo "[cfg] MODEL_SPEC=$MODEL_SPEC"
echo "[cfg] COMPACT_XML=$COMPACT_XML  DCH_SIMHITS=$DCH_SIMHITS  DCH_NAME=$DCH_NAME"
echo "[cfg] STAGE=$STAGE FITTER=$FITTER FIT_OUT=$FIT_OUT"
echo "[cfg] GGTF_LOG=$GGTF_LOG PRODUCE_3DHITS=$PRODUCE_3DHITS MAX_HITS=$MAX_HITS TIMEOUT_K4RUN=$TIMEOUT_K4RUN"
echo "[cfg] TBETA=$TBETA TD=$TD ONNX_CHUNK=$ONNX_CHUNK WIRE_GATE_MM=$WIRE_GATE_MM MAX_3D_PER_EVT=$MAX_3D_PER_EVT MAX_3D_PER_TRK=$MAX_3D_PER_TRK"
echo "[cfg] GF_POS_SCALE=$GF_POS_SCALE GF_LEN2M=$GF_LEN2M GF_HIT_SIGMA_XY=$GF_HIT_SIGMA_XY GF_HIT_SIGMA_Z=$GF_HIT_SIGMA_Z"
echo "[cfg] GF_SEED_POS_SIGMA=$GF_SEED_POS_SIGMA GF_SEED_MOM_SIGMA=$GF_SEED_MOM_SIGMA GF_DEDUP_TOL=$GF_DEDUP_TOL GF_USE_MAT=$GF_USE_MAT"
echo "[cfg] GF_SEED_PT_MIN=$GF_SEED_PT_MIN GF_SEED_PT_MAX=$GF_SEED_PT_MAX GF_SEED_P_MIN=$GF_SEED_P_MIN"
echo "[cfg] GF_MIN_GROUP=$GF_MIN_GROUP GF_USE_FALLBACK=$GF_USE_FALLBACK GF_FALLBACK_EPS_CM=$GF_FALLBACK_EPS_CM GF_FALLBACK_MINPTS=$GF_FALLBACK_MINPTS"
echo "[cfg] GF_RETRY=$GF_RETRY GF_RETRY_MEAS_INFL=$GF_RETRY_MEAS_INFL GF_RETRY_SEED_POS=$GF_RETRY_SEED_POS GF_RETRY_SEED_MOM=$GF_RETRY_SEED_MOM GF_MAX_MEAS_PER_GROUP=$GF_MAX_MEAS_PER_GROUP"
echo "[cfg] GF_BZ=$GF_BZ GF_PDG=$GF_PDG"
echo "[cfg] TP_MIN_DELTA_PHI=$TP_MIN_DELTA_PHI TP_MIN_CHORD_MM=$TP_MIN_CHORD_MM TP_MIN_HITS=$TP_MIN_HITS TP_MIN_RADIUS_MM=$TP_MIN_RADIUS_MM"
echo "[cfg] TP_FIT_TANLAMBDA=$TP_FIT_TANLAMBDA TP_PRINT_DIAG=$TP_PRINT_DIAG TP_DIAG_EVERY_N=$TP_DIAG_EVERY_N"

# --- keep memory tame ---
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TORCH_NUM_THREADS=1
export MALLOC_ARENA_MAX=2
export ORT_DISABLE_MEMORY_ARENA=1
export ORT_ENABLE_MEM_PATTERN=0

export GAUDI_PLUGIN_PATH="${GAUDI_PLUGIN_PATH:-.}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-.}"

# logs
: > k4run.log
: > progress.log

# Build k4run args (Python script will stage the model)
K4_ARGS=(
  ./runDCHTestTrackFinder.py
  --inputFile  "$INPUT"
  --outputFile "$OUTPUT"
  --modelPath  "$MODEL_SPEC"
  --compactXML "${COMPACT_XML}"
  --dchName    "${DCH_NAME}"
  --dchSimHits "${DCH_SIMHITS}"
  --ggtfLog    "${GGTF_LOG}"
  --tbeta      "${TBETA}"
  --td         "${TD}"
  --fitter     "${FITTER}"
  --fitterLog  "${FITTER_LOG}"
  --fitOut     "${FIT_OUT}"
  --stage      "${STAGE}"
  --onnxChunk  "${ONNX_CHUNK}"
  --wireGateMM "${WIRE_GATE_MM}"
  --max3DHitsPerEvent "${MAX_3D_PER_EVT}"
  --max3DPerTrack     "${MAX_3D_PER_TRK}"
)

# Optional toggles converted to presence/absence
[[ "${PRODUCE_3DHITS}" == "1" ]] && K4_ARGS+=( --produce3DHits )
[[ "${MAX_HITS}" -gt 0 ]]        && K4_ARGS+=( --maxHitsPerEvent "${MAX_HITS}" )

# --- GenFit2 options (harmless for other fitters; Python only sets what exists) ---
K4_ARGS+=(
  --gf-posScale     "${GF_POS_SCALE}"
  --gf-len2m        "${GF_LEN2M}"
  --gf-hitSigmaXY   "${GF_HIT_SIGMA_XY}"
  --gf-hitSigmaZ    "${GF_HIT_SIGMA_Z}"
  --gf-seedPosSigma "${GF_SEED_POS_SIGMA}"
  --gf-seedMomSigma "${GF_SEED_MOM_SIGMA}"
  --gf-dedupTol     "${GF_DEDUP_TOL}"
  --gf-seedPTMin    "${GF_SEED_PT_MIN}"
  --gf-seedPTMax    "${GF_SEED_PT_MAX}"
  --gf-seedPMin     "${GF_SEED_P_MIN}"
  --gf-bz           "${GF_BZ}"
  --gf-pdg          "${GF_PDG}"
  --dchDigiVersion "${DCH_DIGI_VERSION}"
  --dch-deadtime-ns "${DCH_DEADTIME_NS}"
  --dch-xy-mm       "${DCH_XY_MM}"
  --dch-z-mm        "${DCH_Z_MM}"
  --dch-gas-type    "${DCH_GAS_TYPE}"
  --dch-drift-vel-um-ns "${DCH_DRIFT_VEL_UM_NS}"
  --dch-signal-vel-mm-ns "${DCH_SIGNAL_VEL_MM_NS}"
  --dch-readout-start-ns "${DCH_READOUT_START_NS}"
  --dch-readout-dur-ns   "${DCH_READOUT_DUR_NS}"
)

if [[ "${GF_USE_MAT}" == "1" ]]; then
  K4_ARGS+=( --gf-useMat )
else
  K4_ARGS+=( --no-gf-useMat )
fi

K4_ARGS+=( --gf-minGroup "${GF_MIN_GROUP}" --gf-fallbackEpsCM "${GF_FALLBACK_EPS_CM}" --gf-fallbackMinPts "${GF_FALLBACK_MINPTS}" )
if [[ "${GF_USE_FALLBACK}" == "1" ]]; then
  K4_ARGS+=( --gf-useFallback )
else
  K4_ARGS+=( --no-gf-useFallback )
fi

K4_ARGS+=( --gf-retryMeasInfl "${GF_RETRY_MEAS_INFL}" --gf-retrySeedPos "${GF_RETRY_SEED_POS}" --gf-retrySeedMom "${GF_RETRY_SEED_MOM}" --gf-maxMeasPerGroup "${GF_MAX_MEAS_PER_GROUP}" )
if [[ "${GF_RETRY}" == "1" ]]; then
  K4_ARGS+=( --gf-retry )
else
  K4_ARGS+=( --no-gf-retry )
fi

# --- ThreePointFitter-specific args (NEW) ---
K4_ARGS+=( --tp-minDeltaPhi "${TP_MIN_DELTA_PHI}" )
K4_ARGS+=( --tp-minChordMM  "${TP_MIN_CHORD_MM}" )
K4_ARGS+=( --tp-minGroup    "${TP_MIN_HITS}" )
K4_ARGS+=( --tp-minRadiusMM "${TP_MIN_RADIUS_MM}" )
# booleans for tp-fitTanLambda / tp-printDiag
if [[ "${TP_FIT_TANLAMBDA}" == "true" ]]; then
  K4_ARGS+=( --tp-fitTanLambda )
else
  K4_ARGS+=( --no-tp-fitTanLambda )
fi
if [[ "${TP_PRINT_DIAG}" == "true" ]]; then
  K4_ARGS+=( --tp-printDiag --tp-diagEveryN "${TP_DIAG_EVERY_N}" )
else
  K4_ARGS+=( --no-tp-printDiag )
fi

echo "[k4run] args: ${K4_ARGS[*]}" | tee -a k4run.log

run_cmd() {
  if [[ "${TIMEOUT_K4RUN}" -gt 0 ]]; then
    timeout --signal=TERM --kill-after=30 "${TIMEOUT_K4RUN}" "$@"
  else
    "$@"
  fi
}

( run_cmd /usr/bin/time -v stdbuf -oL -eL k4run "${K4_ARGS[@]}" ) 2>&1 \
  | tee -a k4run.log \
  | awk '/GGTF_tracking|RSS=|Peak=|TOTAL|flatten:|onnx:|clustering|unique|bucket|build|Application Manager|tracks=|MemoryAuditor/{print; fflush()}' > progress.log

K4_RC=${PIPESTATUS[0]}

check_edm_root() {
  python3 - "$1" <<'PY'
import sys, ROOT
f = ROOT.TFile.Open(sys.argv[1])
ok = bool(f and not f.IsZombie())
nev = 0
if ok:
    t = f.Get("events")
    nev = int(t.GetEntries()) if t else 0
f.Close() if f else None
print(f"[verify] %s OK=%s NEV=%d" % (sys.argv[1], ok, nev))
sys.exit(0 if ok and nev>0 else 1)
PY
}

if [[ $K4_RC -ne 0 ]]; then
  if check_edm_root "${OUTPUT:-reco_local.root}"; then
    echo "[note] k4run rc=$K4_RC but output looks fine; overriding to 0."
    K4_RC=0
  fi
fi

echo "Run complete"
exit $K4_RC
