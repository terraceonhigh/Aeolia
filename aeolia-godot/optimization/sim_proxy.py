"""
Python port of history_engine.gd + substrate.gd for parameter optimization.

Mirrors history_engine.assign_politics() exactly, with all magic numbers
extracted into a SimParams dataclass so scipy.optimize / optuna can search
over them.  Produces the same output schema as the GDScript:

    result = simulate(world, params, seed=42)
    result["states"]   # list[dict] — per-arch, same keys as GDScript states[]
    result["df_year"]  # int|None
    result["epi_log"]  # list[dict] — per-contact mortality (extra; not in GDScript)

Usage
-----
    from sim_proxy import SimParams, DEFAULT_PARAMS, simulate, generate_test_world

    world  = generate_test_world(seed=42)
    result = simulate(world, DEFAULT_PARAMS, seed=42)

World dict format
-----------------
    {
        "archs": list[dict],          # {cx, cy, cz, peaks: [{h}], shelf_r}
        "plateau_edges": list[list],  # [[a, b], ...]
        "reach_arch": int,
        "lattice_arch": int,
        "substrate": list[dict],      # optional; computed if absent
    }
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
    """
    Mulberry32 deterministic PRNG.  Same seed → same world, always.
    Matches JS mulberry32 and GDScript RNG.gd implementations exactly.
    """

    def __init__(self, seed: int) -> None:
        self.state = seed & 0xFFFFFFFF

    @staticmethod
    def _imul(a: int, b: int) -> int:
        a &= 0xFFFFFFFF
        b &= 0xFFFFFFFF
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
        t       = self._imul(s ^ self._urs(s, 15), 1 | s)
        t_orig  = t
        t       = (t + self._imul(t ^ self._urs(t, 7), 61 | t)) ^ t_orig
        result  = (t ^ self._urs(t, 14)) & 0xFFFFFFFF
        return result / 4294967296.0


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

@dataclass
class SimParams:
    """
    All tunable coefficients in the Aeolia history engine.
    Default values match the current GDScript implementation (history_engine.gd).
    Bounds and priority notes from HISTORY_ENGINE_ANALYSIS.md.
    """

    # ── ERA 1: ANTIQUITY (−20,000 to −5,000 BP) ──────────────────────────
    # pop *= (1 + base_growth * potential)^30
    # Current: negligible spread (3–6% over 15 kyr). See ANALYSIS §2.
    antiquity_base_growth:        float = 0.002
    # Lattice paddi-surplus multiplier applied after antiquity growth.
    # Should ideally emerge from substrate; currently hardcoded. See ANALYSIS §2.
    antiquity_lattice_pop_mult:   float = 2.5
    antiquity_tech_floor_reach:   float = 3.5   # tech = max(tech, floor)
    antiquity_tech_floor_lattice: float = 3.8

    # ── ERA 2: SERIAL CONTACT (−5,000 to −2,000 BP) ──────────────────────
    # Epidemiological shock: mortality = base_severity × crop_distance
    # Current: base_severity = 0.20–0.45 (after ANALYSIS §3 correction)
    serial_shock_base_min:    float = 0.20
    serial_shock_base_range:  float = 0.25   # total range [min, min+range]
    # Trade recovery: pop *= 1 + trade_years × rate
    serial_trade_rate:        float = 0.0004
    # Core civilisation network-effect multipliers
    # Lore: Reach A₀=1.2, δ=0.08 → should compound FASTER per contact (higher log coeff)
    #        Lattice A₀=0.8, δ=0.04 → stable surplus, lower network scaling
    reach_serial_base_mult:   float = 1.3
    reach_serial_log_coeff:   float = 0.30   # MUST be > lattice_serial_log_coeff
    lattice_serial_base_mult: float = 1.9
    lattice_serial_log_coeff: float = 0.12   # MUST be < reach_serial_log_coeff

    # ── ERA 3: COLONIAL (−2,000 to −500 BP) ──────────────────────────────
    colonial_shock_base_min:   float = 0.20
    colonial_shock_base_range: float = 0.25
    extraction_base:           float = 0.15   # colony extraction rate (fraction of pop)
    extraction_per_year:       float = 0.0001  # extraction rate increase per year of colonisation
    garrison_absorb_base:      float = 0.15   # garrison demographic relocation fraction
    garrison_absorb_range:     float = 0.10
    reach_colony_surplus:      float = 0.12   # Reach pop bonus per colony (accumulated surplus)
    extracted_return_frac:     float = 0.60   # fraction of extracted pop flowing to Reach core
    lattice_garrison_bonus:    float = 0.15   # Lattice pop bonus per garrison (integration)
    lattice_trib_bonus:        float = 0.08   # Lattice pop bonus per tributary

    # ── ERA 4: INDUSTRIAL (−500 to −200 BP) ──────────────────────────────
    # Reach: higher tech leverage (A₀=1.2), lower resource leverage (β=0.5)
    # Lattice: lower tech leverage (A₀=0.8), higher resource leverage (β=0.6)
    # ANALYSIS §7 notes these were originally INVERTED — current values are corrected.
    reach_ind_tech_mult:     float = 0.12
    reach_ind_pot_mult:      float = 0.14
    reach_ind_log_coeff:     float = 0.14   # log₂(total_network) coefficient for Reach
    reach_ind_tech_growth:   float = 0.9    # tech += potential * this (Reach; δ=0.08 → fast)
    lattice_ind_tech_mult:   float = 0.06
    lattice_ind_pot_mult:    float = 0.22
    lattice_ind_log_coeff:   float = 0.10   # log₂(lattice_integrated) coefficient
    lattice_ind_tech_growth: float = 0.6    # tech += potential * this (Lattice; δ=0.04 → slow)
    tech_floor_reach_ind:    float = 7.0    # Reach minimum tech at end of industrial era
    tech_floor_lattice_ind:  float = 6.5    # Lattice minimum tech

    # ── ERA 4→5 SOVEREIGNTY DRIFT ─────────────────────────────────────────
    colony_sov_drift_mult:    float = 0.30    # extraction strain → sovereignty recovery
    client_sov_drift_per_yr:  float = 0.00005 # autonomy gain per year of client contact

    # ── ERA 5: NUCLEAR (−200 BP to present) ──────────────────────────────
    reach_nuclear_pop_mult:      float = 1.40
    lattice_nuclear_pop_mult:    float = 1.35
    nuclear_access_colony:       float = 0.70  # tech access for Reach colonies
    nuclear_access_garrison:     float = 0.50  # tech access for Lattice garrisons
    nuclear_access_independent:  float = 0.30  # tech access for unaligned archs
    nuclear_green_rev_prob:      float = 0.40  # Green Revolution probability
    nuclear_green_rev_mult_min:  float = 1.30  # min pop boost from Green Rev
    nuclear_green_rev_mult_range:float = 0.30  # range of Green Rev pop boost


DEFAULT_PARAMS = SimParams()

# Parameter definitions for the optimizer: (attr_name, lower_bound, upper_bound)
PARAM_BOUNDS: list = [
    ("antiquity_base_growth",         0.001,  0.010),
    ("antiquity_lattice_pop_mult",    1.50,   4.00),
    ("serial_shock_base_min",         0.10,   0.35),
    ("serial_shock_base_range",       0.10,   0.40),
    ("serial_trade_rate",             0.0001, 0.0010),
    ("reach_serial_base_mult",        0.80,   2.50),
    ("reach_serial_log_coeff",        0.10,   0.60),
    ("lattice_serial_base_mult",      1.20,   3.50),
    ("lattice_serial_log_coeff",      0.03,   0.30),
    ("extraction_base",               0.05,   0.35),
    ("extraction_per_year",           0.00,   0.0003),
    ("garrison_absorb_base",          0.05,   0.35),
    ("reach_colony_surplus",          0.05,   0.25),
    ("lattice_garrison_bonus",        0.05,   0.30),
    ("lattice_trib_bonus",            0.02,   0.20),
    ("reach_ind_tech_mult",           0.04,   0.25),
    ("reach_ind_pot_mult",            0.04,   0.30),
    ("reach_ind_log_coeff",           0.05,   0.30),
    ("reach_ind_tech_growth",         0.40,   1.80),
    ("lattice_ind_tech_mult",         0.02,   0.15),
    ("lattice_ind_pot_mult",          0.10,   0.40),
    ("lattice_ind_log_coeff",         0.03,   0.20),
    ("lattice_ind_tech_growth",       0.20,   1.30),
    ("tech_floor_reach_ind",          6.50,   7.50),
    ("tech_floor_lattice_ind",        6.00,   7.00),
    ("reach_nuclear_pop_mult",        1.10,   2.00),
    ("lattice_nuclear_pop_mult",      1.10,   2.00),
    ("nuclear_access_colony",         0.40,   0.90),
    ("nuclear_access_garrison",       0.25,   0.75),
    ("nuclear_access_independent",    0.10,   0.50),
]


def pack_params(p: SimParams) -> list:
    """Extract parameter values as a list matching PARAM_BOUNDS order."""
    return [getattr(p, name) for name, _, _ in PARAM_BOUNDS]


def unpack_params(x) -> SimParams:
    """Reconstruct SimParams from a parameter vector matching PARAM_BOUNDS order."""
    p = SimParams()
    for i, (name, lo, hi) in enumerate(PARAM_BOUNDS):
        setattr(p, name, float(x[i]))
    return p


def scipy_bounds():
    """Return bounds in scipy.optimize format: list of (lo, hi) tuples."""
    return [(lo, hi) for _, lo, hi in PARAM_BOUNDS]


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
# Substrate fast-path (simplified port of substrate.gd)
# ---------------------------------------------------------------------------

_ISLAND_MAX_HEIGHT = 3000.0
_RAINFALL_MULT     = 1.4     # Aeolia atmospheric multiplier (constants.gd)


def _compute_substrate_fast(archs: list, plateau_edges: list, seed: int) -> list:
    """
    Compute per-arch primary_crop, primary_yield, trade value, and climate.
    Simplified port of substrate.gd: skips gyre model, uses uniform ocean warmth.
    Sufficient for optimisation; use the GDScript version for rendering.
    """
    rng = Mulberry32((seed if seed > 0 else 42) * 47 + 2024)
    n   = len(archs)

    edge_count   = [0] * n
    edge_lengths = [[] for _ in range(n)]
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        edge_count[a] += 1
        edge_count[b] += 1
        dot = (archs[a]["cx"] * archs[b]["cx"] +
               archs[a]["cy"] * archs[b]["cy"] +
               archs[a]["cz"] * archs[b]["cz"])
        dot = max(-1.0, min(1.0, dot))
        ang = math.acos(dot)
        edge_lengths[a].append(ang)
        edge_lengths[b].append(ang)

    substrates = []
    for i, arch in enumerate(archs):
        cy      = max(-1.0, min(1.0, arch["cy"]))
        lat     = math.asin(cy) * 180.0 / math.pi
        abs_lat = abs(lat)

        if   abs_lat < 12: wind_belt = "doldrums"
        elif abs_lat < 28: wind_belt = "trades"
        elif abs_lat < 35: wind_belt = "subtropical"
        elif abs_lat < 55: wind_belt = "westerlies"
        elif abs_lat < 65: wind_belt = "subpolar"
        else:              wind_belt = "polar"

        base_rain = {
            "doldrums":   2800.0,
            "trades":     2200.0,
            "subtropical": 600.0,
            "westerlies": 1400.0,
            "subpolar":   1100.0,
            "polar":       300.0,
        }[wind_belt]

        peaks   = arch.get("peaks", [])
        avg_h   = (sum(p["h"] for p in peaks) / (len(peaks) * _ISLAND_MAX_HEIGHT)
                   if peaks else 0.0)
        orographic = 1.0 + avg_h * 1.8
        effective_rainfall = base_rain * orographic * _RAINFALL_MULT

        mean_temp      = 28.0 - abs_lat * 0.45
        seasonal_range = abs_lat * 0.15 * 0.7

        shelf_r    = arch.get("shelf_r", 0.06)
        tidal_range = 2.0 + shelf_r * 30.0

        upwelling = edge_count[i] * 0.08

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
            # Tidal-hydraulic bonus: extreme tidal range enables terrace dike systems
            # that allow paddi to outcompete sago in high-rainfall equatorial zones.
            # The full GDScript model achieves this implicitly through the gyre model
            # (eastern gyre arches get less moisture, favouring paddi over sago).
            # Without the gyre, we apply a direct bonus when tidal_range > 5 m so that
            # the Lattice's paddi agriculture emerges correctly from its wide shelf.
            # At tidal_range = 6.2 (shelf_r=0.14): bonus = 0.53 → paddi yield ≈ 5.1 > sago 4.0
            tidal_bonus = min(1.0, max(0.0, (tidal_range - 2.0) / 8.0))
            yields["paddi"] = (5.0
                * min(1.0, (mean_temp - 18.0) / 15.0)
                * min(1.0, effective_rainfall / 1800.0)
                * min(1.0, tidal_range / 5.0)
                * (1.0 + tidal_bonus))
        if can_grow["emmer"]:
            yields["emmer"] = (2.5
                * (1.0 - abs(mean_temp - 16.0) / 20.0)
                * (1.0 - abs(effective_rainfall - 700.0) / 1500.0))
        if can_grow["taro"]:
            yields["taro"] = (3.0
                * min(1.0, (mean_temp - 20.0) / 8.0)
                * min(1.0, effective_rainfall / 2000.0))
        if can_grow["nori"]:
            yields["nori"] = (1.5
                * min(1.0, upwelling * 2.0)
                * min(1.0, edge_count[i] / 3.0) * 2.0)
        if can_grow["sago"]:
            yields["sago"] = (4.0
                * min(1.0, effective_rainfall / 2500.0)
                * min(1.0, shelf_r / 0.10))
        if can_grow["papa"]:
            yields["papa"] = (3.5
                * (1.0 - abs(mean_temp - 12.0) / 15.0)
                * min(1.0, effective_rainfall / 600.0))

        if yields:
            primary_crop  = max(yields, key=yields.get)
            primary_yield = yields[primary_crop]
            ranked        = sorted(yields.items(), key=lambda kv: -kv[1])
            secondary_crop = ranked[1][0] if len(ranked) > 1 else None
        else:
            primary_crop   = "foraging"
            primary_yield  = 0.5
            secondary_crop = None

        # Trade value: simplified normalisation to [0, 1]
        total_trade_value = min(1.0, primary_yield / 5.0)

        substrates.append({
            "crops": {
                "primary_crop":   primary_crop,
                "secondary_crop": secondary_crop,
                "primary_yield":  primary_yield,
                "can_grow":       can_grow,
            },
            "climate": {
                "latitude":            lat,
                "abs_latitude":        abs_lat,
                "wind_belt":           wind_belt,
                "mean_temp":           mean_temp,
                "effective_rainfall":  effective_rainfall,
                "tidal_range":         tidal_range,
                "upwelling":           upwelling,
            },
            "trade_goods": {
                "total_trade_value": total_trade_value,
            },
        })

    return substrates


# ---------------------------------------------------------------------------
# Edge cost helpers (mirrors _edge_cost / _base_era_cost in history_engine.gd)
# ---------------------------------------------------------------------------

_ERA_BOUNDS = [-500, -200]


def _base_era_cost(year: int, hops: int, power: str) -> int:
    is_garrison = power == "lattice" and hops <= 3
    if year < -500:
        if is_garrison:    return 167
        if power == "lattice": return 12000
        if hops <= 1:      return 350
        if hops <= 2:      return 580
        if hops <= 3:      return 1060
        return 8000
    elif year < -200:
        if is_garrison:    return 85
        if power == "lattice": return 350 if hops <= 5 else 700
        if hops <= 4:      return 125
        if hops <= 6:      return 145
        return 200
    else:
        return 61


def _edge_cost(year: int, hops: int, power: str) -> int:
    cost = _base_era_cost(year, hops, power)
    for b in _ERA_BOUNDS:
        if year < b < year + cost:
            alt = (b - year + 1) + _base_era_cost(b + 1, hops, power)
            if alt < cost:
                return alt
    return cost


# ---------------------------------------------------------------------------
# World generator — produces synthetic test worlds for optimisation
# ---------------------------------------------------------------------------

def _generate_plateau_edges(archs: list) -> list:
    """
    Connect nearest neighbours (≥2 per arch) plus all pairs within MAX_EDGE_ANGLE.
    Mirrors world_generator.gd / MONOLITH_REFERENCE.jsx plateau edge generation.
    """
    n       = len(archs)
    MAX_ANG = 0.9   # radians (~26 000 km)

    angles: dict = {}
    for i in range(n):
        for j in range(i + 1, n):
            dot = (archs[i]["cx"] * archs[j]["cx"] +
                   archs[i]["cy"] * archs[j]["cy"] +
                   archs[i]["cz"] * archs[j]["cz"])
            dot = max(-1.0, min(1.0, dot))
            angles[(i, j)] = math.acos(dot)

    edges = set()
    # Guarantee MIN_NEIGHBORS = 2
    for i in range(n):
        by_dist = sorted(
            [j for j in range(n) if j != i],
            key=lambda j: angles[(min(i, j), max(i, j))],
        )
        for j in by_dist[:2]:
            edges.add((min(i, j), max(i, j)))

    # Threshold pass
    for (i, j), ang in angles.items():
        if ang <= MAX_ANG:
            edges.add((i, j))

    return [list(e) for e in sorted(edges)]


def _find_arch(archs: list, lat_min: float, lat_max: float, exclude: list = None) -> int:
    """Return index of the arch with the largest shelf_r in a latitude band."""
    exclude = exclude or []
    best_i, best_sz = None, -1.0
    for i, arch in enumerate(archs):
        if i in exclude:
            continue
        cy  = max(-1.0, min(1.0, arch["cy"]))
        lat = math.asin(cy) * 180.0 / math.pi
        if lat_min <= lat <= lat_max and arch["shelf_r"] > best_sz:
            best_i  = i
            best_sz = arch["shelf_r"]
    return best_i if best_i is not None else (0 if 0 not in exclude else 1)


def generate_test_world(seed: int = 42, n_archs: int = 42) -> dict:
    """
    Generate a synthetic test world for optimisation.

    Uses Fibonacci spiral placement + jitter, then overrides the Reach and
    Lattice archs with lore-mandated geographies:

      Reach   — northern westerlies (25–55°N), 14 spread peaks, wide shelf
      Lattice — southern tropics (5–25°S), 22 dense peaks, widest tidal shelf

    Returns
    -------
    dict with keys: archs, plateau_edges, reach_arch, lattice_arch, substrate
    """
    rng = Mulberry32(seed * 31 + 7)
    phi = math.pi * (3.0 - math.sqrt(5.0))  # golden angle

    archs = []
    for i in range(n_archs):
        y     = 1.0 - (i / max(n_archs - 1, 1)) * 2.0
        theta = phi * i
        y     += (rng.next_float() - 0.5) * 0.15
        theta += (rng.next_float() - 0.5) * 0.40
        y     = max(-0.98, min(0.98, y))
        r     = math.sqrt(max(0.0, 1.0 - y * y))
        x     = math.cos(theta) * r
        z     = math.sin(theta) * r
        norm  = math.sqrt(x * x + y * y + z * z) or 1.0
        cx, cy, cz = x / norm, y / norm, z / norm

        rv = rng.next_float()
        if rv < 0.15:        # large
            shelf_r = 0.10 + rng.next_float() * 0.10
            n_peaks = int(8  + rng.next_float() * 14)
        elif rv < 0.40:      # medium
            shelf_r = 0.06 + rng.next_float() * 0.06
            n_peaks = int(4  + rng.next_float() * 6)
        else:                # small
            shelf_r = 0.03 + rng.next_float() * 0.04
            n_peaks = int(1  + rng.next_float() * 4)

        peaks = [{"h": 500.0 + rng.next_float() * 2500.0} for _ in range(max(1, n_peaks))]
        archs.append({"cx": cx, "cy": cy, "cz": cz, "shelf_r": shelf_r, "peaks": peaks})

    # Override Reach: subtropical band (28–34°N) with short peaks.
    # Emmer requires effective_rainfall ≤ 2000 mm.
    #   Subtropical base rain = 600 mm; after Aeolia ×1.4 and orographic
    #   enhancement from ~400 m peaks → ~1100 mm effective, well within emmer range.
    #   Papa cannot grow here (requires abs_lat ≥ 35), so emmer wins uncontested.
    #   Westerlies (lat > 35°) would give base rain 1400 mm → ~2800 mm effective
    #   with any peaks, blowing past the emmer ceiling — so we cap at lat 34°.
    reach_arch = _find_arch(archs, lat_min=28.0, lat_max=34.0)
    if reach_arch is None or reach_arch == 0 and len(archs) > 1:
        # Fallback: expand to full subtropical + low-westerlies
        reach_arch = _find_arch(archs, lat_min=25.0, lat_max=38.0) or 0
    archs[reach_arch]["shelf_r"] = max(archs[reach_arch]["shelf_r"], 0.10)
    # Short peaks (200–600 m) keep effective rainfall inside emmer's 400–2000 mm window
    archs[reach_arch]["peaks"]   = [{"h": 200.0 + rng.next_float() * 400.0} for _ in range(14)]

    # Override Lattice: equatorial zone (4–13°S).
    # Paddi requires mean_temp ≥ 20°C → abs_lat ≤ 17.8° in this model.
    # Sago requires abs_lat ≤ 15°; placing at 4–13°S keeps sago in competition,
    # but the tidal-hydraulic paddi yield bonus (added in _compute_substrate_fast)
    # ensures paddi wins when shelf_r ≥ 0.14 (tidal_range ≥ 6.2 m).
    # Nori is excluded at mean_temp > 22°C (abs_lat < 13.3°), so the range 4–13°S
    # also avoids nori competition.
    lattice_arch = _find_arch(archs, lat_min=-13.0, lat_max=-4.0, exclude=[reach_arch])
    if lattice_arch is None or lattice_arch == reach_arch:
        lattice_arch = _find_arch(archs, lat_min=-17.0, lat_max=-3.0, exclude=[reach_arch]) or 1
    archs[lattice_arch]["shelf_r"] = max(archs[lattice_arch]["shelf_r"], 0.14)
    # Low-medium peaks: keep temp hot (paddi) and rainfall in paddi range
    archs[lattice_arch]["peaks"]   = [{"h": 150.0  + rng.next_float() * 500.0} for _ in range(22)]

    plateau_edges = _generate_plateau_edges(archs)
    substrate     = _compute_substrate_fast(archs, plateau_edges, seed)

    return {
        "archs":         archs,
        "plateau_edges": plateau_edges,
        "reach_arch":    reach_arch,
        "lattice_arch":  lattice_arch,
        "substrate":     substrate,
    }


# ---------------------------------------------------------------------------
# Core simulation — Python port of history_engine.assign_politics
# ---------------------------------------------------------------------------

def _log2(x: float) -> float:
    return math.log2(x) if x > 0.0 else 0.0


def simulate(
    world: dict,
    params: SimParams = DEFAULT_PARAMS,
    seed: int = 42,
) -> dict:
    """
    Run the Aeolia history engine with the given parameters.

    Parameters
    ----------
    world  : dict — output of generate_test_world() or a JSON export from Godot
    params : SimParams — tunable coefficients
    seed   : int — world seed for deterministic RNG

    Returns
    -------
    dict with keys:
      states      — per-arch final state (same schema as GDScript)
      log         — history log entries
      df_year     — year Dark Forest broke (negative BP) or None
      df_arch     — arch index where contact detected
      df_detector — "reach" or "lattice"
      reach_arch  — index of Reach core
      lattice_arch— index of Lattice core
      epi_log     — per-contact mortality records (not in GDScript output)
      substrate   — substrate used (from world or recomputed)
    """
    archs         = world["archs"]
    plateau_edges = world["plateau_edges"]
    reach_arch    = world["reach_arch"]
    lattice_arch  = world["lattice_arch"]
    substrate     = world.get("substrate") or _compute_substrate_fast(archs, plateau_edges, seed)

    rng = Mulberry32((seed if seed != 0 else 42) * 31 + 1066)
    N   = len(archs)

    R_START = -5500
    L_START = -5000

    # Build adjacency
    adj = [[] for _ in range(N)]
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        adj[a].append(b)
        adj[b].append(a)

    # BFS distances (used for log/display only)
    def bfs_dist(start):
        dist = [999] * N
        dist[start] = 0
        q = [start]
        while q:
            u = q.pop(0)
            for v in adj[u]:
                if dist[v] > dist[u] + 1:
                    dist[v] = dist[u] + 1
                    q.append(v)
        return dist

    r_dist = bfs_dist(reach_arch)
    l_dist = bfs_dist(lattice_arch)

    # Resource potential
    potential = []
    for i, arch in enumerate(archs):
        p    = len(arch.get("peaks", []))
        sz   = arch.get("shelf_r", 0.06) / 0.12
        avg_h = 0.0
        if p > 0:
            avg_h = sum(pk["h"] for pk in arch["peaks"]) / (p * _ISLAND_MAX_HEIGHT)
        pot = (p / 20.0 * 0.4 + avg_h * 0.3 + sz / 2.2 * 0.3) * (0.6 + rng.next_float() * 0.4)
        potential.append(pot)

    # ── PHASE 1: DIJKSTRA WAVEFRONT ──────────────────────────────────────
    claimed    = [None] * N
    arrival_yr = [None] * N
    hop_count  = [0]    * N
    parent_arch= [-1]   * N

    claimed[reach_arch]   = "reach"
    arrival_yr[reach_arch] = R_START
    claimed[lattice_arch]  = "lattice"
    arrival_yr[lattice_arch] = L_START

    df_year = df_arch = df_detector = df_target = None

    # heap entries: (year, tie_idx, arch_idx, power, hops, from_arch)
    counter = 0
    pq = []
    for nb in adj[reach_arch]:
        cost = _edge_cost(R_START, 1, "reach")
        heapq.heappush(pq, (R_START + cost, counter, nb, "reach", 1, reach_arch))
        counter += 1
    for nb in adj[lattice_arch]:
        cost = _edge_cost(L_START, 1, "lattice")
        heapq.heappush(pq, (L_START + cost, counter, nb, "lattice", 1, lattice_arch))
        counter += 1

    while pq:
        year, _, idx, power, hops, from_a = heapq.heappop(pq)

        if claimed[idx] is not None:
            if claimed[idx] != power and df_year is None:
                df_year     = year
                df_arch     = idx
                df_detector = power
                df_target   = claimed[idx]
            continue

        claimed[idx]    = power
        arrival_yr[idx] = year
        hop_count[idx]  = hops
        parent_arch[idx]= from_a

        for nb in adj[idx]:
            if claimed[nb] is not None and claimed[nb] != power and df_year is None:
                df_year     = year
                df_arch     = idx
                df_detector = power
                df_target   = claimed[nb]

        for nb in adj[idx]:
            if claimed[nb] is not None:
                continue
            cost = _edge_cost(year, hops + 1, power)
            heapq.heappush(pq, (year + cost, counter, nb, power, hops + 1, idx))
            counter += 1

    # ── PHASE 2: Σ2ⁿ REDISTRIBUTION ─────────────────────────────────────
    contactable = [i for i in range(N)
                   if claimed[i] and i != reach_arch and i != lattice_arch]
    # Stable sort by arrival_yr with index tiebreaker
    contactable.sort(key=lambda i: (arrival_yr[i], i))
    nc = len(contactable)

    serial_n   = max(1, round(nc * 0.05))
    colonial_n = max(1, round(nc * 0.10))
    industrial_n = max(2, round(nc * 0.20))
    nuclear_n    = max(2, round(nc * 0.40))
    total_slots  = serial_n + colonial_n + industrial_n + nuclear_n

    for k, i in enumerate(contactable):
        if k < serial_n:
            arrival_yr[i] = -5000 + round((k + 1) / (serial_n + 1) * 3000.0)
        elif k < serial_n + colonial_n:
            j = k - serial_n
            arrival_yr[i] = -2000 + round((j + 1) / (colonial_n + 1) * 1500.0)
        elif k < serial_n + colonial_n + industrial_n:
            j = k - serial_n - colonial_n
            arrival_yr[i] = -500 + round((j + 1) / (industrial_n + 1) * 300.0)
        elif k < total_slots:
            j     = k - serial_n - colonial_n - industrial_n
            df_off = abs(df_year) if df_year is not None else 200
            arrival_yr[i] = -200 + round(
                (j + 1) / (nuclear_n + 1) * min(200.0, float(df_off - 200))
            )
        else:
            claimed[i]    = None
            arrival_yr[i] = None

    # Recompute DF year after redistribution
    df_year = df_arch = df_detector = df_target = None
    for i in range(N):
        if not claimed[i]:
            continue
        for nb in adj[i]:
            if claimed[nb] and claimed[nb] != claimed[i]:
                yr = max(arrival_yr[i], arrival_yr[nb])
                if df_year is None or yr < df_year:
                    df_year     = yr
                    df_arch     = i
                    df_detector = claimed[i]
                    df_target   = claimed[nb]

    # Null post-DF claims
    for i in range(N):
        if arrival_yr[i] is not None and df_year is not None and arrival_yr[i] > df_year:
            claimed[i]    = None
            arrival_yr[i] = None

    # ── PHASE 3: STATUS ASSIGNMENT ───────────────────────────────────────
    sovereign   = [-1]   * N
    colony_yr   = [None] * N
    status_data = [
        {"sovereignty": 1.0, "tradeIntegration": 0.0, "status": "uncontacted", "eraOfContact": None}
        for _ in range(N)
    ]

    for i in range(N):
        if i == reach_arch or i == lattice_arch:
            status_data[i] = {
                "sovereignty": 1.0, "tradeIntegration": 1.0,
                "status": "core", "eraOfContact": None,
            }
            continue

        yr    = arrival_yr[i]
        power = claimed[i]
        hops  = hop_count[i]

        if not yr or not power:
            continue

        era = ("sail" if yr < -2000 else
               "colonial" if yr < -500 else
               "industrial" if yr < -200 else "nuclear")
        status_data[i]["eraOfContact"] = era

        if power == "reach":
            if hops <= 3 and era != "nuclear":
                sovereign[i]  = reach_arch
                colony_yr[i]  = yr + int(100 + rng.next_float() * 300)
                status_data[i] = {"sovereignty": 0.15, "tradeIntegration": 0.85,
                                   "status": "colony", "eraOfContact": era}
            elif hops <= 5 and era != "nuclear":
                status_data[i] = {"sovereignty": 0.55, "tradeIntegration": 0.60,
                                   "status": "client", "eraOfContact": era}
            else:
                status_data[i] = {"sovereignty": 0.90, "tradeIntegration": 0.20,
                                   "status": "contacted", "eraOfContact": era}
        else:  # lattice
            if hops <= 3:
                sovereign[i] = lattice_arch
                colony_yr[i] = yr + 200
                status_data[i] = {"sovereignty": 0.30, "tradeIntegration": 0.50,
                                   "status": "garrison", "eraOfContact": era}
            elif hops <= 5:
                status_data[i] = {"sovereignty": 0.60, "tradeIntegration": 0.40,
                                   "status": "tributary", "eraOfContact": era}
            else:
                status_data[i] = {"sovereignty": 0.90, "tradeIntegration": 0.15,
                                   "status": "pulse", "eraOfContact": era}

    # ── PHASE 4: POPULATION MODEL ─────────────────────────────────────────

    pop  = []
    tech = []
    for i, arch in enumerate(archs):
        p    = len(arch.get("peaks", []))
        sz   = arch.get("shelf_r", 0.06) / 0.12
        base = float(p) * sz * (3.0 + rng.next_float() * 4.0)
        pop.append(base)
        tech.append(0.0)

    log      = []
    epi_log  = []
    p        = params

    # -- ERA 1: ANTIQUITY --
    log.append({"arch": -1, "name": "═══ ANTIQUITY", "faction": "era",
                "label": "20,000–5,000 BP · Independent development", "contactYr": -20000})
    for i in range(N):
        pop[i]  *= (1.0 + p.antiquity_base_growth * potential[i]) ** 30
        tech[i]  = potential[i] * (2.5 + rng.next_float() * 1.5)

    tech[reach_arch]   = max(tech[reach_arch],   p.antiquity_tech_floor_reach)
    tech[lattice_arch] = max(tech[lattice_arch], p.antiquity_tech_floor_lattice)
    pop[lattice_arch] *= p.antiquity_lattice_pop_mult

    # -- ERA 2: SERIAL CONTACT --
    log.append({"arch": -1, "name": "═══ SERIAL CONTACT", "faction": "era",
                "label": "5,000–2,000 BP · Gap crossings · Epidemiological shock",
                "contactYr": -5000})

    reach_network = lattice_network = 0

    for i in range(N):
        if i == reach_arch or i == lattice_arch:
            continue
        yr    = arrival_yr[i]
        power = claimed[i]
        if yr is not None and yr >= -5000 and yr < -2000:
            contactor_crop = "emmer" if power == "reach" else "paddi"
            contacted_crop = substrate[i]["crops"]["primary_crop"]
            dist           = _crop_distance(contactor_crop, contacted_crop)
            base_sev       = p.serial_shock_base_min + rng.next_float() * p.serial_shock_base_range
            mortality      = base_sev * dist
            shock          = 1.0 - mortality
            pop[i]        *= shock

            epi_log.append({
                "arch":           i,
                "contactor_crop": contactor_crop,
                "contacted_crop": contacted_crop,
                "mortality_rate": mortality,
                "era":            "sail",
            })

            trade_years = max(0, -2000 - yr)
            pop[i]     *= 1.0 + float(trade_years) * p.serial_trade_rate
            tech[i]    += 0.5 + rng.next_float() * 0.5

            if power == "reach":
                reach_network  += 1
            else:
                lattice_network += 1

            log.append({
                "arch": i, "name": f"arch_{i}", "faction": power,
                "status": status_data[i]["status"],
                "label": f"Contacted ~{abs(yr)} BP · {round(mortality*100)}% mortality "
                         f"({contactor_crop}/{contacted_crop})",
                "contactYr": yr,
            })
        elif yr is None or yr >= -2000:
            pop[i] *= 1.0 + 0.001 * potential[i] * 30.0

    # Reach: higher log₂ coefficient — knowledge compounds faster per contact (δ=0.08)
    pop[reach_arch]   *= p.reach_serial_base_mult   * (1.0 + _log2(1.0 + reach_network)   * p.reach_serial_log_coeff)
    tech[reach_arch]   = min(6.0, tech[reach_arch]  + 1.2)
    # Lattice: larger base (paddi surplus), lower log₂ coefficient — stable surplus (δ=0.04)
    pop[lattice_arch] *= p.lattice_serial_base_mult * (1.0 + _log2(1.0 + lattice_network) * p.lattice_serial_log_coeff)
    tech[lattice_arch] = min(6.0, tech[lattice_arch] + 1.0)

    # -- ERA 3: COLONIAL EMPIRES --
    log.append({"arch": -1, "name": "═══ COLONIAL EMPIRES", "faction": "era",
                "label": "2,000–500 BP · Pearl-strings · Extraction · Garrison absorption",
                "contactYr": -2000})

    reach_colonies = lattice_garrisons = lattice_tribs = 0
    total_extracted = total_enslaved = 0.0
    extraction_rate_for = [0.0] * N

    for i in range(N):
        if i == reach_arch or i == lattice_arch:
            continue
        yr    = arrival_yr[i]
        power = claimed[i]
        sd    = status_data[i]
        if yr is None:
            continue

        if yr < -500:
            if sd["status"] == "colony":
                col_years = max(0, -500 - (colony_yr[i] if colony_yr[i] else yr))
                exrate    = p.extraction_base + col_years * p.extraction_per_year
                extraction_rate_for[i] = exrate
                extracted  = pop[i] * exrate
                pop[i]    -= extracted
                total_extracted += extracted
                enslaved   = pop[i] * (0.05 + rng.next_float() * 0.10)
                pop[i]    -= enslaved
                total_enslaved += enslaved
                pop[i]    += 8.0 + rng.next_float() * 15.0
                reach_colonies += 1

            elif sd["status"] == "garrison":
                absorbed        = pop[i] * (p.garrison_absorb_base + rng.next_float() * p.garrison_absorb_range)
                pop[i]         -= absorbed
                pop[lattice_arch] += absorbed
                lattice_garrisons += 1

            elif sd["status"] == "tributary":
                tribute = pop[i] * (0.05 + rng.next_float() * 0.05)
                pop[lattice_arch] += tribute
                lattice_tribs += 1

            elif sd["status"] == "client":
                pop[i]  *= 1.0 + _log2(1.0 + reach_network) * 0.10
                tech[i] += 0.3 + rng.next_float() * 0.3

        # New contacts in colonial era
        if yr >= -2000 and yr < -500:
            contactor_crop2 = "emmer" if power == "reach" else "paddi"
            contacted_crop2 = substrate[i]["crops"]["primary_crop"]
            dist2           = _crop_distance(contactor_crop2, contacted_crop2)
            base_sev2       = p.colonial_shock_base_min + rng.next_float() * p.colonial_shock_base_range
            mortality2      = base_sev2 * dist2
            shock2          = 1.0 - mortality2
            pop[i]         *= shock2
            tech[i]        += 0.3

            epi_log.append({
                "arch":           i,
                "contactor_crop": contactor_crop2,
                "contacted_crop": contacted_crop2,
                "mortality_rate": mortality2,
                "era":            "colonial",
            })

            if power == "reach":
                reach_network  += 1
            else:
                lattice_network += 1

    pop[reach_arch]   *= 1.0 + reach_colonies * p.reach_colony_surplus
    pop[reach_arch]   += total_extracted * p.extracted_return_frac + total_enslaved
    lattice_integrated = lattice_garrisons + lattice_tribs
    pop[lattice_arch] *= 1.0 + lattice_garrisons * p.lattice_garrison_bonus + lattice_tribs * p.lattice_trib_bonus

    for i in range(N):
        if claimed[i] or i == reach_arch or i == lattice_arch:
            continue
        pop[i]  *= 1.0 + 0.0005 * potential[i] * 15.0
        tech[i]  = min(4.0, tech[i] + potential[i] * 0.1)

    # -- ERA 4: INDUSTRIAL --
    log.append({"arch": -1, "name": "═══ INDUSTRIAL", "faction": "era",
                "label": "500–200 BP · Steam · Asymmetric industrialisation",
                "contactYr": -500})

    total_network = reach_network + lattice_network

    for i in range(N):
        if i == reach_arch:
            # A₀=1.2, δ=0.08: faster knowledge compounding
            pop[i]  *= ((1.0 + tech[i] * p.reach_ind_tech_mult + potential[i] * p.reach_ind_pot_mult) *
                        (1.0 + _log2(1.0 + total_network) * p.reach_ind_log_coeff))
            tech[i]  = min(8.0, tech[i] + potential[i] * p.reach_ind_tech_growth)
            continue

        if i == lattice_arch:
            # A₀=0.8, β=0.6: lower tech leverage, higher resource leverage
            pop[i]  *= ((1.0 + tech[i] * p.lattice_ind_tech_mult + potential[i] * p.lattice_ind_pot_mult) *
                        (1.0 + _log2(1.0 + lattice_integrated) * p.lattice_ind_log_coeff))
            tech[i]  = min(8.0, tech[i] + potential[i] * p.lattice_ind_tech_growth)
            continue

        if not claimed[i]:
            pop[i]  *= 1.0 + 0.0003 * potential[i] * 6.0
            tech[i]  = min(4.5, tech[i] + potential[i] * 0.05)
            continue

        if sovereign[i] >= 0:
            pop[i]  *= 1.0 + tech[i] * 0.03 + potential[i] * 0.05
            tech[i]  = min(6.0, tech[i] + potential[i] * 0.3)
        else:
            pop[i]  *= 1.0 + tech[i] * 0.08 + potential[i] * 0.12
            tech[i]  = min(7.5, tech[i] + potential[i] * 0.7)

        yr = arrival_yr[i]
        if yr is not None and yr >= -500 and yr < -200:
            pop[i] *= 0.5 + rng.next_float() * 0.3

    tech[reach_arch]   = max(tech[reach_arch],   p.tech_floor_reach_ind)
    tech[lattice_arch] = max(tech[lattice_arch], p.tech_floor_lattice_ind)

    # -- ERA 4→5 SOVEREIGNTY DRIFT --
    for i in range(N):
        if not claimed[i] or i == reach_arch or i == lattice_arch:
            continue
        sd = status_data[i]
        if sd["status"] == "colony":
            sd["sovereignty"] = min(0.50, sd["sovereignty"] +
                                    extraction_rate_for[i] * p.colony_sov_drift_mult)
        elif sd["status"] == "client":
            contact_age = max(0, -500 - (arrival_yr[i] if arrival_yr[i] else -500))
            sd["sovereignty"] = min(0.85, sd["sovereignty"] +
                                    contact_age * p.client_sov_drift_per_yr)

    # -- ERA 5: NUCLEAR --
    log.append({"arch": -1, "name": "═══ NUCLEAR THRESHOLD", "faction": "era",
                "label": "200 BP–present · Reactor seaplanes · Post-colonial recovery",
                "contactYr": -200})

    pop[reach_arch]   *= p.reach_nuclear_pop_mult
    tech[reach_arch]   = 10.0
    pop[lattice_arch] *= p.lattice_nuclear_pop_mult
    tech[lattice_arch] = 9.5

    for i in range(N):
        if i == reach_arch or i == lattice_arch:
            continue
        if not claimed[i]:
            continue
        if sovereign[i] == reach_arch:
            access = p.nuclear_access_colony
        elif sovereign[i] == lattice_arch:
            access = p.nuclear_access_garrison
        else:
            access = p.nuclear_access_independent

        if sovereign[i] >= 0 and rng.next_float() < p.nuclear_green_rev_prob:
            pop[i] *= p.nuclear_green_rev_mult_min + rng.next_float() * p.nuclear_green_rev_mult_range

        pop[i]  *= 1.0 + access * 0.2
        tech[i]  = min(10.0, tech[i] + access)

    # ── POST-NUCLEAR SOVEREIGNTY RECOVERY ──
    # Matches history_engine.gd lines 631-643 exactly.
    # Post-colonial autonomy: sovereignty rises toward self-determination.
    for i in range(N):
        if not claimed[i] or i == reach_arch or i == lattice_arch:
            continue
        sd5 = status_data[i]
        if sd5["status"] == "colony":
            sd5["sovereignty"]      = min(0.75, sd5["sovereignty"] + 0.35)
            sd5["tradeIntegration"] = sd5["tradeIntegration"] * 0.85
        elif sd5["status"] == "garrison":
            sd5["sovereignty"] = min(0.65, sd5["sovereignty"] + 0.20)

    # ── PHASE 5: FINAL STATE ──────────────────────────────────────────────
    max_pop = max(pop) if pop else 1.0

    states = []
    for i in range(N):
        sd = status_data[i]
        if i == reach_arch:
            faction = "reach"
        elif i == lattice_arch:
            faction = "lattice"
        elif not claimed[i]:
            faction = "unknown"
        else:
            faction = claimed[i]

        states.append({
            "faction":          faction,
            "status":           sd["status"],
            "name":             f"arch_{i}",
            "population":       round(pop[i]),
            "urbanization":     pop[i] / max_pop if max_pop > 0 else 0.0,
            "tech":             round(tech[i] * 10) / 10.0,
            "sovereignty":      sd["sovereignty"],
            "tradeIntegration": sd["tradeIntegration"],
            "eraOfContact":     sd["eraOfContact"],
            "hopCount":         hop_count[i],
        })

    return {
        "states":      states,
        "log":         log,
        "df_year":     df_year,
        "df_arch":     df_arch,
        "df_detector": df_detector,
        "reach_arch":  reach_arch,
        "lattice_arch":lattice_arch,
        "epi_log":     epi_log,
        "substrate":   substrate,
    }
