#!/usr/bin/env python3
"""
view_tracks_event.py

Visualize GGTF_3DHits, DCH digis, and GenFit2 tracks from an EDM4hep ROOT file.

For a chosen event:
  - GGTF_3DHits positions (x,y,z) and labels (type)
  - DCHDigi2Collection positions (SenseWireHit positions in mm)
  - GenFitTracks TrackStates (typically one AtIP state per track):
      * helix visualization from (x0,y0,z0, phi, tanLambda, omega) in uniform Bz

Key fixes vs older version:
  1) Track <-> TrackState association:
     - We now use GenFitTracks.trackStates_begin/end (or equivalent) to group states per track.
     - We pick the AtIP-like state per track (heuristic: smallest r^2 among that track’s states;
       or first state if only one).

  2) Helix handedness:
     - Removed the forced sign hack.
     - Use physically consistent curvature sign: sgn = sign(omega * Bz).

  3) Sanity print:
     - Compare pT stored in TrackState.time (your fitter encodes pT here) to pT derived from omega:
          pT_from_omega = 1/|omega|   (since omega = q/pT)
     - If those disagree wildly, you’re either reading the wrong leaves or the file contains
       corrupted/uninitialized states (or a different omega convention).

  4) Robust leaf discovery:
     - Handles multiple common branch naming patterns for trackStates + begin/end leaves.

Writes histograms, canvases, and metadata into a ROOT file (no interactive windows).
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
    lf = tree.GetLeaf(name)
    return lf


def _scan_leaf_by_suffix(tree, coll_name, suffix):
    """
    Find a leaf whose name contains coll_name and ends with `suffix`.
    Returns the leaf name (string) or None.
    """
    leaves = tree.GetListOfLeaves()
    if not leaves:
        return None
    for obj in leaves:
        nm = obj.GetName()
        if coll_name in nm and nm.endswith(suffix):
            return nm
    return None


def _resolve_begin_end_leaves(tree, coll_name):
    """
    Resolve trackStates begin/end leaves for a Track collection.

    Common names:
      - <coll>.trackStates_begin / <coll>.trackStates_end
      - <coll>.TrackStates_begin / <coll>.TrackStates_end
      - Sometimes different capitalization; if not found, scan by suffix.
    Returns (begin_leaf_name, end_leaf_name) or (None, None)
    """
    candidates = [
        (f"{coll_name}.trackStates_begin", f"{coll_name}.trackStates_end"),
        (f"{coll_name}.TrackStates_begin", f"{coll_name}.TrackStates_end"),
    ]
    for bname, ename in candidates:
        if _find_leaf(tree, bname) and _find_leaf(tree, ename):
            return bname, ename

    # Fallback: scan
    bname = _scan_leaf_by_suffix(tree, coll_name, "trackStates_begin")
    ename = _scan_leaf_by_suffix(tree, coll_name, "trackStates_end")
    if bname and ename:
        return bname, ename

    bname = _scan_leaf_by_suffix(tree, coll_name, "TrackStates_begin")
    ename = _scan_leaf_by_suffix(tree, coll_name, "TrackStates_end")
    if bname and ename:
        return bname, ename

    return None, None


def resolve_ts_prefix(tree, coll_name):
    """
    Try to guess the TrackState leaf prefix for a Track collection.

    We try a few common EDM4hep/podio patterns, e.g.:
      - GenFitTracks.trackStates.*
      - GenFitTracks.TrackStates.*
      - GenFitTracks.trackStates_AtIP.*
      - GenFitTracks.TrackStates_AtIP.*

    If none exist, scan leaves and pick something containing '<coll_name>' and ending in '.phi'.
    Returns prefix ending with '.' or None.
    """
    candidates = [
        f"{coll_name}.trackStates.",
        f"{coll_name}.TrackStates.",
        f"{coll_name}.trackStates_AtIP.",
        f"{coll_name}.TrackStates_AtIP.",
    ]

    for pref in candidates:
        lf = _find_leaf(tree, pref + "phi")
        if lf:
            print(f"[info] Using TrackState prefix '{pref}' (found '{pref}phi').")
            return pref

    # Fallback: scan all leaves for '<coll_name>... .phi'
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


# ------------------------------------------------------------
# Load GGTF_3DHits grouped by label using position.x leaf
# ------------------------------------------------------------
def load_3d_hits(tree, ev_idx, coll_name="GGTF_3DHits"):
    """
    Return dict: label -> list of (x,y,z) for event ev_idx.

    Layout expected:
      - <coll_name>.position.x / y / z: Double_t [N]
      - <coll_name>.type              : Int_t    [N] (optional)
    """
    tracks = defaultdict(list)

    x_leaf = _find_leaf(tree, f"{coll_name}.position.x")
    y_leaf = _find_leaf(tree, f"{coll_name}.position.y")
    z_leaf = _find_leaf(tree, f"{coll_name}.position.z")

    if not (x_leaf and y_leaf and z_leaf):
        raise RuntimeError(
            f"Could not find required leaves for '{coll_name}'.\n"
            f"Expected at least:\n"
            f"  {coll_name}.position.x\n"
            f"  {coll_name}.position.y\n"
            f"  {coll_name}.position.z\n"
            f"Do 'events->Print(\"{coll_name}*\")' in ROOT to verify branch names."
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


# ------------------------------------------------------------
# Load DCHDigi2Collection positions (SenseWireHit positions in mm)
# ------------------------------------------------------------
def load_dch_digi_positions(tree, ev_idx, coll_name="DCHDigi2Collection"):
    """
    Return list of (x,y,z) for digi hits in event ev_idx.

    Layout expected:
      - <coll_name>.position.x / y / z: Double_t [N]
    """
    x_leaf = _find_leaf(tree, f"{coll_name}.position.x")
    y_leaf = _find_leaf(tree, f"{coll_name}.position.y")
    z_leaf = _find_leaf(tree, f"{coll_name}.position.z")

    if not (x_leaf and y_leaf and z_leaf):
        print(f"[info] No digi position leaves found for '{coll_name}'; skipping digi overlay.")
        return []

    tree.GetEntry(ev_idx)
    n = int(x_leaf.GetNdata())
    print(f"[info] {coll_name}: event={ev_idx} nDigis={n}")

    digi_pts = []
    for i in range(n):
        x = float(x_leaf.GetValue(i))
        y = float(y_leaf.GetValue(i))
        z = float(z_leaf.GetValue(i))
        digi_pts.append((x, y, z))

    return digi_pts


# ------------------------------------------------------------
# Load GenFit2 TrackStates per TRACK (using begin/end)
# ------------------------------------------------------------
def load_track_states(tree, ev_idx, coll_name="GenFitTracks"):
    """
    Return list of per-track state dicts for event ev_idx.

    We GROUP states per track using <coll>.trackStates_begin/end, then choose one state per track.
    Preference:
      - if only 1 state: take it
      - else: take the state with smallest r^2 = x0^2 + y0^2 (AtIP-like)
        (this matches your fitter: it exports an AtIP state and it's typically closest to origin)

    Fields expected in TrackState:
      - referencePoint.{x,y,z} (mm)
      - phi
      - tanLambda
      - omega (q/pT [GeV^-1] per your fitter)
      - time  (pT [GeV] per your fitter)
      - optional D0,Z0

    We print sanity checks:
      - pT(time) vs pT(1/|omega|)
    """
    prefix = resolve_ts_prefix(tree, coll_name)
    if not prefix:
        print(f"[warn] No valid TrackState prefix for '{coll_name}'; no tracks will be drawn.")
        return []

    # begin/end leaves for association
    bname, ename = _resolve_begin_end_leaves(tree, coll_name)
    if not (bname and ename):
        print(f"[warn] Could not find '{coll_name}.trackStates_begin/end' (or equivalent).")
        print("       Falling back to interpreting TrackStates as a flat array (less reliable).")
        # We'll still return something, but warn loudly.
    else:
        print(f"[info] Using Track->TrackState association via begin/end leaves:")
        print(f"       begin='{bname}', end='{ename}'")

    def leaf(name):
        lf = _find_leaf(tree, name)
        if not lf:
            print(f"[debug] TrackState leaf '{name}' not found")
        return lf

    # TrackState leaves
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
        print(f"[warn] Missing required TrackState leaves (phi/tanLambda) for '{coll_name}'. "
              f"No tracks will be drawn.")
        return []

    # begin/end leaves (if present)
    beg_leaf = _find_leaf(tree, bname) if bname else None
    end_leaf = _find_leaf(tree, ename) if ename else None

    tree.GetEntry(ev_idx)

    n_states_total = int(phi_leaf.GetNdata())
    print(f"[info] {coll_name}: event={ev_idx} nTrackStates(total)={n_states_total}")

    # Build a flat list of state records first (so we can index them by [stateIndex])
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
            # fallback (rough)
            if math.isfinite(d0) and math.isfinite(z0):
                x0 = -d0 * math.sin(phi)
                y0 =  d0 * math.cos(phi)
                z0p = z0
            else:
                x0 = y0 = z0p = 0.0

        r2 = x0*x0 + y0*y0
        pT_from_omega = (1.0/abs(omg)) if (math.isfinite(omg) and abs(omg) > 0.0) else float("nan")

        flat_states.append({
            "state_index": si,
            "D0": d0,
            "Z0": z0,
            "phi": phi,
            "omega": omg,
            "tanLambda": tl,
            "pT_time": pTt,
            "pT_from_omega": pT_from_omega,
            "x0": x0,
            "y0": y0,
            "z0": z0p,
            "r2": r2,
        })

    # If we can associate per track, do it
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

            # pick best AtIP-like state: smallest r^2
            best = min(states_this, key=lambda st: st["r2"])

            best = dict(best)  # copy
            best["track_index"] = ti
            best["states_begin"] = b
            best["states_end"] = e
            best["n_states_in_track"] = (e - b)
            per_track.append(best)

            # Debug print for each track
            pt_t = best["pT_time"]
            pt_o = best["pT_from_omega"]
            omg  = best["omega"]
            mismatch = ""
            if math.isfinite(pt_t) and math.isfinite(pt_o) and pt_t > 0 and pt_o > 0:
                ratio = pt_t / pt_o
                if ratio > 2.0 or ratio < 0.5:
                    mismatch = f"  !!! mismatch pT(time)/pT(1/|omega|)={ratio:.3g}"
            print(
                f"[debug] Track[{ti}] states[{b}:{e}) pickState={best['state_index']} "
                f"x0={best['x0']:.2f} y0={best['y0']:.2f} z0={best['z0']:.2f} mm "
                f"phi={best['phi']:.3f} tanL={best['tanLambda']:.3f} "
                f"pT(time)={pt_t:.3f} GeV  pT(1/|omega|)={pt_o:.3f} GeV  omega={omg:.4e}"
                f"{mismatch}"
            )

    else:
        # Flat fallback: interpret each state as “a track” (not reliable)
        print("[warn] No begin/end association; treating each TrackState as standalone.")
        for st in flat_states:
            st = dict(st)
            st["track_index"] = st["state_index"]
            st["states_begin"] = st["state_index"]
            st["states_end"] = st["state_index"] + 1
            st["n_states_in_track"] = 1
            per_track.append(st)

            pt_t = st["pT_time"]
            pt_o = st["pT_from_omega"]
            omg  = st["omega"]
            mismatch = ""
            if math.isfinite(pt_t) and math.isfinite(pt_o) and pt_t > 0 and pt_o > 0:
                ratio = pt_t / pt_o
                if ratio > 2.0 or ratio < 0.5:
                    mismatch = f"  !!! mismatch pT(time)/pT(1/|omega|)={ratio:.3g}"
            print(
                f"[debug] TrackState[{st['state_index']}] "
                f"x0={st['x0']:.2f} y0={st['y0']:.2f} z0={st['z0']:.2f} mm "
                f"phi={st['phi']:.3f} tanL={st['tanLambda']:.3f} "
                f"pT(time)={pt_t:.3f} GeV  pT(1/|omega|)={pt_o:.3f} GeV  omega={omg:.4e}"
                f"{mismatch}"
            )

    return per_track


# ------------------------------------------------------------
# Build histograms + 3D display and save to ROOT file
# ------------------------------------------------------------
def make_plots(tracks_by_label,
               digi_points,
               out_root,
               title_prefix="GGTF_3DHits",
               track_states=None,
               track_style="helix",
               Bz=2.0,
               meta_info=None):
    """
    tracks_by_label: dict[label] -> list[(x,y,z)] for GGTF_3DHits
    digi_points: list[(x,y,z)] for DCHDigi2Collection (SenseWireHits)
    out_root: path to ROOT file for output
    track_states: list of per-track state dicts
    track_style: "straight" or "helix"
    Bz: magnetic field along z [T]
    meta_info: dict of metadata strings to store as a TNamed
    """
    # Flatten to find coordinate ranges
    all_points = []
    for pts in tracks_by_label.values():
        all_points.extend(pts)
    all_points.extend(digi_points)

    if not all_points:
        print("[warn] No 3D points (hits or digis) found; nothing to plot.")
        return

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    zs = [p[2] for p in all_points]

    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)

    # Nice margins
    dx = max(1.0, 0.05 * (xmax - xmin if xmax > xmin else 1.0))
    dy = max(1.0, 0.05 * (ymax - ymin if ymax > ymin else 1.0))
    dz = max(1.0, 0.05 * (zmax - zmin if zmax > zmin else 1.0))

    xmin -= dx; xmax += dx
    ymin -= dy; ymax += dy
    zmin -= dz; zmax += dz

    f_out = ROOT.TFile(out_root, "RECREATE")
    if not f_out or f_out.IsZombie():
        raise RuntimeError(f"Could not create output ROOT file: {out_root}")

    # Metadata block
    if meta_info is not None:
        meta_str = "\n".join(f"{k}: {v}" for k, v in meta_info.items())
        meta = ROOT.TNamed("view_tracks_metadata", meta_str)
        meta.Write()

    # 2D XY and RZ histograms (using GGTF hits only)
    hit_points = []
    for pts in tracks_by_label.values():
        hit_points.extend(pts)

    if hit_points:
        h_xy = ROOT.TH2F("h_xy", f"{title_prefix};x [mm];y [mm]",
                         200, xmin, xmax,
                         200, ymin, ymax)

        r_values = [math.hypot(x, y) for (x, y, _) in hit_points]
        rmin = 0.0
        rmax = max(r_values) + 0.1 * (max(r_values) if r_values else 1.0)
        h_rz = ROOT.TH2F("h_rz", f"{title_prefix};z [mm];r [mm]",
                         200, zmin, zmax,
                         200, rmin, rmax)

        for (x, y, z) in hit_points:
            h_xy.Fill(x, y)
            h_rz.Fill(z, math.hypot(x, y))
    else:
        h_xy = None
        h_rz = None
        print("[info] No GGTF_3DHits; XY/RZ histograms will be empty.")

    # Colors
    colors = [
        ROOT.kRed + 1,
        ROOT.kBlue + 1,
        ROOT.kGreen + 1,
        ROOT.kMagenta + 1,
        ROOT.kCyan + 1,
        ROOT.kOrange + 1,
        ROOT.kSpring + 1,
        ROOT.kTeal + 1,
        ROOT.kViolet + 1,
        ROOT.kAzure + 1,
        ROOT.kPink + 1,
    ]

    # Canvases
    c_xy = ROOT.TCanvas("c_xy", "XY view", 800, 800)
    c_rz = ROOT.TCanvas("c_rz", "RZ view", 800, 800)
    c_3d = ROOT.TCanvas("c_3d", "3D tracks", 800, 800)

    if h_xy:
        c_xy.cd()
        h_xy.Draw("COLZ")

    if h_rz:
        c_rz.cd()
        h_rz.Draw("COLZ")

    c_3d.cd()
    frame = ROOT.TH3F(
        "frame3d",
        f"{title_prefix} 3D; x [mm]; y [mm]; z [mm]",
        10, xmin, xmax,
        10, ymin, ymax,
        10, zmin, zmax,
    )
    frame.SetStats(False)
    frame.Draw()

    markers = []
    track_lines = []

    # Scatter markers per GGTF label
    for il, (lbl, pts) in enumerate(sorted(tracks_by_label.items(), key=lambda kv: kv[0])):
        if not pts:
            continue
        n = len(pts)
        pm = ROOT.TPolyMarker3D(n)
        color = colors[il % len(colors)]
        pm.SetMarkerColor(color)
        pm.SetMarkerStyle(20)
        pm.SetMarkerSize(0.8)
        for i, (x, y, z) in enumerate(pts):
            pm.SetPoint(i, x, y, z)
        pm.Draw("P SAME")
        markers.append(pm)

    # Scatter markers for digis (orange)
    if digi_points:
        n_digi = len(digi_points)
        pm_digi = ROOT.TPolyMarker3D(n_digi)
        pm_digi.SetMarkerColor(ROOT.kOrange + 1)
        pm_digi.SetMarkerStyle(20)
        pm_digi.SetMarkerSize(0.9)
        for i, (x, y, z) in enumerate(digi_points):
            pm_digi.SetPoint(i, x, y, z)
        pm_digi.Draw("P SAME")
        markers.append(pm_digi)
        print(f"[info] Drew {n_digi} DCHDigi2Collection points in orange.")

    # Draw GenFit track lines
    if track_states:
        print(f"[info] Drawing {len(track_states)} GenFit track line(s) in 3D view with style='{track_style}'.")

        # Rough scale: use largest radial extent seen in all points
        rmax_hits = max(math.hypot(x, y) for (x, y, _) in all_points)

        # Path length in mm along the track (s range)
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
                # Straight-line approximation
                ux = math.cos(phi)
                uy = math.sin(phi)
                uz = tl
                norm = math.sqrt(ux*ux + uy*uy + uz*uz)
                if norm > 0:
                    ux /= norm
                    uy /= norm
                    uz /= norm

                for i in range(n_points_line):
                    s = s_min + (s_max - s_min) * i / (n_points_line - 1)
                    x = x0 + ux * s
                    y = y0 + uy * s
                    z = z0 + uz * s
                    pl.SetPoint(i, x, y, z)

            else:
                # Helix in uniform Bz
                # Your fitter defines: omega = q/pT  [GeV^-1]
                # Radius in meters: R = pT / (0.3 |q| B) = 1 / (|omega| * 0.3 |B|)
                R_m  = 1.0 / (abs(omg) * 0.3 * abs(Bz))
                R_mm = R_m * 1000.0

                # Physically consistent handedness: sign(q*B) = sign(omega*Bz)
                sgn = 1.0 if (omg * Bz) > 0.0 else -1.0

                # Circle center in XY (from perigee point), tangent at perigee matches phi
                xc = x0 - sgn * R_mm * math.sin(phi)
                yc = y0 + sgn * R_mm * math.cos(phi)

                # Angle of radial vector (center -> perigee)
                alpha0 = math.atan2(y0 - yc, x0 - xc)

                # Pitch from tanLambda = pz/pT
                cos_theta = 1.0 / math.sqrt(1.0 + tl*tl)
                sin_theta = tl * cos_theta

                for i in range(n_points_line):
                    s = s_min + (s_max - s_min) * i / (n_points_line - 1)

                    # projected path length in XY plane
                    s_xy = s * cos_theta

                    # change in azimuth along circle
                    delta_alpha = sgn * s_xy / R_mm
                    alpha = alpha0 + delta_alpha

                    x = xc + R_mm * math.cos(alpha)
                    y = yc + R_mm * math.sin(alpha)
                    z = z0 + s * sin_theta
                    pl.SetPoint(i, x, y, z)

            pl.Draw("SAME")
            track_lines.append(pl)
    else:
        print("[info] No track states provided; only hits+digis will be drawn in 3D.")

    # Write everything
    if h_xy:
        c_xy.Write()
        h_xy.Write()
    if h_rz:
        c_rz.Write()
        h_rz.Write()

    c_3d.Write()
    frame.Write()
    for pm in markers:
        pm.Write()
    for pl in track_lines:
        pl.Write()

    f_out.Close()
    print(f"[info] Wrote plots to {out_root}")


# ------------------------------------------------------------
# Scan events to find one with GGTF_3DHits.position.x hits > 0
# ------------------------------------------------------------
def find_first_event_with_hits(tree, coll_name="GGTF_3DHits", max_print=20):
    x_leaf = _find_leaf(tree, f"{coll_name}.position.x")
    if not x_leaf:
        raise RuntimeError(
            f"Could not find leaf '{coll_name}.position.x' in TTree; "
            f"do 'events->Print(\"{coll_name}*\")' to inspect branch layout."
        )

    n_ev = tree.GetEntries()
    print(f"[debug] Scanning {n_ev} events for {coll_name} hits via '{coll_name}.position.x'...")

    for iev in range(min(n_ev, max_print)):
        tree.GetEntry(iev)
        n_hits = int(x_leaf.GetNdata())
        print(f"[debug] event {iev}: nHits={n_hits}")

    for iev in range(n_ev):
        tree.GetEntry(iev)
        n_hits = int(x_leaf.GetNdata())
        if n_hits > 0:
            print(f"[info] First event with {coll_name} hits: event {iev}, nHits={n_hits}")
            return iev

    print(f"[warn] No events with {coll_name} hits found (all have nHits=0)")
    return None


# ------------------------------------------------------------
# main
# ------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(
        description="View GGTF_3DHits + DCH digis + GenFit tracks for one event."
    )
    ap.add_argument("--input", required=True, help="Input reco ROOT file (EDM4hep)")
    ap.add_argument("--event", type=int, default=-1,
                    help="Event index (0-based). If <0, auto-find first event with GGTF_3DHits.")
    ap.add_argument("--collection", default="GGTF_3DHits",
                    help="3D hits collection base name (default: GGTF_3DHits)")
    ap.add_argument("--digiCollection", default="DCHDigi2Collection",
                    help="DCH digi collection base name (default: DCHDigi2Collection). "
                         "If empty, digis will not be drawn.")
    ap.add_argument("--trackCollection", default="GenFitTracks",
                    help="Track collection base name for GenFit TrackStates (default: GenFitTracks). "
                         "If empty, tracks will not be drawn.")
    ap.add_argument("--trackStyle", choices=["straight", "helix"], default="helix",
                    help="Visualization style for tracks: straight or helix (default: helix).")
    ap.add_argument("--Bz", type=float, default=2.0,
                    help="B-field along z [T] for helix drawing (default: 2.0, "
                         "should match GenFit2DCHFitter.Bz).")
    ap.add_argument("--outRoot", default="tracks_display.root",
                    help="Output ROOT file for histos + canvases")
    args = ap.parse_args()

    f = ROOT.TFile.Open(args.input)
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open input file: {args.input}")

    tree = f.Get("events")
    if not tree:
        raise RuntimeError(f"No TTree named 'events' found in file: {args.input}")

    n_ev = tree.GetEntries()
    print(f"[info] File: {args.input}, events: {n_ev}")

    # Decide which event index to use
    if args.event >= 0:
        ev_idx = args.event
        if ev_idx >= n_ev:
            raise RuntimeError(f"Requested event {ev_idx} out of range [0, {n_ev-1}]")
        print(f"[info] Using user-requested event {ev_idx}")
    else:
        ev_idx = find_first_event_with_hits(tree, args.collection)
        if ev_idx is None:
            print("[fatal] No events with 3D hits; nothing to visualize.")
            return

    # Load GGTF hits for that event
    tracks_by_label = load_3d_hits(tree, ev_idx, args.collection)
    print(f"[info] Found labels: {sorted(tracks_by_label.keys())}")
    for lbl, pts in sorted(tracks_by_label.items(), key=lambda kv: kv[0]):
        print(f"  label {lbl}: {len(pts)} hits")

    # Load DCH digis
    digi_points = []
    if args.digiCollection:
        digi_points = load_dch_digi_positions(tree, ev_idx, args.digiCollection)

    # Load GenFit track states per track
    track_states = []
    if args.trackCollection:
        track_states = load_track_states(tree, ev_idx, args.trackCollection)

    # Metadata
    meta_info = {
        "script": os.path.basename(__file__),
        "command_line": " ".join(sys.argv),
        "input_file": args.input,
        "output_file": args.outRoot,
        "event_index": ev_idx,
        "hits_collection": args.collection,
        "digi_collection": args.digiCollection or "<none>",
        "track_collection": args.trackCollection or "<none>",
        "track_style": args.trackStyle,
        "Bz_T": args.Bz,
        "user": getpass.getuser(),
        "host": socket.gethostname(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    make_plots(tracks_by_label,
               digi_points,
               args.outRoot,
               title_prefix=f"{args.collection} (event {ev_idx})",
               track_states=track_states,
               track_style=args.trackStyle,
               Bz=args.Bz,
               meta_info=meta_info)

    f.Close()


if __name__ == "__main__":
    main()
