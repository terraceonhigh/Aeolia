#!/usr/bin/env python3
"""
million_seed_filter.py — Aeolia 1 M seed geographic pre-filter

Ports the minimal worldgen pipeline (seed -> plateau graph + substrate) from
MONOLITH_REFERENCE.jsx / world_generator.gd to pure Python (no external deps).

For each seed 1..1_000_000, evaluates four geographic pre-filter heuristics
and maintains a running top-100 heap sorted by composite geo score.

Heuristics (derived from loss.py terms 1-4, 6 and the Pu gate):
  H1  Latitude separation  — Reach faction centroid |lat| in [35,55] deg,
                             Lattice faction centroid |lat| < 28 deg
  H2  Civilizational gap   — min cross-faction great-circle distance > 0.5 rad
  H3  Pu access            — >= 1 Reach arch AND >= 1 Lattice arch with Pu
  H4  Density asymmetry    — Lattice mean pairwise GC < 0.6 rad,
                             Reach mean pairwise GC > 0.8 rad

Faction assignment uses BFS Voronoi from Reach/Lattice cores (fast, ~correct
for geographic shape; does not run the full era-gated Dijkstra wavefront).

Output:
  - One JSON per top-100 seed in <outdir>/, matching optimization/worlds/ format
  - Summary table printed to stdout at the end
  - Progress line printed every 10 000 seeds

Usage:
    python million_seed_filter.py                  # seeds 1..1_000_000
    python million_seed_filter.py --verify         # compare seeds 17,42,97,137,256 vs existing JSONs
    python million_seed_filter.py --max 100000     # first 100 K only
    python million_seed_filter.py --out mydir/     # custom output directory
    python million_seed_filter.py --top 50         # keep top 50 instead of 100
"""

from __future__ import annotations

import heapq
import json
import math
import os
import sys
import time
from collections import deque

# ---------------------------------------------------------------------------
# Constants (mirrors constants.gd)
# ---------------------------------------------------------------------------

ARCH_COUNT        = 42
ISLAND_MAX_HEIGHT = 3000.0
MAX_EDGE_ANGLE    = 0.9    # radians (~26 000 km); < not <=, matching GDScript
MIN_NEIGHBORS     = 2

# Polity names from constants.gd (index 0 = Reach, 1 = Lattice, rest shuffled)
POLITY_NAMES: list[str] = [
    "The Reach",    "The Lattice",  "The Gyre",     "The Narrows",  "The Shelf",
    "The Traverse", "The Loom",     "The Windward",  "The Caldera",  "The Strand",
    "The Bight",    "The Cairn",    "The Shoal",     "The Polder",   "The Tidemark",
    "The Breakwater","The Current", "The Sargasso",  "The Atoll",    "The Meridian",
    "The Cordage",  "The Basalt",   "The Estuary",   "The Fathom",   "The Wake",
    "The Isthmus",  "The Shingle",  "The Swell",     "The Trench",   "The Mooring",
    "The Reef",     "The Floe",     "The Passage",   "The Spindle",  "The Brine",
    "The Cay",      "The Eddy",     "The Rime",      "The Berth",    "The Forge",
    "The Drift",    "The Quay",
]

# ---------------------------------------------------------------------------
# Precomputed seed-independent Fibonacci spiral base values
# ---------------------------------------------------------------------------

_GOLDEN_ANGLE = math.pi * (3.0 - math.sqrt(5.0))
_TWO_PI       = 2.0 * math.pi

_FIB_BASE_LAT: list[float] = []
_FIB_BASE_LON: list[float] = []
for _k in range(ARCH_COUNT):
    _y = 1.0 - (2.0 * (_k + 0.5)) / ARCH_COUNT
    _FIB_BASE_LAT.append(math.degrees(math.asin(max(-1.0, min(1.0, _y)))))
    _FIB_BASE_LON.append(math.degrees(_GOLDEN_ANGLE * _k) % 360.0 - 180.0)

# ---------------------------------------------------------------------------
# Mulberry32 PRNG — exact port of JS mulberry32() / GDScript RNG.gd
# Same implementation as sim_proxy.py — identical seed → identical sequence.
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
        t       = self._imul(s ^ self._urs(s, 15), 1 | s)
        t_orig  = t
        t       = (t + self._imul(t ^ self._urs(t, 7), 61 | t)) ^ t_orig
        result  = (t ^ self._urs(t, 14)) & 0xFFFFFFFF
        return result / 4294967296.0


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _lat_lon_to_xyz(lat: float, lon: float) -> tuple[float, float, float]:
    p = math.radians(90.0 - lat)
    t = math.radians(lon + 180.0)
    return math.sin(p) * math.cos(t), math.cos(p), math.sin(p) * math.sin(t)


def _roundi(x: float) -> int:
    """Round-half-up, matching JS Math.round() and GDScript roundi()."""
    return math.floor(x + 0.5)


def _gc_dist(a: dict, b: dict) -> float:
    dot = a["cx"] * b["cx"] + a["cy"] * b["cy"] + a["cz"] * b["cz"]
    return math.acos(max(-1.0, min(1.0, dot)))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _mean_pairwise_gc(archs: list[dict], indices: list[int]) -> float:
    dists = []
    for ii in range(len(indices)):
        ai = archs[indices[ii]]
        for jj in range(ii + 1, len(indices)):
            dists.append(_gc_dist(ai, archs[indices[jj]]))
    return _mean(dists) if dists else 0.0


def _sq_relu(x: float) -> float:
    return max(0.0, x) ** 2


# ---------------------------------------------------------------------------
# World builder — faithful port of world_generator.gd build_world()
# RNG: Mulberry32(seed) — NOT the seed*31+7 variant used by sim_proxy.
# ---------------------------------------------------------------------------

def _regen_peaks(
    arch: dict,
    prng: Mulberry32,
    arch_size: float,
    n: int,
    w_min: float,
    w_range: float,
    h_mul: float,
) -> None:
    """Rebuild core arch peaks with faction-mandated geometry (world_generator.gd _regen_peaks)."""
    cx, cy, cz = arch["cx"], arch["cy"], arch["cz"]
    rx = -cz;  ry = 0.0;  rz = cx
    rl = math.sqrt(rx * rx + rz * rz) or 1.0
    rx /= rl;  rz /= rl
    fx = cy * rz;  fy = cz * rx - cx * rz;  fz = -cy * rx

    peaks: list[dict] = []
    for _ in range(n):
        ang  = prng.next_float() * _TWO_PI
        dist = (0.2 + prng.next_float() * 0.8) * arch_size * 0.12
        ca   = math.cos(ang);  sa = math.sin(ang)
        px   = cx + dist * (ca * rx + sa * fx)
        py   = cy + dist * (ca * ry + sa * fy)
        pz   = cz + dist * (ca * rz + sa * fz)
        pl   = math.sqrt(px * px + py * py + pz * pz) or 1.0
        px /= pl;  py /= pl;  pz /= pl
        w    = w_min + prng.next_float() * w_range * arch_size
        raw_h = ISLAND_MAX_HEIGHT * (0.4 + prng.next_float() * 0.6) * h_mul
        h    = min(ISLAND_MAX_HEIGHT, raw_h)
        peaks.append({"h": h, "w": w})
    arch["peaks"]   = peaks
    arch["shelf_r"] = arch_size * 0.12


def build_world(seed: int) -> dict:
    """
    Port of world_generator.gd build_world().

    Returns:
        archs         — list of arch dicts: {cx,cy,cz, peaks:[{h,w}], shelf_r}
        plateau_edges — list of [i, j] pairs
        reach_arch    — index of Reach core
        lattice_arch  — index of Lattice core
        seed          — normalised seed (0 → 42)
    """
    s   = seed if seed != 0 else 42
    rng = Mulberry32(s)
    N   = ARCH_COUNT

    # ── Arch specs: Fibonacci spiral + seeded jitter ──────────────────────
    arch_specs: list[dict] = []
    for k in range(N):
        j_lat = max(-75.0, min(75.0, _FIB_BASE_LAT[k] + (rng.next_float() - 0.5) * 24.0))
        j_lon = _FIB_BASE_LON[k] + (rng.next_float() - 0.5) * 24.0

        size_roll = rng.next_float()
        if size_roll < 0.15:
            arch_size = 1.3 + rng.next_float() * 0.9
        elif size_roll < 0.40:
            arch_size = 0.7 + rng.next_float() * 0.6
        else:
            arch_size = 0.25 + rng.next_float() * 0.45

        n_peaks = max(2, _roundi(arch_size * (3.0 + rng.next_float() * 5.0)))
        arch_specs.append({"lat": j_lat, "lon": j_lon, "size": arch_size, "n": n_peaks})

    # ── Build arch objects with peaks ──────────────────────────────────────
    archs: list[dict] = []
    for spec in arch_specs:
        cx, cy, cz = _lat_lon_to_xyz(spec["lat"], spec["lon"])

        rx = -cz;  ry = 0.0;  rz = cx
        rl = math.sqrt(rx * rx + rz * rz) or 1.0
        rx /= rl;  rz /= rl
        fx = cy * rz;  fy = cz * rx - cx * rz;  fz = -cy * rx

        peaks: list[dict] = []
        for _ in range(spec["n"]):
            ang  = rng.next_float() * _TWO_PI
            dist = (0.2 + rng.next_float() * 0.8) * spec["size"] * 0.12
            ca   = math.cos(ang);  sa = math.sin(ang)
            px   = cx + dist * (ca * rx + sa * fx)
            py   = cy + dist * (ca * ry + sa * fy)
            pz   = cz + dist * (ca * rz + sa * fz)
            pl   = math.sqrt(px * px + py * py + pz * pz) or 1.0
            px /= pl;  py /= pl;  pz /= pl
            w    = 0.005 + rng.next_float() * 0.008 * spec["size"]
            raw_h = ISLAND_MAX_HEIGHT * (0.4 + rng.next_float() * 0.6) * (spec["size"] / 1.5)
            h    = min(ISLAND_MAX_HEIGHT, raw_h)
            peaks.append({"h": h, "w": w})

        archs.append({
            "cx": cx, "cy": cy, "cz": cz,
            "peaks": peaks,
            "shelf_r": spec["size"] * 0.12,
        })

    # ── Most-antipodal pair → Reach (higher cy = north) & Lattice ─────────
    reach_arch = 0;  lattice_arch = 1;  best_dot = 2.0
    for i in range(N):
        ai = archs[i]
        cxi, cyi, czi = ai["cx"], ai["cy"], ai["cz"]
        for j in range(i + 1, N):
            aj = archs[j]
            d  = cxi * aj["cx"] + cyi * aj["cy"] + czi * aj["cz"]
            if d < best_dot:
                best_dot = d;  reach_arch = i;  lattice_arch = j
    if archs[reach_arch]["cy"] < archs[lattice_arch]["cy"]:
        reach_arch, lattice_arch = lattice_arch, reach_arch

    # ── Override core arch peaks with bible-mandated geographies ──────────
    # Reach: 14 peaks, wide spread (size 1.8), tall peaks
    _regen_peaks(archs[reach_arch],   Mulberry32(s * 7 + 1),  1.8, 14, 0.005, 0.008, 1.2)
    # Lattice: 22 peaks, tight cluster (size 0.8), narrower
    _regen_peaks(archs[lattice_arch], Mulberry32(s * 13 + 2), 0.8, 22, 0.004, 0.006, 1.0)

    # ── Plateau edge network from proximity ────────────────────────────────
    # Collect all pairwise angles (sorted ascending)
    pair_dists: list[tuple[float, int, int]] = []
    for i in range(N):
        ai = archs[i]
        cxi, cyi, czi = ai["cx"], ai["cy"], ai["cz"]
        for j in range(i + 1, N):
            aj = archs[j]
            d  = cxi * aj["cx"] + cyi * aj["cy"] + czi * aj["cz"]
            pair_dists.append((math.acos(max(-1.0, min(1.0, d))), i, j))
    pair_dists.sort()

    edge_set: set[tuple[int, int]] = set()
    conn_count = [0] * N
    plateau_edges: list[list[int]] = []

    def add_edge(i: int, j: int) -> None:
        key = (min(i, j), max(i, j))
        if key in edge_set:
            return
        edge_set.add(key)
        plateau_edges.append([i, j])
        conn_count[i] += 1
        conn_count[j] += 1

    # Pass 1: guarantee MIN_NEIGHBORS connections per arch
    for angle, i, j in pair_dists:
        if conn_count[i] < MIN_NEIGHBORS or conn_count[j] < MIN_NEIGHBORS:
            add_edge(i, j)

    # Pass 2: add all pairs within angular threshold (< not <=, matches GDScript)
    for angle, i, j in pair_dists:
        if angle >= MAX_EDGE_ANGLE:
            break
        add_edge(i, j)

    return {
        "archs":         archs,
        "plateau_edges": plateau_edges,
        "reach_arch":    reach_arch,
        "lattice_arch":  lattice_arch,
        "seed":          s,
    }


# ---------------------------------------------------------------------------
# Gyre position helper — faithful port of substrate.gd _compute_gyre_position()
# ---------------------------------------------------------------------------

def _compute_gyre_position(arch: dict, all_archs: list[dict]) -> float:
    cy_clamped = max(-1.0, min(1.0, arch["cy"]))
    lat        = math.asin(cy_clamped) * 180.0 / math.pi
    abs_lat    = abs(lat)

    band_archs: list[dict] = []
    for other in all_archs:
        other_lat = abs(math.asin(max(-1.0, min(1.0, other["cy"]))) * 180.0 / math.pi)
        if abs(other_lat - abs_lat) < 15.0:
            band_archs.append(other)

    if len(band_archs) < 2:
        return 0.5

    lons = sorted(math.atan2(a["cz"], a["cx"]) * 180.0 / math.pi for a in band_archs)

    max_gap    = 0.0
    gap_center = 0.0
    for jj in range(len(lons)):
        next_lon = lons[(jj + 1) % len(lons)]
        if jj == len(lons) - 1:
            next_lon += 360.0
        gap = next_lon - lons[jj]
        if gap > max_gap:
            max_gap    = gap
            gap_center = lons[jj] + gap / 2.0

    if max_gap < 10.0:
        return 0.5

    my_lon  = math.atan2(arch["cz"], arch["cx"]) * 180.0 / math.pi
    rel_pos = math.fmod(my_lon - gap_center + 540.0, 360.0) / 360.0
    return max(0.0, min(1.0, rel_pos))


# ---------------------------------------------------------------------------
# Substrate — faithful port of sim_proxy.py _compute_substrate()
# (itself a faithful port of substrate.gd compute_substrate())
# ---------------------------------------------------------------------------

def compute_substrate(archs: list[dict], plateau_edges: list[list[int]], seed: int) -> list[dict]:
    """
    Full substrate cascade: climate → crops → trade → minerals.
    Matches substrate.gd / sim_proxy.py _compute_substrate() exactly.
    """
    rng = Mulberry32((seed if seed > 0 else 42) * 47 + 2024)
    N   = len(archs)

    edge_count   = [0] * N
    edge_lengths = [[] for _ in range(N)]
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        edge_count[a] += 1;  edge_count[b] += 1
        dot = (archs[a]["cx"] * archs[b]["cx"] +
               archs[a]["cy"] * archs[b]["cy"] +
               archs[a]["cz"] * archs[b]["cz"])
        ang = math.acos(max(-1.0, min(1.0, dot)))
        edge_lengths[a].append(ang);  edge_lengths[b].append(ang)

    all_lens: list[float] = []
    for ll in edge_lengths:
        all_lens.extend(ll)
    max_edge_len = max(all_lens) if all_lens else 0.5

    substrates: list[dict] = []

    for i, arch in enumerate(archs):
        cy_clamped = max(-1.0, min(1.0, arch["cy"]))
        lat        = math.asin(cy_clamped) * 180.0 / math.pi
        abs_lat    = abs(lat)
        shelf_r    = arch["shelf_r"]
        size       = shelf_r / 0.12

        peaks     = arch.get("peaks", [])
        peak_count = len(peaks)
        avg_h      = 0.0
        if peak_count > 0:
            avg_h = sum(pk["h"] for pk in peaks) / (peak_count * ISLAND_MAX_HEIGHT)

        avg_edge = 0.5
        if edge_lengths[i]:
            avg_edge = sum(edge_lengths[i]) / len(edge_lengths[i])

        # Wind belt
        if   abs_lat < 12: wind_belt = "doldrums"
        elif abs_lat < 28: wind_belt = "trades"
        elif abs_lat < 35: wind_belt = "subtropical"
        elif abs_lat < 55: wind_belt = "westerlies"
        elif abs_lat < 65: wind_belt = "subpolar"
        else:              wind_belt = "polar"

        base_rain = {
            "doldrums":    2800.0, "trades":      2200.0, "subtropical":  600.0,
            "westerlies":  1400.0, "subpolar":    1100.0, "polar":        300.0,
        }[wind_belt]

        orographic_bonus = 1.0 + avg_h * 1.8

        gyre_pos     = _compute_gyre_position(arch, archs)
        if gyre_pos < 0.3:
            ocean_warmth = 0.8 + gyre_pos
        elif gyre_pos > 0.7:
            ocean_warmth = 0.3 - (gyre_pos - 0.7)
        else:
            ocean_warmth = 0.4 + gyre_pos * 0.2
        ocean_warmth = max(0.0, min(1.0, ocean_warmth))

        moisture_bonus     = 1.0 + max(0.0, ocean_warmth - 0.4) * 0.4
        effective_rainfall = base_rain * orographic_bonus * moisture_bonus * 1.4

        mean_temp      = 28.0 - abs_lat * 0.45 + (ocean_warmth - 0.5) * 4.0
        seasonal_range = abs_lat * 0.15 * 0.7

        # Tidal range with cluster density
        nearby = sum(
            1 for other in archs
            if other is not arch and
               arch["cx"] * other["cx"] + arch["cy"] * other["cy"] + arch["cz"] * other["cz"] > 0.95
        )
        cluster_density = min(1.0, float(nearby) / 5.0)
        abs_lat_rad     = abs_lat * math.pi / 180.0
        tidal_range     = ((2.0 + shelf_r * 30.0 + cluster_density * 4.0) *
                           (0.8 + abs(math.sin(abs_lat_rad)) * 0.4))

        # Upwelling
        upwelling = 0.0
        if gyre_pos > 0.7:   upwelling += 0.4
        if abs_lat < 5.0:    upwelling += 0.3
        upwelling += edge_count[i] * 0.08

        fisheries = min(1.0, upwelling * 0.5 + effective_rainfall * 0.0001 + edge_count[i] * 0.05)

        # Climate zone
        if   mean_temp > 24 and effective_rainfall > 2000: climate_zone = "tropical_wet"
        elif mean_temp > 24 and effective_rainfall < 1000: climate_zone = "tropical_dry"
        elif mean_temp > 10 and effective_rainfall > 1200: climate_zone = "temperate_wet"
        elif mean_temp > 10:                               climate_zone = "temperate_dry"
        elif mean_temp > 2:                                climate_zone = "subpolar"
        else:                                              climate_zone = "polar_fringe"

        # Crop viability predicates (§10a)
        can_grow = {
            "paddi": (mean_temp >= 20 and effective_rainfall >= 1200 and
                      tidal_range >= 2.0 and shelf_r >= 0.08 and abs_lat <= 28),
            "emmer": (mean_temp >= 8  and mean_temp <= 24 and
                      effective_rainfall >= 400 and effective_rainfall <= 2000 and
                      abs_lat >= 20 and abs_lat <= 55),
            "taro":  (mean_temp >= 21 and seasonal_range <= 4 and
                      effective_rainfall >= 1500 and abs_lat <= 20),
            "nori":  (mean_temp >= 5  and mean_temp <= 22 and
                      edge_count[i] >= 1 and upwelling >= 0.2),
            "sago":  (mean_temp >= 24 and effective_rainfall >= 2000 and
                      abs_lat <= 15  and shelf_r >= 0.04),
            "papa":  (mean_temp >= 2  and mean_temp <= 18 and
                      effective_rainfall >= 400 and abs_lat >= 35),
        }

        yields: dict[str, float] = {}
        if can_grow["paddi"]:
            yields["paddi"] = (5.0
                * min(1.0, (mean_temp - 18.0) / 15.0)
                * min(1.0, effective_rainfall / 1800.0)
                * min(1.0, tidal_range / 5.0))
        if can_grow["emmer"]:
            yields["emmer"] = (2.5
                * (1.0 - abs(mean_temp - 16.0) / 20.0)
                * (1.0 - abs(effective_rainfall - 700.0) / 1500.0))
        if can_grow["taro"]:
            yields["taro"]  = (3.0
                * min(1.0, (mean_temp - 20.0) / 8.0)
                * min(1.0, effective_rainfall / 2000.0))
        if can_grow["nori"]:
            yields["nori"]  = (1.5
                * min(1.0, upwelling * 2.0)
                * min(1.0, float(edge_count[i]) / 3.0) * 2.0)
        if can_grow["sago"]:
            yields["sago"]  = (4.0
                * min(1.0, effective_rainfall / 2500.0)
                * min(1.0, shelf_r / 0.10))
        if can_grow["papa"]:
            yields["papa"]  = (3.5
                * (1.0 - abs(mean_temp - 12.0) / 15.0)
                * min(1.0, effective_rainfall / 600.0))

        # Stable sort: descending yield then ascending name (matches GDScript stable sort)
        crop_entries = sorted(yields.items(), key=lambda kv: (-kv[1], kv[0]))

        primary_crop   = "foraging"
        secondary_crop = None
        primary_yield  = 0.5
        if crop_entries:
            primary_crop  = crop_entries[0][0]
            primary_yield = crop_entries[0][1]
        if len(crop_entries) > 1:
            secondary_crop = crop_entries[1][0]

        # Trade goods (§10b) — consume RNG calls in substrate order
        stim_map  = {"paddi": "char",   "emmer": "qahwa", "taro": "awa",
                     "sago":  "pinang", "papa":  "aqua",  "nori": "",   "foraging": ""}
        fiber_map = {"paddi": "seric",  "emmer": "fell",  "taro": "tapa",
                     "sago":  "tapa",   "nori":  "byssus","papa": "qivu","foraging": ""}
        prot_map  = {"paddi": "kerbau", "emmer": "kri",   "taro": "moa",
                     "sago":  "moa",    "nori":  "",       "papa": "",    "foraging": ""}

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

        total_trade_value = (stim_prod * 0.4 + fiber_prod * 0.3 +
                             prot_prod * 0.2 + nori_export * 0.3)

        # Minerals (§10g) — MUST come after trade goods RNG calls
        minerals = {
            "Fe": True,
            "Cu": rng.next_float() < 0.20,
            "Au": rng.next_float() < (0.05 + avg_h * 0.08),
            "Pu": rng.next_float() < (0.03 + size * 0.02),
        }

        # Narrative (§10e) — one more RNG-consuming field downstream; not needed
        # for the pre-filter but we include climate for lat-based heuristics.

        substrates.append({
            "climate": {
                "latitude":           lat,
                "abs_latitude":       abs_lat,
                "wind_belt":          wind_belt,
                "mean_temp":          mean_temp,
                "seasonal_range":     seasonal_range,
                "base_rainfall":      base_rain,
                "effective_rainfall": effective_rainfall,
                "tidal_range":        tidal_range,
                "ocean_warmth":       ocean_warmth,
                "gyre_position":      gyre_pos,
                "upwelling":          upwelling,
                "fisheries_richness": fisheries,
                "climate_zone":       climate_zone,
            },
            "crops": {
                "primary_crop":   primary_crop,
                "secondary_crop": secondary_crop,
                "primary_yield":  primary_yield,
                "can_grow":       can_grow,
            },
            "trade_goods": {
                "total_trade_value": total_trade_value,
                "stim_type":         stim_type,
                "fiber_type":        fiber_type,
            },
            "minerals": minerals,
        })

    return substrates


# ---------------------------------------------------------------------------
# Faction assignment — BFS Voronoi from Reach/Lattice cores
# Approximates the full era-gated Dijkstra wavefront.  Fast; captures the
# geographic partition well enough for pre-filter heuristics.
# ---------------------------------------------------------------------------

def assign_factions_bfs(
    archs: list[dict],
    plateau_edges: list[list[int]],
    reach_arch: int,
    lattice_arch: int,
) -> tuple[list[str], list[list[int]]]:
    """
    Returns (factions, adj).
      factions[i] = "reach" | "lattice"
      adj[i]      = list of neighbour indices (built from plateau_edges)
    """
    N   = len(archs)
    adj = [[] for _ in range(N)]
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        adj[a].append(b);  adj[b].append(a)

    dist_r = [999] * N;  dist_r[reach_arch]   = 0
    dist_l = [999] * N;  dist_l[lattice_arch]  = 0

    def _bfs(start: int, dist: list[int]) -> None:
        q = deque([start])
        while q:
            u = q.popleft()
            for v in adj[u]:
                if dist[v] > dist[u] + 1:
                    dist[v] = dist[u] + 1
                    q.append(v)

    _bfs(reach_arch,   dist_r)
    _bfs(lattice_arch, dist_l)

    factions = ["reach" if dist_r[i] <= dist_l[i] else "lattice" for i in range(N)]
    return factions, adj


# ---------------------------------------------------------------------------
# Pre-filter heuristic evaluation
# Scoring mirrors loss.py terms 1-4 (density/spread/lat) and 6 (civ gap),
# plus a Pu-access gate term.  Lower total_loss = better candidate.
# composite_score = -total_loss (higher is better, compatible with max-heap).
# ---------------------------------------------------------------------------

def evaluate_heuristics(
    archs:        list[dict],
    substrate:    list[dict],
    factions:     list[str],
    reach_arch:   int,
    lattice_arch: int,
) -> tuple[float, bool, dict]:
    """
    Returns (composite_score, hard_pass, details).
    composite_score is negative loss — higher = better.
    hard_pass is True only when all four constraints are satisfied.
    """
    reach_idxs   = [i for i, f in enumerate(factions) if f == "reach"]
    lattice_idxs = [i for i, f in enumerate(factions) if f == "lattice"]

    if len(reach_idxs) < 2 or len(lattice_idxs) < 2:
        return float("-inf"), False, {"error": "degenerate faction split"}

    # ── H1: Latitude separation ──────────────────────────────────────────
    reach_lats   = [substrate[i]["climate"]["abs_latitude"] for i in reach_idxs]
    lattice_lats = [substrate[i]["climate"]["abs_latitude"] for i in lattice_idxs]
    reach_centroid   = _mean(reach_lats)
    lattice_centroid = _mean(lattice_lats)

    # Penalty: Reach centroid outside [35, 55]; Lattice centroid > 28
    h1_loss = ((_sq_relu(35.0 - reach_centroid) + _sq_relu(reach_centroid - 55.0)) * 0.01
               + _sq_relu(lattice_centroid - 28.0) * 0.01)

    # ── H2: Civilizational gap ────────────────────────────────────────────
    min_cross = min(
        _gc_dist(archs[i], archs[j])
        for i in reach_idxs for j in lattice_idxs
    )
    h2_loss = _sq_relu(0.5 - min_cross) * 4.0

    # ── H3: Pu access (both factions must have >= 1 Pu arch) ─────────────
    reach_has_pu   = any(substrate[i]["minerals"]["Pu"] for i in reach_idxs)
    lattice_has_pu = any(substrate[i]["minerals"]["Pu"] for i in lattice_idxs)
    # Penalty: 1.0 per missing Pu faction (binary gate)
    h3_loss = (0.0 if reach_has_pu else 1.0) + (0.0 if lattice_has_pu else 1.0)

    # ── H4: Density asymmetry ─────────────────────────────────────────────
    lattice_mean_gc = _mean_pairwise_gc(archs, lattice_idxs)
    reach_mean_gc   = _mean_pairwise_gc(archs, reach_idxs)
    h4_loss = (_sq_relu(lattice_mean_gc - 0.6) * 4.0   # Lattice too spread
               + _sq_relu(0.8 - reach_mean_gc)  * 4.0) # Reach too clustered

    total_loss      = h1_loss + h2_loss + h3_loss + h4_loss
    composite_score = -total_loss  # higher = better

    hard_pass = (
        35.0 <= reach_centroid <= 55.0 and
        lattice_centroid < 28.0 and
        min_cross > 0.5 and
        reach_has_pu and lattice_has_pu and
        lattice_mean_gc < 0.6 and
        reach_mean_gc   > 0.8
    )

    details = {
        "reach_centroid_lat":  round(reach_centroid,   3),
        "lattice_centroid_lat": round(lattice_centroid, 3),
        "min_cross_gc_rad":    round(min_cross,         4),
        "reach_has_pu":        reach_has_pu,
        "lattice_has_pu":      lattice_has_pu,
        "lattice_mean_gc_rad": round(lattice_mean_gc,   4),
        "reach_mean_gc_rad":   round(reach_mean_gc,     4),
        "h1_loss":             round(h1_loss,            4),
        "h2_loss":             round(h2_loss,            4),
        "h3_loss":             round(h3_loss,            4),
        "h4_loss":             round(h4_loss,            4),
        "total_loss":          round(total_loss,         4),
        "composite_score":     round(composite_score,    4),
        "hard_pass":           hard_pass,
    }
    return composite_score, hard_pass, details


# ---------------------------------------------------------------------------
# JSON export — matches run_headless.gd _export() format
# ---------------------------------------------------------------------------

def _compute_potentials_and_names(
    archs: list[dict],
    reach_arch: int,
    lattice_arch: int,
    seed: int,
) -> tuple[list[float], list[str]]:
    """
    Compute per-arch potentials and polity names using the same RNG seed as
    run_headless.gd / history_engine.gd: Mulberry32(seed * 31 + 1066).

    The first N calls produce potentials; subsequent calls shuffle polity names.
    """
    s   = seed if seed != 0 else 42
    rng = Mulberry32(s * 31 + 1066)
    N   = len(archs)

    potentials: list[float] = []
    for arch in archs:
        peaks   = arch.get("peaks", [])
        p_count = len(peaks)
        sz      = arch["shelf_r"] / 0.12
        avg_h   = 0.0
        if p_count > 0:
            avg_h = sum(pk["h"] for pk in peaks) / (p_count * ISLAND_MAX_HEIGHT)
        pot = ((p_count / 20.0 * 0.4 + avg_h * 0.3 + sz / 2.2 * 0.3)
               * (0.6 + rng.next_float() * 0.4))
        potentials.append(pot)

    # Shuffle name pool (same RNG, continues after potential computation)
    pool = list(POLITY_NAMES[2:])
    for ii in range(len(pool) - 1, 0, -1):
        jj = int(rng.next_float() * (ii + 1))
        pool[ii], pool[jj] = pool[jj], pool[ii]

    names: list[str] = [None] * N  # type: ignore[list-item]
    names[reach_arch]   = POLITY_NAMES[0]
    names[lattice_arch] = POLITY_NAMES[1]
    pi = 0
    for ii in range(N):
        if ii == reach_arch or ii == lattice_arch:
            continue
        names[ii] = pool[pi] if pi < len(pool) else f"Archipelago {ii}"
        pi += 1

    return potentials, names


def world_to_json(
    world:      dict,
    substrate:  list[dict],
    factions:   list[str],
    adj:        list[list[int]],
    heuristics: dict,
) -> dict:
    """
    Serialise a generated world into the thin_sim-compatible JSON format
    used by optimization/worlds/seed_*.json (produced by run_headless.gd).
    """
    archs         = world["archs"]
    plateau_edges = world["plateau_edges"]
    reach_arch    = world["reach_arch"]
    lattice_arch  = world["lattice_arch"]
    seed          = world["seed"]
    N             = len(archs)

    potentials, names = _compute_potentials_and_names(archs, reach_arch, lattice_arch, seed)

    # Arch export (mirrors run_headless.gd arch_out format)
    arch_out: list[dict] = []
    for k, arch in enumerate(archs):
        cy  = max(-1.0, min(1.0, arch["cy"]))
        lat = math.degrees(math.asin(cy))
        lon = math.degrees(math.atan2(arch["cz"], arch["cx"]))
        peaks_k = arch.get("peaks", [])
        pc = len(peaks_k)
        ah = 0.0
        if pc > 0:
            ah = sum(pk["h"] for pk in peaks_k) / (pc * ISLAND_MAX_HEIGHT)
        arch_out.append({
            "index":      k,
            "lat":        round(lat, 2),
            "lon":        round(lon, 2),
            "cx":         round(arch["cx"], 5),
            "cy":         round(arch["cy"], 5),
            "cz":         round(arch["cz"], 5),
            "size":       round(arch["shelf_r"] / 0.12, 3),
            "shelf_r":    arch["shelf_r"],
            "peak_count": pc,
            "avg_h":      round(ah, 4),
            "potential":  round(potentials[k], 4),
        })

    # Substrate export (flat format matching run_headless.gd sub_out)
    sub_out: list[dict] = []
    for k, sub in enumerate(substrate):
        cl   = sub["climate"]
        mins = sub["minerals"]
        crops = sub["crops"]
        sub_out.append({
            "primary_crop":       crops["primary_crop"],
            "primary_yield":      crops["primary_yield"],
            "secondary_crop":     crops["secondary_crop"],
            "total_trade_value":  sub["trade_goods"]["total_trade_value"],
            "latitude":           round(cl["latitude"],           2),
            "abs_latitude":       round(cl["abs_latitude"],       2),
            "tidal_range":        round(cl["tidal_range"],        3),
            "mean_temp":          round(cl["mean_temp"],          2),
            "effective_rainfall": round(cl["effective_rainfall"], 0),
            "upwelling":          round(cl["upwelling"],          3),
            "minerals": {
                "Fe": mins["Fe"],
                "Cu": mins["Cu"],
                "Au": mins["Au"],
                "Pu": mins["Pu"],
            },
        })

    # States — simplified BFS-based faction assignment (no full history engine)
    states_out: list[dict] = []
    for k in range(N):
        faction = factions[k]
        if k == reach_arch:
            status = "core"
        elif k == lattice_arch:
            status = "core"
        else:
            status = "territory"
        states_out.append({
            "faction":          faction,
            "status":           status,
            "name":             names[k],
            "population":       0,
            "tech":             0.0,
            "sovereignty":      1.0 if k in (reach_arch, lattice_arch) else 0.7,
            "tradeIntegration": 0.0,
            "eraOfContact":     None,
            "hopCount":         0,
            "urbanization":     0.0,
        })

    return {
        "seed":          seed,
        "n":             N,
        "reach_arch":    reach_arch,
        "lattice_arch":  lattice_arch,
        "archs":         arch_out,
        "plateau_edges": plateau_edges,
        "adj":           adj,
        "substrate":     sub_out,
        "states":        states_out,
        "names":         names,
        # Non-standard field: pre-filter diagnostics
        "prefilter":     heuristics,
    }


# ---------------------------------------------------------------------------
# Verification mode — compare against existing Godot-generated world JSONs
# ---------------------------------------------------------------------------

def verify_against_existing(worlds_dir: str) -> None:
    """
    Run the pipeline on the 5 known seeds, compare arch count, reach_arch
    index, lattice_arch index, and latitude values against existing JSONs.
    """
    check_seeds = [17, 42, 97, 137, 256]
    print(f"\n{'─'*72}")
    print("VERIFICATION — comparing Python port vs Godot-generated worlds/")
    print(f"{'─'*72}")
    print(f"{'seed':>6}  {'py_r':>5} {'gd_r':>5} {'py_l':>5} {'gd_l':>5}"
          f"  {'py_r_lat':>9} {'gd_r_lat':>9}  {'py_l_lat':>9} {'gd_l_lat':>9}  {'match':>5}")
    print(f"{'─'*72}")

    all_pass = True
    for seed in check_seeds:
        w = build_world(seed)
        archs       = w["archs"]
        py_r        = w["reach_arch"]
        py_l        = w["lattice_arch"]
        py_r_lat    = round(math.degrees(math.asin(max(-1.0, min(1.0, archs[py_r]["cy"])))), 2)
        py_l_lat    = round(math.degrees(math.asin(max(-1.0, min(1.0, archs[py_l]["cy"])))), 2)
        py_n        = len(archs)

        json_path = os.path.join(worlds_dir, f"seed_{seed}.json")
        if not os.path.exists(json_path):
            print(f"{seed:>6}  (no reference JSON at {json_path})")
            continue

        with open(json_path) as f:
            gd = json.load(f)

        gd_r     = gd["reach_arch"]
        gd_l     = gd["lattice_arch"]
        gd_n     = gd.get("n", len(gd.get("archs", [])))
        gd_r_lat = None;  gd_l_lat = None
        for a in gd.get("archs", []):
            if a["index"] == gd_r: gd_r_lat = a["lat"]
            if a["index"] == gd_l: gd_l_lat = a["lat"]

        match = (py_r == gd_r and py_l == gd_l and py_n == gd_n)
        if not match:
            all_pass = False
        flag = "OK" if match else "FAIL"

        print(f"{seed:>6}  {py_r:>5} {gd_r:>5} {py_l:>5} {gd_l:>5}"
              f"  {py_r_lat:>9.2f} {gd_r_lat or 0:>9.2f}"
              f"  {py_l_lat:>9.2f} {gd_l_lat or 0:>9.2f}  {flag:>5}")

    print(f"{'─'*72}")
    if all_pass:
        print("All seeds match. Port verified.")
    else:
        print("Some seeds differ — check PRNG alignment or rounding.")
    print()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    args = sys.argv[1:]

    do_verify = "--verify" in args
    max_seed  = 1_000_000
    top_k     = 100

    # Default output dir: same directory as this script → optimization/worlds/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir    = os.path.join(script_dir, "worlds")

    i = 0
    while i < len(args):
        if args[i] == "--max" and i + 1 < len(args):
            max_seed = int(args[i + 1]);  i += 2
        elif args[i] == "--out" and i + 1 < len(args):
            out_dir = args[i + 1];  i += 2
        elif args[i] == "--top" and i + 1 < len(args):
            top_k = int(args[i + 1]);  i += 2
        else:
            i += 1

    if do_verify:
        verify_against_existing(out_dir)
        return

    os.makedirs(out_dir, exist_ok=True)

    print(f"Aeolia million-seed pre-filter")
    print(f"  Seeds:      1 .. {max_seed:,}")
    print(f"  Keep top:   {top_k}")
    print(f"  Output dir: {out_dir}")
    print(f"  Heuristics: H1 reach_lat∈[35,55] | H2 civ_gap>0.5 | H3 Pu×2 | H4 density_asym")
    print()

    # Min-heap: (composite_score, seed, world, substrate, factions, adj, heuristics)
    # Since we want TOP scores and heapq is a MIN-heap, we store (-score, ...).
    # heap[0] = worst of the current top-k (lowest score = most negative).
    heap: list[tuple] = []
    n_hard_pass   = 0
    n_processed   = 0
    t_start       = time.monotonic()
    t_last_report = t_start

    for seed in range(1, max_seed + 1):
        # ── Full pipeline ──────────────────────────────────────────────────
        world     = build_world(seed)
        substrate = compute_substrate(world["archs"], world["plateau_edges"], seed)
        factions, adj = assign_factions_bfs(
            world["archs"], world["plateau_edges"],
            world["reach_arch"], world["lattice_arch"],
        )
        score, hard_pass, details = evaluate_heuristics(
            world["archs"], substrate, factions,
            world["reach_arch"], world["lattice_arch"],
        )

        if hard_pass:
            n_hard_pass += 1

        # ── Top-k heap ────────────────────────────────────────────────────
        # Store (-score, seed, ...) so heappop() removes worst (smallest score).
        entry = (-score, seed, world, substrate, factions, adj, details)
        if len(heap) < top_k:
            heapq.heappush(heap, entry)
        elif -score < heap[0][0]:           # current seed better than worst in heap
            heapq.heapreplace(heap, entry)  # replace worst with new

        n_processed += 1

        # ── Progress report ────────────────────────────────────────────────
        if seed % 10_000 == 0:
            now       = time.monotonic()
            elapsed   = now - t_start
            rate      = seed / elapsed if elapsed > 0 else 0
            remaining = (max_seed - seed) / rate if rate > 0 else 0
            best      = -heap[0][0] if heap else float("-inf")
            worst     = max(-e[0] for e in heap) if heap else float("-inf")
            print(
                f"  seed {seed:>8,} / {max_seed:,}  "
                f"rate {rate:>6.0f}/s  "
                f"eta {remaining/60:>5.1f}m  "
                f"hard_pass {n_hard_pass:>5}  "
                f"heap_worst {worst:.4f}  heap_best {best:.4f}"
            )
            t_last_report = now

    elapsed = time.monotonic() - t_start
    print(f"\nDone in {elapsed:.1f}s ({n_processed:,} seeds, {n_hard_pass} hard-pass).\n")

    # ── Sort and export top-k ─────────────────────────────────────────────
    ranked = sorted(heap, key=lambda e: e[0])   # ascending -score = best first
    print(f"Top {len(ranked)} candidates (best → worst):")
    print(f"  {'rank':>4}  {'seed':>8}  {'score':>8}  "
          f"{'r_lat':>7}  {'l_lat':>6}  {'civ_gap':>7}  "
          f"{'lat_gc':>6}  {'rch_gc':>6}  {'Pu':>4}  {'pass':>5}")
    print(f"  {'─'*74}")

    for rank, entry in enumerate(ranked, 1):
        neg_score, seed, world, substrate, factions, adj, details = entry
        score_val = -neg_score
        d = details
        print(
            f"  {rank:>4}  {seed:>8}  {score_val:>8.4f}  "
            f"{d['reach_centroid_lat']:>7.2f}  {d['lattice_centroid_lat']:>6.2f}  "
            f"{d['min_cross_gc_rad']:>7.4f}  "
            f"{d['lattice_mean_gc_rad']:>6.4f}  {d['reach_mean_gc_rad']:>6.4f}  "
            f"{'Y' if (d['reach_has_pu'] and d['lattice_has_pu']) else 'N':>4}  "
            f"{'PASS' if d['hard_pass'] else 'soft':>5}"
        )

        out_path = os.path.join(out_dir, f"candidate_{seed:07d}.json")
        payload  = world_to_json(world, substrate, factions, adj, details)
        with open(out_path, "w") as f:
            json.dump(payload, f, indent="\t")

    print(f"\nWrote {len(ranked)} JSONs to {out_dir}/")
    hard_in_top = sum(1 for e in ranked if e[6]["hard_pass"])
    print(f"{hard_in_top} of top-{top_k} are hard-pass (all 4 constraints satisfied).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
