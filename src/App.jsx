import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import * as THREE from "three";

// ============================================================
// AEOLIA — QUADTREE LOD TERRAIN ENGINE (Clean Build)
// Cube-sphere, adaptive subdivision, procedural height, arcball.
// ============================================================

const R = 5;
const TILE_RES = 25; // 25×25 = 625 verts per tile (was 17×17 = 289)
const MAX_DEPTH = 10;
const MIN_DEPTH = 3;
const SPLIT_FACTOR = 0.3;
const OCEAN_DEPTH_BASE = -4200;
const PLATEAU_HEIGHT = -120;
const ISLAND_MAX_HEIGHT = 3000; // physics bound: basalt at 1g, Aeolian isostasy
const DISP_MULT = 3.4e-8; // physically correct: 1/R_aeolia_meters // fixed 1× land protrusion

// ─── URBANIZATION ────────────────────────────────────────
const URBAN_GREY   = [0.30, 0.28, 0.26];  // concrete grey — reads against green terrain
const HARBOR_WATER = [0.04, 0.06, 0.10];  // turbid harbor water
const INCLINE_CLR  = [0.36, 0.33, 0.30];  // inclined railway cuts

// ─── FACTION DESIGNATIONS ────────────────────────────────
// Reach: temperate N. hemisphere, widely-spaced peaks → competitive
//        island-state pluralism, open-ocean sailing lineage.
// Lattice: dense S. hemisphere cluster, many peaks → hydraulic
//          cooperation, sheltered-water bureaucratic civilization.
let REACH_ARCH   = 0;
let LATTICE_ARCH = 1;

// ─── POLITY NAMES ────────────────────────────────────────
// 50 thinly-veiled maritime/civilizational names. Indices 0 & 1
// are reserved for the two great powers. The rest are shuffled
// per-seed and assigned to remaining archipelagos.
const POLITY_NAMES = [
  "The Reach",       // 0  — Anglo-Saxon thalassocracy (British maritime arc)
  "The Lattice",     // 1  — hydraulic bureaucracy (Chinese imperial model)
  "The Gyre",        // Greek/Mediterranean — circular, philosophical, maritime
  "The Narrows",     // Turkish/Ottoman — strait-controlling chokepoint power
  "The Shelf",       // Indian subcontinent — vast, stable, deep-rooted
  "The Traverse",    // Polynesian — wayfinding, open-ocean crossing culture
  "The Loom",        // West African — textile trade, inland-to-coast networks
  "The Windward",    // Caribbean — trade-wind corridor, plantation-and-resistance
  "The Caldera",     // Japanese — volcanic island chain, insular intensity
  "The Strand",      // Nordic/Scandinavian — coastal raiders, sagas, cold water
  "The Bight",       // Gulf of Guinea — deep coastal curve, river-mouth kingdoms
  "The Cairn",       // Celtic — stone-marker culture, oral tradition, mist
  "The Shoal",       // Southeast Asian — shallow-water trade, spice routes
  "The Polder",      // Dutch — engineering, reclamation, mercantile republic
  "The Tidemark",    // Mesopotamian — irrigated agriculture, tidal rhythm
  "The Breakwater",  // Venetian/Italian — harbor-city commerce, glasswork
  "The Current",     // Korean — peninsular, caught between larger powers
  "The Sargasso",    // Isolated deep-ocean — becalmed, mysterious, self-contained
  "The Atoll",       // Pacific — coral ring, subsistence, vast ocean identity
  "The Meridian",    // Portuguese — navigation, exploration, cartographic obsession
  "The Cordage",     // Arab/Omani — dhow trade, monsoon sailing, rope and sail
  "The Basalt",      // Icelandic — volcanic isolation, literacy, sagas
  "The Estuary",     // Egyptian/Nile — delta civilization, monumental, ancient
  "The Fathom",      // Persian — depth, trade, mathematical astronomy
  "The Headland",    // Iberian — promontory fortresses, reconquest, Atlantic gaze
  "The Isthmus",     // Mesoamerican — land-bridge, two-ocean, calendrical
  "The Keel",        // Viking — shipbuilding, expansion, thing-law
  "The Leeward",     // Micronesian — sheltered-side settlements, small-island life
  "The Mooring",     // Swahili coast — port cities, monsoon trade, coral stone
  "The Neap",        // Bengali/delta — tidal agriculture, river-laced, dense
  "The Outrigger",   // Austronesian — double-hull voyaging, deep diaspora
  "The Pillar",      // Ethiopian/highland — vertical geography, ancient script
  "The Quay",        // Phoenician — port engineering, alphabet, purple dye
  "The Riptide",     // Māori — powerful currents, carved prows, haka
  "The Spindrift",   // Russian Far East — harsh seas, fur trade, frontier
  "The Trawl",       // Basque — deep-sea fishing, linguistic isolate, endurance
  "The Undertow",    // Siberian coast — hidden currents, permafrost, remote
  "The Vanguard",    // Ottoman/naval — fleet-forward, imperial administration
  "The Waypoint",    // Aboriginal Australian — songlines, deep-time navigation
  "The Zenith",      // Islamic Golden Age — celestial navigation, astronomy, trade
  "The Anchorage",   // Inuit/Arctic — ice-edge survival, seasonal migration
  "The Barque",      // French colonial — square-rigged navy, Code Noir, sugar
  "The Crest",       // Hawaiian — wave mastery, ali'i hierarchy, volcanic
  "The Doldrums",    // Equatorial — becalmed belt, monsoon pivot, patience
  "The Eddy",        // Thai/riverine — backwater kingdoms, silk, temple spires
  "The Freeboard",   // Malay — shipbuilding, sultanates, strait control
  "The Gunwale",     // Filipino — island-hopping, galleon trade, resilience
  "The Haven",       // Hanseatic — trading league, guild law, cold harbors
  "The Inlet",       // Chilean/Patagonian — fjords, isolation, southern rain
  "The Jetty",       // Somali/Horn — port projection, incense trade, coast-and-desert
];

// ─── NOISE ────────────────────────────────────────────────
function _hash(x, y, z) {
  let h = (x * 374761393 + y * 668265263 + z * 1274126177) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) & 0x7fffffff) / 0x7fffffff;
}

function smoothNoise(x, y, z) {
  const ix = Math.floor(x), iy = Math.floor(y), iz = Math.floor(z);
  const fx = x - ix, fy = y - iy, fz = z - iz;
  const ux = fx*fx*(3-2*fx), uy = fy*fy*(3-2*fy), uz = fz*fz*(3-2*fz);
  const n000=_hash(ix,iy,iz),n100=_hash(ix+1,iy,iz),n010=_hash(ix,iy+1,iz),n110=_hash(ix+1,iy+1,iz);
  const n001=_hash(ix,iy,iz+1),n101=_hash(ix+1,iy,iz+1),n011=_hash(ix,iy+1,iz+1),n111=_hash(ix+1,iy+1,iz+1);
  return (n000*(1-ux)*(1-uy)*(1-uz)+n100*ux*(1-uy)*(1-uz)+n010*(1-ux)*uy*(1-uz)+n110*ux*uy*(1-uz)+
    n001*(1-ux)*(1-uy)*uz+n101*ux*(1-uy)*uz+n011*(1-ux)*uy*uz+n111*ux*uy*uz)*2-1;
}

function fbm(x, y, z, octaves) {
  let v=0, a=0.5, f=3.5;
  for (let i=0; i<octaves; i++) { v+=a*smoothNoise(x*f,y*f,z*f); a*=0.5; f*=2.1; }
  return v;
}

// ─── WORLD DATA ───────────────────────────────────────────
function mulberry32(s) {
  return ()=>{s|=0;s=(s+0x6D2B79F5)|0;let t=Math.imul(s^(s>>>15),1|s);t=(t+Math.imul(t^(t>>>7),61|t))^t;return((t^(t>>>14))>>>0)/4294967296;};
}

function latLonToXYZ(lat,lon) {
  const p=(90-lat)*Math.PI/180, t=(lon+180)*Math.PI/180;
  return [Math.sin(p)*Math.cos(t), Math.cos(p), Math.sin(p)*Math.sin(t)];
}

const ARCH_COUNT = 42; // enough for mystery, El Dorados, and Sentinelese


// ─── ENGINE IMPORT (replaces inline buildWorld/computeSubstrate/assignPolitics/detectSettlements) ──
import { buildWorld } from './engine/world.js';

// ─── BUILDING INSTANCE GENERATION ────────────────────────
// Out-of-scale structures: ~100–1000× real size so they read
// from orbit. Terrain-sampled, altitude-penalized, and filtered:
// buildings grow uphill from the coast — no isolated inland clusters.
function generateBuildingData(settlements, world) {
  const brng = mulberry32(777);
  const allBuildings = [];
  const WATERFRONT_CEIL = 80;    // meters ASL: always accept
  const SUPPORT_DOT = 0.99993;   // ~0.008 rad ≈ 235 km: "nearby"

  for (const s of settlements) {
    // Population-driven density: look up urbanization from history
    const archState = world.history.states[s.archIdx];
    const urb = archState ? archState.urbanization : 0.1;
    const popScale = 0.2 + urb * 0.8; // 0.2 minimum, scales to 1.0

    const rawCount = Math.floor((s.kind === "capital"
      ? 40 + s.importance * 60
      : 8 + s.importance * 20) * popScale);

    // Tangent frame at settlement center
    let nx = s.cy*s.mz - s.cz*s.my;
    let ny = s.cz*s.mx - s.cx*s.mz;
    let nz = s.cx*s.my - s.cy*s.mx;
    const nl = Math.sqrt(nx*nx + ny*ny + nz*nz) || 1;
    nx /= nl; ny /= nl; nz /= nl;

    // ── Phase 1: generate candidates with terrain height ──
    const candidates = [];
    for (let i = 0; i < rawCount; i++) {
      const angle = brng() * Math.PI * 2;
      const rawDist = brng() * brng();
      const dist = rawDist * s.radius * 0.65;

      const ca = Math.cos(angle), sa = Math.sin(angle);
      let px = s.cx + dist * (ca * s.mx + sa * nx);
      let py = s.cy + dist * (ca * s.my + sa * ny);
      let pz = s.cz + dist * (ca * s.mz + sa * nz);
      const pl = Math.sqrt(px*px + py*py + pz*pz);
      px /= pl; py /= pl; pz /= pl;

      const terrainH = computeHeight(px, py, pz, world, 5, 0.20);
      if (terrainH < -10 || terrainH > 800) continue;

      let altPenalty = 1.0;
      if (terrainH > 400) altPenalty = 1 - (terrainH - 400) / 400;
      else if (terrainH > 150) altPenalty = 1 - (terrainH - 150) / 500 * 0.4;

      const proximity = 1 - rawDist;
      const maxH = (s.kind === "capital" ? 0.045 : 0.018) * popScale;
      const h = maxH * (0.15 + 0.85 * proximity) * (0.3 + brng() * 0.7) * s.importance * altPenalty;
      if (h < 0.002) continue;
      const w = 0.003 + h * 0.12;

      candidates.push({ px, py, pz, h, w, terrainH, faction: s.faction });
    }

    // ── Phase 2: sequential acceptance (coast → uphill) ──
    // Sort lowest-first so waterfront is accepted before mid-levels.
    candidates.sort((a, b) => a.terrainH - b.terrainH);
    const accepted = [];

    for (const c of candidates) {
      if (c.terrainH < WATERFRONT_CEIL) {
        // Near the water — always accept
        accepted.push(c);
        continue;
      }
      // Uphill: need at least one accepted building nearby AND lower
      let supported = false;
      for (let j = accepted.length - 1; j >= 0; j--) {
        const a = accepted[j];
        if (a.terrainH >= c.terrainH) continue;
        const dot = c.px*a.px + c.py*a.py + c.pz*a.pz;
        if (dot > SUPPORT_DOT) { supported = true; break; }
      }
      if (supported) accepted.push(c);
    }

    for (const c of accepted) {
      allBuildings.push({ px: c.px, py: c.py, pz: c.pz, h: c.h, w: c.w, faction: c.faction });
    }
  }
  return allBuildings;
}

// ─── HEIGHT FUNCTION ──────────────────────────────────────
function computeHeight(x, y, z, world, detail, bwScale) {
  const {archs,edges} = world;
  let height = OCEAN_DEPTH_BASE + fbm(x,y,z, Math.min(detail,6)) * 400;
  // Ridged noise — organic mid-ocean ridges
  const rn1 = 1 - Math.abs(smoothNoise(x*3.2,y*3.2,z*3.2));
  height += rn1*rn1*rn1 * 900;
  const rn2 = 1 - Math.abs(smoothNoise(x*2.1+7.7,y*2.1+3.3,z*2.1+5.5));
  height += rn2*rn2*rn2 * 500;
  // Submarine plateaus — organic, domain-warped continental shelves
  // Two features: (A) shelf blobs at each arch, (B) corridor connections between them
  // Both domain-warped for sinuous edges like real continental margins
  const wMul = (bwScale || 0.13) / 0.13;

  // (A) Shelf blobs — Gaussian platforms around each archipelago center
  // These merge smoothly with the corridor connections at edges
  for (let a=0; a<archs.length; a++) {
    const ar=archs[a];
    const dot=x*ar.cx+y*ar.cy+z*ar.cz;
    const blobR = ar.shelfR * 1.4 * wMul; // slightly wider than the peak scatter
    if (dot < 1 - blobR*blobR*2) continue; // early reject
    // Domain warp — large-scale meander of shelf boundary
    const bws = 3.5; // low frequency for big meanders
    const bwa = blobR * 0.5; // 50% amplitude — significant wander
    const bwx = x + smoothNoise(x*bws+a*11.1, y*bws, z*bws) * bwa;
    const bwy = y + smoothNoise(x*bws+a*11.1+77, y*bws+77, z*bws+77) * bwa;
    const bwz = z + smoothNoise(x*bws+a*11.1+155, y*bws+155, z*bws+155) * bwa;
    const bwl = Math.sqrt(bwx*bwx+bwy*bwy+bwz*bwz)||1;
    const wdot = (bwx*ar.cx+bwy*ar.cy+bwz*ar.cz)/bwl;
    const bd2 = 2*(1-wdot);
    const bf = Math.exp(-bd2/(blobR*blobR*0.8));
    if (bf < 0.02) continue;
    const pn1 = smoothNoise(x*6+a*3.1,y*6,z*6) * 0.3;
    const pn2 = smoothNoise(x*14+a*7.7,y*14,z*14) * 0.12;
    const bl = (PLATEAU_HEIGHT + 30 + (pn1+pn2)*120) * bf + height*(1-bf);
    if (bl>height) height=bl;
  }

  // (B) Corridor connections — domain-warped great-circle bands
  for (let e=0; e<edges.length; e++) {
    const ed=edges[e];
    // Domain warp the sample position — makes corridors meander
    // Low frequency, high amplitude: these are Beringia-scale features
    const cws = 2.5; // large-scale wander frequency
    const cwa = ed.w * 1.2; // amplitude proportional to corridor width
    const cwx = x + smoothNoise(x*cws+e*13.3, y*cws+e*5.5, z*cws+e*9.1) * cwa;
    const cwy = y + smoothNoise(x*cws+e*13.3+77, y*cws+e*5.5+77, z*cws+e*9.1+77) * cwa;
    const cwz = z + smoothNoise(x*cws+e*13.3+155, y*cws+e*5.5+155, z*cws+e*9.1+155) * cwa;
    const cwl = Math.sqrt(cwx*cwx+cwy*cwy+cwz*cwz)||1;
    // Distance from warped position to the edge plane
    const dtp=Math.abs((cwx*ed.nx+cwy*ed.ny+cwz*ed.nz)/cwl);
    // Width variation — medium-frequency noise on the corridor width
    const widthNoise = smoothNoise(x*4+e*7.1, y*4+e*3.3, z*4+e*5.7) * 0.35 + 0.8;
    const effectiveW = ed.w * widthNoise * wMul;
    if (dtp>=effectiveW) continue;
    // Endpoint check (use original unwrapped position for stability)
    const dA=x*ed.ax+y*ed.ay+z*ed.az, dB=x*ed.bx+y*ed.by+z*ed.bz;
    if (dA<ed.dotAB-0.35||dB<ed.dotAB-0.35) continue;
    // Gaussian falloff instead of quadratic — smoother transition to deep ocean
    const f=1-dtp/effectiveW;
    const sf=f*f*(3-2*f); // smoothstep for organic falloff
    // Rolling submarine terrain — hills and channels
    const pn1 = smoothNoise(x*8,y*8,z*8) * 0.4;
    const pn2 = smoothNoise(x*16,y*16,z*16) * 0.15;
    const pn3 = smoothNoise(x*3+1.1,y*3+2.2,z*3+3.3) * 0.2;
    const pt = PLATEAU_HEIGHT + (pn1+pn2+pn3) * 150;
    const bl=pt*sf+height*(1-sf);
    if (bl>height) height=bl;
  }
  // Archipelagos — narrow volcanic peaks
  for (let a=0; a<archs.length; a++) {
    const ar=archs[a];
    const dot=x*ar.cx+y*ar.cy+z*ar.cz;
    if (dot<0.85) continue;
    for (let p=0;p<ar.peaks.length;p++){
      const pk=ar.peaks[p];
      const pd=x*pk.px+y*pk.py+z*pk.pz;
      if(pd<0.96)continue;

      // ── FRACTAL ISLAND GENERATION ──
      // TRUE DOMAIN WARPING: warp the sample position before computing
      // distance to peak center. This creates genuine concavities (bays,
      // coves, harbors) not just radial stretch.
      const ws = 1.0 / Math.max(pk.w, 0.005); // scale relative to peak size
      const warpAmp = pk.w * 0.6; // warp amplitude = 60% of peak width

      // Layer 1: large-scale shape — defines the overall island silhouette
      // (kidney beans, crescents, L-shapes, natural harbors)
      const w1x = smoothNoise(x*ws*1.8, y*ws*1.8, z*ws*1.8) * warpAmp;
      const w1y = smoothNoise(x*ws*1.8+77, y*ws*1.8+77, z*ws*1.8+77) * warpAmp;
      const w1z = smoothNoise(x*ws*1.8+155, y*ws*1.8+155, z*ws*1.8+155) * warpAmp;

      // Layer 2: medium features — bays, peninsulas, headlands
      const w2x = smoothNoise(x*ws*4.5, y*ws*4.5, z*ws*4.5) * warpAmp * 0.35;
      const w2y = smoothNoise(x*ws*4.5+33, y*ws*4.5+33, z*ws*4.5+33) * warpAmp * 0.35;
      const w2z = smoothNoise(x*ws*4.5+66, y*ws*4.5+66, z*ws*4.5+66) * warpAmp * 0.35;

      // Layer 3 (close zoom): small coves, inlets, sea stacks
      let w3x=0, w3y=0, w3z=0;
      if (detail > 5) {
        w3x = smoothNoise(x*ws*12, y*ws*12, z*ws*12) * warpAmp * 0.12;
        w3y = smoothNoise(x*ws*12+44, y*ws*12+44, z*ws*12+44) * warpAmp * 0.12;
        w3z = smoothNoise(x*ws*12+88, y*ws*12+88, z*ws*12+88) * warpAmp * 0.12;
      }

      // Warped sample position
      const wx = x+w1x+w2x+w3x, wy = y+w1y+w2y+w3y, wz = z+w1z+w2z+w3z;
      const wlen = Math.sqrt(wx*wx+wy*wy+wz*wz) || 1;
      // Distance from warped position to peak center (on unit sphere)
      const pdw = (wx*pk.px + wy*pk.py + wz*pk.pz) / wlen;
      const d2w = 2*(1-pdw);

      // Peak shape from warped distance
      let pv = pk.h * Math.exp(-d2w * pk.w2inv);
      if (pv < 10) continue;

      // Ridge/valley erosion on slopes (close zoom)
      if (detail > 4 && pv > 50) {
        const rs = ws * 0.7;
        const ridge = (1 - Math.abs(smoothNoise(x*rs*3, y*rs*3, z*rs*3))) *
                      (1 - Math.abs(smoothNoise(x*rs*7, y*rs*7, z*rs*7)));
        const slopeFactor = Math.sin(Math.min(1, pv / pk.h) * Math.PI);
        pv *= 1 - ridge * 0.35 * slopeFactor;
      }

      // Fine terrain roughness (closest zoom)
      if (detail > 6 && pv > 30) {
        pv *= 1 + fbm(x*ws*4, y*ws*4, z*ws*4, detail-5) * 0.08;
      }

      if(pv>height)height=pv;
    }
  }
  return height;
}

// ─── COLOR LUT — NATURALISTIC GRADIENT ────────────────────
const LUT_N = 1024;
const LUT = new Float32Array(LUT_N * 3);
(function(){
  const S=[
    [-5000,.012,.025,.08],[-4000,.018,.035,.10],[-3000,.025,.050,.14],[-2200,.035,.070,.18],
    [-1500,.045,.100,.24],[-800,.060,.140,.32],[-500,.080,.185,.38],
    [-300,.100,.220,.42],[-150,.130,.270,.48],[-80,.155,.310,.52],
    [-40,.175,.340,.54],[-15,.195,.360,.55],[-5,.210,.375,.54],
    [0,.220,.380,.50],
    [5,.240,.360,.42],[15,.265,.350,.36],[35,.280,.340,.30],
    [80,.260,.330,.24],[150,.240,.310,.20],[300,.225,.290,.18],
    [500,.240,.270,.17],[800,.270,.260,.18],
    [1200,.320,.280,.20],[1800,.380,.330,.25],
    [2500,.460,.420,.36],[3500,.550,.510,.44],
  ];
  for(let i=0;i<LUT_N;i++){
    const h=-5000+(i/(LUT_N-1))*8500;
    let si=0;while(si<S.length-2&&S[si+1][0]<h)si++;
    const [h0,r0,g0,b0]=S[si],[h1,r1,g1,b1]=S[si+1];
    const t=Math.max(0,Math.min(1,(h-h0)/(h1-h0))),s=t*t*(3-2*t);
    LUT[i*3]=r0+s*(r1-r0);LUT[i*3+1]=g0+s*(g1-g0);LUT[i*3+2]=b0+s*(b1-b0);
  }
})();

function heightColor(depth, noiseVal) {
  const perturbed = depth + (noiseVal||0) * 25;
  const i=Math.max(0,Math.min(LUT_N-1,((perturbed+5000)/8500*(LUT_N-1))|0));
  return [LUT[i*3],LUT[i*3+1],LUT[i*3+2]];
}

// ─── CUBE-SPHERE MAPPING ─────────────────────────────────
const FACES = [
  {name:"+X", map:(u,v)=>[1,v,-u]},  {name:"-X", map:(u,v)=>[-1,v,u]},
  {name:"+Y", map:(u,v)=>[u,1,-v]},  {name:"-Y", map:(u,v)=>[u,-1,v]},
  {name:"+Z", map:(u,v)=>[u,v,1]},   {name:"-Z", map:(u,v)=>[-u,v,-1]},
];

function cubeToSphere(faceMap, u, v) {
  const [x,y,z]=faceMap(u,v);
  const len=Math.sqrt(x*x+y*y+z*z);
  return [x/len,y/len,z/len];
}

// ─── TILE MESH GENERATION ─────────────────────────────────
function generateTileMesh(faceMap, uMin, uMax, vMin, vMax, world, seaLevel, depth, bwScale) {
  const N=TILE_RES, du=(uMax-uMin)/(N-1), dv=(vMax-vMin)/(N-1);
  const detailLevel = Math.min(4+depth, 8);
  const positions=new Float32Array(N*N*3);
  const colors=new Float32Array(N*N*3);
  const normals=new Float32Array(N*N*3);
  const heights=new Float32Array(N*N); // raw height per vertex (meters)
  const indices=[];
  for (let j=0;j<N;j++){
    for (let i=0;i<N;i++){
      const u=uMin+i*du, v=vMin+j*dv;
      const [sx,sy,sz]=cubeToSphere(faceMap,u,v);
      const h=computeHeight(sx,sy,sz,world,detailLevel,bwScale);
      const disp=h>seaLevel?1+(h-seaLevel)*DISP_MULT:1;
      const idx=j*N+i;
      positions[idx*3]=sx*R*disp; positions[idx*3+1]=sy*R*disp; positions[idx*3+2]=sz*R*disp;
      const [cr,cg,cb]=heightColor(h-seaLevel, smoothNoise(sx*10,sy*10,sz*10));
      colors[idx*3]=cr; colors[idx*3+1]=cg; colors[idx*3+2]=cb;
      normals[idx*3]=sx; normals[idx*3+1]=sy; normals[idx*3+2]=sz;
      heights[idx]=h;
    }
  }
  for (let j=0;j<N-1;j++) for (let i=0;i<N-1;i++){
    const a=j*N+i,b=a+1,c=a+N,d=c+1;
    indices.push(a,c,b,b,c,d);
  }
  const geo=new THREE.BufferGeometry();
  geo.setAttribute("position",new THREE.BufferAttribute(positions,3));
  geo.setAttribute("color",new THREE.BufferAttribute(colors,3));
  geo.setAttribute("normal",new THREE.BufferAttribute(normals,3));
  geo.setIndex(indices);
  geo.userData.heights=heights; // stashed for urban overlay pass
  return geo;
}

// ─── URBAN OVERLAY (Pass B) ──────────────────────────────
// Modifies vertex colors in-place. Separate from terrain generation
// so it can be toggled per-era without regenerating height data.
function applyUrbanOverlay(geo, world, seaLevel, depth, era) {
  const { settlements } = world;
  if (!settlements || settlements.length === 0) return;

  const pos = geo.attributes.position.array;
  const col = geo.attributes.color.array;
  const hts = geo.userData.heights;
  if (!hts) return;
  const N = pos.length / 3;

  for (let i = 0; i < N; i++) {
    const px = pos[i*3], py = pos[i*3+1], pz = pos[i*3+2];
    const len = Math.sqrt(px*px + py*py + pz*pz);
    // Unit-sphere direction (displacement is negligible)
    const sx = px/len, sy = py/len, sz = pz/len;
    const h = hts[i];
    const altAboveSea = h - seaLevel;

    for (let si = 0; si < settlements.length; si++) {
      const s = settlements[si];
      const dot = sx*s.cx + sy*s.cy + sz*s.cz;
      // Quick reject: generous threshold
      if (dot < 1 - s.radius*s.radius*2) continue;
      const angDist = Math.sqrt(Math.max(0, 2*(1-dot)));
      if (angDist > s.radius) continue;

      const proximity = 1 - angDist / s.radius;

      // ── Altitude-dependent density ──
      // Bible: "Wealth measured in altitude — rich on the peaks,
      // poor at the waterline." Dense waterfront, thins upslope.
      let altFactor;
      if (altAboveSea < -30) {
        // Deep water: harbor turbidity near settlement
        altFactor = Math.max(0, 1 + altAboveSea / 300) * 0.4;
      } else if (altAboveSea < 0) {
        // Shallows / tidal zone: piers, reclaimed land
        altFactor = 0.6 + 0.4 * (1 + altAboveSea / 30);
      } else if (altAboveSea < 60) {
        // Waterfront: maximum density
        altFactor = 1.0;
      } else if (altAboveSea < 600) {
        // Mid-levels: "the aspiring classes, progressively quieter"
        altFactor = 1 - (altAboveSea - 60) / 540 * 0.7;
      } else if (altAboveSea < 1200) {
        // Upper slopes: scattered villas, government buildings
        altFactor = 0.3 * (1 - (altAboveSea - 600) / 600);
      } else {
        altFactor = 0;
      }
      if (altFactor <= 0) continue;

      // Overall blend — importance scales the footprint
      let blend = proximity * altFactor * s.importance; // linear proximity, not squared

      // ── Harbor water darkening ──
      if (altAboveSea < -5 && proximity > 0.2) {
        const hBlend = blend * 0.6;
        col[i*3]   += (HARBOR_WATER[0] - col[i*3])   * hBlend;
        col[i*3+1] += (HARBOR_WATER[1] - col[i*3+1]) * hBlend;
        col[i*3+2] += (HARBOR_WATER[2] - col[i*3+2]) * hBlend;
        continue; // don't also apply land urban color to water
      }

      // ── Incline railway cuts (high zoom only) ──
      if (depth >= 6 && altAboveSea > 20 && altAboveSea < 900 && s.inclines.length > 0) {
        // Offset from harbor center toward vertex
        const ox = sx - s.cx, oy = sy - s.cy, oz = sz - s.cz;
        const ol = Math.sqrt(ox*ox + oy*oy + oz*oz) || 1;
        for (const inc of s.inclines) {
          // Cross product magnitude = perpendicular distance to line
          const crossX = oy*inc.dz - oz*inc.dy;
          const crossY = oz*inc.dx - ox*inc.dz;
          const crossZ = ox*inc.dy - oy*inc.dx;
          const perpDist = Math.sqrt(crossX*crossX + crossY*crossY + crossZ*crossZ);
          const lineWidth = s.radius * 0.03; // narrow cuts
          if (perpDist < lineWidth) {
            const along = (ox*inc.dx + oy*inc.dy + oz*inc.dz);
            if (along > 0) { // only uphill from harbor
              const incBlend = (1 - perpDist/lineWidth) * 0.4 * altFactor;
              col[i*3]   += (INCLINE_CLR[0] - col[i*3])   * incBlend;
              col[i*3+1] += (INCLINE_CLR[1] - col[i*3+1]) * incBlend;
              col[i*3+2] += (INCLINE_CLR[2] - col[i*3+2]) * incBlend;
            }
          }
        }
      }

      // ── Core urban density gradient ──
      // Slight warmth variation with proximity (waterfront = darker)
      const warmth = 1 - proximity * 0.15;
      const uR = URBAN_GREY[0] * warmth;
      const uG = URBAN_GREY[1] * warmth;
      const uB = URBAN_GREY[2] * warmth;
      const bClamped = Math.min(blend, 0.88);
      col[i*3]   += (uR - col[i*3])   * bClamped;
      col[i*3+1] += (uG - col[i*3+1]) * bClamped;
      col[i*3+2] += (uB - col[i*3+2]) * bClamped;
    }
  }
  geo.attributes.color.needsUpdate = true;
}

// ─── QUADTREE NODE ────────────────────────────────────────
class QNode {
  constructor(fi,uMin,uMax,vMin,vMax,depth){
    this.fi=fi;this.uMin=uMin;this.uMax=uMax;this.vMin=vMin;this.vMax=vMax;this.depth=depth;
    this.children=null;
    const [cx,cy,cz]=cubeToSphere(FACES[fi].map,(uMin+uMax)/2,(vMin+vMax)/2);
    this.cx=cx*R;this.cy=cy*R;this.cz=cz*R;
    this.angularSize=(uMax-uMin)*Math.PI/2;
  }
  shouldSplit(camPos){
    if(this.depth>=MAX_DEPTH)return false;
    if(this.depth<MIN_DEPTH)return true;
    const dx=camPos.x-this.cx,dy=camPos.y-this.cy,dz=camPos.z-this.cz;
    return (this.angularSize*R/Math.sqrt(dx*dx+dy*dy+dz*dz))>SPLIT_FACTOR;
  }
  split(){
    if(this.children)return;
    const uM=(this.uMin+this.uMax)/2,vM=(this.vMin+this.vMax)/2,d=this.depth+1,f=this.fi;
    this.children=[new QNode(f,this.uMin,uM,this.vMin,vM,d),new QNode(f,uM,this.uMax,this.vMin,vM,d),
      new QNode(f,this.uMin,uM,vM,this.vMax,d),new QNode(f,uM,this.uMax,vM,this.vMax,d)];
  }
  merge(){
    if(!this.children)return;
    for(const c of this.children){c.merge();if(c.mesh){c.mesh.geometry.dispose();c.mesh=null;}}
    this.children=null;
  }
  collectLeaves(camPos,leaves){
    if(this.shouldSplit(camPos)){if(!this.children)this.split();for(const c of this.children)c.collectLeaves(camPos,leaves);}
    else{if(this.children)this.merge();leaves.push(this);}
  }
}

// ─── EARTH OVERLAY (scale reference) ──────────────────────
// Simplified continent outlines as [lat, lon] in degrees
// All positioned in absolute Earth coordinates, Africa-centric projection
const CONTINENTS = {
  africa: [[35.8,-5.8],[37,10],[32,32],[30,33],[22,37],[12,44],[11.5,51],[2,46],
    [-1,42],[-7,40],[-11,40],[-15,41],[-24,36],[-26,33],[-34,26],[-34.8,18],
    [-33,17],[-29,16],[-18,12],[-12,14],[-6,12],[0,10],[5,1],[5,-5],
    [6,-10],[4,-7],[7,-14],[10,-16],[14.5,-17],[19,-16.5],[21,-17],[24,-16],
    [28,-13],[32,-9],[35.5,-6]],
  europe: [[36,-6],[36,0],[43,-9],[44,-1],[46,0],[48,-5],[51,-5],[53,-1],
    [51,4],[54,8],[56,8],[58,6],[62,5],[65,14],[70,20],[70,28],
    [60,28],[56,22],[54,14],[50,14],[48,17],[44,12],[40,18],[42,24],
    [40,28],[36,28],[38,24],[36,15],[38,6],[36,-6]],
  asia: [[40,28],[42,35],[30,35],[13,44],[25,57],[25,66],[20,73],[8,77],
    [16,80],[22,88],[20,97],[10,98],[2,104],[6,116],[22,108],[24,120],
    [30,122],[35,129],[40,130],[42,132],[46,143],[52,142],[60,163],
    [66,175],[70,170],[72,140],[68,90],[55,73],[52,55],[47,40],[42,28]],
  northAmerica: [[8,-77],[18,-88],[20,-87],[22,-97],[25,-90],[30,-82],
    [30,-81],[36,-76],[40,-74],[42,-70],[45,-67],[47,-53],[52,-56],
    [47,-53],[52,-60],[58,-62],[60,-65],[64,-65],[69,-54],[72,-56],
    [76,-69],[72,-80],[70,-100],[68,-135],[60,-147],[58,-152],[55,-130],
    [50,-125],[40,-124],[33,-117],[23,-110],[18,-105],[15,-92],[8,-77]],
  southAmerica: [[12,-72],[10,-62],[7,-52],[0,-50],[-3,-41],[-8,-35],
    [-15,-39],[-23,-42],[-33,-51],[-38,-57],[-42,-63],[-48,-66],
    [-55,-67],[-55,-64],[-52,-70],[-46,-76],[-40,-73],[-33,-72],
    [-18,-70],[-14,-76],[-5,-80],[0,-78],[7,-77],[12,-72]],
  australia: [[-12,131],[-12,136],[-15,141],[-18,146],[-24,153],[-28,153],
    [-33,152],[-35,150],[-37,150],[-39,146],[-37,140],[-35,137],
    [-34,135],[-33,130],[-31,115],[-25,113],[-22,114],[-20,119],
    [-15,129],[-12,131]],
};
const EARTH_CENTER = [5, 25]; // projection center (Africa-centric)
const EARTH_TO_AEOLIA = 6371 / 29440;

function buildContinentLine(pts, centerDir) {
  const c = new THREE.Vector3(...centerDir).normalize();
  const up = new THREE.Vector3(0, 1, 0);
  const east = new THREE.Vector3().crossVectors(up, c);
  if (east.lengthSq() < 0.001) east.set(1, 0, 0);
  east.normalize();
  const north = new THREE.Vector3().crossVectors(c, east).normalize();
  const positions = [];
  for (const [lat, lon] of pts) {
    const dLat = (lat - EARTH_CENTER[0]) * Math.PI / 180 * EARTH_TO_AEOLIA;
    const dLon = (lon - EARTH_CENTER[1]) * Math.PI / 180 * EARTH_TO_AEOLIA;
    const p = c.clone().addScaledVector(north, dLat).addScaledVector(east, dLon)
      .normalize().multiplyScalar(R * 1.002);
    positions.push(p.x, p.y, p.z);
  }
  positions.push(positions[0], positions[1], positions[2]); // close loop
  return new Float32Array(positions);
}


function AeoliaLODInner({ seed, onSeedChange }) {
  const mountRef=useRef(null);
  const stateRef=useRef({});
  const [seaLevel,setSeaLevel]=useState(0);
  const [lightPct,setLightPct]=useState(500);
  const [bridgeW,setBridgeW]=useState(13); // ×0.01 radians, so 13 = 0.13 rad
  const [overlayMode,setOverlayMode]=useState(0); // 0=off, 1=Africa, 2=All Earth
  const overlayRef=useRef(0);
  const [urbanMode,setUrbanMode]=useState(0); // 0=off, 1=cities, 2=cities+pins
  const urbanRef=useRef(0);
  const [ready,setReady]=useState(false);
  const [stats,setStats]=useState({tiles:0,depth:0,verts:0});
  const [zoom,setZoom]=useState(22);
  const [selectedArch,setSelectedArch]=useState(null);
  const lastM=useRef({x:0,y:0});
  const clickStart=useRef({x:0,y:0});
  const zoomRef=useRef(22);
  const seaRef=useRef(0);
  const lightRef=useRef(500);
  const bwRef=useRef(13);
  const globeQuat=useRef(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),0.3));
  const dragData=useRef({active:false,startPoint:null,startQuat:null,lastGood:null});

  const world=useMemo(()=>buildWorld(seed),[seed]);

  // Init scene
  useEffect(()=>{
    const el=mountRef.current; if(!el)return;
    const w=el.clientWidth, h=el.clientHeight;
    const scene=new THREE.Scene();
    const camera=new THREE.PerspectiveCamera(45,w/h,0.01,200);
    camera.position.set(0,0,zoomRef.current);
    camera.lookAt(0,0,0);
    const renderer=new THREE.WebGLRenderer({antialias:true});
    renderer.setSize(w,h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
    renderer.setClearColor(0x030610);
    el.appendChild(renderer.domElement);

    const ambLight=new THREE.AmbientLight(0x445566,0.5);
    scene.add(ambLight);
    const dirLight=new THREE.DirectionalLight(0xffeedd,0.9);
    dirLight.position.set(0,2,10);
    scene.add(dirLight);

    const globeGroup=new THREE.Group();
    scene.add(globeGroup);
    // Atmosphere
    globeGroup.add(new THREE.Mesh(
      new THREE.IcosahedronGeometry(R*1.02,3),
      new THREE.MeshBasicMaterial({color:0x3366aa,transparent:true,opacity:0.03,side:THREE.BackSide})
    ));
    // Base sphere
    globeGroup.add(new THREE.Mesh(
      new THREE.IcosahedronGeometry(R*0.998,5),
      new THREE.MeshPhongMaterial({color:new THREE.Color(0.02,0.05,0.12),shininess:5,specular:new THREE.Color(0x040810)})
    ));
    // Tiles
    const tileGroup=new THREE.Group();
    globeGroup.add(tileGroup);
    const roots=FACES.map((_,i)=>new QNode(i,-1,1,-1,1,0));
    const tileMat=new THREE.MeshPhongMaterial({vertexColors:true,shininess:5,specular:new THREE.Color(0x060c14),side:THREE.DoubleSide});

    const st=stateRef.current;
    st.scene=scene;st.camera=camera;st.renderer=renderer;
    st.roots=roots;st.tileMat=tileMat;st.tileGroup=tileGroup;
    st.globeGroup=globeGroup;st.dirLight=dirLight;st.ambLight=ambLight;
    st.meshCache=new Map();st.invMat=new THREE.Matrix4();st.localCamPos=new THREE.Vector3();

    // Earth overlay lines (one per continent)
    const overlayGroup=new THREE.Group();
    overlayGroup.visible=false;
    globeGroup.add(overlayGroup);
    const contNames=Object.keys(CONTINENTS);
    const contLines={};
    for(const name of contNames){
      const pts=CONTINENTS[name];
      const geo=new THREE.BufferGeometry();
      geo.setAttribute("position",new THREE.BufferAttribute(new Float32Array((pts.length+1)*3),3));
      const col=name==="africa"?0xffaa44:0x88aacc;
      const line=new THREE.Line(geo,new THREE.LineBasicMaterial({color:col,transparent:true,opacity:0.5,depthTest:false}));
      line.renderOrder=999;
      overlayGroup.add(line);
      contLines[name]=line;
    }
    st.overlayGroup=overlayGroup;
    st.contLines=contLines;

    // Polity labels (floating text sprites, Reach & Lattice only)
    const markerGroup=new THREE.Group();
    markerGroup.visible=false;
    globeGroup.add(markerGroup);
    const markerSprites=[];
    function makeTextTex(text, fillStyle) {
      const c=document.createElement("canvas");
      c.width=512;c.height=128;
      const ctx=c.getContext("2d");
      ctx.font="bold 64px 'JetBrains Mono','Fira Code',monospace";
      ctx.textAlign="center";ctx.textBaseline="middle";
      ctx.strokeStyle="rgba(0,0,0,0.7)";ctx.lineWidth=5;
      ctx.strokeText(text,256,64);
      ctx.fillStyle=fillStyle;
      ctx.fillText(text,256,64);
      const tex=new THREE.CanvasTexture(c);
      tex.needsUpdate=true;
      return tex;
    }
    const factionColors = {reach:"#ffccaa", lattice:"#aaccff", independent:"#8aa0b8", uncontacted:"#506070", unknown:"#383838", contact:"#ff6644", other:"#9ab0c8"};
    // One label per archipelago, placed at its capital (or best settlement)
    const archBestSettlement = new Map();
    for (const s of world.settlements) {
      const prev = archBestSettlement.get(s.archIdx);
      if (!prev || (s.kind==="capital" && prev.kind!=="capital") || (s.kind===prev.kind && s.importance>prev.importance)) {
        archBestSettlement.set(s.archIdx, s);
      }
    }
    for (let ai = 0; ai < world.history.states.length; ai++) {
      const h = world.history.states[ai];
      const s = archBestSettlement.get(ai);
      if (!s) continue;
      const color = factionColors[h.faction] || factionColors.other;
      const tex = makeTextTex(h.name.toUpperCase(), color);
      const mat = new THREE.SpriteMaterial({map:tex, transparent:true, depthTest:false, opacity: h.faction==="unknown" ? 0.3 : h.faction==="uncontacted" ? 0.5 : 0.85});
      const sprite = new THREE.Sprite(mat);
      sprite.position.set(s.cx*R*1.02, s.cy*R*1.02, s.cz*R*1.02);
      sprite.userData.importance = s.importance;
      sprite.userData.aspect = 4;
      sprite.userData.archIdx = ai;
      markerGroup.add(sprite);
      markerSprites.push(sprite);
    }
    st.markerGroup=markerGroup;
    st.markerSprites=markerSprites;

    // 3D building instances — faction-differentiated materials
    // Reach (Chinese set-dressing): warm dark — timber, ceramic, volcanic stone
    // Lattice (American set-dressing): cool dark — steel, concrete, glass
    // Other: neutral
    const bData = generateBuildingData(world.settlements, world);
    const bGeo = new THREE.BoxGeometry(1, 1, 1);
    bGeo.translate(0, 0.5, 0);
    const factionMats = {
      reach: new THREE.MeshPhongMaterial({color:new THREE.Color(0.14,0.10,0.07),emissive:new THREE.Color(0.08,0.05,0.03),shininess:2,specular:new THREE.Color(0)}),
      lattice: new THREE.MeshPhongMaterial({color:new THREE.Color(0.07,0.09,0.13),emissive:new THREE.Color(0.03,0.05,0.08),shininess:2,specular:new THREE.Color(0)}),
      other: new THREE.MeshPhongMaterial({color:new THREE.Color(0.11,0.105,0.10),emissive:new THREE.Color(0.06,0.055,0.05),shininess:2,specular:new THREE.Color(0)}),
    };
    const buildingGroup = new THREE.Group();
    buildingGroup.visible = false;
    const _dummy = new THREE.Object3D();
    const _up = new THREE.Vector3(0, 1, 0);
    for (const faction of ["reach","lattice","other"]) {
      const subset = bData.filter(b => b.faction === faction);
      if (subset.length === 0) continue;
      const mesh = new THREE.InstancedMesh(bGeo, factionMats[faction], subset.length);
      for (let bi = 0; bi < subset.length; bi++) {
        const b = subset[bi];
        const rad = new THREE.Vector3(b.px, b.py, b.pz);
        _dummy.position.copy(rad).multiplyScalar(R);
        _dummy.quaternion.setFromUnitVectors(_up, rad);
        _dummy.scale.set(b.w, b.h, b.w);
        _dummy.updateMatrix();
        mesh.setMatrixAt(bi, _dummy.matrix);
      }
      mesh.instanceMatrix.needsUpdate = true;
      buildingGroup.add(mesh);
    }
    globeGroup.add(buildingGroup);
    st.buildingGroup = buildingGroup;

    // Plateau graph — great-circle arcs between connected archipelagos
    const graphGroup = new THREE.Group();
    graphGroup.visible = false;
    const edgeFactionColor = (ai, bi) => {
      const fa = world.history.states[ai]?.faction;
      const fb = world.history.states[bi]?.faction;
      if (fa==="reach" && fb==="reach") return 0xffccaa;
      if (fa==="lattice" && fb==="lattice") return 0xaaccff;
      if ((fa==="reach"||fb==="reach") && (fa==="lattice"||fb==="lattice")) return 0xff6644; // the contact edge
      if (fa==="reach" || fb==="reach") return 0x996644;
      if (fa==="lattice" || fb==="lattice") return 0x446688;
      if (fa==="unknown" || fb==="unknown") return 0x282828;
      return 0x556677;
    };
    const ARC_SEGS = 48;
    for (const [ai, bi] of world.plateauEdges) {
      const a = world.archs[ai], b = world.archs[bi];
      const va = new THREE.Vector3(a.cx, a.cy, a.cz);
      const vb = new THREE.Vector3(b.cx, b.cy, b.cz);
      const pts = [];
      for (let t = 0; t <= ARC_SEGS; t++) {
        const p = new THREE.Vector3().copy(va).lerp(vb, t / ARC_SEGS).normalize().multiplyScalar(R * 1.003);
        pts.push(p.x, p.y, p.z);
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(pts), 3));
      const col = edgeFactionColor(ai, bi);
      const isUnknown = world.history.states[ai]?.faction==="unknown" || world.history.states[bi]?.faction==="unknown";
      const line = new THREE.Line(geo, new THREE.LineBasicMaterial({
        color: col, transparent: true, opacity: isUnknown ? 0.15 : 0.45, depthTest: true
      }));
      graphGroup.add(line);
    }
    // Node dots at each archipelago center
    const dotGeo = new THREE.SphereGeometry(0.02, 6, 6);
    for (let i = 0; i < world.archs.length; i++) {
      const h = world.history.states[i];
      const col = h.faction==="reach" ? 0xffccaa : h.faction==="lattice" ? 0xaaccff : h.faction==="unknown" ? 0x383838 : 0x8899aa;
      const dot = new THREE.Mesh(dotGeo, new THREE.MeshBasicMaterial({color: col}));
      dot.position.set(world.archs[i].cx * R * 1.004, world.archs[i].cy * R * 1.004, world.archs[i].cz * R * 1.004);
      graphGroup.add(dot);
    }
    globeGroup.add(graphGroup);
    st.graphGroup = graphGroup;

    const onResize=()=>{const ww=el.clientWidth,hh=el.clientHeight;camera.aspect=ww/hh;camera.updateProjectionMatrix();renderer.setSize(ww,hh);};
    window.addEventListener("resize",onResize);
    setReady(true);
    return ()=>{window.removeEventListener("resize",onResize);renderer.dispose();if(el.contains(renderer.domElement))el.removeChild(renderer.domElement);};
  },[]);

  useEffect(()=>{seaRef.current=seaLevel;},[seaLevel]);
  useEffect(()=>{lightRef.current=lightPct;},[lightPct]);
  useEffect(()=>{bwRef.current=bridgeW;},[bridgeW]);
  useEffect(()=>{overlayRef.current=overlayMode;},[overlayMode]);
  useEffect(()=>{urbanRef.current=urbanMode;},[urbanMode]);

  // Animation loop
  useEffect(()=>{
    if(!ready)return;
    const st=stateRef.current;
    let raf;
    const animate=()=>{
      raf=requestAnimationFrame(animate);
      const {scene,camera,renderer,roots,tileMat,tileGroup,globeGroup,dirLight,ambLight,meshCache,invMat,localCamPos}=st;
      if(!renderer)return;
      const z=zoomRef.current;
      camera.position.set(0,0,z);
      camera.lookAt(0,0,0);
      const lf=lightRef.current/100;
      dirLight.intensity=0.9*lf;
      ambLight.intensity=0.5*lf;
      dirLight.position.copy(camera.position).add(new THREE.Vector3(2,3,0));
      globeGroup.quaternion.copy(globeQuat.current);
      globeGroup.updateMatrixWorld(true);
      invMat.copy(globeGroup.matrixWorld).invert();
      localCamPos.copy(camera.position).applyMatrix4(invMat);
      // LOD
      const leaves=[];
      for(const root of roots)root.collectLeaves(localCamPos,leaves);
      const neededKeys=new Set();
      let maxDepth=0;
      for(const leaf of leaves){
        const key=`${leaf.fi}_${leaf.depth}_${leaf.uMin.toFixed(6)}_${leaf.vMin.toFixed(6)}`;
        leaf._key=key;neededKeys.add(key);
        if(leaf.depth>maxDepth)maxDepth=leaf.depth;
      }
      let newTiles=0;
      for(const leaf of leaves){
        if(meshCache.has(leaf._key))continue;
        if(newTiles>=4)break; // rate limit: max 4 new tiles per frame (625 verts each)
        const geo=generateTileMesh(FACES[leaf.fi].map,leaf.uMin,leaf.uMax,leaf.vMin,leaf.vMax,world,seaRef.current,leaf.depth,bwRef.current*0.01);
        if(urbanRef.current) applyUrbanOverlay(geo,world,seaRef.current,leaf.depth,urbanRef.current);
        const mesh=new THREE.Mesh(geo,tileMat);
        tileGroup.add(mesh);meshCache.set(leaf._key,mesh);newTiles++;
      }
      // Only remove stale tiles when no new tiles were needed (loading settled)
      if(newTiles===0){
        const rm=[];
        meshCache.forEach((mesh,key)=>{if(!neededKeys.has(key)){tileGroup.remove(mesh);mesh.geometry.dispose();rm.push(key);}});
        rm.forEach(k=>meshCache.delete(k));
      }
      setStats({tiles:meshCache.size,depth:maxDepth,verts:meshCache.size*TILE_RES*TILE_RES});
      // Earth overlay — project continents at center of camera view
      const oMode=overlayRef.current;
      if(st.overlayGroup){
        st.overlayGroup.visible=oMode>0;
        if(oMode>0){
          const cd=localCamPos.clone().normalize();
          const cda=[cd.x,cd.y,cd.z];
          for(const [name,line] of Object.entries(st.contLines)){
            if(oMode===1&&name!=="africa"){line.visible=false;continue;}
            line.visible=true;
            const pts=CONTINENTS[name];
            const newPos=buildContinentLine(pts,cda);
            line.geometry.setAttribute("position",new THREE.BufferAttribute(newPos,3));
            line.geometry.attributes.position.needsUpdate=true;
          }
        }
      }
      // Settlement markers — constant angular size (mode 2 only)
      if(st.markerGroup){
        const showMarkers=urbanRef.current>=2;
        st.markerGroup.visible=showMarkers;
        if(showMarkers&&st.markerSprites){
          const camDir = localCamPos.clone().normalize();
          for(const sp of st.markerSprites){
            // Hide labels on the far hemisphere
            const labelDir = sp.position.clone().normalize();
            const facing = labelDir.dot(camDir);
            sp.visible = facing > -0.05; // slight tolerance so edge labels don't flicker
            if(!sp.visible) continue;
            const dx=localCamPos.x-sp.position.x, dy=localCamPos.y-sp.position.y, dz=localCamPos.z-sp.position.z;
            const d=Math.sqrt(dx*dx+dy*dy+dz*dz);
            const s=d*0.04*(0.6+sp.userData.importance*0.4);
            const asp=sp.userData.aspect||1;
            sp.scale.set(s*asp,s,1);
          }
        }
      }
      // Building structures
      if(st.buildingGroup) st.buildingGroup.visible=urbanRef.current>=1;
      if(st.graphGroup) st.graphGroup.visible=urbanRef.current>=1;
      renderer.render(scene,camera);
    };
    animate();
    return ()=>cancelAnimationFrame(raf);
  },[ready,world]);

  // Flush cache on sea level change
  useEffect(()=>{
    if(!ready)return;
    const st=stateRef.current;
    st.meshCache.forEach(m=>{st.tileGroup.remove(m);m.geometry.dispose();});
    st.meshCache.clear();
  },[seaLevel,bridgeW,urbanMode,ready]);

  // ── ARCBALL ROTATION ──
  function raycastToSphere(clientX,clientY,quatOverride){
    const st=stateRef.current;
    if(!st.renderer||!st.camera)return null;
    const el=mountRef.current;if(!el)return null;
    const rect=el.getBoundingClientRect();
    const ndcX=((clientX-rect.left)/rect.width)*2-1;
    const ndcY=-((clientY-rect.top)/rect.height)*2+1;
    const cam=st.camera;
    const rayDir=new THREE.Vector3(ndcX,ndcY,0.5).unproject(cam).sub(cam.position).normalize();
    const rayOrigin=cam.position.clone();
    const q=quatOverride||globeQuat.current;
    const invQ=q.clone().invert();
    rayOrigin.applyQuaternion(invQ);
    rayDir.applyQuaternion(invQ);
    const a=rayDir.dot(rayDir), b=rayOrigin.dot(rayDir), c=rayOrigin.dot(rayOrigin)-R*R;
    const disc=b*b-a*c;
    if(disc<0)return null;
    const t=(-b-Math.sqrt(disc))/a;
    if(t<0)return null;
    return rayOrigin.add(rayDir.multiplyScalar(t)).normalize();
  }

  const onPointerDown=useCallback(e=>{
    clickStart.current={x:e.clientX,y:e.clientY};
    const hit=raycastToSphere(e.clientX,e.clientY);
    if(hit){dragData.current={active:true,startPoint:hit,startQuat:globeQuat.current.clone(),lastGood:{x:e.clientX,y:e.clientY}};}
    else{dragData.current={active:true,startPoint:null,startQuat:null,lastGood:null};lastM.current={x:e.clientX,y:e.clientY};}
  },[]);

  const onPointerMove=useCallback(e=>{
    const dd=dragData.current;
    if(!dd.active)return;
    if(dd.startPoint&&dd.startQuat){
      const hit=raycastToSphere(e.clientX,e.clientY,dd.startQuat);
      if(hit){
        const p1=dd.startPoint, p2=hit;
        const axis=new THREE.Vector3().crossVectors(p1,p2);
        const len=axis.length();
        if(len>0.0001){
          axis.divideScalar(len);
          const angle=Math.acos(Math.max(-1,Math.min(1,p1.dot(p2))));
          const rot=new THREE.Quaternion().setFromAxisAngle(axis,angle);
          globeQuat.current.copy(dd.startQuat).multiply(rot);
        }
        dd.lastGood={x:e.clientX,y:e.clientY};
      } else {
        dd.startPoint=null;dd.startQuat=null;
        lastM.current=dd.lastGood||{x:e.clientX,y:e.clientY};
      }
    } else {
      const dx=e.clientX-lastM.current.x, dy=e.clientY-lastM.current.y;
      lastM.current={x:e.clientX,y:e.clientY};
      const qY=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0,1,0),dx*0.004);
      const qX=new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1,0,0),dy*0.004);
      globeQuat.current.premultiply(new THREE.Quaternion().multiplyQuaternions(qX,qY));
    }
  },[]);

  const onPointerUp=useCallback(e=>{
    const dd=dragData.current;
    dd.active=false;
    // Detect click (pointer barely moved)
    const dx=e.clientX-clickStart.current.x, dy=e.clientY-clickStart.current.y;
    if(Math.abs(dx)<5 && Math.abs(dy)<5 && stateRef.current.markerSprites && urbanRef.current>=2){
      const st=stateRef.current;
      const el=mountRef.current; if(!el)return;
      const rect=el.getBoundingClientRect();
      const mouse=new THREE.Vector2(
        ((e.clientX-rect.left)/rect.width)*2-1,
        -((e.clientY-rect.top)/rect.height)*2+1
      );
      const raycaster=new THREE.Raycaster();
      raycaster.far=200;
      raycaster.params.Points={threshold:0.5};
      raycaster.setFromCamera(mouse,st.camera);
      const hits=raycaster.intersectObjects(st.markerSprites,false);
      if(hits.length>0){
        const ai=hits[0].object.userData.archIdx;
        if(ai!==undefined) setSelectedArch(prev=>prev===ai?null:ai);
      } else {
        setSelectedArch(null);
      }
    }
  },[]);
  const onWheel=useCallback(e=>{e.preventDefault();const z=zoomRef.current;const nz=Math.max(R*1.007,Math.min(60,z*(1+e.deltaY*0.001)));zoomRef.current=nz;setZoom(nz);},[]);

  const altitude=Math.max(0,((zoomRef.current-R)*29440/R)).toFixed(0);
  const isGlacial=seaLevel<-50;

  return (
    <div style={{width:"100%",height:"100vh",background:"#030610",color:"#b0c4d8",fontFamily:"'JetBrains Mono','Fira Code',monospace",display:"flex",flexDirection:"column",overflow:"hidden"}}>
      {/* Header */}
      <div style={{padding:"10px 20px 8px",borderBottom:"1px solid #0f1a28",flexShrink:0,display:"flex",justifyContent:"space-between",alignItems:"flex-start",background:"linear-gradient(180deg,#060b14,#030610)"}}>
        <div>
          <div style={{fontSize:"9px",color:"#8aa0b8",letterSpacing:"3px",textTransform:"uppercase",marginBottom:2}}>Quadtree LOD Terrain Engine</div>
          <div style={{fontSize:"15px",color:"#d4e0ec",fontWeight:600}}>AEOLIA — ADAPTIVE SURFACE</div>
          <div style={{fontSize:"9px",color:"#8aa0b8",marginTop:2}}>
            {stats.tiles} tiles · {stats.verts.toLocaleString()} verts · depth {stats.depth}/{MAX_DEPTH} · alt ~{Number(altitude).toLocaleString()} km
          </div>
        </div>
        <div style={{fontSize:"8px",color:"#607888",textAlign:"right",lineHeight:1.6}}>CUBE-SPHERE<br/>{TILE_RES}×{TILE_RES}/tile</div>
      </div>

      {/* Content */}
      <div style={{flex:1,display:"flex",minHeight:0}}>
        {/* Political Map (left sidebar) */}
        <div style={{width:260,flexShrink:0,borderRight:"1px solid #0f1a28",overflowY:"auto",
          background:"linear-gradient(180deg,#050a12,#030610)",fontSize:"9px",lineHeight:1.5,display:"flex",flexDirection:"column"}}>
          <div style={{padding:"10px 12px 6px",borderBottom:"1px solid #0f1a28",flexShrink:0}}>
            <div style={{fontSize:"10px",color:"#daa540",letterSpacing:"2px",textTransform:"uppercase",fontWeight:600,marginBottom:4}}>Political Map</div>
            <div style={{fontSize:"8px",color:"#8aa0b8"}}>{world.history.log.length - 1} archipelagos · Dark Forest breaks {world.history.dfYear ? Math.abs(world.history.dfYear) + " BP" : "at present"}</div>
          </div>
          <div style={{flex:1,overflowY:"auto",padding:"6px 10px"}}>
            {world.history.log.map((entry,idx)=>{
              const fColor = {reach:"#ffccaa",lattice:"#aaccff",independent:"#9ab0c8",uncontacted:"#607888",unknown:"#484848",contact:"#ff6644",era:"#daa540",other:"#9ab0c8"}[entry.faction]||"#9ab0c8";
              const isEra = entry.faction==="era";
              const isContact = entry.status==="contact";
              if (isEra) {
                const yrLabel = entry.contactYr != null
                  ? (entry.contactYr < 0 ? Math.abs(entry.contactYr).toLocaleString() + ' BP' : 'present')
                  : null;
                return <div key={idx} style={{margin:"10px 0 4px",padding:"5px 0 4px",borderBottom:"1px solid #1a2a3a"}}>
                  <div style={{fontSize:"9px",color:"#daa540",fontWeight:700,letterSpacing:"2px",textTransform:"uppercase"}}>{entry.label}</div>
                  {yrLabel && <div style={{fontSize:"7px",color:"#607888",marginTop:1,letterSpacing:"0.5px"}}>{yrLabel}</div>}
                </div>;
              }
              const icon = entry.status==="core"?"\u2605":entry.status==="colony"?"\u25A0":entry.status==="absorbed"?"\u25A3":entry.status==="garrison"?"\u25B2":entry.status==="trade"?"\u25C6":entry.status==="unknown"?"\u2022":isContact?"\u26A0":"\u25CF";
              return <div key={idx} style={{marginBottom:isContact?0:4, paddingLeft:8, borderLeft:`2px solid ${fColor}`,
                marginTop:isContact?10:0, paddingTop:isContact?8:0, borderTop:isContact?"1px solid #1a2a3a":"none"}}>
                <div style={{color:fColor,fontWeight:entry.status==="core"||isContact?600:400,fontSize:isContact?"10px":"9px"}}>
                  <span style={{marginRight:4}}>{icon}</span>{entry.name}
                  {!isContact && entry.arch>=0 && <span style={{color:"#607888",fontWeight:400,marginLeft:4}}>({entry.rDist}R·{entry.lDist}L)</span>}
                </div>
                <div style={{color:isContact?"#ff9977":"#9ab0c8",fontSize:"7px",marginTop:1}}>{entry.label}</div>
              </div>;
            })}
          </div>
        </div>

        <div style={{flex:1,position:"relative"}}>
          <div ref={mountRef} style={{width:"100%",height:"100%",cursor:"grab"}}
            onPointerDown={onPointerDown} onPointerMove={onPointerMove}
            onPointerUp={onPointerUp} onPointerLeave={onPointerUp} onWheel={onWheel} />
          {selectedArch!==null && (() => {
            const h = world.history.states[selectedArch];
            if (!h) return null;
            const archLog = world.history.log.filter(e => e.arch === selectedArch);
            const sub = world.substrate?.[selectedArch];
            const fColor = {reach:"#ffccaa",lattice:"#aaccff",independent:"#9ab0c8",unknown:"#484848",other:"#9ab0c8"}[h.faction]||"#9ab0c8";
            const cropIcon = {paddi:"[P]",emmer:"[E]",taro:"[T]",nori:"[N]",sago:"[S]",papa:"[Pa]",foraging:"[?]"};
            const modeColors = {"asiatic":"#e8c474","mercantile":"#74c4e8","tributary":"#c4e874","petty commodity":"#e8a074","communal":"#a0e8a0","household":"#c4a0e8","frontier":"#888","tributary empire":"#d4a040","state capital":"#e84040"};
            return <div style={{position:"absolute",top:16,left:16,width:340,maxHeight:"calc(100% - 32px)",
              background:"rgba(5,10,18,0.95)",border:"1px solid #1a2a3a",borderRadius:4,
              overflow:"hidden",display:"flex",flexDirection:"column",
              fontFamily:"'JetBrains Mono','Fira Code',monospace",fontSize:"9px",color:"#b0c4d8",
              boxShadow:"0 4px 24px rgba(0,0,0,0.6)"}}>
              <div style={{padding:"12px 14px 8px",borderBottom:"1px solid #1a2a3a",flexShrink:0}}>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                  <div style={{color:fColor,fontSize:"12px",fontWeight:700,letterSpacing:"1.5px",textTransform:"uppercase"}}>{h.name}</div>
                  <div onClick={()=>setSelectedArch(null)} style={{cursor:"pointer",color:"#607888",fontSize:"14px",lineHeight:1,padding:"0 2px"}}>&times;</div>
                </div>
                <div style={{color:"#8aa0b8",fontSize:"8px",marginTop:4,lineHeight:1.5}}>
                  {h.status} · pop {h.population?.toLocaleString()} · tech {h.tech} · {h.faction}
                </div>
              </div>
              {sub && <div style={{padding:"8px 14px",borderBottom:"1px solid #0f1a28",flexShrink:0}}>
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"6px 12px",fontSize:"8px",lineHeight:1.5}}>
                  <div>
                    <div style={{color:"#daa540",fontWeight:600,fontSize:"7px",letterSpacing:"1px",textTransform:"uppercase",marginBottom:2}}>Climate</div>
                    <div style={{color:"#9ab0c8"}}>{sub.climate.latitude.toFixed(1)}° · {sub.climate.wind_belt}</div>
                    <div style={{color:"#9ab0c8"}}>{sub.climate.mean_temp.toFixed(0)}°C · {Math.round(sub.climate.effective_rainfall)}mm</div>
                    <div style={{color:"#9ab0c8"}}>tidal {sub.climate.tidal_range.toFixed(1)}m · fish {(sub.climate.fisheries_richness*100).toFixed(0)}%</div>
                  </div>
                  <div>
                    <div style={{color:"#daa540",fontWeight:600,fontSize:"7px",letterSpacing:"1px",textTransform:"uppercase",marginBottom:2}}>Agriculture</div>
                    <div style={{color:"#c8d4e0"}}>{cropIcon[sub.crops.primary_crop]||""} <span style={{fontWeight:600}}>{sub.crops.primary_crop}</span> (yield {(sub.crops.primary_yield||0).toFixed(1)})</div>
                    {sub.crops.secondary_crop && <div style={{color:"#8aa0b8"}}>+ {sub.crops.secondary_crop}</div>}
                    {sub.crops.can_grow && <div style={{color:"#607888",fontSize:"7px"}}>{Object.entries(sub.crops.can_grow).filter(([,v])=>v).map(([k])=>k).join(" · ")}</div>}
                  </div>
                  <div>
                    <div style={{color:"#daa540",fontWeight:600,fontSize:"7px",letterSpacing:"1px",textTransform:"uppercase",marginBottom:2}}>Trade</div>
                    {sub.trade_goods.stimulant && <div style={{color:"#9ab0c8"}}>{sub.trade_goods.stimulant} <span style={{color:"#607888"}}>(stim)</span></div>}
                    {sub.trade_goods.fiber && <div style={{color:"#9ab0c8"}}>{sub.trade_goods.fiber} <span style={{color:"#607888"}}>(fiber)</span></div>}
                    {sub.trade_goods.protein && <div style={{color:"#9ab0c8"}}>{sub.trade_goods.protein} <span style={{color:"#607888"}}>(prot)</span></div>}
                    {sub.trade_goods.nori_export > 0.05 && <div style={{color:"#9ab0c8"}}>nori {(sub.trade_goods.nori_export*100).toFixed(0)}%</div>}
                    {!sub.trade_goods.stimulant && !sub.trade_goods.fiber && !sub.trade_goods.protein && <div style={{color:"#607888",fontStyle:"italic"}}>subsistence only</div>}
                  </div>
                  <div>
                    <div style={{color:"#daa540",fontWeight:600,fontSize:"7px",letterSpacing:"1px",textTransform:"uppercase",marginBottom:2}}>Minerals</div>
                    <div style={{color:"#9ab0c8"}}>
                      {sub.minerals.Fe && <span style={{marginRight:4}}>Fe</span>}
                      {sub.minerals.Cu && <span style={{color:"#e8a040",marginRight:4}}>Cu</span>}
                      {sub.minerals.Au && <span style={{color:"#e8d040",marginRight:4}}>Au</span>}
                      {sub.minerals.Pu && <span style={{color:"#e84040",fontWeight:700}}>Pu</span>}
                      {sub.minerals.C > 0 && <span style={{color:"#a0c880",marginLeft:2}}>C({sub.minerals.C.toFixed(2)})</span>}
                      {!sub.minerals.Cu && !sub.minerals.Au && !sub.minerals.Pu && !sub.minerals.C && <span style={{color:"#607888"}}>Fe only</span>}
                    </div>
                  </div>
                  <div>
                    <div style={{color:"#daa540",fontWeight:600,fontSize:"7px",letterSpacing:"1px",textTransform:"uppercase",marginBottom:2}}>Political Culture</div>
                    <div style={{color:"#c8d4e0",fontWeight:600}}>{sub.culture}</div>
                    {sub.culture_pos && <div style={{color:"#8aa0b8"}}>CI {sub.culture_pos[0].toFixed(2)} · IO {sub.culture_pos[1].toFixed(2)}</div>}
                  </div>
                  <div>
                    <div style={{color:"#daa540",fontWeight:600,fontSize:"7px",letterSpacing:"1px",textTransform:"uppercase",marginBottom:2}}>Climate Zone</div>
                    <div style={{color:"#9ab0c8",fontWeight:600}}>{sub.climate.climate_zone?.replace(/_/g,' ')}</div>
                    <div style={{color:"#8aa0b8"}}>warmth {(sub.climate.ocean_warmth*100).toFixed(0)}% · up {(sub.climate.upwelling||0).toFixed(2)}</div>
                  </div>
                </div>
              </div>}
              <div style={{flex:1,overflowY:"auto",padding:"8px 14px"}}>
                <div style={{color:"#daa540",fontWeight:600,fontSize:"7px",letterSpacing:"1px",textTransform:"uppercase",marginBottom:6}}>History</div>
                {archLog.length === 0
                  ? <div style={{color:"#607888",fontStyle:"italic",padding:"8px 0"}}>No recorded history</div>
                  : archLog.map((entry,idx) => {
                    const eColor = {reach:"#ffccaa",lattice:"#aaccff",independent:"#9ab0c8",unknown:"#484848"}[entry.faction]||"#9ab0c8";
                    const icon = entry.status==="core"?"\u2605":entry.status==="colony"?"\u25A0":entry.status==="garrison"?"\u25B2":entry.status==="contacted"?"\u25CF":entry.status==="unknown"?"\u2022":"\u25C6";
                    return <div key={idx} style={{marginBottom:8,paddingLeft:8,borderLeft:`2px solid ${eColor}`}}>
                      <div style={{color:eColor,fontWeight:500,fontSize:"9px"}}>
                        <span style={{marginRight:4}}>{icon}</span>
                        {entry.contactYr ? (entry.contactYr < 0 ? Math.abs(entry.contactYr) + " BP" : entry.contactYr + " AP") : "present"}
                      </div>
                      <div style={{color:"#9ab0c8",fontSize:"7px",marginTop:2,lineHeight:1.4}}>{entry.label}</div>
                    </div>;
                  })
                }
              </div>
            </div>;
          })()}
        </div>

        {/* Panel */}
        <div style={{width:260,flexShrink:0,borderLeft:"1px solid #0f1a28",overflowY:"auto",padding:"12px 14px",
          background:"linear-gradient(180deg,#050a12,#030610)",fontSize:"10px",lineHeight:1.7}}>

          <div style={{marginBottom:12}}>
            <div style={{fontSize:"10px",color:"#daa540",letterSpacing:"2px",textTransform:"uppercase",marginBottom:6,fontWeight:600}}>World Seed</div>
            <input type="text" defaultValue={seed}
              placeholder={String(seed)}
              onKeyDown={e=>{if(e.key==="Enter"){const v=parseInt(e.target.value);if(!isNaN(v)&&onSeedChange)onSeedChange(v);}}}
              style={{width:"100%",padding:"4px 6px",fontSize:"9px",fontFamily:"inherit",
                background:"#0a1218",border:"1px solid #1a2a3a",color:"#c8d4e0",
                letterSpacing:"1px",boxSizing:"border-box"}} />
            <div style={{fontSize:"7px",color:"#8aa0b8",marginTop:3,lineHeight:1.5}}>
              Press Enter to regenerate · Reach=arch {world.reachArch}, Lattice=arch {world.latticeArch}
            </div>
          </div>

          <div style={{marginBottom:12}}>
            <div style={{fontSize:"10px",color:"#daa540",letterSpacing:"2px",textTransform:"uppercase",marginBottom:6,fontWeight:600}}>Camera</div>
            <div style={{fontSize:"9px",color:"#9ab0c8",lineHeight:1.6}}>
              Scroll to zoom · Drag to rotate<br/>
              Distance: {zoom.toFixed(1)} (~{Number(altitude).toLocaleString()} km)<br/>
              {zoom<=R*1.2?"* ground":zoom<=R*2?"* island":zoom<=R*4?"* archipelago":"* orbital"}
            </div>
          </div>

          <div style={{marginBottom:12}}>
            <div style={{fontSize:"10px",color:"#daa540",letterSpacing:"2px",textTransform:"uppercase",marginBottom:6,fontWeight:600}}>Sea Level</div>
            <input type="range" min={-220} max={0} value={seaLevel}
              onChange={e=>setSeaLevel(Number(e.target.value))}
              style={{width:"100%",accentColor:"#2a5a8a"}} />
            <div style={{display:"flex",justifyContent:"space-between",fontSize:"8px",color:"#8aa0b8",marginTop:1}}>
              <span>−220m</span>
              <span style={{color:isGlacial?"#c4813a":"#4a8a5a"}}>{seaLevel}m{isGlacial&&" · BRIDGES"}</span>
              <span>0m</span>
            </div>
          </div>

          <div style={{marginBottom:12}}>
            <div style={{fontSize:"10px",color:"#daa540",letterSpacing:"2px",textTransform:"uppercase",marginBottom:6,fontWeight:600}}>Land Bridges</div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:"8px",color:"#9ab0c8",marginBottom:2}}>
              <span>Corridor width</span><span>{(bridgeW*0.01).toFixed(2)} rad</span>
            </div>
            <input type="range" min={2} max={50} value={bridgeW}
              onChange={e=>setBridgeW(Number(e.target.value))}
              style={{width:"100%",accentColor:"#66aa88"}} />
            <div style={{display:"flex",justifyContent:"space-between",fontSize:"7px",color:"#8aa0b8"}}>
              <span>0.02 rad</span><span>0.50 rad</span>
            </div>
          </div>

          <div style={{marginBottom:12}}>
            <div style={{fontSize:"10px",color:"#daa540",letterSpacing:"2px",textTransform:"uppercase",marginBottom:6,fontWeight:600}}>Lighting</div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:"8px",color:"#9ab0c8",marginBottom:2}}>
              <span>Intensity</span><span>{lightPct}%</span>
            </div>
            <input type="range" min={10} max={500} value={lightPct}
              onChange={e=>setLightPct(Number(e.target.value))}
              style={{width:"100%",accentColor:"#daa540"}} />
          </div>

          <div style={{marginBottom:12}}>
            <div style={{fontSize:"10px",color:"#daa540",letterSpacing:"2px",textTransform:"uppercase",marginBottom:6,fontWeight:600}}>Scale Reference</div>
            <button onClick={()=>setOverlayMode((overlayMode+1)%3)} style={{
              width:"100%",padding:"6px 0",fontSize:"9px",fontFamily:"inherit",cursor:"pointer",
              background:overlayMode>0?"#2a3a2a":"#0a1218",border:"1px solid "+(overlayMode>0?"#4a8a4a":"#1a2a3a"),
              color:overlayMode>0?"#88cc88":"#9ab0c8",letterSpacing:"1px",
            }}>
              {overlayMode===0?"▢ OFF":overlayMode===1?"▣ AFRICA ONLY":"▣ ALL EARTH"}
            </button>
            <div style={{fontSize:"7px",color:"#8aa0b8",marginTop:3,lineHeight:1.5}}>
              Projects Earth landmasses (to scale) at screen center.<br/>
              Earth→Aeolia ratio: {EARTH_TO_AEOLIA.toFixed(3)}×
            </div>
          </div>

          <div style={{marginBottom:12}}>
            <div style={{fontSize:"10px",color:"#daa540",letterSpacing:"2px",textTransform:"uppercase",marginBottom:6,fontWeight:600}}>Urbanization</div>
            <button onClick={()=>setUrbanMode((urbanMode+1)%3)} style={{
              width:"100%",padding:"6px 0",fontSize:"9px",fontFamily:"inherit",cursor:"pointer",
              background:urbanMode>0?"#2a2a3a":"#0a1218",border:"1px solid "+(urbanMode>0?"#7a6a9a":"#1a2a3a"),
              color:urbanMode>0?"#bb99dd":"#9ab0c8",letterSpacing:"1px",
            }}>
              {urbanMode===0?"▢ OFF":urbanMode===1?"▣ NUCLEAR ERA":"▣ NUCLEAR ERA + LABELS"}
            </button>
            <div style={{fontSize:"7px",color:"#8aa0b8",marginTop:3,lineHeight:1.5}}>
              Harbor cities derived from terrain concavities.<br/>
              {urbanMode>0?<>
                {world.settlements.length} settlements<br/>
                <span style={{color:"#ffccaa"}}>■</span> Reach ({world.history.states.filter(h=>h.faction==="reach").length}) · <span style={{color:"#aaccff"}}>■</span> Lattice ({world.history.states.filter(h=>h.faction==="lattice").length}) · <span style={{color:"#484848"}}>?</span> Beyond ({world.history.states.filter(h=>h.faction==="unknown").length})
              </>:"Toggle to show urban features"}
            </div>
          </div>

          <div style={{marginBottom:12}}>
            <div style={{fontSize:"10px",color:"#daa540",letterSpacing:"2px",textTransform:"uppercase",marginBottom:6,fontWeight:600}}>Bathymetry</div>
            {[["Abyss","#030a1c"],["Deep","#0a1838"],["Mid ocean","#0f2858"],["Plateau","#1a3a72"],
              ["Shallow","#2d5688"],["Coast","#3c6050"],["Lowland","#425838"],["Slope","#4a4430"],["Summit","#787058"]
            ].map(([l,c])=>(
              <div key={l} style={{display:"flex",alignItems:"center",gap:6,marginBottom:1}}>
                <span style={{width:10,height:7,background:c,display:"inline-block",border:"1px solid #0f1a28"}}/>
                <span style={{fontSize:"8px",color:"#9ab0c8"}}>{l}</span>
              </div>
            ))}
          </div>

          <div style={{background:"#060b14",border:"1px solid #0f1a28",padding:"8px 10px",fontSize:"8px",color:"#8aa0b8",lineHeight:1.7}}>
            <div style={{color:"#daa540",marginBottom:4,fontWeight:600}}>BUILD STATUS</div>
            <div>✅ Quadtree LOD</div><div>✅ Cube-sphere</div><div>✅ Arcball rotation</div>
            <div>✅ Naturalistic coloring</div><div>✅ Sea-level slider</div><div>✅ Camera-following light</div>
            <div>✅ Urban overlay (Pass B)</div>
            <div style={{color:"#607888",marginTop:4}}>⬜ Ocean shader</div><div style={{color:"#607888"}}>⬜ Atmosphere</div>
            <div style={{color:"#607888"}}>⬜ Era timeline</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── WRAPPER: seed state + remount on change ─────────────
export default function AeoliaLOD() {
  const [seed, setSeed] = useState(42);
  return <AeoliaLODInner key={seed} seed={seed} onSeedChange={setSeed} />;
}
