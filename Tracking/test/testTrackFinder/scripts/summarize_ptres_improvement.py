# DOC:
# Summary: Summarize pT-resolution improvement between two analysis ROOT files by matching eta/pT graph points and writing per-point, per-eta, global, text, and ROOT summary products.
# Status: authoritative
# Usage:
#   python3 scripts/summarize_ptres_improvement.py --new NEW.root --old OLD.root --outdir OUTDIR --newLabel NEW --oldLabel OLD
#   python3 scripts/summarize_ptres_improvement.py --new CF_ptres.root --old W_ptres.root --outdir OUTDIR --newLabel CF --oldLabel W --methods central68,truncrms68,rms,mad
# Examples:
#   python3 scripts/summarize_ptres_improvement.py \
#     --new /eos/.../CF25_Au2p227matched_ptres.root \
#     --old /eos/.../W20_Au0p3_defaultlike_ptres.root \
#     --outdir artifacts/analysis/CF25_Au2p227matched_vs_W20_Au0p3_defaultlike_improvement \
#     --newLabel CF25_Au2p227matched \
#     --oldLabel W20_Au0p3_defaultlike \
#     --methods central68,truncrms68,rms,madsigma
# Inputs: Two pT-resolution analysis ROOT files, normally produced by scripts/analyze_pt_resolution_grid.py, containing eta-sliced TGraph/TGraphErrors/TGraphAsymmErrors objects with pT on the x-axis and resolution-like quantities on the y-axis.
# Outputs: improvement_per_point.csv, improvement_per_eta.csv, improvement_global_by_method.csv, summary.txt, and improvement_summary.root under OUTDIR.
# Collections: None; reads ROOT analysis graph objects rather than EDM4hep collections.
# Connects-To: scripts/analyze_pt_resolution_grid.py, scripts/compare_pt_resolution_grid.py, scripts/export_root_plots.py, artifacts/analysis/
# Arguments:
#   --new: new/test analysis ROOT file; for CF-vs-W closeout this is usually the CF variant if smaller resolution is considered improvement.
#   --old: old/reference analysis ROOT file; for CF-vs-W closeout this is usually the W/default-like baseline.
#   --outdir: output directory for CSV, text, and ROOT summary products.
#   --newLabel: label used for the new/test file in summary text; default new.
#   --oldLabel: label used for the old/reference file in summary text; default old.
#   --etaRound: number of decimal digits used when matching eta values between files; default 3.
#   --ptRound: number of decimal digits used when matching pT values between files; default 6.
#   --methods: optional comma-separated filter for method names to keep, such as central68,truncrms68,rms,mad.
# Notes:
#   Improvement is defined as 100*(old-new)/old for metrics where smaller is better, so positive values mean the new/test file has smaller pT-resolution metric than the old/reference file.
#   The script recursively reads all graph-like objects and infers the method name from the graph path/name using canonical substrings such as truncrms68, central68, meanabs, medianabs, mad, and rms.
#   Eta is inferred from graph paths/names; graphs without an identifiable eta token are skipped.
#   Matching is done by rounded eta and rounded pT keys, so etaRound/ptRound should be kept stable across closeout summaries.
#   Per-point CSV rows preserve old/new values, errors, improvement percent, and source graph names for traceability.
#   Per-eta summaries aggregate improvement distributions and also report net improvement from mean and median metric values.
#   The ROOT output contains per-method improvement graphs/histograms versus eta plus a method_summary TTree.
#   Use this after producing variant-specific pT-resolution summary ROOT files; use compare_pt_resolution_grid.py when you also need overlay/ratio plot products.
# Tags: authoritative, pt-resolution, improvement-summary, cf-vs-w, root, csv, closeout, analysis
# DOC_END

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import ROOT


ROOT.gROOT.SetBatch(True)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def is_finite(x: float) -> bool:
    return math.isfinite(x)


def median(vals: List[float]) -> float:
    if not vals:
        return float("nan")
    return statistics.median(vals)


def mean(vals: List[float]) -> float:
    if not vals:
        return float("nan")
    return statistics.fmean(vals)


def rms(vals: List[float]) -> float:
    if not vals:
        return float("nan")
    m = mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / len(vals))


def percentile(vals: List[float], q: float) -> float:
    if not vals:
        return float("nan")
    xs = sorted(vals)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac


def improvement_percent(old_val: float, new_val: float) -> float:
    """
    Positive means 'new' improved relative to 'old' for a metric where smaller is better.
    """
    if not is_finite(old_val) or not is_finite(new_val):
        return float("nan")
    if old_val == 0.0:
        return float("nan")
    return 100.0 * (old_val - new_val) / old_val


def sanitize(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "_", name)


# ------------------------------------------------------------
# Data structures
# ------------------------------------------------------------

@dataclass
class Point:
    eta: float
    pt: float
    y: float
    ey: float
    method: str
    source_graph: str


# ------------------------------------------------------------
# ROOT reading
# ------------------------------------------------------------

def list_all_graphs(tdir: ROOT.TDirectory, prefix: str = "") -> Dict[str, ROOT.TObject]:
    out = {}
    keys = tdir.GetListOfKeys()
    if not keys:
        return out

    for key in keys:
        obj = key.ReadObj()
        name = key.GetName()
        full = f"{prefix}/{name}" if prefix else name

        if obj.InheritsFrom("TDirectory"):
            out.update(list_all_graphs(obj, full))
        else:
            if obj.InheritsFrom("TGraph") or obj.InheritsFrom("TGraphErrors") or obj.InheritsFrom("TGraphAsymmErrors"):
                out[full] = obj
    return out


def infer_method_from_graph_name(graph_path: str) -> str:
    """
    Extract the actual pt-resolution method from a graph/object name.
    Prefer canonical method names over raw object names.
    """
    lower = graph_path.lower()

    # Ordered from more specific to more generic
    canonical_methods = [
        "truncrms68",
        "central68",
        "meanabs",
        "medianabs",
        "gauscore",
        "circle",
        "curv",
        "mad",
        "rms",
    ]

    for method in canonical_methods:
        if method in lower:
            return method

    # Fallback: last path token if nothing canonical matched
    return graph_path.split("/")[-1]


def infer_eta_from_graph_path(graph_path: str) -> Optional[float]:
    """
    Try to infer eta from object path/name if encoded there, e.g. eta+0.50, eta_-1.00, etc.
    """
    m = re.search(r"eta[_:=/]*([+-]?\d+(?:\.\d+)?)", graph_path.replace("p", "."))
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    # Also accept patterns like ..._eta+0.50_...
    m = re.search(r"eta([+-]\d+(?:\.\d+)?)", graph_path)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    return None


def graph_points_with_errors(graph: ROOT.TObject) -> List[Tuple[float, float, float]]:
    """
    Return (x, y, ey) for TGraph-like object.
    Compatible with newer PyROOT where ROOT.Double may not exist.
    """
    pts = []
    n = graph.GetN()

    for i in range(n):
        # Preferred path for modern PyROOT
        if hasattr(graph, "GetPointX") and hasattr(graph, "GetPointY"):
            xv = float(graph.GetPointX(i))
            yv = float(graph.GetPointY(i))
        else:
            # Fallback for older bindings
            import ctypes
            x = ctypes.c_double(0.0)
            y = ctypes.c_double(0.0)
            graph.GetPoint(i, x, y)
            xv = float(x.value)
            yv = float(y.value)

        ey = 0.0
        if graph.InheritsFrom("TGraphErrors"):
            ey = float(graph.GetErrorY(i))
        elif graph.InheritsFrom("TGraphAsymmErrors"):
            ey = 0.5 * (float(graph.GetErrorYlow(i)) + float(graph.GetErrorYhigh(i)))

        pts.append((xv, yv, ey))

    return pts


def read_points(root_path: Path) -> Dict[str, List[Point]]:
    """
    Read all graph-like objects and group them by inferred method.
    Assumes x-axis is pT and eta is encoded in path/name.
    """
    f = ROOT.TFile.Open(str(root_path), "READ")
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open ROOT file: {root_path}")

    graphs = list_all_graphs(f)
    grouped: Dict[str, List[Point]] = {}

    for gpath, gobj in graphs.items():
        eta = infer_eta_from_graph_path(gpath)
        if eta is None:
            # Skip graphs that are not eta-sliced pt-resolution curves
            continue

        method = infer_method_from_graph_name(gpath)
        pts = graph_points_with_errors(gobj)

        if method not in grouped:
            grouped[method] = []

        for pt, y, ey in pts:
            grouped[method].append(
                Point(
                    eta=eta,
                    pt=pt,
                    y=y,
                    ey=ey,
                    method=method,
                    source_graph=gpath,
                )
            )

    f.Close()
    return grouped


# ------------------------------------------------------------
# Matching and summaries
# ------------------------------------------------------------

def build_lookup(points: List[Point], eta_digits: int, pt_digits: int) -> Dict[Tuple[float, float], Point]:
    lut = {}
    for p in points:
        key = (round(p.eta, eta_digits), round(p.pt, pt_digits))
        lut[key] = p
    return lut


def summarize_method(
    method: str,
    new_points: List[Point],
    old_points: List[Point],
    eta_digits: int,
    pt_digits: int,
) -> Tuple[List[dict], List[dict]]:
    """
    Returns:
      per_point_rows, per_eta_rows
    """
    new_lut = build_lookup(new_points, eta_digits, pt_digits)
    old_lut = build_lookup(old_points, eta_digits, pt_digits)

    shared_keys = sorted(set(new_lut.keys()) & set(old_lut.keys()))
    per_point_rows: List[dict] = []

    per_eta_bucket: Dict[float, List[float]] = {}
    old_vals_by_eta: Dict[float, List[float]] = {}
    new_vals_by_eta: Dict[float, List[float]] = {}

    for key in shared_keys:
        newp = new_lut[key]
        oldp = old_lut[key]

        imp = improvement_percent(oldp.y, newp.y)

        row = {
            "method": method,
            "eta": newp.eta,
            "pt": newp.pt,
            "old_value": oldp.y,
            "new_value": newp.y,
            "old_err": oldp.ey,
            "new_err": newp.ey,
            "improvement_percent": imp,
            "old_graph": oldp.source_graph,
            "new_graph": newp.source_graph,
        }
        per_point_rows.append(row)

        per_eta_bucket.setdefault(newp.eta, []).append(imp)
        old_vals_by_eta.setdefault(newp.eta, []).append(oldp.y)
        new_vals_by_eta.setdefault(newp.eta, []).append(newp.y)

    per_eta_rows: List[dict] = []
    for eta in sorted(per_eta_bucket.keys()):
        imps = [x for x in per_eta_bucket[eta] if is_finite(x)]
        olds = [x for x in old_vals_by_eta[eta] if is_finite(x)]
        news = [x for x in new_vals_by_eta[eta] if is_finite(x)]

        per_eta_rows.append({
            "method": method,
            "eta": eta,
            "n_points": len(imps),
            "mean_improvement_percent": mean(imps),
            "median_improvement_percent": median(imps),
            "rms_improvement_percent": rms(imps),
            "min_improvement_percent": min(imps) if imps else float("nan"),
            "max_improvement_percent": max(imps) if imps else float("nan"),
            "p16_improvement_percent": percentile(imps, 0.16),
            "p84_improvement_percent": percentile(imps, 0.84),
            "old_mean_value": mean(olds),
            "new_mean_value": mean(news),
            "old_median_value": median(olds),
            "new_median_value": median(news),
            "net_improvement_from_means_percent": improvement_percent(mean(olds), mean(news)),
            "net_improvement_from_medians_percent": improvement_percent(median(olds), median(news)),
        })

    return per_point_rows, per_eta_rows


def global_method_summary(per_point_rows: List[dict]) -> dict:
    imps = [r["improvement_percent"] for r in per_point_rows if is_finite(r["improvement_percent"])]
    olds = [r["old_value"] for r in per_point_rows if is_finite(r["old_value"])]
    news = [r["new_value"] for r in per_point_rows if is_finite(r["new_value"])]

    return {
        "n_points": len(imps),
        "mean_improvement_percent": mean(imps),
        "median_improvement_percent": median(imps),
        "rms_improvement_percent": rms(imps),
        "min_improvement_percent": min(imps) if imps else float("nan"),
        "max_improvement_percent": max(imps) if imps else float("nan"),
        "p16_improvement_percent": percentile(imps, 0.16),
        "p84_improvement_percent": percentile(imps, 0.84),
        "old_mean_value": mean(olds),
        "new_mean_value": mean(news),
        "old_median_value": median(olds),
        "new_median_value": median(news),
        "net_improvement_from_means_percent": improvement_percent(mean(olds), mean(news)),
        "net_improvement_from_medians_percent": improvement_percent(median(olds), median(news)),
        "frac_points_improved": (
            sum(1 for x in imps if x > 0.0) / len(imps) if imps else float("nan")
        ),
        "frac_points_worsened": (
            sum(1 for x in imps if x < 0.0) / len(imps) if imps else float("nan")
        ),
    }


# ------------------------------------------------------------
# Output writing
# ------------------------------------------------------------

def write_csv(path: Path, rows: List[dict]) -> None:
    if not rows:
        with path.open("w", newline="") as f:
            f.write("")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_txt(
    path: Path,
    new_label: str,
    old_label: str,
    global_rows: List[dict],
    per_eta_rows: List[dict],
) -> None:
    lines = []
    lines.append(f"Improvement summary")
    lines.append(f"new = {new_label}")
    lines.append(f"old = {old_label}")
    lines.append("")

    lines.append("Global per-method summary")
    lines.append("-" * 80)
    for row in global_rows:
        lines.append(
            f"{row['method']}: "
            f"n={row['n_points']}, "
            f"mean={row['mean_improvement_percent']:.3f}%, "
            f"median={row['median_improvement_percent']:.3f}%, "
            f"p16={row['p16_improvement_percent']:.3f}%, "
            f"p84={row['p84_improvement_percent']:.3f}%, "
            f"frac_improved={100.0*row['frac_points_improved']:.1f}%"
        )

    lines.append("")
    lines.append("Per-eta summary")
    lines.append("-" * 80)

    by_method: Dict[str, List[dict]] = {}
    for row in per_eta_rows:
        by_method.setdefault(row["method"], []).append(row)

    for method in sorted(by_method.keys()):
        lines.append(f"[{method}]")
        for row in sorted(by_method[method], key=lambda r: r["eta"]):
            lines.append(
                f"  eta={row['eta']:+.2f}: "
                f"n={row['n_points']}, "
                f"mean={row['mean_improvement_percent']:.3f}%, "
                f"median={row['median_improvement_percent']:.3f}%, "
                f"net_from_means={row['net_improvement_from_means_percent']:.3f}%"
            )
        lines.append("")

    path.write_text("\n".join(lines))


def write_root_summary(
    path: Path,
    per_eta_rows: List[dict],
    global_rows: List[dict],
) -> None:
    f = ROOT.TFile(str(path), "RECREATE")

    # Per-method TGraphErrors vs eta for median improvement
    by_method: Dict[str, List[dict]] = {}
    for row in per_eta_rows:
        by_method.setdefault(row["method"], []).append(row)

    for method, rows in by_method.items():
        rows = sorted(rows, key=lambda r: r["eta"])

        g_mean = ROOT.TGraph(len(rows))
        g_mean.SetName(f"g_mean_improvement_vs_eta__{sanitize(method)}")
        g_mean.SetTitle(f"{method};#eta;Mean improvement [%]")

        g_med = ROOT.TGraph(len(rows))
        g_med.SetName(f"g_median_improvement_vs_eta__{sanitize(method)}")
        g_med.SetTitle(f"{method};#eta;Median improvement [%]")

        h = ROOT.TH1D(
            f"h_improvement_vs_eta__{sanitize(method)}",
            f"{method};#eta bin;Median improvement [%]",
            len(rows),
            0,
            len(rows),
        )

        for i, row in enumerate(rows):
            eta = float(row["eta"])
            mean_imp = float(row["mean_improvement_percent"])
            med_imp = float(row["median_improvement_percent"])

            g_mean.SetPoint(i, eta, mean_imp)
            g_med.SetPoint(i, eta, med_imp)

            h.SetBinContent(i + 1, med_imp)
            h.GetXaxis().SetBinLabel(i + 1, f"{eta:+.2f}")

        g_mean.Write()
        g_med.Write()
        h.Write()

    # Global summary tree
    t = ROOT.TTree("method_summary", "Global per-method improvement summary")

    import array
    method_buf = ROOT.std.string()
    n_points = array.array("i", [0])
    mean_imp = array.array("d", [0.0])
    med_imp = array.array("d", [0.0])
    p16_imp = array.array("d", [0.0])
    p84_imp = array.array("d", [0.0])
    frac_improved = array.array("d", [0.0])

    t.Branch("method", method_buf)
    t.Branch("n_points", n_points, "n_points/I")
    t.Branch("mean_improvement_percent", mean_imp, "mean_improvement_percent/D")
    t.Branch("median_improvement_percent", med_imp, "median_improvement_percent/D")
    t.Branch("p16_improvement_percent", p16_imp, "p16_improvement_percent/D")
    t.Branch("p84_improvement_percent", p84_imp, "p84_improvement_percent/D")
    t.Branch("frac_points_improved", frac_improved, "frac_points_improved/D")

    for row in global_rows:
        method_buf.replace(0, ROOT.std.string.npos, str(row["method"]))
        n_points[0] = int(row["n_points"])
        mean_imp[0] = float(row["mean_improvement_percent"])
        med_imp[0] = float(row["median_improvement_percent"])
        p16_imp[0] = float(row["p16_improvement_percent"])
        p84_imp[0] = float(row["p84_improvement_percent"])
        frac_improved[0] = float(row["frac_points_improved"])
        t.Fill()

    t.Write()
    f.Close()


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize percent improvement per eta/method between a new and old pt-resolution analysis ROOT output."
    )
    parser.add_argument("--new", required=True, help="New analysis ROOT file")
    parser.add_argument("--old", required=True, help="Old analysis ROOT file")
    parser.add_argument("--outdir", required=True, help="Output directory")
    parser.add_argument("--newLabel", default="new", help="Label for new file")
    parser.add_argument("--oldLabel", default="old", help="Label for old file")
    parser.add_argument("--etaRound", type=int, default=3, help="Rounding digits for eta matching")
    parser.add_argument("--ptRound", type=int, default=6, help="Rounding digits for pt matching")
    parser.add_argument(
    "--methods",
    default="",
    help="Comma-separated list of methods to keep, e.g. central68,truncrms68,rms,mad",
)
    args = parser.parse_args()

    new_path = Path(args.new).resolve()
    old_path = Path(args.old).resolve()
    outdir = Path(args.outdir).resolve()

    safe_mkdir(outdir)

    new_grouped = read_points(new_path)
    old_grouped = read_points(old_path)

    common_methods = sorted(set(new_grouped.keys()) & set(old_grouped.keys()))

    if args.methods.strip():
        requested = {m.strip() for m in args.methods.split(",") if m.strip()}
        common_methods = [m for m in common_methods if m in requested]

    if not common_methods:
        raise RuntimeError(
            "No common methods found between the two ROOT files after filtering. "
            "Check --methods or adjust the object-name heuristic."
        )

    all_per_point_rows: List[dict] = []
    all_per_eta_rows: List[dict] = []
    global_rows: List[dict] = []

    for method in common_methods:
        per_point, per_eta = summarize_method(
            method=method,
            new_points=new_grouped[method],
            old_points=old_grouped[method],
            eta_digits=args.etaRound,
            pt_digits=args.ptRound,
        )

        all_per_point_rows.extend(per_point)
        all_per_eta_rows.extend(per_eta)

        grow = {"method": method}
        grow.update(global_method_summary(per_point))
        global_rows.append(grow)

    # Write outputs
    write_csv(outdir / "improvement_per_point.csv", all_per_point_rows)
    write_csv(outdir / "improvement_per_eta.csv", all_per_eta_rows)
    write_csv(outdir / "improvement_global_by_method.csv", global_rows)
    write_summary_txt(
        outdir / "summary.txt",
        new_label=args.newLabel,
        old_label=args.oldLabel,
        global_rows=global_rows,
        per_eta_rows=all_per_eta_rows,
    )
    write_root_summary(
        outdir / "improvement_summary.root",
        per_eta_rows=all_per_eta_rows,
        global_rows=global_rows,
    )

    print(f"[ok] Wrote outputs to: {outdir}")
    print(f"[ok] Common methods: {', '.join(common_methods)}")


if __name__ == "__main__":
    main()