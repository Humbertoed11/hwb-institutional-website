import subprocess
import time
import os

# --- SigmaFidelity™ Worker Launcher v1.0 ---
# Supervises the autonomous agents within the container environment.

AGENTS = [
    ["python", "sigma_orchestrator.py"],
    ["python", "news_updater.py"],
    ["python", "watchdog.py"]
]

def launch_agents():
    print("[WORKER] Initiating SigmaFidelity™ Agent Suite...", flush=True)
    processes = []
    
    for cmd in AGENTS:
        print(f"[WORKER] Starting: {' '.join(cmd)}", flush=True)
        # Using stdout=None to let logs flow to the container's stdout
        p = subprocess.Popen(cmd)
        processes.append(p)

    try:
        while True:
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    print(f"[WORKER] CRITICAL: Agent {AGENTS[i][1]} died. Restarting...", flush=True)
                    processes[i] = subprocess.Popen(AGENTS[i])
            time.sleep(10)
    except KeyboardInterrupt:
        print("[WORKER] Terminating Agent Suite...", flush=True)
        for p in processes:
            p.terminate()

if __name__ == "__main__":
    # Wait for the DB to be ready before starting agents
    time.sleep(5)
    launch_agents()
