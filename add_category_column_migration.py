import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Find the database file in the instance directory
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

print(f"Using database at: {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if the column already exists
cursor.execute("PRAGMA table_info(expense)")
columns = cursor.fetchall()
column_names = [column[1] for column in columns]

print(f"Current columns in expense table: {column_names}")

# Add the column if it doesn't exist
if 'category' not in column_names:
    print("Adding 'category' column to expense table...")
    cursor.execute("ALTER TABLE expense ADD COLUMN category TEXT")
    conn.commit()
    print("Column added successfully!")
else:
    print("Column 'category' already exists.")

# Close the connection
conn.close()
print("Migration completed.") 