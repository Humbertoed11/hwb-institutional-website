import subprocess
import time
import os

# --- SigmaFidelity™ Worker Launcher v1.0 ---
# Supervises the autonomous agents within the container environment.

AGENTS = [
    ["python", "sigma_orchestrator.py"],
    # ["python", "news_updater.py"],
    ["python", "watchdog.py"],
    ["python", "scripts/telegram_listener.py"],
    ["python", "scripts/tessa_regression_suite.py", "--daemon", "--interval", "3600"]
]

def launch_agents():
    print("[WORKER] Initiating SigmaFidelity™ Agent Suite...", flush=True)
    processes = []
    
    for cmd in AGENTS:
        print(f"[WORKER] Starting: {' '.join(cmd)}", flush=True)
        # Using stdout=None to let logs flow to the container's stdout
        p = subprocess.Popen(cmd)
        processes.append(p)

    MAX_RESTARTS = 5
    restart_counts = [0] * len(AGENTS)
    last_start_times = [time.time()] * len(AGENTS)

    try:
        while True:
            now_ts = time.time()
            for i, p in enumerate(processes):
                if p is None:
                    continue
                if p.poll() is not None:
                    if now_ts - last_start_times[i] > 60.0:
                        restart_counts[i] = 0
                    restart_counts[i] += 1
                    if restart_counts[i] > MAX_RESTARTS:
                        print(
                            f"[WORKER] CIRCUIT BREAKER TRIPPED (SEC-13): Agent {AGENTS[i][1]} exceeded {MAX_RESTARTS} rapid crashes. Halting respawn.",
                            flush=True,
                        )
                        processes[i] = None
                        continue
                    print(f"[WORKER] CRITICAL: Agent {AGENTS[i][1]} died (attempt {restart_counts[i]}/{MAX_RESTARTS}). Restarting...", flush=True)
                    processes[i] = subprocess.Popen(AGENTS[i])
                    last_start_times[i] = time.time()
            # 24/7 Dead-Man's Switch: Verify AIEmployeeHeartbeat liveness for telegram_listener.py
            try:
                from core.ai_employee import get_ai_employee
                emp = get_ai_employee()
                emp.record_heartbeat("hwb_worker_supervisor", {"supervised_agents": len(processes)})
            except Exception:
                pass
            time.sleep(10)
    except KeyboardInterrupt:
        print("[WORKER] Terminating Agent Suite...", flush=True)
        for p in processes:
            p.terminate()

if __name__ == "__main__":
    # Wait for the DB to be ready before starting agents
    time.sleep(5)
    launch_agents()
