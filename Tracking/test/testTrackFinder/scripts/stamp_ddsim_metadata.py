#!/usr/bin/env python3
import argparse, json, os, sys, time, subprocess, hashlib

def try_cmd(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
    except Exception:
        return None

def sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def read_text(path, limit_bytes=2_000_000):
    # steering XML can be large; store first N bytes + hash
    try:
        with open(path, "rb") as f:
            data = f.read(limit_bytes)
        text = data.decode("utf-8", errors="replace")
        truncated = os.path.getsize(path) > limit_bytes
        return text, truncated
    except Exception as e:
        return f"<<failed to read: {e}>>", False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Local EDM4hep ROOT file to stamp (UPDATE)")
    ap.add_argument("--params-json", required=True, help="Per-job params JSON")
    ap.add_argument("--compact-xml", required=True, help="Compact XML path/file actually used on worker")
    ap.add_argument("--cmd", required=True, help="Full ddsim command line (string)")
    ap.add_argument("--theta-min", required=True)
    ap.add_argument("--theta-max", required=True)
    ap.add_argument("--phi-opts", default="", help="phi options (string)")
    ap.add_argument("--out-eos", default="", help="EOS_POSIX target")
    ap.add_argument("--out-url", default="", help="EOS_URL target")
    ap.add_argument("--k4-release", default="", help="Key4HEP release tag you sourced")
    ap.add_argument("--job-extra", action="append", default=[], help="Extra key=val pairs (repeatable)")
    args = ap.parse_args()

    # Load params JSON (ground truth of grid)
    try:
        with open(args.params_json, "r", encoding="utf-8") as f:
            params = json.load(f)
    except Exception as e:
        params = {"__error__": f"failed to read params json: {e}"}

    # Compact XML content (truncated) + hash
    compact_txt, compact_trunc = read_text(args.compact_xml)
    compact_sha = sha256_file(args.compact_xml)

    # extras k=v
    extra = {}
    for kv in args.job_extra:
        if "=" in kv:
            k, v = kv.split("=", 1)
            extra[k.strip()] = v.strip()

    payload = {
        "component": "ddsim_provenance_stamp",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),

        # Core provenance
        "ddsim_cmd": args.cmd,
        "params": params,
        "resolved_runtime": {
            "theta_min_rad": args.theta_min,
            "theta_max_rad": args.theta_max,
            "phi_opts": args.phi_opts,
        },

        # Geometry provenance
        "compact_xml": {
            "path": os.path.abspath(args.compact_xml),
            "sha256": compact_sha,
            "contents_truncated": bool(compact_trunc),
            "contents_head": compact_txt,
        },

        # Output targets
        "outputs": {
            "local_root": os.path.abspath(args.root),
            "eos_posix": args.out_eos,
            "eos_url": args.out_url,
        },

        # Environment breadcrumbs (best-effort)
        "env": {
            "hostname": try_cmd(["hostname"]),
            "whoami": try_cmd(["whoami"]),
            "pwd": os.getcwd(),
            "K4PROJECT": os.environ.get("K4PROJECT"),
            "K4VERSION": os.environ.get("K4VERSION"),
            "KEY4HEP_STACK": os.environ.get("KEY4HEP_STACK"),
            "CMTCONFIG": os.environ.get("CMTCONFIG"),
            "BINARY_TAG": os.environ.get("BINARY_TAG"),
            "CONDOR_JOB_AD": os.environ.get("_CONDOR_JOB_AD"),
            "k4_release": args.k4_release,
        },

        "versions": {
            "ddsim_path": try_cmd(["bash", "-lc", "command -v ddsim"]),
            "ddsim_version": try_cmd(["bash", "-lc", "ddsim --version"]),
            "python": sys.version.split()[0],
            "root": try_cmd(["bash", "-lc", "root-config --version"]),
        },

        "extra": extra,
    }

    js = json.dumps(payload, indent=2, sort_keys=True)

    import ROOT  # noqa
    f = ROOT.TFile.Open(args.root, "UPDATE")
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open ROOT file for UPDATE: {args.root}")

    # Store the full JSON blob
    ROOT.TObjString(js).Write("ddsim_metadata_json", ROOT.TObject.kOverwrite)

    # Small convenience keys for fast grepping without parsing JSON
    ROOT.TNamed("ddsim_cmd", args.cmd).Write("ddsim_cmd", ROOT.TObject.kOverwrite)
    ROOT.TNamed("compact_xml_sha256", compact_sha or "").Write("compact_xml_sha256", ROOT.TObject.kOverwrite)

    f.Close()
    print(f"[OK] stamped ddsim provenance into {args.root} as key 'ddsim_metadata_json'")

if __name__ == "__main__":
    main()
