# runDCHTestTrackFinder.py (tri-fitter edition, crash-safe; v02 digi aware)

import os
import math
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
parser.add_argument("--inputFile",  default="ddsim_output_edm4hep.root",
                    help="Input EDM4hep file (from ddsim or digi)")
parser.add_argument("--outputFile", default="output_digi_tracks.root",
                    help="Output EDM4hep file")
parser.add_argument("--modelPath",  default="",
                    help="ONNX model path for GGTF_tracking; accepts .onnx, .onnx.md5, http(s)://, root://")
parser.add_argument("--compactXML", default="",
                    help="Path/URL to compact XML (same one used by ddsim)")
parser.add_argument("--dchSimHits", default="DCHCollection",
                    help="Name of DCH SimTrackerHit collection in the input file")
parser.add_argument("--dchName",    default="DCH_v2",
                    help="DD4hep detector name for the DCH (e.g. DCH_v2, CDCH, DCH)")

# --- NEW: global job tag CLI --------------------------------------------------
parser.add_argument(
    "--jobTag",
    default="",
    help="Optional free-form tag stored in metadata (overrides auto tag). "
         "If empty, an automatic tag based on script/input/stage/fitter is used.",
)

# ----------------- Digitizer selection (v01/v02) -----------------
parser.add_argument("--dchDigiVersion", choices=["v01","v02"], default="v01",
                    help="Choose DCH digitizer implementation")

# v01 common knobs (still honored when present)
parser.add_argument("--zResolution_mm",  type=float, default=30.0, help="z-resolution (mm)")
parser.add_argument("--xyResolution_mm", type=float, default=0.10, help="xy-resolution (mm)")

# v02 extra knobs (silently ignored by v01)
# --- compatibility aliases for your shell/local_chain flags ---
parser.add_argument("--dch-xy-mm",  type=float, dest="xyResolution_mm",
                    help="Alias for --xyResolution_mm")
parser.add_argument("--dch-z-mm",   type=float, dest="zResolution_mm",
                    help="Alias for --zResolution_mm")
parser.add_argument("--dch-readout-start-ns", type=float, dest="rw_start_ns",
                    help="Alias for --rw-start-ns")
parser.add_argument("--dch-readout-dur-ns",   type=float, dest="rw_dur_ns",
                    help="Alias for --rw-duration-ns")

parser.add_argument("--dch-deadtime-ns",     dest="dch_deadtime_ns", type=float, default=400.0,
                    help="[v02] cell deadtime (ns)")
parser.add_argument("--dch-drift-vel-um-ns", dest="dch_drift_um_ns", type=float, default=-1.0,
                    help="[v02] drift velocity (um/ns). If <0, auto by GasType")
parser.add_argument("--dch-signal-vel-mm-ns",dest="dch_sig_mm_ns",   type=float,
                    default=2.0/3.0*299792458.0*1e-6,
                    help="[v02] signal velocity along wire (mm/ns). Default 2/3 c")
parser.add_argument("--dch-gas-type",        dest="dch_gas_type",    type=int,   default=0,
                    help="[v02] gas: 0 He(90)-iC4H10(10), 1 He, 2 Ar(50)-C2H6(50), 3 Ar")
parser.add_argument("--rw-start-ns",         dest="rw_start_ns",     type=float, default=1.0,
                    help="[v02] readout window start (ns)")
parser.add_argument("--rw-duration-ns",      dest="rw_dur_ns",       type=float, default=450.0,
                    help="[v02] readout window duration (ns)")

# ----------------- GGTF clustering -----------------
parser.add_argument("--tbeta", type=float, default=0.6, help="GGTF beta threshold")
parser.add_argument("--td",    type=float, default=0.3, help="GGTF distance threshold")

# Runtime / projection
parser.add_argument("--wireGateMM", type=float, default=3.0,    help="Wire→circle gate [mm]")
parser.add_argument("--onnxChunk",  type=int,   default=4096,   help="ONNX hits per slice")
parser.add_argument("--max3DHitsPerEvent", type=int, default=1000000, help="3D hits cap per event")
parser.add_argument("--max3DPerTrack",     type=int, default=100000,  help="3D hits cap per track")
parser.add_argument("--maxHitsPerEvent",   type=int, default=8000,    help="Cap input hits (0=off)")
parser.add_argument("--produce3DHits", action="store_true", default=True,
                    help="If set, also write GGTF_3DHits")
parser.add_argument("--ggtfLog", choices=["INFO","DEBUG"], default="INFO",
                    help="GGTF_tracking OutputLevel")

# ----------------- Stage control -----------------
parser.add_argument("--stage", choices=["digi","ggtf","fit"], default="fit",
                    help="Which pipeline stage(s) to run")

# ----------------- Fitter selection -----------------
parser.add_argument("--fitter",
                    choices=["none","genfit2","simple","threepoint"],
                    default="genfit2",
                    help="Choose post-GGTF fitter")

parser.add_argument("--fitOut", default="GenFitTracks",
                    help="Output collection name for fitted tracks")
parser.add_argument("--fitterLog", choices=["INFO","DEBUG"], default="INFO",
                    help="Fitter OutputLevel")

# If GenFit2 is unavailable, optionally fall back to Simple
parser.add_argument("--fallbackIfNoGenFit2", dest="fallbackIfNoGenFit2",
                    action="store_true", default=True,
                    help="If GenFit2DCHFitter cannot be imported, fall back to SimpleFitDCHFitter")
parser.add_argument("--no-fallbackIfNoGenFit2", dest="fallbackIfNoGenFit2",
                    action="store_false")

# ----------------- GenFit2-specific knobs (prefix gf-) -----------------
parser.add_argument("--gf-useMat", dest="gf_useMat", action="store_true",  default=True,
                    help="Enable material effects in GenFit2")
parser.add_argument("--no-gf-useMat", dest="gf_useMat", action="store_false")
parser.add_argument("--gf-sortHits", dest="gf_sortHits", action="store_true", default=True)
parser.add_argument("--no-gf-sortHits", dest="gf_sortHits", action="store_false")
parser.add_argument("--gf-dedup", dest="gf_dedup", action="store_true", default=True)
parser.add_argument("--no-gf-dedup", dest="gf_dedup", action="store_false")
parser.add_argument("--gf-posScale", type=float, default=0.1,  help="mm→cm scale for positions")
parser.add_argument("--gf-len2m",    type=float, default=0.01, help="cm→m for seeding geometry")
parser.add_argument("--gf-dedupTol",   type=float, default=0.10, help="Dedup tol [mm]")
parser.add_argument("--gf-hitSigmaXY", type=float, default=0.60, help="XY sigma [mm]")
parser.add_argument("--gf-hitSigmaZ",  type=float, default=3.00, help="Z  sigma [mm]")
parser.add_argument("--gf-seedPosSigma", type=float, default=30.0, help="Seed pos sigma [mm]")
parser.add_argument("--gf-seedMomSigma", type=float, default=2.0,  help="Seed mom sigma [GeV]")
parser.add_argument("--gf-seedPTMin",    type=float, default=0.30, help="Min pT seed [GeV]")
parser.add_argument("--gf-seedPTMax",    type=float, default=50.0, help="Max pT seed [GeV]")
parser.add_argument("--gf-seedPMin",     type=float, default=1.2,  help="Min |p| seed [GeV]")
parser.add_argument("--gf-bz",  type=float, default=2.0, help="Bz [T]")
parser.add_argument("--gf-pdg", type=int,   default=13,  help="PDG hypothesis")
parser.add_argument("--gf-minGroup",        type=int,   default=6)
parser.add_argument("--gf-useFallback",     dest="gf_useFallback", action="store_true",  default=True)
parser.add_argument("--no-gf-useFallback",  dest="gf_useFallback", action="store_false")
parser.add_argument("--gf-fallbackEpsCM",   type=float, default=2.0)
parser.add_argument("--gf-fallbackMinPts",  type=int,   default=6)
parser.add_argument("--gf-retry",          dest="gf_retry", action="store_true",  default=True)
parser.add_argument("--no-gf-retry",       dest="gf_retry", action="store_false")
parser.add_argument("--gf-retryMeasInfl",  type=float, default=4.0)
parser.add_argument("--gf-retrySeedPos",   type=float, default=3.0)
parser.add_argument("--gf-retrySeedMom",   type=float, default=3.0)
parser.add_argument("--gf-maxMeasPerGroup",type=int,   default=0)

# ----------------- SimpleFit-specific knobs (prefix sf-) -----------------
parser.add_argument("--sf-bz",          type=float, default=2.0,  help="Bz [T]")
parser.add_argument("--sf-posScale",    type=float, default=0.1,  help="mm→cm scale")
parser.add_argument("--sf-len2m",       type=float, default=0.01, help="cm→m for R→pT")
parser.add_argument("--sf-minGroup",    type=int,   default=5,    help="Min hits per label/cluster")
parser.add_argument("--sf-useFallback", dest="sf_useFallback", action="store_true",  default=True)
parser.add_argument("--no-sf-useFallback", dest="sf_useFallback", action="store_false")
parser.add_argument("--sf-fallbackEpsCM",  type=float, default=2.5, help="DBSCAN eps [cm]")
parser.add_argument("--sf-fallbackMinPts", type=int,   default=8,   help="DBSCAN minPts")
parser.add_argument("--sf-sortHits",    dest="sf_sortHits", action="store_true", default=True)
parser.add_argument("--no-sf-sortHits", dest="sf_sortHits", action="store_false")
parser.add_argument("--sf-dedup",       dest="sf_dedup", action="store_true", default=True)
parser.add_argument("--no-sf-dedup",    dest="sf_dedup", action="store_false")
parser.add_argument("--sf-dedupTol",    type=float, default=0.50, help="Dedup tol [mm]")
parser.add_argument("--sf-maxMeasPerGroup", type=int, default=80, help="Downsample cap (0=off)")
parser.add_argument("--sf-outHisto",    default="", help="If set, write QA histos here (root)")

# ----------------- ThreePointFitter-specific knobs (prefix tp-) -----------------
parser.add_argument("--tp-bz",          type=float, default=2.0,  help="Bz [T]")
parser.add_argument("--tp-posScale",    type=float, default=0.1,  help="mm→cm scale")
parser.add_argument("--tp-len2m",       type=float, default=0.01, help="cm→m for R→pT")
parser.add_argument("--tp-minGroup",    type=int,   default=3,    help="Need at least 3 hits")
parser.add_argument("--tp-useFallback", dest="tp_useFallback", action="store_true",  default=True)
parser.add_argument("--no-tp-useFallback", dest="tp_useFallback", action="store_false")
parser.add_argument("--tp-fallbackEpsCM",  type=float, default=3.0)
parser.add_argument("--tp-fallbackMinPts", type=int,   default=3)
parser.add_argument("--tp-sortHits",    dest="tp_sortHits", action="store_true", default=True)
parser.add_argument("--no-tp-sortHits", dest="tp_sortHits", action="store_false")
parser.add_argument("--tp-dedup",       dest="tp_dedup", action="store_true", default=True)
parser.add_argument("--no-tp-dedup",    dest="tp_dedup", action="store_false")
parser.add_argument("--tp-dedupTol",    type=float, default=0.50, help="Dedup tol [mm]")
parser.add_argument("--tp-maxMeasPerGroup", type=int, default=24, help="Downsample cap (0=off)")
parser.add_argument("--tp-outHisto",    default="", help="If set, write QA histos here (root)")
parser.add_argument("--tp-minDeltaPhi", type=float, default=0.02,
                    help="Minimum |Δphi| among chosen 3 points [rad]")
parser.add_argument("--tp-minChordMM",  type=float, default=5.0,
                    help="Minimum chord length among 3 points [mm]")
parser.add_argument("--tp-minRadiusMM", type=float, default=100.0,
                    help="Reject tiny circles with R < this [mm]")
parser.add_argument("--tp-fitTanLambda", dest="tp_fitTanLambda", action="store_true", default=True,
                    help="Estimate tanLambda via z(phi) regression")
parser.add_argument("--no-tp-fitTanLambda", dest="tp_fitTanLambda", action="store_false")
parser.add_argument("--tp-printDiag", dest="tp_printDiag", action="store_true", default=False,
                    help="Print diagnostics for first N events/groups")
parser.add_argument("--no-tp-printDiag", dest="tp_printDiag", action="store_false")
parser.add_argument("--tp-diagEveryN", type=int, default=100,
                    help="Diagnostic print frequency (events)")

# ----------------- GGTF label-0 handling -----------------
parser.add_argument("--ggtf-zeroMinSizeKeep", type=int, default=8)
parser.add_argument("--ggtf-minWireFracKeep", type=float, default=0.60)
parser.add_argument("--ggtf-promoteZeroIfGood", action="store_true", default=True)
parser.add_argument("--no-ggtf-promoteZeroIfGood", dest="ggtf_promoteZeroIfGood", action="store_false")
parser.add_argument("--ggtf-skipZeroIfSmall", action="store_true", default=True)
parser.add_argument("--no-ggtf-skipZeroIfSmall", dest="ggtf_skipZeroIfSmall", action="store_false")
parser.add_argument("--ggtf-skipZeroAlways", action="store_true", default=False)
parser.add_argument("--no-ggtf-skipZeroAlways", dest="ggtf_skipZeroAlways", action="store_false")

# ----------------- GenFit2 Fitter outlier / residual options -----------------

# z(phi) outlier filter toggles
parser.add_argument("--gf-filterZOutliers",
                    dest="gf_filterZOutliers",
                    action="store_true",
                    default=False,
                    help="Enable z(phi)-based outlier rejection in GenFit2DCHFitter")
parser.add_argument("--no-gf-filterZOutliers",
                    dest="gf_filterZOutliers",
                    action="store_false")

parser.add_argument("--gf-zOutlierAbsMM",
                    type=float,
                    default=80.0,
                    help="Absolute |z residual| cut [mm] for GF z-outlier filter")
parser.add_argument("--gf-zOutlierNSigma",
                    type=float,
                    default=3.5,
                    help="N-sigma cut for GF z-outlier filter (0 disables sigma part)")
parser.add_argument("--gf-zOutlierMinFracKeep",
                    type=float,
                    default=0.5,
                    help="Minimum fraction of hits to keep after filtering "
                         "(else filter is skipped for that group)")

# generic residual filter toggles (match local_chain.sh)
parser.add_argument(
    "--gf-residualFilterEnable",
    dest="gf_residualFilterEnable",
    action="store_true",
    default=False,
    help="Enable generic residual filter in GenFit2DCHFitter",
)
parser.add_argument(
    "--no-gf-residualFilterEnable",
    dest="gf_residualFilterEnable",
    action="store_false",
)
parser.add_argument(
    "--gf-residualMaxPull",
    type=float,
    default=5.0,
    help="Max |residual pull| to keep a measurement in the residual filter",
)
parser.add_argument(
    "--gf-residualMaxChi2",
    type=float,
    default=25.0,
    help="Max per-hit chi2 to keep a measurement in the residual filter",
)

# -----------------------------------------------------------------------------


args = parser.parse_args()
print(f"[GF2] UseMaterialEffects={args.gf_useMat}")

# --- construct a global job_tag string ---------------------------------------
if args.jobTag:
    job_tag = args.jobTag
else:
    script_name = os.path.basename(globals().get("__file__", "runDCHTestTrackFinder.py"))
    job_tag = (
        f"{script_name}"
        f"|input={os.path.basename(args.inputFile)}"
        f"|stage={args.stage}"
        f"|fitter={args.fitter}"
        f"|digi={args.dchDigiVersion}"
    )
print(f"[meta] JobTag = '{job_tag}'")

if args.fitter == "genfit2" and args.gf_useMat and not args.compactXML:
    raise RuntimeError(
        "UseMaterialEffects=True but --compactXML not provided. "
        "Provide the same compact used by ddsim so TGeo is available."
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
AuditorSvc().Auditors = [ ChronoAuditor(), MemoryAuditor() ]

# ----------------- IO -----------------
svc = IOSvc("IOSvc")
svc.Input  = args.inputFile
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

# ----------------- DCH Digitizer (robust resolver) -----------------
def _resolve_dch_digitizer():
    tried = []
    candidates = [
        ("DCHdigiConf",    "DCHdigi_v02"),
        ("Configurables",  "DCHdigi_v02"),
        ("DCHdigiConf",    "DCHdigi_v01"),
        ("Configurables",  "DCHdigi_v01"),
        ("DCHdigiConf",    "DCHdigi"),
        ("Configurables",  "DCHdigi"),
        ("TrackingConf",   "DCHdigi_v02"),
        ("TrackingConf",   "DCHdigi_v01"),
        ("TrackingConf",   "DCHdigi"),
    ]
    for mod, cls in candidates:
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
        f"\nHints:\n"
        f"  • Ensure k4RecTracker installed libs are on GAUDI_PLUGIN_PATH.\n"
        f"  • Confirm libDCHdigi*.so exists under your install lib dir.\n"
        f"  • Re-run `ninja install` in k4RecTracker.\n"
        f"  • Current GAUDI_PLUGIN_PATH: {paths}"
    )

dch_digitizer = _resolve_dch_digitizer()

# Best-effort property setting
def _set_if_has_digitizer(obj, name, value):
    try:
        if hasattr(obj, name):
            setattr(obj, name, value)
            print(f"[digitizer] set {name} = {value}")
            return True
    except Exception as e:
        print(f"[digitizer] could not set {name}: {e}")
    return False

# Common v01/v02 inputs
_set_if_has_digitizer(dch_digitizer, "DCH_simhits", [args.dchSimHits])
_set_if_has_digitizer(dch_digitizer, "DCH_name", args.dchName)
# --- v02 input bindings (safe no-ops for v01) ---
_set_if_has_digitizer(dch_digitizer, "InputSimHitCollection", [args.dchSimHits])
_set_if_has_digitizer(dch_digitizer, "HeaderName", ["EventHeader"])

# v01 legacy knobs (harmless for v02; set only if exist)
_set_if_has_digitizer(dch_digitizer, "fileDataAlg", "DataAlgFORGEANT.root")
_set_if_has_digitizer(dch_digitizer, "calculate_dndx", False)
_set_if_has_digitizer(dch_digitizer, "create_debug_histograms", False)

# Resolutions (shared semantics)
_set_if_has_digitizer(dch_digitizer, "zResolution_mm",  args.zResolution_mm)
_set_if_has_digitizer(dch_digitizer, "xyResolution_mm", args.xyResolution_mm)

# v02-specific (silently ignored by v01)
_set_if_has_digitizer(dch_digitizer, "Deadtime_ns",              args.dch_deadtime_ns)
_set_if_has_digitizer(dch_digitizer, "DriftVelocity_um_per_ns",  args.dch_drift_um_ns)
_set_if_has_digitizer(dch_digitizer, "SignalVelocity_mm_per_ns", args.dch_sig_mm_ns)
_set_if_has_digitizer(dch_digitizer, "GasType",                  args.dch_gas_type)
_set_if_has_digitizer(dch_digitizer, "ReadoutWindowStartTime_ns", args.rw_start_ns)
_set_if_has_digitizer(dch_digitizer, "ReadoutWindowDuration_ns",  args.rw_dur_ns)

# NEW: pass JobTag into digitizer (DCHdigi_v02 will record it in metadata)
_set_if_has_digitizer(dch_digitizer, "JobTag", job_tag)

# Ensure cluster-size file for v01 (harmless no-op for v02)
cluster_file = "DataAlgFORGEANT.root"
if not os.path.exists(cluster_file):
    url = "https://fccsw.web.cern.ch/fccsw/filesForSimDigiReco/IDEA/DataAlgFORGEANT.root"
    print(f"[setup] Fetching {cluster_file} from {url}")
    subprocess.run(["wget", "--no-verbose", "--timeout=180", "--tries=2", "--no-clobber", url], check=True)

# ----------------- Choose wire collection name by digi version -----------------
if args.dchDigiVersion == "v02":
    wire_coll = "DCHDigi2Collection"
else:
    wire_coll = "DCH_DigiCollection"

# ----------------- Track Finder (GGTF) -----------------
try:
    from TrackingConf import GGTF_tracking
except Exception:
    from Configurables import GGTF_tracking  # registry fallback

GGTF = GGTF_tracking(
    "GGTF_tracking",
    InputWireHitCollections=[wire_coll],
    InputPlanarHitCollections=[],
    OutputTracksGGTF=["CDCHTracks"],
    Output3DHits=["GGTF_3DHits"],
    OutputLevel=INFO,
)

GGTF.ModelPath = stage_model(args.modelPath)
GGTF.Tbeta = args.tbeta
GGTF.Td    = args.td

for name, val in [
    ("ZeroMinSizeKeep", args.ggtf_zeroMinSizeKeep),
    ("MinWireFracKeep", args.ggtf_minWireFracKeep),
    ("PromoteZeroIfGood", args.ggtf_promoteZeroIfGood),
    ("SkipZeroIfSmall", args.ggtf_skipZeroIfSmall),
    ("SkipZeroAlways", args.ggtf_skipZeroAlways),
]:
    try:
        setattr(GGTF, name, val)
    except Exception as e:
        print(f"[warn] could not set GGTF.{name}: {e}")

for name, val in [
    ("WireGateMM", args.wireGateMM),
    ("OnnxChunk", args.onnxChunk),
    ("Max3DHitsPerEvent", args.max3DHitsPerEvent),
    ("Max3DPerTrack", args.max3DPerTrack),
]:
    try:
        setattr(GGTF, name, val)
    except Exception as e:
        print(f"[warn] could not set GGTF.{name}: {e}")

try:
    GGTF.Produce3DHits = bool(args.produce3DHits)
except Exception:
    pass

try:
    if int(args.maxHitsPerEvent) > 0:
        GGTF.maxHitsPerEvent = int(args.maxHitsPerEvent)
except Exception:
    print("[warn] GGTF.maxHitsPerEvent property not present; ignoring.")

# NEW: pass JobTag into GGTF_tracking so it writes it into GGTF_trackingConfig metadata
try:
    GGTF.JobTag = job_tag
    print(f"[GGTF] JobTag set to '{job_tag}'")
except Exception as e:
    print(f"[GGTF][warn] could not set JobTag: {e}")

GGTF.OutputLevel = DEBUG if args.ggtfLog == "DEBUG" else INFO
print(
    f"[GGTF] stage={args.stage} ModelPath={GGTF.ModelPath} Tbeta={GGTF.Tbeta} Td={GGTF.Td} "
    f"produce3DHits={getattr(GGTF,'Produce3DHits','n/a')} "
    f"maxHitsPerEvent={getattr(GGTF,'MaxHitsPerEvent',0)} "
    f"wireGateMM={getattr(GGTF,'WireGateMM','n/a')} "
    f"onnxChunk={getattr(GGTF,'OnnxChunk','n/a')} "
    f"max3DHitsPerEvent={getattr(GGTF,'Max3DHitsPerEvent','n/a')} "
    f"max3DPerTrack={getattr(GGTF,'Max3DPerTrack','n/a')} "
    f"log={args.ggtfLog}  wireColl={wire_coll}"
)

# ----------------- Helper: quiet property setter -----------------
def _set_if_has(obj, name, value):
    try:
        if hasattr(obj, name):
            setattr(obj, name, value)
            print(f"[fitter] set {name} = {value}")
            return True
    except Exception as e:
        print(f"[fitter] could not set {name}: {e}")
    return False

# ----------------- Optional: field/material (GenFit2 only needs them) --------
field_svc_name = None
material_svc_name = None
field_svc_obj = None
material_svc_obj = None

if args.fitter == "genfit2":
    try:
        from Configurables import DD4hepFieldSvc
        field_svc_obj = DD4hepFieldSvc("GenFitFieldSvc", GeoSvcName="GeoSvc")
        field_svc_name = field_svc_obj.getName()
        print(f"[genfit] Using DD4hepFieldSvc -> {field_svc_name}")
    except Exception as e:
        print(f"[genfit] DD4hepFieldSvc not available: {e}")
        try:
            from Configurables import ConstBFieldSvc
            field_svc_obj = ConstBFieldSvc("GenFitFieldSvc", Bz=args.gf_bz)
            field_svc_name = field_svc_obj.getName()
            print(f"[genfit] Using ConstBFieldSvc Bz={args.gf_bz}T -> {field_svc_name}")
        except Exception as e2:
            print(f"[genfit][WARN] No field service available; relying on fitter.Bz={args.gf_bz}")

    try:
        from Configurables import DD4hepMaterialSvc
        material_svc_obj = DD4hepMaterialSvc("GenFitMaterialSvc", GeoSvcName="GeoSvc")
        material_svc_name = material_svc_obj.getName()
        print(f"[genfit] Using DD4hepMaterialSvc -> {material_svc_name}")
    except Exception as e:
        print(f"[genfit] DD4hepMaterialSvc not available: {e}")
        try:
            from Configurables import GenFitMaterialSvc
            material_svc_obj = GenFitMaterialSvc("GenFitMaterialSvc", GeoSvcName="GeoSvc")
            material_svc_name = material_svc_obj.getName()
            print(f"[genfit] Using GenFitMaterialSvc -> {material_svc_name}")
        except Exception as e2:
            print("[genfit][WARN] Material services unavailable; forcing UseMaterialEffects=False for this run.")
            args.gf_useMat = False  # hard-disable to avoid misconfiguration

# ----------------- Choose and configure fitter -----------------
fitter_alg = None
requested_fitter = args.fitter

def _configure_genfit2():
    try:
        try:
            from TrackingConf import GenFit2DCHFitter
        except Exception:
            from Configurables import GenFit2DCHFitter
    except Exception as e:
        print("[fitter][ERROR] cannot import GenFit2DCHFitter:", e)
        traceback.print_exc()
        return None

    alg = GenFit2DCHFitter("GenFit2DCHFitter")
    alg.OutputLevel = DEBUG if args.fitterLog == "DEBUG" else INFO

    for prop, val in (
        ("Input3DHits", "GGTF_3DHits"),
        ("input3DHits", "GGTF_3DHits"),
        ("inputHits",   ["GGTF_3DHits"]),
    ):
        if _set_if_has(alg, prop, val):
            break
    for prop, val in (
        ("OutTracks",   args.fitOut),
        ("outputTracks", [args.fitOut]),
        ("outputTracks", args.fitOut),
        ("TracksOut",   args.fitOut),
    ):
        if _set_if_has(alg, prop, val):
            break

    for prop, val in [
        ("FieldSvc", field_svc_name),
        ("BFieldSvc", field_svc_name),
        ("MaterialSvc", material_svc_name),
        ("MaterialEffectsSvc", material_svc_name),
        ("GeoSvcName", "GeoSvc"),
        ("UseTGeoPath", True),
    ]:
        if val is not None or prop == "UseTGeoPath":
            _set_if_has(alg, prop, val if prop != "UseTGeoPath" else True)

    _set_if_has(alg, "Bz", args.gf_bz)
    _set_if_has(alg, "PDG", args.gf_pdg)
    _set_if_has(alg, "UseMaterialEffects", args.gf_useMat)
    _set_if_has(alg, "PositionUnitScale", args.gf_posScale)
    _set_if_has(alg, "InternalLengthToMeters", args.gf_len2m)

    _set_if_has(alg, "HitSigmaXYMM", args.gf_hitSigmaXY)
    _set_if_has(alg, "HitSigmaZMM",  args.gf_hitSigmaZ)
    _set_if_has(alg, "SeedPosSigmaMM",  args.gf_seedPosSigma)
    _set_if_has(alg, "SeedMomSigmaGeV", args.gf_seedMomSigma)
    _set_if_has(alg, "SeedPTMinGeV",    args.gf_seedPTMin)
    _set_if_has(alg, "SeedPTMaxGeV",    args.gf_seedPTMax)
    _set_if_has(alg, "SeedPMinGeV",     args.gf_seedPMin)

    _set_if_has(alg, "MinGroupSize",          args.gf_minGroup)
    _set_if_has(alg, "UseFallbackClustering", args.gf_useFallback)
    _set_if_has(alg, "FallbackEpsCM",         args.gf_fallbackEpsCM)
    _set_if_has(alg, "FallbackMinPts",        args.gf_fallbackMinPts)
    _set_if_has(alg, "RetryIfNoFitterInfo",   args.gf_retry)
    _set_if_has(alg, "RetryMeasInfl",         args.gf_retryMeasInfl)
    _set_if_has(alg, "RetrySeedPosInfl",      args.gf_retrySeedPos)
    _set_if_has(alg, "RetrySeedMomInfl",      args.gf_retrySeedMom)
    _set_if_has(alg, "MaxMeasPerGroup",       args.gf_maxMeasPerGroup)

    _set_if_has(alg, "pdgHypothesis", args.gf_pdg)
    _set_if_has(alg, "minHitsOnTrack", 4)
    _set_if_has(alg, "maxChi2", 1e6)

    # NEW: z(phi) outlier filter wiring
    _set_if_has(alg, "FilterZOutliers",     args.gf_filterZOutliers)
    _set_if_has(alg, "ZOutlierAbsMM",       args.gf_zOutlierAbsMM)
    _set_if_has(alg, "ZOutlierNSigma",      args.gf_zOutlierNSigma)
    _set_if_has(alg, "ZOutlierMinFracKeep", args.gf_zOutlierMinFracKeep)

    # NEW: generic residual filter wiring
    _set_if_has(alg, "ResidualFilterEnable", args.gf_residualFilterEnable)
    _set_if_has(alg, "ResidualMaxPull",      args.gf_residualMaxPull)
    _set_if_has(alg, "ResidualMaxChi2",      args.gf_residualMaxChi2)

    # NEW: pass JobTag into GenFit2DCHFitter (if the property exists)
    _set_if_has(alg, "JobTag", job_tag)

    print(f"[fitter] GenFit2DCHFitter configured; output -> '{args.fitOut}'")
    return alg

def _configure_simple():
    Simple = None
    tried = []
    for mod, name in (
        ("TrackingConf", "SimpleFitDCHFitter"),
        ("Configurables", "SimpleFitDCHFitter"),
    ):
        try:
            m = __import__(mod, fromlist=[name])
            cand = getattr(m, name)
            if callable(cand):
                Simple = cand
                print(f"[fitter] Using {mod}.{name}")
                break
            else:
                tried.append(f"{mod}.{name} (not callable; shim instance?)")
        except Exception as e:
            tried.append(f"{mod}.{name} ({e})")

    if Simple is None:
        msg = "[fitter][WARN] No callable SimpleFitDCHFitter found; tried:\n  " + "\n  ".join(tried)
        print(msg)
        print("[fitter][WARN] Falling back to ThreePointFitter.")
        return _configure_threepoint()

    alg = Simple("SimpleFitDCHFitter")
    alg.OutputLevel = DEBUG if args.fitterLog == "DEBUG" else INFO

    for prop, val in (("inputHits", ["GGTF_3DHits"]), ("input3DHits", "GGTF_3DHits")):
        if _set_if_has(alg, prop, val):
            break
    for prop, val in (("outputTracks", [args.fitOut]), ("outputTracks", args.fitOut)):
        if _set_if_has(alg, prop, val):
            break

    _set_if_has(alg, "Bz", args.sf_bz)
    _set_if_has(alg, "PositionUnitScale", args.sf_posScale)
    _set_if_has(alg, "InternalLengthToMeters", args.sf_len2m)
    _set_if_has(alg, "UseMaterialEffects", args.gf_useMat)
    _set_if_has(alg, "UseTGeoPath", True)
    _set_if_has(alg, "MinGroupSize",            args.sf_minGroup)
    _set_if_has(alg, "UseFallbackClustering",   args.sf_useFallback)
    _set_if_has(alg, "FallbackEpsCM",           args.sf_fallbackEpsCM)
    _set_if_has(alg, "FallbackMinPts",          args.sf_fallbackMinPts)
    _set_if_has(alg, "SortHits",                args.sf_sortHits)
    _set_if_has(alg, "DeduplicateHits",         args.sf_dedup)
    _set_if_has(alg, "DedupTolMM",              args.sf_dedupTol)
    _set_if_has(alg, "MaxMeasPerGroup",         args.sf_maxMeasPerGroup)

    if args.sf_outHisto:
        _set_if_has(alg, "OutputHistoFile", args.sf_outHisto)

    # NEW: pass JobTag into SimpleFitDCHFitter
    _set_if_has(alg, "JobTag", job_tag)

    print(f"[fitter] SimpleFitDCHFitter configured; output -> '{args.fitOut}'")
    return alg

def _configure_threepoint():
    from Configurables import ThreePointFitter
    alg = ThreePointFitter("ThreePointFitter")
    alg.OutputLevel = DEBUG if args.fitterLog == "DEBUG" else INFO

    for prop, val in (("inputHits", ["GGTF_3DHits"]), ("input3DHits", "GGTF_3DHits")):
        if _set_if_has(alg, prop, val):
            break
    for prop, val in (("outputTracks", [args.fitOut]), ("outputTracks", args.fitOut)):
        if _set_if_has(alg, prop, val):
            break

    _set_if_has(alg, "Bz", args.tp_bz)
    _set_if_has(alg, "PDG", args.gf_pdg)
    _set_if_has(alg, "PositionUnitScale", args.tp_posScale)
    _set_if_has(alg, "InternalLengthToMeters", args.tp_len2m)

    _set_if_has(alg, "UseMaterialEffects", args.gf_useMat)
    _set_if_has(alg, "UseTGeoPath", True)

    _set_if_has(alg, "MinGroupSize",            args.tp_minGroup)
    _set_if_has(alg, "UseFallbackClustering",   args.tp_useFallback)
    _set_if_has(alg, "FallbackEpsCM",           args.tp_fallbackEpsCM)
    _set_if_has(alg, "FallbackMinPts",          args.tp_fallbackMinPts)
    _set_if_has(alg, "SortHits",                args.tp_sortHits)
    _set_if_has(alg, "DeduplicateHits",         args.tp_dedup)
    _set_if_has(alg, "DedupTolMM",              args.tp_dedupTol)
    _set_if_has(alg, "MaxMeasPerGroup",         args.tp_maxMeasPerGroup)

    if args.tp_outHisto:
        _set_if_has(alg, "OutputHistoFile", args.tp_outHisto)

    _set_if_has(alg, "MinDeltaPhi",     args.tp_minDeltaPhi)
    _set_if_has(alg, "MinChordMM",      args.tp_minChordMM)
    _set_if_has(alg, "MinRadiusMM",     args.tp_minRadiusMM)
    _set_if_has(alg, "FitTanLambda",    args.tp_fitTanLambda)
    _set_if_has(alg, "PrintDiagnostics", args.tp_printDiag)
    _set_if_has(alg, "DiagEveryN",      args.tp_diagEveryN)

    # NEW: pass JobTag into ThreePointFitter
    _set_if_has(alg, "JobTag", job_tag)

    print(f"[fitter] ThreePointFitter configured; output -> '{args.fitOut}'")
    return alg

# Build fitter (with optional fallback)
fitter_alg = None

if args.stage == "fit" and requested_fitter != "none":
    if requested_fitter == "genfit2":
        fitter_alg = _configure_genfit2()
        if fitter_alg is None and args.fallbackIfNoGenFit2:
            print("[fitter][WARN] GenFit2DCHFitter unavailable in this runtime; falling back to SimpleFitDCHFitter.")
            fitter_alg = _configure_simple()
        elif fitter_alg is None:
            print("[fitter][FATAL] GenFit2 requested but not available and fallback disabled; no tracks will be written.")
    elif requested_fitter == "simple":
        fitter_alg = _configure_simple()
    elif requested_fitter == "threepoint":
        fitter_alg = _configure_threepoint()

# --- Optional: collection size probe (if available) ---------------------------
try:
    from Configurables import EDM4hepCollectionSizePrinter as SizePrinter
    size_printer = SizePrinter(
        "SizePrinter",
        CollectionsToPrint=["GGTF_3DHits", args.fitOut],
        OutputLevel=INFO,
    )
except Exception:
    size_printer = None

# ----------------- AppMgr / pipeline -----------------
top_algs = []
if args.stage in ("digi", "ggtf", "fit"):
    top_algs.append(dch_digitizer)
if args.stage in ("ggtf", "fit"):
    top_algs.append(GGTF)
if args.stage == "fit" and fitter_alg is not None:
    top_algs.append(fitter_alg)
if size_printer is not None:
    top_algs.append(size_printer)

# Try reader/writer if available
try:
    from k4FWCore import getReader, getWriter
    reader = getReader()
    writer = getWriter()
    top_algs = [reader] + top_algs + [writer]
except Exception:
    pass

print(f"[pipeline] TopAlg order: {[alg.getFullName() for alg in top_algs]}")

# ---- Ext services ----
ext_svcs = [
    geoservice,
    EventDataSvc("EventDataSvc"),
    UniqueIDGenSvc("uidSvc"),
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
