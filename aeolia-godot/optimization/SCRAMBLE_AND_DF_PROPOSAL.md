# Scramble & Dark Forest Sequencing Proposal

## Context

The current sim_proxy_v2.py treats all resource-driven expansion identically — same absorption rate, same sovereignty mechanics, same garrison targeting weight. This produces a single undifferentiated expansion wave rather than the three distinct geopolitical phases that Earth history (and the Aeolia narrative) requires.

The DF tech threshold was also too high (10.0/9.0) given the soft cap at 9.0 with ceiling 11.0, making DF structurally unreachable. This has been fixed to 9.0/8.0.

## Problem

Three scrambles need to coexist in sequence with distinct characters:

1. **Naphtha scramble** (tech ~7): commercial, slow, trade-integration-driven
2. **Pyra scramble** (tech ~8.5): military, fast, existential panic after fission discovery
3. **Dark Forest standoff** (tech ~9): deterrence, map freeze, arms race

With identical expansion mechanics, the simulator compresses or merges these phases.

## Proposed Changes

### 1. Three-Regime Pyra Value Function

`resource_value(pyra)` should have three regimes:

| Tech range | Pyra value | Rationale |
|-----------|------------|-----------|
| < 7.0 | 0 | Unknown, unrecognized mineral |
| 7.0–8.4 | Moderate (same tier as aes/chrysos) | Pre-nuclear industrial applications: catalysis, high-temperature metallurgy, specialty alloys for naphtha-era engines |
| ≥ 8.5 | Maximum (3–5× any other resource) | Fission discovery recontextualizes existing holdings. Nuclear capability is not one priority among many — it's the overriding one |

The discontinuity at 8.5 models the moment of scientific discovery. It's not gradual appreciation — it's a phase transition. Parallel: the moment the Manhattan Project proved chain reactions work, every uranium deposit on Earth changed strategic value overnight.

### 2. Global Fission Discovery Event

When the **first polity on the map** crosses tech 8.5, a global event fires:
- All polities at tech ≥ 8.0 become aware that pyra has fission potential
- This is a one-time, irreversible event (like the Trinity test — you can't un-discover fission)
- Triggers the pyra scramble window (3–5 ticks / 150–250 years)

This prevents the unrealistic scenario where each polity independently "discovers" fission at their own tech 8.5. On Earth, once Hiroshima happened, every industrial nation immediately understood the implications regardless of their own nuclear research status.

### 3. Differentiated Scramble Mechanics

#### Naphtha scramble (tech 7–8.4):
- **Absorption rate**: Slow (higher cost per absorption)
- **Mechanism**: Trade integration increases before sovereignty decreases
- **Model**: British East India Company, Dutch VOC — commercial control precedes political control
- **Duration**: 150–200 ticks (many centuries)
- **Sovereignty transfer**: Gradual erosion through economic dependency

#### Pyra scramble (tech 8.5–8.9, post-fission-discovery):
- **Absorption rate**: Fast (minimum cost for Pu-rich targets)
- **Mechanism**: Direct military seizure. Sovereignty drops to near-zero in 1–2 ticks
- **Model**: US seizure of Shinkolobwe stockpile, Belgian Congo uranium program, Soviet Central Asian mine nationalization
- **Duration**: 3–5 ticks (150–250 years) — the scramble window
- **Sovereignty transfer**: Immediate. Absorbed polity retains population (mine workers needed) but loses all political agency
- **Expansion budget**: Redirected almost entirely toward Pu-rich islands during scramble window
- **Human cost**: Parochial-culture polities on pyra islands — low tech, small populations — get overrun by distant powers they've never met. Their homeland's geology, not their choices, determines their fate.

#### Nuclear standoff (tech ≥ 9.0):
- **Expansion**: Shifts from absorption to consolidation
- **Mechanism**: Hegemons stop acquiring new territory, start fortifying existing holdings
- **Allocation shift**: `expansion_share` drops; `consolidation_share` rises automatically above tech 9.0
- **Arms race**: Tech growth in 9.0–9.5 band may actually *accelerate* due to competitive pressure (the one place competition speeds tech)
- **Map freeze**: Deterrence stabilizes the world map. Proxy competition replaces direct conquest
- **Model**: Post-1949 Cold War — neither superpower scrambles for territory; they build arsenals

### 4. Pyra Scramble as Narrative Engine

The pyra scramble is where the simulation's human cost is concentrated. The pattern:

1. Small Parochial-culture polities occupy pyra-rich volcanic islands at subsistence tech
2. Distant Civic or Subject hegemons discover fission at tech 8.5
3. Within 1–2 ticks, those islands are garrisoned and their sovereignty erased
4. The people living there had no say in what the geology under their feet was suddenly worth

Historical parallels: Congo (uranium), Marshall Islands (testing), Kazakhstan (Soviet nuclear program), Indigenous Australian lands (British testing at Maralinga). In each case, the human cost fell on populations with no political voice in the decision.

The loss function should reward this pattern in Baseline Earth: at DF break, pyra-rich islands should be hegemon-controlled with near-zero sovereignty, absorbed in a compressed window post-fission-discovery.

### 5. DF Threshold Fix (Already Applied)

- Initiator tech threshold: 10.0 → **9.0**
- Target tech threshold: 9.0 → **8.0**
- Narrative justification: Detection and surveillance are early nuclear-era capabilities (U-2 1955, CORONA 1960), not late ones. You don't need to be at the tech frontier to detect another nuclear power.

### 6. Parameter Implications

The existing 21 parameters can encode most of this through the resource_value function shape and tech-gated allocation shifts. Potential additions:

| Parameter | Default | Bounds | Purpose |
|-----------|---------|--------|---------|
| `pu_discovery_tech` | 8.5 | 7.5–9.0 | Tech threshold for global fission discovery event |
| `pyra_scramble_speed` | 3.0 | 1.0–5.0 | Multiplier on absorption rate for Pu-rich islands post-discovery |
| `consolidation_shift_tech` | 9.0 | 8.5–9.5 | Tech threshold where allocation tilts from expansion to consolidation |

These could be folded into existing parameters or hardcoded if the optimizer doesn't need to search over them.

### 7. Implementation Sequence

1. Add three-regime `resource_value(pyra)` to sim_proxy_v2.py
2. Add global fission discovery event (first polity crosses threshold → all aware)
3. Differentiate absorption rates: slow for C-rich targets, fast for Pu-rich post-discovery
4. Add consolidation shift at tech 9.0 (expansion_share drops, consolidation_share rises)
5. Add pyra scramble window (3–5 ticks post-discovery with elevated Pu targeting)
6. Add sub-term to `pu_acquisition` in loss.py: reward compressed Pu island absorption + near-zero sovereignty at DF break
7. Re-verify on seed 216089: naphtha scramble at ~7, pyra scramble at ~8.5, DF standoff at ~9, all with distinct character

### 8. Relationship to Loss Function Library

The scramble mechanics are **simulator-level** (sim_proxy), not loss-function-level. All loss functions benefit from the richer dynamics. The Baseline Earth loss function adds specific targets (timing windows, sovereignty patterns). Alternative loss functions (Resource Curse, Reversed Polarity, etc.) can reward different scramble outcomes without changing the underlying mechanics.

---

## 9. Inference Depth: Relay Trade to First Contact

### The Problem

The current simulator treats all exploration and colonization events identically regardless of prior indirect trade history. But the epistemic impact of meeting a civilization you've been unknowingly exchanging artifacts with for centuries is qualitatively different from meeting one you've never interacted with at all.

### The Mechanic: inference_depth

Every pair of polities accumulates an `inference_depth` value — the count of ticks during which goods flowed between them through intermediary relay chains without direct contact. This accumulates passively through the existing trade integration mechanic.

- Goods flow from polity A → intermediary islands → polity B
- Neither endpoint knows the other exists as a specific entity
- Both endpoints receive artifacts they can't fully explain
- Academic, theological, and strategic traditions develop around the "unknown makers"

When direct contact finally occurs (exploration, colonization, or DF detection), `inference_depth` is consumed — converted into a posture modifier for that specific relationship, then zeroed out because the relationship is now direct.

### Three Regimes

| inference_depth | Character | Example |
|----------------|-----------|---------|
| Zero (no prior trade) | Pure novelty. Both sides assess from scratch. Posture defaults to culture-type prior. | Polynesian wayfinders reaching an uninhabited island |
| Low (few ticks of relay) | Mild surprise. "Oh, so that's where those pots came from." Slight posture adjustment, mostly curiosity. | Early Silk Road — goods arrive but models of the source are vague |
| High (centuries of relay) | Retroactive recontextualization. Every artifact in every museum is suddenly intelligence. Both sides' models of each other were wrong, and the wrongness is destabilizing. Hard defensive posture shift. | The DF break scenario — millennia of artifacts, then radar contact with a peer nuclear power |

### Why Longer Trade Makes Contact Worse

The horror isn't discovery. It's retroactive recontextualization.

A civilization that detects another nuclear power with zero prior information thinks "unknown threat, gather intelligence." A civilization that detects another nuclear power after 800 years of ambiguous artifact exchange thinks "everything we suspected is confirmed, and we've been leaking intelligence about ourselves the entire time."

The relay trade doesn't build a bridge. It builds a dossier. Both sides have been compiling intelligence on each other for centuries without realizing that's what they were doing. At the moment of detection, both sides realize simultaneously that the other side has the same dossier.

This is the worst possible epistemic state for avoiding conflict: enough information to be afraid, not enough to be accurate. Models built on artifacts, not diplomacy. And nuclear-era strategic decisions that must be made based on those models.

### Generalization Across All Contact Events

This mechanic applies identically at every scale, from first canoe landing to nuclear detection:

- **Tech 3, low inference_depth**: A Civic polity's outrigger reaches a neighboring Parochial island. No prior trade. Mild curiosity, assessment based on culture-type priors. The chieftain is impressed by foreign pottery. Low posture shift.

- **Tech 5, moderate inference_depth**: A Civic polity's explorer reaches an island two hops away. Shell ornaments from this direction have been elite prestige goods for generations. Contact reveals the makers — smaller and less technologically advanced than imagined. Model correction is mild. Moderate posture shift.

- **Tech 6, high inference_depth**: Serial contact between archipelagos. Centuries of relay trade. Ceramics, metallurgy, textiles with unexplainable chemistry have been flowing for generations. The arriving polity discovers a civilization larger and more organized than their mythology allowed. Epistemic shock. Strong posture shift, tech acceleration (Meiji Restoration response), exploration surge.

- **Tech 9, maximum inference_depth**: DF break. Millennia of relay trade. A civilization that has built entire academic traditions around the "unknown makers" picks up a radar return from a military aircraft with matching performance characteristics. Every artifact, every theory, every museum exhibit is instantly recontextualized as intelligence about a specific, technologically mature, strategically opaque peer. Maximum posture shift. Panic.

The difference between these events is just `inference_depth × tech_level`. One variable, no special cases.

### Effect on Posture

When direct contact occurs, the contacting polity receives a posture modifier:

```
contact_shock = inference_depth * tech_level_of_contacted * shock_scaling_factor
```

This modifier:
1. Injects a one-time "shock prior" into the Thompson Sampling Beta distribution for that relationship, weighting hostile outcomes
2. Temporarily increases tech_share allocation (the Meiji response — "we must modernize faster")
3. Temporarily increases expansion_share for reconnaissance (the "what else is out there?" response)
4. Decays over 5–10 ticks as direct observation replaces artifact-based inference

The decay is key — the posture shift is not permanent. As direct contact accumulates real information, the artifact-based dossier is superseded. But the 5–10 tick window of elevated threat perception is where the most consequential strategic decisions get made. Wars of conquest, defensive fortification, alliance formation — these happen in the shock window, not after it passes.

### Interaction with Other Mechanics

- **Naphtha scramble**: If relay trade has been running between two hegemons through naphtha-rich intermediary islands, the scramble for those islands is intensified by inference_depth. The hegemon isn't just seizing resources — it's seizing the relay chain, cutting the other side's intelligence pipeline.

- **Pyra scramble**: Post-fission-discovery, polities with high inference_depth about a distant peer will prioritize pyra acquisition more aggressively. "They've been receiving our artifacts for centuries — they know our industrial capacity — we must secure nuclear capability before they use what they know."

- **Dark Forest**: inference_depth is the variable that makes the DF break between relay-trade-connected hegemons categorically more severe than detection of a truly unknown civilization. The Dark Forest on Aeolia isn't about the unknown — it's about the suddenly, terrifyingly known.

### Parameter Implications

One new parameter:

| Parameter | Default | Bounds | Purpose |
|-----------|---------|--------|---------|
| `contact_shock_decay` | 7 | 3–15 | Ticks for the posture shock to decay after direct contact. Lower = faster recovery, higher = longer paranoia window |

The `inference_depth` itself is emergent — it's just a counter on the trade integration mechanic. The `shock_scaling_factor` can be derived from existing parameters (epi_base_severity provides a template for scaling contact severity).

### Narrative Payoff

The civilization that was most cosmopolitan, most engaged in long-distance trade, most intellectually curious about the "unknown makers" experiences the worst contact shock. Their openness compiled the largest dossier, which means the retroactive horror is deepest.

The civilization that was isolationist and ignored the strange trade goods has less to recontextualize and responds more calmly.

This inverts the usual assumption that trade and cultural exchange reduce conflict. On Aeolia, indirect exchange without direct contact *amplifies* the Dark Forest by giving both sides just enough information to be terrified.

---

## 10. Continuous Culture Space (Resolves Q1 & Q2)

### Design

Political culture is not a categorical type (Civic/Subject/Parochial) but a position in a continuous two-dimensional space, inspired by the Inglehart-Welzel Cultural Map but relabeled for causal relevance across all tech levels.

### Axes

**Axis 1: Collective ↔ Individual** (0 to 1)

Where decision-making authority sits.

- Collective end (0): Decisions made by the group, chief, council, or bureaucracy. Individual interests subordinated to collective survival. Centralized resource allocation.
- Individual end (1): Decisions made by autonomous actors — merchants, entrepreneurs, warlords. Individual initiative drives expansion and innovation. Distributed resource allocation.

Causally upstream of: consolidation_share, tech allocation pattern (directed programs vs. distributed innovation), garrison behavior (methodical vs. opportunistic).

At tech 2: village council allocating rice paddies vs. individual families claiming taro plots.
At tech 9: command economy directing nuclear research vs. market economy with competing defense firms.

**Axis 2: Inward ↔ Outward** (0 to 1)

Whether institutions orient toward internal consolidation or external projection.

- Inward end (0): Defense, self-sufficiency, institutional maintenance, suspicion of outsiders.
- Outward end (1): Trade, exploration, alliance-building, cultural exchange, risk-taking.

Causally upstream of: expansion_share, trade integration, contact posture (defensive vs. curious), inference_depth accumulation rate.

At tech 2: inland farming village fortifying against raiders vs. coastal fishing village trading with the next island.
At tech 9: continental power building defensive depth vs. maritime power projecting force across the ocean.

### Old Categories in the New Space

| Old Category | Approximate Position | Historical Examples |
|-------------|---------------------|---------------------|
| Civic | Individual(0.6-0.8) + Outward(0.6-0.9) | Athens, Venice, Dutch Republic, maritime Britain |
| Subject | Collective(0.1-0.3) + Inward(0.1-0.4) | Qin China, Ottoman Empire, Soviet Union |
| Parochial | Center(0.4-0.6) + Center(0.4-0.6) | Small-scale societies where neither axis dominates |
| *Collective + Outward* | Collective(0.1-0.3) + Outward(0.6-0.9) | Mongol Empire, Ming treasure fleets, Soviet space program |
| *Individual + Inward* | Individual(0.6-0.8) + Inward(0.1-0.4) | Isolationist merchant republics |

The continuous space captures positions the three categories couldn't represent.

### Initial Position from Substrate

```
initial_collective_individual = f(
    labor_coordination[crop],     # high coordination → Collective
    island_size,                  # larger → more Collective
    arable_fraction,              # denser settlement → more Collective
    terrain_ruggedness            # rugged → more Individual (Scott's Zomia)
) + prng_noise

initial_inward_outward = f(
    neighbor_count,               # more neighbors → more Outward
    coastline_ratio,              # more coast → more Outward
    surplus_potential[crop],      # higher surplus → more Outward
    isolation                     # geographic isolation → more Inward
) + prng_noise
```

Crop still matters — paddi has high labor coordination, pushing toward Collective. But a small, mountainous, isolated paddi island can produce an Individual position (Balinese subak instead of Chinese imperial bureaucracy). Geography modulates the crop's institutional pressure.

### Allocation as Continuous Functions

```
expansion_share = base_expansion + outward_coeff * outward + individual_coeff * individual
tech_share = base_tech + outward_tech_coeff * outward
consolidation_share = 1 - expansion_share - tech_share
A0 = base_A0 + individual_A0_coeff * individual + outward_A0_coeff * outward
```

~6-8 parameters replace the original 11 culture parameters, with clearer physical interpretations.

### Energy-Budget Drift (Closed Loop)

Each tick, position drifts based on energy budget and spending:

```
# Prosperity erodes coordination pressure
collective_individual += surplus_ratio * (1 - consolidation_share) * drift_rate

# Crisis demands coordination
collective_individual -= threat_level * drift_rate

# Innovation and exchange culture
inward_outward += tech_share * trade_integration * drift_rate

# Defensive retrenchment
inward_outward -= (resource_stress + military_loss) * drift_rate
```

Drift rate ~0.01-0.02 per tick. Culture changes over centuries, not decades.

This closes the feedback loop: crop × geography → initial position → allocation shares → spending pattern → energy outcomes → position drift → new allocation shares. The ibn Khaldun cycle, Inglehart's modernization thesis, and Scott's resistance to centralization all emerge from the same drift mechanic.

### Thompson Sampling Priors (Continuous)

```
alpha = 1 + outward
beta = 1 + (1 - outward) * collective
```

No lookup table. A polity at (0.2, 0.8) — Collective + Outward — gets Beta(1.8, 1.16): aggressive but organized. A polity at (0.8, 0.2) — Individual + Inward — gets Beta(1.2, 1.64): cautious and fragmented.

### Parameter Reduction

Old: 11 culture parameters (3 allocation shares × 3 culture types + 2 unused slots for A0)
New: ~6-8 coefficients for the continuous functions + 1 drift_rate + 1 noise_scale

Net reduction of 2-4 parameters while gaining: culture drift, the full Inglehart-Welzel space, positions the old categories couldn't represent, and dissolution of the crop-determinism problem.

### Interaction with Other Mechanics

- **Inference depth**: Outward polities accumulate inference_depth faster (more active trade). The contact shock when they finally meet a peer is proportionally worse.
- **Naphtha scramble**: Position determines scramble character. Outward polities pursue commercial integration; Collective polities pursue direct seizure.
- **Pyra scramble**: All polities drift Inward after fission discovery (existential threat → defensive retrenchment). The scramble happens during this drift.
- **Dark Forest**: The two hegemons' positions at DF break determine the character of the standoff. Collective+Inward vs. Individual+Outward is the US-Soviet dynamic. Two Collective+Outward hegemons is a different, potentially more dangerous configuration.
- **Loss function**: Baseline Earth specifies target regions in the space for the two hegemons, not target categories. Alternative loss functions can reward different distributions across the space.

---

## 11. Tech Decay & Desperation Mechanics (Resolves Q3)

### The Problem

Tech currently only increases. A polity at tech 8 that loses its naphtha supply, half its population to epidemic, and its best agricultural islands to a rival stays at tech 8 forever. The simulator cannot produce a Bronze Age Collapse, a post-Roman dark age, or a Khmer abandonment.

### Architecture: Layered Energy Balance

The energy surplus calculation is split into layers, each corresponding to a different era of civilizational development:

**Food energy** (tech 0+):
```
food_surplus = Σ(crop_yield[arch] × arable_fraction[arch]) - population × subsistence_cost
```
Negative food_surplus = famine → population decline → absolute desperation. Every polity needs this positive at all times.

**Industrial energy** (tech ~7+):
```
industrial_surplus = naphtha_extraction - industrial_maintenance_cost(tech)
```
Negative industrial_surplus = tech decay. The layer that already exists in the energy budget.

**Nuclear energy** (tech ~9+, post-fission):
```
nuclear_surplus = pyra_production - nuclear_maintenance_cost(tech)
```
Only relevant post-fission. Negative = loss of nuclear capability.

### Tech Maintenance Cost

Each tick, tech has a maintenance cost proportional to its level:

```
maintenance = tech² × maintenance_rate
```

Quadratic because higher-tech civilizations have exponentially more infrastructure to maintain (roads, factories, power grids, telecommunications, research institutions). If energy surplus falls below maintenance, tech decays:

```
if energy_surplus < maintenance:
    shortfall = maintenance - energy_surplus
    tech -= shortfall * decay_rate
```

High-tech civilizations are fragile. A tech-8 polity needs significantly more energy to stay at tech 8 than a tech-4 polity needs for tech 4. Lose your naphtha and you don't plateau — you slide.

### Collapse Cascade

The slide can cascade:
1. Naphtha depletes → industrial surplus turns negative
2. Tech starts decaying → reduces ability to extract remaining resources
3. Reduced extraction → further surplus decline → faster decay
4. If tech drops below military maintenance threshold → garrison capability falls
5. Rivals can now absorb former territory → further resource loss
6. Potential stabilization at a lower tech level where the remaining resource base can sustain maintenance

### Recovery

Can a polity that falls from tech 8 to tech 5 re-industrialize?
- If naphtha remains → yes, slowly. Must re-climb the tech tree.
- If naphtha is depleted → trapped in pre-industrial state on a depleted resource base. Must secure new naphtha through trade or conquest to re-industrialize.
- Knowledge is not fully lost. A "collapse discount" parameter could allow faster re-climbing through tech levels previously attained (manuscripts survive, ruins teach, institutional memory persists).

### Desperation Mechanic

Resource pressure creates a new input to allocation that overrides culture position:

```
resource_pressure = max(0, maintenance_cost - energy_surplus) / maintenance_cost
```

0 when comfortable, approaches 1 as deficit worsens. The polity's response depends on what's available:

**Food deficit (highest priority):**
- If reachable arable land exists → expansion_pressure toward fertile islands
- Model: Rome conquering Egypt for grain, Athens securing Black Sea trade, Japan colonizing Korea/Manchuria for rice
- A small, tech-advanced polity on barren volcanic islands conquers a large, low-tech polity on fertile flatlands to secure calories

**Industrial deficit (second priority):**
- If reachable naphtha exists → expansion_pressure toward C-rich islands
- If no reachable naphtha → tech_pressure (efficiency innovation, necessity-driven R&D)
- If neither → consolidation_pressure (fortress mode, abandon periphery)
- Model: Britain's industrial need for cotton (India), rubber (Malaya), oil (Middle East)

**Nuclear deficit (third priority, post-fission):**
- If reachable pyra exists → expansion_pressure toward Pu-rich islands (the pyra scramble)
- Model: US seizure of Congolese uranium, Soviet Central Asian mine program

The hierarchy is: calories → hydrocarbons → fissiles. Same as Earth.

### Structural Deficit (The Cotton Variant)

A polity may not be in famine but still face structural commodity deficit — its economy requires inputs it can only get through trade. If that trade is unreliable or controlled by a rival:

```
structural_deficit = Σ(required_commodity[i] - domestic_production[i]) for commodities obtained via trade
trade_risk = 1 - trade_reliability(partner)  # rival control, distance, intermediary fragility
structural_pressure = structural_deficit × trade_risk × structural_weight
```

This drives "secure the supply chain" conquests even when the polity isn't starving. The EIC conquered Bengal not because Britain was food-deficit but because cotton supply was unreliable and France might outcompete for it.

### Allocation Override

```
# Desperation modifier overrides culture-based allocation
effective_expansion = culture_expansion + expansion_pressure
effective_tech = culture_tech + tech_pressure
effective_consolidation = culture_consolidation + consolidation_pressure
# renormalize to sum to 1
```

As resource_pressure → 1, desperation dominates culture. A Collective+Inward polity (the most isolationist) lunges outward for naphtha if the alternative is collapse. An Individual+Outward polity (the most expansionist) hunkers down if there's nowhere left to expand.

### Parameters

| Parameter | Default | Bounds | Purpose |
|-----------|---------|--------|---------|
| `maintenance_rate` | 0.01 | 0.005–0.05 | Energy cost per unit tech² per tick |
| `decay_rate` | 0.1 | 0.05–0.3 | How fast tech drops when in deficit |
| `desperation_weight` | 0.5 | 0.2–1.0 | How strongly resource_pressure overrides culture allocation |
| `collapse_discount` | 0.5 | 0.0–0.8 | Speed bonus for re-climbing previously attained tech levels |

### Narrative Payoff

Polities don't just drift through culture space on abstract institutional pressures. They react to material conditions. Culture tells you what a polity *wants* to do. Energy balance tells you what it *has* to do. The divergence — a Collective+Inward civilization forced outward by resource depletion — is where the most interesting and tragic history happens. The Scramble for Africa. The Japanese conquest of Manchuria. Every resource war that started with "vital national interest."

The nastiest scenario the optimizer can now produce: a polity industrializes at tech 8 using naphtha, depletes it, collapses to tech 5, and has no fossil energy to re-industrialize. Permanently trapped in pre-industrial state on a depleted resource base. That's the Resource Curse loss function's nightmare, now mechanically possible.

---

## 12. Trade as Energy (Resolves Trade Model)

### Core Insight

Trade is not a separate system bolted onto the energy budget — it is a component of the energy budget. Every trade flow is an embodied energy transfer. A polity's energy surplus is not just what it produces domestically; it is what it produces plus what it imports minus what it exports minus maintenance.

### Energy Equation (Revised)

```
food_energy = domestic_crop_yield + fish_catch + food_imports - food_exports
industrial_energy = domestic_naphtha + marine_oil + industrial_imports - industrial_exports
nuclear_energy = domestic_pyra + pyra_imports - pyra_exports
maintenance = tech² × maintenance_rate
surplus = food_energy + industrial_energy + nuclear_energy - maintenance
```

Each import term depends on: trade routes existing, the partner being willing and able to supply, and the importing polity having something the partner wants in exchange.

### Fish as Mandatory Resource

On an ocean planet, marine protein is the foundational caloric source for every archipelago civilization.

**Subsistence fish** (tech 0+): reef fish, shellfish, intertidal gathering. Local consumption, doesn't travel. Every coastal arch has this, proportional to coastline length and reef area. The baseline protein that makes island settlement viable.

**Preserved fish** (tech 1+): smoked, salted, dried, fermented. Travels as relay-trade commodity. Calorie-dense, shelf-stable, universally demanded. Comparable to the stimulant and fiber trade goods.

**Industrial fisheries** (tech 5+): whaling, offshore trawling, factory processing. Rendered marine oil as pre-naphtha energy source for lamps, lubrication, early industrial applications. The whale oil → naphtha transition mirrors Earth's 1850s-1860s.

Proposed commodity additions: **kelu** (preserved fish, universal maritime trade good), **rendered marine oil** (pre-naphtha industrial energy).

### Three Trade Layers

**Layer 1: Subsistence trade (tech 0+)**
Direct exchange between adjacent islands. Barter-scale, low volume, operates on plateau graph direct edges. Effect: marginal surplus improvement. Minimal inference_depth — trading partners know each other directly.

**Layer 2: Relay trade (tech 2+)**
Indirect exchange through intermediary chains. Neither endpoint knows the other exists. Volume limited by chain capacity — every intermediary is a bottleneck. Each hop takes an intermediary tax. Effect: prestige goods that stabilize hierarchies, stimulants that become culturally embedded, specialty materials enabling tech advantages. This layer builds inference_depth.

**Layer 3: Administered trade (tech 5+)**
Direct trade routes bypassing intermediaries. Requires sufficient naval range, Outward cultural position, and surplus to fund overhead. Creates direct edges in trade graph — higher capacity, no intermediary tax, but requires military/institutional maintenance. Creates dependency relationships that feed the structural deficit mechanic.

### Economic Foundations

**Ricardian comparative advantage** determines what flows: even if one island is absolutely better at everything, both benefit from specializing in their relative advantage. The archipelago substrate generates comparative advantage naturally.

**Gravity model** determines volume: `trade_volume(A,B) = k × GDP(A) × GDP(B) / hop_distance(A,B)²`

**Prebisch-Singer thesis** determines distributional consequences over time: terms of trade between primary commodity exporters and manufactured goods exporters systematically deteriorate. Parochial intermediary islands export taro and moa, import increasingly sophisticated manufactured goods. They become progressively poorer relative to hegemons even without conquest.

**Dependency theory (Wallerstein)** describes the emergent structure: high-tech endpoints are the core, Parochial intermediaries are semi-periphery (middleman surplus), distant low-tech islands are periphery. Administered trade collapses semi-periphery into periphery by bypassing middlemen.

**Stolper-Samuelson** generates internal political dynamics: trade benefits the abundant factor and hurts the scarce factor within each polity. An Outward polity whose elites benefit from trade but whose commoners are hurt faces internal pressure toward Inward.

**Infant industry effect**: a Parochial island receiving aes tools through trade never develops copper smelting because imports are cheaper. Trade dependency suppresses tech development in peripheral polities.

### Desperation Mechanic Integration

Trade adds a step between "deficit detected" and "launch invasion":

1. Deficit detected (food, industrial, or nuclear)
2. Can trade fill the deficit? → If yes, establish/maintain trade route. Culture trajectory unchanged.
3. Is trade unreliable? (rival controls source, route insecure, intermediary fragile) → Structural deficit triggers expansion pressure toward securing supply chain.
4. Can't trade and can't conquer? → Consolidation/fortress mode.

Britain traded for Indian cotton for two centuries before conquering India. The conquest happened when trade alone couldn't secure the volume demanded.

### Trade Vulnerability

```
trade_dependency = trade_imports / total_energy
trade_risk = Σ(import_volume[route] × (1 / route_security[route]))
risk_adjusted_deficit = actual_deficit + trade_dependency × trade_risk × vulnerability_weight
```

A polity with positive actual energy balance but high trade_dependency and high trade_risk has a negative risk-adjusted balance. The risk-adjusted deficit triggers desperation expansion — not because the polity is currently starving, but because it can't guarantee it won't be. Japan 1941: trade_dependency ≈ 1.0 for oil, trade_risk spiked to maximum when the US imposed embargo. Desperation fired on risk-adjusted deficit.

### Relay Trade as Energy Infrastructure

Intermediary islands aren't just passing goods — they're energy intermediaries facilitating caloric and industrial energy flows. When a hegemon absorbs an intermediary during a scramble, it captures a node in its own energy supply chain. The other hegemon, whose energy also flows through that node, loses energy infrastructure.

Administered trade is an energy efficiency upgrade: cutting intermediary taxes means more energy arrives per unit exported. This is why empires formalize trade into colonies — not just for control, but for margin.

### Parameters

| Parameter | Default | Bounds | Purpose |
|-----------|---------|--------|---------|
| `intermediary_tax_rate` | 0.10 | 0.05–0.20 | Fraction of trade value skimmed per relay hop |
| `trade_range_decay` | 0.15 | 0.10–0.30 | Value lost per hop (perishability, transport cost) |
| `administered_trade_tech` | 5.0 | 4.0–6.0 | Minimum tech to establish direct trade routes |
| `vulnerability_weight` | 0.3 | 0.1–0.5 | How much trade risk inflates effective deficit |

Trade flows themselves are computed from substrate endowments and gravity model, not parameterized.

---

## 13. Trade Model: Research-Corrected Design

### Research Findings (from literature review)

Four parallel research reviews produced corrections to our initial trade model:

**1. Variable markup by commodity class, not flat skim.**
Historical Silk Road markup was ~40-50% per hop for luxury goods, ~10-20% for maritime bulk. The key variable is value-to-weight ratio. High value-to-weight goods (stimulants, fibers, prestige minerals) sustain high markup and propagate through long relay chains. Bulk goods (grain, preserved fish, raw materials) can't sustain relay markup beyond 2-3 hops and remain local.

**2. Intermediaries practice selective disclosure, not distortion.**
Sogdian merchant letters, Cairo Geniza documents, and Greif's Maghribi work converge: historical middlemen maintained accurate information *within* their networks (reputation collapses otherwise) but strategically *withheld* information from outsiders. They didn't fabricate — they controlled access to truth. Model as disclosure rate (0-100% of true state), not distortion.

**3. Cooperation requires layered trust infrastructure, not just reputation.**
Greif's reputation-only model has been challenged. Historical trade cooperation relied on: kinship/affiliation at the base (Polynesian *hau*, Sogdian family networks), reputation in the middle (merchant guilds, diaspora communities), institutional authority where available (Buddhist monasteries, Islamic courts, Champagne fair judges). The applicable cooperation mechanism depends on the polities' culture positions.

**4. Prebisch-Singer doesn't apply pre-industrial. Use merchant monopoly instead.**
Terms-of-trade deterioration requires industrial productivity asymmetry. Pre-industrial inequality is driven by: merchant monopoly/monopsony (controlling routes lets you set prices), comparative advantage lock-in (Banda Islands specialized in nutmeg, abandoned food production, became dependent), and unequal labor exchange. Abu-Lughod's multi-polar model fits pre-industrial better than Wallerstein's single-hegemon model. Prebisch-Singer kicks in post-tech-7.

### Corrected Trade Architecture

#### Commodity Classes and Range

| Class | Examples | Markup tolerance per hop | Effective relay range | inference_depth generation |
|-------|----------|------------------------|----------------------|--------------------------|
| Luxury stimulants | qahwa, char, awa, pinang, aqua | 35-50% | 6-8 hops | High |
| Luxury fibers | seric, byssus, fell, tapa, qivu | 30-45% | 5-7 hops | High |
| Prestige minerals | chrysos, aes artifacts | 30-50% | 5-8 hops | High |
| Preserved protein | kelu (fish), kri, kerbau, moa | 15-25% | 2-4 hops | Low-moderate |
| Bulk food | raw crop surplus, fresh fish | 5-15% | 1-2 hops | Minimal |
| Industrial energy | naphtha, rendered marine oil | 10-20% | 2-3 hops (relay), unlimited (administered) | Moderate |
| Strategic minerals | pyra, raw aes/sider ore | 20-40% | 3-5 hops (relay), unlimited (administered) | Moderate |

Luxury goods propagate through long chains and are the primary inference_depth builders — the "artifacts without authors." Bulk goods stay local. Industrial/strategic resources require administered trade (direct routes) for reliable supply.

#### Cooperation Mechanism by Culture Position

| Culture region | Trust infrastructure | Cooperation mechanic | Vulnerability |
|---------------|---------------------|---------------------|---------------|
| Collective + any | Institutional: treaties, bureaucratic enforcement, standardized terms | Formal agreements with compliance monitoring | Institutional collapse breaks all agreements simultaneously |
| Individual + Outward | Reputation: merchant guilds, diaspora networks, personal relationships | Bilateral reputation scores, collective ostracism for defectors | Reputation is slow to build, fast to destroy |
| Individual + Inward | Market: transactional, each exchange evaluated independently | Price-based, no long-term commitment, every tick is near-one-shot | No persistent cooperation — every deal stands alone |
| Parochial (low centralization, any openness) | Kinship: marriage alliances, gift exchange, reciprocal obligation | Kinship bonds between polity elites, *hau*-like obligation cycles | Only works between culturally similar polities |

**Commitment compatibility** between two polities = function of distance in culture space. Polities in the same quadrant share trust infrastructure and can sustain cooperation. Polities in opposite quadrants face the colonial communication problem: both can talk, neither can commit credibly in the other's framework. This cultural friction on trade is a natural driver of colonial conquest — "we can't trade with them efficiently, so we'll govern them directly."

#### Inequality Mechanisms by Tech Level

| Tech range | Inequality mechanism | Driver |
|-----------|---------------------|--------|
| 0-4 | Geographic endowment | Some islands have better crops, more fish, more minerals. Inequality is natural and moderate. |
| 4-7 | Merchant monopoly + comparative advantage lock-in | Trade-hub polities extract rents. Peripheral islands specialize, lose diversification, become dependent. Banda Islands problem. |
| 7-9 | Prebisch-Singer + administered trade extraction | Industrial polities export manufactured goods, import primary commodities at deteriorating terms. Colonial extraction formalizes unequal exchange. |
| 9+ | Strategic resource monopoly | Pyra-holding polities have existential leverage. Inequality becomes binary: nuclear sovereignty or nuclear dependency. |

The inequality mechanism *switches* as tech advances. The optimizer doesn't need to be told which mechanism to use — the resource_value function and trade gravity model naturally produce the right dynamics at each tech level.

### Parameters (Revised)

| Parameter | Default | Bounds | Purpose |
|-----------|---------|--------|---------|
| `luxury_markup_rate` | 0.40 | 0.25-0.55 | Per-hop markup for luxury goods (stimulants, fibers, prestige minerals) |
| `bulk_markup_rate` | 0.10 | 0.05-0.20 | Per-hop markup for bulk goods (food, raw materials) |
| `administered_trade_tech` | 5.0 | 4.0-6.0 | Minimum tech for direct trade routes |
| `vulnerability_weight` | 0.3 | 0.1-0.5 | How much trade risk inflates effective deficit |
| `commitment_distance_penalty` | 0.5 | 0.2-0.8 | How much culture-space distance reduces cooperation reliability |

Five trade parameters. Commodity flows, relay routing, intermediary behavior, and inequality dynamics all emerge from substrate endowments, gravity model, and culture positions.

---

## 14. Actor-Actor Communication

### Three Communication Layers

Communication between polities operates at three distinct speeds and fidelities:

**Signal** (fastest, lowest fidelity): One-directional, unverified, travels through existing relay chains. "Smoke on the horizon." "Strange ships seen." "The intermediary says the southerners had a bad harvest." Signals degrade per hop (information_decay_per_hop). Five relay hops at 80% disclosure each = 0.33 fidelity. Most content is lost. This is the existing rumor propagation mechanic, extended to carry content type (famine, military, trade disruption) as well as magnitude.

**Message** (medium speed, medium fidelity): Bilateral, intentional, requires a channel. One polity deliberately sends information to another. Requires: awareness > threshold, communication channel (direct or relay), and enough common reference for understanding. Bottlenecked by relay chain — each intermediary can transmit faithfully, delay, modify, or block. Intermediary disclosure behavior follows from culture position: Outward intermediaries facilitate (more trade volume = more revenue), Inward intermediaries obstruct (information control = leverage).

**Negotiation** (slowest, highest fidelity): The repeated game. Two polities that can exchange messages play iterated games — propose terms, observe compliance, punish defection, reward cooperation. Requires sustained bilateral channel with sufficient bandwidth and fidelity. This is where the cooperation mechanism layering (kinship/reputation/institutional) determines outcomes.

### Communication Channel Properties

Each polity pair has an implicit communication channel with three derived properties:

```
channel_bandwidth:          # information per tick (0 = no contact, 1 = full diplomatic exchange)
                            # derived from: trade graph connectivity, administered routes
channel_fidelity:           # message accuracy (degrades with relay hops × intermediary disclosure)
                            # derived from: hop count, intermediary culture positions
commitment_compatibility:   # how well trust infrastructure meshes
                            # derived from: distance in culture space
```

No new parameters — all three are derived from existing systems.

### Game Type by Channel Quality

| bandwidth × fidelity × compatibility | Game type | Historical parallel | Outcome tendency |
|--------------------------------------|-----------|-------------------|------------------|
| High × High × High | Full iterated PD, cooperation stable | Anglo-Portuguese alliance | Sustained trade, mutual prosperity |
| High × High × Low | Can communicate, can't commit | US-Soviet hotline | Understanding without trust, unstable cooperation |
| Low × Low × Any | Near-one-shot, too noisy for Tit-for-Tat | Pre-DF relay chain inference | Dark Forest posture, worst-case assumptions |
| Zero × Any × Any | No game, no contact | Pre-serial-contact isolation | Culture position determines posture toward unknown |

### First Contact as Game-Type Transition

The transition from zero to nonzero bandwidth is the first contact event. The transition from low to high bandwidth is the administered trade / direct diplomatic contact transition. Each transition changes the game structure:

- **Zero → low bandwidth** (first contact via relay chain): The game begins, but it's noisy and nearly one-shot. Posture determined by inference_depth and contact shock. This is destabilizing because the game type changes abruptly from "no game" to "noisy game with high uncertainty."

- **Low → high bandwidth** (administered trade established): The game upgrades from near-one-shot to full iterated. Cooperation strategies become viable. This is why administered trade is strategically important beyond its energy-efficiency benefits — it changes the *game structure* between two polities.

- **High bandwidth lost** (route severed, intermediary absorbed, war): The game downgrades from iterated back toward one-shot. Cooperation collapses. This is the mechanism by which the naphtha scramble destroys relay-chain cooperation — absorbing intermediary islands severs communication channels between endpoint civilizations, downgrading their game from iterated to near-one-shot, triggering defensive posture shifts.

### Repeated Game Mechanics

For polity pairs with sufficient channel quality, the iterated game operates per tick:

**Cooperation history**: Running tally of ticks with successful bilateral exchange. This is the "shadow of the future" — higher = more stable.

**Defection memory**: Decaying record of partner defection (embargo, raid, broken agreement). Recent defection reduces trust. Decay follows exponential halflife (the `defection_memory_halflife` parameter from inference_depth section, repurposed here — same mechanic, different application).

**Power asymmetry distortion**: In symmetric iterated PD, mutual cooperation is stable. In asymmetric PD (large tech/military gap), the stronger party can defect without credible retaliation. This is why colonial relationships are extractive — power asymmetry makes defection costless for the colonizer.

```
cooperation_modifier = cooperation_history * cooperation_growth_rate
defection_modifier = defection_count * exp(-tick_age / defection_halflife)
asymmetry_modifier = min(tech_ratio, military_ratio)  # >1 if asymmetric

effective_cooperation = cooperation_modifier - defection_modifier
if asymmetry_modifier > asymmetry_threshold:
    # stronger party can defect without punishment
    effective_cooperation *= (1 / asymmetry_modifier)
```

### Intermediary Communication Behavior

Intermediaries on relay chains make disclosure decisions each tick based on culture position:

- **Outward intermediaries** (high outward value): High disclosure rate. Facilitate communication between endpoints. More trade volume = more revenue. Active interest in diplomatic stability.

- **Inward intermediaries** (low outward value): Low disclosure rate. Withhold information strategically. Not fabricating — controlling access to truth. Motivated by information leverage and middleman position preservation.

- **Hub intermediaries** (high centralization + high outward): Actively invest in communication infrastructure. Provide translation, standardization, dispute resolution. The Tang Chang'an / Constantinople model. Extract rents through facilitation, not obstruction.

The intermediary's disclosure rate feeds directly into channel_fidelity for any polity pair whose communication passes through that node. Replacing a high-disclosure intermediary with a low-disclosure one (through conquest, culture drift, or regime change) degrades the communication channel between endpoints, potentially collapsing cooperation.

### Parameters

No new parameters required. Communication channel properties are derived from:
- Trade graph connectivity → bandwidth
- Hop count × intermediary disclosure rates → fidelity
- Culture-space distance → commitment compatibility
- Existing defection_memory_halflife → repeated game memory
- Existing cooperation_growth_rate → cooperation accumulation

The communication model is fully emergent from the trade model and culture space.

---

## 15. Production Function & Resource Threshold Decisions (Resolves Q4 & Q5)

### Production Function: Keep Y = A × K^0.3 × E^0.7

The neoclassical production function is unchanged across all tech levels. The energy-budget formulation (E replaces L) is already in place; no further modification is warranted.

**What was tested (exponent_sweep_results.md):** The sweep explored variable exponents by tech regime (three-regime: pre-industrial / industrial / nuclear), interpolated exponents, and population-augmented accelerators. Results:

- Three-regime exponents: nominally 37% better on mean loss. Achieved by breaking DF timing and naphtha scramble timing — not better civilizational dynamics. The improvement is a loss-function artifact.
- Interpolated exponents: 8% better than baseline. Insufficient to justify the parameter overhead and instability.
- Population exponent on tech-growth accelerator (pop^0.5): causes runaway expansion, suppresses Dark Forest, fires the naphtha scramble in the Mesolithic. Fails all timing targets. Rejected.

**Why population doesn't need an explicit term:** Population enters the model indirectly through energy surplus → budget → expansion. Adding it to the production function or accelerator double-counts the effect and breaks competitive balance.

**Why the `accel_rate` table is sufficient:** The five-level table (0 / 0.002 / 0.008 / 0.025 / 0.120) already encodes five implicit growth regimes. Energy composition shifts (food → food+naphtha → food+naphtha+nuclear) produce the regime transitions through the budget. The production function does not need to track eras.

**One justified addition — Malthusian clamp in the energy layer:** For tech < 4, when population approaches carrying capacity, food surplus is clamped downward. This produces the Malthusian trap (population growth constrained by food ceiling, not by production function degeneracy) without requiring regime boundaries anywhere in the production or tech-growth logic. The clamp belongs in the food energy calculation and nowhere else.

### Resource Thresholds: Three-Stage Model (Detection → Exploitation → Strategic Valuation)

The fixed unlock sequence is retained for Exploitation thresholds only. Resources now have three decoupled stages:

**Stage 1 — Detection** (geology-dependent, any tech): A polity can observe surface deposits — bitumen seeps, alluvial gold, exposed pyra outcrops — long before it has the technology to exploit them. This is the stage at which sacred and cultural associations form. Historical analogues: Baku's eternal flames (natural gas seeps worshipped for millennia before petroleum), Mesopotamian bitumen waterproofing (surface tar pits exploited before distillation), salt licks as ritual sites before salt extraction infrastructure.

*Sacralization preservation:* Cultural encodings formed at Detection persist after industrial exploitation begins. A naphtha island that spent 800 ticks as a sacred flame site before industrialization retains that cultural texture in the simulation — detectable in the cultural layer as historical residue, potentially affecting inference_depth accumulation and contact posture for polities aware of the site's history.

**Stage 2 — Exploitation** (fixed tech sequence: naphtha ~5, pyra ~8): Tech-gated, not geology-gated. Detection and Exploitation are deliberately decoupled. A polity sitting on surface naphtha for millennia before tech 5 cannot yet refine it; the gap between Detection and Exploitation is where the sacred/cultural associations form and deepen.

**Stage 3 — Strategic Valuation** (event-triggered): The global fission discovery event (§2) instantly revalues pyra regardless of prior detection or exploitation state. A polity that has been mining pyra for industrial applications (catalysis, specialty alloys, high-temperature metallurgy) wakes up to find existing holdings are now existentially strategic. A polity with no pyra holdings wakes up to find it must acquire them or accept nuclear dependency. This is not gradual appreciation — it is a phase transition, identical in character to the overnight revaluation of every uranium deposit on Earth after Trinity.

**Interaction with §1 (Three-Regime Pyra Value):** The Strategic Valuation stage is the mechanism that drives pyra's value from "moderate industrial" to "maximum (3–5×)" at tech ≥ 8.5. The resource_value function's discontinuity at 8.5 is the simulation expression of the Strategic Valuation event. The two models are consistent.

**Interaction with §4 (Pyra Scramble as Narrative Engine):** The three-stage model deepens the human cost narrative. Parochial-culture polities on pyra-rich islands may have been in a Detection relationship with those deposits for centuries — the volcanic geology is woven into their cosmology, ritual practice, and cultural identity. Strategic Valuation, when it arrives via distant hegemon fission discovery, transforms geology they considered sacred into a target they had no hand in marking. The sacralization preservation mechanic makes this visible: the simulation records what those islands meant before they became strategic, and that record persists into the post-scramble state.
