"""Save, load, and list map presets. Each map has its own DQN (dqn_policy.pth)."""
from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from flowgrid.core.phasing_schemes import DEFAULT_SCHEME
from flowgrid.maps.map_builder import DEFAULT_FLOWS, build_map_into_directory
from flowgrid.maps.policy_paths import resolved_policy_path
from flowgrid.paths import DEFAULTS_DIR, MAPS_DATA_DIR, PROJECT_ROOT

REGISTRY_PATH = MAPS_DATA_DIR / "registry.json"
DEFAULT_MAP_ID = "flowgrid"


@dataclass
class MapPreset:
    id: str
    display_name: str
    arm_length: int
    flows: dict[str, float]
    sumocfg_path: str
    policy_path: str
    created_at: str
    phasing_scheme: str = DEFAULT_SCHEME
    separate_right_turn: bool = True
    lanes_per_approach: int = 4
    baseline_through_seconds: float = 60.0
    baseline_left_to_through_ratio: float = 0.60

    @property
    def directory(self) -> Path:
        return MAPS_DATA_DIR / self.id

    def abs_sumocfg(self) -> str:
        p = Path(self.sumocfg_path)
        if p.is_absolute():
            return str(p)
        return str((PROJECT_ROOT / p).resolve())

    def abs_policy(self) -> str:
        p = Path(self.policy_path)
        if p.is_absolute():
            return str(p)
        return str((PROJECT_ROOT / p).resolve())


def slugify_map_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "map"


def _slugify(name: str) -> str:
    return slugify_map_name(name)


def _load_registry() -> list[dict]:
    MAPS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        return []
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def _save_registry(entries: list[dict]) -> None:
    MAPS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _preset_from_entry(e: dict) -> MapPreset:
    defaults = {
        "phasing_scheme": DEFAULT_SCHEME,
        "separate_right_turn": True,
        "lanes_per_approach": 4,
        "baseline_through_seconds": 60.0,
        "baseline_left_to_through_ratio": 0.60,
    }
    merged = {**defaults, **e}
    if "baseline_left_to_through_ratio" not in merged and "baseline_left_seconds" in merged:
        through = float(merged.get("baseline_through_seconds", 60.0))
        left = float(merged["baseline_left_seconds"])
        merged["baseline_left_to_through_ratio"] = left / through if through > 0 else 0.60
    merged.pop("baseline_left_seconds", None)
    return MapPreset(**{k: merged[k] for k in MapPreset.__dataclass_fields__})


def list_saved_maps() -> list[MapPreset]:
    return [_preset_from_entry(e) for e in _load_registry()]


def get_map(map_id: str) -> MapPreset | None:
    for p in list_saved_maps():
        if p.id == map_id:
            return p
    return None


def ensure_default_map() -> None:
    if list_saved_maps():
        _migrate_registry_paths()
        return
    legacy_cfg = PROJECT_ROOT / "data" / "defaults" / "flowgrid.sumocfg"
    if not legacy_cfg.exists():
        legacy_cfg = PROJECT_ROOT / "flowgrid.sumocfg"
    if not legacy_cfg.exists():
        return
    rel_cfg = str(legacy_cfg.relative_to(PROJECT_ROOT)).replace("\\", "/")
    policy = PROJECT_ROOT / "data" / "defaults" / "dqn_policy.pth"
    if not policy.exists():
        policy = PROJECT_ROOT / "dqn_policy.pth"
    rel_policy = str(policy.relative_to(PROJECT_ROOT)).replace("\\", "/") if policy.exists() else "data/maps/flowgrid/dqn_policy.pth"
    _save_registry(
        [
            {
                "id": "flowgrid",
                "display_name": "Default (flowgrid)",
                "arm_length": 500,
                "flows": DEFAULT_FLOWS,
                "sumocfg_path": rel_cfg,
                "policy_path": rel_policy,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
    )


def _migrate_registry_paths() -> None:
    """Fix old paths after folder reorganization."""
    entries = _load_registry()
    changed = False
    for e in entries:
        for key in ("sumocfg_path", "policy_path"):
            p = e.get(key, "")
            if p.startswith("maps/") and not p.startswith("data/maps/"):
                e[key] = "data/" + p
                changed = True
            if key == "sumocfg_path" and p == "flowgrid.sumocfg":
                e[key] = "data/defaults/flowgrid.sumocfg"
                changed = True
            if key == "policy_path" and p == "dqn_policy.pth":
                e[key] = "data/defaults/dqn_policy.pth"
                changed = True
    if changed:
        _save_registry(entries)


def sync_defaults_from_map(map_dir: Path) -> None:
    map_dir = Path(map_dir)
    DEFAULTS_DIR.mkdir(parents=True, exist_ok=True)
    pairs = (
        ("network.net.xml", "my_net.net.xml"),
        ("routes.rou.xml", "flowgrid.rou.xml"),
        ("connections.con.xml", "my_connections.con.xml"),
        ("edges.edg.xml", "my_edges.edg.xml"),
        ("nodes.nod.xml", "my_nodes.nod.xml"),
    )
    for src_name, dst_name in pairs:
        src = map_dir / src_name
        if src.is_file():
            shutil.copy2(src, DEFAULTS_DIR / dst_name)
    (DEFAULTS_DIR / "flowgrid.sumocfg").write_text(
        """<configuration>
    <input>
        <net-file value="my_net.net.xml"/>
        <route-files value="flowgrid.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>
""",
        encoding="utf-8",
    )


def save_map(
    display_name: str,
    arm_length: int,
    flows: dict[str, float],
    overwrite: bool = False,
    *,
    map_id: str | None = None,
    phasing_scheme: str = DEFAULT_SCHEME,
    separate_right_turn: bool = True,
    lanes_per_approach: int = 4,
    baseline_through_seconds: float = 60.0,
    baseline_left_to_through_ratio: float = 0.60,
    sync_defaults: bool = False,
) -> MapPreset:
    MAPS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    base_id = _slugify(display_name)
    map_id = map_id or base_id
    entries = _load_registry()
    existing_ids = {e["id"] for e in entries}

    if map_id in existing_ids and not overwrite:
        n = 2
        while f"{base_id}_{n}" in existing_ids:
            n += 1
        map_id = f"{base_id}_{n}"

    out_dir = MAPS_DATA_DIR / map_id
    if out_dir.exists() and overwrite:
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    build_map_into_directory(
        out_dir,
        arm_length=arm_length,
        flows=flows,
        lanes_per_approach=lanes_per_approach,
        separate_right_slip=separate_right_turn and lanes_per_approach < 4,
        baseline_through_seconds=float(baseline_through_seconds),
        baseline_left_to_through_ratio=float(baseline_left_to_through_ratio),
    )

    sumocfg_rel = str((out_dir / "map.sumocfg").relative_to(PROJECT_ROOT)).replace("\\", "/")
    policy_rel = str((out_dir / "dqn_policy.pth").relative_to(PROJECT_ROOT)).replace("\\", "/")

    preset = MapPreset(
        id=map_id,
        display_name=display_name.strip(),
        arm_length=arm_length,
        flows=dict(flows),
        sumocfg_path=sumocfg_rel,
        policy_path=policy_rel,
        created_at=datetime.now(timezone.utc).isoformat(),
        phasing_scheme=phasing_scheme,
        separate_right_turn=separate_right_turn,
        lanes_per_approach=lanes_per_approach,
        baseline_through_seconds=float(baseline_through_seconds),
        baseline_left_to_through_ratio=float(baseline_left_to_through_ratio),
    )

    entries = [e for e in entries if e["id"] != map_id]
    entries.append(asdict(preset))
    _save_registry(entries)
    if sync_defaults or map_id == DEFAULT_MAP_ID:
        sync_defaults_from_map(out_dir)
    return preset


def delete_map(map_id: str) -> bool:
    entries = _load_registry()
    new_entries = [e for e in entries if e["id"] != map_id]
    if len(new_entries) == len(entries):
        return False
    _save_registry(new_entries)
    map_dir = MAPS_DATA_DIR / map_id
    if map_dir.is_dir():
        shutil.rmtree(map_dir)
    return True


def list_maps_for_gui() -> list[dict]:
    ensure_default_map()
    presets = list_saved_maps()
    presets.sort(key=lambda p: (0 if p.id == DEFAULT_MAP_ID else 1, p.display_name.lower()))
    return [
        {
            "id": p.id,
            "display_name": p.display_name,
            "sumocfg": p.abs_sumocfg(),
            "policy_path": p.abs_policy(),
            "policy_load_path": resolved_policy_path(p.abs_policy()),
            "arm_length": p.arm_length,
            "flows": p.flows,
            "phasing_scheme": p.phasing_scheme,
            "separate_right_turn": p.separate_right_turn,
            "lanes_per_approach": p.lanes_per_approach,
            "baseline_through_seconds": p.baseline_through_seconds,
            "baseline_left_to_through_ratio": p.baseline_left_to_through_ratio,
        }
        for p in presets
    ]
