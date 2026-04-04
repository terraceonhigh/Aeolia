## Settlement detection — finds capital cities and port towns
## from arch geometry and political history.
## Pure data. No rendering.
class_name SettlementDetector
extends RefCounted


## Detect settlements for all archipelagos.
## archs: Array of arch dicts {cx, cy, cz, peaks: [{px,py,pz,h,w,...}], shelf_r}
## history_states: Array of state dicts {faction, ...} from HistoryEngine
## Returns Array of settlement dicts.
static func detect_settlements(archs: Array, history_states: Array) -> Array:
	var settlements: Array = []

	for a in archs.size():
		var ar: Dictionary = archs[a]
		if ar.peaks.size() < 1:
			continue
		var used_peaks: Dictionary = {}  # Set<int>

		# -- Capital: best peak-pair harbor --
		if ar.peaks.size() >= 2:
			var best_score := -1.0
			var best_i := -1
			var best_j := -1

			for i in ar.peaks.size():
				for j in range(i + 1, ar.peaks.size()):
					var pi: Dictionary = ar.peaks[i]
					var pj: Dictionary = ar.peaks[j]
					var dot: float = pi.px * pj.px + pi.py * pj.py + pi.pz * pj.pz
					var ang_dist: float = sqrt(maxf(0.0, 2.0 * (1.0 - dot)))
					var avg_w: float = (pi.w + pj.w) / 2.0
					var sep_ratio: float = ang_dist / avg_w
					if sep_ratio < 1.0 or sep_ratio > 7.0:
						continue
					var height_score: float = (pi.h + pj.h) / (2.0 * Constants.ISLAND_MAX_HEIGHT)
					var sep_score: float = maxf(0.0, 1.0 - absf(sep_ratio - 2.8) / 4.2)
					var score: float = height_score * sep_score
					if score > best_score:
						best_score = score
						best_i = i
						best_j = j

			if best_i >= 0:
				var main_pk: Dictionary
				var secondary_pk: Dictionary
				if ar.peaks[best_i].h >= ar.peaks[best_j].h:
					main_pk = ar.peaks[best_i]
					secondary_pk = ar.peaks[best_j]
				else:
					main_pk = ar.peaks[best_j]
					secondary_pk = ar.peaks[best_i]
				used_peaks[best_i] = true
				used_peaks[best_j] = true

				# Harbor point between main and secondary peaks
				var hx: float = main_pk.px * 0.6 + secondary_pk.px * 0.4
				var hy: float = main_pk.py * 0.6 + secondary_pk.py * 0.4
				var hz: float = main_pk.pz * 0.6 + secondary_pk.pz * 0.4
				var hl: float = sqrt(hx * hx + hy * hy + hz * hz)
				hx /= hl; hy /= hl; hz /= hl

				# Compute harbor mouth direction
				var ppx: float = secondary_pk.px - main_pk.px
				var ppy: float = secondary_pk.py - main_pk.py
				var ppz: float = secondary_pk.pz - main_pk.pz
				var mx: float = hy * ppz - hz * ppy
				var my: float = hz * ppx - hx * ppz
				var mz: float = hx * ppy - hy * ppx
				var ml: float = sqrt(mx * mx + my * my + mz * mz)
				if ml == 0.0:
					ml = 1.0
				mx /= ml; my /= ml; mz /= ml
				# Point mouth outward from arch center
				if mx * ar.cx + my * ar.cy + mz * ar.cz > mx * hx + my * hy + mz * hz:
					mx = -mx; my = -my; mz = -mz

				# Incline directions for building placement
				var upx: float = main_pk.px - hx
				var upy: float = main_pk.py - hy
				var upz: float = main_pk.pz - hz
				var ul: float = sqrt(upx * upx + upy * upy + upz * upz)
				if ul == 0.0:
					ul = 1.0
				upx /= ul; upy /= ul; upz /= ul
				var inclines: Array = [
					_normalize_dir(upx, upy, upz),
					_normalize_dir(upx * 0.85 + mx * 0.53, upy * 0.85 + my * 0.53, upz * 0.85 + mz * 0.53),
					_normalize_dir(upx * 0.85 - mx * 0.53, upy * 0.85 - my * 0.53, upz * 0.85 - mz * 0.53),
				]

				var faction: String = "other"
				if a < history_states.size():
					var f: String = history_states[a].faction
					if f == "reach" or f == "lattice":
						faction = f

				settlements.append({
					"arch_idx": a, "cx": hx, "cy": hy, "cz": hz,
					"mx": mx, "my": my, "mz": mz,
					"main_peak": main_pk, "secondary_peak": secondary_pk,
					"radius": main_pk.w * 1.8, "inclines": inclines,
					"importance": 1.0, "kind": "capital",
					"faction": faction,
				})

		# -- Secondary port towns: every remaining prominent peak --
		for i in ar.peaks.size():
			if used_peaks.has(i):
				continue
			var pk: Dictionary = ar.peaks[i]
			if pk.h < Constants.ISLAND_MAX_HEIGHT * 0.18:
				continue
			# Place on seaward flank (away from arch center)
			var dx: float = pk.px - ar.cx
			var dy: float = pk.py - ar.cy
			var dz: float = pk.pz - ar.cz
			var dl: float = sqrt(dx * dx + dy * dy + dz * dz)
			if dl == 0.0:
				dl = 1.0
			dx /= dl; dy /= dl; dz /= dl
			var sx: float = pk.px + dx * pk.w * 0.3
			var sy: float = pk.py + dy * pk.w * 0.3
			var sz: float = pk.pz + dz * pk.w * 0.3
			var sl: float = sqrt(sx * sx + sy * sy + sz * sz)
			sx /= sl; sy /= sl; sz /= sl

			var imp: float = 0.25 + 0.45 * (pk.h / Constants.ISLAND_MAX_HEIGHT)

			var faction: String = "other"
			if a < history_states.size():
				var f: String = history_states[a].faction
				if f == "reach" or f == "lattice":
					faction = f

			settlements.append({
				"arch_idx": a, "cx": sx, "cy": sy, "cz": sz,
				"mx": dx, "my": dy, "mz": dz,
				"main_peak": pk, "secondary_peak": {},
				"radius": pk.w * 1.2, "inclines": [],
				"importance": imp, "kind": "port",
				"faction": faction,
			})

	# Normalize importance: capitals near 1.0, ports scale below
	var max_imp := 0.001
	for s in settlements:
		if s.importance > max_imp:
			max_imp = s.importance
	for s in settlements:
		if s.kind == "capital":
			s.importance = maxf(0.7, s.importance / max_imp)
		else:
			s.importance = minf(0.6, s.importance / max_imp)

	return settlements


## Normalize a direction vector and return as dict.
static func _normalize_dir(dx: float, dy: float, dz: float) -> Dictionary:
	var il: float = sqrt(dx * dx + dy * dy + dz * dz)
	if il == 0.0:
		il = 1.0
	return { "dx": dx / il, "dy": dy / il, "dz": dz / il }
