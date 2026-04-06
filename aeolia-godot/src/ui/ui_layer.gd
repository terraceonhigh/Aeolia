## UI layer — pixel-accurate recreation of the React/Three.js Aeolia UI.
## Three-column layout: left sidebar (political map), center (3D viewport),
## right sidebar (controls).  Header bar with stats.  Detail panel on click.
## Dark sci-fi theme, monospace font, navy/blue color scheme.
class_name UILayer
extends CanvasLayer

signal seed_changed(new_seed: int)
signal sea_level_changed(value: float)
signal bridge_width_changed(value: float)
signal sun_dimmer_changed(value: float)
signal urban_mode_changed(mode: int)
signal zoom_speed_changed(value: float)

# ── Color palette (matches React original) ──
const C_BG        := Color(0.012, 0.024, 0.063)  # #030610
const C_BG_DARK   := Color(0.020, 0.039, 0.071)  # #050a12
const C_BG_GRAD   := Color(0.024, 0.043, 0.078)  # #060b14
const C_BORDER    := Color(0.059, 0.102, 0.157)  # #0f1a28
const C_BORDER2   := Color(0.102, 0.165, 0.227)  # #1a2a3a
const C_INPUT_BG  := Color(0.039, 0.071, 0.094)  # #0a1218
const C_TEXT      := Color(0.690, 0.769, 0.847)  # #b0c4d8
const C_TEXT_SEC  := Color(0.604, 0.690, 0.784)  # #9ab0c8
const C_TEXT_DIM  := Color(0.541, 0.627, 0.722)  # #8aa0b8
const C_TEXT_MUTE := Color(0.376, 0.471, 0.533)  # #607888
const C_GOLD      := Color(0.855, 0.647, 0.251)  # #daa540
const C_HEAD_TEXT := Color(0.831, 0.878, 0.925)  # #d4e0ec
const C_REACH     := Color(1.0, 0.8, 0.667)      # #ffccaa
const C_LATTICE   := Color(0.667, 0.8, 1.0)      # #aaccff
const C_CONTACT   := Color(1.0, 0.4, 0.267)      # #ff6644
const C_UNKNOWN   := Color(0.282, 0.282, 0.282)  # #484848

# ── Layout constants ──
const SIDEBAR_W := 460
const DETAIL_W  := 500

# ── Node refs ──
var header: PanelContainer
var left_sidebar: PanelContainer
var right_sidebar: PanelContainer
var detail_panel: PanelContainer
var detail_vbox: VBoxContainer
var stats_label: Label
var seed_input: SpinBox
var left_scroll_vbox: VBoxContainer

## Debug overlay label (FPS + tile count). Updated externally via update_debug().
var _debug_label: Label

var _world_data: Dictionary = {}


func setup(world_data: Dictionary) -> void:
	_world_data = world_data
	for child in get_children():
		child.queue_free()
	_debug_label = null  # reset — will be recreated in _build_debug_overlay
	_build_header()
	_build_left_sidebar()
	_build_right_sidebar()
	_build_detail_panel()
	_build_debug_overlay()


# ═══════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════
func _build_header() -> void:
	header = PanelContainer.new()
	header.anchor_left = 0.0
	header.anchor_right = 1.0
	header.anchor_top = 0.0
	header.anchor_bottom = 0.0
	header.offset_bottom = 100
	_set_panel_style(header, C_BG_GRAD, C_BORDER, false, true)
	add_child(header)
	_block_input(header)

	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 0)
	header.add_child(hbox)

	# Left side: title + stats
	var left := VBoxContainer.new()
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.add_theme_constant_override("separation", 1)
	hbox.add_child(left)

	var sub_label := Label.new()
	sub_label.text = "QUADTREE LOD TERRAIN ENGINE"
	_style_label(sub_label, 9, C_TEXT_DIM)
	left.add_child(sub_label)

	var title := Label.new()
	title.text = "AEOLIA — ADAPTIVE SURFACE"
	_style_label(title, 15, C_HEAD_TEXT)
	left.add_child(title)

	stats_label = Label.new()
	stats_label.text = ""
	_style_label(stats_label, 9, C_TEXT_DIM)
	left.add_child(stats_label)

	_update_stats()

	# Right side: engine info
	var info := Label.new()
	info.text = "GODOT 4.6\nICOSPHERE"
	info.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_style_label(info, 8, C_TEXT_MUTE)
	hbox.add_child(info)


func _update_stats() -> void:
	if not stats_label or _world_data.is_empty():
		return
	var n_arch: int = _world_data.get("archs", []).size()
	var n_edge: int = _world_data.get("edges", []).size()
	var n_sett: int = _world_data.get("settlements", []).size()
	stats_label.text = "%d archipelagos · %d edges · %d settlements" % [n_arch, n_edge, n_sett]


# ═══════════════════════════════════════════════════════════
# LEFT SIDEBAR — POLITICAL MAP
# ═══════════════════════════════════════════════════════════
func _build_left_sidebar() -> void:
	left_sidebar = PanelContainer.new()
	left_sidebar.anchor_left = 0.0
	left_sidebar.anchor_right = 0.0
	left_sidebar.anchor_top = 0.0
	left_sidebar.anchor_bottom = 1.0
	left_sidebar.offset_right = SIDEBAR_W
	left_sidebar.offset_top = 100  # below header
	_set_panel_style(left_sidebar, C_BG_DARK, C_BORDER, true, false)
	add_child(left_sidebar)
	_block_input(left_sidebar)

	var outer := VBoxContainer.new()
	outer.add_theme_constant_override("separation", 0)
	left_sidebar.add_child(outer)

	# Sidebar header
	var sh_panel := PanelContainer.new()
	_set_panel_style(sh_panel, Color(0, 0, 0, 0), C_BORDER, false, true)
	outer.add_child(sh_panel)

	var sh_vbox := VBoxContainer.new()
	sh_vbox.add_theme_constant_override("separation", 2)
	sh_panel.add_child(sh_vbox)

	var sh_title := Label.new()
	sh_title.text = "POLITICAL MAP"
	_style_label(sh_title, 10, C_GOLD)
	sh_vbox.add_child(sh_title)

	var history: Dictionary = _world_data.get("history", {})
	var log_count: int = history.get("log", []).size()
	var df_year = history.get("df_year", null)
	var df_text: String = "Dark Forest breaks %s" % [
		("%d BP" % absi(df_year)) if df_year != null else "at present"
	]

	# JSX shows: `{world.history.log.length - 1} archipelagos · Dark Forest breaks …`
	# The -1 excludes the terminal "⚠ CONTACT" DF event entry from the count.
	var sh_sub := Label.new()
	sh_sub.text = "%d archipelagos · %s" % [log_count - 1, df_text]
	_style_label(sh_sub, 8, C_TEXT_DIM)
	sh_sub.autowrap_mode = TextServer.AUTOWRAP_WORD
	sh_vbox.add_child(sh_sub)

	# Scrollable log
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	outer.add_child(scroll)

	left_scroll_vbox = VBoxContainer.new()
	left_scroll_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left_scroll_vbox.add_theme_constant_override("separation", 0)
	scroll.add_child(left_scroll_vbox)

	_populate_history_log()


func _populate_history_log() -> void:
	var history: Dictionary = _world_data.get("history", {})
	var log: Array = history.get("log", [])

	for entry in log:
		var faction: String = entry.get("faction", "other")
		var status: String = entry.get("status", "")
		var is_era: bool = (faction == "era")
		var is_contact: bool = (faction == "contact")
		var f_color: Color = _faction_color(faction)

		if is_era:
			_add_era_entry(entry, f_color)
		elif is_contact:
			_add_contact_entry(entry)
		else:
			_add_polity_entry(entry, f_color, status)


func _add_era_entry(entry: Dictionary, f_color: Color) -> void:
	var container := VBoxContainer.new()
	container.add_theme_constant_override("separation", 2)

	# Add top margin
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 8)
	container.add_child(spacer)

	var name_lbl := Label.new()
	name_lbl.text = entry.get("name", "")
	_style_label(name_lbl, 9, f_color)
	container.add_child(name_lbl)

	var label_lbl := Label.new()
	label_lbl.text = entry.get("label", "")
	_style_label(label_lbl, 7, C_TEXT_DIM)
	label_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
	container.add_child(label_lbl)

	# Bottom border
	var sep := HSeparator.new()
	var sep_style := StyleBoxLine.new()
	sep_style.color = C_BORDER2
	sep_style.thickness = 1
	sep.add_theme_stylebox_override("separator", sep_style)
	container.add_child(sep)

	left_scroll_vbox.add_child(container)


func _add_contact_entry(entry: Dictionary) -> void:
	var container := VBoxContainer.new()
	container.add_theme_constant_override("separation", 2)

	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 8)
	container.add_child(spacer)

	var name_lbl := Label.new()
	name_lbl.text = "⚠ " + entry.get("name", "CONTACT")
	_style_label(name_lbl, 10, C_CONTACT)
	container.add_child(name_lbl)

	var label_lbl := Label.new()
	label_lbl.text = entry.get("label", "")
	_style_label(label_lbl, 7, Color(1.0, 0.6, 0.467))  # #ff9977
	label_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
	container.add_child(label_lbl)

	left_scroll_vbox.add_child(container)


func _add_polity_entry(entry: Dictionary, f_color: Color, status: String) -> void:
	# Container with left border
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 10)
	margin.add_theme_constant_override("margin_bottom", 4)

	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0, 0, 0, 0)
	style.border_color = f_color
	style.border_width_left = 2
	style.content_margin_left = 8
	style.content_margin_top = 1
	style.content_margin_bottom = 1
	panel.add_theme_stylebox_override("panel", style)
	margin.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 1)
	panel.add_child(vbox)

	# Name line with icon and distance
	var name_hbox := HBoxContainer.new()
	name_hbox.add_theme_constant_override("separation", 4)
	vbox.add_child(name_hbox)

	var icon := Label.new()
	icon.text = _status_icon(status)
	_style_label(icon, 9, f_color)
	name_hbox.add_child(icon)

	var name_lbl := Label.new()
	var is_core: bool = (status == "core")
	name_lbl.text = entry.get("name", "")
	_style_label(name_lbl, 9, f_color)
	name_hbox.add_child(name_lbl)

	# Distance info
	var r_dist: int = entry.get("rDist", 0)
	var l_dist: int = entry.get("lDist", 0)
	if r_dist > 0 or l_dist > 0:
		var dist_lbl := Label.new()
		dist_lbl.text = "(%dR·%dL)" % [r_dist, l_dist]
		_style_label(dist_lbl, 9, C_TEXT_MUTE)
		name_hbox.add_child(dist_lbl)

	# Label line
	var label_lbl := Label.new()
	label_lbl.text = entry.get("label", "")
	_style_label(label_lbl, 7, C_TEXT_SEC)
	label_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
	vbox.add_child(label_lbl)

	left_scroll_vbox.add_child(margin)


# ═══════════════════════════════════════════════════════════
# RIGHT SIDEBAR — CONTROLS
# ═══════════════════════════════════════════════════════════
func _build_right_sidebar() -> void:
	right_sidebar = PanelContainer.new()
	right_sidebar.anchor_left = 1.0
	right_sidebar.anchor_right = 1.0
	right_sidebar.anchor_top = 0.0
	right_sidebar.anchor_bottom = 1.0
	right_sidebar.offset_left = -SIDEBAR_W
	right_sidebar.offset_top = 100
	_set_panel_style(right_sidebar, C_BG_DARK, C_BORDER, false, false)
	add_child(right_sidebar)
	_block_input(right_sidebar)

	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_sidebar.add_child(scroll)

	var vbox := VBoxContainer.new()
	vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	vbox.add_theme_constant_override("separation", 12)
	scroll.add_child(vbox)

	# ── World Seed ──
	_add_section_header(vbox, "WORLD SEED")
	var seed_hbox := HBoxContainer.new()
	seed_hbox.add_theme_constant_override("separation", 6)
	vbox.add_child(seed_hbox)

	seed_input = SpinBox.new()
	seed_input.min_value = 1
	seed_input.max_value = 99999
	seed_input.value = 42
	seed_input.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	seed_hbox.add_child(seed_input)

	var gen_btn := Button.new()
	gen_btn.text = "GENERATE"
	gen_btn.custom_minimum_size = Vector2(90, 0)
	gen_btn.pressed.connect(func(): seed_changed.emit(int(seed_input.value)))
	seed_hbox.add_child(gen_btn)

	var seed_help := Label.new()
	seed_help.text = "Press Enter to regenerate"
	_style_label(seed_help, 7, C_TEXT_DIM)
	vbox.add_child(seed_help)

	# ── Camera ──
	_add_section_header(vbox, "CAMERA")
	var cam_info := Label.new()
	cam_info.text = "Scroll to zoom · Drag to rotate"
	_style_label(cam_info, 9, C_TEXT_SEC)
	vbox.add_child(cam_info)

	var zoom_val_label := Label.new()
	zoom_val_label.text = "Zoom: 0.10"
	_style_label(zoom_val_label, 9, C_TEXT)
	vbox.add_child(zoom_val_label)

	var zoom_slider := HSlider.new()
	zoom_slider.min_value = 1
	zoom_slider.max_value = 20
	zoom_slider.step = 1
	zoom_slider.value = 10
	zoom_slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	zoom_slider.value_changed.connect(func(val: float):
		zoom_val_label.text = "Zoom: %.2f" % (val * 0.01)
		zoom_speed_changed.emit(val * 0.01))
	vbox.add_child(zoom_slider)

	# ── Sea Level ──
	_add_section_header(vbox, "SEA LEVEL")
	var sea_val_label := Label.new()
	sea_val_label.text = "0m"
	_style_label(sea_val_label, 9, C_TEXT)
	vbox.add_child(sea_val_label)

	var sea_slider := HSlider.new()
	sea_slider.min_value = -220
	sea_slider.max_value = 0
	sea_slider.value = 0
	sea_slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sea_slider.value_changed.connect(func(val: float):
		sea_val_label.text = "%dm" % int(val)
		if val < -50:
			sea_val_label.text += "  BRIDGES"
		sea_level_changed.emit(val))
	vbox.add_child(sea_slider)

	var sea_labels := HBoxContainer.new()
	vbox.add_child(sea_labels)
	var sea_min := Label.new()
	sea_min.text = "−220m"
	_style_label(sea_min, 8, C_TEXT_DIM)
	sea_labels.add_child(sea_min)
	var sea_spacer := Control.new()
	sea_spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sea_labels.add_child(sea_spacer)
	var sea_max := Label.new()
	sea_max.text = "0m"
	_style_label(sea_max, 8, C_TEXT_DIM)
	sea_labels.add_child(sea_max)

	# ── Land Bridges Width ──
	_add_section_header(vbox, "LAND BRIDGES")
	var bw_val_label := Label.new()
	bw_val_label.text = "0.13 rad"
	_style_label(bw_val_label, 9, C_TEXT)
	vbox.add_child(bw_val_label)

	var bw_slider := HSlider.new()
	bw_slider.min_value = 2
	bw_slider.max_value = 50
	bw_slider.value = 13
	bw_slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bw_slider.value_changed.connect(func(val: float):
		bw_val_label.text = "%.2f rad" % (val * 0.01)
		bridge_width_changed.emit(val * 0.01))
	vbox.add_child(bw_slider)

	var bw_labels := HBoxContainer.new()
	vbox.add_child(bw_labels)
	var bw_min := Label.new()
	bw_min.text = "0.02 rad"
	_style_label(bw_min, 8, C_TEXT_DIM)
	bw_labels.add_child(bw_min)
	var bw_spacer := Control.new()
	bw_spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bw_labels.add_child(bw_spacer)
	var bw_max := Label.new()
	bw_max.text = "0.50 rad"
	_style_label(bw_max, 8, C_TEXT_DIM)
	bw_labels.add_child(bw_max)

	# ── Lighting ──
	_add_section_header(vbox, "LIGHTING")
	var sun_slider := HSlider.new()
	sun_slider.min_value = 0.0
	sun_slider.max_value = 3.0
	sun_slider.step = 0.05
	sun_slider.value = 1.2
	sun_slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sun_slider.value_changed.connect(func(val: float): sun_dimmer_changed.emit(val))
	vbox.add_child(sun_slider)

	# ── Urbanization ──
	_add_section_header(vbox, "URBANIZATION")
	var urban_state := [0]  # mutable capture for closure
	var urban_btn := Button.new()
	urban_btn.text = "▢ OFF"
	urban_btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
	urban_btn.add_theme_color_override("font_color", C_TEXT_DIM)
	vbox.add_child(urban_btn)
	urban_btn.pressed.connect(func():
		urban_state[0] = (urban_state[0] + 1) % 3
		match urban_state[0]:
			0:
				urban_btn.text = "▢ OFF"
				urban_btn.add_theme_color_override("font_color", C_TEXT_DIM)
			1:
				urban_btn.text = "▣ NUCLEAR ERA"
				urban_btn.add_theme_color_override("font_color", Color(0.733, 0.6, 0.867))  # #bb99dd
			2:
				urban_btn.text = "▣ NUCLEAR ERA + LABELS"
				urban_btn.add_theme_color_override("font_color", Color(0.733, 0.6, 0.867))
		urban_mode_changed.emit(urban_state[0]))

	# ── Bathymetry Legend ──
	_add_section_header(vbox, "BATHYMETRY")
	var legend_data := [
		["Abyss",     Color(0.012, 0.039, 0.110)],  # #030a1c
		["Deep",      Color(0.039, 0.094, 0.220)],  # #0a1838
		["Mid ocean", Color(0.059, 0.157, 0.345)],  # #0f2858
		["Plateau",   Color(0.102, 0.227, 0.447)],  # #1a3a72
		["Shallow",   Color(0.176, 0.337, 0.533)],  # #2d5688
		["Coast",     Color(0.235, 0.376, 0.314)],  # #3c6050
		["Lowland",   Color(0.259, 0.345, 0.220)],  # #425838
		["Slope",     Color(0.290, 0.267, 0.188)],  # #4a4430
		["Summit",    Color(0.471, 0.439, 0.345)],  # #787058
	]
	for item in legend_data:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 6)
		vbox.add_child(row)

		var swatch := ColorRect.new()
		swatch.color = item[1]
		swatch.custom_minimum_size = Vector2(10, 7)
		row.add_child(swatch)

		var lbl := Label.new()
		lbl.text = item[0]
		_style_label(lbl, 8, C_TEXT_SEC)
		row.add_child(lbl)

	# ── Build Status ──
	_add_section_header(vbox, "BUILD STATUS")
	var status_items := [
		["✅", "Icosphere LOD"],
		["✅", "Arcball rotation"],
		["✅", "JSX-identical terrain"],
		["✅", "Naturalistic coloring"],
		["✅", "Camera-following light"],
		["✅", "Horizon culling"],
		["✅", "Political simulation"],
		["✅", "Urbanization overlay"],
		["✅", "Sea level / bridges"],
		["⬜", "Ocean shader"],
		["⬜", "Era timeline"],
	]
	for item in status_items:
		var row_lbl := Label.new()
		row_lbl.text = "%s %s" % [item[0], item[1]]
		var done: bool = (item[0] == "✅")
		_style_label(row_lbl, 8, C_TEXT_DIM if done else C_TEXT_MUTE)
		vbox.add_child(row_lbl)


# ═══════════════════════════════════════════════════════════
# DETAIL PANEL (appears on arch click, overlays the viewport)
# ═══════════════════════════════════════════════════════════
func _build_detail_panel() -> void:
	detail_panel = PanelContainer.new()
	detail_panel.anchor_left = 0.0
	detail_panel.anchor_right = 0.0
	detail_panel.anchor_top = 0.0
	detail_panel.anchor_bottom = 1.0
	detail_panel.offset_left = SIDEBAR_W + 16
	detail_panel.offset_right = SIDEBAR_W + 16 + DETAIL_W
	detail_panel.offset_top = 100 + 16
	detail_panel.offset_bottom = -16
	detail_panel.visible = false

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.020, 0.039, 0.071, 0.95)
	style.border_color = C_BORDER2
	style.set_border_width_all(1)
	style.corner_radius_top_left = 4
	style.corner_radius_top_right = 4
	style.corner_radius_bottom_left = 4
	style.corner_radius_bottom_right = 4
	style.shadow_color = Color(0, 0, 0, 0.6)
	style.shadow_size = 12
	style.content_margin_left = 14
	style.content_margin_right = 14
	style.content_margin_top = 12
	style.content_margin_bottom = 12
	detail_panel.add_theme_stylebox_override("panel", style)
	add_child(detail_panel)
	_block_input(detail_panel)

	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	detail_panel.add_child(scroll)

	detail_vbox = VBoxContainer.new()
	detail_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	detail_vbox.add_theme_constant_override("separation", 4)
	scroll.add_child(detail_vbox)


## Show the detail popup for an archipelago.
func show_arch(idx: int, world_data: Dictionary) -> void:
	if not detail_panel or not detail_vbox:
		return
	_world_data = world_data

	# Clear previous content
	for child in detail_vbox.get_children():
		child.queue_free()

	var states: Array = world_data.get("history", {}).get("states", [])
	if idx < 0 or idx >= states.size():
		return

	var state: Dictionary = states[idx]
	var faction: String = state.get("faction", "unknown")
	var f_color: Color = _faction_color(faction)

	# ── Header: name + close button ──
	var header_row := HBoxContainer.new()
	detail_vbox.add_child(header_row)

	var name_lbl := Label.new()
	name_lbl.text = state.get("name", "Archipelago %d" % idx)
	name_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_style_label(name_lbl, 12, f_color)
	header_row.add_child(name_lbl)

	var close_btn := Button.new()
	close_btn.text = "×"
	close_btn.flat = true
	close_btn.custom_minimum_size = Vector2(24, 24)
	close_btn.add_theme_color_override("font_color", C_TEXT_MUTE)
	close_btn.pressed.connect(func(): detail_panel.visible = false)
	header_row.add_child(close_btn)

	# Status line
	var status_lbl := Label.new()
	status_lbl.text = "%s · pop %s · tech %s · %s" % [
		state.get("status", "?"),
		str(state.get("population", "?")),
		str(state.get("tech", "?")),
		faction
	]
	_style_label(status_lbl, 8, C_TEXT_DIM)
	detail_vbox.add_child(status_lbl)

	_add_detail_separator()

	# ── Substrate data ──
	var substrates: Array = world_data.get("substrate", [])
	if idx < substrates.size():
		var sub: Dictionary = substrates[idx]
		_add_substrate_section(sub)

	# ── History for this arch ──
	_add_detail_section_header("HISTORY")
	var log: Array = world_data.get("history", {}).get("log", [])
	var arch_log: Array = []
	for entry in log:
		if entry.get("arch", -1) == idx:
			arch_log.append(entry)

	if arch_log.is_empty():
		var empty := Label.new()
		empty.text = "No recorded history"
		_style_label(empty, 8, C_TEXT_MUTE)
		detail_vbox.add_child(empty)
	else:
		for entry in arch_log:
			_add_detail_history_entry(entry)

	detail_panel.visible = true


func _add_substrate_section(sub: Dictionary) -> void:
	# Climate
	if sub.has("climate"):
		_add_detail_section_header("CLIMATE")
		var cli: Dictionary = sub.climate
		var grid := _make_detail_grid()
		_grid_item(grid, "Zone", cli.get("climate_zone", "?"))
		_grid_item(grid, "Temp", "%.1f°C" % cli.get("mean_temp", 0.0))
		_grid_item(grid, "Rain", "%.0f mm" % cli.get("effective_rainfall", 0.0))
		_grid_item(grid, "Wind", cli.get("wind_belt", "?"))
		detail_vbox.add_child(grid)
		_add_detail_separator()

	# Agriculture
	if sub.has("crops"):
		_add_detail_section_header("AGRICULTURE")
		var crops: Dictionary = sub.crops
		var crop_lbl := Label.new()
		crop_lbl.text = "Primary: %s" % crops.get("primary_crop", "none")
		_style_label(crop_lbl, 8, Color(0.784, 0.831, 0.878))  # #c8d4e0
		detail_vbox.add_child(crop_lbl)
		var sec: String = str(crops.get("secondary_crop", ""))
		if sec != "" and sec != "null":
			var sec_lbl := Label.new()
			sec_lbl.text = "Secondary: %s" % sec
			_style_label(sec_lbl, 8, C_TEXT_DIM)
			detail_vbox.add_child(sec_lbl)
		_add_detail_separator()

	# Trade goods
	if sub.has("trade_goods"):
		_add_detail_section_header("TRADE")
		var tg: Dictionary = sub.trade_goods
		var goods_text := ""
		if tg.has("stimulant") and tg.stimulant.get("type", "") != "":
			goods_text += "Stimulant: %s  " % tg.stimulant.type
		if tg.has("fiber") and tg.fiber.get("type", "") != "":
			goods_text += "Fiber: %s  " % tg.fiber.type
		if tg.has("protein") and tg.protein.get("type", "") != "":
			goods_text += "Protein: %s" % tg.protein.type
		if goods_text == "":
			goods_text = "none"
		var tg_lbl := Label.new()
		tg_lbl.text = goods_text
		_style_label(tg_lbl, 8, C_TEXT_SEC)
		tg_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
		detail_vbox.add_child(tg_lbl)
		_add_detail_separator()

	# Minerals
	if sub.has("minerals"):
		_add_detail_section_header("MINERALS")
		var mins: Dictionary = sub.minerals
		var found: Array[String] = []
		if mins.get("Fe", false): found.append("Fe")
		if mins.get("Cu", false): found.append("Cu")
		if mins.get("Au", false): found.append("Au")
		if mins.get("Pu", false): found.append("Pu")
		var min_lbl := Label.new()
		min_lbl.text = ", ".join(found) if found.size() > 0 else "Fe only"
		_style_label(min_lbl, 8, C_TEXT_SEC if found.size() > 0 else C_TEXT_MUTE)
		detail_vbox.add_child(min_lbl)
		_add_detail_separator()

	# Political culture
	if sub.has("political_culture"):
		_add_detail_section_header("POLITICAL CULTURE")
		var pc: Dictionary = sub.political_culture
		var pc_lbl := Label.new()
		pc_lbl.text = "%s · awareness %.2f · participation %.2f" % [
			pc.get("label", "?"), pc.get("awareness", 0.0), pc.get("participation", 0.0)
		]
		_style_label(pc_lbl, 8, C_TEXT_SEC)
		pc_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
		detail_vbox.add_child(pc_lbl)
		_add_detail_separator()

	# Production
	if sub.has("production"):
		_add_detail_section_header("PRODUCTION")
		var prod: Dictionary = sub.production
		var prod_lbl := Label.new()
		prod_lbl.text = "%s · surplus %.2f · labor %.2f" % [
			prod.get("mode_label", "?"), prod.get("surplus", 0.0), prod.get("labor", 0.0)
		]
		_style_label(prod_lbl, 8, C_TEXT_SEC)
		prod_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
		detail_vbox.add_child(prod_lbl)
		_add_detail_separator()


func _add_detail_history_entry(entry: Dictionary) -> void:
	var faction: String = entry.get("faction", "other")
	var e_color: Color = _faction_color(faction)

	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0, 0, 0, 0)
	style.border_color = e_color
	style.border_width_left = 2
	style.content_margin_left = 8
	style.content_margin_bottom = 6
	panel.add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 2)
	panel.add_child(vbox)

	# Year / icon
	var yr = entry.get("contactYr", null)
	var yr_text: String
	if yr == null:
		yr_text = "present"
	elif yr < 0:
		yr_text = "%d BP" % absi(yr)
	else:
		yr_text = "%d AP" % yr

	var icon: String = _status_icon(entry.get("status", ""))
	var year_lbl := Label.new()
	year_lbl.text = "%s %s" % [icon, yr_text]
	_style_label(year_lbl, 9, e_color)
	vbox.add_child(year_lbl)

	var label_lbl := Label.new()
	label_lbl.text = entry.get("label", "")
	_style_label(label_lbl, 7, C_TEXT_SEC)
	label_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD
	vbox.add_child(label_lbl)

	detail_vbox.add_child(panel)


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

func _faction_color(faction: String) -> Color:
	match faction:
		"reach": return C_REACH
		"lattice": return C_LATTICE
		"contact": return C_CONTACT
		"era": return C_GOLD
		"unknown": return C_UNKNOWN
		"uncontacted": return C_TEXT_MUTE
		_: return C_TEXT_SEC


func _status_icon(status: String) -> String:
	match status:
		"core": return "★"
		"colony": return "■"
		"absorbed": return "▣"
		"garrison": return "▲"
		"trade", "tributary", "client": return "◆"
		"unknown", "uncontacted": return "•"
		"contact": return "⚠"
		_: return "●"


## Build a small debug overlay in the bottom-right corner of the viewport.
## Shows FPS and active tile count. Updated each frame via update_debug().
func _build_debug_overlay() -> void:
	_debug_label = Label.new()
	_debug_label.name = "DebugOverlay"
	# Anchor to bottom-right corner
	_debug_label.anchor_left = 1.0
	_debug_label.anchor_right = 1.0
	_debug_label.anchor_top = 1.0
	_debug_label.anchor_bottom = 1.0
	_debug_label.offset_left = -200
	_debug_label.offset_right = -8
	_debug_label.offset_top = -44
	_debug_label.offset_bottom = -8
	_debug_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_debug_label.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	_debug_label.text = "FPS: — | tiles: —"
	_style_label(_debug_label, 9, C_TEXT_MUTE)
	# Semi-transparent background effect: just use a darker text color, no panel needed
	add_child(_debug_label)


## Called from main._process() to update FPS and tile count each frame.
func update_debug(fps: int, tile_count: int) -> void:
	if _debug_label:
		_debug_label.text = "FPS: %d | tiles: %d" % [fps, tile_count]


func _style_label(lbl: Label, size: int, color: Color) -> void:
	lbl.add_theme_font_size_override("font_size", size * 4)
	lbl.add_theme_color_override("font_color", color)


func _add_section_header(parent: VBoxContainer, text: String) -> void:
	var lbl := Label.new()
	lbl.text = text
	_style_label(lbl, 10, C_GOLD)
	parent.add_child(lbl)


func _add_detail_section_header(text: String) -> void:
	var lbl := Label.new()
	lbl.text = text
	_style_label(lbl, 7, C_GOLD)
	detail_vbox.add_child(lbl)


func _add_detail_separator() -> void:
	var sep := HSeparator.new()
	var style := StyleBoxLine.new()
	style.color = C_BORDER
	style.thickness = 1
	sep.add_theme_stylebox_override("separator", style)
	detail_vbox.add_child(sep)


func _make_detail_grid() -> GridContainer:
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 2)
	return grid


func _grid_item(grid: GridContainer, key: String, value: String) -> void:
	var k := Label.new()
	k.text = key
	_style_label(k, 8, C_TEXT_MUTE)
	grid.add_child(k)
	var v := Label.new()
	v.text = value
	_style_label(v, 8, C_TEXT_SEC)
	grid.add_child(v)


func _set_panel_style(panel: PanelContainer, bg: Color, border: Color,
		border_right: bool, border_bottom: bool) -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	if border_right:
		style.border_width_right = 1
	if border_bottom:
		style.border_width_bottom = 1
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 10
	style.content_margin_bottom = 8
	panel.add_theme_stylebox_override("panel", style)


## Prevent all mouse events over a panel from reaching the 3D camera.
func _block_input(panel: PanelContainer) -> void:
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	panel.gui_input.connect(func(event: InputEvent) -> void:
		if event is InputEventMouseButton:
			panel.get_viewport().set_input_as_handled()
		elif event is InputEventMouseMotion:
			panel.get_viewport().set_input_as_handled()
	)
