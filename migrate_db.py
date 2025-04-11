from expense_tracker.backend.app_context import init_app
from expense_tracker.backend.database import db

app = init_app()
with app.app_context():
    db.create_all()
    print("Database schema updated successfully!")
