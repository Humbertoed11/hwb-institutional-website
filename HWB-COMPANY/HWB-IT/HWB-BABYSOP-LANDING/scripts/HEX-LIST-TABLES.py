import os
import psycopg2

DB_URL = os.environ.get("DATABASE_URL", "postgresql://hexadmin:hexpassword@hex_postgis_db:5432/hex_dev_db")

def list_tables():
    print(f"Connecting to database at {DB_URL}...")
    try:
        conn = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cur.fetchall()
            print(f"Found {len(tables)} tables:")
            for t in tables:
                table_name = t[0]
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s;
                """, (table_name,))
                columns = cur.fetchall()
                col_str = ", ".join([f"{c[0]} ({c[1]})" for c in columns])
                print(f" - {table_name}: {col_str}")
        conn.close()
    except Exception as e:
        print(f"Error connecting/querying database: {e}")

if __name__ == "__main__":
    list_tables()
