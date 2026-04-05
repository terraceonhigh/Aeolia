## Mulberry32 deterministic PRNG.
## Same seed -> same world, always. Every random decision in the
## simulation traces back to this class.
##
## Matches the JS mulberry32 implementation EXACTLY:
##   function mulberry32(s) {
##     return ()=>{s|=0;s=(s+0x6D2B79F5)|0;
##       let t=Math.imul(s^(s>>>15),1|s);
##       t=(t+Math.imul(t^(t>>>7),61|t))^t;
##       return((t^(t>>>14))>>>0)/4294967296;};
##   }
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
## Matches JS mulberry32 exactly — verified against reference values.
func next_float() -> float:
	# s = (s + 0x6D2B79F5) | 0  — signed 32-bit add
	state = (state + 0x6D2B79F5) & 0xFFFFFFFF
	var s: int = state
	# Sign-extend for |0 semantics
	if s >= 0x80000000:
		s -= 0x100000000

	# t = Math.imul(s ^ (s >>> 15), 1 | s)
	var t: int = _imul(s ^ _urs(s, 15), 1 | s)

	# t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
	# IMPORTANT: the final ^ t uses the ORIGINAL t, and JS evaluates
	# the full right side before assignment.
	var t_orig: int = t
	t = ((t + _imul(t ^ _urs(t, 7), 61 | t)) ^ t_orig)

	# return ((t ^ (t >>> 14)) >>> 0) / 4294967296
	# >>> 0 converts to unsigned 32-bit
	var result: int = (t ^ _urs(t, 14)) & 0xFFFFFFFF
	return float(result) / 4294967296.0


## Unsigned right shift matching JS >>> operator.
## GDScript ints are 64-bit signed, so we mask to 32 bits first.
static func _urs(val: int, shift: int) -> int:
	return (val & 0xFFFFFFFF) >> shift


## 32-bit integer multiply matching JS Math.imul behavior.
## GDScript ints are 64-bit, so we mask to 32-bit after multiply.
static func _imul(a: int, b: int) -> int:
	# Force 32-bit unsigned interpretation
	a = a & 0xFFFFFFFF
	b = b & 0xFFFFFFFF
	# Multiply low 16-bit halves and cross terms to avoid 64-bit overflow issues
	var al: int = a & 0xFFFF
	var ah: int = (a >> 16) & 0xFFFF
	var bl: int = b & 0xFFFF
	var bh: int = (b >> 16) & 0xFFFF
	var result: int = ((al * bl) + (((ah * bl + al * bh) & 0xFFFF) << 16)) & 0xFFFFFFFF
	# Sign-extend for JS signed 32-bit semantics
	if result >= 0x80000000:
		result -= 0x100000000
	return result
