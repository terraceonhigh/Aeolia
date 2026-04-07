"""
sim_proxy.py — Aeolia History Engine v2

Energy-coupled, faction-agnostic tick simulation.

Replaces the era-based, faction-specific v1 engine with:
  - Solow-Romer production coupled to energy (naphtha) economics
  - Political allocation by culture type (Civic / Subject / Parochial)
  - Thompson Sampling expansion with tech-gated resource targeting
  - Naphtha depletion and nuclear forcing
  - 21 physically meaningful parameters

One tick ≈ 50 years.  Antiquity (-20 000 to -5 000 BP) bootstrapped in a
single pass; 100 ticks from -5 000 to 0 BP run the full pipeline.

Usage
-----
    from sim_proxy import SimParams, simulate, load_godot_world
    world = load_godot_world("worlds/candidate_0216089.json")
    result = simulate(world, SimParams(), seed=216089)
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
    """Mulberry32 deterministic PRNG.  Same seed → same world, always."""

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
# Constants
# ---------------------------------------------------------------------------

_ISLAND_MAX_HEIGHT = 3000.0
_TWO_PI = 2.0 * math.pi

# Crop → political culture type (faction-agnostic)
CROP_TO_CULTURE = {
    "emmer":    "civic",
    "paddi":    "subject",
    "taro":     "parochial",
    "nori":     "parochial",
    "sago":     "parochial",
    "papa":     "parochial",
    "foraging": "parochial",
}

# Thompson Sampling Beta priors per culture type
CULTURE_TS_PRIORS = {
    "civic":     (2, 1),   # optimistic explorers
    "subject":   (1, 2),   # skeptical consolidators
    "parochial": (1, 1),   # uniform — no strong prior
}

# IR posture labels
_POSTURE_EXPLORE  = "explore"
_POSTURE_PROJECT  = "project"
_POSTURE_HEDGE    = "hedge"
_POSTURE_FORTIFY  = "fortify"
_POSTURE_ALIGN    = "align"
_POSTURE_FREE_RIDE = "free_ride"


# ---------------------------------------------------------------------------
# Parameters — 21 total (see HISTORY_ENGINE_V2_PLAN.md §4)
# ---------------------------------------------------------------------------

@dataclass
class SimParams:
    """All tunable coefficients for the v2 energy-coupled history engine."""

    # Political culture allocation shares
    civic_expansion_share:       float = 0.45
    civic_tech_share:            float = 0.35
    civic_consolidation_share:   float = 0.20   # derived: 1 - exp - tech
    subject_expansion_share:     float = 0.20
    subject_tech_share:          float = 0.25
    subject_consolidation_share: float = 0.55   # derived
    parochial_expansion_share:   float = 0.30
    parochial_tech_share:        float = 0.25
    # parochial_consolidation = 1 - exp - tech

    # Knowledge compounding
    A0_civic:      float = 1.1
    A0_subject:    float = 0.8
    A0_parochial:  float = 0.5

    # Material conditions
    cu_unlock_tech:           float = 3.0
    au_contact_bonus:         float = 500.0
    naphtha_richness:         float = 2.0
    naphtha_depletion:        float = 0.01
    energy_to_tfp:            float = 1.0
    pu_dependent_factor:      float = 0.6
    resource_targeting_weight: float = 2.0

    # Contact dynamics
    epi_base_severity:   float = 0.30
    sov_extraction_decay: float = 0.05
    df_detection_range:  float = 0.6


DEFAULT_PARAMS = SimParams()

# Parameter definitions for the optimizer: (attr_name, lower, upper)
PARAM_BOUNDS: list = [
    ("civic_expansion_share",       0.20, 0.60),
    ("civic_tech_share",            0.20, 0.60),
    ("civic_consolidation_share",   0.10, 0.40),
    ("subject_expansion_share",     0.10, 0.40),
    ("subject_tech_share",          0.10, 0.50),
    ("subject_consolidation_share", 0.30, 0.70),
    ("parochial_expansion_share",   0.10, 0.40),
    ("parochial_tech_share",        0.10, 0.40),
    ("A0_civic",                    0.80, 1.50),
    ("A0_subject",                  0.50, 1.20),
    ("A0_parochial",                0.30, 0.90),
    ("cu_unlock_tech",              2.00, 4.00),
    ("au_contact_bonus",          100.0, 2000.0),
    ("naphtha_richness",            0.50, 5.00),
    ("naphtha_depletion",           0.001, 0.05),
    ("energy_to_tfp",               0.50, 2.00),
    ("pu_dependent_factor",         0.40, 0.90),
    ("resource_targeting_weight",   0.00, 5.00),
    ("epi_base_severity",           0.15, 0.50),
    ("sov_extraction_decay",        0.01, 0.10),
    ("df_detection_range",          0.30, 1.00),
]


def pack_params(p: SimParams) -> list:
    return [getattr(p, name) for name, _, _ in PARAM_BOUNDS]


def unpack_params(x) -> SimParams:
    p = SimParams()
    for i, (name, lo, hi) in enumerate(PARAM_BOUNDS):
        setattr(p, name, float(x[i]))
    return p


def scipy_bounds():
    return [(lo, hi) for _, lo, hi in PARAM_BOUNDS]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log2(x: float) -> float:
    return math.log2(x) if x > 0.0 else 0.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _gc_dist_xy(a: dict, b: dict) -> float:
    """Great-circle distance in radians between two arch dicts (cx/cy/cz)."""
    dot = a["cx"] * b["cx"] + a["cy"] * b["cy"] + a["cz"] * b["cz"]
    return math.acos(max(-1.0, min(1.0, dot)))


def _beta_sample(alpha: int, beta_param: int, rng: Mulberry32) -> float:
    """Sample from Beta(alpha, beta_param) using order-statistic shortcuts."""
    if alpha == 2 and beta_param == 1:
        return max(rng.next_float(), rng.next_float())
    elif alpha == 1 and beta_param == 2:
        return min(rng.next_float(), rng.next_float())
    elif alpha == 1 and beta_param == 1:
        return rng.next_float()
    else:
        # Fallback: use rng average weighted toward alpha
        total = alpha + beta_param
        return _clamp(rng.next_float() * 0.6 + (alpha / total) * 0.4, 0.01, 0.99)


def _get_culture(core_arch: int, substrate: list) -> str:
    crop = substrate[core_arch]["crops"]["primary_crop"]
    return CROP_TO_CULTURE.get(crop, "parochial")


def _get_shares(params: SimParams, culture: str) -> tuple:
    """Return (expansion, tech, consolidation) shares, normalized to sum=1."""
    if culture == "civic":
        e, t = params.civic_expansion_share, params.civic_tech_share
        c = max(0.05, 1.0 - e - t)
    elif culture == "subject":
        e, t = params.subject_expansion_share, params.subject_tech_share
        c = max(0.05, 1.0 - e - t)
    else:
        e, t = params.parochial_expansion_share, params.parochial_tech_share
        c = max(0.05, 1.0 - e - t)
    total = e + t + c
    return (e / total, t / total, c / total)


def _get_A0(params: SimParams, culture: str) -> float:
    if culture == "civic":
        return params.A0_civic
    elif culture == "subject":
        return params.A0_subject
    return params.A0_parochial


def _resource_value(target: int, tech: float, substrate: list,
                    c_remaining: list, params: SimParams) -> float:
    """Tech-gated resource value of a target arch."""
    val = 0.1   # Fe always present, trivial
    mins = substrate[target]["minerals"]
    if tech >= params.cu_unlock_tech and mins.get("Cu", False):
        val += 1.0
    if tech >= 4.0 and mins.get("Au", False):
        val += params.au_contact_bonus / 500.0
    if tech >= 7.0 and c_remaining[target] > 0:
        val += c_remaining[target] * 3.0
    if tech >= 9.0 and mins.get("Pu", False):
        val += 10.0
    return val


# ---------------------------------------------------------------------------
# Crop distance (mirrors history_engine._crop_distance exactly)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Substrate computation — faithful port of substrate.gd (unchanged from v1)
# ---------------------------------------------------------------------------

def _compute_gyre_position(arch: dict, all_archs: list) -> float:
    cy_clamped = max(-1.0, min(1.0, arch["cy"]))
    lat        = math.asin(cy_clamped) * 180.0 / math.pi
    abs_lat    = abs(lat)
    band_archs = []
    for other_arch in all_archs:
        other_cy  = max(-1.0, min(1.0, other_arch["cy"]))
        other_lat = math.asin(other_cy) * 180.0 / math.pi
        if abs(abs(other_lat) - abs_lat) < 15:
            band_archs.append(other_arch)
    if len(band_archs) < 2:
        return 0.5
    lons = sorted(
        math.atan2(ba["cz"], ba["cx"]) * 180.0 / math.pi for ba in band_archs
    )
    max_gap = 0.0
    gap_center = 0.0
    for j in range(len(lons)):
        next_lon = lons[(j + 1) % len(lons)]
        if j == len(lons) - 1:
            next_lon += 360.0
        gap = next_lon - lons[j]
        if gap > max_gap:
            max_gap = gap
            gap_center = lons[j] + gap / 2.0
    if max_gap < 10:
        return 0.5
    my_lon  = math.atan2(arch["cz"], arch["cx"]) * 180.0 / math.pi
    rel_pos = math.fmod(my_lon - gap_center + 540.0, 360.0) / 360.0
    return max(0.0, min(1.0, rel_pos))


def _compute_substrate(archs: list, plateau_edges: list, seed: int) -> list:
    """Full faithful port of substrate.gd compute_substrate()."""
    rng = Mulberry32((seed if seed > 0 else 42) * 47 + 2024)
    n   = len(archs)

    edge_count   = [0] * n
    edge_lengths = [[] for _ in range(n)]
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        edge_count[a] += 1
        edge_count[b] += 1
        dot = max(-1.0, min(1.0,
            archs[a]["cx"] * archs[b]["cx"] +
            archs[a]["cy"] * archs[b]["cy"] +
            archs[a]["cz"] * archs[b]["cz"]))
        ang = math.acos(dot)
        edge_lengths[a].append(ang)
        edge_lengths[b].append(ang)

    all_lens = []
    for ll in edge_lengths:
        all_lens.extend(ll)
    max_edge_len = max(all_lens) if all_lens else 0.5

    substrates = []
    for i, arch in enumerate(archs):
        cy_clamped = max(-1.0, min(1.0, arch["cy"]))
        lat        = math.asin(cy_clamped) * 180.0 / math.pi
        abs_lat    = abs(lat)
        size       = arch["shelf_r"] / 0.12
        peaks      = arch.get("peaks", [])
        peak_count = len(peaks)
        avg_h      = 0.0
        if peak_count > 0:
            avg_h = sum(pk["h"] for pk in peaks) / (peak_count * _ISLAND_MAX_HEIGHT)
        avg_edge = sum(edge_lengths[i]) / len(edge_lengths[i]) if edge_lengths[i] else 0.5

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
        if   gyre_pos < 0.3: ocean_warmth = 0.8 + gyre_pos
        elif gyre_pos > 0.7: ocean_warmth = 0.3 - (gyre_pos - 0.7)
        else:                ocean_warmth = 0.4 + gyre_pos * 0.2
        ocean_warmth = _clamp(ocean_warmth, 0.0, 1.0)

        moisture_bonus     = 1.0 + max(0.0, ocean_warmth - 0.4) * 0.4
        effective_rainfall = base_rain * orographic_bonus * moisture_bonus * 1.4
        mean_temp      = 28.0 - abs_lat * 0.45 + (ocean_warmth - 0.5) * 4.0
        seasonal_range = abs_lat * 0.15 * 0.7

        nearby_archs = sum(
            1 for oa in archs if oa is not arch and
            arch["cx"]*oa["cx"] + arch["cy"]*oa["cy"] + arch["cz"]*oa["cz"] > 0.95)
        cluster_density = min(1.0, float(nearby_archs) / 5.0)
        abs_lat_rad = abs_lat * math.pi / 180.0
        tidal_range = ((2.0 + arch["shelf_r"] * 30.0 + cluster_density * 4.0) *
                       (0.8 + abs(math.sin(abs_lat_rad)) * 0.4))

        upwelling = 0.0
        if gyre_pos > 0.7: upwelling += 0.4
        if abs_lat < 5:    upwelling += 0.3
        upwelling += edge_count[i] * 0.08

        if   mean_temp > 24 and effective_rainfall > 2000: climate_zone = "tropical_wet"
        elif mean_temp > 24 and effective_rainfall < 1000: climate_zone = "tropical_dry"
        elif mean_temp > 10 and effective_rainfall > 1200: climate_zone = "temperate_wet"
        elif mean_temp > 10:                               climate_zone = "temperate_dry"
        elif mean_temp > 2:                                climate_zone = "subpolar"
        else:                                              climate_zone = "polar_fringe"

        shelf_r = arch["shelf_r"]
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
            yields["paddi"] = (5.0 * min(1.0, (mean_temp - 18.0) / 15.0)
                               * min(1.0, effective_rainfall / 1800.0)
                               * min(1.0, tidal_range / 5.0))
        if can_grow["emmer"]:
            yields["emmer"] = (2.5 * (1.0 - abs(mean_temp - 16.0) / 20.0)
                               * (1.0 - abs(effective_rainfall - 700.0) / 1500.0))
        if can_grow["taro"]:
            yields["taro"] = (3.0 * min(1.0, (mean_temp - 20.0) / 8.0)
                              * min(1.0, effective_rainfall / 2000.0))
        if can_grow["nori"]:
            yields["nori"] = (1.5 * min(1.0, upwelling * 2.0)
                              * min(1.0, float(edge_count[i]) / 3.0) * 2.0)
        if can_grow["sago"]:
            yields["sago"] = (4.0 * min(1.0, effective_rainfall / 2500.0)
                              * min(1.0, shelf_r / 0.10))
        if can_grow["papa"]:
            yields["papa"] = (3.5 * (1.0 - abs(mean_temp - 12.0) / 15.0)
                              * min(1.0, effective_rainfall / 600.0))

        crop_entries = sorted(yields.items(), key=lambda kv: (-kv[1], kv[0]))
        primary_crop = "foraging"
        secondary_crop = None
        primary_yield = 0.5
        if crop_entries:
            primary_crop  = crop_entries[0][0]
            primary_yield = crop_entries[0][1]
        if len(crop_entries) > 1:
            secondary_crop = crop_entries[1][0]

        # Trade goods — consume RNG calls in substrate order
        stim_map  = {"paddi": "char", "emmer": "qahwa", "taro": "awa",
                     "sago": "pinang", "papa": "aqua", "nori": "", "foraging": ""}
        fiber_map = {"paddi": "seric", "emmer": "fell", "taro": "tapa",
                     "sago": "tapa", "nori": "byssus", "papa": "qivu", "foraging": ""}
        prot_map  = {"paddi": "kerbau", "emmer": "kri", "taro": "moa",
                     "sago": "moa", "nori": "", "papa": "", "foraging": ""}
        stim_type  = stim_map.get(primary_crop, "")
        fiber_type = fiber_map.get(primary_crop, "")
        prot_type  = prot_map.get(primary_crop, "")
        stim_prod  = (0.3 + rng.next_float() * 0.5) if stim_type  else 0.0
        fiber_prod = (0.3 + rng.next_float() * 0.5) if fiber_type else 0.0
        prot_prod  = (0.3 + rng.next_float() * 0.4) if prot_type  else 0.0
        nori_export = 0.0
        if primary_crop == "nori":
            nori_export = 0.6 + rng.next_float() * 0.3
        elif can_grow["nori"]:
            nori_export = 0.1 + rng.next_float() * 0.2
        total_trade_value = stim_prod * 0.4 + fiber_prod * 0.3 + prot_prod * 0.2 + nori_export * 0.3

        # Political culture label
        culture_init = {
            "paddi": {"awareness": 0.70, "participation": 0.15},
            "emmer": {"awareness": 0.70, "participation": 0.70},
            "taro":  {"awareness": 0.15, "participation": 0.10},
            "nori":  {"awareness": 0.30, "participation": 0.55},
            "sago":  {"awareness": 0.15, "participation": 0.20},
            "papa":  {"awareness": 0.25, "participation": 0.15},
            "foraging": {"awareness": 0.05, "participation": 0.05},
        }
        pc = dict(culture_init.get(primary_crop, culture_init["foraging"]))
        if pc["awareness"] > 0.5 and pc["participation"] > 0.5:
            culture_label = "civic"
        elif pc["awareness"] > 0.5:
            culture_label = "subject"
        else:
            culture_label = "parochial"

        # Minerals
        minerals = {
            "Fe": True,
            "Cu": rng.next_float() < 0.20,
            "Au": rng.next_float() < (0.05 + avg_h * 0.08),
            "Pu": rng.next_float() < (0.03 + size * 0.02),
        }

        substrates.append({
            "climate": {
                "latitude": lat, "abs_latitude": abs_lat, "wind_belt": wind_belt,
                "mean_temp": mean_temp, "seasonal_range": seasonal_range,
                "effective_rainfall": effective_rainfall,
                "tidal_range": tidal_range, "ocean_warmth": ocean_warmth,
                "gyre_position": gyre_pos, "upwelling": upwelling,
                "climate_zone": climate_zone,
            },
            "crops": {
                "primary_crop": primary_crop, "secondary_crop": secondary_crop,
                "primary_yield": primary_yield,
            },
            "trade_goods": {"total_trade_value": total_trade_value},
            "minerals": minerals,
            "political_culture": {"label": culture_label},
        })
    return substrates


# ---------------------------------------------------------------------------
# World loader — reads Godot-exported JSON (flat substrate → nested)
# ---------------------------------------------------------------------------

def load_godot_world(path: str) -> dict:
    """Load a Godot-exported world JSON and normalise flat substrate."""
    import json
    with open(path) as f:
        data = json.load(f)
    flat_sub = data.get("substrate", [])
    nested_sub = []
    for s in flat_sub:
        if "crops" in s:
            nested_sub.append(s)
            continue
        nested_sub.append({
            "crops": {
                "primary_crop":  s.get("primary_crop",  "foraging"),
                "primary_yield": s.get("primary_yield", 0.5),
                "secondary_crop": s.get("secondary_crop", None),
            },
            "climate": {
                "latitude":           s.get("latitude",           0.0),
                "abs_latitude":       s.get("abs_latitude",      30.0),
                "tidal_range":        s.get("tidal_range",        2.0),
                "mean_temp":          s.get("mean_temp",         18.0),
                "effective_rainfall": s.get("effective_rainfall", 1000.0),
                "upwelling":          s.get("upwelling",          0.1),
            },
            "trade_goods": {
                "total_trade_value": s.get("total_trade_value", 0.0),
            },
            "minerals": s.get("minerals", {"Fe": True, "Cu": False, "Au": False, "Pu": False}),
        })
    data["substrate"] = nested_sub
    return data


# ---------------------------------------------------------------------------
# World generator — for synthetic test worlds
# ---------------------------------------------------------------------------

def _generate_plateau_edges(archs: list) -> list:
    n = len(archs)
    MAX_ANG = 0.9
    angles = {}
    for i in range(n):
        for j in range(i + 1, n):
            dot = max(-1.0, min(1.0,
                archs[i]["cx"]*archs[j]["cx"] + archs[i]["cy"]*archs[j]["cy"] +
                archs[i]["cz"]*archs[j]["cz"]))
            angles[(i, j)] = math.acos(dot)
    edges = set()
    for i in range(n):
        by_dist = sorted(
            [j for j in range(n) if j != i],
            key=lambda j: angles[(min(i, j), max(i, j))],
        )
        for j in by_dist[:2]:
            edges.add((min(i, j), max(i, j)))
    for (i, j), ang in angles.items():
        if ang < MAX_ANG:
            edges.add((i, j))
    return [list(e) for e in sorted(edges)]


def generate_test_world(seed: int = 42, n_archs: int = 42) -> dict:
    """Generate a synthetic world.  Faction-agnostic: reach_arch / lattice_arch
    are retained as geographic markers (most-antipodal pair) only."""
    rng = Mulberry32(seed * 31 + 7)
    phi = math.pi * (3.0 - math.sqrt(5.0))
    archs = []
    for i in range(n_archs):
        y     = 1.0 - (i / max(n_archs - 1, 1)) * 2.0
        theta = phi * i
        y     += (rng.next_float() - 0.5) * 0.15
        theta += (rng.next_float() - 0.5) * 0.40
        y     = _clamp(y, -0.98, 0.98)
        r     = math.sqrt(max(0.0, 1.0 - y * y))
        x     = math.cos(theta) * r
        z     = math.sin(theta) * r
        norm  = math.sqrt(x*x + y*y + z*z) or 1.0
        cx, cy, cz = x / norm, y / norm, z / norm
        rv = rng.next_float()
        if rv < 0.15:
            shelf_r = 0.10 + rng.next_float() * 0.10
            n_pk    = int(8 + rng.next_float() * 14)
        elif rv < 0.40:
            shelf_r = 0.06 + rng.next_float() * 0.06
            n_pk    = int(4 + rng.next_float() * 6)
        else:
            shelf_r = 0.03 + rng.next_float() * 0.04
            n_pk    = int(1 + rng.next_float() * 4)
        peaks = [{"h": 500.0 + rng.next_float() * 2500.0} for _ in range(max(1, n_pk))]
        archs.append({"cx": cx, "cy": cy, "cz": cz, "shelf_r": shelf_r, "peaks": peaks})

    # Most-antipodal pair → geographic markers
    reach_arch = 0; lattice_arch = 1; best_dot = 2.0
    for i in range(n_archs):
        for j in range(i + 1, n_archs):
            d = archs[i]["cx"]*archs[j]["cx"] + archs[i]["cy"]*archs[j]["cy"] + archs[i]["cz"]*archs[j]["cz"]
            if d < best_dot:
                best_dot = d; reach_arch = i; lattice_arch = j
    if archs[reach_arch]["cy"] < archs[lattice_arch]["cy"]:
        reach_arch, lattice_arch = lattice_arch, reach_arch

    plateau_edges = _generate_plateau_edges(archs)
    substrate = _compute_substrate(archs, plateau_edges, seed)
    return {
        "archs": archs, "plateau_edges": plateau_edges,
        "reach_arch": reach_arch, "lattice_arch": lattice_arch,
        "substrate": substrate,
    }


# ---------------------------------------------------------------------------
# Core simulation — energy-coupled tick pipeline
# ---------------------------------------------------------------------------

def simulate(
    world: dict,
    params: SimParams = DEFAULT_PARAMS,
    seed: int = 42,
) -> dict:
    """
    Run the v2 Aeolia history engine.

    Returns dict with: states, polities, df_year, epi_log, expansion_log,
    substrate, archs, hegemons, fleet_scale, tech/c histories.
    """
    archs         = world["archs"]
    plateau_edges = world["plateau_edges"]
    N = len(archs)

    # Normalise substrate
    substrate = world.get("substrate")
    if not substrate:
        substrate = _compute_substrate(archs, plateau_edges, seed)
    elif substrate and not isinstance(substrate[0].get("crops"), dict):
        # Flat Godot substrate — re-normalise
        world_copy = dict(world)
        world_copy["substrate"] = substrate
        world_copy = load_godot_world.__wrapped__(world_copy) if hasattr(load_godot_world, "__wrapped__") else world_copy
        substrate = world_copy["substrate"]
    # Ensure nested format
    if substrate and "crops" not in substrate[0]:
        nested = []
        for s in substrate:
            nested.append({
                "crops": {
                    "primary_crop":  s.get("primary_crop",  "foraging"),
                    "primary_yield": s.get("primary_yield", 0.5),
                    "secondary_crop": s.get("secondary_crop", None),
                },
                "climate": {
                    "tidal_range":  s.get("tidal_range",  2.0),
                    "abs_latitude": s.get("abs_latitude", 30.0),
                    "latitude":     s.get("latitude",     0.0),
                    "mean_temp":    s.get("mean_temp",    18.0),
                },
                "trade_goods": {"total_trade_value": s.get("total_trade_value", 0.0)},
                "minerals": s.get("minerals", {"Fe": True, "Cu": False, "Au": False, "Pu": False}),
            })
        substrate = nested

    p = params
    rng = Mulberry32((seed if seed != 0 else 42) * 31 + 1066)

    # ── Build adjacency ──────────────────────────────────────────────────
    adj = [[] for _ in range(N)]
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        adj[a].append(b)
        adj[b].append(a)

    # ── Pre-compute pairwise GC distances ────────────────────────────────
    gc_mat = [[0.0] * N for _ in range(N)]
    for i in range(N):
        for j in range(i + 1, N):
            d = _gc_dist_xy(archs[i], archs[j])
            gc_mat[i][j] = d
            gc_mat[j][i] = d

    # ── Resource potential (for antiquity bootstrap) ─────────────────────
    potential = []
    for i, arch in enumerate(archs):
        pk = arch.get("peaks", [])
        p_cnt = len(pk)
        avg_h = (sum(x["h"] for x in pk) / (p_cnt * _ISLAND_MAX_HEIGHT)) if p_cnt > 0 else 0.0
        sz = arch.get("shelf_r", 0.06) / 0.12
        pot = (p_cnt / 20.0 * 0.4 + avg_h * 0.3 + sz / 2.2 * 0.3) * (0.6 + rng.next_float() * 0.4)
        potential.append(pot)

    # ── Per-arch state ───────────────────────────────────────────────────
    pop = []
    for i, arch in enumerate(archs):
        pk_cnt = len(arch.get("peaks", []))
        sz = arch.get("shelf_r", 0.06) / 0.12
        base = float(pk_cnt) * sz * (3.0 + rng.next_float() * 4.0)
        pop.append(max(1.0, base))

    # Antiquity bootstrap (-20 000 to -5 000 BP): ~300 generations
    for i in range(N):
        pop[i] *= (1.0 + 0.002 * potential[i]) ** 30
        pop[i] = max(1.0, pop[i])

    # C (naphtha) reserves — shelf_r × tidal_range × naphtha_richness
    c_remaining = [0.0] * N
    for i in range(N):
        shelf_r = archs[i].get("shelf_r", 0.0)
        tidal   = substrate[i]["climate"].get("tidal_range", 2.0)
        if shelf_r >= 0.04:
            c_remaining[i] = shelf_r * tidal * p.naphtha_richness

    c_initial_total = sum(c_remaining)

    sovereignty = [1.0] * N
    trade_integration = [0.0] * N

    # ── Per-polity state (key = leader arch index) ───────────────────────
    leader = list(range(N))
    polity_members = {i: [i] for i in range(N)}

    # Tech — bootstrap from potential
    polity_tech = {}
    for i in range(N):
        polity_tech[i] = potential[i] * (2.5 + rng.next_float() * 1.5)

    polity_knowledge = {i: 1.5 for i in range(N)}
    polity_capital   = {i: max(1.0, pop[i]) for i in range(N)}
    polity_posture   = {i: _POSTURE_EXPLORE for i in range(N)}

    # ── Tracking state ───────────────────────────────────────────────────
    awareness = {}        # (leader_a, leader_b) -> float [0, 1]
    df_year = None
    df_polity_a = None
    df_polity_b = None
    epi_log = []
    expansion_log = []
    epi_exposed = set()     # (contactor_crop, contacted_crop) pairs already contacted
    epi_applied_to = set() # arch indices that have already had epidemic shock
    tech_history = []
    c_history = []
    scramble_tick = None   # first tick a polity targets C-rich islands

    # ══════════════════════════════════════════════════════════════════════
    # TICK LOOP — 100 ticks, -5 000 to 0 BP
    # ══════════════════════════════════════════════════════════════════════
    TICK_COUNT = 100
    TICK_YEARS = 50
    START_YEAR = -5000

    for tick in range(TICK_COUNT):
        year = START_YEAR + tick * TICK_YEARS
        active = list(polity_members.keys())

        # ── Stage 1: RESOURCE ACCOUNTING ─────────────────────────────────
        polity_energy  = {}
        polity_pop     = {}
        polity_surplus = {}

        for pl in active:
            members = polity_members[pl]
            total_pop_p = sum(pop[j] for j in members)
            polity_pop[pl] = max(1.0, total_pop_p)
            tech_now = polity_tech.get(pl, 0)

            if tech_now >= 7.0:
                total_c = sum(c_remaining[j] for j in members)
                demand  = total_pop_p * tech_now * 0.005
                ratio   = _clamp(total_c / max(demand, 0.001), 0.3, 1.5)
            elif tech_now >= p.cu_unlock_tech:
                has_cu = any(substrate[j]["minerals"].get("Cu", False) for j in members)
                ratio = 1.0 + (0.05 if has_cu else 0.0)
            else:
                ratio = 1.0
            polity_energy[pl] = ratio

            # Solow-Romer: per-capita output
            A = p.energy_to_tfp * ratio * polity_knowledge[pl]
            K = max(polity_capital[pl], total_pop_p * 0.3)  # labor-as-capital floor
            L = polity_pop[pl]
            per_capita_Y = A * ((K / L) ** 0.3)
            subsistence  = 0.3 + tech_now * 0.03
            surplus_pc   = max(0.0, per_capita_Y - subsistence)
            polity_surplus[pl] = surplus_pc * L

        # ── Stage 2: POLITICAL ALLOCATION ────────────────────────────────
        exp_budget  = {}
        tech_budget = {}
        cons_budget = {}

        for pl in active:
            culture = _get_culture(pl, substrate)
            e_sh, t_sh, c_sh = _get_shares(p, culture)

            # IR posture adjustment
            posture = polity_posture.get(pl, _POSTURE_EXPLORE)
            if posture in (_POSTURE_EXPLORE, _POSTURE_PROJECT):
                e_sh *= 1.3; c_sh *= 0.7
            elif posture in (_POSTURE_FORTIFY, _POSTURE_HEDGE):
                e_sh *= 0.7; c_sh *= 1.3
            elif posture == _POSTURE_ALIGN:
                e_sh *= 0.5; t_sh *= 0.8; c_sh *= 1.5
            total_sh = e_sh + t_sh + c_sh
            e_sh /= total_sh; t_sh /= total_sh; c_sh /= total_sh

            S = polity_surplus.get(pl, 0)
            exp_budget[pl]  = S * e_sh
            tech_budget[pl] = S * t_sh
            cons_budget[pl] = S * c_sh

        # ── Stage 3: RUMOR PROPAGATION + CONTACTS ────────────────────────
        contacts = {}
        for pl in active:
            c_set = set()
            for m in polity_members[pl]:
                for nb in adj[m]:
                    nb_ldr = leader[nb]
                    if nb_ldr != pl and nb_ldr in polity_members:
                        c_set.add(nb_ldr)
            contacts[pl] = c_set

        # ── Stage 4: BAYESIAN BELIEF UPDATE ──────────────────────────────
        for pl in active:
            for other in contacts.get(pl, set()):
                key = (pl, other)
                old_aw = awareness.get(key, 0.0)
                delta = 0.05  # direct border contact
                # Unfamiliar trade goods
                if _get_culture(pl, substrate) != _get_culture(other, substrate):
                    delta += 0.05
                # Multi-hop rumor propagation: if this contact knows about a third
                for third in contacts.get(other, set()):
                    if third != pl:
                        key3 = (pl, third)
                        old3 = awareness.get(key3, 0.0)
                        if old3 < 0.5:
                            awareness[key3] = min(1.0, old3 + 0.02)
                # Industrial / nuclear signal detection
                other_tech = polity_tech.get(other, 0)
                if other_tech >= 7.0:
                    dist = gc_mat[pl][other] if pl < N and other < N else 1.0
                    det_range = p.df_detection_range * (other_tech / 10.0)
                    if dist < det_range:
                        delta += 0.25
                        if other_tech >= 9.0:
                            delta = 1.0  # nuclear intercept → full awareness
                awareness[key] = min(1.0, old_aw + delta)

        # ── Stage 5: IR POSTURE SELECTION ────────────────────────────────
        max_surplus = max(polity_surplus.values()) if polity_surplus else 1.0
        for pl in active:
            surplus_pl = polity_surplus.get(pl, 0)
            cap = "HIGH" if surplus_pl > max_surplus * 0.6 else ("MED" if surplus_pl > max_surplus * 0.2 else "LOW")

            max_threat = "LOW"
            for other in contacts.get(pl, set()):
                s_oth = polity_surplus.get(other, 0)
                c_oth = "HIGH" if s_oth > max_surplus * 0.6 else ("MED" if s_oth > max_surplus * 0.2 else "LOW")
                if c_oth == "HIGH":
                    max_threat = "HIGH"
                elif c_oth == "MED" and max_threat != "HIGH":
                    max_threat = "MED"

            if cap == "HIGH" and max_threat == "HIGH":
                polity_posture[pl] = _POSTURE_PROJECT   # Mearsheimer
            elif cap == "MED" and max_threat == "HIGH":
                polity_posture[pl] = _POSTURE_HEDGE     # Walt
            elif cap == "LOW" and max_threat == "HIGH":
                polity_posture[pl] = _POSTURE_ALIGN     # Schweller
            elif cap == "HIGH":
                polity_posture[pl] = _POSTURE_EXPLORE
            elif cap == "LOW":
                polity_posture[pl] = _POSTURE_FREE_RIDE
            else:
                polity_posture[pl] = _POSTURE_EXPLORE

        # ── Stage 6: THOMPSON SAMPLING EXPANSION ─────────────────────────
        expand_order = sorted(active, key=lambda x: -polity_tech.get(x, 0))
        absorbed_this_tick = set()

        for pl in expand_order:
            if pl not in polity_members:
                continue
            budget = exp_budget.get(pl, 0)
            if budget < 0.5:
                continue

            p_tech = polity_tech.get(pl, 0)
            culture = _get_culture(pl, substrate)
            ts_a, ts_b = CULTURE_TS_PRIORS[culture]

            # Candidate targets: archs adjacent to our territory, not ours
            candidates = set()
            for m in polity_members[pl]:
                for nb in adj[m]:
                    if leader[nb] != pl and nb not in absorbed_this_tick:
                        candidates.add(nb)
            if not candidates:
                continue

            # Score each candidate
            scored = []
            for target in candidates:
                ts_draw = _beta_sample(ts_a, ts_b, rng)
                rv = _resource_value(target, p_tech, substrate, c_remaining, p)
                # Distance: min from any member to target
                min_d = min(gc_mat[m][target] for m in polity_members[pl])
                score = ts_draw + p.resource_targeting_weight * rv - min_d * 2.0
                scored.append((score, target))

            scored.sort(key=lambda x: -x[0])

            # Track scramble onset
            if scramble_tick is None and p_tech >= 7.0:
                for sc, tgt in scored:
                    if c_remaining[tgt] > 0.1:
                        scramble_tick = tick
                        break

            # Absorb targets in priority order
            n_members = len(polity_members[pl])
            max_absorb = max(1, n_members // 5)   # imperial overstretch cap
            absorb_count = 0
            overstretch = 1.0 + n_members * 0.12  # expansion gets harder

            for score, target in scored:
                if absorb_count >= max_absorb:
                    break
                if target in absorbed_this_tick:
                    continue
                # Check: absorbing from another multi-arch polity requires tech gap
                target_ldr = leader[target]
                target_polity_sz = len(polity_members.get(target_ldr, []))
                conquest_mult = 1.0
                if target_polity_sz > 1:
                    tech_gap = p_tech - polity_tech.get(target_ldr, 0)
                    if tech_gap < 2.0:
                        continue   # can't conquer a peer polity
                    conquest_mult = 2.0  # military conquest is expensive
                # Cost to absorb — scales with polity size (overstretch)
                min_d = min(gc_mat[m][target] for m in polity_members[pl])
                cost = max(0.5, pop[target] * (0.3 + min_d * 0.5)) * overstretch * conquest_mult
                if budget < cost:
                    continue
                budget -= cost
                absorb_count += 1
                absorbed_this_tick.add(target)

                # Record expansion
                target_ldr_old = leader[target]
                target_tech_old = polity_tech.get(target_ldr_old, 0)
                expansion_log.append({
                    "tick": tick, "year": year, "absorber": pl, "target": target,
                    "absorber_tech": p_tech, "target_tech": target_tech_old,
                    "target_culture": _get_culture(target, substrate),
                    "c_at_target": c_remaining[target],
                    "pu_at_target": substrate[target]["minerals"].get("Pu", False),
                })

                # Epidemic shock — only on first contact for this arch
                if target not in epi_applied_to:
                    contactor_crop = substrate[pl]["crops"]["primary_crop"]
                    contacted_crop = substrate[target]["crops"]["primary_crop"]
                    cdist = _crop_distance(contactor_crop, contacted_crop)
                    severity = p.epi_base_severity + rng.next_float() * 0.1
                    pair = (contactor_crop, contacted_crop)
                    if pair in epi_exposed:
                        severity *= 0.3
                    epi_exposed.add(pair)
                    mortality = severity * cdist
                    pop[target] *= max(0.3, 1.0 - mortality)
                    epi_applied_to.add(target)
                    epi_log.append({
                        "arch": target, "tick": tick, "year": year,
                        "contactor_crop": contactor_crop, "contacted_crop": contacted_crop,
                        "mortality_rate": mortality,
                    })

                # Sovereignty drop
                sovereignty[target] = max(0.1, sovereignty[target] * 0.5)
                trade_integration[target] = min(1.0, trade_integration[target] + 0.3)

                # Perform absorption — merge capital from target's polity
                old_ldr = leader[target]
                polity_capital[pl] = polity_capital.get(pl, 0) + pop[target] * 0.3
                leader[target] = pl
                polity_members[pl].append(target)

                if target == old_ldr:
                    # Target was a polity leader
                    remaining = [m for m in polity_members.get(old_ldr, []) if m != target]
                    polity_members.pop(old_ldr, None)
                    if remaining:
                        new_ldr = max(remaining, key=lambda j: pop[j])
                        polity_members[new_ldr] = remaining
                        for m in remaining:
                            leader[m] = new_ldr
                        polity_tech[new_ldr]      = polity_tech.pop(old_ldr, 0)
                        polity_knowledge[new_ldr] = polity_knowledge.pop(old_ldr, 1.0)
                        polity_capital[new_ldr]   = polity_capital.pop(old_ldr, 0)
                        polity_posture[new_ldr]   = polity_posture.pop(old_ldr, _POSTURE_EXPLORE)
                    else:
                        polity_tech.pop(old_ldr, None)
                        polity_knowledge.pop(old_ldr, None)
                        polity_capital.pop(old_ldr, None)
                        polity_posture.pop(old_ldr, None)
                elif old_ldr in polity_members:
                    polity_members[old_ldr].remove(target)
                    if not polity_members[old_ldr]:
                        del polity_members[old_ldr]
                        polity_tech.pop(old_ldr, None)
                        polity_knowledge.pop(old_ldr, None)
                        polity_capital.pop(old_ldr, None)
                        polity_posture.pop(old_ldr, None)

        # ── Stage 7: TECH GROWTH (Solow-Romer) ──────────────────────────
        for pl in list(polity_members.keys()):
            tb = tech_budget.get(pl, 0)
            total_pop_p = polity_pop.get(pl, sum(pop[j] for j in polity_members[pl]))
            n_contacts = len(contacts.get(pl, set()))
            culture = _get_culture(pl, substrate)
            A0 = _get_A0(p, culture)
            er = polity_energy.get(pl, 1.0)
            tech_now = polity_tech.get(pl, 0)

            # delta_tech = scale × (tech_budget/pop) × A₀ × log₂(1+contacts) × energy_ratio / (1+tech)
            # Minimum 1 contact for internal development (knowledge doesn't stop in isolation)
            log_contacts = max(1.0, _log2(1.0 + n_contacts))
            delta = 0.5 * (tb / max(total_pop_p, 1.0)) * A0 * log_contacts * er / (1.0 + tech_now)

            # Pu dependency above nuclear threshold
            if tech_now + delta >= 9.0:
                has_pu = any(substrate[j]["minerals"].get("Pu", False)
                             for j in polity_members.get(pl, []))
                if not has_pu:
                    # Dependent path: slower tech growth, but still achievable
                    delta *= p.pu_dependent_factor

            polity_tech[pl] = tech_now + delta

        # ── Stage 8: SOVEREIGNTY DRIFT + C DEPLETION ─────────────────────
        for pl in list(polity_members.keys()):
            members = polity_members.get(pl, [])
            p_tech = polity_tech.get(pl, 0)
            er = polity_energy.get(pl, 1.0)

            for j in members:
                if j == pl:
                    continue
                # Extraction pressure
                dist = gc_mat[pl][j]
                pressure = (0.01 / max(dist, 0.05)) * min(1.0, er)
                recovery = p.sov_extraction_decay * sovereignty[j] * 0.1
                sovereignty[j] = _clamp(sovereignty[j] + recovery - pressure, 0.05, 1.0)

            # C depletion — only when tech >= 7 (industrial)
            if p_tech >= 7.0:
                for j in members:
                    if c_remaining[j] <= 0:
                        continue
                    depletion = pop[j] * p_tech * p.naphtha_depletion * 0.2
                    c_remaining[j] = max(0.0, c_remaining[j] - depletion)

        # ── Stage 9: SUBSTRATE DRIFT (knowledge + capital + pop growth) ──
        for pl in list(polity_members.keys()):
            members = polity_members.get(pl, [])
            n_contacts = len(contacts.get(pl, set()))
            culture = _get_culture(pl, substrate)
            A0 = _get_A0(p, culture)
            tb = tech_budget.get(pl, 0)
            cb = cons_budget.get(pl, 0)

            # Knowledge compounds from trade and research (diminishing returns)
            log_c = max(1.0, _log2(1.0 + n_contacts))
            dk = 0.01 * tb * A0 * log_c / (1.0 + polity_knowledge[pl])
            polity_knowledge[pl] = min(30.0, polity_knowledge[pl] + dk)

            # Capital from consolidation investment
            polity_capital[pl] += cb * 0.1
            polity_capital[pl] = max(1.0, polity_capital[pl])

            # Pop growth proportional to surplus per capita
            S = polity_surplus.get(pl, 0)
            total_pop_p = max(1.0, sum(pop[j] for j in members))
            growth = _clamp(S / total_pop_p * 0.005, -0.01, 0.03)
            for j in members:
                pop[j] *= (1.0 + growth)
                pop[j] = max(1.0, pop[j])

        # ── DARK FOREST CHECK ────────────────────────────────────────────
        if df_year is None:
            for p1 in list(polity_members.keys()):
                if polity_tech.get(p1, 0) < 9.0:
                    continue
                for p2 in list(polity_members.keys()):
                    if p2 == p1 or polity_tech.get(p2, 0) < 7.0:
                        continue
                    dist = gc_mat[p1][p2]
                    det1 = p.df_detection_range * (polity_tech[p1] / 10.0)
                    det2 = p.df_detection_range * (polity_tech.get(p2, 0) / 10.0)
                    if dist < max(det1, det2):
                        df_year = year
                        df_polity_a = p1
                        df_polity_b = p2
                        break
                if df_year is not None:
                    break

        # ── RECORD HISTORY (every 5 ticks) ───────────────────────────────
        if tick % 5 == 0:
            tech_history.append({
                "tick": tick, "year": year,
                "polities": {pl: round(polity_tech.get(pl, 0), 2)
                             for pl in polity_members},
            })
            c_history.append({"tick": tick, "year": year,
                              "c_total": round(sum(c_remaining), 3)})

    # ══════════════════════════════════════════════════════════════════════
    # POST-SIMULATION: Identify hegemons, compute fleet_scale, assemble
    # ══════════════════════════════════════════════════════════════════════

    # Hegemons: two largest polities by total population
    total_world_pop = sum(pop)
    polity_total_pop = {}
    for pl, members in polity_members.items():
        polity_total_pop[pl] = sum(pop[j] for j in members)

    hegemon_candidates = sorted(polity_total_pop.keys(),
                                key=lambda x: -polity_total_pop[x])
    hegemons = []
    for hc in hegemon_candidates[:2]:
        if polity_total_pop[hc] > total_world_pop * 0.10:
            hegemons.append(hc)

    # Fleet scale
    fleet_scale = {}
    for pl in polity_members:
        t = polity_tech.get(pl, 0)
        if t < 9.0:
            fleet_scale[pl] = 0.0
        else:
            has_pu = any(substrate[j]["minerals"].get("Pu", False)
                         for j in polity_members[pl])
            if has_pu:
                fleet_scale[pl] = 1.0   # full nuclear fleet
            else:
                fleet_scale[pl] = p.pu_dependent_factor  # dependent

    # Build output states array
    states = []
    for i in range(N):
        ldr = leader[i]
        h_label = "unknown"
        if len(hegemons) >= 1 and ldr == hegemons[0]:
            h_label = "hegemon_0"
        elif len(hegemons) >= 2 and ldr == hegemons[1]:
            h_label = "hegemon_1"
        elif ldr in polity_members:
            h_label = "minor"

        states.append({
            "controller":       ldr,
            "faction":          h_label,
            "culture_type":     _get_culture(ldr, substrate),
            "status":           "core" if i == ldr and i in polity_members else "controlled",
            "population":       round(pop[i]),
            "tech":             round(polity_tech.get(ldr, 0) * 10) / 10.0,
            "sovereignty":      round(sovereignty[i], 3),
            "tradeIntegration": round(trade_integration[i], 3),
            "c_remaining":      round(c_remaining[i], 4),
            "fleet_scale":      fleet_scale.get(ldr, 0.0),
            "eraOfContact":     None,
        })

    # Build polities summary
    polities_summary = []
    for pl in sorted(polity_members.keys(), key=lambda x: -polity_total_pop.get(x, 0)):
        members = polity_members[pl]
        has_pu = any(substrate[j]["minerals"].get("Pu", False) for j in members)
        polities_summary.append({
            "core":             pl,
            "culture_type":     _get_culture(pl, substrate),
            "crop":             substrate[pl]["crops"]["primary_crop"],
            "controlled_archs": list(members),
            "total_pop":        round(polity_total_pop.get(pl, 0)),
            "tech":             round(polity_tech.get(pl, 0), 2),
            "has_pu":           has_pu,
            "fleet_scale":      fleet_scale.get(pl, 0.0),
            "is_hegemon":       pl in hegemons,
            "knowledge":        round(polity_knowledge.get(pl, 1.0), 2),
            "energy_ratio":     round(polity_energy.get(pl, 1.0), 3) if pl in polity_energy else 1.0,
        })

    # Uncontacted count
    uncontacted = sum(1 for pl, ms in polity_members.items() if len(ms) == 1)

    return {
        "states":           states,
        "polities":         polities_summary,
        "df_year":          df_year,
        "df_polity_a":      df_polity_a,
        "df_polity_b":      df_polity_b,
        "epi_log":          epi_log,
        "expansion_log":    expansion_log,
        "substrate":        substrate,
        "archs":            archs,
        "plateau_edges":    plateau_edges,
        "hegemons":         hegemons,
        "fleet_scale":      fleet_scale,
        "polity_members":   {k: list(v) for k, v in polity_members.items()},
        "polity_tech":      dict(polity_tech),
        "c_total_initial":  c_initial_total,
        "c_total_final":    sum(c_remaining),
        "tech_history":     tech_history,
        "c_history":        c_history,
        "uncontacted":      uncontacted,
        "scramble_tick":    scramble_tick,
        "reach_arch":       world.get("reach_arch", 0),
        "lattice_arch":     world.get("lattice_arch", 1),
    }


# ---------------------------------------------------------------------------
# Verification entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import os
    import sys
    import time

    script_dir = os.path.dirname(os.path.abspath(__file__))
    world_path = os.path.join(script_dir, "worlds", "candidate_0216089.json")

    if not os.path.exists(world_path):
        print(f"ERROR: world file not found at {world_path}")
        sys.exit(1)

    world = load_godot_world(world_path)
    params = SimParams()

    t0 = time.perf_counter()
    result = simulate(world, params, seed=216089)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print("=" * 60)
    print(f"  SEED 216089 VERIFICATION — sim_proxy.py v2")
    print(f"  Elapsed: {elapsed_ms:.1f} ms")
    print("=" * 60)

    # Crop distribution
    from collections import Counter
    crops = Counter(s["crops"]["primary_crop"] for s in result["substrate"])
    print(f"\nCrop distribution: {dict(crops)}")
    cultures = Counter(_get_culture(i, result["substrate"]) for i in range(len(result["archs"])))
    print(f"Culture types: {dict(cultures)}")

    # Hegemons
    print(f"\nHegemons: {result['hegemons']}")
    for h in result["hegemons"]:
        pl = [p for p in result["polities"] if p["core"] == h][0]
        print(f"  Arch {h}: culture={pl['culture_type']}, crop={pl['crop']}, "
              f"tech={pl['tech']:.1f}, pop={pl['total_pop']}, "
              f"archs={len(pl['controlled_archs'])}, "
              f"fleet_scale={pl['fleet_scale']:.2f}, "
              f"has_pu={pl['has_pu']}, "
              f"knowledge={pl['knowledge']:.1f}, "
              f"energy_ratio={pl['energy_ratio']:.2f}")

    # Nuclear check
    nuclear_polities = [p for p in result["polities"] if p["tech"] >= 9.0]
    print(f"\nNuclear polities (tech >= 9.0): {len(nuclear_polities)}")
    for np_ in nuclear_polities:
        print(f"  Arch {np_['core']}: tech={np_['tech']:.1f}, "
              f"has_pu={np_['has_pu']}, fleet={np_['fleet_scale']:.2f}")

    # Dark Forest
    print(f"\nDark Forest break: {'YES' if result['df_year'] else 'NO'}")
    if result["df_year"]:
        print(f"  Year: {result['df_year']} BP, "
              f"polities: {result['df_polity_a']} vs {result['df_polity_b']}")

    # Naphtha
    c_init = result["c_total_initial"]
    c_final = result["c_total_final"]
    depletion_pct = 100 * (1 - c_final / max(c_init, 0.001))
    print(f"\nNaphtha: {c_init:.1f} → {c_final:.1f} ({depletion_pct:.0f}% depleted)")

    # Scramble
    if result["scramble_tick"] is not None:
        scramble_year = -5000 + result["scramble_tick"] * 50
        print(f"Naphtha scramble onset: tick {result['scramble_tick']} "
              f"(~{abs(scramble_year)} BP)")
    else:
        # Reference the constants for the print
        print("Naphtha scramble: not observed")

    # Expansion stats
    print(f"\nExpansion events: {len(result['expansion_log'])}")
    print(f"Active polities at story present: {len(result['polity_members'])}")
    print(f"Uncontacted archs: {result['uncontacted']}")

    # Tech trajectory for top 2 polities
    print(f"\nTech trajectory (sampled every 5 ticks):")
    for entry in result["tech_history"][-5:]:
        top2 = sorted(entry["polities"].items(), key=lambda x: -x[1])[:2]
        labels = " | ".join(f"arch {k}: {v:.1f}" for k, v in top2)
        print(f"  tick {entry['tick']:3d} (year {entry['year']:5d}): {labels}")

    # C depletion curve
    print(f"\nC depletion curve:")
    for entry in result["c_history"][::4]:
        bar = "#" * int(entry["c_total"] / max(c_init, 0.001) * 40)
        print(f"  tick {entry['tick']:3d}: {entry['c_total']:6.1f} {bar}")

    # Verification checklist
    print(f"\n{'=' * 60}")
    print("VERIFICATION CHECKLIST:")
    has_civic = "civic" in cultures
    print(f"  [{'✓' if has_civic else '—'}] Civic polity present (emmer crop)")
    if not has_civic:
        print(f"      NOTE: No emmer archs in seed 216089 — no Civic culture.")
        print(f"      All {cultures.get('parochial', 0)} parochial + {cultures.get('subject', 0)} subject.")
    naphtha_ok = any(p["tech"] >= 7.0 for p in result["polities"])
    print(f"  [{'✓' if naphtha_ok else '✗'}] Industrial tech (>=7) reached")
    nuclear_ok = len(nuclear_polities) >= 2
    print(f"  [{'✓' if nuclear_ok else '✗'}] Both hegemons nuclear (>=9)")
    df_ok = result["df_year"] is not None
    print(f"  [{'✓' if df_ok else '✗'}] Dark Forest breaks")
    c_ok = depletion_pct > 30
    print(f"  [{'✓' if c_ok else '✗'}] Significant naphtha depletion (>{30}%)")
    print("=" * 60)
