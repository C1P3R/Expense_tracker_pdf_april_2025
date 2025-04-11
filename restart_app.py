"""
Script to restart the Flask application and clear SQLAlchemy metadata cache
"""
from expense_tracker.backend.database import db
from expense_tracker.backend.app import app
import os

print("Restarting application and refreshing database connection...")

# Clear SQLAlchemy metadata cache
db.metadata.clear()

# Reflect the database structure
with app.app_context():
    # Import models to ensure they are registered with SQLAlchemy
    from expense_tracker.backend.models.user import User
    from expense_tracker.backend.models.trip import Trip
    from expense_tracker.backend.models.expense import Expense
    
    # Force SQLAlchemy to refresh its view of the database schema
    db.reflect()
    
    # Test a query to verify the column exists
    try:
        trips = Trip.query.all()
        print(f"Successfully queried {len(trips)} trips")
        
        # Test accessing the general_payments_json field
        for trip in trips:
            payments = trip.get_general_payments()
            print(f"Trip {trip.id}: {len(payments)} general payments")
            
        print("\nDatabase connection is working correctly!")
        print("You can now restart your application normally.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nThere may still be issues with the database schema.")
