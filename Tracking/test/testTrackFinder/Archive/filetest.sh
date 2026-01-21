python3 - <<'PY' /eos/user/c/cglenn/reco_samples/eta_+0.50/reco_gun_eta+0.50_pt200.root
import sys, ROOT
ROOT.gErrorIgnoreLevel = 3001

path = sys.argv[1]
f = ROOT.TFile.Open(path)
if not f or f.IsZombie():
    raise SystemExit(f"Cannot open {path}")
t = f.Get("events")
if not t:
    raise SystemExit("No 'events' tree")

def show_branch(name):
    b = t.GetBranch(name)
    if not b:
        print(f"{name}: MISSING")
        return None
    cls = b.GetClassName()
    leaves = b.GetListOfLeaves()
    types = [(leaves.At(i).GetName(), leaves.At(i).GetTypeName())
             for i in range(leaves.GetSize())]
    print(f"{name}: class='{cls}', leaves={types}")
    return b

print("=== GenFitTracks track-state structure ===")
# PODIO “split” layout usually has:
#   _GenFitTracks_trackStates              (offsets: std::vector<uint32>)
#   GenFitTracks_trackStates_<field>       (values: std::vector<float/double>)
for nm in [
    "_GenFitTracks_trackStates",
    "GenFitTracks_trackStates_omega",
    "GenFitTracks_trackStates_qOverP",
    "GenFitTracks_trackStates_theta",
    "GenFitTracks_trackStates_tanLambda",
    "GenFitTracks_trackStates_phi",
    "GenFitTracks_tracks_omega",
    "GenFitTracks_tracks_qOverP",
    "GenFitTracks_tracks_theta",
]:
    show_branch(nm)

# Also list any other state fields that might exist
print("\n=== All branches starting with 'GenFitTracks_trackStates' ===")
for b in t.GetListOfBranches():
    n = b.GetName()
    if n.startswith("GenFitTracks_trackStates_"):
        show_branch(n)

# Tiny content sanity: read offsets and the first arrays if present
off_b = t.GetBranch("_GenFitTracks_trackStates")
if off_b:
    r = ROOT.TTreeReader(t)
    try:
        off = ROOT.TTreeReaderValue("std::vector<unsigned int>")(r, "_GenFitTracks_trackStates")
    except Exception:
        # some stacks write 'vector<uint32_t>' as 'vector<unsigned int>' transparently;
        # if that fails, try explicit uint32_t
        off = ROOT.TTreeReaderValue("std::vector<uint32_t>")(r, "_GenFitTracks_trackStates")

    # Try available numeric types for values
    def bind_vec(name):
        for typ in ("float","double"):
            try:
                return ROOT.TTreeReaderValue(f"std::vector<{typ}>")(r, name)
            except Exception:
                pass
        return None

    om = bind_vec("GenFitTracks_trackStates_omega")
    tl = bind_vec("GenFitTracks_trackStates_tanLambda")
    qp = bind_vec("GenFitTracks_trackStates_qOverP")
    th = bind_vec("GenFitTracks_trackStates_theta")

    if r.Next():
        offs = list(off.Get())
        print("\n--- content peek ---")
        print("offsets: n=", len(offs), " last=", (offs[-1] if offs else None))
        if om: print("omega array length     :", len(list(om.Get())))
        if tl: print("tanLambda array length :", len(list(tl.Get())))
        if qp: print("qOverP array length    :", len(list(qp.Get())))
        if th: print("theta array length     :", len(list(th.Get())))

f.Close()
PY
