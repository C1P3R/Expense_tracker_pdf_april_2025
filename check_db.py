import sqlite3
import os
from pathlib import Path

# Find the database file
instance_dir = Path('instance')
if instance_dir.exists():
    db_files = list(instance_dir.glob('*.db'))
    if db_files:
        db_path = db_files[0]
        print(f"Found database: {db_path}")
    else:
        print("No database files found in instance directory")
        exit(1)
else:
    print("Instance directory not found")
    exit(1)

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
print("\nTables in the database:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"- {table[0]}")

# For each table, show its structure
for table in tables:
    table_name = table[0]
    print(f"\nStructure of table '{table_name}':")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        print(f"  {column[1]} ({column[2]})")

# Close the connection
conn.close()
