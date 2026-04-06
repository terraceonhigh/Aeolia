"""
Multi-seed composite loss for Aeolia history engine parameter optimization.

This module wraps loss.py (single-seed) and adds multi-seed evaluation with a
variance penalty term.  The full pipeline is:

    1. Run the simulation for N seeds → N sim_output dicts
    2. Call evaluate_seeds() → MultiSeedResult
    3. MultiSeedResult.total  is the Optuna objective value

Variance penalty rationale
--------------------------
Optimizing against seed 42 only risks overfitting to one world geometry.
Different seeds place the Reach and Lattice cores at different latitudes,
produce different plateau-edge graphs, and assign different crop zones to
the 42 archipelagos.  A parameter set that achieves low loss on seed 42 but
collapses on seed 137 is not a good parameter set.

Formula:
    total = mean(per_seed_losses) + variance_weight * std(per_seed_losses)

    variance_weight (λ) defaults to 0.30.  Raise it to suppress variance more
    aggressively; lower it if you want a seed-specific calibration pass.

Public API
----------
    evaluate_seeds(sim_outputs_by_seed, ...) -> MultiSeedResult
    MultiSeedResult.total               -> scalar for Optuna
    MultiSeedResult.per_seed            -> dict[seed, LossResult]
    MultiSeedResult.mean / .std / .total

Dependencies
------------
    loss.py        — compute_loss(), LoreTargets, LossWeights, LossResult
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

# Re-export everything from loss.py so callers need only one import.
from loss import (
    LoreTargets,
    LossWeights,
    LossResult,
    compute_loss,
    crop_distance,
    DEFAULT_TARGETS,
    DEFAULT_WEIGHTS,
)

__all__ = [
    # from loss.py
    "LoreTargets",
    "LossWeights",
    "LossResult",
    "compute_loss",
    "crop_distance",
    "DEFAULT_TARGETS",
    "DEFAULT_WEIGHTS",
    # this module
    "MultiSeedResult",
    "evaluate_seeds",
    "aggregate",
]


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class MultiSeedResult:
    """
    Aggregated loss across multiple simulation seeds.

    Attributes
    ----------
    per_seed : dict[int, LossResult]
        Per-seed loss results, keyed by seed integer.
    failed_seeds : list[int]
        Seeds that raised exceptions during simulation or loss computation.
    mean : float
        Arithmetic mean of per-seed weighted totals.
    std : float
        Sample standard deviation of per-seed weighted totals.
    variance_weight : float
        λ used when computing total.
    total : float
        mean + λ * std.  This is the value to minimize in Optuna.
    """
    per_seed:        dict       # int → LossResult
    failed_seeds:    list       # int list
    mean:            float
    std:             float
    variance_weight: float
    total:           float

    def __repr__(self) -> str:
        ok = len(self.per_seed)
        fail = len(self.failed_seeds)
        return (
            f"MultiSeedResult("
            f"total={self.total:.4f}  mean={self.mean:.4f}  std={self.std:.4f}  "
            f"seeds={ok} ok / {fail} failed)"
        )

    def summary(self, verbose: bool = False) -> str:
        lines = [
            f"Total loss : {self.total:.4f}",
            f"  mean     : {self.mean:.4f}",
            f"  std      : {self.std:.4f}  (λ={self.variance_weight})",
            f"  seeds    : {len(self.per_seed)} evaluated"
              + (f", {len(self.failed_seeds)} failed" if self.failed_seeds else ""),
        ]
        if verbose:
            lines.append("")
            for seed, result in sorted(self.per_seed.items()):
                lines.append(f"  seed={seed:6d}  total={result.total:.4f}  {result}")
        return "\n".join(lines)

    def component_means(self) -> dict:
        """Per-component weighted loss averaged across seeds."""
        if not self.per_seed:
            return {}
        keys = list(next(iter(self.per_seed.values())).components.keys())
        totals = {k: 0.0 for k in keys}
        for r in self.per_seed.values():
            for k, v in r.components.items():
                totals[k] += v
        n = len(self.per_seed)
        return {k: v / n for k, v in totals.items()}

    def component_stds(self) -> dict:
        """Per-component standard deviation across seeds."""
        if len(self.per_seed) < 2:
            return {}
        keys = list(next(iter(self.per_seed.values())).components.keys())
        means = self.component_means()
        sq_errs = {k: 0.0 for k in keys}
        for r in self.per_seed.values():
            for k, v in r.components.items():
                sq_errs[k] += (v - means[k]) ** 2
        n = len(self.per_seed)
        return {k: math.sqrt(v / n) for k, v in sq_errs.items()}


# ---------------------------------------------------------------------------
# Aggregation helper (can be called independently if you already have LossResults)
# ---------------------------------------------------------------------------

def aggregate(
    per_seed_results: dict,        # int → LossResult
    failed_seeds: list = (),
    variance_weight: float = 0.30,
    fail_penalty: float = 2.0,
) -> MultiSeedResult:
    """
    Aggregate a dict of {seed: LossResult} into a MultiSeedResult.

    Parameters
    ----------
    per_seed_results : dict[int, LossResult]
        Successful seed evaluations.
    failed_seeds : list[int]
        Seeds that failed.  Each contributes fail_penalty to the mean.
    variance_weight : float
        λ in total = mean + λ*std.
    fail_penalty : float
        Loss penalty assigned to each failed seed when computing mean.
        This makes failure costly without crashing the trial.

    Returns
    -------
    MultiSeedResult with .total ready for Optuna.
    """
    scalars = [r.total for r in per_seed_results.values()]
    # Failed seeds contribute a high constant loss to discourage param regions
    # that cause simulation failures (NaN, crash, timeout).
    for _ in failed_seeds:
        scalars.append(fail_penalty)

    if not scalars:
        return MultiSeedResult(
            per_seed={}, failed_seeds=list(failed_seeds),
            mean=float("inf"), std=0.0,
            variance_weight=variance_weight, total=float("inf"),
        )

    n = len(scalars)
    mean = sum(scalars) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in scalars) / n) if n >= 2 else 0.0
    total = mean + variance_weight * std

    return MultiSeedResult(
        per_seed=dict(per_seed_results),
        failed_seeds=list(failed_seeds),
        mean=mean,
        std=std,
        variance_weight=variance_weight,
        total=total,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def evaluate_seeds(
    sim_outputs_by_seed: dict,
    substrates_by_seed: Optional[dict] = None,
    weights: Optional[LossWeights]    = None,
    targets: Optional[LoreTargets]    = None,
    variance_weight: float = 0.30,
    fail_penalty:    float = 2.0,
) -> MultiSeedResult:
    """
    Evaluate composite lore-fidelity loss across multiple simulation seeds.

    Parameters
    ----------
    sim_outputs_by_seed : dict[int, dict]
        Mapping from seed integer to sim_output dict.
        Each sim_output must contain "states" and "df_year".
        Optional keys: "epi_log", "substrate", "reach_arch", "lattice_arch".
        See README.md for the full schema.

    substrates_by_seed : dict[int, list] | None
        Optional per-seed substrate lists (overrides sim_output["substrate"]).
        Pass None to use whatever is embedded in each sim_output.

    weights : LossWeights | None
        Component weights.  Defaults to DEFAULT_WEIGHTS from loss.py.

    targets : LoreTargets | None
        Lore reference values.  Defaults to DEFAULT_TARGETS from loss.py.

    variance_weight : float
        λ in total = mean + λ*std.  Default 0.30.

    fail_penalty : float
        Loss assigned to each seed that raises an exception.  Default 2.0.

    Returns
    -------
    MultiSeedResult
        .total       : scalar loss for Optuna (minimize this)
        .per_seed    : {seed: LossResult} for diagnostics
        .failed_seeds: seeds that raised exceptions

    Example
    -------
        outputs = {17: sim_out_17, 42: sim_out_42, 137: sim_out_137}
        result  = evaluate_seeds(outputs, variance_weight=0.30)
        print(result.total)         # pass to optuna
        print(result.summary())     # human-readable breakdown
    """
    per_seed: dict = {}
    failed:   list = []

    for seed, sim_output in sim_outputs_by_seed.items():
        try:
            substrate = None
            if substrates_by_seed:
                substrate = substrates_by_seed.get(seed)

            result = compute_loss(
                sim_output  = sim_output,
                substrate   = substrate,
                weights     = weights,
                targets     = targets,
            )
            per_seed[seed] = result

        except Exception as exc:                       # noqa: BLE001
            import sys
            print(f"  [evaluate_seeds] seed={seed} failed: {exc}", file=sys.stderr)
            failed.append(seed)

    return aggregate(per_seed, failed, variance_weight, fail_penalty)
