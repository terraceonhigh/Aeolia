## Procedural globe mesh — cube-sphere with quadtree LOD.
## Matches the JSX reference architecture: 6 cube faces, each recursively
## subdivided based on camera distance. Each leaf tile is a TILE_RES × TILE_RES
## vertex grid mapped to the sphere via cube-sphere projection.
## Detail level scales with quadtree depth: min(4 + depth, 8).
class_name GlobeMesh
extends Node3D

## Displacement multiplier — matches JSX DISP_MULT = 3.4e-8 scaled to R=1
## JSX: R=5, DISP_MULT=3.4e-8 → effective per-unit = 3.4e-8
## Godot: R=1.0 (mesh units), heights in meters. We want the same visual ratio.
## JSX displaces: 1 + (h-seaLevel)*3.4e-8 at R=5 → visual offset = 5 * h * 3.4e-8
## Godot: 1 + h * scale → visual offset = 1 * h * scale → scale = 5 * 3.4e-8 = 1.7e-7
const DISP_SCALE: float = 1.7e-7

## Tile resolution: TILE_RES × TILE_RES vertices per leaf tile.
## Reduced from 25 to 9: GDScript compute_height is ~100x slower than JS,
## so 9×9=81 verts/tile vs 25×25=625 keeps total vertex count manageable.
const TILE_RES: int = 9
## Max quadtree depth
const MAX_DEPTH: int = 10
## Min depth: always split at least this deep (matches JSX MIN_DEPTH=3)
const MIN_DEPTH: int = 3
## Split factor: tile splits when angularSize / distToTileCenter > SPLIT_FACTOR.
## Tuned for R=1 globe with camera distances in the 1–60 range.
## At the default view distance (~22) tiles stay at depth 3; tiles split deeper
## as the camera zooms toward min_distance (~5) giving depth 5–6.
## The original 0.3 was the JSX value where angular_size is scaled by R=5 so
## the effective dimensionless threshold was 0.3/5 = 0.06 — here we use 0.02
## which gives sensible LOD across the full zoom range for an R=1 globe.
const SPLIT_FACTOR: float = 0.06

## GPU compute tile path toggle.
## Set true to use the compute shader (faster); false forces the CPU path (always works).
## Default is false until the compute path is verified on this platform.
@export var use_gpu_tiles: bool = false

## Bridge width scale for TerrainMath
var bw_scale: float = 0.13

## Sea level offset in meters (0 = present, -220 = glacial max)
var sea_level: float = 0.0

## Urbanization overlay mode: 0=off, 1=cities, 2=cities+labels
var urban_mode: int = 0

## Cached world data for tile generation
var _world_data: Dictionary = {}

## Tile mesh cache: key (face_depth_u_v) → ArrayMesh
var _tile_cache: Dictionary = {}

## Currently visible tile MeshInstance3D nodes
var _active_tiles: Array[MeshInstance3D] = []

## Shared material (created once, reused across all tiles)
var _material: StandardMaterial3D

## Track current LOD state for change detection
var _last_cam_pos: Vector3 = Vector3.ZERO
var _needs_rebuild: bool = true
## True while the initial async tile build is in progress; blocks _process LOD updates.
var _building: bool = false

## Deferred build queue: leaf dicts whose meshes have not yet been computed.
## Drained at TILES_PER_FRAME per frame to spread the compute cost over time.
var _build_queue: Array = []
## Keys already enqueued — O(1) duplicate guard.
var _queued_keys: Dictionary = {}
## Keys desired by the most recent LOD pass (stale-check at dequeue time).
var _desired_keys: Dictionary = {}
## Tiles removed from _active_tiles but kept visible while replacement children build.
## Key → MeshInstance3D. Freed once no queued tile overlaps the covered region.
var _phantom_tiles: Dictionary = {}
## Maximum number of new tile meshes built per frame.
const TILES_PER_FRAME: int = 4

# ── Compute shader state ──────────────────────────────────────────────────────
# All null/invalid until _cs_init() succeeds.  Set to null when unavailable
# (Compatibility renderer, Web export, compile failure) so every code path
# safely falls back to _build_tile_cpu().

## Local RenderingDevice — isolated from the render thread.
var _rd: RenderingDevice = null
## Compiled shader and compute pipeline.
var _cs_shader:   RID = RID()
var _cs_pipeline: RID = RID()
## World-data SSBOs (arch, peak, edge) — recreated on each generate() call.
var _cs_arch_buf: RID = RID()
var _cs_peak_buf: RID = RID()
var _cs_edge_buf: RID = RID()
## Pre-allocated output buffer — 81 verts × 12 floats × 4 bytes = 3888 bytes.
## Reused across every tile dispatch (we sync before reading back).
var _cs_out_buf:  RID = RID()
## Single uniform set (set 0) binding all 4 SSBOs.  Recreated on world change.
var _cs_set:      RID = RID()
## True when the compute path is compiled and world data is uploaded.
var _cs_ready: bool = false

func _init() -> void:
	_material = StandardMaterial3D.new()
	_material.vertex_color_use_as_albedo = true
	_material.roughness = 0.95  # JSX: MeshPhongMaterial(shininess:5) — near-fully diffuse/matte
	_material.cull_mode = BaseMaterial3D.CULL_BACK

	# Ocean backdrop sphere — matches JSX IcosahedronGeometry(R*0.998, 5) with MeshPhongMaterial.
	# This is the primary source of the "raised continents / dark ocean" visual: land tiles sit at
	# R≥1.0 while the ocean sphere sits at R=0.998, creating a visible ~0.2% gap that reads as
	# terrain elevation. Without this sphere, ocean and land tiles share the same radius and the
	# globe looks flat with no land/sea distinction.
	var ocean_mesh := SphereMesh.new()
	ocean_mesh.radius = 0.998
	ocean_mesh.height = 1.996
	ocean_mesh.radial_segments = 48
	ocean_mesh.rings = 24
	var ocean_mat := StandardMaterial3D.new()
	# LUT at OCEAN_DEPTH_BASE (-4200m): interpolating between -5000m and -4000m stops
	# gives approximately (0.017, 0.034, 0.098). Previous Color(0.02, 0.05, 0.12) was too bright.
	ocean_mat.albedo_color = Color(0.017, 0.034, 0.098)
	ocean_mat.roughness = 0.95
	ocean_mat.metallic = 0.0
	var ocean_mi := MeshInstance3D.new()
	ocean_mi.name = "OceanSphere"
	ocean_mi.mesh = ocean_mesh
	ocean_mi.material_override = ocean_mat
	add_child(ocean_mi)


## Cube-sphere projection: map (u, v) on a cube face to a unit sphere point
static func _cube_to_sphere(fi: int, u: float, v: float) -> Vector3:
	var x: float; var y: float; var z: float
	match fi:
		0: x = 1.0;  y = v;  z = -u  # +X
		1: x = -1.0; y = v;  z = u   # -X
		2: x = u;    y = 1.0;  z = -v  # +Y
		3: x = u;    y = -1.0; z = v   # -Y
		4: x = u;    y = v;  z = 1.0  # +Z
		5: x = -u;   y = v;  z = -1.0 # -Z
		_: x = 0.0; y = 0.0; z = 1.0
	return Vector3(x, y, z).normalized()


## Initialize the globe with world data. Call once after world generation.
## Builds the 6 base cube faces at depth 0 (6 cheap tiles) for immediate
## visual feedback, then sets _needs_rebuild so update_lod() refines them
## progressively over subsequent frames as the camera position is known.
func generate(world_data: Dictionary, _subdiv: int = 5) -> void:
	_world_data = world_data
	_building = false
	_needs_rebuild = true

	# Lazy init compute pipeline (no-op if already done or unavailable).
	_cs_init()
	# Upload world geometry to GPU (no-op when _rd is null).
	_cs_upload_world_data(
		world_data.get("archs", []),
		world_data.get("edges", [])
	)

	# Seed 6 base faces at depth 0 — covers the whole globe in one quad each.
	# Very fast (~6 × 81 verts). The LOD system will subdivide over frames.
	for fi in 6:
		var leaf := {"fi": fi, "u_min": -1.0, "u_max": 1.0,
			"v_min": -1.0, "v_max": 1.0, "depth": 0,
			"key": "t_%d_0_-1.0000_-1.0000" % fi}
		var tile_mesh: ArrayMesh = _get_or_build_tile(leaf)
		var mi := MeshInstance3D.new()
		mi.name = leaf.key
		mi.mesh = tile_mesh
		mi.material_override = _material
		add_child(mi)
		_active_tiles.append(mi)


## Invalidate the cache (call when world data changes, e.g. new seed).
func clear_cache() -> void:
	_cs_free_world_bufs()  # Drop stale world SSBOs; shader/pipeline stay alive.
	_tile_cache.clear()
	_build_queue.clear()
	_queued_keys.clear()
	_desired_keys.clear()
	for key in _phantom_tiles:
		var t: MeshInstance3D = _phantom_tiles[key]
		if is_instance_valid(t):
			remove_child(t)
			t.queue_free()
	_phantom_tiles.clear()
	# Remove all active tile meshes from the scene
	for tile in _active_tiles:
		if is_instance_valid(tile):
			remove_child(tile)
			tile.queue_free()
	_active_tiles.clear()
	_needs_rebuild = true


## Legacy compatibility: LOD is now handled by quadtree, not distance table
func get_lod_for_distance(_dist: float) -> int:
	return 5  # Dummy; quadtree handles LOD internally


## Parse a tile key into its face/depth/bounds. Returns empty dict on failure.
func _tile_bounds_from_key(key: String) -> Dictionary:
	var parts := key.split("_")
	if parts.size() < 5:
		return {}
	var fi := int(parts[1])
	var depth := int(parts[2])
	var u_min := float(parts[3])
	var v_min := float(parts[4])
	var tile_size: float = 2.0 / pow(2.0, float(depth))
	return {"fi": fi, "u_min": u_min, "u_max": u_min + tile_size,
			"v_min": v_min, "v_max": v_min + tile_size}


## True if any tile currently in _queued_keys overlaps the given bounds.
## Used to decide whether to keep a phantom tile visible as coverage.
func _queued_covers_bounds(bounds: Dictionary) -> bool:
	if bounds.is_empty():
		return false
	for key in _queued_keys:
		var b := _tile_bounds_from_key(key)
		if b.is_empty() or b.fi != bounds.fi:
			continue
		if b.u_min < bounds.u_max and b.u_max > bounds.u_min and \
				b.v_min < bounds.v_max and b.v_max > bounds.v_min:
			return true
	return false


## Update LOD based on camera position. Called from main._process().
## Removes stale tiles immediately and either shows cached tiles instantly
## or enqueues uncached tiles for deferred building in _process().
func update_lod(cam_pos: Vector3) -> void:
	if _building:
		return
	# Only rebuild if camera moved significantly
	if not _needs_rebuild and cam_pos.distance_to(_last_cam_pos) < 0.005:
		return
	_last_cam_pos = cam_pos
	_needs_rebuild = false

	if _world_data.size() == 0:
		return

	# Collect desired leaf tiles from quadtree traversal
	var leaves: Array = []
	for fi in 6:
		_collect_leaves(fi, -1.0, 1.0, -1.0, 1.0, 0, cam_pos, leaves)

	var needed_keys: Dictionary = {}
	for leaf in leaves:
		needed_keys[leaf.key] = leaf
	# Publish so _process() can skip builds that are no longer wanted
	_desired_keys = needed_keys

	# Handle existing phantom tiles: re-promote if desired again, or release if no
	# queued tiles overlap their region any more.
	var phantoms_to_remove: Array = []
	for pk in _phantom_tiles:
		if needed_keys.has(pk):
			_active_tiles.append(_phantom_tiles[pk])
			phantoms_to_remove.append(pk)
		elif not _queued_covers_bounds(_tile_bounds_from_key(pk)):
			var pt: MeshInstance3D = _phantom_tiles[pk]
			remove_child(pt)
			pt.queue_free()
			phantoms_to_remove.append(pk)
	for pk in phantoms_to_remove:
		_phantom_tiles.erase(pk)

	# Remove or phantomize tiles that are no longer needed.
	# Tiles whose region is still being rebuilt become phantoms (stay visible as
	# coverage) rather than being freed immediately, preventing holes.
	var i := 0
	while i < _active_tiles.size():
		var tile: MeshInstance3D = _active_tiles[i]
		if not needed_keys.has(tile.name):
			_active_tiles.remove_at(i)
			var bounds := _tile_bounds_from_key(tile.name)
			if not bounds.is_empty() and _queued_covers_bounds(bounds):
				_phantom_tiles[tile.name] = tile  # keep rendering as coverage
			else:
				remove_child(tile)
				tile.queue_free()
		else:
			# Already visible — mark as satisfied
			needed_keys.erase(tile.name)
			i += 1

	# For each newly needed tile: show immediately if cached, otherwise enqueue.
	for key in needed_keys:
		var leaf = needed_keys[key]
		if _tile_cache.has(key):
			# Free — just a dict lookup and node creation
			var mi := MeshInstance3D.new()
			mi.name = key
			mi.mesh = _tile_cache[key]
			mi.material_override = _material
			add_child(mi)
			_active_tiles.append(mi)
		elif not _queued_keys.has(key):
			_build_queue.append(leaf)
			_queued_keys[key] = true


## Drain the deferred build queue at a fixed per-frame budget.
## Builds at most TILES_PER_FRAME new tile meshes per frame so the globe
## fills in progressively without stalling the render loop.
func _process(_delta: float) -> void:
	var built := 0
	while _build_queue.size() > 0 and built < TILES_PER_FRAME:
		var leaf: Dictionary = _build_queue.pop_front()
		_queued_keys.erase(leaf.key)

		# Skip tiles that the LOD pass no longer wants (camera moved away)
		if not _desired_keys.has(leaf.key):
			continue

		var tile_mesh: ArrayMesh = _get_or_build_tile(leaf)

		# Guard against a concurrent update_lod() already adding this tile
		var already_active := false
		for t in _active_tiles:
			if t.name == leaf.key:
				already_active = true
				break
		if not already_active:
			var mi := MeshInstance3D.new()
			mi.name = leaf.key
			mi.mesh = tile_mesh
			mi.material_override = _material
			add_child(mi)
			_active_tiles.append(mi)

		built += 1

	# After each build batch, release any phantom tiles whose region is now covered.
	if built > 0 and not _phantom_tiles.is_empty():
		var phantoms_to_remove: Array = []
		for pk in _phantom_tiles:
			if _desired_keys.has(pk):
				_active_tiles.append(_phantom_tiles[pk])
				phantoms_to_remove.append(pk)
			elif not _queued_covers_bounds(_tile_bounds_from_key(pk)):
				var pt: MeshInstance3D = _phantom_tiles[pk]
				remove_child(pt)
				pt.queue_free()
				phantoms_to_remove.append(pk)
		for pk in phantoms_to_remove:
			_phantom_tiles.erase(pk)


## Quadtree traversal — recursively collect leaf tiles
func _collect_leaves(fi: int, u_min: float, u_max: float, v_min: float, v_max: float,
		depth: int, cam_pos: Vector3, leaves: Array) -> void:
	# Horizon culling: if tile center is on the far side of the globe, skip
	var center: Vector3 = _cube_to_sphere(fi, (u_min + u_max) / 2.0, (v_min + v_max) / 2.0)
	var cam_dist: float = cam_pos.length()
	if cam_dist > 1.05:  # Only cull when camera is outside the sphere
		# Geometric horizon: dot(center, cam_dir) must be > cutoff
		var cam_dir: Vector3 = cam_pos.normalized()
		var dot_val: float = center.dot(cam_dir)
		# cutoff = cos(acos(1/D) + tile_angular_radius + margin)
		var horizon_angle: float = acos(minf(1.0, 1.0 / cam_dist))
		var tile_half_angle: float = (u_max - u_min) * PI / 4.0  # half the tile's angular span
		var cutoff: float = cos(horizon_angle + tile_half_angle + deg_to_rad(5.0))
		if dot_val < cutoff:
			return

	# Should this tile split?
	var angular_size: float = (u_max - u_min) * PI / 2.0
	var should_split: bool
	if depth >= MAX_DEPTH:
		should_split = false
	elif depth < MIN_DEPTH:
		should_split = true
	else:
		var dx: float = cam_pos.x - center.x
		var dy: float = cam_pos.y - center.y
		var dz: float = cam_pos.z - center.z
		var dist: float = sqrt(dx * dx + dy * dy + dz * dz)
		should_split = (angular_size / dist) > SPLIT_FACTOR

	if should_split:
		var u_mid: float = (u_min + u_max) / 2.0
		var v_mid: float = (v_min + v_max) / 2.0
		var d1: int = depth + 1
		_collect_leaves(fi, u_min, u_mid, v_min, v_mid, d1, cam_pos, leaves)
		_collect_leaves(fi, u_mid, u_max, v_min, v_mid, d1, cam_pos, leaves)
		_collect_leaves(fi, u_min, u_mid, v_mid, v_max, d1, cam_pos, leaves)
		_collect_leaves(fi, u_mid, u_max, v_mid, v_max, d1, cam_pos, leaves)
	else:
		var key: String = "t_%d_%d_%.4f_%.4f" % [fi, depth, u_min, v_min]
		leaves.append({"fi": fi, "u_min": u_min, "u_max": u_max,
			"v_min": v_min, "v_max": v_max, "depth": depth, "key": key})


## Get or build a tile mesh from cache
func _get_or_build_tile(leaf: Dictionary) -> ArrayMesh:
	if _tile_cache.has(leaf.key):
		return _tile_cache[leaf.key]

	var tile_mesh := _build_tile(leaf.fi, leaf.u_min, leaf.u_max,
		leaf.v_min, leaf.v_max, leaf.depth)
	_tile_cache[leaf.key] = tile_mesh
	return tile_mesh


# ── Compute shader helpers ────────────────────────────────────────────────────

## Try to initialise the local RenderingDevice and compile the compute shader.
## Called lazily from generate().  Safe to call multiple times — returns
## immediately if already initialised or if the GPU path is unavailable.
## Returns true on success.
func _cs_init() -> bool:
	if _cs_ready or _cs_shader.is_valid():
		return _cs_pipeline.is_valid()
	# Require Vulkan (Forward+ / Mobile renderer) — not available on Web / Compat.
	if not RenderingServer.get_rendering_device():
		push_warning("GlobeMesh: no RenderingDevice — using CPU tile path")
		return false
	_rd = RenderingServer.create_local_rendering_device()
	if not _rd:
		push_warning("GlobeMesh: create_local_rendering_device failed — using CPU tile path")
		return false

	var shader_file: RDShaderFile = load("res://src/rendering/globe/terrain_tile.glsl")
	if not shader_file:
		push_warning("GlobeMesh: terrain_tile.glsl not found — using CPU tile path")
		_rd = null
		return false

	var spirv: RDShaderSPIRV = shader_file.get_spirv()
	if spirv.compile_error_compute != "":
		push_warning("GlobeMesh: compute shader error: " + spirv.compile_error_compute)
		_rd = null
		return false

	_cs_shader = _rd.shader_create_from_spirv(spirv)
	if not _cs_shader.is_valid():
		push_warning("GlobeMesh: shader_create_from_spirv failed — using CPU tile path")
		_rd = null
		return false

	_cs_pipeline = _rd.compute_pipeline_create(_cs_shader)
	if not _cs_pipeline.is_valid():
		push_warning("GlobeMesh: compute_pipeline_create failed — using CPU tile path")
		_rd.free_rid(_cs_shader)
		_cs_shader = RID()
		_rd = null
		return false

	# Pre-allocate output buffer: 81 verts × 12 floats × 4 bytes = 3888 bytes.
	var out_bytes := TILE_RES * TILE_RES * 12 * 4
	_cs_out_buf = _rd.storage_buffer_create(out_bytes)
	if not _cs_out_buf.is_valid():
		push_warning("GlobeMesh: output buffer allocation failed — using CPU tile path")
		_rd.free_rid(_cs_pipeline)
		_rd.free_rid(_cs_shader)
		_cs_pipeline = RID()
		_cs_shader = RID()
		_rd = null
		return false

	print("GlobeMesh: compute shader compiled OK — waiting for world data upload")
	return true  # World uniform set created later in _cs_upload_world_data()


## Pack arch + flattened peak data into byte arrays.
## Returns [arch_bytes: PackedByteArray, peak_bytes: PackedByteArray].
## Arch layout (32 bytes): cx cy cz shelf_r | peak_start(u32) peak_count(u32) pad pad
## Peak layout (32 bytes): px py pz w | h w2inv pad pad
func _cs_pack_arch_peak(archs: Array) -> Array:
	var arch_bytes := PackedByteArray()
	arch_bytes.resize(maxi(archs.size(), 1) * 32)
	var peak_total := 0
	for ar in archs:
		peak_total += ar.peaks.size()
	var peak_bytes := PackedByteArray()
	peak_bytes.resize(maxi(peak_total, 1) * 32)

	var pk_cursor := 0
	for a in archs.size():
		var ar: Dictionary = archs[a]
		var ab := a * 32
		arch_bytes.encode_float(ab +  0, ar.cx)
		arch_bytes.encode_float(ab +  4, ar.cy)
		arch_bytes.encode_float(ab +  8, ar.cz)
		arch_bytes.encode_float(ab + 12, ar.shelf_r)
		arch_bytes.encode_u32  (ab + 16, pk_cursor)
		arch_bytes.encode_u32  (ab + 20, ar.peaks.size())
		arch_bytes.encode_float(ab + 24, 0.0)
		arch_bytes.encode_float(ab + 28, 0.0)
		for pk in ar.peaks:
			var pb := pk_cursor * 32
			peak_bytes.encode_float(pb +  0, pk.px)
			peak_bytes.encode_float(pb +  4, pk.py)
			peak_bytes.encode_float(pb +  8, pk.pz)
			peak_bytes.encode_float(pb + 12, pk.w)
			peak_bytes.encode_float(pb + 16, pk.h)
			peak_bytes.encode_float(pb + 20, pk.w2inv)
			peak_bytes.encode_float(pb + 24, 0.0)
			peak_bytes.encode_float(pb + 28, 0.0)
			pk_cursor += 1
	return [arch_bytes, peak_bytes]


## Pack edge data into a byte array.
## Edge layout (48 bytes): ax ay az w | bx by bz dot_ab | nx ny nz pad
func _cs_pack_edges(edges: Array) -> PackedByteArray:
	var edge_bytes := PackedByteArray()
	edge_bytes.resize(maxi(edges.size(), 1) * 48)
	for e in edges.size():
		var ed: Dictionary = edges[e]
		var eb := e * 48
		edge_bytes.encode_float(eb +  0, ed.ax)
		edge_bytes.encode_float(eb +  4, ed.ay)
		edge_bytes.encode_float(eb +  8, ed.az)
		edge_bytes.encode_float(eb + 12, ed.w)
		edge_bytes.encode_float(eb + 16, ed.bx)
		edge_bytes.encode_float(eb + 20, ed.by)
		edge_bytes.encode_float(eb + 24, ed.bz)
		edge_bytes.encode_float(eb + 28, ed.dot_ab)
		edge_bytes.encode_float(eb + 32, ed.nx)
		edge_bytes.encode_float(eb + 36, ed.ny)
		edge_bytes.encode_float(eb + 40, ed.nz)
		edge_bytes.encode_float(eb + 44, 0.0)
	return edge_bytes


## Upload world geometry to GPU SSBOs and (re)build the uniform set.
## Called from generate() after _cs_init() succeeds.
func _cs_upload_world_data(archs: Array, edges: Array) -> void:
	if not _rd:
		return
	_cs_free_world_bufs()

	var ap    := _cs_pack_arch_peak(archs)
	var a_buf: PackedByteArray = ap[0]
	var p_buf: PackedByteArray = ap[1]
	var e_buf := _cs_pack_edges(edges)

	_cs_arch_buf = _rd.storage_buffer_create(a_buf.size(), a_buf)
	_cs_peak_buf = _rd.storage_buffer_create(p_buf.size(), p_buf)
	_cs_edge_buf = _rd.storage_buffer_create(e_buf.size(), e_buf)

	if not (_cs_arch_buf.is_valid() and _cs_peak_buf.is_valid() and _cs_edge_buf.is_valid()):
		push_warning("GlobeMesh: SSBO creation failed — disabling GPU tile path")
		_cs_free_world_bufs()
		return

	# Build the single uniform set (set 0): arch=0, peak=1, edge=2, output=3
	var u_arch := RDUniform.new()
	u_arch.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
	u_arch.binding = 0
	u_arch.add_id(_cs_arch_buf)

	var u_peak := RDUniform.new()
	u_peak.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
	u_peak.binding = 1
	u_peak.add_id(_cs_peak_buf)

	var u_edge := RDUniform.new()
	u_edge.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
	u_edge.binding = 2
	u_edge.add_id(_cs_edge_buf)

	var u_out := RDUniform.new()
	u_out.uniform_type = RenderingDevice.UNIFORM_TYPE_STORAGE_BUFFER
	u_out.binding = 3
	u_out.add_id(_cs_out_buf)

	_cs_set = _rd.uniform_set_create([u_arch, u_peak, u_edge, u_out], _cs_shader, 0)
	if not _cs_set.is_valid():
		push_warning("GlobeMesh: uniform_set_create failed — disabling GPU tile path")
		_cs_free_world_bufs()
		return

	_cs_ready = true
	print("GlobeMesh: GPU tile path ready (archs=%d, edges=%d)" % [archs.size(), edges.size()])


## Free world-data SSBOs and the uniform set, but keep shader/pipeline alive.
func _cs_free_world_bufs() -> void:
	_cs_ready = false
	if not _rd:
		return
	if _cs_set.is_valid():
		_rd.free_rid(_cs_set)
		_cs_set = RID()
	for rid in [_cs_arch_buf, _cs_peak_buf, _cs_edge_buf]:
		if rid.is_valid():
			_rd.free_rid(rid)
	_cs_arch_buf = RID()
	_cs_peak_buf = RID()
	_cs_edge_buf = RID()


## Free all GPU resources (called from clear_cache and _exit_tree).
func _cs_free_all() -> void:
	_cs_free_world_bufs()
	if not _rd:
		return
	if _cs_out_buf.is_valid():
		_rd.free_rid(_cs_out_buf)
		_cs_out_buf = RID()
	if _cs_pipeline.is_valid():
		_rd.free_rid(_cs_pipeline)
		_cs_pipeline = RID()
	if _cs_shader.is_valid():
		_rd.free_rid(_cs_shader)
		_cs_shader = RID()
	_rd = null


func _exit_tree() -> void:
	_cs_free_all()


## GPU tile builder — dispatches the compute shader and reads back the result.
## Returns null on any error (caller falls back to CPU path).
func _build_tile_gpu(fi: int, u_min: float, u_max: float,
		v_min: float, v_max: float, depth: int) -> ArrayMesh:
	var archs: Array = _world_data.get("archs", [])
	var edges: Array = _world_data.get("edges", [])

	# Push constant: 10 × int/float = 40 bytes
	var pc := PackedByteArray()
	pc.resize(40)
	pc.encode_s32  ( 0, fi)
	pc.encode_s32  ( 4, depth)
	pc.encode_float( 8, u_min)
	pc.encode_float(12, u_max)
	pc.encode_float(16, v_min)
	pc.encode_float(20, v_max)
	pc.encode_float(24, sea_level)
	pc.encode_float(28, bw_scale)
	pc.encode_s32  (32, archs.size())
	pc.encode_s32  (36, edges.size())

	var cl := _rd.compute_list_begin()
	_rd.compute_list_bind_compute_pipeline(cl, _cs_pipeline)
	_rd.compute_list_bind_uniform_set(cl, _cs_set, 0)
	_rd.compute_list_set_push_constant(cl, pc, pc.size())
	_rd.compute_list_dispatch(cl, 1, 1, 1)  # one work group of 9×9 invocations
	_rd.compute_list_end()
	_rd.submit()
	_rd.sync()

	var out := _rd.buffer_get_data(_cs_out_buf)
	if out.size() < TILE_RES * TILE_RES * 48:
		push_warning("GlobeMesh: GPU tile readback too small (%d bytes) — falling back to CPU" % out.size())
		return null

	# Sanity-check first vertex position: if all zeros the shader ran but wrote nothing
	# (silent compile failure, wrong binding, barrier issue). Return null → CPU fallback.
	var p0x := out.decode_float(0)
	var p0y := out.decode_float(4)
	var p0z := out.decode_float(8)
	if p0x == 0.0 and p0y == 0.0 and p0z == 0.0:
		push_warning("GlobeMesh: GPU tile first vertex is (0,0,0) — shader output looks degenerate, falling back to CPU")
		return null

	# Parse output: 12 floats (48 bytes) per vertex
	var N    := TILE_RES
	var vpos := PackedVector3Array(); vpos.resize(N * N)
	var vnrm := PackedVector3Array(); vnrm.resize(N * N)
	var vcol := PackedColorArray();   vcol.resize(N * N)
	for idx in N * N:
		var b := idx * 48
		vpos[idx] = Vector3(out.decode_float(b     ), out.decode_float(b +  4), out.decode_float(b +  8))
		vnrm[idx] = Vector3(out.decode_float(b + 16), out.decode_float(b + 20), out.decode_float(b + 24))
		vcol[idx] = Color  (out.decode_float(b + 32), out.decode_float(b + 36), out.decode_float(b + 40))

	# Index buffer — same winding as CPU path (a,c,b then b,c,d)
	var indices := PackedInt32Array(); indices.resize((N - 1) * (N - 1) * 6)
	var ii := 0
	for j in range(N - 1):
		for i in range(N - 1):
			var a := j * N + i
			var b := a + 1
			var c := a + N
			var d := c + 1
			indices[ii    ] = a; indices[ii + 1] = c; indices[ii + 2] = b
			indices[ii + 3] = b; indices[ii + 4] = c; indices[ii + 5] = d
			ii += 6

	var arrays: Array = []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vpos
	arrays[Mesh.ARRAY_NORMAL] = vnrm
	arrays[Mesh.ARRAY_COLOR]  = vcol
	arrays[Mesh.ARRAY_INDEX]  = indices

	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return mesh


# ── Tile builders ─────────────────────────────────────────────────────────────

## Route tile building: GPU path for depth ≤ 7 when use_gpu_tiles is true, CPU otherwise.
## Bypasses GPU when urban_mode > 0 — the settlement overlay runs CPU-only.
## Falls back to CPU on any GPU error or degenerate output.
func _build_tile(fi: int, u_min: float, u_max: float, v_min: float, v_max: float, depth: int) -> ArrayMesh:
	if use_gpu_tiles and _cs_ready and depth <= 7 and urban_mode == 0:
		var gpu_mesh := _build_tile_gpu(fi, u_min, u_max, v_min, v_max, depth)
		if gpu_mesh != null:
			return gpu_mesh
	return _build_tile_cpu(fi, u_min, u_max, v_min, v_max, depth)


## CPU tile builder — original SurfaceTool path, unchanged.
func _build_tile_cpu(fi: int, u_min: float, u_max: float, v_min: float, v_max: float, depth: int) -> ArrayMesh:
	var archs: Array = _world_data.get("archs", [])
	var edges: Array = _world_data.get("edges", [])
	var settlements: Array = _world_data.get("settlements", [])

	var N: int = TILE_RES
	var du: float = (u_max - u_min) / float(N - 1)
	var dv: float = (v_max - v_min) / float(N - 1)

	# Detail level scales with quadtree depth — matches JSX: min(4 + depth, 8)
	var detail_level: int = mini(4 + depth, 8)

	# Generate vertex data
	var positions: Array[Vector3] = []
	var colors: Array[Color] = []
	var heights_arr: PackedFloat32Array = PackedFloat32Array()
	var sphere_pts: Array[Vector3] = []  # unit sphere points for urban overlay
	positions.resize(N * N)
	colors.resize(N * N)
	heights_arr.resize(N * N)
	sphere_pts.resize(N * N)

	for j in N:
		for i in N:
			var u: float = u_min + float(i) * du
			var v: float = v_min + float(j) * dv
			var sp: Vector3 = _cube_to_sphere(fi, u, v)
			var idx: int = j * N + i

			var h: float = TerrainMath.compute_height(
				sp.x, sp.y, sp.z, archs, edges, detail_level, bw_scale
			)
			heights_arr[idx] = h
			sphere_pts[idx] = sp

			# Displacement: only above sea level (matches JSX)
			if h > sea_level:
				positions[idx] = sp * (1.0 + (h - sea_level) * DISP_SCALE)
			else:
				positions[idx] = sp

			# Color with noise perturbation
			var effective_h: float = h - sea_level
			var noise_val: float = TerrainMath.smooth_noise(sp.x * 10.0, sp.y * 10.0, sp.z * 10.0)
			colors[idx] = _get_altitude_color(effective_h, noise_val)

	# Apply urbanization overlay if enabled
	if urban_mode > 0:
		_apply_urban_overlay(sphere_pts, heights_arr, colors, settlements, depth)

	# Build indexed mesh with correct winding
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	for j in range(N - 1):
		for i in range(N - 1):
			var a: int = j * N + i
			var b: int = a + 1
			var c: int = a + N
			var d: int = c + 1

			# Triangle 1: a, c, b (CCW from outside)
			# Use sphere-point normals (unit sphere direction at each vertex) rather than
			# a per-face centroid normal. This matches the JSX reference which sets
			# normals[idx] = [sx, sy, sz] — the sphere surface direction — giving smooth
			# Phong shading that is continuous across tile boundaries and across the
			# diagonal quad split, eliminating seam lines and intra-tile crease artifacts.
			st.set_normal(sphere_pts[a])
			st.set_color(colors[a])
			st.add_vertex(positions[a])
			st.set_normal(sphere_pts[c])
			st.set_color(colors[c])
			st.add_vertex(positions[c])
			st.set_normal(sphere_pts[b])
			st.set_color(colors[b])
			st.add_vertex(positions[b])

			# Triangle 2: b, c, d
			st.set_normal(sphere_pts[b])
			st.set_color(colors[b])
			st.add_vertex(positions[b])
			st.set_normal(sphere_pts[c])
			st.set_color(colors[c])
			st.add_vertex(positions[c])
			st.set_normal(sphere_pts[d])
			st.set_color(colors[d])
			st.add_vertex(positions[d])

	return st.commit()


## Altitude color LUT — identical to the React/Three.js version.
## 26 control points from -5000m to +3500m, smoothstep interpolated.
const _COLOR_STOPS: Array = [
	[-5000.0, 0.012, 0.025, 0.08],
	[-4000.0, 0.018, 0.035, 0.10],
	[-3000.0, 0.025, 0.050, 0.14],
	[-2200.0, 0.035, 0.070, 0.18],
	[-1500.0, 0.045, 0.100, 0.24],
	[ -800.0, 0.060, 0.140, 0.32],
	[ -500.0, 0.080, 0.185, 0.38],
	[ -300.0, 0.100, 0.220, 0.42],
	[ -150.0, 0.130, 0.270, 0.48],
	[  -80.0, 0.155, 0.310, 0.52],
	[  -40.0, 0.175, 0.340, 0.54],
	[  -15.0, 0.195, 0.360, 0.55],
	[   -5.0, 0.210, 0.375, 0.54],
	[    0.0, 0.220, 0.380, 0.50],
	[    5.0, 0.240, 0.360, 0.42],
	[   15.0, 0.265, 0.350, 0.36],
	[   35.0, 0.280, 0.340, 0.30],
	[   80.0, 0.260, 0.330, 0.24],
	[  150.0, 0.240, 0.310, 0.20],
	[  300.0, 0.225, 0.290, 0.18],
	[  500.0, 0.240, 0.270, 0.17],
	[  800.0, 0.270, 0.260, 0.18],
	[ 1200.0, 0.320, 0.280, 0.20],
	[ 1800.0, 0.380, 0.330, 0.25],
	[ 2500.0, 0.460, 0.420, 0.36],
	[ 3500.0, 0.550, 0.510, 0.44],
]

func _get_altitude_color(height: float, noise_val: float = 0.0) -> Color:
	# Noise perturbation — matches JSX: depth + noiseVal * 25
	var h := clampf(height + noise_val * 25.0, -5000.0, 3500.0)

	# Find the surrounding control point pair
	var si := 0
	while si < _COLOR_STOPS.size() - 2 and _COLOR_STOPS[si + 1][0] < h:
		si += 1

	var s0: Array = _COLOR_STOPS[si]
	var s1: Array = _COLOR_STOPS[si + 1]
	var h0: float = s0[0]
	var h1: float = s1[0]

	# Linear parameter then smoothstep (cubic Hermite) — matches JSX exactly
	var t: float = clampf((h - h0) / (h1 - h0), 0.0, 1.0)
	var s: float = t * t * (3.0 - 2.0 * t)

	return Color(
		s0[1] + s * (s1[1] - s0[1]),
		s0[2] + s * (s1[2] - s0[2]),
		s0[3] + s * (s1[3] - s0[3]),
	)


# ── Urbanization overlay — matches JSX applyUrbanOverlay exactly ──
const URBAN_GREY   := Color(0.30, 0.28, 0.26)
const HARBOR_WATER := Color(0.04, 0.06, 0.10)
const INCLINE_CLR  := Color(0.36, 0.33, 0.30)

func _apply_urban_overlay(sphere_pts: Array[Vector3], heights: PackedFloat32Array,
		colors: Array[Color], settlements: Array, depth: int) -> void:
	for i in sphere_pts.size():
		var vn: Vector3 = sphere_pts[i]
		var h: float = heights[i]
		var alt_above_sea: float = h - sea_level

		for si in settlements.size():
			var s: Dictionary = settlements[si]
			var dot: float = vn.x * s.cx + vn.y * s.cy + vn.z * s.cz
			# Quick reject
			if dot < 1.0 - s.radius * s.radius * 2.0:
				continue
			var ang_dist: float = sqrt(maxf(0.0, 2.0 * (1.0 - dot)))
			if ang_dist > s.radius:
				continue

			var proximity: float = 1.0 - ang_dist / s.radius

			# Altitude-dependent density gradient
			var alt_factor: float
			if alt_above_sea < -30.0:
				alt_factor = maxf(0.0, 1.0 + alt_above_sea / 300.0) * 0.4
			elif alt_above_sea < 0.0:
				alt_factor = 0.6 + 0.4 * (1.0 + alt_above_sea / 30.0)
			elif alt_above_sea < 60.0:
				alt_factor = 1.0
			elif alt_above_sea < 600.0:
				alt_factor = 1.0 - (alt_above_sea - 60.0) / 540.0 * 0.7
			elif alt_above_sea < 1200.0:
				alt_factor = 0.3 * (1.0 - (alt_above_sea - 600.0) / 600.0)
			else:
				alt_factor = 0.0
			if alt_factor <= 0.0:
				continue

			var blend: float = proximity * alt_factor * s.importance

			# Harbor water darkening
			if alt_above_sea < -5.0 and proximity > 0.2:
				var h_blend: float = blend * 0.6
				colors[i] = Color(
					colors[i].r + (HARBOR_WATER.r - colors[i].r) * h_blend,
					colors[i].g + (HARBOR_WATER.g - colors[i].g) * h_blend,
					colors[i].b + (HARBOR_WATER.b - colors[i].b) * h_blend,
				)
				continue

			# Incline railway cuts (high zoom only — depth ≥ 6 matches JSX)
			if depth >= 6 and alt_above_sea > 20.0 and alt_above_sea < 900.0:
				var ox: float = vn.x - s.cx
				var oy: float = vn.y - s.cy
				var oz: float = vn.z - s.cz
				for inc in s.inclines:
					var cross_x: float = oy * inc.dz - oz * inc.dy
					var cross_y: float = oz * inc.dx - ox * inc.dz
					var cross_z: float = ox * inc.dy - oy * inc.dx
					var perp_dist: float = sqrt(cross_x * cross_x + cross_y * cross_y + cross_z * cross_z)
					var line_width: float = s.radius * 0.03
					if perp_dist < line_width:
						var along: float = ox * inc.dx + oy * inc.dy + oz * inc.dz
						if along > 0.0:
							var inc_blend: float = (1.0 - perp_dist / line_width) * 0.4 * alt_factor
							colors[i] = Color(
								colors[i].r + (INCLINE_CLR.r - colors[i].r) * inc_blend,
								colors[i].g + (INCLINE_CLR.g - colors[i].g) * inc_blend,
								colors[i].b + (INCLINE_CLR.b - colors[i].b) * inc_blend,
							)

			# Core urban density gradient
			var warmth: float = 1.0 - proximity * 0.15
			var u_r: float = URBAN_GREY.r * warmth
			var u_g: float = URBAN_GREY.g * warmth
			var u_b: float = URBAN_GREY.b * warmth
			var b_clamped: float = minf(blend, 0.88)
			colors[i] = Color(
				colors[i].r + (u_r - colors[i].r) * b_clamped,
				colors[i].g + (u_g - colors[i].g) * b_clamped,
				colors[i].b + (u_b - colors[i].b) * b_clamped,
			)
