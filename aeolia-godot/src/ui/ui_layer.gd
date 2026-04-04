## UI layer — sidebar (history log), popup (arch detail), and controls.
class_name UILayer
extends CanvasLayer

signal seed_changed(new_seed: int)
signal sea_level_changed(value: float)
signal sun_dimmer_changed(value: float)

var sidebar: PanelContainer
var popup_panel: PanelContainer
var popup_title: Label
var popup_content: RichTextLabel
var header_label: Label
var seed_spinbox: SpinBox


func setup(world_data: Dictionary) -> void:
	# Clear previous UI
	for child in get_children():
		child.queue_free()
	_setup_header()
	_setup_sidebar(world_data)
	_setup_popup()
	_setup_controls()


func _setup_header() -> void:
	var h := Label.new()
	h.text = "AEOLIA"
	h.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	h.anchor_left = 0.3
	h.anchor_right = 0.7
	h.offset_top = 12
	h.offset_bottom = 60
	h.add_theme_font_size_override("font_size", 36)
	h.add_theme_color_override("font_color", Color(0.75, 0.78, 0.85, 0.7))
	add_child(h)
	header_label = h


func _setup_sidebar(world_data: Dictionary) -> void:
	var panel := PanelContainer.new()
	panel.anchor_left = 0.0
	panel.anchor_top = 0.0
	panel.anchor_right = 0.0
	panel.anchor_bottom = 1.0
	panel.offset_right = 320
	add_child(panel)

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.06, 0.06, 0.10, 0.85)
	panel.add_theme_stylebox_override("panel", style)

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(320, 0)
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(scroll)

	var vbox := VBoxContainer.new()
	vbox.custom_minimum_size = Vector2(300, 0)
	scroll.add_child(vbox)

	# Sidebar header
	var sh := Label.new()
	sh.text = "AEOLIA — Political History"
	sh.add_theme_font_size_override("font_size", 14)
	sh.add_theme_color_override("font_color", Color(0.7, 0.72, 0.8))
	vbox.add_child(sh)

	# Add separator
	var sep := HSeparator.new()
	vbox.add_child(sep)

	# History log entries
	if world_data.has("history") and world_data.history.has("log"):
		for entry in world_data.history.log:
			var rtl := RichTextLabel.new()
			rtl.fit_content = true
			rtl.scroll_active = false
			rtl.bbcode_enabled = true
			rtl.custom_minimum_size = Vector2(290, 0)
			rtl.add_theme_font_size_override("normal_font_size", 12)

			var color_hex := "#888888"
			var faction: String = entry.get("faction", "")
			if faction == "reach":
				color_hex = "#cc5540"
			elif faction == "lattice":
				color_hex = "#4488cc"
			elif faction == "contact":
				color_hex = "#cccc44"
			elif faction == "era":
				color_hex = "#999999"

			rtl.text = "[color=%s][b]%s[/b][/color]\n%s" % [
				color_hex, entry.get("name", ""), entry.get("label", "")]
			vbox.add_child(rtl)

	sidebar = panel


func _setup_popup() -> void:
	var panel := PanelContainer.new()
	panel.anchor_left = 1.0
	panel.anchor_right = 1.0
	panel.anchor_top = 0.1
	panel.anchor_bottom = 0.9
	panel.offset_left = -370
	panel.offset_right = -20
	panel.visible = false
	add_child(panel)

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.08, 0.08, 0.12, 0.92)
	style.corner_radius_top_left = 8
	style.corner_radius_top_right = 8
	style.corner_radius_bottom_left = 8
	style.corner_radius_bottom_right = 8
	panel.add_theme_stylebox_override("panel", style)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 4)
	panel.add_child(vbox)

	# Close button row
	var close_row := HBoxContainer.new()
	vbox.add_child(close_row)
	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	close_row.add_child(spacer)
	var close_btn := Button.new()
	close_btn.text = "X"
	close_btn.custom_minimum_size = Vector2(30, 30)
	close_btn.pressed.connect(func(): panel.visible = false)
	close_row.add_child(close_btn)

	# Title
	var title := Label.new()
	title.add_theme_font_size_override("font_size", 22)
	title.add_theme_color_override("font_color", Color(0.9, 0.88, 0.82))
	vbox.add_child(title)
	popup_title = title

	# Content
	var content := RichTextLabel.new()
	content.fit_content = true
	content.scroll_active = true
	content.bbcode_enabled = true
	content.custom_minimum_size = Vector2(320, 300)
	content.add_theme_font_size_override("normal_font_size", 13)
	vbox.add_child(content)
	popup_content = content

	popup_panel = panel


func _setup_controls() -> void:
	var panel := PanelContainer.new()
	panel.anchor_left = 0.5
	panel.anchor_right = 0.5
	panel.anchor_top = 1.0
	panel.anchor_bottom = 1.0
	panel.offset_left = -400
	panel.offset_right = 400
	panel.offset_top = -55
	panel.offset_bottom = -10
	add_child(panel)

	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.10, 0.10, 0.15, 0.8)
	style.corner_radius_top_left = 6
	style.corner_radius_top_right = 6
	style.corner_radius_bottom_left = 6
	style.corner_radius_bottom_right = 6
	panel.add_theme_stylebox_override("panel", style)

	var hbox := HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 12)
	hbox.alignment = BoxContainer.ALIGNMENT_CENTER
	panel.add_child(hbox)

	# Seed
	var seed_lbl := Label.new()
	seed_lbl.text = "Seed:"
	hbox.add_child(seed_lbl)

	var spinbox := SpinBox.new()
	spinbox.min_value = 1
	spinbox.max_value = 99999
	spinbox.value = 42
	spinbox.custom_minimum_size = Vector2(100, 0)
	hbox.add_child(spinbox)
	seed_spinbox = spinbox

	var gen_btn := Button.new()
	gen_btn.text = "Generate"
	gen_btn.custom_minimum_size = Vector2(100, 0)
	gen_btn.pressed.connect(func(): seed_changed.emit(int(spinbox.value)))
	hbox.add_child(gen_btn)

	# Separator
	hbox.add_child(VSeparator.new())

	# Sea level
	var sea_lbl := Label.new()
	sea_lbl.text = "Sea Level"
	hbox.add_child(sea_lbl)

	var slider := HSlider.new()
	slider.min_value = -500
	slider.max_value = 500
	slider.value = 0
	slider.custom_minimum_size = Vector2(120, 0)
	slider.value_changed.connect(func(val: float): sea_level_changed.emit(val))
	hbox.add_child(slider)

	# Separator
	hbox.add_child(VSeparator.new())

	# Sun dimmer
	var sun_icon := Label.new()
	sun_icon.text = "Sun"
	sun_icon.add_theme_color_override("font_color", Color(1.0, 0.9, 0.6))
	hbox.add_child(sun_icon)

	var sun_slider := HSlider.new()
	sun_slider.min_value = 0.0
	sun_slider.max_value = 3.0
	sun_slider.step = 0.05
	sun_slider.value = 1.2
	sun_slider.custom_minimum_size = Vector2(100, 0)
	sun_slider.value_changed.connect(func(val: float): sun_dimmer_changed.emit(val))
	hbox.add_child(sun_slider)


## Show the detail popup for an archipelago.
## Pulls data from world_data.history.states[idx] and world_data.substrate[idx].
func show_arch(idx: int, world_data: Dictionary) -> void:
	if not popup_panel or not popup_title or not popup_content:
		return

	var states: Array = world_data.get("history", {}).get("states", [])
	if idx < 0 or idx >= states.size():
		return

	var state: Dictionary = states[idx]
	popup_title.text = state.get("name", "Archipelago %d" % idx)

	var txt := ""

	# Faction & status
	var faction: String = state.get("faction", "unknown")
	var faction_color := "#aaaaaa"
	if faction == "reach":
		faction_color = "#cc5540"
	elif faction == "lattice":
		faction_color = "#4488cc"

	txt += "[color=%s][b]%s[/b][/color]  |  %s\n" % [
		faction_color, faction.capitalize(), state.get("status", "unknown")]
	txt += "[b]Population:[/b] %s  |  [b]Tech:[/b] %s\n" % [
		str(state.get("population", "?")), str(state.get("tech", "?"))]

	var era: String = str(state.get("eraOfContact", "none"))
	txt += "[b]Era of Contact:[/b] %s  |  [b]Hops:[/b] %s\n" % [
		era, str(state.get("hopCount", "?"))]
	txt += "\n"

	# Substrate data (separate array in world_data)
	var substrates: Array = world_data.get("substrate", [])
	if idx < substrates.size():
		var sub: Dictionary = substrates[idx]

		# Climate
		if sub.has("climate"):
			var cli: Dictionary = sub.climate
			txt += "[b]Climate:[/b] %s\n" % cli.get("climate_zone", "?")
			txt += "  Temp: %.1f°C  |  Rain: %.0f mm  |  Wind: %s\n" % [
				cli.get("mean_temp", 0.0), cli.get("effective_rainfall", 0.0),
				cli.get("wind_belt", "?")]

		# Crops
		if sub.has("crops"):
			var crops: Dictionary = sub.crops
			txt += "[b]Primary Crop:[/b] %s" % crops.get("primary_crop", "none")
			var sec: String = str(crops.get("secondary_crop", ""))
			if sec != "" and sec != "null":
				txt += "  (secondary: %s)" % sec
			txt += "\n"

		# Trade goods
		if sub.has("trade_goods"):
			var tg: Dictionary = sub.trade_goods
			var goods: Array[String] = []
			if tg.has("stimulant") and tg.stimulant.get("type", "") != "":
				goods.append(tg.stimulant.type)
			if tg.has("fiber") and tg.fiber.get("type", "") != "":
				goods.append(tg.fiber.type)
			if tg.has("protein") and tg.protein.get("type", "") != "":
				goods.append(tg.protein.type)
			txt += "[b]Trade Goods:[/b] %s\n" % (", ".join(goods) if goods.size() > 0 else "none")

		# Political culture
		if sub.has("political_culture"):
			var pc: Dictionary = sub.political_culture
			txt += "[b]Political Culture:[/b] %s (awareness=%.2f, participation=%.2f)\n" % [
				pc.get("label", "?"), pc.get("awareness", 0.0), pc.get("participation", 0.0)]

		# Mode of production
		if sub.has("production"):
			var prod: Dictionary = sub.production
			txt += "[b]Production:[/b] %s (surplus=%.2f, labor=%.2f)\n" % [
				prod.get("mode_label", "?"), prod.get("surplus", 0.0), prod.get("labor", 0.0)]

		# Minerals
		if sub.has("minerals"):
			var mins: Dictionary = sub.minerals
			var found: Array[String] = []
			for key in mins:
				if mins[key]:
					found.append(key)
			txt += "[b]Minerals:[/b] %s\n" % (", ".join(found) if found.size() > 0 else "none")

	popup_content.text = txt
	popup_panel.visible = true
