# The Lock-In Mechanics

*On what the extractiveness index is measuring, how it builds, and why it matters for the simulation's development trajectories.*

---

The simulation tracks two distinct institutional measures that can retard tech growth. They are often confused because they produce similar output — reduced TFP — but they operate at different levels and respond to different conditions.

The first is the naphtha resource curse: high naphtha concentration drives a TFP penalty through the Sachs-Warner mechanism (Ross 2012). This applies to the core polity's own resource endowment. A polity with too much naphtha relative to the world supply develops extractive elites who capture resource rents and block the creative destruction that tech growth requires.

The second is the Acemoglu-Robinson extractiveness index. This applies not to the polity's own resource endowment but to the character of its *colonial institutions* — how the polity treats the territories it controls. A polity with high extractiveness has developed institutional habits of surplus extraction that are, according to the AR model, incompatible with the inclusive institutions that sustain long-run tech growth.

These are different failure modes. The naphtha curse is about windfall rents degrading institutional quality from the demand side. The extractiveness penalty is about colonial extraction hardening institutional exclusivity from the supply side. Both produce TFP decay, but through different mechanisms that respond to different interventions.

---

The extractiveness index builds from surplus extraction above a tolerable threshold in foreign-controlled territory, under conditions of collectivist culture (low CI position). The mechanism:

```
extractive_pressure = excess_extraction × (1 - CI_position) × institutional_lock_rate
```

The collective/individual culture axis is critical here. The AR finding in *Why Nations Fail* is not simply that extraction occurred (all empires extract surplus). It is that extraction under certain cultural and institutional conditions produces durable institutional lock-in that persists after the extractive relationship ends. The simulation encodes collectivist culture as the condition: polities with low CI scores develop the hierarchical administrative practices that make extraction efficient, but those same practices suppress the decentralized innovation that drives tech growth.

An individualist-culture polity can extract surplus from subject territories without building the same institutional habits, because its administrative practices are not dependent on hierarchical command. The extraction is real, but the institutional lock-in is weaker.

This is a contested finding in the actual historical literature. Whether Acemoglu and Robinson correctly identify culture as the mediating variable — rather than colonial intensity, geographic distance, or legal tradition — is actively debated. The simulation takes a position by parameterizing the effect through the culture vector, but the parameter `institutional_lock_rate` is tunable. The optimizer's job includes determining whether this effect size is consistent with the historical macro-patterns the simulation is calibrated against.

---

The extractiveness index has an important asymmetry: it decays slowly (not at all by default — there is no automatic decay). It only decreases when the polity's culture vector becomes more individualist. The "inclusive reform" path — the only way to reduce the extractiveness penalty in the simulation — requires the cultural transition that individualism enables. Polities that remain collectivist are trapped at whatever extractiveness level they accumulate.

This produces a specific dynamic in the simulation's history. Polities that expand aggressively in the colonial era — absorbing many territories under collectivist culture — accumulate high extractiveness. When those polities later face the pressures that push culture toward individualism (commercial success → prosperity → individualist drift), the extractiveness index does not automatically respond. It persists as a legacy penalty until the inclusive reform path becomes culturally available.

The AJR reversal-of-fortune pattern is partly a consequence of this asymmetry. The polities that were most successful at colonial expansion — the ones that absorbed the most territory under extractive institutional conditions — carry the highest extractiveness penalties into the industrial era. They arrive at the industrial era with the most territory but the most degraded TFP. The polities that expanded more slowly, under more individualist culture, may arrive with less territory but cleaner institutions.

---

There is a second asymmetry in the extractiveness index: it builds per-core, not per-territory. A polity's extractiveness reflects how *it* administers its territories, not what happened to those territories before. If Polity A absorbed Territory X early, built up extractiveness, then lost Territory X to Polity B in a later expansion, the extractiveness legacy stays with Polity A. Polity B gets Territory X's population and resources but not A's institutional habits.

This means the extractiveness penalty is portable: it follows the extracting polity, not the extracted territory. The simulation does not model the extractiveness burden that colonized territories carry into post-colonial development (the AJR finding is symmetric: both the colonizer and the colonized carry institutional legacies). The current implementation captures only the colonizer's side.

Implementing the colonized side — a grievance-plus-extractiveness legacy that reduces subject territory's own development velocity post-absorption — would require tracking per-territory institutional history that the current state space does not maintain at that resolution. The grievance mechanic is a partial substitute: grievance accumulates in subject territories and generates resistance that slows absorption, but it does not directly reduce the subject territory's tech growth. This is an acknowledged gap between what the AR framework predicts and what the simulation models.

---

The practical effect in simulations: polities that build up extractiveness above ~0.5 begin to experience meaningful TFP reduction (default `extractiveness_tfp_penalty` = 0.40, so a polity at extractiveness = 0.5 faces a 20% TFP reduction). At extractiveness = 1.0, the penalty is 40% — enough to prevent any polity from reaching nuclear-era tech without the cultural transition to individualism.

In practice, the most common path to extreme extractiveness is aggressive post-colonial expansion during the industrial era: a polity that absorbs many territories late in the simulation, under conditions of industrial-era collectivist culture, can rapidly push its extractiveness toward 1.0 and lock itself out of nuclear tech. This creates a self-limiting dynamic in the industrial era: the most aggressively expanding polities become the most institutionally degraded, and their tech growth slows as their territory grows. The simulation's history typically shows one or two polities going through this arc and losing the nuclear race to less aggressive but more institutionally flexible rivals.

The Dark Forest fires between the least extractive of the large polities — not necessarily the most powerful, but the ones whose institutional flexibility allowed them to reach nuclear tech first.

---

*See also: two_bargains.md (military vs. legal founding and what it means for extractiveness accumulation)*

*Acemoglu, D. & Robinson, J.A. (2012).* Why Nations Fail. *Crown.*
*Acemoglu, D., Johnson, S. & Robinson, J.A. (2001). "The Colonial Origins of Comparative Development." American Economic Review 91(5): 1369–1401.*
*Ross, M. (2012).* The Oil Curse: How Petroleum Wealth Shapes the Development of Nations. *Princeton University Press.*
