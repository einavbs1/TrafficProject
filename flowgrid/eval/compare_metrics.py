"""Metrics and charts for baseline vs DQN compare runs."""
from __future__ import annotations

from dataclasses import dataclass, field

import matplotlib.pyplot as plt


@dataclass
class CompareEpisodeMetrics:
    total_wait: float = 0.0
    all_vehicles_seen: int = 0
    emergency_wait_sum: float = 0.0
    emergency_max_step_wait: float = 0.0
    emergency_vehicles_seen: int = 0
    emergency_preempt_steps: int = 0
    transit_wait_sum: float = 0.0
    transit_max_step_wait: float = 0.0
    transit_vehicles_seen: int = 0
    scheduled_cars: int = 0
    scheduled_transit: int = 0
    scheduled_emergency: int = 0
    steps_run: int = 0
    ended_reason: str = ""
    timeline_sim_t: list[float] = field(default_factory=list)
    timeline_emergency_wait: list[float] = field(default_factory=list)
    timeline_transit_wait: list[float] = field(default_factory=list)

    @property
    def priority_wait_sum(self) -> float:
        """Bus/transit + emergency only (excludes private cars)."""
        return float(self.transit_wait_sum) + float(self.emergency_wait_sum)


def save_emergency_comparison_charts(
    baseline: CompareEpisodeMetrics,
    dqn: CompareEpisodeMetrics,
    output_dir: str,
    *,
    title_suffix: str = "",
) -> dict[str, str]:
    """Write bar + timeline PNGs; returns paths keyed by chart name."""
    import os

    os.makedirs(output_dir or ".", exist_ok=True)
    bar_path = os.path.join(output_dir, "comparison_emergency_bars.png")
    timeline_path = os.path.join(output_dir, "comparison_emergency_timeline.png")

    _plot_emergency_bars(baseline, dqn, bar_path, title_suffix=title_suffix)
    _plot_emergency_timeline(baseline, dqn, timeline_path, title_suffix=title_suffix)

    return {"emergency_bars": bar_path, "emergency_timeline": timeline_path}


def save_compare_summary_charts(
    baseline: CompareEpisodeMetrics,
    dqn: CompareEpisodeMetrics,
    output_dir: str,
    *,
    title_suffix: str = "",
) -> str:
    """Three bar charts: all vehicles, bus, emergency — green = lower wait."""
    import os

    path = os.path.join(output_dir or ".", "comparison_summary.png")
    fig, axes = plt.subplots(3, 1, figsize=(8, 10), facecolor="#0d1117")
    fig.subplots_adjust(hspace=0.5, top=0.95, bottom=0.08, left=0.14, right=0.96)
    series = [
        ("All vehicles", baseline.total_wait, dqn.total_wait),
        ("Bus / public transport", baseline.transit_wait_sum, dqn.transit_wait_sum),
        ("Emergency", baseline.emergency_wait_sum, dqn.emergency_wait_sum),
    ]
    for ax, (title, b_val, d_val) in zip(axes, series):
        labels = ["Baseline", "DQN"]
        values = [b_val, d_val]
        b_better = b_val <= d_val
        colors = ["#3fb950", "#f85149"] if b_better else ["#f85149", "#3fb950"]
        ax.bar(labels, values, color=colors, width=0.5)
        ax.set_title(title, color="#e6edf3", fontsize=10)
        ymax = max(values) if max(values) > 0 else 1
        for i, v in enumerate(values):
            ax.text(i, v + ymax * 0.03, str(int(v)), ha="center", fontweight="bold", color="white")
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e")
        ax.set_ylabel("Wait sum", color="#8b949e")
        for spine in ax.spines.values():
            spine.set_color("#30363d")
    if title_suffix:
        fig.suptitle(f"Compare summary ({title_suffix})", color="white", fontsize=11)
    fig.savefig(path, facecolor="#0d1117", dpi=120)
    plt.close(fig)
    return path


def save_transit_comparison_charts(
    baseline: CompareEpisodeMetrics,
    dqn: CompareEpisodeMetrics,
    output_dir: str,
    *,
    title_suffix: str = "",
) -> dict[str, str]:
    """Write public-transit (bus) bar + timeline PNGs."""
    import os

    os.makedirs(output_dir or ".", exist_ok=True)
    bar_path = os.path.join(output_dir, "comparison_transit_bars.png")
    timeline_path = os.path.join(output_dir, "comparison_transit_timeline.png")

    _plot_transit_bars(baseline, dqn, bar_path, title_suffix=title_suffix)
    _plot_transit_timeline(baseline, dqn, timeline_path, title_suffix=title_suffix)

    return {"transit_bars": bar_path, "transit_timeline": timeline_path}


def _style_compare_axes(axes, suptitle: str) -> None:
    fig = axes[0].figure
    fig.suptitle(suptitle, color="white", fontsize=11)
    for ax in axes:
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e")
        ax.yaxis.label.set_color("#8b949e")
        ax.title.set_color("#e6edf3")
        for spine in ax.spines.values():
            spine.set_color("#30363d")


def _plot_emergency_bars(
    baseline: CompareEpisodeMetrics,
    dqn: CompareEpisodeMetrics,
    path: str,
    *,
    title_suffix: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor="#0d1117")

    labels = ["Fixed-Time", "DQN"]
    x = range(len(labels))
    width = 0.35

    ax0 = axes[0]
    totals = [baseline.emergency_wait_sum, dqn.emergency_wait_sum]
    colors = ["#f85149", "#3fb950" if dqn.total_wait > 0 else "#484f58"]
    ax0.bar(labels, totals, color=colors, width=0.55)
    ax0.set_ylabel("Sum of emergency wait per step")
    ax0.set_title("Emergency wait (lower is better)")
    ymax = max(totals) if max(totals) > 0 else 1
    for i, v in enumerate(totals):
        ax0.text(i, v + ymax * 0.03, f"{int(v)}", ha="center", fontweight="bold", color="white")

    ax1 = axes[1]
    m1 = [baseline.emergency_max_step_wait, dqn.emergency_max_step_wait]
    m2 = [baseline.emergency_preempt_steps, dqn.emergency_preempt_steps]
    ax1.bar([i - width / 2 for i in x], m1, width=width, label="Max wait (1 step)", color="#d29922")
    ax1.bar([i + width / 2 for i in x], m2, width=width, label="Preempt steps", color="#58a6ff")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels)
    ax1.set_title("Peak & preemption")
    ax1.legend(loc="upper right", fontsize=8, facecolor="#161b22", edgecolor="#30363d")

    title = "Emergency vehicles — baseline vs DQN"
    if title_suffix:
        title = f"{title} ({title_suffix})"
    _style_compare_axes(axes, title)
    fig.tight_layout()
    fig.savefig(path, facecolor="#0d1117", dpi=120)
    plt.close(fig)


def _plot_transit_bars(
    baseline: CompareEpisodeMetrics,
    dqn: CompareEpisodeMetrics,
    path: str,
    *,
    title_suffix: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor="#0d1117")

    labels = ["Fixed-Time", "DQN"]
    x = range(len(labels))
    width = 0.35

    ax0 = axes[0]
    totals = [baseline.transit_wait_sum, dqn.transit_wait_sum]
    colors = ["#f85149", "#3fb950" if dqn.total_wait > 0 else "#484f58"]
    ax0.bar(labels, totals, color=colors, width=0.55)
    ax0.set_ylabel("Sum of bus/transit wait per step")
    ax0.set_title("Public transport wait (lower is better)")
    ymax = max(totals) if max(totals) > 0 else 1
    for i, v in enumerate(totals):
        ax0.text(i, v + ymax * 0.03, f"{int(v)}", ha="center", fontweight="bold", color="white")

    ax1 = axes[1]
    m1 = [baseline.transit_max_step_wait, dqn.transit_max_step_wait]
    m2 = [baseline.transit_vehicles_seen, dqn.transit_vehicles_seen]
    ax1.bar([i - width / 2 for i in x], m1, width=width, label="Max wait (1 step)", color="#d29922")
    ax1.bar([i + width / 2 for i in x], m2, width=width, label="Buses seen", color="#e3b341")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels)
    ax1.set_title("Peak & volume")
    ax1.legend(loc="upper right", fontsize=8, facecolor="#161b22", edgecolor="#30363d")

    title = "Public transport (bus) — baseline vs DQN"
    if title_suffix:
        title = f"{title} ({title_suffix})"
    _style_compare_axes(axes, title)
    fig.tight_layout()
    fig.savefig(path, facecolor="#0d1117", dpi=120)
    plt.close(fig)


def _plot_emergency_timeline(
    baseline: CompareEpisodeMetrics,
    dqn: CompareEpisodeMetrics,
    path: str,
    *,
    title_suffix: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), facecolor="#0d1117", sharey=True)

    for ax, metrics, label, color in (
        (axes[0], baseline, "Fixed-Time baseline", "#f85149"),
        (axes[1], dqn, "DQN", "#3fb950"),
    ):
        if metrics.timeline_sim_t and metrics.timeline_emergency_wait:
            ax.plot(
                metrics.timeline_sim_t,
                metrics.timeline_emergency_wait,
                color=color,
                linewidth=1.8,
                label="Emergency wait",
            )
        else:
            ax.text(0.5, 0.5, "No emergency vehicles", ha="center", va="center", color="#8b949e", transform=ax.transAxes)
        ax.set_xlabel("Simulation time (s)")
        ax.set_title(label)
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e")
        ax.yaxis.label.set_color("#8b949e")
        ax.title.set_color("#e6edf3")
        for spine in ax.spines.values():
            spine.set_color("#30363d")

    axes[0].set_ylabel("Emergency waiting time (all units)")
    title = "Emergency wait over time"
    if title_suffix:
        title = f"{title} ({title_suffix})"
    _style_compare_axes(axes, title)
    fig.tight_layout()
    fig.savefig(path, facecolor="#0d1117", dpi=120)
    plt.close(fig)


def _plot_transit_timeline(
    baseline: CompareEpisodeMetrics,
    dqn: CompareEpisodeMetrics,
    path: str,
    *,
    title_suffix: str,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), facecolor="#0d1117", sharey=True)

    for ax, metrics, label, color in (
        (axes[0], baseline, "Fixed-Time baseline", "#f85149"),
        (axes[1], dqn, "DQN", "#3fb950"),
    ):
        if metrics.timeline_sim_t and metrics.timeline_transit_wait:
            ax.plot(
                metrics.timeline_sim_t,
                metrics.timeline_transit_wait,
                color=color,
                linewidth=1.8,
                label="Bus/transit wait",
            )
        else:
            ax.text(
                0.5,
                0.5,
                "No buses in sim",
                ha="center",
                va="center",
                color="#8b949e",
                transform=ax.transAxes,
            )
        ax.set_xlabel("Simulation time (s)")
        ax.set_title(label)
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e")
        ax.yaxis.label.set_color("#8b949e")
        ax.title.set_color("#e6edf3")
        for spine in ax.spines.values():
            spine.set_color("#30363d")

    axes[0].set_ylabel("Bus/transit waiting time (all units)")
    title = "Public transport wait over time"
    if title_suffix:
        title = f"{title} ({title_suffix})"
    _style_compare_axes(axes, title)
    fig.tight_layout()
    fig.savefig(path, facecolor="#0d1117", dpi=120)
    plt.close(fig)
