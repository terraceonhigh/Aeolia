# History Engine v2 — Unified Plan

> Compiled from RESOURCE_SYSTEM_DESIGN.md and ENERGY_REWRITE_PLAN.md.
> Supersedes both documents as the single source of truth for the rewrite.

---

## 1. What This Is

A rewrite of the Aeolia history engine from era-coefficient-driven simulation to energy-economics-driven simulation. The goal is threefold:

1. **Narrative fidelity** — produce lore-accurate worlds (Baseline Earth loss function) as emergent outcomes of geography, resources, and political culture rather than prescribed era tables.
2. **Optimizer efficiency** — 19 physically meaningful parameters instead of 33 that fight each other. TPE converges faster, no structural loss floors from conflicting terms.
3. **Research generality** — swappable loss functions turn the simulator into a counterfactual engine for political science, economic history, and anthropology. Adjusting the 19 parameters generates alien social science, not just Earth reruns.

---

## 2. Resource System

### 2.1 Naming

| Symbol | Aeolian name | Earth analog | Origin and role |
|--------|-------------|--------------|-----------------|
| Fe | **sider** | iron | Greek *sideros*. Universal in volcanic basalt. Every arch has it. Enables toolmaking but creates no strategic asymmetry. |
| Cu | **aes** | copper | Latin *aes*. ~20% of archs, in malachite veins. First strategic mineral — metallurgical advantage, currency, early trade networks. |
| Au | **chrysos** | gold | Greek *chrysos*. Hydrothermal veins, concentrated by peak height. Doesn't make you powerful; makes you *visible*. Draws navigators, creates contact points. |
| C | **naphtha** | hydrocarbons | Persian *naft* via Greek *naphtha*. Shelf deposits from glacial-cycle sedimentation over 4.6 Gyr. The industrial energy source. Depletes. |
| Pu | **pyra** | plutonium | Greek *pyr* (fire). Anomalously warm rocks in deep volcanic deposits. A curiosity until industrial physics unlocks fission. The existential endgame resource. |

### 2.2 Substrate generation

| Resource | Generation rule |
|----------|----------------|
| Fe | 100% of archs |
| Cu | 20% flat probability |
| Au | 5% + avg_peak_height × 8% |
| Pu | 3% + arch_size × 2% |
| C | present if shelf_r ≥ 0.04; richness = shelf_r × tidal_range × `naphtha_richness` |

C is deterministic (geology, not probability). Richness varies by an order of magnitude — a few big-shelf, high-tide islands are Aeolia's supergiant fields. Small-shelf islands have trace seeps only.

### 2.3 Geological justification for naphtha

Aeolia: 4.6 Gyr old, 4.6× Earth, 95% ocean, volcanic archipelagos on oceanic crust. No continental sedimentary basins — but shallow shelves accumulated biogenic and terrestrial sediment across hundreds of glacial cycles. During glacial maximums (sea level −220m, exposed in the GUI), shelves were dry land — coastal plains, swamp forests, peat bogs. Terrestrial deposits buried under marine sediment when sea level rose. 4.6 billion years of cycling + steep geothermal gradients from volcanism = fully mature petroleum systems.

Shelf deposits are thin veneers over oceanic crust. Total reserves per arch are modest. Industrial civilizations exhaust local shelf reserves in decades, not centuries. This is the nuclear forcing function.

### 2.4 Discovery and utilization

Resources exist from world generation; strategic value activates as a function of the *discovering civilization's* tech level, not global era transitions.

| Tech | Resource unlocked | Strategic effect |
|------|-------------------|-----------------|
| 0 | Fe (sider) | Toolmaking. Universal, no asymmetry. |
| ~3 | Cu (aes) | Metallurgical advantage, currency, first resource asymmetry. |
| ~4 | Au (chrysos) | Network advantage — Au-rich islands are high-priority contact targets. Rewards navigation. |
| ~7 | C (naphtha) | Energy revolution. Shallow drilling. Industrial scramble begins. |
| ~9 | Pu (pyra) | Existential resource. Naphtha depleting; pyra is the only path to sustained civilization. |

A fast-developing hegemon unlocks C exploitation while a slower one is still in the Au trade phase. This temporal asymmetry produces the first-contact scenarios where industrial powers absorb pre-industrial independents — Sentinelese outcomes driven by resource economics, not narrative fiat.

---

## 3. Three-Layer Architecture

### Design principle: faction-agnostic simulator

The simulator does not know about "the Reach" or "the Lattice." These are characters in a specific narrative (Baseline Earth). The simulator knows about archipelagos, crops, political cultures, and energy. Hegemons emerge when one polity's geography + crop + resources produce enough surplus to absorb neighbors. Whether that produces two hegemons, four, one, or none is an emergent outcome.

The crop-to-civilization mapping determines each polity's political culture:

| Crop | Political culture | Default allocation tendency |
|------|------------------|---------------------------|
| emmer | Civic | High expansion, high tech, low consolidation |
| paddi | Subject | Low expansion, moderate tech, high consolidation |
| taro | Parochial (chieftain) | Balanced, lower overall surplus |
| nori | Parochial-Civic hybrid | High tech, maritime trade orientation |
| sago | Parochial (communal) | Low expansion, low tech, moderate consolidation |
| papa | Parochial-Subject | Moderate consolidation, cold-adapted |

"The Reach" and "the Lattice" are what happens when the Baseline Earth loss function selects for a world where a Civic polity and a Subject polity each become hegemons. Other loss functions may produce entirely different hegemon cultures, or no hegemons at all.

### Pedagogical frame (top-down, for the social scientist)

```
Why does this polity colonize?
  → Its political culture allocates surplus to expansion
Why does it have surplus?
  → It controls naphtha-rich shelves
Why does it control those shelves?
  → Its Civic culture drove earlier maritime exploration
Why is the culture Civic?
  → Emmer agriculture on dispersed islands rewards competitive individualism
```

The simulation computes bottom-up. The student reads top-down. Every question bottoms out in geography → crop → culture. No faction names appear in the causal chain.

### Computational frame (bottom-up, for the optimizer)

```
LAYER 1: Energy Economics
  Resource map + tech level → energy_supply, energy_demand, surplus per polity per tick
  Sets the ceiling on all civilizational activity

LAYER 2: Political Allocation
  Surplus + political culture + IR posture → expansion / tech / consolidation budgets
  Crop determines culture type; culture type determines default allocation ratios
  (Civic: wide/trade/innovation; Subject: deep/admin/consolidation; etc.)

LAYER 3: Social Dynamics
  Spec v0.4 tick pipeline — 8 stages, all social science concepts, energy-coupled:
    1. Rumor propagation (social — unchanged)
    2. Bayesian belief update (epistemological — unchanged)
    3. IR posture selection (Mearsheimer/Walt/Schweller — capability now = energy surplus)
    4. Solow-Romer production (economic — energy as TFP input)
    5. Thompson Sampling edge selection (cultural — Beta priors from culture type, funding gated by budget)
    6. Expedition resolution (logistical — success probability from tech + energy)
    7. Sovereignty/tradeIntegration drift (political — energy-gated extraction dynamics)
    8. Substrate drift (anthropological — modernist layer modulated by energy surplus)
```

---

## 4. Parameter Set (21 total)

### Political culture (what kind of civilization emerges from this crop?)

Allocation ratios and knowledge compounding are keyed to **political culture type**, not faction name. Each culture type derived from the crop-to-civilization mapping gets its own tunable allocation profile. The optimizer tunes culture-level parameters; any polity with that crop inherits them.

Only the two dominant culture types (Civic and Subject) get full allocation profiles — these are the cultures that historically produce hegemons. Minor cultures (Parochial variants) use a shared default profile.

| # | Parameter | Controls | Bounds |
|---|-----------|----------|--------|
| 1 | `civic_expansion_share` | Civic (emmer) budget fraction → expansion | [0.2, 0.6] |
| 2 | `civic_tech_share` | Civic (emmer) budget fraction → research | [0.2, 0.6] |
| 3 | `civic_consolidation_share` | Civic (emmer) budget fraction → integration/admin | [0.1, 0.4] |
| 4 | `subject_expansion_share` | Subject (paddi) budget fraction → expansion | [0.1, 0.4] |
| 5 | `subject_tech_share` | Subject (paddi) budget fraction → research | [0.1, 0.5] |
| 6 | `subject_consolidation_share` | Subject (paddi) budget fraction → integration/admin | [0.3, 0.7] |
| 7 | `parochial_expansion_share` | Parochial (taro/sago/papa/nori) budget fraction → expansion | [0.1, 0.4] |
| 8 | `parochial_tech_share` | Parochial budget fraction → research | [0.1, 0.4] |
| 9 | `A0_civic` | Knowledge compounding for Civic polities (dispersed trade network effect) | [0.8, 1.5] |
| 10 | `A0_subject` | Knowledge compounding for Subject polities (institutional continuity) | [0.5, 1.2] |
| 11 | `A0_parochial` | Knowledge compounding for Parochial polities (oral tradition, local knowledge) | [0.3, 0.9] |

Each culture's shares must sum to 1.0. Optimizer samples two freely; third = 1 − a − b, clamped to [0.05, 1.0]. Parochial consolidation_share = 1 − expansion − tech.

This means a nori-culture maritime federation, if it acquires enough surplus, uses the Parochial allocation profile and A₀ — it can become a power, but with different spending priorities than a Civic or Subject hegemon. The Baseline Earth loss function selects for worlds where Civic and Subject polities dominate. Other loss functions may find worlds where Parochial cultures thrive.

### Material conditions (what constrains any civilization?)

| # | Parameter | Controls | Bounds |
|---|-----------|----------|--------|
| 12 | `cu_unlock_tech` | Tech level at which Cu becomes strategic | [2.0, 4.0] |
| 13 | `au_contact_bonus` | How strongly Au pulls serial-era navigators | [100, 2000] |
| 14 | `naphtha_richness` | C reserve size (multiplier on shelf_r × tidal_range) | [0.5, 5.0] |
| 15 | `naphtha_depletion` | C extraction rate (how fast reserves burn) | [0.001, 0.05] |
| 16 | `energy_to_tfp` | Energy surplus → Solow-Romer total factor productivity | [0.5, 2.0] |
| 17 | `pu_dependent_factor` | Nuclear tech/fleet growth rate without indigenous Pu | [0.4, 0.9] |
| 18 | `resource_targeting_weight` | Resource value bias in garrison target selection | [0.0, 5.0] |

### Contact dynamics (what happens when any civilizations meet?)

| # | Parameter | Controls | Bounds |
|---|-----------|----------|--------|
| 19 | `epi_base_severity` | Base mortality of disease shock at first contact | [0.15, 0.50] |
| 20 | `sov_extraction_decay` | Sovereignty erosion rate under colonial extraction | [0.01, 0.10] |
| 21 | `df_detection_range` | GC distance at which industrial signals trigger Dark Forest | [0.3, 1.0] |

Note: `transport_cost_per_rad` from the earlier draft is folded into `resource_targeting_weight` — the optimizer can find the tradeoff between resource value and distance through a single weight rather than separate parameters for each.

---

## 5. Tick Pipeline

One tick ≈ one generation (~50 years). Stages named for social science concepts; energy coupling happens inside each stage.

### 5.1 Resource accounting (bookkeeping)

Per polity per tick: sum C_remaining across controlled islands, compute energy_supply / energy_demand, derive surplus and energy_ratio (clamped [0.3, 1.5]). Every archipelago is a polity; polities that have absorbed neighbors aggregate their resources.

### 5.2 Solow-Romer production

`Y = A × K^0.3 × L^0.7` where A = `energy_to_tfp` × energy_ratio × knowledge_stock. Knowledge stock grows from tech_budget × A₀ × log₂(trade contacts). A₀ is determined by the polity's political culture type (Civic / Subject / Parochial). This is the spec v0.4 budget computation stage, now energy-coupled.

### 5.3 Political allocation

Budget split by political culture type (expansion / tech / consolidation shares looked up from `civic_*`, `subject_*`, or `parochial_*` parameters based on the polity's primary crop). IR posture modifies allocation: "explore" and "project" shift weight toward expansion; "fortify" and "hedge" shift weight toward consolidation. Renormalized after posture adjustment.

A polity that absorbs neighbors with different crops retains its *core* crop's political culture — the conquering culture dominates, just as the Roman Empire remained Roman regardless of what it absorbed. Absorbed polities' crops affect trade goods and epi dynamics, not the hegemon's political culture.

### 5.4 Rumor propagation

Unchanged from spec v0.4. Flows through trade edges. Industrial/nuclear civs generate detectable signals within `df_detection_range × (tech / 10.0)`.

### 5.5 Bayesian belief update

Unchanged. Each polity's otherAwareness of each other polity accumulates: +0.05 unfamiliar goods, +0.10 multi-source rumors, +0.25 unknown vessels, →1.0 nuclear intercept (Dark Forest break). Not limited to two actors — every polity maintains beliefs about every other polity it has evidence of.

### 5.6 IR posture selection

Unchanged table, applied per polity. Capability = categorize(surplus): HIGH/MED/LOW. Mearsheimer at HIGH+HIGH, Walt at MED+HIGH, Schweller at LOW+HIGH, etc. Small independent polities will typically be LOW capability, selecting "align" or "free_ride" — bandwagoning toward the nearest power or buck-passing. This is emergent, not prescribed.

### 5.7 Expansion (Thompson Sampling + resource targeting)

Candidate targets scored by: Thompson Sampling cultural prior + resource_targeting_weight × resource_value(tech) + denial_value − transport_cost. Funded in score order until expansion_budget exhausted. resource_value is tech-gated: Cu at tech 3+, Au at 4+, C at 7+, Pu at 9+. No era tables.

Thompson Sampling Beta priors are culture-typed: Civic gets Beta(2,1) — optimistic explorers. Subject gets Beta(1,2) — skeptical consolidators. Parochial gets Beta(1,1) — uniform, no strong prior either way. These priors mean a Civic polity with surplus will range widely, a Subject polity will garrison what's close, and a Parochial polity will expand opportunistically. A nori-culture maritime polity with Parochial-Civic hybrid culture could use Beta(1.5,1) — moderate optimism, reflecting its trade orientation.

### 5.8 Tech growth

`delta_tech = (tech_budget / pop) × A₀[culture_type] × log₂(contacts) × energy_ratio`. No era-specific coefficients. No tech floors. No faction-specific formulas. Energy gates the rate; knowledge compounds it; culture type determines the compounding coefficient.

### 5.9 Sovereignty drift

Extraction pressure = extraction_rate / distance. Recovery = sov_extraction_decay × sovereignty × population. Energy gate: extraction capped by controller's surplus. Sovereignty drifts toward extraction or recovery depending on balance. C depletes at extraction sites when controller tech ≥ 7.

### 5.10 Epidemic shock (first contact only)

Severity = epi_base_severity + random, scaled by crop distance. Recovery rate proportional to controlling faction's energy surplus. Pre-exposed (trade-chain contact) archs take 30% severity.

---

## 6. Pu Logic

### Old: Pu gates nuclear capability

`pu_nuclear_tech_fraction` blocked tech growth toward nuclear. Optimizer crushed it to 0.09. Structurally incompatible with the requirement that industrial polities achieve nuclear capability on a naphtha-depleting world.

### New: Pu determines nuclear independence and fleet scale

Any polity that industrializes eventually goes nuclear — non-negotiable on a world where naphtha runs out. Pu determines *how*:

| Pu access | Path | Fleet | Sovereignty |
|-----------|------|-------|-------------|
| Controls Pu islands | Indigenous program | Full nuclear fleet | +autonomy |
| No Pu control | Dependent acquisition | Smaller fleet, fuel agreements | −autonomy |

Pu demand scales with fleet size (carriers, strategic aviation, reactor outposts), not warhead count. A Pu-rich polity has strategic mobility; a Pu-poor one has constrained range. This applies to any polity that achieves nuclear-era tech, regardless of its political culture.

---

## 7. Story Present Endpoint

On a 95% ocean world, nuclear propulsion is the only way to maintain coherent civilization across thousands of kilometers. A naphtha-powered fleet has finite range; a nuclear fleet operates indefinitely. The moment any polity transitions to nuclear propulsion, the ocean becomes a highway for that polity.

The Baseline Earth loss function targets a specific endpoint: two dominant hegemons (Civic and Subject) with nuclear fleets. Other loss functions may target different endpoints — multipolar nuclear, single hegemon, or even civilizational collapse before nuclear transition. The simulator doesn't prescribe which outcome is "correct."

---

## 8. Loss Function

### 8.1 Baseline Earth (narrative loss — the Aeolia lore)

This is the *only* loss function that mentions the Reach and Lattice by name. It encodes the specific narrative requirements of the Aeolia worldbuilding project. 12 terms.

**Structural preconditions (geography — narrative-specific):**
- `latitude_separation` — the Civic hegemon's centroid in mid-latitudes [35°, 55°], Subject hegemon's centroid tropical [<28°]
- `civ_gap` — min GC distance between the two dominant polities > threshold
- `density_asymmetry` — Subject polity's cluster denser than Civic polity's spread (relaxed to 1.1 rad)
- `two_hegemons` — exactly two polities achieve hegemon status (controlling >15% of total population each), one Civic, one Subject

**Energy outcomes:**
- `naphtha_peak` — at least one hegemon exhausts >50% C before nuclear era
- `energy_transition` — total world C >70% depleted at story present
- `pu_acquisition` — both hegemons control ≥1 Pu island by story present, acquired during industrial+ eras

**Civilizational outcomes:**
- `nuclear_fleets` — both hegemons at tech ≥9.0 with nuclear fleet capability
- `fleet_asymmetry` — Pu-rich hegemon has larger fleet_scale
- `sovereignty_gradient` — colonies lower sovereignty than core; post-colonial recovery visible
- `dark_forest_timing` — DF break (between the two hegemons specifically) in nuclear era (−200 to −40 BP)
- `el_dorados` — ≥10 archs uncontacted at story present

**Diagnostics (tracked, not penalized):**
- `tech_gap_at_contact` — max tech differential at absorption of independent by either hegemon
- `scramble_onset` — tick when resource-weighted expansion first targets C-rich islands
- `pu_scramble_onset` — tick when Pu-weighted expansion begins
- `naphtha_exhaustion_tick` — when first hegemon's C drops below critical
- `discovery_curve` — contact count by era (tracked for Σ2ⁿ validation, not penalized — should emerge)

### 8.2 Alternative loss functions (future — social science research)

Each loss function is the same simulator, same 19 parameters, different hypothesis:

- **Symmetric Hegemon** — penalize any asymmetry at story present. Tests: can political culture override material conditions?
- **No Dark Forest** — reward early contact + stable coexistence. Tests: liberal internationalism vs. realism.
- **Reversed Polarity** — dense cluster becomes maritime explorer, dispersed becomes consolidator. Tests: is crop-to-civilization mapping deterministic?
- **Resource Curse** — reward naphtha-rich hegemon stagnating. Tests: paradox of plenty as structural mechanism.
- **Multipolar** — 4+ peer powers at story present. Tests: is bipolarity a structural attractor (Waltz) or contingent?
- **Total Collapse** — industrial collapse before nuclear transition. Tests: under what conditions does civilization fail the energy transition?
- **First Contact Variance** — maximize tech gap at contact. Tests: what structural conditions produce worst indigenous outcomes?
- **Isolationist Lattice** — Lattice never expands beyond home cluster. Tests: is imperial expansion inevitable with surplus, or culturally contingent?

---

## 9. Implementation Sequence

### Phase 1: sim_proxy.py (the optimizer target)

Build the energy-coupled simulation in Python first. Must be fast (<10ms/seed), pure Python (no external deps — bash hook blocks pip).

1. Add C generation to substrate
2. Implement Layer 1: resource accounting + energy surplus
3. Implement Layer 2: political allocation (3 shares per faction)
4. Rewire tech growth → tech_budget × energy_ratio × A₀
5. Rewire garrison targeting → resource_value(tech) instead of era tables
6. Add C depletion per tick
7. Add Pu independence/dependency logic
8. Add fleet_scale output

**Verify:** Run on seed 216089 with hand-tuned params. A Civic polity industrializes before a Subject polity (dispersed geography → more Au contacts → faster knowledge), naphtha scramble at tech ~7, multiple polities achieve nuclear capability by story present, ≥10 archs uncontacted. Note: at this stage, we verify mechanics, not narrative — the Baseline Earth loss function handles lore fidelity in Phase 2.

### Phase 2: loss.py

Rewrite with 12-term structure. Drop 16 terms that should now be emergent. Add energy-specific terms.

**Verify:** Run on seed 216089. Each term traceable to a geographic or energetic cause.

### Phase 3: Optimizer run

21-parameter bounds, 10,000 trials, seed 216089 + top 5 candidates from million-seed search.

**Expected:** Faster convergence (21-dim vs 33-dim), lower floor (no Pu gate conflict, no faction-specific parameter conflicts), emergent colonial/sovereignty dynamics. The Baseline Earth loss function drives this run — it's the one that selects for the Reach/Lattice narrative.

### Phase 4: GDScript port

Mechanical translation from sim_proxy.py → history_engine.gd once optimizer validates.

### Phase 5: GUI integration

- C depletion visualization per arch
- fleet_scale on political map
- Resource-motivated expansion edges in distinct color
- Naphtha seep markers at shelf positions

### Phase 6 (future): Astronomic and geologic parameters

Make the planet itself a variable. Two-stage optimizer:

**Outer loop** (~10 slow parameters, searched over hundreds of configurations):
- Ocean fraction (currently 95%)
- Planet radius (currently 4.6× Earth)
- Axial tilt (seasonality → crop cycles → social organization)
- Volcanic intensity (peak height distribution, mineral concentration)
- Shelf width distribution (naphtha substrate)
- Tectonic age (sediment accumulation → hydrocarbon maturation)
- Sea level at story present (how much shelf is submerged)
- Archipelago count (currently 42)
- Latitude placement rules
- Mantle heat flux (geothermal gradient)

**Inner loop** (19 history engine parameters, 10k trials per planet, ~17 min each):
Standard TPE optimization as in Phase 3.

**Output:** A catalog of planet-civilization pairs. Each one a self-consistent world with its own geography, resource distribution, political history, and emergent social science. Not one Aeolia — a library of possible worlds.

The research question becomes: across what range of planetary conditions do the social science outcomes we observe on Earth (bipolarity, colonial extraction, nuclear deterrence, the resource curse) continue to hold? Which are universal dynamics of civilizational development, and which are parochial accidents of Earth's specific initial conditions?

---

## 10. What Dies in the Rewrite

33 current parameters → 21. Two more than the earlier 19-param draft because political culture is now parameterized by culture type (Civic, Subject, Parochial) rather than by faction name (Reach, Lattice), adding A₀_parochial and the Parochial allocation shares. The tradeoff is worth it: these 21 parameters work for any world the simulator produces, not just two-hegemon narratives.

These effects become emergent from energy economics:

| Removed | Replacement mechanism |
|---------|----------------------|
| `antiquity_base_growth` | Surplus-driven growth at low energy demand |
| `antiquity_lattice_pop_mult` | Higher consolidation_share → more population retention |
| `serial_shock_base_min/range` | Epi unchanged; recovery now energy-gated |
| `serial_trade_rate` | Thompson Sampling + expansion budget |
| `reach/lattice_serial_base_mult` | Expansion + tech shares |
| `reach/lattice_serial_log_coeff` | A₀ (knowledge compounding) |
| `extraction_base/per_year` | Sovereignty drift from energy extraction pressure / naphtha_depletion |
| `garrison_absorb_base` | expansion_budget / transport_cost |
| `reach_colony_surplus` | reach_expansion_share |
| `lattice_garrison/trib_bonus` | Emerges from high consolidation spending |
| `reach/lattice_ind_tech/pot/log` | tech_share × energy_ratio × A₀ |
| `tech_floor_reach/lattice_ind` | No floors — energy gates the rate |
| `reach/lattice_nuclear_pop_mult` | Nuclear energy surplus → population boom (emergent) |
| `nuclear_access_*` | pu_dependent_factor |
| `cu_serial_year_bonus` | cu_unlock_tech |
| `pu_nuclear_tech_fraction` | pu_dependent_factor (dependency, not gate) |

---

## 11. Risks

1. **Energy model too abstract for historical texture.** Crop-to-civilization mapping, stimulant trade, textile economies are cultural, not energetic. *Mitigation:* Layer 3 preserves all cultural texture. Energy sets the envelope; culture fills it.

2. **Solow-Romer α sensitivity.** Capital share 0.3, labor share 0.7 are Earth-calibrated. *Mitigation:* Can make α tunable (20th param) if dynamics are wrong. Try fixed first.

3. **C depletion calibration.** Too fast → nobody industrializes. Too slow → no nuclear forcing. *Mitigation:* `naphtha_richness` and `naphtha_depletion` are both tunable; optimizer finds the balance.

4. **Era timing loss of control.** Current model guarantees DF break in nuclear era. Energy model depends on the energy curve producing the right trajectory. *Mitigation:* `df_detection_range` provides direct DF timing control. `dark_forest_timing` loss term catches failures.

5. **Σ2ⁿ non-emergence.** Discovery doubling reflects exponential maritime + economic growth on Earth. May not emerge from energy dynamics alone. *Mitigation:* Track as diagnostic. Investigate A₀ and energy parameters before reimposing redistribution as fallback.

6. **Pedagogical legibility.** A single `colonial_extraction_rate` is easier to teach in a 50-minute lecture than tracing the energy loop. *Mitigation:* This is a depth-vs-accessibility tradeoff. The energy model is better pedagogy (real political economy doesn't have a slider either) but harder to introduce. Documentation should provide both the top-down reading (for students) and the bottom-up computation (for implementers).
