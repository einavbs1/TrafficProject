# FlowGrid — Adaptive Traffic Light Control

A reinforcement learning agent that controls a single SUMO-simulated
intersection, trained to beat fixed-time signal control. This repo covers
both the Phase A proposal and the delivered Phase B project.

## Layout

- **`PhaseA/`** — the original Phase A submission (proposal document,
  presentation), unchanged.
- **`PhaseB/`** — the final submission: `FlowGrid_Capstone_Project_Book.docx`,
  the A0 poster PDF, and two standalone guides (`User_Guide.md`,
  `Developer_Guide.md`). `book_source/` holds the script that generates the
  book (`build_book.js`) plus its chart images, so it can be regenerated.
- **`PPO_Agent/`** — the final, submitted RL agent (V8): training/evaluation
  scripts, the trained model and checkpoints, every evaluation result, and
  the two comparison apps (desktop + web). Start here for the current agent.
- **`DQN_Agent/`** — the project's original RL approach: its own GUI, web
  dashboard, scripts, and evaluation history. Superseded by PPO Agent as the
  primary approach (see `PROJECT_OVERVIEW.md` and the book's Section 2.3
  for why), but fully preserved and still runnable.
- **`Old_Versions/`** — everything superseded: every earlier/alternate PPO
  version (V4 through V9, plus two longer-training experiments), the
  project's pre-versioning first experiments, and pre-RL prototype scripts.
  Kept for the record, not part of the final submission.
- **`SharedData/`** — the SUMO network/route files and shared reports data
  both agents read from.
- **`PROJECT_OVERVIEW.md`** — the technical reference: MDP formulation,
  reward design, and algorithm choices for both agents, and how the PPO
  agent's results were verified.
- **`requirements.txt`**, **`ReadMe - installations.txt`** — Python
  environment setup.

## Where to start

- Read the book: `PhaseB/FlowGrid_Capstone_Project_Book.docx`.
- Run the current agent: `PPO_Agent/README.md`.
- Run the original agent: `DQN_Agent/README.md`.
- Understand the RL design of either: `PROJECT_OVERVIEW.md`.
