#!/bin/bash
# ==============================================================================
# HWB Automated Hourly Database Backup Script
# Authority: Approved under SO-COM-001-DIR-01 (CEO Humberto Dominguez)
# Lead Auditor: Super George (Systems Architect & Lead Autonomous Commander)
# Tactical Builder: George Bytes (Lead Software Engineer)
# Standard: Mandate 12 (Disaster Recovery & Zero Data Loss)
# ==============================================================================

set -euo pipefail

PROJECT_ROOT="/home/humbertoed/gemini_projects"
BACKUP_DIR="$PROJECT_ROOT/backups/hourly"
LATEST_DIR="$PROJECT_ROOT/backups/latest"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/hwb_dev_db_${TIMESTAMP}.dump"
LATEST_FILE="$LATEST_DIR/hwb_dev_db.dump"

mkdir -p "$BACKUP_DIR" "$LATEST_DIR" "$LOG_DIR"

echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Starting HWB Hourly Database Backup ==="

# 1. Pre-flight Disk Space Check (>2GB required)
AVAILABLE_KB=$(df "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
REQUIRED_KB=2097152 # 2 GB in KB

if [ "$AVAILABLE_KB" -lt "$REQUIRED_KB" ]; then
    echo "[CRITICAL ERROR] Insufficient disk space: ${AVAILABLE_KB}KB available, ${REQUIRED_KB}KB required. Aborting backup." >&2
    exit 1
fi
echo "[OK] Disk space check passed: $(awk "BEGIN {print int($AVAILABLE_KB/1024/1024)}")GB available."

# 2. Execute PostgreSQL Custom Compressed Dump (-F c)
echo "[INFO] Executing compressed pg_dump from container hwb_postgres_dev..."
docker exec hwb_postgres_dev pg_dump -U hwbdev -F c hwb_dev_db > "$BACKUP_FILE"

# 3. Verify Dump Integrity and Size
if [ ! -s "$BACKUP_FILE" ]; then
    echo "[CRITICAL ERROR] Backup file is empty or was not created: $BACKUP_FILE" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
echo "[OK] Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"

# 4. Update Latest Snapshot Pointer
cp -f "$BACKUP_FILE" "$LATEST_FILE"
echo "[OK] Latest snapshot updated at: $LATEST_FILE"

# 5. Rotate Backups: Delete files older than 24 hours (1440 minutes)
echo "[INFO] Running 24-hour backup rotation in $BACKUP_DIR..."
PURGED_COUNT=$(find "$BACKUP_DIR" -name "hwb_dev_db_*.dump" -mmin +1440 | wc -l)
find "$BACKUP_DIR" -name "hwb_dev_db_*.dump" -mmin +1440 -delete
echo "[OK] Rotation complete. Purged $PURGED_COUNT old dump(s)."

TOTAL_HOURLY=$(ls -1 "$BACKUP_DIR"/hwb_dev_db_*.dump 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | awk '{print $1}')
echo "[STATUS] Active hourly snapshots: $TOTAL_HOURLY | Hourly storage footprint: $TOTAL_SIZE"
echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Hourly Backup Finished Successfully ==="
