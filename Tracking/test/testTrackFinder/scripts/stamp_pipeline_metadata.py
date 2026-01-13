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
    try:
        with open(path, "rb") as f:
            data = f.read(limit_bytes)
        text = data.decode("utf-8", errors="replace")
        truncated = os.path.getsize(path) > limit_bytes
        return text, truncated
    except Exception as e:
        return f"<<failed to read: {e}>>", False

def git_info(path):
    # best-effort git context for whatever directory contains your chain
    def g(cmd):
        return try_cmd(["bash", "-lc", f"cd {json.dumps(path)} && {cmd}"])
    return {
        "repo_root": g("git rev-parse --show-toplevel"),
        "commit": g("git rev-parse HEAD"),
        "branch": g("git rev-parse --abbrev-ref HEAD"),
        "status_porcelain": g("git status --porcelain"),
        "remote": g("git remote -v"),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="ROOT file to stamp (UPDATE)")
    ap.add_argument("--stage", required=True, help="stage name: ddsim|digi|ggtf|fit|analysis|...")
    ap.add_argument("--cmd", required=True, help="command line used (string)")
    ap.add_argument("--config", action="append", default=[], help="Config file paths to embed head+sha (repeatable)")
    ap.add_argument("--input", action="append", default=[], help="Input file paths (repeatable)")
    ap.add_argument("--extra", action="append", default=[], help="extra key=val (repeatable)")
    ap.add_argument("--workdir", default=".", help="directory to use for git info")
    ap.add_argument("--key", default="pipeline_metadata_json", help="ROOT key name")
    args = ap.parse_args()

    extra = {}
    for kv in args.extra:
        if "=" in kv:
            k, v = kv.split("=", 1)
            extra[k.strip()] = v.strip()

    config_blobs = []
    for p in args.config:
        p_abs = os.path.abspath(p)
        txt, trunc = read_text(p_abs)
        config_blobs.append({
            "path": p_abs,
            "sha256": sha256_file(p_abs),
            "contents_truncated": bool(trunc),
            "contents_head": txt,
        })

    inputs = []
    for p in args.input:
        p_abs = os.path.abspath(p)
        inputs.append({
            "path": p_abs,
            "sha256": sha256_file(p_abs),
            "size_bytes": os.path.getsize(p_abs) if os.path.exists(p_abs) else None,
        })

    payload = {
        "component": "pipeline_provenance_stamp",
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stage": args.stage,
        "cmd": args.cmd,
        "inputs": inputs,
        "configs": config_blobs,
        "env": {
            "hostname": try_cmd(["hostname"]),
            "whoami": try_cmd(["whoami"]),
            "pwd": os.getcwd(),
            "K4PROJECT": os.environ.get("K4PROJECT"),
            "K4VERSION": os.environ.get("K4VERSION"),
            "KEY4HEP_STACK": os.environ.get("KEY4HEP_STACK"),
            "CMTCONFIG": os.environ.get("CMTCONFIG"),
            "BINARY_TAG": os.environ.get("BINARY_TAG"),
        },
        "versions": {
            "python": sys.version.split()[0],
            "root": try_cmd(["bash", "-lc", "root-config --version"]),
            "k4run": try_cmd(["bash", "-lc", "command -v k4run"]),
            "ddsim": try_cmd(["bash", "-lc", "command -v ddsim"]),
        },
        "git": git_info(args.workdir),
        "extra": extra,
    }

    js = json.dumps(payload, indent=2, sort_keys=True)

    import ROOT  # noqa
    f = ROOT.TFile.Open(args.root, "UPDATE")
    if not f or f.IsZombie():
        raise RuntimeError(f"Could not open ROOT file for UPDATE: {args.root}")

    ROOT.TObjString(js).Write(args.key, ROOT.TObject.kOverwrite)
    ROOT.TNamed("pipeline_stage", args.stage).Write("pipeline_stage", ROOT.TObject.kOverwrite)
    ROOT.TNamed("pipeline_cmd", args.cmd).Write("pipeline_cmd", ROOT.TObject.kOverwrite)
    f.Close()
    print(f"[OK] stamped {args.stage} provenance into {args.root} as key '{args.key}'")

if __name__ == "__main__":
    main()
