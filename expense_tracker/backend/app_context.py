from flask import Flask
from flask_login import LoginManager
from expense_tracker.backend.database import db
from expense_tracker.backend.config import Config
import os

# Initialize Flask-Login
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'
login.login_message_category = 'info'

def init_app():
    """Initialize the core application."""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Load configuration
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    login.init_app(app)
    
    with app.app_context():
        # Import models to ensure they are registered with SQLAlchemy
        from expense_tracker.backend.models.user import User
        from expense_tracker.backend.models.trip import Trip
        from expense_tracker.backend.models.expense import Expense
        
        # Models are already initialized with db
        
        # Create database tables
        db.create_all()
        
        # Register blueprints
        from expense_tracker.backend.routes.auth import bp as auth_bp
        from expense_tracker.backend.routes.trips import trips_bp
        from expense_tracker.backend.routes.expenses import bp as expenses_bp
        from expense_tracker.backend.routes.main import bp as main_bp
        
        # Register blueprints with proper URL prefixes
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(trips_bp, url_prefix='/trips')  # Add URL prefix here instead of in blueprint definition
        app.register_blueprint(expenses_bp, url_prefix='/trips')  # Changed from '/trip' to '/trips' for consistency
        app.register_blueprint(main_bp)
        
        # User loader for Flask-Login
        @login.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
        
        return app
