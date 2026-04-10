# The Disease Arc

*On how the simulation's disease mechanics build on each other across contact history, and why the same trade network that spreads commerce spreads plague.*

---

The simulation's disease mechanics are not a single system. They are four interacting systems: virgin-soil first-contact epidemiology, endemicity transition, periodic epidemic waves, and the urban disease sink. Each system draws from a different strand of the historical epidemiology literature, and each fires at a different phase of a polity's contact history. Together they produce a characteristic disease arc for every polity: intense mortality at first contact, declining severity as exposure builds partial immunity, then periodic wave mortality modulated by population density and trade network centrality.

---

## Stage One: Virgin Soil (Diamond; McNeill)

Jared Diamond's *Guns, Germs, and Steel* (1997) synthesized a substantial body of evidence for a specific mechanism: populations isolated from a given pathogen have zero immunity to it, and when first exposed they suffer catastrophic mortality. The historical record is unambiguous on this point. The catastrophic mortality of indigenous American populations following European contact — estimated at 50–90% in some communities within a generation — was not primarily caused by violence. It was caused by first-contact exposure to Old World diseases for which those populations had no immunological preparation.

The mechanism that Diamond identified — which McNeill had documented more broadly in *Plagues and Peoples* (1976) — is pathogen divergence correlated with geographic and agricultural isolation. Populations that had lived for millennia with dense domestic animal populations in temperate Eurasian agricultural settings had accumulated immunological exposure to a range of zoonotic diseases. Populations that had not been exposed to those animals and those diseases had not. Contact between the two groups was immunologically asymmetric.

The simulation encodes pathogen divergence through crop type distance. `_cropDistance(cc, ct)` returns 0.2 for same crop, 0.5 for same crop zone, 0.8 for different crop zone, and 1.0 for maximum divergence (paddi-polity contacting a papa-polity — the wet-rice/Andean root crop pairing that maximizes pathogen environment difference). First-contact mortality: `mort = sev × cdist × (1 − immunity)`. With zero prior immunity and maximum crop distance, the full epidemic severity applies.

This is the most consequential disease event in any polity's history. First contact with a high-crop-distance polity can kill 15–30% of the population in a single tick. The simulation's first-contact popup and dispatch system reflects this: first-contact events are distinguished from epidemic wave events, treated as qualitatively different from the disease events that follow.

---

## Stage Two: Endemicity Transition (McNeill)

After the first-contact catastrophe, if the contact polity survives, something important changes. The surviving population has been exposed. Future contacts with the same pathogen environment are less severe, because some portion of the population has acquired immunity through exposure (or is descended from those who survived precisely because they had some existing immunity).

McNeill's *Plagues and Peoples* documents this transition from epidemic to endemic disease: the first exposure produces catastrophic mortality; subsequent exposures produce attenuated mortality as the disease becomes familiar to the immune system of an exposed population. The transition from epidemic to endemic does not mean the disease disappears; it means its mortality rate falls from catastrophic to manageable as the population builds partial immunity through repeated exposure.

The simulation encodes the endemicity transition through prior contact history. Each polity's `immunity` level is computed from the number of prior relay-contact relationships it has maintained. Per-pair relay contact age accumulates: polities with long-established trade relationships have built partial immunity to each other's pathogen environments. `immunity = min(0.6, sum of per-pair immunity contributions × 0.04/tick)`. The immunity cap at 60% severity reduction represents the biological ceiling of partial (non-specific) cross-immunity — exposure to related pathogens reduces, but does not eliminate, vulnerability to new strains.

The endemicity transition has an important implication for relay-network dynamics: polities in dense, established relay networks are immunologically prepared for their trade partners' pathogen environments in ways that isolated polities are not. High-connectivity polities are not more vulnerable to first contacts — the crop distance calculation is not modulated by contact history — but they are less vulnerable to the ongoing epidemic wave events that propagate through the relay network, because they have higher accumulated immunity.

---

## Stage Three: Epidemic Waves (McNeill; Schmid et al.)

Even after the first-contact crisis and the endemicity transition, periodic epidemic events continue to fire. These are not first-contact events; they are the ongoing background of periodic epidemic waves that propagate through trade networks. The Black Death, the Antonine Plague, the Justinianic Plague — these were not first-contact events for populations with some prior exposure. They were new strains, unusual virulence variants, or pathogen reservoir excursions that temporarily overwhelmed even partially-immunized populations.

The simulation's Stage 5b epidemic wave mechanic generates periodic epidemic events originating at high-connectivity, high-density nodes. The probability: `epiProb = epi_base_severity × 0.015 × (1 + nc × 0.2) × urbanFactor`. Three factors modulate the probability. `nc` is the node's contact count — trade hubs are more exposed to novel pathogen inputs because they have more pathogen-environment contacts. `urbanFactor` is the density modifier — dense populations sustain transmission chains more effectively than sparse ones. The product is the chance of an epidemic wave originating at a given node in a given tick.

Once triggered, the wave spreads. Each of the originating polity's trade partners has a 35% chance of receiving the wave, and each of their trade partners has a further transmission probability. The spread follows the relay network structure: well-connected polities spread waves more widely than isolated polities, because they have more channels through which transmission can occur.

Mortality per epidemic wave: 4–16% of the affected population. This is lower than first-contact mortality but not trivial. Repeated epidemic waves over centuries produce a substantial cumulative mortality effect on high-connectivity, high-density polities.

McNeill's port-warehouse model for the Black Death transmission is the historical precedent: rat fleas carrying Yersinia pestis spread through the medieval trade network with a probability that was proportional to the density of trade contacts, warehouse storage, and urban population. The simulation's trade-network propagation formula is a computational abstraction of this mechanism.

---

## Stage Four: Urban Disease Sink (Davenport; Wrigley & Schofield)

The urban disease sink is the fourth and most persistent disease mechanic. It operates not as a periodic event but as a continuous mortality modifier on dense polities.

Rebecca Davenport's 2020 study of urbanization and mortality in pre-industrial Britain documented a robust historical pattern: cities had negative natural population growth rates. Urban areas could sustain their populations only through continuous rural-to-urban migration; left to themselves, they would have declined. The cause was density-dependent mortality — the close-packed conditions of pre-industrial cities sustained transmission of disease at rates that exceeded natural population increase.

The simulation implements this as a continuous mortality modifier for polities at high population density: `urban_factor = max(1.0, density / 0.7)` — when population density exceeds 70% of carrying capacity, the epidemic wave probability multiplier increases above 1.0. This has two effects: it makes dense polities more likely to originate epidemic waves, and it means the waves that originate in dense polities are more severe when they propagate to other nodes.

The urban disease sink creates a structural trade-off between demographic density (which increases military and commercial capacity) and epidemiological vulnerability (which increases mortality). Polities that accumulate large populations face persistently elevated epidemic risk. This limits how quickly large polities can grow: population growth increases density, which increases epidemic mortality, which dampens further population growth.

---

## The Disease Arc as a Whole

The four mechanics together produce the characteristic disease arc:

1. **First contact**: catastrophic mortality proportional to crop-distance. Isolated polities are devastated when they enter the trade network for the first time. Mortality can be 20–30% in a single tick.
2. **Endemicity**: subsequent contacts are less severe as immunity builds. The first-contact catastrophe is a one-time event; the transition is gradual (0.04 per tick per established contact).
3. **Ongoing waves**: periodic epidemic events propagate through the trade network at mortality rates 4–16%. Frequency and severity scale with connectivity and density.
4. **Urban sink**: sustained mortality multiplier for dense polities.

The arc produces a counterintuitive relationship between trade network participation and disease burden. More connected polities are initially more at risk (they encounter more first contacts) but become more resilient over time (they build broader immunity). Less connected polities are less at risk in the short term (fewer first contacts) but more at risk in the long term (no accumulated immunity buffers against eventual contact). The simulation's disease mechanics therefore penalize late entry into the trade network more than early entry: the polity that enters the relay network in tick 50 faces the same first-contact severity as the polity that entered in tick 30, but has accumulated less immunity against subsequent waves.

This is consistent with the historical record of post-Columbian disease encounters: populations that had been in continuous contact with Old World trade networks for millennia had substantially better outcomes at first contact with novel populations than populations that had been isolated.

---

*See also: the_fever_belt.md (malaria as a persistent geographic constraint, separate from the disease arc); the_malthusian_clamp.md (how disease mortality interacts with the population ceiling mechanic)*

*Diamond, J. (1997).* Guns, Germs, and Steel: The Fates of Human Societies. *W.W. Norton.*
*McNeill, W.H. (1976).* Plagues and Peoples. *Anchor Books / Doubleday.*
*Davenport, R. (2020). "Urbanization and Mortality in Britain, c.1520–c.1850."* Economic History Review *73(2).*
*Schmid, B. et al. (2015). "Plague Pathogen Transmission in the Presence of Multiple Rodent Species and Flea Types."* PNAS *112(30).*
