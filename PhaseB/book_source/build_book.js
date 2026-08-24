const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageBreak, TableOfContents, Header, Footer, PageNumber, ImageRun,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, convertInchesToTwip
} = require("docx");

// __dirname = PhaseB/book_source/; project root is two levels up.
const PROJECT_ROOT = path.join(__dirname, "..", "..");

const FONT = "Calibri";
const SIZE = 24; // 12pt in half points

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 140, line: 252 },
    children: [new TextRun({ text, font: FONT, size: SIZE, ...opts })],
    ...opts.paragraphOpts,
  });
}

function para(children, paragraphOpts = {}) {
  return new Paragraph({ spacing: { after: 140, line: 252 }, children, ...paragraphOpts });
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 260, after: 130 }, children: [new TextRun({ text, font: FONT })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 }, children: [new TextRun({ text, font: FONT })] });
}
function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 100 }, children: [new TextRun({ text, font: FONT, italics: true })] });
}
function bullet(text) {
  return new Paragraph({
    spacing: { after: 90, line: 252 },
    bullet: { level: 0 },
    children: [new TextRun({ text, font: FONT, size: SIZE })],
  });
}
function placeholder(text) {
  return new Paragraph({
    spacing: { after: 140, line: 252 },
    shading: { type: ShadingType.CLEAR, fill: "FFF3CD" },
    children: [new TextRun({ text: "[" + text + "]", font: FONT, size: SIZE, bold: true, color: "8A6D3B" })],
  });
}
function code(text) {
  return new Paragraph({
    spacing: { before: 80, after: 140 },
    shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
    children: [new TextRun({ text, font: "Consolas", size: 20 })],
  });
}
function note(text) {
  return new Paragraph({
    spacing: { before: 80, after: 140 },
    shading: { type: ShadingType.CLEAR, fill: "E8F0FE" },
    children: [new TextRun({ text: "Note: " + text, font: FONT, size: SIZE, italics: true, color: "1F2D3D" })],
  });
}
function warning(text) {
  return new Paragraph({
    spacing: { before: 80, after: 140 },
    shading: { type: ShadingType.CLEAR, fill: "F5F5F5" },
    children: [
      new TextRun({ text: "Pay attention: ", font: FONT, size: SIZE, bold: true }),
      new TextRun({ text: text, font: FONT, size: SIZE }),
    ],
  });
}

function simpleTable(headerRow, rows, colWidths) {
  const totalWidth = 9000;
  const widths = colWidths || headerRow.map(() => Math.floor(totalWidth / headerRow.length));
  const mkCell = (text, bold) => new TableCell({
    width: { size: widths[0], type: WidthType.DXA },
    shading: bold ? { type: ShadingType.CLEAR, fill: "1F2D3D" } : undefined,
    children: [new Paragraph({ children: [new TextRun({ text: String(text), font: FONT, size: 20, bold, color: bold ? "FFFFFF" : "000000" })] })],
  });
  const header = new TableRow({
    tableHeader: true,
    children: headerRow.map((t, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: "1F2D3D" },
      children: [new Paragraph({ children: [new TextRun({ text: t, font: FONT, size: 20, bold: true, color: "FFFFFF" })] })],
    })),
  });
  const body = rows.map(r => new TableRow({
    children: r.map((t, i) => new TableCell({
      width: { size: widths[i], type: WidthType.DXA },
      children: [new Paragraph({ children: [new TextRun({ text: String(t), font: FONT, size: 20 })] })],
    })),
  }));
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: widths,
    rows: [header, ...body],
  });
}

const logoBuffer = fs.readFileSync(path.join(PROJECT_ROOT, "LOGO1.png"));

//                                                                            
// COVER PAGE
//                                                                            
const coverPage = [
  new Paragraph({ spacing: { before: 600, after: 400 }, alignment: AlignmentType.CENTER,
    children: [ new ImageRun({ type: "png", data: logoBuffer, transformation: { width: 342, height: 135 } }) ] }),
  new Paragraph({ spacing: { before: 800, after: 100 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Capstone Project, Phase B", font: FONT, size: 32, bold: true })] }),
  new Paragraph({ spacing: { before: 200, after: 600 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "FlowGrid: Adaptive Traffic Signal Control Using Reinforcement Learning", font: FONT, size: 40, bold: true, color: "1F2D3D" })] }),
  new Paragraph({ spacing: { before: 600, after: 100 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Team Code: ", font: FONT, size: SIZE, bold: true }), new TextRun({ text: "26-1-D-30", font: FONT, size: SIZE, bold: true, color: "1F2D3D" })] }),
  new Paragraph({ spacing: { after: 100 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Students: ", font: FONT, size: SIZE, bold: true }), new TextRun({ text: "Avishag Levi, Einav Momi Ben Shushan", font: FONT, size: SIZE, bold: true, color: "1F2D3D" })] }),
  new Paragraph({ spacing: { after: 100 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Advisor: ", font: FONT, size: SIZE, bold: true }), new TextRun({ text: "Dr. Cohen Reuven", font: FONT, size: SIZE, bold: true, color: "1F2D3D" })] }),
  new Paragraph({ spacing: { before: 400, after: 100 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Git Repository: ", font: FONT, size: 20 }), new TextRun({ text: "https://github.com/einavbs1/FlowGrid", font: FONT, size: 20, color: "1F2D3D" })] }),
  new Paragraph({ spacing: { after: 100 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Demo Video: ", font: FONT, size: 20 }), new TextRun({ text: "https://drive.google.com/file/d/1BE3oeGWWbVrQEC_ZL0rVh5AdPs9kDNTY/view", font: FONT, size: 20, color: "1F2D3D" })] }),
  new Paragraph({ children: [new PageBreak()] }),
];

//                                                                            
// TABLE OF CONTENTS
//                                                                            
const toc = [
  h1("Table of Contents"),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1 2" }),
  new Paragraph({ children: [new PageBreak()] }),
];

//
// CHAPTER 1, INTRODUCTION
//
const chapter1 = [
  h1("1. Introduction"),
  h2("1.1 The Problem"),
  p("Most traffic signals in use today run a fixed cycle of green, yellow, and red, timed once by an engineer and rarely revised. A fixed schedule works while demand stays near the historical averages it was derived from. Real demand does not. It rises during peak hours, falls overnight, and responds to accidents, weather, and events a fixed timer cannot detect. The result is a controller that gives green time to an empty approach while a congested one waits, because it cannot tell them apart."),
  p("Adaptive controllers close part of that gap. Vehicle actuated control improved on fixed timing with inductive loop detectors, extending or ending a phase according to whether a vehicle is present. These systems rely on binary presence detection rather than any measure of volume, and they see only a short distance past the stop line, so they cannot tell how long a queue has grown. More importantly, none of them learn. Their logic is fixed in advance by an engineer, and only the inputs change."),
  h2("1.2 Research Questions"),
  p("This project asks three questions:"),
  bullet("Can a controller given no explicit switching rule, learning only from repeated simulated experience, outperform the fixed time signals already in use?"),
  bullet("Under which traffic conditions does it succeed, where does it fall short, and what explains the difference?"),
  bullet("How much confidence can we place in that answer, given that a reinforcement learning agent can raise its own reward score without helping an actual driver?"),
  h2("1.3 Our Solution"),
  p("This project aims to build a reinforcement learning agent that controls a single traffic signal intersection more effectively than the standard alternatives already in use, and to evaluate it rigorously. More effectively means a lower total vehicle waiting time across light, moderate, and heavy traffic."),
  p("The final system, called FlowGrid, includes three sub systems."),
  p("The first is a SUMO based simulation environment modeling a four way intersection with randomly generated vehicle demand, a camera with a limited sensing range (the agent sees only 150 meters back from the stop line, which represents what a roadside sensor could plausibly observe), and a set of hard safety constraints, including minimum and maximum green durations and mandatory yellow transitions, that cannot be violated."),
  p("The second is the trained agent: a Proximal Policy Optimization (PPO) policy agent, trained from scratch with no predefined switching rules, that decides every five simulated seconds whether to hold the current phase or advance to the next."),
  p("The third is an evaluation and demonstration layer, including two applications, a family of statistical comparison tools, and a Watch Live mode that opens a real SUMO visualization window, so that the agent\'s performance can be interactively checked and questioned."),
  h2("1.4 How We Tested It, and Against What"),
  p("Every method in this project is compared against fixed time control, the approach already deployed at most intersections, using three cycle lengths of 30, 45, and 60 seconds as three separate baselines. We also wanted to include Max Pressure, a more principled adaptive controller from the traffic engineering literature, but integrating it reliably would have taken more development time than we had, so we did not pursue it."),
  p("Every comparison runs in the same traffic. SUMO\'s vehicle generation is seeded, so a given seed produces an identical stream of vehicles whichever controller drives the signal. Any difference in the result therefore comes from the controller, not from one run getting easier traffic. We tested all three demand levels, and the final method evaluates every saved checkpoint against its own seed and scenario, reporting every result rather than a selected best."),
  h2("1.5 Who This Book Is For"),
  p("The intended stakeholders fall into two groups. For traffic engineers or municipal decision makers, what matters is the evaluation results: does the method outperform what is already in use, under which conditions, and with how much confidence. The second group is researchers who wish to continue this work, for whom what matters is the version history, the attempts that failed, and the explanations."),
];

//
// CHAPTER 2, BACKGROUND, TOOLS AND METHODS
//
const chapter2 = [
  h1("2. Background, Tools and Methods"),
  h2("2.1 Related Work"),
  p("Traffic signal control has evolved through several generations. Fixed time control is still the most common. It runs a rigid schedule derived from historical traffic counts (Koonce et al., 2008), blind to current conditions. Vehicle actuated control improved on this with inductive loop detectors, extending or ending a phase according to whether a vehicle is present. The problem is that these systems rely on binary presence detection rather than any measure of volume, so a single vehicle on a minor approach can interrupt a heavy flow on a main road (Akçelik, 1994)."),
  p("A further generation moved beyond a single intersection\'s local logic. SCOOT models platoons using upstream detectors and continuously adjusts split, cycle, and offset to maintain a coordinated green wave along a corridor (UK Department of Transport, 1995). SCATS instead pursues equisaturation, measuring a Degree of Saturation at the stop line and reallocating green time to balance competing approaches (Akçelik, 2010). Both methods are genuinely adaptive and widely deployed. But their logic is fixed, and they are merely responsive to live inputs."),
  p("A more modern line of research looks past physical signals altogether. Dresner and Stone (2008) proposed a reservation based Autonomous Intersection Management protocol, in which vehicles negotiate directly with an intersection manager and pass through without stopping. Liang et al. (2018) demonstrated a Vehicle to Infrastructure architecture, where vehicles broadcast their position and intent to roadside equipment, feeding a high resolution grid into a Double Dueling Deep Q Network. Both methods depend on a level of connected vehicle network penetration that does not exist yet."),
  p("The original design was built on three methods:"),
  bullet("YOLO, short for You Only Look Once (Redmon et al., 2016), is an object detection algorithm. Given a single camera frame it draws a box around every object it finds and labels what each one is, in one pass over the whole image rather than by scanning many candidate regions in turn, which is what makes it efficient for live video. Its role in the design was to recognize the vehicles on each approach from the camera feed, producing a count of how many wait in each lane group, one of the two inputs the controller acts on."),
  bullet("DeepSORT (Wojke et al., 2017) is a tracking algorithm that runs on top of a frame detector such as YOLO. A frame detector treats every frame independently, so it can only report which cars are present in one frame. DeepSORT links detections across frames into continuous tracks, predicting where each vehicle should appear next and matching it by appearance, so a vehicle keeps its identity even when a truck briefly hides it. Its role was to give each vehicle a persistent identity, which is what makes it possible to measure how long one particular car has waited. That per vehicle waiting time is the starvation signal our observation and reward are built on (Section 3.3), and detection alone cannot produce it."),
  bullet("A Deep Q Network, or DQN (Mnih et al., 2015), is a reinforcement learning algorithm. It uses a neural network to estimate the future value of each action available in a situation, then acts by choosing the highest valued one, refining those estimates by replaying its own stored experience. The Double Dueling variant used by Liang et al. adds two refinements that correct a known tendency of the original to overestimate those values. Its role was the decision itself, choosing every few seconds whether to hold the current phase or advance. This is the one part of the pipeline we did build, although Section 4.3 explains why we later replaced it."),
  p("Our original proposal aimed to use a camera as a sensor approach, combining these three methods into a full pipeline retrofitted onto existing intersections. Wang et al. (2024) validated a closely related framework, confirming this remains an active research direction."),
  p("This is also why our agent observes only 150 meters back from the stop line. The observation was shaped to match what a roadside camera could plausibly deliver, so the same trained policy could later be driven by a real perception pipeline. As Chapter 4 explains, the vision layer was not implemented, and it remains the natural next step."),
  h2("2.2 Why Reinforcement Learning Fits This Problem"),
  p("The problem maps onto the reinforcement learning formalism directly. An agent, here the signal controller, observes a state describing current demand at each approach, chooses an action, and receives a reward telling it whether that decision improved conditions. This repeats across thousands of simulated episodes. Three properties make it hard. The right reward is not obvious, since minimizing waiting time, maximizing throughput, and keeping approaches fair are not the same objective. The environment is only partially observable, because a roadside sensor cannot see indefinitely far upstream. And an agent can raise its reward through behavior that satisfies the reward definition but does nothing for road users, which this project encountered repeatedly."),
  p("We therefore built a dedicated single intersection environment in SUMO (Simulation of Urban Mobility) to isolate these issues before considering a larger network. Reward design, partial observability, the exploration and exploitation trade off, and the risk of reward exploitation are all present at a single four phase intersection, and are easier to diagnose there."),
  h2("2.3 Tools and Technologies Used"),
  p("The simulation runs on SUMO, accessed from Python through the sumo-rl and TraCI/libsumo interfaces. Training uses Stable-Baselines3 with its sb3-contrib extension, which provides the maskable variant of PPO, over vectorized parallel environments running ten SUMO instances at once. Evaluation and analysis use pandas, matplotlib, and seaborn. The interactive tooling differs by agent. The PPO agent uses a FastAPI application with a hand written HTML, CSS, and JavaScript front end that includes a guided tour. The DQN agent keeps a Tkinter desktop application. FlowGrid_Web, described in Section 3.7, is a React and Vite front end over its own FastAPI backend. All were kept dependency light rather than built on a larger framework."),
];

//
// CHAPTER 3, THE DELIVERED SYSTEM
//
const chapter3 = [
  h1("3. The Delivered System"),
  p("This chapter presents the algorithms and methodology behind the agent. The software that implements them is documented in the Developer and Maintenance Guide (Appendix B)."),
  h2("3.1 System Architecture"),
  p("FlowGrid is a closed loop training system. A simulated intersection advances in fixed time steps, the agent chooses a control action at each step, and the resulting change in traffic state becomes a reward that updates the policy. Training repeats this loop for several million steps. The components below exist to run that loop correctly and fast enough to be practical."),
  p("The architecture has three layers: the simulator that models traffic, a translation layer that converts raw simulator state into a learnable representation, and the learning algorithm. The agent never talks to the simulator directly. Every observation it receives and every action it issues passes through the middle layer. That separation is what made the sequence of reward and observation experiments in Section 4.4 practical, since each one changed a single layer without disturbing the others."),
  p("Figure 3.1 shows these layers as a UML component diagram. Every component named in it is a real class or module in the delivered code."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_framework_diagram.png")), transformation: { width: 570, height: 292 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 3.1: The training and simulation architecture.", { italics: true, size: 20 }),
  p("Working from the bottom of the diagram upward:"),
  bullet("Simulation layer. Eclipse SUMO models the road network, vehicle dynamics, car following, and queue formation, and holds the ground truth state: where every vehicle is and how long it has waited. We drive it through TraCI, SUMO\'s remote control interface, which lets an external process read state and set the signal phase while the simulation runs. One configuration choice matters: SUMO by default removes vehicles that have been stationary for an implausibly long time, and we disabled it, because it let an early version of the agent exploit the reward function (Section 7.1)."),
  bullet("Translation layer. The SwitchOrKeepWrapper sits between the simulator, which deals in individual vehicles on individual lanes, and the learning algorithm, which needs a fixed length observation vector and a discrete action. It does three things. It builds the 21 element observation described in Section 3.3, subject to the 150 meter sensing limit. It enforces the constraints the policy may not override: a minimum green of 10 seconds, a maximum of 60, a mandatory 3 second yellow on every phase change, and an action mask that removes Switch when no vehicle is present. And it computes the reward. Almost every version in Section 4.4 was a change confined to this layer."),
  bullet("Parallel environment execution. Training time is bound by how fast experience can be generated, and one simulation produces it slowly. SubprocVecEnv, a standard Stable-Baselines3 component, runs ten SUMO instances in separate processes, each with independently generated demand, and merges their experience into one training stream. This brings a six million step run down from days to hours."),
  bullet("Observation normalization. The 21 observation elements sit on very different numeric ranges, and gradient based training degrades when one input is far larger than the rest. VecNormalize tracks a running mean and variance for each element and rescales incoming observations against them, clipping to bound outliers. We normalize observations but not rewards, since the reward is already a bounded physical quantity. These statistics are part of the trained model, not a side file: a checkpoint restored without them receives inputs on the wrong scale and behaves incorrectly, which is why every checkpoint is saved together with its own copy."),
  bullet("Policy optimization. The MaskablePPO agent holds the policy, a multilayer perceptron with two hidden layers of 128 units for the policy head and two for the value head. Action masking is the important property. At each decision the translation layer supplies the set of legal actions, and illegal ones are removed from the policy distribution before sampling rather than rejected afterwards. Section 3.4 explains why that mattered."),
  p("A single decision step runs as follows. The simulation advances five simulated seconds. The translation layer reads the resulting state through TraCI, builds the 21 observation elements, computes the reward earned by the previous action, and determines the current action mask. The observation is normalized. The policy chooses Keep or Switch. The translation layer converts that choice into signal commands, inserting the yellow interval on a phase change. The cycle repeats. Training runs this loop across ten parallel environments until the step budget is spent. Evaluation is the same loop with policy updates disabled, driven by the tooling in Section 3.6."),
  h2("3.2 The Decision Problem, Formally"),
  p("Every reinforcement learning problem reduces to a Markov Decision Process: a state the agent observes, an action it chooses, a reward it receives, and rules governing how the state evolves. Framing the problem this way early forced explicit answers to questions that are easy to leave vague."),
  p("Figure 3.2 shows that loop as our code implements it, inside the SwitchOrKeepWrapper. Its numbered steps map directly onto the state, action, and reward definitions in Section 3.3."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "mdp_loop_diagram.png")), transformation: { width: 450, height: 359 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 3.2: The Markov Decision Process loop.", { italics: true, size: 20 }),
  h2("3.3 State, Action, and Reward"),
  p("The state is a 21 element vector, normalized to the range 0 to 1: a one hot encoding of which of the four phases is green, how long it has held green as a fraction of its maximum, an occupancy density for each of eight lane groups, and a starvation score per lane group giving how long that group\'s longest waiting vehicle has sat there. The starvation term matters because an intersection can show a reasonable average wait while one vehicle in a rarely served lane waits far longer than anyone would accept. It exists so the agent cannot ignore that vehicle when the aggregate looks fine."),
  p("The action space is deliberately small: hold the current phase, or switch to the next in a fixed cyclic order. We do not allow jumps to an arbitrary phase. Early experiments (Chapter 7) showed that a free jump action space encourages rapid cycling through yellow transitions, and a cyclic structure removes that failure mode by construction. The hard constraints listed in Section 3.1 sit on top of this action space and are enforced outside the policy."),
  p("The reward is simple: the reduction in total system wide waiting time between one decision and the next, measured directly from the simulator, minus a small penalty tied to the worst starvation score. Simplicity was a hard won lesson rather than a starting assumption. An earlier reward (Chapter 7) used a dozen hand tuned terms, and it became almost impossible to tell which one drove a given behavior. Tying the reward to the same quantity the project is judged on made training and debugging far easier."),
  h2("3.4 Why MaskablePPO"),
  p("We trained the final agent with MaskablePPO, an extension of Proximal Policy Optimization that understands action masking. When an action is structurally disallowed, such as switching an empty intersection, its probability is removed from the policy distribution rather than blocked after the fact. We considered Deep Q Networks instead, and an earlier DQN implementation exists in the codebase (Section 4.3). PPO\'s clipped updates and its early stopping on excessive KL divergence gave us two independent guards against the abrupt policy collapse that had already cost us time (Section 7.2). Those guards mattered more in practice than any efficiency argument either way."),
  h2("3.5 The Decision Loop in Operation"),
  p("Figure 3.3 traces the decision loop as it runs today, as a UML activity diagram. Every box corresponds to a real step in sumo_rl_env_V8.py. Two things are worth noting. The hard action mask, the step that removes Switch, is the structural constraint from Section 3.3 rather than a penalty applied afterwards. And there is no YOLO detection, DeepSORT tracking, Priority Protocol, or Fallback Mode anywhere in the loop, because none of those were built (Chapter 4)."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_decision_loop_diagram.png")), transformation: { width: 450, height: 345 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 3.3: Activity diagram of the decision loop.", { italics: true, size: 20 }),
  h2("3.6 The Comparison Application"),
  p("The comparison application makes every claim in Chapter 5 independently checkable. It lets anyone pick a trained model, the baselines to measure it against, a traffic scenario, and one or more seeds, then run the comparison in a browser. Its Watch Live mode opens a real SUMO window so the agent\'s behavior can be watched rather than inferred from a number."),
  p("The application is built to be approachable to new users. It opens with a floating, step by step guided tour that highlights each field in turn, for example which models to compare, which baselines to use, how seeds and scenarios work, and what Watch Live does. It starts automatically on every visit and can be reopened from a Guide button in the header. We treat this as part of the deliverable, since a comparison tool nobody can operate produces no results."),
  p("Figure 3.4 shows what Watch Live opens: SUMO\'s own graphical window, the same view a reviewer sees during a demonstration. The intersection geometry and the vehicles in yellow are real, and the red and green bars on each approach are the current signal phase."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "poster_sumo_preview.png")), transformation: { width: 570, height: 270 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 3.4: The SUMO window during a Watch Live session.", { italics: true, size: 20 }),
  p("Figure 3.5 shows the application at the end of a run, comparing PPO_Agent_V8 against the Fixed_45s baseline in medium traffic on seed 732846, with the results table and bar chart it produces. This is a real screenshot, not a mockup."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "webapp_screenshot.png")), transformation: { width: 530, height: 405 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 3.5: The comparison web application, mid comparison.", { italics: true, size: 20 }),
  h2("3.7 FlowGrid_Web, the Operations Dashboard"),
  p("This phase also delivered FlowGrid_Web, an independent SaaS style traffic operations dashboard with its own backend, multi junction navigation, login, device settings, reports, and user management. It shows what a fully deployed version of this system could look like to a traffic authority operator. Every screen is a real, working interface, but for every junction except one the data behind it is simulated. The exception is deliberate: Live Junction (SUMO Simulation) is wired to the same trained PPO agent and simulator used throughout this book, with a Run Agent control that launches a real SUMO episode and streams back live per direction queue counts, signal colors, and a snapshot from the running window, the same simulation shown in Figure 3.4."),
  p("Figure 3.6 reproduces the Use Case Diagram from our Phase A proposal, unchanged. FlowGrid_Web implements all eight use cases as real, clickable screens. What separates it from a deployed system is the data behind those screens, which is real and live only for View Junction Data on the Live Junction and simulated everywhere else, including Log In, which accepts two fixed demonstration accounts rather than a real authentication server."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "phaseA_usecase_diagram.png")), transformation: { width: 490, height: 362 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 3.6: Use Case Diagram from the Phase A proposal.", { italics: true, size: 20 }),
  p("A recorded video walkthrough of the system, including a live Watch Live session and the comparison app end to end, is available at https://drive.google.com/file/d/1BE3oeGWWbVrQEC_ZL0rVh5AdPs9kDNTY/view."),
];

//
// CHAPTER 4, DEVELOPMENT PROCESS AND DECISION MAKING
//
const chapter4 = [
  h1("4. Development Process and Decision Making"),
  h2("4.1 From the Original Plan to What We Actually Built"),
  p("The delivered system differs substantially from the Phase A proposal. The proposal described a full perception to decision pipeline: YOLO for vehicle detection and classification, DeepSORT for tracking across occlusion, a DQN agent for phase selection, a Priority Protocol giving emergency vehicles zero delay, a Rule Based Safety Layer with a Historical Data Fallback Mode, and a cloud hosted dashboard on FastAPI and PostgreSQL. Its success criteria were equally broad: at least 20% less average waiting time, at least 15% less maximum queue length, detection accuracy above 90% and above 95% for emergency vehicles, latency under 100 milliseconds, and zero delay emergency preemption in all test cases."),
  p("Figure 4.1 reproduces the Deployment Diagram from that proposal, relabelled only to say Trained PPO Model in place of Trained DQN Model. We show it because it was not implemented. None of the cloud infrastructure, the edge device, the IP camera, or the controller integration in it exists in the delivered system. What we built instead is the pipeline in Figure 3.1."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "phaseB_deployment_diagram.png")), transformation: { width: 470, height: 442 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 4.1: Deployment Diagram from the Phase A proposal, not implemented.", { italics: true, size: 20 }),
  p("The delivered scope is narrower, and in the one dimension we chose to go deep on, verified far more rigorously than the proposal required: a single intersection control policy, trained and evaluated on the simulator\'s ground truth vehicle state rather than a vision estimate, with no priority protocol, no fallback mode, and no cloud infrastructure. The vision layer, the emergency preemption logic, and the hosted deployment were not built."),
  h2("4.2 Why the Scope Narrowed"),
  p("Two factors explain this. The first was a deliberate research decision. Deciding which phase should be green and for how long is already a substantial problem on its own, as the version history in Section 4.4 shows. Combining it with an unsolved detection and tracking problem would have made it much harder to tell whether a poor result came from perception or from decision making. Isolating the control problem, with ground truth state standing in for perfect perception, let us study it on its own."),
  p("The second factor was circumstantial. During the project both team members were called up for military reserves, which is compulsory once summoned and cannot be deferred, removing a significant and unpredictable block of development time without notice. Faced with a real reduction in available time, we chose to protect the depth of the reinforcement learning work already underway rather than spread the remaining time across perception, tracking, priority logic, and cloud infrastructure and finish none of them to a demonstrable standard. We see the work as two phases of the same project: the decision making component, which we completed and evaluated rigorously, and the simulation to reality deployment layer, which remains the next phase rather than an abandoned attempt."),
  h2("4.3 Changing the Algorithm, DQN to PPO"),
  p("We also changed which reinforcement learning algorithm served as the primary approach. An earlier DQN implementation exists in the codebase, working on the same ground truth state rather than vision input, with its own environment, a much more complex multi term reward, and its own training pipeline."),
  p("We evaluated the DQN implementation against a fixed time baseline many times during its development, and the full log survives in the project data files. The log shows not simply that DQN was worse than PPO, but that its result varied too much between runs to be trusted. Thirty four logged runs exist, excluding a thirty fifth synthetic sanity check, all on the same fixed seed and spanning three intersection configurations over roughly three weeks. Improvement over the baseline ranges from effectively eliminating waiting time, at 99.6% better, to producing roughly 1,380 times more total waiting time than doing nothing, about negative 137,858%. The median run, at 34.8% better, looks respectable on its own. The mean is negative 4,046%, pulled there by a few catastrophic outliers. A metric whose mean and median disagree this violently does not describe a dependable controller."),
  p("Figure 4.2 plots every logged evaluation in chronological order. Each dot is one real test at a different point in development, and the vertical axis is percent improvement over the fixed timer, on a log scale so the good and the extremely bad results fit on one chart. Blue beat the baseline, red did worse, and gray was logged with exactly zero waiting time, which we treat as a failed run rather than a perfect result. Good results and severe failures sit side by side throughout, the opposite of the steady pattern the PPO charts show in Chapter 5."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "dqn_inconsistency_chart.png")), transformation: { width: 570, height: 285 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 4.2: DQN evaluations against the fixed time baseline, in chronological order.", { italics: true, size: 20 }),
  p("By count rather than by extreme value, 23 of the 34 runs beat the baseline, 4 did worse, and 7 were logged with exactly zero waiting time. The worst case, at negative 137,858%, matches that run\'s own log recording 411 vehicles still stuck on the map at the time limit, which is genuine gridlock rather than a numerical artifact. We treat the seven zero waiting time entries as failed evaluations, not successes. No run was excluded from the chart or from these totals."),
  p("This was not a controller we could put in charge of an intersection. The failure mode recurred: individual approaches were starved almost entirely in favor of others, with nothing in the agent\'s own logic to recover, despite more than a dozen hand tuned reward terms meant to prevent exactly that. PPO\'s clipped updates proved much more resistant to the abrupt policy collapse we hit elsewhere (Chapter 7), and its action masking let us rule out unsafe behavior structurally rather than penalize it. The DQN implementation remains in the repository in full."),
  h2("4.4 The Version History"),
  p("Development did not run in a straight line, and the actual sequence of iterations is reported here rather than smoothed over. Each version below is a training run started from random initialization rather than a continuation of the one before it, because changing the reward or observation definition partway through training and then resuming from a checkpoint corrupted the policy instead of improving it."),
  simpleTable(
    ["Version", "Core idea tried", "Outcome"],
    [
      ["V1 – V3", "Cyclic phases, reward tied to raw waiting time", "Agent exploited SUMO's vehicle teleportation feature to make waiting time vanish without serving anyone"],
      ["V4 (Acyclic)", "Let the agent jump to any phase directly", "Excessive switching wasted enormous time in mandatory yellow transitions"],
      ["V5", "Pressure style reward with an uncapped exponential starvation penalty", "Extreme penalty values exploded training gradients"],
      ["V6 (capped)", "Same idea, penalty capped", "More stable, but still worse than a fixed time controller overall"],
      ["V3.1 – V3.3", "Reverted to cyclic phases. Dynamic minimum green rule added, then extended", "V3.3 fully collapsed: a broken dynamic green guard was reinforced over two million additional steps until it became the agent's entire strategy"],
      ["V4 (fresh)", "Reward tied directly to the change in total waiting time", "First version to beat any baseline at all, but still lost badly in light traffic"],
      ["V6 (camera) / V7", "Added a starvation penalty and a distance limited \"camera\" observation", "Fixed the light traffic case. Introduced and then fixed a heavy traffic regression as camera range was tuned"],
      ["V8, champion", "Replaced a soft idle switching penalty with a hard rule: switching is structurally blocked at an empty intersection", "First agent to beat all three fixed time baselines across all three traffic conditions"],
      ["V9", "Tested whether a richer, less saturating observation would fix the remaining heavy traffic gap", "It did not, the gap turned out to be a demand ceiling, not a perception problem (Section 5.3)"],
    ],
    [1800, 4200, 3000]
  ),
  p("The project version history document records what changed between versions and why. The table above is the condensed form."),
  h2("4.5 How We Worked"),
  p("The project was steered through frequent review sessions in which we demonstrated the agent live rather than describing it in a written status report. This is the main reason the graphical comparison tools exist: picking a model, a scenario, and a seed, including one supplied on the spot, then watching the result immediately, demonstrates progress far better than a table of figures."),
  p("Once V8 beat every baseline, the emphasis shifted from improving performance to establishing how confidently that performance could be claimed. Chapter 6 documents the evaluation process that followed."),
];

//
// CHAPTER 5, RESULTS
//
const chapter5 = [
  h1("5. Results"),
  h2("5.1 The Headline Result"),
  p("The project\'s central goal, an agent that beats fixed time control across light, moderate, and heavy traffic, was achieved and independently verified. Our champion agent reduces total waiting time by roughly 50% in light traffic, 36% in moderate traffic, and 8% in heavy traffic, each measured against the best fixed time baseline for that condition. Under the most rigorous test we ran, described in Chapter 6, it beat all three baselines in 53 of 60 cases, or 88.3%. Its remaining losses were narrow single digit misses against the toughest baseline in light traffic, not broad failures."),
  h2("5.2 The Evidence"),
  p("The three figures below show that evidence directly. In each, our agent is measured against ordinary fixed timer signals, and lower means less waiting time, so a line below the fixed timer lines means our agent is winning."),
  p("Figure 5.1 plots total waiting time at every checkpoint of our champion agent against the three baselines, with one independently drawn seed and scenario per checkpoint. The axis uses a log scale only so light and heavy traffic can share one chart. The agent starts roughly level with the fixed timers, drops sharply within the first few hundred thousand steps, then stays below all three for the rest of training, in light, moderate, and heavy traffic alike, shown as solid, dashed, and dotted lines."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_checkpoint_waittime_scatter.png")), transformation: { width: 570, height: 285 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 5.1: Total waiting time per checkpoint, against three fixed time baselines.", { italics: true, size: 20 }),
  p("Figure 5.2 reduces those 60 checkpoints to one number each, percent improvement over the Fixed_60s baseline, split by traffic condition. A dot above the zero line means the agent won at that point in training, below means it lost. Apart from two checkpoints in the first half million steps, nearly every dot sits above the line. This is the direct evidence behind the 88.3% win rate, and the contrast with Figure 4.2, where losing results keep reappearing, is deliberate."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_win_rate_scatter.png")), transformation: { width: 570, height: 244 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 5.2: Percent improvement per checkpoint over the Fixed_60s baseline.", { italics: true, size: 20 }),
  p("Figure 5.3 repeats the comparison for moderate traffic alone on an ordinary axis, which shows the shape of the improvement more directly than a log scale. The agent line starts far above the fixed timers, then falls sharply and settles below all of them for the rest of training."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_medium_scenario_progress.png")), transformation: { width: 555, height: 285 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 5.3: Moderate traffic only, on a linear axis.", { italics: true, size: 20 }),
  h2("5.3 Investigating the Heavy Traffic Gap"),
  p("We investigated the remaining gap in heavy traffic rather than leaving it unexplained. Our hypothesis was that the sensing limit saturates the observation under heavy demand, with every input near its maximum and the policy unable to tell one congested state from another. We tested this directly by training an otherwise identical agent with a richer, non saturating encoding of the same information. It performed identically, checkpoint for checkpoint. We conclude the gap is a demand ceiling, queueing behavior as arrivals approach the physical capacity of the intersection, not a perception limit. Closing it further would require coordinating with neighboring intersections."),
  h2("5.4 Does Training Longer Help?"),
  p("A second, unplanned result concerns training length. Training longer does not reliably help. An agent trained from scratch for twice the original step budget scored 77.4% under the same evaluation, against 88.3% for the original champion, despite twice the experience. The checkpoint history shows why. Even at 99% of the schedule, individual checkpoints sat between much better neighbors ten thousand steps away, which points to a fixed, non decaying exploration coefficient still disturbing the policy rather than to a shortage of training time. A second collapse also appeared partway through the longer run. Part of the cause is how the learning rate schedule is defined relative to the requested run length, and the rest is most likely that non decaying exploration setting. Both are concrete design choices we can fix, not a ceiling on the approach."),
  h2("5.5 Did We Meet Our Phase A Metrics?"),
  p("The Phase A proposal defined six quantitative success criteria. We report against all six, including the ones the delivered scope did not address."),
  simpleTable(
    ["Phase A success criterion", "Target", "Outcome"],
    [
      ["Average waiting time reduction", "At least 20% vs. a fixed time baseline", "Exceeded for two of three traffic conditions, 50% (light traffic) and 36% (moderate traffic). 8% in heavy traffic, independently verified across many random seeds rather than a single run"],
      ["Maximum queue length reduction", "At least 15%", "Not separately measured. Our evaluation reports total waiting time rather than maximum queue length as the primary metric"],
      ["Detection accuracy (mAP)", ">90% standard vehicles, >95% emergency vehicles", "Not applicable, the computer vision component was not implemented (Chapter 4)"],
      ["Real time processing speed", ">30 to 45 FPS, under 100ms latency", "Not applicable, no vision pipeline was implemented"],
      ["Emergency vehicle delay", "0 seconds in 100% of test cases", "Not implemented, no Priority Protocol or emergency vehicle class exists in the delivered system"],
      ["Fallback mode activation", "Within one signal cycle of a detected sensor failure", "Not applicable, no sensor input or fallback mode exists in the delivered system"],
    ],
    [3200, 2600, 3200]
  ),
  p("The one criterion that concerned the control policy itself, at least 20% less average waiting time than a fixed time baseline, was exceeded in two of the three conditions. The condition where it was not, heavy traffic at 8%, was investigated rather than left unexplained (Section 5.3). The other five criteria concern the vision, priority protocol, and infrastructure components which, as Chapter 4 explains, were not built."),
];

//
// CHAPTER 6, TESTING AND VERIFICATION
//
const chapter6 = [
  h1("6. The Testing Process"),
  p("Every number in Chapter 5 rests on the evaluation process described here. We treat it as a contribution in its own right, because the main risk in work like this is not an agent that fails visibly, but one that produces good summary statistics without being dependable."),
  h2("6.1 Verifying the Simulator Is Deterministic"),
  p("Before relying on any comparison between controllers, we verified rather than assumed that SUMO\'s vehicle generation is deterministic. The same seed produces a bit for bit identical stream of vehicles whichever controller drives the signal, across separate processes and across different days. This is what makes a paired comparison meaningful, since any difference must then come from the controller rather than from easier traffic in one run."),
  h2("6.2 How Our Evaluation Methodology Escalated"),
  p("We escalated verification rigor in three stages, each prompted by a specific limitation of the one before it."),
  bullet("Two fixed seeds during early development. Enough to show whether a change had any effect, not enough to claim one version beats another."),
  bullet("Five, then fifty independently drawn seeds, once a comparison needed more confidence than two runs could give."),
  bullet("Every saved checkpoint evaluated against its own independently drawn seed and scenario, with no reuse, no selection, and no unfavorable result excluded."),
  h2("6.3 The Final, Unfiltered Methodology"),
  p("A checkpoint is a saved copy of the agent\'s weights, written automatically every 100,000 steps, so a six million step run produces 60 of them. That gives an evenly spaced record of progress from start to finish rather than only the final state. The final method evaluates all 60, each against its own seed and scenario, and reports every outcome."),
  p("This is what lets us say, with real confidence rather than as a headline figure, that our champion agent beats all three baselines in 53 of 60 independent evaluations, or 88.3%, and that its losses are narrow single digit misses against the toughest baseline in light traffic rather than the systematic failures earlier versions showed. Applying the same method to a second run of the identical recipe gave one of the project\'s more useful negative results, reported in Section 5.4: a repeat run does not reliably reproduce the quality of the first."),
  p("The raw output is kept in the repository, so any claim in Chapter 5 can be checked against the per checkpoint numbers behind it. Running this many episodes only became practical after we added an early exit condition, stopping an episode once no vehicle remains and none are expected, which cut typical evaluation time by roughly seven to eight times with no change to the results."),
];

//
// CHAPTER 7, CHALLENGES
//
const chapter7 = [
  h1("7. Challenges and How We Overcame Them"),
  p("Several problems recurred during development. Most are general lessons about applied reinforcement learning rather than quirks of this intersection."),
  h2("7.1 Reward Hacking via Simulator Artifacts"),
  p("The first working version looked exceptional until we examined how. It was starving selected lanes long enough that SUMO\'s teleportation safety feature, which removes vehicles stationary for an implausible period so the simulation does not deadlock, deleted those vehicles entirely. Waiting time charged to a vehicle that no longer exists is, to the reward function, waiting time that never happened. The fix was simple once found, disabling teleportation permanently, but finding it meant watching the agent\'s behavior directly rather than trusting the reward curve, which rose steadily the whole time."),
  h2("7.2 A Dynamic Minimum Green Rule That Fired on the Wrong Signal"),
  p("One version let the agent switch before the minimum green interval whenever the active phase looked nearly empty, measured by live vehicle counts on that phase\'s lanes. This had a structural flaw. While a phase is green its vehicles are moving rather than halted, so a live count on a green phase reads as nearly empty almost by construction. Trained further against this bug, the agent committed to exploiting it. Some phases switched at the earliest possible moment every cycle, others held for the maximum, and starved phases accumulated waits over 17,000 seconds, the worst result in the project. Only an agent retrained from random initialization fixed it. That set the rule we applied afterwards: resuming training after a real rule change risks reinforcing a bug rather than correcting it."),
  h2("7.3 A Reward with Almost No Gradient in Light Traffic"),
  p("A version rewarded only on the reduction in total waiting time did acceptably in moderate and heavy traffic but could not learn light traffic at all. With few vehicles present, the change in total waiting time between decisions is near zero almost regardless of what the agent does, leaving almost no gradient in exactly the condition where it was needed. Adding a starvation penalty, which responds to how long a lane group\'s longest waiting vehicle has sat there rather than to an aggregate that stays near zero, gave a usable gradient under sparse demand, and light traffic performance improved by roughly a factor of fifteen."),
  h2("7.4 The Camera Range Trade Off"),
  p("Limiting the observation to a fixed distance from the stop line, to model a realistic sensor rather than an omniscient one, first caused a regression in heavy traffic. Queues extending past the sensing range were invisible, so the agent under reacted to congestion it could not see. We tested whether a richer, non saturating encoding of the same observation would compensate. It did not (Section 5.3), and we resolved the regression by extending the sensing range instead."),
  h2("7.5 An Idle Intersection That Still Wanted to Switch"),
  p("Once the other issues were resolved, the agent still occasionally switched phases at a completely empty intersection, for no benefit, because nothing in training had taught it that doing so was pointless. We tried a soft penalty first and it was too weak to compete with the main reward term. The fix removed the action entirely: switching is structurally unavailable whenever no vehicle is present, whatever the policy would otherwise choose. This single change took the agent from beating some baselines to beating every baseline in every tested condition. The principle, enforce a real constraint structurally rather than discourage it with a penalty, is one we would apply earlier next time."),
];

//
// CHAPTER 8, SUMMARY, CONCLUSIONS AND FUTURE WORK
//
const chapter8 = [
  h1("8. Summary, Conclusions and Future Work"),
  h2("8.1 Summary"),
  p("This project asked whether a reinforcement learning agent, given no explicit control rules, could run an intersection better than the fixed time signals in general use. It can, by roughly 50% in light traffic, 36% in moderate, and 8% in heavy, winning 53 of 60 fully independent evaluations. The remaining gap in heavy traffic was investigated rather than left unexplained, and comes from the physical capacity of a single intersection rather than any limit on what the agent can see."),
  h2("8.2 Lessons Learned"),
  p("We would do several things differently. We would enforce real physical or logical constraints structurally through action masking from the first version, rather than discouraging them with a penalty and only reaching for a hard constraint after the penalty had failed. The empty intersection problem cost more iteration time than it needed to for exactly that reason. We would also adopt the full unfiltered evaluation method from the start rather than escalating into it. Several early conclusions that one version was clearly better turned out to be far less certain once tested properly, and committing to rigor sooner would have saved iteration cycles rather than costing them."),
  p("We would also treat \"train it for longer\" with far more skepticism. It is an intuitive, low effort thing to try, and it is not obviously wrong, but we now have controlled evidence that it does not reliably help under this training setup. We would rather have established that early than midway through."),
  p("On balance we handled the project\'s central risk correctly, an agent that looks good on paper but is not dependable, by consistently building better verification rather than accepting an encouraging headline figure. That discipline is the most transferable outcome of this work, independent of the traffic control results."),
  h2("8.3 Thoughts for Future Development"),
  p("Four directions follow from where this project stopped. The first two are the most valuable."),
  bullet("The simulation to reality deployment layer: camera based perception with YOLO and DeepSORT, tracking, and physical integration with a signal controller. This is the half of the Phase A vision we did not build, and the step that turns a validated policy into a deployable system."),
  bullet("Multi intersection coordination. The heavy traffic ceiling in Section 5.3 is a property of one intersection in isolation. Coordinating with neighbors is the way past it, and where the largest remaining gains most likely are."),
  bullet("A decaying exploration schedule. The evidence in Section 5.4 points at the constant, non decaying entropy coefficient as the likely cause of run to run instability, which makes it a concrete next experiment rather than an open question."),
  bullet("A direct comparison between the DQN and PPO agents, applying the method in Chapter 6 to both, which would close the gap described in Section 4.3."),
];


const references = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("References"),
  p("Akçelik, R. (1994). Gap acceptance modeling by traffic signal logic. Transportation Research Record, 1457, 6 16."),
  p("Akçelik, R. (2010). Fundamental traffic variables in adaptive control and the SCATS DS parameter. Proceedings of the 24th ARRB Conference, Melbourne, Australia."),
  p("Department of Transport (UK). (1995). SCOOT: A traffic responsive method of coordinating signals (Traffic Advisory Leaflet 4/95). London, UK."),
  p("Dresner, K., and Stone, P. (2008). A multiagent approach to autonomous intersection management. Journal of Artificial Intelligence Research, 31, 591 656."),
  p("Koonce, P., Rodegerdts, L., Lee, K., Quayle, S., Beaird, S., Braud, C., et al. (2008). Traffic signal timing manual (Report No. FHWA HOP 08 024). Federal Highway Administration."),
  p("Liang, X., Du, X., Wang, G., and Han, Z. (2018). Deep reinforcement learning for traffic light control in vehicular networks. arXiv preprint arXiv:1803.11115."),
  p("Mnih, V., Kavukcuoglu, K., Silver, D., Rusu, A. A., Veness, J., Bellemare, M. G., et al. (2015). Human level control through deep reinforcement learning. Nature, 518(7540), 529 533."),
  p("Redmon, J., Divvala, S., Girshick, R., and Farhadi, A. (2016). You only look once: Unified, real time object detection. Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 779 788."),
  p("Wang, Y., Li, Z., and Zhang, Y. (2024). Traffic co simulation framework empowered by infrastructure camera sensing. arXiv preprint arXiv:2412.03925."),
  p("Wojke, N., Bewley, A., and Paulus, D. (2017). Simple online and realtime tracking with a deep association metric. 2017 IEEE International Conference on Image Processing (ICIP), 3645 3649."),
];

//
// APPENDIX A, USER GUIDE (full text, identical in substance to the
// standalone PhaseB/User_Guide.docx)
//
const appendixA = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("Appendix A, User Guide"),
  h2("A.1 Introduction"),
  p("FlowGrid is a reinforcement learning based traffic signal controller for a single SUMO simulated intersection. This guide is written for anyone who wants to run the project's tools directly: reviewers checking the delivered agent's claims, future developers picking the project back up, or anyone curious to watch the agent control traffic themselves."),
  p("Two independent agents were built over the course of this project: a Maskable PPO agent (the final, submitted \"champion\" agent, referred to throughout this guide as PPO_Agent) and an earlier Deep Q Network agent (DQN_Agent). PPO_Agent has two browser based interfaces, the original comparison app (Section A.5) and a newer SaaS style dashboard, FlowGrid_Web (Section A.6), with one junction wired to the live agent. DQN_Agent's interface is its own desktop application. Each is described separately below. If you only have time to try one thing, start with Section A.4, Quick Start."),
  p("PPO_Agent's web app includes a built in, floating guided tour that walks a first time user through every field on the page (which models and baselines to pick, how seeds and traffic scenarios work, what \"Watch Live\" does) with a short, plain language explanation for each, plus Skip, Previous, and Next controls. It starts automatically the first time the page loads and can be reopened anytime from the \"? Guide\" button in the page header, so this written guide and the app's own in page help reinforce each other rather than duplicate effort. Section A.5.2 covers it in more detail."),
  p("This guide covers normal, successful operating flow: installing the software, launching each tool, and reading the results it produces. It intentionally does not cover every error condition. If something does not behave as described here, see Section A.9, Troubleshooting."),
  h2("A.2 System Requirements"),
  p("The project was developed and tested on Windows with the following software installed."),
  simpleTable(
    ["Requirement", "Version / Notes"],
    [
      ["Operating system", "Windows 10/11 (developed and tested here). Linux/macOS should work with SUMO and Python installed, but were not tested"],
      ["Python", "3.10"],
      ["SUMO (Simulation of Urban Mobility)", "1.20 or later, with the SUMO_HOME environment variable set and the TraCI/libsumo Python bindings on the path"],
      ["CPU", "A multi core processor is strongly recommended. Training and full evaluation sweeps run ten parallel SUMO instances by default"],
      ["GPU", "Optional. Training uses CUDA if available (torch.device(\"cuda\")). It also runs on CPU, just considerably slower"],
      ["Disk space", "Several hundred MB for the trained models and evaluation results already included in this repository. Several GB free if you plan to retrain from scratch"],
    ],
    [3200, 5800]
  ),
  p("Key Python packages (installed via requirements.txt at the project root): FastAPI, uvicorn, gymnasium, numpy, torch, matplotlib, pydantic, PyYAML, and eclipse sumo. In addition, the PPO side of the project requires Stable-Baselines3, sb3-contrib (for MaskablePPO and action masking), sumo-rl, pandas, and seaborn."),
  h2("A.3 Installation"),
  h3("A.3.1 Clone the repository"),
  code("git clone https://github.com/einavbs1/FlowGrid.git\ncd FlowGrid"),
  h3("A.3.2 Install SUMO"),
  p("Install SUMO from https://sumo.dlr.de/ and make sure the SUMO_HOME environment variable points to your installation folder (e.g. C:\\Program Files (x86)\\Eclipse\\Sumo). This is required before any simulation, training, or evaluation script will run."),
  h3("A.3.3 Create a Python environment and install dependencies"),
  code("python -m venv venv\nvenv\\Scripts\\activate\npip install -r requirements.txt\npip install stable-baselines3 sb3-contrib sumo-rl pandas seaborn"),
  note("No further project specific installation is required. Every script locates the SUMO network and route files it needs via paths defined in the code, relative to the project root."),
  h2("A.4 Quick Start"),
  p("The fastest way to see the delivered agent in action is the web comparison app, which lets you pick a traffic scenario and watch the trained PPO agent control the intersection live, side by side with a plain fixed time signal."),
  bullet("Double click run_web.bat right in the PPO_Agent folder (or run it directly: cd PPO_Agent/scripts/comparison_web, then python server.py)."),
  bullet("Your browser opens automatically. A built in guided tour walks through every field the first time. Click \"? Guide\" in the top bar to see it again anytime."),
  bullet("In the page that opens, leave the pre selected champion model and the three fixed time baselines ticked."),
  bullet("Choose \"Manual\" seeds, type in any number (e.g. 42), and select one traffic scenario, e.g. Medium."),
  bullet("Tick \"Watch Live\" and click \"Start Comparison.\""),
  bullet("A real SUMO window opens and plays the simulation live. When it finishes, a results table and bar chart appear in the app comparing total waiting time."),
  p("The rest of this guide covers every part of that flow in more detail, plus the equivalent browser based tool and the original DQN agent's own tools."),
  p("A recorded video walkthrough of this entire flow, including a live Watch Live session, is available at https://drive.google.com/file/d/1BE3oeGWWbVrQEC_ZL0rVh5AdPs9kDNTY/view (also linked on this book's cover page) if you would rather watch it once before trying it yourself."),
  h2("A.5 Using the PPO Comparison Tool (Current Agent)"),
  p("PPO_Agent is the final, submitted agent (internally called V8). Its comparison app lives in PPO_Agent/scripts/comparison_web, sharing its underlying logic with the project's command line sweep tools (comparison_core.py)."),
  h3("A.5.1 Launching the App"),
  p("Double click run_web.bat right in the PPO_Agent folder (or run_web.vbs for no console window), or run it directly:"),
  code("cd PPO_Agent/scripts/comparison_web\npython server.py"),
  p("A local web server starts and a browser tab opens automatically (default: http://127.0.0.1:8000)."),
  h3("A.5.2 The Built In Guided Tour"),
  p("A floating, step by step tour starts automatically every time the page loads, spotlighting each section in turn (Models, Baselines, Seeds, Scenario, Watch Live and Start, Results) with a short explanation. Use Next and Previous to move through it, or Skip guide to dismiss it for that visit. Click \"? Guide\" in the top bar to bring it back at any time."),
  h3("A.5.3 Selecting Models to Compare"),
  p("The Models panel lists every trained agent currently registered in model_registry.json, with the project's champion model (PPO_Agent_V8) pre selected. Tick the checkbox beside any additional model you want included. To compare against a model not yet in the list, use \"Add Model\" and browse to its .zip file (the default browse location is PPO_Agent/models). It is added to the registry immediately and persists for future sessions."),
  h3("A.5.4 Selecting Baselines"),
  p("The Baselines panel lists the fixed time controllers available for comparison: Fixed_30s, Fixed_45s, and Fixed_60s (cycle length in seconds). Tick any you want included alongside the selected model(s)."),
  h3("A.5.5 Choosing Seeds and a Traffic Scenario"),
  p("Choose \"Random\" and a count to have that many fresh, never before seen traffic instances generated automatically, or choose \"Manual\" to type in specific seed values one at a time, useful when you want to reproduce a particular result exactly. Then select which traffic condition to test: Low, Medium, High, or all three at once. SUMO's vehicle generation is seeded, so a given seed always produces the identical vehicle stream regardless of which controller is driving the signal, which is what makes the resulting comparison fair."),
  h3("A.5.6 Watch Live"),
  p("With exactly one seed and one specific scenario selected, tick \"Watch Live\" before starting the comparison. Instead of running entirely in the background, an actual SUMO graphical window opens and plays the episode out in real time, so you can visually confirm what the agent is doing rather than trust the reported numbers alone."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "poster_sumo_preview.png")), transformation: { width: 460, height: 218 } })], { alignment: AlignmentType.CENTER }),
  p("What Watch Live actually opens: SUMO's own simulation window, showing the real intersection geometry, vehicles (yellow), and the current signal phase (red/green bars on each approach). Same view as Figure 3.4 in the main book.", { italics: true, size: 20 }),
  h3("A.5.7 Running the Comparison"),
  p("Click \"Start Comparison.\" A progress indicator tracks how many of the required simulation runs have completed (models x baselines x seeds x scenarios). Runs execute in parallel across multiple CPU cores unless Watch Live is active, in which case they run one at a time so the visualization stays meaningful."),
  h3("A.5.8 Reading the Results"),
  p("Once complete, a results table appears for each tested scenario, listing every selected model and baseline with its total waiting time for each seed and an overall average. The best performing entry in each table is highlighted, and a bar chart beneath the table gives the same comparison visually. Lower total waiting time is better."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "webapp_screenshot.png")), transformation: { width: 440, height: 336 } })], { alignment: AlignmentType.CENTER }),
  p("A real completed comparison: PPO_Agent_V8 against the Fixed_45s baseline, medium traffic, seed 732846. PPO_Agent_V8 is highlighted green as the winner (lower total waiting time), and the bar chart below the table repeats the same comparison visually. Same view as Figure 3.5 in the main book.", { italics: true, size: 20 }),
  h2("A.6 Using FlowGrid_Web (Live Junction Dashboard)"),
  p("FlowGrid_Web is a second, entirely independent web application delivered in this phase, a separate product from the PPO comparison app in Section A.5, not a new view added to it. It is a SaaS style traffic operations dashboard with multi junction navigation, a login screen, device settings, reports, and user management, with its own dedicated backend (its own FastAPI server, its own port, no connection to the comparison app's server). Most of FlowGrid_Web is a UI complete demonstration of what a fully deployed system could look like, not a live backend. One junction, \"Live Junction (SUMO Simulation)\", is genuinely wired to the trained PPO agent and a real SUMO episode. Section A.6.6 below is explicit about which is which."),
  h3("A.6.1 Launching FlowGrid_Web"),
  p("FlowGrid_Web runs as a single process: one double click of run_web.bat inside the FlowGrid_Web folder builds the dashboard, starts its own backend, which serves both the built dashboard and its live data API from one FastAPI server on port 8001, and opens it in your browser automatically. There is no separate dev server to start, and this never touches the separate PPO comparison app from Section A.5."),
  code("cd FlowGrid_Web\nrun_web.bat"),
  p("Allow up to about 30 seconds after launch before using Run Agent (Section A.6.5). FlowGrid_Web's backend needs that long to finish importing torch, SUMO, and Stable-Baselines3. Trying Run Agent before it is ready shows a plain, expected message asking you to try again in a few seconds, not an error. (A separate script, run_flowgrid_demo.bat at the project root, additionally starts the Section A.5 comparison app alongside FlowGrid_Web, for a full project demo. It is not needed just to use FlowGrid_Web.)"),
  h3("A.6.2 Logging In"),
  p("The login screen accepts two fixed demonstration accounts (there is no real authentication server behind this login, by design, see Section A.6.6):"),
  simpleTable(
    ["Username", "Password", "Role"],
    [
      ["admin", "admin123", "Administrator"],
      ["operator", "op123", "Operator"],
    ],
    [2600, 2600, 3800]
  ),
  h3("A.6.3 The Guided Tour"),
  p("Like the PPO comparison app, FlowGrid_Web opens with its own floating, step by step guided tour, spotlighting the search bar and district navigation on the junction selection page, and the Run Agent control and camera grid on the Dashboard page. It starts automatically every time you land on a page it covers and can be skipped or stepped through with the same Previous/Next/Skip guide controls."),
  h3("A.6.4 Selecting the Live Junction"),
  p("From the junction selection screen, open the Simulation district, then FlowGrid Lab, and select \"Live Junction (SUMO Simulation)\". Every other junction in the app uses simulated demonstration data refreshed every few seconds and is safe to explore, but only this one is backed by a real running agent."),
  h3("A.6.5 Running the Agent Live"),
  p("On the Dashboard page for the Live Junction, pick a traffic scenario (Low, Medium, or High) and click \"Run Agent\". Unlike the PPO comparison app, there is no seed field here, a random seed is chosen for you automatically every time, so every run is a genuinely fresh episode, never a rehearsed replay. Once running, all four direction cards update roughly once a second with the real vehicle queue count, the real signal color, and a live snapshot image captured directly from the running SUMO window, deliberately paced (at least 100 milliseconds of simulated time per real second) so the numbers and image are actually watchable rather than flashing past instantly."),
  h3("A.6.6 What Is Real and What Is a Demonstration"),
  p("To be direct about the boundary: \"Live Junction (SUMO Simulation)\" is real. Its queue counts, signal colors, and camera image come from an actual SUMO episode driven by the trained PPO agent, the same one evaluated throughout the book. Every other junction, every login, and every other feature (device settings, reports, user management, adding a junction) is a complete, working UI backed by simulated or randomly generated demonstration data, not a live backend, database, or camera. We built it this way deliberately, to demonstrate the target system's shape honestly without claiming a deployment that does not exist. See the book, Chapter 4 and Section 3.7, for the full reasoning."),
  h2("A.7 Using the DQN Tools (Original Agent, Archived)"),
  p("DQN_Agent is the project's original reinforcement learning approach. It predates PPO_Agent and is preserved, fully runnable, under Old_Versions/DQN_Agent since PPO_Agent is the current submitted agent. See the book (Section 4.3) for why the project moved from DQN to PPO."),
  h3("A.7.1 Desktop Application"),
  code("cd Old_Versions/DQN_Agent/gui\npython flowgrid_gui.py"),
  p("On Windows, double clicking Old_Versions/DQN_Agent/launchers/run_gui.bat launches the same application in its own process, so closing the terminal window does not close the app."),
  h3("A.7.2 Web Dashboard"),
  code("cd Old_Versions/DQN_Agent/web\npython main.py"),
  h3("A.7.3 The Compare Tab"),
  p("The Compare tab answers a focused question: on the same traffic demand, does the DQN signal policy reduce delay more than fixed time control? To make the comparison fair, both runs use the same vehicles (same count, routes, lanes, and depart times). Only the traffic light policy differs. A run has two phases: a fixed time baseline pass (random vehicle injection, then drain), followed by the DQN policy pass replaying the identical vehicle stream. See Old_Versions/DQN_Agent/docs/COMPARE.md for the full technical explanation of how this pairing is guaranteed."),
  h3("A.7.4 Command Line / Menu"),
  code("cd Old_Versions/DQN_Agent/scripts\npython run_menu.py"),
  p("An interactive menu over training, evaluation, and comparison, useful for running the DQN agent's tools without a graphical interface."),
  h2("A.8 Understanding the Traffic Scenarios"),
  p("Every comparison tool offers the same three traffic conditions, corresponding to different vehicle demand levels feeding the intersection."),
  simpleTable(
    ["Scenario", "Demand", "What it tests"],
    [
      ["Low", "Light, sparse traffic", "Whether the agent can find a useful signal to act on when very few vehicles are present (an early failure mode of this project, see the book Section 7.3)"],
      ["Medium", "Moderate, steady traffic", "Typical day to day operating conditions"],
      ["High", "Heavy, near saturating traffic", "Behavior as demand approaches the intersection's physical capacity, where every controller's performance converges (see the book Section 5.3)"],
    ],
    [1800, 3400, 3800]
  ),
  h2("A.9 Troubleshooting / FAQ"),
  h3("\"No model found\" when running evaluate_V8.py or the comparison tools"),
  p("Confirm you are running the script from inside PPO_Agent/scripts (not from PPO_Agent/ or the project root), and that PPO_Agent/models contains at least one ppo_model_*.zip file with a matching vec_normalize_*.pkl."),
  h3("SUMO_HOME is not set / TraCI import errors"),
  p("Every simulation, training, and evaluation script requires SUMO to be installed with the SUMO_HOME environment variable set. See Section A.3.2."),
  h3("The comparison tool is very slow"),
  p("Evaluation runs execute multiple SUMO simulations in parallel, bounded by CPU core count. Reducing the number of seeds, or running fewer scenarios at once, will reduce total wait time. \"Watch Live\" mode is inherently slower since it runs at a visible, non accelerated pace."),
  h3("I changed the reward function or observation and now training behaves strangely"),
  p("Never resume training from an existing checkpoint after changing the reward function or observation definition. Train a fresh agent from random initialization instead. This project encountered a full, unrecoverable policy collapse from doing exactly this once (see the book, Section 7.2). It is documented there as a cautionary example, not a theoretical risk."),
  h3("Where do I find the raw evaluation numbers behind the book's claims?"),
  p("PPO_Agent/results/final_random_seeds_20260705_005802/ contains the full, unfiltered evaluation (summary.txt, final_results.csv) behind the 88.3% win rate figure reported in the book. Old_Versions/DQN_Agent/results/comparison_history.json contains the equivalent raw evaluation history for the DQN agent, discussed in the book's Section 4.3."),
  h3("FlowGrid_Web's Run Agent button says \"Failed to fetch\" or asks me to try again"),
  p("This means FlowGrid_Web's own backend (port 8001) is not reachable yet, either it was never started (see Section A.6.1, run_web.bat starts it together with the dashboard) or it is still importing torch, SUMO, and Stable-Baselines3, which can take up to about 30 seconds after launch. Wait a few seconds and click Run Agent again. This is expected right after starting the servers, not a bug."),
  h2("A.10 Glossary"),
  simpleTable(
    ["Term", "Meaning"],
    [
      ["Baseline", "A non learned controller (fixed time cycle) the trained agent is compared against"],
      ["Checkpoint", "A saved copy of the agent's weights at a specific point during training"],
      ["Episode", "One complete simulated run of a traffic scenario, from an empty road to a defined end condition"],
      ["MaskablePPO", "The specific reinforcement learning algorithm used by PPO_Agent. Standard PPO extended with action masking"],
      ["Seed", "A number that deterministically fixes SUMO's randomly generated vehicle stream, so a given seed always produces the identical traffic"],
      ["SUMO", "Simulation of Urban Mobility, the open source traffic simulator this project's environment is built on"],
      ["TraCI", "SUMO's Traffic Control Interface, the Python API used to step the simulation and read/control the traffic light"],
      ["Vecnormalize", "Stable-Baselines3's running statistics for normalizing observations. Must be loaded alongside a model checkpoint to reproduce its trained behavior correctly"],
      ["Watch Live", "A comparison tool option that opens a real, visible SUMO simulation window instead of running in the background"],
    ],
    [2600, 6400]
  ),
];

//
// APPENDIX B, DEVELOPER / MAINTENANCE GUIDE (full text, identical in
// substance to the standalone PhaseB/Developer_Guide.docx)
//
const appendixB = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("Appendix B, Developer / Maintenance Guide"),
  h2("B.1 Introduction and Audience"),
  p("This guide is written for a developer picking up the FlowGrid codebase after delivery: continuing the PPO agent's development, retraining it, adding a new baseline, or extending the evaluation tooling. It assumes working familiarity with Python, Git, and reinforcement learning terminology (state, action, reward, policy), and focuses on how this specific codebase is organized and why, rather than teaching RL from first principles. For MDP formulation, reward design, and algorithm choice in full technical depth, see PROJECT_OVERVIEW.md at the project root. This guide focuses on the code and workflow around that design, not the design itself."),
  h2("B.2 System Architecture Overview"),
  p("The project is not a single application but three layers built on a shared simulation substrate."),
  bullet("Simulation substrate: SUMO (Simulation of Urban Mobility), driven through the sumo-rl and TraCI/libsumo Python interfaces. Both agents (PPO and DQN) simulate the same physical intersection, defined once under SharedData/maps, and read/write shared evaluation data under SharedData/reports."),
  bullet("Agents: two independently developed reinforcement learning agents, PPO_Agent (final, submitted, at the project root) and DQN_Agent (original, superseded, archived under Old_Versions/), each with its own environment wrapper, training script, and trained model files. They are not two modules of one system. They are two separate, self contained implementations that happen to target the same simulated intersection."),
  bullet("Tooling: evaluation scripts (single run and full checkpoint sweeps), the FastAPI comparison web app (comparison_core.py plus comparison_web/), and plotting utilities, all built specifically to make the agents' claims independently checkable rather than to just produce a headline number."),
  p("Data flows one direction through this stack: a trained model (.zip + matching vec_normalize .pkl for PPO, a .pth policy file for DQN) is loaded by an evaluation script, which drives the SUMO environment for one or more seeded episodes, and reports total waiting time and related metrics. Every comparison and analysis tool in the project is built on top of this same primitive, evaluate one model, on one seed, in one scenario, and get a number back."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_framework_diagram.png")), transformation: { width: 460, height: 236 } })], { alignment: AlignmentType.CENTER }),
  p("Figure B.1: the training and simulation core (PPO_Agent/scripts/train_V8.py + sumo_rl_env_V8.py). SubprocVecEnv runs ten parallel SUMO instances. VecNormalize tracks running observation statistics. The SwitchOrKeepWrapper is the actual translation layer between raw SUMO state and the agent's 21 dimensional observation, and between the agent's action and SUMO's TraCI control commands. Same diagram as Figure 3.1 in the main book.", { italics: true, size: 20 }),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "architecture_diagram.png")), transformation: { width: 440, height: 295 } })], { alignment: AlignmentType.CENTER }),
  p("Figure B.2: the evaluation and comparison layer built around that same core, evaluate_models.py driving scored episodes on demand, and the FastAPI comparison_web app (comparison_core.py) exposing that to a browser. This is the layer described in the Tooling bullet above. The Evaluation Engine and Comparison Web App boxes here correspond directly to evaluate_models.py and comparison_web/server.py in the repository.", { italics: true, size: 20 }),
  h2("B.3 Repository Structure"),
  simpleTable(
    ["Folder", "Contents"],
    [
      ["PPO_Agent/", "The one current, submitted agent (V8), at the project root. run_web.bat launches its comparison app directly. scripts/ has every runnable tool. models/ and checkpoints/ the trained weights. results/ every evaluation run performed against it. docs/ agent specific reference material."],
      ["FlowGrid_Web/", "A second, independent product (Section B.6): a SaaS style dashboard with one junction wired to a real live agent, with its own backend under backend/, entirely separate from PPO_Agent/scripts/comparison_web/."],
      ["Old_Versions/", "Every superseded agent: PPO/ (every earlier PPO version, V4 through V9, plus two longer training experiments, and the project's pre versioning first experiments), DQN_Agent/ (the original agent in full, self contained under its own flowgrid/ package, with gui/, web/, scripts/, launchers/, data/, results/, docs/), and root_prototype/ (pre RL prototype scripts). See Old_Versions/README.md."],
      ["PhaseA/", "The original Phase A proposal submission, unchanged."],
      ["PhaseB/", "The final submission: the capstone book, the poster, this guide and the User Guide. book_source/ holds the scripts that generate all three (build_book.js, build_user_guide.js, build_dev_guide.js) plus their chart images."],
      ["SharedData/", "The SUMO network/route files and the shared reports data both agents read from and write to."],
      ["README.md, PROJECT_OVERVIEW.md", "Whole project overview and RL design reference, at the project root."],
    ],
    [2400, 6600]
  ),
  h2("B.4 Environment Setup for Development"),
  h3("B.4.1 Required Environment"),
  bullet("Python 3.10, with the packages listed in requirements.txt (notably: Stable-Baselines3, sb3-contrib, sumo-rl, pandas, matplotlib, seaborn, FastAPI, uvicorn)."),
  bullet("SUMO, including its Python/TraCI and libsumo bindings, installed and available on the system path (SUMO_HOME set)."),
  bullet("A multi core CPU: training and full evaluation sweeps run ten parallel simulation instances by default (SubprocVecEnv during training, ProcessPoolExecutor during evaluation)."),
  h3("B.4.2 Project Specific Installation"),
  p("Clone the repository, then install Python dependencies into a virtual environment. No project specific installation step beyond this is required. The environment and training scripts locate the SUMO network and route files via paths defined in the code, all anchored at the project root (SharedData/)."),
  h2("B.5 The PPO Agent (V8), Code Walkthrough"),
  p("All PPO_Agent code lives flat inside PPO_Agent/scripts/, deliberately not nested under a version specific subfolder the way the archived versions in Old_Versions/PPO/saved_agents/ are, since V8 is the only version carried into the final submission."),
  h3("B.5.1 Environment: sumo_rl_env_V8.py"),
  p("Defines the Gymnasium environment: builds the 21 dimensional observation (phase one hot, elapsed green time, per lane demand, per lane starvation), the 2 action Keep/Switch action space, the action_masks() method enforcing minimum/maximum green and the hard empty intersection mask, and the reward calculation (diff waiting time minus a starvation penalty). sumo_rl_env.py is a one line shim (from sumo_rl_env_V8 import *) that every other script in this folder imports from generically, so swapping in a different version's environment during development only requires editing this one file."),
  h3("B.5.2 Training: train_V8.py"),
  code("cd PPO_Agent/scripts\npython train_V8.py --timesteps 6000000"),
  p("Builds a MaskablePPO agent (sb3-contrib) over ten parallel SUMO environments (SubprocVecEnv + VecNormalize), with a learning rate that decays linearly from 0.0003 down to 0 across the full run, and a constant entropy coefficient. Automatically resumes from the latest checkpoint in PPO_Agent/checkpoints/ if one exists. Use the fresh flag shown below to force a clean run instead. Saves a checkpoint every 100k steps by default, each with its matching VecNormalize statistics, since resuming or evaluating a checkpoint without its matching stats silently corrupts the observation distribution."),
  code("python train_V8.py --timesteps 6000000 --fresh\npython train_V8.py --timesteps 6000000 --save-freq 50000"),
  warning("Never resume training after changing the reward function or observation definition. Either load the old checkpoint and keep its original environment definition unchanged, or start fresh from random initialization. Never mix an old checkpoint with a changed environment. This produced a full, unrecoverable policy collapse once during this project (documented in the book, Section 7.2, the V3.3 incident)."),
  h3("B.5.3 Evaluation: evaluate_V8.py and evaluate_models.py"),
  code("cd PPO_Agent/scripts\npython evaluate_V8.py --seeds 5"),
  p("evaluate_V8.py auto finds the latest model in PPO_Agent/models/ and runs it against the three fixed time baselines across all three traffic scenarios, saving CSVs and charts to PPO_Agent/results/. The actual simulation running logic lives in evaluate_models.py, a single shared module every other tool in this folder also imports (run_evaluation_task, evaluate_scenario). Training, evaluation, comparison, and sweep tools all funnel through this one function rather than duplicating SUMO driving logic five times."),
  note("evaluate_models.py also exists as a separate copy at Old_Versions/PPO/src/evaluate_models.py, used by every archived version's own evaluate_*.py scripts. If you fix a bug in one copy, check whether the other needs the same fix."),
  h3("B.5.4 Comparison Tools: comparison_core.py, comparison_web/"),
  p("comparison_core.py is UI agnostic: it owns the model registry (model_registry.json), task building (build_tasks), and the actual comparison run (run_comparison, which drives a ProcessPoolExecutor and reports progress via any object with a .put(msg) method). comparison_web/server.py (FastAPI, serving comparison_web/static/) imports this module directly rather than duplicating its logic. The web app's own JobState satisfies the .put() interface run_comparison expects. The frontend (comparison_web/static/) is plain HTML/CSS/JS, no framework or build step, and includes a floating step by step guided tour (tour.js) that auto starts on every page load, reusing the static help text already written under each field so wording is never duplicated."),
  h3("B.5.5 Sweep and Analysis Tools"),
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
  h2("B.6 FlowGrid_Web, a Second, Independent Product"),
  p("FlowGrid_Web/ is a separate React/Vite SaaS style dashboard, added in this phase alongside the original comparison_web/ app. It is deliberately a separate product, not a new view bolted onto the developer facing comparison tool: comparison_web/ is a developer only tool for comparing checkpoints. FlowGrid_Web is the customer facing product, meant to demonstrate what a deployed traffic operations dashboard could look like. Consequently it has its own backend, FlowGrid_Web/backend/server.py, a second FastAPI app running on its own port (8001), entirely separate from comparison_web/server.py (port 8000). The two servers share no code by reference to each other. They both import the same underlying comparison_core.py and evaluate_models.py modules as shared library code, the same way any two independent applications might share a common engine."),
  p("Its pages (login, junction navigation, dashboard, live stream, device settings, reports, users) are a UI complete demonstration of a fully deployed system, backed by in memory demo data generated client side, except for one seed junction, LIVE_JUNCTION_ID (id 100, \"Live Junction (SUMO Simulation)\" in src/JunctionContext.jsx), whose Dashboard page is wired to FlowGrid_Web's own backend below."),
  h3("B.6.1 FlowGrid_Web's Own Backend (FlowGrid_Web/backend/server.py)"),
  simpleTable(
    ["Endpoint", "Purpose"],
    [
      ["GET /api/live_state", "Returns the current live_state dict: active, per direction lane_queues and phase_colors, step, and the seed of the current run. {\"active\": false} if nothing has run yet."],
      ["POST /api/live_demo/start", "The Live Junction panel's only control: body is just {scenario}, no model picker, no seed field. Always the already registered champion checkpoint (comparison_core.DEFAULT_MODEL_PATH), always a server chosen random seed (random.randint), always Watch Live on."],
    ],
    [3000, 6000]
  ),
  p("This file builds its own small job_state (just enough of comparison_web's JobState shape for core.run_comparison to report into) and its own live_state, a multiprocessing.Manager().dict() created lazily on first use rather than at import time, since Windows' spawn based multiprocessing would otherwise try to create a manager process recursively when uvicorn re imports this module. comparison_web/server.py has no CORS entry and no live_state at all. It does not need either, since only FlowGrid_Web calls cross origin."),
  warning("The list of allowed addresses in this file must not be shortened. A browser treats http://127.0.0.1:8001 and http://localhost:8001 as two different websites, even though both are this same computer on this same port. The dashboard always calls the backend at 127.0.0.1, so if the page itself was opened using the name localhost instead, the browser quietly blocks that call and the Run Agent button does nothing at all, with no error message shown anywhere. All four combinations of the two names and the two ports are listed here for exactly that reason. Removing any of them brings the problem back."),
  h3("B.6.2 Publishing Live State (evaluate_models.py, shared by both servers)"),
  p("evaluate_model_on_seed() takes a new optional live_state parameter, the same Manager().dict() proxy, threaded through comparison_core.build_tasks() and run_evaluation_task() only when use_gui is true. This is shared code: comparison_web/server.py's own Watch Live path always passes None here and is unaffected. Only FlowGrid_Web's backend passes a real live_state. Inside the per step loop, _publish_live_state(ts, live_state, step_count, total_queued) does three things every step."),
  bullet("Sums each lane's real halting vehicle count (sumo.lane.getLastStepHaltingNumber), grouped by compass direction from the lane ID's prefix (n_/s_/e_/w_to_center_*), not ts.get_lanes_queue(), which returns a [0, 1] lane capacity fraction rather than a human readable count."),
  bullet("Derives each direction's signal color from ts.sumo.trafficlight.getRedYellowGreenState(ts.id), matched against getControlledLanes(ts.id) by index. This network has an always on, lowercase g \"permitted\" slip lane at index 0 of every approach, so only uppercase G is treated as a real green. Treating lowercase g as green shows every direction as green simultaneously, which is wrong."),
  bullet("Calls ts.sumo.gui.screenshot(\"View #0\", path), writing directly into FlowGrid_Web/backend/static/live_snapshot.png (not comparison_web/static/, the two servers' static folders are entirely separate), which that backend's own /static mount serves. FlowGrid_Web polls this with a cache busting ?step= query parameter."),
  p("Separately, create_sumo_env() (sumo_rl_env_V8.py) gained an additional_sumo_cmd parameter, passed through to sumo_rl.SumoEnvironment. evaluate_model_on_seed() passes \"--delay 100\" whenever live_state is not None, pacing the SUMO GUI to at least 100 milliseconds of real time per simulated second, specifically so FlowGrid_Web's 1 second poll has something meaningful to show."),
  h3("B.6.3 Frontend Pieces (FlowGrid_Web/src/)"),
  simpleTable(
    ["File", "Role"],
    [
      ["JunctionContext.jsx", "Defines LIVE_JUNCTION_ID and the seed LIVE_JUNCTION entry, prepended to the existing demo junction list."],
      ["pages/Dashboard.jsx", "When the active junction is LIVE_JUNCTION_ID, polls http://127.0.0.1:8001/api/live_state once a second instead of generating random metrics, renders the Run Agent control (scenario only, no seed field, POSTs to /api/live_demo/start), and swaps each camera card's placeholder for an <img> pointed at /static/live_snapshot.png, cache busted by the current step."],
      ["Tour.jsx", "A small React reimplementation of comparison_web's vanilla tour.js: spotlights one target element (a React ref) at a time with a title/text pair supplied by the mounting page, auto starting on every page visit. Each page (JunctionSelect.jsx, Dashboard.jsx) mounts its own instance with its own steps."],
    ],
    [2600, 6400]
  ),
  warning("The code that starts the guided tour can look as though a safety check is missing, because the tour begins without first confirming that the parts of the page it points at already exist. Adding that check breaks the tour. While running in development mode, React deliberately runs this startup code twice, and in between the two runs it briefly disconnects the links to those parts of the page. A check landing in that short gap would decide the tour has nothing to show, and would keep that decision permanently, because the code never runs a third time. The tour already handles the not ready case further down, by simply drawing nothing until those parts of the page appear."),
  h3("B.6.4 One Process, Not Two: Serving the Built Frontend"),
  p("server.py also serves the built dashboard itself, so running FlowGrid_Web never needs a separate Vite dev server. After npm run build writes FlowGrid_Web/dist/, server.py mounts dist/assets under /assets and registers a catch all route, @app.get(\"/{full_path:path}\"), registered after every /api/* route so those are always matched first. The catch all returns the requested file if it exists in dist/, or falls back to dist/index.html otherwise, which is what lets React Router's client side routes (e.g. /reports) survive a hard refresh. main() only opens a browser tab automatically when dist/ exists, so running the API alone during development (Section B.6.5) does not pop open a stale or empty tab."),
  p("run_web.bat (or run_web.vbs for no console window) does exactly this: npm run build, then python server.py, nothing else. It never touches comparison_web/server.py. Separately, run_flowgrid_demo.bat at the project root starts both independent products, comparison_web's dev tool and FlowGrid_Web, for a full project demo."),
  code("cd FlowGrid_Web\nrun_web.bat"),
  h3("B.6.5 Active Frontend Development"),
  p("When actively editing FlowGrid_Web's React code, run the Vite dev server instead, for hot reload, alongside the same backend, in a second window, for the API:"),
  code("npm run dev\ncd backend && python server.py"),
  p("Dashboard.jsx's PPO_API constant is a hardcoded http://127.0.0.1:8001 regardless of dev or built mode, so both setups work against the same backend unmodified. Only the page's own origin (5173 while developing, 8001 once built and served) changes."),
  h2("B.7 The DQN Agent, Code Walkthrough"),
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
  p("The reward function (in flowgrid/core/, referenced from the DQN training loop) sums roughly a dozen hand tuned terms (diff wait, absolute wait penalty, spillback penalty, throughput bonus, fairness terms, anti flicker penalty, invalid action penalty). See PROJECT_OVERVIEW.md Section 3 for the exact formula and coefficients, and the book Section 4.3 for why this reward's complexity, and the resulting instability documented in Old_Versions/DQN_Agent/results/comparison_history.json, motivated the move to PPO."),
  h2("B.8 Retraining or Extending the PPO Agent"),
  p("To train a new version, copy PPO_Agent/scripts/ (and the model files, if building on an existing one) into a new folder under Old_Versions/PPO/ rather than modifying PPO_Agent/ in place. This preserves the current submitted agent as a working reference and follows the same \"copy, don't mutate\" convention used throughout this project's version history (see the archived V4 through V9 folders, each a fresh copy rather than an in place edit of the previous one)."),
  bullet("Copy sumo_rl_env_V8.py to a new file with an updated name. Update the sumo_rl_env.py shim's import to point at it."),
  bullet("Copy train_V8.py and evaluate_V8.py. No path edits are needed if the new folder sits at the same depth, since the training step count and other hyperparameters are already command line arguments."),
  bullet("Never resume training an existing checkpoint after changing its reward function or observation definition. Train a fresh agent from random initialization instead."),
  h2("B.9 Adding a New Baseline or Comparison Target"),
  p("New fixed time or rule based baselines can be added by extending AVAILABLE_BASELINES in comparison_core.py. Each baseline needs only a name and, for fixed time controllers, a cycle length, since the comparison tools handle result collection and reporting generically through evaluate_models.py's existing \"fixed\" model type. Max Pressure (model type \"mp\" in evaluate_models.py) is not registered in AVAILABLE_BASELINES. It was never successfully integrated as a reliable comparison baseline on this network (see the book, Section 1.1), so it does not appear in the web app or comparison tooling."),
  h2("B.10 Running an Evaluation Sweep"),
  p("final_results_random_seeds.py and checkpoint_sweep.py both support a dry run flag that reports exactly how many simulation runs a given sweep will perform and how long it is expected to take, without executing anything. Always run this first before committing to a long sweep."),
  code("python final_results_random_seeds.py --version-dir .. --dry-run\npython final_results_random_seeds.py --version-dir .."),
  p("Sweeps write partial results incrementally as they progress (assignments.csv is written up front with the full plan, final_results.csv is appended to after every checkpoint completes). If interrupted, resuming with the flag shown below continues exactly where it left off using the original plan. The summarize only flag regenerates summary.txt and the charts from whatever rows already exist, without running anything new."),
  code("python final_results_random_seeds.py --version-dir .. --resume <out_dir>\npython final_results_random_seeds.py --version-dir .. --summarize-only <out_dir>"),
  h2("B.11 Testing and Verification Methodology"),
  p("This project's evaluation rigor escalated deliberately over its course, and the same escalation is worth reusing for any future work on this codebase rather than trusting an early, less rigorous result."),
  bullet("A couple of fixed seeds, used throughout early development for fast iteration."),
  bullet("Five, then fifty independently drawn seeds, once a comparison needed more confidence than two runs could give."),
  bullet("Every saved checkpoint against its own freshly drawn random seed and scenario (final_results_random_seeds.py), nothing reused, nothing cherry picked, no unfavorable result excluded. This is what let the project report, with real confidence, that the champion agent beats all three fixed time baselines on 53 of 60 independently random evaluations (88.3%)."),
  p("Two properties of the environment make this methodology trustworthy rather than just elaborate: SUMO's seeded vehicle generation is genuinely deterministic (the same seed produces a bit for bit identical vehicle stream regardless of which controller is driving the signal, verified empirically across process restarts), and evaluation episodes now terminate as soon as the road is genuinely empty rather than running to a fixed time limit, which cut typical evaluation time by roughly seven to eight times with no change to the reported results."),
  h2("B.12 Known Limitations and Future Work"),
  bullet("Single intersection scope: this project controls one intersection. Multi intersection coordination is unattempted future work."),
  bullet("High traffic ceiling: performance near the intersection's physical demand capacity reflects queueing physics, not a perception limitation (ruled out directly by a V9 experiment with a richer, non saturating observation encoding, see the book, Section 5.3)."),
  bullet("Training is not reproducible run to run: two independent runs of the identical V8 recipe (V8 and V8_replicate) produced meaningfully different stability profiles. The leading hypothesis is the constant, non decaying entropy coefficient. This is a concrete, addressable item for future work, not a fully solved question."),
  bullet("Computer vision perception (YOLO + DeepSORT), proposed in the original Phase A plan, was not implemented in this delivered scope. See the book, Chapter 4, for the full explanation. It remains the most natural next step for extending this project toward real world deployment."),
  bullet("No formal, rigorous head to head comparison exists between the DQN agent and the fixed time baselines using the same seed verified methodology applied to PPO. Old_Versions/DQN_Agent/results/comparison_history.json contains real evaluation history but was not brought to the same level of statistical rigor."),
  h2("B.13 Coding Conventions Observed in This Codebase"),
  bullet("Copy, don't mutate: a new agent version is a new folder, never an in place edit of a previous one's environment or training script. This preserves every earlier version as a working, comparable reference."),
  bullet("Path resolution: every script computes _HERE = os.path.dirname(os.path.abspath(__file__)) and builds paths relative to it, rather than assuming a particular working directory. Shared modules (evaluate_models.py) are colocated as sibling files within PPO_Agent/scripts/ rather than imported via a separate src/ folder one level up, which is how the earlier, archived versions under Old_Versions/PPO/ still do it. This is a historical difference worth knowing about if you compare the two, not an inconsistency to \"fix.\""),
  bullet("Crash safety: any long running sweep writes its full plan before starting and appends results incrementally, so a kill or crash partway through loses nothing already computed and can be resumed."),
  bullet("Structural constraints over penalties: wherever a behavior must never happen (switching an empty intersection, violating minimum/maximum green), the project moved from discouraging it with a reward penalty to preventing it outright via action masking, after direct evidence that penalties alone were unreliable. Apply the same principle to any new hard constraint."),
];

const doc = new Document({
  features: { updateFields: true },
  styles: {
    default: {
      document: { run: { font: FONT, size: SIZE } },
    },
  },
  sections: [
    {
      properties: {
        page: {
          margin: { top: 1224, right: 1224, bottom: 1224, left: 1224 },
        },
      },
      headers: {
        default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "FlowGrid, Capstone Project Phase B", font: FONT, size: 16, color: "808080" })] })] }),
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18 })],
          })],
        }),
      },
      children: [
        ...coverPage,
        ...toc,
        ...chapter1,
        ...chapter2,
        ...chapter3,
        ...chapter4,
        ...chapter5,
        ...chapter6,
        ...chapter7,
        ...chapter8,
        ...references,
        ...appendixA,
        ...appendixB,
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(path.join(__dirname, "..", "FlowGrid_Capstone_Project_Book.docx"), buffer);
  console.log("Written: FlowGrid_Capstone_Project_Book.docx");
});
