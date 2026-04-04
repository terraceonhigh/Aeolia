## Plateau edge network renderer — great-circle arcs between archipelagos
## plus marker dots at each archipelago center.
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

## MeshInstance3D for all arcs
var arc_mesh_instance: MeshInstance3D

## Dictionary storing MeshInstance3D for each archipelago marker
var marker_instances: Dictionary = {}


func _ready() -> void:
	_setup_arc_material()


## Render the plateau edge network from world data.
func setup(world_data: Dictionary) -> void:
	# Clear any existing children
	for child in get_children():
		child.queue_free()
	marker_instances.clear()

	var archs: Array = world_data.get("archs", [])
	var plateau_edges: Array = world_data.get("plateau_edges", [])
	var history: Dictionary = world_data.get("history", {})
	var states: Array = history.get("states", [])

	_build_arc_network(archs, plateau_edges, states)
	_build_arch_markers(archs, states)


func _setup_arc_material() -> void:
	arc_material = StandardMaterial3D.new()
	arc_material.vertex_color_use_as_albedo = true
	arc_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	arc_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	arc_material.no_depth_test = true


## Build great-circle arcs between connected archipelagos.
func _build_arc_network(archs: Array, plateau_edges: Array, states: Array) -> void:
	var immediate_mesh := ImmediateMesh.new()
	immediate_mesh.surface_begin(Mesh.PRIMITIVE_LINES)

	for edge in plateau_edges:
		var i: int = edge[0]
		var j: int = edge[1]

		var arch_i: Dictionary = archs[i]
		var arch_j: Dictionary = archs[j]
		var v1 := Vector3(arch_i.cx, arch_i.cy, arch_i.cz)
		var v2 := Vector3(arch_j.cx, arch_j.cy, arch_j.cz)

		var color: Color = _get_edge_color(i, j, states)

		# Sample great-circle arc using slerp
		var arc_points: Array[Vector3] = []
		for s in arc_samples:
			var t: float = float(s) / float(arc_samples - 1)
			arc_points.append(v1.slerp(v2, t).normalized() * surface_offset)

		# Add line segments
		for s in range(arc_points.size() - 1):
			immediate_mesh.surface_set_color(color)
			immediate_mesh.surface_add_vertex(arc_points[s])
			immediate_mesh.surface_set_color(color)
			immediate_mesh.surface_add_vertex(arc_points[s + 1])

	immediate_mesh.surface_end()

	arc_mesh_instance = MeshInstance3D.new()
	arc_mesh_instance.mesh = immediate_mesh
	arc_mesh_instance.set_surface_override_material(0, arc_material)
	add_child(arc_mesh_instance)


## Create small sphere markers at each archipelago center.
func _build_arch_markers(archs: Array, states: Array) -> void:
	for arch_idx in archs.size():
		var arch: Dictionary = archs[arch_idx]

		var faction := "unknown"
		if arch_idx < states.size():
			faction = states[arch_idx].get("faction", "unknown")

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


## Edge color based on faction pair.
func _get_edge_color(i: int, j: int, states: Array) -> Color:
	var fi := "unknown"
	var fj := "unknown"
	if i < states.size():
		fi = states[i].get("faction", "unknown")
	if j < states.size():
		fj = states[j].get("faction", "unknown")

	if fi == "reach" and fj == "reach":
		return Color(0.7, 0.3, 0.2, 0.5)
	elif fi == "lattice" and fj == "lattice":
		return Color(0.2, 0.4, 0.7, 0.5)
	else:
		return Color(0.4, 0.4, 0.4, 0.3)


## Marker color by faction.
func _get_faction_color(faction: String) -> Color:
	match faction:
		"reach":
			return Color(0.7, 0.3, 0.2, 1.0)
		"lattice":
			return Color(0.2, 0.4, 0.7, 1.0)
		_:
			return Color(0.4, 0.4, 0.4, 0.8)
