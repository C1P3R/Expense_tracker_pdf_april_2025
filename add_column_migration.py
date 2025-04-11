import sqlite3
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database path from environment or use default
db_path = os.getenv('DATABASE_URL', 'sqlite:///expense_tracker.db')
if db_path.startswith('sqlite:///'):
    db_path = db_path[len('sqlite:///'):]

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
    cursor.execute("ALTER TABLE trip ADD COLUMN unregistered_participants TEXT DEFAULT ?", (json.dumps([]),))
    conn.commit()
    print("Column added successfully!")
else:
    print("Column 'unregistered_participants' already exists.")

# Close the connection
conn.close()
print("Migration completed.")
