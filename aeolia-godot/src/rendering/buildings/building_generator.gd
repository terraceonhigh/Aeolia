## Settlement building generator — MultiMeshInstance3D per faction.
## Places small box buildings around capitals and ports on the globe surface.
class_name BuildingGenerator
extends Node3D


func setup(world_data: Dictionary) -> void:
	# Clear previous
	for child in get_children():
		child.queue_free()

	var faction_colors: Dictionary = {
		"reach": Color(0.35, 0.18, 0.12),   # warm dark timber/ceramic
		"lattice": Color(0.30, 0.33, 0.38), # cool dark steel/concrete
		"other": Color(0.35, 0.32, 0.28),   # neutral stone
	}

	# Collect transforms per faction
	var faction_transforms: Dictionary = { "reach": [], "lattice": [], "other": [] }

	var settlements: Array = world_data.get("settlements", [])
	for s_idx in settlements.size():
		var settlement: Dictionary = settlements[s_idx]
		var num_buildings: int = clampi(int(settlement.importance * 20.0), 3, 20)
		var center := Vector3(settlement.cx, settlement.cy, settlement.cz)
		var radius: float = settlement.get("radius", 0.01)

		var faction: String = settlement.get("faction", "other")
		if not faction_transforms.has(faction):
			faction = "other"

		# Deterministic RNG seeded from arch index + settlement index
		var rng := RNG.new(settlement.get("arch_idx", s_idx) * 1000 + s_idx + 7)

		# Tangent frame at settlement center
		var up := center.normalized()
		var right := Vector3.UP.cross(up)
		if right.length_squared() < 0.001:
			right = Vector3.RIGHT.cross(up)
		right = right.normalized()
		var forward := up.cross(right).normalized()

		for _b in num_buildings:
			var theta: float = rng.next_float() * TAU
			var dist: float = rng.next_float() * radius
			var offset: Vector3 = right * cos(theta) * dist + forward * sin(theta) * dist
			var pos: Vector3 = (center + offset).normalized() * 1.001

			# Building dimensions
			var w: float = 0.003 + rng.next_float() * 0.003
			var h: float = 0.002 + rng.next_float() * 0.006
			var d: float = w

			# Orient perpendicular to sphere
			var loc_up := pos.normalized()
			var loc_right := Vector3.UP.cross(loc_up)
			if loc_right.length_squared() < 0.001:
				loc_right = Vector3.RIGHT.cross(loc_up)
			loc_right = loc_right.normalized()
			var loc_fwd := loc_up.cross(loc_right).normalized()

			var basis := Basis(loc_right * w, loc_up * h, loc_fwd * d)
			faction_transforms[faction].append(Transform3D(basis, pos))

	# Build MultiMeshInstance3D per faction
	var base_mesh := BoxMesh.new()
	base_mesh.size = Vector3(1.0, 1.0, 1.0)  # unit box, scaled by transform

	for faction in faction_transforms:
		var transforms: Array = faction_transforms[faction]
		if transforms.is_empty():
			continue

		var mm := MultiMesh.new()
		mm.mesh = base_mesh
		mm.transform_format = MultiMesh.TRANSFORM_3D
		mm.instance_count = transforms.size()
		for i in transforms.size():
			mm.set_instance_transform(i, transforms[i])

		var mat := StandardMaterial3D.new()
		mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		mat.albedo_color = faction_colors.get(faction, Color(0.35, 0.32, 0.28))

		var inst := MultiMeshInstance3D.new()
		inst.multimesh = mm
		inst.material_override = mat
		inst.name = "Buildings_%s" % faction
		add_child(inst)
