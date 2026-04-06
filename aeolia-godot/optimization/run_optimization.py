"""
Pure-Python Aeolia history engine optimizer.
No external dependencies (no scipy, no optuna, no numpy).

Algorithm: Latin Hypercube random search for the first 40 trials,
then 10 exploitation trials that perturb the best-so-far point.
50 trials total across 5 seeds with variance penalty.

Usage:
    python3 run_optimization.py

Results written to optimization/results/
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup
OPT_DIR = Path(__file__).parent
sys.path.insert(0, str(OPT_DIR))

from sim_proxy import (
    SimParams, DEFAULT_PARAMS, PARAM_BOUNDS,
    generate_test_world, simulate,
    pack_params, unpack_params,
)
from loss import compute_loss, LossWeights, LoreTargets, DEFAULT_WEIGHTS

RESULTS_DIR = OPT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Config

N_TRIALS         = 50
SEEDS            = [17, 42, 97, 137, 256]
VARIANCE_WEIGHT  = 0.30   # lambda: total = mean + lambda * std
FAIL_PENALTY     = 2.0
N_EXPLOIT        = 10     # last N_EXPLOIT trials exploit best-so-far
RNG_SEED         = 1234

# ---------------------------------------------------------------------------
# Helpers

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def _std(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(_mean([(x - m)**2 for x in xs]))

def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

# ---------------------------------------------------------------------------
# Multi-seed evaluation

def evaluate(params: SimParams, worlds: dict) -> dict:
    """
    Run simulate() for each seed, compute per-seed loss, aggregate.
    worlds: {seed: world_dict}
    Returns dict with keys: total, mean, std, per_seed, components_mean
    """
    per_seed_losses = {}
    per_seed_components = {}
    failed = []

    for seed, world in worlds.items():
        try:
            result = simulate(world, params, seed=seed)
            lr = compute_loss(result, substrate=result.get("substrate"))
            per_seed_losses[seed] = lr.total
            per_seed_components[seed] = lr.components
        except Exception as e:
            print(f"  [seed={seed}] sim failed: {e}", file=sys.stderr)
            failed.append(seed)
            per_seed_losses[seed] = FAIL_PENALTY

    scalars = list(per_seed_losses.values())
    m = _mean(scalars)
    s = _std(scalars)
    total = m + VARIANCE_WEIGHT * s

    # Average components across seeds
    comp_mean = {}
    if per_seed_components:
        all_keys = list(next(iter(per_seed_components.values())).keys())
        for k in all_keys:
            vals = [per_seed_components[seed][k] for seed in per_seed_components]
            comp_mean[k] = round(_mean(vals), 5)

    return {
        "total":            round(total, 6),
        "mean":             round(m, 6),
        "std":              round(s, 6),
        "per_seed":         {str(k): round(v, 6) for k, v in per_seed_losses.items()},
        "components_mean":  comp_mean,
        "failed_seeds":     failed,
    }

# ---------------------------------------------------------------------------
# Latin Hypercube sampler (pure Python)

def latin_hypercube_samples(n: int, bounds: list, rng: random.Random) -> list:
    """
    Generate n parameter vectors via Latin Hypercube Sampling.
    bounds: list of (name, lo, hi)
    Returns list of SimParams objects.
    """
    d = len(bounds)
    # For each dimension, divide [0,1] into n equal intervals and shuffle
    intervals = []
    for _ in range(d):
        pts = [(i + rng.random()) / n for i in range(n)]
        rng.shuffle(pts)
        intervals.append(pts)

    samples = []
    for i in range(n):
        x = []
        for j, (name, lo, hi) in enumerate(bounds):
            x.append(lo + intervals[j][i] * (hi - lo))
        samples.append(unpack_params(x))
    return samples

# ---------------------------------------------------------------------------
# Exploitation: perturb best params

def perturb(best: SimParams, bounds: list, rng: random.Random, scale: float = 0.15) -> SimParams:
    """
    Generate a new candidate by gaussian perturbation around best params.
    scale: fraction of each param's range to use as std dev.
    """
    x = pack_params(best)
    new_x = []
    for i, (name, lo, hi) in enumerate(bounds):
        sigma = (hi - lo) * scale
        val = x[i] + rng.gauss(0, sigma)
        new_x.append(_clamp(val, lo, hi))
    return unpack_params(new_x)

# ---------------------------------------------------------------------------
# Main optimization loop

def run():
    rng = random.Random(RNG_SEED)
    t0 = time.monotonic()

    print(f"Aeolia History Engine Optimizer")
    print(f"  Trials       : {N_TRIALS}")
    print(f"  Seeds        : {SEEDS}")
    print(f"  Params       : {len(PARAM_BOUNDS)}")
    print(f"  Variance λ   : {VARIANCE_WEIGHT}")
    print(f"  Results dir  : {RESULTS_DIR}")
    print()

    # Pre-generate all worlds (same worlds used for every trial — fair comparison)
    print("Generating worlds...")
    worlds = {}
    for seed in SEEDS:
        worlds[seed] = generate_test_world(seed=seed)
        print(f"  seed={seed}: {len(worlds[seed]['archs'])} archs, "
              f"{len(worlds[seed]['plateau_edges'])} edges")
    print()

    # Evaluate default params as baseline
    print("Evaluating default params (baseline)...")
    baseline_eval = evaluate(DEFAULT_PARAMS, worlds)
    print(f"  Baseline total={baseline_eval['total']:.4f}  "
          f"mean={baseline_eval['mean']:.4f}  std={baseline_eval['std']:.4f}")
    print(f"  Components: {baseline_eval['components_mean']}")
    print()

    # Generate LHS candidates for first (N_TRIALS - N_EXPLOIT) trials
    n_random = N_TRIALS - N_EXPLOIT
    print(f"Generating {n_random} Latin Hypercube candidates...")
    candidates = latin_hypercube_samples(n_random, PARAM_BOUNDS, rng)

    # Optimization loop
    all_trials = []
    best_total = float("inf")
    best_params = DEFAULT_PARAMS
    best_eval = baseline_eval

    print(f"{'Trial':>5}  {'Total':>8}  {'Mean':>8}  {'Std':>7}  {'Best':>8}  Components")
    print("-" * 90)

    for trial_idx in range(N_TRIALS):
        t_trial = time.monotonic()

        if trial_idx < n_random:
            params = candidates[trial_idx]
        else:
            # Exploitation phase: perturb best-so-far, narrowing scale
            exploit_step = trial_idx - n_random
            scale = 0.12 * (0.85 ** exploit_step)  # shrinking perturbation
            params = perturb(best_params, PARAM_BOUNDS, rng, scale=scale)

        ev = evaluate(params, worlds)
        elapsed_trial = time.monotonic() - t_trial

        # Track best
        if ev["total"] < best_total:
            best_total = ev["total"]
            best_params = params
            best_eval = ev
            marker = " *"
        else:
            marker = ""

        comp_str = "  ".join(f"{k}={v:.3f}" for k, v in ev["components_mean"].items())
        print(f"{trial_idx+1:>5}  {ev['total']:>8.4f}  {ev['mean']:>8.4f}  "
              f"{ev['std']:>7.4f}  {best_total:>8.4f}  {comp_str}{marker}")

        # Record trial
        trial_record = {
            "trial":      trial_idx + 1,
            "phase":      "random" if trial_idx < n_random else "exploit",
            "total":      ev["total"],
            "mean":       ev["mean"],
            "std":        ev["std"],
            "per_seed":   ev["per_seed"],
            "components": ev["components_mean"],
            "elapsed_s":  round(elapsed_trial, 2),
            "is_best":    marker == " *",
        }
        all_trials.append(trial_record)

    total_elapsed = time.monotonic() - t0
    print()
    print(f"Completed {N_TRIALS} trials in {total_elapsed:.1f}s "
          f"({total_elapsed/N_TRIALS:.1f}s/trial)")
    print(f"Best total loss: {best_total:.4f}  "
          f"(baseline: {baseline_eval['total']:.4f}, "
          f"improvement: {baseline_eval['total'] - best_total:.4f})")
    print()

    # ---------------------------------------------------------------------------
    # Save results

    # 1. best_params.json
    best_params_dict = {name: round(getattr(best_params, name), 8)
                        for name, _, _ in PARAM_BOUNDS}
    best_params_path = RESULTS_DIR / "best_params.json"
    best_params_path.write_text(json.dumps(best_params_dict, indent=2))
    print(f"Saved: {best_params_path}")

    # Also write to optimization/ root for runner.py compatibility
    (OPT_DIR / "best_params.json").write_text(json.dumps(best_params_dict, indent=2))

    # 2. loss_breakdown.json
    best_loss_detail = {}
    for seed, world in worlds.items():
        try:
            result = simulate(world, best_params, seed=seed)
            lr = compute_loss(result, substrate=result.get("substrate"))
            best_loss_detail[str(seed)] = {
                "total":      round(lr.total, 6),
                "components": {k: round(v, 6) for k, v in lr.components.items()},
                "details":    {
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
    convergence = {
        "n_trials":        N_TRIALS,
        "seeds":           SEEDS,
        "variance_weight": VARIANCE_WEIGHT,
        "n_params":        len(PARAM_BOUNDS),
        "elapsed_s":       round(total_elapsed, 2),
        "baseline": {
            "total": baseline_eval["total"],
            "mean":  baseline_eval["mean"],
            "std":   baseline_eval["std"],
            "components": baseline_eval["components_mean"],
        },
        "best": {
            "trial":      next(t["trial"] for t in all_trials if t["is_best"] and
                               abs(t["total"] - best_total) < 1e-9),
            "total":      best_total,
            "mean":       best_eval["mean"],
            "std":        best_eval["std"],
            "components": best_eval["components_mean"],
            "per_seed":   best_eval["per_seed"],
        },
        "improvement":     round(baseline_eval["total"] - best_total, 6),
        "trials":          all_trials,
    }
    convergence_path = RESULTS_DIR / "convergence.json"
    convergence_path.write_text(json.dumps(convergence, indent=2))
    print(f"Saved: {convergence_path}")

    # 4. convergence_summary.txt  — human readable
    summary_lines = [
        "Aeolia History Engine — Optimization Results",
        "=" * 60,
        f"Trials         : {N_TRIALS}  ({n_random} random LHS + {N_EXPLOIT} exploit)",
        f"Seeds          : {SEEDS}",
        f"Parameters     : {len(PARAM_BOUNDS)}",
        f"Variance λ     : {VARIANCE_WEIGHT}",
        f"Total time     : {total_elapsed:.1f}s",
        "",
        "Baseline (default params):",
        f"  total={baseline_eval['total']:.4f}  "
        f"mean={baseline_eval['mean']:.4f}  std={baseline_eval['std']:.4f}",
        "  " + "  ".join(f"{k}={v:.4f}" for k, v in baseline_eval["components_mean"].items()),
        "",
        f"Best (trial #{convergence['best']['trial']}):",
        f"  total={best_total:.4f}  "
        f"mean={best_eval['mean']:.4f}  std={best_eval['std']:.4f}",
        "  " + "  ".join(f"{k}={v:.4f}" for k, v in best_eval["components_mean"].items()),
        f"  Improvement vs baseline: {baseline_eval['total'] - best_total:.4f}",
        "",
        "Per-seed losses (best params):",
    ]
    for seed_str, seed_data in best_loss_detail.items():
        if "total" in seed_data:
            summary_lines.append(f"  seed={seed_str}: total={seed_data['total']:.4f}  "
                                  + "  ".join(f"{k}={v:.4f}"
                                              for k, v in seed_data["components"].items()))
        else:
            summary_lines.append(f"  seed={seed_str}: ERROR {seed_data.get('error')}")

    summary_lines += [
        "",
        "Best parameter values (vs defaults):",
    ]
    default_vals = {name: getattr(DEFAULT_PARAMS, name) for name, _, _ in PARAM_BOUNDS}
    for name, lo, hi in PARAM_BOUNDS:
        best_val = best_params_dict[name]
        default_val = default_vals[name]
        delta = best_val - default_val
        pct = delta / max(abs(default_val), 1e-9) * 100
        flag = " <<<" if abs(pct) > 20 else ""
        summary_lines.append(
            f"  {name:<36s} best={best_val:>10.6f}  "
            f"default={default_val:>10.6f}  delta={delta:+.6f} ({pct:+.1f}%){flag}"
        )

    summary_text = "\n".join(summary_lines) + "\n"
    summary_path = RESULTS_DIR / "convergence_summary.txt"
    summary_path.write_text(summary_text)
    print(f"Saved: {summary_path}")
    print()
    print(summary_text)


if __name__ == "__main__":
    run()
