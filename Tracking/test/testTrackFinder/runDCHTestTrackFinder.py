#!/usr/bin/env python3
#DOC
# runDCHTestTrackFinder.py
#
# Robust configuration for:
#   SimTrackerHits -> DCHdigi -> GGTF_tracking (Option A: hits attached to tracks) -> GenFit2DCHFitter
#
# Updated (2026-01-18):
#   - Updated CLI + property wiring to match the *new* GenFit2DCHFitter.cpp (no SimLinks seeding; no best-state weights).
#   - Added knobs present in C++:
#       * PublishStateCentralFrac, SeedTangentK
#       * PreFitOutlierVeto + Outlier* knobs
#       * StatsTruncCentralFrac, MinCovEigenvalue, DiagEveryNTracks
#   - Removed obsolete knobs:
#       * SimLinkSeedMode / SeedMinNHits / SeedMinWeight
#       * BestStateZWeight / BestStateIdxWeight
#
# IMPORTANT robustness rule:
#   Do NOT pass version-dependent properties as constructor kwargs.
#   Instantiate configurables with minimal args, then set properties via _set_any.'
#DOC_END

import os
import subprocess
import shutil
import traceback

# --- HARD STOP ON PRELOADING -------------------------------------------------
os.environ.pop("GAUDI_PLUGINS", None)

from Gaudi.Configuration import INFO, DEBUG
from Gaudi.Configuration import ApplicationMgr as GaudiApp
from Configurables import EventDataSvc, UniqueIDGenSvc, RndmGenSvc, GeoSvc
from Configurables import AuditorSvc, ChronoAuditor, MemoryAuditor, MessageSvc

from k4FWCore import IOSvc
from k4FWCore.parseArgs import parser

# ----------------- IO & geometry -----------------
parser.add_argument("--inputFile", default="ddsim_output_edm4hep.root",
                    help="Input EDM4hep file (from ddsim or digi)")
parser.add_argument("--outputFile", default="output_digi_ggtf_fit.root",
                    help="Output EDM4hep file")
parser.add_argument("--compactXML", default="",
                    help="Path/URL to compact XML (same one used by ddsim). Required for GenFit material effects.")

# NEW: optional TGeo ROOT file to explicitly populate gGeoManager (fallback for GenFit material effects)
parser.add_argument("--tgeoFile", default="/afs/cern.ch/user/c/cglenn/FCCWork/k4RecTracker/Tracking/test/testTrackFinder/IDEA_o1_v03CF.root",
                    help="Optional TGeo ROOT geometry file to Import() if gGeoManager is null "
                         "(e.g. IDEA_o1_v03W.root). Passed to GenFit2DCHFitter property TGeoFile.")

parser.add_argument("--dchSimHits", default="DCHCollection",
                    help="Name of DCH SimTrackerHit collection in the input file")
parser.add_argument("--dchName", default="DCH_v2",
                    help="DD4hep detector name for the DCH (e.g. DCH_v2)")

parser.add_argument("--modelPath", default="",
                    help="ONNX model path for GGTF_tracking; accepts .onnx, .onnx.md5, http(s)://, root://")

parser.add_argument("--stage", choices=["digi", "ggtf", "fit"], default="fit",
                    help="Which pipeline stage(s) to run (cumulative: digi -> digi+ggtf -> digi+ggtf+fit).")
parser.add_argument("--skipDigi", action="store_true", default=False,
                    help="If set: do NOT run the digitizer (useful if inputFile is already digitized).")

parser.add_argument("--jobTag", default="",
                    help="Optional free-form tag stored in metadata. If empty, auto-generated.")

# ----------------- Digitizer -----------------
parser.add_argument("--dchDigiVersion", choices=["v01", "v02"], default="v02",
                    help="Choose DCH digitizer implementation")
parser.add_argument("--xyResolution_mm", type=float, default=0.10, help="xy-resolution (mm)")
parser.add_argument("--zResolution_mm", type=float, default=30.0, help="z-resolution (mm)")

# v02 knobs
parser.add_argument("--dch-deadtime-ns", dest="dch_deadtime_ns", type=float, default=450.0,
                    help="[v02] cell deadtime (ns)")
parser.add_argument("--dch-drift-vel-um-ns", dest="dch_drift_um_ns", type=float, default=-1.0,
                    help="[v02] drift velocity (um/ns). If <0, auto by GasType")
parser.add_argument("--dch-signal-vel-mm-ns", dest="dch_sig_mm_ns", type=float,
                    default=2.0/3.0*299792458.0*1e-6,
                    help="[v02] signal velocity along wire (mm/ns). Default 2/3 c")
parser.add_argument("--dch-gas-type", dest="dch_gas_type", type=int, default=0,
                    help="[v02] gas: 0 He(90)-iC4H10(10), 1 He, 2 Ar(50)-C2H6(50), 3 Ar")
parser.add_argument("--rw-start-ns", dest="rw_start_ns", type=float, default=1.0,
                    help="[v02] readout window start (ns)")
parser.add_argument("--rw-duration-ns", dest="rw_dur_ns", type=float, default=900.0,
                    help="[v02] readout window duration (ns)")

# ----------------- GGTF -----------------
parser.add_argument("--tbeta", type=float, default=0.6, help="GGTF beta threshold")
parser.add_argument("--td", type=float, default=0.3, help="GGTF distance threshold")
parser.add_argument("--onnxChunk", type=int, default=4096, help="ONNX hits per slice")
parser.add_argument("--maxHitsPerEvent", type=int, default=0, help="Cap input hits (0=off)")

parser.add_argument("--ggtf-dropWireIfAbsDTooLarge", dest="ggtf_dropWireIfAbsDTooLarge",
                    action="store_true", default=True)
parser.add_argument("--no-ggtf-dropWireIfAbsDTooLarge", dest="ggtf_dropWireIfAbsDTooLarge",
                    action="store_false")
parser.add_argument("--ggtf-maxAbsDMM", type=float, default=30.0)

parser.add_argument("--ggtf-zeroMinSizeKeep", type=int, default=8)
parser.add_argument("--ggtf-minWireFracKeep", type=float, default=0.60)
parser.add_argument("--ggtf-promoteZeroIfGood", action="store_true", default=True)
parser.add_argument("--no-ggtf-promoteZeroIfGood", dest="ggtf_promoteZeroIfGood", action="store_false")
parser.add_argument("--ggtf-skipZeroIfSmall", action="store_true", default=True)
parser.add_argument("--no-ggtf-skipZeroIfSmall", dest="ggtf_skipZeroIfSmall", action="store_false")
parser.add_argument("--ggtf-skipZeroAlways", action="store_true", default=False)
parser.add_argument("--no-ggtf-skipZeroAlways", dest="ggtf_skipZeroAlways", action="store_false")

# Truth gating (exists in your GGTF_tracking.cpp)
parser.add_argument("--ggtf-filterInputWiresByTruthPdg", dest="ggtf_filterInputWiresByTruthPdg",
                    action="store_true", default=False)
parser.add_argument("--no-ggtf-filterInputWiresByTruthPdg", dest="ggtf_filterInputWiresByTruthPdg",
                    action="store_false")
parser.add_argument("--ggtf-keepTruthPdg", type=int, default=13)
parser.add_argument("--ggtf-dropWireIfUnlinked", dest="ggtf_dropWireIfUnlinked",
                    action="store_true", default=True)
parser.add_argument("--no-ggtf-dropWireIfUnlinked", dest="ggtf_dropWireIfUnlinked",
                    action="store_false")
parser.add_argument("--ggtf-wireSimLinkColl", default="",
                    help="Override wire->SimTrackerHit link collection name for GGTF truth gating. "
                         "If empty, guesses based on digi version.")

parser.add_argument("--ggtfTracksOut", default="CDCHTracks",
                    help="Name of GGTF output track collection.")
parser.add_argument("--ggtfLog", choices=["INFO", "DEBUG"], default="INFO")

# ----------------- Fitter -----------------
parser.add_argument("--fitter", choices=["none", "genfit2"], default="genfit2")
parser.add_argument("--fitOut", default="GenFitTracks")
parser.add_argument("--fitterLog", choices=["INFO", "DEBUG"], default="INFO")

# GenFit2 core
parser.add_argument("--gf-useMat", dest="gf_useMat", action="store_true", default=False)
parser.add_argument("--no-gf-useMat", dest="gf_useMat", action="store_false")
parser.add_argument("--gf-bz", type=float, default=2.0)
parser.add_argument("--gf-pdg", type=int, default=13)

# material policy knobs present in C++
parser.add_argument("--gf-disableEloss", dest="gf_disableEloss", action="store_true", default=True,
                    help="Disable energy loss (keep MS) when material effects enabled.")
parser.add_argument("--no-gf-disableEloss", dest="gf_disableEloss", action="store_false")
parser.add_argument("--gf-disableAllMat", dest="gf_disableAllMat", action="store_true", default=False,
                    help="Disable all GenFit material effects.")
parser.add_argument("--no-gf-disableAllMat", dest="gf_disableAllMat", action="store_false")
parser.add_argument("--gf-hardDisableMatIfNoGeo", dest="gf_hardDisableMatIfNoGeo", action="store_true", default=True,
                    help="If gGeoManager is null: force MaterialEffects::setNoEffects(true).")
parser.add_argument("--no-gf-hardDisableMatIfNoGeo", dest="gf_hardDisableMatIfNoGeo", action="store_false")

# sorting/hygiene
parser.add_argument("--gf-sortHits", dest="gf_sortHits", action="store_true", default=True)
parser.add_argument("--no-gf-sortHits", dest="gf_sortHits", action="store_false")
parser.add_argument("--gf-dedup", dest="gf_dedup", action="store_true", default=True)
parser.add_argument("--no-gf-dedup", dest="gf_dedup", action="store_false")
parser.add_argument("--gf-dedupTolMM", type=float, default=0.10)

# acceptance / minimums
parser.add_argument("--gf-rejectNegativeLabels", dest="gf_rejectNegativeLabels",
                    action="store_true", default=True)
parser.add_argument("--no-gf-rejectNegativeLabels", dest="gf_rejectNegativeLabels",
                    action="store_false")

parser.add_argument("--gf-minHitsPerTrack", type=int, default=8)
parser.add_argument("--gf-minMeasurementsToFit", type=int, default=6)
parser.add_argument("--gf-minFittedPointsWithFI", type=int, default=10)
parser.add_argument("--gf-maxChi2Ndf", type=float, default=20.0)

# fit strategy
parser.add_argument("--gf-useKFPreFit", dest="gf_useKFPreFit", action="store_true", default=True)
parser.add_argument("--no-gf-useKFPreFit", dest="gf_useKFPreFit", action="store_false")
parser.add_argument("--gf-kfMaxIters", type=int, default=12)

parser.add_argument("--gf-useDAF", dest="gf_useDAF", action="store_true", default=True)
parser.add_argument("--no-gf-useDAF", dest="gf_useDAF", action="store_false")
parser.add_argument("--gf-dafMaxIters", type=int, default=8)

parser.add_argument("--gf-fallbackToKFIfDAFFails", dest="gf_fallbackToKFIfDAFFails",
                    action="store_true", default=True)
parser.add_argument("--no-gf-fallbackToKFIfDAFFails", dest="gf_fallbackToKFIfDAFFails",
                    action="store_false")

parser.add_argument("--gf-tryBothMomDirs", dest="gf_tryBothMomDirs", action="store_true", default=True)
parser.add_argument("--no-gf-tryBothMomDirs", dest="gf_tryBothMomDirs", action="store_false")

# publishing
parser.add_argument("--gf-useBiasedStateForPublish", dest="gf_useBiasedStateForPublish",
                    action="store_true", default=True)
parser.add_argument("--no-gf-useBiasedStateForPublish", dest="gf_useBiasedStateForPublish",
                    action="store_false")
parser.add_argument("--gf-publishStateCentralFrac", type=float, default=0.60,
                    help="Fraction of track points (by index) considered around the middle for publish-state selection.")

parser.add_argument("--gf-publishPTMaxGeV", type=float, default=300.0)
parser.add_argument("--gf-invalidPTSentinel", type=float, default=-1.0)
parser.add_argument("--gf-omegaVarGood", type=float, default=1e-4)
parser.add_argument("--gf-omegaVarBad", type=float, default=1.0)

# units / wire / drift model
parser.add_argument("--gf-positionUnitScale", type=float, default=0.1,
                    help="Position unit scale for GenFit internal units (0.1 => mm->cm).")
parser.add_argument("--gf-wireHalfLengthMM", type=float, default=2250.0,
                    help="Half wire length (mm) for endpoint synthesis.")
parser.add_argument("--gf-maxDriftMM", type=float, default=30.0,
                    help="Max drift distance (mm) for WireMeasurementNew setMaxDistance.")
parser.add_argument("--gf-maxDriftMMForHit", type=float, default=35.0,
                    help="Hard hit-level cut on |drift| (mm).")
parser.add_argument("--gf-minDriftErrMM", type=float, default=0.10,
                    help="Floor for drift distance error (mm).")
parser.add_argument("--gf-maxDriftErrMM", type=float, default=5.0,
                    help="Ceiling for drift distance error (mm).")

# seed control
parser.add_argument("--gf-seedEndpointK", type=int, default=6,
                    help="Mean of first/last K hits used as seed endpoints.")
parser.add_argument("--gf-seedTangentK", type=int, default=10,
                    help="Window size for tangent estimation at each end (PCA over first/last K hits).")

parser.add_argument("--gf-seedPosSigmaMM", type=float, default=80.0)
parser.add_argument("--gf-seedMomSigmaGeV", type=float, default=5.0)
parser.add_argument("--gf-seedPTFallbackGeV", type=float, default=50.0)
parser.add_argument("--gf-seedPTMinGeV", type=float, default=0.20)
parser.add_argument("--gf-seedPTMaxGeV", type=float, default=200.0)
parser.add_argument("--gf-seedPMinGeV", type=float, default=0.05)

parser.add_argument("--gf-useSagittaSeed", dest="gf_useSagittaSeed", action="store_true", default=True)
parser.add_argument("--no-gf-useSagittaSeed", dest="gf_useSagittaSeed", action="store_false")
parser.add_argument("--gf-minSagittaForSeedMM", type=float, default=0.20)

# observability gating (matches C++ fields)
parser.add_argument("--gf-minHitsForObs", type=int, default=10)
parser.add_argument("--gf-obsSigmaEffMM", type=float, default=0.25)
parser.add_argument("--gf-obsMinPhiSpanRad", type=float, default=0.06)
parser.add_argument("--gf-obsMinChordMM", type=float, default=200.0)
parser.add_argument("--gf-obsMinSagittaMM", type=float, default=0.15)
parser.add_argument("--gf-obsMinScore", type=float, default=1.0)
parser.add_argument("--gf-skipIfObsTooLow", dest="gf_skipIfObsTooLow", action="store_true", default=False,
                    help="If set: drop tracks that fail observability cuts. Default False keeps track but marks pT invalid.")
parser.add_argument("--no-gf-skipIfObsTooLow", dest="gf_skipIfObsTooLow", action="store_false")

# pre-fit outlier veto (geometry-only)
parser.add_argument("--gf-prefitOutlierVeto", dest="gf_prefitOutlierVeto", action="store_true", default=True)
parser.add_argument("--no-gf-prefitOutlierVeto", dest="gf_prefitOutlierVeto", action="store_false")
parser.add_argument("--gf-outlierMaxDrop", type=int, default=2)
parser.add_argument("--gf-outlierCircleResidualMM", type=float, default=8.0)
parser.add_argument("--gf-outlierChordResidualMM", type=float, default=20.0)
parser.add_argument("--gf-outlierMinKeep", type=int, default=10)

# PD guards / stats / diagnostics
parser.add_argument("--gf-minCovEigenvalue", type=float, default=1e-8)
parser.add_argument("--gf-statsTruncCentralFrac", type=float, default=0.95)
parser.add_argument("--gf-diagEveryNTracks", type=int, default=1)

# detId policy / angles
parser.add_argument("--gf-detId", type=int, default=0)
parser.add_argument("--gf-useLabelAsDetId", dest="gf_useLabelAsDetId", action="store_true", default=False)
parser.add_argument("--no-gf-useLabelAsDetId", dest="gf_useLabelAsDetId", action="store_false")

parser.add_argument("--gf-wireAnglesAreDegrees", dest="gf_wireAnglesAreDegrees",
                    action="store_true", default=False,
                    help="Set if SenseWireHit wire angles are stored in degrees (normally radians).")
parser.add_argument("--gf-wireAnglesAreRadians", dest="gf_wireAnglesAreDegrees",
                    action="store_false")

# -----------------------------------------------------------------------------
args = parser.parse_args()

# --- construct job_tag --------------------------------------------------------
if args.jobTag:
    job_tag = args.jobTag
else:
    script_name = os.path.basename(globals().get("__file__", "runDCHTestTrackFinder.py"))
    job_tag = (
        f"{script_name}"
        f"|input={os.path.basename(args.inputFile)}"
        f"|stage={args.stage}"
        f"|skipDigi={int(args.skipDigi)}"
        f"|digi={args.dchDigiVersion}"
        f"|fitter={args.fitter}"
    )

print(f"[meta] JobTag='{job_tag}'")

# Require model if we will run GGTF (stage ggtf or fit)
will_run_ggtf = (args.stage in ("ggtf", "fit"))
if will_run_ggtf and not args.modelPath:
    raise RuntimeError("--modelPath is required when running GGTF (stage ggtf/fit).")

# Effective material flag
gf_useMat_effective = bool(args.gf_useMat)
if args.fitter == "genfit2" and args.stage == "fit" and gf_useMat_effective and not args.compactXML:
    raise RuntimeError(
        "GenFit2 UseMaterialEffects=True but --compactXML not provided. "
        "Provide the same compact used by ddsim so TGeo/material is available."
    )

# ----------------- Message/Auditing -----------------
MessageSvc().Format = "% F%18W%S%7W%R%T %0W%M"
try:
    GaudiApp().PluginDebugLevel = 1
except Exception:
    pass

GaudiApp().AuditAlgorithms = True
try:
    GaudiApp().AuditTools = True
except Exception:
    pass
AuditorSvc().Auditors = [ChronoAuditor(), MemoryAuditor()]

# ----------------- IO -----------------
svc = IOSvc("IOSvc")
svc.Input = args.inputFile
svc.Output = args.outputFile
print(f"[IO] input={args.inputFile}  output={args.outputFile}")

# ----------------- Geometry -----------------
geoservice = GeoSvc("GeoSvc")
geoservice.detectors = [args.compactXML] if args.compactXML else []
geoservice.OutputLevel = INFO
print(f"[Geo] compactXML={args.compactXML}  DD4hep_XMLPATH={os.environ.get('DD4hep_XMLPATH','')}")

# --------- Model staging helper ----------
def stage_model(spec: str) -> str:
    if not spec:
        raise RuntimeError("modelPath is empty")

    if spec.endswith(".onnx") and os.path.exists(spec):
        return os.path.abspath(spec)

    out = os.path.abspath("model.onnx")

    if spec.endswith(".onnx.md5"):
        with open(spec) as f:
            md5 = f.read().split()[0]
        url = f"https://key4hep.web.cern.ch/testFiles/k4RecTracker/{md5}"
        print(f"[model] from md5: {md5} -> {url}")
        subprocess.run(["wget", "--no-verbose", "--timeout=180", "--tries=2", "-O", out, url], check=True)
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            raise RuntimeError(f"Downloaded model is missing/empty: {out}")
        return out

    if spec.startswith(("http://", "https://")):
        print(f"[model] download {spec} -> {out}")
        subprocess.run(["wget", "--no-verbose", "--timeout=180", "--tries=2", "-O", out, spec], check=True)
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            raise RuntimeError(f"Downloaded model is missing/empty: {out}")
        return out

    if spec.startswith("root://"):
        print(f"[model] xrdcp {spec} -> {out}")
        subprocess.run(["xrdcp", "-f", spec, out], check=True)
        if not os.path.exists(out) or os.path.getsize(out) == 0:
            raise RuntimeError(f"xrdcp model is missing/empty: {out}")
        return out

    if spec.endswith(".onnx"):
        shutil.copy2(spec, out)
        return out

    raise RuntimeError(f"Unrecognized model spec: {spec}")

# --------- Safe property setting helpers ----------
def _list_props(obj):
    """Return a set of property names, or None if not introspectable."""
    try:
        d = obj.getProperties()
        if isinstance(d, dict):
            return set(d.keys())
    except Exception:
        pass
    try:
        d = obj.properties()
        if isinstance(d, dict):
            return set(d.keys())
    except Exception:
        pass
    return None

def _has_prop(obj, name: str) -> bool:
    props = _list_props(obj)
    if props is None:
        # If we cannot introspect, assume it *might* exist and try setattr.
        return True
    return name in props

def _set_if_has(obj, name, value, label=""):
    if not _has_prop(obj, name):
        return False
    try:
        setattr(obj, name, value)
        tag = label or name
        print(f"[set] {tag}: {obj.getName()}.{name} = {value}")
        return True
    except AttributeError:
        return False
    except Exception as e:
        print(f"[set][WARN] could not set {obj.getName()}.{name}: {e}")
        return False

def _set_any(obj, candidates, value, label=""):
    for p in candidates:
        if _set_if_has(obj, p, value, label=label or p):
            return p
    return None

def _dump_props(obj, title="props"):
    props = _list_props(obj)
    if props is None:
        print(f"[{title}] {obj.getName()} properties not introspectable")
        return
    props = sorted(list(props))
    print(f"[{title}] {obj.getName()} has {len(props)} properties:")
    for p in props:
        print(f"  - {p}")

# ----------------- Digitizer resolver -----------------
def _resolve_dch_digitizer(version: str):
    tried = []
    if version == "v02":
        preferred = [("DCHdigiConf", "DCHdigi_v02"), ("Configurables", "DCHdigi_v02"), ("TrackingConf", "DCHdigi_v02")]
        fallback  = [("DCHdigiConf", "DCHdigi_v01"), ("Configurables", "DCHdigi_v01"), ("TrackingConf", "DCHdigi_v01")]
    else:
        preferred = [("DCHdigiConf", "DCHdigi_v01"), ("Configurables", "DCHdigi_v01"), ("TrackingConf", "DCHdigi_v01")]
        fallback  = [("DCHdigiConf", "DCHdigi_v02"), ("Configurables", "DCHdigi_v02"), ("TrackingConf", "DCHdigi_v02")]

    for mod, cls in (preferred + fallback):
        try:
            m = __import__(mod, fromlist=[cls])
            C = getattr(m, cls)
            print(f"[digitizer] Using {mod}.{cls}")
            return C(cls)
        except Exception as e:
            tried.append(f"{mod}.{cls} -> {e}")

    paths = os.environ.get("GAUDI_PLUGIN_PATH", "(unset)")
    raise ImportError(
        "No DCH digitizer component found. Tried:\n  " +
        "\n  ".join(tried) +
        f"\nGAUDI_PLUGIN_PATH={paths}"
    )

# Build digitizer only if we will run it
dch_digitizer = None
if (args.stage in ("digi", "ggtf", "fit")) and (not args.skipDigi):
    dch_digitizer = _resolve_dch_digitizer(args.dchDigiVersion)

    # Configure digitizer
    _set_any(dch_digitizer,
             ["InputSimHitCollection", "DCH_simhits", "DCHSimHits", "InputSimHits"],
             [args.dchSimHits],
             label="InputSimHitCollection")

    _set_any(dch_digitizer, ["HeaderName"], ["EventHeader"], label="HeaderName")
    _set_any(dch_digitizer, ["DCH_name", "DCHName"], args.dchName, label="DCH_name")

    if args.dchDigiVersion == "v02":
        _set_any(dch_digitizer, ["OutputDigihitCollection"], ["DCHDigi2Collection"], label="OutputDigihitCollection")
        _set_any(dch_digitizer, ["OutputLinkCollection"],    ["DCHDigi2SimLinkCollection"], label="OutputLinkCollection")
    else:
        _set_any(dch_digitizer, ["OutputDigihitCollection"], ["DCH_DigiCollection"], label="OutputDigihitCollection")
        _set_any(dch_digitizer, ["OutputLinkCollection"],    ["DCHDigiSimLinkCollection"], label="OutputLinkCollection")

    _set_any(dch_digitizer, ["xyResolution_mm", "xyResolutionMM"], float(args.xyResolution_mm), label="xyResolution_mm")
    _set_any(dch_digitizer, ["zResolution_mm",  "zResolutionMM"],  float(args.zResolution_mm),  label="zResolution_mm")

    _set_any(dch_digitizer, ["Deadtime_ns"], float(args.dch_deadtime_ns), label="Deadtime_ns")
    _set_any(dch_digitizer, ["DriftVelocity_um_per_ns"], float(args.dch_drift_um_ns), label="DriftVelocity_um_per_ns")
    _set_any(dch_digitizer, ["SignalVelocity_mm_per_ns"], float(args.dch_sig_mm_ns), label="SignalVelocity_mm_per_ns")
    _set_any(dch_digitizer, ["GasType"], int(args.dch_gas_type), label="GasType")
    _set_any(dch_digitizer, ["ReadoutWindowStartTime_ns"], float(args.rw_start_ns), label="ReadoutWindowStartTime_ns")
    _set_any(dch_digitizer, ["ReadoutWindowDuration_ns"], float(args.rw_dur_ns), label="ReadoutWindowDuration_ns")

    _set_any(dch_digitizer, ["JobTag"], job_tag, label="JobTag")

    # DCHdigi_v02 optionally uses DataAlgFORGEANT.root; fetch if missing
    cluster_file = "DataAlgFORGEANT.root"
    if not os.path.exists(cluster_file):
        url = "https://fccsw.web.cern.ch/fccsw/filesForSimDigiReco/IDEA/DataAlgFORGEANT.root"
        print(f"[setup] Fetching {cluster_file} from {url}")
        try:
            subprocess.run(["wget", "--no-verbose", "--timeout=180", "--tries=2", "--no-clobber", url], check=True)
        except Exception as e:
            print(f"[setup][WARN] Could not fetch DataAlgFORGEANT.root: {e} (ok if your digi doesn't use it)")

    _set_any(dch_digitizer, ["fileDataAlg"], cluster_file, label="fileDataAlg")
    _set_any(dch_digitizer, ["calculate_dndx"], False, label="calculate_dndx")
    _set_any(dch_digitizer, ["create_debug_histograms"], False, label="create_debug_histograms")

# Choose wire digi collection name used as GGTF input
wire_coll = "DCHDigi2Collection" if args.dchDigiVersion == "v02" else "DCH_DigiCollection"

def _guess_wire_simlink_collections(override: str):
    if override:
        return [override]
    if args.dchDigiVersion == "v02":
        return ["DCHDigi2SimLinkCollection", "DCHDigiSimLinkCollection", "DCHDigi2SimLink", "DCHDigiSimLink"]
    return ["DCHDigiSimLinkCollection", "DCHDigi2SimLinkCollection", "DCHDigiSimLink", "DCHDigi2SimLink"]

# GGTF truth-gate uses these
wire_simlink_colls_for_ggtf = _guess_wire_simlink_collections(args.ggtf_wireSimLinkColl)

# ----------------- GGTF_tracking (Option A) -----------------
GGTF = None
if will_run_ggtf:
    try:
        try:
            from TrackingConf import GGTF_tracking
        except Exception:
            from Configurables import GGTF_tracking
    except Exception as e:
        print("[GGTF][FATAL] cannot import GGTF_tracking:", e)
        traceback.print_exc()
        raise

    GGTF = GGTF_tracking("GGTF_tracking")
    GGTF.OutputLevel = DEBUG if args.ggtfLog == "DEBUG" else INFO

    # Inputs (match your GGTF_tracking.cpp)
    _set_any(GGTF, ["InputWireHitCollections"], [wire_coll], label="InputWireHitCollections")
    _set_any(GGTF, ["InputPlanarHitCollections"], [], label="InputPlanarHitCollections")
    _set_any(GGTF, ["InputWireSimLinkCollections"], wire_simlink_colls_for_ggtf, label="InputWireSimLinkCollections")

    # Output tracks
    _set_any(GGTF, ["OutputTracksGGTF"], [args.ggtfTracksOut], label="OutputTracksGGTF")

    # Model + thresholds
    _set_any(GGTF, ["ModelPath"], stage_model(args.modelPath), label="ModelPath")
    _set_any(GGTF, ["Tbeta"], float(args.tbeta), label="Tbeta")
    _set_any(GGTF, ["Td"], float(args.td), label="Td")
    _set_any(GGTF, ["OnnxChunk"], int(args.onnxChunk), label="OnnxChunk")

    # Optional caps
    if int(args.maxHitsPerEvent) > 0:
        _set_any(GGTF, ["MaxHitsPerEvent"], int(args.maxHitsPerEvent), label="MaxHitsPerEvent")
    else:
        print("[GGTF] maxHitsPerEvent=0 -> no cap")

    # Wire robustness
    _set_any(GGTF, ["DropWireIfAbsDTooLarge"], bool(args.ggtf_dropWireIfAbsDTooLarge), label="DropWireIfAbsDTooLarge")
    _set_any(GGTF, ["MaxAbsDMM"], float(args.ggtf_maxAbsDMM), label="MaxAbsDMM")

    # Label-0 handling
    _set_any(GGTF, ["ZeroMinSizeKeep"], int(args.ggtf_zeroMinSizeKeep), label="ZeroMinSizeKeep")
    _set_any(GGTF, ["MinWireFracKeep"], float(args.ggtf_minWireFracKeep), label="MinWireFracKeep")
    _set_any(GGTF, ["PromoteZeroIfGood"], bool(args.ggtf_promoteZeroIfGood), label="PromoteZeroIfGood")
    _set_any(GGTF, ["SkipZeroIfSmall"], bool(args.ggtf_skipZeroIfSmall), label="SkipZeroIfSmall")
    _set_any(GGTF, ["SkipZeroAlways"], bool(args.ggtf_skipZeroAlways), label="SkipZeroAlways")

    # Truth gating
    _set_any(GGTF, ["FilterInputWiresByTruthPdg"], bool(args.ggtf_filterInputWiresByTruthPdg),
             label="FilterInputWiresByTruthPdg")
    _set_any(GGTF, ["KeepTruthPdg"], int(args.ggtf_keepTruthPdg), label="KeepTruthPdg")
    _set_any(GGTF, ["DropWireIfUnlinked"], bool(args.ggtf_dropWireIfUnlinked), label="DropWireIfUnlinked")

    # Services/metadata
    _set_any(GGTF, ["GeoSvcName"], "GeoSvc", label="GeoSvcName")
    _set_any(GGTF, ["DchName"], args.dchName, label="DchName")
    _set_any(GGTF, ["JobTag"], job_tag, label="JobTag")

    print(
        "[GGTF] configured | "
        f"Tbeta={getattr(GGTF,'Tbeta','?')} Td={getattr(GGTF,'Td','?')} "
        f"wireColl={wire_coll} tracksOut={args.ggtfTracksOut} log={args.ggtfLog}"
    )
    if args.ggtfLog == "DEBUG":
        _dump_props(GGTF, title="GGTF_props")

# ----------------- GenFit2 services (optional; C++ also sets ConstField internally) -----------------
field_svc_obj = None
material_svc_obj = None

if args.fitter == "genfit2" and args.stage == "fit":
    try:
        from Configurables import DD4hepFieldSvc
        field_svc_obj = DD4hepFieldSvc("GenFitFieldSvc", GeoSvcName="GeoSvc")
        print(f"[genfit] Using DD4hepFieldSvc -> {field_svc_obj.getName()}")
    except Exception as e:
        print(f"[genfit][INFO] DD4hepFieldSvc not available (ok): {e}")

    try:
        from Configurables import DD4hepMaterialSvc
        material_svc_obj = DD4hepMaterialSvc("GenFitMaterialSvc", GeoSvcName="GeoSvc")
        print(f"[genfit] Using DD4hepMaterialSvc -> {material_svc_obj.getName()}")
    except Exception as e:
        print(f"[genfit][INFO] DD4hepMaterialSvc not available: {e}")
        if gf_useMat_effective:
            print("[genfit][WARN] Material svc missing; if gGeoManager is also missing, fitter will hard-disable material.")

# ----------------- Configure GenFit2DCHFitter -----------------
fitter_alg = None

def _configure_genfit2():
    try:
        try:
            from TrackingConf import GenFit2DCHFitter
        except Exception:
            from Configurables import GenFit2DCHFitter
    except Exception as e:
        print("[fitter][FATAL] cannot import GenFit2DCHFitter:", e)
        traceback.print_exc()
        return None

    alg = GenFit2DCHFitter("GenFit2DCHFitter")
    alg.OutputLevel = DEBUG if args.fitterLog == "DEBUG" else INFO

    # Data handles (match your C++ Transformer keys)
    _set_any(alg, ["inputTracks", "InputTracks"], [args.ggtfTracksOut], label="inputTracks")
    _set_any(alg, ["outputTracks", "OutputTracks"], [args.fitOut], label="outputTracks")

    # Core physics knobs
    _set_any(alg, ["Bz"], float(args.gf_bz), label="Bz")
    _set_any(alg, ["PDG"], int(args.gf_pdg), label="PDG")

    # NEW: TGeo root file (optional) for gGeoManager fallback
    if args.tgeoFile:
        _set_any(alg, ["TGeoFile"], str(args.tgeoFile), label="TGeoFile")
    else:
        print("[fitter] tgeoFile not provided; relying on GeoSvc/DD4hep to populate gGeoManager (may be null).")

    # Material policy
    _set_any(alg, ["UseMaterialEffects"], bool(gf_useMat_effective), label="UseMaterialEffects")
    _set_any(alg, ["DisableEnergyLoss"], bool(args.gf_disableEloss), label="DisableEnergyLoss")
    _set_any(alg, ["DisableAllMaterialEffects"], bool(args.gf_disableAllMat), label="DisableAllMaterialEffects")
    _set_any(alg, ["HardDisableMaterialIfNoGeo"], bool(args.gf_hardDisableMatIfNoGeo), label="HardDisableMaterialIfNoGeo")

    # Input safety / hygiene
    _set_any(alg, ["RejectNegativeLabels"], bool(args.gf_rejectNegativeLabels), label="RejectNegativeLabels")
    _set_any(alg, ["SortHits"], bool(args.gf_sortHits), label="SortHits")
    _set_any(alg, ["DeduplicateHits"], bool(args.gf_dedup), label="DeduplicateHits")
    _set_any(alg, ["DedupTolMM"], float(args.gf_dedupTolMM), label="DedupTolMM")

    # Pre-fit outlier veto (geometry-only)
    _set_any(alg, ["PreFitOutlierVeto"], bool(args.gf_prefitOutlierVeto), label="PreFitOutlierVeto")
    _set_any(alg, ["OutlierMaxDrop"], int(args.gf_outlierMaxDrop), label="OutlierMaxDrop")
    _set_any(alg, ["OutlierCircleResidualMM"], float(args.gf_outlierCircleResidualMM), label="OutlierCircleResidualMM")
    _set_any(alg, ["OutlierChordResidualMM"], float(args.gf_outlierChordResidualMM), label="OutlierChordResidualMM")
    _set_any(alg, ["OutlierMinKeep"], int(args.gf_outlierMinKeep), label="OutlierMinKeep")

    # Fit strategy
    _set_any(alg, ["UseKFPreFit"], bool(args.gf_useKFPreFit), label="UseKFPreFit")
    _set_any(alg, ["KFMaxIters"], int(args.gf_kfMaxIters), label="KFMaxIters")
    _set_any(alg, ["UseDAF"], bool(args.gf_useDAF), label="UseDAF")
    _set_any(alg, ["DAFMaxIters"], int(args.gf_dafMaxIters), label="DAFMaxIters")
    _set_any(alg, ["FallbackToKFIfDAFFails"], bool(args.gf_fallbackToKFIfDAFFails), label="FallbackToKFIfDAFFails")
    _set_any(alg, ["TryBothMomentumDirections"], bool(args.gf_tryBothMomDirs), label="TryBothMomentumDirections")

    # Acceptance / minimums
    _set_any(alg, ["MinHitsPerTrack"], int(args.gf_minHitsPerTrack), label="MinHitsPerTrack")
    _set_any(alg, ["MinMeasurementsToFit"], int(args.gf_minMeasurementsToFit), label="MinMeasurementsToFit")
    _set_any(alg, ["MinFittedPointsWithFI"], int(args.gf_minFittedPointsWithFI), label="MinFittedPointsWithFI")
    _set_any(alg, ["MaxChi2Ndf"], float(args.gf_maxChi2Ndf), label="MaxChi2Ndf")

    # Publishing
    _set_any(alg, ["UseBiasedStateForPublish"], bool(args.gf_useBiasedStateForPublish), label="UseBiasedStateForPublish")
    _set_any(alg, ["PublishStateCentralFrac"], float(args.gf_publishStateCentralFrac), label="PublishStateCentralFrac")

    _set_any(alg, ["PublishPTMaxGeV"], float(args.gf_publishPTMaxGeV), label="PublishPTMaxGeV")
    _set_any(alg, ["InvalidPTSentinel"], float(args.gf_invalidPTSentinel), label="InvalidPTSentinel")
    _set_any(alg, ["OmegaVarGood"], float(args.gf_omegaVarGood), label="OmegaVarGood")
    _set_any(alg, ["OmegaVarBad"], float(args.gf_omegaVarBad), label="OmegaVarBad")

    # Units / wire / drift model
    _set_any(alg, ["PositionUnitScale"], float(args.gf_positionUnitScale), label="PositionUnitScale")
    _set_any(alg, ["WireHalfLengthMM"], float(args.gf_wireHalfLengthMM), label="WireHalfLengthMM")
    _set_any(alg, ["MaxDriftMM"], float(args.gf_maxDriftMM), label="MaxDriftMM")
    _set_any(alg, ["MaxDriftMMForHit"], float(args.gf_maxDriftMMForHit), label="MaxDriftMMForHit")
    _set_any(alg, ["MinDriftErrMM"], float(args.gf_minDriftErrMM), label="MinDriftErrMM")
    _set_any(alg, ["MaxDriftErrMM"], float(args.gf_maxDriftErrMM), label="MaxDriftErrMM")

    # Seed control
    _set_any(alg, ["SeedEndpointK"], int(args.gf_seedEndpointK), label="SeedEndpointK")
    _set_any(alg, ["SeedTangentK"], int(args.gf_seedTangentK), label="SeedTangentK")
    _set_any(alg, ["SeedPosSigmaMM"], float(args.gf_seedPosSigmaMM), label="SeedPosSigmaMM")
    _set_any(alg, ["SeedMomSigmaGeV"], float(args.gf_seedMomSigmaGeV), label="SeedMomSigmaGeV")
    _set_any(alg, ["SeedPTFallbackGeV"], float(args.gf_seedPTFallbackGeV), label="SeedPTFallbackGeV")
    _set_any(alg, ["SeedPTMinGeV"], float(args.gf_seedPTMinGeV), label="SeedPTMinGeV")
    _set_any(alg, ["SeedPTMaxGeV"], float(args.gf_seedPTMaxGeV), label="SeedPTMaxGeV")
    _set_any(alg, ["SeedPMinGeV"], float(args.gf_seedPMinGeV), label="SeedPMinGeV")
    _set_any(alg, ["UseSagittaSeed"], bool(args.gf_useSagittaSeed), label="UseSagittaSeed")
    _set_any(alg, ["MinSagittaForSeedMM"], float(args.gf_minSagittaForSeedMM), label="MinSagittaForSeedMM")

    # Observability gating
    _set_any(alg, ["MinHitsForObs"], int(args.gf_minHitsForObs), label="MinHitsForObs")
    _set_any(alg, ["ObsSigmaEffMM"], float(args.gf_obsSigmaEffMM), label="ObsSigmaEffMM")
    _set_any(alg, ["ObsMinPhiSpanRad"], float(args.gf_obsMinPhiSpanRad), label="ObsMinPhiSpanRad")
    _set_any(alg, ["ObsMinChordMM"], float(args.gf_obsMinChordMM), label="ObsMinChordMM")
    _set_any(alg, ["ObsMinSagittaMM"], float(args.gf_obsMinSagittaMM), label="ObsMinSagittaMM")
    _set_any(alg, ["ObsMinScore"], float(args.gf_obsMinScore), label="ObsMinScore")
    _set_any(alg, ["SkipIfObsTooLow"], bool(args.gf_skipIfObsTooLow), label="SkipIfObsTooLow")

    # PD guards / stats / diagnostics
    _set_any(alg, ["MinCovEigenvalue"], float(args.gf_minCovEigenvalue), label="MinCovEigenvalue")
    _set_any(alg, ["StatsTruncCentralFrac"], float(args.gf_statsTruncCentralFrac), label="StatsTruncCentralFrac")
    _set_any(alg, ["DiagEveryNTracks"], int(args.gf_diagEveryNTracks), label="DiagEveryNTracks")

    # detId policy / angles
    _set_any(alg, ["DetId"], int(args.gf_detId), label="DetId")
    _set_any(alg, ["UseLabelAsDetId"], bool(args.gf_useLabelAsDetId), label="UseLabelAsDetId")
    _set_any(alg, ["WireAnglesAreDegrees"], bool(args.gf_wireAnglesAreDegrees), label="WireAnglesAreDegrees")

    # Metadata
    _set_any(alg, ["JobTag"], job_tag, label="JobTag")

    print(f"[fitter] GenFit2DCHFitter configured; input='{args.ggtfTracksOut}' output='{args.fitOut}'")
    if args.fitterLog == "DEBUG":
        _dump_props(alg, title="GenFit2DCHFitter_props")
    return alg

if args.stage == "fit" and args.fitter == "genfit2":
    fitter_alg = _configure_genfit2()

# ----------------- Assemble pipeline -----------------
reco_members = []

# stage semantics: cumulative unless --skipDigi
if args.stage in ("digi", "ggtf", "fit"):
    if (not args.skipDigi) and dch_digitizer is not None:
        reco_members.append(dch_digitizer)
    elif not args.skipDigi and dch_digitizer is None:
        raise RuntimeError("Internal error: digitizer should exist but is None.")

if args.stage in ("ggtf", "fit"):
    if GGTF is None:
        raise RuntimeError("GGTF is required for stage ggtf/fit but could not be configured.")
    reco_members.append(GGTF)

if args.stage == "fit" and fitter_alg is not None:
    reco_members.append(fitter_alg)

# Wrap with Reader/Writer if available
top_algs = list(reco_members)
try:
    from k4FWCore import getReader, getWriter
    reader = getReader()
    writer = getWriter()
    top_algs = [reader] + top_algs + [writer]
except Exception:
    pass

print(f"[pipeline] TopAlg order: {[alg.getFullName() for alg in top_algs]}")

# ----------------- Services -----------------
ext_svcs = [
    geoservice,
    EventDataSvc("EventDataSvc"),
    UniqueIDGenSvc("UniqueIDGenSvc"),
    RndmGenSvc(),
    svc,
]
if field_svc_obj is not None:
    ext_svcs.append(field_svc_obj)
if material_svc_obj is not None:
    ext_svcs.append(material_svc_obj)

mgr = GaudiApp(
    TopAlg=top_algs,
    EvtSel="NONE",
    EvtMax=-1,
    ExtSvc=ext_svcs,
    OutputLevel=DEBUG,
)
