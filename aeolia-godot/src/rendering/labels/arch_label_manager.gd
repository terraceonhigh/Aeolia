class_name ArchLabelManager
extends Node3D

## Manages floating Label3D nodes for all 42 archipelagos (arches) in Aeolia.
## Labels show the polity/faction name positioned at each archipelago with
## geometric horizon culling to hide labels on the far side of the globe.

# Color mapping for different factions
const FACTION_COLORS = {
	"reach": Color(0.85, 0.35, 0.25),
	"lattice": Color(0.25, 0.55, 0.85),
	"unknown": Color(0.5, 0.5, 0.5),
	"other": Color(0.7, 0.7, 0.6)
}

const LABEL_FONT_SIZE: int = 48
const LABEL_PIXEL_SIZE: float = 0.000625  # = old 0.005 * (6/48): same visual size, 8x resolution
const LABEL_OUTLINE_SIZE: int = 3
const LABEL_POSITION_SCALE: float = 1.02  # JSX uses 1.02; was 1.008 which caused z-clipping
const LABEL_RENDER_PRIORITY: int = 10


func _ready() -> void:
	set_process(true)


## Initializes all archipelago labels from world data.
func setup(world_data: Dictionary) -> void:
	if not world_data.has("archs") or not world_data.has("history"):
		push_error("ArchLabelManager.setup: Invalid world_data structure")
		return

	var archs = world_data["archs"]
	var history = world_data["history"]

	if not history.has("states"):
		push_error("ArchLabelManager.setup: No states in history data")
		return

	var states = history["states"]

	for i in range(mini(archs.size(), states.size())):
		var arch: Dictionary = archs[i]
		var state: Dictionary = states[i]

		var label := Label3D.new()
		label.text = state.get("name", "Arch %d" % i)

		var center := Vector3(arch.cx, arch.cy, arch.cz)
		label.position = center * LABEL_POSITION_SCALE

		label.font_size = LABEL_FONT_SIZE
		label.pixel_size = LABEL_PIXEL_SIZE
		label.outline_size = LABEL_OUTLINE_SIZE

		var faction = state.get("faction", "unknown") as String
		var color = FACTION_COLORS.get(faction, FACTION_COLORS["other"])
		label.modulate = color

		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		label.no_depth_test = true
		label.render_priority = LABEL_RENDER_PRIORITY

		add_child(label)


## Per-frame: geometric horizon culling using camera distance.
func _process(_delta: float) -> void:
	var camera: Camera3D = get_viewport().get_camera_3d()
	if camera == null:
		return

	var cam_pos: Vector3 = camera.global_position
	var cam_dist: float = cam_pos.length()
	var cam_dir: Vector3 = cam_pos.normalized()

	# Geometric horizon: point visible iff dot(point_dir, cam_dir) > cutoff
	var cutoff: float
	if cam_dist <= 1.0:
		cutoff = -1.0
	else:
		cutoff = cos(acos(1.0 / cam_dist) + deg_to_rad(3.0))

	for child in get_children():
		if child is Label3D:
			var label_dir: Vector3 = (child as Label3D).position.normalized()
			child.visible = label_dir.dot(cam_dir) > cutoff
