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

  // Era markers
  log.push({ arch: -1, name: "Era", faction: "era", status: "marker", label: "Antiquity", contactYr: -20000 });
  log.push({ arch: -1, name: "Era", faction: "era", status: "marker", label: "Serial Contact", contactYr: -5000 });
  log.push({ arch: -1, name: "Era", faction: "era", status: "marker", label: "Colonial", contactYr: -2000 });
  log.push({ arch: -1, name: "Era", faction: "era", status: "marker", label: "Industrial", contactYr: -500 });
  log.push({ arch: -1, name: "Era", faction: "era", status: "marker", label: "Nuclear", contactYr: -200 });

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
