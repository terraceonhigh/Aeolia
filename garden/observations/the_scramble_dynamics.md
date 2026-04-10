# The Scramble Dynamics

*On how resources become strategic, how scrambles emerge, and why they accelerate the transition to collapse or hegemony.*

---

The simulation models resources as passing through three thresholds: Detection (geology identifies the resource), Exploitation (tech-gated extraction becomes profitable), and Strategic Valuation (event-triggered recognition that the resource has military-strategic implications). The first two thresholds are gradual and tech-dependent. The third is sudden and competitive.

The Strategic Valuation threshold is where the scramble begins.

---

## How Strategic Valuation Works

Before Strategic Valuation fires, naphtha is a bulk energy resource: extractable, tradeable, useful, but not distinctively valuable compared to other caloric and energy sources. It appears in commercial tables as one resource among many.

Strategic Valuation fires when total consumption crosses a threshold — when the simulation recognizes that this resource is now central to industrial-era energy production and military-industrial capability. Once Strategic Valuation fires for naphtha, the resource becomes the subject of active competition. Polities that control substantial naphtha stocks suddenly have an asset that rivals want to deny them; polities that lack naphtha stocks suddenly face a strategic vulnerability they had not previously needed to address.

The transition from "useful resource" to "strategic resource" is not gradual. It is punctuated. The simulation models this as an event, not a drift: the scramble fires, the targeting bonuses change, the competition reorients. Real-world equivalents include the moment when petroleum became militarily essential (approximately the 1910s, when navies converted from coal to oil), the moment when uranium became strategically irreplaceable (approximately 1945), and the moment when certain rare earth elements became indispensable for electronics production (approximately the 2000s).

---

## The Naphtha Scramble: Tech ~5

The naphtha scramble fires at approximately tech 5 — the industrial era threshold. At tech 5, fossil fuel extraction becomes the primary energy driver of industrial production; the energy-to-TFP multiplier begins to differentiate sharply between naphtha-rich and naphtha-poor polities.

The scramble has a predictable geographic structure. Naphtha stocks are geographically concentrated: a small number of archipelagos hold the majority of the C stock. This concentration is a feature of the simulation's world generation algorithm (reflecting the historical concentration of petroleum deposits in geological basins) and produces the characteristic scramble pattern: a rush by industrial-era polities to control the concentrated deposits before rivals do.

The scramble produces a specific expansion bonus for polities whose naphtha fraction falls below the threshold: `naphtha_desire_mult` increases their targeting probability for naphtha-bearing archipelagos. The expansion is not neutral — it is specifically oriented toward resource control, with secondary consequences for the populations of the contested territories.

Le Billon (2012) documented the political economy of resource scrambles in the historical record: concentrated, lootable resources in geopolitically peripheral locations produce a distinct pattern of conflict — intense competition over specific sites rather than broad territorial control — with above-average civilian harm in the contested zones. The simulation captures the competition intensity but not the differential harm pattern; all territorial contests use the same expansion mechanic regardless of their resource motivation.

---

## The Pyra Scramble: Tech ~8

The pyra scramble fires later and harder. By tech ~8, polities approaching nuclear capability recognize that pyra — the nuclear-grade fuel analog — is the limiting resource for weapons development. The scramble for pyra is structurally similar to the naphtha scramble but more concentrated in time (the nuclear transition is faster than the industrial transition) and higher in strategic stakes (pyra enables the Dark Forest capability).

The pyra scramble interacts with the military-industrial complex resource curse (§11). Polities that control large pyra fractions — and thus win the strategic scramble — develop the institutional pathologies of the resource curse at the precise moment when institutional quality matters most for the nuclear transition. The winners of the pyra scramble are, on average, institutionally weaker than the polities that were forced to build nuclear capability without relying on pyra resource capture.

This produces the counterintuitive pattern documented in `seven_structural_ironies.md`: the polity with the largest pyra advantage entering the tech 8–9 transition often exits it institutionally weaker than the polity that had to compensate for resource scarcity through trade-derived surplus and technological investment. The pyra scramble produces the nuclear capability; it also produces the institutional deficit that the Strange Peace era will need to manage.

---

## The Scramble as Prisoner's Dilemma

Both scrambles — naphtha and pyra — have the structure of a prisoner's dilemma. Each individual polity has incentive to scramble regardless of what rivals do: if rivals scramble and you don't, you end up resource-poor in an era when the resource is strategically essential. If rivals don't scramble and you do, you capture an advantage. The dominant strategy, in the absence of coordination, is to scramble.

The aggregate result of all polities following the dominant strategy is what Kennedy (1987) called "imperial overextension": each polity, rationally pursuing resource control, acquires more territory than it can profitably administer, triggering maintenance costs that accelerate the desperation cascade and the institutional degradation the resource curse produces.

The scramble is not a mistake. It is the rational response to a competitive structure that makes not-scrambling strategically dangerous. The harm comes not from individual irrationality but from the collective action problem that the concentrated, strategic resource creates.

Whether the scramble could be avoided through coordination — through a multilateral resource-sharing agreement analogous to the Strange Peace's mutual deterrence — is the unanswered question that the simulation poses. The Strange Peace solves the nuclear-era prisoner's dilemma through the deterrence equilibrium. Nothing equivalent exists for the naphtha or pyra scrambles, which occur before the deterrence constraint is established. The scramble era is, in the simulation's history, the least coordinated and most destructive period of the pre-DF competition.

---

## What the Simulation Does Not Model

The three-threshold model captures the punctuated character of strategic valuation — the sudden shift from ordinary resource to contested strategic asset — but does not model the information dynamics that precede it.

In real-world resource scrambles, the scramble often begins before Strategic Valuation formally fires, because individual actors recognize the resource's potential before collective recognition catches up. The oil interests that were drilling in Persia before the Admiralty converted the fleet to oil, the uranium prospectors who were already at work in the Belgian Congo before Trinity — these actors had private information about the resource's strategic potential that produced early-mover advantages.

The simulation applies Strategic Valuation simultaneously to all polities at the threshold crossing. There is no private-information advance scramble, no first-mover advantage from recognizing the resource's potential before rivals. This is a simplification that smooths over one of the most historically interesting features of resource competition: the advantage of correct early recognition.

---

*See also: the_resource_curse.md (how strategic resource control degrades institutions); the_strange_equilibrium.md (the approach-to-parity period when pyra scramble peaks); the_growth_machine.md (how energy resources couple to TFP)*

*Le Billon, P. (2012).* Wars of Plunder: Conflicts, Profits and the Politics of Resources. *Columbia University Press.*
*Kennedy, P. (1987).* The Rise and Fall of the Great Powers. *Random House.*
*Westing, A.H. (1986).* Global Resources and International Conflict. *Oxford University Press.*
*Ross, M. (2012).* The Oil Curse. *Princeton University Press.*
