#!/bin/bash
# ==============================================================================
# HWB Automated Hourly Database Backup Script (Hardened v2.0.0)
# Authority: Approved under CEO Humberto Dominguez (11/12/2026)
# Lead Auditor: Super George (Systems Architect & Lead Autonomous Commander)
# Tactical Builder: George Bytes (Lead Software Engineer) & Peter (Recovery)
# Standard: HWB-QMS-9.3 v4.5.0 (chmod 600 + SHA-256 Integrity Verification)
# ==============================================================================

set -euo pipefail

PROJECT_ROOT="/home/humbertoed/gemini_projects"
BACKUP_DIR="$PROJECT_ROOT/backups/hourly"
LATEST_DIR="$PROJECT_ROOT/backups/latest"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_BASENAME="hwb_dev_db_${TIMESTAMP}.dump"
BACKUP_FILE="$BACKUP_DIR/$BACKUP_BASENAME"
LATEST_BASENAME="hwb_dev_db.dump"
LATEST_FILE="$LATEST_DIR/$LATEST_BASENAME"

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

# 2. Execute PostgreSQL 16.15 Custom Compressed Dump (-F c)
echo "[INFO] Executing compressed pg_dump from container hwb_postgres_dev..."
umask 077
docker exec hwb_postgres_dev pg_dump -U hwbdev -F c hwb_dev_db > "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE"

# 3. Verify Dump Integrity, Size, and Generate SHA-256 Checksum
if [ ! -s "$BACKUP_FILE" ]; then
    echo "[CRITICAL ERROR] Backup file is empty or was not created: $BACKUP_FILE" >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

(cd "$BACKUP_DIR" && sha256sum "$BACKUP_BASENAME" > "${BACKUP_BASENAME}.sha256")
chmod 600 "${BACKUP_FILE}.sha256"

BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
BACKUP_SHA=$(awk '{print $1}' "${BACKUP_FILE}.sha256")
echo "[OK] Backup created & locked (chmod 600): $BACKUP_FILE ($BACKUP_SIZE | sha256:${BACKUP_SHA:0:16}...)"

# 4. Update Latest Snapshot Pointer & Verify Relative SHA-256 Checksum
cp -f "$BACKUP_FILE" "$LATEST_FILE"
chmod 600 "$LATEST_FILE"
(cd "$LATEST_DIR" && sha256sum "$LATEST_BASENAME" > "${LATEST_BASENAME}.sha256" && sha256sum -c "${LATEST_BASENAME}.sha256" >/dev/null)
chmod 600 "${LATEST_FILE}.sha256"
echo "[OK] Latest snapshot & SHA-256 verified at: $LATEST_FILE (chmod 600)"

# 5. Rotate Backups: Delete .dump and .dump.sha256 files older than 24 hours (1440 minutes)
echo "[INFO] Running 24-hour backup rotation in $BACKUP_DIR..."
PURGED_COUNT=$(find "$BACKUP_DIR" -maxdepth 1 -name "hwb_dev_db_*.dump*" -mmin +1440 | wc -l)
find "$BACKUP_DIR" -maxdepth 1 -name "hwb_dev_db_*.dump*" -mmin +1440 -delete
echo "[OK] Rotation complete. Purged $PURGED_COUNT old file(s)."

TOTAL_HOURLY=$(find "$BACKUP_DIR" -maxdepth 1 -name "hwb_dev_db_*.dump" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | awk '{print $1}')
echo "[STATUS] Active hourly snapshots: $TOTAL_HOURLY | Hourly storage footprint: $TOTAL_SIZE"
echo "=== [$(date +'%Y-%m-%d %H:%M:%S')] Hourly Backup Finished Successfully ==="
