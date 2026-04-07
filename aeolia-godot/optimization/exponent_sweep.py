"""
exponent_sweep.py — Production function regime comparison for Aeolia history engine.

Tests three structural approaches to Y = A × K^α × L^β × E^γ in the tech-growth model:
  BASELINE    : original sim_proxy_v2.simulate() (K^0.3, no L term, E^1.0)
  FIXED       : grid-searched (K^α, L^β, E^γ) with K+L+E ≈ 1.0, same across all tech levels
  INTERPOLATED: exponents linearly interpolate between low-tech and high-tech triples
  THREE-REGIME: Q5 proposal — Malthusian (tech 0-3) / Medieval (4-5) / Industrial (6+)

The K/L/E exponents enter into Stage 5 (tech growth accelerator) of the sim.
K = crop_y (land endowment / primary yield), L = normalised population, E = energy ratio.

Usage:
    python exponent_sweep.py           # full sweep (may take several minutes)
    python exponent_sweep.py --quick   # coarse only, seed 216089 only
"""
from __future__ import annotations

import heapq
import itertools
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# ── Locate the optimization directory and import helpers ─────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import sim_proxy_v2 as _spv2
from sim_proxy_v2 import (
    SimParams, DEFAULT_PARAMS,
    Mulberry32, _compute_substrate, _beta_sample, _resource_value,
    _log2, _clamp, _gc_dist_arch, _crop_distance,
    _CROP_TO_CULTURE, _TS_PRIORS, _POSTURE_TABLE, _categorize_cap,
    TICK_YEARS, START_YEAR, N_TICKS,
    load_world,
)
from loss import compute_loss

# ── Seeds to evaluate ────────────────────────────────────────────────────────
PRIMARY_SEED = 216089
_WORLD_FILES = {
    216089: os.path.join(_HERE, "worlds", "candidate_0216089.json"),
    42:     os.path.join(_HERE, "worlds", "candidate_0000042.json"),
    97:     os.path.join(_HERE, "worlds", "candidate_0000097.json"),
    33:     os.path.join(_HERE, "worlds", "candidate_0000033.json"),
    100:    os.path.join(_HERE, "worlds", "candidate_0000100.json"),
}
# Only use seeds whose world files exist
SEEDS = [s for s, p in _WORLD_FILES.items() if os.path.exists(p)]

# ── Production config dataclasses ────────────────────────────────────────────

@dataclass
class FixedProd:
    """Single Cobb-Douglas triple applied at every tech level."""
    k_exp: float = 0.3
    l_exp: float = 0.0
    e_exp: float = 1.0
    label: str   = "FIXED"

    def __str__(self):
        return f"FIXED(K={self.k_exp:.3f} L={self.l_exp:.3f} E={self.e_exp:.3f})"


@dataclass
class InterpProd:
    """Exponents linearly interpolate between (k_lo,l_lo,e_lo) at tech=0
    and (k_hi,l_hi,e_hi) at tech=10."""
    k_lo: float = 0.3; l_lo: float = 0.0; e_lo: float = 0.7
    k_hi: float = 0.3; l_hi: float = 0.0; e_hi: float = 0.7
    label: str  = "INTERPOLATED"

    def exponents(self, tech: float):
        t = _clamp(tech / 10.0, 0.0, 1.0)
        k = self.k_lo + (self.k_hi - self.k_lo) * t
        l = self.l_lo + (self.l_hi - self.l_lo) * t
        e = self.e_lo + (self.e_hi - self.e_lo) * t
        return k, l, e

    def __str__(self):
        return (f"INTERP(lo K={self.k_lo:.3f} L={self.l_lo:.3f} E={self.e_lo:.3f} | "
                f"hi K={self.k_hi:.3f} L={self.l_hi:.3f} E={self.e_hi:.3f})")


@dataclass
class ThreeRegimeProd:
    """Q5 proposal: Malthusian clamp (tech 0-3), then discrete Cobb-Douglas per era."""
    label: str = "THREE-REGIME"

    def __str__(self):
        return ("THREE-REGIME(0-3: Malthusian | 4-5: K^0.25 L^0.50 E^0.25 | "
                "6+: K^0.35 L^0.50 E^0.15)")


# ── Core: parameterised simulate function ────────────────────────────────────

_REF_POP   = 100.0   # normalisation denominator for L term
_MALTHUS_SCALE = 0.00012   # calibrated so min(cap,tp*0.5)*crop_y ≈ 0.003 at (cap=50,tp=100,y=0.5)

def simulate_with_prod(world: dict, params: SimParams, seed: int,
                       prod) -> dict:
    """
    Mirror of sim_proxy_v2.simulate() with Stage 5 production parameterised.

    prod : one of FixedProd | InterpProd | ThreeRegimeProd
           (or None to use baseline behaviour = FixedProd(k=0.3, l=0, e=1))
    """
    p = params
    archs         = world["archs"]
    plateau_edges = world["plateau_edges"]
    N             = len(archs)
    seed          = seed or world.get("seed", 42)

    substrate = world.get("substrate")
    if not substrate or "culture" not in substrate[0]:
        substrate = _compute_substrate(archs, plateau_edges, seed, p.naphtha_richness)
    for i in range(N):
        mins = substrate[i]["minerals"]
        if "C" not in mins:
            sr  = archs[i].get("shelf_r", 0.06)
            td  = substrate[i]["climate"].get("tidal_range", 2.0)
            mins["C"] = sr * td * p.naphtha_richness if sr >= 0.04 else 0.0
        substrate[i]["culture"] = _CROP_TO_CULTURE.get(
            substrate[i]["crops"].get("primary_crop", "foraging"), "parochial")

    rng = Mulberry32((seed if seed != 0 else 42) * 31 + 1066)

    adj = [[] for _ in range(N)]
    for edge in plateau_edges:
        a, b = int(edge[0]), int(edge[1])
        if b not in adj[a]: adj[a].append(b)
        if a not in adj[b]: adj[b].append(a)

    pop          = [0.0] * N
    tech         = [0.0] * N
    sovereignty  = [1.0] * N
    c_remaining  = [0.0] * N
    c_initial    = [0.0] * N
    knowledge    = [0.0] * N
    controller   = list(range(N))
    contact_set  = [set() for _ in range(N)]
    fleet_scale  = [0.0] * N
    awareness    = {}
    absorbed_tick      = [None] * N
    first_contact_tick = [None] * N

    for i, arch in enumerate(archs):
        pk_count = len(arch.get("peaks", [])) or arch.get("peak_count", 2)
        avg_h = arch.get("avg_h", 0.2)
        if "peaks" in arch and arch["peaks"]:
            avg_h = sum(pk["h"] for pk in arch["peaks"]) / (pk_count * 3000.0)
        sz = arch.get("shelf_r", 0.06) / 0.12
        pop[i]        = float(pk_count) * sz * (3.0 + rng.next_float() * 4.0)
        tech[i]       = 0.3 + rng.next_float() * 0.4
        c_remaining[i]= substrate[i]["minerals"].get("C", 0.0)
        c_initial[i]  = c_remaining[i]
        knowledge[i]  = substrate[i]["crops"]["primary_yield"] * 0.3

    carry_cap = [0.0] * N
    for i in range(N):
        y  = substrate[i]["crops"]["primary_yield"]
        pk = len(archs[i].get("peaks", [])) or archs[i].get("peak_count", 2)
        sz = archs[i].get("shelf_r", 0.06) / 0.12
        carry_cap[i] = y * pk * sz * 50.0 + 5.0

    def _culture(i): return substrate[i]["culture"]

    def _shares(culture):
        if culture == "civic":
            s = [p.civic_expansion_share, p.civic_tech_share, p.civic_consolidation_share]
        elif culture == "subject":
            s = [p.subject_expansion_share, p.subject_tech_share, p.subject_consolidation_share]
        else:
            con = _clamp(1.0 - p.parochial_expansion_share - p.parochial_tech_share, 0.05, 1.0)
            s   = [p.parochial_expansion_share, p.parochial_tech_share, con]
        t = sum(s)
        return tuple(x / t for x in s) if t > 0 else (0.33, 0.34, 0.33)

    def _A0(culture):
        if culture == "civic":   return p.A0_civic
        if culture == "subject": return p.A0_subject
        return p.A0_parochial

    def _controlled(core): return [j for j in range(N) if controller[j] == core]
    def _polity_pop(core): return sum(pop[j] for j in range(N) if controller[j] == core)
    def _polity_c(core):   return sum(c_remaining[j] for j in range(N) if controller[j] == core)
    def _has_pu(core):
        return any(substrate[j]["minerals"].get("Pu") for j in range(N) if controller[j] == core)

    epi_log       = []
    expansion_log = []
    df_year = df_arch = df_detector = None
    scramble_onset = pu_scramble_onset = None
    tech_snapshots = {}
    pop_snapshots  = {}

    is_three_regime   = isinstance(prod, ThreeRegimeProd)
    is_interp         = isinstance(prod, InterpProd)
    is_fixed          = isinstance(prod, FixedProd)

    for tick in range(N_TICKS):
        year = START_YEAR + tick * TICK_YEARS
        cores       = sorted(set(controller))
        core_pop    = {c: _polity_pop(c) for c in cores}
        core_c      = {c: _polity_c(c)   for c in cores}

        # ── STAGE 1: Resource accounting ─────────────────────────────────
        energy_ratio  = {}
        energy_surplus = {}

        for core in cores:
            tp = max(1.0, core_pop[core])
            ct = tech[core]

            if ct >= 7.0:
                e_demand = tp * ct * 0.002
                e_supply = core_c[core] * 0.2
                ratio    = _clamp(e_supply / max(0.001, e_demand), 0.3, 1.5)
                surplus  = max(0.0, e_supply - e_demand) * 0.2 + tp * 0.01
            else:
                y      = substrate[core]["crops"]["primary_yield"]
                ratio  = _clamp(0.6 + y * 0.2, 0.3, 1.5)
                # THREE-REGIME Malthusian floor: cap surplus by proximity to carry_cap
                if is_three_regime and ct < 4.0:
                    cap_ratio = _clamp(carry_cap[core] / max(1.0, tp), 0.0, 1.5)
                    surplus   = y * tp * 0.01 * min(1.0, cap_ratio)
                else:
                    surplus = y * tp * 0.01

            energy_ratio[core]   = ratio
            energy_surplus[core] = surplus

        # ── STAGE 2: Political allocation ────────────────────────────────
        exp_budget   = {}
        tech_bgt     = {}
        consol_budget = {}
        max_surplus = max(energy_surplus.values()) if energy_surplus else 1.0

        for core in cores:
            culture = _culture(core)
            exp_s, tec_s, con_s = _shares(culture)
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

        # ── STAGE 3: Rumor propagation ───────────────────────────────────
        for core in cores:
            if tech[core] < 1.5: continue
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
            if tech[core] >= 7.0:
                signal_r = p.df_detection_range * (tech[core] / 10.0)
                for other in cores:
                    if other == core: continue
                    dist = _gc_dist_arch(archs[core], archs[other])
                    if dist <= signal_r:
                        awareness[(other, core)] = min(1.0, awareness.get((other, core), 0.0) + 0.15)
                        awareness[(core, other)] = min(1.0, awareness.get((core, other), 0.0) + 0.10)

        # ── STAGE 4: Bayesian belief / Dark Forest ───────────────────────
        if df_year is None:
            for core in cores:
                if tech[core] < 9.0: continue
                for other in cores:
                    if other == core or tech[other] < 8.0: continue
                    aw   = awareness.get((core, other), 0.0)
                    dist = _gc_dist_arch(archs[core], archs[other])
                    if dist <= p.df_detection_range * 1.5 and aw > 0.2:
                        df_year = year; df_arch = core; df_detector = other
                        awareness[(core, other)] = awareness[(other, core)] = 1.0
                        break
                if df_year is not None: break

        # ── STAGE 5: Production + tech growth ────────────────────────────
        for core in cores:
            culture  = _culture(core)
            a0       = _A0(culture)
            nc       = len(contact_set[core])
            tp       = max(1.0, core_pop[core])
            er       = energy_ratio[core]
            crop_y   = substrate[core]["crops"]["primary_yield"]
            t        = tech[core]

            if t >= 9.0 and not _has_pu(core):
                er *= p.pu_dependent_factor

            eff_nc       = min(nc, int(t * 2) + 1)
            contact_mult = 1.0 + _log2(eff_nc + 1) * 0.3
            share_mult   = _shares(culture)[1] / 0.3

            # ── Production formula (parameterised) ───────────────────────
            if is_three_regime:
                if t < 4.0:
                    # Malthusian: min(Land, population×0.5) × efficiency
                    land_cap    = carry_cap[core]
                    eff_labor   = tp * 0.5
                    malthus_out = min(land_cap, eff_labor) * crop_y
                    delta       = malthus_out * _MALTHUS_SCALE
                else:
                    if t < 6.0:      # Medieval
                        k_exp, l_exp, e_exp = 0.25, 0.50, 0.25
                    else:            # Industrial
                        k_exp, l_exp, e_exp = 0.35, 0.50, 0.15

                    crop_exp   = crop_y ** k_exp
                    pop_factor = (_clamp(tp, 1.0, 10000.0) / _REF_POP) ** l_exp
                    energy_mod = er ** e_exp

                    if t < 5.0: accel_rate = 0.008
                    elif t < 7.0: accel_rate = 0.025
                    else: accel_rate = 0.120

                    accel = (a0 * crop_exp * pop_factor * share_mult
                             * accel_rate * contact_mult
                             * (energy_mod * p.energy_to_tfp))
                    delta = crop_exp * 0.003 + accel

                if t > 9.0:
                    delta *= _clamp((11.0 - t) / 2.0, 0.0, 1.0)

            else:
                # FIXED or INTERPOLATED: same structure as original but with
                # variable exponents
                if is_interp:
                    k_exp, l_exp, e_exp = prod.exponents(t)
                else:  # FIXED (or None / baseline passed as FixedProd)
                    k_exp = prod.k_exp
                    l_exp = prod.l_exp
                    e_exp = prod.e_exp

                crop_exp   = crop_y ** k_exp
                pop_factor = (_clamp(tp, 1.0, 10000.0) / _REF_POP) ** l_exp if l_exp > 0 else 1.0
                energy_mod = er ** e_exp if e_exp != 1.0 else er
                energy_mult = energy_mod * p.energy_to_tfp

                if t < 1.5:   accel_rate = 0.0
                elif t < 3.0: accel_rate = 0.002
                elif t < 5.0: accel_rate = 0.008
                elif t < 7.0: accel_rate = 0.025
                else:         accel_rate = 0.120

                base_floor = crop_exp * 0.003
                accel = (a0 * crop_exp * pop_factor * share_mult
                         * accel_rate * contact_mult * energy_mult)
                delta = base_floor + accel
                if t > 9.0:
                    delta *= _clamp((11.0 - t) / 2.0, 0.0, 1.0)

            tech[core]     += delta
            knowledge[core] += delta * a0 * 0.5

            # Population logistic growth (unchanged)
            for j in range(N):
                if controller[j] != core: continue
                cap = carry_cap[j]
                if tech[core] >= 7.0 and c_remaining[j] > 0:
                    cap *= (1.0 + energy_ratio[core] * 0.5)
                if tech[core] >= 9.0:
                    cap *= 1.5
                gr = 0.03 * energy_ratio[core] * (1.0 - pop[j] / max(1.0, cap))
                pop[j] *= (1.0 + _clamp(gr, -0.05, 0.10))
                pop[j] = max(1.0, pop[j])

            for j in range(N):
                if controller[j] == core and j != core:
                    tech[j] = max(tech[j], tech[core] * 0.7)

        # Knowledge diffusion (unchanged)
        core_set = set(cores)
        world_max_tech = max(tech[c] for c in cores)
        for core in cores:
            max_ct = max((tech[c] for c in contact_set[core] if c in core_set), default=0.0)
            if max_ct > tech[core] + 1.0:
                tech[core] += (max_ct - tech[core]) * 0.08
            if world_max_tech > tech[core] + 1.0:
                tech[core] += (world_max_tech - tech[core]) * 0.03

        # ── STAGE 6: Thompson Sampling expansion ─────────────────────────
        for core in cores:
            budget = exp_budget.get(core, 0.0)
            if budget < 0.1 or tech[core] < 2.0: continue
            culture = _culture(core)
            ts_a, ts_b = _TS_PRIORS.get(culture, (1.0, 1.0))
            ctrl_set = set(_controlled(core))
            frontier = set()
            for j in ctrl_set:
                for nb in adj[j]:
                    if nb not in ctrl_set:
                        frontier.add(nb)
            if not frontier: continue
            candidates = []
            for target in frontier:
                dist  = _gc_dist_arch(archs[core], archs[target])
                ts_sc = _beta_sample(rng, ts_a, ts_b)
                rv    = _resource_value(substrate[target]["minerals"], tech[core], p.cu_unlock_tech)
                if tech[core] >= 7.0 and substrate[target]["minerals"].get("C", 0.0) > 0:
                    if scramble_onset is None: scramble_onset = tick
                if tech[core] >= 9.0 and substrate[target]["minerals"].get("Pu"):
                    if pu_scramble_onset is None: pu_scramble_onset = tick
                score = ts_sc + p.resource_targeting_weight * rv - dist * 1.5
                candidates.append((score, target, dist))
            candidates.sort(key=lambda x: -x[0])
            absorbed_this_tick = 0
            for score, target, dist in candidates:
                if budget < 0.1 or absorbed_this_tick >= 1: break
                tech_adv = max(0.1, tech[core] - tech[target] + 1.0)
                cost = (pop[target] * 0.05 + dist**3 * 40.0) / (tech_adv ** 1.5)
                target_core = controller[target]
                if target_core != target:
                    cost *= 3.0
                    if tech[core] - tech[target_core] < 2.0: continue
                if cost > budget: continue
                if pop[target] > core_pop[core] * 0.5 and tech[core] - tech[target] < 2.0:
                    continue
                if first_contact_tick[target] is None:
                    first_contact_tick[target] = tick
                    cc   = substrate[core]["crops"]["primary_crop"]
                    ct_c = substrate[target]["crops"]["primary_crop"]
                    cdist = _crop_distance(cc, ct_c)
                    sev  = p.epi_base_severity + rng.next_float() * 0.15
                    pop[target] *= (1.0 - sev * cdist)
                    epi_log.append({"arch": target, "contactor": core,
                                    "mortality_rate": sev * cdist, "tick": tick, "year": year})
                for j in range(N):
                    if controller[j] == target: controller[j] = core
                controller[target] = core
                absorbed_tick[target] = tick
                sovereignty[target] = _clamp(0.15 + dist * 0.3, 0.10, 0.50)
                budget -= cost
                absorbed_this_tick += 1
                for c in contact_set[target]:
                    if c != core: contact_set[core].add(c)
                expansion_log.append({"core": core, "target": target,
                                      "tick": tick, "year": year,
                                      "tech_gap": tech[core] - tech[target],
                                      "resource_driven": rv > 0})

        # ── STAGE 7: Sovereignty drift ────────────────────────────────────
        for i in range(N):
            if controller[i] == i: continue
            core = controller[i]
            dist = _gc_dist_arch(archs[core], archs[i])
            extraction = p.sov_extraction_decay / max(0.1, dist)
            extraction *= _clamp(energy_ratio.get(core, 1.0), 0.0, 1.5)
            recovery   = p.sov_extraction_decay * sovereignty[i] * (pop[i] / max(1.0, pop[core])) * 0.5
            sovereignty[i] = _clamp(sovereignty[i] + (recovery - extraction) * 0.1, 0.05, 0.95)
            if tech[core] >= 9.0 and year >= -200:
                sovereignty[i] = min(0.80, sovereignty[i] + 0.015)

        # ── STAGE 8: C depletion ──────────────────────────────────────────
        for i in range(N):
            core = controller[i]
            if tech[core] >= 7.0 and c_remaining[i] > 0:
                c_remaining[i] = max(0.0,
                    c_remaining[i] - pop[i] * tech[core] * p.naphtha_depletion * 0.0005)

        if year == -5000:
            tech_snapshots["after_antiquity"] = list(tech)
            pop_snapshots["after_antiquity"]  = list(pop)
        elif year == -2000:
            tech_snapshots["after_serial"] = list(tech)
        elif year == -500:
            tech_snapshots["after_colonial"] = list(tech)
        elif year == -200:
            tech_snapshots["after_industrial"] = list(tech)

    # ── POST-SIM: Pu / fleet_scale ────────────────────────────────────────
    final_cores  = sorted(set(controller))
    total_world_pop = sum(pop)
    polity_pops  = {c: sum(pop[j] for j in range(N) if controller[j] == c) for c in final_cores}
    hegemons     = sorted([c for c, pp in polity_pops.items() if pp > total_world_pop * 0.09],
                          key=lambda c: -polity_pops[c])
    hegemon_cultures = {c: _culture(c) for c in hegemons}

    for core in final_cores:
        if tech[core] >= 9.0:
            fleet_scale[core] = 1.0 if _has_pu(core) else p.pu_dependent_factor
            if not _has_pu(core):
                sovereignty[core] = max(0.3, sovereignty[core] - 0.05)

    uncontacted  = sum(1 for i in range(N)
                       if controller[i] == i and i not in hegemons and absorbed_tick[i] is None)
    total_c_init = sum(c_initial)
    total_c_rem  = sum(c_remaining)
    max_pop      = max(pop) if pop else 1.0

    # Reach / Lattice backward-compat
    reach_arch = lattice_arch = None
    for h in hegemons:
        if _culture(h) == "civic"   and reach_arch is None:   reach_arch   = h
        elif _culture(h) == "subject" and lattice_arch is None: lattice_arch = h
    if reach_arch is None and hegemons:        reach_arch   = hegemons[0]
    if lattice_arch is None and len(hegemons) >= 2: lattice_arch = hegemons[1]
    elif lattice_arch is None: lattice_arch = reach_arch if reach_arch is not None else 0

    states = []
    for i in range(N):
        core = controller[i]
        if core == i and i in hegemons:
            faction, status = _culture(i), "core"
        elif core in hegemons:
            faction = _culture(core)
            if sovereignty[i] < 0.3:   status = "colony"
            elif sovereignty[i] < 0.6: status = "garrison" if _culture(core) == "subject" else "client"
            else:                      status = "contacted"
        elif controller[i] == i:
            faction, status = "independent", ("uncontacted" if absorbed_tick[i] is None else "independent")
        else:
            faction, status = _culture(core), "tributary"
        era = None
        if absorbed_tick[i] is not None:
            cy = START_YEAR + absorbed_tick[i] * TICK_YEARS
            era = "sail" if cy < -2000 else "colonial" if cy < -500 else "industrial" if cy < -200 else "nuclear"
        states.append({
            "faction": faction, "status": status, "name": f"arch_{i}",
            "population": round(pop[i]), "urbanization": pop[i] / max_pop if max_pop > 0 else 0.0,
            "tech": round(tech[i] * 10) / 10.0, "sovereignty": round(sovereignty[i], 3),
            "tradeIntegration": min(1.0, len(contact_set[i]) / max(1.0, N * 0.3)),
            "eraOfContact": era, "hopCount": 0, "culture": _culture(controller[i]),
            "fleet_scale": fleet_scale[i], "c_remaining": c_remaining[i], "controller": controller[i],
        })
    for i in range(N):
        core = controller[i]
        if core == reach_arch or i == reach_arch: states[i]["faction"] = "reach"
        elif core == lattice_arch or i == lattice_arch: states[i]["faction"] = "lattice"
        elif states[i]["faction"] == "independent": states[i]["faction"] = "unknown"

    polities, polity_members = [], {}
    for core in final_cores:
        members = [j for j in range(N) if controller[j] == core]
        polity_members[core] = members
        polities.append({"core": core, "culture_type": _culture(core),
                         "total_pop": polity_pops[core], "has_pu": _has_pu(core),
                         "tech": tech[core], "fleet_scale": fleet_scale[core]})
    polities.sort(key=lambda x: -x["total_pop"])

    return {
        "states": states, "log": expansion_log,
        "df_year": df_year, "df_arch": df_arch, "df_detector": df_detector,
        "df_polity_a": df_arch, "df_polity_b": df_detector,
        "reach_arch": reach_arch if reach_arch is not None else 0,
        "lattice_arch": lattice_arch if lattice_arch is not None else 1,
        "epi_log": epi_log, "substrate": substrate, "archs": archs,
        "plateau_edges": plateau_edges, "minerals": [substrate[i]["minerals"] for i in range(N)],
        "adj": adj, "contact_years": {i: START_YEAR + absorbed_tick[i] * TICK_YEARS
                                       for i in range(N) if absorbed_tick[i] is not None},
        "hop_count": [0]*N, "mineral_access": [{} for _ in range(N)],
        "tech_snapshots": tech_snapshots, "pop_snapshots": pop_snapshots,
        "colony_sov_pre_nuclear": {},
        "reach_pu_access":  _has_pu(reach_arch) if reach_arch is not None else False,
        "lattice_pu_access": _has_pu(lattice_arch) if lattice_arch is not None else False,
        "polities": polities, "polity_members": polity_members,
        "c_total_initial": total_c_init, "c_total_final": total_c_rem,
        "uncontacted": uncontacted, "hegemons": hegemons,
        "hegemon_cultures": hegemon_cultures,
        "c_depletion_frac": 1.0 - (total_c_rem / total_c_init if total_c_init > 0 else 0.0),
        "total_c_initial": total_c_init, "total_c_remaining": total_c_rem,
        "scramble_onset_tick": scramble_onset, "pu_scramble_onset_tick": pu_scramble_onset,
        "uncontacted_count": uncontacted, "fleet_scales": {c: fleet_scale[c] for c in hegemons},
        "polity_pops": polity_pops, "n_polities": len(final_cores),
    }


# ── Evaluation helpers ────────────────────────────────────────────────────────

def _run_loss(world, seed, prod, params=None):
    if params is None: params = DEFAULT_PARAMS
    try:
        out = simulate_with_prod(world, params, seed, prod)
        lr  = compute_loss(out, naphtha_richness=params.naphtha_richness)
        return lr.total, out
    except Exception as e:
        return 999.0, None


def _eval_multi_seed(worlds_by_seed, prod, params=None):
    """Return mean loss across available seeds."""
    losses = []
    for seed, world in worlds_by_seed.items():
        loss, _ = _run_loss(world, seed, prod, params)
        losses.append(loss)
    return sum(losses) / len(losses) if losses else 999.0


def _trajectory_stats(world, seed, prod, params=None):
    """Return (df_year, hegemon_tech_final, scramble_year) for a single run."""
    if params is None: params = DEFAULT_PARAMS
    try:
        out = simulate_with_prod(world, params, seed, prod)
    except Exception:
        return None, None, None
    df_year = out.get("df_year")
    hegs    = out.get("hegemons", [])
    heg_tech = max((out["states"][h]["tech"] for h in hegs), default=0.0) if hegs else 0.0
    sc_tick = out.get("scramble_onset_tick")
    sc_year = (START_YEAR + sc_tick * TICK_YEARS) if sc_tick is not None else None
    return df_year, heg_tech, sc_year


# ── Grid generators ──────────────────────────────────────────────────────────

def _fixed_candidates(step, e_lo=0.15, e_hi=0.85):
    """Enumerate (k, l, e) with k+l+e=1.0 (projected), both positive."""
    cands = []
    vals = [round(v, 4) for v in _frange(0.05, 0.80, step)]
    for k in vals:
        for l in vals:
            e = round(1.0 - k - l, 4)
            if e < e_lo or e > e_hi: continue
            if l < 0 or k < 0.05:   continue
            cands.append(FixedProd(k_exp=k, l_exp=l, e_exp=e))
    return cands


def _interp_candidates(step, e_lo=0.10, e_hi=0.90):
    """Enumerate (k_lo, l_lo) × (k_hi, l_hi), e = 1-k-l at each end."""
    cands = []
    vals = [round(v, 4) for v in _frange(0.05, 0.70, step)]
    for k_lo in vals:
        for l_lo in vals:
            e_lo_ = round(1.0 - k_lo - l_lo, 4)
            if e_lo_ < e_lo or e_lo_ > e_hi: continue
            for k_hi in vals:
                for l_hi in vals:
                    e_hi_ = round(1.0 - k_hi - l_hi, 4)
                    if e_hi_ < e_lo or e_hi_ > e_hi: continue
                    cands.append(InterpProd(
                        k_lo=k_lo, l_lo=l_lo, e_lo=e_lo_,
                        k_hi=k_hi, l_hi=l_hi, e_hi=e_hi_,
                    ))
    return cands


def _frange(lo, hi, step):
    v = lo
    while v <= hi + 1e-9:
        yield round(v, 6)
        v += step


def _refine_fixed(best: FixedProd, step=0.025, radius=0.075):
    """Generate refinement candidates around a FIXED best."""
    cands = []
    k_vals = [round(best.k_exp + d, 4) for d in _frange(-radius, radius, step)]
    l_vals = [round(best.l_exp + d, 4) for d in _frange(-radius, radius, step)]
    for k in k_vals:
        for l in l_vals:
            e = round(1.0 - k - l, 4)
            if k <= 0 or l < 0 or e < 0.05: continue
            cands.append(FixedProd(k_exp=k, l_exp=l, e_exp=e))
    return cands


def _refine_interp(best: InterpProd, step=0.025, radius=0.075):
    cands = []
    for dk_lo in _frange(-radius, radius, step):
        for dl_lo in _frange(-radius, radius, step):
            for dk_hi in _frange(-radius, radius, step):
                for dl_hi in _frange(-radius, radius, step):
                    k_lo = round(best.k_lo + dk_lo, 4)
                    l_lo = round(best.l_lo + dl_lo, 4)
                    k_hi = round(best.k_hi + dk_hi, 4)
                    l_hi = round(best.l_hi + dl_hi, 4)
                    e_lo = round(1.0 - k_lo - l_lo, 4)
                    e_hi = round(1.0 - k_hi - l_hi, 4)
                    if any(x < 0.0 for x in [k_lo, l_lo, e_lo, k_hi, l_hi, e_hi]): continue
                    cands.append(InterpProd(k_lo=k_lo, l_lo=l_lo, e_lo=e_lo,
                                            k_hi=k_hi, l_hi=l_hi, e_hi=e_hi))
    return cands


# ── Main sweep ────────────────────────────────────────────────────────────────

@dataclass
class RunResult:
    label:        str
    prod_str:     str
    mean_loss:    float
    seed_losses:  dict    # seed -> loss
    df_year:      Optional[int]
    hegemon_tech: Optional[float]
    scramble_year: Optional[int]


def run_sweep(quick=False):
    print("=" * 72)
    print("  Aeolia Exponent Sweep — Production Function Regime Comparison")
    print("=" * 72)

    # Load worlds
    worlds = {}
    for seed in SEEDS:
        path = _WORLD_FILES[seed]
        try:
            worlds[seed] = load_world(path)
            print(f"  Loaded seed {seed:7d}: {os.path.basename(path)}")
        except Exception as e:
            print(f"  WARN: could not load seed {seed}: {e}")
    if not worlds:
        print("ERROR: No world files found. Aborting.")
        sys.exit(1)

    primary_world = worlds[PRIMARY_SEED]

    # Quick mode: single seed for coarse pass, all seeds for final scoring
    coarse_worlds = {PRIMARY_SEED: primary_world} if quick else worlds
    print(f"\n  Seeds for coarse pass : {list(coarse_worlds.keys())}")
    print(f"  Seeds for final score : {list(worlds.keys())}")
    print()

    results: list[RunResult] = []

    # ── BASELINE (original sim_proxy_v2.simulate) ─────────────────────────
    print("── BASELINE ──────────────────────────────────────────────────────")
    baseline_prod = FixedProd(k_exp=0.3, l_exp=0.0, e_exp=1.0, label="BASELINE")
    t0 = time.perf_counter()
    seed_losses = {}
    for seed, world in worlds.items():
        loss, out = _run_loss(world, seed, baseline_prod)
        seed_losses[seed] = loss
    mean_bl = sum(seed_losses.values()) / len(seed_losses)
    df_y, ht, sc_y = _trajectory_stats(primary_world, PRIMARY_SEED, baseline_prod)
    print(f"  mean_loss={mean_bl:.4f}  df_year={df_y}  "
          f"heg_tech={ht:.1f}  scramble={sc_y}  [{time.perf_counter()-t0:.1f}s]")
    results.append(RunResult("BASELINE", str(baseline_prod), mean_bl, seed_losses, df_y, ht, sc_y))

    # ── FIXED: coarse grid search ─────────────────────────────────────────
    print("\n── FIXED: coarse grid (step=0.10) ────────────────────────────────")
    coarse_step = 0.15 if quick else 0.10
    fixed_coarse = _fixed_candidates(coarse_step)
    print(f"  {len(fixed_coarse)} candidates to evaluate")
    t0 = time.perf_counter()
    coarse_scores = []
    for i, prod in enumerate(fixed_coarse):
        loss = _eval_multi_seed(coarse_worlds, prod)
        coarse_scores.append((loss, prod))
        if (i + 1) % 10 == 0:
            print(f"  ... {i+1}/{len(fixed_coarse)}  best so far: {min(coarse_scores, key=lambda x: x[0])[0]:.4f}")
    coarse_scores.sort(key=lambda x: x[0])
    top_fixed = [p for _, p in coarse_scores[:5]]
    print(f"  Coarse done in {time.perf_counter()-t0:.1f}s. "
          f"Top-5 losses: {[f'{s:.4f}' for s, _ in coarse_scores[:5]]}")

    # Refine top-3
    print("── FIXED: refinement (step=0.025) ────────────────────────────────")
    refine_scores = []
    for best in top_fixed[:3]:
        for prod in _refine_fixed(best):
            loss = _eval_multi_seed(coarse_worlds, prod)
            refine_scores.append((loss, prod))
    refine_scores.sort(key=lambda x: x[0])
    print(f"  Refinement done. Best: {refine_scores[0][0]:.4f}  {refine_scores[0][1]}")

    # Final multi-seed score for best FIXED
    best_fixed_prod = refine_scores[0][1]
    best_fixed_prod.label = "FIXED"
    t0 = time.perf_counter()
    seed_losses = {}
    for seed, world in worlds.items():
        loss, _ = _run_loss(world, seed, best_fixed_prod)
        seed_losses[seed] = loss
    mean_fx = sum(seed_losses.values()) / len(seed_losses)
    df_y, ht, sc_y = _trajectory_stats(primary_world, PRIMARY_SEED, best_fixed_prod)
    print(f"  FIXED final: mean_loss={mean_fx:.4f}  df_year={df_y}  "
          f"heg_tech={ht:.1f}  scramble={sc_y}  [{time.perf_counter()-t0:.1f}s]")
    results.append(RunResult("FIXED", str(best_fixed_prod), mean_fx, seed_losses, df_y, ht, sc_y))

    # ── INTERPOLATED: coarse grid ─────────────────────────────────────────
    print("\n── INTERPOLATED: coarse grid (step=0.10) ─────────────────────────")
    interp_step = 0.20 if quick else 0.10
    interp_coarse = _interp_candidates(interp_step)
    print(f"  {len(interp_coarse)} candidates to evaluate")
    t0 = time.perf_counter()
    iscores = []
    for i, prod in enumerate(interp_coarse):
        loss = _eval_multi_seed(coarse_worlds, prod)
        iscores.append((loss, prod))
        if (i + 1) % 50 == 0:
            print(f"  ... {i+1}/{len(interp_coarse)}  best so far: {min(iscores, key=lambda x: x[0])[0]:.4f}")
    iscores.sort(key=lambda x: x[0])
    print(f"  Coarse done in {time.perf_counter()-t0:.1f}s. "
          f"Top-5 losses: {[f'{s:.4f}' for s, _ in iscores[:5]]}")

    # Refine top-3 INTERPOLATED
    if not quick:
        print("── INTERPOLATED: refinement (step=0.025) ─────────────────────────")
        iref_scores = []
        for best in [p for _, p in iscores[:3]]:
            for prod in _refine_interp(best, step=0.025, radius=0.05):
                loss = _eval_multi_seed(coarse_worlds, prod)
                iref_scores.append((loss, prod))
        iref_scores.sort(key=lambda x: x[0])
        print(f"  Refinement done. Best: {iref_scores[0][0]:.4f}")
        best_interp_prod = iref_scores[0][1]
    else:
        best_interp_prod = iscores[0][1]
    best_interp_prod.label = "INTERPOLATED"

    t0 = time.perf_counter()
    seed_losses = {}
    for seed, world in worlds.items():
        loss, _ = _run_loss(world, seed, best_interp_prod)
        seed_losses[seed] = loss
    mean_ip = sum(seed_losses.values()) / len(seed_losses)
    df_y, ht, sc_y = _trajectory_stats(primary_world, PRIMARY_SEED, best_interp_prod)
    print(f"  INTERPOLATED final: mean_loss={mean_ip:.4f}  df_year={df_y}  "
          f"heg_tech={ht:.1f}  scramble={sc_y}  [{time.perf_counter()-t0:.1f}s]")
    results.append(RunResult("INTERPOLATED", str(best_interp_prod), mean_ip, seed_losses, df_y, ht, sc_y))

    # ── THREE-REGIME ──────────────────────────────────────────────────────
    print("\n── THREE-REGIME (Q5 proposal) ────────────────────────────────────")
    three_prod = ThreeRegimeProd()
    t0 = time.perf_counter()
    seed_losses = {}
    for seed, world in worlds.items():
        loss, _ = _run_loss(world, seed, three_prod)
        seed_losses[seed] = loss
    mean_3r = sum(seed_losses.values()) / len(seed_losses)
    df_y, ht, sc_y = _trajectory_stats(primary_world, PRIMARY_SEED, three_prod)
    print(f"  THREE-REGIME: mean_loss={mean_3r:.4f}  df_year={df_y}  "
          f"heg_tech={ht:.1f}  scramble={sc_y}  [{time.perf_counter()-t0:.1f}s]")
    results.append(RunResult("THREE-REGIME", str(three_prod), mean_3r, seed_losses, df_y, ht, sc_y))

    return results


# ── Reporting ─────────────────────────────────────────────────────────────────

def _verdict(results: list[RunResult]) -> str:
    bl  = next((r for r in results if r.label == "BASELINE"),    None)
    fx  = next((r for r in results if r.label == "FIXED"),       None)
    ip  = next((r for r in results if r.label == "INTERPOLATED"), None)
    tr  = next((r for r in results if r.label == "THREE-REGIME"), None)

    lines = ["## Verdict\n"]

    if not (bl and fx and ip and tr):
        lines.append("_Incomplete results — cannot render verdict._")
        return "\n".join(lines)

    ref  = bl.mean_loss if bl.mean_loss > 0 else 1.0
    gap  = abs(ip.mean_loss - tr.mean_loss)
    rel  = gap / ref * 100

    lines.append(f"- **BASELINE** mean loss : {bl.mean_loss:.4f}")
    lines.append(f"- **FIXED best**         : {fx.mean_loss:.4f}  "
                 f"({'↑' if fx.mean_loss > bl.mean_loss else '↓'}"
                 f"{abs(fx.mean_loss - bl.mean_loss):.4f} vs baseline)")
    lines.append(f"- **INTERPOLATED best**  : {ip.mean_loss:.4f}  "
                 f"({'↑' if ip.mean_loss > bl.mean_loss else '↓'}"
                 f"{abs(ip.mean_loss - bl.mean_loss):.4f} vs baseline)")
    lines.append(f"- **THREE-REGIME**       : {tr.mean_loss:.4f}  "
                 f"({'↑' if tr.mean_loss > bl.mean_loss else '↓'}"
                 f"{abs(tr.mean_loss - bl.mean_loss):.4f} vs baseline)")
    lines.append("")
    lines.append(f"INTERPOLATED vs THREE-REGIME gap: **{gap:.4f}** ({rel:.1f}% of baseline loss)")
    lines.append("")

    if rel < 5.0:
        lines.append("**Finding: INTERPOLATED is within 5% of THREE-REGIME.**  "
                     "Discrete regime boundaries appear unnecessary — smoothly "
                     "varying exponents capture equivalent dynamics.")
    elif rel < 15.0:
        lines.append("**Finding: INTERPOLATED is marginally worse than THREE-REGIME "
                     f"({rel:.1f}% gap).**  "
                     "Whether the improvement justifies discrete boundaries is a "
                     "design-taste call; consider a **Hybrid** approach instead "
                     "(Malthusian floor + best single Cobb-Douglas triple).")
    else:
        lines.append("**Finding: THREE-REGIME outperforms INTERPOLATED by a substantial "
                     f"margin ({rel:.1f}%).**  The Malthusian clamp at low tech appears "
                     "to be a meaningful differentiator. Recommend adopting the "
                     "Hybrid: Malthusian floor (tech 0-3) + single best Cobb-Douglas "
                     "for tech 4+, avoiding full three-way branching.")

    # Check whether Malthusian clamp changes trajectory stats
    if tr.df_year and ip.df_year:
        df_shift = tr.df_year - ip.df_year
        if abs(df_shift) > 100:
            lines.append(f"\nNote: THREE-REGIME shifts DF year by **{df_shift:+d} years** "
                         "vs INTERPOLATED — the Malthusian clamp materially changes "
                         "early-game pacing and thus DF timing.")

    return "\n".join(lines)


def _format_results_md(results: list[RunResult], quick: bool) -> str:
    lines = [
        "# Exponent Sweep Results",
        "",
        f"_Generated by `exponent_sweep.py`  |  "
        f"seeds: {SEEDS}  |  mode: {'quick' if quick else 'full'}_",
        "",
        "## Summary Table",
        "",
        "| Approach | Configuration | Mean Loss | DF Year | Hegemon Tech | Naphtha Scramble |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for r in results:
        cfg = r.prod_str
        # truncate long configs
        if len(cfg) > 55:
            cfg = cfg[:52] + "..."
        df  = str(r.df_year)  if r.df_year      else "none"
        ht  = f"{r.hegemon_tech:.1f}" if r.hegemon_tech else "?"
        sc  = str(r.scramble_year) if r.scramble_year else "none"
        lines.append(f"| **{r.label}** | `{cfg}` | {r.mean_loss:.4f} | {df} | {ht} | {sc} |")

    lines += ["", "## Per-seed Losses", ""]
    header = "| Approach | " + " | ".join(f"Seed {s}" for s in SEEDS) + " |"
    sep    = "| --- | " + " | ".join("---:" for _ in SEEDS) + " |"
    lines.append(header)
    lines.append(sep)
    for r in results:
        cells = " | ".join(f"{r.seed_losses.get(s, float('nan')):.4f}" for s in SEEDS)
        lines.append(f"| **{r.label}** | {cells} |")

    lines += ["", _verdict(results), ""]
    return "\n".join(lines)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    quick = "--quick" in sys.argv
    results = run_sweep(quick=quick)

    print("\n" + "=" * 72)
    print("  RESULTS SUMMARY")
    print("=" * 72)
    print(f"\n{'Approach':<16} {'Config':<52} {'MeanLoss':>9}  {'DF Year':>7}  "
          f"{'HegTech':>7}  {'Scramble':>8}")
    print("-" * 104)
    for r in results:
        cfg = str(r.prod_str)
        if len(cfg) > 50: cfg = cfg[:47] + "..."
        df  = str(r.df_year)   if r.df_year      else "none"
        ht  = f"{r.hegemon_tech:.1f}" if r.hegemon_tech else "?"
        sc  = str(r.scramble_year) if r.scramble_year else "none"
        print(f"{r.label:<16} {cfg:<52} {r.mean_loss:>9.4f}  {df:>7}  {ht:>7}  {sc:>8}")

    md = _format_results_md(results, quick)
    out_path = os.path.join(_HERE, "exponent_sweep_results.md")
    with open(out_path, "w") as f:
        f.write(md)
    print(f"\nResults written to {out_path}")
