"""Project paths — all code reads locations from here."""
from pathlib import Path

# flowgrid/paths.py -> Old_Versions/DQN_Agent/flowgrid/paths.py; project root
# is three levels up (flowgrid -> DQN_Agent -> Old_Versions -> TrafficProject)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "SharedData"
MAPS_DATA_DIR = DATA_DIR / "maps"
DEFAULTS_DIR = DATA_DIR / "defaults"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = DATA_DIR / "reports"
COMPARISON_HISTORY_PATH = REPORTS_DIR / "comparison_history.json"
DEFAULT_POLICY_CONFIG_PATH = DEFAULTS_DIR / "dqn_policy_config.yaml"
DQN_TRAINING_LOG_PATH = REPORTS_DIR / "dqn_training_log.jsonl"
LOGS_DIR = PROJECT_ROOT / "logs"
EPISODE_TRANSPARENCY_LOG_PATH = LOGS_DIR / "episode_transparency.log"
LEGACY_DIR = PROJECT_ROOT / "legacy"

# Training: one DQN checkpoint per saved map (not per road / lane).
# Each map = full intersection + routes + traffic → separate policy file.
