## World generation from seed.
## Produces the physical geography: archipelagos, plateau edges,
## Reach/Lattice selection, then orchestrates substrate, history,
## and settlement layers.
##
## Pure function: seed -> WorldState. No rendering dependency.
##
## Usage:
##   var world = WorldGenerator.build_world(42)
##   print(world.archs.size())  # 42
class_name WorldGenerator
extends RefCounted


## Convert latitude/longitude to unit-sphere XYZ.
static func _lat_lon_to_xyz(lat: float, lon: float) -> Vector3:
	var p: float = deg_to_rad(90.0 - lat)
	var t: float = deg_to_rad(lon + 180.0)
	return Vector3(sin(p) * cos(t), cos(p), sin(p) * sin(t))


## Generate a complete world from a seed number.
## Returns a Dictionary with keys:
##   archs, edges, plateau_edges, substrate, history, settlements,
##   reach_arch, lattice_arch, seed
static func build_world(p_seed: int) -> Dictionary:
	var s: int = p_seed if p_seed != 0 else 42
	var rng := RNG.new(s)

	# ── Generate archipelagos via Fibonacci spiral + jitter ──
	var golden_angle: float = PI * (3.0 - sqrt(5.0))
	var arch_specs: Array = []

	for k in Constants.ARCH_COUNT:
		var y_val: float = 1.0 - (2.0 * (k + 0.5)) / Constants.ARCH_COUNT
		var radius: float = sqrt(1.0 - y_val * y_val)
		var theta: float = golden_angle * k
		var base_lat: float = rad_to_deg(asin(y_val))
		var base_lon: float = fmod(rad_to_deg(theta), 360.0) - 180.0
		var j_lat: float = clampf(base_lat + (rng.next_float() - 0.5) * 24.0, -75.0, 75.0)
		var j_lon: float = base_lon + (rng.next_float() - 0.5) * 24.0

		var size_roll: float = rng.next_float()
		var arch_size: float
		if size_roll < 0.15:
			arch_size = 1.3 + rng.next_float() * 0.9
		elif size_roll < 0.40:
			arch_size = 0.7 + rng.next_float() * 0.6
		else:
			arch_size = 0.25 + rng.next_float() * 0.45

		var n: int = maxi(3, roundi(arch_size * (5.0 + rng.next_float() * 8.0)))
		arch_specs.append({ "lat": j_lat, "lon": j_lon, "size": arch_size, "n": n })

	# ── Build arch objects with peaks ──
	var archs: Array = []
	for spec in arch_specs:
		var pos: Vector3 = _lat_lon_to_xyz(spec.lat, spec.lon)
		var cx: float = pos.x
		var cy: float = pos.y
		var cz: float = pos.z

		# Tangent frame
		var rx: float = -cz
		var ry: float = 0.0
		var rz: float = cx
		var rl: float = sqrt(rx * rx + rz * rz)
		if rl == 0.0:
			rl = 1.0
		rx /= rl; rz /= rl
		var fx: float = cy * rz
		var fy: float = cz * rx - cx * rz
		var fz: float = -cy * rx

		var peaks: Array = []
		for i in spec.n:
			var ang: float = rng.next_float() * TAU
			var dist: float = (0.2 + rng.next_float() * 0.8) * spec.size * 0.12
			var ca: float = cos(ang)
			var sa: float = sin(ang)
			var px: float = cx + dist * (ca * rx + sa * fx)
			var py: float = cy + dist * (ca * ry + sa * fy)
			var pz: float = cz + dist * (ca * rz + sa * fz)
			var pl: float = sqrt(px * px + py * py + pz * pz)
			px /= pl; py /= pl; pz /= pl
			var w: float = 0.010 + rng.next_float() * 0.020 * spec.size
			var raw_h: float = Constants.ISLAND_MAX_HEIGHT * (0.4 + rng.next_float() * 0.6) * (spec.size / 1.3)
			var h: float = minf(Constants.ISLAND_MAX_HEIGHT, raw_h)
			peaks.append({
				"px": px, "py": py, "pz": pz,
				"h": h, "w": w, "w2inv": 3.0 / (w * w),
			})

		archs.append({
			"cx": cx, "cy": cy, "cz": cz,
			"peaks": peaks,
			"shelf_r": spec.size * 0.18,
		})

	# ── Find most-antipodal pair → Reach (north) & Lattice (south) ──
	var reach_arch := 0
	var lattice_arch := 1
	var best_dot := 2.0
	for i in archs.size():
		for j in range(i + 1, archs.size()):
			var d: float = archs[i].cx * archs[j].cx + archs[i].cy * archs[j].cy + archs[i].cz * archs[j].cz
			if d < best_dot:
				best_dot = d
				reach_arch = i
				lattice_arch = j
	# Reach in the north (higher cy)
	if archs[reach_arch].cy < archs[lattice_arch].cy:
		var tmp: int = reach_arch
		reach_arch = lattice_arch
		lattice_arch = tmp

	# ── Override core archs with bible-mandated geographies ──
	_regen_peaks(archs[reach_arch], RNG.new(s * 7 + 1), 1.8, 24, 0.010, 0.020, 1.2)
	_regen_peaks(archs[lattice_arch], RNG.new(s * 13 + 2), 0.8, 35, 0.009, 0.014, 1.0)

	# ── Generate plateau edge network from proximity ──
	var pair_dists: Array = []
	for i in archs.size():
		for j in range(i + 1, archs.size()):
			var d: float = archs[i].cx * archs[j].cx + archs[i].cy * archs[j].cy + archs[i].cz * archs[j].cz
			var angle: float = acos(clampf(d, -1.0, 1.0))
			pair_dists.append({ "i": i, "j": j, "angle": angle })
	pair_dists.sort_custom(func(a, b): return a.angle < b.angle)

	var edge_keys: Dictionary = {}  # "i-j" -> true (acts as Set)
	var conn_count: Array = []
	conn_count.resize(archs.size())
	conn_count.fill(0)
	var plateau_edges: Array = []

	# Ensure minimum neighbors
	for pd in pair_dists:
		if conn_count[pd.i] < Constants.MIN_NEIGHBORS or conn_count[pd.j] < Constants.MIN_NEIGHBORS:
			_add_edge(pd.i, pd.j, edge_keys, plateau_edges, conn_count)
	# Add all short-range edges
	for pd in pair_dists:
		if pd.angle < Constants.MAX_EDGE_ANGLE:
			_add_edge(pd.i, pd.j, edge_keys, plateau_edges, conn_count)

	# ── Edge geometry (for terrain rendering) ──
	var edges: Array = []
	for pe in plateau_edges:
		var ai: int = pe[0]
		var bi: int = pe[1]
		var a: Dictionary = archs[ai]
		var b: Dictionary = archs[bi]
		# Normal to great-circle plane
		var nx: float = a.cy * b.cz - a.cz * b.cy
		var ny: float = a.cz * b.cx - a.cx * b.cz
		var nz: float = a.cx * b.cy - a.cy * b.cx
		var nl: float = sqrt(nx * nx + ny * ny + nz * nz)
		if nl == 0.0:
			nl = 1.0
		nx /= nl; ny /= nl; nz /= nl
		var edge_rng := RNG.new(ai * 1000 + bi)
		var w: float = 0.14 + edge_rng.next_float() * 0.12
		edges.append({
			"ax": a.cx, "ay": a.cy, "az": a.cz,
			"bx": b.cx, "by": b.cy, "bz": b.cz,
			"nx": nx, "ny": ny, "nz": nz,
			"dot_ab": a.cx * b.cx + a.cy * b.cy + a.cz * b.cz,
			"w": w,
		})

	# ── Compute all layers ──
	var substrate: Array = Substrate.compute_substrate(archs, plateau_edges, s)
	var history: Dictionary = HistoryEngine.assign_politics(archs, plateau_edges, s, reach_arch, lattice_arch)
	var settlements: Array = SettlementDetector.detect_settlements(archs, history.states)

	return {
		"archs": archs,
		"edges": edges,
		"plateau_edges": plateau_edges,
		"substrate": substrate,
		"history": history,
		"settlements": settlements,
		"reach_arch": reach_arch,
		"lattice_arch": lattice_arch,
		"seed": s,
	}


## Regenerate peaks for a core arch (Reach or Lattice) with specific parameters.
static func _regen_peaks(arch: Dictionary, prng: RNG, arch_size: float, n: int,
		w_min: float, w_range: float, h_mul: float) -> void:
	var cx: float = arch.cx
	var cy: float = arch.cy
	var cz: float = arch.cz
	var rx: float = -cz
	var ry: float = 0.0
	var rz: float = cx
	var rl: float = sqrt(rx * rx + rz * rz)
	if rl == 0.0:
		rl = 1.0
	rx /= rl; rz /= rl
	var fx: float = cy * rz
	var fy: float = cz * rx - cx * rz
	var fz: float = -cy * rx

	var peaks: Array = []
	for i in n:
		var ang: float = prng.next_float() * TAU
		var dist: float = (0.2 + prng.next_float() * 0.8) * arch_size * 0.12
		var ca: float = cos(ang)
		var sa: float = sin(ang)
		var px: float = cx + dist * (ca * rx + sa * fx)
		var py: float = cy + dist * (ca * ry + sa * fy)
		var pz: float = cz + dist * (ca * rz + sa * fz)
		var pl: float = sqrt(px * px + py * py + pz * pz)
		px /= pl; py /= pl; pz /= pl
		var w: float = w_min + prng.next_float() * w_range * arch_size
		var raw_h: float = Constants.ISLAND_MAX_HEIGHT * (0.4 + prng.next_float() * 0.6) * h_mul
		var h: float = minf(Constants.ISLAND_MAX_HEIGHT, raw_h)
		peaks.append({
			"px": px, "py": py, "pz": pz,
			"h": h, "w": w, "w2inv": 3.0 / (w * w),
		})
	arch.peaks = peaks
	arch.shelf_r = arch_size * 0.18


## Add an edge if not already present.
static func _add_edge(i: int, j: int, edge_keys: Dictionary,
		plateau_edges: Array, conn_count: Array) -> void:
	var key: String = str(mini(i, j)) + "-" + str(maxi(i, j))
	if edge_keys.has(key):
		return
	edge_keys[key] = true
	plateau_edges.append([i, j])
	conn_count[i] += 1
	conn_count[j] += 1
