import requests

def test_about_page():
    url = "http://localhost:5000/about"
    print(f"Sending GET request to {url}...")
    res = requests.get(url)
    
    print(f"Status Code: {res.status_code}")
    assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}"
    
    html = res.text
    if "vision" in html:
        start_idx = html.find("vision")
        end_idx = html.find("cta-section", start_idx)
        if end_idx != -1:
            html = html[start_idx:html.find("</section>", end_idx) + 10]
        else:
            html = html[start_idx:]
        
    expected_terms = [
        "Humberto Dominguez",
        "Founder & CEO",
        "Sigma Standard",
        "cleaning technicians are thoroughly trained",
        "Standard cleaning procedures",
        "removes hidden dust and debris",
        "Committed to Quality",
        "cleaning partner committed to quality"
    ]
    
    print("\n--- Verifying EXPECTED TERMS ---")
    for term in expected_terms:
        # Ignore case-sensitive issues for titles
        found = term.lower() in html.lower()
        print(f"Check term '{term}': {'FOUND' if found else 'NOT FOUND'}")
        assert found, f"Term '{term}' not found in rendered HTML!"
        
    deprecated_terms = [
        "spotless",
        "we believe",
        "we call this",
        "we train our",
        "our people",
        "your building succeeds",
        "our team",
        "our exact",
        "we use",
        "you can't see",
        "we follow",
        "your building's",
        "your space",
        "you can trust",
        "our mission",
        "our vision"
    ]
    
    print("\n--- Verifying DEPRECATED TERMS ABSENCE ---")
    for term in deprecated_terms:
        if term == "your":
            found = " your " in html.lower() or " your" in html.lower() or "your " in html.lower()
        else:
            found = term.lower() in html.lower()
        print(f"Check absence of '{term}': {'FOUND (FAIL)' if found else 'ABSENT (PASS)'}")
        assert not found, f"Deprecated term '{term}' was found in rendered HTML!"
        
    print("\nSUCCESS: About page test assertions passed!")

if __name__ == "__main__":
    try:
        test_about_page()
    except AssertionError as e:
        print(f"\nASSERTION ERROR: {e}")
        exit(1)
    except Exception as e:
        print(f"\nTEST RUNTIME ERROR: {e}")
        exit(1)
