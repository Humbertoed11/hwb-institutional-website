import requests

def test_construction_page():
    url = "http://localhost:5000/services/construction"
    print(f"Sending GET request to {url}...")
    res = requests.get(url)
    
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    
    html = res.text
    if "services-view" in html:
        start_idx = html.find("services-view")
        html = html[start_idx:html.find("</section>", start_idx)]
    
    # 1. Assertions for new horizontal neighborhood copy
    expected_terms = [
        "3-Step Neighborhood Cleanup",
        "OSHA-Compliant Teams",
        "Initial Site Cleaning Operations",
        "Rough Site Sweeping",
        "Road and Curb Washing",
        "Handover Sweep & Detail",
        "Road and Sidewalk Washing",
        "utilities setup",
        "cleared of heavy dust and debris"
    ]
    
    print("\n--- Verifying EXPECTED TERMS ---")
    for term in expected_terms:
        found = term.lower() in html.lower()
        print(f"Check term '{term}': {'FOUND' if found else 'NOT FOUND'}")
        assert found, f"Term '{term}' not found in rendered HTML!"
        
    # 2. Assertions for deprecated vertical/corporate terms
    deprecated_terms = [
        "MEP completion",
        "CSI: Clean",
        "Detailed Sanitization",
        "high-stakes",
        "high-performance",
        " your ",
        "dust-free",
        "Cleaning Management",
        "cleaning management"
    ]
    
    print("\n--- Verifying DEPRECATED TERMS ABSENCE ---")
    for term in deprecated_terms:
        found = term.lower() in html.lower()
        print(f"Check absence of '{term}': {'FOUND (FAIL)' if found else 'ABSENT (PASS)'}")
        assert not found, f"Deprecated term '{term}' was found in rendered HTML!"
        
    print("\nSUCCESS: All horizontal post-construction cleanup test assertions passed!")

if __name__ == "__main__":
    try:
        test_construction_page()
    except AssertionError as e:
        print(f"\nASSERTION ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\nTEST RUNTIME ERROR: {e}")
        exit(1)
