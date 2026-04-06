"""
Emergent-outcome loss function for Aeolia history engine parameter optimizer.

28 individual loss terms (spec calls them "27" but counts 28 across categories)
covering geography, agriculture, technology, ore access, historical shape,
political economy, population, and epidemiology.

Design principles
-----------------
- sq_relu(x) = max(0, x)^2 for ALL penalty terms
- All 28 unweighted terms produce loss in [0, ~5] range
- No crop name identity checks, no absolute tech level targets (except emergent
  nuclear test), no sovereignty band targets, no era distribution percentages
- compute_loss accepts the expanded sim_output dict from sim_proxy.simulate()
- Multi-seed: evaluate_seeds evaluates across 5+ seeds and penalises variance

Typical usage
-------------
    from loss import compute_loss, LossWeights, evaluate_seeds
    result = simulate(world, params, seed=42)
    lr = compute_loss(result)
    print(lr.total, lr.components)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Backward-compat stub
# ---------------------------------------------------------------------------

DEFAULT_TARGETS = None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sq_relu(x: float) -> float:
    """Squared ReLU — zero inside the acceptable range, quadratic outside."""
    return max(0.0, x) ** 2


# Keep internal alias
_sq_relu = sq_relu


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(_mean([(v - m) ** 2 for v in values]))


def _gini(values: list) -> float:
    """Gini coefficient over a list of non-negative values."""
    if not values or sum(values) == 0:
        return 0.0
    n = len(values)
    s = sorted(float(v) for v in values)
    total = sum(s)
    cumsum = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(s))
    return cumsum / (n * total)


def _spearman(xs: list, ys: list) -> float:
    """Spearman rank correlation for two equal-length lists."""
    n = len(xs)
    if n < 3:
        return 0.0

    def _ranks(vals):
        indexed = sorted(enumerate(vals), key=lambda iv: iv[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx, ry = _ranks(xs), _ranks(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    denom = math.sqrt(
        sum((rx[i] - mx) ** 2 for i in range(n))
        * sum((ry[i] - my) ** 2 for i in range(n))
    )
    return num / denom if denom > 1e-9 else 0.0


# ---------------------------------------------------------------------------
# Geometry helper
# ---------------------------------------------------------------------------

def _gc_dist(archs: list, i: int, j: int) -> float:
    """Great-circle distance in radians between arch i and arch j."""
    dot = (
        archs[i]["cx"] * archs[j]["cx"]
        + archs[i]["cy"] * archs[j]["cy"]
        + archs[i]["cz"] * archs[j]["cz"]
    )
    return math.acos(max(-1.0, min(1.0, dot)))


def _mean_pairwise_gc(archs: list, indices: list) -> float:
    """Mean pairwise great-circle distance (radians) among a set of arch indices."""
    dists = []
    for a in range(len(indices)):
        for b in range(a + 1, len(indices)):
            dists.append(_gc_dist(archs, indices[a], indices[b]))
    return _mean(dists) if dists else 0.0


# ---------------------------------------------------------------------------
# Crop distance helper (mirrors history_engine._crop_distance exactly)
# ---------------------------------------------------------------------------

_TROPICAL = frozenset(["paddi", "taro", "sago"])
_TEMPERATE = frozenset(["emmer", "papa"])


def crop_distance(contactor: str, contacted: str) -> float:
    if contactor == contacted:
        return 0.2
    ct = contactor in _TROPICAL
    cd = contacted in _TROPICAL
    ce = contactor in _TEMPERATE
    de = contacted in _TEMPERATE
    if (ct and cd) or (ce and de):
        return 0.5
    if frozenset([contactor, contacted]) == frozenset(["paddi", "papa"]):
        return 1.0
    return 0.8


# ---------------------------------------------------------------------------
# LossWeights — per-term
# ---------------------------------------------------------------------------

@dataclass
class LossWeights:
    # Geography
    lattice_density:    float = 1.0
    reach_spread:       float = 1.0
    lattice_latitude:   float = 1.0
    reach_latitude:     float = 1.0
    lattice_shelf:      float = 1.0
    civ_gap:            float = 1.0
    peak_asymmetry:     float = 0.5
    edge_topology:      float = 0.5
    # Agriculture
    climate_crop:       float = 1.0
    yield_asymmetry:    float = 1.0
    # Technology
    industrial_convergence: float = 1.5
    nav_weapons_coupling:   float = 1.0
    security_dilemma:       float = 1.5
    nuclear_emergence:      float = 2.0
    # Ore access
    pu_gate:            float = 2.0
    supply_chain:       float = 1.5
    cu_tech_lead:       float = 1.0
    au_priority:        float = 0.5
    # Historical shape
    serial_horizon:     float = 1.0
    maritime_asymmetry: float = 1.0
    colonial_extraction: float = 1.5
    nuclear_convergence: float = 1.0
    # Political economy
    df_timing:          float = 2.0
    sov_ordering:       float = 1.5
    sov_recovery:       float = 1.5
    # Population
    pop_ratio:          float = 1.0
    pop_inequality:     float = 0.5
    # Epidemiology
    epi_correlation:    float = 1.5


DEFAULT_WEIGHTS = LossWeights()


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class LossResult:
    total:      float
    components: dict   # term_name -> weighted scalar
    details:    dict   # term_name -> raw diagnostics

    def __repr__(self) -> str:
        comp_str = "  ".join(f"{k}={v:.4f}" for k, v in self.components.items())
        return f"LossResult(total={self.total:.4f}  [{comp_str}])"

    def summary(self) -> str:
        lines = [f"Total loss: {self.total:.4f}"]
        for k, v in self.components.items():
            lines.append(f"  {k:24s}: {v:.4f}")
        return "\n".join(lines)


@dataclass
class MultiSeedResult:
    total:    float       # mean + variance_weight * std
    mean:     float
    std:      float
    per_seed: dict        # seed -> LossResult

    def component_means(self) -> dict:
        all_seeds = list(self.per_seed.values())
        if not all_seeds:
            return {}
        keys = list(all_seeds[0].components.keys())
        return {k: _mean([lr.components[k] for lr in all_seeds]) for k in keys}

    def component_stds(self) -> dict:
        all_seeds = list(self.per_seed.values())
        if not all_seeds:
            return {}
        keys = list(all_seeds[0].components.keys())
        return {k: _std([lr.components[k] for lr in all_seeds]) for k in keys}

    def __repr__(self) -> str:
        return (
            f"MultiSeedResult(total={self.total:.4f}  mean={self.mean:.4f}"
            f"  std={self.std:.4f}  n_seeds={len(self.per_seed)})"
        )


# ---------------------------------------------------------------------------
# GEOGRAPHY — terms 1–8
# ---------------------------------------------------------------------------

def _term_lattice_density(archs: list, states: list) -> tuple:
    """Term 1: mean pairwise gc_dist between Lattice-faction archs < 0.6 rad."""
    lat_idxs = [i for i, s in enumerate(states) if s["faction"] == "lattice"]
    if len(lat_idxs) < 2:
        return 2.0, {"note": "fewer than 2 lattice archs", "n_lattice": len(lat_idxs)}
    mean_dist = _mean_pairwise_gc(archs, lat_idxs)
    loss = sq_relu(mean_dist - 0.6) * 4.0
    return min(loss, 10.0), {"mean_dist_rad": mean_dist, "n_lattice": len(lat_idxs)}


def _term_reach_spread(archs: list, states: list) -> tuple:
    """Term 2: mean pairwise gc_dist between Reach-faction archs > 0.8 rad."""
    reach_idxs = [i for i, s in enumerate(states) if s["faction"] == "reach"]
    if len(reach_idxs) < 2:
        return 2.0, {"note": "fewer than 2 reach archs", "n_reach": len(reach_idxs)}
    mean_dist = _mean_pairwise_gc(archs, reach_idxs)
    loss = sq_relu(0.8 - mean_dist) * 4.0
    return min(loss, 10.0), {"mean_dist_rad": mean_dist, "n_reach": len(reach_idxs)}


def _term_lattice_latitude(substrate: list, states: list) -> tuple:
    """Term 3: centroid abs_latitude of Lattice-faction archs in tropical band (<= 28 deg)."""
    lat_idxs = [i for i, s in enumerate(states) if s["faction"] == "lattice"]
    if not lat_idxs or not substrate:
        return 1.0, {"note": "no lattice archs or no substrate"}
    centroid_lat = _mean([
        substrate[i]["climate"]["abs_latitude"]
        for i in lat_idxs if i < len(substrate)
    ])
    loss = sq_relu(centroid_lat - 28.0) * 0.01
    return min(loss, 10.0), {"centroid_abs_lat": centroid_lat}


def _term_reach_latitude(substrate: list, states: list) -> tuple:
    """Term 4: centroid abs_latitude of Reach-faction archs in mid-latitude band (35–55 deg)."""
    reach_idxs = [i for i, s in enumerate(states) if s["faction"] == "reach"]
    if not reach_idxs or not substrate:
        return 1.0, {"note": "no reach archs or no substrate"}
    centroid_lat = _mean([
        substrate[i]["climate"]["abs_latitude"]
        for i in reach_idxs if i < len(substrate)
    ])
    loss = (sq_relu(35.0 - centroid_lat) + sq_relu(centroid_lat - 55.0)) * 0.01
    return min(loss, 10.0), {"centroid_abs_lat": centroid_lat}


def _term_lattice_shelf(substrate: list, states: list, archs: list) -> tuple:
    """Term 5: fraction of Lattice-faction archs with shelf_r >= 0.08 AND tidal_range >= 2.0."""
    lat_idxs = [i for i, s in enumerate(states) if s["faction"] == "lattice"]
    if not lat_idxs or not substrate or not archs:
        return 2.0, {"note": "no lattice archs, substrate, or archs geometry"}
    qualifying = 0
    for i in lat_idxs:
        if i >= len(substrate) or i >= len(archs):
            continue
        shelf_r = archs[i].get("shelf_r", 0.0)
        tidal = substrate[i]["climate"].get("tidal_range", 0.0)
        if shelf_r >= 0.08 and tidal >= 2.0:
            qualifying += 1
    frac = qualifying / len(lat_idxs)
    loss = sq_relu(0.5 - frac) * 4.0
    return min(loss, 10.0), {"frac_qualifying": frac, "qualifying": qualifying, "n_lattice": len(lat_idxs)}


def _term_civ_gap(archs: list, states: list) -> tuple:
    """Term 6: min pairwise gc_dist between any Reach-faction arch and any Lattice-faction arch > 0.5 rad."""
    reach_idxs = [i for i, s in enumerate(states) if s["faction"] == "reach"]
    lat_idxs = [i for i, s in enumerate(states) if s["faction"] == "lattice"]
    if not reach_idxs or not lat_idxs:
        return 2.0, {"note": "missing reach or lattice archs"}
    min_cross = min(
        _gc_dist(archs, i, j)
        for i in reach_idxs
        for j in lat_idxs
    )
    loss = sq_relu(0.5 - min_cross) * 4.0
    return min(loss, 10.0), {"min_cross_dist_rad": min_cross}


def _term_peak_asymmetry(archs: list, states: list) -> tuple:
    """Term 7: mean peak count of Lattice-faction > mean peak count of Reach-faction."""
    lat_idxs = [i for i, s in enumerate(states) if s["faction"] == "lattice"]
    reach_idxs = [i for i, s in enumerate(states) if s["faction"] == "reach"]
    if not lat_idxs or not reach_idxs or not archs:
        return 0.5, {"note": "insufficient faction archs or no archs geometry"}
    lattice_peaks = _mean([len(archs[i].get("peaks", [])) for i in lat_idxs if i < len(archs)])
    reach_peaks = _mean([len(archs[i].get("peaks", [])) for i in reach_idxs if i < len(archs)])
    # Penalty if Reach has more peaks than Lattice
    loss = sq_relu(reach_peaks - lattice_peaks) * 0.1
    return min(loss, 10.0), {"lattice_mean_peaks": lattice_peaks, "reach_mean_peaks": reach_peaks}


def _term_edge_topology(archs: list, states: list) -> tuple:
    """Term 8: mean pairwise gc_dist of Reach > mean pairwise gc_dist of Lattice (Reach more spread, Lattice denser)."""
    lat_idxs = [i for i, s in enumerate(states) if s["faction"] == "lattice"]
    reach_idxs = [i for i, s in enumerate(states) if s["faction"] == "reach"]
    if len(lat_idxs) < 2 or len(reach_idxs) < 2:
        return 1.0, {"note": "insufficient faction archs for pairwise distance"}
    lattice_mean = _mean_pairwise_gc(archs, lat_idxs)
    reach_mean = _mean_pairwise_gc(archs, reach_idxs)
    # Penalty if Lattice mean dist >= Reach mean dist (Lattice should be denser)
    loss = sq_relu(lattice_mean - reach_mean) * 4.0
    return min(loss, 10.0), {"lattice_mean_dist": lattice_mean, "reach_mean_dist": reach_mean}


# ---------------------------------------------------------------------------
# AGRICULTURE — terms 9–10
# ---------------------------------------------------------------------------

def _term_climate_crop(substrate: list, states: list) -> tuple:
    """Term 9: climate->crop emergence coherence."""
    hydraulic_crops = {"paddi", "taro", "sago"}
    dryland_crops = {"emmer", "papa"}
    hydraulic_zones = {"tropical_wet", "tropical_dry"}
    dryland_zones = {"temperate_wet", "temperate_dry", "subpolar"}

    non_foraging = []
    incoherent = 0

    for i, sub in enumerate(substrate):
        if i >= len(states):
            break
        crop = sub["crops"].get("primary_crop", "")
        if not crop or crop == "forage" or crop == "":
            continue
        non_foraging.append(i)
        zone = sub["climate"].get("climate_zone", "")
        if crop in hydraulic_crops and zone not in hydraulic_zones:
            incoherent += 1
        elif crop in dryland_crops and zone not in dryland_zones:
            incoherent += 1
        # nori is always coherent; unknown crops are skipped

    if not non_foraging:
        return 0.0, {"note": "no non-foraging archs"}

    incoherent_frac = incoherent / len(non_foraging)
    loss = sq_relu(incoherent_frac - 0.15) * 5.0
    return min(loss, 10.0), {
        "incoherent_frac": incoherent_frac,
        "incoherent": incoherent,
        "n_non_foraging": len(non_foraging),
    }


def _term_yield_asymmetry(substrate: list) -> tuple:
    """Term 10: mean yield of hydraulic-primary-crop archs > mean yield of dryland-primary-crop archs."""
    hydraulic_set = {"paddi", "taro", "sago"}
    dryland_set = {"emmer", "papa"}

    hydraulic_yields = []
    dryland_yields = []

    for sub in substrate:
        crop = sub["crops"].get("primary_crop", "")
        y = sub["crops"].get("primary_yield", 0.0)
        if crop in hydraulic_set:
            hydraulic_yields.append(y)
        elif crop in dryland_set:
            dryland_yields.append(y)

    if not hydraulic_yields or not dryland_yields:
        return 1.0, {"note": "missing hydraulic or dryland yield data"}

    ratio = _mean(hydraulic_yields) / max(_mean(dryland_yields), 1e-9)
    loss = sq_relu(1.0 - ratio) * 2.0
    return min(loss, 10.0), {
        "hydraulic_mean_yield": _mean(hydraulic_yields),
        "dryland_mean_yield": _mean(dryland_yields),
        "ratio": ratio,
    }


# ---------------------------------------------------------------------------
# TECHNOLOGY — terms 11–14
# ---------------------------------------------------------------------------

def _term_industrial_convergence(
    tech_snapshots: dict,
    reach_arch: int,
    lattice_arch: int,
) -> tuple:
    """Term 11: when either hegemon crosses tech > 7, the other is within 1.5 points."""
    r_ind = tech_snapshots["after_industrial"][reach_arch]
    l_ind = tech_snapshots["after_industrial"][lattice_arch]
    gap = abs(r_ind - l_ind)

    if r_ind > 7 or l_ind > 7:
        loss = sq_relu(gap - 1.5) * 2.0
    else:
        loss = sq_relu(7.0 - max(r_ind, l_ind)) * 0.5

    return min(loss, 10.0), {
        "r_tech_ind": r_ind,
        "l_tech_ind": l_ind,
        "gap_at_ind": gap,
        "either_crosses_7": r_ind > 7 or l_ind > 7,
    }


def _term_nav_weapons_coupling(
    tech_snapshots: dict,
    states: list,
    epi_log: list,
    reach_arch: int,
    lattice_arch: int,
) -> tuple:
    """Term 12: correlation between serial-era Reach network size and tech growth."""
    dtech = (
        tech_snapshots["after_industrial"][reach_arch]
        - tech_snapshots["after_antiquity"][reach_arch]
    )
    # Serial contacts: non-hegemon archs with eraOfContact=="sail" and faction=="reach"
    n_serial = sum(
        1
        for i, s in enumerate(states)
        if i not in (reach_arch, lattice_arch)
        and s.get("eraOfContact") == "sail"
        and s.get("faction") == "reach"
    )
    coupling = dtech * n_serial / max(1, n_serial + dtech)
    loss = sq_relu(0.5 - coupling) * 2.0
    return min(loss, 10.0), {
        "dtech_reach": dtech,
        "n_serial_reach": n_serial,
        "coupling": coupling,
    }


def _term_security_dilemma(
    tech_snapshots: dict,
    df_year: Optional[int],
    reach_arch: int,
    lattice_arch: int,
) -> tuple:
    """Term 13: Dark Forest break year < first year either hegemon crosses tech > 7."""
    # Approximate year Reach crosses tech 7 by lerping colonial->industrial era
    # Era boundaries: serial->colonial is ~-5000 to -2000; colonial->industrial is -2000 to -500
    def _crossing_year(col_val, ind_val):
        if col_val <= 7.0 <= ind_val:
            # lerp: colonial era is -2000, industrial era ends at -500
            frac = (7.0 - col_val) / max(1e-6, ind_val - col_val)
            return -2000 + frac * 1500
        elif ind_val > 7.0:
            return -2000.0  # already crossed by colonial era
        else:
            return 0.0  # never crossed

    r_col = tech_snapshots["after_colonial"][reach_arch]
    r_ind = tech_snapshots["after_industrial"][reach_arch]
    l_col = tech_snapshots["after_colonial"][lattice_arch]
    l_ind = tech_snapshots["after_industrial"][lattice_arch]

    t_r = _crossing_year(r_col, r_ind)
    t_l = _crossing_year(l_col, l_ind)

    t_tech7 = min(t for t in [t_r, t_l] if t != 0.0) if any(t != 0.0 for t in [t_r, t_l]) else 0.0

    if df_year is None or t_tech7 == 0.0:
        loss = 3.0
        details = {"note": "no DF or neither hegemon crosses tech 7", "df_year": df_year, "t_tech7": t_tech7}
    elif df_year >= t_tech7:
        loss = 0.0
        details = {"note": "DF broke before tech 7 — correct", "df_year": df_year, "t_tech7": t_tech7}
    else:
        loss = sq_relu(t_tech7 - df_year) / (200.0 ** 2) * 5.0
        details = {"df_year": df_year, "t_tech7": t_tech7}

    return min(loss, 10.0), details


def _term_nuclear_emergence(nuclear_emergence: Optional[bool]) -> tuple:
    """Term 14: emergent nuclear test — did both hegemons reach tech > 9 without floors?"""
    if nuclear_emergence is None:
        loss = 0.0
        details = {"note": "not evaluated"}
    elif nuclear_emergence is False:
        loss = 3.0
        details = {"note": "preconditions insufficient for nuclear emergence"}
    else:
        loss = 0.0
        details = {"note": "nuclear emerged organically"}
    return min(loss, 10.0), details


# ---------------------------------------------------------------------------
# ORE ACCESS — terms 15–18
# ---------------------------------------------------------------------------

def _term_pu_gate(reach_pu_access: bool, lattice_pu_access: bool) -> tuple:
    """Term 15: both hegemons have Pu access."""
    loss = (0.0 if reach_pu_access else 2.0) + (0.0 if lattice_pu_access else 2.0)
    return min(loss, 10.0), {
        "reach_pu": reach_pu_access,
        "lattice_pu": lattice_pu_access,
    }


def _term_supply_chain(
    substrate: list,
    states: list,
    adj: dict,
    reach_arch: int,
    lattice_arch: int,
    reach_pu_access: bool,
    lattice_pu_access: bool,
) -> tuple:
    """Term 16: no hegemon's ONLY Pu source has sovereignty < 0.2."""

    def _is_robust(hegemon_idx):
        # If hegemon owns Pu itself, robust
        if substrate and hegemon_idx < len(substrate):
            if substrate[hegemon_idx]["minerals"].get("Pu", False):
                return True
        # Otherwise check neighbors
        neighbors = adj.get(hegemon_idx, [])
        pu_neighbors = [
            nb for nb in neighbors
            if nb < len(substrate) and substrate[nb]["minerals"].get("Pu", False)
        ]
        if not pu_neighbors:
            return True  # no Pu neighbors to assess
        # Robust if at least one neighbor has sovereignty >= 0.2
        return any(
            states[nb]["sovereignty"] >= 0.2
            for nb in pu_neighbors
            if nb < len(states)
        )

    reach_robust = _is_robust(reach_arch)
    lattice_robust = _is_robust(lattice_arch)
    loss = (0.0 if reach_robust else 2.0) + (0.0 if lattice_robust else 2.0)
    return min(loss, 10.0), {
        "reach_robust": reach_robust,
        "lattice_robust": lattice_robust,
    }


def _term_cu_tech_lead(substrate: list, states: list) -> tuple:
    """Term 17: Cu-bearing serial-era archs have measurably higher tech than non-Cu serial-era archs."""
    cu_tech = []
    non_cu_tech = []
    for i, s in enumerate(states):
        if i >= len(substrate):
            break
        if s.get("eraOfContact") != "sail":
            continue
        has_cu = substrate[i]["minerals"].get("Cu", False)
        if has_cu:
            cu_tech.append(s["tech"])
        else:
            non_cu_tech.append(s["tech"])

    if not cu_tech or not non_cu_tech:
        return 0.0, {"note": "insufficient data for Cu tech lead"}

    delta = _mean(cu_tech) - _mean(non_cu_tech)
    loss = sq_relu(0.3 - delta) * 2.0
    return min(loss, 10.0), {
        "cu_serial_mean_tech": _mean(cu_tech),
        "non_cu_serial_mean_tech": _mean(non_cu_tech),
        "delta": delta,
        "n_cu": len(cu_tech),
        "n_non_cu": len(non_cu_tech),
    }


def _term_au_priority(
    substrate: list,
    states: list,
    contact_years: dict,
    reach_arch: int,
    lattice_arch: int,
) -> tuple:
    """Term 18: Au-bearing archs contacted earlier on average than non-Au archs (excluding cores)."""
    core_set = {reach_arch, lattice_arch}
    au_years = []
    non_au_years = []

    for i, s in enumerate(states):
        if i in core_set:
            continue
        if i not in contact_years:
            continue
        if i >= len(substrate):
            continue
        has_au = substrate[i]["minerals"].get("Au", False)
        yr = contact_years[i]
        if has_au:
            au_years.append(yr)
        else:
            non_au_years.append(yr)

    if not au_years or not non_au_years:
        return 0.0, {"note": "insufficient data for Au contact priority"}

    # Positive delta means Au was contacted earlier (more negative year = older = earlier)
    delta = _mean(non_au_years) - _mean(au_years)
    loss = sq_relu(-delta) * 0.0001
    return min(loss, 10.0), {
        "au_mean_year": _mean(au_years),
        "non_au_mean_year": _mean(non_au_years),
        "delta_years": delta,
        "n_au": len(au_years),
        "n_non_au": len(non_au_years),
    }


# ---------------------------------------------------------------------------
# HISTORICAL SHAPE — terms 19–22
# ---------------------------------------------------------------------------

def _term_serial_horizon(states: list) -> tuple:
    """Term 19: max hop_count achieved by serial-era contacts > 3."""
    serial_hops = [
        s["hopCount"]
        for s in states
        if s.get("eraOfContact") == "sail"
    ]
    max_hops = max(serial_hops) if serial_hops else 0
    loss = sq_relu(3 - max_hops) * 1.0
    return min(loss, 10.0), {
        "max_serial_hops": max_hops,
        "n_serial": len(serial_hops),
    }


def _term_maritime_asymmetry(states: list, reach_arch: int, lattice_arch: int) -> tuple:
    """Term 20: for Reach, the known/governed ratio (contacted / colonized) in colonial era > 1.5."""
    reach_colonial_contacts = sum(
        1
        for s in states
        if s.get("faction") == "reach"
        and s.get("eraOfContact") in ("sail", "colonial")
    )
    reach_colonial_colonies = sum(
        1
        for s in states
        if s.get("status") == "colony"
        and s.get("faction") == "reach"
    )

    if reach_colonial_colonies == 0:
        return 2.0, {
            "note": "no reach colonies",
            "reach_contacts": reach_colonial_contacts,
            "reach_colonies": reach_colonial_colonies,
        }

    ratio = reach_colonial_contacts / reach_colonial_colonies
    loss = sq_relu(1.5 - ratio) * 1.0
    return min(loss, 10.0), {
        "reach_contacts": reach_colonial_contacts,
        "reach_colonies": reach_colonial_colonies,
        "ratio": ratio,
    }


def _term_colonial_extraction(
    states: list,
    colony_sov_pre_nuclear: dict,
    pop_snapshots: dict,
    epi_log: list,
    reach_arch: int,
) -> tuple:
    """Term 21: three sub-conditions — colony sovereignty, pop flows, epi correlation."""
    # a) Mean colony sovereignty (at colonial era) < 0.3
    if colony_sov_pre_nuclear:
        mean_col_sov = _mean(list(colony_sov_pre_nuclear.values()))
        loss_a = sq_relu(mean_col_sov - 0.3) * 5.0
    else:
        loss_a = 2.0
        mean_col_sov = None

    # b) Pop flows toward metropole: reach pop growth ratio vs colony mean
    try:
        reach_pop_serial = pop_snapshots["after_serial"][reach_arch]
        reach_pop_colonial = pop_snapshots["after_colonial"][reach_arch]
        ratio = reach_pop_colonial / max(1, reach_pop_serial)
    except (KeyError, IndexError, TypeError):
        ratio = 1.0

    if ratio > 1.2:
        loss_b = 0.0
    else:
        loss_b = sq_relu(1.2 - ratio) * 2.0

    # c) Epi mortality correlates with crop distance in colonial era
    colonial_entries = [e for e in (epi_log or []) if e.get("era") == "colonial"]
    if len(colonial_entries) >= 5:
        distances = [crop_distance(e["contactor_crop"], e["contacted_crop"]) for e in colonial_entries]
        mortalities = [e["mortality_rate"] for e in colonial_entries]
        rho = _spearman(distances, mortalities)
        loss_c = sq_relu(0.3 - rho) * 3.0
    else:
        loss_c = 1.0
        rho = None

    loss = (loss_a + loss_b + loss_c) / 3.0
    return min(loss, 10.0), {
        "mean_col_sov_pre_nuclear": mean_col_sov,
        "loss_a": loss_a,
        "reach_pop_growth_ratio": ratio,
        "loss_b": loss_b,
        "colonial_epi_spearman": rho,
        "n_colonial_epi": len(colonial_entries),
        "loss_c": loss_c,
    }


def _term_nuclear_convergence(
    tech_snapshots: dict,
    states: list,
    reach_arch: int,
    lattice_arch: int,
) -> tuple:
    """Term 22: tech gap at nuclear era < tech gap at peak colonial era."""
    gap_colonial = abs(
        tech_snapshots["after_colonial"][reach_arch]
        - tech_snapshots["after_colonial"][lattice_arch]
    )
    gap_nuclear = abs(states[reach_arch]["tech"] - states[lattice_arch]["tech"])
    loss = sq_relu(gap_nuclear - gap_colonial) * 2.0
    return min(loss, 10.0), {
        "gap_colonial": gap_colonial,
        "gap_nuclear": gap_nuclear,
    }


# ---------------------------------------------------------------------------
# POLITICAL ECONOMY — terms 23–25
# ---------------------------------------------------------------------------

def _term_df_timing(df_year: Optional[int]) -> tuple:
    """Term 23: Dark Forest break within -200 to -40 BP."""
    if df_year is None:
        return 4.0, {"note": "no Dark Forest break"}
    loss = (
        sq_relu(-200 - df_year) + sq_relu(df_year - (-40))
    ) / (80.0 ** 2) * 4.0
    return min(loss, 10.0), {"df_year": df_year}


def _term_sov_ordering(states: list) -> tuple:
    """Term 24: monotonic mean(colonies) < mean(garrisons) < mean(clients) < mean(tributaries) < mean(contacted/pulse)."""
    STATUS_ORDER = ["colony", "garrison", "tributary", "client", "pulse", "contacted", "core"]
    sov_by_status = {}
    for st in STATUS_ORDER:
        vals = [s["sovereignty"] for s in states if s["status"] == st]
        if vals:
            sov_by_status[st] = _mean(vals)

    ordered = [st for st in STATUS_ORDER if st in sov_by_status]
    loss = 0.0
    for k in range(len(ordered) - 1):
        lo_st = ordered[k]
        hi_st = ordered[k + 1]
        sov_lo = sov_by_status[lo_st]
        sov_hi = sov_by_status[hi_st]
        loss += sq_relu(sov_lo - sov_hi) * 2.0

    n_pairs = max(len(ordered) - 1, 1)
    loss = loss / n_pairs
    return min(loss, 10.0), {
        "sov_by_status": {k: round(v, 3) for k, v in sov_by_status.items()},
        "n_ordered_groups": len(ordered),
    }


def _term_sov_recovery(
    states: list,
    colony_sov_pre_nuclear: dict,
) -> tuple:
    """Term 25: nuclear-era colony sovereignty > colonial-era colony sovereignty."""
    nuclear_col = [s["sovereignty"] for s in states if s["status"] == "colony"]
    if not nuclear_col or not colony_sov_pre_nuclear:
        return 0.0, {"note": "no colonies or no pre-nuclear snapshot"}

    nuclear_sov = _mean(nuclear_col)
    colonial_sov = _mean(list(colony_sov_pre_nuclear.values()))
    loss = sq_relu(colonial_sov - nuclear_sov) * 5.0
    return min(loss, 10.0), {
        "nuclear_colony_sov": nuclear_sov,
        "colonial_colony_sov": colonial_sov,
    }


# ---------------------------------------------------------------------------
# POPULATION — terms 26–27
# ---------------------------------------------------------------------------

def _term_pop_ratio(states: list, reach_arch: int, lattice_arch: int) -> tuple:
    """Term 26: Lattice > Reach population ratio > 1.0."""
    r_pop = states[reach_arch]["population"]
    l_pop = states[lattice_arch]["population"]
    ratio = l_pop / max(1, r_pop)
    loss = sq_relu(1.0 - ratio) * 2.0
    return min(loss, 10.0), {
        "lattice_pop": l_pop,
        "reach_pop": r_pop,
        "ratio": ratio,
    }


def _term_pop_inequality(states: list) -> tuple:
    """Term 27: Gini of all arch populations in [0.25, 0.80]."""
    pops = [float(s["population"]) for s in states if s["population"] > 0]
    if not pops:
        return 2.0, {"note": "no population data"}
    gini = _gini(pops)
    loss = sq_relu(0.25 - gini) * 4.0 + sq_relu(gini - 0.80) * 4.0
    return min(loss, 10.0), {"gini": gini, "n_archs": len(pops)}


# ---------------------------------------------------------------------------
# EPIDEMIOLOGY — term 28
# ---------------------------------------------------------------------------

def _term_epi_correlation(epi_log: list) -> tuple:
    """Term 28: Spearman rank correlation of mortality with crop distance > 0.3."""
    if not epi_log or len(epi_log) < 5:
        return 1.0, {"note": "fewer than 5 epi events", "n_events": len(epi_log) if epi_log else 0}

    distances = [
        crop_distance(e.get("contactor_crop", ""), e.get("contacted_crop", ""))
        for e in epi_log
    ]
    mortalities = [e.get("mortality_rate", 0.0) for e in epi_log]
    rho = _spearman(distances, mortalities)
    loss = sq_relu(0.3 - rho) * 3.0
    return min(loss, 10.0), {
        "spearman_rho": rho,
        "n_events": len(epi_log),
    }


# ---------------------------------------------------------------------------
# Nuclear emergence check helper
# ---------------------------------------------------------------------------

def run_nuclear_emergence_check(world: dict, params, seed: int = 42) -> bool:
    """
    Run sim without tech floors; returns True if both hegemons reach tech > 9,
    indicating nuclear capability emerged from preconditions alone.
    """
    from sim_proxy import simulate, SimParams
    import copy

    params_nofloor = copy.copy(params)
    for attr in ["tech_floor_reach_ind", "tech_floor_lattice_ind"]:
        if hasattr(params_nofloor, attr):
            setattr(params_nofloor, attr, 0.0)

    result = simulate(world, params_nofloor, seed=seed)
    r_tech = result["states"][result["reach_arch"]]["tech"]
    l_tech = result["states"][result["lattice_arch"]]["tech"]
    return r_tech > 9.0 and l_tech > 9.0


# ---------------------------------------------------------------------------
# Adjacency helper
# ---------------------------------------------------------------------------

def _build_adj(plateau_edges: list) -> dict:
    """Build adjacency dict {arch_idx: [neighbors]} from plateau_edges."""
    adj = {}
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    return adj


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_loss(
    sim_output: dict,
    weights: Optional[LossWeights] = None,
    nuclear_emergence: Optional[bool] = None,
    # Legacy keyword arguments kept for backward compatibility — unused
    substrate: Optional[list] = None,
    targets: Optional[object] = None,
    reach_arch: Optional[int] = None,
    lattice_arch: Optional[int] = None,
    world: Optional[dict] = None,
    params: Optional[object] = None,
) -> LossResult:
    """
    Compute composite emergent-outcome loss from simulation output.

    Parameters
    ----------
    sim_output : dict
        Output from sim_proxy.simulate(). Required keys: states, df_year.
        Also consumes: epi_log, substrate, reach_arch, lattice_arch, archs,
        plateau_edges, contact_years, hop_count, mineral_access, tech_snapshots,
        pop_snapshots, colony_sov_pre_nuclear, reach_pu_access, lattice_pu_access.
    weights : LossWeights | None
    nuclear_emergence : bool | None
        Pre-computed result of run_nuclear_emergence_check, or None to skip.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # Extract all data from sim_output
    states = sim_output["states"]
    df_year = sim_output.get("df_year")
    epi_log = sim_output.get("epi_log") or []

    # substrate — accept from kwarg (legacy) or sim_output
    if substrate is None:
        substrate = sim_output.get("substrate") or []

    # Normalize flat substrate format to nested if needed
    def _norm_sub(sub_list):
        if not sub_list:
            return sub_list
        if "crops" in (sub_list[0] or {}):
            return sub_list
        return [
            {
                "crops": {
                    "primary_crop":  s.get("primary_crop", "emmer"),
                    "primary_yield": s.get("primary_yield", 0.5),
                },
                "climate": {
                    "abs_latitude":       s.get("abs_latitude", 30.0),
                    "latitude":           s.get("latitude", 30.0),
                    "mean_temp":          s.get("mean_temp", 18.0),
                    "effective_rainfall": s.get("effective_rainfall", 1000.0),
                    "tidal_range":        s.get("tidal_range", 2.0),
                    "climate_zone":       s.get("climate_zone", "temperate_wet"),
                    "wind_belt":          s.get("wind_belt", "westerlies"),
                    "upwelling":          s.get("upwelling", 0.1),
                },
                "minerals": s.get("minerals", {}),
            }
            for s in sub_list
        ]

    substrate = _norm_sub(substrate)

    archs = sim_output.get("archs") or []
    plateau_edges = sim_output.get("plateau_edges") or []
    contact_years = sim_output.get("contact_years") or {}
    tech_snapshots = sim_output.get("tech_snapshots") or {}
    pop_snapshots = sim_output.get("pop_snapshots") or {}
    colony_sov_pre_nuclear = sim_output.get("colony_sov_pre_nuclear") or {}
    reach_pu_access = sim_output.get("reach_pu_access", False)
    lattice_pu_access = sim_output.get("lattice_pu_access", False)

    # Infer core arch indices
    if reach_arch is None:
        reach_arch = sim_output.get("reach_arch")
        if reach_arch is None:
            reach_arch = next(
                (i for i, s in enumerate(states)
                 if s["faction"] == "reach" and s["status"] == "core"), 0)
    if lattice_arch is None:
        lattice_arch = sim_output.get("lattice_arch")
        if lattice_arch is None:
            lattice_arch = next(
                (i for i, s in enumerate(states)
                 if s["faction"] == "lattice" and s["status"] == "core"), 1)

    # Build adjacency from plateau_edges
    adj = _build_adj(plateau_edges)

    # Provide default tech_snapshots structure if absent
    def _safe_snapshot(key, idx, fallback=0.0):
        snap = tech_snapshots.get(key)
        if snap is None:
            return fallback
        if isinstance(snap, list) and idx < len(snap):
            return snap[idx]
        return fallback

    # Ensure tech_snapshots dicts have list entries (synthesize from states if missing)
    n = len(states)
    for snap_key in ["after_antiquity", "after_serial", "after_colonial", "after_industrial"]:
        if snap_key not in tech_snapshots or tech_snapshots[snap_key] is None:
            tech_snapshots[snap_key] = [s["tech"] * 0.5 for s in states]

    for snap_key in ["after_serial", "after_colonial", "after_industrial"]:
        if snap_key not in pop_snapshots or pop_snapshots[snap_key] is None:
            pop_snapshots[snap_key] = [s["population"] for s in states]

    # --- Evaluate all 28 terms ---

    # Geography (1–8)
    t1_loss, t1_det = _term_lattice_density(archs, states) if archs else (1.0, {"note": "no archs"})
    t2_loss, t2_det = _term_reach_spread(archs, states) if archs else (1.0, {"note": "no archs"})
    t3_loss, t3_det = _term_lattice_latitude(substrate, states)
    t4_loss, t4_det = _term_reach_latitude(substrate, states)
    t5_loss, t5_det = _term_lattice_shelf(substrate, states, archs) if archs else (1.0, {"note": "no archs"})
    t6_loss, t6_det = _term_civ_gap(archs, states) if archs else (1.0, {"note": "no archs"})
    t7_loss, t7_det = _term_peak_asymmetry(archs, states) if archs else (0.5, {"note": "no archs"})
    t8_loss, t8_det = _term_edge_topology(archs, states) if archs else (0.5, {"note": "no archs"})

    # Agriculture (9–10)
    t9_loss, t9_det = _term_climate_crop(substrate, states)
    t10_loss, t10_det = _term_yield_asymmetry(substrate)

    # Technology (11–14)
    t11_loss, t11_det = _term_industrial_convergence(tech_snapshots, reach_arch, lattice_arch)
    t12_loss, t12_det = _term_nav_weapons_coupling(tech_snapshots, states, epi_log, reach_arch, lattice_arch)
    t13_loss, t13_det = _term_security_dilemma(tech_snapshots, df_year, reach_arch, lattice_arch)
    t14_loss, t14_det = _term_nuclear_emergence(nuclear_emergence)

    # Ore access (15–18)
    t15_loss, t15_det = _term_pu_gate(reach_pu_access, lattice_pu_access)
    t16_loss, t16_det = _term_supply_chain(substrate, states, adj, reach_arch, lattice_arch, reach_pu_access, lattice_pu_access)
    t17_loss, t17_det = _term_cu_tech_lead(substrate, states)
    t18_loss, t18_det = _term_au_priority(substrate, states, contact_years, reach_arch, lattice_arch)

    # Historical shape (19–22)
    t19_loss, t19_det = _term_serial_horizon(states)
    t20_loss, t20_det = _term_maritime_asymmetry(states, reach_arch, lattice_arch)
    t21_loss, t21_det = _term_colonial_extraction(states, colony_sov_pre_nuclear, pop_snapshots, epi_log, reach_arch)
    t22_loss, t22_det = _term_nuclear_convergence(tech_snapshots, states, reach_arch, lattice_arch)

    # Political economy (23–25)
    t23_loss, t23_det = _term_df_timing(df_year)
    t24_loss, t24_det = _term_sov_ordering(states)
    t25_loss, t25_det = _term_sov_recovery(states, colony_sov_pre_nuclear)

    # Population (26–27)
    t26_loss, t26_det = _term_pop_ratio(states, reach_arch, lattice_arch)
    t27_loss, t27_det = _term_pop_inequality(states)

    # Epidemiology (28)
    t28_loss, t28_det = _term_epi_correlation(epi_log)

    # Assemble weighted components
    components = {
        "lattice_density":       t1_loss  * weights.lattice_density,
        "reach_spread":          t2_loss  * weights.reach_spread,
        "lattice_latitude":      t3_loss  * weights.lattice_latitude,
        "reach_latitude":        t4_loss  * weights.reach_latitude,
        "lattice_shelf":         t5_loss  * weights.lattice_shelf,
        "civ_gap":               t6_loss  * weights.civ_gap,
        "peak_asymmetry":        t7_loss  * weights.peak_asymmetry,
        "edge_topology":         t8_loss  * weights.edge_topology,
        "climate_crop":          t9_loss  * weights.climate_crop,
        "yield_asymmetry":       t10_loss * weights.yield_asymmetry,
        "industrial_convergence": t11_loss * weights.industrial_convergence,
        "nav_weapons_coupling":  t12_loss * weights.nav_weapons_coupling,
        "security_dilemma":      t13_loss * weights.security_dilemma,
        "nuclear_emergence":     t14_loss * weights.nuclear_emergence,
        "pu_gate":               t15_loss * weights.pu_gate,
        "supply_chain":          t16_loss * weights.supply_chain,
        "cu_tech_lead":          t17_loss * weights.cu_tech_lead,
        "au_priority":           t18_loss * weights.au_priority,
        "serial_horizon":        t19_loss * weights.serial_horizon,
        "maritime_asymmetry":    t20_loss * weights.maritime_asymmetry,
        "colonial_extraction":   t21_loss * weights.colonial_extraction,
        "nuclear_convergence":   t22_loss * weights.nuclear_convergence,
        "df_timing":             t23_loss * weights.df_timing,
        "sov_ordering":          t24_loss * weights.sov_ordering,
        "sov_recovery":          t25_loss * weights.sov_recovery,
        "pop_ratio":             t26_loss * weights.pop_ratio,
        "pop_inequality":        t27_loss * weights.pop_inequality,
        "epi_correlation":       t28_loss * weights.epi_correlation,
    }
    total = sum(components.values())

    details = {
        "lattice_density":       t1_det,
        "reach_spread":          t2_det,
        "lattice_latitude":      t3_det,
        "reach_latitude":        t4_det,
        "lattice_shelf":         t5_det,
        "civ_gap":               t6_det,
        "peak_asymmetry":        t7_det,
        "edge_topology":         t8_det,
        "climate_crop":          t9_det,
        "yield_asymmetry":       t10_det,
        "industrial_convergence": t11_det,
        "nav_weapons_coupling":  t12_det,
        "security_dilemma":      t13_det,
        "nuclear_emergence":     t14_det,
        "pu_gate":               t15_det,
        "supply_chain":          t16_det,
        "cu_tech_lead":          t17_det,
        "au_priority":           t18_det,
        "serial_horizon":        t19_det,
        "maritime_asymmetry":    t20_det,
        "colonial_extraction":   t21_det,
        "nuclear_convergence":   t22_det,
        "df_timing":             t23_det,
        "sov_ordering":          t24_det,
        "sov_recovery":          t25_det,
        "pop_ratio":             t26_det,
        "pop_inequality":        t27_det,
        "epi_correlation":       t28_det,
    }

    return LossResult(total=total, components=components, details=details)


# ---------------------------------------------------------------------------
# Multi-seed evaluation
# ---------------------------------------------------------------------------

def evaluate_seeds(
    sim_outputs_by_seed: dict,
    weights: Optional[LossWeights] = None,
    variance_weight: float = 0.30,
    fail_penalty: float = 2.0,
    nuclear_emergence_by_seed: Optional[dict] = None,
) -> MultiSeedResult:
    """
    Evaluate loss across multiple seeds and penalise variance.

    Parameters
    ----------
    sim_outputs_by_seed : dict
        {seed: sim_output} mapping. At least 5 seeds recommended.
    weights : LossWeights | None
    variance_weight : float
        Weight applied to std(total_losses) in the aggregate score.
    fail_penalty : float
        Loss added for any seed that raised an exception.
    nuclear_emergence_by_seed : dict | None
        {seed: bool | None} mapping for nuclear emergence results.

    Returns
    -------
    MultiSeedResult
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    per_seed = {}
    for seed, sim_out in sim_outputs_by_seed.items():
        ne = None
        if nuclear_emergence_by_seed is not None:
            ne = nuclear_emergence_by_seed.get(seed)
        try:
            lr = compute_loss(sim_out, weights=weights, nuclear_emergence=ne)
        except Exception as e:
            # Synthesize a failed LossResult with penalty
            failed_components = {k: fail_penalty for k in LossWeights.__dataclass_fields__}
            lr = LossResult(
                total=fail_penalty * len(failed_components),
                components=failed_components,
                details={"error": str(e)},
            )
        per_seed[seed] = lr

    totals = [lr.total for lr in per_seed.values()]
    mean_total = _mean(totals)
    std_total = _std(totals)
    aggregate = mean_total + variance_weight * std_total

    return MultiSeedResult(
        total=aggregate,
        mean=mean_total,
        std=std_total,
        per_seed=per_seed,
    )
