import os
import sys
from typing import List, Dict, Any

# Ensure parent directory and scripts directory are in search path
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

import hex_scar_autologger

try:
    import main_app
    app = main_app.app
except ImportError:
    from app import main_app
    app = main_app.app


def run_smoke_tests() -> bool:
    """
    Executes mock routing smoke tests to verify key dashboard systems.
    """
    print("==================================================")
    print("        HEXGROWTH ROUTING SMOKE TEST SUITE        ")
    print("==================================================")

    client = app.test_client()
    passed: bool = True

    # Setup simulated admin session
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "humberto"
        sess["role"] = "Admin"

    routes_to_test: List[Dict[str, Any]] = [
        {
            "url": "/",
            "required_strings": ["HEXGROWTH", "Explorer", "Initiate Onboarding"]
        },
        {
            "url": "/hud",
            "required_strings": ["hud-container", "george-console", "ADMIN PANEL"]
        },
        {
            "url": "/hud/terminal",
            "required_strings": ["hud-container", "george-console", "ADMIN PANEL"]
        },
        {
            "url": "/hud/surgical",
            "required_strings": ["hud-container", "george-console", "ADMIN PANEL", "HEXGROWTH SURGICAL HUD"]
        },
        {
            "url": "/hud/aggregation",
            "required_strings": ["hud-container", "george-console", "ADMIN PANEL", "HEXGROWTH AGGREGATION HUD"]
        },
        {
            "url": "/hud/explorer",
            "required_strings": ["hud-container", "Feasibility Explorer", "ADMIN PANEL"]
        },
        {
            "url": "/projects",
            "required_strings": ["Projects", "HEXGROWTH"]
        },
        {
            "url": "/design-system",
            "required_strings": ["HEXGROWTH Design System", "Technical Ledger"]
        },
        {
            "url": "/admin/control-panel",
            "required_strings": ["Cognitive Bridge Settings", "L9 Accountability Rules"]
        }
    ]

    failures: List[str] = []

    for route in routes_to_test:
        url: str = route["url"]
        req_strings: List[str] = route["required_strings"]

        print(f"Testing route: {url}")
        try:
            response = client.get(url)
            if response.status_code != 200:
                msg = f"Route {url} failed: HTTP status {response.status_code}"
                print(f"  [FAIL] HTTP status: {response.status_code} (expected 200)")
                passed = False
                failures.append(msg)
                continue
            
            html_content: str = response.get_data(as_text=True)
            missing: List[str] = []
            for s in req_strings:
                if s not in html_content:
                    missing.append(s)
            
            if missing:
                msg = f"Route {url} failed: missing expected content strings {missing}"
                print(f"  [FAIL] Missing expected content strings: {missing}")
                passed = False
                failures.append(msg)
            else:
                print(f"  [PASS] Route responded with 200 and all content verified.")
        except Exception as exc:
            msg = f"Route {url} failed with exception: {exc}"
            print(f"  [ERROR] Exception encountered: {exc}")
            passed = False
            failures.append(msg)

    print("\n==================================================")
    print("               SMOKE TEST SUMMARY                 ")
    print("==================================================")
    print(f"Route Smoke Tests:        {'PASSED' if passed else 'FAILED'}")
    print("==================================================")

    if not passed:
        log_failure_to_scars("\n".join(failures))

    return passed


def log_failure_to_scars(failure_details: str):
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    db_url = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")
    try:
        conn = psycopg2.connect(db_url)
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO "HEX_KnowledgeScars" (description, category, status, impact_level, preventative_rule)
                VALUES (%s, %s, %s, %s, %s)
            """, (f"SMOKE TEST FAILURES:\n{failure_details}", "Smoke Test Failure", "Pending", 3, "Verify all routes pass smoke tests locally before registry update."))
            conn.commit()
        conn.close()
        print("AUTOMATION: Smoke test failures successfully logged to HEX_KnowledgeScars.")
    except Exception as e:
        print(f"AUTOMATION FAILURE: Could not log test failure details: {e}")


if __name__ == "__main__":
    success = run_smoke_tests()
    sys.exit(0 if success else 1)
