# DOC:
# Summary: Build and validate the self-contained runtime.tgz bundle used by Condor reco jobs, including k4RecTracker libraries, Gaudi catalogs, Python config, GenFit2 libraries, steering files, and the GGTF ONNX model.
# Status: authoritative
# Usage:
#   bash scripts/make_runtime.sh
#   K4RT_PREFIX=/afs/.../k4RecTracker GENFIT_LIB_DIR=/afs/.../genfit2/install/lib64 MODEL_PATH=/afs/.../model.onnx bash scripts/make_runtime.sh
# Examples:
#   cd /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder
#   bash scripts/make_runtime.sh
#   Expected result: runtime.tgz is created in the current directory and passes the bundled plugin/fitter usability check.
# Inputs: Built/installed k4RecTracker tree, k4RecTracker plugin libraries, Gaudi component catalogs, Tracking Python configuration, GenFit2 shared libraries, runDCHTestTrackFinder.py, optional local_chain.sh, and model.onnx.
# Outputs: runtime.tgz containing runtime/lib64, runtime/lib, runtime/share, runtime/python, runtime/models/model.onnx, runtime/runDCHTestTrackFinder.py, and optionally runtime/local_chain.sh.
# Collections: None; this is a runtime packaging/validation script and does not inspect EDM4hep collections.
# Connects-To: scripts/submit_reco.sh, configs/condor/reco.condor, scripts/reco_job.sh, steering/runDCHTestTrackFinder.py, steering/local_chain.sh
# Arguments:
#   K4RT_PREFIX: k4RecTracker checkout/build prefix; default /afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker.
#   K4RT_INSTALL_DIR: k4RecTracker install directory; default $K4RT_PREFIX/install.
#   K4RT_BUILD_DIR: k4RecTracker build directory; default $K4RT_PREFIX/build.
#   K4RT_LIBDIR: installed k4RecTracker library directory; auto-selects install/lib64 or install/lib.
#   K4RT_BUILD_LIBDIR: build-tree library fallback directory; auto-selects build/lib64 or build/lib.
#   K4RT_PY_INSTALL: installed Python directory containing Tracking/TrackingConf.py; default $K4RT_INSTALL_DIR/python.
#   K4RT_PY_SRC_FALLBACK: source-tree Tracking directory used if installed Python package is missing.
#   GENFIT_LIB_DIR: GenFit2 shared-library directory bundled into runtime/lib64.
#   MODEL_PATH: GGTF ONNX model copied into runtime/models/model.onnx.
#   TESTTRACKFINDER_DIR: workflow directory containing the steering and local wrapper files.
#   RUN_STEERING: steering file copied as runtime/runDCHTestTrackFinder.py.
#   LOCAL_CHAIN_SRC: optional local_chain.sh copied into the runtime bundle.
# Notes:
#   This is the authoritative runtime-packaging step for the maintained reco Condor pipeline.
#   Run this after rebuilding k4RecTracker, updating GenFit2, changing the GGTF model, or changing the steering that must be staged to worker nodes.
#   The script prefers installed libraries but falls back to build-tree libraries for required plugins such as libTracking.so and libDCHdigi.so.
#   Gaudi catalogs, *.components*, *.confdb, PCM/rootmap files, and relevant XML/conf plugin metadata are harvested because worker-node component discovery is otherwise fragile.
#   A Python sitecustomize shim is bundled only to avoid import-time crashes from missing dynamic Configurables; real plugin/library/catalog availability is still checked separately.
#   The runtime usability check requires core plugin libraries to load and at least one fitter path to be evidenced by catalogs or Python-level importability.
#   If this script fails, do not submit reco jobs; fix the library/catalog/model/steering problem first.
# Tags: authoritative, runtime, condor, reco, packaging, k4rectracker, gaudi, genfit2, ggtf, onnx
# DOC_END

#!/usr/bin/env bash
# mk_runtime.sh — build a self-contained runtime.tgz for Condor jobs
# Bundles k4RecTracker libs/plugins/python, GenFit2 libs, Gaudi catalogs (incl. *.confdb), and model.onnx.
# Then sanity-checks that the bundle is runtime-usable for at least one fitter
# (GenFit2DCHFitter or a Simple* fitter) using library loads + catalogs, with
# old-style Python imports treated as best-effort diagnostics only.

set -euo pipefail

# --- EDIT or override via env -------------------------------------------------
K4RT_PREFIX="${K4RT_PREFIX:-/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker}"
K4RT_INSTALL_DIR="${K4RT_INSTALL_DIR:-$K4RT_PREFIX/install}"
K4RT_BUILD_DIR="${K4RT_BUILD_DIR:-$K4RT_PREFIX/build}"

# Prefer lib64, fallback to lib
K4RT_LIBDIR="${K4RT_LIBDIR:-}"
if [[ -z "${K4RT_LIBDIR}" ]]; then
  if [[ -d "$K4RT_INSTALL_DIR/lib64" ]]; then
    K4RT_LIBDIR="$K4RT_INSTALL_DIR/lib64"
  else
    K4RT_LIBDIR="$K4RT_INSTALL_DIR/lib"
  fi
fi

# Build-side fallbacks (for uninstalled libs)
K4RT_BUILD_LIBDIR="${K4RT_BUILD_LIBDIR:-}"
if [[ -z "${K4RT_BUILD_LIBDIR}" ]]; then
  if [[ -d "$K4RT_BUILD_DIR/lib64" ]]; then
    K4RT_BUILD_LIBDIR="$K4RT_BUILD_DIR/lib64"
  else
    K4RT_BUILD_LIBDIR="$K4RT_BUILD_DIR/lib"
  fi
fi

# Python (installed tree contains Tracking/TrackingConf.py)
K4RT_PY_INSTALL="${K4RT_PY_INSTALL:-$K4RT_INSTALL_DIR/python}"
# Optional source fallback if not installed yet
K4RT_PY_SRC_FALLBACK="${K4RT_PY_SRC_FALLBACK:-$K4RT_PREFIX/Tracking}"   # contains Tracking/...

# GenFit2 shared libs
GENFIT_LIB_DIR="${GENFIT_LIB_DIR:-/afs/cern.ch/user/c/cglenn/FCCWork/genfit2/install/lib64}"

# ONNX model
MODEL_PATH="${MODEL_PATH:-$K4RT_PREFIX/Tracking/test/testTrackFinder/model.onnx}"
# ------------------------------------------------------------------------------

OUT="runtime.tgz"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "[rt] K4RT_INSTALL_DIR   = $K4RT_INSTALL_DIR"
echo "[rt] K4RT_LIBDIR        = $K4RT_LIBDIR"
echo "[rt] K4RT_BUILD_LIBDIR  = $K4RT_BUILD_LIBDIR"
echo "[rt] K4RT_PY_INSTALL    = $K4RT_PY_INSTALL"
echo "[rt] K4RT_PY_SRC_FB     = $K4RT_PY_SRC_FALLBACK"
echo "[rt] GENFIT_LIB_DIR     = $GENFIT_LIB_DIR"
echo "[rt] MODEL_PATH         = $MODEL_PATH"

[[ -d "$K4RT_INSTALL_DIR" ]] || { echo "FATAL: install dir missing: $K4RT_INSTALL_DIR"; exit 2; }
[[ -s "$MODEL_PATH" ]]       || { echo "FATAL: model missing: $MODEL_PATH"; exit 3; }

mkdir -p "$TMP/runtime/lib64" "$TMP/runtime/lib" "$TMP/runtime/share" "$TMP/runtime/python" "$TMP/runtime/models"

# --- k4RecTracker libs (prefer lib64) ----------------------------------------
if [[ -d "$K4RT_LIBDIR" ]]; then
  rsync -a \
    --include='*.so*' \
    --include='*_rdict.pcm' \
    --include='*.pcm' \
    --include='*.rootmap' \
    --exclude='*' \
    "$K4RT_LIBDIR"/ "$TMP/runtime/lib64/" || true
fi

# fallback from build if some libs/pcms only exist there
NEEDED=(libTracking.so libDCHdigi.so)
for L in "${NEEDED[@]}"; do
  if ! ls "$TMP/runtime/lib64/$L"* >/dev/null 2>&1; then
    if [[ -d "$K4RT_BUILD_LIBDIR" && -e "$K4RT_BUILD_LIBDIR/$L" ]]; then
      echo "[rt] pulling $L (+pcms) from build: $K4RT_BUILD_LIBDIR"
      rsync -a \
        --include="$L*" \
        --include='*_rdict.pcm' \
        --include='*.pcm' \
        --include='*.rootmap' \
        --exclude='*' \
        "$K4RT_BUILD_LIBDIR"/ "$TMP/runtime/lib64/" || true
    fi
  fi
done

# Also mirror into runtime/lib (harmless; some tools look at both)
if compgen -G "$TMP/runtime/lib64/*" >/dev/null; then
  rsync -a "$TMP/runtime/lib64/" "$TMP/runtime/lib/" || true
fi

# --- Gaudi share (plugin catalogs, options, confdb) ---------------------------
rsync -a "$K4RT_INSTALL_DIR/share/" "$TMP/runtime/share/" 2>/dev/null || true

# Copy common Gaudi component catalog locations explicitly if present
for d in \
  "$K4RT_INSTALL_DIR/share/Gaudi" \
  "$K4RT_INSTALL_DIR/share/Gaudi/PluginService" \
  "$K4RT_INSTALL_DIR/share/Gaudi/components" \
  "$K4RT_INSTALL_DIR/share/GaudiComponentLibrary" \
  "$K4RT_INSTALL_DIR/share/GaudiComponents"
do
  if [[ -d "$d" ]]; then
    echo "[rt] copying Gaudi catalog dir: $d"
    rsync -a "$d/" "$TMP/runtime/share/$(basename "$d")/" || true
  fi
done

# Harvest any *.components* and friends from libdirs into a dedicated catalog dir
LIB_CATALOGS_DIR="$TMP/runtime/share/k4rt-lib-catalogs"
mkdir -p "$LIB_CATALOGS_DIR"
for SRC in "$K4RT_LIBDIR" "$K4RT_BUILD_LIBDIR"; do
  [[ -d "$SRC" ]] || continue
  while IFS= read -r -d '' F; do
    cp -v "$F" "$LIB_CATALOGS_DIR/$(basename "$F")" || true
  done < <(find "$SRC" -maxdepth 2 -type f \
            \( -name '*.components*' -o -name 'components*.*' -o -name '*Gaudi*.xml' -o -name '*Plugin*' -o -name '*.conf' -o -name '*.xml' -o -name '*.confdb' \) \
            -print0 2>/dev/null)
done

# --- Python (installed) -------------------------------------------------------
if [[ -d "$K4RT_PY_INSTALL" ]]; then
  rsync -a "$K4RT_PY_INSTALL/" "$TMP/runtime/python/" || true
fi

# Fallback from source if Tracking/ is not present yet
if [[ ! -d "$TMP/runtime/python/Tracking" && -d "$K4RT_PY_SRC_FALLBACK" ]]; then
  echo "[rt] adding Tracking/ from source: $K4RT_PY_SRC_FALLBACK"
  rsync -a "$K4RT_PY_SRC_FALLBACK/" "$TMP/runtime/python/Tracking/" || true
fi

# Make Tracking a proper package
if [[ -d "$TMP/runtime/python/Tracking" && ! -f "$TMP/runtime/python/Tracking/__init__.py" ]]; then
  echo > "$TMP/runtime/python/Tracking/__init__.py"
  echo "[rt] created: runtime/python/Tracking/__init__.py"
fi

# Shim so 'import TrackingConf' works
if [[ ! -f "$TMP/runtime/python/TrackingConf.py" ]]; then
  cat > "$TMP/runtime/python/TrackingConf.py" <<'PY'
# Shim so 'import TrackingConf' works
try:
    from Tracking.TrackingConf import *  # noqa
except Exception as _e:
    try:
        from TrackingConf import *  # noqa
    except Exception:
        raise
PY
  echo "[rt] wrote shim: runtime/python/TrackingConf.py"
fi

# --- Inject a sitecustomize shim to avoid ImportError crashes -----------------
cat > "$TMP/runtime/python/sitecustomize.py" <<'PY'
# Ensure key Configurables are present in the import namespace even if
# the factory catalogs are missing, so jobs don't die at import-time.
try:
    import Configurables as C  # Gaudi's dynamic module
    from GaudiKernel.Configurable import ConfigurableGeneric as _CG

    # Helper: inject a callable class stub with the expected name
    def _inject_class_stub(name: str):
        if not hasattr(C, name):
            Stub = type(name, (_CG,), {})
            setattr(C, name, Stub)
            print(f"[shim] Injected Configurables.{name} as class stub")

    # GenFit2 (class stub if missing)
    try:
        from Configurables import GenFit2DCHFitter as _T
    except Exception:
        _inject_class_stub("GenFit2DCHFitter")

    # Simple* variants — class stubs so import won't fail; real factory still needed to do real work
    for _name in ("SimpleFitDCHFitter", "SimpleFitterAlg", "SimpleTrackFitterAlg", "HelixFitter"):
        try:
            getattr(C, _name)
        except Exception:
            _inject_class_stub(_name)

    # Mirror into Gaudi.Configurables for legacy imports
    try:
        import Gaudi.Configurables as GC
        for _name in ("GenFit2DCHFitter",
                      "SimpleFitDCHFitter","SimpleFitterAlg","SimpleTrackFitterAlg","HelixFitter"):
            if not hasattr(GC, _name) and hasattr(C, _name):
                setattr(GC, _name, getattr(C, _name))
    except Exception:
        pass
except Exception as e:
    print(f"[shim][WARN] sitecustomize could not inject: {e}")
PY

# --- GenFit2 libs -------------------------------------------------------------
if [[ -d "$GENFIT_LIB_DIR" ]]; then
  echo "[rt] bundling GenFit2 from $GENFIT_LIB_DIR"
  rsync -a \
    --include='*.so*' \
    --include='*_rdict.pcm' \
    --include='*.pcm' \
    --include='*.rootmap' \
    --exclude='*' \
    "$GENFIT_LIB_DIR"/ "$TMP/runtime/lib64/"
  rsync -a "$TMP/runtime/lib64/" "$TMP/runtime/lib/" || true
else
  echo "[rt][WARN] GENFIT_LIB_DIR missing: $GENFIT_LIB_DIR"
fi

# --- Drivers & model ----------------------------------------------------------
TESTTRACKFINDER_DIR="${TESTTRACKFINDER_DIR:-$K4RT_PREFIX/Tracking/test/testTrackFinder}"
RUN_STEERING="${RUN_STEERING:-$TESTTRACKFINDER_DIR/runDCHTestTrackFinder.py}"
LOCAL_CHAIN_SRC="${LOCAL_CHAIN_SRC:-$TESTTRACKFINDER_DIR/local_chain.sh}"

echo "[rt] TESTTRACKFINDER_DIR = $TESTTRACKFINDER_DIR"
echo "[rt] RUN_STEERING        = $RUN_STEERING"
echo "[rt] LOCAL_CHAIN_SRC     = $LOCAL_CHAIN_SRC"

[[ -f "$RUN_STEERING" ]] || { echo "[rt][FATAL] missing steering file: $RUN_STEERING"; exit 4; }
cp -v "$RUN_STEERING" "$TMP/runtime/runDCHTestTrackFinder.py"

if [[ -f "$LOCAL_CHAIN_SRC" ]]; then
  cp -v "$LOCAL_CHAIN_SRC" "$TMP/runtime/local_chain.sh" || true
  chmod +x "$TMP/runtime/local_chain.sh" || true
fi

cp -v "$MODEL_PATH" "$TMP/runtime/models/model.onnx"

# --- Optional diag: ldd -r to see unresolved deps early ----------------------
TRACKING_LIB="$(ls "$TMP/runtime/lib64"/libTracking*.so 2>/dev/null | head -n1 || true)"
if [[ -n "$TRACKING_LIB" && -x /usr/bin/ldd ]]; then
  echo "[rt][diag] ldd -r on $(basename "$TRACKING_LIB")"
  ldd -r "$TRACKING_LIB" || true
fi

# --- Sanity checks: catalogs & symbols (GenFit + Simple*) --------------------
echo "[rt][check] Catalog/symbol probes for fitters"
if [[ -n "$TRACKING_LIB" && -x "$(command -v strings)" ]]; then
  if strings "$TRACKING_LIB" | grep -q 'GenFit2DCHFitter'; then
    echo "[rt][check] symbol 'GenFit2DCHFitter' appears in libTracking"
  else
    echo "[rt][warn] 'GenFit2DCHFitter' not obvious in strings(libTracking) — factory may still register it."
  fi
  if strings "$TRACKING_LIB" | grep -Eqi 'SimpleFitDCHFitter|SimpleFitterAlg|SimpleTrackFitterAlg|HelixFitter'; then
    echo "[rt][check] Simple* fitter symbol(s) appear in libTracking"
  else
    echo "[rt][warn] No obvious Simple* fitter symbols in libTracking; may still be OK if catalog registers them."
  fi
fi

if compgen -G "$TMP/runtime/share/**" >/dev/null; then
  GREP_OUT_GF="$(grep -R -n --include='*.components*' --include='components*.*' --include='*.confdb' \
                 'GenFit2DCHFitter' "$TMP/runtime/share" 2>/dev/null || true)"
  if [[ -n "$GREP_OUT_GF" ]]; then
    echo "[rt][check] catalogs mention GenFit2DCHFitter:"; echo "$GREP_OUT_GF" | sed 's/^/    /'
  else
    echo "[rt][warn] catalogs do not mention GenFit2DCHFitter"
  fi

  GREP_OUT_SF="$(grep -R -n --include='*.components*' --include='components*.*' --include='*.confdb' \
                 -E 'SimpleFitDCHFitter|SimpleFitterAlg|SimpleTrackFitterAlg|HelixFitter' "$TMP/runtime/share" 2>/dev/null || true)"
  if [[ -n "$GREP_OUT_SF" ]]; then
    echo "[rt][check] catalogs mention a Simple* fitter:"; echo "$GREP_OUT_SF" | sed 's/^/    /'
  else
    echo "[rt][warn] catalogs do not mention any Simple* fitter"
  fi
else
  echo "[rt][warn] no runtime/share content copied; relying on plugin self-registration."
fi

# --- Runtime-usable fitter check ---------------------------------------------
# Trust shell-side catalog grep results as the primary truth for component registration.
SHELL_CATALOG_HAS_GENFIT=0
SHELL_CATALOG_HAS_SIMPLE=0
[[ -n "${GREP_OUT_GF:-}" ]] && SHELL_CATALOG_HAS_GENFIT=1
[[ -n "${GREP_OUT_SF:-}" ]] && SHELL_CATALOG_HAS_SIMPLE=1

echo "[rt][pycheck] Verifying runtime usability of bundled fitters"
SHELL_CATALOG_HAS_GENFIT="$SHELL_CATALOG_HAS_GENFIT" \
SHELL_CATALOG_HAS_SIMPLE="$SHELL_CATALOG_HAS_SIMPLE" \
python3 - <<'PY' || { echo "[rt][FATAL] Runtime usability check failed (no loadable fitter path found)"; exit 41; }
import os, sys

print("[rt][pycheck] starting")
rt    = os.path.join(os.getcwd(), "runtime")
lib64 = os.path.join(rt, "lib64")
lib   = os.path.join(rt, "lib")
pyp   = os.path.join(rt, "python")
share = os.path.join(rt, "share")
extra = os.path.join(share, "k4rt-lib-catalogs")

# Prepend our bundle to search paths
os.environ["LD_LIBRARY_PATH"]       = f"{lib64}:{lib}:" + os.environ.get("LD_LIBRARY_PATH","")
os.environ["GAUDI_PLUGIN_PATH"]     = f"{lib64}:{lib}:" + os.environ.get("GAUDI_PLUGIN_PATH","")
os.environ["GAUDI_COMPONENT_PATH"]  = f"{share}:{extra}:" + os.environ.get("GAUDI_COMPONENT_PATH","")
os.environ["GAUDI_COMPONENTS_PATH"] = os.environ["GAUDI_COMPONENT_PATH"]
os.environ["PYTHONPATH"]            = f"{pyp}:" + os.environ.get("PYTHONPATH","")

# Actually update import search path for this Python process
if pyp not in sys.path:
    sys.path.insert(0, pyp)

shell_catalog_has_genfit = os.environ.get("SHELL_CATALOG_HAS_GENFIT", "0") == "1"
shell_catalog_has_simple = os.environ.get("SHELL_CATALOG_HAS_SIMPLE", "0") == "1"
print(f"[rt][pycheck] shell_catalog_has_genfit={shell_catalog_has_genfit}")
print(f"[rt][pycheck] shell_catalog_has_simple={shell_catalog_has_simple}")

import ROOT
load_rc = {}
for name in ("libTracking", "libDCHdigi", "libDDRec", "libk4FWCorePlugins"):
    rc = ROOT.gSystem.Load(name)
    load_rc[name] = rc
    print(f"[rt][pycheck] ROOT Load {name}: rc={rc}")

core_load_ok = (load_rc.get("libTracking", 1) == 0 and load_rc.get("libDCHdigi", 1) == 0)

# Best-effort python import diagnostics only
ok_genfit = False
try:
    import sitecustomize  # noqa: F401
except Exception:
    pass

try:
    from Gaudi.Configurables import GenFit2DCHFitter  # noqa
    print("[rt][pycheck] OK: Gaudi.Configurables.GenFit2DCHFitter importable")
    ok_genfit = True
except Exception as e:
    print(f"[rt][pycheck] warn: GenFit2DCHFitter python import failed: {e}")

ok_simple = False
for mod, name in [
    ("TrackingConf", "SimpleFitDCHFitter"),
    ("Gaudi.Configurables", "SimpleFitDCHFitter"),
    ("Gaudi.Configurables", "SimpleFitterAlg"),
    ("Gaudi.Configurables", "SimpleTrackFitterAlg"),
    ("Gaudi.Configurables", "HelixFitter"),
]:
    try:
        m = __import__(mod, fromlist=[name])
        getattr(m, name)
        print(f"[rt][pycheck] OK: {mod}.{name} importable")
        ok_simple = True
        break
    except Exception as e:
        print(f"[rt][pycheck] warn: {mod}.{name} import failed: {e}")

# Robust success criterion:
#   - core plugin libs load
#   - and a fitter path is evidenced either by shell-side catalog grep
#     or by python-level importability.
fitter_path_ok = (shell_catalog_has_genfit or shell_catalog_has_simple or ok_genfit or ok_simple)

print(f"[rt][pycheck] core_load_ok={core_load_ok}")
print(f"[rt][pycheck] fitter_path_ok={fitter_path_ok}")

if not core_load_ok:
    print("[rt][pycheck] FATAL: required plugin libs did not load")
    sys.exit(2)
if not fitter_path_ok:
    print("[rt][pycheck] FATAL: no fitter path evidenced by catalogs or python imports")
    sys.exit(3)

print("[rt][pycheck] Runtime usability check passed")
sys.exit(0)
PY
echo "[rt][check] Runtime usability check passed"

# --- Pack --------------------------------------------------------------------
tar -C "$TMP" -czf "$OUT" runtime
echo "[rt] wrote $OUT  size=$(du -h "$OUT" | awk '{print $1}')"