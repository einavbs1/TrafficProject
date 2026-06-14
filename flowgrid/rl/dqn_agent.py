import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
from collections import deque

from flowgrid.rl.device import resolve_training_device_or_fallback
from flowgrid.rl.policy_config import PolicyConfig, TrainingParams
from flowgrid.training.traffic_curriculum import default_phase_counts

MASK_NEG = -1e9


class DQN(nn.Module):
    def __init__(self, input_dim, output_dim, hidden_dim=64):
        super(DQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x):
        return self.net(x)


class ReplayBuffer:
    def __init__(self, capacity):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done, action_mask, next_action_mask):
        self.buffer.append(
            (state, action, reward, next_state, done, action_mask, next_action_mask)
        )

    def sample(self, batch_size):
        batch = random.sample(self.buffer, batch_size)
        return map(np.stack, zip(*batch))

    def __len__(self):
        return len(self.buffer)


class DQNAgent:
    def __init__(
        self,
        input_dim,
        output_dim,
        lr=1e-3,
        gamma=0.99,
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay=0.99,
        buffer_capacity=10000,
        batch_size=64,
        training: TrainingParams | None = None,
        policy_config: PolicyConfig | None = None,
        device_preference: str | None = None,
    ):
        if training is None and policy_config is not None:
            training = policy_config.training
        if training is None:
            training = PolicyConfig.load().training
        self.action_space_dim = output_dim
        self.gamma = training.gamma
        self.epsilon = training.epsilon_start
        self.epsilon_end = training.epsilon_end
        self.epsilon_decay = training.epsilon_decay
        self.batch_size = training.batch_size
        lr = training.learning_rate
        buffer_capacity = training.buffer_capacity
        pref = device_preference if device_preference is not None else training.device
        self.device, self.device_label = resolve_training_device_or_fallback(pref)

        self.policy_net = DQN(input_dim, output_dim).to(self.device)
        self.target_net = DQN(input_dim, output_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()
        self.memory = ReplayBuffer(buffer_capacity)
        self.episodes_done = 0
        self.steps_done = 0
        self.phase_episodes_done = default_phase_counts()

    def export_checkpoint_meta(self) -> dict:
        return {
            "epsilon": float(self.epsilon),
            "episodes_done": int(self.episodes_done),
            "steps_done": int(self.steps_done),
            "epsilon_decay": float(self.epsilon_decay),
            "phase_episodes_done": dict(self.phase_episodes_done),
            "device": str(self.device),
            "device_label": str(self.device_label),
        }

    def import_checkpoint_meta(self, meta: dict) -> None:
        if meta.get("episodes_done") is not None:
            self.episodes_done = int(meta["episodes_done"])
        if meta.get("steps_done") is not None:
            self.steps_done = int(meta["steps_done"])
        if meta.get("epsilon_decay") is not None:
            self.epsilon_decay = float(meta["epsilon_decay"])
        if meta.get("phase_episodes_done") is not None:
            counts = default_phase_counts()
            raw = meta["phase_episodes_done"]
            if isinstance(raw, dict):
                for key in counts:
                    if key in raw:
                        counts[key] = int(raw[key])
            self.phase_episodes_done = counts

    def _valid_actions(self, action_mask):
        if action_mask is None:
            return list(range(self.action_space_dim))
        mask = np.asarray(action_mask, dtype=bool)
        return [i for i in range(self.action_space_dim) if mask[i]]

    def select_action(self, state, action_mask=None):
        valid = self._valid_actions(action_mask)
        if not valid:
            valid = [0]
        if random.random() < self.epsilon:
            return random.choice(valid)
        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_t).squeeze(0).cpu().numpy()
            if action_mask is not None:
                mask = np.asarray(action_mask, dtype=bool)
                q_values = q_values.copy()
                q_values[~mask] = MASK_NEG
            best = int(np.argmax(q_values))
            if best not in valid:
                return valid[0]
            return best

    def update_epsilon(self):
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)

    def optimize_model(self):
        if len(self.memory) < self.batch_size:
            return

        states, actions, rewards, next_states, dones, masks, next_masks = self.memory.sample(
            self.batch_size
        )

        states_t = torch.FloatTensor(states).to(self.device)
        actions_t = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        rewards_t = torch.FloatTensor(rewards).unsqueeze(1).to(self.device)
        next_states_t = torch.FloatTensor(next_states).to(self.device)
        dones_t = torch.FloatTensor(dones).unsqueeze(1).to(self.device)

        q_values = self.policy_net(states_t).gather(1, actions_t)

        with torch.no_grad():
            next_q = self.target_net(next_states_t)
            next_q_np = next_q.cpu().numpy()
            for i in range(len(next_masks)):
                m = np.asarray(next_masks[i], dtype=bool)
                next_q_np[i, ~m] = MASK_NEG
            next_q_masked = torch.FloatTensor(next_q_np).to(self.device)
            max_next_q_values = next_q_masked.max(1)[0].unsqueeze(1)
            target_q_values = rewards_t + self.gamma * max_next_q_values * (1 - dones_t)

        loss = self.loss_fn(q_values, target_q_values)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def update_target_network(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())
