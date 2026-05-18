import sqlite3

def record_session_effort():
    conn = sqlite3.connect('database/sigma_leads.db')
    cursor = conn.cursor()
    print("--- SigmaFidelity: Recording Daily Process Effort ---")
    
    # Effort Data for 2026-02-21
    efforts = [
        ('QMS Documentation & Governance', 2.5, 'Value-Add'),
        ('Web Dev & 3rd Person Tonal Pivot', 3.0, 'Value-Add'),
        ('Lead Intelligence & High-Fidelity Harvesting', 2.0, 'Value-Add'),
        ('S4/IEE & Analytics Integration', 1.5, 'Value-Add'),
        ('AI Defect Correction & Rework (COPQ)', 6.5, 'Non-Value-Add')
    ]
    
    cursor.executemany('INSERT INTO ActivityLog (activity_name, hours, category) VALUES (?, ?, ?)', efforts)
    conn.commit()
    conn.close()
    print("--- SUCCESS: 15.5 Total Project Hours Recorded ---")

if __name__ == "__main__":
    record_session_effort()
