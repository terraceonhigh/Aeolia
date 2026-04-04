## Mulberry32 deterministic PRNG.
## Same seed -> same world, always. Every random decision in the
## simulation traces back to this class.
##
## Usage:
##   var rng = RNG.new(42)
##   var val = rng.next_float()  # 0.0 .. 1.0
class_name RNG
extends RefCounted

var state: int


func _init(p_seed: int) -> void:
	state = p_seed & 0xFFFFFFFF


## Returns the next float in [0.0, 1.0).
## Mirrors the JS: mulberry32(a) closure behavior exactly.
func next_float() -> float:
	state = (state + 0x6D2B79F5) & 0xFFFFFFFF
	var t: int = _imul(state ^ (state >> 15), 1 | state)
	t = (t + _imul(t ^ (t >> 7), 61 | t)) & 0xFFFFFFFF
	t = (t ^ (t >> 14)) & 0x7FFFFFFF
	return float(t) / 2147483648.0


## 32-bit integer multiply matching JS Math.imul behavior.
## GDScript ints are 64-bit, so we mask to 32-bit after multiply.
static func _imul(a: int, b: int) -> int:
	# Force 32-bit signed interpretation
	a = a & 0xFFFFFFFF
	b = b & 0xFFFFFFFF
	# Multiply low 16-bit halves and cross terms to avoid 64-bit overflow issues
	var al: int = a & 0xFFFF
	var ah: int = (a >> 16) & 0xFFFF
	var bl: int = b & 0xFFFF
	var bh: int = (b >> 16) & 0xFFFF
	return ((al * bl) + (((ah * bl + al * bh) & 0xFFFF) << 16)) & 0xFFFFFFFF
