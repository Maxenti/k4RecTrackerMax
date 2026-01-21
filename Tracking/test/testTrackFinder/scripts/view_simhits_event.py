#!/usr/bin/env python3
"""
view_tracks_event_simhits.py

Multi-event visualizer for:
  - GGTF SenseWireHits (or any hit collection with position.{x,y,z} and optional .type)
  - optional DCH SimTrackerHits (simhits) overlay
  - GenFitTracks TrackStates (draw helix/straight in uniform Bz)

NEW: Top-N event selection by sigma(pT) at an expected pT.
  - For each event, compute an event-level sigma(pT) using TrackState covariance:
        sigma(pT)/pT ≈ sigma(omega)/|omega|   with omega = q/pT
    so:
        sigma(pT) ≈ expectedPt * sqrt(Var(omega)) / |q/expectedPt|
                  = expectedPt^2 * sqrt(Var(omega)) / |q|
    (uses expectedPt to avoid relying on TrackState.time semantics)
  - Rank events by this sigma(pT) (default: largest sigma(pT))
  - Process the top N events and write each event into its own directory in ONE output ROOT file:
        event_000012/
        event_000834/
        ...

Notes on covariance:
  - EDM4hep TrackState covariance is 6x6 packed (d0,phi,omega,z0,tanLambda,time).
  - We read Var(omega) from the packed lower-triangle:
        idx(omega,omega) = idx(2,2) = 5  (for 6x6 lower-tri packed)

Examples:
  # Single event
  python3 view_tracks_event_simhits.py --input reco.root --event 12

  # Top 10 events by sigma(pT) at expectedPt=14.142 GeV
  python3 view_tracks_event_simhits.py --input reco.root --topN 10 --expectedPt 14.142

  # Limit scan to first 5000 events
  python3 view_tracks_event_simhits.py --input reco.root --topN 25 --expectedPt 50 --scanMaxEvents 5000

  # Sort smallest sigma(pT) instead (best fits)
  python3 view_tracks_event_simhits.py --input reco.root --topN 10 --expectedPt 14.142 --rankOrder smallest

  # If your omega is for mu- (q=-1), set assumeQ=-1
  python3 view_tracks_event_simhits.py --input reco.root --topN 10 --expectedPt 14.142 --assumeQ -1

Author: ChatGPT (adapted for your FCC-ee IDEA DCH workflow)
"""

import math
import argparse
import os
import sys
import socket
import getpass
import time
from collections import defaultdict

import ROOT
ROOT.gROOT.SetBatch(True)


# ------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------
def _find_leaf(tree, name):
    return tree.GetLeaf(name)


def _leaf_exists(tree, name):
    return bool(_find_leaf(tree, name))


def _scan_leaf_by_suffix(tree, coll_name, suffix):
    leaves = tree.GetListOfLeaves()
    if not leaves:
        return None
    for obj in leaves:
        nm = obj.GetName()
        if coll_name in nm and nm.endswith(suffix):
            return nm
    return None


def _resolve_begin_end_leaves(tree, coll_name):
    candidates = [
        (f"{coll_name}.trackStates_begin", f"{coll_name}.trackStates_end"),
        (f"{coll_name}.TrackStates_begin", f"{coll_name}.TrackStates_end"),
        (f"_{coll_name}_trackStates_begin", f"_{coll_name}_trackStates_end"),
        (f"_{coll_name}_TrackStates_begin", f"_{coll_name}_TrackStates_end"),
    ]
    for bname, ename in candidates:
        if _find_leaf(tree, bname) and _find_leaf(tree, ename):
            return bname, ename

    for sufB, sufE in [("trackStates_begin", "trackStates_end"),
                       ("TrackStates_begin", "TrackStates_end")]:
        bname = _scan_leaf_by_suffix(tree, coll_name, sufB)
        ename = _scan_leaf_by_suffix(tree, coll_name, sufE)
        if bname and ename:
            return bname, ename

        bname = _scan_leaf_by_suffix(tree, f"_{coll_name}_", sufB)
        ename = _scan_leaf_by_suffix(tree, f"_{coll_name}_", sufE)
        if bname and ename:
            return bname, ename

    return None, None


def resolve_ts_prefix(tree, coll_name):
    candidates = [
        f"{coll_name}.trackStates.",
        f"{coll_name}.TrackStates.",
        f"{coll_name}.trackStates_AtIP.",
        f"{coll_name}.TrackStates_AtIP.",
        f"_{coll_name}_trackStates.",
        f"_{coll_name}_TrackStates.",
        f"_{coll_name}_trackStates_AtIP.",
        f"_{coll_name}_TrackStates_AtIP.",
        f"{coll_name}TrackStates.",
        f"_{coll_name}TrackStates.",
    ]

    for pref in candidates:
        lf = _find_leaf(tree, pref + "phi")
        if lf:
            print(f"[info] Using TrackState prefix '{pref}' (found '{pref}phi').")
            return pref

    leaves = tree.GetListOfLeaves()
    if not leaves:
        return None

    for obj in leaves:
        name = obj.GetName()
        if coll_name in name and name.endswith(".phi"):
            pref = name[:-len("phi")]
            print(f"[info] Using TrackState prefix '{pref}' (auto-detected from '{name}').")
            return pref

    print(f"[warn] Could not resolve TrackState prefix for '{coll_name}'.")
    return None


def _collection_has_xyz(tree, coll_name):
    return (_leaf_exists(tree, f"{coll_name}.position.x") and
            _leaf_exists(tree, f"{coll_name}.position.y") and
            _leaf_exists(tree, f"{coll_name}.position.z"))


def _auto_detect_hits_collection(tree, preferred=None):
    if preferred and _collection_has_xyz(tree, preferred):
        return preferred

    leaves = tree.GetListOfLeaves()
    if not leaves:
        return None

    candidates = set()
    for obj in leaves:
        nm = obj.GetName()
        if nm.endswith(".position.x"):
            base = nm[:-len(".position.x")]
            candidates.add(base)

    if not candidates:
        return None

    scored = []
    for base in sorted(candidates):
        has_type = _leaf_exists(tree, f"{base}.type")
        score = 0
        if "GGTF" in base:
            score -= 10
        if "SenseWire" in base or "Wire" in base:
            score -= 5
        if has_type:
            score -= 3
        score += len(base) * 0.001
        scored.append((score, base, has_type))

    scored.sort(key=lambda t: t[0])
    best = scored[0][1]
    print("[info] Auto-detected hits collection:")
    for i, (sc, base, has_type) in enumerate(scored[:10]):
        print(f"   cand[{i}] {base} (has .type={has_type}) score={sc:.3g}")
    print(f"[info] Using hits collection = '{best}'")
    return best


# ------------------------------------------------------------
# Covariance utilities (EDM4hep TrackState covMatrix.values packed lower-triangle)
# ------------------------------------------------------------
def packed_lower_index(i, j):
    """
    Lower-triangle packed index for NxN symmetric matrix, row-major by i:
      (0,0),
      (1,0),(1,1),
      (2,0),(2,1),(2,2), ...
    """
    if i < j:
        i, j = j, i
    return i * (i + 1) // 2 + j


def infer_packed_n_from_len(L):
    # solve n(n+1)/2 = L
    disc = 1 + 8 * L
    if disc <= 0:
        return None
    n = int(round((-1 + math.sqrt(disc)) / 2))
    if n * (n + 1) // 2 == L:
        return n
    return None


def get_event_varomega(tree, ev_idx, track_coll="GenFitTracks", track_state_pick="atip", assume_q=-1):
    """
    Return (varOmega, omegaUsed, ptReco, details_dict) for event.
    Picks ONE representative TrackState for the event:
      - if trackStates_begin/end exist and >=1 track: pick first track's "best" AtIP-like state (min r2)
      - else pick first TrackState entry.
    Reads omega and Var(omega) from covMatrix.values.

    varOmega is returned as float('nan') if cannot be computed.
    """

    prefix = resolve_ts_prefix(tree, track_coll)
    if not prefix:
        return float("nan"), float("nan"), float("nan"), {"reason": "no_trackstate_prefix"}

    # Leaves needed
    phi_leaf = _find_leaf(tree, prefix + "phi")
    omg_leaf = _find_leaf(tree, prefix + "omega")
    cov_leaf = _find_leaf(tree, prefix + "covMatrix.values")
    if not (phi_leaf and omg_leaf and cov_leaf):
        return float("nan"), float("nan"), float("nan"), {"reason": "missing_phi_omega_or_cov"}

    # Ref point for r^2 selection if available
    refx_leaf = _find_leaf(tree, prefix + "referencePoint.x")
    refy_leaf = _find_leaf(tree, prefix + "referencePoint.y")
    d0_leaf   = _find_leaf(tree, prefix + "D0")

    # Track association (optional)
    bname, ename = _resolve_begin_end_leaves(tree, track_coll)
    beg_leaf = _find_leaf(tree, bname) if bname else None
    end_leaf = _find_leaf(tree, ename) if ename else None

    tree.GetEntry(ev_idx)

    n_states = int(phi_leaf.GetNdata())
    if n_states <= 0:
        return float("nan"), float("nan"), float("nan"), {"reason": "no_trackstates"}

    # Determine state index to use
    state_index = 0
    track_index = None
    if beg_leaf and end_leaf and int(beg_leaf.GetNdata()) > 0:
        # pick first track, then pick AtIP-like state in its [b,e) range
        track_index = 0
        b = int(beg_leaf.GetValue(track_index))
        e = int(end_leaf.GetValue(track_index))
        if b < 0 or e <= b or b >= n_states:
            state_index = 0
        else:
            e = min(e, n_states)
            # choose min r^2 among that track's states
            best_si = b
            best_r2 = float("inf")
            for si in range(b, e):
                if refx_leaf and refy_leaf:
                    x0 = float(refx_leaf.GetValue(si))
                    y0 = float(refy_leaf.GetValue(si))
                else:
                    # derive rough x0,y0 from d0 if possible; otherwise 0
                    if d0_leaf:
                        d0 = float(d0_leaf.GetValue(si))
                        phi = float(phi_leaf.GetValue(si))
                        x0 = -d0 * math.sin(phi)
                        y0 =  d0 * math.cos(phi)
                    else:
                        x0 = y0 = 0.0
                r2 = x0*x0 + y0*y0
                if r2 < best_r2:
                    best_r2 = r2
                    best_si = si
            state_index = best_si
    else:
        state_index = 0

    omega = float(omg_leaf.GetValue(state_index))

    # covMatrix.values is a flat array; for podio it flattens per-state arrays too.
    # BUT in your files you observed covLeaf.GetLen()==21 with 1 state => cov values start at offset 0.
    # If multiple states exist, podio usually stores them concatenated: [state0...][state1...]
    cov_len_total = int(cov_leaf.GetLen())
    # infer per-state len by dividing by n_states if divisible; else fall back to cov_len_total for 1-state case
    per_state_len = None
    if cov_len_total % n_states == 0:
        per_state_len = cov_len_total // n_states
    else:
        # common: the covariance leaf stores only for the chosen TrackState branch (often one per track),
        # but safest fallback is: assume per-state packed 21 (6x6) if possible.
        if cov_len_total in (21, 15):
            per_state_len = cov_len_total
        else:
            # last resort: treat as single state
            per_state_len = cov_len_total

    n_packed = infer_packed_n_from_len(per_state_len)
    if n_packed is None:
        return float("nan"), omega, float("nan"), {
            "reason": "unknown_cov_packing",
            "cov_len_total": cov_len_total,
            "n_states": n_states,
            "per_state_len": per_state_len,
        }

    # omega parameter index is 2 for (d0,phi,omega,z0,tanLambda,time)
    if n_packed < 3:
        return float("nan"), omega, float("nan"), {"reason": "cov_n_too_small", "n": n_packed}

    idx_oo = packed_lower_index(2, 2)
    if idx_oo >= per_state_len:
        return float("nan"), omega, float("nan"), {"reason": "idx_out_of_range", "idx": idx_oo, "per_state_len": per_state_len}

    offset = state_index * per_state_len
    if offset + idx_oo >= cov_len_total:
        return float("nan"), omega, float("nan"), {"reason": "offset_out_of_range", "offset": offset, "cov_len_total": cov_len_total}

    var_omega = float(cov_leaf.GetValue(offset + idx_oo))

    # "reco pT" just from omega (not from time)
    pt_reco = (abs(float(assume_q)) / abs(omega)) if (math.isfinite(omega) and abs(omega) > 0.0) else float("nan")

    return var_omega, omega, pt_reco, {
        "state_index": state_index,
        "track_index": track_index,
        "n_states_total": n_states,
        "cov_len_total": cov_len_total,
        "per_state_len": per_state_len,
        "cov_n": n_packed,
        "idx_varomega": idx_oo,
        "offset": offset,
    }


def sigma_pt_from_varomega(expected_pt, var_omega, assume_q=-1):
    """
    Using omega = q/pT and sigma(pT)/pT ≈ sigma(omega)/|omega|,

    with omega_expected = q/expectedPt:
      sigma(pT) ≈ expectedPt * sqrt(var_omega) / |omega_expected|
               = expectedPt * sqrt(var_omega) / (|q|/expectedPt)
               = expectedPt^2 * sqrt(var_omega) / |q|

    Returns nan if cannot compute.
    """
    if not (math.isfinite(expected_pt) and expected_pt > 0):
        return float("nan")
    if not (math.isfinite(var_omega) and var_omega >= 0):
        return float("nan")
    qabs = abs(int(assume_q)) if assume_q != 0 else 1
    return (expected_pt * expected_pt * math.sqrt(var_omega)) / float(qabs)


# ------------------------------------------------------------
# Load labeled hits
# ------------------------------------------------------------
def load_labeled_hits(tree, ev_idx, coll_name):
    tracks = defaultdict(list)

    x_leaf = _find_leaf(tree, f"{coll_name}.position.x")
    y_leaf = _find_leaf(tree, f"{coll_name}.position.y")
    z_leaf = _find_leaf(tree, f"{coll_name}.position.z")
    if not (x_leaf and y_leaf and z_leaf):
        raise RuntimeError(
            f"Could not find required leaves for '{coll_name}'.\n"
            f"Expected: {coll_name}.position.x/y/z"
        )

    tree.GetEntry(ev_idx)
    n_hits = int(x_leaf.GetNdata())
    print(f"[info] {coll_name}: event={ev_idx} nHits={n_hits}")

    type_leaf = _find_leaf(tree, f"{coll_name}.type")
    if type_leaf:
        print(f"[info] Found label leaf '{coll_name}.type'")
    else:
        print(f"[info] No label leaf '{coll_name}.type'; defaulting all labels to 0")

    for i in range(n_hits):
        x = float(x_leaf.GetValue(i))
        y = float(y_leaf.GetValue(i))
        z = float(z_leaf.GetValue(i))
        lbl = int(type_leaf.GetValue(i)) if type_leaf else 0
        tracks[lbl].append((x, y, z))

    return tracks


def load_simhit_positions(tree, ev_idx, coll_name="DCHCollection"):
    x_leaf = _find_leaf(tree, f"{coll_name}.position.x")
    y_leaf = _find_leaf(tree, f"{coll_name}.position.y")
    z_leaf = _find_leaf(tree, f"{coll_name}.position.z")
    if not (x_leaf and y_leaf and z_leaf):
        print(f"[info] No simhit position leaves found for '{coll_name}'; skipping simhit overlay.")
        return []

    tree.GetEntry(ev_idx)
    n = int(x_leaf.GetNdata())
    print(f"[info] {coll_name}: event={ev_idx} nSimHits={n}")

    pts = []
    for i in range(n):
        pts.append((float(x_leaf.GetValue(i)),
                    float(y_leaf.GetValue(i)),
                    float(z_leaf.GetValue(i))))
    return pts


# ------------------------------------------------------------
# TrackStates per TRACK (unchanged visual selection)
# ------------------------------------------------------------
def load_track_states(tree, ev_idx, coll_name="GenFitTracks", assume_q=1):
    prefix = resolve_ts_prefix(tree, coll_name)
    if not prefix:
        print(f"[warn] No valid TrackState prefix for '{coll_name}'; no tracks will be drawn.")
        return []

    bname, ename = _resolve_begin_end_leaves(tree, coll_name)
    if not (bname and ename):
        print(f"[warn] Could not find '{coll_name}.trackStates_begin/end' (or equivalent).")
        print("       Falling back to interpreting TrackStates as a flat array (less reliable).")
    else:
        print(f"[info] Using Track->TrackState association via begin/end leaves:")
        print(f"       begin='{bname}', end='{ename}'")

    def leaf(name):
        return _find_leaf(tree, name)

    d0_leaf   = leaf(prefix + "D0")
    z0_leaf   = leaf(prefix + "Z0")
    phi_leaf  = leaf(prefix + "phi")
    omg_leaf  = leaf(prefix + "omega")
    tl_leaf   = leaf(prefix + "tanLambda")
    time_leaf = leaf(prefix + "time")

    refx_leaf = leaf(prefix + "referencePoint.x")
    refy_leaf = leaf(prefix + "referencePoint.y")
    refz_leaf = leaf(prefix + "referencePoint.z")

    if not (phi_leaf and tl_leaf):
        print(f"[warn] Missing required TrackState leaves (phi/tanLambda) for '{coll_name}'.")
        return []

    beg_leaf = _find_leaf(tree, bname) if bname else None
    end_leaf = _find_leaf(tree, ename) if ename else None

    tree.GetEntry(ev_idx)

    n_states_total = int(phi_leaf.GetNdata())
    print(f"[info] {coll_name}: event={ev_idx} nTrackStates(total)={n_states_total}")

    flat_states = []
    for si in range(n_states_total):
        d0   = float(d0_leaf.GetValue(si))   if d0_leaf   else float("nan")
        z0   = float(z0_leaf.GetValue(si))   if z0_leaf   else float("nan")
        phi  = float(phi_leaf.GetValue(si))
        omg  = float(omg_leaf.GetValue(si))  if omg_leaf  else float("nan")
        tl   = float(tl_leaf.GetValue(si))
        pTt  = float(time_leaf.GetValue(si)) if time_leaf else float("nan")

        if refx_leaf and refy_leaf and refz_leaf:
            x0 = float(refx_leaf.GetValue(si))
            y0 = float(refy_leaf.GetValue(si))
            z0p = float(refz_leaf.GetValue(si))
        else:
            if math.isfinite(d0) and math.isfinite(z0):
                x0 = -d0 * math.sin(phi)
                y0 =  d0 * math.cos(phi)
                z0p = z0
            else:
                x0 = y0 = z0p = 0.0

        r2 = x0*x0 + y0*y0
        pt_from_omega = (abs(float(assume_q)) / abs(omg)) if (math.isfinite(omg) and abs(omg) > 0.0) else float("nan")

        flat_states.append({
            "state_index": si,
            "D0": d0,
            "Z0": z0,
            "phi": phi,
            "omega": omg,
            "tanLambda": tl,
            "pT_time": pTt,
            "pT_from_omega": pt_from_omega,
            "x0": x0,
            "y0": y0,
            "z0": z0p,
            "r2": r2,
        })

    per_track = []

    if beg_leaf and end_leaf:
        n_tracks = int(beg_leaf.GetNdata())
        print(f"[info] {coll_name}: event={ev_idx} nTracks={n_tracks}")

        for ti in range(n_tracks):
            b = int(beg_leaf.GetValue(ti))
            e = int(end_leaf.GetValue(ti))
            if b < 0 or e < 0 or e < b:
                continue
            if b >= n_states_total:
                continue
            e = min(e, n_states_total)

            states_this = flat_states[b:e]
            if not states_this:
                continue

            best = min(states_this, key=lambda st: st["r2"])
            best = dict(best)
            best["track_index"] = ti
            best["states_begin"] = b
            best["states_end"] = e
            best["n_states_in_track"] = (e - b)
            per_track.append(best)

            pt_t = best["pT_time"]
            pt_o = best["pT_from_omega"]
            omg  = best["omega"]
            mismatch = ""
            if math.isfinite(pt_t) and math.isfinite(pt_o) and pt_t > 0 and pt_o > 0:
                ratio = pt_t / pt_o
                if ratio > 2.0 or ratio < 0.5:
                    mismatch = f"  !!! mismatch pT(time)/pT(|q/omega|)={ratio:.3g} (ignore if time not pT)"
            print(
                f"[debug] Track[{ti}] states[{b}:{e}) pickState={best['state_index']} "
                f"x0={best['x0']:.2f} y0={best['y0']:.2f} z0={best['z0']:.2f} mm "
                f"phi={best['phi']:.3f} tanL={best['tanLambda']:.3f} "
                f"pT(time)={pt_t:.3f} GeV  pT(|q/omega|)={pt_o:.3f} GeV  omega={omg:.4e}"
                f"{mismatch}"
            )
    else:
        print("[warn] No begin/end association; treating each TrackState as standalone.")
        for st in flat_states:
            st = dict(st)
            st["track_index"] = st["state_index"]
            st["states_begin"] = st["state_index"]
            st["states_end"] = st["state_index"] + 1
            st["n_states_in_track"] = 1
            per_track.append(st)

    return per_track


def add_xy_track_overlay(c_xy, track_states, Bz):
    if not track_states:
        return []

    overlays = []
    c_xy.cd()

    nseg = 250
    for it, st in enumerate(track_states):
        x0 = st["x0"]; y0 = st["y0"]
        phi = st["phi"]
        omg = st["omega"]

        if (not math.isfinite(omg)) or abs(omg) == 0.0 or abs(Bz) == 0.0:
            ln = ROOT.TLine(x0, y0, x0 + 1000.0*math.cos(phi), y0 + 1000.0*math.sin(phi))
            ln.SetLineWidth(3)
            ln.SetLineStyle(2)
            ln.SetLineColor(ROOT.kBlack if it == 0 else ROOT.kGray + 2)
            ln.Draw("SAME")
            overlays.append(ln)
            continue

        R_m  = 1.0 / (abs(omg) * 0.3 * abs(Bz))
        R_mm = R_m * 1000.0
        sgn = 1.0 if (omg * Bz) > 0.0 else -1.0

        xc = x0 - sgn * R_mm * math.sin(phi)
        yc = y0 + sgn * R_mm * math.cos(phi)
        alpha0 = math.atan2(y0 - yc, x0 - xc)

        dAlpha = 0.8 if R_mm < 2e6 else 0.05

        pl = ROOT.TPolyLine(nseg)
        pl.SetLineWidth(3)
        pl.SetLineColor(ROOT.kBlue if it == 0 else ROOT.kYellow + 1)

        for i in range(nseg):
            a = alpha0 - dAlpha + (2*dAlpha) * i / (nseg - 1)
            x = xc + R_mm * math.cos(a)
            y = yc + R_mm * math.sin(a)
            pl.SetPoint(i, x, y)

        pl.Draw("SAME")
        overlays.append(pl)

    return overlays


# ------------------------------------------------------------
# Plot builder (now supports writing into an existing file + per-event directory)
# ------------------------------------------------------------
def make_plots(tracks_by_label,
               simhit_points,
               out_root,
               title_prefix="GGTF_SenseWireHits",
               track_states=None,
               track_style="helix",
               Bz=2.0,
               meta_info=None,
               out_file=None,
               out_dir_name=None):
    all_points = []
    for pts in tracks_by_label.values():
        all_points.extend(pts)
    all_points.extend(simhit_points)

    if not all_points:
        print("[warn] No 3D points (hits or simhits) found; nothing to plot.")
        return

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    zs = [p[2] for p in all_points]

    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)

    dx = max(1.0, 0.05 * (xmax - xmin if xmax > xmin else 1.0))
    dy = max(1.0, 0.05 * (ymax - ymin if ymax > ymin else 1.0))
    dz = max(1.0, 0.05 * (zmax - zmin if zmax > zmin else 1.0))

    xmin -= dx; xmax += dx
    ymin -= dy; ymax += dy
    zmin -= dz; zmax += dz

    created_local = False
    if out_file is None:
        out_file = ROOT.TFile(out_root, "RECREATE")
        created_local = True
        if not out_file or out_file.IsZombie():
            raise RuntimeError(f"Could not create output ROOT file: {out_root}")

    if out_dir_name:
        d = out_file.GetDirectory(out_dir_name)
        if not d:
            d = out_file.mkdir(out_dir_name)
        d.cd()
    else:
        out_file.cd()

    if meta_info is not None:
        meta_str = "\n".join(f"{k}: {v}" for k, v in meta_info.items())
        meta = ROOT.TNamed("view_tracks_metadata", meta_str)
        meta.Write()

    hit_points = []
    for pts in tracks_by_label.values():
        hit_points.extend(pts)

    if hit_points:
        h_xy = ROOT.TH2F("h_xy", f"{title_prefix};x [mm];y [mm]",
                         200, xmin, xmax, 200, ymin, ymax)

        r_values = [math.hypot(x, y) for (x, y, _) in hit_points]
        rmin = 0.0
        rmax = max(r_values) + 0.1 * (max(r_values) if r_values else 1.0)
        h_rz = ROOT.TH2F("h_rz", f"{title_prefix};z [mm];r [mm]",
                         200, zmin, zmax, 200, rmin, rmax)

        for (x, y, z) in hit_points:
            h_xy.Fill(x, y)
            h_rz.Fill(z, math.hypot(x, y))
    else:
        h_xy = None
        h_rz = None
        print("[info] No hit points; XY/RZ histograms will be empty.")

    colors = [
        ROOT.kRed + 1, ROOT.kBlue + 1, ROOT.kGreen + 1, ROOT.kMagenta + 1,
        ROOT.kCyan + 1, ROOT.kOrange + 1, ROOT.kSpring + 1, ROOT.kTeal + 1,
        ROOT.kViolet + 1, ROOT.kAzure + 1, ROOT.kPink + 1,
    ]

    c_xy = ROOT.TCanvas("c_xy", "XY view", 800, 800)
    c_rz = ROOT.TCanvas("c_rz", "RZ view", 800, 800)
    c_3d = ROOT.TCanvas("c_3d", "3D tracks", 800, 800)

    xy_overlays = []
    if h_xy:
        c_xy.cd()
        h_xy.Draw("COLZ")
        if track_states:
            xy_overlays = add_xy_track_overlay(c_xy, track_states, Bz)

    if h_rz:
        c_rz.cd()
        h_rz.Draw("COLZ")

    c_3d.cd()
    frame = ROOT.TH3F(
        "frame3d",
        f"{title_prefix} 3D; x [mm]; y [mm]; z [mm]",
        10, xmin, xmax, 10, ymin, ymax, 10, zmin, zmax,
    )
    frame.SetStats(False)
    frame.Draw()

    markers = []
    track_lines = []

    # GGTF hits markers per label
    for il, (lbl, pts) in enumerate(sorted(tracks_by_label.items(), key=lambda kv: kv[0])):
        if not pts:
            continue
        pm = ROOT.TPolyMarker3D(len(pts))
        color = colors[il % len(colors)]
        pm.SetMarkerColor(color)
        pm.SetMarkerStyle(20)
        pm.SetMarkerSize(0.8)
        for i, (x, y, z) in enumerate(pts):
            pm.SetPoint(i, x, y, z)
        pm.Draw("P SAME")
        markers.append(pm)

    # SimHits overlay in orange
    if simhit_points:
        pm_sim = ROOT.TPolyMarker3D(len(simhit_points))
        pm_sim.SetMarkerColor(ROOT.kOrange + 1)
        pm_sim.SetMarkerStyle(20)
        pm_sim.SetMarkerSize(0.9)
        for i, (x, y, z) in enumerate(simhit_points):
            pm_sim.SetPoint(i, x, y, z)
        pm_sim.Draw("P SAME")
        markers.append(pm_sim)
        print(f"[info] Drew {len(simhit_points)} simhit points in orange.")

    # Track lines
    if track_states:
        print(f"[info] Drawing {len(track_states)} GenFit track line(s) in 3D view with style='{track_style}'.")

        rmax_hits = max(math.hypot(x, y) for (x, y, _) in all_points)
        s_max = 1.2 * rmax_hits
        s_min = -s_max
        n_points_line = 200

        for it, st in enumerate(track_states):
            x0 = st["x0"]
            y0 = st["y0"]
            z0 = st["z0"]
            phi = st["phi"]
            tl  = st["tanLambda"]
            omg = st["omega"]

            pl = ROOT.TPolyLine3D(n_points_line)
            line_color = ROOT.kBlue if it == 0 else ROOT.kYellow
            pl.SetLineColor(line_color)
            pl.SetLineWidth(3)

            if track_style == "straight" or (not math.isfinite(omg)) or abs(Bz) == 0.0 or abs(omg) == 0.0:
                ux = math.cos(phi)
                uy = math.sin(phi)
                uz = tl
                norm = math.sqrt(ux*ux + uy*uy + uz*uz)
                if norm > 0:
                    ux /= norm; uy /= norm; uz /= norm
                for i in range(n_points_line):
                    s = s_min + (s_max - s_min) * i / (n_points_line - 1)
                    pl.SetPoint(i, x0 + ux * s, y0 + uy * s, z0 + uz * s)
            else:
                R_m  = 1.0 / (abs(omg) * 0.3 * abs(Bz))
                R_mm = R_m * 1000.0
                sgn = 1.0 if (omg * Bz) > 0.0 else -1.0
                xc = x0 - sgn * R_mm * math.sin(phi)
                yc = y0 + sgn * R_mm * math.cos(phi)
                alpha0 = math.atan2(y0 - yc, x0 - xc)

                cos_theta = 1.0 / math.sqrt(1.0 + tl*tl)
                sin_theta = tl * cos_theta

                for i in range(n_points_line):
                    s = s_min + (s_max - s_min) * i / (n_points_line - 1)
                    s_xy = s * cos_theta
                    delta_alpha = sgn * s_xy / R_mm
                    alpha = alpha0 + delta_alpha
                    x = xc + R_mm * math.cos(alpha)
                    y = yc + R_mm * math.sin(alpha)
                    z = z0 + s * sin_theta
                    pl.SetPoint(i, x, y, z)

            pl.Draw("SAME")
            track_lines.append(pl)
    else:
        print("[info] No track states provided; only hits+simhits will be drawn in 3D.")

    # Write objects into the directory
    if h_xy:
        c_xy.Write()
        h_xy.Write()
        for o in xy_overlays:
            o.Write()
    if h_rz:
        c_rz.Write()
        h_rz.Write()

    c_3d.Write()
    frame.Write()
    for pm in markers:
        pm.Write()
    for pl in track_lines:
        pl.Write()

    if created_local:
        out_file.Close()
        print(f"[info] Wrote plots to {out_root}")


# ------------------------------------------------------------
# main
# ------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="View GGTF SenseWireHits + DCH simhits + GenFit tracks for events ranked by sigma(pT)."
    )
    ap.add_argument("--input", required=True, help="Input reco ROOT file (EDM4hep)")
    ap.add_argument("--tree", default="events", help="TTree name (default: events)")
    ap.add_argument("--event", type=int, default=-1,
                    help="Event index (0-based). If >=0, process only this event (ignores --topN).")

    ap.add_argument("--hitsCollection", default="OutputWireHitsGGTF",
                    help="Hit collection with position.{x,y,z}. If not found, auto-detect a likely GGTF hit collection.")
    ap.add_argument("--autoDetectHits", action="store_true",
                    help="If set, auto-detect hits collection even if --hitsCollection is provided.")

    ap.add_argument("--simhitCollection", default="DCHCollection",
                    help="SimTrackerHit collection base name to overlay (default: DCHCollection). If empty, simhits not drawn.")
    ap.add_argument("--trackCollection", default="GenFitTracks",
                    help="Track collection base name for GenFit TrackStates (default: GenFitTracks). If empty, tracks not drawn.")

    ap.add_argument("--trackStyle", choices=["straight", "helix"], default="helix",
                    help="Visualization style for tracks: straight or helix (default: helix).")
    ap.add_argument("--Bz", type=float, default=2.0,
                    help="B-field along z [T] for helix drawing (default: 2.0; should match GenFit2DCHFitter.Bz).")
    ap.add_argument("--assumeQ", type=int, default=-1,
                    help="Charge sign used for pT(|q/omega|) and sigma(pT) calculations (default: -1 for mu-).")

    # Top-N by sigma(pT)
    ap.add_argument("--topN", type=int, default=10,
                    help="If >0 and --event <0: process top N events ranked by sigma(pT).")
    ap.add_argument("--expectedPt", type=float, default=float("2.5897"),
                    help="Expected pT [GeV] for sigma(pT) ranking (required if --topN>0).")
    ap.add_argument("--scanMaxEvents", type=int, default=-1,
                    help="Limit scanning to first N events when ranking (default: -1 means all).")
    ap.add_argument("--rankOrder", choices=["largest", "smallest"], default="largest",
                    help="Rank by largest or smallest sigma(pT) (default: largest).")

    ap.add_argument("--outRoot", default="tracks_display_simhits_multi.root",
                    help="Output ROOT file for histos + canvases (multi-event).")
    args = ap.parse_args()

    f = ROOT.TFile.Open(args.input)
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open input file: {args.input}")

    tree = f.Get(args.tree)
    if not tree:
        raise RuntimeError(f"No TTree named '{args.tree}' found in file: {args.input}")

    n_ev_total = int(tree.GetEntries())
    print(f"[info] File: {args.input}, tree='{args.tree}', events: {n_ev_total}")

    # Decide hits collection
    hits_coll = args.hitsCollection
    if args.autoDetectHits or (not _collection_has_xyz(tree, hits_coll)):
        hits_coll = _auto_detect_hits_collection(tree, preferred=hits_coll)
        if not hits_coll:
            raise RuntimeError("Could not auto-detect any collection with '.position.x/y/z' in this file.")
    else:
        print(f"[info] Using hits collection = '{hits_coll}'")

    # Decide event list
    event_list = []

    if args.event >= 0:
        if args.event >= n_ev_total:
            raise RuntimeError(f"Requested event {args.event} out of range [0, {n_ev_total-1}]")
        event_list = [args.event]
        print(f"[info] Using user-requested event {args.event}")

    else:
        if args.topN and args.topN > 0:
            if not (math.isfinite(args.expectedPt) and args.expectedPt > 0):
                raise RuntimeError("--expectedPt must be provided (>0) when using --topN")

            n_scan = n_ev_total if args.scanMaxEvents < 0 else min(n_ev_total, int(args.scanMaxEvents))
            print(f"[info] Ranking events by sigma(pT) using expectedPt={args.expectedPt} GeV "
                  f"over n_scan={n_scan} events...")

            scored = []
            n_skipped = 0
            for iev in range(n_scan):
                var_omega, omega, pt_reco, det = get_event_varomega(
                    tree, iev, track_coll=args.trackCollection, assume_q=args.assumeQ
                )
                sig_pt = sigma_pt_from_varomega(args.expectedPt, var_omega, assume_q=args.assumeQ)
                if not math.isfinite(sig_pt):
                    n_skipped += 1
                    continue
                scored.append((sig_pt, iev, var_omega, omega, pt_reco, det))

            if not scored:
                raise RuntimeError("No events had finite sigma(pT). Check that TrackState covariance is present and trackCollection is correct.")

            scored.sort(key=lambda t: t[0], reverse=(args.rankOrder == "largest"))
            scored = scored[:int(args.topN)]

            event_list = [iev for (sig_pt, iev, *_rest) in scored]

            print(f"[info] Selected top {len(scored)} events by sigma(pT) ({args.rankOrder}):")
            for rank, (sig_pt, iev, var_omega, omega, pt_reco, det) in enumerate(scored):
                print(f"  rank {rank:02d}: event={iev:6d}  sigmaPt={sig_pt:.6g} GeV"
                      f"  Var(omega)={var_omega:.3g}  omega={omega:.3g}  pT(|q/omega|)={pt_reco:.3g}"
                      f"  state={det.get('state_index','?')} perStateLen={det.get('per_state_len','?')}")

        else:
            # fallback: first event with hits
            x_leaf = _find_leaf(tree, f"{hits_coll}.position.x")
            if not x_leaf:
                raise RuntimeError(f"Missing leaf '{hits_coll}.position.x' for fallback selection.")
            first = None
            for iev in range(n_ev_total):
                tree.GetEntry(iev)
                if int(x_leaf.GetNdata()) > 0:
                    first = iev
                    break
            if first is None:
                print("[fatal] No events with hits; nothing to visualize.")
                return
            event_list = [first]
            print(f"[info] Using first event with hits: {first}")

    # Open ONE output file for all events
    out_file = ROOT.TFile(args.outRoot, "RECREATE")
    if not out_file or out_file.IsZombie():
        raise RuntimeError(f"Could not create output ROOT file: {args.outRoot}")

    meta_global = ROOT.TNamed(
        "view_tracks_metadata_global",
        "\n".join([
            f"script: {os.path.basename(__file__)}",
            f"command_line: {' '.join(sys.argv)}",
            f"input_file: {args.input}",
            f"tree: {args.tree}",
            f"hits_collection: {hits_coll}",
            f"simhit_collection: {args.simhitCollection or '<none>'}",
            f"track_collection: {args.trackCollection or '<none>'}",
            f"track_style: {args.trackStyle}",
            f"Bz_T: {args.Bz}",
            f"assumeQ: {args.assumeQ}",
            f"topN: {args.topN}",
            f"expectedPt_GeV: {args.expectedPt}",
            f"rankOrder: {args.rankOrder}",
            f"scanMaxEvents: {args.scanMaxEvents}",
            f"user: {getpass.getuser()}",
            f"host: {socket.gethostname()}",
            f"timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        ])
    )
    meta_global.Write()

    # Process events
    for ev_idx in event_list:
        print(f"\n[info] ===== Processing event {ev_idx} =====")

        tracks_by_label = load_labeled_hits(tree, ev_idx, hits_coll)

        simhit_points = []
        if args.simhitCollection:
            simhit_points = load_simhit_positions(tree, ev_idx, args.simhitCollection)

        track_states = []
        if args.trackCollection:
            track_states = load_track_states(tree, ev_idx, args.trackCollection, assume_q=args.assumeQ)

        # compute sigmaPt for metadata if possible
        var_omega, omega, pt_reco, det = get_event_varomega(tree, ev_idx, track_coll=args.trackCollection, assume_q=args.assumeQ)
        sig_pt = sigma_pt_from_varomega(args.expectedPt, var_omega, assume_q=args.assumeQ) if (math.isfinite(args.expectedPt) and args.expectedPt > 0) else float("nan")

        meta_info = {
            "event_index": ev_idx,
            "hits_collection": hits_coll,
            "simhit_collection": args.simhitCollection or "<none>",
            "track_collection": args.trackCollection or "<none>",
            "track_style": args.trackStyle,
            "Bz_T": args.Bz,
            "assumeQ": args.assumeQ,
            "expectedPt_GeV": args.expectedPt,
            "omega": omega,
            "VarOmega": var_omega,
            "sigmaPt_GeV": sig_pt,
            "pT_from_omega_GeV": pt_reco,
            "picked_state_index": det.get("state_index", "?"),
            "cov_per_state_len": det.get("per_state_len", "?"),
        }

        out_dir = f"event_{ev_idx:06d}"
        make_plots(tracks_by_label,
                   simhit_points,
                   args.outRoot,
                   title_prefix=f"{hits_coll} (event {ev_idx})",
                   track_states=track_states,
                   track_style=args.trackStyle,
                   Bz=args.Bz,
                   meta_info=meta_info,
                   out_file=out_file,
                   out_dir_name=out_dir)

    out_file.Close()
    f.Close()
    print(f"[info] Wrote multi-event plots to {args.outRoot}")


if __name__ == "__main__":
    main()
