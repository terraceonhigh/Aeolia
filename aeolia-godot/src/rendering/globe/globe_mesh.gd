## Procedural globe mesh — subdivided icosphere with terrain displacement.
## Samples TerrainMath.compute_height() at each vertex and colors by altitude.
class_name GlobeMesh
extends MeshInstance3D

## Subdivision level for the icosphere (5 gives ~10k triangles)
@export var subdivisions: int = 5

## Displacement scale for terrain height (heights in meters, scale to mesh units)
## Tuned so max mountain (~3200m) displaces ~0.032 and ocean (-4500m) clamps to ~-0.025
@export var displacement_scale: float = 0.00001

## Detail level for height sampling (LOD level)
var detail_level: int = 4

## Bridge width scale for TerrainMath
var bw_scale: float = 0.13


## Generate the globe mesh from world data.
## world_data: Dictionary returned by WorldGenerator.build_world()
func generate(world_data: Dictionary) -> void:
	var archs: Array = world_data.get("archs", [])
	var edges: Array = world_data.get("edges", [])

	# Build the icosphere geometry
	var ico: Array = _build_icosphere(subdivisions)
	var vertices: Array = ico[0]
	var indices: Array = ico[1]

	# Create a surface tool to build the mesh
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)

	# Pre-compute displaced positions and colors for all vertices
	var displaced_verts: Array[Vector3] = []
	var vert_colors: Array[Color] = []
	displaced_verts.resize(vertices.size())
	vert_colors.resize(vertices.size())

	var land_count := 0
	for i in vertices.size():
		var v: Vector3 = vertices[i]
		var height: float = TerrainMath.compute_height(
			v.x, v.y, v.z, archs, edges, detail_level, bw_scale
		)
		if height > 0.0:
			land_count += 1
		var disp_h: float = maxf(height, -2500.0)
		displaced_verts[i] = v.normalized() * (1.0 + disp_h * displacement_scale)
		vert_colors[i] = _get_altitude_color(height)

	var ocean_pct: float = 100.0 * (1.0 - float(land_count) / float(vertices.size()))
	print("Ocean coverage: %.1f%% (%d land / %d total vertices)" % [ocean_pct, land_count, vertices.size()])

	# Build non-indexed mesh with REVERSED winding (CCW from outside)
	# so Godot treats the outward-facing side as the front face.
	# Normals always point outward (toward face_center direction).
	for i in range(0, indices.size(), 3):
		var i0: int = indices[i]
		var i1: int = indices[i + 1]
		var i2: int = indices[i + 2]

		var p0: Vector3 = displaced_verts[i0]
		var p1: Vector3 = displaced_verts[i1]
		var p2: Vector3 = displaced_verts[i2]

		# Face center points outward on a unit sphere — use as normal
		var face_center: Vector3 = (p0 + p1 + p2) / 3.0
		var face_normal: Vector3 = face_center.normalized()

		# Emit vertices in REVERSED order (0, 2, 1) to flip CW → CCW
		st.set_normal(face_normal)
		st.set_color(vert_colors[i0])
		st.add_vertex(p0)

		st.set_normal(face_normal)
		st.set_color(vert_colors[i2])
		st.add_vertex(p2)

		st.set_normal(face_normal)
		st.set_color(vert_colors[i1])
		st.add_vertex(p1)

	# Opaque material with vertex colors, backface culling (winding is now correct)
	var mat := StandardMaterial3D.new()
	mat.vertex_color_use_as_albedo = true
	mat.roughness = 0.85
	mat.cull_mode = BaseMaterial3D.CULL_BACK

	self.mesh = st.commit()
	self.material_override = mat


## Build a subdivided icosphere.
## Returns [PackedVector3Array of vertices, PackedInt32Array of indices].
func _build_icosphere(subdiv: int) -> Array:
	# Golden ratio
	var phi: float = (1.0 + sqrt(5.0)) / 2.0

	# 12 vertices of a regular icosahedron (permutations of (0, ±1, ±phi))
	var verts: Array[Vector3] = [
		Vector3(-1.0,  phi, 0.0).normalized(),
		Vector3( 1.0,  phi, 0.0).normalized(),
		Vector3(-1.0, -phi, 0.0).normalized(),
		Vector3( 1.0, -phi, 0.0).normalized(),
		Vector3(0.0, -1.0,  phi).normalized(),
		Vector3(0.0,  1.0,  phi).normalized(),
		Vector3(0.0, -1.0, -phi).normalized(),
		Vector3(0.0,  1.0, -phi).normalized(),
		Vector3( phi, 0.0, -1.0).normalized(),
		Vector3( phi, 0.0,  1.0).normalized(),
		Vector3(-phi, 0.0, -1.0).normalized(),
		Vector3(-phi, 0.0,  1.0).normalized(),
	]

	# 20 triangular faces of the icosahedron
	var tris: Array[int] = [
		0, 11, 5,   0, 5, 1,    0, 1, 7,    0, 7, 10,   0, 10, 11,
		1, 5, 9,    5, 11, 4,   11, 10, 2,  10, 7, 6,   7, 1, 8,
		3, 9, 4,    3, 4, 2,    3, 2, 6,    3, 6, 8,    3, 8, 9,
		4, 9, 5,    2, 4, 11,   6, 2, 10,   8, 6, 7,    9, 8, 1,
	]

	# Subdivide N times
	for _s in subdiv:
		var new_tris: Array[int] = []
		var midpoint_cache: Dictionary = {}  # "min_max" -> vertex index

		for i in range(0, tris.size(), 3):
			var i0: int = tris[i]
			var i1: int = tris[i + 1]
			var i2: int = tris[i + 2]

			# Get or create midpoint vertices
			var m01: int = _get_midpoint(i0, i1, verts, midpoint_cache)
			var m12: int = _get_midpoint(i1, i2, verts, midpoint_cache)
			var m20: int = _get_midpoint(i2, i0, verts, midpoint_cache)

			# 4 sub-triangles
			new_tris.append_array([i0, m01, m20])
			new_tris.append_array([i1, m12, m01])
			new_tris.append_array([i2, m20, m12])
			new_tris.append_array([m01, m12, m20])

		tris = new_tris

	return [verts, tris]


## Get or create a vertex at the midpoint of edge (i0, i1),
## projected onto the unit sphere. Uses cache to avoid duplicates.
func _get_midpoint(i0: int, i1: int, verts: Array, cache: Dictionary) -> int:
	var a: int = mini(i0, i1)
	var b: int = maxi(i0, i1)
	var key: String = "%d_%d" % [a, b]

	if cache.has(key):
		return cache[key]

	var mid: Vector3 = ((verts[i0] as Vector3) + (verts[i1] as Vector3)).normalized()
	var idx: int = verts.size()
	verts.append(mid)
	cache[key] = idx
	return idx


## Altitude-based color — natural oceanic world with volcanic islands.
## Deep indigo abyss → navy mid-ocean → teal shallows → warm sand shore →
## tropical green lowland → dense forest midland → volcanic rock highland →
## snow/ash peak.
func _get_altitude_color(height: float) -> Color:
	var t: float

	# Abyss: deep indigo-black
	if height < -3500.0:
		return Color(0.02, 0.02, 0.08)

	# Deep ocean: indigo → dark navy
	if height < -2000.0:
		t = (height + 3500.0) / 1500.0
		return Color(0.02, 0.02, 0.08).lerp(Color(0.04, 0.06, 0.18), t)

	# Mid ocean: dark navy → muted blue
	if height < -500.0:
		t = (height + 2000.0) / 1500.0
		return Color(0.04, 0.06, 0.18).lerp(Color(0.06, 0.12, 0.28), t)

	# Shallow / plateau shelf: muted blue → teal-green
	if height < -50.0:
		t = (height + 500.0) / 450.0
		return Color(0.06, 0.12, 0.28).lerp(Color(0.10, 0.22, 0.30), t)

	# Shore / tidal zone: teal → warm sand
	if height < 80.0:
		t = (height + 50.0) / 130.0
		return Color(0.10, 0.22, 0.30).lerp(Color(0.52, 0.46, 0.34), t)

	# Coastal lowland: sand → tropical green
	if height < 400.0:
		t = (height - 80.0) / 320.0
		return Color(0.52, 0.46, 0.34).lerp(Color(0.22, 0.40, 0.15), t)

	# Forested midland: tropical → deep forest
	if height < 1200.0:
		t = (height - 400.0) / 800.0
		return Color(0.22, 0.40, 0.15).lerp(Color(0.12, 0.28, 0.08), t)

	# Highland: forest → volcanic brown-grey
	if height < 2200.0:
		t = (height - 1200.0) / 1000.0
		return Color(0.12, 0.28, 0.08).lerp(Color(0.30, 0.24, 0.18), t)

	# Peak: volcanic rock → ash/snow cap
	t = clampf((height - 2200.0) / 1000.0, 0.0, 1.0)
	return Color(0.30, 0.24, 0.18).lerp(Color(0.62, 0.58, 0.54), t)
