// ═══════════════════════════════════════════════════════════
// constants.js — Shared parameters for the Aeolia simulation
// ═══════════════════════════════════════════════════════════

// ── Planet Parameters ──
export const PLANET_RADIUS = 1.0;           // Normalized unit sphere
export const OCEAN_DEPTH_BASE = -4500;      // meters (cosmetic, for height function)
export const ISLAND_MAX_HEIGHT = 3200;      // meters above sea level
export const PLATEAU_HEIGHT = -120;         // meters (submarine shelf depth)
export const ARCH_COUNT = 42;               // number of archipelagos

// ── Physical Scale ──
// The governing constraint: 185,000 km circumference, 4.6× Earth
export const CIRCUMFERENCE_KM = 185000;
export const RADIUS_KM = 29440;
export const SURFACE_GRAVITY = 9.81;        // 1.0g
export const ATMOSPHERE_PRESSURE = 1.7;     // atm (1.5–2.0 range)
export const RAINFALL_MULTIPLIER = 1.4;     // Aeolia vs Earth at same latitude

// ── Simulation Timing ──
export const ANTIQUITY_START = -20000;
export const ACTIVE_SIM_START = -5000;
export const TICK_YEARS = 50;
export const TOTAL_TICKS = 100;             // -5000 to 0 BP

// ── Hegemon Parameters ──
export const REACH_START = -5500;           // aggressive explorer
export const LATTICE_START = -5000;         // older civilization, defensive

// ── Edge Network ──
export const MAX_EDGE_ANGLE = 0.9;         // radians (~26,000 km max plateau span)
export const MIN_NEIGHBORS = 2;

// ── Polity Names ──
// Thinly veiled Earth civilization references.
// Index 0 = Reach, Index 1 = Lattice, rest shuffled per seed.
export const POLITY_NAMES = [
  "The Reach",       // Anglo-Saxon thalassocracy (British maritime arc)
  "The Lattice",     // Hydraulic bureaucracy (Chinese imperial model)
  "The Gyre",        // Greek/Mediterranean — circular, philosophical
  "The Narrows",     // Turkish/Ottoman — strait-controlling chokepoint
  "The Shelf",       // Indian subcontinent — vast, stable, deep-rooted
  "The Traverse",    // Polynesian — wayfinding, open-ocean crossing
  "The Loom",        // West African — textile trade, coast networks
  "The Windward",    // Caribbean — trade-wind corridor, resistance
  "The Caldera",     // Japanese — volcanic chain, insular intensity
  "The Strand",      // Nordic/Scandinavian — coastal raiders, sagas
  "The Bight",       // Gulf of Guinea — deep coastal curve, kingdoms
  "The Cairn",       // Celtic — stone-marker culture, oral tradition
  "The Shoal",       // Southeast Asian — shallow-water trade, spice
  "The Polder",      // Dutch — engineering, reclamation, mercantile
  "The Tidemark",    // Mesopotamian — irrigated agriculture, tidal
  "The Breakwater",  // Venetian/Italian — harbor-city commerce
  "The Current",     // Korean — peninsular, caught between powers
  "The Sargasso",    // Isolated deep-ocean — becalmed, mysterious
  "The Atoll",       // Pacific — coral ring, subsistence, vast ocean
  "The Meridian",    // Portuguese — navigation, cartographic obsession
  "The Cordage",     // Arab/Omani — dhow trade, monsoon sailing
  "The Basalt",      // Icelandic — volcanic isolation, literacy
  "The Estuary",     // Egyptian/Nile — delta civilization, ancient
  "The Fathom",      // Persian — depth, trade, mathematical astronomy
  "The Wake",        // Maori — ocean trail, arrival narrative
  "The Isthmus",     // Mesoamerican — land-bridge, calendrical
  "The Shingle",     // English Channel — pebble beach, fortified
  "The Swell",       // Hawaiian — surf culture, volcanic fertility
  "The Trench",      // Mariana/Philippine — deep-water edge culture
  "The Mooring",     // Hanseatic — merchant league, harbor law
  "The Reef",        // Australian — barrier reef, Indigenous deep-time
  "The Floe",        // Inuit/Arctic — ice-edge adaptation, seasonal
  "The Passage",     // Strait of Malacca — chokepoint trade
  "The Spindle",     // Ethiopian — highland isolation, script
  "The Brine",       // Dead Sea/Caspian — enclosed, mineral-rich
  "The Cay",         // Bahamian — low islands, wrecking, salvage
  "The Eddy",        // Sri Lankan — circular current, crossroads
  "The Rime",        // Faroese — frost culture, wool, saga-keeping
  "The Berth",       // Singaporean — harbor-of-call, entrepôt
  "The Forge",       // Cypriot/Sardinian — island metallurgy, copper
  "The Drift",       // Micronesian — stick-chart navigation, drift
  "The Quay",        // Phoenician — harbor-builder, alphabet-giver
  "The Seiche",      // Swiss/Alpine lake — standing-wave culture
  "The Spindrift",   // Falklands/S. Atlantic — wind-blasted, remote
  "The Roadstead",   // Zanzibar — open anchorage, spice trade
  "The Shallows",    // Bangla/Bengal — delta, monsoon, fishing
  "The Tideway",     // Thames/Rhine — tidal river, industrial
  "The Skerry",      // Norwegian — rocky islet, fjord culture
  "The Sound",       // Danish — strait, toll, passage control
  "The Lagoon",      // Venetian/Pacific — enclosed water, stilts
];

// ── Crop Definitions ──
export const CROPS = {
  paddi: {
    name: "Paddi", earthAnalogue: "Rice (Oryza sativa)",
    calories: 5, labor: "collective-hydraulic", storage: "good",
    stimulant: "char", fiber: "seric", protein: "kerbau",
    politicalCulture: { awareness: 0.70, participation: 0.15 },
    productionMode: { surplus: 0.85, labor: 0.25 },
  },
  emmer: {
    name: "Emmer", earthAnalogue: "Wheat (Triticum dicoccum)",
    calories: 3, labor: "competitive-individual", storage: "excellent",
    stimulant: "qahwa", fiber: "fell", protein: "kri",
    politicalCulture: { awareness: 0.70, participation: 0.70 },
    productionMode: { surplus: 0.65, labor: 0.70 },
  },
  taro: {
    name: "Taro", earthAnalogue: "Taro (Colocasia esculenta)",
    calories: 3, labor: "chieftain-kinship", storage: "poor",
    stimulant: "awa", fiber: "tapa", protein: "moa",
    politicalCulture: { awareness: 0.15, participation: 0.10 },
    productionMode: { surplus: 0.55, labor: 0.15 },
  },
  nori: {
    name: "Nori", earthAnalogue: "Seaweed (Pyropia/Porphyra)",
    calories: 2, labor: "federated-maritime", storage: "excellent",
    stimulant: null, fiber: "byssus", protein: null,
    politicalCulture: { awareness: 0.30, participation: 0.55 },
    productionMode: { surplus: 0.35, labor: 0.55 },
  },
  sago: {
    name: "Sago", earthAnalogue: "Sago palm (Metroxylon sagu)",
    calories: 4, labor: "loose-communal", storage: "good",
    stimulant: "pinang", fiber: "tapa", protein: "moa",
    politicalCulture: { awareness: 0.15, participation: 0.20 },
    productionMode: { surplus: 0.10, labor: 0.05 },
  },
  papa: {
    name: "Papa", earthAnalogue: "Potato (Solanum tuberosum)",
    calories: 3.5, labor: "kinship-cooperative", storage: "excellent",
    stimulant: "aqua", fiber: "qivu", protein: null,
    politicalCulture: { awareness: 0.25, participation: 0.15 },
    productionMode: { surplus: 0.20, labor: 0.10 },
  },
};

// ── Trade Good Names ──
export const STIMULANTS = {
  char:   { name: "Char",   origin: "Mandarin chá (tea)", zone: "paddi" },
  qahwa:  { name: "Qahwa",  origin: "Arabic qahwa (coffee)", zone: "emmer" },
  awa:    { name: "Awa",    origin: "Hawaiian ʻawa (kava)", zone: "taro" },
  pinang: { name: "Pinang", origin: "Malay pinang (betel)", zone: "sago" },
  aqua:   { name: "Aqua",   origin: "Latin aqua vitae (spirits)", zone: "papa" },
};

export const FIBERS = {
  seric:  { name: "Seric",  origin: "Latin sericum (silk)", zone: "paddi" },
  fell:   { name: "Fell",   origin: "Old Norse fell (fleece)", zone: "emmer" },
  tapa:   { name: "Tapa",   origin: "Polynesian tapa (bark cloth)", zone: "taro/sago" },
  byssus: { name: "Byssus", origin: "Greek byssos (sea-fiber)", zone: "nori" },
  qivu:   { name: "Qivu",   origin: "Inuktitut qiviut (underwool)", zone: "papa" },
};

export const PROTEINS = {
  kerbau: { name: "Kerbau", origin: "Malay kerbau (water buffalo)", zone: "paddi" },
  kri:    { name: "Kri",    origin: "Old Norse kið (goat)", zone: "emmer" },
  moa:    { name: "Moa",    origin: "Polynesian moa (fowl)", zone: "taro/sago" },
};
