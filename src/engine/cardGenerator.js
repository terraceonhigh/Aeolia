// ═══════════════════════════════════════════════════════════
// cardGenerator.js — Per-turn situation report cards
//
// Pure function: deterministic given snapshot + game options.
// No rng(). Returns up to 3 card objects each turn.
// Narrative text grounded in the Aeolia series bible.
// ═══════════════════════════════════════════════════════════

import {
  CROP_LORE,
  describeCulture,
  getCultureLabel,
  getExpansionOpener,
  getMineralDetectionText,
  getEpidemicRiskText,
  getCultureDriftText,
  getPiracyWarningText,
  getTechDecayText,
  getNavigatorGuildText,
  getMalariaBreakthroughText,
  getReligiousRevivalText,
  getRogueAircraftText,
  getSchismBody,
  getColonialResistanceText,
  getInstitutionalReformText,
  getCulturalFreezeText,
} from './narrativeText.js';

// ── Mineral labels ───────────────────────────────────────────
const MINERAL_LABEL = { Cu: 'aes (copper)', Au: 'chrysos (gold)', C: 'naphtha', Pu: 'pyra' };

// ── Crop article map ─────────────────────────────────────────
const CROP_ARTICLE = {
  paddi: 'paddi paddies', emmer: 'emmer fields', taro: 'taro gardens',
  nori: 'nori beds', sago: 'sago palms', papa: 'papa terraces',
  foraging: 'foraging grounds',
};

// ── Deterministic hash for selection variety ─────────────────
function hashStr(s) {
  let h = 5381;
  const str = String(s || '');
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) + h) ^ str.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

// ── Main export ──────────────────────────────────────────────

/**
 * generateSituationCards(snapshot, playerCore, names, frontier, opts)
 *
 * snapshot   — SimEngine.snapshot() output
 * playerCore — index of player's home archipelago
 * names      — polity name array (shuffled per seed)
 * frontier   — SimEngine.getFrontier(playerCore) output
 * opts       — { rivalCores: Set, partnerCores: Set, activeFocus: string,
 *               selectedTargets: Set, scoutActive: boolean,
 *               prevCultureLabel: string }
 *
 * Returns an array of up to 3 card objects:
 *   { id, icon, title, body, actions: [{ label, action }] }
 *   action is a reducer action object (or null for Dismiss)
 */
export function generateSituationCards(snapshot, playerCore, names, frontier, opts) {
  const ps = snapshot?.playerStats;
  if (!ps) return [];

  const {
    tech = [], controller = [], cpos = [],
    contactedCores = [], visibility = [], sovereignty = [],
  } = snapshot;

  const {
    rivalCores     = new Set(),
    partnerCores   = new Set(),
    activeFocus    = 'balanced',
    selectedTargets = new Set(),
    scoutActive    = false,
    prevCultureLabel = null,
    prevTech       = null,    // for tech decay detection
    malariaUnlocked = false,  // true once we've shown the breakthrough card
    religiousRevivalShown = false, // throttle: show at most once per high-piety phase
  } = opts || {};

  const cards = [];

  // Pre-compute contacted tech array (used by multiple cards)
  const contactedTechs = contactedCores
    .filter(c => c !== playerCore && (tech[c] || 0) > 0)
    .map(c => tech[c]);

  // ── Card 1: Technology assessment ───────────────────────
  if (contactedTechs.length > 0) {
    const maxTech   = Math.max(...contactedTechs);
    const avgTech   = contactedTechs.reduce((a, b) => a + b, 0) / contactedTechs.length;
    const leadCore  = contactedCores.find(c => c !== playerCore && (tech[c] || 0) === maxTech);
    const techRatio = ps.tech / avgTech;

    if (techRatio < 0.88 && activeFocus !== 'innovate') {
      const leadName = leadCore !== undefined ? names[leadCore] : 'a rival power';
      const leadTech = leadCore !== undefined ? (tech[leadCore] || 0).toFixed(1) : '?';
      const gap = ((1 - techRatio) * 100).toFixed(0);
      cards.push({
        id: 'tech_lag',
        icon: '◈',
        title: 'Technology Gap',
        body: `${leadName} leads at tech ${leadTech}. You trail the known-world average by ${gap}%. Research cycles compound — a gap that is small today is structural tomorrow. The guilds are asking for authorization to accelerate.`,
        actions: [
          { label: 'INNOVATE', action: { type: 'SET_FOCUS', focus: 'innovate' } },
          { label: 'DISMISS',  action: null },
        ],
      });

    } else if (techRatio > 1.18 && frontier.length > 0) {
      const target = frontier
        .filter(f => f.tech < ps.tech * 0.78)
        .sort((a, b) =>
          (ps.tech - b.tech) / (b.distance + 0.1) -
          (ps.tech - a.tech) / (a.distance + 0.1)
        )[0];
      if (target && !selectedTargets.has(target.index)) {
        const seed = hashStr(names[target.index]);
        cards.push({
          id: 'tech_edge',
          icon: '◈',
          title: 'Technological Edge',
          body: `Your technology exceeds all known rivals by ${((techRatio - 1) * 100).toFixed(0)}%. ${names[target.index]} (tech ${target.tech?.toFixed(1)}) is within reach. Such advantages are perishable — they diffuse through the relay trade faster than any state can suppress.`,
          actions: [
            { label: 'TARGET',      action: { type: 'TOGGLE_TARGET', target: target.index } },
            { label: 'SHIFT FOCUS', action: { type: 'SET_FOCUS', focus: 'expand' } },
            { label: 'DISMISS',     action: null },
          ],
        });
      }
    }
  }

  // ── Card 2: Sovereignty / governance strain ──────────────
  if (ps.territory > 1 && cards.length < 3) {
    const unstable = [];
    for (let i = 0; i < controller.length; i++) {
      if (controller[i] === playerCore && i !== playerCore && sovereignty[i] !== undefined) {
        if (sovereignty[i] < 0.32) unstable.push(i);
      }
    }
    if (unstable.length >= 2 && activeFocus !== 'fortify') {
      const worstIdx = unstable.reduce((w, i) =>
        (sovereignty[i] || 1) < (sovereignty[w] || 1) ? i : w, unstable[0]);
      const worstSov = Math.round((sovereignty[worstIdx] || 0) * 100);
      cards.push({
        id: 'sov_strain',
        icon: '▣',
        title: 'Governance Strain',
        body: `${unstable.length} holdings are critically unstable. ${names[worstIdx]} is at ${worstSov}% sovereignty — near the threshold for open revolt. Garrison costs are mounting. Administrators are requesting emergency relief.`,
        actions: [
          { label: 'FORTIFY',   action: { type: 'SET_FOCUS', focus: 'fortify' } },
          { label: 'SOV FOCUS', action: { type: 'TOGGLE_SOV_FOCUS', target: worstIdx } },
          { label: 'DISMISS',   action: null },
        ],
      });
    }
  }

  // ── Card 3: Rival threat ─────────────────────────────────
  if (contactedCores.length > 0 && cards.length < 3) {
    const threats = contactedCores
      .filter(c =>
        c !== playerCore &&
        !rivalCores.has(c) &&
        !partnerCores.has(c) &&
        (tech[c] || 0) > ps.tech * 1.22
      )
      .sort((a, b) => (tech[b] || 0) - (tech[a] || 0));

    if (threats.length > 0) {
      const c = threats[0];
      const gap = (((tech[c] || 0) / ps.tech - 1) * 100).toFixed(0);
      const desc = describeCulture(cpos[c]?.[0], cpos[c]?.[1]);
      cards.push({
        id: `rival_${c}`,
        icon: '⚔',
        title: 'Rising Power',
        body: `${names[c]} is ${gap}% ahead in technology. Their disposition: ${desc}. An undesignated peer growing this fast warrants a formal strategic assessment — the admiralty is requesting designation.`,
        actions: [
          { label: 'MARK RIVAL', action: { type: 'TOGGLE_RIVAL', core: c } },
          { label: 'DISMISS',    action: null },
        ],
      });
    }
  }

  // ── Card 4: Partnership opening ──────────────────────────
  if (contactedCores.length > 0 && cards.length < 3) {
    const candidates = contactedCores
      .filter(c =>
        c !== playerCore &&
        !rivalCores.has(c) &&
        !partnerCores.has(c) &&
        cpos[c] && cpos[c][1] > 0.18 &&
        (tech[c] || 0) >= ps.tech * 0.72
      )
      .sort((a, b) => (cpos[b]?.[1] || 0) - (cpos[a]?.[1] || 0));

    if (candidates.length > 0) {
      const c = candidates[0];
      const desc = describeCulture(cpos[c]?.[0], cpos[c]?.[1]);
      const cropFl = CROP_LORE[snapshot?.crops?.[c]];
      const tradeNote = cropFl
        ? ` Their ${cropFl.product} and ${cropFl.stimulant} trade are already reaching your harbor markets through relay intermediaries.`
        : '';
      cards.push({
        id: `partner_${c}`,
        icon: '◆',
        title: 'Partnership Opening',
        body: `${names[c]} is ${desc} and their outward orientation is creating trade opportunities.${tradeNote} A formal pact would grant 30% bonus on mutual routes and reduce their expansion incentive toward your territory.`,
        actions: [
          { label: 'INVITE PARTNER', action: { type: 'TOGGLE_PARTNER', core: c } },
          { label: 'DISMISS',        action: null },
        ],
      });
    }
  }

  // ── Card 5: Expansion opportunity ────────────────────────
  if (frontier.length > 0 && cards.length < 3 && activeFocus !== 'expand') {
    const techThreshold = contactedTechs.length > 0 ? ps.tech * 0.78 : ps.tech * 0.96;
    const weak = frontier
      .filter(f => f.tech <= techThreshold && f.distance < 0.7)
      .sort((a, b) =>
        (ps.tech - b.tech) / (b.distance + 0.1) -
        (ps.tech - a.tech) / (a.distance + 0.1)
      );

    if (weak.length > 0) {
      const t = weak[0];
      const seed = hashStr(names[t.index] + ps.tech);
      const cropLabel = CROP_ARTICLE[t.crop] || t.crop || 'fertile lands';
      const minerals = [
        t.minerals?.Cu    && 'aes',
        t.minerals?.Au    && 'chrysos',
        t.minerals?.C > 0 && 'naphtha',
        t.minerals?.Pu    && 'pyra',
      ].filter(Boolean);
      const resStr = minerals.length > 0 ? ` Their geology includes ${minerals.join(' and ')} deposits.` : '';
      const techStr = t.tech < ps.tech * 0.85
        ? `lags at tech ${t.tech?.toFixed(1)} against your ${ps.tech.toFixed(1)}`
        : `is within reach`;
      const opener = getExpansionOpener(names[t.index], t.crop, seed);
      cards.push({
        id: `expand_${t.index}`,
        icon: '⚔',
        title: ps.territory <= 1 ? 'First Expansion Window' : 'Vulnerable Frontier',
        body: `${opener} ${names[t.index]} ${techStr}.${resStr} Their ${cropLabel} would strengthen your position. Every turn of hesitation narrows the window.`,
        actions: [
          { label: 'TARGET',      action: { type: 'TOGGLE_TARGET', target: t.index } },
          { label: 'SHIFT FOCUS', action: { type: 'SET_FOCUS', focus: 'expand' } },
          { label: 'DISMISS',     action: null },
        ],
      });
    }
  }

  // ── Card 5b: Homeland only (very early game) ─────────────
  if (ps.territory <= 1 && frontier.length > 0 && cards.length < 3) {
    const closest = [...frontier].sort((a, b) => a.distance - b.distance)[0];
    if (closest && !selectedTargets.has(closest.index)) {
      const cropLabel = CROP_ARTICLE[closest.crop] || closest.crop || 'fertile grounds';
      const seed = hashStr(names[closest.index]);
      const opener = getExpansionOpener(names[closest.index], closest.crop, seed);
      cards.push({
        id: `first_move_${closest.index}`,
        icon: '⚔',
        title: 'Homeland Only',
        body: `Your civilization controls a single archipelago. ${opener} ${names[closest.index]} — ${cropLabel}, ${closest.distance.toFixed(2)} hops away — is the closest expansion target. All the history that will follow begins with a first move.`,
        actions: [
          { label: 'TARGET',  action: { type: 'TOGGLE_TARGET', target: closest.index } },
          { label: 'DISMISS', action: null },
        ],
      });
    }
  }

  // ── Card 6: Scouting recommendation ─────────────────────
  if (!scoutActive && cards.length < 3) {
    const unknownCount = visibility.filter(v => v === 'unknown').length;
    const rumorCount   = visibility.filter(v => v === 'rumor').length;
    if (rumorCount > 0 && unknownCount > 14) {
      cards.push({
        id: 'scout_rec',
        icon: '○',
        title: 'Incomplete Charts',
        body: `Rumor of ${rumorCount} unmapped archipelago${rumorCount > 1 ? 's' : ''} reaches your ports through relay trade and navigator gossip. ${unknownCount} islands remain beyond the charted frontier. The cartographic guild has a saying: what you don't know about will surprise you at the worst moment.`,
        actions: [
          { label: 'DISPATCH SCOUTS', action: { type: 'TOGGLE_SCOUT' } },
          { label: 'DISMISS',         action: null },
        ],
      });
    }
  }

  // ── Card 7: Naphtha / carbon resource alert ──────────────
  if (ps.tech >= 4.5 && ps.tech < 7.5 && frontier.length > 0 && cards.length < 3) {
    const naphthaTargets = frontier
      .filter(f => (f.minerals?.C || 0) > 0 && !selectedTargets.has(f.index))
      .sort((a, b) => (b.minerals?.C || 0) - (a.minerals?.C || 0));
    if (naphthaTargets.length > 0) {
      const t = naphthaTargets[0];
      const seed = hashStr(names[t.index] + 'naphtha');
      cards.push({
        id: `naphtha_${t.index}`,
        icon: '⛏',
        title: 'Carbon Deposit Detected',
        body: getMineralDetectionText('C', names[t.index], seed),
        actions: [
          { label: 'TARGET',  action: { type: 'TOGGLE_TARGET', target: t.index } },
          { label: 'DISMISS', action: null },
        ],
      });
    }
  }

  // ── Card 8: Pyra alert (pre-scramble) ───────────────────
  if (ps.tech >= 7.0 && ps.tech < 9.5 && frontier.length > 0 && cards.length < 3) {
    const pyraTargets = frontier
      .filter(f => f.minerals?.Pu && !selectedTargets.has(f.index))
      .sort((a, b) => a.distance - b.distance);
    if (pyraTargets.length > 0) {
      const t = pyraTargets[0];
      const seed = hashStr(names[t.index] + 'pyra');
      cards.push({
        id: `pyra_${t.index}`,
        icon: '⛏',
        title: 'Pyra Deposit Located',
        body: getMineralDetectionText('Pu', names[t.index], seed),
        actions: [
          { label: 'TARGET',  action: { type: 'TOGGLE_TARGET', target: t.index } },
          { label: 'FILE',    action: null },
        ],
      });
    }
  }

  // ── Card 9: Epidemic risk ────────────────────────────────
  if (contactedCores.length >= 3 && cards.length < 3) {
    // Fires occasionally based on tick parity and contact count — no rng, uses determinism
    const tick = snapshot?.tick || 0;
    const shouldFire = (tick % 7 === 2) && contactedCores.length > 3;
    if (shouldFire) {
      const sourceIdx = contactedCores.filter(c => c !== playerCore)[tick % Math.max(1, contactedCores.length - 1)];
      const sourceName = sourceIdx !== undefined ? (names[sourceIdx] || 'a trade contact') : 'the relay network';
      const seed = hashStr(sourceName + tick);
      cards.push({
        id: `epidemic_risk_${tick}`,
        icon: '◉',
        title: 'Disease Vector Warning',
        body: getEpidemicRiskText(sourceName, contactedCores.length, seed),
        actions: [
          { label: 'EMBARGO',  action: sourceIdx !== undefined ? { type: 'TOGGLE_EMBARGO', core: sourceIdx } : null },
          { label: 'MONITOR',  action: null },
        ],
      });
    }
  }

  // ── Card 10: Culture drift notification ──────────────────
  if (prevCultureLabel && cards.length < 3) {
    const currentCI = ps.culturePos?.[0] ?? cpos[playerCore]?.[0];
    const currentIO = ps.culturePos?.[1] ?? cpos[playerCore]?.[1];
    const currentLabel = getCultureLabel(currentCI, currentIO);
    if (prevCultureLabel !== currentLabel) {
      const seed = hashStr(prevCultureLabel + currentLabel);
      cards.push({
        id: `culture_drift_${currentLabel}`,
        icon: '◎',
        title: 'Cultural Shift',
        body: getCultureDriftText(prevCultureLabel, currentLabel, currentCI, currentIO, seed),
        actions: [
          { label: 'REINFORCE', action: { type: 'SET_CULTURE_POLICY', axis: 'io', value: currentIO > 0 ? 0.4 : -0.4 } },
          { label: 'COUNTER',   action: { type: 'SET_CULTURE_POLICY', axis: 'io', value: currentIO > 0 ? -0.4 : 0.4 } },
          { label: 'ACCEPT',    action: null },
        ],
      });
    }
  }

  // ── Card 11: Saak oil displacement ──────────────────────
  if (ps.tech >= 7.0 && contactedCores.length > 0 && cards.length < 3) {
    const tick = snapshot?.tick || 0;
    if (tick % 11 === 4) {
      // Check if any contact has a fishery that produces oil (saak) —
      // approximate: contacts with outward culture are likely to be affected
      const oilContacts = contactedCores.filter(c =>
        c !== playerCore &&
        cpos[c] && cpos[c][1] > 0.1 &&
        !rivalCores.has(c)
      );
      if (oilContacts.length > 0) {
        const c = oilContacts[tick % oilContacts.length];
        cards.push({
          id: `saak_displacement_${tick}`,
          icon: '⛏',
          title: 'Oil Trade Disruption',
          body: `Naphtha refineries have undercut saak oil prices across the relay network. ${names[c]}'s maritime oil economy faces structural pressure. Their saak fleets will either diversify or contract — and either outcome affects your trade routes.`,
          actions: [
            { label: 'PARTNER', action: { type: 'TOGGLE_PARTNER', core: c } },
            { label: 'DISMISS', action: null },
          ],
        });
      }
    }
  }

  // ── Card 11b: Fishery depletion ─────────────────────────
  // Fires when any controlled arch has fishery stock below 0.35.
  if (cards.length < 3) {
    const fisheryStock = snapshot?.fisheryStock || [];
    const depletedArch = (snapshot?.controller || []).reduce((found, ctrl, j) => {
      if (found !== null) return found;
      if (ctrl === playerCore && j !== playerCore && (fisheryStock[j] || 1.0) < 0.35) return j;
      return null;
    }, null);
    if (depletedArch !== null) {
      const stock = Math.round((fisheryStock[depletedArch] || 0) * 100);
      const depletedName = names[depletedArch] || `Arch ${depletedArch}`;
      cards.push({
        id: `fishery_depletion_${depletedArch}`,
        icon: '◉',
        title: 'Fishery Collapse',
        body: `The ${depletedName} fishing grounds are at ${stock}% stock. Your fishing fleets have outpaced recovery rates. The same waters that defined your food security now require rotation and rest. Reducing population pressure is the only sustainable correction — consolidation reduces exploitation.`,
        actions: [
          { label: 'FORTIFY',  action: { type: 'SET_FOCUS', focus: 'fortify' } },
          { label: 'ACCEPT',   action: null },
        ],
      });
    }
  }

  // ── Card 12: Piracy warning ─────────────────────────────
  // Fires in mid-game when trade network is large but patrol capability hasn't scaled.
  if (contactedCores.length > 5 && ps.tech >= 3.0 && ps.tech < 8.0 && cards.length < 3) {
    const tick = snapshot?.tick || 0;
    if (tick % 9 === 3) {
      const seed = hashStr('piracy' + tick + ps.tech);
      cards.push({
        id: `piracy_${tick}`,
        icon: '⚔',
        title: 'Piracy Warning',
        body: getPiracyWarningText(contactedCores.length, ps.tech, seed),
        actions: [
          { label: 'EXPAND NAVY', action: { type: 'SET_FOCUS', focus: 'expand' } },
          { label: 'FORTIFY',     action: { type: 'SET_FOCUS', focus: 'fortify' } },
          { label: 'ACCEPT',      action: null },
        ],
      });
    }
  }

  // ── Card 13: Tech decay alert ────────────────────────────
  // Fires when technology has declined this tick.
  if (prevTech !== null && ps.tech < prevTech - 0.05 && cards.length < 3) {
    const seed = hashStr('decay' + Math.round(ps.tech * 10));
    cards.push({
      id: `tech_decay_${snapshot?.tick || 0}`,
      icon: '◈',
      title: 'Technology Decline',
      body: getTechDecayText(prevTech, ps.tech, seed),
      actions: [
        { label: 'INNOVATE',  action: { type: 'SET_FOCUS', focus: 'innovate' } },
        { label: 'EXPLOIT',   action: { type: 'SET_FOCUS', focus: 'exploit' } },
        { label: 'ACCEPT',    action: null },
      ],
    });
  }

  // ── Card 14: Navigator guild tension ────────────────────
  // Fires at tech 7-8 (industrial/modern navigation technology).
  if (ps.tech >= 7.0 && ps.tech < 8.5 && cards.length < 3) {
    const tick = snapshot?.tick || 0;
    if (tick % 13 === 7) {
      const seed = hashStr('navigator' + tick);
      cards.push({
        id: `navigator_guild_${tick}`,
        icon: '○',
        title: 'Navigator Guild Dispute',
        body: getNavigatorGuildText(ps.tech, seed),
        actions: [
          { label: 'SUPPORT GUILD',   action: { type: 'SET_CULTURE_POLICY', axis: 'io', value: -0.3 } },
          { label: 'MANDATE MODERN',  action: { type: 'SET_CULTURE_POLICY', axis: 'io', value: 0.3 } },
          { label: 'NO OPINION',      action: null },
        ],
      });
    }
  }

  // ── Card 15: Malaria medical breakthrough ────────────────
  // Fires once when tech crosses 6.0 and player holds tropical territory.
  if (!malariaUnlocked && ps.tech >= 6.0 && ps.territory > 1 && cards.length < 3) {
    const tick = snapshot?.tick || 0;
    // Count approximate tropical holdings (controller[j] === playerCore and malariaFactor hint:
    // we use naphtha proxy — tropical crops are paddi/taro/sago)
    const tropicalCrops = new Set(['paddi', 'taro', 'sago']);
    const crops = snapshot?.crops || [];
    let tropicalCount = 0;
    for (let j = 0; j < (snapshot?.controller || []).length; j++) {
      if (snapshot.controller[j] === playerCore && tropicalCrops.has(crops[j])) {
        tropicalCount++;
      }
    }
    if (tropicalCount > 0) {
      const seed = hashStr('malaria' + tick);
      cards.push({
        id: 'malaria_breakthrough',
        icon: '◉',
        title: 'Medical Breakthrough',
        body: getMalariaBreakthroughText(tropicalCount, seed),
        actions: [
          { label: 'EXPAND TROPICS', action: { type: 'SET_FOCUS', focus: 'expand' } },
          { label: 'ACKNOWLEDGE',    action: null },
        ],
      });
    }
  }

  // ── Card 17: Rogue Aircraft Alert ───────────────────────
  // Nuclear-era piracy equivalent. Fires at tech ≥ 9 periodically.
  // A nuclear seaplane that goes dark: mutiny, defection, or mechanical failure —
  // somewhere on 4 billion km² of ocean. Impossible to find. Cannot be called back.
  if (ps.tech >= 9.0 && contactedCores.length > 3 && cards.length < 3) {
    const tick = snapshot?.tick || 0;
    if (tick % 11 === 4) {
      const seed = hashStr('rogue_aircraft' + tick);
      cards.push({
        id: `rogue_aircraft_${tick}`,
        icon: '⚠',
        title: 'Rogue Aircraft Report',
        body: getRogueAircraftText(contactedCores.length, seed),
        actions: [
          { label: 'EXPAND INTEL', action: { type: 'SET_FOCUS', focus: 'fortify' } },
          { label: 'EXPAND NAVY',  action: { type: 'SET_FOCUS', focus: 'expand' } },
          { label: 'ACKNOWLEDGE',  action: null },
        ],
      });
    }
  }

  // ── Card 16: Religious Revival ───────────────────────────
  // Fires when player piety crosses 0.65, at most once per high-piety phase.
  // Piety is per-core; snapshot.piety[playerCore] carries the value.
  if (!religiousRevivalShown && cards.length < 3) {
    const playerPiety = (snapshot?.piety || [])[playerCore] ?? 0;
    if (playerPiety >= 0.65) {
      const tick = snapshot?.tick || 0;
      const isCollective = (ps.culturePos?.[0] ?? 0) < -0.15;
      const seed = hashStr('piety' + Math.floor(tick / 8) + playerCore);
      cards.push({
        id: 'religious_revival',
        icon: '✦',
        title: 'Religious Revival',
        body: getReligiousRevivalText(playerPiety, ps.tech, isCollective, seed),
        actions: [
          { label: 'EMBRACE FAITH',   action: { type: 'CULTURE_POLICY', culturePolicyCI: isCollective ? 0 : -0.5 } },
          { label: 'CHANNEL OUTWARD', action: { type: 'SET_FOCUS', focus: 'expand' } },
          { label: 'ACKNOWLEDGE',     action: null },
        ],
      });
    }
  }

  // ── Card 18: Schism Warning ──────────────────────────────
  // Fires when schism pressure is elevated (> 0.55) but before schism fires.
  // Gives player a warning turn to adjust policy (lower piety via tech investment,
  // or shore up sovereignty in peripheral territories).
  if (cards.length < 3) {
    const schismP = (snapshot?.schismPressure || [])[playerCore] ?? 0;
    const playerPiety = (snapshot?.piety || [])[playerCore] ?? 0;
    const tick = snapshot?.tick || 0;
    if (schismP > 0.55 && playerPiety >= 0.65 && ps.tech < 7.0) {
      const seed = hashStr('schism_warning' + Math.floor(tick / 5) + playerCore);
      const urgency = schismP > 0.85 ? 'CRITICAL' : 'WARNING';
      cards.push({
        id: `schism_warning_${Math.floor(tick / 5)}`,
        icon: '⊕',
        title: `Schism Risk — ${urgency}`,
        body: getSchismBody({ count: 1, polityName: 'your realm' }, seed).split('.')[0] + '. The conditions for religious fragmentation in your peripheral territories are present and worsening.',
        actions: [
          { label: 'INVEST IN GOVERNANCE', action: { type: 'SET_FOCUS', focus: 'fortify' } },
          { label: 'PUSH TECH',            action: { type: 'SET_FOCUS', focus: 'innovate' } },
          { label: 'ACKNOWLEDGE',          action: null },
        ],
      });
    }
  }

  // ── Card 19: Colonial resistance (Scott 1985) ────────────────────────────
  // Fires when any of the player's holdings has high grievance — excess
  // extraction is building resistance that will accelerate sovereignty loss.
  if (cards.length < 3 && ps.territory > 1) {
    const grievanceArr = snapshot?.grievance || [];
    const stateArr = snapshot?.states || [];
    let maxGrievance = 0;
    let resistanceArch = null;
    for (let i = 0; i < grievanceArr.length; i++) {
      const g = grievanceArr[i];
      if (g > maxGrievance && stateArr[i] && stateArr[i].faction !== 'independent') {
        maxGrievance = g;
        resistanceArch = i;
      }
    }
    if (maxGrievance > 0.35 && resistanceArch !== null) {
      const archName = stateArr[resistanceArch]?.name ?? `archipelago ${resistanceArch}`;
      const seed = hashStr('colonial_resistance' + Math.floor((snapshot?.tick || 0) / 4) + resistanceArch);
      const urgency = maxGrievance > 0.65 ? 'CRITICAL' : 'WARNING';
      cards.push({
        id: `colonial_resistance_${Math.floor((snapshot?.tick || 0) / 4)}`,
        icon: '⚑',
        title: `Colonial Resistance — ${urgency}`,
        body: getColonialResistanceText(maxGrievance, archName, seed),
        actions: [
          { label: 'REDUCE EXTRACTION', action: { type: 'SET_FOCUS', focus: 'fortify' } },
          { label: 'INVEST IN SOV FOCUS', action: { type: 'SET_SOV_FOCUS', archIndex: resistanceArch } },
          { label: 'ACKNOWLEDGE',         action: null },
        ],
      });
    }
  }

  // ── Card 20: Institutional Reform (Acemoglu-Robinson) ─────────────────────
  // Fires when the player's extractiveness_index is high — elite rent-protection
  // blocking TFP growth. Actions: reduce extraction focus, cultural policy shift.
  // Also shows reversal-of-fortune diagnostic when negative (AJR reversal detected).
  const extractivenessArr = snapshot?.extractiveness || [];
  const playerExtractiveness = extractivenessArr[playerCore] ?? 0;
  if (playerExtractiveness > 0.30) {
    const reformSeed = hashStr('institutional_reform' + Math.floor((snapshot?.tick || 0) / 5));
    const severity = playerExtractiveness > 0.65 ? 'CRITICAL' : playerExtractiveness > 0.45 ? 'ELEVATED' : 'WARNING';
    const reversalR = snapshot?.reversal_of_fortune_r ?? 0;
    const reversalNote = reversalR < -0.20
      ? ` The prosperity ranking of your absorbed territories shows a reversal pattern (r=${reversalR.toFixed(2)}): formerly productive polities now lag, consistent with extractive institutional lock-in.`
      : '';
    cards.push({
      id: `institutional_reform_${Math.floor((snapshot?.tick || 0) / 5)}`,
      icon: '⚖',
      title: `Institutional Lock-in — ${severity}`,
      body: getInstitutionalReformText(playerExtractiveness, reformSeed) + reversalNote,
      actions: [
        { label: 'PURSUE INCLUSIVE REFORM',   action: { type: 'SET_CULTURE_POLICY', ci: 0.3, io: 0.2 } },
        { label: 'REDUCE EXTRACTION RATE',    action: { type: 'SET_FOCUS', focus: 'fortify' } },
        { label: 'ACKNOWLEDGE',               action: null },
      ],
    });
  }

  // ── Card 21: Cultural Freeze Warning (Axelrod) ─────────────────────────────
  // Fires when a key trade contact's cultural distance approaches the freeze
  // threshold (0.85). Warns player to adjust cultural policy before trade ceases.
  const cposArr = snapshot?.cpos || [];
  if (cposArr.length > playerCore && cposArr[playerCore]) {
    const [pCI, pIO] = cposArr[playerCore];
    let maxFreezeRisk = 0;
    let freezeRiskPartner = null;
    const contactedList = snapshot?.contactedCores || [];
    for (const partner of contactedList) {
      if (partner === playerCore || !cposArr[partner]) continue;
      const [ci2, io2] = cposArr[partner];
      const dist = Math.sqrt((pCI - ci2) ** 2 + (pIO - io2) ** 2) / 2.828;
      if (dist > maxFreezeRisk) {
        maxFreezeRisk = dist;
        freezeRiskPartner = partner;
      }
    }
    if (maxFreezeRisk > 0.70 && freezeRiskPartner !== null) {
      const partnerName = names?.[freezeRiskPartner] || `Nation ${freezeRiskPartner}`;
      const freezeSeed = hashStr('cultural_freeze' + Math.floor((snapshot?.tick || 0) / 6) + freezeRiskPartner);
      cards.push({
        id: `cultural_freeze_${Math.floor((snapshot?.tick || 0) / 6)}_${freezeRiskPartner}`,
        icon: '❄',
        title: `Cultural Divergence — ${maxFreezeRisk > 0.78 ? 'CRITICAL' : 'WARNING'}`,
        body: getCulturalFreezeText(partnerName, maxFreezeRisk, freezeSeed),
        actions: [
          { label: 'SHIFT CULTURE (OUTWARD)', action: { type: 'SET_CULTURE_POLICY', ci: 0.0, io: 0.3 } },
          { label: 'ENGAGE DIPLOMATICALLY',   action: { type: 'SET_PARTNER', core: freezeRiskPartner } },
          { label: 'ACKNOWLEDGE',             action: null },
        ],
      });
    }
  }

  return cards.slice(0, 3);
}
