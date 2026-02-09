#!/usr/bin/env python3
"""
extract_delphes_tracker_params.py

Purpose
-------
Given your reco gun grid directory layout:
  OUTDIR/eta_+0.00/reco_gun_eta+0.00_pt0.69475.root
  ...

This script:
  1) Calls your trusted scan module: scan_pt_time_by_event.scan_file(...)
  2) Computes per-(eta, pt) tracker "efficiency" and dpT/pT resolution
  3) Fits dpT/pT vs pt to the Delphes-friendly model:
        dpT/pT = sqrt(A^2 + B^2*pt + (C*pt)^2)
     using a linearized weighted least squares on (dpT/pT)^2.
  4) Prints the exact "set RES_A ...", "set RES_B ...", "set RES_C ...",
     and recommended TRACK_* values to paste into your Delphes card (Option A).
  5) Writes a JSON report + CSV table.

Important assumptions (consistent with your current workflow)
-------------------------------------------------------------
- Gun samples: one truth particle per event per file (pt taken from filename, eta from directory).
- scan_file(...) returns:
    results: list of dicts per usable event, each with at least:
      - rel_signed: (pt_reco - pt_true)/pt_true  (signed)
      - pt_used_src: e.g. "time" if using TrackState.time convention
      - curvObservable, circleOK, etc. (optional but used if present)
    n_ev: total events in file (or scanned count)
    n_scanned: scanned events (depends on your scanmod)
- "Efficiency" here is defined as: (# usable results) / (n_scanned or n_ev).
  For gun studies this is a reasonable proxy for tracking efficiency; for full physics
  events you would re-derive efficiency with truth-matching.

Usage
-----
  python3 extract_delphes_tracker_params.py \
    --inputDir /path/to/reco_grid \
    --outJson tracker_params.json \
    --outCsv  tracker_points.csv \
    --trackCollection GenFitTracks \
    --hitCollection OutputWireHitsGGTF \
    --method truncrms68 \
    --qualityCut none

You will typically run it twice (CF and W) and paste the printed values into:
  idea_card2_CF.tcl
  idea_card2_W.tcl
"""

import argparse
import os
import re
import math
import json
import csv
from collections import defaultdict

# Must be available in same dir or PYTHONPATH
import scan_pt_time_by_event as scanmod


# ---------------------------
# small numeric helpers
# ---------------------------
def finite(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)

def median(vals):
    v = [x for x in vals if finite(x)]
    if not v:
        return float("nan")
    v.sort()
    n = len(v)
    m = n // 2
    return float(v[m]) if (n % 2 == 1) else float(0.5 * (v[m - 1] + v[m]))

def percentile(vals, q):
    v = [x for x in vals if finite(x)]
    if not v:
        return float("nan")
    v.sort()
    if q <= 0:
        return float(v[0])
    if q >= 100:
        return float(v[-1])
    pos = (q / 100.0) * (len(v) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(v[lo])
    frac = pos - lo
    return float(v[lo] * (1.0 - frac) + v[hi] * frac)

def mean_std(vals):
    v = [x for x in vals if finite(x)]
    if not v:
        return (float("nan"), float("nan"))
    m = sum(v) / len(v)
    if len(v) < 2:
        return (float(m), float("nan"))
    s2 = sum((x - m) ** 2 for x in v) / (len(v) - 1)
    return (float(m), float(math.sqrt(s2)))

def mad(vals, med=None):
    v = [x for x in vals if finite(x)]
    if not v:
        return float("nan")
    if not finite(med):
        med = median(v)
    return median([abs(x - med) for x in v])

def trunc_rms(vals, central_frac=0.68, center=None):
    v = [x for x in vals if finite(x)]
    if not v:
        return float("nan")
    if not (0.0 < central_frac <= 1.0):
        return float("nan")
    if not finite(center):
        center = median(v)
    d = [abs(x - center) for x in v]
    keep_n = max(1, int(math.floor(central_frac * len(d))))
    thr = sorted(d)[keep_n - 1]
    kept = [(x - center) for x in v if abs(x - center) <= thr]
    if not kept:
        return float("nan")
    s2 = sum(x*x for x in kept)
    return float(math.sqrt(s2 / len(kept)))

def frac_binom_err(p, n):
    if not (finite(p) and n and n > 0):
        return float("nan")
    p = max(0.0, min(1.0, float(p)))
    return float(math.sqrt(p * (1.0 - p) / float(n)))

def sigma_err_from_std(std, n):
    if not (finite(std) and n and n > 1):
        return float("nan")
    return float(std / math.sqrt(2.0 * (n - 1)))

def sigma_err_from_mad_sigma(mad_sigma, n):
    if not (finite(mad_sigma) and n and n > 1):
        return float("nan")
    # conservative-ish
    return float(1.2533 * mad_sigma / math.sqrt(n))


def choose_quality(results, mode):
    if mode == "none":
        return results
    if mode == "curv":
        return [r for r in results if int(r.get("curvObservable", 0)) == 1]
    if mode == "curv_circle":
        return [r for r in results if int(r.get("curvObservable", 0)) == 1 and int(r.get("circleOK", 0)) == 1]
    raise ValueError("unknown qualityCut")


# ---------------------------
# file discovery / parsing
# ---------------------------
RE_PT = re.compile(r"_pt([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)")
RE_ETA_DIR = re.compile(r"^eta_([+-]?[0-9]+(?:\.[0-9]+)?)$")

def parse_pt_from_name(path_or_name):
    base = os.path.basename(path_or_name)
    m = RE_PT.search(base)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

def parse_eta_from_dir(dirname):
    m = RE_ETA_DIR.match(dirname)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

def discover_inputs(input_dir):
    out = {}
    for entry in sorted(os.listdir(input_dir)):
        full = os.path.join(input_dir, entry)
        if not os.path.isdir(full):
            continue
        if not RE_ETA_DIR.match(entry):
            continue
        files = []
        for fn in sorted(os.listdir(full)):
            if not fn.endswith(".root"):
                continue
            if "reco_" not in fn:
                continue
            pt = parse_pt_from_name(fn)
            if pt is None:
                continue
            files.append(os.path.join(full, fn))
        if files:
            out[entry] = files
    return out


# ---------------------------
# metric extraction per file
# ---------------------------
def compute_resolution_and_bias(results_all, quality_cut, method):
    """
    Returns:
      sigma (dpT/pT), sigma_err, bias_median, bias_err, n_used
    where rel_signed = (pt_reco - pt_true)/pt_true.
    """
    results = choose_quality(results_all, quality_cut)
    rel = [r.get("rel_signed", float("nan")) for r in results]
    rel = [x for x in rel if finite(x)]
    n = len(rel)
    if n == 0:
        return (float("nan"), float("nan"), float("nan"), float("nan"), 0)

    med = median(rel)
    bias = med

    # bias error (rough; good enough for “nice to have”)
    # Use MAD-based sigma / sqrt(n) as a scale.
    mad_rs = mad(rel, med=med)
    mad_sigma = 1.4826 * mad_rs if finite(mad_rs) else float("nan")
    bias_err = (mad_sigma / math.sqrt(n)) if (finite(mad_sigma) and n > 0) else float("nan")

    if method == "rms":
        _, s = mean_std(rel)
        return (float(s), float(sigma_err_from_std(s, n)), float(bias), float(bias_err), n)

    if method == "madsigma":
        sig = mad_sigma
        return (float(sig), float(sigma_err_from_mad_sigma(sig, n)), float(bias), float(bias_err), n)

    if method == "central68":
        p16 = percentile(rel, 16)
        p84 = percentile(rel, 84)
        sig = 0.5 * (p84 - p16) if (finite(p16) and finite(p84)) else float("nan")
        # crude SE: treat like std
        sig_err = float(sig / math.sqrt(2.0 * max(1, n - 1))) if (finite(sig) and n > 1) else float("nan")
        return (float(sig), float(sig_err), float(bias), float(bias_err), n)

    if method == "truncrms68":
        sig = trunc_rms(rel, central_frac=0.68, center=med)
        sig_err = float(sig / math.sqrt(2.0 * max(1, n - 1))) if (finite(sig) and n > 1) else float("nan")
        return (float(sig), float(sig_err), float(bias), float(bias_err), n)

    raise ValueError(f"Unknown method: {method}")


# ---------------------------
# fit dpT/pT vs pT to Delphes form
# ---------------------------
def fit_resolution_model(points):
    """
    Fit y(pt) = sqrt(A^2 + B^2*pt + (C*pt)^2) by linearizing y^2:
      y^2 = u + v*pt + w*pt^2
      u=A^2, v=B^2, w=C^2

    points: list of dict with keys: pt, res, res_err
    Returns dict with A,B,C and some fit diagnostics.
    """
    # Build weighted LS for y2
    X = []
    Y = []
    W = []
    used = 0

    for p in points:
        pt = p["pt"]
        y = p["res"]
        ey = p.get("res_err", float("nan"))

        if not (finite(pt) and finite(y) and y > 0):
            continue

        # propagate to y^2
        y2 = y * y
        # sigma(y2) ~ 2*y*σy; if σy missing, assign 10% relative (conservative)
        if not (finite(ey) and ey > 0):
            ey = 0.10 * y
        ey2 = abs(2.0 * y * ey)
        if not (finite(ey2) and ey2 > 0):
            continue

        X.append([1.0, pt, pt * pt])
        Y.append(y2)
        W.append(1.0 / (ey2 * ey2))
        used += 1

    if used < 3:
        return {
            "ok": False,
            "reason": f"Need >=3 valid points to fit, have {used}",
        }

    # Solve (X^T W X) beta = X^T W Y
    # beta = [u,v,w]
    # Do it explicitly with small-matrix algebra (no numpy dependency).
    # Build 3x3 normal matrix and 3-vector rhs.
    M = [[0.0]*3 for _ in range(3)]
    b = [0.0]*3

    for row, y2, wgt in zip(X, Y, W):
        for i in range(3):
            b[i] += wgt * row[i] * y2
            for j in range(3):
                M[i][j] += wgt * row[i] * row[j]

    def det3(A):
        return (
            A[0][0]*(A[1][1]*A[2][2]-A[1][2]*A[2][1])
          - A[0][1]*(A[1][0]*A[2][2]-A[1][2]*A[2][0])
          + A[0][2]*(A[1][0]*A[2][1]-A[1][1]*A[2][0])
        )

    def inv3(A):
        d = det3(A)
        if not (finite(d) and abs(d) > 0):
            return None
        inv = [[0.0]*3 for _ in range(3)]
        inv[0][0] =  (A[1][1]*A[2][2]-A[1][2]*A[2][1]) / d
        inv[0][1] = -(A[0][1]*A[2][2]-A[0][2]*A[2][1]) / d
        inv[0][2] =  (A[0][1]*A[1][2]-A[0][2]*A[1][1]) / d
        inv[1][0] = -(A[1][0]*A[2][2]-A[1][2]*A[2][0]) / d
        inv[1][1] =  (A[0][0]*A[2][2]-A[0][2]*A[2][0]) / d
        inv[1][2] = -(A[0][0]*A[1][2]-A[0][2]*A[1][0]) / d
        inv[2][0] =  (A[1][0]*A[2][1]-A[1][1]*A[2][0]) / d
        inv[2][1] = -(A[0][0]*A[2][1]-A[0][1]*A[2][0]) / d
        inv[2][2] =  (A[0][0]*A[1][1]-A[0][1]*A[1][0]) / d
        return inv

    Minv = inv3(M)
    if Minv is None:
        return {"ok": False, "reason": "Singular normal matrix in fit."}

    beta = [sum(Minv[i][j] * b[j] for j in range(3)) for i in range(3)]
    u, v, w = beta

    # Enforce non-negativity softly (Delphes wants real A,B,C)
    u_cl = max(0.0, u)
    v_cl = max(0.0, v)
    w_cl = max(0.0, w)

    A = math.sqrt(u_cl)
    B = math.sqrt(v_cl)
    C = math.sqrt(w_cl)

    # Fit quality: chi2/ndf in y2-space
    chi2 = 0.0
    for row, y2, wgt in zip(X, Y, W):
        pred = u + v*row[1] + w*row[2]
        chi2 += wgt * (y2 - pred)**2
    ndf = max(1, used - 3)

    return {
        "ok": True,
        "npoints": used,
        "u": u, "v": v, "w": w,
        "A": A, "B": B, "C": C,
        "chi2": chi2,
        "ndf": ndf,
        "chi2_ndf": chi2 / ndf if ndf > 0 else float("nan"),
    }


# ---------------------------
# efficiency helpers
# ---------------------------
def estimate_plateau_eff(points, pt_plateau_min, eta_max_abs=None):
    """
    points: list of dict with pt, eta, eff
    plateau = median eff over points with pt >= pt_plateau_min and |eta|<=eta_max_abs if provided.
    """
    vals = []
    for p in points:
        if not (finite(p["pt"]) and finite(p["eff"])):
            continue
        if p["pt"] < pt_plateau_min:
            continue
        if eta_max_abs is not None and finite(p["eta"]) and abs(p["eta"]) > eta_max_abs:
            continue
        vals.append(p["eff"])
    return median(vals) if vals else float("nan")

def estimate_turnon_ptmin(points, eff_frac_of_plateau=0.5):
    """
    For gun scans: find smallest pT where eff >= eff_frac_of_plateau * plateau.
    Returns pt_min estimate (nice default for TRACK_PT_MIN).
    """
    # group by pt (across etas)
    pts = sorted({p["pt"] for p in points if finite(p.get("pt"))})
    if not pts:
        return float("nan")
    plateau = estimate_plateau_eff(points, pt_plateau_min=max(pts)*0.7)
    if not finite(plateau) or plateau <= 0:
        return float("nan")
    thr = eff_frac_of_plateau * plateau
    for pt in pts:
        effs = [p["eff"] for p in points if finite(p["eff"]) and abs(p["pt"] - pt) < 1e-12]
        if effs and (sum(effs)/len(effs) >= thr):
            return float(pt)
    return float("nan")


# ---------------------------
# main
# ---------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputDir", required=True, help="Reco base dir containing eta_* subdirs")
    ap.add_argument("--outJson", default="tracker_params.json", help="JSON report output")
    ap.add_argument("--outCsv", default="tracker_points.csv", help="CSV table output")

    ap.add_argument("--trackCollection", default="GenFitTracks")
    ap.add_argument("--hitCollection", default="OutputWireHitsGGTF")

    ap.add_argument("--minPhiSpan", type=float, default=0.06)
    ap.add_argument("--minChordXY", type=float, default=500.0)
    ap.add_argument("--maxCircleCond", type=float, default=1e6)
    ap.add_argument("--centralFrac", type=float, default=0.95)

    ap.add_argument("--qualityCut", choices=["none", "curv", "curv_circle"], default="none")
    ap.add_argument("--method", choices=["rms", "madsigma", "central68", "truncrms68"], default="truncrms68",
                    help="Which resolution estimator becomes dpT/pT used for the Delphes fit.")

    # For Delphes card suggestions
    ap.add_argument("--ptPlateauMin", type=float, default=5.0,
                    help="pT threshold used to estimate plateau tracking efficiency")
    ap.add_argument("--effTurnonFrac", type=float, default=0.5,
                    help="Threshold fraction of plateau used to estimate TRACK_PT_MIN")
    ap.add_argument("--overrideEtaMax", type=float, default=float("nan"),
                    help="If provided, forces TRACK_ETA_MAX (otherwise inferred from dirs).")

    # Fit grouping
    ap.add_argument("--fitMode", choices=["global", "perEta"], default="global",
                    help="global: fit all eta points together. perEta: fit each eta separately too (extra outputs).")
    ap.add_argument("--minFitPt", type=float, default=0.2,
                    help="Min pT to include in resolution fit (avoid crazy turn-on region).")

    args = ap.parse_args()

    inputs = discover_inputs(args.inputDir)
    if not inputs:
        raise RuntimeError(f"No eta_* directories with reco_*.root found under {args.inputDir}")

    # Collect per-point measurements
    points = []  # list of dict: eta, pt, eff, eff_err, res, res_err, bias, bias_err, n_used, n_scanned
    eta_values = []

    for eta_dir, files in sorted(inputs.items()):
        eta = parse_eta_from_dir(eta_dir)
        if eta is None:
            continue
        eta_values.append(eta)

        files_sorted = sorted(files, key=lambda p: (parse_pt_from_name(p) if parse_pt_from_name(p) is not None else 1e99))
        print(f"[eta] {eta_dir}: {len(files_sorted)} files")

        for fpath in files_sorted:
            pt = parse_pt_from_name(fpath)
            if pt is None:
                continue

            results, n_ev, n_scanned = scanmod.scan_file(
                fpath,
                track_coll=args.trackCollection,
                expected_pt=pt,
                hit_coll=args.hitCollection,
                min_phi_span=args.minPhiSpan,
                min_chord_xy_mm=args.minChordXY,
                max_circle_cond=args.maxCircleCond,
                central_frac=args.centralFrac,
                logger=None,
            )

            # define denominator: prefer n_scanned if >0, else n_ev if >0, else fallback
            denom = n_scanned if (isinstance(n_scanned, int) and n_scanned > 0) else (n_ev if (isinstance(n_ev, int) and n_ev > 0) else 0)
            n_used_total = len(results) if results else 0

            eff = (float(n_used_total) / float(denom)) if denom > 0 else float("nan")
            eff_err = frac_binom_err(eff, denom) if denom > 0 else float("nan")

            res, res_err, bias, bias_err, n_used = compute_resolution_and_bias(results, args.qualityCut, args.method)

            pt_used_src = None
            if results and isinstance(results, list):
                # fraction timeSrc available later if needed
                pt_used_src = results[0].get("pt_used_src", None)

            points.append({
                "eta_dir": eta_dir,
                "eta": float(eta),
                "pt": float(pt),
                "denom": int(denom),
                "n_used_total": int(n_used_total),
                "eff": float(eff),
                "eff_err": float(eff_err) if finite(eff_err) else float("nan"),

                "res_method": args.method,
                "res": float(res),
                "res_err": float(res_err) if finite(res_err) else float("nan"),

                "bias_med": float(bias),
                "bias_err": float(bias_err) if finite(bias_err) else float("nan"),

                "n_used_for_res": int(n_used),
                "pt_used_src_example": pt_used_src,
            })

    if not points:
        raise RuntimeError("No usable points computed. Check scanmod outputs and file discovery.")

    # Infer TRACK_ETA_MAX
    if finite(args.overrideEtaMax):
        track_eta_max = float(args.overrideEtaMax)
    else:
        track_eta_max = float(max(abs(e) for e in eta_values)) if eta_values else 2.56

    # Estimate plateau efficiency and pt turn-on
    eff_plateau = estimate_plateau_eff(points, pt_plateau_min=args.ptPlateauMin, eta_max_abs=track_eta_max)
    pt_min_est = estimate_turnon_ptmin(points, eff_frac_of_plateau=args.effTurnonFrac)

    # Build fit point set
    fit_points = [p for p in points if finite(p["res"]) and p["res"] > 0 and p["pt"] >= args.minFitPt and abs(p["eta"]) <= track_eta_max]
    fit_result = fit_resolution_model(fit_points)

    # Optional per-eta fits
    per_eta_fits = {}
    if args.fitMode == "perEta":
        by_eta = defaultdict(list)
        for p in fit_points:
            by_eta[p["eta_dir"]].append(p)
        for ed, pts in sorted(by_eta.items()):
            per_eta_fits[ed] = fit_resolution_model(pts)

    # Prepare report
    report = {
        "inputDir": args.inputDir,
        "trackCollection": args.trackCollection,
        "hitCollection": args.hitCollection,
        "qualityCut": args.qualityCut,
        "method": args.method,
        "track_eta_max_inferred": track_eta_max,
        "eff_plateau_estimate": eff_plateau,
        "pt_min_turnon_estimate": pt_min_est,
        "fit": fit_result,
        "fit_mode": args.fitMode,
        "per_eta_fits": per_eta_fits,
        "n_points_total": len(points),
        "n_points_fit": len(fit_points),
    }

    # Write JSON
    with open(args.outJson, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    # Write CSV table
    with open(args.outCsv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(points[0].keys()))
        w.writeheader()
        for p in sorted(points, key=lambda d: (d["eta"], d["pt"])):
            w.writerow(p)

    # Print Delphes card snippet
    print("\n" + "="*72)
    print("Delphes IDEA Option-A tracker parameters (paste into your .tcl card)")
    print("="*72)

    print(f"set TRACK_ETA_MAX {track_eta_max:.6g}")

    if finite(pt_min_est):
        print(f"set TRACK_PT_MIN  {pt_min_est:.6g}   ;# estimated from efficiency turn-on")
    else:
        print("set TRACK_PT_MIN  0.10     ;# fallback; could not estimate from data")

    if finite(eff_plateau):
        print(f"set TRACK_EFF_PLATEAU {eff_plateau:.6g} ;# median eff for pT>={args.ptPlateauMin:g} GeV")
    else:
        print("set TRACK_EFF_PLATEAU 1.00   ;# fallback; could not estimate")

    if fit_result.get("ok", False):
        A = fit_result["A"]
        B = fit_result["B"]
        C = fit_result["C"]
        print(f"\n# dpT/pT = sqrt( A^2 + B^2*pt + (C*pt)^2 )")
        print(f"set RES_A {A:.6g}")
        print(f"set RES_B {B:.6g}")
        print(f"set RES_C {C:.6g}")
        print(f"# Fit quality: npoints={fit_result['npoints']}  chi2/ndf={fit_result['chi2_ndf']:.3g}")
    else:
        print("\n# Fit failed:")
        print(f"# {fit_result.get('reason','unknown')}")
        print("# set RES_A 1.0e-4")
        print("# set RES_B 2.0e-4")
        print("# set RES_C 2.0e-5")

    # Nice-to-have future diagnostics (printed summary)
    # Bias at high pT and overall tail proxy
    hi_pts = [p for p in points if p["pt"] >= args.ptPlateauMin and abs(p["eta"]) <= track_eta_max and finite(p["bias_med"])]
    if hi_pts:
        bias_hi = median([p["bias_med"] for p in hi_pts])
        print("\n# Nice-to-have (future): median bias (pt_reco-pt_true)/pt_true at high pT")
        print(f"# median_bias_highPt ≈ {bias_hi:+.3g}")

    # Fraction using time-source (if present)
    time_src = [p for p in points if p.get("pt_used_src_example") is not None]
    if time_src:
        frac_time = sum(1 for p in time_src if p.get("pt_used_src_example") == "time") / float(len(time_src))
        print(f"# Nice-to-have (future): frac(pt source == time) among sampled points ≈ {frac_time:.3f}")

    if args.fitMode == "perEta" and per_eta_fits:
        print("\n# Per-eta fits (optional):")
        for ed, fr in sorted(per_eta_fits.items()):
            if fr.get("ok", False):
                print(f"#  {ed}: A={fr['A']:.3g}  B={fr['B']:.3g}  C={fr['C']:.3g}  (chi2/ndf={fr['chi2_ndf']:.2g})")
            else:
                print(f"#  {ed}: fit failed ({fr.get('reason','unknown')})")

    print("\nWrote:")
    print(f"  JSON: {args.outJson}")
    print(f"  CSV:  {args.outCsv}")
    print("="*72 + "\n")


if __name__ == "__main__":
    main()
