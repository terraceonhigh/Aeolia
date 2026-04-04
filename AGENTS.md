# AGENTS.md — Aeolia

## What This Is

Aeolia is a worldbuilding simulation engine being migrated from a React/Three.js monolith to Godot 4. The simulation generates procedural worlds from a seed: 42 volcanic archipelagos on a planet 4.6× Earth's size, with computed climate, agriculture, trade, political culture, and 5,000-year political history.

## Read Order

Before writing any code, read these files in order:

1. `HANDOFF.md` — Migration plan, project structure, build order
2. `docs/DESIGN_SPEC.md` — Simulation architecture (1,300+ lines, the technical source of truth)
3. `docs/00_SERIES_BIBLE.md` — Index to the 11 narrative docs (read as needed)

## Source of Truth

- **Narrative**: `docs/00_SERIES_BIBLE.md` through `docs/10_VISUAL_AND_TONE_GUIDE.md`
- **Simulation design**: `docs/DESIGN_SPEC.md` — distinguishes DECIDED, HOOK, and OPEN QUESTION items
- **Reference implementation**: `src/MONOLITH_REFERENCE.jsx` (2,281 lines, the working prototype)
- **Clean extracted modules**: `src/engine/rng.js`, `src/engine/constants.js`, `src/engine/terrain.js`
- **Raw extracts needing cleanup**: `src/engine/history_raw.js`, `src/engine/substrate_raw.js`, `src/engine/settlements_raw.js`

## Architecture

The simulation is a pure function: `seed → WorldState`. No rendering dependency.

```
WorldState = {
  archs[42]:    { cx, cy, cz, peaks, shelfR, ... }
  edges[]:      { ax, ay, az, bx, by, bz, ... }
  substrate[]:  { climate, crops, tradeGoods, politicalCulture, production, minerals }
  history:      { states, log, dfYear, ... }
  settlements:  { cx, cy, cz, kind, ... }
  reachArch, latticeArch, seed
}
```

The substrate cascade is deterministic and geographic:
`latitude/peaks/shelf → climate → crops → tradeGoods → politicalCulture → modeOfProduction`

## Critical Design Constraints

1. **Hegemonic contingency (§0)**: The Reach and Lattice are geographically lucky, not superior. The simulation must produce 3–5 independently sophisticated civilizations per seed.

2. **Determinism**: Same seed must always produce the same world. All randomness flows from `mulberry32(seed)`. Never use `Math.random()` or Godot's built-in RNG.

3. **Separation of concerns**: Simulation produces data. Rendering consumes it. They never mix. No Three.js/Godot imports in simulation code.

4. **Status is derived, not assigned**: Political statuses (colony, tributary, etc.) are labels for regions in a continuous sovereignty–trade space. Never assign them directly.

5. **The forbidden zone**: In the mode-of-production space, `labor_commodification ≤ surplus_centralization + 0.3`. This is a hard constraint.

## Migration Target

Godot 4 with GDScript. The build order from HANDOFF.md:

1. `rng.gd` + `constants.gd` (trivial ports)
2. `world_generator.gd` (arch generation, edge network)
3. Globe renderer (IcoSphere + height shader)
4. `substrate.gd` (climate, crops, trade goods)
5. `history_engine.gd` (Dijkstra wavefront, population)
6. UI (sidebar, popup, controls)
7. Buildings, labels, interactivity

Each step is independently testable. Don't proceed until the current step produces correct output.

## GDScript Translation Notes

- `mulberry32` closure → RNG class with `state` field and `next_float()` method
- `{x, y, z}` objects → `Vector3`
- `Math.floor()` → `floori()`, `Math.sqrt()` → `sqrt()`
- `array.filter(fn)` → manual loop or `Array.filter()`
- No closures for stateful functions — use classes
- Integers must be masked with `& 0xFFFFFFFF` to emulate 32-bit overflow

## The _raw Files

`history_raw.js`, `substrate_raw.js`, and `settlements_raw.js` are direct extracts from the monolith. Before porting, they need:

- Global `REACH_ARCH` / `LATTICE_ARCH` → passed as parameters
- Missing imports added (`mulberry32`, `POLITY_NAMES`, `ISLAND_MAX_HEIGHT`, etc.)
- Exports added for main functions
- Three.js references removed

Use `rng.js`, `constants.js`, and `terrain.js` as the model for clean module structure.

## Testing

There is no test harness yet. Validate each module by comparing output against the monolith:

- **rng.gd**: `RNG.new(42).next_float()` for 10 calls should match `mulberry32(42)()` for 10 calls
- **world_generator.gd**: Arch positions and edge count for seed 42 should match the monolith
- **substrate.gd**: Print substrate for each arch and compare to monolith's popup data
- **history_engine.gd**: Political log entries should match monolith's sidebar output

## Don'ts

- Don't use Godot's built-in `RandomNumberGenerator` — use the ported Mulberry32
- Don't hardcode Reach/Lattice behavior — they emerge from geography
- Don't put rendering logic in simulation files
- Don't skip the series bible — design decisions that look arbitrary have narrative reasons
- Don't implement HOOK or OPEN QUESTION items from the design spec without discussing first

## Code Exploration Policy
Use `cymbal` CLI for code navigation — prefer it over Read, Grep, Glob, or Bash for code exploration.
- **New to a repo?**: `cymbal structure` — entry points, hotspots, central packages. Start here.
- **To understand a symbol**: `cymbal investigate <symbol>` — returns source, callers, impact, or members based on what the symbol is.
- **To understand multiple symbols**: `cymbal investigate Foo Bar Baz` — batch mode, one invocation.
- **To trace an execution path**: `cymbal trace <symbol>` — follows the call graph downward (what does X call, what do those call).
- **To assess change risk**: `cymbal impact <symbol>` — follows the call graph upward (what breaks if X changes).
- Before reading a file: `cymbal outline <file>` or `cymbal show <file:L1-L2>`
- Before searching: `cymbal search <query>` (symbols) or `cymbal search <query> --text` (grep)
- Before exploring structure: `cymbal ls` (tree) or `cymbal ls --stats` (overview)
- To disambiguate: `cymbal show path/to/file.go:SymbolName` or `cymbal investigate file.go:Symbol`
- First run: `cymbal index .` to build the initial index (<1s). After that, queries auto-refresh — no manual reindexing needed.
- All commands support `--json` for structured output.
