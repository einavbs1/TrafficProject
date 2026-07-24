const { p, para, h1, h2, h3, bullet, code, note, warning, simpleTable, coverPage, toc, buildDoc } = require("./build_guides.js");

const intro = [
  h1("1. Introduction and Audience"),
  p("This guide is written for a developer picking up the FlowGrid codebase after delivery: continuing the PPO agent's development, retraining it, adding a new baseline, or extending the evaluation tooling. It assumes working familiarity with Python, Git, and reinforcement learning terminology (state, action, reward, policy), and focuses on how this specific codebase is organized and why, rather than teaching RL from first principles. For MDP formulation, reward design, and algorithm choice in full technical depth, see PROJECT_OVERVIEW.md at the project root; this guide focuses on the code and workflow around that design, not the design itself."),
];

const architecture = [
  h1("2. System Architecture Overview"),
  p("The project is not a single application but three layers built on a shared simulation substrate:"),
  bullet("Simulation substrate: SUMO (Simulation of Urban Mobility), driven through the sumo-rl and TraCI/libsumo Python interfaces. Both agents (PPO and DQN) simulate the same physical intersection, defined once under SharedData/maps, and read/write shared evaluation data under SharedData/reports."),
  bullet("Agents: two independently developed reinforcement learning agents, PPO_Agent (final, submitted) and DQN_Agent (original, superseded), each with its own environment wrapper, training script, and trained model files. They are not two modules of one system; they are two separate, self contained implementations that happen to target the same simulated intersection."),
  bullet("Tooling: evaluation scripts (single run and full checkpoint sweeps), statistical comparison tools (comparison_core.py, shared by both a desktop Tkinter app and a FastAPI web app), and plotting utilities, all built specifically to make the agents' claims independently checkable rather than to just produce a headline number."),
  p("Data flows one direction through this stack: a trained model (.zip + matching vec_normalize .pkl for PPO; a .pth policy file for DQN) is loaded by an evaluation script, which drives the SUMO environment for one or more seeded episodes, and reports total waiting time and related metrics. Every comparison and analysis tool in the project is built on top of this same primitive, evaluate one model, on one seed, in one scenario, and get a number back."),
];

const repoStructure = [
  h1("3. Repository Structure"),
  simpleTable(
  ["Folder", "Contents"],
  [
  ["PPO_Agent/", "The final, submitted agent (V8). scripts/ has every runnable tool; models/ and checkpoints/ the trained weights; results/ every evaluation run performed against it; docs/ agent specific reference material."],
  ["DQN_Agent/", "The original agent. Self contained under its own flowgrid/ package (core/, rl/, maps/, eval/, jobs/, paths.py), with gui/, web/, scripts/, launchers/, data/, results/, docs/."],
  ["Old_Versions/", "Every superseded PPO version (V4 through V9, plus two longer training experiments), the project's pre versioning first experiments, and pre RL prototype scripts. See Old_Versions/README.md."],
  ["PhaseA/", "The original Phase A proposal submission, unchanged."],
  ["PhaseB/", "The final submission: the capstone book, the poster, this guide and the User Guide. book_source/ holds the scripts that generate all three (build_book.js, build_user_guide.js, build_dev_guide.js) plus their chart images."],
  ["SharedData/", "The SUMO network/route files and the shared reports data both agents read from and write to."],
  ["README.md, PROJECT_OVERVIEW.md", "Whole project overview and RL design reference, at the project root."],
  ],
  [2400, 6600]
  ),
];

const envSetup = [
  h1("4. Environment Setup for Development"),
  h2("4.1 Required Environment"),
  bullet("Python 3.10, with the packages listed in requirements.txt (notably: Stable-Baselines3, sb3-contrib, sumo-rl, pandas, matplotlib, seaborn, customtkinter, FastAPI, uvicorn)."),
  bullet("SUMO, including its Python/TraCI and libsumo bindings, installed and available on the system path (SUMO_HOME set)."),
  bullet("A multi core CPU: training and full evaluation sweeps run ten parallel simulation instances by default (SubprocVecEnv during training; ProcessPoolExecutor during evaluation)."),
  h2("4.2 Project Specific Installation"),
  p("Clone the repository, then install Python dependencies into a virtual environment. No project specific installation step beyond this is required; the environment and training scripts locate the SUMO network and route files via paths defined in the code, all anchored at the project root (SharedData/)."),
];

const ppoWalkthrough = [
  h1("5. The PPO Agent (V8), Code Walkthrough"),
  p("All PPO_Agent code lives flat inside PPO_Agent/scripts/, deliberately not nested under a version specific subfolder the way the archived versions in Old_Versions/PPO/saved_agents/ are, since V8 is the only version carried into the final submission."),
  h2("5.1 Environment: sumo_rl_env_V8.py"),
  p("Defines the Gymnasium environment: builds the 21 dimensional observation (phase one hot, elapsed green time, per lane demand, per lane starvation), the 2 action Keep/Switch action space, the action_masks() method enforcing minimum/maximum green and the hard empty intersection mask, and the reward calculation (diff waiting time minus a starvation penalty). sumo_rl_env.py is a one line shim (from sumo_rl_env_V8 import *) that every other script in this folder imports from generically, so swapping in a different version's environment during development only requires editing this one file."),
  h2("5.2 Training: train_V8.py"),
  code("cd PPO_Agent/scripts\npython train_V8.py --timesteps 6000000"),
  p("Builds a MaskablePPO agent (sb3-contrib) over ten parallel SUMO environments (SubprocVecEnv + VecNormalize), with a learning rate that decays linearly from 0.0003 down to 0 across the full run, and a constant entropy coefficient. Automatically resumes from the latest checkpoint in PPO_Agent/checkpoints/ if one exists; use the fresh flag shown below to force a clean run instead. Saves a checkpoint every 100k steps by default, each with its matching VecNormalize statistics, since resuming or evaluating a checkpoint without its matching stats silently corrupts the observation distribution."),
  code("python train_V8.py --timesteps 6000000 --fresh\npython train_V8.py --timesteps 6000000 --save-freq 50000"),
  warning("Never resume training after changing the reward function or observation definition. Load the old checkpoint, keep the old environment definition, or start fresh from random initialization. Never mix an old checkpoint with a changed environment. This produced a full, unrecoverable policy collapse once during this project (documented in the book, Section 2.6, the V3.3 incident)."),
  h2("5.3 Evaluation: evaluate_V8.py and evaluate_models.py"),
  code("cd PPO_Agent/scripts\npython evaluate_V8.py --seeds 5"),
  p("evaluate_V8.py auto finds the latest model in PPO_Agent/models/ and runs it against the three fixed time baselines across all three traffic scenarios, saving CSVs and charts to PPO_Agent/results/. The actual simulation running logic lives in evaluate_models.py, a single shared module every other tool in this folder also imports (run_evaluation_task, evaluate_scenario). Training, evaluation, comparison, and sweep tools all funnel through this one function rather than duplicating SUMO driving logic five times."),
  note("evaluate_models.py also exists as a separate copy at Old_Versions/PPO/src/evaluate_models.py, used by every archived version's own evaluate_*.py scripts. If you fix a bug in one copy, check whether the other needs the same fix."),
  h2("5.4 Comparison Tools: comparison_core.py, comparison_gui.py, comparison_web/"),
  p("comparison_core.py is UI agnostic: it owns the model registry (comparison_gui_models.json), task building (build_tasks), and the actual comparison run (run_comparison, which drives a ProcessPoolExecutor and reports progress via any object with a .put(msg) method). Both comparison_gui.py (Tkinter desktop app) and comparison_web/server.py (FastAPI, serving comparison_web/static/) import this module directly rather than duplicating its logic. A Tkinter queue.Queue and the web app's own JobState both satisfy the .put() interface run_comparison expects."),
  h2("5.5 Sweep and Analysis Tools"),
  simpleTable(
  ["Script", "Purpose"],
  [
  ["checkpoint_sweep.py", "Evaluates every saved checkpoint of a version on all 3 scenarios with a small fixed seed set: the full learning curve view."],
  ["final_results_random_seeds.py", "The project's most rigorous methodology: every checkpoint against its own independently drawn random seed and scenario, nothing reused or cherry picked. Crash safe: supports resuming an interrupted run or regenerating just the summary."],
  ["verify_candidates.py", "5 seed confirmation for a short list of candidate checkpoints, reusing already collected episodes where possible."],
  ["plot_checkpoint_waittime_scatter.py, plot_seed_detail.py", "Plotting utilities consumed by the sweep tools above, and directly reusable for a new version's results."],
  ["sweep_aggregate.py, regenerate_sweep_outputs.py", "Shared scenario/baseline definitions, and a tool to regenerate summary tables/plots from an existing raw CSV without re simulating."],
  ],
  [3000, 6000]
  ),
  p("All three of checkpoint_sweep.py, final_results_random_seeds.py, and verify_candidates.py take the target version's folder as a command line argument rather than hardcoding V8, so they work unmodified against any archived version under Old_Versions/PPO/saved_agents/ as well."),
  code("python final_results_random_seeds.py --version-dir ../../Old_Versions/PPO/saved_agents/V7"),
];

const dqnWalkthrough = [
  h1("6. The DQN Agent, Code Walkthrough"),
  p("DQN_Agent is a separate, self contained codebase under its own flowgrid/ package, not sharing any code with PPO_Agent."),
  simpleTable(
  ["Subfolder", "Contents"],
  [
  ["flowgrid/core/", "The SUMO environment, actuated signal logic, and intersection graph representation."],
  ["flowgrid/rl/", "The DQN agent itself: network, replay buffer, epsilon greedy exploration, target network."],
  ["flowgrid/maps/", "Building and saving map presets."],
  ["flowgrid/eval/", "Baseline vs trained comparison logic."],
  ["flowgrid/jobs/", "Background job handling shared by the GUI and web app."],
  ["flowgrid/paths.py", "Every directory location the project reads or writes, defined once. PROJECT_ROOT is computed as parents[2] relative to this file's own location, so DQN_Agent must stay a direct child of the project root for this to resolve correctly."],
  ],
  [2600, 6400]
  ),
  p("The reward function (in flowgrid/core/, referenced from the DQN training loop) sums roughly a dozen hand tuned terms (diff wait, absolute wait penalty, spillback penalty, throughput bonus, fairness terms, anti flicker penalty, invalid action penalty). See PROJECT_OVERVIEW.md Section 3 for the exact formula and coefficients, and the book Section 2.3 for why this reward's complexity, and the resulting instability documented in DQN_Agent/results/comparison_history.json, motivated the move to PPO."),
];

const retraining = [
  h1("7. Retraining or Extending the PPO Agent"),
  p("To train a new version, copy PPO_Agent/scripts/ (and the model files, if building on an existing one) into a new folder under Old_Versions/PPO/ rather than modifying PPO_Agent/ in place. This preserves the current submitted agent as a working reference and follows the same \"copy, don't mutate\" convention used throughout this project's version history (see the archived V4 through V9 folders, each a fresh copy rather than an in place edit of the previous one)."),
  bullet("Copy sumo_rl_env_V8.py to a new file with an updated name; update the sumo_rl_env.py shim's import to point at it."),
  bullet("Copy train_V8.py and evaluate_V8.py; no path edits are needed if the new folder sits at the same depth, since the training step count and other hyperparameters are already command line arguments."),
  bullet("Never resume training an existing checkpoint after changing its reward function or observation definition. Train a fresh agent from random initialization instead."),
];

const newBaseline = [
  h1("8. Adding a New Baseline or Comparison Target"),
  p("New fixed time or rule based baselines can be added by extending AVAILABLE_BASELINES in comparison_core.py; each baseline needs only a name and, for fixed time controllers, a cycle length, since the comparison tools handle result collection and reporting generically through evaluate_models.py's existing \"fixed\" model type. A previously evaluated baseline, Max Pressure, is deliberately excluded from AVAILABLE_BASELINES after being diagnosed as gridlocking on this network's specific left turn lane geometry (see the book, Section 2.6); re adding it would require first addressing that underlying network issue, not just registering the baseline."),
];

const evalSweep = [
  h1("9. Running an Evaluation Sweep"),
  p("final_results_random_seeds.py and checkpoint_sweep.py both support a dry run flag that reports exactly how many simulation runs a given sweep will perform and how long it is expected to take, without executing anything. Always run this first before committing to a long sweep."),
  code("python final_results_random_seeds.py --version-dir .. --dry-run\npython final_results_random_seeds.py --version-dir .."),
  p("Sweeps write partial results incrementally as they progress (assignments.csv is written up front with the full plan; final_results.csv is appended to after every checkpoint completes). If interrupted, resuming with the flag shown below continues exactly where it left off using the original plan; the summarize only flag regenerates summary.txt and the charts from whatever rows already exist, without running anything new."),
  code("python final_results_random_seeds.py --version-dir .. --resume <out_dir>\npython final_results_random_seeds.py --version-dir .. --summarize-only <out_dir>"),
];

const methodology = [
  h1("10. Testing and Verification Methodology"),
  p("This project's evaluation rigor escalated deliberately over its course, and the same escalation is worth reusing for any future work on this codebase rather than trusting an early, less rigorous result:"),
  bullet("A couple of fixed seeds, used throughout early development for fast iteration."),
  bullet("Five, then fifty independently drawn seeds, when a specific comparison needed more statistical confidence."),
  bullet("Every saved checkpoint against its own freshly drawn random seed and scenario (final_results_random_seeds.py), nothing reused, nothing cherry picked, no unfavorable result excluded. This is what let the project report, with real confidence, that the champion agent beats all three fixed time baselines on 53 of 60 independently random evaluations (88.3%)."),
  p("Two properties of the environment make this methodology trustworthy rather than just elaborate: SUMO's seeded vehicle generation is genuinely deterministic (the same seed produces a bit for bit identical vehicle stream regardless of which controller is driving the signal, verified empirically across process restarts), and evaluation episodes now terminate as soon as the road is genuinely empty rather than running to a fixed time limit, which cut typical evaluation time by roughly seven to eight times with no change to the reported results."),
];

const limitations = [
  h1("11. Known Limitations and Future Work"),
  bullet("Single intersection scope: this project controls one intersection; multi intersection coordination is unattempted future work."),
  bullet("High traffic ceiling: performance near the intersection's physical demand capacity reflects queueing physics, not a perception limitation (ruled out directly by a V9 experiment with a richer, non saturating observation encoding, see the book, Section 2.7)."),
  bullet("Training is not reproducible run to run: two independent runs of the identical V8 recipe (V8 and V8_replicate) produced meaningfully different stability profiles. The leading hypothesis is the constant, non decaying entropy coefficient; this is a concrete, addressable item for future work, not a fully solved question."),
  bullet("Computer vision perception (YOLO + DeepSORT), proposed in the original Phase A plan, was not implemented in this delivered scope. See the book, Section 2.3, for the full explanation. It remains the most natural next step for extending this project toward real world deployment."),
  bullet("No formal, rigorous head to head comparison exists between the DQN agent and the fixed time baselines using the same seed verified methodology applied to PPO; DQN_Agent/results/comparison_history.json contains real evaluation history but was not brought to the same level of statistical rigor."),
];

const conventions = [
  h1("12. Coding Conventions Observed in This Codebase"),
  bullet("Copy, don't mutate: a new agent version is a new folder, never an in place edit of a previous one's environment or training script. This preserves every earlier version as a working, comparable reference."),
  bullet("Path resolution: every script computes _HERE = os.path.dirname(os.path.abspath(__file__)) and builds paths relative to it, rather than assuming a particular working directory. Shared modules (evaluate_models.py) are colocated as sibling files within PPO_Agent/scripts/ rather than imported via a separate src/ folder one level up, which is how the earlier, archived versions under Old_Versions/PPO/ still do it. This is a historical difference worth knowing about if you compare the two, not an inconsistency to \"fix.\""),
  bullet("Crash safety: any long running sweep writes its full plan before starting and appends results incrementally, so a kill or crash partway through loses nothing already computed and can be resumed."),
  bullet("Structural constraints over penalties: wherever a behavior must never happen (switching an empty intersection, violating minimum/maximum green), the project moved from discouraging it with a reward penalty to preventing it outright via action masking, after direct evidence that penalties alone were unreliable. Apply the same principle to any new hard constraint."),
];

buildDoc("Developer_Guide.docx", [
  ...coverPage("Developer / Maintenance Guide", "How to continue developing, retraining, or extending FlowGrid"),
  ...toc(),
  ...intro,
  ...architecture,
  ...repoStructure,
  ...envSetup,
  ...ppoWalkthrough,
  ...dqnWalkthrough,
  ...retraining,
  ...newBaseline,
  ...evalSweep,
  ...methodology,
  ...limitations,
  ...conventions,
]);
