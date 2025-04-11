import sqlite3
import os
from pathlib import Path

# Get the database path
base_dir = Path(__file__).resolve().parent
db_path = os.path.join(base_dir, 'expense_tracker.db')
print(f"Looking for database at: {db_path}")

# Connect to the database
try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("Tables in the database:")
    for table in tables:
        print(f"- {table[0]}")
        
        # Get columns for each table
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        print(f"  Columns in {table[0]}:")
        for column in columns:
            print(f"  - {column[1]} ({column[2]})")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
