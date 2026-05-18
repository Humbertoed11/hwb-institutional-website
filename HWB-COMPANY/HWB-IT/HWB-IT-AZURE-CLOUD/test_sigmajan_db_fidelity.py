import psycopg2
import sys
import socket

# Institutional Parameters
server_base = 'sigmajan-server'
database = 'sigmajan-adb'
user = 'kpbxmfusni'
password = 'gzdAVM7Koloie$R7'

# Potential DNS Variations for Azure PostgreSQL
variations = [
    f"{server_base}.postgres.database.azure.com",
    f"{server_base}.database.azure.com",
    f"{server_base}.database.windows.net" # Highly unlikely for PG
]

def test_connectivity():
    print(f"--- SigmaFidelity™ Connectivity Audit: {database} ---")
    
    found_host = None
    for host in variations:
        try:
            print(f"Resolving {host}...")
            ip = socket.gethostbyname(host)
            print(f"SUCCESS: {host} resolved to {ip}")
            found_host = host
            break
        except socket.gaierror:
            print(f"DEBUG: {host} could not be resolved.")
    
    if not found_host:
        print("CRITICAL: No valid host identified via DNS. Verification required in Azure Portal.")
        return False

    try:
        print(f"Attempting connection to {found_host}...")
        conn = psycopg2.connect(
            host=found_host,
            database=database,
            user=user,
            password=password,
            sslmode='require',
            connect_timeout=10
        )
        print(f"SUCCESS: High-Fidelity Connection established to {database}")
        conn.close()
        return True
    except Exception as e:
        print(f"FAILURE: Connection could not be established.")
        print(f"Error Detail: {str(e)}")
        if "is not allowed to access the server" in str(e):
            print("REMEDIAL ACTION: Whitelist IP 64.25.12.59 in Azure SQL Firewall.")
        return False

if __name__ == "__main__":
    if test_connectivity():
        sys.exit(0)
    else:
        sys.exit(1)
