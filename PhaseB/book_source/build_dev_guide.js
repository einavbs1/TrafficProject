const { p, para, h1, h2, h3, bullet, code, note, warning, simpleTable, coverPage, toc, buildDoc, fs, path, ImageRun, AlignmentType } = require("./build_guides.js");

const intro = [
  h1("1. Introduction and Audience"),
  p("This guide is written for a developer picking up the FlowGrid codebase after delivery: continuing the PPO agent's development, retraining it, adding a new baseline, or extending the evaluation tooling. It assumes working familiarity with Python, Git, and reinforcement learning terminology (state, action, reward, policy), and focuses on how this specific codebase is organized and why, rather than teaching RL from first principles. For MDP formulation, reward design, and algorithm choice in full technical depth, see PROJECT_OVERVIEW.md at the project root; this guide focuses on the code and workflow around that design, not the design itself."),
];

const architecture = [
  h1("2. System Architecture Overview"),
  p("The project is not a single application but three layers built on a shared simulation substrate:"),
  bullet("Simulation substrate: SUMO (Simulation of Urban Mobility), driven through the sumo-rl and TraCI/libsumo Python interfaces. Both agents (PPO and DQN) simulate the same physical intersection, defined once under SharedData/maps, and read/write shared evaluation data under SharedData/reports."),
  bullet("Agents: two independently developed reinforcement learning agents, PPO_Agent (final, submitted, at the project root) and DQN_Agent (original, superseded, archived under Old_Versions/), each with its own environment wrapper, training script, and trained model files. They are not two modules of one system; they are two separate, self contained implementations that happen to target the same simulated intersection."),
  bullet("Tooling: evaluation scripts (single run and full checkpoint sweeps), the FastAPI comparison web app (comparison_core.py plus comparison_web/), and plotting utilities, all built specifically to make the agents' claims independently checkable rather than to just produce a headline number."),
  p("Data flows one direction through this stack: a trained model (.zip + matching vec_normalize .pkl for PPO; a .pth policy file for DQN) is loaded by an evaluation script, which drives the SUMO environment for one or more seeded episodes, and reports total waiting time and related metrics. Every comparison and analysis tool in the project is built on top of this same primitive, evaluate one model, on one seed, in one scenario, and get a number back."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_framework_diagram.png")), transformation: { width: 560, height: 287 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 1: the training and simulation core (PPO_Agent/scripts/train_V8.py + sumo_rl_env_V8.py). SubprocVecEnv runs ten parallel SUMO instances; VecNormalize tracks running observation statistics; the SwitchOrKeepWrapper is the actual translation layer between raw SUMO state and the agent's 21 dimensional observation, and between the agent's action and SUMO's TraCI control commands.", { italics: true, size: 20 }),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "architecture_diagram.png")), transformation: { width: 500, height: 335 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2: the evaluation and comparison layer built around that same core, evaluate_models.py driving scored episodes on demand, and the FastAPI comparison_web app (comparison_core.py) exposing that to a browser. This is the layer described in the Tooling bullet above; the Evaluation Engine and Comparison Web App boxes here correspond directly to evaluate_models.py and comparison_web/server.py in the repository.", { italics: true, size: 20 }),
];

const repoStructure = [
  h1("3. Repository Structure"),
  simpleTable(
  ["Folder", "Contents"],
  [
  ["PPO_Agent/", "The one current, submitted agent (V8), at the project root. run_web.bat launches its comparison app directly; scripts/ has every runnable tool; models/ and checkpoints/ the trained weights; results/ every evaluation run performed against it; docs/ agent specific reference material."],
  ["FlowGrid_Web/", "A second, independent product (Section 6): a SaaS style dashboard with one junction wired to a real live agent, with its own backend under backend/, entirely separate from PPO_Agent/scripts/comparison_web/."],
  ["Old_Versions/", "Every superseded agent: PPO/ (every earlier PPO version, V4 through V9, plus two longer training experiments, and the project's pre versioning first experiments), DQN_Agent/ (the original agent in full, self contained under its own flowgrid/ package, with gui/, web/, scripts/, launchers/, data/, results/, docs/), and root_prototype/ (pre RL prototype scripts). See Old_Versions/README.md."],
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
  bullet("Python 3.10, with the packages listed in requirements.txt (notably: Stable-Baselines3, sb3-contrib, sumo-rl, pandas, matplotlib, seaborn, FastAPI, uvicorn)."),
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
  h2("5.4 Comparison Tools: comparison_core.py, comparison_web/"),
  p("comparison_core.py is UI agnostic: it owns the model registry (model_registry.json), task building (build_tasks), and the actual comparison run (run_comparison, which drives a ProcessPoolExecutor and reports progress via any object with a .put(msg) method). comparison_web/server.py (FastAPI, serving comparison_web/static/) imports this module directly rather than duplicating its logic; the web app's own JobState satisfies the .put() interface run_comparison expects. The frontend (comparison_web/static/) is plain HTML/CSS/JS, no framework or build step, and includes a floating step by step guided tour (tour.js) that auto starts on every page load, reusing the static help text already written under each field so wording is never duplicated."),
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
  p("All three of checkpoint_sweep.py, final_results_random_seeds.py, and verify_candidates.py take the target version's folder as a command line argument rather than hardcoding V8, so they work unmodified against any archived version under Old_Versions/PPO/saved_agents/ as well. Note that each archived version's checkpoints/ was thinned to roughly one in ten of its original checkpoints to keep this submission a reasonable size, always keeping the first and last (see Old_Versions/README.md), so these tools still find real data to sweep over, just at a coarser resolution than the original training run."),
  code("python final_results_random_seeds.py --version-dir ../../Old_Versions/PPO/saved_agents/V7"),
];

const flowgridWebWalkthrough = [
  h1("6. FlowGrid_Web, a Second, Independent Product"),
  p("FlowGrid_Web/ is a separate React/Vite SaaS style dashboard, added in this phase alongside the original comparison_web/ app. It is deliberately a separate product, not a new view bolted onto the developer facing comparison tool: comparison_web/ is a developer only tool for comparing checkpoints; FlowGrid_Web is the customer facing product, meant to demonstrate what a deployed traffic operations dashboard could look like. Consequently it has its own backend, FlowGrid_Web/backend/server.py, a second FastAPI app running on its own port (8001), entirely separate from comparison_web/server.py (port 8000). The two servers share no code by reference to each other; they both import the same underlying comparison_core.py and evaluate_models.py modules as shared library code, the same way any two independent applications might share a common engine."),
  p("Its pages (login, junction navigation, dashboard, live stream, device settings, reports, users) are a UI complete demonstration of a fully deployed system, backed by in memory demo data generated client side, except for one seed junction, LIVE_JUNCTION_ID (id 100, \"Live Junction (SUMO Simulation)\" in src/JunctionContext.jsx), whose Dashboard page is wired to FlowGrid_Web's own backend below."),
  h2("6.1 FlowGrid_Web's Own Backend (FlowGrid_Web/backend/server.py)"),
  simpleTable(
    ["Endpoint", "Purpose"],
    [
      ["GET /api/live_state", "Returns the current live_state dict: active, per direction lane_queues and phase_colors, step, and the seed of the current run. {\"active\": false} if nothing has run yet."],
      ["POST /api/live_demo/start", "The Live Junction panel's only control: body is just {scenario}, no model picker, no seed field. Always the already registered champion checkpoint (comparison_core.DEFAULT_MODEL_PATH), always a server chosen random seed (random.randint), always Watch Live on."],
    ],
    [3000, 6000]
  ),
  p("This file builds its own small job_state (just enough of comparison_web's JobState shape for core.run_comparison to report into) and its own live_state, a multiprocessing.Manager().dict() created lazily on first use rather than at import time, since Windows' spawn based multiprocessing would otherwise try to create a manager process recursively when uvicorn re imports this module. comparison_web/server.py has no CORS entry and no live_state at all, it does not need either, since only FlowGrid_Web calls cross origin."),
  warning("CORSMiddleware here allows all four of 127.0.0.1/localhost times 5173/8001, not just the Vite dev origin. Once this same server also serves the built frontend (Section 6.4), the page can be loaded as either http://127.0.0.1:8001 or http://localhost:8001, and the frontend's fetch() calls are hardcoded to http://127.0.0.1:8001; if the page happened to load via the \"localhost\" hostname, that pairing is a different origin to the browser even though it is the same machine and the same port, and the preflight OPTIONS request fails with 400 unless that exact origin is also allowed. Missing this is an easy way to reintroduce a \"why does Run Agent silently fail\" bug."),
  h2("6.2 Publishing Live State (evaluate_models.py, shared by both servers)"),
  p("evaluate_model_on_seed() takes a new optional live_state parameter, the same Manager().dict() proxy, threaded through comparison_core.build_tasks() and run_evaluation_task() only when use_gui is true. This is shared code: comparison_web/server.py's own Watch Live path always passes None here and is unaffected; only FlowGrid_Web's backend passes a real live_state. Inside the per step loop, _publish_live_state(ts, live_state, step_count, total_queued) does three things every step:"),
  bullet("Sums each lane's real halting vehicle count (sumo.lane.getLastStepHaltingNumber), grouped by compass direction from the lane ID's prefix (n_/s_/e_/w_to_center_*), not ts.get_lanes_queue(), which returns a [0, 1] lane capacity fraction rather than a human readable count."),
  bullet("Derives each direction's signal color from ts.sumo.trafficlight.getRedYellowGreenState(ts.id), matched against getControlledLanes(ts.id) by index. This network has an always on, lowercase g \"permitted\" slip lane at index 0 of every approach, so only uppercase G is treated as a real green; treating lowercase g as green shows every direction as green simultaneously, which is wrong."),
  bullet("Calls ts.sumo.gui.screenshot(\"View #0\", path), writing directly into FlowGrid_Web/backend/static/live_snapshot.png (not comparison_web/static/, the two servers' static folders are entirely separate), which that backend's own /static mount serves. FlowGrid_Web polls this with a cache busting ?step= query parameter."),
  p("Separately, create_sumo_env() (sumo_rl_env_V8.py) gained an additional_sumo_cmd parameter, passed through to sumo_rl.SumoEnvironment. evaluate_model_on_seed() passes \"--delay 100\" whenever live_state is not None, pacing the SUMO GUI to at least 100 milliseconds of real time per simulated second, specifically so FlowGrid_Web's 1 second poll has something meaningful to show."),
  h2("6.3 Frontend Pieces (FlowGrid_Web/src/)"),
  simpleTable(
    ["File", "Role"],
    [
      ["JunctionContext.jsx", "Defines LIVE_JUNCTION_ID and the seed LIVE_JUNCTION entry, prepended to the existing demo junction list."],
      ["pages/Dashboard.jsx", "When the active junction is LIVE_JUNCTION_ID, polls http://127.0.0.1:8001/api/live_state once a second instead of generating random metrics, renders the Run Agent control (scenario only, no seed field, POSTs to /api/live_demo/start), and swaps each camera card's placeholder for an <img> pointed at /static/live_snapshot.png, cache busted by the current step."],
      ["Tour.jsx", "A small React reimplementation of comparison_web's vanilla tour.js: spotlights one target element (a React ref) at a time with a title/text pair supplied by the mounting page, auto starting on every page visit. Each page (JunctionSelect.jsx, Dashboard.jsx) mounts its own instance with its own steps."],
    ],
    [2600, 6400]
  ),
  warning("Tour.jsx's auto start effect deliberately does not gate on whether target refs are already populated at mount time. React's StrictMode double invokes effects in development, which briefly detaches and reattaches refs; a closure that captured \"zero valid steps\" at that exact instant would permanently latch onto that stale value, since the effect never runs a second time. The render itself already guards on a missing step by rendering nothing, so the fix is simply not to gate the timer on ref readiness at all."),
  h2("6.4 One Process, Not Two: Serving the Built Frontend"),
  p("server.py also serves the built dashboard itself, so running FlowGrid_Web never needs a separate Vite dev server. After npm run build writes FlowGrid_Web/dist/, server.py mounts dist/assets under /assets and registers a catch all route, @app.get(\"/{full_path:path}\"), registered after every /api/* route so those are always matched first. The catch all returns the requested file if it exists in dist/, or falls back to dist/index.html otherwise, which is what lets React Router's client side routes (e.g. /reports) survive a hard refresh. main() only opens a browser tab automatically when dist/ exists, so running the API alone during development (Section 6.5) does not pop open a stale or empty tab."),
  p("run_web.bat (or run_web.vbs for no console window) does exactly this: npm run build, then python server.py, nothing else. It never touches comparison_web/server.py. Separately, run_flowgrid_demo.bat at the project root starts both independent products, comparison_web's dev tool and FlowGrid_Web, for a full project demo."),
  code("cd FlowGrid_Web\nrun_web.bat"),
  h2("6.5 Active Frontend Development"),
  p("When actively editing FlowGrid_Web's React code, run the Vite dev server instead, for hot reload, alongside the same backend, in a second window, for the API:"),
  code("npm run dev\ncd backend && python server.py"),
  p("Dashboard.jsx's PPO_API constant is a hardcoded http://127.0.0.1:8001 regardless of dev or built mode, so both setups work against the same backend unmodified; only the page's own origin (5173 while developing, 8001 once built and served) changes."),
];

const dqnWalkthrough = [
  h1("7. The DQN Agent, Code Walkthrough"),
  p("DQN_Agent, archived under Old_Versions/DQN_Agent/, is a separate, self contained codebase under its own flowgrid/ package, not sharing any code with PPO_Agent."),
  simpleTable(
  ["Subfolder", "Contents"],
  [
  ["flowgrid/core/", "The SUMO environment, actuated signal logic, and intersection graph representation."],
  ["flowgrid/rl/", "The DQN agent itself: network, replay buffer, epsilon greedy exploration, target network."],
  ["flowgrid/maps/", "Building and saving map presets."],
  ["flowgrid/eval/", "Baseline vs trained comparison logic."],
  ["flowgrid/jobs/", "Background job handling shared by the GUI and web app."],
  ["flowgrid/paths.py", "Every directory location the project reads or writes, defined once. PROJECT_ROOT is computed as parents[3] relative to this file's own location (flowgrid, DQN_Agent, Old_Versions, project root), so DQN_Agent must stay a direct child of Old_Versions for this to resolve correctly."],
  ],
  [2600, 6400]
  ),
  p("The reward function (in flowgrid/core/, referenced from the DQN training loop) sums roughly a dozen hand tuned terms (diff wait, absolute wait penalty, spillback penalty, throughput bonus, fairness terms, anti flicker penalty, invalid action penalty). See PROJECT_OVERVIEW.md Section 3 for the exact formula and coefficients, and the book Section 2.3 for why this reward's complexity, and the resulting instability documented in Old_Versions/DQN_Agent/results/comparison_history.json, motivated the move to PPO."),
];

const retraining = [
  h1("8. Retraining or Extending the PPO Agent"),
  p("To train a new version, copy PPO_Agent/scripts/ (and the model files, if building on an existing one) into a new folder under Old_Versions/PPO/ rather than modifying PPO_Agent/ in place. This preserves the current submitted agent as a working reference and follows the same \"copy, don't mutate\" convention used throughout this project's version history (see the archived V4 through V9 folders, each a fresh copy rather than an in place edit of the previous one)."),
  bullet("Copy sumo_rl_env_V8.py to a new file with an updated name; update the sumo_rl_env.py shim's import to point at it."),
  bullet("Copy train_V8.py and evaluate_V8.py; no path edits are needed if the new folder sits at the same depth, since the training step count and other hyperparameters are already command line arguments."),
  bullet("Never resume training an existing checkpoint after changing its reward function or observation definition. Train a fresh agent from random initialization instead."),
];

const newBaseline = [
  h1("9. Adding a New Baseline or Comparison Target"),
  p("New fixed time or rule based baselines can be added by extending AVAILABLE_BASELINES in comparison_core.py; each baseline needs only a name and, for fixed time controllers, a cycle length, since the comparison tools handle result collection and reporting generically through evaluate_models.py's existing \"fixed\" model type. Max Pressure (model type \"mp\" in evaluate_models.py) is not registered in AVAILABLE_BASELINES; it was never successfully integrated as a reliable comparison baseline on this network (see the book, Section 2.6), so it does not appear in the web app or comparison tooling."),
];

const evalSweep = [
  h1("10. Running an Evaluation Sweep"),
  p("final_results_random_seeds.py and checkpoint_sweep.py both support a dry run flag that reports exactly how many simulation runs a given sweep will perform and how long it is expected to take, without executing anything. Always run this first before committing to a long sweep."),
  code("python final_results_random_seeds.py --version-dir .. --dry-run\npython final_results_random_seeds.py --version-dir .."),
  p("Sweeps write partial results incrementally as they progress (assignments.csv is written up front with the full plan; final_results.csv is appended to after every checkpoint completes). If interrupted, resuming with the flag shown below continues exactly where it left off using the original plan; the summarize only flag regenerates summary.txt and the charts from whatever rows already exist, without running anything new."),
  code("python final_results_random_seeds.py --version-dir .. --resume <out_dir>\npython final_results_random_seeds.py --version-dir .. --summarize-only <out_dir>"),
];

const methodology = [
  h1("11. Testing and Verification Methodology"),
  p("This project's evaluation rigor escalated deliberately over its course, and the same escalation is worth reusing for any future work on this codebase rather than trusting an early, less rigorous result:"),
  bullet("A couple of fixed seeds, used throughout early development for fast iteration."),
  bullet("Five, then fifty independently drawn seeds, when a specific comparison needed more statistical confidence."),
  bullet("Every saved checkpoint against its own freshly drawn random seed and scenario (final_results_random_seeds.py), nothing reused, nothing cherry picked, no unfavorable result excluded. This is what let the project report, with real confidence, that the champion agent beats all three fixed time baselines on 53 of 60 independently random evaluations (88.3%)."),
  p("Two properties of the environment make this methodology trustworthy rather than just elaborate: SUMO's seeded vehicle generation is genuinely deterministic (the same seed produces a bit for bit identical vehicle stream regardless of which controller is driving the signal, verified empirically across process restarts), and evaluation episodes now terminate as soon as the road is genuinely empty rather than running to a fixed time limit, which cut typical evaluation time by roughly seven to eight times with no change to the reported results."),
];

const limitations = [
  h1("12. Known Limitations and Future Work"),
  bullet("Single intersection scope: this project controls one intersection; multi intersection coordination is unattempted future work."),
  bullet("High traffic ceiling: performance near the intersection's physical demand capacity reflects queueing physics, not a perception limitation (ruled out directly by a V9 experiment with a richer, non saturating observation encoding, see the book, Section 2.7)."),
  bullet("Training is not reproducible run to run: two independent runs of the identical V8 recipe (V8 and V8_replicate) produced meaningfully different stability profiles. The leading hypothesis is the constant, non decaying entropy coefficient; this is a concrete, addressable item for future work, not a fully solved question."),
  bullet("Computer vision perception (YOLO + DeepSORT), proposed in the original Phase A plan, was not implemented in this delivered scope. See the book, Section 2.3, for the full explanation. It remains the most natural next step for extending this project toward real world deployment."),
  bullet("No formal, rigorous head to head comparison exists between the DQN agent and the fixed time baselines using the same seed verified methodology applied to PPO; Old_Versions/DQN_Agent/results/comparison_history.json contains real evaluation history but was not brought to the same level of statistical rigor."),
];

const conventions = [
  h1("13. Coding Conventions Observed in This Codebase"),
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
  ...flowgridWebWalkthrough,
  ...dqnWalkthrough,
  ...retraining,
  ...newBaseline,
  ...evalSweep,
  ...methodology,
  ...limitations,
  ...conventions,
]);
