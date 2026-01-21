#!/usr/bin/env python3
"""
analyze_pt_resolution_grid.py

Batch analysis of reco gun samples organized as:
  OUTDIR/eta_+0.00/reco_gun_eta+0.00_pt0.69475.root
  ...

Writes an output ROOT file with:
  - byEta/<eta_dir> :
      * TGraphErrors per method vs pT (WITH Y-errors for all methods)
      * one TMultiGraph overlay + legend
      * a log-log TCanvas overlay (markers only, no connecting lines)
      * an additional "relative error" graph per method (err/value) to spot unusable estimators
  - diagnostics/<eta_dir> :
      * diagnostic graphs vs pT (WITH errors where meaningful)
      * a log-x TCanvas overlay of key diagnostics (markers only)
  - byMethod/<method> :
      * overlay multigraph of all etas + legend
      * per-eta clones (styled)
      * a log-log TCanvas overlay (markers only)
  - summary TTree with all values (includes *_err for all methods and diag errs)

IMPORTANT PyROOT stability rules used here:
  - Always directory.cd() before calling Write()
  - ROOT.SetOwnership(obj, False) to prevent Python GC deleting objects held by TMultiGraph/TLegend/TCanvas
"""

import argparse
import os
import re
import math
import array
import ROOT
import ctypes
ROOT.gROOT.SetBatch(True)

# Make error bars reliably visible in batch output.
# (Does NOT change the stored errors, only display style on canvases.)
ROOT.gStyle.SetEndErrorSize(3)
ROOT.gStyle.SetErrorX(0.0)

# Import your trusted scanner (must be in same dir / PYTHONPATH)
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
    if n % 2 == 1:
        return float(v[m])
    return 0.5 * (v[m-1] + v[m])

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
        return (m, float("nan"))
    s2 = sum((x - m) ** 2 for x in v) / (len(v) - 1)
    return (m, math.sqrt(s2))

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
    return math.sqrt(s2 / len(kept))

def sigma_err_from_std(std, n):
    """Standard error of sample standard deviation (normal approx)."""
    if not (finite(std) and n and n > 1):
        return float("nan")
    return std / math.sqrt(2.0 * (n - 1))

def sigma_err_from_mad_sigma(mad_sigma, n):
    """
    Rough SE for MAD-based sigma estimator.
    For a normal distribution, asymptotic var(MAD) known, but for robustness we use ~1.253*sigma/sqrt(n).
    Conservative and order-of-magnitude useful for error bars.
    """
    if not (finite(mad_sigma) and n and n > 1):
        return float("nan")
    return 1.2533 * mad_sigma / math.sqrt(n)

def frac_binom_err(p, n):
    """Binomial SE for a fraction p over n trials."""
    if not (finite(p) and n and n > 0):
        return float("nan")
    p = max(0.0, min(1.0, float(p)))
    return math.sqrt(p * (1.0 - p) / float(n))

def median_err_bootstrap(vals, nboot=200, seed=12345):
    """Bootstrap SE for the median (lightweight)."""
    v = [x for x in vals if finite(x)]
    n = len(v)
    if n < 2:
        return float("nan")
    import random
    rnd = random.Random(seed)
    meds = []
    for _ in range(int(nboot)):
        sample = [v[rnd.randrange(n)] for _ in range(n)]
        meds.append(median(sample))
    _, s = mean_std(meds)
    return float(s) if finite(s) else float("nan")


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
# ROOT writing helpers
# ---------------------------
def make_graph(name, title, ytitle):
    g = ROOT.TGraphErrors()
    g.SetName(name)
    g.SetTitle(title)
    g.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
    g.GetYaxis().SetTitle(ytitle)
    ROOT.SetOwnership(g, False)
    return g

def add_point(g, x, y, ex=0.0, ey=0.0):
    i = g.GetN()
    g.SetPoint(i, float(x), float(y))
    g.SetPointError(i, float(ex), float(ey))

def style_graph(g, color, mstyle):
    g.SetMarkerColor(color)
    g.SetMarkerStyle(mstyle)
    g.SetMarkerSize(0.9)

    # Error bars use line attributes → DO NOT set width to 0
    g.SetLineColor(color)
    g.SetLineWidth(1)
    g.SetLineStyle(1)


def make_multigraph(name, title):
    mg = ROOT.TMultiGraph()
    mg.SetName(name)
    mg.SetTitle(title)
    ROOT.SetOwnership(mg, False)
    return mg

def make_legend(name):
    leg = ROOT.TLegend(0.12, 0.70, 0.55, 0.88)
    leg.SetName(name)
    leg.SetBorderSize(0)
    leg.SetFillStyle(0)
    ROOT.SetOwnership(leg, False)
    return leg

def make_canvas(name, title, w=900, h=700):
    c = ROOT.TCanvas(name, title, w, h)
    ROOT.SetOwnership(c, False)
    c.SetTicks(1, 1)
    c.SetGrid(1, 1)
    return c

def ensure_dir(rootdir, path_parts):
    d = rootdir
    for p in path_parts:
        nd = d.GetDirectory(p)
        if not nd:
            nd = d.mkdir(p)
        d = nd
    return d

def write_obj(dir_obj, obj, name_override=None):
    dir_obj.cd()
    if name_override:
        obj.Write(name_override)
    else:
        obj.Write()

def graph_minmax_positive(g):
    n = g.GetN()
    minp = float("inf")
    maxv = -float("inf")
    x = ctypes.c_double(0.0)
    y = ctypes.c_double(0.0)
    for i in range(n):
        g.GetPoint(i, x, y)
        yy = float(y.value)
        if finite(yy):
            if yy > 0.0:
                minp = min(minp, yy)
            maxv = max(maxv, yy)
    if not math.isfinite(minp):
        minp = float("nan")
    if not math.isfinite(maxv):
        maxv = float("nan")
    return minp, maxv

def multigraph_minmax_positive(graphs):
    minp = float("inf")
    maxv = -float("inf")
    for g in graphs:
        a, b = graph_minmax_positive(g)
        if finite(a):
            minp = min(minp, a)
        if finite(b):
            maxv = max(maxv, b)
    if not math.isfinite(minp):
        minp = float("nan")
    if not math.isfinite(maxv):
        maxv = float("nan")
    return minp, maxv


# ---------------------------
# metrics per (eta, pt)
# ---------------------------
METHODS = [
    ("rms",        "RMS(std) of signed rel error",            "rel_signed"),
    ("madsigma",   "1.4826×MAD of signed rel error",          "rel_signed"),
    ("central68",  "Central 68% half-width (p84-p16)/2",      "rel_signed"),
    ("truncrms68", "TruncRMS of central 68% around median",   "rel_signed"),
    ("meanAbs",    "Mean(|rel error|)",                       "rel_abs"),
    ("medianAbs",  "Median(|rel error|)",                     "rel_abs"),
]

DIAG_FIELDS = [
    ("frac_curvObs",    "Fraction curvObservable==1", "binom"),
    ("frac_circleOK",   "Fraction circleOK==1",       "binom"),
    ("frac_timeSrc",    "Fraction pt_used_src==time", "binom"),
    ("med_phiSpan",     "Median phiSpan [rad]",       "median_boot"),
    ("med_chord",       "Median chordXY_mm [mm]",     "median_boot"),
    ("med_cond",        "Median circleCond",          "median_boot"),
    ("med_nhits",       "Median n_hits_primary",      "median_boot"),
    ("med_rmsAlgRes",   "Median rmsAlgRes",           "median_boot"),
    ("n_usable",        "Usable events (post scan_file)", "count"),
    ("n_quality",       "Events used after qualityCut",   "count"),
]

def compute_metrics_and_diags(results_all, expected_pt, quality_cut,
                              diag_bootstrap=200, diag_bootstrap_seed=12345,
                              err_bootstrap=300, err_bootstrap_seed=54321,
                              err_bootstrap_cap=5000):
    """
    Returns:
      metrics: dict method -> (value, err, n_used)
      diags: dict diagnostic -> value
      diag_errs: dict diagnostic -> err

    Notes:
      - Diagnostics medians get bootstrap SEs.
      - central68 and truncrms68 now use bootstrap SEs (plumbed from CLI).
      - Other method errors use fast analytic approximations.
    """
    def _finite_list(vals):
        return [x for x in vals if finite(x)]

    def _cap_sample(v, cap, seed):
        v = _finite_list(v)
        n = len(v)
        if cap and cap > 0 and n > cap:
            import random
            rnd = random.Random(seed)
            return [v[rnd.randrange(n)] for _ in range(cap)]
        return v

    def _bootstrap_se(v, stat_fn, nboot, seed):
        v = _finite_list(v)
        n = len(v)
        if n < 2 or not nboot or nboot < 2:
            return float("nan")
        import random
        rnd = random.Random(seed)
        stats = []
        for _ in range(int(nboot)):
            sample = [v[rnd.randrange(n)] for _ in range(n)]
            stats.append(stat_fn(sample))
        _, s = mean_std(stats)
        return float(s) if finite(s) else float("nan")

    def _stat_central68(sample):
        p16 = percentile(sample, 16)
        p84 = percentile(sample, 84)
        return 0.5 * (p84 - p16) if (finite(p16) and finite(p84)) else float("nan")

    def _stat_truncrms68(sample):
        m = median(sample)
        return trunc_rms(sample, central_frac=0.68, center=m)

    n_usable = len(results_all)
    if n_usable == 0:
        metrics = {}
        diags = {"n_usable": 0, "n_quality": 0}
        diag_errs = {}
        return metrics, diags, diag_errs

    frac_curv = sum(int(r.get("curvObservable", 0)) == 1 for r in results_all) / n_usable
    frac_cok  = sum(int(r.get("circleOK", 0)) == 1 for r in results_all) / n_usable
    frac_time = sum((r.get("pt_used_src", "") == "time") for r in results_all) / n_usable

    phi = [r.get("phiSpan", float("nan")) for r in results_all]
    ch  = [r.get("chordXY_mm", float("nan")) for r in results_all]
    cd  = [r.get("circleCond", float("nan")) for r in results_all]
    nh  = [r.get("n_hits_primary", float("nan")) for r in results_all]
    rr  = [r.get("rmsAlgRes", float("nan")) for r in results_all]

    diags = {
        "n_usable": int(n_usable),
        "frac_curvObs": float(frac_curv),
        "frac_circleOK": float(frac_cok),
        "frac_timeSrc": float(frac_time),
        "med_phiSpan": float(median(phi)),
        "med_chord": float(median(ch)),
        "med_cond": float(median(cd)),
        "med_nhits": float(median(nh)),
        "med_rmsAlgRes": float(median(rr)),
    }

    diag_errs = {}
    diag_errs["n_usable"] = 0.0
    diag_errs["n_quality"] = 0.0
    diag_errs["frac_curvObs"] = float(frac_binom_err(frac_curv, n_usable))
    diag_errs["frac_circleOK"] = float(frac_binom_err(frac_cok, n_usable))
    diag_errs["frac_timeSrc"] = float(frac_binom_err(frac_time, n_usable))

    diag_errs["med_phiSpan"]   = float(median_err_bootstrap(phi, nboot=diag_bootstrap, seed=diag_bootstrap_seed + 1))
    diag_errs["med_chord"]     = float(median_err_bootstrap(ch,  nboot=diag_bootstrap, seed=diag_bootstrap_seed + 2))
    diag_errs["med_cond"]      = float(median_err_bootstrap(cd,  nboot=diag_bootstrap, seed=diag_bootstrap_seed + 3))
    diag_errs["med_nhits"]     = float(median_err_bootstrap(nh,  nboot=diag_bootstrap, seed=diag_bootstrap_seed + 4))
    diag_errs["med_rmsAlgRes"] = float(median_err_bootstrap(rr,  nboot=diag_bootstrap, seed=diag_bootstrap_seed + 5))

    results = choose_quality(results_all, quality_cut)
    n_q = len(results)
    diags["n_quality"] = int(n_q)
    diag_errs["n_quality"] = 0.0

    if n_q == 0:
        return {}, diags, diag_errs

    rel_signed = [r.get("rel_signed", float("nan")) for r in results]
    rel_signed = [x for x in rel_signed if finite(x)]
    if not rel_signed:
        return {}, diags, diag_errs

    rel_abs = [abs(x) for x in rel_signed if finite(x)]

    med_rs = median(rel_signed)
    _, s_rs = mean_std(rel_signed)
    mad_rs = mad(rel_signed, med=med_rs)
    mad_sigma = 1.4826 * mad_rs if finite(mad_rs) else float("nan")

    p16 = percentile(rel_signed, 16)
    p84 = percentile(rel_signed, 84)
    central68 = 0.5 * (p84 - p16) if (finite(p16) and finite(p84)) else float("nan")
    trr68 = trunc_rms(rel_signed, central_frac=0.68, center=med_rs)

    mean_abs, std_abs = mean_std(rel_abs)
    med_abs = median(rel_abs)
    mean_abs_err = (std_abs / math.sqrt(n_q)) if (finite(std_abs) and n_q > 1) else float("nan")

    rel_signed_cap = _cap_sample(rel_signed, err_bootstrap_cap, seed=err_bootstrap_seed + 7)

    central68_err = _bootstrap_se(
        rel_signed_cap, _stat_central68,
        nboot=err_bootstrap, seed=err_bootstrap_seed + 100
    )
    trr68_err = _bootstrap_se(
        rel_signed_cap, _stat_truncrms68,
        nboot=err_bootstrap, seed=err_bootstrap_seed + 200
    )

    metrics = {}
    metrics["rms"] = (float(s_rs), float(sigma_err_from_std(s_rs, n_q)), n_q)
    metrics["madsigma"] = (float(mad_sigma), float(sigma_err_from_mad_sigma(mad_sigma, n_q)), n_q)
    metrics["central68"] = (float(central68), float(central68_err), n_q)
    metrics["truncrms68"] = (float(trr68), float(trr68_err), n_q)
    metrics["meanAbs"] = (float(mean_abs), float(mean_abs_err), n_q)

    med_abs_err = float(median_err_bootstrap(rel_abs, nboot=diag_bootstrap, seed=diag_bootstrap_seed + 10))
    metrics["medianAbs"] = (float(med_abs), float(med_abs_err), n_q)

    return metrics, diags, diag_errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputDir", required=True, help="Reco base dir containing eta_* subdirs")
    ap.add_argument("--outRoot", required=True, help="Output ROOT file")
    ap.add_argument("--trackCollection", default="GenFitTracks")
    ap.add_argument("--hitCollection", default="OutputWireHitsGGTF")

    ap.add_argument("--minPhiSpan", type=float, default=0.06)
    ap.add_argument("--minChordXY", type=float, default=500.0)
    ap.add_argument("--maxCircleCond", type=float, default=1e6)
    ap.add_argument("--centralFrac", type=float, default=0.95)

    ap.add_argument("--qualityCut", choices=["none", "curv", "curv_circle"], default="none")
    ap.add_argument("--maxFilesPerEta", type=int, default=0, help="0=all; otherwise cap files per eta (debug)")

    # Bootstrap controls for diagnostics (median-type)
    ap.add_argument("--diagBootstrap", type=int, default=200, help="Bootstrap samples for median-type error bars")
    ap.add_argument("--diagBootstrapSeed", type=int, default=12345, help="Seed base for diagnostic bootstrap RNG")

    # Bootstrap controls for method error bars (central68/truncrms68)
    ap.add_argument("--methodBootstrap", type=int, default=300,
                    help="Bootstrap samples for method error bars (central68,truncrms68)")
    ap.add_argument("--methodBootstrapSeed", type=int, default=54321,
                    help="Seed base for method bootstrap RNG")
    ap.add_argument("--methodBootstrapCap", type=int, default=5000,
                    help="Cap sample size for method bootstrap (speed)")

    ap.add_argument("--maxRelErrWarn", type=float, default=0.5,
                    help="Warn if (err/value) exceeds this for any method point (value>0)")

    args = ap.parse_args()

    inputs = discover_inputs(args.inputDir)
    if not inputs:
        raise RuntimeError(f"No eta_* directories with reco_*.root found under {args.inputDir}")

    fout = ROOT.TFile.Open(args.outRoot, "RECREATE")
    if not fout or fout.IsZombie():
        raise RuntimeError(f"Could not create output ROOT file: {args.outRoot}")
    ROOT.SetOwnership(fout, False)
    fout.cd()

    summary = ROOT.TTree("summary", "pT resolution summary per (eta, pt)")
    eta_buf = array.array("b", [0] * 64)  # char[64]
    pt_true = array.array("d", [0.0])
    n_usable = array.array("i", [0])
    n_quality = array.array("i", [0])

    method_val = {m[0]: array.array("d", [float("nan")]) for m in METHODS}
    method_err = {m[0]: array.array("d", [float("nan")]) for m in METHODS}

    diag_val = {}
    diag_err = {}
    for (k, _, _) in DIAG_FIELDS:
        if k in ("n_usable", "n_quality"):
            continue
        diag_val[k] = array.array("d", [float("nan")])
        diag_err[k] = array.array("d", [float("nan")])

    summary.Branch("eta", eta_buf, "eta/C")
    summary.Branch("pt_true", pt_true, "pt_true/D")
    summary.Branch("n_usable", n_usable, "n_usable/I")
    summary.Branch("n_quality", n_quality, "n_quality/I")

    for key, _, _ in METHODS:
        summary.Branch(f"{key}", method_val[key], f"{key}/D")
        summary.Branch(f"{key}_err", method_err[key], f"{key}_err/D")

    for k in diag_val:
        summary.Branch(k, diag_val[k], f"{k}/D")
        summary.Branch(f"{k}_err", diag_err[k], f"{k}_err/D")

    data = {}
    relerr_data = {}
    diag_data = {}
    per_method_graphs = {m[0]: {} for m in METHODS}

    for eta_dir, files in inputs.items():
        files_sorted = sorted(files, key=lambda p: (parse_pt_from_name(p) if parse_pt_from_name(p) is not None else 1e99))
        if args.maxFilesPerEta and args.maxFilesPerEta > 0:
            files_sorted = files_sorted[:args.maxFilesPerEta]

        data[eta_dir] = {m[0]: [] for m in METHODS}
        relerr_data[eta_dir] = {m[0]: [] for m in METHODS}
        diag_data[eta_dir] = {k: [] for (k, _, _) in DIAG_FIELDS}

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

            metrics, diags, diag_errs = compute_metrics_and_diags(
                results, pt, args.qualityCut,
                diag_bootstrap=args.diagBootstrap,
                diag_bootstrap_seed=args.diagBootstrapSeed,
                err_bootstrap=args.methodBootstrap,
                err_bootstrap_seed=args.methodBootstrapSeed,
                err_bootstrap_cap=args.methodBootstrapCap,
            )

            eta_s = eta_dir.encode("utf-8")[:63]
            for i in range(64):
                eta_buf[i] = 0
            for i, b in enumerate(eta_s):
                eta_buf[i] = b

            pt_true[0] = float(pt)
            n_usable[0] = int(diags.get("n_usable", 0))
            n_quality[0] = int(diags.get("n_quality", 0))

            for key, _, _ in METHODS:
                method_val[key][0] = float("nan")
                method_err[key][0] = float("nan")

            for key, _, _ in METHODS:
                if key in metrics:
                    v, e, n_used = metrics[key]
                    method_val[key][0] = float(v)
                    method_err[key][0] = float(e) if finite(e) else float("nan")
                    data[eta_dir][key].append((pt, v, e))

                    if finite(v) and v != 0.0 and finite(e) and e >= 0.0:
                        rel = abs(e / v)
                        relerr_data[eta_dir][key].append((pt, rel))
                        if v > 0 and rel > args.maxRelErrWarn:
                            print(f"[warn] {eta_dir} pt={pt:g} method={key}: relErr={rel:.3g} (err={e:.3g}, val={v:.3g})")

            for (k, _, _) in DIAG_FIELDS:
                if k in ("n_usable", "n_quality"):
                    diag_data[eta_dir][k].append((pt, float(diags.get(k, 0.0)), 0.0))
                else:
                    vv = float(diags.get(k, float("nan")))
                    ee = float(diag_errs.get(k, float("nan")))
                    diag_val[k][0] = vv
                    diag_err[k][0] = ee if finite(ee) else float("nan")
                    diag_data[eta_dir][k].append((pt, vv, ee if finite(ee) else 0.0))

            summary.Fill()

    byEta_dir = ensure_dir(fout, ["byEta"])
    byMethod_dir = ensure_dir(fout, ["byMethod"])
    diag_rootdir = ensure_dir(fout, ["diagnostics"])

    colors = [1, 2, 4, 6, 8, 9, 46, 38, 28, 32]
    mstyles = [20, 21, 22, 23, 24, 25, 26, 27, 28, 30]

    keepalive = []

    for eta_dirname in sorted(data.keys()):
        eta_out = ensure_dir(byEta_dir, [eta_dirname])

        graphs = {}
        relerr_graphs = {}

        for im, (mkey, mlabel, _) in enumerate(METHODS):
            pts = sorted(data[eta_dirname][mkey], key=lambda t: t[0])
            g = make_graph(f"gr_{mkey}", f"{eta_dirname}: {mlabel}", "resolution")
            for (pt, val, err) in pts:
                if finite(val) and val > 0.0:
                    add_point(g, pt, val, 0.0, err if finite(err) and err >= 0 else 0.0)
            style_graph(g, colors[im % len(colors)], mstyles[im % len(mstyles)])
            graphs[mkey] = g
            per_method_graphs[mkey][eta_dirname] = g
            write_obj(eta_out, g)
            keepalive.append(g)

            gre = make_graph(f"gr_{mkey}_relerr", f"{eta_dirname}: {mkey} relative error", "err/value")
            for (pt, rel) in sorted(relerr_data[eta_dirname][mkey], key=lambda t: t[0]):
                if finite(rel):
                    add_point(gre, pt, rel, 0.0, 0.0)
            style_graph(gre, colors[im % len(colors)], mstyles[im % len(mstyles)])
            relerr_graphs[mkey] = gre
            write_obj(eta_out, gre)
            keepalive.append(gre)

        mg = make_multigraph("mg_methods", f"{eta_dirname}: resolution estimators; pT [GeV]; resolution")
        leg = make_legend("legend_methods")
        for (mkey, _, _) in METHODS:
            mg.Add(graphs[mkey], "PE")
            leg.AddEntry(graphs[mkey], mkey, "p")

        write_obj(eta_out, mg)
        write_obj(eta_out, leg)
        keepalive.extend([mg, leg])

        c = make_canvas("c_methods_loglog", f"{eta_dirname} methods (log-log)")
        c.SetLogx(1)
        c.SetLogy(1)

        ymin, ymax = multigraph_minmax_positive([graphs[m[0]] for m in METHODS])
        if finite(ymin) and ymin > 0 and finite(ymax) and ymax > 0:
            mg.SetMinimum(ymin * 0.7)
            mg.SetMaximum(ymax * 1.4)
        else:
            mg.SetMinimum(1e-6)
            mg.SetMaximum(1.0)

        mg.Draw("APE")
        mg.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
        mg.GetYaxis().SetTitle("resolution")
        leg.Draw()
        write_obj(eta_out, c)
        keepalive.append(c)

        mgre = make_multigraph("mg_methods_relerr", f"{eta_dirname}: method relative errors; pT [GeV]; err/value")
        legre = make_legend("legend_methods_relerr")
        for (mkey, _, _) in METHODS:
            mgre.Add(relerr_graphs[mkey], "P")
            legre.AddEntry(relerr_graphs[mkey], mkey, "p")
        cre = make_canvas("c_methods_relerr_logx", f"{eta_dirname} method relative errors")
        cre.SetLogx(1)
        cre.SetLogy(0)
        mgre.Draw("A")
        mgre.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
        mgre.GetYaxis().SetTitle("err/value")
        legre.Draw()
        write_obj(eta_out, mgre)
        write_obj(eta_out, legre)
        write_obj(eta_out, cre)
        keepalive.extend([mgre, legre, cre])

        ddir = ensure_dir(diag_rootdir, [eta_dirname])
        diag_graphs = {}

        for idg, (dk, dlabel, _) in enumerate(DIAG_FIELDS):
            g = make_graph(f"gr_{dk}", f"{eta_dirname}: {dlabel}", dk)
            pts = sorted(diag_data[eta_dirname][dk], key=lambda t: t[0])
            for (pt, v, e) in pts:
                if finite(v):
                    add_point(g, pt, v, 0.0, e if (finite(e) and e >= 0.0) else 0.0)
            style_graph(g, colors[idg % len(colors)], mstyles[idg % len(mstyles)])
            write_obj(ddir, g)
            keepalive.append(g)
            diag_graphs[dk] = g

        cdiag = make_canvas("c_diagnostics_logx", f"{eta_dirname} diagnostics (log-x)")
        cdiag.SetLogx(1)
        cdiag.SetLogy(0)

        keys_overlay = ["frac_curvObs", "frac_circleOK", "frac_timeSrc"]
        mgd = make_multigraph("mg_diag_frac", f"{eta_dirname}: key fractions; pT [GeV]; fraction")
        legd = ROOT.TLegend(0.12, 0.70, 0.55, 0.88)
        legd.SetName("legend_diag_frac")
        legd.SetBorderSize(0)
        legd.SetFillStyle(0)
        ROOT.SetOwnership(legd, False)

        for k in keys_overlay:
            if k in diag_graphs:
                mgd.Add(diag_graphs[k], "PE")
                legd.AddEntry(diag_graphs[k], k, "p")

        mgd.Draw("APE")
        mgd.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
        mgd.GetYaxis().SetTitle("fraction")
        legd.Draw()

        write_obj(ddir, mgd)
        write_obj(ddir, legd)
        write_obj(ddir, cdiag)
        keepalive.extend([mgd, legd, cdiag])

    for (mkey, mlabel, _) in METHODS:
        mdir = ensure_dir(byMethod_dir, [mkey])

        mg = make_multigraph("mg_etas", f"{mkey}: {mlabel} (all etas); pT [GeV]; resolution")
        leg = ROOT.TLegend(0.12, 0.65, 0.55, 0.88)
        leg.SetName("legend_etas")
        leg.SetBorderSize(0)
        leg.SetFillStyle(0)
        ROOT.SetOwnership(leg, False)

        clones = []
        for ie, eta_dirname in enumerate(sorted(per_method_graphs[mkey].keys())):
            g0 = per_method_graphs[mkey][eta_dirname]
            g = g0.Clone(f"{eta_dirname}_gr_{mkey}")
            ROOT.SetOwnership(g, False)
            style_graph(g, colors[ie % len(colors)], mstyles[ie % len(mstyles)])
            mg.Add(g, "PE")
            leg.AddEntry(g, eta_dirname, "p")
            clones.append(g)

        write_obj(mdir, mg)
        write_obj(mdir, leg)
        for g in clones:
            write_obj(mdir, g)
        keepalive.extend([mg, leg] + clones)

        c = make_canvas("c_etas_loglog", f"{mkey} across etas (log-log)")
        c.SetLogx(1)
        c.SetLogy(1)

        ymin, ymax = multigraph_minmax_positive(clones)
        if finite(ymin) and ymin > 0 and finite(ymax) and ymax > 0:
            mg.SetMinimum(ymin * 0.7)
            mg.SetMaximum(ymax * 1.4)
        else:
            mg.SetMinimum(1e-6)
            mg.SetMaximum(1.0)

        mg.Draw("APE")
        mg.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
        mg.GetYaxis().SetTitle("resolution")
        leg.Draw()

        write_obj(mdir, c)
        keepalive.append(c)

    fout.cd()
    summary.Write()
    fout.Close()

    print(f"[ok] wrote {args.outRoot}")


if __name__ == "__main__":
    main()
