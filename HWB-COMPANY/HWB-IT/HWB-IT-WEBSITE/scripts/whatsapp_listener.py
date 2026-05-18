from flask import Flask, request, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Institutional Path for Command Queue
BASE_DIR = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects"
DB_PATH = os.path.join(BASE_DIR, "HWB-COMPANY/HWB-IT/HWB-IT-PROCESS-CONTROL/whatsapp_queue.db")

def init_queue_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS CommandQueue 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     sender TEXT, 
                     message TEXT, 
                     status TEXT DEFAULT 'PENDING', 
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    # Twilio sends data as Form Data
    sender = request.values.get('From', '')
    message = request.values.get('Body', '')
    
    # Security: Only accept from verified active line
    if sender == 'whatsapp:+19728007808':
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO CommandQueue (sender, message) VALUES (?, ?)", (sender, message))
        conn.commit()
        conn.close()
        print(f"--- 24/7 Listener: New Directive Received from CEO: {message} ---")
        return "OK", 200
    else:
        print(f"--- 24/7 Listener: Unauthorized attempt from {sender} blocked. ---")
        return "Unauthorized", 403

if __name__ == "__main__":
    init_queue_db()
    print("--- SigmaQuality 24/7 WhatsApp Background Listener Active on Port 5002 ---")
    app.run(port=5002, host='0.0.0.0')
