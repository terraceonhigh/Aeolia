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
- [x] In-universe textbook: Intro to Reach History Ch. 7 (university register)
- [x] In-universe textbook: Our Reach, Our Trade Ch. 3 (elementary register)
- [x] V1 commodity maps kept as canon (stim_map, fiber_map, prot_map)

### Strategy Game (web app, 2026-04-09)
- [x] narrativeText.js: deterministic prose library grounded in series bible (no RNG, hash-based selection)
- [x] cardGenerator.js: 15 situation card types, each actionable
- [x] EventPopup.jsx rewrite: rich narrative prose for all event types
- [x] Dispatches feed with source-tagged intelligence (ADMIRALTY / MERCHANT GUILD / INTERNAL AFFAIRS / etc.)
- [x] Disease mechanics: malaria belts, urban disease sink, epidemic waves (Stage 5b)
- [x] 4 new situation cards: Piracy Warning, Tech Decay Alert, Navigator Guild Dispute, Malaria Medical Breakthrough
- [x] Tech decay dispatches in INTERNAL AFFAIRS feed
- [x] Observatory mode: 10,000-year history viewer with tech/pop charts, event timeline, scrubber, polity standings

### Infrastructure

- [x] GitHub repo: terraceonhigh/Aeolia (public, README, topics)
- [x] Inter-agent channel: ~/Labs/.claude-channel/ with PROTOCOL.md, channel.sh, daemon.sh, ctl.sh
- [x] Scheduled poller: channel-poll (every 5 min, reads CLI replies)
- [x] Hackintosh "Aomori" live at 192.168.1.94 (Sonoma, i5-8250U, 8GB)

---

## Pending: Immediate

### Optimizer Retuning (CRITICAL)
- [ ] DF does not fire on seed 216089 with current mechanics — culture space refactoring shifted RNG sequence, old parameter vector is stale
- [ ] Set up optimizer environment on Aomori (clone repo, install Python + numpy)
- [ ] Kick off 10K+ parameter sweep with new 26-param SimParams space
- [ ] Find parameter vectors that produce DF with continuous culture space + all new mechanics
- [ ] Validate across 5+ seeds

### Push to GitHub
- [ ] Push commit 41c518a (Malthusian clamp + trade energy + desperation) to terraceonhigh/Aeolia
- [ ] Push README.md game-framing edit and expanded CLAUDE.md
- [ ] Push any subsequent commits from optimizer work

### Channel Housekeeping
- [ ] Reorganize ~/Labs/.claude-channel/ — character sheets, soul files, and protocol docs are intermingled with message files
- [ ] Move meta files (PROTOCOL.md, DRAMATIS_PERSONAE.md, *_CHARACTER_SHEET.md, *_SOUL.md) into a subdirectory (e.g., `meta/` or `docs/`)
- [ ] Keep message files ({timestamp}_{sender}.md) flat in root
- [ ] Update channel.sh and daemon.sh if paths change

### Colonial-Era Commodity Name Cleanup
- [ ] Walk back over-eroded names: yavin→?, sini→cini, nila→keep debating, gamba→gambir, tema→?, losa→louça?, agua→aqua (already done?)
- [ ] Add kina (quinine analog, from Quechua kina-kina) to non-staple crops reference
- [ ] Resolve Fisher-Price problem for trade-layer names that lost too much consonant weight

---

## Pending: Lanthier Targets (Next Implementation Round)

### Disease Mechanics ✅ (implemented 2026-04-09 in SimEngine.js)
- [x] Malaria belts: malariaFactor[] array, abs_lat < 20°, malaria_cap_penalty=0.40 param, tech≥6 reduces to 30%
- [x] Epidemic waves: Stage 5b in advanceTick(), waveEpiLog, MERCHANT GUILD dispatches + epidemic_wave popup
- [x] Urban disease sink: density-dependent mortality above 70% capacity, urban_disease_rate=0.08 param
- [x] Disease interaction with desperation mechanic — already handled by existing desperation cascade

### Environmental Shocks
- [ ] Crop failure: random per-archipelago yield penalties, RNG-seeded, pairs with existing world generation
- [ ] Fishery stock-and-flow: depletable fish stocks, over-exploitation → collapse → social destabilization
- [ ] Fishery depletion interaction with desperation mechanic (caloric shortfall → resource pressure → allocation override)

### Religion / Culture as Political Variable
- [ ] Religion as centripetal force: imperial unification (Abbasid model, Manifest Destiny)
- [ ] Religion as centrifugal force: schism, fragmentation (Reformation model)
- [ ] Implementation options: third axis in culture space, modifier on existing two axes, or discrete variable
- [ ] Interaction with absorption blending (conquered populations resist or adopt)

---

## Pending: Architecture & UX

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
