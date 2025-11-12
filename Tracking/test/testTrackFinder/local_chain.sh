#!/bin/bash
# local_chain.sh — run the k4run stage locally (digi → ggtf → fit)
set -euo pipefail

########## defaults  ##########
DEFAULT_INPUT="/eos/user/c/cglenn/gun_samples/eta_+1.00/gun_eta+1.00_pt22.143.root"
DEFAULT_OUTPUT="/eos/user/c/cglenn/reco_samples/eta_+1.00/reco_eta+1.00_pt22.143.root"
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
# Stage: which blocks to run in runDCHTestTrackFinder.py
#   digi  -> digitizer only
#   ggtf  -> digitizer + GGTF
#   fit   -> digitizer + GGTF + fitter
: "${STAGE:=fit}"              # digi|ggtf|fit

# Fitter choice:
#   none       -> no fitter
#   genfit2    -> GenFit2DCHFitter (consumes GGTF_3DHits)
#   simple     -> SimpleFitDCHFitter (straight-ish minimal fit)
#   threepoint -> ThreePointFitter (3-point fast fit)
: "${FITTER:=genfit2}"

# Output collection name from fitter
# You can set FIT_OUT explicitly; if "auto", it will adapt to the fitter.
: "${FIT_OUT:=auto}"

# ----------------- logging & runtime -----------------
: "${GGTF_LOG:=INFO}"          # INFO|DEBUG
: "${PRODUCE_3DHITS:=1}"       # 0|1
: "${MAX_HITS:=10000}"          # hard-cap per event to avoid OOM on huge spikes
: "${TIMEOUT_K4RUN:=0}"

# GGTF clustering thresholds
: "${TBETA:=0.15}"             # default 0.05; slightly tighter by default
: "${TD:=0.3}"                # default 0.05

# GGTF runtime
: "${ONNX_CHUNK:=4096}"        # hits per ONNX slice
: "${WIRE_GATE_MM:=12.0}"      # gate for wire->circle projection
: "${MAX_3D_PER_EVT:=200000}"  # cap spacepoints per event
: "${MAX_3D_PER_TRK:=20000}"   # cap spacepoints per track

# GenFit “stability profile” (only used when Fitter=genfit2)
: "${GF_POS_SCALE:=0.1}"       # mm -> cm internally
: "${GF_LEN2M:=0.01}"          # cm -> m for pT seeding
: "${GF_HIT_SIGMA_XY:=1.2}"    # mm
: "${GF_HIT_SIGMA_Z:=6.0}"     # mm
: "${GF_SEED_POS_SIGMA:=500}"  # mm
: "${GF_SEED_MOM_SIGMA:=30.0}" # GeV
: "${GF_DEDUP_TOL:=0.50}"      # mm
: "${GF_USE_MAT:=1}"           # 0/1 (material effects)
: "${GF_SEED_PT_MIN:=0.2}"
: "${GF_SEED_PT_MAX:=200.0}"
: "${GF_SEED_P_MIN:=0.5}"      # lower bound on |p| seed [GeV]

# Fitter grouping / fallback / retry (GenFit2)
: "${GF_MIN_GROUP:=3}"
: "${GF_USE_FALLBACK:=1}"      # 1=on, 0=off
: "${GF_FALLBACK_EPS_CM:=4}"
: "${GF_FALLBACK_MINPTS:=4}"
: "${GF_RETRY:=1}"             # 1=on, 0=off
: "${GF_RETRY_MEAS_INFL:=9.0}" # variance k (C' = k*C)
: "${GF_RETRY_SEED_POS:=5.0}"  # seed pos sigma ×
: "${GF_RETRY_SEED_MOM:=5.0}"  # seed mom sigma ×
: "${GF_MAX_MEAS_PER_GROUP:=0}"

# Field / PDG (GenFit2 uses these; harmless otherwise)
: "${GF_BZ:=2.0}"
: "${GF_PDG:=13}"

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
  --fitOut     "${FIT_OUT}"
  --stage      "${STAGE}"
  --onnxChunk  "${ONNX_CHUNK}"
  --wireGateMM "${WIRE_GATE_MM}"
  --max3DHitsPerEvent "${MAX_3D_PER_EVT}"
  --max3DPerTrack     "${MAX_3D_PER_TRK}"
)

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
