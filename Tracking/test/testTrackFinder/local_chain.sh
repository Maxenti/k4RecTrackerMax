#!/bin/bash
# local_chain.sh — run the k4run stage locally (digi → ggtf → fit) + stamp provenance metadata
set -euo pipefail

########## defaults  ##########
DEFAULT_INPUT="/eos/user/c/cglenn/gun_samples/1_14_2026/eta_+1.00/gun_eta+1.00_E28.56.root"
DEFAULT_OUTPUT="/eos/user/c/cglenn/reco_samples2/1_15_2026/eta_+1.00/reco_eta+1.00_E28.56_13_22.root"
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
: "${FITTER:=genfit2}"         # genfit2|simple|threepoint|none
: "${FIT_OUT:=auto}"

# ----------------- logging & runtime -----------------
: "${GGTF_LOG:=DEBUG}"         # INFO|DEBUG
: "${PRODUCE_3DHITS:=1}"       # 0|1

# IMPORTANT: default off so you don’t accidentally clip “all hits” studies
: "${MAX_HITS:=0}"             # cap input hits/event (0=off)

: "${TIMEOUT_K4RUN:=0}"        # seconds (0=off)

# GGTF clustering thresholds
: "${TBETA:=0.6}"
: "${TD:=0.3}"

# GGTF runtime
: "${ONNX_CHUNK:=4096}"        # hits per ONNX slice
: "${WIRE_GATE_MM:=2.0}"      # wire→circle gate [mm]
: "${MAX_3D_PER_EVT:=200000}"  # cap spacepoints per event
: "${MAX_3D_PER_TRK:=20000}"   # cap spacepoints per track

# ----------------- GGTF debug/coverage/unit knobs (TRI-STATE) -----------------
# Empty => do NOT pass any flag => do NOT override GGTF_tracking.cpp defaults.
: "${GGTF_3D_POS_SCALE:=}"               # e.g. 10.0 if cm->mm mismatch (empty => don’t pass)
: "${GGTF_PRODUCE_ALL_3DHITS:=}"         # empty|1|0
: "${GGTF_ALL_3DHITS_ONLY:=}"            # empty|1|0
: "${GGTF_ALL_3DHITS_TYPE:=}"            # empty => don’t pass
: "${GGTF_APPLY_WIRE_GATE_TO_3DHITS:=}"  # empty|1|0
: "${GGTF_DEBUG_PRINT_3DHIT_R:=}"        # empty|1|0

# GenFit2 “stability profile”
: "${GF_POS_SCALE:=0.1}"           # mm→cm internally
: "${GF_LEN2M:=0.01}"              # cm→m
: "${GF_HIT_SIGMA_XY:=0.8}"        # mm
: "${GF_HIT_SIGMA_Z:=6.0}"         # mm
: "${GF_SEED_POS_SIGMA:=100}"      # mm
: "${GF_SEED_MOM_SIGMA:=10.0}"     # GeV
: "${GF_DEDUP_TOL:=0.50}"          # mm
: "${GF_USE_MAT:=0}"               # 0/1
: "${GF_SEED_PT_MIN:=0.2}"
: "${GF_SEED_PT_MAX:=200.0}"
: "${GF_SEED_P_MIN:=1.2}"          # GeV

# Fitter grouping / fallback / retry (GenFit2)
: "${GF_MIN_GROUP:=7}"
: "${GF_USE_FALLBACK:=1}"
: "${GF_FALLBACK_EPS_CM:=4}"
: "${GF_FALLBACK_MINPTS:=6}"
: "${GF_RETRY:=1}"
: "${GF_RETRY_MEAS_INFL:=5.0}"
: "${GF_RETRY_SEED_POS:=5.0}"
: "${GF_RETRY_SEED_MOM:=5.0}"
: "${GF_MAX_MEAS_PER_GROUP:=0}"

# GenFit2 residual filter knobs
: "${GF_RES_FILTER:=1}"        # 1=on, 0=off
: "${GF_RES_MAX_PULL:=5.0}"
: "${GF_RES_MAX_CHI2:=25.0}"

# ThreePointFitter args
: "${FITTER_LOG:=DEBUG}"
: "${TP_MIN_DELTA_PHI:=0.10}"
: "${TP_MIN_CHORD_MM:=10}"
: "${TP_MIN_HITS:=6}"
: "${TP_MIN_RADIUS_MM:=50}"
: "${TP_FIT_TANLAMBDA:=true}"     # true|false
: "${TP_PRINT_DIAG:=false}"       # true|false
: "${TP_DIAG_EVERY_N:=100}"

# Field / PDG
: "${GF_BZ:=2.0}"
: "${GF_PDG:=13}"

# Digi_v02 settings
: "${DCH_DIGI_VERSION:=v02}"       # v01|v02
: "${DCH_DEADTIME_NS:=450.0}"
: "${DCH_XY_MM:=0.10}"
: "${DCH_Z_MM:=1.0}"
: "${DCH_GAS_TYPE:=0}"
: "${DCH_DRIFT_VEL_UM_NS:=-1.0}"
: "${DCH_SIGNAL_VEL_MM_NS:=$(python3 - <<'PY'
print((2.0/3.0)*299792458e-6)
PY
)}"
: "${DCH_READOUT_START_NS:=1.0}"
: "${DCH_READOUT_DUR_NS:=2000.0}"

# label-0 handling
: "${GGTF_ZERO_MIN:=8}"
: "${GGTF_WIRE_FRAC:=0.80}"
: "${GGTF_PROMOTE_ZERO:=1}"
: "${GGTF_SKIP_ZERO_SMALL:=1}"
: "${GGTF_SKIP_ZERO_ALWAYS:=0}"

# GGTF truth-PDG wire gating
: "${GGTF_TRUTH_GATE:=1}"
: "${GGTF_KEEP_PDG:=13}"
: "${GGTF_DROP_UNLINKED:=1}"

# Safer default: empty => let python auto-guess by digi version
: "${GGTF_WIRE_SIMLINK_COLL:=DCHDigi2SimLinkCollection}"

# ----------------- provenance stamping -----------------
: "${STAMPER:=./scripts/stamp_pipeline_metadata.py}"
: "${STAMP_KEY:=pipeline_metadata_json}"
: "${JOBTAG:=}"                 # optional
: "${STAMP_CONFIGS:=1}"         # 1=record configs as configs, 0=skip

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
echo "[cfg] GGTF_3D_POS_SCALE=${GGTF_3D_POS_SCALE:-<unset>} GGTF_PRODUCE_ALL_3DHITS=${GGTF_PRODUCE_ALL_3DHITS:-<unset>} GGTF_ALL_3DHITS_ONLY=${GGTF_ALL_3DHITS_ONLY:-<unset>}"
echo "[cfg] GGTF_ALL_3DHITS_TYPE=${GGTF_ALL_3DHITS_TYPE:-<unset>} GGTF_APPLY_WIRE_GATE_TO_3DHITS=${GGTF_APPLY_WIRE_GATE_TO_3DHITS:=<unset>} GGTF_DEBUG_PRINT_3DHIT_R=${GGTF_DEBUG_PRINT_3DHIT_R:-<unset>}"

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

: > k4run.log
: > progress.log

# ----------------- auto-collect ALL pipeline knob vars into stamping extras -----------------
build_stamp_extras () {
  local -a extras
  extras+=( --extra "jobtag=${JOBTAG}" )
  extras+=( --extra "local_chain=1" )
  extras+=( --extra "input=${INPUT}" )
  extras+=( --extra "output=${OUTPUT}" )
  extras+=( --extra "model_spec=${MODEL_SPEC}" )
  extras+=( --extra "compact_xml=${COMPACT_XML}" )
  extras+=( --extra "dch_name=${DCH_NAME}" )
  extras+=( --extra "dch_simhits=${DCH_SIMHITS}" )

  # Include any variable whose name starts with these prefixes:
  # DCH_, GGTF_, GF_, TP_ plus a few globals
  local v
  while IFS= read -r v; do
    # Skip huge/unhelpful process vars or internal bash vars if any slip in
    [[ "$v" == "_" ]] && continue
    [[ "$v" == "PWD" || "$v" == "OLDPWD" || "$v" == "SHLVL" ]] && continue

    # Only stamp if it exists (it will) and is not an unbound expansion
    # Use indirect expansion safely; values may contain spaces (rare) -> still okay in one arg
    local val="${!v-}"
    extras+=( --extra "${v}=${val}" )
  done < <(
    compgen -v \
      | LC_ALL=C sort \
      | awk '
          /^(DCH_|GGTF_|GF_|TP_)/ {print; next}
          /^(STAGE|FITTER|FIT_OUT|GGTF_LOG|PRODUCE_3DHITS|MAX_HITS|TIMEOUT_K4RUN|TBETA|TD|ONNX_CHUNK|WIRE_GATE_MM|MAX_3D_PER_EVT|MAX_3D_PER_TRK|FITTER_LOG)$/ {print; next}
        '
  )

  printf '%s\n' "${extras[@]}"
}

# Build once (stable for the run)
mapfile -t STAMP_EXTRAS < <(build_stamp_extras)

stamp_root () {
  local stage="$1"; shift
  local outfile="$1"; shift
  local cmdline="$1"; shift

  if [[ ! -x "$STAMPER" && ! -f "$STAMPER" ]]; then
    echo "[meta][WARN] stamper not found at $STAMPER (skipping metadata stamp)"
    return 0
  fi
  if [[ -z "$outfile" || ! -f "$outfile" ]]; then
    echo "[meta][WARN] output file missing for stage '$stage': '$outfile' (skipping stamp)"
    return 0
  fi

  local -a SARGS
  SARGS+=( --root "$outfile" --stage "$stage" --cmd "$cmdline" --workdir "$PWD" --key "$STAMP_KEY" )

  # Append auto extras + caller extras (configs/inputs/etc)
  python3 "$STAMPER" "${SARGS[@]}" "${STAMP_EXTRAS[@]}" "$@" \
    >/dev/null 2>&1 || echo "[meta][WARN] stamp failed for stage '$stage' (non-fatal)"
}

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

# Produce3DHits (explicit both ways)
if [[ "${PRODUCE_3DHITS}" == "1" ]]; then
  K4_ARGS+=( --produce3DHits )
else
  K4_ARGS+=( --no-produce3DHits )
fi

# Max hits cap only if >0
[[ "${MAX_HITS}" -gt 0 ]] && K4_ARGS+=( --maxHitsPerEvent "${MAX_HITS}" )

# ---- GGTF debug/coverage/unit CLI wiring (tri-state) ----
if [[ -n "${GGTF_3D_POS_SCALE}" ]]; then
  K4_ARGS+=( --ggtf-3dPosScale "${GGTF_3D_POS_SCALE}" )
fi

if [[ -n "${GGTF_PRODUCE_ALL_3DHITS}" ]]; then
  if [[ "${GGTF_PRODUCE_ALL_3DHITS}" == "1" ]]; then
    K4_ARGS+=( --ggtf-produceAll3DHits )
  else
    K4_ARGS+=( --no-ggtf-produceAll3DHits )
  fi
fi

if [[ -n "${GGTF_ALL_3DHITS_ONLY}" ]]; then
  if [[ "${GGTF_ALL_3DHITS_ONLY}" == "1" ]]; then
    K4_ARGS+=( --ggtf-all3DHitsOnly )
  else
    K4_ARGS+=( --no-ggtf-all3DHitsOnly )
  fi
fi

if [[ -n "${GGTF_ALL_3DHITS_TYPE}" ]]; then
  K4_ARGS+=( --ggtf-all3DHitsTypeValue "${GGTF_ALL_3DHITS_TYPE}" )
fi

if [[ -n "${GGTF_APPLY_WIRE_GATE_TO_3DHITS}" ]]; then
  if [[ "${GGTF_APPLY_WIRE_GATE_TO_3DHITS}" == "1" ]]; then
    K4_ARGS+=( --ggtf-applyWireGateTo3DHits )
  else
    K4_ARGS+=( --no-ggtf-applyWireGateTo3DHits )
  fi
fi

if [[ -n "${GGTF_DEBUG_PRINT_3DHIT_R}" ]]; then
  if [[ "${GGTF_DEBUG_PRINT_3DHIT_R}" == "1" ]]; then
    K4_ARGS+=( --ggtf-debugPrint3DHitR )
  else
    K4_ARGS+=( --no-ggtf-debugPrint3DHitR )
  fi
fi

# --- GGTF truth-PDG gating CLI wiring ---
if [[ "${GGTF_TRUTH_GATE}" == "1" ]]; then
  K4_ARGS+=( --ggtf-filterInputWiresByTruthPdg )
else
  K4_ARGS+=( --no-ggtf-filterInputWiresByTruthPdg )
fi
K4_ARGS+=( --ggtf-keepTruthPdg "${GGTF_KEEP_PDG}" )
if [[ "${GGTF_DROP_UNLINKED}" == "1" ]]; then
  K4_ARGS+=( --ggtf-dropWireIfUnlinked )
else
  K4_ARGS+=( --no-ggtf-dropWireIfUnlinked )
fi
if [[ -n "${GGTF_WIRE_SIMLINK_COLL}" ]]; then
  K4_ARGS+=( --ggtf-wireSimLinkColl "${GGTF_WIRE_SIMLINK_COLL}" )
fi

# --- GenFit2 / digi args ---
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

# Residual filter
if [[ "${GF_RES_FILTER}" == "1" ]]; then
  K4_ARGS+=( --gf-residualFilterEnable )
else
  K4_ARGS+=( --no-gf-residualFilterEnable )
fi
K4_ARGS+=( --gf-residualMaxPull "${GF_RES_MAX_PULL}" )
K4_ARGS+=( --gf-residualMaxChi2 "${GF_RES_MAX_CHI2}" )

# Label-0 handling
K4_ARGS+=( --ggtf-zeroMinSizeKeep "${GGTF_ZERO_MIN}" )
K4_ARGS+=( --ggtf-minWireFracKeep "${GGTF_WIRE_FRAC}" )

if [[ "${GGTF_PROMOTE_ZERO}" -eq 1 ]]; then
  K4_ARGS+=( --ggtf-promoteZeroIfGood )
else
  K4_ARGS+=( --no-ggtf-promoteZeroIfGood )
fi

[[ "${GGTF_SKIP_ZERO_SMALL}" -eq 1 ]] && K4_ARGS+=( --ggtf-skipZeroIfSmall ) || K4_ARGS+=( --no-ggtf-skipZeroIfSmall )
[[ "${GGTF_SKIP_ZERO_ALWAYS}" -eq 1 ]] && K4_ARGS+=( --ggtf-skipZeroAlways ) || K4_ARGS+=( --no-ggtf-skipZeroAlways )

# Mat effects
if [[ "${GF_USE_MAT}" == "1" ]]; then
  K4_ARGS+=( --gf-useMat )
else
  K4_ARGS+=( --no-gf-useMat )
fi

# Fallback & retry
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

# ThreePointFitter args
K4_ARGS+=( --tp-minDeltaPhi "${TP_MIN_DELTA_PHI}" )
K4_ARGS+=( --tp-minChordMM  "${TP_MIN_CHORD_MM}" )
K4_ARGS+=( --tp-minGroup    "${TP_MIN_HITS}" )
K4_ARGS+=( --tp-minRadiusMM "${TP_MIN_RADIUS_MM}" )

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

# ----------------- stage-output discovery -----------------
guess_stage_file () {
  local stage="$1"
  local out="$2"
  local dir base stem ext
  dir="$(dirname "$out")"
  base="$(basename "$out")"
  ext="${base##*.}"
  stem="${base%.*}"

  case "$stage" in
    digi)
      for cand in \
        "${dir}/${stem}_digi.${ext}" \
        "${dir}/${stem}.digi.${ext}" \
        "${dir}/digi_${base}" \
        "${dir}/digi.${ext}" \
        "${dir}/digi.root" \
        "${dir}/${stem}_digi.root" \
        "${out}"
      do
        [[ -f "$cand" ]] && { echo "$cand"; return 0; }
      done
      ;;
    ggtf)
      for cand in \
        "${dir}/${stem}_ggtf.${ext}" \
        "${dir}/${stem}.ggtf.${ext}" \
        "${dir}/ggtf_${base}" \
        "${dir}/ggtf.root" \
        "${dir}/${stem}_ggtf.root" \
        "${out}"
      do
        [[ -f "$cand" ]] && { echo "$cand"; return 0; }
      done
      ;;
    fit|reco|*)
      [[ -f "$out" ]] && { echo "$out"; return 0; }
      ;;
  esac

  [[ -f "$out" ]] && { echo "$out"; return 0; }
  echo ""
}

# ----------------- run -----------------
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
if f:
    f.Close()
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

# ----------------- stamping per step -----------------
# Stamp the INPUT (record its own provenance plus the run knobs used downstream)
if [[ -f "$INPUT" ]]; then
  stamp_root "input" "$INPUT" "local_chain.sh (record input provenance only)" \
    --input "$INPUT" \
    --config "$COMPACT_XML" \
    --config "./runDCHTestTrackFinder.py" \
    --config "$MODEL_SPEC"
fi

DIGI_FILE="$(guess_stage_file digi "$OUTPUT")"
GGTF_FILE="$(guess_stage_file ggtf "$OUTPUT")"
FIT_FILE="$(guess_stage_file fit  "$OUTPUT")"

K4_CMD="k4run ${K4_ARGS[*]}"

if [[ -f "$OUTPUT" ]]; then
  stamp_root "final" "$OUTPUT" "$K4_CMD" \
    --input "$INPUT" \
    --config "./runDCHTestTrackFinder.py" \
    --config "$COMPACT_XML" \
    --config "$MODEL_SPEC"
fi

if [[ -n "$DIGI_FILE" && -f "$DIGI_FILE" && "$DIGI_FILE" != "$OUTPUT" ]]; then
  stamp_root "digi" "$DIGI_FILE" "$K4_CMD" \
    --input "$INPUT" \
    --config "./runDCHTestTrackFinder.py" \
    --config "$COMPACT_XML"
fi

if [[ -n "$GGTF_FILE" && -f "$GGTF_FILE" && "$GGTF_FILE" != "$OUTPUT" ]]; then
  stamp_root "ggtf" "$GGTF_FILE" "$K4_CMD" \
    --input "$INPUT" \
    --config "./runDCHTestTrackFinder.py" \
    --config "$MODEL_SPEC"
fi

if [[ -n "$FIT_FILE" && -f "$FIT_FILE" && "$FIT_FILE" != "$OUTPUT" ]]; then
  stamp_root "fit" "$FIT_FILE" "$K4_CMD" \
    --input "$INPUT" \
    --config "./runDCHTestTrackFinder.py"
fi

echo "Run complete"
exit $K4_RC
