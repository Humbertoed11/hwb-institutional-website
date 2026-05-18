import psycopg2
import sys

server = 'sigmajan-server.postgres.database.azure.com'
database = 'sigmajan-adb'
user = 'kpbxmfusni'
password = 'gzdAVM7Koloie$R7'

def test_connection():
    print(f"Testing connectivity to PostgreSQL database {database}...")
    try:
        conn = psycopg2.connect(
            host=server,
            database=database,
            user=user,
            password=password,
            sslmode='require'
        )
        print(f"SUCCESS: Connected to {database}")
        conn.close()
        return True
    except Exception as e:
        print(f"FAILURE: Could not connect to {database}")
        print(f"Error: {str(e)}")
        return False

if test_connection():
    sys.exit(0)
else:
    sys.exit(1)
