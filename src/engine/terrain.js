// ═══════════════════════════════════════════════════════════
// terrain.js — Height function and noise utilities
// Pure math. No rendering. Produces height values from (x,y,z)
// coordinates on the unit sphere. Used by any renderer.
// ═══════════════════════════════════════════════════════════

import { OCEAN_DEPTH_BASE, ISLAND_MAX_HEIGHT, PLATEAU_HEIGHT } from './constants.js';

// ── Smooth noise (3D, interpolated) ──
const P = new Uint8Array(512);
(function initPermutation() {
  const p = [];
  for (let i = 0; i < 256; i++) p[i] = i;
  // Fisher-Yates with fixed seed for determinism
  let s = 42;
  for (let i = 255; i > 0; i--) {
    s = (s * 16807 + 0) % 2147483647;
    const j = s % (i + 1);
    [p[i], p[j]] = [p[j], p[i]];
  }
  for (let i = 0; i < 512; i++) P[i] = p[i & 255];
})();

function fade(t) { return t * t * t * (t * (t * 6 - 15) + 10); }
function lerp(a, b, t) { return a + t * (b - a); }

function grad(hash, x, y, z) {
  const h = hash & 15;
  const u = h < 8 ? x : y;
  const v = h < 4 ? y : (h === 12 || h === 14 ? x : z);
  return ((h & 1) ? -u : u) + ((h & 2) ? -v : v);
}

export function smoothNoise(x, y, z) {
  const X = Math.floor(x) & 255, Y = Math.floor(y) & 255, Z = Math.floor(z) & 255;
  const xf = x - Math.floor(x), yf = y - Math.floor(y), zf = z - Math.floor(z);
  const u = fade(xf), v = fade(yf), w = fade(zf);
  const A = P[X] + Y, AA = P[A] + Z, AB = P[A + 1] + Z;
  const B = P[X + 1] + Y, BA = P[B] + Z, BB = P[B + 1] + Z;
  return lerp(
    lerp(lerp(grad(P[AA], xf, yf, zf), grad(P[BA], xf - 1, yf, zf), u),
         lerp(grad(P[AB], xf, yf - 1, zf), grad(P[BB], xf - 1, yf - 1, zf), u), v),
    lerp(lerp(grad(P[AA + 1], xf, yf, zf - 1), grad(P[BA + 1], xf - 1, yf, zf - 1), u),
         lerp(grad(P[AB + 1], xf, yf - 1, zf - 1), grad(P[BB + 1], xf - 1, yf - 1, zf - 1), u), v),
    w
  );
}

// ── Fractal Brownian Motion ──
export function fbm(x, y, z, octaves) {
  let val = 0, amp = 1, freq = 1, total = 0;
  for (let i = 0; i < octaves; i++) {
    val += smoothNoise(x * freq, y * freq, z * freq) * amp;
    total += amp;
    amp *= 0.45;
    freq *= 2.1;
  }
  return val / total;
}

// ── Height Function ──
// Computes terrain height at a point on the unit sphere.
// world: { archs, edges } — the world geometry
// detail: LOD level (higher = more noise octaves)
// bwScale: bridge/plateau width multiplier
export function computeHeight(x, y, z, world, detail, bwScale) {
  const { archs, edges } = world;
  let height = OCEAN_DEPTH_BASE + fbm(x, y, z, Math.min(detail, 6)) * 400;

  // Ridged noise — organic mid-ocean ridges
  const rn1 = 1 - Math.abs(smoothNoise(x * 3.2, y * 3.2, z * 3.2));
  height += rn1 * rn1 * rn1 * 900;
  const rn2 = 1 - Math.abs(smoothNoise(x * 2.1 + 7.7, y * 2.1 + 3.3, z * 2.1 + 5.5));
  height += rn2 * rn2 * rn2 * 500;

  // ── Submarine plateaus ──
  const wMul = (bwScale || 0.13) / 0.13;

  // (A) Shelf blobs at each archipelago
  for (let a = 0; a < archs.length; a++) {
    const ar = archs[a];
    const dot = x * ar.cx + y * ar.cy + z * ar.cz;
    const blobR = ar.shelfR * 1.4 * wMul;
    if (dot < 1 - blobR * blobR * 2) continue;
    const bws = 3.5, bwa = blobR * 0.5;
    const bwx = x + smoothNoise(x * bws + a * 11.1, y * bws, z * bws) * bwa;
    const bwy = y + smoothNoise(x * bws + a * 11.1 + 77, y * bws + 77, z * bws + 77) * bwa;
    const bwz = z + smoothNoise(x * bws + a * 11.1 + 155, y * bws + 155, z * bws + 155) * bwa;
    const bwl = Math.sqrt(bwx * bwx + bwy * bwy + bwz * bwz) || 1;
    const wdot = (bwx * ar.cx + bwy * ar.cy + bwz * ar.cz) / bwl;
    const bd2 = 2 * (1 - wdot);
    const bf = Math.exp(-bd2 / (blobR * blobR * 0.8));
    if (bf < 0.02) continue;
    const pn1 = smoothNoise(x * 6 + a * 3.1, y * 6, z * 6) * 0.3;
    const pn2 = smoothNoise(x * 14 + a * 7.7, y * 14, z * 14) * 0.12;
    const bl = (PLATEAU_HEIGHT + 30 + (pn1 + pn2) * 120) * bf + height * (1 - bf);
    if (bl > height) height = bl;
  }

  // (B) Corridor connections — domain-warped great-circle bands
  for (let e = 0; e < edges.length; e++) {
    const ed = edges[e];
    const cws = 2.5, cwa = ed.w * 1.2;
    const cwx = x + smoothNoise(x * cws + e * 13.3, y * cws + e * 5.5, z * cws + e * 9.1) * cwa;
    const cwy = y + smoothNoise(x * cws + e * 13.3 + 77, y * cws + e * 5.5 + 77, z * cws + e * 9.1 + 77) * cwa;
    const cwz = z + smoothNoise(x * cws + e * 13.3 + 155, y * cws + e * 5.5 + 155, z * cws + e * 9.1 + 155) * cwa;
    const cwl = Math.sqrt(cwx * cwx + cwy * cwy + cwz * cwz) || 1;
    const dtp = Math.abs((cwx * ed.nx + cwy * ed.ny + cwz * ed.nz) / cwl);
    const widthNoise = smoothNoise(x * 4 + e * 7.1, y * 4 + e * 3.3, z * 4 + e * 5.7) * 0.35 + 0.8;
    const effectiveW = ed.w * widthNoise * wMul;
    if (dtp >= effectiveW) continue;
    const dA = x * ed.ax + y * ed.ay + z * ed.az;
    const dB = x * ed.bx + y * ed.by + z * ed.bz;
    if (dA < ed.dotAB - 0.35 || dB < ed.dotAB - 0.35) continue;
    const f = 1 - dtp / effectiveW;
    const sf = f * f * (3 - 2 * f);
    const pn1 = smoothNoise(x * 8, y * 8, z * 8) * 0.4;
    const pn2 = smoothNoise(x * 16, y * 16, z * 16) * 0.15;
    const pn3 = smoothNoise(x * 3 + 1.1, y * 3 + 2.2, z * 3 + 3.3) * 0.2;
    const pt = PLATEAU_HEIGHT + (pn1 + pn2 + pn3) * 150;
    const bl = pt * sf + height * (1 - sf);
    if (bl > height) height = bl;
  }

  // ── Archipelagos — domain-warped volcanic peaks ──
  for (let a = 0; a < archs.length; a++) {
    const ar = archs[a];
    const dot = x * ar.cx + y * ar.cy + z * ar.cz;
    if (dot < 0.85) continue;
    for (let p = 0; p < ar.peaks.length; p++) {
      const pk = ar.peaks[p];
      const pd = x * pk.px + y * pk.py + z * pk.pz;
      if (pd < 0.96) continue;

      // Domain warping for organic island shapes
      const ws = 1.0 / Math.max(pk.w, 0.005);
      const warpAmp = pk.w * 0.6;
      const w1x = smoothNoise(x * ws * 1.8, y * ws * 1.8, z * ws * 1.8) * warpAmp;
      const w1y = smoothNoise(x * ws * 1.8 + 77, y * ws * 1.8 + 77, z * ws * 1.8 + 77) * warpAmp;
      const w1z = smoothNoise(x * ws * 1.8 + 155, y * ws * 1.8 + 155, z * ws * 1.8 + 155) * warpAmp;
      const w2x = smoothNoise(x * ws * 4.5, y * ws * 4.5, z * ws * 4.5) * warpAmp * 0.35;
      const w2y = smoothNoise(x * ws * 4.5 + 33, y * ws * 4.5 + 33, z * ws * 4.5 + 33) * warpAmp * 0.35;
      const w2z = smoothNoise(x * ws * 4.5 + 66, y * ws * 4.5 + 66, z * ws * 4.5 + 66) * warpAmp * 0.35;
      let w3x = 0, w3y = 0, w3z = 0;
      if (detail > 5) {
        w3x = smoothNoise(x * ws * 12, y * ws * 12, z * ws * 12) * warpAmp * 0.12;
        w3y = smoothNoise(x * ws * 12 + 44, y * ws * 12 + 44, z * ws * 12 + 44) * warpAmp * 0.12;
        w3z = smoothNoise(x * ws * 12 + 88, y * ws * 12 + 88, z * ws * 12 + 88) * warpAmp * 0.12;
      }
      const wx = x + w1x + w2x + w3x, wy = y + w1y + w2y + w3y, wz = z + w1z + w2z + w3z;
      const wlen = Math.sqrt(wx * wx + wy * wy + wz * wz) || 1;
      const pdw = (wx * pk.px + wy * pk.py + wz * pk.pz) / wlen;
      const d2w = 2 * (1 - pdw);
      let pv = pk.h * Math.exp(-d2w * pk.w2inv);
      if (pv < 10) continue;

      // Ridge/valley erosion
      if (detail > 4 && pv > 50) {
        const rs = ws * 0.7;
        const ridge = (1 - Math.abs(smoothNoise(x * rs * 3, y * rs * 3, z * rs * 3))) *
                      (1 - Math.abs(smoothNoise(x * rs * 7, y * rs * 7, z * rs * 7)));
        const slopeFactor = Math.sin(Math.min(1, pv / pk.h) * Math.PI);
        pv *= 1 - ridge * 0.35 * slopeFactor;
      }

      // Fine roughness
      if (detail > 6 && pv > 100) {
        pv += smoothNoise(x * ws * 25, y * ws * 25, z * ws * 25) * 60 *
              Math.sin(Math.min(1, pv / pk.h) * Math.PI);
      }

      if (pv > height) height = pv;
    }
  }

  return height;
}
