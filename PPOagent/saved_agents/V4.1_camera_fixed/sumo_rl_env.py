"""
Import shim -- DO NOT put real logic here.

evaluate_models.py (in src/) hardcodes `from sumo_rl_env import ...`. Because
this folder is inserted at the front of sys.path, that import resolves to
THIS file instead of src/sumo_rl_env.py, so evaluation uses the camera-range
environment (sumo_rl_env_V4_1_camera.py) that the model was actually trained
on, instead of silently falling back to the full-lane-visibility version.
"""
from sumo_rl_env_V4_1_camera import create_sumo_env, SwitchOrKeepWrapper, MultiRouteWrapper
