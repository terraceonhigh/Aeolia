# Aeolia Godot Port — Rendering Optimization Roadmap

## Phase 1: Lazy Rendering (GDScript) ← CURRENT
- [x] Deferred tile building — tiles build on demand, not all at startup
- [x] Per-frame tile budget — max N tiles built per frame
- [ ] Progressive LOD fill-in — base tiles first, subdivide over frames
- [ ] Loading indicator during initial tile population

## Phase 2: GDExtension C Module
- [ ] Port compute_height to C
- [ ] Port smooth_noise / hash / fbm to C
- [ ] Build system (SCons/CMake) for .dylib/.so
- [ ] GDScript wrapper class
- [ ] Verify bit-identical output vs GDScript version
- [ ] Benchmark: target <1ms per tile at depth 4

## Phase 3: Compute Shader (Orbital Scale)
- [ ] GLSL compute shader for height map generation
- [ ] Buffer textures for edge/archipelago data
- [ ] Shader-generated tiles for depth ≤ 7
- [ ] Seamless handoff to CPU tiles at depth 8+
- [ ] Verify bit-identical base terrain between GPU and CPU paths

## Phase 4: CPU Detail Layer (Street Scale)
- [ ] Erosion simulation (depth 8+)
- [ ] Hydrology / river networks
- [ ] Settlement layout / road networks
- [ ] Building footprint generation
- [ ] Continuous LOD transition — no visible seams between GPU and CPU tiles

## Architecture Invariant
Both GPU (shader) and CPU (C/GDExtension) paths evaluate the same deterministic noise functions with the same parameters. Detail is always additive and scale-dependent — a parent tile's height at any point equals the child tile's height at that point minus the child's fine-detail perturbation. This guarantees seamless zoom from orbit to street level.

## Known Issues
- Archipelago count mismatch: JSX produces 53, Godot produces 42 for seed 42
- OceanSphere backdrop added but not yet visually verified
- Tile seam normals fixed (sphere-point) but not yet visually verified
- Camera distance mapping corrected (R=1 scaling) but not yet visually verified
