#!/usr/bin/env python3
"""
tools/compile_config.py

Generates and compiles YAML configuration for the k4RecTracker repo.

You said:
- Repo root is /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker
- Put tools/ and config/ inside that directory
- Only two modules: Tracking and DCHdigi
- Seed script: Tracking/test/testTrackFinder/local_chain.sh
- FULL by default (scan all .cpp + .py under modules)
- No explicit DCHdigi "entrypoint" (still scan and generate config)

This script supports:
  1) sub  : generate/update module YAMLs
            - Tracking/config_Tracking.yaml
            - DCHdigi/config_DCHdigi.yaml
            - also ensures config/main.yaml exists (portable)
  2) main : compile config/compiled.yaml from config/main.yaml + module YAMLs

It also injects paths.eos_base in compiled.yaml by default (computed from $USER).
You can add more injected defaults later in INJECT_DEFAULTS.

Usage (run from repo root):
  python3 tools/compile_config.py sub
  python3 tools/compile_config.py main
  python3 tools/compile_config.py sub --root /afs/.../k4RecTracker
  python3 tools/compile_config.py main --root /afs/.../k4RecTracker
"""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import yaml


# -----------------------------
# Repo constants (customize here)
# -----------------------------
MODULES = ["Tracking", "DCHdigi"]
SEED_LOCAL_CHAIN = Path("Tracking/test/testTrackFinder/local_chain.sh")

CONFIG_DIRNAME = "config"
TOOLS_DIRNAME = "tools"

TRACKING_CONFIG_NAME = "config_Tracking.yaml"
DCHDIGI_CONFIG_NAME = "config_DCHdigi.yaml"

# directories to skip while scanning
SKIP_DIRS = {
    ".git", "build", "install", ".cache", "work", "logs", "output",
    "third_party", "venv", "__pycache__", ".pytest_cache", "cmake-build-debug",
}

# Injected defaults for compiled config (easy to extend later)
# Key is dot-path; value is computed at runtime (see inject_defaults()).
INJECT_DEFAULTS = {
    "paths.eos_base": "__AUTO_EOS_BASE__",
}


# -----------------------------
# YAML helpers
# -----------------------------
def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def dump_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            sort_keys=False,
            default_flow_style=False,
            width=120,
            allow_unicode=True,
        )


def deep_merge_preserve_values(existing: Dict[str, Any], generated: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge generated -> existing, but preserve user overrides where it makes sense:
      - If a leaf dict has a 'value' key, keep existing['value'] if present.
      - Otherwise, generated wins for scalars; recurse for dicts.
    """
    if not isinstance(existing, dict) or not isinstance(generated, dict):
        return generated

    out = dict(existing)
    for k, gv in generated.items():
        if k not in out:
            out[k] = gv
            continue

        ev = out[k]

        if isinstance(ev, dict) and isinstance(gv, dict):
            # If this object looks like a configurable item, preserve 'value'
            if "value" in gv and "default" in gv:
                merged = dict(gv)
                if "value" in ev:
                    merged["value"] = ev["value"]
                out[k] = deep_merge_preserve_values(ev, merged)
            else:
                out[k] = deep_merge_preserve_values(ev, gv)
        else:
            # keep existing for scalars only if it was explicitly set as a user override?
            # In general, prefer generated for metadata, but let users edit top-level if they want.
            out[k] = gv

    return out


# -----------------------------
# Injected defaults
# -----------------------------
def auto_eos_base() -> str:
    user = (os.environ.get("USER") or "").strip()
    if not user:
        return "/eos/user/unknown/unknown"
    return f"/eos/user/{user[0]}/{user}"


def set_dotpath(d: Dict[str, Any], dotpath: str, value: Any) -> None:
    parts = dotpath.split(".")
    cur = d
    for p in parts[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def get_dotpath(d: Dict[str, Any], dotpath: str) -> Any:
    parts = dotpath.split(".")
    cur: Any = d
    for p in parts:
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def inject_defaults(cfg: Dict[str, Any]) -> None:
    for k, v in INJECT_DEFAULTS.items():
        if get_dotpath(cfg, k) is not None:
            continue
        if v == "__AUTO_EOS_BASE__":
            set_dotpath(cfg, k, auto_eos_base())
        else:
            set_dotpath(cfg, k, v)


# -----------------------------
# Scan helpers
# -----------------------------
def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def list_files(root: Path, exts: Tuple[str, ...]) -> List[Path]:
    out: List[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in exts and not should_skip(p):
            out.append(p)
    return sorted(out)


# -----------------------------
# Parse local_chain.sh (seed)
# -----------------------------
RE_DEFAULT = re.compile(r'^\s*DEFAULT_([A-Z0-9_]+)\s*=\s*"([^"]*)"\s*$')
RE_POS = re.compile(r'^\s*([A-Z0-9_]+)\s*=\s*"\$\{(\d+):-\$(DEFAULT_[A-Z0-9_]+)\}"\s*$')
RE_COLON_DEFAULT = re.compile(r'^\s*:\s*"\$\{([A-Z0-9_]+):=([^}]*)\}"\s*$')

RE_K4_ARGS_START = re.compile(r'^\s*K4_ARGS=\(\s*$')
RE_K4_ARGS_END = re.compile(r'^\s*\)\s*$')
RE_FLAG_VAR = re.compile(r'(--[A-Za-z0-9_.-]+)\s+"?\$([A-Za-z0-9_]+)"?')

RE_IF_TOGGLE = re.compile(r'^\s*if\s+\[\[\s*"\$([A-Za-z0-9_]+)"\s*==\s*"1"\s*\]\];\s*then\s*$')
RE_K4_APPEND = re.compile(r'^\s*K4_ARGS\+\=\(\s*([^)]+)\s*\)\s*$')
RE_ELSE = re.compile(r'^\s*else\s*$')
RE_FI = re.compile(r'^\s*fi\s*$')


def _strip_quotes(x: str) -> str:
    x = x.strip()
    if (x.startswith('"') and x.endswith('"')) or (x.startswith("'") and x.endswith("'")):
        return x[1:-1]
    return x


def parse_local_chain(seed_path: Path) -> Dict[str, Any]:
    lines = seed_path.read_text(encoding="utf-8", errors="replace").splitlines()

    defaults: Dict[str, str] = {}
    positional: Dict[str, Any] = {}
    env: Dict[str, Any] = {}
    args_map: Dict[str, str] = {}
    toggles: Dict[str, Any] = {}

    # Pass 1: DEFAULT_* and positional and : "${X:=...}"
    for line in lines:
        m = RE_DEFAULT.match(line)
        if m:
            defaults[m.group(1)] = m.group(2)
            continue

        m = RE_POS.match(line)
        if m:
            var = m.group(1)
            idx = int(m.group(2))
            defsym = m.group(3)
            defname = defsym.replace("DEFAULT_", "", 1)
            positional[var] = {"index": idx, "default_from": defname, "default": None}
            continue

        m = RE_COLON_DEFAULT.match(line)
        if m:
            var = m.group(1)
            raw_default = _strip_quotes(m.group(2).strip())
            env[var] = {"default": raw_default, "value": raw_default}
            continue

    # Resolve positional defaults from DEFAULT_*
    for var, info in positional.items():
        defkey = info.get("default_from")
        if defkey and defkey in defaults:
            info["default"] = defaults[defkey]
            info["value"] = defaults[defkey]
        else:
            info["default"] = None
            info["value"] = None

    # Pass 2: parse K4_ARGS block for flag -> $VAR mapping
    in_k4 = False
    for line in lines:
        if RE_K4_ARGS_START.match(line):
            in_k4 = True
            continue
        if in_k4 and RE_K4_ARGS_END.match(line):
            in_k4 = False
            continue
        if not in_k4:
            continue

        s = line.strip()
        if not s or s.startswith("#"):
            continue

        for m in RE_FLAG_VAR.finditer(s):
            flag = m.group(1)
            var = m.group(2)
            args_map[flag] = f"${var}"

    # Pass 3: parse toggle blocks
    i = 0
    while i < len(lines):
        m = RE_IF_TOGGLE.match(lines[i])
        if not m:
            i += 1
            continue
        knob = m.group(1)
        i += 1
        then_flags: List[str] = []
        else_flags: List[str] = []
        mode = "then"
        while i < len(lines):
            l = lines[i]
            if RE_ELSE.match(l):
                mode = "else"
                i += 1
                continue
            if RE_FI.match(l):
                i += 1
                break
            am = RE_K4_APPEND.match(l)
            if am:
                toks = am.group(1).strip()
                flags = [t for t in toks.split() if t.startswith("--")]
                if mode == "then":
                    then_flags.extend(flags)
                else:
                    else_flags.extend(flags)
            i += 1
        if then_flags or else_flags:
            toggles[knob] = {"when_1": then_flags, "when_0": else_flags}

    return {
        "__meta__": {
            "seed_script": str(seed_path),
        },
        "seed": {
            "defaults": defaults,
            "positional": positional,
            "env": env,
            "pipeline": {
                "k4_entry": "./runDCHTestTrackFinder.py",
                "args_map": dict(sorted(args_map.items())),
                "toggles": toggles,
            },
        }
    }


def route_seed_to_modules(seed: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Route seed env vars into Tracking vs DCHdigi based on prefix:
      - DCH_* -> DCHdigi
      - everything else in seed env (GF_*, GGTF_*, STAGE, etc.) -> Tracking
    Positional args and defaults remain in Tracking by default (since local_chain is Tracking pipeline driver).
    """
    tracking = {"seed": {"positional": {}, "env": {}, "pipeline": {}, "defaults": {}}}
    dchdigi = {"seed": {"positional": {}, "env": {}, "pipeline": {}, "defaults": {}}}

    s = seed.get("seed", {})
    tracking["seed"]["defaults"] = s.get("defaults", {})
    tracking["seed"]["positional"] = s.get("positional", {})
    tracking["seed"]["pipeline"] = s.get("pipeline", {})

    env = s.get("env", {})
    for k, v in env.items():
        if k.startswith("DCH_"):
            dchdigi["seed"]["env"][k] = v
        else:
            tracking["seed"]["env"][k] = v

    return {"Tracking": tracking, "DCHdigi": dchdigi}


# -----------------------------
# Parse C++ Gaudi::Property
# -----------------------------
RE_GAUDI_PROP = re.compile(
    r'Gaudi::Property\s*<\s*([^>]+)\s*>\s+\w+\s*\{\s*'
    r'this\s*,\s*"([^"]+)"\s*,\s*([^,]+)\s*,\s*"([^"]*)"\s*\}\s*;',
    re.MULTILINE
)

def scan_cpp_gaudi_properties(module_dir: Path) -> Dict[str, Any]:
    props: Dict[str, Any] = {}
    for cpp in list_files(module_dir, (".cpp", ".cc", ".cxx", ".h", ".hpp")):
        txt = cpp.read_text(encoding="utf-8", errors="replace")
        matches = list(RE_GAUDI_PROP.finditer(txt))
        if not matches:
            continue
        rel = str(cpp.relative_to(module_dir))
        props.setdefault(rel, {})
        for m in matches:
            typ = m.group(1).strip()
            name = m.group(2).strip()
            default_raw = m.group(3).strip()
            help_str = m.group(4).strip()

            # keep default_raw as string; don't over-parse (floats like 1e-4 are fine as string too)
            item = {
                "type": typ,
                "default": default_raw,
                "value": default_raw,
                "help": help_str,
            }
            props[rel][name] = item
    return props


# -----------------------------
# Parse Python argparse add_argument (best-effort)
# -----------------------------
RE_ADD_ARG = re.compile(r'\.add_argument\((.*?)\)\s*', re.DOTALL)

def _parse_argparse_call(argstr: str) -> Optional[Dict[str, Any]]:
    """
    Very lightweight parser for typical patterns:
      ap.add_argument("--foo", required=True, default=..., action="store_true", help="...")
    Returns dict with flags, dest, required, default, action, help.
    """
    # Remove newlines and collapse spaces
    s = " ".join(argstr.replace("\n", " ").split())

    # Extract quoted string args that look like flags ("--x" or "-x")
    flags = re.findall(r'["\'](-{1,2}[A-Za-z0-9][A-Za-z0-9_-]*)["\']', s)
    if not flags:
        return None

    # kwargs (best-effort)
    def kw_bool(key: str) -> Optional[bool]:
        m = re.search(rf'\b{re.escape(key)}\s*=\s*(True|False)\b', s)
        return None if not m else (m.group(1) == "True")

    def kw_str(key: str) -> Optional[str]:
        m = re.search(rf'\b{re.escape(key)}\s*=\s*["\']([^"\']*)["\']', s)
        return None if not m else m.group(1)

    def kw_default() -> Optional[str]:
        # literal default=...
        m = re.search(r'\bdefault\s*=\s*([^,\)]+)', s)
        return None if not m else m.group(1).strip()

    required = kw_bool("required")
    action = kw_str("action")
    help_s = kw_str("help")
    default_raw = kw_default()

    # Determine dest: if user passes dest="x", else infer from longest flag --foo-bar -> foo_bar
    dest = kw_str("dest")
    if not dest:
        long = next((f for f in flags if f.startswith("--")), flags[0])
        dest = long.lstrip("-").replace("-", "_")

    # store_true/false default heuristics
    if action in ("store_true", "store_false") and default_raw is None:
        default_raw = "False" if action == "store_true" else "True"

    return {
        "flags": flags,
        "dest": dest,
        "required": required if required is not None else False,
        "action": action,
        "default": default_raw,
        "value": default_raw,
        "help": help_s,
    }


def scan_py_argparse(module_dir: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for py in list_files(module_dir, (".py",)):
        txt = py.read_text(encoding="utf-8", errors="replace")
        calls = RE_ADD_ARG.findall(txt)
        if not calls:
            continue
        items: Dict[str, Any] = {}
        for call in calls:
            parsed = _parse_argparse_call(call)
            if not parsed:
                continue
            # Use dest as key
            items[parsed["dest"]] = parsed
        if items:
            rel = str(py.relative_to(module_dir))
            out[rel] = items
    return out


# -----------------------------
# Module YAML generation
# -----------------------------
def generate_module_yaml(
    repo_root: Path,
    module_name: str,
    seed_routed: Dict[str, Any],
) -> Dict[str, Any]:
    module_dir = repo_root / module_name
    cpp_props = scan_cpp_gaudi_properties(module_dir)
    py_args = scan_py_argparse(module_dir)

    cfg: Dict[str, Any] = {
        "__meta__": {
            "module": module_name,
            "generated_by": "compile_config.py sub",
        },
        # seed (from local_chain.sh) routed to this module
        **seed_routed,
        # full scans
        "cpp_properties": cpp_props,
        "argparse": py_args,
    }
    return cfg


def ensure_main_yaml(repo_root: Path) -> None:
    config_dir = repo_root / CONFIG_DIRNAME
    main_yaml = config_dir / "main.yaml"
    if main_yaml.exists():
        return

    # Portable main.yaml (no machine-specific paths hardcoded)
    data = {
        "__meta__": {
            "generated_by": "compile_config.py sub (bootstrap)",
        },
        "run": {
            "tag": "dev",
            "events": 100,
            "seed": 12345,
        },
        "paths": {
            # intentionally minimal; compiled.yaml will inject eos_base
        },
        "notes": [
            "Edit module configs (Tracking/config_Tracking.yaml, DCHdigi/config_DCHdigi.yaml) to change knobs.",
            "Run `python3 tools/compile_config.py main` to regenerate config/compiled.yaml.",
        ],
    }
    dump_yaml(main_yaml, data)
    print(f"[sub] created {main_yaml}")


def write_module_yaml(repo_root: Path, module_name: str, filename: str, generated: Dict[str, Any]) -> None:
    module_dir = repo_root / module_name
    out_yaml = module_dir / filename
    existing = load_yaml(out_yaml)
    merged = deep_merge_preserve_values(existing, generated)
    dump_yaml(out_yaml, merged)
    print(f"[sub] wrote {out_yaml}")


# -----------------------------
# Main compilation
# -----------------------------
def compile_main(repo_root: Path) -> None:
    config_dir = repo_root / CONFIG_DIRNAME
    main_yaml = config_dir / "main.yaml"
    compiled_yaml = config_dir / "compiled.yaml"

    cfg = load_yaml(main_yaml)
    inject_defaults(cfg)

    modules: Dict[str, Any] = {}
    # known locations for module configs
    tracking_cfg = load_yaml(repo_root / "Tracking" / TRACKING_CONFIG_NAME)
    dchdigi_cfg = load_yaml(repo_root / "DCHdigi" / DCHDIGI_CONFIG_NAME)

    if tracking_cfg:
        modules["Tracking"] = tracking_cfg
    if dchdigi_cfg:
        modules["DCHdigi"] = dchdigi_cfg

    cfg["modules"] = modules
    dump_yaml(compiled_yaml, cfg)
    print(f"[main] wrote {compiled_yaml}")


# -----------------------------
# CLI
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["sub", "main"], help="sub: generate module yamls; main: compile config/compiled.yaml")
    ap.add_argument("--root", default=".", help="k4RecTracker repo root (default: .)")
    ap.add_argument("--seed", default=str(SEED_LOCAL_CHAIN), help="Seed bash script (default: Tracking/test/testTrackFinder/local_chain.sh)")
    args = ap.parse_args()

    repo_root = Path(args.root).resolve()

    if args.mode == "sub":
        ensure_main_yaml(repo_root)

        seed_path = (repo_root / args.seed).resolve()
        if not seed_path.exists():
            raise SystemExit(f"[sub] ERROR: seed script not found: {seed_path}")

        seed = parse_local_chain(seed_path)
        routed = route_seed_to_modules(seed)

        # Generate and write module configs
        tracking_gen = generate_module_yaml(repo_root, "Tracking", routed.get("Tracking", {}))
        dchdigi_gen = generate_module_yaml(repo_root, "DCHdigi", routed.get("DCHdigi", {}))

        write_module_yaml(repo_root, "Tracking", TRACKING_CONFIG_NAME, tracking_gen)
        write_module_yaml(repo_root, "DCHdigi", DCHDIGI_CONFIG_NAME, dchdigi_gen)

        # Also compile main by default? (I’m leaving it manual; run mode=main when desired)
        print("[sub] Done. Now run: python3 tools/compile_config.py main")

    else:
        compile_main(repo_root)


if __name__ == "__main__":
    main()
