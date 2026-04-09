# Disease Mechanic — Design Document

**Status:** Proposal. Not yet implemented.
**Target file:** sim_proxy_v2.py
**Lanthier targets:** Malaria belts, epidemic waves, urban disease sink.

---

## 1. Design Goals

Disease should:
1. **Slow equatorial colonization** — malaria-analog zones gate expansion into tropical archipelagos until medical tech unlocks
2. **Create periodic population shocks** — epidemic waves that disrupt growth trajectories and trigger desperation cascades
3. **Tax urbanization** — dense polities face higher baseline mortality, creating a drag that balances their economic advantages
4. **Spread via trade** — connected polities share disease risk, creating a cost to the trade network that currently has none

Disease should NOT:
- Require its own parameter space explosion (≤3 new SimParams)
- Break existing optimizer convergence (introduce gradually, test on known-good seeds)
- Dominate the simulation — disease is a modifier, not the primary driver

---

## 2. Three Components

### 2a. Malaria Belts (latitude-gated endemic disease)

**Concept:** Archipelagos near the equator have a permanent disease penalty that reduces effective carrying capacity. This gates expansion into the tropics until medical tech (tech ≥ 6) provides partial resistance.

**Implementation:**

```python
# In tick loop, after carry_cap computation:
abs_lat = abs(archs[j][0])  # latitude in radians
if abs_lat < 0.35:  # ~20° from equator
    malaria_severity = (0.35 - abs_lat) / 0.35  # 1.0 at equator, 0 at boundary
    if tech[controller[j]] < 6.0:
        cap *= (1.0 - malaria_severity * p.malaria_cap_penalty)
    else:
        # Medical knowledge reduces but doesn't eliminate the penalty
        cap *= (1.0 - malaria_severity * p.malaria_cap_penalty * 0.3)
```

**New parameter:** `malaria_cap_penalty: float = 0.40` (range 0.2–0.6)
- At equator, pre-medical: 40% carrying capacity reduction
- At equator, post-medical (tech ≥ 6): 12% reduction
- At 10° latitude: ~57% of full penalty

**Historical analog:** European colonial mortality in West Africa vs. temperate colonies. Quinine (≈tech 6–7 era) halved but didn't eliminate tropical disease burden.

### 2b. Epidemic Waves (stochastic population shocks)

**Concept:** Periodic disease events that kill a fraction of population in affected archipelagos. Probability scales with trade connectivity (more contacts = more disease vectors) and population density. Epidemics propagate along trade routes.

**Implementation:**

```python
# New stage, runs every tick after population growth:
# 1. Roll for epidemic origin
for core in cores:
    nc = len(contact_set[core])
    density = core_pop[core] / max(1.0, sum(carry_cap[j] for j in range(N) if controller[j] == core))
    
    # Probability per tick: base × contacts × density
    # ~5% per tick at moderate connectivity, ~15% for trade hubs
    epi_prob = p.epi_base_severity * 0.1 * (1.0 + nc * 0.3) * density
    
    if rng.next_float() < epi_prob:
        # Epidemic strikes this polity
        mortality = 0.05 + rng.next_float() * 0.15  # 5–20% population loss
        
        # Spread to trade partners with probability ∝ trade volume
        affected = {core}
        for other in contact_set[core]:
            if rng.next_float() < 0.4:
                affected.add(other)
        
        for c in affected:
            for j in range(N):
                if controller[j] == c:
                    pop[j] *= (1.0 - mortality)
                    pop[j] = max(1.0, pop[j])
```

**No new parameters** — reuses existing `epi_base_severity` (currently controls contact dynamics). The 0.1 scaling factor and 0.4 spread probability are internal constants, tunable later if needed.

**Interaction with desperation:** Population crash → energy surplus drops → maintenance exceeds surplus → tech decay. This is already handled by the existing desperation mechanic. Disease just provides a new trigger.

### 2c. Urban Disease Sink (density-dependent mortality)

**Concept:** High-population archipelagos have elevated baseline mortality. Cities historically were population sinks — they required constant rural immigration to maintain numbers. This creates a drag on the largest polities.

**Implementation:**

```python
# In population growth section (after line ~1106):
# Density-dependent mortality penalty
density_ratio = pop[j] / max(1.0, cap)
if density_ratio > 0.7:
    # Overcrowded: disease mortality increases
    urban_penalty = (density_ratio - 0.7) * p.urban_disease_rate
    growth_rate -= urban_penalty
```

**New parameter:** `urban_disease_rate: float = 0.08` (range 0.03–0.15)
- At 100% capacity: 0.3 × 0.08 = 2.4% extra mortality per tick
- At 70% capacity: no penalty
- Effectively caps sustainable population below theoretical carrying capacity

---

## 3. Parameter Summary

| Parameter | Default | Range | Component |
|-----------|---------|-------|-----------|
| `malaria_cap_penalty` | 0.40 | 0.20–0.60 | Malaria belts |
| `urban_disease_rate` | 0.08 | 0.03–0.15 | Urban disease sink |
| (reuses `epi_base_severity`) | 0.30 | 0.15–0.50 | Epidemic waves |

Two new parameters. Total SimParams: 28 (currently 26 after DF fix).

---

## 4. Tick Pipeline Placement

Current pipeline:
1. Trade pre-pass
2. Stage 1: Energy budget
3. Stage 2: Culture & allocation
4. Stage 3: Expansion
5. Stage 4: Detection & awareness (DF)
6. Stage 5: Tech growth & population growth
7. Stage 6: Desperation

Proposed insertion:
- **Malaria belts:** Modify `carry_cap` at initialization (before tick loop) and adjust per-tick when tech changes. Lightweight — just a multiplier on existing array.
- **Epidemic waves:** New Stage 5b, after population growth, before desperation check. This ensures population loss feeds into the desperation calculation on the same tick.
- **Urban disease sink:** Inline in existing population growth code (Stage 5, line ~1106). Just an additional term in `growth_rate`.

---

## 5. Interaction Matrix

| Mechanic | Disease interacts via... |
|----------|------------------------|
| Trade network | Epidemic spread probability scales with contacts |
| Desperation | Population crash triggers tech decay cascade |
| Malthusian clamp | Malaria reduces effective carrying capacity |
| Culture drift | Population crisis → Collective drift (existing) |
| Expansion | Tropical archipelagos less attractive until med-tech |
| Tech growth | Large pop loss → reduced total productivity |

---

## 6. Implementation Order

1. **Urban disease sink first** — smallest change, inline in existing code, easy to validate
2. **Malaria belts second** — modify carry_cap array, check latitude distribution in world files
3. **Epidemic waves last** — most complex, needs RNG integration, trade-route propagation

Each can be committed and optimizer-tested independently.

---

## 7. Open Questions

- **Q1:** Should epidemic immunity accumulate? Historically, populations develop partial resistance. This adds state but increases realism.
- **Q2:** Should malaria affect expansion cost (not just carrying capacity)? Conquistador mortality was about campaign logistics, not just settlement viability.
- **Q3:** Should disease interact with the religion mechanic (when implemented)? Plagues historically triggered religious revivals and reform movements.

These are deferred — implement the base mechanic first, iterate based on optimizer results.
