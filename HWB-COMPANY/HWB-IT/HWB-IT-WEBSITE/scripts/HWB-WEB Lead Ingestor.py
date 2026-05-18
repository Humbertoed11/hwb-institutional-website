import sqlite3
import csv
import os
import shutil
import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(BASE_DIR, "../HWB-COMPANY/HWB-IT/HWB-IT-RAW-DATA")
ARCHIVE_DIR = os.path.join(RAW_DATA_DIR, "ARCHIVE")
REGISTRY_PATH = os.path.join(RAW_DATA_DIR, "Data_Processing_Registry.csv")
DATABASE_PATH = os.path.join(BASE_DIR, "../HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/database/sigma_leads.db")

def log_to_registry(filename, count, status):
    """Updates the Data Processing Registry."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Clean logic: if file was already in registry, update it; otherwise append
    new_entry = f"{filename},{now},{now},{now},{count},{status}\n"
    with open(REGISTRY_PATH, "a") as f:
        f.write(new_entry)

def ingest_leads():
    if not os.path.exists(DATABASE_PATH):
        print(f"Error: Database not found at {DATABASE_PATH}")
        return

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    print("--- SigmaFidelity: Initiating Lifecycle-Aware Ingestion ---")

    files_in_queue = [f for f in os.listdir(RAW_DATA_DIR) if f.endswith(".csv") and f != "Data_Processing_Registry.csv" and "CAD" not in f]
    
    if not files_in_queue:
        print("Muda Alert: Raw data folder is clear. No new files to process.")
        return

    for filename in files_in_queue:
        file_path = os.path.join(RAW_DATA_DIR, filename)
        print(f"Processing & Archiving: {filename}")
        
        file_inserted = 0
        
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 1. Sector & Capacity Filtering
                if "ChildCare" in filename:
                    try:
                        capacity_val = row.get('FACILITY CAPACITY') or row.get('total_capacity', 0)
                        capacity = int(capacity_val)
                        if capacity < 99: continue
                    except: continue
                    
                    operation_name = row.get('Company') or row.get('operation_name')
                    industry = "Child Care"
                    location_address = row.get('Street') or row.get('location_address')
                    phone = row.get('PHONE') or row.get('PHONE NUMBER') or row.get('phone_number')
                    county = row.get('COUNTY') or row.get('county')
                    zipcode = row.get('ZIP/postal code') or row.get('ZIP CODE') or row.get('zipcode')
                    director = row.get('administrator_director_name') or operation_name
                    email = row.get('EMAIL') or row.get('EMAIL ADDRESS') or row.get('email_address')
                    city = row.get('CITY') or row.get('city')
                    state = row.get('STATE') or row.get('state')
                    sqf = capacity * 50
                
                elif "Dealers" in filename:
                    industry = "Car Dealership"
                    operation_name = row.get('BusinessName') or row.get('DBAName') or row.get('Company')
                    location_address = row.get('PhysicalAddress') or row.get('Street')
                    phone = row.get('Phone') or row.get('PHONE')
                    county = row.get('County') or row.get('COUNTY')
                    zipcode = row.get('Zip') or row.get('ZIP') or row.get('ZIP/postal code')
                    director = row.get('DBAName') or operation_name
                    email = row.get('BusinessEmail') or row.get('EMAIL')
                    city = row.get('City') or row.get('CITY')
                    state = row.get('State') or row.get('STATE')
                    capacity = 0
                    sqf = 15000
                else:
                    continue # Skip non-standardized files

                if not operation_name: continue

                # Deduplication
                cursor.execute("SELECT id FROM Leads WHERE center_name = ?", (operation_name,))
                if cursor.fetchone(): continue
                
                # Insert
                cursor.execute('''
                    INSERT INTO Leads (
                        process_id, job_title, center_name, email, phone, 
                        address, calculated_waste, county, zipcode, 
                        director, capacity, city, state, industry, sqf
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', ('MKT-HARVEST', 'Facility Director', operation_name, email, phone,
                    location_address, 4680.0, county, zipcode,
                    director, capacity, city, state, industry, sqf))
                file_inserted += 1

        conn.commit()
        
        # 2. Lifecycle Management: Log and Archive
        log_to_registry(filename, file_inserted, "PROCESSED & ARCHIVED")
        shutil.move(file_path, os.path.join(ARCHIVE_DIR, filename))
        print(f"SUCCESS: {filename} moved to ARCHIVE with {file_inserted} leads ingested.")

    conn.close()
    print("--- Data Lifecycle Loop Complete ---")

if __name__ == "__main__":
    ingest_leads()
