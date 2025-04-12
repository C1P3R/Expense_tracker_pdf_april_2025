from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required
from expense_tracker.backend.models.trip import Trip
from expense_tracker.backend.models.expense import Expense
from expense_tracker.backend.models.user import User
from expense_tracker.backend.database import db

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    if current_user.is_authenticated:
        # Get recent trips
        trips = current_user.get_trips()
        recent_trips = sorted(trips, key=lambda t: t.updated_at, reverse=True)[:5]
        
        # Get total balance across all trips
        total_balance = current_user.get_total_balance()
        
        return render_template('main/dashboard.html', 
                              recent_trips=recent_trips,
                              total_balance=total_balance)
    else:
        return render_template('main/index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    # Get recent trips
    trips = current_user.get_trips()
    recent_trips = sorted(trips, key=lambda t: t.updated_at, reverse=True)[:5]
    
    # Get total balance across all trips
    total_balance = current_user.get_total_balance()
    
    # Get recent expenses
    recent_expenses = []
    for trip in recent_trips:
        expenses = Expense.query.filter_by(trip_id=trip.id).order_by(Expense.date.desc()).limit(3).all()
        for expense in expenses:
            # Get payer information
            payer_name = None
            payer_id_str = str(expense.payer_id)
            
            if not payer_id_str.startswith('unregistered_'):
                try:
                    payer = User.query.get(int(payer_id_str))
                    if payer:
                        payer_name = payer.name
                except (ValueError, TypeError):
                    pass
            
            recent_expenses.append({
                'expense': expense,
                'trip': trip,
                'payer_name': payer_name
            })
    
    # Sort by date
    recent_expenses = sorted(recent_expenses, key=lambda e: e['expense'].date, reverse=True)[:5]
    
    return render_template('main/dashboard.html', 
                          recent_trips=recent_trips,
                          recent_expenses=recent_expenses,
                          total_balance=total_balance)
