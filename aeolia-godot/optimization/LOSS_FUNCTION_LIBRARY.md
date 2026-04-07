# Loss Function Library — Research Experiments

> Each loss function uses the same faction-agnostic simulator and 21 parameters.
> Each one asks a different question about civilizational development.
> Only the Baseline Earth loss function references the Reach and Lattice by name.
> All others operate on emergent polities identified by political culture type (Civic, Subject, Parochial), geography, and resource control — not by narrative label.
> Build these after Phase 3 (optimizer validates Baseline Earth).

---

## Baseline Earth (default)

**Question:** What parameter configuration produces a world recognizably analogous to the US-China dynamic — nuclear-era hegemons, colonial history, Dark Forest break?

**Purpose:** Calibration. If the model can reproduce something Earth-like, the mechanics are working. This is the narrative loss function for Aeolia's lore.

**Key terms:** latitude separation, nuclear fleets, energy transition, discovery curve, Dark Forest timing, el Dorados. This is the only loss function that names "Reach" (Civic hegemon) and "Lattice" (Subject hegemon).

---

## Symmetric Hegemon

**Question:** Can both civilizations develop identically despite different geographies?

**What it tests:** Whether political culture can override material conditions. If the optimizer finds symmetry on asymmetric geography, culture dominates. If it can't, geography is destiny.

**Penalizes:** Any asymmetry in tech, population, sovereignty, fleet_scale, or territorial extent at story present.

**Social science relevance:** Directly tests geographic determinism (Diamond) against institutionalism (Acemoglu & Robinson). A positive result would challenge the entire structural school of comparative politics.

---

## No Dark Forest

**Question:** Under what conditions do two civilizations discover each other in the serial era and coexist peacefully for millennia?

**What it tests:** Liberal internationalism vs. realism. Does mutual awareness in a pre-industrial era produce cooperation, trade equilibrium, and institutional integration — or does the security dilemma inevitably escalate?

**Rewards:** Early contact (serial era), stable trade equilibrium, absence of conflict escalation, joint technological development.

**Penalizes:** Arms races, garrison expansion toward the other hegemon, fleet buildup post-contact.

**Social science relevance:** Tests Kant's democratic peace theory and Keohane's institutional liberalism against Mearsheimer's offensive realism. If peaceful coexistence is achievable under any parameter set, liberal internationalism has structural support. If not, realism wins as a universal dynamic.

---

## Reversed Polarity

**Question:** Can the dense-cluster civilization become the maritime explorer and the dispersed one become the consolidator?

**What it tests:** Whether the crop-to-civilization mapping (paddi → hydraulic → bureaucratic; emmer → dryland → competitive) is deterministic or contingent.

**Rewards:** Subject-culture polity's maritime contact count exceeding Civic-culture polity's. A Subject polity with higher expansion_share than consolidation_share. A Civic polity that consolidates rather than projects.

**Penalizes:** Conformity to default Civic=maritime / Subject=bureaucratic pattern.

**Social science relevance:** Directly tests Wittfogel's hydraulic hypothesis. If the optimizer can produce a maritime hydraulic state, collective agriculture doesn't necessitate centralized authoritarianism — it merely correlates with it on Earth. A negative result (can't reverse) strengthens Wittfogel.

---

## Resource Curse

**Question:** Under what conditions does the naphtha-rich hegemon stagnate while the naphtha-poor one industrializes first?

**What it tests:** Whether the paradox of plenty (Dutch Disease, resource curse) is a structural mechanism or an institutional accident.

**Rewards:** High C access correlating with low tech at story present. Naphtha-poor hegemon reaching industrial+ tech before naphtha-rich one.

**Penalizes:** Standard outcome where more resources = faster development.

**Social science relevance:** Tests Sachs & Warner's resource curse hypothesis, Ross's oil curse thesis, and Auty's resource trap. If the energy model can produce Dutch Disease without prescribing it (just by allowing early surplus to suppress tech_share allocation), the mechanism is structural and general.

---

## Multipolar

**Question:** Under what conditions do 4+ peer powers coexist at story present instead of consolidating into 2 hegemons?

**What it tests:** Whether bipolarity is a structural attractor (Waltz's neorealism predicts it) or contingent on Earth's specific geography.

**Rewards:** Multiple independent factions at tech ≥7, no single faction controlling >30% of archs. Power distributed across 4+ actors.

**Penalizes:** Bipolar convergence, any hegemon absorbing >25% of total population.

**Social science relevance:** Tests Waltz's structural realism (bipolarity as equilibrium) against constructivist accounts of multipolar stability. If the optimizer can't find stable multipolarity, Waltz is vindicated — the system structurally selects for two poles. If it can, the historical prevalence of bipolarity is contingent, not necessary.

---

## Total Collapse

**Question:** Under what conditions does naphtha depletion cause industrial collapse before the nuclear transition?

**What it tests:** Civilizational resilience to energy transitions. The existential risk question — not "can we go nuclear?" but "what conditions make us fail?"

**Rewards:** Peak-and-decline tech curves. Both hegemons reaching industrial era then regressing. Naphtha exhausted, nuclear not achieved.

**Penalizes:** Successful nuclear transition. Tech ≥9 at story present.

**Social science relevance:** Tests Tainter's collapse theory (complexity requires energy; energy decline → complexity collapse) and Greer's catabolic collapse model. Produces scenario studies for real-world energy transition policy — what margin of error does an industrializing civilization have between peak fossil fuel and viable nuclear?

---

## First Contact Variance

**Question:** What structural conditions maximize the tech gap at first contact between an industrial hegemon and an uncontacted independent?

**What it tests:** What produces the worst contact outcomes for pre-industrial peoples.

**Rewards:** Extreme tech differential at moment of garrison absorption (tech 8+ absorbing tech 2-). Multiple such events per simulation run.

**Penalizes:** Gradual, trade-chain-mediated contact. Low tech gap at absorption.

**Social science relevance:** Produces quantified case studies for contact theory in anthropology. Identifies which geographic and economic conditions create the most asymmetric encounters — and by implication, which conditions protect indigenous autonomy (high civ_gap + low resource_targeting_weight + late industrialization).

---

## Isolationist Lattice

**Question:** Under what conditions does a powerful civilization choose not to project power beyond its home cluster?

**What it tests:** Whether imperial expansion is an inevitable consequence of surplus, or a culturally contingent choice. The Zheng He question.

**Rewards:** Subject-culture polity at tech ≥8 (industrial+), territorial extent ≤ home cluster + 2 hops. High consolidation spending, low frontier expansion.

**Penalizes:** Subject polity expansion beyond 3 hops from core. Subject colonial network.

**Social science relevance:** Tests offensive realism's prediction that surplus-rich states inevitably expand. If the optimizer finds a parameter set where the Lattice achieves industrial civilization without projecting (high consolidation_share, low expansion_share, defensive posture), that challenges Mearsheimer's universalism. Ming China's maritime withdrawal becomes a generalizable strategy, not a historical anomaly.

---

## Peaceful Nuclear

**Question:** Can both hegemons achieve nuclear capability and maintain stable deterrence without the scramble for Pu islands producing territorial conflict?

**What it tests:** Whether nuclear deterrence can emerge from cooperative Pu sharing rather than competitive acquisition.

**Rewards:** Both hegemons nuclear, no Pu islands changed hands by force, trade-based fuel agreements, stable sovereignty across all archs.

**Penalizes:** Pu island conquest, declining sovereignty post-industrial, fleet asymmetry >2:1.

**Social science relevance:** Tests whether the nuclear nonproliferation regime's cooperative model (IAEA, civilian fuel supply agreements) is achievable in a world with existential energy scarcity, or whether resource competition always produces the adversarial nuclear landscape we observe on Earth.
