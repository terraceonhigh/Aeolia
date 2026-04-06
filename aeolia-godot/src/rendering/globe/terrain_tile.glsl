// Aeolia terrain tile compute shader.
// Generates one TILE_RES×TILE_RES (9×9) vertex grid on the GPU.
//
// Each invocation handles one vertex (gl_LocalInvocationID.xy = [i, j]).
// Dispatch: (1, 1, 1) work group — all 81 invocations in one group.
//
// Math is bit-identical to terrain_math.gd:
//   - Hash: uint32 arithmetic (wrapping per Vulkan/SPIR-V spec = JS imul behavior)
//   - smooth_noise: smoothstep trilinear value noise, not Perlin
//   - fbm: amplitude 0.5, frequency 3.5, half/2.1x per octave
//   - compute_height: OCEAN_DEPTH_BASE=-4200, PLATEAU_HEIGHT=-120
//
// Output layout (set 0, binding 3): 12 floats per vertex (48 bytes)
//   [0-2]  position xyz   [3]  pad
//   [4-6]  normal xyz     [7]  pad
//   [8-10] color rgb      [11] pad

#[compute]
#version 450

layout(local_size_x = 9, local_size_y = 9, local_size_z = 1) in;

// ─────────────────────────────────────────────────────────
// Push constant — per-tile parameters (40 bytes)
// ─────────────────────────────────────────────────────────
layout(push_constant) uniform TileParams {
    int   fi;          // Cube face index 0–5
    int   depth;       // Quadtree depth (LOD)
    float u_min;
    float u_max;
    float v_min;
    float v_max;
    float sea_level;   // meters
    float bw_scale;    // bridge/plateau width multiplier
    int   arch_count;
    int   edge_count;
} params;

// ─────────────────────────────────────────────────────────
// SSBOs — all in set 0
// ─────────────────────────────────────────────────────────

// Arch data (binding 0): 32 bytes per arch
// cx,cy,cz,shelf_r | peak_start(u32),peak_count(u32),pad,pad
struct ArchData {
    float cx, cy, cz, shelf_r;
    uint  peak_start, peak_count;
    float _pad0, _pad1;
};
layout(std430, set = 0, binding = 0) readonly buffer ArchBuf {
    ArchData archs[];
};

// Peak data (binding 1): 32 bytes per peak (flattened across all archs)
// px,py,pz,w | h,w2inv,pad,pad
struct PeakData {
    float px, py, pz, w;
    float h, w2inv;
    float _pad0, _pad1;
};
layout(std430, set = 0, binding = 1) readonly buffer PeakBuf {
    PeakData peaks[];
};

// Edge data (binding 2): 48 bytes per edge
// ax,ay,az,w | bx,by,bz,dot_ab | nx,ny,nz,pad
struct EdgeData {
    float ax, ay, az, w;
    float bx, by, bz, dot_ab;
    float nx, ny, nz, _pad;
};
layout(std430, set = 0, binding = 2) readonly buffer EdgeBuf {
    EdgeData edges[];
};

// Output (binding 3): 12 floats (48 bytes) per vertex — 81 verts = 3888 bytes
layout(std430, set = 0, binding = 3) writeonly buffer OutputBuf {
    float verts[];
};

// ─────────────────────────────────────────────────────────
// Color LUT — 26 stops from -5000m to +3500m
// Matches _COLOR_STOPS in globe_mesh.gd exactly.
// ─────────────────────────────────────────────────────────
const int LUT_N = 26;
const float LUT_H[26] = float[26](
    -5000.0, -4000.0, -3000.0, -2200.0, -1500.0,  -800.0,  -500.0,  -300.0,
     -150.0,   -80.0,   -40.0,   -15.0,    -5.0,     0.0,     5.0,    15.0,
       35.0,    80.0,   150.0,   300.0,   500.0,   800.0,  1200.0,  1800.0,
     2500.0,  3500.0
);
const float LUT_R[26] = float[26](
    0.012, 0.018, 0.025, 0.035, 0.045, 0.060, 0.080, 0.100,
    0.130, 0.155, 0.175, 0.195, 0.210, 0.220, 0.240, 0.265,
    0.280, 0.260, 0.240, 0.225, 0.240, 0.270, 0.320, 0.380,
    0.460, 0.550
);
const float LUT_G[26] = float[26](
    0.025, 0.035, 0.050, 0.070, 0.100, 0.140, 0.185, 0.220,
    0.270, 0.310, 0.340, 0.360, 0.375, 0.380, 0.360, 0.350,
    0.340, 0.330, 0.310, 0.290, 0.270, 0.260, 0.280, 0.330,
    0.420, 0.510
);
const float LUT_B[26] = float[26](
    0.08, 0.10, 0.14, 0.18, 0.24, 0.32, 0.38, 0.42,
    0.48, 0.52, 0.54, 0.55, 0.54, 0.50, 0.42, 0.36,
    0.30, 0.24, 0.20, 0.18, 0.17, 0.18, 0.20, 0.25,
    0.36, 0.44
);

// ─────────────────────────────────────────────────────────
// Hash-based value noise — bit-identical to terrain_math.gd
//
// Uses uint32 arithmetic. Vulkan/SPIR-V guarantees two's-complement
// wrapping for unsigned integer ops (OpIAdd, OpIMul) — same as JS
// Math.imul / >>> behavior that the GDScript version emulates.
// ─────────────────────────────────────────────────────────

// Matches _hash(ix, iy, iz). Returns [0, 1].
float aeolia_hash(int ix, int iy, int iz) {
    uint h = uint(ix) * 374761393u
           + uint(iy) * 668265263u
           + uint(iz) * 1274126177u;
    h ^= (h >> 13u);
    h *= 1274126177u;
    h ^= (h >> 16u);
    return float(h & 0x7FFFFFFFu) / float(0x7FFFFFFF);
}

// Matches smooth_noise(x, y, z). Returns roughly [-1, 1].
// Smoothstep (cubic Hermite) trilinear interpolation — NOT Perlin gradient noise.
float smooth_noise(float x, float y, float z) {
    int ix = int(floor(x));
    int iy = int(floor(y));
    int iz = int(floor(z));
    float fx = x - float(ix);
    float fy = y - float(iy);
    float fz = z - float(iz);
    float ux = fx * fx * (3.0 - 2.0 * fx);
    float uy = fy * fy * (3.0 - 2.0 * fy);
    float uz = fz * fz * (3.0 - 2.0 * fz);
    float n000 = aeolia_hash(ix,   iy,   iz  );
    float n100 = aeolia_hash(ix+1, iy,   iz  );
    float n010 = aeolia_hash(ix,   iy+1, iz  );
    float n110 = aeolia_hash(ix+1, iy+1, iz  );
    float n001 = aeolia_hash(ix,   iy,   iz+1);
    float n101 = aeolia_hash(ix+1, iy,   iz+1);
    float n011 = aeolia_hash(ix,   iy+1, iz+1);
    float n111 = aeolia_hash(ix+1, iy+1, iz+1);
    return (n000*(1.0-ux)*(1.0-uy)*(1.0-uz) +
            n100*ux      *(1.0-uy)*(1.0-uz) +
            n010*(1.0-ux)*uy      *(1.0-uz) +
            n110*ux      *uy      *(1.0-uz) +
            n001*(1.0-ux)*(1.0-uy)*uz       +
            n101*ux      *(1.0-uy)*uz       +
            n011*(1.0-ux)*uy      *uz       +
            n111*ux      *uy      *uz) * 2.0 - 1.0;
}

// Matches fbm(x, y, z, octaves). Amplitude 0.5, frequency 3.5, ×0.5/×2.1 per octave.
float aeolia_fbm(float x, float y, float z, int octaves) {
    float v = 0.0;
    float a = 0.5;
    float f = 3.5;
    for (int i = 0; i < octaves; i++) {
        v += a * smooth_noise(x * f, y * f, z * f);
        a *= 0.5;
        f *= 2.1;
    }
    return v;
}

// ─────────────────────────────────────────────────────────
// Cube-sphere projection — matches _cube_to_sphere() in globe_mesh.gd
// ─────────────────────────────────────────────────────────
vec3 cube_to_sphere(int fi, float u, float v) {
    float cx, cy, cz;
    if      (fi == 0) { cx =  1.0; cy = v;    cz = -u;   }  // +X
    else if (fi == 1) { cx = -1.0; cy = v;    cz =  u;   }  // -X
    else if (fi == 2) { cx =  u;   cy =  1.0; cz = -v;   }  // +Y
    else if (fi == 3) { cx =  u;   cy = -1.0; cz =  v;   }  // -Y
    else if (fi == 4) { cx =  u;   cy = v;    cz =  1.0; }  // +Z
    else              { cx = -u;   cy = v;    cz = -1.0; }  // -Z
    return normalize(vec3(cx, cy, cz));
}

// ─────────────────────────────────────────────────────────
// Terrain height — matches compute_height() in terrain_math.gd
//
// Constants:
//   OCEAN_DEPTH_BASE = -4200.0
//   PLATEAU_HEIGHT   = -120.0
// ─────────────────────────────────────────────────────────
float compute_height(float x, float y, float z, int detail, float bw_scale) {
    // Base ocean noise
    float height = -4200.0 + aeolia_fbm(x, y, z, min(detail, 6)) * 400.0;

    // Ridged noise — organic mid-ocean ridges
    float rn1 = 1.0 - abs(smooth_noise(x * 3.2, y * 3.2, z * 3.2));
    height += rn1 * rn1 * rn1 * 900.0;
    float rn2 = 1.0 - abs(smooth_noise(x * 2.1 + 7.7, y * 2.1 + 3.3, z * 2.1 + 5.5));
    height += rn2 * rn2 * rn2 * 500.0;

    float w_mul = (bw_scale > 0.0) ? (bw_scale / 0.13) : 1.0;

    // ── (A) Submarine shelf blobs at each archipelago ──
    for (int a = 0; a < params.arch_count; a++) {
        ArchData ar = archs[a];
        float dot = x * ar.cx + y * ar.cy + z * ar.cz;
        float blob_r = ar.shelf_r * 1.4 * w_mul;
        if (dot < 1.0 - blob_r * blob_r * 2.0)
            continue;
        float bws = 3.5;
        float bwa = blob_r * 0.5;
        float fa  = float(a);
        float bwx = x + smooth_noise(x*bws + fa*11.1,        y*bws,         z*bws        ) * bwa;
        float bwy = y + smooth_noise(x*bws + fa*11.1 + 77.0, y*bws + 77.0,  z*bws + 77.0 ) * bwa;
        float bwz = z + smooth_noise(x*bws + fa*11.1 +155.0, y*bws + 155.0, z*bws + 155.0) * bwa;
        float bwl = length(vec3(bwx, bwy, bwz));
        if (bwl == 0.0) bwl = 1.0;
        float wdot = (bwx*ar.cx + bwy*ar.cy + bwz*ar.cz) / bwl;
        float bd2  = 2.0 * (1.0 - wdot);
        float bf   = exp(-bd2 / (blob_r * blob_r * 0.8));
        if (bf < 0.02) continue;
        float pn1 = smooth_noise(x*6.0  + fa*3.1, y*6.0,  z*6.0 ) * 0.3;
        float pn2 = smooth_noise(x*14.0 + fa*7.7, y*14.0, z*14.0) * 0.12;
        // PLATEAU_HEIGHT = -120.0; +30 offset matches GDScript: PLATEAU_HEIGHT + 30.0
        float bl = (-90.0 + (pn1 + pn2) * 120.0) * bf + height * (1.0 - bf);
        if (bl > height) height = bl;
    }

    // ── (B) Corridor connections — domain-warped great-circle bands ──
    for (int e = 0; e < params.edge_count; e++) {
        EdgeData ed = edges[e];
        // Fast pre-reject: vertex too far from great-circle plane
        if (abs(x*ed.nx + y*ed.ny + z*ed.nz) > ed.w * 3.5)
            continue;
        // Must be angularly between the two arch endpoints (with slack)
        if (x*ed.ax + y*ed.ay + z*ed.az < ed.dot_ab - 0.55)
            continue;
        if (x*ed.bx + y*ed.by + z*ed.bz < ed.dot_ab - 0.55)
            continue;

        float cws = 2.5;
        float cwa = ed.w * 1.2;
        float fe  = float(e);
        float cwx = x + smooth_noise(x*cws + fe*13.3,        y*cws + fe*5.5,        z*cws + fe*9.1        ) * cwa;
        float cwy = y + smooth_noise(x*cws + fe*13.3 + 77.0, y*cws + fe*5.5 + 77.0, z*cws + fe*9.1 + 77.0 ) * cwa;
        float cwz = z + smooth_noise(x*cws + fe*13.3 +155.0, y*cws + fe*5.5 +155.0, z*cws + fe*9.1 +155.0 ) * cwa;
        float cwl = length(vec3(cwx, cwy, cwz));
        if (cwl == 0.0) cwl = 1.0;
        float dtp = abs((cwx*ed.nx + cwy*ed.ny + cwz*ed.nz) / cwl);
        float width_noise = smooth_noise(x*4.0 + fe*7.1, y*4.0 + fe*3.3, z*4.0 + fe*5.7) * 0.35 + 0.8;
        float effective_w = ed.w * width_noise * w_mul;
        if (dtp >= effective_w) continue;

        float d_a = x*ed.ax + y*ed.ay + z*ed.az;
        float d_b = x*ed.bx + y*ed.by + z*ed.bz;
        if (d_a < ed.dot_ab - 0.35 || d_b < ed.dot_ab - 0.35) continue;

        float f  = 1.0 - dtp / effective_w;
        float sf = f * f * (3.0 - 2.0 * f);
        float pn1 = smooth_noise(x*8.0,       y*8.0,       z*8.0      ) * 0.4;
        float pn2 = smooth_noise(x*16.0,      y*16.0,      z*16.0     ) * 0.15;
        float pn3 = smooth_noise(x*3.0 + 1.1, y*3.0 + 2.2, z*3.0 + 3.3) * 0.2;
        float pt  = -120.0 + (pn1 + pn2 + pn3) * 150.0;  // PLATEAU_HEIGHT
        float bl  = pt * sf + height * (1.0 - sf);
        if (bl > height) height = bl;
    }

    // ── Volcanic peaks — domain-warped Gaussian blobs ──
    for (int a = 0; a < params.arch_count; a++) {
        ArchData ar = archs[a];
        float dot = x*ar.cx + y*ar.cy + z*ar.cz;
        if (dot < 0.85) continue;

        uint pend = ar.peak_start + ar.peak_count;
        for (uint p = ar.peak_start; p < pend; p++) {
            PeakData pk = peaks[p];
            float pd = x*pk.px + y*pk.py + z*pk.pz;
            if (pd < 0.96) continue;

            float ws       = 1.0 / max(pk.w, 0.005);
            float warp_amp = pk.w * 0.6;

            // Layer 1 domain warp
            float w1x = smooth_noise(x*ws*1.8,         y*ws*1.8,         z*ws*1.8        ) * warp_amp;
            float w1y = smooth_noise(x*ws*1.8 + 77.0,  y*ws*1.8 + 77.0,  z*ws*1.8 + 77.0 ) * warp_amp;
            float w1z = smooth_noise(x*ws*1.8 +155.0,  y*ws*1.8 +155.0,  z*ws*1.8 +155.0 ) * warp_amp;
            // Layer 2 domain warp
            float w2x = smooth_noise(x*ws*4.5,         y*ws*4.5,         z*ws*4.5        ) * warp_amp * 0.35;
            float w2y = smooth_noise(x*ws*4.5 + 33.0,  y*ws*4.5 + 33.0,  z*ws*4.5 + 33.0 ) * warp_amp * 0.35;
            float w2z = smooth_noise(x*ws*4.5 + 66.0,  y*ws*4.5 + 66.0,  z*ws*4.5 + 66.0 ) * warp_amp * 0.35;
            // Layer 3 domain warp (high detail only)
            float w3x = 0.0, w3y = 0.0, w3z = 0.0;
            if (detail > 5) {
                w3x = smooth_noise(x*ws*12.0,        y*ws*12.0,        z*ws*12.0       ) * warp_amp * 0.12;
                w3y = smooth_noise(x*ws*12.0 + 44.0, y*ws*12.0 + 44.0, z*ws*12.0 + 44.0) * warp_amp * 0.12;
                w3z = smooth_noise(x*ws*12.0 + 88.0, y*ws*12.0 + 88.0, z*ws*12.0 + 88.0) * warp_amp * 0.12;
            }

            float wx   = x + w1x + w2x + w3x;
            float wy   = y + w1y + w2y + w3y;
            float wz   = z + w1z + w2z + w3z;
            float wlen = length(vec3(wx, wy, wz));
            if (wlen == 0.0) wlen = 1.0;
            float pdw = (wx*pk.px + wy*pk.py + wz*pk.pz) / wlen;
            float d2w = 2.0 * (1.0 - pdw);
            float pv  = pk.h * exp(-d2w * pk.w2inv);
            if (pv < 10.0) continue;

            // Ridge/valley erosion (detail > 4)
            if (detail > 4 && pv > 50.0) {
                float rs    = ws * 0.7;
                float ridge = (1.0 - abs(smooth_noise(x*rs*3.0, y*rs*3.0, z*rs*3.0))) *
                              (1.0 - abs(smooth_noise(x*rs*7.0, y*rs*7.0, z*rs*7.0)));
                float slope_factor = sin(min(1.0, pv / pk.h) * 3.14159265359);
                pv *= 1.0 - ridge * 0.35 * slope_factor;
            }

            // Fine terrain roughness (detail > 6)
            if (detail > 6 && pv > 30.0) {
                pv *= 1.0 + aeolia_fbm(x*ws*4.0, y*ws*4.0, z*ws*4.0, detail - 5) * 0.08;
            }

            if (pv > height) height = pv;
        }
    }

    return height;
}

// ─────────────────────────────────────────────────────────
// Altitude color — matches _get_altitude_color() in globe_mesh.gd
// ─────────────────────────────────────────────────────────
vec3 get_altitude_color(float height, float noise_val) {
    float h = clamp(height + noise_val * 25.0, -5000.0, 3500.0);

    // Linear scan to find the bounding stop pair (branchless: always runs 24 iters)
    int si = 0;
    for (int k = 0; k < 24; k++) {
        if (LUT_H[k + 1] < h) si = k + 1;
    }

    float h0 = LUT_H[si];
    float h1 = LUT_H[si + 1];
    float t  = clamp((h - h0) / (h1 - h0), 0.0, 1.0);
    float s  = t * t * (3.0 - 2.0 * t);  // smoothstep — matches JSX

    return vec3(
        LUT_R[si] + s * (LUT_R[si + 1] - LUT_R[si]),
        LUT_G[si] + s * (LUT_G[si + 1] - LUT_G[si]),
        LUT_B[si] + s * (LUT_B[si + 1] - LUT_B[si])
    );
}

// ─────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────
void main() {
    const int N = 9;  // TILE_RES — must match globe_mesh.gd
    int i   = int(gl_LocalInvocationID.x);
    int j   = int(gl_LocalInvocationID.y);
    int idx = j * N + i;

    float du = (params.u_max - params.u_min) / float(N - 1);
    float dv = (params.v_max - params.v_min) / float(N - 1);
    float u  = params.u_min + float(i) * du;
    float v  = params.v_min + float(j) * dv;

    vec3  sp           = cube_to_sphere(params.fi, u, v);
    int   detail_level = min(4 + params.depth, 8);
    float h            = compute_height(sp.x, sp.y, sp.z, detail_level, params.bw_scale);

    // Displacement — matches globe_mesh.gd DISP_SCALE = 1.7e-7
    vec3 pos;
    if (h > params.sea_level) {
        pos = sp * (1.0 + (h - params.sea_level) * 1.7e-7);
    } else {
        pos = sp;
    }

    // Color: smooth_noise perturbation then altitude LUT
    float noise_val = smooth_noise(sp.x * 10.0, sp.y * 10.0, sp.z * 10.0);
    vec3  col       = get_altitude_color(h - params.sea_level, noise_val);

    // Write 12 floats per vertex at offset idx*12:
    //   [0-2]  position  [3]  pad
    //   [4-6]  normal    [7]  pad
    //   [8-10] color     [11] pad
    int base = idx * 12;
    verts[base +  0] = pos.x;
    verts[base +  1] = pos.y;
    verts[base +  2] = pos.z;
    verts[base +  3] = 0.0;
    verts[base +  4] = sp.x;   // sphere-point normal
    verts[base +  5] = sp.y;
    verts[base +  6] = sp.z;
    verts[base +  7] = 0.0;
    verts[base +  8] = col.r;
    verts[base +  9] = col.g;
    verts[base + 10] = col.b;
    verts[base + 11] = 1.0;
}
