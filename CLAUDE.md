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
│   │   ├── cardGenerator.js     # Situation card generator (11 card types, actionable responses)
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
│       ├── loss_v2.py           # Baseline Earth loss function (12 terms)
│       ├── optimizer_v2.py      # CMA-ES parameter optimizer
│       ├── worlds/              # RNG-seeded world JSON files (candidate_*.json)
│       ├── OPEN_QUESTIONS.md    # Design decisions — Q1-Q5 resolved, Q6-Q7 open
│       ├── SCRAMBLE_AND_DF_PROPOSAL.md  # 15-section design document
│       ├── FISHERIES_REFERENCE.md       # Six named marine species
│       ├── NON_STAPLE_CROPS_REFERENCE.md # Trade commodities with etymologies
│       ├── exponent_sweep.py            # Production function sweep experiment
│       ├── exponent_sweep_results.md    # Sweep analysis
│       └── worldbuilding/               # In-universe textbook chapters
├── TODO.md                      # Full project status and task queue
├── README.md                    # Project overview (game framing)
└── CLAUDE.md                    # You are here
```

## Simulation Architecture (sim_proxy_v2.py)

**SimParams:** 26 tunable parameters in a dataclass. All optimizer work targets this space.

**Tick pipeline (50-year resolution):**
1. **Stage 1 — Energy budget:** Crop yield × land + fish yield × coast = total calories. Malthusian clamp for tech < 4. Trade energy from three layers (Subsistence/Relay/Administered).
2. **Stage 2 — Culture & allocation:** 2D continuous culture space (Collective↔Individual × Inward↔Outward). Drift based on prosperity, crisis, trade exposure, resource stress, fishery type. Allocation shares (expansion/tech/consolidation) derived from position.
3. **Stage 3 — Expansion:** Controller map, conquest, absorption blending (0.95 core + 0.05 target).
4. **Stage 4 — Detection & awareness:** Dark Forest detection between nuclear-capable polities.
5. **Stage 5 — Tech growth & decay:** accel_rate table (5 regimes). Maintenance cost = tech² × rate. Tech decays when surplus < maintenance.
6. **Stage 6 — Desperation:** Resource pressure overrides allocation. Food/industrial/nuclear deficit hierarchy. Targeting bonus for resource-rich islands.

**Key mechanics:**
- Three-threshold resources: Detection (geology) → Exploitation (tech-gated) → Strategic Valuation (event-triggered)
- Naphtha scramble (tech ~5), pyra scramble (tech ~8), Dark Forest (two nuclear hegemons detect each other)
- Desperation cascade: surplus shortfall → tech decay → allocation override → aggressive expansion

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
- Event popups (first contact, absorption, territory lost, era transition, tech milestones, dark forest, defeat)
- Defeat condition on 0 territory

## Current State

**Working:** Sim runs, produces hegemons, all new mechanics (culture space, Malthusian clamp, trade energy, desperation) are implemented and validated on seed 216089. Narrative engine (`src/engine/narrativeText.js`) provides deterministic prose for all event types grounded in the series bible. Situation cards system (`src/engine/cardGenerator.js`) generates 11 card types with player-actionable responses. Event popups draw from `narrativeText.js` for varied, flavored text. Dispatches panel shows source-tagged intelligence feed (ADMIRALTY / MERCHANT GUILD / INTERNAL AFFAIRS / etc.).

**Broken:** Dark Forest doesn't fire. The culture space refactoring shifted the RNG sequence — the old optimized parameter vector no longer produces DF. This is a calibration problem, not a bug. The optimizer needs retuning with the new 26-parameter space.

**Next implementation round (from Lanthier consultation):** Disease mechanics, environmental shocks (crop failure, fishery depletion), religion/culture as political variable. See TODO.md. Also: Observatory/history viewer mode for the Lanthier presentation (timeline scrubber, tech curves, event markers).

## Running the Sim

```python
from sim_proxy_v2 import SimParams, simulate
import json

world = json.load(open('worlds/candidate_0216089.json'))
result = simulate(world, SimParams())
print(result.keys())  # states, polities, hegemon_tech, df_year, etc.
```

World files are `candidate_NNNNNN.json`, not `world_NNNNNN.json`.

## Running the Optimizer

```python
python3 optimizer_v2.py  # CMA-ES, runs indefinitely, Ctrl-C to stop
```

Results are printed to stdout. Best parameters are logged. For long runs, use tmux/nohup.

## Conventions

- Commodity names are canon from V1 sim_proxy.py maps (paddi, emmer, taro, sago, papa, nori, qahwa, char, kapas, seric, etc.)
- Fish species: sthaq (salmon), saak (eulachon), tunnu (tuna), sardai (sardine), bakala (cod), kauri (shellfish)
- Names are drawn from historical non-English trade languages — do not anglicize them
- The Fisher-Price problem: some over-eroded colonial-era names need consonant weight restored (see TODO.md)
