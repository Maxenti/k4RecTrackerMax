#!/bin/bash
# local_chain.sh — run locally (digi → ggtf → fit) + stamp provenance metadata
# Updated for: DCHdigi_v02 + GGTF_tracking labeled SenseWireHits + GenFit2DCHFitter
set -euo pipefail

########## defaults  ##########
DEFAULT_INPUT="/eos/user/c/cglenn/gun_samples/1_16_2026/eta_+0.50/gun_eta+0.50_pt53.183.root"
DEFAULT_OUTPUT="/eos/user/c/cglenn/reco_samples2/1_16_2026/eta_+0.50/reco_eta+0.50_pt53.183_23_32.root"
DEFAULT_MODEL_SPEC="/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/model.onnx"
DEFAULT_COMPACT_XML="/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml"
DEFAULT_DCH_SIMHITS="DCHCollection"
DEFAULT_DCH_NAME="DCH_v2"
###########################################

# CLI overrides (optional positional args)
INPUT="${1:-$DEFAULT_INPUT}"
OUTPUT="${2:-$DEFAULT_OUTPUT}"
MODEL_SPEC="${3:-$DEFAULT_MODEL_SPEC}"
COMPACT_XML="${4:-$DEFAULT_COMPACT_XML}"
DCH_SIMHITS="${5:-$DEFAULT_DCH_SIMHITS}"
DCH_NAME="${6:-$DEFAULT_DCH_NAME}"

# ----------------- pipeline controls -----------------
: "${STAGE:=fit}"              # digi|ggtf|fit
: "${FITTER:=genfit2}"         # genfit2|none
: "${FIT_OUT:=auto}"

# ----------------- logging & runtime -----------------
: "${GGTF_LOG:=DEBUG}"         # INFO|DEBUG
: "${FITTER_LOG:=DEBUG}"       # INFO|DEBUG
: "${TIMEOUT_K4RUN:=0}"        # seconds (0=off)

# IMPORTANT: default off so you don’t accidentally clip studies
: "${MAX_HITS:=0}"             # cap input hits/event (0=off)

# ----------------- GGTF clustering thresholds -----------------
: "${TBETA:=0.6}"
: "${TD:=0.3}"

# Runtime / ONNX slicing
: "${ONNX_CHUNK:=4096}"        # hits per ONNX slice

# ----------------- NEW: GGTF SenseWireHits output controls -----------------
: "${GGTF_PRODUCE_SENSEWIREHITS:=1}"      # 1 => emit GGTF_SenseWireHits (for fitter)
: "${GGTF_PRODUCE_ALL_SENSEWIREHITS:=0}"  # 1 => emit GGTF_AllSenseWireHits debug stream
: "${GGTF_ALL_SENSEWIREHITS_TYPE:=-777}"  # type value for debug all-stream

# ----------------- NEW: wire hygiene / safety -----------------
: "${GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE:=1}"  # drop insane drift distances
: "${GGTF_MAX_ABS_D_MM:=30.0}"               # |distanceToWire| above this is dropped (if enabled)

# ----------------- label-0 handling -----------------
: "${GGTF_ZERO_MIN:=8}"
: "${GGTF_WIRE_FRAC:=0.80}"
: "${GGTF_PROMOTE_ZERO:=1}"
: "${GGTF_SKIP_ZERO_SMALL:=1}"
: "${GGTF_SKIP_ZERO_ALWAYS:=0}"

# ----------------- GGTF truth-PDG wire gating -----------------
# Safer default OFF unless explicitly debugging truth-gated behavior
: "${GGTF_TRUTH_GATE:=0}"     # 1=on, 0=off
: "${GGTF_KEEP_PDG:=13}"
: "${GGTF_DROP_UNLINKED:=1}"
# Safer default: empty => let python auto-guess by digi version
: "${GGTF_WIRE_SIMLINK_COLL:=DCHDigi2SimLinkCollection}"

# ----------------- GenFit2 knobs -----------------
: "${GF_USE_MAT:=0}"           # 0/1  (if 1, compact XML must exist)
: "${GF_BZ:=2.0}"
: "${GF_PDG:=13}"

: "${GF_SORT_HITS:=1}"         # 1 => --gf-sortHits, 0 => --no-gf-sortHits
: "${GF_DEDUP:=1}"             # 1 => --gf-dedup,    0 => --no-gf-dedup
: "${GF_DEDUP_TOL:=0.10}"      # mm

: "${GF_MIN_GROUP:=6}"
: "${GF_MAX_MEAS_PER_GROUP:=0}"

# Optional z-outlier filter (off by default)
: "${GF_FILTER_Z_OUTLIERS:=0}"
: "${GF_Z_OUTLIER_ABS_MM:=80.0}"
: "${GF_Z_OUTLIER_NSIGMA:=3.5}"
: "${GF_Z_OUTLIER_MIN_FRAC_KEEP:=0.5}"

# ----------------- Digi_v02 settings -----------------
: "${DCH_DIGI_VERSION:=v02}"       # v01|v02
: "${DCH_DEADTIME_NS:=450.0}"
: "${DCH_XY_MM:=0.10}"
: "${DCH_Z_MM:=30.0}"
: "${DCH_GAS_TYPE:=0}"
: "${DCH_DRIFT_VEL_UM_NS:=-1.0}"
: "${DCH_SIGNAL_VEL_MM_NS:=$(python3 - <<'PY'
print((2.0/3.0)*299792458e-6)
PY
)}"
: "${DCH_READOUT_START_NS:=1.0}"
: "${DCH_READOUT_DUR_NS:=900.0}"

# ----------------- provenance stamping -----------------
: "${STAMPER:=./scripts/stamp_pipeline_metadata.py}"
: "${STAMP_KEY:=pipeline_metadata_json}"
: "${JOBTAG:=}"                 # optional
: "${STAMP_CONFIGS:=1}"         # 1=record configs as configs, 0=skip

# ----------------- choose FIT_OUT automatically when requested -----------------
if [[ "${FIT_OUT}" == "auto" ]]; then
  case "${FITTER}" in
    genfit2) FIT_OUT="GenFitTracks" ;;
    none|*)  FIT_OUT="Tracks" ;;
  esac
fi

echo "[cfg] INPUT=$INPUT"
echo "[cfg] OUTPUT=$OUTPUT"
echo "[cfg] MODEL_SPEC=$MODEL_SPEC"
echo "[cfg] COMPACT_XML=$COMPACT_XML  DCH_SIMHITS=$DCH_SIMHITS  DCH_NAME=$DCH_NAME"
echo "[cfg] STAGE=$STAGE FITTER=$FITTER FIT_OUT=$FIT_OUT"
echo "[cfg] GGTF_LOG=$GGTF_LOG FITTER_LOG=$FITTER_LOG MAX_HITS=$MAX_HITS TIMEOUT_K4RUN=$TIMEOUT_K4RUN"
echo "[cfg] TBETA=$TBETA TD=$TD ONNX_CHUNK=$ONNX_CHUNK"
echo "[cfg] GGTF_PRODUCE_SENSEWIREHITS=$GGTF_PRODUCE_SENSEWIREHITS GGTF_PRODUCE_ALL_SENSEWIREHITS=$GGTF_PRODUCE_ALL_SENSEWIREHITS"
echo "[cfg] GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE=$GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE GGTF_MAX_ABS_D_MM=$GGTF_MAX_ABS_D_MM"
echo "[cfg] GF_USE_MAT=$GF_USE_MAT GF_SORT_HITS=$GF_SORT_HITS GF_DEDUP=$GF_DEDUP GF_DEDUP_TOL=$GF_DEDUP_TOL GF_MIN_GROUP=$GF_MIN_GROUP"

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

  local v
  while IFS= read -r v; do
    [[ "$v" == "_" ]] && continue
    [[ "$v" == "PWD" || "$v" == "OLDPWD" || "$v" == "SHLVL" ]] && continue
    local val="${!v-}"
    extras+=( --extra "${v}=${val}" )
  done < <(
    compgen -v \
      | LC_ALL=C sort \
      | awk '
          /^(DCH_|GGTF_|GF_)/ {print; next}
          /^(STAGE|FITTER|FIT_OUT|GGTF_LOG|FITTER_LOG|MAX_HITS|TIMEOUT_K4RUN|TBETA|TD|ONNX_CHUNK)$/ {print; next}
        '
  )

  printf '%s\n' "${extras[@]}"
}

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

  python3 "$STAMPER" "${SARGS[@]}" "${STAMP_EXTRAS[@]}" "$@" \
    >/dev/null 2>&1 || echo "[meta][WARN] stamp failed for stage '$stage' (non-fatal)"
}

# ----------------- build python args -----------------
K4_ARGS=(
  ./runDCHTestTrackFinder.py
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
  --fitter     "$FITTER"
  --fitterLog  "$FITTER_LOG"
  --fitOut     "$FIT_OUT"
  --stage      "$STAGE"
  --dchDigiVersion   "$DCH_DIGI_VERSION"
  --dch-deadtime-ns  "$DCH_DEADTIME_NS"
  --xyResolution_mm  "$DCH_XY_MM"
  --zResolution_mm   "$DCH_Z_MM"
  --dch-gas-type     "$DCH_GAS_TYPE"
  --dch-drift-vel-um-ns   "$DCH_DRIFT_VEL_UM_NS"
  --dch-signal-vel-mm-ns  "$DCH_SIGNAL_VEL_MM_NS"
  --rw-start-ns      "$DCH_READOUT_START_NS"
  --rw-duration-ns   "$DCH_READOUT_DUR_NS"
  --gf-bz           "$GF_BZ"
  --gf-pdg          "$GF_PDG"
  --gf-dedupTol     "$GF_DEDUP_TOL"
  --gf-minGroup     "$GF_MIN_GROUP"
  --gf-maxMeasPerGroup "$GF_MAX_MEAS_PER_GROUP"
)

# Max hits cap only if >0
[[ "$MAX_HITS" -gt 0 ]] && K4_ARGS+=( --maxHitsPerEvent "$MAX_HITS" )

# GGTF output toggles
if [[ "$GGTF_PRODUCE_SENSEWIREHITS" == "1" ]]; then
  K4_ARGS+=( --ggtf-produceSenseWireHits )
else
  K4_ARGS+=( --no-ggtf-produceSenseWireHits )
fi

if [[ "$GGTF_PRODUCE_ALL_SENSEWIREHITS" == "1" ]]; then
  K4_ARGS+=( --ggtf-produceAllSenseWireHits )
else
  K4_ARGS+=( --no-ggtf-produceAllSenseWireHits )
fi
K4_ARGS+=( --ggtf-allSenseWireHitsTypeValue "$GGTF_ALL_SENSEWIREHITS_TYPE" )

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
if [[ -n "$GGTF_WIRE_SIMLINK_COLL" ]]; then
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

# Optional z-outlier filter
if [[ "$GF_FILTER_Z_OUTLIERS" == "1" ]]; then
  K4_ARGS+=( --gf-filterZOutliers )
else
  K4_ARGS+=( --no-gf-filterZOutliers )
fi
K4_ARGS+=( --gf-zOutlierAbsMM "$GF_Z_OUTLIER_ABS_MM" )
K4_ARGS+=( --gf-zOutlierNSigma "$GF_Z_OUTLIER_NSIGMA" )
K4_ARGS+=( --gf-zOutlierMinFracKeep "$GF_Z_OUTLIER_MIN_FRAC_KEEP" )

echo "[k4run] args: ${K4_ARGS[*]}" | tee -a k4run.log

run_cmd() {
  if [[ "$TIMEOUT_K4RUN" -gt 0 ]]; then
    timeout --signal=TERM --kill-after=30 "$TIMEOUT_K4RUN" "$@"
  else
    "$@"
  fi
}

# ----------------- stage-output discovery (unchanged) -----------------
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
  | awk '/GGTF_tracking|GenFit2DCHFitter|RSS=|Peak=|TOTAL|flatten:|onnx:|clustering|Application Manager|tracks=|MemoryAuditor/{print; fflush()}' > progress.log

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

# ----------------- stamping per step (unchanged) -----------------
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
