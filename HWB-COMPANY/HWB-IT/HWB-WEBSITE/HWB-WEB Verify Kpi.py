import sqlite3

def verify_active_metrics():
    conn = sqlite3.connect('database/sigma_leads.db')
    conn.row_factory = sqlite3.Row
    print("--- SigmaFidelity: Verifying Active KPI Monitoring ---")
    
    # 1. Check KPIVs
    print("\n[KPIVs - Key Process Input Variables]")
    rows = conn.execute('SELECT * FROM KPIVs').fetchall()
    for row in rows:
        print(f"- {row['metric_name']}: {row['value']} (Target: {row['target']})")

    # 2. Check Milestones
    print("\n[Milestones - Project Pulse]")
    rows = conn.execute('SELECT * FROM Milestones').fetchall()
    for row in rows:
        print(f"- [{row['category']}] {row['name']}: {row['status']} ({row['description']})")

    # 3. Check COPQ
    print("\n[COPQ - Defect Tracking]")
    rows = conn.execute('SELECT * FROM COPQ').fetchall()
    for row in rows:
        print(f"- {row['defect_type']}: {row['impact']} ({row['status']})")

    conn.close()

if __name__ == "__main__":
    verify_active_metrics()
