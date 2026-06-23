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
IMAGE_TAG="v5.2-$CURRENT_DATE-$CURRENT_HASH"
FULL_IMAGE="$ACR_URL/sigmafidelity-web:$IMAGE_TAG"

echo "--- SigmaFidelity: Starting Zero-Touch Production Deploy (Tag: $IMAGE_TAG) ---"

# 2. Local Container Compilation
echo "Compiling web application image..."
docker build -t "$FULL_IMAGE" -f "$PROJECT_ROOT/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/Dockerfile" "$PROJECT_ROOT/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE"
if [ $? -ne 0 ]; then
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
        'appCommandLine': 'gunicorn --bind=0.0.0.0:5000 --timeout 600 main_app:app'
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

echo "--- SigmaFidelity: Deploy Completed Successfully ---"
