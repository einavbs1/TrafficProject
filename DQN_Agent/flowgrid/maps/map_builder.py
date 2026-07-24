"""Generate SUMO network and routes (traffic lights come from netconvert --tls.guess)."""
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from flowgrid.paths import DEFAULTS_DIR, PROJECT_ROOT

PROJECT_DIR = PROJECT_ROOT

DEFAULT_FLOWS = {
    "ns_straight": 0.08,
    "ns_left": 0.05,
    "ns_right": 0.04,
    "sn_straight": 0.08,
    "sn_left": 0.05,
    "sn_right": 0.04,
    "ew_straight": 0.06,
    "ew_left": 0.04,
    "ew_right": 0.03,
    "we_straight": 0.06,
    "we_left": 0.04,
    "we_right": 0.03,
}

_FOUR_LANE_APPROACHES = ("n_to_center", "e_to_center", "s_to_center", "w_to_center")
_CENTER_EXITS = ("center_to_n", "center_to_s", "center_to_e", "center_to_w")
_SIXTEEN_LANE_LINK_ORDER: tuple[tuple[str, int], ...] = (
    ("n_to_center", 0),
    ("n_to_center", 1),
    ("n_to_center", 2),
    ("n_to_center", 3),
    ("e_to_center", 0),
    ("e_to_center", 1),
    ("e_to_center", 2),
    ("e_to_center", 3),
    ("s_to_center", 0),
    ("s_to_center", 1),
    ("s_to_center", 2),
    ("s_to_center", 3),
    ("w_to_center", 0),
    ("w_to_center", 1),
    ("w_to_center", 2),
    ("w_to_center", 3),
)
_FOUR_LANE_TURNS: dict[str, dict[int, tuple[str, int]]] = {
    "s_to_center": {
        0: ("center_to_e", 0),
        1: ("center_to_n", 1),
        2: ("center_to_n", 2),
        3: ("center_to_w", 3),
    },
    "w_to_center": {
        0: ("center_to_s", 0),
        1: ("center_to_e", 1),
        2: ("center_to_e", 2),
        3: ("center_to_n", 3),
    },
    "n_to_center": {
        0: ("center_to_w", 0),
        1: ("center_to_s", 1),
        2: ("center_to_s", 2),
        3: ("center_to_e", 3),
    },
    "e_to_center": {
        0: ("center_to_n", 0),
        1: ("center_to_w", 1),
        2: ("center_to_w", 2),
        3: ("center_to_s", 3),
    },
}

_FOUR_LANE_ROUTE_EDGES: dict[str, tuple[str, str, str]] = {
    "ns_right": ("n_to_center", "center_to_w", "0"),
    "ns_straight": ("n_to_center", "center_to_s", "1"),
    "ns_left": ("n_to_center", "center_to_e", "3"),
    "sn_right": ("s_to_center", "center_to_e", "0"),
    "sn_straight": ("s_to_center", "center_to_n", "1"),
    "sn_left": ("s_to_center", "center_to_w", "3"),
    "ew_right": ("e_to_center", "center_to_n", "0"),
    "ew_straight": ("e_to_center", "center_to_w", "1"),
    "ew_left": ("e_to_center", "center_to_s", "3"),
    "we_right": ("w_to_center", "center_to_s", "0"),
    "we_straight": ("w_to_center", "center_to_e", "1"),
    "we_left": ("w_to_center", "center_to_n", "3"),
}


def _netconvert_exe() -> str:
    import os
    import shutil

    exe = shutil.which("netconvert")
    if exe:
        return exe
    for sumo_home in (os.environ.get("SUMO_HOME"),):
        if sumo_home:
            for name in ("netconvert.exe", "netconvert"):
                candidate = Path(sumo_home) / "bin" / name
                if candidate.is_file():
                    return str(candidate)
    try:
        import sumo

        for name in ("netconvert.exe", "netconvert"):
            candidate = Path(sumo.SUMO_HOME) / "bin" / name
            if candidate.is_file():
                return str(candidate)
    except ImportError:
        pass
    for candidate in (
        Path(r"C:\Program Files (x86)\Eclipse\Sumo\bin\netconvert.exe"),
        Path(r"C:\Program Files\Eclipse\Sumo\bin\netconvert.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(
        "netconvert not found. Install SUMO or run: python -m pip install eclipse-sumo"
    )


def _four_lane_destinations(approach: str) -> tuple[str, ...]:
    return tuple(sorted({dest for dest, _ in _FOUR_LANE_TURNS[approach].values()}))


def _write_connections(connections_path: Path, lanes_per_approach: int) -> None:
    if int(lanes_per_approach) < 4:
        connections_path.write_text("<connections/>\n", encoding="utf-8")
        return
    lines = ["<connections>"]
    for approach in _FOUR_LANE_APPROACHES:
        for dest in _four_lane_destinations(approach):
            lines.append(f'    <connection from="{approach}" to="{dest}"/>')
    for approach, from_lane in _SIXTEEN_LANE_LINK_ORDER:
        to_edge, to_lane = _FOUR_LANE_TURNS[approach][from_lane]
        lines.append(
            f'    <connection from="{approach}" to="{to_edge}" '
            f'fromLane="{from_lane}" toLane="{to_lane}"/>'
        )
    for approach in _FOUR_LANE_APPROACHES:
        allowed_dests = set(_four_lane_destinations(approach))
        for exit_edge in _CENTER_EXITS:
            if exit_edge not in allowed_dests:
                lines.append(f'    <delete from="{approach}" to="{exit_edge}"/>')
    lines.append("</connections>")
    connections_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_netconvert(
    nodes_path: Path,
    edges_path: Path,
    net_path: Path,
    connections_path: Path | None = None,
) -> None:
    cmd = [
        _netconvert_exe(),
        f"--node-files={nodes_path}",
        f"--edge-files={edges_path}",
        f"--output-file={net_path}",
        "--tls.guess",
        "--no-turnarounds",
        "--junctions.corner-detail",
        "5",
    ]
    if connections_path and connections_path.is_file():
        cmd.append(f"--connection-files={connections_path}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=nodes_path.parent)
    if result.returncode != 0:
        raise RuntimeError(f"netconvert failed:\n{result.stderr or result.stdout}")


def _sync_sixteen_lane_net(
    net_path: Path,
    tls_id: str = "center",
    *,
    through_seconds: float = 60.0,
    left_to_through_ratio: float = 0.60,
    yellow_seconds: float = 3.0,
) -> None:
    from flowgrid.core.intersection_graph import IntersectionTopology
    from flowgrid.core.tls_builder import baseline_tls_phase_elements

    root = ET.parse(net_path).getroot()
    expected: dict[tuple[str, int], int] = {
        key: idx for idx, key in enumerate(_SIXTEEN_LANE_LINK_ORDER)
    }
    for conn in root.findall("connection"):
        if conn.get("tl") != tls_id:
            continue
        from_edge = conn.get("from")
        from_lane = conn.get("fromLane")
        if from_edge is None or from_lane is None:
            continue
        link_idx = expected.get((from_edge, int(from_lane)))
        if link_idx is None:
            continue
        conn.set("linkIndex", str(link_idx))
    tls = root.find(f'tlLogic[@id="{tls_id}"]')
    if tls is not None:
        for phase in list(tls.findall("phase")):
            tls.remove(phase)
        topo = IntersectionTopology.standard_four_way_four_lane()
        for duration, state in baseline_tls_phase_elements(
            topo,
            through_seconds=through_seconds,
            left_to_through_ratio=left_to_through_ratio,
            yellow_seconds=yellow_seconds,
        ):
            ET.SubElement(tls, "phase", duration=duration, state=state)
    ET.ElementTree(root).write(net_path, encoding="UTF-8", xml_declaration=True)


def bootstrap_map_from_defaults(output_dir: Path, flows: dict, lanes_per_approach: int = 2) -> None:
    import shutil

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    src_net = DEFAULTS_DIR / "my_net.net.xml"
    if not src_net.is_file():
        raise FileNotFoundError(f"Missing default network: {src_net}")
    shutil.copy2(src_net, output_dir / "network.net.xml")
    _write_routes(output_dir / "routes.rou.xml", flows, lanes_per_approach)
    (output_dir / "map.sumocfg").write_text(
        """<configuration>
    <input>
        <net-file value="network.net.xml"/>
        <route-files value="routes.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>
""",
        encoding="utf-8",
    )


def _lane_count(lanes_per_approach: int) -> int:
    n = int(lanes_per_approach)
    if n >= 4:
        return 4
    return max(2, min(3, n))


def _edge_xml(
    edge_id: str,
    from_node: str,
    to_node: str,
    nlanes: int,
    *,
    dedicated_lanes: bool = False,
    priority: str = "2",
    speed: str = "15.0",
    shape: str | None = None,
) -> str:
    shape_attr = f' shape="{shape}"' if shape else ""
    if not dedicated_lanes:
        return (
            f'    <edge id="{edge_id}" from="{from_node}" to="{to_node}" '
            f'priority="{priority}" numLanes="{nlanes}" speed="{speed}"{shape_attr}/>'
        )
    lane_lines = [
        '        <lane index="0" changeLeft="authority"/>',
        '        <lane index="1" changeLeft="authority" changeRight="authority"/>',
        '        <lane index="2" changeLeft="authority" changeRight="authority"/>',
        '        <lane index="3" changeRight="authority"/>',
    ]
    return (
        f'    <edge id="{edge_id}" from="{from_node}" to="{to_node}" '
        f'priority="{priority}" numLanes="4" speed="{speed}"{shape_attr}>\n'
        + "\n".join(lane_lines)
        + "\n    </edge>"
    )


def _write_nodes_edges(
    nodes_path: Path,
    edges_path: Path,
    arm_length: int,
    lanes_per_approach: int = 4,
    separate_right_slip: bool = False,
) -> None:
    half = arm_length
    nlanes = _lane_count(lanes_per_approach)
    slip_nodes = ""
    slip_edges = ""
    if separate_right_slip and nlanes == 3:
        off = max(25, arm_length // 12)
        slip_nodes = f"""
    <node id="n_slip" x="{off}" y="{half - off}" type="priority"/>
    <node id="s_slip" x="{off}" y="-{half + off}" type="priority"/>
    <node id="e_slip" x="{half - off}" y="{off}" type="priority"/>
    <node id="w_slip" x="-{half + off}" y="{off}" type="priority"/>"""
        slip_edges = f"""
    <edge id="n_slip_to_center" from="n_slip" to="center" priority="1" numLanes="1" speed="12.0" shape="{off},{half - off} 0,0"/>
    <edge id="s_slip_to_center" from="s_slip" to="center" priority="1" numLanes="1" speed="12.0"/>
    <edge id="e_slip_to_center" from="e_slip" to="center" priority="1" numLanes="1" speed="12.0"/>
    <edge id="w_slip_to_center" from="w_slip" to="center" priority="1" numLanes="1" speed="12.0"/>"""
    center_radius = 20 if nlanes >= 4 else 10
    nodes_path.write_text(
        f"""<nodes>
    <node id="center" x="0" y="0" type="traffic_light" radius="{center_radius}"/>
    <node id="n" x="0" y="{half}" type="priority"/>
    <node id="s" x="0" y="-{half}" type="priority"/>
    <node id="e" x="{half}" y="0" type="priority"/>
    <node id="w" x="-{half}" y="0" type="priority"/>{slip_nodes}
</nodes>
""",
        encoding="utf-8",
    )
    dedicated = nlanes >= 4
    edge_block = "\n".join(
        [
            _edge_xml("n_to_center", "n", "center", nlanes, dedicated_lanes=dedicated),
            _edge_xml("center_to_n", "center", "n", nlanes, dedicated_lanes=False),
            _edge_xml("s_to_center", "s", "center", nlanes, dedicated_lanes=dedicated),
            _edge_xml("center_to_s", "center", "s", nlanes, dedicated_lanes=False),
            _edge_xml("e_to_center", "e", "center", nlanes, dedicated_lanes=dedicated),
            _edge_xml("center_to_e", "center", "e", nlanes, dedicated_lanes=False),
            _edge_xml("w_to_center", "w", "center", nlanes, dedicated_lanes=dedicated),
            _edge_xml("center_to_w", "center", "w", nlanes, dedicated_lanes=False),
        ]
    )
    edges_path.write_text(
        f"<edges>\n{edge_block}{slip_edges}\n</edges>\n",
        encoding="utf-8",
    )


def _four_lane_route_xml(flow_key: str) -> tuple[str, str, str, str]:
    from_edge, to_edge, lane = _FOUR_LANE_ROUTE_EDGES[flow_key]
    route_id = f"route_{flow_key}"
    route_line = f'    <route id="{route_id}" edges="{from_edge} {to_edge}"/>'
    return route_id, route_line, from_edge, lane


def _auxiliary_flow_block(
    *,
    bus_probability: float,
    emergency_probability: float,
    four_lane: bool,
    route_ids: dict[str, str] | None = None,
    ds1: str = "1",
    lane_strict: str = "",
) -> str:
    lines: list[str] = []
    if bus_probability > 0:
        if four_lane and route_ids is not None:
            for flow_id, key in (
                ("f_ns_s_bus", "ns_straight"),
                ("f_sn_s_bus", "sn_straight"),
                ("f_ew_s_bus", "ew_straight"),
                ("f_we_s_bus", "we_straight"),
            ):
                lines.append(
                    f'    <flow id="{flow_id}" type="bus" route="{route_ids[key]}" departLane="{ds1}"{lane_strict} begin="0" end="3600" probability="{bus_probability}"/>'
                )
        else:
            for flow_id, route_name in (
                ("f_ns_s_bus", "route_ns_straight"),
                ("f_sn_s_bus", "route_sn_straight"),
                ("f_ew_s_bus", "route_ew_straight"),
                ("f_we_s_bus", "route_we_straight"),
            ):
                lines.append(
                    f'    <flow id="{flow_id}" type="bus" route="{route_name}" departLane="{ds1}"{lane_strict} begin="0" end="3600" probability="{bus_probability}"/>'
                )
    if emergency_probability > 0:
        if four_lane and route_ids is not None:
            for flow_id, key in (("f_ns_s_emg", "ns_straight"), ("f_ew_s_emg", "ew_straight")):
                lines.append(
                    f'    <flow id="{flow_id}" type="emergency" route="{route_ids[key]}" departLane="{ds1}" begin="0" end="3600" probability="{emergency_probability}"/>'
                )
        else:
            for flow_id, route_name in (("f_ns_s_emg", "route_ns_straight"), ("f_ew_s_emg", "route_ew_straight")):
                lines.append(
                    f'    <flow id="{flow_id}" type="emergency" route="{route_name}" departLane="{ds1}" begin="0" end="3600" probability="{emergency_probability}"/>'
                )
    if not lines:
        return ""
    return "\n" + "\n".join(lines)


def write_routes_file(
    routes_path: Path,
    flows: dict,
    lanes_per_approach: int = 4,
    *,
    bus_probability: float = 0.02,
    emergency_probability: float = 0.005,
) -> None:
    _write_routes(
        routes_path,
        flows,
        lanes_per_approach,
        bus_probability=bus_probability,
        emergency_probability=emergency_probability,
    )


def _write_routes(
    routes_path: Path,
    flows: dict,
    lanes_per_approach: int = 4,
    *,
    bus_probability: float = 0.02,
    emergency_probability: float = 0.005,
) -> None:
    nlanes = _lane_count(lanes_per_approach)
    lane_strict = ' departLaneStrict="true"' if nlanes >= 4 else ""
    if nlanes >= 4:
        dl, ds1, ds2, dr = "3", "1", "2", "0"
        route_lines = []
        route_ids: dict[str, str] = {}
        for key in (
            "ns_straight",
            "ns_left",
            "sn_straight",
            "sn_left",
            "ew_straight",
            "ew_left",
            "we_straight",
            "we_left",
            "ns_right",
            "sn_right",
            "ew_right",
            "we_right",
        ):
            route_id, route_line, _, _ = _four_lane_route_xml(key)
            route_ids[key] = route_id
            route_lines.append(route_line)
        route_block = "\n".join(route_lines)
        right_flows = f"""
    <flow id="f_ns_r" type="car" route="{route_ids['ns_right']}" departLane="{dr}"{lane_strict} begin="0" end="3600" probability="{flows.get('ns_right', 0.03)}"/>
    <flow id="f_sn_r" type="car" route="{route_ids['sn_right']}" departLane="{dr}"{lane_strict} begin="0" end="3600" probability="{flows.get('sn_right', 0.03)}"/>
    <flow id="f_ew_r" type="car" route="{route_ids['ew_right']}" departLane="{dr}"{lane_strict} begin="0" end="3600" probability="{flows.get('ew_right', 0.03)}"/>
    <flow id="f_we_r" type="car" route="{route_ids['we_right']}" departLane="{dr}"{lane_strict} begin="0" end="3600" probability="{flows.get('we_right', 0.03)}"/>"""
        thru_flows = f"""
    <flow id="f_ns_s" type="car" route="{route_ids['ns_straight']}" departLane="{ds1}"{lane_strict} begin="0" end="3600" probability="{flows['ns_straight']}"/>
    <flow id="f_ns_s2" type="car" route="{route_ids['ns_straight']}" departLane="{ds2}"{lane_strict} begin="0" end="3600" probability="{flows['ns_straight']}"/>
    <flow id="f_sn_s" type="car" route="{route_ids['sn_straight']}" departLane="{ds1}"{lane_strict} begin="0" end="3600" probability="{flows['sn_straight']}"/>
    <flow id="f_sn_s2" type="car" route="{route_ids['sn_straight']}" departLane="{ds2}"{lane_strict} begin="0" end="3600" probability="{flows['sn_straight']}"/>
    <flow id="f_ew_s" type="car" route="{route_ids['ew_straight']}" departLane="{ds1}"{lane_strict} begin="0" end="3600" probability="{flows['ew_straight']}"/>
    <flow id="f_ew_s2" type="car" route="{route_ids['ew_straight']}" departLane="{ds2}"{lane_strict} begin="0" end="3600" probability="{flows['ew_straight']}"/>
    <flow id="f_we_s" type="car" route="{route_ids['we_straight']}" departLane="{ds1}"{lane_strict} begin="0" end="3600" probability="{flows['we_straight']}"/>
    <flow id="f_we_s2" type="car" route="{route_ids['we_straight']}" departLane="{ds2}"{lane_strict} begin="0" end="3600" probability="{flows['we_straight']}"/>"""
        left_flows = f"""
    <flow id="f_ns_l" type="car" route="{route_ids['ns_left']}" departLane="{dl}"{lane_strict} begin="0" end="3600" probability="{flows['ns_left']}"/>
    <flow id="f_sn_l" type="car" route="{route_ids['sn_left']}" departLane="{dl}"{lane_strict} begin="0" end="3600" probability="{flows['sn_left']}"/>
    <flow id="f_ew_l" type="car" route="{route_ids['ew_left']}" departLane="{dl}"{lane_strict} begin="0" end="3600" probability="{flows['ew_left']}"/>
    <flow id="f_we_l" type="car" route="{route_ids['we_left']}" departLane="{dl}"{lane_strict} begin="0" end="3600" probability="{flows['we_left']}"/>"""
        bus_emg_flows = _auxiliary_flow_block(
            bus_probability=bus_probability,
            emergency_probability=emergency_probability,
            four_lane=True,
            route_ids=route_ids,
            ds1=ds1,
            lane_strict=lane_strict,
        )
        routes_path.write_text(
            f"""<routes>
    <vType id="car" vClass="passenger" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.7" guiShape="passenger"/>
    <vType id="bus" vClass="bus" accel="0.7" decel="4.0" sigma="0.3" length="12" minGap="3" maxSpeed="14.0" guiShape="bus" color="yellow"/>
    <vType id="emergency" vClass="emergency" accel="1.5" decel="5.0" sigma="0.0" length="6.5" minGap="2.5" maxSpeed="25.0" guiShape="emergency" color="red"/>

{route_block}{thru_flows}{left_flows}{right_flows}{bus_emg_flows}
</routes>
""",
            encoding="utf-8",
        )
        return
    elif nlanes >= 3:
        dl, ds1, ds2, dr = "0", "1", "1", "2"
        right_flows = f"""
    <route id="route_ns_right" edges="n_to_center center_to_w"/>
    <route id="route_sn_right" edges="s_to_center center_to_e"/>
    <route id="route_ew_right" edges="e_to_center center_to_s"/>
    <route id="route_we_right" edges="w_to_center center_to_n"/>
    <flow id="f_ns_r" type="car" route="route_ns_right" departLane="{dr}" begin="0" end="3600" probability="{flows.get('ns_right', 0.03)}"/>
    <flow id="f_sn_r" type="car" route="route_sn_right" departLane="{dr}" begin="0" end="3600" probability="{flows.get('sn_right', 0.03)}"/>
    <flow id="f_ew_r" type="car" route="route_ew_right" departLane="{dr}" begin="0" end="3600" probability="{flows.get('ew_right', 0.03)}"/>
    <flow id="f_we_r" type="car" route="route_we_right" departLane="{dr}" begin="0" end="3600" probability="{flows.get('we_right', 0.03)}"/>"""
        thru_flows = f"""
    <flow id="f_ns_s" type="car" route="route_ns_straight" departLane="{ds1}" begin="0" end="3600" probability="{flows['ns_straight']}"/>
    <flow id="f_sn_s" type="car" route="route_sn_straight" departLane="{ds1}" begin="0" end="3600" probability="{flows['sn_straight']}"/>
    <flow id="f_ew_s" type="car" route="route_ew_straight" departLane="{ds1}" begin="0" end="3600" probability="{flows['ew_straight']}"/>
    <flow id="f_we_s" type="car" route="route_we_straight" departLane="{ds1}" begin="0" end="3600" probability="{flows['we_straight']}"/>"""
    else:
        dl, ds1, ds2, dr = "1", "0", "0", "0"
        right_flows = ""
        thru_flows = f"""
    <flow id="f_ns_s" type="car" route="route_ns_straight" departLane="{ds1}" begin="0" end="3600" probability="{flows['ns_straight']}"/>
    <flow id="f_sn_s" type="car" route="route_sn_straight" departLane="{ds1}" begin="0" end="3600" probability="{flows['sn_straight']}"/>
    <flow id="f_ew_s" type="car" route="route_ew_straight" departLane="{ds1}" begin="0" end="3600" probability="{flows['ew_straight']}"/>
    <flow id="f_we_s" type="car" route="route_we_straight" departLane="{ds1}" begin="0" end="3600" probability="{flows['we_straight']}"/>"""

    routes_path.write_text(
        f"""<routes>
    <vType id="car" vClass="passenger" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.7" guiShape="passenger"/>
    <vType id="bus" vClass="bus" accel="0.7" decel="4.0" sigma="0.3" length="12" minGap="3" maxSpeed="14.0" guiShape="bus" color="yellow"/>
    <vType id="emergency" vClass="emergency" accel="1.5" decel="5.0" sigma="0.0" length="6.5" minGap="2.5" maxSpeed="25.0" guiShape="emergency" color="red"/>

    <route id="route_ns_straight" edges="n_to_center center_to_s"/>
    <route id="route_ns_left"     edges="n_to_center center_to_e"/>
    <route id="route_sn_straight" edges="s_to_center center_to_n"/>
    <route id="route_sn_left"     edges="s_to_center center_to_w"/>
    <route id="route_ew_straight" edges="e_to_center center_to_w"/>
    <route id="route_ew_left"     edges="e_to_center center_to_s"/>
    <route id="route_we_straight" edges="w_to_center center_to_e"/>
    <route id="route_we_left"     edges="w_to_center center_to_n"/>{thru_flows}
    <flow id="f_ns_l" type="car" route="route_ns_left"     departLane="{dl}"{lane_strict} begin="0" end="3600" probability="{flows['ns_left']}"/>
    <flow id="f_sn_l" type="car" route="route_sn_left"     departLane="{dl}"{lane_strict} begin="0" end="3600" probability="{flows['sn_left']}"/>
    <flow id="f_ew_l" type="car" route="route_ew_left"     departLane="{dl}"{lane_strict} begin="0" end="3600" probability="{flows['ew_left']}"/>
    <flow id="f_we_l" type="car" route="route_we_left"     departLane="{dl}"{lane_strict} begin="0" end="3600" probability="{flows['we_left']}"/>{right_flows}{_auxiliary_flow_block(bus_probability=bus_probability, emergency_probability=emergency_probability, four_lane=False, ds1=ds1, lane_strict=lane_strict)}
</routes>
""",
        encoding="utf-8",
    )


def build_map_into_directory(
    output_dir: Path,
    arm_length: int = 500,
    flows: dict | None = None,
    lanes_per_approach: int = 4,
    separate_right_slip: bool = False,
    baseline_through_seconds: float | None = None,
    baseline_left_to_through_ratio: float | None = None,
) -> dict:
    from flowgrid.rl.policy_config import PolicyConfig

    flows = {**DEFAULT_FLOWS, **(flows or {})}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_cfg = PolicyConfig.load().baseline_timing
    through_seconds = float(
        baseline_through_seconds
        if baseline_through_seconds is not None
        else baseline_cfg.through_seconds_default
    )
    left_ratio = float(
        baseline_left_to_through_ratio
        if baseline_left_to_through_ratio is not None
        else baseline_cfg.left_to_through_ratio
    )

    nodes_path = output_dir / "nodes.nod.xml"
    edges_path = output_dir / "edges.edg.xml"
    connections_path = output_dir / "connections.con.xml"
    net_path = output_dir / "network.net.xml"
    routes_path = output_dir / "routes.rou.xml"
    sumocfg_path = output_dir / "map.sumocfg"

    try:
        _write_nodes_edges(
            nodes_path, edges_path, arm_length, lanes_per_approach, separate_right_slip
        )
        _write_connections(connections_path, lanes_per_approach)
        _run_netconvert(nodes_path, edges_path, net_path, connections_path)
        if int(lanes_per_approach) >= 4:
            _sync_sixteen_lane_net(
                net_path,
                through_seconds=through_seconds,
                left_to_through_ratio=left_ratio,
            )
        _write_routes(routes_path, flows, lanes_per_approach)
    except FileNotFoundError as exc:
        if int(lanes_per_approach) >= 4:
            raise FileNotFoundError(
                "netconvert is required for 4-lane maps. "
                "Install SUMO or run: python -m pip install eclipse-sumo"
            ) from exc
        bootstrap_map_from_defaults(output_dir, flows, lanes_per_approach=2)

    sumocfg_path.write_text(
        """<configuration>
    <input>
        <net-file value="network.net.xml"/>
        <route-files value="routes.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>
""",
        encoding="utf-8",
    )

    return {
        "directory": str(output_dir),
        "sumocfg": str(sumocfg_path),
        "arm_length": arm_length,
        "flows": flows,
        "lanes_per_approach": lanes_per_approach,
        "baseline_through_seconds": through_seconds,
        "baseline_left_to_through_ratio": left_ratio,
    }


def build_map(
    name: str = "flowgrid",
    arm_length: int = 500,
    flows: dict | None = None,
    lanes_per_approach: int = 4,
) -> dict:
    flows = {**DEFAULT_FLOWS, **(flows or {})}
    prefix = name if name != "flowgrid" else "flowgrid"
    DEFAULTS_DIR.mkdir(parents=True, exist_ok=True)
    nodes_path = DEFAULTS_DIR / "my_nodes.nod.xml"
    edges_path = DEFAULTS_DIR / "my_edges.edg.xml"
    connections_path = DEFAULTS_DIR / "my_connections.con.xml"
    net_path = DEFAULTS_DIR / "my_net.net.xml"
    routes_path = DEFAULTS_DIR / f"{prefix}.rou.xml"
    sumocfg_path = DEFAULTS_DIR / f"{prefix}.sumocfg"

    _write_nodes_edges(nodes_path, edges_path, arm_length, lanes_per_approach)
    _write_connections(connections_path, lanes_per_approach)
    _run_netconvert(nodes_path, edges_path, net_path, connections_path)
    from flowgrid.rl.policy_config import PolicyConfig

    baseline_cfg = PolicyConfig.load().baseline_timing
    if int(lanes_per_approach) >= 4:
        _sync_sixteen_lane_net(
            net_path,
            through_seconds=float(baseline_cfg.through_seconds_default),
            left_to_through_ratio=float(baseline_cfg.left_to_through_ratio),
        )
    _write_routes(routes_path, flows, lanes_per_approach)

    sumocfg_path.write_text(
        f"""<configuration>
    <input>
        <net-file value="my_net.net.xml"/>
        <route-files value="{routes_path.name}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>
""",
        encoding="utf-8",
    )

    if prefix == "flowgrid":
        (DEFAULTS_DIR / "flowgrid.rou.xml").write_text(routes_path.read_text(encoding="utf-8"), encoding="utf-8")
        (DEFAULTS_DIR / "flowgrid.sumocfg").write_text(sumocfg_path.read_text(encoding="utf-8"), encoding="utf-8")

    return {
        "name": prefix,
        "sumocfg": str(sumocfg_path.name),
        "net": str(net_path.name),
        "routes": str(routes_path.name),
        "flows": flows,
        "arm_length": arm_length,
        "lanes_per_approach": lanes_per_approach,
    }


def parse_tls_link_map(net_path: Path, tls_id: str = "center") -> dict[tuple[str, str, int], int]:
    root = ET.parse(net_path).getroot()
    out: dict[tuple[str, str, int], int] = {}
    for conn in root.findall("connection"):
        if conn.get("tl") != tls_id:
            continue
        from_edge = conn.get("from")
        to_edge = conn.get("to")
        from_lane = int(conn.get("fromLane", "0"))
        link_index = conn.get("linkIndex")
        if from_edge and to_edge and link_index is not None:
            out[(from_edge, to_edge, from_lane)] = int(link_index)
    return out


def list_maps() -> list[dict]:
    from flowgrid.maps.map_registry import list_maps_for_gui

    return list_maps_for_gui()
