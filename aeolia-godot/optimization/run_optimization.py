"""
Optuna-based Aeolia history engine optimizer.
50 trials, 5 seeds, TPE sampler with variance penalty.

Usage:
    python3 run_optimization.py

Results written to optimization/results/
"""

from __future__ import annotations

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

from sim_proxy import (
    SimParams, DEFAULT_PARAMS, PARAM_BOUNDS,
    generate_test_world, simulate,
    pack_params, unpack_params,
)
from loss import (
    compute_loss, evaluate_seeds, LossWeights, DEFAULT_WEIGHTS,
    MultiSeedResult, run_nuclear_emergence_check,
)

RESULTS_DIR = OPT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Config

N_TRIALS        = 50
SEEDS           = [17, 42, 97, 137, 256]
VARIANCE_WEIGHT = 0.30   # λ: total = mean + λ * std
FAIL_PENALTY    = 2.0

# ---------------------------------------------------------------------------
# Helpers

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def _std(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(_mean([(x - m)**2 for x in xs]))

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
        sim_outputs_by_seed = sim_outputs,
        weights             = DEFAULT_WEIGHTS,
        variance_weight     = VARIANCE_WEIGHT,
        fail_penalty        = FAIL_PENALTY,
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
# Main optimization loop

def run():
    t0 = time.monotonic()

    print("Aeolia History Engine Optimizer (Optuna TPE)")
    print(f"  Trials       : {N_TRIALS}")
    print(f"  Seeds        : {SEEDS}")
    print(f"  Params       : {len(PARAM_BOUNDS)}")
    print(f"  Variance λ   : {VARIANCE_WEIGHT}")
    print(f"  Results dir  : {RESULTS_DIR}")
    print()

    print("Generating worlds...")
    worlds = {}
    for seed in SEEDS:
        worlds[seed] = generate_test_world(seed=seed)
        print(f"  seed={seed}: {len(worlds[seed]['archs'])} archs, "
              f"{len(worlds[seed]['plateau_edges'])} edges")
    print()

    print("Evaluating default params (baseline)...")
    baseline_eval = evaluate_params(DEFAULT_PARAMS, worlds)
    print(f"  Baseline total={baseline_eval['total']:.4f}  "
          f"mean={baseline_eval['mean']:.4f}  std={baseline_eval['std']:.4f}")
    comp_str = "  ".join(f"{k}={v:.3f}" for k, v in baseline_eval["components_mean"].items())
    print(f"  Components: {comp_str}")
    print()

    all_trials: list[dict] = []
    best_total = float("inf")

    print(f"{'Trial':>5}  {'Total':>8}  {'Mean':>8}  {'Std':>7}  {'Best':>8}")
    print("-" * 55)

    def objective(trial: optuna.Trial) -> float:
        x = [
            trial.suggest_float(name, lo, hi)
            for name, lo, hi in PARAM_BOUNDS
        ]
        params = unpack_params(x)
        t_trial = time.monotonic()
        ev = evaluate_params(params, worlds)
        elapsed_trial = time.monotonic() - t_trial

        nonlocal best_total
        is_best = ev["total"] < best_total
        if is_best:
            best_total = ev["total"]

        marker = " *" if is_best else ""
        print(f"{trial.number+1:>5}  {ev['total']:>8.4f}  {ev['mean']:>8.4f}  "
              f"{ev['std']:>7.4f}  {best_total:>8.4f}{marker}")

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

    sampler = optuna.samplers.TPESampler(
        seed=42,
        multivariate=True,
        n_startup_trials=20,
    )
    study = optuna.create_study(
        direction="minimize",
        study_name="aeolia_history_engine",
        sampler=sampler,
    )
    study.optimize(objective, n_trials=N_TRIALS, show_progress_bar=False)

    total_elapsed = time.monotonic() - t0

    print()
    print(f"Completed {N_TRIALS} trials in {total_elapsed:.1f}s "
          f"({total_elapsed/max(N_TRIALS,1):.1f}s/trial)")
    print(f"Best total loss: {best_total:.4f}  "
          f"(baseline: {baseline_eval['total']:.4f}, "
          f"improvement: {baseline_eval['total'] - best_total:.4f})")
    print()

    # Reconstruct best params from study
    best_x = [study.best_params[name] for name, _, _ in PARAM_BOUNDS]
    best_params = unpack_params(best_x)
    best_eval = evaluate_params(best_params, worlds)

    # ---------------------------------------------------------------------------
    # Save results

    # 1. best_params.json
    best_params_dict = {name: round(getattr(best_params, name), 8)
                        for name, _, _ in PARAM_BOUNDS}
    best_params_path = RESULTS_DIR / "best_params.json"
    best_params_path.write_text(json.dumps(best_params_dict, indent=2))
    (OPT_DIR / "best_params.json").write_text(json.dumps(best_params_dict, indent=2))
    print(f"Saved: {best_params_path}")

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

    breakdown_path = RESULTS_DIR / "loss_breakdown.json"
    breakdown_path.write_text(json.dumps(best_loss_detail, indent=2))
    print(f"Saved: {breakdown_path}")

    # 3. convergence.json
    best_trial_num = next(t["trial"] for t in all_trials
                          if t["is_best"] and abs(t["total"] - best_total) < 1e-9)
    convergence = {
        "n_trials":        N_TRIALS,
        "seeds":           SEEDS,
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
            "total":      best_total,
            "mean":       best_eval["mean"],
            "std":        best_eval["std"],
            "components": best_eval["components_mean"],
            "per_seed":   best_eval["per_seed"],
        },
        "improvement":  round(baseline_eval["total"] - best_total, 6),
        "trials":       all_trials,
    }
    convergence_path = RESULTS_DIR / "convergence.json"
    convergence_path.write_text(json.dumps(convergence, indent=2))
    print(f"Saved: {convergence_path}")

    # 4. convergence_summary.txt
    best_so_far = float("inf")
    milestone_lines = []
    milestones = {0, 4, 9, 19, 29, 49, N_TRIALS - 1}
    for t in all_trials:
        if t["total"] < best_so_far:
            best_so_far = t["total"]
        if (t["trial"] - 1) in milestones:
            milestone_lines.append(f"  trial {t['trial']:3d}: best_so_far={best_so_far:.4f}")

    summary_lines = [
        "Aeolia History Engine — Optimization Results",
        "=" * 60,
        f"Backend        : Optuna TPE (multivariate, n_startup=20)",
        f"Trials         : {N_TRIALS}",
        f"Seeds          : {SEEDS}",
        f"Parameters     : {len(PARAM_BOUNDS)}",
        f"Variance λ     : {VARIANCE_WEIGHT}",
        f"Total time     : {total_elapsed:.1f}s  ({total_elapsed/max(N_TRIALS,1):.1f}s/trial)",
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
    summary_path = RESULTS_DIR / "convergence_summary.txt"
    summary_path.write_text(summary_text)
    print(f"Saved: {summary_path}")
    print()
    print(summary_text)


if __name__ == "__main__":
    run()
