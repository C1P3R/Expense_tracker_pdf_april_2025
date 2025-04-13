from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from expense_tracker.backend.database import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128))
    profile_photo = db.Column(db.String(255), nullable=True)  # Path to profile photo
    bio = db.Column(db.Text, nullable=True)  # Short bio or description
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    trips_created = db.relationship('Trip', backref='admin', lazy='dynamic', foreign_keys='Trip.admin_id')
    
    # Get expenses paid by this user
    def get_expenses_paid(self):
        from expense_tracker.backend.models.expense import Expense
        return Expense.query.filter(Expense.payer_id == str(self.id)).all()
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def update_last_seen(self):
        self.last_seen = datetime.utcnow()
        db.session.commit()
    
    def get_trips(self):
        """Get all trips where user is a participant or admin"""
        from expense_tracker.backend.models.trip import Trip
        admin_trips = Trip.query.filter_by(admin_id=self.id).all()
        # Find trips where user is a participant (stored in JSON field)
        participant_trips = Trip.query.filter(Trip.participants.contains(str(self.id))).all()
        # Combine and remove duplicates
        all_trips = list(set(admin_trips + participant_trips))
        return all_trips
    
    def get_total_balance(self):
        """Calculate total balance across all trips"""
        trips = self.get_trips()
        total_balance = 0
        for trip in trips:
            total_balance += trip.calculate_user_balance(self.id)
        return total_balance
    
    def __repr__(self):
        return f'<User {self.name}>'
