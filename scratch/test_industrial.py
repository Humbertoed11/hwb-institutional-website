import requests

def test_industrial_page():
    url = "http://localhost:5000/services/industrial"
    print(f"Sending GET request to {url}...")
    res = requests.get(url)
    
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    
    html = res.text
    if "services-view" in html:
        start_idx = html.find("services-view")
        html = html[start_idx:html.find("</section>", start_idx)]
    
    # 1. Assertions for new standard terms
    expected_terms = [
        "Licensed equipment operators",
        "Floor Care",
        "Debris Removal",
        "Restroom Care",
        "consistent quality control",
        "debris-cleared finish",
        "deep cleaning",
        "high-quality industrial excellence",
        "high-traffic shifts"
    ]
    
    print("\n--- Verifying EXPECTED TERMS ---")
    for term in expected_terms:
        found = term.lower() in html.lower()
        print(f"Check term '{term}': {'FOUND' if found else 'NOT FOUND'}")
        assert found, f"Term '{term}' not found in rendered HTML!"
        
    # 2. Assertions for deprecated/untruthful terms
    deprecated_terms = [
        "PIT certified",
        "zero missed spots",
        "zero-debris finish",
        "deep disinfection",
        "ISO 9001-compliant",
        " your ",
        "never",
        "250+ workers",
        "warehouse management",
        "specialized management",
        "manage large-scale"
    ]
    
    print("\n--- Verifying DEPRECATED TERMS ABSENCE ---")
    for term in deprecated_terms:
        found = term.lower() in html.lower()
        print(f"Check absence of '{term}': {'FOUND (FAIL)' if found else 'ABSENT (PASS)'}")
        assert not found, f"Deprecated term '{term}' was found in rendered HTML!"
        
    print("\nSUCCESS: All industrial page test assertions passed!")

if __name__ == "__main__":
    try:
        test_industrial_page()
    except AssertionError as e:
        print(f"\nASSERTION ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\nTEST RUNTIME ERROR: {e}")
        exit(1)
