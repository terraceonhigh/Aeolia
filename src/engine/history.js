// ═══════════════════════════════════════════════════════════
// history.js — Adapter: simulate() output → renderer format
// Bridges the emergent sim engine to the MONOLITH renderer's
// expected {states, log, dfYear, dfArch, dfDetector} contract.
// ═══════════════════════════════════════════════════════════

import { simulate, DEFAULT_PARAMS } from './simulate.js';
import { POLITY_NAMES } from './constants.js';
import { mulberry32 } from './rng.js';

export function assignPolitics(archs, plateauEdges, seed, reachArch, latticeArch) {
  const world = { archs, plateauEdges, seed: seed || 42 };
  const result = simulate(world, DEFAULT_PARAMS);

  // Shuffle polity names deterministically per seed (same logic as MONOLITH)
  const nameRng = mulberry32(((seed || 42) * 19 + 7) | 0);
  const shuffled = [...POLITY_NAMES];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(nameRng() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  // Pin index 0 = Reach, index 1 = Lattice
  shuffled[0] = "The Reach";
  shuffled[1] = "The Lattice";

  // Map arch indices to names: hegemons get Reach/Lattice, others get shuffled
  const nameMap = new Array(archs.length);
  let nameIdx = 2;
  for (let i = 0; i < archs.length; i++) {
    if (i === result.reach_arch) nameMap[i] = "The Reach";
    else if (i === result.lattice_arch) nameMap[i] = "The Lattice";
    else nameMap[i] = shuffled[nameIdx++] || `Archipelago ${i}`;
  }

  // Transform states
  const states = result.states.map((s, i) => ({
    faction: s.faction,
    status: s.status,
    name: nameMap[i],
    population: s.population,
    urbanization: s.urbanization,
    tech: s.tech,
    sovereignty: s.sovereignty,
    tradeIntegration: s.tradeIntegration,
    eraOfContact: s.eraOfContact,
    hopCount: s.hopCount,
  }));

  // Build log for sidebar display
  const log = [];

  // ── Dynamic era markers ────────────────────────────────────
  // The sim runs from -20,000 to 0 (400 × 50-year ticks). Where
  // expansion events actually cluster depends on the seed's tech
  // pace — hardcoded thresholds leave most eras empty for fast
  // seeds. Instead, derive pre-colonial boundaries from the data.
  //
  // Fixed late-era boundaries (match simulate.js eraOfContact):
  //   cy < -2000 → "sail"   -2000..-500 → "colonial"
  //   -500..-200 → "industrial"   ≥ -200 → "nuclear"
  function _eraMarker(label, contactYr) {
    return { arch: -1, name: 'Era', faction: 'era', status: 'marker', label, contactYr };
  }

  // Gather all expansion-event years
  const _expYears = result.log
    .filter(e => e.year != null)
    .map(e => e.year)
    .sort((a, b) => a - b);

  const _simStart = _expYears.length > 0 ? _expYears[0] - 2000 : -20000;

  // Pre-colonial events (cy < -2000): split into two eras at the median
  const _preCYears = _expYears.filter(y => y < -2000);

  if (_preCYears.length === 0) {
    // No events before colonial — just show founding + sail stubs
    log.push(_eraMarker('Founding',     -20000));
    log.push(_eraMarker('Age of Sail',  -10000));
  } else {
    const _first   = _preCYears[0];
    const _midIdx  = Math.floor(_preCYears.length / 2);
    const _midYear = _preCYears[_midIdx];

    // "Founding" starts the entire timeline (no events here by definition)
    log.push(_eraMarker('Founding', _simStart));

    // "First Contact" label lands at the very first expansion event
    log.push(_eraMarker('First Contact', _first));

    // "Age of Sail" splits the remaining pre-colonial events at the median —
    // only emit if it would create a non-trivial second bucket (> 200 years gap)
    if (_midYear > _first + 200 && _midYear < -2100) {
      log.push(_eraMarker('Age of Sail', _midYear));
    }
  }

  // Fixed late-era markers (always present, match sim canonical thresholds)
  log.push(_eraMarker('Colonial',   -2000));
  log.push(_eraMarker('Industrial',  -500));
  log.push(_eraMarker('Nuclear',     -200));

  // Expansion events
  for (const ev of result.log) {
    log.push({
      arch: ev.target,
      name: nameMap[ev.target],
      faction: states[ev.core]?.faction || "unknown",
      status: states[ev.target]?.status || "contacted",
      label: `${nameMap[ev.core]} absorbs ${nameMap[ev.target]}`,
      contactYr: ev.year,
      rDist: ev.core === result.reach_arch ? 1 : 0,
      lDist: ev.core === result.lattice_arch ? 1 : 0,
    });
  }

  // DF event
  if (result.df_year !== null) {
    log.push({
      arch: result.df_arch,
      name: "Dark Forest",
      faction: "df",
      status: "detection",
      label: `⚠ CONTACT: ${nameMap[result.df_arch]} detects ${nameMap[result.df_detector]}`,
      contactYr: result.df_year,
    });
  }

  // Uncontacted
  for (let i = 0; i < archs.length; i++) {
    if (states[i].status === "uncontacted") {
      log.push({
        arch: i, name: nameMap[i], faction: "unknown",
        status: "uncontacted", label: `${nameMap[i]} (El Dorado)`, contactYr: null,
      });
    }
  }

  log.sort((a, b) => (a.contactYr ?? Infinity) - (b.contactYr ?? Infinity));

  return {
    states, log,
    dfYear: result.df_year,
    dfArch: result.df_arch,
    dfDetector: result.df_detector,
    // Pass through for future use
    timeline: result.timeline,
    hegemons: result.hegemons,
    substrate: result.substrate,
  };
}
