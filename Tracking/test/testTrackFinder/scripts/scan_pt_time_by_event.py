#!/usr/bin/env python3
"""
scan_pt_time_by_event.py

UPDATED:
  - Observability points are derived from SenseWireHit fields (wire point + angles + drift distance),
    not from position.x/y/z (which may not exist for SenseWireHit in podio ROOT output).
  - Track->trackerHits relation is decoded using:
      GenFitTracks.trackerHits_begin/end
      _GenFitTracks_trackerHits.index / _GenFitTracks_trackerHits.collectionID
    and we infer the target hit-collectionID per-track from the mode of collectionID values
    inside that track’s slice (no need for SenseWireHit@collectionID).

FIX (this update):
  - Preserve circle condition number values, including +inf, instead of converting them to NaN.
    Previously, circleCond was stored/printed as NaN whenever not finite, so inf -> NaN.
    Now, circleCond stores raw float values (finite / inf / nan).
    Only "None" is converted to NaN.

Usage:
  python3 scan_pt_time_by_event.py --input reco.root --expectedPt 53.183 --stdout
"""

import argparse
import math
import csv
import os
import logging
import ROOT
ROOT.gROOT.SetBatch(True)

# ---------------- logging ----------------

def setup_logger(log_path: str, also_stdout: bool) -> logging.Logger:
    logger = logging.getLogger("scan_pt")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    logger.propagate = False

    os.makedirs(os.path.dirname(os.path.abspath(log_path)) or ".", exist_ok=True)

    fh = logging.FileHandler(log_path, mode="w")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s"))
    logger.addHandler(fh)

    if also_stdout:
        sh = logging.StreamHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(logging.Formatter("%(levelname)-7s | %(message)s"))
        logger.addHandler(sh)

    logger.info("Logging to: %s", os.path.abspath(log_path))
    return logger


# ---------------- basic helpers ----------------

def _find_leaf(tree, name):
    return tree.GetLeaf(name)

def _finite(x):
    return x is not None and math.isfinite(x)

def _is_number(x):
    # True for finite, inf, nan; False for None or non-float-convertible
    try:
        float(x)
        return True
    except Exception:
        return False

def _as_float_or_nan(x):
    # Preserve inf/nan. Only None/non-convertible becomes NaN.
    try:
        return float(x)
    except Exception:
        return float("nan")

def _median(vals):
    vals = [v for v in vals if _finite(v)]
    if not vals:
        return float("nan")
    vals.sort()
    n = len(vals)
    mid = n // 2
    if (n % 2) == 1:
        return float(vals[mid])
    return 0.5 * (vals[mid - 1] + vals[mid])

def _percentile(vals, q):
    vals = [v for v in vals if _finite(v)]
    if not vals:
        return float("nan")
    vals.sort()
    if q <= 0:
        return float(vals[0])
    if q >= 100:
        return float(vals[-1])
    pos = (q / 100.0) * (len(vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(vals[lo])
    frac = pos - lo
    return float(vals[lo] * (1.0 - frac) + vals[hi] * frac)

def _mad(vals, med=None):
    vals = [v for v in vals if _finite(v)]
    if not vals:
        return float("nan")
    if not _finite(med):
        med = _median(vals)
    absdev = [abs(v - med) for v in vals]
    return _median(absdev)

def _trunc_rms(vals, central_frac=0.95, center=None):
    vals = [v for v in vals if _finite(v)]
    if not vals:
        return float("nan")
    if not (0.0 < central_frac <= 1.0):
        return float("nan")
    if not _finite(center):
        center = _median(vals)
    d = [abs(v - center) for v in vals]
    keep_n = max(1, int(math.floor(central_frac * len(d))))
    thr = sorted(d)[keep_n - 1]
    kept = [(v - center) for v in vals if abs(v - center) <= thr]
    if not kept:
        return float("nan")
    s2 = sum(x*x for x in kept)
    return math.sqrt(s2 / len(kept))

def _mean_std(vals):
    vals = [v for v in vals if _finite(v)]
    if not vals:
        return (float("nan"), float("nan"))
    m = sum(vals) / len(vals)
    v = sum((x - m) ** 2 for x in vals) / max(1, (len(vals) - 1))
    return (m, math.sqrt(v))

def _list_leaves(tree):
    leaves = tree.GetListOfLeaves()
    if not leaves:
        return []
    return [obj.GetName() for obj in leaves]

def _scan_leaf_by_suffix(tree, coll_name, suffix):
    for nm in _list_leaves(tree):
        if coll_name in nm and nm.endswith(suffix):
            return nm
    return None

def _prefix_for_collection(tree, coll_name, required_suffix):
    for nm in _list_leaves(tree):
        if coll_name in nm and nm.endswith(required_suffix):
            return nm[:-len(required_suffix)]
    return None

def _resolve_leaf_any(tree, coll, suffixes):
    """
    Find any leaf for this collection whose name ends with one of suffixes.
    Returns (leafname, suffixUsed) or (None, None).
    """
    leaves = _list_leaves(tree)
    for suf in suffixes:
        cand = _scan_leaf_by_suffix(tree, coll, suf)
        if cand:
            return cand, suf
        direct = f"{coll}.{suf}" if not suf.startswith("@") else f"{coll}{suf}"
        if direct in leaves:
            return direct, suf
    return None, None


def phi_span_from_chord_sagitta(chord_mm, sagitta_mm):
    """
    Estimate arc angle (phi span) from chord c and sagitta s for a circular arc.
    Returns NaN if inputs are invalid.
    """
    if not (_finite(chord_mm) and _finite(sagitta_mm)):
        return float("nan")
    c = float(chord_mm)
    s = float(sagitta_mm)
    if c <= 0.0 or s <= 0.0:
        return float("nan")

    R = (c*c) / (8.0*s) + 0.5*s
    if not (_finite(R) and R > 0.0):
        return float("nan")

    x = c / (2.0*R)
    x = max(-1.0, min(1.0, x))
    return 2.0 * math.asin(x)


# ---------------- TrackState resolution ----------------

def resolve_ts_prefix(tree, coll_name):
    candidates = [
        f"{coll_name}.trackStates_AtIP.",
        f"{coll_name}.TrackStates_AtIP.",
        f"{coll_name}.trackStates.",
        f"{coll_name}.TrackStates.",
        f"_{coll_name}_trackStates_AtIP.",
        f"_{coll_name}_TrackStates_AtIP.",
        f"_{coll_name}_trackStates.",
        f"_{coll_name}_TrackStates.",
    ]
    for pref in candidates:
        if _find_leaf(tree, pref + "phi"):
            return pref
    pref = _prefix_for_collection(tree, coll_name, "phi")
    return pref

def resolve_begin_end(tree, coll_name):
    pairs = [
        (f"{coll_name}.trackStates_begin", f"{coll_name}.trackStates_end"),
        (f"{coll_name}.TrackStates_begin", f"{coll_name}.TrackStates_end"),
    ]
    for b, e in pairs:
        if _find_leaf(tree, b) and _find_leaf(tree, e):
            return b, e
    b = _scan_leaf_by_suffix(tree, coll_name, "trackStates_begin")
    e = _scan_leaf_by_suffix(tree, coll_name, "trackStates_end")
    if b and e:
        return b, e
    b = _scan_leaf_by_suffix(tree, coll_name, "TrackStates_begin")
    e = _scan_leaf_by_suffix(tree, coll_name, "TrackStates_end")
    if b and e:
        return b, e
    return None, None


# ---------------- Track->Hits relation resolution ----------------

def resolve_track_hit_begin_end(tree, track_coll):
    candidates = [
        (f"{track_coll}.trackerHits_begin", f"{track_coll}.trackerHits_end"),
        (f"{track_coll}.TrackerHits_begin", f"{track_coll}.TrackerHits_end"),
        (f"{track_coll}.hits_begin",        f"{track_coll}.hits_end"),
        (f"{track_coll}.Hits_begin",        f"{track_coll}.Hits_end"),
    ]
    for b, e in candidates:
        if _find_leaf(tree, b) and _find_leaf(tree, e):
            return b, e
    b = _scan_leaf_by_suffix(tree, track_coll, "trackerHits_begin")
    e = _scan_leaf_by_suffix(tree, track_coll, "trackerHits_end")
    if b and e:
        return b, e
    b = _scan_leaf_by_suffix(tree, track_coll, "hits_begin")
    e = _scan_leaf_by_suffix(tree, track_coll, "hits_end")
    if b and e:
        return b, e
    return None, None

def resolve_track_hit_relation_index_leaves(tree, track_coll):
    candidates = [
        (f"{track_coll}.trackerHits.index",        f"{track_coll}.trackerHits.collectionID"),
        (f"{track_coll}.TrackerHits.index",        f"{track_coll}.TrackerHits.collectionID"),
        (f"{track_coll}.hits.index",               f"{track_coll}.hits.collectionID"),
        (f"{track_coll}.Hits.index",               f"{track_coll}.Hits.collectionID"),
    ]
    for idx, cid in candidates:
        if _find_leaf(tree, idx) and _find_leaf(tree, cid):
            return idx, cid
    idx = _scan_leaf_by_suffix(tree, track_coll, "trackerHits.index")
    cid = _scan_leaf_by_suffix(tree, track_coll, "trackerHits.collectionID")
    if idx and cid:
        return idx, cid
    idx = _scan_leaf_by_suffix(tree, track_coll, "hits.index")
    cid = _scan_leaf_by_suffix(tree, track_coll, "hits.collectionID")
    if idx and cid:
        return idx, cid
    return None, None


# ---------------- SenseWireHit field resolution + point building ----------------

def resolve_sensewire_fields(tree, hit_coll):
    """
    Try to resolve leaves needed to build an XY point proxy from SenseWireHit:
      - wire point: position.{x,y,z} OR wirePosition.{x,y,z}
      - distanceToWire
      - wireAzimuthalAngle
      - wireStereoAngle
    Returns dict of leaf names + leaf objects (or None values).
    """
    px_name, _ = _resolve_leaf_any(tree, hit_coll, ["position.x", "Position.x", "wirePosition.x", "WirePosition.x"])
    py_name, _ = _resolve_leaf_any(tree, hit_coll, ["position.y", "Position.y", "wirePosition.y", "WirePosition.y"])
    pz_name, _ = _resolve_leaf_any(tree, hit_coll, ["position.z", "Position.z", "wirePosition.z", "WirePosition.z"])

    d_name, _   = _resolve_leaf_any(tree, hit_coll, ["distanceToWire", "DistanceToWire"])
    phi_name, _ = _resolve_leaf_any(tree, hit_coll, ["wireAzimuthalAngle", "WireAzimuthalAngle"])
    st_name, _  = _resolve_leaf_any(tree, hit_coll, ["wireStereoAngle", "WireStereoAngle"])

    out = {
        "px_name": px_name, "py_name": py_name, "pz_name": pz_name,
        "d_name": d_name, "phi_name": phi_name, "st_name": st_name,
        "px": _find_leaf(tree, px_name) if px_name else None,
        "py": _find_leaf(tree, py_name) if py_name else None,
        "pz": _find_leaf(tree, pz_name) if pz_name else None,
        "d":  _find_leaf(tree, d_name)  if d_name  else None,
        "phi":_find_leaf(tree, phi_name)if phi_name else None,
        "st": _find_leaf(tree, st_name) if st_name else None,
    }
    return out

def _unit(vx, vy, vz, fallback=(0.0, 0.0, 1.0)):
    m2 = vx*vx + vy*vy + vz*vz
    if not (m2 > 0.0) or not math.isfinite(m2):
        return fallback
    m = math.sqrt(m2)
    return (vx/m, vy/m, vz/m)

def _cross(ax, ay, az, bx, by, bz):
    return (ay*bz - az*by, az*bx - ax*bz, ax*by - ay*bx)

def _build_mmid_from_wire(wpos, d, phi, st):
    """
    Reproduce the GGTF_tracking construction:
      dir = (0,0,1) rotated X by st, rotated Z by phi
      xprime = (1,0,-dirx/dirz) normalized (fallbacks)
      L = wpos + xprime*(-d)
      R = wpos + xprime*(+d)
      Mmid = 0.5*(L+R)
    """
    dx0 = 0.0
    dy0 = -math.sin(st)
    dz0 = math.cos(st)

    dx = dx0*math.cos(phi) - dy0*math.sin(phi)
    dy = dx0*math.sin(phi) + dy0*math.cos(phi)
    dz = dz0
    (dx, dy, dz) = _unit(dx, dy, dz, fallback=(0.0, 0.0, 1.0))

    if abs(dz) < 1e-12:
        xpx, xpy, xpz = (1.0, 0.0, 0.0)
    else:
        xpx, xpy, xpz = (1.0, 0.0, -dx/dz)
    (xpx, xpy, xpz) = _unit(xpx, xpy, xpz, fallback=(1.0, 0.0, 0.0))

    (ypx, ypy, ypz) = _cross(dx, dy, dz, xpx, xpy, xpz)
    (ypx, ypy, ypz) = _unit(ypx, ypy, ypz, fallback=(0.0, 1.0, 0.0))

    (xpx, xpy, xpz) = _cross(ypx, ypy, ypz, dx, dy, dz)
    (xpx, xpy, xpz) = _unit(xpx, xpy, xpz, fallback=(1.0, 0.0, 0.0))

    wx, wy, wz = wpos
    Lx, Ly, Lz = (wx + xpx*(-d), wy + xpy*(-d), wz + xpz*(-d))
    Rx, Ry, Rz = (wx + xpx*(+d), wy + xpy*(+d), wz + xpz*(+d))
    mx, my, mz = (0.5*(Lx+Rx), 0.5*(Ly+Ry), 0.5*(Lz+Rz))
    return (mx, my, mz)


# ---------------- circle fit + observability ----------------

def fit_circle_ls_svd_xy(points_xy):
    n = len(points_xy)
    if n < 3:
        return (False, float("nan"), float("nan"), float("nan"), float("inf"), float("inf"))
    try:
        xs = [p[0] for p in points_xy]
        ys = [p[1] for p in points_xy]
        mx = sum(xs) / n
        my = sum(ys) / n
        scale = 0.0
        for (x, y) in points_xy:
            scale = max(scale, math.hypot(x - mx, y - my))
        if not (_finite(scale) and scale > 0.0):
            scale = 1.0

        A = ROOT.TMatrixD(n, 3)
        b = ROOT.TVectorD(n)
        for i, (x, y) in enumerate(points_xy):
            xn = (x - mx) / scale
            yn = (y - my) / scale
            A[i][0] = xn
            A[i][1] = yn
            A[i][2] = 1.0
            b[i] = -(xn*xn + yn*yn)

        svd = ROOT.TDecompSVD(A)
        if not svd.Decompose():
            return (False, float("nan"), float("nan"), float("nan"), float("inf"), float("inf"))

        sig = svd.GetSig()
        svals = [float(sig[i]) for i in range(sig.GetNrows())]
        smax = max(svals) if svals else 0.0
        smin = min([s for s in svals if s > 0.0], default=0.0)
        if not (smax > 0.0 and smin > 0.0):
            return (False, float("nan"), float("nan"), float("nan"), float("inf"), float("inf"))
        cond = smax / smin

        u = svd.Solve(b)
        Dn = float(u[0]); En = float(u[1]); Fn = float(u[2])
        D = Dn * scale
        E = En * scale
        F = Fn * scale * scale

        cx = mx - 0.5 * D
        cy = my - 0.5 * E
        R2 = cx*cx + cy*cy - F
        if not (_finite(cx) and _finite(cy) and _finite(R2) and R2 > 1e-18):
            return (False, float("nan"), float("nan"), float("nan"), cond, float("inf"))
        R = math.sqrt(R2)
        if not (_finite(R) and R > 1e-9):
            return (False, float("nan"), float("nan"), float("nan"), cond, float("inf"))

        ss = 0.0
        for (x, y) in points_xy:
            r = (x*x + y*y) + D*x + E*y + F
            ss += r*r
        rms = math.sqrt(ss / n)
        return (True, cx, cy, R, cond, rms)
    except Exception:
        return (False, float("nan"), float("nan"), float("nan"), float("inf"), float("inf"))

def unwrap_phi_span(points_xy, cx, cy):
    n = len(points_xy)
    if n < 2 or not (_finite(cx) and _finite(cy)):
        return (False, float("nan"), float("nan"), float("nan"))
    phi = [math.atan2(y - cy, x - cx) for (x, y) in points_xy]
    for i in range(1, n):
        d = phi[i] - phi[i-1]
        while d > math.pi:
            phi[i] -= 2.0*math.pi
            d = phi[i] - phi[i-1]
        while d < -math.pi:
            phi[i] += 2.0*math.pi
            d = phi[i] - phi[i-1]
    return (True, min(phi), max(phi), max(phi) - min(phi))

def chord_xy_maxpair_mm(points_xyz_mm):
    n = len(points_xyz_mm)
    if n < 2:
        return float("nan"), -1, -1
    best_d2 = -1.0
    best = (-1, -1)
    for i in range(n):
        x0, y0, _ = points_xyz_mm[i]
        for j in range(i + 1, n):
            x1, y1, _ = points_xyz_mm[j]
            dx = x1 - x0
            dy = y1 - y0
            d2 = dx*dx + dy*dy
            if d2 > best_d2 and math.isfinite(d2):
                best_d2 = d2
                best = (i, j)
    if best_d2 <= 0:
        return float("nan"), -1, -1
    return math.sqrt(best_d2), best[0], best[1]

def sagitta_max_mm(points_xyz_mm, i0, i1):
    n = len(points_xyz_mm)
    if n < 3 or i0 < 0 or i1 < 0 or i0 == i1:
        return float("nan")
    x0, y0, _ = points_xyz_mm[i0]
    x1, y1, _ = points_xyz_mm[i1]
    dx = x1 - x0
    dy = y1 - y0
    denom = math.hypot(dx, dy)
    if denom < 1e-12:
        return float("nan")
    smax = 0.0
    for (x, y, _) in points_xyz_mm:
        s = abs(dx*(y0 - y) - dy*(x0 - x)) / denom
        if math.isfinite(s):
            smax = max(smax, s)
    return smax


# ---------------- stats packaging ----------------

def stats_bundle(vals, central_frac=0.95):
    x = [v for v in vals if _finite(v)]
    out = {"n": len(x)}
    if not x:
        out.update({k: float("nan") for k in ["mean","std","median","mad","madsigma","truncRMS","p05","p16","p50","p84","p95"]})
        return out
    mean, std = _mean_std(x)
    med = _median(x)
    mad = _mad(x, med=med)
    trr = _trunc_rms(x, central_frac=central_frac, center=med)
    out.update({
        "mean": mean, "std": std, "median": med,
        "mad": mad, "madsigma": (1.4826 * mad) if _finite(mad) else float("nan"),
        "truncRMS": trr,
        "p05": _percentile(x, 5), "p16": _percentile(x, 16), "p50": _percentile(x, 50),
        "p84": _percentile(x, 84), "p95": _percentile(x, 95),
    })
    return out


# ---------------- main scan logic ----------------

def scan_file(path, track_coll, expected_pt, top_n=30, event_filter=None,
              verbose=False, invalid_time=-1.0, dump_states=0, dump_hits=0,
              hit_coll="GGTF_SenseWireHits",
              min_phi_span=0.06, min_chord_xy_mm=500.0, max_circle_cond=1e6,
              central_frac=0.95,
              logger=None):
    if logger is None:
        logger = logging.getLogger("scan_pt")

    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open: {path}")

    tree = f.Get("events")
    if not tree:
        raise RuntimeError("No TTree named 'events'")

    # TrackStates
    ts_prefix = resolve_ts_prefix(tree, track_coll)
    if not ts_prefix:
        raise RuntimeError(f"Could not resolve TrackState prefix for '{track_coll}'")

    time_leaf = _find_leaf(tree, ts_prefix + "time")
    omg_leaf  = _find_leaf(tree, ts_prefix + "omega")
    phi_leaf  = _find_leaf(tree, ts_prefix + "phi")
    if not phi_leaf:
        raise RuntimeError(f"Missing required leaf: '{ts_prefix}phi'")

    # Track->TrackStates association
    bname, ename = resolve_begin_end(tree, track_coll)
    beg_ts_leaf = _find_leaf(tree, bname) if bname else None
    end_ts_leaf = _find_leaf(tree, ename) if ename else None

    # Track->Hits association
    hbname, hename = resolve_track_hit_begin_end(tree, track_coll)
    beg_hit_leaf = _find_leaf(tree, hbname) if hbname else None
    end_hit_leaf = _find_leaf(tree, hename) if hename else None

    # Relation payload leaves
    hidx_name, hcid_name = resolve_track_hit_relation_index_leaves(tree, track_coll)
    hit_rel_index_leaf = _find_leaf(tree, hidx_name) if hidx_name else None
    hit_rel_cid_leaf   = _find_leaf(tree, hcid_name) if hcid_name else None

    # SenseWireHit field leaves
    sw = resolve_sensewire_fields(tree, hit_coll)

    have_rel = bool(beg_hit_leaf and end_hit_leaf and hit_rel_index_leaf and hit_rel_cid_leaf)
    have_sw_fields = bool(sw["px"] and sw["py"] and sw["d"] and sw["phi"] and sw["st"])
    have_hits = bool(have_rel and have_sw_fields)

    logger.info("[file] %s", path)
    logger.info("[cfg] TrackColl=%s", track_coll)
    logger.info("[cfg] TrackState prefix=%s", ts_prefix)
    logger.info("[cfg] TrackStates assoc begin/end=%s %s (%s)", bname, ename, "OK" if (beg_ts_leaf and end_ts_leaf) else "MISSING")
    logger.info("[cfg] TrackHits assoc begin/end=%s %s (%s)", hbname, hename, "OK" if (beg_hit_leaf and end_hit_leaf) else "MISSING")
    logger.info("[cfg] TrackHits relation payload: index=%s collectionID=%s (%s)", hidx_name, hcid_name,
                "OK" if (hit_rel_index_leaf and hit_rel_cid_leaf) else "MISSING")

    logger.info("[cfg] SenseWireHit leaf map for '%s':", hit_coll)
    logger.info("      wireX=%s", sw["px_name"])
    logger.info("      wireY=%s", sw["py_name"])
    logger.info("      wireZ=%s", sw["pz_name"])
    logger.info("      d    =%s", sw["d_name"])
    logger.info("      phi  =%s", sw["phi_name"])
    logger.info("      st   =%s", sw["st_name"])

    logger.info("[cfg] Hit association + observability mode: %s", "OK" if have_hits else "MISSING (observability will be NaN)")
    logger.info("[cfg] Obs thresholds: minPhiSpan=%.4g rad  minChordXY=%.4g mm  maxCond=%.3g",
                min_phi_span, min_chord_xy_mm, max_circle_cond)
    logger.info("[cfg] Robust stats central fraction for truncRMS = %.3f", central_frac)

    if not have_hits:
        leaves = _list_leaves(tree)
        near = [nm for nm in leaves if (hit_coll in nm)]
        logger.info("[hint] Leaves containing '%s' (first 80):", hit_coll)
        for nm in near[:80]:
            logger.info("       %s", nm)

    def time_is_valid(t):
        return _finite(t) and (t != invalid_time) and (t > 0.0)

    def omg_is_valid(o):
        return _finite(o) and abs(o) > 0.0

    def mode_int(vals):
        if not vals:
            return None
        cnt = {}
        for v in vals:
            cnt[v] = cnt.get(v, 0) + 1
        return max(cnt.items(), key=lambda kv: kv[1])[0]

    n_ev = tree.GetEntries()
    results = []

    ev_range = range(n_ev) if event_filter is None else [event_filter]
    for iev in ev_range:
        tree.GetEntry(iev)

        n_states_evt = int(phi_leaf.GetNdata())
        time_vals = [float(time_leaf.GetValue(i)) for i in range(n_states_evt)] if time_leaf else [float("nan")] * n_states_evt
        omg_vals  = [float(omg_leaf.GetValue(i))  for i in range(n_states_evt)] if omg_leaf  else [float("nan")] * n_states_evt
        ptomg_vals = [(1.0/abs(o) if omg_is_valid(o) else float("nan")) for o in omg_vals]

        time_valid_all = [t for t in time_vals if time_is_valid(t)]
        pt_time_med_all = _median(time_valid_all)
        pt_time_min_all = min(time_valid_all) if time_valid_all else float("nan")
        pt_time_max_all = max(time_valid_all) if time_valid_all else float("nan")
        n_time_valid_all = len(time_valid_all)

        ptomg_valid_all = [p for p in ptomg_vals if _finite(p)]
        pt_omg_med_all = _median(ptomg_valid_all)
        pt_omg_min_all = min(ptomg_valid_all) if ptomg_valid_all else float("nan")
        pt_omg_max_all = max(ptomg_valid_all) if ptomg_valid_all else float("nan")

        per_track = []
        n_tracks_evt = int(beg_ts_leaf.GetNdata()) if (beg_ts_leaf and end_ts_leaf) else 0
        nstates_per_track = []

        for ti in range(n_tracks_evt):
            bts = int(beg_ts_leaf.GetValue(ti))
            ets = int(end_ts_leaf.GetValue(ti))
            if bts < 0 or ets < 0 or ets <= bts or bts >= n_states_evt:
                nstates_per_track.append(0)
                continue
            ets = min(ets, n_states_evt)
            nseg = ets - bts
            nstates_per_track.append(nseg)

            seg_time = [time_vals[k] for k in range(bts, ets) if time_is_valid(time_vals[k])]
            seg_ptomg = [ptomg_vals[k] for k in range(bts, ets) if _finite(ptomg_vals[k])]
            pt_t = _median(seg_time)
            pt_o = _median(seg_ptomg)

            phi_span = chord = cond = sag = rms = float("nan")
            circle_ok = False
            curv_obs = False
            n_hits_primary = 0

            if have_hits:
                bh = int(beg_hit_leaf.GetValue(ti))
                eh = int(end_hit_leaf.GetValue(ti))
                n_rel_tot = int(hit_rel_index_leaf.GetNdata())
                if bh >= 0 and eh > bh and bh < n_rel_tot:
                    eh = min(eh, n_rel_tot)

                    cids = [int(hit_rel_cid_leaf.GetValue(ri)) for ri in range(bh, eh)]
                    target_cid = mode_int(cids)

                    hits_xyz = []
                    n_sw = int(sw["px"].GetNdata())
                    for ri in range(bh, eh):
                        idx = int(hit_rel_index_leaf.GetValue(ri))
                        cid = int(hit_rel_cid_leaf.GetValue(ri))
                        if target_cid is not None and cid != target_cid:
                            continue
                        if idx < 0 or idx >= n_sw:
                            continue

                        wx = float(sw["px"].GetValue(idx))
                        wy = float(sw["py"].GetValue(idx))
                        wz = float(sw["pz"].GetValue(idx)) if sw["pz"] else 0.0
                        d  = float(sw["d"].GetValue(idx))
                        ph = float(sw["phi"].GetValue(idx))
                        st = float(sw["st"].GetValue(idx))

                        mx, my, mz = _build_mmid_from_wire((wx, wy, wz), d, ph, st)
                        if math.isfinite(mx) and math.isfinite(my) and math.isfinite(mz):
                            hits_xyz.append((mx, my, mz))

                    n_hits_primary = len(hits_xyz)

                    hits_xyz = [(x, y, z) for (x, y, z) in hits_xyz if _finite(x) and _finite(y) and _finite(z)]

                    if len(hits_xyz) >= 3:
                        chord, i0, i1 = chord_xy_maxpair_mm(hits_xyz)
                        sag = sagitta_max_mm(hits_xyz, i0, i1)

                        pts_xy = [(x, y) for (x, y, _) in hits_xyz]
                        okc, cx, cy, R, cond_est, rms_res = fit_circle_ls_svd_xy(pts_xy)
                        circle_ok = bool(okc)
                        rms = rms_res

                        # Preserve inf/nan/finite values
                        cond = cond_est

                        phi_span = float("nan")
                        if okc and _finite(cx) and _finite(cy):
                            okp, _, _, span = unwrap_phi_span(pts_xy, cx, cy)
                            if okp and _finite(span):
                                phi_span = span

                        if not _finite(phi_span):
                            phi_span = phi_span_from_chord_sagitta(chord, sag)

                        phi_ok   = _finite(phi_span) and (phi_span >= min_phi_span)
                        chord_ok = _finite(chord) and (chord >= min_chord_xy_mm)

                        # For low-curvature tracks, cond can be inf/huge; don't require finiteness
                        cond_ok  = (not _finite(cond_est)) or (cond_est <= max_circle_cond)

                        curv_obs = bool(phi_ok and chord_ok and cond_ok)

            per_track.append((ti, pt_t, pt_o, bts, ets,
                              phi_span, chord, cond, curv_obs, sag, circle_ok, rms, nseg, n_hits_primary))

        if nstates_per_track:
            nstates_min = min(nstates_per_track)
            nstates_max = max(nstates_per_track)
            nstates_med = _median([float(x) for x in nstates_per_track])
        else:
            nstates_min = nstates_med = nstates_max = float("nan")

        expected_pt = float(expected_pt)

        if per_track:
            def score(tt):
                _, pt_t, pt_o, *_ = tt
                if _finite(pt_t):
                    return abs(pt_t - expected_pt)
                if _finite(pt_o):
                    return abs(pt_o - expected_pt)
                return float("inf")
            primary = min(per_track, key=score)
            (ti, pt_primary_time, pt_primary_omg, bts, ets,
             phi_span, chord, cond, curv_obs, sag, circle_ok, rms, nseg, n_hits_primary) = primary
            assoc_note = f"track={ti} ts[{bts}:{ets})"
            primary_track_nstates = nseg
        else:
            ti = -1
            pt_primary_time = pt_time_med_all
            pt_primary_omg  = pt_omg_med_all
            assoc_note = "flatStates(median)"
            phi_span = chord = cond = sag = rms = float("nan")
            curv_obs = False
            circle_ok = False
            primary_track_nstates = 0
            n_hits_primary = 0

        pt_time_valid_primary = _finite(pt_primary_time) and time_is_valid(pt_primary_time)
        pt_omg_valid_primary  = _finite(pt_primary_omg) and (pt_primary_omg > 0.0)

        if pt_time_valid_primary:
            pt_used = float(pt_primary_time)
            pt_used_src = "time"
        elif pt_omg_valid_primary:
            pt_used = float(pt_primary_omg)
            pt_used_src = "omega"
        else:
            continue

        signed_err = pt_used - expected_pt
        abs_err = abs(signed_err)
        rel_err = abs_err / expected_pt if expected_pt > 0 else float("inf")
        rel_signed = signed_err / expected_pt if expected_pt > 0 else float("nan")

        results.append({
            "event": int(iev),
            "pt_used": pt_used,
            "pt_used_src": pt_used_src,
            "primary_track_index": int(ti),
            "primary_track_nstates": int(primary_track_nstates),
            "pt_primary_time": float(pt_primary_time) if _finite(pt_primary_time) else float("nan"),
            "pt_primary_omega": float(pt_primary_omg) if _finite(pt_primary_omg) else float("nan"),
            "pt_time_valid_primary": int(bool(pt_time_valid_primary)),
            "pt_omega_valid_primary": int(bool(pt_omg_valid_primary)),
            "n_tracks_evt": int(n_tracks_evt),
            "n_states_evt": int(n_states_evt),
            "nstates_per_track_min": float(nstates_min) if _finite(nstates_min) else float("nan"),
            "nstates_per_track_med": float(nstates_med) if _finite(nstates_med) else float("nan"),
            "nstates_per_track_max": float(nstates_max) if _finite(nstates_max) else float("nan"),
            "n_time_valid_allstates": int(n_time_valid_all),
            "pt_time_min_allstates": float(pt_time_min_all) if _finite(pt_time_min_all) else float("nan"),
            "pt_time_med_allstates": float(pt_time_med_all) if _finite(pt_time_med_all) else float("nan"),
            "pt_time_max_allstates": float(pt_time_max_all) if _finite(pt_time_max_all) else float("nan"),
            "pt_omg_min_allstates": float(pt_omg_min_all) if _finite(pt_omg_min_all) else float("nan"),
            "pt_omg_med_allstates": float(pt_omg_med_all) if _finite(pt_omg_med_all) else float("nan"),
            "pt_omg_max_allstates": float(pt_omg_max_all) if _finite(pt_omg_max_all) else float("nan"),
            "signed_err": float(signed_err),
            "abs_err": float(abs_err),
            "rel_err": float(rel_err),
            "rel_signed": float(rel_signed),
            "phiSpan": float(phi_span) if _finite(phi_span) else float("nan"),
            "chordXY_mm": float(chord) if _finite(chord) else float("nan"),
            # IMPORTANT FIX: preserve inf/nan/finite (only None -> NaN)
            "circleCond": _as_float_or_nan(cond),
            "circleOK": int(bool(circle_ok)),
            "rmsAlgRes": float(rms) if _finite(rms) else float("nan"),
            "sagitta_mm": float(sag) if _finite(sag) else float("nan"),
            "curvObservable": int(bool(curv_obs)),
            "n_hits_primary": int(n_hits_primary),
            "assoc": assoc_note,
        })

        if verbose:
            logger.info(
                "[ev %5d] used=%4s pT=%9.3f dPt=%+8.3f abs=%7.3f rel=%7.3f "
                "nHits=%3d phiSpan=%7.4f chord=%7.1f cond=%9.3g curvObs=%d %s",
                iev, pt_used_src, pt_used, signed_err, abs_err, rel_err,
                int(n_hits_primary),
                phi_span if _finite(phi_span) else float("nan"),
                chord if _finite(chord) else float("nan"),
                _as_float_or_nan(cond),
                int(curv_obs), assoc_note
            )

    f.Close()
    return results, n_ev, len(list(ev_range))


def write_csv(results, out_csv, logger):
    if not results:
        logger.warning("no results to write CSV: %s", out_csv)
        return
    with open(out_csv, "w", newline="") as fp:
        fieldnames = list(results[0].keys())
        w = csv.DictWriter(fp, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow(r)
    logger.info("wrote CSV: %s", out_csv)


def log_global_stats(results, expected_pt, central_frac, logger):
    pts = [r["pt_used"] for r in results if _finite(r.get("pt_used"))]
    dpt = [r["signed_err"] for r in results if _finite(r.get("signed_err"))]
    drel = [r["rel_signed"] for r in results if _finite(r.get("rel_signed"))]
    absd = [r["abs_err"] for r in results if _finite(r.get("abs_err"))]
    absrel = [r["rel_err"] for r in results if _finite(r.get("rel_err"))]

    st_pt = stats_bundle(pts, central_frac=central_frac)
    st_dpt = stats_bundle(dpt, central_frac=central_frac)
    st_drel = stats_bundle(drel, central_frac=central_frac)
    st_abs = stats_bundle(absd, central_frac=central_frac)
    st_absrel = stats_bundle(absrel, central_frac=central_frac)

    logger.info("")
    logger.info("[global] expectedPt = %.6g GeV", expected_pt)
    logger.info("[global] N usable events = %d", st_pt["n"])

    def fmt(st):
        return (f"mean={st['mean']:.6g} std={st['std']:.6g} "
                f"median={st['median']:.6g} MAD={st['mad']:.6g} MADsigma={st['madsigma']:.6g} "
                f"truncRMS={st['truncRMS']:.6g} "
                f"p16/p84={st['p16']:.6g}/{st['p84']:.6g} p05/p95={st['p05']:.6g}/{st['p95']:.6g}")

    logger.info("[global] pT_used:          %s", fmt(st_pt))
    logger.info("[global] (pT-expected):    %s", fmt(st_dpt))
    logger.info("[global] (pT-expected)/pt: %s", fmt(st_drel))
    logger.info("[global] |pT-expected|:    %s", fmt(st_abs))
    logger.info("[global] |pT-expected|/pt: %s", fmt(st_absrel))

    n_time = sum(1 for r in results if r.get("pt_used_src") == "time")
    n_omg = sum(1 for r in results if r.get("pt_used_src") == "omega")
    logger.info("[global] pt_used_src: time=%d omega=%d", n_time, n_omg)

    n_curv = sum(1 for r in results if int(r.get("curvObservable", 0)) == 1)
    logger.info("[global] curvObservable (primary track): %d / %d", n_curv, st_pt["n"])


def main():
    ap = argparse.ArgumentParser(description="Scan TrackState.time/omega + observability from SenseWireHits + robust stats.")
    ap.add_argument("--input", required=True, help="Input EDM4hep ROOT file")
    ap.add_argument("--trackCollection", default="GenFitTracks", help="Track collection name (default: GenFitTracks)")
    ap.add_argument("--hitCollection", default="OutputWireHitsGGTF", help="SenseWireHit collection name")
    ap.add_argument("--expectedPt", type=float, required=True, help="Expected pT for this sample [GeV]")

    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--event", type=int, default=None)
    ap.add_argument("--csv", default=None)

    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--invalidTime", type=float, default=-1.0)

    ap.add_argument("--minPhiSpan", type=float, default=0.06)
    ap.add_argument("--minChordXY", type=float, default=500.0)
    ap.add_argument("--maxCircleCond", type=float, default=1e6)
    ap.add_argument("--centralFrac", type=float, default=0.95)

    ap.add_argument("--type", choices=["bad", "good"], default="bad")
    ap.add_argument("--metric", choices=["abs", "rel"], default="abs")

    ap.add_argument("--log", default="")
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args()

    log_path = args.log.strip() or f"{os.path.basename(args.input).replace('.root','')}.scan_pt.log"
    logger = setup_logger(log_path, also_stdout=bool(args.stdout))

    results, n_ev, n_scanned = scan_file(
        args.input, args.trackCollection, args.expectedPt,
        top_n=args.top, event_filter=args.event, verbose=args.verbose,
        invalid_time=args.invalidTime,
        hit_coll=args.hitCollection,
        min_phi_span=args.minPhiSpan, min_chord_xy_mm=args.minChordXY, max_circle_cond=args.maxCircleCond,
        central_frac=args.centralFrac,
        logger=logger,
    )

    if not results:
        logger.warning("scanned %d event(s) (file has %d events) but found no usable per-event pT.", n_scanned, n_ev)
        print(f"[done] log written to: {os.path.abspath(log_path)}")
        return

    log_global_stats(results, args.expectedPt, args.centralFrac, logger)

    key = "abs_err" if args.metric == "abs" else "rel_err"
    reverse = True if args.type == "bad" else False
    results.sort(key=lambda r: r.get(key, float("inf")), reverse=reverse)

    n_show = min(args.top, len(results))
    label = "worst" if args.type == "bad" else "best"
    metric_label = "|pT-expected|" if args.metric == "abs" else "|pT-expected|/expected"

    logger.info("")
    logger.info("[summary] scanned %d event(s) (file has %d events)", n_scanned, n_ev)
    logger.info("[summary] expectedPt = %.6g GeV", args.expectedPt)
    logger.info("[summary] showing top %d %s events by %s", n_show, label, metric_label)

    header = (f"{'rank':>4s} {'event':>6s} {'src':>4s} "
              f"{'pT_used':>9s} {'dPt':>9s} {'absErr':>8s} {'relErr':>7s} "
              f"{'nHit':>4s} {'phiSpan':>8s} {'chord':>7s} {'cond':>9s} {'curv':>4s}  assoc")
    logger.info(header)

    for i, r in enumerate(results[:n_show], 1):
        logger.info(
            f"{i:4d} {r['event']:6d} {r['pt_used_src']:>4s} "
            f"{r['pt_used']:9.2f} {r['signed_err']:+9.2f} {r['abs_err']:8.2f} {r['rel_err']:7.3f} "
            f"{r['n_hits_primary']:4d} {r['phiSpan']:8.4f} {r['chordXY_mm']:7.1f} {r['circleCond']:9.3g} {r['curvObservable']:4d}  {r['assoc']}"
        )

    if args.csv:
        write_csv(results, args.csv, logger)

    print(f"[done] log written to: {os.path.abspath(log_path)}")


if __name__ == "__main__":
    main()
