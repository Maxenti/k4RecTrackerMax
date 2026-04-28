# DOC:
# Summary: Build the XRootD input file list for reco Condor submission by scanning selected eta directories under a gun-sample campaign.
# Status: authoritative
# Usage:
#   bash scripts/make_filelist.sh [BASE_DIR] [OUT_FILE]
# Examples:
#   bash scripts/make_filelist.sh \
#     /eos/user/c/cglenn/gun_samples/1_29_2026/100umCF_0.313474umAu \
#     filelist.txt
# Inputs: EOS or local gun-sample campaign directory containing eta_<+X.XX> or eta<+X.XX> subdirectories with ROOT files.
# Outputs: Sorted unique text file containing one ROOT input path per line, converted to root://eosuser.cern.ch// URLs for EOS paths.
# Collections: None; this is a file-discovery helper and does not inspect EDM4hep collections.
# Connects-To: scripts/submit_reco.sh, configs/condor/reco.condor, scripts/reco_job.sh, scripts/condor_ddsim.sh, configs/condor/ddsim.condor
# Arguments:
#   BASE_DIR: optional first positional argument; base directory containing eta subdirectories. Defaults to a hard-coded campaign path.
#   OUT_FILE: optional second positional argument; output file list path. Default filelist.txt.
#   ETAS: internal bash array controlling which eta points are scanned; edit this list when changing campaign eta coverage.
# Notes:
#   This script is authoritative for preparing the reco Condor queue input list, but it is campaign-specific in the sense that the ETAS array is currently hard-coded.
#   It checks both eta_<tag> and eta<tag> directory naming conventions, where tag is formatted as %+0.2f, such as +1.00.
#   EOS POSIX paths are converted to XRootD URLs so worker nodes can read inputs robustly.
#   Missing eta directories are warnings, not fatal errors, so always check the final path count before submitting reco.
#   If a campaign uses a different eta grid, update ETAS or replace this script with a flag-driven eta-list version before production submission.
# Tags: authoritative, reco, filelist, eos, xrootd, condor, gun-samples, submission
# DOC_END

#!/usr/bin/env bash
set -euo pipefail

# Base directory on EOS where the gun sample subdirs live
BASE_DIR="${1:-/eos/user/c/cglenn/gun_samples/1_29_2026/100umCF_0.313474umAu}"

# Output file (in CWD unless you pass a second arg)
OUT_FILE="${2:-filelist.txt}"

# The eta values you want to include
ETAS=(0 0.1 0.5 1.0 1.5 2.0)

to_xrd() {
  local p="$1"
  if [[ "$p" == root://* ]]; then
    echo "$p"
  elif [[ "$p" == /eos/* ]]; then
    # convert POSIX EOS path to xrootd URL
    echo "root://eosuser.cern.ch//${p}"
  else
    echo "$p"
  fi
}

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

> "$TMP"

for eta in "${ETAS[@]}"; do
  tag=$(printf "%+.2f" "$eta")           # e.g. +0.00
  d1="${BASE_DIR}/eta_${tag}"
  d2="${BASE_DIR}/eta${tag}"

  dir=""
  if [[ -d "$d1" ]]; then
    dir="$d1"
  elif [[ -d "$d2" ]]; then
    dir="$d2"
  else
    echo "[warn] no directory for eta=$eta (checked '$d1' and '$d2')" >&2
    continue
  fi

  echo "[scan] eta=$eta  dir=$dir"
  while IFS= read -r -d '' f; do
    printf '%s\n' "$(to_xrd "$f")"
  done < <(find "$dir" -maxdepth 1 -type f -name '*.root' -print0) >> "$TMP"
done

sed -e 's/[[:space:]]*$//' "$TMP" | grep -v '^$' | sort -u > "$OUT_FILE"

echo "[done] Wrote $(wc -l < "$OUT_FILE") paths to $OUT_FILE"
