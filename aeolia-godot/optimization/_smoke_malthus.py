"""Smoke test: seed 216089 after Malthusian clamp implementation."""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from sim_proxy_v2 import DEFAULT_PARAMS, simulate, load_world

base = os.path.dirname(os.path.abspath(__file__))
candidates = (
    glob.glob(os.path.join(base, "worlds/candidate_0216089.json"))
    + glob.glob(os.path.join(base, "worlds/*216089*.json"))
)
if not candidates:
    print("ERROR: no world file found for seed 216089")
    available = os.listdir("worlds") if os.path.isdir("worlds") else []
    print("Available:", available[:10])
    sys.exit(1)

world = load_world(candidates[0])
result = simulate(world, DEFAULT_PARAMS)

hegemons = result.get("hegemons", [])
polities = {p["core"]: p for p in result.get("polities", [])}

print("=== Smoke test: seed 216089 ===")
print(f"df_year:      {result.get('df_year')}")
print(f"n_hegemons:   {len(hegemons)}")
for h in hegemons:
    tech = polities[h]["tech"] if h in polities else "?"
    culture = result.get("hegemon_cultures", {}).get(h, "?")
    print(f"  hegemon arch={h}  tech={tech:.2f}  culture={culture}")
print(f"n_polities:   {result.get('n_polities')}")
print(f"crash:        False")
