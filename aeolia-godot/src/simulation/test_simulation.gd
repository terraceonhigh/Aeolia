## Test script for the Aeolia simulation layer.
## Generates a world from seed 42 and prints key outputs for validation
## against the JavaScript monolith.
##
## Attach to any Node and run the scene, or run via:
##   godot --headless --script res://src/simulation/test_simulation.gd
extends SceneTree


func _init() -> void:
	print("=" .repeat(60))
	print("  AEOLIA SIMULATION TEST — Seed 42")
	print("=" .repeat(60))
	print("")

	# ── Test 1: RNG determinism ──
	print("── RNG (10 calls from seed 42) ──")
	var rng := RNG.new(42)
	for i in 10:
		print("  rng[%d] = %.10f" % [i, rng.next_float()])
	print("")

	# ── Test 2: Full world generation ──
	print("── Generating world... ──")
	var t0 := Time.get_ticks_msec()
	var world: Dictionary = WorldGenerator.build_world(42)
	var elapsed := Time.get_ticks_msec() - t0
	print("  Generated in %d ms" % elapsed)
	print("")

	# ── Test 3: Archipelago positions ──
	print("── Archipelagos (%d) ──" % world.archs.size())
	print("  Reach: arch #%d" % world.reach_arch)
	print("  Lattice: arch #%d" % world.lattice_arch)
	print("")
	for i in mini(5, world.archs.size()):
		var a: Dictionary = world.archs[i]
		print("  [%02d] pos=(%.4f, %.4f, %.4f) peaks=%d shelf_r=%.4f" % [
			i, a.cx, a.cy, a.cz, a.peaks.size(), a.shelf_r])
	print("  ... (%d more)" % (world.archs.size() - 5))
	print("")

	# ── Test 4: Edge network ──
	print("── Plateau edges: %d ──" % world.plateau_edges.size())
	for i in mini(5, world.plateau_edges.size()):
		var e: Array = world.plateau_edges[i]
		print("  [%d] %d <-> %d" % [i, e[0], e[1]])
	print("")

	# ── Test 5: Substrate cascade ──
	print("── Substrate (first 5 archs) ──")
	for i in mini(5, world.substrate.size()):
		var sub: Dictionary = world.substrate[i]
		var cli: Dictionary = sub.climate
		var crops: Dictionary = sub.crops
		var prod: Dictionary = sub.production
		var pol: Dictionary = sub.political_culture
		print("  [%02d] %s | %.0fmm rain | %.1f°C | crop=%s | %s | %s (s=%.2f l=%.2f)" % [
			i, cli.climate_zone, cli.effective_rainfall, cli.mean_temp,
			crops.primary_crop, pol.label, prod.mode_label,
			prod.surplus, prod.labor])
	print("")

	# ── Test 6: History ──
	var hist: Dictionary = world.history
	print("── History ──")
	print("  Dark Forest break: year %s at arch %s" % [
		str(hist.df_year) if hist.df_year != null else "?",
		str(hist.df_arch) if hist.df_arch != null else "?"])
	print("  States: %d" % hist.states.size())
	print("")

	# Show Reach and Lattice
	if world.reach_arch < hist.states.size():
		var rs: Dictionary = hist.states[world.reach_arch]
		print("  REACH: %s | pop=%d | tech=%.1f | status=%s" % [
			rs.name, rs.population, rs.tech, rs.status])
	if world.lattice_arch < hist.states.size():
		var ls: Dictionary = hist.states[world.lattice_arch]
		print("  LATTICE: %s | pop=%d | tech=%.1f | status=%s" % [
			ls.name, ls.population, ls.tech, ls.status])
	print("")

	# Faction summary
	var reach_count := 0
	var lattice_count := 0
	var unknown_count := 0
	for s in hist.states:
		match s.faction:
			"reach": reach_count += 1
			"lattice": lattice_count += 1
			"unknown": unknown_count += 1
	print("  Reach territories: %d | Lattice territories: %d | Uncontacted: %d" % [
		reach_count, lattice_count, unknown_count])
	print("")

	# ── Test 7: Log entries ──
	print("── Political log (%d entries) ──" % hist.log.size())
	for i in mini(10, hist.log.size()):
		var entry: Dictionary = hist.log[i]
		print("  %s — %s" % [entry.name, entry.label])
	if hist.log.size() > 10:
		print("  ... (%d more entries)" % (hist.log.size() - 10))
	print("")

	# ── Test 8: Settlements ──
	print("── Settlements: %d total ──" % world.settlements.size())
	var capitals := 0
	var ports := 0
	for s in world.settlements:
		if s.kind == "capital":
			capitals += 1
		else:
			ports += 1
	print("  Capitals: %d | Ports: %d" % [capitals, ports])
	print("")

	# Show a few settlements
	for i in mini(5, world.settlements.size()):
		var s: Dictionary = world.settlements[i]
		print("  [%02d] %s at arch #%d | faction=%s | importance=%.2f" % [
			i, s.kind, s.arch_idx, s.faction, s.importance])
	print("")

	print("=" .repeat(60))
	print("  TEST COMPLETE")
	print("=" .repeat(60))

	quit()
