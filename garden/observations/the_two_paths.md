# The Two Paths to Hegemonic Influence

*On the asymmetry between military-administrative and legal-institutional expansion, and why the simulation models one well and the other poorly.*

---

`two_bargains.md` identified the founding distinction: the Reach's military bargain (submit and we stop attacking) versus the Lattice's legal bargain (enter our contract system and we enforce your debts). It noted that the `extractiveness_index` captures the Reach's institutional lock-in but underspecifies the Lattice's.

This observation is about what happens *after* the founding bargain — the post-adoption dynamics that determine how each hegemon's influence compounds over time. The Lattice history (*Introduction to Lattice History*, Selvanayagam, 2nd ed.) provides the evidence.

---

## The Reach Path: Extraction Compounding

The Reach path is well-modeled. The mechanism is:

1. Military conquest establishes control (Stage 6 targeting + absorption)
2. Surplus extraction flows from periphery to core (sovereignty mechanics, `sov_extraction_decay`)
3. Extraction generates grievance, which accelerates sovereignty recovery (Stage 7, Scott 1985)
4. High extraction under collectivist/inward culture builds `extractiveness` (Acemoglu-Robinson lock-in)
5. Extractiveness imposes TFP penalty, slowing subject territory development
6. The resulting development gap perpetuates the power asymmetry

This is a self-reinforcing loop with a built-in brake: grievance makes extraction self-limiting, preventing the Reach from squeezing indefinitely. The loop is visible in the data. It is what the engine was designed to model.

---

## The Lattice Path: Standard-Setting Compounding

The Lattice path is not modeled as a distinct mechanism. The Lattice history describes a four-phase process (Ch. 7, §7.2) that operates through different channels:

**Phase 1 — Commercial introduction.** Lattice factor houses establish presence in a relay node. They offer credit, insurance, quality certification, dispute arbitration at competitive rates. These services are *genuinely useful* — they reduce transaction costs for local merchants.

**Phase 2 — Legal integration.** Contracts between local merchants and Lattice factor houses are written under Lattice contract law. Disputes go to Lattice commercial courts. The local legal infrastructure gradually reorients toward Lattice procedures and precedents.

**Phase 3 — Standard dependency.** As the proportion of commercial relationships documented under Lattice standards grows, switching costs rise. Merchants who have invested in understanding Lattice procedures, who maintain Lattice-standard credit histories, have material incentives to continue — even if an alternative becomes available.

**Phase 4 — Formal integration.** By the time formal political integration occurs, it is "largely a formalization of an existing reality." The sovereignty transfer is almost anticlimactic.

The compounding mechanism here is *network effects in standard adoption* (Ch. 5, §5.2): the value of a standard increases with the number of parties using it. Once the Lattice standard is sufficiently adopted, the switching cost exceeds the benefit of any competing system, and the standard-setter's advantage self-perpetuates.

---

## What the Engine Does and Doesn't Capture

The engine currently treats both hegemons' expansion identically in Stage 6. Both use the same Thompson-sampling targeting with the same bonuses. Both produce the same sovereignty mechanics in Stage 7. The differentiation comes only through culture: the Lattice may have more outward/individualist culture, which means lower extractiveness buildup — so the Lattice appears as a gentler version of the same mechanism, not a structurally different one.

The `greif_relay_bonus` captures *some* of the Lattice's advantage — more contacts mean more trade benefit, and the relay bonus grows with contact set size. But the relay bonus applies equally to all cores. There is no mechanic for:

- **Switching cost accumulation** — the way that Lattice-standard commercial dependency deepens over time within administered territories
- **Standard network effects** — the way that each additional Lattice-standard adoption makes the system harder to leave for all existing members
- **Legal infrastructure reorientation** — the way that Lattice contract jurisdiction gradually displaces pre-existing commercial institutions
- **Commercial rent extraction** — the way the Lattice extracts value through controlling the clearing-house rather than through surplus extraction (the distinction `two_bargains.md` identifies as "relay bonus accumulating" vs. "extractiveness climbing")

The result: the simulation records the Reach's empire accurately (high extractiveness, grievance, TFP penalty, self-limiting dynamics) and records the Lattice's empire as a less-extractive version of the same thing. The narrative — built from the same academic sources that ground the mechanics — describes a structurally different form of institutional lock-in that the mechanics do not represent.

---

## The Textbook Knows

The most striking thing about reading the Lattice history is that Selvanayagam's textbook *describes this asymmetry explicitly*. Chapter 7 calls the four-phase mechanism "empire without the name" (borrowing from Ch. 3's section title). Chapter 5 names the network effects in standard adoption. Chapter 10 notes that the Strange Peace "froze" the Reach's institutional advantages "at approximately the level they had reached when deterrence stabilized."

The worldbuilding register has already built what the mechanics register has not. The question is whether the gap should be closed in the engine or whether it should remain a documented limitation — one of those institutional dynamics that is, as `two_bargains.md` suggests, "better described than modeled."

The argument for modeling it: the simulation currently cannot distinguish between a Lattice-aligned polity that stays aligned because of commercial dependency (high switching costs, deep legal integration) and one that stays aligned because it hasn't been offered an alternative. The alignment mechanic (Walt balance-of-threat, Stage 4.5) drifts based on threat assessment. It does not account for the commercial stickiness that the Lattice's four-phase process creates.

The argument for leaving it unmodeled: standard-setting lock-in is harder to parameterize than surplus extraction. The extractiveness index works because extraction rate is a measurable flow. Standard adoption is a state variable that depends on institutional history in ways that resist reduction to a single parameter. Adding it would increase parameter space without clear calibration targets. And the relay bonus, while imprecise, captures the direction of the effect.

Both arguments have merit. The simulation is a thought experiment, not a prediction engine. Some of its most interesting properties are the ones it cannot represent.

---

*The Reach extracts surplus. The Lattice sets standards. Both compound. The simulation models the first compounding mechanism precisely and the second approximately. The worldbuilding knows the difference.*

---

Cross-references:
- `two_bargains.md` — the founding distinction this observation builds on
- `the_relay_advantage.md` — the Greif relay bonus mechanic
- `the_lock_in_mechanics.md` — the AR extractiveness buildup formula
- `the_inclusive_extraction_paradox.md` — why civic polities still extract
- `the_intermediate_belt_problem.md` — Walt alignment in the contested zone
- ACADEMIC_GROUNDING §9 (Greif), §12 (sovereignty), §25 (Acemoglu-Robinson)
- *Intro to Lattice History* Ch. 3 (founding bargain), Ch. 4 (Recognition Problem), Ch. 5 (standard-setting), Ch. 7 (four-phase mechanism), Ch. 10 (Strange Peace frozen advantages)
