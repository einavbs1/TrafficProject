# FlowGrid — User Guide

This guide describes the normal, successful operating flow of the FlowGrid
comparison tool (available as both a desktop application and a browser
application, with an identical feature set). It intentionally does not
cover error conditions or unusual inputs, only the flow a user follows to
get a result.

## Starting the Application

- **Desktop version:** run `comparison_gui.py` from `PPO_Agent/scripts/`.
  The application window opens directly.
- **Web version:** run `server.py` from `PPO_Agent/scripts/comparison_web/`;
  a browser tab opens automatically at the local address shown in the
  terminal.

## Selecting Models to Compare

The Models panel lists every trained agent currently registered, with the
project's champion model pre-selected. Tick the checkbox beside any
additional model you want included in the comparison. To compare against an
agent not yet in the list, use "Add Model" and browse to its saved file
(default location: `PPO_Agent/models/`); it will appear in the list
immediately and persist for future sessions.

## Selecting Baselines

The Baselines panel lists the fixed-time controllers available for
comparison (30, 45, and 60 second cycles). Tick any you want included
alongside the selected model(s).

## Choosing Seeds and a Traffic Scenario

Choose "Random" and a count to have that many fresh, never-repeated traffic
instances generated automatically, or choose "Manual" to type in specific
seed values one at a time. Then select which traffic condition to test:
Low, Medium, High, or All three at once.

## Running the Comparison

Click "Start Comparison." A progress indicator tracks how many of the
required simulation runs have completed. Optionally, tick "Watch Live"
beforehand (with exactly one seed and one specific scenario selected) to
have the actual SUMO simulation window open and play out visibly while the
comparison runs, rather than entirely in the background.

## Reading the Results

Once complete, a results table appears for each tested scenario, listing
every selected model and baseline with its total waiting time for each seed
and an overall average. The best-performing entry in each table is
highlighted, and a bar chart beneath the table gives the same comparison
visually.

## Running the DQN Agent's Tools

The original DQN agent has its own desktop app and browser dashboard, with
the same kind of comparison functionality. See `../DQN_Agent/README.md` and
`../DQN_Agent/docs/GUI.md` / `COMPARE.md` for details.
