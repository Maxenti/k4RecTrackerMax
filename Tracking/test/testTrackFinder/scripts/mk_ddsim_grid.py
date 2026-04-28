#!/usr/bin/env python3


"""
DOC
Summary: Generate a JSONL pT–eta parameter grid for DDSim single-particle gun Condor production.
Status: secondary
Usage:
  python3 scripts/mk_ddsim_grid.py --out params_ddsim.jsonl
  python3 scripts/mk_ddsim_grid.py --out params_ddsim.jsonl --pt-min 0.01 --pt-max 200 --pt-n 30 --etas "0.0,0.1,0.5,1.0,1.5,2.0" --nev 1000 --particle mu-
Examples:
  python3 scripts/mk_ddsim_grid.py \
    --out configs/params/params_ddsim_CF25_Au2p227matched.jsonl \
    --pt-min 0.01 \
    --pt-max 200.0 \
    --pt-n 30 \
    --etas "0.0,0.1,0.5,1.0,1.5,2.0" \
    --nev 1000 \
    --particle mu- \
    --seed0 1000000
Inputs: pT range, number of pT points, comma-separated eta list, event count per grid point, particle name, theta-smearing setting, and base random seed.
Outputs: JSONL file with one DDSim job record per pT/eta point.
Collections: None; this is a job-parameter generation utility and does not read or write EDM4hep collections.
Connects-To: scripts/prepare_and_submit.sh, configs/condor/ddsim.condor, scripts/condor_ddsim.sh, scripts/make_filelist.sh
Arguments:
  --out: output JSONL parameter file; default params_ddsim.jsonl.
  --pt-min: minimum transverse momentum in GeV for logarithmic pT grid; default 0.01.
  --pt-max: maximum transverse momentum in GeV for logarithmic pT grid; default 200.0.
  --pt-n: number of logarithmically spaced pT points; default 30.
  --etas: comma-separated eta values; default "0.0, 0.05, 1.0, 1.5, 2.0".
  --nev: number of generated events per pT/eta point; default 1000.
  --particle: DDSim gun particle name; default mu-.
  --phi-uniform: record phi_uniform=true in each job record; enabled by default and recommended.
  --theta-smear: optional uniform |Δθ| half-width in radians around the exact theta(eta); default 0.0 disables smearing.
  --seed0: base random seed; each eta/pT point gets seed0 + 10000*ieta + ipt.
Notes:
  Each JSONL record contains pt, eta, p, theta, nev, particle, phi_uniform, theta_smear, seed, and job_id.
  Momentum magnitude is computed as p = pT*cosh(eta), and polar angle is computed as theta = 2*atan(exp(-eta)).
  The output is intended to be consumed by the DDSim Condor production pipeline, especially prepare_and_submit.sh, ddsim.condor, and condor_ddsim.sh.
  Keep the eta grid synchronized with make_filelist.sh and downstream reco/analysis expectations before launching a production campaign.
  Because pT spacing is logarithmic, pt-min must be positive and pt-n should be greater than one for normal production grids.
  This script defines upstream gun-sample coverage; changing it can invalidate direct comparisons unless reco and analysis are regenerated consistently.
Tags: secondary, ddsim, gun-production, parameter-grid, jsonl, eta-grid, pt-grid, condor
DOC_END
"""
import os, math, argparse, json

ap = argparse.ArgumentParser(description="Generate pT-eta grid file for ddsim condor")
ap.add_argument("--out", default="params_ddsim.jsonl", help="Output JSONL of job params")
ap.add_argument("--pt-min", type=float, default=0.01, help="min pT [GeV]")
ap.add_argument("--pt-max", type=float, default=200.0, help="max pT [GeV]")
ap.add_argument("--pt-n",   type=int,   default=30,    help="number of pT points (logspace)")
ap.add_argument("--etas",   default="0.0, 0.05, 1.0, 1.5, 2.0",
                help="comma list of eta values")
ap.add_argument("--nev",    type=int,   default=1000,  help="events per point")
ap.add_argument("--particle", default="mu-", help="gun particle PDG name")
ap.add_argument("--phi-uniform", action="store_true", default=True,
                help="sample phi uniformly 0..2pi (recommended)")
ap.add_argument("--theta-smear", type=float, default=0.0,
                help="optional uniform |Δθ| [rad] around exact theta(eta). 0 disables.")
ap.add_argument("--seed0", type=int, default=1_000_000, help="base RNG seed")

args = ap.parse_args()

def logspace(a, b, n):
    la, lb = math.log10(a), math.log10(b)
    return [10**(la + i*(lb-la)/(n-1)) for i in range(n)]

etas = [float(x) for x in args.etas.split(",") if x.strip()!=""]
pts  = logspace(args.pt_min, args.pt_max, args.pt_n)

with open(args.out, "w") as f:
    jid = 0
    for ie, eta in enumerate(etas):
        for ip, pt in enumerate(pts):
            # p = pT * cosh(eta)
            p = pt * math.cosh(eta)
            theta = 2*math.atan(math.exp(-eta))  # rad
            # unique seed
            seed = args.seed0 + 10_000*ie + ip
            rec = {
                "pt": pt,
                "eta": eta,
                "p": p,
                "theta": theta,
                "nev": args.nev,
                "particle": args.particle,
                "phi_uniform": bool(args.phi_uniform),
                "theta_smear": args.theta_smear,
                "seed": seed,
                "job_id": jid,
            }
            f.write(json.dumps(rec) + "\n")
            jid += 1

print(f"Wrote {jid} lines to {args.out}")
