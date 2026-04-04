class_name ArchLabelManager
extends Node3D

## Manages floating Label3D nodes for all 42 archipelagos (arches) in Aeolia.
## Labels show the polity/faction name positioned at each archipelago with hemisphere culling
## to hide labels that face away from the camera.

# Color mapping for different factions
const FACTION_COLORS = {
	"reach": Color(0.85, 0.35, 0.25),      # Reddish
	"lattice": Color(0.25, 0.55, 0.85),    # Bluish
	"unknown": Color(0.5, 0.5, 0.5),       # Gray
	"other": Color(0.7, 0.7, 0.6)          # Beige
}

const LABEL_FONT_SIZE: int = 6
const LABEL_PIXEL_SIZE: float = 0.005
const LABEL_OUTLINE_SIZE: int = 3
const LABEL_POSITION_SCALE: float = 1.008  # Push labels just above sphere surface
const LABEL_RENDER_PRIORITY: int = 10


func _ready() -> void:
	set_process(true)


## Initializes all archipelago labels from world data.
##
## Args:
##   world_data: Dictionary containing archipelago positions and polity information
##               Expected structure:
##               - archs: Array of archipelago center positions [Vector3, ...]
##               - history: Dictionary with states information
##                 - states: Array of state dictionaries with 'name' and 'faction' keys
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

	# Create a label for each archipelago
	for i in range(mini(archs.size(), states.size())):
		var arch: Dictionary = archs[i]
		var state: Dictionary = states[i]

		var label := Label3D.new()

		# Set text from polity name
		label.text = state.get("name", "Arch %d" % i)

		# Position at archipelago center, pushed outward
		var center := Vector3(arch.cx, arch.cy, arch.cz)
		label.position = center * LABEL_POSITION_SCALE

		# Configure text rendering
		label.font_size = LABEL_FONT_SIZE
		label.pixel_size = LABEL_PIXEL_SIZE
		label.outline_size = LABEL_OUTLINE_SIZE

		# Set color based on faction
		var faction = state.get("faction", "unknown") as String
		var color = FACTION_COLORS.get(faction, FACTION_COLORS["other"])
		label.modulate = color

		# Always face the camera
		label.billboard = BaseMaterial3D.BILLBOARD_ENABLED

		# Render on top of other elements
		label.render_priority = LABEL_RENDER_PRIORITY

		# Add as child node
		add_child(label)


## Per-frame update to handle hemisphere culling.
## Hides labels that face away from the camera to avoid visual clutter and overlap.
func _process(_delta: float) -> void:
	var camera = get_viewport().get_camera_3d()
	if camera == null:
		return

	# Get camera forward direction (negative Z in camera space)
	var camera_forward = -camera.global_transform.basis.z

	# Check visibility for each label child
	for child in get_children():
		if child is Label3D:
			var label = child as Label3D

			# Get normalized direction from origin to label
			var label_direction = label.position.normalized()

			# Calculate dot product to determine if label faces camera
			# Positive values = facing camera, negative = facing away
			# Use -0.1 threshold for generous culling (allows edge labels to show)
			var dot_product = label_direction.dot(camera_forward)

			# Show if dot product > -0.1 (slightly generous to handle edge cases)
			label.visible = dot_product > -0.1
