# The Inclusive Extraction Paradox

*On why even the best institutions accumulate extractiveness when they run empires, and what that implies about the limits of structural prediction.*

---

The simulation had a bug. The bug was also a theory.

The original extractiveness accumulation formula gated buildup on `(1.0 - inclusiveCulture)`: a polity with a civic, outward-facing culture — the kind of polity that scores high on the Putnam index, that builds transparent contract enforcement, that invests in public goods — would accumulate extractiveness at a near-zero rate, even while governing conquered territory and extracting surplus from it.

The theory embedded in the formula was this: inclusive institutions prevent extractive behavior. A civic culture, because it has institutional mechanisms for accountability and reform, does not develop the rent-seeking patterns that produce institutional lock-in. The Acemoglu-Robinson framework predicts this: inclusive institutions produce inclusive outcomes; extractive institutions produce extractive outcomes; the two do not mix.

The playtester who found the bug — Yetunde Afolabi, working from an institutional economics perspective — pointed out that this is not what AJR actually says.

---

## What AJR Actually Says

Acemoglu, Johnson, and Robinson's argument in *Why Nations Fail* (2012) is not that inclusive institutions prevent extraction. It is that inclusive institutions create the conditions for broad-based economic growth *in the polity that has them*. The argument is about domestic institutional quality, not about how that polity behaves toward others.

A polity with inclusive domestic institutions can — and historically did — run extractive empires abroad. The British East India Company operated under the authority of a Parliament that was, by the standards of its time, one of the more inclusive legislative bodies in the world. The Dutch VOC was chartered by a Republic. The Belgian Congo was administered by one of the more liberal constitutional monarchies in Europe.

The inclusive institutions that produced accountability at home did not prevent extraction abroad. In some cases, they facilitated it: the transparency and contract enforcement that made domestic commerce efficient also made colonial extraction more *systematically* profitable. The inclusive institution was an excellent machine for organizing extraction at a distance. It simply did not direct that extraction's effects back toward the extracting polity's own institutional health — or rather, it did, but slowly and through channels that the original institutional designers did not anticipate.

The bug in the formula was treating inclusive_culture as a gate on accumulation. The fix separates the two channels: accumulation fires at a base rate whenever excess extraction > 0, regardless of culture. Culture gates the *decay rate* — inclusive polities reform faster, not because they don't extract, but because their institutional mechanisms for self-correction are more responsive.

This is a meaningful distinction.

---

## The Paradox in Practice

Run the simulation with the corrected formula and watch what happens to a civic/outward polity that acquires a large territorial empire.

In the relay and early administered eras, its extractiveness stays low. The empire is small; extraction is modest; the inclusive decay rate keeps up with the trickle of accumulation. The Putnam thesis holds: civic culture produces institutional health.

In the late administered era, the polity controls fifteen or twenty archipelagos. Extraction is no longer modest. Every peripheral holding generates excess extraction above the tolerable threshold. Fifteen trickles become a stream. The decay rate — still operating, still responsive to the polity's civic culture — cannot keep pace. Extractiveness begins to accumulate.

The polity's domestic institutions are still inclusive. Its universities still publish. Its arbitration panels still function. Its commerce is still transparent. But its peripheral administration is developing the rent-seeking patterns, the captured local elites, the infrastructure oriented toward extraction rather than development, that AJR identified as the signature of extractive institutions.

The inclusive polity is becoming extractive in its periphery while remaining inclusive in its core.

This is the British Empire. It is also the Dutch Empire, the French Empire, the American informal empire of the Cold War period. The paradox is not that inclusive polities behave badly. It is that empire itself is an extractive act, and no domestic institutional quality can prevent the extractive logic of empire from manifesting in the relationship between core and periphery.

---

## What the Simulation Cannot Model

The simulation captures the accumulation and the decay. It does not capture the feedback from periphery to core.

In the historical record, the extractive institutions that inclusive polities built abroad eventually affected domestic institutional quality. The British "gentlemanly capitalism" that Cain and Hopkins (1993) documented — the financialization of the British economy around imperial revenue streams — was a domestic institutional change driven by the profitability of extraction abroad. The Dutch "VOC mentality" that historians of the Netherlands identify as a factor in the Republic's economic decline was a domestic cultural shift produced by the institutional patterns of colonial commerce.

The simulation's extractiveness index lives at the polity level. It does not distinguish between the institutional health of the core and the institutional health of the periphery. A polity with extractiveness = 0.4 is 0.4 everywhere. In practice, the historical pattern is more differentiated: extractiveness concentrated in the periphery, with slow seepage back to the core through the financial and administrative channels that connected them.

Modeling this would require a per-territory extractiveness index — each island carrying its own institutional history, its own accumulated lock-in, its own relationship to the administering core. The simulation is not architected for this level of granularity. But the observation stands: the mechanism that the corrected formula captures (inclusive polities accumulate extractiveness when they extract) implies a feedback channel (extraction abroad degrades institutions at home) that the simulation does not yet represent.

---

## The Structural Limit

This is, I think, the observation about the simulation that the garden has been circling without quite stating directly.

The simulation's structural logic is powerful. It produces the Organski transition, the Snyder paradox, the Innis trap, the AJR reversal, the Weber reform dividend. It produces them from parameter interactions without being told to. This is genuinely remarkable.

But the structural logic has a boundary. It explains why systems develop the way they do up to the point where the systems begin generating second-order effects that feed back into the parameters that generated them.

The inclusive extraction paradox is an example. The simulation can model a civic polity becoming extractive. It cannot model the extractiveness feeding back to degrade the civic culture that was supposed to prevent it. The feedback loop is there in the historical record — it is the entire story of how democratic empires became less democratic — but it requires the simulation to allow its own parameters to be endogenous rather than exogenous.

The strange equilibrium has a similar boundary. The simulation can model deterrence producing stability. It cannot model stability producing institutional innovation that changes the terms of deterrence. The Commerce Council at Year 98 SP is building institutions that the deterrence equilibrium made possible but that the deterrence model does not predict. The institutions are endogenous to the system, not to the simulation.

This is not a deficiency to be fixed. It is a boundary to be understood. The simulation is a thought experiment, not a predictive model. Its value is not that it gets everything right but that it gets enough right to make the boundaries visible.

The inclusive extraction paradox makes one boundary visible: the boundary between what structural logic can predict about institutions and what happens when institutions start acting on the structures that created them.

---

*The Vaanthi are free. Their institutions are not.*
*The Reach is inclusive. Its empire is not.*
*The paradox is the same in both directions.*

---

*Acemoglu, D., Johnson, S. & Robinson, J. (2001). "The Colonial Origins of Comparative Development." American Economic Review 91(5).*
*Acemoglu, D. & Robinson, J. (2012). Why Nations Fail. Crown.*
*Cain, P.J. & Hopkins, A.G. (1993). British Imperialism: Innovation and Expansion, 1688–1914. Longman.*
*Putnam, R.D. (1993). Making Democracy Work. Princeton University Press.*
*Scott, J.C. (1985). Weapons of the Weak. Yale University Press.*
