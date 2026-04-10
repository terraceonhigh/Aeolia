// ═══════════════════════════════════════════════════════════
// simulate.js — Port of sim_proxy_v2.py simulate()
// Energy-coupled, faction-agnostic history engine
// 400 ticks × 50 years = 20,000 year simulation
// ═══════════════════════════════════════════════════════════

import { mulberry32 } from './rng.js';
import { computeSubstrate } from './substrate.js';

const TICK_YEARS = 50;
const START_YEAR = -20000;
const END_YEAR = 0;
const N_TICKS = (END_YEAR - START_YEAR) / TICK_YEARS; // 400
const _ISLAND_MAX_HEIGHT = 3000.0;

function _clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }
function _log2(x) { return x > 0 ? Math.log2(x) : 0; }

// ── Parameters ──────────────────────────────────────────────

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
  // Continuous ramps replace cliff-gates so resource scrambles are gradients,
  // not single-tick events. Each mineral's desirability rises smoothly as
  // the polity's tech crosses the relevant metallurgical / industrial / nuclear
  // threshold window.
  let val = 0;
  // Copper: useful from early metallurgy (~tech 2) through industrialisation (~tech 5)
  if (minerals.Cu) val += 1.0 * _clamp((tech - (cuUnlock - 1)) / 2.0, 0, 1);
  // Gold: trade-era prestige; ramps from tech 3 to 5
  if (minerals.Au) val += 1.5 * _clamp((tech - 3.0) / 2.0, 0, 1);
  // Naphtha: industrial fuel; ramps from tech 5 (early use) to tech 8 (full dependence)
  const c = minerals.C || 0;
  if (c > 0) val += c * 5.0 * _clamp((tech - 5.0) / 3.0, 0, 1);
  // Pyra: nuclear material; ramps from tech 7 (research) to tech 9.5 (weapons programme)
  if (minerals.Pu) val += 10.0 * _clamp((tech - 7.0) / 2.5, 0, 1);
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

// ── Main simulation ─────────────────────────────────────────

export function simulate(world, params = null) {
  const p = params || DEFAULT_PARAMS;
  const archs = world.archs;
  const plateauEdges = world.plateauEdges;
  const N = archs.length;
  const seed = world.seed || 42;

  // Substrate
  let substrate = world.substrate;
  if (!substrate || !substrate[0] || !substrate[0].culture_pos) {
    substrate = computeSubstrate(archs, plateauEdges, seed, p.naphtha_richness);
  }
  // Ensure fields
  for (let i = 0; i < N; i++) {
    const mins = substrate[i].minerals;
    if (mins.C === undefined) {
      const sr = archs[i].shelfR ?? archs[i].shelf_r ?? 0.06;
      const td = substrate[i].climate.tidal_range ?? 2.0;
      mins.C = sr >= 0.04 ? sr * td * p.naphtha_richness : 0;
    }
    if (!substrate[i].culture_pos) {
      const crop = substrate[i].crops.primary_crop || "foraging";
      substrate[i].culture_pos = [...(_CROP_CULTURE_SEED[crop] || [0, 0])];
    }
    substrate[i].culture = _cultureLabelFromPos(substrate[i].culture_pos);

    // Fallback coast/fish fields
    const clim = substrate[i].climate;
    if (clim.coast_factor === undefined) {
      const ec = plateauEdges.reduce((n, e) => n + (e[0] === i || e[1] === i ? 1 : 0), 0);
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
      const pks = archs[i].peaks || [];
      clim.avg_h = pks.length > 0
        ? pks.reduce((s, pk) => s + pk.h, 0) / (pks.length * _ISLAND_MAX_HEIGHT)
        : (archs[i].avg_h ?? 0.2);
    }
  }

  const rng = mulberry32(((seed !== 0 ? seed : 42) * 31 + 1066) | 0);

  // Culture-space positions
  const cpos = [];
  for (let i = 0; i < N; i++) {
    const base = substrate[i].culture_pos || [0, 0];
    const ci = _clamp(base[0] + (rng() - 0.5) * 2.0 * p.culture_noise_scale, -1, 1);
    const io = _clamp(base[1] + (rng() - 0.5) * 2.0 * p.culture_noise_scale, -1, 1);
    cpos.push([ci, io]);
  }

  // Adjacency
  const adj = Array.from({ length: N }, () => []);
  for (const edge of plateauEdges) {
    const [a, b] = edge;
    if (!adj[a].includes(b)) adj[a].push(b);
    if (!adj[b].includes(a)) adj[b].push(a);
  }

  // Per-arch state
  const pop = new Float64Array(N);
  const tech = new Float64Array(N);
  const sovereignty = new Float64Array(N).fill(1.0);
  const cRemaining = new Float64Array(N);
  const cInitial = new Float64Array(N);
  const knowledge = new Float64Array(N);
  const controller = Array.from({ length: N }, (_, i) => i);
  const contactSet = Array.from({ length: N }, () => new Set());
  const fleetScale = new Float64Array(N);
  const awareness = new Map();
  const absorbedTick = new Array(N).fill(null);
  const absorbedTech = new Array(N).fill(null); // tech level of absorbing core at time of absorption
  const firstContactTick = new Array(N).fill(null);

  // Initialize
  for (let i = 0; i < N; i++) {
    const arch = archs[i];
    const pkCount = (arch.peaks ? arch.peaks.length : 0) || arch.peak_count || 2;
    const sz = (arch.shelfR ?? arch.shelf_r ?? 0.06) / 0.12;
    pop[i] = pkCount * sz * (3.0 + rng() * 4.0);
    tech[i] = 0.3 + rng() * 0.4;
    cRemaining[i] = substrate[i].minerals.C || 0;
    cInitial[i] = cRemaining[i];
    knowledge[i] = substrate[i].crops.primary_yield * 0.3;
  }

  // Carrying capacity
  const carryCap = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    const y = substrate[i].crops.primary_yield;
    const pk = (archs[i].peaks ? archs[i].peaks.length : 0) || archs[i].peak_count || 2;
    const sz = (archs[i].shelfR ?? archs[i].shelf_r ?? 0.06) / 0.12;
    carryCap[i] = y * pk * sz * 50.0 + 5.0;
  }

  // Culture helpers
  function sharesFromPos(pos) {
    const [ci, io] = pos;
    const individual = (ci + 1) * 0.5;
    const outward = (io + 1) * 0.5;
    let expS = p.base_expansion + p.outward_expansion_coeff * outward + p.individual_expansion_coeff * individual;
    let tecS = p.base_tech + p.outward_tech_coeff * outward;
    let conS = Math.max(0.05, 1.0 - expS - tecS);
    const t = expS + tecS + conS;
    return [expS / t, tecS / t, conS / t];
  }

  function A0FromPos(pos) {
    const [ci, io] = pos;
    return p.base_A0 + p.individual_A0_coeff * ((ci + 1) * 0.5) + p.outward_A0_coeff * ((io + 1) * 0.5);
  }

  function tsPriorsFromPos(pos) {
    const [ci, io] = pos;
    const outward = (io + 1) * 0.5;
    const collective = (1 - ci) * 0.5;
    return [1.0 + outward, 1.0 + (1.0 - outward) * collective];
  }

  function controlled(core) {
    const r = [];
    for (let j = 0; j < N; j++) if (controller[j] === core) r.push(j);
    return r;
  }
  function polityPop(core) {
    let s = 0;
    for (let j = 0; j < N; j++) if (controller[j] === core) s += pop[j];
    return s;
  }
  function polityC(core) {
    let s = 0;
    for (let j = 0; j < N; j++) if (controller[j] === core) s += cRemaining[j];
    return s;
  }
  function hasPu(core) {
    for (let j = 0; j < N; j++) if (controller[j] === core && substrate[j].minerals.Pu) return true;
    return false;
  }

  // Diagnostics
  const epiLog = [];
  const expansionLog = [];
  let dfYear = null, dfArch = null, dfDetector = null;
  let scrambleOnset = null, puScrambleOnset = null;
  const techSnapshots = {};
  const popSnapshots = {};
  const techDecayLog = [];
  const desperationLog = [];
  const timeline = [];

  // ── TICK LOOP ─────────────────────────────────────────────

  for (let tick = 0; tick < N_TICKS; tick++) {
    const year = START_YEAR + tick * TICK_YEARS;

    const coresSet = new Set();
    for (let j = 0; j < N; j++) coresSet.add(controller[j]);
    const cores = [...coresSet].sort((a, b) => a - b);

    // Per-core aggregates
    const corePop = {};
    const coreC = {};
    const coreNCtrl = {};
    const coreFood = {};
    for (const c of cores) {
      corePop[c] = polityPop(c);
      coreC[c] = polityC(c);
      let nCtrl = 0, food = 0;
      for (let j = 0; j < N; j++) {
        if (controller[j] === c) {
          nCtrl++;
          food += substrate[j].crops.primary_yield;
        }
      }
      coreNCtrl[c] = nCtrl;
      coreFood[c] = food;
    }

    // ── TRADE PRE-PASS ──────────────────────────────────────
    const tradeNet = {};
    for (const c of cores) tradeNet[c] = 0;

    for (const tc of cores) {
      const tcTech = tech[tc];
      for (const other of contactSet[tc]) {
        if (!coresSet.has(other) || other <= tc) continue;
        const otherTech = tech[other];
        const effTech = Math.min(tcTech, otherTech);
        const distRad = _gcDistArch(archs[tc], archs[other]);
        if (distRad < 1e-6) continue;

        const cropA = substrate[tc].crops.primary_crop;
        const cropB = substrate[other].crops.primary_crop;
        let comp = cropA === cropB ? 0.5 : 1.0;
        if (Math.abs(substrate[tc].climate.abs_latitude - substrate[other].climate.abs_latitude) > 15) comp += 0.3;
        for (const res of ["Au", "Cu"]) {
          if (!!substrate[tc].minerals[res] !== !!substrate[other].minerals[res]) comp += 0.15;
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

        const massA = Math.sqrt(Math.max(1, corePop[tc])) * substrate[tc].crops.primary_yield;
        const massB = Math.sqrt(Math.max(1, corePop[other])) * substrate[other].crops.primary_yield;
        const volume = layerMult * comp * Math.sqrt(massA * massB) / (distRad ** 2);
        const netBenefit = volume * (1 - effMarkup) * 0.003;
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
      const ct = tech[core];
      let ratio, surplus, indDef;

      if (ct >= 7.0) {
        const eDemand = tp * ct * 0.002;
        const eSupply = coreC[core] * 0.2;
        ratio = _clamp(eSupply / Math.max(0.001, eDemand), 0.3, 1.5);
        surplus = Math.max(0, eSupply - eDemand) * 0.2 + tp * 0.01;
        indDef = eSupply < eDemand;
      } else {
        const cropY = substrate[core].crops.primary_yield;
        const avgHC = substrate[core].climate.avg_h ?? 0.2;
        const landFactor = Math.max(0.3, 1.0 - avgHC * 0.35);
        let fishPol = 0;
        for (let j = 0; j < N; j++) {
          if (controller[j] === core) {
            fishPol += (substrate[j].climate.fish_y ?? 0) * (substrate[j].climate.coast_factor ?? 0);
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
      nucDeficit[core] = ct >= 9.0 && !hasPu(core);
    }

    // ── STAGE 2: Political allocation ───────────────────────
    const expBudget = {};
    const techBgt = {};
    const consolBudget = {};
    const maxSurplus = Math.max(...Object.values(energySurplus), 1.0);

    for (const core of cores) {
      let [expS, tecS, conS] = sharesFromPos(cpos[core]);

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
          t = expS + tecS + conS;
          expS /= t; tecS /= t; conS /= t;
          desperationLog.push({ core, tick, year, resource_pressure: rp,
            food_deficit: foodDeficit[core], ind_deficit: indDeficit[core], nuc_deficit: nucDeficit[core] });
        }

        t = expS + tecS + conS;
        expS /= t; tecS /= t; conS /= t;
      }

      const budgetMult = rp > 0.3 ? 1.0 + _clamp(rp - 0.3, 0, 0.7) * 0.8 : 1.0;
      const budget = (energySurplus[core] + corePop[core] * 0.002) * budgetMult;
      expBudget[core] = budget * expS;
      techBgt[core] = budget * tecS;
      consolBudget[core] = budget * conS;
    }

    // ── STAGE 2b: Culture-space drift ───────────────────────
    for (const core of cores) {
      let [ci, io] = cpos[core];
      const [, tecS, conS] = sharesFromPos(cpos[core]);
      const er = energyRatio[core];

      ci += _clamp(er / 1.5, 0, 1) * (1 - conS) * p.culture_drift_rate;
      const threatLevel = _clamp(1.0 - er, 0, 1);
      ci -= threatLevel * p.culture_drift_rate;

      const tradeInt = Math.min(1.0, contactSet[core].size / Math.max(1, N * 0.3));
      io += tecS * tradeInt * p.culture_drift_rate;
      io -= _clamp(1.0 - er, 0, 1) * p.culture_drift_rate * 0.5;

      // Fisheries drift
      const fishR = substrate[core].climate.fisheries_richness ?? 0;
      if (fishR > 0.05) {
        const mt = substrate[core].climate.mean_temp ?? 18;
        const up = substrate[core].climate.upwelling ?? 0;
        const fdr = p.culture_drift_rate * fishR * 0.3;
        if (mt < 14) { ci -= fdr * 0.6; io -= fdr * 0.2; }
        if (up > 0.3) io += fdr * 0.8;
        if (mt > 20) { ci += fdr * 0.4; io += fdr * 0.4; }
        ci -= fdr * 0.1;
      }

      cpos[core] = [_clamp(ci, -1, 1), _clamp(io, -1, 1)];
    }

    // ── STAGE 3: Rumor propagation ──────────────────────────
    for (const core of cores) {
      if (tech[core] < 1.0) continue;
      const ctrlSet = new Set(controlled(core));
      let newThisTick = 0;
      // Contact discovery rate grows continuously with tech rather than stepping at 5.0
      const maxNew = Math.max(1, Math.floor(tech[core] / 4));
      outer: for (const j of ctrlSet) {
        if (newThisTick >= maxNew) break;
        for (const nb of adj[j]) {
          if (!ctrlSet.has(nb)) {
            const otherCore = controller[nb];
            if (otherCore !== core && !contactSet[core].has(otherCore)) {
              contactSet[core].add(otherCore);
              contactSet[otherCore].add(core);
              newThisTick++;
              if (newThisTick >= maxNew) break outer;
            }
          }
        }
      }

      if (tech[core] >= 7.0) {
        const signalR = p.df_detection_range * (tech[core] / 10.0);
        for (const other of cores) {
          if (other === core) continue;
          const dist = _gcDistArch(archs[core], archs[other]);
          if (dist <= signalR) {
            const keyOC = `${other},${core}`;
            const keyCO = `${core},${other}`;
            awareness.set(keyOC, Math.min(1, (awareness.get(keyOC) || 0) + 0.15));
            awareness.set(keyCO, Math.min(1, (awareness.get(keyCO) || 0) + 0.10));
          }
        }
      }
    }

    // ── STAGE 4: Dark Forest detection ──────────────────────
    if (dfYear === null) {
      for (const core of cores) {
        if (tech[core] < 9.0) continue;
        for (const other of cores) {
          if (other === core || tech[other] < 8.0) continue;
          const aw = awareness.get(`${core},${other}`) || 0;
          const minArchs = Math.max(1, Math.floor(p.df_min_territory_frac * N));
          if (coreNCtrl[core] < minArchs || coreNCtrl[other] < minArchs) continue;
          const dist = _gcDistArch(archs[core], archs[other]);
          if (dist <= p.df_detection_range * 1.5 && aw > 0.2) {
            dfYear = year;
            dfArch = core;
            dfDetector = other;
            awareness.set(`${core},${other}`, 1.0);
            awareness.set(`${other},${core}`, 1.0);
            break;
          }
        }
        if (dfYear !== null) break;
      }
    }

    // ── STAGE 5: Tech growth + decay + population ───────────
    for (const core of cores) {
      const a0 = A0FromPos(cpos[core]);
      const nc = contactSet[core].size;
      const er = tech[core] >= 9.0 && !hasPu(core)
        ? energyRatio[core] * p.pu_dependent_factor
        : energyRatio[core];
      const cropY = substrate[core].crops.primary_yield;

      const effNc = Math.min(nc, Math.floor(tech[core] * 2) + 1);
      const contactMult = 1.0 + _log2(effNc + 1) * 0.3;
      const energyMult = er * p.energy_to_tfp;
      const shareMult = sharesFromPos(cpos[core])[1] / 0.3;

      const cropExp = cropY ** 0.3;
      const baseFloor = cropExp * 0.003;

      let accelRate;
      const t = tech[core];
      if (t < 1.5) accelRate = 0;
      else if (t < 3.0) accelRate = 0.002;
      else if (t < 5.0) accelRate = 0.008;
      else if (t < 7.0) accelRate = 0.025;
      else accelRate = 0.120;

      const accel = a0 * cropExp * shareMult * accelRate * contactMult * energyMult;
      let delta = baseFloor + accel;
      if (t > 9.0) delta *= _clamp((11.0 - t) / 2.0, 0, 1);
      tech[core] += delta;

      // Tech decay
      const maintenanceCost = tech[core] * tech[core] * p.maintenance_rate;
      const availE = energySurplus[core];
      if (availE < maintenanceCost) {
        const shortfall = maintenanceCost - availE;
        const decayAmt = shortfall * p.decay_rate;
        const oldT = tech[core];
        tech[core] = Math.max(0.1, tech[core] - decayAmt);
        if (decayAmt > 0.005) {
          techDecayLog.push({ core, tick, year, tech_before: oldT, tech_after: tech[core], decay: decayAmt });
        }
      }

      knowledge[core] += delta * a0 * 0.5;

      // Population
      for (let j = 0; j < N; j++) {
        if (controller[j] !== core) continue;
        let cap = carryCap[j];
        if (tech[core] >= 7.0 && cRemaining[j] > 0) cap *= (1.0 + er * 0.5);
        if (tech[core] >= 9.0) cap *= 1.5;
        const growthRate = 0.03 * er * (1.0 - pop[j] / Math.max(1, cap));
        pop[j] *= (1.0 + _clamp(growthRate, -0.05, 0.10));
        pop[j] = Math.max(1.0, pop[j]);
      }

      // Propagate tech to periphery
      for (let j = 0; j < N; j++) {
        if (controller[j] === core && j !== core) tech[j] = Math.max(tech[j], tech[core] * 0.7);
      }
    }

    // Knowledge diffusion
    const worldMaxTech = Math.max(...cores.map(c => tech[c]));
    for (const core of cores) {
      let maxContactTech = 0;
      for (const c of contactSet[core]) {
        if (coresSet.has(c) && tech[c] > maxContactTech) maxContactTech = tech[c];
      }
      if (maxContactTech > tech[core] + 1.0) tech[core] += (maxContactTech - tech[core]) * 0.08;
      if (worldMaxTech > tech[core] + 1.0) tech[core] += (worldMaxTech - tech[core]) * 0.03;
    }

    // ── STAGE 6: Thompson Sampling expansion ────────────────
    for (const core of cores) {
      let budget = expBudget[core] || 0;
      if (budget < 0.1) continue;

      const [tsA, tsB] = tsPriorsFromPos(cpos[core]);
      const ctrlSet = new Set(controlled(core));
      const frontier = new Set();
      for (const j of ctrlSet) {
        for (const nb of adj[j]) {
          if (!ctrlSet.has(nb)) frontier.add(nb);
        }
      }
      if (frontier.size === 0) continue;

      const candidates = [];
      for (const target of frontier) {
        let dist = _gcDistArch(archs[core], archs[target]);
        const tsScore = _betaSample(rng, tsA, tsB);
        const rv = _resourceValue(substrate[target].minerals, tech[core], p.cu_unlock_tech);

        if (tech[core] >= 7.0 && (substrate[target].minerals.C || 0) > 0 && scrambleOnset === null)
          scrambleOnset = tick;
        if (tech[core] >= 9.0 && substrate[target].minerals.Pu && puScrambleOnset === null)
          puScrambleOnset = tick;

        let despBonus = 0;
        const rp = resourcePressure[core] || 0;
        if (rp > 0) {
          const tMins = substrate[target].minerals;
          const tCrops = substrate[target].crops;
          const tClim = substrate[target].climate;
          if (foodDeficit[core]) despBonus += rp * ((tCrops.primary_yield || 0) * 1.5 + (tClim.fisheries_richness || 0) * 2.5);
          if (indDeficit[core]) despBonus += rp * (tMins.C || 0) * 4.0;
          if (nucDeficit[core] && tMins.Pu) despBonus += rp * 6.0;
          if (rp > 0.3) dist *= _clamp(1.0 - (rp - 0.3) * 0.5, 0.5, 1.0);
        }

        candidates.push([tsScore + p.resource_targeting_weight * rv + despBonus - dist * 1.5, target, dist, rv]);
      }
      candidates.sort((a, b) => b[0] - a[0]);

      let absorbedThisTick = 0;
      for (const [score, target, dist, rv] of candidates) {
        if (budget < 0.1 || absorbedThisTick >= 1) break;

        const techAdv = Math.max(0.1, tech[core] - tech[target] + 1.0);
        let cost = (pop[target] * 0.05 + dist ** 3 * 40) / (techAdv ** 1.5);

        const targetCore = controller[target];
        if (targetCore !== target) {
          cost *= 3.0;
          if (tech[core] - tech[targetCore] < 2.0) continue;
        }
        if (cost > budget) continue;
        if (pop[target] > corePop[core] * 0.5 && tech[core] - tech[target] < 2.0) continue;

        // Epidemic shock
        if (firstContactTick[target] === null) {
          firstContactTick[target] = tick;
          const cc = substrate[core].crops.primary_crop;
          const ct = substrate[target].crops.primary_crop;
          const cdist = _cropDistance(cc, ct);
          const sev = p.epi_base_severity + rng() * 0.15;
          const mort = sev * cdist;
          pop[target] *= (1 - mort);
          epiLog.push({ arch: target, contactor: core, mortality_rate: mort, tick, year });
        }

        // Transfer
        for (let j = 0; j < N; j++) {
          if (controller[j] === target) controller[j] = core;
        }
        controller[target] = core;
        absorbedTick[target] = tick;
        absorbedTech[target] = tech[core];
        sovereignty[target] = _clamp(0.15 + dist * 0.3, 0.10, 0.50);
        budget -= cost;
        absorbedThisTick++;

        for (const c of contactSet[target]) {
          if (c !== core) contactSet[core].add(c);
        }
        cpos[core][0] = _clamp(cpos[core][0] * 0.95 + cpos[target][0] * 0.05, -1, 1);
        cpos[core][1] = _clamp(cpos[core][1] * 0.95 + cpos[target][1] * 0.05, -1, 1);

        expansionLog.push({ core, target, tick, year, tech_gap: tech[core] - tech[target], resource_driven: rv > 0 });
      }
    }

    // ── STAGE 7: Sovereignty drift ──────────────────────────
    for (let i = 0; i < N; i++) {
      if (controller[i] === i) continue;
      const core = controller[i];
      const dist = _gcDistArch(archs[core], archs[i]);
      const extraction = p.sov_extraction_decay / Math.max(0.1, dist) * _clamp(energyRatio[core] ?? 1, 0, 1.5);
      const recovery = p.sov_extraction_decay * sovereignty[i] * (pop[i] / Math.max(1, pop[core])) * 0.5;
      sovereignty[i] += (recovery - extraction) * 0.1;
      sovereignty[i] = _clamp(sovereignty[i], 0.05, 0.95);
      // Nuclear-era hegemonic consolidation: year gate removed — tech level alone
      // determines when this applies, so fast and slow seeds both experience it.
      if (tech[core] >= 9.0) sovereignty[i] = Math.min(0.80, sovereignty[i] + 0.015);
    }

    // ── STAGE 8: Naphtha depletion ──────────────────────────
    for (let i = 0; i < N; i++) {
      const core = controller[i];
      if (tech[core] >= 7.0 && cRemaining[i] > 0) {
        const extraction = pop[i] * tech[core] * p.naphtha_depletion * 0.0005;
        cRemaining[i] = Math.max(0, cRemaining[i] - extraction);
      }
    }

    // Era snapshots keyed to tech-threshold crossings, not fixed calendar years.
    // Each snapshot fires the first time any core reaches the threshold — so the
    // snapshot always captures a meaningful transition regardless of seed pacing.
    const maxCoreTech = cores.length > 0 ? Math.max(...cores.map(c => tech[c])) : 0;
    if (!techSnapshots.after_antiquity && maxCoreTech >= 3.0) {
      techSnapshots.after_antiquity = [...tech]; popSnapshots.after_antiquity = [...pop];
    }
    if (!techSnapshots.after_serial && maxCoreTech >= 5.0) {
      techSnapshots.after_serial = [...tech]; popSnapshots.after_serial = [...pop];
    }
    if (!techSnapshots.after_colonial && maxCoreTech >= 7.0) {
      techSnapshots.after_colonial = [...tech]; popSnapshots.after_colonial = [...pop];
    }
    if (!techSnapshots.after_industrial && maxCoreTech >= 9.0) {
      techSnapshots.after_industrial = [...tech]; popSnapshots.after_industrial = [...pop];
    }

    // Timeline snapshot (for future slider)
    if (tick % 4 === 0) { // Every 200 years
      timeline.push({
        year,
        controller: [...controller],
        tech: Array.from(tech, t => Math.round(t * 10) / 10),
        pop: Array.from(pop, p => Math.round(p)),
      });
    }
  }

  // ── POST-SIM ──────────────────────────────────────────────
  const finalCores = [...new Set(controller)].sort((a, b) => a - b);
  for (const core of finalCores) {
    if (tech[core] >= 9.0) {
      if (hasPu(core)) { fleetScale[core] = 1.0; sovereignty[core] = Math.min(1, sovereignty[core] + 0.1); }
      else { fleetScale[core] = p.pu_dependent_factor; sovereignty[core] = Math.max(0.3, sovereignty[core] - 0.05); }
    }
  }

  const totalWorldPop = pop.reduce((s, v) => s + v, 0);
  const polityPops = {};
  for (const c of finalCores) {
    let pp = 0;
    for (let j = 0; j < N; j++) if (controller[j] === c) pp += pop[j];
    polityPops[c] = pp;
  }

  const hegemons = finalCores
    .filter(c => polityPops[c] > totalWorldPop * 0.09)
    .sort((a, b) => polityPops[b] - polityPops[a]);
  const hegemonCultures = {};
  for (const c of hegemons) hegemonCultures[c] = _cultureLabelFromPos(cpos[c]);

  const maxPop = Math.max(...pop);

  // Build states
  const states = [];
  for (let i = 0; i < N; i++) {
    const core = controller[i];
    let faction, status;
    if (core === i && hegemons.includes(i)) {
      faction = _cultureLabelFromPos(cpos[i]);
      status = "core";
    } else if (hegemons.includes(core)) {
      faction = _cultureLabelFromPos(cpos[core]);
      if (sovereignty[i] < 0.3) status = "colony";
      else if (sovereignty[i] < 0.6) status = _cultureLabelFromPos(cpos[core]) === "subject" ? "garrison" : "client";
      else status = "contacted";
    } else if (controller[i] === i) {
      faction = "independent";
      status = absorbedTick[i] === null ? "uncontacted" : "independent";
    } else {
      faction = _cultureLabelFromPos(cpos[core]);
      status = "tributary";
    }

    // Era-of-contact labelled by the absorbing polity's tech level at the moment
    // of absorption, not by calendar year — so the label reflects what kind of
    // civilisation did the absorbing, regardless of seed pacing.
    let era = null;
    if (absorbedTick[i] !== null) {
      const at = absorbedTech[i] ?? 1.0;
      if (at < 3.0)      era = "stone";
      else if (at < 5.0) era = "sail";
      else if (at < 7.0) era = "colonial";
      else if (at < 9.0) era = "industrial";
      else               era = "nuclear";
    }

    states.push({
      faction, status,
      name: `arch_${i}`,
      population: Math.round(pop[i]),
      urbanization: maxPop > 0 ? pop[i] / maxPop : 0,
      tech: Math.round(tech[i] * 10) / 10,
      sovereignty: Math.round(sovereignty[i] * 1000) / 1000,
      tradeIntegration: Math.min(1, contactSet[i].size / Math.max(1, N * 0.3)),
      eraOfContact: era,
      hopCount: 0,
      culture: _cultureLabelFromPos(cpos[controller[i]]),
      culture_pos: [...cpos[controller[i]]],
      fleet_scale: fleetScale[i],
      c_remaining: cRemaining[i],
      controller: controller[i],
    });
  }

  // Backward-compat faction labels
  let reachArch = null, latticeArch = null;
  for (const h of hegemons) {
    const label = _cultureLabelFromPos(cpos[h]);
    if (label === "civic" && reachArch === null) reachArch = h;
    else if (label === "subject" && latticeArch === null) latticeArch = h;
  }
  if (reachArch === null && hegemons.length > 0) reachArch = hegemons[0];
  if (latticeArch === null && hegemons.length >= 2) latticeArch = hegemons[1];
  else if (latticeArch === null) latticeArch = reachArch ?? 0;

  for (let i = 0; i < N; i++) {
    const core = controller[i];
    if (core === reachArch || i === reachArch) states[i].faction = "reach";
    else if (core === latticeArch || i === latticeArch) states[i].faction = "lattice";
    else if (states[i].faction === "independent") states[i].faction = "unknown";
  }

  const totalCInit = cInitial.reduce((s, v) => s + v, 0);
  const totalCRem = cRemaining.reduce((s, v) => s + v, 0);

  return {
    states, log: expansionLog,
    df_year: dfYear, df_arch: dfArch, df_detector: dfDetector,
    reach_arch: reachArch ?? 0, lattice_arch: latticeArch ?? 0,
    epi_log: epiLog, substrate,
    hegemons, hegemon_cultures: hegemonCultures,
    hegemon_culture_pos: Object.fromEntries(hegemons.map(c => [c, [...cpos[c]]])),
    tech_snapshots: techSnapshots, pop_snapshots: popSnapshots,
    tech_decay_log: techDecayLog, desperation_log: desperationLog,
    scramble_onset_tick: scrambleOnset, pu_scramble_onset_tick: puScrambleOnset,
    c_depletion_frac: totalCInit > 0 ? 1 - totalCRem / totalCInit : 0,
    polity_pops: polityPops,
    n_polities: finalCores.length,
    uncontacted_count: Array.from({ length: N }, (_, i) => i)
      .filter(i => controller[i] === i && !hegemons.includes(i) && absorbedTick[i] === null).length,
    timeline,
  };
}
