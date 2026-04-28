#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, math, argparse
from pathlib import Path
import numpy as np

import ROOT
ROOT.gROOT.SetBatch(True)

# Matplotlib is optional; if missing we still write CSV
try:
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except Exception:
    HAVE_MPL = False

# ----------- parsing helpers -----------
ETA_DIR_RE = re.compile(r"^eta[_]?([+-]?\d+(?:\.\d+)?)$")
E_TAG_RE   = re.compile(r"(?:^|_)E([0-9]+(?:\.[0-9]+)?)")

PDG_MASS_GEV = {
    11: 0.000510999, -11: 0.000510999,
    13: 0.1056583755, -13: 0.1056583755,
    211: 0.13957039,  -211: 0.13957039,
    321: 0.493677,    -321: 0.493677,
    2212: 0.938272088, -2212: 0.938272088,
}

TARGET_ETAS = [0.0, 0.5, 1.0, 1.5, 2.0]
ETA_TOL = 0.06  # accept folders within ±0.06 of target

def parse_eta_from_path(p: Path):
    # Accept eta folder itself or parent of file
    for name in (p.parent.name, p.parent.parent.name):
        m = ETA_DIR_RE.match(name)
        if m:
            return float(m.group(1))
    return None

def parse_energy_from_fname(fname: str):
    m = E_TAG_RE.search(fname)
    return float(m.group(1)) if m else None

def p_from_E(E, m):
    x = E*E - m*m
    return math.sqrt(x) if x > 0 else 0.0

def pt_from_p_eta(p, eta):
    return p / math.cosh(eta)

def iter_reco_files(root: Path):
    for d in root.rglob("*"):
        if d.is_dir() and ETA_DIR_RE.match(d.name):
            for f in sorted(d.glob("*.root")):
                yield f

# ----------- ROOT helpers -----------

def _branch_exists(tree, name: str) -> bool:
    try:
        return bool(tree.GetBranch(name))
    except Exception:
        return False

def _best_track_index(nHits_vec, fitted_vec, converged_vec):
    """Pick best index given optional std::vector<int> (or float/bool) branches."""
    n = 0
    if nHits_vec is not None: n = nHits_vec.size()
    elif fitted_vec is not None: n = fitted_vec.size()
    elif converged_vec is not None: n = converged_vec.size()
    else: return 0  # no info, pick 0

    if n == 0: return -1
    if nHits_vec is not None and nHits_vec.size() > 0:
        # argmax nHits
        best = 0
        bestNH = nHits_vec[0]
        for i in range(1, nHits_vec.size()):
            if nHits_vec[i] > bestNH:
                bestNH = nHits_vec[i]
                best = i
        return int(best)
    # Next: any fitted&converged
    if fitted_vec is not None and converged_vec is not None and fitted_vec.size()==converged_vec.size():
        for i in range(fitted_vec.size()):
            try:
                if int(fitted_vec[i])==1 and int(converged_vec[i])==1:
                    return int(i)
            except Exception:
                pass
    # Fallback: first
    return 0

def extract_reco_pt_pyroot(root_file: Path, tracks_prefix="GenFitTracks"):
    """
    Returns np.array of pT (GeV) per event (best track). Uses track-level branches:
      - {prefix}.momentum.x / y
      - optional {prefix}.nHits, {prefix}.fitted, {prefix}.converged
    If momentum.x/y are missing, tries qOverP + tanLambda at track level.
    """
    f = ROOT.TFile.Open(str(root_file))
    if not f or f.IsZombie():
        raise RuntimeError(f"Cannot open {root_file}")
    t = f.Get("events")
    if not t:
        f.Close(); raise RuntimeError(f"No 'events' tree in {root_file}")

    # Prefer momentum.x/y on tracks
    bx = f"{tracks_prefix}.momentum.x"
    by = f"{tracks_prefix}.momentum.y"
    bq = f"{tracks_prefix}.qOverP"
    bt = f"{tracks_prefix}.tanLambda"

    have_mom = _branch_exists(t, bx) and _branch_exists(t, by)
    have_qt  = _branch_exists(t, bq) and _branch_exists(t, bt)

    if not have_mom and not have_qt:
        f.Close()
        raise RuntimeError(f"No usable track-level momentum or qOverP/tanLambda in {root_file}")

    b_nh = f"{tracks_prefix}.nHits"
    b_ft = f"{tracks_prefix}.fitted"
    b_cv = f"{tracks_prefix}.converged"

    # Set addresses (std::vector<float> etc.)
    # Use ROOT.std.vector('float') etc. PyROOT auto-handles conversion on access, but we’ll read via t.GetEntry.
    n_entries = t.GetEntries()
    pt = np.full(n_entries, np.nan, dtype=float)

    # No need to SetBranchAddress explicitly; we access via getattr after GetEntry
    for i in range(n_entries):
        t.GetEntry(i)

        # Vectors for selection
        nh_vec = getattr(t, b_nh) if _branch_exists(t, b_nh) else None
        ft_vec = getattr(t, b_ft) if _branch_exists(t, b_ft) else None
        cv_vec = getattr(t, b_cv) if _branch_exists(t, b_cv) else None

        best_idx = _best_track_index(nh_vec, ft_vec, cv_vec)
        if best_idx < 0:
            continue

        if have_mom:
            vx = getattr(t, bx)
            vy = getattr(t, by)
            if vx.size() > best_idx and vy.size() > best_idx:
                px = float(vx[best_idx])
                py = float(vy[best_idx])
                pt[i] = math.hypot(px, py)
                continue  # done

        if have_qt:
            vq = getattr(t, bq)
            vt = getattr(t, bt)
            if vq.size() > best_idx and vt.size() > best_idx:
                qOverP = float(vq[best_idx])
                tanL   = float(vt[best_idx])
                if qOverP != 0.0:
                    p = 1.0 / abs(qOverP)
                    cos_theta = 1.0 / math.sqrt(1.0 + tanL*tanL)
                    pt[i] = p * cos_theta

    f.Close()
    return pt

# ----------- aggregation + plot -----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reco-root", required=True, help="Root folder containing reco outputs grouped by eta±X.XX")
    ap.add_argument("--pdg", type=int, default=13, help="PDG for true-mass pT calc (default muon)")
    ap.add_argument("--out-png", default="pt_resolution_vs_pt.png")
    ap.add_argument("--out-csv", default="", help="Optional CSV with binned results")
    ap.add_argument("--nbins", type=int, default=12)
    ap.add_argument("--pt-min", type=float, default=0.05)
    ap.add_argument("--pt-max", type=float, default=20.0)
    ap.add_argument("--tracks-prefix", default="GenFitTracks")
    args = ap.parse_args()

    root = Path(args.reco_root).resolve()
    if not root.is_dir():
        raise SystemExit(f"[FATAL] reco-root not found: {root}")

    mass = PDG_MASS_GEV.get(args.pdg, 0.0)
    buckets = {e: {"pt_true": [], "pt_reco": []} for e in TARGET_ETAS}

    files = list(iter_reco_files(root))
    if not files:
        raise SystemExit(f"[FATAL] no .root files found under {root}/eta±X.XX")

    for rf in files:
        eta = parse_eta_from_path(rf)
        if eta is None:
            continue
        abs_eta = abs(eta)
        # map to nearest target eta
        eta_key = None
        for target in TARGET_ETAS:
            if abs(abs_eta - target) <= ETA_TOL:
                eta_key = target
                break
        if eta_key is None:
            continue

        E = parse_energy_from_fname(rf.name)
        if E is None:
            print(f"[warn] skip (no E tag): {rf}")
            continue

        p  = p_from_E(E, mass)
        pt_true_val = pt_from_p_eta(p, eta)

        try:
            pt_reco = extract_reco_pt_pyroot(rf, tracks_prefix=args.tracks_prefix)
        except Exception as e:
            print(f"[warn] failed reading {rf}: {e}")
            continue

        n_ev = len(pt_reco)
        buckets[eta_key]["pt_true"].append(np.full(n_ev, pt_true_val))
        buckets[eta_key]["pt_reco"].append(pt_reco)

    # stack
    for k in buckets:
        if buckets[k]["pt_true"]:
            buckets[k]["pt_true"] = np.concatenate(buckets[k]["pt_true"])
            buckets[k]["pt_reco"] = np.concatenate(buckets[k]["pt_reco"])
        else:
            buckets[k]["pt_true"] = np.array([], dtype=float)
            buckets[k]["pt_reco"] = np.array([], dtype=float)

    # binning
    pt_edges = np.logspace(math.log10(args.pt_min), math.log10(args.pt_max), args.nbins+1)
    pt_centers = np.sqrt(pt_edges[:-1]*pt_edges[1:])

    curves = {}
    for eta_key in TARGET_ETAS:
        ttrue = buckets[eta_key]["pt_true"]
        treco = buckets[eta_key]["pt_reco"]
        mask = np.isfinite(ttrue) & np.isfinite(treco) & (ttrue > 0)
        ttrue = ttrue[mask]; treco = treco[mask]
        if ttrue.size == 0:
            curves[eta_key] = (pt_centers, np.full_like(pt_centers, np.nan), np.zeros_like(pt_centers, int))
            continue
        rel = (treco - ttrue)/ttrue
        inds = np.digitize(ttrue, pt_edges) - 1
        res = np.full(len(pt_centers), np.nan)
        counts = np.zeros(len(pt_centers), dtype=int)
        for i in range(len(pt_centers)):
            sel = (inds == i)
            if not np.any(sel): continue
            x = rel[sel]
            res[i] = np.sqrt(np.mean(x*x))
            counts[i] = int(sel.sum())
        curves[eta_key] = (pt_centers, res, counts)

    # CSV
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

    # Plot
    if HAVE_MPL:
        plt.figure(figsize=(7.5, 5.0))
        for eta_key in TARGET_ETAS:
            x, y, n = curves[eta_key]
            ok = np.isfinite(y)
            if np.any(ok):
                plt.plot(x[ok], y[ok], marker="o", label=f"|η|≈{eta_key:g}")
        plt.xscale("log"); plt.yscale("log")
        plt.xlabel(r"$p_T^{\mathrm{true}}$ [GeV]")
        plt.ylabel(r"Resolution  RMS($\Delta p_T/p_T$)")
        plt.title("pT resolution vs pT (GenFit + GGTF)")
        plt.grid(True, which="both", alpha=0.3)
        plt.legend()
        plt.tight_layout()
        plt.savefig(args.out_png, dpi=180)
        print(f"[ok] wrote {args.out_png}")
    else:
        print("[note] matplotlib not available; skipped PNG. CSV is still written if requested.")

if __name__ == "__main__":
    main()
