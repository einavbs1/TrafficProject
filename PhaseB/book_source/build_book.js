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
    spacing: { after: 200, line: 276 },
    children: [new TextRun({ text, font: FONT, size: SIZE, ...opts })],
    ...opts.paragraphOpts,
  });
}

function para(children, paragraphOpts = {}) {
  return new Paragraph({ spacing: { after: 200, line: 276 }, children, ...paragraphOpts });
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 400, after: 200 }, children: [new TextRun({ text, font: FONT })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 300, after: 150 }, children: [new TextRun({ text, font: FONT })] });
}
function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 100 }, children: [new TextRun({ text, font: FONT, italics: true })] });
}
function bullet(text) {
  return new Paragraph({
    spacing: { after: 120, line: 276 },
    bullet: { level: 0 },
    children: [new TextRun({ text, font: FONT, size: SIZE })],
  });
}
function placeholder(text) {
  return new Paragraph({
    spacing: { after: 200, line: 276 },
    shading: { type: ShadingType.CLEAR, fill: "FFF3CD" },
    children: [new TextRun({ text: "[" + text + "]", font: FONT, size: SIZE, bold: true, color: "8A6D3B" })],
  });
}
function code(text) {
  return new Paragraph({
    spacing: { before: 100, after: 200 },
    shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
    children: [new TextRun({ text, font: "Consolas", size: 20 })],
  });
}
function note(text) {
  return new Paragraph({
    spacing: { before: 100, after: 200 },
    shading: { type: ShadingType.CLEAR, fill: "E8F0FE" },
    children: [new TextRun({ text: "Note: " + text, font: FONT, size: SIZE, italics: true, color: "1F2D3D" })],
  });
}
function warning(text) {
  return new Paragraph({
    spacing: { before: 100, after: 200 },
    shading: { type: ShadingType.CLEAR, fill: "FDEDED" },
    children: [new TextRun({ text: "Caution: " + text, font: FONT, size: SIZE, bold: true, color: "8A1F1F" })],
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
    children: [ new ImageRun({ type: "png", data: logoBuffer, transformation: { width: 380, height: 150 } }) ] }),
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
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1 3" }),
  new Paragraph({ children: [new PageBreak()] }),
];

//                                                                            
// SECTION 1, PROBLEM OVERVIEW AND BACKGROUND
//                                                                            
const section1 = [
  h1("1. Problem Overview and Background"),
  p("Most traffic signals in daily use still run on an idea that has barely changed in decades: a fixed cycle of green, yellow, and red, timed once by an engineer and rarely touched again. That works well enough when traffic is predictable, but real traffic rarely is, it swells during rush hour, thins out at night, and reacts to accidents, weather, and events in ways a fixed timer cannot see and cannot respond to. The practical result is a signal that is sometimes too generous to an empty approach and too stingy to a congested one, for no better reason than that it has no way of knowing which is which."),
  p("Other \"adaptive\" families of controllers try to close that gap. Actuated controllers use loop detectors to extend or shorten a phase depending on whether vehicles are currently arriving, but they typically cannot see more than a short distance past the stop line, so they have little sense of how long a queue actually is once it grows past the detector. We compared our agent against fixed time cycles (30, 45, and 60 seconds), the actual baselines used throughout this book. We also wanted to include Max Pressure, a more principled adaptive controller from the traffic engineering literature, as another agent to compare against, but integrating it reliably would have taken more development time than we had available, so we chose to skip it."),
  p("This project asks a more open question than \"which fixed cycle length is best\": could an agent that is never given an explicit rule at all, and instead learns purely from repeated, simulated experience of driving traffic through an intersection, learn to do this job better than either of the above? And where it does, or does not, we wanted to actually understand why, rather than accept a single headline number."),
  p("Reinforcement learning is a natural fit for this problem because it has exactly the shape RL is built to handle: an agent (the signal controller) observes some state (who is waiting, for how long, how the intersection currently looks from the camera's point of view), takes an action (hold the current phase, or advance to the next one), and receives feedback about whether that was a good decision, over and over, across thousands of simulated episodes. What makes the problem genuinely hard is also what makes it interesting: the \"right\" reward signal is not obvious (reward the absence of waiting? reward throughput? something else?), the environment is only partially observable (a real camera cannot see indefinitely far down the road), and, as this project demonstrated more than once, an RL agent can find a technically correct but practically wrong way to make its reward number go up without doing anything useful for an actual driver."),
  p("We built a dedicated single intersection SUMO (Simulation of Urban Mobility) environment to study this cleanly, before considering anything more ambitious, since most of the genuinely hard problems in this space, reward design, partial observability, exploration versus exploitation, and the risk of reward hacking, are already fully present at a single four phase intersection."),
  h2("1.1 Related Work"),
  p("Traffic signal control has evolved through several distinct generations, each addressing a limitation of the one before it, and our Phase A research surveyed this progression in some depth. The oldest and still most common approach, fixed time control, runs a rigid schedule derived from historical traffic counts (Koonce et al., 2008). It is predictable but, by design, blind to what is actually happening on the road at any given moment. Vehicle actuated control improves on this using inductive loop detectors embedded in the road surface, extending or ending a phase based on whether a vehicle is currently present, but this relies on binary presence detection rather than any real measure of traffic volume, and a single vehicle arriving on a minor approach can interrupt a heavy flow on a main road (Akçelik, 1994)."),
  p("A further generation of network wide adaptive systems moved beyond a single intersection's local logic. SCOOT models platoons of vehicles using upstream detectors and continuously adjusts split, cycle, and offset to maintain a coordinated \"green wave\" across a corridor (UK Department of Transport, 1995), while SCATS pursues an \"equisaturation\" philosophy, using stop line detectors to measure a Degree of Saturation and reallocate green time to balance load across competing approaches (Akçelik, 2010). Both are genuinely adaptive and both remain widely deployed, but neither learns in the machine learning sense. Their logic is fixed by design, just responsive to live inputs rather than to a static clock."),
  p("A more recent and more ambitious line of research looks past physical signals altogether. Dresner and Stone (2008) proposed a reservation based Autonomous Intersection Management protocol in which vehicles negotiate directly with an intersection manager and weave through without ever stopping, and Liang et al. (2018) demonstrated a Vehicle to Infrastructure architecture feeding a high resolution grid state into a Double Dueling Deep Q Network. Both depend on a level of connected vehicle market penetration that does not exist today, which is precisely the gap our own project's original proposal set out to bridge with a \"camera as a sensor\" approach: real time detection using YOLO (Redmon et al., 2016), tracking across occlusion using DeepSORT (Wojke et al., 2017), and a Deep Q Network agent in the tradition of Mnih et al. (2015), retrofitted onto existing intersections. Wang et al. (2024) validated a closely related \"camera as sensor\" framework, reinforcing that this remains an active research direction."),
  p("Our own project began, in its Phase A proposal, exactly here: a full perception to decision pipeline combining YOLO detection, DeepSORT tracking, and a DQN control agent. As Section 2.3 describes in full, the project's actual development narrowed this scope considerably, for reasons that were partly deliberate (isolating the control policy question from the perception question, to study each cleanly) and partly circumstantial (both of us were called up for military reserves during the project, reducing available development time). What we are able to report on rigorously in this book is the control policy question in isolation, using the simulator's own ground truth vehicle state in place of a vision pipeline, evaluated far more exhaustively than the original proposal's success criteria called for. We consider the vision based perception layer proposed in Phase A to remain the natural and most valuable next step for this project, not a direction that was tried and found wanting."),
];

//                                                                            
// SECTION 2, DESCRIPTION OF WHAT WE ACHIEVED
//                                                                            
const section2_intro = [
  h1("2. Description of What We Achieved"),
  h2("2.1 General Description"),
  p("At a high level, this project set out to build and, just as importantly, rigorously evaluate a reinforcement learning agent capable of controlling a single traffic signal intersection more effectively than the standard alternatives already used in practice. \"More effectively\" meant, concretely, lower total vehicle waiting time across a range of traffic conditions, light, moderate, and heavy, since that is the number that actually matters to a driver sitting at a red light, and it is the number every baseline in this project is judged against."),
  p("The system we ended up with, which we call FlowGrid, is really three things working together. The first is a SUMO based simulation environment modelling one four way intersection with realistic, randomly generated vehicle demand, camera limited sensing (the agent only \"sees\" 150 meters back from the stop line, meant to represent what an actual roadside sensor could plausibly observe, not an omniscient view of the whole street), and a set of hard safety constraints, minimum and maximum green durations, mandatory yellow transitions, that no learned policy is ever permitted to violate, regardless of what it has learned. The second is the trained agent itself: a Proximal Policy Optimization (PPO) policy, trained from scratch with no hand coded switching rules, that decides every five simulated seconds whether to hold the current phase or advance to the next one. The third is a full evaluation and demonstration layer, two graphical applications (a desktop version and a browser based one), a family of statistical comparison tools, and a \"Watch Live\" mode that opens a real SUMO visualization window on demand, built specifically so the agent's performance could be checked, questioned, and shown to someone else, rather than simply trusted on the strength of one reported number."),
  p("We also put real effort into making that browser based application approachable to someone who has never seen it before. It opens with a floating, step by step guided tour, built directly into the page, that spotlights each field in turn (which models to compare, which baselines, how seeds and traffic scenarios work, what \"Watch Live\" does) with a plain language explanation of what to choose, and Skip, Previous, and Next controls. It starts automatically on every visit and can be reopened from a \"? Guide\" button in the page's header. We consider this a genuine part of the deliverable, since a comparison tool nobody can figure out how to use is not meaningfully more useful than no tool at all."),
  p("The intended audience for this system splits naturally into two groups with different needs. Traffic engineers or municipal decision makers would weigh whether an RL based controller is worth piloting, and for them what matters most is the evaluation story: does it actually beat what is already in use, under which conditions, and how much confidence is behind that claim. The second audience is anyone continuing this line of work, including ourselves, for whom what matters is the version history, the attempts that failed and precisely why, and tooling that makes it possible to test a new idea quickly rather than re derive all of this from first principles."),
];

const section2_solution = [
  h2("2.2 Solution Description, Research Approach"),
  p("Because this is a research track project, this section leads with the algorithms and methodology behind the agent, the software system that carries them out is documented in full in the Maintenance Guide (Appendix B), with the same architecture diagrams repeated here since they are just as relevant to understanding the research approach as they are to maintaining the code."),
  h3("System Architecture"),
  p("The diagram below shows the actual, delivered implementation: a training orchestrator running ten parallel SUMO instances (SubprocVecEnv, VecNormalize) feeding a Maskable PPO agent, connected to the simulator itself through a translation layer, our SwitchOrKeepWrapper, responsible for constructing the observation, enforcing phase and safety logic, and computing the reward, which in turn drives Eclipse SUMO through its TraCI API and vehicle physics engine."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_framework_diagram.png")), transformation: { width: 500, height: 256 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.0a: the training and simulation architecture actually implemented and used to produce every result in this book, drawn as a UML component diagram. Every component named here (SubprocVecEnv, VecNormalize, the Maskable PPO Agent, the SwitchOrKeep Wrapper and its three responsibilities, the TraCI API) is a real class or module in the delivered codebase, not an aspirational diagram.", { italics: true, size: 20 }),
  p("This same core is wrapped in the evaluation and comparison tooling described in Section 2.5: an Evaluation Engine that drives scored episodes against this training/simulation core, and two browser based front ends built on top of it, the original Comparison Web App and the newer FlowGrid_Web dashboard, both covered in the Maintenance Guide's architecture section rather than repeated here."),
  h3("The decision problem, formally"),
  p("Every reinforcement learning problem reduces to a Markov Decision Process: a state the agent observes, an action it chooses, a reward it receives, and rules governing how the state evolves. Framing our own problem this way early on was one of the more clarifying steps in the project, since it forced explicit answers to questions that are easy to leave vague otherwise."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "mdp_loop_diagram.png")), transformation: { width: 360, height: 287 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.0b: the MDP loop as implemented, concretely, by our SwitchOrKeepWrapper. The numbered steps below the diagram correspond directly to the state, action, and reward definitions that follow.", { italics: true, size: 20 }),
  p("The state our final agent observes is a 21 dimensional vector, entirely normalized to the range [0, 1]: a one hot encoding of which of the four signal phases currently has the green light, how long that phase has already held green as a fraction of its allowed maximum, an occupancy density reading for each of eight lane groups (again, camera limited to 150 meters), and a starvation score per lane group capturing how long the single longest waiting vehicle in that group has been sitting there. That last piece deserves a note: an intersection can have a very reasonable looking average wait time while one unlucky vehicle in a rarely served lane waits far longer than anyone would consider acceptable, and the starvation term exists specifically so the agent cannot ignore that vehicle just because the aggregate numbers look fine."),
  p("The action space is intentionally small: hold the current phase, or switch to the next one in a fixed cyclic order. We do not let the agent jump directly to an arbitrary phase, early experimentation (described in Section 2.6) showed that a free jump action space encourages rapid, wasteful cycling through yellow transitions, and a cyclic structure removes that failure mode by construction rather than trying to penalize it away. On top of this action space sits a layer of hard, structural constraints, enforced outside the learned policy entirely: the agent is physically prevented from switching before a minimum green time has elapsed, is forced to switch once a maximum green time is reached regardless of its preference, and, critically, as covered below, is prevented from ever switching an already empty intersection."),
  p("The reward is deliberately simple: the reduction in total accumulated system wide waiting time between one decision and the next, measured directly from the simulator rather than estimated, minus a small penalty tied to the worst starvation score currently observed. Simplicity here was a hard won lesson rather than a starting assumption, an earlier version of this reward (Section 2.6) used a dozen or more separately hand tuned terms, and untangling which term was actually driving a given behavior became close to impossible. Tying the reward directly to the same ground truth quantity the project is ultimately evaluated on turned out to make both training and debugging noticeably more tractable."),
  h3("Why PPO"),
  p("We trained the final agent using MaskablePPO, an extension of standard Proximal Policy Optimization that is aware of action masking: when an action is structurally disallowed in a given state (for instance, switching an empty intersection), the masked probability is properly excluded from the policy's own distribution rather than merely blocked after the fact. We considered Deep Q Networks as an alternative, an earlier, parallel DQN implementation exists in this project's codebase and is described in Section 2.3 above, with a fuller note in Section 2.8, but PPO's clipped policy updates and built in early stopping on excessive KL divergence gave us two independent safeguards against the kind of violent, single update policy collapse that had already cost us real time earlier in the project (see the V3.3 incident in Section 2.6). Those safeguards mattered more to us, in practice, than any small efficiency argument in either algorithm's favor."),
];

const section2_pivot = [
  h2("2.3 From the Original Plan to What We Actually Built"),
  p("It is worth being direct about how far the delivered project sits from the Phase A proposal, since the difference is significant and we would rather explain it plainly than let it surface as an unexplained gap. The original proposal described a complete perception to decision pipeline: YOLO for real time vehicle detection and classification, DeepSORT for persistent multi object tracking across occlusion, a Deep Q Network agent making the phase decisions, a dedicated Priority Protocol guaranteeing zero delay for emergency vehicles, a Rule Based Safety Layer and Historical Data Fallback Mode, and a cloud hosted web dashboard (FastAPI, a managed PostgreSQL database, deployed on Render) for live monitoring. Phase A's own success criteria were correspondingly broad: at least a 20% reduction in average waiting time, at least a 15% reduction in maximum queue length, detection accuracy above 90% (95% for emergency vehicles), sub 100 millisecond processing latency, and zero delay emergency preemption in 100% of test cases."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "phaseB_deployment_diagram.png")), transformation: { width: 380, height: 357 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.0c: the Deployment Diagram from our Phase A proposal, updated only to say \"Trained PPO Model\" in place of the original \"Trained DQN Model\" label, reflecting the algorithm change described later in this section, an IP camera and edge computer running the trained model and control logic on site, talking to a cloud hosted database and API server, with a browser dashboard for monitoring. We are showing this diagram here specifically because it was not implemented. None of the cloud infrastructure, the edge device, the IP camera, or the traffic light controller integration shown here exists in the delivered system. What we built instead is the ground truth simulation pipeline shown in Figure 2.0a.", { italics: true, size: 20 }),
  p("What we actually delivered is narrower and, in the one dimension we chose to go deep on, considerably more rigorously verified than the original plan called for: a single intersection reinforcement learning control policy, trained and evaluated using the SUMO simulator's own ground truth vehicle state rather than a vision based perception pipeline, with no priority protocol, no fallback mode, and no web dashboard. The computer vision layer (YOLO and DeepSORT), the emergency vehicle priority logic, and the cloud infrastructure described in Phase A were not implemented."),
  h3("Why the scope narrowed"),
  p("Two distinct reasons drove this, and we want to be honest that both were real rather than picking the more flattering one. The first was a deliberate research decision: the control policy question, given a reasonable traffic state, which phase should be green and for how long, is already a substantial research problem on its own, as the version history in Section 2.4 demonstrates at length. Bundling it together with an unsolved computer vision and tracking problem from the start would have made it far harder to tell, when something went wrong, whether the fault was in perception or in decision making. Isolating the control problem first, using ground truth state as a stand in for a perfect perception system, let us study it cleanly."),
  p("The second reason was circumstantial rather than planned: during the project timeline, both of us were called up for military reserves, which is compulsory once summoned and cannot be deferred on request, removing a significant and unpredictable block of development time with no advance warning. Faced with a real reduction in available time, we chose to protect the depth and rigor of the reinforcement learning work already underway, rather than spread the remaining time thinly across vision, tracking, priority logic, and cloud infrastructure and risk finishing all of them shallowly, with nothing brought to a genuinely complete, demonstrable state. We see this as two distinct phases of the same project: the decision making \"brain,\" the reinforcement learning policy itself, which we finished and evaluated rigorously, and the sim to real deployment layer, camera based perception, tracking, and physical integration, which remains the natural next phase rather than something we attempted and abandoned. We think this was the right trade off under the circumstances, and we say more about it directly in Section 2.6."),
  h3("Algorithm choice within the narrowed scope: DQN to PPO"),
  p("Separately from the scope reduction above, we also changed which reinforcement learning algorithm served as the project's primary approach. An early Deep Q Network implementation exists in the project's codebase, operating on the same kind of ground truth state described above rather than on vision input, with its own environment, a substantially more complex, multi term reward function, and its own training pipeline."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "phaseA_dqn_architecture.png")), transformation: { width: 410, height: 201 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.0d: the DQN network originally planned in Phase A, a small fully connected network mapping a 5 value queue state (one count per approach, plus current phase) to two output actions, Keep Phase or Switch Phase. We are showing the planned network for reference. The DQN implementation actually built and evaluated (Section 2.8) grew this to a 10 dimensional input and a substantially more complex, multi term reward, not the simple version shown here.", { italics: true, size: 20 }),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_decision_loop_diagram.png")), transformation: { width: 360, height: 276 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.0e: the activity diagram of the decision loop as it actually runs today, PPO_Agent's replacement for the planned DQN pipeline above. There is no YOLO detection, no DeepSORT tracking, no Priority Protocol, and no Fallback Mode here, since none of those were built (Section 2.3). Every box in this diagram corresponds to a real step inside sumo_rl_env_V8.py, and the hard action mask (\"Mask out Switch\") is the structural safety constraint described throughout this section, not the simple two branch action space Phase A originally planned.", { italics: true, size: 20 }),
  p("The DQN implementation was evaluated against a fixed time baseline many times over its development, and the full log of those evaluations survives in the project's own data files. We show that log directly, because what it reveals is not simply \"DQN was a bit worse than PPO,\" it is that DQN's own result, run to run, was not consistent enough to trust. Thirty four logged evaluation runs exist (a thirty fifth, synthetic sanity check entry is excluded), all on the same fixed random seed, spanning three intersection configurations across roughly three weeks. Their improvement over the fixed time baseline ranges from a best case of essentially eliminating waiting time (99.6% better) to a worst case of roughly 1,380 times more total waiting time than doing nothing (about negative 137,858%). The median run, 34.8% better than baseline, looks respectable in isolation. The mean across all thirty four runs is a meaningless negative 4,046%, dragged there by a handful of catastrophic outliers, which is itself the point: a metric whose mean and median disagree this violently is not describing a reliable controller."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "dqn_inconsistency_chart.png")), transformation: { width: 500, height: 250 } })], { alignment: AlignmentType.CENTER }),
  p("How to read this chart: each dot is one real test of the DQN controller, our earlier reinforcement learning approach, against an ordinary fixed timer traffic light, run at a different point during its development. The vertical axis is percent improvement over the fixed timer, so a dot above the black horizontal line means DQN did better than the fixed timer that test, and a dot below the line means it did worse, sometimes far worse. The axis is compressed (a log scale) purely so that both the good results near the top and the extremely bad results far below can appear on the same chart at all. Without compressing it, the worst dot would sit thousands of times further down the page than shown here.", { italics: true, size: 20 }),
  p("Figure 2.1: every logged DQN vs. fixed time baseline evaluation, in chronological order. Blue points beat the fixed timer baseline. Red points did worse than it. Gray points were logged with exactly zero DQN waiting time, which we treat as a likely failed or aborted run rather than a genuine perfect result, not a real success. Notice how scattered the outcome is from one test to the next, good results and severe failures appear side by side throughout the project's history, which is the opposite of the steady, predictable pattern the PPO agent's own charts show in Section 2.7.", { italics: true, size: 20 }),
  p("Counting the runs rather than only the extremes: 23 of the 34 logged runs beat the fixed time baseline outright, 4 performed worse than the baseline (one of them, the negative 137,858% case above, coincides with the same run's own log noting the DQN agent hit its time limit with 411 vehicles still stuck on the map, a genuine gridlock, not a rounding artifact), and 7 were logged with exactly zero DQN waiting time, which across a real, non trivial traffic scenario reads as a failed or crashed evaluation rather than a perfect controller, so we do not count them as successes either. We did not exclude any of these from the chart or from this count. Every logged run appears above, good and bad alike."),
  p("This was not an agent we could safely put in charge of an intersection: the honest average across all thirty four logged runs is negative 4,046% versus the fixed time baseline, driven by a recurring failure mode where certain approaches were starved almost entirely in favor of others, with nothing in the DQN agent's own logic pulling it back out, despite more than a dozen hand tuned reward terms already trying to discourage exactly that. PPO's clipped, on policy updates were materially more stable against the kind of violent policy collapse this project encountered more than once (Section 2.6), and its native support for action masking let us rule out unsafe behavior structurally rather than merely discourage it with a penalty, the same approach that later fixed the empty intersection switching problem. We view this as a documented methodological decision, not an abandoned line of work, the DQN implementation remains in the repository in full, and a rigorous, head to head comparison against it would be a natural next step for anyone continuing this project."),
];

const section2_process = [
  h2("2.4 Description of the Research Process"),
  p("The project did not progress in a straight line, and we think that is worth stating plainly rather than smoothing over. What follows is the actual sequence of major iterations, each one a fresh, from scratch training run rather than a continuation of the last, since changing the reward or observation definition partway through training and then resuming from an old checkpoint turned out, the hard way, to reliably corrupt the agent rather than improve it."),
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
      ["V9", "Tested whether a richer, less saturating observation would fix the remaining heavy traffic gap", "It did not, the gap turned out to be a demand ceiling, not a perception problem (Section 2.7)"],
    ],
    [1800, 4200, 3000]
  ),
  p("A full account of exactly what changed between each version, and the reasoning behind each change, is preserved in the project's version history document rather than repeated here in full. The table above is the condensed arc of it."),
  p("Once V8 emerged as a genuine improvement over every baseline, the project's center of gravity shifted from \"can we build something better\" to \"how sure are we, actually.\" That shift is arguably where the more interesting research work happened. We progressively escalated how rigorously we verified each claim: starting from a couple of fixed seeds used throughout early development, to five, then fifty independently drawn seeds when a specific comparison needed more statistical confidence, and finally to a fully unfiltered methodology in which every single saved checkpoint of a training run is evaluated against its own freshly drawn random seed and traffic scenario, nothing reused, nothing cherry picked, and no unfavorable result excluded from the reported summary. A checkpoint here is a saved copy of the agent's weights, written automatically every 100,000 training steps, so a full 6 million step training run produces 60 checkpoints, an evenly spaced record of the agent's progress from the start of training to the end, not just its final state. That last methodology is what eventually let us say, with real confidence rather than a hopeful headline number, that our champion agent beats all three fixed time baselines on 53 of 60 independently random evaluations (88.3%), and that its few losses are narrow, single digit percent misses against only the toughest baseline in light traffic, not the kind of catastrophic failure we had seen and had to fix in earlier versions."),
  p("That same rigorous methodology, turned on a second, independently trained run of the identical recipe, also produced one of the project's more sobering findings: a second run is not guaranteed to reproduce the first one's quality at all. We return to this in Section 2.7, since it materially changed how we now think about what \"training for longer\" actually buys us."),
];

const section2_tools = [
  h2("2.5 Tools Used and Client Interaction During Development"),
  p("The simulation itself runs on SUMO (Simulation of Urban Mobility), driven through the sumo-rl and TraCI/libsumo interfaces from Python. Training uses Stable-Baselines3 and its sb3-contrib extension for the maskable variant of PPO, with vectorized, parallel environments (ten simultaneous SUMO instances during training) to make reasonable use of available CPU. Evaluation and analysis lean on pandas, matplotlib, and seaborn. The interactive comparison tooling differs by agent: the PPO agent's is a single FastAPI web application plus a small hand written HTML/CSS/JavaScript frontend, including a floating guided tour that walks a new user through every field. The DQN agent's is a plain Tkinter desktop application. Both are deliberately kept dependency light rather than pulled into a larger framework."),
  p("Rather than a single formal client, this project was steered through frequent, hands on review sessions in which the current state of the agent was shown directly, live, rather than described in a status report. This is the entire reason the two graphical comparison tools exist: picking a model, a traffic scenario, and a seed, including one typed in on the spot and never seen before, and watching the result immediately, is a far more convincing way to demonstrate progress than a static slide of numbers. The \"Watch Live\" feature, an actual SUMO visualization window showing the intersection and the agent's decisions in real time, exists specifically for this kind of on demand demonstration."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "poster_sumo_preview.png")), transformation: { width: 500, height: 237 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.0f: a live screenshot of SUMO's own graphical window during a Watch Live session, the same view a reviewer sees when we demonstrate the agent, showing the actual intersection geometry, real vehicles (yellow), and the current signal phase (the red and green bars on the approach lanes).", { italics: true, size: 20 }),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "webapp_screenshot.png")), transformation: { width: 430, height: 328 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.0g: the comparison web app itself, mid comparison, showing a completed run (PPO_Agent_V8 against the Fixed_45s baseline, medium traffic, seed 732846) with the results table and bar chart it produces. This is a real screenshot of the delivered application, not a mockup.", { italics: true, size: 20 }),
  h3("FlowGrid_Web, a second interface built for this phase"),
  p("This phase also delivered FlowGrid_Web, a fully independent SaaS style traffic operations dashboard (its own dedicated backend, multi junction navigation, login, device settings, reports, user management) demonstrating what an eventual, fully deployed version of this system could look like to a traffic authority operator. Every screen is a real, working UI, but for every junction except one, the data behind it is simulated demonstration data. The one exception is deliberate: \"Live Junction (SUMO Simulation)\" is wired directly to the same trained PPO agent and SUMO simulator described throughout this book, with a \"Run Agent\" control (scenario only, a random seed chosen automatically) that launches a real, paced SUMO episode and streams back live per direction queue counts, signal colors, and a snapshot image from the running SUMO window, the same simulation shown in Figure 2.0f."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "phaseA_usecase_diagram.png")), transformation: { width: 400, height: 296 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.0h: the Use Case Diagram from our Phase A proposal, unchanged from the original: a User actor with Log In, View Junction Data, Manage Devices Settings, and Switch Between Modes, and an Admin actor, extending User, adding Configure Direction and Traffic Signals, View Reports, and Manage Users. Unlike Figures 2.0c and 2.0d above, this one no longer needs a blanket \"not implemented\" caveat: FlowGrid_Web implements every one of these eight use cases as a real, clickable screen. What still separates it from a fully deployed system is the data behind those screens, real and live only for View Junction Data on \"Live Junction (SUMO Simulation),\" simulated everywhere else, including Log In itself, which accepts two fixed demo accounts rather than a real authentication server.", { italics: true, size: 20 }),
  p("A recorded video walkthrough of the system, including a live Watch Live session and the comparison app end to end, is available at https://drive.google.com/file/d/1BE3oeGWWbVrQEC_ZL0rVh5AdPs9kDNTY/view."),
];

const section2_challenges = [
  h2("2.6 Challenges and the Solutions We Found"),
  p("Several distinct problems recurred throughout the project, and most of them are more general lessons about reinforcement learning than quirks of this particular intersection."),
  h3("Reward hacking via simulator artifacts"),
  p("The very first working version of the agent appeared, briefly, to be doing extremely well, until we noticed it was achieving that by deliberately starving certain lanes long enough that SUMO's own vehicle teleportation safety feature (which removes a vehicle that has waited an unreasonably long time, to keep the simulation from stalling) would kick in and delete those vehicles from the simulation entirely. Waiting time attributed to a vehicle that no longer exists is, from the reward function's point of view, waiting time that never happened. The fix was simple in hindsight, permanently disable teleportation in the simulator configuration, but finding it required actually watching the agent's behavior rather than trusting the reward curve, which was climbing steadily the entire time this was happening."),
  h3("Gradient explosions from an unbounded penalty"),
  p("An early reward design used an exponentially growing starvation penalty with no upper limit, on the reasoning that truly excessive waiting should be punished much more severely than mild waiting. In practice, values in the thousands occasionally appeared in the reward signal and destabilized training outright. Capping the penalty at a fixed maximum resolved the numerical instability, though the underlying reward design was still eventually replaced altogether (see below)."),
  h3("A \"dynamic minimum green\" rule that fired on the wrong signal"),
  p("One version let the agent switch earlier than the standard minimum green time whenever the current phase appeared to have very few vehicles left, measured by live vehicle counts on that phase's lanes. This had a structural flaw: while a phase is green, its own vehicles are moving rather than halting, so a live count on a green phase reads as nearly empty almost by construction. Trained further on this bug, the agent fully committed to exploiting it: certain phases switched at the earliest possible moment every time, others held for the maximum duration, and starved phases waited over 17,000 seconds in the worst cases, the single worst result in the project's history. Only a fresh agent trained from random initialization resolved it, the general lesson we applied for the rest of the project: resuming training after a meaningful rule change risks reinforcing a bug rather than correcting it."),
  h3("A reward with almost no gradient in light traffic"),
  p("A version whose reward was simply the reduction in total waiting time performed acceptably in moderate and heavy traffic but could not learn to handle light traffic at all. The reason became clear once we looked at it directly: with very few vehicles present, the change in total waiting time between one decision and the next is close to zero almost regardless of what the agent does, which gives it almost no signal to learn from in exactly the condition where learning was needed most. Adding a starvation based penalty term, one that responds to how long a lane's single longest waiting vehicle has been sitting there, rather than to an aggregate that can trivially stay near zero, supplied a meaningful gradient even when overall traffic was sparse, and light traffic performance improved roughly fifteen fold in the version where this was introduced."),
  h3("The camera range trade off"),
  p("Limiting the agent's observation to a fixed distance from the stop line, meant to model a realistic sensor rather than an omniscient one, initially caused a regression in heavy traffic: queues that extended past the visible range were effectively invisible, so the agent under reacted to congestion it could not see building up. We tested whether a richer, non saturating way of encoding the same observation would help, it did not, which is discussed further in Section 2.7, and ultimately resolved the regression by extending the visible range rather than changing what was done with it."),
  h3("An idle intersection that still wanted to switch"),
  p("Even once most other issues were resolved, the agent would occasionally switch phases at a completely empty intersection for no discernible benefit, apparently because nothing in its training had ever taught it that doing so was pointless. A soft penalty for this behavior was tried first and was simply too weak to compete with the main reward signal. The eventual fix removed the option outright: switching is now a structurally masked, unavailable action whenever no vehicle is visible to any camera, regardless of what the policy itself would otherwise prefer. This turned out to be the single change that took the agent from \"beats some baselines\" to \"beats every baseline in every tested condition,\" and the general principle, enforce a genuine constraint structurally rather than discourage it with a penalty, is one we would apply earlier if we did this again."),
  h3("A scope reduction caused by military reserves"),
  p("Section 2.3 describes this in full: the computer vision and tracking layer (YOLO and DeepSORT) proposed in Phase A was not implemented, in part because both of us were called up for military reserves, removing a significant, unplanned block of development time. We chose to protect the depth of the reinforcement learning work rather than implement the vision pipeline shallowly, and we are transparent about that trade off rather than treating it as a hidden gap."),
  h3("Confirming the evaluation methodology was actually trustworthy"),
  p("Before relying on any comparison between controllers, we verified, rather than assumed, that SUMO's seeded vehicle generation is genuinely deterministic: the same seed reliably produces a bit for bit identical stream of vehicles regardless of which controller is driving the signal, across separate process runs and even across different days. This property is what makes a \"paired\" comparison between our agent and a baseline meaningful in the first place, and we would not have trusted the comparisons in this project without having checked it directly."),
  h3("Wasted simulation time, and a training run that never fully settled"),
  p("Late in the project we noticed that evaluation episodes kept running long after a scenario's road had genuinely emptied out, since episodes were originally terminated only by a fixed simulated time limit rather than by traffic actually clearing. Adding an early exit condition, stop the moment no vehicle remains and none are still expected to arrive, cut typical evaluation time by roughly seven to eight times with no change whatsoever to the reported results, since nothing further can happen on an empty road either way."),
  p("Separately, we investigated whether training longer than our original budget would reliably improve the agent, after an initial, mistaken impression that a shorter second run had performed worse simply for being shorter. Its checkpoint history told a more specific story: even at 99% through its schedule, a checkpoint could still sit between two much better neighbors ten thousand steps away, consistent with a fixed, never decaying exploration noise setting still perturbing the policy. Training a fresh agent for twice the original budget confirmed it: it did not exceed the original's quality, and a second collapse appeared partway through. We consider this a useful negative result: more training time is not automatically safer under an exploration setup that does not itself decay."),
];

const section2_results = [
  h2("2.7 Results and Conclusions"),
  p("The project's central goal, an agent that beats fixed time control across light, moderate, and heavy traffic, was achieved and independently verified rather than taken on faith. Our champion agent reduces total waiting time by roughly 50% in light traffic, 36% in moderate traffic, and 8% in heavy traffic, each measured against the best performing fixed time baseline for that condition. Under the project's most rigorous test, every saved training checkpoint evaluated against its own independently drawn random seed and scenario, with no result excluded or reused, the champion agent beat every one of the three fixed time baselines outright in 53 of 60 cases (88.3%), and its remaining losses were narrow, single digit percentage misses against only the single toughest baseline in light traffic, never a broad or catastrophic failure."),
  p("The three charts below are the same evidence base behind that headline number, shown directly rather than only summarized, and the first and third are the same figures used on the project poster. In every chart on this page, the red line or red dots are PPO, our own agent, the one this project actually delivers, being directly measured against ordinary fixed timer traffic lights (the blue, orange, and green lines, one for each fixed cycle length we tested). In every case, lower on the chart means less time cars spent waiting, so lower is better, and a PPO line sitting below the fixed timer lines means our agent is outperforming them."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_checkpoint_waittime_scatter.png")), transformation: { width: 500, height: 250 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.2: total waiting time at every training checkpoint of our champion PPO agent (red), tested against three fixed timer baselines (blue, orange, green) under identical conditions, with one independently drawn random seed and traffic scenario used per checkpoint so nothing here was cherry picked. The vertical axis is compressed (a log scale) only so that both light and heavy traffic, which differ enormously in scale, can be shown on one chart. It does not change the conclusion, which is simple: PPO (red) starts out roughly tied with the fixed timers, drops sharply within the first few hundred thousand training steps as it learns, and then stays below all three fixed timer lines for essentially the rest of training, in light, moderate, and heavy traffic alike (solid, dashed, and dotted lines respectively). This is the agent visibly getting better with practice, and then reliably beating the alternative it was trained to replace.", { italics: true, size: 20 }),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_win_rate_scatter.png")), transformation: { width: 500, height: 215 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.3: the same 60 checkpoints as Figure 2.2, now shown as a single number per checkpoint, percent improvement over one specific fixed timer baseline (Fixed_60s), split by traffic condition (green, orange, and red dots for light, moderate, and heavy traffic). A dot above the black zero line means PPO beat the fixed timer at that point in training. A dot below means it lost. Aside from two early checkpoints, in the first half million steps of training, before the agent had learned very much yet, nearly every dot for the rest of training sits above the line, which is the direct, checkpoint by checkpoint evidence behind the 88.3% win rate reported above, and stands in direct contrast to Figure 2.1's DQN chart, where losing dots keep reappearing throughout the entire project rather than settling down early and staying resolved.", { italics: true, size: 20 }),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "ppo_medium_scenario_progress.png")), transformation: { width: 480, height: 247 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.4: the same comparison as Figure 2.2, but for moderate traffic only, using an ordinary (non compressed) vertical axis, which makes the shape of the improvement easier to see at a glance than the log scale charts above: PPO's blue line starts out far above all three fixed timers, meaning it initially performs worse, then falls sharply and settles in below every fixed timer (orange, green, red flat lines) for essentially the entire rest of training. This is the same underlying story as Figure 2.2, told at a scale a reader unfamiliar with log axes may find easier to follow directly.", { italics: true, size: 20 }),
  p("The remaining gap in heavy traffic was the subject of a dedicated investigation. We hypothesized that the agent's camera limited observation was \"saturating\" under heavy demand, every input reading effectively maxed out, leaving the policy unable to distinguish one badly congested state from another, and tested this directly by training an otherwise identical agent with a richer, non saturating encoding of the same information. It performed identically to the original, checkpoint for checkpoint. We concluded that this gap reflects a genuine demand ceiling, queueing physics as arrivals approach the intersection's physical service capacity, rather than a perception limitation, and that closing it further would likely require coordinating with neighboring intersections."),
  p("A second, unplanned but genuinely valuable result came from directly testing whether training for longer improves the agent. It does not, reliably: a fresh agent trained for twice the original step budget scored 77.4% on the same rigorous evaluation, meaningfully below the original champion's 88.3%, despite twice the training experience. We traced part of the reason to how the learning rate schedule is defined relative to the requested training length, and consider the likely remaining cause a fixed exploration noise setting that never decreases across training. Both are concrete, addressable design choices for future work, not a fundamental ceiling on what this approach can achieve."),
];

const section2_lessons = [
  h2("2.8 Lessons Learned"),
  p("If we were repeating this project from the beginning, several things would change. We would enforce genuine physical or logical constraints structurally, through action masking, from the very first version, rather than attempting to discourage undesired behavior through a penalty term and only reaching for a hard constraint once the penalty had already been shown to fail, the empty intersection switching problem cost more iteration time than it needed to for exactly this reason. We would also introduce our full, rigorous, unfiltered evaluation methodology much earlier in the project rather than escalating into it gradually. Several early \"this version is clearly better\" conclusions, based on only one or two fixed seeds, turned out to be considerably less certain once tested properly, and an earlier commitment to rigor would likely have saved iteration cycles rather than costing them."),
  p("We would also treat \"train it for longer\" with far more skepticism from the outset. It is an intuitive, low effort thing to try, and it is not obviously wrong, but we now have direct, controlled evidence that it does not reliably help under this project's specific training setup, and we would have preferred to reach that conclusion earlier rather than midway through the project."),
  p("On balance, we believe we approached the project's central risk, an agent that looks good on paper but is not actually trustworthy, correctly, by consistently choosing to build more rigorous verification tooling rather than accepting an encouraging headline number at face value. That discipline is, in our view, the most transferable outcome of this project, independent of the specific traffic control results."),
  h3("A brief note on the DQN alternative"),
  p("An earlier, parallel implementation of a Deep Q Network agent for the same general problem exists in this project's codebase, using a somewhat richer, more heavily hand tuned reward function (over a dozen separate weighted terms, covering throughput, fairness between approaches, and anti flicker penalties, among others) against a smaller 10 dimensional observation. It was not carried forward to the same level of rigorous, seed verified evaluation as the PPO line of work described above, and we do not have a formal, apples to apples comparison between the two to report. We consider this an honest gap in the project's coverage rather than evidence that DQN itself underperforms here, and it would be a reasonable next step for anyone continuing this work."),
];

const section2_metrics = [
  h2("2.9 Did We Meet Our Project Metrics?"),
  p("Our Phase A proposal defined six quantitative success criteria, and honesty requires reporting against every one of them, not only the ones the project ended up addressing. The table below does that directly."),
  simpleTable(
    ["Phase A success criterion", "Target", "Outcome"],
    [
      ["Average waiting time reduction", "At least 20% vs. a fixed time baseline", "Exceeded for two of three traffic conditions, 50% (light traffic) and 36% (moderate traffic). 8% in heavy traffic, independently verified across many random seeds rather than a single run"],
      ["Maximum queue length reduction", "At least 15%", "Not separately measured. Our evaluation reports total waiting time rather than maximum queue length as the primary metric"],
      ["Detection accuracy (mAP)", ">90% standard vehicles, >95% emergency vehicles", "Not applicable, the computer vision component was not implemented (Section 2.3)"],
      ["Real time processing speed", ">30 to 45 FPS, under 100ms latency", "Not applicable, no vision pipeline was implemented"],
      ["Emergency vehicle delay", "0 seconds in 100% of test cases", "Not implemented, no Priority Protocol or emergency vehicle class exists in the delivered system"],
      ["Fallback mode activation", "Within one signal cycle of a detected sensor failure", "Not applicable, no sensor input or fallback mode exists in the delivered system"],
    ],
    [3200, 2600, 3200]
  ),
  p("Put plainly: the single criterion that concerned the control policy itself, reducing average waiting time by at least 20% against a fixed time baseline, was not only met but exceeded in two of the three traffic conditions we tested, and the one condition where it was not exceeded (heavy traffic, an 8% reduction) was investigated specifically rather than left unexplained (Section 2.7). The remaining five criteria all concerned the computer vision, priority protocol, and infrastructure components described in Phase A, which, as Section 2.3 explains, were not implemented within this project's delivered scope. We would rather report this gap plainly than describe the project's success only in terms of the criterion we did address."),
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
  p("What Watch Live actually opens: SUMO's own simulation window, showing the real intersection geometry, vehicles (yellow), and the current signal phase (red/green bars on each approach). Same view as Figure 2.0f in the main book.", { italics: true, size: 20 }),
  h3("A.5.7 Running the Comparison"),
  p("Click \"Start Comparison.\" A progress indicator tracks how many of the required simulation runs have completed (models x baselines x seeds x scenarios). Runs execute in parallel across multiple CPU cores unless Watch Live is active, in which case they run one at a time so the visualization stays meaningful."),
  h3("A.5.8 Reading the Results"),
  p("Once complete, a results table appears for each tested scenario, listing every selected model and baseline with its total waiting time for each seed and an overall average. The best performing entry in each table is highlighted, and a bar chart beneath the table gives the same comparison visually. Lower total waiting time is better."),
  para([new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, "webapp_screenshot.png")), transformation: { width: 440, height: 336 } })], { alignment: AlignmentType.CENTER }),
  p("A real completed comparison: PPO_Agent_V8 against the Fixed_45s baseline, medium traffic, seed 732846. PPO_Agent_V8 is highlighted green as the winner (lower total waiting time), and the bar chart below the table repeats the same comparison visually. Same view as Figure 2.0g in the main book.", { italics: true, size: 20 }),
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
  p("To be direct about the boundary: \"Live Junction (SUMO Simulation)\" is real. Its queue counts, signal colors, and camera image come from an actual SUMO episode driven by the trained PPO agent, the same one evaluated throughout the book. Every other junction, every login, and every other feature (device settings, reports, user management, adding a junction) is a complete, working UI backed by simulated or randomly generated demonstration data, not a live backend, database, or camera. We built it this way deliberately, to demonstrate the target system's shape honestly without claiming a deployment that does not exist. See the book, Section 2.3 and Section 2.5, for the full reasoning."),
  h2("A.7 Using the DQN Tools (Original Agent, Archived)"),
  p("DQN_Agent is the project's original reinforcement learning approach. It predates PPO_Agent and is preserved, fully runnable, under Old_Versions/DQN_Agent since PPO_Agent is the current submitted agent. See the book (Section 2.3) for why the project moved from DQN to PPO."),
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
      ["Low", "Light, sparse traffic", "Whether the agent can find a useful signal to act on when very few vehicles are present (an early failure mode of this project, see the book Section 2.6)"],
      ["Medium", "Moderate, steady traffic", "Typical day to day operating conditions"],
      ["High", "Heavy, near saturating traffic", "Behavior as demand approaches the intersection's physical capacity, where every controller's performance converges (see the book Section 2.7)"],
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
  p("Never resume training from an existing checkpoint after changing the reward function or observation definition. Train a fresh agent from random initialization instead. This project encountered a full, unrecoverable policy collapse from doing exactly this once (see the book, Section 2.6). It is documented there as a cautionary example, not a theoretical risk."),
  h3("Where do I find the raw evaluation numbers behind the book's claims?"),
  p("PPO_Agent/results/final_random_seeds_20260705_005802/ contains the full, unfiltered evaluation (summary.txt, final_results.csv) behind the 88.3% win rate figure reported in the book. Old_Versions/DQN_Agent/results/comparison_history.json contains the equivalent raw evaluation history for the DQN agent, discussed in the book's Section 2.3."),
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
  p("Figure B.1: the training and simulation core (PPO_Agent/scripts/train_V8.py + sumo_rl_env_V8.py). SubprocVecEnv runs ten parallel SUMO instances. VecNormalize tracks running observation statistics. The SwitchOrKeepWrapper is the actual translation layer between raw SUMO state and the agent's 21 dimensional observation, and between the agent's action and SUMO's TraCI control commands. Same diagram as Figure 2.0a in the main book.", { italics: true, size: 20 }),
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
  warning("Never resume training after changing the reward function or observation definition. Load the old checkpoint, keep the old environment definition, or start fresh from random initialization. Never mix an old checkpoint with a changed environment. This produced a full, unrecoverable policy collapse once during this project (documented in the book, Section 2.6, the V3.3 incident)."),
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
  warning("CORSMiddleware here allows all four of 127.0.0.1/localhost times 5173/8001, not just the Vite dev origin. Once this same server also serves the built frontend (Section B.6.4), the page can be loaded as either http://127.0.0.1:8001 or http://localhost:8001, and the frontend's fetch() calls are hardcoded to http://127.0.0.1:8001. If the page happened to load via the \"localhost\" hostname, that pairing is a different origin to the browser even though it is the same machine and the same port, and the preflight OPTIONS request fails with 400 unless that exact origin is also allowed. Missing this is an easy way to reintroduce a \"why does Run Agent silently fail\" bug."),
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
  warning("Tour.jsx's auto start effect deliberately does not gate on whether target refs are already populated at mount time. React's StrictMode double invokes effects in development, which briefly detaches and reattaches refs. A closure that captured \"zero valid steps\" at that exact instant would permanently latch onto that stale value, since the effect never runs a second time. The render itself already guards on a missing step by rendering nothing, so the fix is simply not to gate the timer on ref readiness at all."),
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
  p("The reward function (in flowgrid/core/, referenced from the DQN training loop) sums roughly a dozen hand tuned terms (diff wait, absolute wait penalty, spillback penalty, throughput bonus, fairness terms, anti flicker penalty, invalid action penalty). See PROJECT_OVERVIEW.md Section 3 for the exact formula and coefficients, and the book Section 2.3 for why this reward's complexity, and the resulting instability documented in Old_Versions/DQN_Agent/results/comparison_history.json, motivated the move to PPO."),
  h2("B.8 Retraining or Extending the PPO Agent"),
  p("To train a new version, copy PPO_Agent/scripts/ (and the model files, if building on an existing one) into a new folder under Old_Versions/PPO/ rather than modifying PPO_Agent/ in place. This preserves the current submitted agent as a working reference and follows the same \"copy, don't mutate\" convention used throughout this project's version history (see the archived V4 through V9 folders, each a fresh copy rather than an in place edit of the previous one)."),
  bullet("Copy sumo_rl_env_V8.py to a new file with an updated name. Update the sumo_rl_env.py shim's import to point at it."),
  bullet("Copy train_V8.py and evaluate_V8.py. No path edits are needed if the new folder sits at the same depth, since the training step count and other hyperparameters are already command line arguments."),
  bullet("Never resume training an existing checkpoint after changing its reward function or observation definition. Train a fresh agent from random initialization instead."),
  h2("B.9 Adding a New Baseline or Comparison Target"),
  p("New fixed time or rule based baselines can be added by extending AVAILABLE_BASELINES in comparison_core.py. Each baseline needs only a name and, for fixed time controllers, a cycle length, since the comparison tools handle result collection and reporting generically through evaluate_models.py's existing \"fixed\" model type. Max Pressure (model type \"mp\" in evaluate_models.py) is not registered in AVAILABLE_BASELINES. It was never successfully integrated as a reliable comparison baseline on this network (see the book, Section 2.6), so it does not appear in the web app or comparison tooling."),
  h2("B.10 Running an Evaluation Sweep"),
  p("final_results_random_seeds.py and checkpoint_sweep.py both support a dry run flag that reports exactly how many simulation runs a given sweep will perform and how long it is expected to take, without executing anything. Always run this first before committing to a long sweep."),
  code("python final_results_random_seeds.py --version-dir .. --dry-run\npython final_results_random_seeds.py --version-dir .."),
  p("Sweeps write partial results incrementally as they progress (assignments.csv is written up front with the full plan, final_results.csv is appended to after every checkpoint completes). If interrupted, resuming with the flag shown below continues exactly where it left off using the original plan. The summarize only flag regenerates summary.txt and the charts from whatever rows already exist, without running anything new."),
  code("python final_results_random_seeds.py --version-dir .. --resume <out_dir>\npython final_results_random_seeds.py --version-dir .. --summarize-only <out_dir>"),
  h2("B.11 Testing and Verification Methodology"),
  p("This project's evaluation rigor escalated deliberately over its course, and the same escalation is worth reusing for any future work on this codebase rather than trusting an early, less rigorous result."),
  bullet("A couple of fixed seeds, used throughout early development for fast iteration."),
  bullet("Five, then fifty independently drawn seeds, when a specific comparison needed more statistical confidence."),
  bullet("Every saved checkpoint against its own freshly drawn random seed and scenario (final_results_random_seeds.py), nothing reused, nothing cherry picked, no unfavorable result excluded. This is what let the project report, with real confidence, that the champion agent beats all three fixed time baselines on 53 of 60 independently random evaluations (88.3%)."),
  p("Two properties of the environment make this methodology trustworthy rather than just elaborate: SUMO's seeded vehicle generation is genuinely deterministic (the same seed produces a bit for bit identical vehicle stream regardless of which controller is driving the signal, verified empirically across process restarts), and evaluation episodes now terminate as soon as the road is genuinely empty rather than running to a fixed time limit, which cut typical evaluation time by roughly seven to eight times with no change to the reported results."),
  h2("B.12 Known Limitations and Future Work"),
  bullet("Single intersection scope: this project controls one intersection. Multi intersection coordination is unattempted future work."),
  bullet("High traffic ceiling: performance near the intersection's physical demand capacity reflects queueing physics, not a perception limitation (ruled out directly by a V9 experiment with a richer, non saturating observation encoding, see the book, Section 2.7)."),
  bullet("Training is not reproducible run to run: two independent runs of the identical V8 recipe (V8 and V8_replicate) produced meaningfully different stability profiles. The leading hypothesis is the constant, non decaying entropy coefficient. This is a concrete, addressable item for future work, not a fully solved question."),
  bullet("Computer vision perception (YOLO + DeepSORT), proposed in the original Phase A plan, was not implemented in this delivered scope. See the book, Section 2.3, for the full explanation. It remains the most natural next step for extending this project toward real world deployment."),
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
      properties: {},
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
        ...section1,
        ...section2_intro,
        ...section2_solution,
        ...section2_pivot,
        ...section2_process,
        ...section2_tools,
        ...section2_challenges,
        ...section2_results,
        ...section2_lessons,
        ...section2_metrics,
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
