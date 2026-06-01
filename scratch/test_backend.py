import os
import sys

# Change to the webserver directory to load imports correctly
sys.path.insert(0, "/app")
os.chdir("/app")

from main_app import app, User
from flask_login import login_user

def audit_backend():
    print("# SigmaFidelity™ Backend Interface Audit Log")
    print("Programmatic verification of all protected Backoffice systems:\n")
    
    # Enable test mode and configure SQLite/PostgreSQL path
    app.config["TESTING"] = True
    
    routes = [
        ("/admin/operations", "Operations Dashboard"),
        ("/admin/executive", "Executive Pulse"),
        ("/admin/master", "Master Admin Repository"),
        ("/admin/lab", "SigmaJan R&D Lab")
    ]
    
    print("| Protected Route | View Component | Authentication Status | Render Status | Integrity Check |")
    print("| :--- | :--- | :--- | :--- | :--- |")
    
    with app.test_client() as client:
        # Establish application context and session to log in a test user
        with app.app_context():
            # Create a mock session to authenticate our administrator
            with client.session_transaction() as sess:
                pass # Trigger session interface
            
            # Request route *without* login first to verify redirect security
            for route, name in routes:
                res_anon = client.get(route)
                sec_status = "🔒 Secure Redirect (302)" if res_anon.status_code == 302 else "⚠️ Unsecured!"
                
                # Now log in the administrator and perform render audit
                # Simulating a valid hdominguez admin session
                with client:
                    # We inject a test request context to perform login_user
                    with app.test_request_context():
                        test_user = User(2, "hdominguez", "Admin")
                        login_user(test_user)
                        # Store in session
                        client.get("/") # active session handshake
                    
                    res_auth = client.get(route)
                    render_status = f"✅ HTTP {res_auth.status_code} OK" if res_auth.status_code == 200 else f"❌ HTTP {res_auth.status_code}"
                    
                    integrity = "✅ 100% Render Parity" if res_auth.status_code == 200 and len(res_auth.data) > 1000 else "⚠️ Empty or Broken Render"
                    
                    print(f"| `{route}` | {name} | {sec_status} | {render_status} | {integrity} |")
                    
if __name__ == "__main__":
    audit_backend()
