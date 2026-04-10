# The Intermediate Belt Problem

*On what the Walt alignment mechanic is modeling, and why it matters for the Strange Peace's stability.*

---

The simulation's intermediate belt is not a geographic zone — it is a structural position. Any polity that sits between two nuclear hegemons, trading with both, absorbed by neither, is in the intermediate belt regardless of where on the ocean world it is located. The polities with this structural position face a specific problem that the post-DF era creates for them.

The problem: before the Strange Peace, a polity in this position could remain neutral because neutrality was commercially viable. Both hegemons needed relay contacts, and a polity that traded with both could extract rents from that position (the Greif relay bonus, in the simulation's terms). After the Strange Peace, the problem changes. The hegemons are frozen against each other; their competition moves into the intermediate belt; and each hegemon has strong incentives to absorb intermediate belt polities before the other does. Neutrality becomes harder to maintain.

The Walt alignment mechanic models the intermediate belt polity's response to this pressure. The alignment variable is not a choice — it is an assessment. Each tick after DF fires, a non-hegemon polity assesses which hegemon poses greater threat: which is more powerful, more extractive, with more fleet presence, and closer. The alignment drifts toward the less threatening option.

This is Walt's insight: alignment is not primarily about affinity, ideology, or commercial interest. It is about threat perception. A polity aligned with Hegemon B is not aligned because it likes Hegemon B. It is aligned because Hegemon A is more threatening than Hegemon B, and the cost of opposing Hegemon A's expansion is reduced by being in Hegemon B's orbit.

---

The simulation's implementation reflects three of Walt's four threat components:

**Capability** (tech level): higher tech = more threatening. Modeled directly.

**Intentions** (extractiveness): higher extractiveness = more threatening. A hegemon that has demonstrated extractive behavior toward its subjects is assessed as more threatening than one that has demonstrated inclusive behavior. This is the simulation's encoding of Walt's "perceived aggressive intentions" — inferred from institutional behavior, not stated policy.

**Offensive capability** (fleet_scale): fleet presence = more threatening. A hegemon with greater fleet capacity can project power farther. Modeled directly.

The fourth Walt component — **geographic proximity** — is in the denominator (distance). Closer hegemons are more threatening than distant ones of equivalent capability and extractiveness.

The product of these four components, divided by distance, is the threat score that drives the drift. The alignment score is the difference between the two hegemons' scores, normalized.

---

What the mechanic produces in the simulation depends heavily on how different the two hegemons are on these dimensions.

In simulations where both hegemons are roughly symmetric — comparable tech, comparable extractiveness, comparable fleet scale — the intermediate belt polities align roughly by proximity. The closer hegemon is more threatening; polities drift away from it. The intermediate belt divides roughly along geographic lines, each hegemon drawing the nearby polities into alignment, leaving a zone of ambiguity in the middle.

In simulations where the hegemons are asymmetric — one more extractive, one more capable, one with more fleet presence — the alignment pattern is more complex. Polities close to the more extractive hegemon may align strongly toward the less extractive one, even if the less extractive hegemon is farther away, because extractiveness contributes to threat faster than distance discounts it. This produces what looks like an ideological alignment: polities preferring the "nicer" hegemon.

The simulation does not have ideology. It has extractiveness. The pattern that looks ideological in the output is mechanically a threat calculation. This is, arguably, close to what Walt claims happens in actual international politics: ideological alignment is usually a rationalization of threat-based alignment, not its cause.

---

The alignment mechanic's effect on the simulation's expansion dynamics is modest but directional.

In the pre-DF era, the intermediate belt is absorbed by whoever reaches it first — the territorial expansion race. In the DF era, each hegemon faces a targeting penalty when trying to absorb polities aligned toward the other. The penalty grows as alignment strengthens (as threat asymmetry persists over many ticks). A polity that has been strongly aligned toward Hegemon B for ten ticks is significantly harder for Hegemon A to absorb than an unaligned polity.

This creates a stabilizing dynamic: as the Strange Peace continues, the intermediate belt's alignment hardens, and the hegemons' ability to expand into each other's aligned territory decreases. The proxy war competition — which the stability-instability paradox produces — becomes costlier over time as alignment protection accumulates.

The long-run equilibrium is not full alignment (alignment is bounded at ±1 and the drift rate is slow). It is partial alignment: most intermediate belt polities in modest alignment toward the less threatening hegemon, with genuine ambiguity in the middle zone. This matches the Cold War pattern better than a clean bloc division.

---

The historical analog is the non-aligned movement of the actual Cold War — but inverted. The non-aligned movement was an attempt by intermediate belt polities to *resist* alignment, to remain genuinely neutral in the face of superpower pressure. The simulation's alignment mechanic models the pressure that makes neutrality hard to maintain. The fact that some polities resist this pressure — maintain alignment near zero despite persistent threat asymmetry — is the simulation's version of the non-aligned movement's project.

Whether the non-aligned movement succeeded in the actual Cold War is contested. (Most IR scholars conclude that declared non-alignment often masked practical alignment toward one bloc or the other.) Whether non-alignment is viable in the simulation's Strange Peace depends on geography and threat symmetry. Polities equidistant from both hegemons, in a simulation with roughly symmetric hegemon capabilities and extractiveness, can maintain low alignment. Polities in asymmetric positions, under persistent threat from one dominant hegemon, cannot.

This is the intermediate belt problem. It does not resolve. It is an ongoing condition of the Strange Peace.

---

*See also: the_mutual_recognition.md (how the Strange Peace was established); two_bargains.md (what it didn't resolve)*

*Walt, S. (1987).* The Origins of Alliances. *Cornell University Press.*
*Rubinstein, A. and Zweifel, T. (2004). "In search of 'imperial understretch': A new look at Cold War neutralism."* Journal of Peace Research.
*Vital, D. (1967).* The Inequality of States: A Study of the Small Power in International Relations. *Oxford University Press.*
