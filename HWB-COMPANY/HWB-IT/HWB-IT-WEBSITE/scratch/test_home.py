import requests

def test_home_page():
    url = "http://localhost:5000/"
    print(f"Sending GET request to {url}...")
    res = requests.get(url)
    
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    
    html = res.text
    
    # 1. Assertions for new standard terms
    expected_terms = [
        "Focus on business operations",
        "gaps in the current setup",
        "Specialized Cleaning Services",
        "Standardized cleaning operations",
        "to prepare the building for handover",
        "Request a Free Cleaning Quote",
        "Submit contact information",
        "Full Name",
        "Request Free Quote",
        "rely on",
        "Ready for a clean building?",
        "deliver professional cleaning services",
        "Start a plan"
    ]
    
    print("\n--- Verifying EXPECTED TERMS ---")
    for term in expected_terms:
        found = term.lower() in html.lower()
        print(f"Check term '{term}': {'FOUND' if found else 'NOT FOUND'}")
        assert found, f"Term '{term}' not found in rendered HTML!"
        
    # 2. Assertions for deprecated/untruthful terms
    deprecated_terms = [
        "Stop managing cleaning issues",
        "managing your business",
        "We find the gaps",
        "your current setup",
        "Our Specialized",
        "ISO 9001-Compliant Management",
        "ensuring your building",
        "Get Your Free",
        "Fill in your details",
        "we will reach out",
        "Your Name",
        "Get My Free Quote",
        "We believe doing",
        "you can actually rely",
        "spotless",
        "View our cleaning",
        "Start your plan"
    ]
    
    print("\n--- Verifying DEPRECATED TERMS ABSENCE ---")
    for term in deprecated_terms:
        found = term.lower() in html.lower()
        print(f"Check absence of '{term}': {'FOUND (FAIL)' if found else 'ABSENT (PASS)'}")
        assert not found, f"Deprecated term '{term}' was found in rendered HTML!"
        
    print("\nSUCCESS: All home page test assertions passed!")

if __name__ == "__main__":
    try:
        test_home_page()
    except AssertionError as e:
        print(f"\nASSERTION ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\nTEST RUNTIME ERROR: {e}")
        exit(1)
