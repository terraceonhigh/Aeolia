// ═══════════════════════════════════════════════════════════
// world.js — World generation from seed
// Produces the physical geography: archipelagos, plateau edges,
// Reach/Lattice selection. Pure data, no rendering.
// ═══════════════════════════════════════════════════════════

import { mulberry32 } from './rng.js';
import { ARCH_COUNT, ISLAND_MAX_HEIGHT, MAX_EDGE_ANGLE, MIN_NEIGHBORS } from './constants.js';
import { computeSubstrate } from './substrate.js';
import { assignPolitics } from './history.js';
import { detectSettlements } from './settlements.js';
export { computeSubstrate, assignPolitics, detectSettlements };

function latLonToXYZ(lat, lon) {
  const p = (90 - lat) * Math.PI / 180, t = (lon + 180) * Math.PI / 180;
  return [Math.sin(p) * Math.cos(t), Math.cos(p), Math.sin(p) * Math.sin(t)];
}

export function buildWorld(seed) {
  const rng = mulberry32(seed || 42);

  // ── Generate archipelagos via Fibonacci spiral + jitter ──
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  const archSpecs = [];
  for (let k = 0; k < ARCH_COUNT; k++) {
    const y = 1 - (2 * (k + 0.5)) / ARCH_COUNT;
    const radius = Math.sqrt(1 - y * y);
    const theta = goldenAngle * k;
    const baseLat = Math.asin(y) * 180 / Math.PI;
    const baseLon = (theta * 180 / Math.PI) % 360 - 180;
    const jLat = Math.max(-75, Math.min(75, baseLat + (rng() - 0.5) * 24));
    const jLon = baseLon + (rng() - 0.5) * 24;

    const sizeRoll = rng();
    const size = sizeRoll < 0.15 ? 1.3 + rng() * 0.9 :
                 sizeRoll < 0.40 ? 0.7 + rng() * 0.6 :
                 0.25 + rng() * 0.45;
    const n = Math.max(2, Math.round(size * (3 + rng() * 5)));
    archSpecs.push({ lat: jLat, lon: jLon, size, n });
  }

  // ── Build arch objects with peaks ──
  const archs = archSpecs.map(a => {
    const [cx, cy, cz] = latLonToXYZ(a.lat, a.lon);
    let rx = -cz, ry = 0, rz = cx;
    const rl = Math.sqrt(rx * rx + rz * rz) || 1; rx /= rl; rz /= rl;
    const fx = cy * rz, fy = cz * rx - cx * rz, fz = -cy * rx;
    const peaks = [];
    for (let i = 0; i < a.n; i++) {
      const ang = rng() * 6.283, dist = (0.2 + rng() * 0.8) * a.size * 0.12;
      const ca = Math.cos(ang), sa = Math.sin(ang);
      let px = cx + dist * (ca * rx + sa * fx);
      let py = cy + dist * (ca * ry + sa * fy);
      let pz = cz + dist * (ca * rz + sa * fz);
      const pl = Math.sqrt(px * px + py * py + pz * pz); px /= pl; py /= pl; pz /= pl;
      const w = 0.005 + rng() * 0.008 * a.size;
      const rawH = ISLAND_MAX_HEIGHT * (0.4 + rng() * 0.6) * (a.size / 1.5);
      peaks.push({ px, py, pz, h: Math.min(ISLAND_MAX_HEIGHT, rawH), w, w2inv: 3.0 / (w * w) });
    }
    return { cx, cy, cz, peaks, shelfR: a.size * 0.12 };
  });

  // ── Find most-antipodal pair → Reach (north) & Lattice (south) ──
  let reachArch = 0, latticeArch = 1;
  let bestDot = 2;
  for (let i = 0; i < archs.length; i++) {
    for (let j = i + 1; j < archs.length; j++) {
      const d = archs[i].cx * archs[j].cx + archs[i].cy * archs[j].cy + archs[i].cz * archs[j].cz;
      if (d < bestDot) { bestDot = d; reachArch = i; latticeArch = j; }
    }
  }
  // Reach is whichever of the antipodal pair is further north — no geographic override.
  // The antipodal selection already gives them maximally contrasting positions; peak
  // geometry is left to the seed's own RNG so it can vary across worlds.
  if (archs[reachArch].cy < archs[latticeArch].cy) {
    [reachArch, latticeArch] = [latticeArch, reachArch];
  }

  // ── Generate plateau edge network from proximity ──
  const pairDists = [];
  for (let i = 0; i < archs.length; i++) {
    for (let j = i + 1; j < archs.length; j++) {
      const d = archs[i].cx * archs[j].cx + archs[i].cy * archs[j].cy + archs[i].cz * archs[j].cz;
      pairDists.push({ i, j, angle: Math.acos(Math.max(-1, Math.min(1, d))) });
    }
  }
  pairDists.sort((a, b) => a.angle - b.angle);
  const edgeSet = new Set();
  const connCount = new Array(archs.length).fill(0);
  const plateauEdges = [];
  function addEdge(i, j) {
    const key = Math.min(i, j) + "-" + Math.max(i, j);
    if (edgeSet.has(key)) return;
    edgeSet.add(key); plateauEdges.push([i, j]);
    connCount[i]++; connCount[j]++;
  }
  for (const { i, j } of pairDists) {
    if (connCount[i] < MIN_NEIGHBORS || connCount[j] < MIN_NEIGHBORS) addEdge(i, j);
  }
  for (const { i, j, angle } of pairDists) {
    if (angle < MAX_EDGE_ANGLE) addEdge(i, j);
  }

  // ── Edge geometry (for terrain rendering) ──
  const edges = plateauEdges.map(([ai, bi]) => {
    const a = archs[ai], b = archs[bi];
    let nx = a.cy * b.cz - a.cz * b.cy;
    let ny = a.cz * b.cx - a.cx * b.cz;
    let nz = a.cx * b.cy - a.cy * b.cx;
    const nl = Math.sqrt(nx * nx + ny * ny + nz * nz) || 1;
    nx /= nl; ny /= nl; nz /= nl;
    const w = 0.14 + mulberry32(ai * 1000 + bi)() * 0.12;
    return {
      ax: a.cx, ay: a.cy, az: a.cz,
      bx: b.cx, by: b.cy, bz: b.cz,
      nx, ny, nz,
      dotAB: a.cx * b.cx + a.cy * b.cy + a.cz * b.cz,
      w
    };
  });

  // ── Compute all layers ──
  const substrate = computeSubstrate(archs, plateauEdges, seed);
  const history = assignPolitics(archs, plateauEdges, seed, reachArch, latticeArch);
  const settlements = detectSettlements(archs, history.states);

  return {
    archs, edges, plateauEdges,
    substrate, history, settlements,
    reachArch, latticeArch,
    seed: seed || 42,
  };
}
