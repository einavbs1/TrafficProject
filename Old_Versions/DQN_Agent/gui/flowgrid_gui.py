"""
FlowGrid desktop control panel — one tab per action.

Run: python flowgrid_gui.py
"""
from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flowgrid.jobs.job_runner import JobRunner
from flowgrid.maps.map_builder import DEFAULT_FLOWS, build_map
from flowgrid.reports.batch_evaluation_log import batch_evaluation_log_path, parse_batch_evaluation_log
from flowgrid.reports.comparison_history import clear_history, comparison_history_path, load_history
from flowgrid.reports.training_summary import load_training_dashboard
from flowgrid.reports.curriculum import CurriculumConfig, curriculum_status_lines
from flowgrid.rl.policy_config import PolicyConfig
from flowgrid.paths import DEFAULT_POLICY_CONFIG_PATH, DQN_TRAINING_LOG_PATH
from flowgrid.core.phasing_schemes import SCHEME_LABELS, DEFAULT_SCHEME
from flowgrid.maps.map_registry import (
    delete_map,
    ensure_default_map,
    get_map,
    list_maps_for_gui,
    save_map,
    slugify_map_name,
)
from flowgrid.maps.policy_paths import policy_checkpoint_exists
from flowgrid.paths import PROJECT_ROOT
from gui.theme import (
    C,
    FONT,
    FONT_HUGE,
    FONT_LG,
    FONT_SM,
    FONT_TITLE,
    FONTS,
    apply_ttk_style,
    legend_style,
    style_matplotlib_axes,
)

PROJECT_DIR = PROJECT_ROOT


class FlowGridApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FlowGrid")
        self.root.minsize(1100, 700)
        self.root.geometry("1280x800")
        self.root.configure(bg=C["bg"])

        self.runner = JobRunner()
        self.current_job_id: str | None = None
        self._flow_vars: dict[str, tk.StringVar] = {}
        self._saved_maps: list[dict] = []
        self._last_train_chart = PROJECT_DIR / "learning_curve.png"
        self.compare_show_sumo = tk.BooleanVar(value=True)
        self.compare_delay = tk.IntVar(value=30)
        self.train_show_sumo = tk.BooleanVar(value=False)
        self.train_delay = tk.IntVar(value=30)
        self._train_job_active = False
        self._pages: dict[str, tk.Frame] = {}
        self._train_ax = None
        self._train_fig = None
        self._train_canvas_mpl = None
        self._cmp_summary_fig = None
        self._cmp_summary_axes: list = []
        self._cmp_summary_canvas = None
        self._cmp_emergency_fig = None
        self._cmp_emergency_axes: list = []
        self._cmp_emergency_canvas = None
        self._cmp_transit_fig = None
        self._cmp_transit_axes: list = []
        self._cmp_transit_canvas = None
        self._reports_fig = None
        self._reports_ax = None
        self._reports_emg_fig = None
        self._reports_emg_ax = None
        self._reports_transit_fig = None
        self._reports_transit_ax = None
        self._reports_canvas = None
        self._reports_emg_canvas = None
        self._reports_transit_canvas = None
        self.reports_tree = None
        self.batch_reports_tree = None
        self.batch_episodes_filter_var = None
        self.batch_sort_var = None
        self.batch_summary_var = None
        self._batch_fig = None
        self._batch_ax = None
        self._batch_canvas = None

        self._build_styles()
        self._build_ui()
        self._refresh_map_list()
        self._show_page("train")
        self.root.after(250, self._poll_job)

    def _build_styles(self):
        apply_ttk_style(self.root)

    def _frame(self, parent, **kw) -> tk.Frame:
        return tk.Frame(parent, bg=kw.pop("bg", C["surface"]), **kw)

    def _label(self, parent, text, muted=False, **kw) -> tk.Label:
        fg = C["muted"] if muted else C["text"]
        bg = kw.pop("bg", parent.cget("bg"))
        return tk.Label(parent, text=text, fg=fg, bg=bg, font=FONT_SM if muted else FONT, **kw)

    def _entry(self, parent, var, width=10) -> tk.Entry:
        return tk.Entry(
            parent,
            textvariable=var,
            width=width,
            bg=C["input_bg"],
            fg=C["text"],
            insertbackground=C["accent"],
            relief=tk.SOLID,
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
            font=FONT,
        )

    def _btn(self, parent, text, command=None, primary=False, green=False) -> tk.Button:
        if primary:
            bg, fg, active = C["accent"], C["on_accent"], C["accent_dim"]
        elif green:
            bg, fg, active = C["success"], C["on_success"], C["success_dim"]
        else:
            bg, fg, active = C["surface2"], C["text"], C["border"]
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=active,
            font=FONTS["btn"],
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2",
        )

    def _set_btn_enabled(self, btn: tk.Button, enabled: bool, *, primary: bool = False, green: bool = False) -> None:
        if enabled:
            if primary:
                bg, fg, active = C["accent"], C["on_accent"], C["accent_dim"]
            elif green:
                bg, fg, active = C["success"], C["on_success"], C["success_dim"]
            else:
                bg, fg, active = C["surface2"], C["text"], C["border"]
            btn.config(state=tk.NORMAL, bg=bg, fg=fg, activebackground=active, cursor="hand2")
        else:
            btn.config(state=tk.DISABLED, bg=C["border"], fg=C["muted"], cursor="arrow")

    def _refresh_train_live_sim_btn(self) -> None:
        if not hasattr(self, "train_live_sim_btn"):
            return
        if self.train_show_sumo.get():
            self.train_live_sim_btn.config(bg=C["success"], fg=C["on_success"], text="●  Live simulator ON")
        else:
            self.train_live_sim_btn.config(bg=C["surface2"], fg=C["text"], text="○  Live simulator")

    def _toggle_train_live_sim(self) -> None:
        if self._train_job_active:
            return
        self.train_show_sumo.set(not self.train_show_sumo.get())
        self._refresh_train_live_sim_btn()

    def _set_train_job_controls(self, running: bool) -> None:
        self._train_job_active = running
        self._set_btn_enabled(self.train_start_btn, not running, primary=True)
        self._set_btn_enabled(self.train_stop_btn, running)
        if hasattr(self, "train_live_sim_btn"):
            self._set_btn_enabled(self.train_live_sim_btn, not running)
        if hasattr(self, "curriculum_start_btn"):
            self._set_btn_enabled(self.curriculum_start_btn, not running, green=True)

    def _card(self, parent, title: str) -> tk.Frame:
        outer = self._frame(parent, bg=C["border"], padx=1, pady=1)
        body = self._frame(outer, bg=C["surface2"], padx=20, pady=16)
        body.pack(fill=tk.BOTH, expand=True)
        tk.Label(body, text=title.upper(), font=FONTS["card_title"], fg=C["muted"], bg=C["surface2"]).pack(
            anchor=tk.W, pady=(0, 10)
        )
        outer.body = body
        return outer

    def _build_ui(self):
        top = self._frame(self.root, bg=C["surface2"])
        top.pack(fill=tk.X)
        row = self._frame(top, bg=C["surface2"])
        row.pack(fill=tk.X, padx=20, pady=14)
        tk.Label(row, text="FlowGrid", font=FONT_TITLE, fg=C["text"], bg=C["surface2"]).pack(side=tk.LEFT)
        map_box = self._frame(row, bg=C["surface2"])
        map_box.pack(side=tk.RIGHT)
        self._label(map_box, "Active map", muted=True).pack(anchor=tk.E)
        self.active_map_var = tk.StringVar()
        self.active_map_combo = ttk.Combobox(
            map_box, textvariable=self.active_map_var, width=32, state="readonly", font=FONT
        )
        self.active_map_combo.pack(anchor=tk.E, pady=(4, 0))
        self.active_map_combo.bind("<<ComboboxSelected>>", lambda _: self._on_active_map_changed())

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self._build_page_map()
        self._build_page_train()
        self._build_page_compare()
        self._build_page_reports()

        foot = self._frame(self.root, bg=C["surface"])
        foot.pack(fill=tk.X)
        sr = self._frame(foot, bg=C["surface"])
        sr.pack(fill=tk.X, padx=16, pady=(8, 4))
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(sr, textvariable=self.status_var, fg=C["muted"], bg=C["surface"], font=FONT_SM).pack(
            side=tk.LEFT, fill=tk.X, expand=True
        )
        self.progress = ttk.Progressbar(sr, mode="determinate", length=280)
        self.progress.pack(side=tk.RIGHT)
        log_outer = self._frame(foot, bg=C["surface"])
        log_outer.pack(fill=tk.X, padx=16, pady=(0, 10))
        self.log_text = tk.Text(
            log_outer, height=2, font=FONTS["mono"], bg=C["surface"], fg=C["text"], relief=tk.FLAT
        )
        self.log_text.pack(fill=tk.X)

    def _page(self, key: str, title: str) -> tk.Frame:
        wrap = self._frame(self.notebook, bg=C["bg"])
        self.notebook.add(wrap, text=f"  {title}  ")
        self._pages[key] = wrap
        return wrap

    def _show_page(self, key: str):
        keys = list(self._pages.keys())
        if key in keys:
            self.notebook.select(keys.index(key))

    def _on_tab_changed(self, _event=None):
        idx = self.notebook.index(self.notebook.select())
        keys = list(self._pages.keys())
        if 0 <= idx < len(keys):
            key = keys[idx]
            self.status_var.set(f"{key.replace('_', ' ').title()} tab")
            if key == "reports":
                self._refresh_reports()

    def _build_page_map(self):
        page = self._page("map", "Build map")
        inner = self._frame(page, bg=C["bg"])
        inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        inner.columnconfigure(0, weight=1)
        inner.columnconfigure(1, weight=1)

        left = self._card(inner, "Map settings")
        left.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 8))
        body = left.body
        self.map_save_name_var = tk.StringVar(value="My intersection")
        self.arm_length_var = tk.StringVar(value="500")
        for lbl, var, w in [("Map name", self.map_save_name_var, 28), ("Arm length (m)", self.arm_length_var, 10)]:
            r = self._frame(body, bg=C["surface2"])
            r.pack(fill=tk.X, pady=4)
            self._label(r, lbl, muted=True).pack(side=tk.LEFT)
            self._entry(r, var, w).pack(side=tk.RIGHT)
        r = self._frame(body, bg=C["surface2"])
        r.pack(fill=tk.X, pady=4)
        self._label(r, "Phasing plan", muted=True).pack(side=tk.LEFT)
        self.phasing_scheme_var = tk.StringVar(value=DEFAULT_SCHEME)
        self._phasing_by_label = {v: k for k, v in SCHEME_LABELS.items()}
        ph_combo = ttk.Combobox(
            r,
            values=list(SCHEME_LABELS.values()),
            state="readonly",
            width=42,
        )
        ph_combo.set(SCHEME_LABELS[DEFAULT_SCHEME])
        ph_combo.pack(side=tk.RIGHT)
        self._phasing_combo = ph_combo
        self.separate_right_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            body,
            text="Right turn free (Israeli — not stopped by signal)",
            variable=self.separate_right_var,
        ).pack(anchor=tk.W, pady=4)
        self.baseline_through_var = tk.StringVar(value="60")
        self.baseline_left_ratio_var = tk.StringVar(value="0.60")
        for lbl, var, w in [
            ("Fixed thru / full-arm (s)", self.baseline_through_var, 6),
            ("Left / thru ratio", self.baseline_left_ratio_var, 6),
        ]:
            r = self._frame(body, bg=C["surface2"])
            r.pack(fill=tk.X, pady=2)
            self._label(r, lbl, muted=True).pack(side=tk.LEFT)
            self._entry(r, var, w).pack(side=tk.RIGHT)
        self._label(
            body,
            "3 lanes per approach: left | thru | right (vehicles stay in lane).",
            muted=True,
        ).pack(anchor=tk.W, pady=(6, 0))
        self._label(body, "Traffic flow (0–1)", muted=True).pack(anchor=tk.W, pady=(10, 4))
        for key, label in {
            "ns_straight": "N straight",
            "ns_left": "N left",
            "sn_straight": "S straight",
            "sn_left": "S left",
            "ew_straight": "E straight",
            "ew_left": "E left",
            "we_straight": "W straight",
            "we_left": "W left",
        }.items():
            r = self._frame(body, bg=C["surface2"])
            r.pack(fill=tk.X, pady=1)
            self._label(r, label, muted=True).pack(side=tk.LEFT)
            v = tk.StringVar(value=str(DEFAULT_FLOWS[key]))
            self._flow_vars[key] = v
            self._entry(r, v, 6).pack(side=tk.RIGHT)
        br = self._frame(body, bg=C["surface2"])
        br.pack(fill=tk.X, pady=(16, 0))
        self._btn(br, "Save map", command=self._on_save_map, primary=True).pack(side=tk.LEFT, padx=(0, 8))
        self._btn(br, "Build default", command=self._on_build_map).pack(side=tk.LEFT)

        right = self._card(inner, "Saved maps")
        right.grid(row=0, column=1, sticky=tk.NSEW)
        rb = right.body
        self.map_listbox = tk.Listbox(
            rb, height=18, font=FONT, bg=C["bg"], fg=C["text"], selectbackground=C["accent_dim"], relief=tk.FLAT
        )
        self.map_listbox.pack(fill=tk.BOTH, expand=True)
        self.map_listbox.bind("<<ListboxSelect>>", lambda _: self._on_map_list_select())
        bts = self._frame(rb, bg=C["surface2"])
        bts.pack(fill=tk.X, pady=(10, 0))
        self._btn(bts, "Load into editor", command=self._on_load_map_to_editor).pack(side=tk.LEFT, padx=(0, 8))
        self._btn(bts, "Delete", command=self._on_delete_map).pack(side=tk.LEFT)

    def _build_page_train(self):
        page = self._page("train", "Train AI")
        inner = self._frame(page, bg=C["bg"])
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        top = self._frame(inner, bg=C["bg"])
        top.pack(fill=tk.X, pady=(0, 12))
        self._label(top, "Episodes").pack(side=tk.LEFT)
        self.train_episodes = tk.StringVar(value="50")
        self._entry(top, self.train_episodes, 8).pack(side=tk.LEFT, padx=(8, 16))
        self._label(top, "Save every N ep.", muted=True).pack(side=tk.LEFT)
        self.train_checkpoint_every = tk.IntVar(value=1)
        ttk.Spinbox(top, from_=1, to=500, textvariable=self.train_checkpoint_every, width=6).pack(
            side=tk.LEFT, padx=(6, 16)
        )
        self._label(top, "Min base (s)", muted=True).pack(side=tk.LEFT)
        self.train_min_green_base = tk.StringVar(value="5")
        self._entry(top, self.train_min_green_base, 5).pack(side=tk.LEFT, padx=(4, 12))
        self._label(top, "Min green cap (s)", muted=True).pack(side=tk.LEFT)
        self.train_min_green = tk.StringVar(value="60")
        self._entry(top, self.train_min_green, 5).pack(side=tk.LEFT, padx=(4, 12))
        self._label(top, "Min cars switch", muted=True).pack(side=tk.LEFT)
        self.train_min_cars_switch = tk.StringVar(value="3")
        self._entry(top, self.train_min_cars_switch, 4).pack(side=tk.LEFT, padx=(4, 16))
        self._label(top, "Max green (0=off)", muted=True).pack(side=tk.LEFT)
        self.train_max_green = tk.StringVar(value="0")
        self._entry(top, self.train_max_green, 6).pack(side=tk.LEFT, padx=(4, 16))
        vis_row = self._frame(inner, bg=C["bg"])
        vis_row.pack(fill=tk.X, pady=(0, 8))
        self.train_live_sim_btn = self._btn(vis_row, "○  Live simulator", command=self._toggle_train_live_sim)
        self.train_live_sim_btn.pack(side=tk.LEFT, padx=(0, 12))
        self._label(vis_row, "Delay ms", muted=True).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Spinbox(vis_row, from_=0, to=500, textvariable=self.train_delay, width=6).pack(side=tk.LEFT)
        btn_row = self._frame(top, bg=C["bg"])
        btn_row.pack(side=tk.RIGHT)
        self.train_stop_btn = self._btn(btn_row, "■  Stop", command=self._on_stop_train)
        self.train_stop_btn.pack(side=tk.RIGHT, padx=(8, 0))
        self.train_start_btn = self._btn(btn_row, "▶  Start training", command=self._on_train, primary=True)
        self.train_start_btn.pack(side=tk.RIGHT)
        self._set_train_job_controls(False)
        self._label(
            inner,
            "Bulk-first: finish larger platoons on green; do not flip for one car while others still have queues.",
            muted=True,
        ).pack(anchor=tk.W)
        self._label(
            inner,
            "Min green cap = earliest switch allowed (not a fixed phase length like Compare baseline). "
            "The agent may hold longer than the cap; set Max green to force a maximum.",
            muted=True,
        ).pack(anchor=tk.W, pady=(2, 0))
        self._label(
            inner,
            "Min green grows with platoon size (tiers), not per-car. Switch when red arm has enough cars (min cars).",
            muted=True,
        ).pack(anchor=tk.W, pady=(2, 0))
        self._label(
            inner,
            "Auto-saves every episode (or every N) — safe to stop early.",
            muted=True,
        ).pack(anchor=tk.W, pady=(2, 0))
        self.train_resume_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            inner,
            text="Resume from existing dqn_policy.pth (recommended — keeps your weights)",
            variable=self.train_resume_var,
        ).pack(anchor=tk.W, pady=(4, 0))
        self._label(
            inner,
            "Episodes end when the junction clears (~40% start from a busy snapshot). "
            "Use terminal --resume for fine-tuning; avoid --fresh unless you want a new network.",
            muted=True,
        ).pack(anchor=tk.W, pady=(2, 0))
        cfg_row = self._frame(inner, bg=C["bg"])
        cfg_row.pack(fill=tk.X, pady=(8, 0))
        self._btn(cfg_row, "Edit policy config", command=self._open_policy_config).pack(side=tk.LEFT)
        self._label(cfg_row, " — goals, reward weights, hard constraints (YAML)", muted=True).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        self.train_objectives_var = tk.StringVar(
            value=f"Config: {DEFAULT_POLICY_CONFIG_PATH.relative_to(PROJECT_DIR)}"
        )
        tk.Label(inner, textvariable=self.train_objectives_var, fg=C["muted"], bg=C["bg"], font=FONT_SM).pack(
            anchor=tk.W, pady=(4, 0)
        )
        self.train_reward_parts_var = tk.StringVar(value="")
        tk.Label(inner, textvariable=self.train_reward_parts_var, fg=C["yellow"], bg=C["bg"], font=FONT_SM).pack(
            anchor=tk.W, pady=(2, 0)
        )

        prog_card = self._card(inner, "Training progress")
        prog_card.pack(fill=tk.X, pady=12)
        pb = prog_card.body
        self.train_episode_var = tk.StringVar(value="Not started")
        tk.Label(pb, textvariable=self.train_episode_var, font=FONT_LG, fg=C["text"], bg=C["surface2"]).pack(anchor=tk.W)
        self.train_reward_var = tk.StringVar(value="")
        tk.Label(pb, textvariable=self.train_reward_var, fg=C["muted"], bg=C["surface2"], font=FONT_SM).pack(
            anchor=tk.W, pady=(4, 0)
        )
        self.train_wait_var = tk.StringVar(value="")
        tk.Label(pb, textvariable=self.train_wait_var, fg=C["yellow"], bg=C["surface2"], font=FONT_SM).pack(
            anchor=tk.W, pady=(2, 8)
        )
        self.train_progress = ttk.Progressbar(pb, mode="determinate")
        self.train_progress.pack(fill=tk.X, pady=(0, 8))

        chart_card = self._card(inner, "Learning curve (live)")
        chart_card.pack(fill=tk.BOTH, expand=True)
        self._train_fig = Figure(figsize=(9, 4), dpi=100, facecolor=C["bg"])
        self._train_ax = self._train_fig.add_subplot(111)
        self._train_ax.set_facecolor(C["chart_surface"])
        self._style_ax(self._train_ax, "Episode", "Reward")
        self._train_canvas_mpl = FigureCanvasTkAgg(self._train_fig, master=chart_card.body)
        self._train_canvas_mpl.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        auto_card = self._card(inner, "Auto progress (train → compare → repeat)")
        auto_card.pack(fill=tk.X, pady=(0, 12))
        ab = auto_card.body
        cfg = CurriculumConfig.load()
        self.curriculum_cycles_var = tk.StringVar(value=str(cfg.max_cycles))
        self.curriculum_episodes_var = tk.StringVar(value=str(cfg.episodes_per_cycle))
        r1 = self._frame(ab, bg=C["surface2"])
        r1.pack(fill=tk.X, pady=(0, 8))
        self._label(r1, "Episodes / cycle").pack(side=tk.LEFT)
        self._entry(r1, self.curriculum_episodes_var, 6).pack(side=tk.LEFT, padx=(8, 20))
        self._label(r1, "Max cycles").pack(side=tk.LEFT)
        self._entry(r1, self.curriculum_cycles_var, 5).pack(side=tk.LEFT, padx=(8, 0))
        self._label(
            ab,
            "Each cycle: train N episodes → fair Compare (seed 42) → log advice → repeat until "
            "DQN beats baseline on all-vehicle wait or max cycles.",
            muted=True,
        ).pack(anchor=tk.W, pady=(0, 8))
        ar = self._frame(ab, bg=C["surface2"])
        ar.pack(fill=tk.X)
        self.curriculum_start_btn = self._btn(ar, "▶  Start auto curriculum", command=self._on_curriculum, green=True)
        self.curriculum_start_btn.pack(side=tk.RIGHT)
        self.curriculum_status_var = tk.StringVar(value="\n".join(curriculum_status_lines(3)))
        tk.Label(
            ab,
            textvariable=self.curriculum_status_var,
            fg=C["text"],
            bg=C["surface2"],
            font=FONT_SM,
            justify=tk.LEFT,
            wraplength=900,
        ).pack(anchor=tk.W, pady=(10, 0), fill=tk.X)

    def _build_page_compare(self):
        page = self._page("compare", "Compare")
        inner = self._frame(page, bg=C["bg"])
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        settings = self._frame(inner, bg=C["bg"])
        settings.pack(fill=tk.X, pady=(0, 12))
        inject_default = "800"
        try:
            from flowgrid.eval.evaluate import _compare_yaml

            inject_default = str(int(float(_compare_yaml().get("inject_seconds", 800))))
        except (ImportError, TypeError, ValueError):
            pass
        for lbl, attr, default in [
            ("Baseline green (s)", "baseline_sec", "60"),
            ("Inject until (s)", "compare_inject_sec", inject_default),
            ("Seed", "compare_seed", "42"),
        ]:
            self._label(settings, lbl, muted=True).pack(side=tk.LEFT, padx=(0, 6))
            v = tk.StringVar(value=default)
            setattr(self, attr, v)
            self._entry(settings, v, 6).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(settings, text="SUMO 3D", variable=self.compare_show_sumo).pack(side=tk.LEFT, padx=8)
        self._label(settings, "Delay ms", muted=True).pack(side=tk.LEFT, padx=(8, 4))
        ttk.Spinbox(settings, from_=0, to=500, textvariable=self.compare_delay, width=6).pack(side=tk.LEFT)
        self._btn(settings, "▶  Run comparison", command=self._on_compare, green=True).pack(side=tk.RIGHT)

        fair = self._frame(inner, bg=C["bg"])
        fair.pack(fill=tk.X, pady=(0, 8))
        self._label(
            fair,
            "Fair compare: same map, routes, seed, and a saved snapshot — baseline runs first, "
            "then DQN reloads that exact starting traffic (not a new random injection).",
            muted=True,
        ).pack(anchor=tk.W)
        self._label(
            fair,
            "Baseline = fixed Plan 2 rotation (~60 s thru / ~25 s left per step). "
            "DQN = same phases, learns when to switch and can hold longer than the min green cap.",
            muted=True,
        ).pack(anchor=tk.W, pady=(2, 0))
        self.compare_inject_hint = tk.StringVar(
            value="Inject until (s): random flows stop, then drain to 0 vehicles; DQN replays that fleet."
        )
        tk.Label(inner, textvariable=self.compare_inject_hint, fg=C["muted"], bg=C["bg"], font=FONT_SM).pack(
            anchor=tk.W, pady=(2, 0)
        )
        self.compare_delay_hint = tk.StringVar(
            value="Delay ms = pause in SUMO 3D only; 0 ms runs fastest (sim time unchanged, not wall-clock seconds)."
        )
        tk.Label(inner, textvariable=self.compare_delay_hint, fg=C["muted"], bg=C["bg"], font=FONT_SM).pack(
            anchor=tk.W, pady=(2, 0)
        )

        results = self._frame(inner, bg=C["bg"])
        results.pack(fill=tk.BOTH, expand=True)
        results.columnconfigure(0, weight=1)
        results.columnconfigure(1, weight=1)

        for col, key, title, color in [
            (0, "baseline", "1 · Fixed-time baseline", C["red"]),
            (1, "dqn", "2 · DQN agent", C["green"]),
        ]:
            card = self._card(results, title)
            card.grid(row=0, column=col, sticky=tk.NSEW, padx=(0 if col == 0 else 8, 8 if col == 0 else 0))
            b = card.body
            status_var = tk.StringVar(value="Waiting...")
            setattr(self, f"compare_{key}_status_var", status_var)
            tk.Label(b, textvariable=status_var, fg=C["muted"], bg=C["surface2"], font=FONT).pack(anchor=tk.W)
            all_lbl = tk.Label(b, text="All vehicles: —", font=FONT_LG, bg=C["surface2"])
            all_lbl.pack(anchor=tk.W, pady=(8, 2))
            setattr(self, f"compare_{key}_all_lbl", all_lbl)
            tr_lbl = tk.Label(b, text="Bus/transit: —", font=FONT_LG, bg=C["surface2"])
            tr_lbl.pack(anchor=tk.W, pady=2)
            setattr(self, f"compare_{key}_transit_lbl", tr_lbl)
            emg_lbl = tk.Label(b, text="Emergency: —", font=FONT_LG, bg=C["surface2"])
            emg_lbl.pack(anchor=tk.W, pady=2)
            setattr(self, f"compare_{key}_emg_lbl", emg_lbl)
            pri_lbl = tk.Label(b, text="Bus + emergency: —", fg=C["muted"], bg=C["surface2"], font=FONT_SM)
            pri_lbl.pack(anchor=tk.W, pady=(6, 0))
            setattr(self, f"compare_{key}_priority_lbl", pri_lbl)
            self._label(b, "Green = better vs other method (see charts below)", muted=True).pack(anchor=tk.W)

        charts_card = self._card(inner, "Comparison — lower wait is green")
        charts_card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self._cmp_summary_fig = Figure(figsize=(10, 11), dpi=100, facecolor=C["bg"])
        self._cmp_summary_axes = [
            self._cmp_summary_fig.add_subplot(311),
            self._cmp_summary_fig.add_subplot(312),
            self._cmp_summary_fig.add_subplot(313),
        ]
        self._cmp_summary_fig.subplots_adjust(hspace=0.55, top=0.96, bottom=0.06, left=0.12, right=0.96)
        titles = (
            "1 · All vehicles (cars + bus + emergency)",
            "2 · Bus / public transport only",
            "3 · Emergency vehicles only",
        )
        for ax, title in zip(self._cmp_summary_axes, titles):
            ax.set_facecolor(C["chart_surface"])
            ax.set_title(title, color=C["text"], fontsize=9, loc="left")
            self._style_ax(ax, "", "Wait sum")
        self._cmp_summary_canvas = FigureCanvasTkAgg(self._cmp_summary_fig, master=charts_card.body)
        self._cmp_summary_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.compare_imp_var = tk.StringVar(value="Run comparison to fill both panels.")
        tk.Label(inner, textvariable=self.compare_imp_var, fg=C["muted"], bg=C["bg"], font=FONT).pack(
            anchor=tk.W, pady=(12, 0)
        )

        emg_card = self._card(inner, "Emergency vehicles — wait over time")
        emg_card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self._cmp_emergency_fig = Figure(figsize=(9, 3.2), dpi=100, facecolor=C["bg"])
        self._cmp_emergency_axes = [self._cmp_emergency_fig.add_subplot(121), self._cmp_emergency_fig.add_subplot(122)]
        for ax, title in zip(self._cmp_emergency_axes, ("Fixed-Time baseline", "DQN")):
            ax.set_facecolor(C["chart_surface"])
            self._style_ax(ax, "Sim time (s)", "Emergency wait")
            ax.set_title(title, color=C["text"], fontsize=9)
        self._cmp_emergency_canvas = FigureCanvasTkAgg(self._cmp_emergency_fig, master=emg_card.body)
        self._cmp_emergency_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tr_card = self._card(inner, "Public transport (bus) — wait over time")
        tr_card.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        self._cmp_transit_fig = Figure(figsize=(9, 3.2), dpi=100, facecolor=C["bg"])
        self._cmp_transit_axes = [self._cmp_transit_fig.add_subplot(121), self._cmp_transit_fig.add_subplot(122)]
        for ax, title in zip(self._cmp_transit_axes, ("Fixed-Time baseline", "DQN")):
            ax.set_facecolor(C["chart_surface"])
            self._style_ax(ax, "Sim time (s)", "Bus wait")
            ax.set_title(title, color=C["text"], fontsize=9)
        self._cmp_transit_canvas = FigureCanvasTkAgg(self._cmp_transit_fig, master=tr_card.body)
        self._cmp_transit_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_page_reports(self):
        page = self._page("reports", "Reports")
        inner = self._frame(page, bg=C["bg"])
        inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        toolbar = self._frame(inner, bg=C["bg"])
        toolbar.pack(fill=tk.X, pady=(0, 8))
        self._label(toolbar, "Batch episodes", muted=True).pack(side=tk.LEFT)
        self.batch_episodes_filter_var = tk.StringVar(value="All episodes")
        self.batch_episodes_filter_combo = ttk.Combobox(
            toolbar, textvariable=self.batch_episodes_filter_var, width=18, state="readonly"
        )
        self.batch_episodes_filter_combo.pack(side=tk.LEFT, padx=(8, 12))
        self.batch_episodes_filter_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_batch_reports())
        self._label(toolbar, "Sort", muted=True).pack(side=tk.LEFT)
        self.batch_sort_var = tk.StringVar(value="Newest first")
        self.batch_sort_combo = ttk.Combobox(
            toolbar,
            textvariable=self.batch_sort_var,
            width=22,
            state="readonly",
            values=(
                "Newest first",
                "Oldest first",
                "Training episodes (low→high)",
                "Training episodes (high→low)",
                "Improvement % (best first)",
            ),
        )
        self.batch_sort_combo.pack(side=tk.LEFT, padx=(8, 12))
        self.batch_sort_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_batch_reports())
        self._btn(toolbar, "Refresh", command=self._refresh_reports).pack(side=tk.LEFT, padx=4)
        self._label(toolbar, "Compare map", muted=True).pack(side=tk.LEFT, padx=(12, 0))
        self.reports_filter_var = tk.StringVar(value="All maps")
        self.reports_filter_combo = ttk.Combobox(
            toolbar, textvariable=self.reports_filter_var, width=22, state="readonly"
        )
        self.reports_filter_combo.pack(side=tk.LEFT, padx=(8, 12))
        self.reports_filter_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_reports())
        self._btn(toolbar, "Clear compare history", command=self._on_clear_reports).pack(side=tk.LEFT, padx=4)

        self.reports_path_var = tk.StringVar()
        tk.Label(inner, textvariable=self.reports_path_var, fg=C["muted"], bg=C["bg"], font=FONT_SM).pack(
            anchor=tk.W, pady=(0, 4)
        )

        batch_card = self._card(inner, "Batch evaluation — RL maturity vs performance")
        batch_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self._batch_fig = Figure(figsize=(9, 3.0), dpi=100, facecolor=C["bg"])
        self._batch_ax = self._batch_fig.add_subplot(111)
        self._batch_canvas = FigureCanvasTkAgg(self._batch_fig, master=batch_card.body)
        self._batch_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        batch_cols = (
            "when",
            "map",
            "episodes",
            "runs",
            "win_rate",
            "improve",
            "avg_base",
            "avg_dqn",
        )
        batch_wrap = self._frame(batch_card.body, bg=C["surface2"])
        batch_wrap.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.batch_reports_tree = ttk.Treeview(batch_wrap, columns=batch_cols, show="headings", height=8)
        batch_headings = {
            "when": "Date / time",
            "map": "Map",
            "episodes": "Train eps",
            "runs": "Runs OK",
            "win_rate": "DQN win %",
            "improve": "Avg improve %",
            "avg_base": "Avg base wait",
            "avg_dqn": "Avg DQN wait",
        }
        batch_widths = {
            "when": 145,
            "map": 150,
            "episodes": 72,
            "runs": 72,
            "win_rate": 78,
            "improve": 92,
            "avg_base": 100,
            "avg_dqn": 100,
        }
        for col in batch_cols:
            self.batch_reports_tree.heading(col, text=batch_headings[col])
            anchor = tk.W if col in ("when", "map") else tk.CENTER
            self.batch_reports_tree.column(col, width=batch_widths[col], anchor=anchor, minwidth=48)
        self.batch_reports_tree.tag_configure("positive", foreground=C["green"])
        self.batch_reports_tree.tag_configure("negative", foreground=C["red"])
        self.batch_reports_tree.tag_configure("neutral", foreground=C["muted"])
        batch_vsb = ttk.Scrollbar(batch_wrap, orient=tk.VERTICAL, command=self.batch_reports_tree.yview)
        self.batch_reports_tree.configure(yscrollcommand=batch_vsb.set)
        self.batch_reports_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        batch_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_summary_var = tk.StringVar(value="Run scripts/run_evaluate.py to record batch results.")
        tk.Label(batch_card.body, textvariable=self.batch_summary_var, fg=C["muted"], bg=C["surface2"], font=FONT_SM).pack(
            anchor=tk.W, pady=(6, 0)
        )

        train_card = self._card(inner, "Training progress (DQN)")
        train_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self._train_dash_fig = Figure(figsize=(9, 3.6), dpi=100, facecolor=C["bg"])
        self._train_dash_ax = self._train_dash_fig.add_subplot(111)
        self._train_dash_canvas = FigureCanvasTkAgg(self._train_dash_fig, master=train_card.body)
        self._train_dash_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.train_dash_var = tk.StringVar(value="")
        tk.Label(train_card.body, textvariable=self.train_dash_var, fg=C["muted"], bg=C["surface2"], font=FONT_SM).pack(
            anchor=tk.W, pady=(6, 0)
        )

        all_chart_card = self._card(inner, "Compare history — all vehicles wait")
        all_chart_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self._reports_all_fig = Figure(figsize=(9, 2.8), dpi=100, facecolor=C["bg"])
        self._reports_all_ax = self._reports_all_fig.add_subplot(111)
        self._reports_all_canvas = FigureCanvasTkAgg(self._reports_all_fig, master=all_chart_card.body)
        self._reports_all_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        chart_card = self._card(inner, "Compare history — bus + emergency wait")
        chart_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self._reports_fig = Figure(figsize=(9, 3.2), dpi=100, facecolor=C["bg"])
        self._reports_ax = self._reports_fig.add_subplot(111)
        self._reports_canvas = FigureCanvasTkAgg(self._reports_fig, master=chart_card.body)
        self._reports_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        emg_chart_card = self._card(inner, "Progress — emergency vehicle wait per run")
        emg_chart_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self._reports_emg_fig = Figure(figsize=(9, 3.2), dpi=100, facecolor=C["bg"])
        self._reports_emg_ax = self._reports_emg_fig.add_subplot(111)
        self._reports_emg_canvas = FigureCanvasTkAgg(self._reports_emg_fig, master=emg_chart_card.body)
        self._reports_emg_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        tr_chart_card = self._card(inner, "Progress — public transport wait per run")
        tr_chart_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self._reports_transit_fig = Figure(figsize=(9, 3.2), dpi=100, facecolor=C["bg"])
        self._reports_transit_ax = self._reports_transit_fig.add_subplot(111)
        self._reports_transit_canvas = FigureCanvasTkAgg(self._reports_transit_fig, master=tr_chart_card.body)
        self._reports_transit_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        table_card = self._card(inner, "Saved comparisons")
        table_card.pack(fill=tk.BOTH, expand=True)
        cols = (
            "when",
            "map",
            "seed",
            "base_s",
            "baseline",
            "dqn",
            "improve",
            "tr_base",
            "tr_dqn",
            "tr_imp",
            "emg_base",
            "emg_dqn",
            "emg_imp",
            "note",
        )
        tree_wrap = self._frame(table_card.body, bg=C["surface2"])
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        self.reports_tree = ttk.Treeview(tree_wrap, columns=cols, show="headings", height=12)
        headings = {
            "when": "Date / time",
            "map": "Map",
            "seed": "Seed",
            "base_s": "Baseline green (s)",
            "baseline": "Bus+emg base",
            "dqn": "Bus+emg DQN",
            "improve": "Improve %",
            "tr_base": "Bus base",
            "tr_dqn": "Bus DQN",
            "tr_imp": "Bus Δ %",
            "emg_base": "Emg base",
            "emg_dqn": "Emg DQN",
            "emg_imp": "Emg Δ %",
            "note": "Note",
        }
        widths = {
            "when": 120,
            "map": 95,
            "seed": 40,
            "base_s": 85,
            "baseline": 72,
            "dqn": 62,
            "improve": 58,
            "tr_base": 62,
            "tr_dqn": 58,
            "tr_imp": 54,
            "emg_base": 62,
            "emg_dqn": 58,
            "emg_imp": 54,
            "note": 80,
        }
        for col in cols:
            self.reports_tree.heading(col, text=headings[col])
            anchor = tk.W if col in ("when", "map", "note") else tk.CENTER
            self.reports_tree.column(col, width=widths[col], anchor=anchor, minwidth=40)
        vsb = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL, command=self.reports_tree.yview)
        self.reports_tree.configure(yscrollcommand=vsb.set)
        self.reports_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.reports_summary_var = tk.StringVar(value="Run a comparison to record results here.")
        tk.Label(inner, textvariable=self.reports_summary_var, fg=C["muted"], bg=C["bg"], font=FONT_SM).pack(
            anchor=tk.W, pady=(10, 0)
        )
        self.reports_curriculum_var = tk.StringVar(value="")
        tk.Label(inner, textvariable=self.reports_curriculum_var, fg=C["text"], bg=C["bg"], font=FONT_SM).pack(
            anchor=tk.W, pady=(6, 0)
        )
        self._refresh_reports()

    def _filtered_report_records(self) -> list[dict]:
        records = load_history()
        filt = self.reports_filter_var.get()
        if filt and filt != "All maps":
            records = [r for r in records if r.get("map_name") == filt or r.get("map_id") == filt]
        return records

    def _batch_improvement_tag(self, improvement: float | None) -> str:
        if improvement is None:
            return "neutral"
        if improvement > 0:
            return "positive"
        if improvement < 0:
            return "negative"
        return "neutral"

    def _filtered_batch_records(self) -> list:
        records = parse_batch_evaluation_log()
        filt = self.batch_episodes_filter_var.get() if self.batch_episodes_filter_var else "All episodes"
        if filt and filt != "All episodes":
            try:
                target = int(filt.split()[0])
                records = [r for r in records if r.training_episodes == target]
            except ValueError:
                if filt.lower() == "unknown":
                    records = [r for r in records if r.training_episodes is None]
        sort_key = self.batch_sort_var.get() if self.batch_sort_var else "Newest first"
        if sort_key == "Oldest first":
            return records
        if sort_key == "Training episodes (low→high)":
            return sorted(
                records,
                key=lambda r: (r.training_episodes is None, r.training_episodes or -1, r.timestamp),
            )
        if sort_key == "Training episodes (high→low)":
            return sorted(
                records,
                key=lambda r: (
                    r.training_episodes is None,
                    -(r.training_episodes if r.training_episodes is not None else 0),
                ),
            )
        if sort_key == "Improvement % (best first)":
            return sorted(
                records,
                key=lambda r: (
                    r.avg_improvement_pct is None,
                    -(r.avg_improvement_pct or 0.0),
                    r.timestamp,
                ),
            )
        return list(reversed(records))

    def _refresh_batch_reports(self):
        if self.batch_reports_tree is None:
            return
        records = self._filtered_batch_records()
        all_records = parse_batch_evaluation_log()
        episode_values = sorted(
            {r.training_episodes for r in all_records if r.training_episodes is not None}
        )
        filter_values = ["All episodes"] + [f"{n} episodes" for n in episode_values]
        if any(r.training_episodes is None for r in all_records):
            filter_values.append("Unknown")
        self.batch_episodes_filter_combo["values"] = filter_values
        if self.batch_episodes_filter_var.get() not in filter_values:
            self.batch_episodes_filter_var.set("All episodes")

        for row in self.batch_reports_tree.get_children():
            self.batch_reports_tree.delete(row)
        for rec in records:
            imp = rec.avg_improvement_pct
            imp_s = f"{imp:+.1f}" if imp is not None else "—"
            win_s = f"{rec.win_rate_pct:.1f}" if rec.win_rate_pct is not None else "—"
            eps_s = str(rec.training_episodes) if rec.training_episodes is not None else "Unknown"
            base_s = f"{rec.avg_baseline_wait:,.0f}" if rec.avg_baseline_wait is not None else "—"
            dqn_s = f"{rec.avg_dqn_wait:,.0f}" if rec.avg_dqn_wait is not None else "—"
            runs_s = f"{rec.runs_ok}/{rec.runs_total}"
            tag = self._batch_improvement_tag(imp)
            self.batch_reports_tree.insert(
                "",
                tk.END,
                values=(
                    rec.timestamp,
                    rec.map_display,
                    eps_s,
                    runs_s,
                    win_s,
                    imp_s,
                    base_s,
                    dqn_s,
                ),
                tags=(tag,),
            )

        ax = self._batch_ax
        ax.clear()
        ax.set_facecolor(C["chart_surface"])
        plot_records = [r for r in records if r.training_episodes is not None and r.avg_improvement_pct is not None]
        if not plot_records:
            ax.text(
                0.5,
                0.5,
                "No batch evaluation data yet",
                ha="center",
                va="center",
                color=C["muted"],
                transform=ax.transAxes,
            )
            self._style_ax(ax, "Training episodes", "Avg wait improvement %")
            self.batch_summary_var.set("Run scripts/run_evaluate.py to record batch results.")
        else:
            xs = [float(r.training_episodes) for r in plot_records]
            ys = [float(r.avg_improvement_pct) for r in plot_records]
            colors = [C["green"] if y > 0 else C["red"] if y < 0 else C["muted"] for y in ys]
            ax.axhline(0.0, color=C["muted"], linewidth=1.0, linestyle="--", alpha=0.6)
            ax.scatter(xs, ys, c=colors, s=70, zorder=3)
            for rec in plot_records:
                if rec.avg_baseline_wait is not None and rec.avg_dqn_wait is not None:
                    ax.annotate(
                        f"{rec.win_rate_pct:.0f}% wins" if rec.win_rate_pct is not None else "",
                        (float(rec.training_episodes), float(rec.avg_improvement_pct)),
                        textcoords="offset points",
                        xytext=(0, 8),
                        ha="center",
                        fontsize=7,
                        color=C["muted"],
                    )
            self._style_ax(ax, "Model training episodes", "Avg wait improvement % (batch mean)")
            imps = [r.avg_improvement_pct for r in plot_records if r.avg_improvement_pct is not None]
            wins = [r.win_rate_pct for r in plot_records if r.win_rate_pct is not None]
            avg_imp = sum(imps) / len(imps) if imps else 0.0
            avg_win = sum(wins) / len(wins) if wins else 0.0
            self.batch_summary_var.set(
                f"{len(all_records)} batch run(s) in log · showing {len(records)} · "
                f"avg improvement {avg_imp:+.1f}% · avg win rate {avg_win:.1f}%"
            )
        self._batch_canvas.draw()
        try:
            batch_rel = batch_evaluation_log_path().relative_to(PROJECT_DIR)
        except ValueError:
            batch_rel = batch_evaluation_log_path()
        try:
            compare_rel = comparison_history_path().relative_to(PROJECT_DIR)
        except ValueError:
            compare_rel = comparison_history_path()
        self.reports_path_var.set(f"Batch log: {batch_rel}  ·  Compare history: {compare_rel}")

    def _refresh_curriculum_summary(self):
        lines = curriculum_status_lines(6)
        self.reports_curriculum_var.set("\n".join(lines))

    def _refresh_training_dashboard(self):
        if self._train_dash_ax is None:
            return
        dash = load_training_dashboard(DQN_TRAINING_LOG_PATH)
        ax = self._train_dash_ax
        ax.clear()
        ax.set_facecolor(C["chart_surface"])
        if dash.episode_waits:
            xs = [p[0] for p in dash.episode_waits]
            ys = [p[1] for p in dash.episode_waits]
            ax.plot(xs, ys, color=C["green"], linewidth=1.2, alpha=0.85)
            if len(ys) >= 20:
                win = max(10, len(ys) // 40)
                smooth = []
                for i in range(len(ys)):
                    lo = max(0, i - win)
                    smooth.append(sum(ys[lo : i + 1]) / (i - lo + 1))
                ax.plot(xs, smooth, color=C["yellow"], linewidth=2, label="moving avg")
                ax.legend(**legend_style())
            self._style_ax(ax, "Episode", "Total wait (training)")
        else:
            ax.text(0.5, 0.5, "No episodes in log", ha="center", va="center", color=C["muted"], transform=ax.transAxes)
            self._style_ax(ax, "Episode", "Total wait")
        self._train_dash_canvas.draw()
        try:
            log_rel = DQN_TRAINING_LOG_PATH.relative_to(PROJECT_DIR)
        except ValueError:
            log_rel = DQN_TRAINING_LOG_PATH
        lines = [f"Log: {log_rel}"] + dash.summary_lines()
        self.train_dash_var.set("\n".join(lines))

    def _refresh_reports(self):
        if self.reports_tree is None:
            return
        self._refresh_batch_reports()
        self._refresh_training_dashboard()
        self._refresh_curriculum_summary()

        all_records = load_history()
        map_names = sorted({r.get("map_name", "") for r in all_records if r.get("map_name")})
        filter_values = ["All maps"] + map_names
        self.reports_filter_combo["values"] = filter_values
        if self.reports_filter_var.get() not in filter_values:
            self.reports_filter_var.set("All maps")

        records = self._filtered_report_records()
        for row in self.reports_tree.get_children():
            self.reports_tree.delete(row)
        for rec in reversed(records):
            imp = rec.get("improvement_percent")
            imp_s = f"{imp:+.1f}" if isinstance(imp, (int, float)) else "—"
            dqn_w = rec.get("dqn_wait", 0)
            note = rec.get("model_error") or ""
            if not note and dqn_w <= 0:
                note = "DQN missing"
            tr_b = rec.get("baseline_transit_wait")
            tr_d = rec.get("dqn_transit_wait")
            tr_imp = rec.get("transit_improvement_percent")
            tr_imp_s = f"{tr_imp:+.1f}" if isinstance(tr_imp, (int, float)) else "—"
            emg_b = rec.get("baseline_emergency_wait")
            emg_d = rec.get("dqn_emergency_wait")
            emg_imp = rec.get("emergency_improvement_percent")
            emg_imp_s = f"{emg_imp:+.1f}" if isinstance(emg_imp, (int, float)) else "—"
            self.reports_tree.insert(
                "",
                tk.END,
                values=(
                    rec.get("timestamp_display") or rec.get("timestamp", ""),
                    rec.get("map_name", ""),
                    rec.get("seed", ""),
                    rec.get("baseline_green_seconds", ""),
                    int(rec.get("baseline_wait", 0)),
                    int(dqn_w) if dqn_w else "—",
                    imp_s,
                    int(tr_b) if tr_b is not None else "—",
                    int(tr_d) if tr_d is not None and dqn_w else "—",
                    tr_imp_s,
                    int(emg_b) if emg_b is not None else "—",
                    int(emg_d) if emg_d is not None and dqn_w else "—",
                    emg_imp_s,
                    note[:50],
                ),
            )

        ax = self._reports_ax
        ax.clear()
        ax.set_facecolor(C["chart_surface"])
        if not records:
            ax.text(0.5, 0.5, "No runs yet", ha="center", va="center", color=C["muted"], transform=ax.transAxes)
            self._style_ax(ax, "Run #", "Total wait")
            self.reports_summary_var.set("No comparison runs saved yet.")
        else:
            xs = list(range(1, len(records) + 1))
            baseline_vals = [float(r.get("baseline_wait", 0)) for r in records]
            dqn_vals = [float(r.get("dqn_wait", 0)) if r.get("dqn_wait", 0) else None for r in records]
            ax.plot(xs, baseline_vals, color=C["red"], marker="o", linewidth=2, label="Baseline")
            dqn_plot = [v if v is not None else float("nan") for v in dqn_vals]
            ax.plot(xs, dqn_plot, color=C["green"], marker="o", linewidth=2, label="DQN")
            ax.legend(**legend_style())
            self._style_ax(ax, "Run (oldest → newest)", "Bus + emergency wait")
            imps = [r.get("improvement_percent") for r in records if r.get("dqn_wait", 0) > 0]
            avg_imp = sum(imps) / len(imps) if imps else 0.0
            self.reports_summary_var.set(
                f"{len(records)} run(s) · avg bus+emergency improvement {avg_imp:+.1f}% (saved baseline/dqn columns)"
            )
        self._reports_canvas.draw()

        ax_emg = self._reports_emg_ax
        ax_emg.clear()
        ax_emg.set_facecolor(C["chart_surface"])
        emg_records = [
            r
            for r in records
            if r.get("baseline_emergency_wait") is not None or r.get("dqn_emergency_wait") is not None
        ]
        if not emg_records:
            ax_emg.text(0.5, 0.5, "No emergency metrics yet", ha="center", va="center", color=C["muted"], transform=ax_emg.transAxes)
            self._style_ax(ax_emg, "Run #", "Emergency wait sum")
        else:
            xs = list(range(1, len(emg_records) + 1))
            emg_base = [float(r.get("baseline_emergency_wait", 0)) for r in emg_records]
            emg_dqn = [
                float(r.get("dqn_emergency_wait", 0)) if r.get("dqn_wait", 0) else float("nan")
                for r in emg_records
            ]
            ax_emg.plot(xs, emg_base, color=C["red"], marker="o", linewidth=2, label="Baseline")
            ax_emg.plot(xs, emg_dqn, color=C["green"], marker="o", linewidth=2, label="DQN")
            ax_emg.legend(**legend_style())
            self._style_ax(ax_emg, "Run (oldest → newest)", "Emergency wait (sum per step)")
        self._reports_emg_canvas.draw()

        ax_all = self._reports_all_ax
        ax_all.clear()
        ax_all.set_facecolor(C["chart_surface"])
        all_records = [r for r in records if r.get("baseline_wait_all") or r.get("dqn_wait_all")]
        if not all_records:
            ax_all.text(0.5, 0.5, "No all-vehicle metrics yet", ha="center", va="center", color=C["muted"], transform=ax_all.transAxes)
            self._style_ax(ax_all, "Run #", "All vehicles wait")
        else:
            xs = list(range(1, len(all_records) + 1))
            b_all = [float(r.get("baseline_wait_all", 0)) for r in all_records]
            d_all = [
                float(r.get("dqn_wait_all", 0)) if r.get("dqn_wait_all", 0) else float("nan")
                for r in all_records
            ]
            ax_all.plot(xs, b_all, color=C["red"], marker="o", linewidth=2, label="Baseline")
            ax_all.plot(xs, d_all, color=C["green"], marker="o", linewidth=2, label="DQN")
            ax_all.legend(**legend_style())
            self._style_ax(ax_all, "Run (oldest → newest)", "All vehicles wait (lower is better)")
        self._reports_all_canvas.draw()

        ax_tr = self._reports_transit_ax
        ax_tr.clear()
        ax_tr.set_facecolor(C["chart_surface"])
        tr_records = [
            r
            for r in records
            if r.get("baseline_transit_wait") is not None or r.get("dqn_transit_wait") is not None
        ]
        if not tr_records:
            ax_tr.text(
                0.5, 0.5, "No transit metrics yet", ha="center", va="center", color=C["muted"], transform=ax_tr.transAxes
            )
            self._style_ax(ax_tr, "Run #", "Bus wait sum")
        else:
            xs = list(range(1, len(tr_records) + 1))
            tr_base = [float(r.get("baseline_transit_wait", 0)) for r in tr_records]
            tr_dqn = [
                float(r.get("dqn_transit_wait", 0)) if r.get("dqn_wait", 0) else float("nan")
                for r in tr_records
            ]
            ax_tr.plot(xs, tr_base, color=C["red"], marker="o", linewidth=2, label="Baseline")
            ax_tr.plot(xs, tr_dqn, color=C["success"], marker="o", linewidth=2, label="DQN")
            ax_tr.legend(**legend_style())
            self._style_ax(ax_tr, "Run (oldest → newest)", "Bus/transit wait (sum per step)")
        self._reports_transit_canvas.draw()

    def _on_clear_reports(self):
        if not messagebox.askyesno("Clear history", "Delete all saved comparison reports?"):
            return
        n = clear_history()
        self._log(f"Cleared {n} comparison report(s).")
        self._refresh_reports()

    def _style_ax(self, ax, xlabel: str, ylabel: str):
        style_matplotlib_axes(ax, xlabel, ylabel)

    def _log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def _collect_flows(self) -> dict[str, float]:
        return {k: float(v.get()) for k, v in self._flow_vars.items()}

    def _refresh_map_list(self):
        ensure_default_map()
        self._saved_maps = list_maps_for_gui()
        labels = [m["display_name"] for m in self._saved_maps]
        self.active_map_combo["values"] = labels
        self.map_listbox.delete(0, tk.END)
        for m in self._saved_maps:
            self.map_listbox.insert(tk.END, m["display_name"])
        if labels and not self.active_map_var.get():
            self.active_map_var.set(labels[0])
        elif labels and self.active_map_var.get() not in labels:
            self.active_map_var.set(labels[0])

    def _get_active_map(self) -> dict | None:
        name = self.active_map_var.get()
        for m in self._saved_maps:
            if m["display_name"] == name:
                return m
        return self._saved_maps[0] if self._saved_maps else None

    def _on_active_map_changed(self):
        m = self._get_active_map()
        if m:
            self._log(f"Active map: {m['display_name']}")
            if hasattr(self, "baseline_sec"):
                self.baseline_sec.set(str(m.get("baseline_through_seconds", 60)))

    def _on_map_list_select(self):
        sel = self.map_listbox.curselection()
        if sel:
            self.active_map_var.set(self.map_listbox.get(sel[0]))

    def _phasing_scheme_from_ui(self) -> str:
        label = self._phasing_combo.get()
        return self._phasing_by_label.get(label, DEFAULT_SCHEME)

    def _set_phasing_combo(self, scheme_key: str):
        self.phasing_scheme_var.set(scheme_key)
        self._phasing_combo.set(SCHEME_LABELS.get(scheme_key, SCHEME_LABELS[DEFAULT_SCHEME]))

    def _fill_editor_from_map(self, m: dict):
        self.map_save_name_var.set(m["display_name"])
        self.arm_length_var.set(str(m["arm_length"]))
        self._set_phasing_combo(m.get("phasing_scheme", DEFAULT_SCHEME))
        self.separate_right_var.set(bool(m.get("separate_right_turn", True)))
        self.baseline_through_var.set(str(m.get("baseline_through_seconds", 60)))
        self.baseline_left_ratio_var.set(str(m.get("baseline_left_to_through_ratio", 0.60)))
        for key, val in m.get("flows", {}).items():
            if key in self._flow_vars:
                self._flow_vars[key].set(str(val))

    def _on_load_map_to_editor(self):
        m = self._get_active_map()
        if not m:
            messagebox.showinfo("Maps", "No saved maps.")
            return
        self._fill_editor_from_map(m)
        self._show_page("map")
        self._log(f"Loaded: {m['display_name']}")

    def _on_save_map(self):
        name = self.map_save_name_var.get().strip()
        if not name:
            messagebox.showerror("Save map", "Enter a map name.")
            return
        try:
            flows = self._collect_flows()
            arm = int(self.arm_length_var.get())
            thru_sec = float(self.baseline_through_var.get())
            left_ratio = float(self.baseline_left_ratio_var.get())
        except ValueError:
            messagebox.showerror("Save map", "Check numeric fields.")
            return
        overwrite = False
        if get_map(slugify_map_name(name)):
            overwrite = messagebox.askyesno("Overwrite?", f"Overwrite existing map '{name}'?")
            if not overwrite:
                return

        def work():
            try:
                preset = save_map(
                    name,
                    arm,
                    flows,
                    overwrite=overwrite,
                    phasing_scheme=self._phasing_scheme_from_ui(),
                    separate_right_turn=bool(self.separate_right_var.get()),
                    baseline_through_seconds=thru_sec,
                    baseline_left_to_through_ratio=left_ratio,
                )
                self.root.after(0, lambda: self._save_map_ok(preset))
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Save failed", str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _save_map_ok(self, preset):
        self._refresh_map_list()
        self.active_map_var.set(preset.display_name)
        self._log(f"Saved map: {preset.display_name}")
        messagebox.showinfo("Saved", f"Map saved: data/maps/{preset.id}/")

    def _on_delete_map(self):
        m = self._get_active_map()
        if not m or m["id"] == "flowgrid":
            messagebox.showwarning("Delete", "Cannot delete default map.")
            return
        if messagebox.askyesno("Delete", f"Delete '{m['display_name']}'?"):
            if delete_map(m["id"]):
                self._refresh_map_list()

    def _on_build_map(self):
        def work():
            try:
                info = build_map("flowgrid", int(self.arm_length_var.get()), self._collect_flows())
                def ok():
                    self._refresh_map_list()
                    self._log(f"Built: {info.get('sumocfg', 'ok')}")

                self.root.after(0, ok)
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Build failed", str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _wait_win_color(self, baseline_val: float, dqn_val: float, side: str) -> str:
        baseline_better = baseline_val <= dqn_val
        if side == "baseline":
            return C["green"] if baseline_better else C["red"]
        return C["red"] if baseline_better else C["green"]

    def _draw_compare_summary_charts(self, r: dict) -> None:
        series = [
            ("baseline_wait_all", "dqn_wait_all"),
            ("baseline_transit_wait", "dqn_transit_wait"),
            ("baseline_emergency_wait", "dqn_emergency_wait"),
        ]
        for ax, keys in zip(self._cmp_summary_axes, series):
            ax.clear()
            ax.set_facecolor(C["chart_surface"])
            b_val = float(r.get(keys[0], 0))
            d_val = float(r.get(keys[1], 0))
            labels = ["Baseline", "DQN"]
            values = [b_val, d_val]
            colors = self._wait_win_color(b_val, d_val, "baseline"), self._wait_win_color(b_val, d_val, "dqn")
            bars = ax.bar(labels, values, color=list(colors), width=0.42)
            ymax = max(values) if max(values) > 0 else 1
            for bar, v in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    v + ymax * 0.04,
                    str(int(v)),
                    ha="center",
                    fontsize=9,
                    color=C["text"],
                )
            winner = "Baseline" if b_val <= d_val else "DQN"
            ax.text(
                0.98,
                0.95,
                f"Better: {winner}",
                transform=ax.transAxes,
                ha="right",
                va="top",
                color=C["green"],
                fontsize=9,
            )
            self._style_ax(ax, "", "Wait sum")
            ax.tick_params(axis="x", pad=6)
        if self._cmp_summary_fig:
            self._cmp_summary_fig.subplots_adjust(hspace=0.55, top=0.96, bottom=0.06, left=0.12, right=0.96)
        if self._cmp_summary_canvas:
            self._cmp_summary_canvas.draw()

    def _refresh_compare_panel_labels(self, r: dict) -> None:
        b_all = float(r.get("baseline_wait_all", 0))
        d_all = float(r.get("dqn_wait_all", 0))
        b_bus = float(r.get("baseline_transit_wait", 0))
        d_bus = float(r.get("dqn_transit_wait", 0))
        b_emg = float(r.get("baseline_emergency_wait", 0))
        d_emg = float(r.get("dqn_emergency_wait", 0))
        sched_cars = int(r.get("compare_scheduled_cars", 0) or 0)
        sched_bus = int(r.get("compare_scheduled_transit", 0) or 0)
        sched_emg = int(r.get("compare_scheduled_emergency", 0) or 0)
        b_all_n = int(r.get("baseline_all_vehicles", 0) or 0)
        d_all_n = int(r.get("dqn_all_vehicles", 0) or 0)
        b_bus_n = int(r.get("baseline_transit_vehicles", 0) or 0)
        d_bus_n = int(r.get("dqn_transit_vehicles", 0) or 0)
        b_emg_n = int(r.get("baseline_emergency_vehicles", 0) or 0)
        d_emg_n = int(r.get("dqn_emergency_vehicles", 0) or 0)
        for side, all_v, bus_v, emg_v, all_n, bus_n, emg_n in (
            ("baseline", b_all, b_bus, b_emg, b_all_n, b_bus_n, b_emg_n),
            ("dqn", d_all, d_bus, d_emg, d_all_n, d_bus_n, d_emg_n),
        ):
            getattr(self, f"compare_{side}_all_lbl").configure(
                text=f"All vehicles: {int(all_v)} wait · {all_n}/{sched_cars + sched_bus + sched_emg} served",
                fg=self._wait_win_color(b_all, d_all, side),
            )
            getattr(self, f"compare_{side}_transit_lbl").configure(
                text=f"Bus/transit: {int(bus_v)} wait · {bus_n}/{sched_bus} buses",
                fg=self._wait_win_color(b_bus, d_bus, side),
            )
            getattr(self, f"compare_{side}_emg_lbl").configure(
                text=f"Emergency: {int(emg_v)} wait · {emg_n}/{sched_emg} emergencies",
                fg=self._wait_win_color(b_emg, d_emg, side),
            )
            getattr(self, f"compare_{side}_priority_lbl").configure(
                text=f"Bus + emergency: {int(bus_v + emg_v)}",
            )

    def _reset_compare_panels(self):
        for key in ("baseline", "dqn"):
            getattr(self, f"compare_{key}_status_var").set("Waiting...")
            getattr(self, f"compare_{key}_all_lbl").configure(text="All vehicles: —", fg=C["muted"])
            getattr(self, f"compare_{key}_transit_lbl").configure(text="Bus/transit: —", fg=C["muted"])
            getattr(self, f"compare_{key}_emg_lbl").configure(text="Emergency: —", fg=C["muted"])
            getattr(self, f"compare_{key}_priority_lbl").configure(text="Bus + emergency: —")
        for ax in self._cmp_summary_axes:
            ax.clear()
            ax.set_facecolor(C["chart_surface"])
            self._style_ax(ax, "", "Wait sum")
        if self._cmp_summary_canvas:
            self._cmp_summary_canvas.draw()
        for ax in self._cmp_transit_axes:
            ax.clear()
            ax.set_facecolor(C["chart_surface"])
            self._style_ax(ax, "Sim time (s)", "Bus wait")
        if self._cmp_transit_canvas:
            self._cmp_transit_canvas.draw()
        for ax in self._cmp_emergency_axes:
            ax.clear()
            ax.set_facecolor(C["chart_surface"])
            self._style_ax(ax, "Sim time (s)", "Emergency wait")
        if self._cmp_emergency_canvas:
            self._cmp_emergency_canvas.draw()
        self.compare_imp_var.set("Running...")

    def _on_train(self):
        if self._train_job_active:
            return
        if self.current_job_id:
            messagebox.showwarning("Busy", "Wait for the current job to finish.")
            return
        try:
            episodes = int(self.train_episodes.get())
            checkpoint_every = max(1, int(self.train_checkpoint_every.get()))
            min_green = float(self.train_min_green.get())
            min_base = float(self.train_min_green_base.get())
            min_cars_switch = int(self.train_min_cars_switch.get())
            max_green = float(self.train_max_green.get())
            max_green_opt = max_green if max_green > 0 else None
        except ValueError:
            messagebox.showerror("Input", "Check episodes, save interval, and green times.")
            return
        m = self._get_active_map()
        if not m:
            messagebox.showerror("Train", "Select a map first.")
            return
        resume = bool(self.train_resume_var.get())
        if resume and not policy_checkpoint_exists(m["policy_path"]):
            messagebox.showwarning(
                "Train",
                "No checkpoint found for this map. Starting a fresh training run.",
            )
            resume = False
            self.train_resume_var.set(False)
        curve = str(Path(m["policy_path"]).parent / "learning_curve.png")
        self._last_train_chart = Path(curve)
        self._show_page("train")
        self.train_episode_var.set("Starting...")
        self.train_reward_var.set("")
        self.train_wait_var.set("")
        self.train_progress["value"] = 0
        self._train_ax.clear()
        self._train_ax.set_facecolor(C["chart_surface"])
        self._style_ax(self._train_ax, "Episode", "Reward")
        self._train_canvas_mpl.draw()
        self._log(
            f"Training {m['display_name']} ({episodes} episodes, save every {checkpoint_every})..."
        )
        self._set_train_job_controls(True)
        self.current_job_id = self.runner.start_train(
            m["sumocfg"],
            episodes,
            policy_path=m["policy_path"],
            learning_curve_path=curve,
            checkpoint_every=checkpoint_every,
            min_green_seconds=min_green,
            min_green_base_seconds=min_base,
            switch_min_vehicles=min_cars_switch,
            switch_min_wait_seconds=25.0,
            max_green_seconds=max_green_opt,
            map_name=m["display_name"],
            map_id=m["id"],
            resume=resume,
            gui=bool(self.train_show_sumo.get()),
            gui_delay=int(self.train_delay.get()),
            quiet=True,
        )

    def _open_policy_config(self):
        cfg = PolicyConfig.load()
        path = Path(cfg.source_path) if cfg.source_path else DEFAULT_POLICY_CONFIG_PATH
        if not path.is_file():
            messagebox.showerror("Policy config", f"File not found:\n{path}")
            return
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError:
            messagebox.showinfo("Policy config", f"Open this file in an editor:\n{path}")

    def _on_stop_train(self):
        if not self._train_job_active or not self.current_job_id:
            return
        job = self.runner.get_job(self.current_job_id)
        if job and job.kind in ("train", "curriculum") and job.status == "running":
            if self.runner.request_cancel(self.current_job_id):
                self._set_btn_enabled(self.train_stop_btn, False)
                if job.kind == "curriculum":
                    self.curriculum_status_var.set("Stopping after current step...")
                else:
                    self.train_episode_var.set("Stopping… saving checkpoint")
                self._log("Stop requested — saving checkpoint when the current episode ends.")

    def _on_curriculum(self):
        if self._train_job_active:
            return
        if self.current_job_id:
            messagebox.showwarning("Busy", "Wait for the current job to finish.")
            return
        try:
            max_cycles = max(1, int(self.curriculum_cycles_var.get()))
            episodes_per = max(1, int(self.curriculum_episodes_var.get()))
        except ValueError:
            messagebox.showerror("Input", "Episodes per cycle and max cycles must be numbers.")
            return
        m = self._get_active_map()
        if not m:
            messagebox.showerror("Curriculum", "Select a map first.")
            return
        cfg = CurriculumConfig.load()
        cfg = CurriculumConfig(
            episodes_per_cycle=episodes_per,
            max_cycles=max_cycles,
            compare_seed=cfg.compare_seed,
            compare_inject_seconds=cfg.compare_inject_seconds,
            compare_gui=cfg.compare_gui,
            compare_delay_ms=cfg.compare_delay_ms,
            baseline_green_seconds=cfg.baseline_green_seconds,
            stop_when_all_improvement_pct=cfg.stop_when_all_improvement_pct,
            min_cycles=cfg.min_cycles,
            resume_after_first_cycle=cfg.resume_after_first_cycle,
        )
        curve = str(Path(m["policy_path"]).parent / "learning_curve.png")
        self._show_page("train")
        self._log(f"Auto curriculum: {episodes_per} ep × {max_cycles} cycles on {m['display_name']}...")
        self.curriculum_status_var.set("Starting...")
        try:
            min_g = float(self.train_min_green.get())
            min_base = float(self.train_min_green_base.get())
            min_cars = int(self.train_min_cars_switch.get())
            max_g = float(self.train_max_green.get())
            max_g_opt = max_g if max_g > 0 else None
        except ValueError:
            messagebox.showerror("Input", "Check green time fields on the Train tab.")
            return
        self._set_train_job_controls(True)
        self.current_job_id = self.runner.start_curriculum(
            m["sumocfg"],
            m["policy_path"],
            curve,
            map_id=m["id"],
            map_name=m["display_name"],
            min_green_seconds=min_g,
            min_green_base_seconds=min_base,
            switch_min_vehicles=min_cars,
            switch_min_wait_seconds=25.0,
            max_green_seconds=max_g_opt,
            checkpoint_every=max(1, int(self.train_checkpoint_every.get())),
            curriculum=cfg,
            gui=bool(self.train_show_sumo.get()),
            gui_delay=int(self.train_delay.get()),
            quiet=True,
        )

    def _on_compare(self):
        if self.current_job_id:
            messagebox.showwarning("Busy", "Wait for the current job.")
            return
        try:
            baseline = float(self.baseline_sec.get())
            inject_sec = float(self.compare_inject_sec.get())
            seed = int(self.compare_seed.get())
            if inject_sec < 60:
                raise ValueError("inject too small")
        except ValueError:
            messagebox.showerror("Input", "Invalid baseline, inject time, or seed.")
            return
        m = self._get_active_map()
        if not m:
            messagebox.showerror("Compare", "Select a map first.")
            return
        self._show_page("compare")
        self._reset_compare_panels()
        self.progress["value"] = 0
        self._log(f"Compare {m['display_name']}...")
        min_g = float(self.train_min_green.get())
        min_base = float(self.train_min_green_base.get())
        min_cars_switch = int(self.train_min_cars_switch.get())
        max_g = float(self.train_max_green.get())
        max_g_opt = max_g if max_g > 0 else None
        self.current_job_id = self.runner.start_compare(
            m["sumocfg"],
            baseline,
            seed=seed,
            gui=bool(self.compare_show_sumo.get()),
            gui_delay=int(self.compare_delay.get()),
            policy_path=m["policy_path"],
            min_green_seconds=min_g,
            min_green_base_seconds=min_base,
            switch_min_vehicles=min_cars_switch,
            switch_min_wait_seconds=25.0,
            max_green_seconds=max_g_opt,
            map_id=m["id"],
            map_name=m["display_name"],
            inject_seconds=inject_sec,
        )

    def _update_train_progress_from_curriculum(self, job):
        r = job.result or {}
        last_train = r.get("last_train") or {}
        if last_train:
            fake = type("J", (), {"result": last_train, "progress": job.progress})()
            self._update_train_progress(fake)
        cycles = r.get("cycles") or []
        if cycles:
            last = cycles[-1]
            self.train_episode_var.set(
                f"Auto cycle {last.get('cycle', '?')}/{self.curriculum_cycles_var.get()} — {last.get('summary', '')}"
            )
        self.curriculum_status_var.set("\n".join(curriculum_status_lines(5)))

    def _finish_curriculum(self, job):
        self.curriculum_status_var.set("\n".join(curriculum_status_lines(8)))
        self._log(job.message or "Auto curriculum finished.")
        r = job.result or {}
        last_compare = r.get("last_compare")
        if last_compare:
            self._show_page("compare")
            self._finalize_compare(last_compare)
        last_train = r.get("last_train")
        if last_train:
            self._update_train_progress(type("J", (), {"result": last_train})())
        self._refresh_training_dashboard()
        self._refresh_reports()
        if job.status == "failed" and job.error:
            messagebox.showerror("Auto curriculum", job.error)

    def _update_train_progress(self, job):
        r = job.result or {}
        done = r.get("episodes_done", 0)
        total = r.get("episodes_total", r.get("episodes_planned", 1))
        self.train_progress["value"] = job.progress * 100
        self.train_episode_var.set(f"Episode {done} / {total}")
        reward_line = f"Last reward: {r.get('last_reward', 0):.1f}   ·   ε = {r.get('epsilon', 0):.3f}"
        saved_ep = r.get("last_saved_episode")
        if saved_ep:
            reward_line += f"   ·   saved ep {saved_ep}"
        self.train_reward_var.set(reward_line)
        wait_last10 = r.get("avg_wait_last_10")
        wait_run = r.get("avg_wait_running")
        if wait_last10 is not None:
            self.train_wait_var.set(
                f"Avg wait (last 10 ep): {wait_last10:.0f}   ·   running avg: {wait_run:.0f}  (lower is better)"
            )
        parts = r.get("last_reward_components") or {}
        if parts:
            bits = ", ".join(f"{k}={v:.0f}" for k, v in sorted(parts.items()))
            self.train_reward_parts_var.set(f"Last ep. reward parts: {bits}")
        log_p = r.get("training_log_path")
        if log_p:
            try:
                rel_log = Path(log_p).relative_to(PROJECT_DIR)
            except ValueError:
                rel_log = Path(log_p)
            self.train_objectives_var.set(
                f"Log: {rel_log}  ·  objectives: dqn_policy_objectives.txt (next to .pth)"
            )
        hist = r.get("rewards_history") or []
        wait_hist = r.get("avg_wait_history") or []
        if hist and self._train_ax:
            self._train_ax.clear()
            self._train_ax.set_facecolor(C["chart_surface"])
            self._train_ax.plot(range(1, len(hist) + 1), hist, color=C["accent"], linewidth=2, label="Reward")
            if wait_hist:
                ax2 = self._train_ax.twinx()
                ax2.plot(
                    range(1, len(wait_hist) + 1),
                    wait_hist,
                    color=C["yellow"],
                    linewidth=1.5,
                    alpha=0.85,
                    label="Total wait",
                )
                ax2.set_ylabel("Total wait", color=C["yellow"], fontsize=9)
                ax2.tick_params(axis="y", colors=C["yellow"], labelsize=8)
            self._style_ax(self._train_ax, "Episode", "Reward")
            self._train_canvas_mpl.draw()

    def _draw_emergency_timeline_compare(self, result: dict) -> None:
        timelines = result.get("emergency_timelines") or {}
        specs = (
            ("baseline", self._cmp_emergency_axes[0], C["red"], "Fixed-Time baseline"),
            ("dqn", self._cmp_emergency_axes[1], C["green"], "DQN"),
        )
        for key, ax, color, title in specs:
            ax.clear()
            ax.set_facecolor(C["chart_surface"])
            series = timelines.get(key) or {}
            t_vals = series.get("t") or []
            w_vals = series.get("w") or []
            if t_vals and w_vals:
                ax.plot(t_vals, w_vals, color=color, linewidth=1.8)
            else:
                ax.text(0.5, 0.5, "No emergency vehicles", ha="center", va="center", color=C["muted"], transform=ax.transAxes)
            ax.set_title(title, color=C["text"], fontsize=9)
            self._style_ax(ax, "Sim time (s)", "Emergency wait")
        if self._cmp_emergency_canvas:
            self._cmp_emergency_canvas.draw()

    def _draw_transit_timeline_compare(self, result: dict) -> None:
        timelines = result.get("transit_timelines") or {}
        specs = (
            ("baseline", self._cmp_transit_axes[0], C["red"], "Fixed-Time baseline"),
            ("dqn", self._cmp_transit_axes[1], C["success"], "DQN"),
        )
        for key, ax, color, title in specs:
            ax.clear()
            ax.set_facecolor(C["chart_surface"])
            series = timelines.get(key) or {}
            t_vals = series.get("t") or []
            w_vals = series.get("w") or []
            if t_vals and w_vals:
                ax.plot(t_vals, w_vals, color=color, linewidth=1.8)
            else:
                ax.text(0.5, 0.5, "No buses in sim", ha="center", va="center", color=C["muted"], transform=ax.transAxes)
            ax.set_title(title, color=C["text"], fontsize=9)
            self._style_ax(ax, "Sim time (s)", "Bus wait")
        if self._cmp_transit_canvas:
            self._cmp_transit_canvas.draw()

    def _update_compare_phase(self, r: dict):
        labels = {
            "waiting": "Waiting...",
            "running": "Running now...",
            "done": "Complete",
            "failed": "Skipped / failed",
        }
        for key in ("baseline", "dqn"):
            st = r.get(f"{key}_status", "waiting")
            getattr(self, f"compare_{key}_status_var").set(labels.get(st, st))
        err = r.get("model_error") or ""
        if err and r.get("baseline_status") == "done" and r.get("dqn_status") != "running":
            self.compare_imp_var.set(err)
        if r.get("baseline_status") == "done" and r.get("dqn_status") == "done":
            self._refresh_compare_panel_labels(r)
            self._draw_compare_summary_charts(r)

    def _finalize_compare(self, result: dict):
        self._update_compare_phase(result)
        self._refresh_compare_panel_labels(result)
        self._draw_compare_summary_charts(result)
        self._draw_emergency_timeline_compare(result)
        self._draw_transit_timeline_compare(result)
        fixed = int(result.get("fixed_wait", 0) or result.get("baseline_wait", 0))
        dqn = int(result.get("dqn_wait") or 0)
        fixed_all = int(result.get("fixed_wait_all", 0) or result.get("baseline_wait_all", 0))
        dqn_all = int(result.get("dqn_wait_all", 0))
        saved_at = result.get("report_saved_at")
        emg_chart = result.get("emergency_timeline_chart") or result.get("emergency_chart")
        for chart_key, label in (
            ("emergency_timeline_chart", "Emergency"),
            ("transit_timeline_chart", "Transit"),
        ):
            chart_path = result.get(chart_key) or result.get(chart_key.replace("_timeline", ""))
            if chart_path:
                try:
                    rel = Path(chart_path).relative_to(PROJECT_DIR)
                    self._log(f"{label} charts: {rel}")
                except ValueError:
                    self._log(f"{label} charts: {chart_path}")
        if result.get("report_save_error"):
            self._log(f"Could not save report: {result['report_save_error']}")
        elif saved_at:
            self._log(f"Comparison saved to reports ({saved_at}).")
        self._refresh_reports()
        if dqn_all > 0 and fixed_all > 0:
            imp_all = result.get("improvement_percent_all", 0)
            tr_imp = result.get("transit_improvement_percent")
            emg_imp = result.get("emergency_improvement_percent")
            suffix = f" Saved to Reports ({saved_at})." if saved_at else ""
            parts = [f"All vehicles: {imp_all:+.1f}%"]
            if isinstance(tr_imp, (int, float)) and result.get("baseline_transit_wait", 0) > 0:
                parts.append(f"bus {tr_imp:+.1f}%")
            if isinstance(emg_imp, (int, float)) and result.get("baseline_emergency_wait", 0) > 0:
                parts.append(f"emergency {emg_imp:+.1f}%")
            summary = " · ".join(parts) + f" (DQN vs baseline).{suffix}"
            if imp_all >= 0 and (not isinstance(emg_imp, (int, float)) or emg_imp >= 0):
                self.compare_imp_var.set(f"DQN wins on average wait.{summary}")
            else:
                self.compare_imp_var.set(f"Mixed results — check green/red per chart.{summary}")
        else:
            self.compare_imp_var.set(result.get("model_error", "DQN result not available."))

    def _poll_job(self):
        if self.current_job_id:
            job = self.runner.get_job(self.current_job_id)
            if job:
                self.progress["value"] = job.progress * 100
                self.status_var.set(job.message or job.status)
                if job.kind == "train" and job.status == "running":
                    self._update_train_progress(job)
                if job.kind == "curriculum" and job.status == "running":
                    self._update_train_progress_from_curriculum(job)
                if job.kind == "compare" and job.result:
                    self._update_compare_phase(job.result)
                if job.status in ("completed", "failed"):
                    if job.kind in ("train", "curriculum"):
                        self._set_train_job_controls(False)
                    if job.status == "completed":
                        if job.kind != "train":
                            self._log(job.message)
                        if job.kind == "train":
                            self._update_train_progress(job)
                            if job.result and job.result.get("cancelled"):
                                self.train_episode_var.set("Training stopped — press Start to run again")
                                self._log("Training stopped. Checkpoint saved — you can start again.")
                            else:
                                self.train_episode_var.set("Training complete — press Start to run again")
                                self._log(job.message or "Training complete.")
                            self._refresh_training_dashboard()
                        elif job.kind == "curriculum":
                            self._finish_curriculum(job)
                        elif job.kind == "compare" and job.result:
                            self._finalize_compare(job.result)
                            err = job.result.get("model_error")
                            if err and not job.result.get("dqn_wait"):
                                if "Train" in err and messagebox.askyesno("DQN missing", f"{err}\n\nTrain now?"):
                                    self._on_train()
                                else:
                                    messagebox.showwarning("DQN", err)
                    else:
                        if job.kind in ("train", "curriculum"):
                            self.train_episode_var.set("Training failed — fix the error, then press Start")
                        self._log(f"ERROR: {job.error}")
                        messagebox.showerror("Failed", job.error or "Unknown")
                    self.current_job_id = None
        self.root.after(300, self._poll_job)

    def run(self):
        self.root.mainloop()


def main():
    os.chdir(PROJECT_DIR)
    FlowGridApp().run()


if __name__ == "__main__":
    main()
