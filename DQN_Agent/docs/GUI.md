# FlowGrid desktop GUI

The control panel runs with **`python flowgrid_gui.py`** (or `run_gui.bat`).

## Theme

- **Default:** modern **light** theme (off-white background, dark text, white cards).
- **Colors and fonts** live in [`gui/theme.py`](../gui/theme.py) — edit `THEME_LIGHT` to adjust the look.
- **Charts** use light plot areas with readable axis labels and a subtle grid.
- **Reports table** (`ttk.Treeview`) uses dark text on white rows.

A **dark** palette is kept as `THEME_DARK` in the same file for possible future use; the app currently loads **light** only.

## Typography

| Token | Font |
|-------|------|
| Body | Segoe UI 11 |
| Small / table | Segoe UI 10 |
| Section metrics | Segoe UI Semibold 15 |
| App title | Segoe UI 20 bold |
| Status log | Cascadia Mono 10 |

## Tabs

| Tab | Purpose |
|-----|---------|
| **Maps** | Build / select intersection maps |
| **Train** | DQN training, live chart, **Auto progress** (train→compare loop) |
| **Compare** | Baseline vs DQN, wait summaries and bar charts |
| **Reports** | Training dashboard, compare history table |

## Related

- [TRAINING.md](TRAINING.md) — training from CLI or GUI
- [COMPARE.md](COMPARE.md) — compare settings (inject time, delay)
- [CHANGELOG.md](CHANGELOG.md) — GUI theme change log
