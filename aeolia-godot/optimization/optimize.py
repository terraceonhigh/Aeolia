"""
Optimization runner: finds history-engine parameter values that minimise
the composite lore-fidelity loss.

Supports two backends:
  scipy.optimize  — gradient-based (L-BFGS-B) with finite-difference gradients
  optuna          — Bayesian TPE sampler (better for noisy / non-convex objectives)

The objective averages loss over multiple world seeds to avoid fitting to one
geometry — a parameter set that works for seed 42 but fails on 43 is not useful.

Usage (command-line)
--------------------
    python optimize.py --backend scipy --seeds 42 43 44
    python optimize.py --backend optuna --n-trials 200 --seeds 42 43 44 77 99
    python optimize.py --eval-default        # print loss for DEFAULT_PARAMS

Usage (import)
--------------
    from optimize import make_objective, run_scipy, run_optuna
    obj  = make_objective(seeds=[42, 43, 44])
    best = run_scipy(obj)           # returns optimized SimParams
    best = run_optuna(obj, n=200)   # returns optimized SimParams
"""

from __future__ import annotations

import argparse
import time
from typing import Optional

from loss import compute_loss, LossWeights, DEFAULT_WEIGHTS
from sim_proxy import (
    SimParams, DEFAULT_PARAMS, PARAM_BOUNDS,
    generate_test_world, simulate,
    pack_params, unpack_params, scipy_bounds,
)


# ---------------------------------------------------------------------------
# Objective function factory
# ---------------------------------------------------------------------------

def make_objective(
    seeds:   list  = None,
    weights: LossWeights = None,
    verbose: bool  = False,
):
    """
    Return an objective function  f(x) → float  suitable for scipy / optuna.

    The objective generates one world per seed, runs the simulation with the
    given parameter vector, and returns the mean loss.  Using multiple seeds
    prevents overfitting to a single geometry.

    Parameters
    ----------
    seeds   : list of ints — world seeds to average over (default [42, 43, 44])
    weights : LossWeights  — component weights (default DEFAULT_WEIGHTS)
    verbose : bool         — print per-seed details at each call

    Returns
    -------
    Callable[[array-like], float]
    """
    if seeds is None:
        seeds = [42, 43, 44]
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # Pre-generate worlds so they aren't regenerated on every call
    worlds = {s: generate_test_world(seed=s) for s in seeds}

    def objective(x) -> float:
        params = unpack_params(x)
        total  = 0.0
        for s in seeds:
            result  = simulate(worlds[s], params, seed=s)
            lr      = compute_loss(result, weights=weights)
            total  += lr.total
            if verbose:
                print(f"  seed={s}: {lr}")
        mean = total / len(seeds)
        if verbose:
            print(f"  mean loss: {mean:.4f}")
        return mean

    return objective


# ---------------------------------------------------------------------------
# Diagnostic: evaluate default parameters
# ---------------------------------------------------------------------------

def eval_default(seeds: list = None, verbose: bool = True) -> dict:
    """Evaluate DEFAULT_PARAMS and print a breakdown."""
    if seeds is None:
        seeds = [42, 43, 44]

    worlds = {s: generate_test_world(seed=s) for s in seeds}
    totals = []

    for s in seeds:
        result = simulate(worlds[s], DEFAULT_PARAMS, seed=s)
        lr     = compute_loss(result)
        totals.append(lr.total)
        if verbose:
            print(f"\n── seed {s} ──")
            print(lr.summary())

    mean = sum(totals) / len(totals)
    if verbose:
        print(f"\nmean loss across seeds {seeds}: {mean:.4f}")
    return {"mean": mean, "per_seed": dict(zip(seeds, totals))}


# ---------------------------------------------------------------------------
# scipy backend
# ---------------------------------------------------------------------------

def run_scipy(
    objective,
    x0:        Optional[list] = None,
    maxiter:   int            = 200,
    verbose:   bool           = True,
) -> SimParams:
    """
    Minimise objective with scipy.optimize.minimize (L-BFGS-B).

    Parameters
    ----------
    objective : callable — f(x) → float, from make_objective()
    x0        : initial parameter vector (defaults to DEFAULT_PARAMS)
    maxiter   : maximum iterations
    verbose   : print progress

    Returns
    -------
    SimParams — optimised parameter set
    """
    try:
        from scipy.optimize import minimize
    except ImportError:
        raise ImportError("scipy is required for the scipy backend: pip install scipy")

    if x0 is None:
        x0 = pack_params(DEFAULT_PARAMS)

    bounds = scipy_bounds()

    call_count = [0]
    t_start    = time.time()

    def wrapped(x):
        call_count[0] += 1
        loss = objective(x)
        if verbose and call_count[0] % 10 == 0:
            elapsed = time.time() - t_start
            print(f"  iter {call_count[0]:4d}  loss={loss:.4f}  t={elapsed:.1f}s")
        return loss

    if verbose:
        print(f"Starting L-BFGS-B optimisation over {len(PARAM_BOUNDS)} parameters …")
        print(f"Initial loss: {objective(x0):.4f}")

    result = minimize(
        wrapped,
        x0,
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": maxiter, "ftol": 1e-6, "gtol": 1e-5, "disp": verbose},
    )

    best = unpack_params(result.x)
    if verbose:
        print(f"\nOptimisation complete: loss={result.fun:.4f}  "
              f"({result.nit} iterations, success={result.success})")
        print(f"Message: {result.message}")
        _print_param_diff(DEFAULT_PARAMS, best)

    return best


# ---------------------------------------------------------------------------
# Optuna backend
# ---------------------------------------------------------------------------

def run_optuna(
    objective,
    n_trials: int  = 100,
    verbose:  bool = True,
    study_name: str = "aeolia-history-params",
) -> SimParams:
    """
    Minimise objective with optuna (TPE sampler — better for noisy objectives).

    Parameters
    ----------
    objective  : callable — f(x) → float, from make_objective()
    n_trials   : number of trials
    verbose    : show optuna progress bar and final report
    study_name : optuna study name

    Returns
    -------
    SimParams — optimised parameter set
    """
    try:
        import optuna
    except ImportError:
        raise ImportError("optuna is required for the optuna backend: pip install optuna")

    if not verbose:
        optuna.logging.set_verbosity(optuna.logging.WARNING)

    def trial_fn(trial: "optuna.Trial") -> float:
        x = [
            trial.suggest_float(name, lo, hi)
            for name, lo, hi in PARAM_BOUNDS
        ]
        return objective(x)

    if verbose:
        print(f"Starting Optuna TPE search: {n_trials} trials over "
              f"{len(PARAM_BOUNDS)} parameters …")

    study = optuna.create_study(
        direction="minimize",
        study_name=study_name,
        sampler=optuna.samplers.TPESampler(seed=0),
    )
    study.optimize(trial_fn, n_trials=n_trials, show_progress_bar=verbose)

    best_x = [study.best_params[name] for name, _, _ in PARAM_BOUNDS]
    best   = unpack_params(best_x)

    if verbose:
        print(f"\nBest loss: {study.best_value:.4f}")
        _print_param_diff(DEFAULT_PARAMS, best)

    return best


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _print_param_diff(default: SimParams, optimised: SimParams) -> None:
    """Print parameters that changed significantly from defaults."""
    print("\nParameter changes (|Δ| > 5% of range):")
    for name, lo, hi in PARAM_BOUNDS:
        d  = getattr(default,   name)
        o  = getattr(optimised, name)
        rng = hi - lo
        if rng == 0:
            continue
        if abs(o - d) / rng > 0.05:
            direction = "▲" if o > d else "▼"
            print(f"  {direction} {name:<35s}  {d:.5f} → {o:.5f}")


def _run_one_loop_demo(seeds: list = None) -> None:
    """
    Minimal self-contained demo: one optimisation loop with scipy, 50 iterations.
    Prints progress and the final parameter diff.
    """
    if seeds is None:
        seeds = [42, 43, 44]

    print("=" * 60)
    print("Aeolia history-engine parameter optimisation")
    print(f"Seeds: {seeds}  |  Parameters: {len(PARAM_BOUNDS)}")
    print("=" * 60)

    print("\n── Baseline (DEFAULT_PARAMS) ──")
    eval_default(seeds=seeds[:1], verbose=True)

    print("\n── Running scipy L-BFGS-B (50 iterations) ──")
    obj  = make_objective(seeds=seeds, verbose=False)
    best = run_scipy(obj, maxiter=50, verbose=True)

    print("\n── Evaluating optimised parameters ──")
    worlds = {s: generate_test_world(seed=s) for s in seeds}
    for s in seeds:
        result = simulate(worlds[s], best, seed=s)
        lr     = compute_loss(result)
        print(f"\nseed {s}:")
        print(lr.summary())


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Optimise Aeolia history-engine parameters for lore fidelity"
    )
    parser.add_argument(
        "--backend", choices=["scipy", "optuna"], default="scipy",
        help="Optimisation backend (default: scipy)"
    )
    parser.add_argument(
        "--seeds", nargs="+", type=int, default=[42, 43, 44],
        help="World seeds to average over (default: 42 43 44)"
    )
    parser.add_argument(
        "--n-trials", type=int, default=100,
        help="Number of optuna trials (optuna backend only)"
    )
    parser.add_argument(
        "--maxiter", type=int, default=200,
        help="Maximum iterations (scipy backend only)"
    )
    parser.add_argument(
        "--eval-default", action="store_true",
        help="Evaluate DEFAULT_PARAMS and exit"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="Run the one-loop demo and exit"
    )
    args = parser.parse_args()

    if args.eval_default:
        eval_default(seeds=args.seeds, verbose=True)
        return

    if args.demo:
        _run_one_loop_demo(seeds=args.seeds)
        return

    obj = make_objective(seeds=args.seeds, verbose=False)

    if args.backend == "scipy":
        best = run_scipy(obj, maxiter=args.maxiter, verbose=True)
    else:
        best = run_optuna(obj, n_trials=args.n_trials, verbose=True)

    # Print GDScript-ready constant lines for the changed parameters
    print("\n── GDScript constants to update ──")
    for name, lo, hi in PARAM_BOUNDS:
        d = getattr(DEFAULT_PARAMS, name)
        o = getattr(best, name)
        if abs(o - d) / max(hi - lo, 1e-9) > 0.02:
            print(f"  var {name} := {o:.5f}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 1:
        # No arguments: run the one-loop demo
        _run_one_loop_demo()
    else:
        main()
