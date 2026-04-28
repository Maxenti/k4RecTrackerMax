# DOC:
# Summary: Authoritative reco campaign submission wrapper that builds the gun-sample input file list and submits one Condor reco job per input ROOT file.
# Status: authoritative
# Usage:
#   bash scripts/submit_reco.sh
#   IN_DIR=/eos/.../gun_samples/VARIANT OUT_DIR=/eos/.../reco_samples/VARIANT COMPACT_XML=/eos/.../VARIANT.xml TGEOFILE=/eos/.../VARIANT.root bash scripts/submit_reco.sh
# Examples:
#   IN_DIR=/eos/user/c/cglenn/gun_samples/1_29_2026/100umCF_0.313474umAu \
#   OUT_DIR=/eos/user/c/cglenn/reco_samples2/1_29_2026/100umCF_0.313474umAu \
#   COMPACT_XML=/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03_100umCF_0.313474umAu.xml \
#   TGEOFILE=/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03_100umCF_0.313474umAu.root \
#   FITTER=genfit2 GF_USE_MAT=1 STAGE=fit FIT_OUT=auto K4REL=2026-04-22 \
#   bash scripts/submit_reco.sh
# Inputs: Gun-sample campaign directory with eta_* ROOT files, compact DD4hep XML, matching TGeo ROOT geometry for material-aware GenFit, runtime.tgz in the Condor transfer context, reco.condor, reco_job.sh, and make_filelist.sh.
# Outputs: scripts/filelist.txt containing XRootD input paths, HTCondor reco jobs, logs under scripts/logs/reco, and final reco ROOT outputs under OUT_DIR/<eta_dir>/reco_<input>.root.
# Collections: Does not read collections directly; submitted jobs normally run DCHCollection -> DCHDigi2Collection/DCH_DigiCollection -> CDCHTracks -> GenFitTracks through steering/runDCHTestTrackFinder.py.
# Connects-To: scripts/make_filelist.sh, configs/condor/reco.condor, scripts/reco_job.sh, scripts/make_runtime.sh, steering/runDCHTestTrackFinder.py, scripts/analyze_job.sh
# Arguments:
#   IN_DIR: EOS/local base directory containing DDSim gun samples organized by eta; default is a hard-coded campaign path.
#   OUT_DIR: EOS output directory base for reco products; default is a hard-coded campaign path.
#   COMPACT_XML: compact DD4hep XML detector/material variant passed to reco_job.sh.
#   TGEOFILE: TGeo ROOT geometry passed to reco_job.sh when material-aware GenFit is enabled.
#   FITTER: fitter mode for steering; default genfit2.
#   FIT_OUT: fitted output collection or auto; default auto maps genfit2 to GenFitTracks.
#   GF_USE_MAT: material-effects toggle passed to reco_job.sh; default 1.
#   STAGE: cumulative reco stage, normally digi, ggtf, or fit; default fit.
#   K4REL: Key4HEP nightly release used inside worker jobs; default 2026-04-22.
#   EXTRA: currently retained for compatibility but not passed through this Condor path.
# Notes:
#   This is the authoritative high-level entry point for the maintained Condor reco pipeline.
#   Run scripts/make_runtime.sh before submitting if k4RecTracker, GenFit2, steering, or the ONNX model changed.
#   The script cd's into scripts/, expects reco.condor and make_filelist.sh there, and writes filelist.txt in that directory.
#   The input list is built from IN_DIR by make_filelist.sh, so its internal eta list must match the gun campaign coverage.
#   For CF-vs-W or other material comparisons, COMPACT_XML and TGEOFILE must match the same detector/material variant while all non-geometry reco knobs remain fixed.
#   The submitted worker jobs are idempotent at the expected EOS output path; stale outputs must be removed manually before rerunning changed configurations.
#   Check the printed sample inputs and final job count before trusting a large submission.
# Tags: authoritative, reco, condor, submission, eos, xrootd, dch, ggtf, genfit2, key4hep
# DOC_END

#!/usr/bin/env bash
set -euo pipefail

# -------- EDIT/OVERRIDE VIA ENV --------
IN_DIR="${IN_DIR:-/eos/user/c/cglenn/gun_samples/1_29_2026/100umCF_0.313474umAu}"
OUT_DIR="${OUT_DIR:-/eos/user/c/cglenn/reco_samples2/1_29_2026/100umCF_0.313474umAu}"
COMPACT_XML="${COMPACT_XML:-/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03_100umCF_0.313474umAu.xml}"

FITTER="${FITTER:-genfit2}"             # genfit2 | simple | threepoint
FIT_OUT="${FIT_OUT:-auto}"              # auto | <collection name>
GF_USE_MAT="${GF_USE_MAT:-1}"           # 1|0
STAGE="${STAGE:-fit}"                   # digi|ggtf|fit
EXTRA="${EXTRA:---fitterLog INFO}"      # any additional flags (currently unused by condor path)

# Key4hep nightly to use inside jobs
K4REL="${K4REL:-2026-04-22}"
TGEOFILE="${TGEOFILE:-/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03_100umCF_0.313474umAu.root}"

# --------------------------------------

cd "$(dirname "$0")"   # scripts/
mkdir -p logs
mkdir -p logs/reco

[[ -s reco.condor ]] || { echo "FATAL: reco.condor missing" >&2; exit 2; }
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

echo "[submit] Using:"
echo "  IN_DIR=$IN_DIR"
echo "  OUT_DIR=$OUT_DIR"
echo "  COMPACT_XML=$COMPACT_XML"
echo "  TGEOFILE=$TGEOFILE"
echo "  FITTER=$FITTER"
echo "  FIT_OUT=$FIT_OUT"
echo "  GF_USE_MAT=$GF_USE_MAT"
echo "  STAGE=$STAGE"
echo "  K4REL=$K4REL"

echo "[submit] Submitting $N jobs..."
condor_submit reco.condor \
  -append "queuefile=$(pwd)/$FILELIST" \
  -append "outdir=$OUT_DIR" \
  -append "compactxml=$COMPACT_XML" \
  -append "fitter=$FITTER" \
  -append "usemat=$GF_USE_MAT" \
  -append "stage=$STAGE" \
  -append "fitout=$FIT_OUT" \
  -append "k4rel=$K4REL" \
  -append "tgeofile=$TGEOFILE"