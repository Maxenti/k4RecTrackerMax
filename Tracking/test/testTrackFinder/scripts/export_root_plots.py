# DOC:
# Summary: Recursively export plottable ROOT objects from analysis/comparison ROOT files to PNG and PDF while preserving the ROOT directory structure.
# Status: authoritative
# Usage:
#   python3 scripts/export_root_plots.py --input INPUT.root --outdir OUTDIR
#   python3 scripts/export_root_plots.py --input INPUT.root --outdir OUTDIR --logy --logz --width 1200 --height 900
# Examples:
#   python3 scripts/export_root_plots.py \
#     --input /eos/.../compare_CF_vs_W.root \
#     --outdir artifacts/analysis/compare_CF_vs_W_plots \
#     --logy
# Inputs: ROOT file containing canvases, histograms, profiles, graphs, multigraphs, efficiencies, stacks, or other drawable ROOT objects.
# Outputs: PNG and PDF files for each rendered object, written under OUTDIR with subdirectories mirroring the input ROOT directory layout.
# Collections: None; reads ROOT analysis objects rather than EDM4hep collections. TTree and TNtuple objects are intentionally skipped.
# Connects-To: scripts/analyze_pt_resolution_grid.py, scripts/compare_pt_resolution_grid.py, scripts/summarize_ptres_improvement.py, artifacts/analysis/
# Arguments:
#   --input: input ROOT file to export.
#   --outdir: output directory for exported PNG/PDF plots.
#   --logy: enable log-y drawing for supported 1D histograms, graphs, multigraphs, profiles, and stacks.
#   --logz: enable log-z drawing for supported 2D histograms and 2D profiles.
#   --width: canvas width in pixels for newly rendered objects; default 1000.
#   --height: canvas height in pixels for newly rendered objects; default 800.
# Notes:
#   Existing TCanvas objects are saved directly; other supported objects are drawn on a fresh batch-mode canvas.
#   The script supports TH1/TH2/TH3, TProfile/TProfile2D/TProfile3D, TGraph, TMultiGraph, TEfficiency, THStack, and generic objects with a Draw method.
#   TTree and TNtuple objects are skipped because they are data containers, not directly meaningful static plots.
#   Output filenames are sanitized from ROOT object names to avoid filesystem-problematic characters.
#   Use this after pT-resolution analysis or CF-vs-W comparison ROOT production to create reviewable closeout plot directories.
#   Generated PNG/PDF outputs should live under artifacts/analysis/ or another generated-output area, not active source directories.
# Tags: authoritative, plotting, root, export, png, pdf, analysis, closeout
# DOC_END

#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import ROOT


def sanitize_name(name: str) -> str:
    """
    Make a ROOT object name safe for filesystem output.
    """
    name = name.strip()
    if not name:
        name = "unnamed"
    name = re.sub(r"[\\/:\*\?\"<>\|\s]+", "_", name)
    return name


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def class_name(obj) -> str:
    try:
        return obj.ClassName()
    except Exception:
        return type(obj).__name__


def is_directory(obj) -> bool:
    return obj.InheritsFrom("TDirectory")


def is_canvas(obj) -> bool:
    return obj.InheritsFrom("TCanvas")


def is_hist1(obj) -> bool:
    return obj.InheritsFrom("TH1") and not obj.InheritsFrom("TH2") and not obj.InheritsFrom("TH3")


def is_hist2(obj) -> bool:
    return obj.InheritsFrom("TH2") and not obj.InheritsFrom("TH3")


def is_hist3(obj) -> bool:
    return obj.InheritsFrom("TH3")


def is_profile(obj) -> bool:
    return obj.InheritsFrom("TProfile") or obj.InheritsFrom("TProfile2D") or obj.InheritsFrom("TProfile3D")


def is_graph(obj) -> bool:
    return obj.InheritsFrom("TGraph") and not obj.InheritsFrom("TMultiGraph")


def is_multigraph(obj) -> bool:
    return obj.InheritsFrom("TMultiGraph")


def is_efficiency(obj) -> bool:
    return obj.InheritsFrom("TEfficiency")


def is_stack(obj) -> bool:
    return obj.InheritsFrom("THStack")


def is_skippable(obj) -> bool:
    """
    Objects we do not try to render directly.
    """
    if obj.InheritsFrom("TTree"):
        return True
    if obj.InheritsFrom("TNtuple"):
        return True
    return False


def draw_object(obj, canvas: ROOT.TCanvas, logy: bool = False, logz: bool = False) -> bool:
    """
    Draw a supported ROOT object onto the given canvas.
    Returns True if it was drawn, False otherwise.
    """
    canvas.cd()
    canvas.Clear()
    canvas.SetLogy(False)
    canvas.SetLogz(False)

    try:
        if is_canvas(obj):
            # Save the canvas contents directly elsewhere; caller handles that.
            return True

        if is_hist2(obj):
            if logz:
                canvas.SetLogz(True)
            obj.SetStats(False)
            obj.Draw("COLZ")
            return True

        if is_hist3(obj):
            # Reasonable generic choice; 3D hist rendering is always somewhat ad hoc.
            obj.SetStats(False)
            obj.Draw("BOX2")
            return True

        if is_profile(obj):
            obj.SetStats(False)
            if obj.InheritsFrom("TProfile2D"):
                if logz:
                    canvas.SetLogz(True)
                obj.Draw("COLZ")
            else:
                if logy:
                    canvas.SetLogy(True)
                obj.Draw("E")
            return True

        if is_hist1(obj):
            obj.SetStats(False)
            if logy:
                # Only turn on logy if the histogram has positive content somewhere.
                if obj.GetMaximum() > 0:
                    canvas.SetLogy(True)
            obj.Draw("HIST E")
            return True

        if is_graph(obj):
            if logy:
                canvas.SetLogy(True)
            obj.Draw("ALP")
            return True

        if is_multigraph(obj):
            if logy:
                canvas.SetLogy(True)
            obj.Draw("A")
            return True

        if is_efficiency(obj):
            obj.Draw("AP")
            return True

        if is_stack(obj):
            if logy:
                canvas.SetLogy(True)
            obj.Draw("NOSTACK")
            return True

        # Fallback: try plain Draw
        draw_meth = getattr(obj, "Draw", None)
        if callable(draw_meth):
            draw_meth()
            return True

        return False

    except Exception as exc:
        print(f"[warn] draw failed for {obj.GetName()} ({class_name(obj)}): {exc}")
        return False


def save_canvas(canvas: ROOT.TCanvas, out_base: Path) -> None:
    png_path = str(out_base.with_suffix(".png"))
    pdf_path = str(out_base.with_suffix(".pdf"))
    canvas.SaveAs(png_path)
    canvas.SaveAs(pdf_path)


def render_object(obj, out_dir: Path, rel_root_path: str, logy: bool, logz: bool, width: int, height: int) -> None:
    """
    Render one object to png/pdf in out_dir.
    """
    name = sanitize_name(obj.GetName())
    out_base = out_dir / name
    cls = class_name(obj)

    print(f"[render] {rel_root_path} ({cls}) -> {out_base}.png/.pdf")

    if is_skippable(obj):
        print(f"[skip] {rel_root_path} ({cls}) is not rendered")
        return

    if is_canvas(obj):
        # Save original canvas directly.
        try:
            obj.SaveAs(str(out_base.with_suffix(".png")))
            obj.SaveAs(str(out_base.with_suffix(".pdf")))
            return
        except Exception as exc:
            print(f"[warn] failed to save existing canvas {rel_root_path}: {exc}")
            return

    canvas = ROOT.TCanvas(f"c_{name}", name, width, height)
    ok = draw_object(obj, canvas, logy=logy, logz=logz)
    if not ok:
        print(f"[skip] unsupported object: {rel_root_path} ({cls})")
        return

    canvas.Modified()
    canvas.Update()
    save_canvas(canvas, out_base)

    # Explicit cleanup helps in large files.
    canvas.Close()


def walk_directory(tdir, out_dir: Path, rel_path: str, logy: bool, logz: bool, width: int, height: int) -> None:
    """
    Recursively walk a ROOT TDirectory and export plottable contents.
    """
    ensure_dir(out_dir)

    keys = tdir.GetListOfKeys()
    if not keys:
        return

    for key in keys:
        key_name = key.GetName()
        obj = key.ReadObj()

        if rel_path:
            obj_rel_path = f"{rel_path}/{key_name}"
        else:
            obj_rel_path = key_name

        if is_directory(obj):
            subdir_name = sanitize_name(key_name)
            sub_out_dir = out_dir / subdir_name
            walk_directory(
                obj,
                sub_out_dir,
                obj_rel_path,
                logy=logy,
                logz=logz,
                width=width,
                height=height,
            )
        else:
            render_object(
                obj,
                out_dir=out_dir,
                rel_root_path=obj_rel_path,
                logy=logy,
                logz=logz,
                width=width,
                height=height,
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export all plottable objects from a ROOT file to PNG and PDF, preserving folder structure."
    )
    parser.add_argument("--input", required=True, help="Input ROOT file")
    parser.add_argument("--outdir", required=True, help="Output directory")
    parser.add_argument("--logy", action="store_true", help="Use log-y for 1D histograms/graphs where sensible")
    parser.add_argument("--logz", action="store_true", help="Use log-z for 2D/profile2D histograms where sensible")
    parser.add_argument("--width", type=int, default=1000, help="Canvas width")
    parser.add_argument("--height", type=int, default=800, help="Canvas height")
    args = parser.parse_args()

    ROOT.gROOT.SetBatch(True)
    ROOT.gStyle.SetOptStat(0)

    input_path = Path(args.input).resolve()
    out_dir = Path(args.outdir).resolve()

    if not input_path.exists():
        print(f"[fatal] input ROOT file does not exist: {input_path}", file=sys.stderr)
        return 2

    ensure_dir(out_dir)

    root_file = ROOT.TFile.Open(str(input_path), "READ")
    if not root_file or root_file.IsZombie():
        print(f"[fatal] could not open ROOT file: {input_path}", file=sys.stderr)
        return 3

    print(f"[info] input  = {input_path}")
    print(f"[info] outdir = {out_dir}")

    walk_directory(
        root_file,
        out_dir=out_dir,
        rel_path="",
        logy=args.logy,
        logz=args.logz,
        width=args.width,
        height=args.height,
    )

    root_file.Close()
    print("[ok] export complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())