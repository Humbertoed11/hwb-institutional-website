import sqlite3
import os

DB_PATH = "HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/clients.db"

def expand_schema():
    if not os.path.exists(DB_PATH):
        print(f"FAILURE: Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print("Step 1: Creating WorkOrders table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS WorkOrders (
                work_order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                service_id INTEGER,
                status TEXT DEFAULT 'PENDING', -- PENDING, ASSIGNED, IN_PROGRESS, COMPLETED, CANCELLED
                scheduled_date TEXT,
                scheduled_time TEXT,
                actual_start_time TEXT,
                actual_end_time TEXT,
                crew_lead_id INTEGER,
                client_notes TEXT,
                crew_notes TEXT,
                photo_proof_url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES Customers (customer_id),
                FOREIGN KEY (service_id) REFERENCES Services (service_id)
            )
        ''')

        print("Step 2: Creating CrewSync table (for App authentication and tracking)...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS CrewSync (
                crew_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                role TEXT DEFAULT 'TECHNICIAN', -- TECHNICIAN, SUPERVISOR, MANAGER
                current_status TEXT DEFAULT 'OFF_DUTY', -- ON_DUTY, OFF_DUTY, ON_BREAK
                last_gps_lat REAL,
                last_gps_long REAL,
                last_sync_at DATETIME,
                auth_token TEXT -- For secure mobile API handshake
            )
        ''')

        print("Step 3: Creating WorkOrderSnapshots (for offline delta sync)...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS WorkOrderSnapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_order_id INTEGER NOT NULL,
                snapshot_data TEXT, -- JSON blob of the state
                captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (work_order_id) REFERENCES WorkOrders (work_order_id)
            )
        ''')

        conn.commit()
        conn.close()
        print("SUCCESS: Database schema expanded for Mobile SaaS operations.")
    except Exception as e:
        print(f"FAILURE: Schema expansion failed: {str(e)}")

if __name__ == "__main__":
    expand_schema()
