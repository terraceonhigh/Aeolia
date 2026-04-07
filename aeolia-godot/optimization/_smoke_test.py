import sys
sys.path.insert(0, '.')
from sim_proxy import generate_test_world, simulate, DEFAULT_PARAMS, PARAM_BOUNDS
from loss import compute_loss
w = generate_test_world(seed=42)
r = simulate(w, DEFAULT_PARAMS, seed=42)
lr = compute_loss(r)
print("smoke-test OK, total loss:", round(lr.total, 4))
print("params:", len(PARAM_BOUNDS))
print("components:", {k: round(v, 4) for k, v in lr.components.items()})
