#!/usr/bin/env python3

"""
DOC
Summary: Stamp general pipeline-stage provenance into a ROOT output file as a JSON payload plus convenience ROOT keys.
Status: secondary
Usage:
  python3 scripts/stamp_pipeline_metadata.py --root OUTPUT.root --stage fit --cmd "k4run ..." --input INPUT.root --config CONFIG.xml --config model.onnx
Examples:
  python3 scripts/stamp_pipeline_metadata.py \
    --root reco_gun_eta+1.00_pt14.142.root \
    --stage final \
    --cmd "k4run runtime/runDCHTestTrackFinder.py --inputFile ... --stage fit ..." \
    --input root://eosuser.cern.ch///eos/.../gun_eta+1.00_pt14.142.root \
    --config geom/IDEA_variant.xml \
    --config runtime/models/model.onnx \
    --config runtime/runDCHTestTrackFinder.py \
    --workdir . \
    --key pipeline_metadata_json \
    --extra condor_job=1 \
    --extra k4rel=2026-01-11
Inputs: ROOT file opened in UPDATE mode, stage label, command string, optional input paths, optional config paths, optional extra key=value metadata, and a working directory for git context.
Outputs: ROOT key pipeline_metadata_json or the requested --key containing full JSON provenance; convenience keys pipeline_stage and pipeline_cmd.
Collections: None; writes top-level ROOT metadata objects rather than EDM4hep event collections.
Connects-To: scripts/reco_job.sh, steering/local_chain.sh, scripts/print_metadata.py, scripts/analyze_pt_resolution_grid.py, downstream closeout/reproducibility checks
Arguments:
  --root: ROOT file to update with provenance metadata.
  --stage: pipeline stage label, such as ddsim, digi, ggtf, fit, final, or analysis.
  --cmd: command line used to produce the file.
  --config: config or steering file to hash and embed; may be repeated.
  --input: input file path to hash and record; may be repeated.
  --extra: additional key=value metadata entry; may be repeated.
  --workdir: directory used for best-effort git repository context; default current directory.
  --key: ROOT key name for the JSON payload; default pipeline_metadata_json.
Notes:
  This script is the general reco/pipeline provenance stamper, complementary to stamp_ddsim_metadata.py for DDSim gun production.
  The JSON payload records stage, command, input file hashes/sizes, config file hashes/content heads, environment breadcrumbs, tool versions, git branch/commit/status/remote, and arbitrary extras.
  Config contents are stored only up to a size limit and accompanied by SHA256 hashes to keep the ROOT file size controlled.
  Input paths that are not local files may have null size/hash values; the path is still recorded for reproducibility.
  Worker wrappers treat stamping as non-fatal so provenance failures do not hide actual reco success/failure.
  Use print_metadata.py or ROOT key inspection to verify the stored payload.
Tags: secondary, metadata, provenance, root, reco, k4run, condor, reproducibility, key4hep
DOC_END
"""



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
