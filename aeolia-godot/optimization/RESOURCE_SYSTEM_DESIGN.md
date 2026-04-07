# Resource System Redesign: C (Naphtha) + Pu Logic

## Naming

The substrate resource symbols are: **Fe, Cu, Au, Pu, C**

| Symbol | Aeolian name | Earth analog | Naming origin |
|--------|-------------|--------------|---------------|
| Fe | **sider** | iron | Greek *sideros* (σίδηρος). Ubiquitous in volcanic basalt — every archipelago has it. Civilizations don't discover sider, they've always known it. The progression is technological: cold-hammered meteoritic iron → smelted bog iron → bloomery steel. |
| Cu | **aes** | copper | Latin *aes* (copper/bronze, root of "aeneous"). The first strategic mineral — only ~20% of archipelagos have native copper (malachite veins in volcanic rock). Discovery: someone hammers a green rock and it deforms instead of shattering. |
| Au | **chrysos** | gold | Greek *chrysos* (root of "chrysanthemum"). Appears in volcanic hydrothermal veins, concentrated by peak height. Discovery is immediate (alluvial gold in streams). Doesn't make you powerful, makes you *visible* — draws navigators, creates first contact points. |
| Pu | **pyra** | plutonium | Greek *pyr* (fire — root of "pyre," "pyrite," "pyroclastic"). Encountered as anomalously warm rocks in deep volcanic deposits. Mildly dangerous, occasionally sickens miners. A curiosity for most of history — shamans note its perpetual warmth. Energy potential unlocked only with industrial-era physics. |
| C | **naphtha** | hydrocarbons | Persian *naft* (نفط), via Greek *naphtha*. One of the oldest recorded words for petroleum — Herodotus used it, the Byzantines burned it. To "petroleum" as "emmer" is to "wheat" and "paddi" is to "rice": the ancient source-language name for something modernity renamed. |

On Aeolia, naphtha is what thalassocratic sailors call the dark seeps they harvest from shallow shelves to caulk hulls and fuel lamps. The industrial name would come later.

---

## Geological Justification

Aeolia is 4.6 Gyr old (same as Earth), 4.6× Earth radius, 95% ocean, volcanic archipelagos on oceanic crust.

**Why naphtha exists on a volcanic ocean world:**

The archipelagos sit on oceanic crust — no continental sedimentary basins. But the shallow shelves (Dogger Bank analogs, already computed as `shelf_r` per arch) have accumulated biogenic and terrestrial sediment across hundreds of glacial cycles. During glacial maximums (sea level −220m, exposed in the GUI), these shelves were dry land — coastal plains, mangrove-analog swamps, peat bogs. When sea level rose, terrestrial organic deposits were buried under marine sediment.

4.6 billion years of this cycling, plus steep geothermal gradients from volcanic activity, produces fully mature petroleum systems. Source rock (organic-rich sediment), reservoir rock (porous volcanic interbeds), and cap rock (impermeable ash layers) are all present. The result: conventional oil and gas trapped in shallow shelf structures, accessible without deepwater drilling.

**Why naphtha runs out:**

Shelf deposits are thin veneers over oceanic crust — nothing like Earth's supergiant continental basin fields (Ghawar, Permian Basin). Total recoverable reserves per archipelago are modest. An industrializing civilization burns through its local shelf reserves in decades, not centuries. This is the nuclear forcing function: naphtha sustains early industrialization but cannot sustain full modernization. Pu becomes existentially necessary, not merely strategically advantageous.

---

## Substrate Generation

### C (naphtha) — new

```
threshold: shelf_r >= 0.04
probability: 100% if above threshold (it's there or it's not — geology is deterministic)
richness: shelf_r × tidal_range × naphtha_constant
```

This gives ~40–60% of archs some C, but richness varies by an order of magnitude. A few big-shelf, high-tide islands are the supergiant fields of Aeolia. Small-shelf islands have trace seeps — enough for caulking, not enough for industry.

### Existing minerals (unchanged)

- Fe: 100% (universal)
- Cu: 20% flat
- Au: 5% + avg_peak_height × 8%
- Pu: 3% + arch_size × 2%

---

## Resource Discovery and Utilization Model

Minerals exist in the substrate from world generation, but their *strategic value* activates era by era as a function of the discovering civilization's tech level — not as global era transitions. A fast-developing hegemon might unlock C exploitation at tech 7 while a slower one is still in the Au-driven trade phase at tech 5. This temporal asymmetry is deliberate: the first civilization to industrialize gets first pick of naphtha-rich islands before the other one even understands what they're worth.

| Tech threshold | Resource unlocked | Strategic effect |
|---------------|-------------------|-----------------|
| 0 (always) | Fe (sider) | Basic toolmaking. Universal, creates no asymmetry. |
| ~3 | Cu (aes) | Metallurgical advantage — better tools, weapons, currency. First resource asymmetry between archipelagos. Aes-rich islands develop a modest compounding tech lead. |
| ~4 | Au (chrysos) | Network advantage — gold-rich islands become high-priority contact targets. More contacts = more trade = faster knowledge diffusion. Rewards navigation-oriented cultures (the Reach). |
| ~7 | C (naphtha) | Energy revolution. Shallow drilling unlocks shelf hydrocarbons. Industrial scramble for naphtha-rich islands begins. First resource-driven conquest wave. |
| ~9 | Pu (pyra) | Existential resource. Naphtha is depleting; pyra is the only path to sustained civilization. Second (and final) resource-driven conquest wave. |

---

## Era-by-Era Resource Influence

### Antiquity (Era 1–2): Fe only

Expansion driven by population pressure and proximity. All minerals and naphtha exist in the ground but aren't strategic. Surface naphtha seeps are known and used (lamp fuel, caulking) but don't drive conquest. Cu is occasionally worked as ornamentation but not smelted.

### Serial Era (Era 3): Cu and Au unlock

Cu (aes) accelerates serial-era technology — tool-making, early metallurgy, coinage. The `cu_serial_year_bonus` parameter captures this: Cu-bearing islands enter the serial trade network earlier.

Au (chrysos) drives contact priority — gold-rich islands are visited first by long-range navigators (`au_contact_year_bonus`). Au doesn't give a tech advantage, it gives a *network* advantage: more contacts, more trade, more cultural exchange, faster knowledge diffusion. The spread Reach, with islands scattered along the westerlies, benefits more than the dense Lattice — their geography forces them to become navigators, and chrysos rewards navigation.

C (naphtha) is a traded commodity but not a conquest driver. Surface seeps near major trade routes are valuable for caulking and lamp fuel.

### Industrial Era (Era 4): C drives the scramble

When a civilization hits tech ~7 (industrial threshold), shallow drilling becomes possible. Naphtha-rich shelf islands suddenly become the most strategically valuable territory on the planet.

**Conquest mechanic:** Garrison/colonial expansion targets weighted by:
```
target_value = C_remaining[target] / distance(hegemon_core, target)
```
Nearby naphtha-rich islands get conquered first. As local reserves deplete, the scramble extends further — analogous to the European colonial scramble for oil in the Middle East, Baku, Indonesia.

**First-contact asymmetry:** When a tech-7+ hegemon's resource-weighted expansion targets an independent island at tech 3, the resulting absorption is the Sentinelese scenario — guided missile destroyer meets outrigger canoe. The tech gap at the moment of garrison absorption should be recorded; it *is* the contact asymmetry the lore describes. This isn't optional cruelty — the hegemon that doesn't secure shelf resources ceases to exist as an industrial civilization when its own naphtha runs out.

**Depletion mechanic:** Each archipelago's C reserve depletes proportionally to:
```
extraction_rate = population × tech_level × extraction_efficiency
C_remaining[t+1] = C_remaining[t] - extraction_rate × dt
```
When C hits zero, that island's energy contribution drops. The civilization must either conquer more C islands or transition to nuclear.

### Late Industrial / Nuclear Era (Era 5): Pu is the endgame

As total C reserves across a hegemon's controlled islands drop below a critical threshold relative to energy demand, Pu islands become priority conquest targets.

**Conquest mechanic:**
```
target_value = has_Pu[target] × (1.0 / distance(hegemon_core, target))
```

The hegemon that industrialized faster burned C faster and needs Pu sooner — creating a race condition. The slower industrializer may still have C reserves when the faster one is already scrambling for Pu, giving a brief strategic window.

### Story Present: Nuclear Fleets

At story present, both hegemons operate **nuclear-powered air and sea fleets**. This is the convergent endpoint and the optimization target — not merely "tech ≥ 9" but full nuclear propulsion infrastructure.

On a 95% ocean world, nuclear propulsion isn't a military luxury — it's the only way to maintain a coherent civilization across thousands of kilometers of open water. A naphtha-powered fleet has finite endurance tied to fuel logistics and shelf depot chains. A nuclear fleet can operate indefinitely. The moment one hegemon transitions its fleet to nuclear propulsion, the strategic map transforms: the ocean stops being a barrier and becomes a highway.

**Pu demand scales with fleet size, not warhead count.** You don't need much pyra for a bomb. You need a *lot* of pyra for a carrier fleet, a strategic bomber wing, and a network of reactor-powered outposts across the archipelagos. The hegemon that controls more Pu islands doesn't just have strategic independence — it has strategic *mobility* that the other cannot match.

This creates the final strategic asymmetry at story present: both hegemons are nuclear-capable, but the one with more Pu has a larger, more autonomous fleet with greater operational range. The Pu-poor hegemon operates a smaller nuclear fleet supplemented by dependent fuel agreements — functional, but constrained. Both can destroy each other. Only one can project power freely.

---

## Pu Logic Redesign

### Old behavior

`pu_nuclear_tech_fraction` gated tech growth toward nuclear. Both hegemons blocked from nuclear capability if no Pu access. The optimizer crushed this to 0.09, effectively disabling it, because it conflicted with the lore requirement that both hegemons achieve nuclear capability.

### New behavior

Pu determines nuclear **independence and fleet scale**, not nuclear **capability**.

Both hegemons achieve nuclear capability — that's non-negotiable on a world where naphtha runs out. The difference is how they get there and what they can do with it.

| Pu access | Nuclear path | Fleet capability | Sovereignty effect |
|-----------|-------------|-----------------|-------------------|
| Controls Pu islands | Indigenous program | Full nuclear fleet (carriers, strategic aviation, reactor outposts) | +sovereignty (strategic autonomy + mobility) |
| No Pu control | Dependent acquisition (trade/espionage/fuel agreements) | Smaller nuclear fleet, supplemented by dependent fuel supply | −sovereignty (strategic dependency, constrained range) |

Both paths converge to nuclear air and sea fleets by story present. The difference is:
- **Indigenous (Pu-rich):** larger fleet, full operational range, strategic autonomy — analogous to US/USSR blue-water navies
- **Dependent (Pu-poor):** functional fleet, constrained by fuel agreements, limited forward deployment — analogous to UK/French nuclear capability (real but dependent on alliances for full force projection)

### Implementation (sim_proxy.py / history_engine.gd)

```
# During nuclear era tech growth:
if hegemon_controls_pu_island:
    tech_growth *= 1.0              # full rate
    fleet_scale *= 1.0              # full nuclear fleet
    sovereignty += pu_independence_bonus
else:
    tech_growth *= pu_dependent_growth_factor  # 0.6–0.8, tunable
    fleet_scale *= pu_dependent_fleet_factor   # 0.4–0.7, tunable
    sovereignty -= pu_dependency_penalty
```

The `pu_dependent_growth_factor` and `pu_dependent_fleet_factor` are new tunable parameters for the optimizer.

---

## Loss Function Changes

### Remove
- `pu_gate` (old binary Pu blocking term)

### Replace with

**`c_scramble`** — At least one hegemon should exhaust >50% of its C reserves before the nuclear era. Validates that the energy transition forcing function exists.

**`pu_acquisition`** — Both hegemons should control ≥1 Pu island by nuclear era, acquired *during* industrial/nuclear eras (not initial geography). Validates resource-motivated conquest.

**`pu_asymmetry`** — The hegemon with more Pu should have higher sovereignty at story present. Validates that Pu access creates a meaningful strategic independence premium.

**`energy_transition`** — Total world C reserves should be substantially depleted (>70%) by story present. Validates that nuclear wasn't optional — it was the only path forward after naphtha peak.

**`nuclear_fleets`** — Both hegemons should have nuclear fleet capability at story present (tech ≥ 9.0 + Pu access or dependent fuel supply). The Pu-rich hegemon should have higher fleet_scale. Validates the lore endpoint: nuclear air and sea fleets on both sides, asymmetric in scale.

### Keep (from current redesign)
- `pu_convergence` — Both hegemons reach nuclear tech regardless of Pu access. (Already implemented in latest loss.py.)
- `pu_dependency` — Asymmetric Pu access creates strategic tension. (Already implemented.)

---

## New Tunable Parameters

| Parameter | Description | Initial bounds |
|-----------|-------------|---------------|
| `naphtha_constant` | Multiplier for C richness from shelf_r × tidal_range | [0.5, 5.0] |
| `naphtha_extraction_rate` | How fast C depletes relative to pop × tech | [0.001, 0.05] |
| `c_scramble_tech_threshold` | Tech level at which C becomes strategically targetable | [5.0, 8.0] |
| `pu_scramble_c_threshold` | Fraction of C remaining that triggers Pu targeting | [0.1, 0.5] |
| `pu_dependent_growth_factor` | Nuclear tech growth rate without Pu access | [0.4, 0.9] |
| `pu_independence_sov_bonus` | Sovereignty bonus for indigenous nuclear program | [0.05, 0.30] |
| `c_conquest_weight` | How much C richness influences garrison target selection | [0.0, 5.0] |
| `pu_conquest_weight` | How much Pu presence influences garrison target selection | [0.0, 10.0] |
| `pu_dependent_fleet_factor` | Nuclear fleet scale without indigenous Pu access (1.0 = full parity) | [0.3, 0.8] |
| `naphtha_tech_factor` | How strongly naphtha access multiplies industrial tech growth | [0.5, 2.0] |
| `pu_tech_factor` | How strongly Pu access multiplies nuclear tech growth | [0.8, 1.5] |
| `energy_per_capita` | Naphtha demand per unit population × tech (sets depletion speed) | [0.001, 0.02] |
| `cu_tech_bonus` | Cu contribution to serial-era tech growth | [0.0, 0.3] |
| `cu_conquest_weight` | How much Cu presence influences serial-era garrison targeting | [0.0, 3.0] |
| `au_conquest_weight` | How much Au presence influences serial-era garrison targeting | [0.0, 3.0] |

---

## Files to Modify

1. **substrate.gd** / **sim_proxy.py** — Add C generation based on shelf_r × tidal_range
2. **sim_proxy.py** — Add C depletion mechanic, resource-weighted garrison targeting, Pu independence/dependency logic
3. **loss.py** — Replace pu_gate with c_scramble, pu_acquisition, pu_asymmetry, energy_transition
4. **history_engine.gd** — Port changes from sim_proxy once optimizer validates the design
5. **run_optimization.py** — Add new parameter bounds

## Tech Growth ← Resource Coupling

The current tech growth model is population-driven with faction-specific coefficients. Resources affect *timing* (when trade contacts happen) but not *rate* (how fast technology develops). This is historically backwards — on Earth, technology tracks energy availability. The industrial revolution was a coal breakthrough before it was a knowledge breakthrough.

### Proposed: energy-gated tech growth

Each era's tech growth rate should be multiplied by an energy availability factor derived from the dominant resource of that era.

```
tech_growth[era] = base_formula[era] × energy_factor[era]
```

| Era | Energy source | energy_factor formula | Interpretation |
|-----|--------------|----------------------|----------------|
| 1–2 (Antiquity) | Muscle + wind | 1.0 (constant) | No energy constraint on pre-industrial tech. Population and knowledge are the bottleneck. |
| 3 (Serial) | Muscle + wind + Cu tools | 1.0 + cu_tech_bonus × has_Cu | Cu (aes) gives a modest efficiency boost to toolmaking and metallurgy, slightly accelerating serial-era development. Not transformative. |
| 4 (Industrial) | C (naphtha) | naphtha_tech_factor × (C_controlled / C_demand) | Tech growth rate directly proportional to naphtha access. A hegemon controlling more C-rich islands industrializes faster. If C_controlled < C_demand, tech growth is throttled — you can't run factories without fuel. This is the core coupling: energy access → industrialization rate. |
| 5 (Nuclear) | Pu (pyra) | pu_tech_factor × (Pu_controlled > 0 ? 1.0 : pu_dependent_growth_factor) | Full tech growth if you have indigenous Pu. Reduced but nonzero if dependent. Both converge to nuclear fleets, but the Pu-rich hegemon gets there first. |

### C_controlled / C_demand ratio

```
C_controlled = sum(C_remaining[i] for i in controlled_islands)
C_demand = total_population × tech_level × energy_per_capita
energy_factor = clamp(C_controlled / C_demand, 0.3, 1.5)
```

The clamp at 0.3 prevents total stagnation (even without naphtha, knowledge still diffuses). The ceiling at 1.5 represents energy surplus — a hegemon drowning in naphtha can fund speculative research (Aeolia's Bell Labs).

This creates three distinct industrial trajectories:
- **Energy surplus (ratio > 1.0):** accelerated tech growth, rapid industrialization, early nuclear transition
- **Energy balance (ratio ≈ 1.0):** normal tech growth, standard trajectory
- **Energy deficit (ratio < 1.0):** throttled tech growth, desperate scramble for more C islands, delayed nuclear transition

### Implications for the scramble

Energy-gated tech growth makes the naphtha scramble *self-reinforcing*. A hegemon that conquers C-rich islands gets more energy, which accelerates its tech, which increases its military capability, which lets it conquer more islands. This is the positive feedback loop that produced the British Empire and Standard Oil. The loss function doesn't need to prescribe colonialism — energy-gated growth produces it as an emergent outcome.

Conversely, the hegemon that falls behind in the naphtha scramble faces a death spiral: less energy → slower tech → weaker military → loses more islands → even less energy. The only escape is leapfrogging to nuclear — which requires Pu, which requires its own scramble. This is the design tension that makes the late-industrial era dramatic.

### Resource-driven garrison targeting (updated)

The garrison absorption mechanic should select targets based on era-appropriate resource value:

```python
def garrison_target_weight(target_arch, hegemon, era, tech_level):
    base = population[target] / distance(hegemon_core, target)

    if tech_level < 3:
        return base  # antiquity: pure proximity + population

    if tech_level < 7:
        # serial era: Cu and Au matter
        resource_bonus = (cu_conquest_weight * has_Cu[target] +
                         au_conquest_weight * has_Au[target])
        return base + resource_bonus

    if tech_level < 9:
        # industrial era: naphtha is king
        resource_bonus = c_conquest_weight * C_remaining[target]
        return base + resource_bonus

    # nuclear era: Pu is existential
    resource_bonus = (pu_conquest_weight * has_Pu[target] +
                     c_conquest_weight * C_remaining[target] * 0.3)  # C still matters, less
    return base + resource_bonus
```

The tech_level thresholds are per-hegemon, not global — a tech-8 Reach targets naphtha islands while a tech-5 Lattice is still chasing gold trade routes. This temporal asymmetry produces the first-contact scenarios where industrial powers absorb pre-industrial independents.

---

## Open Questions

- Should C depletion be visible in the GUI? (e.g., a resource bar per archipelago that drains over time)
- Should naphtha seeps be visible on the globe as a terrain feature?
- Would the Reach and Lattice have different words for naphtha? (Different discovery contexts — thalassocratic sailors vs. hydraulic farmers)
- Should the pre-filter (million_seed_filter.py) also screen for C distribution, or is shelf_r sufficient as a proxy?
- Should fleet_scale be a visible stat in the history engine output, or derived at display time from tech + Pu control?
- How does the nuclear fleet asymmetry interact with the Dark Forest break? (Does the Pu-rich hegemon's larger fleet create a first-strike temptation, or does mutual nuclear capability still produce deterrence?)
