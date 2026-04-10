# The Culture-Allocation Link

*On how culture position translates to economic behavior — the output side of the culture engine.*

---

The culture engine (`the_culture_engine.md`) documents how polities move through the 2D culture space. This observation documents what the culture space position actually does: how position on the CI (Collective↔Individual) and IO (Inward↔Outward) axes translates to economic and expansionist behavior.

The translation happens through two functions: `_sharesFromPos`, which determines how a polity divides its energy surplus among expansion, tech investment, and sovereignty consolidation; and `_A0FromPos`, which determines the polity's baseline TFP (total factor productivity). Both are linear functions of culture position, normalized to [0, 1] from the [-1, 1] culture space.

---

## The Allocation Shares Formula

`_sharesFromPos(pos)` returns three normalized shares: expansion, tech, and consolidation.

```
individual = (CI + 1) / 2       ∈ [0, 1]
outward    = (IO + 1) / 2       ∈ [0, 1]

expS = base_expansion + outward_expansion_coeff × outward + individual_expansion_coeff × individual
tecS = base_tech       + outward_tech_coeff       × outward
conS = max(0.05, 1 - expS - tecS)
```

The implications by culture type:

**Outward-Individual (nori/emmer, maritime civic):** High outward drives both expansion (exploration, trade-route extension) and tech investment (learning-by-contact); high individual drives expansion further and boosts TFP. These polities are simultaneously more aggressive in expansion and more productive per unit of energy — the Civic culture archetype.

**Inward-Collective (paddi, hydraulic bureaucratic):** Low outward reduces both expansion willingness and tech investment through contact; low individual reduces TFP. These polities consolidate more — they spend a larger share of energy on sovereignty maintenance of existing territory — but grow their territorial and technological position more slowly. The consolidation share is the residual after expansion and tech are determined; inward-collective polities consolidate by default.

**Foraging (no primary crop):** Starting position near center; behavior is malleable and shifts quickly in response to prosperity or crisis. These polities can end up anywhere in the culture space depending on their early material circumstances.

---

## The TFP Formula

`_A0FromPos(pos)` returns the baseline A₀ for the growth formula:

```
A₀ = base_A0 + individual_A0_coeff × individual + outward_A0_coeff × outward
```

Both axes boost TFP, but for different reasons. The individual coefficient encodes the Putnam/Inglehart finding that civic individualism correlates with higher productive innovation — the diffuse social trust and competitive dynamism of market-oriented cultures produces more efficient resource use. The outward coefficient encodes the Romer/endogenous-growth finding that exposure to external knowledge and trade networks accelerates innovation — even absent individualism, outward-oriented polities that engage actively in the trade network learn from their partners.

The combination of the two axes produces the simulation's TFP distribution: the highest-A₀ polities are those with both high individual and high outward orientation (the maritime civic cultures); the lowest-A₀ polities are those with low individual and low outward (the inward collective cultures). The difference is substantial — at typical parameter values, the gap between maximum and minimum A₀ is approximately 2× — and it compounds over time through the tech growth formula.

---

## The Academic Grounding

The culture-allocation link operationalizes three related traditions in the social science literature on culture and economic performance.

**Putnam (1993):** *Making Democracy Work* documented the correlation between civic culture (social trust, horizontal association, participation in civic life) and economic development across Italian regions. The northern Italian regions with high social capital — outward, civic, individually accountable — consistently outperformed the southern regions with Banfield's (1958) "amoral familism" (inward, collectivist within the family unit only, distrustful of strangers). The simulation encodes this as the IO axis: outward orientation captures the trust-in-strangers that enables trade and civic cooperation; inward orientation captures the closed networks that Banfield identified as economically limiting.

**Inglehart (1997, 2018):** *Modernization and Postmodernization* and *Cultural Evolution* documented the cross-national correlation between survival values (collectivist, inward, authoritarian, religious) and self-expression values (individualist, outward, secular, innovative) with economic development levels. Inglehart treated the correlation as evidence of a developmental sequence — societies become more individualist and outward as they become more prosperous — and the simulation models this as a dynamic by making prosperity one of the drift terms in the culture engine.

**Banfield (1958):** *The Moral Basis of a Backward Society* provided the negative-case archetype. Banfield's "amoral familism" — maximize short-term material interest of the nuclear family, assume all others do the same — produces economic stagnation because it makes cooperation beyond the family impossible. In the simulation, this maps to the inward-collective culture's consolidation focus and reduced outward expansion: the polity that doesn't trust neighbors doesn't trade with them, doesn't learn from them, and spends resources maintaining existing sovereignty rather than building new partnerships.

---

## Known Limitations

The allocation formula is linear. An increase in outward orientation produces the same expansion-share increase regardless of where you start in the culture space. This is a simplification — real culture-behavior relationships likely have threshold effects (the shift from amoral familism to civic culture isn't continuous) and interaction effects (individual orientation matters differently in collective vs. market societies). A non-linear mapping would capture more of the Putnam/Inglehart pattern but would require additional calibration and reduce interpretability.

The A₀ formula is also linear and additive. In reality, individual and outward orientations likely interact multiplicatively — a polity that is both highly individualist and highly outward is more than additively productive relative to a polity that is only one or the other. The current formula, which treats the two axes as independent contributors, understates the synergy between civic trust (outward) and individual innovation (individual) that the endogenous growth literature documents.

The consolidation share is a residual rather than an explicit preference. In the simulation, polities don't "choose" to consolidate; they consolidate because expansion and tech investments don't use up all the budget. A more sophisticated implementation would model consolidation investment as a positive choice driven by sovereignty security concerns, with distinct cultural correlates.

---

*See also: the_culture_engine.md (how culture position drifts); the_crop_culture_seed.md (how culture position is initialized); the_growth_machine.md (how A₀ and shares_mult enter the tech growth formula)*

*Putnam, R. (1993).* Making Democracy Work: Civic Traditions in Modern Italy. *Princeton University Press.*
*Inglehart, R. (1997).* Modernization and Postmodernization. *Princeton University Press.*
*Inglehart, R. (2018).* Cultural Evolution: People's Motivations Are Changing, and Reshaping the World. *Cambridge University Press.*
*Banfield, E. (1958).* The Moral Basis of a Backward Society. *Free Press.*
