import cx_Oracle
import socket
import sys
import os

# Get Windows IP
import subprocess
try:
    windows_ip = subprocess.check_output("ip route show default | awk '{print $3}'", 
                                         shell=True).decode().strip()
    print(f"Detected Windows IP: {windows_ip}")
except:
    windows_ip = input("Enter your Windows IP address: ")

# Set Oracle client location

oracle_client_path = os.path.expanduser("~/oracle/instantclient_11_2")
cx_Oracle.init_oracle_client(lib_dir=oracle_client_path)

# Connection parameters
username = "rnair"  # Replace with your actual username
password = "amdocs"  # Replace with your actual password

# Try connecting with different methods
connection_strings = [
    # Format 1: Using SID
    f"{windows_ip}:1521/XE",
    
    # Format 2: Using full TNS descriptor with SID
    f"""(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={windows_ip})(PORT=1521))(CONNECT_DATA=(SID=XE)))""",
    
    # Format 3: Using full TNS descriptor with SERVICE_NAME
    f"""(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={windows_ip})(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=XE)))"""
]

connected = False
for i, dsn in enumerate(connection_strings):
    try:
        print(f"\nAttempting connection using method {i+1}...")
        print(f"DSN: {dsn}")
        
        connection = cx_Oracle.connect(username, password, dsn)
        
        print("Connection successful!")
        
        # Test with a simple query
        cursor = connection.cursor()
        cursor.execute("SELECT 'Connection working from WSL!' FROM dual")
        result = cursor.fetchone()
        print(f"Query result: {result[0]}")
        
        cursor.close()
        connection.close()
        
        print("Database connection test complete - SUCCESS!")
        connected = True
        break
        
    except Exception as e:
        print(f"Connection failed: {e}")