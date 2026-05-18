import sqlite3
import os

# Paths as defined in mop_incident/HWB-WEB App.py
DATABASE = 'mop_incident/database/sigma_leads.db'
CLIENT_DATABASE = 'mop_incident/database/clients.db'

def diagnose_conversion(lead_id):
    print(f"--- SigmaFidelity: Conversion Diagnostic for Lead #{lead_id} ---")
    
    try:
        # 1. Connect to Sigma Leads
        print(f"Connecting to {DATABASE}...")
        conn_sigma = sqlite3.connect(DATABASE)
        conn_sigma.row_factory = sqlite3.Row
        lead = conn_sigma.execute('SELECT * FROM Leads WHERE id = ?', (lead_id,)).fetchone()
        
        if not lead:
            print(f"FAILED: Lead #{lead_id} not found in sigma_leads.db")
            return

        print(f"LEAD FOUND: {lead['center_name']} ({lead['email']})")

        # 2. Connect to Clients DB
        print(f"Connecting to {CLIENT_DATABASE}...")
        if not os.path.exists(CLIENT_DATABASE):
            print(f"FAILED: {CLIENT_DATABASE} does not exist.")
            return
            
        conn_clients = sqlite3.connect(CLIENT_DATABASE)
        
        # 3. Attempt Insert into Customers
        print("Attempting INSERT into Customers...")
        try:
            conn_clients.execute(
                'INSERT INTO Customers (company_name, email, company_address) VALUES (?, ?, ?)', 
                (lead['center_name'], lead['email'], 'DIAGNOSTIC_ADDRESS')
            )
            conn_clients.commit()
            print("SUCCESS: Data migrated to Clients DB.")
        except Exception as e:
            print(f"FAILED (Customers Table): {str(e)}")
            return
        finally:
            conn_clients.close()

        # 4. Attempt Log in ClientActivities
        print("Attempting to log activity in ClientActivities...")
        try:
            conn_sigma.execute(
                'INSERT INTO ClientActivities (client_id, activity_type, description) VALUES (?, ?, ?)',
                (lead_id, "Conversion", "Diagnostic test conversion.")
            )
            conn_sigma.commit()
            print("SUCCESS: Activity logged in Sigma DB.")
        except Exception as e:
            print(f"FAILED (ClientActivities Table): {str(e)}")
            return

        conn_sigma.close()
        print("--- Diagnostic Complete: ALL STEPS PASSED ---")

    except Exception as e:
        print(f"CRITICAL SYSTEM ERROR: {str(e)}")

if __name__ == "__main__":
    diagnose_conversion(1)
