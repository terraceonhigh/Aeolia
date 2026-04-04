## Substrate cascade: climate, crops, trade goods, political culture, production, minerals, and narrative.
## Ported from src/engine/substrate_raw.js to GDScript for Godot 4.
##
## This module computes per-arch substrate attributes derived from:
## - Latitude and wind belt
## - Orographic rainfall enhancement
## - Ocean gyre circulation model
## - Crop viability (canGrow predicates) and yield ranking
## - Trade goods assignment from primary crop
## - Political culture (Almond & Verba civic/subject/parochial)
## - Mode of production (Marxian surplus/labor distribution)
## - Forbidden zone enforcement: labor <= surplus + 0.3
## - Mineral distribution (Fe, Cu, Au, Pu)
## - Narrative substrate (gender economy, metaphor, religion)
##
class_name Substrate
extends RefCounted


## Main entry point for substrate computation.
## Args:
##   archs: Array of arch dicts {cx, cy, cz, peaks: Array, shelf_r: float}
##   plateau_edges: Array of [arch_a, arch_b] pairs (directed graph edges)
##   seed: integer random seed
## Returns: Array of substrate dicts, one per arch
static func compute_substrate(archs: Array, plateau_edges: Array, p_seed: int) -> Array:
	var rng = RNG.new((p_seed if p_seed > 0 else 42) * 47 + 2024)
	var n = archs.size()

	# Precompute per-arch edge statistics
	var edge_count = []
	edge_count.resize(n)
	for i in range(n):
		edge_count[i] = 0

	var edge_lengths = []
	edge_lengths.resize(n)
	for i in range(n):
		edge_lengths[i] = []

	for edge in plateau_edges:
		var a = edge[0]
		var b = edge[1]
		edge_count[a] += 1
		edge_count[b] += 1

		var arch_a = archs[a]
		var arch_b = archs[b]
		# Dot product of normalized sphere points
		var dot = arch_a["cx"] * arch_b["cx"] + arch_a["cy"] * arch_b["cy"] + arch_a["cz"] * arch_b["cz"]
		dot = maxf(minf(dot, 1.0), -1.0)
		var angle = acos(dot)
		edge_lengths[a].append(angle)
		edge_lengths[b].append(angle)

	# Max edge length for gender economy scaling
	var all_lens = []
	for lens_list in edge_lengths:
		all_lens.append_array(lens_list)
	var max_edge_len = 0.5
	if all_lens.size() > 0:
		max_edge_len = all_lens.max()

	var substrates = []

	# Process each arch
	for i in range(n):
		var arch = archs[i]

		# Latitude and cardinal properties
		var cy_clamped = maxf(minf(arch["cy"], 1.0), -1.0)
		var lat = asin(cy_clamped) * 180.0 / PI
		var abs_lat = absf(lat)
		var size = arch["shelf_r"] / 0.12

		# Peak statistics
		var peak_count = arch["peaks"].size()
		var avg_h = 0.0
		if peak_count > 0:
			var sum_h = 0.0
			for peak in arch["peaks"]:
				sum_h += peak["h"]
			avg_h = sum_h / (peak_count * Constants.ISLAND_MAX_HEIGHT)

		# Edge statistics
		var avg_edge = 0.5
		if edge_lengths[i].size() > 0:
			var sum_edges = 0.0
			for e in edge_lengths[i]:
				sum_edges += e
			avg_edge = sum_edges / edge_lengths[i].size()

		# ═══════════════════════════════════════════════════════════════════════
		# CLIMATE MODEL
		# ═══════════════════════════════════════════════════════════════════════

		# Wind belt classification by latitude
		var wind_belt = ""
		if abs_lat < 12:
			wind_belt = "doldrums"
		elif abs_lat < 28:
			wind_belt = "trades"
		elif abs_lat < 35:
			wind_belt = "subtropical"
		elif abs_lat < 55:
			wind_belt = "westerlies"
		elif abs_lat < 65:
			wind_belt = "subpolar"
		else:
			wind_belt = "polar"

		# Base rainfall by wind belt
		var base_rain = 0.0
		if wind_belt == "doldrums":
			base_rain = 2800.0
		elif wind_belt == "trades":
			base_rain = 2200.0
		elif wind_belt == "subtropical":
			base_rain = 600.0
		elif wind_belt == "westerlies":
			base_rain = 1400.0
		elif wind_belt == "subpolar":
			base_rain = 1100.0
		else:
			base_rain = 300.0

		# Orographic enhancement from peak height
		var orographic_bonus = 1.0 + avg_h * 1.8

		# Gyre position and ocean warmth
		var gyre_pos = _compute_gyre_position(arch, archs)
		var ocean_warmth = 0.0
		if gyre_pos < 0.3:
			ocean_warmth = 0.8 + gyre_pos
		elif gyre_pos > 0.7:
			ocean_warmth = 0.3 - (gyre_pos - 0.7)
		else:
			ocean_warmth = 0.4 + gyre_pos * 0.2
		ocean_warmth = maxf(minf(ocean_warmth, 1.0), 0.0)

		# Moisture from ocean warmth
		var moisture_bonus = 1.0 + maxf(0.0, ocean_warmth - 0.4) * 0.4

		# Effective rainfall (includes Aeolia atmospheric multiplier 1.4)
		var effective_rainfall = base_rain * orographic_bonus * moisture_bonus * 1.4

		# Temperature model
		var mean_temp = 28.0 - abs_lat * 0.45 + (ocean_warmth - 0.5) * 4.0
		var seasonal_range = abs_lat * 0.15 * 0.7  # maritime moderation

		# Tidal range from shelf size and cluster density
		var nearby_archs = 0
		for other_arch in archs:
			if other_arch != arch:
				var d = arch["cx"] * other_arch["cx"] + arch["cy"] * other_arch["cy"] + arch["cz"] * other_arch["cz"]
				if d > 0.95:
					nearby_archs += 1

		var cluster_density = minf(1.0, float(nearby_archs) / 5.0)
		var abs_lat_rad = abs_lat * PI / 180.0
		var tidal_range = (2.0 + arch["shelf_r"] * 30.0 + cluster_density * 4.0) * (0.8 + absf(sin(abs_lat_rad)) * 0.4)

		# Upwelling and fisheries richness
		var upwelling = 0.0
		if gyre_pos > 0.7:
			upwelling += 0.4
		if abs_lat < 5:
			upwelling += 0.3
		upwelling += edge_count[i] * 0.08

		var fisheries_richness = minf(1.0, upwelling * 0.5 + effective_rainfall * 0.0001 + edge_count[i] * 0.05)

		# Climate zone classification
		var climate_zone = ""
		if mean_temp > 24 and effective_rainfall > 2000:
			climate_zone = "tropical_wet"
		elif mean_temp > 24 and effective_rainfall < 1000:
			climate_zone = "tropical_dry"
		elif mean_temp > 10 and effective_rainfall > 1200:
			climate_zone = "temperate_wet"
		elif mean_temp > 10:
			climate_zone = "temperate_dry"
		elif mean_temp > 2:
			climate_zone = "subpolar"
		else:
			climate_zone = "polar_fringe"

		var climate = {
			"latitude": lat,
			"abs_latitude": abs_lat,
			"wind_belt": wind_belt,
			"mean_temp": mean_temp,
			"seasonal_range": seasonal_range,
			"base_rainfall": base_rain,
			"effective_rainfall": effective_rainfall,
			"tidal_range": tidal_range,
			"ocean_warmth": ocean_warmth,
			"gyre_position": gyre_pos,
			"upwelling": upwelling,
			"fisheries_richness": fisheries_richness,
			"climate_zone": climate_zone
		}

		# ═══════════════════════════════════════════════════════════════════════
		# CROP ASSIGNMENT (§10a canGrow predicates)
		# ═══════════════════════════════════════════════════════════════════════

		var can_grow = {
			"paddi": mean_temp >= 20 and effective_rainfall >= 1200 and tidal_range >= 2.0 and arch["shelf_r"] >= 0.08 and abs_lat <= 28,
			"emmer": mean_temp >= 8 and mean_temp <= 24 and effective_rainfall >= 400 and effective_rainfall <= 2000 and abs_lat >= 20 and abs_lat <= 55,
			"taro": mean_temp >= 21 and seasonal_range <= 4 and effective_rainfall >= 1500 and abs_lat <= 20,
			"nori": mean_temp >= 5 and mean_temp <= 22 and edge_count[i] >= 1 and upwelling >= 0.2,
			"sago": mean_temp >= 24 and effective_rainfall >= 2000 and abs_lat <= 15 and arch["shelf_r"] >= 0.04,
			"papa": mean_temp >= 2 and mean_temp <= 18 and effective_rainfall >= 400 and abs_lat >= 35
		}

		# Compute yield for each growable crop
		var yields = {}
		if can_grow["paddi"]:
			var y = 5.0 * minf(1.0, (mean_temp - 18.0) / 15.0) * minf(1.0, effective_rainfall / 1800.0) * minf(1.0, tidal_range / 5.0)
			yields["paddi"] = y

		if can_grow["emmer"]:
			var y = 2.5 * (1.0 - absf(mean_temp - 16.0) / 20.0) * (1.0 - absf(effective_rainfall - 700.0) / 1500.0)
			yields["emmer"] = y

		if can_grow["taro"]:
			var y = 3.0 * minf(1.0, (mean_temp - 20.0) / 8.0) * minf(1.0, effective_rainfall / 2000.0)
			yields["taro"] = y

		if can_grow["nori"]:
			var y = 1.5 * minf(1.0, upwelling * 2.0) * minf(1.0, float(edge_count[i]) / 3.0) * 2.0
			yields["nori"] = y

		if can_grow["sago"]:
			var y = 4.0 * minf(1.0, effective_rainfall / 2500.0) * minf(1.0, arch["shelf_r"] / 0.10)
			yields["sago"] = y

		if can_grow["papa"]:
			var y = 3.5 * (1.0 - absf(mean_temp - 12.0) / 15.0) * minf(1.0, effective_rainfall / 600.0)
			yields["papa"] = y

		# Sort crops by yield (descending)
		var crop_entries = []
		for crop_name in yields.keys():
			crop_entries.append([crop_name, yields[crop_name]])
		crop_entries.sort_custom(func(a, b): return a[1] > b[1])

		var primary_crop = "foraging"
		var secondary_crop = null
		var primary_yield = 0.5

		if crop_entries.size() > 0:
			primary_crop = crop_entries[0][0]
			primary_yield = crop_entries[0][1]
		if crop_entries.size() > 1:
			secondary_crop = crop_entries[1][0]

		# ═══════════════════════════════════════════════════════════════════════
		# TRADE GOODS (§10b)
		# ═══════════════════════════════════════════════════════════════════════

		var stimulant_map = {
			"paddi": "char",
			"emmer": "qahwa",
			"taro": "awa",
			"sago": "pinang",
			"papa": "aqua",
			"nori": "",
			"foraging": ""
		}

		var fiber_map = {
			"paddi": "seric",
			"emmer": "fell",
			"taro": "tapa",
			"sago": "tapa",
			"nori": "byssus",
			"papa": "qivu",
			"foraging": ""
		}

		var protein_map = {
			"paddi": "kerbau",
			"emmer": "kri",
			"taro": "moa",
			"sago": "moa",
			"nori": "",
			"papa": "",
			"foraging": ""
		}

		var stimulant_type = stimulant_map.get(primary_crop, "")
		var fiber_type = fiber_map.get(primary_crop, "")
		var protein_type = protein_map.get(primary_crop, "")

		var stimulant_production = 0.0
		var fiber_production = 0.0
		var protein_production = 0.0
		var nori_export = 0.0

		if stimulant_type != "":
			stimulant_production = 0.3 + rng.next_float() * 0.5

		if fiber_type != "":
			fiber_production = 0.3 + rng.next_float() * 0.5

		if protein_type != "":
			protein_production = 0.3 + rng.next_float() * 0.4

		if primary_crop == "nori":
			nori_export = 0.6 + rng.next_float() * 0.3
		elif can_grow["nori"]:
			nori_export = 0.1 + rng.next_float() * 0.2

		var total_trade_value = stimulant_production * 0.4 + fiber_production * 0.3 + protein_production * 0.2 + nori_export * 0.3

		var trade_goods = {
			"stimulant": {
				"type": stimulant_type,
				"production": stimulant_production
			},
			"fiber": {
				"type": fiber_type,
				"production": fiber_production
			},
			"protein": {
				"type": protein_type,
				"production": protein_production
			},
			"nori_export": nori_export,
			"stimulant_deficit": stimulant_type == "",
			"fiber_deficit": fiber_type == "",
			"total_trade_value": total_trade_value
		}

		# ═══════════════════════════════════════════════════════════════════════
		# POLITICAL CULTURE (§10c — Almond & Verba civic/subject/parochial)
		# ═══════════════════════════════════════════════════════════════════════

		var culture_init = {
			"paddi": {"awareness": 0.70, "participation": 0.15},
			"emmer": {"awareness": 0.70, "participation": 0.70},
			"taro": {"awareness": 0.15, "participation": 0.10},
			"nori": {"awareness": 0.30, "participation": 0.55},
			"sago": {"awareness": 0.15, "participation": 0.20},
			"papa": {"awareness": 0.25, "participation": 0.15},
			"foraging": {"awareness": 0.05, "participation": 0.05}
		}

		var political_culture = (culture_init.get(primary_crop, culture_init["foraging"])).duplicate()

		var culture_label = ""
		if political_culture["awareness"] > 0.5:
			culture_label = "civic" if political_culture["participation"] > 0.5 else "subject"
		else:
			culture_label = "parochial"

		# ═══════════════════════════════════════════════════════════════════════
		# MODE OF PRODUCTION (§10d — Marxian surplus/labor continuous space)
		# ═══════════════════════════════════════════════════════════════════════

		var prod_init = {
			"paddi": {"surplus": 0.85, "labor": 0.25},
			"emmer": {"surplus": 0.65, "labor": 0.70},
			"taro": {"surplus": 0.55, "labor": 0.15},
			"nori": {"surplus": 0.35, "labor": 0.55},
			"sago": {"surplus": 0.10, "labor": 0.05},
			"papa": {"surplus": 0.20, "labor": 0.10},
			"foraging": {"surplus": 0.05, "labor": 0.02}
		}

		var production = (prod_init.get(primary_crop, prod_init["foraging"])).duplicate()

		# Forbidden zone enforcement: labor <= surplus + 0.3
		production["labor"] = minf(production["labor"], production["surplus"] + 0.3)

		# Mode label from position in surplus/labor space
		var mode_label = ""
		if production["surplus"] > 0.7 and production["labor"] < 0.3:
			mode_label = "asiatic"
		elif production["surplus"] > 0.7 and production["labor"] < 0.6:
			mode_label = "tributary empire"
		elif production["surplus"] > 0.7 and production["labor"] >= 0.6:
			mode_label = "state capital"
		elif production["surplus"] > 0.4 and production["labor"] >= 0.6:
			mode_label = "mercantile"
		elif production["surplus"] > 0.4 and production["labor"] >= 0.3:
			mode_label = "petty commodity"
		elif production["surplus"] > 0.4:
			mode_label = "tributary"
		elif production["surplus"] > 0.15:
			mode_label = "household"
		elif production["labor"] < 0.2:
			mode_label = "communal"
		else:
			mode_label = "frontier"

		# Derived production values
		var collaboration_efficiency = 0.0
		if production["surplus"] > 0.7:
			collaboration_efficiency = 0.85
		elif production["surplus"] > 0.5:
			collaboration_efficiency = 0.60
		elif production["surplus"] > 0.3:
			collaboration_efficiency = 0.45
		elif production["surplus"] > 0.15:
			collaboration_efficiency = 0.20
		else:
			collaboration_efficiency = 0.05

		var extraction_ceiling = 0.30  # default
		if mode_label == "asiatic":
			extraction_ceiling = 0.40
		elif mode_label == "mercantile":
			extraction_ceiling = 0.30
		elif mode_label == "tributary":
			extraction_ceiling = 0.50
		elif mode_label == "petty commodity":
			extraction_ceiling = 0.25
		elif mode_label == "household":
			extraction_ceiling = 0.10
		elif mode_label == "communal":
			extraction_ceiling = 0.05

		var production_dict = {
			"surplus": production["surplus"],
			"labor": production["labor"],
			"mode": mode_label,
			"collaboration_efficiency": collaboration_efficiency,
			"extraction_ceiling": extraction_ceiling
		}

		# ═══════════════════════════════════════════════════════════════════════
		# MINERALS (§10g — Fe, Cu, Au, Pu)
		# ═══════════════════════════════════════════════════════════════════════

		var minerals = {
			"Fe": true,
			"Cu": rng.next_float() < 0.20,
			"Au": rng.next_float() < (0.05 + avg_h * 0.08),  # taller peaks = more hydrothermal
			"Pu": rng.next_float() < (0.03 + size * 0.02)    # larger archs = more evolved magma
		}

		# ═══════════════════════════════════════════════════════════════════════
		# NARRATIVE SUBSTRATE (§10e)
		# ═══════════════════════════════════════════════════════════════════════

		var gender_economy = minf(1.0, avg_edge / max_edge_len)

		var metaphor_map = {
			"paddi": "tidal",
			"emmer": "navigational",
			"taro": "seasonal",
			"sago": "seasonal",
			"nori": "oceanic",
			"papa": "endurance",
			"foraging": "animist"
		}

		var religion_map = {
			"subject": "formal-institutional",
			"civic": "devotional-debate",
			"parochial": "animist-local"
		}

		var narrative = {
			"gender_economy": gender_economy,
			"metaphor": metaphor_map.get(primary_crop, "animist"),
			"religion": religion_map.get(culture_label, "animist-local")
		}

		# ═══════════════════════════════════════════════════════════════════════
		# ASSEMBLE SUBSTRATE DICT
		# ═══════════════════════════════════════════════════════════════════════

		var substrate = {
			"climate": climate,
			"crops": {
				"primary_crop": primary_crop,
				"secondary_crop": secondary_crop,
				"primary_yield": primary_yield,
				"can_grow": can_grow
			},
			"trade_goods": trade_goods,
			"political_culture": {
				"awareness": political_culture["awareness"],
				"participation": political_culture["participation"],
				"label": culture_label
			},
			"production": production_dict,
			"minerals": minerals,
			"narrative": narrative
		}

		substrates.append(substrate)

	return substrates


## Compute gyre position for an arch within its latitude band.
## Returns position along the dominant ocean current circulation (0.0 = cool eastern side, 1.0 = warm western side).
static func _compute_gyre_position(arch: Dictionary, all_archs: Array) -> float:
	# Extract latitude from north pole position (cy)
	var cy_clamped = maxf(minf(arch["cy"], 1.0), -1.0)
	var lat = asin(cy_clamped) * 180.0 / PI
	var abs_lat = absf(lat)

	# Find archs in same latitude band (within 15°)
	var band_archs = []
	for other_arch in all_archs:
		var other_cy_clamped = maxf(minf(other_arch["cy"], 1.0), -1.0)
		var other_lat = asin(other_cy_clamped) * 180.0 / PI
		var other_abs_lat = absf(other_lat)
		if absf(other_abs_lat - abs_lat) < 15:
			band_archs.append(other_arch)

	if band_archs.size() < 2:
		return 0.5

	# Extract longitudes (atan2 of xz plane)
	var lons = []
	for band_arch in band_archs:
		var lon = atan2(band_arch["cz"], band_arch["cx"]) * 180.0 / PI
		lons.append(lon)

	# Sort longitudes
	lons.sort()

	# Find widest longitudinal gap (open ocean boundary)
	var max_gap = 0.0
	var gap_center = 0.0
	for j in range(lons.size()):
		var next_lon = lons[(j + 1) % lons.size()]
		if j == lons.size() - 1:
			next_lon += 360.0  # wrap around
		var gap = next_lon - lons[j]
		if gap > max_gap:
			max_gap = gap
			gap_center = lons[j] + gap / 2.0

	# If no clear gap, return neutral position
	if max_gap < 10:
		return 0.5

	# Position relative to gap center
	var my_lon = atan2(arch["cz"], arch["cx"]) * 180.0 / PI
	var rel_pos = fmod(my_lon - gap_center + 540.0, 360.0) / 360.0
	return maxf(0.0, minf(1.0, rel_pos))
