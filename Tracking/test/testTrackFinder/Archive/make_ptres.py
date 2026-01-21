#!/usr/bin/env python3
import argparse, math, csv
import numpy as np
import ROOT
import matplotlib.pyplot as plt

def branch_names(t):
    lb = t.GetListOfBranches()
    return [lb.At(i).GetName() for i in range(lb.GetEntries())]

def has_branch(t, name):
    return name in branch_names(t)

def robust_sigma(vals):
    a = np.asarray(vals, float)
    a = a[np.isfinite(a)]
    if a.size < 3: return float("nan")
    p16, p84 = np.percentile(a, [16, 84])
    return 0.5*(p84-p16)

def truth_pt_from_MCParticles(t):
    if not has_branch(t, "MCParticles"):
        return None
    n = t.GetEntries()
    out = np.full(n, np.nan, float)
    for i in range(n):
        t.GetEntry(i)
        try:
            coll = t.MCParticles
        except Exception:
            continue
        pts = []
        for p in coll:
            try:
                if abs(int(p.PDG)) != 13:
                    continue
                px = float(p.momentum.x)
                py = float(p.momentum.y)
                pts.append(math.hypot(px, py))
            except Exception:
                pass
        if pts:
            out[i] = max(pts)
    return out

def reco_pt_from_trackstates(t, coll_name, Bz, allow_any=False):
    br = f"_{coll_name}_trackStates"
    if not has_branch(t, br):
        return None
    ATIP = int(ROOT.edm4hep.TrackState.AtIP)
    n = t.GetEntries()
    out = np.full(n, np.nan, float)
    k = 0.0003 * float(Bz)
    for i in range(n):
        t.GetEntry(i)
        try:
            sts = getattr(t, br)
        except Exception:
            continue
        pts = []
        for st in sts:
            try:
                loc = int(st.location)
                omg = float(st.omega)
                if omg == 0.0 or not math.isfinite(omg):
                    continue
                if (loc == ATIP) or allow_any:
                    pts.append(k / abs(omg))
            except Exception:
                pass
        if pts:
            out[i] = max(pts)
    return out

def reco_pt_fallback_from_tracks(t, coll_name):
    # Most EDM4hep track RNTuples don’t expose pt/px/py directly; keep as placeholder.
    return None

def choose_reco_collection(t, fitter):
    prefer_map = {
        "genfit2":   ["GenFitTracks", "CDCHTracks"],
        "simple":    ["SimpleFitTracks", "SimpleTracks"],
        "threepoint":["ThreePointTracks", "Tracks", "CDCHTracks"],
        "auto":      ["GenFitTracks", "SimpleFitTracks", "ThreePointTracks",
                      "SimpleTracks", "Tracks", "CDCHTracks"],
    }
    names = branch_names(t)
    # prefer ones that have underscore trackStates
    for c in prefer_map[fitter]:
        if f"_{c}_trackStates" in names:
            return c, True
    # then any collection by top-level name (rarely useful without trackStates)
    for c in prefer_map[fitter]:
        if c in names:
            return c, False
    return None, False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--tree", default="events")
    ap.add_argument("--fitter", choices=["genfit2","simple","threepoint","auto"], default="auto")
    ap.add_argument("--Bz", type=float, default=2.0, help="Tesla (used when deriving pT from omega)")
    ap.add_argument("--allow-any-location", action="store_true",
                    help="Use any TrackState location, not just AtIP")
    ap.add_argument("--emin", type=float, default=0.5)
    ap.add_argument("--emax", type=float, default=20.0)
    ap.add_argument("--nbins", type=int, default=10)
    ap.add_argument("--out", default="")
    ap.add_argument("--csv", default="")
    args = ap.parse_args()

    f = ROOT.TFile.Open(args.input)
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open {args.input}")
    t = f.Get(args.tree)
    if not t:
        raise RuntimeError(f"Tree '{args.tree}' not found")

    reco_coll, has_states = choose_reco_collection(t, args.fitter)
    if not reco_coll:
        sample = branch_names(t)[:40]
        raise RuntimeError(f"No suitable reco collection found. Sample branches: {sample}")
    print(f"[info] using reco collection: {reco_coll} (trackStates={has_states})")

    tpt = truth_pt_from_MCParticles(t)
    if tpt is None:
        raise RuntimeError("Missing 'MCParticles' collection in the file; can't get truth pT.")

    if has_states:
        rpt = reco_pt_from_trackstates(t, reco_coll, args.Bz, allow_any=args.allow_any_location)
    else:
        rpt = reco_pt_fallback_from_tracks(t, reco_coll)

    if rpt is None:
        raise RuntimeError("Could not derive reco pT from this collection.")

    valid = np.isfinite(tpt) & np.isfinite(rpt) & (tpt > 0)
    print(f"[info] valid pairs: {int(valid.sum())}/{len(tpt)}")

    rel = (rpt[valid] - tpt[valid]) / tpt[valid]
    edges = np.linspace(args.emin, args.emax, args.nbins + 1)
    centers = 0.5 * (edges[:-1] + edges[1:])
    sig = np.full_like(centers, np.nan, float)
    cnt = np.zeros_like(centers, int)

    for i in range(len(centers)):
        m = (tpt[valid] >= edges[i]) & (tpt[valid] < edges[i+1])
        cnt[i] = int(m.sum())
        sig[i] = robust_sigma(rel[m]) if cnt[i] >= 8 else float("nan")

    tag = args.fitter
    png = args.out or f"pt_resolution_{tag}.png"
    csvp = args.csv or f"pt_resolution_{tag}.csv"

    with open(csvp, "w", newline="") as cf:
        w = csv.writer(cf)
        w.writerow(["pt_center_GeV", "n_events", "sigma_pt_over_pt"])
        for c, n, s in zip(centers, cnt, sig):
            w.writerow([f"{c:.6g}", n, "" if not math.isfinite(s) else f"{s:.6g}"])
    print(f"[info] wrote {csvp}")

    plt.figure(figsize=(6,4))
    plt.plot(centers, sig, marker="o", linestyle="-")
    plt.xlabel(r"truth $p_T$ [GeV]")
    plt.ylabel(r"$\sigma(p_T)/p_T$")
    ttl = f"pT resolution ({tag}, {reco_coll})"
    if args.allow_any_location: ttl += " [any location]"
    plt.title(ttl)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(png, dpi=150)
    print(f"[info] wrote {png}")
    f.Close()

if __name__ == "__main__":
    main()
