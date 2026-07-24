import os
import sys
import traci
import random
import numpy as np
import time
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from collections import deque

# --- הגדרות ה-AI ---
# שים לב: input_dim יהיה עכשיו 8 (כי יש 8 נתיבים שונים לבדוק)
INPUT_DIM = 8 
OUTPUT_DIM = 2 # עדיין בוחרים בין שתי אופציות גדולות (ירוק לצפון-דרום או למזרח-מערב)
BATCH_SIZE = 64
GAMMA = 0.99
EPS_START = 1.0
EPS_END = 0.01
EPS_DECAY = 0.995
LEARNING_RATE = 0.001
MEMORY_SIZE = 10000
MODEL_FILE_NAME = "traffic_model_complex.pth"

# --- הגדרות הצומת ---
PHASE_NS_GREEN = 0
PHASE_NS_YELLOW = 1
PHASE_EW_GREEN = 2
PHASE_EW_YELLOW = 3

def create_files():
    with open("my_nodes.nod.xml", "w") as nodes:
        print("""<nodes>
    <node id="center" x="0" y="0" type="traffic_light"/>
    <node id="n" x="0" y="500" type="priority"/>
    <node id="s" x="0" y="-500" type="priority"/>
    <node id="e" x="500" y="0" type="priority"/>
    <node id="w" x="-500" y="0" type="priority"/>
</nodes>""", file=nodes)

    with open("my_edges.edg.xml", "w") as edges:
        print("""<edges>
    <edge id="n_to_center" from="n" to="center" priority="2" numLanes="2" speed="15.0"/>
    <edge id="center_to_n" from="center" to="n" priority="2" numLanes="2" speed="15.0"/>
    <edge id="s_to_center" from="s" to="center" priority="2" numLanes="2" speed="15.0"/>
    <edge id="center_to_s" from="center" to="s" priority="2" numLanes="2" speed="15.0"/>
    <edge id="e_to_center" from="e" to="center" priority="2" numLanes="2" speed="15.0"/>
    <edge id="center_to_e" from="center" to="e" priority="2" numLanes="2" speed="15.0"/>
    <edge id="w_to_center" from="w" to="center" priority="2" numLanes="2" speed="15.0"/>
    <edge id="center_to_w" from="center" to="w" priority="2" numLanes="2" speed="15.0"/>
</edges>""", file=edges)

    # יצירת הרשת
    os.system("netconvert --node-files=my_nodes.nod.xml --edge-files=my_edges.edg.xml --output-file=my_net.net.xml --tls.guess")

    # --- השינוי הגדול: מסלולים לכל הכיוונים (ישר ושמאלה) ---
    with open("my_routes.rou.xml", "w") as routes:
        print("""<routes>
    <vType id="car" accel="0.8" decel="4.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.7" guiShape="passenger"/>
    
    <route id="route_ns_straight" edges="n_to_center center_to_s"/>
    <route id="route_ns_left"     edges="n_to_center center_to_e"/> <route id="route_sn_straight" edges="s_to_center center_to_n"/>
    <route id="route_sn_left"     edges="s_to_center center_to_w"/> <route id="route_ew_straight" edges="e_to_center center_to_w"/>
    <route id="route_ew_left"     edges="e_to_center center_to_s"/> <route id="route_we_straight" edges="w_to_center center_to_e"/>
    <route id="route_we_left"     edges="w_to_center center_to_n"/> <flow id="f_ns_s" type="car" route="route_ns_straight" begin="0" end="3600" probability="0.08"/>
    <flow id="f_ns_l" type="car" route="route_ns_left"     begin="0" end="3600" probability="0.05"/>
    
    <flow id="f_sn_s" type="car" route="route_sn_straight" begin="0" end="3600" probability="0.08"/>
    <flow id="f_sn_l" type="car" route="route_sn_left"     begin="0" end="3600" probability="0.05"/>
    
    <flow id="f_ew_s" type="car" route="route_ew_straight" begin="0" end="3600" probability="0.06"/>
    <flow id="f_ew_l" type="car" route="route_ew_left"     begin="0" end="3600" probability="0.04"/>
    
    <flow id="f_we_s" type="car" route="route_we_straight" begin="0" end="3600" probability="0.06"/>
    <flow id="f_we_l" type="car" route="route_we_left"     begin="0" end="3600" probability="0.04"/>

</routes>""", file=routes)

    with open("my_config.sumocfg", "w") as config:
        print("""<configuration>
    <input>
        <net-file value="my_net.net.xml"/>
        <route-files value="my_routes.rou.xml"/>
    </input>
</configuration>""", file=config)

class DQN(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQN, self).__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, output_dim)

    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.fc3(x)

class Agent:
    def __init__(self, input_dim, output_dim):
        self.model = DQN(input_dim, output_dim)
        self.target_model = DQN(input_dim, output_dim)
        self.target_model.load_state_dict(self.model.state_dict())
        self.optimizer = optim.Adam(self.model.parameters(), lr=LEARNING_RATE)
        self.memory = deque(maxlen=MEMORY_SIZE)
        self.epsilon = EPS_START

    def select_action(self, state):
        if random.random() < self.epsilon:
            return random.randint(0, OUTPUT_DIM - 1)
        else:
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            with torch.no_grad():
                q_values = self.model(state_tensor)
            return q_values.argmax().item()

    def store_transition(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def train(self):
        if len(self.memory) < BATCH_SIZE:
            return

        batch = random.sample(self.memory, BATCH_SIZE)
        state_batch, action_batch, reward_batch, next_state_batch, done_batch = zip(*batch)

        state_batch = torch.FloatTensor(np.array(state_batch))
        action_batch = torch.LongTensor(action_batch).unsqueeze(1)
        reward_batch = torch.FloatTensor(reward_batch).unsqueeze(1)
        next_state_batch = torch.FloatTensor(np.array(next_state_batch))
        done_batch = torch.FloatTensor(done_batch).unsqueeze(1)

        q_values = self.model(state_batch).gather(1, action_batch)
        next_q_values = self.target_model(next_state_batch).max(1)[0].unsqueeze(1)
        expected_q_values = reward_batch + (GAMMA * next_q_values * (1 - done_batch))

        loss = F.mse_loss(q_values, expected_q_values)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        if self.epsilon > EPS_END:
            self.epsilon *= EPS_DECAY

    def update_target_network(self):
        self.target_model.load_state_dict(self.model.state_dict())

    def save_model(self):
        torch.save(self.model.state_dict(), MODEL_FILE_NAME)

    def load_model(self):
        if os.path.exists(MODEL_FILE_NAME):
            self.model.load_state_dict(torch.load(MODEL_FILE_NAME))
            self.model.eval()
            self.epsilon = EPS_END 
            return True
        return False

# --- פונקציה מעודכנת לקריאת נתיבים נפרדים ---
def get_state():
    # הגדרת שמות הנתיבים (Lane IDs) ב-SUMO
    # הפורמט הוא: edge_id_0 (ימין/ישר), edge_id_1 (שמאל)
    
    lane_ids = [
        "n_to_center_0", "n_to_center_1", # צפון: ישר, שמאלה
        "s_to_center_0", "s_to_center_1", # דרום: ישר, שמאלה
        "e_to_center_0", "e_to_center_1", # מזרח: ישר, שמאלה
        "w_to_center_0", "w_to_center_1"  # מערב: ישר, שמאלה
    ]
    
    state = []
    for lane in lane_ids:
        # קריאת אורך התור בנתיב הספציפי הזה
        state.append(traci.lane.getLastStepHaltingNumber(lane))
        
    return np.array(state) # מחזיר מערך בגודל 8

def get_reward(state):
    return -1 * np.sum(state)

if __name__ == "__main__":
    create_files()
    
    # שים לב: Input Dim = 8 (כי יש 8 נתיבים)
    agent = Agent(input_dim=8, output_dim=2)
    model_loaded = agent.load_model()

    if model_loaded:
        print("Model loaded!")
    else:
        print("Training new model...")

    sumoBinary = "sumo-gui"
    sumoCmd = [sumoBinary, "-c", "my_config.sumocfg", "--delay", "100", "--start", "--quit-on-end", "--no-step-log", "true", "--waiting-time-memory", "1000"]
    
    EPISODES = 10
    
    for episode in range(EPISODES):
        print(f"Starting Episode {episode+1}/{EPISODES} (Epsilon: {agent.epsilon:.2f})")
        
        traci.start(sumoCmd)
        step = 0
        action_interval = 10 
        last_action_step = 0
        state = get_state()
        total_reward = 0
        
        while step < 1000:
            traci.simulationStep()
            time.sleep(0.05) 
            
            if step - last_action_step >= action_interval:
                action = agent.select_action(state)
                
                # --- לוגיקת הרמזור (2 פאזות עיקריות) ---
                current_phase = traci.trafficlight.getPhase("center")
                
                # Action 0: Green for North-South (כולל הפונים שמאלה משם)
                if action == 0 and current_phase == PHASE_EW_GREEN:
                    traci.trafficlight.setPhase("center", PHASE_EW_YELLOW)
                    for _ in range(4): 
                        traci.simulationStep()
                        step += 1
                        time.sleep(0.05)
                    traci.trafficlight.setPhase("center", PHASE_NS_GREEN)
                    
                # Action 1: Green for East-West (כולל הפונים שמאלה משם)
                elif action == 1 and current_phase == PHASE_NS_GREEN:
                    traci.trafficlight.setPhase("center", PHASE_NS_YELLOW)
                    for _ in range(4):
                        traci.simulationStep()
                        step += 1
                        time.sleep(0.05)
                    traci.trafficlight.setPhase("center", PHASE_EW_GREEN)
                
                next_state = get_state()
                reward = get_reward(next_state)
                total_reward += reward
                
                done = False
                if step >= 1000: done = True
                
                agent.store_transition(state, action, reward, next_state, done)
                agent.train()
                
                state = next_state
                last_action_step = step
            
            step += 1
            
        print(f"Episode {episode+1} Finished. Total Reward: {total_reward}")
        agent.update_target_network()
        traci.close()
        agent.save_model()