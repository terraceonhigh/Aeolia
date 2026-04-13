# Aeolia TODO

Status as of April 9, 2026. Everything above the line is implemented. Everything below is pending.

---

## Implemented

### Simulation Engine (sim_proxy_v2.py)

- [x] Energy-budget production function: Y = A × K^0.3 × E^0.7
- [x] Five-regime accel_rate table (foraging → agriculture → early state → industrial → nuclear)
- [x] Continuous 2D culture space (Collective↔Individual × Inward↔Outward), replacing categorical crop→culture mapping (Q1, Q2 resolved)
- [x] Culture drift per tick: prosperity→Individual, crisis→Collective, tech×trade→Outward, resource stress→Inward
- [x] Continuous allocation functions: expansion/tech/consolidation shares derived from culture-space position
- [x] Fisheries as second caloric stream: total_calories = crop_y × land_factor + fish_y × coast_factor
- [x] Six named fish species with culture-space drift vectors (sthaq, saak, tunnu, sardai, bakala, kauri)
- [x] Three tech-gated trade layers: Subsistence (tech 0+), Relay (tech 2+), Administered (tech 5+)
- [x] Gravity-model trade volumes with variable markup
- [x] Malthusian clamp on energy surplus for tech < 4 (Q5 resolved)
- [x] Three-threshold resource model: Detection → Exploitation → Strategic Valuation (Q4 resolved)
- [x] Desperation mechanic: quadratic maintenance cost (tech² × rate), tech decay on shortfall (Q3 resolved)
- [x] Resource-pressure allocation override: food/industrial/nuclear deficit hierarchy
- [x] Desperation-mode expansion bonus and resource-targeted conquest
- [x] Absorption blending for culture space (0.95 core + 0.05 target)
- [x] Wind bands, latitude-differentiated outputs, continental shelf model
- [x] RNG-seeded world generation with 30-archipelago topology
- [x] Expansion penalties (marginal utility of territorial acquisition eventually negative)
- [x] Dark Forest detection (stages 3-4), naphtha/pyra scramble mechanics
- [x] Loss function v2 (Baseline Earth comparison)
- [x] CMA-ES optimizer (optimizer_v2.py)

### Worldbuilding Canon

- [x] Fisheries reference: six species with etymology, ecology, trade properties, culture drift vectors
- [x] Non-staple crops reference: stimulants (qahwa/char/awa/pinang/aqua), fibers (kapas/seric/byssus/fell/tapa/qivu), prestige minerals (chrysos/aes), fruits, oils, dyes, fermentables, East Asian layer, vegetables
- [x] In-universe textbook series: Intro to Reach History, university register (all 12 chapters complete as of 2026-04-09)
  - Ch. 1: The Ocean World — Geography as History
  - Ch. 2: The Relay Trading Networks — From Contact to Commerce
  - Ch. 3: The Colonial Expansion — From Relay to Empire
  - Ch. 4: The Feitoria System and the Reshaping of Archipelago Production
  - Ch. 5: Resistance and Accommodation — The Intermediate Belt in the Colonial Period
  - Ch. 6: The Late Colonial Period — Integration and Dissolution
  - Ch. 7: The Strait Trade and the Collapse of the Relay Age (relay era, Tahan houses, university register)
  - Ch. 8: The Architecture of the Administered Trade Network
  - Ch. 9: The Saak Transition — Energy Economics and the Industrial Scramble
  - Ch. 10: The Years Before the Equilibrium — From First Detonation to Mutual Deterrence
  - Ch. 11: Geometry and Geology — The Strange Peace and Its Structure
  - Ch. 12: What Comes After the Strange Peace?
- [x] In-universe textbook series: Our Reach, Our Trade, elementary register
  - Ch. 3: How the Peoples of the Reach Traded With Each Other
  - Ch. 4: When Everything Sped Up (The Time of Naphtha and Fast Ships)
  - Ch. 5: The Strange Peace
  - Ch. 6: The Things We Still Trade (and Why We Still Need Each Other)
  - Ch. 7: The Children of the Relay (Where Did the Old Trading Peoples Go?)
  - Ch. 8: What Is a Nation? (And What Was It Before?)
- [x] V1 commodity maps kept as canon (stim_map, fiber_map, prot_map)

### Strategy Game (web app, 2026-04-09)
- [x] narrativeText.js: deterministic prose library grounded in series bible (no RNG, hash-based selection)
- [x] cardGenerator.js: 17 situation card types, each actionable
- [x] EventPopup.jsx rewrite: rich narrative prose for all event types
- [x] Dispatches feed with source-tagged intelligence (ADMIRALTY / MERCHANT GUILD / INTERNAL AFFAIRS / etc.)
- [x] Disease mechanics: malaria belts, urban disease sink, epidemic waves (Stage 5b)
- [x] Environmental shocks: crop failure, fishery depletion
- [x] Religion/piety: centripetal force mechanic, TurnDashboard piety display
- [x] 5 new situation cards: Piracy Warning, Tech Decay Alert, Navigator Guild Dispute, Malaria Breakthrough, Religious Revival
- [x] Tech decay + crop failure + piety dispatches in INTERNAL AFFAIRS feed
- [x] Observatory mode: 10,000-year history viewer with tech/pop/piety charts, event timeline, scrubber, polity standings, world map
- [x] Post-DF deterrence freeze + arms race (minimal Q7 implementation)
- [x] All OPEN_QUESTIONS.md issues resolved (Q1-Q7)

### Infrastructure

- [x] GitHub repo: terraceonhigh/Aeolia (public, README, topics)
- [x] Hackintosh "Aomori" live at 192.168.1.94 (Sonoma, i5-8250U, 8GB)
- [x] Inter-agent channel deprecated (2026-04-09) — removed from all docs

---

## Pending: Immediate

### Optimizer Retuning (completed 2026-04-09)
- [x] DF now fires correctly (fixed 2026-04-09): nuclear peer awareness accumulates globally (distance-independent) once both polities tech ≥ 9; `energy_to_tfp=0.51` calibrated so DF fires at year ~-200 on seed 216089 with 2 hegemons
- [x] Run full 10K-trial optuna optimization — converged at trial ~7850/10000, best loss=14.38 (trial 2213). Results in `results/`.
- [x] Validate DF timing across full geo+anchor seed suite — done; 2/9 seeds fire DF in target window with energy_to_tfp=0.51. Most seeds have only 1 hegemon (structural: DF requires 2 nuclear peers).
- **DECISION (2026-04-09):** Optimizer found different parameter regime (energy_to_tfp≈1.97) that minimizes cross-seed variance but sacrifices DF timing on demo seed. Hybrid test failed (DF fires at year -1000, 4 hegemons). **SimParams defaults kept as-is** (energy_to_tfp=0.51, hand-tuned for demo). Optimizer output archived in `best_params_v2.json` for reference. Future work: design loss function that rewards DF timing on seed 216089 specifically while not penalizing seeds that structurally can't produce 2 hegemons.

### Push to GitHub
- [x] Merge all 2026-04-09 session commits into master (done; 7 commits from claude/trusting-tu worktree)
- [ ] Push master to origin — blocked by HTTPS auth on Aomori (no stored keychain credentials, no SSH key, gh CLI not installed)
- [ ] **TERRACE:** run `git push origin master` from MacBook Neo where credentials are cached, or set up SSH key on Aomori

### Inter-Agent Channel
- [x] Channel deprecated per user instruction (2026-04-09) — removed from CLAUDE.md

### Colonial-Era Commodity Name Cleanup
- [x] Add kina (quinine analog, from Quechua kina-kina) to non-staple crops reference — done 2026-04-09; links to malaria mechanic
- [x] Document protein sources (kerbau/kri/moa) in reference — were in sim but not in worldbuilding docs
- [x] Add V1 commodity map table to reference for clarity
- [ ] Walk back over-eroded names: yavin→?, sini→cini, nila→nili (done), gamba→gambir, tema→?, losa→louça?
  - Note: these names don't appear in current codebase — may be from pre-V2 sim. Revisit when narrative text expands.
- [x] Resolve Fisher-Price problem for trade-layer names: tech 5 milestone renamed "Guild Charter Era" in narrativeText.js; internal sim labels (subsistence/relay/administered) are analytical taxonomy, not UI-visible; "relay" is already in-universe vocabulary

---

## Pending: Lanthier Targets (Next Implementation Round)

### Disease Mechanics ✅ (implemented 2026-04-09 in SimEngine.js)
- [x] Malaria belts: malariaFactor[] array, abs_lat < 20°, malaria_cap_penalty=0.40 param, tech≥6 reduces to 30%
- [x] Epidemic waves: Stage 5b in advanceTick(), waveEpiLog, MERCHANT GUILD dispatches + epidemic_wave popup
- [x] Urban disease sink: density-dependent mortality above 70% capacity, urban_disease_rate=0.08 param
- [x] Disease interaction with desperation mechanic — already handled by existing desperation cascade

### Environmental Shocks ✅ (implemented 2026-04-09 in SimEngine.js)
- [x] Crop failure: random per-arch yield penalties, cropFailureModifier[], recovers +0.25/tick, tech-gated probability
- [x] Fishery stock-and-flow: fisheryStock[], natural recovery (0.08/tick), over-exploitation depletion at density>50%
- [x] Fishery depletion interaction with desperation mechanic — caloric shortfall feeds existing resource pressure cascade
- [x] INTERNAL AFFAIRS dispatch for crop failures; Fishery Collapse situation card (Card 11b)

### Religion / Culture as Political Variable ✅ (implemented 2026-04-09 in SimEngine.js)
- [x] piety[core] scalar (0-1): crisis→up, prosperity→down, tech>7→secular, contact diversity→secular
- [x] Centripetal force: high piety boosts expansion scoring (missionary drive) + accelerates sovereignty extraction (absorption)
- [x] Piety blending on conquest: conqueror inherits 8% of absorbed polity's piety (cultural contamination)
- [x] Religious Revival situation card (Card 16): fires at piety≥0.65, collective vs. individual narrative variants
- [x] Rogue Aircraft situation card (Card 17): nuclear-era piracy equivalent (tech≥9, series bible 08_MARITIME_TRADITIONS); fires periodically when contacts>3
- [x] INTERNAL AFFAIRS piety dispatch at high/elevated levels (every 6 ticks)
- [x] Centrifugal force: schism, fragmentation (Reformation model) — implemented 2026-04-09
  - schismPressure[core] scalar; builds under high piety + low-sov peripheral holdings + pre-industrial tech
  - Schism fires at pressure > 1.0: lowest-sov third of peripheral holdings transferred to adjacent rivals or collapsed to ungoverned
  - Schism Warning situation card (Card 18): fires at pressure > 0.55 as advance notice
  - Schism event popup + INTERNAL AFFAIRS dispatch entry
  - Tech damping: mechanic dissolves at tech ≥ 7 (enlightenment/nationalism replaces religious authority)
- [x] Interaction with culture space axes: high piety (>0.5) pulls CI toward Collective and IO mildly Inward (drift rate × 0.4, capped); closes piety↔culture feedback loop in both JS and Python

---

## Pending: Architecture & UX

### Playtester Issues (2026-04-12, Wave 2 — Mace/Calder/Loma, Sonnet agents)

Three specialist reviewers dispatched sequentially: Mace (4X veteran), Calder (Georgian flag officer, 21C world model), Loma (oils/adobe painter, UI critique). Protocol: play-first, no corpus read. Findings below, ordered by severity. Earlier findings from the April 10 Haiku wave are preserved below.

#### From Mace (4X veteran)

**Critical:**
- **Silent National Focus overrides from situation card responses.** Choosing EXPAND FISHERIES on the Harvest Assessment card silently shifted national focus to EXPLOIT (40/45/15) without warning or confirmation. The card label and mechanical effect are disconnected. This is a trust failure — when the button does not do what it says, players stop engaging with cards. *Fix: add a post-choice dispatch entry explaining any focus override, or surface it as a separate prompt.*
- **Auto-focus override from revolt pressure (T3) also silent.** Game shifted EXPAND→FORTIFY in response to a revolt warning with no confirmation prompt. The dispatch "Guilds acknowledge new priority" frames an override as institutional response. *Fix: surface as an urgent situation card with recommended action, not a state change. Let the player confirm.*

**Significant:**
- **Dead turns T4–T11** — seven turns of near-silence, one flavor dispatch, no new situations. The situation card rate needs a minimum floor in early game. Dispatches must narrate passive processes (sovereignty trends, tech movement, fishery stocks) rather than going silent between threshold crossings.
- **No counterfactual visibility on founding-bargain choices.** Having chosen ADMINISTER, the player has no way to see what EXTRACT would have produced. The choice was present; the consequence differential was not. *Proposed fix: show ADMINISTER/EXTRACT stat comparison in the ArchDetailPanel after the choice is made.*
- **The Cairn unabsorbed after 14 turns of EXPAND focus** at d=0.45 (second nearest target). No intermediate feedback — no "approach made," no "navigator sighted their shelf." The expansion mechanic generates no partial signals.

**Moderate:**
- Harvest Assessment card recycled identically 8 turns after first appearance with no visible indication that prior choice produced any fishery state change.
- NAPH stat held at 1.6 for 16 turns with no dispatch explaining why (probable cause: naphtha locked behind unabsorbed territory, but the game doesn't say so).

#### From Calder (Georgian flag officer)

**Critical:**
- **ADMIRALTY goes silent for 12 turns after designating an expansion target.** "NAVY PLOTTING APPROACH" acknowledged at T2; zero follow-up for fifteen consecutive turns on that objective. A professional intelligence apparatus would produce conjectural reports from merchant rumors, navigator accounts, seasonal routing intelligence. The silence here is not professional restraint — it is absence. *Fix: generate low-confidence ADMIRALTY dispatches during sustained expansion attempts ("navigator guilds report unfavorable currents near The Cairn this season").*
- **Threshold language in INTERNAL AFFAIRS breaks the institutional register.** "Approaching revolt threshold" is simulation-engine language dressed as administrative despatch. A real colonial intelligence memo would name the specific incident and leave the threshold inference to the officer. *Fix: audit INTERNAL AFFAIRS dispatches for threshold/percentage language and replace with specific institutional observations.*

**Significant:**
- **No intelligence about expansion targets.** After 17 turns targeting The Cairn under EXPAND focus, zero information about what is there — population, political structure, rival polity activity. "Known world: 9/42" and "Terra incognita: 33" — but those 33 archipelagos contain polities that are themselves moving. ADMIRALTY should generate conjectural intelligence about rival movements even in Antiquity.
- **The situation cards occasionally cite academic sources in-line** (Ostrom 1990, Hardin 1968 visible as italic footnotes). This surfaces the designer's apparatus to the player. The `why` field convention is correct; the in-line citation in card body text is not. *Fix: move all real-world academic citations to the `why` field only; keep card body text in-universe.*

**Praised:**
- ADMIRALTY dispatch register is correct: terse, passive construction, no editorializing. "The Caldera has been absorbed into your domain" is exactly right.
- MERCHANT GUILD Y5 dispatch is the strongest single piece of writing in the feed — guild voice distinct from ADMIRALTY, commercial intelligence as byproduct of profit motive.
- Absorption mechanic correctly models institutional fragility at moment of conquest. The ADMINISTER/EXTRACT founding bargain "is a more sophisticated understanding of colonial administration than most strategy games manage."
- Game grasps that distance is cost, not just space (d=0.39 vs d=0.72 expansion targets).

#### From Loma (oils/adobe painter, UI critique)

**Critical:**
- **STABILITY in the CommandBar is a simulation variable presented as a self-evident readout**, at the same typographic weight as POP and TECH. Institutional stability is a derived interpretive score (extractiveness × 0.6 + grievance × 0.4). It should be marked as such — visually or through tooltip. PIETY gets a color-coded spectrum (fervent/devout/moderate/secular); STABILITY should too, with explicit framing as a judgment rather than a measurement.
- **The interface is organized around actions, not institutions** — the right panel presents NATIONAL FOCUS → EXPANSION TARGETS → INTELLIGENCE → CULTURAL POLICY as a decision-tree menu. The game's thesis is that decisions now determine institutional trajectories for centuries; the interface should have a persistent institutional-state view, not only a decision menu. The `why` field convention on situation cards is the honest exception — it should become the rule.
- **CULTURE label in CommandBar has no urgency coloring.** PIETY gets four color levels; CULTURE ("parochial") does not. Culture position is consequential (trade relationships, Axelrod freezing threshold) and should have the same treatment.

**Significant:**
- **The globe encodes faction culture in vertex color** (CI/IO positions mapped to RGB) but the variation is too subtle to read at globe scale under the sepia constraint, and there is no legend. The idea is right; the implementation is inaudible.
- **Edge lines between archipelagos are not differentiated** — subsistence/relay/administered trade connections render identically. The simulation tracks three tiers with meaningfully different energy contributions; the globe should distinguish them visually.
- **Delta arrows absent from ArchDetailPanel.** Sovereignty, grievance, and extraction rate are shown as current values but not trajectories. "Declining" vs. "recovering" is decision-critical information. *Fix: add small directional indicators (↑↓) with per-turn delta.*
- **The NEXT TURN button is the brightest interactive element in the interface.** Its visual weight communicates "skip past this" rather than "commit to this." In a game about 50-year consequential ticks, the punctuation mark on every turn should feel like commitment, not dismissal. *Proposed: soften the button color slightly, or reframe the label — "COMMIT TURN" or "ADVANCE 50 YEARS."*

**Praised:**
- Fog-of-war gradient (dark umber → faint sepia → aged brown) is elegant and load-bearing. The ocean at early game is genuinely dark. Correct.
- Dispatch left-border color system (ADMIRALTY red-brown, MERCHANT GUILD amber, INTERNAL AFFAIRS muted olive) is one of the interface's best decisions — source identity without palette violation.
- Crisis gradient (green → yellow → orange → red) is consistent across FOOD, STABILITY, TERR, TENSION. Correct.
- EventPopup accent-color system correctly separates event types by register (dark forest blood red, fishery collapse cold blue-grey, schism dusty violet).
- Parchment tonal field (`#b8923a`, `#c8a878`, `#907858`) and typeface commitment (JetBrains Mono throughout) is coherent and correctly executed.

---

### Playtester Issues (2026-04-10, three independent Haiku sessions)

Six issues surfaced consistently across all three testers:

1. **Action button feedback absent** — clicking TARGET / EXPAND / COUNTER on situation cards produces no visible confirmation. Players cannot tell if their input registered or changed anything.
2. **National Focus invisible as a system** — testers did not recognize Focus cards as interactive or understand they drove tech/expansion allocations. Active focus not visually distinguished from inactive.
3. **Stats scroll off-screen while reading cards** — the turn/stats header lives in the scrollable right panel. Scrolling to situation cards or dispatches hides game state.
4. **Globe is decorative, not a decision surface** — all three testers noted they made no decisions via the map. All interaction was in the right panel, disconnected from geography.
5. **No end-of-game summary** — game returns silently to main menu on defeat or completion. No closure, no stats, no story of the reign.
6. **Player agency felt absent** — "I'm not sure if I did that or if it happened to me." Root cause: UI presents outcomes, not inputs. The player is not made to feel like a rational actor issuing directives.

### UX Migration: Map-Game Convergence

**Design principle:** The player IS a rational actor. The simulation's 30 polities each have an energy budget allocation, expansion targets, a culture position, and a piety level. The player substitutes for one. The UI should feel like setting parameters on a decision engine, not reading a report about one. Reference: EU4 (province click → sidebar populate), Victoria 3 (allocation bars as primary verb), CK3 (contextual entity panel).

#### Phase 1 — Fixed layout (no mechanics changes)
- [ ] Split right panel into three non-overlapping zones:
  - **Zone A (fixed, never scrolls):** Compact stats strip — TURN/YEAR/ERA · Pop/Tech/Terr/Naph/Contacts/Culture/Piety in two rows · Turn timer bar · Speed controls · Active Focus badge showing focus name + allocation (e.g. "EXPAND · 50/30/20")
  - **Zone B (scrollable, context-driven):** Default: National Focus cards + culture sliders + SOV targets. When globe arch selected: Arch Detail Panel. ~60% of panel height.
  - **Zone C (fixed height, internally scrollable):** Situation cards + dispatches feed. Pinned to bottom.
- [ ] Zone A height ~90px. Stat values in monospace small caps. No decoration.

#### Phase 2 — National Focus visibility
- [ ] Active Focus card: inverted color scheme (light on dark vs dark on light for inactive)
- [ ] Each card shows three-segment allocation bar (expansion / tech / consolidation proportional to values)
- [ ] Live allocation summary line below cards: "CURRENT: EXPANSION 50% · TECH 30% · CONSOLIDATION 20%"
- [ ] On Focus change: emit INTERNAL AFFAIRS dispatch — "National focus shifted to [NAME]. Allocation now [X/Y/Z]."
- [ ] Active focus badge in Zone A updates immediately

#### Phase 3 — Action button feedback
- [ ] Button inversion on click (dark/light flip 300ms) → committed state (✓ prefix for 2 seconds)
- [ ] Every action emits a dispatch entry in Zone C:
  - Set expansion target → "ADMIRALTY · [Arch] designated expansion target."
  - Counter action → "INTERNAL AFFAIRS · Counter-strategy engaged against [Polity]."
  - Propose alliance → "ADMIRALTY · Diplomatic dispatch sent to [Polity]."
  - Focus change → "INTERNAL AFFAIRS · National focus shifted to [Focus]."
- [ ] After action taken: situation card enters "resolved" state (dimmed, buttons replaced with "DIRECTIVE ISSUED · TURN X"), fades after 2 turns
- [ ] Globe: expansion targets gain a crosshair annotation on their marker (antique cartography style)

#### Phase 4 — Globe as primary decision surface
- [ ] Add raycasting click handler to arch markers in GameApp.jsx Three.js scene
- [ ] Hover tooltip on arch markers: name + ownership/relationship + pop/tech if known (cartographic annotation style — no rounded corners, no shadow)
- [ ] Click foreign arch → Zone B becomes Arch Detail Panel:
  - Arch name header
  - Visibility tier label (RUMOR / CONTACTED / FRONTIER) + foggy values (~prefix for rumored data)
  - Relationship status if contacted
  - Stamp-style action row: [ SET EXPANSION TARGET ] [ SURVEY ] for frontier; [ PROPOSE ALLIANCE ] [ DECLARE RIVALRY ] [ IMPOSE EMBARGO ] for contacted; [ DISPATCH SURVEY VESSEL ] for unknown
- [ ] Click owned arch → Zone B becomes Arch Detail Panel:
  - Sovereignty level + stability dash-bar
  - Local pop, naphtha, culture
  - [ ADD TO SOV FOCUS ] / [ REMOVE FROM SOV FOCUS ]
- [ ] Click ocean (deselect) → Zone B returns to default dashboard
- [ ] Unknown/rumor arches are clickable but show "POSITION UNKNOWN" with no actions
- [ ] When situation card references a specific arch, clicking card highlights that arch on globe

#### Phase 5 — End-of-game Terminal Report
- [ ] On defeat or turn 340: show Terminal Report screen instead of silent menu redirect
- [ ] Header: "FINAL RECORD — [POLITY NAME]" / "TURNS 1–N · YEAR X" / outcome in large type (POLITY DISSOLVED / DOMINION ESTABLISHED / SIMULATION CONCLUDED)
- [ ] Four stat columns: population trajectory (start/peak/final), territory (start/peak/final), tech (start/final + peak turn), diplomatic record (alliances/rivals/embargos count)
- [ ] Rank among 30 polities at game end for each major stat
- [ ] Key events log: 5–8 entries pulled from dispatch history (first expansion, first alliance, largest territorial gain, final event)
- [ ] Decision record: breakdown of turns spent on each National Focus ("EXPAND: 87 turns · BALANCED: 120 turns")
- [ ] Two buttons: [ PLAY AGAIN ] [ MAIN MENU ]

### Human-in-the-Loop Mode
- [ ] Mode toggle on actor layer: player substitutes for deterministic rational actor on one polity
- [ ] Bounded rationality, imperfect information, turn-based tick
- [ ] Design doc needed before implementation

### GUI
- [ ] HoI-style map interface with charts/graphs (Godot frontend exists but needs sim integration)
- [ ] Dense tables identified as engagement barrier — visual at-a-glance readability is the UX constraint
- [ ] Sim-to-Godot bridge: pipe sim_proxy_v2 output to the map renderer

### Distribution (macOS App)
- [ ] **TERRACE:** Enroll in Apple Developer Program ($99/year) — required for code signing + notarization so Lanthier doesn't hit Gatekeeper wall
- [ ] Scaffold Aeolia.app from Bacalhau template (Go + Wails v2 shell, .app bundling, Info.plist, icon pipeline, three-platform CI)
  - Replace `static/` with Aeolia globe/sim frontend
  - Strip manuscript editor API routes, add sim API if needed
  - Update `wails.json`, `Info.plist.template`, bundle identifier
- [ ] Wire real code signing in CI: `codesign -s "Developer ID Application: ..."` with `--timestamp`
- [ ] Add notarization step: `xcrun notarytool submit` + `xcrun stapler staple`
- [ ] No App Store needed for academic demo audience

---

## Pending: Design Decisions

### Q6. Two-Hegemon Prescription
- [ ] Baseline Earth loss function rewards exactly two hegemons — this is prescribed, not emergent
- [ ] Ensure documentation makes this clear
- [ ] Alternative loss functions (Multipolar) should properly remove bipolarity constraint

### Q7. Post-DF Dynamics
- [ ] Decide: extend simulation past DF break, or treat post-DF as separate project?
- [ ] If extending: deterrence freeze, arms race, proxy warfare, nuclear exchange probability
- [ ] Deferred — sufficient complexity in pre-DF mechanics for now

### Game vs. Research Tool Framing
- [ ] Lanthier: game framing, not research tool. "Even underspecified models get read as prescriptive."
- [ ] Update README and demo materials to frame as game / thought experiment
- [ ] Resolve before any academic or institutional demos

---

## Consultation Leads (from Lanthier)

- [ ] Dr. [Knutson?] — Abbasid Caliphate, religion as imperial variable
- [ ] Dr. [Morton?] — long-term societal development
- [ ] Vancouver School of Economics — production functions, economic modeling
- [ ] UBC Anthropology — pre-state societies, non-Western historical templates
