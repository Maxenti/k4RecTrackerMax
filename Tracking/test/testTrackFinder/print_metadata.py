#!/usr/bin/env python3
import sys
import os
import ROOT

def main():
    if len(sys.argv) < 2:
        print("Usage: print_metadata.py <file.root>")
        sys.exit(1)

    fname = sys.argv[1]
    if not os.path.exists(fname):
        print(f"[error] File not found: {fname}")
        sys.exit(1)

    ROOT.gROOT.SetBatch(True)

    f = ROOT.TFile.Open(fname)
    if not f or f.IsZombie():
        print(f"[error] Could not open ROOT file: {fname}")
        sys.exit(1)

    # Common tree names used by podio/EDM4hep
    candidates = [
        "metadata",
        "runMetadata",
        "MetaData",
        "metaData",
    ]

    found_any = False
    print(f"[info] Scanning metadata-like trees in {fname}")

    for tname in candidates:
        t = f.Get(tname)
        if not t:
            continue

        found_any = True
        print("\n====================================================")
        print(f"[tree] '{tname}' : entries = {t.GetEntries()}")
        print("----------------------------------------------------")
        print("[structure]")
        t.Print()  # prints branches and their types

        # Show first few entries (JSON strings will appear here)
        n_show = min(3, t.GetEntries())
        for i in range(n_show):
            print(f"\n[entry {i}] in tree '{tname}':")
            t.Show(i)

    if not found_any:
        print("[warn] No metadata-like trees found (tried: "
              + ", ".join(candidates) + ")")

    f.Close()

if __name__ == "__main__":
    main()
