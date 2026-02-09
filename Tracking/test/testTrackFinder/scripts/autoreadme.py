#!/usr/bin/env python3
"""
DOC
autoreadme.py (v3)

Generates:
  - README.md in each directory under --root
  - DOCS_INDEX.md at --root
  - docs/chain.mmd Mermaid graph at --root/docs (unless --no-graph)

Primary signal: per-file DOC block near the top of each file.

Accepted DOC block markers (case-insensitive; with or without comment prefixes):
  Start markers (any of):
    DOC
    DOC:
    DOC_START
    DOC_BEGIN
    DOCBLOCK
    DOC_BLOCK
    BEGIN_DOC
  End markers (any of):
    DOC_END
    END_DOC
    DOC_STOP
    DOC_FINISH

DOC blocks can appear as:
  - comment blocks:  # ...   // ...   /* ... */   ; ...   -- ...
  - inside Python triple-quoted docstrings (the script strips bare triple-quote-only lines)

Recommended fields inside a DOC block (all optional but strongly encouraged):
  Summary: one-liner of what the file does
  Usage: how to run / how to include in a chain
  Examples: runnable example commands + what you expect to get
  Inputs: input files / collections / objects + types
  Outputs: outputs created + types
  Collections: collection names + schemas/types
  Connects-To: upstream/downstream files or components
  Arguments: CLI args or Gaudi properties + defaults + meaning
  Tags: comma-separated keywords
DOC_END
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

# How far from the top we search for a DOC block.
DOC_SCAN_MAX_LINES = 600

# -------------
# Regex helpers
# -------------
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

# Heuristic extraction of argparse add_argument lines (best-effort, not full AST)
ARGPARSE_ADDARG_RE = re.compile(
    r"""add_argument\(\s*([^\)]*?)\s*\)""",
    flags=re.IGNORECASE
)

# Heuristic extraction of Gaudi::Property declarations in C++ (best-effort)
# Matches e.g. Gaudi::Property<double> m_Bz {this, "Bz", 2.0, "..."};
GAUDI_PROPERTY_RE = re.compile(
    r"""Gaudi::Property<\s*([^>]+?)\s*>\s+([A-Za-z0-9_]+)\s*\{\s*this\s*,\s*"([^"]+)"\s*,\s*([^,}]+)""",
    flags=re.MULTILINE
)

# -----------------------------
# DOC block parsing (flexible)
# -----------------------------

# Start/end marker tokens we accept (normalized)
DOC_START_TOKENS = {
    "DOC", "DOC:", "DOC_START", "DOC_BEGIN", "DOCBLOCK", "DOC_BLOCK", "BEGIN_DOC"
}
DOC_END_TOKENS = {
    "DOC_END", "END_DOC", "DOC_STOP", "DOC_FINISH"
}

# Comment prefixes we know how to strip from DOC block lines
COMMENT_PREFIX_RE = re.compile(
    r"""^\s*(?:
          \# |
          // |
          /\* |
          \* |
          ; |
          -- |
          ! |
          :: |
        )\s*""",
    re.VERBOSE
)

TRIPLE_QUOTE_ONLY_RE = re.compile(r"""^\s*("{3}|'{3})\s*$""")


def _strip_leading_comment(line: str) -> str:
    """Remove one leading comment prefix token (if present)."""
    return COMMENT_PREFIX_RE.sub("", line, count=1).rstrip()


def _normalize_marker(s: str) -> str:
    """
    Normalize a candidate marker line:
      - strip leading comment tokens
      - strip surrounding whitespace
      - collapse spaces
      - keep underscores/colons
      - uppercase
    """
    s2 = _strip_leading_comment(s).strip()
    # remove surrounding brackets if someone wrote [DOC] etc.
    s2 = s2.strip("[](){}")
    # collapse internal whitespace
    s2 = re.sub(r"\s+", " ", s2)
    return s2.upper()


def _is_doc_start(line: str) -> bool:
    m = _normalize_marker(line)
    return m in DOC_START_TOKENS


def _is_doc_end(line: str) -> bool:
    m = _normalize_marker(line)
    return m in DOC_END_TOKENS


def _strip_doc_line(line: str) -> Optional[str]:
    """
    Strip comment prefix; drop bare triple-quote-only lines; return cleaned line or None if ignorable.
    """
    ln2 = _strip_leading_comment(line)

    # Drop bare triple-quote lines inside DOC blocks (common in Python docstrings)
    if TRIPLE_QUOTE_ONLY_RE.match(ln2.strip()):
        return None

    # Also drop empty
    if not ln2.strip():
        return None

    return ln2.rstrip()


def _canonical_key(k: str) -> str:
    """
    Map possible field header spellings to canonical keys used in FileDoc.
    """
    k0 = k.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "connects": "connects_to",
        "connects_to": "connects_to",
        "connects-to": "connects_to",
        "collections": "collections",
        "inputs": "inputs",
        "outputs": "outputs",
        "summary": "summary",
        "usage": "usage",
        "examples": "examples",
        "example": "examples",
        "args": "arguments",
        "arguments": "arguments",
        "parameters": "arguments",
        "properties": "arguments",
        "tags": "tags",
        "notes": "notes",
    }
    return aliases.get(k0, k0)


def parse_doc_block(text: str) -> Dict[str, List[str]]:
    """
    Parse the first DOC block found near the top of the file.

    The parser is intentionally permissive:
      - accepts many start markers: DOC, DOC:, DOC_START, ...
      - accepts many end markers: DOC_END, END_DOC, ...
      - strips common comment prefixes (#, //, /*, *, ;, --, ...)
      - tolerates Python docstrings by ignoring bare triple-quote-only lines
    """
    lines = text.splitlines()
    in_doc = False
    block: List[str] = []

    for ln in lines[:DOC_SCAN_MAX_LINES]:
        if not in_doc and _is_doc_start(ln):
            in_doc = True
            continue
        if in_doc and _is_doc_end(ln):
            break
        if in_doc:
            cleaned = _strip_doc_line(ln)
            if cleaned is not None:
                block.append(cleaned)

    if not block:
        return {}

    fields: Dict[str, List[str]] = {}
    current_key: Optional[str] = None

    # Field header pattern: Key: value
    header_re = re.compile(r"^([A-Za-z0-9_\- ]+)\s*:\s*(.*)$")

    for ln in block:
        m = header_re.match(ln)
        if m:
            current_key = _canonical_key(m.group(1))
            fields.setdefault(current_key, [])
            val = m.group(2).strip()
            if val:
                fields[current_key].append(val)
        else:
            if current_key:
                fields[current_key].append(ln.strip())

    return fields


# -----------------------------
# Model / file doc structure
# -----------------------------
@dataclass
class FileDoc:
    path: Path
    summary: str = ""
    usage: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    inputs: str = ""
    outputs: str = ""
    connects_to: List[str] = field(default_factory=list)
    collections: str = ""
    arguments: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    inferred_links: List[str] = field(default_factory=list)
    inferred_arguments: List[str] = field(default_factory=list)
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


# -----------------------------
# Heuristic extraction helpers
# -----------------------------
def fallback_summary(text: str) -> str:
    # Python module docstring first line
    m = re.search(r'^\s*"""(.*?)"""', text, flags=re.DOTALL | re.MULTILINE)
    if m:
        first = m.group(1).strip().splitlines()[0].strip()
        if first:
            return first

    # First meaningful comment line
    for ln in text.splitlines()[:60]:
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


def infer_links(p: Path, text: str) -> List[str]:
    links: Set[str] = set()

    lines = text.splitlines()
    head = lines[:800]
    full = lines[:3000]

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
    for ln in full:
        m = GAUDI_CONFIGURABLES_RE.match(ln)
        if m:
            links.add("gaudi:imports:Configurables")
            break

    # Algorithm names in TopAlg patterns (very heuristic)
    topalg_str = " ".join(full)
    for alg in re.findall(r'"([A-Za-z0-9_]+)"', topalg_str):
        if len(alg) >= 5 and any(k in alg.lower() for k in ("track", "dch", "fit", "gtt", "gltf", "acts", "genfit")):
            links.add(f"gaudi:topalg:{alg}")

    # C++ Gaudi component hint
    if p.suffix in (".cpp", ".cc", ".cxx") and GAUDI_DECLARE_COMPONENT_RE.search(text):
        links.add("gaudi:declares_component")

    return sorted(links)


def infer_argparse_arguments(text: str, max_items: int = 25) -> List[str]:
    """
    Best-effort extraction of argparse add_argument(...) calls.
    Produces short, markdown-friendly bullet lines.
    """
    if not ARGPARSE_RE.search(text):
        return []

    out: List[str] = []
    lines = text.splitlines()
    window = "\n".join(lines[:2500])

    for m in ARGPARSE_ADDARG_RE.finditer(window):
        body = m.group(1)
        if not body:
            continue

        opt = None
        optm = re.search(r"""(["'])(--?[A-Za-z0-9_\-]+)\1""", body)
        if optm:
            opt = optm.group(2)

        default = None
        dm = re.search(r"\bdefault\s*=\s*([^,\)]+)", body)
        if dm:
            default = dm.group(1).strip()

        help_s = None
        hm = re.search(r"""\bhelp\s*=\s*["']([^"']+)["']""", body)
        if hm:
            help_s = hm.group(1).strip()

        if opt:
            parts = [opt]
            if default is not None:
                parts.append(f"default={default}")
            if help_s:
                parts.append(help_s)
            out.append("  - " + " | ".join(parts))
        else:
            snippet = re.sub(r"\s+", " ", body).strip()
            out.append("  - " + (snippet[:160] + ("..." if len(snippet) > 160 else "")))

        if len(out) >= max_items:
            break

    return out


def infer_gaudi_properties_cpp(text: str, max_items: int = 40) -> List[str]:
    """
    Best-effort extraction of Gaudi::Property declarations from C++.
    Produces bullet lines like:
      - Bz (double) default=2.0 : Bz field [T]
    """
    out: List[str] = []
    for m in GAUDI_PROPERTY_RE.finditer(text[:350_000]):
        typ = m.group(1).strip()
        member = m.group(2).strip()
        propname = m.group(3).strip()
        default = m.group(4).strip()

        start = m.end()
        eol = text.find("\n", start)
        if eol == -1:
            eol = min(len(text), start + 300)
        tail = text[start:eol]
        docm = re.search(r""",\s*"([^"]+)"\s*\}""", tail)
        doc = docm.group(1).strip() if docm else ""

        line = f"  - {propname} ({typ}) default={default}"
        if doc:
            line += f" : {doc}"
        else:
            line += f" (member={member})"
        out.append(line)

        if len(out) >= max_items:
            break
    return out


def is_interesting(p: Path, root: Path) -> bool:
    if p.is_dir():
        return False
    if any(part in IGNORE_DIR_PARTS for part in p.parts):
        return False
    if p.suffix and p.suffix not in INCLUDE_EXTS:
        return False
    if p.name in ("README.md", "DOCS_INDEX.md"):
        return False
    try:
        p.relative_to(root)
    except Exception:
        return False
    return True


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
        fd.examples = fields.get("examples", [])
        fd.inputs = " ".join(fields.get("inputs", [])).strip()
        fd.outputs = " ".join(fields.get("outputs", [])).strip()
        fd.collections = " ".join(fields.get("collections", [])).strip()

        conns = fields.get("connects-to", []) + fields.get("connects_to", []) + fields.get("connects", [])
        fd.connects_to = [x.strip() for x in conns if x.strip()]

        fd.arguments = (
            fields.get("arguments", [])
            + fields.get("args", [])
            + fields.get("parameters", [])
            + fields.get("properties", [])
        )

        tags: List[str] = []
        for tline in fields.get("tags", []):
            tags += [t.strip() for t in tline.split(",") if t.strip()]
        fd.tags = sorted(set(tags))
    else:
        fd.summary = fallback_summary(text)

    fd.inferred_links = infer_links(p, text)

    inferred_args: List[str] = []
    if p.suffix == ".py":
        inferred_args = infer_argparse_arguments(text)
    elif p.suffix in (".cpp", ".cc", ".cxx", ".h", ".hpp"):
        inferred_args = infer_gaudi_properties_cpp(text)

    fd.inferred_arguments = inferred_args

    if not fd.summary:
        fd.notes.append("missing_summary")
    if not fd.has_doc_block:
        fd.notes.append("no_doc_block")

    return fd


def write_dir_readme(dirpath: Path, root: Path, docs: List[FileDoc], write: bool) -> None:
    if not docs:
        return

    rp = relpath(dirpath, root)
    title = f"# {rp}\n"
    intro = (
        "\nThis README is auto-generated from per-file DOC blocks (preferred) plus heuristics.\n"
        "Improve accuracy by adding a DOC header to important glue files, then re-run:\n\n"
        "```bash\npython3 scripts/autoreadme.py --root . --write\n```\n\n"
        "Accepted DOC start markers include `DOC`, `DOC:`, `DOC_START`, `DOC_BEGIN` (and similar); "
        "end markers include `DOC_END`, `END_DOC` (and similar).\n\n"
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

    details = [fd for fd in docs if (fd.inputs or fd.outputs or fd.collections or fd.examples or fd.arguments or fd.inferred_arguments)]
    if details:
        lines.append("\n## Details\n")
        for fd in sorted(details, key=lambda x: x.path.name.lower()):
            lines.append(f"\n### `{fd.path.name}`\n")
            if fd.inputs:
                lines.append(f"- **Inputs:** {md_escape(fd.inputs)}\n")
            if fd.outputs:
                lines.append(f"- **Outputs:** {md_escape(fd.outputs)}\n")
            if fd.collections:
                lines.append(f"- **Collections:** {md_escape(fd.collections)}\n")

            if fd.examples:
                lines.append("- **Examples:**\n")
                for ex in fd.examples[:12]:
                    lines.append(f"  - {md_escape(ex)}\n")

            if fd.arguments:
                lines.append("- **Arguments / Properties (DOC):**\n")
                for a in fd.arguments[:25]:
                    lines.append(f"  - {md_escape(a)}\n")

            if fd.inferred_arguments:
                lines.append("- **Arguments / Properties (inferred):**\n")
                for a in fd.inferred_arguments[:25]:
                    lines.append(f"{md_escape(a)}\n")

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

    edges: Set[Tuple[str, str]] = set()
    nodes: Set[str] = set()

    def node_id(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]", "_", s)

    basename_to_rel: Dict[str, str] = {}
    for fd in all_docs:
        rp = relpath(fd.path, root)
        basename_to_rel[fd.path.name] = rp

    for fd in all_docs:
        src = relpath(fd.path, root)
        nodes.add(src)

        for c in fd.connects_to:
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


def file_contains_any_doc_marker(text: str) -> bool:
    for ln in text.splitlines()[:DOC_SCAN_MAX_LINES]:
        if _is_doc_start(ln):
            return True
    return False


def comment_prefix_for_path(p: Path) -> str:
    if p.suffix in (".cpp", ".cc", ".cxx", ".h", ".hpp"):
        return "// "
    if p.suffix in (".sh", ".bash", ".zsh"):
        return "# "
    if p.suffix in (".ini", ".cfg"):
        return "; "
    return "# "


def inject_stub_doc_block(p: Path) -> bool:
    text = read_text_safely(p)
    if not text:
        return False
    if file_contains_any_doc_marker(text):
        return False

    prefix = comment_prefix_for_path(p)

    stub = (
        f"{prefix}DOC:\n"
        f"{prefix}Summary: TODO one-line description\n"
        f"{prefix}Usage:\n"
        f"{prefix}  TODO how to run / include\n"
        f"{prefix}Examples:\n"
        f"{prefix}  TODO example command(s) + expected result\n"
        f"{prefix}Inputs: TODO (include types/classes/collections)\n"
        f"{prefix}Outputs: TODO (include types/classes/collections)\n"
        f"{prefix}Collections: TODO (name -> type/schema)\n"
        f"{prefix}Connects-To: TODO upstream/downstream files/components\n"
        f"{prefix}Arguments: TODO important args/properties + defaults + meaning\n"
        f"{prefix}Tags: TODO comma,separated,tags\n"
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

    all_docs: List[FileDoc] = []
    interesting_files: List[Path] = [p for p in root.rglob("*") if is_interesting(p, root)]

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
