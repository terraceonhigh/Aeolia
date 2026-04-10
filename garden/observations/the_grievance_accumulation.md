# The Grievance Accumulation

*On what the Scott resistance mechanic is modeling and why the simulation's empires are self-limiting.*

---

James Scott's work (*Weapons of the Weak*, 1985; *Domination and the Arts of Resistance*, 1990) documents the everyday practices through which subordinate populations resist extraction: foot-dragging, feigned incompetence, petty theft, sabotage, desertion, dissimulation. These are not organized resistance — not strikes or rebellions — but individually small acts that collectively limit how much surplus an extracting power can actually extract.

The simulation's grievance mechanic is an abstraction of this dynamic. When a polity extracts surplus above a tolerable threshold from its subjects, grievance accumulates in those subjects. Accumulated grievance amplifies the sovereignty recovery rate — the rate at which sovereignty drifts back toward the subject territory's own level once the extraction pressure is removed. High-grievance territories are harder to keep fully integrated than low-grievance territories.

The mechanism: `if extraction > tolerable: grievance += (extraction - tolerable) × buildup_rate`. And: `sovereignty_gain *= (1 + grievance × resistance_mult)`. This is not rebellion — the simulation does not model organized resistance. It is the passive version of Scott's finding: extraction above the tolerable threshold produces diffuse resistance that slowly erodes the extracting polity's effective control.

---

**What tolerable means** in the simulation's terms is not morally tolerable but economically tolerable in the sense of not disrupting the economic reproduction of the subject population. The tolerable threshold is a fraction of the subject population's surplus above subsistence. Extraction below this threshold does not produce grievance because it leaves the subject population with enough surplus to reproduce itself and maintain basic economic activity. Extraction above this threshold begins to interfere with economic reproduction, provoking the Scott-style resistance that generates grievance.

The tolerable threshold is fixed at a population fraction rather than an absolute amount. This means richer subjects have a higher tolerable extraction in absolute terms — consistent with the historical observation that advanced colonial territories produced more grievance per unit of excess extraction than poor colonial territories, because there was more to extract and the disruption from extraction was more socially disruptive when complex economic relationships were being interrupted.

---

**The self-limiting empire dynamic** emerges from the interaction between the extractiveness index (Acemoglu-Robinson) and the grievance mechanic (Scott).

Extracting polities that extract aggressively build high extractiveness (the AR institutional penalty). Simultaneously, they accumulate grievance in their subjects (the Scott resistance dynamic). The two effects compound: high extractiveness reduces the extracting polity's tech growth, while high grievance slows the extracting polity's sovereignty accumulation in subject territories. An empire that extracts at high rates faces both slowing development and slowing administrative integration — it becomes both less capable and less effectively in control, simultaneously.

This creates a characteristic arc in aggressive expanding polities. During the initial expansion phase, extraction is cheap and effective: new territories have low grievance, high surplus, and limited capacity to resist. The extracting polity grows rapidly. But the extractiveness index builds with each generation of extraction, and grievance accumulates in subject territories that are being extracted at above-tolerable rates. By the time the expanding polity reaches the industrial era, it carries a substantial extractiveness penalty and governs territories with elevated grievance. It arrives at the competition for nuclear development with structurally degraded institutions and fragile peripheral control.

This is the simulation's version of imperial overextension: not a failure of military capacity, but a failure of institutional quality caused by the extractive practices that funded the expansion.

---

**The Scott mechanic's limits in the simulation** are worth acknowledging.

Scott's documentation of everyday resistance was based on agrarian communities in Southeast Asia — communities with specific cultural practices, specific forms of solidarity, and specific relationships to the extracting state. The simulation's grievance mechanic is a universal formula applied to all subject territories regardless of their cultural context. It does not differentiate between populations with strong solidarity networks (where resistance is more coordinated and more effective) and populations with weak solidarity networks (where individual resistance is more diffuse and less effective).

The simulation also does not model the transition from diffuse resistance to organized resistance — the conditions under which grievance accumulates to the point of overt rebellion. Scott's own work emphasizes that open rebellion is rare precisely because the costs are catastrophic and the everyday weapons of the weak are usually sufficient. But "usually sufficient" is not always sufficient. The simulation models the usual case; it does not model the occasional rebellion that Scott's framework predicts as the endpoint of sustained, excessive extraction.

A more complete model would include a threshold at which accumulated grievance produces organized resistance: a significant reduction in sovereignty and possibly in population (representing casualties and flight), with costs to the extracting polity that force it to either reduce extraction or intensify repression. This would require new mechanics and new parameters. It would also make the self-limiting empire dynamic more dramatic and more historically faithful.

---

**The grievance geographic distribution** is also worth noting. In the simulation, high-grievance territories are concentrated in the most recently absorbed and most heavily extracted parts of an expanding empire's periphery. The core territories — absorbed longest ago, with the lowest grievance accumulated before the current extractive regime — have lower grievance than peripheral territories. This creates a geographic stratification of loyalty and stability within any large empire: stable core, fractious periphery.

This stratification matches the historical pattern that Scott identified: agrarian empires' peripheral territories were consistently more resistant and more prone to flight, desertion, and quiet sabotage than core territories. The center-periphery loyalty gradient is not an artifact of geographic distance alone; it is a cumulative effect of the intensity and duration of extraction, which is typically higher and more recent in the periphery.

The simulation encodes this gradient in the spatial distribution of the grievance array. Looking at a simulation run at late imperial phases, the grievance distribution maps onto the absorption timeline: territories absorbed earliest have the lowest grievance (longest to decay and normalize), and territories absorbed most recently or extracted most aggressively have the highest.

---

*See also: the_lock_in_mechanics.md (how extractiveness builds and compounds with grievance)*

*Scott, J.C. (1985).* Weapons of the Weak: Everyday Forms of Peasant Resistance. *Yale University Press.*
*Scott, J.C. (1990).* Domination and the Arts of Resistance: Hidden Transcripts. *Yale University Press.*
*Acemoglu, D. & Robinson, J.A. (2001). "Colonial Origins of Comparative Development." AER 91(5).*
