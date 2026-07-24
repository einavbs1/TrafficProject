# Deep Reinforcement Learning for Traffic Signal Control: PPO vs DQN Architecture

When designing an AI to control a complex, highly dynamic environment like a city traffic grid, the choice of the foundational neural network algorithm dictates the ultimate ceiling of its intelligence. While Deep Q-Networks (DQN) are famous for beating Atari games, **Proximal Policy Optimization (PPO)** is the industry standard for modern robotics and continuous control.

Here is a breakdown of exactly why the Maskable PPO agent vastly outperforms the old DQN agent, and the specific architectural upgrades we attached to its policy.

---

## 1. Algorithmic Supremacy: Why PPO Dominates DQN

### On-Policy vs Off-Policy Learning
* **DQN (Off-Policy)**: DQN relies heavily on an "Experience Replay" buffer. It stores memories of past traffic states and randomly pulls them out later to train on. Traffic physics are highly chaotic; a memory of a 50-car traffic jam from 5 hours ago may be completely irrelevant to the AI's *current* strategy. This makes DQN highly unstable and prone to catastrophic forgetting.
* **PPO (On-Policy)**: PPO learns purely from what is happening *right now*. It executes actions, immediately calculates how successful they were using "Advantage Estimation", updates its brain, and throws the memory away. This ensures rapid, stable, and highly focused convergence.

### Policy Gradient vs Value Maximization
* **DQN (Value-Based)**: DQN assigns a raw numerical score (Q-Value) to every possible action, and simply picks the highest number. If the traffic grid is highly unpredictable, the Q-Values fluctuate violently, causing the AI to stutter or get stuck in gridlock loops.
* **PPO (Policy Gradient)**: PPO outputs a **Probability Distribution** across all actions (e.g., 80% chance to hold Green, 20% chance to switch to Yellow). This allows the AI to develop highly nuanced, probabilistic strategies rather than blindly chasing a single maximum number.

### Native Action Masking
* **DQN**: Standard DQN cannot comprehend "illegal" moves natively. If the light is already Red, DQN might still try to select the "Turn Red" action. You have to hack DQN to apply massive negative rewards to stop it from choosing illegal moves, which pollutes its learning.
* **Maskable PPO**: The PPO variant we implemented supports native Action Masking. We simply hand the AI a mathematical mask of invalid actions, and it completely removes them from the probability calculation. The AI never wastes a single second evaluating impossible traffic light transitions.

---

## 2. The V2 Policy Upgrades

To push the PPO agent beyond the theoretical limits of the hardcoded `Max Pressure` baseline, we completely rewrote the surrounding environment and injected several advanced training mechanics into the policy pipeline:

> [!IMPORTANT]  
> **Curriculum Multi-Map Training (Curing Overfitting)**
> The V1 agent suffered from extreme Map Overfitting—it memorized the `Extreme` traffic map and completely panicked when tested on `Low` traffic because it had never seen empty roads. We engineered a `MultiRouteWrapper` that dynamically injects one of three completely different traffic densities (Low, Medium, Extreme) at the start of every single episode. This forced the Neural Network to generalize its logic: *"If I see 2 cars, cycle fast. If I see 50 cars, hold green."*

> [!TIP]  
> **Continuous Starvation Penalty**
> We removed a catastrophic 90-second safety override that was preventing the AI from learning cause-and-effect. In its place, we injected a mathematically balanced variance penalty: `(max(wait) - min(wait)) * 0.05`. If the AI holds a light green too long, the wait-time difference between the main road and the cross street grows, and the AI organically bleeds points. This perfectly simulates "cross-street pressure" without hardcoding it.

> [!NOTE]  
> **Dynamic Switching Freedom**
> We reduced the artificial switching penalty from a harsh `-3` down to `-0.1`. In V1, the AI was terrified of losing points, so it would hold lights green indefinitely. By removing this fear, the AI is now free to rapidly flutter the lights in high-density scenarios, matching the aggressive optimization style of Max Pressure.

> [!TIP]  
> **Observation Normalization (VecNormalize)**
> A traffic queue can range from 0 to 500 cars. Feeding raw numbers like "500" into a Neural Network causes the mathematical gradients to explode, breaking the AI. We applied a running statistical normalizer that squashes all traffic data into a clean `[-10, 10]` range, ensuring the AI can process extreme gridlock without its brain crashing.

> [!IMPORTANT]  
> **Massive Multi-Core CPU/GPU Parallelization**
> We decoupled the SUMO physics engine from the PyTorch AI math. By utilizing `SubprocVecEnv`, we launched **10 to 12 completely independent traffic simulations** simultaneously across your physical CPU cores, while forcing the AI's neural network to calculate the math exclusively on your Graphics Card (`device="cuda"`). This accelerated training speeds by an order of magnitude.
