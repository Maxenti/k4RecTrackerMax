#!/usr/bin/env bash
# local_chain_all.sh — run local_chain.sh over all gun samples, optionally in parallel
set -euo pipefail

# ----------------- defaults (override via env) -----------------
IN_DIR="${IN_DIR:-/eos/user/c/cglenn/gun_samples}"        # where gun .root live (can contain eta_* subdirs)
OUT_DIR="${OUT_DIR:-/eos/user/c/cglenn/reco_samples}"     # where reco .root + logs go
MODEL_SPEC="${MODEL_SPEC:-/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/model.onnx}"
COMPACT_XML="${COMPACT_XML:-/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml}"
DCH_SIMHITS="${DCH_SIMHITS:-DCHCollection}"
DCH_NAME="${DCH_NAME:-DCH_v2}"

JOBS="${JOBS:-8}"                 # only used if GNU parallel is available
SKIP_EXISTING="${SKIP_EXISTING:-1}"  # 1=skip files whose OUT exists & is non-empty
DRY_RUN="${DRY_RUN:-0}"              # 1=print commands only
# ---------------------------------------------------------------

# where this script lives (so we can find local_chain.sh reliably)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHAIN="${SCRIPT_DIR}/local_chain.sh"
[[ -x "$CHAIN" ]] || { echo "FATAL: local_chain.sh not found/executable at $CHAIN" >&2; exit 2; }

echo "[all] IN_DIR=$IN_DIR"
echo "[all] OUT_DIR=$OUT_DIR"
echo "[all] MODEL_SPEC=$MODEL_SPEC"
echo "[all] COMPACT_XML=$COMPACT_XML"
echo "[all] DCH_SIMHITS=$DCH_SIMHITS  DCH_NAME=$DCH_NAME"
echo "[all] JOBS=$JOBS  SKIP_EXISTING=$SKIP_EXISTING  DRY_RUN=$DRY_RUN"

[[ -d "$IN_DIR" ]] || { echo "FATAL: IN_DIR not found: $IN_DIR" >&2; exit 3; }
mkdir -p "$OUT_DIR" "$OUT_DIR/logs"

# function to run one file
run_one() {
  local in="$1"
  local base rel sub out_sub out log

  # mirror input subdir structure under OUT_DIR
  rel="${in#$IN_DIR/}"                # e.g. "eta_+0.00/gun_eta+0.00_pt0.10.root" or just "gun_....root"
  sub="$(dirname "$rel")"             # "eta_+0.00" or "."
  base="$(basename "$rel")"           # "gun_eta+0.00_pt0.10.root"

  out_sub="$OUT_DIR/${sub#.}"         # drop "." if top-level
  mkdir -p "$out_sub"
  out="$out_sub/reco_${base}"         # reco_<input>.root
  log="$OUT_DIR/logs/${base}.log"

  if [[ "$SKIP_EXISTING" == "1" && -s "$out" ]]; then
    echo "[skip] $in -> $out (exists)"
    return 0
  fi

  echo "[run]  $in"
  echo "      -> $out"
  echo "[cmd] $CHAIN \"$in\" \"$out\" \"$MODEL_SPEC\" \"$COMPACT_XML\" \"$DCH_SIMHITS\" \"$DCH_NAME\"" | tee "$log"

  if [[ "$DRY_RUN" == "1" ]]; then
    return 0
  fi

  # Call local_chain.sh with all your environment knobs (material, fitter, etc.)
  # local_chain.sh will read those from the env (GF_USE_MAT, FITTER, TBETA, …).
  if ! "$CHAIN" \
        "$in" \
        "$out" \
        "$MODEL_SPEC" \
        "$COMPACT_XML" \
        "$DCH_SIMHITS" \
        "$DCH_NAME" \
        >> "$log" 2>&1; then
    echo "[FAIL] $in (see $log)"
    return 1
  fi

  # post-check: output exists and is non-empty
  if [[ ! -s "$out" ]]; then
    echo "[WARN] output is missing/empty: $out (see $log)"
    return 1
  fi

  echo "[OK]   $out"
}

export -f run_one
export IN_DIR OUT_DIR MODEL_SPEC COMPACT_XML DCH_SIMHITS DCH_NAME SKIP_EXISTING DRY_RUN
export CHAIN

# collect inputs (any *.root under IN_DIR)
mapfile -t INPUTS < <(find "$IN_DIR" -type f -name '*.root' | sort)
echo "[all] found ${#INPUTS[@]} input ROOT files under $IN_DIR"

if [[ ${#INPUTS[@]} -eq 0 ]]; then
  echo "[all] nothing to do."
  exit 0
fi

# run in parallel if available
if command -v parallel >/dev/null 2>&1; then
  echo "[all] using GNU parallel -j $JOBS"
  # --halt now,fail=1 stops on first failure; drop if you prefer to continue
  parallel --halt now,fail=1 -j "$JOBS" run_one ::: "${INPUTS[@]}"
else
  echo "[all] GNU parallel not found; running serially."
  rc=0
  for f in "${INPUTS[@]}"; do
    if ! run_one "$f"; then rc=1; fi
  done
  exit $rc
fi

echo "[all] done → $OUT_DIR"
