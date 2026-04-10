# The Three-Layer Trade System

*On why the simulation's commerce works at three speeds and what each layer is modeling.*

---

The simulation's trade energy calculation runs across three distinct layers: Subsistence, Relay, and Administered. Each layer has its own formula, its own conditions of access, and its own relationship to the polities participating in it. The three-layer structure is not arbitrary bookkeeping. It is the simulation's compression of three different theoretical traditions about how commercial exchange has worked across history.

---

## Layer One: Subsistence

The subsistence layer is local exchange — the trade that happens within an archipelago's own economic community, at the pace of seasonal markets and direct barter. It does not require commercial infrastructure beyond the ability to travel within a polity's controlled territory. Every polity participates in it by default. Its yield is a fixed fraction of the polity's own agricultural and fishery production, representing the gains from local specialization (the farmer who grows more wheat and the fisherman who catches more fish, trading with each other, are both better off than if each tried to produce everything they needed independently).

The Annales historian Fernand Braudel called this the layer of "material life" — the long-duration, slow-changing, mostly-invisible underpinning of economic activity that precedes and outlasts the commercial arrangements built on top of it. In his three-volume study of early modern European economic history, Braudel distinguished this layer from the "market economy" (organized commercial exchange, the relay layer in the simulation's terms) and from "capitalism" (the long-distance, high-profit, administered commercial networks of major trading houses). Material life was neither market nor capitalism; it was the subsistence economy that sustained the populations who participated in the more visible layers.

The simulation's subsistence layer is similarly invisible in the aggregate statistics — it does not appear in the trade flows tracked by the relay or administered metrics — but it forms the floor of every polity's energy budget. Destroying a polity's agricultural and fishery base eliminates this floor. No amount of commercial access to the relay or administered networks can compensate for the loss of subsistence-layer production, because those networks require a population capable of producing surplus to trade.

---

## Layer Two: Relay

The relay layer is long-distance trade between polities that are not within the same empire. Goods move through intermediate nodes — relay polities that sit between trading partners and take a margin for facilitating the exchange. The relay layer requires commercial relationships (established by diplomatic contact and maintained by the trade network mechanics), and its yield depends on the tech level and outward culture orientation of the participating polities.

The relay layer encodes what the historian Janet Abu-Lughod documented in her study of the thirteenth and fourteenth century world-system before European hegemony: a polycentric commercial network in which no single power dominated, in which trade flowed through multiple overlapping circuits, and in which the comparative advantage of each circuit came from geographic position and commercial specialization rather than from coercive enforcement of terms. Abu-Lughod's world-system had eight distinct commercial circuits — the Champagne fairs, the Italian city-states, the Egyptian Red Sea trade, the Indian Ocean dhow network, and others — each functioning with substantial autonomy and each connected to the others through relay points where goods changed hands.

The relay layer's decentralization is its defining feature. No polity is required to participate; polities participate because the mutual gains from exchange are positive. The relay layer's yield is therefore sensitive to disruption in a characteristic way: trade embargoes, wars, and political hostility reduce relay access symmetrically — the polity imposing the embargo loses relay yield to the embargoed partner as well as gaining the coercive objective. This makes the relay layer a domain of genuinely voluntary exchange.

The Sovereignty's commercial architecture, in the simulation's late-game configuration, resembles the relay-layer model. It is organized around mutual agreement, RSC arbitration, and Commercial Standards that any participant can choose to adopt. The relay layer is where the Sovereignty's institutional investment produces its commercial returns.

---

## Layer Three: Administered

The administered layer is the Wallerstein layer. Immanuel Wallerstein's world-systems theory argues that modern capitalism organizes global economic activity into a hierarchical structure: core polities (high-tech, high-value-added production, strong institutions) extract surplus from peripheral polities (raw material exporters, weak institutions, unfavorable terms of trade) through the mechanism of unequal exchange. The exchange is not literally coerced in each individual transaction — market prices are set — but the structure of the market is coercive: peripheral polities have limited alternatives to the terms set by core polities, because the commercial infrastructure that would allow them to find better terms is itself controlled by core polities.

The administered layer in the simulation is the commercial relationship between an imperial power (a polity that has achieved sovereignty over another polity's archipelago) and its administered territories. Administered trade is not voluntary in the relay-layer sense: the terms are set by the administering polity's commercial framework, access is granted through the administering polity's infrastructure, and the administered polity does not have a meaningful exit option without forfeiting the commercial relationship entirely.

The administered layer's terms are systematically less favorable to the peripheral polity than relay-layer terms would be. This encodes both Wallerstein's unequal exchange finding and the Prebisch-Singer terms-of-trade dynamic documented elsewhere in this garden. The administered layer's yield for the administering polity is higher than relay-layer yield from the same trade volume, precisely because the administered polity cannot negotiate on equal terms. The difference in yield is the extraction premium of colonial commercial administration.

The Reach's commercial architecture, in the simulation's late-game configuration, resembles the administered-layer model. Bridge Documentation standards, Commercial Registry requirements, administered levy payments — these are the institutional form of the Wallerstein core/periphery extraction structure. The administered layer is where the Reach's institutional investment produces its commercial returns, but also where its grievance accumulation occurs.

---

## What the Layered Structure Produces

The three-layer structure creates commercial trajectories that a single-layer trade model would not produce.

**Pre-industrial polities** primarily operate in the subsistence layer, with relay-layer participation proportional to their outward culture orientation and their tech level. Administered-layer participation comes only when a polity is absorbed into an expanding empire. The pre-industrial commercial picture is therefore one of overlapping relay networks with varying degrees of connection, consistent with the polycentric pre-hegemonic world Abu-Lughod documents.

**The scramble phases** (naphtha at tech ~5, pyra at tech ~8) shift this picture by dramatically raising the value of the administered layer. When a strategic resource is in demand, the polity that controls the territory containing it captures the full administered-layer premium on that resource — not the relay-layer margin, but the coercive extraction premium. This creates an incentive for aggressive expansion at exactly the moment when tech growth is fastest and expansion capacity is highest. The scramble dynamics are thus the simulation's version of the historical colonial scrambles: periods when resource valuation shifts sharply upward, triggering rapid administrative expansion by whichever polities have the capacity to move first.

**The post-DF period** freezes the administered-layer architecture. The deterrence equilibrium prevents direct military conquest between nuclear-capable polities, which means the administered-layer distribution established before deterrence locks in. Late-game commercial competition is therefore primarily relay-layer competition: polities compete to become relay nodes in the commercial network, to set relay-layer standards, and to attract administered-territory polities toward the Sovereignty's associate-member arrangements rather than the Reach's direct administration.

This late-game shift from administered to relay competition is the simulation's encoding of what happened to colonial commercial empires in the post-nuclear world: the administered-layer arrangements became increasingly costly to defend (grievance accumulation, anti-colonial political movements, the rising cost of military enforcement) at exactly the moment when deterrence made new administered-layer expansion impossible. The Wallerstein world-system did not end; it evolved — the extraction premium shifted from direct administration to structural terms-of-trade disadvantage, maintaining core/periphery inequality through financial and commercial mechanisms rather than direct political control.

---

## What the Layers Do Not Capture

The three-layer model compresses several important distinctions.

The simulation does not differentiate within the relay layer between different kinds of voluntary commercial exchange — between truly competitive markets with many suppliers and buyers, and oligopolistic relay networks in which a small number of relay nodes effectively control access and can extract monopoly rents. Braudel's "capitalism" layer was specifically characterized by this rent-extraction through monopoly of long-distance trade routes; his "market economy" layer was competitive in the sense of having many participants with genuine alternatives. The simulation uses a single relay yield formula for both.

The simulation also does not model financial flows as distinct from commodity flows. In historical commercial empires, the extraction mechanism was often financial — interest payments on colonial debts, currency manipulation, insurance monopolies — as much as it was through commodity price manipulation. The Prebisch-Singer finding is about commodity terms of trade, but much of the surplus extraction that Wallerstein documented worked through financial channels that commodity prices do not capture. The simulation's trade energy calculations are in caloric-equivalent energy units, not in monetary units, which means financial extraction mechanisms are simply absent from the model.

These are gaps that matter more as the simulation's tech level increases and the commercial economy becomes more sophisticated. Pre-industrial trade is mostly commodity trade, so the absence of financial mechanisms is less consequential. Industrial and post-industrial trade has a financial architecture that is substantially more important than the commodity flows, and the simulation's three-layer model does not represent it.

---

*See also: the_terms_of_trade_ratchet.md (Prebisch-Singer within administered trade); the_grievance_accumulation.md (Scott resistance in administered territories)*

*Wallerstein, I. (1974).* The Modern World-System, Vol. 1: Capitalist Agriculture and the Origins of the European World-Economy in the Sixteenth Century. *Academic Press.*
*Braudel, F. (1979).* Civilization and Capitalism, 15th–18th Century. *3 vols. Harper & Row.*
*Abu-Lughod, J.L. (1989).* Before European Hegemony: The World System A.D. 1250–1350. *Oxford University Press.*
