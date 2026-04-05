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

# -- Loading --
var loading: LoadingScreen


func _ready() -> void:
	# Create a persistent loading screen (lives outside the regeneration cycle)
	loading = LoadingScreen.new()
	loading.name = "LoadingScreen"
	add_child(loading)

	_generate_world(world_seed)


## Coroutine-style world generation with loading screen updates.
## Each phase yields one frame so the spinner animates visibly.
func _generate_world(p_seed: int) -> void:
	world_seed = p_seed

	# Show loading screen
	loading.show_loading()
	loading.set_phase("Initializing...")
	loading.set_status("seed %d" % world_seed)

	# Clean up previous children (except loading screen)
	for child in get_children():
		if child != loading:
			child.queue_free()

	# Yield a frame so the loading screen paints
	await get_tree().process_frame

	# ── Phase 1: Simulation ──
	loading.set_phase("Simulating history...")
	loading.set_status("Building archipelagos, running Dijkstra wavefronts")
	await get_tree().process_frame

	print("Aeolia — generating world from seed %d..." % world_seed)
	var t0 := Time.get_ticks_msec()
	world = WorldGenerator.build_world(world_seed)
	var elapsed := Time.get_ticks_msec() - t0
	print("World generated in %d ms" % elapsed)
	print("  %d archipelagos, %d edges, %d settlements" % [
		world.archs.size(), world.edges.size(), world.settlements.size()])

	loading.set_status("%d archipelagos · %d edges · %d settlements · %d ms" % [
		world.archs.size(), world.edges.size(), world.settlements.size(), elapsed])
	await get_tree().process_frame

	# ── Phase 2: Lighting ──
	loading.set_phase("Setting up lighting...")
	loading.set_status("Sun, environment, atmosphere")
	await get_tree().process_frame

	_setup_lighting()

	# ── Phase 3: Globe mesh ──
	loading.set_phase("Sculpting terrain...")
	loading.set_status("Cube-sphere quadtree · %dx%d tiles · max depth %d" % [GlobeMesh.TILE_RES, GlobeMesh.TILE_RES, GlobeMesh.MAX_DEPTH])
	await get_tree().process_frame

	globe = GlobeMesh.new()
	globe.name = "Globe"
	add_child(globe)
	var t1 := Time.get_ticks_msec()
	await globe.generate(world, 5)
	print("Globe mesh generated in %d ms" % (Time.get_ticks_msec() - t1))

	# ── Phase 4: Atmosphere ── (disabled — JSX has no atmosphere effect)
	# atmosphere = Atmosphere.new()
	# atmosphere.name = "Atmosphere"
	# add_child(atmosphere)
	# atmosphere.setup()

	# ── Phase 5: Network + labels + buildings ──
	loading.set_phase("Placing civilizations...")
	loading.set_status("Edges, labels, settlements, buildings")
	await get_tree().process_frame

	plateau = PlateauRenderer.new()
	plateau.name = "PlateauGraph"
	add_child(plateau)
	plateau.setup(world)

	labels = ArchLabelManager.new()
	labels.name = "ArchLabels"
	add_child(labels)
	labels.setup(world)

	buildings = BuildingGenerator.new()
	buildings.name = "Buildings"
	add_child(buildings)
	buildings.setup(world)

	# ── Phase 6: Camera ──
	loading.set_phase("Focusing camera...")
	loading.set_status("")
	await get_tree().process_frame

	camera = Camera3D.new()
	camera.name = "Camera"
	camera.set_script(preload("res://src/rendering/camera/arcball_camera.gd"))
	camera.near = 0.001  # min_distance=1.007 puts camera 0.007 above sphere surface
	camera.far = 200.0
	camera.fov = 45.0
	add_child(camera)
	camera.make_current()

	# Attach sun to camera so it always lights from behind the viewer
	_attach_sun_to_camera()

	# ── Phase 7: UI ──
	loading.set_phase("Booting interface...")
	loading.set_status("")
	await get_tree().process_frame

	ui = UILayer.new()
	ui.name = "UI"
	add_child(ui)
	ui.setup(world)
	ui.seed_changed.connect(_on_seed_changed)
	ui.sun_dimmer_changed.connect(_on_sun_dimmer_changed)
	ui.sea_level_changed.connect(_on_sea_level_changed)
	ui.bridge_width_changed.connect(_on_bridge_width_changed)
	ui.urban_mode_changed.connect(_on_urban_mode_changed)

	# ── Done ──
	var reach_name: String = world.history.states[world.reach_arch].name
	var lattice_name: String = world.history.states[world.lattice_arch].name
	print("Aeolia ready. Reach: %s | Lattice: %s" % [reach_name, lattice_name])
	if world.history.df_year != null:
		print("Dark Forest breaks: %d BP" % absi(world.history.df_year))

	loading.set_phase("Welcome to Aeolia")
	loading.set_status("%s vs %s · Dark Forest: %s BP" % [
		reach_name, lattice_name,
		str(absi(world.history.df_year)) if world.history.df_year != null else "?"
	])
	await get_tree().process_frame

	loading.hide_loading()


var _lod_cooldown: float = 0.0  # seconds remaining before next LOD update

func _process(delta: float) -> void:
	# ── LOD: cube-sphere quadtree updates based on camera position ──
	# Cooldown prevents frame drops from rapid zoom.
	if _lod_cooldown > 0.0:
		_lod_cooldown -= delta
	elif globe and camera and globe._world_data.size() > 0:
		globe.update_lod(camera.global_position)
		_lod_cooldown = 0.15  # throttle LOD updates


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
	camera.add_child(sun)


func _on_sun_dimmer_changed(value: float) -> void:
	if sun:
		sun.light_energy = value


func _on_sea_level_changed(value: float) -> void:
	if globe and world.size() > 0:
		globe.sea_level = value
		globe.clear_cache()
		globe._needs_rebuild = true


func _on_bridge_width_changed(value: float) -> void:
	if globe and world.size() > 0:
		globe.bw_scale = value
		globe.clear_cache()
		globe._needs_rebuild = true


func _on_urban_mode_changed(mode: int) -> void:
	if globe and world.size() > 0:
		globe.urban_mode = mode
		globe.clear_cache()
		globe._needs_rebuild = true


func _unhandled_input(event: InputEvent) -> void:
	# Click to select an archipelago
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT and mb.pressed == false and not mb.is_echo():
			_try_select_arch(mb.position)


func _try_select_arch(screen_pos: Vector2) -> void:
	if not camera or not world.has("archs"):
		return

	var from := camera.project_ray_origin(screen_pos)
	var dir := camera.project_ray_normal(screen_pos)

	var best_idx := -1
	var best_dist := 0.05  # Angular threshold for selection

	for i in world.archs.size():
		var a: Dictionary = world.archs[i]
		var arch_pos := Vector3(a.cx, a.cy, a.cz)

		var to_arch := arch_pos - from
		var t := to_arch.dot(dir)
		if t < 0.0:
			continue
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
	call_deferred("_generate_world", new_seed)
