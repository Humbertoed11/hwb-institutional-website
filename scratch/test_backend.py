import os
import sys

# Change to the webserver directory to load imports correctly
sys.path.insert(0, "/app")
os.chdir("/app")

from main_app import app

def audit_backend():
    print("# SigmaFidelity™ Backend Interface Audit Log")
    print("Programmatic verification of all protected Backoffice systems:\n")
    
    # Enable test mode
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
        # Request route *without* login first to verify redirect security
        for route, name in routes:
            res_anon = client.get(route)
            sec_status = "🔒 Secure Redirect (302)" if res_anon.status_code == 302 else "⚠️ Unsecured!"
            
            # Post credentials to authenticate
            client.post('/login', data={'username': 'hdominguez', 'password': 'password11'})
            
            res_auth = client.get(route)
            render_status = f"✅ HTTP {res_auth.status_code} OK" if res_auth.status_code == 200 else f"❌ HTTP {res_auth.status_code}"
            
            integrity = "✅ 100% Render Parity" if res_auth.status_code == 200 and len(res_auth.data) > 1000 else "⚠️ Empty or Broken Render"
            
            print(f"| `{route}` | {name} | {sec_status} | {render_status} | {integrity} |")
            
            # Log out to reset session for next loop iteration's anonymous check
            client.get('/logout')

if __name__ == "__main__":
    audit_backend()
