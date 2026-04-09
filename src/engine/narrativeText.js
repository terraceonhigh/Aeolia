// ═══════════════════════════════════════════════════════════
// narrativeText.js — Deterministic narrative prose generation
//
// No RNG. Uses hash-based selection from curated text pools.
// All vocabulary grounded in the Aeolia series bible:
//   docs/00_SERIES_BIBLE.md, 02_HISTORICAL_TIMELINE.md,
//   05_TECHNOLOGY.md, 07_CULTURAL_ATLAS.md, 08_MARITIME_TRADITIONS.md,
//   optimization/FISHERIES_REFERENCE.md, NON_STAPLE_CROPS_REFERENCE.md
// ═══════════════════════════════════════════════════════════

// ── Deterministic selection ──────────────────────────────────

function pick(arr, seed) {
  if (!arr || arr.length === 0) return '';
  return arr[Math.abs(Math.floor(seed ?? 0)) % arr.length];
}

function hashStr(s) {
  let h = 5381;
  const str = String(s || '');
  for (let i = 0; i < str.length; i++) {
    h = ((h << 5) + h) ^ str.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

// ── Canon vocabulary ─────────────────────────────────────────

// Six canonical crops with lore-accurate associated goods
export const CROP_LORE = {
  paddi: {
    harvest: 'paddi paddies',
    product: 'rice surplus',
    season: 'flood season',
    culture: 'hydraulic cultivation traditions',
    stimulant: 'char',
    fiber: 'byssus cloth',
    notes: 'collective labor, tidal management, dike systems',
  },
  emmer: {
    harvest: 'emmer fields',
    product: 'grain stores',
    season: 'threshing season',
    culture: 'dry-farming traditions',
    stimulant: 'qahwa',
    fiber: 'kapas cloth',
    notes: 'qahwa-house culture, merchant guilds, competitive island-states',
  },
  taro: {
    harvest: 'taro gardens',
    product: 'taro starch',
    season: 'garden harvest',
    culture: 'terraced garden traditions',
    stimulant: 'awa',
    fiber: 'tapa cloth',
    notes: 'ceremonial awa, bark cloth, intimate island scale',
  },
  nori: {
    harvest: 'nori beds',
    product: 'dried nori',
    season: 'tidal harvest',
    culture: 'coastal gathering traditions',
    stimulant: 'pinang',
    fiber: 'seric cloth',
    notes: 'tidal economy, pinang chewing visible as stained teeth, kauri shell currency',
  },
  sago: {
    harvest: 'sago palms',
    product: 'sago flour',
    season: 'palm season',
    culture: 'grove cultivation traditions',
    stimulant: 'pinang',
    fiber: 'tapa cloth',
    notes: 'low-intensity cultivation, long-fallowing, scattered settlements',
  },
  papa: {
    harvest: 'papa terraces',
    product: 'papa stores',
    season: 'highland harvest',
    culture: 'highland terrace traditions',
    stimulant: 'aqua',
    fiber: 'fell cloth',
    notes: 'cold-adapted, distilled spirits, hide and leather trade',
  },
};

// Six canonical fish species
export const FISH_LORE = {
  sthaq: {
    name: 'sthaq',
    type: 'salmon-analog',
    habitat: 'cold-water, seasonal runs',
    product: 'dried sthaq',
    tradeRange: '1–3 hops',
    culture: 'collective seasonal harvest',
    note: 'anadromous — the fish so important it became the word for food',
  },
  saak: {
    name: 'saak',
    type: 'oil-fish',
    habitat: 'coastal rivers, spring runs',
    product: 'saak oil',
    tradeRange: '4–6 hops',
    culture: 'outward-oriented oil trade',
    note: 'rendered oil displaces at tech 7+ by naphtha — the economic transition',
  },
  tunnu: {
    name: 'tunnu',
    type: 'pelagic tuna-analog',
    habitat: 'open ocean, warm currents',
    product: 'fresh or dried tunnu',
    tradeRange: '2–3 hops',
    culture: 'individualist deep-water crews',
    note: 'schools follow inter-archipelago currents — the first relay trade paths',
  },
  sardai: {
    name: 'sardai',
    type: 'sardine-analog',
    habitat: 'everywhere with coastline',
    product: 'dried sardai, sardai paste',
    tradeRange: '1–2 hops',
    culture: 'neutral — universal subsistence',
    note: 'sardai paste is the Aeolian garum equivalent',
  },
  bakala: {
    name: 'bakala',
    type: 'cod-analog',
    habitat: 'cold-water demersal',
    product: 'dried stockfish',
    tradeRange: '4–8 hops',
    culture: 'inward merchant oligarchy',
    note: 'the fish that enables long-distance trade — keeps for years without salt',
  },
  kauri: {
    name: 'kauri',
    type: 'shellfish',
    habitat: 'nearshore beds',
    product: 'kauri shell, meat',
    tradeRange: '3–6 hops (shell)',
    culture: 'slight collectivist — egalitarian gathering',
    note: 'shell functions as currency — cowrie parallel',
  },
};

// ── Culture labels ────────────────────────────────────────────

/**
 * Returns a lore-accurate culture label from continuous CI/IO position.
 * ci: Collective (−1) ↔ Individual (+1)
 * io: Inward (−1) ↔ Outward (+1)
 */
export function getCultureLabel(ci, io) {
  if (ci == null || io == null) return 'parochial';
  const c = ci >  0.3 ? 'indiv'  : ci < -0.3 ? 'coll'   : 'civic';
  const o = io >  0.3 ? 'out'    : io < -0.3 ? 'in'     : 'bal';
  const MAP = {
    'indiv out':  'thalassocratic',
    'indiv bal':  'mercantile',
    'indiv in':   'parochial',
    'civic out':  'civic',
    'civic bal':  'civic',
    'civic in':   'civic isolationist',
    'coll out':   'hegemonic',
    'coll bal':   'hydraulic',
    'coll in':    'subject',
  };
  return MAP[`${c} ${o}`] || 'parochial';
}

/**
 * Returns a one-line description of a culture position.
 */
export function describeCulture(ci, io) {
  if (ci == null || io == null) return 'disposition unknown';
  const label = getCultureLabel(ci, io);
  const DESCS = {
    'thalassocratic': 'competitive maritime, outward-driven, commerce-oriented',
    'mercantile': 'individualist, trade-focused, institutionally flexible',
    'parochial': 'inward-facing, self-sufficient, resistant to outside authority',
    'civic': 'balanced institutions, moderate outreach, stable governance',
    'civic isolationist': 'procedural, internally organized, cautious of contact',
    'hegemonic': 'collectively organized, expansionist, state-directed growth',
    'hydraulic': 'collective management, high population density, central coordination',
    'subject': 'hierarchical, inward, organized around resource control',
  };
  return DESCS[label] || label;
}

// ── Era narratives ────────────────────────────────────────────

export const ERA_NARRATIVES = {
  Antiquity: {
    icon: '◉',
    short: 'Before the gap crossings. Each island-group inhabits the world it has.',
    long: `Your people have inhabited this archipelago since the memory of the flood — the great drowning the oral tradition remembers as the moment the land-bridges submerged and the world broke apart. The ocean is not hostile. It is simply absolute. Your charts end at the shelf edge. Beyond the shelf, nothing your navigators have returned to describe. You are alone, and the world is the size of the sky visible from your highest peak.`,
    color: '#9a8a6a',
  },
  'Serial Contact': {
    icon: '◆',
    short: 'The gap crossings begin. Each contact is a New World event.',
    long: `Deep-keeled hulls and celestial navigation have made the shelf edges crossable. The first captains to return from beyond the horizon were treated as near-mythological figures — and for good reason. Contact with peoples who diverged from common stock 30,000–80,000 years ago produces simultaneous enrichment and catastrophe: new crops, new diseases, new gods, new enemies. The horizon is no longer a boundary. It is a door, and it swings both ways.`,
    color: '#a09060',
  },
  Colonial: {
    icon: '⚔',
    short: 'Naval supremacy enables distant conquest. Pearl-string empires form.',
    long: `Whoever commands the sea-lanes commands everything. Pearl-string garrison chains extend thousands of kilometers along wind-belt corridors. Civilizations that mastered blue-water sailing a generation earlier are absorbing those that didn't. The moral debates about contact and conquest began before the fleets sailed — they continue with the fleets at sea, the intellectuals writing from the same civilizations doing the conquering. The pattern is known. It continues anyway.`,
    color: '#8a7040',
  },
  Industrial: {
    icon: '⛏',
    short: 'Naphtha transforms the energy budget. Control of deposits becomes existential.',
    long: `Refineries and combustion engines have broken the Malthusian ceiling. A civilization with naphtha can grow faster than one without, and the gap compounds with each generation. The geological survey has become a military instrument. Islands that were valued for their anchorages are now valued for what lies beneath them. The word *scramble* has entered diplomatic vocabulary — first as a description, then as a policy.`,
    color: '#7a8a5a',
  },
  Nuclear: {
    icon: '⚠',
    short: 'Fission. Unlimited range. The Dark Forest logic goes planetary.',
    long: `Two civilizations can now end each other. Neither can afford to strike first; neither can afford not to watch. The surveillance aircraft that pioneered gap-crossing now map the world for threat vectors. Intelligence agencies have replaced admiralties. Pyra deposits are the most valuable geology on Aeolia — more valuable than the islands that contain them, more valuable than the populations who live above them. And somewhere, across 55,000 kilometers of dark water, something is watching back.`,
    color: '#8a2020',
  },
};

// ── Tech milestone narratives ─────────────────────────────────

export const TECH_MILESTONE_NARRATIVES = {
  2: {
    title: 'Gap Crossing Capability',
    color: '#a09060',
    body: `Deep-keeled hulls and celestial navigation have made the shelf edges crossable. Your navigators can now reach archipelagos beyond the visible horizon. The navigator's guild has filed a formal claim on the commission for any successful gap crossing — their leverage is absolute, because no one else knows how to do it. Every expedition that returns answers one question and asks three more.`,
  },
  5: {
    title: 'Guild Charter Era',
    color: '#9a8a5a',
    body: `The relay has matured into something different: formal guild charters, standardized commodity grades, letters of credit valid across multiple archipelagos. Your harbors receive dried bakala, saak oil, and marich from partners who have never met your people directly — three and four hops away, the goods arrive on schedule. The qahwa houses in your trading districts are where foreign merchants negotiate. They are also where dissent accumulates.`,
  },
  7: {
    title: 'Naphtha Refinement',
    color: '#8a6a3a',
    body: `The first refineries are burning. Surface seeps that your ancestors treated as sacred fire — the eternal flame, the bitumen spring — are now industrial inputs. The energy surplus this produces is unlike anything before it. A civilization with functional naphtha infrastructure can grow its tech level three times faster than one without. And everyone with a geological survey knows who has deposits and who does not.`,
  },
  9: {
    title: 'Nuclear Capability',
    color: '#8a2020',
    body: `The chain reaction has been demonstrated. Your civilization commands energy sufficient to render a large island uninhabitable. So does at least one other power. The mutual awareness of this fact changes every calculation — expansion, diplomacy, alliance, even the tenor of ordinary correspondence. This is not a new kind of weapon. It is a new kind of world. The navigator who made the first nuclear gap crossing described the ocean from altitude as "a dark mirror." They were right in more ways than they meant.`,
  },
};

// ── First contact narrative ───────────────────────────────────

/**
 * Generates first-contact event body text.
 * data: { name, culture, tech, crop, fish }
 * seed: integer for deterministic selection
 */
export function getFirstContactBody(data, seed) {
  const { name, culture, tech, crop } = data;
  const cropFl = CROP_LORE[crop];
  const s = seed ?? hashStr(name);

  const opening = pick([
    `At dawn, on a submarine plateau your charts did not show, your fishing fleet encountered vessels flying unknown colors.`,
    `A pilot on deep-survey patrol reported structured radio traffic from a bearing your intelligence had marked as empty ocean.`,
    `Two boats. Eighty meters of water between them. Both crews staring. Someone on the far vessel raised their hand.`,
    `Merchant scouts running a speculative relay route found anchored vessels in a harbor that has no name in any chart you hold.`,
    `A seaplane on extended patrol logged a city visible from altitude — harbor lights, docks, the unmistakable geometry of a working port — on an island marked as uninhabited.`,
  ], s);

  const cultureNote = pick([
    `Their institutions read as ${culture}. Contact will require patience.`,
    `First reports describe ${culture} social organization — recognizably Aeolian, entirely unfamiliar.`,
    `Intelligence assessment: ${culture}. Their motivations will take time to read.`,
  ], s + 1);

  const cropNote = cropFl
    ? ` Their harbors cultivate ${cropFl.harvest}. Their ${cropFl.stimulant} houses appear to be where public life happens.`
    : '';

  return `${opening}${cropNote} Technology: ${tech}. ${cultureNote} Trade routes may now form. The contact has also reset the epidemiological clock — both populations carry pathogens the other has never encountered.`;
}

// ── Dark Forest narrative ─────────────────────────────────────

export function getDarkForestBody(names, playerCore) {
  return `Surveillance aircraft operating at the edge of your detection range have returned with reactor-isotope readings that admit only one interpretation: a nuclear-capable peer civilization exists, and they know about you. The chain of suspicion runs to its logical terminus — *if they can strike, and I know they know, and they know I know they know* — faster than any diplomat can interrupt it. Neither side made this situation. Both sides have to live in it. Every subsequent interaction, every trade negotiation, every navigation incident, every radio silence will be interpreted through this fact. Welcome to the dark half of the ocean.`;
}

// ── Event log dispatch entries ────────────────────────────────

/**
 * Returns a source-tagged dispatch string for the event log.
 * type: one of the log event types
 * data: event-specific data
 * names: polity names array
 * tick: current tick (for seed variation)
 */
export function getDispatchEntry(type, data, names, tick) {
  const s = (tick || 0) + (data?.idx || data?.core || 0);

  switch (type) {
    case 'culture_shift': {
      const label = data?.label || 'unknown';
      const reason = pick([
        'A generation of sustained trade contact has reoriented your people outward.',
        'The last century of consolidation has turned your institutions inward.',
        'Prosperity and open markets have individualized your commercial culture.',
        'Resource pressure and collective response have reinforced communal institutions.',
        'Absorbing new territory has introduced competing cultural currents.',
        'The intellectual class in your qahwa houses has turned the political conversation.',
      ], s);
      return `CULTURAL OBSERVER — Disposition has shifted to ${label}. ${reason}`;
    }

    case 'sovereignty_stabilized': {
      const name = data?.name || 'the territory';
      const how = pick([
        'Garrison rotations have normalized. Tax collection is proceeding.',
        'A new administrative compact has reduced local resistance.',
        'The harbor market has recovered. Revenue is flowing.',
        'Three years without incident. The occupation has become administration.',
      ], s);
      return `INTERNAL AFFAIRS — ${name} has stabilized. ${how}`;
    }

    case 'sovereignty_critical': {
      const name = data?.name || 'a holding';
      const incident = pick([
        'tax resistance at three collection points',
        'a garrison incident near the harbor market',
        'public demonstrations outside the administrative compound',
        'underground organizing among dock workers',
        'two administrators requesting emergency relief',
      ], s);
      return `INTERNAL AFFAIRS — ${name} approaching revolt threshold. Reports of ${incident}.`;
    }

    case 'trade_growth': {
      const ct = data?.contacts || '?';
      const good = pick([
        `Dried bakala stockfish has appeared in your waterfront markets from a source four hops distant.`,
        `Marich from southern routes has entered your spice trade for the first time.`,
        `Saak oil from a newly contacted northern partner is displacing local sources.`,
        `Char from a western archipelago has arrived in your qahwa houses.`,
        `Seric cloth of foreign weave is appearing in the upper-harbor markets.`,
        `Kauri shell currency from an eastern contact is circulating in your port districts.`,
      ], s);
      return `MERCHANT GUILD — Network now spans ${ct} foreign polities. ${good}`;
    }

    case 'saak_displacement': {
      const name = data?.name || 'a contact';
      return `MERCHANT GUILD — Naphtha refineries have undercut saak oil prices across your trade network. ${name}'s fishing economy faces structural disruption. Their saak fleets will either find new markets or contract.`;
    }

    case 'epidemic_wave': {
      const name = data?.name || 'a contact';
      const severity = data?.severity || 'moderate';
      return `ADMIRALTY INTELLIGENCE — ${severity === 'severe' ? 'Severe' : 'Moderate'} epidemic wave reported in ${name}. Trade-route propagation is likely. Your port authorities have been advised.`;
    }

    case 'naphtha_scramble': {
      return `ADMIRALTY INTELLIGENCE — Multiple powers are now contesting naphtha-bearing islands on your frontier. The scramble is underway. Commercial control will precede political control — for now.`;
    }

    case 'pyra_revaluation': {
      return `ADMIRALTY INTELLIGENCE — Fission has been demonstrated. Every pyra deposit on Aeolia has changed strategic value overnight. Geological surveys are being reclassified. The scramble has a new object.`;
    }

    case 'tech_decay': {
      const from = data?.from?.toFixed(1) || '?';
      const to = data?.to?.toFixed(1) || '?';
      const deficit = pick([
        'Energy reserves below maintenance threshold.',
        'Research institution funding has lapsed.',
        'Scholar recruitment and retention has collapsed.',
      ], s);
      return `INTERNAL AFFAIRS — Technology has declined: ${from} → ${to}. ${deficit}`;
    }

    case 'piracy_incident': {
      const route = pick([
        'the northern relay corridor',
        'frontier trade lanes',
        'southern convoy routes',
        'the island chain connecting your outer holdings',
      ], s);
      return `MERCHANT GUILD — Piracy reported on ${route}. Cargo losses above seasonal average. Escort allocation review underway.`;
    }

    default:
      return data?.text || type;
  }
}

// ── Card body text fragments ──────────────────────────────────

/**
 * Returns a lore-flavored opening line for expansion cards.
 */
export function getExpansionOpener(targetName, crop, seed) {
  const cropFl = CROP_LORE[crop];
  const s = seed ?? hashStr(targetName);
  return pick([
    cropFl ? `Your navigators have been mapping their ${cropFl.harvest} for three seasons.` : `Your scouts have been watching their coastline.`,
    `Merchant pilots returning from the frontier confirm the intelligence.`,
    `Three expedition reports agree on the window of opportunity.`,
    `The charts of their anchorage are complete. Timing is the only open question.`,
    cropFl ? `Their ${cropFl.stimulant} houses trade in your currency.` : `Their harbors are already familiar with your flag.`,
  ], s);
}

/**
 * Returns a mineral detection description.
 */
export function getMineralDetectionText(mineral, archName, seed) {
  const s = seed ?? hashStr(archName);
  const POOLS = {
    C: [
      `Surface bitumen seeps have been mapped near ${archName}. Local inhabitants treat the sites as sacred — the eternal flame tradition. Geological assessment indicates significant recoverable naphtha.`,
      `A geological survey of islands near ${archName} shows carbon-bearing strata consistent with naphtha formations. Exploitation threshold: tech 7. The survey record is being filed.`,
      `Prospectors mapping the ${archName} shelf have confirmed subsurface naphtha deposits. The scramble will reach here. When is the question.`,
    ],
    Pu: [
      `Mineral surveys near ${archName} have identified pyra-bearing volcanic formations. No exploitation pathway at current technology. The record has been filed — and will be revisited.`,
      `Geological cores from ${archName} show pyra concentrations in the volcanic substrate. Strategic value: none at current tech. Known value: considerable, when fission arrives.`,
    ],
    Au: [
      `Alluvial surveys of waterways near ${archName} indicate recoverable chrysos. Your merchant guild will take interest before your admiralty does.`,
      `Surface chrysos has been reported by fishing crews operating near ${archName}. The rumors have reached the guild houses.`,
    ],
    Cu: [
      `Volcanic outcrops near ${archName} show aes-bearing formations. Metallurgists in your harbor districts have submitted acquisition proposals.`,
      `An aes deposit near ${archName} has been confirmed. Your foundries are at capacity — but another source creates options.`,
    ],
  };
  const options = POOLS[mineral];
  if (!options) return `Unusual geological formations near ${archName} have been surveyed. Report filed.`;
  return pick(options, s);
}

/**
 * Returns epidemic risk card body text.
 */
export function getEpidemicRiskText(sourceName, contactCount, seed) {
  const s = seed ?? hashStr(sourceName);
  return pick([
    `Merchant vessels arriving from ${sourceName} have reported unusual illness among dock crews. The contact network that enriches you creates vectors the quarantine officers are only now learning to map.`,
    `Three ships from ${sourceName} arrived this season with crews showing fever symptoms. With ${contactCount} active trade contacts, a pathogen that travels the relay network will reach your harbors. When is the question.`,
    `Intelligence from ${sourceName} indicates a disease event of uncertain severity. Your trade routes and their trade routes overlap significantly. Restricting contact reduces the risk — and the revenue.`,
  ], s);
}

/**
 * Returns a piracy warning card body.
 * contacts: int, tech: float, seed: int
 */
export function getPiracyWarningText(contacts, tech, seed) {
  const s = seed ?? 0;
  return pick([
    `Trade convoys on your relay routes are reporting losses to opportunistic seizure. With ${contacts} active contacts, the surface area of your trade network has outpaced your escort capacity. The math of piracy is simple: target value divided by interdiction risk. For some of your outlying routes, that ratio has turned unfavorable.`,
    `Your merchant fleet is operating across multiple relay hops without consistent escort. ${contacts} active trade relationships create ${contacts} vectors for seizure. The old maritime prize law distinction between privateers and pirates is theoretical — your cargo captains don't have time to read charters.`,
    `Pirate confederacies operating from unheld islands are targeting your cargo ships between hops. This is not a patrol gap — it is a structural feature of any trade network that expands faster than the naval force protecting it. At tech ${tech.toFixed(1)}, the balance of arms slightly favors the defenders. Slightly.`,
  ], s);
}

/**
 * Returns a tech decay warning card body.
 * prevTech, currTech: float, seed: int
 */
export function getTechDecayText(prevTech, currTech, seed) {
  const s = seed ?? 0;
  const loss = (prevTech - currTech).toFixed(1);
  return pick([
    `Your technology level has declined from ${prevTech.toFixed(1)} to ${currTech.toFixed(1)}. Energy surplus no longer covers maintenance costs. Research institutions are mothballed when they can't pay their scholars — and those scholars disperse, and do not return.`,
    `Maintenance costs exceed your available energy surplus. Technology level has slipped ${loss} points. Civilizations that have crossed this threshold describe it as a ratchet: the decline is faster than the recovery, because the institutions that produce knowledge require continuous investment.`,
    `Your tech advantage has eroded by ${loss} points this cycle. The qahwa houses in your administrative district, where the educated class congregates, are reporting a mood shift. When technical capacity declines, political confidence follows.`,
  ], s);
}

/**
 * Returns a navigator guild tension card body.
 * tech: float, seed: int
 */
export function getNavigatorGuildText(tech, seed) {
  const s = seed ?? 0;
  return pick([
    `The navigator's guild has filed a formal protest against the proliferation of automated position-fixing. Their argument is not sentimental: if a ship's crew cannot navigate by stars when the instrument fails, the ship is an accident waiting for the right conditions. The guild's casualty statistics are correct. The cost of their institutional resistance is also real.`,
    `The guild of navigators — selected through rigorous examination, carriers of individually calibrated instruments, professional caste going back to the first gap crossings — views the new automated celestial-fix systems as an existential threat to institutional knowledge. Both positions have merit. You are required to have an opinion.`,
    `A navigator's guild delegation has presented an unusual argument: the new position-fixing technology doesn't merely make navigators redundant, it makes navigators who can no longer navigate by hand without it. The guild wants certification requirements that mandate manual navigation alongside any automated system. Their proposal is technically sound and commercially inconvenient.`,
  ], s);
}

/**
 * Returns a malaria medical breakthrough card body.
 * tropicalArches: int (number of tropical holdings), seed: int
 */
export function getMalariaBreakthroughText(tropicalArches, seed) {
  const s = seed ?? 0;
  return pick([
    `Medical knowledge derived from your research programs has produced the first effective treatment against the endemic fevers of equatorial archipelagos. Your ${tropicalArches} tropical holding${tropicalArches > 1 ? 's' : ''} — previously costly to garrison — now carry a penalty reduced by 70%. The carrying capacity of your equatorial territories has effectively expanded without a single new island.`,
    `A pharmacological breakthrough: your medical corps has isolated the effective compound in bark preparations that equatorial populations have used for generations. Garrisoning tropical archipelagos was previously a death sentence for temperate-origin troops. It is now merely expensive. Your ${tropicalArches} equatorial holding${tropicalArches > 1 ? 's' : ''} can now be administered rather than merely occupied.`,
    `Empirical medicine has caught up to traditional knowledge. The plant preparations your equatorial contacts have used for generations — which your physicians dismissed as superstition — have proven pharmacologically sound. Your tropical garrison mortality has dropped substantially. ${tropicalArches} archipelago${tropicalArches > 1 ? 's' : ''} that were administrative liabilities are becoming viable territories.`,
  ], s);
}

/**
 * Returns a culture-drift card body.
 */
export function getCultureDriftText(oldLabel, newLabel, ci, io, seed) {
  const s = seed ?? 0;
  const direction = (() => {
    if (io > 0.2) return 'outward-facing, commercially engaged with the wider world';
    if (io < -0.2) return 'inward-facing, self-reliant, resistant to outside authority';
    if (ci > 0.2) return 'individualist, commercially competitive, resistant to central coordination';
    if (ci < -0.2) return 'collectivist, institutionally unified, capable of mass mobilization';
    return 'balanced — stable but without a defining strategic character';
  })();
  const cause = pick([
    'A generation of sustained trade contact has shifted your people\'s political character.',
    'Three cycles of expansion and absorption have changed your institutional culture.',
    'Resource pressure and the collective response it required has moved your political center.',
    'Prosperity from the relay trade has individualized your merchant class and, through them, your institutions.',
    'Prolonged isolation from external contact has turned your civilization inward.',
  ], s);
  return `Your civilization has shifted from ${oldLabel} to ${newLabel}. ${cause} Your people are now ${direction}.`;
}

/**
 * Returns a religious revival situation card body.
 * piety: float (0-1), tech: float, isCollective: bool, seed: int
 */
export function getReligiousRevivalText(piety, tech, isCollective, seed) {
  const s = seed ?? 0;
  const fervorLevel = piety > 0.80 ? 'exceptional' : piety > 0.65 ? 'significant' : 'moderate';
  if (isCollective) {
    return pick([
      `Religious fervor at ${fervorLevel} intensity is functioning as a centripetal force in your polity. Disputed territories are being incorporated faster than the administrative model predicted — conversion and cultural assimilation proceeding in parallel with physical occupation. Your political theologians describe this as the canonical model: the faith as empire-builder. The historical precedents are large.`,
      `Your institutional religion has become an integrative technology. Absorbed populations are converting at rates that exceed your garrison capacity to enforce — which means they are converting voluntarily, under social pressure rather than coercion. This is the efficient mechanism. The absorbed polity's traditional practices are becoming syncretic accretions to your own rather than sites of resistance. The ${fervorLevel} piety reading across your territory represents political cohesion, not just spiritual sentiment.`,
      `Your religious establishment has outpaced your administrative corps in the newly absorbed territories. Ritual houses, pilgrimage circuits, sacred market days — the physical infrastructure of faith is being built faster than tax collection infrastructure. The result is a population that identifies as yours before the paperwork confirms it. Piety at ${fervorLevel} levels is currently your cheapest integration technology.`,
    ], s);
  } else {
    return pick([
      `A ${fervorLevel} religious revival is sweeping your merchant and administrative classes. The timing is notable: revivals in competitive, individualist societies typically follow a resource shock or a military setback — a search for meaning in structural failure. Your analysts are uncertain whether this represents a genuine cultural turn or a fashion. The policy implications differ significantly.`,
      `Piety at ${fervorLevel} levels is producing a strategic anomaly: your expansion-oriented culture is suddenly acquiring a missionary character. Expeditions that were commercial in mandate are returning with accounts of spiritual purpose. Whether this represents a genuine shift in your civilization's character or a useful post-hoc narrative for conquest is, functionally, the same question.`,
      `Your religious institutions are experiencing ${fervorLevel} activity in a civilization whose individualism typically resists collective spiritual authority. The pattern suggests a social technology function rather than a purely spiritual one: in the absence of other cohesive institutions, religious community provides the coordination mechanism. This is historically common. It is also, historically, a precursor to significant political change.`,
    ], s);
  }
}

/**
 * Dispatch text for a religious revival event.
 */
export function getReligiousRevivalDispatch(polityName, piety, seed) {
  const s = seed ?? 0;
  const intensity = piety > 0.80 ? 'HIGH' : piety > 0.65 ? 'ELEVATED' : 'MODERATE';
  return pick([
    `INTERNAL AFFAIRS — Religious activity index at ${intensity} across ${polityName} territory. Integration rates in newly absorbed archipelagos exceeding baseline. Sovereignty acceleration detected.`,
    `INTERNAL AFFAIRS — Piety index elevated to ${intensity} in ${polityName}. Missionary expansion pressure building. Absorption efficiency in tropical territories above projection.`,
    `INTERNAL AFFAIRS — Fervor reading: ${intensity}. ${polityName} faith infrastructure deployment in peripheral territories outpacing administrative settlement. Recommend monitoring conversion rates.`,
  ], s);
}
