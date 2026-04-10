# The Relay Advantage

*On information asymmetry in commercial networks, and why the node between trading partners captures more surplus than the ends.*

---

Avner Greif's 1989 study of Maghribi Jewish traders in the eleventh-century Mediterranean documented a commercial structure that seems counterintuitive: the traders who profited most from long-distance commerce were not those who produced the most, but those who sat between producers who could not observe each other's prices.

The Maghribi traders operated as agents for merchants in different port cities. A merchant in Alexandria wanted to sell silk in Sicily; he could not travel there himself; he could not easily observe the price that silk was fetching in Sicily. He needed an agent. The agent who sat between Alexandria and Sicily, who knew prices in both ports, who had relationships with buyers on both ends, could capture a price differential that neither the Alexandria merchant nor the Sicilian buyer could close on their own — because closing it would require the trust and information that only the relay agent had accumulated.

Greif called the mechanism "reputation and coalitions in medieval trade." The coalitions were the networks of Maghribi traders who shared information with each other, enforcing commercial honesty through repeated interaction and social sanction, and denying access to the network to merchants who cheated. The reputation was what allowed the relay agent to be trusted by both ends simultaneously. The information advantage — knowing prices on both sides — was what made the relay position profitable.

---

## The Simulation's Relay Bonus

The simulation encodes Greif's finding in the relay trade mechanic.

When two polities conduct relay trade through an intermediate node, the intermediate node receives a contact-count bonus: `relayBonusA = min(0.40, contactSet[tc].size × greif_relay_bonus)`. A relay node with more contacts captures a larger share of the trade surplus than a relay node with fewer contacts, because more contacts means more price-surface visibility and more coalition enforcement capacity.

The `greif_relay_bonus` parameter defaults to 0.04. Each additional contact in the relay node's network adds 4% to the relay bonus, up to the cap of 40%. A relay node with five contacts captures 20% of trade surplus in addition to its normal trade yield; a relay node with ten contacts captures the full 40%.

The cap exists to prevent the relay bonus from becoming the dominant economic mechanism. At a fully uncapped relay bonus, the simulation would produce extreme concentration of commercial wealth at relay nodes in ways that distort the other mechanics. The 40% cap means that relay nodes are commercially advantaged but not commercially dominant — they supplement their productive base rather than replacing it.

---

## What the Relay Bonus Produces

The relay bonus creates a characteristic economic geography in the simulation: high-connectivity archipelagos accumulate commercial wealth that is disproportionate to their productive base.

An archipelago at a geographic chokepoint — between two major trading zones, on the route between a high-tech production center and a high-population consumption center — will accumulate more relay contacts than a comparable archipelago in a peripheral position. Over 50 to 100 ticks, the relay income from this position compounds into a significantly higher energy budget, which funds faster tech growth (through `energy_mult`) and larger expansion ambitions.

The commercial chokepoint dynasties in the simulation's output — the polities that dominate relay networks in the pre-DF era — are almost never the largest polities. They are the best-positioned polities. This is consistent with the historical pattern of commercial empires: Venice was not the largest polity in medieval Europe; it was the most strategically positioned for Mediterranean relay trade. The Hanseatic League's member cities were not the most productive in Europe; they controlled the Baltic-North Sea relay routes.

---

## The Asymmetry and Its Limits

The relay asymmetry has a self-correcting limit in the simulation that it did not always have in history.

The relay bonus grows with contact count. But contact count grows through diplomatic activity and trade establishment, not through the relay mechanic itself. A relay node cannot force other polities to route trade through it — it can only benefit from trade that naturally passes through its geographic position. This means the relay advantage requires geographic luck: being in the right place when the trade network forms.

Geographically non-central polities cannot build relay advantages through commercial investment alone. They can become relay nodes only if their geographic position becomes strategically valuable — if a new trade route opens that their position commands, if nearby polities become major producers or consumers that need intermediaries. The simulation does not allow polities to build relay infrastructure that changes which geographic positions are optimal. Geographic advantage is given; it is not constructed.

This is probably an accurate simplification for pre-industrial periods but is less accurate for the industrial and post-industrial periods, when infrastructure investment genuinely did change which geographic positions were commercially valuable. The Suez and Panama Canals are the clearest historical examples: they transformed the commercial geography of the world through infrastructure investment, not through geographic luck. The simulation has no equivalent.

The relay bonus also caps at 40% and applies per-contact, not per-volume. This means a relay node does not benefit from the value of what is traded — only from how many contacts it has. A relay node in a high-volume luxury goods circuit and a relay node in a low-volume staples circuit with the same number of contacts receive the same relay bonus. The simulation does not implement Greif's finding that the information asymmetry is larger for luxury goods (where price differentials are higher and price discovery is harder) than for staple goods (where prices are well-known and differentials are small).

These are the known approximations. The relay bonus captures the structural essence of Greif's finding — position in the network is commercially valuable, and the value is proportional to network centrality — without capturing the full micro-mechanism of how that value is extracted.

---

## The Coalition Side

Greif's study emphasizes two mechanisms: the information asymmetry and the coalition enforcement. The simulation models the first and omits the second.

The Maghribi traders' coalition was not just an information network — it was an enforcement mechanism. Coalition members shared information about merchants who had cheated or defaulted. Merchants who violated commercial norms were denied future access to the coalition's agents. This threat of exclusion enforced honest commercial behavior without requiring legal enforcement, which was largely unavailable for cross-jurisdictional long-distance trade.

The simulation has no equivalent coalition enforcement mechanic. Polities do not accumulate trust or reputation through their commercial history; they do not face exclusion from relay networks as a consequence of past defection. The relay bonus depends only on current contact count, not on commercial behavior history.

Adding coalition enforcement would require tracking a commercial reputation variable per polity and modifying the contact-establishment mechanics to reflect reputation effects on whether other polities are willing to form relay relationships. This is feasible but was judged as adding complexity without proportional improvement to the simulation's macro-level calibration. The relay bonus already produces approximately the right geographic pattern of commercial wealth concentration. Coalition enforcement would change the micro-mechanism without necessarily improving the macro-pattern.

---

*See also: the_three_layer_trade_system.md (relay layer in the full trade system context)*

*Greif, A. (1989). "Reputation and Coalitions in Medieval Trade: Evidence on the Maghribi Traders."* Journal of Economic History *49(4).*
*Greif, A. (1993). "Contract Enforceability and Economic Institutions in Early Trade: The Maghribi Traders' Reputations."* American Economic Review *83(3).*
*Greif, A. (2006).* Institutions and the Path to the Modern Economy: Lessons from Medieval Trade. *Cambridge University Press.*
