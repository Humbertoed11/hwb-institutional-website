cat <<EOF > app.py
from flask import Flask
import psycopg2
import os
app = Flask(__name__)
# Institutional Parameters (Centralized via Azure App Service Config)
DB_HOST = os.getenv('DB_HOST', 'sigmajan-server.postgres.database.azure.com')
DB_NAME = os.getenv('DB_NAME', 'sigmajan-adb')
DB_USER = os.getenv('DB_USER', 'kpbxmfusni')
DB_PASS = os.getenv('DB_PASS', 'gzdAVM7Koloie$R7')
@app.route('/')
 def test_connection():
        status = "<h2>--- SigmaJan™ Internal Connectivity Audit ---</h2>
     try:
         # High-Fidelity Connection Handshake
         conn = psycopg2.connect(
          host=DB_HOST,
             database=DB_NAME,
             user=DB_USER,
             password=DB_PASS,
             sslmode='require',
             connect_timeout=10
         )
         status += "<p style='color: green;'><b>SUCCESS:</b> High-Fidelity Connection established from App Service to Private Database.</p>"

         # Verify Database Version
         cur = conn.cursor()
         cur.execute('SELECT version();')
         db_version = cur.fetchone()
         status += f"<p><b>Database Version:</b> {db_version[0]}</p>"

         cur.close()
         conn.close()
     except Exception as e:
         status += "<p style='color: red;'><b>FAILURE:</b> Internal Connectivity could not be established.</p>"
         status += f"<p><b>Error Detail:</b> {str(e)}</p>"
         status += "<p><i>Audit Note: Ensure VNet Integration is active for the App Service.</i></p>"

     return status

 if __name__ == "__main__":
     app.run()
 EOF