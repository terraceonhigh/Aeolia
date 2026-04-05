## True raycast arcball camera.
## On click, raycasts to find the grabbed point on the unit sphere.
## During drag, rotates the camera orbit so that sphere point stays
## pinned under the cursor.  No speed constants — pure geometry.
extends Camera3D

# -- Zoom --
# JSX uses R=5; Godot uses R=1 — divide all JSX distances by 5.
# JSX: default=22, min=R*1.007=5.035, max=60
# Godot: default=22/5=4.4, min=5.035/5=1.007, max=60/5=12.0
@export var min_distance := 1.007
@export var max_distance := 12.0
@export var zoom_speed := 0.10        # JSX: deltaY*0.001 ≈ 10% per notch
@export var zoom_smoothing := 8.0

# -- Inertia --
@export var inertia_damping := 0.92

# -- State --
var _orientation := Quaternion.IDENTITY
var _distance: float = 4.4
var _target_distance: float = 4.4
var _dragging := false
var _spin := Quaternion.IDENTITY          # last frame's incremental rotation (for coast)
var _grab_point := Vector3.ZERO           # point on unit sphere grabbed at drag start


func _ready() -> void:
	_orientation = Quaternion(Vector3.UP, 0.4) * Quaternion(Vector3.RIGHT, 0.3)
	_orientation = _orientation.normalized()
	_apply_transform()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_dragging = true
				_spin = Quaternion.IDENTITY
				_grab_point = _screen_to_sphere(mb.position)
			else:
				_dragging = false
			get_viewport().set_input_as_handled()
		elif mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			_target_distance = maxf(min_distance, _target_distance * (1.0 - zoom_speed))
			get_viewport().set_input_as_handled()
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_target_distance = minf(max_distance, _target_distance * (1.0 + zoom_speed))
			get_viewport().set_input_as_handled()

	if event is InputEventMouseMotion and _dragging:
		var mm := event as InputEventMouseMotion
		var current := _screen_to_sphere(mm.position)
		# Rotation that brings `current` to `_grab_point` on the unit sphere,
		# i.e. orbits the camera so the grabbed point lands under the cursor.
		var q := _quat_between(current, _grab_point)
		_orientation = (q * _orientation).normalized()
		_spin = q
		_apply_transform()
		get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	var needs_update := false

	# Inertial coast — slerp the per-frame rotation toward identity
	if not _dragging and not _spin.is_equal_approx(Quaternion.IDENTITY):
		_orientation = (_spin * _orientation).normalized()
		_spin = _spin.slerp(Quaternion.IDENTITY, 1.0 - inertia_damping)
		needs_update = true

	# Smooth zoom
	if absf(_distance - _target_distance) > 0.001:
		_distance = lerpf(_distance, _target_distance, delta * zoom_smoothing)
		needs_update = true

	if needs_update:
		_apply_transform()


# ── Raycasting ────────────────────────────────────────────────────────

## Project a screen position onto the unit sphere at the origin.
## If the ray hits the sphere, returns the near intersection (front face).
## If the ray misses (cursor past the limb), returns the nearest point
## on the sphere to the ray — so dragging past the edge still rotates.
func _screen_to_sphere(screen_pos: Vector2) -> Vector3:
	var ray_from := project_ray_origin(screen_pos)
	var ray_dir := project_ray_normal(screen_pos)

	# Solve |ray_from + t * ray_dir|² = 1  (unit sphere)
	var a := ray_dir.dot(ray_dir)
	var b := 2.0 * ray_from.dot(ray_dir)
	var c := ray_from.dot(ray_from) - 1.0
	var disc := b * b - 4.0 * a * c

	if disc >= 0.0:
		# Hit — near intersection
		var t := (-b - sqrt(disc)) / (2.0 * a)
		return (ray_from + t * ray_dir).normalized()
	else:
		# Miss — closest approach on ray, projected onto sphere
		var t_closest := maxf(0.0, -ray_from.dot(ray_dir) / a)
		return (ray_from + t_closest * ray_dir).normalized()


# ── Quaternion helpers ────────────────────────────────────────────────

## Quaternion that rotates unit vector `from` to unit vector `to`.
## Uses the half-vector method — no trig functions, numerically stable.
func _quat_between(from: Vector3, to: Vector3) -> Quaternion:
	var d := from.dot(to)
	if d > 0.99999:
		return Quaternion.IDENTITY
	if d < -0.99999:
		# ~180°: pick any perpendicular axis
		var perp := Vector3.RIGHT.cross(from)
		if perp.length_squared() < 0.0001:
			perp = Vector3.UP.cross(from)
		return Quaternion(perp.normalized(), PI)
	var cross := from.cross(to)
	# q = (cross.x, cross.y, cross.z, 1 + dot)  then normalize
	return Quaternion(cross.x, cross.y, cross.z, 1.0 + d).normalized()


# ── Transform ─────────────────────────────────────────────────────────

## Camera looks along -Z toward origin.  Position along +Z * distance.
func _apply_transform() -> void:
	var ori_basis := Basis(_orientation)
	var pos := ori_basis * Vector3(0.0, 0.0, _distance)
	global_transform = Transform3D(ori_basis, pos)


# ── Public API ────────────────────────────────────────────────────────

## Fly to look at a surface point.
func fly_to(surface_point: Vector3, target_dist: float = -1.0) -> void:
	var dir := surface_point.normalized()
	var z_axis := dir
	var ref_up := Vector3.UP
	if absf(z_axis.dot(ref_up)) > 0.99:
		ref_up = Vector3.RIGHT
	var x_axis := ref_up.cross(z_axis).normalized()
	var y_axis := z_axis.cross(x_axis).normalized()
	_orientation = Basis(x_axis, y_axis, z_axis).get_rotation_quaternion().normalized()
	if target_dist > 0.0:
		_target_distance = clampf(target_dist, min_distance, max_distance)
	_spin = Quaternion.IDENTITY
	_apply_transform()


## Current view direction (toward origin).
func get_view_direction() -> Vector3:
	return -global_position.normalized()
