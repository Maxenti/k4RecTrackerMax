#!/usr/bin/env bash
# Wrapper for DDSim gun jobs on HTCondor: write local, stage to EOS via xrdcp, validate.
set -euo pipefail

# ------------------------ Key4HEP environment ------------------------
if [ -f /cvmfs/sw.hsf.org/key4hep/setup.sh ]; then
  K4SETUP=/cvmfs/sw.hsf.org/key4hep/setup.sh
else
  K4SETUP=/cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh
fi

# Source only if not already set; clear "$@" while sourcing
if [[ -z "${KEY4HEP_STACK:-}" && -z "${K4ENV:-}" ]]; then
  __orig_args=("$@"); set +u; set --; source "$K4SETUP"; set -- "${__orig_args[@]}"; set -u 2>/dev/null || true
else
  echo "[env] Key4HEP already set, not sourcing again."
fi

# ----------------------------- Logging ------------------------------
echo "[env] host=$(hostname) user=$(whoami) date=$(date)"
echo "[env] PWD=$PWD"
command -v ddsim   >/dev/null && echo "[env] ddsim=$(command -v ddsim)"
command -v python3 >/dev/null && echo "[env] python3=$(command -v python3)"
command -v jq      >/dev/null && echo "[env] jq=$(command -v jq)"
command -v xrdfs   >/dev/null && echo "[env] xrdfs=$(command -v xrdfs)"
command -v xrdcp   >/dev/null && echo "[env] xrdcp=$(command -v xrdcp)"
echo "[env] ls -la:" && ls -la

# --------------------------- Input arguments ------------------------
# 1: params JSON, 2: compact XML, 3: EOS output directory base
PARAMS_JSON="${1:?need PARAMS_JSON file}"
COMPACT_XML="${2:?need COMPACT_XML path or file}"
OUT_DIR_BASE="${3:?need OUT_DIR base on EOS}"

# Basename fallback (Condor often flattens paths)
[[ -s "$PARAMS_JSON" ]] || { b=$(basename "$PARAMS_JSON"); [[ -s "$b" ]] && PARAMS_JSON="$b"; }
[[ -s "$COMPACT_XML"  ]] || { b=$(basename "$COMPACT_XML");  [[ -s "$b" ]] && COMPACT_XML="$b"; }

echo "[args] PARAMS_JSON=$PARAMS_JSON"
echo "[args] COMPACT_XML=$COMPACT_XML"
echo "[args] OUT_DIR_BASE=$OUT_DIR_BASE"

# Basic checks
[[ -s "$PARAMS_JSON" ]] || { echo "FATAL: params JSON missing: $PARAMS_JSON" >&2; exit 2; }
[[ -s "$COMPACT_XML"  ]] || { echo "FATAL: compact XML missing: $COMPACT_XML" >&2; exit 3; }
command -v jq >/dev/null 2>&1      || { echo "FATAL: jq not found" >&2; exit 4; }
command -v ddsim >/dev/null 2>&1   || { echo "FATAL: ddsim not found" >&2; exit 5; }
command -v python3 >/dev/null 2>&1 || { echo "FATAL: python3 not found" >&2; exit 6; }
command -v xrdfs  >/dev/null 2>&1  || { echo "FATAL: xrdfs not found" >&2; exit 7; }
command -v xrdcp  >/dev/null 2>&1  || { echo "FATAL: xrdcp not found" >&2; exit 8; }

# ---------------------------- Parameters ----------------------------
pt=$(jq -r '.pt' "$PARAMS_JSON")
eta=$(jq -r '.eta' "$PARAMS_JSON")
p=$(jq -r '.p' "$PARAMS_JSON")
theta=$(jq -r '.theta' "$PARAMS_JSON")
nev=$(jq -r '.nev' "$PARAMS_JSON")
particle=$(jq -r '.particle' "$PARAMS_JSON")
seed=$(jq -r '.seed' "$PARAMS_JSON")
phi_uniform=$(jq -r '.phi_uniform' "$PARAMS_JSON")
theta_smear=$(jq -r '.theta_smear' "$PARAMS_JSON")

for k in pt eta p theta nev particle seed; do
  v=$(jq -r ".${k}" "$PARAMS_JSON")
  [[ -n "$v" && "$v" != "null" ]] || { echo "FATAL: params JSON missing key: ${k}" >&2; jq . "$PARAMS_JSON" >&2 || true; exit 9; }
done

# ------------------------ Output naming/layout ----------------------
eta_tag=$(printf "%+.2f" "$eta")
pt_tag=$(
python3 - "$pt" <<'PY'
import sys
pt=float(sys.argv[1]); s=f"{pt:.5g}"
print(s.replace("+","").replace("-","m"))
PY
)
rel_dir="eta_${eta_tag}"
file_name="gun_eta${eta_tag}_pt${pt_tag}.root"

# Local scratch output
SCRATCH="${TMPDIR:-$PWD}"
LOCAL_OUT="${SCRATCH}/${file_name}"

# EOS (POSIX path) and XRootD URL
EOS_POSIX="${OUT_DIR_BASE%/}/${rel_dir}/${file_name}"
EOS_DIR_POSIX="$(dirname "$EOS_POSIX")"
EOS_URL="root://eosuser.cern.ch//${EOS_POSIX#/}"

echo "[job] eta=$eta  pt=$pt  p=$p  theta=$theta  nev=$nev  seed=$seed"
echo "[job] LOCAL_OUT=$LOCAL_OUT"
echo "[job] EOS_POSIX=$EOS_POSIX"
echo "[job] EOS_URL=$EOS_URL"

# Ensure EOS directory exists
export XRD_RUNFORKHANDLER=1
xrdfs eosuser.cern.ch mkdir -p "//${EOS_DIR_POSIX#/}" || true

# ---------------------------- Gun options ---------------------------
phi_opts=( --gun.phiMin 0*deg --gun.phiMax 360*deg )
[[ "${phi_uniform}" == "true" ]] && phi_opts+=( --gun.distribution uniform )

theta_min="$theta"; theta_max="$theta"
if python3 - "$theta" "$theta_smear" <<'PY' >/dev/null
import math,sys
t=float(sys.argv[1]); s=float(sys.argv[2])
raise SystemExit(0 if (s>0 and math.isfinite(s)) else 1)
PY
then
  theta_min=$(python3 - "$theta" "$theta_smear" <<'PY'
import math,sys
t=float(sys.argv[1]); s=float(sys.argv[2])
print(max(0.0, t-s))
PY
)
  theta_max=$(python3 - "$theta" "$theta_smear" <<'PY'
import math,sys
t=float(sys.argv[1]); s=float(sys.argv[2])
print(min(math.pi, t+s))
PY
)
  echo "[job] theta smear: [${theta_min}, ${theta_max}] rad"
fi

# ------------------------ Validation helpers ------------------------
validate_root_local () {
  python3 - "$LOCAL_OUT" <<'PY'
import sys, ROOT
ROOT.gErrorIgnoreLevel = 3001
path=sys.argv[1]
f = ROOT.TFile.Open(path)
def fail(msg): print(f"[validate-local][FAIL] {msg}"); sys.exit(1)
if not f or f.IsZombie(): fail(f"cannot open: {path}")
t = f.Get("events"); m = f.Get("podio_metadata")
if not t: fail("missing 'events' tree")
if not m: fail("missing 'podio_metadata' tree")
if t.GetListOfBranches().GetEntries() < 1: fail("no branches in 'events'")
f.Close()
print("[validate-local][OK]")
PY
}

validate_root_remote () {
  python3 - "$EOS_URL" <<'PY'
import sys, ROOT
ROOT.gErrorIgnoreLevel = 3001
url=sys.argv[1]
f = ROOT.TFile.Open(url)
def fail(msg): print(f"[validate-remote][FAIL] {msg}"); sys.exit(1)
if not f or f.IsZombie(): fail(f"cannot open: {url}")
t = f.Get("events"); m = f.Get("podio_metadata")
if not t: fail("missing 'events' tree")
if not m: fail("missing 'podio_metadata' tree")
if t.GetListOfBranches().GetEntries() < 1: fail("no branches in 'events'")
f.Close()
print("[validate-remote][OK]")
PY
}

# ------------------------------ Run DDSim ---------------------------
run_ddsim_local () {
  local out="$1"
  echo "[ddsim] starting (local write) ..."
  set -x
  ddsim \
    --compactFile "$COMPACT_XML" \
    --numberOfEvents "$nev" \
    --random.seed "$seed" \
    --enableGun \
    --gun.particle "$particle" \
    --gun.energy "${p}*GeV" \
    --gun.distribution uniform \
    --gun.thetaMin "${theta_min}*rad" \
    --gun.thetaMax "${theta_max}*rad" \
    "${phi_opts[@]}" \
    --outputFile "$out"
  set +x
  echo "[ddsim] finished -> $out"
}

stage_to_eos () {
  # remove any pre-existing target to avoid “file exists” races
  xrdfs eosuser.cern.ch rm "//${EOS_POSIX#/}" >/dev/null 2>&1 || true
  xrdcp -f "$LOCAL_OUT" "$EOS_URL"
}

# Attempts (re-run DDSim with different seed if validation fails)
attempt=1
max_attempts=2
while (( attempt <= max_attempts )); do
  rm -f "$LOCAL_OUT"
  run_ddsim_local "$LOCAL_OUT" || echo "[ddsim] non-zero exit (attempt $attempt) — will still try to validate."

  if [[ -s "$LOCAL_OUT" ]] && validate_root_local; then
    stage_to_eos
    if validate_root_remote; then
      size=$(xrdfs eosuser.cern.ch stat -q Size "//${EOS_POSIX#/}" 2>/dev/null | awk '{print $2}')
      echo "[done] ${size:-?} bytes  $EOS_POSIX"
      rm -f "$LOCAL_OUT" || true
      exit 0
    else
      echo "[stage][WARN] remote validation failed; will retry run."
    fi
  else
    echo "[retry] local validation failed on attempt $attempt"
  fi
  seed=$((seed+12345))
  attempt=$((attempt+1))
done

echo "FATAL: no valid output at $EOS_POSIX after $max_attempts attempt(s)" >&2
exit 10
