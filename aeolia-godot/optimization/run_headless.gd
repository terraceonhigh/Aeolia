## Headless world-state exporter for Aeolia parameter optimization.
##
## Runs WorldGenerator.build_world(seed) from the command line and writes
## the complete world state — geography, substrate, history, and adjacency —
## as JSON to stdout (or a file).  The output is the "base_world" consumed
## by thin_sim.py and loss.py.
##
## Usage (from project root):
##   godot --headless --path . -- --seed 42
##   godot --headless --path . -- --seed 42 --output optimization/worlds/seed_42.json
##   godot --headless --path . -- --seeds 42,137,1000,9999
##
## The --path argument loads the full project so class_name registrations
## (WorldGenerator, HistoryEngine, Substrate, etc.) are active.
##
## Pre-generate worlds for several seeds before running optimize.py:
##   for s in 42 137 1000 9999 12345; do
##     godot --headless --path . -- --seed $s \
##           --output optimization/worlds/seed_$s.json
##   done

extends SceneTree


func _init() -> void:
	var args := OS.get_cmdline_user_args()
	var seeds: Array[int] = []
	var output_dir := ""
	var output_file := ""

	var i := 0
	while i < args.size():
		match args[i]:
			"--seed":
				i += 1
				if i < args.size():
					seeds.append(int(args[i]))
			"--seeds":
				i += 1
				if i < args.size():
					for part in args[i].split(","):
						seeds.append(int(part.strip_edges()))
			"--output":
				i += 1
				if i < args.size():
					output_file = args[i]
			"--output-dir":
				i += 1
				if i < args.size():
					output_dir = args[i]
		i += 1

	if seeds.is_empty():
		seeds.append(42)

	for s in seeds:
		var world := WorldGenerator.build_world(s)
		var payload := _export(world)
		var json_str := JSON.stringify(payload, "\t")

		if not output_dir.is_empty():
			var path := output_dir.path_join("seed_%d.json" % s)
			_write_file(path, json_str)
			print("Wrote %s" % path)
		elif not output_file.is_empty():
			_write_file(output_file, json_str)
			print("Wrote %s" % output_file)
		else:
			print(json_str)

	quit()


## Serialise a full WorldGenerator.build_world() result into a JSON-safe dict.
## Includes everything thin_sim.py needs to re-run the population model:
##   archs      — {lat, size, shelf_r, peak_count, potential} per arch
##   adj        — adjacency lists
##   substrate  — {primary_crop} per arch (from Substrate.compute_substrate)
##   names      — arch names from history
##   states     — final simulation output (for direct loss evaluation)
##   df_year / df_arch / df_detector
##   log        — history log entries (contains mortality strings for fallback epi parsing)
func _export(world: Dictionary) -> Dictionary:
	var archs         : Array = world["archs"]
	var history       : Dictionary = world["history"]
	var substrate_raw : Array = world["substrate"]
	var plateau_edges : Array = world["plateau_edges"]
	var reach_arch    : int = world["reach_arch"]
	var lattice_arch  : int = world["lattice_arch"]
	var seed_val      : int = world["seed"]
	var N             := archs.size()

	# ── Adjacency list ────────────────────────────────────────────────────
	var adj : Array = []
	adj.resize(N)
	for k in N:
		adj[k] = []
	for edge in plateau_edges:
		adj[edge[0]].append(edge[1])
		adj[edge[1]].append(edge[0])

	# ── Potentials (mirrors history_engine.gd Phase 1 exactly) ───────────
	# Same RNG seed formula: (seed * 31 + 1066)
	var rng := RNG.new((seed_val if seed_val != 0 else 42) * 31 + 1066)
	var potentials : Array[float] = []
	for k in N:
		var arch = archs[k]
		var peaks = arch["peaks"]
		var p_count := peaks.size()
		var sz := arch["shelf_r"] / 0.12
		var avg_h := 0.0
		if p_count > 0:
			for pk in peaks:
				avg_h += pk["h"]
			avg_h /= float(p_count) * Constants.ISLAND_MAX_HEIGHT
		var pot := (float(p_count) / 20.0 * 0.4
				  + avg_h * 0.3
				  + sz / 2.2 * 0.3) * (0.6 + rng.next_float() * 0.4)
		potentials.append(pot)

	# ── Arch export (lat, size, shelf_r, peak_count, potential) ──────────
	var arch_out : Array = []
	for k in N:
		var arch = archs[k]
		var cy := clampf(arch["cy"], -1.0, 1.0)
		var lat := rad_to_deg(asin(cy))
		arch_out.append({
			"index":      k,
			"lat":        snappedf(lat, 0.01),
			"size":       snappedf(arch["shelf_r"] / 0.12, 0.001),
			"shelf_r":    arch["shelf_r"],
			"peak_count": arch["peaks"].size(),
			"potential":  snappedf(potentials[k], 0.0001),
		})

	# ── Substrate: only the fields thin_sim.py actually uses ─────────────
	var sub_out : Array = []
	for k in N:
		var s = substrate_raw[k] if k < substrate_raw.size() else {}
		var crops : Dictionary = s.get("crops", {})
		sub_out.append({
			"primary_crop":  crops.get("primary_crop",  "emmer"),
			"primary_yield": crops.get("primary_yield", 0.5),
			"secondary_crop": crops.get("secondary_crop", null),
			"total_trade_value": s.get("trade_goods", {}).get("total_trade_value", 0.0),
		})

	# ── Names from history states ─────────────────────────────────────────
	var hist_states : Array = history["states"]
	var names : Array = []
	for s in hist_states:
		names.append(s.get("name", ""))

	# ── States: pass through as-is ────────────────────────────────────────
	var states_out : Array = []
	for s in hist_states:
		states_out.append({
			"faction":          s.get("faction",          "unknown"),
			"status":           s.get("status",           "uncontacted"),
			"name":             s.get("name",             ""),
			"population":       s.get("population",       0),
			"tech":             s.get("tech",             0.0),
			"sovereignty":      s.get("sovereignty",      1.0),
			"tradeIntegration": s.get("tradeIntegration", 0.0),
			"eraOfContact":     s.get("eraOfContact",     null),
			"hopCount":         s.get("hopCount",         0),
			"urbanization":     s.get("urbanization",     0.0),
		})

	return {
		"seed":          seed_val,
		"n":             N,
		"reach_arch":    reach_arch,
		"lattice_arch":  lattice_arch,
		"archs":         arch_out,
		"plateau_edges": plateau_edges,
		"adj":           adj,
		"substrate":     sub_out,
		"names":         names,
		"states":        states_out,
		"df_year":       history.get("df_year"),
		"df_arch":       history.get("df_arch"),
		"df_detector":   history.get("df_detector"),
		"log":           history.get("log", []),
	}


func _write_file(path: String, content: String) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	if f == null:
		push_error("run_headless.gd: cannot open for writing: %s  (error %s)" % [
			path, FileAccess.get_open_error()
		])
		return
	f.store_string(content)
