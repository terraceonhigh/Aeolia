/// terrain_math_ext.cpp
/// GDExtension C implementation of Aeolia terrain math.
///
/// All math functions are bit-identical to the GDScript TerrainMath class.
/// The hash function replicates JS integer overflow arithmetic exactly using
/// explicit 32-bit truncation (matching GDScript's _imul / _unsigned_rshift).
///
/// Do NOT build with -ffast-math or /fp:fast — that would break IEEE 754
/// compliance and produce different bit patterns from the GDScript reference.

#include "terrain_math_ext.h"

#include <algorithm>
#include <cmath>
#include <cstdint>

#include <godot_cpp/core/class_db.hpp>
#include <godot_cpp/variant/array.hpp>
#include <godot_cpp/variant/dictionary.hpp>

using namespace godot;

// ============================================================
//  Planet constants — must match GDScript Constants class exactly.
// ============================================================
static constexpr double OCEAN_DEPTH_BASE = -4200.0;
static constexpr double PLATEAU_HEIGHT   = -120.0;

// ============================================================
//  Pure-C math — no Godot types, no dynamic dispatch.
//  These are the hot functions called millions of times per frame.
// ============================================================

/// 32-bit multiply matching GDScript _imul / JS Math.imul.
/// Returns lower 32 bits of the product as a signed 32-bit integer.
static inline int32_t imul32(int32_t a, int32_t b) {
    // Unsigned multiply is well-defined for truncation; cast back to signed.
    return static_cast<int32_t>(static_cast<uint32_t>(a) * static_cast<uint32_t>(b));
}

/// Hash at integer lattice point.
///
/// Matches GDScript TerrainMath._hash(ix, iy, iz) step-for-step:
///   h = (ix*374761393 + iy*668265263 + iz*1274126177) & 0xFFFFFFFF  [mask → uint32]
///   h sign-extended to int32
///   h = _imul(h ^ _unsigned_rshift(h,13), 1274126177)
///   return ((h ^ _unsigned_rshift(h,16)) & 0x7FFFFFFF) / 0x7FFFFFFF
///
/// The "unsigned right shift" in GDScript is (val & 0xFFFFFFFF) >> shift,
/// which is exactly (uint32_t)val >> shift.
static double c_hash(int32_t ix, int32_t iy, int32_t iz) {
    // Initial combination in 64-bit to avoid overflow, then mask to 32 bits.
    const int64_t sum = static_cast<int64_t>(ix) * 374761393LL
                      + static_cast<int64_t>(iy) * 668265263LL
                      + static_cast<int64_t>(iz) * 1274126177LL;
    // Mask + sign-extend: equivalent to GDScript's (... & 0xFFFFFFFF) then
    // "if h >= 0x80000000: h -= 0x100000000".
    int32_t h = static_cast<int32_t>(static_cast<uint32_t>(sum & 0xFFFFFFFFLL));

    // h ^ _unsigned_rshift(h, 13)  →  (uint32_t)h ^ ((uint32_t)h >> 13)
    uint32_t uh = static_cast<uint32_t>(h);
    h = imul32(static_cast<int32_t>(uh ^ (uh >> 13u)), 1274126177);

    // Final avalanche: (h ^ _unsigned_rshift(h,16)) & 0x7FFFFFFF
    uh = static_cast<uint32_t>(h);
    const uint32_t final_val = (uh ^ (uh >> 16u)) & 0x7FFFFFFFu;
    return static_cast<double>(final_val) / static_cast<double>(0x7FFFFFFF);
}

/// 3-D value noise with cubic smoothstep interpolation.
/// Matches GDScript TerrainMath.smooth_noise() exactly.
/// Returns roughly [-1, 1].
static double c_smooth_noise(double x, double y, double z) {
    const int32_t ix = static_cast<int32_t>(std::floor(x));
    const int32_t iy = static_cast<int32_t>(std::floor(y));
    const int32_t iz = static_cast<int32_t>(std::floor(z));
    const double fx = x - static_cast<double>(ix);
    const double fy = y - static_cast<double>(iy);
    const double fz = z - static_cast<double>(iz);

    // Cubic smoothstep (not quintic): t² (3 − 2t)
    const double ux = fx * fx * (3.0 - 2.0 * fx);
    const double uy = fy * fy * (3.0 - 2.0 * fy);
    const double uz = fz * fz * (3.0 - 2.0 * fz);

    // 8 corner hashes
    const double n000 = c_hash(ix,     iy,     iz    );
    const double n100 = c_hash(ix + 1, iy,     iz    );
    const double n010 = c_hash(ix,     iy + 1, iz    );
    const double n110 = c_hash(ix + 1, iy + 1, iz    );
    const double n001 = c_hash(ix,     iy,     iz + 1);
    const double n101 = c_hash(ix + 1, iy,     iz + 1);
    const double n011 = c_hash(ix,     iy + 1, iz + 1);
    const double n111 = c_hash(ix + 1, iy + 1, iz + 1);

    // Trilinear interpolation, then remap [0,1] → [-1,1]
    return (  n000 * (1.0 - ux) * (1.0 - uy) * (1.0 - uz)
            + n100 *        ux  * (1.0 - uy) * (1.0 - uz)
            + n010 * (1.0 - ux) *        uy  * (1.0 - uz)
            + n110 *        ux  *        uy  * (1.0 - uz)
            + n001 * (1.0 - ux) * (1.0 - uy) *        uz
            + n101 *        ux  * (1.0 - uy) *        uz
            + n011 * (1.0 - ux) *        uy  *        uz
            + n111 *        ux  *        uy  *        uz
           ) * 2.0 - 1.0;
}

/// Fractal Brownian motion.
/// Matches GDScript TerrainMath.fbm() exactly:
///   amplitude 0.5, frequency 3.5, each octave: a *= 0.5, f *= 2.1
static double c_fbm(double x, double y, double z, int octaves) {
    double v = 0.0, a = 0.5, f = 3.5;
    for (int i = 0; i < octaves; ++i) {
        v += a * c_smooth_noise(x * f, y * f, z * f);
        a *= 0.5;
        f *= 2.1;
    }
    return v;
}

/// Full terrain height — matches GDScript TerrainMath.compute_height() exactly.
/// Accesses world_archs / world_edges through Godot Variant/Dictionary, so
/// this function takes godot-cpp types even though the math is C-style.
static double c_compute_height(
        double x, double y, double z,
        const Array &world_archs, const Array &world_edges,
        int detail, double bw_scale)
{
    // ---- Base height: FBM ocean floor ----
    double height = OCEAN_DEPTH_BASE
                  + c_fbm(x, y, z, detail < 6 ? detail : 6) * 400.0;

    // ---- Ridged noise: organic mid-ocean ridges ----
    {
        double rn = 1.0 - std::abs(c_smooth_noise(x * 3.2, y * 3.2, z * 3.2));
        height += rn * rn * rn * 900.0;
    }
    {
        double rn = 1.0 - std::abs(
                c_smooth_noise(x * 2.1 + 7.7, y * 2.1 + 3.3, z * 2.1 + 5.5));
        height += rn * rn * rn * 500.0;
    }

    const double w_mul = (bw_scale > 0.0) ? bw_scale / 0.13 : 1.0;
    const int n_archs = world_archs.size();
    const int n_edges = world_edges.size();

    // ---- (A) Submarine shelf blobs at each archipelago ----
    for (int a = 0; a < n_archs; ++a) {
        const Dictionary ar = world_archs[a];
        const double arc_cx  = ar["cx"];
        const double arc_cy  = ar["cy"];
        const double arc_cz  = ar["cz"];
        const double shelf_r = ar["shelf_r"];

        const double dot    = x * arc_cx + y * arc_cy + z * arc_cz;
        const double blob_r = shelf_r * 1.4 * w_mul;
        if (dot < 1.0 - blob_r * blob_r * 2.0) {
            continue;
        }

        const double bws = 3.5;
        const double bwa = blob_r * 0.5;
        const double da  = static_cast<double>(a);

        const double bwx = x + c_smooth_noise(x * bws + da * 11.1,
                                              y * bws,
                                              z * bws) * bwa;
        const double bwy = y + c_smooth_noise(x * bws + da * 11.1 + 77.0,
                                              y * bws + 77.0,
                                              z * bws + 77.0) * bwa;
        const double bwz = z + c_smooth_noise(x * bws + da * 11.1 + 155.0,
                                              y * bws + 155.0,
                                              z * bws + 155.0) * bwa;

        double bwl = std::sqrt(bwx * bwx + bwy * bwy + bwz * bwz);
        if (bwl == 0.0) { bwl = 1.0; }

        const double wdot = (bwx * arc_cx + bwy * arc_cy + bwz * arc_cz) / bwl;
        const double bd2  = 2.0 * (1.0 - wdot);
        const double bf   = std::exp(-bd2 / (blob_r * blob_r * 0.8));
        if (bf < 0.02) { continue; }

        const double pn1 = c_smooth_noise(x * 6.0  + da * 3.1,
                                          y * 6.0, z * 6.0) * 0.3;
        const double pn2 = c_smooth_noise(x * 14.0 + da * 7.7,
                                          y * 14.0, z * 14.0) * 0.12;

        const double bl = (PLATEAU_HEIGHT + 30.0 + (pn1 + pn2) * 120.0) * bf
                        + height * (1.0 - bf);
        if (bl > height) { height = bl; }
    }

    // ---- (B) Corridor connections: domain-warped great-circle bands ----
    for (int e = 0; e < n_edges; ++e) {
        const Dictionary ed = world_edges[e];
        const double ed_nx  = ed["nx"];
        const double ed_ny  = ed["ny"];
        const double ed_nz  = ed["nz"];
        const double ed_w   = ed["w"];
        const double ed_ax  = ed["ax"];
        const double ed_ay  = ed["ay"];
        const double ed_az  = ed["az"];
        const double ed_bx  = ed["bx"];
        const double ed_by  = ed["by"];
        const double ed_bz  = ed["bz"];
        const double dot_ab = ed["dot_ab"];

        // Fast pre-reject: unwarped perpendicular distance outside 3.5× width.
        if (std::abs(x * ed_nx + y * ed_ny + z * ed_nz) > ed_w * 3.5) {
            continue;
        }
        // Angular pre-reject: vertex not between the two endpoints.
        if (x * ed_ax + y * ed_ay + z * ed_az < dot_ab - 0.55) { continue; }
        if (x * ed_bx + y * ed_by + z * ed_bz < dot_ab - 0.55) { continue; }

        const double cws = 2.5;
        const double cwa = ed_w * 1.2;
        const double de  = static_cast<double>(e);

        const double cwx = x + c_smooth_noise(x * cws + de * 13.3,
                                              y * cws + de *  5.5,
                                              z * cws + de *  9.1) * cwa;
        const double cwy = y + c_smooth_noise(x * cws + de * 13.3 + 77.0,
                                              y * cws + de *  5.5 + 77.0,
                                              z * cws + de *  9.1 + 77.0) * cwa;
        const double cwz = z + c_smooth_noise(x * cws + de * 13.3 + 155.0,
                                              y * cws + de *  5.5 + 155.0,
                                              z * cws + de *  9.1 + 155.0) * cwa;

        double cwl = std::sqrt(cwx * cwx + cwy * cwy + cwz * cwz);
        if (cwl == 0.0) { cwl = 1.0; }

        const double dtp = std::abs(
                (cwx * ed_nx + cwy * ed_ny + cwz * ed_nz) / cwl);
        const double width_noise = c_smooth_noise(x * 4.0 + de * 7.1,
                                                  y * 4.0 + de * 3.3,
                                                  z * 4.0 + de * 5.7) * 0.35 + 0.8;
        const double effective_w = ed_w * width_noise * w_mul;
        if (dtp >= effective_w) { continue; }

        const double d_a = x * ed_ax + y * ed_ay + z * ed_az;
        const double d_b = x * ed_bx + y * ed_by + z * ed_bz;
        if (d_a < dot_ab - 0.35 || d_b < dot_ab - 0.35) { continue; }

        const double f_val = 1.0 - dtp / effective_w;
        const double sf    = f_val * f_val * (3.0 - 2.0 * f_val);

        const double pn1 = c_smooth_noise(x * 8.0,       y * 8.0,       z * 8.0      ) * 0.40;
        const double pn2 = c_smooth_noise(x * 16.0,      y * 16.0,      z * 16.0     ) * 0.15;
        const double pn3 = c_smooth_noise(x * 3.0 + 1.1, y * 3.0 + 2.2, z * 3.0 + 3.3) * 0.20;
        const double pt  = PLATEAU_HEIGHT + (pn1 + pn2 + pn3) * 150.0;
        const double bl  = pt * sf + height * (1.0 - sf);
        if (bl > height) { height = bl; }
    }

    // ---- Archipelagos: domain-warped volcanic peaks ----
    for (int a = 0; a < n_archs; ++a) {
        const Dictionary ar  = world_archs[a];
        const double arc_cx  = ar["cx"];
        const double arc_cy  = ar["cy"];
        const double arc_cz  = ar["cz"];

        const double dot = x * arc_cx + y * arc_cy + z * arc_cz;
        if (dot < 0.85) { continue; }

        const Array peaks  = ar["peaks"];
        const int   n_peaks = peaks.size();

        for (int p = 0; p < n_peaks; ++p) {
            const Dictionary pk = peaks[p];
            const double pk_px    = pk["px"];
            const double pk_py    = pk["py"];
            const double pk_pz    = pk["pz"];
            const double pk_h     = pk["h"];
            const double pk_w     = pk["w"];
            const double pk_w2inv = pk["w2inv"];

            const double pd = x * pk_px + y * pk_py + z * pk_pz;
            if (pd < 0.96) { continue; }

            const double ws       = 1.0 / std::max(pk_w, 0.005);
            const double warp_amp = pk_w * 0.6;

            // First-order domain warp
            const double w1x = c_smooth_noise(x * ws * 1.8,
                                              y * ws * 1.8,
                                              z * ws * 1.8       ) * warp_amp;
            const double w1y = c_smooth_noise(x * ws * 1.8 + 77.0,
                                              y * ws * 1.8 + 77.0,
                                              z * ws * 1.8 + 77.0) * warp_amp;
            const double w1z = c_smooth_noise(x * ws * 1.8 + 155.0,
                                              y * ws * 1.8 + 155.0,
                                              z * ws * 1.8 + 155.0) * warp_amp;

            // Second-order domain warp
            const double w2x = c_smooth_noise(x * ws * 4.5,
                                              y * ws * 4.5,
                                              z * ws * 4.5       ) * warp_amp * 0.35;
            const double w2y = c_smooth_noise(x * ws * 4.5 + 33.0,
                                              y * ws * 4.5 + 33.0,
                                              z * ws * 4.5 + 33.0) * warp_amp * 0.35;
            const double w2z = c_smooth_noise(x * ws * 4.5 + 66.0,
                                              y * ws * 4.5 + 66.0,
                                              z * ws * 4.5 + 66.0) * warp_amp * 0.35;

            // Third-order domain warp (detail > 5 only)
            double w3x = 0.0, w3y = 0.0, w3z = 0.0;
            if (detail > 5) {
                w3x = c_smooth_noise(x * ws * 12.0,
                                     y * ws * 12.0,
                                     z * ws * 12.0       ) * warp_amp * 0.12;
                w3y = c_smooth_noise(x * ws * 12.0 + 44.0,
                                     y * ws * 12.0 + 44.0,
                                     z * ws * 12.0 + 44.0) * warp_amp * 0.12;
                w3z = c_smooth_noise(x * ws * 12.0 + 88.0,
                                     y * ws * 12.0 + 88.0,
                                     z * ws * 12.0 + 88.0) * warp_amp * 0.12;
            }

            const double wx = x + w1x + w2x + w3x;
            const double wy = y + w1y + w2y + w3y;
            const double wz = z + w1z + w2z + w3z;

            double wlen = std::sqrt(wx * wx + wy * wy + wz * wz);
            if (wlen == 0.0) { wlen = 1.0; }

            const double pdw = (wx * pk_px + wy * pk_py + wz * pk_pz) / wlen;
            const double d2w = 2.0 * (1.0 - pdw);
            double pv        = pk_h * std::exp(-d2w * pk_w2inv);
            if (pv < 10.0) { continue; }

            // Ridge/valley erosion (detail > 4, significant elevation only)
            if (detail > 4 && pv > 50.0) {
                const double rs    = ws * 0.7;
                const double ridge =
                        (1.0 - std::abs(c_smooth_noise(x * rs * 3.0,
                                                       y * rs * 3.0,
                                                       z * rs * 3.0))) *
                        (1.0 - std::abs(c_smooth_noise(x * rs * 7.0,
                                                       y * rs * 7.0,
                                                       z * rs * 7.0)));
                const double clamped     = std::min(1.0, pv / pk_h);
                const double slope_factor = std::sin(clamped * M_PI);
                pv *= 1.0 - ridge * 0.35 * slope_factor;
            }

            // Fine terrain roughness at closest zoom
            if (detail > 6 && pv > 30.0) {
                pv *= 1.0 + c_fbm(x * ws * 4.0,
                                  y * ws * 4.0,
                                  z * ws * 4.0,
                                  detail - 5) * 0.08;
            }

            if (pv > height) { height = pv; }
        }
    }

    return height;
}

// ============================================================
//  GDExtension class — thin wrappers calling the C functions above
// ============================================================

namespace godot {

void TerrainMathExt::_bind_methods() {
    ClassDB::bind_method(
            D_METHOD("hash_int", "ix", "iy", "iz"),
            &TerrainMathExt::hash_int);
    ClassDB::bind_method(
            D_METHOD("smooth_noise", "x", "y", "z"),
            &TerrainMathExt::smooth_noise);
    ClassDB::bind_method(
            D_METHOD("fbm", "x", "y", "z", "octaves"),
            &TerrainMathExt::fbm);
    ClassDB::bind_method(
            D_METHOD("compute_height",
                     "x", "y", "z",
                     "world_archs", "world_edges",
                     "detail", "bw_scale"),
            &TerrainMathExt::compute_height);
}

double TerrainMathExt::hash_int(int64_t ix, int64_t iy, int64_t iz) const {
    // GDScript uses 64-bit ints but the hash function works in 32-bit.
    // Truncate here exactly as GDScript does via (... & 0xFFFFFFFF) masking.
    return c_hash(static_cast<int32_t>(ix),
                  static_cast<int32_t>(iy),
                  static_cast<int32_t>(iz));
}

double TerrainMathExt::smooth_noise(double x, double y, double z) const {
    return c_smooth_noise(x, y, z);
}

double TerrainMathExt::fbm(double x, double y, double z, int64_t octaves) const {
    return c_fbm(x, y, z, static_cast<int>(octaves));
}

double TerrainMathExt::compute_height(
        double x, double y, double z,
        const Array &world_archs, const Array &world_edges,
        int64_t detail, double bw_scale) const {
    return c_compute_height(x, y, z,
                            world_archs, world_edges,
                            static_cast<int>(detail), bw_scale);
}

} // namespace godot
