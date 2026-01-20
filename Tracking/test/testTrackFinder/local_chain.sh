#!/bin/bash
# local_chain.sh — run locally (digi → ggtf → fit) + stamp provenance metadata
# Updated for: runDCHTestTrackFinder.py (Jan 18 2026) + GenFit2DCHFitter (Jan 11 2026 nightly)
#
# This version:
#   - Adds optional TGeo ROOT geometry import support via runDCHTestTrackFinder.py:
#       * New env knob:  TGEO_FILE
#       * New positional arg: [7] TGeo ROOT file (optional)
#       * Passes: --tgeoFile "$TGEO_FILE" (only if non-empty)
#       * Stamps: tgeo_file into metadata extras
#
# Usage:
#   ./local_chain.sh [INPUT] [OUTPUT] [MODEL_SPEC] [COMPACT_XML] [DCH_SIMHITS] [DCH_NAME] [TGEO_FILE]
#
set -euo pipefail

########## defaults  ##########
DEFAULT_INPUT="/eos/user/c/cglenn/gun_samples/1_16_2026/eta_+0.00/gun_eta+0.00_pt1.root"
DEFAULT_OUTPUT="/eos/user/c/cglenn/reco_samples2/Debugging/eta_+0.00/reco_eta+0.00_pt1_nomat.root"
DEFAULT_MODEL_SPEC="/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/model.onnx"
DEFAULT_COMPACT_XML="/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml"
DEFAULT_DCH_SIMHITS="DCHCollection"
DEFAULT_DCH_NAME="DCH_v2"
# Optional: if you have a pre-exported ROOT TGeo geometry file (sets gGeoManager via TGeoManager::Import)
DEFAULT_TGEO_FILE="/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03CF.root"
###########################################

# CLI overrides (optional positional args)
INPUT="${1:-$DEFAULT_INPUT}"
OUTPUT="${2:-$DEFAULT_OUTPUT}"
MODEL_SPEC="${3:-$DEFAULT_MODEL_SPEC}"
COMPACT_XML="${4:-$DEFAULT_COMPACT_XML}"
DCH_SIMHITS="${5:-$DEFAULT_DCH_SIMHITS}"
DCH_NAME="${6:-$DEFAULT_DCH_NAME}"
TGEO_FILE="${7:-$DEFAULT_TGEO_FILE}"

# ----------------- pipeline controls -----------------
: "${STAGE:=fit}"              # digi|ggtf|fit  (cumulative in runDCHTestTrackFinder.py)
: "${SKIP_DIGI:=0}"            # 1 => pass --skipDigi (input already digitized)
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

# ----------------- wire hygiene / safety -----------------
: "${GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE:=1}"  # drop insane drift distances
: "${GGTF_MAX_ABS_D_MM:=30.0}"               # |distanceToWire| above this is dropped (if enabled)

# ----------------- label-0 handling -----------------
: "${GGTF_ZERO_MIN:=8}"
: "${GGTF_WIRE_FRAC:=0.60}"
: "${GGTF_PROMOTE_ZERO:=1}"
: "${GGTF_SKIP_ZERO_SMALL:=1}"
: "${GGTF_SKIP_ZERO_ALWAYS:=0}"

# ----------------- GGTF truth-PDG wire gating -----------------
: "${GGTF_TRUTH_GATE:=0}"     # 1=on, 0=off (default off unless you’re debugging)
: "${GGTF_KEEP_PDG:=13}"
: "${GGTF_DROP_UNLINKED:=1}"
: "${GGTF_WIRE_SIMLINK_COLL:=DCHDigi2SimLinkCollection}"   # optional override; leave empty to let python guess

# ----------------- GGTF output collection name -----------------
: "${GGTF_TRACKS_OUT:=CDCHTracks}"

# ----------------- GenFit2 knobs (match UPDATED runDCHTestTrackFinder.py) -----------------
: "${GF_USE_MAT:=0}"                  # 0/1  (if 1, compact XML must exist)
: "${GF_DISABLE_ELOSS:=1}"            # default in python: True
: "${GF_DISABLE_ALL_MAT:=0}"
: "${GF_HARD_DISABLE_MAT_IF_NO_GEO:=1}"

: "${GF_BZ:=2.0}"
: "${GF_PDG:=13}"

: "${GF_REJECT_NEGATIVE_LABELS:=1}"   # default in python: True

: "${GF_SORT_HITS:=1}"
: "${GF_DEDUP:=1}"
: "${GF_DEDUP_TOL:=0.010}"             # mm

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
: "${GF_POSITION_UNIT_SCALE:=0.1}"     # mm->cm for GenFit internal
: "${GF_WIRE_HALF_LENGTH_MM:=2250.0}"  # synthetic endpoints half-length
: "${GF_MAX_DRIFT_MM:=7.0}"
: "${GF_MAX_DRIFT_MM_FOR_HIT:=8.0}"
: "${GF_MIN_DRIFT_ERR_MM:=0.10}"
: "${GF_MAX_DRIFT_ERR_MM:=1.0}"

# Angles
: "${GF_WIRE_ANGLES_DEGREES:=0}"      # 1 => --gf-wireAnglesAreDegrees, else radians explicitly

# ----------------- observability gating knobs -----------------
: "${GF_SKIP_IF_OBS_TOO_LOW:=0}"   # 1 => --gf-skipIfObsTooLow, 0 => --no-gf-skipIfObsTooLow
: "${GF_MIN_HITS_FOR_OBS:=10}"
: "${GF_OBS_SIGMA_EFF_MM:=0.025}"
: "${GF_OBS_MIN_PHISPAN_RAD:=0.006}"
: "${GF_OBS_MIN_CHORD_MM:=20.0}"
: "${GF_OBS_MIN_SAGITTA_MM:=0.015}"
: "${GF_OBS_SCORE_MIN:=1.0}"

# ----------------- seed discipline knobs -----------------
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

# ----------------- pre-fit outlier veto knobs -----------------
: "${GF_PREFIT_OUTLIER_VETO:=0}"
: "${GF_OUTLIER_MAX_DROP:=1}"
: "${GF_OUTLIER_CIRCLE_RESIDUAL_MM:=0.8}"
: "${GF_OUTLIER_CHORD_RESIDUAL_MM:=2.0}"
: "${GF_OUTLIER_MIN_KEEP:=10}"

# ----------------- PD guards / stats / diagnostics -----------------
: "${GF_MIN_COV_EIGENVALUE:=0}"
: "${GF_STATS_TRUNC_CENTRAL_FRAC:=0.80}"
: "${GF_DIAG_EVERY_N_TRACKS:=1}"

# ----------------- Digi settings -----------------
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
: "${JOBTAG:=}"
: "${STAMP_CONFIGS:=1}"

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
echo "[cfg] TGEO_FILE=${TGEO_FILE:-<none>}"
echo "[cfg] STAGE=$STAGE SKIP_DIGI=$SKIP_DIGI FITTER=$FITTER FIT_OUT=$FIT_OUT GGTF_TRACKS_OUT=$GGTF_TRACKS_OUT"
echo "[cfg] GGTF_LOG=$GGTF_LOG FITTER_LOG=$FITTER_LOG MAX_HITS=$MAX_HITS TIMEOUT_K4RUN=$TIMEOUT_K4RUN"
echo "[cfg] TBETA=$TBETA TD=$TD ONNX_CHUNK=$ONNX_CHUNK"
echo "[cfg] GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE=$GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE GGTF_MAX_ABS_D_MM=$GGTF_MAX_ABS_D_MM"
echo "[cfg] GF_USE_MAT=$GF_USE_MAT GF_DISABLE_ELOSS=$GF_DISABLE_ELOSS GF_DISABLE_ALL_MAT=$GF_DISABLE_ALL_MAT GF_HARD_DISABLE_MAT_IF_NO_GEO=$GF_HARD_DISABLE_MAT_IF_NO_GEO"
echo "[cfg] GF_REJECT_NEGATIVE_LABELS=$GF_REJECT_NEGATIVE_LABELS GF_SORT_HITS=$GF_SORT_HITS GF_DEDUP=$GF_DEDUP GF_DEDUP_TOL=$GF_DEDUP_TOL"
echo "[cfg] GF_MIN_HITS_PER_TRACK=$GF_MIN_HITS_PER_TRACK GF_MIN_MEASUREMENTS_TO_FIT=$GF_MIN_MEASUREMENTS_TO_FIT GF_MIN_FITTED_POINTS_WITH_FI=$GF_MIN_FITTED_POINTS_WITH_FI"
echo "[cfg] GF_USE_KF_PREFIT=$GF_USE_KF_PREFIT GF_KF_MAX_ITERS=$GF_KF_MAX_ITERS GF_USE_DAF=$GF_USE_DAF GF_DAF_MAX_ITERS=$GF_DAF_MAX_ITERS GF_TRY_BOTH_MOM_DIRS=$GF_TRY_BOTH_MOM_DIRS GF_FALLBACK_TO_KF_IF_DAF_FAILS=$GF_FALLBACK_TO_KF_IF_DAF_FAILS"
echo "[cfg] GF_PUBLISH_STATE_CENTRAL_FRAC=$GF_PUBLISH_STATE_CENTRAL_FRAC GF_PUBLISH_PT_MAX_GEV=$GF_PUBLISH_PT_MAX_GEV GF_MAX_CHI2_NDF=$GF_MAX_CHI2_NDF"
echo "[cfg] GF_INVALID_PT_SENTINEL=$GF_INVALID_PT_SENTINEL GF_OMEGA_VAR_GOOD=$GF_OMEGA_VAR_GOOD GF_OMEGA_VAR_BAD=$GF_OMEGA_VAR_BAD"
echo "[cfg] GF_POSITION_UNIT_SCALE=$GF_POSITION_UNIT_SCALE GF_WIRE_HALF_LENGTH_MM=$GF_WIRE_HALF_LENGTH_MM GF_MAX_DRIFT_MM=$GF_MAX_DRIFT_MM GF_MAX_DRIFT_MM_FOR_HIT=$GF_MAX_DRIFT_MM_FOR_HIT"
echo "[cfg] GF_MIN_DRIFT_ERR_MM=$GF_MIN_DRIFT_ERR_MM GF_MAX_DRIFT_ERR_MM=$GF_MAX_DRIFT_ERR_MM"
echo "[cfg] GF_WIRE_ANGLES_DEGREES=$GF_WIRE_ANGLES_DEGREES"
echo "[cfg] GF_SKIP_IF_OBS_TOO_LOW=$GF_SKIP_IF_OBS_TOO_LOW GF_MIN_HITS_FOR_OBS=$GF_MIN_HITS_FOR_OBS GF_OBS_SIGMA_EFF_MM=$GF_OBS_SIGMA_EFF_MM"
echo "[cfg] GF_OBS_MIN_PHISPAN_RAD=$GF_OBS_MIN_PHISPAN_RAD GF_OBS_MIN_CHORD_MM=$GF_OBS_MIN_CHORD_MM GF_OBS_MIN_SAGITTA_MM=$GF_OBS_MIN_SAGITTA_MM GF_OBS_SCORE_MIN=$GF_OBS_SCORE_MIN"
echo "[cfg] GF_SEED_ENDPOINT_K=$GF_SEED_ENDPOINT_K GF_SEED_TANGENT_K=$GF_SEED_TANGENT_K GF_SEED_POS_SIGMA_MM=$GF_SEED_POS_SIGMA_MM GF_SEED_MOM_SIGMA_GEV=$GF_SEED_MOM_SIGMA_GEV"
echo "[cfg] GF_USE_SAGITTA_SEED=$GF_USE_SAGITTA_SEED GF_MIN_SAGITTA_FOR_SEED_MM=$GF_MIN_SAGITTA_FOR_SEED_MM"
echo "[cfg] GF_SEED_PT_FALLBACK_GEV=$GF_SEED_PT_FALLBACK_GEV GF_SEED_PT_MIN_GEV=$GF_SEED_PT_MIN_GEV GF_SEED_PT_MAX_GEV=$GF_SEED_PT_MAX_GEV GF_SEED_P_MIN_GEV=$GF_SEED_P_MIN_GEV"
echo "[cfg] GF_PREFIT_OUTLIER_VETO=$GF_PREFIT_OUTLIER_VETO GF_OUTLIER_MAX_DROP=$GF_OUTLIER_MAX_DROP GF_OUTLIER_CIRCLE_RESIDUAL_MM=$GF_OUTLIER_CIRCLE_RESIDUAL_MM"
echo "[cfg] GF_OUTLIER_CHORD_RESIDUAL_MM=$GF_OUTLIER_CHORD_RESIDUAL_MM GF_OUTLIER_MIN_KEEP=$GF_OUTLIER_MIN_KEEP"
echo "[cfg] GF_MIN_COV_EIGENVALUE=$GF_MIN_COV_EIGENVALUE GF_STATS_TRUNC_CENTRAL_FRAC=$GF_STATS_TRUNC_CENTRAL_FRAC GF_DIAG_EVERY_N_TRACKS=$GF_DIAG_EVERY_N_TRACKS"
echo "[cfg] GGTF_TRUTH_GATE=$GGTF_TRUTH_GATE KEEP_PDG=$GGTF_KEEP_PDG DROP_UNLINKED=$GGTF_DROP_UNLINKED WIRE_SIMLINK_COLL=${GGTF_WIRE_SIMLINK_COLL:-<auto>}"

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
  extras+=( --extra "tgeo_file=${TGEO_FILE}" )
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
          /^(STAGE|SKIP_DIGI|FITTER|FIT_OUT|GGTF_TRACKS_OUT|GGTF_LOG|FITTER_LOG|MAX_HITS|TIMEOUT_K4RUN|TBETA|TD|ONNX_CHUNK|TGEO_FILE)$/ {print; next}
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

# Optional: import a ROOT TGeo geometry file (sets gGeoManager) if provided
if [[ -n "${TGEO_FILE}" ]]; then
  K4_ARGS+=( --tgeoFile "$TGEO_FILE" )
fi

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
print("[verify] %s OK=%s NEV=%d" % (sys.argv[1], ok, nev))
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
