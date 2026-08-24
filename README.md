# FlowGrid — Adaptive Traffic Light Control

A reinforcement learning agent that controls a single SUMO-simulated
intersection, trained to beat fixed-time signal control. This repo covers
both the Phase A proposal and the delivered Phase B project.

## Layout

- **`PhaseA/`** — the original Phase A submission (proposal document,
  presentation), unchanged.
- **`PhaseB/`** — the final submission: `FlowGrid_Capstone_Project_Book.docx`,
  the A0 poster PDF, and two standalone guides (`User_Guide.docx`,
  `Developer_Guide.docx`). `book_source/` holds the scripts that generate all
  three (`build_book.js`, `build_user_guide.js`, `build_dev_guide.js`) plus
  their chart images, so they can be regenerated.
- **`PPO_Agent/`** — the one current, submitted RL agent (V8): training/
  evaluation scripts, the trained model and checkpoints, every evaluation
  result, and its developer-only comparison app (with a built-in guided
  tour). Double click `run_web.bat` right in this folder to launch it.
  Start here.
- **`FlowGrid_Web/`** — a second, independent product: a SaaS-style traffic
  operations dashboard with its own dedicated backend, separate from
  `PPO_Agent`'s comparison app. One junction ("Live Junction (SUMO
  Simulation)") is wired to the real trained agent; everything else is a
  complete, working UI demo. Double click `FlowGrid_Web/run_web.bat` to
  launch it (one process, opens your browser automatically). Login:
  `admin`/`admin123` or `operator`/`op123`.
- **`Old_Versions/`** — every superseded agent, PPO and DQN alike: every
  earlier/alternate PPO version (V4 through V9, plus two longer-training
  experiments), the project's original DQN agent (superseded by PPO as the
  primary approach — see `PROJECT_OVERVIEW.md` and the book's Section 2.3
  for why), the project's pre-versioning first PPO experiments, and pre-RL
  prototype scripts. Kept for the record, not part of the final submission,
  but still runnable.
- **`SharedData/`** — the SUMO network/route files and shared reports data
  every agent, current and archived, reads from.
- **`PROJECT_OVERVIEW.md`** — the technical reference: MDP formulation,
  reward design, and algorithm choices for both PPO and DQN, and how the PPO
  agent's results were verified.
- **`requirements.txt`**, **`ReadMe - installations.txt`** — Python
  environment setup.

## Where to start

- Read the book: `PhaseB/FlowGrid_Capstone_Project_Book.docx`.
- Run the current agent (developer comparison tool): double click
  `PPO_Agent/run_web.bat`, or see `PPO_Agent/README.md`.
- See the customer-facing dashboard, with one junction genuinely live:
  double click `FlowGrid_Web/run_web.bat`, or see `FlowGrid_Web/README.md`.
- Run both at once for a full demo: `run_flowgrid_demo.bat`, at the
  project root.
- Watch the recorded demo video instead of running anything:
  https://drive.google.com/file/d/1BE3oeGWWbVrQEC_ZL0rVh5AdPs9kDNTY/view
- Run the original DQN agent: `Old_Versions/DQN_Agent/README.md`.
- Understand the RL design of either: `PROJECT_OVERVIEW.md`.
