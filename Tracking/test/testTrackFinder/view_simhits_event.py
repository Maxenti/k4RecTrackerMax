#!/usr/bin/env python3
"""
view_simhits_event.py

Like view_tracks_event.py, but overlays SIM HITS instead of DIGI HITS.

For a chosen event:
  - GGTF_3DHits positions (x,y,z) and labels (type)
  - SimTrackerHits positions (x,y,z) from a SimHit collection (default: DCHCollection)
  - (optional) GenFitTracks TrackStates(AtIP) helix/straight visualization

Extras:
  - Draw inner/outer drift-chamber radius rings (XY-plane circles) in the 3D view.

Writes histograms, canvases, and 3D objects into an output ROOT file.
No interactive windows (ROOT batch mode enabled), but you can rotate the 3D canvas
inside ROOT when you open the output .root file.
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
# Load GGTF_3DHits grouped by label using position.x leaf
# ------------------------------------------------------------
def load_3d_hits(tree, ev_idx, coll_name="GGTF_3DHits"):
    tracks = defaultdict(list)

    def leaf(name):
        lf = tree.GetLeaf(name)
        if not lf:
            print(f"[debug] Leaf '{name}' not found")
        return lf

    x_leaf = leaf(f"{coll_name}.position.x")
    y_leaf = leaf(f"{coll_name}.position.y")
    z_leaf = leaf(f"{coll_name}.position.z")

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

    type_leaf = tree.GetLeaf(f"{coll_name}.type")
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
# Load SimTrackerHit positions (x,y,z)
# ------------------------------------------------------------
def load_simhit_positions(tree, ev_idx, coll_name="DCHCollection"):
    """
    Return list of (x,y,z) for sim hits in event ev_idx.

    Expected leaves:
      - <coll_name>.position.x / y / z
    """
    def leaf(name):
        lf = tree.GetLeaf(name)
        if not lf:
            print(f"[debug] SimHit leaf '{name}' not found")
        return lf

    x_leaf = leaf(f"{coll_name}.position.x")
    y_leaf = leaf(f"{coll_name}.position.y")
    z_leaf = leaf(f"{coll_name}.position.z")

    if not (x_leaf and y_leaf and z_leaf):
        print(f"[warn] No simhit position leaves found for '{coll_name}'; skipping simhit overlay.")
        return []

    tree.GetEntry(ev_idx)
    n = int(x_leaf.GetNdata())
    print(f"[info] {coll_name}: event={ev_idx} nSimHits={n}")

    pts = []
    for i in range(n):
        pts.append((
            float(x_leaf.GetValue(i)),
            float(y_leaf.GetValue(i)),
            float(z_leaf.GetValue(i)),
        ))
    return pts


# ------------------------------------------------------------
# Helper: resolve TrackState leaf prefix for a Track collection
# ------------------------------------------------------------
def resolve_ts_prefix(tree, coll_name):
    candidates = [
        f"{coll_name}.trackStates.",
        f"{coll_name}.TrackStates.",
        f"{coll_name}.trackStates_AtIP.",
        f"{coll_name}.TrackStates_AtIP.",
    ]
    for pref in candidates:
        if tree.GetLeaf(pref + "phi"):
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


# ------------------------------------------------------------
# Load GenFit2 TrackStates (AtIP) for an event
# ------------------------------------------------------------
def load_track_states(tree, ev_idx, coll_name="GenFitTracks"):
    def leaf(name):
        lf = tree.GetLeaf(name)
        if not lf:
            print(f"[debug] TrackState leaf '{name}' not found")
        return lf

    prefix = resolve_ts_prefix(tree, coll_name)
    if not prefix:
        print(f"[warn] No valid TrackState prefix for '{coll_name}'; no tracks will be drawn.")
        return []

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

    tree.GetEntry(ev_idx)
    n_states = int(phi_leaf.GetNdata())
    print(f"[info] {coll_name}: event={ev_idx} nTrackStates={n_states}")

    states = []
    for i in range(n_states):
        d0   = float(d0_leaf.GetValue(i))   if d0_leaf   else float("nan")
        z0   = float(z0_leaf.GetValue(i))   if z0_leaf   else float("nan")
        phi  = float(phi_leaf.GetValue(i))
        omg  = float(omg_leaf.GetValue(i))  if omg_leaf  else float("nan")
        tl   = float(tl_leaf.GetValue(i))
        pT   = float(time_leaf.GetValue(i)) if time_leaf else float("nan")

        if refx_leaf and refy_leaf and refz_leaf:
            x0 = float(refx_leaf.GetValue(i))
            y0 = float(refy_leaf.GetValue(i))
            z0p = float(refz_leaf.GetValue(i))
        else:
            if math.isfinite(d0) and math.isfinite(z0):
                x0 = -d0 * math.sin(phi)
                y0 =  d0 * math.cos(phi)
                z0p = z0
            else:
                x0 = y0 = z0p = 0.0

        states.append({"phi": phi, "omega": omg, "tanLambda": tl, "x0": x0, "y0": y0, "z0": z0p, "pT": pT})

    return states


# ------------------------------------------------------------
# Scan events to find one with hits in a collection
# ------------------------------------------------------------
def find_first_event_with_hits(tree, coll_name, max_print=20):
    x_leaf = tree.GetLeaf(f"{coll_name}.position.x")
    if not x_leaf:
        raise RuntimeError(f"Could not find leaf '{coll_name}.position.x'")

    n_ev = tree.GetEntries()
    print(f"[debug] Scanning {n_ev} events for {coll_name} hits...")

    for iev in range(min(n_ev, max_print)):
        tree.GetEntry(iev)
        print(f"[debug] event {iev}: nHits={int(x_leaf.GetNdata())}")

    for iev in range(n_ev):
        tree.GetEntry(iev)
        if int(x_leaf.GetNdata()) > 0:
            print(f"[info] First event with {coll_name} hits: event {iev}")
            return iev

    print(f"[warn] No events with {coll_name} hits found")
    return None


# ------------------------------------------------------------
# Helper: make a circle ring in XY plane as TPolyLine3D
# ------------------------------------------------------------
def make_xy_ring(R_mm, z_mm, nseg=360):
    pl = ROOT.TPolyLine3D(nseg + 1)
    for i in range(nseg + 1):
        ang = 2.0 * math.pi * float(i) / float(nseg)
        x = R_mm * math.cos(ang)
        y = R_mm * math.sin(ang)
        pl.SetPoint(i, x, y, z_mm)
    return pl


# ------------------------------------------------------------
# Build plots and write to ROOT
# ------------------------------------------------------------
def make_plots(tracks_by_label,
               simhit_points,
               out_root,
               title_prefix="GGTF_3DHits",
               track_states=None,
               track_style="helix",
               Bz=2.0,
               meta_info=None,
               dch_rin_m=0.35,
               dch_rout_m=2.0,
               ring_z_mm=None):
    # Flatten to find ranges
    all_points = []
    for pts in tracks_by_label.values():
        all_points.extend(pts)
    all_points.extend(simhit_points)

    if not all_points:
        print("[warn] No points found; nothing to plot.")
        return

    xs = [p[0] for p in all_points]
    ys = [p[1] for p in all_points]
    zs = [p[2] for p in all_points]

    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)

    # Choose ring Z inside the frame so it always shows up
    if ring_z_mm is None:
        ring_z_mm = 0.5 * (zmin + zmax)

    # Expand bounds a bit
    dx = max(1.0, 0.05 * (xmax - xmin if xmax > xmin else 1.0))
    dy = max(1.0, 0.05 * (ymax - ymin if ymax > ymin else 1.0))
    dz = max(1.0, 0.05 * (zmax - zmin if zmax > zmin else 1.0))
    xmin -= dx; xmax += dx
    ymin -= dy; ymax += dy
    zmin -= dz; zmax += dz

    # Ensure the outer ring is not clipped by the frame
    dch_rin_mm  = float(dch_rin_m)  * 1000.0
    dch_rout_mm = float(dch_rout_m) * 1000.0
    rpad = 1.05 * dch_rout_mm
    xmin = min(xmin, -rpad)
    xmax = max(xmax,  rpad)
    ymin = min(ymin, -rpad)
    ymax = max(ymax,  rpad)
    # Ensure the ring z is inside the axis range too
    zmin = min(zmin, ring_z_mm - 1.0)
    zmax = max(zmax, ring_z_mm + 1.0)

    f_out = ROOT.TFile(out_root, "RECREATE")
    if not f_out or f_out.IsZombie():
        raise RuntimeError(f"Could not create output ROOT file: {out_root}")

    # Metadata
    if meta_info is not None:
        meta_str = "\n".join(f"{k}: {v}" for k, v in meta_info.items())
        ROOT.TNamed("view_tracks_metadata", meta_str).Write()

    # 2D histos from GGTF hits
    hit_points = []
    for pts in tracks_by_label.values():
        hit_points.extend(pts)

    h_xy = h_rz = None
    if hit_points:
        h_xy = ROOT.TH2F("h_xy", f"{title_prefix};x [mm];y [mm]", 200, xmin, xmax, 200, ymin, ymax)
        r_values = [math.hypot(x, y) for x, y, _ in hit_points]
        rmax = max(r_values) + 0.1 * (max(r_values) if r_values else 1.0)
        h_rz = ROOT.TH2F("h_rz", f"{title_prefix};z [mm];r [mm]", 200, zmin, zmax, 200, 0.0, rmax)
        for (x, y, z) in hit_points:
            h_xy.Fill(x, y)
            h_rz.Fill(z, math.hypot(x, y))

    # Canvases
    c_xy = ROOT.TCanvas("c_xy", "XY view", 800, 800)
    c_rz = ROOT.TCanvas("c_rz", "RZ view", 800, 800)
    c_3d = ROOT.TCanvas("c_3d", "3D hits", 900, 850)

    if h_xy:
        c_xy.cd()
        h_xy.Draw("COLZ")
    if h_rz:
        c_rz.cd()
        h_rz.Draw("COLZ")

    # 3D frame
    c_3d.cd()
    frame = ROOT.TH3F("frame3d", f"{title_prefix} 3D; x [mm]; y [mm]; z [mm]",
                      10, xmin, xmax, 10, ymin, ymax, 10, zmin, zmax)
    frame.SetStats(False)
    frame.Draw()

    markers = []
    track_lines = []
    ring_lines = []

    # GGTF markers by label
    colors = [
        ROOT.kRed + 1, ROOT.kBlue + 1, ROOT.kGreen + 1, ROOT.kMagenta + 1,
        ROOT.kCyan + 1, ROOT.kOrange + 1, ROOT.kSpring + 1, ROOT.kTeal + 1,
        ROOT.kViolet + 1, ROOT.kAzure + 1, ROOT.kPink + 1,
    ]

    for il, (lbl, pts) in enumerate(sorted(tracks_by_label.items(), key=lambda kv: kv[0])):
        if not pts:
            continue
        pm = ROOT.TPolyMarker3D(len(pts))
        pm.SetMarkerColor(colors[il % len(colors)])
        pm.SetMarkerStyle(20)
        pm.SetMarkerSize(0.8)
        for i, (x, y, z) in enumerate(pts):
            pm.SetPoint(i, x, y, z)
        pm.Draw("P SAME")
        markers.append(pm)

    # SimHits overlay
    if simhit_points:
        pm_sim = ROOT.TPolyMarker3D(len(simhit_points))
        pm_sim.SetMarkerColor(ROOT.kGreen + 2)
        pm_sim.SetMarkerStyle(20)
        pm_sim.SetMarkerSize(0.65)
        for i, (x, y, z) in enumerate(simhit_points):
            pm_sim.SetPoint(i, x, y, z)
        pm_sim.Draw("P SAME")
        markers.append(pm_sim)
        print(f"[info] Drew {len(simhit_points)} SimHits points (green).")

    # --- DCH radius rings (XY plane) ---
    # Draw at ring_z_mm (default mid-Z of event), so it always shows up in the saved 3D canvas.
    rin = make_xy_ring(dch_rin_mm, ring_z_mm, nseg=360)
    rin.SetLineColor(ROOT.kGray + 1)
    rin.SetLineWidth(2)
    rin.SetLineStyle(2)  # dashed
    rin.Draw("SAME")
    ring_lines.append(rin)

    rout = make_xy_ring(dch_rout_mm, ring_z_mm, nseg=360)
    rout.SetLineColor(ROOT.kGray + 2)
    rout.SetLineWidth(3)
    rout.SetLineStyle(1)  # solid
    rout.Draw("SAME")
    ring_lines.append(rout)

    print(f"[info] Drew DCH rings at z={ring_z_mm:.2f} mm: Rin={dch_rin_mm:.1f} mm, Rout={dch_rout_mm:.1f} mm")

    # Optional track lines (same logic as your script)
    if track_states:
        rmax_hits = max(math.hypot(x, y) for x, y in zip(xs, ys))
        s_max = 1.2 * rmax_hits
        s_min = -s_max
        n_points_line = 200

        for it, st in enumerate(track_states):
            x0, y0, z0 = st["x0"], st["y0"], st["z0"]
            phi, tl, omg = st["phi"], st["tanLambda"], st["omega"]

            pl = ROOT.TPolyLine3D(n_points_line)
            pl.SetLineColor(ROOT.kBlue if it == 0 else ROOT.kYellow)
            pl.SetLineWidth(3)

            if track_style == "straight" or not math.isfinite(omg) or Bz == 0.0:
                ux, uy, uz = math.cos(phi), math.sin(phi), tl
                norm = math.sqrt(ux*ux + uy*uy + uz*uz)
                if norm > 0:
                    ux /= norm; uy /= norm; uz /= norm
                for i in range(n_points_line):
                    s = s_min + (s_max - s_min) * i / (n_points_line - 1)
                    pl.SetPoint(i, x0 + ux*s, y0 + uy*s, z0 + uz*s)
            else:
                R_m  = 1.0 / (abs(omg) * 0.3 * abs(Bz)) if abs(omg) > 0 and abs(Bz) > 0 else 1e6
                R_mm = R_m * 1000.0
                sgn = -1.0
                if omg * Bz < 0:
                    sgn = 1.0
                xc = x0 - sgn * R_mm * math.sin(phi)
                yc = y0 + sgn * R_mm * math.cos(phi)
                alpha0 = math.atan2(y0 - yc, x0 - xc)

                cos_theta = 1.0 / math.sqrt(1.0 + tl*tl)
                sin_theta = tl * cos_theta

                for i in range(n_points_line):
                    s = s_min + (s_max - s_min) * i / (n_points_line - 1)
                    s_xy = s * cos_theta
                    alpha = alpha0 + sgn * s_xy / R_mm
                    x = xc + R_mm * math.cos(alpha)
                    y = yc + R_mm * math.sin(alpha)
                    z = z0 + s * sin_theta
                    pl.SetPoint(i, x, y, z)

            pl.Draw("SAME")
            track_lines.append(pl)

    # Write
    if h_xy:
        c_xy.Write(); h_xy.Write()
    if h_rz:
        c_rz.Write(); h_rz.Write()

    c_3d.Write()
    frame.Write()
    for pm in markers:
        pm.Write()
    for pl in track_lines:
        pl.Write()
    for rl in ring_lines:
        rl.Write()

    f_out.Close()
    print(f"[info] Wrote plots to {out_root}")


def main():
    ap = argparse.ArgumentParser(description="View GGTF_3DHits + SIM hits (+ optional tracks) for one event.")
    ap.add_argument("--input", required=True, help="Input reco ROOT file (EDM4hep)")
    ap.add_argument("--event", type=int, default=-1,
                    help="Event index (0-based). If <0, auto-find first event with GGTF_3DHits.")
    ap.add_argument("--hitsCollection", default="GGTF_3DHits",
                    help="3D hits collection base name (default: GGTF_3DHits)")
    ap.add_argument("--simCollection", default="DCHCollection",
                    help="SimTrackerHit collection base name (default: DCHCollection)")

    ap.add_argument("--trackCollection", default="GenFitTracks",
                    help="Track collection base name for GenFit TrackStates (default: GenFitTracks). "
                         "If empty, tracks will not be drawn.")
    ap.add_argument("--trackStyle", choices=["straight", "helix"], default="helix",
                    help="Visualization style for tracks: straight or helix (default: helix).")
    ap.add_argument("--Bz", type=float, default=2.0,
                    help="B-field along z [T] for helix drawing (default: 2.0).")
    ap.add_argument("--outRoot", default="simhits_display.root",
                    help="Output ROOT file for histos + canvases")

    # DCH ring controls
    ap.add_argument("--dchRin_m", type=float, default=0.35,
                    help="Inner radius to draw (meters). Default: 0.35")
    ap.add_argument("--dchRout_m", type=float, default=2.0,
                    help="Outer radius to draw (meters). Default: 2.0")
    ap.add_argument("--dchRingZ_mm", type=float, default=None,
                    help="Z position (mm) at which to draw the XY rings. "
                         "Default: mid-Z of the event (so it always appears in-frame).")

    args = ap.parse_args()

    f = ROOT.TFile.Open(args.input)
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open input file: {args.input}")

    tree = f.Get("events")
    if not tree:
        raise RuntimeError(f"No TTree named 'events' found in file: {args.input}")

    n_ev = tree.GetEntries()
    print(f"[info] File: {args.input}, events: {n_ev}")

    if args.event >= 0:
        ev_idx = args.event
        if ev_idx >= n_ev:
            raise RuntimeError(f"Requested event {ev_idx} out of range [0, {n_ev-1}]")
        print(f"[info] Using user-requested event {ev_idx}")
    else:
        ev_idx = find_first_event_with_hits(tree, args.hitsCollection)
        if ev_idx is None:
            print("[fatal] No events with 3D hits; nothing to visualize.")
            return

    tracks_by_label = load_3d_hits(tree, ev_idx, args.hitsCollection)
    sim_pts = load_simhit_positions(tree, ev_idx, args.simCollection)

    track_states = []
    if args.trackCollection:
        track_states = load_track_states(tree, ev_idx, args.trackCollection)

    meta_info = {
        "script": os.path.basename(__file__),
        "command_line": " ".join(sys.argv),
        "input_file": args.input,
        "output_file": args.outRoot,
        "event_index": ev_idx,
        "ggtf_hits_collection": args.hitsCollection,
        "simhit_collection": args.simCollection,
        "track_collection": args.trackCollection or "<none>",
        "track_style": args.trackStyle,
        "Bz_T": args.Bz,
        "dch_rin_m": args.dchRin_m,
        "dch_rout_m": args.dchRout_m,
        "dch_ring_z_mm": args.dchRingZ_mm if args.dchRingZ_mm is not None else "<auto mid-Z>",
        "user": getpass.getuser(),
        "host": socket.gethostname(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    make_plots(tracks_by_label,
               sim_pts,
               args.outRoot,
               title_prefix=f"{args.hitsCollection} + {args.simCollection} (event {ev_idx})",
               track_states=track_states,
               track_style=args.trackStyle,
               Bz=args.Bz,
               meta_info=meta_info,
               dch_rin_m=args.dchRin_m,
               dch_rout_m=args.dchRout_m,
               ring_z_mm=args.dchRingZ_mm)

    f.Close()


if __name__ == "__main__":
    main()
