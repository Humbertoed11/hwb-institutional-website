#!/bin/bash
# ==============================================================================
# SigmaFidelity™ Instant Rollback Script — Lead Notes Workflow (Pre-v5.5.0)
# Restores exact byte-for-byte pre-change files and flushes Gunicorn container
# ==============================================================================
set -e

SNAP_DIR="/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/.snapshots/pre_lead_notes_v550"
WEB_DIR="/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE"

if [ ! -d "$SNAP_DIR" ]; then
    echo "ERROR: Snapshot directory $SNAP_DIR not found."
    exit 1
fi

echo "--- Restoring Pre-Lead-Notes Files from $SNAP_DIR ---"
cp -a "$SNAP_DIR/schema_engine.py" "$WEB_DIR/database/schema_engine.py"
cp -a "$SNAP_DIR/crm_api.py" "$WEB_DIR/blueprints/crm_api.py"
cp -a "$SNAP_DIR/operations.py" "$WEB_DIR/blueprints/operations.py"
cp -a "$SNAP_DIR/search.py" "$WEB_DIR/core/services/search.py"
cp -a "$SNAP_DIR/backoffice_operations.html" "$WEB_DIR/templates/backoffice_operations.html"
cp -a "$SNAP_DIR/backoffice_operations_core.js" "$WEB_DIR/static/js/backoffice_operations_core.js"
cp -a "$SNAP_DIR/test_web_performance_rack_14.py" "$WEB_DIR/scripts/test_web_performance_rack_14.py"

echo "--- Restarting hwb_web_app Container ---"
docker restart hwb_web_app

echo "✅ Rollback complete. All Lead Notes files restored to pre-change state."
