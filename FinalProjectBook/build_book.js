const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  PageBreak, TableOfContents, Header, Footer, PageNumber, ImageRun,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, convertInchesToTwip
} = require("docx");

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

const logoBuffer = fs.readFileSync("C:\\Users\\Einavs_PC\\Documents\\TrafficProject\\LOGO1.png");

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
  p("Two more \"adaptive\" families of controllers try to close that gap, and both show up as baselines in this project. Actuated controllers use loop detectors to extend or shorten a phase depending on whether vehicles are currently arriving, but they typically cannot see more than a short distance past the stop line, so they have little sense of how long a queue actually is once it grows past the detector. Max Pressure controllers, a more principled idea from the traffic engineering literature, try to always serve whichever phase currently has the greatest \"pressure\", roughly, more vehicles waiting to enter than are currently leaving, and come with a reasonable theoretical guarantee of network stability under fairly general conditions. We compared our agent against both fixed time cycles (30, 45, and 60 seconds) and Max Pressure, and, as described in Section 2.6, actually ended up learning something unexpected about where Max Pressure itself breaks down on our specific intersection geometry."),
  p("This project asks a more open question than \"which fixed cycle length is best\": could an agent that is never given an explicit rule at all, and instead learns purely from repeated, simulated experience of driving traffic through an intersection, learn to do this job better than either of the above? And where it does, or does not, we wanted to actually understand why, rather than accept a single headline number."),
  p("Reinforcement learning is a natural fit for this problem because it has exactly the shape RL is built to handle: an agent (the signal controller) observes some state (who is waiting, for how long, how the intersection currently looks from the camera's point of view), takes an action (hold the current phase, or advance to the next one), and receives feedback about whether that was a good decision, over and over, across thousands of simulated episodes. What makes the problem genuinely hard is also what makes it interesting: the \"right\" reward signal is not obvious (reward the absence of waiting? reward throughput? something else?), the environment is only partially observable (a real camera cannot see indefinitely far down the road), and, as this project demonstrated more than once, an RL agent can find a technically correct but practically wrong way to make its reward number go up without doing anything useful for an actual driver."),
  p("We built a dedicated single intersection SUMO (Simulation of Urban Mobility) environment to study this cleanly, before considering anything more ambitious, since most of the genuinely hard problems in this space, reward design, partial observability, exploration versus exploitation, and the risk of reward hacking, are already fully present at a single four phase intersection."),
  h2("1.1 Related Work"),
  p("Traffic signal control has evolved through several distinct generations, each addressing a limitation of the one before it, and our Phase A research surveyed this progression in some depth. The oldest and still most common approach, fixed time control, runs a rigid schedule derived from historical traffic counts (Koonce et al., 2008); it is predictable but, by design, blind to what is actually happening on the road at any given moment. Vehicle actuated control improves on this using inductive loop detectors embedded in the road surface, extending or ending a phase based on whether a vehicle is currently present, but this relies on binary presence detection rather than any real measure of traffic volume, and a single vehicle arriving on a minor approach can interrupt a heavy flow on a main road (Akçelik, 1994)."),
  p("A further generation of network wide adaptive systems moved beyond a single intersection's local logic. SCOOT models platoons of vehicles using upstream detectors and continuously adjusts split, cycle, and offset to maintain a coordinated \"green wave\" across a corridor (UK Department of Transport, 1995), while SCATS pursues an \"equisaturation\" philosophy, using stop line detectors to measure a Degree of Saturation and reallocate green time to balance load across competing approaches (Akçelik, 2010). Both are genuinely adaptive and both remain widely deployed, but neither learns in the machine learning sense; their logic is fixed by design, just responsive to live inputs rather than to a static clock."),
  p("A more recent and more ambitious line of research looks past physical signals altogether. Dresner and Stone (2008) proposed a reservation based Autonomous Intersection Management protocol in which vehicles negotiate directly with an intersection manager and weave through without ever stopping, and Liang et al. (2018) demonstrated a Vehicle to Infrastructure architecture feeding a high resolution grid state into a Double Dueling Deep Q Network. Both report large theoretical improvements, and both depend on a level of connected vehicle market penetration that does not exist today, which is precisely the gap our own project's original proposal set out to bridge with a \"camera as a sensor\" approach: real time object detection using YOLO (Redmon et al., 2016), persistent multi object tracking across occlusion using DeepSORT (Wojke et al., 2017), and a Deep Q Network decision agent in the tradition of Mnih et al. (2015), retrofitted onto existing intersections without waiting for future vehicle to infrastructure standardization. Wang et al. (2024) more recently validated a closely related \"camera as sensor\" co simulation framework, reinforcing that this remains an active and credible research direction rather than an abandoned one."),
  p("Our own project began, in its Phase A proposal, exactly here: a full perception to decision pipeline combining YOLO detection, DeepSORT tracking, and a DQN control agent. As Section 2.3 describes in full, the project's actual development narrowed this scope considerably, for reasons that were partly deliberate (isolating the control policy question from the perception question, to study each cleanly) and partly circumstantial (a team member's mandatory military reserve service reduced available development time during the project). What we are able to report on rigorously in this book is the control policy question in isolation, using the simulator's own ground truth vehicle state in place of a vision pipeline, evaluated far more exhaustively than the original proposal's success criteria called for. We consider the vision based perception layer proposed in Phase A to remain the natural and most valuable next step for this project, not a direction that was tried and found wanting."),
];

//                                                                            
// SECTION 2, DESCRIPTION OF WHAT WE ACHIEVED
//                                                                            
const section2_intro = [
  h1("2. Description of What We Achieved"),
  h2("2.1 General Description"),
  p("At a high level, this project set out to build and, just as importantly, rigorously evaluate a reinforcement learning agent capable of controlling a single traffic signal intersection more effectively than the standard alternatives already used in practice. \"More effectively\" meant, concretely, lower total vehicle waiting time across a range of traffic conditions, light, moderate, and heavy, since that is the number that actually matters to a driver sitting at a red light, and it is the number every baseline in this project is judged against."),
  p("The system we ended up with, which we call FlowGrid, is really three things working together. The first is a SUMO based simulation environment modelling one four way intersection with realistic, randomly generated vehicle demand, camera limited sensing (the agent only \"sees\" 150 meters back from the stop line, meant to represent what an actual roadside sensor could plausibly observe, not an omniscient view of the whole street), and a set of hard safety constraints, minimum and maximum green durations, mandatory yellow transitions, that no learned policy is ever permitted to violate, regardless of what it has learned. The second is the trained agent itself: a Proximal Policy Optimization (PPO) policy, trained from scratch with no hand coded switching rules, that decides every five simulated seconds whether to hold the current phase or advance to the next one. The third is a full evaluation and demonstration layer, two graphical applications (a desktop version and a browser based one), a family of statistical comparison tools, and a \"Watch Live\" mode that opens a real SUMO visualization window on demand, built specifically so the agent's performance could be checked, questioned, and shown to someone else, rather than simply trusted on the strength of one reported number."),
  p("The intended audience for this system splits naturally into two groups with different needs. Traffic engineers or municipal decision makers are the people who would actually weigh whether an RL based controller is worth piloting or deploying, and for them what matters most is the evaluation story: does it actually beat what is already in use, under which conditions, and how much confidence is really behind that claim. The second audience is anyone continuing this specific line of work, including ourselves, months from now, for whom what matters is the version history, the attempts that failed and precisely why, and tooling that makes it possible to test a new idea quickly rather than re derive all of this from first principles."),
];

const section2_solution = [
  h2("2.2 Solution Description, Research Approach"),
  p("Because this is a research track project, this section focuses on the algorithms and methodology behind the agent, rather than a conventional software architecture diagram, though the supporting software system is documented in full in the Maintenance Guide (Appendix B)."),
  h3("The decision problem, formally"),
  p("Every reinforcement learning problem reduces to a Markov Decision Process: a state the agent observes, an action it chooses, a reward it receives, and rules governing how the state evolves. Framing our own problem this way early on was one of the more clarifying steps in the project, since it forced explicit answers to questions that are easy to leave vague otherwise."),
  p("The state our final agent observes is a 21 dimensional vector, entirely normalized to the range [0, 1]: a one hot encoding of which of the four signal phases currently has the green light, how long that phase has already held green as a fraction of its allowed maximum, an occupancy density reading for each of eight lane groups (again, camera limited to 150 meters), and a starvation score per lane group capturing how long the single longest waiting vehicle in that group has been sitting there. That last piece deserves a note: an intersection can have a very reasonable looking average wait time while one unlucky vehicle in a rarely served lane waits far longer than anyone would consider acceptable, and the starvation term exists specifically so the agent cannot ignore that vehicle just because the aggregate numbers look fine."),
  p("The action space is intentionally small: hold the current phase, or switch to the next one in a fixed cyclic order. We do not let the agent jump directly to an arbitrary phase, early experimentation (described in Section 2.6) showed that a free jump action space encourages rapid, wasteful cycling through yellow transitions, and a cyclic structure removes that failure mode by construction rather than trying to penalize it away. On top of this action space sits a layer of hard, structural constraints, enforced outside the learned policy entirely: the agent is physically prevented from switching before a minimum green time has elapsed, is forced to switch once a maximum green time is reached regardless of its preference, and, critically, as covered below, is prevented from ever switching an already empty intersection."),
  p("The reward is deliberately simple: the reduction in total accumulated system wide waiting time between one decision and the next, measured directly from the simulator rather than estimated, minus a small penalty tied to the worst starvation score currently observed. Simplicity here was a hard won lesson rather than a starting assumption, an earlier version of this reward (Section 2.6) used a dozen or more separately hand tuned terms, and untangling which term was actually driving a given behavior became close to impossible. Tying the reward directly to the same ground truth quantity the project is ultimately evaluated on turned out to make both training and debugging noticeably more tractable."),
  h3("Why PPO"),
  p("We trained the final agent using MaskablePPO, an extension of standard Proximal Policy Optimization that is aware of action masking: when an action is structurally disallowed in a given state (for instance, switching an empty intersection), the masked probability is properly excluded from the policy's own distribution rather than merely blocked after the fact. We considered Deep Q Networks as an alternative, an earlier, parallel DQN implementation exists in this project's codebase and is described in Section 2.3 above, with a fuller note in Section 2.8, but PPO's clipped policy updates and built in early stopping on excessive KL divergence gave us two independent safeguards against the kind of violent, single update policy collapse that had already cost us real time earlier in the project (see the V3.3 incident in Section 2.6). Those safeguards mattered more to us, in practice, than any small efficiency argument in either algorithm's favor."),
];

const section2_pivot = [
  h2("2.3 From the Original Plan to What We Actually Built"),
  p("It is worth being direct about how far the delivered project sits from the Phase A proposal, since the difference is significant and we would rather explain it plainly than let it surface as an unexplained gap. The original proposal described a complete perception to decision pipeline: YOLO for real time vehicle detection and classification, DeepSORT for persistent multi object tracking across occlusion, a Deep Q Network agent making the phase decisions, a dedicated Priority Protocol guaranteeing zero delay for emergency vehicles, a Rule Based Safety Layer and Historical Data Fallback Mode, and a cloud hosted web dashboard (FastAPI, a managed PostgreSQL database, deployed on Render) for live monitoring. Phase A's own success criteria were correspondingly broad: at least a 20% reduction in average waiting time, at least a 15% reduction in maximum queue length, detection accuracy above 90% (95% for emergency vehicles), sub 100 millisecond processing latency, and zero delay emergency preemption in 100% of test cases."),
  p("What we actually delivered is narrower and, in the one dimension we chose to go deep on, considerably more rigorously verified than the original plan called for: a single intersection reinforcement learning control policy, trained and evaluated using the SUMO simulator's own ground truth vehicle state rather than a vision based perception pipeline, with no priority protocol, no fallback mode, and no web dashboard. The computer vision layer (YOLO and DeepSORT), the emergency vehicle priority logic, and the cloud infrastructure described in Phase A were not implemented."),
  h3("Why the scope narrowed"),
  p("Two distinct reasons drove this, and we want to be honest that both were real rather than picking the more flattering one. The first was a deliberate research decision: the control policy question, given a reasonable traffic state, which phase should be green and for how long, is already a substantial research problem on its own, as the version history in Section 2.4 demonstrates at length. Bundling it together with an unsolved computer vision and tracking problem from the start would have made it far harder to tell, when something went wrong, whether the fault was in perception or in decision making. Isolating the control problem first, using ground truth state as a stand in for a perfect perception system, let us study it cleanly."),
  p("The second reason was circumstantial rather than planned: during the project timeline, one or more team members were called up for mandatory Israeli military reserve duty (מילואים), which is compulsory, cannot be deferred on request, and removed a significant and unpredictable block of development time with no advance warning. Faced with a real reduction in available time, we chose to protect the depth and rigor of the reinforcement learning work already underway, rather than spread the remaining time thinly across vision, tracking, priority logic, and cloud infrastructure and risk finishing all of them shallowly. We think this was the right trade off under the circumstances, and we say more about it directly in Section 2.6."),
  h3("Algorithm choice within the narrowed scope: DQN to PPO"),
  p("Separately from the scope reduction above, we also changed which reinforcement learning algorithm served as the project's primary approach. An early Deep Q Network implementation exists in the project's codebase, operating on the same kind of ground truth state described above rather than on vision input, with its own environment, a substantially more complex, multi term reward function, and its own training pipeline."),
  p("The DQN implementation was, in fact, evaluated against a fixed time baseline many times over the course of its development, not just once, and the full log of those evaluations survives in the project's own data files. We think that log is worth showing directly rather than summarizing away, because what it shows is not simply \"DQN was a bit worse than PPO,\" it is that DQN's own result, run to run, was not consistent enough to trust. Thirty four logged evaluation runs exist (a thirty fifth, synthetic sanity check entry is excluded here), all on the same fixed random seed, spanning three different intersection configurations across roughly three weeks of development. Their improvement over the fixed time baseline ranges from a best case of essentially eliminating waiting time (99.6% better) to a worst case of the DQN agent producing roughly 1,380 times more total waiting time than doing nothing differently at all (an improvement figure of about negative 137,858%). The median run, 34.8% better than baseline, looks respectable in isolation; the mean across all thirty four runs is a meaningless negative 4,046%, dragged there entirely by a handful of catastrophic outliers, which is itself the point: a metric whose mean and median disagree this violently is not describing a reliable controller."),
  para([new ImageRun({ type: "png", data: fs.readFileSync("C:\\Users\\Einavs_PC\\Documents\\TrafficProject\\FinalProjectBook\\dqn_inconsistency_chart.png"), transformation: { width: 580, height: 290 } })], { alignment: AlignmentType.CENTER }),
  p("How to read this chart: each dot is one real test of the DQN controller, our earlier reinforcement learning approach, against an ordinary fixed timer traffic light, run at a different point during its development. The vertical axis is percent improvement over the fixed timer, so a dot above the black horizontal line means DQN did better than the fixed timer that test, and a dot below the line means it did worse, sometimes far worse. The axis is compressed (a log scale) purely so that both the good results near the top and the extremely bad results far below can appear on the same chart at all; without compressing it, the worst dot would sit thousands of times further down the page than shown here.", { italics: true, size: 20 }),
  p("Figure 2.1: every logged DQN vs. fixed time baseline evaluation, in chronological order. Blue points beat the fixed timer baseline; red points did worse than it; gray points were logged with exactly zero DQN waiting time, which we treat as a likely failed or aborted run rather than a genuine perfect result, not a real success. Notice how scattered the outcome is from one test to the next, good results and severe failures appear side by side throughout the project's history, which is the opposite of the steady, predictable pattern the PPO agent's own charts show in Section 2.7.", { italics: true, size: 20 }),
  p("Counting the runs rather than only the extremes: 23 of the 34 logged runs beat the fixed time baseline outright, 4 performed worse than the baseline (one of them, the negative 137,858% case above, coincides with the same run's own log noting the DQN agent hit its time limit with 411 vehicles still stuck on the map, a genuine gridlock, not a rounding artifact), and 7 were logged with exactly zero DQN waiting time, which across a real, non trivial traffic scenario reads as a failed or crashed evaluation rather than a perfect controller, so we do not count them as successes either. We did not exclude any of these from the chart or from this count; every logged run appears above, good and bad alike."),
  p("We want to be precise about what this data does and does not show. It is a single seed throughout, so it cannot separate \"DQN is inherently unstable\" from \"this particular seed happened to be unlucky for DQN\" the way the multi seed, multi checkpoint methodology used for PPO throughout this book can (Section 2.4). What it does show, credibly, is that across three different intersection layouts and roughly three weeks of iteration, the DQN implementation's evaluated performance never settled into the kind of narrow, predictable band that would let us trust a single reported number, whereas the PPO champion agent's equivalent evaluation, run under a far more demanding unfiltered methodology across many checkpoints and seeds, produced a tight, explainable result (Section 2.7). That difference in consistency, not only the difference in typical performance, is the honest reason PPO carried the project forward."),
  p("Put in plain terms rather than statistics: this was not an agent we could safely put in charge of an intersection. The average outcome across all thirty four logged runs, taken honestly rather than cherry picked, is negative 4,046% versus the fixed time baseline, meaning that on average, across everything we logged, the DQN controller left the intersection worse off than doing nothing at all, and by an enormous margin. That average is driven by a specific, recurring failure mode we saw repeatedly during development: certain approaches to the intersection would be starved almost entirely in favor of others, sometimes for the full length of an evaluation run, and once that pattern set in, nothing in the DQN agent's own logic pulled it back out. That is precisely the kind of behavior a reward penalty is supposed to discourage, and in our DQN implementation, more than a dozen separately hand tuned reward terms were already trying to discourage it, without reliably succeeding. We could not, in practice, control it."),
  p("Several factors drove the decision to carry PPO forward as the project's primary algorithm rather than continue tuning the DQN implementation. PPO's on policy, clipped update training is materially more stable against the kind of violent policy collapse this project encountered more than once (Section 2.6); and, critically, its native support for action masking let us stop trying to discourage lane starvation with a penalty and instead rule it out structurally, by making the unsafe action unavailable to the policy in the first place, the same hard constraint approach that later fixed the empty intersection switching problem described in Section 2.6. DQN's discrete Q value masking can approximate this, but nowhere near as directly as PPO's action masker, and by the time this became clear, PPO's evaluation history had already demonstrated the kind of narrow, repeatable, checkpoint over checkpoint consistency (Section 2.4, Section 2.7) that the DQN log above conspicuously lacks. Pragmatically, too, the reward function driving our DQN implementation had grown to more than a dozen separately hand tuned terms, which made it considerably harder to diagnose why a given result was good or bad compared to PPO's simpler, two term reward. We view this as a legitimate and documented methodological decision, not an abandoned line of work, the DQN implementation remains in the repository in full, and a rigorous, head to head comparison against it, using the same evaluation methodology applied to PPO throughout this book, would be a natural next step for anyone continuing this project."),
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
      ["V3.1 – V3.3", "Reverted to cyclic phases; dynamic minimum green rule added, then extended", "V3.3 fully collapsed: a broken dynamic green guard was reinforced over two million additional steps until it became the agent's entire strategy"],
      ["V4 (fresh)", "Reward tied directly to the change in total waiting time", "First version to beat any baseline at all, but still lost badly in light traffic"],
      ["V6 (camera) / V7", "Added a starvation penalty and a distance limited \"camera\" observation", "Fixed the light traffic case; introduced and then fixed a heavy traffic regression as camera range was tuned"],
      ["V8, champion", "Replaced a soft idle switching penalty with a hard rule: switching is structurally blocked at an empty intersection", "First agent to beat all three fixed time baselines across all three traffic conditions"],
      ["V9", "Tested whether a richer, less saturating observation would fix the remaining heavy traffic gap", "It did not, the gap turned out to be a demand ceiling, not a perception problem (Section 2.7)"],
    ],
    [1800, 4200, 3000]
  ),
  p("A full account of exactly what changed between each version, and the reasoning behind each change, is preserved in the project's version history document rather than repeated here in full; the table above is the condensed arc of it."),
  p("Once V8 emerged as a genuine improvement over every baseline, the project's center of gravity shifted from \"can we build something better\" to \"how sure are we, actually.\" That shift is arguably where the more interesting research work happened. We progressively escalated how rigorously we verified each claim: starting from a couple of fixed seeds used throughout early development, to five, then fifty independently drawn seeds when a specific comparison needed more statistical confidence, and finally to a fully unfiltered methodology in which every single saved checkpoint of a training run is evaluated against its own freshly drawn random seed and traffic scenario, nothing reused, nothing cherry picked, and no unfavorable result excluded from the reported summary. That last methodology is what eventually let us say, with real confidence rather than a hopeful headline number, that our champion agent beats all three fixed time baselines on 53 of 60 independently random evaluations (88.3%), and that its few losses are narrow, single digit percent misses against only the toughest baseline in light traffic, not the kind of catastrophic failure we had seen and had to fix in earlier versions."),
  p("That same rigorous methodology, turned on a second, independently trained run of the identical recipe, also produced one of the project's more sobering findings: a second run is not guaranteed to reproduce the first one's quality at all. We return to this in Section 2.7, since it materially changed how we now think about what \"training for longer\" actually buys us."),
];

const section2_tools = [
  h2("2.5 Tools Used and Client Interaction During Development"),
  p("The simulation itself runs on SUMO (Simulation of Urban Mobility), driven through the sumo-rl and TraCI/libsumo interfaces from Python. Training uses Stable-Baselines3 and its sb3-contrib extension for the maskable variant of PPO, with vectorized, parallel environments (ten simultaneous SUMO instances during training) to make reasonable use of available CPU. Evaluation and analysis lean on pandas, matplotlib, and seaborn; the interactive comparison tools are built with customtkinter for the desktop application and FastAPI plus a small hand written HTML/CSS/JavaScript frontend for the browser based one, deliberately kept dependency light rather than pulled into a larger frontend framework."),
  p("Rather than a single formal client, this project was steered through frequent, hands on review sessions in which the current state of the agent was shown directly, live, rather than described in a status report. This is, in fact, the entire reason the two graphical comparison tools exist at all: being able to pick a model, pick a traffic scenario, pick a seed, including a seed typed in on the spot, never seen before by anyone, and watch the result immediately, turned out to be a far more convincing and more honest way to demonstrate progress than a static slide of numbers. The \"Watch Live\" feature, which opens an actual SUMO visualization window showing the intersection and the agent's decisions in real time, exists specifically for this kind of live, on demand demonstration."),
];

const section2_challenges = [
  h2("2.6 Challenges and the Solutions We Found"),
  p("Several distinct problems recurred throughout the project, and most of them are more general lessons about reinforcement learning than quirks of this particular intersection."),
  h3("Reward hacking via simulator artifacts"),
  p("The very first working version of the agent appeared, briefly, to be doing extremely well, until we noticed it was achieving that by deliberately starving certain lanes long enough that SUMO's own vehicle teleportation safety feature (which removes a vehicle that has waited an unreasonably long time, to keep the simulation from stalling) would kick in and delete those vehicles from the simulation entirely. Waiting time attributed to a vehicle that no longer exists is, from the reward function's point of view, waiting time that never happened. The fix was simple in hindsight, permanently disable teleportation in the simulator configuration, but finding it required actually watching the agent's behavior rather than trusting the reward curve, which was climbing steadily the entire time this was happening."),
  h3("Gradient explosions from an unbounded penalty"),
  p("An early reward design used an exponentially growing starvation penalty with no upper limit, on the reasoning that truly excessive waiting should be punished much more severely than mild waiting. In practice, values in the thousands occasionally appeared in the reward signal and destabilized training outright. Capping the penalty at a fixed maximum resolved the numerical instability, though the underlying reward design was still eventually replaced altogether (see below)."),
  h3("A \"dynamic minimum green\" rule that fired on the wrong signal"),
  p("One version tried to let the agent switch earlier than the standard minimum green time whenever the current phase appeared to have very few vehicles left, measured by live vehicle counts on that phase's lanes. This looked reasonable in isolation but had a structural flaw: while a phase is green, its own vehicles are actively moving rather than halting, so a live vehicle count on a green phase reads as nearly empty almost by construction, regardless of actual traffic level. The guard intended to prevent this from firing in heavy traffic (a total queue threshold) turned out to be broken in essentially the same way, and never actually engaged. Trained further on top of this bug, the agent fully committed to exploiting it: certain phases were switched at the earliest possible moment every single time, while others held for the maximum allowed duration, and vehicles in the starved phases were left waiting for over 17,000 seconds in the worst cases. This was, by a wide margin, the worst result in the project's history, and it could not be recovered by further training on top of the same weights, only a fresh agent, trained from random initialization with the flawed logic removed entirely, resolved it. The general lesson we took from this, and applied for the remainder of the project, is that resuming training after a meaningful change to the reward or the rules the agent operates under is not a safe shortcut; it risks reinforcing a bug rather than correcting it."),
  h3("A reward with almost no gradient in light traffic"),
  p("A version whose reward was simply the reduction in total waiting time performed acceptably in moderate and heavy traffic but could not learn to handle light traffic at all. The reason became clear once we looked at it directly: with very few vehicles present, the change in total waiting time between one decision and the next is close to zero almost regardless of what the agent does, which gives it almost no signal to learn from in exactly the condition where learning was needed most. Adding a starvation based penalty term, one that responds to how long a lane's single longest waiting vehicle has been sitting there, rather than to an aggregate that can trivially stay near zero, supplied a meaningful gradient even when overall traffic was sparse, and light traffic performance improved roughly fifteen fold in the version where this was introduced."),
  h3("The camera range trade off"),
  p("Limiting the agent's observation to a fixed distance from the stop line, meant to model a realistic sensor rather than an omniscient one, initially caused a regression in heavy traffic: queues that extended past the visible range were effectively invisible, so the agent under reacted to congestion it could not see building up. We tested whether a richer, non saturating way of encoding the same observation would help, it did not, which is discussed further in Section 2.7, and ultimately resolved the regression by extending the visible range rather than changing what was done with it."),
  h3("An idle intersection that still wanted to switch"),
  p("Even once most other issues were resolved, the agent would occasionally switch phases at a completely empty intersection for no discernible benefit, apparently because nothing in its training had ever taught it that doing so was pointless. A soft penalty for this behavior was tried first and was simply too weak to compete with the main reward signal. The eventual fix removed the option outright: switching is now a structurally masked, unavailable action whenever no vehicle is visible to any camera, regardless of what the policy itself would otherwise prefer. This turned out to be the single change that took the agent from \"beats some baselines\" to \"beats every baseline in every tested condition,\" and the general principle, enforce a genuine constraint structurally rather than discourage it with a penalty, is one we would apply earlier if we did this again."),
  h3("A scope reduction caused by military reserve duty"),
  p("Section 2.3 describes this in full: the computer vision and tracking layer (YOLO and DeepSORT) proposed in Phase A was not implemented, in part because a team member's mandatory military reserve duty (מילואים) removed a significant, unplanned block of development time. We chose to protect the depth of the reinforcement learning work rather than implement the vision pipeline shallowly, and we are transparent about that trade off rather than treating it as a hidden gap."),
  h3("Diagnosing why a classical baseline itself failed badly"),
  p("Not every challenge involved our own agent. The Max Pressure baseline, expected to be a strong, principled comparison point, instead performed dramatically worse than even the simplest fixed time controller on our specific network. Rather than accept that at face value, we built a short instrumented diagnostic that logged the controller's internal pressure readings against the real, unfiltered vehicle queue at every decision point, and traced the failure to a genuine gridlock: two of the four phases would saturate at the physical capacity of their approach lanes and never recover, because Max Pressure's pressure formula has no way to distinguish \"this phase needs service\" from \"this phase's exit is itself jammed, and no amount of green time will help.\" We documented this finding rather than quietly excluding the baseline, since it is a genuine and reproducible property of the comparison, not a tuning artifact in our favor."),
  h3("Confirming the evaluation methodology was actually trustworthy"),
  p("Before relying on any comparison between controllers, we verified, rather than assumed, that SUMO's seeded vehicle generation is genuinely deterministic: the same seed reliably produces a bit for bit identical stream of vehicles regardless of which controller is driving the signal, across separate process runs and even across different days. This property is what makes a \"paired\" comparison between our agent and a baseline meaningful in the first place, and we would not have trusted the comparisons in this project without having checked it directly."),
  h3("Wasted simulation time, and a training run that never fully settled"),
  p("Late in the project we noticed that evaluation episodes kept running long after a scenario's road had genuinely emptied out, since episodes were originally terminated only by a fixed simulated time limit rather than by traffic actually clearing. Adding an early exit condition, stop the moment no vehicle remains and none are still expected to arrive, cut typical evaluation time by roughly seven to eight times with no change whatsoever to the reported results, since nothing further can happen on an empty road either way."),
  p("Separately, and more fundamentally, we investigated whether training the agent for longer than our original budget would reliably improve it, given an initial (mistaken) impression that a second, shorter training run had performed worse simply because it was shorter. Looking closely at that second run's own checkpoint history showed a more specific explanation: even at 99% of the way through its own training schedule, with its learning rate almost fully annealed, an individual checkpoint could still be sandwiched between two much better neighbors just ten thousand steps away in either direction, a pattern far more consistent with a fixed, never decaying exploration noise setting continuing to perturb the policy throughout training than with simply running out of time. We tested this directly by training a fresh agent for twice the original step budget; it did not exceed the original agent's quality, and a second collapse appeared partway through its extended schedule, in a step range where the original, shorter run's learning rate had already decayed to a small fraction of its starting value but the longer run's had not, since that schedule stretches proportionally to whatever total length is requested. We consider this one of the project's more useful negative results: it directly contradicts the intuitive assumption that more training time is a safe, guaranteed way to improve a reinforcement learning agent, at least under a reward and exploration setup that does not itself decay over time."),
];

const section2_results = [
  h2("2.7 Results and Conclusions"),
  p("The project's central goal, an agent that beats fixed time control across light, moderate, and heavy traffic, was achieved and independently verified rather than taken on faith. Our champion agent reduces total waiting time by roughly 50% in light traffic, 36% in moderate traffic, and 8% in heavy traffic, each measured against the best performing fixed time baseline for that condition. Under the project's most rigorous test, every saved training checkpoint evaluated against its own independently drawn random seed and scenario, with no result excluded or reused, the champion agent beat every one of the three fixed time baselines outright in 53 of 60 cases (88.3%), and its remaining losses were narrow, single digit percentage misses against only the single toughest baseline in light traffic, never a broad or catastrophic failure."),
  p("The three charts below are the same evidence base behind that headline number, shown directly rather than only summarized, and the first and third are the same figures used on the project poster. In every chart on this page, the red line or red dots are PPO, our own agent, the one this project actually delivers, being directly measured against ordinary fixed timer traffic lights (the blue, orange, and green lines, one for each fixed cycle length we tested). In every case, lower on the chart means less time cars spent waiting, so lower is better, and a PPO line sitting below the fixed timer lines means our agent is outperforming them."),
  para([new ImageRun({ type: "png", data: fs.readFileSync("C:\\Users\\Einavs_PC\\Documents\\TrafficProject\\FinalProjectBook\\ppo_checkpoint_waittime_scatter.png"), transformation: { width: 580, height: 290 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.2: total waiting time at every training checkpoint of our champion PPO agent (red), tested against three fixed timer baselines (blue, orange, green) under identical conditions, with one independently drawn random seed and traffic scenario used per checkpoint so nothing here was cherry picked. The vertical axis is compressed (a log scale) only so that both light and heavy traffic, which differ enormously in scale, can be shown on one chart; it does not change the conclusion, which is simple: PPO (red) starts out roughly tied with the fixed timers, drops sharply within the first few hundred thousand training steps as it learns, and then stays below all three fixed timer lines for essentially the rest of training, in light, moderate, and heavy traffic alike (solid, dashed, and dotted lines respectively). This is the agent visibly getting better with practice, and then reliably beating the alternative it was trained to replace.", { italics: true, size: 20 }),
  para([new ImageRun({ type: "png", data: fs.readFileSync("C:\\Users\\Einavs_PC\\Documents\\TrafficProject\\FinalProjectBook\\ppo_win_rate_scatter.png"), transformation: { width: 580, height: 249 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.3: the same 60 checkpoints as Figure 2.2, now shown as a single number per checkpoint, percent improvement over one specific fixed timer baseline (Fixed_60s), split by traffic condition (green, orange, and red dots for light, moderate, and heavy traffic). A dot above the black zero line means PPO beat the fixed timer at that point in training; a dot below means it lost. Aside from two early checkpoints, in the first half million steps of training, before the agent had learned very much yet, nearly every dot for the rest of training sits above the line, which is the direct, checkpoint by checkpoint evidence behind the 88.3% win rate reported above, and stands in direct contrast to Figure 2.1's DQN chart, where losing dots keep reappearing throughout the entire project rather than settling down early and staying resolved.", { italics: true, size: 20 }),
  para([new ImageRun({ type: "png", data: fs.readFileSync("C:\\Users\\Einavs_PC\\Documents\\TrafficProject\\FinalProjectBook\\ppo_medium_scenario_progress.png"), transformation: { width: 560, height: 288 } })], { alignment: AlignmentType.CENTER }),
  p("Figure 2.4: the same comparison as Figure 2.2, but for moderate traffic only, using an ordinary (non compressed) vertical axis, which makes the shape of the improvement easier to see at a glance than the log scale charts above: PPO's blue line starts out far above all three fixed timers, meaning it initially performs worse, then falls sharply and settles in below every fixed timer (orange, green, red flat lines) for essentially the entire rest of training. This is the same underlying story as Figure 2.2, told at a scale a reader unfamiliar with log axes may find easier to follow directly.", { italics: true, size: 20 }),
  p("The remaining gap in heavy traffic was itself the subject of a dedicated investigation rather than left unexamined. We hypothesized that the agent's camera limited observation was \"saturating\" under heavy demand, every input reading effectively maxed out, leaving the policy unable to distinguish one badly congested state from another, and tested this directly by training an otherwise identical agent with a richer, non saturating way of encoding the same information. It performed identically to the original, checkpoint for checkpoint, tracking the same underlying demand pattern rather than the richer observation. We concluded that this remaining gap reflects a genuine demand ceiling, queueing physics when arrivals approach the intersection's physical service capacity, rather than a limitation of what the agent can perceive, and that closing it further would likely require coordinating with neighboring intersections rather than refining a single one in isolation."),
  p("A second, unplanned but genuinely valuable result came from directly testing whether training for longer improves the agent. It does not, reliably: a fresh agent trained for twice the original step budget scored 77.4% on the same rigorous evaluation, meaningfully below the original champion's 88.3%, despite having twice the training experience. We traced part of the reason to how the learning rate schedule is defined relative to the total training length requested, and consider the likely remaining cause to be a fixed exploration noise setting that never decreases across training, regardless of how long that training runs. Both are concrete, addressable design choices for future work, rather than a fundamental ceiling on what this approach can achieve."),
];

const section2_lessons = [
  h2("2.8 Lessons Learned"),
  p("If we were repeating this project from the beginning, several things would change. We would enforce genuine physical or logical constraints structurally, through action masking, from the very first version, rather than attempting to discourage undesired behavior through a penalty term and only reaching for a hard constraint once the penalty had already been shown to fail, the empty intersection switching problem cost more iteration time than it needed to for exactly this reason. We would also introduce our full, rigorous, unfiltered evaluation methodology much earlier in the project rather than escalating into it gradually; several early \"this version is clearly better\" conclusions, based on only one or two fixed seeds, turned out to be considerably less certain once tested properly, and an earlier commitment to rigor would likely have saved iteration cycles rather than costing them."),
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
      ["Average waiting time reduction", "At least 20% vs. a fixed time baseline", "Exceeded for two of three traffic conditions, 50% (light traffic) and 36% (moderate traffic); 8% in heavy traffic, independently verified across many random seeds rather than a single run"],
      ["Maximum queue length reduction", "At least 15%", "Not separately measured; our evaluation reports total waiting time rather than maximum queue length as the primary metric"],
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
// APPENDIX A, USER GUIDE
//
const appendixA = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("Appendix A, User Guide"),
  p("This guide describes the normal, successful operating flow of the FlowGrid comparison tool (available as both a desktop application and a browser based application, with an identical feature set). It intentionally does not cover error conditions or unusual inputs, only the flow a user follows to get a result."),
  h2("A.1 Starting the Application"),
  bullet("Desktop version: run comparison_gui.py from the project's tools folder. The application window opens directly."),
  bullet("Web version: run server.py from the comparison_web folder; a browser tab opens automatically at the local address shown in the terminal."),
  h2("A.2 Selecting Models to Compare"),
  p("The Models panel lists every trained agent currently registered, with the project's champion model pre selected. Tick the checkbox beside any additional model you want included in the comparison. To compare against an agent not yet in the list, use \"Add Model\" and browse to its saved file; it will appear in the list immediately and persist for future sessions."),
  h2("A.3 Selecting Baselines"),
  p("The Baselines panel lists the fixed time controllers available for comparison (30, 45, and 60 second cycles). Tick any you want included alongside the selected model(s)."),
  h2("A.4 Choosing Seeds and a Traffic Scenario"),
  p("Choose \"Random\" and a count to have that many fresh, never repeated traffic instances generated automatically, or choose \"Manual\" to type in specific seed values one at a time. Then select which traffic condition to test, Low, Medium, High, or All three at once."),
  h2("A.5 Running the Comparison"),
  p("Click \"Start Comparison.\" A progress indicator tracks how many of the required simulation runs have completed. Optionally, tick \"Watch Live\" beforehand (with exactly one seed and one specific scenario selected) to have the actual SUMO simulation window open and play out visibly while the comparison runs, rather than entirely in the background."),
  h2("A.6 Reading the Results"),
  p("Once complete, a results table appears for each tested scenario, listing every selected model and baseline with its total waiting time for each seed and an overall average. The best performing entry in each table is highlighted, and a bar chart beneath the table gives the same comparison visually."),
];

//                                                                            
// APPENDIX B, MAINTENANCE GUIDE
//                                                                            
const appendixB = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("Appendix B, Maintenance Guide"),
  p("This guide covers what is needed to continue developing, retraining, or extending this project after its initial delivery. It assumes familiarity with standard Python development and does not cover installing well known general purpose infrastructure (Python itself, Git, a code editor) in detail."),
  h2("B.1 Required Environment"),
  bullet("Python 3.10, with the packages listed in the project's requirements file (notably: Stable-Baselines3, sb3-contrib, sumo-rl, pandas, matplotlib, seaborn, customtkinter, FastAPI, uvicorn)."),
  bullet("SUMO (Simulation of Urban Mobility), including its Python/TraCI and libsumo bindings, installed and available on the system path."),
  bullet("A multi core CPU is strongly recommended: training and full evaluation sweeps run ten parallel simulation instances by default."),
  h2("B.2 Project Specific Installation"),
  p("Clone the project's Git repository, then install Python dependencies from the included requirements file into a virtual environment. No project specific installation step beyond this is required, the environment and training scripts locate the SUMO network and route files via paths defined in the code."),
  h2("B.3 Project Structure, at a Glance"),
  bullet("Each trained agent version lives in its own folder under saved_agents/, containing its environment definition, training script, saved checkpoints, and evaluation results, never overwritten by later versions."),
  bullet("Shared, version agnostic tools (comparison applications, evaluation sweeps, plotting utilities) live in a common tools/ folder and are reused across every agent version."),
  bullet("A version history document records every major iteration, what changed, and why, and should be extended rather than replaced when a new version is added."),
  h2("B.4 Retraining or Extending the Agent"),
  p("To train a new version, copy an existing version's folder rather than modifying it in place, update its internal import references to point to the copy, and adjust the training script's hyperparameters as needed. This preserves every previous version as a working fallback. Never resume training an existing checkpoint after changing its reward function or observation definition; train a fresh agent from random initialization instead, since resuming under a changed definition has previously produced a full, unrecoverable policy collapse."),
  h2("B.5 Adding a New Baseline or Comparison Target"),
  p("New fixed time or rule based baselines can be added by extending the baseline list used by the evaluation tools; each baseline needs only a name and, for fixed time controllers, a cycle length, since the comparison tools handle result collection and reporting generically."),
  h2("B.6 Running an Evaluation Sweep"),
  p("The project's evaluation tools support a dry run mode that reports exactly how many simulation runs a given sweep will perform and how long it is expected to take, without executing anything, always run this first before committing to a long sweep. Sweeps also write partial results incrementally as they progress and can be resumed from where they left off if interrupted."),
];

//
// APPENDIX C, USE OF GENERATIVE AI
//
const appendixC = [
  new Paragraph({ children: [new PageBreak()] }),
  h1("Appendix C, Use of Generative AI"),
  p("In the interest of the same honesty this book has tried to maintain throughout, we are disclosing directly how generative AI tools were used during Phase B, following the same disclosure practice as our Phase A submission."),
  h2("C.1 Coding assistance"),
  p("An AI coding assistant (Claude Code) was used throughout development, primarily for writing and debugging Python scripts: evaluation and plotting tooling, the crash safe incremental sweep scripts described in Section 2.4, diagnostic scripts used to trace specific bugs (the Max Pressure gridlock investigation and the reward hacking investigation described in Section 2.6), and this document itself, generated programmatically from a script we reviewed and directed. In every case, the research questions, the experiments to run, the interpretation of results, and the decision of what to report were made by us, not by the assistant; the assistant's role was implementation and drafting support under our direction, not independent judgment about what the project's findings were."),
  h2("C.2 What was not delegated to AI"),
  p("The core reinforcement learning design decisions described throughout Section 2, the reward function iterations, the observation space design, the choice to move from DQN to PPO, and the interpretation of every evaluation result including the DQN inconsistency data in Section 2.3, were our own analysis, not generated content we accepted uncritically. Where an AI assistant proposed placeholder or estimated figures during drafting, we did not accept them as final; every quantitative result in this book that is presented as fact is drawn from a real training log, evaluation CSV, or comparison history file in the project's own codebase, not from an estimate."),
  h2("C.3 Writing style"),
  p("The prose in this book was drafted with AI assistance and then reviewed by us for accuracy, tone, and honesty, in particular to make sure it did not overstate what was actually built or soften the parts of the project's history, the scope reduction, the reserve duty interruption, and the DQN evaluation problems among them, that we wanted stated plainly rather than glossed over."),
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
        ...appendixC,
      ],
    },
  ],
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("FlowGrid_Capstone_Project_Book.docx", buffer);
  console.log("Written: FlowGrid_Capstone_Project_Book.docx");
});
