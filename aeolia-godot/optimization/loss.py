"""
Emergent-outcome loss function for Aeolia history engine parameter optimization.

Eight weighted components verify that the simulation produces lore-faithful
macro-patterns WITHOUT hard-coding expected values for crop names, era
distribution percentages, or sovereignty band targets.

  geo          – topology asymmetry (hops, latitude, shelf, edge density)
  ag           – climate→yield coherence, hydraulic > dryland asymmetry
  tech         – industrial convergence, DF precedence, emergent nuclear test
  ore          – Pu access, Cu serial lead, Au contact timing
  hist_shape   – maritime asymmetry, colonial extraction signature, nuclear convergence
  poleco       – DF timing, sovereignty monotonic ordering, sovereignty recovery
  pop          – Lattice:Reach ratio, population Gini
  epi          – Spearman(mortality, crop_distance) rank correlation

Design principles
-----------------
- sq_relu penalties only (zero inside acceptable range, quadratic outside)
- All unweighted component losses in [0, ~5]
- No crop names hard-coded in loss terms
- No era distribution percentage targets
- No sovereignty band targets (monotonic ordering instead)
- Multi-seed: caller aggregates mean + λ·std; this module is single-seed

Typical usage
-------------
    from loss import compute_loss, LossWeights
    result = simulate(world, params, seed=42)
    lr = compute_loss(result, world=world, params=params)
    print(lr.total, lr.components)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _sq_relu(x: float) -> float:
    """Squared ReLU — zero inside the acceptable range, quadratic outside."""
    return max(0.0, x) ** 2


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


def _ranks(values: list) -> list:
    """Return rank of each element (1-indexed, average ranks for ties)."""
    n = len(values)
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and values[order[j + 1]] == values[order[j]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def _spearman(x: list, y: list) -> float:
    """Spearman rank correlation coefficient."""
    n = len(x)
    if n < 3:
        return 0.0
    rx = _ranks(x)
    ry = _ranks(y)
    d_sq = sum((rx[i] - ry[i]) ** 2 for i in range(n))
    denom = n * (n ** 2 - 1)
    return 1.0 - 6.0 * d_sq / denom if denom > 0 else 0.0


# ---------------------------------------------------------------------------
# Crop distance helper (mirrors history_engine._crop_distance exactly)
# ---------------------------------------------------------------------------

_TROPICAL  = frozenset(["paddi", "taro", "sago"])
_TEMPERATE = frozenset(["emmer", "papa"])


def crop_distance(contactor: str, contacted: str) -> float:
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
# Weights
# ---------------------------------------------------------------------------

@dataclass
class LossWeights:
    geo:        float = 1.0
    ag:         float = 1.0
    tech:       float = 1.5
    ore:        float = 1.0
    hist_shape: float = 1.0
    poleco:     float = 1.5
    pop:        float = 1.0
    epi:        float = 1.5


DEFAULT_WEIGHTS = LossWeights()


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class LossResult:
    total:      float
    components: dict   # str → weighted scalar loss per component
    details:    dict   # raw diagnostics per component

    def __repr__(self) -> str:
        comp_str = "  ".join(f"{k}={v:.4f}" for k, v in self.components.items())
        return f"LossResult(total={self.total:.4f}  [{comp_str}])"

    def summary(self) -> str:
        lines = [f"Total loss: {self.total:.4f}"]
        for k, v in self.components.items():
            lines.append(f"  {k:12s}: {v:.4f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Component: Geography
# Topology asymmetry encodes the lore-mandated structural difference between
# Lattice (dense tropical cluster, short hops, high tidal shelf) and Reach
# (temperate spread, long hops, sparse open-ocean topology).
# ---------------------------------------------------------------------------

def geo_component(
    states:       list,
    substrate:    list,
    adj:          list,
    reach_arch:   int,
    lattice_arch: int,
) -> tuple:
    """
    Topology asymmetry: hop count, latitude, tidal shelf, edge density,
    civilizational gap.

    Lore basis
    ----------
    Lattice: southern hemisphere dense cluster, inter-island crossings trivial,
      shallow sheltered waters, short hops.
    Reach: temperate mid-latitudes, islands spaced widely, open-ocean conditions,
      long hops.
    docs/03, docs/04, docs/01 (planet geometry).
    """
    N = len(states)
    details = {}

    # Classify by faction (exclude cores — they are the definition anchors)
    lat_idxs  = [i for i, s in enumerate(states)
                 if s["faction"] == "lattice" and s["status"] != "core"]
    reach_idxs = [i for i, s in enumerate(states)
                  if s["faction"] == "reach" and s["status"] != "core"]

    # 1. Hop asymmetry: Lattice hops < Reach hops
    lat_hops   = [states[i]["hopCount"] for i in lat_idxs]
    reach_hops = [states[i]["hopCount"] for i in reach_idxs]
    if lat_hops and reach_hops:
        lat_mean_hops   = _mean(lat_hops)
        reach_mean_hops = _mean(reach_hops)
        # Lattice should average ≤ 3.5 hops; Reach should average ≥ 3.5 hops
        l_hop = _sq_relu(lat_mean_hops - 3.5) + _sq_relu(3.5 - reach_mean_hops)
        details.update({"lat_mean_hops": lat_mean_hops, "reach_mean_hops": reach_mean_hops})
    else:
        l_hop = 2.0
        details["hop_note"] = "insufficient faction archs"

    # 2. Latitude asymmetry: Lattice tropical, Reach mid-latitude
    if substrate:
        def _abs_lat(i):
            return substrate[i]["climate"]["abs_latitude"] if i < len(substrate) else 30.0

        lat_lats   = [_abs_lat(i) for i in lat_idxs]
        reach_lats = [_abs_lat(i) for i in reach_idxs]
        lat_core_lat = _abs_lat(lattice_arch)
        reach_core_lat = _abs_lat(reach_arch)

        # Lattice core should be tropical (abs_lat < 20°)
        l_lat_core = _sq_relu((lat_core_lat - 20.0) / 5.0)
        # Reach core should be mid-latitude (abs_lat > 25°)
        l_reach_core = _sq_relu((25.0 - reach_core_lat) / 5.0)
        # Entire Lattice sphere should skew tropical
        l_lat_sphere = _sq_relu(_mean(lat_lats) - 25.0) if lat_lats else 0.0
        # Entire Reach sphere should skew mid-lat
        l_reach_sphere = _sq_relu(25.0 - _mean(reach_lats)) if reach_lats else 0.0
        l_lat = (l_lat_core + l_reach_core + l_lat_sphere + l_reach_sphere) / 4.0
        details.update({
            "lat_core_lat": lat_core_lat, "reach_core_lat": reach_core_lat,
            "lat_sphere_mean_lat": _mean(lat_lats) if lat_lats else None,
            "reach_sphere_mean_lat": _mean(reach_lats) if reach_lats else None,
        })
    else:
        l_lat = 0.0

    # 3. Lattice shelf condition: tidal range should be high at Lattice core
    if substrate and lattice_arch < len(substrate):
        lat_tidal = substrate[lattice_arch]["climate"]["tidal_range"]
        # Lore: Lattice tidal-flat agriculture requires tidal_range > 4 m
        l_shelf = _sq_relu((4.0 - lat_tidal) / 2.0)
        details["lat_core_tidal_range"] = lat_tidal
    else:
        l_shelf = 0.0

    # 4. Civilizational gap: hegemons should be far apart (lat gap > 30°)
    if substrate and reach_arch < len(substrate) and lattice_arch < len(substrate):
        r_lat = substrate[reach_arch]["climate"]["latitude"]
        l_lat_val = substrate[lattice_arch]["climate"]["latitude"]
        lat_gap = abs(r_lat - l_lat_val)
        l_gap = _sq_relu((30.0 - lat_gap) / 10.0)
        details["hegemon_lat_gap"] = lat_gap
    else:
        l_gap = 0.0

    # 5. Edge density asymmetry: Lattice should have denser local topology
    if adj:
        edge_count = [len(adj[i]) for i in range(min(N, len(adj)))]
        lat_edges   = _mean([edge_count[i] for i in lat_idxs if i < len(edge_count)])
        reach_edges = _mean([edge_count[i] for i in reach_idxs if i < len(edge_count)])
        # Lattice topology should be denser (more edges per arch) than Reach
        l_edge = _sq_relu((reach_edges - lat_edges) / 1.5) if lat_edges and reach_edges else 0.0
        details.update({"lat_mean_edges": lat_edges, "reach_mean_edges": reach_edges})
    else:
        l_edge = 0.0

    loss = (l_hop * 1.5 + l_lat * 1.0 + l_shelf * 0.5 + l_gap * 0.5 + l_edge * 0.5) / 4.5
    return _clamp(loss, 0.0, 5.0), details


# ---------------------------------------------------------------------------
# Component: Agriculture
# Climate→yield coherence without hard-coding crop names.
# The fundamental lore signal: hydraulic (tidal) agriculture yields more than
# dryland agriculture; the Lattice hegemon has high tidal range.
# ---------------------------------------------------------------------------

def ag_component(
    states:       list,
    substrate:    list,
    reach_arch:   int,
    lattice_arch: int,
) -> tuple:
    """
    Hydraulic vs dryland yield asymmetry; climate coherence.

    Lore basis
    ----------
    - Lattice: tidal-flat hydraulic staple; high yield, collective labor.
    - Reach: temperate dryland grain; moderate yield, individual labor.
    - substrate.gd: paddi ~5.0 t/ha, emmer ~2.5 t/ha (hydraulic > dryland by ~2×).
    - docs/04: "calorie-dense grain cultivated in managed tidal flats... feeds millions".
    """
    if not substrate:
        return 0.0, {"note": "no substrate"}

    details = {}

    # 1. Hegemon yield asymmetry: Lattice yield > Reach yield
    r_yield = substrate[reach_arch]["crops"]["primary_yield"]   if reach_arch < len(substrate) else 1.0
    l_yield = substrate[lattice_arch]["crops"]["primary_yield"] if lattice_arch < len(substrate) else 1.0
    ratio   = l_yield / max(r_yield, 0.01)
    # Target: Lattice/Reach yield ratio in [1.3, 3.5] (log-space tolerance)
    log_ratio = math.log(max(ratio, 1e-6))
    log_lo    = math.log(1.3)
    log_hi    = math.log(3.5)
    l_yield_asym = _sq_relu(log_lo - log_ratio) + _sq_relu(log_ratio - log_hi)
    details.update({"r_yield": r_yield, "l_yield": l_yield, "yield_ratio": ratio})

    # 2. Hydraulic zone coherence: arches with high tidal range (> 4 m) should have
    #    above-median yield (they are hydraulic → high productivity).
    tidal_ranges = [substrate[i]["climate"]["tidal_range"] for i in range(len(substrate))]
    yields       = [substrate[i]["crops"]["primary_yield"]  for i in range(len(substrate))]
    median_yield = sorted(yields)[len(yields) // 2] if yields else 1.0

    hydraulic_yields = [yields[i] for i in range(len(substrate)) if tidal_ranges[i] > 4.0]
    dryland_yields   = [yields[i] for i in range(len(substrate)) if tidal_ranges[i] < 2.0]

    l_hydraulic_floor = 0.0
    if hydraulic_yields:
        # Each hydraulic arch should exceed median yield
        below = [_sq_relu((median_yield - y) / median_yield) for y in hydraulic_yields]
        l_hydraulic_floor = _mean(below)
        details["hydraulic_mean_yield"] = _mean(hydraulic_yields)

    l_hyd_vs_dry = 0.0
    if hydraulic_yields and dryland_yields:
        hyd_mean = _mean(hydraulic_yields)
        dry_mean = _mean(dryland_yields)
        # Hydraulic archs should yield at least 1.3× dryland archs
        l_hyd_vs_dry = _sq_relu(1.3 - hyd_mean / max(dry_mean, 0.01))
        details["hyd_dry_ratio"] = hyd_mean / max(dry_mean, 0.01)

    # 3. Lattice core must have high tidal range (tidal agriculture precondition)
    if lattice_arch < len(substrate):
        lat_tidal = substrate[lattice_arch]["climate"]["tidal_range"]
        l_lat_tidal = _sq_relu((4.0 - lat_tidal) / 2.0)
        details["lat_tidal_range"] = lat_tidal
    else:
        l_lat_tidal = 0.0

    loss = (l_yield_asym * 1.5 + l_hydraulic_floor + l_hyd_vs_dry + l_lat_tidal) / 4.5
    return _clamp(loss, 0.0, 5.0), details


# ---------------------------------------------------------------------------
# Component: Technology
# Preconditions + target verification. We DO target tech levels but verify
# they emerge rather than being purely floor-driven.
# ---------------------------------------------------------------------------

def tech_component(
    states:       list,
    df_year:      Optional[int],
    reach_arch:   int,
    lattice_arch: int,
    world:        Optional[dict] = None,
    params:       Optional[object] = None,
) -> tuple:
    """
    Industrial convergence, DF < industrial precedence, emergent nuclear test.

    Lore basis
    ----------
    - Both hegemons cross tech > 7 (industrial threshold) within 1.5 tech points
      of each other — neither industrialises without the other noticing.
    - DF break is a nuclear-era event, so it cannot precede industrialisation.
    - Nuclear tech levels (≥ 9.0) should emerge organically from preconditions,
      not solely from hard tech floors.
    - docs/05: nuclear transition is fast + enthusiastic; both civs want it.
    """
    details = {}

    reach_tech   = states[reach_arch]["tech"]
    lattice_tech = states[lattice_arch]["tech"]

    # 1. Industrial convergence: both should be near each other at nuclear era.
    #    Lore: both hegemons are nuclear-capable → both tech ≥ 9.0.
    l_reach_nuc   = _sq_relu((9.0 - reach_tech)   / 1.0)
    l_lattice_nuc = _sq_relu((9.0 - lattice_tech)  / 1.0)
    gap_nuc = reach_tech - lattice_tech
    # Gap should be in [0, 1.5]: Reach leads but gap is not vast
    l_gap = _sq_relu(-gap_nuc / 0.5) + _sq_relu((gap_nuc - 1.5) / 0.5)
    details.update({
        "reach_tech": reach_tech, "lattice_tech": lattice_tech, "gap": gap_nuc,
    })

    # 2. DF < industrial precedence: DF break must come AFTER industrialisation.
    #    Lore: DF break is a nuclear-era event (mutual awareness via reactor emissions).
    #    Industrial era ends at -200 BP → DF must be ≥ -200.
    if df_year is None:
        l_df_prec = 2.0  # no DF at all is bad
        details["df_precedence"] = "no DF"
    elif df_year < -200:
        l_df_prec = _sq_relu((-200 - df_year) / 50.0)
        details["df_precedence"] = f"DF at {df_year} (pre-industrial)"
    else:
        l_df_prec = 0.0
        details["df_precedence"] = f"DF at {df_year} (nuclear era, correct)"

    # 3. Emergent nuclear test: run without tech floors; verify hegemons still hit ≥ 9.0.
    #    Only executed when world + params are provided (adds ~5% overhead per eval).
    l_emergent = 0.0
    if world is not None and params is not None:
        try:
            from sim_proxy import simulate, SimParams
            import copy
            p_nf = copy.copy(params)
            p_nf.tech_floor_reach_ind   = 5.0  # far below nuclear threshold
            p_nf.tech_floor_lattice_ind = 4.5
            # Use a fixed seed for the second run so comparison is deterministic
            seed_nf = world.get("_opt_seed", 42)
            result_nf = simulate(world, p_nf, seed=seed_nf)
            r_nf = result_nf["states"][reach_arch]["tech"]
            l_nf = result_nf["states"][lattice_arch]["tech"]
            l_emergent = _sq_relu((9.0 - r_nf) / 1.5) + _sq_relu((9.0 - l_nf) / 1.5)
            details.update({"emergent_reach_tech": r_nf, "emergent_lattice_tech": l_nf})
        except Exception as e:
            details["emergent_test_error"] = str(e)

    loss = (l_reach_nuc + l_lattice_nuc + l_gap * 0.5 + l_df_prec + l_emergent) / 4.5
    return _clamp(loss, 0.0, 5.0), details


# ---------------------------------------------------------------------------
# Component: Ore
# Mineral-driven civilizational development.
# ---------------------------------------------------------------------------

def ore_component(
    states:       list,
    substrate:    list,
    minerals:     list,
    adj:          list,
    reach_arch:   int,
    lattice_arch: int,
) -> tuple:
    """
    Pu access for both hegemons, Cu→tech lead in serial-era archs,
    Au→earlier contact timing.

    Lore basis
    ----------
    - docs/03: settler colony "richer mineral deposits including uranium".
    - docs/05: nuclear competes with expensive fossils → everyone wants Pu.
    - ORE_SYSTEM_ANALYSIS.md: Cu accelerant for serial era, Au contact priority.
    - Both hegemons must have Pu in their sphere for mutual deterrence.
    """
    if not minerals or not substrate:
        return 0.0, {"note": "no minerals/substrate"}

    N = len(states)
    details = {}

    def _sphere_has_pu(hegemon_idx, faction_name):
        """True if any arch in hegemon's sphere (or the core itself) has Pu."""
        if minerals[hegemon_idx].get("Pu"):
            return True
        return any(
            states[i]["faction"] == faction_name and minerals[i].get("Pu")
            for i in range(N)
        )

    # 1. Pu access for both hegemons
    reach_has_pu   = _sphere_has_pu(reach_arch,   "reach")
    lattice_has_pu = _sphere_has_pu(lattice_arch, "lattice")
    l_pu_reach   = 0.0 if reach_has_pu   else 2.0
    l_pu_lattice = 0.0 if lattice_has_pu else 1.5  # weaker penalty: outer-island Pu is lore
    details.update({"reach_pu": reach_has_pu, "lattice_pu": lattice_has_pu})

    # 2. Supply chain robustness: Pu-bearing archs in Reach sphere should be
    #    within 3 hops (otherwise the supply line is fragile).
    reach_pu_hops = [
        states[i]["hopCount"] for i in range(N)
        if states[i]["faction"] == "reach" and minerals[i].get("Pu")
    ]
    l_pu_supply = _sq_relu(_mean(reach_pu_hops) - 3.0) if reach_pu_hops else 0.5
    details["reach_pu_mean_hops"] = _mean(reach_pu_hops) if reach_pu_hops else None

    # 3. Cu → tech lead in serial-era archs.
    #    Archs contacted in the serial era with Cu should have measurably higher tech.
    serial_archs    = [i for i, s in enumerate(states)
                       if s.get("eraOfContact") == "sail" and i < len(minerals)]
    cu_serial_tech  = [states[i]["tech"] for i in serial_archs if minerals[i].get("Cu")]
    nocu_serial_tech= [states[i]["tech"] for i in serial_archs if not minerals[i].get("Cu")]
    l_cu_lead = 0.0
    if cu_serial_tech and nocu_serial_tech:
        lead = _mean(cu_serial_tech) - _mean(nocu_serial_tech)
        # Cu archs should lead by at least 0.3 tech points
        l_cu_lead = _sq_relu((0.3 - lead) / 0.3)
        details.update({"cu_serial_lead": lead,
                         "cu_n": len(cu_serial_tech), "nocu_n": len(nocu_serial_tech)})

    # 4. Au → earlier contact timing.
    #    Au-bearing archs should be contacted earlier (lower absolute BP year = closer to present
    #    means LATER, so higher abs(arrival_yr) = earlier contact).
    au_contact = []
    noau_contact = []
    for i, s in enumerate(states):
        if i >= len(minerals):
            continue
        yr = s.get("eraOfContact")
        # Use hopCount as proxy for contact timing (lower hops ≈ earlier contact)
        if yr in ("sail", "colonial", "industrial", "nuclear"):
            hops = s["hopCount"]
            if minerals[i].get("Au"):
                au_contact.append(hops)
            else:
                noau_contact.append(hops)
    l_au_priority = 0.0
    if au_contact and noau_contact:
        # Au archs should have lower (earlier) hop count than non-Au archs
        au_mean   = _mean(au_contact)
        noau_mean = _mean(noau_contact)
        # Soft target: Au archs contact earlier (lower hop mean)
        l_au_priority = _sq_relu((au_mean - noau_mean + 0.5) / 1.0)
        details.update({"au_mean_hops": au_mean, "noau_mean_hops": noau_mean})

    loss = (l_pu_reach * 1.5 + l_pu_lattice + l_pu_supply * 0.5 +
            l_cu_lead + l_au_priority) / 4.5
    return _clamp(loss, 0.0, 5.0), details


# ---------------------------------------------------------------------------
# Component: Historical Shape
# Macro-patterns of expansion, extraction, and convergence.
# ---------------------------------------------------------------------------

def hist_shape_component(
    states:       list,
    reach_arch:   int,
    lattice_arch: int,
) -> tuple:
    """
    Maritime asymmetry, colonial extraction signature, nuclear tech convergence.

    Lore basis
    ----------
    - docs/02: "Reach contacts more civilizations than any other power" →
      Reach sphere > Lattice sphere (area fraction).
    - docs/03: colony + extraction + epi = the Reach's Middle Passage analogue.
    - docs/05: nuclear competes with expensive fossil → fast convergence.
    """
    N = len(states)
    details = {}

    n_reach   = sum(1 for s in states if s["faction"] == "reach")
    n_lattice = sum(1 for s in states if s["faction"] == "lattice")

    # 1. Maritime asymmetry: Reach sphere / Lattice sphere > 1.5
    #    Reach is the dominant colonial projector; it contacts more civilisations.
    ratio_reach_lattice = n_reach / max(n_lattice, 1)
    l_maritime = _sq_relu((1.5 - ratio_reach_lattice) / 0.5)
    details.update({
        "n_reach": n_reach, "n_lattice": n_lattice,
        "reach_lattice_ratio": ratio_reach_lattice,
    })

    # 2. Colonial extraction signature.
    #    Colonies should have: (a) low sovereignty, (b) high trade integration,
    #    (c) population below the global median (extraction depressed growth).
    colony_states = [s for s in states if s["status"] == "colony"]
    l_extraction = 0.0
    if colony_states:
        all_pops     = sorted(s["population"] for s in states if s["population"] > 0)
        median_pop   = all_pops[len(all_pops) // 2] if all_pops else 1.0
        col_pops     = [s["population"] for s in colony_states]
        col_sovs     = [s["sovereignty"] for s in colony_states]
        col_ti       = [s["tradeIntegration"] for s in colony_states]

        # Most colonies should be below median population
        frac_below_median = sum(1 for p in col_pops if p < median_pop) / len(col_pops)
        l_col_pop = _sq_relu((0.5 - frac_below_median) / 0.25)

        # Colonies should have low sovereignty (< 0.55 mean)
        l_col_sov = _sq_relu((_mean(col_sovs) - 0.55) / 0.2)

        # Colonies should have high trade integration (> 0.5 mean)
        l_col_ti = _sq_relu((0.5 - _mean(col_ti)) / 0.2)

        l_extraction = (l_col_pop + l_col_sov + l_col_ti) / 3.0
        details.update({
            "n_colonies": len(colony_states),
            "col_mean_sov": _mean(col_sovs),
            "col_mean_ti":  _mean(col_ti),
            "col_frac_below_median_pop": frac_below_median,
        })

    # 3. Nuclear convergence: Lattice tech ≥ 9.0 (it converges to nuclear capability).
    #    Also: the nuclear gap should be smaller than 2.0 (both civs are nuclear powers).
    reach_tech   = states[reach_arch]["tech"]
    lattice_tech = states[lattice_arch]["tech"]
    l_convergence = _sq_relu((9.0 - lattice_tech) / 1.0)
    details.update({
        "nuclear_gap": reach_tech - lattice_tech,
        "lattice_tech_nuclear": lattice_tech,
    })

    loss = (l_maritime * 1.0 + l_extraction * 1.0 + l_convergence * 0.5) / 2.5
    return _clamp(loss, 0.0, 5.0), details


# ---------------------------------------------------------------------------
# Component: Political Economy
# DF timing, sovereignty monotonic ordering, post-nuclear sovereignty recovery.
# ---------------------------------------------------------------------------

def poleco_component(
    states:       list,
    df_year:      Optional[int],
    reach_arch:   int,
    lattice_arch: int,
) -> tuple:
    """
    DF timing window, sovereignty monotonic ordering (no band targets),
    sovereignty recovery in nuclear era.

    Lore basis
    ----------
    - docs/09: DF breaks in nuclear era (−200 to −40 BP) — not before.
    - Monotonic ordering: colony < garrison < tributary < client < pulse ≈ contacted.
    - docs/03: post-colonial decolonisation raises colony sovereignty.
    """
    details = {}

    # 1. DF timing window: −200 to −40 BP
    if df_year is None:
        l_df = 3.0
        details["df_year"] = None
    else:
        l_df = (
            _sq_relu((-200 - df_year) / 50.0) +   # penalty if DF before -200 BP
            _sq_relu((df_year - (-40))  / 50.0)    # penalty if DF after  -40 BP
        )
        details["df_year"] = df_year

    # 2. Sovereignty monotonic ordering (no fixed band targets — just ordering).
    #    Expected order: colony < garrison < tributary < client < (pulse, contacted, core).
    STATUS_ORDER = ["colony", "garrison", "tributary", "client", "pulse", "contacted", "core"]
    sov_by_status = {}
    for st in STATUS_ORDER:
        vals = [s["sovereignty"] for s in states if s["status"] == st]
        if vals:
            sov_by_status[st] = _mean(vals)

    # Penalise any adjacent pair that is out of order
    l_mono = 0.0
    ordered_statuses = [st for st in STATUS_ORDER if st in sov_by_status]
    for k in range(len(ordered_statuses) - 1):
        lo_st = ordered_statuses[k]
        hi_st = ordered_statuses[k + 1]
        sov_lo = sov_by_status[lo_st]
        sov_hi = sov_by_status[hi_st]
        # hi should be ≥ lo; penalise inversions
        l_mono += _sq_relu((sov_lo - sov_hi) / 0.1)
    l_mono /= max(len(ordered_statuses) - 1, 1)
    details["sov_by_status"] = {k: round(v, 3) for k, v in sov_by_status.items()}

    # 3. Sovereignty recovery: post-nuclear colony sovereignty > initial colonial value (0.15).
    #    The drift model should have raised it; target mean > 0.25.
    colony_sovs = [s["sovereignty"] for s in states if s["status"] == "colony"]
    if colony_sovs:
        mean_col_sov = _mean(colony_sovs)
        l_recovery = _sq_relu((0.25 - mean_col_sov) / 0.1)
        details["mean_colony_sov_nuclear"] = mean_col_sov
    else:
        l_recovery = 0.0

    loss = (l_df * 1.5 + l_mono * 1.0 + l_recovery * 0.5) / 3.0
    return _clamp(loss, 0.0, 5.0), details


# ---------------------------------------------------------------------------
# Component: Population
# ---------------------------------------------------------------------------

def pop_component(
    states:       list,
    reach_arch:   int,
    lattice_arch: int,
) -> tuple:
    """
    Lattice:Reach ratio > 1.0, broad Gini.

    Lore basis
    ----------
    - docs/04: paddi surplus → Lattice demographically larger than Reach.
    - Two peer civilisations + colonial extraction → wide but not absolute pop inequality.
    """
    reach_pop   = states[reach_arch]["population"]
    lattice_pop = states[lattice_arch]["population"]
    ratio       = lattice_pop / max(reach_pop, 1.0)

    # Lattice should be larger (ratio > 1.0); soft upper bound (< 4.0) prevents collapse
    l_ratio = _sq_relu(1.0 - ratio) + _sq_relu((ratio - 4.0) / 1.0)

    all_pops = [float(s["population"]) for s in states if s["population"] > 0]
    gini     = _gini(all_pops)
    # Gini in [0.30, 0.75]: significant inequality, not monopoly
    l_gini = _sq_relu((0.30 - gini) / 0.1) + _sq_relu((gini - 0.75) / 0.1)

    details = {
        "lattice_reach_ratio": ratio,
        "pop_gini":            gini,
        "reach_pop":           reach_pop,
        "lattice_pop":         lattice_pop,
    }
    loss = (l_ratio * 1.5 + l_gini) / 2.5
    return _clamp(loss, 0.0, 5.0), details


# ---------------------------------------------------------------------------
# Component: Epidemiology
# Spearman rank correlation of mortality with crop distance.
# No absolute mortality bounds — the correlation is the signal.
# ---------------------------------------------------------------------------

def epi_component(
    epi_log:   Optional[list],
    states:    Optional[list] = None,
) -> tuple:
    """
    Spearman(mortality_rate, crop_distance) should be strongly positive.

    Lore basis
    ----------
    - DESIGN_SPEC §10a: shock severity = base_severity × crop_distance.
    - The crop-distance mechanism should produce rank-order correlation between
      ecological distance and mortality — that's the whole point of the formula.
    - We test the correlation rather than absolute mortality bands, so the
      optimizer can vary base_severity freely while preserving the mechanism.
    """
    details = {}

    if not epi_log:
        # Fallback: if no epi_log, penalise mildly (can't verify mechanism)
        return 0.5, {"note": "no epi_log; correlation unverifiable"}

    distances  = []
    mortalities = []
    for entry in epi_log:
        m  = entry.get("mortality_rate", 0.0)
        cc = entry.get("contactor_crop", "")
        tc = entry.get("contacted_crop",  "")
        d  = crop_distance(cc, tc)
        distances.append(d)
        mortalities.append(m)

    if len(distances) < 3:
        return 0.5, {"note": "too few epi events"}

    # Spearman correlation: target ρ > 0.50
    rho = _spearman(distances, mortalities)
    # Penalty if ρ < 0.50; target = 0.70 (strong positive correlation)
    l_corr = _sq_relu((0.50 - rho) / 0.25)
    details.update({"spearman_rho": rho, "n_events": len(distances)})

    # Sanity check: there must be some variance in mortality
    if len(set(round(m, 3) for m in mortalities)) < 2:
        l_corr += 1.0
        details["note"] = "zero mortality variance — crop distance mechanism inactive"

    loss = l_corr
    return _clamp(loss, 0.0, 5.0), details


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_loss(
    sim_output:   dict,
    substrate:    Optional[list]   = None,
    weights:      Optional[LossWeights]  = None,
    targets:      Optional[object] = None,   # kept for API compatibility; unused
    reach_arch:   Optional[int]    = None,
    lattice_arch: Optional[int]    = None,
    world:        Optional[dict]   = None,   # for emergent nuclear test + geo topology
    params:       Optional[object] = None,   # for emergent nuclear test
) -> LossResult:
    """
    Compute composite emergent-outcome loss from simulation output.

    Parameters
    ----------
    sim_output : dict
        Output from sim_proxy.simulate() or history_engine.
        Required : "states", "df_year"
        Consumed  : "epi_log", "reach_arch", "lattice_arch", "substrate",
                    "minerals", "adj"
    substrate : list[dict] | None
        Per-arch substrate. Falls back to sim_output["substrate"].
    weights : LossWeights | None
    reach_arch, lattice_arch : int | None   (inferred from states if absent)
    world : dict | None
        Original world dict (from generate_test_world). Enables geo topology
        checks and the emergent nuclear test.
    params : SimParams | None
        Current parameter set. Enables emergent nuclear test.

    Returns
    -------
    LossResult with .total, .components, .details
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    states   = sim_output["states"]
    df_year  = sim_output.get("df_year")
    epi_log  = sim_output.get("epi_log")
    minerals = sim_output.get("minerals", [])
    adj      = sim_output.get("adj", [])

    if substrate is None:
        substrate = sim_output.get("substrate") or []

    # Normalise flat substrate format (from run_headless.gd) to nested format
    def _norm_sub(sub_list):
        if not sub_list:
            return sub_list
        if "crops" in (sub_list[0] or {}):
            return sub_list
        return [
            {
                "crops": {
                    "primary_crop":   s.get("primary_crop",  "emmer"),
                    "primary_yield":  s.get("primary_yield", 0.5),
                    "secondary_crop": s.get("secondary_crop", None),
                },
                "climate": {
                    "abs_latitude":       s.get("abs_latitude", 30.0),
                    "latitude":           s.get("latitude", 30.0),
                    "mean_temp":          s.get("mean_temp", 18.0),
                    "effective_rainfall": s.get("effective_rainfall", 1000.0),
                    "tidal_range":        s.get("tidal_range", 2.0),
                    "upwelling":          s.get("upwelling", 0.1),
                },
                "trade_goods": {"total_trade_value": s.get("total_trade_value", 0.0)},
                "minerals":    s.get("minerals", {}),
            }
            for s in sub_list
        ]

    substrate = _norm_sub(substrate)

    # Infer minerals list from substrate if not in sim_output
    if not minerals and substrate:
        minerals = [s.get("minerals", {}) for s in substrate]

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

    # Build adj from world if not in sim_output
    if not adj and world is not None:
        N_w = len(world["archs"])
        adj_w = [[] for _ in range(N_w)]
        for edge in world["plateau_edges"]:
            a, b = int(edge[0]), int(edge[1])
            adj_w[a].append(b)
            adj_w[b].append(a)
        adj = adj_w

    # Attach seed to world for emergent nuclear test reproducibility
    if world is not None and "_opt_seed" not in world:
        world["_opt_seed"] = sim_output.get("_seed", 42)

    # Evaluate all components
    geo_loss,    geo_det    = geo_component(states, substrate, adj, reach_arch, lattice_arch)
    ag_loss,     ag_det     = ag_component(states, substrate, reach_arch, lattice_arch)
    tech_loss,   tech_det   = tech_component(states, df_year, reach_arch, lattice_arch,
                                              world=world, params=params)
    ore_loss,    ore_det    = ore_component(states, substrate, minerals, adj, reach_arch, lattice_arch)
    hist_loss,   hist_det   = hist_shape_component(states, reach_arch, lattice_arch)
    poleco_loss, poleco_det = poleco_component(states, df_year, reach_arch, lattice_arch)
    pop_loss,    pop_det    = pop_component(states, reach_arch, lattice_arch)
    epi_loss,    epi_det    = epi_component(epi_log, states)

    components = {
        "geo":        geo_loss    * weights.geo,
        "ag":         ag_loss     * weights.ag,
        "tech":       tech_loss   * weights.tech,
        "ore":        ore_loss    * weights.ore,
        "hist_shape": hist_loss   * weights.hist_shape,
        "poleco":     poleco_loss * weights.poleco,
        "pop":        pop_loss    * weights.pop,
        "epi":        epi_loss    * weights.epi,
    }
    total = sum(components.values())

    details = {
        "geo":        geo_det,
        "ag":         ag_det,
        "tech":       tech_det,
        "ore":        ore_det,
        "hist_shape": hist_det,
        "poleco":     poleco_det,
        "pop":        pop_det,
        "epi":        epi_det,
    }
    return LossResult(total=total, components=components, details=details)
