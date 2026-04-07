"""Launcher: cd to optimization dir and run the optimizer."""
import os, sys
from pathlib import Path
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))
exec(open(Path(__file__).parent / "run_optimization.py").read())
run()
