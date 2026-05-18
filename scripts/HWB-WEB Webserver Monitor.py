import tkinter as tk
from tkinter import messagebox
import requests
import time
import threading
import sqlite3
import os

# SigmaFidelity™ Styling Convention
BG_COLOR = "#f8fafc"
TEXT_PRIMARY = "#0f172a"
ACCENT_RED = "#ef4444"  # Alert color
ACCENT_BLUE = "#2563eb"
WHITE = "#ffffff"
FONT_FAMILY = ("Inter", "sans-serif", "bold")

# Database Configuration
DB_PATH = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db"

class WebserverMonitor:
    def __init__(self):
        self.url = "http://127.0.0.1:5000"
        self.check_interval = 30  # seconds
        self.is_running = True

    def log_status(self, status):
        """Logs status to the Uptime table (1 for UP, 0 for DOWN)"""
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("INSERT INTO Uptime (status) VALUES (?)", (status,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database Log Error: {e}")

    def check_server(self):
        try:
            # We check the local IP since the server is restricted to 127.0.0.1
            response = requests.get(self.url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            return False
        return False

    def trigger_alarm(self):
        def show_alert():
            root = tk.Tk()
            root.withdraw()  # Hide main window
            
            # Create Custom Styled Alert Window
            alert = tk.Toplevel()
            alert.title("SigmaFidelity™ | System Alert")
            alert.geometry("450x250")
            alert.configure(bg=BG_COLOR)
            alert.attributes("-topmost", True)
            
            # Header
            header = tk.Label(alert, text="SYSTEM DEFECT DETECTED", 
                             bg=ACCENT_RED, fg=WHITE, 
                             font=("Inter", 14, "bold"), pady=10)
            header.pack(fill="x")
            
            # Message
            msg = tk.Label(alert, text=f"The webserver at {self.url}\nis currently OFFLINE.", 
                          bg=BG_COLOR, fg=TEXT_PRIMARY, 
                          font=("Inter", 11), pady=20)
            msg.pack()
            
            # Action Button
            btn = tk.Button(alert, text="ACKNOWLEDGE", 
                           bg=ACCENT_BLUE, fg=WHITE, 
                           font=("Inter", 10, "bold"),
                           padx=20, pady=10, borderwidth=0,
                           command=alert.destroy)
            btn.pack(pady=10)
            
            # Play System Bell
            root.bell()
            
            alert.mainloop()
        
        # Run alert in a separate thread to not block monitoring
        thread = threading.Thread(target=show_alert)
        thread.daemon = True
        thread.start()

    def run(self):
        print(f"--- SigmaFidelity: Monitoring {self.url} ---")
        while self.is_running:
            is_up = self.check_server()
            status_val = 1 if is_up else 0
            self.log_status(status_val)
            
            if not is_up:
                print(f"ALERT: Server is OFF at {time.strftime('%H:%M:%S')}")
                self.trigger_alarm()
            
            time.sleep(self.check_interval)

if __name__ == "__main__":
    monitor = WebserverMonitor()
    monitor.run()
