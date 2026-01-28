#!/usr/bin/env python3
"""

DOC
compare_pt_resolution_outputs.py

Compare two ROOT outputs from analyze_pt_resolution_grid.py (e.g. CF vs W).

Creates a new ROOT file containing:
  - compare/byEta/<eta>/ : overlays CF vs W + ratio CF/W for each resolution METHOD
  - compare/byMethod/<method>/ : overlays across etas for each METHOD + per-eta compare + ratio
  - compare/diagnostics/byEta/<eta>/ :
      * overlays for diagnostic quantities from the *summary* TTree (A vs B)
      * ratio A/B for those diagnostics (only where both exist and denominator != 0)
      * pass fraction plots: n_quality/n_usable (A vs B) and ratio
  - compare/diagnostics/diag_compare : a TTree with per-(eta,pt) diagnostic values + diffs/ratios + a simple "suspect" flag

This diagnostic section is meant to help decide whether improvements are "representative"
(physics/material) or could be driven by selection/algorithmic survivorship.

Missing points are handled gracefully: ratio only includes pT where both exist and finite.

Usage:
  python3 compare_pt_resolution_outputs.py \
    --a CF_out.root --b W_out.root \
    --out compare_CF_vs_W.root \
    --tagA CF --tagB W

Optional knobs:
  --diagAbsTolPassFrac 0.05   (absolute tolerance on pass fraction difference)
  --diagRelTolPassFrac 0.10   (relative tolerance on pass fraction ratio-1)
  --diagAbsTolFrac     0.05   (abs tol for frac_* diagnostics)
  --diagRelTolMed      0.25   (rel tol for med_* diagnostics)

DOC_END
"""

import argparse
import math
import ctypes
import ROOT
ROOT.gROOT.SetBatch(True)


# -----------------------------
# helpers
# -----------------------------
def finite(x):
    return x is not None and isinstance(x, (int, float)) and math.isfinite(x)

def ensure_dir(rootdir, parts):
    d = rootdir
    for p in parts:
        nd = d.GetDirectory(p)
        if not nd:
            nd = d.mkdir(p)
        d = nd
    return d

def write_obj(d, obj, name_override=None):
    d.cd()
    if name_override:
        obj.Write(name_override)
    else:
        obj.Write()

def get_tgraph(f, path):
    """Return TGraphErrors/TGraph at path or None."""
    obj = f.Get(path)
    if not obj:
        return None
    if not isinstance(obj, ROOT.TGraph):
        return None
    return obj

def graph_points_map(g, x_round=6):
    """
    Convert graph points to dict keyed by rounded x.
    Returns: dict[key] = (x, y, ex, ey)
    """
    out = {}
    n = g.GetN()
    x = ctypes.c_double(0.0)
    y = ctypes.c_double(0.0)
    for i in range(n):
        g.GetPoint(i, x, y)
        xx = float(x.value)
        yy = float(y.value)
        ex = float(g.GetErrorX(i)) if hasattr(g, "GetErrorX") else 0.0
        ey = float(g.GetErrorY(i)) if hasattr(g, "GetErrorY") else 0.0
        key = round(xx, x_round)
        out[key] = (xx, yy, ex, ey)
    return out

def make_ratio_graph(name, title, gA, gB, x_round=6):
    """
    Ratio = A/B. Only fill points where both exist, yA finite, yB finite, yB!=0.
    If both ey finite, propagate: r * sqrt((eyA/yA)^2 + (eyB/yB)^2), guarding yA,yB.
    """
    if (gA is None) or (gB is None):
        return None

    mA = graph_points_map(gA, x_round=x_round)
    mB = graph_points_map(gB, x_round=x_round)

    gr = ROOT.TGraphErrors()
    gr.SetName(name)
    gr.SetTitle(title)
    gr.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
    gr.GetYaxis().SetTitle("ratio")
    ROOT.SetOwnership(gr, False)

    keys = sorted(set(mA.keys()) & set(mB.keys()))
    ip = 0
    for k in keys:
        xA, yA, exA, eyA = mA[k]
        xB, yB, exB, eyB = mB[k]
        xx = float(xA)

        if not (finite(yA) and finite(yB)):
            continue
        if yB == 0.0:
            continue

        r = yA / yB

        er = 0.0
        if finite(eyA) and finite(eyB) and eyA >= 0 and eyB >= 0:
            if yA != 0.0 and yB != 0.0:
                er = abs(r) * math.sqrt((eyA / yA) ** 2 + (eyB / yB) ** 2)

        gr.SetPoint(ip, xx, r)
        gr.SetPointError(ip, 0.0, er)
        ip += 1

    return gr

def style_graph(g, color, mstyle, msize=0.95, no_line=True):
    g.SetMarkerColor(color)
    g.SetLineColor(color)
    g.SetMarkerStyle(mstyle)
    g.SetMarkerSize(msize)
    if no_line:
        g.SetLineWidth(0)
    else:
        g.SetLineWidth(2)

def graph_minmax_positive(g):
    n = g.GetN()
    x = ctypes.c_double(0.0)
    y = ctypes.c_double(0.0)
    minp = float("inf")
    maxv = -float("inf")
    for i in range(n):
        g.GetPoint(i, x, y)
        yy = float(y.value)
        if finite(yy):
            if yy > 0:
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
        if not g:
            continue
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

def make_canvas(name, title, w=900, h=700):
    c = ROOT.TCanvas(name, title, w, h)
    ROOT.SetOwnership(c, False)
    c.SetTicks(1, 1)
    c.SetGrid(1, 1)
    return c


# -----------------------------
# summary tree helpers (diagnostics)
# -----------------------------
def _decode_eta_field(v):
    # In your analyze script, eta is stored as "eta/C" (char array). In PyROOT, it can show up as bytes/str.
    if v is None:
        return None
    if isinstance(v, bytes):
        try:
            return v.decode("utf-8", errors="ignore").split("\x00")[0]
        except Exception:
            return str(v)
    if isinstance(v, str):
        return v.split("\x00")[0]
    return str(v)

def read_summary_map(f, x_round=6):
    """
    Read TTree 'summary' and return:
      data[eta][pt_key] = { branch: value, ... }

    pt_key = round(pt_true, x_round)
    """
    t = f.Get("summary")
    if not t or not isinstance(t, ROOT.TTree):
        return {}, []

    # Determine available branches (names)
    branches = [b.GetName() for b in t.GetListOfBranches()]

    needed = ["eta", "pt_true", "n_usable", "n_quality"]
    for n in needed:
        if n not in branches:
            # If these aren't there, we can't do the diagnostics compare robustly
            return {}, branches

    out = {}
    nent = t.GetEntries()
    for i in range(nent):
        t.GetEntry(i)

        eta = _decode_eta_field(getattr(t, "eta", None))
        pt = float(getattr(t, "pt_true"))
        if not eta or not finite(pt):
            continue
        pt_key = round(pt, x_round)

        if eta not in out:
            out[eta] = {}
        if pt_key not in out[eta]:
            out[eta][pt_key] = {}

        # copy all numeric branches we can access
        for bn in branches:
            if bn == "eta":
                continue
            try:
                val = getattr(t, bn)
                # PyROOT gives python scalars for basic branches
                if isinstance(val, (int, float)):
                    out[eta][pt_key][bn] = float(val)
                else:
                    # ignore weird/complex branches
                    pass
            except Exception:
                pass

        # Always store original pt for exact plotting x
        out[eta][pt_key]["pt_true"] = float(pt)

    return out, branches

def make_diag_graph_from_summary(name, title, summary_map_eta, branch_name):
    """
    Build a TGraphErrors vs pT from summary_map_eta[pt_key][branch_name].
    """
    gr = ROOT.TGraphErrors()
    gr.SetName(name)
    gr.SetTitle(title)
    gr.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
    gr.GetYaxis().SetTitle(branch_name)
    ROOT.SetOwnership(gr, False)

    # Sort by actual pt_true if present
    pts = []
    for pt_key, rec in summary_map_eta.items():
        pt = rec.get("pt_true", None)
        val = rec.get(branch_name, None)
        if finite(pt) and finite(val):
            pts.append((float(pt), float(val)))
    pts.sort(key=lambda t: t[0])

    for i, (pt, val) in enumerate(pts):
        gr.SetPoint(i, pt, val)
        gr.SetPointError(i, 0.0, 0.0)

    return gr

def make_passfrac_graph(name, title, summary_map_eta):
    """
    passFrac = n_quality/n_usable (only where n_usable>0)
    """
    gr = ROOT.TGraphErrors()
    gr.SetName(name)
    gr.SetTitle(title)
    gr.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
    gr.GetYaxis().SetTitle("passFrac")
    ROOT.SetOwnership(gr, False)

    pts = []
    for pt_key, rec in summary_map_eta.items():
        pt = rec.get("pt_true", None)
        nu = rec.get("n_usable", None)
        nq = rec.get("n_quality", None)
        if not (finite(pt) and finite(nu) and finite(nq)):
            continue
        if nu <= 0:
            continue
        pf = float(nq) / float(nu)
        pts.append((float(pt), float(pf)))
    pts.sort(key=lambda t: t[0])

    for i, (pt, pf) in enumerate(pts):
        gr.SetPoint(i, pt, pf)
        gr.SetPointError(i, 0.0, 0.0)

    return gr

def ratio_from_summary_maps(eta, mA_eta, mB_eta, branch_name, x_round=6):
    """
    Ratio = A/B using summary maps directly (more robust than graph roundtrips).
    Only where both exist and denom != 0.
    """
    gr = ROOT.TGraphErrors()
    gr.SetName(f"gr_ratio_{branch_name}")
    gr.SetTitle(f"{eta} {branch_name} ratio; p_{{T}}^{{true}} [GeV]; {branch_name}({{A}})/{branch_name}({{B}})")
    gr.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
    gr.GetYaxis().SetTitle("ratio")
    ROOT.SetOwnership(gr, False)

    keys = sorted(set(mA_eta.keys()) & set(mB_eta.keys()))
    ip = 0
    for k in keys:
        pt = mA_eta[k].get("pt_true", None)
        a = mA_eta[k].get(branch_name, None)
        b = mB_eta[k].get(branch_name, None)
        if not (finite(pt) and finite(a) and finite(b)):
            continue
        if b == 0.0:
            continue
        gr.SetPoint(ip, float(pt), float(a) / float(b))
        gr.SetPointError(ip, 0.0, 0.0)
        ip += 1

    return gr

def passfrac_ratio_from_summary_maps(eta, mA_eta, mB_eta):
    gr = ROOT.TGraphErrors()
    gr.SetName("gr_ratio_passFrac")
    gr.SetTitle(f"{eta} passFrac ratio; p_{{T}}^{{true}} [GeV]; (nq/nu)_A / (nq/nu)_B")
    gr.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
    gr.GetYaxis().SetTitle("ratio")
    ROOT.SetOwnership(gr, False)

    keys = sorted(set(mA_eta.keys()) & set(mB_eta.keys()))
    ip = 0
    for k in keys:
        pt = mA_eta[k].get("pt_true", None)
        nuA = mA_eta[k].get("n_usable", None)
        nqA = mA_eta[k].get("n_quality", None)
        nuB = mB_eta[k].get("n_usable", None)
        nqB = mB_eta[k].get("n_quality", None)
        if not (finite(pt) and finite(nuA) and finite(nqA) and finite(nuB) and finite(nqB)):
            continue
        if nuA <= 0 or nuB <= 0:
            continue
        pfA = float(nqA) / float(nuA)
        pfB = float(nqB) / float(nuB)
        if pfB == 0.0:
            continue
        gr.SetPoint(ip, float(pt), float(pfA) / float(pfB))
        gr.SetPointError(ip, 0.0, 0.0)
        ip += 1

    return gr


# -----------------------------
# main
# -----------------------------
METHODS = ["rms", "madsigma", "central68", "truncrms68", "meanAbs", "medianAbs"]

# Default diagnostic branches to compare (we'll intersect with what exists in the file)
DEFAULT_DIAG_BRANCHES = [
    "n_usable",
    "n_quality",
    "frac_curvObs",
    "frac_circleOK",
    "frac_timeSrc",
    "med_phiSpan",
    "med_chord",
    "med_cond",
    "med_nhits",
    "med_rmsAlgRes",
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="Input ROOT A (e.g. CF) from analyze_pt_resolution_grid.py")
    ap.add_argument("--b", required=True, help="Input ROOT B (e.g. W) from analyze_pt_resolution_grid.py")
    ap.add_argument("--out", required=True, help="Output ROOT comparison file")
    ap.add_argument("--tagA", default="A", help="Label for A (legend)")
    ap.add_argument("--tagB", default="B", help="Label for B (legend)")
    ap.add_argument("--xRound", type=int, default=6, help="Rounding digits for matching pT points")

    # Representativeness thresholds (simple but effective)
    ap.add_argument("--diagAbsTolPassFrac", type=float, default=0.05,
                    help="Abs tolerance for passFrac difference |pfA-pfB| (flag suspect if exceeded).")
    ap.add_argument("--diagRelTolPassFrac", type=float, default=0.10,
                    help="Rel tolerance for passFrac ratio deviation |pfA/pfB - 1| (flag suspect if exceeded).")
    ap.add_argument("--diagAbsTolFrac", type=float, default=0.05,
                    help="Abs tolerance for frac_* diagnostic differences.")
    ap.add_argument("--diagRelTolMed", type=float, default=0.25,
                    help="Rel tolerance for med_* diagnostic ratios deviation |A/B - 1|.")
    args = ap.parse_args()

    fA = ROOT.TFile.Open(args.a, "READ")
    fB = ROOT.TFile.Open(args.b, "READ")
    if not fA or fA.IsZombie():
        raise RuntimeError(f"Cannot open {args.a}")
    if not fB or fB.IsZombie():
        raise RuntimeError(f"Cannot open {args.b}")
    ROOT.SetOwnership(fA, False)
    ROOT.SetOwnership(fB, False)

    fout = ROOT.TFile.Open(args.out, "RECREATE")
    if not fout or fout.IsZombie():
        raise RuntimeError(f"Cannot create {args.out}")
    ROOT.SetOwnership(fout, False)

    keepalive = []

    top = ensure_dir(fout, ["compare"])
    byEta_out = ensure_dir(top, ["byEta"])
    byMethod_out = ensure_dir(top, ["byMethod"])
    diag_out = ensure_dir(top, ["diagnostics"])
    diag_byEta_out = ensure_dir(diag_out, ["byEta"])

    # ----------------------------------------
    # Collect eta dirs present in either file
    # ----------------------------------------
    etas = set()

    dA = fA.Get("byEta")
    if dA:
        for k in dA.GetListOfKeys():
            etas.add(k.GetName())
    dB = fB.Get("byEta")
    if dB:
        for k in dB.GetListOfKeys():
            etas.add(k.GetName())

    etas = sorted(etas)

    # ----------------------------------------
    # byEta overlays + ratios, per method
    # ----------------------------------------
    for eta in etas:
        eta_dir = ensure_dir(byEta_out, [eta])

        for m in METHODS:
            path = f"byEta/{eta}/gr_{m}"
            gA0 = get_tgraph(fA, path)
            gB0 = get_tgraph(fB, path)

            if (gA0 is None) and (gB0 is None):
                continue

            gA = gA0.Clone(f"{eta}_A_{m}") if gA0 else None
            gB = gB0.Clone(f"{eta}_B_{m}") if gB0 else None
            if gA: ROOT.SetOwnership(gA, False)
            if gB: ROOT.SetOwnership(gB, False)

            if gA: style_graph(gA, 4, 20)  # blue filled circle
            if gB: style_graph(gB, 2, 24)  # red open circle

            mg = ROOT.TMultiGraph()
            mg.SetName(f"mg_{m}")
            mg.SetTitle(f"{eta} {m}; p_{{T}}^{{true}} [GeV]; resolution")
            ROOT.SetOwnership(mg, False)

            leg = ROOT.TLegend(0.12, 0.74, 0.55, 0.88)
            leg.SetName(f"leg_{m}")
            leg.SetBorderSize(0)
            leg.SetFillStyle(0)
            ROOT.SetOwnership(leg, False)

            if gA:
                mg.Add(gA, "P")
                leg.AddEntry(gA, args.tagA, "p")
            if gB:
                mg.Add(gB, "P")
                leg.AddEntry(gB, args.tagB, "p")

            c = make_canvas(f"c_{m}_loglog", f"{eta} {m} {args.tagA} vs {args.tagB}")
            c.SetLogx(1)
            c.SetLogy(1)

            ymin, ymax = multigraph_minmax_positive([gA, gB])
            if finite(ymin) and ymin > 0 and finite(ymax) and ymax > 0:
                mg.SetMinimum(ymin * 0.7)
                mg.SetMaximum(ymax * 1.4)
            else:
                mg.SetMinimum(1e-6)
                mg.SetMaximum(1.0)

            mg.Draw("A")
            mg.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
            mg.GetYaxis().SetTitle("resolution")
            leg.Draw()

            grR = make_ratio_graph(
                name=f"gr_ratio_{m}",
                title=f"{eta} {m} ratio {args.tagA}/{args.tagB}; p_{{T}}^{{true}} [GeV]; ratio",
                gA=gA0, gB=gB0, x_round=args.xRound
            )
            if grR:
                style_graph(grR, 1, 21)  # black triangles
                cR = make_canvas(f"c_ratio_{m}_logx", f"{eta} ratio {m} {args.tagA}/{args.tagB}")
                cR.SetLogx(1)
                cR.SetLogy(0)
                grR.Draw("AP")
                grR.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
                grR.GetYaxis().SetTitle(f"{args.tagA}/{args.tagB}")

                write_obj(eta_dir, grR)
                write_obj(eta_dir, cR)
                keepalive += [grR, cR]

            write_obj(eta_dir, mg)
            write_obj(eta_dir, leg)
            write_obj(eta_dir, c)
            if gA: write_obj(eta_dir, gA, f"{args.tagA}_{m}")
            if gB: write_obj(eta_dir, gB, f"{args.tagB}_{m}")

            keepalive += [mg, leg, c]
            if gA: keepalive.append(gA)
            if gB: keepalive.append(gB)

    # ----------------------------------------
    # byMethod overlays
    # ----------------------------------------
    eta_colors = {}
    palette = [1, 2, 4, 6, 8, 9, 46, 38, 28, 32]
    for i, eta in enumerate(etas):
        eta_colors[eta] = palette[i % len(palette)]

    for m in METHODS:
        mdir = ensure_dir(byMethod_out, [m])

        mg_all = ROOT.TMultiGraph()
        mg_all.SetName("mg_etas_compare")
        mg_all.SetTitle(f"{m} all etas: {args.tagA} vs {args.tagB}; p_{{T}}^{{true}} [GeV]; resolution")
        ROOT.SetOwnership(mg_all, False)

        leg_all = ROOT.TLegend(0.12, 0.60, 0.62, 0.88)
        leg_all.SetName("leg_etas_compare")
        leg_all.SetBorderSize(0)
        leg_all.SetFillStyle(0)
        leg_all.SetNColumns(2)
        ROOT.SetOwnership(leg_all, False)

        graphs_added = []

        for eta in etas:
            path = f"byEta/{eta}/gr_{m}"
            gA0 = get_tgraph(fA, path)
            gB0 = get_tgraph(fB, path)

            if gA0:
                gA = gA0.Clone(f"{eta}_{m}_{args.tagA}")
                ROOT.SetOwnership(gA, False)
                style_graph(gA, eta_colors[eta], 20)  # filled
                mg_all.Add(gA, "P")
                leg_all.AddEntry(gA, f"{eta} {args.tagA}", "p")
                graphs_added.append(gA)

            if gB0:
                gB = gB0.Clone(f"{eta}_{m}_{args.tagB}")
                ROOT.SetOwnership(gB, False)
                style_graph(gB, eta_colors[eta], 24)  # open
                mg_all.Add(gB, "P")
                leg_all.AddEntry(gB, f"{eta} {args.tagB}", "p")
                graphs_added.append(gB)

        c_all = make_canvas("c_etas_compare_loglog", f"{m} all etas compare")
        c_all.SetLogx(1)
        c_all.SetLogy(1)

        ymin, ymax = multigraph_minmax_positive(graphs_added)
        if finite(ymin) and ymin > 0 and finite(ymax) and ymax > 0:
            mg_all.SetMinimum(ymin * 0.7)
            mg_all.SetMaximum(ymax * 1.4)
        else:
            mg_all.SetMinimum(1e-6)
            mg_all.SetMaximum(1.0)

        mg_all.Draw("A")
        mg_all.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
        mg_all.GetYaxis().SetTitle("resolution")
        leg_all.Draw()

        write_obj(mdir, mg_all)
        write_obj(mdir, leg_all)
        write_obj(mdir, c_all)
        keepalive += [mg_all, leg_all, c_all] + graphs_added

        per_eta_dir = ensure_dir(mdir, ["perEta"])
        for eta in etas:
            sub = ensure_dir(per_eta_dir, [eta])

            path = f"byEta/{eta}/gr_{m}"
            gA0 = get_tgraph(fA, path)
            gB0 = get_tgraph(fB, path)
            if (gA0 is None) and (gB0 is None):
                continue

            gA = gA0.Clone(f"{eta}_{m}_A") if gA0 else None
            gB = gB0.Clone(f"{eta}_{m}_B") if gB0 else None
            if gA: ROOT.SetOwnership(gA, False)
            if gB: ROOT.SetOwnership(gB, False)

            if gA: style_graph(gA, 4, 20)
            if gB: style_graph(gB, 2, 24)

            mg = ROOT.TMultiGraph()
            mg.SetName("mg_compare")
            mg.SetTitle(f"{eta} {m}: {args.tagA} vs {args.tagB}; p_{{T}}^{{true}} [GeV]; resolution")
            ROOT.SetOwnership(mg, False)

            leg = ROOT.TLegend(0.12, 0.74, 0.55, 0.88)
            leg.SetName("leg_compare")
            leg.SetBorderSize(0)
            leg.SetFillStyle(0)
            ROOT.SetOwnership(leg, False)

            if gA:
                mg.Add(gA, "P")
                leg.AddEntry(gA, args.tagA, "p")
            if gB:
                mg.Add(gB, "P")
                leg.AddEntry(gB, args.tagB, "p")

            c = make_canvas("c_compare_loglog", f"{eta} {m} compare")
            c.SetLogx(1)
            c.SetLogy(1)

            ymin, ymax = multigraph_minmax_positive([gA, gB])
            if finite(ymin) and ymin > 0 and finite(ymax) and ymax > 0:
                mg.SetMinimum(ymin * 0.7)
                mg.SetMaximum(ymax * 1.4)
            else:
                mg.SetMinimum(1e-6)
                mg.SetMaximum(1.0)

            mg.Draw("A")
            mg.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
            mg.GetYaxis().SetTitle("resolution")
            leg.Draw()

            grR = make_ratio_graph(
                name="gr_ratio",
                title=f"{eta} {m} ratio {args.tagA}/{args.tagB}; p_{{T}}^{{true}} [GeV]; ratio",
                gA=gA0, gB=gB0, x_round=args.xRound
            )
            if grR:
                style_graph(grR, 1, 21)
                cR = make_canvas("c_ratio_logx", f"{eta} {m} ratio")
                cR.SetLogx(1)
                cR.SetLogy(0)
                grR.Draw("AP")
                grR.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
                grR.GetYaxis().SetTitle(f"{args.tagA}/{args.tagB}")
                write_obj(sub, grR)
                write_obj(sub, cR)
                keepalive += [grR, cR]

            write_obj(sub, mg)
            write_obj(sub, leg)
            write_obj(sub, c)
            if gA: write_obj(sub, gA, f"{args.tagA}")
            if gB: write_obj(sub, gB, f"{args.tagB}")

            keepalive += [mg, leg, c]
            if gA: keepalive.append(gA)
            if gB: keepalive.append(gB)

    # =========================================================================
    # Diagnostics compare from summary TTree (representativeness checks)
    # =========================================================================
    sumA, branchesA = read_summary_map(fA, x_round=args.xRound)
    sumB, branchesB = read_summary_map(fB, x_round=args.xRound)

    # Determine which diagnostic branches we can compare
    all_branches = set(branchesA) & set(branchesB)
    diag_branches = [b for b in DEFAULT_DIAG_BRANCHES if b in all_branches]
    # Always add passFrac derived
    if not diag_branches:
        # Still write a note so you notice
        tn = ROOT.TNamed("diagnostics_note", "No common diagnostic branches found in summary trees; diagnostics compare skipped.")
        write_obj(diag_out, tn)
    else:
        # Make a TTree with per-point diagnostics and a simple suspect flag
        diag_tree = ROOT.TTree("diag_compare", "Per-(eta,pt) diagnostics A vs B + diffs/ratios + suspect flag")
        ROOT.SetOwnership(diag_tree, False)

        # Branch buffers
        eta_buf = ROOT.std.string()
        pt_true = ctypes.c_double(0.0)

        # core
        nuA = ctypes.c_double(float("nan"))
        nqA = ctypes.c_double(float("nan"))
        nuB = ctypes.c_double(float("nan"))
        nqB = ctypes.c_double(float("nan"))
        pfA = ctypes.c_double(float("nan"))
        pfB = ctypes.c_double(float("nan"))
        pf_diff = ctypes.c_double(float("nan"))
        pf_ratio = ctypes.c_double(float("nan"))

        suspect = ctypes.c_int(0)

        diag_tree.Branch("eta", eta_buf)
        diag_tree.Branch("pt_true", pt_true, "pt_true/D")
        diag_tree.Branch("n_usable_A", nuA, "n_usable_A/D")
        diag_tree.Branch("n_quality_A", nqA, "n_quality_A/D")
        diag_tree.Branch("n_usable_B", nuB, "n_usable_B/D")
        diag_tree.Branch("n_quality_B", nqB, "n_quality_B/D")
        diag_tree.Branch("passFrac_A", pfA, "passFrac_A/D")
        diag_tree.Branch("passFrac_B", pfB, "passFrac_B/D")
        diag_tree.Branch("passFrac_diff", pf_diff, "passFrac_diff/D")
        diag_tree.Branch("passFrac_ratio", pf_ratio, "passFrac_ratio/D")
        diag_tree.Branch("suspect", suspect, "suspect/I")

        # Add per-diag numeric branches (A,B,diff,ratio)
        diag_buffers = {}
        for bn in diag_branches:
            if bn in ("n_usable", "n_quality"):
                continue
            a = ctypes.c_double(float("nan"))
            b = ctypes.c_double(float("nan"))
            d = ctypes.c_double(float("nan"))
            r = ctypes.c_double(float("nan"))
            diag_buffers[bn] = (a, b, d, r)
            diag_tree.Branch(f"{bn}_A", a, f"{bn}_A/D")
            diag_tree.Branch(f"{bn}_B", b, f"{bn}_B/D")
            diag_tree.Branch(f"{bn}_diff", d, f"{bn}_diff/D")
            diag_tree.Branch(f"{bn}_ratio", r, f"{bn}_ratio/D")

        # Write diagnostic plots per eta
        etas_diag = sorted(set(sumA.keys()) | set(sumB.keys()))
        diag_summary_note = ROOT.TNamed(
            "diagnostics_compared_branches",
            "Compared diagnostic branches from summary tree:\n  " + "\n  ".join(diag_branches + ["passFrac(n_quality/n_usable)"])
        )
        write_obj(diag_out, diag_summary_note)

        for eta in etas_diag:
            etaD = ensure_dir(diag_byEta_out, [eta])

            mA_eta = sumA.get(eta, {})
            mB_eta = sumB.get(eta, {})

            # Build + write pass fraction overlays
            g_pfA = make_passfrac_graph(f"gr_passFrac_{args.tagA}", f"{eta} passFrac {args.tagA}; pT [GeV]; n_quality/n_usable", mA_eta) if mA_eta else None
            g_pfB = make_passfrac_graph(f"gr_passFrac_{args.tagB}", f"{eta} passFrac {args.tagB}; pT [GeV]; n_quality/n_usable", mB_eta) if mB_eta else None
            if g_pfA: style_graph(g_pfA, 4, 20)
            if g_pfB: style_graph(g_pfB, 2, 24)

            if g_pfA or g_pfB:
                mgpf = ROOT.TMultiGraph()
                mgpf.SetName("mg_passFrac")
                mgpf.SetTitle(f"{eta} passFrac; p_{{T}}^{{true}} [GeV]; n_quality/n_usable")
                ROOT.SetOwnership(mgpf, False)

                legpf = ROOT.TLegend(0.12, 0.74, 0.55, 0.88)
                legpf.SetName("leg_passFrac")
                legpf.SetBorderSize(0)
                legpf.SetFillStyle(0)
                ROOT.SetOwnership(legpf, False)

                if g_pfA:
                    mgpf.Add(g_pfA, "P")
                    legpf.AddEntry(g_pfA, args.tagA, "p")
                if g_pfB:
                    mgpf.Add(g_pfB, "P")
                    legpf.AddEntry(g_pfB, args.tagB, "p")

                c_pf = make_canvas("c_passFrac_logx", f"{eta} passFrac compare")
                c_pf.SetLogx(1)
                c_pf.SetLogy(0)
                mgpf.Draw("A")
                mgpf.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
                mgpf.GetYaxis().SetTitle("n_quality/n_usable")
                legpf.Draw()

                # ratio passFrac
                gr_pfR = passfrac_ratio_from_summary_maps(eta, mA_eta, mB_eta) if (mA_eta and mB_eta) else None
                if gr_pfR and gr_pfR.GetN() > 0:
                    style_graph(gr_pfR, 1, 21)
                    c_pfR = make_canvas("c_passFrac_ratio_logx", f"{eta} passFrac ratio")
                    c_pfR.SetLogx(1)
                    c_pfR.SetLogy(0)
                    gr_pfR.Draw("AP")
                    gr_pfR.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
                    gr_pfR.GetYaxis().SetTitle(f"{args.tagA}/{args.tagB}")

                    write_obj(etaD, gr_pfR)
                    write_obj(etaD, c_pfR)
                    keepalive += [gr_pfR, c_pfR]

                write_obj(etaD, mgpf)
                write_obj(etaD, legpf)
                write_obj(etaD, c_pf)
                if g_pfA: write_obj(etaD, g_pfA)
                if g_pfB: write_obj(etaD, g_pfB)
                keepalive += [mgpf, legpf, c_pf]
                if g_pfA: keepalive.append(g_pfA)
                if g_pfB: keepalive.append(g_pfB)

            # Now compare each diagnostic branch (including n_usable/n_quality as normal numeric graphs)
            for bn in diag_branches:
                gA_bn = make_diag_graph_from_summary(f"gr_{bn}_{args.tagA}", f"{eta} {bn} {args.tagA}; pT [GeV]; {bn}", mA_eta, bn) if mA_eta else None
                gB_bn = make_diag_graph_from_summary(f"gr_{bn}_{args.tagB}", f"{eta} {bn} {args.tagB}; pT [GeV]; {bn}", mB_eta, bn) if mB_eta else None
                if gA_bn: style_graph(gA_bn, 4, 20)
                if gB_bn: style_graph(gB_bn, 2, 24)

                if not (gA_bn or gB_bn):
                    continue

                mg = ROOT.TMultiGraph()
                mg.SetName(f"mg_{bn}")
                mg.SetTitle(f"{eta} {bn}; p_{{T}}^{{true}} [GeV]; {bn}")
                ROOT.SetOwnership(mg, False)

                leg = ROOT.TLegend(0.12, 0.74, 0.55, 0.88)
                leg.SetName(f"leg_{bn}")
                leg.SetBorderSize(0)
                leg.SetFillStyle(0)
                ROOT.SetOwnership(leg, False)

                if gA_bn:
                    mg.Add(gA_bn, "P")
                    leg.AddEntry(gA_bn, args.tagA, "p")
                if gB_bn:
                    mg.Add(gB_bn, "P")
                    leg.AddEntry(gB_bn, args.tagB, "p")

                c = make_canvas(f"c_{bn}_logx", f"{eta} {bn} compare")
                c.SetLogx(1)
                c.SetLogy(0)

                mg.Draw("A")
                mg.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
                mg.GetYaxis().SetTitle(bn)
                leg.Draw()

                write_obj(etaD, mg)
                write_obj(etaD, leg)
                write_obj(etaD, c)
                if gA_bn: write_obj(etaD, gA_bn)
                if gB_bn: write_obj(etaD, gB_bn)
                keepalive += [mg, leg, c]
                if gA_bn: keepalive.append(gA_bn)
                if gB_bn: keepalive.append(gB_bn)

                # ratio (A/B) from summary maps
                if mA_eta and mB_eta:
                    grR = ratio_from_summary_maps(eta, mA_eta, mB_eta, bn, x_round=args.xRound)
                    if grR and grR.GetN() > 0:
                        style_graph(grR, 1, 21)
                        cR = make_canvas(f"c_ratio_{bn}_logx", f"{eta} {bn} ratio")
                        cR.SetLogx(1)
                        cR.SetLogy(0)
                        grR.Draw("AP")
                        grR.GetXaxis().SetTitle("p_{T}^{true} [GeV]")
                        grR.GetYaxis().SetTitle(f"{args.tagA}/{args.tagB}")
                        write_obj(etaD, grR)
                        write_obj(etaD, cR)
                        keepalive += [grR, cR]

        # Fill diag_compare tree with flags
        # Iterate over common keys per eta
        for eta in sorted(set(sumA.keys()) & set(sumB.keys())):
            mA_eta = sumA.get(eta, {})
            mB_eta = sumB.get(eta, {})
            common_keys = sorted(set(mA_eta.keys()) & set(mB_eta.keys()))
            for k in common_keys:
                recA = mA_eta[k]
                recB = mB_eta[k]

                pt = recA.get("pt_true", None)
                if not finite(pt):
                    continue

                eta_buf.assign(eta)
                pt_true.value = float(pt)

                # core counts
                _nuA = recA.get("n_usable", float("nan"))
                _nqA = recA.get("n_quality", float("nan"))
                _nuB = recB.get("n_usable", float("nan"))
                _nqB = recB.get("n_quality", float("nan"))
                nuA.value = float(_nuA) if finite(_nuA) else float("nan")
                nqA.value = float(_nqA) if finite(_nqA) else float("nan")
                nuB.value = float(_nuB) if finite(_nuB) else float("nan")
                nqB.value = float(_nqB) if finite(_nqB) else float("nan")

                _pfA = float("nan")
                _pfB = float("nan")
                if finite(_nuA) and finite(_nqA) and _nuA > 0:
                    _pfA = float(_nqA) / float(_nuA)
                if finite(_nuB) and finite(_nqB) and _nuB > 0:
                    _pfB = float(_nqB) / float(_nuB)

                pfA.value = float(_pfA) if finite(_pfA) else float("nan")
                pfB.value = float(_pfB) if finite(_pfB) else float("nan")
                pf_diff.value = float(_pfA - _pfB) if (finite(_pfA) and finite(_pfB)) else float("nan")
                pf_ratio.value = float(_pfA / _pfB) if (finite(_pfA) and finite(_pfB) and _pfB != 0.0) else float("nan")

                # Fill diag buffers
                for bn in diag_buffers:
                    a_buf, b_buf, d_buf, r_buf = diag_buffers[bn]
                    a = recA.get(bn, float("nan"))
                    b = recB.get(bn, float("nan"))
                    a_buf.value = float(a) if finite(a) else float("nan")
                    b_buf.value = float(b) if finite(b) else float("nan")
                    d_buf.value = float(a - b) if (finite(a) and finite(b)) else float("nan")
                    r_buf.value = float(a / b) if (finite(a) and finite(b) and b != 0.0) else float("nan")

                # Suspect logic:
                #  - passFrac differs "too much" (abs or rel)
                #  - frac_* differs too much (abs)
                #  - med_* differs too much (rel ratio deviation)
                sus = 0

                if finite(_pfA) and finite(_pfB):
                    if abs(_pfA - _pfB) > args.diagAbsTolPassFrac:
                        sus = 1
                    if _pfB != 0.0 and abs((_pfA / _pfB) - 1.0) > args.diagRelTolPassFrac:
                        sus = 1

                for bn in diag_buffers:
                    a = recA.get(bn, None)
                    b = recB.get(bn, None)
                    if not (finite(a) and finite(b)):
                        continue
                    if bn.startswith("frac_"):
                        if abs(a - b) > args.diagAbsTolFrac:
                            sus = 1
                    if bn.startswith("med_"):
                        if b != 0.0 and abs((a / b) - 1.0) > args.diagRelTolMed:
                            sus = 1

                suspect.value = int(sus)
                diag_tree.Fill()

        write_obj(diag_out, diag_tree)

        # Add a quick text summary as TNamed (counts of suspect points)
        n_sus = 0
        n_all = diag_tree.GetEntries()
        for i in range(n_all):
            diag_tree.GetEntry(i)
            if int(getattr(diag_tree, "suspect")) == 1:
                n_sus += 1
        frac = (float(n_sus) / float(n_all)) if n_all > 0 else float("nan")
        summ = ROOT.TNamed("diagnostics_suspect_summary",
                           f"suspect_points={n_sus} / total_points={n_all}  (fraction={frac:.4g})\n"
                           f"Thresholds: passFrac abs>{args.diagAbsTolPassFrac}, passFrac rel>{args.diagRelTolPassFrac}, "
                           f"frac_* abs>{args.diagAbsTolFrac}, med_* rel>{args.diagRelTolMed}")
        write_obj(diag_out, summ)

    fout.Close()
    fA.Close()
    fB.Close()
    print(f"[ok] wrote {args.out}")

if __name__ == "__main__":
    main()
