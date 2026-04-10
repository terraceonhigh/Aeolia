# Aeolia — Academic Grounding

**Mechanic-by-mechanic citation map.**  
For each simulation mechanic, this document records the scholarly framework it operationalizes, the specific causal claim encoded, the file(s) where it lives, and any known gaps between the simulation and the literature.

Grading scale for empirical grounding: **A** (directly empirically validated), **B** (theoretically well-grounded, plausible parameters), **C** (defensible simplification, weak empirical precedent).

---

## I. State Formation and Political Culture

### 1. Crop-to-culture mapping (Wittfogel; Almond & Verba)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (§10 `_CROP_CULTURE_SEED`), `aeolia-godot/optimization/sim_proxy_v2.py`

**Claim:** Legible, taxable grain agriculture (paddi) produces Subject cultures (bureaucratic, collectively organized); dryland grain agriculture (emmer) produces Civic cultures (competitive, pluralistic); marginal or maritime crops produce Parochial cultures.

**Sources:**
- Scott, J. (2017). *Against the Grain: A Deep History of the Earliest States*. Yale University Press. (Primary: grain legibility thesis)
- Wittfogel, K. (1957). *Oriental Despotism: A Comparative Study of Total Power*. Yale University Press. (Historical precedent; used as generative starting condition, not deterministic law — see Gap)
- Almond, G. & Verba, S. (1963). *The Civic Culture*. Princeton University Press. (Parochial/Subject/Civic typology used metaphorically at civilizational scale, not as individual-level survey instrument — see Jackman & Miller 1996 critique)
- Inglehart, R. & Welzel, C. (2005). *Modernization, Cultural Change, and Democracy*. Cambridge University Press.

**Implementation:** `_CROP_CULTURE_SEED` seeds each crop in a 2D continuous culture space (CI = Collective↔Individual, IO = Inward↔Outward). Paddi at (−0.55, −0.20) encodes hydraulic bureaucracy; emmer at (0.45, 0.55) encodes mercantile pluralism.

**Gap:** Wittfogel's hypothesis has been criticized for being unfalsifiable and selecting on the dependent variable (Levi 1988; Mitch 1992). Bali's subak irrigation system is the classic counterexample — hydraulic agriculture without centralized despotism. Aeolia uses crop-to-culture mapping as a generative starting condition, not a deterministic law — polities drift from their seed positions based on material circumstances. The better theoretical grounding is Scott's (2017) "grain thesis": legible, storable, taxable crops enable state formation because they are visible to tax collectors, not because irrigation requires central coordination. See also Tilly (1990) on coercion-capital paths to state formation as an alternative framework.

**→ Garden:** `garden/observations/the_crop_culture_seed.md`

---

### 2. Continuous culture-space drift (Axelrod 1997; Boyd & Richerson 1985)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 2b), `sim_proxy_v2.py`

**Claim:** Political culture drifts based on prosperity (→ Individual), crisis (→ Collective), trade exposure (→ Outward), resource stress (→ Inward). Culture is not fixed but responds to material conditions.

**Sources:**
- Axelrod, R. (1997). "The Dissemination of Culture." *Journal of Conflict Resolution* 41(2).
- Boyd, R. & Richerson, P. (1985). *Culture and the Evolutionary Process*. University of Chicago Press.
- Norris, P. & Inglehart, R. (2004). *Sacred and Secular*. Cambridge University Press.

**Implementation note:** Two Axelrod mechanisms now implemented:
1. **Convergence-through-contact** (primary Axelrod mechanism): Trading partners with culture_dist < `axelrod_freeze_threshold` (default 0.85) drift toward each other proportional to trade volume fraction × `culture_convergence_rate` (default 0.005) × (1 − culture_dist). This produces emergent cultural regions through local interaction.
2. **Freeze at maximum divergence**: `culture_dist >= 0.85` → `complement = 0` in trade, fully isolating maximally divergent cultures from trade and cultural exchange. This is Axelrod's polarization prediction.

Five environmental drift terms: prosperity → Individual, crisis → Collective, trade exposure → Outward, resource stress → Inward, piety feedback → Collective/Inward mild pull. The environmental drifts are closer to Boyd & Richerson's (1985) biased cultural transmission (pressures select for traits); the convergence-through-contact is closer to Axelrod's (1997) feature-copying.

**→ Garden:** `garden/observations/the_culture_engine.md`

---

### 3. Weber legitimacy types (Reach vs. Lattice)
**Grade: A** (as worldbuilding framing) / **C** (as simulation mechanic)  
**Files:** `src/engine/constants.js` (POLITY_NAMES), `docs/` worldbuilding files

**Claim:** The Reach (Civic/emmer) derives legitimacy from liberal mercantile pluralism; The Lattice (Subject/paddi) derives it from bureaucratic-procedural regularity (Mandate of Heaven analog).

**Sources:**
- Weber, M. (1922/1978). *Economy and Society*. University of California Press.

**Implementation:** Operationalized through allocation shares — Subject cultures compound tech through institutional channels; Civic cultures through dispersed maritime trade.

---

## II. International Relations

### 4. IR posture matrix + alliance formation (Mearsheimer; Walt; Schweller)
**Grade: A−**  
**Files:** `src/engine/SimEngine.js` (Stage 2 `_POSTURE_TABLE`, Stage 4.5 Walt alignment), `sim_proxy_v2.py`

**Claim:** High capability + high threat → offensive expansion (offensive realism). Medium capability + high threat → alliance-seeking (balance-of-threat). Low capability + high threat → bandwagoning (Schweller revisionist states).

**Sources:**
- Mearsheimer, J. (2001). *The Tragedy of Great Power Politics*. Norton.
- Walt, S. (1987). *The Origins of Alliances*. Cornell University Press.
- Schweller, R. (1994). "Bandwagoning for Profit." *International Security* 19(1).

**Implementation:** 
- Stage 2: Walt multi-variable threat calculus replaces the old capability-bin posture lookup. Per-neighbor threat = `tech[other] × sqrt(territory[other]) × (1 + extractiveness[other]) / dist`. Max threat feeds into posture table. This encodes Walt's four variables: aggregate power (tech × territory), proximity (1/dist), offensive capability (extractiveness amplifies), perceived intent (implicit in extractiveness).
- Stage 4.5 implements Walt's balance-of-threat: post-DF, each non-hegemon polity maintains `alignment[i] ∈ [-1, 1]` that drifts toward the less-threatening hegemon each tick. Threat = `tech × sqrt(territory) × (1 + extractiveness) / distance`. Aligned polities impose a penalty (up to `alliance_protection_str × |alignment|`, default 2.5) on the opposing hegemon's expansion attempts against them. Two new params: `alliance_formation_rate` (0.04), `alliance_protection_str` (2.5).

**Additional sources (2026-04-10):**
- Fearon, J. (1995). "Rationalist Explanations for War." *International Organization* 49(3). (Commitment problems in expansion targeting)
- Jervis, R. (1978). "Cooperation Under the Security Dilemma." *World Politics* 30(2). (Spiral model vs. deterrence model — awareness accumulation can lead to either)

**→ Garden:** `garden/observations/the_intermediate_belt_problem.md`

---

### 5. The Strange Peace: Security Dilemma at civilizational scale
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 3–4), `sim_proxy_v2.py`

**Claim:** First contact between nuclear-capable civilizations replicates the security dilemma: defensive preparations are indistinguishable from offensive ones. Mutual awareness triggers a deterrence equilibrium, not open war.

**Note on naming:** The mechanic is internally labeled "Dark Forest" after Liu Cixin's *The Dark Forest* (2008), but the simulation's outcome is the opposite of Liu's prediction. Liu's Dark Forest hypothesis predicts preemptive annihilation — the rational response to detecting another civilization is immediate destruction, because you cannot verify intent. Aeolia's simulation instead produces mutual deterrence (the "Strange Peace"): nuclear peer detection triggers a −12.0 expansion penalty that freezes hegemons against each other, not a preemptive strike. This divergence is structurally significant — the simulation implicitly argues that when two civilizations reach nuclear capability roughly simultaneously (within ~7 ticks / 350 years), the conditions for Dark Forest preemption do not hold because neither side has a credible first-strike window. The Strange Peace is Schelling's and Waltz's prediction, not Liu Cixin's. The "Dark Forest" label is retained as the internal trigger name but the academic paper should reference the mechanic as the nuclear security dilemma, not the Dark Forest hypothesis.

**Sources:**
- Schelling, T. (1960). *The Strategy of Conflict*. Harvard University Press.
- Schelling, T. (1966). *Arms and Influence*. Yale University Press.
- Waltz, K. (1981). "The Spread of Nuclear Weapons: More May Be Better." *Adelphi Paper* 171. IISS.
- Powell, R. (1990). *Nuclear Deterrence Theory: The Search for Credibility*. Cambridge University Press. (Second-strike credibility through resource control)

**Implementation:** `otherAwareness` accumulates at 0.04/tick once both polities have tech ≥ 9.0; fires at awareness > 0.30. Arms race continues post-DF with tech bonus for hegemons above 8.5. Post-DF deterrence penalty (−12.0) + proxy war bonus (+3.0 in rival periphery) + alliance formation produce the Strange Peace: hegemons frozen against each other but competing aggressively in non-nuclear client territories.

**→ Garden:** `garden/observations/the_strange_equilibrium.md`

---

### 6. Stability-instability paradox (Snyder 1965; Waltz 1981)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 6 `proxyBonus`), `sim_proxy_v2.py`

**Claim:** Nuclear deterrence stabilizes direct inter-hegemon conflict but paradoxically enables sub-nuclear proxy warfare. Hegemons compete aggressively in each other's client periphery because the nuclear threshold prevents escalation.

**Sources:**
- Snyder, G. (1965). "The Balance of Power and the Balance of Terror." In *Balance of Power*, ed. Paul Seabury.
- Waltz, K. (1981). *The Spread of Nuclear Weapons*. IISS.

**Implementation (upgraded 2026-04-10):** After DF fires, nuclear hegemons receive `+proxy_war_bonus` (default 3.0) expansion bonus targeting non-nuclear territory in the rival hegemon's contact network, partially offsetting the −12.0 deterrence penalty against each other. Population losses in proxy zones are multiplied by `proxy_casualty_rate` (default 1.4), modeling the elevated cost of proxy competition. New SimParams: `proxy_war_bonus` (3.0), `proxy_casualty_rate` (1.4).

**→ Garden:** `garden/observations/the_strange_equilibrium.md`

---

## III. Political Economy and Trade

### 7. Technology accumulation with energy coupling and knowledge stock
**Grade: B+** (upgraded 2026-04-10: Ayres-Warr conversion efficiency + Romer knowledge stock)  
**Files:** `src/engine/SimEngine.js` (Stage 5), `sim_proxy_v2.py`

**Claim:** Technology grows as a reduced-form function of TFP, energy availability (with tech-dependent conversion efficiency), cumulative knowledge stock, and trade-network connectivity.

**Sources:**
- Ayres, R. & Warr, B. (2005). "Accounting for Growth: The Role of Physical Work." *Structural Change and Economic Dynamics* 16. (Conversion efficiency curve: thermodynamic efficiency of energy use improves with tech)
- Romer, P. (1990). "Endogenous Technological Change." *Journal of Political Economy* 98(5). (Knowledge stock: non-rival, cumulative, positive spillovers)
- Stern, D. (2011). "The Role of Energy in Economic Growth." *Annals of the New York Academy of Sciences*. (Broader energy-growth coupling)
- Jackson, M. (2008). *Social and Economic Networks*. Princeton University Press. (Network externalities in knowledge diffusion)
- Krugman, P. (1991). "Increasing Returns and Economic Geography." *Journal of Political Economy* 99(3). (Agglomeration externalities from market access)

**Implementation:**
- `delta_tech = A₀ × crop_exp × share_mult × accel_rate × contact_mult × energy_mult`
- `energy_mult = er × energy_to_tfp × conversionEff` where `conversionEff = 0.15 + 0.75 × clamp((tech−1)/9, 0, 1)^0.6` (Ayres-Warr: pre-industrial ~15%, industrial ~55%, modern ~85%)
- `contact_mult = 1 + log₂(effNc+1) × 0.15 + log₂(knowledgeStock+1) × 0.15` (split between raw contacts and cumulative knowledge)
- `knowledgeStock` accumulates from tech investment × energy surplus × `knowledge_accumulation_rate`; neighbors spill over via `knowledge_spillover_rate`

**Note:** This is a reduced-form technology accumulation function, not a structural Solow or Romer model. There is no capital accumulation with diminishing returns (Solow) and no R&D sector with non-rival ideas (Romer in the strict sense). The knowledge stock captures Romer's key insight (cumulative, non-rival, positive externalities) without the full microfoundation. The contact-based diffusion is closer to Krugman (1991) agglomeration or Jackson (2008) network economics than to Romer's R&D formulation.

**→ Garden:** `garden/observations/the_growth_machine.md`

---

### 8. Three-layer trade system: Subsistence → Relay → Administered (Abu-Lughod; Wallerstein; Braudel)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Trade Pre-Pass), `sim_proxy_v2.py`

**Claim:** Trade escalates through three regimes gated by technology: subsistence exchange (direct neighbors, bulk goods), relay trade (multi-hop luxury circuits), administered trade (polity-directed bulk extraction). Each regime has different markup, range, and complementarity dynamics.

**Sources:**
- Abu-Lughod, J. (1989). *Before European Hegemony*. Oxford University Press.
- Wallerstein, I. (1974). *The Modern World-System*, Vol. I. Academic Press.
- Braudel, F. (1949/1972). *The Mediterranean*. University of California Press.

**→ Garden:** `garden/observations/the_three_layer_trade_system.md`

---

### 9. Greif relay information asymmetry (Greif 1989)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Trade Pre-Pass `relayBonusA/B`), `sim_proxy_v2.py`

**Claim:** High-connectivity intermediary nodes capture asymmetric price differentials by controlling information flows between trading partners who cannot observe each other's prices. Per-contact bonus represents the Maghribi trader coalition model.

**Sources:**
- Greif, A. (1989). "Reputation and Coalitions in Medieval Trade: Evidence on the Maghribi Traders." *Journal of Economic History* 49(4).
- Greif, A. (1993). "Contract Enforceability and Economic Institutions in Early Trade." *American Economic Review* 83(3).

**Implementation:** `relayBonusA = min(0.40, contactSet[tc].size × greif_relay_bonus)`. Nodes with more contacts capture a larger share of the trade surplus.

**→ Garden:** `garden/observations/the_relay_advantage.md`

---

### 10. Prebisch-Singer declining terms of trade (Prebisch 1950; Singer 1950)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Trade Pre-Pass `psA/psB`), `sim_proxy_v2.py`

**Claim:** Bulk calorie-producing peripheries face structurally declining terms of trade relative to specialty/luxury/relay nodes. Paddi, taro, sago, and papa are bulk staples; emmer and nori produce storable specialty goods (stimulants, fibers) commanding higher per-unit value.

**Sources:**
- Prebisch, R. (1950). *The Economic Development of Latin America and Its Principal Problems*. ECLA/UN.
- Singer, H. (1950). "The Distribution of Gains between Investing and Borrowing Countries." *American Economic Review* 40(2).

**Implementation:** `psA = prebisch_bulk_discount (0.75)` for bulk crops, `1.0` for specialty crops. Applied per trading side, producing asymmetric benefits from the same trade relationship.

**→ Garden:** `garden/observations/the_terms_of_trade_ratchet.md`

---

### 11. Resource curse: Sachs-Warner / Ross (extractive institutions)
**Grade: A−** (upgraded 2026-04-10: now fully implemented with TFP penalty + pyra MIC curse)  
**Files:** `src/engine/SimEngine.js` (Stage 5 `a0` penalty), `sim_proxy_v2.py`

**Claim:** Naphtha-rich polities in the industrial era develop extractive institutions — elite resource rents that divert investment from broad-based human capital development, penalizing TFP growth.

**Sources:**
- Sachs, J. & Warner, A. (1995). "Natural Resource Abundance and Economic Growth." *NBER Working Paper 5398*.
- Ross, M. (2012). *The Oil Curse*. Princeton University Press.
- Vitalis, R. (2018). "The Myth of the Authoritarian Oil State." *Perspectives on Politics* 16(2).

**Implementation:** Fires when polity controls > ~13% of world initial C stock, tech 6–9.5. `curse = clamp(polityFrac × 3.0 − 0.4, 0, 0.5); a0 × = (1 − curse × resource_curse_strength)`.

**Gap:** None. See Mechanic 25 (Acemoglu-Robinson) below.

**→ Garden:** `garden/observations/the_resource_curse.md`

---

## IV. Colonial Dynamics and Sovereignty

### 12. Wallerstein world-systems hierarchy (six-level sovereignty taxonomy)
**Grade: A** (as structural framework) / **B** (as mechanic)  
**Files:** `src/engine/SimEngine.js` (state output `status` field), `sim_proxy_v2.py`

**Claim:** Colonial relationships produce a continuous sovereignty spectrum from full autonomy through tributary, client, garrison, colony to full core integration. Status is determined by sovereignty score, not categorical assignment.

**Sources:**
- Wallerstein, I. (1974). *The Modern World-System*. Academic Press.

**→ Garden:** `garden/observations/two_bargains.md` (Reach military vs. Lattice legal colonial founding; extractiveness_index differentiation); `garden/observations/the_three_layer_trade_system.md` (Administered layer as Wallerstein core/periphery extraction)

---

### 36. Frank/Cardoso dependency: unequal exchange at administered trade (Frank 1967; Cardoso & Faletto 1979)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (trade pre-pass, administered layer), `sim_proxy_v2.py`

**Claim:** In asymmetric colonial trade relationships, the more extractive polity captures a disproportionate share of trade surplus — "unequal exchange." This is distinct from the Prebisch-Singer terms-of-trade effect (§10), which is about commodity type; the Frank/Cardoso mechanism is about institutional asymmetry. Even when trading identical goods, the extractive party extracts surplus from the less extractive.

**Sources:**
- Frank, A.G. (1967). *Capitalism and Underdevelopment in Latin America*. Monthly Review Press.
- Cardoso, F.H. & Faletto, E. (1979). *Dependency and Development in Latin America*. University of California Press.
- Frank, A.G. & Gills, B. (1993). *The World System: Five Hundred Years or Five Thousand?*. Routledge.
- Emmanuel, A. (1972). *Unequal Exchange*. Monthly Review Press. (Formalization of the wage-differential mechanism underlying unequal exchange)

**Implementation (2026-04-09):** At tech ≥ 5 (administered trade tier), when `extractiveness[A] > extractiveness[B] + 0.05`: `drain = (ext_A − ext_B) × 0.3`. `benefit_A ×= (1 + drain)`, `benefit_B ×= (1 − drain)`. The 0.05 threshold prevents noise from triggering redistribution; the 0.3 factor is a half-drain of the extractiveness delta. This applies symmetrically — a less-extractive polity trading with a more-extractive one loses surplus proportional to the institutional gap.

**Effect:** Inclusive polities suffer a trade penalty when engaged in administered-tier exchange with extractive counterparts. This creates an incentive for inclusive-culture polities to either (a) avoid administered trade with extractive partners, (b) build their own institutional capacity, or (c) seek military protection. Mirrors Cardoso's "associated-dependent development" — some local growth is possible, but structural surplus flows upward.

**Gap:** The Emmanuel (1972) mechanism involves differential wage rates enabling the same technical composition to generate unequal exchange — this requires a labor price variable the simulation does not model. The current implementation proxies institutional extraction for all mechanisms of surplus drain, which captures the direction but not the full political economy.

**→ Garden:** `garden/observations/the_three_layer_trade_system.md` (unequal exchange as administered layer dynamic)

---

### 13. Scott's resistance: self-limiting colonialism (Scott 1985, 1990)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 7 `grievance`), `sim_proxy_v2.py`

**Claim:** Colonial extraction above a tolerable threshold generates grievance that accelerates sovereignty recovery, making extraction self-limiting. "It is not exploitation per se, but exploitation beyond what is deemed legitimate that triggers organized resistance."

**Sources:**
- Scott, J. (1985). *Weapons of the Weak: Everyday Forms of Peasant Resistance*. Yale University Press.
- Scott, J. (1990). *Domination and the Arts of Resistance*. Yale University Press.

**Implementation (upgraded 2026-04-10):** `grievance[i]` accumulates from excess extraction above `sov_extraction_decay × 0.5`. Culture distance amplifier: colonies culturally distant from their controller accumulate grievance faster (Hechter internal colonialism model). `resistanceMult = 1 + grievance × grievance_resistance_mult` amplifies the recovery term in sovereignty drift. Grievance decays at 2%/tick (slow memory — resistance fades over generations).

**Additional source:** Hechter, M. (1975). *Internal Colonialism: The Celtic Fringe in British National Development*. University of California Press. (Structural resistance at the level the simulation operates — culture distance as proxy for institutional alienation.)

**Remaining gap:** Scott's model emphasizes micro-level everyday resistance (foot-dragging, false compliance, hidden transcripts), not just aggregate sovereignty recovery. The current implementation captures the structural outcome (extraction → resistance → recovery) with a culture distance amplifier. The cultural/cognitive mechanism (consciousness-raising) is now partially addressed by Mechanic 35 below: high grievance in colonial periphery drifts the colonizer's culture toward Collective+Inward, modeling the ideological feedback of colonial resistance on metropolitan political culture (c.f. Fanon 1961, Césaire 1955).

**→ Garden:** `garden/observations/the_grievance_accumulation.md`

---

### 35. Grievance → consciousness-raising: colonial resistance feedback (Scott 1990; Fanon 1961)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 2b, after Axelrod convergence), `sim_proxy_v2.py`

**Claim:** High colonial grievance in the periphery feeds back on the colonizer's metropolitan culture, shifting it toward collectivism and inwardness — a consciousness-raising effect in which the resistance of the colonized reshapes the political culture of the colonizer. Historically: anti-colonial movements in France and Britain stimulated metropolitan left politics; Portuguese colonial wars drove the Carnation Revolution.

**Sources:**
- Scott, J. (1990). *Domination and the Arts of Resistance*. Yale University Press. (Consciousness-raising as the cognitive mechanism of resistance, not merely structural sovereignty recovery)
- Fanon, F. (1961). *The Wretched of the Earth*. Grove Press. (Colonial violence as a mirror deforming the colonizer's culture — the colonized subject's resistance redefines the categories of the metropole)
- Césaire, A. (1955). *Discourse on Colonialism*. Monthly Review Press. (Colonialism brutalizes the colonizer — "colonization works to decivilize the colonizer")
- Memmi, A. (1957). *The Colonizer and the Colonized*. Beacon Press. (Colonizer's identity distorted by the colonial relationship)

**Implementation (2026-04-10):** Stage 2b, after Axelrod cultural convergence. `avgGrievance` = mean `grievance[j]` across all non-core controlled islands. If `avgGrievance > 0.20`: `gPush = grievance_culture_drift_rate × (avgGrievance − 0.20)`. Colonizer CI `−= gPush` (→ Collective), IO `−= gPush` (→ Inward). New param: `grievance_culture_drift_rate = 0.008` (bounds [0.001, 0.03]).

**Effect on gameplay:** Extractive empires that accumulate high colonial grievance gradually drift their own culture toward collectivist/inward values, depressing their TFP growth (civic culture produces tech externalities) and reducing trade exposure. This creates an endogenous limit on extractive expansion — the empire's cultural profile becomes less competitive as the human cost of empire rises.

**Gap:** The direction of the effect (always toward Collective+Inward) is a simplification. Historically, colonial feedback could also produce nationalist/militarist drift (Inward but also more Individual in the fascist sense). A more complete model would allow culture drift direction to depend on which political faction absorbs the colonial feedback.

**→ Garden:** `garden/observations/the_consciousness_raising_feedback.md` (to be written)

---

### 14. Diamond first-contact epidemiology (Diamond 1997; McNeill 1976)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 6 first-contact), `sim_proxy_v2.py`

**Claim:** Virgin-soil epidemic severity scales with pathogen divergence between contacting populations. Crop-zone distance proxies for pathogen divergence — tropical and temperate crops produce different endemic pathogen environments.

**Sources:**
- Diamond, J. (1997). *Guns, Germs, and Steel*. W.W. Norton.
- McNeill, W. (1976). *Plagues and Peoples*. Anchor Books.

**Implementation:** `_cropDistance(cc, ct)` returns 0.2 (same crop), 0.5 (same zone), 0.8 (cross-zone), 1.0 (paddi↔papa maximum divergence). `mort = sev × cdist × (1 − immunity)`.

**→ Garden:** `garden/observations/the_disease_arc.md` (§§14–15, 17–18 treated as a system)

---

### 15. Endemicity transition (McNeill 1976)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 6 `immunity`), `sim_proxy_v2.py`

**Claim:** Prior trade contacts provide partial immunological exposure, reducing virgin-soil epidemic severity for later contacts. Diseases transition from epidemic (full virgin-soil mortality) to endemic (attenuated, familiar mortality) as populations develop partial immunity through gradual exposure.

**Sources:**
- McNeill, W. (1976). *Plagues and Peoples*. Anchor Books.
- Schmid, B. et al. (2015). "Plague Pathogen Transmission Through Rat Flea." *PNAS* 112(30).

**Implementation:** Per-pair relay contact age (not global count): `relayContactSince` Map records when each pair first established relay trade. `relayAge = tick − relayContactSince[pairKey]`. `immunity = min(0.6, relayAge × 0.04)`. Caps at 60% severity reduction after ~15 ticks of relay trade. Virgin-soil mortality still applies to pairs with no prior relay contact.

Wave epidemic mortality (Stage 5b) uses tech-gated reduction: `waveMortScale = max(0.20, 1.0 − (tech − 4.0) × 0.10)` for tech > 4. At tech 5 → 90% of base; tech 7 → 70%; tech 9 → 50%, floor 20%. Encodes McNeill's finding that industrial public health (sanitation, germ theory, vaccination) substantially reduced epidemic severity even for recurring diseases.

**Gap (partially resolved 2026-04-09):** Per-pair contact age fixed (was global count). Wave epidemic tech-gated mortality implemented. Remaining gap: no pathogen-specific immunity decay, no acquired immunity from prior epidemic waves.

**→ Garden:** `garden/observations/the_disease_arc.md`

---

## V. Disease Mechanics

### 16. Malaria carrying-capacity penalty (McNeill 1976; Gallup & Sachs 2001)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 5 population growth), `sim_proxy_v2.py`

**Claim:** Malaria reduces effective carrying capacity in tropical belts (abs_lat < 20°). Effect resolves at tech ≥ 6 (germ-theory / vector-control analogue). Gallup & Sachs estimated malaria reduces GDP per capita growth by ~1.3% per year in heavily-affected countries.

**Sources:**
- Gallup, J. & Sachs, J. (2001). "The Economic Burden of Malaria." *CID Working Paper 52*, Harvard.
- Packard, R. (2007). *The Making of a Tropical Disease*. Johns Hopkins University Press.

**Implementation:** `malariaFactor[i] = max(0, (20 − absLat) / 20)` for absLat < 20. `cap × = max(0.1, 1 − mSev × malaria_cap_penalty × (tech ≥ 6 ? 0.3 : 1.0))`.

**→ Garden:** `garden/observations/the_fever_belt.md`

---

### 17. Epidemic waves through trade networks (McNeill 1976; Schmid et al. 2015)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 5b), `sim_proxy_v2.py`

**Claim:** Periodic epidemic events originate in high-connectivity, high-density trade nodes and spread through the contact graph. Trade hubs function as disease amplifiers (port warehouse model — Antonine Plague / Black Death mechanism).

**Sources:**
- McNeill, W. (1976). *Plagues and Peoples*. Anchor Books.
- Schmid, B. et al. (2015). "Plague Pathogen Transmission." *PNAS* 112(30).
- Davenport, R. (2020). "Urbanization and Mortality in Britain." *Economic History Review*.

**Implementation:** `epiProb = epi_base_severity × 0.015 × (1 + nc × 0.2) × urbanFactor`. Spreads to trade partners with 35% probability each. Mortality 4–16% of affected population.

**→ Garden:** `garden/observations/the_disease_arc.md`

---

### 18. Urban disease sink (Davenport 2020; Wrigley & Schofield 1981)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 5b `urban_factor`), `sim_proxy_v2.py`

**Claim:** Pre-modern cities had negative natural population growth rates sustained only by rural immigration. High-density populations above carrying-capacity threshold face elevated epidemic risk.

**Sources:**
- Davenport, R. (2020). "Urbanization and Mortality in Britain, c.1520–c.1850." *Economic History Review* 73(2).
- Wrigley, E.A. & Schofield, R. (1981). *The Population History of England, 1541–1871*. Arnold.

**→ Garden:** `garden/observations/the_disease_arc.md`

---

## VI. Religion and Piety

### 19. Crisis→piety / prosperity→secular (Norris & Inglehart 2004)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 2c), `sim_proxy_v2.py`

**Claim:** Secularization is driven by existential security, not scientific sophistication. Societies under existential stress (energy crisis, war) show rising religiosity; prosperous societies show declining religiosity.

**Sources:**
- Norris, P. & Inglehart, R. (2004). *Sacred and Secular: Religion and Politics Worldwide*. Cambridge University Press.

**Implementation:** `if (er < 0.6) piety += dRate × (0.6 − er) × 2.5`. High tech → secular via `piety −= dRate × (tech − 7.0) × 0.25` (mediated by prosperity, compressed for sim resolution).

**→ Garden:** `garden/observations/the_piety_dynamics.md`

---

### 20. Reformation-model schism: piety + weak sovereignty → fragmentation (Grzymala-Busse 2023)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 2d), `sim_proxy_v2.py`

**Claim:** High piety combined with low-sovereignty peripheral holdings generates religious fragmentation. "Tilly Goes to Church": the Reformation produced enduring state fragmentation in the Holy Roman Empire (weak sovereignty) but not France or England (strong sovereignty). Schism dissolves above industrial tech threshold.

**Sources:**
- Grzymala-Busse, A. (2023). "Tilly Goes to Church: The Religious and Medieval Roots of European State Fragmentation." *American Political Science Review* 117(1).

**Implementation:** Pressure = `(piety − 0.60) × lowSovFrac × 3.0 × techDamp`. Fires at pressure > 1.0 → bottom third of low-sovereignty peripherals break away.

**→ Garden:** `garden/observations/the_piety_dynamics.md`

---

### 21. Piety as centripetal force: absorption bonus (Abbasid / Catholic models)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 7), `sim_proxy_v2.py`

**Claim:** High-piety empires integrate conquered populations faster through religious legitimation, missionary administration, and cultural conversion (Abbasid mawali system; Catholic missionary orders).

**Sources:**
- Kennedy, H. (2004). *The Prophet and the Age of the Caliphates*. Pearson.
- MacCulloch, D. (2009). *A History of Christianity*. Penguin.

**→ Garden:** `garden/observations/the_piety_dynamics.md` (centripetal force mechanic documented in "The Centripetal Force Mechanic" section)

---

## VII. Population Dynamics

### 22. Malthusian clamp + Boserupian release (Turchin & Nefedov 2009)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 1), `sim_proxy_v2.py`

**Claim:** For tech < 4, population growth is constrained by carrying capacity, producing Malthusian traps. Tech gains (Boserupian agricultural intensification) relax the constraint. Secular cycles of population growth → elite overproduction → instability → collapse operate over 200–300 year periods.

**Sources:**
- Turchin, P. & Nefedov, S. (2009). *Secular Cycles*. Princeton University Press.
- Malthus, T. (1798). *An Essay on the Principle of Population*.
- Boserup, E. (1965). *The Conditions of Agricultural Growth*. Aldine.

**→ Garden:** `garden/observations/the_malthusian_clamp.md`

---

### 23. Tech decay / collapse cascade (Tainter 1988; Cline 2014)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 5 tech decay), `sim_proxy_v2.py`

**Claim:** Collapse is an adaptive economic response to diminishing marginal returns on complexity. Energy shortfall → tech regression via maintenance cost shortfall. Linked to Bronze Age Collapse model: loss of trade-network inputs → cascade across interlocked systems.

**Sources:**
- Tainter, J. (1988). *The Collapse of Complex Societies*. Cambridge University Press.
- Cline, E. (2014). *1177 B.C.: The Year Civilization Collapsed*. Princeton University Press.

**Implementation:** `maintenance_cost = tech² × maintenance_rate`. If `energy_surplus < maintenance_cost`, `tech −= shortfall × decay_rate`. Desperation cascade then overrides allocation toward resource acquisition.

**→ Garden:** `garden/observations/the_collapse_cascade.md`

---

## VIII. Maritime Civilization Specifics

### 24. Thalassocratic fragility model (Spykman 1942; Friesian School)
**Grade: B** (no direct empirical precedent for full-ocean world)  
**Files:** Worldbuilding files, docs/DESIGN_SPEC.md

**Claim:** Sea-power-based empires are structurally dependent on trade route control, resistant to interior penetration, prone to rapid coalition formation/dissolution, and vulnerable to single-battle naval defeat. In a pure ocean world, Spykman's Rimland framework displaces Mackinder's Heartland theory entirely.

**Sources:**
- Spykman, N. (1942). *America's Strategy in World Politics*. Harcourt.
- Mackinder, H. (1904). "The Geographical Pivot of History." *Geographical Journal* 23(4).
- Kirch, P. (2000). *On the Road of the Winds*. University of California Press.

**Note:** No direct academic precedent exists for a ~95% ocean world. This is the thought-experiment frontier. Internal consistency with thalassocratic dynamics is the primary validity criterion.

**→ Garden:** `garden/observations/the_thalassocratic_condition.md`

---

## IX. Institutional Dynamics

### 25. Acemoglu-Robinson institutional lock-in (Why Nations Fail, 2012)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 5 TFP penalty; Stage 7 buildup), `aeolia-godot/optimization/sim_proxy_v2.py`

**Claim:** Extractive institutions — concentrated surplus extraction from subject populations under low-inclusivity political culture — block creative destruction by protecting elite rents against competitive entry. This produces tech stagnation independent of the naphtha resource curse; inclusive institutions (broad property rights, outward civic culture) allow Schumpeterian destruction and renewed growth.

The Acemoglu-Robinson "reversal of fortune" applies to Aeolia: polities that developed high-extraction colonial relationships early may lock into institutional structures that prevent industrial-era tech acceleration even when energy is abundant.

**Sources:**
- Acemoglu, D. & Robinson, J. (2012). *Why Nations Fail: The Origins of Power, Prosperity, and Poverty*. Crown.
- Acemoglu, D., Johnson, S. & Robinson, J. (2001). "The Colonial Origins of Comparative Development." *AER* 91(5).
- North, D. (1990). *Institutions, Institutional Change and Economic Performance*. Cambridge University Press.

**Implementation:** `extractiveness[core]` builds from `excess_extraction × (1 − inclusive_culture)` where `inclusive_culture = ci × 0.7 + io × 0.3` (civic + outward orientation). Decays slowly via inclusive reform rate. TFP penalty: `a0 × = (1 − extractiveness × extractiveness_tfp_penalty)`. Two new SimParams: `institutional_lock_rate` (default 0.12), `extractiveness_tfp_penalty` (default 0.40).

**Reversal-of-fortune diagnostic (implemented 2026-04-09):** `pre_colonial_state` dict records each archipelago's tech and population at the tick of first absorption. `reversal_of_fortune_r` (Spearman rank correlation) in the output dict measures the correlation between pre-colonial tech rank and final tech rank. A negative value confirms the AJR reversal pattern: formerly more-prosperous polities ended up comparatively worse off after colonization. On seed 216089, r ≈ +0.03 (no strong reversal), consistent with AJR's finding that reversal appears in cross-section, not on individual simulation paths. The diagnostic is now available for optimizer-level analysis across seeds.

**Known diagnostic flaw (identified 2026-04-10):** The current Spearman r correlates pre-absorption tech with post-game tech of the *same archipelago*, which primarily measures tech diffusion from colonizer to colony (positive r = tech propagated from colonizer, not reversal). AJR (2001) tested a different proposition: that pre-1500 *indigenous population density* (proxy for institutional sophistication) negatively predicts *post-colonial per-capita income*. The simulation's diagnostic needs restructuring to: (a) compare pre-absorption relative tech advantage of the *colonized territory* against the *colonizer*, (b) measure post-game relative tech *disadvantage* of the colonized territory vs. world average at game end. A negative Spearman r under that formulation would confirm the reversal — that territories which were *less disadvantaged* relative to eventual colonizers ended up more disadvantaged post-contact. **Status: marked for fix in next diagnostic revision session.**

**→ Garden:** `garden/observations/the_lock_in_mechanics.md`

---

## X. Environmental Mechanics

### 26. Crop failure stochasticity (Le Roy Ladurie 1967; Davis 2001)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 0 environmental pre-pass), `sim_proxy_v2.py`

**Claim:** Pre-industrial agricultural yields were stochastic, subject to periodic failure from climate variability, pests, and soil exhaustion. Tech development reduces failure probability (storage, irrigation, crop variety buffering). Failure events in extractively-administered territories produce amplified mortality per Davis (2001).

**Sources:**
- Le Roy Ladurie, E. (1967). *Times of Feast, Times of Famine*. Doubleday.
- Davis, M. (2001). *Late Victorian Holocausts: El Niño Famines and the Making of the Third World*. Verso.

**Implementation:** `cropFailureModifier[]` per arch; failure probability tech-gated (higher for tech < 5). Failure reduces yield by 20–60%; recovery at +0.25/tick. Davis amplification (both engines): `davisModifier = baseModifier × (1 − extractiveness[archCore] × davis_amplification)`, floored at 0.15. New param: `davis_amplification` (default 0.30) — at extractiveness=1.0, failure modifier is 30% worse than baseline. Ported to Python reference engine 2026-04-10.

**Gap (resolved 2026-04-09):** Davis amplification now implemented in SimEngine.js. Recovery rate remains uniform regardless of institutional quality — a secondary Davis finding (that distribution infrastructure affects recovery speed, not just severity) is not modeled.

**→ Garden:** `garden/observations/the_environmental_shocks.md`

---

### 27. Fishery depletion: tragedy of the commons (Hardin 1968; Ostrom 1990)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 0 fishery stock update), `sim_proxy_v2.py`

**Claim:** Open-access fisheries are subject to progressive depletion when extraction rate exceeds recovery rate, with stock collapse as the endpoint. Commons governance (Ostrom) can prevent collapse; absence of governance produces the Hardin tragedy.

**Sources:**
- Hardin, G. (1968). "The Tragedy of the Commons." *Science* 162(3859).
- Ostrom, E. (1990). *Governing the Commons*. Cambridge University Press.

**Implementation:** `fisheryStock[]` recovers at 8%/tick; depletes proportional to coastal population × fishing_intensity. Collapse below threshold produces yield reduction until stock recovers. Ostrom commons governance (both engines): `commonsGov = clamp((ioPos × 0.5 + inclus × 0.5 + 0.5) × 0.5, 0, 0.70)` where `ioPos` = IO culture axis, `inclus = 1 − extractiveness`. `overExploit × = (1 − commonsGov × ostrom_commons_factor)`. At max governance (outward, inclusive): depletion reduced by ~38.5%. New param: `ostrom_commons_factor` (default 0.55). Ported to Python reference engine 2026-04-10.

**Gap (partially resolved 2026-04-09):** Institutional differentiation implemented via culture-space + extractiveness proxy. Remaining gap: Ostrom's specific governance conditions (territorial use rights, seasonal closures, graduated sanctions, monitoring) are not individually modeled — governance capacity is a continuous function of culture/extractiveness rather than a discrete institutional choice.

**→ Garden:** `garden/observations/the_environmental_shocks.md`

---

## XI. Power Transition

### 30. Approach to parity: power transition period (Organski 1958; Gilpin 1981)
**Grade: B−** (emergent, not explicitly encoded)  
**Files:** `src/engine/SimEngine.js` (Stage 3 industrial signals, Stage 4 DF detection), `sim_proxy_v2.py`

**Claim:** The most dangerous period in great-power competition is not hegemonic dominance or post-parity deterrence, but the transition when the challenger closes the capability gap. The incumbent has incentive for preemptive war (closing window for successful prevention); the challenger has incentive to accelerate (closing window for being destroyed while vulnerable). Organski (1958) proposed this as power transition theory; Gilpin (1981) extended it to hegemonic war theory.

**Sources:**
- Organski, A.F.K. (1958). *World Politics*. Knopf.
- Gilpin, R. (1981). *War and Change in World Politics*. Cambridge University Press.
- Modelski, G. (1987). *Long Cycles in World Politics*. University of Washington Press.

**Implementation:** The power transition period in Aeolia runs from tech ~7 (pyra scramble, proto-hegemons acquiring strategic energy assets) to DF firing (tech ≥ 9 in both, awareness > 0.30). Duration: approximately 8 ticks (400 years). The pyra resource curse (tech ≥ 8.5, 60% curse strength) fires during this window — polities racing for strategic advantage simultaneously acquire the resource that penalizes institutional development. Nuclear peer awareness accumulates at 0.04/tick per side from when both reach tech ≥ 9; the 0.30 threshold requires ~7–8 ticks, producing a brief window of mutual nuclear capability before formal deterrence.

**Implementation (added 2026-04-10):** When two polities both have tech ≥ 7.0 and mutual awareness > 0.10 but DF hasn't fired: the technologically leading polity receives `+power_transition_bonus` (default 2.0) in expansion targeting against the lagging polity's territory. This creates a pre-DF "scramble" where the incumbent has incentive for territorial pre-positioning. New SimParam: `power_transition_bonus` (default 2.0).

**Remaining gap:** The mechanic models increased expansion pressure but not the full Organski/Gilpin prediction of preemptive war incentives. The leading polity gets an expansion bonus, not a first-strike mechanic. The lagging polity does not receive a defensive posture correction.

**→ Garden:** `garden/observations/the_strange_equilibrium.md` (§ "The Approach to Parity: Power Transition Before Dark Forest")

---

## XII. Culture and Economic Behavior

### 32. Culture-to-behavior mapping: civic culture and TFP (Putnam 1993; Inglehart 1997)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (`_sharesFromPos`, `_A0FromPos`), `sim_proxy_v2.py`

**Claim:** Culture position on the CI (Collective↔Individual) and IO (Inward↔Outward) axes determines economic behavior through two functions: allocation shares (how surplus is divided among expansion, tech investment, and consolidation) and baseline TFP (A₀). Outward orientation drives both expansion and tech investment (trade-network learning); Individual orientation drives TFP independently (civic individualism → productive innovation). The highest-performing polities combine both (maritime civic cultures); the lowest combine neither (inward collective / amoral familist).

**Sources:**
- Putnam, R. (1993). *Making Democracy Work: Civic Traditions in Modern Italy*. Princeton University Press.
- Inglehart, R. (1997). *Modernization and Postmodernization*. Princeton University Press.
- Inglehart, R. (2018). *Cultural Evolution*. Cambridge University Press.
- Banfield, E. (1958). *The Moral Basis of a Backward Society*. Free Press.

**Implementation:**
- `expS = base_expansion + outward_expansion_coeff × outward + individual_expansion_coeff × individual`
- `tecS = base_tech + outward_tech_coeff × outward`
- `A₀ = base_A0 + individual_A0_coeff × individual + outward_A0_coeff × outward`
- All mappings linear; individual and outward treated as independent additive contributors.

**Gap:** Linear mapping misses threshold effects (amoral familism → civic culture transition non-linear) and interaction effects (individual × outward synergy understated). Consolidation is a residual rather than a modeled preference.

**→ Garden:** `garden/observations/the_culture_allocation_link.md`

---

## XIII. Staple Trap and Specialist Economies

### 33. Relay specialist economies and the staple trap (Innis 1930; Watkins 1963)
**Grade: B−** (emergent, not explicitly encoded)  
**Files:** `src/engine/SimEngine.js` (relay layer trade, Greif relay bonus), `sim_proxy_v2.py`

**Claim:** Economies built on commodity export develop infrastructure, institutions, and political economies oriented toward that commodity, creating structural barriers to diversification — the "staple trap." In Aeolia, nori-culture relay specialist polities develop commercial dependencies on the relay layer that make them prosperous during the relay era and structurally exposed during transitions to administered trade and post-DF proxy competition. The success of relay specialization creates the conditions for its vulnerability.

**Sources:**
- Innis, H. (1930). *The Fur Trade in Canada*. University of Toronto Press.
- Innis, H. (1940). *The Cod Fisheries: The History of an International Economy*. Yale University Press.
- Watkins, M. (1963). "A Staple Theory of Economic Growth." *Canadian Journal of Economics and Political Science* 29(2).

**Implementation:** The staple trap is emergent rather than mechanically encoded. Nori polities' initial culture seed ([0.35, 0.65] outward/individual) drives high relay bonus capture (Greif mechanism), which drives prosperity → reinforced outward drift. The loop reinforces relay specialization without a mechanic forcing diversification. The trap appears in the data: nori polities in the relay chokepoint position are commercially central and strategically exposed in the post-DF era.

**Gap:** Transportation infrastructure is not modeled; the spatial dimension of Innis's argument (infrastructure orientation constrains switching costs) is absent. The staple trap is visible in commercial data but not in explicit infrastructure constraints.

**→ Garden:** `garden/observations/the_staple_trap.md`

---

### 34. Tilly coercion-capital differentiation (Tilly 1990)
**Grade: B** (added 2026-04-10)  
**Files:** `src/engine/SimEngine.js` (Stage 6 expansion scoring, Stage 7 sovereignty init), `sim_proxy_v2.py`

**Claim:** States form through two structurally different paths: coercion-intensive (military conquest, garrison occupation, low initial sovereignty) and capital-intensive (trade dominance, commercial integration, higher initial sovereignty). Culture position on the CI/IO axes determines which path a polity follows: collective+inward = high coercion; individual+outward = high capital.

**Sources:**
- Tilly, C. (1990). *Coercion, Capital, and European States, AD 990–1992*. Blackwell.
- Mann, M. (1986). *The Sources of Social Power*, Vol. 1. Cambridge University Press. (Infrastructural vs. despotic power — related framework)
- Herbst, J. (2000). *States and Power in Africa*. Princeton University Press. (Cost of projecting sovereignty over distance — directly relevant to archipelago world)

**Implementation:** `coercion = ((1 − ci) + (1 − io)) / 4` from core culture position. High-coercion polities get expansion bonus for close targets and penalty for distant targets (garrison projection). Low-coercion (capital-intensive) polities get bonus for high-trade-value targets. On conquest, initial sovereignty = `base + (1 − coercion) × 0.20`, so civic conquests start with higher sovereignty (trade integration) while coercive conquests start lower (garrison occupation).

**Gap:** Tilly's argument is specifically about the interaction of war-making, state-making, extraction, and capital accumulation as four interdependent processes. The simulation captures the coercion-capital axis but not the war-making → extraction → state-making feedback loop. Infrastructure (Mann's infrastructural power) is not modeled.

---

## XIV. Resource Competition and Strategic Scrambles

### 31. Three-threshold resource model and strategic scrambles (Le Billon 2012; Kennedy 1987)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 3 detection, Stage 8 naphtha depletion), `sim_proxy_v2.py`

**Claim:** Resources cross three discrete thresholds: geological Detection (always possible), tech-gated Exploitation (profitable only above tech threshold), and Strategic Valuation (event-triggered recognition of military-industrial necessity). The Strategic Valuation threshold triggers the scramble — a punctuated competitive rush for control of a resource that was previously treated as commercially ordinary. Geographic concentration of strategic resources produces prisoner's dilemma dynamics: rational individual scrambling produces collectively destructive outcomes (overextension, institutional degradation, conflict in contested zones).

**Sources:**
- Le Billon, P. (2012). *Wars of Plunder: Conflicts, Profits and the Politics of Resources*. Columbia University Press.
- Kennedy, P. (1987). *The Rise and Fall of the Great Powers*. Random House.
- Westing, A.H. (1986). *Global Resources and International Conflict*. Oxford University Press.

**Implementation:** `naphtha_desire_mult` expansion bonus fires at tech ~5 for polities below naphtha-fraction threshold. `pyra_desire_mult` fires at tech ~8. Strategic Valuation applies simultaneously to all polities at threshold crossing (no private-information first-mover advantage implemented).

**Gap:** Simultaneous Strategic Valuation overstates coordination in scramble recognition. Historical scrambles involve private-information early movers who pre-position before collective recognition. No differential harm modeling for resource-motivated vs. non-resource territorial expansion.

**→ Garden:** `garden/observations/the_scramble_dynamics.md`

---

## XV. Collective Action and Institutional Fragility

### 28. Desperation expansion as collective action failure (Olson 1965; Tainter 1988)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 6 expansion targeting under desperation), `sim_proxy_v2.py`

**Claim:** The desperation cascade produces expansion that is locally rational for each polity but collectively catastrophic — a collective action failure in which multiple polities simultaneously under resource stress attack each other, consuming resources none of them can afford to spend. The mechanism is structurally identical to Olson's logic of collective action applied to inter-polity competition: each actor's individually rational response to the common-pool problem intensifies the problem for all actors.

**Sources:**
- Olson, M. (1965). *The Logic of Collective Action*. Harvard University Press.
- Tainter, J. (1988). *The Collapse of Complex Societies*. Cambridge University Press.
- Cline, E. (2014). *1177 B.C.: The Year Civilization Collapsed*. Princeton University Press.

**Implementation:** Desperation cascade overrides the polity's normal cultural allocation, boosting expansion share. Polities under equal resource stress from the same systemic cause (crop failure year, fishery depletion, epidemic) simultaneously target each other — neighboring polities that are also under stress and do not have surplus to offer the conqueror. The cascade is self-reinforcing because failed expansion raises maintenance cost and deepens the resource shortfall.

**Gap:** The simulation does not model the coordination mechanism by which real polities have sometimes escaped this collective action failure (Concert of Europe analog, mutual contraction agreements). The Strange Peace's deterrence structure is a partial implementation — the −12.0 targeting penalty between hegemons prevents the cascade at the nuclear tier — but pre-nuclear polities have no equivalent coordination mechanism.

**→ Garden:** `garden/observations/the_desperation_trap.md`

---

### 29. Veto players and crisis reallocation lag (Tsebelis 2002; Olson 1982)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (desperation threshold, allocation override speed), `sim_proxy_v2.py`

**Claim:** Polities with distributed governance — multiple veto players who must agree before resource allocation shifts — respond more slowly to resource crises than polities with unified command structures. Tsebelis's core finding: more veto players → greater policy stability in normal times → greater policy fragility in crisis times. The tradeoff is structural, not correctable by intent. Olson's Rise and Decline adds the distributional dimension: established veto coalitions capture allocation rents and resist shifts that would cost their constituency.

**Sources:**
- Tsebelis, G. (2002). *Veto Players: How Political Institutions Work*. Princeton University Press.
- Olson, M. (1982). *The Rise and Decline of Nations*. Yale University Press.
- North, D. (1990). *Institutions, Institutional Change and Economic Performance*. Cambridge University Press.

**Implementation:** `desperation_threshold` varies by polity but does not explicitly encode governance type. The mechanic operationalizes governance type through outcome proxies: Sovereignty-type polities (high veto players) enter the cascade more readily under equivalent resource stress than Reach-type polities (unified command). The simulation does not track veto-player count directly; the variation is embedded in the effective allocation override speed.

**Gap:** The veto players mechanic is not explicitly parameterized in SimParams. The variation is implicit in initial culture-space positioning and allocation share functions. A more explicit implementation would encode a `governance_concentration` variable that modifies allocation override speed and `desperation_threshold` directly, allowing the Tsebelis tradeoff to be studied across the parameter space.

**→ Garden:** `garden/observations/the_veto_players_trap.md`

---

## XVI. Known Gaps (Priority Order)

| Gap | Status | Notes |
|-----|--------|-------|
| Axelrod freezing: divergent cultures don't converge | ✓ Implemented | culture_dist >= 0.85 → comp = 0; full cultural isolation above freeze threshold |
| Alliance formation mechanic | ✓ Implemented | Stage 4.5 Walt alignment: `alignment[i]` drifts toward less-threatening hegemon post-DF; opposed-hegemon targeting penalty up to 2.5× |alignment| |
| AR reversal-of-fortune diagnostic | ✓ Implemented | `pre_colonial_state` + `reversal_of_fortune_r` (Spearman r) in output; r ≈ +0.03 on seed 216089 (cross-sectional pattern, not single-path) |
| Proxy war casualties | ✓ Implemented | Population losses in DF-era expansion into rival's sub-nuclear periphery |
| Doctrinal innovation in schism | ✓ Implemented | Ungoverned breakaway polities receive Reformed culture shift (+0.30 CI, +0.15 IO); Weber (1904) |
| Endemicity at wave-epidemic level | ✓ Implemented | Per-pair relay contact age replaces global count; 0.04/tick immunity buildup |
| Resource curse without naphtha | ✓ Implemented | Pyra MIC curse (tech ≥ 8.5; 60% of naphtha curse strength) |
| Davis / Ostrom not ported to Python | ✓ Ported | Both Davis amplification and Ostrom commons governance ported to sim_proxy_v2.py (2026-04-10) |
| Scott consciousness-raising gap | ✓ Partially implemented | Mechanic 35: high colonial grievance drifts colonizer culture → Collective+Inward; models ideological feedback of resistance on metropole (Fanon/Césaire) |
| Frank/Cardoso unequal exchange | ✓ Implemented | Mechanic 36: administered-layer trade surplus drains toward more-extractive party proportional to extractiveness gap |

---

*Last updated: 2026-04-10 (Session 7). Maintained by Clio. 36 sections total. §35–§36 added this session (consciousness-raising feedback, Frank/Cardoso unequal exchange). Davis and Ostrom ported to Python reference. Hegemonic guard added to DF detection (top-3 by territory). 45 SimParams total. Garden cross-references complete (§1–§34); §35–§36 gardens pending.*
