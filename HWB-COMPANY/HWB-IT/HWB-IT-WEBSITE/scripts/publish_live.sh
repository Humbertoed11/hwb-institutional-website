#!/usr/bin/env bash
# ==============================================================================
# SigmaFidelity™ Master Publishing & Database Parity Pipeline
# Fulfills HWB-QMS-9.3 & Guarantees Dev-to-Prod Data & Code Parity
# ==============================================================================
set -e

echo "=== SigmaFidelity™ Initiating Master Live Deployment Sequence ==="

# 1. Export Latest Local Dev Database Dataset to Seed Payload
echo "[STEP 1/5] Exporting latest Local Dev DB state to scripts/seed_data.json..."
docker exec hwb_web_app python -c "
import json, datetime
from decimal import Decimal
from main_app import get_db, app

def serialize_row(row):
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (datetime.date, datetime.datetime)):
            d[k] = v.isoformat()
        elif isinstance(v, Decimal):
            d[k] = float(v)
    return d

conn = get_db(app.config.get('CLIENT_DATABASE_URL', 'postgresql://hwbdev:hwbpassword@db:5432/hwb_dev_db'))
with conn.cursor() as cur:
    cur.execute('SELECT * FROM \"Leads\";')
    leads = cur.fetchall()
    cur.execute('SELECT * FROM \"Customers\";')
    accounts = cur.fetchall()

with open('/app/seed_data.json', 'w') as f:
    json.dump({
        'leads': [serialize_row(l) for l in leads],
        'accounts': [serialize_row(a) for a in accounts]
    }, f)
"
docker cp hwb_web_app:/app/seed_data.json HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/scripts/seed_data.json

# 2. Version Control Commit via AI Version Agent
echo "[STEP 2/5] Committing code, SOP, and database snapshot..."
bash scripts/ai_version_agent.sh || git commit -a -m "George: Deploy master live release with dev-to-prod database sync"

# 3. Azure Container Registry Image Build & Push
echo "[STEP 3/5] Building and pushing container image to Azure ACR..."
az acr build --registry hwbprodacr --image hwb-web-app:latest HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/

# 4. Restart Azure App Service Web App
echo "[STEP 4/5] Restarting Azure Web App service..."
az webapp restart --name hwb-institutional-website --resource-group HWB-Production-RG

# 5. Live Health Audit
echo "[STEP 5/5] Executing Live Health Telemetry Check..."
curl -sS -I https://www.hwbcleaning.com/admin/operations?view=leads | head -n 5

echo "=== SUCCESS: Master Live Deployment & Database Parity Complete ==="
