function detectSettlements(archs, history) {
  const settlements = [];
  for (let a = 0; a < archs.length; a++) {
    const ar = archs[a];
    if (ar.peaks.length < 1) continue;
    const usedPeaks = new Set();

    // ── Capital: best peak-pair harbor ──
    if (ar.peaks.length >= 2) {
      let bestScore = -1, bestI = -1, bestJ = -1;
      for (let i = 0; i < ar.peaks.length; i++) {
        for (let j = i + 1; j < ar.peaks.length; j++) {
          const pi = ar.peaks[i], pj = ar.peaks[j];
          const dot = pi.px*pj.px + pi.py*pj.py + pi.pz*pj.pz;
          const angDist = Math.sqrt(Math.max(0, 2*(1-dot)));
          const avgW = (pi.w + pj.w) / 2;
          const sepRatio = angDist / avgW;
          if (sepRatio < 1.0 || sepRatio > 7.0) continue;
          const heightScore = (pi.h + pj.h) / (2 * ISLAND_MAX_HEIGHT);
          const sepScore = Math.max(0, 1 - Math.abs(sepRatio - 2.8) / 4.2);
          const score = heightScore * sepScore;
          if (score > bestScore) { bestScore = score; bestI = i; bestJ = j; }
        }
      }
      if (bestI >= 0) {
        const main = ar.peaks[bestI].h >= ar.peaks[bestJ].h ? ar.peaks[bestI] : ar.peaks[bestJ];
        const secondary = ar.peaks[bestI].h >= ar.peaks[bestJ].h ? ar.peaks[bestJ] : ar.peaks[bestI];
        usedPeaks.add(bestI); usedPeaks.add(bestJ);

        let hx = main.px*0.6 + secondary.px*0.4;
        let hy = main.py*0.6 + secondary.py*0.4;
        let hz = main.pz*0.6 + secondary.pz*0.4;
        const hl = Math.sqrt(hx*hx + hy*hy + hz*hz);
        hx /= hl; hy /= hl; hz /= hl;

        const ppx = secondary.px - main.px, ppy = secondary.py - main.py, ppz = secondary.pz - main.pz;
        let mx = hy*ppz - hz*ppy, my = hz*ppx - hx*ppz, mz = hx*ppy - hy*ppx;
        const ml = Math.sqrt(mx*mx + my*my + mz*mz) || 1;
        mx /= ml; my /= ml; mz /= ml;
        if (mx*ar.cx + my*ar.cy + mz*ar.cz > mx*hx + my*hy + mz*hz) { mx=-mx; my=-my; mz=-mz; }

        const upx = main.px - hx, upy = main.py - hy, upz = main.pz - hz;
        const ul = Math.sqrt(upx*upx + upy*upy + upz*upz) || 1;
        const inclines = [
          { dx: upx/ul, dy: upy/ul, dz: upz/ul },
          { dx: upx/ul*0.85 + mx*0.53, dy: upy/ul*0.85 + my*0.53, dz: upz/ul*0.85 + mz*0.53 },
          { dx: upx/ul*0.85 - mx*0.53, dy: upy/ul*0.85 - my*0.53, dz: upz/ul*0.85 - mz*0.53 },
        ];
        for (const inc of inclines) {
          const il = Math.sqrt(inc.dx*inc.dx + inc.dy*inc.dy + inc.dz*inc.dz) || 1;
          inc.dx /= il; inc.dy /= il; inc.dz /= il;
        }
        settlements.push({
          archIdx: a, cx: hx, cy: hy, cz: hz, mx, my, mz,
          mainPeak: main, secondaryPeak: secondary,
          radius: main.w * 1.8, inclines,
          importance: 1.0, kind: "capital",
          faction: (history[a].faction==="reach"||history[a].faction==="lattice") ? history[a].faction : "other",
        });
      }
    }

    // ── Secondary port towns: every remaining prominent peak ──
    for (let i = 0; i < ar.peaks.length; i++) {
      if (usedPeaks.has(i)) continue;
      const pk = ar.peaks[i];
      if (pk.h < ISLAND_MAX_HEIGHT * 0.18) continue; // skip tiny islets
      // Place settlement on the peak's seaward flank (away from arch center)
      let dx = pk.px - ar.cx, dy = pk.py - ar.cy, dz = pk.pz - ar.cz;
      const dl = Math.sqrt(dx*dx + dy*dy + dz*dz) || 1;
      dx /= dl; dy /= dl; dz /= dl;
      let sx = pk.px + dx * pk.w * 0.3;
      let sy = pk.py + dy * pk.w * 0.3;
      let sz = pk.pz + dz * pk.w * 0.3;
      const sl = Math.sqrt(sx*sx + sy*sy + sz*sz);
      sx /= sl; sy /= sl; sz /= sl;

      const imp = 0.25 + 0.45 * (pk.h / ISLAND_MAX_HEIGHT);
      settlements.push({
        archIdx: a, cx: sx, cy: sy, cz: sz,
        mx: dx, my: dy, mz: dz,
        mainPeak: pk, secondaryPeak: null,
        radius: pk.w * 1.2, inclines: [],
        importance: imp, kind: "port",
        faction: (history[a].faction==="reach"||history[a].faction==="lattice") ? history[a].faction : "other",
      });
    }
  }
  // Normalize: capitals stay near 1.0, ports scale below
  const maxImp = Math.max(...settlements.map(s => s.importance), 0.001);
  for (const s of settlements) {
    s.importance = s.kind === "capital"
      ? Math.max(0.7, s.importance / maxImp)
      : Math.min(0.6, s.importance / maxImp);
  }
  return settlements;
}
