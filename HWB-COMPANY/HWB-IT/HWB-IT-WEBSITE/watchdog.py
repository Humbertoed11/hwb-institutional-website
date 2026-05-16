import os
import time
import subprocess
import requests
from datetime import datetime

# --- SigmaFidelity™ Watchdog v1.0 ---
# Mandated by HWB-QMS-9.2 (Proactive Diagnostics)

LOG_PATH = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-SYSTEM-LOGS/HWB-WEB Server.log"
WEBSITE_DIR = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE"
HEALTH_URL = "http://127.0.0.1:5000/admin/operations"

def log_event(message):
    timestamp = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    print(f"[{timestamp}] [WATCHDOG] {message}")

def check_server_health():
    try:
        response = requests.get(HEALTH_URL, timeout=5)
        if response.status_code == 500:
            return "ERROR_500"
        return "HEALTHY"
    except Exception as e:
        return "DOWN"

def restart_suite():
    log_event("INTEGRITY BREACH DETECTED: Restarting SigmaFidelity Suite...")
    # Execute master startup script to refresh all services
    subprocess.run(["bash", "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/scripts/startup_master.sh"], check=True)
    log_event("RECOVERY COMPLETE: Systems Synchronized.")

def monitor_logs():
    log_event("WATCHDOG ACTIVE: Monitoring Institutional Integrity...")
    
    # Simple tail-based monitoring for critical error patterns
    with subprocess.Popen(['tail', '-F', LOG_PATH], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
        for line in proc.stdout:
            if "TemplateSyntaxError" in line or "sqlite3.OperationalError: database is locked" in line:
                log_event(f"CRITICAL PATTERN DETECTED: {line.strip()}")
                restart_suite()
            
            # Periodically check HTTP health as a secondary layer
            if int(time.time()) % 60 == 0:
                health = check_server_health()
                if health != "HEALTHY":
                    log_event(f"HTTP HEALTH FAILURE: {health}")
                    restart_suite()

if __name__ == "__main__":
    try:
        monitor_logs()
    except KeyboardInterrupt:
        log_event("WATCHDOG SUSPENDED.")
