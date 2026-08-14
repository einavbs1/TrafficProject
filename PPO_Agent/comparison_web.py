"""Launch the FlowGrid PPO web app (kept here for convenience)."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).parent / "scripts" / "comparison_web" / "server.py"), run_name="__main__")
