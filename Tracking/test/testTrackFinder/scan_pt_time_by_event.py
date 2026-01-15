#!/usr/bin/env python3
"""
scan_pt_time_by_event.py

Scan an EDM4hep ROOT file event-by-event and extract pT from TrackState.time for a given track collection.

Outputs a ranked list of either:
  - "bad" events: largest deviation from expected pT
  - "good" events: smallest deviation from expected pT

Assumptions (matches your fitter convention):
  - TrackState.time encodes pT [GeV]
  - TrackState.omega encodes q/pT [GeV^-1] (so pT_from_omega = 1/|omega|)
  - TrackState fields are in the Track collection's trackStates array, associated using
    <Tracks>.trackStates_begin/end (if available). If not available, uses flat array.

Usage examples:
  python3 scan_pt_time_by_event.py --input reco.root --expectedPt 60.88
  python3 scan_pt_time_by_event.py --input reco.root --expectedPt 60.88 --top 40 --type bad
  python3 scan_pt_time_by_event.py --input reco.root --expectedPt 60.88 --top 40 --type good
  python3 scan_pt_time_by_event.py --input reco.root --expectedPt 60.88 --metric rel --type bad --csv out.csv
  python3 scan_pt_time_by_event.py --input reco.root --expectedPt 60.88 --event 500 --verbose
"""

import argparse
import math
import csv
import ROOT
ROOT.gROOT.SetBatch(True)


def _find_leaf(tree, name):
    return tree.GetLeaf(name)


def _scan_leaf_by_suffix(tree, coll_name, suffix):
    leaves = tree.GetListOfLeaves()
    if not leaves:
        return None
    for obj in leaves:
        nm = obj.GetName()
        if coll_name in nm and nm.endswith(suffix):
            return nm
    return None


def resolve_ts_prefix(tree, coll_name):
    candidates = [
        f"{coll_name}.trackStates.",
        f"{coll_name}.TrackStates.",
        f"{coll_name}.trackStates_AtIP.",
        f"{coll_name}.TrackStates_AtIP.",
        f"_{coll_name}_trackStates.",  # sometimes podio writes underscored collection names
        f"_{coll_name}_TrackStates.",
    ]
    for pref in candidates:
        if _find_leaf(tree, pref + "phi"):
            return pref

    # fallback scan for "<something>.phi"
    leaves = tree.GetListOfLeaves()
    if not leaves:
        return None
    for obj in leaves:
        name = obj.GetName()
        if coll_name in name and name.endswith(".phi"):
            return name[:-len("phi")]
    return None


def resolve_begin_end(tree, coll_name):
    # direct common names
    pairs = [
        (f"{coll_name}.trackStates_begin", f"{coll_name}.trackStates_end"),
        (f"{coll_name}.TrackStates_begin", f"{coll_name}.TrackStates_end"),
    ]
    for b, e in pairs:
        if _find_leaf(tree, b) and _find_leaf(tree, e):
            return b, e

    # fallback scan
    b = _scan_leaf_by_suffix(tree, coll_name, "trackStates_begin")
    e = _scan_leaf_by_suffix(tree, coll_name, "trackStates_end")
    if b and e:
        return b, e
    b = _scan_leaf_by_suffix(tree, coll_name, "TrackStates_begin")
    e = _scan_leaf_by_suffix(tree, coll_name, "TrackStates_end")
    if b and e:
        return b, e
    return None, None


def scan_file(path, track_coll, expected_pt, top_n=30, event_filter=None, verbose=False):
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open: {path}")

    tree = f.Get("events")
    if not tree:
        raise RuntimeError("No TTree named 'events'")

    prefix = resolve_ts_prefix(tree, track_coll)
    if not prefix:
        raise RuntimeError(f"Could not resolve TrackState prefix for '{track_coll}'")

    # Leaves we need
    time_leaf = _find_leaf(tree, prefix + "time")
    omg_leaf  = _find_leaf(tree, prefix + "omega")
    phi_leaf  = _find_leaf(tree, prefix + "phi")  # for GetNdata()
    if not time_leaf or not phi_leaf:
        raise RuntimeError(f"Missing required leaves: '{prefix}time' and/or '{prefix}phi'")

    bname, ename = resolve_begin_end(tree, track_coll)
    beg_leaf = _find_leaf(tree, bname) if bname else None
    end_leaf = _find_leaf(tree, ename) if ename else None

    n_ev = tree.GetEntries()
    results = []

    ev_range = range(n_ev) if event_filter is None else [event_filter]
    for iev in ev_range:
        tree.GetEntry(iev)

        n_states = int(phi_leaf.GetNdata())
        if n_states <= 0:
            continue

        # flat arrays of pT(time) and pT(omega)
        pts_time = []
        pts_omg  = []
        for si in range(n_states):
            pt_t = float(time_leaf.GetValue(si))
            pts_time.append(pt_t)

            if omg_leaf:
                omg = float(omg_leaf.GetValue(si))
                pt_o = (1.0 / abs(omg)) if (math.isfinite(omg) and abs(omg) > 0) else float("nan")
            else:
                pt_o = float("nan")
            pts_omg.append(pt_o)

        # If we have per-track association, compute per-track pT and then choose the “primary” track.
        per_track_pts = []
        if beg_leaf and end_leaf:
            n_tracks = int(beg_leaf.GetNdata())
            for ti in range(n_tracks):
                b = int(beg_leaf.GetValue(ti))
                e = int(end_leaf.GetValue(ti))
                if b < 0 or e < 0 or e <= b or b >= n_states:
                    continue
                e = min(e, n_states)

                seg = [pts_time[k] for k in range(b, e)]
                seg = [x for x in seg if math.isfinite(x)]
                if not seg:
                    continue
                seg.sort()
                pt_rep = seg[len(seg)//2]  # median
                per_track_pts.append((ti, pt_rep, b, e))

        # Choose one “primary” pT per event to rank:
        # - If we have per-track pts, use the one closest to expected_pt
        # - else use median over all states
        if per_track_pts:
            ti, pt_primary, b, e = min(per_track_pts, key=lambda t: abs(t[1] - expected_pt))
            assoc_note = f"track={ti} states[{b}:{e})"
        else:
            seg = [x for x in pts_time if math.isfinite(x)]
            if not seg:
                continue
            seg.sort()
            pt_primary = seg[len(seg)//2]
            assoc_note = "flatStates(median)"

        abs_err = abs(pt_primary - expected_pt)
        rel_err = abs_err / expected_pt if expected_pt > 0 else float("inf")

        finite_pts = [x for x in pts_time if math.isfinite(x)]
        pt_min = min(finite_pts) if finite_pts else float("nan")
        pt_max = max(finite_pts) if finite_pts else float("nan")

        results.append({
            "event": iev,
            "pt_primary": pt_primary,
            "abs_err": abs_err,
            "rel_err": rel_err,
            "n_states": n_states,
            "pt_min": pt_min,
            "pt_max": pt_max,
            "assoc": assoc_note,
        })

        if verbose:
            print(f"[ev {iev:5d}] pT_primary={pt_primary:10.3f}  absErr={abs_err:10.3f}  relErr={rel_err:10.3f}  "
                  f"nStates={n_states:3d}  pTmin={pt_min:10.3f}  pTmax={pt_max:10.3f}  {assoc_note}")

    f.Close()
    return results, n_ev, len(list(ev_range))


def write_csv(results, out_csv):
    if not results:
        print(f"[warn] no results to write CSV: {out_csv}")
        return
    with open(out_csv, "w", newline="") as fp:
        fieldnames = list(results[0].keys())
        w = csv.DictWriter(fp, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(f"[info] wrote CSV: {out_csv}")


def main():
    ap = argparse.ArgumentParser(description="Scan TrackState.time pT event-by-event and rank events.")
    ap.add_argument("--input", required=True, help="Input EDM4hep ROOT file")
    ap.add_argument("--trackCollection", default="GenFitTracks", help="Track collection name (default: GenFitTracks)")
    ap.add_argument("--expectedPt", type=float, required=True, help="Expected pT for this sample [GeV]")
    ap.add_argument("--top", type=int, default=30, help="How many events to print (default: 30)")
    ap.add_argument("--event", type=int, default=None, help="If set, scan only this event index")
    ap.add_argument("--csv", default=None, help="Optional output CSV with per-event results")
    ap.add_argument("--verbose", action="store_true", help="Print one line per event")

    ap.add_argument("--type", choices=["bad", "good"], default="bad",
                    help="Ranking type: 'bad' = largest error, 'good' = smallest error (default: bad)")
    ap.add_argument("--metric", choices=["abs", "rel"], default="abs",
                    help="Sort metric: abs=|pT-expected|, rel=|pT-expected|/expected (default: abs)")

    args = ap.parse_args()

    results, n_ev, n_scanned = scan_file(
        args.input,
        args.trackCollection,
        args.expectedPt,
        top_n=args.top,
        event_filter=args.event,
        verbose=args.verbose
    )

    if not results:
        print(f"[summary] scanned {n_scanned} event(s) (file has {n_ev} events) but found no TrackStates.")
        return

    key = "abs_err" if args.metric == "abs" else "rel_err"
    reverse = True if args.type == "bad" else False
    results.sort(key=lambda r: r[key], reverse=reverse)

    n_show = min(args.top, len(results))
    label = "worst" if args.type == "bad" else "best"
    metric_label = "|pT-expected|" if args.metric == "abs" else "|pT-expected|/expected"

    print(f"\n[summary] scanned {n_scanned} event(s) (file has {n_ev} events)")
    print(f"[summary] expectedPt = {args.expectedPt:.6g} GeV")
    print(f"[summary] showing top {n_show} {label} events by {metric_label}:\n")

    print(f"{'rank':>4s} {'event':>6s} {'pT_primary':>12s} {'absErr':>12s} {'relErr':>12s} "
          f"{'nStates':>7s} {'pTmin':>12s} {'pTmax':>12s}  assoc")
    for i, r in enumerate(results[:n_show], 1):
        print(f"{i:4d} {r['event']:6d} {r['pt_primary']:12.3f} {r['abs_err']:12.3f} {r['rel_err']:12.3f} "
              f"{r['n_states']:7d} {r['pt_min']:12.3f} {r['pt_max']:12.3f}  {r['assoc']}")

    if args.csv:
        write_csv(results, args.csv)


if __name__ == "__main__":
    main()
