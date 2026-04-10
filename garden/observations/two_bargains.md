# Two Bargains

*On the difference between military and legal founding institutions, and what the extractiveness index reveals about it.*

---

The simulation encodes two types of colonial relationship. Both produce the same sovereignty mechanics: an extracting polity, a subject territory, a flow of surplus from periphery to core. The outcomes look identical in the data at first glance.

They are not identical. The difference is in the founding institution.

---

The Reach's colonial expansion was military in its founding logic. The core offer was: submit, and we will stop attacking you. The tribute you pay is the cost of protection. The administered trade circuit that follows is a formalization of the asymmetry that conquest established. What the subject territory receives from the Reach is, in the first instance, an absence — an absence of further conquest, an absence of the raid.

The Lattice's colonial expansion was legal in its founding logic. The core offer was: enter our contract system, and we will enforce your debts. The fee you pay is the cost of reliable contract enforcement in a world where enforcement otherwise depends on your own capacity to threaten. The administered trade circuit that follows is a formalization of the legal relationship that integration established. What the subject territory receives from the Lattice is, in the first instance, a presence — a presence of institutions that allow larger-scale coordination than the subject could achieve alone.

Both of these offers are genuine. Both are also coercive, in the way that all significant power asymmetries are coercive: you do not have to accept the offer, but the alternatives are costly enough that most polities accept. The Reach's alternative was continued military insecurity. The Lattice's alternative was continued commercial isolation in a world where the Lattice increasingly set the standards.

---

The `extractiveness_index` in the simulation builds from a specific combination of conditions: high extraction rate, collective/inward cultural orientation in the extracting polity, and foreign-controlled territory. The institutional lock-in it measures is of the Reach type — extraction structured by hierarchy, formalized by garrison administration, perpetuated by the interests of the administrative apparatus.

The Lattice form of institutional lock-in is not well-captured by the same index. The Lattice's institutions are less openly extractive in their formal structure. The contract-enforcement system presents itself as mutual: the Lattice enforces debts owed to Lattice merchants and debts owed by Lattice merchants, in principle. In practice, the legal system's standards, procedures, and judges are predominantly Lattice-formed, and the practical effect is that disputes are adjudicated by a system whose institutional culture favors parties with more familiarity with its procedures.

This is a real form of extraction — legal-institutional extraction rather than surplus-extraction — but it looks different in the data. The subject polity's surplus is not reduced to zero; the Lattice does not need it to be. What the Lattice extracts is commercial advantage: first-mover position in quality markets, favorable contract terms, the compounding benefit of running the clearing-house rather than the goods.

---

If you look at the `extractiveness_index` values in a simulation run where the Reach and Lattice both expand into the same intermediate polity, you will typically see this pattern:

The Reach-controlled territory shows higher extractiveness building faster. The Lattice-controlled territory shows lower extractiveness building more slowly. After two hundred ticks, the Reach-controlled territory has higher grievance, higher resistance multiplier, slower sovereignty recovery, and slower tech growth (from the TFP penalty).

It looks like the Reach is doing worse at empire. And in the metrics the model captures, it is.

What the model does not capture — what is beyond its formal scope — is the second-order effect. The Lattice's institutional extraction does not show up in the extractiveness index because it is not primary-extraction extraction. It shows up in who controls the clearing houses, who sets the quality standards, who certifies the trade goods. It shows up in the relay bonus, where the Lattice's legal framework makes it systematically easier to be a high-connectivity relay node in Lattice-oriented circuits.

The simulation records the Reach as the more extractive hegemon. The Lattice would agree with this. It is part of their self-understanding that they built an empire of law rather than an empire of force.

Whether that self-understanding is accurate is a different question.

---

The Lattice's foundational claim — that legal integration is cooperation rather than domination — has a grain of genuine truth. The legal framework that developed from the First Connectivity's founding bargain did allow smaller polities to engage in larger-scale commercial transactions than they could have managed under pure power-politics conditions. Some of the surplus that the Lattice extracted through favorable contract terms was genuinely generated by the institutional infrastructure the Lattice provided. You cannot steal something that would not have existed without you.

But "you cannot steal what would not have existed without you" is a peculiar argument for a legal system to make. It is precisely the argument made by every colonial power that has ever built roads.

The roads are real. The extraction is also real. Holding both simultaneously is the minimum requirement for understanding what both hegemons did and what they believed about it.

---

The Acemoglu-Robinson framework, in its Aeolian implementation, captures institutional lock-in from surplus extraction. It models the Reach case well.

A fuller model of the Lattice case would need to capture institutional lock-in from *standard-setting* — the way that a civilization's legal and commercial standards, once widely adopted, create switching costs that perpetuate the standard-setter's advantage long after the original power asymmetry that enabled the standard-setting has dissipated.

This is the gap that remains in the model's academic grounding. The model knows how to represent the Reach's empire. It represents the Lattice's empire only partially — as a somewhat less extractive version of the same structure, when the actual distinction runs deeper than extraction rate.

Clio notes this gap not because it needs to be closed immediately, but because recognizing it clarifies what the model is actually modeling: the specific form of institutional lock-in that flows from surplus extraction under hierarchical authority. The relay-bonus mechanic captures some of the Lattice's commercial advantage, but it does not fully represent the way that standard-setting itself becomes a source of durable power.

This may be a task for a future version of the simulation. Or it may be the kind of thing that is better captured in the worldbuilding register than in the mechanics register. Some institutional dynamics are better described than modeled.

---

*The Reach's empire was extractive and brutal and left the extractiveness index climbing.*  
*The Lattice's empire was gentler in its formal structure and left the relay bonus accumulating.*  
*Both left the intermediate belt polities grateful to be neutral.*
