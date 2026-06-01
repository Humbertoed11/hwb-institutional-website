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
IMAGE_TAG="v5.2-458ee34fc74c93a66c41b816c4d17f24d15853cc"
FULL_IMAGE="$ACR_URL/sigmafidelity-web:$IMAGE_TAG"

echo "--- SigmaFidelity: Starting Zero-Touch Production Deploy ---"

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

# 4. Live Server Reload via Azure ARM API
echo "Requesting server reload from Azure Resource Manager..."
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
AUTHORITY = f'https://login.microsoftonline.com/{TENANT_ID}'
SCOPE = ['https://management.azure.com/.default']
app = msal.ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)
result = app.acquire_token_for_client(scopes=SCOPE)
token = result.get('access_token')
if not token:
    print('Failed to get Azure token')
    exit(1)
headers = {'Authorization': f'Bearer {token}'}
url = f'https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RG}/providers/Microsoft.Web/sites/{APP_NAME}/restart?api-version=2022-03-01'
res = requests.post(url, headers=headers)
if res.status_code == 200:
    print('SUCCESS: Azure Web App container restart request accepted.')
else:
    print(f'FAILED: Azure returned status {res.status_code}')
"

echo "--- SigmaFidelity: Deploy Completed Successfully ---"
