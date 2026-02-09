#!/usr/bin/env python3
"""
Calculate_Aucoating_thickness.py

AC-aware conductance matching with optional Ni(P) adhesion/underplate layer (Option A: constant thickness).

Goal:
  Given a carbon-fiber (CF) core diameter/radius, compute the Au coating thickness required so that the
  *AC resistance per unit length* (R_ac/L) of:

      CF  (+ optional NiP underlayer)  +  Au

  matches the AC resistance per unit length of the reference wire:

      20 µm tungsten (W) core + 0.3 µm Au coat

AC model (engineering approximation, transparent):
  - Skin effect via effective conducting thickness:
        t_eff = min(t, k * delta)
  - Shell effective conducting area (thin-shell approx):
        A_eff_shell ≈ 2π * R_outer * t_eff
  - Core effective conducting area if fields reach it:
        A_eff_core ≈ π * min(r_core, k*delta_core)^2

Screening rule (simple, deterministic):
  - If Au is thick enough: t_Au >= k*δ_Au  -> ignore deeper layers (NiP + core).
  - Else include Au + NiP.
  - If NiP is thick enough: t_NiP >= k*δ_NiP -> ignore core.
  - Else include core as well.

Option A (what you chose):
  - Ni(P) thickness is a *constant* (continuous-film threshold + margin):
        t_NiP = --t_nip_um  (default 0.10 µm)
    enabled by --use_nip

Notes / limitations:
  - This is still a simplified AC-resistance model (ignores proximity effect, detailed impedance, roughness, etc.).
  - The relevant “frequency” is a proxy for frontend bandwidth / rise time, not bunch frequency.

Example:
  python3 Calculate_Aucoating_thickness.py --cf_d_um 25 --use_nip --t_nip_um 0.10 --f_max_GHz 2.0
"""

import argparse
import math

MU0 = 4.0e-7 * math.pi  # H/m


def skin_depth(sigma: float, f_hz: float, mu_r: float = 1.0) -> float:
    """Skin depth δ = sqrt(1 / (π f μ σ))."""
    if sigma <= 0.0 or f_hz <= 0.0:
        return float("inf")
    mu = MU0 * float(mu_r)
    return math.sqrt(1.0 / (math.pi * f_hz * mu * sigma))


def aeff_shell(r_outer: float, t: float, delta: float, k_skin: float) -> float:
    """
    Effective conducting area for a cylindrical shell near the outer surface.
    Uses t_eff = min(t, k*δ). A_eff ≈ 2π r_outer t_eff
    """
    if r_outer <= 0.0:
        return 0.0
    t = max(t, 0.0)
    if not math.isfinite(delta):
        t_eff = t
    else:
        t_eff = min(t, k_skin * delta)
    return 2.0 * math.pi * r_outer * t_eff


def aeff_core_disk(r_core: float, delta: float, k_skin: float) -> float:
    """
    Effective conducting area for a solid core if fields reach it.
    Conservative: disk of radius min(r_core, k*δ).
    """
    if r_core <= 0.0:
        return 0.0
    if not math.isfinite(delta):
        r_eff = r_core
    else:
        r_eff = min(r_core, k_skin * delta)
    return math.pi * r_eff * r_eff


def rac_over_l_wire_3layer(
    r_core: float,          # meters
    t_nip: float,           # meters (0 if none)
    t_au: float,            # meters
    sigma_core: float,      # S/m
    sigma_nip: float,       # S/m
    sigma_au: float,        # S/m
    delta_core: float,      # meters
    delta_nip: float,       # meters
    delta_au: float,        # meters
    k_skin: float,
) -> float:
    """
    AC resistance per unit length for core + NiP + Au.

    Radii:
      r_nip_outer = r_core + t_nip
      r_au_outer  = r_core + t_nip + t_au

    Screening:
      - If t_au  >= k*δ_au  -> only Au
      - Else include Au + NiP
      - If t_nip >= k*δ_nip -> ignore core
      - Else include core too
    """
    t_nip = max(t_nip, 0.0)
    t_au = max(t_au, 0.0)

    r_nip_outer = r_core + t_nip
    r_au_outer = r_core + t_nip + t_au

    # Au (outermost)
    A_au = aeff_shell(r_outer=r_au_outer, t=t_au, delta=delta_au, k_skin=k_skin)
    G_au = (sigma_au * A_au) if (sigma_au > 0.0 and A_au > 0.0) else 0.0

    # If Au screens everything below
    au_screens = (t_au >= k_skin * delta_au) if math.isfinite(delta_au) else False
    if au_screens:
        return float("inf") if G_au <= 0.0 else (1.0 / G_au)

    # NiP (middle)
    G_nip = 0.0
    if t_nip > 0.0 and sigma_nip > 0.0:
        A_nip = aeff_shell(r_outer=r_nip_outer, t=t_nip, delta=delta_nip, k_skin=k_skin)
        G_nip = sigma_nip * A_nip

    # If NiP screens core
    nip_screens = (t_nip >= k_skin * delta_nip) if (t_nip > 0.0 and math.isfinite(delta_nip)) else False

    # Core
    G_core = 0.0
    if (not nip_screens) and sigma_core > 0.0:
        A_core = aeff_core_disk(r_core=r_core, delta=delta_core, k_skin=k_skin)
        G_core = sigma_core * A_core

    G_tot = G_au + G_nip + G_core
    return float("inf") if G_tot <= 0.0 else (1.0 / G_tot)


def solve_required_au_thickness_ac(
    cf_radius_m: float,
    t_nip_m: float,
    sigma_cf: float,
    sigma_nip: float,
    # reference wire:
    w_core_radius_m: float,
    au_ref_thickness_m: float,
    sigma_w: float,
    sigma_au: float,
    # frequency model
    f_max_hz: float,
    k_skin: float,
    # permeabilities
    mu_r_au: float = 1.0,
    mu_r_w: float = 1.0,
    mu_r_cf: float = 1.0,
    mu_r_nip: float = 1.0,
    # solver controls
    tmax_factor: float = 50.0,
    rtol: float = 1e-10,
) -> dict:
    """
    Solve for Au thickness on CF core such that:
      (R/L)_CF(+NiP)+Au(f_max) = (R/L)_W+Au_ref(f_max)
    via bracketed bisection.
    """
    # Skin depths
    d_au  = skin_depth(sigma_au,  f_max_hz, mu_r=mu_r_au)
    d_w   = skin_depth(sigma_w,   f_max_hz, mu_r=mu_r_w)
    d_cf  = skin_depth(sigma_cf,  f_max_hz, mu_r=mu_r_cf)  if sigma_cf  > 0 else float("inf")
    d_nip = skin_depth(sigma_nip, f_max_hz, mu_r=mu_r_nip) if (t_nip_m > 0 and sigma_nip > 0) else float("inf")

    # Reference R/L (W + Au only; no NiP)
    Rref = rac_over_l_wire_3layer(
        r_core=w_core_radius_m,
        t_nip=0.0,
        t_au=au_ref_thickness_m,
        sigma_core=sigma_w,
        sigma_nip=0.0,
        sigma_au=sigma_au,
        delta_core=d_w,
        delta_nip=float("inf"),
        delta_au=d_au,
        k_skin=k_skin,
    )
    if not math.isfinite(Rref) or Rref <= 0.0:
        raise ValueError("Reference R/L is non-finite or non-positive; check inputs.")

    # Root function
    def f(t_au_m: float) -> float:
        return rac_over_l_wire_3layer(
            r_core=cf_radius_m,
            t_nip=t_nip_m,
            t_au=t_au_m,
            sigma_core=sigma_cf,
            sigma_nip=sigma_nip,
            sigma_au=sigma_au,
            delta_core=d_cf,
            delta_nip=d_nip,
            delta_au=d_au,
            k_skin=k_skin,
        ) - Rref

    # Bracket
    t_lo = 0.0
    f_lo = f(t_lo)

    # If already more conductive than reference at t_Au=0, no solution by adding Au (would only reduce R)
    if f_lo < 0.0:
        raise ValueError(
            "No physical solution: CF(+NiP) with t_Au=0 already has lower AC resistance/length than the reference.\n"
            "That implies it is already more conductive than (W 20µm + Au 0.3µm) under this AC model."
        )

    t_hi = max(
        tmax_factor * au_ref_thickness_m,
        10.0 * d_au if math.isfinite(d_au) else tmax_factor * au_ref_thickness_m,
    )
    f_hi = f(t_hi)
    if f_hi > 0.0:
        raise ValueError(
            "No physical solution within search range: even very thick Au does not reach the reference AC resistance.\n"
            "Try increasing CF radius, reducing f_max, increasing sigma_cf, or increasing tmax_factor."
        )

    # Bisection
    for _ in range(250):
        t_mid = 0.5 * (t_lo + t_hi)
        f_mid = f(t_mid)

        if abs(f_mid) <= max(abs(Rref) * 1e-12, 1e-18):
            t_lo = t_hi = t_mid
            break

        if f_mid > 0.0:
            t_lo, f_lo = t_mid, f_mid
        else:
            t_hi, f_hi = t_mid, f_mid

        if (t_hi - t_lo) <= max(rtol * max(1.0, t_hi), 1e-18):
            break

    t_sol = 0.5 * (t_lo + t_hi)
    r_total = cf_radius_m + t_nip_m + t_sol

    Rsol = rac_over_l_wire_3layer(
        r_core=cf_radius_m,
        t_nip=t_nip_m,
        t_au=t_sol,
        sigma_core=sigma_cf,
        sigma_nip=sigma_nip,
        sigma_au=sigma_au,
        delta_core=d_cf,
        delta_nip=d_nip,
        delta_au=d_au,
        k_skin=k_skin,
    )

    t_dim_au = (k_skin * d_au) if math.isfinite(d_au) else float("inf")
    diminishing = (t_sol >= t_dim_au) if math.isfinite(t_dim_au) else False

    return {
        "f_max_hz": f_max_hz,
        "k_skin": k_skin,
        "t_nip_m": t_nip_m,
        "delta_au_m": d_au,
        "delta_w_m": d_w,
        "delta_cf_m": d_cf,
        "delta_nip_m": d_nip,
        "Rref_ohm_per_m": Rref,
        "Rsol_ohm_per_m": Rsol,
        "t_au_m": t_sol,
        "r_total_m": r_total,
        "t_dim_au_m": t_dim_au,
        "diminishing_returns": diminishing,
    }


def main():
    ap = argparse.ArgumentParser()

    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--cf_d_um", type=float, help="Carbon fiber core diameter [µm]")
    g.add_argument("--cf_r_um", type=float, help="Carbon fiber core radius [µm]")

    # Conductivities (S/m)
    ap.add_argument("--sigma_au",  type=float, default=4.10e7, help="Gold conductivity [S/m] (default 4.10e7)")
    ap.add_argument("--sigma_w",   type=float, default=1.79e7, help="Tungsten conductivity [S/m] (default 1.79e7)")
    ap.add_argument("--sigma_cf",  type=float, default=4.00e4, help="Carbon fiber conductivity [S/m] (default 4.00e4; use 0 for none)")
    ap.add_argument("--sigma_nip", type=float, default=1.5e6,  help="Ni(P) conductivity [S/m] (default 1.5e6)")

    # Reference geometry
    ap.add_argument("--w_d_um",      type=float, default=20.0, help="Reference W core diameter [µm] (default 20)")
    ap.add_argument("--au_ref_t_um", type=float, default=0.3,  help="Reference Au thickness [µm] (default 0.3)")

    # AC model controls
    ap.add_argument("--f_max_GHz", type=float, default=2.0, help="Max frequency for skin depth [GHz] (default 2.0)")
    ap.add_argument("--k_skin",    type=float, default=3.0, help="Effective conducting depth in units of skin depth (default 3.0)")

    ap.add_argument("--mu_r_au",  type=float, default=1.0, help="Relative permeability Au (default 1.0)")
    ap.add_argument("--mu_r_w",   type=float, default=1.0, help="Relative permeability W (default 1.0)")
    ap.add_argument("--mu_r_cf",  type=float, default=1.0, help="Relative permeability CF (default 1.0)")
    ap.add_argument("--mu_r_nip", type=float, default=1.0, help="Relative permeability Ni(P) (default 1.0)")

    # Option A: constant Ni(P) layer
    ap.add_argument("--use_nip", action="store_true", help="Include a Ni(P) adhesion/underplate layer under Au")
    ap.add_argument("--t_nip_um", type=float, default=0.10, help="Ni(P) thickness [µm] (Option A constant film, default 0.10)")

    # Solver range
    ap.add_argument("--tmax_factor", type=float, default=50.0,
                    help="Search upper bound as factor * au_ref_thickness (plus 10*delta safeguard) (default 50)")

    args = ap.parse_args()

    um = 1e-6

    # CF geometry
    if args.cf_r_um is not None:
        cf_r_m = args.cf_r_um * um
        cf_d_um = 2.0 * args.cf_r_um
    else:
        cf_r_m = 0.5 * args.cf_d_um * um
        cf_d_um = args.cf_d_um

    # Reference geometry
    w_r_m = 0.5 * args.w_d_um * um
    au_ref_t_m = args.au_ref_t_um * um

    # Frequency
    f_max_hz = float(args.f_max_GHz) * 1e9

    # Option A NiP thickness
    t_nip_m = (max(args.t_nip_um, 0.0) * um) if args.use_nip else 0.0

    out = solve_required_au_thickness_ac(
        cf_radius_m=cf_r_m,
        t_nip_m=t_nip_m,
        sigma_cf=float(args.sigma_cf),
        sigma_nip=float(args.sigma_nip) if args.use_nip else 0.0,
        w_core_radius_m=w_r_m,
        au_ref_thickness_m=au_ref_t_m,
        sigma_w=float(args.sigma_w),
        sigma_au=float(args.sigma_au),
        f_max_hz=f_max_hz,
        k_skin=float(args.k_skin),
        mu_r_au=float(args.mu_r_au),
        mu_r_w=float(args.mu_r_w),
        mu_r_cf=float(args.mu_r_cf),
        mu_r_nip=float(args.mu_r_nip),
        tmax_factor=float(args.tmax_factor),
    )

    # Unit conversions for printing
    r_total_um = out["r_total_m"] / um
    t_au_um = out["t_au_m"] / um
    t_nip_um = out["t_nip_m"] / um
    r_cf_um = cf_r_m / um
    r_ref_total_um = (w_r_m + au_ref_t_m) / um

    d_au_um  = out["delta_au_m"]  / um if math.isfinite(out["delta_au_m"])  else float("inf")
    d_w_um   = out["delta_w_m"]   / um if math.isfinite(out["delta_w_m"])   else float("inf")
    d_cf_um  = out["delta_cf_m"]  / um if math.isfinite(out["delta_cf_m"])  else float("inf")
    d_nip_um = out["delta_nip_m"] / um if math.isfinite(out["delta_nip_m"]) else float("inf")
    t_dim_au_um = out["t_dim_au_m"] / um if math.isfinite(out["t_dim_au_m"]) else float("inf")

    print("=== Match AC resistance/length: CF(+NiP)+Au to (W 20µm + Au 0.3µm) ===")
    print(f"Input CF core diameter: {cf_d_um:.6g} µm  (radius {r_cf_um:.6g} µm)")
    print(f"AC max frequency: {args.f_max_GHz:.6g} GHz")
    print(f"k_skin (effective depth): {args.k_skin:.6g} × δ")
    print("")

    print("Reference wire:")
    print(f"  W core diameter: {args.w_d_um:.6g} µm (radius {args.w_d_um/2:.6g} µm)")
    print(f"  Au thickness:    {args.au_ref_t_um:.6g} µm")
    print(f"  Total radius:    {r_ref_total_um:.6g} µm")
    print(f"  Target R_ac/L:   {out['Rref_ohm_per_m']:.6g} Ω/m")
    print("")

    if args.use_nip:
        print("Ni(P) underlayer (Option A):")
        print(f"  t_NiP:           {t_nip_um:.6g} µm (constant)")
        print(f"  sigma_NiP:       {args.sigma_nip:.6g} S/m")
        print("")
    else:
        print("Ni(P) underlayer: disabled")
        print("")

    print("Skin depths at f_max:")
    print(f"  δ_Au  = {d_au_um:.6g} µm")
    print(f"  δ_W   = {d_w_um:.6g} µm")
    if args.use_nip:
        print(f"  δ_NiP = {d_nip_um:.6g} µm")
    if args.sigma_cf > 0:
        print(f"  δ_CF  = {d_cf_um:.6g} µm")
    else:
        print("  δ_CF  = inf (sigma_cf=0)")
    print("")

    print("Solved CF(+NiP)+Au wire (AC model):")
    if args.use_nip:
        print(f"  NiP thickness:        {t_nip_um:.6g} µm")
    print(f"  Required Au thickness: {t_au_um:.6g} µm")
    print(f"  Required total radius: {r_total_um:.6g} µm")
    print(f"  Achieved R_ac/L:       {out['Rsol_ohm_per_m']:.6g} Ω/m")
    rel = (out["Rsol_ohm_per_m"] - out["Rref_ohm_per_m"]) / out["Rref_ohm_per_m"]
    print(f"  Relative diff (should be ~0): {rel:.3e}")
    print("")

    print("Diminishing-returns check (Au):")
    print(f"  Threshold ~ k_skin*δ_Au = {t_dim_au_um:.6g} µm")
    if out["diminishing_returns"]:
        print(f"[warn] Required Au thickness ({t_au_um:.6g} µm) is >= k_skin*δ_Au ({t_dim_au_um:.6g} µm).")
        print("       Past this point, extra Au thickness contributes little to AC conductance.")
        print("       If you still need more conductivity, increasing outer radius (larger CF core) helps more than thicker Au.")
    else:
        print("[ok] Required Au thickness is below the diminishing-returns threshold.")

    if math.isfinite(d_au_um) and d_au_um > 0:
        if t_au_um < 0.2 * d_au_um:
            print("[note] Au thickness is << δ_Au: current is closer to uniform across Au thickness (DC-like).")
        elif t_au_um > 5.0 * d_au_um:
            print("[note] Au thickness is >> δ_Au: strong skin regime; Au dominates and inner layers are largely screened.")


if __name__ == "__main__":
    main()
