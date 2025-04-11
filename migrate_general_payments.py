"""
Migration script to add the general_payments_json column to the trip table
This script will find and update the correct database file
"""
import sqlite3
import os
from pathlib import Path
import glob

def find_database_files():
    """Find all potential SQLite database files in the project"""
    base_dir = Path(__file__).resolve().parent
    
    # List of potential database files/paths
    potential_paths = [
        base_dir / 'instance' / 'app.db',
        base_dir / 'app.db',
        base_dir / 'expense_tracker.db',
        base_dir / 'expense_tracker' / 'app.db',
        base_dir / 'expense_tracker' / 'backend' / 'app.db'
    ]
    
    # Add any .db files in the root directory
    potential_paths.extend(base_dir.glob('*.db'))
    
    # Return all existing database files
    return [str(path) for path in potential_paths if path.exists()]

def check_table_exists(conn, table_name):
    """Check if a table exists in the database"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None

def check_column_exists(conn, table_name, column_name):
    """Check if a column exists in a table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return any(column[1] == column_name for column in columns)

def add_column(conn, table_name, column_name, column_type, default_value):
    """Add a column to a table"""
    cursor = conn.cursor()
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type} DEFAULT '{default_value}'")
    conn.commit()

def run_migration():
    """Run the migration on all found database files"""
    db_files = find_database_files()
    
    if not db_files:
        print("No database files found!")
        return
    
    for db_path in db_files:
        print(f"\nChecking database: {db_path}")
        
        try:
            conn = sqlite3.connect(db_path)
            
            # Check if the trip table exists
            if not check_table_exists(conn, 'trip'):
                print(f"  - 'trip' table not found in {db_path}")
                continue
                
            # Check if the column already exists
            if check_column_exists(conn, 'trip', 'general_payments_json'):
                print(f"  - 'general_payments_json' column already exists in {db_path}")
            else:
                # Add the column
                add_column(conn, 'trip', 'general_payments_json', 'TEXT', '[]')
                print(f"  - Added 'general_payments_json' column to 'trip' table in {db_path}")
                
        except Exception as e:
            print(f"  - Error processing {db_path}: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

if __name__ == "__main__":
    run_migration()
    print("\nMigration completed. Please restart your application.")
