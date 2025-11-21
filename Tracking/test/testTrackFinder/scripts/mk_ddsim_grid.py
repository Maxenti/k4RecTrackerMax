#!/usr/bin/env python3
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
