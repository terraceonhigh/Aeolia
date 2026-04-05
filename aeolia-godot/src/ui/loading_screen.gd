## Full-screen loading overlay with animated spinner and status messages.
## Displayed during world generation.  Call show_loading() / hide_loading()
## and update_status() from the generation coroutine.
class_name LoadingScreen
extends CanvasLayer

var _panel: ColorRect
var _spinner: Label
var _status: Label
var _phase: Label
var _tween: Tween

## Spinner frames — rotating braille clock
const SPINNER_FRAMES := ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
var _frame_idx: int = 0
var _spin_timer: float = 0.0


func _ready() -> void:
	layer = 100  # above everything

	# Full-screen dark background
	_panel = ColorRect.new()
	_panel.color = Color(0.012, 0.024, 0.063, 1.0)  # #030610
	_panel.anchor_right = 1.0
	_panel.anchor_bottom = 1.0
	add_child(_panel)

	# Title
	var title := Label.new()
	title.text = "AEOLIA"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.anchor_left = 0.0
	title.anchor_right = 1.0
	title.anchor_top = 0.35
	title.anchor_bottom = 0.35
	title.offset_top = -30
	title.offset_bottom = 30
	title.add_theme_font_size_override("font_size", 96)
	title.add_theme_color_override("font_color", Color(0.831, 0.878, 0.925, 0.8))  # #d4e0ec
	_panel.add_child(title)

	# Spinner
	_spinner = Label.new()
	_spinner.text = SPINNER_FRAMES[0]
	_spinner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_spinner.anchor_left = 0.0
	_spinner.anchor_right = 1.0
	_spinner.anchor_top = 0.48
	_spinner.anchor_bottom = 0.48
	_spinner.offset_top = -20
	_spinner.offset_bottom = 20
	_spinner.add_theme_font_size_override("font_size", 64)
	_spinner.add_theme_color_override("font_color", Color(0.855, 0.647, 0.251, 0.9))  # #daa540 gold
	_panel.add_child(_spinner)

	# Phase label (e.g. "Generating terrain...")
	_phase = Label.new()
	_phase.text = ""
	_phase.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_phase.anchor_left = 0.0
	_phase.anchor_right = 1.0
	_phase.anchor_top = 0.55
	_phase.anchor_bottom = 0.55
	_phase.offset_top = -12
	_phase.offset_bottom = 12
	_phase.add_theme_font_size_override("font_size", 48)
	_phase.add_theme_color_override("font_color", Color(0.604, 0.690, 0.784, 0.7))  # #9ab0c8
	_panel.add_child(_phase)

	# Detailed status line
	_status = Label.new()
	_status.text = ""
	_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_status.anchor_left = 0.0
	_status.anchor_right = 1.0
	_status.anchor_top = 0.60
	_status.anchor_bottom = 0.60
	_status.offset_top = -10
	_status.offset_bottom = 10
	_status.add_theme_font_size_override("font_size", 36)
	_status.add_theme_color_override("font_color", Color(0.376, 0.471, 0.533, 0.5))  # #607888
	_panel.add_child(_status)

	set_process(true)
	visible = false


func _process(delta: float) -> void:
	if not visible:
		return
	# Animate spinner
	_spin_timer += delta
	if _spin_timer >= 0.08:
		_spin_timer = 0.0
		_frame_idx = (_frame_idx + 1) % SPINNER_FRAMES.size()
		_spinner.text = SPINNER_FRAMES[_frame_idx]


## Show the loading screen.
func show_loading() -> void:
	visible = true
	_panel.color.a = 1.0


## Hide the loading screen with a fade.
func hide_loading() -> void:
	if _tween:
		_tween.kill()
	_tween = create_tween()
	_tween.tween_property(_panel, "color:a", 0.0, 0.4)
	_tween.tween_callback(func(): visible = false)


## Update the phase heading (short, e.g. "Sculpting terrain").
func set_phase(text: String) -> void:
	_phase.text = text


## Update the detail status line (e.g. "42 archipelagos, 180 edges").
func set_status(text: String) -> void:
	_status.text = text
