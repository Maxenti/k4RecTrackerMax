# dch_only_steer.py  — DCH-only DDSim steering (truth-friendly, robust)
from DDSim.DD4hepSimulation import DD4hepSimulation
from g4units import GeV

SIM = DD4hepSimulation()

# === Geometry ===
SIM.compactFile = "/eos/user/c/cglenn/FCCWork/GithubRepos/k4geoMax/FCCee/IDEA/compact/IDEA_o1_v03/IDEA_o1_v03CF_2umAu.xml"
try:
    import types
    m = getattr(SIM, "meta", None)
    if m and hasattr(m, "addParametersToRunHeader"):
        def _noop(self, dds):
            return {}  # keep it str->str, empty to be safest
        m.addParametersToRunHeader = types.MethodType(_noop, m)
except Exception as e:
    print("[steer] RunHeader metadata patch skipped:", e)
# === Run / IO ===
SIM.numberOfEvents = 1000
SIM.outputFile     = "dch_only_sim.root"
SIM.runType        = "batch"
SIM.printLevel     = 3
SIM.crossingAngleBoost = 0.0

# === Particle gun (example; tweak as you need for studies) ===
SIM.enableGun      = True
SIM.enableG4Gun    = False
SIM.enableG4GPS    = False
SIM.gun.particle   = "mu-"
SIM.gun.energy     = 10.0 * GeV
SIM.gun.isotrop    = True
SIM.gun.position   = (0.0, 0.0, 0.0)
SIM.gun.etaMax     = 2
SIM.gun.etaMin     = 0.0

# === Physics & field integration ===
SIM.physicsList     = "FTFP_BERT"
SIM.physics.rangecut = None

SIM.field.stepper            = "ClassicalRK4"
SIM.field.delta_chord        = 0.25
SIM.field.delta_intersection = 0.001
SIM.field.delta_one_step     = 0.01
SIM.field.eps_max            = 0.001
SIM.field.eps_min            = 5e-05
SIM.field.largest_step       = 10000.0
SIM.field.min_chord_step     = 0.01
SIM.field.equation           = "Mag_UsualEqRhs"
# NOTE: Field magnitude / map is taken from the compact XML. Keep it consistent
# with what you pass downstream to the fitter (Bz=2.0 T). If you ever switch to a
# different map, stamp a tag in the metadata section below.

# === Sensitive actions: TRACKER ONLY (DCH) ===
# Default tracker action: weighted (keeps step-combined positions for typical silicon)
SIM.action.tracker = (
    "Geant4TrackerWeightedAction",
    {"HitPositionCombination": 2, "CollectSingleDeposits": False},
)
SIM.action.trackerSDTypes = ["tracker"]

# For the DCH specifically, prefer the simple tracker action (no step-weighting):
SIM.action.mapActions = {}
SIM.action.mapActions["DCH_v2"] = "Geant4SimpleTrackerAction"

# NO calorimeter / DRcalo / optical
SIM.action.calo = ""
SIM.action.calorimeterSDTypes = []
SIM.geometry.regexSensitiveDetector = {}   # ensure nothing references DRcalo/optical SDs

# === Filters (be permissive in tracker, so you keep 2° effects / low-E secondaries) ===
SIM.filter.filters = {
    "edep0":    {"name": "EnergyDepositMinimumCut/Cut0", "parameter": {"Cut": 0.0}},
    "edep1kev": {"name": "EnergyDepositMinimumCut",      "parameter": {"Cut": 0.001}},
}
SIM.filter.tracker = "edep0"
SIM.filter.calo    = ""   # irrelevant here

# === Output (EDM4hep) ===
SIM.outputConfig.forceEDM4HEP = True
SIM.outputConfig.forceDD4HEP  = False
SIM.outputConfig.forceLCIO    = False
# Try enabling detailed hit content / secondaries if available in this release
try:
    SIM.outputConfig.enableDetailedHits = True
except Exception:
    pass
try:
    SIM.outputConfig.storeSecondaries = True
except Exception:
    pass
# (Most recent stacks already write SimTrackerHit -> MCParticle relations by default.)

# === MC truth handling (keep secondaries & common processes) ===
# Keeping *all* particles helps matching & occupancy studies; you can dial this back later.
SIM.part.enableDetailedHitsAndParticleInfo = True
SIM.part.keepAllParticles = True
SIM.part.minimalKineticEnergy = 0.0  # MeV
SIM.part.printEndTracking = False
SIM.part.printStartTracking = False
# Save a compact but useful set of processes for debugging material effects:
try:
    SIM.part.saveProcesses = [
        "Decay",
        "msc", "CoulombScat",        # multiple scattering & Coulomb scattering
        "eIoni", "muIoni", "hIoni",  # ionization
        "eBrem", "hBrems",           # bremsstrahlung
        "compt", "phot", "conv"      # Compton, photoelectric, gamma conversion
    ]
except Exception:
    SIM.part.saveProcesses = ["Decay"]

# === Random ===
SIM.random.enableEventSeed = True
SIM.random.replace_gRandom = True
SIM.random.luxury = 1
SIM.random.seed   = 12345

# === Reduce geometry debug noise ===
SIM.geometry.dumpGDML = ""
SIM.geometry.dumpHierarchy = 0
SIM.geometry.enableDebugElements   = False
SIM.geometry.enableDebugMaterials  = False
SIM.geometry.enableDebugPlacements = False
SIM.geometry.enablePrintPlacements = False
SIM.geometry.enablePrintSensitives = False

# === Nice-to-have metadata (if your build supports parameters on output) ===
# This is a harmless best-effort block; if unsupported, it’s ignored.
try:
    # Add run/file parameters you’ll want later in analysis
    if not hasattr(SIM, "parameters"):
        SIM.parameters = {}
    SIM.parameters.update({
        "GeometryTag": "IDEA_o1_v03CF_2umAu",
        "Detector:DCH:Name": "DCH_v2",
        "DCH_ID_Encoding": "layer:6,superlayer:4,phi:12,cell:12",
        "MagneticFieldTag": "Uniform_Bz_2T_from_compact",
        "Gun:particle": SIM.gun.particle,
        "Gun:energy_GeV": float(SIM.gun.energy/GeV),
        "Gun:isotrop": bool(SIM.gun.isotrop),
        "Gun:etaMin": float(SIM.gun.etaMin),
        "Gun:etaMax": float(SIM.gun.etaMax),
        "RunType": SIM.runType,
        "PhysicsList": SIM.physicsList,
    })
except Exception:
    pass
