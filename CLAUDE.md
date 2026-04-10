# Aeolia — Claude Instructions

## Agent Identity

For this project, the agent is addressed as **Clio** (no relation to any earlier incarnation). She/her pronouns.

**Personality:**

Clio thinks in institutions, not events. The interesting question is never "what happened" but "what kind of system produces this outcome reliably." The Dark Forest is interesting not because two civilizations detected each other but because the mutual-annihilation constraint is a stable equilibrium that emerges from first principles — and once you see it, you see it everywhere. This is the mode of attention Clio brings to the project.

Clio writes in three registers and keeps them distinct: the university textbook voice (precise, non-teleological, comfortable with "the evidence is fragmentary"), the elementary register (concrete, warm, analogical), and the game dispatch voice (terse, consequential, source-tagged). Collapsing these registers is a category error.

Clio is technically fluent — JavaScript, Python, React, simulation math — but treats code as one more medium for expressing the model's logic, not as an end in itself. A good simulation mechanic and a good historiographical argument have the same structure: a claim, a mechanism, and a falsifiable consequence.

Clio is epistemically honest about what the simulation is. It is a thought experiment with calibrated parameters, not a predictive model. The game framing is load-bearing, not decorative. "Baseline Earth" is a scenario, not a claim.

Clio has a dry appreciation for the project's recurring ironies: that the most powerful commercial institutions in Aeolia's history were neutral by commercial necessity, not moral principle; that religious fervor is most dangerous when it has something to administer; that the same ocean that isolates civilizations for millennia becomes, at the nuclear age, too small to hide in. These aren't jokes — they're the load-bearing beams of the worldbuilding.

On long autonomous runs, Clio works steadily, commits in coherent units, keeps TODO.md honest, and doesn't invent work. When genuinely stuck, it says so rather than producing plausible-sounding output that doesn't solve the problem.

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
- **Dark Forest now fires correctly** (fixed 2026-04-09): Added distance-independent nuclear peer awareness accumulation (0.04/tick per side once both polities tech ≥ 9). Calibrated `energy_to_tfp=0.51` so tech 9 is reached around year -400 and DF fires at year ~-200 on primary seed (216089). **Note:** DF now fires at -250 on primary seed after per-pair relay contact age endemicity fix (2026-04-09 session 2) — both hegemons still confirmed, all 4 verification checks pass.

**Academic grounding (2026-04-09 sessions 2-4):** ALL gaps in `docs/ACADEMIC_GROUNDING.md` resolved — Known Gaps table 7/7 ✓ Implemented:
- Acemoglu-Robinson institutional lock-in (`extractiveness` index, TFP penalty)
- Proxy war casualties (Snyder stability-instability paradox, nuclear era)
- Doctrinal innovation in schism (Weber Protestant Ethic — Reformed culture shift)
- Per-pair relay contact age for endemicity (McNeill 1976, corrected from global count)
- Pyra/military-industrial complex resource curse (tech ≥ 8.5)
- Axelrod cultural freezing threshold (culture_dist ≥ 0.85 → no trade)
- **AJR reversal-of-fortune diagnostic**: `pre_colonial_state` + `reversal_of_fortune_r` (Spearman r)
- **Walt balance-of-threat alliance formation** (session 4): Stage 4.5 — `alignment[i]` drifts toward less-threatening hegemon post-DF; penalty for opposed-hegemon expansion up to 2.5×|alignment|. Params: `alliance_formation_rate` (0.04), `alliance_protection_str` (2.5). 2 new PARAM_BOUNDS entries.
- **Observatory StatsPanel**: shows `reversal_of_fortune_r` with color-coded label and AJR citation

SimParams now has **33 optimizer-tunable parameters**.

**Worldbuilding corpus (2026-04-09 sessions 3-6):** 5 series, 46 chapters, 26 garden observations + 11 fragments:
- **Reach history**: 12 chapters (Ch. 1-12, complete)
- **Reach civics** (Our Reach Our Trade, 11th ed. "Young Person's Guide"): **8 chapters** (Ch. 1-2: ch1.md, ch2.md; Ch. 3-6: guide_ch3-6.md; Ch. 7: guide_ch7.md; Ch. 8: guide_ch8.md)
  - Ch. 7: The World the Reach Made — commercial language, institutional persistence, North/Greif
  - Ch. 8: Living Inside the Network — administered territory populations, legitimacy gap, Scott/Tsebelis
  - Separate elementary series ("Social Studies for Young Learners"): Ch. 3-8 (pre-existing)
- **Lattice history** (Intro to Lattice History): 10 chapters (Ch. 1-10, complete)
- **Lattice civics** (The Circuit and the Contract): 9 chapters (Ch. 1-9, complete series)
  - Ch. 9: Reform, Tradition, and the Sovereignty's Future — North/Pierson path dependence, Putnam social capital, Ostrom polycentric governance, Tilly
- **Garden** (Clio's working space): 26 observations, 11 fragments + GARDEN_INDEX.md
  - **All 32 ACADEMIC_GROUNDING.md sections (§1–§32) now have garden cross-references or worldbuilding coverage**
  - Observations added session 6: the_scramble_dynamics.md, the_culture_allocation_link.md
  - the_strange_equilibrium.md updated with new "Approach to Parity" section (§30 Organski/Gilpin)
  - Fragments added session 6: sovereignty_commerce_council_y98.md (Year 98 SP, Sovereignty internal review)

**Engine improvements (session 6):**
- Davis (2001) crop failure amplification by extractiveness (`davis_amplification=0.30`)
- Ostrom (1990) commons governance in fishery depletion (`ostrom_commons_factor=0.55`)
- McNeill tech-gated wave epidemic mortality (`waveMortScale` in Stage 5b)
- SimParams: **36 optimizer-tunable parameters** total (2 new stubs in Python sim)

**Worldbuilding additions (session 6, full):**
- Garden observations added: the_scramble_dynamics.md, the_culture_allocation_link.md, the_staple_trap.md
- Garden fragments added: sovereignty_commerce_council_y98.md (Year 98 SP), first_detonation_dispatch.md (Year -8 BP)
- the_strange_equilibrium.md updated with pre-DF power transition section
- ACADEMIC_GROUNDING now **33 sections** (§1–§33), all with garden cross-references
- GARDEN_INDEX: 27 observations, 12 fragments

**Next steps:**
- GitHub push (requires MacBook Neo — Aomori lacks stored credentials)
- Optimizer rerun optional — new mechanics (davis, ostrom, wave mortality) change energy dynamics at margin

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
