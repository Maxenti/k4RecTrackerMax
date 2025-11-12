import glob, re, math, numpy as np, uproot
import matplotlib.pyplot as plt

RECO_DIR = "reco_samples"
FIT_COLLECTION = "FittedTracks"     # matches --fitOut in reco_scan.sh

# filename pattern
pat = re.compile(r".*gun_eta(?P<eta>[+-]\d+\.\d+)_pt(?P<pt>[\d\.eE+-]+)_reco\.root$")

def extract_eta_pt(path):
    m = pat.match(path)
    if not m: return None
    return float(m.group("eta")), float(m.group("pt"))

def get_leading_pt(reco_file):
    with uproot.open(reco_file) as f:
        # edm4hep Tracks are typically in a TTree like "events/FittedTracks"
        # Common branches: FittedTracks.tracks, FittedTracks.TrackStates, etc.
        # Minimal: use pT from TrackState(AtIP) if present; otherwise derive from px,py if stored.
        # Here we assume TrackState is flat with "FittedTracks.TrackStates_time" storing pT (as in your GF2 code).
        # Fallback: compute from px,py if present.
        # Adjust branch names to match your output (inspect one file with uproot.open(...).keys()).
        try:
            tree = f["events"]
        except Exception:
            # sometimes it's "collections" or top-level; print keys if needed
            for k in f.keys(): print("ROOT key:", k)
            raise

        # Try the TrackStates 'time' as pT (your GF2 sets ts.time = pT)
        # Branch could be: f"events/{FIT_COLLECTION}#TrackStates_time" if split; uproot flattens differently per writer.
        # Let's search keys for something containing the collection and 'TrackStates_time'
        keys = [k for k in tree.keys() if FIT_COLLECTION in k]
        time_keys = [k for k in keys if "TrackStates_time" in k]
        if time_keys:
            arr = tree[time_keys[0]].array(library="np")
            if arr.size == 0: return None
            # pick leading per event: but we have 1 track per event; flatted array works
            # If multiple tracks: take max pT
            return float(np.max(arr))
        # Fallback: px/py approach
        px_keys = [k for k in keys if k.endswith("_px")]
        py_keys = [k for k in keys if k.endswith("_py")]
        if px_keys and py_keys:
            px = tree[px_keys[0]].array(library="np")
            py = tree[py_keys[0]].array(library="np")
            if px.size == 0: return None
            return float(np.max(np.hypot(px, py)))

        # Last fallback: if there is a scalar pT branch
        pt_keys = [k for k in keys if k.endswith("_pt") or k.endswith(".pt")]
        if pt_keys:
            arr = tree[pt_keys[0]].array(library="np")
            if arr.size == 0: return None
            return float(np.max(arr))

        raise RuntimeError(f"Could not find pT branch for {reco_file}")

def robust_sigma(x):
    if len(x) == 0: return None
    q16, q84 = np.percentile(x, [16, 84])
    return 0.5*(q84 - q16)

# collect results
curves = {}  # eta -> list of (pt_true, sigma_rel)
files = sorted(glob.glob(f"{RECO_DIR}/gun_eta*_pt*_reco.root"))
if not files:
    raise SystemExit(f"No files found in {RECO_DIR}")

for path in files:
    parsed = extract_eta_pt(path)
    if not parsed: 
        print("skip (no match):", path)
        continue
    eta, pt_true = parsed

    # read all events' reco pT; because files are 1 setting each, we just need a vector of reco pT per event
    with uproot.open(path) as f:
        tree = f["events"]
        # same discovery as above:
        keys = [k for k in tree.keys() if FIT_COLLECTION in k]
        time_keys = [k for k in keys if "TrackStates_time" in k]
        if time_keys:
            pt_rec = tree[time_keys[0]].array(library="np")
        else:
            # try px/py fallback
            px_keys = [k for k in keys if k.endswith("_px")]
            py_keys = [k for k in keys if k.endswith("_py")]
            if px_keys and py_keys:
                px = tree[px_keys[0]].array(library="np")
                py = tree[py_keys[0]].array(library="np")
                pt_rec = np.hypot(px, py)
            else:
                # last fallback: any pt-like branch
                pt_keys = [k for k in keys if k.endswith("_pt") or k.endswith(".pt")]
                if not pt_keys:
                    print("WARN: no pT branches for", path)
                    continue
                pt_rec = tree[pt_keys[0]].array(library="np")

    pt_rec = np.asarray(pt_rec, dtype=float)
    if pt_rec.size == 0:
        print("WARN: no reco tracks in", path)
        continue

    # relative residuals
    rel = (pt_rec - pt_true) / pt_true
    sig = robust_sigma(rel)
    if sig is None: 
        continue

    curves.setdefault(eta, []).append((pt_true, sig))

# plot
plt.figure(figsize=(7.5, 5.5))
for eta, pts in sorted(curves.items(), key=lambda kv: kv[0]):
    pts = sorted(pts, key=lambda t: t[0])
    x = [p for p,_ in pts]
    y = [s for _,s in pts]
    lbl = rf"$\eta={eta:+.2f}$"
    plt.plot(x, y, marker="o", lw=1.2, label=lbl)

plt.xscale("log")
plt.yscale("log")
plt.xlabel(r"$p_{T}$  [GeV]")
plt.ylabel(r"$\sigma(p_{T})/p_{T}$")
plt.grid(True, which="both", ls=":")
plt.legend(fontsize=9, ncol=2)
plt.tight_layout()
plt.savefig("pt_resolution_vs_pt_by_eta.png", dpi=160)
print("wrote pt_resolution_vs_pt_by_eta.png")
