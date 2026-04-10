# The Terms-of-Trade Ratchet

*On what the Prebisch-Singer mechanic is modeling, and why it produces the polity stratification it does.*

---

The simulation encodes two different prices for the same caloric unit: the `prebisch_bulk_discount` (default 0.75) reduces the trade energy that bulk calorie exporters — sago, papa, paddi, taro producers — receive per contact relative to what luxury and relay-node polities receive. The `greif_relay_bonus` (default 0.08) adds a per-contact bonus for high-connectivity relay nodes.

Together these produce what Prebisch and Singer documented in the 1950 cross-national data: the terms of trade between primary commodity exporters and processed-goods exporters tend to deteriorate over time against the commodity exporters. In the simulation, this is structural rather than dynamic — it is not that the terms worsen over the simulation's history, but that they are always unfavorable for the polities in the bulk-commodity position. The ratchet is already set; bulk-crop polities start behind and remain behind unless they diversify.

The mechanism Prebisch and Singer identified was not simply that one side was being exploited. It was structural: income elasticity of demand for manufactured goods is higher than for food. As incomes rise globally, demand for processed goods grows faster than demand for bulk calories. The price ratio shifts accordingly.

The simulation does not model income elasticity explicitly — it is too simple an engine for that. What it does model is the consequence: relay-node and luxury-commodity polities capture more trade surplus per contact than bulk-calorie polities do, and this difference compounds over the full 10,000-year run. A polity that starts as a sago producer and remains one ends the simulation with systematically lower commercial energy than an adjacent nori-and-char producer at equivalent proximity and population.

---

The compounding operates through the tech growth mechanic. Trade energy feeds into the tech growth formula via `energy_to_tfp`. A polity with higher commercial energy accumulates tech faster. A polity that accumulates tech faster enters the industrial era earlier, accesses naphtha earlier, and achieves deterrence capability earlier. The Prebisch-Singer discount is not just a trade disadvantage; it is a development velocity disadvantage that propagates forward through the entire simulation.

This is the simulation's version of the structural divergence that development economists documented between the industrial core and the commodity periphery. The core and the periphery started at similar positions; the terms-of-trade structure accelerated the core's development while retarding the periphery's. By the time anyone noticed the divergence, it had already compounded through multiple generations of tech and institutional development.

The simulation makes this visible as a spatial pattern. In any simulation run where the world has been seeded with geographically clustered crop types — tropical bulks in the equatorial belt, luxury goods and relay nodes in the temperate zones — the equatorial belt lags the temperate zones in the tech progression even with equivalent geographic position, equivalent population density, and equivalent initial culture. The lag is the Prebisch-Singer effect rendered spatially.

This is not the only factor producing the equatorial lag in the simulation. The malaria belt (abs_lat < 20°) independently suppresses carrying capacity and therefore population density, which compounds with the trade disadvantage. The overlapping of the bulk-crop zone with the malaria zone — which reflects the actual geographic distribution of tropical crops and tropical disease — produces a double penalty in the equatorial belt that neither mechanism alone would produce.

---

What would eliminate the Prebisch-Singer disadvantage in the simulation? Not diversification alone — a sago-producing polity that adopts a tech diversification strategy still trades its primary output as sago for most of the simulation's history. The structural improvement comes from two paths.

**Route 1: Relay position.** If a bulk-calorie polity occupies a relay position — sits at a high-connectivity node in the contact network where goods transit from multiple trading partners — the Greif relay bonus can partially offset the bulk discount. A sago polity with five relay contacts captures more commercial energy than a sago polity with one. This is the relay operator model: value comes from position, not from what you produce. The polities that transition from producers to intermediaries in the pre-industrial era — who build their tech on the coordination surplus rather than on commodity rents — escape the Prebisch-Singer ratchet.

**Route 2: Tech-driven processing.** At higher tech levels, bulk polities can add processing capacity — the sago equivalent of nori pressed into oil, the papa equivalent of emmer milled into flour. The simulation models this implicitly through culture-space effects on the `individual_A0_coeff`: individualist cultures develop processing innovation faster, which breaks the commodity-producer dependency. But this requires crossing a development threshold that the Prebisch-Singer discount makes harder to reach. The bootstrap problem: escaping commodity dependence requires development, but commodity dependence retards the development needed to escape it.

The simulation's parameter `prebisch_bulk_discount` controls how strong this structural trap is. At 1.0 (no discount), bulk polities develop at the same velocity as luxury polities with equivalent contact networks. At 0.5 (50% discount), the trap is severe: equatorial bulk polities almost never reach nuclear-era tech without external trade investment or lucky relay positioning. The default 0.75 produces a noticeable but not deterministic gap — the equatorial belt lags but does not always fail to industrialize.

---

The real Prebisch-Singer finding was not that commodity exporters are poorer than manufactured-goods exporters at any given moment. It was that the gap tends to widen over time. The simulation captures this as a path-dependent compound rather than a continuing rate of change — once behind, the lag compounds forward.

What neither the simulation nor the historical data captures cleanly is the mechanism of escape: the polities that did industrialize from commodity-dependent starting positions. Brazil's industrial transition in the mid-20th century, South Korea's, Malaysia's — all of them involved specific policy choices, specific state capacity, specific moments of strategic investment in processing industry that broke the primary-commodity trap. The simulation does not model deliberate industrial policy because deliberate policy is something the AI players don't implement and the player choices don't directly encode.

This is a real gap in the simulation's academic grounding. The Prebisch-Singer mechanic captures the trap; it does not capture the policy toolkit for escaping it. The absence is noted. It is not correctable without a more complex player action set than the current six-parameter decision object supports.

---

*See also: the_desperation_trap.md (resource pressure → cascade); the_fever_belt.md (epidemiological reinforcement of equatorial disadvantage)*

*Prebisch, R. (1950).* The Economic Development of Latin America and Its Principal Problems. *ECLA/UN.*
*Singer, H.W. (1950). "The Distribution of Gains Between Investing and Borrowing Countries."* American Economic Review *40(2).*
*Ocampo, J.A. & Parra, M.A. (2006). "The commodity terms of trade and their strategic implications for development."* Rethinking Development Economics, *Palgrave.*
