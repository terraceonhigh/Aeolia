// ═══════════════════════════════════════════════════════════
// substrate.js — Port of sim_proxy_v2.py _compute_substrate()
// Climate → crops → trade goods → minerals → culture position
// ═══════════════════════════════════════════════════════════

import { mulberry32 } from './rng.js';

const _ISLAND_MAX_HEIGHT = 3000.0;

const _CROP_CULTURE_SEED = {
  emmer:    [ 0.45,  0.55],
  nori:     [ 0.35,  0.65],
  paddi:    [-0.55, -0.20],
  taro:     [-0.10,  0.05],
  sago:     [-0.20, -0.10],
  papa:     [ 0.15,  0.15],
  foraging: [ 0.00,  0.00],
};

function _clamp(x, lo, hi) { return Math.max(lo, Math.min(hi, x)); }

function _cultureLabelFromPos(pos) {
  const [ci, io] = pos;
  if (ci > 0.3 && io > 0.3) return "civic";
  if (ci < -0.3 && io < 0.0) return "subject";
  return "parochial";
}

function _computeGyrePosition(arch, allArchs) {
  const cy = _clamp(arch.cy, -1, 1);
  const lat = Math.asin(cy) * 180 / Math.PI;
  const absLat = Math.abs(lat);
  const bandArchs = allArchs.filter(a => {
    const aLat = Math.abs(Math.asin(_clamp(a.cy, -1, 1)) * 180 / Math.PI);
    return Math.abs(aLat - absLat) < 15;
  });
  if (bandArchs.length < 2) return 0.5;
  const lons = bandArchs.map(a => Math.atan2(a.cz, a.cx) * 180 / Math.PI).sort((a, b) => a - b);
  let maxGap = 0, gapCenter = 0;
  for (let j = 0; j < lons.length; j++) {
    let nextLon = lons[(j + 1) % lons.length];
    if (j === lons.length - 1) nextLon += 360;
    const gap = nextLon - lons[j];
    if (gap > maxGap) { maxGap = gap; gapCenter = lons[j] + gap / 2; }
  }
  if (maxGap < 10) return 0.5;
  const myLon = Math.atan2(arch.cz, arch.cx) * 180 / Math.PI;
  return _clamp(((myLon - gapCenter + 540) % 360) / 360, 0, 1);
}

export function computeSubstrate(archs, plateauEdges, seed, naphthaRichness = 2.0) {
  const rng = mulberry32(((seed > 0 ? seed : 42) * 47 + 2024) | 0);
  const N = archs.length;

  const edgeCount = new Array(N).fill(0);
  const edgeLengths = Array.from({ length: N }, () => []);
  for (const edge of plateauEdges) {
    const a = edge[0], b = edge[1];
    edgeCount[a]++; edgeCount[b]++;
    const dot = _clamp(archs[a].cx * archs[b].cx + archs[a].cy * archs[b].cy + archs[a].cz * archs[b].cz, -1, 1);
    const ang = Math.acos(dot);
    edgeLengths[a].push(ang);
    edgeLengths[b].push(ang);
  }

  const substrates = [];
  for (let i = 0; i < N; i++) {
    const arch = archs[i];
    const cy = _clamp(arch.cy, -1, 1);
    const lat = Math.asin(cy) * 180 / Math.PI;
    const absLat = Math.abs(lat);
    const shelfR = arch.shelfR ?? arch.shelf_r ?? 0.06;
    const size = shelfR / 0.12;

    const peaks = arch.peaks || [];
    const peakCount = peaks.length;
    const avgH = peakCount > 0
      ? peaks.reduce((s, pk) => s + pk.h, 0) / (peakCount * _ISLAND_MAX_HEIGHT)
      : (arch.avg_h ?? 0.0);

    // Wind belt
    let windBelt;
    if (absLat < 12) windBelt = "doldrums";
    else if (absLat < 28) windBelt = "trades";
    else if (absLat < 35) windBelt = "subtropical";
    else if (absLat < 55) windBelt = "westerlies";
    else if (absLat < 65) windBelt = "subpolar";
    else windBelt = "polar";

    const baseRainMap = { doldrums: 2800, trades: 2200, subtropical: 600, westerlies: 1400, subpolar: 1100, polar: 300 };
    const baseRain = baseRainMap[windBelt];
    const orographicBonus = 1.0 + avgH * 1.8;
    const gyrePos = _computeGyrePosition(arch, archs);

    let oceanWarmth;
    if (gyrePos < 0.3) oceanWarmth = 0.8 + gyrePos;
    else if (gyrePos > 0.7) oceanWarmth = 0.3 - (gyrePos - 0.7);
    else oceanWarmth = 0.4 + gyrePos * 0.2;
    oceanWarmth = _clamp(oceanWarmth, 0, 1);

    const moistureBonus = 1.0 + Math.max(0, oceanWarmth - 0.4) * 0.4;
    const effectiveRainfall = baseRain * orographicBonus * moistureBonus * 1.4;
    const meanTemp = 28.0 - absLat * 0.45 + (oceanWarmth - 0.5) * 4.0;
    const seasonalRange = absLat * 0.15 * 0.7;

    const nearby = archs.filter((other, idx) => idx !== i &&
      arch.cx * other.cx + arch.cy * other.cy + arch.cz * other.cz > 0.95).length;
    const clusterDensity = Math.min(1.0, nearby / 5.0);
    const absLatRad = absLat * Math.PI / 180;
    const tidalRange = (2.0 + shelfR * 30.0 + clusterDensity * 4.0) * (0.8 + Math.abs(Math.sin(absLatRad)) * 0.4);

    let upwelling = 0;
    if (gyrePos > 0.7) upwelling += 0.4;
    if (absLat < 5) upwelling += 0.3;
    upwelling += edgeCount[i] * 0.08;
    const fisheries = Math.min(1.0, upwelling * 0.5 + effectiveRainfall * 0.0001 + edgeCount[i] * 0.05);

    const coastFactor = Math.min(1.0, edgeCount[i] * 0.18 + Math.min(1.0, upwelling) * 0.25);

    let fishBase;
    if (absLat > 38) fishBase = 2.0 + upwelling;
    else if (absLat > 22) fishBase = 1.6 + upwelling * 0.8;
    else if (absLat > 10) fishBase = 1.2 + upwelling * 0.6;
    else fishBase = 1.0 + upwelling * 0.4;
    const fishY = coastFactor * fishBase;

    let climateZone;
    if (meanTemp > 24 && effectiveRainfall > 2000) climateZone = "tropical_wet";
    else if (meanTemp > 24 && effectiveRainfall < 1000) climateZone = "tropical_dry";
    else if (meanTemp > 10 && effectiveRainfall > 1200) climateZone = "temperate_wet";
    else if (meanTemp > 10) climateZone = "temperate_dry";
    else if (meanTemp > 2) climateZone = "subpolar";
    else climateZone = "polar_fringe";

    // Crop viability
    const canGrow = {
      paddi: meanTemp >= 20 && effectiveRainfall >= 1200 && tidalRange >= 2.0 && shelfR >= 0.08 && absLat <= 28,
      emmer: meanTemp >= 8 && meanTemp <= 24 && effectiveRainfall >= 400 && effectiveRainfall <= 2000 && absLat >= 20 && absLat <= 55,
      taro:  meanTemp >= 21 && seasonalRange <= 4 && effectiveRainfall >= 1500 && absLat <= 20,
      nori:  meanTemp >= 5 && meanTemp <= 22 && edgeCount[i] >= 1 && upwelling >= 0.2,
      sago:  meanTemp >= 24 && effectiveRainfall >= 2000 && absLat <= 15 && shelfR >= 0.04,
      papa:  meanTemp >= 2 && meanTemp <= 18 && effectiveRainfall >= 400 && absLat >= 35,
    };

    const yields = {};
    if (canGrow.paddi)
      yields.paddi = 5.0 * Math.min(1, (meanTemp - 18) / 15) * Math.min(1, effectiveRainfall / 1800) * Math.min(1, tidalRange / 5);
    if (canGrow.emmer)
      yields.emmer = 2.5 * (1 - Math.abs(meanTemp - 16) / 20) * (1 - Math.abs(effectiveRainfall - 700) / 1500);
    if (canGrow.taro)
      yields.taro = 3.0 * Math.min(1, (meanTemp - 20) / 8) * Math.min(1, effectiveRainfall / 2000);
    if (canGrow.nori)
      yields.nori = 1.5 * Math.min(1, upwelling * 2) * Math.min(1, edgeCount[i] / 3) * 2;
    if (canGrow.sago)
      yields.sago = 4.0 * Math.min(1, effectiveRainfall / 2500) * Math.min(1, shelfR / 0.10);
    if (canGrow.papa)
      yields.papa = 3.5 * (1 - Math.abs(meanTemp - 12) / 15) * Math.min(1, effectiveRainfall / 600);

    const cropEntries = Object.entries(yields).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    const primaryCrop = cropEntries.length > 0 ? cropEntries[0][0] : "foraging";
    const primaryYield = cropEntries.length > 0 ? cropEntries[0][1] : 0.5;
    const secondaryCrop = cropEntries.length > 1 ? cropEntries[1][0] : null;

    // Trade goods — RNG consumption order must match Python
    const stimMap = { paddi: "char", emmer: "qahwa", taro: "awa", sago: "pinang", papa: "aqua", nori: "", foraging: "" };
    const fiberMap = { paddi: "seric", emmer: "fell", taro: "tapa", sago: "tapa", nori: "byssus", papa: "qivu", foraging: "" };
    const protMap = { paddi: "kerbau", emmer: "kri", taro: "moa", sago: "moa", nori: "", papa: "", foraging: "" };
    const stimType = stimMap[primaryCrop] || "";
    const fiberType = fiberMap[primaryCrop] || "";
    const protType = protMap[primaryCrop] || "";
    const stimProd = stimType ? (0.3 + rng() * 0.5) : 0.0;
    const fiberProd = fiberType ? (0.3 + rng() * 0.5) : 0.0;
    const protProd = protType ? (0.3 + rng() * 0.4) : 0.0;
    let noriExport = 0;
    if (primaryCrop === "nori") noriExport = 0.6 + rng() * 0.3;
    else if (canGrow.nori) noriExport = 0.1 + rng() * 0.2;
    const totalTradeValue = stimProd * 0.4 + fiberProd * 0.3 + protProd * 0.2 + noriExport * 0.3;

    // Minerals
    const minerals = {
      Fe: true,
      Cu: rng() < 0.20,
      Au: rng() < (0.05 + avgH * 0.08),
      Pu: rng() < (0.03 + size * 0.02),
      C: shelfR >= 0.04 ? shelfR * tidalRange * naphthaRichness : 0.0,
    };

    // Continuous culture-space initial position
    const [ciSeed, ioSeed] = _CROP_CULTURE_SEED[primaryCrop] || [0, 0];
    const ciGeo = -size * 0.25 + avgH * 0.20;
    let ioGeo = Math.min(1.0, nearby / 5.0) * 0.25;
    ioGeo += Math.min(1.0, shelfR / 0.12) * 0.15;
    ioGeo -= (1.0 - Math.min(1.0, nearby / 3.0)) * 0.15;
    ioGeo += primaryYield * 0.08;

    const ciInit = _clamp(ciSeed + ciGeo + (rng() - 0.5) * 0.30, -1, 1);
    const ioInit = _clamp(ioSeed + ioGeo + (rng() - 0.5) * 0.30, -1, 1);
    const culturePos = [ciInit, ioInit];

    substrates.push({
      climate: {
        latitude: lat, abs_latitude: absLat,
        wind_belt: windBelt, mean_temp: meanTemp,
        seasonal_range: seasonalRange,
        effective_rainfall: effectiveRainfall,
        tidal_range: tidalRange, ocean_warmth: oceanWarmth,
        gyre_position: gyrePos, upwelling,
        fisheries_richness: fisheries, climate_zone: climateZone,
        coast_factor: coastFactor, fish_y: fishY, avg_h: avgH,
      },
      crops: {
        primary_crop: primaryCrop, secondary_crop: secondaryCrop,
        primary_yield: primaryYield,
        can_grow: canGrow,
      },
      trade_goods: {
        total_trade_value: totalTradeValue,
        stimulant: stimType || null, stimulant_prod: stimProd,
        fiber: fiberType || null, fiber_prod: fiberProd,
        protein: protType || null, protein_prod: protProd,
        nori_export: noriExport,
        stimulant_deficit: stimType === "" && stimProd === 0.0,
      },
      minerals,
      culture_pos: culturePos,
      culture: _cultureLabelFromPos(culturePos),
    });
  }
  // Crop distribution is now fully emergent from geography.
  // Which crops appear (and how many) varies by seed — that is information,
  // not a defect. Loss function terms in loss.py capture crop diversity as
  // a soft optimisation target rather than a hard override.

  return substrates;
}
