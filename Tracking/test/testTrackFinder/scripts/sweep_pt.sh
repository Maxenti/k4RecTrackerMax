#!/usr/bin/env bash

#DOC:
#Summary: Legacy/secondary local pT-sweep helper that runs local_chain.sh over a small hand-coded eta≈0 gun-sample pT list.
#Status: secondary
#Usage:
#  bash scripts/sweep_pt.sh
#Examples:
#  cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder
#  bash scripts/sweep_pt.sh
#Inputs: Hand-edited INPUT_DIR, OUTPUT_DIR, MODEL, XML, and PTS array; input gun ROOT files matching either gun_eta+0.00_E<PT>GeV.root or gun_eta+0.00_E<PT*1000>MeV.root.
#Outputs: Reco ROOT files named reco_eta+0.00_pT<PT>GeV.root under OUTPUT_DIR.
#Collections: Does not inspect collections directly; local_chain.sh normally runs DCHCollection -> DCH digi -> GGTF tracks -> GenFitTracks.
#Connects-To: steering/local_chain.sh, steering/runDCHTestTrackFinder.py, scripts/submit_reco.sh, scripts/reco_job.sh, scripts/analyze_pt_resolution_grid.py
#Arguments:
#  INPUT_DIR: directory containing local or EOS-mounted gun ROOT files.
#  OUTPUT_DIR: output directory for local reco ROOT files.
#  MODEL: GGTF ONNX model path passed to local_chain.sh.
#  XML: compact DD4hep XML path passed to local_chain.sh.
#  PTS: hard-coded bash array of pT values in GeV to scan.
#  STAGE: exported as fit for local_chain.sh.
#  FITTER: exported as genfit2 for local_chain.sh.
#  GF_SEED_PT_MIN, GF_SEED_PT_MAX, GF_SEED_P_MIN: GenFit seed momentum bounds used for this local sweep.
#  GGTF_LOG, PRODUCE_3DHITS, MAX_HITS, TBETA, TD, WIRE_GATE_MM, MAX_3D_PER_EVT, MAX_3D_PER_TRK: GGTF/debug controls passed through the environment when recognized by local_chain.sh/steering.
#  GF_HIT_SIGMA_XY, GF_HIT_SIGMA_Z, GF_MIN_GROUP, GF_USE_FALLBACK, GF_FALLBACK_EPS_CM, GF_FALLBACK_MINPTS, GF_RETRY, GF_RETRY_MEAS_INFL, GF_RETRY_SEED_POS, GF_RETRY_SEED_MOM, GF_MAX_MEAS_PER_GROUP: older/fallback fitter tuning knobs retained for historical local tests.
#Notes:
#  This is not the authoritative production campaign submission path. Production reco should use scripts/submit_reco.sh -> configs/condor/reco.condor -> scripts/reco_job.sh.
#  This helper is still useful for quick local smoke tests over a few pT points when debugging steering or fitter behavior before Condor submission.
#  Several exported knobs appear to come from an older local-chain/fitter era and may be ignored by the current runDCHTestTrackFinder.py interface.
#  The input filename pattern is older and energy-like, not the newer gun_eta<eta>_pt<pt>.root naming used by the DDSim Condor pipeline.
#  If this script is kept, treat it as a small manual diagnostic wrapper; do not rely on it for CF-vs-W closeout production.
#  Before using it, verify that ./local_chain.sh resolves correctly from the working directory; in the current layout the maintained wrapper may live under steering/local_chain.sh.
#Tags: secondary, local-test, pt-sweep, legacy-helper, reco, ggtf, genfit2, smoke-test
#DOC_END
set -euo pipefail

# --- EDIT THESE ---
INPUT_DIR="/eos/user/c/cglenn/gun_samples"
OUTPUT_DIR="/eos/user/c/cglenn/reco_samples2"
MODEL="/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/model.onnx"
XML="/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml"

# pT grid in GeV (true pT ~= total p for eta~0)
PTS=(6.6261 11.192)

mkdir -p "${OUTPUT_DIR}"

for PT in "${PTS[@]}"; do
  # Example gun filename pattern — edit to match your files
  # Try both “GeV” and “MeV” patterns (best-effort)
  IN_GEV="${INPUT_DIR}/gun_eta+0.00_E${PT}GeV.root"
  IN_MEV="${INPUT_DIR}/gun_eta+0.00_E$(awk -v p="${PT}" 'BEGIN{printf("%.0f", p*1000)}')MeV.root"
  if [[ -f "$IN_GEV" ]]; then INPUT="$IN_GEV"
  elif [[ -f "$IN_MEV" ]]; then INPUT="$IN_MEV"
  else
    echo "[skip] No input for pT=${PT} GeV at ${IN_GEV} or ${IN_MEV}"
    continue
  fi

  OUT="${OUTPUT_DIR}/reco_eta+0.00_pT${PT}GeV.root"
  echo "[run] pT=${PT} GeV -> ${OUT}"

  STAGE=fit \
  FITTER=genfit2 \
  GF_SEED_PT_MIN=0.2 GF_SEED_PT_MAX=200.0 GF_SEED_P_MIN=0.8 \
  GGTF_LOG=INFO PRODUCE_3DHITS=1 MAX_HITS=100000 \
  TBETA=0.60 TD=0.35 \
  WIRE_GATE_MM=10.0 \
  MAX_3D_PER_EVT=200000 MAX_3D_PER_TRK=20000 \
  GF_HIT_SIGMA_XY=0.8 GF_HIT_SIGMA_Z=6.0 \
  GF_MIN_GROUP=6 GF_USE_FALLBACK=1 GF_FALLBACK_EPS_CM=4 GF_FALLBACK_MINPTS=4 \
  GF_RETRY=1 GF_RETRY_MEAS_INFL=5 GF_RETRY_SEED_POS=5 GF_RETRY_SEED_MOM=5 \
  GF_MAX_MEAS_PER_GROUP=0 \
  ./local_chain.sh \
      "${INPUT}" "${OUT}" "${MODEL}" "${XML}" DCHCollection DCH_v2
done
