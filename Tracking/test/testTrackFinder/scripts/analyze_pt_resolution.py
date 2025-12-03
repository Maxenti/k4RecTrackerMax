#!/usr/bin/env python3
import argparse, os, math, glob, numpy as np
import awkward as ak
import uproot
import csv
import matplotlib.pyplot as plt

def robust_sigma(arr):
    arr = np.asarray(arr)
    if arr.size == 0:
        return np.nan
    # 68% central interval
    q16, q84 = np.nanpercentile(arr, [16, 84])
    return 0.5*(q84 - q16)

def pick_best_track_per_event(tracks, chi2, nstates):
    """
    tracks: dict of arrays ('px','py','pz'), shape per event: variable-length list
    chi2, nstates: per-track arrays
    returns per-event reco px,py,pz (or NaN if none)
    """
    nevt = len(tracks["px"])
    out_px = np.full(nevt, np.nan)
    out_py = np.full(nevt, np.nan)
    out_pz = np.full(nevt, np.nan)

    for i in range(nevt):
      if len(tracks["px"][i]) == 0:
          continue
      # prefer lowest chi2; if chi2 not finite, fallback to max nstates; else first
      chi2_i = np.array(chi2[i]) if len(chi2[i]) else np.array([])
      nst_i  = np.array(nstates[i]) if len(nstates[i]) else np.array([])
      idx = None
      if chi2_i.size and np.isfinite(chi2_i).any():
          good = np.where(np.isfinite(chi2_i))[0]
          idx = good[np.argmin(chi2_i[good])]
      elif nst_i.size:
          idx = int(np.argmax(nst_i))
      else:
          idx = 0
      out_px[i] = tracks["px"][i][idx]
      out_py[i] = tracks["py"][i][idx]
      out_pz[i] = tracks["pz"][i][idx]
    return out_px, out_py, out_pz

def read_truth_pt(file, mc_col="MCParticles"):
    with uproot.open(file) as f:
        tree = f["events"]
        # Common EDM4hep branch names
        mx = tree[f"{mc_col}.momentum.x"].arrays(library="ak")[f"{mc_col}.momentum.x"]
        my = tree[f"{mc_col}.momentum.y"].arrays(library="ak")[f"{mc_col}.momentum.y"]
        # Take the first MC particle per event (single-muon gun)
        px = ak.fill_none(ak.firsts(mx), np.nan)
        py = ak.fill_none(ak.firsts(my), np.nan)
        pt = np.sqrt(ak.to_numpy(px)**2 + ak.to_numpy(py)**2)
        return np.asarray(pt)

def read_tracks(file, trk_col="GenFitTracks"):
    with uproot.open(file) as f:
        tree = f["events"]
        # TrackStates present: take last (or first) state momentum per track
        # Arrays are jagged: tracks per event, states per track
        # We'll load momentum in the flattened TrackStates and then regroup via offsets.
        pxs = tree[f"{trk_col}.trackStates.momentum.x"].arrays(library="ak")[f"{trk_col}.trackStates.momentum.x"]
        pys = tree[f"{trk_col}.trackStates.momentum.y"].arrays(library="ak")[f"{trk_col}.trackStates.momentum.y"]
        pzs = tree[f"{trk_col}.trackStates.momentum.z"].arrays(library="ak")[f"{trk_col}.trackStates.momentum.z"]
        chis= tree[f"{trk_col}.tracks.chi2"].arrays(library="ak")[f"{trk_col}.tracks.chi2"]
        # Regroup states by track, then pick last state per track
        # pxs has structure: events -> tracks -> states
        last_px = ak.fill_none(ak.lasts(pxs, axis=2), np.nan)
        last_py = ak.fill_none(ak.lasts(pys, axis=2), np.nan)
        last_pz = ak.fill_none(ak.lasts(pzs, axis=2), np.nan)
        nstates = ak.num(pxs, axis=2)

        # Now pick best track per event
        tracks = {
            "px": last_px,
            "py": last_py,
            "pz": last_pz,
        }
        best_px, best_py, best_pz = pick_best_track_per_event(tracks, chis, nstates)
        pt = np.sqrt(best_px**2 + best_py**2)
        return np.asarray(pt)

def main():
    ap = argparse.ArgumentParser(description="Compute pT resolution vs pT")
    ap.add_argument("reco_files", nargs="+", help="Reco ROOT files (one pT value per file)")
    ap.add_argument("--mc-col", default="MCParticles")
    ap.add_argument("--trk-col", default="GenFitTracks")
    ap.add_argument("--out-csv", default="pt_resolution.csv")
    ap.add_argument("--out-png", default="pt_resolution.png")
    ap.add_argument("--eta-max", type=float, default=1.0, help="(optional) cut if you also read MC eta")
    args = ap.parse_args()

    rows = []
    for rf in args.reco_files:
        if not os.path.isfile(rf):
            print(f"[warn] missing {rf}, skip")
            continue
        # Guess true pT from filename if possible (fallback to median truth)
        pT_guess = None
        base = os.path.basename(rf)
        for tag in ("pT", "E"):
            if f"{tag}" in base and "GeV" in base:
                try:
                    pT_guess = float(base.split(f"{tag}")[1].split("GeV")[0])
                    break
                except Exception:
                    pass

        pt_true = read_truth_pt(rf, args.mc_col)
        pt_reco = read_tracks(rf, args.trk_col)

        # Drop events with no reco
        good = np.isfinite(pt_reco)
        pt_true = pt_true[good]
        pt_reco = pt_reco[good]

        if pt_true.size == 0:
            print(f"[info] {rf}: no reco tracks")
            continue

        # Metrics
        rel = (pt_reco - pt_true) / pt_true
        inv_resid = (1.0/pt_reco) - (1.0/pt_true)

        sigma_rel = robust_sigma(rel)
        sigma_inv = robust_sigma(inv_resid)

        pt_ref = np.nanmedian(pt_true) if pT_guess is None else pT_guess
        rows.append((pt_ref, sigma_rel, sigma_inv, pt_true.size, os.path.basename(rf)))
        print(f"[done] {os.path.basename(rf)}  N={pt_true.size}  pT≈{pt_ref:.3g} GeV  "
              f"sigma(rel)={sigma_rel:.3e}  sigma(1/pT)={sigma_inv:.3e} GeV^-1")

    rows.sort(key=lambda r: r[0])

    # CSV
    with open(args.out_csv, "w", newline="") as fp:
        w = csv.writer(fp)
        w.writerow(["pT_true_GeV", "sigma_rel", "sigma_invpt_GeV^-1", "N_events", "file"])
        for r in rows: w.writerow(r)

    # Plot
    pT = [r[0] for r in rows]
    sig_rel = [r[1] for r in rows]
    sig_inv = [r[2] for r in rows]

    plt.figure()
    plt.loglog(pT, sig_inv, marker="o")
    plt.xlabel("pT [GeV]")
    plt.ylabel(r"$\sigma(1/p_T)$  [GeV$^{-1}$]")
    plt.title("pT resolution (inverse) vs pT")
    plt.grid(True, which="both", ls=":")
    plt.tight_layout()
    plt.savefig(args.out_png, dpi=180)
    print(f"[write] {args.out_csv}, {args.out_png}")

if __name__ == "__main__":
    main()
