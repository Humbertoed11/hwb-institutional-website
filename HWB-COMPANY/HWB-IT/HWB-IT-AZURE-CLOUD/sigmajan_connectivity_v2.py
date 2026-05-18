from flask import Flask
import psycopg2
import os
import socket
import sys

app = Flask(__name__)

# Institutional Parameters (Centralized via Azure App Service Config)
DB_HOST = os.getenv('DB_HOST', 'sigmajan-server.postgres.database.azure.com')
DB_NAME = os.getenv('DB_NAME', 'sigmajan-adb')
DB_USER = os.getenv('DB_USER', 'kpbxmfusni')
DB_PASS = os.getenv('DB_PASS', 'gzdAVM7Koloie$R7')

@app.route('/')
def test_connection():
    status = "<h2>--- SigmaJan™ High-Fidelity Connectivity Audit ---</h2>"
    
    # Step 1: DNS Resolution Audit
    try:
        ip = socket.gethostbyname(DB_HOST)
        status += f"<p style='color: blue;'><b>DNS Audit:</b> {DB_HOST} resolved to {ip}</p>"
    except Exception as e:
        status += f"<p style='color: orange;'><b>DNS Audit FAILURE:</b> Could not resolve {DB_HOST}. Error: {str(e)}</p>"
        status += "<p><i>Check if Private DNS Zone is linked to the VNet.</i></p>"

    # Step 2: Database Handshake Audit
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            sslmode='require',
            connect_timeout=10
        )
        status += "<p style='color: green;'><b>SUCCESS:</b> Connection established from App to Database.</p>"
        
        cur = conn.cursor()
        cur.execute('SELECT version();')
        db_version = cur.fetchone()
        status += f"<p><b>Database Version:</b> {db_version[0]}</p>"
        
        cur.close()
        conn.close()
    except Exception as e:
        status += "<p style='color: red;'><b>FAILURE:</b> Connection failed.</p>"
        status += f"<p><b>Error Detail:</b> {str(e)}</p>"
        if "is not allowed to access the server" in str(e):
             status += "<p><i>Whitelisting required.</i></p>"
    
    return status

if __name__ == "__main__":
    app.run()
