"""Verify real Godot world loads and runs through loss without errors."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sim_proxy import DEFAULT_PARAMS, load_godot_world, simulate, PARAM_BOUNDS
from loss import compute_loss

WORLDS_DIR = Path(__file__).parent / "worlds"

for seed in [42, 17]:
    path = WORLDS_DIR / f"seed_{seed}.json"
    world = load_godot_world(str(path))
    world["_opt_seed"] = seed
    print(f"seed={seed}: n={world['n']}  reach={world['reach_arch']}  "
          f"lattice={world['lattice_arch']}  df_year={world['df_year']}")
    result = simulate(world, DEFAULT_PARAMS, seed=seed)
    lr = compute_loss(result, substrate=result.get("substrate"), world=world, params=DEFAULT_PARAMS)
    print(f"  total={round(lr.total, 4)}  components: {lr.summary()}")

print(f"\nPARAM_BOUNDS count: {len(PARAM_BOUNDS)}")
print("OK")
