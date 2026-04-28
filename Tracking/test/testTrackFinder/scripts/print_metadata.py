#!/usr/bin/env python3


"""
DOC
Summary: Print metadata-like ROOT trees from an EDM4hep/PODIO ROOT file for quick provenance inspection.
Status: secondary
Usage:
  python3 scripts/print_metadata.py FILE.root
Examples:
  python3 scripts/print_metadata.py /eos/.../reco_eta+1.00_pt14.142.root
  python3 scripts/print_metadata.py /eos/.../gun_eta+1.00_pt14.142.root
Inputs: ROOT file containing optional metadata-like TTrees.
Outputs: Terminal dump of metadata tree structure and the first few entries from each detected metadata-like tree.
Collections: None; reads metadata-style ROOT TTrees, not EDM4hep event collections.
Connects-To: scripts/stamp_pipeline_metadata.py, scripts/stamp_ddsim_metadata.py, scripts/reco_job.sh, scripts/condor_ddsim.sh, steering/local_chain.sh
Arguments:
  file.root: input ROOT file to inspect.
Notes:
  The script checks common metadata tree names: metadata, runMetadata, MetaData, and metaData.
  For each found tree, it prints the ROOT branch structure with TTree.Print() and shows up to the first three entries with TTree.Show().
  This is intended for quick validation of provenance stamping after DDSim production, local-chain reco, or Condor reco jobs.
  It does not inspect the standard PODIO events or podio_metadata trees.
  Use this after stamp_ddsim_metadata.py or stamp_pipeline_metadata.py when verifying campaign/job metadata was embedded correctly.
Tags: secondary, metadata, provenance, root, edm4hep, podio, diagnostics
DOC_END
"""



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
