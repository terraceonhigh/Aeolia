#pragma once
#include <godot_cpp/classes/object.hpp>
#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/array.hpp>

namespace godot {

/// GDExtension wrapper exposing Aeolia terrain math in compiled C.
/// Registered as an Engine singleton ("TerrainMathExt") so GDScript can reach
/// it without directly naming the class (which would be a parse error if the
/// dylib is not built):
///
///   var ext = Engine.get_singleton("TerrainMathExt")
///   if ext:
///       height = ext.compute_height(x, y, z, archs, edges, detail, bw_scale)
///
/// All methods produce bit-identical results to the GDScript TerrainMath class.
class TerrainMathExt : public Object {
    GDCLASS(TerrainMathExt, Object)

protected:
    static void _bind_methods();

public:
    /// Hash at integer lattice point — matches GDScript _hash(ix, iy, iz).
    /// Returns [0, 1].
    double hash_int(int64_t ix, int64_t iy, int64_t iz) const;

    /// 3-D value noise with smoothstep — matches GDScript smooth_noise().
    /// Returns roughly [-1, 1].
    double smooth_noise(double x, double y, double z) const;

    /// Fractal Brownian motion — matches GDScript fbm().
    /// Initial amplitude 0.5, frequency 3.5, halving amplitude, ×2.1 frequency.
    double fbm(double x, double y, double z, int64_t octaves) const;

    /// Full terrain height at unit-sphere point (x, y, z).
    /// world_archs / world_edges are Arrays of Dictionaries matching the layout
    /// produced by WorldGenerator.  detail is the LOD level; bw_scale is the
    /// bridge-width multiplier (0.13 = standard).
    double compute_height(double x, double y, double z,
            const Array &world_archs, const Array &world_edges,
            int64_t detail, double bw_scale) const;
};

} // namespace godot
