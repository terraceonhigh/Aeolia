## Height function and noise utilities.
## Pure math. No rendering. Produces height values from (x,y,z)
## coordinates on the unit sphere. Used by any renderer.
class_name TerrainMath
extends RefCounted

# -- Permutation table (fixed seed 42 for determinism) --
static var _P: PackedInt32Array
static var _initialized := false


static func _ensure_init() -> void:
	if _initialized:
		return
	_initialized = true
	var p: Array[int] = []
	p.resize(256)
	for i in 256:
		p[i] = i
	# Fisher-Yates with fixed seed for determinism
	var s: int = 42
	for i in range(255, 0, -1):
		s = (s * 16807) % 2147483647
		var j: int = s % (i + 1)
		var tmp: int = p[i]
		p[i] = p[j]
		p[j] = tmp
	_P.resize(512)
	for i in 512:
		_P[i] = p[i & 255]


static func _fade(t: float) -> float:
	return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


static func _grad(hash_val: int, x: float, y: float, z: float) -> float:
	var h: int = hash_val & 15
	var u: float = x if h < 8 else y
	var v: float
	if h < 4:
		v = y
	elif h == 12 or h == 14:
		v = x
	else:
		v = z
	return ((-u) if (h & 1) else u) + ((-v) if (h & 2) else v)


## 3D Perlin noise. Returns roughly [-1, 1].
static func smooth_noise(x: float, y: float, z: float) -> float:
	_ensure_init()
	var xi: int = floori(x) & 255
	var yi: int = floori(y) & 255
	var zi: int = floori(z) & 255
	var xf: float = x - floorf(x)
	var yf: float = y - floorf(y)
	var zf: float = z - floorf(z)
	var u: float = _fade(xf)
	var v: float = _fade(yf)
	var w: float = _fade(zf)
	var A: int = _P[xi] + yi
	var AA: int = _P[A] + zi
	var AB: int = _P[A + 1] + zi
	var B: int = _P[xi + 1] + yi
	var BA: int = _P[B] + zi
	var BB: int = _P[B + 1] + zi
	return lerpf(
		lerpf(
			lerpf(_grad(_P[AA], xf, yf, zf), _grad(_P[BA], xf - 1.0, yf, zf), u),
			lerpf(_grad(_P[AB], xf, yf - 1.0, zf), _grad(_P[BB], xf - 1.0, yf - 1.0, zf), u),
			v),
		lerpf(
			lerpf(_grad(_P[AA + 1], xf, yf, zf - 1.0), _grad(_P[BA + 1], xf - 1.0, yf, zf - 1.0), u),
			lerpf(_grad(_P[AB + 1], xf, yf - 1.0, zf - 1.0), _grad(_P[BB + 1], xf - 1.0, yf - 1.0, zf - 1.0), u),
			v),
		w)


## Fractal Brownian Motion — layered noise.
static func fbm(x: float, y: float, z: float, octaves: int) -> float:
	var val := 0.0
	var amp := 1.0
	var freq := 1.0
	var total := 0.0
	for i in octaves:
		val += smooth_noise(x * freq, y * freq, z * freq) * amp
		total += amp
		amp *= 0.45
		freq *= 2.1
	return val / total


## Computes terrain height at a point on the unit sphere.
## world_archs: Array of arch dictionaries with {cx, cy, cz, peaks, shelf_r}
## world_edges: Array of edge dictionaries
## detail: LOD level (higher = more noise octaves)
## bw_scale: bridge/plateau width multiplier
static func compute_height(x: float, y: float, z: float,
		world_archs: Array, world_edges: Array,
		detail: int, bw_scale: float) -> float:
	var height: float = Constants.OCEAN_DEPTH_BASE + fbm(x, y, z, mini(detail, 6)) * 400.0

	# Ridged noise - organic mid-ocean ridges
	var rn1: float = 1.0 - absf(smooth_noise(x * 3.2, y * 3.2, z * 3.2))
	height += rn1 * rn1 * rn1 * 900.0
	var rn2: float = 1.0 - absf(smooth_noise(x * 2.1 + 7.7, y * 2.1 + 3.3, z * 2.1 + 5.5))
	height += rn2 * rn2 * rn2 * 500.0

	# -- Submarine plateaus --
	var w_mul: float = bw_scale / 0.13 if bw_scale > 0.0 else 1.0

	# (A) Shelf blobs at each archipelago
	for a in world_archs.size():
		var ar: Dictionary = world_archs[a]
		var dot: float = x * ar.cx + y * ar.cy + z * ar.cz
		var blob_r: float = ar.shelf_r * 1.4 * w_mul
		if dot < 1.0 - blob_r * blob_r * 2.0:
			continue
		var bws := 3.5
		var bwa: float = blob_r * 0.5
		var bwx: float = x + smooth_noise(x * bws + a * 11.1, y * bws, z * bws) * bwa
		var bwy: float = y + smooth_noise(x * bws + a * 11.1 + 77.0, y * bws + 77.0, z * bws + 77.0) * bwa
		var bwz: float = z + smooth_noise(x * bws + a * 11.1 + 155.0, y * bws + 155.0, z * bws + 155.0) * bwa
		var bwl: float = sqrt(bwx * bwx + bwy * bwy + bwz * bwz)
		if bwl == 0.0:
			bwl = 1.0
		var wdot: float = (bwx * ar.cx + bwy * ar.cy + bwz * ar.cz) / bwl
		var bd2: float = 2.0 * (1.0 - wdot)
		var bf: float = exp(-bd2 / (blob_r * blob_r * 0.8))
		if bf < 0.02:
			continue
		var pn1: float = smooth_noise(x * 6.0 + a * 3.1, y * 6.0, z * 6.0) * 0.3
		var pn2: float = smooth_noise(x * 14.0 + a * 7.7, y * 14.0, z * 14.0) * 0.12
		var bl: float = (Constants.PLATEAU_HEIGHT + 30.0 + (pn1 + pn2) * 120.0) * bf + height * (1.0 - bf)
		if bl > height:
			height = bl

	# (B) Corridor connections - domain-warped great-circle bands
	for e in world_edges.size():
		var ed: Dictionary = world_edges[e]
		var cws := 2.5
		var cwa: float = ed.w * 1.2
		var cwx: float = x + smooth_noise(x * cws + e * 13.3, y * cws + e * 5.5, z * cws + e * 9.1) * cwa
		var cwy: float = y + smooth_noise(x * cws + e * 13.3 + 77.0, y * cws + e * 5.5 + 77.0, z * cws + e * 9.1 + 77.0) * cwa
		var cwz: float = z + smooth_noise(x * cws + e * 13.3 + 155.0, y * cws + e * 5.5 + 155.0, z * cws + e * 9.1 + 155.0) * cwa
		var cwl: float = sqrt(cwx * cwx + cwy * cwy + cwz * cwz)
		if cwl == 0.0:
			cwl = 1.0
		var dtp: float = absf((cwx * ed.nx + cwy * ed.ny + cwz * ed.nz) / cwl)
		var width_noise: float = smooth_noise(x * 4.0 + e * 7.1, y * 4.0 + e * 3.3, z * 4.0 + e * 5.7) * 0.35 + 0.8
		var effective_w: float = ed.w * width_noise * w_mul
		if dtp >= effective_w:
			continue
		var d_a: float = x * ed.ax + y * ed.ay + z * ed.az
		var d_b: float = x * ed.bx + y * ed.by + z * ed.bz
		if d_a < ed.dot_ab - 0.35 or d_b < ed.dot_ab - 0.35:
			continue
		var f: float = 1.0 - dtp / effective_w
		var sf: float = f * f * (3.0 - 2.0 * f)
		var pn1: float = smooth_noise(x * 8.0, y * 8.0, z * 8.0) * 0.4
		var pn2: float = smooth_noise(x * 16.0, y * 16.0, z * 16.0) * 0.15
		var pn3: float = smooth_noise(x * 3.0 + 1.1, y * 3.0 + 2.2, z * 3.0 + 3.3) * 0.2
		var pt: float = Constants.PLATEAU_HEIGHT + (pn1 + pn2 + pn3) * 150.0
		var bl: float = pt * sf + height * (1.0 - sf)
		if bl > height:
			height = bl

	# -- Archipelagos - domain-warped volcanic peaks --
	for a in world_archs.size():
		var ar: Dictionary = world_archs[a]
		var dot: float = x * ar.cx + y * ar.cy + z * ar.cz
		if dot < 0.85:
			continue
		for p in ar.peaks.size():
			var pk: Dictionary = ar.peaks[p]
			var pd: float = x * pk.px + y * pk.py + z * pk.pz
			if pd < 0.96:
				continue
			# Domain warping for organic island shapes
			var ws: float = 1.0 / maxf(pk.w, 0.005)
			var warp_amp: float = pk.w * 0.6
			var w1x: float = smooth_noise(x * ws * 1.8, y * ws * 1.8, z * ws * 1.8) * warp_amp
			var w1y: float = smooth_noise(x * ws * 1.8 + 77.0, y * ws * 1.8 + 77.0, z * ws * 1.8 + 77.0) * warp_amp
			var w1z: float = smooth_noise(x * ws * 1.8 + 155.0, y * ws * 1.8 + 155.0, z * ws * 1.8 + 155.0) * warp_amp
			var w2x: float = smooth_noise(x * ws * 4.5, y * ws * 4.5, z * ws * 4.5) * warp_amp * 0.35
			var w2y: float = smooth_noise(x * ws * 4.5 + 33.0, y * ws * 4.5 + 33.0, z * ws * 4.5 + 33.0) * warp_amp * 0.35
			var w2z: float = smooth_noise(x * ws * 4.5 + 66.0, y * ws * 4.5 + 66.0, z * ws * 4.5 + 66.0) * warp_amp * 0.35
			var w3x := 0.0
			var w3y := 0.0
			var w3z := 0.0
			if detail > 5:
				w3x = smooth_noise(x * ws * 12.0, y * ws * 12.0, z * ws * 12.0) * warp_amp * 0.12
				w3y = smooth_noise(x * ws * 12.0 + 44.0, y * ws * 12.0 + 44.0, z * ws * 12.0 + 44.0) * warp_amp * 0.12
				w3z = smooth_noise(x * ws * 12.0 + 88.0, y * ws * 12.0 + 88.0, z * ws * 12.0 + 88.0) * warp_amp * 0.12
			var wx: float = x + w1x + w2x + w3x
			var wy: float = y + w1y + w2y + w3y
			var wz: float = z + w1z + w2z + w3z
			var wlen: float = sqrt(wx * wx + wy * wy + wz * wz)
			if wlen == 0.0:
				wlen = 1.0
			var pdw: float = (wx * pk.px + wy * pk.py + wz * pk.pz) / wlen
			var d2w: float = 2.0 * (1.0 - pdw)
			var pv: float = pk.h * exp(-d2w * pk.w2inv)
			if pv < 10.0:
				continue
			# Ridge/valley erosion
			if detail > 4 and pv > 50.0:
				var rs: float = ws * 0.7
				var ridge: float = (1.0 - absf(smooth_noise(x * rs * 3.0, y * rs * 3.0, z * rs * 3.0))) * \
					(1.0 - absf(smooth_noise(x * rs * 7.0, y * rs * 7.0, z * rs * 7.0)))
				var slope_factor: float = sin(minf(1.0, pv / pk.h) * PI)
				pv *= 1.0 - ridge * 0.35 * slope_factor
			# Fine roughness
			if detail > 6 and pv > 100.0:
				pv += smooth_noise(x * ws * 25.0, y * ws * 25.0, z * ws * 25.0) * 60.0 * \
					sin(minf(1.0, pv / pk.h) * PI)
			if pv > height:
				height = pv

	return height
