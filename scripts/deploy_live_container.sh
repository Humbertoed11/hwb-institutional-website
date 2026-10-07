#!/bin/bash
# --- SigmaFidelity™ Automated Container Deployment Script ---
# Standard: HWB-QMS-9.5 (System Containerization)
# Version: 2.0.0
# George (Systems Architect) - Poka-Yoke Automated Deploy

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 1. Load Environment Settings & Secrets
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "Loading environment settings..."
    set -a && source "$PROJECT_ROOT/.env" && set +a
else
    echo "CRITICAL: .env file missing in project root."
    exit 1
fi

ACR_URL="hwbprodacr.azurecr.io"
CURRENT_HASH=$(git rev-parse --short HEAD)
CURRENT_DATE=$(date +%Y-%m-%d)
IMAGE_TAG="v5.4-$CURRENT_DATE-$CURRENT_HASH"
FULL_IMAGE="$ACR_URL/sigmafidelity-web:$IMAGE_TAG"

echo "--- SigmaFidelity: Starting Zero-Touch Production Deploy (Tag: $IMAGE_TAG) ---"

VERSION_FILE="$PROJECT_ROOT/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/version.json"

# Write production version stamp for container compilation
cat <<EOF > "$VERSION_FILE"
{
  "version": "v5.4.1",
  "commit": "$CURRENT_HASH",
  "build_date": "$(date '+%Y-%m-%d %I:%M %p')",
  "build_tag": "$IMAGE_TAG",
  "environment": "AZURE_PRODUCTION"
}
EOF
echo "Authoritative production version.json generated (commit: $CURRENT_HASH, env: AZURE_PRODUCTION)."

# 2. Local Container Compilation
echo "Compiling web application image..."
docker build -t "$FULL_IMAGE" -f "$PROJECT_ROOT/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/Dockerfile" "$PROJECT_ROOT/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE"
BUILD_STATUS=$?

# Immediately restore local development version stamp for local container parity
cat <<EOF > "$VERSION_FILE"
{
  "version": "v5.4.1",
  "commit": "$CURRENT_HASH",
  "build_date": "$(date '+%Y-%m-%d %I:%M %p')",
  "build_tag": "v5.4.1-$CURRENT_HASH",
  "environment": "LOCAL_DEV"
}
EOF

if [ $BUILD_STATUS -ne 0 ]; then
    echo "ERROR: Local Docker build failed."
    exit 1
fi

# 3. Registry Authentication & Push
echo "Authenticating with private container registry..."
docker login "$ACR_URL" -u "$acr_username" -p "$acr_password"
if [ $? -ne 0 ]; then
    echo "ERROR: Registry login failed."
    exit 1
fi

echo "Pushing container image to ACR..."
docker push "$FULL_IMAGE"
if [ $? -ne 0 ]; then
    echo "ERROR: Pushing image to ACR failed."
    exit 1
fi

# 4. Update Azure Web App Configuration & Reload
echo "Updating Azure Web App configuration to use new image: $IMAGE_TAG"
docker exec hwb_web_app python -c "
import os, requests, msal
from dotenv import load_dotenv
load_dotenv()
CLIENT_ID = os.getenv('GRAPH_API_PROD_APPLICATION_ID')
CLIENT_SECRET = os.getenv('GRAPH_API_PROD_SECRET_VALUE')
TENANT_ID = os.getenv('GRAPH_API_PROD_TENANT_ID')
SUBSCRIPTION_ID = 'd778faac-02a4-4d74-9881-199994f2bd98'
APP_NAME = 'hwb-institutional-website'
RG = 'HWB-Production-RG'
NEW_IMAGE = '$FULL_IMAGE'

AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
SCOPE = ['https://management.azure.com/.default']
app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
result = app.acquire_token_for_client(scopes=SCOPE)
token = result.get('access_token')

if not token:
    print('Failed to get Azure token')
    exit(1)

headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# 1. Update linuxFxVersion and appCommandLine
url_config = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/config/web?api-version=2022-03-01'
config_payload = {
    'properties': {
        'linuxFxVersion': f'DOCKER|{NEW_IMAGE}',
        'appCommandLine': ''
    }
}
res_config = requests.patch(url_config, headers=headers, json=config_payload)

if res_config.status_code in [200, 202]:
    print(f'SUCCESS: Azure Web App configuration (Image & Startup) updated.')
else:
    print(f'FAILED: Azure config update returned {res_config.status_code}: {res_config.text}')
    exit(1)

# 2. Update WEBSITES_PORT in App Settings
url_settings_list = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/config/appsettings/list?api-version=2022-03-01'
res_settings_list = requests.post(url_settings_list, headers=headers)
settings = res_settings_list.json().get('properties', {})
settings['WEBSITES_PORT'] = '5000'

url_settings_put = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/config/appsettings?api-version=2022-03-01'
res_settings_put = requests.put(url_settings_put, headers=headers, json={'properties': settings})
if res_settings_put.status_code == 200:
    print('SUCCESS: WEBSITES_PORT enforced to 5000.')

# 3. Restart App
url_restart = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/restart?api-version=2022-03-01'
res_restart = requests.post(url_restart, headers=headers)
if res_restart.status_code == 200:
    print('SUCCESS: Azure Web App restart request accepted.')
else:
    print(f'FAILED: Azure restart returned {res_restart.status_code}')
"

# 5. Live Azure Production Deployment Sentinel & Health Verification
echo "--- Polling Azure Live Production Endpoint to Certify Deployment (Max 120s) ---"
MAX_ATTEMPTS=24
SLEEP_SECS=5
CERTIFIED=false

for i in $(seq 1 $MAX_ATTEMPTS); do
    echo "Check $i/$MAX_ATTEMPTS: Querying https://www.hwbcleaning.com/api/v1/version..."
    RESP=$(curl -s --max-time 10 "https://www.hwbcleaning.com/api/v1/version" 2>/dev/null)
    
    if [ -n "$RESP" ]; then
        STATUS=$(echo "$RESP" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('status',''))" 2>/dev/null)
        LIVE_COMMIT=$(echo "$RESP" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('commit',''))" 2>/dev/null)
        LIVE_ENV=$(echo "$RESP" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('env_label',''))" 2>/dev/null)
        LIVE_DISPLAY=$(echo "$RESP" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('display_version',''))" 2>/dev/null)

        if [ "$STATUS" = "ok" ] && [ "$LIVE_COMMIT" = "$CURRENT_HASH" ]; then
            echo "=========================================================="
            echo " SUCCESS: Live Azure Production Swapped & Certified!"
            echo " Version Stamp: $LIVE_DISPLAY"
            echo " Commit Hash:   $LIVE_COMMIT"
            echo " Environment:   $LIVE_ENV"
            echo "=========================================================="
            CERTIFIED=true
            break
        else
            echo "   Warmup in progress... (Azure is serving commit: $LIVE_COMMIT / waiting for $CURRENT_HASH)"
        fi
    else
        echo "   Waiting for Azure container initialization..."
    fi
    sleep $SLEEP_SECS
done

if [ "$CERTIFIED" = false ]; then
    echo "WARNING: Live container swap did not report matching hash within timeout."
    echo "Check Azure Container Logs: https://portal.azure.com"
else
    echo "--- SigmaFidelity: Deploy Completed & Verified Successfully ---"
fi
