"""Embedded intersection view — draws SUMO state inside the FlowGrid window."""
from __future__ import annotations

import tkinter as tk

from gui.theme import get_canvas_colors

C = get_canvas_colors("light")


class IntersectionCanvas(tk.Canvas):
    """Schematic 4-way intersection; vehicles from TraCI live snapshot."""

    def __init__(self, parent, **kw):
        super().__init__(
            parent,
            bg=C["bg"],
            highlightthickness=1,
            highlightbackground=C["border"],
            **kw,
        )
        self._veh_ids: dict[str, int] = {}
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _event=None):
        self._draw_static()

    def _cxcy(self) -> tuple[float, float]:
        return self.winfo_width() / 2, self.winfo_height() / 2

    def _draw_static(self):
        self.delete("static")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 40 or h < 40:
            return
        cx, cy = w / 2, h / 2
        arm_len = min(w, h) * 0.38
        road_w = min(w, h) * 0.11
        box = road_w * 1.35

        self.create_rectangle(
            cx - box, cy - box, cx + box, cy + box, fill=C["intersection"], outline=C["road_line"], tags="static"
        )
        self.create_rectangle(
            cx - road_w / 2, cy - arm_len, cx + road_w / 2, cy + arm_len, fill=C["road"], outline="", tags="static"
        )
        self.create_rectangle(
            cx - arm_len, cy - road_w / 2, cx + arm_len, cy + road_w / 2, fill=C["road"], outline="", tags="static"
        )
        for arm, ox, oy, lx, ly in [
            ("N", 0, -1, road_w * 0.22, 0),
            ("S", 0, 1, road_w * 0.22, 0),
            ("E", 1, 0, 0, road_w * 0.22),
            ("W", -1, 0, 0, road_w * 0.22),
        ]:
            x0 = cx + ox * (box + 4) - lx
            y0 = cy + oy * (box + 4) - ly
            x1 = cx + ox * arm_len + lx
            y1 = cy + oy * arm_len + ly
            self.create_line(x0, y0, x1, y1, fill=C["road_line"], dash=(4, 6), tags="static")
            self.create_text(
                cx + ox * (arm_len * 0.72),
                cy + oy * (arm_len * 0.72),
                text=arm,
                fill=C["muted"],
                font=("Segoe UI", 10, "bold"),
                tags="static",
            )

        self._signal_items: dict[str, dict[str, int]] = {}
        for arm, ox, oy in [("N", 0, -1), ("S", 0, 1), ("E", 1, 0), ("W", -1, 0)]:
            sx = cx + ox * (box + 18)
            sy = cy + oy * (box + 18)
            self._signal_items[arm] = {}
            for mov, dx, dy in [("straight", -10, 0), ("left", 10, 0)]:
                if ox != 0:
                    dx, dy = dy, dx
                oid = self.create_oval(
                    sx + dx - 5, sy + dy - 5, sx + dx + 5, sy + dy + 5, fill=C["red"], outline="", tags="static"
                )
                self._signal_items[arm][mov] = oid

    def _vehicle_xy(self, arm: str, lane_kind: str, t: float) -> tuple[float, float]:
        cx, cy = self._cxcy()
        arm_len = min(self.winfo_width(), self.winfo_height()) * 0.38
        road_w = min(self.winfo_width(), self.winfo_height()) * 0.11
        offset = road_w * 0.22 if lane_kind == "left" else -road_w * 0.22
        dist = arm_len * (1.0 - max(0.0, min(1.0, t)))
        if arm == "N":
            return cx + offset, cy - dist
        if arm == "S":
            return cx + offset, cy + dist
        if arm == "E":
            return cx + dist, cy + offset
        return cx - dist, cy + offset

    def update_live(self, live: dict | None):
        if live is None:
            return
        if not self.find_withtag("static"):
            self._draw_static()

        arms = live.get("arms") or {}
        for arm, movs in getattr(self, "_signal_items", {}).items():
            data = arms.get(arm, {})
            for mov, oid in movs.items():
                key = f"signal_{mov}"
                sig = data.get(key, "red")
                color = {"green": C["green"], "yellow": C["yellow"], "red": C["red"]}.get(sig, C["red"])
                self.itemconfigure(oid, fill=color)

        seen: set[str] = set()
        for v in live.get("vehicles") or []:
            vid = v.get("id", "")
            seen.add(vid)
            arm = v.get("arm", "N")
            lane = v.get("lane", "")
            if lane.endswith("_0") or "left" in lane:
                kind = "left"
            elif lane.endswith("_2") or "right" in lane:
                kind = "right"
            else:
                kind = "straight"
            x, y = self._vehicle_xy(arm, kind, float(v.get("t", 0.5)))
            hot = v.get("waiting", False)
            fill = C["vehicle_hot"] if hot else C["vehicle"]
            if vid in self._veh_ids and self._veh_ids[vid]:
                self.coords(self._veh_ids[vid], x - 5, y - 3, x + 5, y + 3)
                self.itemconfigure(self._veh_ids[vid], fill=fill)
            else:
                self._veh_ids[vid] = self.create_rectangle(
                    x - 5, y - 3, x + 5, y + 3, fill=fill, outline="", tags="vehicle"
                )

        for vid, oid in list(self._veh_ids.items()):
            if vid not in seen:
                self.delete(oid)
                del self._veh_ids[vid]
