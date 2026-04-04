  return {archs, edges, history, substrate, settlements: detectSettlements(archs, history.states), seed: seed||42, reachArch: REACH_ARCH, latticeArch: LATTICE_ARCH, plateauEdges};
}

// ─── STATIC SUBSTRATE CASCADE ────────────────────────────
// Pass 1: computed once at world generation from arch geometry.
// arch position → climate → crop → trade goods → political culture
// → mode of production → minerals → narrative substrate
function computeSubstrate(archs, plateauEdges, seed) {
  const rng = mulberry32((seed || 42) * 47 + 2024);
  const N = archs.length;

  // ── Per-arch edge statistics ──
  const edgeCount = new Array(N).fill(0);
  const edgeLengths = Array.from({length:N}, ()=>[]);
  for (const [a,b] of plateauEdges) {
    edgeCount[a]++; edgeCount[b]++;
    const dot = archs[a].cx*archs[b].cx + archs[a].cy*archs[b].cy + archs[a].cz*archs[b].cz;
    const angle = Math.acos(Math.max(-1, Math.min(1, dot)));
    edgeLengths[a].push(angle);
    edgeLengths[b].push(angle);
  }
  const allLens = edgeLengths.flat();
  const maxEdgeLen = allLens.length > 0 ? Math.max(...allLens) : 0.5;

  // ── Gyre computation: per latitude band, find arch distribution ──
  // Simplified: within each band, widest longitudinal gap = open ocean
  // Western side of gap = warm current. Eastern = cool. In gap = center.
  function computeGyrePosition(arch, allArchs) {
    const lat = Math.asin(Math.max(-1,Math.min(1,arch.cy))) * 180/Math.PI;
    const absLat = Math.abs(lat);
    const bandArchs = allArchs.filter(a => {
      const aLat = Math.abs(Math.asin(Math.max(-1,Math.min(1,a.cy))) * 180/Math.PI);
      return Math.abs(aLat - absLat) < 15;
    });
    if (bandArchs.length < 2) return 0.5;
    const lons = bandArchs.map(a => Math.atan2(a.cz, a.cx) * 180/Math.PI).sort((a,b)=>a-b);
    let maxGap = 0, gapCenter = 0;
    for (let j = 0; j < lons.length; j++) {
      const next = j < lons.length-1 ? lons[j+1] : lons[0] + 360;
      const gap = next - lons[j];
      if (gap > maxGap) { maxGap = gap; gapCenter = lons[j] + gap/2; }
    }
    if (maxGap < 10) return 0.5; // no clear gyre structure
    const myLon = Math.atan2(arch.cz, arch.cx) * 180/Math.PI;
    const relPos = ((myLon - gapCenter + 540) % 360) / 360;
    return Math.max(0, Math.min(1, relPos));
  }

  const substrates = [];

  for (let i = 0; i < N; i++) {
    const arch = archs[i];
    const lat = Math.asin(Math.max(-1,Math.min(1,arch.cy))) * 180/Math.PI;
    const absLat = Math.abs(lat);
    const size = arch.shelfR / 0.12;
    const peakCount = arch.peaks.length;
    const avgH = arch.peaks.reduce((s,p)=>s+p.h, 0) / (peakCount * ISLAND_MAX_HEIGHT);
    const avgEdge = edgeLengths[i].length > 0 ? edgeLengths[i].reduce((s,v)=>s+v,0)/edgeLengths[i].length : 0.5;

    // ════════════════════════════════════════════════
    // CLIMATE MODEL
    // ════════════════════════════════════════════════
    const windBelt = absLat < 12 ? "doldrums" :
                     absLat < 28 ? "trades" :
                     absLat < 35 ? "subtropical" :
                     absLat < 55 ? "westerlies" :
                     absLat < 65 ? "subpolar" : "polar";

    const baseRain = windBelt==="doldrums" ? 2800 :
                     windBelt==="trades" ? 2200 :
                     windBelt==="subtropical" ? 600 :
                     windBelt==="westerlies" ? 1400 :
                     windBelt==="subpolar" ? 1100 : 300;

    const orographicBonus = 1 + avgH * 1.8;
    const gyrePos = computeGyrePosition(arch, archs);
    const oceanWarmth = Math.max(0, Math.min(1,
      gyrePos < 0.3 ? 0.8 + gyrePos :
      gyrePos > 0.7 ? 0.3 - (gyrePos-0.7) : 0.4 + gyrePos*0.2
    ));
    const moistureBonus = 1 + Math.max(0, oceanWarmth - 0.4) * 0.4;
    const effectiveRainfall = baseRain * orographicBonus * moistureBonus * 1.4; // 1.4 = Aeolia atm multiplier

    const meanTemp = 28 - absLat * 0.45 + (oceanWarmth - 0.5) * 4;
    const seasonalRange = absLat * 0.15 * 0.7; // maritime moderation

    // Cluster density for tidal computation
    const nearbyArchs = archs.filter(a => {
      const d = arch.cx*a.cx + arch.cy*a.cy + arch.cz*a.cz;
      return d > 0.95 && a !== arch;
    }).length;
    const clusterDensity = Math.min(1, nearbyArchs / 5);
    const tidalRange = (2 + arch.shelfR * 30 + clusterDensity * 4) * (0.8 + Math.abs(Math.sin(absLat*Math.PI/180))*0.4);

    // Upwelling
    const upwelling = (gyrePos > 0.7 ? 0.4 : 0) + (absLat < 5 ? 0.3 : 0) + edgeCount[i] * 0.08;
    const fisheriesRichness = Math.min(1, upwelling * 0.5 + effectiveRainfall * 0.0001 + edgeCount[i]*0.05);

    const climate = {
      latitude: lat, absLatitude: absLat, windBelt, meanTemp, seasonalRange,
      baseRainfall: baseRain, effectiveRainfall, tidalRange,
      oceanWarmth, gyrePosition: gyrePos, upwelling, fisheriesRichness,
      climateZone: meanTemp > 24 && effectiveRainfall > 2000 ? "tropical_wet" :
                   meanTemp > 24 && effectiveRainfall < 1000 ? "tropical_dry" :
                   meanTemp > 10 && effectiveRainfall > 1200 ? "temperate_wet" :
                   meanTemp > 10 ? "temperate_dry" :
                   meanTemp > 2 ? "subpolar" : "polar_fringe"
    };

    // ════════════════════════════════════════════════
    // CROP ASSIGNMENT (§10a canGrow predicates)
    // ════════════════════════════════════════════════
    const canGrow = {};
    canGrow.paddi = meanTemp >= 20 && effectiveRainfall >= 1200 && tidalRange >= 2.0 && arch.shelfR >= 0.08 && absLat <= 28;
    canGrow.emmer = meanTemp >= 8 && meanTemp <= 24 && effectiveRainfall >= 400 && effectiveRainfall <= 2000 && absLat >= 20 && absLat <= 55;
    canGrow.taro  = meanTemp >= 21 && seasonalRange <= 4 && effectiveRainfall >= 1500 && absLat <= 20;
    canGrow.nori  = meanTemp >= 5 && meanTemp <= 22 && edgeCount[i] >= 1 && upwelling >= 0.2;
    canGrow.sago  = meanTemp >= 24 && effectiveRainfall >= 2000 && absLat <= 15 && arch.shelfR >= 0.04;
    canGrow.papa  = meanTemp >= 2 && meanTemp <= 18 && effectiveRainfall >= 400 && absLat >= 35;

    // Primary crop: highest-yield growable crop
    // Yield approximations for ranking
    const yields = {};
    if (canGrow.paddi) yields.paddi = 5.0 * Math.min(1,(meanTemp-18)/15) * Math.min(1,effectiveRainfall/1800) * Math.min(1,tidalRange/5);
    if (canGrow.emmer) yields.emmer = 2.5 * (1-Math.abs(meanTemp-16)/20) * (1-Math.abs(effectiveRainfall-700)/1500);
    if (canGrow.taro)  yields.taro  = 3.0 * Math.min(1,(meanTemp-20)/8) * Math.min(1,effectiveRainfall/2000);
    if (canGrow.nori)  yields.nori  = 1.5 * Math.min(1,upwelling*2) * Math.min(1,edgeCount[i]/3) * 2.0;
    if (canGrow.sago)  yields.sago  = 4.0 * Math.min(1,effectiveRainfall/2500) * Math.min(1,arch.shelfR/0.10);
    if (canGrow.papa)  yields.papa  = 3.5 * (1-Math.abs(meanTemp-12)/15) * Math.min(1,effectiveRainfall/600);

    const cropEntries = Object.entries(yields).sort((a,b)=>b[1]-a[1]);
    const primaryCrop = cropEntries.length > 0 ? cropEntries[0][0] : "foraging";
    const secondaryCrop = cropEntries.length > 1 ? cropEntries[1][0] : null;
    const primaryYield = cropEntries.length > 0 ? cropEntries[0][1] : 0.5;

    // ════════════════════════════════════════════════
    // TRADE GOODS (§10b)
    // ════════════════════════════════════════════════
    const stimulantMap = {paddi:"char",emmer:"qahwa",taro:"awa",sago:"pinang",papa:"aqua",nori:null,foraging:null};
    const fiberMap = {paddi:"seric",emmer:"fell",taro:"tapa",sago:"tapa",nori:"byssus",papa:"qivu",foraging:null};
    const proteinMap = {paddi:"kerbau",emmer:"kri",taro:"moa",sago:"moa",nori:null,papa:null,foraging:null};

    const stimulant = stimulantMap[primaryCrop] || null;
    const fiber = fiberMap[primaryCrop] || null;
    const protein = proteinMap[primaryCrop] || null;

    const tradeGoods = {
      stimulant: {type: stimulant, production: stimulant ? 0.3 + rng()*0.5 : 0},
      fiber: {type: fiber, production: fiber ? 0.3 + rng()*0.5 : 0},
      protein: {type: protein, production: protein ? 0.3 + rng()*0.4 : 0},
      noriExport: primaryCrop === "nori" ? 0.6 + rng()*0.3 : (canGrow.nori ? 0.1 + rng()*0.2 : 0),
      stimulantDeficit: !stimulant,
      fiberDeficit: !fiber,
      totalTradeValue: 0 // computed below
    };
    tradeGoods.totalTradeValue = tradeGoods.stimulant.production * 0.4
      + tradeGoods.fiber.production * 0.3
      + tradeGoods.protein.production * 0.2
      + tradeGoods.noriExport * 0.3;

    // ════════════════════════════════════════════════
    // POLITICAL CULTURE (§10c — Almond & Verba)
    // ════════════════════════════════════════════════
    const cultureInit = {
      paddi:   {awareness:0.70, participation:0.15},
      emmer:   {awareness:0.70, participation:0.70},
      taro:    {awareness:0.15, participation:0.10},
      nori:    {awareness:0.30, participation:0.55},
      sago:    {awareness:0.15, participation:0.20},
      papa:    {awareness:0.25, participation:0.15},
      foraging:{awareness:0.05, participation:0.05},
    };
    const politicalCulture = {...(cultureInit[primaryCrop] || cultureInit.foraging)};
    const cultureLabel = politicalCulture.awareness > 0.5
      ? (politicalCulture.participation > 0.5 ? "civic" : "subject")
      : "parochial";

    // ════════════════════════════════════════════════
    // MODE OF PRODUCTION (§10d — Marxian continuous)
    // ════════════════════════════════════════════════
    const prodInit = {
      paddi:   {surplus:0.85, labor:0.25},
      emmer:   {surplus:0.65, labor:0.70},
      taro:    {surplus:0.55, labor:0.15},
      nori:    {surplus:0.35, labor:0.55},
      sago:    {surplus:0.10, labor:0.05},
      papa:    {surplus:0.20, labor:0.10},
      foraging:{surplus:0.05, labor:0.02},
    };
    const production = {...(prodInit[primaryCrop] || prodInit.foraging)};
    // Enforce forbidden zone: labor <= surplus + 0.3
    production.labor = Math.min(production.labor, production.surplus + 0.3);

    // Mode label from position
    const modeLabel =
      production.surplus > 0.7 && production.labor < 0.3 ? "asiatic" :
      production.surplus > 0.7 && production.labor < 0.6 ? "tributary empire" :
      production.surplus > 0.7 && production.labor >= 0.6 ? "state capital" :
      production.surplus > 0.4 && production.labor >= 0.6 ? "mercantile" :
      production.surplus > 0.4 && production.labor >= 0.3 ? "petty commodity" :
      production.surplus > 0.4 ? "tributary" :
      production.surplus > 0.15 ? "household" :
      production.labor < 0.2 ? "communal" : "frontier";

    // Derived production values
    const collaborationEfficiency =
      production.surplus > 0.7 ? 0.85 :
      production.surplus > 0.5 ? 0.60 :
      production.surplus > 0.3 ? 0.45 :
      production.surplus > 0.15 ? 0.20 : 0.05;

    const extractionCeiling =
      modeLabel === "asiatic" ? 0.40 :
      modeLabel === "mercantile" ? 0.30 :
      modeLabel === "tributary" ? 0.50 :
      modeLabel === "petty commodity" ? 0.25 :
      modeLabel === "household" ? 0.10 :
      modeLabel === "communal" ? 0.05 : 0.30;

    // ════════════════════════════════════════════════
    // MINERALS (§10g — Fe, Cu, Au, Pu)
    // ════════════════════════════════════════════════
    const minerals = {
      Fe: true,
      Cu: rng() < 0.20,
      Au: rng() < (0.05 + avgH * 0.08),  // taller peaks = more hydrothermal
      Pu: rng() < (0.03 + size * 0.02),   // larger archs = more evolved magma
    };

    // ════════════════════════════════════════════════
    // NARRATIVE SUBSTRATE (§10e — not simulated)
    // ════════════════════════════════════════════════
    const genderEconomy = Math.min(1, avgEdge / maxEdgeLen);
    const metaphorMap = {paddi:"tidal",emmer:"navigational",taro:"seasonal",sago:"seasonal",nori:"oceanic",papa:"endurance",foraging:"animist"};
    const religionMap = {subject:"formal-institutional",civic:"devotional-debate",parochial:"animist-local"};

    substrates.push({
      climate,
      crops: {primaryCrop, secondaryCrop, primaryYield, canGrow},
      tradeGoods,
      politicalCulture: {...politicalCulture, label: cultureLabel},
      production: {...production, modeLabel, collaborationEfficiency, extractionCeiling},
      minerals,
      narrative: {
        genderEconomy,
        metaphorSystem: metaphorMap[primaryCrop] || "animist",
        religiousMode: religionMap[cultureLabel] || "animist-local",
      }
    });
  }
  return substrates;
}



// ─── DUAL-SOURCE DIJKSTRA HISTORY ENGINE ─────────────────
// Two wavefronts radiate from Reach and Lattice along plateau
// edges. Edge costs depend on era + power + hop count.
// The wavefronts partition the globe. Where they collide = DF break.
// Hooks ready for sovereignty/trade status model.
function assignPolitics(archs, plateauEdges, worldSeed) {
  const rng = mulberry32((worldSeed || 42) * 31 + 1066);
  const N = archs.length;

  // ── Adjacency ──
  const adj = Array.from({length: N}, () => []);
  for (const [a, b] of plateauEdges) { adj[a].push(b); adj[b].push(a); }

  // BFS distances (kept for display and status logic)
  function bfsDist(start) {
    const dist = new Array(N).fill(999);
    dist[start] = 0;
    const q = [start];
    while (q.length) {
      const u = q.shift();
      for (const v of adj[u]) { if (dist[v] > dist[u]+1) { dist[v] = dist[u]+1; q.push(v); } }
    }
    return dist;
  }
  const rDist = bfsDist(REACH_ARCH);
  const lDist = bfsDist(LATTICE_ARCH);

  // ── Resource potential ──
  const potential = archs.map(a => {
    const p = a.peaks.length;
    const sz = a.shelfR / 0.12;
    const avgH = a.peaks.reduce((s, pk) => s + pk.h, 0) / (p * ISLAND_MAX_HEIGHT);
    return (p/20*0.4 + avgH*0.3 + sz/2.2*0.3) * (0.6 + rng()*0.4);
  });

  // ── Name assignment ──
  const names = new Array(N);
  names[REACH_ARCH] = POLITY_NAMES[0];
  names[LATTICE_ARCH] = POLITY_NAMES[1];
  const pool = POLITY_NAMES.slice(2);
  for (let i = pool.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [pool[i], pool[j]] = [pool[j], pool[i]];
  }
  for (let i = 0, pi = 0; i < N; i++) {
    if (i === REACH_ARCH || i === LATTICE_ARCH) continue;
    names[i] = pi < pool.length ? pool[pi++] : "Archipelago " + i;
  }

  // ═══════════════════════════════════════════════════════════
  // PHASE 1: DIJKSTRA WAVEFRONT
  // Two ink drops on wet paper. Edge cost = f(era, power, hops).
  // Era-boundary mechanic: if a hop is too expensive in the
  // current era, wait for the era to change and retry cheaper.
  // ═══════════════════════════════════════════════════════════

  const R_START = -5500;
  const L_START = -5000;
  const ERA_BOUNDS = [-500, -200]; // sail→industrial→nuclear

  function edgeCost(year, hops, power) {
    const isLattice = power === "lattice";
    const isGarrison = isLattice && hops <= 3;

    function costInEra(y) {
      if (y < -500) {
        // SAIL ERA
        if (isGarrison) return 167;    // trivial inter-island crossings
        if (isLattice)  return 12000;  // pulse-and-recall: practically blocked
        // Reach pearl-string: each garrison provisions the next
        return hops <= 1 ? 350 : hops <= 2 ? 580 : hops <= 3 ? 1060 : 8000;
      } else if (y < -200) {
        // INDUSTRIAL
        if (isGarrison) return 85;
        if (isLattice)  return hops <= 5 ? 350 : 700;
        return hops <= 4 ? 125 : hops <= 6 ? 145 : 200;
      } else {
        // NUCLEAR
        return 61;
      }
    }

    const cost = costInEra(year);
    // If cost pushes past an era boundary, check if waiting is cheaper
    for (const b of ERA_BOUNDS) {
      if (year < b && year + cost > b) {
        const alt = (b - year + 1) + costInEra(b + 1);
        if (alt < cost) return alt;
      }
    }
    return cost;
  }

  // Per-arch Dijkstra state
  const claimed = new Array(N).fill(null);    // "reach" | "lattice" | null
  const arrivalYr = new Array(N).fill(null);
  const hopCount = new Array(N).fill(0);
  const parentArch = new Array(N).fill(-1);   // expansion path

  // Seed wavefronts
  claimed[REACH_ARCH] = "reach";     arrivalYr[REACH_ARCH] = R_START;
  claimed[LATTICE_ARCH] = "lattice"; arrivalYr[LATTICE_ARCH] = L_START;

  // Priority queue: [year, archIdx, power, hops, fromArch]
  let pq = [];
  for (const nb of adj[REACH_ARCH])
    pq.push([R_START + edgeCost(R_START, 1, "reach"), nb, "reach", 1, REACH_ARCH]);
  for (const nb of adj[LATTICE_ARCH])
    pq.push([L_START + edgeCost(L_START, 1, "lattice"), nb, "lattice", 1, LATTICE_ARCH]);

  let dfYear = null, dfArch = null, dfDetector = null, dfTarget = null;

  while (pq.length > 0) {
    // Pop earliest arrival
    pq.sort((a, b) => a[0] - b[0]);
    const [year, idx, power, hops, from] = pq.shift();

    if (claimed[idx] !== null) {
      // DF detection: wavefront hits territory of the other power
      if (claimed[idx] !== power && !dfYear) {
        dfYear = year; dfArch = idx;
        dfDetector = power; dfTarget = claimed[idx];
      }
      continue;
    }

    // Claim
    claimed[idx] = power;
    arrivalYr[idx] = year;
    hopCount[idx] = hops;
    parentArch[idx] = from;

    // Check neighbors for DF adjacency
    for (const nb of adj[idx]) {
      if (claimed[nb] && claimed[nb] !== power && !dfYear) {
        dfYear = year; dfArch = idx;
        dfDetector = power; dfTarget = claimed[nb];
      }
    }

    // Expand to unclaimed neighbors
    for (const nb of adj[idx]) {
      if (claimed[nb]) continue;
      pq.push([year + edgeCost(year, hops + 1, power), nb, power, hops + 1, idx]);
    }
  }

  // ═══════════════════════════════════════════════════════════
  // PHASE 2: Σ2^n REDISTRIBUTION
  // Preserves Dijkstra ORDER, adjusts TIMING so each era
  // roughly doubles discoveries. 2+4+8+16 = 30, ~25% uncontacted.
  // ═══════════════════════════════════════════════════════════
  const contactable = [];
  for (let i = 0; i < N; i++) {
    if (claimed[i] && i !== REACH_ARCH && i !== LATTICE_ARCH) contactable.push(i);
  }
  contactable.sort((a, b) => arrivalYr[a] - arrivalYr[b]);
  const nC = contactable.length;

  const serialN     = Math.max(1, Math.round(nC * 0.05));
  const colonialN   = Math.max(1, Math.round(nC * 0.10));
  const industrialN = Math.max(2, Math.round(nC * 0.20));
  const nuclearN    = Math.max(2, Math.round(nC * 0.40));
  const totalSlots  = serialN + colonialN + industrialN + nuclearN;

  for (let k = 0; k < nC; k++) {
    const i = contactable[k];
    if (k < serialN) {
      arrivalYr[i] = -5000 + Math.round((k+1) / (serialN+1) * 3000);
    } else if (k < serialN + colonialN) {
      const j = k - serialN;
      arrivalYr[i] = -2000 + Math.round((j+1) / (colonialN+1) * 1500);
    } else if (k < serialN + colonialN + industrialN) {
      const j = k - serialN - colonialN;
      arrivalYr[i] = -500 + Math.round((j+1) / (industrialN+1) * 300);
    } else if (k < totalSlots) {
      const j = k - serialN - colonialN - industrialN;
      const dfOff = dfYear ? Math.abs(dfYear) : 200;
      arrivalYr[i] = -200 + Math.round((j+1) / (nuclearN+1) * Math.min(200, dfOff - 200));
    } else {
      // El Dorados — beyond Σ2^n budget
      claimed[i] = null; arrivalYr[i] = null;
    }
  }

  // Recompute DF year after redistribution
  dfYear = null; dfArch = null; dfDetector = null; dfTarget = null;
  for (let i = 0; i < N; i++) {
    if (!claimed[i]) continue;
    for (const nb of adj[i]) {
      if (claimed[nb] && claimed[nb] !== claimed[i]) {
        const yr = Math.max(arrivalYr[i], arrivalYr[nb]);
        if (dfYear === null || yr < dfYear) {
          dfYear = yr; dfArch = i;
          dfDetector = claimed[i]; dfTarget = claimed[nb];
        }
      }
    }
  }
  // Null out post-DF claims
  for (let i = 0; i < N; i++) {
    if (arrivalYr[i] !== null && dfYear !== null && arrivalYr[i] > dfYear) {
      claimed[i] = null; arrivalYr[i] = null;
    }
  }

  // ═══════════════════════════════════════════════════════════
  // PHASE 3: STATUS ASSIGNMENT
  // Simple rules from power + hopCount + era. Hooks for
  // sovereignty/trade 2D space, Silk Road, Tokugawa closures,
  // Mughal independents, pulse contacts — all TODO.
  // ═══════════════════════════════════════════════════════════
  const sovereign = new Array(N).fill(-1);
  const colonyYr = new Array(N).fill(null);
  const statusData = Array.from({length: N}, () => ({
    sovereignty: 1.0,       // 0=governed externally, 1=self-governing
    tradeIntegration: 0.0,  // 0=autarkic, 1=fully integrated
    status: "uncontacted",
    eraOfContact: null,     // "sail"|"colonial"|"industrial"|"nuclear"
  }));

  for (let i = 0; i < N; i++) {
    if (i === REACH_ARCH || i === LATTICE_ARCH) {
      statusData[i] = {sovereignty:1, tradeIntegration:1, status:"core", eraOfContact:null};
      continue;
    }
    const yr = arrivalYr[i], power = claimed[i], hops = hopCount[i];
    if (!yr || !power) {
      statusData[i] = {sovereignty:1, tradeIntegration:0, status:"uncontacted", eraOfContact:null};
      continue;
    }
    const era = yr < -2000 ? "sail" : yr < -500 ? "colonial" : yr < -200 ? "industrial" : "nuclear";
    statusData[i].eraOfContact = era;

    if (power === "reach") {
      if (hops <= 3 && era !== "nuclear") {
        sovereign[i] = REACH_ARCH;
        colonyYr[i] = yr + Math.floor(100 + rng()*300);
        statusData[i] = {sovereignty:0.15, tradeIntegration:0.85, status:"colony", eraOfContact:era};
      } else if (hops <= 5 && era !== "nuclear") {
        statusData[i] = {sovereignty:0.55, tradeIntegration:0.60, status:"client", eraOfContact:era};
      } else {
        statusData[i] = {sovereignty:0.90, tradeIntegration:0.20, status:"contacted", eraOfContact:era};
      }
    } else {
      if (hops <= 3) {
        sovereign[i] = LATTICE_ARCH;
        colonyYr[i] = yr + 200;
        statusData[i] = {sovereignty:0.30, tradeIntegration:0.50, status:"garrison", eraOfContact:era};
      } else if (hops <= 5) {
        statusData[i] = {sovereignty:0.60, tradeIntegration:0.40, status:"tributary", eraOfContact:era};
      } else {
        statusData[i] = {sovereignty:0.90, tradeIntegration:0.15, status:"pulse", eraOfContact:era};
      }
    }
  }

  // ═══════════════════════════════════════════════════════════
  // PHASE 4: POPULATION MODEL
