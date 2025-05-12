import sqlite3

# Connect to the database
conn = sqlite3.connect('instance/GEE.db')
cursor = conn.cursor()

# List all tables
print('Tables in GEE.db:')
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(table[0])

# Close the connection
conn.close()