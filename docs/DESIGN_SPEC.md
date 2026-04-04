# AEOLIA SIMULATION ENGINE — DESIGN SPEC v0.4

## Architecture: 50-Year Tick Simulation with Imperfect Information

---

## 0. CORE DESIGN PRINCIPLE — HEGEMONIC CONTINGENCY

The Reach and the Lattice are not special civilizations. They are
**geographically fortunate** civilizations. Their primacy at Story
Present is the product of specific environmental conditions — wind
belts, shelf geometry, mineral deposits, island spacing — not
civilizational superiority.

The simulation must be capable of producing:

- **3–5 independently sophisticated civilizations** per seed.
  Writing, metallurgy, complex states, philosophical traditions —
  all developed without hegemon contact. These are the Mughals,
  Ottomans, Songhai, Majapahit of Aeolia. They are not "contacted
  primitives." They are civilizations whose geographic hand didn't
  include the specific combination that produces nuclear-era
  projection capability.

- **Seeds where the hegemons are different.** The two most-
  antipodal large archs become Reach and Lattice, but the
  simulation should occasionally produce worlds where a third
  power reaches comparable tech independently, or where the
  "hegemons" are less dominant and the world at Story Present
  is genuinely multipolar.

- **No arch that is inherently inferior.** A small atoll with
  2 peaks and poor resources is *disadvantaged*, not lesser.
  Given 100,000 years of independent development, it produced
  its own language, navigation tradition, oral literature, and
  cosmology. The tech delta at contact reflects geography, not
  capacity.

### What Makes a Hegemon (Geographic Conditions)

**Thalassocratic projector (Reach-type):**
- Mid-latitude westerlies (reliable sailing winds)
- Spread island spacing → competitive maritime culture
- Mineral endowment including fissile material
- A settler archipelago along wind corridors

**Hydraulic absorber (Lattice-type):**
- Dense core cluster → unification geography
- Wide tidal-flat shelf → mass agriculture → population base
- Peripheral raider pressure → defensive garrison culture
- Sufficient isolation for bureaucratic maturation

**Independent power (Mughal/Ottoman-type):**
- Large arch (high peak count, high potential)
- Moderate connectivity (trades but isn't on a critical path)
- Agricultural base sufficient for independent industrialization
- Contact late enough to absorb techniques selectively

These conditions are computed from `arch.geo`, not assigned.
The Reach and Lattice are initialized from the most-antipodal
pair, but any arch meeting the geographic criteria for
independent power should develop accordingly in the simulation.

### The Narrator Nudge (Optional, Ambiguous)

The bible's substrate engineers (Narrators 5 and 7) may have
tuned the geography to produce exactly two peer civilizations at
the nuclear threshold. Or they may not have. The simulation does
not encode this — it computes from geography. If the geography
happens to produce two and only two nuclear-capable powers on
most seeds, that's either evidence of design or evidence that
the geographic conditions for nuclear hegemony are rare. The
ambiguity is the point.

---

## 1. TICK STRUCTURE

| Phase | Span | Resolution | Notes |
|-------|------|-----------|-------|
| Antiquity | −20,000 to −5,000 BP | 1 batch | No inter-arch interaction. Independent growth + substrate seeding. |
| Active Sim | −5,000 to 0 BP | 100 ticks × 50yr | All interesting dynamics. |

### Per-Tick Pipeline (8 stages)

```
for each tick t (−5,000 to 0, step 50):

  1. RUMOR PROPAGATION
     Trade chains carry garbled information 2-3 hops ahead of frontier.
     Silk Road cross-sphere bleeding when trade reaches overlap.
     Other-awareness accumulates from artifact/signal evidence.

  2. BELIEF UPDATE
     Every actor (not just hegemons) updates beliefs about:
     — known actors (capability, posture, intent)
     — unknown threat level (unexplored frontier fraction)
     — Other-awareness (garbled evidence of the opposing hegemon)

  3. POSTURE SELECTION
     Every contacted arch selects a behavioral posture based on
     capability × threat assessment. IR theory lookup:
     explore / fortify / hide / align / hedge / free-ride.

  4. BUDGET ALLOCATION (Solow-Romer)
     Each hegemon computes expeditionary capacity from production
     function. E = A(t) × K(t)^α × L(t)^β.
     Regional powers compute smaller budgets for local exploration.

  5. EDGE SELECTION (Thompson Sampling)
     Each hegemon draws from Beta priors for frontier edges.
     Priors informed by: rumors, actor posture, denial value,
     Other-awareness direction. Top E edges funded.

  6. EXPEDITION RESOLUTION
     Funded edges attempted. Success/failure per era.
     Success → full information reveal. Failure → mild prior update.

  7. STATUS EVALUATION
     Newly contacted archs: hegemon motivation / control cost decision.
     Existing archs: re-evaluate for status transitions.
     Position in sovereignty-trade space updated continuously.

  8. POPULATION + TECH + TRADE UPDATE
     Growth, extraction, absorption, tech transfer, ceiling enforcement.
     Trade network recomputed. Posture consequences applied.
```

---

## 2. RUMOR PROPAGATION

### Information Quality by Distance from Frontier

| Hops | Label | What hegemon knows |
|------|-------|-------------------|
| 0 | **Known** | Full: pop, tech, resources, harbors, posture, military capacity |
| 1 | **Rumored** | Partial: size ±50%, resources unknown, position from soundings |
| 2 | **Mythologized** | Garbled: "traders say a great civilization to the south" |
| 3+ | **Terra incognita** | Nothing. Here be dragons. |

### Garble Function

```
garbled(trueValue, hops) = trueValue × (1 + noise(seed, tick, arch) × hops)
noise ~ Uniform(-0.5, +0.5), seeded deterministically
```

### Rumor Packet

```
{
  sourceArch, targetArch,
  estimatedSize: garbled,
  estimatedResources: garbled,
  estimatedPosition: exact,      // plateau edges known from soundings
  confidence: 1 / hops,
  age: 0                         // increments per tick; old rumors decay
}
```

### Silk Road Cross-Sphere Bleeding

When both powers' trade reaches overlap on an intermediary arch,
rumors from one sphere bleed into the other. These are maximally
garbled (2+ hops), unreliable, but persistent. They accumulate
as the "unknown provenance" artifact file:

```
if tradeReach(reach).includes(arch) && tradeReach(lattice).includes(arch):
    arch.silkRoadNode = true
    reach.otherAwareness += 0.02 × (1 / distFromReachFrontier)
    lattice.otherAwareness += 0.02 × (1 / distFromLatticeFrontier)
```

### Other-Awareness Propagation (Gradual)

Not a binary switch. A rising tide of evidence:

| otherAwareness | Evidence level | Hegemon response |
|---|---|---|
| 0.0–0.1 | No evidence | No response |
| 0.1–0.3 | Trade goods with unfamiliar writing | Admiralty opens a file |
| 0.3–0.5 | Consistent rumors from multiple sources | File gets a name |
| 0.5–0.7 | Specific descriptions (examinations, ships, cities) | File gets a budget |
| 0.7–0.9 | Fishing fleet encounters unknown vessels | Intelligence priority |
| 0.9–1.0 | Surveillance flight detects radio traffic | Dark Forest breaks |

---

## 3. DISTRIBUTED DARK FOREST — BELIEF MODEL

### Every Actor Maintains Beliefs

Not just hegemons — every contacted arch models its strategic
environment. The sophistication of the model scales with capability.

```
arch.beliefs = {
  knownActors: [
    {id, estimatedPower, distance, posture, lastUpdated, reliability}
  ],

  unknownThreat: 0-1,
    // = unexplored edges adjacent to this arch / total edges
    // frontier archs: high. Interior archs: low.

  otherAwareness: 0-1,
    // garbled awareness of the opposing hegemon (see §2)

  threatDirection: [edgeWeights],
    // per-edge threat estimate. Higher toward unexplored/rumored threats.
    // The Lattice's garrison wall extends in the direction of
    // highest threatDirection values.
}
```

### Belief Update Rules (Per Tick)

```
// Known actors: decay reliability, update from trade contacts
for each known actor:
    actor.reliability *= 0.98         // stale intelligence decays
    if trade route exists this tick:
        actor.reliability = 1.0       // refreshed
        actor.estimatedPower = observe(actor)

// Unknown threat: recompute from frontier topology
unknownThreat = unexploredAdjacentEdges / totalEdges
    + otherAwareness × 0.3            // suspicion inflates threat

// Other-awareness: accumulate from Silk Road bleeding + signals
otherAwareness += silkRoadIncrement   // from §2
if nuclearEra && arch.hasSIGINT:
    otherAwareness += 0.1 per tick    // radio intercepts
```

---

## 4. POSTURE SELECTION (IR Theory)

### The Lookup

Each tick, every contacted arch selects a posture from capability
× perceived threat. The posture determines how the arch allocates
its resources and how it interacts with the hegemon.

```
                    unknownThreat / otherAwareness →
                    LOW                     HIGH
                ┌───────────────────┬───────────────────┐
  capability    │ FREE-RIDE         │ ALIGN             │
  LOW           │ buck-pass, hope   │ bandwagon with     │
                │ someone else      │ strongest visible  │
                │ handles it        │ actor              │
                ├───────────────────┼───────────────────┤
  capability    │ HEDGE             │ FORTIFY            │
  MEDIUM        │ multiple partners │ defensive realism  │
                │ play both sides   │ garrison wall      │
                │ Singapore         │ build defenses     │
                ├───────────────────┼───────────────────┤
  capability    │ PROJECT           │ EXPLORE            │
  HIGH          │ liberal hegemony  │ offensive realism  │
                │ expand trade,     │ reduce uncertainty │
                │ open markets      │ through information│
                │                   │ dominance          │
                └───────────────────┴───────────────────┘
```

### Capability Computation

```
capability = f(population, techLevel, resourceBase, cohesion)

// Normalized 0-1 relative to the strongest known actor.
// A large sophisticated arch with tech 7 adjacent to tech 10
// hegemon has capability ~0.5-0.6. A small atoll: ~0.05.
```

### Posture Consequences (Applied in Stage 8)

| Posture | sovereignty Δ | tradeIntegration Δ | Budget contribution | Signal |
|---------|--------------|-------------------|--------------------|----|
| EXPLORE | +0.02 | +0.01 | Contributes to hegemon E | High (visible) |
| PROJECT | +0.01 | +0.03 | Own local budget | High |
| FORTIFY | +0.03 | −0.02 | Diverts to defense | Medium |
| HEDGE | +0.01 | +0.02 | Split across patrons | Medium |
| ALIGN | −0.02 | +0.03 | Contributes to patron | Low (sheltered) |
| FREE-RIDE | 0 | +0.01 | None | Low |
| HIDE | +0.01 | −0.03 | None | Minimal (hard to find) |

### The Tokugawa Mechanic as Posture Transition

A contacted arch with rising capability and rising threat may
transition from ALIGN → FORTIFY → HIDE. The HIDE posture is
the Tokugawa closure: rejection of foreign contact, harbor sealing,
independent development. The arch's sovereignty snaps to ~0.95,
tradeIntegration drops to ~0.05. It develops on its own curve
until forced open (industrial/nuclear era capability asymmetry
makes closure unsustainable).

Trigger conditions:
```
if sovereignty > 0.5
    && techLevel > 4.0
    && neighborColonizedRecently
    && posture === "FORTIFY"
    && rng(seed, tick) < 0.15:
        → transition to HIDE (Tokugawa closure)
```

---

## 5. BUDGET ALLOCATION (Solow-Romer)

### Production Function

```
E(t) = A(t) × K(t)^α × L(t)^β

E = expeditions per tick (fractional: 2.3 → 2 certain + 30% chance of 3rd)
A = total factor productivity (navigation tech, cartographic method)
K = geographic capital (accumulated knowledge: contacted archs, chart quality)
L = available resources (crews, ships, colonial revenue)
```

### Endogenous Growth (Romer)

A isn't exogenous — it grows with K:

```
A(t) = A₀ × (1 + K(t) × δ)
δ = knowledge spillover rate
```

Every contacted arch improves the technique. Columbus was nearly
impossible; the tenth Caribbean voyage was routine. Not the ocean
changing — A increasing.

### Parameters by Power

| Parameter | The Reach | The Lattice | Meaning |
|-----------|-----------|-------------|---------|
| A₀ | 1.2 | 0.8 | Base productivity (competitive vs conservative) |
| α | 0.4 | 0.3 | Knowledge elasticity (pearl-string vs garrison-wall) |
| β | 0.5 | 0.6 | Resource elasticity (extraction-driven vs agriculture-driven) |
| δ | 0.08 | 0.04 | Knowledge spillover (merchant charts vs bureaucratic archives) |

### Resource Input L — The Imperial Feedback Loop

```
L_reach(t) = baseCrew
    + Σ(extraction[colonies] × 0.3)      // colonial revenue → more ships
    + Σ(trade[clients] × 0.1)            // trade revenue
    + Σ(align_posture_archs × 0.05)      // aligned archs contribute crews
    − militaryDrain                        // defending existing territory
    − overstretchPenalty(if colonies > threshold)

L_lattice(t) = baseCrew
    + internalAgSurplus × 0.4            // tidal-flat agriculture (large, stable)
    + Σ(tribute[tributaries] × 0.2)      // tributary contributions
    + Σ(garrison_surplus × 0.1)           // integrated garrisons
    − garrisonMaintenance                  // maintaining the wall
```

The Reach's feedback: colonize → extract → fund more expeditions →
colonize more. Accelerates until imperial overstretch.

The Lattice's steady state: agricultural surplus is large but
constant. Doesn't scale with expansion. Budget is stable, not
growing. This is why Zheng He sailed once and stopped.

### What the Budget Produces Over Time

| Era | K (known archs) | A | E (expeditions/tick) | Character |
|-----|-----------------|---|---------------------|-----------|
| Early sail | 2–3 | ~1.4 | 0.5–1.0 | Columbus-grade gambles |
| Late sail | 5–8 | ~1.8 | 1.5–2.5 | Steady flow |
| Industrial | 12–20 | ~2.8 | 4–6 | Accelerating |
| Nuclear | 25–35 | ~4.0 | 8–12 | Systematic survey |

The Σ2^n curve should emerge from the production function rather
than being imposed by redistribution.

---

## 6. EDGE SELECTION (Thompson Sampling)

### Per-Edge Belief Distribution

```
edge.belief = Beta(α, β)
α = accumulated evidence of value
β = accumulated evidence of worthlessness
```

### Priors (Civilizational Personality)

```
Reach prior:   Beta(2.0, 1.0) — optimistic
    "There's always something over the horizon."

Lattice prior: Beta(1.0, 2.0) — skeptical
    "Show me the evidence before I authorize the fleet."
```

### Belief Updates

```
// Rumors (weak signal, frequent)
positive rumor:  α += rumorStrength × (1 / hopsFromSource)
negative rumor:  β += rumorStrength × (1 / hopsFromSource)
no rumor:        α *= 0.99; β *= 0.99   // slow decay toward indifference

// Expedition outcomes (strong signal, rare)
success + valuable:    α += 3.0   // also update neighboring edge beliefs
success + worthless:   β += 2.0
failure (lost at sea): β += 1.0   // doesn't PROVE worthlessness
```

### Actor-Posture Awareness (Dark Forest Feedback into Thompson)

The hegemon's priors are modified by inferred posture of the
target arch (when rumors carry posture signals):

```
if target appears to FORTIFY:
    α_strategic += 2.0    // "it's hiding something"
    β_cost += 3.0          // "it will resist"

if target appears to ALIGN toward us:
    α_strategic += 1.0    // willing partner
    β_cost −= 1.0          // low resistance expected

if target appears to ALIGN toward the OTHER:
    α_strategic += 3.0    // URGENT — denial value
    β_cost += 1.0          // "we must get there first"
    // This is the Scramble for Africa dynamic
```

### Denial Value (Other-Awareness → Thompson Inflation)

When otherAwareness > 0.3, edges in the direction of the Other
get an α bonus proportional to otherAwareness:

```
for each frontier edge pointing toward estimated Other direction:
    α_denial += otherAwareness × 2.0
```

The Reach doesn't know the Lattice exists but its Thompson priors
for southward edges keep inflating because the Silk Road rumors
come from that direction. The wavefront is pulled toward the Other
by accumulated garbled evidence.

### Selection Algorithm

```
each tick:
  1. For every frontier edge, sample from Beta(α, β)
  2. Add denial value bonus to sample
  3. Rank by sampled value
  4. Fund top floor(E) edges
  5. Fractional remainder → probability for one more
```

### The El Dorado Emerges Naturally

Garbled positive rumors inflate α for a particular edge across
many ticks. Hegemon funds expensive expedition. Arrives to find
a moderately useful archipelago. Not the city of gold. α gets
a weak update. β unchanged. The myth persists in rumor chains
even as the admiralty quietly writes down the asset.

### Age of Exploration → Modernity Transition

When E > |frontierEdges|, every edge gets funded. The age of
exploration ends not from lost interest but because the production
function makes comprehensive survey cheaper than selective gambling.
The transition from gamble to survey is continuous.

---

## 7. HEGEMON MOTIVATION & CONTROL COST

### The Contact Decision (Full Information, Post-Expedition)

When an expedition reveals an arch, the hegemon evaluates with
true values:

```
motivation = betweenness × 0.3
           + resourceValue × 0.25
           + frontierExtension × 0.2
           + denialValue × 0.25     // if Other-awareness > 0.3

controlCost = population × techLevel × supplyChainLength
              × (1 + arch.cohesion)  // cohesive cultures resist harder

ratio = motivation / max(0.1, controlCost)
```

### Decision Outcomes

| motivation | controlCost | Result | Earth analogue |
|---|---|---|---|
| HIGH | LOW | Colony / Garrison | Barbados, Marshall Islands |
| HIGH | HIGH | Client / Tributary | Siam, Trucial States |
| LOW | LOW | Bypassed | North Sentinel Island |
| LOW | HIGH | Definitely bypassed | Ethiopia pre-Scramble |
| HIGH position, LOW resource | any | Strategic garrison | Diego Garcia, Singapore |
| LOW position, HIGH resource | LOW cost | Extraction colony | Congo, Bolivia |
| any | any + HIGH cohesion + HIGH tech | Sovereign trader | Mughal India, Ottoman |

### Dynamic Re-evaluation (Per Tick)

Status is NOT permanent. Each tick, motivation and controlCost
are recomputed. Status transitions when ratio crosses thresholds:

| From | To | Trigger |
|------|-----|---------|
| Colony | Post-colony | Nuclear era + cost > revenue |
| Colony | Client | Hegemon weakens / overstretch |
| Client | Colony | Resources discovered / hegemon strengthens |
| Bypassed | Garrison | Frontier shifts / denial value spikes |
| Tributary | Garrison | Lattice wall expands outward |
| Tributary | Sovereign | Tributary grows strong / Lattice weakens |
| Any | Closed | Tokugawa mechanic (see §4) |
| Closed | Reopened | Industrial/nuclear tech asymmetry |
| Any | Contested | Second hegemon's wavefront arrives |
| Contacted | Independent power | Tech > 6 + pop > threshold + size > threshold |

### Independent Power Emergence (§0 Compliance)

Per §0, any arch meeting the geographic conditions for independent
sophistication should develop accordingly. Each tick, uncolonized
archs with sufficient size, potential, and tech are evaluated:

```
if sovereignty > 0.7
    && techLevel > 6.0
    && geo.size > 0.6
    && population > popThreshold:
        → arch becomes INDEPENDENT POWER
        → runs own (small) exploration budget
        → maintains own Thompson priors for frontier edges
        → can become patron to smaller neighbors (local hegemon)
```

These are the third, fourth, fifth voices. They don't need to be
nuclear-capable to matter — a tech-7 regional power with a navy
and a philosophical tradition is a civilization, not a subject.
The world at Story Present should have 3-5 of these alongside
the two nuclear hegemons.

---

## 8. POLITICAL-ECONOMY SPACE (Continuous)

### Named Statuses as Regions, Not Categories

The sovereignty-trade space is continuous. An arch drifts through
it each tick. Labels are derived from position, never assigned
directly.

```
                Trade Integration →
        0.0          0.5          1.0
    ┌────────────┬────────────┬────────────┐
1.0 │ CLOSED     │ SOVEREIGN  │ SILK ROAD  │
    │ Tokugawa   │ Mughal     │ NODE       │
S   │            │ Ottoman    │ Malacca    │
o   ├────────────┼────────────┼────────────┤
v   │ BYPASSED   │ BUFFER     │ CLIENT     │
.   │ Sentinel   │ Siam       │ Trucial    │
    │            │ Nepal      │ States     │
0.5 ├────────────┼────────────┼────────────┤
    │ NEGLECTED  │ TRIBUTARY  │ COLONY     │
    │ forgotten  │ Korea      │ Barbados   │
    │ outpost    │ Vietnam    │ Congo      │
0.0 └────────────┴────────────┴────────────┘
```

### Sovereignty = f(inputs)

```
sovereignty =
    + cohesion × 0.25              // unified cultures resist
    + (1 − techDelta) × 0.25      // tech parity enables independence
    + geo.size × 0.20             // bigger is harder to hold
    + ambition × 0.15             // the will to resist
    + hopCount × 0.05             // distance helps
    − hegemon.controlCapacity × 0.10
```

### Trade Integration = f(inputs)

```
tradeIntegration =
    + openness × 0.25             // receptive cultures trade more
    + geo.betweenness × 0.20      // chokepoints have more trade
    + geo.resourceValue × 0.20    // valuable resources attract trade
    + era.techFactor × 0.15       // better ships = more trade
    + (1 − sovereignty) × 0.10    // colonies are forcibly integrated
    + log2(networkSize) × 0.10    // Metcalfe's law
```

### Extraction (Derived, Not an Axis)

```
extraction = tradeIntegration × (1 − sovereignty) × hegemon.extractionPolicy
```

### Trajectory Display (Popup)

The popup shows a sparkline through the sovereignty-trade space:
one point per tick where the position changed. The shape of the
trajectory IS the story.

```
arch.history = [
  {tick, sovereignty, tradeIntegration, techLevel, status, posture, event},
  ...
]
```

---

## 9. CIVILIZATIONAL PERSONALITY (Two Layers)

### Layer A — Deep Substrate (Primordialist)

Seeded once at world generation from geography. Stable across
the full simulation. Represents 100,000 years of independent
development. Changes on geological timescales, not political ones.

```
arch.substrate = {
  agriculturalBase,         // → §10a
  metaphorSystem,           // → §10e
  socialOrganization,       // → §10c
  genderEconomy,            // → §10d
  religiousMode,            // → §10f
}
```

These resist political change. Colonization doesn't change your
agricultural base. A century of Reach occupation doesn't erase a
tidal metaphor system that's been developing for 50,000 years.

### Layer B — Political Identity (Modernist)

Doesn't exist before contact. Emerges IN RESPONSE TO the hegemon's
presence. Updates per tick after contact.

```
arch.identity = {
  openness: 0-1,        // receptivity to external contact
  cohesion: 0-1,        // internal unity under pressure
  ambition: 0-1,        // outward projection desire
}
```

### Identity Initialization (At Contact Tick)

```
identity.cohesion = substrate.socialOrganization × 0.5
identity.openness = 0.5 + (substrate.genderEconomy − 0.5) × 0.3
identity.ambition = geo.size × 0.4 + substrate.socialOrganization × 0.3
```

### Identity Drift (Per Tick After Contact)

```
if neighbor colonized this tick:
    cohesion += 0.05          // "we must unify"
    openness −= 0.03          // "they can't be trusted"

if extraction rate > 0.2:
    ambition += 0.02          // "this is unacceptable"

if trade integration rising:
    openness += 0.01          // exposure normalizes contact

if tech delta narrowing:
    ambition += 0.01          // "we can compete"
    cohesion += 0.01          // institutional confidence

if posture = HIDE for > 5 ticks:
    openness −= 0.02          // isolation reinforces insularity
    cohesion += 0.01           // internal consolidation
```

### Personality Archetypes (Emergent, Not Assigned)

| Openness | Cohesion | Ambition | Archetype | Example |
|----------|----------|----------|-----------|---------|
| HIGH | LOW | LOW | Absorbed | Philippines |
| LOW | HIGH | LOW | Closed | Tokugawa Japan |
| HIGH | HIGH | HIGH | Selective adopter | Meiji Japan |
| HIGH | LOW | HIGH | Contested | post-colonial fragile state |
| LOW | HIGH | HIGH | Resistant power | Ottoman Empire, Ethiopia |
| LOW | LOW | LOW | Bypassed | North Sentinel Island |
| HIGH | MED | MED | Bridge culture | Malacca, Singapore |
| MED | HIGH | LOW | Stable tributary | Vietnam under Lattice |

---

## 10. SUBSTRATE FROM GEOGRAPHY

### 10a. STAPLE CROPS

Six staple crops, each derived from an Earth cultivar (Narrator 4's
shortcuts — suspiciously shallow phylogenetic roots, another seam).
Each crop is defined by growing conditions derived from the climate
model (§7 of the Earth Sciences) and determines caloric yield,
labor organization, population ceiling, and political culture.

**Paddi** — from Malay *padi* (unhusked rice). The tidal grain.

```
paddi.canGrow(arch) =
    meanTemp >= 20°C
    && effectiveRainfall >= 1200mm
    && tidalRange >= 2.0m
    && shelfR >= 0.08
    && |latitude| <= 28

paddi.yield = 5.0 × tempBonus × waterBonus × tidalBonus × shelfBonus
// Max ~6.5 t/ha in the Lattice core. Min viable ~2.0 t/ha.
```

Calories: ★★★★★ · Labor: collective-hydraulic · Storage: good ·
Trade value: moderate (bulky). The crop that creates the bureaucracy.
The dike system requires central coordination; neglect = famine.
The Lattice exists because paddi exists.

**Emmer** — from ancient wheat *Triticum dicoccum*. The storm grain.

```
emmer.canGrow(arch) =
    meanTemp >= 8°C && meanTemp <= 24°C
    && effectiveRainfall >= 400mm && effectiveRainfall <= 2000mm
    && |latitude| >= 20 && |latitude| <= 55

emmer.yield = 2.5 × tempBonus × rainBonus × drainageBonus
// Wide shelf PENALIZES emmer (waterlogged). Inverse of paddi.
// Max ~3.2 t/ha. Min viable ~1.2 t/ha.
```

Calories: ★★★ · Labor: competitive-individual · Storage: excellent ·
Trade value: high (compact, provisions voyages). One family, one
terrace. The market sets prices. You demand a say in how the state
runs because nobody coordinates your planting.

**Taro** — from *Colocasia esculenta*. Essentially unchanged from
the Earth cultivar. Narrator 4 barely touched it.

```
taro.canGrow(arch) =
    meanTemp >= 21°C
    && seasonalRange <= 4°C
    && effectiveRainfall >= 1500mm
    && |latitude| <= 20

taro.yield = 3.0 × tempBonus × rainBonus
// Max ~3.8 t/ha. Min viable ~1.5 t/ha.
```

Calories: ★★★ · Labor: chieftain-kinship · Storage: poor (rots
in weeks — must be processed into paste or flour). Can't provision
a naval expedition. Constrains strategic horizon to canoe-voyage
range. Civilizations are sophisticated but not urban.

**Nori** — from *Pyropia/Porphyra* spp. Cultivated on submarine
plateau edges by free-diving crews.

```
nori.canGrow(arch) =
    meanTemp >= 5°C && meanTemp <= 22°C
    && plateauEdgeCount >= 1
    && upwelling >= 0.2

nori.yield = 1.5 × nutrientBonus × shelfBonus × proteinMultiplier(2.0)
// Low raw calories but high protein, iodine, iron, B12.
// Max ~4.5 t/ha-equiv. Min viable ~1.0.
```

Calories: ★★(+protein) · Labor: federated-maritime · Storage:
excellent (dried sheets last years). NOT a sole staple — always
a supplement. But nori + any grain = complete diet. Dried nori
sheets are the universal trade good of Aeolia: lightweight,
nutritious, imperishable, demanded everywhere. Nori archs have
permanent trade advantage — the spice islands of Aeolia.

**Sago** — from *Metroxylon sagu*. The leisure crop. Possibly
enhanced starch content (another seam — suspiciously high yield
for a "wild" palm).

```
sago.canGrow(arch) =
    meanTemp >= 24°C
    && effectiveRainfall >= 2000mm
    && |latitude| <= 15
    && shelfR >= 0.04

sago.yield = 4.0 × rainBonus × areaLimit
// But labor cost is 1/5 of grain crops.
// Max ~5.0 t/ha. Min viable ~2.0.
```

Calories: ★★★★ · Labor: loose-communal · Storage: good ·
Minimal cultivation — palms grow wild in suitable habitat.
One palm yields 200–800 kg of starch. Surplus time invested in
navigation, art, canoe-building. Polynesian pattern: materially
modest, culturally rich.

**Papa** — from Quechua *papa* (potato). Adapted to subpolar
volcanic slopes. 60–80 day compressed growing season.

```
papa.canGrow(arch) =
    meanTemp >= 2°C && meanTemp <= 18°C
    && effectiveRainfall >= 400mm
    && |latitude| >= 35

papa.yield = 3.5 × tempBonus × rainBonus × frostPenalty
// Max ~4.0 t/ha at 35-45° latitude. Min viable ~1.5 subpolar.
```

Calories: ★★★½ · Labor: kinship-cooperative · Storage: excellent
(volcanic caves at constant 4–6°C). Famine insurance: when emmer
fails, papa survives. Every civilization that acquires papa through
the Columbian Exchange becomes more resilient.

**Columbian Exchange dynamics between crop zones:**

```
diseaseShock = baseSeverity × cropDistance(contactor, contacted)

cropDistance =
    0.2 if same crop type (similar pathogen pools)
    0.5 if adjacent climate zones
    0.8 if distant climate zones
    1.0 if maximally different (paddi meets papa)
```

**Crop matrix summary:**

```
CROP    TEMP     RAIN      LAT     SHELF  TIDAL  PLATEAU  CAL   LABOR    STORE
paddi   20-35°C  1200+mm   0-28°   ≥0.08  ≥2.0m  —        ★★★★★ Heavy    Good
emmer   8-24°C   400-2000  20-55°  <0.10  —      —        ★★★   Medium   Excellent
taro    21+°C    1500+mm   0-20°   —      —      —        ★★★   Low      Poor
nori    5-22°C   —         —       —      —      ≥1 edge  ★★+   Medium   Excellent
sago    24+°C    2000+mm   0-15°   ≥0.04  —      —        ★★★★  Minimal  Good
papa    2-18°C   400+mm    35-65°  —      —      —        ★★★½  Medium   Excellent
```

### 10b. TRADE GOODS — Secondary Products

Not individually simulated crops. Three categories of trade goods
that emerge from the staple zones and drive long-distance trade.
Named for the sound of three trade pidgins and a navigator's log.

**Stimulants** — the single most important driver of long-distance
trade. Stimulant demand funded more naval expeditions than gold.

| Zone | Name | Derivation | Earth analogue |
|------|------|-----------|---------------|
| Paddi | **Char** | Mandarin *chá* (茶) via Portuguese | Tea. Refined, ceremonial. The Reach's daily ritual. |
| Emmer | **Qahwa** | Arabic *qahwa* (قهوة), pre-European | Coffee. Functional. The navigator's fuel. |
| Taro | **Awa** | Hawaiian *ʻawa* (kava) | Kava. Sedative, social. The chief's ceremonial drink. |
| Sago | **Pinang** | Malay *pinang* (areca nut) | Betel. Mild, ubiquitous. Chewed while sailing. |
| Papa | **Aqua** | Latin *aqua vitae* → Scandinavian *aquavit* | Distilled tuber spirit. Warming. The subpolar necessity. |
| Nori | — | None produced | Imports all stimulants → natural trade intermediary. |

**Fibers** — what your clothes are made of determines material
culture, trade relationships, and visual identity.

| Zone | Name | Derivation | Character |
|------|------|-----------|-----------|
| Paddi | **Seric** | Latin *sericum* from Greek *Sēres* (the Silk People) | Fine, lustrous. The prestige textile. The Romans never knew where it came from. |
| Emmer | **Fell** | Old Norse *fell* (skin, hide, fleece) | One syllable, blunt. Sailor's cloth. Keeps the spray out. From the goat-equivalent. |
| Taro/Sago | **Tapa** | Polynesian *tapa* (bark cloth) | Beaten, not woven. Painted, ceremonial. Sounds like what it is. |
| Nori | **Byssus** | Greek *byssos* (fine fiber from the sea) | Woven from processed kelp stipe. Waterproof. The diver's weave. Unique to Aeolia. |
| Papa | **Qivu** | Inuktitut *qiviut* (musk ox underwool) | Soft sound for a soft fiber. Warmest thing on the planet. Worth more per weight than seric. |

**Proteins** — domesticated animals as supplements to the
universal marine protein base.

| Zone | Name | Derivation | Role |
|------|------|-----------|------|
| Paddi | **Kerbau** | Malay *kerbau* (water buffalo) | Draft animal for dike work. You don't eat kerbau — you mourn it when it dies. |
| Emmer | **Kri** | Old Norse *kið* → Faroese *kri* (young goat) | Milk, cheese, leather, meat. Climbs volcanic scree. Eats anything. The Reach's companion. |
| Taro/Sago | **Moa** | Polynesian *moa* (common fowl) | Eggs, feathers, meat. Low-maintenance. Sunday dinner. |
| Papa | — | No domesticate. | Pure fisheries + tuber. The harshest diet. |
| All zones | **Reef stock** | — | Managed fish in enclosed lagoons. Too ordinary to name. |

**Trade good simulation per arch:**

```
arch.tradeGoods = {
  stimulant: {
    type: "char"|"qahwa"|"awa"|"pinang"|"aqua"|null,
    production: 0-1,     // climate-dependent
    tradeValue: 0-1      // demand elsewhere
  },
  fiber: {
    type: "seric"|"fell"|"tapa"|"byssus"|"qivu"|null,
    production: 0-1,
    tradeValue: 0-1
  },
  protein: {
    type: "kerbau"|"kri"|"moa"|null,
    production: 0-1,
    tradeValue: 0-1
  },

  // Deficits drive trade motivation (→ Thompson Sampling α inflation)
  stimulantDeficit: bool,  // needs stimulant, doesn't grow one
  fiberDeficit: bool,      // needs fiber, doesn't produce enough
  proteinDeficit: bool     // low fisheries + no domesticate

  totalTradeValue: Σ(production × tradeValue) + noriExport
}
```

**Cargo manifest flavor text (from trade vocabulary):**

Reach merchant: *"Forty bales of fell, twelve casks of qahwa,
six bolts of seric (second-quality), nori in standard sheets,
three hundred weight."*

Lattice tribute fleet: *"Char: four hundred catties, spring leaf.
Seric: sixty bolts, imperial grade. Kerbau: twelve head, breeding
stock. Paddi: surplus grain, hull-dried, six hundred measures."*

### 10c. POLITICAL CULTURE (Almond & Verba)

The crop determines which political culture type develops because
the crop determines whether you need to be aware of the central
political system.

**Parochial** — awareness < 0.3. You identify with your village,
your kinship group, your island. The central state is distant and
irrelevant. Political knowledge is local.

**Subject** — awareness > 0.6, participation < 0.3. You are aware
of the central state and comply with it. You pay taxes, follow the
dike schedule, present for examination. But you don't participate
in policy formation. The system runs; you are run by it.

**Civic** — awareness > 0.6, participation > 0.6. You believe you
can influence the political process. You argue in the assembly,
petition the court, publish in the free press.

**Initialization from crop:**

```
arch.politicalCulture = { awareness, participation }

paddi  → { 0.70, 0.15 }   // Subject: knows the system, doesn't question it
emmer  → { 0.70, 0.70 }   // Civic: knows the system, fights over it
taro   → { 0.15, 0.10 }   // Parochial: local world only
nori   → { 0.30, 0.55 }   // Parochial-civic hybrid: crew-level democracy
sago   → { 0.15, 0.20 }   // Parochial: prestige politics, not institutional
papa   → { 0.25, 0.15 }   // Parochial-subject: kin-group cooperation
```

**Drift per tick after contact:**

```
if colonized:            awareness += 0.05, participation −= 0.02
if garrisoned:           awareness += 0.03, participation −= 0.01
if traded (no colony):   awareness += 0.02, participation += 0.01
if independence gained:  participation += 0.04
if extraction > 0.3:    participation += 0.02  // grievance drives engagement
```

**Contact character predicted by political culture:**

Parochial colonized by Civic → doesn't rebel, doesn't understand
what rebellion means. Resists through non-compliance, withdrawal,
weapons of the weak.

Subject colonized by Civic → produces collaborators. Subject
skills (procedural compliance) transfer to the new system.

Civic colonized by anyone → organized resistance, pamphleteers,
and eventually revolution.

### 10d. MODE OF PRODUCTION (Marxian, Continuous)

The crop determines the mode. The mode determines who benefits
from hegemon contact and who loses. Mapped onto two continuous
axes rather than discrete Marxian categories, consistent with
all other simulation spaces.

**Axis 1 — Surplus Centralization (0–1):** Who captures surplus?

```
0.0 = nobody (communal — no surplus exists)
0.2 = household (kin-group retains)
0.4 = distributed (crews keep shares)
0.6 = personal (chief redistributes)
0.8 = contested (bourgeoisie vs aristocracy)
0.9 = state (bureaucratic taxation)
```

**Axis 2 — Labor Commodification (0–1):** How is labor organized?

```
0.0 = kin obligation (work because you're family)
0.2 = communal obligation (work because the chief says)
0.4 = corvée/tribute (work because the state says, unpaid)
0.6 = guild/cooperative (work for shared proceeds)
0.8 = wage labor (work for money)
1.0 = fully commodified (labor is a market price)
```

**The constraint:** Labor commodification cannot exceed surplus
centralization + 0.3. You need someone accumulating before wage
labor makes sense. Market requires a buyer.

```
laborCommodification <= surplusCentralization + 0.3
// violation → snap back (market collapses without accumulator)
```

**The full space, with historical examples:**

```
            Labor Commodification →
      0.0           0.3           0.6           1.0
  ┌─────────────┬─────────────┬─────────────┬─────────────┐
  │ ASIATIC     │ TRIBUTARY   │ STATE       │ PLANTATION  │
  │             │ EMPIRE      │ CAPITAL     │ COLONY      │
1 │ Song China  │ Aztec Empire│ Qing salt   │ Barbados    │
  │ Mughal India│ Mongol khan.│  monopoly   │ Dutch Java  │
  │ Pharaonic   │ Inca mit'a │ Tokugawa    │ Belgian     │
  │  Egypt      │             │  Japan      │  Congo      │
S │ Angkor Wat  │ Benin Empire│ Meiji Japan │ Saint-      │
u │             │             │ Modern PRC  │  Domingue   │
r ├─────────────┼─────────────┼─────────────┼─────────────┤
p │ THEOCRATIC  │ TRIBUTARY   │ PETTY       │ MERCANTILE  │
l │ CHIEFTAINCY │             │ COMMODITY   │             │
u │             │ Tonga       │             │ Dutch       │
s │ Hawai'i     │ Asante      │ Hanseatic   │  Republic   │
  │  (kapu)     │  kingdom    │  League     │ Genoa/Venice│
C │ Ancient     │ Buganda     │ Amalfi      │ British     │
e │  Sumer      │ Chola       │  coast      │  Empire     │
n │ Göbekli     │  dynasty    │ Free divers │ Edo-period  │
t │  Tepe?      │             │  of Ama     │  Osaka      │
r ├─────────────┼─────────────┼─────────────┼─────────────┤
a │ HOUSEHOLD   │ FRONTIER    │ PROLETARIAN │ ANARCHO-    │
l │             │ ECONOMY     │ SUBSISTENCE │ MERCANTILE  │
. │ Norse       │             │             │             │
  │  farmstead  │ Vinland     │ Post-       │ Tortuga     │
  │ Ainu        │ Jamestown   │  colonial   │ Nassau      │
  │  kotan      │  (early)    │  Lagos      │ Cossack     │
  │ Highland    │ Plymouth    │ Informal    │  Host       │
  │  clans      │  (early)    │  Cairo      │ Libertatia  │
0 │ Faroe       │ Botany Bay  │ Modern gig  │  (legend)   │
  │  Islands    │  (early)    │  economy    │ Zomia       │
  ├─────────────┼─────────────┤─────────────┴─────────────┤
  │             │ COMMUNAL    │                           │
  │             │             │       FORBIDDEN           │
  │             │ !Kung San   │                           │
  │             │ Pirahã      │  Can't commodify labor    │
  │             │ Hadza       │  without someone          │
  │             │ Pre-contact │  accumulating surplus.     │
  │             │  Polynesia  │  Market requires a buyer.  │
  │             │ Sentinelese │                           │
  └─────────────┴─────────────┴───────────────────────────┘
```

**Notes on less obvious placements:**

Tokugawa Japan as State Capital, not Asiatic — centralized
surplus extraction AND rice-futures market in Osaka (arguably
world's first commodity exchange). High centralization AND high
commodification. The state ran the market rather than replacing it.

Modern PRC as State Capital — the gaokao allocates labor, the
state captures surplus, but labor IS commodified. Marx would
not have predicted this stable combination.

Post-colonial Lagos as Proletarian Subsistence — commodified
labor but surplus flows out through unequal trade terms, not
institutional capture. The neocolonial trap.

Libertatia as legendary Anarcho-Mercantile — maximum
commodification (everything has a market price including the
captain's commission) with zero centralization (the crew votes
on everything). Zomia is the land-based equivalent.

**Initialization from crop:**

```
paddi → { surplus: 0.85, labor: 0.25 }  // asiatic
emmer → { surplus: 0.65, labor: 0.70 }  // mercantile
taro  → { surplus: 0.55, labor: 0.15 }  // tributary
nori  → { surplus: 0.35, labor: 0.55 }  // petty commodity
sago  → { surplus: 0.10, labor: 0.05 }  // communal
papa  → { surplus: 0.20, labor: 0.10 }  // household
```

**Colonial drift trajectories (paths through the space):**

```
Reach colonizes taro arch:
  Tributary (0.55, 0.15) → Plantation Colony (0.90, 0.85)
  Path: chief co-opted → corvée imposed → wage labor introduced
        → monoculture export economy
  Duration: ~30 ticks (1,500 years). Passes through Tributary
  Empire and State Capital on the way.

Lattice garrisons papa arch:
  Household (0.20, 0.10) → Asiatic (0.85, 0.25)
  Path: kin-groups taxed → corvée for dike extension →
        examination system arrives → full bureaucratic absorption
  Duration: ~20 ticks (1,000 years). Passes through Theocratic
  Chieftaincy on the way.

Nori arch goes pirate:
  Petty Commodity (0.35, 0.55) → Anarcho-Mercantile (0.15, 0.85)
  Path: crews reject state authority → captured trade goods
        create market economy → pirate republic constituted
  Duration: ~5 ticks (250 years). Fast — decentralization is
  a subtraction, not a construction.

Decolonized plantation arch:
  Plantation Colony (0.90, 0.85) → ??? 
  Path: colonial state withdraws → surplus centralization drops →
        IF institutions rebuilt: drifts to Mercantile (0.65, 0.70)
        IF institutions NOT rebuilt: stalls at Proletarian 
        Subsistence (0.25, 0.70) — the neocolonial trap
  Duration: variable. Fastest recovery from Mercantile-origin
  archs. Slowest from Tributary-origin (chieftaincy destroyed,
  no indigenous institution to rebuild around).
```

**Contradiction as tension vector (per tick):**

Each position in the space has an internal contradiction that
pushes toward instability. Computed as a force:

```
if surplus > 0.7 && labor < 0.3:
    // Asiatic contradiction: state extracts without developing
    // productive forces. Pressure toward commodification or collapse.
    tension = (surplus - 0.5) × 0.01
    // Applied: labor += tension (slow commodification under pressure)

if surplus > 0.5 && labor > 0.5:
    // Capitalist contradiction: bourgeoisie vs proletariat
    rebellionPressure += (surplus × labor) × 0.005

if surplus < 0.3 && labor > 0.6:
    // Neocolonial trap: commodified labor, no surplus capture
    // Pressure toward either re-centralization or anarcho-drift
    tension = labor - surplus
    // Unstable — pushes toward Mercantile (up) or Anarcho (right-down)
```

**Simulation variables:**

```
arch.production = {
  surplusCentralization: 0-1,
  laborCommodification: 0-1,
  
  // Derived from position
  modeLabel: string,          // region label, not assigned
  collaborationEfficiency: f(surplusCentralization),
    // 0.85 at asiatic, 0.05 at communal
  extractionCeiling: f(surplus, labor),
    // 0.40 at asiatic, 0.50 at plantation (but with social collapse)
  recoveryRate: f(labor, arch.identity.cohesion),
    // 0.8 mercantile, 0.2 tributary (chieftaincy destroyed)
  contradictionTension: vector,  // the instability force
}
```

### 10e. NARRATIVE SUBSTRATE (Not Simulated)

The following are derived from geography for narrative use
(scene-writing, dialogue, cultural detail, popup flavor text)
but do not affect computed simulation variables:

```
arch.narrative = {
  genderEconomy: clamp(avgEdgeLength / maxEdgeLength, 0, 1),
    // Longer voyages → more egalitarian.
    // Applied as ±10% tech growth modifier only.
    // techGrowthRate *= 1 + genderEconomy × 0.1

  metaphorSystem: f(stapleCrop),
    // paddi  → TIDAL (cyclical, flow-based, interconnection)
    // emmer  → NAVIGATIONAL (directional, positional, star-fixed)
    // taro   → SEASONAL (agricultural, cyclical, land-rooted)
    // sago   → SEASONAL (leisure-surplus, prestige-narrative)
    // nori   → OCEANIC (depth-based, vertical, pressure-layered)
    // papa   → ENDURANCE (patience, storage, survival through scarcity)

  religiousMode: f(politicalCulture),
    // Subject    → formal-institutional (state-adjacent ceremony)
    // Civic      → devotional + institutional debate
    // Parochial  → animist, local spirit traditions
    // No evangelical equivalent on Aeolia (bible §07).
}
```

These are available in the arch state vector for popup display
and narrative generation but do not enter the tick pipeline.

### 10f. SUBSTRATE INTERACTION MATRIX — Hooks

How different substrates interact at contact. The crop-zone
pairing determines the character of the colonial relationship:

```
colonizer crop × colonized crop → interaction pattern

emmer × paddi    = institutional disruption (Civic disrupts Subject)
emmer × taro     = demographic replacement (surplus provisions settlers)
emmer × sago     = commercial absorption (trade overwhelms gift economy)
emmer × papa     = extraction (resources drained to temperate core)
paddi × emmer    = tributary tension (Subject system meets Civic resistance)
paddi × taro     = bureaucratic integration (dike system extended)
paddi × nori     = trade partnership (complementary goods)
paddi × papa     = benign neglect (too cold, too far, too little return)

diseaseShock modifier by crop distance:
  same crop:        × 0.2 (similar pathogen pools)
  adjacent zone:    × 0.5
  distant zone:     × 0.8
  maximum distance: × 1.0 (paddi meets papa = catastrophe)
```

### 10g. MINERAL RESOURCES

Simplified to four ore types. Seeded from RNG, biased by geology.

```
arch.minerals = {
  Fe: true,              // universal (volcanic basalt = iron source)
  Cu: seeded, ~20%,      // enables Bronze Age
  Au: seeded, ~10%,      // precious metals, correlated with peak height
  Pu: seeded, ~5%,       // fissile material (2 out of 42 archs)
                         // biased toward large archs with tall peaks
                         // (evolved magma = granitic intrusions)
}
```

Fe is universal. Cu is the Bronze Age lottery ticket. Au drives
trade and colonial motivation. Pu determines who goes nuclear.
Per §0, the geographic distribution of Pu is either the rarest
natural coincidence or evidence that Narrator 7 placed it.

---

## 11. OPEN QUESTIONS (Updated)

### Resolved

1. ~~Budget model~~ → Thompson Sampling (edge selection) +
   Solow-Romer (budget sizing). **DECIDED.**

2. ~~Culture theory~~ → Primordialist substrate (deep, geographic,
   stable) + Modernist identity (reactive, contact-triggered,
   per-tick drift). **DECIDED.**

3. ~~Status assignment~~ → Continuous sovereignty-trade space.
   Named statuses are region labels, not assigned categories.
   **DECIDED.**

4. ~~Dark Forest~~ → Distributed belief model. Every actor
   maintains beliefs. Posture selection from IR theory.
   Other-awareness propagates gradually via Silk Road.
   **DECIDED.**

5. ~~Agriculture~~ → Six staple crops (paddi, emmer, taro, nori,
   sago, papa). Growing conditions derived from Earth cultivars.
   Three trade good categories (stimulants, fibers, proteins)
   with Cathay-vector naming. **DECIDED.**

6. ~~Political culture~~ → Almond & Verba (parochial, subject,
   civic). Initialized from crop, drifts per tick. **DECIDED.**

7. ~~Minerals~~ → Four ores (Fe universal, Cu ~20%, Au ~10%,
   Pu ~5%). Seeded from RNG. **DECIDED.**

8. ~~Mode of production~~ → Two continuous axes (surplus
   centralization, labor commodification). Marxian modes as
   regions, not categories. Contradiction as tension vector.
   Forbidden zone enforced. **DECIDED.**

### Open

5. **Tick cost**: 100 ticks × 42 archs × 8 stages. Thompson
   Sampling adds per-edge Beta draws. Profile before optimizing.
   Batch-compute on seed change (not real-time per frame).

6. **Determinism**: All noise seeded from `worldSeed × tick × arch`.
   Thompson draws use seeded RNG, not Math.random().

7. **Popup visualization**: Sparkline through sovereignty-trade
   space with posture markers. Implementation: inline SVG or
   canvas element in the React popup.

8. **Lattice pulse mechanic**: Zheng He = single-tick exploration
   beyond garrison wall at high budget cost. Does NOT claim.
   Reveals information, sets positive Thompson prior, but
   bureaucracy doesn't fund follow-up for decades. The arch
   remembers (otherAwareness set). How often? Once per 10 ticks
   when a "reformist emperor" RNG event fires?

9. **Imperial overstretch**: L_reach goes negative when
   garrisonMaintenance > extraction revenue. Threshold emerges
   from the production function. When it hits, the Reach stops
   expanding and starts losing colonies. Let it emerge or set
   a hard cap?

10. **Multi-polar late game (§0 compliance)**: Per §0, the
    simulation must produce 3-5 independent powers. These should
    emerge naturally from geographic conditions, not be assigned.
    They run their own exploration budgets, maintain their own
    Thompson priors, and can patron smaller neighbors. The nuclear
    era should feel genuinely multipolar, not bipolar-with-extras.
    Implementation: any arch exceeding thresholds in §7 gets
    promoted to active explorer. Cap at 5-6 to keep tractable.

11. **Substrate seeding**: §10 requires climate model. Simple
    latitude bands (3 zones) or full Hadley cell simulation
    (6 zones with windward/leeward)? The bible specifies
    recognizable trade winds and westerlies — suggests 6-zone.

12. **Substrate interaction matrix**: §10g needs empirical
    calibration. How much does the colonizer's substrate type
    affect extraction rate? This is where the real political
    science lives. Defer to next pass with literature review.

---

*Aeolia Simulation Engine — Design Spec v0.4*
*Thompson-Solow budget · Dark Forest beliefs · IR posture selection*
*Continuous political-economy space · Primordialist-modernist culture*
*Six staple crops · Cathay-vector trade nomenclature · Almond-Verba political culture*
*Marxian mode of production as continuous 2D space with contradiction tensors*
*Gender economy, metaphor system, religious mode as narrative-only derivations.*
