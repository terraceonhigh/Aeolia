#!/usr/bin/env python3
"""Quick inspection of seed 216089 world data."""
import json

d = json.load(open("worlds/candidate_0216089.json"))
from collections import Counter
crops = Counter(s["primary_crop"] for s in d["substrate"])
print("Crops:", dict(crops))

shelves = [a.get("shelf_r", 0) for a in d["archs"]]
print("Shelf range:", min(shelves), "-", max(shelves))

pu_archs = [i for i, s in enumerate(d["substrate"]) if s["minerals"].get("Pu")]
cu_archs = [i for i, s in enumerate(d["substrate"]) if s["minerals"].get("Cu")]
au_archs = [i for i, s in enumerate(d["substrate"]) if s["minerals"].get("Au")]
print("Pu archs:", pu_archs)
print("Cu archs:", cu_archs)
print("Au archs:", au_archs)

print("Reach crop:", d["substrate"][d["reach_arch"]]["primary_crop"])
print("Lattice crop:", d["substrate"][d["lattice_arch"]]["primary_crop"])

tides = [s["tidal_range"] for s in d["substrate"]]
print("Tidal range:", min(tides), "-", max(tides))

# Check which archs have C potential (shelf_r >= 0.04)
c_eligible = [(i, a["shelf_r"], d["substrate"][i]["tidal_range"])
              for i, a in enumerate(d["archs"]) if a.get("shelf_r", 0) >= 0.04]
print(f"\nC-eligible archs ({len(c_eligible)}):")
for i, sr, tr in sorted(c_eligible, key=lambda x: -x[1]*x[2]):
    print(f"  arch {i}: shelf_r={sr:.3f} tidal={tr:.1f} richness_raw={sr*tr:.3f} crop={d['substrate'][i]['primary_crop']}")
