// ═══════════════════════════════════════════════════════════
// SimEngine.js — Tickable simulation class (fork of simulate.js)
// Exposes tick-by-tick interface for 1-player game mode.
// simulate.js stays untouched; this is a parallel copy.
// ═══════════════════════════════════════════════════════════

import { mulberry32 } from './rng.js';
import { computeSubstrate } from './substrate.js';

const TICK_YEARS = 50;
const START_YEAR = -20000;
const N_TICKS = 400;
const _ISLAND_MAX_HEIGHT = 3000.0;

function _clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
function _log2(x) { return x > 0 ? Math.log2(x) : 0; }

export const DEFAULT_PARAMS = {
  base_expansion: 0.05,
  outward_expansion_coeff: 0.35,
  individual_expansion_coeff: 0.10,
  base_tech: 0.05,
  outward_tech_coeff: 0.42,
  base_A0: 0.30,
  individual_A0_coeff: 0.80,
  outward_A0_coeff: 0.40,
  culture_drift_rate: 0.010,
  culture_noise_scale: 0.15,
  cu_unlock_tech: 3.0,
  au_contact_bonus: 500.0,
  naphtha_richness: 2.0,
  naphtha_depletion: 0.008,
  energy_to_tfp: 1.0,
  pu_dependent_factor: 0.65,
  resource_targeting_weight: 2.0,
  luxury_markup_rate: 0.40,
  bulk_markup_rate: 0.10,
  epi_base_severity: 0.30,
  sov_extraction_decay: 0.04,
  df_detection_range: 0.6,
  df_min_territory_frac: 0.08,
  carry_cap_scale: 1.0,
  maintenance_rate: 0.01,
  decay_rate: 0.10,
  desperation_weight: 0.50,
  // ── Disease mechanics (from DISEASE_MECHANIC.md) ─────────
  malaria_cap_penalty: 0.40,   // carrying capacity reduction at equator, pre-medical
  urban_disease_rate: 0.08,    // density-dependent mortality above 70% capacity
  // ── Environmental shocks ──────────────────────────────────
  crop_failure_rate: 0.025,    // probability of crop failure per arch per tick
  fishery_recovery_rate: 0.08, // natural fishery stock recovery per tick
  fishery_overfish_rate: 0.06, // stock depletion per unit of excess exploitation
  // ── Religion / culture as political variable ──────────────
  piety_drift_rate: 0.008,      // base rate of piety change per tick
  piety_absorption_bonus: 0.35, // extra sovereignty extraction from high piety (centripetal force)
};

// ── Crop culture seeds ──────────────────────────────────────

const _CROP_CULTURE_SEED = {
  emmer: [0.45, 0.55], nori: [0.35, 0.65], paddi: [-0.55, -0.20],
  taro: [-0.10, 0.05], sago: [-0.20, -0.10], papa: [0.15, 0.15],
  foraging: [0.00, 0.00],
};

const _TROPICAL = new Set(["paddi", "taro", "sago"]);
const _TEMPERATE = new Set(["emmer", "papa"]);

function _cultureLabelFromPos(pos) {
  const [ci, io] = pos;
  if (ci > 0.3 && io > 0.3) return "civic";
  if (ci < -0.3 && io < 0.0) return "subject";
  return "parochial";
}

function _cropDistance(contactor, contacted) {
  if (contactor === contacted) return 0.2;
  const ct = _TROPICAL.has(contactor), cd = _TROPICAL.has(contacted);
  if ((ct && cd) || (_TEMPERATE.has(contactor) && _TEMPERATE.has(contacted))) return 0.5;
  if ((contactor === "paddi" && contacted === "papa") || (contactor === "papa" && contacted === "paddi")) return 1.0;
  return 0.8;
}

function _gcDistArch(a, b) {
  const dot = a.cx * b.cx + a.cy * b.cy + a.cz * b.cz;
  return Math.acos(_clamp(dot, -1, 1));
}

function _resourceValue(minerals, tech, cuUnlock) {
  let val = 0;
  if (tech >= cuUnlock && minerals.Cu) val += 1.0;
  if (tech >= 4.0 && minerals.Au) val += 1.5;
  const c = minerals.C || 0;
  if (tech >= 7.0 && c > 0) val += c * 5.0;
  if (tech >= 9.0 && minerals.Pu) val += 10.0;
  return val;
}

const _POSTURE_TABLE = {
  "HIGH,HIGH": "fortify", "HIGH,MED": "project", "HIGH,LOW": "explore",
  "MED,HIGH": "hedge", "MED,MED": "hedge", "MED,LOW": "project",
  "LOW,HIGH": "align", "LOW,MED": "free_ride", "LOW,LOW": "explore",
};

function _categorizeCap(surplus, ref) {
  if (ref <= 0) return "LOW";
  const r = surplus / ref;
  if (r > 0.6) return "HIGH";
  if (r > 0.25) return "MED";
  return "LOW";
}

function _betaSample(rng, a, b) {
  const mean = a / (a + b);
  const variance = (a * b) / ((a + b) ** 2 * (a + b + 1));
  const u1 = Math.max(1e-10, rng());
  const u2 = rng();
  const z = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
  return _clamp(mean + z * Math.sqrt(variance), 0.01, 0.99);
}


// ═══════════════════════════════════════════════════════════
// SimEngine class
// ═══════════════════════════════════════════════════════════

export class SimEngine {
  /**
   * @param {Object} world - { archs, plateauEdges, seed }
   * @param {Object} params - DEFAULT_PARAMS or custom
   * @param {number|null} playerCore - index of the player-controlled polity (null = 0-player)
   */
  constructor(world, params, playerCore = null) {
    this.p = params || DEFAULT_PARAMS;
    this.archs = world.archs;
    this.plateauEdges = world.plateauEdges;
    this.N = this.archs.length;
    this.seed = world.seed || 42;
    this.playerCore = playerCore;
    this._scouting = false; // player scout/explore state

    // ── Substrate ──────────────────────────────────────────
    let substrate = world.substrate;
    if (!substrate || !substrate[0] || !substrate[0].culture_pos) {
      substrate = computeSubstrate(this.archs, this.plateauEdges, this.seed, this.p.naphtha_richness);
    }
    for (let i = 0; i < this.N; i++) {
      const mins = substrate[i].minerals;
      if (mins.C === undefined) {
        const sr = this.archs[i].shelfR ?? this.archs[i].shelf_r ?? 0.06;
        const td = substrate[i].climate.tidal_range ?? 2.0;
        mins.C = sr >= 0.04 ? sr * td * this.p.naphtha_richness : 0;
      }
      if (!substrate[i].culture_pos) {
        const crop = substrate[i].crops.primary_crop || "foraging";
        substrate[i].culture_pos = [...(_CROP_CULTURE_SEED[crop] || [0, 0])];
      }
      substrate[i].culture = _cultureLabelFromPos(substrate[i].culture_pos);

      const clim = substrate[i].climate;
      if (clim.coast_factor === undefined) {
        const ec = this.plateauEdges.reduce((n, e) => n + (e[0] === i || e[1] === i ? 1 : 0), 0);
        const up = clim.upwelling ?? 0.1;
        clim.coast_factor = Math.min(1.0, ec * 0.18 + Math.min(1, up) * 0.25);
        const al = clim.abs_latitude ?? 30;
        let fb;
        if (al > 38) fb = 2.0 + up;
        else if (al > 22) fb = 1.6 + up * 0.8;
        else if (al > 10) fb = 1.2 + up * 0.6;
        else fb = 1.0 + up * 0.4;
        clim.fish_y = clim.coast_factor * fb;
      }
      if (clim.avg_h === undefined) {
        const pks = this.archs[i].peaks || [];
        clim.avg_h = pks.length > 0
          ? pks.reduce((s, pk) => s + pk.h, 0) / (pks.length * _ISLAND_MAX_HEIGHT)
          : (this.archs[i].avg_h ?? 0.2);
      }
    }
    this.substrate = substrate;

    // ── RNG ────────────────────────────────────────────────
    this.rng = mulberry32(((this.seed !== 0 ? this.seed : 42) * 31 + 1066) | 0);

    // ── Culture-space positions ────────────────────────────
    this.cpos = [];
    for (let i = 0; i < this.N; i++) {
      const base = substrate[i].culture_pos || [0, 0];
      const ci = _clamp(base[0] + (this.rng() - 0.5) * 2.0 * this.p.culture_noise_scale, -1, 1);
      const io = _clamp(base[1] + (this.rng() - 0.5) * 2.0 * this.p.culture_noise_scale, -1, 1);
      this.cpos.push([ci, io]);
    }

    // ── Adjacency ──────────────────────────────────────────
    this.adj = Array.from({ length: this.N }, () => []);
    for (const edge of this.plateauEdges) {
      const [a, b] = edge;
      if (!this.adj[a].includes(b)) this.adj[a].push(b);
      if (!this.adj[b].includes(a)) this.adj[b].push(a);
    }

    // ── Per-arch state ─────────────────────────────────────
    this.pop = new Float64Array(this.N);
    this.tech = new Float64Array(this.N);
    this.sovereignty = new Float64Array(this.N).fill(1.0);
    this.cRemaining = new Float64Array(this.N);
    this.cInitial = new Float64Array(this.N);
    this.knowledge = new Float64Array(this.N);
    this.controller = Array.from({ length: this.N }, (_, i) => i);
    this.contactSet = Array.from({ length: this.N }, () => new Set());
    this.fleetScale = new Float64Array(this.N);
    this.awareness = new Map();
    this.absorbedTick = new Array(this.N).fill(null);
    this.firstContactTick = new Array(this.N).fill(null);

    // Initialize pop/tech/resources
    for (let i = 0; i < this.N; i++) {
      const arch = this.archs[i];
      const pkCount = (arch.peaks ? arch.peaks.length : 0) || arch.peak_count || 2;
      const sz = (arch.shelfR ?? arch.shelf_r ?? 0.06) / 0.12;
      this.pop[i] = pkCount * sz * (3.0 + this.rng() * 4.0);
      this.tech[i] = 0.3 + this.rng() * 0.4;
      this.cRemaining[i] = substrate[i].minerals.C || 0;
      this.cInitial[i] = this.cRemaining[i];
      this.knowledge[i] = substrate[i].crops.primary_yield * 0.3;
    }

    // Carrying capacity
    this.carryCap = new Float64Array(this.N);
    for (let i = 0; i < this.N; i++) {
      const y = substrate[i].crops.primary_yield;
      const pk = (this.archs[i].peaks ? this.archs[i].peaks.length : 0) || this.archs[i].peak_count || 2;
      const sz = (this.archs[i].shelfR ?? this.archs[i].shelf_r ?? 0.06) / 0.12;
      this.carryCap[i] = y * pk * sz * 50.0 + 5.0;
    }

    // ── Malaria belts: per-arch severity (0 at 20°+, peaks at equator) ───
    // Based on abs_latitude in degrees. Threshold: 20° from equator.
    this.malariaFactor = new Float64Array(this.N);
    for (let i = 0; i < this.N; i++) {
      const absLat = substrate[i].climate?.abs_latitude ?? 30;
      if (absLat < 20) {
        this.malariaFactor[i] = (20 - absLat) / 20;  // 1.0 at equator, 0 at 20°
      }
    }

    // ── Environmental shocks ───────────────────────────────
    // cropFailureModifier[i]: 1.0 = normal, < 1.0 = active failure (recovers each tick)
    this.cropFailureModifier = new Float64Array(this.N).fill(1.0);
    // fisheryStock[i]: 1.0 = fully stocked, depletes with exploitation, recovers naturally
    this.fisheryStock = new Float64Array(this.N).fill(1.0);

    // ── Religion: piety per core (0 = secular, 1 = theocratic fervor) ─────
    // Initialized from climate: tropical warm arches seed higher piety;
    // temperate and cold seed moderate. Collective cultures seed higher.
    this.piety = new Float64Array(this.N);
    for (let i = 0; i < this.N; i++) {
      const absLat = substrate[i].climate?.abs_latitude ?? 30;
      const crop = substrate[i].crops.primary_crop || 'foraging';
      const [ci0] = substrate[i].culture_pos || [0, 0];
      const warmSeed = Math.max(0, (25 - absLat) / 25);   // 1.0 at equator, 0 at 25°+
      const collectiveSeed = Math.max(0, -ci0 * 0.3);     // collective CI → slightly higher
      this.piety[i] = _clamp(0.25 + warmSeed * 0.25 + collectiveSeed + (this.rng() - 0.5) * 0.20, 0.05, 0.90);
    }

    // ── Logs ───────────────────────────────────────────────
    this.epiLog = [];
    this.waveEpiLog = [];  // spontaneous epidemic waves (separate from contact epidemics)
    this.cropFailureLog = [];
    this.fisheryLog = [];
    this.expansionLog = [];
    this.dfYear = null;
    this.dfArch = null;
    this.dfDetector = null;
    this.scrambleOnset = null;
    this.puScrambleOnset = null;
    this.techSnapshots = {};
    this.popSnapshots = {};
    this.techDecayLog = [];
    this.desperationLog = [];
    this.timeline = [];

    // ── Tick counter ───────────────────────────────────────
    this.tick = 0;
    this.year = START_YEAR;
    this.finished = false;
  }

  // ── Helpers (instance methods) ──────────────────────────

  _sharesFromPos(pos) {
    const [ci, io] = pos;
    const individual = (ci + 1) * 0.5;
    const outward = (io + 1) * 0.5;
    let expS = this.p.base_expansion + this.p.outward_expansion_coeff * outward + this.p.individual_expansion_coeff * individual;
    let tecS = this.p.base_tech + this.p.outward_tech_coeff * outward;
    let conS = Math.max(0.05, 1.0 - expS - tecS);
    const t = expS + tecS + conS;
    return [expS / t, tecS / t, conS / t];
  }

  _A0FromPos(pos) {
    const [ci, io] = pos;
    return this.p.base_A0 + this.p.individual_A0_coeff * ((ci + 1) * 0.5) + this.p.outward_A0_coeff * ((io + 1) * 0.5);
  }

  _tsPriorsFromPos(pos) {
    const [ci, io] = pos;
    const outward = (io + 1) * 0.5;
    const collective = (1 - ci) * 0.5;
    return [1.0 + outward, 1.0 + (1.0 - outward) * collective];
  }

  _controlled(core) {
    const r = [];
    for (let j = 0; j < this.N; j++) if (this.controller[j] === core) r.push(j);
    return r;
  }
  _polityPop(core) {
    let s = 0;
    for (let j = 0; j < this.N; j++) if (this.controller[j] === core) s += this.pop[j];
    return s;
  }
  _polityC(core) {
    let s = 0;
    for (let j = 0; j < this.N; j++) if (this.controller[j] === core) s += this.cRemaining[j];
    return s;
  }
  _hasPu(core) {
    for (let j = 0; j < this.N; j++) if (this.controller[j] === core && this.substrate[j].minerals.Pu) return true;
    return false;
  }

  // ── Skip forward (AI-only, for skipping early game) ──

  skipToTick(n) {
    while (this.tick < n && !this.finished) this.advanceTick(null);
  }

  // ── Visibility: fog of war status for each archipelago ──

  getVisibility(core, scouting = false) {
    // Returns array of visibility levels per archipelago:
    // 'owned'     — player controls this
    // 'frontier'  — adjacent to player territory, can see details
    // 'contacted' — belongs to a polity we've contacted
    // 'rumor'     — adjacent to a contacted polity (2-hop visibility)
    // 'unknown'   — terra incognita
    const vis = new Array(this.N).fill('unknown');
    const ctrlSet = new Set(this._controlled(core));

    // Mark owned
    for (const j of ctrlSet) vis[j] = 'owned';

    // Mark frontier (adjacent to owned)
    const frontierSet = new Set();
    for (const j of ctrlSet) {
      for (const nb of this.adj[j]) {
        if (!ctrlSet.has(nb)) {
          vis[nb] = 'frontier';
          frontierSet.add(nb);
        }
      }
    }

    // Scout: when active, frontier extends one extra hop (frontier-of-frontier becomes frontier)
    if (scouting) {
      const extraFrontier = new Set();
      for (const j of frontierSet) {
        for (const nb of this.adj[j]) {
          if (vis[nb] === 'unknown') {
            extraFrontier.add(nb);
          }
        }
      }
      for (const j of extraFrontier) {
        vis[j] = 'frontier';
        frontierSet.add(j);
      }
    }

    // Mark contacted polities' territories
    const contactedCores = this.contactSet[core];
    for (const cc of contactedCores) {
      for (let j = 0; j < this.N; j++) {
        if (this.controller[j] === cc && vis[j] === 'unknown') {
          vis[j] = 'contacted';
        }
      }
    }

    // Mark rumors (1-hop from contacted territory)
    for (let j = 0; j < this.N; j++) {
      if (vis[j] === 'contacted' || vis[j] === 'frontier') {
        for (const nb of this.adj[j]) {
          if (vis[nb] === 'unknown') vis[nb] = 'rumor';
        }
      }
    }

    return vis;
  }

  // ── Frontier: archipelagos adjacent to a polity's territory ──

  getFrontier(core) {
    const ctrlSet = new Set(this._controlled(core));
    const frontier = [];
    const seen = new Set();
    for (const j of ctrlSet) {
      for (const nb of this.adj[j]) {
        if (!ctrlSet.has(nb) && !seen.has(nb)) {
          seen.add(nb);
          const dist = _gcDistArch(this.archs[core], this.archs[nb]);
          const rv = _resourceValue(this.substrate[nb].minerals, this.tech[core], this.p.cu_unlock_tech);
          frontier.push({
            index: nb,
            distance: dist,
            resourceValue: rv,
            pop: Math.round(this.pop[nb]),
            tech: Math.round(this.tech[nb] * 10) / 10,
            controller: this.controller[nb],
            crop: this.substrate[nb].crops.primary_crop,
            minerals: { ...this.substrate[nb].minerals },
          });
        }
      }
    }
    frontier.sort((a, b) => a.distance - b.distance);
    return frontier;
  }

  // ── Core method: advance one tick ──────────────────────

  /**
   * @param {Object|null} playerDecision - {
   *   expansion, techShare, consolidation, targets: number[],
   *   embargoTargets?: number[],       // cores to block trade with
   *   culturePolicyCI?: number,         // culture nudge: -1 (collectivist) to +1 (individualist)
   *   culturePolicyIO?: number,         // culture nudge: -1 (inward) to +1 (outward)
   *   sovFocusTargets?: number[],       // islands to prioritize consolidation on
   *   scoutActive?: boolean,            // spend allocation to expand fog of war
   *   rivalCores?: number[],            // cores to target preferentially in expansion
   *   partnerCores?: number[],          // cores to avoid targeting / trade bonus
   * }
   * @returns {Object} snapshot of current state
   */
  advanceTick(playerDecision = null) {
    if (this.finished) return this.snapshot();

    // Store scouting state for snapshot visibility
    this._scouting = !!(playerDecision?.scoutActive);

    const tick = this.tick;
    const year = this.year;
    const p = this.p;
    const N = this.N;

    const coresSet = new Set();
    for (let j = 0; j < N; j++) coresSet.add(this.controller[j]);
    const cores = [...coresSet].sort((a, b) => a - b);

    // Per-core aggregates
    const corePop = {};
    const coreC = {};
    const coreNCtrl = {};
    const coreFood = {};
    for (const c of cores) {
      corePop[c] = this._polityPop(c);
      coreC[c] = this._polityC(c);
      let nCtrl = 0, food = 0;
      for (let j = 0; j < N; j++) {
        if (this.controller[j] === c) {
          nCtrl++;
          food += this.substrate[j].crops.primary_yield;
        }
      }
      coreNCtrl[c] = nCtrl;
      coreFood[c] = food;
    }

    // ── ENVIRONMENTAL PRE-PASS: crop failure + fishery ──────
    // Crop failure: random per-arch yield penalty, more likely at low tech
    for (let j = 0; j < N; j++) {
      // Recover from previous failure
      if (this.cropFailureModifier[j] < 1.0) {
        this.cropFailureModifier[j] = Math.min(1.0, this.cropFailureModifier[j] + 0.25);
      }
      // Roll for new failure (only for inhabited arches with population above threshold)
      const archCore = this.controller[j];
      const archTech = this.tech[archCore] || 0;
      const failureProb = p.crop_failure_rate * Math.max(0.3, 1.0 - archTech / 8.0);
      if (this.pop[j] > 2 && this.cropFailureModifier[j] >= 1.0 && this.rng() < failureProb) {
        // 40-75% yield retained during failure
        this.cropFailureModifier[j] = 0.40 + this.rng() * 0.35;
        this.cropFailureLog.push({ arch: j, core: archCore, tick, year, modifier: this.cropFailureModifier[j] });
      }
    }

    // ── TRADE PRE-PASS ──────────────────────────────────────
    const tradeNet = {};
    for (const c of cores) tradeNet[c] = 0;

    // Player embargo & partner trade bonus sets
    const embargoSet = playerDecision?.embargoTargets ? new Set(playerDecision.embargoTargets) : null;
    const partnerSet = playerDecision?.partnerCores ? new Set(playerDecision.partnerCores) : null;

    for (const tc of cores) {
      const tcTech = this.tech[tc];
      for (const other of this.contactSet[tc]) {
        if (!coresSet.has(other) || other <= tc) continue;

        // Player embargo: skip trade with embargoed cores
        if (embargoSet && (tc === this.playerCore || other === this.playerCore)) {
          const otherSide = tc === this.playerCore ? other : tc;
          if (embargoSet.has(otherSide)) continue;
        }
        const otherTech = this.tech[other];
        const effTech = Math.min(tcTech, otherTech);
        const distRad = _gcDistArch(this.archs[tc], this.archs[other]);
        if (distRad < 1e-6) continue;

        const cropA = this.substrate[tc].crops.primary_crop;
        const cropB = this.substrate[other].crops.primary_crop;
        let comp = cropA === cropB ? 0.5 : 1.0;
        if (Math.abs(this.substrate[tc].climate.abs_latitude - this.substrate[other].climate.abs_latitude) > 15) comp += 0.3;
        for (const res of ["Au", "Cu"]) {
          if (!!this.substrate[tc].minerals[res] !== !!this.substrate[other].minerals[res]) comp += 0.15;
        }
        comp = Math.min(comp, 2.0);

        let effMarkup, layerMult;
        if (effTech < 2.0) {
          if (distRad > 0.55) continue;
          effMarkup = p.bulk_markup_rate;
          layerMult = 0.25;
        } else if (effTech < 5.0) {
          const hops = Math.max(1, Math.floor(distRad / 0.35) + 1);
          if (hops > 4) continue;
          effMarkup = Math.min(0.85, (p.luxury_markup_rate * 0.6 + p.bulk_markup_rate * 0.4) * hops);
          layerMult = 0.65;
        } else {
          effMarkup = p.bulk_markup_rate;
          layerMult = 1.0;
        }

        const massA = Math.sqrt(Math.max(1, corePop[tc])) * this.substrate[tc].crops.primary_yield;
        const massB = Math.sqrt(Math.max(1, corePop[other])) * this.substrate[other].crops.primary_yield;
        const volume = layerMult * comp * Math.sqrt(massA * massB) / (distRad ** 2);
        let netBenefit = volume * (1 - effMarkup) * 0.003;

        // Player partner bonus: +30% trade with partner cores
        if (partnerSet && (tc === this.playerCore || other === this.playerCore)) {
          const otherSide = tc === this.playerCore ? other : tc;
          if (partnerSet.has(otherSide)) netBenefit *= 1.3;
        }

        tradeNet[tc] += netBenefit;
        tradeNet[other] += netBenefit;
      }
    }

    // ── STAGE 1: Resource accounting ────────────────────────
    const energyRatio = {};
    const energySurplus = {};
    const resourcePressure = {};
    const foodDeficit = {};
    const indDeficit = {};
    const nucDeficit = {};

    for (const core of cores) {
      const tp = Math.max(1.0, corePop[core]);
      const ct = this.tech[core];
      let ratio, surplus, indDef;

      if (ct >= 7.0) {
        const eDemand = tp * ct * 0.002;
        const eSupply = coreC[core] * 0.2;
        ratio = _clamp(eSupply / Math.max(0.001, eDemand), 0.3, 1.5);
        surplus = Math.max(0, eSupply - eDemand) * 0.2 + tp * 0.01;
        indDef = eSupply < eDemand;
      } else {
        // Crop yield with failure modifier applied
        const cropY = this.substrate[core].crops.primary_yield * this.cropFailureModifier[core];
        const avgHC = this.substrate[core].climate.avg_h ?? 0.2;
        const landFactor = Math.max(0.3, 1.0 - avgHC * 0.35);
        let fishPol = 0;
        for (let j = 0; j < N; j++) {
          if (this.controller[j] === core) {
            // Fish yield modulated by fishery stock level
            fishPol += (this.substrate[j].climate.fish_y ?? 0)
              * (this.substrate[j].climate.coast_factor ?? 0)
              * this.fisheryStock[j];
          }
        }
        const fishAvg = fishPol / Math.max(1, coreNCtrl[core]);
        const totalCal = cropY * landFactor + fishAvg;
        const netTrade = tradeNet[core] || 0;
        ratio = _clamp(0.6 + totalCal * 0.2, 0.3, 1.5);
        surplus = totalCal * tp * 0.01 + netTrade;
        indDef = false;

        if (ct < 4.0) {
          const nCtrl = Math.max(1, coreNCtrl[core]);
          const cap = cropY * nCtrl * p.carry_cap_scale;
          surplus *= Math.min(1.0, cap / Math.max(tp, 1));
        }
      }

      energyRatio[core] = ratio;
      energySurplus[core] = surplus;
      const maintenance = ct * ct * p.maintenance_rate;
      resourcePressure[core] = maintenance > 0 ? Math.max(0, (maintenance - surplus) / maintenance) : 0;
      foodDeficit[core] = (coreFood[core] / Math.max(1, coreNCtrl[core])) < 1.0;
      indDeficit[core] = indDef;
      nucDeficit[core] = ct >= 9.0 && !this._hasPu(core);
    }

    // ── STAGE 2: Political allocation ───────────────────────
    const expBudget = {};
    const techBgt = {};
    const consolBudget = {};
    const maxSurplus = Math.max(...Object.values(energySurplus), 1.0);

    for (const core of cores) {
      const isPlayer = core === this.playerCore && playerDecision;

      let expS, tecS, conS;

      if (isPlayer) {
        // Player-provided allocation
        const total = (playerDecision.expansion || 0) + (playerDecision.techShare || 0) + (playerDecision.consolidation || 0);
        const norm = total > 0 ? total : 1;
        expS = (playerDecision.expansion || 0.33) / norm;
        tecS = (playerDecision.techShare || 0.33) / norm;
        conS = (playerDecision.consolidation || 0.34) / norm;
      } else {
        // AI allocation (same as simulate.js)
        [expS, tecS, conS] = this._sharesFromPos(this.cpos[core]);

        // IR posture
        const ownCap = _categorizeCap(energySurplus[core], maxSurplus);
        const otherSurpluses = cores.filter(c => c !== core).map(c => energySurplus[c]);
        const maxOther = otherSurpluses.length > 0 ? Math.max(...otherSurpluses) : 0;
        const othCap = _categorizeCap(maxOther, maxSurplus);
        const posture = _POSTURE_TABLE[`${ownCap},${othCap}`] || "hedge";

        if (posture === "explore" || posture === "project") { expS *= 1.3; conS *= 0.7; }
        else if (posture === "fortify" || posture === "hedge") { conS *= 1.3; expS *= 0.7; }
        else if (posture === "align") { conS *= 1.2; tecS *= 0.8; }

        let t = expS + tecS + conS;
        expS /= t; tecS /= t; conS /= t;

        // Desperation override
        const rp = resourcePressure[core] || 0;
        if (rp > 0) {
          let dExp, dTec, dCon;
          if (foodDeficit[core]) { dExp = 0.65; dTec = 0.20; dCon = 0.15; }
          else if (indDeficit[core]) { dExp = 0.55; dTec = 0.28; dCon = 0.17; }
          else if (nucDeficit[core]) { dExp = 0.58; dTec = 0.25; dCon = 0.17; }
          else { dExp = 0.45; dTec = 0.30; dCon = 0.25; }

          const w = _clamp(rp * p.desperation_weight, 0, 1);
          expS = (1 - w) * expS + w * dExp;
          tecS = (1 - w) * tecS + w * dTec;
          conS = (1 - w) * conS + w * dCon;

          if (rp > 0.3) {
            expS = Math.min(0.85, expS * 1.35);
            let t2 = expS + tecS + conS;
            expS /= t2; tecS /= t2; conS /= t2;
            this.desperationLog.push({ core, tick, year, resource_pressure: rp,
              food_deficit: foodDeficit[core], ind_deficit: indDeficit[core], nuc_deficit: nucDeficit[core] });
          }

          t = expS + tecS + conS;
          expS /= t; tecS /= t; conS /= t;
        }
      }

      const rp = resourcePressure[core] || 0;
      const budgetMult = rp > 0.3 ? 1.0 + _clamp(rp - 0.3, 0, 0.7) * 0.8 : 1.0;
      const budget = (energySurplus[core] + corePop[core] * 0.002) * budgetMult;
      expBudget[core] = budget * expS;
      techBgt[core] = budget * tecS;
      consolBudget[core] = budget * conS;
    }

    // ── STAGE 2b: Culture-space drift ───────────────────────
    for (const core of cores) {
      let [ci, io] = this.cpos[core];
      const [, tecS, conS] = this._sharesFromPos(this.cpos[core]);
      const er = energyRatio[core];

      ci += _clamp(er / 1.5, 0, 1) * (1 - conS) * p.culture_drift_rate;
      const threatLevel = _clamp(1.0 - er, 0, 1);
      ci -= threatLevel * p.culture_drift_rate;

      const tradeInt = Math.min(1.0, this.contactSet[core].size / Math.max(1, N * 0.3));
      io += tecS * tradeInt * p.culture_drift_rate;
      io -= _clamp(1.0 - er, 0, 1) * p.culture_drift_rate * 0.5;

      const fishR = this.substrate[core].climate.fisheries_richness ?? 0;
      if (fishR > 0.05) {
        const mt = this.substrate[core].climate.mean_temp ?? 18;
        const up = this.substrate[core].climate.upwelling ?? 0;
        const fdr = p.culture_drift_rate * fishR * 0.3;
        if (mt < 14) { ci -= fdr * 0.6; io -= fdr * 0.2; }
        if (up > 0.3) io += fdr * 0.8;
        if (mt > 20) { ci += fdr * 0.4; io += fdr * 0.4; }
        ci -= fdr * 0.1;
      }

      // Player cultural policy: small nudge (capped at ±0.3 of drift rate)
      if (core === this.playerCore && playerDecision) {
        const nudgeCap = p.culture_drift_rate * 0.3;
        if (playerDecision.culturePolicyCI) ci += _clamp(playerDecision.culturePolicyCI, -1, 1) * nudgeCap;
        if (playerDecision.culturePolicyIO) io += _clamp(playerDecision.culturePolicyIO, -1, 1) * nudgeCap;
      }

      this.cpos[core] = [_clamp(ci, -1, 1), _clamp(io, -1, 1)];
    }

    // ── STAGE 2c: Piety drift ───────────────────────────────
    // Crisis → faith rises. Prosperity → slow secularization.
    // Collective culture → piety reinforced. Tech > 7 → secularization pressure.
    for (const core of cores) {
      let piety = this.piety[core];
      const er = energyRatio[core];
      const [ci] = this.cpos[core];
      const dRate = p.piety_drift_rate;

      // Crisis: low energy ratio → piety rises (crisis → collective solidarity, spiritual appeal)
      if (er < 0.6) piety += dRate * (0.6 - er) * 2.5;
      // Prosperity: high surplus → gentle secularization
      else piety -= dRate * Math.min(0.4, (er - 0.6)) * 0.8;

      // Culture CI: collective reinforces piety, individual erodes it
      piety -= ci * dRate * 0.6;

      // Secularization at high tech (enlightenment pressure, tech ≥ 7)
      if (this.tech[core] > 7.0) piety -= dRate * (this.tech[core] - 7.0) * 0.25;

      // Trade contact diversity → mild secularization (exposure to other beliefs)
      const contactDiv = Math.min(1.0, this.contactSet[core].size / Math.max(1, this.N * 0.25));
      piety -= dRate * contactDiv * 0.3;

      this.piety[core] = _clamp(piety, 0.05, 0.95);
    }

    // ── STAGE 3: Rumor propagation ──────────────────────────
    for (const core of cores) {
      if (this.tech[core] < 1.5) continue;
      const ctrlSet = new Set(this._controlled(core));
      let newThisTick = 0;
      const maxNew = this.tech[core] < 5.0 ? 1 : 2;
      outer: for (const j of ctrlSet) {
        if (newThisTick >= maxNew) break;
        for (const nb of this.adj[j]) {
          if (!ctrlSet.has(nb)) {
            const otherCore = this.controller[nb];
            if (otherCore !== core && !this.contactSet[core].has(otherCore)) {
              this.contactSet[core].add(otherCore);
              this.contactSet[otherCore].add(core);
              newThisTick++;
              if (newThisTick >= maxNew) break outer;
            }
          }
        }
      }

      if (this.tech[core] >= 7.0) {
        const signalR = p.df_detection_range * (this.tech[core] / 10.0);
        for (const other of cores) {
          if (other === core) continue;
          const dist = _gcDistArch(this.archs[core], this.archs[other]);
          if (dist <= signalR) {
            const keyOC = `${other},${core}`;
            const keyCO = `${core},${other}`;
            this.awareness.set(keyOC, Math.min(1, (this.awareness.get(keyOC) || 0) + 0.15));
            this.awareness.set(keyCO, Math.min(1, (this.awareness.get(keyCO) || 0) + 0.10));
          }
        }
      }
    }

    // ── STAGE 4: Dark Forest detection ──────────────────────
    if (this.dfYear === null) {
      for (const core of cores) {
        if (this.tech[core] < 9.0) continue;
        for (const other of cores) {
          if (other === core || this.tech[other] < 8.0) continue;
          const aw = this.awareness.get(`${core},${other}`) || 0;
          const minArchs = Math.max(1, Math.floor(p.df_min_territory_frac * N));
          if (coreNCtrl[core] < minArchs || coreNCtrl[other] < minArchs) continue;
          const dist = _gcDistArch(this.archs[core], this.archs[other]);
          if (dist <= p.df_detection_range * 1.5 && aw > 0.2) {
            this.dfYear = year;
            this.dfArch = core;
            this.dfDetector = other;
            this.awareness.set(`${core},${other}`, 1.0);
            this.awareness.set(`${other},${core}`, 1.0);
            break;
          }
        }
        if (this.dfYear !== null) break;
      }
    }

    // ── STAGE 5: Tech growth + decay + population ───────────
    for (const core of cores) {
      const a0 = this._A0FromPos(this.cpos[core]);
      const nc = this.contactSet[core].size;
      const er = this.tech[core] >= 9.0 && !this._hasPu(core)
        ? energyRatio[core] * p.pu_dependent_factor
        : energyRatio[core];
      const cropY = this.substrate[core].crops.primary_yield;

      const effNc = Math.min(nc, Math.floor(this.tech[core] * 2) + 1);
      const contactMult = 1.0 + _log2(effNc + 1) * 0.3;
      const energyMult = er * p.energy_to_tfp;
      const shareMult = this._sharesFromPos(this.cpos[core])[1] / 0.3;

      const cropExp = cropY ** 0.3;
      const baseFloor = cropExp * 0.003;

      let accelRate;
      const t = this.tech[core];
      if (t < 1.5) accelRate = 0;
      else if (t < 3.0) accelRate = 0.002;
      else if (t < 5.0) accelRate = 0.008;
      else if (t < 7.0) accelRate = 0.025;
      else accelRate = 0.120;

      const accel = a0 * cropExp * shareMult * accelRate * contactMult * energyMult;
      let delta = baseFloor + accel;
      if (t > 9.0) delta *= _clamp((11.0 - t) / 2.0, 0, 1);
      this.tech[core] += delta;

      // Tech decay
      const maintenanceCost = this.tech[core] * this.tech[core] * p.maintenance_rate;
      const availE = energySurplus[core];
      if (availE < maintenanceCost) {
        const shortfall = maintenanceCost - availE;
        const decayAmt = shortfall * p.decay_rate;
        const oldT = this.tech[core];
        this.tech[core] = Math.max(0.1, this.tech[core] - decayAmt);
        if (decayAmt > 0.005) {
          this.techDecayLog.push({ core, tick, year, tech_before: oldT, tech_after: this.tech[core], decay: decayAmt });
        }
      }

      this.knowledge[core] += delta * a0 * 0.5;

      // Population
      for (let j = 0; j < N; j++) {
        if (this.controller[j] !== core) continue;
        let cap = this.carryCap[j];
        if (this.tech[core] >= 7.0 && this.cRemaining[j] > 0) cap *= (1.0 + er * 0.5);
        if (this.tech[core] >= 9.0) cap *= 1.5;
        // Malaria belt: reduce effective carrying capacity in tropical archipelagos
        // Medical knowledge (tech ≥ 6) cuts the penalty to 30%
        const mSev = this.malariaFactor[j];
        if (mSev > 0) {
          const mPenalty = mSev * p.malaria_cap_penalty * (this.tech[core] >= 6.0 ? 0.30 : 1.0);
          cap *= (1.0 - mPenalty);
        }
        let growthRate = 0.03 * er * (1.0 - this.pop[j] / Math.max(1, cap));
        // Urban disease sink: density-dependent mortality above 70% capacity
        const densityRatio = this.pop[j] / Math.max(1, cap);
        if (densityRatio > 0.7) {
          growthRate -= (densityRatio - 0.7) * p.urban_disease_rate;
        }
        this.pop[j] *= (1.0 + _clamp(growthRate, -0.05, 0.10));
        this.pop[j] = Math.max(1.0, this.pop[j]);
      }

      // Propagate tech to periphery
      for (let j = 0; j < N; j++) {
        if (this.controller[j] === core && j !== core) this.tech[j] = Math.max(this.tech[j], this.tech[core] * 0.7);
      }
    }

    // Knowledge diffusion
    const worldMaxTech = Math.max(...cores.map(c => this.tech[c]));
    for (const core of cores) {
      let maxContactTech = 0;
      for (const c of this.contactSet[core]) {
        if (coresSet.has(c) && this.tech[c] > maxContactTech) maxContactTech = this.tech[c];
      }
      if (maxContactTech > this.tech[core] + 1.0) this.tech[core] += (maxContactTech - this.tech[core]) * 0.08;
      if (worldMaxTech > this.tech[core] + 1.0) this.tech[core] += (worldMaxTech - this.tech[core]) * 0.03;
    }

    // ── STAGE 5b: Epidemic waves ────────────────────────────
    // Periodic disease events propagating through trade contact networks.
    // Probability per tick scales with contact count × population density.
    // Separate from contact epidemics (which fire on first-contact absorption).
    for (const core of cores) {
      const nc = this.contactSet[core].size;
      if (nc < 2) continue;  // isolated polities don't originate waves
      // Compute population density relative to carrying capacity
      let totalCap = 0, totalPop = 0;
      for (let j = 0; j < N; j++) {
        if (this.controller[j] === core) {
          totalCap += this.carryCap[j];
          totalPop += this.pop[j];
        }
      }
      const density = totalCap > 0 ? totalPop / totalCap : 0;
      // Probability: base × contact bonus × density. ~3-8% per tick for trade hubs.
      const epiProb = p.epi_base_severity * 0.015 * (1.0 + nc * 0.2) * Math.max(0.3, density);
      if (this.rng() < epiProb) {
        const mortality = 0.04 + this.rng() * 0.12;  // 4–16% population loss
        const sourceName = core;
        // Spread to trade partners with ~35% probability each
        const affected = new Set([core]);
        for (const other of this.contactSet[core]) {
          if (coresSet.has(other) && this.rng() < 0.35) affected.add(other);
        }
        for (const c of affected) {
          for (let j = 0; j < N; j++) {
            if (this.controller[j] === c) {
              this.pop[j] *= (1.0 - mortality);
              this.pop[j] = Math.max(1.0, this.pop[j]);
            }
          }
        }
        this.waveEpiLog.push({
          tick, year, source: sourceName,
          mortality_rate: mortality,
          affected: [...affected],
        });
      }
    }

    // ── Fishery stock update ────────────────────────────────
    // Natural recovery + depletion from over-exploitation.
    // Over-exploitation = population density above sustainable threshold.
    for (let j = 0; j < N; j++) {
      const core = this.controller[j];
      const cap = this.carryCap[j];
      const densityRatio = cap > 0 ? this.pop[j] / cap : 0;
      // Depletion increases when density is above 50% carrying capacity
      const overExploit = Math.max(0, densityRatio - 0.5) * p.fishery_overfish_rate;
      // Natural recovery toward 1.0
      const recovery = p.fishery_recovery_rate * (1.0 - this.fisheryStock[j]);
      this.fisheryStock[j] = _clamp(this.fisheryStock[j] + recovery - overExploit, 0.05, 1.0);
      // Log severe depletion
      if (this.fisheryStock[j] < 0.3 && (tick % 4 === 0)) {
        const prev = this.fisheryLog[this.fisheryLog.length - 1];
        if (!prev || prev.arch !== j || tick - prev.tick > 8) {
          this.fisheryLog.push({ arch: j, core, tick, year, stock: this.fisheryStock[j] });
        }
      }
    }

    // ── STAGE 6: Thompson Sampling expansion ────────────────
    for (const core of cores) {
      let budget = expBudget[core] || 0;
      if (budget < 0.1 || this.tech[core] < 2.0) continue;

      const isPlayer = core === this.playerCore && playerDecision;
      const playerTargets = isPlayer && playerDecision.targets ? new Set(playerDecision.targets) : null;

      const [tsA, tsB] = this._tsPriorsFromPos(this.cpos[core]);
      const ctrlSet = new Set(this._controlled(core));
      const frontier = new Set();
      for (const j of ctrlSet) {
        for (const nb of this.adj[j]) {
          if (!ctrlSet.has(nb)) frontier.add(nb);
        }
      }
      if (frontier.size === 0) continue;

      const candidates = [];
      for (const target of frontier) {
        // If player specified targets, only consider those
        if (playerTargets && !playerTargets.has(target)) continue;

        let dist = _gcDistArch(this.archs[core], this.archs[target]);
        const tsScore = _betaSample(this.rng, tsA, tsB);
        const rv = _resourceValue(this.substrate[target].minerals, this.tech[core], p.cu_unlock_tech);

        if (this.tech[core] >= 7.0 && (this.substrate[target].minerals.C || 0) > 0 && this.scrambleOnset === null)
          this.scrambleOnset = tick;
        if (this.tech[core] >= 9.0 && this.substrate[target].minerals.Pu && this.puScrambleOnset === null)
          this.puScrambleOnset = tick;

        let despBonus = 0;
        const rp = resourcePressure[core] || 0;
        if (rp > 0) {
          const tMins = this.substrate[target].minerals;
          const tCrops = this.substrate[target].crops;
          const tClim = this.substrate[target].climate;
          if (foodDeficit[core]) despBonus += rp * ((tCrops.primary_yield || 0) * 1.5 + (tClim.fisheries_richness || 0) * 2.5);
          if (indDeficit[core]) despBonus += rp * (tMins.C || 0) * 4.0;
          if (nucDeficit[core] && tMins.Pu) despBonus += rp * 6.0;
          if (rp > 0.3) dist *= _clamp(1.0 - (rp - 0.3) * 0.5, 0.5, 1.0);
        }

        // Player diplomacy: rival bonus / partner penalty for expansion targeting
        let diploBonus = 0;
        if (isPlayer && playerDecision) {
          const targetCtrl = this.controller[target];
          const rivalSet = playerDecision.rivalCores ? new Set(playerDecision.rivalCores) : null;
          const partnerSetD = playerDecision.partnerCores ? new Set(playerDecision.partnerCores) : null;
          if (rivalSet && rivalSet.has(targetCtrl)) diploBonus += 2.0;
          if (partnerSetD && partnerSetD.has(targetCtrl)) diploBonus -= 3.0; // strongly avoid partner territory
        }

        // Piety bonus: high-piety polities are driven toward missionary expansion
        // Extra affinity for low-tech targets (conversion dynamic)
        let pietyBonus = 0;
        const cPiety = this.piety[core];
        if (cPiety > 0.65) {
          pietyBonus = (cPiety - 0.65) * 2.0;
          if (this.tech[core] - this.tech[target] > 1.5) pietyBonus += (cPiety - 0.65) * 1.5;
        }

        candidates.push([tsScore + p.resource_targeting_weight * rv + despBonus + diploBonus + pietyBonus - dist * 1.5, target, dist, rv]);
      }
      candidates.sort((a, b) => b[0] - a[0]);

      let absorbedThisTick = 0;
      for (const [score, target, dist, rv] of candidates) {
        if (budget < 0.1 || absorbedThisTick >= 1) break;

        const techAdv = Math.max(0.1, this.tech[core] - this.tech[target] + 1.0);
        let cost = (this.pop[target] * 0.05 + dist ** 3 * 40) / (techAdv ** 1.5);

        const targetCore = this.controller[target];
        if (targetCore !== target) {
          cost *= 3.0;
          if (this.tech[core] - this.tech[targetCore] < 2.0) continue;
        }
        if (cost > budget) continue;
        if (this.pop[target] > corePop[core] * 0.5 && this.tech[core] - this.tech[target] < 2.0) continue;

        // Epidemic shock
        if (this.firstContactTick[target] === null) {
          this.firstContactTick[target] = tick;
          const cc = this.substrate[core].crops.primary_crop;
          const ct = this.substrate[target].crops.primary_crop;
          const cdist = _cropDistance(cc, ct);
          const sev = p.epi_base_severity + this.rng() * 0.15;
          const mort = sev * cdist;
          this.pop[target] *= (1 - mort);
          this.epiLog.push({ arch: target, contactor: core, mortality_rate: mort, tick, year });
        }

        // Transfer
        for (let j = 0; j < N; j++) {
          if (this.controller[j] === target) this.controller[j] = core;
        }
        this.controller[target] = core;
        this.absorbedTick[target] = tick;
        this.sovereignty[target] = _clamp(0.15 + dist * 0.3, 0.10, 0.50);
        budget -= cost;
        absorbedThisTick++;

        for (const c of this.contactSet[target]) {
          if (c !== core) this.contactSet[core].add(c);
        }
        this.cpos[core][0] = _clamp(this.cpos[core][0] * 0.95 + this.cpos[target][0] * 0.05, -1, 1);
        this.cpos[core][1] = _clamp(this.cpos[core][1] * 0.95 + this.cpos[target][1] * 0.05, -1, 1);
        // Piety blending: conqueror absorbs a fraction of the conquered polity's piety
        this.piety[core] = _clamp(this.piety[core] * 0.92 + this.piety[target] * 0.08, 0.05, 0.95);

        this.expansionLog.push({ core, target, tick, year, tech_gap: this.tech[core] - this.tech[target], resource_driven: rv > 0 });
      }
    }

    // ── STAGE 7: Sovereignty drift ──────────────────────────
    const sovFocusSet = playerDecision?.sovFocusTargets ? new Set(playerDecision.sovFocusTargets) : null;
    for (let i = 0; i < N; i++) {
      if (this.controller[i] === i) continue;
      const core = this.controller[i];
      const dist = _gcDistArch(this.archs[core], this.archs[i]);
      let extraction = p.sov_extraction_decay / Math.max(0.1, dist) * _clamp(energyRatio[core] ?? 1, 0, 1.5);

      // Player sovereignty focus: reduce extraction on focused islands (faster stabilization)
      if (core === this.playerCore && sovFocusSet && sovFocusSet.has(i)) {
        extraction *= 0.4; // 60% less extraction = faster sovereignty recovery
      }

      // Piety bonus: high-piety empires integrate conquered populations faster
      // (religious conversion as centripetal force — Abbasid model)
      const corePiety = this.piety[core];
      if (corePiety > 0.5) {
        extraction *= (1.0 + (corePiety - 0.5) * p.piety_absorption_bonus);
      }

      const recovery = p.sov_extraction_decay * this.sovereignty[i] * (this.pop[i] / Math.max(1, this.pop[core])) * 0.5;
      this.sovereignty[i] += (recovery - extraction) * 0.1;
      this.sovereignty[i] = _clamp(this.sovereignty[i], 0.05, 0.95);
      if (this.tech[core] >= 9.0 && year >= -200) this.sovereignty[i] = Math.min(0.80, this.sovereignty[i] + 0.015);
    }

    // ── STAGE 8: Naphtha depletion ──────────────────────────
    for (let i = 0; i < N; i++) {
      const core = this.controller[i];
      if (this.tech[core] >= 7.0 && this.cRemaining[i] > 0) {
        const extraction = this.pop[i] * this.tech[core] * p.naphtha_depletion * 0.0005;
        this.cRemaining[i] = Math.max(0, this.cRemaining[i] - extraction);
      }
    }

    // Snapshots
    if (year === -5000) { this.techSnapshots.after_antiquity = [...this.tech]; this.popSnapshots.after_antiquity = [...this.pop]; }
    else if (year === -2000) { this.techSnapshots.after_serial = [...this.tech]; this.popSnapshots.after_serial = [...this.pop]; }
    else if (year === -500) { this.techSnapshots.after_colonial = [...this.tech]; this.popSnapshots.after_colonial = [...this.pop]; }
    else if (year === -200) { this.techSnapshots.after_industrial = [...this.tech]; this.popSnapshots.after_industrial = [...this.pop]; }

    // Timeline snapshot (every 4 ticks = 200 years)
    if (tick % 4 === 0) {
      this.timeline.push({
        year,
        controller: [...this.controller],
        tech: Array.from(this.tech, t => Math.round(t * 10) / 10),
        pop: Array.from(this.pop, p => Math.round(p)),
      });
    }

    // Advance tick
    this.tick++;
    this.year += TICK_YEARS;
    if (this.tick >= N_TICKS) this.finished = true;

    return this.snapshot();
  }

  // ── Snapshot: cheap copy of rendering-relevant state ────

  snapshot() {
    const cores = [...new Set(this.controller)].sort((a, b) => a - b);
    const polityPops = {};
    for (const c of cores) {
      let pp = 0;
      for (let j = 0; j < this.N; j++) if (this.controller[j] === c) pp += this.pop[j];
      polityPops[c] = pp;
    }
    const totalWorldPop = this.pop.reduce((s, v) => s + v, 0);

    // Player stats
    let playerStats = null;
    if (this.playerCore !== null) {
      const pc = this.playerCore;
      const territory = this._controlled(pc);
      playerStats = {
        pop: Math.round(this._polityPop(pc)),
        tech: Math.round(this.tech[pc] * 10) / 10,
        territory: territory.length,
        naphtha: Math.round(this._polityC(pc) * 100) / 100,
        hasPu: this._hasPu(pc),
        culturePos: [...this.cpos[pc]],
        cultureLabel: _cultureLabelFromPos(this.cpos[pc]),
        sovereignty: Math.round(this.sovereignty[pc] * 1000) / 1000,
        contacts: this.contactSet[pc].size,
      };
    }

    return {
      tick: this.tick,
      year: this.year,
      finished: this.finished,
      controller: [...this.controller],
      tech: Array.from(this.tech, t => Math.round(t * 10) / 10),
      pop: Array.from(this.pop, p => Math.round(p)),
      cpos: this.cpos.map(c => [...c]),
      nPolities: cores.length,
      polityPops,
      totalWorldPop: Math.round(totalWorldPop),
      dfYear: this.dfYear,
      dfArch: this.dfArch,
      dfDetector: this.dfDetector,
      playerStats,
      // Last tick's events
      events: this.expansionLog.filter(e => e.tick === this.tick - 1),
      // Fog of war
      visibility: this.playerCore !== null ? this.getVisibility(this.playerCore, this._scouting) : null,
      // Sovereignty per-island (for sovereignty focus UI)
      sovereignty: Array.from(this.sovereignty, s => Math.round(s * 1000) / 1000),
      // Contacted polity cores (for intel display)
      contactedCores: this.playerCore !== null ? [...this.contactSet[this.playerCore]] : [],
      // Primary crop per archipelago (for narrative text)
      crops: this.substrate.map(s => s.crops?.primary_crop || 'foraging'),
      // Epidemic waves that fired this tick (for event popups / dispatch)
      waveEpis: this.waveEpiLog.filter(e => e.tick === this.tick - 1),
      // Crop failures this tick (for dispatch)
      cropFailures: this.cropFailureLog.filter(e => e.tick === this.tick - 1),
      // Current fishery stock per arch (for situation cards + Observatory)
      fisheryStock: Array.from(this.fisheryStock, s => Math.round(s * 100) / 100),
      // Piety per core (for situation cards + dispatch)
      piety: Array.from(this.piety, v => Math.round(v * 100) / 100),
    };
  }

  // ── Finalize: same return shape as simulate() ──────────

  finalize() {
    const N = this.N;
    const finalCores = [...new Set(this.controller)].sort((a, b) => a - b);
    for (const core of finalCores) {
      if (this.tech[core] >= 9.0) {
        if (this._hasPu(core)) { this.fleetScale[core] = 1.0; this.sovereignty[core] = Math.min(1, this.sovereignty[core] + 0.1); }
        else { this.fleetScale[core] = this.p.pu_dependent_factor; this.sovereignty[core] = Math.max(0.3, this.sovereignty[core] - 0.05); }
      }
    }

    const totalWorldPop = this.pop.reduce((s, v) => s + v, 0);
    const polityPops = {};
    for (const c of finalCores) {
      let pp = 0;
      for (let j = 0; j < N; j++) if (this.controller[j] === c) pp += this.pop[j];
      polityPops[c] = pp;
    }

    const hegemons = finalCores
      .filter(c => polityPops[c] > totalWorldPop * 0.09)
      .sort((a, b) => polityPops[b] - polityPops[a]);
    const hegemonCultures = {};
    for (const c of hegemons) hegemonCultures[c] = _cultureLabelFromPos(this.cpos[c]);

    const maxPop = Math.max(...this.pop);

    const states = [];
    for (let i = 0; i < N; i++) {
      const core = this.controller[i];
      let faction, status;
      if (core === i && hegemons.includes(i)) {
        faction = _cultureLabelFromPos(this.cpos[i]);
        status = "core";
      } else if (hegemons.includes(core)) {
        faction = _cultureLabelFromPos(this.cpos[core]);
        if (this.sovereignty[i] < 0.3) status = "colony";
        else if (this.sovereignty[i] < 0.6) status = _cultureLabelFromPos(this.cpos[core]) === "subject" ? "garrison" : "client";
        else status = "contacted";
      } else if (this.controller[i] === i) {
        faction = "independent";
        status = this.absorbedTick[i] === null ? "uncontacted" : "independent";
      } else {
        faction = _cultureLabelFromPos(this.cpos[core]);
        status = "tributary";
      }

      let era = null;
      if (this.absorbedTick[i] !== null) {
        const cy = START_YEAR + this.absorbedTick[i] * TICK_YEARS;
        if (cy < -2000) era = "sail";
        else if (cy < -500) era = "colonial";
        else if (cy < -200) era = "industrial";
        else era = "nuclear";
      }

      states.push({
        faction, status,
        name: `arch_${i}`,
        population: Math.round(this.pop[i]),
        urbanization: maxPop > 0 ? this.pop[i] / maxPop : 0,
        tech: Math.round(this.tech[i] * 10) / 10,
        sovereignty: Math.round(this.sovereignty[i] * 1000) / 1000,
        tradeIntegration: Math.min(1, this.contactSet[i].size / Math.max(1, N * 0.3)),
        eraOfContact: era,
        hopCount: 0,
        culture: _cultureLabelFromPos(this.cpos[this.controller[i]]),
        culture_pos: [...this.cpos[this.controller[i]]],
        fleet_scale: this.fleetScale[i],
        c_remaining: this.cRemaining[i],
        controller: this.controller[i],
      });
    }

    let reachArch = null, latticeArch = null;
    for (const h of hegemons) {
      const label = _cultureLabelFromPos(this.cpos[h]);
      if (label === "civic" && reachArch === null) reachArch = h;
      else if (label === "subject" && latticeArch === null) latticeArch = h;
    }
    if (reachArch === null && hegemons.length > 0) reachArch = hegemons[0];
    if (latticeArch === null && hegemons.length >= 2) latticeArch = hegemons[1];
    else if (latticeArch === null) latticeArch = reachArch ?? 0;

    for (let i = 0; i < N; i++) {
      const core = this.controller[i];
      if (core === reachArch || i === reachArch) states[i].faction = "reach";
      else if (core === latticeArch || i === latticeArch) states[i].faction = "lattice";
      else if (states[i].faction === "independent") states[i].faction = "unknown";
    }

    const totalCInit = this.cInitial.reduce((s, v) => s + v, 0);
    const totalCRem = this.cRemaining.reduce((s, v) => s + v, 0);

    return {
      states, log: this.expansionLog,
      df_year: this.dfYear, df_arch: this.dfArch, df_detector: this.dfDetector,
      reach_arch: reachArch ?? 0, lattice_arch: latticeArch ?? 0,
      epi_log: this.epiLog, wave_epi_log: this.waveEpiLog, substrate: this.substrate,
      hegemons, hegemon_cultures: hegemonCultures,
      hegemon_culture_pos: Object.fromEntries(hegemons.map(c => [c, [...this.cpos[c]]])),
      tech_snapshots: this.techSnapshots, pop_snapshots: this.popSnapshots,
      tech_decay_log: this.techDecayLog, desperation_log: this.desperationLog,
      scramble_onset_tick: this.scrambleOnset, pu_scramble_onset_tick: this.puScrambleOnset,
      c_depletion_frac: totalCInit > 0 ? 1 - totalCRem / totalCInit : 0,
      polity_pops: polityPops,
      n_polities: finalCores.length,
      uncontacted_count: Array.from({ length: N }, (_, i) => i)
        .filter(i => this.controller[i] === i && !hegemons.includes(i) && this.absorbedTick[i] === null).length,
      timeline: this.timeline,
    };
  }
}
