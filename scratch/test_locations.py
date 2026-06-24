import requests
import re

def test_locations():
    base_url = "http://localhost:5000"
    
    # Core target locations to verify
    locations = ["dallas", "plano", "fort-worth", "waxahachie", "frisco", "mckinney"]
    
    print("--- Verifying Target Location Pages ---")
    for loc in locations:
        url = f"{base_url}/locations/{loc}"
        print(f"Requesting {url}...")
        res = requests.get(url)
        print(f"Status Code: {res.status_code}")
        assert res.status_code == 200, f"Expected 200 OK for {loc}, got {res.status_code}"
        
        html = res.text
        
        # Verify page title and header
        title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else ""
        
        h1_match = re.search(r'<h1>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
        h1 = h1_match.group(1).strip() if h1_match else ""
        
        print(f"Title: '{title}'")
        print(f"H1: '{h1}'")
        
        # City name verification inside content
        city_proper = loc.replace("-", " ").title()
        assert city_proper.lower() in h1.lower(), f"Expected city name '{city_proper}' in H1, got '{h1}'"
        
        # Meta description verification
        meta_desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html, re.DOTALL | re.IGNORECASE)
        if not meta_desc_match:
            # Try alternate ordering of attributes
            meta_desc_match = re.search(r'<meta\s+content="([^"]+)"\s+name="description"', html, re.DOTALL | re.IGNORECASE)
            
        desc_content = meta_desc_match.group(1).strip() if meta_desc_match else ""
        print(f"Meta Description: '{desc_content}'")
        assert desc_content, "Meta description is missing!"
        assert "osha-compliant" in desc_content.lower(), f"Expected OSHA-compliant claim in meta description"
        assert city_proper.lower() in desc_content.lower(), f"Expected city name in meta description"
        print("Page audit: PASS\n")

    print("--- Verifying Invalid Location Routing (404 Gate) ---")
    invalid_url = f"{base_url}/locations/non-existent-city"
    print(f"Requesting {invalid_url}...")
    res_invalid = requests.get(invalid_url)
    print(f"Status Code: {res_invalid.status_code}")
    assert res_invalid.status_code == 404, f"Expected 404 Not Found, got {res_invalid.status_code}"
    print("Invalid routing audit: PASS\n")

    print("--- Verifying Footer Directory and Header Megabar Links ---")
    res_home = requests.get(base_url)
    html_home = res_home.text
    
    # 1. Footer links verify
    # Check if links are present inside footer block
    footer_start = html_home.find("<footer")
    assert footer_start != -1, "Global footer element not found on home page!"
    footer_html = html_home[footer_start:]
    
    for loc in locations:
        target_href = f"/locations/{loc}"
        # Match href in quotes (single or double)
        found_link = f'href="{target_href}"' in footer_html or f"href='{target_href}'" in footer_html
        print(f"Checking footer link '{target_href}': {'FOUND' if found_link else 'NOT FOUND'}")
        assert found_link, f"Footer link to '{target_href}' is missing!"
        
    # 2. Megabar links verify
    desktop_nav_start = html_home.find('class="desktop-nav"')
    assert desktop_nav_start != -1, "Desktop navigation bar not found!"
    desktop_nav_end = html_home.find('</nav>', desktop_nav_start)
    desktop_nav_html = html_home[desktop_nav_start:desktop_nav_end]
    
    for loc in locations:
        target_href = f"/locations/{loc}"
        found_link = f'href="{target_href}"' in desktop_nav_html or f"href='{target_href}'" in desktop_nav_html
        print(f"Checking Megabar dropdown link '{target_href}': {'FOUND' if found_link else 'NOT FOUND'}")
        assert found_link, f"Megabar dropdown link to '{target_href}' is missing!"

    print("\nSUCCESS: All location routing and interface tests passed 100%!")

if __name__ == "__main__":
    try:
        test_locations()
    except AssertionError as e:
        print(f"\nASSERTION ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\nTEST RUNTIME ERROR: {e}")
        exit(1)
