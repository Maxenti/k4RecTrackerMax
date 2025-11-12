#!/usr/bin/env python3
# ptres_from_edm4hep.py  (v2: spacepoint→SimHit proximity matching)

import math
import argparse
from collections import defaultdict, Counter
import numpy as np
from podio.root_io import Reader
import edm4hep  # ensure type mapping

K = 0.299792458  # GeV/(c·T·m)

def pT_from_state(ts, bz_t):
    denom = abs(ts.omega) * 1000.0
    if bz_t == 0.0 or denom == 0.0:
        return 0.0
    return (K * abs(bz_t)) / (denom)

def signed_q_over_pT_from_state(ts, bz_t):
    if bz_t == 0.0 or ts.omega == 0.0:
        return 0.0
    return (ts.omega * 1000.0) / (K * bz_t)

def robust_sigma(values):
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

def obj_key(obj):
    oid = obj.getObjectID()
    return (oid.collectionID, oid.index)

def mcp_from_simhit(simhit):
    # Try several bindings styles
    try:
        mcp = simhit.getMCParticle()
        if mcp is not None and getattr(mcp, "isAvailable", lambda: True)():
            return mcp
    except Exception:
        pass
    for attr in ("mcParticle", "MCParticle"):
        try:
            mcp = getattr(simhit, attr)
            if callable(mcp): mcp = mcp()
            if mcp is not None and getattr(mcp, "isAvailable", lambda: True)():
                return mcp
        except Exception:
            continue
    return None

def main():
    ap = argparse.ArgumentParser(description="pT resolution from EDM4hep using SimHit proximity matching")
    ap.add_argument("input", help="EDM4hep ROOT file")
    ap.add_argument("--tracks", default="GenFitTracks", help="Track collection name")
    ap.add_argument("--simhits", default="DCHCollection", help="DCH SimTrackerHit collection")
    ap.add_argument("--mc", default="MCParticles", help="MCParticle collection")
    ap.add_argument("--bz", type=float, default=2.0, help="Magnetic field [T] used in fit")
    ap.add_argument("--purity", type=float, default=0.60, help="Minimum spacepoint→MC vote purity")
    ap.add_argument("--minSimHits", type=int, default=6, help="MC denominator: min SimHits in DCH")
    ap.add_argument("--ptBins", default="0.5,1,2,5,10,20,50,100", help="Comma-separated pT bin edges [GeV]")
    # proximity gates (mm)
    ap.add_argument("--drXY", type=float, default=3.0, help="Max XY distance (mm) to associate a spacepoint to a SimHit")
    ap.add_argument("--dz",   type=float, default=15.0, help="Max |Δz| (mm) to associate a spacepoint to a SimHit")
    args = ap.parse_args()

    pt_edges = np.array([float(x) for x in args.ptBins.split(",") if x])

    rdr = Reader(args.input)
    events = rdr.get("events")

    n_truth_den = Counter()
    bin_residuals = defaultdict(list)
    matched_count = 0
    reco_count = 0

    for iev, evt in enumerate(events):
        tracks  = evt.get(args.tracks)
        simhits = evt.get(args.simhits)
        mcparts = evt.get(args.mc)

        # ---- build SimHit arrays + map to MC keys
        sim_xyz = []
        sim_mc_keys = []

        mc_simhit_count = Counter()
        for sh in simhits:
            mcp = mcp_from_simhit(sh)
            if mcp is None:
                continue
            mc_key = obj_key(mcp)
            mc_simhit_count[mc_key] += 1
            p = sh.getPosition()
            sim_xyz.append((p.x, p.y, p.z))
            sim_mc_keys.append(mc_key)

        if len(sim_xyz) == 0:
            continue

        sim_xyz = np.asarray(sim_xyz, dtype=np.float32)
        sim_xy = sim_xyz[:, :2]
        sim_z  = sim_xyz[:, 2]
        dr2_max = args.drXY * args.drXY
        dz_max  = args.dz

        # ---- denominator by truth pT bins
        for mcp in mcparts:
            n_hits = mc_simhit_count.get(obj_key(mcp), 0)
            if n_hits >= args.minSimHits:
                mom = mcp.getMomentum()
                pt_truth = math.hypot(mom.x, mom.y)
                ib = int(np.digitize([pt_truth], pt_edges)[0] - 1)
                if 0 <= ib < len(pt_edges) - 1:
                    n_truth_den[ib] += 1

        # ---- per-track matching
        for trk in tracks:
            reco_count += 1

            # choose the AtIP state we wrote in the fitter
            ts_atip = None
            for ts in trk.getTrackStates():
                if ts.location == edm4hep.TrackState.AtIP:
                    ts_atip = ts
                    break
            if ts_atip is None or ts_atip.omega == 0.0:
                continue

            # collect spacepoints
            sp_xyz = []
            for h in trk.getTrackerHits():
                try:
                    p = h.getPosition()
                except Exception:
                    # older bindings
                    p = h.position()
                sp_xyz.append((p.x, p.y, p.z))
            if not sp_xyz:
                continue

            sp_xyz = np.asarray(sp_xyz, dtype=np.float32)
            sp_xy  = sp_xyz[:, :2]
            sp_z   = sp_xyz[:, 2]

            # nearest-neighbour in XY with Δz gate (vectorized)
            votes = Counter()
            for i in range(sp_xy.shape[0]):
                dxy = sim_xy - sp_xy[i]
                dr2 = (dxy * dxy).sum(axis=1)
                # fast pre-gate by dr2
                mask = dr2 <= dr2_max
                if not np.any(mask):
                    continue
                # now apply |Δz|
                dz = np.abs(sim_z[mask] - sp_z[i])
                m2 = dz <= dz_max
                if not np.any(m2):
                    continue
                # pick closest among the remaining
                cand_idx = np.nonzero(mask)[0][m2]
                j = cand_idx[np.argmin(dr2[mask][m2])]
                votes[sim_mc_keys[j]] += 1

            if not votes:
                continue

            mc_key, n_vote = votes.most_common(1)[0]
            purity = n_vote / sum(votes.values())
            if purity < args.purity:
                continue

            # fetch MCParticle to get truth pT and charge
            mcp = None
            try:
                # index part of key often works
                mcp = mcparts[mc_key[1]]
                if obj_key(mcp) != mc_key:
                    mcp = None
            except Exception:
                mcp = None
            if mcp is None:
                for cand in mcparts:
                    if obj_key(cand) == mc_key:
                        mcp = cand
                        break
            if mcp is None:
                continue

            q_truth = int(round(mcp.getCharge()))
            mom = mcp.getMomentum()
            pt_truth = math.hypot(mom.x, mom.y)
            if pt_truth <= 0:
                continue

            q_over_pt_reco  = signed_q_over_pT_from_state(ts_atip, args.bz)
            q_over_pt_truth = q_truth / pt_truth
            delta_q_over_pt = q_over_pt_reco - q_over_pt_truth

            ib = int(np.digitize([pt_truth], pt_edges)[0] - 1)
            if 0 <= ib < len(pt_edges) - 1:
                bin_residuals[ib].append(delta_q_over_pt)
                matched_count += 1

    # ---- report ----
    print("\n=== pT Resolution (using Δ(q/pT)) ===")
    print(f"Input: {args.input}")
    print(f"Bz = {args.bz} T | purity >= {args.purity:.2f} | minSimHits (den) >= {args.minSimHits}")
    print(f"Reco tracks seen: {reco_count} | Matched tracks: {matched_count}\n")

    header = f"{'pT bin [GeV]':>14} | {'Nmatch':>7} | {'bias <Δ(q/pT)>':>15} | {'σ_core(Δ(q/pT))':>18} | {'eff (matched/den)':>18}"
    print(header)
    print("-" * len(header))

    for ib in range(len(pt_edges) - 1):
        lo, hi = pt_edges[ib], pt_edges[ib+1]
        vals = bin_residuals.get(ib, [])
        n_den = n_truth_den.get(ib, 0)
        n = len(vals)
        bias = float(np.mean(vals)) if n > 0 else float("nan")
        sig = robust_sigma(vals) if n > 0 else float("nan")
        eff = (n / n_den) if n_den > 0 else float("nan")
        print(f"[{lo:5.1f},{hi:5.1f}] | {n:7d} | {bias:15.4e} | {sig:18.4e} | {eff:18.3f}")

    print("\nNotes:")
    print(" • Matching is done by nearest SimTrackerHit to each spacepoint (ΔR_xy<=drXY, |Δz|<=dz);"
          " dominant MC by votes per track, with a purity cut.")
    print(" • Denominator counts MCParticles with ≥ minSimHits in the DCH per pT bin.")
    print(" • Convert to σ(pT)/pT by multiplying σ(Δ(q/pT)) by pT_truth in each bin.")

if __name__ == "__main__":
    main()
