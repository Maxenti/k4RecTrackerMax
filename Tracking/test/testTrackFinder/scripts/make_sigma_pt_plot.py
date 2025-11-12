#!/usr/bin/env python3
import os, re, math, numpy as np, ROOT, sys
ROOT.gErrorIgnoreLevel = 3001

def parse_truth_pt(path):
    m = re.search(r"_pt([0-9.]+)\.root$", os.path.basename(path))
    return float(m.group(1)) if m else None

def bind_vec(reader, name, types):
    """
    Try binding ROOT TTreeReaderValue('vector<type>') for the given branch.
    `types` is a list like ['unsigned int','ULong64_t'] tried in order.
    Returns the bound TTreeReaderValue or None if not found.
    """
    for t in types:
        try:
            v = ROOT.TTreeReaderValue(f"vector<{t}>")(reader, name)
            # touch once to force creation
            _ = v.GetSize() if hasattr(v, "GetSize") else 0
            return v
        except Exception:
            continue
    return None

def get_state_handles(t, coll="GenFitTracks"):
    names = {b.GetName() for b in t.GetListOfBranches()}

    offs_name = f"_{coll}_trackStates"
    if offs_name not in names:
        raise RuntimeError(f"Missing offset table: {offs_name}")

    r = ROOT.TTreeReader(t)

    # offsets: vector<unsigned int> (podio uses uint32), sometimes uint64
    offs = bind_vec(r, offs_name, ["unsigned int","ULong64_t","ULong_t","size_t","UInt_t"])
    if offs is None:
        raise RuntimeError(f"Cannot bind offsets vector: {offs_name}")

    # state arrays are vector<float>
    def vfloat(field):
        nm = f"{coll}_trackStates_{field}"
        if nm not in names:
            return None
        v = bind_vec(r, nm, ["float"])
        return v

    omega     = vfloat("omega")
    tanLambda = vfloat("tanLambda")
    qOverP    = vfloat("qOverP")
    theta     = vfloat("theta")

    mode = None
    if omega is not None:
        mode = "helix"  # omega (=q/pT) present; tanLambda optional
    elif (qOverP is not None) and (theta is not None):
        mode = "qoverp_theta"
    else:
        raise RuntimeError("No usable state params found (need omega or qOverP+theta)")

    return r, offs, {"omega": omega, "tanLambda": tanLambda, "qOverP": qOverP, "theta": theta}, mode

def pt_from_state(mode, arrays, idx):
    if mode == "helix":
        omega_val = float(arrays["omega"].Get()[idx])
        if omega_val == 0 or not math.isfinite(omega_val):
            return None
        # omega ≈ q/pT  (sign from q; magnitude is 1/pT)
        return abs(1.0/omega_val)
    else:
        qop = float(arrays["qOverP"].Get()[idx])
        th  = float(arrays["theta"].Get()[idx])
        if qop == 0 or not (math.isfinite(qop) and math.isfinite(th)):
            return None
        p = abs(1.0/qop)
        return p*math.sin(th)

def collect_track_pt(path, coll="GenFitTracks"):
    f = ROOT.TFile.Open(path)
    if not f or f.IsZombie():
        raise OSError(f"cannot open {path}")
    t = f.Get("events")
    if not t:
        raise OSError("no 'events' tree")

    r, offs, arrs, mode = get_state_handles(t, coll)

    pts = []
    # Loop events; per event the arrays and offsets are re-filled
    while r.Next():
        o = offs.Get()
        n_off = o.size()
        if n_off <= 1:
            continue

        # We assume at least one of the arrays is present by mode
        # Take the FIRST state in each track's slice [a,b)
        for ti in range(n_off - 1):
            a = int(o[ti])
            b = int(o[ti+1])
            if b > a:
                pt = pt_from_state(mode, arrs, a)
                if pt is not None and math.isfinite(pt):
                    pts.append(pt)

    f.Close()
    return pts

def robust_sigma_rel_pt(pts, pt_true):
    if not pts:
        return math.nan
    a = np.asarray(pts, float)
    med = np.median(a)
    mad = 1.4826*np.median(np.abs(a - med))
    sel = a[np.abs(a - med) < 3.0*mad] if mad > 0 else a
    if sel.size < 10:
        sel = a
    rel = (sel - pt_true)/pt_true
    if rel.size < 5:
        return math.nan
    return float(np.std(rel, ddof=1))

def main():
    if len(sys.argv) < 3:
        print("usage: make_sigma_pt_plot.py <filelist.txt> --out fig.png [--coll GenFitTracks]")
        sys.exit(1)
    filelist = sys.argv[1]
    out = "sigma_pt_over_pt.png"
    coll = "GenFitTracks"
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--out":
            out = sys.argv[i+1]; i += 2; continue
        if sys.argv[i] == "--coll":
            coll = sys.argv[i+1]; i += 2; continue
        i += 1

    files = [l.strip() for l in open(filelist) if l.strip()]
    xs, ys = [], []
    skipped = []

    for fpath in files:
        pt_true = parse_truth_pt(fpath)
        if pt_true is None:
            skipped.append(("no-pt", fpath)); continue
        try:
            rec_pts = collect_track_pt(fpath, coll=coll)
        except Exception as e:
            skipped.append((f"read-fail: {e}", fpath)); continue
        s = robust_sigma_rel_pt(rec_pts, pt_true)
        if math.isfinite(s):
            xs.append(pt_true); ys.append(s)

    import matplotlib.pyplot as plt
    plt.figure()
    plt.loglog(xs, ys, "o", label="per file")
    plt.grid(True, which="both")
    plt.xlabel(r"$p_T^\mathrm{truth}$ [GeV]")
    plt.ylabel(r"$\sigma(p_T)/p_T$")
    plt.tight_layout()
    plt.legend()
    plt.savefig(out, dpi=200)
    print(f"[ok] saved {out}")

    if skipped:
        print("\n[warn] Some files were skipped:")
        for why, fp in skipped[:25]:
            print(f"  - {why} : {fp}")
        if len(skipped) > 25:
            print(f"  (+{len(skipped)-25} more)")

if __name__ == "__main__":
    main()
