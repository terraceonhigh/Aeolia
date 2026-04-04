## Aeolia — main entry point.
## Generates a world, builds the 3D globe, and wires up interaction.
## Google Earth-style: drag to rotate, scroll to zoom, click archs for detail.
extends Node3D

@export var world_seed: int = 42

var world: Dictionary

# -- Scene components --
var globe: GlobeMesh
var atmosphere: Atmosphere
var plateau: PlateauRenderer
var labels: ArchLabelManager
var buildings: BuildingGenerator
var camera: Camera3D  # ArcballCamera script
var ui: UILayer

# -- Lighting --
var sun: DirectionalLight3D
var env: WorldEnvironment


func _ready() -> void:
	_generate_world(world_seed)


func _generate_world(p_seed: int) -> void:
	world_seed = p_seed

	# Clean up previous children (for regeneration)
	for child in get_children():
		child.queue_free()

	# -- Generate simulation data --
	print("Aeolia — generating world from seed %d..." % world_seed)
	var t0 := Time.get_ticks_msec()
	world = WorldGenerator.build_world(world_seed)
	var elapsed := Time.get_ticks_msec() - t0
	print("World generated in %d ms" % elapsed)
	print("  %d archipelagos, %d edges, %d settlements" % [
		world.archs.size(), world.edges.size(), world.settlements.size()])

	# -- Lighting --
	_setup_lighting()

	# -- Globe mesh --
	globe = GlobeMesh.new()
	globe.name = "Globe"
	add_child(globe)
	print("Generating globe mesh...")
	var t1 := Time.get_ticks_msec()
	globe.generate(world)
	print("Globe mesh generated in %d ms" % (Time.get_ticks_msec() - t1))

	# -- Atmosphere --
	atmosphere = Atmosphere.new()
	atmosphere.name = "Atmosphere"
	add_child(atmosphere)
	atmosphere.setup()

	# -- Plateau edges --
	plateau = PlateauRenderer.new()
	plateau.name = "PlateauGraph"
	add_child(plateau)
	plateau.setup(world)

	# -- Labels --
	labels = ArchLabelManager.new()
	labels.name = "ArchLabels"
	add_child(labels)
	labels.setup(world)

	# -- Buildings --
	buildings = BuildingGenerator.new()
	buildings.name = "Buildings"
	add_child(buildings)
	buildings.setup(world)

	# -- Camera --
	camera = Camera3D.new()
	camera.name = "Camera"
	camera.set_script(preload("res://src/rendering/camera/arcball_camera.gd"))
	camera.far = 20.0
	camera.fov = 45.0
	add_child(camera)
	camera.make_current()

	# Attach sun to camera so it always lights from behind the viewer
	_attach_sun_to_camera()

	# -- UI --
	ui = UILayer.new()
	ui.name = "UI"
	add_child(ui)
	ui.setup(world)
	ui.seed_changed.connect(_on_seed_changed)
	ui.sun_dimmer_changed.connect(_on_sun_dimmer_changed)

	print("Aeolia ready. Reach: %s | Lattice: %s" % [
		world.history.states[world.reach_arch].name,
		world.history.states[world.lattice_arch].name])
	if world.history.df_year != null:
		print("Dark Forest breaks: %d BP" % absi(world.history.df_year))


func _setup_lighting() -> void:
	# Sun — will be reparented to camera later so it always lights from behind
	sun = DirectionalLight3D.new()
	sun.name = "Sun"
	sun.light_energy = 1.2
	sun.light_color = Color(1.0, 0.97, 0.92)
	sun.shadow_enabled = false
	# Point straight down the camera's -Z (toward the globe) with a slight angle
	sun.rotation_degrees = Vector3(-15, 0, 0)
	# Don't add to scene yet — _attach_sun_to_camera() adds it to camera

	# Environment — maritime atmosphere
	var env_res := Environment.new()
	env_res.background_mode = Environment.BG_COLOR
	env_res.background_color = Color(0.02, 0.02, 0.06)
	env_res.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env_res.ambient_light_color = Color(0.15, 0.18, 0.25)
	env_res.ambient_light_energy = 0.4
	env_res.glow_enabled = true
	env_res.glow_intensity = 0.3
	env_res.glow_bloom = 0.1

	env = WorldEnvironment.new()
	env.name = "Environment"
	env.environment = env_res
	add_child(env)


func _attach_sun_to_camera() -> void:
	# Add sun as a child of the camera so it moves with it.
	# The light direction is relative to the camera — always shining forward.
	camera.add_child(sun)


func _on_sun_dimmer_changed(value: float) -> void:
	if sun:
		sun.light_energy = value


func _unhandled_input(event: InputEvent) -> void:
	# Click to select an archipelago
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT and mb.pressed == false and not mb.is_echo():
			# Only select if it was a click (not a drag)
			# Check if mouse moved very little since press
			_try_select_arch(mb.position)


func _try_select_arch(screen_pos: Vector2) -> void:
	if not camera or not world.has("archs"):
		return

	# Cast a ray from the screen position
	var from := camera.project_ray_origin(screen_pos)
	var dir := camera.project_ray_normal(screen_pos)

	# Find the closest arch to the ray
	var best_idx := -1
	var best_dist := 0.05  # Angular threshold for selection

	for i in world.archs.size():
		var a: Dictionary = world.archs[i]
		var arch_pos := Vector3(a.cx, a.cy, a.cz)

		# Point-to-ray distance
		var to_arch := arch_pos - from
		var t := to_arch.dot(dir)
		if t < 0.0:
			continue  # Behind camera
		var closest := from + dir * t
		var dist := closest.distance_to(arch_pos)

		if dist < best_dist:
			best_dist = dist
			best_idx = i

	if best_idx >= 0 and ui:
		ui.show_arch(best_idx, world)
		print("Selected: %s (#%d)" % [world.history.states[best_idx].name, best_idx])


func _on_seed_changed(new_seed: int) -> void:
	print("Regenerating world with seed %d..." % new_seed)
	# Defer to avoid issues during signal processing
	call_deferred("_generate_world", new_seed)
