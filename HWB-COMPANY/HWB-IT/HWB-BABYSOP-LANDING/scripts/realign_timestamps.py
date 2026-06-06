import os
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")
HEX_QMS_DIR = "/app/static/manual_source"

def realign_timestamps() -> None:
    print("--- George Bytes: Realigning QMS Timestamps to Disk mtime ---")
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute('SELECT doc_id, url_slug FROM "HEX_ManualIndex";')
        records = cursor.fetchall()
        
        updated_count = 0
        for doc_id, url_slug in records:
            file_path = os.path.join(HEX_QMS_DIR, url_slug)
            if os.path.exists(file_path):
                # Get the actual file modification time from disk
                mtime_epoch = os.path.getmtime(file_path)
                mtime_dt = datetime.fromtimestamp(mtime_epoch, tz=timezone.utc)
                
                # Update the database record with the true modification date
                cursor.execute("""
                    UPDATE "HEX_ManualIndex"
                    SET last_updated = %s
                    WHERE doc_id = %s
                """, (mtime_dt, doc_id))
                updated_count += 1
                print(f"REALIGNED: [{doc_id}] -> {mtime_dt.isoformat()}")
            else:
                print(f"WARNING: File not found for [{doc_id}] at {file_path}")
                
        conn.commit()
        conn.close()
        print(f"SUCCESS: Realigned {updated_count} manual index timestamps to disk parity.")
    except Exception as e:
        print(f"FAILURE: Failed to realign timestamps: {e}")

if __name__ == '__main__':
    realign_timestamps()
