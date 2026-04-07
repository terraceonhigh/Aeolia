"""
10,000-trial batch optimizer for Aeolia history engine.

Strategy: 10 batches × 1000 trials. Each batch resets the TPE sampler
to escape local optima (basin-restart). Global best is tracked across
all batches. Each batch after the first is warm-started by enqueuing
the current global best, so TPE can exploit around it before exploring.

Usage:
    python3 run_batch_optimization.py

Results written to optimization/results/ (same schema as run_optimization.py).
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

OPT_DIR = Path(__file__).parent
sys.path.insert(0, str(OPT_DIR))

from sim_proxy import (
    SimParams, DEFAULT_PARAMS, PARAM_BOUNDS,
    generate_test_world, load_godot_world, simulate,
    pack_params, unpack_params,
)
from loss import (
    compute_loss, evaluate_seeds, LossWeights, DEFAULT_WEIGHTS,
    MultiSeedResult, run_nuclear_emergence_check,
)

RESULTS_DIR = OPT_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)
WORLDS_DIR  = OPT_DIR / "worlds"

# ---------------------------------------------------------------------------
# Config

N_BATCHES          = 10
N_TRIALS_PER_BATCH = 1000
N_STARTUP_TRIALS   = 80    # random exploration before TPE fires each batch
SEEDS              = [17, 42, 97, 137, 256]
VARIANCE_WEIGHT    = 0.30
FAIL_PENALTY       = 2.0

# ---------------------------------------------------------------------------

def _mean(xs): return sum(xs) / len(xs) if xs else 0.0
def _std(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return math.sqrt(_mean([(x - m) ** 2 for x in xs]))


def evaluate_params(params: SimParams, worlds: dict) -> dict:
    sim_outputs = {}
    for seed, world in worlds.items():
        try:
            world["_opt_seed"] = seed
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


def run():
    t0 = time.monotonic()

    print("Aeolia History Engine — Batch Optimizer")
    print(f"  Batches      : {N_BATCHES}")
    print(f"  Trials/batch : {N_TRIALS_PER_BATCH}  (total: {N_BATCHES * N_TRIALS_PER_BATCH})")
    print(f"  Startup/batch: {N_STARTUP_TRIALS}")
    print(f"  Seeds        : {SEEDS}")
    print(f"  Params       : {len(PARAM_BOUNDS)}")
    print(f"  Variance λ   : {VARIANCE_WEIGHT}")
    print()

    # Load worlds
    print("Loading worlds...")
    worlds = {}
    for seed in SEEDS:
        real_path = WORLDS_DIR / f"seed_{seed}.json"
        if real_path.exists():
            worlds[seed] = load_godot_world(str(real_path))
            src = "godot"
        else:
            worlds[seed] = generate_test_world(seed=seed)
            src = "synthetic"
        print(f"  seed={seed} [{src}]: {len(worlds[seed]['archs'])} archs, "
              f"{len(worlds[seed]['plateau_edges'])} edges")
    print()

    # Baseline
    print("Evaluating default params (baseline)...")
    baseline_eval = evaluate_params(DEFAULT_PARAMS, worlds)
    print(f"  Baseline total={baseline_eval['total']:.4f}  "
          f"mean={baseline_eval['mean']:.4f}  std={baseline_eval['std']:.4f}")
    top_comps = sorted(baseline_eval["components_mean"].items(), key=lambda x: -x[1])[:8]
    print("  Top components: " + "  ".join(f"{k}={v:.3f}" for k, v in top_comps))
    print()

    # Global tracking
    global_best_total  = float("inf")
    global_best_params = None   # dict of name→value
    all_batch_summaries = []
    all_trials: list[dict] = []
    trial_offset = 0

    print(f"{'Batch':>5}  {'Trial':>6}  {'Total':>8}  {'Mean':>8}  {'Std':>7}  {'GBest':>8}")
    print("-" * 60)

    for batch in range(N_BATCHES):
        t_batch = time.monotonic()
        batch_best = float("inf")

        sampler = optuna.samplers.TPESampler(
            seed=42 + batch * 1337,
            multivariate=True,
            n_startup_trials=N_STARTUP_TRIALS,
        )
        study = optuna.create_study(
            direction="minimize",
            study_name=f"aeolia_batch_{batch}",
            sampler=sampler,
        )

        # Warm-start: enqueue global best so TPE has a reference point
        if batch > 0 and global_best_params is not None:
            study.enqueue_trial(global_best_params)

        def objective(trial: optuna.Trial) -> float:
            x = [trial.suggest_float(name, lo, hi) for name, lo, hi in PARAM_BOUNDS]
            params = unpack_params(x)
            ev = evaluate_params(params, worlds)

            nonlocal batch_best, global_best_total, global_best_params
            is_batch_best = ev["total"] < batch_best
            if is_batch_best:
                batch_best = ev["total"]
            is_global_best = ev["total"] < global_best_total
            if is_global_best:
                global_best_total = ev["total"]
                global_best_params = {name: trial.params[name] for name, _, _ in PARAM_BOUNDS}

            abs_trial = trial_offset + trial.number + 1
            marker = " **" if is_global_best else (" *" if is_batch_best else "")
            print(f"{batch+1:>5}  {abs_trial:>6}  {ev['total']:>8.4f}  {ev['mean']:>8.4f}  "
                  f"{ev['std']:>7.4f}  {global_best_total:>8.4f}{marker}")

            all_trials.append({
                "batch":      batch + 1,
                "trial":      abs_trial,
                "total":      ev["total"],
                "mean":       ev["mean"],
                "std":        ev["std"],
                "per_seed":   ev["per_seed"],
                "components": ev["components_mean"],
                "is_best":    is_global_best,
            })
            return ev["total"]

        study.optimize(objective, n_trials=N_TRIALS_PER_BATCH, show_progress_bar=False)

        elapsed_batch = time.monotonic() - t_batch
        all_batch_summaries.append({
            "batch":       batch + 1,
            "batch_best":  round(batch_best, 6),
            "global_best": round(global_best_total, 6),
            "elapsed_s":   round(elapsed_batch, 2),
        })
        trial_offset += N_TRIALS_PER_BATCH

        print(f"  → Batch {batch+1} done in {elapsed_batch:.1f}s  "
              f"batch_best={batch_best:.4f}  global_best={global_best_total:.4f}")
        print()

    total_elapsed = time.monotonic() - t0
    total_trials  = N_BATCHES * N_TRIALS_PER_BATCH

    print(f"Completed {total_trials} trials in {total_elapsed:.1f}s "
          f"({total_elapsed/total_trials:.3f}s/trial)")
    print(f"Best total loss : {global_best_total:.4f}  "
          f"(baseline: {baseline_eval['total']:.4f}, "
          f"improvement: {baseline_eval['total'] - global_best_total:.4f})")
    print()

    # Reconstruct best params
    best_x      = [global_best_params[name] for name, _, _ in PARAM_BOUNDS]
    best_params = unpack_params(best_x)
    best_eval   = evaluate_params(best_params, worlds)

    # ── Save results ─────────────────────────────────────────────────────────

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
    best_trial_entry = next(
        (t for t in all_trials if t["is_best"] and abs(t["total"] - global_best_total) < 1e-9),
        all_trials[-1],
    )
    convergence = {
        "n_batches":       N_BATCHES,
        "n_trials_batch":  N_TRIALS_PER_BATCH,
        "total_trials":    total_trials,
        "seeds":           SEEDS,
        "variance_weight": VARIANCE_WEIGHT,
        "n_params":        len(PARAM_BOUNDS),
        "elapsed_s":       round(total_elapsed, 2),
        "backend":         "optuna-TPE-batch-restart",
        "baseline": {
            "total":      baseline_eval["total"],
            "mean":       baseline_eval["mean"],
            "std":        baseline_eval["std"],
            "components": baseline_eval["components_mean"],
        },
        "best": {
            "batch":      best_trial_entry["batch"],
            "trial":      best_trial_entry["trial"],
            "total":      global_best_total,
            "mean":       best_eval["mean"],
            "std":        best_eval["std"],
            "components": best_eval["components_mean"],
            "per_seed":   best_eval["per_seed"],
        },
        "improvement":    round(baseline_eval["total"] - global_best_total, 6),
        "batch_summaries": all_batch_summaries,
        "trials":          all_trials,
    }
    convergence_path = RESULTS_DIR / "convergence.json"
    convergence_path.write_text(json.dumps(convergence, indent=2))
    print(f"Saved: {convergence_path}")

    # 4. convergence_summary.txt
    milestone_steps  = {0, 99, 199, 499, 999, 1999, 4999, 9999, total_trials - 1}
    best_so_far = float("inf")
    milestone_lines = []
    for t in all_trials:
        if t["total"] < best_so_far:
            best_so_far = t["total"]
        if (t["trial"] - 1) in milestone_steps:
            milestone_lines.append(
                f"  trial {t['trial']:5d} (batch {t['batch']}): best_so_far={best_so_far:.4f}")

    default_vals = {name: getattr(DEFAULT_PARAMS, name) for name, _, _ in PARAM_BOUNDS}
    param_lines  = []
    for name, lo, hi in PARAM_BOUNDS:
        bv  = best_params_dict[name]
        dv  = default_vals[name]
        delta = bv - dv
        pct   = delta / max(abs(hi - lo), 1e-9) * 100
        flag  = " <<<" if abs(pct) > 20 else ""
        param_lines.append(
            f"  {name:<36s} best={bv:>10.6f}  "
            f"default={dv:>10.6f}  delta={delta:+.6f} ({pct:+.0f}% of range){flag}")

    gdscript_lines = []
    for name, lo, hi in PARAM_BOUNDS:
        bv = best_params_dict[name]
        dv = default_vals[name]
        if abs(bv - dv) / max(hi - lo, 1e-9) > 0.05:
            gdscript_lines.append(f"  var {name} := {bv:.6f}")

    summary_lines = [
        "Aeolia History Engine — Batch Optimization Results",
        "=" * 60,
        f"Backend        : Optuna TPE batch-restart ({N_BATCHES}×{N_TRIALS_PER_BATCH})",
        f"Total trials   : {total_trials}",
        f"Seeds          : {SEEDS}",
        f"Parameters     : {len(PARAM_BOUNDS)}",
        f"Variance λ     : {VARIANCE_WEIGHT}",
        f"Total time     : {total_elapsed:.1f}s  ({total_elapsed/total_trials:.3f}s/trial)",
        "",
        "Baseline (default params):",
        f"  total={baseline_eval['total']:.4f}  mean={baseline_eval['mean']:.4f}  std={baseline_eval['std']:.4f}",
        "  " + "  ".join(f"{k}={v:.4f}" for k, v in baseline_eval["components_mean"].items()),
        "",
        f"Best (batch {best_trial_entry['batch']}, trial #{best_trial_entry['trial']}):",
        f"  total={global_best_total:.4f}  mean={best_eval['mean']:.4f}  std={best_eval['std']:.4f}",
        "  " + "  ".join(f"{k}={v:.4f}" for k, v in best_eval["components_mean"].items()),
        f"  Improvement vs baseline: {baseline_eval['total'] - global_best_total:.4f}",
        "",
        "Per-seed losses (best params):",
    ]
    for seed_str, sd in best_loss_detail.items():
        if "total" in sd:
            summary_lines.append(
                f"  seed={seed_str}: total={sd['total']:.4f}  "
                + "  ".join(f"{k}={v:.4f}" for k, v in sd["components"].items()))
        else:
            summary_lines.append(f"  seed={seed_str}: ERROR {sd.get('error')}")

    summary_lines += [
        "",
        "Batch summary:",
    ] + [f"  batch {b['batch']:2d}: best={b['batch_best']:.4f}  global={b['global_best']:.4f}  {b['elapsed_s']:.1f}s"
         for b in all_batch_summaries]

    summary_lines += ["", "Convergence (best-so-far at milestones):"] + milestone_lines

    summary_lines += ["", "Best parameter values (vs defaults):"] + param_lines

    summary_lines += ["", "GDScript constants (|Δ| > 5% of range):"] + gdscript_lines

    summary_text = "\n".join(summary_lines) + "\n"
    summary_path = RESULTS_DIR / "convergence_summary.txt"
    summary_path.write_text(summary_text)
    print(f"Saved: {summary_path}")
    print()
    print(summary_text)


if __name__ == "__main__":
    run()
