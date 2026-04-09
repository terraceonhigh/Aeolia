# Aeolia Simulation — Lanthier Consultation Brief

**Source:** Interview with Prof. Michael Lanthier, Department of History, UBC  
**Date:** April 7  
**Interviewer:** Terrace Hung (lead researcher / architect)  
**Purpose:** Historical variable elicitation for Aeolia simulation engine  

---

## World Premise

Aeolia is a 4.6× Earth circumference ocean world (~95% water) with no Gulf Stream analog. The world is archipelago-structured — no continuous landmass. The simulation runs a 10,000-year loss function. The origin constraint: a nuclear ramjet aircraft capable of sustained flight for weeks, requiring geographic distances large enough to make that vehicle meaningful.

The engine currently models each archipelago as a deterministic rational actor. Technology plugs into total factor productivity (TFP), which drives economic surplus, which governs conquest and barter capacity.

---

## Status: Confirmed Implemented

- **Technology as TFP** — non-monotonic; requires sustained caloric surplus to maintain; can regress (consistent with late Roman Empire, certain Chinese dynastic collapses)
- **Wind bands** — easterlies, westerlies, trade winds, polar vortex
- **Latitude-differentiated outputs** — insolation → crop yield, ocean climate zone, fishery type
- **Continental shelf model** — circular geometry, ~20–50m depth → high maritime protein productivity
- **Species-differentiated fisheries** — salmon (high latitude; feast-or-famine cycle; encourages collective action), sardines
- **Simulation tick** — 50-year resolution; finer ticks possible at compute cost
- **Expansion penalties** — marginal utility of territorial acquisition eventually negative
- **World generation** — RNG-seeded; loss function tunable to produce ocean-China / ocean-America topology for Cold War analog scenarios

---

## Status: Next-Round Implementation Targets

### Disease

| Mechanism | Detail |
|---|---|
| Colonial expansion limiter | Malaria and tropical disease belts constrain high-latitude civilizations from projecting power into equatorial archipelagos |
| Epidemic waves | Random, civilization-scale setback events; not limited to bubonic plague analog |
| Urban disease sink | Cities replenish population via immigration rather than reproduction; human-animal contact as vector; models early modern European urban demographic pattern |

### Environmental Shocks

| Mechanism | Detail |
|---|---|
| Crop failure | Random events — harsh winters, anomalous rainfall, crop-specific disease; pairs with existing RNG seed |
| Fishery stock-and-flow | Over-exploitation loop → stock collapse → social destabilization (Easter Island model) |

### Political Variables

| Mechanism | Detail |
|---|---|
| Religion / Culture | Implementable as discrete variable or sub-score within culture; functions as centripetal force (imperial unification) or centrifugal force (schism, fragmentation); historical analogs: Abbasid Caliphate, Reformation, Manifest Destiny |

---

## Architecture Notes

### Human-in-the-Loop Mode
Lanthier explicitly endorsed a mode where the human player substitutes for the deterministic rational actor on a turn-based tick. Rationale: introduces bounded rationality, imperfect information processing, and the laziness / inattention factor that deterministic models cannot replicate. Recommend implementing as a mode toggle on the actor layer.

### Island-Empire Dynamics
The relevant historical analog is Polynesian / Greek city-state, not Eurasian land empire. Transit cost and transit risk are first-class variables. Transit risk is already modeled as a function of technology level. This framing should be held constant across all expansion and political stability modeling.

### GUI Target
HoI (Hearts of Iron) style map interface with charts and graphs. Dense tables are identified as a primary engagement barrier. Visual at-a-glance readability is the principal UX constraint. Lanthier confirmed willingness to distribute via USB within the UBC History department.

### Distribution
Faculty of Arts is approximately 80–90% macOS. First ship target is a macOS binary. App Store distribution is not required — Homebrew or direct binary distribution is sufficient for the academic demo audience.

---

## Design Philosophy Flag

Lanthier expressed explicit concern about the **research tool framing**. His argument: even an underspecified model will be treated as prescriptive by audiences motivated to find confirmation. The simulation will be read as telling us what *should have happened* and by extension what *should happen now*. He finds this epistemologically dangerous and is personally opposed to cyclical history theories for the same reason.

**His stated preference: game framing.** Abstraction from reality, playfulness, no claim to canonical simulation of actual history.

This is a product positioning decision with downstream consequences for how the engine is documented, demoed, and described to external collaborators. Resolve before any academic or institutional demos.

---

## Interdisciplinary Consultation Leads (Suggested by Lanthier)

| Name | Specialty | Status |
|---|---|---|
| Dr. [Knutson?] | Abbasid Caliphate; religion as imperial variable | Not yet contacted |
| Dr. [Morton?] | Long-term societal development | Not yet contacted |
| Vancouver School of Economics (VSE) | Production functions, economic modeling | Not yet contacted |
| UBC Anthropology | Pre-state societies, non-Western historical templates | Not yet contacted |

---

## Notes on Data Quality

This brief was derived from a cleaned transcription of a recorded interview. The following items remain uncertain and should be verified before use in citations or formal documentation:

- **Dr. [Knutson?]** — name uncertain; could be Knudsen, Knutsen, etc.
- **Dr. [Morton?]** — could be Norton, Moreton
- **"two thousand lines of code"** — transcription guess; figure unverified
- **"imperial expiration"** — likely "imperial expansion"; kept ambiguous in source
- **"northerners"** — likely "Europeans" in context of malaria / colonial expansion passage
