#!/usr/bin/env python3
"""
scan_pt_time_by_event.py

One-stop debug script (LOGGING EDITION):
  - Reads TrackState.time (your pT convention; may be invalid sentinel)
  - Reads TrackState.omega (q/pT convention => pT = 1/|omega|)
  - For the primary track in each event, ALSO computes geometry observability:
      * chordXY_mm
      * circle-fit condition estimate "cond" (SVD smax/smin)
      * phiSpan (unwrapped) around fitted circle center
      * sagitta_mm (middle point to chord, XY)
      * curvObservable (based on thresholds)

NEW in this revision:
  - Robust logging to a .log file (optional stdout mirror)
  - Prefer TrackStates_AtIP if present
  - Diagnostics:
      * Predicted omega for fixed mu-: omega ≈ -1/pT (GeV^-1)
      * Track/TrackState structure checks (states per track, multiple tracks per event)
      * Omega sign-mixing checks within tracks
      * Time validity/negativity summary
      * Optional MCParticles.PDG sanity check (to catch accidental mu+)

Usage:
  python3 scan_pt_time_by_event.py --input reco.root --expectedPt 20
  python3 scan_pt_time_by_event.py --input reco.root --expectedPt 20 --top 30 --type bad --metric rel
  python3 scan_pt_time_by_event.py --input reco.root --expectedPt 20 --event 718 --dumpStates 30 --dumpHits 40 --verbose

Logging:
  --log mydebug.log         # write all diagnostics here
  --stdout                 # also echo log lines to terminal
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

    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

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

def _median(vals):
    vals = [v for v in vals if _finite(v)]
    if not vals:
        return float("nan")
    vals.sort()
    return vals[len(vals)//2]

def _scan_leaf_by_suffix(tree, coll_name, suffix):
    leaves = tree.GetListOfLeaves()
    if not leaves:
        return None
    for obj in leaves:
        nm = obj.GetName()
        if coll_name in nm and nm.endswith(suffix):
            return nm
    return None

def _list_leaves(tree):
    leaves = tree.GetListOfLeaves()
    if not leaves:
        return []
    return [obj.GetName() for obj in leaves]

def _prefix_for_collection(tree, coll_name, required_suffix):
    """Try to find a leaf name containing coll_name and ending with required_suffix; return prefix up to suffix."""
    for nm in _list_leaves(tree):
        if coll_name in nm and nm.endswith(required_suffix):
            return nm[:-len(required_suffix)]
    return None


# ---------------- resolve TrackState leaves ----------------

def resolve_ts_prefix(tree, coll_name):
    """
    Prefer AtIP states if they exist (this avoids mixing AtIP vs other states).
    """
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

    # fallback: find any "<...>.phi" containing coll_name
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


# ---------------- resolve Track->Hits association ----------------

def resolve_track_hit_begin_end(tree, track_coll):
    """
    Try common EDM4hep/podio encodings for track->trackerHit association.
    """
    candidates = [
        (f"{track_coll}.trackerHits_begin", f"{track_coll}.trackerHits_end"),
        (f"{track_coll}.TrackerHits_begin", f"{track_coll}.TrackerHits_end"),
        (f"{track_coll}.hits_begin",        f"{track_coll}.hits_end"),
        (f"{track_coll}.Hits_begin",        f"{track_coll}.Hits_end"),
    ]
    for b, e in candidates:
        if _find_leaf(tree, b) and _find_leaf(tree, e):
            return b, e

    # fallback scan by suffix
    b = _scan_leaf_by_suffix(tree, track_coll, "trackerHits_begin")
    e = _scan_leaf_by_suffix(tree, track_coll, "trackerHits_end")
    if b and e:
        return b, e
    b = _scan_leaf_by_suffix(tree, track_coll, "hits_begin")
    e = _scan_leaf_by_suffix(tree, track_coll, "hits_end")
    if b and e:
        return b, e

    return None, None


def resolve_hit_pos_prefix(tree, hit_coll):
    """
    Find prefix for hit position leaves: prefix+"x" etc. (where prefix usually ends with 'position.')
    """
    candidates = [
        f"{hit_coll}.position.",
        f"{hit_coll}.Position.",
        f"_{hit_coll}_position.",
        f"_{hit_coll}_Position.",
    ]
    for pref in candidates:
        if _find_leaf(tree, pref + "x") and _find_leaf(tree, pref + "y"):
            return pref

    # fallback: find any leaf containing hit_coll and ending with "x" where also "y" exists
    pref = _prefix_for_collection(tree, hit_coll, "x")
    if pref and _find_leaf(tree, pref + "y"):
        return pref
    return None


def autodetect_hit_collection(tree):
    """
    Heuristic: look for common hit collections that have 'position.x' leaves.
    Returns best guess name or None.
    """
    leaves = _list_leaves(tree)
    guesses = ["GGTF_3DHits", "GGTF3DHits", "DCHHits", "DCHHits3D", "TrackerHits", "SiTrackerHits"]
    for g in guesses:
        if any((g in nm and nm.endswith("position.x")) for nm in leaves) or any((f"{g}.position.x" == nm) for nm in leaves):
            return g

    for nm in leaves:
        if nm.endswith("position.x"):
            parts = nm.split(".")
            if len(parts) >= 3:
                return parts[0]
    return None


# ---------------- optional truth sanity (MCParticles.PDG) ----------------

def resolve_mc_pdg_leaf(tree):
    """
    Best-effort: find MCParticles PDG leaf.
    Common forms:
      MCParticles.PDG
      MCParticles.pdg
      _MCParticles_PDG
    """
    candidates = [
        "MCParticles.PDG",
        "MCParticles.pdg",
        "_MCParticles_PDG",
        "_MCParticles_pdg",
    ]
    for c in candidates:
        lf = _find_leaf(tree, c)
        if lf:
            return c
    # fallback scan: contains MCParticles and endswith PDG/pdg
    for nm in _list_leaves(tree):
        if "MCParticles" in nm and (nm.endswith(".PDG") or nm.endswith(".pdg") or nm.endswith("_PDG") or nm.endswith("_pdg")):
            return nm
    return None


# ---------------- circle fit + observability (PyROOT-safe) ----------------

def fit_circle_ls_svd_xy(points_xy):
    """
    Fit x^2 + y^2 + D x + E y + F = 0  (LS)
    Returns: ok, cx, cy, R, cond, rmsResidual
    """
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

    phi = []
    for (x, y) in points_xy:
        phi.append(math.atan2(y - cy, x - cx))

    for i in range(1, n):
        d = phi[i] - phi[i-1]
        while d > math.pi:
            phi[i] -= 2.0*math.pi
            d = phi[i] - phi[i-1]
        while d < -math.pi:
            phi[i] += 2.0*math.pi
            d = phi[i] - phi[i-1]

    phiMin = min(phi)
    phiMax = max(phi)
    span = phiMax - phiMin
    return (True, phiMin, phiMax, span)


def chord_xy_mm(points_xyz_mm):
    if len(points_xyz_mm) < 2:
        return float("nan")
    (x0, y0, _) = points_xyz_mm[0]
    (x1, y1, _) = points_xyz_mm[-1]
    return math.hypot(x1 - x0, y1 - y0)


def sagitta_mm(points_xyz_mm):
    n = len(points_xyz_mm)
    if n < 3:
        return float("nan")
    (x0, y0, _) = points_xyz_mm[0]
    (xm, ym, _) = points_xyz_mm[n//2]
    (x1, y1, _) = points_xyz_mm[-1]

    dx = x1 - x0
    dy = y1 - y0
    denom = math.hypot(dx, dy)
    if denom < 1e-12:
        return float("nan")

    s = abs(dx*(y0 - ym) - dy*(x0 - xm)) / denom
    return s


# ---------------- main scan logic ----------------

def scan_file(path, track_coll, expected_pt, top_n=30, event_filter=None,
              verbose=False, invalid_time=-1.0, dump_states=0, dump_hits=0,
              hit_coll=None,
              min_phi_span=0.06, min_chord_xy_mm=500.0, max_circle_cond=1e6,
              logger=None,
              check_truth=True,
              assume_mu_minus=True):
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
    if not time_leaf:
        logger.warning("Leaf missing: %stime (your custom pT-in-time may not be present)", ts_prefix)
    if not omg_leaf:
        logger.warning("Leaf missing: %somega (cannot compute pT from omega)", ts_prefix)

    # Track->TrackStates association
    bname, ename = resolve_begin_end(tree, track_coll)
    beg_ts_leaf = _find_leaf(tree, bname) if bname else None
    end_ts_leaf = _find_leaf(tree, ename) if ename else None

    # Track->Hits association
    hbname, hename = resolve_track_hit_begin_end(tree, track_coll)
    beg_hit_leaf = _find_leaf(tree, hbname) if hbname else None
    end_hit_leaf = _find_leaf(tree, hename) if hename else None

    # Hit collection
    if hit_coll is None:
        hit_coll = autodetect_hit_collection(tree)
    hit_pos_pref = resolve_hit_pos_prefix(tree, hit_coll) if hit_coll else None
    hit_x_leaf = _find_leaf(tree, hit_pos_pref + "x") if hit_pos_pref else None
    hit_y_leaf = _find_leaf(tree, hit_pos_pref + "y") if hit_pos_pref else None
    hit_z_leaf = _find_leaf(tree, hit_pos_pref + "z") if hit_pos_pref else None

    have_hits = bool(beg_hit_leaf and end_hit_leaf and hit_x_leaf and hit_y_leaf)

    # Truth PDG sanity
    mc_pdg_name = resolve_mc_pdg_leaf(tree) if check_truth else None
    mc_pdg_leaf = _find_leaf(tree, mc_pdg_name) if mc_pdg_name else None

    # Expectations
    expected_pt = float(expected_pt)
    expected_omega_mag = (1.0/expected_pt) if expected_pt > 0 else float("nan")
    expected_omega = (-expected_omega_mag) if assume_mu_minus else expected_omega_mag

    logger.info("[file] %s", path)
    logger.info("[cfg] TrackColl=%s", track_coll)
    logger.info("[cfg] TrackState prefix=%s", ts_prefix)
    logger.info("[cfg] TrackStates assoc begin/end=%s %s (%s)", bname, ename, "OK" if (beg_ts_leaf and end_ts_leaf) else "MISSING")
    logger.info("[cfg] TrackHits assoc begin/end=%s %s (%s)", hbname, hename, "OK" if (beg_hit_leaf and end_hit_leaf) else "MISSING")
    logger.info("[cfg] HitColl=%s | hit pos prefix=%s | have_hits=%s", hit_coll, hit_pos_pref, have_hits)
    logger.info("[cfg] expectedPt=%.6g GeV -> expected omega ~ %.6g GeV^-1 (mu- assumption=%s)",
                expected_pt, expected_omega, str(assume_mu_minus))
    if mc_pdg_leaf:
        logger.info("[truth] MC PDG leaf=%s", mc_pdg_name)
    else:
        logger.info("[truth] MCParticles.PDG leaf not found (skipping truth PDG check)")

    logger.info("[cfg] Obs thresholds: minPhiSpan=%.4g rad  minChordXY=%.4g mm  maxCond=%.3g",
                min_phi_span, min_chord_xy_mm, max_circle_cond)

    def time_is_valid(t):
        return _finite(t) and (t != invalid_time) and (t > 0.0)

    n_ev = tree.GetEntries()
    results = []

    # global counters
    total_tracks = 0
    events_with_tracks = 0
    events_with_multitrack = 0
    events_with_multistate_per_track = 0
    events_with_omega_sign_mix_in_track = 0
    total_time_vals = 0
    total_time_invalid_or_nonpos = 0
    total_omega_vals = 0
    total_omega_nonfinite_or_zero = 0

    ev_range = range(n_ev) if event_filter is None else [event_filter]
    for iev in ev_range:
        tree.GetEntry(iev)

        # truth PDG summary (per-event)
        if mc_pdg_leaf:
            pdgs = [int(mc_pdg_leaf.GetValue(i)) for i in range(int(mc_pdg_leaf.GetNdata()))]
            if pdgs:
                # just log the first few, plus counts
                from collections import Counter
                c = Counter(pdgs)
                logger.debug("[ev %d][truth] MCParticles PDG counts: %s", iev, dict(c))

        n_states = int(phi_leaf.GetNdata())
        if n_states <= 0:
            continue

        # pull all state arrays (flat)
        time_vals = []
        if time_leaf:
            time_vals = [float(time_leaf.GetValue(i)) for i in range(n_states)]
            total_time_vals += len(time_vals)
            total_time_invalid_or_nonpos += sum(1 for t in time_vals if not time_is_valid(t))
        else:
            time_vals = [float("nan")] * n_states

        if omg_leaf:
            omg_vals = [float(omg_leaf.GetValue(i)) for i in range(n_states)]
            total_omega_vals += len(omg_vals)
            total_omega_nonfinite_or_zero += sum(1 for o in omg_vals if (not _finite(o) or abs(o) == 0.0))
        else:
            omg_vals = [float("nan")] * n_states

        ptomg_vals = []
        for o in omg_vals:
            if _finite(o) and abs(o) > 0.0:
                ptomg_vals.append(1.0/abs(o))
            else:
                ptomg_vals.append(float("nan"))

        # event-level summaries
        time_valid = [t for t in time_vals if time_is_valid(t)]
        pt_time_med = _median(time_valid)
        pt_time_min = min(time_valid) if time_valid else float("nan")
        pt_time_max = max(time_valid) if time_valid else float("nan")
        n_time_valid = len(time_valid)

        ptomg_valid = [p for p in ptomg_vals if _finite(p)]
        pt_omg_med = _median(ptomg_valid)
        pt_omg_min = min(ptomg_valid) if ptomg_valid else float("nan")
        pt_omg_max = max(ptomg_valid) if ptomg_valid else float("nan")

        # per-track summaries (state + optional observability)
        per_track = []
        n_tracks = int(beg_ts_leaf.GetNdata()) if (beg_ts_leaf and end_ts_leaf) else 0
        if n_tracks > 0:
            events_with_tracks += 1
            total_tracks += n_tracks
            if n_tracks > 1:
                events_with_multitrack += 1

        for ti in range(n_tracks) if n_tracks > 0 else []:
            bts = int(beg_ts_leaf.GetValue(ti))
            ets = int(end_ts_leaf.GetValue(ti))
            if bts < 0 or ets < 0 or ets <= bts or bts >= n_states:
                continue
            ets = min(ets, n_states)
            nseg = ets - bts
            if nseg > 1:
                events_with_multistate_per_track = events_with_multistate_per_track + 1  # event-level counter later guarded

            # within-track omega sign mix check
            seg_omg_raw = [omg_vals[k] for k in range(bts, ets) if _finite(omg_vals[k]) and abs(omg_vals[k]) > 0.0]
            if seg_omg_raw:
                has_pos = any(o > 0 for o in seg_omg_raw)
                has_neg = any(o < 0 for o in seg_omg_raw)
                if has_pos and has_neg:
                    events_with_omega_sign_mix_in_track = events_with_omega_sign_mix_in_track + 1

            seg_time = [time_vals[k] for k in range(bts, ets) if time_is_valid(time_vals[k])]
            seg_ptomg = [ptomg_vals[k] for k in range(bts, ets) if _finite(ptomg_vals[k])]
            pt_t = _median(seg_time)
            pt_o = _median(seg_ptomg)

            # observability defaults
            phi_span = float("nan")
            chord = float("nan")
            cond = float("nan")
            circle_ok = False
            curv_obs = False
            sag = float("nan")
            rms = float("nan")

            if have_hits:
                bh = int(beg_hit_leaf.GetValue(ti))
                eh = int(end_hit_leaf.GetValue(ti))
                n_hits_tot = int(hit_x_leaf.GetNdata())
                if bh >= 0 and eh > bh and bh < n_hits_tot:
                    eh = min(eh, n_hits_tot)

                    hits_xyz = []
                    for hi in range(bh, eh):
                        x = float(hit_x_leaf.GetValue(hi))
                        y = float(hit_y_leaf.GetValue(hi))
                        z = float(hit_z_leaf.GetValue(hi)) if hit_z_leaf else 0.0
                        hits_xyz.append((x, y, z))

                    if len(hits_xyz) >= 3:
                        chord = chord_xy_mm(hits_xyz)
                        sag = sagitta_mm(hits_xyz)

                        pts_xy = [(x, y) for (x, y, _) in hits_xyz]
                        okc, cx, cy, R, cond_est, rms_res = fit_circle_ls_svd_xy(pts_xy)
                        circle_ok = bool(okc)
                        cond = cond_est
                        rms = rms_res

                        if okc and _finite(cx) and _finite(cy) and _finite(cond_est):
                            okp, _, _, span = unwrap_phi_span(pts_xy, cx, cy)
                            if okp:
                                phi_span = span

                        phi_ok = _finite(phi_span) and (phi_span >= min_phi_span)
                        chord_ok = _finite(chord) and (chord >= min_chord_xy_mm)
                        cond_ok = _finite(cond_est) and (cond_est <= max_circle_cond)
                        curv_obs = bool(okc and cond_ok and phi_ok and chord_ok)

            per_track.append((ti, pt_t, pt_o, bts, ets,
                              phi_span, chord, cond, curv_obs, sag, circle_ok, rms))

        # choose primary track:
        if per_track:
            # if you *expect* a fixed mu- gun, omega sign should mostly be negative.
            # But for pT magnitude comparison, pick the track closest to expected pT.
            def score(tt):
                _, pt_t, pt_o, *_ = tt
                if _finite(pt_t):
                    return abs(pt_t - expected_pt)
                if _finite(pt_o):
                    return abs(pt_o - expected_pt)
                return float("inf")
            primary = min(per_track, key=score)
            (ti, pt_primary_time, pt_primary_omg, bts, ets,
             phi_span, chord, cond, curv_obs, sag, circle_ok, rms) = primary
            assoc_note = f"track={ti} ts[{bts}:{ets})"
        else:
            ti = -1
            pt_primary_time = pt_time_med
            pt_primary_omg  = pt_omg_med
            assoc_note = "flatStates(median)"
            phi_span = chord = cond = sag = rms = float("nan")
            curv_obs = False
            circle_ok = False

        # ranking uses time if finite else omega
        if _finite(pt_primary_time):
            pt_for_rank = pt_primary_time
            rank_source = "time"
        elif _finite(pt_primary_omg):
            pt_for_rank = pt_primary_omg
            rank_source = "omega"
        else:
            continue

        abs_err = abs(pt_for_rank - expected_pt)
        rel_err = abs_err / expected_pt if expected_pt > 0 else float("inf")

        results.append({
            "event": iev,
            "rank_source": rank_source,
            "pt_primary_time": pt_primary_time,
            "pt_primary_omega": pt_primary_omg,
            "abs_err": abs_err,
            "rel_err": rel_err,
            "n_states": n_states,
            "n_tracks": int(len(per_track)),
            "n_time_valid": n_time_valid,
            "pt_time_min": pt_time_min,
            "pt_time_med": pt_time_med,
            "pt_time_max": pt_time_max,
            "pt_omg_min": pt_omg_min,
            "pt_omg_med": pt_omg_med,
            "pt_omg_max": pt_omg_max,
            # observability
            "phiSpan": phi_span,
            "chordXY_mm": chord,
            "circleCond": cond,
            "circleOK": int(bool(circle_ok)),
            "rmsAlgRes": rms,
            "sagitta_mm": sag,
            "curvObservable": int(bool(curv_obs)),
            "assoc": assoc_note,
        })

        if verbose:
            logger.info(
                "[ev %5d] src=%4s pT_time=%10.3f pT_omg=%10.3f absErr=%9.3f relErr=%8.3f "
                "nTracks=%2d nStates=%3d nTimeV=%3d phiSpan=%8.4f chordXYmm=%8.1f cond=%9.3g curvObs=%d "
                "sagitta=%7.3f rmsAlgRes=%9.3g %s",
                iev, rank_source, pt_primary_time, pt_primary_omg, abs_err, rel_err,
                int(len(per_track)), n_states, n_time_valid,
                phi_span, chord, cond, int(curv_obs), sag, rms, assoc_note
            )

        # deep dumps for a single event
        if dump_states and event_filter is not None:
            n_dump = min(int(dump_states), n_states)
            logger.info("[dump] event %d first %d/%d TrackStates under prefix '%s'", iev, n_dump, n_states, ts_prefix)
            logger.info("%4s %12s %12s %12s %10s", "i", "time", "omega", "1/|omega|", "time_valid")
            for si in range(n_dump):
                t = time_vals[si]
                o = omg_vals[si]
                po = ptomg_vals[si]
                tv = "yes" if time_is_valid(t) else "no"
                logger.info("%4d %12.4f %12.4e %12.4f %10s", si, t, o, po, tv)

        if dump_hits and event_filter is not None and have_hits and ti >= 0:
            bh = int(beg_hit_leaf.GetValue(ti))
            eh = int(end_hit_leaf.GetValue(ti))
            n_hits_tot = int(hit_x_leaf.GetNdata())
            if bh >= 0 and eh > bh and bh < n_hits_tot:
                eh = min(eh, n_hits_tot)
                n_dump = min(int(dump_hits), eh - bh)
                logger.info("[dump] event %d track %d first %d/%d hits from '%s'", iev, ti, n_dump, eh-bh, hit_coll)
                logger.info("%4s %12s %12s %12s %12s", "i", "x(mm)", "y(mm)", "z(mm)", "r(mm)")
                for j in range(n_dump):
                    hi = bh + j
                    x = float(hit_x_leaf.GetValue(hi))
                    y = float(hit_y_leaf.GetValue(hi))
                    z = float(hit_z_leaf.GetValue(hi)) if hit_z_leaf else 0.0
                    r = math.hypot(x, y)
                    logger.info("%4d %12.3f %12.3f %12.3f %12.3f", j, x, y, z, r)

    f.Close()

    # summarize diagnostics
    scanned = len(list(ev_range))
    logger.info("---- GLOBAL DIAGNOSTIC SUMMARY ----")
    logger.info("events scanned: %d (tree entries=%d)", scanned, n_ev)
    logger.info("events with >=1 track: %d", events_with_tracks)
    logger.info("total tracks (across scanned events): %d", total_tracks)
    logger.info("events with >1 track: %d", events_with_multitrack)
    # note: the two counters below are incremented per track; treat as "occurrences", not strict event counts
    logger.info("occurrences of tracks with >1 TrackState in slice: %d (note: per-track count)", events_with_multistate_per_track)
    logger.info("occurrences of omega sign-mixing within a track slice: %d (note: per-track count)", events_with_omega_sign_mix_in_track)

    if total_time_vals > 0:
        frac_bad_time = total_time_invalid_or_nonpos / float(total_time_vals)
        logger.info("TrackState.time: total=%d invalid_or_nonpos=%d frac=%.3f",
                    total_time_vals, total_time_invalid_or_nonpos, frac_bad_time)
    else:
        logger.info("TrackState.time: not present / not read")

    if total_omega_vals > 0:
        frac_bad_omega = total_omega_nonfinite_or_zero / float(total_omega_vals)
        logger.info("TrackState.omega: total=%d nonfinite_or_zero=%d frac=%.3f",
                    total_omega_vals, total_omega_nonfinite_or_zero, frac_bad_omega)
        logger.info("Expected omega (mu- assumption): ~ %.6g GeV^-1 (for expectedPt=%.6g)", expected_omega, expected_pt)
    else:
        logger.info("TrackState.omega: not present / not read")

    return results, n_ev, scanned


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


def main():
    ap = argparse.ArgumentParser(description="Scan TrackState.time/omega + observability + diagnostics (logs to file).")
    ap.add_argument("--input", required=True, help="Input EDM4hep ROOT file")
    ap.add_argument("--trackCollection", default="GenFitTracks", help="Track collection name (default: GenFitTracks)")
    ap.add_argument("--hitCollection", default="GGTF_3DHits",
                    help="Hit collection to use for observability (use 'auto' to autodetect)")
    ap.add_argument("--expectedPt", type=float, required=True, help="Expected pT for this sample [GeV]")

    ap.add_argument("--top", type=int, default=30, help="How many events to show in final summary table (default: 30)")
    ap.add_argument("--event", type=int, default=None, help="If set, scan only this event index")
    ap.add_argument("--csv", default=None, help="Optional output CSV with per-event results")

    ap.add_argument("--verbose", action="store_true", help="Log one line per event (can be big)")
    ap.add_argument("--dumpStates", type=int, default=0,
                    help="If --event is set, dump first N TrackStates (time/omega) for that event")
    ap.add_argument("--dumpHits", type=int, default=0,
                    help="If --event is set, dump first N hits for the chosen primary track")

    ap.add_argument("--invalidTime", type=float, default=-1.0,
                    help="Invalid pT sentinel stored in TrackState.time (default: -1)")

    ap.add_argument("--minPhiSpan", type=float, default=0.06,
                    help="Curvature observability threshold: min phiSpan (rad)")
    ap.add_argument("--minChordXY", type=float, default=500.0,
                    help="Curvature observability threshold: min chordXY in mm")
    ap.add_argument("--maxCircleCond", type=float, default=1e6,
                    help="Circle-fit condition threshold (SVD smax/smin)")

    ap.add_argument("--type", choices=["bad", "good"], default="bad",
                    help="Ranking type: 'bad' = largest error, 'good' = smallest error (default: bad)")
    ap.add_argument("--metric", choices=["abs", "rel"], default="abs",
                    help="Sort metric: abs=|pT-expected|, rel=|pT-expected|/expected (default: abs)")

    # logging controls
    ap.add_argument("--log", default="",
                    help="Log file path. Default: <input_basename>.scan_pt.log in CWD")
    ap.add_argument("--stdout", action="store_true",
                    help="Also print INFO-level logs to terminal (otherwise log-only)")

    # truth/sign assumptions
    ap.add_argument("--no-truthCheck", dest="truthCheck", action="store_false", default=True,
                    help="Disable MCParticles.PDG sanity check")
    ap.add_argument("--assumeMuonMinus", dest="assumeMuonMinus", action="store_true", default=True,
                    help="Assume gun is mu- so expected omega sign is negative (default True)")
    ap.add_argument("--assumeMuonPlus", dest="assumeMuonMinus", action="store_false",
                    help="Assume mu+ (expected omega positive)")

    args = ap.parse_args()

    log_path = args.log.strip()
    if not log_path:
        base = os.path.basename(args.input)
        base = base.replace(".root", "")
        log_path = f"{base}.scan_pt.log"

    logger = setup_logger(log_path, also_stdout=bool(args.stdout))

    hit_coll = None if (args.hitCollection.strip().lower() == "auto") else args.hitCollection

    results, n_ev, n_scanned = scan_file(
        args.input,
        args.trackCollection,
        args.expectedPt,
        top_n=args.top,
        event_filter=args.event,
        verbose=args.verbose,
        invalid_time=args.invalidTime,
        dump_states=args.dumpStates,
        dump_hits=args.dumpHits,
        hit_coll=hit_coll,
        min_phi_span=args.minPhiSpan,
        min_chord_xy_mm=args.minChordXY,
        max_circle_cond=args.maxCircleCond,
        logger=logger,
        check_truth=bool(args.truthCheck),
        assume_mu_minus=bool(args.assumeMuonMinus),
    )

    if not results:
        logger.warning("scanned %d event(s) (file has %d events) but found no usable TrackStates.", n_scanned, n_ev)
        # still tell user where the log is
        print(f"[done] log written to: {os.path.abspath(log_path)}")
        return

    key = "abs_err" if args.metric == "abs" else "rel_err"
    reverse = True if args.type == "bad" else False
    results.sort(key=lambda r: r[key], reverse=reverse)

    n_show = min(args.top, len(results))
    label = "worst" if args.type == "bad" else "best"
    metric_label = "|pT-expected|" if args.metric == "abs" else "|pT-expected|/expected"

    logger.info("")
    logger.info("[summary] scanned %d event(s) (file has %d events)", n_scanned, n_ev)
    logger.info("[summary] expectedPt = %.6g GeV", args.expectedPt)
    logger.info("[summary] showing top %d %s events by %s", n_show, label, metric_label)

    header = (f"{'rank':>4s} {'event':>6s} {'src':>4s} "
              f"{'pT_time':>10s} {'pT_omg':>10s} "
              f"{'absErr':>9s} {'relErr':>8s} "
              f"{'phiSpan':>8s} {'chordXY':>8s} {'cond':>9s} {'curv':>4s} {'sag':>7s}  assoc")
    logger.info(header)
    for i, r in enumerate(results[:n_show], 1):
        logger.info(
            f"{i:4d} {r['event']:6d} {r['rank_source']:>4s} "
            f"{r['pt_primary_time']:10.2f} {r['pt_primary_omega']:10.2f} "
            f"{r['abs_err']:9.2f} {r['rel_err']:8.3f} "
            f"{r['phiSpan']:8.4f} {r['chordXY_mm']:8.1f} {r['circleCond']:9.3g} "
            f"{r['curvObservable']:4d} {r['sagitta_mm']:7.3f}  {r['assoc']}"
        )

    if args.csv:
        write_csv(results, args.csv, logger)

    # always print where the log went (even if --stdout was not used)
    print(f"[done] log written to: {os.path.abspath(log_path)}")


if __name__ == "__main__":
    main()
