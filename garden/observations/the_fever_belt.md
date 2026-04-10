# The Fever Belt

*On what the malaria mechanic is actually modeling, and why the simulation produces the geography it does.*

---

The simulation's malaria belt is defined by a single condition: absolute latitude below 20 degrees. Archipelagos in this zone have a `malaria_factor` applied to their carrying capacity — a ceiling on the population they can sustainably support. At base, the ceiling is 40% below normal. Post-tech-6, the penalty reduces to 30% (models partial prophylactic and drainage technology). It never disappears entirely within the simulation's tech range.

This is a crude model. The actual distribution of Plasmodium falciparum and its Anopheles vectors is considerably more complex than a latitude cutoff. But the crude model encodes something that the precise model would also encode, and encodes it more cleanly: there is a band of the ocean world where tropical infectious disease creates a structural ceiling on population density that the polities within it cannot engineer their way past with pre-industrial technology.

The consequences of this ceiling for the simulation's history are not subtle.

---

Within the malaria belt, polities develop more slowly. Their population supports a smaller tech base; the tech base supports slower expansion; slower expansion means less trade contact; less trade contact means slower knowledge diffusion. In isolation, this produces a gradual divergence between tropical and non-tropical polities — not because the tropical polities are less capable but because the disease ceiling imposes a structural constraint on the compounding that drives development.

What makes the divergence important is not the divergence itself but the interaction between the divergence and the expansion dynamics.

By the time the high-latitude polities have developed sufficient commercial and military capacity to expand into the malaria belt, the malaria belt polities are behind in the tech progression that determines military resistance. Tropical polities are absorbed earlier, at lower tech levels, than non-tropical polities of equivalent geographic position. Once absorbed, they face additional structural disadvantages: the extractiveness index builds faster in tropical polities (they are more often in the position of having their surplus extracted under foreign administration) and their carrying-capacity ceiling limits the population growth that would eventually close the tech gap.

The reversal-of-fortune pattern — which the AJR diagnostic measures — is, in the simulation, partly a tropical-geography story. Tropical polities that had large populations relative to their carrying capacity at the time of absorption tend to show more reversal than non-tropical polities. This is the simulation's version of the AJR finding that high-population-density pre-colonial territories became extractive colonies more consistently than low-density territories.

The causal mechanism in both cases: high density creates extractive opportunity; disease burden prevents the extracted population from resisting effectively; institutional extraction compounds over time into institutional lock-in.

---

The urban disease sink adds a second epidemiological dynamic. Above a density threshold of 70% carrying capacity, urban disease mortality becomes significant: the close contact of dense urban populations allows disease transmission at rates that rural populations don't experience. In the simulation, this models a constraint on proto-urban development: polities that densify rapidly face a disease mortality penalty that limits the benefits of density.

This is Diamond's argument from *Guns, Germs, and Steel* about the historical relationship between population density, domesticated animals, and epidemic disease. Dense populations living with domesticated animals are exposed to zoonotic disease at high rates, develop immunity over generations, and then carry those diseases to populations that have not had the same exposure. The simulation doesn't model the zoonotic pathway directly — it models the aggregate effect as an urban disease sink — but the underlying logic is the same: density creates disease vulnerability before it creates disease resistance.

The interaction between the malaria ceiling and the urban disease sink creates a particular difficulty for tropical polities that are trying to develop. A tropical polity that tries to densify its population to support the economic specialization that tech development requires faces both the malaria carrying-capacity ceiling (limiting how dense it can sustainably be) and the urban disease sink (imposing mortality on the density it does achieve). The combination is a double constraint on the path that non-tropical polities use to develop: they cannot take the same path, and the alternative paths are slower.

---

The epidemic wave mechanic adds a third dynamic: periodic stochastic disease events that propagate through the contact network. A wave originates in a polity under high population pressure, propagates to its trade contacts with mortality proportional to their contact exposure and inversely proportional to their prior relay-trade contact history (the per-pair relay contact age endemicity model).

The epidemic wave mechanic models, at a high level, the pattern that McNeill identifies in *Plagues and Peoples*: epidemic disease is an endemic feature of dense, interconnected commercial networks, and its specific impact on any given community depends on the community's history of exposure to the disease environment that the network creates.

Communities that have been in relay contact for longer have more prior exposure and therefore more immunity. Communities that enter the relay network later — newly contacted, recently absorbed — are more vulnerable. The vulnerability decreases over time as relay contact accumulates, but the transition period can be devastating.

The simulation records this transition period in its epidemic log. The events that appear as first-contact epidemics in the event timeline are mechanically driven by the immunity gap between newly contacted polities and their contactors. They are not random. They are the predictable consequence of two populations with different disease histories encountering each other through the commercial contact that the relay network creates.

---

The combined effect of these three epidemiological mechanics — malaria ceiling, urban disease sink, epidemic waves — produces a world where disease is not a uniform background condition but a structured feature that varies with geography, population density, and contact history. Polities in different positions in this structure face different developmental trajectories.

This is a structural truth about the historical record as well. The epidemiological geography of disease was not neutral. It created systematic advantages for populations in temperate latitudes, in populations with long livestock-domestication histories, and in populations with sustained commercial contact. It created systematic disadvantages for populations in tropical latitudes, in populations without prior epidemic exposure, and in populations newly entering the commercial network.

The simulation does not model all of these dynamics at full resolution. It models them at the resolution that produces recognizable historical patterns at scale: a world where tropical polities develop more slowly, are absorbed more easily, and show more pronounced reversal patterns in the development data.

Whether the simulation's resolution is adequate depends on what you need it for. For the purpose of producing historically plausible macro-patterns, it is adequate. For the purpose of understanding the specific experiences of specific populations in the disease transition, it is not — and is not trying to be.

The fever belt is a structural condition in the simulation. It was a structural condition in history. The populations that lived within it understood that before any model did.

---

*McNeill, W. (1976).* Plagues and Peoples. *Anchor.*  
*Diamond, J. (1997).* Guns, Germs, and Steel: The Fates of Human Societies. *W.W. Norton.*  
*Gallup, J.L. & Sachs, J.D. (2001). "The Economic Burden of Malaria." American Journal of Tropical Medicine and Hygiene 64(1): 85-96.*
