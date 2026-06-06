import os
import re
import json
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")
RESEARCH_DIR = "/app/Research-docs" if os.path.exists("/app") else "/home/humbertoed/hexgrowth/Research-docs"

def run_report_learning_cycle():
    print("--- George Bytes: Launching Lobe 10 Active Learning & Scouter Cycle ---")
    
    if not os.path.exists(RESEARCH_DIR):
        print(f"FAILURE: Research directory {RESEARCH_DIR} not found.")
        return
        
    pdf_files = [f for f in os.listdir(RESEARCH_DIR) if f.endswith('.pdf')]
    print(f"INFO: Found {len(pdf_files)} PDF reports in research directory.")
    
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # 1. Fetch already ingested reports from telemetry to prevent duplicate processing
        cursor.execute("SELECT technical_data FROM \"HEX_Telemetry\" WHERE action_name = 'Report_Ingestion_Learning';")
        rows = cursor.fetchall()
        ingested_files = set()
        for r in rows:
            td = r['technical_data']
            if isinstance(td, str):
                td = json.loads(td)
            filename = td.get('filename')
            if filename:
                ingested_files.add(filename)
                
        new_learnings_count = 0
        
        for file in pdf_files:
            if file in ingested_files:
                print(f"INFO: File '{file}' already ingested. Skipping.")
                continue
                
            print(f"PROCESS: Ingesting and analyzing new market report: {file}")
            pdf_path = os.path.join(RESEARCH_DIR, file)
            txt_path = pdf_path.replace('.pdf', '_extracted.txt')
            
            # Convert PDF to text using pdftotext tool via subprocess (with pre-existing fallback)
            if not os.path.exists(txt_path):
                alt_txt_path = os.path.join(RESEARCH_DIR, "brookfield_baybrook_text.txt")
                if "Baybrook" in file and os.path.exists(alt_txt_path):
                    txt_path = alt_txt_path
                    print(f"FALLBACK: Using pre-existing text file: {txt_path}")
                else:
                    try:
                        subprocess.run(["pdftotext", pdf_path, txt_path], check=True)
                        print(f"SUCCESS: Converted {file} to text.")
                    except Exception as e:
                        print(f"WARNING: pdftotext not available inside container: {e}")
                        # Skip if no text source is available
                        if not os.path.exists(txt_path):
                            print(f"SKIP: No text file found for {file}")
                            continue
            else:
                print(f"INFO: Using pre-existing text file: {txt_path}")
                
            # Read extracted text and digest key market concepts
            with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # 2. Contextual page-by-page extraction (Lobe 10 Publisher Brain Parser)
            pages = content.split('\f')
            
            lot_sizes_found = []
            interest_rates_found = []
            cap_rates_found = []
            premiums_found = []
            
            for p_num, page_text in enumerate(pages):
                # Scan for lot sizes directly (e.g. 30', 50', 70')
                sizes = re.findall(r"\b(30|35|40|50|55|60|70)'", page_text)
                lot_sizes_found.extend(sizes)
                
                # Scan for percentages and match to concepts contextually
                pct_matches = re.findall(r"(\d+(?:\.\d+)?)%", page_text)
                for pct in pct_matches:
                    val = float(pct)
                    # Skip common formatting or standard counts
                    if val > 50.0:
                        continue
                        
                    lower_text = page_text.lower()
                    if "premium" in lower_text:
                        premiums_found.append(val)
                    if "interest" in lower_text or "mortgage" in lower_text:
                        interest_rates_found.append(val)
                    if "cap rate" in lower_text or "capitalization" in lower_text:
                        cap_rates_found.append(val)
                        
            # Dedup and sort results
            lot_sizes = sorted(list(set(lot_sizes_found)), key=int)
            interest_rates = sorted(list(set(interest_rates_found)))
            cap_rates = sorted(list(set(cap_rates_found)))
            premiums = sorted(list(set(premiums_found)))
            
            digest_summary = {
                "filename": file,
                "extracted_lot_sizes": lot_sizes[:5],
                "extracted_interest_rates": [f"{x}%" for x in interest_rates[:3]],
                "extracted_cap_rates": [f"{x}%" for x in cap_rates[:3]],
                "extracted_premiums": [f"{x}%" for x in premiums[:3]]
            }
            
            # 3. Save report concepts to HEX_KB_Library (Knowledge Base Core)
            doc_id = "HEX-COMP-" + file.lower().replace(" ", "-").replace(".pdf", "")[:35]
            title = file.replace(".pdf", "")
            
            cursor.execute("""
                INSERT INTO "HEX_KB_Library" (doc_id, title, category, content, url_slug)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    content = EXCLUDED.content,
                    last_updated = CURRENT_TIMESTAMP;
            """, (doc_id, title, "05 Marketing & Sales", f"Digested Comps: {json.dumps(digest_summary)}", file))
            
            # 4. Update Cognitive Bridge with new findings if they are validated
            if premiums:
                # Take a representative premium (e.g. 6.2% is standard in Balmoral case study)
                # Let's filter for realistic premiums around 5.0% - 10.0%
                valid_premiums = [p for p in premiums if 4.0 <= p <= 12.0]
                if valid_premiums:
                    new_premium = float(valid_premiums[0]) / 100.0
                    cursor.execute("""
                        INSERT INTO "HEX_CognitiveBridge" (parameter_name, parameter_value, source_lobe, description)
                        VALUES ('amenity_premium_benchmark', %s, 'L10 Alpha Brain', 'Benchmark premium value extracted from JBREC comps.')
                        ON CONFLICT (parameter_name) DO UPDATE SET
                            parameter_value = EXCLUDED.parameter_value,
                            last_updated = CURRENT_TIMESTAMP;
                    """, (new_premium,))
                    print(f"BRIDGE UPDATE: Ingested amenity_premium_benchmark = {new_premium*100:.2f}% from {file}")
                    
            # Log successful ingestion telemetry
            # Since the table is already seeded, we delete previous error/empty logs to clean telemetry
            cursor.execute("DELETE FROM \"HEX_Telemetry\" WHERE action_name = 'Report_Ingestion_Learning';")
            
            cursor.execute("""
                INSERT INTO "HEX_Telemetry" (action_name, status, technical_data)
                VALUES (%s, %s, %s);
            """, ("Report_Ingestion_Learning", "SUCCESS", json.dumps(digest_summary)))
            
            new_learnings_count += 1
            
        conn.commit()
        conn.close()
        print(f"SUCCESS: Learning cycle complete. Ingested {new_learnings_count} new reports.")
    except Exception as e:
        print(f"FAILURE: Learning cycle failed: {e}")

if __name__ == '__main__':
    run_report_learning_cycle()
