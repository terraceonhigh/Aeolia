# AEOLIA — GODOT 4 MIGRATION HANDOFF

## For: Claude Code instance
## From: Claude chat session (conversation history in docs/)
## Date: April 2026

---

## What This Is

Aeolia is a worldbuilding simulation engine for a speculative fiction
project — a planet 4.6× Earth's size, 95% ocean, where human
civilizations developed on volcanic archipelagos isolated for 100,000
years and are now being reconnected by nuclear-powered seaplanes.

The simulation generates procedural worlds from a seed number:
42 archipelagos, each with computed climate, agriculture, trade goods,
political culture, mode of production, and a 5,000-year political
history of contact, colonization, and independence.

## What Exists

### The Series Bible (11 files in docs/)
The narrative foundation. 00–10 markdown files defining the planet's
physics, history, civilizations, technology, characters, culture,
maritime traditions, contact sequence, and visual style. READ THESE
FIRST — they are the source of truth for every design decision.

### The Design Spec (docs/DESIGN_SPEC.md)
1,352 lines. The simulation architecture we designed over a long
conversation. Includes:
- §0: Core principle — hegemonic contingency (the Reach and Lattice
  are geographically lucky, not superior)
- §1-2: 50-year tick structure, rumor propagation
- §3-4: Distributed Dark Forest beliefs, IR theory posture selection
- §5-6: Solow-Romer budget, Thompson Sampling edge selection
- §7-8: Hegemon motivation, continuous political-economy space
- §9: Civilizational personality (primordialist + modernist layers)
- §10a-g: Crops, trade goods, Almond-Verba political culture,
  Marxian mode of production, minerals

The spec distinguishes DECIDED items (ready to implement) from
HOOKS (designed but not yet coded) from OPEN QUESTIONS.

### The Monolith (src/MONOLITH_REFERENCE.jsx)
2,282 lines of React/Three.js in a single file. This is the working
prototype — a 3D globe with:
- Cube-sphere terrain with quadtree LOD (25×25 tiles, max depth 10)
- Procedural height via FBM noise + domain-warped volcanic peaks
- Submarine plateaus with domain-warped shelf blobs
- Dual-source Dijkstra political history engine
- Population model across 5 eras
- Σ2^n discovery curve redistribution
- Urban overlay (buildings, settlement detection)
- Floating labels with hemisphere culling
- Click-to-popup arch detail panel
- Static substrate cascade (climate → crops → trade → culture)
- Sea-level slider (glacial simulation)
- Seed input for world regeneration

It works but outgrew the artifact sandbox (116KB, WebGL context
failures). The code is not modular — everything is in one file.
This is what needs to be decomposed and migrated.

### Extracted Modules (src/engine/)
Partial decomposition — the simulation logic extracted from the
monolith into separate files:
- rng.js — Mulberry32 PRNG (clean, ready to use)
- constants.js — All shared constants, crop definitions, names
- terrain.js — Height function and noise (clean, ready to use)
- world.js — World generation (references substrate/history/settlements)
- history_raw.js — Raw extract of the Dijkstra history engine
- substrate_raw.js — Raw extract of the substrate cascade
- settlements_raw.js — Raw extract of settlement detection

The _raw files need cleanup: remove Three.js references, add proper
imports/exports, fix the REACH_ARCH/LATTICE_ARCH globals.

---

## The Migration Plan

### Phase 1: Simulation Layer (Pure GDScript or JS)

The simulation is a pure function: seed → WorldState. No rendering.

```
WorldState = {
  archs: [{cx,cy,cz, peaks, shelfR}],      // 42 archipelagos
  edges: [{ax,ay,az, bx,by,bz, ...}],       // plateau connections
  plateauEdges: [[i,j], ...],                // adjacency pairs
  substrate: [{climate, crops, tradeGoods,   // per-arch substrate
               politicalCulture, production,
               minerals, narrative}],
  history: {states, log, dfYear, ...},       // political history
  settlements: [{cx,cy,cz, kind, ...}],      // cities/ports
  reachArch, latticeArch,                    // core power indices
  seed,
}
```

This can be implemented in:
- **GDScript** (native, fast iteration in Godot)
- **JavaScript via GDExtension** (reuse existing code)
- **C++ via GDExtension** (performance, if needed for batch runs)

Recommendation: GDScript for the simulation, with the option to
port to C++ later if 10,000-seed batch analysis is needed.

### Phase 2: Globe View (Godot 3D)

Port the current renderer to Godot's 3D scene system:

```
Godot Scene Tree:
  World (Node3D)
  ├── Globe (MeshInstance3D)
  │   ├── TerrainQuadtree (custom LOD system)
  │   │   └── TerrainTile × N (procedural mesh generation)
  │   ├── PlateauGraph (ImmediateGeometry3D)
  │   │   ├── EdgeArcs (great-circle lines)
  │   │   └── ShelfBlobs (at arch centers)
  │   └── ArchLabels (Label3D × 42)
  │       └── Hemisphere visibility check in _process()
  ├── Buildings (MultiMeshInstance3D)
  │   ├── ReachMaterial (warm dark — timber, ceramic)
  │   ├── LatticeMaterial (cool dark — steel, concrete)
  │   └── OtherMaterial (neutral)
  ├── Camera (Camera3D)
  │   └── ArcballController (script)
  ├── Lighting
  │   ├── DirectionalLight3D (sun)
  │   └── WorldEnvironment (maritime atmosphere)
  └── UI (CanvasLayer)
      ├── Sidebar (political map log)
      ├── Popup (arch detail panel with substrate)
      ├── Controls (seed, sliders, toggles)
      └── Header
```

Key Godot features to use:
- **SurfaceTool** or **ArrayMesh** for procedural terrain generation
- **MultiMeshInstance3D** for instanced buildings (thousands of boxes)
- **Shader material** for terrain coloring (altitude, faction, urban overlay)
- **Label3D** for floating arch names
- **RichTextLabel** in CanvasLayer for the popup/sidebar

### Phase 3: LOD Descent (Globe → City → Street)

The scene tree extends downward:

```
LOD 0: Orbital     — Globe with terrain displacement
LOD 1: Archipelago — Individual islands visible
LOD 2: Island      — Coastline detail, settlement markers
LOD 3: City        — Building blocks, harbor, roads
LOD 4: District    — Architecture, railways, piers
LOD 5: Street      — Boats, cable cars, market stalls

Each LOD is a scene that loads/unloads as camera descends.
The substrate data tells each scene WHAT to generate:

LOD 3 reads: substrate.crops.primaryCrop
  → paddi: tidal flat terraces along coast
  → emmer: hillside grain terraces

LOD 4 reads: history.states.faction
  → reach: curved rooflines, red columns, timber
  → lattice: steel frame, glass curtain wall, neon

LOD 5 reads: substrate.tradeGoods.stimulant.type
  → char: tea houses on stepped lanes
  → qahwa: coffee houses near the harbor
```

### Phase 4: Full Tick Simulation

Implement the spec's 8-stage tick pipeline:
1. Rumor propagation
2. Belief update (distributed Dark Forest)
3. Posture selection (IR theory)
4. Budget allocation (Solow-Romer)
5. Edge selection (Thompson Sampling)
6. Expedition resolution
7. Status evaluation
8. Population/tech/trade update

This is the most complex phase. The design spec (§1-8) has the
full architecture. Implement incrementally:
- First: simple Dijkstra wavefront (what exists now)
- Then: add tick-based expansion with budget
- Then: add Thompson Sampling for edge selection
- Then: add beliefs and posture
- Then: add contradiction tensors

---

## Critical Design Decisions (Already Made)

Read the DESIGN_SPEC.md §11 "Resolved" section for the full list.
Key decisions:

1. **Budget model**: Thompson Sampling (which edges to explore) +
   Solow-Romer production function (how many expeditions per tick)

2. **Culture theory**: Primordialist substrate (geographic, stable)
   + Modernist identity (reactive, per-tick drift after contact)

3. **Status assignment**: Continuous sovereignty-trade space.
   Named statuses (colony, garrison, tributary, etc.) are region
   labels derived from position, never assigned directly.

4. **Political culture**: Almond & Verba (parochial/subject/civic)
   initialized from crop type, drifts per tick.

5. **Mode of production**: Two continuous axes (surplus
   centralization × labor commodification). Marxian modes as
   regions. Contradiction as computable tension vector.
   Forbidden zone: labor ≤ surplus + 0.3.

6. **Hegemonic contingency (§0)**: The Reach and Lattice are
   geographically lucky, not inherently superior. The simulation
   must produce 3-5 independently sophisticated civilizations.

---

## Godot Project Setup

```bash
# Create Godot 4.x project
mkdir aeolia-godot && cd aeolia-godot

# Project structure
aeolia-godot/
├── project.godot
├── src/
│   ├── simulation/
│   │   ├── rng.gd
│   │   ├── constants.gd
│   │   ├── world_generator.gd
│   │   ├── substrate.gd
│   │   ├── history_engine.gd
│   │   ├── settlement_detector.gd
│   │   └── terrain_math.gd
│   ├── rendering/
│   │   ├── globe/
│   │   │   ├── terrain_quadtree.gd
│   │   │   ├── terrain_tile.gd
│   │   │   ├── plateau_renderer.gd
│   │   │   └── globe_scene.tscn
│   │   ├── buildings/
│   │   │   ├── building_generator.gd
│   │   │   └── faction_materials.tres
│   │   ├── labels/
│   │   │   └── arch_label.gd
│   │   └── camera/
│   │       └── arcball_camera.gd
│   ├── ui/
│   │   ├── sidebar.tscn
│   │   ├── popup.tscn
│   │   ├── controls.tscn
│   │   └── theme.tres
│   └── main.gd
├── assets/
│   └── fonts/
│       └── jetbrains_mono.ttf
├── docs/
│   ├── DESIGN_SPEC.md
│   └── (series bible files)
└── reference/
    └── MONOLITH_REFERENCE.jsx   # the original, for comparison
```

### GDScript Translation Notes

The JavaScript simulation code maps to GDScript almost 1:1:

```javascript
// JavaScript
function mulberry32(a) {
  return function() {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    // ...
  };
}
```

```gdscript
# GDScript
class_name RNG

var state: int

func _init(seed: int) -> void:
    state = seed

func next_float() -> float:
    state = (state + 0x6D2B79F5) & 0xFFFFFFFF
    var t = ((state ^ (state >> 15)) * (1 | state)) & 0xFFFFFFFF
    t = (t + ((t ^ (t >> 7)) * (61 | t))) & 0xFFFFFFFF
    return float((t ^ (t >> 14)) & 0x7FFFFFFF) / 2147483648.0
```

Key differences:
- GDScript uses `Vector3` natively (no {x,y,z} objects)
- Array operations: `array.filter()` → manual loop or `Array.filter()`
- No closures for RNG — use a class instead
- `Math.floor()` → `floori()`, `Math.sqrt()` → `sqrt()`
- Dictionaries use `{}` syntax like JS but typed with `:=`

### Terrain Shader

The height function should move to a compute shader for GPU
performance. The CPU version (terrain.js) is the reference
implementation. The GPU version samples the same noise functions
but runs per-vertex in parallel.

```glsl
// terrain.gdshader (vertex shader)
shader_type spatial;

uniform float sea_level = 0.0;
uniform float bridge_width = 0.13;

// ... noise functions ported from terrain.js ...

void vertex() {
    vec3 sphere_pos = normalize(VERTEX);
    float h = compute_height(sphere_pos, sea_level, bridge_width);
    VERTEX = sphere_pos * (1.0 + h * DISPLACEMENT_SCALE);
    // Color from altitude
    COLOR = altitude_color(h, sea_level);
}
```

---

## What to Build First

1. **Create Godot project** with the directory structure above.

2. **Port rng.gd and constants.gd** — these are trivial, do them
   first to establish the pattern.

3. **Port world_generator.gd** — arch generation, edge network,
   Reach/Lattice selection. Test by printing arch positions.

4. **Build the globe renderer** — a single IcoSphere with a shader
   that samples the height function. Get the planet visible.

5. **Port substrate.gd** — climate, crops, trade goods. Test by
   printing substrate data for each arch.

6. **Port history_engine.gd** — Dijkstra wavefront, population.
   Test by printing the political log.

7. **Build the UI** — sidebar, popup, controls. Wire everything up.

8. **Add buildings, labels, interactivity** — the polish layer.

Each step is independently testable. Don't proceed to the next
until the current one produces correct output.

---

## Files in This Handoff Package

```
handoff/
├── HANDOFF.md                    ← YOU ARE HERE
├── src/
│   ├── engine/
│   │   ├── rng.js                — PRNG (clean, portable)
│   │   ├── constants.js          — All constants + crop/name data
│   │   ├── terrain.js            — Height function (clean, portable)
│   │   ├── world.js              — World generation (needs settlements.js)
│   │   ├── history_raw.js        — Dijkstra engine (needs cleanup)
│   │   ├── substrate_raw.js      — Substrate cascade (needs cleanup)
│   │   └── settlements_raw.js    — Settlement detection (needs cleanup)
│   ├── MONOLITH_REFERENCE.jsx    — The complete working prototype
│   └── data/                     — (empty, constants.js has all data)
└── docs/
    ├── DESIGN_SPEC.md            — Simulation architecture v0.4
    ├── 00_SERIES_BIBLE.md        — Master document index
    ├── 01_PLANET_AND_PHYSICS.md  — Physical parameters
    ├── 02_HISTORICAL_TIMELINE.md — 500,000 BP to present
    ├── 03_THE_REACH.md           — Anglo-Saxon thalassocracy
    ├── 04_THE_LATTICE.md         — Hydraulic bureaucracy
    ├── 05_TECHNOLOGY.md          — Maritime, aviation, nuclear, comms
    ├── 06_CHARACTERS.md          — All named characters
    ├── 07_CULTURAL_ATLAS.md      — Daily life, food, gender, religion
    ├── 08_MARITIME_TRADITIONS.md — Sailing, navigation, piracy
    ├── 09_CONTACT_SEQUENCE.md    — Artifacts, first contact, recursion
    └── 10_VISUAL_AND_TONE_GUIDE.md — Aesthetic direction
```

---

## The _raw Files Need Cleanup

The `*_raw.js` files are direct extracts from the monolith.
They need:

1. **Remove global variables**: `REACH_ARCH` and `LATTICE_ARCH`
   are module-level `let` in the monolith. Pass as parameters.

2. **Add imports**: They reference `mulberry32`, `POLITY_NAMES`,
   `ISLAND_MAX_HEIGHT`, etc. from the monolith's top scope.

3. **Add exports**: Each file should export its main function.

4. **Type annotations**: Optional but helpful. The substrate
   function returns a well-defined shape (see DESIGN_SPEC §10).

The `rng.js`, `constants.js`, and `terrain.js` files are already
clean and portable. Start from those.

---

*Handoff prepared by Claude (Anthropic), April 2026.*
*The fish is still good.*
