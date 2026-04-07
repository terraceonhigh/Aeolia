# Energy Economics Rewrite — Implementation Plan

## Design Goal

Replace the era-coefficient-driven history engine with a three-layer architecture (energy substrate → political allocation → social dynamics) while preserving the spec v0.4 tick pipeline and all social science elements. The resulting model should be faster to optimize because:

1. Fewer parameters (~19 vs ~33), all physically meaningful
2. No parameters that structurally fight each other (the current Pu gate vs tech convergence problem)
3. Emergent era transitions instead of prescribed era tables — the optimizer searches over energy curves, not per-era coefficients
4. Loss function simplifies: check outcomes, not intermediate mechanisms

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  LAYER 1: Energy Economics (substrate)                  │
│  Determines the ceiling on all civilizational activity  │
│                                                         │
│  Inputs:  resource map (Fe, Cu, Au, C, Pu per arch)    │
│           tech level → resource unlock thresholds       │
│  Outputs: energy_supply, energy_demand, surplus         │
│           per hegemon per tick                          │
└────────────────────┬────────────────────────────────────┘
                     │ surplus
┌────────────────────▼────────────────────────────────────┐
│  LAYER 2: Political Allocation (faction personality)    │
│  Determines how surplus is spent                        │
│                                                         │
│  Inputs:  surplus, faction type, posture (from L3)      │
│  Outputs: expansion_budget, tech_budget,                │
│           consolidation_budget, military_budget          │
└────────────────────┬────────────────────────────────────┘
                     │ budgets
┌────────────────────▼────────────────────────────────────┐
│  LAYER 3: Social Dynamics (texture)                     │
│  Determines what actually happens given budgets         │
│                                                         │
│  Spec v0.4 pipeline stages:                             │
│  1. Rumor propagation                                   │
│  2. Bayesian belief update (otherAwareness)             │
│  3. IR posture selection (Mearsheimer/Walt/Schweller)   │
│  4. Solow-Romer production (now energy-coupled)         │
│  5. Thompson Sampling edge selection (Beta priors)      │
│  6. Expedition resolution                               │
│  7. Sovereignty/tradeIntegration drift                  │
│  8. Substrate drift (modernist layer)                   │
└─────────────────────────────────────────────────────────┘
```

---

## Parameter Set (19 total)

### Layer 1 — Energy (8 params)

These replace the ~15 era-specific growth coefficients in the current model.

| # | Parameter | What it controls | Bounds |
|---|-----------|-----------------|--------|
| 1 | `cu_unlock_tech` | Tech level at which Cu becomes strategically useful | [2.0, 4.0] |
| 2 | `au_contact_bonus` | How strongly Au pulls navigators (same role as current `au_contact_year_bonus`) | [100, 2000] |
| 3 | `naphtha_richness` | Multiplier on shelf_r × tidal_range for C reserve size | [0.5, 5.0] |
| 4 | `naphtha_depletion` | Extraction rate: how fast C burns relative to pop × tech | [0.001, 0.05] |
| 5 | `energy_to_tfp` | How energy surplus converts to Solow-Romer total factor productivity | [0.5, 2.0] |
| 6 | `pu_dependent_factor` | Nuclear tech/fleet growth rate without indigenous Pu | [0.4, 0.9] |
| 7 | `resource_targeting_weight` | How strongly resource value biases garrison target selection over proximity | [0.0, 5.0] |
| 8 | `transport_cost_per_rad` | Energy cost of projecting power per radian of great-circle distance | [0.1, 2.0] |

### Layer 2 — Political Allocation (6 params)

These replace the per-faction per-era multipliers. Each faction gets 3 ratios that sum to 1.0 (so really 2 free params each = 4 free params, but expressed as 6 for clarity).

| # | Parameter | What it controls | Bounds |
|---|-----------|-----------------|--------|
| 9 | `reach_expansion_share` | Fraction of Reach surplus allocated to expansion | [0.2, 0.6] |
| 10 | `reach_tech_share` | Fraction of Reach surplus allocated to tech/research | [0.2, 0.6] |
| 11 | `reach_consolidation_share` | Fraction of Reach surplus allocated to integration/admin | [0.1, 0.4] |
| 12 | `lattice_expansion_share` | Fraction of Lattice surplus allocated to expansion | [0.1, 0.4] |
| 13 | `lattice_tech_share` | Fraction of Lattice surplus allocated to tech/research | [0.1, 0.5] |
| 14 | `lattice_consolidation_share` | Fraction of Lattice surplus allocated to integration/admin | [0.3, 0.7] |

Constraint: each faction's shares must sum to 1.0. The optimizer samples two shares freely; the third is `1 - a - b`, clamped to [0.05, 1.0].

### Layer 3 — Social Dynamics (5 params)

These are the surviving social-science parameters that energy economics doesn't replace.

| # | Parameter | What it controls | Bounds |
|---|-----------|-----------------|--------|
| 15 | `A0_reach` | Knowledge compounding rate for Reach (network effect of dispersed trade) | [0.8, 1.5] |
| 16 | `A0_lattice` | Knowledge compounding rate for Lattice (institutional continuity) | [0.5, 1.2] |
| 17 | `epi_base_severity` | Base mortality of disease shock at first contact | [0.15, 0.50] |
| 18 | `sov_extraction_decay` | How fast sovereignty erodes under colonial extraction (energy-gated ceiling) | [0.01, 0.10] |
| 19 | `df_detection_range` | Great-circle distance at which industrial signals become detectable (Dark Forest trigger range) | [0.3, 1.0] |

---

## Tick Pipeline (one tick = one generation, ~50 years)

Each tick processes all archipelagos. The pipeline is the spec v0.4 8-stage design, now energy-coupled.

### Stage 1: Resource accounting

Per arch, per tick. No social science — pure bookkeeping.

```python
def resource_accounting(arch, tick):
    # What resources does this arch have?
    C_remaining = arch.naphtha - cumulative_extraction
    has_Pu = arch.minerals.Pu
    has_Cu = arch.minerals.Cu
    has_Au = arch.minerals.Au

    # What's the controlling faction's total energy picture?
    faction = arch.faction
    energy_supply = sum(C_remaining[i] for i in faction.controlled)
    energy_demand = faction.total_pop * faction.tech * energy_per_capita
    faction.surplus = energy_supply - energy_demand
    faction.energy_ratio = clamp(energy_supply / max(energy_demand, 0.01), 0.3, 1.5)
```

### Stage 2: Solow-Romer production (spec stage 4, moved up)

Energy-coupled production determines the total budget *before* political allocation. This is the Solow-Romer step from spec v0.4, now with energy as TFP.

```python
def production(faction, tick):
    K = faction.capital  # accumulated from prior investment
    L = faction.total_pop
    A = energy_to_tfp * faction.energy_ratio * knowledge_stock(faction)

    # Solow-Romer: Y = A * K^alpha * L^(1-alpha)
    Y = A * (K ** 0.3) * (L ** 0.7)

    faction.budget = Y

    # Knowledge stock grows from tech investment + trade contacts
    # A0 determines how contacts compound into knowledge
    faction.knowledge += A0_faction * log2(1 + faction.trade_contacts) * faction.tech_budget
```

### Stage 3: Political allocation (new — Layer 2)

Faction personality determines how the budget gets split. This replaces all per-era per-faction coefficients.

```python
def allocate(faction, tick):
    B = faction.budget
    posture = faction.current_posture  # from IR stage

    # Base allocation from faction personality
    exp_share = faction.expansion_share
    tech_share = faction.tech_share
    cons_share = faction.consolidation_share

    # Posture modifies allocation
    if posture in ("explore", "project"):
        exp_share *= 1.3; cons_share *= 0.7
    elif posture in ("fortify", "hedge"):
        exp_share *= 0.7; cons_share *= 1.3

    # Renormalize
    total = exp_share + tech_share + cons_share

    faction.expansion_budget = B * exp_share / total
    faction.tech_budget = B * tech_share / total
    faction.consolidation_budget = B * cons_share / total
```

### Stage 4: Rumor propagation (spec stage 1)

Unchanged from spec v0.4. Rumors flow through trade edges. Energy surplus affects signal generation (industrial civs are louder) but not propagation mechanics.

```python
def propagate_rumors(world, tick):
    for edge in world.plateau_edges:
        if edge.trade_active:
            # Rumors flow bidirectionally along trade routes
            propagate(edge.src, edge.dst, attenuation=0.8)

    # Industrial/nuclear civs generate detectable signals
    for arch in world.archs:
        if arch.tech >= 7:
            signal_radius = df_detection_range * (arch.tech / 10.0)
            for neighbor in archs_within(arch, signal_radius):
                neighbor.rumor_signals.append(arch.faction)
```

### Stage 5: Bayesian belief update (spec stage 2)

Unchanged. Each actor's otherAwareness updates on evidence.

```python
def update_beliefs(arch, tick):
    evidence = arch.rumor_signals
    if unfamiliar_trade_goods(evidence):
        arch.otherAwareness += 0.05
    if consistent_multi_source(evidence):
        arch.otherAwareness += 0.10
    if unknown_vessels(evidence):
        arch.otherAwareness += 0.25
    if nuclear_intercept(evidence):
        arch.otherAwareness = 1.0  # Dark Forest break
```

### Stage 6: IR posture selection (spec stage 3)

Unchanged table, but "capability" is now energy-derived.

```python
def select_posture(faction, tick):
    capability = categorize(faction.surplus)  # HIGH/MED/LOW from energy
    threat = faction.max_otherAwareness       # from belief update

    # Mearsheimer / Walt / Schweller lookup
    posture_table = {
        ("HIGH", "HIGH"): "explore",    # offensive realism
        ("HIGH", "LOW"):  "project",    # liberal hegemony
        ("MED",  "HIGH"): "fortify",    # defensive realism
        ("MED",  "LOW"):  "hedge",
        ("LOW",  "HIGH"): "align",      # bandwagoning
        ("LOW",  "LOW"):  "free_ride",
    }
    faction.current_posture = posture_table[(capability, threat)]
```

### Stage 7: Expansion — Thompson Sampling + garrison (spec stages 5, 6)

Expedition funding gated by expansion_budget. Cultural priors (Beta shapes) unchanged. Resource targeting replaces era-specific garrison tables.

```python
def expand(faction, tick):
    budget_remaining = faction.expansion_budget

    # Rank candidate targets by Thompson Sampling score + resource value
    candidates = []
    for edge in faction.frontier_edges:
        target = edge.target_arch

        # Thompson Sampling: cultural exploration prior
        ts_score = beta_sample(faction.alpha_prior, faction.beta_prior)

        # Resource value: era-appropriate
        rv = resource_value(target, faction.tech)

        # Denial value: worth more if opponent is closer to it
        dv = denial_value(target, faction, opponent)

        # Projection cost: energy cost of reaching and holding
        cost = transport_cost_per_rad * gc_dist(faction.core, target)

        score = (ts_score + resource_targeting_weight * rv + dv) / cost
        candidates.append((target, score, cost))

    # Fund expeditions in score order until budget exhausted
    for target, score, cost in sorted(candidates, key=lambda x: -x[1]):
        if budget_remaining < cost:
            break
        success = resolve_expedition(faction, target, tick)
        budget_remaining -= cost
        if success:
            absorb(faction, target, tick)


def resource_value(arch, tech):
    """Era-appropriate resource valuation. No hardcoded era table —
    value emerges from tech-gated unlock thresholds."""
    value = 0.0
    if tech >= cu_unlock_tech:
        value += arch.minerals.Cu * 1.0
    if tech >= 4.0:
        value += arch.minerals.Au * 2.0
    if tech >= 7.0:
        value += arch.C_remaining * 3.0   # naphtha is king
    if tech >= 9.0:
        value += arch.minerals.Pu * 10.0  # pyra is existential
    return value
```

### Stage 8: Tech growth (currently embedded in era tables, now from budget)

Tech grows from the tech_budget portion of surplus, modulated by knowledge compounding (A₀) and energy availability.

```python
def grow_tech(faction, tick):
    # Base growth from tech investment
    base = faction.tech_budget / faction.total_pop  # per-capita research investment

    # Knowledge compounding: A0 × log2(trade contacts)
    compound = faction.A0 * log2(1 + faction.trade_contacts)

    # Energy multiplier: can't innovate without energy
    energy_mult = faction.energy_ratio

    # Resource unlock bonus: Cu slightly accelerates serial tech,
    # but this is small compared to energy coupling
    cu_bonus = 0.0
    if faction.tech < 5.0 and faction.controls_Cu:
        cu_bonus = cu_tech_bonus

    delta_tech = (base * compound * energy_mult) + cu_bonus
    faction.tech = min(faction.tech + delta_tech, 10.0)
```

### Stage 9: Sovereignty drift (spec stage 7)

Energy-gated continuous dynamics on the sovereignty × tradeIntegration plane.

```python
def sovereignty_drift(arch, tick):
    if arch.status == "core":
        return  # cores don't drift

    controller = arch.controlling_faction

    # Extraction pressure: how hard is the core squeezing?
    extraction = controller.extraction_rate * (1.0 / gc_dist(controller.core, arch))

    # Resistance: sovereignty wants to recover
    recovery = sov_extraction_decay * arch.sovereignty * arch.population

    # Energy gate: extraction can't exceed controller's surplus
    max_extraction = controller.surplus * extraction_fraction
    effective_extraction = min(extraction, max_extraction)

    # Drift
    if effective_extraction > recovery:
        arch.sovereignty -= (effective_extraction - recovery) * dt
    else:
        arch.sovereignty += (recovery - effective_extraction) * dt

    arch.sovereignty = clamp(arch.sovereignty, 0.0, 1.0)

    # Naphtha depletion at extraction site
    if arch.C_remaining > 0 and controller.tech >= 7:
        extracted = naphtha_depletion * arch.population * controller.tech
        arch.C_remaining = max(0, arch.C_remaining - extracted)
```

### Stage 10: Epidemic shock (on first contact only)

Unchanged from current model. Biological, not economic. Energy surplus affects recovery rate.

```python
def epidemic_check(arch, contacting_faction, tick):
    if arch.previously_contacted:
        severity *= 0.3  # trade-chain pre-exposure
    else:
        severity = epi_base_severity + rng() * 0.25
        severity *= crop_distance(arch.crop, contacting_faction.primary_crop)

    arch.population *= (1.0 - severity)

    # Recovery rate proportional to controlling faction's energy surplus
    arch.recovery_rate = base_recovery * (1.0 + contacting_faction.energy_ratio * 0.5)
```

---

## Loss Function (simplified)

The energy rewrite lets us collapse 28 loss terms into ~12, because many intermediate behaviors (colonial extraction signature, sovereignty ordering, maritime asymmetry) should emerge from energy dynamics rather than being checked independently.

### Structural preconditions (check geography — same as before)

| Term | What it checks |
|------|---------------|
| `latitude_separation` | Reach mid-latitude, Lattice tropical |
| `civ_gap` | Min cross-faction distance > threshold |
| `density_asymmetry` | Lattice denser than Reach |

### Energy outcomes (new)

| Term | What it checks |
|------|---------------|
| `naphtha_peak` | At least one hegemon exhausts >50% C before nuclear era |
| `energy_transition` | Total world C >70% depleted at story present |
| `pu_acquisition` | Both hegemons control ≥1 Pu island by story present, acquired during industrial+ eras |

### Civilizational outcomes (streamlined)

| Term | What it checks |
|------|---------------|
| `nuclear_fleets` | Both hegemons at tech ≥9.0 with nuclear fleet capability at story present |
| `fleet_asymmetry` | Pu-rich hegemon has larger fleet_scale |
| `sovereignty_gradient` | Colonies have lower sovereignty than core; post-colonial recovery visible |
| `discovery_curve` | Contact count roughly follows Σ2ⁿ doubling (emergent, not enforced) |
| `dark_forest_timing` | DF break occurs in nuclear era (−200 to −40 BP), not earlier |
| `el_dorados` | ≥10 archipelagos uncontacted at story present |

### Diagnostic (not penalized, just tracked)

| Term | What it tracks |
|------|---------------|
| `tech_gap_at_contact` | Max tech differential when industrial hegemon absorbs pre-industrial independent |
| `scramble_onset` | Tick at which resource-weighted expansion first targets C-rich islands |
| `pu_scramble_onset` | Tick at which Pu-weighted expansion begins |
| `naphtha_exhaustion_tick` | When the first hegemon's C reserves drop below critical |

---

## Implementation Sequence

### Phase 1: Python sim_proxy (optimizer target)

Build the energy-coupled sim in `sim_proxy.py` first. This is what the optimizer runs against — it must be fast (< 10ms per seed) and pure Python (no external deps).

**Steps:**
1. Add C generation to substrate (shelf_r × tidal_range × naphtha_richness)
2. Implement Layer 1: resource accounting + energy surplus per tick
3. Implement Layer 2: political allocation (3 shares per faction)
4. Rewire tech growth to depend on tech_budget × energy_ratio × A₀
5. Rewire garrison targeting to use resource_value() instead of era tables
6. Add C depletion per tick
7. Add Pu independence/dependency logic for nuclear era
8. Add fleet_scale output

**Verification:** Run on seed 216089 with hand-tuned params. Check that:
- Reach industrializes before Lattice (spread geography → more Au contacts → faster knowledge)
- Naphtha scramble happens when Reach hits tech ~7
- Both hegemons achieve nuclear fleets by story present
- ≥10 archs remain uncontacted

### Phase 2: Loss function

Rewrite `loss.py` with the 12-term structure above. Drop the 16 terms that should now be emergent (colonial_extraction, maritime_asymmetry, sov_ordering, sov_recovery, etc.). Add the energy-specific terms (naphtha_peak, energy_transition, pu_acquisition).

**Verification:** Run loss on seed 216089 with hand-tuned params. Total loss should be interpretable — each term should be traceable to a specific geographic or energetic cause.

### Phase 3: Optimizer run

Update `run_optimization.py` with the 19-parameter bounds. Run 10,000 trials on seed 216089 + top 5 candidates from the million-seed search.

**Expected improvement over current model:**
- Fewer parameters → faster convergence (TPE explores 19-dim space more efficiently than 33-dim)
- No structural conflicts → lower loss floor (the Pu gate vs tech convergence problem is dissolved)
- Energy-coupled garrison targeting → colonial extraction and sovereignty dynamics emerge from the same parameters that drive expansion, instead of being tuned independently

### Phase 4: GDScript port

Once the optimizer validates the design, port the energy-coupled sim from `sim_proxy.py` to `history_engine.gd`. This is mechanical translation — the sim_proxy is the ground truth.

### Phase 5: GUI integration

- Add C depletion visualization (resource bar per arch that drains over time)
- Add fleet_scale to the political map display
- Show resource-motivated expansion edges in a different color than proximity-based ones
- Naphtha seep markers on the globe at shelf positions

---

## What Dies

These current parameters are removed, not replaced 1:1. Their effects emerge from energy economics.

| Dead parameter | What replaces it |
|---------------|-----------------|
| `antiquity_base_growth` | Surplus-driven growth at low energy demand |
| `antiquity_lattice_pop_mult` | Lattice higher consolidation_share → more population retention |
| `serial_shock_base_min/range` | Epidemics unchanged, but severity recovery now energy-gated |
| `serial_trade_rate` | Trade follows Thompson Sampling + expansion budget |
| `reach_serial_base_mult` | reach_expansion_share + reach_tech_share |
| `reach_serial_log_coeff` | A0_reach (knowledge compounding) |
| `lattice_serial_base_mult` | lattice_expansion_share + lattice_consolidation_share |
| `lattice_serial_log_coeff` | A0_lattice |
| `extraction_base` | Sovereignty drift from energy extraction pressure |
| `extraction_per_year` | naphtha_depletion |
| `garrison_absorb_base` | expansion_budget / transport_cost |
| `reach_colony_surplus` | reach_expansion_share |
| `lattice_garrison_bonus` | lattice_consolidation_share |
| `lattice_trib_bonus` | Emerges from Lattice's high consolidation spending |
| `reach_ind_tech_mult/pot/log` | reach_tech_share × energy_ratio × A0_reach |
| `lattice_ind_tech_mult/pot/log` | lattice_tech_share × energy_ratio × A0_lattice |
| `tech_floor_reach_ind` | No floors — tech grows from budget, energy gates the rate |
| `tech_floor_lattice_ind` | Same |
| `reach_nuclear_pop_mult` | Nuclear energy surplus → population boom (emergent) |
| `lattice_nuclear_pop_mult` | Same |
| `nuclear_access_*` | pu_dependent_factor |
| `cu_serial_year_bonus` | cu_unlock_tech (when Cu matters, not how much bonus) |
| `pu_nuclear_tech_fraction` | pu_dependent_factor (dependency, not gate) |

---

## Risk Assessment

**What could go wrong:**

1. **Energy model too abstract to produce specific historical textures.** The crop-to-civilization mapping, stimulant trade, textile economies — these aren't energy phenomena. Mitigation: Layer 3 preserves all social/cultural texture. Energy determines the envelope; culture determines the content.

2. **Solow-Romer production function too sensitive to parameter choice.** The α=0.3 capital share and (1-α)=0.7 labor share are Earth-calibrated. On Aeolia with different demographics and energy availability, these might produce wrong dynamics. Mitigation: α could be a tunable param if needed (20 params instead of 19), but try fixed first.

3. **C depletion timeline hard to calibrate.** If naphtha runs out too fast, nobody industrializes. Too slow, no nuclear forcing function. Mitigation: `naphtha_richness` and `naphtha_depletion` are both tunable — the optimizer can find the balance.

4. **Loss of prescriptive control over era timing.** The current model guarantees the Dark Forest break happens in the nuclear era via direct parameter control. The energy model only guarantees it if the energy curve produces the right tech trajectory. Mitigation: `df_detection_range` still provides direct control over when detection becomes possible. If the curve is wrong, the df_timing loss term catches it.

5. **The Σ2ⁿ curve might not emerge.** On Earth, the doubling pattern reflects exponential growth in maritime technology + economic surplus. If the energy model produces a different contact curve, the lore requirement fails. Mitigation: track the curve as a diagnostic. If it doesn't emerge naturally, investigate whether energy parameters or A₀ values need adjustment before reimposing redistribution as a fallback.
