## Dijkstra history engine + population model.
## Two wavefronts (Reach, Lattice) radiate along plateau edges.
## Edge costs depend on era + power + hop count.
## Phases: 1) Dijkstra wavefront, 2) Σ2^n redistribution,
## 3) Status assignment, 4) Population model (5 eras),
## 5) Final state + log construction.
class_name HistoryEngine
extends RefCounted

# Era boundaries (in years BP)
const R_START := -5500
const L_START := -5000
const ERA_BOUNDS := [-500, -200]


## Main entry point. Assigns polity control via dual-source Dijkstra,
## then runs population model through 5 historical eras.
##
## archs: Array of archipelago objects with .peaks, .shelfR, .cx, .cy, .cz
## plateau_edges: Array of [a, b] edge pairs
## seed: World seed for deterministic RNG
## reach_arch: Index of Reach starting archipelago
## lattice_arch: Index of Lattice starting archipelago
##
## Returns: { "states": Array, "log": Array, "df_year": Variant, "df_arch": Variant, "df_detector": Variant }
static func assign_politics(archs: Array, plateau_edges: Array, p_seed: int, reach_arch: int, lattice_arch: int) -> Dictionary:
	var rng := RNG.new((p_seed if p_seed != 0 else 42) * 31 + 1066)
	var N := archs.size()

	# ── Adjacency ──
	var adj := []
	adj.resize(N)
	for i in range(N):
		adj[i] = []
	for edge in plateau_edges:
		var a = edge[0]
		var b = edge[1]
		adj[a].append(b)
		adj[b].append(a)

	# BFS distances (kept for display and status logic)
	var r_dist := _bfs_dist(reach_arch, adj, N)
	var l_dist := _bfs_dist(lattice_arch, adj, N)

	# ── Resource potential ──
	var potential := []
	for i in range(N):
		var arch = archs[i]
		var p = arch.peaks.size()
		var sz = arch.shelf_r / 0.12
		var avg_h = 0.0
		if p > 0:
			for pk in arch.peaks:
				avg_h += pk.h
			avg_h /= (p * Constants.ISLAND_MAX_HEIGHT)
		var pot = (p / 20.0 * 0.4 + avg_h * 0.3 + sz / 2.2 * 0.3) * (0.6 + rng.next_float() * 0.4)
		potential.append(pot)

	# ── Name assignment ──
	var names := []
	names.resize(N)
	names[reach_arch] = Constants.POLITY_NAMES[0]
	names[lattice_arch] = Constants.POLITY_NAMES[1]

	var pool = Constants.POLITY_NAMES.slice(2)
	# Fisher-Yates shuffle
	for i in range(pool.size() - 1, 0, -1):
		var j = int(rng.next_float() * (i + 1))
		var tmp = pool[i]
		pool[i] = pool[j]
		pool[j] = tmp

	var pi = 0
	for i in range(N):
		if i == reach_arch or i == lattice_arch:
			continue
		if pi < pool.size():
			names[i] = pool[pi]
			pi += 1
		else:
			names[i] = "Archipelago %d" % i

	# ═══════════════════════════════════════════════════════════
	# PHASE 1: DIJKSTRA WAVEFRONT
	# Two ink drops on wet paper. Edge cost = f(era, power, hops).
	# Era-boundary mechanic: if a hop is too expensive in the
	# current era, wait for the era to change and retry cheaper.
	# ═══════════════════════════════════════════════════════════

	var claimed := []
	claimed.resize(N)
	claimed.fill(null)

	var arrival_yr := []
	arrival_yr.resize(N)
	arrival_yr.fill(null)

	var hop_count := []
	hop_count.resize(N)
	hop_count.fill(0)

	var parent_arch := []
	parent_arch.resize(N)
	parent_arch.fill(-1)

	# Seed wavefronts
	claimed[reach_arch] = "reach"
	arrival_yr[reach_arch] = R_START
	claimed[lattice_arch] = "lattice"
	arrival_yr[lattice_arch] = L_START

	# Priority queue: [year, archIdx, power, hops, fromArch]
	var pq := []
	for nb in adj[reach_arch]:
		var cost = _edge_cost(R_START, 1, "reach")
		pq.append([R_START + cost, nb, "reach", 1, reach_arch])

	for nb in adj[lattice_arch]:
		var cost = _edge_cost(L_START, 1, "lattice")
		pq.append([L_START + cost, nb, "lattice", 1, lattice_arch])

	var df_year = null
	var df_arch = null
	var df_detector = null
	var df_target = null

	while pq.size() > 0:
		# Pop earliest arrival
		pq.sort_custom(func(a, b): return a[0] < b[0])
		var entry = pq.pop_front()
		var year = entry[0]
		var idx = entry[1]
		var power = entry[2]
		var hops = entry[3]
		var from = entry[4]

		if claimed[idx] != null:
			# DF detection: wavefront hits territory of the other power
			if claimed[idx] != power and df_year == null:
				df_year = year
				df_arch = idx
				df_detector = power
				df_target = claimed[idx]
			continue

		# Claim
		claimed[idx] = power
		arrival_yr[idx] = year
		hop_count[idx] = hops
		parent_arch[idx] = from

		# Check neighbors for DF adjacency: a newly claimed node
		# borders an existing node of the other power across an edge
		for nb in adj[idx]:
			if claimed[nb] and claimed[nb] != power and df_year == null:
				df_year = year
				df_arch = idx
				df_detector = power
				df_target = claimed[nb]

		# Expand to unclaimed neighbors
		for nb in adj[idx]:
			if claimed[nb]:
				continue
			var cost = _edge_cost(year, hops + 1, power)
			pq.append([year + cost, nb, power, hops + 1, idx])

	# ═══════════════════════════════════════════════════════════
	# PHASE 2: Σ2^n REDISTRIBUTION
	# Preserves Dijkstra ORDER, adjusts TIMING so each era
	# roughly doubles discoveries. 2+4+8+16 = 30, ~25% uncontacted.
	# ═══════════════════════════════════════════════════════════
	var contactable := []
	for i in range(N):
		if claimed[i] and i != reach_arch and i != lattice_arch:
			contactable.append(i)

	contactable.sort_custom(func(a, b): return arrival_yr[a] < arrival_yr[b])
	var nc = contactable.size()

	var serial_n = maxi(1, roundi(float(nc) * 0.05))
	var colonial_n = maxi(1, roundi(float(nc) * 0.10))
	var industrial_n = maxi(2, roundi(float(nc) * 0.20))
	var nuclear_n = maxi(2, roundi(float(nc) * 0.40))
	var total_slots = serial_n + colonial_n + industrial_n + nuclear_n

	for k in range(nc):
		var i = contactable[k]
		if k < serial_n:
			arrival_yr[i] = -5000 + roundi(float(k + 1) / float(serial_n + 1) * 3000.0)
		elif k < serial_n + colonial_n:
			var j = k - serial_n
			arrival_yr[i] = -2000 + roundi(float(j + 1) / float(colonial_n + 1) * 1500.0)
		elif k < serial_n + colonial_n + industrial_n:
			var j = k - serial_n - colonial_n
			arrival_yr[i] = -500 + roundi(float(j + 1) / float(industrial_n + 1) * 300.0)
		elif k < total_slots:
			var j = k - serial_n - colonial_n - industrial_n
			var df_off = absi(df_year) if df_year != null else 200
			arrival_yr[i] = -200 + roundi(float(j + 1) / float(nuclear_n + 1) * float(mini(200, df_off - 200)))
		else:
			# El Dorados — beyond Σ2^n budget
			claimed[i] = null
			arrival_yr[i] = null

	# Recompute DF year after redistribution
	df_year = null
	df_arch = null
	df_detector = null
	df_target = null

	for i in range(N):
		if not claimed[i]:
			continue
		for nb in adj[i]:
			if claimed[nb] and claimed[nb] != claimed[i]:
				var yr = maxi(arrival_yr[i], arrival_yr[nb])
				if df_year == null or yr < df_year:
					df_year = yr
					df_arch = i
					df_detector = claimed[i]
					df_target = claimed[nb]

	# Null out post-DF claims
	for i in range(N):
		if arrival_yr[i] != null and df_year != null and arrival_yr[i] > df_year:
			claimed[i] = null
			arrival_yr[i] = null

	# ═══════════════════════════════════════════════════════════
	# PHASE 3: STATUS ASSIGNMENT
	# Simple rules from power + hopCount + era. Hooks for
	# sovereignty/trade 2D space, Silk Road, Tokugawa closures,
	# Mughal independents, pulse contacts — all TODO.
	# ═══════════════════════════════════════════════════════════
	var sovereign := []
	sovereign.resize(N)
	sovereign.fill(-1)

	var colony_yr := []
	colony_yr.resize(N)
	colony_yr.fill(null)

	var status_data := []
	for i in range(N):
		status_data.append({
			"sovereignty": 1.0,
			"tradeIntegration": 0.0,
			"status": "uncontacted",
			"eraOfContact": null,
		})

	for i in range(N):
		if i == reach_arch or i == lattice_arch:
			status_data[i] = {"sovereignty": 1.0, "tradeIntegration": 1.0, "status": "core", "eraOfContact": null}
			continue

		var yr = arrival_yr[i]
		var power = claimed[i]
		var hops = hop_count[i]

		if not yr or not power:
			status_data[i] = {"sovereignty": 1.0, "tradeIntegration": 0.0, "status": "uncontacted", "eraOfContact": null}
			continue

		var era = "sail"
		if yr < -2000:
			era = "sail"
		elif yr < -500:
			era = "colonial"
		elif yr < -200:
			era = "industrial"
		else:
			era = "nuclear"

		status_data[i]["eraOfContact"] = era

		if power == "reach":
			if hops <= 3 and era != "nuclear":
				sovereign[i] = reach_arch
				colony_yr[i] = yr + int(100 + rng.next_float() * 300)
				status_data[i] = {"sovereignty": 0.15, "tradeIntegration": 0.85, "status": "colony", "eraOfContact": era}
			elif hops <= 5 and era != "nuclear":
				status_data[i] = {"sovereignty": 0.55, "tradeIntegration": 0.60, "status": "client", "eraOfContact": era}
			else:
				status_data[i] = {"sovereignty": 0.90, "tradeIntegration": 0.20, "status": "contacted", "eraOfContact": era}
		else:
			if hops <= 3:
				sovereign[i] = lattice_arch
				colony_yr[i] = yr + 200
				status_data[i] = {"sovereignty": 0.30, "tradeIntegration": 0.50, "status": "garrison", "eraOfContact": era}
			elif hops <= 5:
				status_data[i] = {"sovereignty": 0.60, "tradeIntegration": 0.40, "status": "tributary", "eraOfContact": era}
			else:
				status_data[i] = {"sovereignty": 0.90, "tradeIntegration": 0.15, "status": "pulse", "eraOfContact": era}

	# ═══════════════════════════════════════════════════════════
	# PHASE 4: POPULATION MODEL
	# Five eras. Uses Dijkstra output (claimed, arrival_yr,
	# hop_count, status_data) instead of old BFS race.
	# ═══════════════════════════════════════════════════════════
	var pop := []
	var tech := []

	for i in range(N):
		var arch = archs[i]
		var p = arch.peaks.size()
		var sz = arch.shelf_r / 0.12
		var base_pop = float(p) * (sz) * (3.0 + rng.next_float() * 4.0)
		pop.append(base_pop)
		tech.append(0.0)

	var log := []

	# ── ERA 1: ANTIQUITY ──
	log.append({
		"arch": -1, "name": "═══ ANTIQUITY",
		"faction": "era", "status": "era",
		"label": "20,000 – 5,000 BP · Independent development · Lattice develops tidal-flat agriculture",
		"rDist": 0, "lDist": 0, "contactYr": -20000
	})

	for i in range(N):
		pop[i] *= pow(1.0 + 0.002 * potential[i], 30.0)
		tech[i] = potential[i] * (2.5 + rng.next_float() * 1.5)

	tech[reach_arch] = maxf(tech[reach_arch], 3.5)
	tech[lattice_arch] = maxf(tech[lattice_arch], 3.8)
	pop[lattice_arch] *= 2.5

	# ── ERA 2: SERIAL CONTACT ──
	log.append({
		"arch": -1, "name": "═══ SERIAL CONTACT",
		"faction": "era", "status": "era",
		"label": "5,000 – 2,000 BP · First gap crossings · Epidemiological shock · Trade enrichment",
		"rDist": 0, "lDist": 0, "contactYr": -5000
	})

	var reach_network = 0
	var lattice_network = 0

	for i in range(N):
		if i == reach_arch or i == lattice_arch:
			continue

		var yr = arrival_yr[i]
		if yr != null and yr >= -5000 and yr < -2000:
			var shock = 0.25 + rng.next_float() * 0.35
			var pre_pop = roundi(pop[i])
			pop[i] *= shock
			var trade_years = maxi(0, -2000 - yr)
			pop[i] *= 1.0 + float(trade_years) * 0.0004
			tech[i] += 0.5 + rng.next_float() * 0.5

			if claimed[i] == "reach":
				reach_network += 1
			if claimed[i] == "lattice":
				lattice_network += 1

			log.append({
				"arch": i, "name": names[i],
				"faction": claimed[i], "status": status_data[i]["status"],
				"label": "Contacted ~%d BP · pop %d→%d · %d%% shock" % [abs(yr), pre_pop, roundi(pop[i]), roundi(shock * 100)],
				"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": yr
			})
		elif not yr or yr >= -2000:
			pop[i] *= 1.0 + 0.001 * potential[i] * 30.0

	pop[reach_arch] *= 1.5 * (1.0 + _log2(1.0 + float(reach_network)) * 0.20)
	tech[reach_arch] = minf(6.0, tech[reach_arch] + 1.2)
	pop[lattice_arch] *= 1.6 * (1.0 + _log2(1.0 + float(lattice_network)) * 0.30)
	tech[lattice_arch] = minf(6.0, tech[lattice_arch] + 1.0)

	# ── ERA 3: COLONIAL EMPIRES ──
	log.append({
		"arch": -1, "name": "═══ COLONIAL EMPIRES",
		"faction": "era", "status": "era",
		"label": "2,000 – 500 BP · Pearl-strings · Lattice absorption · Reach extraction",
		"rDist": 0, "lDist": 0, "contactYr": -2000
	})

	var reach_colonies = 0
	var lattice_garrisons = 0
	var lattice_tribs = 0
	var total_extracted = 0.0
	var total_enslaved = 0.0

	for i in range(N):
		if i == reach_arch or i == lattice_arch:
			continue

		var yr = arrival_yr[i]
		var power = claimed[i]
		var sd = status_data[i]

		if not yr:
			continue

		if yr < -500:
			if sd["status"] == "colony":
				var col_years = maxi(0, -500 - (colony_yr[i] if colony_yr[i] else yr))
				var extraction_rate = 0.15 + float(col_years) * 0.0001
				var extracted = pop[i] * extraction_rate
				pop[i] -= extracted
				total_extracted += extracted

				var enslaved = pop[i] * (0.05 + rng.next_float() * 0.10)
				pop[i] -= enslaved
				total_enslaved += enslaved
				pop[i] += 8.0 + rng.next_float() * 15.0

				reach_colonies += 1
				log.append({
					"arch": i, "name": names[i],
					"faction": "reach", "status": "colony",
					"label": "Colonized ~%d BP · pop %d · %d%% extracted · %d enslaved" % [
						abs(colony_yr[i] if colony_yr[i] else yr), roundi(pop[i]),
						roundi(extraction_rate * 100), roundi(enslaved)
					],
					"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": yr
				})
			elif sd["status"] == "garrison":
				var absorbed = pop[i] * (0.15 + rng.next_float() * 0.10)
				pop[lattice_arch] += absorbed
				lattice_garrisons += 1
				log.append({
					"arch": i, "name": names[i],
					"faction": "lattice", "status": "garrison",
					"label": "Garrisoned ~%d BP · pop %d · %d absorbed · hop %d" % [
						abs(colony_yr[i] if colony_yr[i] else yr), roundi(pop[i]),
						roundi(absorbed), hop_count[i]
					],
					"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": yr
				})
			elif sd["status"] == "tributary":
				var tribute = pop[i] * (0.05 + rng.next_float() * 0.05)
				pop[lattice_arch] += tribute
				lattice_tribs += 1
				log.append({
					"arch": i, "name": names[i],
					"faction": "lattice", "status": "tributary",
					"label": "Tributary ~%d BP · pop %d · %d tribute" % [abs(yr), roundi(pop[i]), roundi(tribute)],
					"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": yr
				})
			elif sd["status"] == "client":
				pop[i] *= 1.0 + _log2(1.0 + float(reach_network)) * 0.10
				tech[i] += 0.3 + rng.next_float() * 0.3
				log.append({
					"arch": i, "name": names[i],
					"faction": "reach", "status": "client",
					"label": "Client state ~%d BP · pop %d" % [abs(yr), roundi(pop[i])],
					"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": yr
				})
			elif sd["status"] == "pulse":
				log.append({
					"arch": i, "name": names[i],
					"faction": "lattice", "status": "pulse",
					"label": "Pulse-contacted ~%d BP · Zheng He'd · fleet departed · pop %d" % [abs(yr), roundi(pop[i])],
					"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": yr
				})

		# New contacts in this era
		if yr >= -2000 and yr < -500:
			var shock = 0.30 + rng.next_float() * 0.35
			var pre_pop = roundi(pop[i])
			pop[i] *= shock
			tech[i] += 0.3

			if power == "reach":
				reach_network += 1
			if power == "lattice":
				lattice_network += 1

			log.append({
				"arch": i, "name": names[i],
				"faction": power, "status": sd["status"],
				"label": "Contacted ~%d BP · pop %d→%d · %d%% shock" % [
					abs(yr), pre_pop, roundi(pop[i]), roundi(shock * 100)
				],
				"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": yr
			})

	pop[reach_arch] *= 1.0 + float(reach_colonies) * 0.12
	pop[reach_arch] += total_extracted * 0.6 + total_enslaved
	var lattice_integrated = lattice_garrisons + lattice_tribs
	pop[lattice_arch] *= 1.0 + float(lattice_garrisons) * 0.15 + float(lattice_tribs) * 0.08

	for i in range(N):
		if claimed[i] or i == reach_arch or i == lattice_arch:
			continue
		pop[i] *= 1.0 + 0.0005 * potential[i] * 15.0
		tech[i] = minf(4.0, tech[i] + potential[i] * 0.1)

	# ── ERA 4: INDUSTRIAL ──
	log.append({
		"arch": -1, "name": "═══ INDUSTRIAL",
		"faction": "era", "status": "era",
		"label": "500 – 200 BP · Steam · Colonies stagnate · Trade partners industrialize",
		"rDist": 0, "lDist": 0, "contactYr": -500
	})

	var total_network = reach_network + lattice_network

	for i in range(N):
		if i == reach_arch:
			pop[i] *= (1.0 + tech[i] * 0.08 + potential[i] * 0.15) * (1.0 + _log2(1.0 + float(total_network)) * 0.12)
			tech[i] = minf(8.0, tech[i] + potential[i] * 0.8)
			continue

		if i == lattice_arch:
			pop[i] *= (1.0 + tech[i] * 0.10 + potential[i] * 0.18) * (1.0 + float(lattice_integrated) * 0.08)
			tech[i] = minf(8.0, tech[i] + potential[i] * 0.7)
			continue

		if not claimed[i]:
			pop[i] *= 1.0 + 0.0003 * potential[i] * 6.0
			tech[i] = minf(4.5, tech[i] + potential[i] * 0.05)
			continue

		if sovereign[i] >= 0:
			pop[i] *= 1.0 + tech[i] * 0.03 + potential[i] * 0.05
			tech[i] = minf(6.0, tech[i] + potential[i] * 0.3)
		else:
			pop[i] *= 1.0 + tech[i] * 0.08 + potential[i] * 0.12
			tech[i] = minf(7.5, tech[i] + potential[i] * 0.7)

		var yr = arrival_yr[i]
		if yr != null and yr >= -500 and yr < -200:
			pop[i] *= 0.5 + rng.next_float() * 0.3
			log.append({
				"arch": i, "name": names[i],
				"faction": claimed[i], "status": status_data[i]["status"],
				"label": "Industrial contact ~%d BP · pop %d · tech Δ%.1f" % [
					abs(yr), roundi(pop[i]), float(roundi((tech[reach_arch] - tech[i]) * 10)) / 10.0
				],
				"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": yr
			})

	tech[reach_arch] = maxf(tech[reach_arch], 7.0)
	tech[lattice_arch] = maxf(tech[lattice_arch], 6.5)

	# ── ERA 5: NUCLEAR ──
	log.append({
		"arch": -1, "name": "═══ NUCLEAR THRESHOLD",
		"faction": "era", "status": "era",
		"label": "200 BP – contact · Reactor seaplanes · Post-colonial recovery",
		"rDist": 0, "lDist": 0, "contactYr": -200
	})

	pop[reach_arch] *= 1.4
	tech[reach_arch] = 10.0
	pop[lattice_arch] *= 1.35
	tech[lattice_arch] = 9.5

	for i in range(N):
		if i == reach_arch or i == lattice_arch:
			continue
		if not claimed[i]:
			continue

		var access = 0.0
		if sovereign[i] == reach_arch:
			access = 0.7
		elif sovereign[i] == lattice_arch:
			access = 0.5
		else:
			access = 0.3

		if sovereign[i] >= 0 and rng.next_float() < 0.4:
			pop[i] *= 1.3 + rng.next_float() * 0.3

		pop[i] *= 1.0 + access * 0.2
		tech[i] = minf(10.0, tech[i] + access)

		var yr = arrival_yr[i]
		if yr != null and yr >= -200:
			log.append({
				"arch": i, "name": names[i],
				"faction": claimed[i], "status": status_data[i]["status"],
				"label": "Nuclear surveillance · pop %d · tech Δ%.1f" % [
					roundi(pop[i]), float(roundi((10.0 - tech[i]) * 10)) / 10.0
				],
				"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": yr
			})

	# ═══════════════════════════════════════════════════════════
	# PHASE 5: FINAL STATE + LOG
	# ═══════════════════════════════════════════════════════════
	var max_pop = 0.0
	for p in pop:
		max_pop = maxf(max_pop, p)

	var states := []
	for i in range(N):
		var sd = status_data[i]
		var urbanization = pop[i] / max_pop if max_pop > 0 else 0.0
		var faction = ""

		if i == reach_arch:
			faction = "reach"
		elif i == lattice_arch:
			faction = "lattice"
		elif not claimed[i]:
			faction = "unknown"
		else:
			faction = claimed[i]

		states.append({
			"faction": faction,
			"status": sd["status"],
			"name": names[i],
			"population": roundi(pop[i]),
			"urbanization": urbanization,
			"tech": float(roundi(tech[i] * 10)) / 10.0,
			"sovereignty": sd["sovereignty"],
			"tradeIntegration": sd["tradeIntegration"],
			"eraOfContact": sd["eraOfContact"],
			"hopCount": hop_count[i],
		})

	# Core log entries
	log.insert(1, {
		"arch": reach_arch, "name": names[reach_arch],
		"faction": "reach", "status": "core",
		"label": "Core · pop %d · tech %.1f · %d colonies · %d contacts" % [
			roundi(pop[reach_arch]), tech[reach_arch], reach_colonies, reach_network
		],
		"rDist": 0, "lDist": l_dist[reach_arch], "contactYr": -20000
	})
	log.insert(2, {
		"arch": lattice_arch, "name": names[lattice_arch],
		"faction": "lattice", "status": "core",
		"label": "Core · pop %d · tech %.1f · %d garrisons · %d tributaries" % [
			roundi(pop[lattice_arch]), tech[lattice_arch], lattice_garrisons, lattice_tribs
		],
		"rDist": l_dist[reach_arch], "lDist": 0, "contactYr": -20000
	})

	# Unknowns
	for i in range(N):
		if not claimed[i] and i != reach_arch and i != lattice_arch:
			var max_tech = 0.0
			for t in tech:
				max_tech = maxf(max_tech, t)
			var tech_delta = roundi(max_tech - tech[i])
			log.append({
				"arch": i, "name": names[i],
				"faction": "unknown", "status": "unknown",
				"label": "%d islands · Neolithic isolation · tech Δ%d · pop %d" % [
					archs[i].peaks.size(), tech_delta, roundi(pop[i])
				],
				"rDist": r_dist[i], "lDist": l_dist[i], "contactYr": null
			})

	# DF event
	var d_name = "?"
	var t_name = "?"
	if df_detector == "reach":
		d_name = names[reach_arch]
	elif df_detector == "lattice":
		d_name = names[lattice_arch]

	if df_target == "reach":
		t_name = names[reach_arch]
	elif df_target == "lattice":
		t_name = names[lattice_arch]

	var v_name = names[df_arch] if (df_arch != null and df_arch >= 0) else "unknown"
	var df_label: String
	if df_year != null:
		df_label = "%d BP — %s detects radio traffic beyond %s. %s exists. The Dark Forest breaks." % [
			abs(df_year), d_name, v_name, t_name
		]
	else:
		df_label = "The Dark Forest holds. No contact detected."

	log.append({
		"arch": -1, "name": "⚠ CONTACT",
		"faction": "contact", "status": "contact",
		"label": df_label,
		"rDist": 0, "lDist": 0, "contactYr": df_year
	})

	return {
		"states": states,
		"log": log,
		"df_year": df_year,
		"df_arch": df_arch,
		"df_detector": df_detector,
	}


# ─── HELPERS ──────────────────────────────────────────────────

## Compute edge cost based on era, power, and hop count.
static func _edge_cost(year: int, hops: int, power: String) -> int:
	var is_lattice = power == "lattice"
	var is_garrison = is_lattice and hops <= 3

	var cost = 0

	if year < -500:
		# SAIL ERA
		if is_garrison:
			cost = 167
		elif is_lattice:
			cost = 12000
		else:
			if hops <= 1:
				cost = 350
			elif hops <= 2:
				cost = 580
			elif hops <= 3:
				cost = 1060
			else:
				cost = 8000
	elif year < -200:
		# INDUSTRIAL
		if is_garrison:
			cost = 85
		elif is_lattice:
			if hops <= 5:
				cost = 350
			else:
				cost = 700
		else:
			if hops <= 4:
				cost = 125
			elif hops <= 6:
				cost = 145
			else:
				cost = 200
	else:
		# NUCLEAR
		cost = 61

	# If cost pushes past an era boundary, check if waiting is cheaper.
	# Match JSX exactly: use plain era cost (non-recursive) and return on first improvement.
	for b in ERA_BOUNDS:
		if year < b and year + cost > b:
			var alt = (b - year + 1) + _base_era_cost(b + 1, hops, power)
			if alt < cost:
				return alt

	return cost


## Plain era cost lookup — no boundary-crossing optimization.
## Mirrors JSX's inner costInEra() closure used in the alt formula.
static func _base_era_cost(year: int, hops: int, power: String) -> int:
	var is_lattice = power == "lattice"
	var is_garrison = is_lattice and hops <= 3
	if year < -500:
		if is_garrison: return 167
		if is_lattice: return 12000
		if hops <= 1: return 350
		if hops <= 2: return 580
		if hops <= 3: return 1060
		return 8000
	elif year < -200:
		if is_garrison: return 85
		if is_lattice: return 350 if hops <= 5 else 700
		if hops <= 4: return 125
		if hops <= 6: return 145
		return 200
	else:
		return 61


## BFS to compute distances from start node.
static func _bfs_dist(start: int, adj: Array, N: int) -> Array:
	var dist := []
	dist.resize(N)
	dist.fill(999)

	dist[start] = 0
	var q = [start]

	while q.size() > 0:
		var u = q.pop_front()
		for v in adj[u]:
			if dist[v] > dist[u] + 1:
				dist[v] = dist[u] + 1
				q.append(v)

	return dist


## log₂(x) = ln(x) / ln(2)
static func _log2(x: float) -> float:
	if x <= 0.0:
		return 0.0
	return log(x) / log(2.0)
