# DOC:
# Summary: Authoritative HTCondor worker wrapper for one DCH reco job, staging geometry/runtime/model inputs, running k4run, validating GenFit/GGTF output, stamping provenance, and copying the final ROOT file to EOS.
# Status: authoritative
# Usage:
#   ./reco_job.sh INFILE OUTDIR COMPACT_XML [FITTER] [GF_USE_MAT_ARG] [STAGE] [FIT_OUT] [K4REL] [TGEO_FILE]
# Examples:
#   ./reco_job.sh \
#     root://eosuser.cern.ch///eos/.../gun_samples/CF/eta_+1.00/gun_eta+1.00_pt14.142.root \
#     /eos/.../reco_samples/CF \
#     /eos/.../IDEA_CF.xml \
#     genfit2 \
#     1 \
#     fit \
#     GenFitTracks \
#     2026-01-11 \
#     /eos/.../IDEA_CF.root
# Inputs: One DDSim gun-sample EDM4hep ROOT file, EOS reco output directory, compact DD4hep XML, runtime.tgz, bundled GGTF model.onnx, optional matching TGeo ROOT geometry, and a pinned Key4HEP nightly release.
# Outputs: Local reco_<input>.root copied to OUTDIR/<eta_dir>/reco_<input>.root on EOS; optional failure log under OUTDIR/<eta_dir>/logs/; provenance metadata stamped into final and any intermediate stage outputs when available.
# Collections: Reads DCHCollection by default; writes the cumulative requested stage output, normally DCHDigi2Collection/DCH_DigiCollection, CDCHTracks/GGTF output, OutputWireHitsGGTF/GGTF_3DHits where configured by steering, and GenFitTracks when FITTER=genfit2 and STAGE=fit.
# Connects-To: configs/condor/reco.condor, scripts/submit_reco.sh, scripts/make_runtime.sh, steering/runDCHTestTrackFinder.py, scripts/stamp_pipeline_metadata.py, scripts/analyze_pt_resolution_grid.py
# Arguments:
#   INFILE: input DDSim/reco ROOT file; may be /eos/... or root://... and is converted to XRootD for worker reading.
#   OUTDIR: EOS output directory base for reco outputs.
#   COMPACT_XML: compact DD4hep XML path or XRootD URL; the containing geometry directory is staged locally and added to DD4hep_XMLPATH.
#   FITTER: fitter selection passed to steering; default genfit2.
#   GF_USE_MAT_ARG: default material-effects toggle used to initialize GF_USE_MAT; 1 enables material-aware GenFit.
#   STAGE: cumulative steering stage, normally digi, ggtf, or fit; default fit.
#   FIT_OUT: output track collection; auto maps genfit2 to GenFitTracks and none/other to Tracks.
#   K4REL: pinned Key4HEP nightly release sourced inside a clean environment; default 2026-01-11.
#   TGEO_FILE: TGeo ROOT geometry file used when GF_USE_MAT=1; should match COMPACT_XML/material variant.
#   SKIP_DIGI: set to 1 to bypass digitization when the input is already digitized.
#   GGTF_LOG, FITTER_LOG, TIMEOUT_K4RUN, MAX_HITS: logging, timeout, and debug caps.
#   TBETA, TD, ONNX_CHUNK: GGTF clustering/model execution controls.
#   GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE, GGTF_MAX_ABS_D_MM: wire-hit drift-distance rejection controls.
#   GGTF_ZERO_MIN, GGTF_WIRE_FRAC, GGTF_PROMOTE_ZERO, GGTF_SKIP_ZERO_SMALL, GGTF_SKIP_ZERO_ALWAYS: GGTF label-zero handling controls.
#   GGTF_TRUTH_GATE, GGTF_KEEP_PDG, GGTF_DROP_UNLINKED, GGTF_WIRE_SIMLINK_COLL: optional truth-gated GGTF debug controls; normally off for production.
#   GGTF_TRACKS_OUT: GGTF output track collection, normally CDCHTracks.
#   GF_USE_MAT, GF_DISABLE_ELOSS, GF_DISABLE_ALL_MAT, GF_HARD_DISABLE_MAT_IF_NO_GEO: GenFit material-effects policy.
#   GF_BZ, GF_PDG: magnetic field and particle hypothesis used by GenFit2DCHFitter.
#   GF_REJECT_NEGATIVE_LABELS, GF_SORT_HITS, GF_DEDUP, GF_DEDUP_TOL: input-hit hygiene controls.
#   GF_MIN_HITS_PER_TRACK, GF_MIN_MEASUREMENTS_TO_FIT, GF_MIN_FITTED_POINTS_WITH_FI, GF_MAX_CHI2_NDF: fit acceptance controls.
#   GF_USE_KF_PREFIT, GF_KF_MAX_ITERS, GF_TRY_BOTH_MOM_DIRS, GF_USE_DAF, GF_DAF_MAX_ITERS, GF_FALLBACK_TO_KF_IF_DAF_FAILS: GenFit fit-strategy controls.
#   GF_USE_BIASED_STATE_FOR_PUBLISH, GF_PUBLISH_STATE_CENTRAL_FRAC, GF_PUBLISH_PT_MAX_GEV, GF_INVALID_PT_SENTINEL, GF_OMEGA_VAR_GOOD, GF_OMEGA_VAR_BAD: output-state and pT-publication controls.
#   GF_POSITION_UNIT_SCALE, GF_WIRE_HALF_LENGTH_MM, GF_MAX_DRIFT_MM, GF_MAX_DRIFT_MM_FOR_HIT, GF_MIN_DRIFT_ERR_MM, GF_MAX_DRIFT_ERR_MM, GF_WIRE_ANGLES_DEGREES: wire geometry, unit, and measurement-error controls.
#   GF_SKIP_IF_OBS_TOO_LOW, GF_MIN_HITS_FOR_OBS, GF_OBS_SIGMA_EFF_MM, GF_OBS_MIN_PHISPAN_RAD, GF_OBS_MIN_CHORD_MM, GF_OBS_MIN_SAGITTA_MM, GF_OBS_SCORE_MIN: curvature-observability controls.
#   GF_SEED_ENDPOINT_K, GF_SEED_TANGENT_K, GF_SEED_POS_SIGMA_MM, GF_SEED_MOM_SIGMA_GEV, GF_USE_SAGITTA_SEED, GF_MIN_SAGITTA_FOR_SEED_MM, GF_SEED_PT_FALLBACK_GEV, GF_SEED_PT_MIN_GEV, GF_SEED_PT_MAX_GEV, GF_SEED_P_MIN_GEV: seed construction controls.
#   GF_PREFIT_OUTLIER_VETO, GF_OUTLIER_MAX_DROP, GF_OUTLIER_CIRCLE_RESIDUAL_MM, GF_OUTLIER_CHORD_RESIDUAL_MM, GF_OUTLIER_MIN_KEEP: prefit outlier rejection controls.
#   GF_MIN_COV_EIGENVALUE, GF_STATS_TRUNC_CENTRAL_FRAC, GF_DIAG_EVERY_N_TRACKS: covariance/statistics/diagnostic controls.
#   DCH_DIGI_VERSION, DCH_DEADTIME_NS, DCH_XY_MM, DCH_Z_MM, DCH_GAS_TYPE, DCH_DRIFT_VEL_UM_NS, DCH_SIGNAL_VEL_MM_NS, DCH_READOUT_START_NS, DCH_READOUT_DUR_NS: DCH digitizer timing/readout controls.
#   STAMPER, STAMP_KEY, JOBTAG, STAMP_CONFIGS: provenance metadata stamping controls.
# Notes:
#   This is the authoritative worker-side reco job used by the maintained Condor reco pipeline.
#   It is intended to match the local_chain.sh physics/reco knob surface while adding Condor-safe staging, XRootD/EOS I/O, idempotent output checks, and failure-log preservation.
#   runtime.tgz must be produced by scripts/make_runtime.sh before submission and must contain the steering file, libraries, catalogs, Python config, and model.onnx.
#   For material-aware CF-vs-W comparisons, COMPACT_XML and TGEO_FILE must correspond to the same detector/material variant, and all reco knobs should remain fixed between variants.
#   The script skips work if the expected EOS output already exists, so remove stale outputs explicitly before rerunning a changed configuration.
#   A nonzero k4run return code is overridden only when the output ROOT file opens and contains events; inspect copied logs before trusting such cases.
#   Full logs are copied to EOS when fatal/error patterns are detected or validation fails.
#   The final collection check only verifies that the requested FIT_OUT appears among output branches; downstream pT analysis is still needed for physics validation.
# Tags: authoritative, reco, condor, worker, k4run, eos, xrootd, dch, ggtf, genfit2, metadata, key4hep
# DOC_END

#!/usr/bin/env bash
# reco_job.sh — HTCondor wrapper for ONE input file/job.
# Goal: pass EXACTLY the same knobs and defaults as local_chain.sh
# while still being Condor/EOS-safe (xrootd staging, idempotent output,
# pinned Key4hep nightly via arg).

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
GF_USE_MAT_ARG="${5:-1}"              # 0/1
STAGE="${6:-fit}"                     # digi|ggtf|fit
FIT_OUT="${7:-auto}"                  # auto|<name>
K4REL="${8:-2026-01-11}"              # key4hep nightly tag
TGEO_FILE="${9:-/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03_100umCF_0.313474umAu.root}"

LOCAL_TGEO=""

echo "[args] INFILE=$INFILE"
echo "[args] OUTDIR=$OUTDIR"
echo "[args] COMPACT_XML=$COMPACT_XML"
echo "[args] FITTER=$FITTER GF_USE_MAT_ARG=$GF_USE_MAT_ARG STAGE=$STAGE FIT_OUT=$FIT_OUT"
echo "[args] K4REL=$K4REL"
echo "[args] TGEO_FILE=$TGEO_FILE"

# ---------------- Source pinned nightly inside job via clean subshell ----------------
echo "[env] K4SETUP=$K4SETUP"
echo "[env] Building clean Key4hep environment for nightly $K4REL ..."

K4_EXPORTS="$PWD/key4hep_env_${K4REL}.exports"

env -i \
  HOME="${HOME:-$PWD}" \
  USER="${USER:-condor}" \
  LOGNAME="${LOGNAME:-condor}" \
  SHELL=/bin/bash \
  TERM="${TERM:-xterm}" \
  PATH=/usr/bin:/bin \
  /bin/bash -lc "
    set -eo pipefail
    set +u
    source '$K4SETUP' -r '$K4REL' >/dev/null
    set -u
    declare -px
  " > "$K4_EXPORTS"

[[ -s "$K4_EXPORTS" ]] || { echo "[env][FATAL] failed to build clean Key4hep exports"; exit 13; }

# Import the clean nightly environment into this job shell.
# shellcheck disable=SC1090
source "$K4_EXPORTS"

command -v k4run >/dev/null || { echo "[env][FATAL] k4run not in PATH after clean setup"; exit 10; }
echo "[env] k4run=$(command -v k4run)"
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

to_eos_posix() {
  local p="$1"
  if [[ "$p" == root://eosuser.cern.ch//* ]]; then
    echo "/${p#root://eosuser.cern.ch//}"
  else
    echo "$p"
  fi
}

eos_path_from_xrd() {
  echo "$1" | sed -E 's#^root://eosuser\.cern\.ch##'
}

extract_eta_dir() {
  local eos_path="$1"
  local eta=""
  eta="$(echo "$eos_path" | grep -oE 'eta_[+-][0-9]+(\.[0-9]+)?' | head -n1 || true)"
  if [[ -n "$eta" ]]; then
    echo "$eta"
    return 0
  fi

  local tok
  tok="$(basename "$eos_path" | grep -oE 'eta[+-][0-9]+(\.[0-9]+)?' | head -n1 || true)"
  if [[ -n "$tok" ]]; then
    echo "eta_${tok#eta}"
    return 0
  fi

  echo "eta_unknown"
}

copy_failure_log_to_eos() {
  if [[ -n "${FULLLOG:-}" && -f "${FULLLOG:-}" ]]; then
    echo "[log] copying full log to EOS: $LOG_EOS_XRD"
    xrdcp -f "$FULLLOG" "$LOG_EOS_XRD" || true
  else
    echo "[log][WARN] full log missing, cannot copy to EOS: ${FULLLOG:-<unset>}"
  fi
}

# ---------------- TGeo staging ----------------
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

# ---------------- Runtime bundle ----------------
[[ -s runtime.tgz ]] || { echo "FATAL: runtime.tgz missing"; exit 4; }
tar -xzf runtime.tgz
RTPFX="$PWD/runtime"

# ---------------- Provenance stamping ----------------
: "${STAMP_KEY:=pipeline_metadata_json}"
: "${JOBTAG:=}"
: "${STAMP_CONFIGS:=1}"

STAMPER="${STAMPER:-}"
if [[ -z "$STAMPER" ]]; then
  for cand in \
    "$PWD/scripts/stamp_pipeline_metadata.py" \
    "$PWD/stamp_pipeline_metadata.py" \
    "$RTPFX/scripts/stamp_pipeline_metadata.py" \
    "$RTPFX/python/stamp_pipeline_metadata.py"
  do
    if [[ -f "$cand" ]]; then
      STAMPER="$cand"
      break
    fi
  done
fi

echo "[meta] STAMPER=${STAMPER:-<not found>}"

build_stamp_extras() {
  local -a extras

  extras+=( --extra "condor_clusterid=${_CONDOR_CLUSTERID:-}" )
  extras+=( --extra "condor_procid=${_CONDOR_PROCID:-}" )
  extras+=( --extra "condor_schedd=${_CONDOR_SCHEDD_HOST:-}" )
  extras+=( --extra "condor_slot=${_CONDOR_SLOT:-}" )
  extras+=( --extra "condor_scratch=${_CONDOR_SCRATCH_DIR:-}" )

  extras+=( --extra "jobtag=${JOBTAG}" )
  extras+=( --extra "condor_job=1" )
  extras+=( --extra "infile=${INFILE}" )
  extras+=( --extra "infile_xrd=${INFILE_XRD:-}" )
  extras+=( --extra "out_eos=${OUT_EOS_XRD:-}" )
  extras+=( --extra "outdir=${OUTDIR}" )
  extras+=( --extra "eta_dir=${ETA_DIR:-}" )

  extras+=( --extra "k4rel=${K4REL}" )
  extras+=( --extra "k4setup=${K4SETUP}" )
  extras+=( --extra "root_version=$(root-config --version 2>/dev/null || true)" )
  extras+=( --extra "hostname=$(hostname -f 2>/dev/null || hostname)" )

  extras+=( --extra "compact_xml_arg=${COMPACT_XML}" )
  extras+=( --extra "local_compact_xml=${LOCAL_COMPACT_XML:-}" )
  extras+=( --extra "dd4hep_xmlpath=${DD4hep_XMLPATH:-}" )
  extras+=( --extra "tgeo_file_arg=${TGEO_FILE:-}" )
  extras+=( --extra "local_tgeo=${LOCAL_TGEO:-}" )
  extras+=( --extra "onnx_model=${MODEL:-}" )

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

stamp_root() {
  local stage="$1"; shift
  local outfile="$1"; shift
  local cmdline="$1"; shift

  if [[ -z "$STAMPER" || ! -f "$STAMPER" ]]; then
    echo "[meta][WARN] stamper not found in runtime (skipping metadata stamp)"
    return 0
  fi
  if [[ -z "$outfile" || ! -f "$outfile" ]]; then
    echo "[meta][WARN] output missing for stage '$stage': '$outfile' (skipping stamp)"
    return 0
  fi

  local -a SARGS
  SARGS+=( --root "$outfile" --stage "$stage" --cmd "$cmdline" --workdir "$PWD" --key "$STAMP_KEY" )

  if [[ "${STAMP_CONFIGS}" == "1" ]]; then
    [[ -n "${LOCAL_COMPACT_XML:-}" ]] && SARGS+=( --config "$LOCAL_COMPACT_XML" )
    [[ -n "${MODEL:-}" ]] && SARGS+=( --config "$MODEL" )
    [[ -n "${LOCAL_TGEO:-}" ]] && SARGS+=( --config "$LOCAL_TGEO" )
    SARGS+=( --config "$RTPFX/runDCHTestTrackFinder.py" )
  fi

  python3 "$STAMPER" "${SARGS[@]}" "${STAMP_EXTRAS[@]}" "$@" >/dev/null 2>&1 \
    || echo "[meta][WARN] stamp failed for stage '$stage' (non-fatal)"
}

guess_stage_file() {
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
        "${dir}/digi.root" \
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
        "${out}"
      do
        [[ -f "$cand" ]] && { echo "$cand"; return 0; }
      done
      ;;
    fit|final|reco|*)
      [[ -f "$out" ]] && { echo "$out"; return 0; }
      ;;
  esac
  echo ""
}

# ---------------- Runtime env ----------------
export LD_LIBRARY_PATH="$RTPFX/lib64:$RTPFX/lib:${LD_LIBRARY_PATH:-}"
export GAUDI_PLUGIN_PATH="$RTPFX/lib64:$RTPFX/lib:${GAUDI_PLUGIN_PATH:-}"
export PYTHONPATH="$RTPFX/python:${PYTHONPATH:-}"

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

# ---------------- Stage compact geometry ----------------
LOCAL_GEOM_BASE="$PWD/geom"
mkdir -p "$LOCAL_GEOM_BASE"
LOCAL_COMPACT_XML="$COMPACT_XML"

if [[ "$COMPACT_XML" == root://* ]]; then
  EOS_COMPACT_PATH="$(echo "$COMPACT_XML" | sed -E 's#^root://eosuser\.cern\.ch/+##')"
  EOS_COMPACT_PATH="/${EOS_COMPACT_PATH#"/"}"
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
  LOCAL_COMPACT_XML="$COMPACT_XML"
fi

[[ -s "$LOCAL_COMPACT_XML" ]] || { echo "[env][FATAL] staged compact not found: $LOCAL_COMPACT_XML"; exit 31; }

export DD4hep_XMLPATH="$(dirname "$LOCAL_COMPACT_XML"):${DD4hep_XMLPATH:-}"
echo "[env] Using compact: $LOCAL_COMPACT_XML"
echo "[env] DD4hep_XMLPATH=$DD4hep_XMLPATH"

# ---------------- Model resolution ----------------
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
INFILE_EOS="$(to_eos_posix "$INFILE")"
ETA_DIR="$(extract_eta_dir "$INFILE_EOS")"

base="$(basename "$INFILE_EOS")"
OUT_LOCAL="$PWD/reco_${base}"

OUT_EOS_POSIX="${OUTDIR%/}/${ETA_DIR}/reco_${base}"
OUT_EOS_XRD="$(to_xrd "$OUT_EOS_POSIX")"
OUT_EOS_PATH_ON_EOS="$(eos_path_from_xrd "$OUT_EOS_XRD")"

echo "[io] input:   $INFILE_XRD"
echo "[io] eta_dir: $ETA_DIR"
echo "[io] output:  $OUT_EOS_XRD"
echo "[io] local:   $OUT_LOCAL"

# ---------------- Full log policy ----------------
TMPDIR="${_CONDOR_SCRATCH_DIR:-${TMPDIR:-$PWD}}"
FULLLOG="${TMPDIR}/reco_${ETA_DIR}_${base}.full.log"

LOG_EOS_POSIX="${OUTDIR%/}/${ETA_DIR}/logs/reco_${base}.log"
LOG_EOS_XRD="$(to_xrd "$LOG_EOS_POSIX")"
LOG_EOS_PATH_ON_EOS="$(eos_path_from_xrd "$LOG_EOS_XRD")"

if command -v xrdfs >/dev/null 2>&1; then
  xrdfs eosuser.cern.ch mkdir -p "$(dirname "$LOG_EOS_PATH_ON_EOS")" >/dev/null 2>&1 || true
fi

echo "[log] full log (scratch): $FULLLOG"
echo "[log] eos log (on fail):  $LOG_EOS_XRD"

# ---------------- Skip existing output ----------------
if command -v xrdfs >/dev/null 2>&1; then
  if xrdfs eosuser.cern.ch stat "$OUT_EOS_PATH_ON_EOS" >/dev/null 2>&1; then
    echo "[skip] Output already exists: $OUT_EOS_XRD"
    exit 0
  fi
fi

if command -v xrdfs >/dev/null 2>&1; then
  xrdfs eosuser.cern.ch mkdir -p "$(dirname "$OUT_EOS_PATH_ON_EOS")" >/dev/null 2>&1 || true
fi

# ======================================================================
#  KNOBS
# ======================================================================

: "${SKIP_DIGI:=0}"
: "${FIT_OUT:=$FIT_OUT}"
: "${FITTER:=$FITTER}"
: "${STAGE:=$STAGE}"

: "${GGTF_LOG:=DEBUG}"
: "${FITTER_LOG:=DEBUG}"
: "${TIMEOUT_K4RUN:=0}"
: "${MAX_HITS:=0}"

: "${TBETA:=0.6}"
: "${TD:=0.3}"

: "${ONNX_CHUNK:=4096}"

: "${GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE:=1}"
: "${GGTF_MAX_ABS_D_MM:=30.0}"

: "${GGTF_ZERO_MIN:=8}"
: "${GGTF_WIRE_FRAC:=0.60}"
: "${GGTF_PROMOTE_ZERO:=1}"
: "${GGTF_SKIP_ZERO_SMALL:=1}"
: "${GGTF_SKIP_ZERO_ALWAYS:=0}"

: "${GGTF_TRUTH_GATE:=0}"
: "${GGTF_KEEP_PDG:=13}"
: "${GGTF_DROP_UNLINKED:=1}"
: "${GGTF_WIRE_SIMLINK_COLL:=DCHDigi2SimLinkCollection}"

: "${GGTF_TRACKS_OUT:=CDCHTracks}"

: "${GF_USE_MAT:=$GF_USE_MAT_ARG}"
: "${GF_DISABLE_ELOSS:=1}"
: "${GF_DISABLE_ALL_MAT:=0}"
: "${GF_HARD_DISABLE_MAT_IF_NO_GEO:=1}"

: "${GF_BZ:=2.0}"
: "${GF_PDG:=13}"

: "${GF_REJECT_NEGATIVE_LABELS:=1}"
: "${GF_SORT_HITS:=1}"
: "${GF_DEDUP:=1}"
: "${GF_DEDUP_TOL:=0.010}"

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

: "${GF_USE_BIASED_STATE_FOR_PUBLISH:=1}"
: "${GF_PUBLISH_STATE_CENTRAL_FRAC:=0.30}"
: "${GF_PUBLISH_PT_MAX_GEV:=300.0}"

: "${GF_INVALID_PT_SENTINEL:=-1.0}"
: "${GF_OMEGA_VAR_GOOD:=1e-4}"
: "${GF_OMEGA_VAR_BAD:=1.0}"

: "${GF_POSITION_UNIT_SCALE:=0.1}"
: "${GF_WIRE_HALF_LENGTH_MM:=2250.0}"
: "${GF_MAX_DRIFT_MM:=7.0}"
: "${GF_MAX_DRIFT_MM_FOR_HIT:=8.0}"
: "${GF_MIN_DRIFT_ERR_MM:=0.10}"
: "${GF_MAX_DRIFT_ERR_MM:=1.0}"
: "${GF_WIRE_ANGLES_DEGREES:=0}"

: "${GF_SKIP_IF_OBS_TOO_LOW:=0}"
: "${GF_MIN_HITS_FOR_OBS:=10}"
: "${GF_OBS_SIGMA_EFF_MM:=0.025}"
: "${GF_OBS_MIN_PHISPAN_RAD:=0.006}"
: "${GF_OBS_MIN_CHORD_MM:=20.0}"
: "${GF_OBS_MIN_SAGITTA_MM:=0.015}"
: "${GF_OBS_SCORE_MIN:=1.0}"

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

: "${GF_PREFIT_OUTLIER_VETO:=0}"
: "${GF_OUTLIER_MAX_DROP:=1}"
: "${GF_OUTLIER_CIRCLE_RESIDUAL_MM:=0.8}"
: "${GF_OUTLIER_CHORD_RESIDUAL_MM:=2.0}"
: "${GF_OUTLIER_MIN_KEEP:=10}"

: "${GF_MIN_COV_EIGENVALUE:=0}"
: "${GF_STATS_TRUNC_CENTRAL_FRAC:=0.80}"
: "${GF_DIAG_EVERY_N_TRACKS:=1}"

: "${DCH_DIGI_VERSION:=v02}"
: "${DCH_DEADTIME_NS:=450.0}"
: "${DCH_XY_MM:=0.10}"
: "${DCH_Z_MM:=30.0}"
: "${DCH_GAS_TYPE:=0}"
: "${DCH_DRIFT_VEL_UM_NS:=-1.0}"
: "${DCH_SIGNAL_VEL_MM_NS:=199.86163866666666}"

: "${DCH_READOUT_START_NS:=1.0}"
: "${DCH_READOUT_DUR_NS:=900.0}"

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TORCH_NUM_THREADS=1
export MALLOC_ARENA_MAX=2
export ORT_DISABLE_MEMORY_ARENA=1
export ORT_ENABLE_MEM_PATTERN=0

if [[ "${FIT_OUT}" == "auto" ]]; then
  case "${FITTER}" in
    genfit2) FIT_OUT="GenFitTracks" ;;
    none|*)  FIT_OUT="Tracks" ;;
  esac
fi

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

if [[ "$SKIP_DIGI" == "1" ]]; then
  K4_ARGS+=( --skipDigi )
fi

[[ "$MAX_HITS" -gt 0 ]] && K4_ARGS+=( --maxHitsPerEvent "$MAX_HITS" )

if [[ "$GGTF_DROP_WIRE_IF_ABS_D_TOO_LARGE" == "1" ]]; then
  K4_ARGS+=( --ggtf-dropWireIfAbsDTooLarge )
else
  K4_ARGS+=( --no-ggtf-dropWireIfAbsDTooLarge )
fi
K4_ARGS+=( --ggtf-maxAbsDMM "$GGTF_MAX_ABS_D_MM" )

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

K4_ARGS+=( --ggtf-zeroMinSizeKeep "$GGTF_ZERO_MIN" )
K4_ARGS+=( --ggtf-minWireFracKeep "$GGTF_WIRE_FRAC" )
[[ "$GGTF_PROMOTE_ZERO" -eq 1 ]] && K4_ARGS+=( --ggtf-promoteZeroIfGood ) || K4_ARGS+=( --no-ggtf-promoteZeroIfGood )
[[ "$GGTF_SKIP_ZERO_SMALL" -eq 1 ]] && K4_ARGS+=( --ggtf-skipZeroIfSmall ) || K4_ARGS+=( --no-ggtf-skipZeroIfSmall )
[[ "$GGTF_SKIP_ZERO_ALWAYS" -eq 1 ]] && K4_ARGS+=( --ggtf-skipZeroAlways ) || K4_ARGS+=( --no-ggtf-skipZeroAlways )

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

if [[ "$GF_SKIP_IF_OBS_TOO_LOW" == "1" ]]; then
  K4_ARGS+=( --gf-skipIfObsTooLow )
else
  K4_ARGS+=( --no-gf-skipIfObsTooLow )
fi

if [[ "$GF_USE_SAGITTA_SEED" == "1" ]]; then
  K4_ARGS+=( --gf-useSagittaSeed )
else
  K4_ARGS+=( --no-gf-useSagittaSeed )
fi

if [[ "$GF_USE_BIASED_STATE_FOR_PUBLISH" == "1" ]]; then
  K4_ARGS+=( --gf-useBiasedStateForPublish )
else
  K4_ARGS+=( --no-gf-useBiasedStateForPublish )
fi

if [[ "$GF_PREFIT_OUTLIER_VETO" == "1" ]]; then
  K4_ARGS+=( --gf-prefitOutlierVeto )
else
  K4_ARGS+=( --no-gf-prefitOutlierVeto )
fi

if [[ "$GF_WIRE_ANGLES_DEGREES" == "1" ]]; then
  K4_ARGS+=( --gf-wireAnglesAreDegrees )
else
  K4_ARGS+=( --gf-wireAnglesAreRadians )
fi

# ---------------- Run ----------------
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
sys.exit(0 if ok and nev > 0 else 1)
PY
}

if [[ $K4_RC -ne 0 ]]; then
  if check_edm_root "$OUT_LOCAL"; then
    echo "[note] k4run rc=$K4_RC but output looks fine; overriding to 0."
    echo "[note] k4run rc=$K4_RC but output looks fine; overriding to 0." >>"$FULLLOG"
    K4_RC=0
  fi
fi

NEED_LOG=0
if [[ $K4_RC -ne 0 ]]; then
  NEED_LOG=1
fi
if grep -Eqi '(FATAL|Segmentation|Traceback|Exception thrown|ill-conditioned covariance|not positive definite|ERROR)' "$FULLLOG"; then
  NEED_LOG=1
fi

if [[ $NEED_LOG -eq 1 ]]; then
  echo "[log] issues detected -> copying full log to EOS: $LOG_EOS_XRD"
  echo "---- tail(full log) ----"
  tail -n 120 "$FULLLOG" || true
  copy_failure_log_to_eos
fi

# ---------------- Verify required collection exists ----------------
set +e
python3 - <<PY "$OUT_LOCAL" "$FIT_OUT"
import sys, ROOT
out = sys.argv[1]
coll = sys.argv[2]
f = ROOT.TFile.Open(out)
if not f or f.IsZombie():
    print(f"[verify] FATAL: cannot open output: {out}")
    sys.exit(2)
t = f.Get("events")
if not t:
    print("[verify] FATAL: no 'events' tree")
    sys.exit(3)
names = [b.GetName() for b in t.GetListOfBranches()]
present = any(coll in n for n in names)
print("[verify] first branches:", ",".join(names[:12]), "..." if len(names) > 12 else "")
print(f"[verify] looking for '{coll}' -> present={present}")
f.Close()
sys.exit(0 if present else 4)
PY
VER_RC=$?
set -e

if [[ $VER_RC -ne 0 ]]; then
  echo "[verify] collection check failed rc=$VER_RC (coll=$FIT_OUT)."
  echo "[verify] collection check failed rc=$VER_RC (coll=$FIT_OUT)." >>"$FULLLOG"
  copy_failure_log_to_eos
  exit $VER_RC
fi

# ---------------- Stamp metadata into ROOT output(s) ----------------
K4_CMD="k4run ${K4_ARGS[*]}"

stamp_root "final" "$OUT_LOCAL" "$K4_CMD" --input "$INFILE_XRD"

DIGI_FILE="$(guess_stage_file digi "$OUT_LOCAL")"
GGTF_FILE="$(guess_stage_file ggtf "$OUT_LOCAL")"

if [[ -n "$DIGI_FILE" && -f "$DIGI_FILE" && "$DIGI_FILE" != "$OUT_LOCAL" ]]; then
  stamp_root "digi" "$DIGI_FILE" "$K4_CMD" --input "$INFILE_XRD"
fi
if [[ -n "$GGTF_FILE" && -f "$GGTF_FILE" && "$GGTF_FILE" != "$OUT_LOCAL" ]]; then
  stamp_root "ggtf" "$GGTF_FILE" "$K4_CMD" --input "$INFILE_XRD"
fi

echo "[stage] xrdcp -> $OUT_EOS_XRD"
xrdcp -f "$OUT_LOCAL" "$OUT_EOS_XRD"
echo "[ok] wrote $OUT_EOS_XRD"

rm -f "$OUT_LOCAL" || true
rm -f "$FULLLOG" || true

exit $K4_RC