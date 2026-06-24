import requests

def test_commercial_page():
    url = "http://localhost:5000/services/commercial"
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
        "high-quality floor and surface care",
        "keeps the environment professional",
        "The SigmaQuality™ Standard",
        "multi-layer checking process",
        "supporting a clean facility",
        "deep carpet cleaning",
        "vinyl (VCT) floors",
        "Start a custom plan today",
        "deliver high-quality commercial cleaning"
    ]
    
    print("\n--- Verifying EXPECTED TERMS ---")
    for term in expected_terms:
        found = term.lower() in html.lower()
        print(f"Check term '{term}': {'FOUND' if found else 'NOT FOUND'}")
        assert found, f"Term '{term}' not found in rendered HTML!"
        
    # 2. Assertions for deprecated/untruthful terms
    deprecated_terms = [
        "high-fidelity surface management",
        "keeps your environment",
        "your environment",
        "high-solids",
        "ensuring a safe facility",
        "Deep extraction cleaning",
        "VCT floors",
        "Start your custom plan today",
        "ISO 9001-compliant",
        "your building",
        "Request your",
        "stripping and waxing process",
        "SigmaQuality™ Finish"
    ]
    
    print("\n--- Verifying DEPRECATED TERMS ABSENCE ---")
    for term in deprecated_terms:
        # Special check for VCT floors alone without vinyl
        if term == "VCT floors":
            found = "vct floors" in html.lower() and "vinyl (vct) floors" not in html.lower()
        elif term == "your":
            found = " your " in html.lower() or " your" in html.lower() or "your " in html.lower()
        else:
            found = term.lower() in html.lower()
            
        print(f"Check absence of '{term}': {'FOUND (FAIL)' if found else 'ABSENT (PASS)'}")
        assert not found, f"Deprecated term '{term}' was found in rendered HTML!"
        
    print("\nSUCCESS: All commercial page test assertions passed!")

if __name__ == "__main__":
    try:
        test_commercial_page()
    except AssertionError as e:
        print(f"\nASSERTION ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\nTEST RUNTIME ERROR: {e}")
        exit(1)
