# Phase 1: Generate the Baseline

## Objective
Establish a fundamental dataset of correct, safe actions before introducing reinforcement learning.

## Execution
Run the data collection script:
```bash
python collect_expert_data.py
```

## What Happens Under the Hood
1. The script bypasses neural networks entirely.
2. It launches a `sumo-rl` environment and connects to your base `.net.xml` and `.rou.xml` files.
3. It utilizes a deterministic, analytical **Max-Pressure heuristic**. At each simulation step, it calculates the difference between incoming and outgoing queues.
4. It executes the optimal phase to relieve intersection pressure.
5. Every single state observation and the corresponding chosen action are recorded.

## Output
The phase produces a `expert_data.pkl` file containing state-action transitions. This acts as the "textbook" that the agent will study in Phase 2.
