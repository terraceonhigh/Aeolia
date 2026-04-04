## True quaternion arcball camera.
## Both drag axes rotate in camera-local space — no world-axis mixing,
## no pole singularity, free rotation in every direction.
## Transform built entirely from Basis(Quaternion): always orthonormal.
extends Camera3D

# -- Zoom --
@export var min_distance := 1.15
@export var max_distance := 5.0
@export var zoom_speed := 0.15
@export var zoom_smoothing := 8.0

# -- Rotation --
@export var rotate_speed := 0.004
@export var inertia_damping := 0.92

# -- State --
var _orientation := Quaternion.IDENTITY
var _distance: float = 3.0
var _target_distance: float = 3.0
var _dragging := false
var _spin := Quaternion.IDENTITY  # per-frame inertia rotation


func _ready() -> void:
	# Start tilted slightly
	_orientation = Quaternion(Vector3.UP, 0.4) * Quaternion(Vector3.RIGHT, 0.3)
	_orientation = _orientation.normalized()
	_apply_transform()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			_dragging = mb.pressed
			if mb.pressed:
				_spin = Quaternion.IDENTITY
			get_viewport().set_input_as_handled()
		elif mb.button_index == MOUSE_BUTTON_WHEEL_UP:
			_target_distance = maxf(min_distance, _target_distance * (1.0 - zoom_speed))
			get_viewport().set_input_as_handled()
		elif mb.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_target_distance = minf(max_distance, _target_distance * (1.0 + zoom_speed))
			get_viewport().set_input_as_handled()

	if event is InputEventMouseMotion and _dragging:
		var mm := event as InputEventMouseMotion
		var q := _rotation_from_mouse(mm.relative)
		_orientation = (q * _orientation).normalized()
		_spin = q  # store for inertia on release
		_apply_transform()
		get_viewport().set_input_as_handled()


func _process(delta: float) -> void:
	var needs_update := false

	# Inertial spin — slerp the per-frame rotation toward identity
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


## Convert a mouse delta into an incremental rotation quaternion.
## Horizontal pixels → rotate around camera-local Y (up).
## Vertical pixels   → rotate around camera-local X (right).
## Both in camera space — no world axes, no singularities.
func _rotation_from_mouse(relative: Vector2) -> Quaternion:
	var ori_basis := Basis(_orientation)
	var cam_right: Vector3 = ori_basis.x  # already normalized (orthonormal basis)
	var cam_up: Vector3 = ori_basis.y

	var angle_x: float = -relative.x * rotate_speed
	var angle_y: float = -relative.y * rotate_speed

	var q_yaw := Quaternion(cam_up, angle_x)
	var q_pitch := Quaternion(cam_right, angle_y)
	return (q_yaw * q_pitch).normalized()


## Transform: Basis directly from quaternion, position along +Z * distance.
## Camera looks along -Z toward origin. Always orthonormal.
func _apply_transform() -> void:
	var ori_basis := Basis(_orientation)
	var pos := ori_basis * Vector3(0.0, 0.0, _distance)
	global_transform = Transform3D(ori_basis, pos)


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
