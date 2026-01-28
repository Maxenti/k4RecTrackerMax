#!/usr/bin/env python3
"""

DOC
pt_diagnostics_to_root.py

- Reads MCParticles momentum branches (flattened EDM4hep style)
- Reads TrackStates omega (and friends) if present
- Writes an output ROOT with TTrees:
    * mc  : particle rows (optionally filtered by PDG)
    * ts  : trackstate rows (if found)
    * evt : per-event summary (including selected-PDG truth)

Key fixes vs earlier version:
  - Uses uproot arrays(..., how=dict) so branch names remain exact
  - Robust TrackState prefix resolution (scans for *.omega)
  - Correct default prefix for your file: _GenFitTracks_TrackStates

New:
  - --pdg (default 13) to filter MCParticles by PDG
  - --pdg-abs (default True) to match abs(PDG)

DOC_END
"""

import argparse
import numpy as np

def charge_from_pdg(pdg: np.ndarray) -> np.ndarray:
    pdg = np.asarray(pdg, dtype=np.int32)
    q = np.zeros_like(pdg, dtype=np.int8)
    a = np.abs(pdg)

    # leptons: PDG>0 is negative lepton (e-, mu-, tau-)
    m = (a == 11) | (a == 13) | (a == 15)
    q[m] = np.where(pdg[m] > 0, -1, +1).astype(np.int8)

    # common hadrons
    m = (a == 211) | (a == 321) | (a == 2212)
    q[m] = np.where(pdg[m] > 0, +1, -1).astype(np.int8)

    return q

def find_first_existing(keys_set, candidates):
    for c in candidates:
        if c in keys_set:
            return c
    return None

def autodetect_ts_prefix(tree_keys):
    """
    Return prefix for a branch like '<prefix>.omega' by scanning keys.
    Prefer ones that look like GenFitTracks TrackStates.
    """
    omega_branches = [k for k in tree_keys if k.endswith(".omega")]
    if not omega_branches:
        return None, []

    preferred = [
        "_GenFitTracks_trackState.omega",     # <-- your file (one common variant)
        "_GenFitTracks_trackStates.omega",
        "_GenFitTracks_TrackStates.omega",
        "GenFitTracks.trackState.omega",
        "GenFitTracks.trackStates.omega",
        "GenFitTracks.TrackStates.omega",
    ]

    for p in preferred:
        if p in omega_branches:
            return p[:-len(".omega")], omega_branches

    omega_branches_sorted = sorted(
        omega_branches,
        key=lambda s: (("TrackStates" not in s and "trackStates" not in s and "trackState" not in s),
                       ("GenFit" not in s and "GenFitTracks" not in s),
                       len(s))
    )

    best = omega_branches_sorted[0]
    return best[:-len(".omega")], omega_branches

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input ROOT file")
    ap.add_argument("--out", default="pt_diagnostics.root", help="Output ROOT file")
    ap.add_argument("--tree", default="events", help="TTree name (default: events)")

    ap.add_argument("--mc-prefix", default="MCParticles/MCParticles",
                    help="Prefix under tree for MCParticles (default: MCParticles/MCParticles)")

    ap.add_argument("--max-events", type=int, default=-1,
                    help="Limit number of events to read (-1 = all)")

    # NEW: MC PDG filtering
    ap.add_argument("--pdg", type=int, default=13,
                    help="Keep only MCParticles with PDG matching this value (default: 13).")
    ap.add_argument("--pdg-abs", dest="pdg_abs", action="store_true",
                    help="Match abs(PDG) (default).")
    ap.add_argument("--no-pdg-abs", dest="pdg_abs", action="store_false",
                    help="Match PDG with sign.")
    ap.set_defaults(pdg_abs=True)

    # TrackStates
    ap.add_argument("--trackstate-prefix", default="",
                    help="Explicit TrackState prefix (e.g. _GenFitTracks_TrackStates). If empty, auto-detect.")
    ap.add_argument("--assume-q", type=int, default=-1,
                    help="Charge sign used for pT=|q/omega| if you don't want to derive q from MC (default: -1 for mu-).")

    args = ap.parse_args()

    try:
        import uproot
        import awkward as ak
    except Exception as e:
        raise SystemExit(
            "This script needs 'uproot' and 'awkward'.\n"
            "If not available: python3 -m pip install --user uproot awkward\n"
            f"Import error: {e}"
        )

    with uproot.open(args.input) as f:
        if args.tree not in f:
            raise SystemExit(f"Tree '{args.tree}' not found. Available keys: {list(f.keys())}")
        t = f[args.tree]
        keys = list(t.keys())
        keys_set = set(keys)

        # ---- MCParticles branches ----
        mc_px = f"{args.mc_prefix}.momentum.x"
        mc_py = f"{args.mc_prefix}.momentum.y"
        mc_pz = f"{args.mc_prefix}.momentum.z"

        mc_pdg = find_first_existing(keys_set, [
            f"{args.mc_prefix}.PDG",
            f"{args.mc_prefix}.pdg",
            f"{args.mc_prefix}.particleID",
            f"{args.mc_prefix}.ParticleID",
        ])

        for b in (mc_px, mc_py, mc_pz):
            if b not in keys_set:
                sample = "\n  ".join(keys[:120])
                raise SystemExit(f"Missing branch '{b}'. First ~120 branches:\n  {sample}")

        read_branches = [mc_px, mc_py, mc_pz]
        if mc_pdg:
            read_branches.append(mc_pdg)

        # ---- TrackStates branches (resolve prefix) ----
        ts_prefix = args.trackstate_prefix.strip() if args.trackstate_prefix.strip() else None
        omega_candidates = []
        if ts_prefix is None:
            ts_prefix, omega_candidates = autodetect_ts_prefix(keys)

        ts_branches = []
        if ts_prefix is not None and f"{ts_prefix}.omega" in keys_set:
            for b in [
                f"{ts_prefix}.omega",
                f"{ts_prefix}.time",
                f"{ts_prefix}.phi",
                f"{ts_prefix}.tanLambda",
                f"{ts_prefix}.D0",
                f"{ts_prefix}.Z0",
            ]:
                if b in keys_set:
                    ts_branches.append(b)
        else:
            ts_prefix = None  # treat as absent

        all_read = read_branches + ts_branches

        arrays = t.arrays(
            all_read,
            entry_stop=(args.max_events if args.max_events and args.max_events > 0 else None),
            how=dict,
            library="ak",
        )

    import awkward as ak  # now safe

    # ---------------- MC calculations (per-event jagged) ----------------
    px = arrays[mc_px]
    py = arrays[mc_py]
    pz = arrays[mc_pz]

    mc_pt = np.sqrt(px*px + py*py)
    mc_p  = np.sqrt(px*px + py*py + pz*pz)

    tiny = 1e-12
    mc_eta = np.arcsinh(pz / np.maximum(mc_pt, tiny))
    mc_phi = np.arctan2(py, px)

    # PDG + charge
    if mc_pdg:
        pdg = arrays[mc_pdg]
    else:
        # if no PDG branch, make a dummy array of zeros with same shape
        pdg = ak.zeros_like(mc_pt, dtype=np.int32)

    # Build selection mask
    target = int(args.pdg)
    if args.pdg_abs:
        sel = (np.abs(pdg) == abs(target))
    else:
        sel = (pdg == target)

    # Apply selection (MCParticles)
    px_sel   = px[sel]
    py_sel   = py[sel]
    pz_sel   = pz[sel]
    pt_sel   = mc_pt[sel]
    p_sel    = mc_p[sel]
    eta_sel  = mc_eta[sel]
    phi_sel  = mc_phi[sel]
    pdg_sel  = pdg[sel]

    # Flatten selected for mc tree
    mc_pt_f  = ak.to_numpy(ak.flatten(pt_sel, axis=None))
    mc_p_f   = ak.to_numpy(ak.flatten(p_sel, axis=None))
    mc_eta_f = ak.to_numpy(ak.flatten(eta_sel, axis=None))
    mc_phi_f = ak.to_numpy(ak.flatten(phi_sel, axis=None))
    mc_px_f  = ak.to_numpy(ak.flatten(px_sel, axis=None))
    mc_py_f  = ak.to_numpy(ak.flatten(py_sel, axis=None))
    mc_pz_f  = ak.to_numpy(ak.flatten(pz_sel, axis=None))
    mc_pdg_f = ak.to_numpy(ak.flatten(pdg_sel, axis=None)).astype(np.int32)

    if mc_pdg:
        mc_q_f = charge_from_pdg(mc_pdg_f)
        mc_q_f = np.where(mc_q_f == 0, np.int8(args.assume_q), mc_q_f).astype(np.int8)
    else:
        mc_q_f = np.full_like(mc_pt_f, np.int8(args.assume_q), dtype=np.int8)

    n_ev = len(px)
    ev_ids = np.arange(n_ev, dtype=np.int32)

    # Event id + particle index for selected-only list
    mc_ev = ak.to_numpy(ak.flatten(ak.broadcast_arrays(ev_ids, pt_sel)[0], axis=None)).astype(np.int32)
    mc_ip = ak.to_numpy(ak.flatten(ak.local_index(pt_sel, axis=1), axis=None)).astype(np.int32)

    print(f"[mc] Filter: pdg={'abs' if args.pdg_abs else 'signed'}({args.pdg})")
    print(f"[mc] N selected particles = {mc_pt_f.size} across N events = {n_ev}")
    if mc_pt_f.size > 0:
        print(f"[mc] selected pT min/median/mean/max = "
              f"{mc_pt_f.min():.6g} / {np.median(mc_pt_f):.6g} / {mc_pt_f.mean():.6g} / {mc_pt_f.max():.6g} (GeV)")
    else:
        print("[mc] WARNING: selection produced zero particles. Check --pdg/--no-pdg-abs or input branches.")

    # ---------------- TrackState calculations ----------------
    have_ts = False
    ts_ev = ts_it = ts_omega_f = ts_pt_from_omega_f = None
    ts_time_f = ts_phi_f = ts_tanL_f = ts_d0_f = ts_z0_f = None

    if ts_prefix is not None and f"{ts_prefix}.omega" in arrays:
        have_ts = True
        omega = arrays[f"{ts_prefix}.omega"]

        ts_ev = ak.to_numpy(ak.flatten(ak.broadcast_arrays(ev_ids, omega)[0], axis=None)).astype(np.int32)
        ts_it = ak.to_numpy(ak.flatten(ak.local_index(omega, axis=1), axis=None)).astype(np.int32)

        ts_omega_f = ak.to_numpy(ak.flatten(omega, axis=None)).astype(np.float32)

        q_assume = float(args.assume_q) if args.assume_q != 0 else -1.0
        denom = np.where(np.isfinite(ts_omega_f) & (np.abs(ts_omega_f) > 0.0), ts_omega_f, np.nan)
        ts_pt_from_omega_f = np.abs(q_assume / denom).astype(np.float32)

        def get_flat(branch, dtype=np.float32):
            if branch in arrays:
                return ak.to_numpy(ak.flatten(arrays[branch], axis=None)).astype(dtype)
            return None

        ts_time_f = get_flat(f"{ts_prefix}.time", np.float32)
        ts_phi_f  = get_flat(f"{ts_prefix}.phi", np.float32)
        ts_tanL_f = get_flat(f"{ts_prefix}.tanLambda", np.float32)
        ts_d0_f   = get_flat(f"{ts_prefix}.D0", np.float32)
        ts_z0_f   = get_flat(f"{ts_prefix}.Z0", np.float32)

        print(f"[ts] TrackState prefix = {ts_prefix}")
        print(f"[ts] N trackstates = {ts_omega_f.size}")
        if np.isfinite(ts_omega_f).any():
            print(f"[ts] omega min/median/mean/max = "
                  f"{np.nanmin(ts_omega_f):.6g} / {np.nanmedian(ts_omega_f):.6g} / "
                  f"{np.nanmean(ts_omega_f):.6g} / {np.nanmax(ts_omega_f):.6g} (GeV^-1)")
        if np.isfinite(ts_pt_from_omega_f).any():
            print(f"[ts] pT_from_omega min/median/mean/max = "
                  f"{np.nanmin(ts_pt_from_omega_f):.6g} / {np.nanmedian(ts_pt_from_omega_f):.6g} / "
                  f"{np.nanmean(ts_pt_from_omega_f):.6g} / {np.nanmax(ts_pt_from_omega_f):.6g} (GeV)")
    else:
        print("[ts] No TrackStates omega branch found.")
        if omega_candidates:
            print("[ts] But I *did* find omega-like branches in the file:")
            for k in omega_candidates[:20]:
                print("   ", k)
            if len(omega_candidates) > 20:
                print(f"   ... ({len(omega_candidates)-20} more)")
        print("[ts] If you know the right one, run with: --trackstate-prefix '<prefix>'")

    # ---------------- Event-level summary ----------------
    # How many selected truth particles in each event?
    n_mc_sel_evt = ak.to_numpy(ak.num(pt_sel, axis=1)).astype(np.int32)

    # "mc0_pt" = first selected particle's pT (NaN if none)
    mc0_pt = ak.to_numpy(ak.fill_none(ak.firsts(pt_sel), np.nan)).astype(np.float32)

    if have_ts:
        n_ts_evt = ak.to_numpy(ak.num(arrays[f"{ts_prefix}.omega"], axis=1)).astype(np.int32)
        ts0_omega = ak.to_numpy(ak.fill_none(ak.firsts(arrays[f"{ts_prefix}.omega"]), np.nan)).astype(np.float32)
        denom0 = np.where(np.isfinite(ts0_omega) & (np.abs(ts0_omega) > 0), ts0_omega, np.nan)
        ts0_pt = np.abs(float(args.assume_q) / denom0).astype(np.float32)
    else:
        n_ts_evt = np.zeros(n_ev, dtype=np.int32)
        ts0_omega = np.full(n_ev, np.nan, dtype=np.float32)
        ts0_pt    = np.full(n_ev, np.nan, dtype=np.float32)

    # ---------------- Write output ROOT ----------------
    import uproot

    with uproot.recreate(args.out) as fout:
        fout["mc"] = {
            "event": mc_ev,
            "ipart": mc_ip,
            "px": mc_px_f.astype(np.float32),
            "py": mc_py_f.astype(np.float32),
            "pz": mc_pz_f.astype(np.float32),
            "pt": mc_pt_f.astype(np.float32),
            "p":  mc_p_f.astype(np.float32),
            "eta": mc_eta_f.astype(np.float32),
            "phi": mc_phi_f.astype(np.float32),
            "pdg": mc_pdg_f.astype(np.int32),
            "q":   mc_q_f.astype(np.int8),
        }

        if have_ts:
            out_ts = {
                "event": ts_ev,
                "its": ts_it,
                "omega": ts_omega_f,
                "pt_from_omega": ts_pt_from_omega_f,
            }
            if ts_time_f is not None: out_ts["time"] = ts_time_f
            if ts_phi_f  is not None: out_ts["phi"]  = ts_phi_f
            if ts_tanL_f is not None: out_ts["tanLambda"] = ts_tanL_f
            if ts_d0_f   is not None: out_ts["d0"] = ts_d0_f
            if ts_z0_f   is not None: out_ts["z0"] = ts_z0_f
            fout["ts"] = out_ts

        fout["evt"] = {
            "event": ev_ids.astype(np.int32),
            "n_mc_sel": n_mc_sel_evt,
            "n_ts": n_ts_evt,
            "mc0_pt": mc0_pt,
            "ts0_omega": ts0_omega,
            "ts0_pt_from_omega": ts0_pt,
        }

    print(f"[info] Wrote ROOT diagnostics file: {args.out}")
    print("[info] Trees:", "mc, ts, evt" if have_ts else "mc, evt (no ts)")

if __name__ == "__main__":
    main()
