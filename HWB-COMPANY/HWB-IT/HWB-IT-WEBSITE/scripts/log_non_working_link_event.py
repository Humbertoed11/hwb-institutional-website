import sqlite3
import os

def log_event():
    db_path = 'HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db'
    if not os.path.exists(db_path):
        db_path = 'database/sigma_leads.db'
    if not os.path.exists(db_path):
        print("Error: Database not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- SigmaFidelity: Logging Non-Value-Add (NVA) Event ---")
    
    # 1. Log to ActivityLog (Loss time)
    activity_name = "COPQ: Broken Link Fix/Revert Cycle (Revision History)"
    hours = 0.5 
    category = "Non-Value-Add"
    cursor.execute('INSERT INTO ActivityLog (activity_name, hours, category) VALUES (?, ?, ?)', 
                   (activity_name, hours, category))
    
    # 2. Log to COPQ (Defect Tracking)
    defect_type = "Software Defect: Broken Revision Links"
    impact = "Loss of time (0.5 hrs), system rework, user frustration."
    cursor.execute('INSERT INTO COPQ (defect_type, impact, status) VALUES (?, ?, ?)', 
                   (defect_type, impact, "CLOSED"))
    
    conn.commit()
    conn.close()
    print(f"SUCCESS: Logged {hours} hours of NVA effort and 1 COPQ entry.")

if __name__ == "__main__":
    log_event()
