"""
Optuna-based Aeolia history engine v2 optimizer.

25-parameter continuous culture-space search using TPE sampler.
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
GEO_SEEDS  = [216089, 51, 73, 74, 11, 66]
ANCHOR_SEEDS = [17, 42, 97]

# ---------------------------------------------------------------------------
# Helpers

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def _std(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(_mean([(x - m)**2 for x in xs]))

# Lookup table for bounds
_BOUNDS = {name: (lo, hi) for name, lo, hi in PARAM_BOUNDS}


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
        # Suggest all 25 parameters directly from PARAM_BOUNDS
        suggested = {}
        for name, lo, hi in PARAM_BOUNDS:
            suggested[name] = trial.suggest_float(name, lo, hi)

        params = SimParams(**suggested)

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
    print(f"  Params       : {len(PARAM_BOUNDS)} (v2 continuous culture-space)")
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
    best_params = SimParams(**bp)

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
        f"Parameters     : {len(PARAM_BOUNDS)} (v2 continuous culture-space)",
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
