import sqlite3
import os
from datetime import datetime

DB_PATH = "/mnt/c/Users/humbe/OneDrive - hwbcleaning.com/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigmafidelity.db"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Rename columns in Leads
    print("Renaming columns in Leads...")
    try:
        cursor.execute(
            "ALTER TABLE Leads RENAME COLUMN center_name TO company_name;")
    except sqlite3.OperationalError as e:
        print(f"Leads company_name rename: {e}")
    try:
        cursor.execute(
            "ALTER TABLE Leads RENAME COLUMN director TO contact_person_name;")
    except sqlite3.OperationalError as e:
        print(f"Leads contact_person_name rename: {e}")

    # 2. Add created_at and updated_at to all primary tables if missing
    tables = [
        ("Leads", "id"),
        ("Customers", "customer_id"),
        ("Services", "service_id"),
        ("WorkOrders", "work_order_id"),
        ("ServiceTasks", "task_id"),
        ("Contacts", "contact_id"),
        ("Opportunities", "opp_id"),
        ("Users", "id"),
        ("Chemicals", "id")
    ]

    for table_name, pk in tables:
        print(f"Updating timestamps for {table_name}...")
        cursor.execute(f"PRAGMA table_info({table_name});")
        cols = [col[1] for col in cursor.fetchall()]

        if "created_at" not in cols and "timestamp" not in cols and "last_modified" not in cols:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN created_at DATETIME;")
            cursor.execute(
                f"UPDATE {table_name} SET created_at = CURRENT_TIMESTAMP;")
        elif "timestamp" in cols:
            cursor.execute(
                f"ALTER TABLE {table_name} RENAME COLUMN timestamp TO created_at;")
        elif "last_modified" in cols:
            cursor.execute(
                f"ALTER TABLE {table_name} RENAME COLUMN last_modified TO updated_at;")
            if "created_at" not in cols:
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN created_at DATETIME;")
                cursor.execute(
                    f"UPDATE {table_name} SET created_at = CURRENT_TIMESTAMP;")

        if "updated_at" not in cols:
            cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN updated_at DATETIME;")
            cursor.execute(
                f"UPDATE {table_name} SET updated_at = CURRENT_TIMESTAMP;")

    # 3. Create Addresses table
    print("Creating Addresses table...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Addresses (
        address_id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id INTEGER NOT NULL,
        parent_type TEXT NOT NULL, -- 'Lead', 'Customer'
        address_type TEXT NOT NULL, -- 'Primary', 'Billing'
        line1 TEXT,
        city TEXT,
        state TEXT,
        zipcode TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Migrate Address data from Leads
    print("Migrating addresses from Leads...")
    cursor.execute("SELECT id, address, city, state, zipcode FROM Leads;")
    leads = cursor.fetchall()
    for lead_id, addr, city, state, zip_code in leads:
        if addr or city or state or zip_code:
            # Check if already migrated to avoid duplicates
            cursor.execute(
                "SELECT 1 FROM Addresses WHERE parent_id=? AND parent_type='Lead' AND address_type='Primary' LIMIT 1;",
                (lead_id,
                 ))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO Addresses (parent_id, parent_type, address_type, line1, city, state, zipcode)
                    VALUES (?, 'Lead', 'Primary', ?, ?, ?, ?);
                """, (lead_id, addr, city, state, zip_code))

    # 5. Migrate Address data from Customers
    print("Migrating addresses from Customers...")
    cursor.execute(
        "SELECT customer_id, company_address, city, zip, state, billing_address FROM Customers;")
    customers = cursor.fetchall()
    for cust_id, addr, city, zip_code, state, billing_addr in customers:
        if addr or city or zip_code or state:
            cursor.execute(
                "SELECT 1 FROM Addresses WHERE parent_id=? AND parent_type='Customer' AND address_type='Primary' LIMIT 1;",
                (cust_id,
                 ))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO Addresses (parent_id, parent_type, address_type, line1, city, state, zipcode)
                    VALUES (?, 'Customer', 'Primary', ?, ?, ?, ?);
                """, (cust_id, addr, city, state, zip_code))
        if billing_addr:
            cursor.execute(
                "SELECT 1 FROM Addresses WHERE parent_id=? AND parent_type='Customer' AND address_type='Billing' LIMIT 1;",
                (cust_id,
                 ))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO Addresses (parent_id, parent_type, address_type, line1)
                    VALUES (?, 'Customer', 'Billing', ?);
                """, (cust_id, billing_addr))

    conn.commit()
    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()
