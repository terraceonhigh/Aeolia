# The Strange Equilibrium

*On what the Dark Forest firing produces, and the deterrence-stability-instability paradox that follows.*

---

The Dark Forest event is not the end of something. It is the beginning of a new regime.

Before the Dark Forest fires, the simulation's world is organized around one primary dynamic: expansion. Polities grow or decline based on their energy budgets and their capacity for territorial consolidation. The dominant strategic question is: who will be large enough and capable enough to reach nuclear capability first?

After the Dark Forest fires — after two polities have detected each other as nuclear-capable peers — the simulation's world reorganizes around a different dynamic: deterrence. The dominant strategic question becomes: given that direct conflict is survivable for neither hegemon, how do both hegemons continue to compete?

The answer the simulation produces has a name in real-world strategic studies: the stability-instability paradox.

---

## The Deterrence Equilibrium

The Dark Forest mechanic establishes mutual nuclear awareness between the two hegemons. Once both polities know the other is nuclear-capable, the expansion targeting penalty for the hegemon pairing is set to −12.0. This is strong enough to effectively rule out direct military conflict between the two hegemons for the rest of the simulation. Neither hegemon will willingly target the other's controlled territory.

This is the "stable" part of the stability-instability paradox. Nuclear deterrence works. It prevents the direct large-scale warfare that would otherwise be the natural conclusion of the competition between two polities at the top of the tech distribution. The Strange Peace is real: the hegemons do not fight each other.

Glenn Snyder (1965) named the paradox: deterrence at the nuclear level creates instability at the sub-nuclear level. Because both hegemons know that neither can use nuclear weapons against the other, both hegemons are free to compete aggressively through conventional means — proxy conflicts, commercial competition, expansion into non-nuclear territory — without fearing escalation to the catastrophic level. The nuclear threshold that prevents the worst outcome also caps the expected cost of sub-nuclear aggression, which makes sub-nuclear aggression more attractive than it would be without the nuclear threshold.

The simulation encodes this: after DF fires, hegemons receive a +3.0 expansion bonus targeting non-nuclear territory in the rival hegemon's contact network. They are simultaneously constrained from fighting each other (−12.0) and incentivized to compete in each other's periphery (+3.0). The cold war period — the competition in the shadow of deterrence — is not peaceful; it is a reconfiguration of conflict from direct to indirect.

---

## The Arms Race

The deterrence equilibrium also does not mean the hegemons stop developing. The arms race continues after DF fires.

The post-DF tech growth bonus for hegemons at tech > 8.5: `if tech > 8.5 and is_hegemon: delta_tech *= arms_race_mult`. The arms race bonus applies in both directions — both hegemons are rewarded with accelerated tech growth by the competitive pressure of the standoff. Neither can afford to stop; if one slows its tech development and the other continues, the deterrence balance shifts.

This is Kenneth Waltz's point in his 1981 analysis: "more may be better." In one reading, nuclear proliferation to two polities is actually more stable than single-hegemon dominance, because single-hegemon dominance eliminates the deterrence constraint and leaves only one polity capable of unconstrained action. Mutual deterrence is, from the perspective of everyone who is not one of the two hegemons, a form of mutual constraint imposed by both parties on themselves — a constraint that happens to benefit everyone else.

The arms race bonus is also self-limiting, through the delta cap: `delta_tech = min(delta_tech, 0.05)` per tick. The arms race accelerates development toward the ceiling; it does not produce runaway tech explosion. Both hegemons tend to converge toward the maximum achievable tech level and maintain approximate parity, because the arms race bonus is symmetric and both polities face the same ceiling.

The convergence is imperfect. If one hegemon had a significant tech lead at the time of DF firing, it tends to maintain some portion of that lead through the arms race period, because the bonus is multiplicative (applied to existing delta_tech) and a faster-developing hegemon produces a larger absolute bonus. This asymmetry in the arms race is one of the mechanisms that determines the simulation's endgame configuration: whether the Strange Peace is a genuinely balanced standoff or a deterrence equilibrium in which one hegemon is structurally more capable than the other.

---

## The Proxy Belt

The simulation's "proxy bonus" territory — the non-nuclear territory in the rival hegemon's contact network — has a characteristic geographic distribution. It tends to be:

- Higher-tech than uncontacted periphery (because it has been in contact with a major power's relay network)
- Lower-sovereignty than the hegemon's own core (because it has not been fully administered)
- Higher-grievance than the hegemon's own core (if it has been extracted by the first hegemon)

This produces the classic cold war geography: a belt of contested, partially-developed, strategically valuable territories that both hegemons want to influence but neither can directly control without risking the deterrence threshold. The competition in the proxy belt is not purely military — it also involves commercial relationships, cultural diffusion, and the piety absorption mechanic (missionary expansion into the proxy belt is one of the channels through which a high-piety hegemon competes in the stability-instability zone).

The simulation does not model the full range of proxy-competition instruments that historical cold wars produced (propaganda, economic aid, covert operations, arms transfers). The proxy bonus is a simplified targeting incentive, not a full model of influence competition. But the geographic pattern it produces — concentrated competition in the intermediate belt between the two hegemons' cores — is consistent with the historical geography of 20th century cold war proxy conflicts.

---

## Why Two Hegemons and Not Three

The simulation reliably produces exactly two nuclear hegemons, not one or three. This is a calibration feature, not an accident.

One hegemon is unstable: a single nuclear-capable polity faces no deterrence constraint and the simulation's subsequent history degenerates into unconstrained expansion. Calibration targets include the presence of a meaningful deterrence equilibrium, which requires at least two hegemons.

Three hegemons would require a three-way deterrence configuration: A is deterred from attacking B by B's second-strike capacity; A is deterred from attacking C by C's second-strike capacity; B and C are deterred from each other. This is technically possible, but the simulation's accel_rate table and energy budget parameters are calibrated so that tech 9 (nuclear capability) is reached by approximately two polities in a 200-tick run. Adding a third nuclear polity would require either a slower accel_rate (pushing DF later) or a higher tech ceiling for nuclear capability. Both would require recalibration.

There is also a structural argument: in the three-hegemon case, the stability-instability paradox produces more complex proxy dynamics — each hegemon competes in the periphery of two rivals simultaneously — and the arms race becomes triangular rather than bilateral. This may produce more realistic late-game dynamics, but it would require substantially more parameter tuning to produce coherent outcomes. The current calibration optimizes for a well-understood two-hegemon configuration.

---

## The Approach to Parity: Power Transition Before Dark Forest

The Dark Forest does not appear from nowhere. It is the endpoint of a power transition period — the simulation-decades when two proto-hegemons are racing toward nuclear capability from behind the cover of the industrial and pyra scrambles.

Organski (1958) and Gilpin (1981) identified the approach to parity as the most dangerous period in great-power relations, more dangerous than either the established hegemonic period (one dominant power, stable hierarchy) or the post-parity deterrence period (mutual capability, stable deterrence). The transition period — when the challenger is closing the gap but has not yet reached parity — is when preemptive war is most tempting to the declining hegemon: the window for successful preemption is closing, and the cost of waiting is an opponent who will eventually be as capable as you are.

The simulation's version of this period runs from approximately tech 7 (when pyra scramble begins and both proto-hegemons are acquiring strategic energy assets) to the DF firing point (when both have tech ≥ 9 and mutual awareness has accumulated to the threshold). This is approximately 8 ticks = 400 simulation-years. During this period:

The pyra military-industrial resource curse applies at tech ≥ 8.5 — polities controlling the largest shares of pyra stock receive a 60% resource curse penalty, reducing their TFP growth. This creates a counterintuitive dynamic: the polities scrambling hardest for strategic advantage simultaneously acquire the resource that penalizes their institutional development. The polity that wins the scramble acquires an early deterrence advantage and a late institutional disadvantage.

The nuclear peer awareness accumulates at 0.04/tick per side once both have tech ≥ 9. The 0.30 threshold is reached in approximately 7–8 ticks from when both cross the nuclear threshold. This 7-8 tick window is the simulation's most concentrated danger period — both sides have strategic capability, neither has formalized deterrence, and the awareness that would stabilize their relationship is still accumulating.

The simulation does not model preemptive war during this window. There is no mechanic for a nuclear first strike before deterrence is formalized; the DF firing either stabilizes the relationship or doesn't apply. This is consistent with how the historical Cold War unfolded (despite the Organski prediction, the United States did not launch preemptive war during the Soviet Union's approach to nuclear parity) but it is a gap: the simulation assumes that both proto-hegemons behave as if they understand the deterrence logic before the DF formally fires.

---

## The Long Equilibrium

The most striking feature of the post-DF simulation is that the Strange Peace is indeed strange: it endures.

The deterrence equilibrium, once established, does not degrade in a 10,000-year run that has 200 ticks to work through. The hegemons maintain approximate parity, continue competing in the proxy belt, and neither finds a path to eliminating the other. The nuclear ceiling creates a floor beneath which neither can be pushed.

This is the simulation's version of the observation that nuclear-armed great powers have not fought each other since 1945. The Strange Peace of the historical record has lasted approximately 80 years. The simulation's version lasts the remaining portion of the simulation, typically 1,000–2,000 simulation-years. The simulation may be overstating the durability of the deterrence equilibrium — it does not model the accident-and-miscalculation pathways that scholars like Scott Sagan (1993) document as real risks in nuclear deterrence systems — but the macro-level pattern (extended great-power peace under nuclear conditions) is what the calibration was designed to produce, and it produces it.

The Strange Peace is not just strange. It is, in the simulation's mechanics, load-bearing: the deterrence equilibrium is what allows the late-game political structures (the Sovereignty's Circuit Assembly, the Reach's Civil Cabinet) to develop the complexity they achieve, because those structures require long-term stability to accumulate institutional knowledge and legitimate governance. A world in which the two hegemons eventually fought a nuclear war would produce different institutions — or no institutions at all.

---

*See also: the_intermediate_belt_problem.md (Walt alignment in the proxy belt); the_lock_in_mechanics.md (how extractiveness changes through the deterrence period)*

*Snyder, G.H. (1965). "The Balance of Power and the Balance of Terror." In* Balance of Power, *ed. Paul Seabury. Chandler.*
*Waltz, K.N. (1981). "The Spread of Nuclear Weapons: More May Be Better."* Adelphi Paper 171. *IISS.*
*Sagan, S.D. (1993).* The Limits of Safety: Organizations, Accidents, and Nuclear Weapons. *Princeton University Press.*
*Brodie, B. (1959).* Strategy in the Missile Age. *Princeton University Press.*
*Organski, A.F.K. (1958).* World Politics. *Knopf.*
*Gilpin, R. (1981).* War and Change in World Politics. *Cambridge University Press.*
