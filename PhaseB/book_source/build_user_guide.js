const { p, para, h1, h2, h3, bullet, code, note, warning, simpleTable, coverPage, toc, buildDoc } = require("./build_guides.js");

const intro = [
  h1("1. Introduction"),
  p("FlowGrid is a reinforcement learning based traffic signal controller for a single SUMO simulated intersection. This guide is written for anyone who wants to run the project's tools directly: reviewers checking the delivered agent's claims, future developers picking the project back up, or anyone curious to watch the agent control traffic themselves."),
  p("Two independent agents were built over the course of this project: a Maskable PPO agent (the final, submitted \"champion\" agent, referred to throughout this guide as PPO_Agent) and an earlier Deep Q Network agent (DQN_Agent). Both have their own desktop application and browser dashboard, described separately below. If you only have time to try one thing, start with Section 4, Quick Start."),
  p("This guide covers normal, successful operating flow: installing the software, launching each tool, and reading the results it produces. It intentionally does not cover every error condition; if something does not behave as described here, see Section 8, Troubleshooting."),
];

const requirements = [
  h1("2. System Requirements"),
  p("The project was developed and tested on Windows with the following software installed."),
  simpleTable(
  ["Requirement", "Version / Notes"],
  [
  ["Operating system", "Windows 10/11 (developed and tested here); Linux/macOS should work with SUMO and Python installed, but were not tested"],
  ["Python", "3.10"],
  ["SUMO (Simulation of Urban Mobility)", "1.20 or later, with the SUMO_HOME environment variable set and the TraCI/libsumo Python bindings on the path"],
  ["CPU", "A multi core processor is strongly recommended; training and full evaluation sweeps run ten parallel SUMO instances by default"],
  ["GPU", "Optional. Training uses CUDA if available (torch.device(\"cuda\")); it also runs on CPU, just considerably slower"],
  ["Disk space", "Several hundred MB for the trained models and evaluation results already included in this repository; several GB free if you plan to retrain from scratch"],
  ],
  [3200, 5800]
  ),
  p("Key Python packages (installed via requirements.txt at the project root): FastAPI, uvicorn, gymnasium, numpy, torch, matplotlib, pydantic, PyYAML, and eclipse sumo. In addition, the PPO side of the project requires Stable-Baselines3, sb3-contrib (for MaskablePPO and action masking), sumo-rl, pandas, seaborn, and customtkinter (for the desktop comparison app)."),
];

const installation = [
  h1("3. Installation"),
  h2("3.1 Clone the repository"),
  code("git clone https://github.com/einavbs1/FlowGrid.git\ncd FlowGrid"),
  h2("3.2 Install SUMO"),
  p("Install SUMO from https://sumo.dlr.de/ and make sure the SUMO_HOME environment variable points to your installation folder (e.g. C:\\Program Files (x86)\\Eclipse\\Sumo). This is required before any simulation, training, or evaluation script will run."),
  h2("3.3 Create a Python environment and install dependencies"),
  code("python -m venv venv\nvenv\\Scripts\\activate\npip install -r requirements.txt\npip install stable-baselines3 sb3-contrib sumo-rl pandas seaborn customtkinter"),
  note("No further project specific installation is required. Every script locates the SUMO network and route files it needs via paths defined in the code, relative to the project root."),
];

const quickStart = [
  h1("4. Quick Start"),
  p("The fastest way to see the delivered agent in action is the desktop comparison tool, which lets you pick a traffic scenario and watch the trained PPO agent control the intersection live, side by side with a plain fixed time signal."),
  bullet("Open a terminal in PPO_Agent/scripts."),
  bullet("Run: python comparison_gui.py"),
  bullet("In the window that opens, leave the pre selected champion model and the three fixed time baselines ticked."),
  bullet("Choose \"Manual\" seeds, type in any number (e.g. 42), and select one traffic scenario, e.g. Medium."),
  bullet("Tick \"Watch Live\" and click \"Start Comparison.\""),
  bullet("A real SUMO window opens and plays the simulation live. When it finishes, a results table and bar chart appear in the app comparing total waiting time."),
  p("The rest of this guide covers every part of that flow in more detail, plus the equivalent browser based tool and the original DQN agent's own tools."),
];

const ppoSection = [
  h1("5. Using the PPO Comparison Tool (Current Agent)"),
  p("PPO_Agent is the final, submitted agent (internally called V8). Its comparison tools live in PPO_Agent/scripts and PPO_Agent/scripts/comparison_web, and share one underlying engine (comparison_core.py) so the desktop and browser versions behave identically."),
  h2("5.1 Desktop Application"),
  code("cd PPO_Agent/scripts\npython comparison_gui.py"),
  p("The application window opens directly. It has three main panels: Models, Baselines, and Run Settings, followed by a results area that fills in once a comparison finishes."),
  h2("5.2 Web Application"),
  code("cd PPO_Agent/scripts/comparison_web\npython server.py"),
  p("A local web server starts and a browser tab opens automatically (default: http://127.0.0.1:8000). The page offers the identical set of controls as the desktop app."),
  h2("5.3 Selecting Models to Compare"),
  p("The Models panel lists every trained agent currently registered in comparison_gui_models.json, with the project's champion model (PPO_Agent_V8) pre selected. Tick the checkbox beside any additional model you want included. To compare against a model not yet in the list, use \"Add Model\" and browse to its .zip file (the default browse location is PPO_Agent/models); it is added to the registry immediately and persists for future sessions."),
  h2("5.4 Selecting Baselines"),
  p("The Baselines panel lists the fixed time controllers available for comparison: Fixed_30s, Fixed_45s, and Fixed_60s (cycle length in seconds). Tick any you want included alongside the selected model(s)."),
  h2("5.5 Choosing Seeds and a Traffic Scenario"),
  p("Choose \"Random\" and a count to have that many fresh, never before seen traffic instances generated automatically, or choose \"Manual\" to type in specific seed values one at a time, useful when you want to reproduce a particular result exactly. Then select which traffic condition to test: Low, Medium, High, or all three at once. SUMO's vehicle generation is seeded, so a given seed always produces the identical vehicle stream regardless of which controller is driving the signal, which is what makes the resulting comparison fair."),
  h2("5.6 Watch Live"),
  p("With exactly one seed and one specific scenario selected, tick \"Watch Live\" before starting the comparison. Instead of running entirely in the background, an actual SUMO graphical window opens and plays the episode out in real time, so you can visually confirm what the agent is doing rather than trust the reported numbers alone."),
  h2("5.7 Running the Comparison"),
  p("Click \"Start Comparison.\" A progress indicator tracks how many of the required simulation runs have completed (models x baselines x seeds x scenarios). Runs execute in parallel across multiple CPU cores unless Watch Live is active, in which case they run one at a time so the visualization stays meaningful."),
  h2("5.8 Reading the Results"),
  p("Once complete, a results table appears for each tested scenario, listing every selected model and baseline with its total waiting time for each seed and an overall average. The best performing entry in each table is highlighted, and a bar chart beneath the table gives the same comparison visually. Lower total waiting time is better."),
];

const dqnSection = [
  h1("6. Using the DQN Tools (Original Agent)"),
  p("DQN_Agent is the project's original reinforcement learning approach. It predates PPO_Agent and is preserved with its own, separate desktop app, browser dashboard, and comparison logic. See the book (Section 2.3) for why the project moved from DQN to PPO."),
  h2("6.1 Desktop Application"),
  code("cd DQN_Agent/gui\npython flowgrid_gui.py"),
  p("On Windows, double clicking DQN_Agent/launchers/run_gui.bat launches the same application in its own process, so closing the terminal window does not close the app."),
  h2("6.2 Web Dashboard"),
  code("cd DQN_Agent/web\npython main.py"),
  h2("6.3 The Compare Tab"),
  p("The Compare tab answers a focused question: on the same traffic demand, does the DQN signal policy reduce delay more than fixed time control? To make the comparison fair, both runs use the same vehicles (same count, routes, lanes, and depart times); only the traffic light policy differs. A run has two phases: a fixed time baseline pass (random vehicle injection, then drain), followed by the DQN policy pass replaying the identical vehicle stream. See DQN_Agent/docs/COMPARE.md for the full technical explanation of how this pairing is guaranteed."),
  h2("6.4 Command Line / Menu"),
  code("cd DQN_Agent/scripts\npython run_menu.py"),
  p("An interactive menu over training, evaluation, and comparison, useful for running the DQN agent's tools without a graphical interface."),
];

const scenarios = [
  h1("7. Understanding the Traffic Scenarios"),
  p("Every comparison tool offers the same three traffic conditions, corresponding to different vehicle demand levels feeding the intersection:"),
  simpleTable(
  ["Scenario", "Demand", "What it tests"],
  [
  ["Low", "Light, sparse traffic", "Whether the agent can find a useful signal to act on when very few vehicles are present (an early failure mode of this project, see the book Section 2.6)"],
  ["Medium", "Moderate, steady traffic", "Typical day to day operating conditions"],
  ["High", "Heavy, near saturating traffic", "Behavior as demand approaches the intersection's physical capacity, where every controller's performance converges (see the book Section 2.7)"],
  ],
  [1800, 3400, 3800]
  ),
];

const troubleshooting = [
  h1("8. Troubleshooting / FAQ"),
  h3("\"No model found\" when running evaluate_V8.py or the comparison tools"),
  p("Confirm you are running the script from inside PPO_Agent/scripts (not from PPO_Agent/ or the project root), and that PPO_Agent/models contains at least one ppo_model_*.zip file with a matching vec_normalize_*.pkl."),
  h3("SUMO_HOME is not set / TraCI import errors"),
  p("Every simulation, training, and evaluation script requires SUMO to be installed with the SUMO_HOME environment variable set. See Section 3.2."),
  h3("The comparison tool is very slow"),
  p("Evaluation runs execute multiple SUMO simulations in parallel, bounded by CPU core count. Reducing the number of seeds, or running fewer scenarios at once, will reduce total wait time. \"Watch Live\" mode is inherently slower since it runs at a visible, non accelerated pace."),
  h3("I changed the reward function or observation and now training behaves strangely"),
  p("Never resume training from an existing checkpoint after changing the reward function or observation definition. Train a fresh agent from random initialization instead. This project encountered a full, unrecoverable policy collapse from doing exactly this once (see the book, Section 2.6); it is documented there as a cautionary example, not a theoretical risk."),
  h3("Where do I find the raw evaluation numbers behind the book's claims?"),
  p("PPO_Agent/results/final_random_seeds_20260705_005802/ contains the full, unfiltered evaluation (summary.txt, final_results.csv) behind the 88.3% win rate figure reported in the book. DQN_Agent/results/comparison_history.json contains the equivalent raw evaluation history for the DQN agent, discussed in the book's Section 2.3."),
];

const glossary = [
  h1("9. Glossary"),
  simpleTable(
  ["Term", "Meaning"],
  [
  ["Baseline", "A non learned controller (fixed time cycle) the trained agent is compared against"],
  ["Checkpoint", "A saved copy of the agent's weights at a specific point during training"],
  ["Episode", "One complete simulated run of a traffic scenario, from an empty road to a defined end condition"],
  ["MaskablePPO", "The specific reinforcement learning algorithm used by PPO_Agent; standard PPO extended with action masking"],
  ["Seed", "A number that deterministically fixes SUMO's randomly generated vehicle stream, so a given seed always produces the identical traffic"],
  ["SUMO", "Simulation of Urban Mobility, the open source traffic simulator this project's environment is built on"],
  ["TraCI", "SUMO's Traffic Control Interface, the Python API used to step the simulation and read/control the traffic light"],
  ["Vecnormalize", "Stable-Baselines3's running statistics for normalizing observations; must be loaded alongside a model checkpoint to reproduce its trained behavior correctly"],
  ["Watch Live", "A comparison tool option that opens a real, visible SUMO simulation window instead of running in the background"],
  ],
  [2600, 6400]
  ),
];

buildDoc("User_Guide.docx", [
  ...coverPage("User Guide", "How to install and run the FlowGrid comparison tools"),
  ...toc(),
  ...intro,
  ...requirements,
  ...installation,
  ...quickStart,
  ...ppoSection,
  ...dqnSection,
  ...scenarios,
  ...troubleshooting,
  ...glossary,
]);
