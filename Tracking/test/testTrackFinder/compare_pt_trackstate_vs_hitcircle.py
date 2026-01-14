#!/usr/bin/env python3
import argparse, math, csv
import ROOT
ROOT.gROOT.SetBatch(True)

def leaf(tree, name):
    return tree.GetLeaf(name)

def resolve_ts_prefix(tree, coll):
    cands = [
        f"{coll}.trackStates.", f"{coll}.TrackStates.",
        f"{coll}.trackStates_AtIP.", f"{coll}.TrackStates_AtIP.",
        f"_{coll}_trackStates.", f"_{coll}_TrackStates.",
    ]
    for p in cands:
        if leaf(tree, p + "phi"):
            return p
    leaves = tree.GetListOfLeaves()
    for obj in leaves:
        nm = obj.GetName()
        if coll in nm and nm.endswith(".phi"):
            return nm[:-len("phi")]
    return None

def get_hits_xy(tree, ev, coll):
    lx = leaf(tree, f"{coll}.position.x")
    ly = leaf(tree, f"{coll}.position.y")
    lz = leaf(tree, f"{coll}.position.z")
    if not (lx and ly and lz):
        return None
    tree.GetEntry(ev)
    n = int(lx.GetNdata())
    xs = [float(lx.GetValue(i)) for i in range(n)]
    ys = [float(ly.GetValue(i)) for i in range(n)]
    zs = [float(lz.GetValue(i)) for i in range(n)]
    rs = [math.hypot(xs[i], ys[i]) for i in range(n)]
    return xs, ys, zs, rs

def circle_fit_kasa(xs, ys):
    # Algebraic circle fit (Kåsa). Returns (xc, yc, R) in same units as x,y.
    # Good enough for diagnostics; robust methods exist but this is fast.
    n = len(xs)
    if n < 6:
        return None
    sum_x = sum(xs); sum_y = sum(ys)
    sum_x2 = sum(x*x for x in xs); sum_y2 = sum(y*y for y in ys)
    sum_xy = sum(xs[i]*ys[i] for i in range(n))
    sum_x3 = sum(xs[i]**3 for i in range(n))
    sum_y3 = sum(ys[i]**3 for i in range(n))
    sum_x1y2 = sum(xs[i]*(ys[i]**2) for i in range(n))
    sum_x2y1 = sum((xs[i]**2)*ys[i] for i in range(n))

    C = n*sum_x2 - sum_x**2
    D = n*sum_xy - sum_x*sum_y
    E = n*sum_x3 + n*sum_x1y2 - (sum_x2 + sum_y2)*sum_x
    G = n*sum_y2 - sum_y**2
    H = n*sum_x2y1 + n*sum_y3 - (sum_x2 + sum_y2)*sum_y

    denom = 2*(C*G - D*D)
    if abs(denom) < 1e-12:
        return None

    xc = (E*G - H*D) / denom
    yc = (C*H - D*E) / denom

    R = sum(math.hypot(xs[i]-xc, ys[i]-yc) for i in range(n))/n
    return xc, yc, R

def get_trackstate_pt(tree, ev, track_coll):
    pref = resolve_ts_prefix(tree, track_coll)
    if not pref:
        return None
    tree.GetEntry(ev)
    ltime = leaf(tree, pref+"time")
    lomg  = leaf(tree, pref+"omega")
    if not ltime:
        return None
    n = int(ltime.GetNdata())
    if n <= 0:
        return None
    pt = float(ltime.GetValue(0))
    omg = float(lomg.GetValue(0)) if lomg else float("nan")
    return pt, omg

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--events", required=True, help="Comma-separated event indices")
    ap.add_argument("--hits", default="GGTF_3DHits")
    ap.add_argument("--track", default="GenFitTracks")
    ap.add_argument("--Bz", type=float, default=2.0, help="Tesla (for hit-circle pT)")
    ap.add_argument("--out", default="pt_diagnostic.csv")
    args = ap.parse_args()

    f = ROOT.TFile.Open(args.input)
    tree = f.Get("events")

    evs = [int(x.strip()) for x in args.events.split(",") if x.strip()]
    rows = []

    for ev in evs:
        hits = get_hits_xy(tree, ev, args.hits)
        ts = get_trackstate_pt(tree, ev, args.track)

        if hits:
            xs, ys, zs, rs = hits
            rspan = max(rs)-min(rs) if rs else 0.0
            zspan = max(zs)-min(zs) if zs else 0.0
            circ = circle_fit_kasa(xs, ys)
        else:
            rspan = zspan = float("nan")
            circ = None

        if circ:
            xc, yc, Rmm = circ
            # pT[GeV] ≈ 0.3 * B[T] * R[m]
            pt_hit = 0.3 * abs(args.Bz) * (Rmm/1000.0)
        else:
            pt_hit = float("nan")

        if ts:
            pt_time, omg = ts
        else:
            pt_time, omg = float("nan"), float("nan")

        print(f"event {ev}: pT(time)={pt_time:.3f}  omega={omg:.3e}  "
              f"pT(hitCircle)={pt_hit:.3f}  rspan={rspan:.1f}mm zspan={zspan:.1f}mm")

        rows.append([ev, pt_time, omg, pt_hit, rspan, zspan])

    with open(args.out, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["event","pt_time","omega","pt_hitCircle","rspan_mm","zspan_mm"])
        w.writerows(rows)

    f.Close()
    print(f"[info] wrote {args.out}")

if __name__ == "__main__":
    main()
