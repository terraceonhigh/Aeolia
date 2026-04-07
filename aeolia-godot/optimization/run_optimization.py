"""
Optuna-based Aeolia history engine v2 optimizer.

21-parameter energy-coupled search using TPE sampler.
Seeds: 216089 (primary) + top candidates from worlds/ directory.
10,000 trials with variance weighting across seeds.

Usage:
    python3 run_optimization.py              # full 10K run
    python3 run_optimization.py --test 100   # quick 100-trial test

Results written to optimization/results/
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

# ---------------------------------------------------------------------------
# Path setup
OPT_DIR = Path(__file__).parent
sys.path.insert(0, str(OPT_DIR))

from sim_proxy_v2 import (
    SimParams, DEFAULT_PARAMS, PARAM_BOUNDS,
    simulate, load_world,
    pack_params, unpack_params,
)
from loss import (
    compute_loss, evaluate_seeds, LossWeights, DEFAULT_WEIGHTS,
    MultiSeedResult,
)

WORLDS_DIR = OPT_DIR / "worlds"
RESULTS_DIR = OPT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Config

N_TRIALS_DEFAULT = 10000
PRIMARY_SEED     = 216089
VARIANCE_WEIGHT  = 0.30   # total = mean + λ * std
FAIL_PENALTY     = 2.0

# Seeds from the geo-filter pass + stability anchors.
# 216089 is mandatory; others are top candidates from worlds/ directory.
# Primary geo-filter winners + anchors (all must have candidate files with cx/cy/cz)
GEO_SEEDS  = [216089, 51, 73, 74, 11, 66]
ANCHOR_SEEDS = [17, 42, 97]  # also available as candidate files

# Culture share groups — optimizer samples 2 freely, third = 1 - a - b
_SHARE_GROUPS = [
    ("civic_expansion_share", "civic_tech_share", "civic_consolidation_share"),
    ("subject_expansion_share", "subject_tech_share", "subject_consolidation_share"),
    ("parochial_expansion_share", "parochial_tech_share", None),  # parochial_consolidation derived
]

# ---------------------------------------------------------------------------
# Helpers

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def _std(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(_mean([(x - m)**2 for x in xs]))


def _bounds_for(name: str):
    """Look up bounds from PARAM_BOUNDS."""
    for n, lo, hi in PARAM_BOUNDS:
        if n == name:
            return lo, hi
    raise KeyError(f"Unknown param: {name}")


def _suggest_shares(trial: optuna.Trial, prefix: str):
    """Suggest two shares freely, derive third = 1 - a - b clamped to [0.05, 1.0].
    Returns (expansion, tech, consolidation)."""
    exp_name = f"{prefix}_expansion_share"
    tech_name = f"{prefix}_tech_share"
    cons_name = f"{prefix}_consolidation_share"

    lo_e, hi_e = _bounds_for(exp_name)
    lo_t, hi_t = _bounds_for(tech_name)

    exp_val = trial.suggest_float(exp_name, lo_e, hi_e)
    tech_val = trial.suggest_float(tech_name, lo_t, hi_t)
    cons_val = max(0.05, min(1.0, 1.0 - exp_val - tech_val))

    # Clamp consolidation to its bounds if it has explicit bounds
    try:
        lo_c, hi_c = _bounds_for(cons_name)
        cons_val = max(lo_c, min(hi_c, cons_val))
    except KeyError:
        pass  # parochial has no explicit consolidation bounds

    return exp_val, tech_val, cons_val


# ---------------------------------------------------------------------------
# Multi-seed evaluation

def evaluate_params(params: SimParams, worlds: dict) -> dict:
    sim_outputs = {}
    for seed, world in worlds.items():
        try:
            sim_outputs[seed] = simulate(world, params, seed=seed)
        except Exception as e:
            print(f"  [seed={seed}] sim failed: {e}", file=sys.stderr)

    msr: MultiSeedResult = evaluate_seeds(
        sim_outputs_by_seed=sim_outputs,
        weights=DEFAULT_WEIGHTS,
        variance_weight=VARIANCE_WEIGHT,
        fail_penalty=FAIL_PENALTY,
    )

    comp_mean = msr.component_means()
    return {
        "total":           round(msr.total, 6),
        "mean":            round(msr.mean, 6),
        "std":             round(msr.std, 6),
        "per_seed":        {str(s): round(lr.total, 6) for s, lr in msr.per_seed.items()},
        "components_mean": {k: round(v, 5) for k, v in comp_mean.items()},
    }


# ---------------------------------------------------------------------------
# Objective

def make_objective(worlds: dict, all_trials: list, best_holder: list):
    """Create an Optuna objective closure."""

    def objective(trial: optuna.Trial) -> float:
        # --- Suggest 21 parameters ---
        # Culture shares: sample 2 freely, derive third
        civic_e, civic_t, civic_c = _suggest_shares(trial, "civic")
        subject_e, subject_t, subject_c = _suggest_shares(trial, "subject")
        parochial_e, parochial_t, parochial_c = _suggest_shares(trial, "parochial")

        # Knowledge compounding
        A0_civic     = trial.suggest_float("A0_civic",     *_bounds_for("A0_civic"))
        A0_subject   = trial.suggest_float("A0_subject",   *_bounds_for("A0_subject"))
        A0_parochial = trial.suggest_float("A0_parochial", *_bounds_for("A0_parochial"))

        # Material conditions
        cu_unlock_tech           = trial.suggest_float("cu_unlock_tech",           *_bounds_for("cu_unlock_tech"))
        au_contact_bonus         = trial.suggest_float("au_contact_bonus",         *_bounds_for("au_contact_bonus"))
        naphtha_richness         = trial.suggest_float("naphtha_richness",         *_bounds_for("naphtha_richness"))
        naphtha_depletion        = trial.suggest_float("naphtha_depletion",        *_bounds_for("naphtha_depletion"))
        energy_to_tfp            = trial.suggest_float("energy_to_tfp",            *_bounds_for("energy_to_tfp"))
        pu_dependent_factor      = trial.suggest_float("pu_dependent_factor",      *_bounds_for("pu_dependent_factor"))
        resource_targeting_weight = trial.suggest_float("resource_targeting_weight", *_bounds_for("resource_targeting_weight"))

        # Contact dynamics
        epi_base_severity    = trial.suggest_float("epi_base_severity",    *_bounds_for("epi_base_severity"))
        sov_extraction_decay = trial.suggest_float("sov_extraction_decay", *_bounds_for("sov_extraction_decay"))
        df_detection_range   = trial.suggest_float("df_detection_range",   *_bounds_for("df_detection_range"))

        # Build SimParams
        params = SimParams(
            civic_expansion_share=civic_e,
            civic_tech_share=civic_t,
            civic_consolidation_share=civic_c,
            subject_expansion_share=subject_e,
            subject_tech_share=subject_t,
            subject_consolidation_share=subject_c,
            parochial_expansion_share=parochial_e,
            parochial_tech_share=parochial_t,
            A0_civic=A0_civic,
            A0_subject=A0_subject,
            A0_parochial=A0_parochial,
            cu_unlock_tech=cu_unlock_tech,
            au_contact_bonus=au_contact_bonus,
            naphtha_richness=naphtha_richness,
            naphtha_depletion=naphtha_depletion,
            energy_to_tfp=energy_to_tfp,
            pu_dependent_factor=pu_dependent_factor,
            resource_targeting_weight=resource_targeting_weight,
            epi_base_severity=epi_base_severity,
            sov_extraction_decay=sov_extraction_decay,
            df_detection_range=df_detection_range,
        )

        t_trial = time.monotonic()
        ev = evaluate_params(params, worlds)
        elapsed_trial = time.monotonic() - t_trial

        is_best = ev["total"] < best_holder[0]
        if is_best:
            best_holder[0] = ev["total"]

        marker = " *" if is_best else ""
        print(f"{trial.number+1:>5}  {ev['total']:>8.4f}  {ev['mean']:>8.4f}  "
              f"{ev['std']:>7.4f}  {best_holder[0]:>8.4f}{marker}")

        all_trials.append({
            "trial":      trial.number + 1,
            "total":      ev["total"],
            "mean":       ev["mean"],
            "std":        ev["std"],
            "per_seed":   ev["per_seed"],
            "components": ev["components_mean"],
            "elapsed_s":  round(elapsed_trial, 3),
            "is_best":    is_best,
        })
        return ev["total"]

    return objective


# ---------------------------------------------------------------------------
# Load worlds

def load_worlds(seeds: list) -> dict:
    """Load world files for each seed from candidate JSON files."""
    worlds = {}
    for seed in seeds:
        candidate_path = WORLDS_DIR / f"candidate_{seed:07d}.json"
        if not candidate_path.exists():
            print(f"  seed={seed}: SKIPPED (no candidate file)", file=sys.stderr)
            continue
        worlds[seed] = load_world(str(candidate_path))
        print(f"  seed={seed}: {len(worlds[seed]['archs'])} archs, "
              f"{len(worlds[seed]['plateau_edges'])} edges")
    return worlds


# ---------------------------------------------------------------------------
# Per-term loss breakdown printer

def print_loss_breakdown(params: SimParams, worlds: dict):
    """Print detailed per-term loss breakdown for best parameters."""
    print()
    print("=" * 70)
    print("  PER-TERM LOSS BREAKDOWN (best params)")
    print("=" * 70)

    for seed in sorted(worlds.keys()):
        world = worlds[seed]
        try:
            result = simulate(world, params, seed=seed)
            lr = compute_loss(result)
        except Exception as e:
            print(f"\n  seed={seed}: ERROR — {e}")
            continue

        print(f"\n  seed={seed}  total={lr.total:.4f}  "
              f"mapping={lr.mapping.get('mapping_note', '?')}")
        print(f"    Reach  → arch {lr.mapping.get('reach_core')} "
              f"({lr.mapping.get('reach_culture', '?')})")
        print(f"    Lattice → arch {lr.mapping.get('lattice_core')} "
              f"({lr.mapping.get('lattice_culture', '?')})")
        print(f"    {'Term':<26s} {'Weighted':>8s}  {'Raw':>8s}")
        print(f"    {'-'*46}")
        for k in lr.components:
            print(f"    {k:<26s} {lr.components[k]:>8.4f}  {lr.raw[k]:>8.4f}")


# ---------------------------------------------------------------------------
# Main

def run():
    parser = argparse.ArgumentParser(description="Aeolia v2 optimizer")
    parser.add_argument("--test", type=int, default=None,
                        help="Quick test with N trials (e.g. --test 100)")
    args = parser.parse_args()

    n_trials = args.test if args.test else N_TRIALS_DEFAULT
    seeds = GEO_SEEDS + ANCHOR_SEEDS

    t0 = time.monotonic()

    print("Aeolia History Engine v2 Optimizer (Optuna TPE)")
    print(f"  Trials       : {n_trials}" + (" [TEST MODE]" if args.test else ""))
    print(f"  Seeds        : {seeds}")
    print(f"  Params       : {len(PARAM_BOUNDS)} (21 v2 parameters)")
    print(f"  Variance λ   : {VARIANCE_WEIGHT}")
    print(f"  Results dir  : {RESULTS_DIR}")
    print()

    print("Loading worlds...")
    worlds = load_worlds(seeds)
    print()

    print("Evaluating default params (baseline)...")
    baseline_eval = evaluate_params(DEFAULT_PARAMS, worlds)
    print(f"  Baseline total={baseline_eval['total']:.4f}  "
          f"mean={baseline_eval['mean']:.4f}  std={baseline_eval['std']:.4f}")
    comp_str = "  ".join(f"{k}={v:.3f}" for k, v in baseline_eval["components_mean"].items())
    print(f"  Components: {comp_str}")
    print()

    all_trials: list[dict] = []
    best_holder = [float("inf")]

    print(f"{'Trial':>5}  {'Total':>8}  {'Mean':>8}  {'Std':>7}  {'Best':>8}")
    print("-" * 55)

    sampler = optuna.samplers.TPESampler(
        seed=42,
        multivariate=True,
        n_startup_trials=min(20, max(5, n_trials // 10)),
    )
    study = optuna.create_study(
        direction="minimize",
        study_name="aeolia_v2",
        sampler=sampler,
    )

    objective = make_objective(worlds, all_trials, best_holder)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    total_elapsed = time.monotonic() - t0
    best_total = best_holder[0]

    print()
    print(f"Completed {n_trials} trials in {total_elapsed:.1f}s "
          f"({total_elapsed/max(n_trials,1):.1f}s/trial)")
    print(f"Best total loss: {best_total:.4f}  "
          f"(baseline: {baseline_eval['total']:.4f}, "
          f"improvement: {baseline_eval['total'] - best_total:.4f})")
    print()

    # Reconstruct best params from study
    best_trial = study.best_trial
    bp = best_trial.params

    # Derive consolidation shares (not directly in Optuna params)
    civic_c = max(0.05, min(1.0, 1.0 - bp["civic_expansion_share"] - bp["civic_tech_share"]))
    subject_c = max(0.05, min(1.0, 1.0 - bp["subject_expansion_share"] - bp["subject_tech_share"]))
    parochial_c = max(0.05, min(1.0, 1.0 - bp["parochial_expansion_share"] - bp["parochial_tech_share"]))

    # Clamp consolidation to its bounds
    for name, val_ref in [("civic_consolidation_share", civic_c),
                          ("subject_consolidation_share", subject_c)]:
        lo, hi = _bounds_for(name)
        if name == "civic_consolidation_share":
            civic_c = max(lo, min(hi, val_ref))
        else:
            subject_c = max(lo, min(hi, val_ref))

    best_params = SimParams(
        civic_expansion_share=bp["civic_expansion_share"],
        civic_tech_share=bp["civic_tech_share"],
        civic_consolidation_share=civic_c,
        subject_expansion_share=bp["subject_expansion_share"],
        subject_tech_share=bp["subject_tech_share"],
        subject_consolidation_share=subject_c,
        parochial_expansion_share=bp["parochial_expansion_share"],
        parochial_tech_share=bp["parochial_tech_share"],
        A0_civic=bp["A0_civic"],
        A0_subject=bp["A0_subject"],
        A0_parochial=bp["A0_parochial"],
        cu_unlock_tech=bp["cu_unlock_tech"],
        au_contact_bonus=bp["au_contact_bonus"],
        naphtha_richness=bp["naphtha_richness"],
        naphtha_depletion=bp["naphtha_depletion"],
        energy_to_tfp=bp["energy_to_tfp"],
        pu_dependent_factor=bp["pu_dependent_factor"],
        resource_targeting_weight=bp["resource_targeting_weight"],
        epi_base_severity=bp["epi_base_severity"],
        sov_extraction_decay=bp["sov_extraction_decay"],
        df_detection_range=bp["df_detection_range"],
    )

    best_eval = evaluate_params(best_params, worlds)

    # --- Per-term loss breakdown ---
    print_loss_breakdown(best_params, worlds)

    # ---------------------------------------------------------------------------
    # Save results

    # 1. best_params_v2.json
    best_params_dict = {}
    for name, _, _ in PARAM_BOUNDS:
        best_params_dict[name] = round(getattr(best_params, name), 8)
    best_params_path = RESULTS_DIR / "best_params_v2.json"
    best_params_path.write_text(json.dumps(best_params_dict, indent=2))
    # Also save a copy at the optimization root for easy access
    (OPT_DIR / "best_params_v2.json").write_text(json.dumps(best_params_dict, indent=2))
    print(f"\nSaved: {best_params_path}")

    # 2. loss_breakdown.json
    best_loss_detail = {}
    for seed, world in worlds.items():
        try:
            result = simulate(world, best_params, seed=seed)
            lr = compute_loss(result)
            best_loss_detail[str(seed)] = {
                "total":      round(lr.total, 6),
                "components": {k: round(v, 6) for k, v in lr.components.items()},
                "details": {
                    comp: {dk: (round(dv, 6) if isinstance(dv, float) else dv)
                           for dk, dv in dets.items()}
                    for comp, dets in lr.details.items()
                },
            }
        except Exception as e:
            best_loss_detail[str(seed)] = {"error": str(e)}

    breakdown_path = RESULTS_DIR / "loss_breakdown_v2.json"
    breakdown_path.write_text(json.dumps(best_loss_detail, indent=2))
    print(f"Saved: {breakdown_path}")

    # 3. convergence_v2.json
    best_trial_num = best_trial.number + 1
    convergence = {
        "n_trials":        n_trials,
        "seeds":           seeds,
        "variance_weight": VARIANCE_WEIGHT,
        "n_params":        len(PARAM_BOUNDS),
        "elapsed_s":       round(total_elapsed, 2),
        "backend":         "optuna-TPE",
        "baseline": {
            "total":      baseline_eval["total"],
            "mean":       baseline_eval["mean"],
            "std":        baseline_eval["std"],
            "components": baseline_eval["components_mean"],
        },
        "best": {
            "trial":      best_trial_num,
            "total":      round(best_total, 6),
            "mean":       best_eval["mean"],
            "std":        best_eval["std"],
            "components": best_eval["components_mean"],
            "per_seed":   best_eval["per_seed"],
        },
        "improvement":  round(baseline_eval["total"] - best_total, 6),
        "trials":       all_trials,
    }
    convergence_path = RESULTS_DIR / "convergence_v2.json"
    convergence_path.write_text(json.dumps(convergence, indent=2))
    print(f"Saved: {convergence_path}")

    # 4. convergence_summary_v2.txt
    best_so_far = float("inf")
    milestone_lines = []
    milestones = {0, 4, 9, 19, 49, 99, 499, 999, 2499, 4999, n_trials - 1}
    for t in all_trials:
        if t["total"] < best_so_far:
            best_so_far = t["total"]
        if (t["trial"] - 1) in milestones:
            milestone_lines.append(f"  trial {t['trial']:5d}: best_so_far={best_so_far:.4f}")

    summary_lines = [
        "Aeolia History Engine v2 — Optimization Results",
        "=" * 60,
        f"Backend        : Optuna TPE (multivariate, n_startup={min(20, max(5, n_trials // 10))})",
        f"Trials         : {n_trials}",
        f"Seeds          : {seeds}",
        f"Parameters     : {len(PARAM_BOUNDS)} (21 v2 energy-coupled)",
        f"Variance λ     : {VARIANCE_WEIGHT}",
        f"Total time     : {total_elapsed:.1f}s  ({total_elapsed/max(n_trials,1):.1f}s/trial)",
        "",
        "Baseline (default params):",
        f"  total={baseline_eval['total']:.4f}  mean={baseline_eval['mean']:.4f}  std={baseline_eval['std']:.4f}",
        "  " + "  ".join(f"{k}={v:.4f}" for k, v in baseline_eval["components_mean"].items()),
        "",
        f"Best (trial #{best_trial_num}):",
        f"  total={best_total:.4f}  mean={best_eval['mean']:.4f}  std={best_eval['std']:.4f}",
        "  " + "  ".join(f"{k}={v:.4f}" for k, v in best_eval["components_mean"].items()),
        f"  Improvement vs baseline: {baseline_eval['total'] - best_total:.4f}",
        "",
        "Per-seed losses (best params):",
    ]
    for seed_str, seed_data in best_loss_detail.items():
        if "total" in seed_data:
            summary_lines.append(
                f"  seed={seed_str}: total={seed_data['total']:.4f}  "
                + "  ".join(f"{k}={v:.4f}" for k, v in seed_data["components"].items()))
        else:
            summary_lines.append(f"  seed={seed_str}: ERROR {seed_data.get('error')}")

    summary_lines += ["", "Convergence (best-so-far):"] + milestone_lines

    summary_lines += ["", "Best parameter values (vs defaults):"]
    default_vals = {name: getattr(DEFAULT_PARAMS, name) for name, _, _ in PARAM_BOUNDS}
    for name, lo, hi in PARAM_BOUNDS:
        best_val = best_params_dict[name]
        default_val = default_vals[name]
        delta = best_val - default_val
        pct = delta / max(abs(hi - lo), 1e-9) * 100
        flag = " <<<" if abs(pct) > 20 else ""
        summary_lines.append(
            f"  {name:<36s} best={best_val:>10.6f}  "
            f"default={default_val:>10.6f}  delta={delta:+.6f} ({pct:+.0f}% of range){flag}")

    summary_lines += [
        "",
        "GDScript constants (changed params, |Δ| > 5% of range):",
    ]
    for name, lo, hi in PARAM_BOUNDS:
        best_val = best_params_dict[name]
        default_val = default_vals[name]
        if abs(best_val - default_val) / max(hi - lo, 1e-9) > 0.05:
            summary_lines.append(f"  var {name} := {best_val:.6f}")

    summary_text = "\n".join(summary_lines) + "\n"
    summary_path = RESULTS_DIR / "convergence_summary_v2.txt"
    summary_path.write_text(summary_text)
    print(f"Saved: {summary_path}")
    print()
    print(summary_text)


if __name__ == "__main__":
    run()
