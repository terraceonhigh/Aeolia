# The Environmental Shocks

*On crop failure, fishery depletion, and the commons problem at civilizational scale.*

---

The simulation's energy budget is not constant. Two environmental mechanics introduce stochastic variation into the caloric supply that polities depend on: crop failure events, which temporarily reduce agricultural yield; and fishery depletion, which permanently reduces the marine caloric supplement until stock recovery occurs.

These two mechanics draw from different theoretical traditions and have different structural properties. Crop failure is episodic and recoverable; fishery depletion is cumulative and self-accelerating until the stock collapses. Together they model the two characteristic ways that environmental constraints have historically disrupted civilizational development: the acute, recoverable shock (drought, frost, flooding) and the chronic, extractive depletion (the tragedy of the commons).

---

## Crop Failure

The simulation's crop failure mechanic fires probabilistically each tick, independently per polity. The failure probability is tech-dependent: pre-industrial polities (tech < 5) face higher failure probability because they lack the storage, distribution, and agronomic knowledge to buffer against harvest variation. Industrial polities (tech ≥ 5) have developed these buffers — grain storage, irrigation, crop varieties resistant to climate variation, international trade to substitute for local shortfall — and face substantially lower failure probability.

When crop failure fires, the polity's agricultural yield for that tick is multiplied by a failure modifier (`cropFailureModifier[]`), which reduces yield by 20–60% depending on severity. Recovery is gradual: the modifier returns toward 1.0 at +0.25 per tick (recovering over two to four ticks from a severe failure event).

The historical grounding is a straightforward empirical finding: pre-industrial agrarian societies experienced crop failures regularly, and those failures were among the primary drivers of short-term mortality and long-term demographic instability. Le Roy Ladurie's *Times of Feast, Times of Famine* (1967) documented the millennia-long oscillation of European harvests. Mike Davis's *Late Victorian Holocausts* (2001) documented how El Niño-driven crop failures in the late 19th century interacted with colonial extraction to produce mass mortality on a scale comparable to the Black Death.

The Davis finding is now partially implemented (2026-04-09): when crop failure fires, the failure modifier is amplified by the controlling polity's `extractiveness` index. At maximum extractiveness, the modifier is 30% worse than baseline — so a polity with extractiveness=1.0 retains only 70% as much yield as the base failure modifier would produce. The amplification parameter is `davis_amplification` (default 0.30) in SimEngine.js.

What remains unimplemented is Davis's recovery-side finding: extractively administered territories also have worse distribution infrastructure, meaning recovery from failure takes longer. The simulation's uniform +0.25/tick recovery rate applies regardless of administrative quality. This secondary gap means the simulation captures Davis's severity amplification but not his persistence amplification — extractive administration in Aeolia makes failures deeper but not slower to resolve.

---

## Fishery Depletion: The Commons Problem

The fishery depletion mechanic is structurally different from crop failure in a way that matters for the simulation's long-run dynamics.

Each polity's `fisheryStock[]` — the population of harvestable fish in its coastal waters — follows a stock-and-flow equation: natural recovery at 8% per tick, reduced by extraction proportional to the polity's coastal population and fishing activity. When the extraction rate exceeds the recovery rate, stock declines. When stock falls below a threshold, fish yields collapse and do not recover until the stock rebuilds.

This is the mathematical structure of the tragedy of the commons, as Garrett Hardin (1968) formalized it: a shared resource with natural recovery capacity, subject to extraction by multiple users who each have incentives to extract more than their share of the sustainable yield, with the aggregate result of overextraction and stock collapse.

The historical record of fishery collapses is extensive. The North Atlantic cod fishery, the California sardine fishery, the Peruvian anchovy fishery — each followed the same basic trajectory: rapid expansion of extraction capacity in response to apparent abundance, followed by stock collapse when extraction persistently exceeded recovery capacity. The collapses were not mysterious; the biology of stock-and-flow was well understood. They occurred because the institutional mechanisms for constraining extraction to sustainable levels were absent, inadequate, or not enforced.

Elinor Ostrom's 1990 work on governing the commons documented the conditions under which communities have successfully maintained shared resources: clear boundaries, rules matched to local conditions, collective-choice arrangements, monitoring, graduated sanctions, conflict resolution mechanisms. The simulation does not model these conditions; it models the failure mode (extraction without governance, leading to collapse) as the default. This is historically accurate for most pre-modern fisheries; it overstates the depletion rate for communities that developed effective commons governance.

---

## How the Two Mechanics Interact

Crop failure and fishery depletion interact through the energy budget. Both reduce the total caloric supply; the desperation cascade fires when total supply falls below the maintenance threshold. But they interact differently with the polity's strategic response.

Crop failure is known to be temporary. A polity experiencing crop failure has some expectation that the failure will resolve — the recovery rate is predictable. The rational response is to draw down reserves, reduce consumption, and wait. The simulation models this through the slow convergence of the failure modifier back to 1.0.

Fishery depletion is cumulative and self-reinforcing. A polity that has depleted its fishery stock is not experiencing a temporary shortfall; it is experiencing a permanent reduction in caloric capacity until the stock recovers (which, at 8% recovery per tick, can take many ticks from a severe depletion). The caloric loss from fishery depletion compounds the Malthusian ceiling reduction described in `the_malthusian_clamp.md`: a polity that simultaneously faces crop failure and fishery depletion may find its total caloric supply well below the subsistence floor, triggering both the Malthusian mortality mechanic and the desperation cascade.

For coastal polities that derive a significant fraction of their calories from fisheries — particularly nori and sthaq-rich polities that built their Boserupian release partly on marine calories — fishery depletion is potentially catastrophic in ways that crop failure alone is not. Fishery depletion removes a structural component of the caloric base; crop failure reduces it temporarily. This asymmetry is one reason why historically aggressive expansion of fishing capacity has been so reliably followed by collapse: the short-term caloric gain from over-fishing accelerates population growth and commercial development, and the eventual stock collapse removes the caloric foundation that those developments were built on.

---

## What Neither Mechanic Models

Both mechanics model supply-side shocks without modeling the demand-side responses that historical societies developed to buffer against them.

Real pre-industrial societies developed a range of buffers against crop failure: grain storage systems, communal redistribution of surpluses, diversification of crop types, selection of low-yield but high-variance-tolerance varieties for subsistence plots. These buffers reduced the mortality impact of harvest variation without eliminating it. The simulation's crop failure mechanic applies a uniform yield shock without differentiating between polities with good buffering capacity and polities with poor buffering capacity.

Real pre-industrial fishery communities developed a range of commons governance mechanisms: territorial fishing rights, seasonal closures, gear restrictions, community monitoring of stock health. These mechanisms reduced depletion rates below what pure open-access extraction would produce. The simulation's fishery depletion mechanic models open-access extraction without differentiating between polities with commons governance and polities without it.

Both gaps point in the same direction: the simulation underestimates the variability in how environmental shocks translate into demographic and economic impacts, based on the quality of existing institutional buffers. This is consistent with the broader pattern in the simulation's institutional mechanics — the AR extractiveness index captures some institutional quality variation, but the environmental shock mechanics are relatively institution-blind.

A model that incorporated institutional buffers for environmental shocks would produce less uniform shock impacts and more differentiated developmental trajectories. It would also require substantially more state variables and calibration work.

---

*See also: the_malthusian_clamp.md (how energy shortfall caps population through the Malthusian clamp); the_desperation_trap.md (how severe energy shortfall triggers the cascade)*

*Hardin, G. (1968). "The Tragedy of the Commons."* Science *162(3859).*
*Ostrom, E. (1990).* Governing the Commons: The Evolution of Institutions for Collective Action. *Cambridge University Press.*
*Davis, M. (2001).* Late Victorian Holocausts: El Niño Famines and the Making of the Third World. *Verso.*
*Le Roy Ladurie, E. (1967).* Times of Feast, Times of Famine: A History of Climate Since the Year 1000. *Doubleday.*
