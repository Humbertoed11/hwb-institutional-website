import os
import requests
import json
from dotenv import load_dotenv

# Load empirical secrets from .env
load_dotenv()

class TXComptrollerClient:
    """
    HWB SigmaFidelity™ Interface for Texas Comptroller APIs.
    Standardized according to openapi.json specification.
    """
    
    BASE_URL = "https://api.comptroller.texas.gov"
    
    def __init__(self):
        self.api_key = os.getenv("TX_COMPTROLLER_API_KEY")
        if not self.api_key:
            print("CRITICAL: TX_COMPTROLLER_API_KEY not found in .env. Empirical connection failed.")
        
        self.headers = {
            "x-api-key": self.api_key,
            "Accept": "application/json"
        }

    def get_sales_tax_payer(self, taxpayer_id):
        """
        Verify a business entity by its 11-digit Taxpayer ID.
        Endpoint: /public-data/v1/public/sales-tax-payer/{id}
        """
        url = f"{self.BASE_URL}/public-data/v1/public/sales-tax-payer/{taxpayer_id}"
        response = requests.get(url, headers=self.headers)
        return self._handle_response(response)

    def search_locations_by_zip(self, zipcode, page=1, page_size=10):
        """
        Harvest all registered business locations within a North Texas Zip Code.
        Endpoint: /public-data/v1/public/sales-tax-payer-location
        """
        url = f"{self.BASE_URL}/public-data/v1/public/sales-tax-payer-location"
        params = {
            "ZIPCODE": zipcode,
            "page": page,
            "pageSize": page_size
        }
        response = requests.get(url, headers=self.headers, params=params)
        return self._handle_response(response)

    def get_franchise_details(self, taxpayer_id):
        """
        Retrieve deep details including Officers and legal status.
        Endpoint: /public-data/v1/public/franchise-tax/{id}
        """
        url = f"{self.BASE_URL}/public-data/v1/public/franchise-tax/{taxpayer_id}"
        response = requests.get(url, headers=self.headers)
        return self._handle_response(response)

    def _handle_response(self, response):
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {"error": "Unauthorized: Invalid API Key", "status": 401}
        elif response.status_code == 404:
            return {"error": "Record not found", "status": 404}
        else:
            return {"error": f"API Error: {response.status_code}", "content": response.text}

if __name__ == "__main__":
    # Internal Test Mode (Requires .env)
    client = TXComptrollerClient()
    print("--- HWB TX Comptroller Client initialized ---")
    # Example usage (commented out to prevent execution without key)
    # print(client.search_locations_by_zip("75034")) # Frisco, TX
