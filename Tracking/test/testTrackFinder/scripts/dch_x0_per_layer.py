#!/usr/bin/env python3
"""
DOC
Summary: Compute an effective IDEA DCH radiation length for Delphes TrackCovariance cards from gas, field/guard wires, and configurable W-or-CF sense-wire material assumptions.
Status: secondary
Usage:
  python3 scripts/dch_x0_per_layer.py --sense-core CF --sense-d-um 25 --au-um 1.4 --ag-um 0.3
  python3 scripts/dch_x0_per_layer.py --sense-core W --sense-d-um 25 --au-um 0.3 --ag-um 0.3 --print-layers 112
Examples:
  python3 scripts/dch_x0_per_layer.py \
    --sense-core CF \
    --sense-d-um 25 \
    --au-um 1.4 \
    --ag-um 0.3 \
    --print-layers 112
  Expected result: prints X0_meters plus an optional repeated per-layer X0 list suitable for copying into a Delphes DetectorGeometry-style table.
Inputs: DCH radial bounds, He/isobutane gas fractions, total field/guard/sense wire counts, field/guard wire diameters, Ag coating thickness, sense-wire core material/diameter, and Au coating thickness.
Outputs: Printed effective radiation length in meters, mixture X0 in g/cm^2, average density, per-component mass fractions, and optional identical per-layer X0 values.
Collections: None; this is a standalone material-parameter utility, not an EDM4hep/ROOT event processor.
Connects-To: configs/delphes/*.tcl, scripts/Calculate_Aucoating_thickness.py, scripts/patch_trkCov_match_dch_material.py, material-budget closeout studies, CF-vs-W wire-variant studies
Arguments:
  --rin-cm: inner radius of the DCH active annulus in cm; default 35.0.
  --rout-cm: outer radius of the DCH active annulus in cm; default 200.0.
  --f-he: helium volume fraction in the gas mixture; default 0.9.
  --f-iso: isobutane volume fraction in the gas mixture; default 0.1.
  --n-field: total number of field wires included in the effective DCH mixture; default 229056.
  --n-guard: total number of guard wires included in the effective DCH mixture; default 58464.
  --n-sense: total number of sense wires included in the effective DCH mixture; default 56448.
  --field-d-um: field-wire Al core diameter in micrometers; default 40.0.
  --guard-d-um: guard-wire Al core diameter in micrometers; default 50.0.
  --sense-core: sense-wire core material; allowed values are W and CF; default CF.
  --sense-d-um: sense-wire core diameter in micrometers; default 25.0.
  --ag-um: Ag coating thickness on Al field/guard wires in micrometers; default 0.3.
  --au-um: Au coating thickness on sense wires in micrometers; default 1.4.
  --no-displacement: do not subtract wire volume from gas volume before computing gas mass.
  --print-layers: if greater than zero, print that many identical X0_meters lines for layer-table insertion.
Notes:
  The calculation follows a spreadsheet-style effective-mixture model: compute mass per cm, form mass fractions, combine material radiation lengths in g/cm^2 with 1/X0 = sum_i w_i/X0_i, compute average density, then convert X0 to a length in meters.
  The result is a fastsim/Delphes parameterization value, not a replacement for full DD4hep/Geant4 material-budget scans.
  The current model uses total wire counts integrated over the full DCH and therefore prints the same X0 value for every layer.
  If reliable per-layer wire counts become available, this script should be extended to compute radius- or layer-dependent X0 instead of repeating one global value.
  Keep gas fractions, wire counts, and coating assumptions synchronized with the detector/material variant being studied before using the output in CF-vs-W comparisons.
  The optional wire-volume displacement correction is small but enabled by default for consistency with the effective-density calculation.
Tags: secondary, material-budget, delphes, track-covariance, dch, radiation-length, x0, carbon-fiber, tungsten, wire-materials
DOC_END
"""

import argparse, math

# --- Material properties (density in g/cm^3, X0 in g/cm^2) ---
# Values are standard and sufficient for this fastsim parameterization.
MATERIAL = {
    "He":  {"rho": 1.66e-4, "X0": 94.32},
    "Iso": {"rho": 2.67e-3, "X0": 45.07},   # isobutane
    "Al":  {"rho": 2.699,   "X0": 24.01},
    "W":   {"rho": 19.3,    "X0": 6.76},
    "CF":  {"rho": 1.90,    "X0": 42.7},
    "Ag":  {"rho": 10.49,   "X0": 9.69},
    "Au":  {"rho": 19.32,   "X0": 6.46},
}

def um_to_cm(x_um: float) -> float:
    return x_um * 1.0e-4

def split_wire_masses_g_per_cm(d_core_um: float, core_mat: str, coats):
    """
    Returns:
      masses: dict(mat -> g/cm) for a single wire (1 cm long)
      r_out:  outer radius (cm) after all coatings
    """
    r_core_cm = um_to_cm(d_core_um) / 2.0
    masses = {}

    # core
    masses[core_mat] = math.pi * (r_core_cm**2) * MATERIAL[core_mat]["rho"]

    # coatings (each layer adds annulus mass)
    r_in = r_core_cm
    for (t_um, mat) in coats:
        t_cm = um_to_cm(t_um)
        r_out = r_in + t_cm
        masses[mat] = masses.get(mat, 0.0) + math.pi * (r_out**2 - r_in**2) * MATERIAL[mat]["rho"]
        r_in = r_out

    return masses, r_in

def compute_x0_length_m(args):
    # Geometry / gas volume per 1 cm slice
    area_cm2 = math.pi * (args.rout_cm**2 - args.rin_cm**2)

    # Wires: field + guard + sense
    field_masses, r_field = split_wire_masses_g_per_cm(args.field_d_um, "Al", [(args.ag_um, "Ag")] if args.ag_um > 0 else [])
    guard_masses, r_guard = split_wire_masses_g_per_cm(args.guard_d_um, "Al", [(args.ag_um, "Ag")] if args.ag_um > 0 else [])
    sense_masses, r_sense = split_wire_masses_g_per_cm(args.sense_d_um, args.sense_core, [(args.au_um, "Au")] if args.au_um > 0 else [])

    # Displaced volume (optional)
    vol_wires_cm3 = (
        args.n_field * math.pi * (r_field**2) +
        args.n_guard * math.pi * (r_guard**2) +
        args.n_sense * math.pi * (r_sense**2)
    ) * 1.0  # 1 cm slice length

    vol_gas_cm3 = area_cm2 * 1.0
    if args.displacement:
        vol_gas_cm3 = max(vol_gas_cm3 - vol_wires_cm3, 0.0)

    # Total masses per cm by material
    masses = {}

    def add_scaled(mdict, scale):
        for k, v in mdict.items():
            masses[k] = masses.get(k, 0.0) + scale * v

    add_scaled(field_masses, args.n_field)
    add_scaled(guard_masses, args.n_guard)
    add_scaled(sense_masses, args.n_sense)

    # gas (He/Iso volume fractions)
    masses["He"]  = masses.get("He", 0.0)  + vol_gas_cm3 * MATERIAL["He"]["rho"]  * args.f_he
    masses["Iso"] = masses.get("Iso", 0.0) + vol_gas_cm3 * MATERIAL["Iso"]["rho"] * args.f_iso

    # Total mass per cm
    m_tot = sum(masses.values())
    if m_tot <= 0:
        raise RuntimeError("Total mass is zero; check inputs.")

    # Mass fractions
    w = {k: v / m_tot for k, v in masses.items()}

    # Mixture X0 in g/cm^2: 1/X0 = sum w_i / X0_i
    inv_x0 = 0.0
    for k, wk in w.items():
        inv_x0 += wk / MATERIAL[k]["X0"]
    x0_gcm2 = 1.0 / inv_x0

    # Average density in g/cm^3: (g/cm) / (cm^2)
    rho_avg = m_tot / area_cm2

    # Radiation length as a length (cm), then meters
    x0_cm = x0_gcm2 / rho_avg
    x0_m  = x0_cm / 100.0

    return x0_m, x0_gcm2, rho_avg, masses, w

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rin-cm",  type=float, default=35.0)
    ap.add_argument("--rout-cm", type=float, default=200.0)
    ap.add_argument("--f-he",  type=float, default=0.9)
    ap.add_argument("--f-iso", type=float, default=0.1)

    ap.add_argument("--n-field", type=int, default=229056)
    ap.add_argument("--n-guard", type=int, default=58464)
    ap.add_argument("--n-sense", type=int, default=56448)

    ap.add_argument("--field-d-um", type=float, default=40.0)
    ap.add_argument("--guard-d-um", type=float, default=50.0)

    ap.add_argument("--sense-core", choices=["W", "CF"], default="CF")
    ap.add_argument("--sense-d-um", type=float, default=25.0)

    ap.add_argument("--ag-um", type=float, default=0.3, help="Ag coating thickness on Al field/guard (µm)")
    ap.add_argument("--au-um", type=float, default=1.4, help="Au coating thickness on sense wires (µm)")

    ap.add_argument("--no-displacement", dest="displacement", action="store_false",
                    help="Do NOT subtract wire volume from gas volume (tiny effect).")
    ap.set_defaults(displacement=True)

    ap.add_argument("--print-layers", type=int, default=0,
                    help="If >0, print that many identical per-layer X0 numbers (meters).")

    args = ap.parse_args()

    x0_m, x0_gcm2, rho_avg, masses, w = compute_x0_length_m(args)

    print("=== DCH effective radiation length (for Delphes DetectorGeometry X0 column) ===")
    print(f"sense_core={args.sense_core}  sense_d_um={args.sense_d_um:.3f}  au_um={args.au_um:.3f}  ag_um={args.ag_um:.3f}")
    print(f"rin_cm={args.rin_cm:.3f}  rout_cm={args.rout_cm:.3f}  f_he={args.f_he:.3f}  f_iso={args.f_iso:.3f}")
    print(f"wire_displacement={'ON' if args.displacement else 'OFF'}")
    print()
    print(f"X0_meters = {x0_m:.6g}")
    print(f"(debug) X0_gcm2={x0_gcm2:.6g}   rho_avg_gcm3={rho_avg:.6g}")
    print()

    print("Mass per cm slice (g/cm) by component:")
    for k in sorted(masses.keys()):
        print(f"  {k:>3s}: {masses[k]:.6g}   (w={w[k]*100:.3f}%)")

    if args.print_layers and args.print_layers > 0:
        print()
        print(f"Per-layer X0 list (meters), N={args.print_layers}:")
        for i in range(args.print_layers):
            print(f"{i:03d}  {x0_m:.6g}")

if __name__ == "__main__":
    main()
