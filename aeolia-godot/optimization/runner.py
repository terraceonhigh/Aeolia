"""
Optuna-compatible runner for Aeolia history engine parameter optimization.

For each trial, the objective function:
    1. Samples a parameter dict from PARAM_SPACE
    2. Writes it to a temp JSON config
    3. Runs Godot 4 headlessly for each of N seeds
    4. Parses the JSON output from each run
    5. Calls evaluate_seeds() → mean_loss + λ*std  (multi-seed loss)
    6. Returns that scalar to Optuna

Usage
-----
    # Fast smoke-test (no Godot required):
    python runner.py --n-trials 20 --n-seeds 4 --stub

    # Real run:
    python runner.py --n-trials 200 --n-seeds 12 --godot /path/to/godot4

    # Continue an existing study (SQLite storage):
    python runner.py --n-trials 500 --storage sqlite:///study.db --study-name aeolia_v2

    # Show best params from a finished study:
    python runner.py --best --storage sqlite:///study.db

Godot interface
---------------
Each trial spawns one Godot subprocess per seed:

    godot4 --headless --path <project_root> \\
           --script res://optimization/history_engine_runner.gd \\
           -- --params <params.json> --seed <N> --out <output.json>

history_engine_runner.gd reads the params file, runs HistoryEngine.assign_politics
with those coefficients overriding the GDScript constants, and writes the
simulation output to --out.  See README.md for the required output schema and
a minimal implementation sketch.

Parameter space
---------------
All parameters map directly to constants in history_engine.gd.  Names use
the naming convention: <era>_<civ>_<quantity>.  Current default values are
the values currently hardcoded in the GDScript, so the default configuration
sits at the center of the prior.

Parallelism
-----------
--n-jobs > 1 runs multiple Optuna workers in the same process pool.  Each
worker runs all N seeds sequentially (Godot subprocesses are not thread-safe
from a single Python process, but separate workers are fine).  For large
studies, use --storage with SQLite or PostgreSQL and run multiple runner.py
processes in separate terminals.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

import optuna
from optuna.samplers import TPESampler

from loss_function import (
    DEFAULT_TARGETS,
    DEFAULT_WEIGHTS,
    LoreTargets,
    LossWeights,
    MultiSeedResult,
    evaluate_seeds,
)

# ---------------------------------------------------------------------------
# Configuration defaults (override via CLI flags or env vars)
# ---------------------------------------------------------------------------

# Seeds covering a range of world topologies:
#   - small primes     : 17, 31, 97   → varied island spacing
#   - round powers     : 256, 1024    → different Fibonacci jitter
#   - large values     : 8191, 65537  → exotic plateau graphs
DEFAULT_SEEDS = [17, 31, 42, 97, 137, 256, 512, 1024, 4096, 8191, 16384, 65537]

DEFAULT_GODOT_BIN  = os.environ.get("GODOT_BIN", "godot4")
DEFAULT_PROJECT    = Path(__file__).parent.parent   # aeolia-godot/
RUNNER_SCRIPT      = "res://optimization/history_engine_runner.gd"
GODOT_TIMEOUT      = 90        # seconds per subprocess
DEFAULT_VARIANCE_WEIGHT = 0.30
DEFAULT_FAIL_PENALTY    = 2.0

# ---------------------------------------------------------------------------
# Parameter space
# ---------------------------------------------------------------------------
# Format: name → (low, high)  for float params
#         name → [choice1, ...]  for categorical params
#
# All names must be accepted as JSON keys by history_engine_runner.gd and
# override the corresponding GDScript constant.  Current code values are
# noted beside each entry so reviewers can see how much room we're giving
# the optimizer.

PARAM_SPACE: dict[str, Any] = {

    # ── ERA 1: ANTIQUITY ────────────────────────────────────────────────────
    # Growth formula: pop[i] *= pow(1.0 + antiquity_growth_base * potential[i],
    #                               antiquity_growth_exponent)
    # Current: base=0.002, exp=30  → negligible spread; analysis §2 recommends
    # base 0.003–0.009 and exp 25–40 to produce meaningful differentiation.
    "antiquity_growth_base":       (0.001,  0.010),   # code: 0.002
    "antiquity_growth_exponent":   (20.0,   50.0),    # code: 30.0

    # Lattice paddi multiplier applied post-antiquity.
    # Analysis §2: the hardcoded 2.5× should emerge from geography, but until
    # substrate lat_factor is tunable this scalar is the main lever.
    "lattice_antiquity_pop_mult":  (1.3,    5.0),     # code: 2.5

    # Antiquity tech floors for hegemons.
    "reach_tech_floor_antiquity":  (2.0,    5.5),     # code: 3.5
    "lattice_tech_floor_antiquity":(2.5,    6.0),     # code: 3.8

    # ── ERA 2: SERIAL CONTACT ───────────────────────────────────────────────
    # Epidemic shock: severity = lerp(1.0, base_shock, crop_dist)
    # base_shock = base_lo + rng * base_range  →  [base_lo, base_lo+base_range]
    # Analysis §3: base_lo 0.20, base_range 0.25 is reasonable but severity
    # range should be calibrated against historical epidemics (20–45% max-dist).
    "epi_base_severity_lo":        (0.10,   0.30),    # code: 0.20
    "epi_base_severity_range":     (0.10,   0.45),    # code: 0.25

    # Trade recovery: pop *= 1 + trade_years * recovery_rate
    # Analysis §4: structurally sound, magnitude is the only lever here.
    "trade_recovery_rate":         (0.0001, 0.0012),  # code: 0.0004

    # Network effects for hegemon cores.
    # Formula: pop[reach] *= reach_serial_base * (1 + log2(1+network) * reach_serial_log)
    # Analysis §5: Reach A₀=1.2 δ=0.08 → higher log coefficient, lower base.
    #              Lattice A₀=0.8 → larger base, lower log coefficient.
    "reach_serial_base_mult":      (0.8,    2.5),     # code: 1.3
    "reach_serial_log_coef":       (0.12,   0.60),    # code: 0.30
    "reach_serial_tech_bonus":     (0.5,    2.5),     # code: 1.2
    "lattice_serial_base_mult":    (1.0,    4.0),     # code: 1.9
    "lattice_serial_log_coef":     (0.04,   0.30),    # code: 0.12
    "lattice_serial_tech_bonus":   (0.4,    2.0),     # code: 1.0

    # ── ERA 3: COLONIAL ─────────────────────────────────────────────────────
    # Reach extraction: rate = min(extraction_cap, base + col_years * per_year)
    # Analysis §7: needs ceiling; collapse trigger at extraction_collapse_threshold.
    "extraction_base_rate":        (0.08,   0.28),    # code: 0.15
    "extraction_per_year":         (3e-5,   3e-4),    # code: 0.0001
    "extraction_cap":              (0.18,   0.45),    # code: no cap (analysis recommends 0.30)
    "extraction_collapse_threshold":(0.18,  0.32),    # code: absent (analysis: 0.22)

    # Garrison absorption: Lattice absorbs fraction of source arch's pop.
    # Analysis §6: source pop should be decremented (now fixed); tune rate.
    "garrison_absorption_base":    (0.08,   0.35),    # code: 0.15
    "garrison_absorption_range":   (0.04,   0.20),    # code: 0.10

    # Tributary tribute rate.
    "tribute_base":                (0.02,   0.15),    # code: 0.05
    "tribute_range":               (0.02,   0.12),    # code: 0.05

    # ── ERA 4: INDUSTRIAL ───────────────────────────────────────────────────
    # Reach: A₀=1.2, δ=0.08 → higher tech leverage, faster compounding.
    # pop *= (1 + tech*reach_ind_tech_coef + pot*reach_ind_pot_coef)
    #       * (1 + log2(1+network)*reach_ind_log_coef)
    # tech += pot * reach_ind_tech_growth
    "reach_ind_tech_coef":         (0.05,   0.25),    # code: 0.12
    "reach_ind_pot_coef":          (0.05,   0.30),    # code: 0.14
    "reach_ind_log_coef":          (0.05,   0.35),    # code: 0.14
    "reach_ind_tech_growth":       (0.4,    1.8),     # code: 0.9

    # Lattice: β=0.6 → higher resource leverage, lower tech leverage.
    # pop *= (1 + tech*lattice_ind_tech_coef + pot*lattice_ind_pot_coef)
    #       * (1 + log2(1+lattice_integrated)*lattice_ind_log_coef)
    # tech += pot * lattice_ind_tech_growth
    "lattice_ind_tech_coef":       (0.02,   0.18),    # code: 0.06
    "lattice_ind_pot_coef":        (0.10,   0.40),    # code: 0.22
    "lattice_ind_log_coef":        (0.03,   0.25),    # code: 0.10
    "lattice_ind_tech_growth":     (0.2,    1.3),     # code: 0.6

    # Industrial-era tech floors (soft lower bounds post-era).
    # Analysis §9: hard floors suppress seed variance; these can be loosened.
    "reach_tech_floor_ind":        (5.0,    8.5),     # code: 7.0
    "lattice_tech_floor_ind":      (4.5,    8.0),     # code: 6.5

    # ── ERA 5: NUCLEAR ──────────────────────────────────────────────────────
    # Pop multipliers applied to hegemon cores at nuclear era entry.
    "reach_nuclear_pop_mult":      (1.05,   2.8),     # code: 1.4
    "lattice_nuclear_pop_mult":    (1.00,   2.5),     # code: 1.35
}


def suggest_params(trial: optuna.Trial) -> dict[str, float]:
    """Sample all PARAM_SPACE entries for a given Optuna trial."""
    params: dict = {}
    for name, spec in PARAM_SPACE.items():
        if isinstance(spec, list):
            params[name] = trial.suggest_categorical(name, spec)
        elif isinstance(spec[0], int) and isinstance(spec[1], int):
            params[name] = trial.suggest_int(name, spec[0], spec[1])
        else:
            params[name] = trial.suggest_float(name, float(spec[0]), float(spec[1]))
    return params


# ---------------------------------------------------------------------------
# Godot subprocess interface
# ---------------------------------------------------------------------------

def run_simulation(
    params:       dict,
    seed:         int,
    godot_bin:    str  = DEFAULT_GODOT_BIN,
    project_root: Path = DEFAULT_PROJECT,
    timeout:      int  = GODOT_TIMEOUT,
) -> dict:
    """
    Run the Godot history engine headlessly for one seed, return parsed output.

    Writes params + seed to a temp JSON file, invokes Godot, reads back the
    output JSON written by history_engine_runner.gd.

    Raises
    ------
    RuntimeError
        On non-zero exit code, timeout, or malformed output JSON.
    """
    with tempfile.TemporaryDirectory() as tmp:
        params_path = Path(tmp) / "params.json"
        out_path    = Path(tmp) / "output.json"

        params_path.write_text(json.dumps({**params, "seed": seed}))

        cmd = [
            godot_bin,
            "--headless",
            "--path", str(project_root),
            "--script", RUNNER_SCRIPT,
            "--",
            "--params", str(params_path),
            "--seed",   str(seed),
            "--out",    str(out_path),
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Godot timed out (>{timeout}s) for seed={seed}")

        if proc.returncode != 0:
            tail = proc.stderr[-1500:] if proc.stderr else ""
            raise RuntimeError(
                f"Godot exited {proc.returncode} for seed={seed}:\n{tail}"
            )

        if not out_path.exists():
            raise RuntimeError(
                f"Godot did not write output for seed={seed} "
                f"(expected {out_path})"
            )

        try:
            return json.loads(out_path.read_text())
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Godot output is not valid JSON for seed={seed}: {exc}"
            )


# ---------------------------------------------------------------------------
# Stub simulation (no Godot required — for pipeline smoke-testing)
# ---------------------------------------------------------------------------

def _stub_crop_distance(a: str, b: str) -> float:
    _TROPICAL  = {"paddi", "taro", "sago"}
    _TEMPERATE = {"emmer", "papa"}
    if a == b:
        return 0.2
    if frozenset([a, b]) == frozenset(["paddi", "papa"]):
        return 1.0
    at, bt = a in _TROPICAL, b in _TROPICAL
    ae, be = a in _TEMPERATE, b in _TEMPERATE
    if (at and bt) or (ae and be):
        return 0.5
    return 0.8


def run_simulation_stub(params: dict, seed: int) -> dict:
    """
    Generate deterministic synthetic simulation output for pipeline testing.

    Values are shaped by key params so the loss function can actually respond
    to parameter changes.  NOT valid for real optimization results.
    """
    import random
    rng = random.Random(seed ^ (hash(tuple(sorted(params.items()))) & 0xFFFF_FFFF))

    crops = ["paddi", "emmer", "taro", "nori", "sago", "papa"]

    # Antiquity growth: larger base → wider pop spread
    base = params.get("antiquity_growth_base", 0.002)
    exp  = params.get("antiquity_growth_exponent", 30.0)

    def _antiquity_pop(potential: float) -> float:
        return 10.0 * (1.0 + base * potential) ** exp

    N = 42
    states = []
    epi_log = []

    reach_arch   = 0
    lattice_arch = 1
    reach_crop   = "emmer"
    lattice_crop = "paddi"

    for i in range(N):
        if i == reach_arch:
            faction, status = "reach",   "core"
            crop = reach_crop
            potential = 0.85 + rng.gauss(0, 0.05)
        elif i == lattice_arch:
            faction, status = "lattice", "core"
            crop = lattice_crop
            potential = 0.80 + rng.gauss(0, 0.05)
        elif i < 8:
            faction = rng.choice(["reach", "lattice"])
            status  = rng.choice(["colony", "garrison", "tributary", "client"])
            crop    = rng.choice(crops)
            potential = 0.4 + rng.random() * 0.4
        elif i < 16:
            faction, status = "unknown", "uncontacted"
            crop    = rng.choice(crops)
            potential = 0.3 + rng.random() * 0.5
        else:
            faction = rng.choice(["reach", "lattice", "unknown"])
            status  = rng.choice(["pulse", "contacted", "uncontacted"])
            crop    = rng.choice(crops)
            potential = 0.2 + rng.random() * 0.6

        # Tech: Reach should lead; Lattice should have larger pop base
        if i == reach_arch:
            reach_tech_coef  = params.get("reach_ind_tech_coef", 0.12)
            tech = min(10.0, params.get("reach_tech_floor_ind", 7.0) + potential * reach_tech_coef * 10)
            tech = params.get("reach_tech_floor_antiquity", 3.5) + potential * 6.0
        elif i == lattice_arch:
            tech = params.get("lattice_tech_floor_antiquity", 3.8) + potential * 5.5
        else:
            tech = 2.0 + potential * 5.0

        # Population: Lattice paddi multiplier shapes ratio
        base_pop = _antiquity_pop(potential) * (1.0 + rng.gauss(0, 0.1))
        if i == lattice_arch:
            base_pop *= params.get("lattice_antiquity_pop_mult", 2.5)
        elif crop == "paddi":
            base_pop *= params.get("lattice_antiquity_pop_mult", 2.5) * 0.6

        # Status assignments (sovereignty/trade by status)
        sov_map   = {"core": 1.0, "colony": 0.25, "garrison": 0.35,
                     "tributary": 0.65, "client": 0.65, "pulse": 0.85,
                     "contacted": 0.90, "uncontacted": 1.0}
        trade_map = {"core": 0.80, "colony": 0.80, "garrison": 0.50,
                     "tributary": 0.40, "client": 0.60, "pulse": 0.20,
                     "contacted": 0.30, "uncontacted": 0.05}
        era_map   = {"colony": "colonial", "garrison": "colonial",
                     "tributary": "sail", "client": "industrial",
                     "pulse": "colonial", "contacted": "nuclear",
                     "uncontacted": None, "core": None}

        states.append({
            "faction":         faction,
            "status":          status,
            "name":            f"Arch_{i}",
            "population":      max(1.0, base_pop + rng.gauss(0, base_pop * 0.05)),
            "urbanization":    min(1.0, base_pop / 1000.0),
            "tech":            round(min(10.0, max(0.0, tech + rng.gauss(0, 0.3))), 1),
            "sovereignty":     min(1.0, max(0.0, sov_map.get(status, 0.5) + rng.gauss(0, 0.05))),
            "tradeIntegration":min(1.0, max(0.0, trade_map.get(status, 0.3) + rng.gauss(0, 0.05))),
            "eraOfContact":    era_map.get(status),
            "hopCount":        rng.randint(1, 8) if faction not in ("unknown",) else 0,
        })

    # Epi log: severity correlates with crop distance (parameterised)
    epi_base_lo    = params.get("epi_base_severity_lo", 0.20)
    epi_base_range = params.get("epi_base_severity_range", 0.25)
    for s in states[:12]:
        if s["status"] in ("uncontacted", "core"):
            continue
        contactor = reach_crop if s["faction"] == "reach" else lattice_crop
        cd = _stub_crop_distance(contactor, s.get("_crop", "emmer"))
        base_shock = epi_base_lo + rng.random() * epi_base_range
        mortality  = base_shock * cd + rng.gauss(0, 0.02)
        mortality  = min(0.95, max(0.01, mortality))
        epi_log.append({
            "arch":            states.index(s),
            "contactor_crop":  contactor,
            "contacted_crop":  rng.choice(crops),
            "mortality_rate":  mortality,
        })

    # Dark Forest break year: somewhere in nuclear era
    df_year = -200 + rng.randint(-150, 160)
    df_year = max(-300, min(-10, df_year))

    return {
        "states":     states,
        "df_year":    df_year,
        "reach_arch": reach_arch,
        "lattice_arch": lattice_arch,
        "epi_log":    epi_log,
        "substrate":  None,   # ag component degrades gracefully when absent
    }


# ---------------------------------------------------------------------------
# Optuna objective
# ---------------------------------------------------------------------------

def make_objective(
    seeds:           list,
    variance_weight: float,
    fail_penalty:    float,
    weights:         LossWeights,
    targets:         LoreTargets,
    godot_bin:       str,
    project_root:    Path,
    use_stub:        bool,
    verbose:         bool,
):
    """
    Factory returning the Optuna objective function with closed-over config.
    """
    def objective(trial: optuna.Trial) -> float:
        params = suggest_params(trial)
        outputs: dict = {}
        failed: list  = []

        for seed in seeds:
            try:
                if use_stub:
                    out = run_simulation_stub(params, seed)
                else:
                    out = run_simulation(params, seed, godot_bin, project_root)
                outputs[seed] = out
            except Exception as exc:  # noqa: BLE001
                print(
                    f"  [trial {trial.number}] seed={seed} sim failed: {exc}",
                    file=sys.stderr,
                )
                failed.append(seed)

        result: MultiSeedResult = evaluate_seeds(
            sim_outputs_by_seed = outputs,
            weights             = weights,
            targets             = targets,
            variance_weight     = variance_weight,
            fail_penalty        = fail_penalty,
        )

        if verbose:
            print(f"\ntrial={trial.number:4d}  {result}")
            means = result.component_means()
            stds  = result.component_stds()
            for k in means:
                print(f"  {k:8s}  mean={means[k]:.4f}  std={stds.get(k, 0.0):.4f}")

        # Report intermediate value so Optuna can prune with MedianPruner
        trial.report(result.mean, step=len(outputs))

        return result.total

    return objective


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Optimize Aeolia history engine parameters with Optuna.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--n-trials",        type=int,   default=100)
    p.add_argument("--n-seeds",         type=int,   default=8,
                   help="Number of seeds per trial (taken from front of DEFAULT_SEEDS)")
    p.add_argument("--variance-weight", type=float, default=DEFAULT_VARIANCE_WEIGHT,
                   help="λ: total = mean + λ * std across seeds")
    p.add_argument("--fail-penalty",    type=float, default=DEFAULT_FAIL_PENALTY,
                   help="Loss assigned to each failed seed")
    p.add_argument("--godot",           type=str,   default=DEFAULT_GODOT_BIN)
    p.add_argument("--project",         type=Path,  default=DEFAULT_PROJECT)
    p.add_argument("--study-name",      type=str,   default="aeolia_history_engine")
    p.add_argument("--storage",         type=str,   default=None,
                   help="Optuna storage URL, e.g. sqlite:///study.db")
    p.add_argument("--n-jobs",          type=int,   default=1,
                   help="Parallel Optuna workers (-1 = all CPUs)")
    p.add_argument("--stub",            action="store_true",
                   help="Use synthetic stub data (no Godot required)")
    p.add_argument("--verbose",         action="store_true",
                   help="Print per-seed component breakdown each trial")
    p.add_argument("--best",            action="store_true",
                   help="Print best params from existing study and exit")
    p.add_argument("--weights",         type=str,   default=None,
                   help='JSON overrides for loss component weights, e.g. \'{"epi":3.0}\'')
    p.add_argument("--params-subset",   type=str,   default=None,
                   help="Comma-separated list of param names to optimize (others held fixed)")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    seeds   = DEFAULT_SEEDS[: args.n_seeds]
    weights = LossWeights()
    if args.weights:
        for k, v in json.loads(args.weights).items():
            setattr(weights, k, float(v))

    # Optionally restrict the search space to a subset of params
    active_params = set(PARAM_SPACE.keys())
    if args.params_subset:
        active_params = set(args.params_subset.split(","))
        unknown = active_params - set(PARAM_SPACE.keys())
        if unknown:
            sys.exit(f"Unknown params: {unknown}")

    # Temporarily restrict PARAM_SPACE for this run
    global PARAM_SPACE
    if args.params_subset:
        _full_space = PARAM_SPACE
        PARAM_SPACE = {k: v for k, v in _full_space.items() if k in active_params}

    sampler = TPESampler(
        seed=42,
        multivariate=True,     # group=True lets TPE learn cross-param correlations
        group=True,
        n_startup_trials=max(20, len(PARAM_SPACE) * 2),
    )

    study = optuna.create_study(
        study_name   = args.study_name,
        direction    = "minimize",
        sampler      = sampler,
        storage      = args.storage,
        load_if_exists = True,
    )

    if args.best:
        if not study.trials:
            print("No completed trials in this study.")
            return
        best = study.best_trial
        print(f"Best trial: #{best.number}  loss={best.value:.4f}")
        print(json.dumps(best.params, indent=2))
        return

    objective = make_objective(
        seeds           = seeds,
        variance_weight = args.variance_weight,
        fail_penalty    = args.fail_penalty,
        weights         = weights,
        targets         = DEFAULT_TARGETS,
        godot_bin       = args.godot,
        project_root    = args.project,
        use_stub        = args.stub,
        verbose         = args.verbose,
    )

    print(f"Optimizing {len(PARAM_SPACE)} parameters across {len(seeds)} seeds")
    print(f"Seeds    : {seeds}")
    print(f"λ (var)  : {args.variance_weight}")
    print(f"Trials   : {args.n_trials}  jobs={args.n_jobs}")
    if args.stub:
        print("[STUB] Using synthetic data — results are for pipeline testing only")

    t0 = time.monotonic()
    study.optimize(
        objective,
        n_trials         = args.n_trials,
        n_jobs           = args.n_jobs,
        show_progress_bar= True,
    )
    elapsed = time.monotonic() - t0

    print(f"\nCompleted in {elapsed:.1f}s  ({elapsed / max(len(study.trials), 1):.1f}s/trial)")
    print(f"Best loss : {study.best_value:.4f}")
    print("Best params:")
    print(json.dumps(study.best_params, indent=2))

    out_path = Path(__file__).parent / "best_params.json"
    out_path.write_text(json.dumps(study.best_params, indent=2))
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
