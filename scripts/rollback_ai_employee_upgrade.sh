#!/usr/bin/env bash
# ==============================================================================
# HWB Cleaning 1-Command Rollback: 24/7 Enterprise AI Employee Upgrade (BUG-163)
# Restores scripts/telegram_listener.py, worker_launcher.py, and main_app.py
# to their exact pre-upgrade state and restarts hwb_web_app & hwb_agent_worker.
# ==============================================================================
set -e

BACKUP_DIR="/home/humbertoed/gemini_projects/backups/ai_employee_pre_upgrade_20261029"
WEB_DIR="/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "[ERROR] Backup directory $BACKUP_DIR not found."
    exit 1
fi

echo "[ROLLBACK] Restoring pre-upgrade files from $BACKUP_DIR..."
cp "$BACKUP_DIR/telegram_listener.py.bak" "$WEB_DIR/scripts/telegram_listener.py"
cp "$BACKUP_DIR/worker_launcher.py.bak" "$WEB_DIR/worker_launcher.py"
cp "$BACKUP_DIR/main_app.py.bak" "$WEB_DIR/main_app.py"
rm -rf "$WEB_DIR/core/ai_employee"
rm -f "$WEB_DIR/blueprints/ai_employee_api.py"

echo "[ROLLBACK] Restarting hwb_web_app and hwb_agent_worker..."
docker restart hwb_web_app hwb_agent_worker

echo "[ROLLBACK] Complete. System restored to exact pre-upgrade state."
