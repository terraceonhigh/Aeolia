# Open Questions: Remaining Prescriptions in the Simulator

These are assumptions currently hardcoded into sim_proxy_v2.py or the V2 plan that constrain outcomes rather than letting them emerge. Each question should be resolved before or during implementation to determine whether the prescription should be kept (with justification), softened (add variance), or removed.

---

## Q1. Crop → Culture Determinism

**Current behavior:** Crop type deterministically assigns political culture. emmer → Civic, paddi → Subject, taro/sago/papa → Parochial, nori → Civic hybrid.

**The problem:** This is Wittfogel's hydraulic hypothesis encoded as a lookup table. It says "if you grow rice, you develop authoritarian institutions." Scott's *Against the Grain* and *The Art of Not Being Governed* argue that the same crop can produce radically different political cultures depending on geography, population density, and state-evading strategies. A rice-growing archipelago polity faces very different institutional pressures than a rice-growing river valley empire.

**The question:** Should crop → culture be a deterministic mapping, a weighted probability distribution, or a tendency with additional geographic inputs (island size, neighbor count, trade connectivity)?

**Stakes:** If deterministic, the optimizer can only find worlds where rice-growers are always authoritarian. If probabilistic, the same seed can produce different cultural outcomes on different runs, which changes what "optimizing a seed" means.

---

## Q2. Static Allocation Shares

**Current behavior:** A Civic polity always allocates high expansion, high tech, low consolidation. The shares are fixed by culture type for the entire simulation.

**The problem:** Real civilizations oscillate. Ming China was Civic-expansionist under Yongle (Zheng He voyages) and Subject-isolationist under his successors, with the same crop base throughout. The Roman Republic was expansionist; the late Empire was consolidationist. Political culture sets a tendency, but internal dynamics (succession crises, military defeats, resource windfalls) cause regimes to deviate from type.

**The question:** Should allocation shares drift stochastically over time, with culture type as an attractor rather than a fixed point? If so, what drives the drift — random shocks, military outcomes, resource changes, or all three?

**Stakes:** Static shares mean the optimizer finds a single "personality" per culture type that works across all ticks. Drifting shares mean polities can surprise themselves and each other, producing richer emergent narratives but harder optimization (stochastic outcomes per seed).

---

## Q3. Monotonic Tech Progress

**Current behavior:** Tech never decreases. The soft cap slows growth above 9.0, but a polity at tech 8 will never fall back to tech 7.

**The problem:** Civilizations regress. The Roman withdrawal from Britain. The Late Bronze Age Collapse. The Khmer Empire's abandonment of Angkor. The Maya Classic period collapse. On Aeolia, a polity that loses its naphtha supply at tech 8 should experience tech decay as its industrial base contracts. A polity that loses population to epidemic after first contact should lose the labor force that sustains its tech level.

**The question:** Should tech have a maintenance cost — a minimum energy surplus or population threshold below which tech decays? If so, how fast? And can a polity that collapses from tech 8 to tech 5 re-industrialize, or is the resource base (depleted naphtha) gone?

**Stakes:** Without regression, the simulation can't produce collapse events — one of the most studied phenomena in historical social science. With regression, the optimizer must find parameters robust to collapse risk, and the loss function library gains access to scenarios like Total Collapse and Resource Curse that currently can't fully express themselves.

---

## Q4. Fixed Resource Unlock Sequence

**Current behavior:** Fe always available → Cu at tech ~3 → Au at tech ~4 → C at tech ~7 → Pu at tech ~9. This is hardcoded and identical for all polities regardless of geography.

**The problem:** This is Earth's sequence. A civilization on a volcanic island with surface naphtha seeps could plausibly discover hydrocarbons before copper metallurgy — they literally step in the stuff. A civilization on an island with no copper ore but abundant gold alluvial deposits might work gold before copper (as happened in parts of pre-Columbian South America). The unlock sequence assumes a Eurasian continental development path.

**The question:** Should unlock thresholds be geography-dependent? For example: if an arch has high naphtha_richness and surface geology, lower the C unlock tech. If an arch has gold but no copper, swap the Cu/Au order. Or should the sequence remain fixed as a simplifying assumption?

**Stakes:** Fixed sequence is simpler to optimize and produces more predictable outcomes. Geography-dependent unlocks produce more diverse civilizational paths but add complexity and may require per-arch parameter tuning.

**RESOLVED 2026-04-07:** Three-threshold model. Resources progress through three decoupled stages:

1. **Detection** — geology-dependent, can happen at any tech level. A polity can observe bitumen seeps, surface pyra outcrops, or alluvial gold without the technology to exploit them. Sacred/cultural associations form at Detection: Baku's eternal flames from natural gas seeps, Mesopotamian bitumen used for waterproofing, salt licks becoming ritual sites. These associations are permanent — they persist as cultural texture even after industrial exploitation begins (*sacralization preservation*: early cultural encodings of a resource site leave traces in the simulation's cultural layer regardless of later exploitation state).

2. **Exploitation** — fixed tech sequence: naphtha ~5, pyra ~8. Tech-gated, not geology-gated. A polity sitting on surface naphtha can know about it for millennia before they can refine it. Detection and Exploitation are deliberately decoupled to allow exactly this gap.

3. **Strategic Valuation** — triggered by discovery events, not tech level. The fission discovery event (§2 of this document) makes pyra strategically critical regardless of whether a polity has previously detected or exploited it. A polity with zero pyra deposits suddenly needs to acquire them. A polity that has been mining pyra for industrial uses (catalysis, specialty alloys) undergoes a revaluation of existing holdings overnight.

The unlock sequence is not abolished — it describes Exploitation thresholds only. Detection is always geography-dependent. Strategic Valuation is always event-triggered. The three stages can be separated by hundreds of ticks on the same island.

---

## Q5. Neoclassical Production Function

**Current behavior:** Y = A × K^0.3 × L^0.7 (Solow-Romer). Diminishing returns to capital, constant returns to scale, labor-dominant.

**The problem:** This is a reasonable model for industrial economies but a poor fit for pre-agricultural maritime-trade economies (where returns to scale are increasing due to network effects of trade routes) or subsistence economies (where capital is negligible and output is roughly linear in labor). A Parochial fishing chieftaincy and a Civic industrial empire use the same production function with the same exponents.

**The question:** Should the production function exponents vary by tech level (pre-industrial vs. industrial vs. nuclear) or by culture type (trade-oriented vs. labor-intensive vs. capital-intensive)? Or is the Solow-Romer model "good enough" as a simplifying assumption given that the production function is an intermediate calculation, not a direct output?

**Stakes:** Variable exponents would make the model more theoretically defensible but add parameters and complexity. Fixed exponents are standard in the computational social science literature and defensible as a simplification. The question is whether the production function's inaccuracy at low tech levels materially affects the simulation's high-tech-level outcomes that the loss function actually cares about.

**RESOLVED 2026-04-07:** Keep Y = A × K^0.3 × E^0.7 unchanged across all tech levels. (Note: the active formula uses energy E, not labor L — this is the energy-budget formulation from §11/12.)

Do **not** add a population exponent to the tech-growth accelerator. Population already enters indirectly via energy surplus → budget → expansion. Adding it explicitly double-counts and breaks competitive balance: sweep results (exponent_sweep_results.md) showed that pop^0.5 causes runaway expansion, suppresses Dark Forest, and fires the naphtha scramble in the Mesolithic. Three-regime variable exponents scored nominally 37% better on mean loss but achieved this by breaking DF timing and scramble timing — the improvement is an artifact of the loss function, not better dynamics. Interpolated exponents were only 8% better than baseline, insufficient to justify the added complexity and instability.

The existing `accel_rate` table (0 / 0.002 / 0.008 / 0.025 / 0.120) already encodes five implicit growth regimes. The production function does not need to know what era it is in. Energy composition changes (food → food+naphtha → food+naphtha+nuclear) naturally produce regime transitions through the energy budget.

**One justified addition:** a Malthusian carrying-capacity clamp applied to energy surplus in the **energy layer** (not the production function) for tech < 4. When population approaches carrying capacity, food surplus shrinks — producing the Malthusian trap without requiring regime boundaries in the production function or the tech-growth accelerator. The clamp belongs in the food energy calculation, not in Y.

---

## Q6. Two-Hegemon Prescription

**Current behavior:** The Baseline Earth loss function rewards exactly two hegemons at DF break. The simulator is faction-agnostic, but the optimizer converges on bipolarity because that's what the loss function demands.

**The problem:** This is a narrative choice (Aeolia parallels US-China bipolarity), not an emergent result. A world where three or four roughly equal powers maintain a multipolar equilibrium gets penalized. The simulator *can* produce multipolarity — the loss function won't let it.

**The question:** Is this intentional and should remain as-is for Baseline Earth? (Almost certainly yes.) Is it sufficiently clear in the documentation that bipolarity is prescribed, not emergent? Do the alternative loss functions (especially Multipolar) properly remove this constraint?

**Stakes:** Low for implementation — this is already handled correctly by the faction-agnostic design. The risk is presentational: if bipolarity is presented as an emergent result of the model rather than an optimization target, the academic credibility of the project suffers.

**RESOLVED 2026-04-09:** Prescription is explicit and intentional. Baseline Earth loss function bipolarity target is documented in loss_v2.py comments and in README. "Even underspecified models get read as prescriptive" (Lanthier) — the game framing handles this: the player is told they are optimizing for a specific Baseline Earth scenario, not discovering a universal law. The multipolar loss function is available as an explicit alternative. No code change needed; documentation is sufficient. Added clarifying comment to loss_v2.py.

---

## Q7. Dark Forest as Terminal Event

**Current behavior:** The simulation effectively ends at or shortly after DF break. Post-DF dynamics (deterrence, arms control, proxy warfare, normalization, potential nuclear war) are not modeled.

**The problem:** The post-DF world is where most of the interesting political science lives. Deterrence theory (Schelling), arms control (Waltz's stability-instability paradox), proxy warfare (Westad), eventual normalization (détente). The simulation generates the conditions for these dynamics and then stops.

**The question:** Should the simulation continue for N ticks after DF break, modeling post-DF dynamics? If so, what mechanics change after DF? (Deterrence freezes expansion, arms race accelerates tech in narrow band, proxy competition through client states, potential for nuclear exchange as a terminal catastrophic event.) Or is post-DF modeling a separate project that takes DF-break state as initial conditions?

**Stakes:** Extending past DF adds significant mechanical complexity (deterrence logic, proxy mechanics, nuclear war probability) but opens up the most policy-relevant research questions. Keeping DF as terminal is simpler and sufficient for the Vanilla Aeolia narrative (which begins at DF break). This may be best addressed as a future phase.

**RESOLVED 2026-04-09 (minimal implementation in SimEngine.js and sim_proxy_v2.py):**

Two post-DF mechanics implemented, sufficient for demo and Observatory visualization:

1. **Deterrence freeze (Stage 6):** After DF fires, any polity with tech ≥ 9.0 receives a strong negative targeting penalty (-12.0) when targeting territory controlled by another nuclear-capable polity (also tech ≥ 9.0). This applies to ALL nuclear pairs, not just the specific DF trigger pair — once the first nuclear detection occurs, the mutual-annihilation constraint is universally understood. Non-nuclear polities and non-nuclear territory continue to be contested normally. The territorial stasis between nuclear powers is visible in Observatory charts as parallel flatlines in the late period.

2. **Arms race bonus (Stage 5):** After DF fires, all polities with tech > 8.5 receive an extra tech growth bonus (up to 40% of delta, capped at 0.05). Models diversion of budget toward nuclear delivery systems, deterrence infrastructure, and second-strike capability. Visible in Observatory tech chart as continued divergence between nuclear and non-nuclear polities after territorial stasis.

3. **Nuclear peer awareness (Stage 3):** The DF detection mechanism itself was overhauled (2026-04-09). Once two polities both reach tech ≥ 9.0, mutual awareness accumulates globally (0.04/tick per side) independent of geographic distance — representing weapons-test seismology, satellite surveillance, and signals intelligence. DF fires when awareness exceeds 0.30. This produces naturally timed detection (~7–8 ticks = 350–400 years after both go nuclear) and removes the unphysical requirement for geographic proximity.

Full post-DF proxy mechanics (client state competition, nuclear exchange probability, eventual normalization) are deferred to a future phase. This implementation gives the Observatory a visually coherent "Cold War phase" distinct from the expansion phase.

---

## Resolution Tracking

| Question | Status | Resolution | Date |
|----------|--------|------------|------|
| Q1. Crop → Culture | Resolved | Replaced with continuous Collective↔Individual / Inward↔Outward space. Culture is a position, not a type. | 2026-04-06 |
| Q2. Static Allocation | Resolved | Dissolved by continuous culture space — allocation shares are continuous functions of position that drift every tick. | 2026-04-06 |
| Q3. Monotonic Tech | Resolved | Tech maintenance cost + desperation mechanic. Layered energy balance (food → industrial → nuclear). Resource pressure overrides culture-based allocation. Collapse cascades and recovery mechanics. | 2026-04-06 |
| Q4. Resource Unlock | Resolved | Three-threshold model: Detection (geology-dependent, any tech) → Exploitation (fixed tech: naphtha ~5, pyra ~8) → Strategic Valuation (event-triggered). Sacralization preservation: early cultural associations persist after industrial exploitation. | 2026-04-07 |
| Q5. Production Function | Resolved | Keep Y = A × K^0.3 × E^0.7 unchanged. No population exponent — double-counts and breaks DF/scramble timing (sweep: pop^0.5 fires naphtha scramble in Mesolithic). `accel_rate` table encodes growth regimes implicitly. Malthusian clamp added to food energy layer (not production function) for tech < 4. | 2026-04-07 |
| Q6. Two-Hegemon | Resolved | Prescribed bipolarity is explicit in loss_v2.py and README; game framing + multipolar alternative handle the presentational risk. | 2026-04-09 |
| Q7. Post-DF Dynamics | Resolved (minimal) | Nuclear peer awareness (global, distance-independent, 0.04/tick) triggers DF at ~7–8 ticks after both go nuclear. Deterrence freeze (-12 targeting penalty between ALL nuclear pairs). Arms race bonus (40% of delta, capped) for all nuclear polities. Full proxy mechanics deferred. | 2026-04-09 |
