import requests

def test_privacy_page():
    url = "http://localhost:5000/privacy-policy"
    print(f"Sending GET request to {url}...")
    res = requests.get(url)
    
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    
    html = res.text
    
    expected_terms = [
        "the Company",
        "committed to maintaining",
        "The Company only collects",
        "The Company processes",
        "The Company does not sell",
        "consent is obtained",
        "appeal the decision"
    ]
    
    print("\n--- Verifying EXPECTED TERMS ---")
    for term in expected_terms:
        found = term.lower() in html.lower()
        print(f"Check term '{term}': {'FOUND' if found else 'NOT FOUND'}")
        assert found, f"Term '{term}' not found in rendered HTML!"
        
    deprecated_terms = [
        "\"we,\"",
        "\"our,\"",
        "our B2B clients",
        "your information",
        "We only collect",
        "We process",
        "We never sell",
        "our forms",
        "your personal data",
        "obtain your prior",
        "emailing our support",
        "grants you",
        "our compliance desk",
        "We will respond"
    ]
    
    print("\n--- Verifying DEPRECATED TERMS ABSENCE ---")
    for term in deprecated_terms:
        found = term.lower() in html.lower()
        print(f"Check absence of '{term}': {'FOUND (FAIL)' if found else 'ABSENT (PASS)'}")
        assert not found, f"Deprecated term '{term}' was found in rendered HTML!"
        
    print("\nSUCCESS: Privacy Policy page test assertions passed!")

if __name__ == "__main__":
    try:
        test_privacy_page()
    except AssertionError as e:
        print(f"\nASSERTION ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\nTEST RUNTIME ERROR: {e}")
        exit(1)
