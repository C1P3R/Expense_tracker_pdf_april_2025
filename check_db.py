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

# Get list of tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print(f"- {table[0]}")
    
    # If there are tables, show their schema
    if tables:
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        print(f"  Columns in {table[0]}:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        print()

# Close the connection
conn.close()
