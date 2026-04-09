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
- [x] In-universe textbook series: Intro to Reach History, university register
  - Ch. 7: The Administered Trade Network (relay era, Tahan houses, university register)
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
- [ ] Centrifugal force: schism, fragmentation (Reformation model) — deferred to next round
- [x] Interaction with culture space axes: high piety (>0.5) pulls CI toward Collective and IO mildly Inward (drift rate × 0.4, capped); closes piety↔culture feedback loop in both JS and Python

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
