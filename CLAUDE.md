# Aeolia — Claude Instructions

## What This Is

A civilization simulation engine modeling a 4.6× Earth circumference ocean world (~95% water, no continuous landmass). The world is archipelago-structured. The simulation runs a 10,000-year tick-based history, producing trade networks, resource scrambles, and nuclear deterrence equilibria.

This is framed as a **game / thought experiment**, not a research tool or predictive model. See the epistemology note in README.md.

## Repository Layout

```
Aeolia/
├── src/                         # Vite + React + Three.js web app
│   ├── GameApp.jsx              # Strategy game shell (useReducer, Three.js globe, fog of war)
│   ├── main.jsx                 # Mode selector (Observatory / Strategy)
│   ├── engine/
│   │   ├── SimEngine.js         # JS port of sim_proxy_v2.py with player interaction hooks
│   │   ├── narrativeText.js     # Deterministic prose library (no RNG; hash-based selection)
│   │   ├── cardGenerator.js     # Situation card generator (17 card types, actionable responses)
│   │   ├── world.js             # World generation (archipelagos, edges, substrate)
│   │   ├── constants.js         # Polity names, parameters
│   │   └── rng.js               # Mulberry32 PRNG
│   └── components/
│       ├── TurnDashboard.jsx    # Right panel: stats, timer, focus, diplomacy, culture, ops
│       ├── TurnTimer.jsx        # TOTP-style countdown ring (setInterval-based)
│       ├── EventPopup.jsx       # Modal overlays for game events
│       └── PolitySelect.jsx     # Starting archipelago picker
├── aeolia-godot/
│   └── optimization/
│       ├── sim_proxy_v2.py      # The simulation engine (Python reference)
│       ├── loss.py              # Baseline Earth loss function (12 terms)
│       ├── run_optimization.py  # Optuna-based parameter optimizer
│       ├── worlds/              # RNG-seeded world JSON files (candidate_*.json)
│       ├── OPEN_QUESTIONS.md    # Design decisions — Q1-Q7 all resolved (2026-04-09)
│       ├── SCRAMBLE_AND_DF_PROPOSAL.md  # 15-section design document
│       ├── FISHERIES_REFERENCE.md       # Six named marine species
│       ├── NON_STAPLE_CROPS_REFERENCE.md # Trade commodities with etymologies
│       ├── exponent_sweep.py            # Production function sweep experiment
│       ├── exponent_sweep_results.md    # Sweep analysis
│       └── worldbuilding/               # In-universe textbook chapters (12 chapters, 2 series)
├── TODO.md                      # Full project status and task queue
├── README.md                    # Project overview (game framing)
└── CLAUDE.md                    # You are here
```

## Simulation Architecture (sim_proxy_v2.py)

**SimParams:** 26 tunable parameters in a dataclass. All optimizer work targets this space.

**Tick pipeline (50-year resolution):**
0. **Environmental pre-pass:** Crop failure rolling and recovery; fishery stock update.
1. **Stage 1 — Energy budget:** Crop yield (×failure modifier) × land + fish yield (×fishery stock) × coast. Malthusian clamp for tech < 4. Trade energy from three layers (Subsistence/Relay/Administered).
2. **Stage 2 — Culture & allocation:** 2D continuous culture space (Collective↔Individual × Inward↔Outward). Drift from prosperity, crisis, trade exposure, resource stress, fishery type. Piety drift (Stage 2c): crisis→up, prosperity→down, tech>7→secular.
3. **Stage 3 — Expansion + Detection:** Rumor propagation, controller map, conquest, culture/piety absorption blending. Industrial signals build awareness (proximity-gated). Nuclear peer awareness builds globally (distance-independent, 0.04/tick per side) once both polities have tech ≥ 9.
4. **Stage 4 — Dark Forest detection:** Fires when nuclear peer awareness > 0.30 (no distance gate) or when pre-nuclear rival detects within proximity range.
5. **Stage 5 — Tech growth & decay:** accel_rate table (5 regimes). Post-DF arms race bonus for hegemons at tech > 8.5. Malaria cap penalty in population growth.
6. **Stage 5b — Epidemic waves:** Periodic disease events propagating through contact networks.
7. **Stage 6 — Expansion (targeting):** Thompson-sampling with piety bonus (missionary drive) and deterrence penalty (post-DF hegemon freeze, -12.0).
8. **Stage 7 — Sovereignty:** Extraction with piety absorption bonus (centripetal force mechanic).
9. **Stage 8 — Naphtha depletion.**

**Key mechanics:**
- Three-threshold resources: Detection (geology) → Exploitation (tech-gated) → Strategic Valuation (event-triggered)
- Naphtha scramble (tech ~5), pyra scramble (tech ~8), Dark Forest (two nuclear hegemons detect each other)
- Post-DF deterrence: hegemons frozen against each other (-12.0 targeting penalty); arms race continues (≤40% delta, capped 0.05/tick)
- Desperation cascade: surplus shortfall → tech decay → allocation override → aggressive expansion
- Disease: malaria belts (abs_lat < 20°), urban disease sink (density > 70%), epidemic waves (Stage 5b)
- Environmental shocks: crop failure (RNG per tick, tech-gated recovery), fishery depletion (stock-and-flow)
- Religion/piety: centripetal force — crisis drives fervor, fervor drives absorption + expansion

## Web App (Strategy Game Mode)

**Stack:** Vite + React + Three.js + bun (npm blocked by hooks)

**Run:** `bun run dev` (port 5173)

**Game flow:** Main menu → Strategy → Pick archipelago → Turn-based play (50-year ticks, timer-driven)

**Player decision object** passed to `SimEngine.advanceTick()`:
```javascript
{
  expansion, techShare, consolidation,  // allocation shares (from National Focus)
  targets: number[],                     // expansion target archipelagos
  embargoTargets: number[],              // cores to block trade with
  culturePolicyCI: number,               // culture nudge: -1 (collectivist) to +1 (individualist)
  culturePolicyIO: number,               // culture nudge: -1 (inward) to +1 (outward)
  sovFocusTargets: number[],             // islands to prioritize consolidation on
  scoutActive: boolean,                  // expand fog of war by one hop
  rivalCores: number[],                  // cores to target preferentially in expansion
  partnerCores: number[],               // cores to avoid targeting + trade bonus
}
```

**5 interaction mechanics (engine hooks):**
1. **Trade Embargo** — skips trade pair in trade pre-pass for embargoed cores
2. **Cultural Policy** — ±30% of `culture_drift_rate` nudge per tick on CI/IO axes
3. **Sovereignty Focus** — 60% extraction reduction on focused islands (faster stabilization)
4. **Scout/Explore** — extends fog-of-war frontier by one extra adjacency hop
5. **Diplomacy Stance** — rivals get +2.0 expansion targeting bonus; partners get -3.0 penalty + 30% trade bonus

**UI features:**
- Antique cartography colorway (parchment ocean, dark ink landmasses)
- TOTP-style turn timer with speed controls (pause/1x/5x/10x)
- National Focus cards (Expand/Innovate/Fortify/Balanced/Exploit)
- Fog of war with 5 visibility levels (owned/frontier/contacted/rumor/unknown)
- Event popups: first contact (tech-gated: pre-industrial vs. nuclear-era variants), absorption, territory lost, era transition, tech milestones, dark forest (deterrence + arms race text), naphtha/pyra scramble, epidemic wave, fishery collapse, schism, defeat
- 18 situation cards (cardGenerator.js): tech assessment, resource detection, expansion opportunity, culture drift, epidemic risk, naphtha/pyra, era transition, administered trade, fishery collapse, piracy warning, tech decay, navigator guild dispute, malaria breakthrough, religious revival, rogue aircraft alert, schism warning
- Dispatches panel: ADMIRALTY / MERCHANT GUILD / INTERNAL AFFAIRS source-tagged intelligence feed
- Player stats panel: piety reading (fervent/devout/moderate/secular) with color coding
- Defeat condition on 0 territory
- Observatory mode: 3-chart panel (tech/pop/piety) + equirectangular world map + event timeline + scrubber

## Current State

**Working:** Full simulation pipeline with all Lanthier consultation targets implemented (2026-04-09):
- Disease mechanics: malaria belts, epidemic waves, urban disease sink
- Environmental shocks: crop failure, fishery depletion
- Religion/piety: centripetal force, missionary expansion, absorption bonus
- Post-DF deterrence: hegemons frozen against each other; arms race continues
- Observatory mode: 3-chart panel (tech/pop/piety) + world map + event timeline + scrubber
- 17 situation cards, 10+ popup types, source-tagged dispatches feed
- **Dark Forest now fires correctly** (fixed 2026-04-09): Added distance-independent nuclear peer awareness accumulation (0.04/tick per side once both polities tech ≥ 9). Calibrated `energy_to_tfp=0.51` so tech 9 is reached around year -400 and DF fires at year -200 on primary seed (216089).

**Next steps:**
- Run optimizer (run_optimization.py, 10K trials) to further refine all 26 parameters
- GitHub push (requires MacBook Neo — Aomori lacks stored credentials)

## Running the Sim

```python
from sim_proxy_v2 import SimParams, simulate
import json

world = json.load(open('worlds/candidate_0216089.json'))
result = simulate(world, SimParams())
print(result.keys())  # states, polities, df_year, hegemons, etc.
```

World files are `candidate_NNNNNN.json`, not `world_NNNNNN.json`.

## Running the Optimizer

```python
# From aeolia-godot/optimization/
python3 run_optimization.py              # full 10K run
python3 run_optimization.py --test 100   # quick 100-trial test
```

Results saved to `results/`. For long runs, use tmux/nohup.

Quick seed scan:
```python
from sim_proxy_v2 import SimParams, simulate
import json
from pathlib import Path
for wf in sorted(Path('worlds').glob('candidate_*.json')):
    r = simulate(json.loads(wf.read_text()), SimParams())
    if r['df_year']:
        print(f"DF seed {int(wf.stem.split('_')[1])}: year {r['df_year']}, {len(r['hegemons'])} hegemons")
```

## Session Management for Unattended Runs

During long autonomous or unattended development sessions, Claude must manage the 5-hour usage window to prevent premature termination.

**Periodic usage check cadence:** Every ~20 tool uses (roughly every significant work block), run:
```bash
date && bunx ccusage
```

**Thresholds and actions:**

| Usage level | Action |
|-------------|--------|
| < 70% | Continue normally |
| 70–89% | Note remaining capacity in next commit message or comment; prefer smaller scoped tasks |
| ≥ 90% | **Stop work immediately.** Commit all staged changes, write a brief status summary of what was done and what's next to TODO.md, then stop. Do not start new work. |

**What `bunx ccusage` reports:** Token usage and elapsed time against the 5-hour rolling window. If the command is unavailable or returns an error, fall back to checking elapsed time via `date` and estimating conservatively (assume heavy usage if uncertain).

**Compaction:** If context is growing large but usage is under 90%, compaction is preferable to stopping. Note in the session that compaction is needed and allow it to proceed.

**Goal:** Uninterrupted programming over days. The priority order is: finish the current unit of work → commit → check usage → decide whether to continue.

## Conventions

- Commodity names are canon from V1 sim_proxy.py maps (paddi, emmer, taro, sago, papa, nori, qahwa, char, kapas, seric, etc.)
- Fish species: sthaq (salmon), saak (eulachon), tunnu (tuna), sardai (sardine), bakala (cod), kauri (shellfish)
- Names are drawn from historical non-English trade languages — do not anglicize them
- The Fisher-Price problem: some over-eroded colonial-era names need consonant weight restored (see TODO.md)
