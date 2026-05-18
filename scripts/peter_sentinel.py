import os
import shutil
import time
from datetime import datetime
from dotenv import load_dotenv

# SigmaFidelity™ Peter Sentinel v1.0
# Standard: HWB-QMS-9.3.1 (Shadow Snapshots)
# Responsibility: Peter (Recovery Specialist)

def create_shadow_snapshot():
    """Creates a local 'Shadow Snapshot' of critical logic and memory files."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    snapshot_dir = f"HWB-COMPANY/HWB-IT/HWB-IT-SYSTEM-LOGS/shadow_snapshots/{timestamp}"
    
    # Critical Logic paths to protect
    targets = [
        "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/core/models",
        "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/core/agents",
        "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/main_app.py",
        "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/sigma_orchestrator.py",
        ".env"
    ]
    
    os.makedirs(snapshot_dir, exist_ok=True)
    
    print(f"--- SigmaFidelity: Peter Sentinel Initiating Shadow Snapshot ({timestamp}) ---")
    
    for target in targets:
        if os.path.exists(target):
            dest = os.path.join(snapshot_dir, os.path.basename(target))
            if os.path.isdir(target):
                shutil.copytree(target, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(target, dest)
            print(f"[SENTINEL] Protected: {target}")
        else:
            print(f"[SENTINEL] WARNING: Target missing - {target}")
            
    # Cleanup old snapshots (Keep last 10)
    parent_dir = "HWB-COMPANY/HWB-IT/HWB-IT-SYSTEM-LOGS/shadow_snapshots"
    snapshots = sorted([d for d in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, d))])
    if len(snapshots) > 10:
        for old in snapshots[:-10]:
            shutil.rmtree(os.path.join(parent_dir, old))
            print(f"[SENTINEL] Rotated: {old}")

if __name__ == "__main__":
    # Load env for absolute path resolution if needed
    load_dotenv()
    
    # One-off execution (intended to be called by watchdog or crontab)
    try:
        create_shadow_snapshot()
    except Exception as e:
        print(f"[SENTINEL] CRITICAL FAILURE: {e}")
