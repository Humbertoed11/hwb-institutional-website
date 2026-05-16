import os
import sys

# Ensure core is importable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path.append(PROJECT_ROOT)

from core.agents.orchestrator import SigmaOrchestrator
from core.agents.base import SigmaAgent

class MockAgent(SigmaAgent):
    def execute(self, task_data):
        print(f"[MOCK] Executing task {task_data['task_id']} with payload {task_data['payload']}")
        return True

if __name__ == "__main__":
    # Use path that works with get_db lstrip('/')
    db_url = "sqlite:///database/test_sigma.db"
    if not os.path.exists("/app/database"):
        os.makedirs("/app/database")
        
    orch = SigmaOrchestrator(db_url=db_url)
    mock = MockAgent(agent_id="Peter", db_url=db_url)
    
    orch.register_agent(mock)
    
    # Enqueue a test recovery task
    orch.enqueue_task("RECOVERY_CHECKPOINT", {"type": "ghost_snapshot"})
    
    # Process the cycle
    orch.run_cycle()
    print("[SUCCESS] Orchestrator test cycle complete.")
