import os
import sys
import traci

def run_simulation(sumocfg_path, steps=1000):
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    
    sumo_cmd = ["sumo", "-c", sumocfg_path, "--no-step-log", "true", "--waiting-time-memory", "10000"]
    
    traci.start(sumo_cmd)
    
    tls_id = traci.trafficlight.getIDList()[0] if traci.trafficlight.getIDList() else None
    lanes = traci.lane.getIDList()
    
    for step in range(steps):
        traci.simulationStep()
        
        current_phase = traci.trafficlight.getPhase(tls_id) if tls_id else None
        
        counts = {}
        wait_times = {}
        
        for lane in lanes:
            if not lane.startswith(":"):
                counts[lane] = traci.lane.getLastStepVehicleNumber(lane)
                wait_times[lane] = traci.lane.getWaitingTime(lane)
        
        print(f"Step: {step}")
        print(f"TLS Phase: {current_phase}")
        print(f"Counts: {counts}")
        print(f"Wait Times: {wait_times}")
        print("-" * 30)

    traci.close()

if __name__ == "__main__":
    cfg = "flowgrid.sumocfg"
    run_simulation(cfg, steps=50)
