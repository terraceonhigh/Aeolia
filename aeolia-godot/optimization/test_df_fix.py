#!/usr/bin/env python3
"""Quick test: run all 9 seeds with default params, check DF targeting."""
import json, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
from sim_proxy_v2 import SimParams, simulate

seeds = [216089, 42, 51, 66, 73, 11, 17, 74, 97]
p = SimParams()

for s in seeds:
    fname = f"worlds/candidate_{s:07d}.json"
    if not os.path.exists(fname):
        print(f"seed {s:>6d}: FILE NOT FOUND ({fname})")
        continue

    w = json.load(open(fname))
    N = w["n"]
    r = simulate(w, p)
    df = r.get("df_year")
    a = r.get("df_arch")
    b = r.get("df_detector")
    hegs = r.get("hegemons", [])
    between = (a in hegs and b in hegs) if df is not None else False
    print(f"seed {s:>6d}: N={N} df_year={str(df):>6s} a={str(a):>3s} b={str(b):>3s} between={between} hegemons={hegs}")
