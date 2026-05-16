import os
import time
import uuid
import datetime
import json
from typing import List, Optional
from core.agents.base import SigmaAgent
from core.services.database import db_cursor

# --- SigmaFidelity™ Institutional Orchestrator ---
# Version: 1.0.1 (George / System Architect)
# Mandate: HWB-QMS-8.6 (Routine Governance)
# Updated: Added flush=True for containerized logging

class SigmaOrchestrator(SigmaAgent):
    def __init__(self, db_url: Optional[str] = None):
        super().__init__(agent_id="George", db_url=db_url)
        self.active_agents = {}
        self.setup_orchestration_tables()

    def setup_orchestration_tables(self):
        """Initializes the task queue and routine schedule tables."""
        sql_sqlite = [
            "CREATE TABLE IF NOT EXISTS task_queue (task_id TEXT PRIMARY KEY, task_type TEXT, priority INTEGER, payload TEXT, status TEXT, created_at DATETIME, started_at DATETIME, completed_at DATETIME)",
            "CREATE TABLE IF NOT EXISTS routine_schedule (routine_id TEXT PRIMARY KEY, task_type TEXT, frequency_seconds INTEGER, last_run DATETIME, status TEXT)"
        ]
        sql_pg = [
            "CREATE TABLE IF NOT EXISTS task_queue (task_id TEXT PRIMARY KEY, task_type TEXT, priority INTEGER, payload TEXT, status TEXT DEFAULT 'PENDING', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, started_at TIMESTAMP, completed_at TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS routine_schedule (routine_id TEXT PRIMARY KEY, task_type TEXT, frequency_seconds INTEGER, last_run TIMESTAMP, status TEXT DEFAULT 'ACTIVE')"
        ]
        
        scheme = "postgres" if "postgres" in self.db_url else "sqlite"
        statements = sql_pg if scheme == "postgres" else sql_sqlite
        
        with db_cursor(self.db_url) as cur:
            for stmt in statements:
                cur.execute(stmt)

    def register_agent(self, agent_instance: SigmaAgent):
        """Registers a specialized agent with the orchestrator."""
        self.active_agents[agent_instance.agent_id] = agent_instance
        print(f"[ORCHESTRATOR] Registered Agent: {agent_instance.agent_id}", flush=True)

    def enqueue_task(self, task_type: str, payload: dict, priority: int = 3):
        """Adds a new task to the institutional queue."""
        task_id = str(uuid.uuid4())
        payload_json = json.dumps(payload)
        
        with db_cursor(self.db_url) as cur:
            if "postgres" in self.db_url:
                cur.execute("INSERT INTO task_queue (task_id, task_type, priority, payload, status) VALUES (%s, %s, %s, %s, %s)",
                             (task_id, task_type, priority, payload_json, "PENDING"))
            else:
                cur.execute("INSERT INTO task_queue (task_id, task_type, priority, payload, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                             (task_id, task_type, priority, payload_json, "PENDING", datetime.datetime.now()))
        
        print(f"[ORCHESTRATOR] Enqueued Task: {task_type} (ID: {task_id})", flush=True)
        return task_id

    def run_cycle(self):
        """Processes one task from the queue based on priority."""
        try:
            with db_cursor(self.db_url) as cur:
                # 1. Fetch highest priority pending task
                cur.execute("SELECT task_id, task_type, payload FROM task_queue WHERE status = 'PENDING' ORDER BY priority ASC, created_at ASC LIMIT 1")
                task = cur.fetchone()
                
                if not task:
                    return False

                task_id, task_type, payload_json = task
                payload = json.loads(payload_json)

                # 2. Mark as running
                if "postgres" in self.db_url:
                    cur.execute("UPDATE task_queue SET status = 'RUNNING', started_at = CURRENT_TIMESTAMP WHERE task_id = %s", (task_id,))
                else:
                    cur.execute("UPDATE task_queue SET status = 'RUNNING', started_at = ? WHERE task_id = ?", (datetime.datetime.now(), task_id))
            
            # 3. Dispatch to Agent
            success = self.dispatch(task_id, task_type, payload)

            # 4. Finalize
            with db_cursor(self.db_url) as cur:
                final_status = "COMPLETED" if success else "FAILED"
                if "postgres" in self.db_url:
                    cur.execute("UPDATE task_queue SET status = %s, completed_at = CURRENT_TIMESTAMP WHERE task_id = %s", (final_status, task_id))
                else:
                    cur.execute("UPDATE task_queue SET status = ?, completed_at = ? WHERE task_id = ?", (final_status, datetime.datetime.now(), task_id))
            
            return True
        except Exception as e:
            self.handle_error("ORCHESTRATOR_CYCLE", e)
            return False

    def dispatch(self, task_id: str, task_type: str, payload: dict):
        """Surgically dispatches a task to the correct agent."""
        # This mapping will grow as agents are hardened
        agent_map = {
            "FEDERAL_SYNC": "George",
            "MARKETING_DISPATCH": "Lauri",
            "RECOVERY_CHECKPOINT": "Peter"
        }
        
        agent_id = agent_map.get(task_type)
        if not agent_id or agent_id not in self.active_agents:
            print(f"[ERROR] No active agent registered for {task_type}", flush=True)
            return False

        agent = self.active_agents[agent_id]
        print(f"[ORCHESTRATOR] Dispatching {task_type} to {agent_id}...", flush=True)
        
        try:
            agent.execute({"task_id": task_id, "payload": payload})
            self.log_telemetry(task_id, f"DISPATCH_{task_type}", "SUCCESS")
            return True
        except Exception as e:
            hard_break = agent.handle_error(task_id, e)
            if hard_break:
                print(f"[CRITICAL] {agent_id} halted due to hard break.", flush=True)
            return False

    def execute(self, task_data: dict):
        """Orchestrator's internal execution (e.g., self-healing)."""
        pass
