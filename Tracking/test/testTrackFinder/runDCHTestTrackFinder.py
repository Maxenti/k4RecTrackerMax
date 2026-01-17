#!/usr/bin/env python3
# runDCHTestTrackFinder.py  (WIRE+DRIFT chain; v02 digi + labeled SenseWireHits + GenFit2)
#
# Pipeline (new):
#   SimTrackerHits (DCHCollection)  ->
#   DCHdigi_v02 produces SenseWireHit digis (DCHDigi2Collection) + links ->
#   GGTF_tracking clusters and outputs:
#       - extension::TrackCollection (CDCHTracks) [unchanged behavior]
#       - labeled SenseWireHits (GGTF_SenseWireHits) with hit.type = cluster label
#       - optional debug ALL used wires (GGTF_AllSenseWireHits)
#   GenFit2DCHFitter consumes GGTF_SenseWireHits and builds WireMeasurementNew internally.
#
# Key changes vs older script:
#   - NO GGTF_3DHits anywhere
#   - GGTF properties renamed to ProduceSenseWireHits / ProduceAllSenseWireHits etc.
#   - GenFit2DCHFitter input points to SenseWireHits collection, not 3D hits
#
# Critical:
#   - UniqueIDGenSvc MUST be instantiated with name "UniqueIDGenSvc" (matches C++ default lookup)

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
parser.add_argument("--inputFile",  default="ddsim_output_edm4hep.root",
                    help="Input EDM4hep file (from ddsim or digi)")
parser.add_argument("--outputFile", default="output_digi_ggtf_fit.root",
                    help="Output EDM4hep file")
parser.add_argument("--compactXML", default="",
                    help="Path/URL to compact XML (same one used by ddsim). Required for GenFit material effects.")
parser.add_argument("--dchSimHits", default="DCHCollection",
                    help="Name of DCH SimTrackerHit collection in the input file")
parser.add_argument("--dchName",    default="DCH_v2",
                    help="DD4hep detector name for the DCH (e.g. DCH_v2)")

parser.add_argument("--modelPath", default="",
                    help="ONNX model path for GGTF_tracking; accepts .onnx, .onnx.md5, http(s)://, root://")

parser.add_argument("--stage", choices=["digi","ggtf","fit"], default="fit",
                    help="Which pipeline stage(s) to run")

parser.add_argument("--jobTag", default="",
                    help="Optional free-form tag stored in metadata. If empty, auto-generated.")

# ----------------- Digitizer (v02 default) -----------------
parser.add_argument("--dchDigiVersion", choices=["v01","v02"], default="v02",
                    help="Choose DCH digitizer implementation")
parser.add_argument("--xyResolution_mm", type=float, default=0.10, help="xy-resolution (mm)")
parser.add_argument("--zResolution_mm",  type=float, default=30.0, help="z-resolution (mm)")

# v02 knobs
parser.add_argument("--dch-deadtime-ns",     dest="dch_deadtime_ns", type=float, default=450.0,
                    help="[v02] cell deadtime (ns)")
parser.add_argument("--dch-drift-vel-um-ns", dest="dch_drift_um_ns", type=float, default=-1.0,
                    help="[v02] drift velocity (um/ns). If <0, auto by GasType")
parser.add_argument("--dch-signal-vel-mm-ns",dest="dch_sig_mm_ns", type=float,
                    default=2.0/3.0*299792458.0*1e-6,
                    help="[v02] signal velocity along wire (mm/ns). Default 2/3 c")
parser.add_argument("--dch-gas-type", dest="dch_gas_type", type=int, default=0,
                    help="[v02] gas: 0 He(90)-iC4H10(10), 1 He, 2 Ar(50)-C2H6(50), 3 Ar")
parser.add_argument("--rw-start-ns", dest="rw_start_ns", type=float, default=1.0,
                    help="[v02] readout window start (ns)")
parser.add_argument("--rw-duration-ns", dest="rw_dur_ns", type=float, default=900.0,
                    help="[v02] readout window duration (ns)")

# ----------------- GGTF clustering -----------------
parser.add_argument("--tbeta", type=float, default=0.6, help="GGTF beta threshold")
parser.add_argument("--td",    type=float, default=0.3, help="GGTF distance threshold")
parser.add_argument("--onnxChunk", type=int, default=4096, help="ONNX hits per slice")
parser.add_argument("--maxHitsPerEvent", type=int, default=0, help="Cap input hits (0=off)")

# GGTF labeled SenseWireHits output controls
parser.add_argument("--ggtf-produceSenseWireHits", dest="ggtf_produceSenseWireHits",
                    action="store_true", default=True,
                    help="Emit per-track labeled SenseWireHits for fitter (GGTF_SenseWireHits). Default True.")
parser.add_argument("--no-ggtf-produceSenseWireHits", dest="ggtf_produceSenseWireHits",
                    action="store_false")

parser.add_argument("--ggtf-produceAllSenseWireHits", dest="ggtf_produceAllSenseWireHits",
                    action="store_true", default=False,
                    help="Emit debug ALL used wire inputs (GGTF_AllSenseWireHits). Default False.")
parser.add_argument("--no-ggtf-produceAllSenseWireHits", dest="ggtf_produceAllSenseWireHits",
                    action="store_false")
parser.add_argument("--ggtf-allSenseWireHitsTypeValue", type=int, default=-777,
                    help="Type value used for GGTF_AllSenseWireHits debug hits (default -777).")

# GGTF wire sanity
parser.add_argument("--ggtf-dropWireIfAbsDTooLarge", dest="ggtf_dropWireIfAbsDTooLarge",
                    action="store_true", default=True)
parser.add_argument("--no-ggtf-dropWireIfAbsDTooLarge", dest="ggtf_dropWireIfAbsDTooLarge",
                    action="store_false")
parser.add_argument("--ggtf-maxAbsDMM", type=float, default=30.0,
                    help="Max |distanceToWire| [mm] allowed before dropping input wire (if enabled).")

# GGTF label-0 handling
parser.add_argument("--ggtf-zeroMinSizeKeep", type=int, default=8)
parser.add_argument("--ggtf-minWireFracKeep", type=float, default=0.60)
parser.add_argument("--ggtf-promoteZeroIfGood", action="store_true", default=True)
parser.add_argument("--no-ggtf-promoteZeroIfGood", dest="ggtf_promoteZeroIfGood", action="store_false")
parser.add_argument("--ggtf-skipZeroIfSmall", action="store_true", default=True)
parser.add_argument("--no-ggtf-skipZeroIfSmall", dest="ggtf_skipZeroIfSmall", action="store_false")
parser.add_argument("--ggtf-skipZeroAlways", action="store_true", default=False)
parser.add_argument("--no-ggtf-skipZeroAlways", dest="ggtf_skipZeroAlways", action="store_false")

# GGTF truth-gating
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

parser.add_argument("--ggtfLog", choices=["INFO","DEBUG"], default="INFO",
                    help="GGTF_tracking OutputLevel")

# ----------------- Fitter selection (GenFit2 recommended) -----------------
parser.add_argument("--fitter", choices=["none","genfit2"], default="genfit2")
parser.add_argument("--fitOut", default="GenFitTracks", help="Output collection name for fitted tracks")
parser.add_argument("--fitterLog", choices=["INFO","DEBUG"], default="INFO")

# GenFit2 knobs (subset; keep what matters)
parser.add_argument("--gf-useMat", dest="gf_useMat", action="store_true", default=True,
                    help="Enable material effects in GenFit2 (requires --compactXML)")
parser.add_argument("--no-gf-useMat", dest="gf_useMat", action="store_false")
parser.add_argument("--gf-bz", type=float, default=2.0, help="Bz [T]")
parser.add_argument("--gf-pdg", type=int, default=13, help="PDG hypothesis")

parser.add_argument("--gf-sortHits", dest="gf_sortHits", action="store_true", default=True)
parser.add_argument("--no-gf-sortHits", dest="gf_sortHits", action="store_false")
parser.add_argument("--gf-dedup", dest="gf_dedup", action="store_true", default=True)
parser.add_argument("--no-gf-dedup", dest="gf_dedup", action="store_false")
parser.add_argument("--gf-dedupTol", type=float, default=0.10, help="Dedup tol [mm]")

parser.add_argument("--gf-minGroup", type=int, default=6, help="Minimum hits per cluster label to fit")
parser.add_argument("--gf-maxMeasPerGroup", type=int, default=0, help="Cap measurements per group (0=off)")

# Optional outlier filtering toggles (only if your fitter implements them)
parser.add_argument("--gf-filterZOutliers", dest="gf_filterZOutliers",
                    action="store_true", default=False)
parser.add_argument("--no-gf-filterZOutliers", dest="gf_filterZOutliers",
                    action="store_false")
parser.add_argument("--gf-zOutlierAbsMM", type=float, default=80.0)
parser.add_argument("--gf-zOutlierNSigma", type=float, default=3.5)
parser.add_argument("--gf-zOutlierMinFracKeep", type=float, default=0.5)

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
        f"|digi={args.dchDigiVersion}"
        f"|fitter={args.fitter}"
    )

print(f"[meta] JobTag='{job_tag}'")

# Effective material flag
gf_useMat_effective = bool(args.gf_useMat)
if args.fitter == "genfit2" and gf_useMat_effective and not args.compactXML:
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

def _has_prop(obj, name: str) -> bool:
    # Gaudi Configurable properties are not reliably visible to hasattr()
    try:
        props = obj.getProperties()  # dict
        return name in props
    except Exception:
        pass
    try:
        props = obj.properties()     # sometimes exists
        return name in props
    except Exception:
        pass
    # last resort: try setting and catch
    return True

def _set_if_has(obj, name, value, label=""):
    try:
        if not _has_prop(obj, name):
            return False
        setattr(obj, name, value)
        tag = label or name
        print(f"[set] {tag}: {obj.getName()}.{name} = {value}")
        return True
    except Exception as e:
        print(f"[set][WARN] could not set {obj.getName()}.{name}: {e}")
        return False

def _set_any(obj, candidates, value, label=""):
    for p in candidates:
        if _set_if_has(obj, p, value, label=label or p):
            return p
    return None

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

dch_digitizer = _resolve_dch_digitizer(args.dchDigiVersion)

# Configure digitizer (property names vary; set both old/new where possible)
_set_any(dch_digitizer,
         ["InputSimHitCollection", "DCH_simhits", "DCHSimHits", "InputSimHits"],
         [args.dchSimHits],
         label="InputSimHitCollection")

_set_any(dch_digitizer,
         ["HeaderName"],
         ["EventHeader"],
         label="HeaderName")

_set_any(dch_digitizer,
         ["DCH_name", "DCHName"],
         args.dchName,
         label="DCH_name")

# Force consistent output names for v02 if properties exist
if args.dchDigiVersion == "v02":
    _set_any(dch_digitizer, ["OutputDigihitCollection"], ["DCHDigi2Collection"], label="OutputDigihitCollection")
    _set_any(dch_digitizer, ["OutputLinkCollection"],    ["DCHDigi2SimLinkCollection"], label="OutputLinkCollection")
else:
    _set_any(dch_digitizer, ["OutputDigihitCollection"], ["DCH_DigiCollection"], label="OutputDigihitCollection")
    _set_any(dch_digitizer, ["OutputLinkCollection"],    ["DCHDigiSimLinkCollection"], label="OutputLinkCollection")

_set_any(dch_digitizer, ["xyResolution_mm", "xyResolutionMM"], float(args.xyResolution_mm), label="xyResolution_mm")
_set_any(dch_digitizer, ["zResolution_mm",  "zResolutionMM"],  float(args.zResolution_mm),  label="zResolution_mm")

# v02 extras (silently ignored if not present)
_set_any(dch_digitizer, ["Deadtime_ns"], float(args.dch_deadtime_ns), label="Deadtime_ns")
_set_any(dch_digitizer, ["DriftVelocity_um_per_ns"], float(args.dch_drift_um_ns), label="DriftVelocity_um_per_ns")
_set_any(dch_digitizer, ["SignalVelocity_mm_per_ns"], float(args.dch_sig_mm_ns), label="SignalVelocity_mm_per_ns")
_set_any(dch_digitizer, ["GasType"], int(args.dch_gas_type), label="GasType")
_set_any(dch_digitizer, ["ReadoutWindowStartTime_ns"], float(args.rw_start_ns), label="ReadoutWindowStartTime_ns")
_set_any(dch_digitizer, ["ReadoutWindowDuration_ns"], float(args.rw_dur_ns), label="ReadoutWindowDuration_ns")

_set_any(dch_digitizer, ["JobTag"], job_tag, label="JobTag")

# DCHdigi_v02 optionally uses DataAlgFORGEANT.root; fetch if missing and property exists
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

# Choose wire digi collection names based on digi version
wire_coll = "DCHDigi2Collection" if args.dchDigiVersion == "v02" else "DCH_DigiCollection"

def _guess_wire_simlink_collections():
    if args.ggtf_wireSimLinkColl:
        return [args.ggtf_wireSimLinkColl]
    if args.dchDigiVersion == "v02":
        return ["DCHDigi2SimLinkCollection", "DCHDigiSimLinkCollection", "DCHDigi2SimLink", "DCHDigiSimLink"]
    return ["DCHDigiSimLinkCollection", "DCHDigi2SimLinkCollection", "DCHDigiSimLink", "DCHDigi2SimLink"]

wire_simlink_colls = _guess_wire_simlink_collections()

# ----------------- GGTF_tracking -----------------
try:
    from TrackingConf import GGTF_tracking
except Exception:
    from Configurables import GGTF_tracking

GGTF = GGTF_tracking(
    "GGTF_tracking",
    InputWireHitCollections=[wire_coll],
    InputPlanarHitCollections=[],
    InputWireSimLinkCollections=wire_simlink_colls,
    OutputTracksGGTF=["CDCHTracks"],
    OutputSenseWireHits=["GGTF_SenseWireHits"],
    OutputAllSenseWireHits=["GGTF_AllSenseWireHits"],
    OutputLevel=INFO,
)

GGTF.ModelPath = stage_model(args.modelPath)
GGTF.Tbeta = float(args.tbeta)
GGTF.Td    = float(args.td)

_set_any(GGTF, ["OnnxChunk"], int(args.onnxChunk), label="OnnxChunk")

# MaxHitsPerEvent differs across builds
if int(args.maxHitsPerEvent) > 0:
    _set_any(GGTF, ["MaxHitsPerEvent", "maxHitsPerEvent"], int(args.maxHitsPerEvent), label="MaxHitsPerEvent")
else:
    print("[GGTF] maxHitsPerEvent=0 -> no cap")

# Outputs toggles
_set_any(GGTF, ["ProduceSenseWireHits"], bool(args.ggtf_produceSenseWireHits), label="ProduceSenseWireHits")
_set_any(GGTF, ["ProduceAllSenseWireHits"], bool(args.ggtf_produceAllSenseWireHits), label="ProduceAllSenseWireHits")
_set_any(GGTF, ["AllSenseWireHitsTypeValue"], int(args.ggtf_allSenseWireHitsTypeValue), label="AllSenseWireHitsTypeValue")

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
_set_any(GGTF, ["FilterInputWiresByTruthPdg"], bool(args.ggtf_filterInputWiresByTruthPdg), label="FilterInputWiresByTruthPdg")
_set_any(GGTF, ["KeepTruthPdg"], int(args.ggtf_keepTruthPdg), label="KeepTruthPdg")
_set_any(GGTF, ["DropWireIfUnlinked"], bool(args.ggtf_dropWireIfUnlinked), label="DropWireIfUnlinked")

_set_any(GGTF, ["DchName"], args.dchName, label="DchName")
_set_any(GGTF, ["JobTag"], job_tag, label="JobTag")

GGTF.OutputLevel = DEBUG if args.ggtfLog == "DEBUG" else INFO

print(
    "[GGTF] configured | "
    f"ModelPath={getattr(GGTF,'ModelPath','?')} Tbeta={getattr(GGTF,'Tbeta','?')} Td={getattr(GGTF,'Td','?')} "
    f"wireColl={wire_coll} wireSimLinkColls={wire_simlink_colls} "
    f"ProduceSenseWireHits={getattr(GGTF,'ProduceSenseWireHits','?')} "
    f"ProduceAllSenseWireHits={getattr(GGTF,'ProduceAllSenseWireHits','?')} "
    f"MaxAbsDMM={getattr(GGTF,'MaxAbsDMM','?')} "
    f"log={args.ggtfLog}"
)

# ----------------- GenFit2 services (optional) -----------------
field_svc_obj = None
material_svc_obj = None
field_svc_name = None
material_svc_name = None

if args.fitter == "genfit2":
    try:
        from Configurables import DD4hepFieldSvc
        field_svc_obj = DD4hepFieldSvc("GenFitFieldSvc", GeoSvcName="GeoSvc")
        field_svc_name = field_svc_obj.getName()
        print(f"[genfit] Using DD4hepFieldSvc -> {field_svc_name}")
    except Exception as e:
        print(f"[genfit][WARN] DD4hepFieldSvc not available: {e}")
        # Many GenFit setups can still run with fitter.Bz only.

    try:
        from Configurables import DD4hepMaterialSvc
        material_svc_obj = DD4hepMaterialSvc("GenFitMaterialSvc", GeoSvcName="GeoSvc")
        material_svc_name = material_svc_obj.getName()
        print(f"[genfit] Using DD4hepMaterialSvc -> {material_svc_name}")
    except Exception as e:
        print(f"[genfit][WARN] DD4hepMaterialSvc not available: {e}")
        if gf_useMat_effective:
            print("[genfit][WARN] Material services missing -> forcing UseMaterialEffects=False")
            gf_useMat_effective = False

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

    # Input: NEW -> SenseWireHits, not 3D hits
    inp = _set_any(
        alg,
        candidates=[
            "InputHits", "inputHits",
            "InputSenseWireHits", "inputSenseWireHits",
            "InputWireHits", "inputWireHits",
        ],
        value=["GGTF_SenseWireHits"],
        label="Input hits (SenseWireHits)"
    )
    if inp is None:
        # Some builds want a single string
        inp = _set_any(
            alg,
            candidates=["InputHits", "inputHits", "InputSenseWireHits", "inputSenseWireHits"],
            value="GGTF_SenseWireHits",
            label="Input hits (SenseWireHits, string)"
        )

    # Output
    outp = _set_any(
        alg,
        candidates=["outputTracks", "OutputTracks", "OutTracks", "TracksOut"],
        value=[args.fitOut],
        label="Output tracks"
    )
    if outp is None:
        _set_any(alg, ["outputTracks", "OutputTracks", "OutTracks", "TracksOut"], args.fitOut, label="Output tracks")

    # Services (best-effort)
    if field_svc_name is not None:
        _set_any(alg, ["FieldSvc", "BFieldSvc"], field_svc_name, label="FieldSvc")
    if material_svc_name is not None:
        _set_any(alg, ["MaterialSvc", "MaterialEffectsSvc"], material_svc_name, label="MaterialSvc")
    _set_any(alg, ["GeoSvcName"], "GeoSvc", label="GeoSvcName")
    _set_any(alg, ["UseTGeoPath"], True, label="UseTGeoPath")

    # Physics knobs
    _set_any(alg, ["Bz"], float(args.gf_bz), label="Bz")
    _set_any(alg, ["PDG", "pdgHypothesis"], int(args.gf_pdg), label="PDG")
    _set_any(alg, ["UseMaterialEffects"], bool(gf_useMat_effective), label="UseMaterialEffects")

    # Grouping and hygiene
    _set_any(alg, ["MinGroupSize"], int(args.gf_minGroup), label="MinGroupSize")
    _set_any(alg, ["MaxMeasPerGroup"], int(args.gf_maxMeasPerGroup), label="MaxMeasPerGroup")
    _set_any(alg, ["SortHits"], bool(args.gf_sortHits), label="SortHits")
    _set_any(alg, ["DeduplicateHits"], bool(args.gf_dedup), label="DeduplicateHits")
    _set_any(alg, ["DedupTolMM"], float(args.gf_dedupTol), label="DedupTolMM")

    # Optional outlier filters (only if your fitter implements them)
    _set_any(alg, ["FilterZOutliers"], bool(args.gf_filterZOutliers), label="FilterZOutliers")
    _set_any(alg, ["ZOutlierAbsMM"], float(args.gf_zOutlierAbsMM), label="ZOutlierAbsMM")
    _set_any(alg, ["ZOutlierNSigma"], float(args.gf_zOutlierNSigma), label="ZOutlierNSigma")
    _set_any(alg, ["ZOutlierMinFracKeep"], float(args.gf_zOutlierMinFracKeep), label="ZOutlierMinFracKeep")

    _set_any(alg, ["JobTag"], job_tag, label="JobTag")

    print(f"[fitter] GenFit2DCHFitter configured; output -> '{args.fitOut}'")
    return alg

if args.stage == "fit" and args.fitter == "genfit2":
    fitter_alg = _configure_genfit2()

# ----------------- Assemble pipeline -----------------
reco_members = []
if args.stage in ("digi", "ggtf", "fit"):
    reco_members.append(dch_digitizer)
if args.stage in ("ggtf", "fit"):
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

# Services
ext_svcs = [
    geoservice,
    EventDataSvc("EventDataSvc"),
    UniqueIDGenSvc("UniqueIDGenSvc"),  # CRITICAL NAME
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
