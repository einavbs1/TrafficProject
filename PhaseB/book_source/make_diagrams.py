"""Generates the architecture and MDP-loop diagrams embedded in the book
and the Developer Guide. Run from this folder: python make_diagrams.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.path import Path
import matplotlib.patches as mpatches

NAVY = "#16213e"
NAVY_SOFT = "#1f2d4d"
GREEN = "#2ecc71"
BG = "#f5f6fa"
BORDER = "#e9eaee"
TEXT_MUTED = "#6b7280"


def box(ax, xy, w, h, title, subtitle=None, fc="white", ec=NAVY, tc=NAVY, lw=1.8):
    x, y = xy
    patch = FancyBboxPatch((x, y), w, h,
                            boxstyle="round,pad=0.02,rounding_size=0.08",
                            linewidth=lw, edgecolor=ec, facecolor=fc)
    ax.add_patch(patch)
    if subtitle:
        ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center",
                 fontsize=11.5, fontweight="bold", color=tc)
        ax.text(x + w / 2, y + h * 0.30, subtitle, ha="center", va="center",
                 fontsize=8.7, color=TEXT_MUTED, wrap=True)
    else:
        ax.text(x + w / 2, y + h / 2, title, ha="center", va="center",
                 fontsize=11.5, fontweight="bold", color=tc)
    return (x, y, w, h)


def arrow(ax, start, end, label=None, color=NAVY, style="-|>", curve=0.0, lw=1.6):
    a = FancyArrowPatch(start, end, arrowstyle=style, mutation_scale=14,
                         color=color, linewidth=lw,
                         connectionstyle=f"arc3,rad={curve}")
    ax.add_patch(a)
    if label:
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        ax.text(mx, my + 0.18, label, ha="center", va="bottom", fontsize=8.3,
                 color=TEXT_MUTED, style="italic")


# ---------------------------------------------------------------------------
# Diagram 1: System architecture (what was actually delivered)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 7.4), dpi=150)
fig.patch.set_facecolor("white")
ax.set_xlim(0, 11)
ax.set_ylim(0, 7.6)
ax.axis("off")

sumo = box(ax, (0.4, 5.1), 2.6, 1.3, "SUMO Simulator", "Traffic microsimulation\n(TraCI)")
env = box(ax, (3.6, 5.1), 3.0, 1.3, "Environment Wrapper", "sumo_rl_env_V8.py:\nobservation, action mask, reward")
agent = box(ax, (7.2, 5.1), 3.2, 1.3, "MaskablePPO Agent", "sb3-contrib policy\n(trained, 21-dim obs)")

evalengine = box(ax, (3.6, 2.9), 3.0, 1.3, "Evaluation Engine", "evaluate_models.py:\nruns scored episodes")
webapp = box(ax, (7.2, 2.9), 3.2, 1.3, "Comparison Web App", "FastAPI + comparison_core.py\n+ guided tour frontend")
browser = box(ax, (7.2, 0.6), 3.2, 1.3, "Browser (User)", "pick model, seed, scenario\nwatch results", fc=NAVY, tc="white", ec=NAVY)

arrow(ax, (3.0, 5.75), (3.6, 5.75), "state via TraCI")
arrow(ax, (3.6, 5.35), (3.0, 5.35), "control command", color=TEXT_MUTED)
arrow(ax, (6.6, 5.75), (7.2, 5.75), "observation")
arrow(ax, (7.2, 5.35), (6.6, 5.35), "action (Keep / Switch)", color=TEXT_MUTED)

arrow(ax, (5.1, 5.1), (5.1, 4.2), "drives episodes")
arrow(ax, (1.7, 5.1), (4.2, 4.2), curve=-0.2, color=TEXT_MUTED, label=None)

arrow(ax, (6.6, 3.55), (7.2, 3.55), "task results")
arrow(ax, (8.8, 2.9), (8.8, 1.9), "HTTP / JSON")
arrow(ax, (9.3, 1.9), (9.3, 2.9), curve=0.0, color=TEXT_MUTED)

ax.text(5.5, 7.35, "FlowGrid System Architecture", ha="center", fontsize=15,
        fontweight="bold", color=NAVY)
ax.text(5.5, 7.0, "The delivered system: ground-truth SUMO state in, a trained control policy out,",
        ha="center", fontsize=9, color=TEXT_MUTED)
ax.text(5.5, 6.75, "wrapped in tooling built to make its performance independently checkable.",
        ha="center", fontsize=9, color=TEXT_MUTED)

plt.tight_layout()
plt.savefig("architecture_diagram.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("saved architecture_diagram.png")

# ---------------------------------------------------------------------------
# Diagram 2: MDP / RL training loop
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 6), dpi=150)
fig.patch.set_facecolor("white")
ax.set_xlim(0, 8)
ax.set_ylim(0, 7.2)
ax.axis("off")

agent_b = box(ax, (0.6, 4.6), 3.0, 1.4, "Agent", "MaskablePPO policy\nπ(action | state)", fc=NAVY, tc="white", ec=NAVY)
env_b = box(ax, (4.4, 4.6), 3.0, 1.4, "Environment", "SUMO intersection\n+ traffic demand")

arrow(ax, (3.6, 5.5), (4.4, 5.5), "action a_t\n(Keep / Switch)", curve=-0.15)
arrow(ax, (4.4, 4.9), (3.6, 4.9), "state s_t+1, reward r_t\n(-Δ waiting time - starvation)", curve=-0.15, color=TEXT_MUTED)

steps = [
    "1. Agent observes the 21-dim state: phase, elapsed green, per-lane demand, per-lane starvation.",
    "2. Action mask blocks Switch if minimum green not met, or the intersection is empty.",
    "3. Agent picks Keep or Switch; environment steps SUMO forward 5 simulated seconds.",
    "4. Reward = reduction in total waiting time, minus a starvation penalty.",
    "5. Repeat until the episode ends (traffic demand exhausted); update the policy (PPO, clipped).",
]
y = 3.7
for s in steps:
    ax.text(0.5, y, s, fontsize=9.3, color=NAVY, va="top")
    y -= 0.62

ax.text(4.0, 6.85, "The Reinforcement Learning Loop", ha="center", fontsize=15,
        fontweight="bold", color=NAVY)

plt.tight_layout()
plt.savefig("mdp_loop_diagram.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("saved mdp_loop_diagram.png")

# ---------------------------------------------------------------------------
# Diagram 3: Activity diagram of the actual decision loop (swimlanes), the
# delivered counterpart to Phase A's Figure 6 cross-functional flowchart --
# same visual convention, but no YOLO/DeepSORT/priority/fallback, since none
# of that was built. This is what PPO_Agent's step loop actually does.
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 8.6), dpi=150)
fig.patch.set_facecolor("white")
W, H = 11, 8.8
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

LANE_TOP = 8.1
LANE_BOTTOM = 0.3
lane_x = [0.3, 3.9, 7.5, 10.7]
lane_names = ["SUMO Environment", "SwitchOrKeepWrapper", "PPO Agent"]
for i, name in enumerate(lane_names):
    x0, x1 = lane_x[i], lane_x[i + 1]
    ax.add_patch(plt.Rectangle((x0, LANE_BOTTOM), x1 - x0, LANE_TOP - LANE_BOTTOM,
                                 fill=False, edgecolor=BORDER, linewidth=1.4))
    ax.text((x0 + x1) / 2, LANE_TOP + 0.18, name, ha="center", fontsize=10.5,
             fontweight="bold", color=NAVY)
for x in lane_x[1:-1]:
    ax.plot([x, x], [LANE_BOTTOM, LANE_TOP], color=BORDER, linewidth=1.4)

def act(cx, cy, w, h, text, fc="white"):
    box(ax, (cx - w / 2, cy - h / 2), w, h, text, fc=fc, lw=1.4)

def diamond(cx, cy, w, h, text):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    ax.add_patch(plt.Polygon(pts, closed=True, fill=True, facecolor="white",
                              edgecolor=NAVY, linewidth=1.4))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=7.6, color=NAVY, wrap=True)

def vline(x, y0, y1, color=NAVY):
    ax.annotate("", xy=(x, y1), xytext=(x, y0),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5))

def hline(x0, x1, y, color=NAVY):
    ax.annotate("", xy=(x1, y), xytext=(x0, y),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5))

start_y = 7.6
ax.add_patch(plt.Circle((2.1, start_y), 0.12, color=NAVY))
ax.text(2.1, start_y - 0.38, "start / next\ndecision step", ha="center", fontsize=7.5, color=TEXT_MUTED)

act(2.1, 6.65, 3.0, 0.7, "Capture raw state via TraCI\n(queues, phase, elapsed green)")
vline(2.1, 7.45, 7.0)

hline(3.6, 5.75, 6.65)
act(5.65, 6.65, 3.1, 0.7, "Construct 21-dim observation\n(demand + starvation, camera-limited)")

vline(5.65, 6.3, 5.75)
diamond(5.65, 5.1, 3.0, 1.0, "Min green met AND\nintersection non-empty?")

ax.text(4.05, 5.1, "no", fontsize=8, color=TEXT_MUTED)
vline(5.65, 4.6, 4.05)
act(5.65, 3.55, 3.1, 0.7, "Mask out Switch\n(only Keep is legal)")

ax.text(7.05, 5.3, "yes", fontsize=8, color=TEXT_MUTED)
ax.annotate("", xy=(9.3, 2.95), xytext=(7.15, 5.1),
            arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.5,
                             connectionstyle="arc3,rad=-0.15"))

vline(5.65, 3.2, 2.5)
hline(5.65, 8.0, 2.5)
act(9.3, 2.5, 2.6, 0.9, "PPO selects Keep\nor Switch\n(mask applied)")

hline(9.3, 5.65, 1.55)
vline(5.65, 1.9, 1.55)
diamond(5.65, 0.95, 2.6, 1.0, "Switch\nselected?")

ax.text(3.5, 0.95, "yes", fontsize=8, color=TEXT_MUTED)
hline(4.35, 2.15, 0.95)
act(1.3, 0.95, 1.7, 0.9, "Apply yellow\ntransition,\nadvance phase")

ax.text(6.1, 0.3, "no: hold current phase", fontsize=7.6, color=TEXT_MUTED, ha="left")

ax.annotate("", xy=(1.3, 6.3), xytext=(1.3, 1.4),
            arrowprops=dict(arrowstyle="-|>", color=TEXT_MUTED, lw=1.4,
                             connectionstyle="arc3,rad=0.22"))
ax.text(0.55, 3.85, "step SUMO forward 5s,\ncompute reward, loop", fontsize=7.5,
        color=TEXT_MUTED, ha="center", rotation=90)

ax.text(W / 2, 8.6, "PPO Decision Loop (as actually implemented)", ha="center",
        fontsize=14.5, fontweight="bold", color=NAVY)

plt.tight_layout()
plt.savefig("ppo_activity_diagram.png", dpi=150, bbox_inches="tight", facecolor="white")
plt.close()
print("saved ppo_activity_diagram.png")
