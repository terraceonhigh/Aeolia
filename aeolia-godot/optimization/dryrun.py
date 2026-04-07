"""One-trial dry run to catch errors before the full 500-trial run."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sim_proxy import SimParams, DEFAULT_PARAMS, generate_test_world, simulate, PARAM_BOUNDS
from loss import compute_loss

world = generate_test_world(seed=42)
world["_opt_seed"] = 42
result = simulate(world, DEFAULT_PARAMS, seed=42)
lr = compute_loss(result, substrate=result.get("substrate"), world=world, params=DEFAULT_PARAMS)
print("total =", round(lr.total, 4))
print(lr.summary())
print("minerals[0] =", result["minerals"][0])
print("PARAM_BOUNDS count:", len(PARAM_BOUNDS))
print("adj[0] =", result["adj"][0][:4], "...")
print("OK")
