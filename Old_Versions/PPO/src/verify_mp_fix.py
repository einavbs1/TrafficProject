"""
Quick MP verification: runs evaluate_mp_on_seed on 2 seeds per traffic level
to confirm the halting-vehicle fix + TL re-assertion + dynamic MIN_GREEN work.
Takes ~5 minutes. Run this while the main training job is in progress.
"""
import os
_MAPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SharedData", "maps", "flowgrid")
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from evaluate_models import evaluate_mp_on_seed

ROUTE_FILES = {
    "Low":    os.path.join(_MAPS_DIR, "routes.rou.xml"),
    "Medium": os.path.join(_MAPS_DIR, "routes_hard.rou.xml"),
    "High":   os.path.join(_MAPS_DIR, "routes_extreme.rou.xml"),
}
SEEDS = [1337, 42]  # seed 1337 worked before; seed 42 was broken

print("=" * 60)
print("MAX PRESSURE VERIFICATION (halting vehicles + TL re-assert)")
print("=" * 60)

for label, route in ROUTE_FILES.items():
    print(f"\n[{label} traffic]")
    for seed in SEEDS:
        df = evaluate_mp_on_seed(route_file=route, seed=seed, use_gui=False)
        total_wait  = df["system_total_waiting_time"].sum()
        peak_wait   = df["episode_peak_max_wait"].max()
        switches    = df["total_switches"].max()
        arrived     = df["total_arrived"].max()
        print(f"  Seed {seed:5d} | Wait: {total_wait:>14,.0f} | Peak: {peak_wait:>8.1f}s | Switches: {switches:4d} | Arrived: {arrived:4d}")

print("\nDone.")
