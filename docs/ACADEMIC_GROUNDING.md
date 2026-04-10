# Aeolia — Academic Grounding

**Mechanic-by-mechanic citation map.**  
For each simulation mechanic, this document records the scholarly framework it operationalizes, the specific causal claim encoded, the file(s) where it lives, and any known gaps between the simulation and the literature.

Grading scale for empirical grounding: **A** (directly empirically validated), **B** (theoretically well-grounded, plausible parameters), **C** (defensible simplification, weak empirical precedent).

---

## I. State Formation and Political Culture

### 1. Crop-to-culture mapping (Wittfogel; Almond & Verba)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (§10 `_CROP_CULTURE_SEED`), `aeolia-godot/optimization/sim_proxy_v2.py`

**Claim:** Hydraulic agriculture (paddi) produces Subject cultures (bureaucratic, collectively organized); dryland grain agriculture (emmer) produces Civic cultures (competitive, pluralistic); marginal or maritime crops produce Parochial cultures.

**Sources:**
- Wittfogel, K. (1957). *Oriental Despotism: A Comparative Study of Total Power*. Yale University Press.
- Almond, G. & Verba, S. (1963). *The Civic Culture*. Princeton University Press.
- Inglehart, R. & Welzel, C. (2005). *Modernization, Cultural Change, and Democracy*. Cambridge University Press.

**Implementation:** `_CROP_CULTURE_SEED` seeds each crop in a 2D continuous culture space (CI = Collective↔Individual, IO = Inward↔Outward). Paddi at (−0.55, −0.20) encodes hydraulic bureaucracy; emmer at (0.45, 0.55) encodes mercantile pluralism.

**Gap:** Wittfogel's hypothesis has been criticized for being unfalsifiable and selecting on the dependent variable (Levi 1988). Aeolia uses it as a generative starting condition, not a deterministic law — polities drift from their seed positions based on material circumstances.

---

### 2. Continuous culture-space drift (Axelrod 1997; Boyd & Richerson 1985)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 2b), `sim_proxy_v2.py`

**Claim:** Political culture drifts based on prosperity (→ Individual), crisis (→ Collective), trade exposure (→ Outward), resource stress (→ Inward). Culture is not fixed but responds to material conditions.

**Sources:**
- Axelrod, R. (1997). "The Dissemination of Culture." *Journal of Conflict Resolution* 41(2).
- Boyd, R. & Richerson, P. (1985). *Culture and the Evolutionary Process*. University of Chicago Press.
- Norris, P. & Inglehart, R. (2004). *Sacred and Secular*. Cambridge University Press.

**Gap:** Axelrod's model predicts cultural freezing/polarization for maximally divergent cultures. Aeolia currently does not implement a freezing threshold — divergent cultures converge more readily than the literature predicts.

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

### 4. IR posture matrix (Mearsheimer; Walt; Schweller)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 2 `_POSTURE_TABLE`), `sim_proxy_v2.py`

**Claim:** High capability + high threat → offensive expansion (offensive realism). Medium capability + high threat → alliance-seeking (balance-of-threat). Low capability + high threat → bandwagoning (Schweller revisionist states).

**Sources:**
- Mearsheimer, J. (2001). *The Tragedy of Great Power Politics*. Norton.
- Walt, S. (1987). *The Origins of Alliances*. Cornell University Press.
- Schweller, R. (1994). "Bandwagoning for Profit." *International Security* 19(1).

---

### 5. Dark Forest / Security Dilemma at civilizational scale
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 3–4), `sim_proxy_v2.py`

**Claim:** First contact between nuclear-capable civilizations replicates the security dilemma: defensive preparations are indistinguishable from offensive ones. Mutual awareness triggers a deterrence equilibrium, not open war.

**Sources:**
- Schelling, T. (1960). *The Strategy of Conflict*. Harvard University Press.
- Schelling, T. (1966). *Arms and Influence*. Yale University Press.
- Waltz, K. (1981). "The Spread of Nuclear Weapons: More May Be Better." *Adelphi Paper* 171. IISS.

**Implementation:** `otherAwareness` accumulates at 0.04/tick once both polities have tech ≥ 9.0; fires DF when awareness > 0.30. Arms race continues post-DF with tech bonus for hegemons above 8.5.

---

### 6. Stability-instability paradox (Snyder 1965; Waltz 1981)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 6 `proxyBonus`), `sim_proxy_v2.py`

**Claim:** Nuclear deterrence stabilizes direct inter-hegemon conflict but paradoxically enables sub-nuclear proxy warfare. Hegemons compete aggressively in each other's client periphery because the nuclear threshold prevents escalation.

**Sources:**
- Snyder, G. (1965). "The Balance of Power and the Balance of Terror." In *Balance of Power*, ed. Paul Seabury.
- Waltz, K. (1981). *The Spread of Nuclear Weapons*. IISS.

**Implementation:** After DF fires, nuclear hegemons receive a +3.0 expansion bonus targeting non-nuclear territory in the rival hegemon's contact network, partially offsetting the −12.0 deterrence penalty against each other.

---

## III. Political Economy and Trade

### 7. Solow-Romer growth with energy coupling (Ayres & Warr 2005)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 5), `sim_proxy_v2.py`

**Claim:** Output is a function of capital, labor, and TFP; TFP depends on energy availability and trade-network connectivity. Energy is a fundamental production factor, not merely an input cost.

**Sources:**
- Solow, R. (1956). "A Contribution to the Theory of Economic Growth." *Quarterly Journal of Economics* 70(1).
- Romer, P. (1990). "Endogenous Technological Change." *Journal of Political Economy* 98(5).
- Ayres, R. & Warr, B. (2005). "Accounting for Growth: The Role of Physical Work." *Structural Change and Economic Dynamics* 16.

**Implementation:** `delta_tech = A₀ × crop_exp × share_mult × accel_rate × contact_mult × energy_mult`. `energy_mult = er × energy_to_tfp` directly couples energy surplus to TFP.

---

### 8. Three-layer trade system: Subsistence → Relay → Administered (Abu-Lughod; Wallerstein; Braudel)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Trade Pre-Pass), `sim_proxy_v2.py`

**Claim:** Trade escalates through three regimes gated by technology: subsistence exchange (direct neighbors, bulk goods), relay trade (multi-hop luxury circuits), administered trade (polity-directed bulk extraction). Each regime has different markup, range, and complementarity dynamics.

**Sources:**
- Abu-Lughod, J. (1989). *Before European Hegemony*. Oxford University Press.
- Wallerstein, I. (1974). *The Modern World-System*, Vol. I. Academic Press.
- Braudel, F. (1949/1972). *The Mediterranean*. University of California Press.

---

### 9. Greif relay information asymmetry (Greif 1989)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Trade Pre-Pass `relayBonusA/B`), `sim_proxy_v2.py`

**Claim:** High-connectivity intermediary nodes capture asymmetric price differentials by controlling information flows between trading partners who cannot observe each other's prices. Per-contact bonus represents the Maghribi trader coalition model.

**Sources:**
- Greif, A. (1989). "Reputation and Coalitions in Medieval Trade: Evidence on the Maghribi Traders." *Journal of Economic History* 49(4).
- Greif, A. (1993). "Contract Enforceability and Economic Institutions in Early Trade." *American Economic Review* 83(3).

**Implementation:** `relayBonusA = min(0.40, contactSet[tc].size × greif_relay_bonus)`. Nodes with more contacts capture a larger share of the trade surplus.

---

### 10. Prebisch-Singer declining terms of trade (Prebisch 1950; Singer 1950)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Trade Pre-Pass `psA/psB`), `sim_proxy_v2.py`

**Claim:** Bulk calorie-producing peripheries face structurally declining terms of trade relative to specialty/luxury/relay nodes. Paddi, taro, sago, and papa are bulk staples; emmer and nori produce storable specialty goods (stimulants, fibers) commanding higher per-unit value.

**Sources:**
- Prebisch, R. (1950). *The Economic Development of Latin America and Its Principal Problems*. ECLA/UN.
- Singer, H. (1950). "The Distribution of Gains between Investing and Borrowing Countries." *American Economic Review* 40(2).

**Implementation:** `psA = prebisch_bulk_discount (0.75)` for bulk crops, `1.0` for specialty crops. Applied per trading side, producing asymmetric benefits from the same trade relationship.

---

### 11. Resource curse: Sachs-Warner / Ross (extractive institutions)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 5 `a0` penalty), `sim_proxy_v2.py`

**Claim:** Naphtha-rich polities in the industrial era develop extractive institutions — elite resource rents that divert investment from broad-based human capital development, penalizing TFP growth.

**Sources:**
- Sachs, J. & Warner, A. (1995). "Natural Resource Abundance and Economic Growth." *NBER Working Paper 5398*.
- Ross, M. (2012). *The Oil Curse*. Princeton University Press.
- Vitalis, R. (2018). "The Myth of the Authoritarian Oil State." *Perspectives on Politics* 16(2).

**Implementation:** Fires when polity controls > ~13% of world initial C stock, tech 6–9.5. `curse = clamp(polityFrac × 3.0 − 0.4, 0, 0.5); a0 × = (1 − curse × resource_curse_strength)`.

**Gap:** None. See Mechanic 25 (Acemoglu-Robinson) below.

---

## IV. Colonial Dynamics and Sovereignty

### 12. Wallerstein world-systems hierarchy (six-level sovereignty taxonomy)
**Grade: A** (as structural framework) / **B** (as mechanic)  
**Files:** `src/engine/SimEngine.js` (state output `status` field), `sim_proxy_v2.py`

**Claim:** Colonial relationships produce a continuous sovereignty spectrum from full autonomy through tributary, client, garrison, colony to full core integration. Status is determined by sovereignty score, not categorical assignment.

**Sources:**
- Wallerstein, I. (1974). *The Modern World-System*. Academic Press.
- Frank, A.G. & Gills, B. (1993). *The World System: Five Hundred Years or Five Thousand?*. Routledge.

---

### 13. Scott's resistance: self-limiting colonialism (Scott 1985, 1990)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 7 `grievance`), `sim_proxy_v2.py`

**Claim:** Colonial extraction above a tolerable threshold generates grievance that accelerates sovereignty recovery, making extraction self-limiting. "It is not exploitation per se, but exploitation beyond what is deemed legitimate that triggers organized resistance."

**Sources:**
- Scott, J. (1985). *Weapons of the Weak: Everyday Forms of Peasant Resistance*. Yale University Press.
- Scott, J. (1990). *Domination and the Arts of Resistance*. Yale University Press.

**Implementation:** `grievance[i]` accumulates from excess extraction above `sov_extraction_decay × 0.5`. `resistanceMult = 1 + grievance × grievance_resistance_mult` amplifies the recovery term in sovereignty drift.

**Gap:** Scott's model emphasizes micro-level everyday resistance, not just aggregate sovereignty recovery. The current implementation operationalizes the structural outcome (extraction → resistance → recovery) without modeling the cultural/cognitive mechanism (consciousness-raising, participation axis drift).

---

### 14. Diamond first-contact epidemiology (Diamond 1997; McNeill 1976)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 6 first-contact), `sim_proxy_v2.py`

**Claim:** Virgin-soil epidemic severity scales with pathogen divergence between contacting populations. Crop-zone distance proxies for pathogen divergence — tropical and temperate crops produce different endemic pathogen environments.

**Sources:**
- Diamond, J. (1997). *Guns, Germs, and Steel*. W.W. Norton.
- McNeill, W. (1976). *Plagues and Peoples*. Anchor Books.

**Implementation:** `_cropDistance(cc, ct)` returns 0.2 (same crop), 0.5 (same zone), 0.8 (cross-zone), 1.0 (paddi↔papa maximum divergence). `mort = sev × cdist × (1 − immunity)`.

---

### 15. Endemicity transition (McNeill 1976)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 6 `immunity`), `sim_proxy_v2.py`

**Claim:** Prior trade contacts provide partial immunological exposure, reducing virgin-soil epidemic severity for later contacts. Diseases transition from epidemic (full virgin-soil mortality) to endemic (attenuated, familiar mortality) as populations develop partial immunity through gradual exposure.

**Sources:**
- McNeill, W. (1976). *Plagues and Peoples*. Anchor Books.
- Schmid, B. et al. (2015). "Plague Pathogen Transmission Through Rat Flea." *PNAS* 112(30).

**Implementation:** `priorContacts = count of non-null firstContactTick entries before current tick`. `immunity = min(0.6, priorContacts × 0.02)`. Caps at 60% severity reduction.

**Gap:** The implementation uses a global prior-contact count as a proxy for population-level immunity. A more accurate model would track per-arch contact history and pathogen-specific immunity decay. The endemicity transition also applies only to first contacts, not to epidemic waves.

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

---

### 18. Urban disease sink (Davenport 2020; Wrigley & Schofield 1981)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 5b `urban_factor`), `sim_proxy_v2.py`

**Claim:** Pre-modern cities had negative natural population growth rates sustained only by rural immigration. High-density populations above carrying-capacity threshold face elevated epidemic risk.

**Sources:**
- Davenport, R. (2020). "Urbanization and Mortality in Britain, c.1520–c.1850." *Economic History Review* 73(2).
- Wrigley, E.A. & Schofield, R. (1981). *The Population History of England, 1541–1871*. Arnold.

---

## VI. Religion and Piety

### 19. Crisis→piety / prosperity→secular (Norris & Inglehart 2004)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 2c), `sim_proxy_v2.py`

**Claim:** Secularization is driven by existential security, not scientific sophistication. Societies under existential stress (energy crisis, war) show rising religiosity; prosperous societies show declining religiosity.

**Sources:**
- Norris, P. & Inglehart, R. (2004). *Sacred and Secular: Religion and Politics Worldwide*. Cambridge University Press.

**Implementation:** `if (er < 0.6) piety += dRate × (0.6 − er) × 2.5`. High tech → secular via `piety −= dRate × (tech − 7.0) × 0.25` (mediated by prosperity, compressed for sim resolution).

---

### 20. Reformation-model schism: piety + weak sovereignty → fragmentation (Grzymala-Busse 2023)
**Grade: A**  
**Files:** `src/engine/SimEngine.js` (Stage 2d), `sim_proxy_v2.py`

**Claim:** High piety combined with low-sovereignty peripheral holdings generates religious fragmentation. "Tilly Goes to Church": the Reformation produced enduring state fragmentation in the Holy Roman Empire (weak sovereignty) but not France or England (strong sovereignty). Schism dissolves above industrial tech threshold.

**Sources:**
- Grzymala-Busse, A. (2023). "Tilly Goes to Church: The Religious and Medieval Roots of European State Fragmentation." *American Political Science Review* 117(1).

**Implementation:** Pressure = `(piety − 0.60) × lowSovFrac × 3.0 × techDamp`. Fires at pressure > 1.0 → bottom third of low-sovereignty peripherals break away.

---

### 21. Piety as centripetal force: absorption bonus (Abbasid / Catholic models)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 7), `sim_proxy_v2.py`

**Claim:** High-piety empires integrate conquered populations faster through religious legitimation, missionary administration, and cultural conversion (Abbasid mawali system; Catholic missionary orders).

**Sources:**
- Kennedy, H. (2004). *The Prophet and the Age of the Caliphates*. Pearson.
- MacCulloch, D. (2009). *A History of Christianity*. Penguin.

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

---

### 23. Tech decay / collapse cascade (Tainter 1988; Cline 2014)
**Grade: B**  
**Files:** `src/engine/SimEngine.js` (Stage 5 tech decay), `sim_proxy_v2.py`

**Claim:** Collapse is an adaptive economic response to diminishing marginal returns on complexity. Energy shortfall → tech regression via maintenance cost shortfall. Linked to Bronze Age Collapse model: loss of trade-network inputs → cascade across interlocked systems.

**Sources:**
- Tainter, J. (1988). *The Collapse of Complex Societies*. Cambridge University Press.
- Cline, E. (2014). *1177 B.C.: The Year Civilization Collapsed*. Princeton University Press.

**Implementation:** `maintenance_cost = tech² × maintenance_rate`. If `energy_surplus < maintenance_cost`, `tech −= shortfall × decay_rate`. Desperation cascade then overrides allocation toward resource acquisition.

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

**Gap:** The reversal-of-fortune path — where *initially high-population* islands become colonial periphery and stagnate — is implicit but not tracked as a specific diagnostic. Full Acemoglu-Johnson-Robinson would require tracking pre-colonial prosperity rank vs. contemporary colonial status.

---

## X. Known Gaps (Priority Order)

| Gap | Grade if unaddressed | Recommended fix |
|-----|---------------------|-----------------|
| Axelrod freezing: divergent cultures don't converge | C | Add `frozen_divergence` threshold — cultures too far apart stop trading and polarize |
| Proxy war casualties | C | DF-era conflicts should produce population-level casualties in contested periphery |
| Doctrinal innovation in schism | C | Schism should sometimes produce breakaway "reformed" culture — doctrinal heterodoxy as trigger |
| Endemicity at wave-epidemic level | C | Wave epidemic severity should decay with contact age per-pair, not globally |
| Alliance formation mechanic | B→C | Walt balance-of-threat predicts formal alliances; currently only informal contact bonuses |
| Resource curse without naphtha | ~~C~~ | Implemented: pyra MIC curse added (tech ≥ 8.5; 60% of naphtha curse strength) |
| AR reversal-of-fortune diagnostic | C | Track pre-colonial prosperity rank vs. post-colonial status for AJR validation |

---

*Last updated: 2026-04-09. Maintained by Clio.*
