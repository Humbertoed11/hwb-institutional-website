import os
import requests
import msal
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

CLIENT_ID = os.getenv("GRAPH_API_PROD_APPLICATION_ID")
CLIENT_SECRET = os.getenv("GRAPH_API_PROD_SECRET_VALUE")
TENANT_ID = os.getenv("GRAPH_API_PROD_TENANT_ID")
SUBSCRIPTION_ID = "d778faac-02a4-4d74-9881-199994f2bd98"

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://management.azure.com/.default"]

def get_azure_costs():
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    result = app.acquire_token_for_client(scopes=SCOPE)
    
    if "access_token" not in result:
        print(f"Error: {result.get('error_description')}")
        return None

    token = result["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/providers/Microsoft.CostManagement/query?api-version=2021-10-01"
    
    payload = {
        "type": "ActualCost",
        "dataSet": {
            "granularity": "None",
            "aggregation": {
                "totalCost": {
                    "name": "PreTaxCost",
                    "function": "Sum"
                }
            },
            "grouping": [
                {
                    "type": "Dimension",
                    "name": "ServiceName"
                }
            ],
            "timeframe": "MonthToDate"
        }
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"API Error: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    costs = get_azure_costs()
    if costs:
        print("Live Azure Costs (Month to Date):")
        # Azure Cost Management API returns data in rows/columns format
        rows = costs.get("properties", {}).get("rows", [])
        total = 0
        for row in rows:
            service = row[1]
            cost = row[0]
            currency = row[2]
            print(f"- {service}: {cost} {currency}")
            total += cost
        print(f"\nTOTAL MTD: {total}")
