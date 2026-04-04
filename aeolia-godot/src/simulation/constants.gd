## Shared constants for the Aeolia simulation.
## All magic numbers live here. Imported by every other simulation module.
class_name Constants
extends RefCounted

# -- Planet Parameters --
const PLANET_RADIUS := 1.0           # Normalized unit sphere
const OCEAN_DEPTH_BASE := -4500.0    # meters (cosmetic, for height function)
const ISLAND_MAX_HEIGHT := 3200.0    # meters above sea level
const PLATEAU_HEIGHT := -120.0       # meters (submarine shelf depth)
const ARCH_COUNT := 42               # number of archipelagos

# -- Physical Scale --
const CIRCUMFERENCE_KM := 185000.0
const RADIUS_KM := 29440.0
const SURFACE_GRAVITY := 9.81
const ATMOSPHERE_PRESSURE := 1.7     # atm (1.5-2.0 range)
const RAINFALL_MULTIPLIER := 1.4     # Aeolia vs Earth at same latitude

# -- Simulation Timing --
const ANTIQUITY_START := -20000
const ACTIVE_SIM_START := -5000
const TICK_YEARS := 50
const TOTAL_TICKS := 100             # -5000 to 0 BP

# -- Hegemon Parameters --
const REACH_START := -5500           # aggressive explorer
const LATTICE_START := -5000         # older civilization, defensive

# -- Edge Network --
const MAX_EDGE_ANGLE := 0.9          # radians (~26,000 km max plateau span)
const MIN_NEIGHBORS := 2

# -- Polity Names --
# Index 0 = Reach, Index 1 = Lattice, rest shuffled per seed.
const POLITY_NAMES: Array[String] = [
	"The Reach",       # Anglo-Saxon thalassocracy
	"The Lattice",     # Hydraulic bureaucracy
	"The Gyre",        # Greek/Mediterranean
	"The Narrows",     # Turkish/Ottoman
	"The Shelf",       # Indian subcontinent
	"The Traverse",    # Polynesian
	"The Loom",        # West African
	"The Windward",    # Caribbean
	"The Caldera",     # Japanese
	"The Strand",      # Nordic/Scandinavian
	"The Bight",       # Gulf of Guinea
	"The Cairn",       # Celtic
	"The Shoal",       # Southeast Asian
	"The Polder",      # Dutch
	"The Tidemark",    # Mesopotamian
	"The Breakwater",  # Venetian/Italian
	"The Current",     # Korean
	"The Sargasso",    # Isolated deep-ocean
	"The Atoll",       # Pacific
	"The Meridian",    # Portuguese
	"The Cordage",     # Arab/Omani
	"The Basalt",      # Icelandic
	"The Estuary",     # Egyptian/Nile
	"The Fathom",      # Persian
	"The Wake",        # Maori
	"The Isthmus",     # Mesoamerican
	"The Shingle",     # English Channel
	"The Swell",       # Hawaiian
	"The Trench",      # Mariana/Philippine
	"The Mooring",     # Hanseatic
	"The Reef",        # Australian
	"The Floe",        # Inuit/Arctic
	"The Passage",     # Strait of Malacca
	"The Spindle",     # Ethiopian
	"The Brine",       # Dead Sea/Caspian
	"The Cay",         # Bahamian
	"The Eddy",        # Sri Lankan
	"The Rime",        # Faroese
	"The Berth",       # Singaporean
	"The Forge",       # Cypriot/Sardinian
	"The Drift",       # Micronesian
	"The Quay",        # Phoenician
	"The Seiche",      # Swiss/Alpine lake
	"The Spindrift",   # Falklands/S. Atlantic
	"The Roadstead",   # Zanzibar
	"The Shallows",    # Bangla/Bengal
	"The Tideway",     # Thames/Rhine
	"The Skerry",      # Norwegian
	"The Sound",       # Danish
	"The Lagoon",      # Venetian/Pacific
]

# -- Crop Definitions --
# Each crop carries its associated trade goods, political culture seed,
# and mode-of-production seed values.
const CROPS: Dictionary = {
	"paddi": {
		"name": "Paddi", "earth_analogue": "Rice (Oryza sativa)",
		"calories": 5, "labor": "collective-hydraulic", "storage": "good",
		"stimulant": "char", "fiber": "seric", "protein": "kerbau",
		"political_culture": { "awareness": 0.70, "participation": 0.15 },
		"production_mode": { "surplus": 0.85, "labor": 0.25 },
	},
	"emmer": {
		"name": "Emmer", "earth_analogue": "Wheat (Triticum dicoccum)",
		"calories": 3, "labor": "competitive-individual", "storage": "excellent",
		"stimulant": "qahwa", "fiber": "fell", "protein": "kri",
		"political_culture": { "awareness": 0.70, "participation": 0.70 },
		"production_mode": { "surplus": 0.65, "labor": 0.70 },
	},
	"taro": {
		"name": "Taro", "earth_analogue": "Taro (Colocasia esculenta)",
		"calories": 3, "labor": "chieftain-kinship", "storage": "poor",
		"stimulant": "awa", "fiber": "tapa", "protein": "moa",
		"political_culture": { "awareness": 0.15, "participation": 0.10 },
		"production_mode": { "surplus": 0.55, "labor": 0.15 },
	},
	"nori": {
		"name": "Nori", "earth_analogue": "Seaweed (Pyropia/Porphyra)",
		"calories": 2, "labor": "federated-maritime", "storage": "excellent",
		"stimulant": "", "fiber": "byssus", "protein": "",
		"political_culture": { "awareness": 0.30, "participation": 0.55 },
		"production_mode": { "surplus": 0.35, "labor": 0.55 },
	},
	"sago": {
		"name": "Sago", "earth_analogue": "Sago palm (Metroxylon sagu)",
		"calories": 4, "labor": "loose-communal", "storage": "good",
		"stimulant": "pinang", "fiber": "tapa", "protein": "moa",
		"political_culture": { "awareness": 0.15, "participation": 0.20 },
		"production_mode": { "surplus": 0.10, "labor": 0.05 },
	},
	"papa": {
		"name": "Papa", "earth_analogue": "Potato (Solanum tuberosum)",
		"calories": 3.5, "labor": "kinship-cooperative", "storage": "excellent",
		"stimulant": "aqua", "fiber": "qivu", "protein": "",
		"political_culture": { "awareness": 0.25, "participation": 0.15 },
		"production_mode": { "surplus": 0.20, "labor": 0.10 },
	},
}

# -- Trade Good Names --
const STIMULANTS: Dictionary = {
	"char":   { "name": "Char",   "origin": "Mandarin cha (tea)",      "zone": "paddi" },
	"qahwa":  { "name": "Qahwa",  "origin": "Arabic qahwa (coffee)",   "zone": "emmer" },
	"awa":    { "name": "Awa",    "origin": "Hawaiian awa (kava)",      "zone": "taro" },
	"pinang": { "name": "Pinang", "origin": "Malay pinang (betel)",     "zone": "sago" },
	"aqua":   { "name": "Aqua",   "origin": "Latin aqua vitae (spirits)", "zone": "papa" },
}

const FIBERS: Dictionary = {
	"seric":  { "name": "Seric",  "origin": "Latin sericum (silk)",        "zone": "paddi" },
	"fell":   { "name": "Fell",   "origin": "Old Norse fell (fleece)",     "zone": "emmer" },
	"tapa":   { "name": "Tapa",   "origin": "Polynesian tapa (bark cloth)","zone": "taro/sago" },
	"byssus": { "name": "Byssus", "origin": "Greek byssos (sea-fiber)",    "zone": "nori" },
	"qivu":   { "name": "Qivu",   "origin": "Inuktitut qiviut (underwool)","zone": "papa" },
}

const PROTEINS: Dictionary = {
	"kerbau": { "name": "Kerbau", "origin": "Malay kerbau (water buffalo)", "zone": "paddi" },
	"kri":    { "name": "Kri",    "origin": "Old Norse kid (goat)",          "zone": "emmer" },
	"moa":    { "name": "Moa",    "origin": "Polynesian moa (fowl)",         "zone": "taro/sago" },
}
