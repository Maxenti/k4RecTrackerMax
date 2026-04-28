#!/usr/bin/env python3
"""
DOC
Summary: Patch Delphes TrackCovariance cards so DCH DetectorGeometry X0 values reproduce Geant4 DCH material-budget x/X0 versus |eta| for CF and W variants.
Status: secondary
Usage:
  python3 scripts/patch_trkCov_match_dch_material.py --base-card BASE.tcl --g4-cf CF.root --g4-w W.root --outdir OUTDIR --npart 12 --hist hMatVsAbsEta_total
Examples:
  python3 scripts/patch_trkCov_match_dch_material.py \
    --base-card configs/delphes/delphes_card_IDEAtrkCov.tcl \
    --g4-cf /eos/.../output_eta_folded_CF_E15000MeV.root \
    --g4-w  /eos/.../output_eta_folded_W_E15000MeV.root \
    --outdir configs/delphes/generated \
    --npart 12 \
    --hist hMatVsAbsEta_total \
    --tag IDEA_DCH
Inputs: Base Delphes Tcl card containing module TrackCovariance TrackSmearing with a DetectorGeometry block; Geant4 material-budget ROOT files for CF and W variants; optional histogram name.
Outputs: Two patched Delphes Tcl cards, <tag>_CF.tcl and <tag>_W.tcl, with DCH X0 columns adjusted by radial partition.
Collections: None; reads ROOT material-budget histograms and edits Delphes Tcl card geometry lines.
Connects-To: configs/delphes/*.tcl, scripts/dch_x0_per_layer.py, material-budget closeout ROOT outputs, Delphes TrackCovariance studies
Arguments:
  --base-card: input Delphes Tcl card to patch.
  --g4-cf: Geant4/material-budget ROOT file for the CF detector/material variant.
  --g4-w: Geant4/material-budget ROOT file for the W/default-like detector/material variant.
  --outdir: output directory for patched Tcl cards.
  --npart: number of contiguous radial DCH layer partitions used in the X0 fit; default 12.
  --hist: histogram name to read from each ROOT file; if omitted, the script tries to auto-pick an eta/x0/radlen-like TH1.
  --tag: output card basename prefix; default IDEA_DCH.
Notes:
  This script patches only the X0 column of existing "1 DCH ..." DetectorGeometry lines.
  It does not slice in z, does not duplicate DCH geometry lines, and does not change zmin/zmax/radius/thickness values.
  The fitted model approximates x/X0(|eta|) as cosh(|eta|) times the sum over crossed DCH layer thicknesses divided by effective partition X0.
  A layer is considered crossed when r_i*sinh(|eta|) < zmax_i.
  The fitted parameters are one effective X0 per contiguous radial partition, then each DCH line inherits the X0 value of its partition.
  Use DCH-only or appropriately isolated material-budget histograms; fitting total-detector material can incorrectly absorb non-DCH material into DCH X0.
  The output cards are generated artifacts and should be reviewed before being treated as maintained Delphes configs.
  This is a fastsim/material-matching helper and does not replace DD4hep/Geant4 material-budget validation.
Tags: secondary, delphes, track-covariance, material-budget, dch, x0, geant4, cf-vs-w, tcl, fastsim

NOTE:
  Do NOT use --fit-cans for DCH-only Geant4 files.

DOC_END
"""



import argparse, os, re
import numpy as np

# -----------------------------
# ROOT histogram reading
# -----------------------------
def _read_hist_root(filename, hist_name=None):
    try:
        import uproot
        with uproot.open(filename) as f:
            keys = [k.split(";")[0] for k in f.keys()]
            pick = hist_name
            if pick is None:
                ranked = []
                for k in keys:
                    kl = k.lower()
                    score = 0
                    if "eta" in kl: score += 2
                    if "abseta" in kl or "abs" in kl: score += 2
                    if "x0" in kl or "radlen" in kl or "xoverx0" in kl: score += 3
                    if "total" in kl: score += 1
                    ranked.append((score, k))
                ranked.sort(reverse=True)
                pick = ranked[0][1] if ranked and ranked[0][0] > 0 else None
            if pick is None:
                raise RuntimeError(f"Could not auto-pick TH1 in {filename}. Keys: {keys[:50]}")
            h = f[pick]
            vals = h.values().astype(float)
            edges = h.axis().edges().astype(float)
            centers = 0.5*(edges[:-1] + edges[1:])
            return np.abs(centers), vals, pick
    except Exception as e:
        # PyROOT fallback
        import ROOT
        ROOT.gROOT.SetBatch(True)
        tf = ROOT.TFile.Open(filename, "READ")
        if not tf or tf.IsZombie():
            raise RuntimeError(f"Failed to open ROOT file: {filename}")
        if hist_name is None:
            keys = [k.GetName() for k in tf.GetListOfKeys()]
            ranked = []
            for k in keys:
                kl = k.lower()
                score = 0
                if "eta" in kl: score += 2
                if "abseta" in kl or "abs" in kl: score += 2
                if "x0" in kl or "radlen" in kl or "xoverx0" in kl: score += 3
                if "total" in kl: score += 1
                ranked.append((score, k))
            ranked.sort(reverse=True)
            hist_name = ranked[0][1] if ranked and ranked[0][0] > 0 else None
        if hist_name is None:
            raise RuntimeError(f"Could not auto-pick TH1 in {filename}")
        h = tf.Get(hist_name)
        if not h:
            raise RuntimeError(f"Histogram '{hist_name}' not found in {filename}")
        n = h.GetNbinsX()
        centers_abs = np.array([abs(h.GetXaxis().GetBinCenter(i)) for i in range(1, n+1)], dtype=float)
        y = np.array([h.GetBinContent(i) for i in range(1, n+1)], dtype=float)
        tf.Close()
        return centers_abs, y, hist_name

# -----------------------------
# Card parsing
# -----------------------------
def _extract_detector_geometry_block(card_text):
    m = re.search(r"module\s+TrackCovariance\s+TrackSmearing\s*\{", card_text)
    if not m:
        raise RuntimeError("Could not find: module TrackCovariance TrackSmearing {")
    start = m.start()

    m2 = re.search(r"set\s+DetectorGeometry\s*\{", card_text[start:])
    if not m2:
        raise RuntimeError("Could not find: set DetectorGeometry { inside TrackSmearing module")
    dg_start = start + m2.end()

    i = dg_start
    depth = 1
    while i < len(card_text) and depth > 0:
        if card_text[i] == "{":
            depth += 1
        elif card_text[i] == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise RuntimeError("Unbalanced braces while parsing DetectorGeometry block")
    dg_end = i - 1

    return card_text[:dg_start], card_text[dg_start:dg_end], card_text[dg_end:]

def _parse_geom_lines(geom_block):
    out = []
    for ln in geom_block.splitlines():
        raw = ln.rstrip("\n")
        s = raw.strip()
        if not s:
            out.append(("blank", raw, None))
        elif s.startswith("#"):
            out.append(("comment", raw, None))
        else:
            out.append(("data", raw, s.split()))
    return out

def _is_dch(toks):
    return len(toks) >= 13 and toks[0] == "1" and toks[1] == "DCH"

def _format_float(x):
    if x is None or (isinstance(x, float) and (not np.isfinite(x))):
        return None
    x = float(x)
    ax = abs(x)
    if ax == 0:
        return "0"
    if ax < 1e-3 or ax > 1e4:
        return f"{x:.6e}"
    return f"{x:.6g}"

# -----------------------------
# Fit X0 per radial partition
# -----------------------------
def _fit_partitions(eta_abs, y, dch_layers, npart):
    eta = np.array(eta_abs, dtype=float)
    y = np.array(y, dtype=float)
    m = np.isfinite(eta) & np.isfinite(y) & (y >= 0)
    eta, y = eta[m], y[m]

    # layer info from card tokens:
    # 1 DCH zmin zmax r w X0 ...
    r = np.array([float(t[4]) for t in dch_layers], dtype=float)
    zmax = np.array([max(abs(float(t[2])), abs(float(t[3]))) for t in dch_layers], dtype=float)
    w = np.array([float(t[5]) for t in dch_layers], dtype=float)

    nlay = len(dch_layers)
    edges = np.linspace(0, nlay, npart + 1).astype(int)
    part_ids = np.zeros(nlay, dtype=int)
    for p in range(npart):
        part_ids[edges[p]:edges[p+1]] = p

    cosh = np.cosh(eta)
    sinh = np.sinh(eta)

    cols = []
    for p in range(npart):
        idx = np.where(part_ids == p)[0]
        crossed = (r[idx][None, :] * sinh[:, None] < zmax[idx][None, :]).astype(float)
        # sum thicknesses of crossed layers in that partition
        sum_w = (crossed * w[idx][None, :]).sum(axis=1)
        cols.append(cosh * sum_w)

    A = np.stack(cols, axis=1)  # y ~ A @ u, where u_p = 1/X0_p
    u_hat, *_ = np.linalg.lstsq(A, y, rcond=None)

    # convert to X0 per partition using X0 = 1/u
    X0_parts = []
    for u in u_hat:
        if np.isfinite(u) and u > 0:
            X0_parts.append(1.0 / u)
        else:
            X0_parts.append(None)

    yhat = A @ np.nan_to_num(u_hat, nan=0.0)
    return {
        "X0_parts": X0_parts,
        "part_ids": part_ids,
        "eta": eta,
        "y": y,
        "yhat": yhat,
    }

def _apply_X0_parts(parsed, fit):
    X0_parts = fit["X0_parts"]
    part_ids = fit["part_ids"]

    dch_idx = 0
    new_lines = []
    for kind, raw, toks in parsed:
        if kind != "data":
            new_lines.append(raw)
            continue
        if _is_dch(toks):
            p = int(part_ids[dch_idx])
            x0 = X0_parts[p]
            sx0 = _format_float(x0)
            if sx0 is None:
                new_lines.append(raw)  # fallback: keep original
            else:
                toks2 = toks[:]
                toks2[6] = sx0
                new_lines.append("      " + " ".join(toks2))
            dch_idx += 1
        else:
            new_lines.append(raw)
    return "\n".join(new_lines) + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-card", required=True)
    ap.add_argument("--g4-cf", required=True)
    ap.add_argument("--g4-w", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--npart", type=int, default=12)
    ap.add_argument("--hist", default=None)
    ap.add_argument("--tag", default="IDEA_DCH")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    base = open(args.base_card, "r", encoding="utf-8").read()
    prefix, geom_block, suffix = _extract_detector_geometry_block(base)
    parsed = _parse_geom_lines(geom_block)

    dch_layers = [toks for kind, raw, toks in parsed if kind == "data" and _is_dch(toks)]
    if not dch_layers:
        raise RuntimeError("No '1 DCH ...' lines found in DetectorGeometry block")

    def build(label, g4file):
        eta_abs, y, picked = _read_hist_root(g4file, args.hist)
        fit = _fit_partitions(eta_abs, y, dch_layers, args.npart)
        new_geom = _apply_X0_parts(parsed, fit)
        out_text = prefix + new_geom + suffix

        out_card = os.path.join(args.outdir, f"{args.tag}_{label}.tcl")
        with open(out_card, "w", encoding="utf-8") as f:
            f.write(out_text)

        resid = fit["y"] - fit["yhat"]
        rms = float(np.sqrt(np.mean(resid**2))) if len(resid) else float("nan")
        print(f"[{label}] hist='{picked}' npart={args.npart} fit_rms={rms:.6g}")
        print(f"[{label}] wrote: {out_card}")

    build("CF", args.g4_cf)
    build("W", args.g4_w)

if __name__ == "__main__":
    main()
