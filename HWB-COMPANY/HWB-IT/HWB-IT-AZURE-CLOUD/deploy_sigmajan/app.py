from flask import Flask, render_template, os
import psycopg2
import sys

app = Flask(__name__)

# Institutional Parameters (Azure Config)
DB_HOST = os.getenv('DB_HOST', 'sigmajan-server.postgres.database.azure.com')
DB_NAME = os.getenv('DB_NAME', 'sigmajan-adb')
DB_USER = os.getenv('DB_USER', 'kpbxmfusni')
DB_PASS = os.getenv('DB_PASS', 'gzdAVM7Koloie$R7')

def get_db_status():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            sslmode='require',
            connect_timeout=5
        )
        conn.close()
        return "ACTIVE"
    except:
        return "OFFLINE"

@app.route('/')
def index():
    db_status = get_db_status()
    return render_template('index.html', db_status=db_status)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
