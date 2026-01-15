#!/usr/bin/env python3
"""
compare_pt_trackstate_vs_hitcircle.py

Compare per-event pT from GenFit TrackState (time/omega) to a hit-based XY circle estimate,
and add curvature observability diagnostics (phiSpan, chord, sagitta, circle condition, etc.).

This version fixes the "nullptr result where temporary expected" ROOT/PyROOT matrix issue by:
  - doing Kåsa circle fit using centered/scaled coordinates
  - solving the 3x3 normal equations with explicit inversion (TMatrixD.Invert) + SVD fallback
  - never using "A*B" temporaries that sometimes yield nullptr in PyROOT

It also makes phiSpan more meaningful by providing two variants:
  - phiSpan_meanCenter: angles about mean(x,y)
  - phiSpan_circleCenter: angles about fitted circle center (if circle fit succeeded), else NaN

Usage:
  python3 compare_pt_trackstate_vs_hitcircle.py --input reco.root --events 718,838,302 --Bz 2.0
"""

import argparse
import csv
import math
import ROOT
ROOT.gROOT.SetBatch(True)


# -----------------------------
# leaf resolution helpers
# -----------------------------
def _find_leaf(tree, name):
    return tree.GetLeaf(name)


def resolve_ts_prefix(tree, coll_name):
    candidates = [
        f"{coll_name}.trackStates.",
        f"{coll_name}.TrackStates.",
        f"{coll_name}.trackStates_AtIP.",
        f"{coll_name}.TrackStates_AtIP.",
        f"_{coll_name}_trackStates.",
        f"_{coll_name}_TrackStates.",
    ]
    for pref in candidates:
        if _find_leaf(tree, pref + "phi"):
            return pref

    leaves = tree.GetListOfLeaves()
    if not leaves:
        return None
    for obj in leaves:
        nm = obj.GetName()
        if coll_name in nm and nm.endswith(".phi"):
            return nm[:-len("phi")]
    return None


def resolve_begin_end(tree, coll_name):
    pairs = [
        (f"{coll_name}.trackStates_begin", f"{coll_name}.trackStates_end"),
        (f"{coll_name}.TrackStates_begin", f"{coll_name}.TrackStates_end"),
    ]
    for b, e in pairs:
        if _find_leaf(tree, b) and _find_leaf(tree, e):
            return b, e

    leaves = tree.GetListOfLeaves()
    if not leaves:
        return None, None

    bname = None
    ename = None
    for obj in leaves:
        nm = obj.GetName()
        if coll_name in nm and nm.endswith("trackStates_begin"):
            bname = nm
        if coll_name in nm and nm.endswith("trackStates_end"):
            ename = nm
        if coll_name in nm and nm.endswith("TrackStates_begin"):
            bname = nm
        if coll_name in nm and nm.endswith("TrackStates_end"):
            ename = nm

    return bname, ename


# -----------------------------
# math helpers
# -----------------------------
def _smallest_angular_span(phi_list):
    """
    Compute angular span robustly (order-independent):
      - sort angles
      - find maximum gap on circle
      - span = 2pi - max_gap
    Returns span in [0, 2pi].
    """
    if len(phi_list) < 2:
        return 0.0
    ph = sorted(phi_list)
    gaps = []
    for i in range(1, len(ph)):
        gaps.append(ph[i] - ph[i - 1])
    gaps.append((ph[0] + 2.0 * math.pi) - ph[-1])
    max_gap = max(gaps) if gaps else 2.0 * math.pi
    span = 2.0 * math.pi - max_gap
    if span < 0:
        span = 0.0
    if span > 2.0 * math.pi:
        span = 2.0 * math.pi
    return float(span)


def _dist_point_to_line_xy(x, y, x0, y0, x1, y1):
    """Perpendicular distance from point (x,y) to the infinite line through (x0,y0)-(x1,y1)."""
    dx = x1 - x0
    dy = y1 - y0
    denom = math.hypot(dx, dy)
    if denom <= 0:
        return float("nan")
    num = abs(dy * x - dx * y + x1 * y0 - y1 * x0)
    return num / denom


def _circle_fit_kasa_xy_centered(xy):
    """
    Algebraic circle fit (Kåsa) using centered/scaled coordinates to avoid singularities and
    improve conditioning, implemented without PyROOT matrix temporaries.

    Solve least squares for:
        x^2 + y^2 + D x + E y + F = 0
    by normal equations on [x, y, 1] * [D,E,F]^T = -(x^2+y^2)

    Returns:
      xc, yc, R, ok, cond

    - Coordinates are centered: x' = (x - mx)/s, y' = (y - my)/s
      where s is RMS radius (or 1 if degenerate).
    - Circle parameters are solved in primed coords then transformed back.
    - cond is estimated from SVD singular values of the 3x3 normal matrix (in primed coords).
    """
    n = len(xy)
    if n < 3:
        return 0.0, 0.0, float("inf"), False, float("inf")

    xs = [p[0] for p in xy]
    ys = [p[1] for p in xy]
    mx = sum(xs) / n
    my = sum(ys) / n

    # scale ~ RMS radius about mean
    rr = [(x - mx) * (x - mx) + (y - my) * (y - my) for x, y in zip(xs, ys)]
    rms = math.sqrt(sum(rr) / n) if n > 0 else 0.0
    s = rms if (math.isfinite(rms) and rms > 0) else 1.0

    # Accumulate sums in primed coordinates for ATA and ATB
    Sx = Sy = Sxx = Syy = Sxy = 0.0
    Sb = Sxb = Syb = 0.0

    for (x, y) in xy:
        xp = (x - mx) / s
        yp = (y - my) / s
        xx = xp * xp
        yy = yp * yp
        b = -(xx + yy)

        Sx += xp
        Sy += yp
        Sxx += xx
        Syy += yy
        Sxy += xp * yp

        Sb += b
        Sxb += xp * b
        Syb += yp * b

    # Normal matrix M and vector v in primed coords
    M = ROOT.TMatrixD(3, 3)
    M[0][0] = Sxx; M[0][1] = Sxy; M[0][2] = Sx
    M[1][0] = Sxy; M[1][1] = Syy; M[1][2] = Sy
    M[2][0] = Sx;  M[2][1] = Sy;  M[2][2] = float(n)

    v = ROOT.TVectorD(3)
    v[0] = Sxb
    v[1] = Syb
    v[2] = Sb

    def _extract(sol):
        Dp = float(sol[0]); Ep = float(sol[1]); Fp = float(sol[2])
        xcp = -Dp / 2.0
        ycp = -Ep / 2.0
        R2p = xcp * xcp + ycp * ycp - Fp
        if not (math.isfinite(R2p) and R2p > 0):
            return 0.0, 0.0, float("inf"), False
        Rp = math.sqrt(R2p)
        if not (math.isfinite(Rp) and Rp > 0):
            return 0.0, 0.0, float("inf"), False

        # transform back: x = mx + s * x'
        xc = mx + s * xcp
        yc = my + s * ycp
        R = s * Rp
        if not (math.isfinite(xc) and math.isfinite(yc) and math.isfinite(R) and R > 0):
            return 0.0, 0.0, float("inf"), False
        return xc, yc, R, True

    # Estimate cond from SVD singular values of M
    cond = float("inf")
    try:
        svd0 = ROOT.TDecompSVD(M)
        sig = svd0.GetSig()
        vals = [float(sig[i]) for i in range(sig.GetNrows())]
        vals = [x for x in vals if math.isfinite(x) and x > 0]
        if len(vals) >= 2:
            cond = max(vals) / min(vals)
    except Exception:
        cond = float("inf")

    # First try invert (stable enough for 3x3 in most cases), then SVD if needed.
    try:
        Minv = ROOT.TMatrixD(M)  # copy
        det = ROOT.Double(0.0)
        Minv.Invert(det)
        if math.isfinite(float(det)) and abs(float(det)) > 0:
            sol = ROOT.TVectorD(3)
            # sol = Minv * v  (manual multiply to avoid temporaries)
            for i in range(3):
                sol[i] = Minv[i][0] * v[0] + Minv[i][1] * v[1] + Minv[i][2] * v[2]
            xc, yc, R, ok = _extract(sol)
            if ok:
                return xc, yc, R, True, cond
    except Exception:
        pass

    # SVD fallback solve
    try:
        svd = ROOT.TDecompSVD(M)
        ok_svd = ROOT.Bool_t(True)
        sol = svd.Solve(v, ok_svd)
        if bool(ok_svd):
            xc, yc, R, ok = _extract(sol)
            if ok:
                # update cond from this svd if possible
                try:
                    sig = svd.GetSig()
                    vals = [float(sig[i]) for i in range(sig.GetNrows())]
                    vals = [x for x in vals if math.isfinite(x) and x > 0]
                    if len(vals) >= 2:
                        cond = max(vals) / min(vals)
                except Exception:
                    pass
                return xc, yc, R, True, cond
        return 0.0, 0.0, float("inf"), False, cond
    except Exception:
        return 0.0, 0.0, float("inf"), False, cond


# -----------------------------
# I/O: load hits + trackstate
# -----------------------------
def load_hits_xyz(tree, ev, coll="GGTF_3DHits"):
    x = _find_leaf(tree, f"{coll}.position.x")
    y = _find_leaf(tree, f"{coll}.position.y")
    z = _find_leaf(tree, f"{coll}.position.z")
    if not (x and y and z):
        raise RuntimeError(f"Missing hit leaves for '{coll}': need {coll}.position.(x,y,z)")

    tree.GetEntry(ev)
    n = int(x.GetNdata())
    pts = []
    for i in range(n):
        pts.append((float(x.GetValue(i)), float(y.GetValue(i)), float(z.GetValue(i))))
    return pts


def load_primary_track_pt(tree, ev, track_coll="GenFitTracks", expected_pt=None):
    """
    Returns dict with:
      n_states, pt_time, omega, pt_from_omega, phi, tanL, D0, Z0, assoc
    """
    prefix = resolve_ts_prefix(tree, track_coll)
    if not prefix:
        raise RuntimeError(f"Could not resolve TrackState prefix for '{track_coll}'")

    phi_leaf = _find_leaf(tree, prefix + "phi")
    time_leaf = _find_leaf(tree, prefix + "time")
    omg_leaf = _find_leaf(tree, prefix + "omega")
    tl_leaf = _find_leaf(tree, prefix + "tanLambda")
    d0_leaf = _find_leaf(tree, prefix + "D0")
    z0_leaf = _find_leaf(tree, prefix + "Z0")

    if not (phi_leaf and time_leaf):
        raise RuntimeError(f"Missing required TrackState leaves: '{prefix}phi' and/or '{prefix}time'")

    bname, ename = resolve_begin_end(tree, track_coll)
    beg_leaf = _find_leaf(tree, bname) if bname else None
    end_leaf = _find_leaf(tree, ename) if ename else None

    tree.GetEntry(ev)
    n_states = int(phi_leaf.GetNdata())
    if n_states <= 0:
        return {
            "n_states": 0,
            "pt_time": float("nan"),
            "omega": float("nan"),
            "pt_omega": float("nan"),
            "phi": float("nan"),
            "tanL": float("nan"),
            "D0": float("nan"),
            "Z0": float("nan"),
            "assoc": "noStates",
        }

    pts_time = [float(time_leaf.GetValue(i)) for i in range(n_states)]
    omegas = [float(omg_leaf.GetValue(i)) if omg_leaf else float("nan") for i in range(n_states)]

    def pt_from_omega(w):
        return (1.0 / abs(w)) if (math.isfinite(w) and abs(w) > 0) else float("nan")

    pts_omega = [pt_from_omega(w) for w in omegas]

    per_track = []
    if beg_leaf and end_leaf:
        n_tracks = int(beg_leaf.GetNdata())
        for ti in range(n_tracks):
            b = int(beg_leaf.GetValue(ti))
            e = int(end_leaf.GetValue(ti))
            if b < 0 or e < 0 or e <= b or b >= n_states:
                continue
            e = min(e, n_states)
            seg = [pts_time[k] for k in range(b, e) if math.isfinite(pts_time[k])]
            if not seg:
                continue
            seg.sort()
            pt_rep = seg[len(seg) // 2]
            per_track.append((ti, pt_rep, b, e))

    if per_track and expected_pt is not None:
        ti, pt_pick, b, e = min(per_track, key=lambda t: abs(t[1] - expected_pt))
        pick_state = b
        assoc = f"track={ti} states[{b}:{e})"
    elif per_track:
        per_track.sort(key=lambda t: t[1])
        ti, pt_pick, b, e = per_track[len(per_track) // 2]
        pick_state = b
        assoc = f"track={ti} states[{b}:{e})"
    else:
        finite = [p for p in pts_time if math.isfinite(p)]
        finite.sort()
        pt_pick = finite[len(finite) // 2] if finite else float("nan")
        pick_state = 0
        assoc = "flatStates(median)"

    i = max(0, min(int(pick_state), n_states - 1))
    phi = float(phi_leaf.GetValue(i))
    tl = float(tl_leaf.GetValue(i)) if tl_leaf else float("nan")
    d0 = float(d0_leaf.GetValue(i)) if d0_leaf else float("nan")
    z0 = float(z0_leaf.GetValue(i)) if z0_leaf else float("nan")
    omg = omegas[i]
    pt_o = pts_omega[i]
    pt_t = float(time_leaf.GetValue(i))

    return {
        "n_states": n_states,
        "pt_time": pt_t,
        "omega": omg,
        "pt_omega": pt_o,
        "phi": phi,
        "tanL": tl,
        "D0": d0,
        "Z0": z0,
        "assoc": assoc,
    }


# -----------------------------
# per-event diagnostics
# -----------------------------
def compute_hit_diagnostics(hits_xyz, sigma_xy_mm=0.5):
    """
    Returns dict with:
      nHits, rmin,rmax,rspan,zmin,zmax,zspan,rmean,
      phiSpan_meanCenter_rad/deg,
      chordMM,sagittaMM,sagittaSig,arcLenEstMM,
      hitCircleRmm, circleCond,
      phiSpan_circleCenter_rad/deg  (if circle fit ok; else NaN)
    """
    n = len(hits_xyz)
    if n == 0:
        return {
            "nHits": 0,
            "rmin": float("nan"), "rmax": float("nan"), "rspan": float("nan"),
            "zmin": float("nan"), "zmax": float("nan"), "zspan": float("nan"),
            "rmean": float("nan"),
            "phiSpan_mean_rad": float("nan"), "phiSpan_mean_deg": float("nan"),
            "chordMM": float("nan"), "sagittaMM": float("nan"), "sagittaSig": float("nan"),
            "arcLenEstMM": float("nan"),
            "hitCircleRmm": float("nan"),
            "circleCond": float("inf"),
            "phiSpan_circle_rad": float("nan"), "phiSpan_circle_deg": float("nan"),
        }

    xs = [p[0] for p in hits_xyz]
    ys = [p[1] for p in hits_xyz]
    zs = [p[2] for p in hits_xyz]
    rs = [math.hypot(x, y) for x, y in zip(xs, ys)]

    rmin, rmax = min(rs), max(rs)
    zmin, zmax = min(zs), max(zs)
    rspan = rmax - rmin
    zspan = zmax - zmin
    rmean = sum(rs) / len(rs)

    # mean-center span
    xc_mean = sum(xs) / len(xs)
    yc_mean = sum(ys) / len(ys)
    phis_mean = [math.atan2(y - yc_mean, x - xc_mean) for (x, y, _) in hits_xyz]
    phi_span_mean = _smallest_angular_span(phis_mean)
    phi_deg_mean = phi_span_mean * 180.0 / math.pi

    # endpoints around mean-center for chord
    pairs = list(zip(phis_mean, hits_xyz))
    pairs.sort(key=lambda t: t[0])
    p0 = pairs[0][1]
    p1 = pairs[-1][1]
    x0, y0 = p0[0], p0[1]
    x1, y1 = p1[0], p1[1]
    chord = math.hypot(x1 - x0, y1 - y0)

    # sagitta proxy: max distance to chord line
    dmax = 0.0
    for (x, y, _) in hits_xyz:
        d = _dist_point_to_line_xy(x, y, x0, y0, x1, y1)
        if math.isfinite(d) and d > dmax:
            dmax = d
    sagitta = dmax
    sag_sig = sagitta / sigma_xy_mm if (sigma_xy_mm > 0 and math.isfinite(sagitta)) else float("nan")

    arc_len_est = rmean * phi_span_mean if (math.isfinite(rmean) and math.isfinite(phi_span_mean)) else float("nan")

    # Circle fit (centered/scaled Kåsa)
    xy = [(p[0], p[1]) for p in hits_xyz]
    xc2, yc2, R, ok, circleCond = _circle_fit_kasa_xy_centered(xy)
    hitCircleR = R if ok else float("nan")

    # phi span about circle center (much more meaningful when curvature is measurable)
    if ok:
        phis_c = [math.atan2(y - yc2, x - xc2) for (x, y) in xy]
        phi_span_c = _smallest_angular_span(phis_c)
        phi_deg_c = phi_span_c * 180.0 / math.pi
    else:
        phi_span_c = float("nan")
        phi_deg_c = float("nan")

    return {
        "nHits": n,
        "rmin": rmin, "rmax": rmax, "rspan": rspan,
        "zmin": zmin, "zmax": zmax, "zspan": zspan,
        "rmean": rmean,
        "phiSpan_mean_rad": phi_span_mean, "phiSpan_mean_deg": phi_deg_mean,
        "chordMM": chord,
        "sagittaMM": sagitta,
        "sagittaSig": sag_sig,
        "arcLenEstMM": arc_len_est,
        "hitCircleRmm": hitCircleR,
        "circleCond": circleCond,
        "phiSpan_circle_rad": phi_span_c,
        "phiSpan_circle_deg": phi_deg_c,
    }


def pT_from_circle_radius_mm(R_mm, Bz_T):
    """pT [GeV] from circle radius in a uniform Bz."""
    if not (math.isfinite(R_mm) and R_mm > 0 and math.isfinite(Bz_T) and abs(Bz_T) > 0):
        return float("nan")
    R_m = R_mm / 1000.0
    return 0.3 * abs(Bz_T) * R_m


# -----------------------------
# main
# -----------------------------
def parse_events_list(s):
    s = s.strip()
    if not s:
        return []
    out = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


def main():
    ap = argparse.ArgumentParser(description="Compare GenFit pT vs hit-circle pT and add curvature observability diagnostics.")
    ap.add_argument("--input", required=True, help="Input EDM4hep ROOT file")
    ap.add_argument("--events", required=True, help="Comma-separated event indices, e.g. 718,838,96")
    ap.add_argument("--hits", default="GGTF_3DHits", help="Hits collection name (default: GGTF_3DHits)")
    ap.add_argument("--track", default="GenFitTracks", help="Track collection name (default: GenFitTracks)")
    ap.add_argument("--Bz", type=float, default=2.0, help="Bz field [T] (default: 2.0)")
    ap.add_argument("--expectedPt", type=float, default=None,
                    help="Optional: expected pT [GeV] (helps choose the primary track if multiple)")
    ap.add_argument("--sigmaXY", type=float, default=0.5,
                    help="Assumed per-hit sigmaXY [mm] for sagitta significance (default: 0.5)")
    ap.add_argument("--out", default="pt_diagnostic.csv", help="Output CSV (default: pt_diagnostic.csv)")
    args = ap.parse_args()

    events = parse_events_list(args.events)
    if not events:
        raise RuntimeError("No events parsed from --events")

    f = ROOT.TFile.Open(args.input)
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open: {args.input}")
    tree = f.Get("events")
    if not tree:
        raise RuntimeError("No TTree named 'events' in file")

    rows = []
    for ev in events:
        hits = load_hits_xyz(tree, ev, args.hits)
        hd = compute_hit_diagnostics(hits, sigma_xy_mm=args.sigmaXY)

        ts = load_primary_track_pt(tree, ev, args.track, expected_pt=args.expectedPt)

        pT_hitCircle = pT_from_circle_radius_mm(hd["hitCircleRmm"], args.Bz)

        row = {
            "event": ev,
            "nHits": hd["nHits"],
            "rmin_mm": hd["rmin"], "rmax_mm": hd["rmax"], "rspan_mm": hd["rspan"],
            "zmin_mm": hd["zmin"], "zmax_mm": hd["zmax"], "zspan_mm": hd["zspan"],
            "rmean_mm": hd["rmean"],

            "phiSpan_mean_rad": hd["phiSpan_mean_rad"],
            "phiSpan_mean_deg": hd["phiSpan_mean_deg"],
            "phiSpan_circle_rad": hd["phiSpan_circle_rad"],
            "phiSpan_circle_deg": hd["phiSpan_circle_deg"],

            "chord_mm": hd["chordMM"],
            "sagitta_mm": hd["sagittaMM"],
            "sagitta_sig": hd["sagittaSig"],
            "arcLenEst_mm": hd["arcLenEstMM"],

            "hitCircleR_mm": hd["hitCircleRmm"],
            "circleCond": hd["circleCond"],
            "pT_hitCircle_GeV": pT_hitCircle,

            "n_states": ts["n_states"],
            "pT_time_GeV": ts["pt_time"],
            "omega_GeVinv": ts["omega"],
            "pT_omega_GeV": ts["pt_omega"],
            "phi": ts["phi"],
            "tanLambda": ts["tanL"],
            "D0": ts["D0"],
            "Z0": ts["Z0"],
            "assoc": ts["assoc"],
        }
        rows.append(row)

        print(
            f"event {ev}: "
            f"pT(time)={row['pT_time_GeV']:.3f}  omega={row['omega_GeVinv']:.3e}  "
            f"pT(hitCircle)={row['pT_hitCircle_GeV']:.3f}  "
            f"phiSpan(mean)={row['phiSpan_mean_deg']:.2f}deg  "
            f"phiSpan(circle)={(row['phiSpan_circle_deg'] if math.isfinite(row['phiSpan_circle_deg']) else float('nan')):.2f}deg  "
            f"chord={row['chord_mm']:.1f}mm  sag={row['sagitta_mm']:.3f}mm  "
            f"sag/sig={row['sagitta_sig']:.2f}  "
            f"cond={row['circleCond']:.2e}  "
            f"R={row['hitCircleR_mm']:.1f}mm"
        )

    if rows:
        with open(args.out, "w", newline="") as fp:
            w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"[info] wrote {args.out}")

    f.Close()


if __name__ == "__main__":
    main()
