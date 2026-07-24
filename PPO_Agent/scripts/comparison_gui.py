"""
Comparison GUI -- interactive PPO model comparison tool (V8-family only).

Lets you pick which trained checkpoints to compare, pick random or manually-
entered seeds, pick a traffic scenario (or all three), and see a results
table with total wait time per seed plus an Average column that decides the
winner -- an interactive complement to this project's batch CLI tools
(checkpoint_sweep.py, verify_candidates.py, final_results_random_seeds.py).

HARD CONSTRAINT: evaluate_models.py resolves its environment class via
`from sumo_rl_env import ...`, a process-wide import cached the first time it
happens, resolved via whichever version folder is first on sys.path. This
GUI hardcodes that resolution to V8's shim (see below). Every model you add
here MUST be a V8-family checkpoint (V8 itself, V8_replicate, or another
V8-derived version, all sharing V8's 21-dim observation/action space). Do
NOT add V4/V6/V7 checkpoints -- they use a different (13-dim) observation
space and this process only ever loads one environment definition.

UI built with customtkinter (light, rounded, modern widget set). Seed-mode
and scenario selection use CTkSegmentedButton -- a row of clickable toggle
buttons, web-style -- instead of classic radio buttons. The results table
still uses ttk.Treeview, themed to match, since customtkinter has no
built-in table/grid widget.

Usage:
    cd PPO_Agent/scripts
    python comparison_gui.py
"""
import os
import sys
import random
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog
import customtkinter as ctk
from PIL import Image

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from comparison_core import (
    REGISTRY_PATH, DEFAULT_MODEL_NAME, DEFAULT_MODEL_PATH, AVAILABLE_BASELINES,
    EST_MIN_PER_EPISODE,
    load_registry, save_registry, add_model_entry,
    compute_estimate, build_tasks, run_comparison, describe_task,
)

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# FlowGrid palette -- same colors/values as comparison_web/static/style.css,
# so the Tkinter and web UIs look like the same product.
LOGO_PATH     = os.path.join(_HERE, "comparison_web", "static", "logo.png")
ACCENT        = "#16213e"   # navy -- primary buttons, headings, checkboxes
ACCENT_HOVER  = "#1f2d4d"
ACCENT_SOFT   = "#e8f9ef"   # winner-row highlight (soft green -- matches the logo's "go" signal)
TEXT_MAIN     = "#16213e"
TEXT_MUTED    = "#6b7280"
BG_PAGE       = "#f5f6fa"
BG_CARD       = "#ffffff"
BG_CHIP       = "#e9eaee"
REMOVE_HOVER  = "#fdecea"
REMOVE_TEXT   = "#e74c3c"
WINNER_GREEN  = "#2ecc71"   # strong green for the bar chart's winner bar (vs. the soft treeview highlight)


# ---------------------------------------------------------------------------
# GUI (customtkinter widgets; ttk.Treeview only for the results table, since
# customtkinter has no built-in table widget -- themed to match)
# ---------------------------------------------------------------------------

def _style_treeview_light():
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview",
                     background=BG_CARD, fieldbackground=BG_CARD,
                     foreground=TEXT_MAIN, rowheight=30, borderwidth=0, font=("Segoe UI", 12))
    style.configure("Treeview.Heading",
                     background=BG_CHIP, foreground=TEXT_MAIN, relief="flat",
                     font=("Segoe UI", 12, "bold"))
    style.map("Treeview.Heading", background=[("active", BG_CHIP)])
    style.map("Treeview", background=[("selected", ACCENT_SOFT)])


class ComparisonApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FlowGrid -- Model Comparison")
        self.root.geometry("1000x800")
        self.root.configure(fg_color=BG_PAGE)

        _style_treeview_light()

        # Whole app lives inside one scrollable frame so the window can hold
        # more sections (Models, Baselines, Run Config, Results) than fit on
        # screen at once -- mirrors the web version's scrolling page.
        self.scroll_root = ctk.CTkScrollableFrame(self.root, fg_color=BG_PAGE)
        self.scroll_root.pack(fill="both", expand=True)

        self.registry = load_registry()
        self.model_vars = {}          # path -> tk.BooleanVar
        self.baseline_vars = {}       # baseline name -> tk.BooleanVar
        self.manual_seeds = []        # list[int]
        self.seed_mode = tk.StringVar(value="Random")
        self.seed_count_var = tk.IntVar(value=5)
        self.seed_entry_var = tk.StringVar()
        self.scenario_var = tk.StringVar(value="Low")
        self.watch_live_var = tk.BooleanVar(value=False)
        self.estimate_var = tk.StringVar()
        self.progress_var = tk.StringVar()
        self.current_task_var = tk.StringVar()
        self.result_queue = queue.Queue()
        self._task_labels = []
        self._watch_live_active = False
        self._chart_canvases = []     # keeps matplotlib FigureCanvasTkAgg refs alive

        self._build_header()
        self._build_models_frame()
        self._build_baselines_frame()
        self._build_run_config_frame()
        self._build_estimate_start_frame()
        self._build_results_frame()

        self._update_estimate()

    # ---------- header ----------
    def _build_header(self):
        frame = ctk.CTkFrame(self.scroll_root, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=(12, 8))
        # Keep a reference on self -- CTkImage/PhotoImage get garbage
        # collected (and the label goes blank) if nothing else holds them.
        self.logo_image = ctk.CTkImage(light_image=Image.open(LOGO_PATH), size=(162, 64))
        ctk.CTkLabel(frame, image=self.logo_image, text="").pack(anchor="w")

    # ---------- models ----------
    def _build_models_frame(self):
        self.models_scroll = ctk.CTkScrollableFrame(
            self.scroll_root, label_text="Models to Compare", height=160)
        self.models_scroll.pack(fill="x", padx=12, pady=6)

        ctk.CTkButton(self.scroll_root, text="+ Add Model...", width=180, height=44,
                      font=("Segoe UI", 13), fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      command=self._on_add_model_clicked
                      ).pack(anchor="w", padx=12)

        self._rebuild_model_checklist()

    def _rebuild_model_checklist(self):
        for w in self.models_scroll.winfo_children():
            w.destroy()
        self.model_vars = {}
        for entry in self.registry:
            path = entry["path"]
            var = tk.BooleanVar(value=(entry["name"] == DEFAULT_MODEL_NAME))
            self.model_vars[path] = var
            row = ctk.CTkFrame(self.models_scroll, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkCheckBox(row, text=entry["name"], variable=var,
                             onvalue=True, offvalue=False, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                             command=self._update_estimate).pack(side="left")
            ctk.CTkLabel(row, text=path, text_color=TEXT_MUTED,
                         font=("Segoe UI", 10)).pack(side="left", padx=8)
            ctk.CTkButton(row, text="x", width=38, height=38, font=("Segoe UI", 14, "bold"),
                          fg_color="transparent", hover_color=REMOVE_HOVER, text_color=REMOVE_TEXT,
                          command=lambda p=path: self._on_remove_model_clicked(p)
                          ).pack(side="right")

    def _on_add_model_clicked(self):
        path = filedialog.askopenfilename(
            title="Select PPO model .zip",
            initialdir=os.path.join(_HERE, "..", "models"),
            filetypes=[("Model zip", "*.zip")])
        if not path:
            return
        self.registry = add_model_entry(self.registry, path)
        self._rebuild_model_checklist()
        self._update_estimate()

    def _on_remove_model_clicked(self, path):
        self.registry = [e for e in self.registry if e["path"] != path]
        save_registry(self.registry)
        self._rebuild_model_checklist()
        self._update_estimate()

    # ---------- baselines ----------
    def _build_baselines_frame(self):
        scroll = ctk.CTkScrollableFrame(
            self.scroll_root, label_text="Baselines to Include", height=100)
        scroll.pack(fill="x", padx=12, pady=6)
        for baseline in AVAILABLE_BASELINES:
            name = baseline["name"]
            var = tk.BooleanVar(value=False)
            self.baseline_vars[name] = var
            ctk.CTkCheckBox(scroll, text=name, variable=var,
                            onvalue=True, offvalue=False, fg_color=ACCENT, hover_color=ACCENT_HOVER,
                            command=self._update_estimate).pack(anchor="w", pady=3)

    # ---------- run configuration ----------
    def _build_run_config_frame(self):
        outer = ctk.CTkFrame(self.scroll_root)
        outer.pack(fill="x", padx=12, pady=6)

        seeds_frame = ctk.CTkFrame(outer, fg_color="transparent")
        seeds_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)
        ctk.CTkLabel(seeds_frame, text="Seeds", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ctk.CTkSegmentedButton(seeds_frame, values=["Random", "Manual"],
                               variable=self.seed_mode, height=44, font=("Segoe UI", 13),
                               selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                               command=lambda v: self._on_seed_mode_changed()
                               ).pack(anchor="w", pady=6)

        self.random_subframe = ctk.CTkFrame(seeds_frame, fg_color="transparent")
        ctk.CTkLabel(self.random_subframe, text="Count:", font=("Segoe UI", 12)).pack(side="left")
        count_entry = ctk.CTkEntry(self.random_subframe, textvariable=self.seed_count_var,
                                    width=80, height=42, font=("Segoe UI", 13))
        count_entry.pack(side="left", padx=6)
        self.seed_count_var.trace_add("write", lambda *a: self._update_estimate())

        self.manual_subframe = ctk.CTkFrame(seeds_frame, fg_color="transparent")
        entry_row = ctk.CTkFrame(self.manual_subframe, fg_color="transparent")
        entry_row.pack(fill="x")
        ctk.CTkEntry(entry_row, textvariable=self.seed_entry_var, width=120, height=42,
                     font=("Segoe UI", 13), placeholder_text="e.g. 42").pack(side="left")
        ctk.CTkButton(entry_row, text="Add", width=80, height=42, font=("Segoe UI", 13),
                      fg_color=ACCENT, hover_color=ACCENT_HOVER,
                      command=self._on_add_seed_clicked).pack(side="left", padx=6)
        self.seed_chips_frame = ctk.CTkFrame(self.manual_subframe, fg_color="transparent")
        self.seed_chips_frame.pack(fill="x", pady=6)

        self._on_seed_mode_changed()  # show the right sub-frame initially

        scen_frame = ctk.CTkFrame(outer, fg_color="transparent")
        scen_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)
        ctk.CTkLabel(scen_frame, text="Scenario", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ctk.CTkSegmentedButton(scen_frame, values=["Low", "Medium", "High", "All"],
                               variable=self.scenario_var, height=44, font=("Segoe UI", 13),
                               selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                               command=lambda v: self._update_estimate()
                               ).pack(anchor="w", pady=6)

    def _on_seed_mode_changed(self):
        if self.seed_mode.get() == "Random":
            self.manual_subframe.pack_forget()
            self.random_subframe.pack(anchor="w", pady=4)
        else:
            self.random_subframe.pack_forget()
            self.manual_subframe.pack(anchor="w", pady=4)
        self._update_estimate()

    def _on_add_seed_clicked(self):
        raw = self.seed_entry_var.get().strip()
        try:
            seed = int(raw)
        except ValueError:
            return
        self.manual_seeds.append(seed)
        self.seed_entry_var.set("")
        self._rebuild_seed_chips()
        self._update_estimate()

    def _rebuild_seed_chips(self):
        for w in self.seed_chips_frame.winfo_children():
            w.destroy()
        row = ctk.CTkFrame(self.seed_chips_frame, fg_color="transparent")
        row.pack(anchor="w")
        for seed in self.manual_seeds:
            chip = ctk.CTkFrame(row, fg_color=BG_CHIP, corner_radius=16)
            chip.pack(side="left", padx=4)
            ctk.CTkLabel(chip, text=str(seed), text_color=TEXT_MAIN,
                         font=("Segoe UI", 13)).pack(side="left", padx=(14, 4), pady=7)
            ctk.CTkButton(chip, text="x", width=30, height=30, corner_radius=15,
                          font=("Segoe UI", 13, "bold"),
                          fg_color="transparent", hover_color=REMOVE_HOVER, text_color=REMOVE_TEXT,
                          command=lambda s=seed: self._on_remove_seed_chip(s)
                          ).pack(side="left", padx=(0, 8), pady=7)

    def _on_remove_seed_chip(self, seed):
        if seed in self.manual_seeds:
            self.manual_seeds.remove(seed)
        self._rebuild_seed_chips()
        self._update_estimate()

    # ---------- estimate + start ----------
    def _build_estimate_start_frame(self):
        frame = ctk.CTkFrame(self.scroll_root, fg_color="transparent")
        frame.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(frame, textvariable=self.estimate_var,
                     font=("Segoe UI", 12)).pack(anchor="w")
        ctk.CTkCheckBox(frame, text="Watch Live (opens a real SUMO window)",
                        variable=self.watch_live_var, onvalue=True, offvalue=False,
                        fg_color=ACCENT, hover_color=ACCENT_HOVER,
                        command=self._update_estimate).pack(anchor="w", pady=(10, 0))
        ctk.CTkLabel(frame, text=("Requires exactly 1 seed and one specific scenario "
                                  "(not \"All\"). Any number of models/baselines run one "
                                  "at a time, one visible window at a time."),
                     text_color=TEXT_MUTED, font=("Segoe UI", 10),
                     justify="left", wraplength=920).pack(anchor="w")
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", pady=8)
        self.start_button = ctk.CTkButton(row, text="Start Comparison", width=260, height=56,
                                           font=("Segoe UI", 15, "bold"),
                                           fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                           command=self.on_start)
        self.start_button.pack(side="left")
        self.progress_bar = ctk.CTkProgressBar(row, width=320, height=20, progress_color=ACCENT)
        self.progress_bar.set(0)
        self.progress_label = ctk.CTkLabel(row, textvariable=self.progress_var,
                                            font=("Segoe UI", 12))
        ctk.CTkLabel(frame, textvariable=self.current_task_var, text_color=ACCENT,
                     font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(4, 0))

    def _safe_seed_count(self):
        try:
            return max(0, self.seed_count_var.get())
        except (tk.TclError, ValueError):
            return 0

    def _current_selection(self):
        models = [e for e in self.registry
                  if e["path"] in self.model_vars and self.model_vars[e["path"]].get()]
        baselines = [b for b in AVAILABLE_BASELINES
                     if self.baseline_vars.get(b["name"]) and self.baseline_vars[b["name"]].get()]
        if self.seed_mode.get() == "Random":
            seeds = None  # drawn fresh at start time
            n_seeds = self._safe_seed_count()
        else:
            seeds = list(self.manual_seeds)
            n_seeds = len(seeds)
        scen = self.scenario_var.get()
        scenario_names = ["Low", "Medium", "High"] if scen == "All" else [scen]
        return models, baselines, seeds, n_seeds, scenario_names

    def _update_estimate(self):
        models, baselines, seeds, n_seeds, scenario_names = self._current_selection()
        n_controllers = len(models) + len(baselines)
        n_episodes, eta_min, workers = compute_estimate(n_controllers, n_seeds, len(scenario_names))
        if self.watch_live_var.get() and n_episodes > 0:
            workers = 1
            eta_min = n_episodes * EST_MIN_PER_EPISODE
        self.estimate_var.set(
            f"{n_episodes} episodes  ({n_controllers} models/baselines x {n_seeds} seeds x "
            f"{len(scenario_names)} scenarios)  ~{eta_min:.1f} min est. ({workers} workers)")

    # ---------- run lifecycle ----------
    def on_start(self):
        models, baselines, seeds, n_seeds, scenario_names = self._current_selection()
        if not models and not baselines:
            self.progress_var.set("Select at least one model or baseline.")
            return
        if n_seeds == 0:
            self.progress_var.set("Add at least one seed.")
            return
        watch_live = self.watch_live_var.get()
        if watch_live and (n_seeds != 1 or len(scenario_names) != 1):
            self.progress_var.set(
                "Watch Live requires exactly 1 seed and 1 specific scenario (not \"All\").")
            return
        if seeds is None:
            seeds = random.sample(range(1, 1_000_000), n_seeds)

        tasks, task_meta = build_tasks(models, seeds, scenario_names,
                                        baselines=baselines, use_gui=watch_live)

        self.start_button.configure(state="disabled")
        self.progress_bar.pack(side="left", padx=8)
        self.progress_label.pack(side="left")
        self.progress_bar.set(0)
        self._current_total = len(tasks)
        self._task_labels = [t[0] for t in tasks]
        self._watch_live_active = watch_live
        self.progress_var.set(f"0/{len(tasks)} episodes done")
        if watch_live and self._task_labels:
            self.current_task_var.set(f"Now running: {describe_task(self._task_labels[0])}")
        else:
            self.current_task_var.set("")

        max_workers = 1 if watch_live else None
        thread = threading.Thread(target=run_comparison,
                                   args=(tasks, task_meta, self.result_queue, max_workers),
                                   daemon=True)
        thread.start()
        self.root.after(150, self._poll_queue)

    def _poll_queue(self):
        while True:
            try:
                msg = self.result_queue.get_nowait()
            except queue.Empty:
                break
            if msg["type"] == "progress":
                total = max(msg["total"], 1)
                self.progress_bar.set(msg["done"] / total)
                self.progress_var.set(f"{msg['done']}/{msg['total']} episodes done")
                # With max_workers=1 (Watch Live), tasks complete in strict
                # submission order -- task_labels[done] is exactly the one
                # actually running right now (see describe_task's docstring).
                if self._watch_live_active and msg["done"] < len(self._task_labels):
                    self.current_task_var.set(
                        f"Now running: {describe_task(self._task_labels[msg['done']])}")
                else:
                    self.current_task_var.set("")
            elif msg["type"] == "episode_error":
                self.progress_var.set(f"warning: {msg['label']} failed: {msg['error']}")
            elif msg["type"] == "done":
                self._on_run_done(msg["results_by_scenario"])
                return
            elif msg["type"] == "fatal_error":
                self._on_run_error(msg["error"])
                return
        self.root.after(150, self._poll_queue)

    def _on_run_error(self, message):
        self.start_button.configure(state="normal")
        self.progress_var.set(f"ERROR: {message}")
        self.current_task_var.set("")

    def _on_run_done(self, results_by_scenario):
        self.start_button.configure(state="normal")
        self.progress_var.set("Done.")
        self.current_task_var.set("")
        self._render_results(results_by_scenario)

    # ---------- results ----------
    def _build_results_frame(self):
        # A visibly bordered "box" so it's obvious this is where results will
        # show up, even before a comparison has been run.
        self.results_box = ctk.CTkFrame(self.scroll_root, fg_color=BG_CARD,
                                         border_width=2, border_color=BG_CHIP,
                                         corner_radius=10)
        self.results_box.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        ctk.CTkLabel(self.results_box, text="Results", font=("Segoe UI", 15, "bold"),
                     text_color=TEXT_MAIN).pack(anchor="w", padx=16, pady=(12, 0))

        self.results_content = ctk.CTkFrame(self.results_box, fg_color="transparent")
        self.results_content.pack(fill="both", expand=True, padx=12, pady=12)

        self.results_placeholder = ctk.CTkLabel(
            self.results_content, text="Run a comparison to see results here.",
            text_color=TEXT_MUTED, font=("Segoe UI", 12))
        self.results_placeholder.pack(pady=30)

    def _render_results(self, results_by_scenario):
        for w in self.results_content.winfo_children():
            w.destroy()
        self._chart_canvases = []  # drop old refs so previous run's figures can be GC'd
        tabview = ctk.CTkTabview(self.results_content)
        tabview.pack(fill="both", expand=True)
        for scen, df in results_by_scenario.items():
            tab = tabview.add(scen)
            seed_cols = [c for c in df.columns if c != "Average"]
            columns = ["Model"] + [f"Seed {c}" for c in seed_cols] + ["Average"]
            tree = ttk.Treeview(tab, columns=columns, show="headings")
            for c in columns:
                tree.heading(c, text=c)
                tree.column(c, width=110, anchor="center")
            tree.tag_configure("winner", background=ACCENT_SOFT, foreground=TEXT_MAIN)
            df_sorted = df.sort_values("Average")
            winner_name = df["Average"].idxmin()
            for model_name, row in df_sorted.iterrows():
                values = [model_name] + [f"{row[c]:,.0f}" for c in seed_cols] + \
                         [f"{row['Average']:,.0f}"]
                item_id = tree.insert("", "end", values=values)
                if model_name == winner_name:
                    tree.item(item_id, tags=("winner",))
            tree.pack(fill="both", expand=True, padx=4, pady=4)

            self._add_bar_chart(tab, df_sorted, winner_name)

    def _add_bar_chart(self, tab, df_sorted, winner_name):
        names = df_sorted.index.tolist()
        values = df_sorted["Average"].tolist()
        colors = [WINNER_GREEN if n == winner_name else ACCENT for n in names]

        fig = Figure(figsize=(6, max(1.6, 0.45 * len(names))), dpi=100)
        ax = fig.add_subplot(111)
        ax.barh(names, values, color=colors)
        ax.invert_yaxis()  # df_sorted is ascending (best first) -> best bar on top
        ax.set_xlabel("Average wait time (seconds)", fontsize=9)
        ax.tick_params(labelsize=9)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=4, pady=(8, 4))
        self._chart_canvases.append(canvas)  # keep a reference so it isn't garbage-collected


def main():
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = ComparisonApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
