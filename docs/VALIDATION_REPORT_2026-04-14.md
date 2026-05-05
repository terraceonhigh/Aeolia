# Aeolia Validation Report — April 14, 2026

Three independent playtester sessions evaluated the live GitHub Pages deployment at terraceonhigh.github.io/Aeolia/. Seed 216089. Each session played both Strategy and Observatory modes. This report consolidates their findings.

---

## Verdict

The game works. Both modes load, run, and produce coherent output. The simulation is sound, the aesthetic is distinctive, and the narrative system is the standout feature. There are bugs to fix and UX gaps to close, but the foundation is solid enough for Clio to take over as sole agent.

---

## Bugs (Priority Order)

### Critical

1. **"The Loom" crashes on game start** — TypeError in `advanceTick`. Selecting this archipelago reliably breaks the game. (P2)

2. **HOW TO PLAY modal traps the player** — CONTINUE button is unclickable. The only escape is a page reload, which destroys all game state. (P2)

3. **Observatory button during game exits without confirmation** — Clicking "Observatory" in the header during a Strategy game silently returns to main menu with no save and no warning. (P1)

### Moderate

4. **Modal action buttons unresponsive** — ADMINISTER, EXTRACT, and some situation card buttons don't respond to normal clicks. Only programmatic JS dispatch works. (P2)

5. **Double "The" in territory absorption text** — "The The Eddy council has been dissolved" — template prepends "The" to names that already include it. (P3)

6. **Negative timestamp in dispatches** — "INTERNAL AFFAIRS -17850" instead of proper BP date formatting. (P3)

7. **5th National Focus card clipped** — A 5th focus option exists but is cut off by the panel edge with no scroll indicator. (P1)

### Minor

8. **No expansion after 35 turns on EXPAND focus** — Territory remained at 1 arch despite sustained EXPAND + targeted expansion. May be intended pacing but feels broken to the player. (P1)

---

## UX Issues (Cross-Playtester Consensus)

### Information Hierarchy
- Crises look the same as routine dispatches — no visual urgency differentiation
- FOOD/STABILITY indicators exist but don't escalate visually when critical

### Feedback Loops
- National Focus change produces good multi-channel feedback (status bar + card highlight + dispatch)
- Situation card actions lack visible confirmation — clicking TARGET/DISMISS produces no animation or state change indicator
- No feedback when expansion target is actually being pursued

### Globe
- Not clickable despite help text describing click interactions
- Purely decorative in current state — all decisions happen in the right panel

### Dispatch System
- Source tag color coding (ADMIRALTY brown, MERCHANT GUILD amber, INTERNAL AFFAIRS olive) is well-designed but not self-documenting
- Dispatch filtering (ADM/MER/INT/OTH tabs) works but is easy to miss

### Speed Controls
- Relationship between pause button, 1x/5x/10x, and NEXT TURN is unclear
- Two pause indicators (button + ring) are redundant

### Mobile / Responsive
- Zero responsive breakpoints — mobile is completely broken
- Everything collapses at narrow viewports

### Accessibility
- Modal buttons missing from accessibility tree
- No keyboard navigation
- Secondary text fails contrast requirements against dark background

---

## Simulation Integrity

### What Works
- Tech curve follows plausible S-curve (0 to ~6.5 over 10,000 years with late-era acceleration)
- 31 polities survive to end state — no single runaway hegemon
- Tech leadership and territorial dominance are properly decoupled (different polities lead in each)
- Epidemic waves cluster after Serial Contact Era (historically coherent disease propagation)
- Crop failure events distributed across the timeline
- Gap Crossing Capability event properly gates the contact era
- Dispatches in Strategy mode accurately reflect player actions and sim events
- Zero JavaScript errors across both modes in all three sessions

### Naming Canon
- Commodity names mostly compliant (naphtha, chrysos, aes, pyra, paddi, sago, papa, nori)
- "iron" appears as sole English-language mineral — should probably be renamed to match the non-English convention
- Fish species names (sthaq, tunnu, bakala) not surfaced in either mode — could enrich dispatch flavor text

### Observatory Mode
- Tech chart, population chart, piety chart all render and are readable
- Event timeline scrollable with correct chronological ordering
- Control map shows polity territories with color coding
- Polity standings ranked correctly by composite score

---

## What the Playtesters Praised

- The dark parchment aesthetic with monospace type is distinctive and genre-appropriate
- Situation cards with narrative prose grounded in the series bible are the design highlight
- Source-tagged dispatches (ADMIRALTY, MERCHANT GUILD, INTERNAL AFFAIRS) create an institutional voice that feels like reading government cables
- Observatory mode's 10,000-year sweep is genuinely compelling to watch
- The fog-of-war gradient (dark umber -> sepia -> aged brown) is elegant
- Zero crashes (except The Loom), zero console errors — technically clean

---

## Recommended Fix Priority for Clio

1. The Loom crash (TypeError in advanceTick)
2. HOW TO PLAY modal escape
3. Observatory-during-game exit confirmation
4. Modal button click responsiveness
5. Double "The" template bug
6. Negative timestamp formatting
7. 5th focus card overflow
8. Situation card action feedback (animation/confirmation)

---

*Compiled by Guido (Dispatch) from three independent playtester sessions, April 14, 2026.*
