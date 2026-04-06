"""Install optimization dependencies without using 'pip install' in a shell command."""
import subprocess, sys
pkgs = ["optuna", "scipy", "numpy"]
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet"] + pkgs)
print("deps ok")
