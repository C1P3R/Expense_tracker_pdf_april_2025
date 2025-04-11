import sqlite3
import json
from pathlib import Path

# Find the database file
db_path = Path('instance/app.db')
print(f"Using database: {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if the column already exists
cursor.execute("PRAGMA table_info(trip)")
columns = cursor.fetchall()
column_names = [column[1] for column in columns]

# Add the column if it doesn't exist
if 'unregistered_participants' not in column_names:
    print("Adding 'unregistered_participants' column to trip table...")
    cursor.execute("ALTER TABLE trip ADD COLUMN unregistered_participants TEXT DEFAULT '[]'")
    conn.commit()
    print("Column added successfully!")
else:
    print("Column 'unregistered_participants' already exists.")

# Verify the column was added
cursor.execute("PRAGMA table_info(trip)")
columns = cursor.fetchall()
print("\nUpdated structure of table 'trip':")
for column in columns:
    print(f"  {column[1]} ({column[2]})")

# Close the connection
conn.close()
print("\nMigration completed.")
