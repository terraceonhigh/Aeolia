# The Collapse Cascade

*On what happens when a polity's energy budget falls below its maintenance floor, and why complexity makes it worse.*

---

Joseph Tainter's 1988 study of collapsed civilizations proposed an explanation that differed from the conventional archaeology of catastrophe. Civilizations do not collapse because they run out of resources, because they are invaded, or because of moral failure. They collapse because the returns on complexity diminish.

Every layer of institutional complexity a civilization adds — administrative hierarchies, legal systems, military organization, trade infrastructure — requires maintenance. That maintenance is a fixed cost that the civilization's energy surplus must cover. When the surplus is abundant, the maintenance cost is small relative to the returns on complexity: the bureaucracy that manages water distribution produces more calories than it costs in salaries. When the surplus shrinks — through resource depletion, trade disruption, agricultural failure, climate shift — the ratio changes. The maintenance cost stays fixed while the returns on complexity decline. At some threshold, maintaining the complexity consumes more resources than the complexity produces. Simplification becomes economically rational.

Tainter's key insight was that collapse is not failure. It is adaptation. Shedding institutional complexity releases the resources that complexity was consuming, allowing the population to survive at a lower level of organization. The collapse is not the end of the civilization; it is the civilization's response to the point where its organizational overhead exceeded its productive capacity.

---

## The Maintenance Formula

The simulation's tech decay mechanic is the computational version of Tainter's argument.

Each tick: `maintenance_cost = tech² × maintenance_rate`. The quadratic dependence on tech encodes the increasing returns to maintenance that higher complexity requires. A polity at tech 3 (classical agricultural) has a maintenance cost of 9 × maintenance_rate. A polity at tech 8 (industrial) has a maintenance cost of 64 × maintenance_rate. The same maintenance_rate coefficient produces dramatically different absolute burdens at high tech levels.

When `energy_surplus < maintenance_cost`, tech decays: `delta_tech = -(shortfall × decay_rate)`. The shortfall is the gap between what the polity's energy budget produces above subsistence and what its tech level costs to maintain. A small shortfall produces slow decay; a large shortfall produces rapid decay. Tech 8+ polities can fall several tech levels in a handful of ticks if their energy budget collapses completely.

The desperation cascade fires at the same time: the allocation override forces spending toward expansion, compounding the maintenance shortfall. A polity in tech decay is simultaneously losing capability and being forced to spend resources on acquisition rather than maintenance. This is the Tainter spiral: reduced capacity → reduced returns on complexity → maintenance shortfall → further reduced capacity.

---

## The Bronze Age Collapse Model

Eric Cline's 2014 study of the Late Bronze Age Collapse around 1177 BC proposed a different mechanism that is not inconsistent with Tainter but emphasizes network fragility. The Bronze Age palace economies — Mycenaean Greece, Hittite Anatolia, New Kingdom Egypt, Ugarit, Cyprus — were tightly interconnected through specialized trade. Each polity's production was specialized: one produced copper, another tin, another grain, another textiles. None could produce everything it needed independently.

When this system came under stress — through drought, invasions, internal revolt, or some combination of all three — the interconnection that had been the system's strength became its vulnerability. Supply disruptions in one node cascaded through all the dependent nodes. Polities that had invested in specialization at the cost of self-sufficiency found that their trade partners were simultaneously unavailable. The collapse was not one polity's failure; it was the networked failure of an entire production system.

The simulation encodes the Cline mechanism through the relay trade dependency. Polities that have grown their energy budgets partly through relay trade gains are vulnerable to relay network disruption. When a major relay partner is absorbed, destroyed, or embargoed, the trade energy contribution to the absorber's surplus falls. If the polity's tech level was calibrated against a surplus that included relay gains, the loss of those gains can push maintenance_cost above available surplus, triggering tech decay.

The relay network dependency makes the collapse cascade contagious: a polity undergoing tech decay produces reduced relay trade for its partners, which can reduce their energy surplus, which can push some of them below their maintenance thresholds, which produces reduced relay trade for their partners. Whether a cascade propagates or is absorbed depends on whether the affected polities have enough internal energy surplus to absorb the relay shock. Well-cushioned polities (high agricultural productivity, good fisheries) absorb shocks that cascaded into vulnerable polities (high relay dependency, marginal agriculture) will not survive.

---

## Historical Shape of the Cascade

The tech decay cascade produces a characteristic signature in the simulation's output that matches the historical signature Tainter and Cline document.

**Rapid onset**: once a polity crosses the maintenance threshold, decay is fast. The quadratic maintenance cost means that even small energy shortfalls at high tech levels produce large decay rates. A polity at tech 8 with a 10% energy shortfall loses tech much faster than a polity at tech 4 with the same 10% shortfall.

**Irreversibility in the short term**: a decaying polity cannot easily stop its decay by investing in tech, because the investment mechanism (the share_mult innovation allocation) is being overridden by the desperation cascade toward expansion. By the time the expansion attempts succeed (if they succeed), the tech level has already fallen significantly.

**Asymmetric recovery**: if a polity successfully acquires new territory and restores its energy budget, tech growth resumes. But the recovery is slow — the normal accel_rate applies — while the decay was fast. Polities that collapse to tech 5 from tech 8 do not quickly recover to tech 8. The collapse produces a lasting disadvantage.

**Geographic contagion**: the cascade spreads through relay networks in the pattern Cline documented. The most vulnerable polities are those most dependent on relay trade and least buffered by internal production. These tend to be the most commercially developed polities — the ones that had specialized into relay nodes precisely because relay specialization was economically optimal when the network was functioning.

---

## The Limits of the Model

Tainter's argument has been criticized on grounds that it assumes complexity always produces declining returns, when historically some complexity increases have produced improving returns for extended periods. The simulation applies the maintenance cost quadratically to all polities regardless of their institutional quality, which means it does not capture the variance in maintenance-efficiency that Tainter's own comparative evidence shows. Some civilizations maintained high-complexity institutions at lower relative cost than others with similar formal complexity, because their institutions were more efficient.

The simulation also does not model the *rate* at which a polity can simplify. Tainter argues that simplification is a deliberate (if sometimes painful) adaptation; the simulation models simplification as involuntary decay. A polity cannot choose to shed institutional complexity preemptively to preserve its energy surplus. This means the simulation may overstate the catastrophic-ness of the cascade relative to historical cases where managed simplification allowed polities to survive at reduced complexity.

The Cline network-contagion mechanism is also simplified. The simulation propagates relay-loss shocks through the network but does not model the additional second-order effects that Cline documents: the movements of displaced populations, the resource competition produced by multiple collapsing polities seeking the same acquisition targets simultaneously, the psychological breakdown of trading relationships that had been sustained by long-term trust.

These gaps matter for the simulation's accuracy in modeling collapse episodes, which are among its most dramatic outputs. A more mechanistically faithful collapse model would be one of the highest-value improvements to the simulation's historical representativeness. It would also require the most new mechanics.

---

*See also: the_desperation_trap.md (how the cascade fires); the_three_layer_trade_system.md (relay dependency that makes collapse contagious)*

*Tainter, J.A. (1988).* The Collapse of Complex Societies. *Cambridge University Press.*
*Cline, E.H. (2014).* 1177 B.C.: The Year Civilization Collapsed. *Princeton University Press.*
*Turchin, P. (2003).* Historical Dynamics: Why States Rise and Fall. *Princeton University Press.*
