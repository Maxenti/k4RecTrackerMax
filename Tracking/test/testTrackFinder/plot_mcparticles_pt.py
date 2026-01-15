#!/usr/bin/env python3
"""
plot_mcparticles_pt_flatbranches.py

Reads flattened EDM4hep-style MCParticles momentum branches like:
  events/MCParticles/MCParticles.momentum.x
(and y,z), computes pT, and plots a histogram.

Usage:
  python3 plot_mcparticles_pt_flatbranches.py --input file.root
  python3 plot_mcparticles_pt_flatbranches.py --input file.root --max-events 2000
  python3 plot_mcparticles_pt_flatbranches.py --input file.root --out pt.png
"""

import argparse
import math
import numpy as np
import matplotlib.pyplot as plt

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input ROOT file")
    ap.add_argument("--tree", default="events", help="TTree name (default: events)")
    ap.add_argument("--prefix", default="MCParticles/MCParticles", help="Folder/prefix under tree (default: MCParticles/MCParticles)")
    ap.add_argument("--max-events", type=int, default=-1, help="Limit number of events to read (-1 = all)")
    ap.add_argument("--bins", type=int, default=200, help="Histogram bins")
    ap.add_argument("--range", nargs=2, type=float, default=None, metavar=("PTMIN","PTMAX"),
                    help="Optional pT range in GeV, e.g. --range 0 2")
    ap.add_argument("--out", default="mcparticles_pt.png", help="Output png")
    args = ap.parse_args()

    # --- Use uproot (recommended for these branch paths) ---
    try:
        import uproot
        import awkward as ak
    except Exception as e:
        raise SystemExit(
            "This script needs 'uproot' and 'awkward'. On lxplus/key4hep they’re often available.\n"
            "If not: python3 -m pip install --user uproot awkward\n"
            f"Import error: {e}"
        )

    px_name = f"{args.prefix}.momentum.x"
    py_name = f"{args.prefix}.momentum.y"
    # pz not needed for pT, but you can read it similarly if you want:
    # pz_name = f"{args.prefix}.momentum.z"

    with uproot.open(args.input) as f:
        if args.tree not in f:
            raise SystemExit(f"Tree '{args.tree}' not found. Available keys: {list(f.keys())}")
        t = f[args.tree]

        # Check branch existence
        for b in (px_name, py_name):
            if b not in t.keys():
                # Print a few keys to help you spot the right path
                sample_keys = list(t.keys())[:50]
                raise SystemExit(
                    f"Branch '{b}' not found.\n"
                    f"First 50 branches are:\n  " + "\n  ".join(sample_keys)
                )

        # Read jagged arrays: one list of particles per event
        arrays = t.arrays([px_name, py_name],
                          entry_stop=(args.max_events if args.max_events and args.max_events > 0 else None))

    px = arrays[px_name]
    py = arrays[py_name]

    # Compute pT per particle (still jagged), then flatten to 1D

    pt = np.sqrt(px*px + py*py)          # <- use numpy ufunc
    pt_flat = ak.to_numpy(ak.flatten(pt, axis=None))

    # Basic stats
    if pt_flat.size == 0:
        raise SystemExit("No MCParticles found / pT array is empty.")

    print(f"[info] N particles = {pt_flat.size}")
    print(f"[info] pT min/median/mean/max = "
          f"{pt_flat.min():.6g} / {np.median(pt_flat):.6g} / {pt_flat.mean():.6g} / {pt_flat.max():.6g} (GeV)")

    # Plot
    plt.figure()
    hist_kwargs = dict(bins=args.bins)
    if args.range is not None:
        hist_kwargs["range"] = (args.range[0], args.range[1])

    plt.hist(pt_flat, **hist_kwargs)
    plt.xlabel("MCParticles pT [GeV]")
    plt.ylabel("Counts")
    plt.title("MCParticles pT distribution")
    plt.tight_layout()
    plt.savefig(args.out, dpi=200)
    print(f"[info] Wrote {args.out}")

if __name__ == "__main__":
    main()
