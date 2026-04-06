"""
Generate a thin_sim-compatible base_world JSON from sim_proxy's synthetic world.

Use this to run smoke tests and local optimization without a Godot binary.
The substrate is computed by sim_proxy's Python model (no gyre model), so the
ag loss component will show a constant offset vs Godot-generated worlds — but
all other components optimize correctly.

Usage
-----
    python3 make_test_world.py [seed] [--output path]
    python3 make_test_world.py 42 --output worlds/seed_42.json

    # Generate several seeds at once
    python3 make_test_world.py 42 137 1000 9999 --output-dir worlds/

If no seed is given, generates seed 42 and prints to stdout.
"""

from __future__ import annotations

import json
import math
import sys
import os
from pathlib import Path


def convert(seed: int) -> dict:
    """
    Build a thin_sim base_world dict from sim_proxy's synthetic world.

    sim_proxy world format:
        archs: [{cx, cy, cz, shelf_r, peaks:[{h}]}]
        plateau_edges: [[a,b]]
        reach_arch, lattice_arch: int
        substrate: [{crops:{primary_crop, primary_yield, secondary_crop}, ...}]

    thin_sim base_world format:
        n, reach_arch, lattice_arch, seed
        archs: [{index, lat, size, shelf_r, peak_count, potential}]
        adj: [[neighbours]]
        substrate: [{primary_crop, primary_yield, secondary_crop, total_trade_value}]
        names: [str]
    """
    from sim_proxy import generate_test_world, Mulberry32

    proxy_world = generate_test_world(seed=seed)
    archs_raw   = proxy_world["archs"]
    edges       = proxy_world["plateau_edges"]
    reach_arch  = proxy_world["reach_arch"]
    lattice_arch = proxy_world["lattice_arch"]
    substrate_raw = proxy_world.get("substrate", [])
    N = len(archs_raw)

    # Potential — same formula as run_headless.gd Phase-1 potential computation.
    rng = Mulberry32((seed if seed != 0 else 42) * 31 + 1066)
    potentials: list[float] = []
    for arch in archs_raw:
        peaks   = arch["peaks"]
        p_count = len(peaks)
        sz      = arch["shelf_r"] / 0.12
        avg_h   = 0.0
        if p_count > 0:
            ISLAND_MAX_HEIGHT = 3000.0
            for pk in peaks:
                avg_h += pk["h"]
            avg_h /= float(p_count) * ISLAND_MAX_HEIGHT
        pot = (
            float(p_count) / 20.0 * 0.4
            + avg_h * 0.3
            + sz / 2.2 * 0.3
        ) * (0.6 + rng.next_float() * 0.4)
        potentials.append(pot)

    # Arch list in thin_sim format
    archs_out: list[dict] = []
    for k, arch in enumerate(archs_raw):
        cy  = max(-1.0, min(1.0, arch["cy"]))
        lat = round(math.degrees(math.asin(cy)), 2)
        archs_out.append({
            "index":      k,
            "lat":        lat,
            "size":       round(arch["shelf_r"] / 0.12, 3),
            "shelf_r":    arch["shelf_r"],
            "peak_count": len(arch["peaks"]),
            "potential":  round(potentials[k], 4),
        })

    # Adjacency list from plateau_edges
    adj: list[list[int]] = [[] for _ in range(N)]
    for edge in edges:
        a, b = edge[0], edge[1]
        adj[a].append(b)
        adj[b].append(a)

    # Substrate in thin_sim format
    substrate_out: list[dict] = []
    for k in range(N):
        s = substrate_raw[k] if k < len(substrate_raw) else {}
        crops = s.get("crops", {})
        trade = s.get("trade_goods", {})
        substrate_out.append({
            "primary_crop":       crops.get("primary_crop",   "emmer"),
            "primary_yield":      crops.get("primary_yield",  0.5),
            "secondary_crop":     crops.get("secondary_crop", None),
            "total_trade_value":  trade.get("total_trade_value", 0.0),
        })

    # Names (synthetic)
    names = [f"Arch {k}" for k in range(N)]
    names[reach_arch]   = "The Reach"
    names[lattice_arch] = "The Lattice"

    return {
        "seed":          seed,
        "n":             N,
        "reach_arch":    reach_arch,
        "lattice_arch":  lattice_arch,
        "archs":         archs_out,
        "plateau_edges": edges,
        "adj":           adj,
        "substrate":     substrate_out,
        "names":         names,
    }


def main() -> None:
    args = sys.argv[1:]

    output_dir  = ""
    output_file = ""
    seeds: list[int] = []

    i = 0
    while i < len(args):
        if args[i] == "--output" and i + 1 < len(args):
            output_file = args[i + 1]; i += 2
        elif args[i] == "--output-dir" and i + 1 < len(args):
            output_dir = args[i + 1]; i += 2
        else:
            try:
                seeds.append(int(args[i]))
            except ValueError:
                print(f"Ignoring unrecognized argument: {args[i]}", file=sys.stderr)
            i += 1

    if not seeds:
        seeds = [42]

    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    for seed in seeds:
        world = convert(seed)
        js    = json.dumps(world, indent="\t")

        if output_dir:
            path = os.path.join(output_dir, f"seed_{seed}.json")
            with open(path, "w") as f:
                f.write(js)
            print(f"Wrote {path}")
        elif output_file:
            with open(output_file, "w") as f:
                f.write(js)
            print(f"Wrote {output_file}")
        else:
            print(js)


if __name__ == "__main__":
    main()
