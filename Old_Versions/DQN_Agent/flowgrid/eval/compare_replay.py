"""Capture random baseline departures and replay the same vehicles for DQN compare."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import traci


@dataclass(frozen=True)
class DepartureRecord:
    vehicle_id: str
    type_id: str
    route_id: str
    depart: float
    depart_lane: str | None = None


@dataclass(frozen=True)
class CompareReplayManifest:
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


def ensure_compare_baseline_demand(map_dir: Path, inject_seconds: float) -> tuple[str, str]:
    """
    Routes file identical to the map except all <flow> elements stop at ``inject_seconds``.
    No new random vehicles after that time; the episode then drains the network.
    """
    map_dir = Path(map_dir)
    source_routes = map_dir / "routes.rou.xml"
    if not source_routes.is_file():
        raise FileNotFoundError(f"Missing routes: {source_routes}")

    cache_dir = map_dir / ".compare_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    inject_tag = int(inject_seconds)
    routes_out = cache_dir / f"compare_baseline_inject{inject_tag}.rou.xml"
    sumocfg_out = cache_dir / f"compare_baseline_inject{inject_tag}.sumocfg"

    if routes_out.is_file() and sumocfg_out.is_file():
        return str(routes_out.resolve()), str(sumocfg_out.resolve())

    tree = ET.parse(source_routes)
    root = tree.getroot()
    lines: list[str] = []
    for child in root:
        if child.tag == "flow":
            child.set("end", str(inject_tag))
            if child.get("begin") is None:
                child.set("begin", "0")
        lines.append(ET.tostring(child, encoding="unicode").strip())

    routes_out.write_text(f"<routes>\n" + "\n".join(lines) + "\n</routes>\n", encoding="utf-8")
    sumocfg_out.write_text(
        f"""<configuration>
    <input>
        <net-file value="../network.net.xml"/>
        <route-files value="{routes_out.name}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="{inject_tag + 7200}"/>
    </time>
</configuration>
""",
        encoding="utf-8",
    )
    return str(routes_out.resolve()), str(sumocfg_out.resolve())


def load_flow_metadata(source_routes: Path) -> dict[str, dict[str, str]]:
    """Map flow id -> route id and departLane from the map's routes.rou.xml."""
    meta: dict[str, dict[str, str]] = {}
    root = ET.parse(source_routes).getroot()
    for child in root:
        if child.tag != "flow":
            continue
        flow_id = child.get("id")
        if not flow_id:
            continue
        entry: dict[str, str] = {"route": child.get("route", "")}
        if child.get("departLane") is not None:
            entry["departLane"] = child.get("departLane", "")
        meta[flow_id] = entry
    return meta


def _flow_id_from_vehicle(vehicle_id: str) -> str | None:
    """SUMO flow vehicles look like ``f_ns_s.12`` -> flow ``f_ns_s``."""
    if "." not in vehicle_id:
        return None
    return vehicle_id.rsplit(".", 1)[0]


def _depart_lane_for_vehicle(
    vehicle_id: str, flow_meta: dict[str, dict[str, str]], *, at_depart: bool
) -> str | None:
    flow_id = _flow_id_from_vehicle(vehicle_id)
    if flow_id and flow_id in flow_meta:
        lane = flow_meta[flow_id].get("departLane")
        if lane is not None and lane != "":
            return str(lane)
    if not at_depart:
        return None
    try:
        lane_idx = traci.vehicle.getLaneIndex(vehicle_id)
        if lane_idx >= 0:
            return str(lane_idx)
    except traci.exceptions.TraCIException:
        pass
    return None


def capture_departed_micro_step(
    departures: list[DepartureRecord],
    seen_ids: set[str],
    flow_meta: dict[str, dict[str, str]],
) -> None:
    """Record vehicles that entered on this SUMO micro-step (correct depart lane)."""
    try:
        for vid in traci.simulation.getDepartedIDList():
            if vid in seen_ids:
                continue
            seen_ids.add(vid)
            route_id = traci.vehicle.getRouteID(vid)
            departures.append(
                DepartureRecord(
                    vehicle_id=vid,
                    type_id=traci.vehicle.getTypeID(vid),
                    route_id=route_id,
                    depart=float(traci.vehicle.getDeparture(vid)),
                    depart_lane=_depart_lane_for_vehicle(vid, flow_meta, at_depart=True),
                )
            )
    except traci.exceptions.TraCIException:
        return


def manifest_from_departures(departures: list[DepartureRecord]) -> CompareReplayManifest:
    car_n = bus_n = emg_n = 0
    for rec in departures:
        kind = _classify_type(rec.type_id)
        if kind == "emergency":
            emg_n += 1
        elif kind == "bus":
            bus_n += 1
        else:
            car_n += 1
    return CompareReplayManifest(
        routes_path="",
        sumocfg_path="",
        car_count=car_n,
        bus_count=bus_n,
        emergency_count=emg_n,
    )


def write_compare_replay_files(
    map_dir: Path,
    source_routes: Path,
    departures: list[DepartureRecord],
    *,
    seed: int,
    sim_end_seconds: float,
) -> CompareReplayManifest:
    """Write replay rou + sumocfg from vehicles that actually departed in the baseline run."""
    map_dir = Path(map_dir)
    cache_dir = map_dir / ".compare_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    tag = f"seed{seed}_n{len(departures)}"
    routes_out = cache_dir / f"compare_replay_{tag}.rou.xml"
    sumocfg_out = cache_dir / f"compare_replay_{tag}.sumocfg"

    tree = ET.parse(source_routes)
    root = tree.getroot()
    static_lines: list[str] = []
    for child in root:
        if child.tag in ("vType", "route"):
            static_lines.append(ET.tostring(child, encoding="unicode").strip())

    vehicle_lines: list[str] = []
    for rec in sorted(departures, key=lambda d: (d.depart, d.vehicle_id)):
        lane_attr = f' departLane="{rec.depart_lane}"' if rec.depart_lane is not None else ""
        vehicle_lines.append(
            f'    <vehicle id="{rec.vehicle_id}" type="{rec.type_id}" '
            f'route="{rec.route_id}" depart="{rec.depart:.1f}"{lane_attr}/>'
        )

    routes_out.write_text(
        f"<routes>\n" + "\n".join(static_lines + vehicle_lines) + "\n</routes>\n",
        encoding="utf-8",
    )
    end_t = int(max(sim_end_seconds, 1.0)) + 120
    sumocfg_out.write_text(
        f"""<configuration>
    <input>
        <net-file value="../network.net.xml"/>
        <route-files value="{routes_out.name}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="{end_t}"/>
    </time>
</configuration>
""",
        encoding="utf-8",
    )

    counts = manifest_from_departures(departures)
    return CompareReplayManifest(
        routes_path=str(routes_out.resolve()),
        sumocfg_path=str(sumocfg_out.resolve()),
        car_count=counts.car_count,
        bus_count=counts.bus_count,
        emergency_count=counts.emergency_count,
    )
