"""
FlowGrid GUI theme — light default, optional dark.

Import ``C``, ``FONT``, ``apply_ttk_style``, and ``style_matplotlib_axes`` from here.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

THEME_LIGHT: dict[str, str] = {
    "bg": "#f6f8fb",
    "surface": "#ffffff",
    "surface2": "#f1f5f9",
    "border": "#e2e8f0",
    "text": "#0f172a",
    "muted": "#64748b",
    "accent": "#2563eb",
    "accent_dim": "#1d4ed8",
    "accent_soft": "#dbeafe",
    "success": "#16a34a",
    "success_dim": "#15803d",
    "danger": "#dc2626",
    "warning": "#d97706",
    "green": "#16a34a",
    "red": "#dc2626",
    "yellow": "#d97706",
    "input_bg": "#ffffff",
    "input_border": "#cbd5e1",
    "on_accent": "#ffffff",
    "on_success": "#ffffff",
    "chart_bg": "#ffffff",
    "chart_surface": "#f8fafc",
    "chart_grid": "#e2e8f0",
}

THEME_DARK: dict[str, str] = {
    "bg": "#0c0f14",
    "surface": "#151b26",
    "surface2": "#1e2736",
    "border": "#2d3a4f",
    "text": "#eef2f7",
    "muted": "#8b9cb3",
    "accent": "#4f8cff",
    "accent_dim": "#3566b8",
    "accent_soft": "#1a3055",
    "success": "#34d399",
    "success_dim": "#2bb87d",
    "danger": "#f87171",
    "warning": "#fbbf24",
    "green": "#34d399",
    "red": "#f87171",
    "yellow": "#fbbf24",
    "input_bg": "#1a2332",
    "input_border": "#2d3a4f",
    "on_accent": "#ffffff",
    "on_success": "#0c0f14",
    "chart_bg": "#0c0f14",
    "chart_surface": "#1e2736",
    "chart_grid": "#2d3a4f",
}

CANVAS_LIGHT: dict[str, str] = {
    "bg": "#f6f8fb",
    "road": "#cbd5e1",
    "road_line": "#94a3b8",
    "intersection": "#e2e8f0",
    "text": "#0f172a",
    "muted": "#64748b",
    "green": "#16a34a",
    "yellow": "#d97706",
    "red": "#dc2626",
    "vehicle": "#2563eb",
    "vehicle_hot": "#d97706",
    "border": "#e2e8f0",
}

CANVAS_DARK: dict[str, str] = {
    "bg": "#0a0e14",
    "road": "#2a3548",
    "road_line": "#3d4f6a",
    "intersection": "#1a2433",
    "text": "#eef2f7",
    "muted": "#6b7c93",
    "green": "#34d399",
    "yellow": "#fbbf24",
    "red": "#f87171",
    "vehicle": "#4f8cff",
    "vehicle_hot": "#fbbf24",
    "border": "#2d3a4f",
}

FONTS: dict[str, tuple] = {
    "body": ("Segoe UI", 11),
    "sm": ("Segoe UI", 10),
    "lg": ("Segoe UI Semibold", 15),
    "title": ("Segoe UI", 20, "bold"),
    "huge": ("Segoe UI", 28, "bold"),
    "btn": ("Segoe UI Semibold", 11),
    "card_title": ("Segoe UI", 9, "bold"),
    "mono": ("Cascadia Mono", 10),
}

_active_name = "light"


def get_theme(name: str = "light") -> dict[str, str]:
    return THEME_LIGHT if name == "light" else THEME_DARK


def get_canvas_colors(name: str = "light") -> dict[str, str]:
    return CANVAS_LIGHT if name == "light" else CANVAS_DARK


def set_active_theme(name: str) -> dict[str, str]:
    global C, _active_name
    _active_name = name
    C = get_theme(name)
    return C


# Module-level aliases (default: light)
C: dict[str, str] = get_theme("light")
FONT = FONTS["body"]
FONT_SM = FONTS["sm"]
FONT_LG = FONTS["lg"]
FONT_TITLE = FONTS["title"]
FONT_HUGE = FONTS["huge"]


def apply_ttk_style(root: tk.Misc, theme: dict[str, str] | None = None) -> ttk.Style:
    c = theme or C
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", background=c["surface"], foreground=c["text"], font=FONT)
    style.configure("TFrame", background=c["surface"])
    style.configure("TLabel", background=c["surface"], foreground=c["text"], font=FONT)

    style.configure("TNotebook", background=c["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=c["surface2"],
        foreground=c["muted"],
        padding=[18, 11],
        font=FONT,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", c["accent_soft"])],
        foreground=[("selected", c["text"])],
    )

    style.configure(
        "TCombobox",
        fieldbackground=c["input_bg"],
        background=c["surface"],
        foreground=c["text"],
        arrowcolor=c["muted"],
    )
    style.map("TCombobox", fieldbackground=[("readonly", c["input_bg"])])

    style.configure(
        "TSpinbox",
        fieldbackground=c["input_bg"],
        background=c["surface"],
        foreground=c["text"],
        arrowcolor=c["muted"],
    )

    style.configure(
        "TProgressbar",
        troughcolor=c["surface2"],
        background=c["accent"],
        thickness=12,
        borderwidth=0,
    )

    style.configure(
        "TCheckbutton",
        background=c["surface"],
        foreground=c["text"],
        font=FONT_SM,
    )
    style.map("TCheckbutton", background=[("active", c["surface2"])])

    style.configure(
        "Treeview",
        background=c["surface"],
        fieldbackground=c["surface"],
        foreground=c["text"],
        rowheight=26,
        font=FONT_SM,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=c["surface2"],
        foreground=c["text"],
        font=("Segoe UI Semibold", 10),
        relief="flat",
    )
    style.map(
        "Treeview",
        background=[("selected", c["accent_soft"])],
        foreground=[("selected", c["text"])],
    )

    style.configure(
        "Vertical.TScrollbar",
        troughcolor=c["surface2"],
        background=c["border"],
        arrowcolor=c["muted"],
        borderwidth=0,
    )
    style.map("Vertical.TScrollbar", background=[("active", c["muted"])])

    return style


def style_matplotlib_axes(
    ax: Any,
    xlabel: str = "",
    ylabel: str = "",
    *,
    theme: dict[str, str] | None = None,
    grid: bool = True,
) -> None:
    c = theme or C
    ax.tick_params(colors=c["muted"], labelsize=9)
    if xlabel:
        ax.set_xlabel(xlabel, color=c["muted"], fontsize=10)
    if ylabel:
        ax.set_ylabel(ylabel, color=c["muted"], fontsize=10)
    for spine in ax.spines.values():
        spine.set_color(c["border"])
    if grid:
        ax.grid(True, axis="y", linestyle="-", linewidth=0.6, color=c["chart_grid"], alpha=0.85)
        ax.set_axisbelow(True)


def legend_style(theme: dict[str, str] | None = None) -> dict[str, Any]:
    c = theme or C
    return {
        "loc": "upper right",
        "fontsize": 9,
        "facecolor": c["chart_surface"],
        "edgecolor": c["border"],
        "labelcolor": c["text"],
    }
