#!/usr/bin/env python3
"""
autoreadme.py (v2)

Generates:
  - README.md in each directory under --root
  - DOCS_INDEX.md at --root
  - docs/chain.mmd Mermaid graph at --root/docs (unless --no-graph)

Primary signal: per-file DOC block:
  # DOC:
  # Summary: ...
  # Usage:
  #   ...
  # Inputs: ...
  # Outputs: ...
  # Connects-To: ...
  # Collections: ...
  # Tags: ...
  # DOC_END

Also adds heuristic "Inferred" links:
  - python imports
  - C++ includes
  - bash/python calls
  - k4run / condor usage
  - Gaudi configuration patterns (TopAlg, Configurables)
"""

from __future__ import annotations
import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# -----------------------------
# Config knobs (edit if needed)
# -----------------------------
IGNORE_DIR_PARTS = {
    ".git", "__pycache__", ".cache", ".pytest_cache",
    "build", "install", "cmake-build-debug", "cmake-build-release",
}
INCLUDE_EXTS = {
    ".py", ".sh", ".bash", ".zsh",
    ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".md", ".yaml", ".yml", ".json", ".toml",
    ".txt", ".cfg", ".ini",
}
# Folders where we *want* DOC blocks (for --check / --inject-stubs)
IMPORTANT_SUBPATH_HINTS = (
    "scripts", "python", "options", "job", "condor", "run", "test",
)

TEXTFILE_MAX = 400_000  # bytes

DOC_START_RE = re.compile(r'^\s*(?:(#|//)\s*)?DOC:\s*$')
DOC_END_RE   = re.compile(r'^\s*(?:(#|//)\s*)?DOC_END\s*$')


PY_IMPORT_RE = re.compile(r"^\s*(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\.]+))")
CPP_INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]')
BASH_CALL_RE = re.compile(r"^\s*(?:\./|bash\s+|sh\s+|zsh\s+|python3\s+|python\s+)([A-Za-z0-9_\-./]+)")
K4RUN_RE = re.compile(r"\bk4run\b")
CONDOR_RE = re.compile(r"\bcondor_submit\b|\bqueue\b|\bJobFlavour\b", re.IGNORECASE)

# Gaudi-ish Python config heuristics
GAUDI_CONFIGURABLES_RE = re.compile(r"^\s*from\s+Configurables\s+import\s+(.+)$")
GAUDI_TOPALG_RE = re.compile(r"\bTopAlg\b|\bApplicationMgr\b|\bEvtSel\b|\bEventSelector\b")
GAUDI_DECLARE_COMPONENT_RE = re.compile(r"\bDECLARE_COMPONENT\b|\bDECLARE_FACTORY\b|\bDECLARE_ALGORITHM_FACTORY\b")

# simple CLI usage extraction (argparse)
ARGPARSE_RE = re.compile(r"\bargparse\.ArgumentParser\b|\badd_argument\(")

@dataclass
class FileDoc:
    path: Path
    summary: str = ""
    usage: List[str] = field(default_factory=list)
    inputs: str = ""
    outputs: str = ""
    connects_to: List[str] = field(default_factory=list)
    collections: str = ""
    tags: List[str] = field(default_factory=list)

    inferred_links: List[str] = field(default_factory=list)
    has_doc_block: bool = False
    notes: List[str] = field(default_factory=list)

def read_text_safely(p: Path) -> str:
    try:
        data = p.read_bytes()
        if len(data) > TEXTFILE_MAX:
            return ""
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""



        
def parse_doc_block(text: str) -> Dict[str, List[str]]:
    lines = text.splitlines()
    in_doc = False
    block: List[str] = []

    # scan near top (allow licenses + module docstring)
    for ln in lines[:260]:
        if not in_doc and DOC_START_RE.match(ln):
            in_doc = True
            continue
        if in_doc and DOC_END_RE.match(ln):
            break
        if in_doc:
            # Remove leading comment markers if present
            ln2 = re.sub(r"^\s*(#|//)\s*", "", ln).rstrip()

            # Remove bare triple-quote lines inside the DOC block (optional)
            if ln2.strip() in ('"""', "'''"):
                continue

            block.append(ln2)

    if not block:
        return {}

    fields: Dict[str, List[str]] = {}
    current_key: Optional[str] = None

    for ln in block:
        if not ln.strip():
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*)$", ln)
        if m:
            current_key = m.group(1).strip().lower()
            fields.setdefault(current_key, [])
            val = m.group(2).strip()
            if val:
                fields[current_key].append(val)
        else:
            if current_key:
                fields[current_key].append(ln.strip())

    return fields


def fallback_summary(text: str) -> str:
    # Python module docstring first line
    m = re.search(r'^\s*"""(.*?)"""', text, flags=re.DOTALL | re.MULTILINE)
    if m:
        first = m.group(1).strip().splitlines()[0].strip()
        if first:
            return first

    # First meaningful comment line
    for ln in text.splitlines()[:40]:
        s = ln.strip()
        if s.startswith("#") or s.startswith("//"):
            cleaned = re.sub(r"^(#|//)\s*", "", s).strip()
            if cleaned and not cleaned.lower().startswith(("copyright", "license")):
                return cleaned

    # If argparse exists, give a hint
    if ARGPARSE_RE.search(text):
        return "CLI script (argparse detected); run with --help"

    # If looks like Gaudi options
    if GAUDI_TOPALG_RE.search(text) and "Configurables" in text:
        return "Gaudi options/config file (heuristic)"

    return ""

def is_interesting(p: Path, root: Path) -> bool:
    if p.is_dir():
        return False
    if any(part in IGNORE_DIR_PARTS for part in p.parts):
        return False
    if p.suffix and p.suffix not in INCLUDE_EXTS:
        return False
    # skip generated readmes we write
    if p.name in ("README.md", "DOCS_INDEX.md"):
        return False
    try:
        p.relative_to(root)
    except Exception:
        return False
    return True

def infer_links(p: Path, text: str) -> List[str]:
    links: Set[str] = set()

    # keep inference near top for speed, but scan more for gaudi-ish wiring
    lines = text.splitlines()
    head = lines[:500]
    full = lines[:2000]

    for ln in head:
        m = PY_IMPORT_RE.match(ln)
        if m:
            mod = m.group(1) or m.group(2)
            if mod:
                links.add(f"import:{mod}")

        m2 = CPP_INCLUDE_RE.match(ln)
        if m2:
            links.add(f"include:{m2.group(1)}")

        m3 = BASH_CALL_RE.match(ln)
        if m3:
            tgt = m3.group(1)
            if any(tgt.endswith(ext) for ext in (".py", ".sh", ".bash", ".zsh")) or "/" in tgt:
                links.add(f"calls:{tgt}")

    if K4RUN_RE.search(text):
        links.add("uses:k4run")
    if CONDOR_RE.search(text):
        links.add("uses:condor")

    # Gaudi Python config inference
    # - list Configurables imported
    for ln in full:
        m = GAUDI_CONFIGURABLES_RE.match(ln)
        if m:
            # avoid huge lines; just label it
            links.add("gaudi:imports:Configurables")
            break

    # - find algorithm names in TopAlg patterns (very heuristic)
    # e.g. ApplicationMgr( TopAlg = [ "Alg1", "Alg2" ] )
    topalg_str = " ".join(full)
    for alg in re.findall(r'"([A-Za-z0-9_]+)"', topalg_str):
        if len(alg) >= 5 and any(k in alg.lower() for k in ("track", "dch", "fit", "gtt", "gltf", "acts")):
            links.add(f"gaudi:topalg:{alg}")

    # C++ Gaudi component hint
    if p.suffix in (".cpp", ".cc", ".cxx") and GAUDI_DECLARE_COMPONENT_RE.search(text):
        links.add("gaudi:declares_component")

    return sorted(links)

def build_filedoc(p: Path, root: Path) -> Optional[FileDoc]:
    text = read_text_safely(p)
    if not text:
        return None

    fields = parse_doc_block(text)
    fd = FileDoc(path=p)

    if fields:
        fd.has_doc_block = True
        fd.summary = " ".join(fields.get("summary", [])).strip()
        fd.usage = fields.get("usage", [])
        fd.inputs = " ".join(fields.get("inputs", [])).strip()
        fd.outputs = " ".join(fields.get("outputs", [])).strip()
        fd.collections = " ".join(fields.get("collections", [])).strip()

        conns = fields.get("connects-to", []) + fields.get("connects_to", [])
        fd.connects_to = [x.strip() for x in conns if x.strip()]

        tags: List[str] = []
        for tline in fields.get("tags", []):
            tags += [t.strip() for t in tline.split(",") if t.strip()]
        fd.tags = sorted(set(tags))
    else:
        fd.summary = fallback_summary(text)

    fd.inferred_links = infer_links(p, text)

    # small quality notes
    if not fd.summary:
        fd.notes.append("missing_summary")
    if not fd.has_doc_block:
        fd.notes.append("no_doc_block")

    return fd

def relpath(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except Exception:
        return str(p)

def md_escape(s: str) -> str:
    return s.replace("|", "\\|")

def is_important(p: Path, root: Path) -> bool:
    rp = relpath(p, root).lower()
    return any(f"/{h}/" in f"/{rp}/" for h in IMPORTANT_SUBPATH_HINTS)

def write_dir_readme(dirpath: Path, root: Path, docs: List[FileDoc], write: bool) -> None:
    if not docs:
        return

    rp = relpath(dirpath, root)
    title = f"# {rp}\n"
    intro = (
        "\nThis README is auto-generated from per-file `DOC:` blocks (preferred) plus heuristics.\n"
        "Improve accuracy by adding a `DOC:` header to important glue files, then re-run:\n\n"
        "```bash\npython3 scripts/autoreadme.py --root . --write\n```\n\n"
    )

    lines: List[str] = [title, intro]
    lines.append("## Files\n")
    lines.append("| File | Summary | Usage | Connects-To | Inferred |\n")
    lines.append("|---|---|---|---|---|\n")

    for fd in sorted(docs, key=lambda x: x.path.name.lower()):
        usage = "<br>".join(md_escape(u) for u in fd.usage[:3]) if fd.usage else ""
        conns = "<br>".join(md_escape(c) for c in fd.connects_to[:6]) if fd.connects_to else ""
        inf = "<br>".join(md_escape(i) for i in fd.inferred_links[:10]) if fd.inferred_links else ""
        summ = md_escape(fd.summary) if fd.summary else ""
        badge = "✅" if fd.has_doc_block else "⚠️"
        lines.append(f"| {badge} `{fd.path.name}` | {summ} | {usage} | {conns} | {inf} |\n")

    # Inputs / Outputs / Collections section
    io = [fd for fd in docs if fd.inputs or fd.outputs or fd.collections]
    if io:
        lines.append("\n## Inputs / Outputs / Collections\n")
        for fd in io:
            lines.append(f"### `{fd.path.name}`\n")
            if fd.inputs:
                lines.append(f"- **Inputs:** {md_escape(fd.inputs)}\n")
            if fd.outputs:
                lines.append(f"- **Outputs:** {md_escape(fd.outputs)}\n")
            if fd.collections:
                lines.append(f"- **Collections:** {md_escape(fd.collections)}\n")

    out = dirpath / "README.md"
    content = "".join(lines)
    if write:
        out.write_text(content, encoding="utf-8")
        print(f"[write] {out}")
    else:
        print(f"[dry] would write {out}")

def write_root_index(root: Path, all_docs: List[FileDoc], write: bool) -> None:
    out = root / "DOCS_INDEX.md"
    lines: List[str] = []
    lines.append("# Tracking documentation index\n\n")
    lines.append("Auto-generated index of files and per-directory READMEs.\n\n")
    lines.append("## How to regenerate\n\n")
    lines.append("```bash\npython3 scripts/autoreadme.py --root . --write\n```\n\n")

    # group by directory
    by_dir: Dict[Path, List[FileDoc]] = {}
    for fd in all_docs:
        by_dir.setdefault(fd.path.parent, []).append(fd)

    lines.append("## Directories\n\n")
    for d in sorted(by_dir.keys(), key=lambda p: relpath(p, root).lower()):
        rp = relpath(d, root)
        lines.append(f"- `{rp}/README.md`\n")

    lines.append("\n## All files\n\n")
    lines.append("| Path | Summary | Doc | Tags |\n")
    lines.append("|---|---|---|---|\n")
    for fd in sorted(all_docs, key=lambda x: relpath(x.path, root).lower()):
        tags = ", ".join(fd.tags) if fd.tags else ""
        docflag = "yes" if fd.has_doc_block else "no"
        lines.append(
            f"| `{relpath(fd.path, root)}` | {md_escape(fd.summary)} | {docflag} | {md_escape(tags)} |\n"
        )

    content = "".join(lines)
    if write:
        out.write_text(content, encoding="utf-8")
        print(f"[write] {out}")
    else:
        print(f"[dry] would write {out}")

def write_mermaid_graph(root: Path, all_docs: List[FileDoc], write: bool) -> None:
    docs_dir = root / "docs"
    docs_dir.mkdir(exist_ok=True)
    out = docs_dir / "chain.mmd"

    # edges from explicit connects_to plus inferred calls/mentions/gaudi topalg
    edges: Set[Tuple[str, str]] = set()
    nodes: Set[str] = set()

    def node_id(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]", "_", s)

    # build quick lookup of basenames for resolution
    basename_to_rel: Dict[str, str] = {}
    for fd in all_docs:
        rp = relpath(fd.path, root)
        basename_to_rel[fd.path.name] = rp

    for fd in all_docs:
        src = relpath(fd.path, root)
        nodes.add(src)

        for c in fd.connects_to:
            # resolve "runX.py" -> repo-relative if present
            tgt = basename_to_rel.get(Path(c).name, c)
            edges.add((src, tgt))
            nodes.add(tgt)

        for inf in fd.inferred_links:
            if inf.startswith("calls:"):
                raw = inf.replace("calls:", "")
                tgt = basename_to_rel.get(Path(raw).name, raw)
                edges.add((src, tgt))
                nodes.add(tgt)
            if inf.startswith("gaudi:topalg:"):
                alg = inf.replace("gaudi:topalg:", "")
                tgt = f"Alg::{alg}"
                edges.add((src, tgt))
                nodes.add(tgt)

    lines: List[str] = ["flowchart LR\n"]
    for n in sorted(nodes):
        lines.append(f'  {node_id(n)}["{n}"]\n')
    for a, b in sorted(edges):
        lines.append(f"  {node_id(a)} --> {node_id(b)}\n")

    content = "".join(lines)
    if write:
        out.write_text(content, encoding="utf-8")
        print(f"[write] {out}")
    else:
        print(f"[dry] would write {out}")

def inject_stub_doc_block(p: Path) -> bool:
    """
    Inserts a DOC block at the top of a file if none exists.
    Conservative: only for text-like files, and only if file doesn't already contain 'DOC:'.
    """
    text = read_text_safely(p)
    if not text or "DOC:" in text:
        return False

    # Choose comment prefix
    if p.suffix in (".cpp", ".cc", ".cxx", ".h", ".hpp"):
        prefix = "// "
    else:
        prefix = "# "

    stub = (
        f"{prefix}DOC:\n"
        f"{prefix}Summary: TODO\n"
        f"{prefix}Usage:\n"
        f"{prefix}  TODO\n"
        f"{prefix}Inputs: TODO\n"
        f"{prefix}Outputs: TODO\n"
        f"{prefix}Connects-To: TODO\n"
        f"{prefix}Collections: TODO\n"
        f"{prefix}Tags: TODO\n"
        f"{prefix}DOC_END\n\n"
    )

    p.write_text(stub + text, encoding="utf-8")
    return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Path to Tracking directory (run from inside it: --root .)")
    ap.add_argument("--write", action="store_true", help="Write README.md / DOCS_INDEX.md / docs/chain.mmd")
    ap.add_argument("--no-graph", action="store_true", help="Skip writing docs/chain.mmd")
    ap.add_argument("--check", action="store_true",
                    help="Exit non-zero if important files are missing DOC blocks")
    ap.add_argument("--inject-stubs", action="store_true",
                    help="Insert stub DOC blocks into important files that lack them (use with caution)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    # collect docs
    all_docs: List[FileDoc] = []
    interesting_files: List[Path] = [p for p in root.rglob("*") if is_interesting(p, root)]

    # optionally inject stubs
    if args.inject_stubs:
        changed = 0
        for p in interesting_files:
            if is_important(p, root):
                if inject_stub_doc_block(p):
                    changed += 1
        print(f"[inject-stubs] inserted DOC stubs into {changed} file(s)")

    for p in interesting_files:
        fd = build_filedoc(p, root)
        if fd:
            all_docs.append(fd)

    # check mode (CI): important files must have DOC block
    if args.check:
        missing: List[str] = []
        for fd in all_docs:
            if is_important(fd.path, root) and not fd.has_doc_block:
                missing.append(relpath(fd.path, root))
        if missing:
            print("[check] Missing DOC blocks in important files:")
            for m in missing:
                print(f"  - {m}")
            raise SystemExit(2)
        print("[check] OK: all important files have DOC blocks")

    # group by directory
    by_dir: Dict[Path, List[FileDoc]] = {}
    for fd in all_docs:
        by_dir.setdefault(fd.path.parent, []).append(fd)

    for d, docs in by_dir.items():
        write_dir_readme(d, root, docs, write=args.write)

    write_root_index(root, all_docs, write=args.write)
    if not args.no_graph:
        write_mermaid_graph(root, all_docs, write=args.write)

if __name__ == "__main__":
    main()
