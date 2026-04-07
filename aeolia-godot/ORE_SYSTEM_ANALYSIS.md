# ORE SYSTEM ANALYSIS — AEOLIA HISTORY ENGINE

**Status:** Research + Design Proposal
**Date:** 2026-04-05
**Scope:** How Fe/Cu/Au/Pu should drive civilizational development as emergent outcomes

---

## 0. THE GAP: WHAT'S THERE NOW VS. WHAT SHOULD BE

### Current state

`computeSubstrate()` in `MONOLITH_REFERENCE.jsx` (ported to `substrate.gd`) generates four mineral flags per archipelago:

```javascript
Fe: true                              // always present
Cu: rng() < 0.20                      // 20% flat chance
Au: rng() < (0.05 + avgH * 0.08)     // ~10% average; height-biased
Pu: rng() < (0.03 + size * 0.02)     // ~5% average; size-biased
```

`history_engine.gd` reads substrate for exactly one purpose: `substrate[arch]["crops"]["primary_crop"]` for the epidemiological crop-distance calculation. The minerals field is never accessed. The four ore flags are computed, stored in the substrate struct, displayed in the UI color-coded, and then do nothing.

The DESIGN_SPEC §10g documents the intended design in two sentences:

> "Fe is universal. Cu is the Bronze Age lottery ticket. Au drives trade and colonial motivation. Pu determines who goes nuclear."

None of these effects are implemented. This is the gap.

### Why this matters for the emergent-vs-prescribed problem

The history engine currently treats all archipelagos as fungible except for the `potential` score (a function of peak count, average height, and shelf size). Two archs with identical potential but different mineral endowments have identical trajectories. The differences the player sees — in tech levels, colonial relationships, population — derive entirely from geography-position effects (Dijkstra hop count, era of contact, extraction rates). There is no pathway by which an arch's resource endowment independently shapes what kind of civilization it becomes.

The redesign must give each ore a specific causal pathway that influences *which* civilizational outcomes become available, without prescribing *which* civilization achieves them.

---

## 1. GEOLOGICAL REALISM: WHAT AEOLIA'S PHYSICS ACTUALLY ALLOWS

Before designing ore effects, it's worth establishing whether the four ores make geological sense for a 95% ocean volcanic world with no continental crust.

### The constraint: no continental geology

Aeolia's interior structure is `small rocky/metallic core → high-pressure ice mantle → global ocean → thin volcanic crust`. There is no continental crust in the terrestrial sense. This eliminates entire classes of Earth ore deposit:

- **No Archean cratons** → no BIF (Banded Iron Formations, Earth's largest iron ore deposits), no kimberlites
- **No pegmatites** → no lithium, beryllium, REE, tantalum
- **No sedimentary basins** → no coal (except submarine, on drowned plateaus), no conventional oil (only offshore)
- **No river systems** → no placer deposits. All gold and heavy minerals are hard-rock only. This is a significant constraint with major civilizational consequences (see §2).

What *does* exist on volcanic ocean islands:

| Deposit type | What it contains | Formation |
|---|---|---|
| VMS (volcanogenic massive sulfide) | Cu, Zn, Pb, Au, Ag | Mid-ocean ridge / arc spreading; seafloor black smokers |
| Epithermal gold | Au, Ag, (Hg, Sb, As) | High-level hydrothermal near volcanic centers; typical of island arcs |
| Magmatic Fe-Ti | Fe, Ti (magnetite/ilmenite) | Differentiated intrusions in layered mafic bodies |
| Porphyry Cu | Cu, Mo, Au | Subduction-related arc plutonics; requires deeper, evolved magmatic systems |
| Laterite Ni-Co | Ni, Co (from Fe-rich basalt weathering) | Tropical weathering of ultramafic rocks |

The current four-ore design maps cleanly onto this geology:

**Fe (iron)** — Universal because basalt is ~8-12% FeO/Fe₂O₃ by weight. Every island has iron-rich rock. But *accessible metallic iron* is different from iron in basalt matrix. The universal flag correctly represents raw material availability; it says nothing about smelting capability.

**Cu (copper)** — 20% prevalence is geologically reasonable. Porphyry copper deposits cluster at subduction-zone island arcs (Pacific Ring of Fire analog). VMS deposits form at spreading centers. Both environments exist on Aeolia but are not universal. More importantly, *native copper* (requiring no smelting) occurs in hydrothermal settings. Early Anatolian copper use (~9000 BCE) involved hammering native copper — the first metallurgy doesn't require furnaces.

**Au (gold)** — Height correlation is correct. Epithermal gold deposits form in the upper 1-2 km of hydrothermal systems, close to volcanic centers. Taller peaks = larger, more active volcanic systems = more hydrothermal circulation. This is well-established in the geological record (Lihir deposit, Papua New Guinea; Ladolam deposit, Lihir Island; Crater Mountain, PNG — all high-elevation volcanic-island gold). ~10% overall prevalence is generous but appropriate for a world where gold has to drive enough trade to be interesting.

**Pu (fissile material)** — This is the fiction's geological weak point, acknowledged in-world. Natural Pu-239 doesn't occur; the proxy is uranium (U-235/U-238). Uranium deposits in island-arc settings come from granitic/felsic intrusions in evolved magmatic systems — large, long-lived volcanic systems where partial melting has concentrated incompatible elements. The size correlation is correct: larger islands with more complex volcanic histories are more likely to have the evolved, differentiated magma chambers that produce uranium-bearing felsic rocks.

### What's missing from the geological model: ore correlation

**Cu and Au should be correlated.** In both VMS and epithermal systems, copper and gold co-occur. An arch with Au should have a higher-than-20% probability of Cu, and an arch with Cu should have a higher-than-5% chance of Au. Currently they're sampled independently, producing geologically implausible scenarios (rich epithermal Au with no associated Cu mineralization is unusual).

**Pu should also correlate with Au.** Evolved granitic systems that produce uranium also tend to have epithermal gold. Currently they're on different axes (size vs. height) when they should partially overlap.

These correlations matter for simulation because they create realistic resource endowment clusters: either an arch is a rich hydrothermal province (Cu + Au + possibly Pu) or it's iron-only basaltic crust. The current binary lottery spreads ores more evenly than geology would.

Proposed fix in `computeSubstrate()`:
```javascript
const cuBase = rng() < 0.18;
// Au correlated with Cu (shared hydrothermal origin)
const auBase = rng() < (0.04 + avgH * 0.07 + (cuBase ? 0.06 : 0));
// Pu correlated with size AND height AND slightly with Au (evolved granitic systems)
const puBase = rng() < (0.02 + size * 0.015 + avgH * 0.01 + (auBase ? 0.02 : 0));
```

This produces ~18% Cu, ~8-12% Au (height-biased, Cu-correlated), ~4-6% Pu (size+height+Au biased). More importantly, it produces *provinces*: archs that drew the hydrothermal lottery tend to have both Cu and Au; those that didn't have Fe only.

---

## 2. EARTH METALLURGICAL HISTORY AND THE AEOLIAN DIVERGENCE

### Earth's canonical progression

1. **Chalcolithic / Copper Age** (~5500–3200 BCE in Near East): native copper cold-worked, then smelted from oxide/carbonate ores
2. **Bronze Age** (~3200–1200 BCE): Cu + Sn alloy; tin scarcity drives the first global commodity networks
3. **Iron Age** (~1200 BCE onward): iron smelting at scale; cheaper than bronze, democratizes metalwork
4. **Steel Age** (~500 BCE onward): deliberately produced high-carbon iron (wootz, Damascus, bloomery steel)
5. **Industrial** (~1760 onward): coke-fired blast furnaces → cheap steel → rails, steam engines
6. **Electrical** (~1880 onward): copper as conductor; telegraph, motors, power grid
7. **Nuclear** (~1940 onward): uranium as fuel/weapon

The critical bottleneck on Earth: **tin**. Bronze Age geopolitics was dominated by tin scarcity. Tin sources in Bronze Age Eurasia were limited to Cornwall (England), Afghanistan (Badakhshan), Sardinia, and a few other deposits — all far from major centers of civilization. The Bronze Age tin trade was the first global commodity network. The collapse of Bronze Age civilizations (~1200 BCE Sea Peoples event) was partly a tin trade disruption. Civilizations without tin access were stuck at the copper level.

### The Aeolian divergence: no tin

There is no Sn (tin) in Aeolia's four-ore system, and this is geologically correct. Tin deposits on Earth are typically associated with granitic intrusions in continental settings (cassiterite in granite-derived placer deposits, or tin-tungsten greisens). In a world without continental crust, tin is extremely rare or absent.

**This changes the entire Bronze Age analog.** Without tin:
- Copper doesn't alloy into true bronze → copper tools and weapons are softer, less militarily decisive
- The metallurgical progression skips bronze and goes from copper to iron directly
- OR: copper arsenide takes the role of bronze

The copper arsenide path is historically attested — many early "bronze" artifacts are actually Cu-As alloys, because arsenopyrite co-occurs with Cu sulfides in hydrothermal deposits. Smelting sulfide ores with co-mingled arsenopyrite naturally produces Cu-As, which is harder than pure copper. This phase doesn't require tin trade. It requires only a Cu-bearing arch with the right mineralogy.

This makes Cu distribution *more* strategically important, not less: Cu-having archs can independently develop harder metallurgy without any trade network. The trade motivation for Cu comes from deficit, not from needing tin to complement it.

### The iron smelting constraint on volcanic islands

On Earth, the transition to iron was constrained by:
1. **Charcoal supply**: forests must be cut and burned (Ireland was largely deforested for iron smelting by the medieval period)
2. **Furnace temperature**: 1500°C+ required for iron; 1100°C for copper
3. **Smithing knowledge**: iron must be worked hot and quenched correctly; copper is more forgiving

On volcanic islands with limited forest cover, constraint 1 is severe. Small islands have small forests. A civilization that industrializes charcoal production for iron smelting may deforest itself.

The DESIGN_SPEC timeline is explicit: `wood/charcoal → wind/tidal → expensive coal → oil → nuclear`. Coal is submarine, expensive, mined from coastal margins. This explains why iron smelting at scale is delayed: you need coal to smelt iron at industrial volumes, and coal requires offshore mining capability that only exists in the industrial era.

**Key implication:** Fe is universally available but industrially inaccessible until coal becomes cheap. Fe should gate industrial-era tech not because iron is rare but because *iron at scale* requires energy infrastructure that comes from coal mining. The universality of Fe removes it as a strategic variable in early eras — it's a gate that everyone will eventually unlock — and focuses early-era differentiation on Cu.

### Gold on a world without rivers

On Earth, most gold discoveries that triggered colonial expansion were placer gold — gold concentrated in river sediments by hydraulic sorting. California Gold Rush (1848), Australian gold rushes (1850s), Klondike (1896), Spanish Caribbean discoveries (1490s) — all placer. Placer gold requires no mining technology: you pan rivers. This is why it triggered mass civilian migration ("rushes") rather than requiring industrial capital.

On Aeolia, **there are no rivers.** Gold is exclusively in hard-rock deposits. To access gold, you need:
1. Geological knowledge to identify promising formations
2. Shaft mining into volcanic rock
3. Processing equipment to crush and sort ore

The "gold rush" dynamic — mass civilian exploitation requiring no capital — doesn't exist on Aeolia. Gold extraction is industrial from the beginning.

Earth parallel that fits better: the Witwatersrand deep gold mines of South Africa, which required industrial capital investment from the start and created a mining-industrial complex rather than a rush economy. Or the medieval European silver and copper mines (Rammelsberg, Falun) which were corporate enterprises requiring significant infrastructure.

**Implication for the simulation:** Au-bearing archs become attractive targets for *sustained colonial industrial investment*, not quick-extraction placer operations. The motivation is long-term extraction, not a gold rush. Au should inflate hegemon motivation with a cumulative effect: contact → reconnaissance → industrial investment → sustained extraction. This is the dynamic that creates colonies in the "extraction colony" mode (Congo, Bolivia) rather than the "settler colony" mode.

### Uranium geopolitics: the real Pu story

The Manhattan Project's uranium supply chain is the closest Earth parallel:
- Belgian Congo (Shinkolobwe mine) supplied ~80% of the Manhattan Project's uranium
- The US and UK jointly controlled all known uranium sources during WWII
- The Soviet atomic program was delayed partly by uranium access problems (until they secured Czech/East German sources and developed Kazakhstan deposits)

Post-WWII:
- USA: domestic (Colorado Plateau) + Belgian Congo sources
- USSR: Kazakhstan, Kyrgyzstan, plus Czech/East German satellite production
- France: African deposits (Niger, Gabon, Central Africa) → critical for nuclear independence from both superpowers
- Australia (Olympic Dam) and Canada (Athabasca Basin) became major producers later

The geopolitical pattern: uranium deposits are geographically concentrated, strategically critical, and motivate intense imperial competition that overrides normal cost-benefit calculations. The Belgian Congo was strategically insignificant by most measures but became one of the most closely watched territories on Earth because of Shinkolobwe.

On Aeolia: **Pu-bearing archs become strategic objectives in the nuclear era regardless of other attributes.** A small arch with Pu and no other resources goes from "bypassed" to "garrison" the moment nuclear capability becomes a competitive concern. The `pu_denial_value` mechanic should override the normal `motivation/controlCost` calculation entirely.

---

## 3. ERA-BY-ERA DESIGN: HOW EACH ORE SHOULD FUNCTION

### Antiquity (~-20,000 to -5,000 BP)

**Fe:** No direct effect. All archs have it; none can exploit it at scale. The only exception — magnetite beach sand near volcanic coasts can be cold-worked into low-grade iron objects — is a craft industry, not a metallurgical tradition. No tech modifier.

**Cu:** The crucial early differentiator. Native copper can be cold-worked (no furnace required) in hydrothermal settings. As fire-making and kiln technology develops for ceramics, the same kilns can smelt copper oxide/carbonate ores. The transition from pottery kiln to copper smelter is historically well-attested.

*Design:* Cu-bearing archs receive a `tech` bonus at the END of antiquity, representing 10,000+ years of metallurgical head start:
```
tech[i] += 0.8 if minerals[i].Cu
pop[i] *= 1.08 if minerals[i].Cu  // slightly larger pop (better tools = better agriculture)
```

**Au:** Not extractable without established metallurgy and hard-rock mining. Not detectable by accident (no placer). No effect in antiquity.

**Pu:** Undetectable without scientific capability many eras away. No effect.

### Serial Contact Era (~-5,000 to -2,000 BP)

**Fe:** Still no mass effect. Craft iron production (meteoritic iron, volcanic native iron near fumaroles) exists as prestige items. Iron-rich soils support slightly higher agricultural productivity, but this is already captured in `potential`. No new modifier.

**Cu:** Primary differentiator. Cu-bearing archs can export metal goods (weapons, tools, ornaments) in demand everywhere. This creates the first ore-driven trade incentive: Cu-deficit archs preferentially trade with Cu-bearing archs.

*Design for Cu:*
- Cu-bearing arch: `tech += 0.5`, `tradeIntegration += 0.06` (metal goods export)
- Cu-deficit arch that contacts a Cu-bearing arch: Thompson α inflation of `+1.5` for edges toward Cu-bearing archs (they've encountered metal goods and want the source)
- Cu-deficit arch without any Cu connection: `tech_soft_cap = 4.5` (not a hard ceiling yet — can still develop through non-metallic routes, but slower)

This is the Aeolian equivalent of the Bronze Age copper route structure: civilizations will travel far to maintain metal supply chains.

**Au:** In this era, gold begins to function as a store of value and prestige display, but only where Cu metallurgy already exists to mine and work it. Hard-rock Au extraction requires Cu tools.

*Design for Au (conditional on Cu also present):*
- Cu + Au arch: `tradeIntegration += 0.10`, becomes a "monetary hub" that increases all trade values through it
- Cu + Au arch: `hegemon_motivation_multiplier = 1.3` for contact decisions (already worth visiting)
- Au without Cu: no direct effect yet (can't mine it)

**Pu:** No effect. Not detectable.

### Colonial Era (~-2,000 to -500 BP)

**Fe:** Charcoal-smelting of iron begins at the colonial/industrial boundary. Wood charcoal can achieve ~1100°C with bellows — enough for wrought iron. Colonial-era civilizations begin producing iron tools at craft scale. Fe is universal, so this creates no strategic asymmetry, but it establishes `ironcraft_tradition` as a precursor state.

**Cu:** The critical gate for future industrialization. An arch that reaches the colonial era without Cu access cannot independently develop the metallurgical foundation required for later iron-working. Copper metallurgy teaches fire control, the bellows, and alloy ratios — knowledge that transfers to iron smelting.

*Design for Cu:*
- Cu-deficit arch NOT connected by trade to a Cu-bearing arch: `tech_ceiling = 4.5` (pre-industrial hard cap)
- Cu-deficit arch with trade access to Cu-bearing arch: `tech_ceiling = 6.0` (technology transfer possible but slower)
- Cu-bearing arch: `tech_ceiling = 7.5`, normal industrialization path

**Au:** This is where Au earns its description as the primary colonial motivation driver. Au on Aeolia is:
1. A monetary medium enabling credit and long-distance trade without barter
2. A direct financing mechanism for expeditions (Au-backed credit)
3. A self-reinforcing colonial incentive (the expedition that finds gold funds three more)

*Design for Au:*
- Au-bearing arch: `hegemon_motivation_multiplier = 2.0` for the contact decision
- Au-bearing arch in Reach sphere: colony probability increases (extraction motive), not client
- Au-bearing arch in Lattice sphere: tributary status more likely (Lattice extracts tribute-in-kind)
- For Thompson Sampling: any edge toward a rumored Au-bearing arch gets `α += 2.5` once rumors reach the hegemon

**Pu:** Still no effect. Uranium is an unknown element at this tech level.

### Industrial Era (~-500 to -200 BP)

**Fe:** The Aeolian industrial revolution requires Fe + coal. Fe is universal; coal is not. The differentiation comes from the Cu/metallurgical foundation:

*Design:*
- Fe + Cu tradition + coal access (proxied by `potential > threshold`): full industrialization, `tech_ceiling = 8.0`
- Fe + no Cu + coal: partial industrialization, `tech_ceiling = 6.5` (can make iron but lacks metallurgical know-how)
- Fe + Cu + no coal: excellent metalwork tradition but craft-scale; `tech_ceiling = 7.0`

**Cu:** Transitions from metallurgy to *electricity* in this era. The telegraph (submarine cable), electric motors, and power grid are all copper-dependent. Cu-bearing archs can build electrical infrastructure; Cu-deficit archs cannot build the submarine cable network.

*Design for Cu:*
- Cu-bearing arch: `tech_growth_rate *= 1.15` (electrical infrastructure accelerates industrial development)
- Cu-bearing arch in Reach sphere: higher `tradeIntegration` (copper is the most strategically important industrial commodity after coal)
- Cu-bearing arch in Lattice sphere: absorbed as electrical node in the tidal-industrial system

**Au:** The gold standard consolidates in the industrial era. Au-bearing archs that have been extracted since the colonial era have partially depleted deposits, but the mining infrastructure is now industrial-scale.

*Design for Au:*
- Au-bearing colonized arch: `extraction_rate += 0.03` (industrial mining intensifies; increases both extraction total and sovereignty drift)
- Sovereign Au-bearing arch: `ambition += 0.08` (knows it has something others want; builds defensive capacity)
- Au-bearing Reach colony: minor additional `pop[reach_arch]` multiplier (gold standard → credit expansion)
- Anti-colonial feedback: Au extraction strain accelerates `cohesion` growth of the colonized arch

**Pu:** The Curie/Rutherford moment. An arch with Pu deposits and industrial survey capability (`tech >= 6.0`) gains `uranium_discovered` flag. This is a precursor state — no tech effect yet, but radioactivity is detectable with industrial instruments at range, seeding the nuclear-era scramble.

*Design:*
- Pu-bearing arch with `tech >= 6.0`: gains `uranium_discovered` flag
- `uranium_discovered` flag inflates Thompson Sampling α for hegemon edges toward that arch even before nuclear era starts

### Nuclear Era (~-200 to 0 BP)

**Fe:** Background infrastructure. Universal; no differential effect at this point.

**Cu:** Electrical grid for global information infrastructure. Cu-bearing or Cu-connected archs have better information networks → higher `otherAwareness` accumulation rate. Relevant to the Dark Forest mechanic: better cable networks = earlier radio intercept capability.

*Design:*
- Cu-bearing arch: `otherAwareness_accumulation_rate += 0.02` per tick
- Arch without Cu access cannot build the cable network → `tradeIntegration` ceiling capped

**Au:** Monetary system support and nuclear-grade electronics (gold contacts, radiation shielding components). Minor effect.

*Design:*
- Au-bearing arch at nuclear tech tier: `tech[i] += 0.3` (precision manufacturing advantage)
- Au-bearing archs in contact situations: mild `openness` bonus (they have something to offer diplomatically)

**Pu:** The gate. The critical design.

*Design — absolute nuclear tech ceiling:*
```
has_pu_access(i) = minerals[i].Pu
                 OR (sovereign[i] >= 0 AND minerals[sovereign[i]].Pu)
                 OR treaty_with_pu_bearer(i)  // future mechanic

tech_ceiling = 10.0 if has_pu_access(i) else 8.5
tech[i] = min(tech[i], tech_ceiling)
```

*Pu late scramble:*
Once any power reaches `tech >= 8.5`, every uncontrolled Pu-bearing arch becomes a strategic priority regardless of normal motivation/controlCost:
```
if (reach_tech >= 8.5 OR lattice_tech >= 8.5) AND minerals[i].Pu AND NOT claimed[i]:
    motivation_override = 999   // Pu denial value overrides normal calculation
    → guarantee late contact in nuclear era
```

This is the Aeolian Belgian Congo moment: a previously-bypassed small arch suddenly becomes the most contested territory on the planet because it has uranium.

---

## 4. ORE DISTRIBUTION AND THE REACH/LATTICE ASYMMETRY

### The Reach: Tall-Peak, Spread Islands, Mid-Latitude

Geographic profile:
- Mid-latitude westerlies → reliable sailing winds → maritime trade capacity
- Spread island spacing → competitive culture, strong inter-island identity
- **Tall peaks** (`avgH` high) → high hydrothermal activity → **elevated Au probability**
- Several major islands with diverse geologies → statistically likely to have Cu somewhere
- Settler archipelago explicitly described as having "richer mineral deposits including uranium" → **Pu confirmed**

Expected mineral endowment: near-universal Fe (all volcanic), moderate Cu, **high Au** (height bias), Pu in the settler archipelago.

**What this produces politically (emergent, not prescribed):**

The Reach's emmer-crop mercantile culture (`surplus: 0.65, labor: 0.70` → Mercantile mode of production) combined with Cu metallurgy and Au monetary system creates optimal conditions for commercial expansion. The Reach merchant houses have:
1. A metallurgical tradition (Cu from early hydrothermal contact)
2. A monetary system (Au enabling credit-financed expeditions)
3. A competitive culture that rewards finding and exploiting new resources

The Reach goes looking for gold not because it's programmed to but because its mercantile political economy systematically rewards it. This is the emergent outcome: Cu-tradition + Au-monetary-system + competitive-commercial-culture organically produces thalassocratic projection.

**The settler colony and Pu:**

The settler archipelago's uranium endowment explains why it enables the nuclear breakthrough that makes the Reach dominant. In simulation terms, making the settler archipelago large (biasing Pu probability) and tall (biasing Au probability) creates a world where the colony is both rich enough to outgrow the metropole AND has the resource that eventually enables nuclear-era primacy. This should be an emergent property of the size/height correlations, not a hard-coded assignment.

### The Lattice: Dense Cluster, Tidal Flats, Tropical

Geographic profile:
- Dense core cluster → cooperative, hydraulic governance
- Wide tidal-flat shelf, **low peak height in core cluster** → **lower Au probability**
- Tropical → paddi crop → subject political culture → state controls ore extraction
- Outer garrison islands extend toward more evolved volcanic systems → **Pu probably in the periphery, not the core**

Expected mineral endowment: moderate Fe, **low-to-moderate Cu** (low-altitude core doesn't favor deep hydrothermal systems), **low Au** (flat peaks), Pu in outer garrison chain islands.

**What this produces politically:**

The Lattice's paddi-crop hydraulic culture (`surplus: 0.85, labor: 0.25` → Asiatic mode of production) combined with lower Cu/Au endowment produces a fundamentally different political economy:

1. Lower metallurgical tradition (less Cu) → the Lattice's industrial development is *later* than the Reach's despite equal agricultural surplus
2. Lower monetary base (less Au) → the Lattice relies on tribute-in-kind rather than monetary exchange → fits perfectly with the Asiatic mode
3. Pu in the outer garrison chain → the Lattice's nuclear capability is tied to its *defensive perimeter*, not its core

**The garrison chain and Pu:**

The Lattice's nuclear program is politically complex in a way the Reach's isn't: the Reach's uranium is in its own settled territory (controlled). The Lattice's uranium is in the outer garrison islands — the zone of peripheral raiders and contested sovereignty. The Lattice must maintain the garrison chain *both* to defend against peripheral threats *and* to secure its fissile material supply. Weakening the garrison chain (which happens during dynastic transitions) potentially compromises nuclear capability. This is an emergent political vulnerability, not a prescribed one.

### The Ore Asymmetry Table

| | Reach | Lattice |
|---|---|---|
| Cu presence | Moderate-high (competitive culture exploited it) | Low-moderate (hydraulic culture internalized it) |
| Au presence | High (tall peaks, hydrothermal) | Low (flat core, tidal flats) |
| Pu location | Core territory (settler colony) | Periphery (garrison chain) |
| Monetary system | Gold-backed mercantile exchange | Tribute-in-kind, non-monetary |
| Industrial path | Cu-tradition → electrical → nuclear | Agricultural surplus → tidal-industrial → nuclear |
| Nuclear security | High (Pu in settled core) | Medium (Pu in contested outer ring) |
| Colonial motivation | Au + Pu (primary drivers) | Pu (primary, late); tribute/population (early) |

This divergence is not prescribed. It emerges from:
1. The substrate generation correlating tall peaks (Reach) with higher Au
2. The Reach's competitive mercantile culture exploiting ore endowment more aggressively
3. The Lattice's agricultural surplus reducing the need for monetary exchange

---

## 5. CONCRETE SIMULATION CHANGES TO `history_engine.gd`

These are the specific changes needed to wire `substrate[i]["minerals"]` into the simulation.

### 5.1 Antiquity Phase: Copper Tech Seed

At the end of the antiquity population initialization loop:

```gdscript
# Copper age head start: Cu-bearing archs developed metallurgy earlier
for i in range(N):
    if substrate[i]["minerals"]["Cu"]:
        tech[i] += 0.8   # ~2,000-year metallurgical head start
        pop[i] *= 1.08   # better tools → better agriculture → more people
```

### 5.2 Serial Contact Phase: Cu Trade Incentives and Au Hubs

In the serial contact per-arch loop:

```gdscript
var arch_cu = substrate[i]["minerals"]["Cu"]
var arch_au = substrate[i]["minerals"]["Au"]

# Cu-bearing arch exports metal goods
if arch_cu:
    status_data[i]["tradeIntegration"] += 0.06
    tech[i] += 0.5

# Cu + Au arch becomes a monetary hub
if arch_cu and arch_au:
    status_data[i]["tradeIntegration"] += 0.10
    # Tag for elevated hegemon motivation when contact decision is made

# Cu-deficit arch tagged for trade motivation
if not arch_cu:
    status_data[i]["cu_deficit_motivation"] = true
    # Thompson α inflation toward Cu-bearing neighbors (when Thompson Sampling implemented)
```

### 5.3 Colonial Phase: Au Motivation Multiplier and Cu Tech Ceiling

When evaluating the contact decision for each arch:

```gdscript
var arch_cu = substrate[i]["minerals"]["Cu"]
var arch_au = substrate[i]["minerals"]["Au"]

# Au dramatically increases colonial motivation
if arch_au:
    motivation_modifier *= 2.0

# Cu-deficit tech ceiling (enforce at era boundary)
if not arch_cu:
    var has_cu_access = _check_cu_trade_access(i, substrate, claimed, adj)
    if not has_cu_access:
        tech[i] = minf(tech[i], 4.5)

# Au extraction increases colonial yield
if arch_au and status_data[i]["status"] == "colony":
    extraction_rate_for[i] += 0.04
```

The helper function:

```gdscript
static func _check_cu_trade_access(arch_idx: int, substrate: Array, claimed: Array, adj: Array) -> bool:
    # An arch has Cu access if any neighbor in the same sphere has Cu
    for nb in adj[arch_idx]:
        if claimed[nb] == claimed[arch_idx] and substrate[nb]["minerals"]["Cu"]:
            return true
    return false
```

### 5.4 Industrial Phase: Fe-Cu Synergy and Electrical Infrastructure

At the industrial tech update:

```gdscript
var has_cu = substrate[i]["minerals"]["Cu"]
var has_au = substrate[i]["minerals"]["Au"]
var has_pu = substrate[i]["minerals"]["Pu"]

# Cu = electrical infrastructure → accelerated industrial development
if has_cu:
    tech[i] = minf(tech_ceiling, tech[i] + 0.4)
    # (tech_ceiling for Cu-bearer is already higher from colonial-era rules)

# Au = gold standard → expanded capital base
if has_au:
    if status_data[i]["status"] in ["colony", "client"]:
        extraction_rate_for[i] += 0.03
        pop[i] -= pop[i] * 0.03
        total_extracted += pop[i] * 0.03
    if status_data[i]["sovereignty"] > 0.6:
        # Sovereign Au-bearer knows its value and builds defense
        status_data[i]["cohesion"] = minf(1.0, status_data[i].get("cohesion", 0.5) + 0.08)

# Pu discovery event (precursor)
if has_pu and tech[i] >= 6.0:
    status_data[i]["uranium_discovered"] = true
    # Will inflate Thompson α for hegemon edges toward this arch
```

### 5.5 Nuclear Phase: Pu as Absolute Gate

```gdscript
# Pu access check
static func _has_pu_access(arch_idx: int, substrate: Array, sovereign: Array) -> bool:
    if substrate[arch_idx]["minerals"]["Pu"]:
        return true
    var sov = sovereign[arch_idx]
    if sov >= 0 and substrate[sov]["minerals"]["Pu"]:
        return true
    return false

# Apply nuclear tech ceiling
for i in range(N):
    var pu_access = _has_pu_access(i, substrate, sovereign)
    var nuclear_cap = 10.0 if pu_access else 8.5
    tech[i] = minf(tech[i], nuclear_cap)

# Late scramble: Pu denial value
# Once any power approaches nuclear threshold, unclaimed Pu arches become priority targets
var any_near_nuclear = tech[reach_arch] >= 8.5 or tech[lattice_arch] >= 8.5
for i in range(N):
    if any_near_nuclear and not claimed[i] and substrate[i]["minerals"]["Pu"]:
        status_data[i]["pu_strategic_flag"] = true
        # Guarantee late contact in nuclear era (will be absorbed by whichever power gets there first)
```

### 5.6 Sanity Checks for Hegemon Pu Access

```gdscript
# Verify hegemons have Pu access — should emerge naturally from geography,
# but log failure as a seed-specific anomaly rather than crashing
var reach_has_pu = _has_pu_access(reach_arch, substrate, sovereign)
var lattice_has_pu = _has_pu_access(lattice_arch, substrate, sovereign)

if not reach_has_pu:
    push_warning("Seed %d: Reach lacks Pu access — unipolar nuclear world possible" % p_seed)
if not lattice_has_pu:
    push_warning("Seed %d: Lattice lacks Pu access — Reach monopolar world possible" % p_seed)
```

Per §0 of the DESIGN_SPEC: seeds where one hegemon lacks uranium are valid. They produce worlds where nuclear capability is monopolar — one hegemon reaches tech 10, the other caps at 8.5. The Dark Forest break happens at a different moment (the tech-10 power overflies the tech-8.5 power at will; the reverse is not true). These are the interesting seeds, not the broken ones.

---

## 6. ORE-DRIVEN TRADE ROUTES AS EMERGENT STRUCTURES

### The copper route parallel

On Earth, the Bronze Age tin trade created the first truly long-distance commodity networks. Tin was required for bronze but available only in a few locations. Civilizations 3,000+ km from tin sources maintained trade routes specifically to maintain metallurgical capability — the trade route was an existential military necessity (bronze weapons vs. stone weapons).

On Aeolia, without tin, the equivalent is **copper**. Cu-deficit archs that have been contacted by a Cu-bearing civilization will develop persistent Thompson Sampling priors for edges toward their Cu source. This is the mechanism that creates the Aeolian "tin routes" — except they're copper routes, and they form organically from the deficit-motivation mechanic.

The difference between stimulant trade and ore trade is important:
- **Stimulants** drive *volume* trade (you need them regularly, they're consumed, they create ongoing relationships)
- **Ores** drive *structural* trade (Cu access is a prerequisite for metallurgical capability; losing it means losing the capacity to upgrade tools and weapons)

A Cu trade route established in the serial era becomes critical in the industrial era (electrical infrastructure requires more copper, not less) and existential in the nuclear era (copper cable networks are how SIGINT works, how the cable economy operates). The same route carries different stakes at each transition.

### Deep-sea mining in the industrial era

The submarine plateau system is already the simulation's exploration graph. In the industrial era, VMS deposits on plateau surfaces become mineable — hydrothermal black smoker fields that deposit Cu, Zn, Au, and Ag as massive sulfide mounds on the seafloor.

This creates a second pathway to Cu and Au that removes the geographic lottery for industrial-era civilizations: any arch with plateau access (`edgeCount[i] >= 2`) and industrial technology (`tech >= 6.5`) could receive bonus Cu/Au access from submarine mining. This would allow late-developing archs to bypass the initial ore scarcity that constrained them in earlier eras — analogous to how the Haber-Bosch process bypassed nitrogen scarcity in the industrial era.

This mechanic doesn't require new data structures: `edgeCount` is already computed in `computeSubstrate()`. An industrial-era check of `edgeCount * tech_factor` could grant partial Cu access to plateau-adjacent archs without their own surface Cu deposit.

---

## 7. LOSS FUNCTION DESIGN: VERIFYING EMERGENCE WITHOUT PRESCRIBING OUTCOMES

These terms detect whether ore-driven development is emerging correctly. They should be *violated* if minerals have no effect, and *satisfied* by a wide range of specific civilizational outcomes. No term specifies who achieves what — only whether the structural relationship between ore and development holds.

### 7.1 Cu-Trade Correlation Term

**Hypothesis:** Cu-deficit archs should be more trade-integrated than Cu-rich archs of equivalent size and position, because they're seeking Cu through trade.

```
L_cu_trade = -corr(cu_deficit_flag, tradeIntegration | era ∈ {serial, colonial})

Expected: +0.2 to +0.4 positive correlation (Cu-deficit archs seek integration)
Violation: negative correlation (Cu-deficit archs are more isolated)
```

Violation would indicate the ore system is not creating the trade motivation that should exist. A Cu-deficit civilization with no metallurgical tradition has strong incentive to access metal goods through trade — if this isn't showing up as higher tradeIntegration, the mechanic isn't wired correctly.

### 7.2 Au-Colonial Motivation Term

**Hypothesis:** Au-bearing archs should be colonized at higher rates than their `potential` and hop-count alone would predict.

```
L_au_colony = residual(P(colonized) | potential, hopCount) for Au_bearing vs non_Au_bearing

Run regression: colonized ~ potential + hopCount
Measure residual for Au-bearing archs
Expected: Au-bearing archs colonized at ~1.5-2.0× baseline rate (controlling for position)
Violation: no significant Au coefficient (Au not driving contact motivation)
```

This doesn't specify which civilization colonizes them, or when. It only verifies that Au creates the incentive structure that should exist.

### 7.3 Pu-Nuclear Gate Hard Constraint

**Hypothesis:** No arch should achieve `tech >= 9.0` without Pu access in its sovereignty chain.

```
L_pu_gate = max(0, tech[i] - 8.5) for all i where !has_pu_access(i)

Zero penalty if all non-Pu archs stay at or below 8.5
Hard constraint violation: any non-Pu arch reaching tech 10.0
```

This is the strongest term — a hard physical constraint, not a statistical pattern. It should never be violated.

### 7.4 Cu-Metallurgical Foundation Term

**Hypothesis:** Fe-only archs (no Cu, no Cu trade access) should not independently industrialize.

```
L_cu_foundation = Σ over independent archs (not colonized at ERA 4):
    penalty += max(0, tech[i] - 5.0) * (1 - has_cu_access_ever(i))

Zero penalty if Fe-only archs stay pre-industrial
Does not penalize Fe-only archs that industrialize via technology transfer
```

A Fe-only arch can still industrialize — but only through the realistic path of technology transfer from a Cu-metallurgy civilization, not through independent development.

### 7.5 Ore Asymmetry → Political Economy Divergence Term

**Hypothesis:** The hegemon with more total Au in its sovereignty sphere should show higher cumulative extraction.

```
L_au_divergence = sign(au_sphere_reach - au_sphere_lattice)
                * sign(total_extracted_reach - total_extracted_lattice)

Must equal +1 (greater Au sphere → greater extraction)
Penalize if -1 (more Au but less extraction — Au not driving behavior)
```

This doesn't prescribe which hegemon has more Au. If the Lattice happens to have an unusually Au-rich colony chain on a given seed, the Lattice should show higher extraction. The term only verifies the *relationship* holds.

### 7.6 Pu Late-Scramble Term

**Hypothesis:** Once nuclear capability is known, previously-bypassed Pu-bearing archs should be absorbed into sovereignty spheres.

```
L_pu_scramble = count(Pu_bearing archs with status=="bypassed" at nuclear era) * penalty_weight

Zero penalty if all Pu-bearing archs are in a sovereignty sphere by Dark Forest break
Penalize proportionally to unclaimed Pu archs remaining at story present
```

Verifies that fissile material doesn't remain strategically inert in the nuclear era.

### 7.7 Path Diversity Anti-Prescription Term

**Hypothesis:** Adding ore effects should not make civilizational outcomes more uniform. Cu-bearing archs with similar potential should have *higher* variance, not lower, because ore opens multiple paths rather than prescribing one.

```
L_diversity = -variance(tech[i] at ERA 4 | Cu=true AND similar_potential)

Penalize LOW variance: all Cu-bearing archs reaching identical tech levels
Reward HIGH variance: Cu is necessary but not sufficient; paths diverge
Expected: higher variance than in Fe-only archs (ore opens paths, doesn't guarantee them)
```

This term acts as a safeguard against over-determinism. If the ore system causes all Cu-bearing archs to mechanically hit the same tech ceiling at the same era, the system is prescribing rather than enabling.

---

## 8. SYNTHESIS: WHAT THE REDESIGNED ORE SYSTEM PRODUCES

With these changes, the four ores function as follows:

**Fe:** Background infrastructure. Universal but unlocked by the energy transition (coal mining). Fe's universality removes one axis of inequality and focuses early-era differentiation on Cu, Au, and Pu. Its effect is that *industrialization requires Fe + coal* — a gate that everyone eventually passes if they have the energy infrastructure — rather than creating strategic asymmetry. This is historically correct: iron is everywhere; the knowledge and energy to use it is what's rare.

**Cu:** The civilizational bootstrapper. Having copper in the early eras (or accessing it through trade) is the precondition for everything that follows: copper metallurgy → iron-scale smelting → electrical infrastructure → industrial base for nuclear development. Cu creates the first emergent trade routes (deficit archs seek supply), the first technology-transfer relationships (Cu-bearing archs teach smelting), and the first asymmetry between civilizations that develop independently and those that require external input. Cu is the "Bronze Age lottery ticket" that compounds across 10,000 years — and the compounding means that Cu-deficit in the serial era shows up as industrial-era disadvantage. The 20% prevalence means Cu-rich archs are the minority, which correctly makes Cu access a strategic concern rather than a universal baseline.

**Au:** The colonial amplifier and monetary seed. Au transforms trade from barter-exchange into credit-financed expansion. Au-bearing archs attract colonial attention proportionally to their endowment — not because the simulation tells the hegemon to go there, but because the monetary incentive structure makes those expeditions reliably profitable (and on Aeolia, unlike Earth, gold requires industrial extraction from the start, which means the value goes specifically to whoever can build a mine, not whoever shows up with a pan). Au also creates the internal tension of colonial extraction: the more Au is extracted, the more cohesion builds in the colonized population. Au is the mechanism connecting ore endowment to the sovereignty-trade trajectory.

**Pu:** The nuclear gate and late-era strategic scramble trigger. Inert until the nuclear era, then the single most consequential geographic variable in the simulation. The late scramble for Pu-bearing unclaimed archs should be one of the most dramatic periods of the simulation — equivalent to the Scramble for Africa but compressed into two or three ticks and explicitly motivated by fissile material. The Reach-Lattice asymmetry (Reach has Pu in settled core; Lattice has Pu in contested periphery) creates structurally different nuclear-era strategies without prescribing them.

Together, the four ores create a substrate of civilizational opportunity and constraint that interacts with the crop-political culture system (already implemented) to produce divergent outcomes from similar starting conditions. A Cu-bearing paddi arch (early metallurgy in a hydraulic agricultural system) develops differently than a Cu-bearing emmer arch (early metallurgy in a mercantile competitive system). This is the interaction matrix that DESIGN_SPEC §10g's open question 12 defers to: "the real political science lives in the combination of crop × ore, not in either system alone."

---

## 9. APPENDIX: GEOLOGICAL NOTES FOR AEOLIA WORLDBUILDING

### On the absence of tin and what it implies for historical periodization

The Bronze Age is the longest period of continuous metallurgical civilization on Earth (~2,000 years). Its absence on Aeolia — replaced by a shorter copper-arsenide phase — means:
1. The "long bronze stasis" of Earth history doesn't exist on Aeolia
2. The transition from copper to iron happens faster (no intermediate bronze plateau)
3. But iron requires coal, and coal is expensive → the transition to iron takes longer than on Earth
4. Net result: a compressed copper phase followed by a long "pre-industrial charcoal iron" period, then a rapid jump to coal-industrial when offshore mining matures

This fits the Aeolian energy timeline perfectly: the "tidal-industrial" phase (which has no Earth parallel) occupies the gap where Earth has cheap-coal blast-furnace iron.

### On submarine VMS as late-era Cu/Au source

VMS (volcanogenic massive sulfide) deposits on plateau surfaces represent the largest untapped ore reserve on Aeolia. These are the "black smokers" of the deep ocean — currently inaccessible at 100-300m water depth, but technologically reachable in the industrial era.

The significance: deep-sea mining removes the geographic lottery for Cu in the industrial era. Any arch with plateau access and industrial technology can reach Cu. This transition (from geographic endowment to technology-mediated access) mirrors Earth's Industrial Revolution transformation of resource geography. The arc from "Cu-bearing archs control metallurgy" (serial era) to "any industrial arch can mine submarine VMS" (industrial era) is already implicit in the simulation's plateau graph — it only needs a tech-threshold unlock.

### On the "Pu" fiction and uranium geology

The substitution of "Pu" for "U" is a narrative convenience acknowledged in the DESIGN_SPEC. The geological mechanism is:

- The geological presence is **uranium** (U-235/U-238 in granitic felsic intrusions)
- Industrial-era science discovers radioactivity (~Curie/Rutherford analog moment)
- Nuclear-era engineering produces Pu-239 from U-238 in reactors (same as Earth's actual nuclear weapons path)
- The `Pu` flag represents *geological uranium presence*, not manufactured plutonium stocks

This doesn't require any code change. But it matters for the `_has_pu_access()` logic: an arch with `Pu=true` has uranium ore deposits. An arch without `Pu=true` cannot build reactors without trading for processed fuel from a Pu-bearing sovereign — which is itself a political relationship with specific sovereignty implications.

The Reach's settler colony having Pu (confirmed in lore doc 03) is the geological explanation for why that colony became the economic and military center of gravity: it had harbor geography AND mineral endowment AND wind corridor position simultaneously. The substrate generation system should be capable of producing this outcome organically (large arch → higher Pu probability; tall peaks → higher Au probability), which means the settler colony's dominance is an emergent consequence of geography rather than a predetermined result.

---

*See also: DESIGN_SPEC.md §10g (Mineral Resources), HISTORY_ENGINE_ANALYSIS.md, 01_PLANET_AND_PHYSICS.md §Internal Structure, 05_TECHNOLOGY.md §Energy Sequence*
