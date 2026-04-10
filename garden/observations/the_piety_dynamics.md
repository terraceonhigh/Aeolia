# The Piety Dynamics

*On what the religion mechanics are modeling and what they are not.*

---

The simulation's piety score is not a measure of sincere belief. It is a measure of the role that religious institutions play in a polity's social organization — how much of the polity's governance, charity, cultural transmission, and collective identity is organized through religious rather than secular institutions. The distinction matters because it is possible to have a high-piety polity whose population is privately skeptical (organized religion remains central to social structure despite declining personal conviction) and a low-piety polity whose population is personally devout (strong personal faith without institutional religious dominance).

The simulation does not model the distinction between institutional religion and personal faith. It models the first: institutional religiosity as a feature of social organization. Everything the piety score affects — absorption bonuses, schism pressure, expansion targeting — is mediated through institutional structure, not individual conviction.

---

**The Norris-Inglehart secular transition** is encoded in the piety decay formula. As a polity's prosperity and tech level increase, piety decreases at a steady rate. The mechanism Norris and Inglehart documented (2004) is existential security: when populations feel physically and economically secure, they have less need for the comfort and social insurance that religious institutions provide. Institutional religion's hold weakens when people trust secular alternatives for the functions religion previously served.

The simulation encodes this as: `if tech > 7.0, piety -= drift_rate × (tech - 7.0) × 0.25`. Tech 7 is the rough threshold for what the simulation calls the "industrial era" — when manufactured goods and commercial infrastructure begin providing alternatives to communal resource-sharing mediated by religious institutions. Above tech 7, each additional tech unit reduces piety at a rate that increases with tech distance from the threshold.

The inverse also holds: crisis drives piety up. Low energy ratios (below 0.6) produce piety increase: `piety += drift_rate × (0.6 - er) × 2.5`. The crisis-to-piety link is Norris and Inglehart's negative finding: populations under existential stress do not secularize. In the simulation's terms, resource stress triggers increased institutional religious activity — charitable organizations, communal resource distribution, social coordination — that raises the institutional religiosity score.

The practical result: in normal development trajectories, polities secularize as they develop. In desperation cascades, polities become more religious even as their tech decays. The desecularization under stress is a partial recovery mechanism: high piety increases absorption efficiency through the centripetal force mechanic, which allows desperate polities to hold their territories together with religious legitimacy even as their economic and military capacity declines. It is a fragile stability, but it is something.

---

**The Grzymala-Busse schism mechanic** fires when the combination of high piety and weak sovereignty exceeds a threshold. The pressure formula: `(piety - 0.60) × low_sov_frac × 3.0 × tech_damp`. High piety creates institutional fervor; weak sovereignty in peripheral territories creates ungoverned space; the combination produces religious fragmentation. Breakaway polities adopt the Reformed culture shift (more individualist, more outward — the Weber result).

The historical reference is Grzymala-Busse's "Tilly Goes to Church" (2023): the Reformation produced state fragmentation in the Holy Roman Empire (weak central sovereignty, high religious diversity) but not in France or England (strong central sovereignty). The simulation's schism mechanic is the minimalist encoding of this finding: fragmentation fires when the institutional conditions match the HRE pattern.

What the mechanic does not capture: the content of the doctrinal dispute. In real Reformations, breakaway movements had specific theological positions, specific critiques of the dominant institution, specific visions of what the reformed practice should look like. The simulation's breakaway polities simply receive a culture shift; they do not have doctrine. This is a genuine simplification. The culture shift — more individualist, more outward — is the aggregate behavioral change that Weber associated with Protestant practice, applied as a single transformation rather than the decades-long process that the actual Reformation produced.

The schism mechanic is most active in the mid-development range: above the industrial tech threshold (tech > 7), the tech_damp term reduces schism pressure, reflecting the secularization process. Most schisms fire in the colonial and early industrial era, when piety is still high enough to generate pressure but sovereignty is thin enough in peripheral territories to allow fragmentation. This timing is consistent with the historical concentration of Reformation-like events in the early modern period rather than the contemporary one.

---

**The centripetal force mechanic** (Grzymala-Busse 2023, same citation) is the piety bonus in sovereignty extraction. High-piety polities extract sovereignty from their subjects faster: `sovereignty_gain += base_gain × (1 + piety_absorption_bonus × piety_level)`. The mechanism is institutional: religious administration of colonial territories — missionaries, local religious officials trained in the colonial power's tradition, the use of religious legitimacy to naturalize extraction — increases the speed of administrative integration.

The simulation models this as a general bonus rather than a polity-type-specific one. In practice, the centripetal force effect is stronger in polities with both high piety AND outward culture orientation — the combination that produces missionary-style administration. A polity that is high-piety but inward-oriented gets the piety bonus on sovereignty extraction but does not direct it outward into the expansion targeting. The targeting bonus from piety (the missionary expansion drive) applies only when piety exceeds the 0.65 threshold.

The interaction between the centripetal force mechanic and the schism mechanic creates a double-edged institutional religion effect: high piety helps integrate peripheral territories (centripetal), but excessive piety in combination with weak periphery control produces schism (centrifugal). The simulation models religion as a force that can hold empires together or tear them apart depending on the interaction of piety level, sovereignty density, and tech stage. This is a better encoding of the historical record than treating religion as simply stability-increasing or stability-decreasing.

---

**What the piety mechanics do not model:** several important features of religious institutions' historical role that the simulation's resolution cannot capture.

The simulation does not model inter-polity religious conflict. The schism mechanic produces domestic fragmentation, not cross-polity religious warfare. In history, religiously motivated cross-polity warfare was a substantial factor in early modern international relations — the Thirty Years' War, the Crusades, the Mughal expansion. The simulation's piety bonus in expansion targeting is a pale shadow of this: it produces more aggressive expansion by high-piety polities, but it does not produce coalition warfare, crusade dynamics, or religiously-defined enemy categories.

The simulation does not model religious toleration policy. A polity that absorbs populations of different religious traditions may find those populations harder or easier to integrate depending on its approach to religious diversity. The simulation has no variable for toleration; all absorption is treated as culturally uniform.

The simulation does not model the distinction between state religion and voluntary religion. In many historical cases, the most fervent religious practice was in voluntary, dissenting traditions, not the official state religion. The piety score cannot distinguish the two.

These are gaps. They are acceptable gaps at the simulation's resolution — filling them would require substantially more state variables and substantially more calibration — but they should be noted as limits on what the piety dynamics can represent.

---

*See also: the_reform_dividend.md (Weber's schism as doctrinal innovation); two_bargains.md (piety's role in the Lattice's legal vs. Reach's military colonial founding)*

*Norris, P. & Inglehart, R. (2004).* Sacred and Secular: Religion and Politics Worldwide. *Cambridge University Press.*
*Grzymala-Busse, A. (2023). "Tilly Goes to Church: The Religious and Medieval Roots of European State Fragmentation."* American Political Science Review *117(1).*
*Weber, M. (1904/1905).* The Protestant Ethic and the Spirit of Capitalism. *Translated by Talcott Parsons (1930), Scribner.*
