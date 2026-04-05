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
## Maximum number of new tile meshes built per frame.
const TILES_PER_FRAME: int = 4

func _init() -> void:
	_material = StandardMaterial3D.new()
	_material.vertex_color_use_as_albedo = true
	_material.roughness = 0.85
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
	ocean_mat.albedo_color = Color(0.02, 0.05, 0.12)
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
	_tile_cache.clear()
	_build_queue.clear()
	_queued_keys.clear()
	_desired_keys.clear()
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

	# Remove tiles that are no longer needed
	var i := 0
	while i < _active_tiles.size():
		var tile: MeshInstance3D = _active_tiles[i]
		if not needed_keys.has(tile.name):
			remove_child(tile)
			tile.queue_free()
			_active_tiles.remove_at(i)
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


## Build a single tile mesh (TILE_RES × TILE_RES grid on one cube face)
func _build_tile(fi: int, u_min: float, u_max: float, v_min: float, v_max: float, depth: int) -> ArrayMesh:
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
