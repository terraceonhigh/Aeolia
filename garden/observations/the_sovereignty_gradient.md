# The Sovereignty Gradient

*On what the sovereignty parameter actually measures, and why its spatial distribution tells you more than any single value.*

---

The sovereignty parameter in `sim_proxy_v2` is not sovereignty in the political theory sense — it does not mean formal independence or recognized statehood. It is a continuous measure of institutional integration between a controlled territory and its controlling core. A sovereignty value of 0.95 means the territory is essentially self-governing within its polity's framework. A value of 0.15 means it is a fresh conquest being actively extracted with minimal institutional infrastructure. Everything between is a spectrum.

The spectrum has named thresholds in the simulation: below 0.3 is "colony," 0.3–0.6 is "client" or "garrison" (depending on culture), above 0.6 is increasingly autonomous. But these labels are descriptive, not causal. The mechanics that move sovereignty up and down do not care about the labels. They care about the extraction/recovery balance.

---

## The Extraction/Recovery Balance

Sovereignty at island *i* changes each tick by the net of two forces:

**Extraction** pulls sovereignty down. It is proportional to `sov_extraction_decay`, inversely proportional to distance from core, and amplified by two factors: energy ratio (richer polities extract more efficiently) and piety (high-piety polities integrate faster through religious conversion — the Abbasid/Ottoman centripetal force model). Player sovereignty focus reduces extraction by 60%.

**Recovery** pushes sovereignty up. It is proportional to existing sovereignty (a bootstrapping effect — some institutional base is needed to build more), to the ratio of local population to core population (larger populations resist more effectively), and to the grievance-resistance multiplier (Scott's weapons of the weak).

The balance between these two forces determines whether a territory is being consolidated or degraded. The key structural insight: extraction is distance-dependent but recovery is not. Territories close to the core are extracted more intensely but also consolidate faster (because the core's institutional presence is stronger). Distant territories are extracted less intensely but also recover more slowly.

This produces the sovereignty gradient: a spatial pattern where sovereignty decreases with distance from the core, with the steepest gradient in the first ring of controlled territory and a flattening toward the periphery. The pattern is not linear — it has the shape of a logistics curve, compressed at both ends and steepest in the middle — because the multiplication of distance effects in both extraction and recovery creates a nonlinear equilibrium.

---

## What the Gradient Tells You

A polity's sovereignty gradient is a diagnostic for its institutional health.

**Steep gradient, high core:** A polity that has consolidated its core territory but is actively expanding. The core is well-integrated; the periphery is under extraction. This is the typical mid-game profile of a successful expanding polity — it has the institutional base to govern itself and the extractive infrastructure to run an empire. The gradient steepness tells you how much the empire depends on extraction from the periphery for its energy budget.

**Flat gradient, low everywhere:** A polity in institutional crisis. Core sovereignty has been degraded by conflict, schism, or the desperation cascade. When the core isn't consolidated, the periphery can't be either. This profile often precedes territorial breakup — the schism mechanic fires when peripheral sovereignty drops below 0.45 in enough holdings.

**Flat gradient, high everywhere:** The rare late-game profile of a polity that has stopped expanding and spent several hundred simulation-years consolidating. All its territory is well-integrated. This is the profile the Strange Peace enables: by freezing expansion between hegemons, it gives both hegemons time to consolidate their holdings. The 0.015/tick sovereignty boost after year -200 at tech ≥ 9 accelerates this process — the simulation's encoding of the observation that nuclear-era great powers invested in institutional depth because they could no longer invest in territorial breadth.

**Inverted gradient:** Peripheral sovereignty higher than core. This can happen after a successful schism: the newly independent territory starts with low sovereignty (0.04–0.08) but recovers quickly because it has no empire to maintain. Meanwhile the parent polity's core may be degraded from the crisis that triggered the schism. The inversion is temporary — within a few ticks the normal gradient reasserts itself — but it represents the window during which the post-schism polity is institutionally more coherent than the empire that lost it.

---

## The Wallerstein Connection

The sovereignty gradient is the simulation's version of Wallerstein's core-periphery-semiperiphery hierarchy, rendered as a continuous variable rather than a categorical assignment.

Wallerstein (1974) argued that the capitalist world-system produces three structural zones: core states that dominate exchange relationships, peripheral regions that are dominated, and semiperipheral states that occupy an intermediate position — both exploiting the periphery and being exploited by the core. The zones are defined by their position in exchange relationships, not by their geographic location or intrinsic characteristics.

The simulation encodes this as the sovereignty gradient within each polity: the core island is the extracting center (highest sovereignty, lowest grievance); the periphery is the extracted territory (lowest sovereignty, highest grievance); and the intermediate holdings — the "semiperiphery" — are territories with enough institutional integration to resist full extraction but not enough to resist being integrated.

The simulation's semiperiphery is not a fixed zone. It moves as the polity expands or contracts. When a polity conquers new territory, the old periphery becomes the new semiperiphery (its sovereignty has partially recovered; it is no longer the most-extracted territory). When a polity loses territory to schism, its semiperiphery may become the new periphery (fewer holdings to share the extraction burden).

This is consistent with Wallerstein's argument that semiperipheral status is a structural position, not an intrinsic characteristic. The same archipelago can be core, semiperiphery, or periphery depending on what polity controls it and what the sovereignty gradient looks like at that moment.

---

## The Sovereignty Focus Decision

The player's sovereignty focus mechanic — selecting islands for reduced extraction — is a decision about the gradient's shape. Focusing on a peripheral island pushes its sovereignty up faster (60% extraction reduction), which reduces grievance accumulation and schism risk. But it also reduces the energy extracted from that island, which reduces the polity's total energy budget.

The strategic question is: which shape of gradient do you want?

A steep gradient generates more energy (high extraction from periphery) but more schism risk. A flat gradient generates less energy but more stability. The optimal gradient depends on the game state: during expansion, you want energy (steep gradient); during consolidation, you want stability (flat gradient); during the Strange Peace, you want depth (high everywhere).

This is the player's version of the institutional trade-off that the simulation models for AI polities automatically. The AI doesn't get to choose which islands to focus. Its gradient is determined by the mechanical balance of extraction and recovery. The player can override this — and the choice is one of the deepest strategic decisions in the game.

---

*See also: the_legibility_problem.md (how the administering power sees the periphery); the_lock_in_mechanics.md (how extractiveness accumulates along the gradient); the_grievance_accumulation.md (Scott's resistance mechanic in the recovery term)*

*Wallerstein, I. (1974).* The Modern World-System I: Capitalist Agriculture and the Origins of the European World-Economy in the Sixteenth Century. *Academic Press.*
*North, D.C. (1990).* Institutions, Institutional Change and Economic Performance. *Cambridge University Press.*
*Scott, J.C. (1985).* Weapons of the Weak: Everyday Forms of Peasant Resistance. *Yale University Press.*
