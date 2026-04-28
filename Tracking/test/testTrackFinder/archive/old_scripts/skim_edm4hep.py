#!/usr/bin/env python3
import argparse
import os
import sys

def has_leaf(tree, name: str) -> bool:
    try:
        return bool(tree.GetLeaf(name))
    except Exception:
        return False

def skim_with_root_leaves(fin_path, fout_path, coll, tmax_ns, nhits_max, keep_empty):
    import ROOT
    ROOT.gROOT.SetBatch(True)

    fin_path  = os.path.abspath(fin_path)
    fout_path = os.path.abspath(fout_path)

    fin = ROOT.TFile.Open(fin_path)
    if not fin or fin.IsZombie():
        raise RuntimeError(f"Cannot open input: {fin_path}")

    tin = fin.Get("events")
    if not tin:
        raise RuntimeError("No TTree named 'events' in input file")

    # We’ll use position.z to count hits (GetNdata), and time to compute max.
    z_leaf = tin.GetLeaf(f"{coll}.position.z")
    t_leaf = tin.GetLeaf(f"{coll}.time")

    if not z_leaf or not t_leaf:
        raise RuntimeError(
            f"[ROOT-leaf mode] Missing required leaves.\n"
            f"Need: {coll}.position.z and {coll}.time\n"
            f"Found position.z={bool(z_leaf)} time={bool(t_leaf)}"
        )

    fout = ROOT.TFile(fout_path, "RECREATE")
    if not fout or fout.IsZombie():
        raise RuntimeError(f"Cannot create output: {fout_path}")

    # Copy everything except events first (metadata trees, etc.)
    for key in fin.GetListOfKeys():
        name = key.GetName()
        if name == "events":
            continue
        obj = key.ReadObj()
        fout.cd()
        obj.Write()

    tout = tin.CloneTree(0)

    n_in = tin.GetEntries()
    kept = 0
    dropped = 0

    for iev in range(n_in):
        tin.GetEntry(iev)

        n_hits = int(z_leaf.GetNdata())
        if n_hits <= 0:
            if keep_empty:
                tout.Fill(); kept += 1
            else:
                dropped += 1
            continue

        if nhits_max > 0 and n_hits > nhits_max:
            dropped += 1
            continue

        # max time
        n_t = int(t_leaf.GetNdata())
        tmax = -1e30
        for i in range(n_t):
            t = float(t_leaf.GetValue(i))
            if t > tmax:
                tmax = t

        if tmax <= tmax_ns:
            tout.Fill(); kept += 1
        else:
            dropped += 1

    fout.cd()
    tout.Write()
    fout.Close()
    fin.Close()

    print(f"[skim][ROOT-leaf] infile={fin_path}")
    print(f"[skim][ROOT-leaf] outfile={fout_path}")
    print(f"[skim][ROOT-leaf] coll={coll} cut: tmax<={tmax_ns} ns, nHits<={nhits_max} keep_empty={keep_empty}")
    print(f"[skim][ROOT-leaf] events in={n_in} kept={kept} dropped={dropped}")

def skim_with_podio(fin_path, fout_path, coll, tmax_ns, nhits_max, keep_empty):
    fin_path  = os.path.abspath(fin_path)
    fout_path = os.path.abspath(fout_path)

    # Podio python APIs differ a bit across releases; this is the most common.
    from podio import root_io

    reader = root_io.Reader(fin_path)
    writer = root_io.Writer(fout_path)

    total = 0
    kept = 0
    dropped = 0

    for frame in reader:
        total += 1

        try:
            hits = frame.get(coll)
        except Exception as e:
            raise RuntimeError(
                f"[PODIO mode] Could not get collection '{coll}' from frame.\n"
                f"Error: {e}"
            )

        n_hits = len(hits)
        if n_hits <= 0:
            if keep_empty:
                writer.write_frame(frame, "events")
                kept += 1
            else:
                dropped += 1
            continue

        if nhits_max > 0 and n_hits > nhits_max:
            dropped += 1
            continue

        # SimTrackerHit time is available as getTime()
        # Position is typically a Vector3f: hit.getPosition().z
        tmax = -1e30
        for h in hits:
            t = float(h.getTime())
            if t > tmax:
                tmax = t

        if tmax <= tmax_ns:
            writer.write_frame(frame, "events")
            kept += 1
        else:
            dropped += 1

    writer.finish()

    print(f"[skim][PODIO] infile={fin_path}")
    print(f"[skim][PODIO] outfile={fout_path}")
    print(f"[skim][PODIO] coll={coll} cut: tmax<={tmax_ns} ns, nHits<={nhits_max} keep_empty={keep_empty}")
    print(f"[skim][PODIO] events in={total} kept={kept} dropped={dropped}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--coll", default="DCHCollection")
    ap.add_argument("--tmax", type=float, default=450.0)
    ap.add_argument("--nhits-max", type=int, default=30000)
    ap.add_argument("--keep-empty", action="store_true", default=False)
    ap.add_argument("--force-mode", choices=["auto", "root", "podio"], default="auto",
                    help="auto: try ROOT leaves then PODIO. root: only ROOT leaves. podio: only PODIO.")
    args = ap.parse_args()

    # AUTO detection: check if the subleaves exist
    if args.force_mode in ("auto", "root"):
        try:
            import ROOT
            ROOT.gROOT.SetBatch(True)
            f = ROOT.TFile.Open(args.input)
            t = f.Get("events") if f else None
            ok = bool(t) and has_leaf(t, f"{args.coll}.time") and has_leaf(t, f"{args.coll}.position.z")
            if f: f.Close()
        except Exception:
            ok = False

        if args.force_mode == "root":
            if not ok:
                raise RuntimeError(
                    f"force-mode=root but leaves are missing: "
                    f"{args.coll}.time or {args.coll}.position.z"
                )
            skim_with_root_leaves(args.input, args.output, args.coll, args.tmax, args.nhits_max, args.keep_empty)
            return

        if ok:
            skim_with_root_leaves(args.input, args.output, args.coll, args.tmax, args.nhits_max, args.keep_empty)
            return

    # Fall back to PODIO
    skim_with_podio(args.input, args.output, args.coll, args.tmax, args.nhits_max, args.keep_empty)

if __name__ == "__main__":
    main()
