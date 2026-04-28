#!/usr/bin/env python3



"""
DOC
Summary: Inspect selected reco events for pT/pathology debugging by printing GGTF 3D-hit spatial spans and GenFit TrackState parameters.
Status: secondary
Usage:
  python3 scripts/inspect_events_pt_pathology.py --input RECO.root --events EVENT1,EVENT2,EVENT3
  python3 scripts/inspect_events_pt_pathology.py --input RECO.root --events 718,838,302 --hits GGTF_3DHits --track GenFitTracks
Examples:
  python3 scripts/inspect_events_pt_pathology.py \
    --input /eos/.../reco_eta+1.00_pt14.142.root \
    --events 718,838,302 \
    --hits GGTF_3DHits \
    --track GenFitTracks
Inputs: Reco ROOT file containing an events TTree, a 3D hit collection with position leaves, and a reconstructed track collection with TrackState leaves.
Outputs: Terminal report for each requested event showing hit count, r/z min/max/span, TrackState count, pT from TrackState.time, pT from 1/|omega|, omega, phi, tanLambda, D0, and Z0.
Collections: Reads GGTF_3DHits by default; reads GenFitTracks TrackStates by default; auto-detects common TrackState branch prefixes for the selected track collection.
Connects-To: scripts/scan_pt_time_by_event.py, scripts/dump_covmatrix_one_event.py, scripts/debug_z_spur_event.py, scripts/view_tracks_event.py, Tracking/components/GenFit2DCHFitter.cpp
Arguments:
  --input: input reco ROOT file.
  --events: comma-separated zero-based event indices to inspect.
  --hits: 3D hit collection prefix used for position.x/y/z leaves; default GGTF_3DHits.
  --track: reconstructed track collection used for TrackState leaves; default GenFitTracks.
Notes:
  This is a read-only event-level diagnostic utility for investigating suspicious pT estimates, large geometry spans, bad curvature values, or track-state publication issues.
  The script compares pT encoded in TrackState.time with pT inferred as 1/|omega|, which is useful for checking the project convention where pT may be stored in the time field.
  Hit statistics are simple geometric summaries: radial span and z span of the selected hit collection in mm.
  TrackState prefix detection checks common EDM4hep/ROOT branch layouts such as GenFitTracks.trackStates., GenFitTracks.TrackStates., and underscored collection forms.
  This script does not create plots or modify files; pair it with debug_z_spur_event.py or view_tracks_event.py when a visual event display is needed.
Tags: secondary, diagnostics, pt-pathology, trackstate, genfittracks, ggtf, root, event-inspection
DOC_END
"""





import argparse, math
import ROOT
ROOT.gROOT.SetBatch(True)

def leaf(tree, name):
    lf = tree.GetLeaf(name)
    return lf

def resolve_ts_prefix(tree, coll):
    cands = [
        f"{coll}.trackStates.",
        f"{coll}.TrackStates.",
        f"{coll}.trackStates_AtIP.",
        f"{coll}.TrackStates_AtIP.",
        f"_{coll}_trackStates.",
        f"_{coll}_TrackStates.",
    ]
    for p in cands:
        if leaf(tree, p + "phi"):
            return p
    # scan
    leaves = tree.GetListOfLeaves()
    for obj in leaves:
        nm = obj.GetName()
        if coll in nm and nm.endswith(".phi"):
            return nm[:-len("phi")]
    return None

def event_hit_stats(tree, ev, coll="GGTF_3DHits"):
    lx = leaf(tree, f"{coll}.position.x")
    ly = leaf(tree, f"{coll}.position.y")
    lz = leaf(tree, f"{coll}.position.z")
    if not (lx and ly and lz):
        return None
    tree.GetEntry(ev)
    n = int(lx.GetNdata())
    if n <= 0:
        return {"n": 0}
    xs = [float(lx.GetValue(i)) for i in range(n)]
    ys = [float(ly.GetValue(i)) for i in range(n)]
    zs = [float(lz.GetValue(i)) for i in range(n)]
    rs = [math.hypot(xs[i], ys[i]) for i in range(n)]
    return {
        "n": n,
        "rmin": min(rs), "rmax": max(rs), "rspan": max(rs)-min(rs),
        "zmin": min(zs), "zmax": max(zs), "zspan": max(zs)-min(zs),
    }

def trackstate_params(tree, ev, track_coll="GenFitTracks"):
    pref = resolve_ts_prefix(tree, track_coll)
    if not pref:
        return None
    tree.GetEntry(ev)
    lphi = leaf(tree, pref+"phi")
    ltl  = leaf(tree, pref+"tanLambda")
    lomg = leaf(tree, pref+"omega")
    ltime= leaf(tree, pref+"time")
    ld0  = leaf(tree, pref+"D0")
    lz0  = leaf(tree, pref+"Z0")
    if not lphi:
        return None
    n = int(lphi.GetNdata())
    if n <= 0:
        return {"n_states": 0}
    # You usually have 1 state; if more, report all
    out = {"n_states": n, "states": []}
    for i in range(n):
        phi  = float(lphi.GetValue(i))
        tl   = float(ltl.GetValue(i)) if ltl else float("nan")
        omg  = float(lomg.GetValue(i)) if lomg else float("nan")
        pt_t = float(ltime.GetValue(i)) if ltime else float("nan")
        pt_o = (1.0/abs(omg)) if (math.isfinite(omg) and abs(omg)>0) else float("nan")
        d0   = float(ld0.GetValue(i)) if ld0 else float("nan")
        z0   = float(lz0.GetValue(i)) if lz0 else float("nan")
        out["states"].append({
            "i": i, "pt_time": pt_t, "pt_1overomega": pt_o, "omega": omg,
            "phi": phi, "tanL": tl, "D0": d0, "Z0": z0
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--events", required=True,
                    help="Comma-separated event indices, e.g. 718,838,302")
    ap.add_argument("--hits", default="GGTF_3DHits")
    ap.add_argument("--track", default="GenFitTracks")
    args = ap.parse_args()

    f = ROOT.TFile.Open(args.input)
    tree = f.Get("events")

    evs = [int(x.strip()) for x in args.events.split(",") if x.strip()]
    print(f"[info] inspecting {len(evs)} events: {evs}")

    for ev in evs:
        hs = event_hit_stats(tree, ev, args.hits)
        ts = trackstate_params(tree, ev, args.track)

        print("\n" + "="*90)
        print(f"event {ev}")
        if hs is None:
            print("  [hits] collection missing")
        else:
            print(f"  [hits] n={hs['n']}")
            if hs["n"] > 0:
                print(f"         rmin={hs['rmin']:.2f} rmax={hs['rmax']:.2f} rspan={hs['rspan']:.2f}  mm")
                print(f"         zmin={hs['zmin']:.2f} zmax={hs['zmax']:.2f} zspan={hs['zspan']:.2f}  mm")

        if ts is None:
            print("  [track] no trackstate prefix / missing leaves")
        else:
            print(f"  [track] n_states={ts['n_states']}")
            for st in ts.get("states", []):
                print(f"         state[{st['i']}]: pT(time)={st['pt_time']:.3f}  "
                      f"pT(1/|omega|)={st['pt_1overomega']:.3f}  omega={st['omega']:.6e}  "
                      f"phi={st['phi']:.3f} tanL={st['tanL']:.3f} D0={st['D0']:.3f} Z0={st['Z0']:.3f}")

    f.Close()

if __name__ == "__main__":
    main()
