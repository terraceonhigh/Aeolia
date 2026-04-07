"""
Baseline Earth loss function for Aeolia history engine v2.

12-term loss function encoding the specific narrative requirements of the
Aeolia worldbuilding project.  This is the ONLY file that mentions "Reach"
and "Lattice" — the simulator is faction-agnostic; hegemons are mapped to
narrative labels here based on political culture type.

Design principles
-----------------
- sq_relu(x) = max(0, x)^2 for ALL penalty terms
- All 12 unweighted terms produce loss in [0, ~5] range
- Hegemon->Reach/Lattice mapping by culture type (Civic->Reach, Subject->Lattice)
- Structure supports swappable loss functions (see LOSS_FUNCTION_LIBRARY.md)
- compute_loss accepts the output dict from sim_proxy.simulate()
- baseline_earth_loss accepts 21-element param vector, returns scalar (optimizer API)

Typical usage
-------------
    from sim_proxy import SimParams, simulate, load_godot_world
    from loss import compute_loss, baseline_earth_loss

    # Option A: two-step (inspect intermediate sim output)
    world = load_godot_world("worlds/candidate_0216089.json")
    result = simulate(world, SimParams(), seed=216089)
    lr = compute_loss(result)
    print(lr.summary())

    # Option B: one-step (optimizer API — 21 params in, scalar out)
    world = load_godot_world("worlds/candidate_0216089.json")
    from sim_proxy import pack_params
    x = pack_params(SimParams())  # default 21-element vector
    loss_value = baseline_earth_loss(x, world, seed=216089)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sq_relu(x: float) -> float:
    """Squared ReLU -- zero inside the acceptable range, quadratic outside."""
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


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _gc_dist(archs: list, i: int, j: int) -> float:
    """Great-circle distance in radians between arch i and arch j."""
    ai, aj = archs[i], archs[j]
    dot = ai["cx"] * aj["cx"] + ai["cy"] * aj["cy"] + ai["cz"] * aj["cz"]
    return math.acos(max(-1.0, min(1.0, dot)))


def _mean_pairwise_gc(archs: list, indices: list) -> float:
    """Mean pairwise great-circle distance (radians) among a set of arch indices."""
    dists = []
    for a in range(len(indices)):
        for b in range(a + 1, len(indices)):
            dists.append(_gc_dist(archs, indices[a], indices[b]))
    return _mean(dists) if dists else 0.0


def _centroid_lat(archs: list, indices: list) -> float:
    """Mean absolute latitude (degrees) of a set of arch indices."""
    lats = []
    for i in indices:
        cy = max(-1.0, min(1.0, archs[i]["cy"]))
        lats.append(abs(math.asin(cy) * 180.0 / math.pi))
    return _mean(lats) if lats else 30.0


# ---------------------------------------------------------------------------
# Hegemon -> Reach/Lattice mapping
# ---------------------------------------------------------------------------

def _map_hegemons(sim_output: dict) -> dict:
    """Map the two largest polities to Reach/Lattice narrative labels.

    Mapping rules (this is the ONLY place faction names are assigned):
      1. If one hegemon is Civic and one is Subject -> Civic=Reach, Subject=Lattice
      2. If both are same culture -> more spread-out = Reach, denser = Lattice
      3. If only one hegemon exists -> it becomes Reach, Lattice is None
      4. If no hegemons -> both None

    Returns dict with keys: reach_core, lattice_core, reach_members,
    lattice_members, reach_culture, lattice_culture, mapping_note.
    """
    hegemons = sim_output.get("hegemons", [])
    polities = sim_output.get("polities", [])
    polity_members = sim_output.get("polity_members", {})
    archs = sim_output.get("archs", [])

    result = {
        "reach_core": None, "lattice_core": None,
        "reach_members": [], "lattice_members": [],
        "reach_culture": None, "lattice_culture": None,
        "mapping_note": "",
    }

    if len(hegemons) == 0:
        result["mapping_note"] = "no hegemons"
        return result

    def _get_polity(core):
        for p in polities:
            if p["core"] == core:
                return p
        return None

    if len(hegemons) == 1:
        h = hegemons[0]
        hp = _get_polity(h)
        result["reach_core"] = h
        result["reach_members"] = polity_members.get(h, [h])
        result["reach_culture"] = hp["culture_type"] if hp else "unknown"
        result["mapping_note"] = "single hegemon -> Reach"
        return result

    # Two hegemons
    h0, h1 = hegemons[0], hegemons[1]
    p0, p1 = _get_polity(h0), _get_polity(h1)
    c0 = p0["culture_type"] if p0 else "parochial"
    c1 = p1["culture_type"] if p1 else "parochial"
    m0 = polity_members.get(h0, [h0])
    m1 = polity_members.get(h1, [h1])

    # Rule 1: Civic=Reach, Subject=Lattice
    if c0 == "civic" and c1 != "civic":
        reach_idx, lattice_idx = 0, 1
        note = "civic->Reach, other->Lattice"
    elif c1 == "civic" and c0 != "civic":
        reach_idx, lattice_idx = 1, 0
        note = "civic->Reach, other->Lattice"
    elif c0 == "subject" and c1 != "subject":
        reach_idx, lattice_idx = 1, 0
        note = "subject->Lattice, other->Reach"
    elif c1 == "subject" and c0 != "subject":
        reach_idx, lattice_idx = 0, 1
        note = "subject->Lattice, other->Reach"
    else:
        # Rule 2: same culture -- more spread = Reach
        spread0 = _mean_pairwise_gc(archs, m0) if len(m0) >= 2 and archs else 0.0
        spread1 = _mean_pairwise_gc(archs, m1) if len(m1) >= 2 and archs else 0.0
        if spread0 >= spread1:
            reach_idx, lattice_idx = 0, 1
        else:
            reach_idx, lattice_idx = 1, 0
        note = f"same culture ({c0}) -- spread tiebreak"

    cores = [h0, h1]
    cultures = [c0, c1]
    members = [m0, m1]

    result["reach_core"] = cores[reach_idx]
    result["lattice_core"] = cores[lattice_idx]
    result["reach_members"] = members[reach_idx]
    result["lattice_members"] = members[lattice_idx]
    result["reach_culture"] = cultures[reach_idx]
    result["lattice_culture"] = cultures[lattice_idx]
    result["mapping_note"] = note
    return result


# ---------------------------------------------------------------------------
# LossWeights -- per-term weights for Baseline Earth
# ---------------------------------------------------------------------------

@dataclass
class LossWeights:
    # Structural preconditions (geography)
    latitude_separation:  float = 1.0
    civ_gap:              float = 1.0
    density_asymmetry:    float = 1.0
    two_hegemons:         float = 2.0
    # Energy outcomes
    naphtha_peak:         float = 1.5
    energy_transition:    float = 1.5
    pu_acquisition:       float = 1.5
    # Civilizational outcomes
    nuclear_fleets:       float = 2.0
    fleet_asymmetry:      float = 1.0
    sovereignty_gradient: float = 1.5
    dark_forest_timing:   float = 2.0
    el_dorados:           float = 1.0


DEFAULT_WEIGHTS = LossWeights()


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class LossResult:
    total:      float
    components: dict   # term_name -> weighted scalar
    raw:        dict   # term_name -> unweighted scalar
    details:    dict   # term_name -> diagnostic dict
    mapping:    dict   # hegemon mapping info

    def __repr__(self) -> str:
        comp_str = "  ".join(f"{k}={v:.4f}" for k, v in self.components.items())
        return f"LossResult(total={self.total:.4f}  [{comp_str}])"

    def summary(self) -> str:
        lines = [f"Total loss: {self.total:.4f}",
                 f"Hegemon mapping: {self.mapping.get('mapping_note', '?')}"]
        lines.append(f"  Reach  -> arch {self.mapping.get('reach_core')} "
                     f"({self.mapping.get('reach_culture', '?')})")
        lines.append(f"  Lattice -> arch {self.mapping.get('lattice_core')} "
                     f"({self.mapping.get('lattice_culture', '?')})")
        lines.append("")
        for k in self.components:
            w = self.components[k]
            r = self.raw.get(k, 0.0)
            lines.append(f"  {k:24s}: {w:7.4f}  (raw {r:.4f})")
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

    def __repr__(self) -> str:
        return (
            f"MultiSeedResult(total={self.total:.4f}  mean={self.mean:.4f}"
            f"  std={self.std:.4f}  n_seeds={len(self.per_seed)})"
        )


# ---------------------------------------------------------------------------
# Term 1: latitude_separation
# ---------------------------------------------------------------------------

def _term_latitude_separation(archs, mapping):
    """Civic hegemon centroid in mid-latitudes [35, 55],
    Subject hegemon centroid tropical [<28]."""
    reach_members = mapping["reach_members"]
    lattice_members = mapping["lattice_members"]

    if not reach_members or not lattice_members:
        return 3.0, {"note": "missing hegemon(s)"}

    reach_lat = _centroid_lat(archs, reach_members)
    lattice_lat = _centroid_lat(archs, lattice_members)

    # Reach (Civic): centroid should be in [35, 55]
    loss_r = sq_relu(35.0 - reach_lat) + sq_relu(reach_lat - 55.0)
    # Lattice (Subject): centroid should be < 28
    loss_l = sq_relu(lattice_lat - 28.0)
    # Scale to [0, ~5]
    loss = (loss_r + loss_l) * 0.01
    return min(loss, 5.0), {
        "reach_centroid_lat": round(reach_lat, 1),
        "lattice_centroid_lat": round(lattice_lat, 1),
    }


# ---------------------------------------------------------------------------
# Term 2: civ_gap
# ---------------------------------------------------------------------------

def _term_civ_gap(archs, mapping):
    """Min GC distance between the two dominant polities' members > 0.5 rad."""
    reach_members = mapping["reach_members"]
    lattice_members = mapping["lattice_members"]

    if not reach_members or not lattice_members:
        return 3.0, {"note": "missing hegemon(s)"}

    min_cross = min(
        _gc_dist(archs, i, j)
        for i in reach_members
        for j in lattice_members
    )
    loss = sq_relu(0.5 - min_cross) * 4.0
    return min(loss, 5.0), {"min_cross_dist_rad": round(min_cross, 3)}


# ---------------------------------------------------------------------------
# Term 3: density_asymmetry
# ---------------------------------------------------------------------------

def _term_density_asymmetry(archs, mapping):
    """Subject polity's cluster denser than Civic polity's spread.
    Lattice mean pairwise GC < Reach mean pairwise GC.
    Relaxed: Lattice mean < 1.1 rad."""
    reach_members = mapping["reach_members"]
    lattice_members = mapping["lattice_members"]

    if len(reach_members) < 2 or len(lattice_members) < 2:
        return 2.0, {"note": "need >=2 members per hegemon for pairwise"}

    reach_spread = _mean_pairwise_gc(archs, reach_members)
    lattice_spread = _mean_pairwise_gc(archs, lattice_members)

    # Lattice should be denser (smaller spread) AND below 1.1 rad
    loss_order = sq_relu(lattice_spread - reach_spread) * 4.0
    loss_abs = sq_relu(lattice_spread - 1.1) * 4.0
    loss = (loss_order + loss_abs) * 0.5
    return min(loss, 5.0), {
        "reach_spread_rad": round(reach_spread, 3),
        "lattice_spread_rad": round(lattice_spread, 3),
    }


# ---------------------------------------------------------------------------
# Term 4: two_hegemons
# ---------------------------------------------------------------------------

def _term_two_hegemons(sim_output, mapping):
    """Exactly two polities achieve hegemon status (>15% of total pop each),
    one Civic, one Subject."""
    polities = sim_output.get("polities", [])

    total_pop = sum(p["total_pop"] for p in polities) if polities else 1
    big_polities = [p for p in polities
                    if p["total_pop"] > total_pop * 0.15]

    loss = 0.0

    # Penalty for not having exactly 2
    n_big = len(big_polities)
    if n_big != 2:
        loss += sq_relu(abs(n_big - 2)) * 2.0

    # Penalty for not having one Civic and one Subject
    rc = mapping.get("reach_culture")
    lc = mapping.get("lattice_culture")
    if rc == "civic" and lc == "subject":
        pass  # ideal
    elif rc == "subject" and lc == "civic":
        pass  # also fine (mapping handles it)
    else:
        culture_penalty = 1.0
        if rc == "civic" or lc == "civic":
            culture_penalty = 0.3
        elif rc == "subject" or lc == "subject":
            culture_penalty = 0.5
        loss += culture_penalty

    return min(loss, 5.0), {
        "n_big_polities": n_big,
        "reach_culture": rc,
        "lattice_culture": lc,
    }


# ---------------------------------------------------------------------------
# Term 5: naphtha_peak
# ---------------------------------------------------------------------------

def _term_naphtha_peak(sim_output, mapping, naphtha_richness: float = 2.0):
    """At least one hegemon exhausts >50% of its C reserves before nuclear era.

    Uses per-arch c_remaining from states and reconstructs initial C from
    archs[j].shelf_r * substrate[j].climate.tidal_range * naphtha_richness.
    """
    states = sim_output.get("states", [])
    substrate = sim_output.get("substrate", [])
    archs = sim_output.get("archs", [])

    def _hegemon_c_depletion(members):
        if not members:
            return 0.0
        remaining = 0.0
        initial = 0.0
        for j in members:
            if j >= len(states) or j >= len(archs) or j >= len(substrate):
                continue
            shelf_r = archs[j].get("shelf_r", 0.0)
            if shelf_r < 0.04:
                continue
            tidal = substrate[j].get("climate", {}).get("tidal_range",
                    substrate[j].get("tidal_range", 2.0))
            c_init_j = shelf_r * tidal * naphtha_richness
            initial += c_init_j
            remaining += states[j].get("c_remaining", 0)
        if initial <= 0:
            return 0.0
        return 1.0 - (remaining / initial)

    reach_depl = _hegemon_c_depletion(mapping["reach_members"])
    lattice_depl = _hegemon_c_depletion(mapping["lattice_members"])
    max_depl = max(reach_depl, lattice_depl)

    loss = sq_relu(0.50 - max_depl) * 8.0
    return min(loss, 5.0), {
        "reach_c_depletion": round(reach_depl, 3),
        "lattice_c_depletion": round(lattice_depl, 3),
        "max_depletion": round(max_depl, 3),
    }


# ---------------------------------------------------------------------------
# Term 6: energy_transition
# ---------------------------------------------------------------------------

def _term_energy_transition(sim_output):
    """Total world C >70% depleted at story present."""
    c_init = sim_output.get("c_total_initial", 0)
    c_final = sim_output.get("c_total_final", 0)

    if c_init <= 0:
        return 2.0, {"note": "no initial C"}

    depletion = 1.0 - (c_final / c_init)
    loss = sq_relu(0.70 - depletion) * 8.0
    return min(loss, 5.0), {
        "c_initial": round(c_init, 2),
        "c_final": round(c_final, 2),
        "depletion_frac": round(depletion, 3),
    }


# ---------------------------------------------------------------------------
# Term 7: pu_acquisition
# ---------------------------------------------------------------------------

def _term_pu_acquisition(sim_output, mapping):
    """Both hegemons control >=1 Pu island by story present."""
    polities = sim_output.get("polities", [])

    def _has_pu(core):
        for p in polities:
            if p["core"] == core:
                return p.get("has_pu", False)
        return False

    reach_pu = _has_pu(mapping["reach_core"]) if mapping["reach_core"] is not None else False
    lattice_pu = _has_pu(mapping["lattice_core"]) if mapping["lattice_core"] is not None else False

    if reach_pu and lattice_pu:
        loss = 0.0
    elif reach_pu or lattice_pu:
        loss = 1.5
    else:
        loss = 4.0

    return min(loss, 5.0), {
        "reach_has_pu": reach_pu,
        "lattice_has_pu": lattice_pu,
    }


# ---------------------------------------------------------------------------
# Term 8: nuclear_fleets
# ---------------------------------------------------------------------------

def _term_nuclear_fleets(sim_output, mapping):
    """Both hegemons at tech >=9.0 with nuclear fleet capability."""
    polities = sim_output.get("polities", [])

    def _get_tech(core):
        for p in polities:
            if p["core"] == core:
                return p.get("tech", 0)
        return 0.0

    def _get_fleet(core):
        for p in polities:
            if p["core"] == core:
                return p.get("fleet_scale", 0)
        return 0.0

    r_tech = _get_tech(mapping["reach_core"]) if mapping["reach_core"] is not None else 0.0
    l_tech = _get_tech(mapping["lattice_core"]) if mapping["lattice_core"] is not None else 0.0
    r_fleet = _get_fleet(mapping["reach_core"]) if mapping["reach_core"] is not None else 0.0
    l_fleet = _get_fleet(mapping["lattice_core"]) if mapping["lattice_core"] is not None else 0.0

    loss_tech = sq_relu(9.0 - r_tech) * 0.5 + sq_relu(9.0 - l_tech) * 0.5
    loss_fleet = (0.0 if r_fleet > 0 else 1.5) + (0.0 if l_fleet > 0 else 1.5)

    loss = loss_tech + loss_fleet
    return min(loss, 5.0), {
        "reach_tech": round(r_tech, 2),
        "lattice_tech": round(l_tech, 2),
        "reach_fleet": round(r_fleet, 2),
        "lattice_fleet": round(l_fleet, 2),
    }


# ---------------------------------------------------------------------------
# Term 9: fleet_asymmetry
# ---------------------------------------------------------------------------

def _term_fleet_asymmetry(sim_output, mapping):
    """Pu-rich hegemon has larger fleet_scale than Pu-poor hegemon."""
    polities = sim_output.get("polities", [])

    def _get_info(core):
        for p in polities:
            if p["core"] == core:
                return p.get("has_pu", False), p.get("fleet_scale", 0)
        return False, 0.0

    r_pu, r_fleet = _get_info(mapping["reach_core"]) if mapping["reach_core"] is not None else (False, 0.0)
    l_pu, l_fleet = _get_info(mapping["lattice_core"]) if mapping["lattice_core"] is not None else (False, 0.0)

    if r_pu == l_pu:
        loss = 0.0
        note = "same Pu status"
    elif r_pu and not l_pu:
        loss = sq_relu(l_fleet - r_fleet + 0.1) * 5.0
        note = "Reach has Pu"
    else:
        loss = sq_relu(r_fleet - l_fleet + 0.1) * 5.0
        note = "Lattice has Pu"

    return min(loss, 5.0), {
        "reach_pu": r_pu, "reach_fleet": round(r_fleet, 2),
        "lattice_pu": l_pu, "lattice_fleet": round(l_fleet, 2),
        "note": note,
    }


# ---------------------------------------------------------------------------
# Term 10: sovereignty_gradient
# ---------------------------------------------------------------------------

def _term_sovereignty_gradient(sim_output, mapping):
    """Colonies have lower sovereignty than core; gradient visible."""
    states = sim_output.get("states", [])
    polity_members = sim_output.get("polity_members", {})

    if not mapping["reach_core"] and not mapping["lattice_core"]:
        return 3.0, {"note": "no hegemons"}

    loss = 0.0
    details = {}

    for label, core in [("reach", mapping["reach_core"]),
                        ("lattice", mapping["lattice_core"])]:
        if core is None:
            continue
        members = polity_members.get(core, [core])
        if len(members) <= 1:
            details[f"{label}_note"] = "single-arch polity"
            continue

        core_sov = states[core]["sovereignty"] if core < len(states) else 1.0
        periphery = [j for j in members if j != core and j < len(states)]
        if not periphery:
            continue

        peri_sovs = [states[j]["sovereignty"] for j in periphery]
        mean_peri = _mean(peri_sovs)

        loss += sq_relu(mean_peri - core_sov + 0.05) * 3.0

        details[f"{label}_core_sov"] = round(core_sov, 3)
        details[f"{label}_periphery_mean_sov"] = round(mean_peri, 3)

    return min(loss, 5.0), details


# ---------------------------------------------------------------------------
# Term 11: dark_forest_timing
# ---------------------------------------------------------------------------

def _term_dark_forest_timing(sim_output, mapping):
    """DF break between the two hegemons in nuclear era (-200 to -40 BP)."""
    df_year = sim_output.get("df_year")
    df_a = sim_output.get("df_polity_a")
    df_b = sim_output.get("df_polity_b")

    if df_year is None:
        return 4.0, {"note": "no Dark Forest break"}

    hegemon_set = set()
    if mapping["reach_core"] is not None:
        hegemon_set.add(mapping["reach_core"])
    if mapping["lattice_core"] is not None:
        hegemon_set.add(mapping["lattice_core"])

    between_hegemons = (df_a in hegemon_set and df_b in hegemon_set)

    # Timing penalty: should be in [-200, -40]
    loss_timing = (
        sq_relu(-200 - df_year) + sq_relu(df_year - (-40))
    ) / (80.0 ** 2) * 4.0

    loss_actors = 0.0 if between_hegemons else 1.5

    loss = loss_timing + loss_actors
    return min(loss, 5.0), {
        "df_year": df_year,
        "between_hegemons": between_hegemons,
        "df_polity_a": df_a,
        "df_polity_b": df_b,
    }


# ---------------------------------------------------------------------------
# Term 12: el_dorados
# ---------------------------------------------------------------------------

def _term_el_dorados(sim_output):
    """>=10 archs uncontacted at story present."""
    uncontacted = sim_output.get("uncontacted", 0)
    loss = sq_relu(10 - uncontacted) * 0.05
    return min(loss, 5.0), {"uncontacted": uncontacted}


# ---------------------------------------------------------------------------
# compute_loss -- Baseline Earth loss from sim output dict
# ---------------------------------------------------------------------------

def compute_loss(
    sim_output: dict,
    weights: Optional[LossWeights] = None,
    naphtha_richness: float = 2.0,
) -> LossResult:
    """
    Compute 12-term Baseline Earth loss from sim_proxy.simulate() output.

    This is the only loss function that maps hegemons to Reach/Lattice.
    The simulator is faction-agnostic; narrative labels are applied here.

    Parameters
    ----------
    sim_output : dict from sim_proxy.simulate()
    weights : per-term weights (default: all 1.0-2.0)
    naphtha_richness : the naphtha_richness param used in the sim run,
                       needed to reconstruct initial C per arch for naphtha_peak
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    archs = sim_output.get("archs", [])
    mapping = _map_hegemons(sim_output)

    # Evaluate all 12 terms
    terms = {}
    terms["latitude_separation"] = _term_latitude_separation(archs, mapping)
    terms["civ_gap"]             = _term_civ_gap(archs, mapping)
    terms["density_asymmetry"]   = _term_density_asymmetry(archs, mapping)
    terms["two_hegemons"]        = _term_two_hegemons(sim_output, mapping)
    terms["naphtha_peak"]        = _term_naphtha_peak(sim_output, mapping, naphtha_richness)
    terms["energy_transition"]   = _term_energy_transition(sim_output)
    terms["pu_acquisition"]      = _term_pu_acquisition(sim_output, mapping)
    terms["nuclear_fleets"]      = _term_nuclear_fleets(sim_output, mapping)
    terms["fleet_asymmetry"]     = _term_fleet_asymmetry(sim_output, mapping)
    terms["sovereignty_gradient"] = _term_sovereignty_gradient(sim_output, mapping)
    terms["dark_forest_timing"]  = _term_dark_forest_timing(sim_output, mapping)
    terms["el_dorados"]          = _term_el_dorados(sim_output)

    # Assemble
    raw = {k: v[0] for k, v in terms.items()}
    details = {k: v[1] for k, v in terms.items()}

    weight_map = {
        "latitude_separation":  weights.latitude_separation,
        "civ_gap":              weights.civ_gap,
        "density_asymmetry":    weights.density_asymmetry,
        "two_hegemons":         weights.two_hegemons,
        "naphtha_peak":         weights.naphtha_peak,
        "energy_transition":    weights.energy_transition,
        "pu_acquisition":       weights.pu_acquisition,
        "nuclear_fleets":       weights.nuclear_fleets,
        "fleet_asymmetry":      weights.fleet_asymmetry,
        "sovereignty_gradient": weights.sovereignty_gradient,
        "dark_forest_timing":   weights.dark_forest_timing,
        "el_dorados":           weights.el_dorados,
    }

    components = {k: raw[k] * weight_map[k] for k in raw}
    total = sum(components.values())

    return LossResult(
        total=total,
        components=components,
        raw=raw,
        details=details,
        mapping=mapping,
    )


# ---------------------------------------------------------------------------
# baseline_earth_loss -- optimizer API (21 params in, scalar out)
# ---------------------------------------------------------------------------

def baseline_earth_loss(
    x,
    world: dict,
    seed: int = 42,
    weights: Optional[LossWeights] = None,
) -> float:
    """
    End-to-end loss: 21-element parameter vector -> scalar.

    This is the function the optimizer calls.  It:
      1. Unpacks x into SimParams
      2. Runs simulate()
      3. Computes 12-term Baseline Earth loss
      4. Returns the scalar total

    Parameters
    ----------
    x : list/array of 21 floats (order matches PARAM_BOUNDS)
    world : pre-loaded world dict from load_godot_world()
    seed : RNG seed for the simulation
    weights : optional per-term weights
    """
    from sim_proxy import unpack_params, simulate

    params = unpack_params(x)
    sim_output = simulate(world, params, seed=seed)
    lr = compute_loss(sim_output, weights=weights,
                      naphtha_richness=params.naphtha_richness)
    return lr.total


def baseline_earth_loss_detailed(
    x,
    world: dict,
    seed: int = 42,
    weights: Optional[LossWeights] = None,
) -> LossResult:
    """Like baseline_earth_loss but returns full LossResult for diagnostics."""
    from sim_proxy import unpack_params, simulate

    params = unpack_params(x)
    sim_output = simulate(world, params, seed=seed)
    return compute_loss(sim_output, weights=weights,
                        naphtha_richness=params.naphtha_richness)


# ---------------------------------------------------------------------------
# Multi-seed evaluation
# ---------------------------------------------------------------------------

def evaluate_seeds(
    sim_outputs_by_seed: dict,
    weights: Optional[LossWeights] = None,
    naphtha_richness: float = 2.0,
    variance_weight: float = 0.30,
    fail_penalty: float = 5.0,
) -> MultiSeedResult:
    """Evaluate loss across multiple seeds and penalise variance."""
    if weights is None:
        weights = DEFAULT_WEIGHTS

    per_seed = {}
    for seed, sim_out in sim_outputs_by_seed.items():
        try:
            lr = compute_loss(sim_out, weights=weights,
                              naphtha_richness=naphtha_richness)
        except Exception as e:
            failed_components = {f.name: fail_penalty
                                 for f in LossWeights.__dataclass_fields__.values()}
            lr = LossResult(
                total=fail_penalty * len(failed_components),
                components=failed_components,
                raw=failed_components,
                details={"error": str(e)},
                mapping={"mapping_note": f"error: {e}"},
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


def evaluate_seeds_from_params(
    x,
    world: dict,
    seeds: list,
    weights: Optional[LossWeights] = None,
    variance_weight: float = 0.30,
) -> MultiSeedResult:
    """Multi-seed evaluation from a 21-element param vector."""
    from sim_proxy import unpack_params, simulate

    params = unpack_params(x)
    outputs = {}
    for seed in seeds:
        outputs[seed] = simulate(world, params, seed=seed)
    return evaluate_seeds(outputs, weights=weights,
                          naphtha_richness=params.naphtha_richness,
                          variance_weight=variance_weight)


# ---------------------------------------------------------------------------
# Test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import sys
    import time

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    from sim_proxy import SimParams, simulate, load_godot_world, pack_params

    world_path = os.path.join(script_dir, "worlds", "candidate_0216089.json")
    if not os.path.exists(world_path):
        print(f"ERROR: world file not found at {world_path}")
        sys.exit(1)

    world = load_godot_world(world_path)
    params = SimParams()

    # --- Two-step: simulate then compute_loss ---
    t0 = time.perf_counter()
    result = simulate(world, params, seed=216089)
    sim_ms = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    lr = compute_loss(result, naphtha_richness=params.naphtha_richness)
    loss_ms = (time.perf_counter() - t1) * 1000

    print("=" * 65)
    print("  BASELINE EARTH LOSS -- seed 216089")
    print(f"  Sim: {sim_ms:.1f} ms  |  Loss: {loss_ms:.1f} ms")
    print("=" * 65)
    print()
    print(lr.summary())
    print()
    print("-" * 65)
    print("DETAILS:")
    print("-" * 65)
    for term, det in lr.details.items():
        print(f"\n  {term}:")
        for k, v in det.items():
            print(f"    {k}: {v}")

    # --- One-step: optimizer API ---
    print()
    print("=" * 65)
    print("  OPTIMIZER API VERIFICATION")
    print("=" * 65)
    x = pack_params(params)
    t2 = time.perf_counter()
    scalar = baseline_earth_loss(x, world, seed=216089)
    api_ms = (time.perf_counter() - t2) * 1000
    print(f"  baseline_earth_loss(defaults, seed=216089) = {scalar:.4f}")
    print(f"  End-to-end: {api_ms:.1f} ms")
    print(f"  Match: {'YES' if abs(scalar - lr.total) < 1e-10 else 'NO'}")
