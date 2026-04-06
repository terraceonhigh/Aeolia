"""
Composite lore-fidelity loss for Aeolia history engine parameter optimization.

Six weighted components encode lore constraints from docs/ and HISTORY_ENGINE_ANALYSIS.md:

  geo      – contact fraction, sphere balance, independent powers
  ag       – crop zone distribution, yield ratios, Reach/Lattice crop identity
  tech     – Reach/Lattice tech gap, industrial compounding, epoch progression
  poleco   – Dark Forest timing, era distribution, sovereignty/trade integration
  epi      – epidemiological shock variance, mortality by crop distance
  pop      – Lattice:Reach ratio, population distribution shape, demographic transitions

All components produce un-weighted losses in [0, ~5] so component weights are
directly interpretable as relative importance. Total loss is the weighted sum.

Typical usage:
    from loss import compute_loss, LossWeights
    result = compute_loss(sim_output, substrate)
    print(result.total, result.components)

To plug into an optimizer, call compute_loss inside the objective function and
return result.total.  See optimize.py for scipy.optimize and optuna examples.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Crop-distance helper (mirrors history_engine._crop_distance exactly)
# ---------------------------------------------------------------------------

_TROPICAL = frozenset(["paddi", "taro", "sago"])
_TEMPERATE = frozenset(["emmer", "papa"])


def crop_distance(contactor: str, contacted: str) -> float:
    """
    Ecological distance between two crop zones.

    Returns
    -------
    0.2  same crop type            (similar pathogen pools — mild shock)
    0.5  adjacent climate zones    (50% of base severity)
    0.8  distant climate zones     (80% of base severity)
    1.0  maximum distance          (paddi ↔ papa — catastrophic)

    Source: DESIGN_SPEC §10a; verified against history_engine._crop_distance.
    """
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
# Targets — lore-derived reference values
# ---------------------------------------------------------------------------

@dataclass
class LoreTargets:
    """
    Reference values derived from docs/ and HISTORY_ENGINE_ANALYSIS.md.
    Override individual fields to explore alternative lore interpretations.
    """

    # -- Geography --
    # docs/02_HISTORICAL_TIMELINE.md: "15% of surface unmapped", "8-12k cultures"
    contact_frac_target: float = 0.75   # ~75% of archs contacted by present
    contact_frac_tol:    float = 0.10   # acceptable ± deviation before penalty
    indep_powers_min:    int   = 3      # DESIGN_SPEC §0: 3-5 independent powers per seed
    indep_powers_max:    int   = 5
    reach_sphere_min:    float = 0.38   # Reach fraction of all claimed archs
    reach_sphere_max:    float = 0.55   # Lattice is denser cluster but Reach projects farther

    # -- Agriculture --
    # docs/03_THE_REACH.md: emmer (temperate westerlies)
    # docs/04_THE_LATTICE.md: paddi (tropical tidal-flat hydraulic)
    # substrate.gd: paddi yield 5.0 t/ha, emmer 2.5 t/ha → ratio ~2.0
    reach_primary_crop:   str   = "emmer"
    lattice_primary_crop: str   = "paddi"
    yield_ratio_target:   float = 2.0   # lattice_yield / reach_yield
    yield_ratio_log_tol:  float = 0.4   # tolerance in log-space (±0.4 nats ≈ factor 1.5)

    # -- Technology --
    # history_engine ERA 5: tech floors 10.0 / 9.5
    # DESIGN_SPEC §5 Solow-Romer: Reach A₀=1.2 δ=0.08 > Lattice A₀=0.8 δ=0.04
    reach_tech_target:    float = 10.0
    lattice_tech_target:  float = 9.5
    tech_gap_min:         float = 0.3   # Reach leads by this many tech points at nuclear era
    tech_gap_max:         float = 0.8
    indep_tech_min:       float = 6.5   # independent power tech floor (industrialised)
    indep_tech_max:       float = 8.5   # not nuclear-capable

    # -- Political Economy --
    # docs/09_CONTACT_SEQUENCE.md: DF breaks in nuclear era
    # history_engine: DF recomputed after Σ2ⁿ redistribution at era boundary −200 BP
    df_year_min:  int = -200   # no earlier than industrial→nuclear transition
    df_year_max:  int = -40    # no later than "50 BP – now" lore window
    # Σ2ⁿ redistribution targets from history_engine phase 2
    era_fracs: dict = field(default_factory=lambda: {
        "sail":       0.05,   # serial contact era (−5000 to −2000 BP)
        "colonial":   0.10,   # colonial era (−2000 to −500 BP)
        "industrial": 0.20,   # industrial era (−500 to −200 BP)
        "nuclear":    0.40,   # nuclear era (−200 BP to present)
        "uncontacted":0.25,   # El Dorados — beyond Σ2ⁿ budget
    })
    # Sovereignty targets: (mean, min, max) per status
    # Source: history_engine phase 3 initial assignments + drift
    sov_targets: dict = field(default_factory=lambda: {
        "colony":    (0.20, 0.10, 0.40),
        "garrison":  (0.30, 0.15, 0.50),
        "client":    (0.60, 0.45, 0.80),
        "tributary": (0.65, 0.50, 0.85),
        "pulse":     (0.85, 0.70, 1.00),
        "contacted": (0.90, 0.75, 1.00),
    })
    # Trade integration targets: (mean, min, max) per status
    trade_targets: dict = field(default_factory=lambda: {
        "colony":    (0.80, 0.60, 0.95),
        "garrison":  (0.50, 0.30, 0.70),
        "client":    (0.60, 0.45, 0.80),
        "tributary": (0.40, 0.20, 0.60),
    })

    # -- Epidemiology --
    # DESIGN_SPEC §10a: cropDistance=0.2→mild, 1.0→catastrophic
    # Historical calibration: max-distance ~20-45% mortality, same-crop ~4-9%
    shock_same_crop_max:    float = 0.09   # mean mortality must be below this for same-crop contacts
    shock_max_dist_min:     float = 0.20   # paddi↔papa contacts must exceed this
    shock_max_dist_max:     float = 0.45   # paddi↔papa contacts must be below this
    shock_cv_min:           float = 0.30   # min coefficient of variation across all contacts
                                           # (tests that crop-distance is producing variance)

    # -- Population --
    # docs/04_THE_LATTICE.md: paddi surplus → Lattice larger than Reach
    # DESIGN_SPEC §5: Lattice β=0.6 (resource) vs Reach β=0.5 → pop scales with land
    lattice_reach_ratio_min: float = 1.20
    lattice_reach_ratio_max: float = 2.20
    pop_gini_min:            float = 0.35  # significant inequality (cores >> periphery)
    pop_gini_max:            float = 0.70  # not total monopoly


DEFAULT_TARGETS = LoreTargets()


# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------

@dataclass
class LossWeights:
    """
    Per-component weights. Defaults reflect relative lore-fidelity priority
    from HISTORY_ENGINE_ANALYSIS.md:
      - epi is rated 'Highest Priority' (inverted formula)
      - poleco is load-bearing for narrative structure
    """
    geo:    float = 1.0
    ag:     float = 1.0
    tech:   float = 1.0
    poleco: float = 1.5   # era structure is architecturally important
    epi:    float = 1.5   # highest-priority bug per analysis doc
    pop:    float = 1.0


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
            lines.append(f"  {k:8s}: {v:.4f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _sq_relu(x: float) -> float:
    """Squared ReLU — zero inside the acceptable range, quadratic outside."""
    return max(0.0, x) ** 2


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _gini(values: list) -> float:
    """Gini coefficient over a list of non-negative values."""
    if not values or sum(values) == 0:
        return 0.0
    n = len(values)
    s = sorted(float(v) for v in values)
    total = sum(s)
    cumsum = sum((2 * (i + 1) - n - 1) * v for i, v in enumerate(s))
    return cumsum / (n * total)


def _mean(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return math.sqrt(_mean([(v - m) ** 2 for v in values]))


# ---------------------------------------------------------------------------
# Component: Geography
# ---------------------------------------------------------------------------

def geo_component(
    states: list,
    reach_arch: int,
    lattice_arch: int,
    targets: LoreTargets = DEFAULT_TARGETS,
) -> tuple:
    """
    Contact fraction, sphere balance, independent powers.

    Lore basis
    ----------
    - ~75% of planet contacted, 15% unmapped  (docs/02_HISTORICAL_TIMELINE.md)
    - 3–5 independent sophisticates per seed  (docs/DESIGN_SPEC §0)
    - Two peer civilizations → Reach and Lattice hold roughly comparable spheres
    """
    N = len(states)

    # Contact fraction
    n_uncontacted = sum(1 for s in states if s["status"] == "uncontacted")
    contact_frac = (N - n_uncontacted) / N
    l_contact = ((contact_frac - targets.contact_frac_target) / targets.contact_frac_tol) ** 2

    # Independent powers: contacted archs that independently reached industrial-era sophistication.
    # DESIGN_SPEC §7: sovereignty > 0.7 && techLevel > 6.0 → arch becomes INDEPENDENT POWER.
    # These are NOT uncontacted archs (faction == "unknown" means uncontacted in the output).
    # Use status (contacted / client / pulse) + tech + sovereignty as the proxy.
    _INDEP_STATUSES = {"contacted", "client", "pulse"}
    n_indep = sum(
        1 for s in states
        if (s["status"] in _INDEP_STATUSES
            and s["tech"] > 6.0
            and s["sovereignty"] > 0.7)
    )
    l_indep = (
        _sq_relu(targets.indep_powers_min - n_indep) +
        _sq_relu(n_indep - targets.indep_powers_max)
    )

    # Sphere balance
    n_reach   = sum(1 for s in states if s["faction"] == "reach")
    n_lattice = sum(1 for s in states if s["faction"] == "lattice")
    n_claimed = n_reach + n_lattice
    reach_frac = n_reach / n_claimed if n_claimed > 0 else 0.5
    l_balance = (
        _sq_relu(targets.reach_sphere_min - reach_frac) +
        _sq_relu(reach_frac - targets.reach_sphere_max)
    )

    loss = (l_contact + l_indep * 0.5 + l_balance) / 3.0
    details = {
        "contact_frac": contact_frac,
        "n_indep": n_indep,
        "reach_frac": reach_frac,
        "l_contact": l_contact,
        "l_indep": l_indep,
        "l_balance": l_balance,
    }
    return _clamp(loss, 0.0, 10.0), details


# ---------------------------------------------------------------------------
# Component: Agriculture
# ---------------------------------------------------------------------------

def ag_component(
    states: list,
    substrate: list,
    reach_arch: int,
    lattice_arch: int,
    targets: LoreTargets = DEFAULT_TARGETS,
) -> tuple:
    """
    Crop identity, yield ratios, zone distribution.

    Lore basis
    ----------
    - Reach = emmer-origin (temperate westerlies, competitive-individual labor)
    - Lattice = paddi-origin (tropical tidal-flat, collective-hydraulic labor)
    - paddi ~5.0 t/ha vs emmer ~2.5 t/ha → ratio ≈ 2.0 (substrate.gd yield formulas)
    - Meaningful crop diversity across 42 archs (substrate.gd defines 6 crop types)
    """
    details = {}
    if not substrate:
        return 0.0, {"note": "no substrate provided; ag component skipped"}

    # Core crop identity (binary)
    reach_crop   = substrate[reach_arch]["crops"]["primary_crop"]
    lattice_crop = substrate[lattice_arch]["crops"]["primary_crop"]
    l_reach_id   = 0.0 if reach_crop   == targets.reach_primary_crop   else 2.0
    l_lattice_id = 0.0 if lattice_crop == targets.lattice_primary_crop else 2.0
    details.update({"reach_crop": reach_crop, "lattice_crop": lattice_crop})

    # Yield ratio
    reach_yield   = substrate[reach_arch]["crops"]["primary_yield"]
    lattice_yield = substrate[lattice_arch]["crops"]["primary_yield"]
    ratio         = lattice_yield / max(reach_yield, 0.01)
    log_err       = math.log(max(ratio, 1e-6)) - math.log(targets.yield_ratio_target)
    l_yield       = (log_err / targets.yield_ratio_log_tol) ** 2
    details["yield_ratio"] = ratio

    # Crop diversity
    crop_counts: dict = {}
    for sub in substrate:
        c = sub["crops"]["primary_crop"]
        crop_counts[c] = crop_counts.get(c, 0) + 1
    n_distinct   = len(crop_counts)
    paddi_frac   = crop_counts.get("paddi",  0) / len(substrate)
    emmer_frac   = crop_counts.get("emmer",  0) / len(substrate)
    l_diversity  = _sq_relu(4 - n_distinct) * 0.25
    l_paddi_zone = _sq_relu(0.15 - paddi_frac) * 2.0  # need tropical belt coverage
    l_emmer_zone = _sq_relu(0.15 - emmer_frac) * 2.0  # need temperate belt coverage
    details.update({
        "n_distinct_crops": n_distinct,
        "paddi_frac": paddi_frac,
        "emmer_frac": emmer_frac,
    })

    loss = (l_reach_id + l_lattice_id + l_yield + l_diversity + l_paddi_zone + l_emmer_zone) / 6.0
    return _clamp(loss, 0.0, 10.0), details


# ---------------------------------------------------------------------------
# Component: Technology
# ---------------------------------------------------------------------------

def tech_component(
    states: list,
    reach_arch: int,
    lattice_arch: int,
    targets: LoreTargets = DEFAULT_TARGETS,
) -> tuple:
    """
    Tech levels, compounding advantage, epoch progression.

    Lore basis
    ----------
    - Reach A₀=1.2, δ=0.08 → knowledge compounds faster per contact (DESIGN_SPEC §5)
    - Lattice A₀=0.8, δ=0.04 → stable paddi surplus, lower knowledge scaling
    - Nuclear-era tech floors: Reach 10.0, Lattice 9.5  (history_engine ERA 5)
    - Tech gap 0.3–0.8 in Reach's favour
    - Independent powers 6.5–8.5: industrialised but not nuclear-capable
    """
    reach_tech   = states[reach_arch]["tech"]
    lattice_tech = states[lattice_arch]["tech"]
    tech_gap     = reach_tech - lattice_tech

    l_reach_tech   = ((reach_tech   - targets.reach_tech_target)   / 0.5) ** 2
    l_lattice_tech = ((lattice_tech - targets.lattice_tech_target)  / 0.5) ** 2
    l_gap = (
        _sq_relu(targets.tech_gap_min - tech_gap) +
        _sq_relu(tech_gap - targets.tech_gap_max)
    )

    # Independent-power tech envelope: contacted archs with high sovereignty.
    # "uncontacted" archs have default tech ~2-4, not the 6.5-8.5 industrial range.
    # The indep_tech targets encode the lore expectation that regional powers
    # independently industrialise without reaching nuclear capability.
    _INDEP_STATUSES = {"contacted", "client", "pulse"}
    indep_techs = [
        s["tech"] for s in states
        if (s["status"] in _INDEP_STATUSES and s["sovereignty"] > 0.7)
    ]
    l_indep = 0.0
    if indep_techs:
        for t in indep_techs:
            l_indep += (
                _sq_relu(targets.indep_tech_min - t) +
                _sq_relu(t - targets.indep_tech_max)
            )
        l_indep /= len(indep_techs)

    loss = (l_reach_tech + l_lattice_tech + l_gap + l_indep) / 4.0
    details = {
        "reach_tech":   reach_tech,
        "lattice_tech": lattice_tech,
        "tech_gap":     tech_gap,
        "indep_techs":  indep_techs,
    }
    return _clamp(loss, 0.0, 10.0), details


# ---------------------------------------------------------------------------
# Component: Political Economy
# ---------------------------------------------------------------------------

def poleco_component(
    states: list,
    df_year: Optional[int],
    reach_arch: int,
    lattice_arch: int,
    targets: LoreTargets = DEFAULT_TARGETS,
) -> tuple:
    """
    Dark Forest timing, era distribution, sovereignty/trade integration.

    Lore basis
    ----------
    - Dark Forest breaks in nuclear era, −200 to −40 BP (docs/09_CONTACT_SEQUENCE.md)
    - Σ2ⁿ redistribution: serial 5%, colonial 10%, industrial 20%, nuclear 40% (history_engine phase 2)
    - Sovereignty targets from phase 3 status assignments + era drift
    - Reach colonies: lower sovereignty (0.10–0.40), high trade (0.60–0.95)
    - Lattice garrisons: moderate sovereignty (0.15–0.50), moderate trade (0.30–0.70)
    """
    N = len(states)
    details = {}

    # Dark Forest timing
    if df_year is None:
        l_df = 4.0          # lore requires contact; None means simulation never produced a DF break
        details["df_year"] = None
    else:
        # Quadratic penalty outside target window, normalised to 1.0 at ±100 yr error
        l_df = (
            _sq_relu(targets.df_year_min - df_year) / (100.0 ** 2) +
            _sq_relu(df_year - targets.df_year_max)  / (100.0 ** 2)
        )
        details["df_year"] = df_year

    # Era distribution — MSE vs Σ2ⁿ targets
    era_counts: dict = {k: 0 for k in targets.era_fracs}
    for s in states:
        era = s.get("eraOfContact")
        if era in era_counts:
            era_counts[era] += 1
        elif s["status"] == "uncontacted":
            era_counts["uncontacted"] = era_counts.get("uncontacted", 0) + 1
    actual_fracs = {k: v / max(N, 1) for k, v in era_counts.items()}
    l_era = sum(
        (actual_fracs.get(k, 0.0) - targets.era_fracs[k]) ** 2
        for k in targets.era_fracs
    )
    details["era_fracs"] = actual_fracs

    # Sovereignty by status
    sov_err   = 0.0
    sov_count = 0
    for s in states:
        st = s["status"]
        if st not in targets.sov_targets:
            continue
        mean_t, min_t, max_t = targets.sov_targets[st]
        sov = s["sovereignty"]
        band = max(max_t - min_t, 0.1)
        sov_err += ((sov - mean_t) / band) ** 2
        sov_count += 1
    l_sov = sov_err / max(sov_count, 1)

    # Trade integration by status
    trade_err   = 0.0
    trade_count = 0
    for s in states:
        st = s["status"]
        if st not in targets.trade_targets:
            continue
        mean_t, min_t, max_t = targets.trade_targets[st]
        ti = s["tradeIntegration"]
        band = max(max_t - min_t, 0.1)
        trade_err += ((ti - mean_t) / band) ** 2
        trade_count += 1
    l_trade = trade_err / max(trade_count, 1)

    loss = (l_df + l_era * 5.0 + l_sov + l_trade) / 4.0
    details.update({"l_df": l_df, "l_era": l_era, "l_sov": l_sov, "l_trade": l_trade})
    return _clamp(loss, 0.0, 10.0), details


# ---------------------------------------------------------------------------
# Component: Epidemiology
# ---------------------------------------------------------------------------

def epi_component(
    states: list,
    substrate: list,
    epi_log: Optional[list],
    targets: LoreTargets = DEFAULT_TARGETS,
) -> tuple:
    """
    Crop-distance mortality variance, mean shock by ecological distance.

    Lore basis
    ----------
    - DESIGN_SPEC §10a: cropDistance determines shock severity
    - Max-distance contact (paddi↔papa): 20–45% mortality
    - Same-crop contact: 4–9% mortality
    - HISTORY_ENGINE_ANALYSIS §3: highest-priority misalignment in current code
    - If epi_log not provided, falls back to population-depression proxy (weaker signal).

    epi_log format
    --------------
    List of dicts: {arch, contactor_crop, contacted_crop, mortality_rate}
    Produced by sim_proxy.simulate(); not available in raw Godot output.
    """
    details = {}

    if epi_log:
        same_m     = []
        max_dist_m = []
        all_m      = []

        for entry in epi_log:
            m  = entry.get("mortality_rate", 0.0)
            cc = entry.get("contactor_crop", "")
            tc = entry.get("contacted_crop",  "")
            d  = crop_distance(cc, tc)
            all_m.append(m)
            if d <= 0.2:
                same_m.append(m)
            elif d >= 1.0:
                max_dist_m.append(m)

        # Same-crop: low mortality
        l_same = 0.0
        if same_m:
            mean_same = _mean(same_m)
            l_same = _sq_relu(mean_same - targets.shock_same_crop_max) * 4.0
            details["mean_same_crop_mortality"] = mean_same

        # Max-distance: substantial mortality
        l_max = 0.0
        if max_dist_m:
            mean_max = _mean(max_dist_m)
            l_max = (
                _sq_relu(targets.shock_max_dist_min - mean_max) +
                _sq_relu(mean_max - targets.shock_max_dist_max)
            ) * 4.0
            details["mean_max_dist_mortality"] = mean_max

        # CV: crop distance must produce variance in mortality
        l_cv = 0.0
        if len(all_m) >= 3:
            cv = _std(all_m) / (_mean(all_m) + 1e-6)
            l_cv = _sq_relu(targets.shock_cv_min - cv) * 2.0
            details["mortality_cv"] = cv

        loss = (l_same + l_max + l_cv) / 3.0

    else:
        # Fallback: contacted archs should have lower pop than uncontacted peers
        # (epidemic survivors vs untouched populations)
        early_pops = [
            s["population"] for s in states
            if s.get("eraOfContact") in ("sail", "colonial")
        ]
        unc_pops = [
            s["population"] for s in states
            if s["status"] == "uncontacted"
        ]
        if early_pops and unc_pops:
            ratio = _mean(early_pops) / max(_mean(unc_pops), 1.0)
            # Expect contacted archs to be somewhat depressed vs untouched
            l_ratio = _sq_relu(ratio - 1.3) * 1.5
            loss    = l_ratio
            details["contacted_vs_uncontacted_ratio"] = ratio
        else:
            loss = 0.0
            details["note"] = "no epi_log and insufficient state data; epi component skipped"

    return _clamp(loss, 0.0, 10.0), details


# ---------------------------------------------------------------------------
# Component: Population
# ---------------------------------------------------------------------------

def pop_component(
    states: list,
    reach_arch: int,
    lattice_arch: int,
    targets: LoreTargets = DEFAULT_TARGETS,
) -> tuple:
    """
    Lattice:Reach ratio, distribution shape, demographic transitions.

    Lore basis
    ----------
    - Lattice paddi surplus → higher base population than Reach (docs/04_THE_LATTICE.md)
    - Solow-Romer Lattice β=0.6 (resource) vs Reach β=0.5 → population scales with land
    - Distribution shape: cores >> colonies >> periphery (Pareto / Zipf-like)
    - Gini 0.35–0.70: significant inequality without total monopoly
    - Colony post-independence recovery: sovereignty drift brings colonies to 0.20–0.50
    """
    reach_pop   = states[reach_arch]["population"]
    lattice_pop = states[lattice_arch]["population"]
    ratio       = lattice_pop / max(reach_pop, 1.0)

    l_ratio = (
        _sq_relu(targets.lattice_reach_ratio_min - ratio) +
        _sq_relu(ratio - targets.lattice_reach_ratio_max)
    )

    all_pops = [float(s["population"]) for s in states if s["population"] > 0]
    gini     = _gini(all_pops)
    l_gini   = (
        _sq_relu(targets.pop_gini_min - gini) +
        _sq_relu(gini - targets.pop_gini_max)
    )

    # Colony sovereignty at nuclear era: partial decolonisation expected
    colony_sovs = [s["sovereignty"] for s in states if s["status"] == "colony"]
    l_col_sov = 0.0
    if colony_sovs:
        mean_sov  = _mean(colony_sovs)
        l_col_sov = (
            _sq_relu(0.20 - mean_sov) +
            _sq_relu(mean_sov - 0.50)
        ) * 2.0

    # Lattice should be well above median (paddi surplus drives demographic dominance)
    median_pop = sorted(all_pops)[len(all_pops) // 2] if all_pops else 1.0
    l_surplus  = _sq_relu(1.5 - lattice_pop / max(median_pop, 1.0))

    loss = (l_ratio + l_gini + l_col_sov + l_surplus) / 4.0
    details = {
        "lattice_reach_ratio": ratio,
        "pop_gini":            gini,
        "mean_colony_sov":     _mean(colony_sovs) if colony_sovs else None,
        "lattice_vs_median":   lattice_pop / max(median_pop, 1.0),
    }
    return _clamp(loss, 0.0, 10.0), details


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def compute_loss(
    sim_output: dict,
    substrate: Optional[list]   = None,
    weights:   Optional[LossWeights]  = None,
    targets:   Optional[LoreTargets]  = None,
    reach_arch:   Optional[int] = None,
    lattice_arch: Optional[int] = None,
) -> LossResult:
    """
    Compute composite lore-fidelity loss from simulation output.

    Parameters
    ----------
    sim_output : dict
        Output from history_engine (or sim_proxy.simulate).
        Required keys : "states", "df_year"
        Optional keys : "df_arch", "df_detector", "epi_log",
                        "reach_arch", "lattice_arch", "substrate"
    substrate : list[dict] | None
        Per-arch substrate dicts from compute_substrate / sim_proxy.
        If None, looks in sim_output["substrate"]; if still absent,
        ag and epi components are degraded.
    weights : LossWeights | None
        Component weights. Defaults to DEFAULT_WEIGHTS.
    targets : LoreTargets | None
        Lore reference values. Defaults to DEFAULT_TARGETS.
    reach_arch : int | None
        Index of Reach core arch. Inferred from states if None.
    lattice_arch : int | None
        Index of Lattice core arch. Inferred from states if None.

    Returns
    -------
    LossResult
        .total       : scalar loss — lower is more lore-faithful
        .components  : per-component weighted losses (dict)
        .details     : raw diagnostics per component (dict)
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    if targets is None:
        targets = DEFAULT_TARGETS

    states  = sim_output["states"]
    df_year = sim_output.get("df_year")
    epi_log = sim_output.get("epi_log")

    if substrate is None:
        substrate = sim_output.get("substrate")

    # Infer core arch indices
    if reach_arch is None:
        reach_arch = sim_output.get("reach_arch")
        if reach_arch is None:
            reach_arch = next(
                (i for i, s in enumerate(states)
                 if s["faction"] == "reach" and s["status"] == "core"),
                0,
            )
    if lattice_arch is None:
        lattice_arch = sim_output.get("lattice_arch")
        if lattice_arch is None:
            lattice_arch = next(
                (i for i, s in enumerate(states)
                 if s["faction"] == "lattice" and s["status"] == "core"),
                1,
            )

    # Normalize substrate to the nested sim_proxy format that ag_component expects:
    #   substrate[i]["crops"]["primary_crop"]
    # run_headless.gd / thin_sim emit a flat format:
    #   substrate[i]["primary_crop"]
    # Both are accepted here so loss.py works with all three optimization paths.
    def _norm_sub(sub_list: list) -> list:
        if not sub_list:
            return sub_list
        if "crops" in (sub_list[0] or {}):
            return sub_list  # already nested
        return [
            {
                "crops": {
                    "primary_crop":   s.get("primary_crop",  "emmer"),
                    "primary_yield":  s.get("primary_yield", 0.5),
                    "secondary_crop": s.get("secondary_crop", None),
                },
                "trade_goods": {
                    "total_trade_value": s.get("total_trade_value", 0.0),
                },
            }
            for s in sub_list
        ]

    substrate = _norm_sub(substrate or [])

    geo_loss,    geo_det    = geo_component(states, reach_arch, lattice_arch, targets)
    ag_loss,     ag_det     = ag_component(states, substrate or [], reach_arch, lattice_arch, targets)
    tech_loss,   tech_det   = tech_component(states, reach_arch, lattice_arch, targets)
    poleco_loss, poleco_det = poleco_component(states, df_year, reach_arch, lattice_arch, targets)
    epi_loss,    epi_det    = epi_component(states, substrate or [], epi_log, targets)
    pop_loss,    pop_det    = pop_component(states, reach_arch, lattice_arch, targets)

    components = {
        "geo":    geo_loss    * weights.geo,
        "ag":     ag_loss     * weights.ag,
        "tech":   tech_loss   * weights.tech,
        "poleco": poleco_loss * weights.poleco,
        "epi":    epi_loss    * weights.epi,
        "pop":    pop_loss    * weights.pop,
    }
    total = sum(components.values())

    details = {
        "geo":    geo_det,
        "ag":     ag_det,
        "tech":   tech_det,
        "poleco": poleco_det,
        "epi":    epi_det,
        "pop":    pop_det,
    }
    return LossResult(total=total, components=components, details=details)
