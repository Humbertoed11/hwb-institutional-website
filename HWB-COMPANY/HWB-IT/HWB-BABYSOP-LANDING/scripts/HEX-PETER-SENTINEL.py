import os
import shutil
import subprocess
from datetime import datetime
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# HEXGROWTH: Peter Sentinel (Recovery Specialist)
# Standard: HEX-SOP-9.3 (Disaster Recovery & Data Restoration)
# Responsibility: Peter (Recovery Specialist)

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")
SOURCE_ROOT = "/app" # Path inside container
SNAPSHOT_BASE = "/app/HEX-DATA/RECOVERY-ZONE"

def run_db_snapshot():
    """Executes a binary database snapshot of the Alpha Spine."""
    timestamp = datetime.now().strftime("%m-%d-%Y-%H%M")
    backup_file = f"{SNAPSHOT_BASE}/hex_dev_db_{timestamp}.sql"
    
    print(f"--- HEXGROWTH: Peter initiating DB Snapshot ({timestamp}) ---")
    
    try:
        # Since we are inside hex_web_app, we use pg_dump directly (it must be installed)
        # Or we use the PG_URL components
        cmd = [
            "pg_dump", 
            "-h", "hex_postgis_db", 
            "-U", "hexadmin", 
            "-d", "hex_dev_db",
            "-f", backup_file
        ]
        # Set PGPASSWORD env to avoid interactive prompt
        os.environ["PGPASSWORD"] = "hexpassword"
        subprocess.run(cmd, check=True)
        print(f"[PETER] Alpha Spine Snapshotted: {backup_file}")
        return True
    except Exception as e:
        print(f"[PETER] DB SNAPSHOT FAILURE: {e}")
        return False

def run_environment_freeze():
    """Freezes the current application logic and configurations."""
    timestamp = datetime.now().strftime("%m-%d-%Y-%H%M")
    freeze_dir = f"{SNAPSHOT_BASE}/FREEZE-{timestamp}"
    
    targets = [
        f"{SOURCE_ROOT}/main_app.py",
        f"{SOURCE_ROOT}/templates",
        f"{SOURCE_ROOT}/qms_index.json",
        f"{SOURCE_ROOT}/scripts",
        f"{SOURCE_ROOT}/.env"
    ]
    
    print(f"--- HEXGROWTH: Peter initiating Environment Freeze ({timestamp}) ---")
    os.makedirs(freeze_dir, exist_ok=True)
    
    for target in targets:
        if os.path.exists(target):
            name = os.path.basename(target)
            dest = os.path.join(freeze_dir, name)
            if os.path.isdir(target):
                shutil.copytree(target, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(target, dest)
            print(f"[PETER] Frozen: {name}")
    
    # Rotate freezes (Keep last 5)
    if os.path.exists(SNAPSHOT_BASE):
        freezes = sorted([d for d in os.listdir(SNAPSHOT_BASE) if d.startswith("FREEZE-")])
        if len(freezes) > 5:
            for old in freezes[:-5]:
                old_path = os.path.join(SNAPSHOT_BASE, old)
                shutil.rmtree(old_path)
                print(f"[PETER] Rotated Freeze: {old}")

if __name__ == "__main__":
    os.makedirs(SNAPSHOT_BASE, exist_ok=True)
    
    # 1. Protect the Spine
    run_db_snapshot()
    
    # 2. Freeze the Logic
    run_environment_freeze()
    
    print("--- HEXGROWTH: Recovery Cycle Complete ---")
