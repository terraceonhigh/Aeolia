# Aeolia

**A procedural history game that generates trade networks, resource scrambles, and nuclear deterrence on fictional archipelago worlds.**

Aeolia is a thought experiment in game form. It generates planets — randomized archipelago geographies with distinct climates, crops, and resource endowments — then simulates 20,000 years of geopolitical history on each one. Civilizations trade, expand, colonize, and eventually discover nuclear fission, at which point the system models a deterrence standoff. The simulation does not claim to represent what *did* or *should* happen in human history — it explores what *could* happen under simplified assumptions on a world very different from our own.

## What this project models

The history engine treats civilizational development as an energy economics problem. Each polity has a caloric budget determined by its geography (staple crops, fisheries, coastline), and its political decisions — how much surplus to allocate to military, research, expansion, or trade — emerge from that budget under pressure.

**Trade and information asymmetry.** Long-distance trade operates through relay networks where goods pass hand-to-hand across intermediary archipelagos. Intermediaries profit from information asymmetry: they know prices at both ends of their segment, and their trading partners don't. This produces structural inequality between calorie-producing peripheries and intermediary-controlled bottlenecks — a dynamic recognizable from pre-modern Indian Ocean trade and the Silk Road.

**Resource scrambles.** When fossil fuels (naphtha) become commercially viable, polities scramble to secure supply chains on archipelagos they don't control — paralleling 20th century oil politics. When fissile material (pyra) becomes strategically critical after a simulated fission discovery, a faster, more militarized scramble follows, paralleling the early Cold War uranium race.

**Deterrence and the Dark Forest.** When two mature nuclear-capable polities directly detect each other for the first time — after centuries of indirect relay trade — the system enters a deterrence standoff. The simulation models whether the outcome is negotiation or escalation based on prior trade exposure, communication channel quality, and cultural compatibility.

**Continuous culture space.** Political culture is modeled as a position in a two-dimensional continuous space (Collective↔Individual × Inward↔Outward), inspired by the Inglehart-Welzel Cultural Map. Culture drifts over time based on energy budget composition, trade exposure, and resource pressure — not as a fixed assignment from geography.

## Theoretical foundations

The simulation draws on established frameworks in political science, economics, and historical sociology:

- **Energy economics**: Ayres, Warr, and Kümmel on energy as an explicit factor of production
- **Trade theory**: Ricardian comparative advantage, gravity model of trade, Prebisch-Singer thesis on terms-of-trade deterioration for commodity exporters
- **Cooperation theory**: Axelrod's iterated prisoner's dilemma, Greif's Maghribi traders coalition, Milgrom-North-Weingast Law Merchant model
- **World-systems theory**: Wallerstein's core-periphery dynamics, Abu-Lughod's multi-polar pre-modern world system
- **Cliodynamics**: Turchin's demographic-fiscal model, Galor's unified growth theory
- **Deterrence theory**: Cold War nuclear detection and mutual vulnerability as modeled through awareness thresholds and capability gaps

## Worldbuilding layer

Aeolia includes a worldbuilding reference system with named trade commodities drawn from historical non-English trade languages — Arabic, Sanskrit, Malay, Polynesian, Halkomelem (Coast Salish), Ainu, Okinawan, Portuguese, and others. Commodity names encode their trade-network provenance: a player who traces the etymology of each good reconstructs the history of the trade routes that carried it.

The project includes sample in-universe documents written at different registers (university-level economic history, elementary social studies) to test whether the worldbuilding sustains multiple reading levels — a technique borrowed from the design of historical curricula.

## Structure

- `optimization/` — Python simulation engine, loss functions, parameter optimizer
  - `sim_proxy_v2.py` — tick-based history simulator (energy budgets, tech growth, awareness, deterrence)
  - `loss.py` — 12-term Baseline Earth loss function scoring sim output against historical benchmarks
  - `run_optimization.py` — Optuna TPE parameter search across 21 tunable parameters
  - `SCRAMBLE_AND_DF_PROPOSAL.md` — 15-section design document covering all simulation mechanics
  - `FISHERIES_REFERENCE.md` — named marine species and their economic/cultural roles
  - `NON_STAPLE_CROPS_REFERENCE.md` — non-staple trade commodities with etymologies and trade properties
  - `worldbuilding/` — in-universe textbook chapters
- `aeolia-godot/` — Godot 4 GDScript planet renderer (procedural terrain, globe visualization)

## A note on epistemology

Aeolia is a game, not a predictive model. Its simulation mechanics encode deliberate simplifications — deterministic rational actors, Cobb-Douglas production, gravity-model trade — that would be indefensible as claims about real history. The value is in the exploration, not the output: watching how energy constraints, geography, and information asymmetry interact under controlled conditions, then asking whether the patterns remind you of anything. If the simulation told you what *had* to happen, it would be wrong. If it makes you argue about *why* something happened, it's working.

## Status

Design phase. The simulation engine runs and produces 20,000-year histories on procedurally generated worlds. Parameter optimization against a Baseline Earth loss function is ongoing. The worldbuilding commodity layer is documented and partially integrated into the simulation code. A human-in-the-loop mode (player replaces the deterministic rational actor on one polity) is planned.
