# The Thalassocratic Condition

*On why ocean-dominant civilizations work differently from land-dominant ones, and what the simulation loses and gains from being set in a world with no heartland.*

---

Nicholas Spykman's 1942 geopolitical framework offered a revision of Halford Mackinder's "Heartland" thesis. Mackinder had argued that control of the Eurasian landmass — specifically, the interior steppe zone that he called the Heartland — was the key to global dominance: whoever held the Heartland commanded the "World Island" (Eurasia + Africa), and whoever commanded the World Island commanded the world. The Heartland thesis was a theory of continental land power.

Spykman reversed the emphasis: what mattered was not the interior but the coast. He called the coastal zone the "Rimland" — the crescent of densely populated, commercially active, strategically contested territory surrounding the Eurasian interior. In Spykman's framework, sea power projected from the Rimland was more capable of shaping world politics than land power projected from the Heartland. The critical chokepoints were maritime — straits, port cities, oceanic routes — not continental.

The simulation's world makes Spykman's revision not a revision but a complete displacement. There is no Heartland. The world is 95% ocean. There are no continental interiors to hold, no steppe routes to control, no land power to threaten coastal polities from behind. All geopolitics is Rimland geopolitics: all strategic positions are islands, all trade routes are sea routes, all military power is naval power. The question Spykman was arguing with — whether land power or sea power is the decisive factor in world politics — does not arise. The answer is given by the world's physical structure.

---

## What Changes Without a Heartland

Classical geopolitical theory identifies four properties of land power:

1. **Internal lines of communication**: land powers can move forces through their interior without exposure to enemy interception
2. **Depth**: land empires can absorb coastal incursions and trade space for time
3. **Agricultural sustainability**: land powers can survive trade blockades because their food supply is internal
4. **Conquest persistence**: occupying territory is more durable than sea control because land can be permanently settled

In the simulation's ocean world, all four of these properties are degraded or eliminated.

Internal lines of communication are sea lanes. They can be interdicted. A polity whose trade network is severed does not have an interior route to fall back on. This makes trade disruption more consequential in the simulation than it would be in a continental world. The trade embargo mechanic in the strategy game is more decisive than a comparable mechanic would be in a land-dominant world.

Depth does not exist. An archipelago either controls its own surrounding waters or it does not. There is no hinterland to which a defeated polity can retreat and reconstitute. When the simulation models territory loss, the loss is immediate in its economic consequences because there is no safe interior to draw on.

Agricultural sustainability is limited by island scale. Small archipelagos cannot be agriculturally self-sufficient. They depend on trade and fisheries to supplement their land base. This makes the Malthusian ceiling lower and the desperation cascade threshold more reachable for island polities than for comparable continental polities.

Conquest persistence requires ongoing naval superiority. An island territory held by a polity whose fleet is subsequently defeated does not remain held. The sovereignty mechanics in the simulation reflect this: sovereignty score decays at a rate that depends on the extracting polity's ongoing presence and force projection. Continental empires can hold territory through garrisons that benefit from interior supply lines; thalassocratic empires hold territory by maintaining relative naval dominance, which can shift.

---

## What Persists

Some geopolitical dynamics are robust enough to apply in an ocean world despite the elimination of the Heartland.

**Chokepoint economics** — the disproportionate commercial value of geographic positions that allow control of passages — operate identically. In Aeolia, the chokepoints are passage gaps between island chains, the narrow straits between archipelago groups that all long-distance trade must transit. Polities positioned at these chokepoints capture relay trade premiums without proportional production investment. The Greif relay bonus in the simulation is the computational expression of this: high-contact nodes extract asymmetric commercial surplus from their intermediary position.

**Coalition dynamics** — the tendency for secondary powers to align against the most threatening hegemon — operate with more freedom in the ocean world than in a continental setting, because there is no geographic contiguity constraint on alliance formation. Any polity can ally with any other polity across any distance. Walt's balance-of-threat formation (implemented in Stage 4.5) is therefore unconstrained by continental geography; alignment drifts based purely on threat calculation.

**Deterrence stability** — the mutual-vulnerability logic of nuclear deterrence — operates identically. The ocean world's geography does not change the fact that two polities capable of second-strike response have no rational basis for initiating nuclear conflict with each other. The Dark Forest equilibrium is geography-independent.

**Trade-network dependency** — the degree to which a polity's economic viability depends on trade relationships rather than self-sufficiency — is amplified, not changed in kind. Continental polities can be self-sufficient; island polities cannot. The relay and administered trade layers matter more in the simulation than they would in a continental equivalent, because subsistence-only polities face a genuine caloric ceiling that cannot be overcome without marine trade supplements.

---

## The Instability Premium

Fernand Braudel's study of Mediterranean maritime civilization documented what might be called the "thalassocratic instability premium": commercial city-states and maritime empires tend to rise and fall faster than continental empires. Venice, Genoa, Carthage, the Hanseatic League, the Portuguese Estado da India — all achieved remarkable commercial dominance over periods measured in decades or a few centuries, then declined sharply when trade routes shifted or when competitors gained naval parity. Continental empires like Rome or China measured their dominant periods in centuries.

The reason is structural: maritime commercial empires are held together by the economic value of their network position. When the network changes — when a new route opens, when a new chokepoint falls to a rival, when a new technology reduces the strategic value of an old transit point — the empire that depended on that position loses its organizing principle faster than a continental empire would. Continental empires have the geographic anchors of territory; maritime empires have only the economic anchors of trade.

The simulation reproduces this pattern. Maritime polities in the simulation show higher variance in trajectory than territorial polities at equivalent tech levels. They can rise fast — the relay bonus compounds quickly once a high-connectivity position is established — and they can fall fast when the network around them reorganizes. This is not modeled as a distinct mechanic; it emerges from the interaction of the relay bonus, the sovereignty decay dynamics, and the absence of geographic depth.

The thalassocratic instability premium is one reason why the simulation's late-game configuration tends toward two dominant powers rather than one. A single maritime hegemon faces the instability premium alone; two hegemons in deterrence equilibrium face it together, and the symmetry of mutual deterrence provides a stability anchor that a single-hegemon world would not have. This is not an argument for the desirability of the nuclear standoff — but it is an observation about why the Strange Peace is, structurally, a more durable configuration than a pre-nuclear single-hegemon world would be.

---

## What the Simulation Cannot Model

The absence of a heartland eliminates a class of strategic dynamics that classical geopolitics treats as fundamental: the land-power / sea-power rivalry, the question of whether a sea power can be successfully threatened by a land power that develops naval capacity, the tension between interior-line logistics and exterior-sea logistics that shaped the major conflicts of the 20th century.

The simulation also cannot model the unique features of truly isolated ocean civilizations — the Polynesian wayfinding tradition, the navigational technology required for inter-island contact across thousands of kilometers of open ocean, the cultural consequences of extreme geographic isolation over hundreds of generations. Patrick Kirch's work on Polynesian expansion documents how long-distance navigation capacity shaped everything from crop selection to social stratification in island civilizations that had no land-power alternative. The simulation's archipelago world is connected enough that the isolation extreme is not reached, but the intermediate cases — polities with low contact counts who exist in the fog-of-war frontier — have some of the isolation dynamics without the full modeling.

The thalassocratic fragility grade of B reflects honest uncertainty rather than identified failure. The simulation's ocean world is working as a thought experiment; it produces coherent and interesting strategic dynamics. What is uncertain is whether the specific magnitudes — the speed of rise and fall, the coalition formation rates, the sovereignty decay rates — are the right magnitudes for a world with this physical structure. There is no empirical baseline. The calibration is against Earth-history macro patterns that emerged from a continental world. This is the best available approximation, but the approximation error is unknown.

---

*See also: the_three_layer_trade_system.md (relay chokepoints and Greif asymmetry); the_intermediate_belt_problem.md (Walt alignment without geographic contiguity constraints)*

*Spykman, N.J. (1942).* America's Strategy in World Politics: The United States and the Balance of Power. *Harcourt, Brace.*
*Mackinder, H.J. (1904). "The Geographical Pivot of History."* Geographical Journal *23(4).*
*Kirch, P.V. (2000).* On the Road of the Winds: An Archaeological History of the Pacific Islands before European Contact. *University of California Press.*
*Braudel, F. (1949/1972).* The Mediterranean and the Mediterranean World in the Age of Philip II. *University of California Press.*
