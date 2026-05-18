import pyodbc
import sys

server = 'sigmajan-server.database.windows.net'
username = 'kpbxmfusni'
password = 'gzdAVM7Koloie$R7'
databases = ['sigmajan-db', 'sigmajan-adb']

def test_connection(database):
    print(f"Testing connectivity to {database}...")
    connection_string = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    try:
        conn = pyodbc.connect(connection_string)
        print(f"SUCCESS: Connected to {database}")
        conn.close()
        return True
    except Exception as e:
        print(f"FAILURE: Could not connect to {database}")
        print(f"Error: {str(e)}")
        return False

results = {}
for db in databases:
    results[db] = test_connection(db)

if any(results.values()):
    sys.exit(0)
else:
    sys.exit(1)
