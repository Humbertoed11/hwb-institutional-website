import requests

def test_compliance_page():
    url = "http://localhost:5000/compliance"
    print(f"Sending GET request to {url}...")
    res = requests.get(url)
    
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    
    html = res.text
    if "compliance-view" in html:
        start_idx = html.find("compliance-view")
        html = html[start_idx:html.find("</section>", start_idx)]
        
    expected_terms = [
        "OSHA Standards Implementation",
        "strictly adheres",
        "The team is trained",
        "The centralized Safety Data Sheet"
    ]
    
    print("\n--- Verifying EXPECTED TERMS ---")
    for term in expected_terms:
        found = term.lower() in html.lower()
        print(f"Check term '{term}': {'FOUND' if found else 'NOT FOUND'}")
        assert found, f"Term '{term}' not found in rendered HTML!"
        
    deprecated_terms = [
        "Access our",
        "Safety is our priority",
        "Our team",
        "Our centralized"
    ]
    
    print("\n--- Verifying DEPRECATED TERMS ABSENCE ---")
    for term in deprecated_terms:
        found = term.lower() in html.lower()
        print(f"Check absence of '{term}': {'FOUND (FAIL)' if found else 'ABSENT (PASS)'}")
        assert not found, f"Deprecated term '{term}' was found in rendered HTML!"
        
    print("\nSUCCESS: Compliance page test assertions passed!")

if __name__ == "__main__":
    try:
        test_compliance_page()
    except AssertionError as e:
        print(f"\nASSERTION ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\nTEST RUNTIME ERROR: {e}")
        exit(1)
