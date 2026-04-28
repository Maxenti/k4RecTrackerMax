#!/usr/bin/env python3
"""
DOC
Summary: Project-aware README/index generator for testTrackFinder cleanup docs.
Usage:
  python3 scripts/autoreadme.py --root . --write
  python3 scripts/autoreadme.py --root . --write --include-archive
  python3 scripts/autoreadme.py --root . --check
  python3 scripts/autoreadme.py --root . --inject-stubs
Outputs: Per-directory generated README files, DOCS_INDEX.md, and docs/chain.mmd.
Tags: documentation, maintenance, testTrackFinder, autoreadme
DOC_END

autoreadme.py

Project-aware documentation generator for:

  Tracking/test/testTrackFinder/

This script is intentionally not a replacement for curated top-level workflow
documentation. It is meant to amplify documentation for subdirectories such as:

  scripts/
  steering/
  configs/
  docs/

while protecting human-written root documentation.

Core behavior:
  - extracts DOC blocks from files
  - infers basic imports, calls, argparse options, Gaudi components/properties
  - groups files by status: authoritative / secondary / legacy / archive-candidate / unknown
  - writes generated README files only where allowed
  - writes DOCS_INDEX.md at the root
  - writes docs/chain.mmd Mermaid workflow graph
  - ignores artifacts/ and archive/ by default

Important project policy:
  - Top-level README.md is curated and protected by default.
  - docs/workflow.md and docs/directory_layout.md are curated and protected.
  - Generated docs should help inventory subdirectories, not redefine the
    authoritative workflow.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


# =============================================================================
# Project-specific configuration
# =============================================================================

VERSION = "testTrackFinder-autoreadme-v4"

DEFAULT_IGNORE_DIR_PARTS = {
    ".git",
    "__pycache__",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "install",
    "cmake-build-debug",
    "cmake-build-release",
    "artifacts",
    "archive",
}

ALWAYS_IGNORE_FILE_NAMES = {
    ".DS_Store",
}

INCLUDE_EXTS = {
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".cpp",
    ".cc",
    ".cxx",
    ".c",
    ".h",
    ".hpp",
    ".hh",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".txt",
    ".cfg",
    ".ini",
    ".condor",
    ".submit",
    ".tcl",
    ".xml",
}

GENERATED_DOC_MARKER_BEGIN = "<!-- BEGIN AUTOREADME GENERATED -->"
GENERATED_DOC_MARKER_END = "<!-- END AUTOREADME GENERATED -->"

PROTECTED_CURATED_DOCS = {
    "README.md",
    "docs/workflow.md",
    "docs/directory_layout.md",
}

DEFAULT_GENERATED_README_DIRS = {
    "scripts",
    "steering",
    "configs",
    "configs/condor",
    "configs/geom",
    "configs/delphes",
    "docs",
}

IMPORTANT_SUBPATH_HINTS = (
    "scripts",
    "steering",
    "configs",
    "condor",
)

TEXTFILE_MAX_BYTES = 600_000
DOC_SCAN_MAX_LINES = 700

STATUS_ORDER = [
    "authoritative",
    "campaign-specific",
    "secondary",
    "legacy",
    "archive-candidate",
    "unknown",
]

STATUS_LABEL = {
    "authoritative": "Authoritative",
    "campaign-specific": "Authoritative / campaign-specific",
    "secondary": "Secondary",
    "legacy": "Legacy",
    "archive-candidate": "Archive candidate",
    "unknown": "Unknown / needs classification",
}

STATUS_BADGE = {
    "authoritative": "✅",
    "campaign-specific": "🟦",
    "secondary": "🛠️",
    "legacy": "🕰️",
    "archive-candidate": "📦",
    "unknown": "⚠️",
}


# =============================================================================
# Project classification defaults
# =============================================================================

PROJECT_CLASSIFICATION: Dict[str, Dict[str, str]] = {
    # Steering
    "steering/runDCHTestTrackFinder.py": {
        "status": "authoritative",
        "purpose": "Main k4run steering for DCH digi → GGTF → GenFit2 fitting.",
        "document_where": "README.md, docs/workflow.md",
    },
    "steering/local_chain.sh": {
        "status": "authoritative",
        "purpose": "Local end-to-end wrapper around main steering with environment knobs and metadata stamping.",
        "document_where": "README.md, docs/workflow.md",
    },
    "steering/dd4hep2root.py": {
        "status": "authoritative",
        "purpose": "Convert compact DD4hep XML into TGeo ROOT geometry.",
        "document_where": "docs/workflow.md",
    },
    "steering/runTestTrackFinder.py": {
        "status": "legacy",
        "purpose": "Older broader test steering with planar + DCH digi + GGTF.",
        "document_where": "archive note or docs/workflow.md legacy note",
    },

    # Runtime/reco Condor
    "scripts/make_runtime.sh": {
        "status": "authoritative",
        "purpose": "Build worker-node runtime bundle and validate plugin usability.",
        "document_where": "README.md, docs/workflow.md",
    },
    "scripts/submit_reco.sh": {
        "status": "authoritative",
        "purpose": "Main reco campaign submission wrapper.",
        "document_where": "README.md, docs/workflow.md",
    },
    "scripts/reco_job.sh": {
        "status": "authoritative",
        "purpose": "Condor worker wrapper for one reco job.",
        "document_where": "docs/workflow.md",
    },
    "configs/condor/reco.condor": {
        "status": "authoritative",
        "purpose": "Fixed submit description for reco jobs.",
        "document_where": "docs/workflow.md, docs/directory_layout.md",
    },
    "scripts/make_filelist.sh": {
        "status": "authoritative",
        "purpose": "Discover eta-organized input ROOT files and build submission file list.",
        "document_where": "docs/workflow.md",
    },

    # Analysis/closeout
    "scripts/analyze_pt_resolution_grid.py": {
        "status": "authoritative",
        "purpose": "Reduce reco outputs into summary ROOT with by-eta, by-method, and diagnostics.",
        "document_where": "README.md, docs/workflow.md",
    },
    "scripts/analyze_job.sh": {
        "status": "authoritative",
        "purpose": "Condor worker wrapper for pT-resolution analysis.",
        "document_where": "docs/workflow.md",
    },
    "configs/condor/analyze_CF25_Au2p227matched.condor": {
        "status": "campaign-specific",
        "purpose": "Campaign-specific Condor submission for CF closeout analysis.",
        "document_where": "docs/workflow.md",
    },
    "configs/condor/analyze_W20_Au0p3_defaultlike.condor": {
        "status": "campaign-specific",
        "purpose": "Campaign-specific Condor submission for W closeout analysis.",
        "document_where": "docs/workflow.md",
    },
    "configs/condor/analyze.condor": {
        "status": "secondary",
        "purpose": "Generic/shared analysis Condor template.",
        "document_where": "docs/workflow.md if still used",
    },
    "scripts/compare_pt_resolution_grid.py": {
        "status": "authoritative",
        "purpose": "Compare two pT-resolution summary ROOT outputs.",
        "document_where": "README.md, docs/workflow.md",
    },
    "scripts/summarize_ptres_improvement.py": {
        "status": "authoritative",
        "purpose": "Build closeout improvement summaries and CSV/text/ROOT products.",
        "document_where": "docs/workflow.md",
    },
    "scripts/export_root_plots.py": {
        "status": "authoritative",
        "purpose": "Recursively export ROOT objects to PNG/PDF.",
        "document_where": "docs/workflow.md",
    },

    # Configs
    "configs/geom/compact.xml": {
        "status": "authoritative",
        "purpose": "Maintained geometry/config reference used by workflow.",
        "document_where": "docs/workflow.md, docs/directory_layout.md",
    },
    "configs/tracker_params.json": {
        "status": "authoritative",
        "purpose": "Maintained tracking parameter config.",
        "document_where": "docs/workflow.md or config section",
    },
    "configs/test.yaml": {
        "status": "authoritative",
        "purpose": "Maintained workflow/config file.",
        "document_where": "docs/workflow.md or config section",
    },
    "configs/condor/ddsim.condor": {
        "status": "authoritative",
        "purpose": "Condor submit description for DDSim single-particle gun-production jobs.",
        "document_where": "README.md, docs/workflow.md, docs/directory_layout.md",
    },

    # Secondary operational utilities
    "scripts/scan_pt_time_by_event.py": {
        "status": "secondary",
        "purpose": "Per-event scanner used by pT-resolution analysis.",
        "document_where": "scripts/README.md",
    },
    "scripts/debug_z_spur_event.py": {
        "status": "secondary",
        "purpose": "Debug suspicious z-spur or event-level pathology.",
        "document_where": "scripts/README.md",
    },
    "scripts/dump_covmatrix_one_event.py": {
        "status": "secondary",
        "purpose": "Dump one-event covariance information for debugging.",
        "document_where": "scripts/README.md",
    },
    "scripts/inspect_events_pt_pathology.py": {
        "status": "secondary",
        "purpose": "Inspect events with pathological pT behavior.",
        "document_where": "scripts/README.md",
    },
    "scripts/view_simhits_event.py": {
        "status": "secondary",
        "purpose": "Event display / inspection utility for sim hits.",
        "document_where": "scripts/README.md",
    },
    "scripts/view_tracks_event.py": {
        "status": "secondary",
        "purpose": "Event display / inspection utility for tracks.",
        "document_where": "scripts/README.md",
    },
    "scripts/plot_mcparticles_pt.py": {
        "status": "secondary",
        "purpose": "Plot MC-particle pT distributions.",
        "document_where": "scripts/README.md",
    },
    "scripts/plot_pt_from_trackstate_time.py": {
        "status": "secondary",
        "purpose": "Inspect pT encoded in trackStates.time.",
        "document_where": "scripts/README.md",
    },
    "scripts/stamp_pipeline_metadata.py": {
        "status": "secondary",
        "purpose": "Stamp provenance metadata into ROOT outputs.",
        "document_where": "scripts/README.md, workflow appendix",
    },
    "scripts/stamp_ddsim_metadata.py": {
        "status": "secondary",
        "purpose": "Stamp DDsim-related metadata.",
        "document_where": "scripts/README.md",
    },
    "scripts/print_metadata.py": {
        "status": "secondary",
        "purpose": "Read/display stamped metadata.",
        "document_where": "scripts/README.md",
    },
    "scripts/autoreadme.py": {
        "status": "secondary",
        "purpose": "Generate directory READMEs, DOCS_INDEX.md, and docs/chain.mmd from DOC blocks and heuristics.",
        "document_where": "scripts/README.md",
    },

    # Legacy wrappers
    "scripts/prepare_and_submit.sh": {
        "status": "authoritative",
        "purpose": "Submission wrapper for DDSim gun-production campaigns.",
        "document_where": "README.md, docs/workflow.md",
    },
    "scripts/prepare_and_submit_CF25_Au2p227matched.sh": {
        "status": "legacy",
        "purpose": "Variant-specific older wrapper.",
        "document_where": "archive note",
    },
    "scripts/prepare_and_submit_W20_Au0p3_defaultlike.sh": {
        "status": "legacy",
        "purpose": "Variant-specific older wrapper.",
        "document_where": "archive note",
    },
    "scripts/condor_ddsim.sh": {
        "status": "authoritative",
        "purpose": "Condor worker wrapper for DDSim gun production, validation, metadata stamping, and EOS staging.",
        "document_where": "README.md, docs/workflow.md",
    },
    "archive/legacy_reco_wrappers/condor_reco.sh": {
        "status": "legacy",
        "purpose": "Old reco worker wrapper superseded by submit_reco.sh -> reco.condor -> reco_job.sh.",
        "document_where": "archive note only",
    },
    "test_trackFinder.sh": {
        "status": "legacy",
        "purpose": "Older local test runner.",
        "document_where": "archive note",
    },

    # Side-study / auxiliary
    "scripts/sweep_pt.sh": {
        "status": "secondary",
        "purpose": "Convenience helper for pT sweeps; confirm whether still active.",
        "document_where": "scripts/README.md",
    },
    "scripts/Calculate_Aucoating_thickness.py": {
        "status": "secondary",
        "purpose": "Side-study / materials utility.",
        "document_where": "scripts/README.md",
    },
    "scripts/patch_trkCov_match_dch_material.py": {
        "status": "secondary",
        "purpose": "Side-study / materials/config patch helper.",
        "document_where": "scripts/README.md",
    },
    "scripts/dch_x0_per_layer.py": {
        "status": "secondary",
        "purpose": "Material-budget / per-layer utility.",
        "document_where": "scripts/README.md",
    },
    "scripts/DelphesParamsOutput.py": {
        "status": "secondary",
        "purpose": "Delphes-related helper outside main reco closeout path.",
        "document_where": "scripts/README.md",
    },
    "scripts/mk_ddsim_grid.py": {
        "status": "secondary",
        "purpose": "Campaign/grid-generation helper.",
        "document_where": "scripts/README.md",
    },
    "scripts/collect_knobs.py": {
        "status": "secondary",
        "purpose": "Knob/config collection helper.",
        "document_where": "scripts/README.md",
    },

    # Archive candidates
    "scripts/cglenn.cc": {
        "status": "archive-candidate",
        "purpose": "Unclear workflow role; archive unless demonstrably active.",
        "document_where": "none unless still active",
    },
    "cglenn.cc": {
        "status": "archive-candidate",
        "purpose": "Unclear workflow role; archive unless demonstrably active.",
        "document_where": "none unless still active",
    },
}


# =============================================================================
# Regex helpers
# =============================================================================

PY_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([A-Za-z0-9_\.]+)\s+import|import\s+([A-Za-z0-9_\.]+))"
)
CPP_INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"]([^">]+)[">]')
BASH_CALL_RE = re.compile(
    r"^\s*(?:\./|bash\s+|sh\s+|zsh\s+|python3\s+|python\s+)([A-Za-z0-9_\-./]+)"
)
K4RUN_RE = re.compile(r"\bk4run\b")
CONDOR_RE = re.compile(r"\bcondor_submit\b|\bqueue\b|\bJobFlavour\b", re.IGNORECASE)
XRDCP_RE = re.compile(r"\bxrdcp\b|\bxrdfs\b")
EOS_RE = re.compile(r"/eos/|root://eos", re.IGNORECASE)

GAUDI_CONFIGURABLES_RE = re.compile(r"^\s*from\s+Configurables\s+import\s+(.+)$")
GAUDI_TOPALG_RE = re.compile(r"\bTopAlg\b|\bApplicationMgr\b|\bEvtSel\b|\bEventSelector\b")
GAUDI_DECLARE_COMPONENT_RE = re.compile(
    r"\bDECLARE_COMPONENT\b|\bDECLARE_FACTORY\b|\bDECLARE_ALGORITHM_FACTORY\b"
)

ARGPARSE_RE = re.compile(r"\bargparse\.ArgumentParser\b|\badd_argument\(")
ARGPARSE_ADDARG_RE = re.compile(
    r"""add_argument\(\s*([^\)]*?)\s*\)""",
    flags=re.IGNORECASE | re.DOTALL,
)

GAUDI_PROPERTY_RE = re.compile(
    r"""Gaudi::Property<\s*([^>]+?)\s*>\s+([A-Za-z0-9_]+)\s*\{\s*this\s*,\s*"([^"]+)"\s*,\s*([^,}]+)""",
    flags=re.MULTILINE,
)

ENV_DEFAULT_RE = re.compile(r"""^\s*:?\s*"?\$?\{?([A-Z][A-Z0-9_]+).*?:[=-]([^}"]+)""")
SHELL_VAR_DEFAULT_RE = re.compile(r"""^\s*([A-Z][A-Z0-9_]+)=["']?\$\{[A-Z0-9_]+:-([^}"']+)""")
DOC_START_TOKENS = {
    "DOC",
    "DOC:",
    "DOC_START",
    "DOC_BEGIN",
    "DOCBLOCK",
    "DOC_BLOCK",
    "BEGIN_DOC",
}
DOC_END_TOKENS = {
    "DOC_END",
    "END_DOC",
    "DOC_STOP",
    "DOC_FINISH",
}

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
    re.VERBOSE,
)

TRIPLE_QUOTE_ONLY_RE = re.compile(r"""^\s*("{3}|'{3})\s*$""")


# =============================================================================
# Data model
# =============================================================================

@dataclass
class FileDoc:
    path: Path
    relpath: str

    summary: str = ""
    purpose: str = ""
    status: str = "unknown"
    document_where: str = ""
    usage: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    inputs: str = ""
    outputs: str = ""
    connects_to: List[str] = field(default_factory=list)
    collections: str = ""
    arguments: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    inferred_links: List[str] = field(default_factory=list)
    inferred_arguments: List[str] = field(default_factory=list)
    inferred_env_knobs: List[str] = field(default_factory=list)

    has_doc_block: bool = False
    from_project_classification: bool = False


@dataclass
class Options:
    root: Path
    write: bool
    no_graph: bool
    check: bool
    inject_stubs: bool
    include_archive: bool
    include_artifacts: bool
    overwrite_curated: bool
    all_dirs: bool
    generated_readme_dirs: Set[str]
    classification_file: Optional[Path]
    strict_status: bool


# =============================================================================
# Basic helpers
# =============================================================================

def relpath(p: Path, root: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return p.as_posix()


def md_escape(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", "<br>")


def normalize_relpath(s: str) -> str:
    return Path(s).as_posix().strip("./")


def read_text_safely(p: Path) -> str:
    try:
        data = p.read_bytes()
        if len(data) > TEXTFILE_MAX_BYTES:
            return ""
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""


def status_sort_key(status: str) -> int:
    try:
        return STATUS_ORDER.index(status)
    except ValueError:
        return len(STATUS_ORDER)


def split_csvish(vals: Iterable[str]) -> List[str]:
    out: List[str] = []
    for val in vals:
        for item in re.split(r"[,;]", val):
            item = item.strip()
            if item:
                out.append(item)
    return out


def uniqued(seq: Iterable[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in seq:
        if not x:
            continue
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


# =============================================================================
# DOC block parsing
# =============================================================================

def _strip_leading_comment(line: str) -> str:
    return COMMENT_PREFIX_RE.sub("", line, count=1).rstrip()


def _normalize_marker(s: str) -> str:
    s2 = _strip_leading_comment(s).strip()
    s2 = s2.strip("[](){}")
    s2 = re.sub(r"\s+", " ", s2)
    return s2.upper()


def _is_doc_start(line: str) -> bool:
    return _normalize_marker(line) in DOC_START_TOKENS


def _is_doc_end(line: str) -> bool:
    return _normalize_marker(line) in DOC_END_TOKENS


def _strip_doc_line(line: str) -> Optional[str]:
    ln2 = _strip_leading_comment(line)
    if TRIPLE_QUOTE_ONLY_RE.match(ln2.strip()):
        return None
    if not ln2.strip():
        return None
    return ln2.rstrip()


def _canonical_key(k: str) -> str:
    k0 = k.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "connects": "connects_to",
        "connects_to": "connects_to",
        "connects-to": "connects_to",
        "collections": "collections",
        "inputs": "inputs",
        "outputs": "outputs",
        "summary": "summary",
        "purpose": "purpose",
        "usage": "usage",
        "examples": "examples",
        "example": "examples",
        "args": "arguments",
        "arguments": "arguments",
        "parameters": "arguments",
        "properties": "arguments",
        "tags": "tags",
        "notes": "notes",
        "status": "status",
        "document_where": "document_where",
        "document-where": "document_where",
        "doc": "document_where",
    }
    return aliases.get(k0, k0)


def parse_doc_block(text: str) -> Dict[str, List[str]]:
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
    header_re = re.compile(r"^([A-Za-z0-9_\- ]+)\s*:\s*(.*)$")

    for ln in block:
        m = header_re.match(ln)
        if m:
            current_key = _canonical_key(m.group(1))
            fields.setdefault(current_key, [])
            val = m.group(2).strip()
            if val:
                fields[current_key].append(val)
        elif current_key:
            fields.setdefault(current_key, []).append(ln.strip())

    return fields


def file_contains_any_doc_marker(text: str) -> bool:
    for ln in text.splitlines()[:DOC_SCAN_MAX_LINES]:
        if _is_doc_start(ln):
            return True
    return False


# =============================================================================
# Heuristic extraction
# =============================================================================

def fallback_summary(text: str) -> str:
    m = re.search(r'^\s*"""(.*?)"""', text, flags=re.DOTALL | re.MULTILINE)
    if m:
        body = m.group(1).strip()
        for line in body.splitlines():
            line = line.strip()
            if line and line.upper() not in DOC_START_TOKENS and line.upper() not in DOC_END_TOKENS:
                return line[:220]

    for ln in text.splitlines()[:80]:
        s = ln.strip()
        if s.startswith("#") or s.startswith("//"):
            cleaned = re.sub(r"^(#|//)\s*", "", s).strip()
            if cleaned and not cleaned.lower().startswith(("copyright", "license", "doc", "doc_end")):
                return cleaned[:220]

    if ARGPARSE_RE.search(text):
        return "CLI script; argparse detected."
    if GAUDI_TOPALG_RE.search(text) and "Configurables" in text:
        return "Gaudi options/config file; inferred from Configurables/ApplicationMgr."
    if CONDOR_RE.search(text):
        return "Condor submit/config file; inferred from Condor syntax."
    return ""


def infer_links(p: Path, text: str) -> List[str]:
    links: Set[str] = set()
    lines = text.splitlines()
    head = lines[:900]
    full = lines[:3500]

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
    if XRDCP_RE.search(text):
        links.add("uses:xrootd")
    if EOS_RE.search(text):
        links.add("uses:eos")

    for ln in full:
        if GAUDI_CONFIGURABLES_RE.match(ln):
            links.add("gaudi:imports:Configurables")
            break

    joined = " ".join(full)
    for alg in re.findall(r'"([A-Za-z0-9_]+)"', joined):
        if len(alg) >= 4 and any(
            k in alg.lower()
            for k in ("track", "dch", "fit", "gtt", "ggtf", "acts", "genfit", "digi")
        ):
            links.add(f"gaudi:topalg:{alg}")

    if p.suffix in (".cpp", ".cc", ".cxx") and GAUDI_DECLARE_COMPONENT_RE.search(text):
        links.add("gaudi:declares_component")

    return sorted(links)


def infer_argparse_arguments(text: str, max_items: int = 45) -> List[str]:
    if not ARGPARSE_RE.search(text):
        return []

    out: List[str] = []
    window = "\n".join(text.splitlines()[:3000])

    for m in ARGPARSE_ADDARG_RE.finditer(window):
        body = re.sub(r"\s+", " ", m.group(1)).strip()
        if not body:
            continue

        opts = re.findall(r"""["'](--?[A-Za-z0-9_\-]+)["']""", body)
        opt = ", ".join(opts[:3]) if opts else ""

        default = ""
        dm = re.search(r"\bdefault\s*=\s*([^,\)]+)", body)
        if dm:
            default = dm.group(1).strip()

        help_s = ""
        hm = re.search(r"""\bhelp\s*=\s*["']([^"']+)["']""", body)
        if hm:
            help_s = hm.group(1).strip()

        if opt:
            parts = [opt]
            if default:
                parts.append(f"default={default}")
            if help_s:
                parts.append(help_s)
            out.append("  - " + " | ".join(parts))
        else:
            out.append("  - " + body[:180] + ("..." if len(body) > 180 else ""))

        if len(out) >= max_items:
            break

    return out


def infer_gaudi_properties_cpp(text: str, max_items: int = 50) -> List[str]:
    out: List[str] = []
    for m in GAUDI_PROPERTY_RE.finditer(text[:450_000]):
        typ = m.group(1).strip()
        member = m.group(2).strip()
        propname = m.group(3).strip()
        default = m.group(4).strip()

        start = m.end()
        eol = text.find("\n", start)
        if eol == -1:
            eol = min(len(text), start + 400)
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


def infer_shell_env_knobs(text: str, max_items: int = 80) -> List[str]:
    out: List[str] = []
    for line in text.splitlines()[:2000]:
        s = line.strip()
        if not s or s.startswith("#"):
            continue

        m = SHELL_VAR_DEFAULT_RE.match(s)
        if m:
            out.append(f"  - {m.group(1)} | default={m.group(2)}")
            continue

        m2 = re.match(r""":\s*"\$\{([A-Z][A-Z0-9_]+):=([^}]+)\}""", s)
        if m2:
            out.append(f"  - {m2.group(1)} | default={m2.group(2)}")

        if len(out) >= max_items:
            break

    return uniqued(out)


# =============================================================================
# Classification loading
# =============================================================================

def load_external_classification(path: Optional[Path]) -> Dict[str, Dict[str, str]]:
    if not path:
        return {}

    if not path.exists():
        raise SystemExit(f"classification file does not exist: {path}")

    suffix = path.suffix.lower()
    data: Dict[str, Dict[str, str]] = {}

    if suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for k, v in raw.items():
                if isinstance(v, dict):
                    data[normalize_relpath(k)] = {str(kk): str(vv) for kk, vv in v.items()}
        return data

    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get("File") or row.get("file") or row.get("path") or row.get("Path")
                if not key:
                    continue
                data[normalize_relpath(key)] = {
                    "purpose": row.get("Purpose", row.get("purpose", "")),
                    "status": row.get("Status", row.get("status", "")),
                    "document_where": row.get("Document where", row.get("document_where", "")),
                }
        return data

    raise SystemExit(
        "Unsupported classification file format. Use JSON or CSV. "
        f"Got: {path}"
    )


def normalize_status(status: str) -> str:
    s = status.strip().lower()
    s = s.replace("_", "-")
    if not s:
        return "unknown"
    if "campaign" in s:
        return "campaign-specific"
    if "authoritative" in s:
        return "authoritative"
    if "secondary" in s:
        return "secondary"
    if "legacy" in s:
        return "legacy"
    if "archive" in s:
        return "archive-candidate"
    return s if s in STATUS_ORDER else "unknown"


def classification_for(rel: str, external: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    rel_norm = normalize_relpath(rel)
    merged: Dict[str, str] = {}
    if rel_norm in PROJECT_CLASSIFICATION:
        merged.update(PROJECT_CLASSIFICATION[rel_norm])
    if rel_norm in external:
        merged.update({k: v for k, v in external[rel_norm].items() if v})
    return merged


# =============================================================================
# File selection and construction
# =============================================================================

def should_ignore_path(p: Path, root: Path, opts: Options) -> bool:
    rel = relpath(p, root)
    parts = set(Path(rel).parts)

    ignore_parts = set(DEFAULT_IGNORE_DIR_PARTS)
    if opts.include_archive:
        ignore_parts.discard("archive")
    if opts.include_artifacts:
        ignore_parts.discard("artifacts")

    if any(part in ignore_parts for part in parts):
        return True
    if p.name in ALWAYS_IGNORE_FILE_NAMES:
        return True
    if p.name.startswith(".") and p.name not in {".gitignore"}:
        return True
    return False


def is_interesting_file(p: Path, root: Path, opts: Options) -> bool:
    if not p.is_file():
        return False
    if should_ignore_path(p, root, opts):
        return False
    if p.name in {"DOCS_INDEX.md"}:
        return False
    if p.name == "README.md":
        return False
    if p.suffix and p.suffix not in INCLUDE_EXTS:
        return False
    return True


def is_important(fd: FileDoc) -> bool:
    """
    Files that make --check fail if missing DOC blocks.

    Project policy:
      - authoritative and campaign-specific workflow files should have DOC blocks
      - secondary utilities should be documented, but missing DOC blocks should not block cleanup
      - legacy/archive-candidate files should not block cleanup
    """
    return fd.status in {"authoritative", "campaign-specific"}


def build_filedoc(
    p: Path,
    root: Path,
    external_classification: Dict[str, Dict[str, str]],
) -> Optional[FileDoc]:
    text = read_text_safely(p)
    if not text:
        return None

    rp = relpath(p, root)
    fields = parse_doc_block(text)
    fd = FileDoc(path=p, relpath=rp)

    c = classification_for(rp, external_classification)
    if c:
        fd.from_project_classification = True
        fd.status = normalize_status(c.get("status", ""))
        fd.purpose = c.get("purpose", "")
        fd.document_where = c.get("document_where", "")

    if fields:
        fd.has_doc_block = True

        fd.summary = " ".join(fields.get("summary", [])).strip()
        fd.purpose = " ".join(fields.get("purpose", [])).strip() or fd.purpose
        if fields.get("status"):
            fd.status = normalize_status(" ".join(fields.get("status", [])))
        if fields.get("document_where"):
            fd.document_where = " ".join(fields.get("document_where", [])).strip()

        fd.usage = fields.get("usage", [])
        fd.examples = fields.get("examples", [])
        fd.inputs = " ".join(fields.get("inputs", [])).strip()
        fd.outputs = " ".join(fields.get("outputs", [])).strip()
        fd.collections = " ".join(fields.get("collections", [])).strip()
        fd.connects_to = fields.get("connects_to", [])
        fd.arguments = fields.get("arguments", [])
        fd.notes.extend(fields.get("notes", []))

        fd.tags = sorted(set(split_csvish(fields.get("tags", []))))

    if not fd.summary:
        fd.summary = fd.purpose or fallback_summary(text)

    fd.inferred_links = infer_links(p, text)

    if p.suffix == ".py":
        fd.inferred_arguments = infer_argparse_arguments(text)
    elif p.suffix in (".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hh"):
        fd.inferred_arguments = infer_gaudi_properties_cpp(text)
    elif p.suffix in (".sh", ".bash", ".zsh"):
        fd.inferred_env_knobs = infer_shell_env_knobs(text)

    if not fd.summary:
        fd.notes.append("missing_summary")
    if not fd.has_doc_block:
        fd.notes.append("no_doc_block")
    if fd.status == "unknown":
        fd.notes.append("unknown_status")

    return fd


# =============================================================================
# Stub injection
# =============================================================================

def comment_prefix_for_path(p: Path) -> str:
    if p.suffix in (".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hh"):
        return "// "
    if p.suffix in (".sh", ".bash", ".zsh"):
        return "# "
    if p.suffix in (".ini", ".cfg", ".condor", ".submit"):
        return "# "
    if p.suffix in (".yaml", ".yml"):
        return "# "
    if p.suffix == ".tcl":
        return "# "
    if p.suffix == ".xml":
        return ""
    return "# "


def inject_stub_doc_block(p: Path, fd: Optional[FileDoc] = None) -> bool:
    text = read_text_safely(p)
    if not text:
        return False
    if file_contains_any_doc_marker(text):
        return False

    prefix = comment_prefix_for_path(p)
    if not prefix:
        return False

    purpose = fd.purpose if fd else ""
    status = fd.status if fd else "unknown"

    stub = (
        f"{prefix}DOC:\n"
        f"{prefix}Summary: TODO one-line description"
        + (f" ({purpose})" if purpose else "")
        + "\n"
        f"{prefix}Status: {status}\n"
        f"{prefix}Usage:\n"
        f"{prefix}  TODO how to run / include\n"
        f"{prefix}Examples:\n"
        f"{prefix}  TODO example command(s) + expected result\n"
        f"{prefix}Inputs: TODO input files/classes/collections\n"
        f"{prefix}Outputs: TODO output files/classes/collections\n"
        f"{prefix}Collections: TODO collection names and types/schemas\n"
        f"{prefix}Connects-To: TODO upstream/downstream files/components\n"
        f"{prefix}Arguments: TODO important args/properties/defaults\n"
        f"{prefix}Tags: TODO comma,separated,tags\n"
        f"{prefix}DOC_END\n\n"
    )

    p.write_text(stub + text, encoding="utf-8")
    return True


# =============================================================================
# Markdown rendering
# =============================================================================

def render_generated_header(scope: str) -> List[str]:
    return [
        f"{GENERATED_DOC_MARKER_BEGIN}\n",
        f"<!-- Generated by {VERSION}. Do not hand-edit inside this block. -->\n\n",
        f"# {scope}\n\n",
        "This section is auto-generated from project classification, per-file DOC blocks, and conservative heuristics.\n\n",
        "Project rule: curated workflow docs remain authoritative. This generated content is an inventory and maintenance aid.\n\n",
    ]


def render_status_group(fd_list: List[FileDoc], root: Path, local_dir: Optional[Path] = None) -> List[str]:
    lines: List[str] = []

    for status in STATUS_ORDER:
        group = [fd for fd in fd_list if fd.status == status]
        if not group:
            continue

        lines.append(f"\n## {STATUS_BADGE.get(status, '•')} {STATUS_LABEL.get(status, status)}\n\n")
        lines.append("| File | Summary / purpose | Usage | Connects-To | Inferred |\n")
        lines.append("|---|---|---|---|---|\n")

        for fd in sorted(group, key=lambda x: x.path.name.lower()):
            display_name = fd.path.name if local_dir else fd.relpath
            usage = "<br>".join(md_escape(u) for u in fd.usage[:3]) if fd.usage else ""
            conns = "<br>".join(md_escape(c) for c in fd.connects_to[:6]) if fd.connects_to else ""
            inf = "<br>".join(md_escape(i) for i in fd.inferred_links[:10]) if fd.inferred_links else ""
            summary = fd.summary or fd.purpose
            if fd.document_where:
                summary = f"{summary}<br><sub>Doc: {md_escape(fd.document_where)}</sub>"
            doc_badge = "DOC" if fd.has_doc_block else "heuristic"
            lines.append(
                f"| `{display_name}`<br><sub>{doc_badge}</sub> | "
                f"{md_escape(summary)} | {usage} | {conns} | {inf} |\n"
            )

    return lines


def render_details(fd_list: List[FileDoc]) -> List[str]:
    detail_files = [
        fd for fd in fd_list
        if fd.inputs
        or fd.outputs
        or fd.collections
        or fd.examples
        or fd.arguments
        or fd.inferred_arguments
        or fd.inferred_env_knobs
        or fd.notes
    ]

    if not detail_files:
        return []

    lines: List[str] = ["\n## Details\n\n"]

    for fd in sorted(detail_files, key=lambda x: (status_sort_key(x.status), x.path.name.lower())):
        lines.append(f"### `{fd.path.name}`\n\n")
        lines.append(f"- **Status:** {STATUS_LABEL.get(fd.status, fd.status)}\n")
        if fd.purpose and fd.purpose != fd.summary:
            lines.append(f"- **Purpose:** {md_escape(fd.purpose)}\n")
        if fd.inputs:
            lines.append(f"- **Inputs:** {md_escape(fd.inputs)}\n")
        if fd.outputs:
            lines.append(f"- **Outputs:** {md_escape(fd.outputs)}\n")
        if fd.collections:
            lines.append(f"- **Collections:** {md_escape(fd.collections)}\n")
        if fd.tags:
            lines.append(f"- **Tags:** {md_escape(', '.join(fd.tags))}\n")
        if fd.notes:
            lines.append(f"- **Notes:** {md_escape(', '.join(uniqued(fd.notes)))}\n")

        if fd.examples:
            lines.append("\n**Examples**\n\n")
            for ex in fd.examples[:16]:
                lines.append(f"- {md_escape(ex)}\n")

        if fd.arguments:
            lines.append("\n**Arguments / properties from DOC block**\n\n")
            for a in fd.arguments[:45]:
                lines.append(f"- {md_escape(a)}\n")

        if fd.inferred_arguments:
            lines.append("\n**Arguments / properties inferred**\n\n")
            for a in fd.inferred_arguments[:45]:
                lines.append(f"{md_escape(a)}\n")

        if fd.inferred_env_knobs:
            lines.append("\n**Environment knobs inferred**\n\n")
            for a in fd.inferred_env_knobs[:80]:
                lines.append(f"{md_escape(a)}\n")

        lines.append("\n")

    return lines


def generated_block(content_lines: List[str]) -> str:
    lines = list(content_lines)
    if not lines or lines[-1].strip() != GENERATED_DOC_MARKER_END:
        lines.append(f"{GENERATED_DOC_MARKER_END}\n")
    return "".join(lines)


def replace_generated_block(existing: str, new_block: str) -> str:
    if GENERATED_DOC_MARKER_BEGIN in existing and GENERATED_DOC_MARKER_END in existing:
        pattern = re.compile(
            re.escape(GENERATED_DOC_MARKER_BEGIN)
            + r".*?"
            + re.escape(GENERATED_DOC_MARKER_END),
            flags=re.DOTALL,
        )
        return pattern.sub(new_block.rstrip(), existing).rstrip() + "\n"

    if existing.strip():
        return existing.rstrip() + "\n\n" + new_block
    return new_block


def write_text_file(path: Path, content: str, write: bool, protect_existing: bool = False) -> None:
    if protect_existing and path.exists():
        existing = path.read_text(encoding="utf-8", errors="replace")
        content = replace_generated_block(existing, content)

    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"[write] {path}")
    else:
        print(f"[dry] would write {path}")


def should_write_readme_for_dir(d: Path, root: Path, opts: Options) -> bool:
    rp = relpath(d, root)
    if rp == ".":
        return opts.overwrite_curated
    if opts.all_dirs:
        return True
    return rp in opts.generated_readme_dirs


def write_dir_readme(dirpath: Path, root: Path, docs: List[FileDoc], opts: Options) -> None:
    if not docs:
        return
    if not should_write_readme_for_dir(dirpath, root, opts):
        return

    rp = relpath(dirpath, root)
    if rp == ".":
        title = "testTrackFinder generated file inventory"
    else:
        title = f"{rp}/ generated file inventory"

    lines = render_generated_header(title)

    lines.extend(
        [
            "## Regenerate\n\n",
            "```bash\n",
            "python3 scripts/autoreadme.py --root . --write\n",
            "```\n\n",
            "DOC blocks are preferred over heuristics. Use `Status:` and `Tags:` fields for classification.\n",
        ]
    )

    lines.extend(render_status_group(docs, root, local_dir=dirpath))
    lines.extend(render_details(docs))
    content = generated_block(lines)

    out = dirpath / "README.md"
    protect = out.exists() and relpath(out, root) in PROTECTED_CURATED_DOCS
    if protect and not opts.overwrite_curated:
        print(f"[skip] protected curated README: {out}")
        return

    write_text_file(out, content, write=opts.write, protect_existing=out.exists())


def write_docs_index(root: Path, all_docs: List[FileDoc], opts: Options) -> None:
    lines: List[str] = []
    lines.extend(render_generated_header("testTrackFinder documentation index"))

    lines.extend(
        [
            "## Curated docs\n\n",
            "- `README.md` — main human-written workflow entry point.\n",
            "- `docs/workflow.md` — authoritative operational workflow.\n",
            "- `docs/directory_layout.md` — directory contract and cleanup policy.\n",
            "- `docs/chain.mmd` — generated Mermaid graph of detected file/component links.\n\n",
            "## Regenerate\n\n",
            "```bash\n",
            "python3 scripts/autoreadme.py --root . --write\n",
            "```\n\n",
        ]
    )

    by_dir: Dict[str, List[FileDoc]] = {}
    for fd in all_docs:
        by_dir.setdefault(str(Path(fd.relpath).parent).replace(".", ""), []).append(fd)

    lines.append("## Generated/readable directory inventories\n\n")
    candidate_dirs = sorted({str(fd.path.parent.relative_to(root)).replace(".", "") for fd in all_docs})
    for d in candidate_dirs:
        d_clean = d.strip("/")
        if not d_clean:
            continue
        if opts.all_dirs or d_clean in opts.generated_readme_dirs:
            lines.append(f"- `{d_clean}/README.md`\n")

    lines.append("\n## Main authoritative path\n\n")
    main = [fd for fd in all_docs if fd.status in {"authoritative", "campaign-specific"}]
    lines.extend(render_status_group(main, root, local_dir=None))

    lines.append("\n## Full file index\n\n")
    lines.append("| Path | Status | Summary / purpose | DOC | Tags |\n")
    lines.append("|---|---|---|---|---|\n")

    for fd in sorted(all_docs, key=lambda x: (status_sort_key(x.status), x.relpath.lower())):
        tags = ", ".join(fd.tags)
        docflag = "yes" if fd.has_doc_block else "no"
        summary = fd.summary or fd.purpose
        lines.append(
            f"| `{fd.relpath}` | {STATUS_LABEL.get(fd.status, fd.status)} | "
            f"{md_escape(summary)} | {docflag} | {md_escape(tags)} |\n"
        )

    content = generated_block(lines)
    write_text_file(root / "DOCS_INDEX.md", content, write=opts.write, protect_existing=False)


def write_mermaid_graph(root: Path, all_docs: List[FileDoc], opts: Options) -> None:
    docs_dir = root / "docs"
    out = docs_dir / "chain.mmd"

    edges: Set[Tuple[str, str]] = set()
    nodes: Set[str] = set()

    def node_id(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]", "_", s)

    basename_to_rel: Dict[str, str] = {}
    rel_to_rel: Dict[str, str] = {}
    for fd in all_docs:
        basename_to_rel[fd.path.name] = fd.relpath
        rel_to_rel[fd.relpath] = fd.relpath

    for fd in all_docs:
        src = fd.relpath
        nodes.add(src)

        for c in fd.connects_to:
            c_norm = normalize_relpath(c)
            tgt = rel_to_rel.get(c_norm) or basename_to_rel.get(Path(c_norm).name) or c_norm
            edges.add((src, tgt))
            nodes.add(tgt)

        for inf in fd.inferred_links:
            if inf.startswith("calls:"):
                raw = normalize_relpath(inf.replace("calls:", ""))
                tgt = rel_to_rel.get(raw) or basename_to_rel.get(Path(raw).name) or raw
                edges.add((src, tgt))
                nodes.add(tgt)
            elif inf.startswith("gaudi:topalg:"):
                alg = inf.replace("gaudi:topalg:", "")
                tgt = f"Alg::{alg}"
                edges.add((src, tgt))
                nodes.add(tgt)
            elif inf.startswith("uses:k4run"):
                tgt = "Tool::k4run"
                edges.add((src, tgt))
                nodes.add(tgt)
            elif inf.startswith("uses:condor"):
                tgt = "Tool::HTCondor"
                edges.add((src, tgt))
                nodes.add(tgt)

    lines: List[str] = [
        "%% Generated by autoreadme.py. Do not hand edit unless you stop regenerating it.\n",
        "flowchart LR\n",
    ]

    for n in sorted(nodes):
        safe_label = n.replace('"', "'")
        lines.append(f'  {node_id(n)}["{safe_label}"]\n')
    for a, b in sorted(edges):
        lines.append(f"  {node_id(a)} --> {node_id(b)}\n")

    content = "".join(lines)
    if opts.write:
        docs_dir.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
        print(f"[write] {out}")
    else:
        print(f"[dry] would write {out}")


# =============================================================================
# Checks
# =============================================================================

def run_checks(all_docs: List[FileDoc], opts: Options) -> int:
    failures: List[str] = []

    for fd in all_docs:
        if is_important(fd) and not fd.has_doc_block:
            failures.append(f"missing DOC block in authoritative/campaign file: {fd.relpath}")
        elif fd.status == "secondary" and not fd.has_doc_block:
            print(f"[check][warn] secondary file lacks DOC block: {fd.relpath}")
        elif fd.status in {"legacy", "archive-candidate"} and not fd.has_doc_block:
            print(f"[check][info] legacy/archive-candidate lacks DOC block: {fd.relpath}")

        if opts.strict_status and fd.status == "unknown":
            failures.append(f"unknown status: {fd.relpath}")

        if fd.status in {"authoritative", "campaign-specific"} and not fd.summary:
            failures.append(f"authoritative file missing summary: {fd.relpath}")

    if failures:
        print("[check] Problems found:")
        for f in failures:
            print(f"  - {f}")
        return 2

    print("[check] OK")
    return 0


# =============================================================================
# Main
# =============================================================================

def parse_args(argv: Optional[Sequence[str]] = None) -> Options:
    ap = argparse.ArgumentParser(
        description="Generate project-aware documentation inventories for testTrackFinder."
    )
    ap.add_argument("--root", required=True, help="Path to Tracking/test/testTrackFinder root.")
    ap.add_argument("--write", action="store_true", help="Actually write files.")
    ap.add_argument("--no-graph", action="store_true", help="Skip docs/chain.mmd.")
    ap.add_argument("--check", action="store_true", help="Validate DOC/status coverage.")
    ap.add_argument("--inject-stubs", action="store_true", help="Insert DOC stubs into important files missing them.")
    ap.add_argument("--include-archive", action="store_true", help="Include archive/ in scan.")
    ap.add_argument("--include-artifacts", action="store_true", help="Include artifacts/ in scan.")
    ap.add_argument(
        "--overwrite-curated",
        action="store_true",
        help="Allow generated block insertion into curated/protected docs.",
    )
    ap.add_argument(
        "--all-dirs",
        action="store_true",
        help="Generate README.md in every scanned directory, not only configured dirs.",
    )
    ap.add_argument(
        "--generated-readme-dir",
        action="append",
        default=[],
        help="Directory where README.md generation is allowed. Can be repeated.",
    )
    ap.add_argument(
        "--classification-file",
        default="",
        help="Optional external JSON/CSV classification file overriding built-ins.",
    )
    ap.add_argument(
        "--strict-status",
        action="store_true",
        help="In --check mode, fail if any scanned file has unknown status.",
    )

    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit(f"Not a directory: {root}")

    generated_dirs = set(DEFAULT_GENERATED_README_DIRS)
    generated_dirs.update(normalize_relpath(x) for x in args.generated_readme_dir)

    cls_file = Path(args.classification_file).resolve() if args.classification_file else None

    return Options(
        root=root,
        write=bool(args.write),
        no_graph=bool(args.no_graph),
        check=bool(args.check),
        inject_stubs=bool(args.inject_stubs),
        include_archive=bool(args.include_archive),
        include_artifacts=bool(args.include_artifacts),
        overwrite_curated=bool(args.overwrite_curated),
        all_dirs=bool(args.all_dirs),
        generated_readme_dirs=generated_dirs,
        classification_file=cls_file,
        strict_status=bool(args.strict_status),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    opts = parse_args(argv)
    root = opts.root

    external_classification = load_external_classification(opts.classification_file)

    interesting_files = [
        p for p in sorted(root.rglob("*"))
        if is_interesting_file(p, root, opts)
    ]

    # Build docs once before possible stubs so stubs can use status/purpose.
    pre_docs_by_path: Dict[Path, FileDoc] = {}
    for p in interesting_files:
        fd = build_filedoc(p, root, external_classification)
        if fd:
            pre_docs_by_path[p] = fd

    if opts.inject_stubs:
        changed = 0
        for p, fd in pre_docs_by_path.items():
            if is_important(fd):
                if inject_stub_doc_block(p, fd):
                    changed += 1
        print(f"[inject-stubs] inserted DOC stubs into {changed} file(s)")

    all_docs: List[FileDoc] = []
    for p in interesting_files:
        fd = build_filedoc(p, root, external_classification)
        if fd:
            all_docs.append(fd)

    all_docs.sort(key=lambda fd: (status_sort_key(fd.status), fd.relpath.lower()))

    if opts.check:
        rc = run_checks(all_docs, opts)
        if rc != 0:
            return rc

    by_dir: Dict[Path, List[FileDoc]] = {}
    for fd in all_docs:
        by_dir.setdefault(fd.path.parent, []).append(fd)

    for d in sorted(by_dir.keys(), key=lambda p: relpath(p, root).lower()):
        write_dir_readme(d, root, by_dir[d], opts)

    write_docs_index(root, all_docs, opts)

    if not opts.no_graph:
        write_mermaid_graph(root, all_docs, opts)

    print(f"[done] scanned {len(all_docs)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())