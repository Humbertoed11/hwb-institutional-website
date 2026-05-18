import requests
import re
import json
import csv
import sys

def scrape_maps(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Connecting to Google Maps...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        return []

    # Look for the window.APP_INITIALIZATION_STATE or similar data blocks
    # Note: This is a complex extraction as Google obfuscates the data
    html = response.text
    
    # We look for the data that looks like a large JSON array
    # This is a fallback pattern for businesses in search results
    pattern = r'\[\[\["\d+",\[\["([^"]+)"'
    matches = re.findall(pattern, html)
    
    # Refining the search for business names and addresses
    # Industry standard: It's better to use a library like Playwright or an API
    # But we will try to find strings that look like Distribution Centers
    results = []
    
    # Extract names using a broader regex for business titles
    names = re.findall(r'","([^"]+ Distribution Center)"', html)
    if not names:
        names = re.findall(r'","([^"]+ Warehouse)"', html)
        
    for name in set(names):
        results.append({"Name": name, "Status": "Found in Source"})

    return results

if __name__ == "__main__":
    target_url = "https://www.google.com/maps/search/distribution+centers+within+70+miles+from+my+location/@32.7039792,-97.2001033,10585m/data=!3m1!1e3?entry=ttu"
    data = scrape_maps(target_url)
    
    if data:
        output_file = "mop_incident/distribution_centers.csv"
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Name", "Status"])
            writer.writeheader()
            writer.writerows(data)
        print(f"Success! {len(data)} items saved to {output_file}")
    else:
        print("Initial source scrape yielded no direct matches. Suggesting API-based approach.")
