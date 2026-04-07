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
    # Political Culture (11)
    civic_expansion_share:      float = 0.40
    civic_tech_share:           float = 0.40
    civic_consolidation_share:  float = 0.20
    subject_expansion_share:    float = 0.20
    subject_tech_share:         float = 0.30
    subject_consolidation_share:float = 0.50
    parochial_expansion_share:  float = 0.25
    parochial_tech_share:       float = 0.25
    A0_civic:                   float = 1.2
    A0_subject:                 float = 0.8
    A0_parochial:               float = 0.5

    # Material Conditions (7)
    cu_unlock_tech:             float = 3.0
    au_contact_bonus:           float = 500.0
    naphtha_richness:           float = 2.0
    naphtha_depletion:          float = 0.008
    energy_to_tfp:              float = 1.0
    pu_dependent_factor:        float = 0.65
    resource_targeting_weight:  float = 2.0

    # Contact Dynamics (3)
    epi_base_severity:          float = 0.30
    sov_extraction_decay:       float = 0.04
    df_detection_range:         float = 0.6


DEFAULT_PARAMS = SimParams()

PARAM_BOUNDS: list = [
    ("civic_expansion_share",       0.2,  0.6),
    ("civic_tech_share",            0.2,  0.6),
    ("civic_consolidation_share",   0.1,  0.4),
    ("subject_expansion_share",     0.1,  0.4),
    ("subject_tech_share",          0.1,  0.5),
    ("subject_consolidation_share", 0.3,  0.7),
    ("parochial_expansion_share",   0.1,  0.4),
    ("parochial_tech_share",        0.1,  0.4),
    ("A0_civic",                    0.8,  1.5),
    ("A0_subject",                  0.5,  1.2),
    ("A0_parochial",                0.3,  0.9),
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

_ISLAND_MAX_HEIGHT = 3000.0

# ---------------------------------------------------------------------------
# Crop → political culture mapping
# Plan: emmer→Civic, paddi→Subject, taro/sago/papa→Parochial, nori→Parochial-Civic hybrid
# Nori maps to civic because it fills the same niche as emmer (mid-latitude maritime
# trade culture with high tech orientation) and the plan describes it as "High tech,
# maritime trade orientation" with Beta(1.5,1) optimistic priors.
# ---------------------------------------------------------------------------

_CROP_TO_CULTURE = {
    "emmer":    "civic",
    "nori":     "civic",       # Parochial-Civic hybrid → civic allocation
    "paddi":    "subject",
    "taro":     "parochial",
    "sago":     "parochial",
    "papa":     "parochial",
    "foraging": "parochial",
}

# Thompson Sampling Beta priors by culture (plan §5.7)
_TS_PRIORS = {
    "civic":     (2.0, 1.0),   # optimistic explorers
    "subject":   (1.0, 2.0),   # skeptical consolidators
    "parochial": (1.0, 1.0),   # uniform, no strong prior
}

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

        culture = _CROP_TO_CULTURE.get(primary_crop, "parochial")

        substrates.append({
            "climate": {
                "latitude": lat, "abs_latitude": abs_lat,
                "wind_belt": wind_belt, "mean_temp": mean_temp,
                "seasonal_range": seasonal_range,
                "effective_rainfall": effective_rainfall,
                "tidal_range": tidal_range, "ocean_warmth": ocean_warmth,
                "gyre_position": gyre_pos, "upwelling": upwelling,
                "fisheries_richness": fisheries, "climate_zone": climate_zone,
            },
            "crops": {
                "primary_crop": primary_crop, "secondary_crop": secondary_crop,
                "primary_yield": primary_yield,
            },
            "trade_goods": {"total_trade_value": total_trade_value},
            "minerals": minerals,
            "culture": culture,
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
                "culture": _CROP_TO_CULTURE.get(crop, "parochial"),
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

    # Substrate (recompute if needed, adding C and culture)
    substrate = world.get("substrate")
    if not substrate or "culture" not in substrate[0]:
        substrate = _compute_substrate(archs, plateau_edges, seed, p.naphtha_richness)
    # Ensure C and culture fields
    for i in range(N):
        mins = substrate[i]["minerals"]
        if "C" not in mins:
            sr = archs[i].get("shelf_r", 0.06)
            td = substrate[i]["climate"].get("tidal_range", 2.0)
            mins["C"] = sr * td * p.naphtha_richness if sr >= 0.04 else 0.0
        # Always recompute culture from crop (don't trust pre-computed values)
        substrate[i]["culture"] = _CROP_TO_CULTURE.get(
            substrate[i]["crops"].get("primary_crop", "foraging"), "parochial")

    rng = Mulberry32((seed if seed != 0 else 42) * 31 + 1066)

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

    # Helper: culture and allocation for a polity core
    def _culture(i):
        return substrate[i]["culture"]

    def _shares(culture):
        if culture == "civic":
            s = [p.civic_expansion_share, p.civic_tech_share, p.civic_consolidation_share]
        elif culture == "subject":
            s = [p.subject_expansion_share, p.subject_tech_share, p.subject_consolidation_share]
        else:
            paroch_con = _clamp(1.0 - p.parochial_expansion_share - p.parochial_tech_share, 0.05, 1.0)
            s = [p.parochial_expansion_share, p.parochial_tech_share, paroch_con]
        t = sum(s)
        return tuple(x / t for x in s) if t > 0 else (0.33, 0.34, 0.33)

    def _A0(culture):
        if culture == "civic":     return p.A0_civic
        if culture == "subject":   return p.A0_subject
        return p.A0_parochial

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
    scramble_onset     = None   # tick when C-rich targeting begins
    pu_scramble_onset  = None
    tech_snapshots     = {}
    pop_snapshots      = {}

    # ── TICK LOOP ─────────────────────────────────────────────────────────
    for tick in range(N_TICKS):
        year = START_YEAR + tick * TICK_YEARS

        # Active polity cores
        cores = sorted(set(controller))

        # Precompute per-core aggregates (amortised over stages)
        core_pop     = {c: _polity_pop(c) for c in cores}
        core_c       = {c: _polity_c(c) for c in cores}
        core_n_ctrl  = {c: sum(1 for j in range(N) if controller[j] == c) for c in cores}

        # ──────────────────────────────────────────────────────────────
        # STAGE 1: Resource accounting (Layer 1)
        # ──────────────────────────────────────────────────────────────
        energy_ratio  = {}  # per core
        energy_surplus = {}

        for core in cores:
            tp = max(1.0, core_pop[core])
            ct = tech[core]

            if ct >= 7.0:
                # Industrial+ energy from naphtha
                e_demand = tp * ct * 0.002
                e_supply = core_c[core] * 0.2
                ratio = _clamp(e_supply / max(0.001, e_demand), 0.3, 1.5)
                surplus = max(0.0, e_supply - e_demand) * 0.2 + tp * 0.01
            else:
                # Pre-industrial: crop yield drives surplus
                y = substrate[core]["crops"]["primary_yield"]
                ratio = _clamp(0.6 + y * 0.2, 0.3, 1.5)
                surplus = y * tp * 0.01

            energy_ratio[core]   = ratio
            energy_surplus[core] = surplus

        # ──────────────────────────────────────────────────────────────
        # STAGE 2: Political allocation (Layer 2)
        # ──────────────────────────────────────────────────────────────
        exp_budget   = {}
        tech_bgt     = {}
        consol_budget = {}

        max_surplus = max(energy_surplus.values()) if energy_surplus else 1.0

        for core in cores:
            culture = _culture(core)
            exp_s, tec_s, con_s = _shares(culture)

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

            budget = energy_surplus[core] + core_pop[core] * 0.002
            exp_budget[core]    = budget * exp_s
            tech_bgt[core]      = budget * tec_s
            consol_budget[core] = budget * con_s

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
                    # DF triggers when two nuclear-capable polities detect each other
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

        # ──────────────────────────────────────────────────────────────
        # STAGE 5: Solow-Romer production + tech growth (plan §5.2, §5.8)
        # delta_tech = A₀ × yield × contact_mult × energy_mult × tech_accel × share_mult × 0.001
        # Tech accelerates with: more contacts, energy surplus, existing tech level
        # ──────────────────────────────────────────────────────────────
        for core in cores:
            culture   = _culture(core)
            a0        = _A0(culture)
            nc        = len(contact_set[core])
            tp        = max(1.0, core_pop[core])
            er        = energy_ratio[core]
            crop_y    = substrate[core]["crops"]["primary_yield"]

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
            share_mult   = _shares(culture)[1] / 0.3

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
        # STAGE 6: Thompson Sampling expansion (plan §5.7)
        # ──────────────────────────────────────────────────────────────
        for core in cores:
            budget = exp_budget.get(core, 0.0)
            if budget < 0.1: continue
            if tech[core] < 2.0: continue  # need bronze-age institutions to project power

            culture = _culture(core)
            ts_a, ts_b = _TS_PRIORS.get(culture, (1.0, 1.0))

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

                score = ts_score + p.resource_targeting_weight * rv - dist * 1.5
                candidates.append((score, target, dist))

            candidates.sort(key=lambda x: -x[0])

            absorbed_this_tick = 0
            for score, target, dist in candidates:
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

                # Epidemiological shock at first contact
                if first_contact_tick[target] is None:
                    first_contact_tick[target] = tick
                    cc = substrate[core]["crops"]["primary_crop"]
                    ct = substrate[target]["crops"]["primary_crop"]
                    cdist = _crop_distance(cc, ct)
                    sev = p.epi_base_severity + rng.next_float() * 0.15
                    mort = sev * cdist
                    pop[target] *= (1.0 - mort)
                    epi_log.append({"arch": target, "contactor": core,
                                    "mortality_rate": mort, "tick": tick, "year": year})

                # Transfer all archs controlled by target to core
                for j in range(N):
                    if controller[j] == target:
                        controller[j] = core
                controller[target] = core
                absorbed_tick[target] = tick
                sovereignty[target] = _clamp(0.15 + dist * 0.3, 0.10, 0.50)
                budget -= cost
                absorbed_this_tick += 1

                # Inherit target's contacts
                for c in contact_set[target]:
                    if c != core:
                        contact_set[core].add(c)

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
            recovery = p.sov_extraction_decay * sovereignty[i] * (pop[i] / max(1.0, pop[core])) * 0.5

            sovereignty[i] += (recovery - extraction) * 0.1
            sovereignty[i] = _clamp(sovereignty[i], 0.05, 0.95)

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
    hegemon_cultures = {c: _culture(c) for c in hegemons}

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
            faction = _culture(i)
            status  = "core"
        elif core in hegemons:
            faction = _culture(core)
            if sovereignty[i] < 0.3:   status = "colony"
            elif sovereignty[i] < 0.6: status = "garrison" if _culture(core) == "subject" else "client"
            else:                      status = "contacted"
        elif controller[i] == i:
            faction = "independent"
            status  = "uncontacted" if absorbed_tick[i] is None else "independent"
        else:
            faction = _culture(core)
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
            "culture":          _culture(controller[i]),
            "fleet_scale":      fleet_scale[i],
            "c_remaining":      c_remaining[i],
            "controller":       controller[i],
        })

    # Backward-compat faction labels: map civic→reach, subject→lattice
    reach_arch = lattice_arch = None
    for h in hegemons:
        if _culture(h) == "civic" and reach_arch is None:
            reach_arch = h
        elif _culture(h) == "subject" and lattice_arch is None:
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
            "culture_type": _culture(core),
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
        "c_depletion_frac":     c_depletion_frac,
        "total_c_initial":      total_c_init,
        "total_c_remaining":    total_c_rem,
        "scramble_onset_tick":  scramble_onset,
        "pu_scramble_onset_tick": pu_scramble_onset,
        "uncontacted_count":    uncontacted,
        "fleet_scales":         {c: fleet_scale[c] for c in hegemons},
        "polity_pops":          polity_pops,
        "n_polities":           len(final_cores),
    }


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_seed(seed=216089, world_path=None, params=None, verbose=True):
    if params is None:
        params = DEFAULT_PARAMS
    if world_path:
        world = load_world(world_path)
    else:
        import os
        candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 f"worlds/candidate_{seed:07d}.json")
        if os.path.exists(candidate):
            world = load_world(candidate)
        else:
            raise FileNotFoundError(f"No world file for seed {seed}")

    result = simulate(world, params, seed=seed)

    if verbose:
        lines = [f"=== Seed {seed} verification ==="]
        lines.append(f"Hegemons ({len(result['hegemons'])}): {result['hegemons']}")
        for h in result["hegemons"]:
            c = result["hegemon_cultures"][h]
            s = result["states"][h]
            lines.append(f"  arch {h}: culture={c}, tech={s['tech']:.1f}, "
                         f"pop={s['population']}, fleet={result['fleet_scales'].get(h, 0):.2f}, "
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
            lines.append(f"[{'OK' if -200 <= result['df_year'] <= -40 else 'WARN'}] "
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
