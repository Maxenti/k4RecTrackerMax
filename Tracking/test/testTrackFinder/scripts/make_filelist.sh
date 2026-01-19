#!/usr/bin/env bash
set -euo pipefail

# Base directory on EOS where the gun sample subdirs live
BASE_DIR="${1:-/eos/user/c/cglenn/gun_samples/1_19_2026/W}"

# Output file (in CWD unless you pass a second arg)
OUT_FILE="${2:-filelist.txt}"

# The eta values you want to include
ETAS=(0 0.1 0.5 1.0 1.5 2.0 2.5)

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
