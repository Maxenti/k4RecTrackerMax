#!/usr/bin/env bash
set -euo pipefail

# Base directory on EOS where the gun sample subdirs live
BASE_DIR="${1:-/eos/user/c/cglenn/gun_samples}"

# Output file (in CWD unless you pass a second arg)
OUT_FILE="${2:-filelist.txt}"

# The eta values you want to include
ETAS=(0 0.1 0.5 1.0 1.5 2.0)

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

> "$TMP"  # ensure empty

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
  # NUL-delimited find; print each path on its own line via printf
  while IFS= read -r -d '' f; do
    printf '%s\n' "$f"
  done < <(find "$dir" -maxdepth 1 -type f -name '*.root' -print0) >> "$TMP"
done

# Sort & de-dup; remove any accidental blank lines
grep -v '^$' "$TMP" | sort -u > "$OUT_FILE"

echo "[done] Wrote $(wc -l < "$OUT_FILE") paths to $OUT_FILE"
