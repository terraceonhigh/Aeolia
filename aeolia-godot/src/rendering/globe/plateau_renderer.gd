## Plateau edge network renderer — great-circle arcs between archipelagos
## plus marker dots at each archipelago center.
## Per-frame horizon culling hides arcs and markers on the far side of the globe.
## Uses geometric horizon threshold derived from camera distance.
class_name PlateauRenderer
extends Node3D

## Radius offset for drawing arcs and markers above the globe surface
var surface_offset: float = 1.002

## Number of samples along each great-circle arc
var arc_samples: int = 20

## Radius of archipelago center marker spheres
var marker_radius: float = 0.008

## Material for the great-circle arcs
var arc_material: StandardMaterial3D

## Cached world data for per-frame rebuild of visible arcs
var _archs: Array = []
var _edges: Array = []
var _states: Array = []

## MeshInstance3D for arcs (rebuilt each frame for horizon culling)
var arc_mesh_instance: MeshInstance3D

## Dictionary of arch_idx → MeshInstance3D for markers
var marker_instances: Dictionary = {}

## Pre-computed arch center directions (normalized)
var _arch_dirs: Array[Vector3] = []

## Cached camera direction for throttling arc rebuilds
var _last_cam_dir := Vector3.ZERO
const _CAM_DIR_THRESHOLD := 0.002  # rebuild arcs only when camera moves noticeably


func _ready() -> void:
	_setup_arc_material()
	set_process(true)


## Render the plateau edge network from world data.
func setup(world_data: Dictionary) -> void:
	for child in get_children():
		child.queue_free()
	marker_instances.clear()
	_arch_dirs.clear()

	_archs = world_data.get("archs", [])
	_edges = world_data.get("plateau_edges", [])
	var history: Dictionary = world_data.get("history", {})
	_states = history.get("states", [])

	# Pre-compute normalized directions
	_arch_dirs.resize(_archs.size())
	for i in _archs.size():
		var a: Dictionary = _archs[i]
		_arch_dirs[i] = Vector3(a.cx, a.cy, a.cz).normalized()

	_build_arch_markers()

	arc_mesh_instance = MeshInstance3D.new()
	arc_mesh_instance.name = "Arcs"
	add_child(arc_mesh_instance)
	_rebuild_arcs(Vector3.FORWARD, 0.0)


func _setup_arc_material() -> void:
	arc_material = StandardMaterial3D.new()
	arc_material.vertex_color_use_as_albedo = true
	arc_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	arc_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	arc_material.no_depth_test = true


## Geometric horizon threshold.
## For a camera at distance D from the center of a unit sphere,
## a surface point is visible iff  point_dir · cam_dir > cos(acos(1/D) + margin).
## Returns the dot-product cutoff below which a point is hidden.
static func _horizon_cutoff(cam_dist: float, margin_deg: float = 3.0) -> float:
	if cam_dist <= 1.0:
		return -1.0  # inside the sphere — everything visible
	var horizon_angle: float = acos(1.0 / cam_dist)
	return cos(horizon_angle + deg_to_rad(margin_deg))


## Per-frame: cull markers and rebuild arcs for visible edges only.
func _process(_delta: float) -> void:
	var cam := get_viewport().get_camera_3d()
	if cam == null:
		return

	var cam_pos := cam.global_position
	var cam_dist := cam_pos.length()
	var cam_dir := cam_pos.normalized()  # direction from origin to camera
	var cutoff := _horizon_cutoff(cam_dist)

	# Cull markers
	for idx in marker_instances:
		var inst: MeshInstance3D = marker_instances[idx]
		inst.visible = _arch_dirs[idx].dot(cam_dir) > cutoff

	# Rebuild arc mesh only when camera moves meaningfully
	if _last_cam_dir.distance_squared_to(cam_dir) > _CAM_DIR_THRESHOLD:
		_last_cam_dir = cam_dir
		_rebuild_arcs(cam_dir, cutoff)


## Rebuild the arc ImmediateMesh, skipping edges fully beyond the horizon.
func _rebuild_arcs(cam_dir: Vector3, cutoff: float) -> void:
	if _edges.is_empty() or arc_mesh_instance == null:
		return

	var im := ImmediateMesh.new()
	im.surface_begin(Mesh.PRIMITIVE_LINES)

	var any_verts := false

	for edge in _edges:
		var i: int = edge[0]
		var j: int = edge[1]

		# Skip if BOTH endpoints are beyond the horizon
		var d1 := _arch_dirs[i].dot(cam_dir)
		var d2 := _arch_dirs[j].dot(cam_dir)
		if d1 < cutoff and d2 < cutoff:
			continue

		var v1 := Vector3(_archs[i].cx, _archs[i].cy, _archs[i].cz)
		var v2 := Vector3(_archs[j].cx, _archs[j].cy, _archs[j].cz)
		var color: Color = _get_edge_color(i, j)

		# Sample great-circle arc using slerp with per-segment culling
		var prev := v1.slerp(v2, 0.0).normalized() * surface_offset
		for s in range(1, arc_samples):
			var t: float = float(s) / float(arc_samples - 1)
			var cur := v1.slerp(v2, t).normalized() * surface_offset

			# Per-segment horizon test
			if prev.normalized().dot(cam_dir) > cutoff or \
			   cur.normalized().dot(cam_dir) > cutoff:
				im.surface_set_color(color)
				im.surface_add_vertex(prev)
				im.surface_set_color(color)
				im.surface_add_vertex(cur)
				any_verts = true

			prev = cur

	if not any_verts:
		# ImmediateMesh needs at least one degenerate segment
		im.surface_set_color(Color(0, 0, 0, 0))
		im.surface_add_vertex(Vector3.ZERO)
		im.surface_set_color(Color(0, 0, 0, 0))
		im.surface_add_vertex(Vector3.ZERO)

	im.surface_end()

	arc_mesh_instance.mesh = im
	if arc_mesh_instance.get_surface_override_material_count() == 0 or \
	   arc_mesh_instance.get_surface_override_material(0) != arc_material:
		arc_mesh_instance.set_surface_override_material(0, arc_material)


## Edge color based on faction pair.
func _get_edge_color(i: int, j: int) -> Color:
	var fi := "unknown"
	var fj := "unknown"
	if i < _states.size():
		fi = _states[i].get("faction", "unknown")
	if j < _states.size():
		fj = _states[j].get("faction", "unknown")

	if fi == "reach" and fj == "reach":
		return Color(0.7, 0.3, 0.2, 0.5)
	elif fi == "lattice" and fj == "lattice":
		return Color(0.2, 0.4, 0.7, 0.5)
	else:
		return Color(0.4, 0.4, 0.4, 0.3)


## Create small sphere markers at each archipelago center.
func _build_arch_markers() -> void:
	for arch_idx in _archs.size():
		var arch: Dictionary = _archs[arch_idx]

		var faction := "unknown"
		if arch_idx < _states.size():
			faction = _states[arch_idx].get("faction", "unknown")

		var color: Color = _get_faction_color(faction)

		var sphere_mesh := SphereMesh.new()
		sphere_mesh.radius = marker_radius
		sphere_mesh.height = marker_radius * 2.0
		sphere_mesh.radial_segments = 8
		sphere_mesh.rings = 4

		var mat := StandardMaterial3D.new()
		mat.albedo_color = color
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.no_depth_test = true

		var inst := MeshInstance3D.new()
		inst.mesh = sphere_mesh
		inst.set_surface_override_material(0, mat)
		inst.position = Vector3(arch.cx, arch.cy, arch.cz) * surface_offset
		add_child(inst)
		marker_instances[arch_idx] = inst


## Marker color by faction.
func _get_faction_color(faction: String) -> Color:
	match faction:
		"reach":
			return Color(0.7, 0.3, 0.2, 1.0)
		"lattice":
			return Color(0.2, 0.4, 0.7, 1.0)
		_:
			return Color(0.4, 0.4, 0.4, 0.8)
