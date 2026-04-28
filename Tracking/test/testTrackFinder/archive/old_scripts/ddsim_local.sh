#!/usr/bin/env bash
set -euo pipefail

# --- USER KNOBS ---
COMPACT_XML="${COMPACT_XML:-/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml}"   # same compact used by ddsim
NEVENTS="${NEVENTS:-500}"                             # events per (pT,eta) point
OUTDIR="${OUTDIR:-gun_samples}"                       # where to write ddsim ROOTs
PARTICLE="${PARTICLE:-mu-}"                           # gun particle
SEED_BASE="${SEED_BASE:-12345}"

# pT grid (log-spaced 0.01 → 200 GeV) — adjust count as needed
PT_LIST=$(python3 - <<'PY'
import numpy as np
pts = np.logspace(np.log10(0.01), np.log10(200.0), 5)  # 5 points
print(" ".join(f"{x:.6g}" for x in pts))
PY
)

# η points across detector acceptance (edit as you like)
ETA_LIST="0.0 0.5 1.0 2.0"

mkdir -p "$OUTDIR"

# small python to convert (pT,eta)->(theta,energy)
pteta_to_thetaE () {
python3 - "$1" "$2" <<'PY'
import math,sys
pt=float(sys.argv[1]); eta=float(sys.argv[2])
theta = 2.0*math.atan(math.exp(-eta))
p     = pt*math.cosh(eta)  # GeV/c
E     = math.sqrt(p*p + 0.105658*0.105658)  # mu mass ~105.7 MeV (small but safe)
print(f"{theta} {E}")
PY
}

# loop over eta and pT
i=0
for eta in $ETA_LIST; do
  for pt in $PT_LIST; do
    i=$((i+1))
    read theta energy <<<"$(pteta_to_thetaE "$pt" "$eta")"
    out="${OUTDIR}/gun_eta$(printf "%+.2f" "$eta")_pt$(printf "%.5g" "$pt").root"
    seed=$((SEED_BASE + i))

    echo "[ddsim] eta=${eta}  pT=${pt} GeV  theta=${theta} rad  E~${energy} GeV -> $out"

    ddsim \
      --compactFile="${COMPACT_XML}" \
      --enableGun \
      --gun.particle "${PARTICLE}" \
      --gun.energy   "${energy}" \
      --gun.thetaMin "${theta}" --gun.thetaMax "${theta}" \
      --gun.phiMin 0 --gun.phiMax 360 \
      --gun.position "0 0 0" \
      --gun.distribution uniform \
      --random.seed ${seed} \
      --numberOfEvents 500 \
      --outputFile "${out}"
  done
done

echo "[ddsim] Done. Files in ${OUTDIR}"
