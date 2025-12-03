#!/usr/bin/env bash
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
