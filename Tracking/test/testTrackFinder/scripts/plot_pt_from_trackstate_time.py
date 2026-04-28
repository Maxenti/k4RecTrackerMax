#!/usr/bin/env python3
"""
DOC
Summary: Plot pT values stored in EDM4hep TrackState.time for a selected track collection, with flexible event selection, filtering, and histogram binning.
Status: secondary
Usage:
  python3 scripts/plot_pt_from_trackstate_time.py -i RECO.root --coll GenFitTracks --bins 80 -o pt.png
  python3 scripts/plot_pt_from_trackstate_time.py -i RECO.root --coll GenFitTracks --bins 0:200:200 --logy -o pt_0_200_logy.png
Examples:
  python3 scripts/plot_pt_from_trackstate_time.py \
    -i /eos/.../reco_eta+1.00_pt14.142.root \
    --coll GenFitTracks \
    --bins 0:200:200 \
    --per-event median \
    --logy \
    -o artifacts/analysis/pt_from_trackstate_time_eta+1.00.png
Inputs: EDM4hep/ROOT reco file containing an events TTree and TrackState.time leaf for the selected track collection.
Outputs: Histogram image file, usually PNG or PDF, showing pT values read from TrackState.time.
Collections: Reads TrackState.time from GenFitTracks by default; supports common branch layouts such as GenFitTracks.trackStates.time, GenFitTracks.TrackStates.time, _GenFitTracks_trackStates.time, and _GenFitTracks_TrackStates.time.
Connects-To: scripts/pt_diagnostics_to_root.py, scripts/inspect_events_pt_pathology.py, scripts/scan_pt_time_by_event.py, scripts/dump_covmatrix_one_event.py, steering/runDCHTestTrackFinder.py
Arguments:
  -i, --input: input EDM4hep ROOT reco file.
  --tree: TTree name; default events.
  --coll: track collection name; default GenFitTracks.
  --leaf: explicit TrackState.time leaf name; overrides auto-detection.
  --invalid-sentinel: invalid pT marker value stored in TrackState.time; default -1.0.
  --include-invalid: include invalid sentinel values instead of dropping them.
  --min: minimum pT value to keep in GeV.
  --max: maximum pT value to keep in GeV.
  --per-event: reduction mode for multiple TrackState.time values per event; choices are all, first, median, mean; default all.
  --max-events: process only the first N events.
  --events: comma-separated list of zero-based event indices to process.
  --bins: histogram binning as either N or min:max:nbins; default 80.
  --bin-edges: comma-separated custom bin edges; overrides --bins.
  --logy: draw histogram with logarithmic y-axis.
  --title: custom plot title.
  -o, --out: output image file path; default pt_hist.png.
  --dpi: output image DPI; default 160.
  --show: display an interactive matplotlib window when available.
  --verbose: print TrackState.time leaf auto-detection diagnostics.
Notes:
  This script assumes the project convention that TrackState.time may carry reconstructed pT in GeV for diagnostic/publication purposes.
  Auto-detection tries several common EDM4hep/k4 branch naming patterns and falls back to scanning all leaves for collection/time matches.
  Use --per-event median or --per-event first when you want one pT entry per event instead of one entry per TrackState.
  Invalid sentinel values are dropped by default so failed fits do not dominate the histogram.
  This is a diagnostic plotting utility, not a replacement for the full pT-resolution analysis chain.
  Pair this with pt_diagnostics_to_root.py, inspect_events_pt_pathology.py, or dump_covmatrix_one_event.py when debugging TrackState.time versus omega behavior.
Tags: secondary, diagnostics, plotting, pt, trackstate, genfittracks, root, matplotlib, edm4hep
DOC_END
"""

import argparse
import math
import re
import sys

def parse_bins(bins_str):
    """
    Accept:
      - integer: "80"
      - min:max:nbins : "0:200:200"
    """
    if bins_str is None:
        return None
    s = bins_str.strip()
    if re.fullmatch(r"\d+", s):
        return int(s), None  # (nbins, range)
    m = re.fullmatch(r"([+-]?\d*\.?\d+):([+-]?\d*\.?\d+):(\d+)", s)
    if m:
        lo = float(m.group(1))
        hi = float(m.group(2))
        nb = int(m.group(3))
        return nb, (lo, hi)
    raise ValueError(f"Unrecognized --bins format: {bins_str!r}. Use '80' or 'min:max:nbins' like '0:200:200'.")

def parse_edges(edges_str):
    if edges_str is None:
        return None
    edges = [float(x) for x in edges_str.split(",") if x.strip() != ""]
    if len(edges) < 2:
        raise ValueError("Need at least 2 edges for --bin-edges")
    # ensure strictly increasing
    for a, b in zip(edges, edges[1:]):
        if not (b > a):
            raise ValueError("Edges must be strictly increasing.")
    return edges

def is_finite(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)

def pick_time_leaf(tree, coll, explicit_leaf=None, verbose=False):
    """
    Try hard to find the leaf corresponding to TrackState.time for a given collection.
    Supports a bunch of common EDM4hep ROOT naming patterns.
    """
    if explicit_leaf:
        leaf = tree.GetLeaf(explicit_leaf)
        if not leaf:
            raise RuntimeError(f"Requested leaf not found: {explicit_leaf}")
        return explicit_leaf, leaf

    # Common candidates (covers lots of k4/edm4hep ROOT variations)
    candidates = [
        f"{coll}.trackStates.time",
        f"{coll}.TrackStates.time",
        f"{coll}.trackStates_AtIP.time",
        f"{coll}.TrackStates_AtIP.time",
        f"_{coll}_trackStates.time",
        f"_{coll}_TrackStates.time",
        f"_{coll}_trackStates_AtIP.time",
        f"_{coll}_TrackStates_AtIP.time",
    ]

    for name in candidates:
        leaf = tree.GetLeaf(name)
        if leaf:
            return name, leaf

    # Fallback: scan all leaves and pick a best match
    leaves = tree.GetListOfLeaves()
    all_names = [leaves.At(i).GetName() for i in range(leaves.GetEntries())]

    # Score leaves that look like the right thing
    def score(n):
        s = 0
        if coll in n:
            s += 5
        if "trackStates" in n or "TrackStates" in n:
            s += 5
        if n.endswith(".time") or n.endswith("_time") or n.endswith("time"):
            s += 3
        # prefer ones explicitly containing ".time"
        if ".time" in n:
            s += 2
        return s

    scored = sorted([(score(n), n) for n in all_names], reverse=True)
    best_score, best_name = scored[0] if scored else (0, None)

    if verbose:
        print("[debug] Top candidate leaves:")
        for sc, nm in scored[:10]:
            print(f"  score={sc:2d}  {nm}")

    if best_score < 8 or not best_name:
        # Print helpful info
        near = [n for n in all_names if (coll in n and ("time" in n.lower()))]
        msg = [
            f"Could not reliably auto-detect TrackState.time leaf for collection '{coll}'.",
            "Try passing --leaf <leafname> explicitly.",
        ]
        if near:
            msg.append("Leaves containing your collection + 'time':")
            msg.extend([f"  {n}" for n in near[:40]])
        raise RuntimeError("\n".join(msg))

    leaf = tree.GetLeaf(best_name)
    if not leaf:
        raise RuntimeError(f"Auto-picked leaf name '{best_name}' but GetLeaf returned null.")
    return best_name, leaf

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True, help="Input EDM4hep ROOT file (reco output).")
    ap.add_argument("--tree", default="events", help="TTree name (default: events).")
    ap.add_argument("--coll", default="GenFitTracks", help="Track collection name (default: GenFitTracks).")
    ap.add_argument("--leaf", default=None, help="Explicit leaf name to read (overrides auto-detect).")

    ap.add_argument("--invalid-sentinel", type=float, default=-1.0,
                    help="Value used for invalid pT in ts.time (default: -1).")
    ap.add_argument("--include-invalid", action="store_true",
                    help="Include invalid sentinel values in the histogram (default: drop them).")
    ap.add_argument("--min", dest="xmin", type=float, default=None, help="Minimum pT to keep (GeV).")
    ap.add_argument("--max", dest="xmax", type=float, default=None, help="Maximum pT to keep (GeV).")

    ap.add_argument("--per-event", choices=["all", "first", "median", "mean"], default="all",
                    help="How to reduce multiple TrackState.time values per event. "
                         "'all' = histogram all values (default).")
    ap.add_argument("--max-events", type=int, default=None, help="Only process first N events.")
    ap.add_argument("--events", default=None,
                    help="Comma-separated list of event indices to process (0-based).")

    ap.add_argument("--bins", default="80",
                    help="Binning: 'N' or 'min:max:nbins' (default: 80). Ignored if --bin-edges is set.")
    ap.add_argument("--bin-edges", default=None,
                    help="Comma-separated custom bin edges, e.g. '0,1,2,5,10,20,50,100,200'.")

    ap.add_argument("--logy", action="store_true", help="Log scale on y-axis.")
    ap.add_argument("--title", default=None, help="Plot title.")
    ap.add_argument("-o", "--out", default="pt_hist.png", help="Output image file (png/pdf/etc).")
    ap.add_argument("--dpi", type=int, default=160, help="Output DPI (default: 160).")
    ap.add_argument("--show", action="store_true", help="Show an interactive window (if available).")
    ap.add_argument("--verbose", action="store_true", help="Verbose diagnostics.")
    args = ap.parse_args()

    # Imports that require local environment
    try:
        import ROOT
        ROOT.gROOT.SetBatch(True)  # still allows saving; --show uses mpl
    except Exception as e:
        print("ERROR: Failed to import ROOT (PyROOT). Are you in a Key4HEP environment?")
        print(e)
        return 2

    import numpy as np
    import matplotlib
    import matplotlib.pyplot as plt

    # Open file/tree
    f = ROOT.TFile.Open(args.input)
    if not f or f.IsZombie():
        print(f"ERROR: Could not open file: {args.input}")
        return 2

    tree = f.Get(args.tree)
    if not tree:
        print(f"ERROR: Could not find TTree '{args.tree}' in file.")
        print("Tip: run `rootls -t <file.root>` or `root -l <file.root>` and check tree names.")
        return 2

    leaf_name, leaf = pick_time_leaf(tree, args.coll, explicit_leaf=args.leaf, verbose=args.verbose)
    if args.verbose:
        print(f"[info] Using leaf: {leaf_name}")

    # Event selection
    n_entries = int(tree.GetEntries())
    event_list = None
    if args.events:
        event_list = [int(x) for x in args.events.split(",") if x.strip() != ""]
        for ev in event_list:
            if ev < 0 or ev >= n_entries:
                print(f"ERROR: event index out of range: {ev} (n_entries={n_entries})")
                return 2

    def keep_value(v):
        if not is_finite(v):
            return False
        if (not args.include_invalid) and (v == args.invalid_sentinel):
            return False
        if args.xmin is not None and v < args.xmin:
            return False
        if args.xmax is not None and v > args.xmax:
            return False
        return True

    # Read values
    values = []
    n_proc = 0
    n_skipped_empty = 0
    n_invalid = 0

    if event_list is None:
        indices = range(n_entries if args.max_events is None else min(n_entries, args.max_events))
    else:
        indices = event_list

    for ievt in indices:
        tree.GetEntry(ievt)
        n_proc += 1

        # leaf can be a vector; GetLen gives current length
        try:
            n = int(leaf.GetLen())
        except Exception:
            n = 1

        evt_vals = []
        for j in range(max(1, n)):
            try:
                v = float(leaf.GetValue(j))
            except Exception:
                continue
            if (not args.include_invalid) and (v == args.invalid_sentinel):
                n_invalid += 1
                continue
            if keep_value(v):
                evt_vals.append(v)
            else:
                if v == args.invalid_sentinel:
                    n_invalid += 1

        if not evt_vals:
            n_skipped_empty += 1
            continue

        if args.per_event == "all":
            values.extend(evt_vals)
        elif args.per_event == "first":
            values.append(evt_vals[0])
        elif args.per_event == "median":
            values.append(float(np.median(evt_vals)))
        elif args.per_event == "mean":
            values.append(float(np.mean(evt_vals)))

    if len(values) == 0:
        print("No values found after filtering.")
        print(f"Processed events: {n_proc}, empty-after-filter events: {n_skipped_empty}, invalid dropped: {n_invalid}")
        return 1

    arr = np.asarray(values, dtype=float)

    # Binning
    edges = parse_edges(args.bin_edges) if args.bin_edges else None
    if edges is not None:
        bins = np.asarray(edges, dtype=float)
        hist_range = None
    else:
        nbins, hist_range = parse_bins(args.bins)
        bins = nbins

    # Plot
    plt.figure(figsize=(9.2, 5.6))
    plt.hist(arr, bins=bins, range=hist_range, histtype="stepfilled", alpha=0.85)
    plt.xlabel("pT from TrackState.time [GeV]")
    plt.ylabel("Entries")
    if args.logy:
        plt.yscale("log")

    title = args.title
    if title is None:
        title = f"{args.coll}: pT from TrackState.time"
        if args.per_event != "all":
            title += f" (per-event: {args.per_event})"
    plt.title(title)

    # Stats annotation
    mean = float(np.mean(arr))
    med = float(np.median(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    q16, q84 = np.percentile(arr, [16, 84])

    txt = (
        f"N = {len(arr)}\n"
        f"mean = {mean:.4g} GeV\n"
        f"median = {med:.4g} GeV\n"
        f"std = {std:.4g} GeV\n"
        f"16–84% = [{q16:.4g}, {q84:.4g}] GeV\n"
        f"leaf = {leaf_name}"
    )
    plt.gca().text(
        0.98, 0.98, txt,
        transform=plt.gca().transAxes,
        ha="right", va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="0.7")
    )

    plt.tight_layout()
    plt.savefig(args.out, dpi=args.dpi)
    print(f"Wrote: {args.out}")
    print(f"Processed events: {n_proc}, empty-after-filter events: {n_skipped_empty}, invalid dropped: {n_invalid}")
    print(f"Values kept: {len(arr)}  |  mean={mean:.6g}  median={med:.6g}  std={std:.6g}")

    if args.show:
        plt.show()

    return 0

if __name__ == "__main__":
    sys.exit(main())
