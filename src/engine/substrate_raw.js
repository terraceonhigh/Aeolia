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
