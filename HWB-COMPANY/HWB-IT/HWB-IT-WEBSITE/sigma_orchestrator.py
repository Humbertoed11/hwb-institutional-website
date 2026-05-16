import os
import sys
import time
from dotenv import load_dotenv

# --- SigmaFidelity™ Master Orchestration Layer ---
# Version: 1.0.0 (George / System Architect)
# Mandate: HWB-QMS-8.6 (Routine Governance)

# Ensure institutional core is importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from core.agents.orchestrator import SigmaOrchestrator
from core.agents.george import GeorgeAgent
from core.agents.peter import PeterAgent

def main():
    # Load Institutional Secrets
    load_dotenv(os.path.join(BASE_DIR, "../../..", ".env"))
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[FATAL] DATABASE_URL not found. Orchestrator halting.")
        return

    print("--- SigmaFidelity™ Enterprise Orchestrator Initializing ---")
    
    # 1. Initialize Orchestrator Core
    orchestrator = SigmaOrchestrator(db_url=db_url)
    
    # 2. Register Specialized Agents
    orchestrator.register_agent(GeorgeAgent(db_url=db_url))
    orchestrator.register_agent(PeterAgent(db_url=db_url))
    
    # 3. Queue Periodic Routines (If Queue is Empty)
    # Note: In a production loop, these would be managed by the routine_schedule table
    
    print("[ORCHESTRATOR] Entering Autonomous Cycle...")
    
    try:
        while True:
            # Check for tasks
            task_processed = orchestrator.run_cycle()
            
            if not task_processed:
                # If no tasks, we check the routine schedule
                # (Logic to trigger periodic SAM Syncs or Checkpoints)
                pass
                
            time.sleep(10) # 10-second industrial heartbeat
    except KeyboardInterrupt:
        print("[ORCHESTRATOR] Manual Halt Received. Shutting down gracefully.")
    except Exception as e:
        orchestrator.log_friction("Orchestrator Panic", str(e))
        print(f"[FATAL] Orchestrator Panic: {e}")

if __name__ == "__main__":
    main()
