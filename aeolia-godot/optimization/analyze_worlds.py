"""
Aeolia world JSON comparative analysis.
Reads seed_*.json (worlds/) and loss_breakdown.json (results/) and prints a full table.

Notes on great-circle distances:
  World JSONs have lat but no lon, so mean pairwise GC distances and the
  min cross-faction GC distance are taken from precomputed values in
  loss_breakdown.json (details.lattice_density.mean_dist_rad,
  details.reach_spread.mean_dist_rad, details.civ_gap.min_cross_dist_rad).
  Values in radians; multiply by 6371 for km.
"""

import json
import os
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
WORLDS_DIR = os.path.join(BASE, 'worlds')
RESULTS_DIR = os.path.join(BASE, 'results')

SEEDS = [17, 42, 97, 137, 256]
MINERALS = ['Cu', 'Au', 'Pu']
R_EARTH_KM = 6371.0


def load_world(seed):
    path = os.path.join(WORLDS_DIR, f'seed_{seed}.json')
    with open(path) as f:
        return json.load(f)


def load_loss():
    path = os.path.join(RESULTS_DIR, 'loss_breakdown.json')
    with open(path) as f:
        return json.load(f)


def analyse_seed(seed, world, loss_detail):
    n = world['n']
    states = world['states']
    substrate = world['substrate']

    # --- faction membership ---
    reach_idx = [i for i, s in enumerate(states) if s['faction'] == 'reach']
    lattice_idx = [i for i, s in enumerate(states) if s['faction'] == 'lattice']
    unknown_idx = [i for i, s in enumerate(states) if s['faction'] == 'unknown']

    n_reach = len(reach_idx)
    n_lattice = len(lattice_idx)
    n_unknown = len(unknown_idx)

    # --- latitude stats ---
    def mean_abs_lat(indices):
        if not indices:
            return float('nan')
        return sum(substrate[i]['abs_latitude'] for i in indices) / len(indices)

    reach_mean_lat = mean_abs_lat(reach_idx)
    lattice_mean_lat = mean_abs_lat(lattice_idx)

    # --- mineral breakdown ---
    def mineral_counts(indices):
        counts = {m: 0 for m in MINERALS}
        for i in indices:
            mins = substrate[i]['minerals']
            for m in MINERALS:
                if mins.get(m, False):
                    counts[m] += 1
        return counts

    reach_mins = mineral_counts(reach_idx)
    lattice_mins = mineral_counts(lattice_idx)

    # --- crop distribution ---
    def crop_counts(indices):
        counts = defaultdict(int)
        for i in indices:
            pc = substrate[i].get('primary_crop')
            sc = substrate[i].get('secondary_crop')
            if pc:
                counts[pc] += 1
            if sc:
                counts[sc] += 1
        return dict(sorted(counts.items()))

    reach_crops = crop_counts(reach_idx)
    lattice_crops = crop_counts(lattice_idx)

    # --- great-circle distances from loss_breakdown ---
    lattice_mean_dist_rad = loss_detail.get('lattice_density', {}).get('mean_dist_rad', float('nan'))
    reach_mean_dist_rad = loss_detail.get('reach_spread', {}).get('mean_dist_rad', float('nan'))
    min_cross_dist_rad = loss_detail.get('civ_gap', {}).get('min_cross_dist_rad', float('nan'))

    lattice_mean_dist_km = lattice_mean_dist_rad * R_EARTH_KM
    reach_mean_dist_km = reach_mean_dist_rad * R_EARTH_KM
    min_cross_dist_km = min_cross_dist_rad * R_EARTH_KM

    return {
        'seed': seed,
        'n_total': n,
        'n_reach': n_reach,
        'n_lattice': n_lattice,
        'n_unknown': n_unknown,
        'reach_mean_abs_lat': reach_mean_lat,
        'lattice_mean_abs_lat': lattice_mean_lat,
        'reach_Cu': reach_mins['Cu'],
        'reach_Au': reach_mins['Au'],
        'reach_Pu': reach_mins['Pu'],
        'lattice_Cu': lattice_mins['Cu'],
        'lattice_Au': lattice_mins['Au'],
        'lattice_Pu': lattice_mins['Pu'],
        'reach_crops': reach_crops,
        'lattice_crops': lattice_crops,
        'reach_mean_dist_km': reach_mean_dist_km,
        'lattice_mean_dist_km': lattice_mean_dist_km,
        'min_cross_dist_km': min_cross_dist_km,
        'reach_mean_dist_rad': reach_mean_dist_rad,
        'lattice_mean_dist_rad': lattice_mean_dist_rad,
        'min_cross_dist_rad': min_cross_dist_rad,
    }


def print_section(title):
    print()
    print('=' * 80)
    print(f'  {title}')
    print('=' * 80)


def fmt(v, w=10, d=3):
    if isinstance(v, float):
        return f'{v:{w}.{d}f}'
    return f'{str(v):{w}}'


def main():
    loss = load_loss()
    results = []
    for seed in SEEDS:
        world = load_world(seed)
        ld = loss[str(seed)]['details']
        r = analyse_seed(seed, world, ld)
        r['loss_total'] = loss[str(seed)]['total']
        r['loss_components'] = loss[str(seed)]['components']
        results.append(r)

    # ---------------------------------------------------------------
    # TABLE 1: Arch counts and faction split
    # ---------------------------------------------------------------
    print_section('TABLE 1 — Arch counts & faction split')
    hdr = f"{'Seed':>6} {'Total':>7} {'Reach':>7} {'Lattice':>9} {'Unknown':>9}"
    print(hdr)
    print('-' * len(hdr))
    for r in results:
        print(f"{r['seed']:>6} {r['n_total']:>7} {r['n_reach']:>7} {r['n_lattice']:>9} {r['n_unknown']:>9}")

    # ---------------------------------------------------------------
    # TABLE 2: Per-faction mean absolute latitude
    # ---------------------------------------------------------------
    print_section('TABLE 2 — Per-faction mean absolute latitude (degrees)')
    hdr = f"{'Seed':>6} {'Reach mean |lat|':>18} {'Lattice mean |lat|':>20}"
    print(hdr)
    print('-' * len(hdr))
    for r in results:
        print(f"{r['seed']:>6} {r['reach_mean_abs_lat']:>18.4f} {r['lattice_mean_abs_lat']:>20.4f}")

    # ---------------------------------------------------------------
    # TABLE 3: Per-faction mineral breakdown (Cu, Au, Pu; Fe omitted)
    # ---------------------------------------------------------------
    print_section('TABLE 3 — Per-faction mineral breakdown (arch count with mineral; Fe omitted)')
    hdr = (f"{'Seed':>6} "
           f"{'R:Cu':>6} {'R:Au':>6} {'R:Pu':>6}  "
           f"{'L:Cu':>6} {'L:Au':>6} {'L:Pu':>6}")
    print(hdr)
    print('-' * len(hdr))
    for r in results:
        print(f"{r['seed']:>6} "
              f"{r['reach_Cu']:>6} {r['reach_Au']:>6} {r['reach_Pu']:>6}  "
              f"{r['lattice_Cu']:>6} {r['lattice_Au']:>6} {r['lattice_Pu']:>6}")

    # ---------------------------------------------------------------
    # TABLE 4: Per-faction crop distribution (all crops seen)
    # ---------------------------------------------------------------
    print_section('TABLE 4 — Per-faction crop distribution (primary + secondary slot counts)')

    # Collect all crop types across all seeds
    all_crops = set()
    for r in results:
        all_crops.update(r['reach_crops'].keys())
        all_crops.update(r['lattice_crops'].keys())
    all_crops = sorted(all_crops)

    for r in results:
        print(f"\n  Seed {r['seed']}:")
        print(f"    {'Crop':<20} {'Reach':>8} {'Lattice':>8}")
        print(f"    {'-'*38}")
        for crop in all_crops:
            rv = r['reach_crops'].get(crop, 0)
            lv = r['lattice_crops'].get(crop, 0)
            if rv > 0 or lv > 0:
                print(f"    {crop:<20} {rv:>8} {lv:>8}")

    # ---------------------------------------------------------------
    # TABLE 5: Mean pairwise GC distance within each faction
    # ---------------------------------------------------------------
    print_section('TABLE 5 — Mean pairwise GC distance within faction (from loss_breakdown)')
    print('  (Source: details.reach_spread.mean_dist_rad / details.lattice_density.mean_dist_rad)')
    hdr = (f"{'Seed':>6} "
           f"{'Reach dist (rad)':>18} {'Reach dist (km)':>16}  "
           f"{'Lattice dist (rad)':>20} {'Lattice dist (km)':>18}")
    print(hdr)
    print('-' * len(hdr))
    for r in results:
        print(f"{r['seed']:>6} "
              f"{r['reach_mean_dist_rad']:>18.6f} {r['reach_mean_dist_km']:>16.1f}  "
              f"{r['lattice_mean_dist_rad']:>20.6f} {r['lattice_mean_dist_km']:>18.1f}")

    # ---------------------------------------------------------------
    # TABLE 6: Min cross-faction GC distance
    # ---------------------------------------------------------------
    print_section('TABLE 6 — Min cross-faction GC distance (civilizational gap; from loss_breakdown)')
    print('  (Source: details.civ_gap.min_cross_dist_rad)')
    hdr = f"{'Seed':>6} {'Min cross dist (rad)':>22} {'Min cross dist (km)':>22}"
    print(hdr)
    print('-' * len(hdr))
    for r in results:
        print(f"{r['seed']:>6} {r['min_cross_dist_rad']:>22.6f} {r['min_cross_dist_km']:>22.1f}")

    # ---------------------------------------------------------------
    # TABLE 7: Loss breakdown — total + all geo-relevant components
    # ---------------------------------------------------------------
    print_section('TABLE 7 — Per-seed total loss & individual component scores')
    geo_components = [
        'lattice_density', 'reach_spread', 'lattice_latitude', 'reach_latitude',
        'lattice_shelf', 'civ_gap', 'peak_asymmetry', 'edge_topology',
        'climate_crop', 'yield_asymmetry',
    ]
    all_components = list(results[0]['loss_components'].keys())

    # Header
    col_w = 14
    seed_col = 8
    row0 = f"{'Component':<28}"
    for r in results:
        row0 += f"{'seed_'+str(r['seed']):>{col_w}}"
    print(row0)
    print('-' * (28 + col_w * len(results)))

    # Total loss row
    row = f"{'TOTAL':<28}"
    for r in results:
        row += f"{r['loss_total']:>{col_w}.6f}"
    print(row)
    print()

    for comp in all_components:
        row = f"{comp:<28}"
        for r in results:
            val = r['loss_components'].get(comp, float('nan'))
            row += f"{val:>{col_w}.6f}"
        print(row)

    # ---------------------------------------------------------------
    # Summary note
    # ---------------------------------------------------------------
    print()
    print('  NOTE: GC distances computed by the Godot sim engine (no lon in exported JSON).')
    print('        mean_dist_rad values from loss_breakdown details; 1 rad ≈ 6371 km.')
    print()


if __name__ == '__main__':
    main()
