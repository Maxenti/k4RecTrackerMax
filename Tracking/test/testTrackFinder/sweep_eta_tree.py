#!/usr/bin/env python3
"""
pt_resolution_plot.py
---------------------

Combine many reco outputs into a single plot: pT resolution vs pT,
with one curve per |eta| in {0.0, 0.5, 1.0, 1.5, 2.0}.

Assumptions / conventions:
- Files live under .../eta+X.XX/*.root or .../eta_X.XX/*.root
- Filename contains energy tag like *_E2.3224*.root  (GeV)
- Single-particle gun; true pT is inferred from (E, eta, PDG mass)
- Reco pT is taken from the *best* track per event (see selection below)
- Works with EDM4hep PODIO trees via uproot; it autodetects several common
  GenFit output branch layouts:
    1) TrackStates momentum components:
         "GenFitTracksStates.momentum.x/y/z"   (preferred)
    2) Track-level momentum components:
         "GenFitTracks.momentum.x/y/z"
    3) TrackStates qOverP + tanLambda:
         "GenFitTracksStates.qOverP" + "GenFitTracksStates.tanLambda"
    4) Fallback: per-track qOverP + tanLambda if present

If multiple tracks exist in an event, we pick the one with the largest
attached-measurement count when available; otherwise the first fitted/converged;
otherwise the first track.

Outputs:
- A PNG and a CSV (optional) summarizing bin centers & resolutions per eta-slice.
"""

import os, re, math, argparse, json
from pathlib import Path
import numpy as np
import uproot
import awkward as ak
import matplotlib.pyplot as plt

# ------------------------------ parsing helpers ------------------------------

ETA_DIR_RE = re.compile(r"^eta[_]?([+-]?\d+(?:\.\d+)?)$")
E_TAG_RE   = re.compile(r"(?:^|_)E([0-9]+(?:\.[0-9]+)?)")

PDG_MASS_GEV = {
    11: 0.000510999, -11: 0.000510999,
    13: 0.1056583755, -13: 0.1056583755,
    211: 0.13957039, -211: 0.13957039,
    321: 0.493677, -321: 0.493677,
    2212: 0.938272088, -2212: 0.938272088,
}

def parse_eta_from_path(p: Path) -> float | None:
    # Accept eta folder itself or parent of file
    candidates = [p.parent.name, p.parent.parent.name]
    for name in candidates:
        m = ETA_DIR_RE.match(name)
        if m:
            return float(m.group(1))
    return None

def parse_energy_from_fname(fname: str) -> float | None:
    m = E_TAG_RE.search(fname)
    return float(m.group(1)) if m else None

def p_from_E(E, m):
    x = E*E - m*m
    return math.sqrt(x) if x > 0 else 0.0

def pt_from_p_eta(p, eta):
    return p / math.cosh(eta)

# ------------------------------ IO discovery ------------------------------

def iter_reco_files(root: Path):
    # Walk tree and yield .root files under eta±X.XX folders
    for d in root.rglob("*"):
        if not d.is_dir():
            continue
        if not ETA_DIR_RE.match(d.name):
            continue
        for f in sorted(d.glob("*.root")):
            yield f

# ------------------------------ ROOT readers ------------------------------

def _has(tree, name: str) -> bool:
    try:
        return name in tree.keys()
    except Exception:
        return False

def _first_existing(tree, names):
    for n in names:
        if _has(tree, n):
            return n
    return None

def _vector_len_field(tree, coll_prefix):
    """
    Try to find a per-event length field for the collection, e.g.
      'GenFitTracks#0' or 'GenFitTracks_offset'
    Returns array of per-event lengths or None.
    """
    # Common PODIO schemas
    candidates = [f"{coll_prefix}#0", f"{coll_prefix}_offsets", f"{coll_prefix}_offset"]
    for c in candidates:
        if _has(tree, c):
            try:
                arr = tree[c].array(library="ak")
                # For "#0", it's usually an index; convert to counts via diff of offsets if present
                if c.endswith("#0") and isinstance(arr, ak.Array):
                    # Sometimes a scalar (total entries); skip
                    continue
                return arr
            except Exception:
                pass
    return None

def _get_event_track_indices(tree, coll_prefix):
    """
    Build per-event track slicing indices using PODIO 'offset' branches if present,
    else best-effort fallback: read 'GenFitTracks' id branch.
    """
    # PODIO often provides offsets for the relation tables (states), but for top-level
    # collection we can try the "n" counter if present.
    # Robust fallback: use the 'index' branch of e.g. GenFitTracks.ID or so.
    # We'll instead infer event grouping from the generic 'events' TTree entry grouping.
    n_events = tree.num_entries
    # Without explicit offsets, we’ll assume one event per entry in the 'events' TTree.
    # Track arrays will be jagged (length per event) with uproot/awkward selections.
    return n_events

def _best_track_index_per_event(track_nhits, track_converged, track_fitted):
    """
    Select best track per event by:
      - max nhits (if available)
      - else any fitted&converged
      - else first index
    Inputs are awkward lists per event (could be None).
    Returns an array of indices (one per event, -1 if no track).
    """
    n_ev = len(track_fitted) if track_fitted is not None else len(track_nhits)
    idxs = []
    for i in range(n_ev):
        nh = track_nhits[i] if track_nhits is not None else None
        cv = track_converged[i] if track_converged is not None else None
        ft = track_fitted[i] if track_fitted is not None else None
        ntrk = len(nh) if nh is not None else (len(cv) if cv is not None else (len(ft) if ft is not None else 0))
        if ntrk == 0:
            idxs.append(-1)
            continue
        choice = 0
        if nh is not None and len(nh)>0:
            choice = int(ak.argmax(nh[i]))
        elif cv is not None and ft is not None:
            ok = ak.where((cv[i]==1) & (ft[i]==1))[0]
            choice = int(ok[0]) if len(ok)>0 else 0
        idxs.append(choice)
    return np.array(idxs, dtype=int)

def _pt_from_momentum(px, py):
    return np.sqrt(px*px + py*py)

def _pt_from_qOverP_tanLambda(qOverP, tanLambda):
    # p = 1/|qOverP| ; cosθ = 1/sqrt(1+tan^2λ) ; pT = p * cosθ
    p = 1.0 / np.abs(qOverP)
    cos_theta = 1.0 / np.sqrt(1.0 + tanLambda*tanLambda)
    return p * cos_theta

def extract_reco_pt(root_file: Path, tracks_prefix="GenFitTracks", states_prefix="GenFitTracksStates"):
    """
    Return (pt_reco [per event best track], nhits [per event], converged/fitted if available)
    """
    with uproot.open(root_file) as f:
        # find 'events' tree
        t = None
        for k in f.keys():
            if k.rstrip(";1").endswith("events"):
                t = f[k]
                break
        if t is None:
            raise RuntimeError(f"No 'events' tree in {root_file}")

        # candidate branches
        px_b = _first_existing(t, [f"{states_prefix}.momentum.x", f"{tracks_prefix}.momentum.x"])
        py_b = _first_existing(t, [f"{states_prefix}.momentum.y", f"{tracks_prefix}.momentum.y"])
        pz_b = _first_existing(t, [f"{states_prefix}.momentum.z", f"{tracks_prefix}.momentum.z"])

        qop_b   = _first_existing(t, [f"{states_prefix}.qOverP", f"{tracks_prefix}.qOverP"])
        tanl_b  = _first_existing(t, [f"{states_prefix}.tanLambda", f"{tracks_prefix}.tanLambda"])

        # quality-ish helpers
        nh_b    = _first_existing(t, [f"{tracks_prefix}.nHits", f"{tracks_prefix}.nhits"])
        conv_b  = _first_existing(t, [f"{tracks_prefix}.converged", f"{tracks_prefix}.isConverged"])
        fit_b   = _first_existing(t, [f"{tracks_prefix}.fitted", f"{tracks_prefix}.isFitted"])

        # Load jagged arrays
        def arr(name):
            return t[name].arrays(library="ak")[name] if name else None

        px = arr(px_b); py = arr(py_b)
        qop = arr(qop_b); tanl = arr(tanl_b)
        nh  = arr(nh_b)
        cv  = arr(conv_b)
        ft  = arr(fit_b)

        # If both states and tracks exist, prefer STATES (fitter output per state)
        # Some files have one state per track; we can just take the first state for selection.
        # Standardize to per-track jagged:
        def first_if_jag(a):
            if a is None: return None
            # if a is list[list[vals]], take first along inner axis if 2-level deep
            if ak.num(a, axis=2, with_name=None, highlevel=False) is not None:
                return a[:,0]
            return a

        px = first_if_jag(px); py = first_if_jag(py)
        qop = first_if_jag(qop); tanl = first_if_jag(tanl)

        # selection: best track per event
        idx_best = _best_track_index_per_event(nh, cv, ft)

        # Build chosen pT per event
        n_events = len(idx_best)
        pt = np.full(n_events, np.nan, dtype=float)

        for i in range(n_events):
            k = idx_best[i]
            if k < 0: continue
            if px is not None and py is not None and len(px[i])>k and len(py[i])>k:
                pt[i] = _pt_from_momentum(np.array(px[i][k]), np.array(py[i][k]))
            elif qop is not None and tanl is not None and len(qop[i])>k and len(tanl[i])>k:
                pt[i] = _pt_from_qOverP_tanLambda(np.array(qop[i][k]), np.array(tanl[i][k]))
            else:
                # no usable components
                continue

        return pt

# ------------------------------ aggregation & plotting ------------------------------

TARGET_ETAS = [0.0, 0.5, 1.0, 1.5, 2.0]
ETA_TOL = 0.06  # accept folders within ±0.06 of target (so +0.05 still matches bin)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reco-root", required=True, help="Root folder containing reco outputs grouped by eta±X.XX")
    ap.add_argument("--pdg", type=int, default=13, help="PDG for true-mass pT calc (default muon)")
    ap.add_argument("--out-png", default="pt_resolution_vs_pt.png")
    ap.add_argument("--out-csv", default="", help="Optional CSV to save (pt_bin_center, res, n) for each eta")
    ap.add_argument("--nbins", type=int, default=10, help="pT bins per-eta (log spaced)")
    ap.add_argument("--pt-min", type=float, default=0.05, help="min pT [GeV]")
    ap.add_argument("--pt-max", type=float, default=50.0, help="max pT [GeV]")
    ap.add_argument("--tracks-prefix", default="GenFitTracks", help="collection prefix for tracks")
    ap.add_argument("--states-prefix", default="GenFitTracksStates", help="collection prefix for track states")
    args = ap.parse_args()

    root = Path(args.reco_root).resolve()
    if not root.is_dir():
        raise SystemExit(f"[FATAL] reco-root not found: {root}")

    mass = PDG_MASS_GEV.get(args.pdg, 0.0)
    # gather by |eta| bucket
    buckets = {e: {"pt_true": [], "pt_reco": []} for e in TARGET_ETAS}

    files = list(iter_reco_files(root))
    if not files:
        raise SystemExit(f"[FATAL] no .root files found under {root}/eta±X.XX")

    for rf in files:
        eta = parse_eta_from_path(rf)
        if eta is None:
            continue
        abs_eta = abs(eta)
        # assign to nearest target eta if within tolerance
        eta_key = None
        for target in TARGET_ETAS:
            if abs(abs_eta - target) <= ETA_TOL:
                eta_key = target
                break
        if eta_key is None:
            continue

        E = parse_energy_from_fname(rf.name)
        if E is None:
            # can't form true pT; skip file
            continue

        p  = p_from_E(E, mass)
        pt_true = pt_from_p_eta(p, eta)

        try:
            pt_reco = extract_reco_pt(rf, tracks_prefix=args.tracks_prefix, states_prefix=args.states_prefix)
        except Exception as e:
            print(f"[warn] failed reading {rf}: {e}")
            continue

        # One pT_true per *event* in this file; replicate to match number of events
        n_ev = len(pt_reco)
        buckets[eta_key]["pt_true"].append(np.full(n_ev, pt_true))
        buckets[eta_key]["pt_reco"].append(pt_reco)

    # stack arrays
    for k in buckets:
        if buckets[k]["pt_true"]:
            buckets[k]["pt_true"] = np.concatenate(buckets[k]["pt_true"])
            buckets[k]["pt_reco"] = np.concatenate(buckets[k]["pt_reco"])
        else:
            buckets[k]["pt_true"] = np.array([], dtype=float)
            buckets[k]["pt_reco"] = np.array([], dtype=float)

    # compute resolution vs pT (relative RMS of (pTreco - pTtrue)/pTtrue)
    pt_edges = np.logspace(math.log10(args.pt_min), math.log10(args.pt_max), args.nbins+1)
    pt_centers = np.sqrt(pt_edges[:-1]*pt_edges[1:])

    curves = {}  # eta -> (centers, res, n)
    for eta_key in TARGET_ETAS:
        ttrue = buckets[eta_key]["pt_true"]
        treco = buckets[eta_key]["pt_reco"]
        # filter finite
        mask = np.isfinite(ttrue) & np.isfinite(treco) & (ttrue>0)
        ttrue = ttrue[mask]; treco = treco[mask]
        if ttrue.size == 0:
            curves[eta_key] = (pt_centers, np.full_like(pt_centers, np.nan), np.zeros_like(pt_centers, int))
            continue
        rel = (treco - ttrue)/ttrue
        # bin by true pT
        inds = np.digitize(ttrue, pt_edges) - 1
        res = np.full(len(pt_centers), np.nan)
        counts = np.zeros(len(pt_centers), dtype=int)
        for i in range(len(pt_centers)):
            sel = (inds == i)
            if not np.any(sel): continue
            x = rel[sel]
            # robust RMS (std of residuals)
            res[i] = np.sqrt(np.mean(x*x))
            counts[i] = int(sel.sum())
        curves[eta_key] = (pt_centers, res, counts)

    # plot
    fig = plt.figure(figsize=(7.5, 5.0))
    for eta_key in TARGET_ETAS:
        x, y, n = curves[eta_key]
        # plot only bins with counts
        ok = np.isfinite(y)
        if np.any(ok):
            plt.plot(x[ok], y[ok], marker="o", label=f"|η|≈{eta_key:g}")

    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel(r"$p_T^{\mathrm{true}}$ [GeV]")
    plt.ylabel(r"Resolution  $\sqrt{\langle((p_T^{\mathrm{reco}}-p_T^{\mathrm{true}})/p_T^{\mathrm{true}})^2\rangle}$")
    plt.title("pT resolution vs pT (GenFit, GGTF)")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=180)
    print(f"[ok] wrote {args.out_png}")

    if args.out_csv:
        import csv
        with open(args.out_csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["eta_bin","pt_center_GeV","resolution","count"])
            for eta_key in TARGET_ETAS:
                x, y, n = curves[eta_key]
                for xi, yi, ni in zip(x, y, n):
                    if np.isfinite(yi):
                        w.writerow([eta_key, f"{xi:.6g}", f"{yi:.6g}", int(ni)])
        print(f"[ok] wrote {args.out_csv}")

if __name__ == "__main__":
    main()
