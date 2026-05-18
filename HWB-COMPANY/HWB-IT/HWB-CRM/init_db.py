import sqlite3
import os

db_path = 'hwb_crm/database/crm.db'

schema = """
-- HWB CRM Schema v1.0
-- Compliant with ISO 9001 Traceability Mandates

CREATE TABLE IF NOT EXISTS Leads (
    lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    source TEXT, -- e.g., Web, Referral, LinkedIn
    status TEXT DEFAULT 'New', -- New, Qualified, Disqualified, Converted
    assigned_to TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Contacts (
    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER,
    customer_id INTEGER, -- Links to Customers table in clients.db
    first_name TEXT,
    last_name TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    job_title TEXT,
    is_primary INTEGER DEFAULT 0,
    FOREIGN KEY (lead_id) REFERENCES Leads(lead_id)
);

CREATE TABLE IF NOT EXISTS Opportunities (
    opp_id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER,
    customer_id INTEGER,
    name TEXT NOT NULL,
    stage TEXT DEFAULT 'Prospecting', -- Proposal, Negotiation, Won, Lost
    expected_value REAL,
    probability INTEGER, -- 0-100%
    expected_close_date DATE,
    FOREIGN KEY (lead_id) REFERENCES Leads(lead_id)
);

CREATE TABLE IF NOT EXISTS Interactions (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    related_type TEXT, -- 'Lead', 'Opportunity', 'Customer'
    related_id INTEGER,
    interaction_type TEXT, -- Call, Email, Meeting, Note
    summary TEXT,
    outcome TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    recorded_by TEXT DEFAULT 'George'
);

CREATE TABLE IF NOT EXISTS Tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    related_type TEXT,
    related_id INTEGER,
    description TEXT NOT NULL,
    due_date DATE,
    status TEXT DEFAULT 'Pending', -- Pending, In-Progress, Completed
    assigned_to TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executescript(schema)
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path}")

if __name__ == "__main__":
    init_db()
