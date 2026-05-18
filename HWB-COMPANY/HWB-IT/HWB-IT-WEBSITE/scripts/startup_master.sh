#!/bin/bash

# Startup Master Batch File for SigmaFidelity
# Version 1.7.0 (Institutional Containerized Standard)
# Mandated by HWB-QMS-9.5 (System Containerization)

# Dynamically determine the project root relative to the script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IT_LOG_DIR="$PROJECT_ROOT/HWB-COMPANY/HWB-IT/HWB-IT-SYSTEM-LOGS"
IT_WEBSITE_DIR="$PROJECT_ROOT/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE"

# Load Institutional Secrets (Mandated by HWB-QMS-9.5)
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading Institutional Secrets from .env..."
    set -a && source "$PROJECT_ROOT/.env" && set +a
else
    echo "CRITICAL WARNING: Root .env file not found. System operations may fail."
fi

# Run Self-Healing & Optimization Sequence (Mandated by HWB-QMS-9.6)
bash "$IT_WEBSITE_DIR/scripts/hwb_self_healing.sh"

echo "--- SigmaFidelity: Initiating Containerized Startup Sequence ---"

# Initialize Session Recovery Black Box (Mandated by HWB-QMS-9.3)
echo "Verifying Session Resilience Black Box..."
if [ ! -f "$PROJECT_ROOT/HWB-SESSION-RECOVERY.md" ]; then
    echo "Initializing SigmaFidelity™ Session Recovery Scratchpad..."
    cat <<'INNEREOF' > "$PROJECT_ROOT/HWB-SESSION-RECOVERY.md"
# SigmaFidelity™ Session Recovery Scratchpad

| **Field** | **Current State** |
| :--- | :--- |
| **Objective** | System Boot - Awaiting Directives |
| **Heat Zone Files** | N/A |
| **Last Action** | System Initialized via startup_master.sh |
| **Next Step** | Awaiting Executive Command |
| **Session ID** | $(date +'%Y-%m-%d-%H%M')-STARTUP |
| **Timestamp** | $(date +'%m/%d/%Y %I:%M %p') |

---
*Note: This file is a temporary "Black Box" for immediate context recovery. It must be updated after every successful Directive.*
INNEREOF
fi

# Change to Project Root for execution
cd "$PROJECT_ROOT" || exit

# 1. Start/Verify Containerized Suite
echo "Deploying SigmaFidelity™ Infrastructure via Docker..."
docker-compose up -d

# 2. Verify Database Stability
echo "Verifying Production Database Integrity..."
docker exec hwb_postgres_dev pg_isready -U hwbdev -d hwb_dev_db

# 3. Start the Traffic Director (Port 8000 Gateway)
echo "Starting Traffic Director Gateway..."
# pkill any existing native director if present
pkill -f "proxy_gateway.py" 2>/dev/null
nohup python3 "$PROJECT_ROOT/scripts/proxy_gateway.py" > "$IT_LOG_DIR/traffic_director.log" 2>&1 &
echo "Traffic Director active on Port 8000"

# 4. Run Production Diagnostics
echo "Running Production Diagnostics..."
docker exec hwb_web_app python "diag_dashboard.py"
echo "Diagnostics Complete."

echo "--- Startup Sequence Finished ---"
echo "Project Location: $IT_WEBSITE_DIR"
echo "Logs Location: $IT_LOG_DIR"
echo "Monitor logs for real-time status: docker logs -f hwb_web_app"
