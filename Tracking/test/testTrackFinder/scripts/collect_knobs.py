#!/usr/bin/env python3
"""
DOC
Summary: WIP utility that scans Python argparse knobs and C++ Gaudi::Property declarations and exports a normalized knob inventory for future pipeline/config automation.
Status: secondary
Usage:
  python3 scripts/collect_knobs.py --root . --out configs/auto_knobs.yaml --format yaml --verbose
  python3 scripts/collect_knobs.py --root . --out configs/auto_knobs.json --format json --include-ext .py .cpp .h .hpp
Examples:
  python3 scripts/collect_knobs.py \
    --root . \
    --include-ext .py .cpp .h .hpp \
    --out configs/auto_knobs.yaml \
    --format yaml \
    --exports configs/auto_knob_exports.sh \
    --export-prefix gf_ ggtf_ dch_ \
    --verbose
Inputs: Repository or workflow subtree containing Python scripts with parser.add_argument(...) calls and C++ headers/sources with Gaudi::Property<T> declarations.
Outputs: YAML or JSON knob inventory with flat and grouped views; optional exports.sh file containing environment-variable defaults for selected knob prefixes.
Collections: None; this is a static source/config introspection utility, not an EDM4hep/ROOT event processor.
Connects-To: steering/runDCHTestTrackFinder.py, steering/local_chain.sh, scripts/reco_job.sh, Tracking/components/GGTF_tracking.cpp, Tracking/components/GenFit2DCHFitter.cpp, configs/auto_knobs.yaml
Arguments:
  --root: directory tree to scan.
  --out: output YAML/JSON config path.
  --format: output format, yaml or json; inferred from --out extension when omitted.
  --include-ext: file extensions to scan; default .py .cpp .h .hpp.
  --exclude-dir: directory names pruned from scan; default excludes .git, build, install, __pycache__, .condor, and cmake-build.
  --keep-first: duplicate policy that keeps the first encountered knob name; default behavior.
  --keep-last: duplicate policy that replaces earlier knob metadata with the last encountered instance.
  --exports: optional output path for generated shell exports; empty disables export generation.
  --export-prefix: optional list of knob-name prefixes to include in exports.sh, such as gf_, ggtf_, dch_.
  --verbose: print scan/write diagnostics.
Notes:
  This script is explicitly WIP and should be treated as an exploratory maintenance helper, not an authoritative pipeline runner.
  The intended long-term use is to help audit and eventually unify knob surfaces across ddsim, DCH digitization, GGTF_tracking, GenFit2DCHFitter, local wrappers, and Condor wrappers.
  Python parsing is regex-based and intentionally limited to common parser.add_argument(...) patterns; it will not safely understand arbitrary AST/metaprogramming.
  C++ parsing is regex-based and focused on Gaudi::Property<T> declarations; custom property wrappers may require new patterns.
  Duplicate knob names are expected in this project because the same concept can appear in steering, local wrappers, worker wrappers, and C++ components. Review duplicate warnings before trusting generated configs.
  Generated auto_knobs.yaml/json should be considered a diagnostic inventory until the project explicitly adopts it as a config contract.
  Do not use this script to silently overwrite hand-maintained configs for production CF-vs-W or pT-resolution closeout campaigns.
Tags: secondary, wip, config-audit, knob-inventory, argparse, gaudi-property, automation, maintenance
DOC_END
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Optional YAML support
try:
    import yaml  # type: ignore
except Exception:
    yaml = None


# -----------------------------
# Data model
# -----------------------------
@dataclass
class Knob:
    name: str
    kind: str                 # "cli" or "property"
    lang: str                 # "python" or "cpp"
    type: str                 # "int", "float", "bool", "str", "list[str]", ...
    default: Optional[str]    # stored as string repr for robustness
    help: str
    source_file: str
    source_line: int
    raw: str                  # raw matched snippet


@dataclass
class Duplicate:
    name: str
    kept: Tuple[str, int]     # (file, line)
    dropped: Tuple[str, int]  # (file, line)


# -----------------------------
# Helpers
# -----------------------------
def warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def info(msg: str) -> None:
    print(f"[INFO] {msg}", file=sys.stderr)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return path.read_text(errors="replace")


def iter_files(root: Path, exts: List[str], exclude_dirs: List[str]) -> List[Path]:
    out: List[Path] = []
    exts = [e if e.startswith(".") else "." + e for e in exts]
    for dirpath, dirnames, filenames in os.walk(root):
        # prune excluded dirs
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs and not d.startswith(".")]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix in exts:
                out.append(p)
    return sorted(out)


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


def _guess_py_type(kwargs_blob: str) -> str:
    """
    Infer type from parser.add_argument(...) kwargs:
      type=float/int/str
      action="store_true"/"store_false" -> bool
      nargs='+' or '*' with type -> list[type]
    """
    # bool by action
    if re.search(r'action\s*=\s*["\']store_true["\']', kwargs_blob):
        return "bool"
    if re.search(r'action\s*=\s*["\']store_false["\']', kwargs_blob):
        return "bool"

    # explicit type
    m = re.search(r'\btype\s*=\s*([A-Za-z_][A-Za-z0-9_]*)', kwargs_blob)
    base = None
    if m:
        base = m.group(1)
        if base in ("int", "float", "str"):
            base = base
        else:
            # could be "pathlib.Path", custom callable, etc.
            base = "str"

    # nargs -> list
    if re.search(r'\bnargs\s*=\s*["\']?\+["\']?', kwargs_blob) or re.search(r'\bnargs\s*=\s*["\']?\*["\']?', kwargs_blob):
        if base is None:
            base = "str"
        return f"list[{base}]"

    return base or "str"


def _extract_py_default(kwargs_blob: str) -> Optional[str]:
    m = re.search(r'\bdefault\s*=\s*([^,\n\)]+)', kwargs_blob)
    if not m:
        return None
    return m.group(1).strip()


def _extract_py_help(kwargs_blob: str) -> str:
    # help="..." or help='...'
    m = re.search(r'\bhelp\s*=\s*(?P<q>["\'])(?P<txt>.*?)(?P=q)', kwargs_blob, flags=re.S)
    if m:
        return m.group("txt").replace("\n", " ").strip()
    return ""


def _guess_cpp_type(cpp_type: str) -> str:
    t = cpp_type.strip()
    # common gaudi types
    t = t.replace("std::string", "str").replace("Gaudi::StringKey", "str")
    t = t.replace("bool", "bool").replace("int", "int").replace("double", "float").replace("float", "float")
    # vectors
    if "vector" in t or "std::vector" in t:
        # best effort
        if "string" in t:
            return "list[str]"
        if "int" in t:
            return "list[int]"
        if "double" in t or "float" in t:
            return "list[float]"
        return "list[str]"
    if t in ("str", "bool", "int", "float"):
        return t
    # fallback
    return "str"


def _extract_cpp_default(default_blob: str) -> Optional[str]:
    default_blob = default_blob.strip()
    if default_blob == "":
        return None
    return default_blob


def _extract_cpp_doc(doc_blob: str) -> str:
    # doc is often the last arg "..."
    return _strip_quotes(doc_blob.strip()).replace("\n", " ").strip()


# -----------------------------
# Parsers
# -----------------------------
def parse_python_args(text: str, source_file: str) -> List[Knob]:
    """
    Regex scan for:
      parser.add_argument("..."/'...', ...)

    It also tries to capture:
      dest=...
      default=...
      type=...
      action=...
      help=...
    """
    knobs: List[Knob] = []

    # Match parser.add_argument(<args...>)
    # We capture the whole call body to parse name + kwargs roughly.
    call_re = re.compile(
        r'(?P<prefix>\bparser\s*\.\s*add_argument\s*\()\s*(?P<body>.*?)(?P<suffix>\)\s*)',
        re.S
    )

    # Match first positional string which is the flag ("--foo" or "-f")
    first_str_re = re.compile(r'^\s*(?P<q>["\'])(?P<flag>.*?)(?P=q)\s*(?:,|$)', re.S)

    # Match dest="name"
    dest_re = re.compile(r'\bdest\s*=\s*(?P<q>["\'])(?P<dest>.*?)(?P=q)')

    # We also want line numbers: approximate by counting newlines up to match start.
    for m in call_re.finditer(text):
        body = m.group("body")
        start_idx = m.start()
        line_no = text.count("\n", 0, start_idx) + 1

        # Extract first flag
        mflag = first_str_re.search(body)
        if not mflag:
            continue
        flag = mflag.group("flag")

        # Compute canonical knob name:
        # Prefer dest=..., else use the long flag --foo-bar -> foo_bar
        mdest = dest_re.search(body)
        if mdest:
            name = mdest.group("dest")
        else:
            if flag.startswith("--"):
                name = flag[2:]
            elif flag.startswith("-"):
                name = flag[1:]
            else:
                name = flag
            name = name.replace("-", "_")

        # kwargs blob is body after first positional chunk
        # (this is crude but works for typical add_argument usage)
        after = body[mflag.end():]

        ktype = _guess_py_type(after)
        kdefault = _extract_py_default(after)
        khelp = _extract_py_help(after)

        knobs.append(
            Knob(
                name=name,
                kind="cli",
                lang="python",
                type=ktype,
                default=kdefault,
                help=khelp,
                source_file=source_file,
                source_line=line_no,
                raw=f"parser.add_argument({body})",
            )
        )

    return knobs


def parse_cpp_gaudi_properties(text: str, source_file: str) -> List[Knob]:
    """
    Regex scan for common Gaudi property declarations, e.g.:

      Gaudi::Property<double> Bz{this, "Bz", 2.0, "Mag field"};
      Gaudi::Property<std::string> TGeoFile{this, "TGeoFile", "", "..."};
      Gaudi::Property<std::vector<std::string>> inputTracks{this, "inputTracks", {"A"}, "..."};

    We capture:
      - template type
      - property name string
      - default expression (best-effort)
      - doc string (best-effort)
    """
    knobs: List[Knob] = []

    # This covers Gaudi::Property<...> var{ this, "Prop", default, "doc" };
    prop_re = re.compile(
        r'Gaudi\s*::\s*Property\s*<\s*(?P<type>[^>]+?)\s*>\s*'
        r'(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*'
        r'\{\s*this\s*,\s*'
        r'(?P<q>["\'])(?P<pname>.*?)(?P=q)\s*'
        r'(?:,\s*(?P<default>.*?))?'
        r'(?:,\s*(?P<doc>(?P=q).*?))?'
        r'\s*\}\s*;',
        re.S
    )

    for m in prop_re.finditer(text):
        start_idx = m.start()
        line_no = text.count("\n", 0, start_idx) + 1

        ctype = m.group("type")
        pname = m.group("pname")
        default_blob = m.group("default") or ""
        doc_blob = m.group("doc") or ""

        ktype = _guess_cpp_type(ctype)

        # default/doc parsing: doc_blob may include quotes already; default_blob may include trailing parts
        # We try to split default/doc if doc didn't match cleanly.
        kdoc = ""
        kdefault = None

        # If doc_blob captured, it includes opening quote; extract inside quotes
        if doc_blob:
            q = m.group("q")
            dm = re.search(rf'{re.escape(q)}(.*?){re.escape(q)}', doc_blob, re.S)
            if dm:
                kdoc = dm.group(1).strip()

        # If default blob exists, strip trailing , "doc" etc if our doc capture failed
        if default_blob:
            # remove trailing doc if present
            if kdoc == "":
                # attempt: split on last comma + quoted string
                md = re.search(r',\s*(?P<q>["\'])(?P<doc>.*?)(?P=q)\s*$', default_blob, re.S)
                if md:
                    kdoc = md.group("doc").strip()
                    default_blob = default_blob[: md.start()].strip()

            # Remove trailing commas
            default_blob = default_blob.strip().rstrip(",").strip()
            kdefault = _extract_cpp_default(default_blob)

        knobs.append(
            Knob(
                name=pname,
                kind="property",
                lang="cpp",
                type=ktype,
                default=kdefault,
                help=_extract_cpp_doc(kdoc) if kdoc else "",
                source_file=source_file,
                source_line=line_no,
                raw=m.group(0).strip(),
            )
        )

    return knobs


# -----------------------------
# Merge + output
# -----------------------------
def merge_knobs(knobs: List[Knob], keep_first: bool = True) -> Tuple[Dict[str, Knob], List[Duplicate]]:
    merged: Dict[str, Knob] = {}
    dups: List[Duplicate] = []

    for k in knobs:
        if k.name in merged:
            kept = merged[k.name]
            dups.append(
                Duplicate(
                    name=k.name,
                    kept=(kept.source_file, kept.source_line),
                    dropped=(k.source_file, k.source_line),
                )
            )
            if not keep_first:
                merged[k.name] = k
            continue
        merged[k.name] = k

    return merged, dups


def dump_yaml(path: Path, payload: Dict[str, Any]) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is not available. Use --format json or install pyyaml.")
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def dump_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def build_output_schema(merged: Dict[str, Knob], dups: List[Duplicate], root: Path) -> Dict[str, Any]:
    # Provide both a flat "knobs" dict and a grouped view by common prefixes.
    knobs_dict: Dict[str, Any] = {}
    grouped: Dict[str, Dict[str, Any]] = {}

    def group_key(name: str) -> str:
        # Heuristic grouping for your DCH chain:
        # gf_* -> genfit2, ggtf_* -> ggtf, dch_* -> digitizer, compactXML/inputFile/modelPath -> io/geo
        if name.startswith("gf_") or name in ("Bz", "PDG", "UseDAF", "UseMaterialEffects", "TGeoFile"):
            return "genfit2"
        if name.startswith("ggtf_") or name in ("tbeta", "td", "onnxChunk", "maxHitsPerEvent", "modelPath"):
            return "ggtf"
        if name.startswith("dch_") or name in ("xyResolution_mm", "zResolution_mm", "dchDigiVersion"):
            return "digitizer"
        if name in ("compactXML", "tgeoFile", "dchName", "dchSimHits"):
            return "geometry"
        if name in ("inputFile", "outputFile", "stage", "skipDigi", "jobTag", "fitOut", "ggtfTracksOut", "fitter"):
            return "pipeline"
        return "misc"

    for name, k in merged.items():
        knobs_dict[name] = {
            "kind": k.kind,
            "lang": k.lang,
            "type": k.type,
            "default": k.default,
            "help": k.help,
            "source": {
                "file": os.path.relpath(k.source_file, str(root)),
                "line": k.source_line,
            },
            "raw": k.raw,
        }
        gk = group_key(name)
        grouped.setdefault(gk, {})[name] = knobs_dict[name]

    payload = {
        "schema_version": 1,
        "root": str(root.resolve()),
        "summary": {
            "num_knobs": len(merged),
            "num_duplicates": len(dups),
        },
        "duplicates": [
            {
                "name": d.name,
                "kept": {"file": d.kept[0], "line": d.kept[1]},
                "dropped": {"file": d.dropped[0], "line": d.dropped[1]},
            }
            for d in dups
        ],
        "knobs": knobs_dict,
        "groups": grouped,
    }
    return payload


def write_exports_sh(path: Path, payload: Dict[str, Any], prefixes: List[str]) -> None:
    """
    Optional: emit a shell snippet exporting defaults as env vars.

    Example:
      export DCH_INPUTFILE="..."
      export GF_BZ="2.0"
    """
    knobs = payload.get("knobs", {})
    lines: List[str] = []
    lines.append("#!/usr/bin/env bash")
    lines.append("# Auto-generated exports from collect_knobs.py")
    lines.append("set -euo pipefail")
    lines.append("")

    def want(name: str) -> bool:
        if not prefixes:
            return True
        return any(name.startswith(p) for p in prefixes)

    for name, meta in knobs.items():
        if not want(name):
            continue
        default = meta.get("default", None)
        if default is None:
            continue
        env = name.upper()
        env = re.sub(r'[^A-Z0-9_]', "_", env)
        # quote safely
        val = str(default).strip()
        lines.append(f'export {env}="{val}"')

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o755)
    except Exception:
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description="Scan repo for CLI args + Gaudi::Property and emit YAML/JSON config.")
    ap.add_argument("--root", required=True, help="Root directory to scan")
    ap.add_argument("--out", required=True, help="Output config path (.yaml/.yml/.json)")
    ap.add_argument("--format", choices=["yaml", "json"], default=None, help="Output format (default inferred from --out)")
    ap.add_argument("--include-ext", nargs="+", default=[".py", ".cpp", ".h", ".hpp"],
                    help="File extensions to scan")
    ap.add_argument("--exclude-dir", nargs="+", default=[".git", "build", "install", "__pycache__", ".condor", "cmake-build"],
                    help="Directory names to exclude")
    ap.add_argument("--keep-first", action="store_true", default=True,
                    help="On duplicate knob names: keep the first encountered (default true).")
    ap.add_argument("--keep-last", dest="keep_first", action="store_false",
                    help="On duplicate knob names: keep the last encountered.")
    ap.add_argument("--exports", default="", help="Optional path to write exports.sh (empty disables).")
    ap.add_argument("--export-prefix", nargs="+", default=[],
                    help="Only export env vars for knob names starting with these prefixes (e.g. gf_ ggtf_ dch_)")
    ap.add_argument("--verbose", action="store_true", default=False)

    args = ap.parse_args()
    root = Path(args.root).resolve()
    out = Path(args.out).resolve()

    fmt = args.format
    if fmt is None:
        if out.suffix.lower() in (".yaml", ".yml"):
            fmt = "yaml"
        elif out.suffix.lower() == ".json":
            fmt = "json"
        else:
            raise RuntimeError("Cannot infer format from --out. Use --format yaml|json.")

    files = iter_files(root, args.include_ext, args.exclude_dir)
    if args.verbose:
        info(f"Scanning {len(files)} files under {root}")

    all_knobs: List[Knob] = []
    for p in files:
        txt = read_text(p)
        if p.suffix == ".py":
            all_knobs.extend(parse_python_args(txt, str(p)))
        if p.suffix in (".cpp", ".h", ".hpp"):
            all_knobs.extend(parse_cpp_gaudi_properties(txt, str(p)))

    merged, dups = merge_knobs(all_knobs, keep_first=args.keep_first)

    # Print duplicate warnings
    for d in dups:
        warn(
            f"Duplicate knob '{d.name}': keeping {d.kept[0]}:{d.kept[1]} "
            f"dropping {d.dropped[0]}:{d.dropped[1]}"
        )

    payload = build_output_schema(merged, dups, root)

    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "yaml":
        dump_yaml(out, payload)
    else:
        dump_json(out, payload)

    if args.exports:
        ex_path = Path(args.exports).resolve()
        ex_path.parent.mkdir(parents=True, exist_ok=True)
        write_exports_sh(ex_path, payload, prefixes=args.export_prefix)
        if args.verbose:
            info(f"Wrote exports: {ex_path}")

    if args.verbose:
        info(f"Wrote config: {out}")
        info(f"Knobs: {payload['summary']['num_knobs']}  duplicates: {payload['summary']['num_duplicates']}")

    print(f"[ok] wrote {out} ({fmt}), knobs={payload['summary']['num_knobs']} duplicates={payload['summary']['num_duplicates']}")


if __name__ == "__main__":
    main()
