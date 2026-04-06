"""Quick smoke-test: 1 trial, 2 seeds."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from sim_proxy import generate_test_world, simulate, DEFAULT_PARAMS
from loss import compute_loss

world = generate_test_world(seed=42)
result = simulate(world, DEFAULT_PARAMS, seed=42)
lr = compute_loss(result, substrate=result.get("substrate"))
print("loss =", round(lr.total, 4))
print(lr.summary())
print("states[0]:", result["states"][0])
print("df_year:", result.get("df_year"))
print("OK")
