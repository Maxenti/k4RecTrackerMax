#!/usr/bin/env python3
"""
DOC
dump_covmatrix_one_event.py

Dump EDM4hep TrackState covMatrix for ONE event, correctly handling
EDM4hep CovMatrix6f packed LOWER-triangle storage (21 floats).

- Auto-detects TrackState prefix (or --prefix).
- Reads the *base leaf* "<prefix>covMatrix.values" to get all values for this entry.
- Splits into per-TrackState blocks if multiple TrackStates exist in the event.
- Reconstructs and prints the full NxN covariance matrix with labels.
- Prints Var(omega) correctly.

Usage:

  python3 scripts/dump_covmatrix_one_event.py /eos/user/c/cglenn/reco_samples2/Debugging/1_20_2026/CF/eta_+1.00/reco_eta+1.00_pt14.142.root --event 0 --raw
  python3 scripts/dump_covmatrix_one_event.py file.root --event 0
  python3 scripts/dump_covmatrix_one_event.py file.root --event 0 --prefix _GenFitTracks_trackStates.
  python3 scripts/dump_covmatrix_one_event.py file.root --event 0 --raw

DOC_END
"""

import argparse
import math
import ROOT
ROOT.gROOT.SetBatch(True)

DEFAULT_PREFIXES = [
    "_GenFitTracks_trackStates.",
    "_GenFitTracks_TrackStates.",
    "GenFitTracks.trackStates.",
    "GenFitTracks.TrackStates.",
    "_GenFitTracks_trackStates_AtIP.",
    "_GenFitTracks_TrackStates_AtIP.",
    "GenFitTracks.trackStates_AtIP.",
    "GenFitTracks.TrackStates_AtIP.",
]

# EDM4hep TrackParams ordering (as used by edm4hep::TrackState)
PARAM_NAMES = ["d0", "phi", "omega", "z0", "tanLambda", "time"]

def find_tree(f: ROOT.TFile) -> ROOT.TTree:
    for name in ["events", "Events"]:
        t = f.Get(name)
        if t and t.InheritsFrom("TTree") and t.GetEntries() > 0:
            return t
    for key in f.GetListOfKeys():
        obj = f.Get(key.GetName())
        if obj and obj.InheritsFrom("TTree") and obj.GetEntries() > 0:
            return obj
    raise RuntimeError("No non-empty TTree found.")

def leaf_exists(t: ROOT.TTree, name: str) -> bool:
    return t.GetLeaf(name) is not None

def autodetect_prefix(t: ROOT.TTree) -> str:
    for p in DEFAULT_PREFIXES:
        if leaf_exists(t, p + "covMatrix.values"):
            return p
    raise RuntimeError("Could not auto-detect a prefix containing covMatrix.values")

def infer_n_from_packed_len(L: int):
    # Packed triangular length: n(n+1)/2 = L
    disc = 1 + 8*L
    if disc <= 0:
        return None
    n = int(round((-1 + math.sqrt(disc))/2))
    if n*(n+1)//2 == L:
        return n
    return None

def unpack_lower_triangle(vals, n):
    """vals length = n(n+1)/2 in LOWER-triangle row-major. Return full n x n matrix."""
    M = [[float("nan")]*n for _ in range(n)]
    k = 0
    for r in range(n):
        for c in range(r+1):
            v = vals[k]
            M[r][c] = v
            M[c][r] = v
            k += 1
    return M

def fmt(x):
    if x is None or not math.isfinite(x):
        return "nan"
    return f"{x:.6g}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--event", type=int, default=0)
    ap.add_argument("--prefix", default="AUTO")
    ap.add_argument("--raw", action="store_true", help="Print raw packed values with indices")
    ap.add_argument("--max-states", type=int, default=50, help="Safety cap if something looks weird")
    args = ap.parse_args()

    f = ROOT.TFile.Open(args.file, "READ")
    if not f or f.IsZombie():
        raise SystemExit(f"FATAL: could not open {args.file}")

    t = find_tree(f)
    nent = int(t.GetEntries())
    if args.event < 0 or args.event >= nent:
        raise SystemExit(f"FATAL: --event {args.event} out of range (0..{nent-1})")

    if args.prefix == "AUTO":
        prefix = autodetect_prefix(t)
    else:
        prefix = args.prefix
        if not leaf_exists(t, prefix + "covMatrix.values"):
            raise SystemExit(f"FATAL: leaf not found: {prefix}covMatrix.values")

    leaf_name = prefix + "covMatrix.values"
    leaf = t.GetLeaf(leaf_name)
    if not leaf:
        raise SystemExit(f"FATAL: could not get leaf {leaf_name}")

    print(f"[file]  {args.file}")
    print(f"[tree]  {t.GetName()} entries={nent}")
    print(f"[event] {args.event}")
    print(f"[pref]  {prefix}")
    print(f"[leaf]  {leaf_name}")

    t.GetEntry(args.event)

    L = int(leaf.GetLen())   # total floats for this entry (all TrackStates flattened)
    Ndata = int(leaf.GetNdata())
    # Usually GetLen()==GetNdata() for this kind of leaf
    print(f"[leaf]  GetLen()={L}  GetNdata()={Ndata}")

    if L <= 0:
        print("[cov]   no covariance data in this entry.")
        return

    # Common: 21 (CovMatrix6f packed), 15 (CovMatrix5f packed)
    # Could also be multiple states: 2*21, 3*21, ...
    per_state = None
    n = None

    # Prefer 6x6 packed if divisible by 21
    if L % 21 == 0:
        per_state = 21
        n = 6
    elif L % 15 == 0:
        per_state = 15
        n = 5
    else:
        # Try to infer n from L (single state) as packed n(n+1)/2
        n_try = infer_n_from_packed_len(L)
        if n_try is not None:
            per_state = L
            n = n_try

    if per_state is None or n is None:
        print(f"[cov]   could not infer packed covariance layout from length L={L}.")
        print("        If you expect 6x6 packed, L should be 21 * n_states.")
        return

    n_states = L // per_state
    if n_states > args.max_states:
        print(f"[cov]   inferred n_states={n_states} (cap {args.max_states}); refusing.")
        return

    print(f"[cov]   per-state length={per_state} inferred n={n} packing=lower-triangle")
    print(f"[cov]   TrackStates in this event (inferred): {n_states}")

    # Grab all values
    all_vals = [float(leaf.GetValue(i)) for i in range(L)]

    for s in range(n_states):
        block = all_vals[s*per_state:(s+1)*per_state]

        finite = [(i, v) for i, v in enumerate(block) if math.isfinite(v)]
        finite_preview = ", ".join([f"{i}:{fmt(v)}" for i, v in finite[:20]])
        print("\n" + "="*80)
        print(f"TrackState {s}/{n_states-1}")
        print(f"[finite] count={len(finite)} first20={finite_preview}")

        if args.raw:
            print("- raw packed values:")
            cols = 6
            for k in range(0, len(block), cols):
                chunk = block[k:k+cols]
                line = "  ".join([f"[{k+i:03d}] {fmt(v):>10s}" for i, v in enumerate(chunk)])
                print("  " + line)

        M = unpack_lower_triangle(block, n)

        # Print matrix with labels if it’s the standard 6 params
        if n == 6:
            labels = PARAM_NAMES
        else:
            labels = [f"p{i}" for i in range(n)]

        print(f"- reconstructed {n}x{n} covariance matrix:")
        header = "          " + " ".join([f"{lab:>10s}" for lab in labels])
        print(header)
        for r in range(n):
            row = " ".join([f"{fmt(M[r][c]):>10s}" for c in range(n)])
            print(f"  {labels[r]:>8s} {row}")

        # Var(omega) if available
        if n == 6:
            var_omega = M[2][2]
            print(f"- Var(omega) = {fmt(var_omega)}")

    f.Close()

if __name__ == "__main__":
    main()
