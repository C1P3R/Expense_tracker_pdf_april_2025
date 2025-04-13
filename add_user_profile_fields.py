from expense_tracker.backend.app_factory import create_app
from expense_tracker.backend.database import db
import sqlite3
import os

def add_user_profile_fields():
    """Add profile_photo and bio columns to the user table"""
    # Define possible database paths
    possible_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'app.db'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expense_tracker', 'instance', 'app.db'),
    ]
    
    # Find the first existing database file
    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("Could not find database file")
        return
    
    print(f"Using database at: {db_path}")
    
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor.fetchall()]
    print(f"Available tables: {tables}")
    
    # Check if the User table exists
    if 'user' not in [t.lower() for t in tables]:
        print("Could not find user table in the database")
        conn.close()
        return
    
    # Find the exact table name with correct case
    user_table = next((t for t in tables if t.lower() == 'user'), None)
    print(f"Found user table: {user_table}")
    
    # Check if columns already exist
    cursor.execute(f"PRAGMA table_info({user_table})")
    columns = [column[1] for column in cursor.fetchall()]
    print(f"Existing columns: {columns}")
    
    # Add profile_photo column if it doesn't exist
    if 'profile_photo' not in columns:
        print(f"Adding profile_photo column to {user_table} table...")
        cursor.execute(f"ALTER TABLE {user_table} ADD COLUMN profile_photo TEXT")
    else:
        print("profile_photo column already exists")
    
    # Add bio column if it doesn't exist
    if 'bio' not in columns:
        print(f"Adding bio column to {user_table} table...")
        cursor.execute(f"ALTER TABLE {user_table} ADD COLUMN bio TEXT")
    else:
        print("bio column already exists")
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Migration completed successfully")

if __name__ == "__main__":
    add_user_profile_fields()
