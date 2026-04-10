# Aeolia

**A procedural civilization game that generates trade networks, resource scrambles, and nuclear deterrence on fictional archipelago worlds.**

Aeolia is a thought experiment in game form. It generates planets — randomized archipelago geographies with distinct climates, crops, and resource endowments — then simulates 10,000 years of geopolitical history. Civilizations trade, expand, colonize, and eventually discover nuclear fission, at which point the system models a deterrence standoff. This is a **game, not a predictive model** — it explores what *could* happen under simplified assumptions on a world very different from our own.

---

## Quick Start (Web App)

**Requirements:** [Bun](https://bun.sh) (npm is blocked by project hooks — use `bun` everywhere)

```bash
# Install dependencies
bun install

# Start the dev server
bun run dev
# → Opens at http://localhost:5173
```

### Two game modes

| Mode | What it does |
|------|--------------|
| **Observatory** | Runs a full 10,000-year AI simulation. Watch it unfold, scrub through the timeline, inspect tech/population/piety charts. No interaction required. |
| **Strategy** | You play as one polity. Make decisions every turn (50-year tick). Manage trade, expansion, culture, diplomacy. |

### Observatory mode

1. Click **Observatory** from the main menu
2. The simulation runs automatically — watch the world map fill in
3. Use the **timeline scrubber** at the bottom to jump to any year
4. The **three-chart panel** shows tech / population / piety over time for each polity
5. The **event timeline** shows major events (DF firing, scrambbles, collapses)
6. The **polity standings** panel ranks civilisations by tech and territory

### Strategy mode

1. Click **Strategy** → pick a starting archipelago from the **polity picker**
2. Each turn: a 50-year timer counts down (pause / 1× / 5× / 10× speed controls)
3. **Situation cards** appear at the bottom — each has actionable choices
4. The **right panel** shows: stats, national focus, diplomacy, culture position, ops, dispatches
5. The game ends on **defeat** (0 territory held)

#### Key controls
- **National Focus** — drag the allocation bar to set Expansion / Innovate / Fortify / Balanced / Exploit
- **Dispatches** — intelligence feed tagged by source (ADMIRALTY / MERCHANT GUILD / INTERNAL AFFAIRS)
- **Fog of War** — 5 visibility levels; use Scout action to extend frontier visibility
- **Diplomacy** — mark polities as Rivals (+2 targeting) or Partners (−3 targeting, +30% trade)

---

## Running the Python Simulation Engine

The Python sim is the reference engine used by the optimizer. It runs independently of the web app.

```python
# From aeolia-godot/optimization/
from sim_proxy_v2 import SimParams, simulate
import json

world = json.load(open('worlds/candidate_0216089.json'))
result = simulate(world, SimParams())
print(result.keys())
# → states, polities, df_year, hegemons, reversal_of_fortune_r, …
```

**World files** are `candidate_NNNNNN.json` — not `world_NNNNNN.json`.

**Quick seed scan** (find seeds that produce a Dark Forest):
```python
from sim_proxy_v2 import SimParams, simulate
import json
from pathlib import Path

for wf in sorted(Path('worlds').glob('candidate_*.json')):
    r = simulate(json.loads(wf.read_text()), SimParams())
    if r['df_year']:
        print(f"DF seed {int(wf.stem.split('_')[1])}: year {r['df_year']}, {len(r['hegemons'])} hegemons")
```

**Primary demo seed:** `candidate_0216089.json` — Dark Forest fires at year −250, two hegemons confirmed.

### Running the optimizer

```bash
cd aeolia-godot/optimization/
python3 run_optimization.py              # full 10K-trial Optuna run
python3 run_optimization.py --test 100   # quick 100-trial test
```

Results saved to `results/`. For long runs use tmux/nohup.

---

## Project Layout

```
Aeolia/
├── src/                         # Vite + React + Three.js web app
│   ├── GameApp.jsx              # Strategy game shell (useReducer, Three.js globe, fog of war)
│   ├── main.jsx                 # Mode selector (Observatory / Strategy)
│   └── engine/
│       ├── SimEngine.js         # JS simulation engine (tick-based, player interaction hooks)
│       ├── narrativeText.js     # Deterministic prose library (hash-based, no RNG)
│       ├── cardGenerator.js     # 18 situation card types with actionable responses
│       ├── world.js             # World generation (30 archipelagos, climate, substrate)
│       ├── constants.js         # Polity names, era names
│       └── rng.js               # Mulberry32 PRNG (deterministic by seed)
├── aeolia-godot/
│   └── optimization/
│       ├── sim_proxy_v2.py      # Python reference simulation engine (33 SimParams)
│       ├── loss.py              # Baseline Earth loss function (12 terms)
│       ├── run_optimization.py  # Optuna TPE parameter optimizer
│       ├── worlds/              # RNG-seeded world JSON files (candidate_*.json)
│       ├── ACADEMIC_GROUNDING.md # 33-section citation map for all mechanics
│       └── worldbuilding/       # In-universe textbook chapters (5 series, 46+ chapters)
├── garden/                      # Analytical observations and primary-source fragments
│   ├── observations/            # 27 mechanic-by-mechanic academic analyses
│   ├── fragments/               # 12 in-universe historical documents (−240 BP → +140 SP)
│   └── GARDEN_INDEX.md          # Navigable index
├── docs/
│   └── ACADEMIC_GROUNDING.md   # Full citation map (§1–§33)
├── TODO.md
└── CLAUDE.md                    # AI session instructions
```

---

## Academic Foundations

The simulation draws on established scholarly frameworks. Each mechanic in `SimEngine.js` carries an inline citation. Full detail in `docs/ACADEMIC_GROUNDING.md`.

| Mechanic | Framework | Key source |
|----------|-----------|------------|
| Energy budget | Energy as production factor | Ayres & Warr (2005) |
| Tech growth | Solow + Romer endogenous growth | Solow (1956), Romer (1990) |
| Tech decay | Diminishing returns on complexity | Tainter (1988) |
| Trade layers | Subsistence / Relay / Administered | Braudel (1949), Abu-Lughod (1989), Wallerstein (1974) |
| Terms of trade | Prebisch-Singer bulk discount | Prebisch (1950), Singer (1950) |
| Relay asymmetry | Maghribi trader coalition | Greif (1989) |
| Culture drift | Dissemination of culture | Axelrod (1997), Inglehart (1997) |
| Piety dynamics | Sacred and Secular | Norris & Inglehart (2004) |
| Schism | "Tilly Goes to Church" | Grzymala-Busse (2023) |
| Malthusian clamp | Population and carrying capacity | Malthus (1798), Boserup (1965) |
| First contact epidemics | Virgin-soil epidemics | Diamond (1997), McNeill (1976) |
| Resource curse | Natural resource abundance | Sachs & Warner (1995), Ross (2012) |
| Institutional lock-in | Why Nations Fail | Acemoglu & Robinson (2012) |
| Resistance | Weapons of the Weak | Scott (1985, 1990) |
| IR posture | Offensive realism / bandwagoning | Mearsheimer (2001), Schweller (1994) |
| Alliance formation | Balance of threat | Walt (1987) |
| Deterrence | Strategy of Conflict | Schelling (1960, 1966) |
| Stability-instability | Nuclear paradox | Snyder (1965), Waltz (1981) |
| Crop failure | Times of Feast, Times of Famine | Le Roy Ladurie (1967), Davis (2001) |
| Fishery commons | Governing the Commons | Hardin (1968), Ostrom (1990) |
| Power transition | Approach to parity | Organski (1958), Gilpin (1981) |

---

## Worldbuilding Layer

The simulation includes a corpus of in-universe textual documents written at different academic registers — university textbooks, elementary school social studies, classified government assessments, commercial intelligence dispatches. These test whether the simulation's mechanics are coherent enough to sustain multiple narrative perspectives.

**Commodity names** are drawn from historical non-English trade languages (Arabic, Sanskrit, Malay, Polynesian, Halkomelem, Ainu, Portuguese). Tracing their etymologies reconstructs the trade networks that historically carried them.

**Primary document arc:** Year −240 BP (pre-DF commercial) → Year −8 BP (first detonation) → Year 0 (Strange Peace) → Year 140 SP (centenary retrospective)

---

## Epistemology Note

Aeolia is a game, not a predictive model. Its simulation mechanics encode deliberate simplifications — deterministic rational actors, Cobb-Douglas production, gravity-model trade — that would be indefensible as claims about real history. The value is in the exploration, not the output: watching how energy constraints, geography, and information asymmetry interact under controlled conditions, then asking whether the patterns remind you of anything. If the simulation told you what *had* to happen, it would be wrong. If it makes you argue about *why* something happened, it's working.

---

## Status (April 2026)

- ✅ Full simulation pipeline: 10,000-year, 200-tick, 30 polities, Dark Forest at year −250 on primary seed
- ✅ Strategy game: turn-based play, 18 situation cards, fog of war, event popups
- ✅ Observatory mode: full history viewer with charts, timeline, scrubber
- ✅ Academic grounding: 33-section citation map, all mechanics documented
- ✅ Worldbuilding: 5 series, 46 chapters, 27 observations, 12 historical fragments
- ⏳ GitHub push: blocked on HTTPS credentials (run `git push origin master` from MacBook Neo)
- ⏳ Optimizer rerun with updated 33-parameter space
