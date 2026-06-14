"""Build a deterministic demand file so baseline and DQN see the same vehicles."""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class CompareDemandManifest:
    routes_path: str
    sumocfg_path: str
    car_count: int
    bus_count: int
    emergency_count: int

    @property
    def total_count(self) -> int:
        return self.car_count + self.bus_count + self.emergency_count


def _classify_type(type_id: str) -> str:
    tid = (type_id or "").lower()
    if tid == "emergency" or "emergency" in tid:
        return "emergency"
    if tid == "bus" or tid in ("coach", "tram", "trolleybus"):
        return "bus"
    return "car"


def ensure_fixed_compare_demand(
    map_dir: Path,
    *,
    seed: int,
    duration_seconds: float,
    resolution_seconds: float = 1.0,
) -> CompareDemandManifest:
    """
    Expand probabilistic <flow> entries into fixed <vehicle depart="..."> times using ``seed``.
    Cached under map_dir/.compare_cache/.
    """
    map_dir = Path(map_dir)
    source_routes = map_dir / "routes.rou.xml"
    if not source_routes.is_file():
        raise FileNotFoundError(f"Missing routes: {source_routes}")

    cache_dir = map_dir / ".compare_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dur_tag = int(duration_seconds)
    routes_out = cache_dir / f"compare_seed{seed}_dur{dur_tag}.rou.xml"
    sumocfg_out = cache_dir / f"compare_seed{seed}_dur{dur_tag}.sumocfg"

    if routes_out.is_file() and sumocfg_out.is_file():
        return _manifest_from_routes(routes_out, sumocfg_out)

    tree = ET.parse(source_routes)
    root = tree.getroot()
    rng = np.random.default_rng(int(seed))

    static_lines: list[str] = []
    vehicles: list[str] = []
    car_n = bus_n = emg_n = 0
    seq: dict[str, int] = {}

    for child in root:
        tag = child.tag
        if tag == "vType":
            static_lines.append(ET.tostring(child, encoding="unicode").strip())
        elif tag == "route":
            static_lines.append(ET.tostring(child, encoding="unicode").strip())
        elif tag != "flow":
            continue

        flow_id = child.get("id", "flow")
        vtype = child.get("type", "car")
        route_id = child.get("route", "")
        prob = float(child.get("probability", child.get("prob", "0")))
        begin = int(float(child.get("begin", "0")))
        end = int(float(child.get("end", str(duration_seconds))))
        end = min(end, int(duration_seconds))
        depart_lane = child.get("departLane")
        vclass = _classify_type(vtype)

        t = begin
        while t < end:
            if rng.random() < prob:
                seq[flow_id] = seq.get(flow_id, 0) + 1
                vid = f"{flow_id}.{seq[flow_id]}"
                lane_attr = f' departLane="{depart_lane}"' if depart_lane is not None else ""
                vehicles.append(
                    f'    <vehicle id="{vid}" type="{vtype}" route="{route_id}" depart="{t:.1f}"{lane_attr}/>'
                )
                if vclass == "emergency":
                    emg_n += 1
                elif vclass == "bus":
                    bus_n += 1
                else:
                    car_n += 1
            t += float(resolution_seconds)

    routes_body = "\n".join(static_lines + vehicles)
    routes_out.write_text(
        f"<routes>\n{routes_body}\n</routes>\n",
        encoding="utf-8",
    )

    net_name = "network.net.xml"
    sumocfg_out.write_text(
        f"""<configuration>
    <input>
        <net-file value="../network.net.xml"/>
        <route-files value="{routes_out.name}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="{dur_tag + 60}"/>
    </time>
</configuration>
""",
        encoding="utf-8",
    )

    return CompareDemandManifest(
        routes_path=str(routes_out.resolve()),
        sumocfg_path=str(sumocfg_out.resolve()),
        car_count=car_n,
        bus_count=bus_n,
        emergency_count=emg_n,
    )


def _manifest_from_routes(routes_path: Path, sumocfg_path: Path) -> CompareDemandManifest:
    text = routes_path.read_text(encoding="utf-8")
    car_n = bus_n = emg_n = 0
    for m in re.finditer(r'<vehicle[^>]+type="([^"]+)"', text):
        kind = _classify_type(m.group(1))
        if kind == "emergency":
            emg_n += 1
        elif kind == "bus":
            bus_n += 1
        else:
            car_n += 1
    return CompareDemandManifest(
        routes_path=str(routes_path.resolve()),
        sumocfg_path=str(sumocfg_path.resolve()),
        car_count=car_n,
        bus_count=bus_n,
        emergency_count=emg_n,
    )
