# Aeolia History Engine — Parameter Optimisation

Finds history-engine coefficient values that produce lore-accurate simulation outcomes.
Written in Python so it can plug directly into `scipy.optimize` or `optuna` without
modifying the Godot project.

---

## Files

| File | Purpose |
|------|---------|
| `loss.py` | Composite lore-fidelity loss (6 components, documented/weightable) |
| `loss_function.py` | Multi-seed wrapper: `evaluate_seeds()` + variance-penalty `aggregate()` |
| `sim_proxy.py` | Python port of `history_engine.gd` + `substrate.gd` with all magic numbers in `SimParams` |
| `optimize.py` | Optimization runner: scipy L-BFGS-B and optuna TPE backends (mean aggregation) |
| `runner.py` | Optuna-only harness using `loss_function.py`: mean + λ·std multi-seed objective, 26-param `PARAM_SPACE`, Godot subprocess support |
| `thin_sim.py` | Parameterized Python port (Phases 1–5) that accepts pre-exported worlds; 70-param `DEFAULT_PARAMS` |
| `params.py` | 65-dimensional `PARAM_SPACE` for `thin_sim.py`; Optuna/scipy helper functions |
| `make_test_world.py` | Converts a `sim_proxy` synthetic world to `thin_sim` JSON format (no Godot required) |
| `run_headless.gd` | GDScript headless exporter: exports full world JSON for `thin_sim.py` or `runner.py` |

---

## Quick start

```bash
pip install scipy optuna          # both optional — only the one you use is required

# Evaluate default parameters against lore targets
python3 optimize.py --eval-default

# One full optimization loop (scipy, 3 seeds, 200 iterations)
python3 optimize.py --backend scipy --maxiter 200 --seeds 42 43 44

# Bayesian search with optuna (better for noisy / non-convex objectives)
python3 optimize.py --backend optuna --n-trials 300 --seeds 42 43 44 77 99

# No arguments = quick demo (1 seed, 50 scipy iterations)
python3 optimize.py
```

---

## Multi-seed variance penalty (`loss_function.py` / `runner.py`)

`optimize.py` averages loss across seeds to avoid fitting to one world geometry.
`runner.py` goes further with an explicit variance penalty:

```
total = mean(per_seed_loss) + λ · std(per_seed_loss)
```

λ defaults to **0.30**.  A parameter set that achieves low loss on seed 42 but
collapses on seed 137 is not acceptable — different seeds produce different
plateau graphs, different hegemon core latitudes, and different crop-zone
assignments.  The variance term penalises instability directly.

```python
from loss_function import evaluate_seeds

outputs = {17: sim_out_17, 42: sim_out_42, 137: sim_out_137}
result  = evaluate_seeds(outputs, variance_weight=0.30)
print(result.total)           # scalar for Optuna
print(result.summary())       # mean, std, per-seed breakdown
print(result.component_means())
```

```bash
# runner.py — smoke-test without Godot:
python3 runner.py --n-trials 20 --n-seeds 4 --stub --verbose

# Real run (requires run_headless.gd):
GODOT_BIN=/path/to/godot4 python3 runner.py --n-trials 200 --n-seeds 12

# Tune only epi params first (staged approach):
python3 runner.py --n-trials 80 \
  --params-subset epi_base_severity_lo,epi_base_severity_range \
  --weights '{"epi":4.5}'

# Print best params from a stored study:
python3 runner.py --best --storage sqlite:///study.db
```

---

## Architecture

```
generate_test_world(seed)           # synthetic world: archs, plateau_edges, substrate
        |
simulate(world, params, seed)       # Python port of history_engine.assign_politics()
        |                           # returns: states, df_year, epi_log, substrate
compute_loss(sim_output, substrate) # 6-component lore-fidelity loss -> LossResult
        |
scipy.minimize / optuna.optimize    # search over SimParams
```

The Python simulation is a faithful port of `history_engine.gd` with every magic
number exposed as a `SimParams` field.  `Mulberry32` is ported from `rng.gd` and
produces identical outputs for identical seeds.

The objective averages loss over multiple seeds to avoid fitting to one world
geometry.

---

## Loss components

All components return values in [0, ~5] before weighting.

| Component | Weight | What it measures | Key lore source |
|-----------|--------|-----------------|-----------------|
| `geo` | 1.0 | Contact fraction (~75%), sphere balance, 3-5 independent powers | `docs/02`, `DESIGN_SPEC §0` |
| `ag` | 1.0 | Reach=emmer, Lattice=paddi, yield ratio ~2.0, crop diversity | `docs/03`, `docs/04`, `substrate.gd` |
| `tech` | 1.0 | Reach 10.0 / Lattice 9.5, gap 0.3-0.8, independent powers 6.5-8.5 | `DESIGN_SPEC §5`, ERA 5 |
| `poleco` | 1.5 | Dark Forest -200 to -40 BP, era distribution, sovereignty targets | `docs/09`, phases 2-3 |
| `epi` | 1.5 | Crop-distance mortality: same-crop <=9%, paddi<->papa 20-45% | `DESIGN_SPEC §10a`, `ANALYSIS §3` |
| `pop` | 1.0 | Lattice:Reach ratio 1.2-2.2, Gini 0.35-0.70, colony recovery | `docs/04`, `DESIGN_SPEC §5` |

Weights are higher for `poleco` and `epi` because these correspond to the
highest-priority lore misalignments in `HISTORY_ENGINE_ANALYSIS.md`.

Override weights:
```python
from loss import compute_loss, LossWeights
result = compute_loss(sim_output, weights=LossWeights(epi=3.0, poleco=2.0))
print(result.summary())
```

Override lore targets:
```python
from loss import LoreTargets
targets = LoreTargets(df_year_max=-100, lattice_reach_ratio_min=1.5)
```

---

## Parameters being optimised

`SimParams` exposes 28 tunable coefficients across 5 simulation eras.
From `HISTORY_ENGINE_ANALYSIS.md`, highest-priority targets:

### Epidemiology (highest priority — ANALYSIS §3)
| Param | Default | Range | Why |
|-------|---------|-------|-----|
| `serial_shock_base_min` | 0.20 | [0.10, 0.35] | Base mortality before crop-distance scaling |
| `serial_shock_base_range` | 0.25 | [0.10, 0.40] | Max-distance (paddi<->papa) must reach 20-45% |
| `reach_serial_log_coeff` | 0.30 | [0.10, 0.60] | Must be > lattice (Reach delta=0.08) |
| `lattice_serial_log_coeff` | 0.12 | [0.03, 0.30] | Must be < reach (Lattice delta=0.04) |

### Industrial compounding (high priority — ANALYSIS §7)
| Param | Default | Range | Why |
|-------|---------|-------|-----|
| `reach_ind_tech_mult` | 0.12 | [0.04, 0.25] | Reach industrialises faster (A0=1.2) |
| `lattice_ind_tech_mult` | 0.06 | [0.02, 0.15] | Lattice slower tech leverage (A0=0.8) |
| `lattice_ind_pot_mult` | 0.22 | [0.10, 0.40] | Lattice higher resource leverage (beta=0.6) |
| `antiquity_lattice_pop_mult` | 2.5 | [1.5, 4.0] | Paddi surplus demographic dominance |

---

## Applying results to GDScript

After optimisation, `optimize.py` prints GDScript-ready constant lines:

```
-- GDScript constants to update --
  var serial_shock_base_min := 0.18432
  var reach_serial_log_coeff := 0.34871
  ...
```

Copy these into the relevant ERA blocks in `history_engine.gd`.

---

## Using Godot-exported world data

The loss function accepts any dict matching the history-engine output schema.
Export from Godot and evaluate directly:

```python
import json
from loss import compute_loss

with open("world_export.json") as f:
    export = json.load(f)

result = compute_loss(export, substrate=export.get("substrate"))
print(result.summary())
```

### Note on the `ag` component

Crop assignments are determined by geography (latitude, shelf_r, peaks height)
through the substrate model -- they are NOT a function of `SimParams`.

For test worlds from `generate_test_world()`, the simplified substrate proxy
(no gyre model) can give nori at the Reach when edge count is high, because
nori's upwelling-scaled yield formula beats emmer's yield at those edge counts.
This produces a constant ag loss offset that does not affect optimisation
gradients for the other 5 components.

For production runs, use Godot-exported world data where the full gyre model
correctly assigns emmer/paddi to the Reach/Lattice cores.

### Note on the `epi` component

The `epi_log` key (per-contact mortality records) is produced by `sim_proxy.simulate()`
but not by the Godot engine.  To enable the precise epi component against Godot output,
add epi logging to `history_engine.gd` (track contactor/contacted crop and mortality
per contact event) and include it in the JSON export.  Without `epi_log`, the epi
component degrades to a population-depression proxy.

---

## Extending the loss

Each component is a standalone function returning `(float, dict)`.

Add a new component:
1. Write `my_component(states, ..., targets) -> tuple` in `loss.py`
2. Add a weight field to `LossWeights`
3. Call it in `compute_loss()` and add to `components` dict

Add a new tunable parameter:

**`optimize.py` / `sim_proxy.py` route:**
1. Add a field to `SimParams` in `sim_proxy.py`
2. Add a `(name, lo, hi)` entry to `PARAM_BOUNDS`
3. Use the field in the relevant ERA block of `simulate()`

**`runner.py` / Godot subprocess route:**
1. Add an entry to `PARAM_SPACE` in `runner.py`
2. Override the corresponding constant in `run_headless.gd`

---

## `run_headless.gd` output schema

`runner.py` expects this JSON written to `--out`:

```jsonc
{
    "states": [
        { "faction": "reach", "status": "core", "name": "The Reach",
          "population": 12345, "tech": 10.0, "sovereignty": 1.0,
          "tradeIntegration": 0.80, "eraOfContact": null, "hopCount": 0 }
    ],
    "df_year":      -180,   // null if Dark Forest never fired
    "reach_arch":   0,
    "lattice_arch": 1,
    "epi_log": [            // optional — enables precise epi component
        { "arch": 5, "contactor_crop": "emmer", "contacted_crop": "paddi",
          "mortality_rate": 0.38 }
    ],
    "substrate": [          // optional — enables ag component
        { "crops": { "primary_crop": "paddi", "primary_yield": 5.0 },
          "tradeGoods": { "totalTradeValue": 0.72 } }
    ]
}
```

Without `epi_log`, epi degrades to a population-depression proxy.
Without `substrate`, ag is skipped (0 loss, not penalised).

---

## Third path: offline JSON worlds + thin_sim.py

`sim_proxy.py` generates world geometry in Python (fast, no Godot).
`thin_sim.py` is an alternative that loads pre-computed worlds and re-runs
only the population model, so the Godot-accurate substrate/gyre crops are
preserved while the optimizer iterates at Python speed.

```bash
# Option A: synthetic worlds (no Godot, for rapid testing)
python3 make_test_world.py 42 137 1000 9999 --output-dir optimization/worlds/

# Option B: real Godot worlds (accurate gyre/substrate)
for s in 42 137 1000 9999; do
  godot --headless --path . -- --seed $s \
        --output optimization/worlds/seed_$s.json
done

# Evaluate default params against a world
python3 thin_sim.py optimization/worlds/seed_42.json

# Run optimization (optuna) across multiple seeds
python3 - <<'EOF'
import json, optuna
from thin_sim import simulate
from loss import compute_loss
from params import suggest_params

SEEDS = [42, 137, 1000, 9999]
worlds = {}
for s in SEEDS:
    with open(f"optimization/worlds/seed_{s}.json") as f:
        worlds[s] = json.load(f)

def objective(trial):
    p = suggest_params(trial)
    total = 0.0
    for s, w in worlds.items():
        r = simulate(w, p, rng_seed=s)
        total += compute_loss(r, substrate=r["substrate"]).total
    return total / len(worlds)

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=300)
print(study.best_params)
EOF
```

### When to use which path

| Path | Speed | Accuracy | Godot needed |
|------|-------|----------|--------------|
| `sim_proxy` + `optimize.py` | fastest | Python substrate proxy | no |
| `thin_sim` + `params.py` + real worlds | fast | exact Godot substrate/crops | pre-generate |
| `runner.py` + Godot subprocess | slow | exact GDScript simulation | yes |

### Note on substrate format

`compute_loss` accepts substrate in both formats:
- **Nested** (sim_proxy): `substrate[i]["crops"]["primary_crop"]`
- **Flat** (thin_sim / run_headless.gd): `substrate[i]["primary_crop"]`

The normalization happens automatically inside `compute_loss`.

---

## Bug fixes applied

**`loss.py` — independent powers definition** (`geo_component`, `tech_component`)

The original code counted independent powers as `faction == "unknown"`, which
selects *uncontacted* archs (tech ~2–4, default values).  Per DESIGN_SPEC §0 the
correct definition is contacted archs with high autonomy:

```python
status in {"contacted", "client", "pulse"} and tech > 6.0 and sovereignty > 0.7
```

With the old code the geo and tech components never penalised for zero independent
powers, so the optimizer had no gradient toward the 3–5 required by the lore.
