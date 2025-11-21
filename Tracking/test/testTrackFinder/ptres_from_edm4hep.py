#!/usr/bin/env python3
# ptres_vs_pt.py
#
# Compute and plot pT resolution vs truth pT using Δ(q/pT) from TrackState.omega.
# Each input reco file is expected to be a single-pT gun sample; the truth pT is
# derived from the filename/path via either:
#   • "...eta_+X.XX..." AND "...EYY.Y..."  → pT_truth = sqrt(E^2 - m^2)/cosh(eta)
#   • OR "...ptYY.Y..."                    → pT_truth = given value
#
# Output: a PNG scatter plot of σ(pT)/pT vs pT_truth (one point per input file).
#
# Requires: podio (Reader), edm4hep, numpy, matplotlib.
#
# Example:
#   python3 ptres_vs_pt.py \
#     /eos/.../reco_eta+0.00_pt1.0.root \
#     /eos/.../reco_eta+0.00_pt2.0.root \
#     /eos/.../reco_eta+0.00_pt5.0.root \
#     --bz 2.0 --png ptres_vs_pt.png
#
#   # or with energy+eta encoded
#   python3 ptres_vs_pt.py /eos/.../reco_eta+1.00_E50.0.root --bz 2.0

import re
import os
import math
import argparse
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")  # for batch systems
import matplotlib.pyplot as plt

from podio.root_io import Reader
import edm4hep

K = 0.299792458  # GeV/(c·T·m)

# ------------- parsing helpers -------------
def parse_eta_energy_or_pt_from_path(path):
    """
    Returns (eta, E_GeV or None, pt_GeV or None) parsed from the path.
    Accepts 'eta_+1.00' or 'eta+1.00' or 'eta=-0.75';
    Accepts 'E50.0' or 'pt22.143'.
    """
    s = path
    m_eta = re.search(r'eta[_=]?([+\-]?\d+(?:\.\d+)?)', s)
    eta = float(m_eta.group(1)) if m_eta else None

    m_E = re.search(r'(?:^|[^A-Za-z0-9])E([0-9]+(?:\.[0-9]+)?)', s)
    E = float(m_E.group(1)) if m_E else None

    m_pt = re.search(r'(?:^|[^A-Za-z0-9])pt([0-9]+(?:\.[0-9]+)?)', s, re.IGNORECASE)
    pt = float(m_pt.group(1)) if m_pt else None

    return eta, E, pt

def truth_pt_from_eta_and_energy(eta, E_GeV, mass_GeV):
    """pT = sqrt(E^2 - m^2)/cosh(eta)."""
    if eta is None or E_GeV is None:
        return None
    if E_GeV <= mass_GeV:
        return None
    p = math.sqrt(max(0.0, E_GeV*E_GeV - mass_GeV*mass_GeV))
    return p / math.cosh(eta)

# ------------- track-state helpers -------------
def signed_q_over_pT_from_state(ts, bz_t):
    if bz_t == 0.0 or ts.omega == 0.0:
        return 0.0
    # omega is 1/mm; convert to 1/m with *1000
    return (ts.omega * 1000.0) / (K * bz_t)

def robust_sigma(values):
    """Core width ~ (p84 - p16)/2 to reduce tail sensitivity."""
    if len(values) < 3:
        return float("nan")
    v = np.sort(np.asarray(values))
    try:
        p16 = np.percentile(v, 16.0, method="nearest")
        p84 = np.percentile(v, 84.0, method="nearest")
    except TypeError:
        p16 = np.percentile(v, 16.0, interpolation="nearest")
        p84 = np.percentile(v, 84.0, interpolation="nearest")
    return 0.5 * (p84 - p16)

def boot_sigma(values, n_boot=300, rng=None):
    """Bootstrap uncertainty on robust sigma (optional)."""
    if n_boot <= 0 or len(values) < 5:
        return float("nan")
    rng = np.random.default_rng() if rng is None else rng
    vals = np.asarray(values)
    sigmas = []
    n = len(vals)
    for _ in range(n_boot):
        resamp = vals[rng.integers(0, n, n)]
        sigmas.append(robust_sigma(resamp))
    return float(np.std(sigmas, ddof=1)) if len(sigmas) > 1 else float("nan")

# ------------- per-file analysis -------------
def analyze_file(input_path, tracks_name, bz_t, mass_GeV, require_atip=False):
    """
    Returns dict with:
      {
        'pt_truth': float,
        'n_tracks': int,
        'n_used': int,
        'n_atip_miss': int,
        'bias_dqopT': float,
        'sigcore_dqopT': float,
        'rel_sigma_pt': float,     # ~ σ(pT)/pT
        'residuals': list[float],  # Δ(q/pT)
        'source': str              # text on how pt_truth was derived
      }
    """
    eta, E_GeV, pt_in_name = parse_eta_energy_or_pt_from_path(input_path)
    if E_GeV is not None and eta is not None:
        pt_truth = truth_pt_from_eta_and_energy(eta, E_GeV, mass_GeV)
        source = f"E={E_GeV:g} GeV, eta={eta:g}"
    elif pt_in_name is not None:
        pt_truth = pt_in_name
        source = f"pt(name)={pt_truth:g} GeV"
    else:
        raise RuntimeError(f"Could not parse truth pT from path: {input_path}")

    rdr = Reader(input_path)
    events = rdr.get("events")

    residuals = []
    n_tracks = 0
    n_atip_miss = 0

    for evt in events:
        tracks = evt.get(tracks_name)
        for trk in tracks:
            n_tracks += 1
            # Prefer AtIP, else first state if allowed
            ts_use = None
            for ts in trk.getTrackStates():
                if ts.location == edm4hep.TrackState.AtIP:
                    ts_use = ts
                    break
            if ts_use is None and not require_atip:
                states = list(trk.getTrackStates())
                if states:
                    ts_use = states[0]

            if ts_use is None:
                n_atip_miss += 1
                continue
            if ts_use.omega == 0.0:
                continue

            q_over_pt_reco = signed_q_over_pT_from_state(ts_use, bz_t)
            # Adopt reco charge sign for truth (uniform-charge gun assumption)
            sign = 1.0 if q_over_pt_reco >= 0 else -1.0
            q_over_pt_truth = sign / pt_truth

            residuals.append(q_over_pt_reco - q_over_pt_truth)

    n_used = len(residuals)
    bias = float(np.mean(residuals)) if n_used > 0 else float("nan")
    sig = robust_sigma(residuals) if n_used > 0 else float("nan")
    rel = sig * pt_truth if np.isfinite(sig) else float("nan")

    return {
        "pt_truth": float(pt_truth),
        "n_tracks": int(n_tracks),
        "n_used": int(n_used),
        "n_atip_miss": int(n_atip_miss),
        "bias_dqopT": float(bias),
        "sigcore_dqopT": float(sig),
        "rel_sigma_pt": float(rel),
        "residuals": residuals,
        "source": source,
    }

# ------------- main -------------
def main():
    ap = argparse.ArgumentParser(description="Plot σ(pT)/pT vs pT_truth using Δ(q/pT) from reco track states.")
    ap.add_argument("inputs", nargs="+", help="One or more EDM4hep reco ROOT files (single-pT gun per file).")
    ap.add_argument("--tracks", default="GenFitTracks", help="Track collection name.")
    ap.add_argument("--bz", type=float, default=2.0, help="Magnetic field [T] used in fit.")
    ap.add_argument("--speciesMass", type=float, default=0.10566, help="Gun particle mass [GeV] (muon default).")
    ap.add_argument("--png", default="ptres_vs_pt.png", help="Output PNG filename.")
    ap.add_argument("--requireAtIP", action="store_true", default=False,
                    help="Only accept tracks that have an AtIP state.")
    ap.add_argument("--bootstrap", type=int, default=0,
                    help="If >0, bootstrap resamples for error bars on σ(pT)/pT (e.g. 300).")
    args = ap.parse_args()

    results = []
    for path in args.inputs:
        try:
            r = analyze_file(path, args.tracks, args.bz, args.speciesMass, args.requireAtIP)
            results.append((path, r))
        except Exception as e:
            print(f"[WARN] Skipping {path}: {e}")

    if not results:
        raise SystemExit("No valid inputs produced results.")

    # Aggregate points (one point per file)
    pts = []
    rels = []
    yerrs = []
    labels = []

    # Report table
    print("\n=== Per-file pT resolution ===")
    header = f"{'pT_truth [GeV]':>14} | {'Ntracks':>8} | {'Nused':>6} | {'bias <Δ(q/pT)> [1/GeV]':>24} | {'σ_core[1/GeV]':>14} | {'σ(pT)/pT':>10} | source"
    print(header)
    print("-"*len(header))

    for path, r in sorted(results, key=lambda x: x[1]["pt_truth"]):
        pt_truth = r["pt_truth"]
        ntr = r["n_tracks"]
        nuse = r["n_used"]
        bias = r["bias_dqopT"]
        sigc = r["sigcore_dqopT"]
        rel  = r["rel_sigma_pt"]
        src  = r["source"]

        pts.append(pt_truth)
        rels.append(rel)

        if args.bootstrap > 0 and r["n_used"] > 5:
            sig_err = boot_sigma(r["residuals"], n_boot=args.bootstrap)
            yerr = sig_err * pt_truth if np.isfinite(sig_err) else float("nan")
        else:
            yerr = float("nan")
        yerrs.append(yerr)

        print(f"{pt_truth:14.6g} | {ntr:8d} | {nuse:6d} | {bias:24.4e} | {sigc:14.4e} | {rel:10.4e} | {src}")

    pts  = np.asarray(pts, dtype=float)
    rels = np.asarray(rels, dtype=float)
    yerrs = np.asarray(yerrs, dtype=float)

    # ---- Plot: σ(pT)/pT vs pT_truth ----
    plt.figure(figsize=(7.5, 5.0))
    if np.any(np.isfinite(yerrs)):
        plt.errorbar(pts, rels, yerr=np.where(np.isfinite(yerrs), yerrs, 0.0),
                     fmt="o", capsize=3, label=r"$\sigma(p_T)/p_T$")
    else:
        plt.plot(pts, rels, "o", label=r"$\sigma(p_T)/p_T$")

    # Optional: join points for readability (monotonic pT grid typical for guns)
    order = np.argsort(pts)
    plt.plot(pts[order], rels[order], "-", alpha=0.5)

    plt.xlabel(r"$p_T^{\mathrm{truth}}\ \mathrm{[GeV]}$")
    plt.ylabel(r"$\sigma(p_T)/p_T$")
    plt.title(r"$\sigma(p_T)/p_T$ vs $p_T^{\mathrm{truth}}$ (from $\Delta(q/p_T)$ core width)")
    plt.grid(True, alpha=0.3)
    plt.legend(loc="best")
    plt.tight_layout()
    plt.savefig(args.png, dpi=170)
    print(f"\nSaved figure: {args.png}")

if __name__ == "__main__":
    main()
