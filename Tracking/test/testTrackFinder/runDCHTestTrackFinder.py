#!/usr/bin/env python3
# runDCHTestTrackFinder.py (tri-fitter edition, crash-safe; v02 digi aware)
#
# FIXED (this revision):
#  - Ensures CLI values actually WIN for GGTF + GenFit2 (no silent “profile” overrides).
#  - Wires GenFit2 knobs that were parsed but never applied:
#      * --gf-sortHits / --no-gf-sortHits
#      * --gf-dedup / --no-gf-dedup
#      * --gf-dedupTol
#  - Makes the “summary print” report the *actual* configured GGTF properties (not just args).
#  - Digitizer resolver now respects --dchDigiVersion (v01/v02) preference order.
#  - Explicitly sets v02 output collection names when supported (keeps names consistent).
#  - Robust looper filter wiring WITHOUT importing GaudiSequencer from Gaudi.Configurables.
#
# CRITICAL FIX (this revision):
#  - Instantiate UniqueIDGenSvc with the NAME "UniqueIDGenSvc".
#    Your DCHdigi_v02 resolves it by serviceLocator()->service("UniqueIDGenSvc") by default.
#    If you create it as "uidSvc", digitization will FAIL at initialize().
#
# NOTE:
#  - Truth-gating is MC-truth dependent. If the link collection is absent/empty,
#    GGTF_tracking may effectively disable the gate for that event in C++.


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
parser.add_argument("--dchDigiVersion", choices=["v01","v02"], default="v02",
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

parser.add_argument("--dch-deadtime-ns",     dest="dch_deadtime_ns", type=float, default=450.0,
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
parser.add_argument("--rw-duration-ns",      dest="rw_dur_ns",       type=float, default=900.0,
                    help="[v02] readout window duration (ns)")

# ----------------- GGTF clustering -----------------
parser.add_argument("--tbeta", type=float, default=0.6, help="GGTF beta threshold")
parser.add_argument("--td",    type=float, default=0.3, help="GGTF distance threshold")

# Runtime / projection
parser.add_argument("--wireGateMM", type=float, default=3.0,    help="Wire→circle gate [mm]")
parser.add_argument("--onnxChunk",  type=int,   default=4096,   help="ONNX hits per slice")
parser.add_argument("--max3DHitsPerEvent", type=int, default=1000000, help="3D hits cap per event")
parser.add_argument("--max3DPerTrack",     type=int, default=100000,  help="3D hits cap per track")

# IMPORTANT: default 0 (off) to avoid silently capping "all hits" debug mode
parser.add_argument("--maxHitsPerEvent",   type=int, default=0,        help="Cap input hits (0=off)")

# Produce3DHits as a real toggle pair (matches shell style)
parser.add_argument("--produce3DHits", dest="produce3DHits", action="store_true", default=True,
                    help="Write GGTF_3DHits (default True).")
parser.add_argument("--no-produce3DHits", dest="produce3DHits", action="store_false",
                    help="Disable GGTF_3DHits output.")

parser.add_argument("--ggtfLog", choices=["INFO","DEBUG"], default="INFO",
                    help="GGTF_tracking OutputLevel")

# ----------------- GGTF debug / coverage / unit knobs -------------------
parser.add_argument("--ggtf-3dPosScale", type=float, default=None,
                    help="If supported: scale applied when writing GGTF_3DHits positions (e.g. 10.0 if cm->mm).")
parser.add_argument("--ggtf-threeDHitPosScale", type=float, default=None,
                    help="Alias for --ggtf-3dPosScale.")

parser.add_argument("--ggtf-produceAll3DHits", dest="ggtf_produceAll3DHits",
                    action="store_true", default=False,
                    help="If supported: emit 3D hits for ALL FLATTENED inputs (planar + wire) right after flatten.")
parser.add_argument("--no-ggtf-produceAll3DHits", dest="ggtf_produceAll3DHits",
                    action="store_false")

# Tri-state so we don't override C++ default unless user asked.
parser.add_argument("--ggtf-all3DHitsOnly", dest="ggtf_all3DHitsOnly",
                    action="store_const", const=True, default=None,
                    help="If supported: when ProduceAll3DHits is on, skip per-track 3D hits (avoid duplicates).")
parser.add_argument("--no-ggtf-all3DHitsOnly", dest="ggtf_all3DHitsOnly",
                    action="store_const", const=False,
                    help="If supported: allow both all-input 3D hits and per-track 3D hits (duplicates possible).")

parser.add_argument("--ggtf-all3DHitsTypeValue", type=int, default=None,
                    help="If supported: set Type for the 'all-3D-hits' stream to a constant (e.g. -777).")

parser.add_argument("--ggtf-applyWireGateTo3DHits", dest="ggtf_applyWireGateTo3DHits",
                    action="store_const", const=True, default=None,
                    help="If supported: require wire gate pass for 3D hit emission.")
parser.add_argument("--no-ggtf-applyWireGateTo3DHits", dest="ggtf_applyWireGateTo3DHits",
                    action="store_const", const=False,
                    help="If supported: emit wire 3D hits even if failing gate (still clamps d).")

parser.add_argument("--ggtf-debugPrint3DHitR", dest="ggtf_debugPrint3DHitR",
                    action="store_const", const=True, default=None,
                    help="If supported: enable GGTF 3D-hit radius/unit debug prints.")
parser.add_argument("--no-ggtf-debugPrint3DHitR", dest="ggtf_debugPrint3DHitR",
                    action="store_const", const=False,
                    help="If supported: disable GGTF 3D-hit radius/unit debug prints.")

# ----------------- GGTF truth-PDG gating for wire hits -------------------
parser.add_argument(
    "--ggtf-filterInputWiresByTruthPdg",
    dest="ggtf_filterInputWiresByTruthPdg",
    action="store_true",
    default=False,
    help="If set, GGTF_tracking will exclude wire digis whose linked MCParticle PDG != --ggtf-keepTruthPdg "
         "(requires InputWireSimLinkCollections).",
)
parser.add_argument(
    "--no-ggtf-filterInputWiresByTruthPdg",
    dest="ggtf_filterInputWiresByTruthPdg",
    action="store_false",
)
parser.add_argument(
    "--ggtf-keepTruthPdg",
    type=int,
    default=13,
    help="PDG code to keep when --ggtf-filterInputWiresByTruthPdg is enabled (default 13).",
)
parser.add_argument(
    "--ggtf-dropWireIfUnlinked",
    dest="ggtf_dropWireIfUnlinked",
    action="store_true",
    default=True,
    help="When truth-PDG filtering is enabled: drop wire digis with no truth link (default True).",
)
parser.add_argument(
    "--no-ggtf-dropWireIfUnlinked",
    dest="ggtf_dropWireIfUnlinked",
    action="store_false",
)
parser.add_argument(
    "--ggtf-wireSimLinkColl",
    default="",
    help="Override the wire->SimTrackerHit link collection name for GGTF truth gating. "
         "If empty, an automatic guess based on --dchDigiVersion is used.",
)

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

# ----------------- Looper event filter (C++ Gaudi Alg) -----------------
parser.add_argument("--looperFilter", dest="looperFilter", action="store_true", default=True,
                    help="Enable DCHLooperEventFilter (veto events with too-late simhit times / too many simhits).")
parser.add_argument("--no-looperFilter", dest="looperFilter", action="store_false",
                    help="Disable DCHLooperEventFilter (default).")

parser.add_argument("--looperColl", default="",
                    help="SimTrackerHit collection to filter on (default: --dchSimHits).")

parser.add_argument("--looperTmaxNs", type=float, default=450.0,
                    help="Veto event if max(simhit.time) > this [ns].")

parser.add_argument("--looperNHitsMax", type=int, default=30000,
                    help="Veto event if nSimHits > this (<=0 disables this cut).")

parser.add_argument("--looperKeepEmpty", action="store_true", default=False,
                    help="If set, keep events with 0 simhits (default: drop empty events).")

parser.add_argument("--looperPassIfMissing", dest="looperPassIfMissing", action="store_true", default=True,
                    help="If simhit collection is missing, PASS the event (default True).")
parser.add_argument("--no-looperPassIfMissing", dest="looperPassIfMissing", action="store_false",
                    help="If simhit collection is missing, FAIL the job immediately (safer).")

# -----------------------------------------------------------------------------
args = parser.parse_args()

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

# Effective material flag (we may force it off if services are missing)
gf_useMat_effective = bool(args.gf_useMat)

print(f"[GF2] UseMaterialEffects(requested)={args.gf_useMat}  UseMaterialEffects(effective)={gf_useMat_effective}")
print(f"[meta] JobTag = '{job_tag}'")

if args.fitter == "genfit2" and gf_useMat_effective and not args.compactXML:
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

# ----------------- DCH Digitizer (robust resolver) -----------------
def _resolve_dch_digitizer(version: str):
    tried = []

    # Prefer the requested version first.
    if version == "v02":
        preferred = [("DCHdigiConf", "DCHdigi_v02"), ("Configurables", "DCHdigi_v02"), ("TrackingConf", "DCHdigi_v02")]
        fallback  = [("DCHdigiConf", "DCHdigi_v01"), ("Configurables", "DCHdigi_v01"), ("TrackingConf", "DCHdigi_v01")]
    else:
        preferred = [("DCHdigiConf", "DCHdigi_v01"), ("Configurables", "DCHdigi_v01"), ("TrackingConf", "DCHdigi_v01")]
        fallback  = [("DCHdigiConf", "DCHdigi_v02"), ("Configurables", "DCHdigi_v02"), ("TrackingConf", "DCHdigi_v02")]

    generic = [("DCHdigiConf", "DCHdigi"), ("Configurables", "DCHdigi"), ("TrackingConf", "DCHdigi")]

    for mod, cls in (preferred + fallback + generic):
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

dch_digitizer = _resolve_dch_digitizer(args.dchDigiVersion)

def _set_if_has_digitizer(obj, name, value):
    try:
        if hasattr(obj, name):
            setattr(obj, name, value)
            print(f"[digitizer] set {name} = {value}")
            return True
    except Exception as e:
        print(f"[digitizer] could not set {name}: {e}")
    return False

_set_if_has_digitizer(dch_digitizer, "DCH_simhits", [args.dchSimHits])
_set_if_has_digitizer(dch_digitizer, "DCH_name", args.dchName)
_set_if_has_digitizer(dch_digitizer, "InputSimHitCollection", [args.dchSimHits])
_set_if_has_digitizer(dch_digitizer, "HeaderName", ["EventHeader"])

# Keep output names consistent when the properties exist.
if args.dchDigiVersion == "v02":
    _set_if_has_digitizer(dch_digitizer, "OutputDigihitCollection", ["DCHDigi2Collection"])
    _set_if_has_digitizer(dch_digitizer, "OutputLinkCollection",    ["DCHDigi2SimLinkCollection"])
else:
    _set_if_has_digitizer(dch_digitizer, "OutputDigihitCollection", ["DCH_DigiCollection"])
    _set_if_has_digitizer(dch_digitizer, "OutputLinkCollection",    ["DCHDigiSimLinkCollection"])

_set_if_has_digitizer(dch_digitizer, "fileDataAlg", "DataAlgFORGEANT.root")
_set_if_has_digitizer(dch_digitizer, "calculate_dndx", False)
_set_if_has_digitizer(dch_digitizer, "create_debug_histograms", False)

_set_if_has_digitizer(dch_digitizer, "zResolution_mm",  args.zResolution_mm)
_set_if_has_digitizer(dch_digitizer, "xyResolution_mm", args.xyResolution_mm)

_set_if_has_digitizer(dch_digitizer, "Deadtime_ns",               args.dch_deadtime_ns)
_set_if_has_digitizer(dch_digitizer, "DriftVelocity_um_per_ns",   args.dch_drift_um_ns)
_set_if_has_digitizer(dch_digitizer, "SignalVelocity_mm_per_ns",  args.dch_sig_mm_ns)
_set_if_has_digitizer(dch_digitizer, "GasType",                   args.dch_gas_type)
_set_if_has_digitizer(dch_digitizer, "ReadoutWindowStartTime_ns", args.rw_start_ns)
_set_if_has_digitizer(dch_digitizer, "ReadoutWindowDuration_ns",  args.rw_dur_ns)

_set_if_has_digitizer(dch_digitizer, "JobTag", job_tag)

cluster_file = "DataAlgFORGEANT.root"
if not os.path.exists(cluster_file):
    url = "https://fccsw.web.cern.ch/fccsw/filesForSimDigiReco/IDEA/DataAlgFORGEANT.root"
    print(f"[setup] Fetching {cluster_file} from {url}")
    subprocess.run(["wget", "--no-verbose", "--timeout=180", "--tries=2", "--no-clobber", url], check=True)

# Choose wire digi collection names based on requested digi version.
wire_coll = "DCHDigi2Collection" if args.dchDigiVersion == "v02" else "DCH_DigiCollection"

def _guess_wire_simlink_collections():
    if args.ggtf_wireSimLinkColl:
        return [args.ggtf_wireSimLinkColl]
    if args.dchDigiVersion == "v02":
        return ["DCHDigi2SimLinkCollection", "DCHDigiSimLinkCollection", "DCHDigi2SimLink", "DCHDigiSimLink"]
    else:
        return ["DCHDigiSimLinkCollection", "DCHDigi2SimLinkCollection", "DCHDigiSimLink", "DCHDigi2SimLink"]

wire_simlink_colls = _guess_wire_simlink_collections()

# ----------------- Track Finder (GGTF) -----------------
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
    Output3DHits=["GGTF_3DHits"],
    OutputLevel=INFO,
)

GGTF.ModelPath = stage_model(args.modelPath)
GGTF.Tbeta = float(args.tbeta)
GGTF.Td    = float(args.td)

def _set_if_has_g(obj, name, value):
    try:
        if hasattr(obj, name):
            setattr(obj, name, value)
            print(f"[GGTF] set {name} = {value}")
            return True
    except Exception as e:
        print(f"[GGTF][warn] could not set {name}: {e}")
    return False

# Label-0 handling
for name, val in [
    ("ZeroMinSizeKeep", int(args.ggtf_zeroMinSizeKeep)),
    ("MinWireFracKeep", float(args.ggtf_minWireFracKeep)),
    ("PromoteZeroIfGood", bool(args.ggtf_promoteZeroIfGood)),
    ("SkipZeroIfSmall", bool(args.ggtf_skipZeroIfSmall)),
    ("SkipZeroAlways", bool(args.ggtf_skipZeroAlways)),
]:
    _set_if_has_g(GGTF, name, val)

# Core GGTF runtime knobs
for name, val in [
    ("WireGateMM", float(args.wireGateMM)),
    ("OnnxChunk", int(args.onnxChunk)),
    ("Max3DHitsPerEvent", int(args.max3DHitsPerEvent)),
    ("Max3DPerTrack", int(args.max3DPerTrack)),
]:
    if not _set_if_has_g(GGTF, name, val):
        if name.endswith("MM") and _set_if_has_g(GGTF, name[:-2] + "Mm", val):
            pass

_set_if_has_g(GGTF, "Produce3DHits", bool(args.produce3DHits))

# MaxHitsPerEvent name differs across builds
if int(args.maxHitsPerEvent) > 0:
    if not _set_if_has_g(GGTF, "MaxHitsPerEvent", int(args.maxHitsPerEvent)):
        if not _set_if_has_g(GGTF, "maxHitsPerEvent", int(args.maxHitsPerEvent)):
            print("[GGTF][warn] MaxHitsPerEvent property not present; ignoring.")
else:
    print("[GGTF] maxHitsPerEvent=0 -> no cap")

# Truth gating
_set_if_has_g(GGTF, "FilterInputWiresByTruthPdg", bool(args.ggtf_filterInputWiresByTruthPdg))
_set_if_has_g(GGTF, "KeepTruthPdg", int(args.ggtf_keepTruthPdg))
_set_if_has_g(GGTF, "DropWireIfUnlinked", bool(args.ggtf_dropWireIfUnlinked))
_set_if_has_g(GGTF, "JobTag", job_tag)

# Optional knobs
pos_scale = args.ggtf_3dPosScale if args.ggtf_3dPosScale is not None else args.ggtf_threeDHitPosScale
if pos_scale is not None:
    _set_if_has_g(GGTF, "ThreeDHitPosScale", float(pos_scale))

_set_if_has_g(GGTF, "ProduceAll3DHits", bool(args.ggtf_produceAll3DHits))

if args.ggtf_all3DHitsOnly is not None:
    _set_if_has_g(GGTF, "All3DHitsOnly", bool(args.ggtf_all3DHitsOnly))

if args.ggtf_all3DHitsTypeValue is not None:
    _set_if_has_g(GGTF, "All3DHitsTypeValue", int(args.ggtf_all3DHitsTypeValue))

if args.ggtf_applyWireGateTo3DHits is not None:
    _set_if_has_g(GGTF, "ApplyWireGateTo3DHits", bool(args.ggtf_applyWireGateTo3DHits))

if args.ggtf_debugPrint3DHitR is not None:
    _set_if_has_g(GGTF, "DebugPrint3DHitR", bool(args.ggtf_debugPrint3DHitR))

GGTF.OutputLevel = DEBUG if args.ggtfLog == "DEBUG" else INFO

def _ggtf_prop(name, fallback="n/a"):
    return getattr(GGTF, name, fallback)

print(
    "[GGTF] configured | "
    f"stage={args.stage} "
    f"ModelPath={_ggtf_prop('ModelPath')} "
    f"Tbeta={_ggtf_prop('Tbeta')} Td={_ggtf_prop('Td')} "
    f"Produce3DHits={_ggtf_prop('Produce3DHits')} "
    f"MaxHitsPerEvent={_ggtf_prop('MaxHitsPerEvent', _ggtf_prop('maxHitsPerEvent'))} "
    f"WireGateMM={_ggtf_prop('WireGateMM')} "
    f"OnnxChunk={_ggtf_prop('OnnxChunk')} "
    f"Max3DHitsPerEvent={_ggtf_prop('Max3DHitsPerEvent')} "
    f"Max3DPerTrack={_ggtf_prop('Max3DPerTrack')} "
    f"log={args.ggtfLog} "
    f"wireColl={wire_coll} wireSimLinkColls={wire_simlink_colls} "
    f"FilterInputWiresByTruthPdg={_ggtf_prop('FilterInputWiresByTruthPdg')} "
    f"KeepTruthPdg={_ggtf_prop('KeepTruthPdg')} "
    f"DropWireIfUnlinked={_ggtf_prop('DropWireIfUnlinked')} "
    f"MinWireFracKeep={_ggtf_prop('MinWireFracKeep')} "
    f"ThreeDHitPosScale={_ggtf_prop('ThreeDHitPosScale')} "
    f"ProduceAll3DHits={_ggtf_prop('ProduceAll3DHits')} "
    f"All3DHitsOnly={_ggtf_prop('All3DHitsOnly')} "
    f"All3DHitsTypeValue={_ggtf_prop('All3DHitsTypeValue')} "
    f"ApplyWireGateTo3DHits={_ggtf_prop('ApplyWireGateTo3DHits')} "
    f"DebugPrint3DHitR={_ggtf_prop('DebugPrint3DHitR')}"
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
            field_svc_obj = ConstBFieldSvc("GenFitFieldSvc", Bz=float(args.gf_bz))
            field_svc_name = field_svc_obj.getName()
            print(f"[genfit] Using ConstBFieldSvc Bz={args.gf_bz}T -> {field_svc_name}")
        except Exception:
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
        except Exception:
            print("[genfit][WARN] Material services unavailable; forcing UseMaterialEffects=False for this run.")
            gf_useMat_effective = False

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

    # Inputs
    for prop, val in (
        ("Input3DHits", "GGTF_3DHits"),
        ("input3DHits", "GGTF_3DHits"),
        ("inputHits",   ["GGTF_3DHits"]),
    ):
        if _set_if_has(alg, prop, val):
            break

    # Outputs
    for prop, val in (
        ("OutTracks",   args.fitOut),
        ("outputTracks", [args.fitOut]),
        ("outputTracks", args.fitOut),
        ("TracksOut",   args.fitOut),
    ):
        if _set_if_has(alg, prop, val):
            break

    # Services
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

    # Core physics knobs
    _set_if_has(alg, "Bz", float(args.gf_bz))
    _set_if_has(alg, "PDG", int(args.gf_pdg))

    # IMPORTANT: use the *effective* UseMaterialEffects (may be forced off above)
    _set_if_has(alg, "UseMaterialEffects", bool(gf_useMat_effective))

    _set_if_has(alg, "PositionUnitScale", float(args.gf_posScale))
    _set_if_has(alg, "InternalLengthToMeters", float(args.gf_len2m))

    _set_if_has(alg, "HitSigmaXYMM", float(args.gf_hitSigmaXY))
    _set_if_has(alg, "HitSigmaZMM",  float(args.gf_hitSigmaZ))
    _set_if_has(alg, "SeedPosSigmaMM",  float(args.gf_seedPosSigma))
    _set_if_has(alg, "SeedMomSigmaGeV", float(args.gf_seedMomSigma))
    _set_if_has(alg, "SeedPTMinGeV",    float(args.gf_seedPTMin))
    _set_if_has(alg, "SeedPTMaxGeV",    float(args.gf_seedPTMax))
    _set_if_has(alg, "SeedPMinGeV",     float(args.gf_seedPMin))

    # FIX: previously parsed but not applied
    _set_if_has(alg, "SortHits", bool(args.gf_sortHits))
    _set_if_has(alg, "DeduplicateHits", bool(args.gf_dedup))
    _set_if_has(alg, "DedupTolMM", float(args.gf_dedupTol))

    # Grouping / clustering / retry knobs
    _set_if_has(alg, "MinGroupSize",          int(args.gf_minGroup))
    _set_if_has(alg, "UseFallbackClustering", bool(args.gf_useFallback))
    _set_if_has(alg, "FallbackEpsCM",         float(args.gf_fallbackEpsCM))
    _set_if_has(alg, "FallbackMinPts",        int(args.gf_fallbackMinPts))
    _set_if_has(alg, "RetryIfNoFitterInfo",   bool(args.gf_retry))
    _set_if_has(alg, "RetryMeasInfl",         float(args.gf_retryMeasInfl))
    _set_if_has(alg, "RetrySeedPosInfl",      float(args.gf_retrySeedPos))
    _set_if_has(alg, "RetrySeedMomInfl",      float(args.gf_retrySeedMom))
    _set_if_has(alg, "MaxMeasPerGroup",       int(args.gf_maxMeasPerGroup))

    # Optional “legacy” property names
    _set_if_has(alg, "pdgHypothesis", int(args.gf_pdg))

    # Outlier / residual filters
    _set_if_has(alg, "FilterZOutliers",     bool(args.gf_filterZOutliers))
    _set_if_has(alg, "ZOutlierAbsMM",       float(args.gf_zOutlierAbsMM))
    _set_if_has(alg, "ZOutlierNSigma",      float(args.gf_zOutlierNSigma))
    _set_if_has(alg, "ZOutlierMinFracKeep", float(args.gf_zOutlierMinFracKeep))

    _set_if_has(alg, "ResidualFilterEnable", bool(args.gf_residualFilterEnable))
    _set_if_has(alg, "ResidualMaxPull",      float(args.gf_residualMaxPull))
    _set_if_has(alg, "ResidualMaxChi2",      float(args.gf_residualMaxChi2))

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
        print("[fitter][WARN] No callable SimpleFitDCHFitter found; falling back to ThreePointFitter.")
        return _configure_threepoint()

    alg = Simple("SimpleFitDCHFitter")
    alg.OutputLevel = DEBUG if args.fitterLog == "DEBUG" else INFO

    for prop, val in (("inputHits", ["GGTF_3DHits"]), ("input3DHits", "GGTF_3DHits")):
        if _set_if_has(alg, prop, val):
            break
    for prop, val in (("outputTracks", [args.fitOut]), ("outputTracks", args.fitOut)):
        if _set_if_has(alg, prop, val):
            break

    _set_if_has(alg, "Bz", float(args.sf_bz))
    _set_if_has(alg, "PositionUnitScale", float(args.sf_posScale))
    _set_if_has(alg, "InternalLengthToMeters", float(args.sf_len2m))
    _set_if_has(alg, "UseMaterialEffects", bool(gf_useMat_effective))
    _set_if_has(alg, "UseTGeoPath", True)
    _set_if_has(alg, "MinGroupSize",            int(args.sf_minGroup))
    _set_if_has(alg, "UseFallbackClustering",   bool(args.sf_useFallback))
    _set_if_has(alg, "FallbackEpsCM",           float(args.sf_fallbackEpsCM))
    _set_if_has(alg, "FallbackMinPts",          int(args.sf_fallbackMinPts))
    _set_if_has(alg, "SortHits",                bool(args.sf_sortHits))
    _set_if_has(alg, "DeduplicateHits",         bool(args.sf_dedup))
    _set_if_has(alg, "DedupTolMM",              float(args.sf_dedupTol))
    _set_if_has(alg, "MaxMeasPerGroup",         int(args.sf_maxMeasPerGroup))

    if args.sf_outHisto:
        _set_if_has(alg, "OutputHistoFile", args.sf_outHisto)

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

    _set_if_has(alg, "Bz", float(args.tp_bz))
    _set_if_has(alg, "PDG", int(args.gf_pdg))
    _set_if_has(alg, "PositionUnitScale", float(args.tp_posScale))
    _set_if_has(alg, "InternalLengthToMeters", float(args.tp_len2m))

    _set_if_has(alg, "UseMaterialEffects", bool(gf_useMat_effective))
    _set_if_has(alg, "UseTGeoPath", True)

    _set_if_has(alg, "MinGroupSize",            int(args.tp_minGroup))
    _set_if_has(alg, "UseFallbackClustering",   bool(args.tp_useFallback))
    _set_if_has(alg, "FallbackEpsCM",           float(args.tp_fallbackEpsCM))
    _set_if_has(alg, "FallbackMinPts",          float(args.tp_fallbackMinPts))
    _set_if_has(alg, "SortHits",                bool(args.tp_sortHits))
    _set_if_has(alg, "DeduplicateHits",         bool(args.tp_dedup))
    _set_if_has(alg, "DedupTolMM",              float(args.tp_dedupTol))
    _set_if_has(alg, "MaxMeasPerGroup",         int(args.tp_maxMeasPerGroup))

    if args.tp_outHisto:
        _set_if_has(alg, "OutputHistoFile", args.tp_outHisto)

    _set_if_has(alg, "MinDeltaPhi",      float(args.tp_minDeltaPhi))
    _set_if_has(alg, "MinChordMM",       float(args.tp_minChordMM))
    _set_if_has(alg, "MinRadiusMM",      float(args.tp_minRadiusMM))
    _set_if_has(alg, "FitTanLambda",     bool(args.tp_fitTanLambda))
    _set_if_has(alg, "PrintDiagnostics", bool(args.tp_printDiag))
    _set_if_has(alg, "DiagEveryN",       int(args.tp_diagEveryN))

    _set_if_has(alg, "JobTag", job_tag)

    print(f"[fitter] ThreePointFitter configured; output -> '{args.fitOut}'")
    return alg

fitter_alg = None
if args.stage == "fit" and requested_fitter != "none":
    if requested_fitter == "genfit2":
        fitter_alg = _configure_genfit2()
        if fitter_alg is None and args.fallbackIfNoGenFit2:
            print("[fitter][WARN] GenFit2DCHFitter unavailable; falling back to SimpleFitDCHFitter.")
            fitter_alg = _configure_simple()
        elif fitter_alg is None:
            print("[fitter][FATAL] GenFit2 requested but not available and fallback disabled.")
    elif requested_fitter == "simple":
        fitter_alg = _configure_simple()
    elif requested_fitter == "threepoint":
        fitter_alg = _configure_threepoint()

# Optional size printer
try:
    from Configurables import EDM4hepCollectionSizePrinter as SizePrinter
    size_printer = SizePrinter(
        "SizePrinter",
        CollectionsToPrint=["GGTF_3DHits", args.fitOut],
        OutputLevel=INFO,
    )
except Exception:
    size_printer = None

# ----------------- Optional looper filter wrapper -----------------
top_algs = []

def _cfg_get(name: str):
    """Best-effort: fetch a Configurable class by name from Configurables."""
    try:
        m = __import__("Configurables", fromlist=[name])
        return getattr(m, name)
    except Exception:
        return None

def _try_set_any(obj, candidates, value, label):
    """
    Try to set the first property in 'candidates' that exists on obj.
    Also tries [value] if value is a string and the property expects a vector<string>.
    Returns the property name used, or None.
    """
    for prop in candidates:
        if not hasattr(obj, prop):
            continue
        try:
            setattr(obj, prop, value)
            print(f"[looperFilter] set {prop} = {value}  ({label})")
            return prop
        except Exception as e:
            # Try list form if it might be vector<string>
            if isinstance(value, str):
                try:
                    setattr(obj, prop, [value])
                    print(f"[looperFilter] set {prop} = {[value]}  ({label}, list-fallback)")
                    return prop
                except Exception:
                    pass
            print(f"[looperFilter][WARN] failed setting {prop} ({label}): {e}")
    return None

def _dump_props(obj, prefix="[looperFilter]"):
    """Print available properties for debugging (safe)."""
    try:
        props = obj.getDefaultProperties()
        keys = sorted(list(props.keys()))
        print(f"{prefix} Available properties ({len(keys)}): {keys}")
    except Exception as e:
        print(f"{prefix} Could not read getDefaultProperties(): {e}")
        print(f"{prefix} dir() sample: {[k for k in dir(obj) if not k.startswith('_')][:80]}")

# Assemble pipeline members
reco_members = []
if args.stage in ("digi", "ggtf", "fit"):
    reco_members.append(dch_digitizer)
if args.stage in ("ggtf", "fit"):
    reco_members.append(GGTF)
if args.stage == "fit" and fitter_alg is not None:
    reco_members.append(fitter_alg)
if size_printer is not None:
    reco_members.append(size_printer)

if args.looperFilter:
    looper_coll = args.looperColl.strip() if args.looperColl.strip() else args.dchSimHits

    DCHLooperEventFilter = _cfg_get("DCHLooperEventFilter")
    if DCHLooperEventFilter is None:
        paths = os.environ.get("GAUDI_PLUGIN_PATH", "(unset)")
        raise RuntimeError(
            "[looperFilter] Enabled but could not import DCHLooperEventFilter.\n"
            "Make sure your C++ plugin is built+installed and GAUDI_PLUGIN_PATH includes it.\n"
            f"GAUDI_PLUGIN_PATH={paths}"
        )

    Sequencer = _cfg_get("GaudiSequencer") or _cfg_get("Sequencer") or _cfg_get("AthSequencer")

    looper = DCHLooperEventFilter("DCHLooperEventFilter")
    looper.OutputLevel = INFO

    input_prop_used = _try_set_any(
        looper,
        candidates=[
            "InputSimHits",
            "InputSimHitCollection",
            "InputSimHitCollections",
            "SimHitCollection",
            "SimHits",
            "InputCollection",
            "InputCollections",
            "inputHits",
            "inHits",
            "InputHits",
            "InputHitCollection",
            "InputHitCollections",
        ],
        value=looper_coll,
        label="input collection",
    )

    if input_prop_used is None:
        print(
            "[looperFilter][WARN] DCHLooperEventFilter has no recognized input-collection property "
            f"to set to '{looper_coll}'. Disabling looper filter for this run to avoid crashing."
        )
        _dump_props(looper, prefix="[looperFilter]")
        top_algs = reco_members
        print("[looperFilter] disabled (auto)")
    else:
        _try_set_any(looper, ["TmaxNs", "MaxTimeNs", "Tmax", "MaxTime"], float(args.looperTmaxNs), "Tmax cut")
        _try_set_any(looper, ["NHitsMax", "MaxNHits", "NHits", "MaxHits"], int(args.looperNHitsMax), "NHits cut")
        _try_set_any(looper, ["KeepEmpty", "KeepEmptyEvents", "PassEmpty"], bool(args.looperKeepEmpty), "KeepEmpty")

        if not args.looperPassIfMissing:
            print("[looperFilter][WARN] --no-looperPassIfMissing requested, but unless your C++ alg exposes a "
                  "PassIfMissing/FailIfMissing property, python cannot enforce it here.")

        if Sequencer is None:
            print("[looperFilter][WARN] No Sequencer/GaudiSequencer configurable found. "
                  "Running looper as first TopAlg (no sequencer).")
            top_algs = [looper] + reco_members
        else:
            seq = Sequencer("RecoSeq")
            if hasattr(seq, "IgnoreFilterPassed"):
                seq.IgnoreFilterPassed = False
            if hasattr(seq, "Members"):
                seq.Members = [looper] + reco_members
            elif hasattr(seq, "members"):
                seq.members = [looper] + reco_members
            else:
                print("[looperFilter][WARN] Sequencer has no Members attribute; falling back to flat TopAlg.")
                top_algs = [looper] + reco_members
            if not top_algs:
                top_algs = [seq]

        print(f"[looperFilter] ENABLED: coll='{looper_coll}' TmaxNs={args.looperTmaxNs} NHitsMax={args.looperNHitsMax}")

else:
    top_algs = reco_members
    print("[looperFilter] disabled")

# Wrap with Reader/Writer if available
try:
    from k4FWCore import getReader, getWriter
    reader = getReader()
    writer = getWriter()
    top_algs = [reader] + top_algs + [writer]
except Exception:
    pass

print(f"[pipeline] TopAlg order: {[alg.getFullName() for alg in top_algs]}")

# Services
# CRITICAL: create UniqueIDGenSvc with the NAME "UniqueIDGenSvc" (not "uidSvc")
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
