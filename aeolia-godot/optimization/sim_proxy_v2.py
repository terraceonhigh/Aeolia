"""
sim_proxy_v2.py — Energy-coupled, faction-agnostic history engine (Phase 1)

Implements the History Engine v2 plan:
  - Layer 1: Resource accounting + energy surplus per polity per tick
  - Layer 2: Political allocation by culture type (Civic/Subject/Parochial)
  - Layer 3: Spec v0.4 tick pipeline (8 stages), energy-coupled

21 tunable parameters.  No faction names in the simulation — hegemons emerge
from surplus + geography + culture.

One tick = one generation (~50 years).  400 ticks from -20,000 BP to present.

Usage:
    from sim_proxy_v2 import SimParams, DEFAULT_PARAMS, simulate, load_world
    world  = load_world("worlds/candidate_0216089.json")
    result = simulate(world, DEFAULT_PARAMS)
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Mulberry32 PRNG — matches GDScript RNG.gd exactly
# ---------------------------------------------------------------------------

class Mulberry32:
    __slots__ = ("state",)

    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF

    @staticmethod
    def _imul(a: int, b: int) -> int:
        a &= 0xFFFFFFFF; b &= 0xFFFFFFFF
        al, ah = a & 0xFFFF, (a >> 16) & 0xFFFF
        bl, bh = b & 0xFFFF, (b >> 16) & 0xFFFF
        r = (al * bl + (((ah * bl + al * bh) & 0xFFFF) << 16)) & 0xFFFFFFFF
        return r - 0x100000000 if r >= 0x80000000 else r

    @staticmethod
    def _urs(val: int, shift: int) -> int:
        return (val & 0xFFFFFFFF) >> shift

    def next_float(self) -> float:
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        s = self.state
        if s >= 0x80000000:
            s -= 0x100000000
        t      = self._imul(s ^ self._urs(s, 15), 1 | s)
        t_orig = t
        t      = (t + self._imul(t ^ self._urs(t, 7), 61 | t)) ^ t_orig
        result = (t ^ self._urs(t, 14)) & 0xFFFFFFFF
        return result / 4294967296.0


# ---------------------------------------------------------------------------
# Parameters — 21 tunable, grouped per v2 plan
# ---------------------------------------------------------------------------

@dataclass
class SimParams:
    # Continuous Culture Space (10) — replaces 11 categorical params
    # Allocation shares are affine functions of culture-space position (§10).
    # Calibrated so seed positions reproduce old categorical behavior:
    #   sago/taro  (ind≈0.4, out≈0.45)  → exp≈0.25, tech≈0.24, A0≈0.80  (old Parochial)
    #   emmer/nori (ind≈0.70, out≈0.75) → exp≈0.38, tech≈0.37, A0≈1.16  (old Civic)
    base_expansion:             float = 0.05   # minimum expansion share (at collective+inward)
    outward_expansion_coeff:    float = 0.35   # outward adds to expansion
    individual_expansion_coeff: float = 0.10   # individual adds to expansion
    base_tech:                  float = 0.05   # minimum tech share
    outward_tech_coeff:         float = 0.42   # outward adds to tech share
    base_A0:                    float = 0.30   # minimum TFP coefficient
    individual_A0_coeff:        float = 0.80   # individual amplifies A0
    outward_A0_coeff:           float = 0.40   # outward amplifies A0
    culture_drift_rate:         float = 0.010  # position drift per tick (~0.005–0.02)
    culture_noise_scale:        float = 0.15   # noise on initial culture position

    # Material Conditions (7)
    cu_unlock_tech:             float = 3.0
    au_contact_bonus:           float = 500.0
    naphtha_richness:           float = 2.0
    naphtha_depletion:          float = 0.008
    energy_to_tfp:              float = 0.51  # calibrated: gives DF at ~-200 on primary seed
    pu_dependent_factor:        float = 0.65
    resource_targeting_weight:  float = 2.0

    # Trade model (§12/§13)
    luxury_markup_rate:         float = 0.40   # per-hop markup for luxury goods (stimulants, fibers, prestige)
    bulk_markup_rate:           float = 0.10   # per-hop markup for bulk goods (food, raw materials)

    # Contact Dynamics (3)
    epi_base_severity:          float = 0.30
    sov_extraction_decay:       float = 0.04
    df_detection_range:         float = 0.6
    df_min_territory_frac:      float = 0.08   # both polities must control >= this fraction of world for DF

    # Malthusian clamp (Q5 resolution) — applied to energy surplus for tech < 4
    carry_cap_scale:            float = 1.0    # carrying_capacity = crop_y × n_archipelagos × scale

    # Desperation / Tech Decay (3) — §11
    maintenance_rate:           float = 0.01   # energy cost per tech² per tick
    decay_rate:                 float = 0.10   # tech loss per unit maintenance shortfall
    desperation_weight:         float = 0.50   # how strongly resource_pressure overrides culture

    # Religion / Piety (Norris-Inglehart + Grzymala-Busse) — Stage 2c/2d
    piety_drift_rate:           float = 0.008  # base piety change per tick
    piety_absorption_bonus:     float = 0.35   # centripetal force: high piety boosts sovereignty extraction
    malaria_cap_penalty:        float = 0.40   # McNeill: carrying-capacity reduction in malaria belt (abs_lat<20)

    # Resource Curse (Sachs-Warner) — Stage 5
    resource_curse_strength:    float = 0.30   # TFP penalty for naphtha-heavy polities in industrial era

    # Trade Structure (Prebisch-Singer / Greif)
    prebisch_bulk_discount:     float = 0.75   # calorie exporters' terms of trade relative to luxury/relay nodes
    greif_relay_bonus:          float = 0.08   # extra per-contact benefit for high-connectivity relay nodes (Maghribi)

    # Resistance Dynamics (Scott's weapons of the weak)
    grievance_buildup_rate:     float = 0.25   # excess extraction → grievance accumulation rate
    grievance_resistance_mult:  float = 2.0    # grievance amplifies sovereignty recovery rate

    # Acemoglu-Robinson institutional stagnation (Why Nations Fail, 2012)
    # Extractive institutions accumulate when a polity is extracting surplus from
    # foreign-controlled territory with low individualism culture. The index
    # penalizes TFP independently of the naphtha resource curse — institutional
    # lock-in blocks creative destruction even when energy is abundant.
    institutional_lock_rate:    float = 0.12   # extraction → extractiveness buildup rate
    extractiveness_tfp_penalty: float = 0.40   # max TFP multiplier penalty at extractiveness=1.0

    # Proxy war casualties (Snyder 1965; Kahn 1965)
    # Nuclear deterrence stabilises direct hegemon conflict but enables sub-nuclear
    # competition in the contested periphery.  Each proxy absorption incurs population
    # losses proportional to target's defensive capacity (tech gap inverse).
    proxy_war_casualty_rate:    float = 0.10   # base population loss rate per proxy conquest

    # Walt balance-of-threat alliance formation (Walt 1987)
    # Non-hegemon polities align toward the less-threatening hegemon; aligned polities
    # resist absorption by the opposing hegemon. Threat = tech × (1 + extractiveness)
    # × fleet_scale / distance.
    alliance_formation_rate:    float = 0.04   # alignment drift speed per tick
    alliance_protection_str:    float = 2.5    # max targeting penalty for aligned-against hegemon

    # Fishery mechanics (calibrated in SimEngine.js; mirrored here for optimizer)
    fishery_recovery_rate:      float = 0.04
    fishery_overfish_rate:      float = 0.06

    # Davis (2001) — extractive admin amplifies crop failure (SimEngine.js only; not yet in Python sim)
    davis_amplification:        float = 0.30   # extractiveness=1.0 worsens failure modifier by 30%
    # Ostrom (1990) — civic/inclusive polities develop commons governance (SimEngine.js only)
    ostrom_commons_factor:      float = 0.55   # max depletion rate reduction from commons governance


DEFAULT_PARAMS = SimParams()

PARAM_BOUNDS: list = [
    ("base_expansion",              0.00, 0.20),
    ("outward_expansion_coeff",     0.10, 0.60),
    ("individual_expansion_coeff",  0.00, 0.25),
    ("base_tech",                   0.00, 0.15),
    ("outward_tech_coeff",          0.20, 0.70),
    ("base_A0",                     0.10, 0.60),
    ("individual_A0_coeff",         0.40, 1.50),
    ("outward_A0_coeff",            0.10, 0.80),
    ("culture_drift_rate",          0.003, 0.030),
    ("culture_noise_scale",         0.05, 0.35),
    ("cu_unlock_tech",              2.0,  4.0),
    ("au_contact_bonus",          100.0, 2000.0),
    ("naphtha_richness",            0.5,  5.0),
    ("naphtha_depletion",           0.001, 0.05),
    ("energy_to_tfp",               0.5,  2.0),
    ("pu_dependent_factor",         0.4,  0.9),
    ("resource_targeting_weight",   0.0,  5.0),
    ("epi_base_severity",           0.15, 0.50),
    ("sov_extraction_decay",        0.01, 0.10),
    ("df_detection_range",          0.3,  1.0),
    ("df_min_territory_frac",       0.03, 0.20),
    ("luxury_markup_rate",          0.25, 0.55),
    ("bulk_markup_rate",            0.05, 0.20),
    ("maintenance_rate",            0.005, 0.05),
    ("decay_rate",                  0.05, 0.30),
    ("desperation_weight",          0.2,  1.0),
    # Religion / Piety
    ("piety_drift_rate",            0.003, 0.020),
    ("piety_absorption_bonus",      0.10,  0.60),
    ("malaria_cap_penalty",         0.20,  0.70),
    # Resource curse / trade structure
    ("resource_curse_strength",     0.10,  0.60),
    ("prebisch_bulk_discount",      0.50,  0.95),
    ("greif_relay_bonus",           0.02,  0.20),
    # Resistance
    ("grievance_buildup_rate",      0.10,  0.50),
    ("grievance_resistance_mult",   1.0,   4.0),
    # Acemoglu-Robinson
    ("institutional_lock_rate",     0.04,  0.30),
    ("extractiveness_tfp_penalty",  0.10,  0.60),
    # Proxy war
    ("proxy_war_casualty_rate",     0.02,  0.25),
    # Walt alliance formation
    ("alliance_formation_rate",     0.01,  0.12),
    ("alliance_protection_str",     1.0,   5.0),
]


def pack_params(p: SimParams) -> list:
    return [getattr(p, name) for name, _, _ in PARAM_BOUNDS]


def unpack_params(x) -> SimParams:
    p = SimParams()
    for i, (name, lo, hi) in enumerate(PARAM_BOUNDS):
        setattr(p, name, float(x[i]))
    return p


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log2(x: float) -> float:
    return math.log2(x) if x > 0 else 0.0

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _spearman_reversal(pre_colonial_state: dict, final_tech: list, N: int) -> float:
    """Compute Spearman rank correlation between pre-colonial tech and final tech.

    AJR reversal-of-fortune hypothesis (Acemoglu, Johnson & Robinson 2001):
    polities with higher pre-colonial prosperity (proxy: tech at first absorption)
    should end up *lower* in the final tech distribution if colonial institutions
    created extractive lock-in — producing a negative correlation.

    Returns float in [-1, 1] or 0.0 if fewer than 3 data points.
    """
    if len(pre_colonial_state) < 3:
        return 0.0
    indices = sorted(pre_colonial_state.keys())
    pre  = [pre_colonial_state[i]["tech"] for i in indices]
    post = [final_tech[i] for i in indices]
    n = len(indices)

    def _ranks(vals):
        sorted_idx = sorted(range(n), key=lambda k: vals[k])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and vals[sorted_idx[j + 1]] == vals[sorted_idx[j]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[sorted_idx[k]] = avg_rank
            i = j + 1
        return ranks

    r_pre  = _ranks(pre)
    r_post = _ranks(post)
    d2_sum = sum((r_pre[k] - r_post[k]) ** 2 for k in range(n))
    denom = n * (n * n - 1)
    if denom == 0:
        return 0.0
    return 1.0 - 6.0 * d2_sum / denom


_ISLAND_MAX_HEIGHT = 3000.0

# ---------------------------------------------------------------------------
# Crop → political culture mapping
# Plan: emmer→Civic, paddi→Subject, taro/sago/papa→Parochial, nori→Parochial-Civic hybrid
# Nori maps to civic because it fills the same niche as emmer (mid-latitude maritime
# trade culture with high tech orientation) and the plan describes it as "High tech,
# maritime trade orientation" with Beta(1.5,1) optimistic priors.
# ---------------------------------------------------------------------------

# Crop → culture-space seed: (coll_ind, inw_out) in range -1 to +1
# coll_ind: -1 = Collective, +1 = Individual (§10 Axis 1)
# inw_out:  -1 = Inward,     +1 = Outward    (§10 Axis 2)
# Calibrated so the old categorical regions emerge naturally:
#   Civic   ≈ coll_ind >  0.3 & inw_out >  0.3
#   Subject ≈ coll_ind < -0.3 & inw_out <  0.0
#   Parochial ≈ centre
_CROP_CULTURE_SEED: dict = {
    "emmer":    ( 0.45,  0.55),   # Individual+Outward → Civic analog
    "nori":     ( 0.35,  0.65),   # Individual+Outward, maritime emphasis
    "paddi":    (-0.55, -0.20),   # Collective, slight inward (irrigated-rice bureaucracy)
    "taro":     (-0.10,  0.05),   # Slight collective, near centre
    "sago":     (-0.20, -0.10),   # Slight collective+inward
    "papa":     ( 0.15,  0.15),   # Near centre, slight individual
    "foraging": ( 0.00,  0.00),   # True centre
}


def _culture_label_from_pos(pos) -> str:
    """Derive backward-compat culture label from continuous position."""
    ci, io = pos
    if ci > 0.3 and io > 0.3:   return "civic"
    if ci < -0.3 and io < 0.0:  return "subject"
    return "parochial"

_TROPICAL  = frozenset(["paddi", "taro", "sago"])
_TEMPERATE = frozenset(["emmer", "papa"])


def _crop_distance(contactor: str, contacted: str) -> float:
    if contactor == contacted:
        return 0.2
    ct = contactor in _TROPICAL
    cd = contacted in _TROPICAL
    if (ct and cd) or (contactor in _TEMPERATE and contacted in _TEMPERATE):
        return 0.5
    if frozenset([contactor, contacted]) == frozenset(["paddi", "papa"]):
        return 1.0
    return 0.8


def _gc_dist_arch(a: dict, b: dict) -> float:
    dot = a["cx"] * b["cx"] + a["cy"] * b["cy"] + a["cz"] * b["cz"]
    return math.acos(_clamp(dot, -1.0, 1.0))


# ---------------------------------------------------------------------------
# Substrate computation (with C generation)
# ---------------------------------------------------------------------------

def _compute_gyre_position(arch: dict, all_archs: list) -> float:
    cy_clamped = _clamp(arch["cy"], -1.0, 1.0)
    lat    = math.asin(cy_clamped) * 180.0 / math.pi
    abs_lat = abs(lat)
    band_archs = [a for a in all_archs
                  if abs(abs(math.asin(_clamp(a["cy"], -1.0, 1.0)) * 180.0 / math.pi) - abs_lat) < 15.0]
    if len(band_archs) < 2:
        return 0.5
    lons = sorted(math.atan2(a["cz"], a["cx"]) * 180.0 / math.pi for a in band_archs)
    max_gap = gap_center = 0.0
    for j in range(len(lons)):
        next_lon = lons[(j + 1) % len(lons)]
        if j == len(lons) - 1:
            next_lon += 360.0
        gap = next_lon - lons[j]
        if gap > max_gap:
            max_gap = gap
            gap_center = lons[j] + gap / 2.0
    if max_gap < 10.0:
        return 0.5
    my_lon = math.atan2(arch["cz"], arch["cx"]) * 180.0 / math.pi
    return _clamp(math.fmod(my_lon - gap_center + 540.0, 360.0) / 360.0, 0.0, 1.0)


def _compute_substrate(archs, plateau_edges, seed, naphtha_richness=2.0):
    rng = Mulberry32((seed if seed > 0 else 42) * 47 + 2024)
    n = len(archs)

    edge_count   = [0] * n
    edge_lengths = [[] for _ in range(n)]
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        edge_count[a] += 1; edge_count[b] += 1
        dot = _clamp(archs[a]["cx"] * archs[b]["cx"] + archs[a]["cy"] * archs[b]["cy"] +
                     archs[a]["cz"] * archs[b]["cz"], -1.0, 1.0)
        ang = math.acos(dot)
        edge_lengths[a].append(ang); edge_lengths[b].append(ang)

    substrates = []
    for i, arch in enumerate(archs):
        cy_clamped = _clamp(arch["cy"], -1.0, 1.0)
        lat     = math.asin(cy_clamped) * 180.0 / math.pi
        abs_lat = abs(lat)
        shelf_r = arch.get("shelf_r", 0.06)
        size    = shelf_r / 0.12

        peaks = arch.get("peaks", [])
        peak_count = len(peaks)
        avg_h = (sum(pk["h"] for pk in peaks) / (peak_count * _ISLAND_MAX_HEIGHT)
                 if peak_count > 0 else arch.get("avg_h", 0.0))

        if   abs_lat < 12: wind_belt = "doldrums"
        elif abs_lat < 28: wind_belt = "trades"
        elif abs_lat < 35: wind_belt = "subtropical"
        elif abs_lat < 55: wind_belt = "westerlies"
        elif abs_lat < 65: wind_belt = "subpolar"
        else:              wind_belt = "polar"

        base_rain = {"doldrums": 2800.0, "trades": 2200.0, "subtropical": 600.0,
                     "westerlies": 1400.0, "subpolar": 1100.0, "polar": 300.0}[wind_belt]
        orographic_bonus = 1.0 + avg_h * 1.8
        gyre_pos = _compute_gyre_position(arch, archs)
        if gyre_pos < 0.3:     ocean_warmth = 0.8 + gyre_pos
        elif gyre_pos > 0.7:   ocean_warmth = 0.3 - (gyre_pos - 0.7)
        else:                  ocean_warmth = 0.4 + gyre_pos * 0.2
        ocean_warmth = _clamp(ocean_warmth, 0.0, 1.0)

        moisture_bonus     = 1.0 + max(0.0, ocean_warmth - 0.4) * 0.4
        effective_rainfall = base_rain * orographic_bonus * moisture_bonus * 1.4
        mean_temp      = 28.0 - abs_lat * 0.45 + (ocean_warmth - 0.5) * 4.0
        seasonal_range = abs_lat * 0.15 * 0.7

        nearby = sum(1 for other in archs if other is not arch and
                     arch["cx"]*other["cx"] + arch["cy"]*other["cy"] + arch["cz"]*other["cz"] > 0.95)
        cluster_density = min(1.0, float(nearby) / 5.0)
        abs_lat_rad = abs_lat * math.pi / 180.0
        tidal_range = (2.0 + shelf_r * 30.0 + cluster_density * 4.0) * (0.8 + abs(math.sin(abs_lat_rad)) * 0.4)

        upwelling = 0.0
        if gyre_pos > 0.7: upwelling += 0.4
        if abs_lat < 5:    upwelling += 0.3
        upwelling += edge_count[i] * 0.08
        fisheries = min(1.0, upwelling * 0.5 + effective_rainfall * 0.0001 + edge_count[i] * 0.05)

        # Coast factor: ocean access for fisheries (coastline/area proxy)
        coast_factor_val = min(1.0, edge_count[i] * 0.18 + min(1.0, upwelling) * 0.25)

        # Fish base caloric yield by latitude: cold→sthaq/bakala, warm→tunnu/sardai
        if abs_lat > 38:
            fish_base_val = 2.0 + upwelling          # cold: sthaq + bakala (highest productivity)
        elif abs_lat > 22:
            fish_base_val = 1.6 + upwelling * 0.8    # temperate: mixed
        elif abs_lat > 10:
            fish_base_val = 1.2 + upwelling * 0.6    # subtropical: tunnu
        else:
            fish_base_val = 1.0 + upwelling * 0.4    # equatorial: sardai
        # fish_y = coast_factor * fish_base  (per §12 spec)
        fish_y_val = coast_factor_val * fish_base_val

        if   mean_temp > 24 and effective_rainfall > 2000: climate_zone = "tropical_wet"
        elif mean_temp > 24 and effective_rainfall < 1000: climate_zone = "tropical_dry"
        elif mean_temp > 10 and effective_rainfall > 1200: climate_zone = "temperate_wet"
        elif mean_temp > 10:                               climate_zone = "temperate_dry"
        elif mean_temp > 2:                                climate_zone = "subpolar"
        else:                                              climate_zone = "polar_fringe"

        can_grow = {
            "paddi": (mean_temp >= 20 and effective_rainfall >= 1200 and
                      tidal_range >= 2.0 and shelf_r >= 0.08 and abs_lat <= 28),
            "emmer": (mean_temp >= 8 and mean_temp <= 24 and
                      effective_rainfall >= 400 and effective_rainfall <= 2000 and
                      abs_lat >= 20 and abs_lat <= 55),
            "taro":  (mean_temp >= 21 and seasonal_range <= 4 and
                      effective_rainfall >= 1500 and abs_lat <= 20),
            "nori":  (mean_temp >= 5 and mean_temp <= 22 and
                      edge_count[i] >= 1 and upwelling >= 0.2),
            "sago":  (mean_temp >= 24 and effective_rainfall >= 2000 and
                      abs_lat <= 15 and shelf_r >= 0.04),
            "papa":  (mean_temp >= 2 and mean_temp <= 18 and
                      effective_rainfall >= 400 and abs_lat >= 35),
        }

        yields = {}
        if can_grow["paddi"]:
            yields["paddi"] = 5.0 * min(1.0, (mean_temp-18.0)/15.0) * min(1.0, effective_rainfall/1800.0) * min(1.0, tidal_range/5.0)
        if can_grow["emmer"]:
            yields["emmer"] = 2.5 * (1.0 - abs(mean_temp-16.0)/20.0) * (1.0 - abs(effective_rainfall-700.0)/1500.0)
        if can_grow["taro"]:
            yields["taro"] = 3.0 * min(1.0, (mean_temp-20.0)/8.0) * min(1.0, effective_rainfall/2000.0)
        if can_grow["nori"]:
            yields["nori"] = 1.5 * min(1.0, upwelling*2.0) * min(1.0, float(edge_count[i])/3.0) * 2.0
        if can_grow["sago"]:
            yields["sago"] = 4.0 * min(1.0, effective_rainfall/2500.0) * min(1.0, shelf_r/0.10)
        if can_grow["papa"]:
            yields["papa"] = 3.5 * (1.0 - abs(mean_temp-12.0)/15.0) * min(1.0, effective_rainfall/600.0)

        crop_entries = sorted(yields.items(), key=lambda kv: (-kv[1], kv[0]))
        primary_crop  = crop_entries[0][0] if crop_entries else "foraging"
        primary_yield = crop_entries[0][1] if crop_entries else 0.5
        secondary_crop = crop_entries[1][0] if len(crop_entries) > 1 else None

        # Trade goods — consume RNG in substrate order
        stim_map  = {"paddi": "char", "emmer": "qahwa", "taro": "awa", "sago": "pinang", "papa": "aqua", "nori": "", "foraging": ""}
        fiber_map = {"paddi": "seric", "emmer": "fell", "taro": "tapa", "sago": "tapa", "nori": "byssus", "papa": "qivu", "foraging": ""}
        prot_map  = {"paddi": "kerbau", "emmer": "kri", "taro": "moa", "sago": "moa", "nori": "", "papa": "", "foraging": ""}
        stim_type  = stim_map.get(primary_crop, "")
        fiber_type = fiber_map.get(primary_crop, "")
        prot_type  = prot_map.get(primary_crop, "")
        stim_prod  = (0.3 + rng.next_float() * 0.5) if stim_type  else 0.0
        fiber_prod = (0.3 + rng.next_float() * 0.5) if fiber_type else 0.0
        prot_prod  = (0.3 + rng.next_float() * 0.4) if prot_type  else 0.0
        nori_export = 0.0
        if primary_crop == "nori":      nori_export = 0.6 + rng.next_float() * 0.3
        elif can_grow.get("nori"):      nori_export = 0.1 + rng.next_float() * 0.2
        total_trade_value = stim_prod * 0.4 + fiber_prod * 0.3 + prot_prod * 0.2 + nori_export * 0.3

        # Minerals
        minerals = {
            "Fe": True,
            "Cu": rng.next_float() < 0.20,
            "Au": rng.next_float() < (0.05 + avg_h * 0.08),
            "Pu": rng.next_float() < (0.03 + size * 0.02),
        }

        # C (naphtha) — deterministic from geology (plan §2.2)
        minerals["C"] = shelf_r * tidal_range * naphtha_richness if shelf_r >= 0.04 else 0.0

        # Continuous culture-space initial position (§10)
        # Axis 0: coll_ind  -1=Collective, +1=Individual
        # Axis 1: inw_out   -1=Inward,     +1=Outward
        ci_seed, io_seed = _CROP_CULTURE_SEED.get(primary_crop, (0.0, 0.0))

        # Geography modulates crop's institutional pressure (§10 Initial Position)
        # Larger island → more Collective (coordination pressure at scale)
        ci_geo = -size * 0.25
        # Rugged terrain → more Individual (Scott's Zomia effect)
        ci_geo += avg_h * 0.20
        # More neighbors → more Outward; isolated → more Inward
        io_geo = min(1.0, nearby / 5.0) * 0.25
        # Larger coastline ratio (shelf_r proxy) → more Outward
        io_geo += min(1.0, shelf_r / 0.12) * 0.15
        # Isolation penalty
        io_geo -= (1.0 - min(1.0, nearby / 3.0)) * 0.15
        # Higher surplus potential → more Outward
        io_geo += primary_yield * 0.08

        ci_init = _clamp(ci_seed + ci_geo + (rng.next_float() - 0.5) * 0.30, -1.0, 1.0)
        io_init = _clamp(io_seed + io_geo + (rng.next_float() - 0.5) * 0.30, -1.0, 1.0)
        culture_pos = [ci_init, io_init]

        substrates.append({
            "climate": {
                "latitude": lat, "abs_latitude": abs_lat,
                "wind_belt": wind_belt, "mean_temp": mean_temp,
                "seasonal_range": seasonal_range,
                "effective_rainfall": effective_rainfall,
                "tidal_range": tidal_range, "ocean_warmth": ocean_warmth,
                "gyre_position": gyre_pos, "upwelling": upwelling,
                "fisheries_richness": fisheries, "climate_zone": climate_zone,
                "coast_factor": coast_factor_val, "fish_y": fish_y_val, "avg_h": avg_h,
            },
            "crops": {
                "primary_crop": primary_crop, "secondary_crop": secondary_crop,
                "primary_yield": primary_yield,
            },
            "trade_goods": {"total_trade_value": total_trade_value},
            "minerals": minerals,
            "culture_pos": culture_pos,
            "culture": _culture_label_from_pos(culture_pos),
        })
    return substrates


# ---------------------------------------------------------------------------
# World loading
# ---------------------------------------------------------------------------

def load_world(path: str) -> dict:
    import json
    with open(path) as f:
        data = json.load(f)
    flat_sub = data.get("substrate", [])
    if flat_sub and isinstance(flat_sub[0], dict) and "climate" not in flat_sub[0]:
        nested = []
        for idx, s in enumerate(flat_sub):
            shelf_r = data["archs"][idx].get("shelf_r", 0.06) if idx < len(data["archs"]) else 0.06
            tidal   = s.get("tidal_range", 2.0)
            minerals = dict(s.get("minerals", {"Fe": True, "Cu": False, "Au": False, "Pu": False}))
            if "C" not in minerals:
                minerals["C"] = shelf_r * tidal * 2.0 if shelf_r >= 0.04 else 0.0
            crop = s.get("primary_crop", "foraging")
            nested.append({
                "climate": {
                    "latitude": s.get("latitude", 0.0), "abs_latitude": s.get("abs_latitude", 30.0),
                    "tidal_range": tidal, "mean_temp": s.get("mean_temp", 18.0),
                    "effective_rainfall": s.get("effective_rainfall", 1000.0),
                    "upwelling": s.get("upwelling", 0.1),
                },
                "crops": {
                    "primary_crop": crop, "primary_yield": s.get("primary_yield", 0.5),
                    "secondary_crop": s.get("secondary_crop", None),
                },
                "trade_goods": {"total_trade_value": s.get("total_trade_value", 0.0)},
                "minerals": minerals,
                "culture_pos": list(_CROP_CULTURE_SEED.get(crop, (0.0, 0.0))),
                "culture": _culture_label_from_pos(_CROP_CULTURE_SEED.get(crop, (0.0, 0.0))),
            })
        data["substrate"] = nested
    return data


# ---------------------------------------------------------------------------
# IR posture selection (plan §5.6)
# ---------------------------------------------------------------------------

_POSTURE_TABLE = {
    ("HIGH", "HIGH"): "fortify",  ("HIGH", "MED"):  "project", ("HIGH", "LOW"): "explore",
    ("MED",  "HIGH"): "hedge",    ("MED",  "MED"):  "hedge",   ("MED",  "LOW"): "project",
    ("LOW",  "HIGH"): "align",    ("LOW",  "MED"):  "free_ride", ("LOW", "LOW"): "explore",
}


def _categorize_cap(surplus: float, ref: float) -> str:
    if ref <= 0: return "LOW"
    r = surplus / ref
    if r > 0.6: return "HIGH"
    if r > 0.25: return "MED"
    return "LOW"


# ---------------------------------------------------------------------------
# Beta sample (approximate, deterministic from Mulberry32)
# ---------------------------------------------------------------------------

def _beta_sample(rng: Mulberry32, a: float, b: float) -> float:
    mean = a / (a + b)
    var  = (a * b) / ((a + b) ** 2 * (a + b + 1))
    u1 = max(1e-10, rng.next_float())
    u2 = rng.next_float()
    z  = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return _clamp(mean + z * math.sqrt(var), 0.01, 0.99)


# ---------------------------------------------------------------------------
# Resource value — tech-gated unlock (plan §2.4)
# ---------------------------------------------------------------------------

def _resource_value(minerals: dict, tech: float, cu_unlock: float) -> float:
    val = 0.0
    if tech >= cu_unlock and minerals.get("Cu"):
        val += 1.0
    if tech >= 4.0 and minerals.get("Au"):
        val += 1.5
    c = minerals.get("C", 0.0)
    if tech >= 7.0 and c > 0:
        val += c * 5.0
    if tech >= 9.0 and minerals.get("Pu"):
        val += 10.0
    return val


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

TICK_YEARS = 50
START_YEAR = -20000
END_YEAR   = 0
N_TICKS    = (END_YEAR - START_YEAR) // TICK_YEARS  # 400


def simulate(world: dict, params: SimParams = None, seed: int = 0) -> dict:
    if params is None:
        params = DEFAULT_PARAMS
    p = params

    archs         = world["archs"]
    plateau_edges = world["plateau_edges"]
    N             = len(archs)
    seed          = seed or world.get("seed", 42)

    # Substrate (recompute if needed, adding C and culture_pos)
    substrate = world.get("substrate")
    if not substrate or "culture_pos" not in substrate[0]:
        substrate = _compute_substrate(archs, plateau_edges, seed, p.naphtha_richness)
    # Ensure C and culture_pos fields
    for i in range(N):
        mins = substrate[i]["minerals"]
        if "C" not in mins:
            sr = archs[i].get("shelf_r", 0.06)
            td = substrate[i]["climate"].get("tidal_range", 2.0)
            mins["C"] = sr * td * p.naphtha_richness if sr >= 0.04 else 0.0
        if "culture_pos" not in substrate[i]:
            crop = substrate[i]["crops"].get("primary_crop", "foraging")
            substrate[i]["culture_pos"] = list(_CROP_CULTURE_SEED.get(crop, (0.0, 0.0)))
        # Refresh backward-compat label from position
        substrate[i]["culture"] = _culture_label_from_pos(substrate[i]["culture_pos"])

    # Fish and land fields fallback (for pre-computed substrates without these fields)
    for i in range(N):
        clim_i = substrate[i]["climate"]
        if "coast_factor" not in clim_i:
            abs_lat_i = clim_i.get("abs_latitude", 30.0)
            upwell_i  = clim_i.get("upwelling", 0.1)
            ec_i = sum(1 for e in plateau_edges if int(e[0]) == i or int(e[1]) == i)
            cf_i = min(1.0, ec_i * 0.18 + min(1.0, upwell_i) * 0.25)
            if abs_lat_i > 38:   fb_i = 2.0 + upwell_i
            elif abs_lat_i > 22: fb_i = 1.6 + upwell_i * 0.8
            elif abs_lat_i > 10: fb_i = 1.2 + upwell_i * 0.6
            else:                fb_i = 1.0 + upwell_i * 0.4
            clim_i["coast_factor"] = cf_i
            clim_i["fish_y"] = cf_i * fb_i
        if "avg_h" not in clim_i:
            peaks_i = archs[i].get("peaks", [])
            clim_i["avg_h"] = (sum(pk["h"] for pk in peaks_i) / (len(peaks_i) * _ISLAND_MAX_HEIGHT)
                               if peaks_i else archs[i].get("avg_h", 0.2))

    rng = Mulberry32((seed if seed != 0 else 42) * 31 + 1066)

    # ── Continuous culture-space positions (§10) ─────────────────────────────
    # cpos[i] = [coll_ind, inw_out]  range -1..+1 each
    # Initialised from substrate seed + sim-RNG noise; drifts for polity cores.
    cpos = []
    for i in range(N):
        base = substrate[i].get("culture_pos", [0.0, 0.0])
        ci = _clamp(float(base[0]) + (rng.next_float() - 0.5) * 2.0 * p.culture_noise_scale, -1.0, 1.0)
        io = _clamp(float(base[1]) + (rng.next_float() - 0.5) * 2.0 * p.culture_noise_scale, -1.0, 1.0)
        cpos.append([ci, io])

    # Adjacency
    adj = [[] for _ in range(N)]
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        if b not in adj[a]: adj[a].append(b)
        if a not in adj[b]: adj[b].append(a)

    # ── Per-arch state ────────────────────────────────────────────────────
    pop          = [0.0] * N
    tech         = [0.0] * N
    sovereignty  = [1.0] * N
    c_remaining  = [0.0] * N
    c_initial    = [0.0] * N
    knowledge    = [0.0] * N
    controller   = list(range(N))    # each arch controls itself
    contact_set  = [set() for _ in range(N)]  # per-arch: set of other polity cores contacted
    fleet_scale  = [0.0] * N
    awareness    = {}                # sparse: (i,j) -> float
    absorbed_tick = [None] * N
    first_contact_tick = [None] * N

    # ── Religion / Piety state (Norris-Inglehart + Grzymala-Busse) ──────────
    # Initialized from climate (tropical warmth → higher initial piety) and
    # culture-space position (collective orientation → higher initial piety).
    # Uses a SEPARATE RNG to avoid contaminating the main simulation RNG stream
    # (which is calibrated against the seed-216089 Dark Forest timing target).
    piety_rng     = Mulberry32((seed if seed != 0 else 42) * 13 + 2025)
    piety         = [0.0] * N
    schism_pressure = [0.0] * N
    for i in range(N):
        abs_lat_i = substrate[i]["climate"].get("abs_latitude", 30.0)
        warm_seed_p = max(0.0, (25.0 - abs_lat_i) / 25.0) * 0.20
        ci_seed_i = substrate[i].get("culture_pos", [0.0, 0.0])[0]
        collective_seed = max(0.0, -ci_seed_i) * 0.15
        piety[i] = _clamp(0.25 + warm_seed_p + collective_seed
                          + (piety_rng.next_float() - 0.5) * 0.20, 0.05, 0.90)
    schism_log = []

    # ── Malaria factors (McNeill 1976; Gallup & Sachs 2001) ──────────────────
    # Carrying-capacity penalty for tropical belts (abs_lat < 20°).
    # Penalty resolves at tech ≥ 6 (germ-theory medicine / DDT analogue).
    malaria_factor = [0.0] * N
    for i in range(N):
        al = substrate[i]["climate"].get("abs_latitude", 30.0)
        malaria_factor[i] = max(0.0, (20.0 - al) / 20.0) if al < 20.0 else 0.0

    # ── Grievance / Resistance state (Scott 1985, 1990) ──────────────────────
    # Per arch: accumulated grievance from colonial extraction above tolerable level.
    # Grievance amplifies sovereignty recovery (self-limiting empire mechanic).
    grievance       = [0.0] * N
    extractiveness  = [0.0] * N   # Acemoglu-Robinson: institutional lock-in index (0=inclusive, 1=extractive)
    proxy_war_log   = []           # Snyder/Kahn: proxy war events in nuclear era
    relay_contact_since = {}       # (core, other) → tick: per-pair relay contact age for endemicity
    pre_colonial_state = {}        # AJR reversal-of-fortune: arch → {tick, pop, tech} at first absorption

    # Initialise
    for i, arch in enumerate(archs):
        pk_count = len(arch.get("peaks", [])) or arch.get("peak_count", 2)
        avg_h = arch.get("avg_h", 0.2)
        if "peaks" in arch and arch["peaks"]:
            avg_h = sum(pk["h"] for pk in arch["peaks"]) / (pk_count * _ISLAND_MAX_HEIGHT)
        sz = arch.get("shelf_r", 0.06) / 0.12
        pop[i]  = float(pk_count) * sz * (3.0 + rng.next_float() * 4.0)
        tech[i] = 0.3 + rng.next_float() * 0.4
        c_remaining[i] = substrate[i]["minerals"].get("C", 0.0)
        c_initial[i]   = c_remaining[i]
        knowledge[i]   = substrate[i]["crops"]["primary_yield"] * 0.3

    # Carrying capacity per arch (from crop yield and terrain)
    carry_cap = [0.0] * N
    for i in range(N):
        y = substrate[i]["crops"]["primary_yield"]
        pk = len(archs[i].get("peaks", [])) or archs[i].get("peak_count", 2)
        sz = archs[i].get("shelf_r", 0.06) / 0.12
        carry_cap[i] = y * pk * sz * 50.0 + 5.0  # base carrying capacity

    # ── Continuous culture helpers (§10) ─────────────────────────────────────

    def _culture_label(core: int) -> str:
        """Backward-compat label derived from polity's current position."""
        return _culture_label_from_pos(cpos[core])

    def _shares_from_pos(pos) -> tuple:
        """Allocation shares as affine functions of culture-space position."""
        ci, io = pos
        individual = (ci + 1.0) * 0.5   # 0=Collective, 1=Individual
        outward    = (io + 1.0) * 0.5   # 0=Inward,     1=Outward
        exp_s = p.base_expansion + p.outward_expansion_coeff * outward + p.individual_expansion_coeff * individual
        tec_s = p.base_tech + p.outward_tech_coeff * outward
        con_s = max(0.05, 1.0 - exp_s - tec_s)
        t = exp_s + tec_s + con_s
        return (exp_s / t, tec_s / t, con_s / t)

    def _A0_from_pos(pos) -> float:
        """TFP coefficient as affine function of culture-space position."""
        ci, io = pos
        individual = (ci + 1.0) * 0.5
        outward    = (io + 1.0) * 0.5
        return p.base_A0 + p.individual_A0_coeff * individual + p.outward_A0_coeff * outward

    def _ts_priors_from_pos(pos) -> tuple:
        """Thompson Sampling Beta priors from continuous position (§10)."""
        ci, io = pos
        outward    = (io + 1.0) * 0.5
        collective = (1.0 - ci) * 0.5   # 1=Collective, 0=Individual
        ts_a = 1.0 + outward
        ts_b = 1.0 + (1.0 - outward) * collective
        return (ts_a, ts_b)

    # Helper: polity aggregation
    def _controlled(core):
        return [j for j in range(N) if controller[j] == core]

    def _polity_pop(core):
        return sum(pop[j] for j in range(N) if controller[j] == core)

    def _polity_c(core):
        return sum(c_remaining[j] for j in range(N) if controller[j] == core)

    def _has_pu(core):
        return any(substrate[j]["minerals"].get("Pu") for j in range(N) if controller[j] == core)

    # ── Diagnostics ───────────────────────────────────────────────────────
    epi_log            = []
    expansion_log      = []
    df_year = df_arch = df_detector = None
    df_hegemon_pair    = None   # [df_arch, df_detector] set once on DF fire
    scramble_onset     = None   # tick when C-rich targeting begins
    pu_scramble_onset  = None
    tech_snapshots     = {}
    pop_snapshots      = {}
    wave_epi_log       = []     # accumulated across all ticks (Stage 5b)

    # ── Walt balance-of-threat alignment (post-DF) ────────────────────────
    # alignment[i] ∈ [-1, 1]: positive → aligned toward df_detector (h_b),
    # negative → aligned toward df_arch (h_a). Initialized after DF fires.
    # Walt (1987): states balance against threats (power × extractiveness ×
    # fleet_scale / distance), not raw power alone.
    alignment = [0.0] * N
    tech_decay_log     = []     # §11: records of tech decay events
    desperation_log    = []     # §11: records of desperation-mode activations

    # ── TICK LOOP ─────────────────────────────────────────────────────────
    for tick in range(N_TICKS):
        year = START_YEAR + tick * TICK_YEARS

        # Active polity cores
        cores = sorted(set(controller))

        # Precompute per-core aggregates (amortised over stages)
        core_pop     = {c: _polity_pop(c) for c in cores}
        core_c       = {c: _polity_c(c) for c in cores}
        core_n_ctrl  = {c: sum(1 for j in range(N) if controller[j] == c) for c in cores}
        # Aggregate food yield across all controlled arches (for §11 deficit detection)
        core_food    = {c: sum(substrate[j]["crops"]["primary_yield"]
                               for j in range(N) if controller[j] == c) for c in cores}

        # ──────────────────────────────────────────────────────────────
        # TRADE PRE-PASS: Net trade energy per polity (§12)
        # Gravity model: volume ∝ complementarity × sqrt(mass_A×mass_B) / dist²
        # Layers gated by tech: Subsistence(0+), Relay(2+), Administered(5+)
        # ──────────────────────────────────────────────────────────────
        cores_set  = set(cores)
        trade_net  = {c: 0.0 for c in cores}

        for _tc in cores:
            tc_tech = tech[_tc]
            for _other in contact_set[_tc]:
                if _other not in cores_set or _other <= _tc:
                    continue
                tc_other_tech = tech[_other]
                eff_tech = min(tc_tech, tc_other_tech)

                dist_rad = _gc_dist_arch(archs[_tc], archs[_other])
                if dist_rad < 1e-6:
                    continue

                # Commodity complementarity: different goods → more to trade
                crop_a = substrate[_tc]["crops"]["primary_crop"]
                crop_b = substrate[_other]["crops"]["primary_crop"]
                comp = 0.5 if crop_a == crop_b else 1.0

                lat_a = substrate[_tc]["climate"]["abs_latitude"]
                lat_b = substrate[_other]["climate"]["abs_latitude"]
                if abs(lat_a - lat_b) > 15.0:
                    comp += 0.3   # cold+warm water: fish variety trade

                for _res in ("Au", "Cu"):
                    if bool(substrate[_tc]["minerals"].get(_res)) != bool(substrate[_other]["minerals"].get(_res)):
                        comp += 0.15
                comp = min(comp, 2.0)

                # ── Axelrod (1997) cultural polarization + freezing ───────────────────
                # Polities with maximal cultural distance trade less effectively (fewer
                # shared norms, legal frameworks, practices) and, beyond a threshold,
                # stop interacting entirely — frozen cultural divergence.
                # Axelrod (1997): "The Dissemination of Culture." *J. Conflict Resolution* 41(2).
                # Below freeze threshold: continuous friction (0.6 → 0.0 penalty range).
                # At/above freeze threshold: no trade interaction (cultural isolation).
                ci_a, io_a = cpos[_tc]
                ci_b, io_b = cpos[_other]
                culture_dist = math.sqrt((ci_a - ci_b)**2 + (io_a - io_b)**2) / 2.828
                if culture_dist >= 0.85:          # frozen: no cultural overlap → no interaction
                    comp = 0.0
                else:
                    axelrod_friction = 1.0 - max(0.0, (culture_dist - 0.6) * 0.5)
                    comp *= axelrod_friction

                # Tech-gated layer: markup and effective range
                if eff_tech < 2.0:
                    # Subsistence: direct neighbors only, low markup
                    if dist_rad > 0.55:
                        continue
                    eff_markup = p.bulk_markup_rate
                    layer_mult = 0.25
                elif eff_tech < 5.0:
                    # Relay: luxury+bulk mix, hop-limited
                    hops = max(1, int(dist_rad / 0.35) + 1)
                    if hops > 4:
                        continue
                    eff_markup = min(0.85, (p.luxury_markup_rate * 0.6 + p.bulk_markup_rate * 0.4) * hops)
                    layer_mult = 0.65
                else:
                    # Administered: direct routes, bulk markup
                    eff_markup = p.bulk_markup_rate
                    layer_mult = 1.0

                # Gravity model: mass = sqrt(pop) × primary_yield
                mass_a = math.sqrt(max(1.0, core_pop[_tc]))    * substrate[_tc]["crops"]["primary_yield"]
                mass_b = math.sqrt(max(1.0, core_pop[_other])) * substrate[_other]["crops"]["primary_yield"]
                volume = layer_mult * comp * math.sqrt(mass_a * mass_b) / (dist_rad ** 2)
                base_benefit = volume * (1.0 - eff_markup) * 0.003   # scale: ~0.1 per pair at relay

                # ── Prebisch-Singer (1950): bulk calorie exporters face structurally
                # declining terms of trade relative to specialty/luxury/relay nodes.
                # Paddi, taro, sago, papa are bulk staples; emmer and nori produce
                # storable/specialty goods that command higher per-unit value.
                _BULK_CROPS = frozenset(["paddi", "taro", "sago", "papa"])
                ps_a = p.prebisch_bulk_discount if crop_a in _BULK_CROPS else 1.0
                ps_b = p.prebisch_bulk_discount if crop_b in _BULK_CROPS else 1.0

                # ── Greif (1989): relay intermediaries with many contacts capture
                # asymmetric price differential (Maghribi trader coalition model).
                # High-connectivity nodes act as information bottlenecks.
                relay_bonus_a = min(0.40, len(contact_set[_tc]) * p.greif_relay_bonus)
                relay_bonus_b = min(0.40, len(contact_set[_other]) * p.greif_relay_bonus)

                trade_net[_tc]    += base_benefit * ps_a * (1.0 + relay_bonus_a)
                trade_net[_other] += base_benefit * ps_b * (1.0 + relay_bonus_b)

        # ──────────────────────────────────────────────────────────────
        # STAGE 1: Resource accounting (Layer 1) — layered energy balance
        # ──────────────────────────────────────────────────────────────
        energy_ratio      = {}  # per core
        energy_surplus    = {}
        resource_pressure = {}  # §11: 0=comfortable, →1=near-collapse
        food_deficit_flag = {}  # §11: food layer in shortfall
        ind_deficit_flag  = {}  # §11: industrial layer in shortfall
        nuc_deficit_flag  = {}  # §11: nuclear layer in shortfall

        for core in cores:
            tp = max(1.0, core_pop[core])
            ct = tech[core]

            if ct >= 7.0:
                # Industrial+ energy from naphtha
                e_demand = tp * ct * 0.002
                e_supply = core_c[core] * 0.2
                ratio = _clamp(e_supply / max(0.001, e_demand), 0.3, 1.5)
                surplus = max(0.0, e_supply - e_demand) * 0.2 + tp * 0.01
                ind_def = e_supply < e_demand
            else:
                # Pre-industrial: caloric budget = crop + fish + trade (§12)
                crop_y   = substrate[core]["crops"]["primary_yield"]
                clim_c   = substrate[core]["climate"]
                avg_h_c  = clim_c.get("avg_h", archs[core].get("avg_h", 0.2))
                land_factor = max(0.3, 1.0 - avg_h_c * 0.35)

                # Fish: aggregate over polity, average per arch
                # total_cal = crop_y × land_factor + fish_y × coast_factor  (per spec)
                fish_pol = sum(
                    substrate[j]["climate"].get("fish_y", 0.0) *
                    substrate[j]["climate"].get("coast_factor", 0.0)
                    for j in range(N) if controller[j] == core
                )
                fish_avg = fish_pol / max(1, core_n_ctrl[core])

                total_cal = crop_y * land_factor + fish_avg

                # Trade: energy = total_cal + trade_imports − trade_exports → net_trade
                net_trade = trade_net.get(core, 0.0)

                ratio   = _clamp(0.6 + total_cal * 0.2, 0.3, 1.5)
                surplus = total_cal * tp * 0.01 + net_trade
                ind_def = False

                # Malthusian carrying-capacity clamp (Q5 resolution):
                # for tech < 4, surplus shrinks as population approaches
                # carrying capacity — produces Malthusian trap without
                # touching the production function or accel_rate table.
                if ct < 4.0:
                    n_ctrl = max(1, core_n_ctrl[core])
                    carrying_capacity = crop_y * n_ctrl * p.carry_cap_scale
                    surplus *= min(1.0, carrying_capacity / max(tp, 1.0))

            energy_ratio[core]   = ratio
            energy_surplus[core] = surplus

            # — §11 Desperation: maintenance cost and resource pressure —
            # Maintenance is quadratic: high-tech civs need more energy to stay there
            maintenance = ct * ct * p.maintenance_rate
            rp = max(0.0, (maintenance - surplus) / maintenance) if maintenance > 0 else 0.0
            resource_pressure[core] = rp

            # Deficit flags for targeting hierarchy (food > industrial > nuclear)
            # Food: average food yield per controlled arch vs. per-arch subsistence
            avg_food_yield = core_food[core] / max(1, core_n_ctrl[core])
            food_deficit_flag[core] = avg_food_yield < 1.0          # below subsistence threshold
            ind_deficit_flag[core]  = ind_def
            nuc_deficit_flag[core]  = ct >= 9.0 and not _has_pu(core)

        # ──────────────────────────────────────────────────────────────
        # STAGE 2: Political allocation (Layer 2)
        # ──────────────────────────────────────────────────────────────
        exp_budget   = {}
        tech_bgt     = {}
        consol_budget = {}

        max_surplus = max(energy_surplus.values()) if energy_surplus else 1.0

        for core in cores:
            exp_s, tec_s, con_s = _shares_from_pos(cpos[core])

            # IR posture
            own_cap = _categorize_cap(energy_surplus[core], max_surplus)
            other_surpluses = [energy_surplus[c] for c in cores if c != core]
            max_other = max(other_surpluses) if other_surpluses else 0.0
            oth_cap = _categorize_cap(max_other, max_surplus)
            posture = _POSTURE_TABLE.get((own_cap, oth_cap), "hedge")

            if posture in ("explore", "project"):
                exp_s *= 1.3; con_s *= 0.7
            elif posture in ("fortify", "hedge"):
                con_s *= 1.3; exp_s *= 0.7
            elif posture == "align":
                con_s *= 1.2; tec_s *= 0.8

            t = exp_s + tec_s + con_s
            exp_s /= t; tec_s /= t; con_s /= t

            # — §11 Desperation override: resource_pressure blends culture out —
            rp = resource_pressure.get(core, 0.0)
            if rp > 0.0:
                # Determine desperation allocation target from deficit hierarchy
                if food_deficit_flag.get(core, False):
                    # Food-first: maximum expansion toward fertile land
                    d_exp, d_tec, d_con = 0.65, 0.20, 0.15
                elif ind_deficit_flag.get(core, False):
                    # Industrial: strong expansion toward naphtha
                    d_exp, d_tec, d_con = 0.55, 0.28, 0.17
                elif nuc_deficit_flag.get(core, False):
                    # Nuclear: expansion toward pyra
                    d_exp, d_tec, d_con = 0.58, 0.25, 0.17
                else:
                    # Generic maintenance stress: moderately expansionist
                    d_exp, d_tec, d_con = 0.45, 0.30, 0.25

                w = _clamp(rp * p.desperation_weight, 0.0, 1.0)
                exp_s = (1.0 - w) * exp_s + w * d_exp
                tec_s = (1.0 - w) * tec_s + w * d_tec
                con_s = (1.0 - w) * con_s + w * d_con

                # Desperation mode (rp > 0.3): military spike, burn reserves
                if rp > 0.3:
                    exp_s = min(0.85, exp_s * 1.35)
                    t = exp_s + tec_s + con_s
                    exp_s /= t; tec_s /= t; con_s /= t
                    desperation_log.append({
                        "core": core, "tick": tick, "year": year,
                        "resource_pressure": rp,
                        "food_deficit": food_deficit_flag.get(core, False),
                        "ind_deficit":  ind_deficit_flag.get(core, False),
                        "nuc_deficit":  nuc_deficit_flag.get(core, False),
                    })

                # Final renorm after desperation adjustment
                t = exp_s + tec_s + con_s
                exp_s /= t; tec_s /= t; con_s /= t

            # Desperate polities mobilise beyond normal surplus (burn reserves)
            budget_mult = 1.0 + _clamp(rp - 0.3, 0.0, 0.7) * 0.8 if rp > 0.3 else 1.0
            budget = (energy_surplus[core] + core_pop[core] * 0.002) * budget_mult
            exp_budget[core]    = budget * exp_s
            tech_bgt[core]      = budget * tec_s
            consol_budget[core] = budget * con_s

        # ──────────────────────────────────────────────────────────────
        # STAGE 2b: Culture-space drift (§10 energy-budget closed loop)
        # Each polity core's position drifts ~0.01–0.02 per tick
        # ──────────────────────────────────────────────────────────────
        for core in cores:
            ci, io = cpos[core]
            exp_s, tec_s, con_s = _shares_from_pos(cpos[core])
            er = energy_ratio[core]

            # Prosperity erodes coordination pressure → Individual
            surplus_ratio = _clamp(er / 1.5, 0.0, 1.0)
            ci += surplus_ratio * (1.0 - con_s) * p.culture_drift_rate

            # Crisis demands coordination → Collective
            threat_level = _clamp(1.0 - er, 0.0, 1.0)
            ci -= threat_level * p.culture_drift_rate

            # Tech research × trade integration → Outward
            trade_int = min(1.0, len(contact_set[core]) / max(1.0, N * 0.3))
            io += tec_s * trade_int * p.culture_drift_rate

            # Resource stress → Inward (defensive retrenchment)
            io -= _clamp(1.0 - er, 0.0, 1.0) * p.culture_drift_rate * 0.5

            # Fisheries culture-drift vectors (FISHERIES_REFERENCE.md)
            fish_r = substrate[core]["climate"].get("fisheries_richness", 0.0)
            if fish_r > 0.05:
                mt  = substrate[core]["climate"].get("mean_temp", 18.0)
                up  = substrate[core]["climate"].get("upwelling", 0.0)
                fdr = p.culture_drift_rate * fish_r * 0.3  # scale by local richness
                # Cold water → sthaq (Collective push) + bakala (Individual+Inward)
                if mt < 14.0:
                    ci -= fdr * 0.6   # sthaq: communal seasonal harvest
                    io -= fdr * 0.2   # bakala: merchant-oligarch inward accumulation
                # High upwelling → saak oil (Outward push regardless of axis 0)
                if up > 0.3:
                    io += fdr * 0.8
                # Warm water → tunnu (Individual+Outward)
                if mt > 20.0:
                    ci += fdr * 0.4
                    io += fdr * 0.4
                # Universal coastal: kauri slight Collective push
                ci -= fdr * 0.1

            cpos[core] = [_clamp(ci, -1.0, 1.0), _clamp(io, -1.0, 1.0)]

        # ──────────────────────────────────────────────────────────────
        # STAGE 2c: Piety drift (Norris-Inglehart 2004; Weber 1905)
        # crisis→fervor, prosperity→secular; high tech→secular (existential security)
        # Collective reinforces piety (Durkheim solidarity mechanism).
        # ──────────────────────────────────────────────────────────────
        for core in cores:
            pi     = piety[core]
            dRate  = p.piety_drift_rate
            er     = energy_ratio.get(core, 1.0)
            ci, _  = cpos[core]
            # Crisis → piety rises (Norris-Inglehart: existential insecurity → religion)
            if er < 0.6:
                pi += dRate * (0.6 - er) * 2.5
            else:
                pi -= dRate * min(0.4, er - 0.6) * 0.8
            # Collective culture reinforces piety; Individual erodes it (Weber)
            pi -= ci * dRate * 0.6
            # High tech → secular transition (mediated by prosperity, compressed here)
            if tech[core] > 7.0:
                pi -= dRate * (tech[core] - 7.0) * 0.25
            # Trade diversity → cosmopolitan erosion of piety (contact with Other)
            contact_div = min(1.0, len(contact_set[core]) / max(1.0, N * 0.25))
            pi -= dRate * contact_div * 0.3
            piety[core] = _clamp(pi, 0.05, 0.95)
            # Piety feeds back into culture: high piety → Collective/Inward pull
            if piety[core] > 0.5:
                piety_pull = (piety[core] - 0.5) * dRate * 0.4
                ci2, io2 = cpos[core]
                cpos[core] = [_clamp(ci2 - piety_pull, -1.0, 1.0),
                               _clamp(io2 - piety_pull * 0.5, -1.0, 1.0)]

        # ──────────────────────────────────────────────────────────────
        # STAGE 2d: Schism pressure (Grzymala-Busse 2023; Reformation model)
        # High piety + low-sovereignty peripheral holdings + pre-industrial tech
        # → fragmentation risk. "Tilly Goes to Church" mechanism: religious
        # intensity produces state formation divergence in weak-sovereignty periphery.
        # ──────────────────────────────────────────────────────────────
        for core in cores:
            pi = piety[core]
            if pi < 0.60:
                schism_pressure[core] = max(0.0, schism_pressure[core] - 0.02)
                continue
            controlled_arches = [j for j in range(N) if controller[j] == core and j != core]
            if not controlled_arches:
                continue
            low_sov = [j for j in controlled_arches if sovereignty[j] < 0.45]
            low_sov_frac = len(low_sov) / max(1, len(controlled_arches))
            # Tech damping: schism dissolves above industrial threshold
            t_damp = _clamp((7.0 - tech[core]) / 4.0, 0.0, 1.0)
            dp = (pi - 0.60) * low_sov_frac * 3.0 * t_damp
            schism_pressure[core] = _clamp(schism_pressure[core] + dp, 0.0, 1.5)
            # Schism fires at pressure > 1.0: peripheral holdings break away
            if schism_pressure[core] > 1.0 and low_sov:
                low_sov_sorted = sorted(low_sov, key=lambda j: sovereignty[j])
                n_release = max(1, len(low_sov_sorted) // 3)
                released = 0
                reformed_count = 0
                for j in low_sov_sorted[:n_release]:
                    # Transfer to nearest independent arch or make ungoverned
                    nearest_other = None
                    nearest_dist  = float("inf")
                    for other in range(N):
                        if controller[other] == other and other != core:
                            d = _gc_dist_arch(archs[j], archs[other])
                            if d < nearest_dist:
                                nearest_dist = d
                                nearest_other = other
                    if nearest_other is not None and nearest_dist < 0.8:
                        controller[j] = nearest_other
                        sovereignty[j] = 0.08
                    else:
                        controller[j] = j   # ungoverned
                        sovereignty[j] = 0.04
                        # ── Doctrinal innovation: Reformed culture shift ───────────────
                        # Weber (1904): Reformation heterodoxy correlates with Protestant
                        # ethic — individualist, outward-facing, market-compatible culture.
                        # Breaking from collective/hierarchical religious authority creates
                        # impetus toward individualist orientation (creative destruction,
                        # Protestant work ethic, priesthood of all believers).
                        # Source: Weber, M. (1904). *The Protestant Ethic and the Spirit
                        #         of Capitalism*. Routledge.
                        #         Grzymala-Busse (2023): religious fragmentation and state
                        #         capacity building outside imperial control.
                        old_ci, old_io = cpos[j]
                        # Reformed: push toward individualist (+CI) and slightly outward (+IO)
                        reform_ci = _clamp(old_ci + 0.30, -1.0, 1.0)
                        reform_io = _clamp(old_io + 0.15, -1.0, 1.0)
                        cpos[j] = [reform_ci, reform_io]
                        # Also reduce piety (schism breaks the prior religious structure)
                        piety[j] = max(0.05, piety[j] * 0.60)
                        reformed_count += 1
                    released += 1
                schism_pressure[core] = 0.0
                if released > 0:
                    schism_log.append({"tick": tick, "year": year,
                                       "core": core, "count": released,
                                       "reformed": reformed_count})

        # ──────────────────────────────────────────────────────────────
        # STAGE 3: Rumor propagation (plan §5.4)
        # Trade contacts require tech >= 2 (agricultural surplus for trade)
        # Max 1 new contact per polity per tick (takes a generation)
        # ──────────────────────────────────────────────────────────────
        for core in cores:
            if tech[core] < 1.5:
                continue  # subsistence: no trade network

            ctrl_set = set(_controlled(core))
            new_this_tick = 0
            max_new = 1 if tech[core] < 5.0 else 2
            for j in ctrl_set:
                if new_this_tick >= max_new: break
                for nb in adj[j]:
                    if nb not in ctrl_set:
                        other_core = controller[nb]
                        if other_core != core and other_core not in contact_set[core]:
                            contact_set[core].add(other_core)
                            contact_set[other_core].add(core)
                            # Record per-pair relay contact age for endemicity transition
                            # (McNeill 1976: relay-trade contact before formal absorption
                            #  builds partial pathogen immunity in the contacted population)
                            relay_contact_since[(core, other_core)] = tick
                            relay_contact_since[(other_core, core)] = tick
                            new_this_tick += 1
                            if new_this_tick >= max_new: break

            # Industrial+ signals detectable at range
            if tech[core] >= 7.0:
                signal_r = p.df_detection_range * (tech[core] / 10.0)
                for other in cores:
                    if other == core: continue
                    dist = _gc_dist_arch(archs[core], archs[other])
                    if dist <= signal_r:
                        awareness[(other, core)] = min(1.0, awareness.get((other, core), 0.0) + 0.15)
                        awareness[(core, other)] = min(1.0, awareness.get((core, other), 0.0) + 0.10)
            # Nuclear peer detection: once both polities are nuclear-capable,
            # awareness accumulates globally regardless of distance.
            # Represents weapons-test seismology, satellite surveillance, signals intel.
            # Rate: 0.04/tick → threshold 0.30 fires after ~7–8 ticks (350–400 years).
            if tech[core] >= 9.0:
                for other in cores:
                    if other == core: continue
                    if tech[other] >= 9.0:
                        awareness[(other, core)] = min(1.0, awareness.get((other, core), 0.0) + 0.04)
                        awareness[(core, other)] = min(1.0, awareness.get((core, other), 0.0) + 0.04)

        # ──────────────────────────────────────────────────────────────
        # STAGE 4: Bayesian belief update (plan §5.5)
        # Nuclear intercept → Dark Forest break
        # ──────────────────────────────────────────────────────────────
        if df_year is None:
            for core in cores:
                if tech[core] < 9.0: continue
                for other in cores:
                    if other == core or tech[other] < 8.0: continue
                    aw = awareness.get((core, other), 0.0)
                    # DF triggers when two nuclear-capable polities detect each other.
                    # Territory gate: both polities must control a significant fraction
                    # of the world — only major powers develop intercontinental
                    # surveillance / early-warning networks.
                    min_archs = max(1, int(p.df_min_territory_frac * N))
                    if core_n_ctrl[core] < min_archs or core_n_ctrl[other] < min_archs:
                        continue
                    # Nuclear peer pair (both ≥9.0): no distance gate — global awareness.
                    # Pre-nuclear rival (8.0–9.0): proximity gate still applies.
                    if tech[other] >= 9.0:
                        if aw > 0.30:
                            df_year = year
                            df_arch = core
                            df_detector = other
                            awareness[(core, other)] = 1.0
                            awareness[(other, core)] = 1.0
                            break
                    else:
                        dist = _gc_dist_arch(archs[core], archs[other])
                        if dist <= p.df_detection_range * 1.5 and aw > 0.2:
                            df_year = year
                            df_arch = core
                            df_detector = other
                            awareness[(core, other)] = 1.0
                            awareness[(other, core)] = 1.0
                            break
                if df_year is not None:
                    break
        # Record hegemon pair once on first DF fire
        if df_year is not None and df_hegemon_pair is None:
            df_hegemon_pair = [df_arch, df_detector]

        # ──────────────────────────────────────────────────────────────
        # STAGE 4.5: Walt balance-of-threat alignment update (post-DF)
        # Non-hegemon polities drift their alignment toward whichever
        # hegemon poses less threat.  Threat = tech × (1+extractiveness)
        # × fleet_scale / distance  (Walt 1987, Origins of Alliances).
        # ──────────────────────────────────────────────────────────────
        if df_hegemon_pair is not None:
            h_a, h_b = df_hegemon_pair
            # fleet_scale is finalized post-sim; approximate it intra-sim using
            # pyra availability (pu_dependent_factor vs full scale).
            def _runtime_fleet(h):
                return 1.0 if _has_pu(h) else p.pu_dependent_factor
            fs_a = _runtime_fleet(h_a)
            fs_b = _runtime_fleet(h_b)
            for core in cores:
                if core in (h_a, h_b):
                    continue  # hegemons do not align
                dist_a = max(_gc_dist_arch(archs[core], archs[h_a]), 0.05)
                dist_b = max(_gc_dist_arch(archs[core], archs[h_b]), 0.05)
                threat_a = tech[h_a] * (1.0 + extractiveness[h_a]) * fs_a / dist_a
                threat_b = tech[h_b] * (1.0 + extractiveness[h_b]) * fs_b / dist_b
                denom = max(threat_a + threat_b, 0.001)
                # positive net_threat → h_a more threatening → align toward h_b (positive)
                net_threat = (threat_a - threat_b) / denom
                alignment[core] += (net_threat - alignment[core]) * p.alliance_formation_rate
                alignment[core] = _clamp(alignment[core], -1.0, 1.0)

        # ──────────────────────────────────────────────────────────────
        # STAGE 5: Solow-Romer production + tech growth (plan §5.2, §5.8)
        # delta_tech = A₀ × yield × contact_mult × energy_mult × tech_accel × share_mult × 0.001
        # Tech accelerates with: more contacts, energy surplus, existing tech level
        # ──────────────────────────────────────────────────────────────
        for core in cores:
            a0        = _A0_from_pos(cpos[core])
            nc        = len(contact_set[core])
            tp        = max(1.0, core_pop[core])
            er        = energy_ratio[core]
            crop_y    = substrate[core]["crops"]["primary_yield"]

            # ── Sachs-Warner resource curse (Ross 2012; Vitalis 2018) ────────
            # Naphtha-rich polities in the industrial era develop extractive
            # institutions that reduce broad-based innovation (TFP penalty).
            # Mechanism: high resource rents → elite extraction rather than
            # investment in human capital or institutional capacity.
            # Fires when polity holds > ~13% of world C stock, tech 6–9.5.
            if 6.0 < tech[core] < 9.5:
                total_c_init_sum = sum(c_initial)
                polity_c_frac = (sum(c_initial[j] for j in range(N) if controller[j] == core)
                                 / max(0.001, total_c_init_sum))
                curse = _clamp(polity_c_frac * 3.0 - 0.4, 0.0, 0.5)
                a0 *= (1.0 - curse * p.resource_curse_strength)

            # ── Acemoglu-Robinson institutional stagnation ───────────────────
            # Extractive institutions — formed through concentrated surplus
            # extraction from periphery under low-individualism culture — block
            # creative destruction by protecting elite rents against competitive
            # entry. Effect: TFP penalty proportional to extractiveness index,
            # independent of naphtha (can form from any extraction surplus).
            # Source: Acemoglu & Robinson (2012). *Why Nations Fail*. Crown.
            #         Acemoglu, Johnson & Robinson (2001). AER 91(5).
            a0 *= (1.0 - extractiveness[core] * p.extractiveness_tfp_penalty)

            # ── Pyra / military-industrial complex resource curse ─────────────
            # Polities monopolising Pu access in the nuclear era develop a
            # different form of resource curse: military-industrial rents crowd
            # out civilian innovation.  Analogous to Ross (2012) oil curse, but
            # applied to strategic minerals rather than energy commodities.
            # Note: this is distinct from the naphtha curse — it fires at tech >= 8.5
            # (nuclear era) rather than 6–9.5 (industrial era).
            if tech[core] >= 8.5:
                pu_islands = sum(1 for j in range(N)
                                 if controller[j] == core and substrate[j]["minerals"].get("Pu"))
                total_pu_islands = sum(1 for j in range(N) if substrate[j]["minerals"].get("Pu"))
                if total_pu_islands > 0:
                    pu_frac = pu_islands / total_pu_islands
                    mic_curse = _clamp(pu_frac * 2.5 - 0.5, 0.0, 0.4)
                    a0 *= (1.0 - mic_curse * p.resource_curse_strength * 0.6)  # 60% of naphtha curse strength

            # Pu dependency at nuclear era
            if tech[core] >= 9.0 and not _has_pu(core):
                er *= p.pu_dependent_factor

            # Solow-Romer tech growth (plan §5.8)
            # Two-component model:
            #   floor: steady background progress (crop-dependent, culture-independent)
            #   accel: institutional acceleration (a0, share, contacts, energy)
            # Calibrated: civic ~10 at story present, parochial ~3, subject ~9
            eff_nc       = min(nc, int(tech[core] * 2) + 1)
            contact_mult = 1.0 + _log2(eff_nc + 1) * 0.3
            energy_mult  = er * p.energy_to_tfp
            share_mult   = _shares_from_pos(cpos[core])[1] / 0.3

            # Floor: everyone progresses slowly (neolithic → bronze → iron)
            crop_exp     = crop_y ** 0.3
            base_floor   = crop_exp * 0.003

            # Accelerator: culture-dependent, kicks in with contacts and tech
            t = tech[core]
            if t < 1.5:
                accel_rate = 0.0
            elif t < 3.0:
                accel_rate = 0.002
            elif t < 5.0:
                accel_rate = 0.008
            elif t < 7.0:
                accel_rate = 0.025
            else:
                accel_rate = 0.120   # industrial (C energy)

            accel = a0 * crop_exp * share_mult * accel_rate * contact_mult * energy_mult

            delta = base_floor + accel

            # Diminishing returns near tech cap (soft ceiling at ~11)
            if t > 9.0:
                delta *= _clamp((11.0 - t) / 2.0, 0.0, 1.0)
            tech[core] += delta

            # Post-DF arms race: all nuclear polities (tech > 8.5) get extra tech investment
            # Models deterrence infrastructure, delivery systems, second-strike capability
            if df_year is not None and tech[core] > 8.5:
                arms_bonus = min(0.05, delta * 0.4)
                tech[core] += arms_bonus

            # — §11 Tech decay: maintenance shortfall slides tech downward —
            # maintenance = tech² × maintenance_rate (quadratic: high-tech is fragile)
            # if energy_surplus < maintenance → tech erodes
            maintenance_cost = tech[core] * tech[core] * p.maintenance_rate
            avail_e = energy_surplus[core]
            if avail_e < maintenance_cost:
                shortfall = maintenance_cost - avail_e
                decay_amt = shortfall * p.decay_rate
                old_t = tech[core]
                tech[core] = max(0.1, tech[core] - decay_amt)
                if decay_amt > 0.005:  # log non-trivial decay events
                    tech_decay_log.append({
                        "core": core, "tick": tick, "year": year,
                        "tech_before": round(old_t, 3),
                        "tech_after":  round(tech[core], 3),
                        "decay":       round(decay_amt, 4),
                        "shortfall":   round(shortfall, 4),
                        "resource_pressure": round(resource_pressure.get(core, 0.0), 3),
                    })

            # Knowledge accumulation
            knowledge[core] += delta * a0 * 0.5

            # Population: logistic growth gated by energy
            for j in range(N):
                if controller[j] != core: continue
                cap = carry_cap[j]
                if tech[core] >= 7.0 and c_remaining[j] > 0:
                    cap *= (1.0 + er * 0.5)
                if tech[core] >= 9.0:
                    cap *= 1.5
                # Malaria carrying-capacity penalty (McNeill 1976; Gallup & Sachs 2001)
                # Reduces effective cap in tropical belt (abs_lat < 20°).
                # Resolves at tech ≥ 6 (germ-theory / vector-control analogue).
                m_sev = malaria_factor[j]
                if m_sev > 0:
                    m_penalty = m_sev * p.malaria_cap_penalty * (0.30 if tech[core] >= 6.0 else 1.0)
                    cap *= max(0.1, 1.0 - m_penalty)
                growth_rate = 0.03 * er * (1.0 - pop[j] / max(1.0, cap))
                pop[j] *= (1.0 + _clamp(growth_rate, -0.05, 0.10))
                pop[j] = max(1.0, pop[j])

            # Propagate tech to periphery
            for j in range(N):
                if controller[j] == core and j != core:
                    tech[j] = max(tech[j], tech[core] * 0.7)

        # Knowledge diffusion: lagging polities catch up from contacts
        core_set = set(cores)
        world_max_tech = max(tech[c] for c in cores)
        for core in cores:
            # Contact-based catch-up (direct trade/exchange)
            max_contact_tech = max((tech[c] for c in contact_set[core]
                                    if c in core_set), default=0.0)
            if max_contact_tech > tech[core] + 1.0:
                gap = max_contact_tech - tech[core]
                tech[core] += gap * 0.08

            # Global diffusion (rumors, observation, espionage)
            if world_max_tech > tech[core] + 1.0:
                gap = world_max_tech - tech[core]
                tech[core] += gap * 0.03

        # ──────────────────────────────────────────────────────────────
        # STAGE 5b: Epidemic waves (McNeill 1976; Schmid et al. 2015)
        # Periodic disease events propagating through trade contact networks.
        # Trade hubs as amplifiers (Black Death / Silk Road model): port density
        # drives origin probability; spread follows contact graph.
        # Separate from first-contact virgin-soil epidemics (Stage 6).
        # ──────────────────────────────────────────────────────────────
        for core in cores:
            nc = len(contact_set[core])
            if nc < 2: continue  # isolated polities don't originate waves
            total_cap = sum(carry_cap[j] for j in range(N) if controller[j] == core)
            total_pol_pop = sum(pop[j] for j in range(N) if controller[j] == core)
            density = total_pol_pop / max(1.0, total_cap)
            # Urban disease sink: Davenport 2020 — cities as net mortality zones
            urban_factor = max(0.3, density)
            epi_prob = p.epi_base_severity * 0.015 * (1.0 + nc * 0.2) * urban_factor
            if rng.next_float() < epi_prob:
                mortality = 0.04 + rng.next_float() * 0.12  # 4–16% pop loss
                affected = {core}
                for other in contact_set[core]:
                    if other in set(cores) and rng.next_float() < 0.35:
                        affected.add(other)
                for c in affected:
                    for j in range(N):
                        if controller[j] == c:
                            pop[j] = max(1.0, pop[j] * (1.0 - mortality))
                wave_epi_log.append({"tick": tick, "year": year, "source": core,
                                     "mortality_rate": mortality,
                                     "affected": list(affected)})

        # ──────────────────────────────────────────────────────────────
        # STAGE 6: Thompson Sampling expansion (plan §5.7)
        # ──────────────────────────────────────────────────────────────
        for core in cores:
            budget = exp_budget.get(core, 0.0)
            if budget < 0.1: continue
            if tech[core] < 2.0: continue  # need bronze-age institutions to project power

            ts_a, ts_b = _ts_priors_from_pos(cpos[core])

            # Build frontier
            ctrl_set = set(_controlled(core))
            frontier = set()
            for j in ctrl_set:
                for nb in adj[j]:
                    if nb not in ctrl_set:
                        frontier.add(nb)

            if not frontier: continue

            # Score candidates
            candidates = []
            for target in frontier:
                dist = _gc_dist_arch(archs[core], archs[target])
                ts_score = _beta_sample(rng, ts_a, ts_b)

                # Resource targeting
                rv = _resource_value(substrate[target]["minerals"], tech[core], p.cu_unlock_tech)

                # Track scramble onset
                if tech[core] >= 7.0 and substrate[target]["minerals"].get("C", 0.0) > 0:
                    if scramble_onset is None:
                        scramble_onset = tick
                if tech[core] >= 9.0 and substrate[target]["minerals"].get("Pu"):
                    if pu_scramble_onset is None:
                        pu_scramble_onset = tick

                # — §11 Desperation targeting: deficit drives resource-specific expansion —
                desp_bonus = 0.0
                rp = resource_pressure.get(core, 0.0)
                if rp > 0.0:
                    t_mins    = substrate[target]["minerals"]
                    t_crops   = substrate[target]["crops"]
                    t_climate = substrate[target]["climate"]
                    # Food deficit → fertile islands and fish-rich archipelagos
                    if food_deficit_flag.get(core, False):
                        desp_bonus += rp * (t_crops.get("primary_yield", 0.0) * 1.5
                                            + t_climate.get("fisheries_richness", 0.0) * 2.5)
                    # Industrial deficit → naphtha-bearing islands
                    if ind_deficit_flag.get(core, False):
                        desp_bonus += rp * t_mins.get("C", 0.0) * 4.0
                    # Nuclear deficit → pyra islands
                    if nuc_deficit_flag.get(core, False) and t_mins.get("Pu"):
                        desp_bonus += rp * 6.0
                    # Desperation mode distance penalty softens: desperate polities reach farther
                    if rp > 0.3:
                        dist *= _clamp(1.0 - (rp - 0.3) * 0.5, 0.5, 1.0)

                # Post-DF deterrence: nuclear peers strongly avoid each other's territory
                deterrence_penalty = 0.0
                proxy_bonus = 0.0
                if df_year is not None:
                    target_ctrl = controller[target]
                    if tech[core] >= 9.0 and tech[target_ctrl] >= 9.0 and core != target_ctrl:
                        deterrence_penalty = 12.0  # hegemons frozen against each other
                    elif tech[core] >= 9.0 and tech[target_ctrl] < 9.0:
                        # ── Stability-instability paradox (Snyder 1965; Waltz 1981) ──
                        # Nuclear deterrence stabilizes direct inter-hegemon conflict
                        # but paradoxically ENABLES proxy warfare: hegemons compete
                        # aggressively in the sub-nuclear periphery.
                        # Bonus for targeting rival hegemon's client/tributary states.
                        for other_h in [c for c in cores if c != core and tech[c] >= 9.0]:
                            if target_ctrl in contact_set[other_h]:
                                proxy_bonus = 3.0
                                break

                # ── Piety missionary bonus (Grzymala-Busse 2023 centripetal force) ──
                # High-piety polities receive expansion bonus representing missionary
                # drive, religious legitimation of conquest, and cultural absorption.
                piety_bonus = 0.0
                c_piety = piety[core]
                if c_piety > 0.65:
                    piety_bonus = (c_piety - 0.65) * 2.0
                    if tech[core] - tech[controller[target]] > 1.5:
                        piety_bonus += (c_piety - 0.65) * 1.5

                # ── Walt balance-of-threat: alliance protection ──────────────────
                # Polities aligned toward a hegemon gain resistance against the
                # other hegemon's expansion attempts. Resistance ∝ alignment strength.
                # (Walt 1987: states balance against threats, not just power.)
                alliance_penalty = 0.0
                if df_hegemon_pair is not None:
                    h_a, h_b = df_hegemon_pair
                    t_align = alignment[controller[target]]  # alignment of target's polity
                    if core == h_a and t_align > 0:
                        # h_a attacking a polity aligned toward h_b → resistance
                        alliance_penalty = t_align * p.alliance_protection_str
                    elif core == h_b and t_align < 0:
                        # h_b attacking a polity aligned toward h_a → resistance
                        alliance_penalty = (-t_align) * p.alliance_protection_str

                score = (ts_score + p.resource_targeting_weight * rv + desp_bonus
                         + piety_bonus + proxy_bonus - dist * 1.5
                         - deterrence_penalty - alliance_penalty)
                candidates.append((score, target, dist, proxy_bonus > 0))

            candidates.sort(key=lambda x: -x[0])

            absorbed_this_tick = 0
            for score, target, dist, is_proxy in candidates:
                if budget < 0.1 or absorbed_this_tick >= 1: break

                # Absorption cost: scales with distance² and target pop
                # tech_adv^1.5 rewards tech-advanced polities exponentially
                tech_adv = max(0.1, tech[core] - tech[target] + 1.0)
                cost = (pop[target] * 0.05 + dist * dist * dist * 40.0) / (tech_adv ** 1.5)

                # Conquering controlled territory is much harder (garrison defense)
                target_core = controller[target]
                if target_core != target:
                    cost *= 3.0
                    # Can't conquer a near-peer polity's territory
                    if tech[core] - tech[target_core] < 2.0:
                        continue

                if cost > budget: continue
                if pop[target] > core_pop[core] * 0.5 and tech[core] - tech[target] < 2.0:
                    continue  # can't absorb near-peer

                # ── Epidemiological shock at first contact ─────────────────────
                # Diamond (1997): severity scaled by crop distance (pathogen divergence
                # proxy). Crop zones differ in endemic pathogen exposure — tropical/
                # temperate isolation determines naive-population mortality.
                # Endemicity transition (McNeill 1976): prior relay-trade contact
                # provides partial immunological exposure, reducing virgin-soil severity.
                if first_contact_tick[target] is None:
                    first_contact_tick[target] = tick
                    cc = substrate[core]["crops"]["primary_crop"]
                    ct = substrate[target]["crops"]["primary_crop"]
                    cdist = _crop_distance(cc, ct)
                    sev = p.epi_base_severity + rng.next_float() * 0.15
                    # ── Endemicity transition (McNeill 1976): per-pair relay-trade contact
                    # age determines immunity before formal political absorption.
                    # Fixed: now uses per-pair contact duration (time since core and target
                    # first appeared in each other's contact_set via relay trade) rather
                    # than global count.  0.04/tick → max 0.6 immunity after 15 ticks (~750 yr).
                    relay_ticks = tick - relay_contact_since.get((core, target), tick)
                    immunity = _clamp(relay_ticks * 0.04, 0.0, 0.6)
                    mort = sev * cdist * (1.0 - immunity)
                    pop[target] *= (1.0 - mort)
                    epi_log.append({"arch": target, "contactor": core,
                                    "mortality_rate": mort, "tick": tick, "year": year,
                                    "immunity_factor": immunity,
                                    "relay_contact_age": relay_ticks})

                # Transfer all archs controlled by target to core
                # AJR reversal-of-fortune: record pre-colonial state at first absorption
                if target not in pre_colonial_state:
                    pre_colonial_state[target] = {
                        "tick": tick, "pop": pop[target], "tech": tech[target]
                    }
                for j in range(N):
                    if controller[j] == target:
                        controller[j] = core
                        # Also record sub-islands under target if not yet tracked
                        if j != target and j not in pre_colonial_state:
                            pre_colonial_state[j] = {
                                "tick": tick, "pop": pop[j], "tech": tech[j]
                            }
                controller[target] = core
                absorbed_tick[target] = tick
                sovereignty[target] = _clamp(0.15 + dist * 0.3, 0.10, 0.50)
                budget -= cost
                absorbed_this_tick += 1

                # ── Proxy war casualties (Snyder 1965; Kahn 1965) ──────────────────
                # In the nuclear era, DF-era expansion into a rival's periphery
                # constitutes a proxy conflict. Population losses are proportional to
                # the target's defensive capacity (lower tech gap = harder resistance)
                # and the base casualty rate.  Models: Korean/Vietnam/Angola patterns.
                if is_proxy:
                    # target_core captured before absorption: original controller
                    prev_ctrl_tech = tech[target_core] if target_core < N else tech[target]
                    tech_gap = max(0.1, tech[core] - prev_ctrl_tech)
                    # Stiffer resistance when tech gap is small (near-peer proxy)
                    resistance_factor = _clamp(1.0 - (tech_gap - 0.5) * 0.3, 0.3, 1.0)
                    casualty_rate = p.proxy_war_casualty_rate * resistance_factor
                    pop_before = pop[target]
                    pop[target] = max(1.0, pop[target] * (1.0 - casualty_rate))
                    proxy_war_log.append({
                        "aggressor": core, "target": target, "tick": tick, "year": year,
                        "casualty_rate": casualty_rate, "pop_lost": pop_before - pop[target],
                    })

                # Inherit target's contacts
                for c in contact_set[target]:
                    if c != core:
                        contact_set[core].add(c)

                # Blend absorbed polity's culture position into core (5% pull)
                t_ci, t_io = cpos[target]
                cpos[core][0] = _clamp(cpos[core][0] * 0.95 + t_ci * 0.05, -1.0, 1.0)
                cpos[core][1] = _clamp(cpos[core][1] * 0.95 + t_io * 0.05, -1.0, 1.0)

                expansion_log.append({
                    "core": core, "target": target, "tick": tick, "year": year,
                    "tech_gap": tech[core] - tech[target],
                    "resource_driven": rv > 0,
                })

        # ──────────────────────────────────────────────────────────────
        # STAGE 7: Sovereignty drift (plan §5.9)
        # ──────────────────────────────────────────────────────────────
        for i in range(N):
            if controller[i] == i: continue
            core = controller[i]
            dist = _gc_dist_arch(archs[core], archs[i])

            extraction = p.sov_extraction_decay / max(0.1, dist)
            extraction *= _clamp(energy_ratio.get(core, 1.0), 0.0, 1.5)

            # ── Piety absorption bonus (centripetal force — Grzymala-Busse 2023) ──
            # High-piety empires integrate conquered populations faster through
            # religious legitimation, missionary administration, and cultural absorption.
            core_piety = piety[core]
            if core_piety > 0.5:
                extraction *= (1.0 + (core_piety - 0.5) * p.piety_absorption_bonus)

            # ── Scott's resistance mechanic (Scott 1985, 1990) ────────────────
            # "Weapons of the Weak": colonial extraction above tolerable threshold
            # generates grievance that accelerates sovereignty recovery.
            # Colonialism is self-limiting: extraction creates the consciousness
            # that makes resistance possible (mediated through participation axis).
            tolerable = p.sov_extraction_decay * 0.5
            excess_extraction = max(0.0, extraction - tolerable)
            grievance[i] = _clamp(
                grievance[i] * 0.95 + excess_extraction * p.grievance_buildup_rate,
                0.0, 1.0
            )
            resistance_mult = 1.0 + grievance[i] * p.grievance_resistance_mult

            recovery = (p.sov_extraction_decay * sovereignty[i]
                        * (pop[i] / max(1.0, pop[core])) * 0.5 * resistance_mult)

            sovereignty[i] += (recovery - extraction) * 0.1
            sovereignty[i] = _clamp(sovereignty[i], 0.05, 0.95)

            # ── Acemoglu-Robinson institutional buildup ────────────────────────
            # Extractive institutions crystallise from the practice of extraction.
            # Pressure is proportional to: how much extraction is occurring ×
            # how collectivist/inward the imperial culture is (low individualism
            # = no incentive to extend property rights to subjects).
            # The index decays slowly (sticky institutions), but inclusive
            # reforms (high individualism × low extraction) drive faster decay.
            ci_core, io_core = cpos[core]  # individualism [0..1], outwardness [0..1]
            inclusive_culture = ci_core * 0.7 + io_core * 0.3   # civic/outward → more inclusive
            extractive_pressure = excess_extraction * (1.0 - inclusive_culture) * p.institutional_lock_rate
            inclusive_reform    = inclusive_culture * 0.02       # slow institutional liberalisation
            extractiveness[core] = _clamp(
                extractiveness[core] * (1.0 - inclusive_reform) + extractive_pressure,
                0.0, 1.0
            )

            # Post-nuclear decolonisation recovery
            if tech[core] >= 9.0 and year >= -200:
                sovereignty[i] = min(0.80, sovereignty[i] + 0.015)

        # ──────────────────────────────────────────────────────────────
        # STAGE 8: Substrate drift — C depletion (plan §5.10)
        # ──────────────────────────────────────────────────────────────
        for i in range(N):
            core = controller[i]
            if tech[core] >= 7.0 and c_remaining[i] > 0:
                # C depletion: pop × tech × depletion_rate
                extraction = pop[i] * tech[core] * p.naphtha_depletion * 0.0005
                c_remaining[i] = max(0.0, c_remaining[i] - extraction)

        # ── Snapshots ─────────────────────────────────────────────────
        if year == -5000:
            tech_snapshots["after_antiquity"] = list(tech)
            pop_snapshots["after_antiquity"]  = list(pop)
        elif year == -2000:
            tech_snapshots["after_serial"] = list(tech)
            pop_snapshots["after_serial"]  = list(pop)
        elif year == -500:
            tech_snapshots["after_colonial"] = list(tech)
            pop_snapshots["after_colonial"]  = list(pop)
        elif year == -200:
            tech_snapshots["after_industrial"] = list(tech)
            pop_snapshots["after_industrial"]  = list(pop)

    # ── POST-SIM: Pu logic + fleet_scale (plan §6) ───────────────────────
    final_cores = sorted(set(controller))
    for core in final_cores:
        if tech[core] >= 9.0:
            if _has_pu(core):
                fleet_scale[core] = 1.0
                sovereignty[core] = min(1.0, sovereignty[core] + 0.1)
            else:
                fleet_scale[core] = p.pu_dependent_factor
                sovereignty[core] = max(0.3, sovereignty[core] - 0.05)

    # ── FINAL STATE ───────────────────────────────────────────────────────
    total_world_pop = sum(pop)
    polity_pops = {c: sum(pop[j] for j in range(N) if controller[j] == c) for c in final_cores}

    # Hegemons: >9% total pop
    hegemons = sorted([c for c, pp in polity_pops.items() if pp > total_world_pop * 0.09],
                      key=lambda c: -polity_pops[c])
    hegemon_cultures = {c: _culture_label(c) for c in hegemons}

    uncontacted = sum(1 for i in range(N) if controller[i] == i and i not in hegemons
                      and absorbed_tick[i] is None)

    total_c_init = sum(c_initial)
    total_c_rem  = sum(c_remaining)
    c_depletion_frac = 1.0 - (total_c_rem / total_c_init if total_c_init > 0 else 0.0)

    max_pop = max(pop) if pop else 1.0

    # Build states array
    states = []
    for i in range(N):
        core = controller[i]
        if core == i and i in hegemons:
            faction = _culture_label(i)
            status  = "core"
        elif core in hegemons:
            faction = _culture_label(core)
            if sovereignty[i] < 0.3:   status = "colony"
            elif sovereignty[i] < 0.6: status = "garrison" if _culture_label(core) == "subject" else "client"
            else:                      status = "contacted"
        elif controller[i] == i:
            faction = "independent"
            status  = "uncontacted" if absorbed_tick[i] is None else "independent"
        else:
            faction = _culture_label(core)
            status  = "tributary"

        era = None
        if absorbed_tick[i] is not None:
            cy = START_YEAR + absorbed_tick[i] * TICK_YEARS
            if cy < -2000:   era = "sail"
            elif cy < -500:  era = "colonial"
            elif cy < -200:  era = "industrial"
            else:            era = "nuclear"

        states.append({
            "faction":          faction,
            "status":           status,
            "name":             f"arch_{i}",
            "population":       round(pop[i]),
            "urbanization":     pop[i] / max_pop if max_pop > 0 else 0.0,
            "tech":             round(tech[i] * 10) / 10.0,
            "sovereignty":      round(sovereignty[i], 3),
            "tradeIntegration": min(1.0, len(contact_set[i]) / max(1.0, N * 0.3)),
            "eraOfContact":     era,
            "hopCount":         0,
            "culture":          _culture_label(controller[i]),
            "culture_pos":      list(cpos[controller[i]]),
            "fleet_scale":      fleet_scale[i],
            "c_remaining":      c_remaining[i],
            "controller":       controller[i],
            # Walt alignment of the controlling polity (post-DF only)
            "alignment":        round(alignment[controller[i]], 3),
        })

    # Backward-compat faction labels: map civic→reach, subject→lattice
    reach_arch = lattice_arch = None
    for h in hegemons:
        if _culture_label(h) == "civic" and reach_arch is None:
            reach_arch = h
        elif _culture_label(h) == "subject" and lattice_arch is None:
            lattice_arch = h
    if reach_arch is None and hegemons:
        reach_arch = hegemons[0]
    if lattice_arch is None and len(hegemons) >= 2:
        lattice_arch = hegemons[1]
    elif lattice_arch is None:
        lattice_arch = reach_arch if reach_arch is not None else 0

    # Set faction labels for backward compat with loss.py
    for i in range(N):
        core = controller[i]
        if core == reach_arch or i == reach_arch:
            states[i]["faction"] = "reach"
        elif core == lattice_arch or i == lattice_arch:
            states[i]["faction"] = "lattice"
        elif states[i]["faction"] == "independent":
            states[i]["faction"] = "unknown"

    # Build polities list and polity_members dict (for loss.py interface)
    polities = []
    polity_members = {}
    for core in final_cores:
        members = [j for j in range(N) if controller[j] == core]
        polity_members[core] = members
        polities.append({
            "core":         core,
            "culture_type": _culture_label(core),
            "culture_pos":  list(cpos[core]),
            "total_pop":    polity_pops[core],
            "has_pu":       _has_pu(core),
            "tech":         tech[core],
            "fleet_scale":  fleet_scale[core],
        })
    polities.sort(key=lambda p: -p["total_pop"])

    return {
        "states":               states,
        "log":                  expansion_log,
        "df_year":              df_year,
        "df_arch":              df_arch,
        "df_detector":          df_detector,
        "df_polity_a":          df_arch,       # alias for loss.py
        "df_polity_b":          df_detector,   # alias for loss.py
        "reach_arch":           reach_arch if reach_arch is not None else 0,
        "lattice_arch":         lattice_arch if lattice_arch is not None else 1,
        "epi_log":              epi_log,
        "substrate":            substrate,
        "archs":                archs,
        "plateau_edges":        plateau_edges,
        "minerals":             [substrate[i]["minerals"] for i in range(N)],
        "adj":                  adj,
        "contact_years":        {i: START_YEAR + absorbed_tick[i] * TICK_YEARS
                                 for i in range(N) if absorbed_tick[i] is not None},
        "hop_count":            [0] * N,
        "mineral_access":       [{} for _ in range(N)],
        "tech_snapshots":       tech_snapshots,
        "pop_snapshots":        pop_snapshots,
        "colony_sov_pre_nuclear": {},
        "reach_pu_access":      _has_pu(reach_arch) if reach_arch is not None else False,
        "lattice_pu_access":    _has_pu(lattice_arch) if lattice_arch is not None else False,
        # loss.py interface fields
        "polities":             polities,
        "polity_members":       polity_members,
        "c_total_initial":      total_c_init,
        "c_total_final":        total_c_rem,
        "uncontacted":          uncontacted,
        # v2 diagnostics
        "hegemons":             hegemons,
        "hegemon_cultures":     hegemon_cultures,
        "hegemon_culture_pos":  {c: list(cpos[c]) for c in hegemons},
        "c_depletion_frac":     c_depletion_frac,
        "total_c_initial":      total_c_init,
        "total_c_remaining":    total_c_rem,
        "scramble_onset_tick":  scramble_onset,
        "pu_scramble_onset_tick": pu_scramble_onset,
        "uncontacted_count":    uncontacted,
        "fleet_scales":         {c: fleet_scale[c] for c in hegemons},
        "polity_pops":          polity_pops,
        "n_polities":           len(final_cores),
        # §11 desperation / tech decay diagnostics
        "tech_decay_log":       tech_decay_log,
        "desperation_log":      desperation_log,
        "n_tech_decay_events":  len(tech_decay_log),
        "n_desperation_events": len(desperation_log),
        # Religion / piety (Norris-Inglehart; Grzymala-Busse)
        "piety":                list(piety),
        "schism_log":           schism_log,
        "n_schisms":            len(schism_log),
        "schism_pressure":      list(schism_pressure),
        # Disease (McNeill; Gallup & Sachs)
        "wave_epi_log":         wave_epi_log,
        "malaria_factors":      list(malaria_factor),
        # Trade / resistance diagnostics
        "grievance":            list(grievance),
        # Acemoglu-Robinson institutional diagnostics
        "extractiveness":       list(extractiveness),
        # Proxy war casualties (Snyder/Kahn; stability-instability paradox)
        "proxy_war_log":        proxy_war_log,
        "n_proxy_wars":         len(proxy_war_log),
        # AJR reversal-of-fortune (Acemoglu, Johnson & Robinson 2001)
        # Tracks pre-colonial prosperity (tech/pop at first absorption) vs. final tech rank.
        # reversal_of_fortune_r: Spearman rank correlation in [-1, 1].
        #   Negative = reversal confirmed (formerly prosperous polities now lag).
        #   Positive = no reversal (prosperity advantage persisted through colonization).
        "pre_colonial_state":   pre_colonial_state,
        "reversal_of_fortune_r": _spearman_reversal(pre_colonial_state, tech, N),
        # Walt balance-of-threat alignment (Walt 1987)
        # alignment[i] ∈ [-1, 1]: final alignment of each polity core.
        # Positive = aligned toward df_detector (h_b); negative = toward df_arch (h_a).
        "alignment":            alignment,
        "hegemon_pair":         df_hegemon_pair,
    }


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_seed(seed=216089, world_path=None, params=None, verbose=True):
    if params is None:
        params = DEFAULT_PARAMS
    import os, json as _json
    if world_path:
        path = world_path
    else:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            f"worlds/candidate_{seed:07d}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"No world file for seed {seed}")
    # Use json.load directly (not load_world) so simulate() recomputes substrate
    # via _compute_substrate().  load_world produces an older substrate schema
    # (missing fishery / coast fields) that silently degrades DF timing.
    with open(path) as _f:
        world = _json.load(_f)

    result = simulate(world, params, seed=seed)

    if verbose:
        lines = [f"=== Seed {seed} verification ==="]
        lines.append(f"Hegemons ({len(result['hegemons'])}): {result['hegemons']}")
        for h in result["hegemons"]:
            c   = result["hegemon_cultures"][h]
            pos = result["hegemon_culture_pos"].get(h, [0.0, 0.0])
            s   = result["states"][h]
            lines.append(f"  arch {h}: culture={c} pos=({pos[0]:+.2f},{pos[1]:+.2f}), "
                         f"tech={s['tech']:.1f}, pop={s['population']}, "
                         f"fleet={result['fleet_scales'].get(h, 0):.2f}, "
                         f"crop={substrate_crop(result['substrate'], h)}")
        lines.append(f"C depletion: {result['c_depletion_frac']*100:.1f}%")
        lines.append(f"Uncontacted: {result['uncontacted_count']}")
        lines.append(f"DF year: {result['df_year']}")
        lines.append(f"Scramble onset tick: {result['scramble_onset_tick']} "
                      f"(year {START_YEAR + result['scramble_onset_tick'] * TICK_YEARS if result['scramble_onset_tick'] else 'N/A'})")
        lines.append(f"Pu scramble tick: {result['pu_scramble_onset_tick']}")
        lines.append(f"N polities: {result['n_polities']}")
        lines.append(f"N expansions: {len(result['log'])}")

        # Top polities by tech
        lines.append("\nTop polities by tech:")
        for core in sorted(result["polity_pops"].keys(),
                           key=lambda c: -result["states"][c]["tech"])[:5]:
            s = result["states"][core]
            pp = result["polity_pops"][core]
            pct = pp / sum(result["polity_pops"].values()) * 100
            n_ctrl = sum(1 for st in result["states"] if st["controller"] == core)
            lines.append(f"  arch {core}: culture={s['culture']}, tech={s['tech']:.1f}, "
                         f"pop={pp:.0f} ({pct:.1f}%), ctrl={n_ctrl} archs, "
                         f"crop={substrate_crop(result['substrate'], core)}")

        # Tech distribution at snapshots
        for era_name, snap in result["tech_snapshots"].items():
            avg = sum(snap) / len(snap) if snap else 0
            mx  = max(snap) if snap else 0
            lines.append(f"  {era_name}: avg_tech={avg:.2f}, max_tech={mx:.2f}")

        lines.append("\n--- Verification ---")

        civic_h = [h for h in result["hegemons"] if result["hegemon_cultures"][h] == "civic"]
        subj_h  = [h for h in result["hegemons"] if result["hegemon_cultures"][h] == "subject"]

        if civic_h and subj_h:
            ct = max(result["states"][h]["tech"] for h in civic_h)
            st = max(result["states"][h]["tech"] for h in subj_h)
            lines.append(f"[{'OK' if ct >= st else 'FAIL'}] Civic industrializes first "
                         f"(civic={ct:.1f} vs subject={st:.1f})")
        elif civic_h:
            lines.append(f"[OK] Civic hegemon (tech={result['states'][civic_h[0]]['tech']:.1f}), no Subject")
        else:
            lines.append(f"[FAIL] No Civic hegemon")

        if result["scramble_onset_tick"]:
            sy = START_YEAR + result["scramble_onset_tick"] * TICK_YEARS
            lines.append(f"[{'OK' if sy >= -2000 else 'WARN'}] Naphtha scramble at year {sy}")
        else:
            lines.append("[FAIL] No naphtha scramble")

        nuc = sum(1 for h in result["hegemons"] if result["states"][h]["tech"] >= 9.0)
        lines.append(f"[{'OK' if nuc >= 2 else 'FAIL'}] Nuclear hegemons: {nuc}")

        if result["df_year"] is not None:
            lines.append(f"[{'OK' if -350 <= result['df_year'] <= -40 else 'WARN'}] "
                         f"DF break: year {result['df_year']}")
        else:
            lines.append("[FAIL] No DF break")

        print("\n".join(lines))

    return result


def substrate_crop(substrate, i):
    return substrate[i]["crops"]["primary_crop"] if i < len(substrate) else "?"


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 216089
    verify_seed(seed)
