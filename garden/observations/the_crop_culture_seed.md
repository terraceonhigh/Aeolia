# The Crop-Culture Seed

*On why the world starts arranged the way it does, and what that initial arrangement encodes.*

---

The simulation's culture space has two axes: Collective/Individual (CI) and Inward/Outward (IO). Every polity begins the simulation at a position in this space that is determined partly by random variation and partly by its primary crop.

The crop-to-culture seed table:

| Crop | CI seed | IO seed |
|------|---------|---------|
| Emmer | +0.45 | +0.55 |
| Nori | +0.35 | +0.65 |
| Paddi | −0.55 | −0.20 |
| Taro | −0.10 | +0.05 |
| Sago | −0.20 | −0.10 |
| Papa | +0.15 | +0.15 |
| Foraging | 0.00 | 0.00 |

The emmer and nori polities start individualist and outward. The paddi, sago, and taro polities start collectivist and inward. Papa and foraging polities start near center.

This is not arbitrary. It encodes Karl Wittfogel's hydraulic hypothesis — itself a contested reading of Karl Marx's "Asiatic mode of production" — that the type of agriculture a society practices shapes its political culture.

---

**Wittfogel's argument** (1957): wet-rice cultivation requires coordinated irrigation. You cannot manage a paddy system as individual family units; you need coordinated construction, maintenance, and water-sharing arrangements across multiple farms. This coordination requirement produces collectivist, hierarchical social organization — a strong administrative state, extended kinship networks, emphasis on group solidarity over individual autonomy. The "hydraulic civilizations" of monsoon Asia (China, India, the Near East, Mesoamerica's chinampa systems) all share this feature: complex irrigation requiring centralized organization producing collectivist culture.

Dry-grain agriculture — emmer wheat, European barley, American maize in non-irrigated settings — can be managed at the family-farm level. You do not need your neighbor's cooperation to plant and harvest your field. This independence produces individualist, less hierarchical social organization.

The simulation encodes this through the crop seed:
- Paddi (wet-rice) gets the most collectivist seed: CI = −0.55
- Sago and taro (tropical crops with communal harvesting practices) get moderate collectivist seeds
- Emmer and nori (temperate dry-grain and ocean fishery) get individualist seeds
- Papa (Andean root crop, manageable at family scale) gets a near-neutral seed

The Inward/Outward dimension encodes a different but related finding: commercial orientation. Nori and emmer polities start outward because their surplus production was historically oriented toward long-distance trade. Paddi and sago polities start inward because their caloric surplus was historically consumed locally rather than exported.

---

**Almond and Verba** (1963, *The Civic Culture*) contribute a different conceptual framing for the IO dimension: civic culture as a combination of participant (engaged in governance and commerce) and subject (deferential to authority) orientations. The outward culture in the simulation maps loosely onto the participant orientation: polities that orient toward external engagement also tend to be more commercially innovative and more politically active in the relay network's governance structures.

The mapping is loose because the simulation compresses two distinct theoretical traditions into a single two-dimensional space. Wittfogel's hydraulic hypothesis is about the material conditions of agriculture shaping political organization. Almond and Verba's civic culture framework is about the psychological orientations of political participants. These are different levels of analysis. The simulation uses a shared two-dimensional representation for computational simplicity, not because the theories are equivalent.

---

**What the initial seed means for the simulation's history:**

The crop-to-culture seed creates systematic geographic patterns at the start of the simulation and propagates them forward through the cultural drift dynamics.

Polities that start individualist and outward tend to drift toward civic culture faster (the drift mechanics reinforce prosperity → individualism and trade exposure → outwardness). Polities that start collectivist and inward tend to develop the institutional forms that produce high extractiveness and high piety. The initial seed is not destiny — culture drift over thousands of years can move any polity far from its starting position — but the 10,000-year simulation does not always have enough time to fully overcome a collectivist/inward seed in the equatorial belt.

The equatorial belt's paddi, sago, and taro polities therefore tend to arrive at the industrial era with more collectivist culture than temperate zone polities, contributing to the institutional lock-in dynamic (the AR extractiveness penalty is stronger under collectivist culture) and the piety retention dynamic (the Norris-Inglehart secular transition is slower for polities that started collectivist).

This geographic correlation between crop type, culture seed, and development trajectory is the simulation's version of the crop-culture path dependency that development economists have debated for decades. It is consistent with the AJR reversal finding (the most productive tropical territories became the most extractively administered); it is consistent with the Prebisch-Singer terms-of-trade dynamic (tropical bulk crops are discounted relative to temperate luxury goods); and it is consistent with the malaria-belt population ceiling (which applies to the same geographic zone where paddi/sago/taro crops appear).

The simulation's equatorial belt disadvantage is overdetermined: it is produced independently by crop culture, malaria, and terms of trade. All three mechanisms are pointing the same direction for the same polities, producing a compound effect that is more durable than any single mechanism would produce alone.

---

**The critique:** Wittfogel's hydraulic hypothesis has been substantially criticized in the historical literature. The evidence for hydraulic civilization producing more authoritarian governance than non-hydraulic civilization is mixed; many hydraulic civilizations maintained sophisticated participatory institutions alongside their administrative irrigation structures. Some scholars argue Wittfogel's framework served Cold War political purposes (associating Asian collectivism with authoritarian stagnation) more than it reflected historical evidence.

The simulation does not take a position on the contested historical sociology. It uses the crop-to-culture seed as one input into an initial condition, calibrated so that the macro-level patterns it produces are consistent with the historical data the simulation is trained against. If the crop-culture seed were removed — if all polities started at the culture-space center regardless of crop type — the simulation would produce less geographic variation in cultural development trajectories, and the calibration against historical macro-patterns would be worse.

Whether the specific mechanism Wittfogel proposed is the real cause of that geographic variation is a question the simulation cannot answer. The simulation uses the finding without endorsing the mechanism.

---

*Wittfogel, K.A. (1957).* Oriental Despotism: A Comparative Study of Total Power. *Yale University Press.*
*Almond, G. & Verba, S. (1963).* The Civic Culture: Political Attitudes and Democracy in Five Nations. *Princeton University Press.*
*Bentzen, J.S., Kaarsen, N. & Wingender, A. (2017). "Irrigation and Autocracy."* Journal of the European Economic Association *15(1): 1—53.*
