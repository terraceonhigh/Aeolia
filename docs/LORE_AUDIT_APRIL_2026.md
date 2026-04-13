# Lore Audit — April 2026

*Three specialist audits conducted by Sonnet agents after full corpus reading.*

---

## Audit 1: Relay Trade Specialist (8 findings)

| # | Issue | Severity | File(s) |
|---|-------|----------|---------|
| 1 | Emmer→fell fiber swap: constants.js assigns fell (cold-climate) to emmer; should be kapas per NON_STAPLE_CROPS_REFERENCE and narrativeText.js CROP_LORE | Critical | constants.js, substrate.js |
| 2 | Nori stimulant three-way contradiction: reference says pinang→sago, CROP_LORE says pinang→nori, engine substrate says nori has no stimulant | Critical | narrativeText.js, constants.js |
| 3 | Tech 5 "Guild Charter Era" describes administered trade (formal charters, standardized grades, letters of credit) while calling it relay maturation; Chapter 2 warns against this category error | Significant | narrativeText.js |
| 4 | "paddy terraces" anglicizes canon spelling "paddi" in crop failure dispatch | Moderate | narrativeText.js line ~435 |
| 5 | "Char from a western archipelago has arrived in your qahwa houses" — char is paddi-economy stimulant, qahwa houses are emmer-economy institutions | Significant | narrativeText.js |
| 6 | Saak displacement dispatch fires without tech gating; textbook places initial price disruption at tech ~5 (phased process), FISH_LORE says tech 7+ | Moderate | narrativeText.js |
| 7 | "Relay trade" used as generic synonym for all long-distance commerce, including post-administered era; dilutes three-layer framework | Moderate | narrativeText.js, cardGenerator.js |
| 8 | No named trading institutions (Tahan houses, feitorias) anywhere in game text; textbooks build a world of specific institutional names | Cosmetic/Structural | narrativeText.js, cardGenerator.js |

---

## Audit 2: Piety/Religion Specialist (8 findings)

| # | Issue | Severity | File(s) |
|---|-------|----------|---------|
| 1 | Religious revival card has no `why` field; every other major card carries causal citation | Significant | cardGenerator.js |
| 2 | Schism warning card recommends "PUSH TECH" as peer option to governance investment; misrepresents temporal relationship (tech damping is multi-generational, schism is immediate crisis) | Significant | cardGenerator.js |
| 3 | Schism warning body uses `.split('.')[0]` truncation, losing the strongest institutional framing ("the periphery has found in religious dissent the language for a grievance that was always fundamentally about distance and neglect") | Significant | cardGenerator.js |
| 4 | "EMBRACE FAITH" action label imports theological/personal-devotion language into institutional register; should be "REINFORCE INSTITUTIONAL RELIGION" or similar | Significant | cardGenerator.js |
| 5 | Schism popup secondary text says "high piety without institutional depth" — inverts the paradox; canon says schism fires because institutional religion is TOO central, not too shallow | Critical | EventPopup.jsx |
| 6 | Revival dispatch uses "conversion rates" without clarifying institutional vs. theological meaning; missionary fragment is explicit that conversion is administrative, not devotional | Moderate | narrativeText.js |
| 7 | Collective revival text option describes "syncretic accretions" — doctrinal assimilation not modeled in engine; reintroduces theological register | Moderate | narrativeText.js |
| 8 | Piety labels (fervent/devout/moderate/secular) read as personal faith spectrum, not institutional role; better: administered/integrated/nominal/secular | Moderate | TurnDashboard.jsx |

---

## Audit 3: Institutional Voice Specialist (13 findings)

| # | Issue | Severity | File(s) |
|---|-------|----------|---------|
| 1 | "The simulation" in player-facing text: simulation_complete popup, ReignSummary outcome, "SIMULATION CONCLUDED" header | Critical | EventPopup.jsx, ReignSummary.jsx |
| 2 | Out-of-world academic citations in `why` fields: Scott (1985), Ostrom (1990), Greif (1993), Axelrod (1997), Boyd & Richerson (1985) | Critical | cardGenerator.js |
| 3 | "CULTURAL OBSERVER" dispatch source has no institutional identity in corpus; culture drift belongs to INTERNAL AFFAIRS | Critical | narrativeText.js |
| 4 | "Welcome to the dark half of the ocean" — dungeon-master voice; fragments never welcome the reader | Significant | narrativeText.js |
| 5 | "East India Company before it was British India" — our-world analogy; game has its own equivalent | Significant | EventPopup.jsx |
| 6 | "All the history that will follow begins with a first move" — portentous announcement; Lattice voice never declares historical significance | Significant | narrativeText.js |
| 7 | ADMIRALTY dispatch makes commercial observation ("your commercial access is at risk" in naphtha scramble) — Guild territory | Moderate | narrativeText.js |
| 8 | "The ocean remembers those who persist" — grants ocean positive memory; acceptable form is "remembers no names" (removes memory) | Moderate | ReignSummary.jsx |
| 9 | Dispatch feed voices undifferentiated — ADMIRALTY, MERCHANT GUILD, INTERNAL AFFAIRS all sound like same narrator | Moderate | narrativeText.js |
| 10 | No Reach/Lattice positional distinction in player-facing prose; omniscient narrator voice for both civilizational perspectives | Moderate | all prose files |
| 11 | "Every subsequent interaction carries systemic risk" — Admiralty editorializing; institutional voice states facts and implies | Minor | narrativeText.js |
| 12 | "The ocean does not judge. It simply continues" — declaring indifference instead of showing it | Minor | EventPopup.jsx |
| 13 | `why` fields use academic shorthand ("coalition enforcement as institutional foundation") instead of in-world analytical language | Minor | cardGenerator.js |

---

## Priority Queue

**Tier 1 — Critical (break immersion or contradict canon):**
- [ ] Replace "simulation" / "SIMULATION CONCLUDED" in endings with in-world language
- [ ] Fix emmer→kapas, papa→fell fiber assignments in constants.js/substrate.js
- [ ] Fix schism secondary text: "too central" not "without depth"
- [ ] Reformulate `why` fields as in-world analytical language, not OOW citations
- [ ] Replace "CULTURAL OBSERVER" with "INTERNAL AFFAIRS"

**Tier 2 — Significant (register errors a close reader notices):**
- [ ] Fix char-in-qahwa-houses cultural collapse
- [ ] Fix Tech 5 relay/administered category error
- [ ] Add `why` field to religious revival card
- [ ] Fix "EMBRACE FAITH" → institutional language
- [ ] Fix schism warning truncation (use full institutional framing)
- [ ] Remove "Welcome to the dark half" dungeon-master voice
- [ ] Remove "East India Company" our-world analogy

**Tier 3 — Moderate (internal consistency and voice refinement):**
- [ ] Resolve nori stimulant three-way contradiction
- [ ] Fix "paddy" → "paddi" spelling
- [ ] Fix relay-as-generic-commerce post-administered
- [ ] Differentiate dispatch voices per institutional source
- [ ] Institutional piety labels

**Tier 4 — Cosmetic/Structural (would enrich but not currently broken):**
- [ ] Add named trading institutions (Tahan houses) to game prose
- [ ] Reach/Lattice voice differentiation in player-facing prose
