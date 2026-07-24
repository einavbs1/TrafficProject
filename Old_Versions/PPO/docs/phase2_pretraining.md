# Phase 2: Pre-training via Behavioral Cloning (BC)

## Objective
Give the neural network a massive head start by forcing it to mimic the baseline Max-Pressure algorithm, avoiding the chaotic early exploration phase of standard RL.

## Execution
Run the behavioral cloning script:
```bash
python train_bc.py
```

## What Happens Under the Hood
1. The script loads the `expert_data.pkl` generated in Phase 1.
2. It structures the data into `imitation` library Transition formats.
3. A Multi-Layer Perceptron (MLP) neural network is trained entirely **offline**. It attempts to predict the expert action given the state observation.
4. The network parameters are optimized using supervised learning to minimize the difference between its predictions and the actual expert choices.

## Output
This phase produces `bc_policy.zip`. This file contains the pre-trained weights of the neural network. The agent now "knows" the basics of traffic management.
