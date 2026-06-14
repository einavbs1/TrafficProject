"""Launch desktop GUI (kept at project root for convenience)."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).parent / "gui" / "flowgrid_gui.py"), run_name="__main__")
