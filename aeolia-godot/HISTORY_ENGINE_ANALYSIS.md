# History Engine — Continuous Function Analysis

**File:** `src/simulation/history_engine.gd`
**Reference:** `src/MONOLITH_REFERENCE.jsx` (`assignPolitics`, `computeSubstrate`)
**Lore sources:** `docs/00_SERIES_BIBLE.md` through `docs/10_VISUAL_AND_TONE_GUIDE.md`, `docs/DESIGN_SPEC.md`

---

## Overview

The history engine runs in five sequential phases:

1. **Dijkstra wavefront** — dual-source expansion (Reach from −5500 BP, Lattice from −5000 BP) across the plateau-edge graph, with era-aware edge costs
2. **Σ2ⁿ redistribution** — remaps Dijkstra arrival order onto four era time windows (serial/colonial/industrial/nuclear) so discovery accelerates across eras
3. **Status assignment** — assigns sovereignty, trade integration, and a named status to each claimed arch
4. **Population model** — five era passes updating `pop[]` and `tech[]` arrays using per-arch state from phases 1–3
5. **Final state construction** — normalizes arrays into the `states[]` output used by the renderer

This document catalogs every continuous mathematical function in phases 1–5, assesses its lore fidelity, and recommends tuning changes.

---

## Domain Map

| Function | Domain |
|---|---|
| Resource potential formula | Geography |
| Antiquity growth curve | Agriculture / Geography |
| Epidemiological shock | Geography / Agriculture |
| Trade recovery (time-on-network) | Agriculture / Economics |
| Network effect (log₂) | Economics |
| Garrison absorption / tributary tribute | Political Economy |
| Colonial extraction rate curve | Political Economy |
| Industrial era growth multipliers | Technology / Economics |
| Tech progression curves | Technology |
| Nuclear era access / tech transfer | Technology / Political Economy |
| Status assignment values | Political Economy |
| Edge cost function | Geography / Technology |
| Σ2ⁿ redistribution | Geography |
| Missing: `computeSubstrate` | All four domains |

---

## Function-by-Function Analysis

---

### 1. Resource Potential Formula

**Domain:** Geography
**Location:** `assign_politics()`, lines ~45–57

**The math:**
```gdscript
var p   = arch.peaks.size()
var sz  = arch.shelf_r / 0.12        # shelf size normalized to ~1.0
var avg_h = Σ(pk.h) / (p * ISLAND_MAX_HEIGHT)

potential[i] = (p/20.0 * 0.4 + avg_h * 0.3 + sz/2.2 * 0.3) * (0.6 + rng * 0.4)
```

Weights: peak count 40%, average peak height 30%, shelf size 30%. Randomized ±40%.

**Lore says:**
DESIGN_SPEC §0 specifies that hegemon-grade civilizations require specific geographic combinations:

- **Thalassocratic projector (Reach-type):** mid-latitude westerlies, spread island spacing, mineral endowment including fissile material, a settler archipelago along wind corridors
- **Hydraulic absorber (Lattice-type):** dense core cluster, wide tidal-flat shelf for mass agriculture, peripheral raider pressure driving a defensive garrison culture
- **Independent power (Mughal/Ottoman-type):** large arch, moderate connectivity, agricultural base sufficient for independent industrialization

The potential formula's three inputs (peak count, height, shelf size) are all architectural/size measures. They do not encode:
- **Latitude** — which determines wind belt (doldrums/trades/westerlies/subpolar) and therefore which crops grow and how hard open-ocean sailing is
- **Mineral deposits** — Pu biased toward large archs with tall peaks (evolved magma) per §10g, which is the determining factor for nuclear-era projection
- **Island spacing** — the "spread" quality that produces competitive maritime culture in the Reach vs the "dense cluster" that produces the Lattice's unification geography
- **Tidal-flat shelf width** — shelf size is partially captured by `sz`, but paddi cultivation specifically requires `shelfR >= 0.08` AND tidal range ≥ 2.0m AND latitude ≤ 28°

Two archipelagos at 5°N and 45°N with identical size and peak profiles receive the same `potential` score, despite facing completely different productive capacity: the equatorial arch can grow paddi (5.0 t/ha, collective hydraulic labor, mass bureaucracy) while the mid-latitude arch grows emmer (2.5 t/ha, individual competitive labor, civic political culture).

**Assessment:** Adequate as a relative size proxy but blind to the substrate differentiation the lore demands. Every function downstream that uses `potential` inherits this flattening.

**Recommendations:**
- Add a latitude modifier using the arch's `cy` (elevation on unit sphere approximates sin(lat)):
  ```gdscript
  var abs_lat = asin(clamp(arch.cy, -1.0, 1.0)) * 180.0 / PI
  var lat_factor = 1.0
  if abs_lat <= 28.0 and arch.shelf_r >= 0.08:
      lat_factor = 1.25   # paddi zone: wide tidal shelf + warm = high yield
  elif abs_lat >= 25.0 and abs_lat <= 55.0:
      lat_factor = 1.10   # emmer zone: competitive individual cultivation
  elif abs_lat >= 35.0:
      lat_factor = 0.85   # subpolar/papa zone: lower yield ceiling
  potential[i] *= lat_factor
  ```
- Until `computeSubstrate` is ported, this single modifier captures the most consequential lore-driven differentiation.

---

### 2. Antiquity Growth Curve

**Domain:** Agriculture / Geography
**Location:** ERA 1 block, `assign_politics()`

**The math:**
```gdscript
# Represents 15,000 years of independent development (−20,000 to −5,000 BP)
pop[i] *= pow(1.0 + 0.002 * potential[i], 30.0)
tech[i] = potential[i] * (2.5 + rng.next_float() * 1.5)

tech[REACH_ARCH] = maxf(tech[REACH_ARCH], 3.5)
tech[LATTICE_ARCH] = maxf(tech[LATTICE_ARCH], 3.8)
pop[LATTICE_ARCH] *= 2.5
```

Growth factors for the `pow()` formula:
- Average arch (potential = 0.5): `(1.001)^30 ≈ 1.030` — **3% total growth over 15,000 years**
- High-potential arch (potential = 1.0): `(1.002)^30 ≈ 1.062` — **6% total growth**
- The `2.5×` Lattice multiplier does almost all the differentiation work

**Lore says:**
DESIGN_SPEC §1: Antiquity (−20,000 to −5,000 BP) is "Independent growth + substrate seeding." No inter-arch interaction. The era log label reads: "Independent development · Lattice develops tidal-flat agriculture."

DESIGN_SPEC §10a on paddi: "The crop that creates the bureaucracy. Max ~6.5 t/ha in the Lattice core. The dike system requires central coordination; neglect = famine." A paddi arch over 15,000 years of hydraulic agriculture should produce a population base orders of magnitude larger than a sago arch. Paddi yields 5× more calories per hectare than emmer, and emmer yields more than sago.

The Lattice's 2.5× multiplier is the right instinct but the wrong mechanism. It is a hardcoded constant applied to one arch; the proper signal is that wide-shelf equatorial archs with tidal ranges ≥ 2.0m should grow at higher rates everywhere, not just at the Lattice core.

**Assessment:** The `pow()` formula produces negligible differentiation — a high-potential arch grows 3 percentage points more than a low-potential arch over 15,000 years. The 2.5× Lattice constant is doing all the narrative work but doesn't generalize to other paddi-capable archs. Antiquity should be the era where agricultural geography produces the largest population divergence; instead it produces near-uniform populations corrected by a single hard multiplier.

**Recommendations:**
- Increase base growth exponent to produce meaningful differentiation:
  ```gdscript
  # Before: pow(1.0 + 0.002 * potential[i], 30.0)
  # After:
  var growth_rate = 0.003 + potential[i] * 0.006  # range 0.003–0.009
  pop[i] *= pow(1.0 + growth_rate, 30.0)
  # This gives: low potential 1.094×, high potential 1.306× — real spread
  ```
- Replace the hardcoded `2.5×` Lattice multiplier with a paddi-proxy calculation using shelf and latitude until full substrate is ported:
  ```gdscript
  var abs_lat = asin(clamp(archs[i].cy, -1.0, 1.0)) * 180.0 / PI
  if abs_lat <= 28.0 and archs[i].shelf_r >= 0.08:
      pop[i] *= 1.8 + archs[i].shelf_r / 0.12 * 0.6  # ~1.8–2.8× for paddi archs
  ```
  This makes the Lattice core's 2.5× emerge from its actual tidal-flat geography rather than a hardcoded special case.
- Tech initialization (`potential * 2.5–4.0`) is fine. The floor values (3.5 / 3.8) are appropriate.

---

### 3. Epidemiological Shock Function

**Domain:** Agriculture / Geography
**Location:** ERA 2 (serial contact) and ERA 3 (colonial) blocks

**The math:**
```gdscript
# Serial Contact era (−5,000 to −2,000 BP):
var shock = 0.25 + rng.next_float() * 0.35   # 25–60% survive (40–75% die)
pop[i] *= shock

# Colonial era (−2,000 to −500 BP):
var shock = 0.30 + rng.next_float() * 0.35   # 30–65% survive (35–70% die)
pop[i] *= shock
```

Applied uniformly to every contacted arch regardless of:
- What crops the contactor grows (Reach = emmer-origin, Lattice = paddi-origin)
- What crops the contacted arch grows
- How ecologically distant the two pathogen pools are

**Lore says:**
DESIGN_SPEC §10a specifies an explicit crop-distance disease modifier:
```
diseaseShock = baseSeverity × cropDistance(contactor, contacted)

cropDistance =
    0.2  if same crop type         (similar pathogen pools — 20% of base severity)
    0.5  if adjacent climate zones (50%)
    0.8  if distant climate zones  (80%)
    1.0  if maximally different    (paddi meets papa = catastrophe — 100%)
```

Series Bible §Core Thesis: "The gap crossing carries trade goods and epidemiological catastrophe." The magnitude of that catastrophe is explicitly an ecological distance function.

The Reach colonizes from an emmer-origin (temperate, mid-latitude) base. It contacts paddi archs (equatorial, hydraulic), taro archs (tropical, kinship-chieftain), sago archs (equatorial-humid, communal), and papa archs (subpolar). The emmer-meets-papa contact (maximum ecological distance) should produce near-total mortality. The emmer-meets-emmer contact (same crop zone) should produce mild shock. The current implementation makes both identical.

Historical calibration: Amerindian contact with European diseases (maximum ecological distance) produced 75–90%+ mortality. Same-zone Mediterranean contacts in classical antiquity produced 20–40% in severe plague events, much less in ordinary epidemic spread.

**Assessment:** This is the highest-priority misalignment in the shock functions. It is both lore-specified precisely and computationally easy to implement even without the full substrate model, because the contactor identities (Reach = emmer, Lattice = paddi) are fixed and the contacted arch's latitude can proxy for crop zone.

**Recommendations:**
- Implement crop-distance approximation using latitude until substrate is ported:
  ```gdscript
  func _shock_multiplier(contactor_power: String, arch_lat_abs: float, shelf_r: float) -> float:
      # Approximate contacted arch's crop zone from latitude + shelf
      var contacted_zone: String
      if arch_lat_abs <= 28.0 and shelf_r >= 0.08:
          contacted_zone = "paddi"
      elif arch_lat_abs <= 20.0:
          contacted_zone = "taro"
      elif arch_lat_abs <= 15.0 and shelf_r >= 0.04:
          contacted_zone = "sago"
      elif arch_lat_abs >= 35.0:
          contacted_zone = "papa"
      else:
          contacted_zone = "emmer"

      # Contactor crop
      var contactor_zone = "emmer" if contactor_power == "reach" else "paddi"

      # Crop distance lookup
      if contactor_zone == contacted_zone:
          return 0.2
      var tropical = ["paddi", "taro", "sago"]
      var temperate = ["emmer", "papa"]
      if (contactor_zone in tropical and contacted_zone in tropical) or \
         (contactor_zone in temperate and contacted_zone in temperate):
          return 0.5
      if (contactor_zone == "papa" and contacted_zone == "paddi") or \
         (contactor_zone == "paddi" and contacted_zone == "papa"):
          return 1.0
      return 0.8

  # In ERA 2:
  var base_shock = 0.25 + rng.next_float() * 0.35
  var abs_lat = asin(clamp(archs[i].cy, -1.0, 1.0)) * 180.0 / PI
  var dist = _shock_multiplier(claimed[i], abs_lat, archs[i].shelf_r)
  var shock = lerpf(1.0, base_shock, dist)   # dist=0.2 → mild, dist=1.0 → full
  pop[i] *= shock
  ```
- Calibrate base severity: serial-contact era base should be `0.20 + rng * 0.25` (20–45% mortality before crop-distance scaling), so the scaled range at maximum distance becomes 20–45% which is realistic for maximum-severity pandemics, not the current 40–75% which implies every contact is a catastrophe.

---

### 4. Trade Recovery Function

**Domain:** Agriculture / Economics
**Location:** ERA 2 (serial contact) block

**The math:**
```gdscript
var trade_years = maxi(0, -2000 - yr)        # years on network before era ends
pop[i] *= 1.0 + float(trade_years) * 0.0004
tech[i] += 0.5 + rng.next_float() * 0.5
```

Recovery per year of trade contact: 0.04% population growth.
Contacted at −5000 BP (3000 years): `×2.2` population recovery
Contacted at −3000 BP (1000 years): `×1.4` recovery
Contacted at −2001 BP (1 year): essentially no recovery

**Lore says:**
DESIGN_SPEC §10b on nori: "The universal trade good of Aeolia — lightweight, nutritious, imperishable, demanded everywhere. Nori archs have permanent trade advantage — the spice islands of Aeolia."

DESIGN_SPEC §10b on stimulants: "The single most important driver of long-distance trade. Stimulant demand funded more naval expeditions than gold."

The trade recovery rate should vary enormously based on what the arch produces. A nori arch contacted early should recover explosively — every civilization in the network demands nori, regardless of latitude or crop zone. A sago arch produces *pinang* (betel) which has high local demand but limited long-range appeal. An arch that produces *seric* (paddi-silk) has enormous prestige value and trades across maximum distance.

**Assessment:** The linear time-on-network formula is structurally sound — longer contact means more recovery, and the rate `0.0004/yr` produces plausible magnitudes. The flaw is that it ignores total trade value, making a nori export node identical to a sago-leisure island. This is one of the easiest high-payoff improvements once substrate is ported.

The tech increment (`+0.5–1.0`) is appropriate — contact brings knowledge regardless of trade goods.

**Recommendations:**
- Add a `totalTradeValue` multiplier from substrate output:
  ```gdscript
  var trade_value_factor = substrate[i].tradeGoods.totalTradeValue  # 0.0–1.0
  pop[i] *= 1.0 + float(trade_years) * 0.0004 * (0.4 + trade_value_factor * 1.2)
  ```
  This gives nori archs (`totalTradeValue ≈ 0.9`) roughly 2.5× the recovery rate of low-trade-value archs (`totalTradeValue ≈ 0.1`).
- Until substrate is ported: use a latitude-proxy for `trade_value_factor` where upwelling-zone archs (nori-likely) get a 1.4× bonus.

---

### 5. Network Effect (log₂ Formula)

**Domain:** Economics
**Location:** ERA 2 (serial contact) block — core civilizations

**The math:**
```gdscript
pop[REACH_ARCH]   *= 1.5 * (1.0 + _log2(1.0 + float(reach_network)) * 0.20)
tech[REACH_ARCH]   = minf(6.0, tech[REACH_ARCH] + 1.2)

pop[LATTICE_ARCH] *= 1.6 * (1.0 + _log2(1.0 + float(lattice_network)) * 0.30)
tech[LATTICE_ARCH] = minf(6.0, tech[LATTICE_ARCH] + 1.0)
```

At 10 contacts: Reach network term = `log₂(11) × 0.20 ≈ 0.69`; Lattice = `log₂(11) × 0.30 ≈ 1.03`
At 20 contacts: Reach = `0.89`; Lattice = `1.34`

The Lattice has a higher base multiplier (1.6 vs 1.5) AND a higher log₂ coefficient (0.30 vs 0.20). At every network size, the Lattice gains more from its contacts than the Reach.

**Lore says:**
DESIGN_SPEC §5 (Budget Allocation, Solow-Romer parameters):

| Parameter | Reach | Lattice | Meaning |
|---|---|---|---|
| A₀ | 1.2 | 0.8 | Base total factor productivity |
| α | 0.4 | 0.3 | Knowledge elasticity |
| δ | 0.08 | 0.04 | Knowledge spillover rate |

The Reach has **50% higher base productivity** and **2× the knowledge spillover rate**. Every new contact improves Reach cartographic technique faster than Lattice bureaucratic records. "Columbus was nearly impossible; the tenth Caribbean voyage was routine. Not the ocean changing — A increasing."

DESIGN_SPEC §5 on the Lattice's feedback loop: "Agricultural surplus is large but constant. Doesn't scale with expansion. Budget is stable, not growing. This is why Zheng He sailed once and stopped."

The Lattice's advantage is its large paddi-based population, not its per-contact knowledge yield. The current code gives the Lattice both advantages: a larger base multiplier (1.6 vs 1.5) AND more efficient network scaling (0.30 vs 0.20).

The tech gains are correctly differentiated: Reach +1.2, Lattice +1.0. The Reach learns more from contacts. This matches the A₀ and δ differential. The population formula contradicts it.

**Assessment:** The network effect coefficients are inverted. This is a medium-priority fix that is easy to implement and has clear lore justification.

**Recommendations:**
- Swap and re-tune to reflect the A₀ differential:
  ```gdscript
  # Reach: smaller base, higher network coefficient (knowledge-spillover dominant)
  pop[REACH_ARCH] *= 1.3 * (1.0 + _log2(1.0 + float(reach_network)) * 0.30)

  # Lattice: larger base (paddi surplus), lower network coefficient (stable, not scaling)
  pop[LATTICE_ARCH] *= 1.9 * (1.0 + _log2(1.0 + float(lattice_network)) * 0.12)
  ```
  This preserves the Lattice's large absolute population (large base ×1.9 vs ×1.3) while correctly modeling the Reach as the civilization that compounds knowledge faster with each new contact.

---

### 6. Garrison Absorption & Tributary Tribute

**Domain:** Political Economy
**Location:** ERA 3 (colonial) block

**The math:**
```gdscript
# Garrison (Lattice, hops ≤ 3):
var absorbed = pop[i] * (0.15 + rng.next_float() * 0.10)   # 15–25%
pop[LATTICE_ARCH] += absorbed
# NOTE: pop[i] is NOT decremented

# Tributary (Lattice, hops 4–5):
var tribute = pop[i] * (0.05 + rng.next_float() * 0.05)    # 5–10%
pop[LATTICE_ARCH] += tribute
# NOTE: pop[i] is NOT decremented
```

**Lore says:**
The Lattice model is "bureaucratic absorption" — people are pulled into the administrative and agricultural labor system of the hydraulic core. DESIGN_SPEC §10d colonial drift trajectory: "Lattice garrisons papa arch: Household (0.20, 0.10) → Asiatic (0.85, 0.25). Path: kin-groups taxed → corvée for dike extension → examination system arrives → full bureaucratic absorption."

This is population movement — people relocate to the administrative center, not a magical duplication. The absorbed population should reduce the source arch's headcount.

The JSX reference (`assignPolitics`) has the same omission, so this is not a porting error — it's a bug in the original that was faithfully reproduced.

**Assessment:** This is the only outright bug in the history engine. The absorbed population is both retained by the source arch AND added to the Lattice core, double-counting those people. Over many garrisoned archs, this inflates the Lattice's population by 15–25% per garrison arch without any corresponding reduction anywhere.

The tribute rate (5–10%) is historically reasonable for hydraulic empires. The absorption rate (15–25%) is plausible for the Lattice's deep integration model, though the DESIGN_SPEC §10d trajectory suggests absorption should be heavier on garrison archs (dike extension requires labor transplanted to the core).

**Recommendations:**
- Fix the bug: `pop[i] -= absorbed` after the Lattice receives the people
- Tribute does not need subtraction (tribute is annual tax flow, not demographic relocation) but consider reducing the arch's productive capacity: `pop[i] *= 1.0 - tribute * 0.5` (tribute extracts some population equivalent in labor)

---

### 7. Colonial Extraction Rate Curve

**Domain:** Political Economy
**Location:** ERA 3 (colonial) block — Reach colonies

**The math:**
```gdscript
var col_years = maxi(0, -500 - (colony_yr[i] if colony_yr[i] else yr))
var extraction_rate = 0.15 + float(col_years) * 0.0001   # linear growth
var extracted = pop[i] * extraction_rate
var enslaved = pop[i] * (0.05 + rng.next_float() * 0.10)
pop[i] -= extracted
pop[i] -= enslaved
pop[i] += 8 + rng.next_float() * 15                      # settler immigration
pop[REACH_ARCH] += total_extracted * 0.6 + total_enslaved # 60% transit efficiency
```

Rate growth: starts at 15%, increases 0.01% per year of colonization.
At 1,500 years (maximum): rate = `0.15 + 0.15 = 0.30` — 30% extraction + 5–15% enslavement = **35–45% total drain per colonial period**
Settler immigration: +8–23 people (absolute, not percentage) — negligible relative to colonial-era populations.

**Lore says:**
DESIGN_SPEC §8 (extraction formula):
```
extraction = tradeIntegration × (1 − sovereignty) × hegemon.extractionPolicy
```
For a colony: `0.85 × (1 − 0.15) × policy = 0.72 × policy`
Extraction ceilings from §10d:
- Asiatic mode: 0.40
- Plantation colony: 0.50 "but with social collapse risk"

DESIGN_SPEC §10d on colonial drift trajectory: "Reach colonizes taro arch: Tributary → Plantation Colony. Passes through Tributary Empire and State Capital on the way. Duration: ~30 ticks (1,500 years)."

The `extractionCeiling` and social-collapse mechanic are absent. A long-colonized arch should eventually hit a breaking point where extraction-induced depopulation triggers collapse (monoculture failure, labor shortage, famine) rather than continuing to drain linearly.

The enslaved population being added directly to the Reach core (`pop[REACH_ARCH] += total_enslaved`) is an error of category. Enslaved people in the metropole boost the labor supply and therefore economic productivity and tech growth — not raw population headcount. The Series Bible is explicit that the Reach's colonial model is extractive, not absorptive (absorption is the Lattice's mechanism).

**Assessment:** The linear extraction rate is structurally reasonable. The ceiling and collapse mechanics are missing. The enslaved-population accounting is miscategorized.

**Recommendations:**
- Cap extraction rate at 0.30 with a stochastic social-collapse trigger above 0.22:
  ```gdscript
  var extraction_rate = minf(0.30, 0.15 + float(col_years) * 0.0001)
  if extraction_rate > 0.22:
      var collapse_prob = (extraction_rate - 0.22) / 0.08 * 0.35
      if rng.next_float() < collapse_prob:
          pop[i] *= 0.55 + rng.next_float() * 0.20   # collapse event
  ```
- Move enslaved persons from raw population addition to a productive capacity bonus:
  ```gdscript
  # Instead of: pop[REACH_ARCH] += total_enslaved
  tech[REACH_ARCH] = minf(8.0, tech[REACH_ARCH] + total_enslaved * 0.0001)
  pop[REACH_ARCH] += total_extracted * 0.6   # only extracted goods, not persons
  ```

---

### 8. Industrial Era Growth Multipliers

**Domain:** Technology / Economics
**Location:** ERA 4 (industrial) block

**The math:**
```gdscript
# Reach core:
pop[i] *= (1.0 + tech[i] * 0.08 + potential[i] * 0.15)
        * (1.0 + _log2(1.0 + float(total_network)) * 0.12)
tech[i] = minf(8.0, tech[i] + potential[i] * 0.8)

# Lattice core:
pop[i] *= (1.0 + tech[i] * 0.10 + potential[i] * 0.18)
        * (1.0 + float(lattice_integrated) * 0.08)
tech[i] = minf(8.0, tech[i] + potential[i] * 0.7)

# Free client/contact (sovereign < 0):
pop[i] *= 1.0 + tech[i] * 0.08 + potential[i] * 0.12
tech[i] = minf(7.5, tech[i] + potential[i] * 0.7)

# Colony (sovereign >= 0):
pop[i] *= 1.0 + tech[i] * 0.03 + potential[i] * 0.05
tech[i] = minf(6.0, tech[i] + potential[i] * 0.3)
```

**Lore says:**
DESIGN_SPEC §5 (Solow-Romer parameters, Reach vs Lattice):

| Parameter | Reach | Lattice | Meaning |
|---|---|---|---|
| A₀ | 1.2 | 0.8 | Base total factor productivity |
| α (knowledge elasticity) | 0.4 | 0.3 | Each new contact improves technique more for Reach |
| β (resource elasticity) | 0.5 | 0.6 | Lattice's output more dependent on resource base |
| δ (knowledge spillover) | 0.08 | 0.04 | Reach charts compound; Lattice archives don't |

The Reach should be more technologically productive per contact and per unit of tech. The Lattice's industrial strength comes from its large agricultural surplus and large integrated population base, not from superior knowledge compounding.

The era label: "Steam · Colonies stagnate · Trade partners industrialize." The colony differential (0.03 tech vs 0.08 free client) correctly captures stagnation. The core multipliers do not correctly capture the Reach/Lattice distinction.

**Current misalignment:**
- Lattice core uses `tech * 0.10` vs Reach's `tech * 0.08` — Lattice gets more tech leverage
- Lattice core uses `potential * 0.18` vs Reach's `potential * 0.15` — Lattice gets more resource leverage
- Lattice uses linear `lattice_integrated * 0.08` network term; with 15 integrated archs this = 1.20, which can exceed the Reach's log₂ term at moderate network sizes
- The Reach should have *both* higher tech leverage (δ=0.08 vs 0.04) *and* competitive resource leverage (A₀=1.2 vs 0.8); currently the Lattice has both

**Assessment:** Both core multiplier pairs are inverted relative to the design spec. This produces a Lattice that is both larger (correct) and faster-growing industrially (incorrect). The Reach should be the faster industrializer — "Colonies stagnate · Trade partners industrialize" describes Reach extraction fueling Reach growth, not Lattice out-teching the Reach.

**Recommendations:**
```gdscript
# Reach core: higher tech leverage (A₀=1.2, δ=0.08), moderate resource leverage
pop[i] *= (1.0 + tech[i] * 0.12 + potential[i] * 0.14)
        * (1.0 + _log2(1.0 + float(total_network)) * 0.14)
tech[i] = minf(8.0, tech[i] + potential[i] * 0.9)   # faster tech growth

# Lattice core: lower tech leverage (A₀=0.8, δ=0.04), higher resource leverage (β=0.6)
pop[i] *= (1.0 + tech[i] * 0.06 + potential[i] * 0.22)
        * (1.0 + _log2(1.0 + float(lattice_integrated)) * 0.10)
tech[i] = minf(8.0, tech[i] + potential[i] * 0.6)   # slower tech growth, bigger base
```

The Lattice's large population comes from `potential * 0.22` (agricultural surplus = high resource elasticity). The Reach's faster growth comes from `tech * 0.12` and the higher log₂ network coefficient. Both cores end up large; the Reach ends up technologically ahead going into the nuclear era, which matches the lore.

---

### 9. Tech Progression Curves

**Domain:** Technology
**Location:** All five era blocks

**The full tech trajectory (for a typical arch):**

| Phase | Formula | Result |
|---|---|---|
| Antiquity init | `potential * (2.5 + 1.5*rng)` | ~2.0–4.0 |
| Reach/Lattice floor | `maxf(tech, 3.5/3.8)` | 3.5/3.8 minimum |
| Serial contact | `+= 0.5–1.0` per contact, core `+1.2/1.0` | Core ~5.0–6.0 |
| Colonial contacts | `+= 0.3` flat | ~4.5–6.0 |
| Industrial | `+= potential * 0.3–0.8` by status | Core hits 7.0–8.0 |
| Industrial floor | `maxf(tech, 7.0/6.5)` for cores | Hard floor |
| Nuclear | Reach = 10.0 (hard set), Lattice = 9.5 | Fixed |

**Lore says:**
DESIGN_SPEC §0: "Seeds where a third power reaches comparable tech independently, or where the 'hegemons' are less dominant and the world at Story Present is genuinely multipolar." A tech-7 regional power with a navy and a philosophical tradition is a civilization, not a subject. The simulation should produce 3–5 independent powers, not just two nuclear hegemons and everyone else at tech 4–6.

DESIGN_SPEC §7 (independent power emergence threshold): `techLevel > 6.0 && geo.size > 0.6 && sovereignty > 0.7 → arch becomes INDEPENDENT POWER, runs own exploration budget`

The hard industrial floor at tech 7.0 for Reach and 6.5 for Lattice ensures the hegemons always hit industrial grade. This is correct. But it forecloses independent powers matching them: no free-client arch can reach 7.0 (capped at 7.5 but lacking the floor to guarantee it), and the formula makes high-potential free clients grow their tech at `potential * 0.7` — a large but not guaranteed path to 6.5+.

The nuclear-era hard-set to 10.0 and 9.5 removes all seed variance from the core civilizations. Every world has identical end-state tech levels for the hegemons.

**Assessment:** The tech scale is a reasonable ordinal ranking device but the hard floors/ceilings prevent:
1. Seed variance in hegemon tech levels (a geographically marginal Reach-candidate should sometimes fall short)
2. Third-power emergence (a large high-potential independent arch should occasionally reach nuclear capability)

**Recommendations:**
- Replace the industrial-era hard floor with a soft guarantee based on potential:
  ```gdscript
  tech[REACH_ARCH]   = maxf(tech[REACH_ARCH],   4.5 + potential[REACH_ARCH] * 2.5)
  tech[LATTICE_ARCH] = maxf(tech[LATTICE_ARCH],  4.0 + potential[LATTICE_ARCH] * 2.5)
  ```
  A high-potential Reach arch still hits 7.0; a marginal one hits 5.5–6.0, making the nuclear era more uncertain.
- Keep the nuclear hard-set for now (it simplifies the end-state), but add a `±0.5` variance:
  ```gdscript
  tech[REACH_ARCH]   = 10.0 - rng.next_float() * 0.5   # 9.5–10.0
  tech[LATTICE_ARCH] = 9.5  - rng.next_float() * 0.5   # 9.0–9.5
  ```

---

### 10. Nuclear Era Access / Tech Transfer

**Domain:** Technology / Political Economy
**Location:** ERA 5 (nuclear) block

**The math:**
```gdscript
var access = 0.0
if sovereign[i] == REACH_ARCH:
    access = 0.7   # former colonies: high trade integration, max diffusion
elif sovereign[i] == LATTICE_ARCH:
    access = 0.5   # former garrisons: absorbed but not commodified
else:
    access = 0.3   # independent contacts: selective adoption

if sovereign[i] >= 0 and rng.next_float() < 0.4:
    pop[i] *= 1.3 + rng.next_float() * 0.3   # Green Revolution (40% chance)

pop[i]   *= 1.0 + access * 0.2              # 6/10/14% population growth
tech[i]   = minf(10.0, tech[i] + access)    # +0.3/0.5/0.7 tech gain
```

**Lore says:**
Era label: "200 BP – contact · Reactor seaplanes · Post-colonial recovery."

THE_REACH doc (03): The settler colony outgrew the metropole. The indigenous population was devastated, survivors pushed to marginal islands. The Reach's legal system has never fully resolved their status. Post-colonial recovery is a central narrative theme.

The access differentials are lore-consistent:
- Former Reach colonies (access=0.7): high tradeIntegration (0.85) means knowledge diffuses naturally through commercial channels. The Reach's A₀=1.2 advantage in tech spread applies here.
- Former Lattice garrisons (access=0.5): bureaucratically absorbed but labor not commodified; tech transfer is institutional, not commercial
- Independent contacts (access=0.3): selective adoption, no structural dependency

The Green Revolution (random 40% chance × 1.3–1.6 pop multiplier) is the "population explosion enabled by industrial-era agricultural improvements reaching the periphery." The 40% probability is arbitrary.

**Assessment:** The access levels are well-calibrated to lore. The structural fix needed is that post-colonial recovery should not be random — it should correlate with prior extraction severity (archs that were extracted most heavily have the most to recover) and institutional resilience (archs with high prior sovereignty or civic political culture recover faster).

**Recommendations:** Low priority as a standalone fix, but worth noting the connection once extraction history is tracked:
```gdscript
# Future: tie recovery probability to prior extraction
var recovery_prob = 0.15 + extraction_history[i] * 0.5   # heavier extraction → more recovery headroom
if sovereign[i] >= 0 and rng.next_float() < recovery_prob:
    pop[i] *= 1.2 + rng.next_float() * 0.4
```

---

### 11. Status Assignment Values (Sovereignty / Trade Integration)

**Domain:** Political Economy
**Location:** Phase 3 (status assignment)

**The math:**
```gdscript
# Reach colonies (hops ≤ 3, pre-nuclear):
{ sovereignty: 0.15, tradeIntegration: 0.85 }

# Reach clients (hops ≤ 5, pre-nuclear):
{ sovereignty: 0.55, tradeIntegration: 0.60 }

# Reach contacted (all others):
{ sovereignty: 0.90, tradeIntegration: 0.20 }

# Lattice garrison (hops ≤ 3):
{ sovereignty: 0.30, tradeIntegration: 0.50 }

# Lattice tributary (hops ≤ 5):
{ sovereignty: 0.60, tradeIntegration: 0.40 }

# Lattice pulse (all others):
{ sovereignty: 0.90, tradeIntegration: 0.15 }
```

Assigned once at contact, never updated.

**Lore says:**
DESIGN_SPEC §8 (Political-Economy Space):

> "Named statuses are regions, not categories. The sovereignty-trade space is continuous. An arch drifts through it each tick. Labels are derived from position, never assigned directly."

The design spec provides continuous drift formulas for both axes:

```
sovereignty =
    + cohesion × 0.25
    + (1 − techDelta) × 0.25
    + geo.size × 0.20
    + ambition × 0.15
    + hopCount × 0.05
    − hegemon.controlCapacity × 0.10

tradeIntegration =
    + openness × 0.25
    + geo.betweenness × 0.20
    + geo.resourceValue × 0.20
    + era.techFactor × 0.15
    + (1 − sovereignty) × 0.10
    + log2(networkSize) × 0.10
```

And per-tick drift rules:
```
if colonized: sovereignty decreases, tradeIntegration increases
if extraction > 0.3: ambition increases → sovereignty pushes up
if trade integration rising: openness increases
if tech delta narrowing: ambition + cohesion both rise
if posture = HIDE for > 5 ticks: tradeIntegration drops, cohesion rises (Tokugawa closure)
```

The Tokugawa mechanic (ALIGN → FORTIFY → HIDE → sovereignty snap to ~0.95, tradeIntegration → ~0.05) requires per-tick updates to be implementable at all. It cannot exist with static assignments.

DESIGN_SPEC §7 on dynamic re-evaluation: "Status is NOT permanent. Each tick, motivation and controlCost are recomputed. Status transitions when ratio crosses thresholds." Explicit transitions include: Colony → Post-colony (nuclear era + cost > revenue), Colony → Client (hegemon weakens), Client → Colony (resources discovered), Bypassed → Garrison (denial value spikes), Any → Closed (Tokugawa).

**Assessment:** This is the largest structural gap between the current implementation and the design spec's vision. The entire continuous political-economy space — the feature that produces the Tokugawa mechanic, post-colonial recovery trajectories, contested-arch dynamics, and independent power emergence — is collapsed to a six-row lookup table with no subsequent updates.

Every colony ends the simulation at exactly (0.15, 0.85) regardless of:
- Whether the colonizer weakened (which should push sovereignty up)
- Whether the colonial era was long or short
- Whether the arch had high cohesion and resisted extraction
- Whether the nuclear era brought post-colonial recovery
- Whether a second hegemon's wavefront arrived, creating a contested arch

The six initial values are lore-reasonable as starting points. They are not reasonable as permanent assignments.

**Recommendations:**

This requires a larger architectural change (per-tick update loop), but a minimum-viable improvement for the current batch-history model adds era-transition updates:

```gdscript
# After ERA 4 (industrial) and before ERA 5 (nuclear):
for i in range(N):
    if not claimed[i] or i == REACH_ARCH or i == LATTICE_ARCH:
        continue
    var sd = status_data[i]

    # Industrial-era resistance: extraction builds cohesion and ambition
    if sd["status"] == "colony":
        var extraction_strain = extraction_rate_for[i]   # tracked from ERA 3
        sd["sovereignty"] = minf(0.45, sd["sovereignty"] + extraction_strain * 0.3)

    # Long-contact clients develop autonomy
    elif sd["status"] == "client":
        var contact_age = maxi(0, -500 - arrival_yr[i])  # years as client
        sd["sovereignty"] = minf(0.80, sd["sovereignty"] + contact_age * 0.00005)

# After ERA 5 (nuclear):
for i in range(N):
    if not claimed[i] or i == REACH_ARCH or i == LATTICE_ARCH:
        continue
    # Post-colonial recovery: sovereignty rises, tradeIntegration adjusts
    if status_data[i]["status"] == "colony":
        status_data[i]["sovereignty"] = minf(0.75, status_data[i]["sovereignty"] + 0.35)
        status_data[i]["tradeIntegration"] *= 0.85   # retains trade links, less extractive
    elif status_data[i]["status"] == "garrison":
        status_data[i]["sovereignty"] = minf(0.65, status_data[i]["sovereignty"] + 0.20)
```

---

### 12. Edge Cost Function

**Domain:** Geography / Technology
**Location:** `_edge_cost()` and `_base_era_cost()` helpers

**The math:**
```
SAIL ERA (year < −500):
  Reach, hops 1:   350 years
  Reach, hops 2:   580 years
  Reach, hops 3:  1060 years
  Reach, hops 4+: 8000 years
  Lattice, garrison (hops ≤ 3):  167 years
  Lattice, other:              12000 years

INDUSTRIAL ERA (−500 to −200):
  Reach, hops 1–4: 125 years
  Reach, hops 5–6: 145 years
  Reach, hops 7+:  200 years
  Lattice, garrison (hops ≤ 3):   85 years
  Lattice, hops ≤ 5:             350 years
  Lattice, hops 6+:              700 years

NUCLEAR ERA (year > −200):
  All:  61 years
```

Era-boundary optimization: if crossing from one era to the next mid-edge, check whether waiting for the cheaper era costs less total.

**Lore says:**
THE_REACH doc (03): "Pearl-string colonization — each garrison provisions the next." The escalating hop cost (350 → 580 → 1060 → 8000) encodes exactly this: each additional hop requires staging from the previous garrison, and the marginal cost of provisioning rises geometrically with each step into unknown water.

THE_LATTICE doc (04): The Lattice's garrison wall is characterized by short-distance reliability (167 years for nearby hops) and near-total inability to project beyond it (12000 years for non-garrison hops). "Zheng He sailed once and stopped" — the pulse model is prohibitively expensive, not impossible.

The industrial era cost reduction (~3–4× cheaper) reflects steam-powered ships reducing crossing uncertainty. Nuclear era (61 years, uniform) reflects comprehensive survey mode.

**Assessment:** This function is the best-calibrated piece of the history engine. It correctly encodes:
- The pearl-string compounding cost of Reach expansion
- The Lattice's defensive short-hop effectiveness and long-hop impracticality
- Era-driven cost reductions matching technological capability
- The smart era-boundary optimization (waiting for a better era is sometimes cheaper)

The era-boundary optimization has a subtle correctness property: it uses `_base_era_cost()` (a plain lookup without recursion) rather than calling `_edge_cost()` recursively, which correctly matches the JSX implementation.

**No changes recommended.** This function works as intended.

---

### 13. Σ2ⁿ Redistribution

**Domain:** Geography
**Location:** Phase 2, `assign_politics()`

**The math:**
```gdscript
var serial_n     = maxi(1, roundi(float(nc) * 0.05))   # 5%  of contactable archs
var colonial_n   = maxi(1, roundi(float(nc) * 0.10))   # 10%
var industrial_n = maxi(2, roundi(float(nc) * 0.20))   # 20%
var nuclear_n    = maxi(2, roundi(float(nc) * 0.40))   # 40%
# remaining 25% = El Dorados (uncontacted)

# Era time windows:
# Serial:     −5000 to −2000 BP (3000 year window)
# Colonial:   −2000 to  −500 BP (1500 year window)
# Industrial:  −500 to  −200 BP ( 300 year window)
# Nuclear:     −200 to  df_year  (variable, < 200 year window)
```

Dijkstra order is preserved; only timing is remapped. The redistribution ensures the discovery rate accelerates (more contacts per unit time as the simulation approaches the present).

**Lore says:**
DESIGN_SPEC §5 on the Σ2ⁿ distribution: "2+4+8+16 = 30, ~25% uncontacted. The Σ2ⁿ curve should emerge from the production function rather than being imposed by redistribution."

The design spec's intended architecture is that the Solow-Romer E(t) function produces expeditions per tick, and the accelerating contact rate emerges naturally from A(t) compounding with each new contact. The redistribution is an explicit acknowledgment that the production function isn't fully implemented yet.

**Assessment:** The redistribution correctly implements the 2+4+8+16 proportions. As a placeholder for the full production function, it is effective and produces the right macro-shape of discovery history. The El Dorado mechanic (archs beyond the budget disappear from the map entirely) is lore-consistent and narratively interesting.

The nuclear-era window sizing (`min(200, df_off - 200)`) correctly ties the nuclear-era discovery window to the Dark Forest year, ensuring nuclear-era contacts happen before the DF event rather than racing to finish after it.

**No changes recommended** until the full Solow-Romer per-tick simulation is implemented.

---

## Critical Missing Feature: `computeSubstrate`

The JSX reference contains a `computeSubstrate()` function (lines 265–509) that computes per-arch:

| Computed | Used for | Design Spec reference |
|---|---|---|
| Climate model (wind belt, rainfall, temp, tidal range, gyre position, upwelling) | All downstream substrate | §10a, §11 |
| Crop assignment (paddi/emmer/taro/nori/sago/papa with canGrow predicates) | Population ceilings, political culture, mode of production | §10a |
| Yield ranking (primary/secondary crop + quality) | Trade recovery, extraction ceilings | §10a |
| Trade goods (stimulant/fiber/protein production + deficit flags) | Thompson Sampling α inflation, trade recovery | §10b |
| Political culture (Almond & Verba awareness/participation, initialized from crop) | Per-tick drift targets, posture selection | §10c |
| Mode of production (surplus centralization / labor commodification, initialized from crop) | Extraction ceiling, contradiction tension, colonial trajectory | §10d |
| Mineral resources (Fe/Cu/Au/Pu with geology-biased seeding) | Nuclear-era capability, colonial motivation | §10g |
| Narrative substrate (gender economy, metaphor system, religious mode) | Popup display, narrative generation | §10e |

None of this exists in `history_engine.gd`. The Godot simulation uses only the `potential` scalar as a proxy for everything `computeSubstrate` computes. As a consequence:

- The history engine cannot distinguish a paddi arch from a papa arch
- The epidemic shock cannot implement the crop-distance modifier
- The trade recovery cannot differentiate a nori trade-hub from a sago leisure island
- The extraction ceiling cannot be derived from the mode of production
- The colonial trajectory (e.g., Tributary → Plantation Colony) cannot be computed
- The political culture (parochial/subject/civic) is absent from all state output
- The contradiction tension (Asiatic, capitalist, neocolonial) cannot drive drift

The substrate model is the root cause of most of the deficiencies listed in this document. The epidemiological shock, trade recovery rate, extraction ceiling, and antiquity growth curve are all approximations of substrate-derived functions that the design spec has fully specified.

**Port priority:** `computeSubstrate` should be ported to GDScript before the continuous political-economy space is implemented, because political culture initialization (Almond & Verba from crop) and mode of production initialization (from crop) are required inputs to the per-tick drift model.

---

## Summary and Priority Matrix

| # | Function | Current Behavior | Lore Alignment | Priority |
|---|---|---|---|---|
| 1 | Resource potential formula | Peak count + height + shelf, ignores latitude and minerals | Partial | Medium |
| 2 | Antiquity growth curve | `pow(1.002, 30)` = 3–6% growth over 15,000 years | Low — near-flat, crop differentiation absent | High |
| 3 | Epidemiological shock | Uniform 40–75% mortality regardless of ecology | Low — crop-distance modifier absent | High |
| 4 | Trade recovery | Linear time-on-network, `×0.0004/yr` | Partial — nori/stimulant advantage absent | Low |
| 5 | Network effect (log₂) | Lattice coefficient 0.30 > Reach 0.20 | Inverted — contradicts A₀ differential | Medium |
| 6 | Garrison absorption | Bug: absorbed pop not subtracted from source arch | Bug | High (trivial) |
| 7 | Tributary tribute | 5–10%, not subtracted from arch | Acceptable | Low |
| 8 | Extraction rate curve | Linear 15%→30%, no ceiling, enslaved as headcount | Partial — ceiling and collapse absent | Medium |
| 9 | Industrial growth multipliers | Lattice higher tech+resource coefficients than Reach | Inverted — contradicts Solow-Romer A₀ differential | Medium |
| 10 | Tech progression curves | Hard floors prevent seed variance and third-power emergence | Partial | Low |
| 11 | Nuclear era access/transfer | Access 0.7/0.5/0.3 by prior status | Good | None |
| 12 | Status assignment values | Fixed at contact, never updated | Critical gap — entire continuous space absent | Critical |
| 13 | Edge cost function | Pearl-string and garrison-wall costs, era-aware optimization | Excellent | None |
| 14 | Σ2ⁿ redistribution | 5/10/20/40% by era, 25% El Dorado | Correct | None |
| 15 | `computeSubstrate` | **Does not exist in GDScript** | Critical gap — root cause of all substrate deficiencies | Critical |

### Recommended Implementation Order

**Critical (blocks lore fidelity at a structural level):**
1. Port `computeSubstrate()` to GDScript — unblocks items 2, 3, 4, 8, 9, 12 simultaneously
2. Add per-era sovereignty/trade integration drift so nuclear-era output shows post-colonial recovery

**High (significant misalignment, tractable without substrate):**
3. Fix garrison absorption bug: add `pop[i] -= absorbed`
4. Implement crop-distance epidemic shock using latitude proxy (see §3 recommendations)
5. Raise antiquity growth exponent: `0.003 + potential * 0.006` base rate

**Medium (design-spec misalignment, easy fix once identified):**
6. Swap Reach/Lattice log₂ coefficients in network effect formula
7. Correct industrial-era multipliers: Reach higher tech coefficient (0.12), Lattice higher resource coefficient (0.22)
8. Add extraction ceiling at 0.30 with stochastic social-collapse penalty

**Low (lore-consistent, minor polish):**
9. Reclassify enslaved population from raw headcount to productive capacity bonus
10. Soft-floor industrial-era tech to allow seed variance
11. Tie Green Revolution probability to extraction history
12. Add trade good type as multiplier in trade recovery formula

---

*Analysis written 2026-04-05. Based on lore docs through `docs/DESIGN_SPEC.md v0.4` and the JSX reference at `src/MONOLITH_REFERENCE.jsx`.*
