import os
import subprocess
import datetime
import json
from typing import Any, Optional
from core.agents.base import SigmaAgent

# --- SigmaFidelity™ Peter Agent (Recovery Specialist) ---
# Version: 3.0.1 (Enterprise Hardened)
# Mandate: HWB-QMS-9.3 (Disaster Recovery)
# Updated: Added flush=True for containerized logging

class PeterAgent(SigmaAgent):
    def __init__(self, db_url: Optional[str] = None):
        super().__init__(agent_id="Peter", db_url=db_url)
        self.project_root = "/app" if os.path.exists("/app/main_app.py") else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def execute(self, task_data: Any):
        task_id = task_data.get("task_id", "MANUAL")
        payload = task_data.get("payload", {})
        action_type = payload.get("type", "ghost_snapshot")

        if action_type == "ghost_snapshot":
            return self.create_ghost_checkpoint(task_id)
        elif action_type == "db_snapshot":
            return self.create_db_snapshot(task_id)
        else:
            print(f"[PETER] Unknown action type: {action_type}", flush=True)
            return False

    def create_ghost_checkpoint(self, task_id: str):
        """Creates a Git-based shadow snapshot of the current state."""
        try:
            tag = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
            self.log_telemetry(task_id, "GHOST_CHECKPOINT", "RUNNING")
            
            subprocess.run(["git", "add", "."], cwd=self.project_root, check=True)
            subprocess.run(["git", "commit", "-m", f"Peter: Ghost Checkpoint {tag}"], cwd=self.project_root, check=True)
            
            self.log_telemetry(task_id, "GHOST_CHECKPOINT", "SUCCESS", data={"tag": tag})
            print(f"[PETER] Ghost Checkpoint created: {tag}", flush=True)
            return True
        except Exception as e:
            self.handle_error(task_id, e)
            return False

    def create_db_snapshot(self, task_id: str):
        """Executes a PostgreSQL dump for institutional data security."""
        try:
            timestamp = datetime.datetime.now().strftime("%m-%d-%Y_%H%M")
            filename = f"hwb_db_snapshot_{timestamp}.sql"
            backup_dir = os.path.join(self.project_root, "backup")
            os.makedirs(backup_dir, exist_ok=True)
            
            dest_path = os.path.join(backup_dir, filename)
            
            self.log_telemetry(task_id, "DB_SNAPSHOT", "RUNNING")
            
            env = os.environ.copy()
            cmd = ["pg_dump", "-h", "db", "-U", "hwbdev", "-d", "hwb_dev_db", "-f", dest_path]
            env["PGPASSWORD"] = "hwbpassword"
            
            subprocess.run(cmd, env=env, check=True)
            
            self.log_telemetry(task_id, "DB_SNAPSHOT", "SUCCESS", data={"file": filename})
            print(f"[PETER] DB Snapshot created: {filename}", flush=True)
            return True
        except Exception as e:
            self.handle_error(task_id, e)
            return False
