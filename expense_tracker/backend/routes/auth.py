from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from expense_tracker.backend.models.user import User
from expense_tracker.backend.models.trip import Trip
from expense_tracker.backend.models.expense import Expense
from expense_tracker.backend.database import db
from datetime import datetime
from dateutil.relativedelta import relativedelta
from collections import defaultdict

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        # Validate input
        if not email or not name or not password:
            flash('All fields are required', 'error')
            return render_template('auth/register.html')
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'error')
            return render_template('auth/register.html')
        
        # Create new user
        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember_me = 'remember_me' in request.form
        
        # Validate input
        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('auth/login.html')
        
        # Check user credentials
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return render_template('auth/login.html')
        
        # Log user in
        login_user(user, remember=remember_me)
        user.update_last_seen()
        
        # Redirect to next page or home
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        
        return redirect(next_page)
    
    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        name = request.form.get('name')
        
        # Validate input
        if not name:
            flash('Name is required', 'error')
            return render_template('auth/edit_profile.html')
        
        # Update user profile (email cannot be changed)
        current_user.name = name
        db.session.commit()
        
        flash('Profile updated successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/edit_profile.html')

@bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('auth/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('auth/change_password.html')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'error')
            return render_template('auth/change_password.html')
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password changed successfully', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html')

@bp.route('/statistics')
@login_required
def statistics():
    # Get user's trips
    user_trips = Trip.query.filter(
        (Trip.creator_id == current_user.id) | 
        (Trip.participants.any(id=current_user.id))
    ).all()
    
    # Get all expenses from user's trips
    all_expenses = []
    total_spent = 0
    trip_partners = set()
    
    for trip in user_trips:
        expenses = Expense.query.filter_by(trip_id=trip.id).all()
        all_expenses.extend(expenses)
        
        # Calculate total spent by user
        for expense in expenses:
            if expense.payer_id == str(current_user.id):
                total_spent += expense.amount
            
        # Collect unique trip partners
        trip_partners.update([p.id for p in trip.participants if p.id != current_user.id])
    
    # Get recent trips (last 5)
    recent_trips = Trip.query.filter(
        (Trip.creator_id == current_user.id) | 
        (Trip.participants.any(id=current_user.id))
    ).order_by(Trip.start_date.desc()).limit(5).all()
    
    # Get recent expenses (last 5)
    recent_expenses = Expense.query.join(Trip).filter(
        (Trip.creator_id == current_user.id) | 
        (Trip.participants.any(id=current_user.id))
    ).order_by(Expense.date.desc()).limit(5).all()
    
    # Calculate monthly spending for the last 12 months
    monthly_spending = defaultdict(float)
    today = datetime.today()
    twelve_months_ago = today - relativedelta(months=12)
    
    for expense in all_expenses:
        if expense.date >= twelve_months_ago and expense.payer_id == str(current_user.id):
            month_key = expense.date.strftime('%B %Y')
            monthly_spending[month_key] += expense.amount
    
    # Sort monthly data
    sorted_months = sorted(
        monthly_spending.keys(),
        key=lambda x: datetime.strptime(x, '%B %Y')
    )
    monthly_labels = sorted_months
    monthly_data = [monthly_spending[month] for month in sorted_months]
    
    return render_template('auth/statistics.html',
                         total_trips=len(user_trips),
                         total_expenses=len(all_expenses),
                         total_spent=total_spent,
                         total_partners=len(trip_partners),
                         recent_trips=recent_trips,
                         recent_expenses=recent_expenses,
                         monthly_labels=monthly_labels,
                         monthly_spending=monthly_data)
