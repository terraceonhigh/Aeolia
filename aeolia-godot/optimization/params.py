"""
Parameter space definition for Aeolia history engine optimization.

Each parameter has:
  - A default value matching the current GDScript implementation
  - A search bound (lo, hi) for the optimizer
  - A scale hint ("linear" | "log") for sampling

Organised by the era in which the parameter has effect.  Comments link
each entry to the lore constraint it controls and the HISTORY_ENGINE_ANALYSIS
section that documents the recommended change.

Usage
-----
    from params import PARAM_SPACE, DEFAULT_PARAMS, suggest_params, array_to_params

    # Optuna trial
    import optuna
    def objective(trial):
        params = suggest_params(trial)
        result = simulate(base_world, params)
        total, _ = compute_loss(result).total
        return total

    # Scipy (normalized array interface)
    from scipy.optimize import differential_evolution
    names, bounds = zip(*[(k, (lo, hi)) for k, (lo, hi, _) in PARAM_SPACE.items()])
    def f(x):
        params = array_to_params(x, list(names))
        ...
"""

from __future__ import annotations
from thin_sim import DEFAULT_PARAMS

# ---------------------------------------------------------------------------
# Parameter space
# Each entry: param_name → (lo, hi, scale)
# scale = "linear" | "log"  (hint to Optuna suggest_float)
# ---------------------------------------------------------------------------

PARAM_SPACE: dict[str, tuple] = {

    # ── Phase 3: Status assignment ─────────────────────────────────────────
    # Hop limits: increasing reach_colony_hop_limit → more colonies,
    # decreasing → fewer colonies, more contacts.
    # HISTORY_ENGINE_ANALYSIS §11: initial values are reasonable starting points
    # but should drift per-tick (not implemented yet — these are static assignments).
    "reach_colony_hop_limit":        (2,    4,    "linear"),
    "reach_client_hop_limit":        (4,    7,    "linear"),
    "lattice_garrison_hop_limit":    (2,    4,    "linear"),
    "lattice_tributary_hop_limit":   (4,    7,    "linear"),

    # Initial sovereignty: controls where in the 2D sovereignty-trade space
    # an arch starts.  Lower colony sovereignty → more extractive relationship.
    "reach_colony_sovereignty":      (0.05, 0.30, "linear"),
    "reach_colony_trade":            (0.65, 0.95, "linear"),
    "reach_client_sovereignty":      (0.40, 0.70, "linear"),
    "reach_client_trade":            (0.45, 0.75, "linear"),
    "lattice_garrison_sovereignty":  (0.15, 0.45, "linear"),
    "lattice_garrison_trade":        (0.30, 0.65, "linear"),
    "lattice_tributary_sovereignty": (0.45, 0.75, "linear"),
    "lattice_tributary_trade":       (0.25, 0.55, "linear"),

    # ── Era 1: Antiquity ───────────────────────────────────────────────────
    # HISTORY_ENGINE_ANALYSIS §2: current 0.002 produces only 3–6% differentiation
    # over 15,000 years.  Recommended range 0.003–0.009 (analysis §2 formula).
    # Raising this is the single highest-leverage antiquity improvement.
    "antiquity_growth_rate":         (0.001, 0.010, "log"),
    "antiquity_periods":             (20,    45,    "linear"),

    # Lattice paddi advantage: DESIGN_SPEC §10a paddi 5.0 t/ha vs emmer 2.5.
    # Current 2.5× is mechanically correct; the optimiser confirms whether the
    # FULL pop ratio target [1.2, 2.2] requires a different multiplier.
    "lattice_antiquity_pop_mult":    (1.5,   4.0,  "linear"),

    "tech_init_low":                 (1.5,   3.5,  "linear"),
    "reach_tech_floor":              (2.5,   4.5,  "linear"),
    "lattice_tech_floor":            (3.0,   5.0,  "linear"),

    # ── Era 2: Serial contact ──────────────────────────────────────────────
    # Epidemiological shock parameters.
    # HISTORY_ENGINE_ANALYSIS §3: highest-priority misalignment.
    # base_severity is scaled by crop_distance [0.2, 1.0].
    # Historical calibration: same-crop ~4-9% mortality, max-distance ~20-45%.
    "shock_base_min":                (0.05,  0.35, "linear"),
    "shock_base_range":              (0.05,  0.40, "linear"),

    # Trade recovery: too high → contacts recover too fast,
    # erasing the epidemic depression.
    "trade_recovery_rate":           (0.0001, 0.0012, "log"),

    # Reach network effect (HISTORY_ENGINE_ANALYSIS §5 — corrected coefficients).
    # Reach A₀=1.2, δ=0.08: should have HIGHER log₂ coefficient than Lattice.
    # Current (1.3, 0.30) is the corrected version.
    "reach_serial_pop_base":         (0.9,   2.0,  "linear"),
    "reach_serial_log_coeff":        (0.10,  0.55, "linear"),
    "reach_serial_tech_bonus":       (0.6,   2.0,  "linear"),

    # Lattice stable surplus: large base, low scaling.
    # DESIGN_SPEC §5: "Agricultural surplus is large but constant."
    "lattice_serial_pop_base":       (1.2,   3.0,  "linear"),
    "lattice_serial_log_coeff":      (0.04,  0.25, "linear"),
    "lattice_serial_tech_bonus":     (0.5,   1.5,  "linear"),

    # ── Era 3: Colonial empires ─────────────────────────────────────────────
    "extraction_base_rate":          (0.05,  0.25, "linear"),
    "extraction_growth_per_year":    (0.00002, 0.00025, "log"),
    "garrison_absorption_min":       (0.05,  0.30, "linear"),
    "garrison_absorption_range":     (0.03,  0.15, "linear"),
    "tributary_tribute_min":         (0.02,  0.12, "linear"),
    "reach_colonies_pop_coeff":      (0.05,  0.25, "linear"),
    "extracted_transit_eff":         (0.30,  0.85, "linear"),
    "lattice_garrisons_pop_coeff":   (0.05,  0.30, "linear"),
    "lattice_tribs_pop_coeff":       (0.02,  0.15, "linear"),

    # ── Era 4: Industrial ───────────────────────────────────────────────────
    # HISTORY_ENGINE_ANALYSIS §8: corrected Solow-Romer differentials.
    # Reach A₀=1.2, δ=0.08 → higher tech leverage (reach_ind_tech_coeff)
    # Lattice A₀=0.8, β=0.6 → higher resource leverage (lattice_ind_resource_coeff)
    "reach_ind_tech_coeff":          (0.05,  0.22, "linear"),
    "reach_ind_resource_coeff":      (0.05,  0.25, "linear"),
    "reach_ind_log_coeff":           (0.05,  0.25, "linear"),
    "reach_ind_tech_growth":         (0.4,   1.5,  "linear"),

    "lattice_ind_tech_coeff":        (0.02,  0.12, "linear"),
    "lattice_ind_resource_coeff":    (0.10,  0.35, "linear"),
    "lattice_ind_log_coeff":         (0.04,  0.18, "linear"),
    "lattice_ind_tech_growth":       (0.3,   1.0,  "linear"),

    # Free/independent contacts — raising free_tech_growth is the lever for
    # producing the 3-5 independent powers required by DESIGN_SPEC §0.
    "free_tech_coeff":               (0.04,  0.16, "linear"),
    "free_resource_coeff":           (0.06,  0.22, "linear"),
    "free_tech_growth":              (0.3,   1.2,  "linear"),

    # Colony tech: should be suppressed vs free contacts (stagnation era).
    "colony_tech_coeff":             (0.01,  0.07, "linear"),
    "colony_resource_coeff":         (0.02,  0.10, "linear"),
    "colony_tech_growth":            (0.1,   0.6,  "linear"),

    # Industrial tech floors.
    # HISTORY_ENGINE_ANALYSIS §9: hard floors prevent seed variance.
    # Raising the lower bound on reach_ind_tech_floor raises the Reach's
    # guaranteed industrial competence; lowering it allows marginal Reach seeds.
    "reach_ind_tech_floor":          (5.0,   8.0,  "linear"),
    "lattice_ind_tech_floor":        (4.5,   7.5,  "linear"),

    # ── Era 4→5 sovereignty drift ──────────────────────────────────────────
    "colony_sov_drift_coeff":        (0.1,   0.6,  "linear"),
    "client_sov_drift_rate":         (0.00001, 0.0002, "log"),

    # ── Era 5: Nuclear ─────────────────────────────────────────────────────
    "reach_nuclear_pop_mult":        (1.1,   2.0,  "linear"),
    "lattice_nuclear_pop_mult":      (1.05,  1.8,  "linear"),

    "nuclear_access_colony":         (0.4,   0.9,  "linear"),
    "nuclear_access_garrison":       (0.2,   0.7,  "linear"),
    "nuclear_access_contact":        (0.1,   0.5,  "linear"),
    "green_revolution_prob":         (0.15,  0.70, "linear"),
    "green_revolution_mult_min":     (1.1,   1.8,  "linear"),
    "nuclear_pop_coeff":             (0.05,  0.40, "linear"),

    # ── Post-nuclear sovereignty recovery ──────────────────────────────────
    "colony_nuclear_sov_recovery":   (0.15,  0.60, "linear"),
    "colony_nuclear_trade_decay":    (0.60,  0.98, "linear"),
    "garrison_nuclear_sov_recovery": (0.05,  0.40, "linear"),
}

# Convenience: integer params (hop limits, periods) that need int casting
_INT_PARAMS = {
    "reach_colony_hop_limit", "reach_client_hop_limit",
    "lattice_garrison_hop_limit", "lattice_tributary_hop_limit",
    "antiquity_periods",
}


# ---------------------------------------------------------------------------
# Helpers for optimization frameworks
# ---------------------------------------------------------------------------

def suggest_params(trial) -> dict:
    """
    Suggest a parameter dict from an Optuna trial.

    Usage:
        import optuna
        def objective(trial):
            p = suggest_params(trial)
            result = simulate(base_world, p)
            return compute_loss(result).total

        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=300)
    """
    p = dict(DEFAULT_PARAMS)  # start from defaults so unlisted params stay valid
    for name, (lo, hi, scale) in PARAM_SPACE.items():
        if scale == "log":
            val = trial.suggest_float(name, lo, hi, log=True)
        else:
            if name in _INT_PARAMS:
                val = trial.suggest_int(name, int(lo), int(hi))
            else:
                val = trial.suggest_float(name, lo, hi)
        p[name] = val
    return p


def array_to_params(x, names: list[str]) -> dict:
    """
    Convert a flat array (for scipy.optimize) to a params dict.

    ``names`` and ``x`` must be parallel.  Values are back-transformed
    from the unit cube [0,1] to their natural range using PARAM_SPACE bounds.

    Usage:
        names = list(PARAM_SPACE.keys())
        bounds = [(0, 1)] * len(names)   # unit cube
        def f(x):
            return compute_loss(simulate(bw, array_to_params(x, names))).total
        result = differential_evolution(f, bounds, maxiter=1000)
    """
    import math as _math
    p = dict(DEFAULT_PARAMS)
    for name, xi in zip(names, x):
        lo, hi, scale = PARAM_SPACE[name]
        if scale == "log":
            val = _math.exp(_math.log(lo) + xi * (_math.log(hi) - _math.log(lo)))
        else:
            val = lo + xi * (hi - lo)
        if name in _INT_PARAMS:
            val = int(round(val))
        p[name] = val
    return p


def params_to_array(params: dict, names: list[str]) -> list[float]:
    """
    Inverse of array_to_params — map a params dict back to unit-cube floats.
    Useful for warm-starting an optimizer from a known-good param set.
    """
    import math as _math
    result = []
    for name in names:
        lo, hi, scale = PARAM_SPACE[name]
        v = float(params.get(name, DEFAULT_PARAMS[name]))
        if scale == "log":
            result.append((_math.log(v) - _math.log(lo)) / (_math.log(hi) - _math.log(lo)))
        else:
            result.append((v - lo) / (hi - lo))
    return result


def diff_from_default(params: dict) -> dict:
    """Return only the entries that differ from DEFAULT_PARAMS."""
    return {k: v for k, v in params.items() if v != DEFAULT_PARAMS.get(k)}


if __name__ == "__main__":
    print(f"Parameter space: {len(PARAM_SPACE)} dimensions")
    log_count  = sum(1 for _, (_, _, s) in PARAM_SPACE.items() if s == "log")
    int_count  = sum(1 for k in PARAM_SPACE if k in _INT_PARAMS)
    print(f"  log-scale: {log_count}  integer: {int_count}  continuous: {len(PARAM_SPACE) - int_count}")
