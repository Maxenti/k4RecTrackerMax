#!/usr/bin/env bash
set -euo pipefail

# -------- EDIT/OVERRIDE VIA ENV --------
IN_DIR="${IN_DIR:-/eos/user/c/cglenn/gun_samples/1_19_2026/CF}"
OUT_DIR="${OUT_DIR:-/eos/user/c/cglenn/reco_samples2/1_21_2026/CFmat}"
COMPACT_XML="${COMPACT_XML:-/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml}"

FITTER="${FITTER:-genfit2}"             # genfit2 | simple | threepoint
FIT_OUT="${FIT_OUT:-auto}"              # auto | <collection name>
GF_USE_MAT="${GF_USE_MAT:-1}"           # 1|0
STAGE="${STAGE:-fit}"                   # digi|ggtf|fit
EXTRA="${EXTRA:---fitterLog INFO}"      # any additional flags (NO quotes)
      # any additional flags (quotes ok)

# Key4hep nightly to use inside jobs
K4REL="${K4REL:-2026-01-11}"
TGEOFILE="${TGEOFILE:-/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03CF.root}"

# --------------------------------------

cd "$(dirname "$0")"   # scripts/
mkdir -p logs

[[ -s reco.condor ]] || { echo "FATAL: scripts/reco.condor missing" >&2; exit 2; }
[[ -x make_filelist.sh ]] || chmod +x make_filelist.sh

FILELIST="filelist.txt"
echo "[prep] Building filelist from: $IN_DIR"
./make_filelist.sh "$IN_DIR" "$FILELIST"

N=$(wc -l < "$FILELIST" || echo 0)
echo "[prep] Filelist entries: $N"
if [[ "$N" == "0" ]]; then
  echo "FATAL: no inputs found under $IN_DIR" >&2
  exit 3
fi
echo "[prep] Sample inputs:"
head -n 3 "$FILELIST" || true

# Escape EXTRA so it survives condor variable substitution and arrives as ONE argument

echo "[submit] Submitting $N jobs..."
condor_submit reco.condor \
  -append "queuefile=$(pwd)/$FILELIST" \
  -append "outdir=$OUT_DIR" \
  -append "compactxml=$COMPACT_XML" \
  -append "fitter=$FITTER" \
  -append "usemat=$GF_USE_MAT" \
  -append "stage=$STAGE" \
  -append "fitout=$FIT_OUT" \
  -append "k4rel=$K4REL"
