import requests

def test_janitorial_page():
    url = "http://localhost:5000/services/janitorial"
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
        "Commercial buildings across Dallas",
        "Day Porters assist during business hours",
        "Crews follow a structured checklist",
        "Standardized procedures ensure consistent cleanliness",
        "Reliable and professional service",
        "Start a custom plan today",
        "The team is ready to deliver",
        "deliver high-quality janitorial services",
        "janitorial_breakroom.png"
    ]
    
    print("\n--- Verifying EXPECTED TERMS ---")
    for term in expected_terms:
        found = term.lower() in html.lower()
        print(f"Check term '{term}': {'FOUND' if found else 'NOT FOUND'}")
        assert found, f"Term '{term}' not found in rendered HTML!"
        
    # 2. Assertions for deprecated/untruthful terms
    deprecated_terms = [
        "We keep your",
        "Our Day Porters",
        "help you",
        "our Night Crews",
        "We follow the same steps",
        "make sure nothing is missed",
        "ISO 9001-compliant",
        "your commercial space",
        "Start your custom plan",
        "Our team is ready",
        "your building",
        "Request your no-obligation"
    ]
    
    print("\n--- Verifying DEPRECATED TERMS ABSENCE ---")
    for term in deprecated_terms:
        if term == "your":
            found = " your " in html.lower() or " your" in html.lower() or "your " in html.lower()
        else:
            found = term.lower() in html.lower()
            
        print(f"Check absence of '{term}': {'FOUND (FAIL)' if found else 'ABSENT (PASS)'}")
        assert not found, f"Deprecated term '{term}' was found in rendered HTML!"
        
    print("\nSUCCESS: All janitorial page test assertions passed!")

if __name__ == "__main__":
    try:
        test_janitorial_page()
    except AssertionError as e:
        print(f"\nASSERTION ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\nTEST RUNTIME ERROR: {e}")
        exit(1)
