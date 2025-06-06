from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import current_user, login_required
from datetime import datetime
from expense_tracker.backend.models.trip import Trip
from expense_tracker.backend.models.user import User
from expense_tracker.backend.models.expense import Expense
from expense_tracker.backend.database import db
from sqlalchemy import func
from io import BytesIO
import json

# Define the blueprint without a URL prefix
trips_bp = Blueprint('trips', __name__)

@trips_bp.route('/')
@login_required
def list_trips():
    # Get all trips where user is a participant or admin
    trips = current_user.get_trips()
    return render_template('trips/list.html', trips=trips)

@trips_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_trip():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Validate input
        if not name or not start_date_str or not end_date_str:
            flash('Name and dates are required', 'error')
            return render_template('trips/add.html')
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format', 'error')
            return render_template('trips/add.html')
        
        if end_date < start_date:
            flash('End date cannot be before start date', 'error')
            return render_template('trips/add.html')
        
        # Create new trip
        trip = Trip(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            admin_id=current_user.id,
            participants='[]'  # Initialize with empty JSON array
        )
        
        # Add current user as a participant
        trip.add_participant(current_user.id)
        
        db.session.add(trip)
        db.session.commit()
        
        flash('Trip created successfully', 'success')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    
    return render_template('trips/add.html')

@trips_bp.route('/test')
def test_route():
    return "Test route works!"

@trips_bp.route('/<int:trip_id>')
@login_required
def view_trip(trip_id):
    try:
        # Debug information
        print(f"Attempting to view trip with ID: {trip_id}")
        
        # Get the trip
        trip = Trip.query.get_or_404(trip_id)
        print(f"Found trip: {trip.name}")
        
        # Check if user is a participant or admin
        participants = trip.get_participants_list()
        print(f"Participants: {participants}")
        print(f"Current user ID: {current_user.id}")
        print(f"Trip admin ID: {trip.admin_id}")
        
        if str(current_user.id) not in participants and current_user.id != trip.admin_id:
            print("Access denied: User is not a participant or admin")
            flash('You do not have access to this trip', 'error')
            return redirect(url_for('trips.list_trips'))
        
        # Get expenses for this trip
        expenses = Expense.query.filter_by(trip_id=trip_id).order_by(Expense.date.desc()).all()
        print(f"Found {len(expenses)} expenses")
        
        # Get user names for display
        participant_ids = trip.get_participants_list()
        if str(trip.admin_id) not in participant_ids:
            participant_ids.append(str(trip.admin_id))
        
        # Get registered participants
        registered_participants = User.query.filter(User.id.in_([int(pid) for pid in participant_ids])).all()
        user_map = {str(user.id): user.name for user in registered_participants}
        
        # Create participant objects for display (both registered and unregistered)
        participants = []
        
        # Add registered participants
        for user in registered_participants:
            participants.append({
                'id': str(user.id),
                'name': user.name,
                'type': 'registered'
            })
        
        # Add unregistered participants
        unregistered_names = trip.get_unregistered_participants()
        for name in unregistered_names:
            participants.append({
                'id': f'unreg_{name}',
                'name': name,
                'type': 'unregistered'
            })
            # Also add to user_map for settlements display
            user_map[f'unreg_{name}'] = name
        
        # Calculate total expenses
        total_expenses = trip.calculate_total_expenses()
        
        # Calculate settlements with error handling
        try:
            settlements = trip.calculate_settlements()
        except MemoryError:
            print("Memory error occurred during settlements calculation, using empty settlements")
            settlements = []
        except Exception as e:
            print(f"Error calculating settlements: {str(e)}")
            settlements = []
        
        return render_template('trips/view.html', 
                            trip=trip, 
                            expenses=expenses, 
                            participants=participants,
                            user_map=user_map,
                            total_expenses=total_expenses,
                            settlements=settlements)
                            
    except Exception as e:
        print(f"Error viewing trip: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error viewing trip: {str(e)}', 'error')
        return redirect(url_for('trips.list_trips'))
    
    # This code is now inside the try block

@trips_bp.route('/<int:trip_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    
    # Check if user is the admin
    if trip.admin_id != current_user.id:
        flash('You do not have permission to edit this trip', 'error')
        return redirect(url_for('trips.view_trip', trip_id=trip_id))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Validate input
        if not name or not start_date_str or not end_date_str:
            flash('Name and dates are required', 'error')
            return render_template('trips/edit.html', trip=trip)
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format', 'error')
            return render_template('trips/edit.html', trip=trip)
        
        if end_date < start_date:
            flash('End date cannot be before start date', 'error')
            return render_template('trips/edit.html', trip=trip)
        
        # Update trip
        trip.name = name
        trip.description = description
        trip.start_date = start_date
        trip.end_date = end_date
        
        db.session.commit()
        
        flash('Trip updated successfully', 'success')
        return redirect(url_for('trips.view_trip', trip_id=trip.id))
    
    # Format dates for the form
    start_date = trip.start_date.strftime('%Y-%m-%d')
    end_date = trip.end_date.strftime('%Y-%m-%d')
    
    return render_template('trips/edit.html', 
                          trip=trip,
                          start_date=start_date,
                          end_date=end_date)

@trips_bp.route('/<int:trip_id>/manage-participants', methods=['GET', 'POST'])
@login_required
def manage_participants(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    
    # Check if user is the admin
    if trip.admin_id != current_user.id:
        flash('You do not have permission to manage participants', 'error')
        return redirect(url_for('trips.view_trip', trip_id=trip_id))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_registered':
            email = request.form.get('email')
            
            # Find user by email
            user = User.query.filter_by(email=email).first()
            if not user:
                flash(f'No user found with email: {email}', 'error')
                return redirect(url_for('trips.manage_participants', trip_id=trip_id))
            
            # Add user to trip
            if trip.add_participant(user.id):
                db.session.commit()
                flash(f'Added {user.name} to the trip', 'success')
            else:
                flash(f'{user.name} is already a participant', 'info')
        
        elif action == 'add_unregistered':
            name = request.form.get('name')
            
            # Add unregistered participant by name
            if trip.add_unregistered_participant(name):
                db.session.commit()
                flash(f'Added {name} to the trip', 'success')
            else:
                flash(f'{name} is already a participant or the name is invalid', 'info')
        
        elif action == 'remove_registered':
            user_id = request.form.get('user_id')
            
            # Remove user from trip
            if trip.remove_participant(user_id):
                db.session.commit()
                flash('Participant removed from the trip', 'success')
            else:
                flash('Participant not found', 'error')
        
        elif action == 'remove_unregistered':
            name = request.form.get('name')
            
            # Remove unregistered participant
            if trip.remove_unregistered_participant(name):
                db.session.commit()
                flash(f'Removed {name} from the trip', 'success')
            else:
                flash('Participant not found', 'error')
        
        elif action == 'link_participant':
            name = request.form.get('name')
            email = request.form.get('email')
            
            # Find user by email
            user = User.query.filter_by(email=email).first()
            if not user:
                flash(f'No user found with email: {email}', 'error')
                return redirect(url_for('trips.manage_participants', trip_id=trip_id))
            
            # Link unregistered participant to user
            if trip.link_participant(name, user.id):
                db.session.commit()
                flash(f'Linked {name} to user {user.name}', 'success')
            else:
                flash(f'Failed to link {name} to user {user.name}', 'error')
        
        return redirect(url_for('trips.manage_participants', trip_id=trip_id))
    
    # Get current registered participants
    participant_ids = trip.get_participants_list()
    participants = User.query.filter(User.id.in_([int(pid) for pid in participant_ids if pid.isdigit()])).all()
    
    # Get unregistered participants
    unregistered_participants = trip.get_unregistered_participants()
    
    return render_template('trips/manage_participants.html', 
                          trip=trip,
                          participants=participants,
                          unregistered_participants=unregistered_participants)

@trips_bp.route('/<int:trip_id>/delete', methods=['POST'])
@login_required
def delete_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    
    # Check if user is the admin
    if trip.admin_id != current_user.id:
        flash('You do not have permission to delete this trip', 'error')
        return redirect(url_for('trips.view_trip', trip_id=trip_id))
    
    db.session.delete(trip)
    db.session.commit()
    
    flash('Trip deleted successfully', 'success')
    return redirect(url_for('trips.list_trips'))

@trips_bp.route('/<int:trip_id>/advances', methods=['GET', 'POST'])
@login_required
def manage_advances(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    
    # Check if user is a participant or admin
    participants = trip.get_participants_list()
    if str(current_user.id) not in participants and current_user.id != trip.admin_id:
        flash('You do not have access to this trip', 'error')
        return redirect(url_for('trips.list_trips'))
    
    # Get all participants (registered and unregistered)
    registered_participants = User.query.filter(User.id.in_([int(pid) for pid in trip.get_participants_list()])).all()
    registered_map = {str(user.id): user for user in registered_participants}
    
    # Add admin if not already in participants
    if str(trip.admin_id) not in [str(p.id) for p in registered_participants]:
        admin = User.query.get(trip.admin_id)
        registered_participants.append(admin)
        registered_map[str(admin.id)] = admin
    
    # Get unregistered participants
    unregistered_participants = trip.get_unregistered_participants()
    
    # Get current advances
    advances = trip.get_advances()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            participant_id = request.form.get('participant_id')
            amount = request.form.get('amount')
            
            try:
                print(f"Adding advance for participant ID: {participant_id}, type: {type(participant_id)}")
                
                # Handle participant_id
                if participant_id is None:
                    flash('Participant must be selected', 'error')
                    return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                    
                amount = float(amount)
                if amount <= 0:
                    flash('Amount must be greater than zero', 'error')
                    return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                
                # Add advance payment
                trip.add_advance(participant_id, amount)
                db.session.commit()
                
                # Determine participant name for the flash message
                if participant_id.startswith('unregistered_'):
                    name = participant_id.replace('unregistered_', '')
                    print(f"Detected unregistered participant with name: {name}")
                    flash(f'Added advance payment of ₹{amount} for {name}', 'success')
                else:
                    user = registered_map.get(participant_id)
                    name = user.name if user else 'Unknown'
                    flash(f'Added advance payment of ₹{amount} for {name}', 'success')
                    
                return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                
            except (ValueError, TypeError) as e:
                flash(f'Invalid input: {str(e)}', 'error')
                return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                
        elif action == 'edit':
            participant_id = request.form.get('participant_id')
            amount = request.form.get('amount')
            
            try:
                amount = float(amount)
                if amount <= 0:
                    flash('Amount must be greater than zero', 'error')
                    return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                
                # Get current amount to calculate the difference
                current_amount = advances.get(participant_id, 0)
                amount_difference = amount - current_amount
                
                # Edit advance payment
                if not trip.edit_advance(participant_id, amount):
                    flash('Advance payment not found', 'error')
                    return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                    
                db.session.commit()
                
                # Determine participant name for the flash message
                if participant_id.startswith('unregistered_'):
                    name = participant_id.replace('unregistered_', '')
                    flash(f'Updated advance payment for {name} by ₹{amount_difference}', 'success')
                else:
                    user = registered_map.get(participant_id)
                    name = user.name if user else 'Unknown'
                    flash(f'Updated advance payment for {name} by ₹{amount_difference}', 'success')
                    
                return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                
            except (ValueError, TypeError) as e:
                flash(f'Invalid input: {str(e)}', 'error')
                return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                
        elif action == 'delete':
            participant_id = request.form.get('participant_id')
            
            try:
                print(f"Attempting to delete advance for participant ID: {participant_id}")
                # Debug the advance data
                advances = trip.get_advances()
                if participant_id in advances:
                    print(f"Advance to delete: {advances[participant_id]} for participant {participant_id}")
                else:
                    print(f"No advance found for participant: {participant_id}")
                    print(f"Available advances: {advances}")
                
                # Delete advance payment
                if not trip.delete_advance(participant_id):
                    flash('Advance payment not found', 'error')
                    return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                    
                db.session.commit()
                
                # Determine participant name for the flash message
                if participant_id.startswith('unregistered_'):
                    name = participant_id.replace('unregistered_', '')
                    flash(f'Deleted advance payment for {name}', 'success')
                else:
                    user = registered_map.get(participant_id)
                    name = user.name if user else 'Unknown'
                    flash(f'Deleted advance payment for {name}', 'success')
                    
                return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error deleting advance payment: {str(e)}', 'error')
                return redirect(url_for('trips.manage_advances', trip_id=trip_id))
                
        else:
            flash('Invalid action', 'error')
            return redirect(url_for('trips.manage_advances', trip_id=trip_id))
    
    # Format advances for display
    formatted_advances = []
    for participant_id, amount in advances.items():
        if participant_id.startswith('unregistered_'):
            name = participant_id.replace('unregistered_', '')
            formatted_advances.append({
                'id': participant_id,
                'name': name,
                'type': 'unregistered',
                'amount': amount
            })
        elif participant_id in registered_map:
            user = registered_map[participant_id]
            formatted_advances.append({
                'id': participant_id,
                'name': user.name,
                'type': 'registered',
                'amount': amount
            })
    
    # Sort advances by participant name
    formatted_advances.sort(key=lambda x: x['name'])
    
    return render_template('trips/manage_advances.html',
                          trip=trip,
                          registered_participants=registered_participants,
                          unregistered_participants=unregistered_participants,
                          advances=formatted_advances)

@trips_bp.route('/<int:trip_id>/payments', methods=['GET', 'POST'])
@login_required
def manage_payments(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    
    # Check if user is a participant or admin
    participants = trip.get_participants_list()
    if str(current_user.id) not in participants and current_user.id != trip.admin_id:
        flash('You do not have access to this trip', 'error')
        return redirect(url_for('trips.list_trips'))
    
    # Get all participants (registered and unregistered)
    registered_participants = User.query.filter(User.id.in_([int(pid) for pid in trip.get_participants_list()])).all()
    registered_map = {str(user.id): user for user in registered_participants}
    
    # Add admin if not already in participants
    if str(trip.admin_id) not in [str(p.id) for p in registered_participants]:
        admin = User.query.get(trip.admin_id)
        registered_participants.append(admin)
        registered_map[str(admin.id)] = admin
    
    # Get unregistered participants
    unregistered_participants = trip.get_unregistered_participants()
    
    # Get current payments
    payments = trip.get_general_payments()
    
    # Get all expenses for this trip
    expenses = trip.expenses.all()
    
    # Calculate expense summary by category
    expense_summary = {}
    for expense in expenses:
        category = expense.category or 'Uncategorized'
        if category not in expense_summary:
            expense_summary[category] = {
                'count': 0,
                'total': 0
            }
        expense_summary[category]['count'] += 1
        expense_summary[category]['total'] += expense.amount
    
    # Convert to sorted list for display
    expense_summary_list = [
        {
            'category': category,
            'count': data['count'],
            'total': data['total']
        }
        for category, data in expense_summary.items()
    ]
    
    # Sort by total amount (highest first)
    expense_summary_list.sort(key=lambda x: x['total'], reverse=True)
    
    # Calculate overall totals
    total_expense_count = sum(item['count'] for item in expense_summary_list)
    total_expense_amount = sum(item['total'] for item in expense_summary_list)
    
    # Calculate general payment summary by extracting categories from descriptions
    payment_summary = {}
    
    # Format payments for display and calculate summary
    formatted_payments = []
    for payment in payments:
        participant_id = payment['participant_id']
        payment_amount = payment['amount']
        description = payment['description']
        
        # Extract payment category from description (use first word or 'Miscellaneous')
        category = description.split()[0].capitalize() if description else 'Miscellaneous'
        
        # Add to payment summary
        if category not in payment_summary:
            payment_summary[category] = {
                'count': 0,
                'total': 0
            }
        payment_summary[category]['count'] += 1
        payment_summary[category]['total'] += payment_amount
        
        # Format the payment for display
        if participant_id.startswith('unregistered_'):
            name = participant_id.replace('unregistered_', '')
            formatted_payments.append({
                'id': participant_id,
                'name': name,
                'type': 'unregistered',
                'amount': payment_amount,
                'description': description,
                'date': payment['date'],
                'expense_id': payment['expense_id']
            })
        elif participant_id in registered_map:
            user = registered_map[participant_id]
            formatted_payments.append({
                'id': participant_id,
                'name': user.name,
                'type': 'registered',
                'amount': payment_amount,
                'description': description,
                'date': payment['date'],
                'expense_id': payment['expense_id']
            })
    
    # Convert payment summary to sorted list for display
    payment_summary_list = [
        {
            'category': category,
            'count': data['count'],
            'total': data['total']
        }
        for category, data in payment_summary.items()
    ]
    
    # Sort by total amount (highest first)
    payment_summary_list.sort(key=lambda x: x['total'], reverse=True)
    
    # Calculate overall payment totals
    total_payment_count = sum(item['count'] for item in payment_summary_list)
    total_payment_amount = sum(item['total'] for item in payment_summary_list)
    
    # Sort payments by date (newest first)
    formatted_payments.sort(key=lambda x: x['date'], reverse=True)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            participant_id = request.form.get('participant_id')
            description = request.form.get('description')
            amount = request.form.get('amount')
            date_str = request.form.get('date')
            expense_id = request.form.get('expense_id')
            
            try:
                amount = float(amount)
                if amount <= 0:
                    flash('Amount must be greater than zero', 'error')
                    return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                
                date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Add general payment
                trip.add_general_payment(participant_id, amount, description, date, expense_id)
                db.session.commit()
                
                # Determine participant name for the flash message
                if participant_id.startswith('unregistered_'):
                    name = participant_id.replace('unregistered_', '')
                    flash(f'Added payment of ₹{amount} for {name}', 'success')
                else:
                    user = registered_map.get(participant_id)
                    name = user.name if user else 'Unknown'
                    flash(f'Added payment of ₹{amount} for {name}', 'success')
                    
                return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                
            except (ValueError, TypeError) as e:
                flash(f'Invalid input: {str(e)}', 'error')
                return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                
        elif action == 'edit':
            payment_index = int(request.form.get('payment_index'))
            participant_id = request.form.get('participant_id')
            description = request.form.get('description')
            amount = request.form.get('amount')
            date_str = request.form.get('date')
            expense_id = request.form.get('expense_id')
            
            try:
                amount = float(amount)
                if amount <= 0:
                    flash('Amount must be greater than zero', 'error')
                    return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                
                date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Edit general payment
                if not trip.edit_general_payment(payment_index, participant_id, amount, description, date, expense_id):
                    flash('Payment not found', 'error')
                    return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                    
                db.session.commit()
                flash('Payment updated successfully', 'success')
                return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                
            except (ValueError, TypeError) as e:
                flash(f'Invalid input: {str(e)}', 'error')
                return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                
        elif action == 'delete':
            payment_index = int(request.form.get('payment_index'))
            
            try:
                print(f"Attempting to delete payment at index: {payment_index}")
                # Debug the payment data
                all_payments = trip.get_general_payments()
                if 0 <= payment_index < len(all_payments):
                    print(f"Payment to delete: {all_payments[payment_index]}")
                else:
                    print(f"Invalid payment index: {payment_index}, total payments: {len(all_payments)}")
                
                # Delete general payment
                if not trip.delete_general_payment(payment_index):
                    flash('Invalid payment index', 'error')
                    return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                    
                db.session.commit()
                flash('Payment deleted successfully', 'success')
                return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error deleting payment: {str(e)}', 'error')
                return redirect(url_for('trips.manage_payments', trip_id=trip_id))
                
        else:
            flash('Invalid action', 'error')
            return redirect(url_for('trips.manage_payments', trip_id=trip_id))
    
    return render_template('trips/manage_payments.html',
                          trip=trip,
                          registered_participants=registered_participants,
                          unregistered_participants=unregistered_participants,
                          payments=formatted_payments,
                          expenses=expenses,
                          expense_summary=expense_summary_list,
                          total_expense_count=total_expense_count,
                          total_expense_amount=total_expense_amount,
                          payment_summary=payment_summary_list,
                          total_payment_count=total_payment_count,
                          total_payment_amount=total_payment_amount)

@trips_bp.route('/<int:trip_id>/settlements')
@login_required
def view_settlements(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    
    # Check if user is a participant or admin
    participants = trip.get_participants_list()
    if str(current_user.id) not in participants and current_user.id != trip.admin_id:
        flash('You do not have access to this trip', 'error')
        return redirect(url_for('trips.list_trips'))
    
    # Get user names for display
    participant_ids = trip.get_participants_list()
    if str(trip.admin_id) not in participant_ids:
        participant_ids.append(str(trip.admin_id))
    
    participants = User.query.filter(User.id.in_([int(pid) for pid in participant_ids])).all()
    user_map = {str(user.id): user.name for user in participants}
    
    # Calculate settlements
    settlements = trip.calculate_settlements()
    
    # Calculate individual balances
    balances = {}
    total_paid = {}
    total_share = {}
    
    # Import Expense model
    from expense_tracker.backend.models.expense import Expense
    
    # Get all expenses for this trip, ordered by date (newest first)
    expenses = Expense.query.filter_by(trip_id=trip.id).order_by(Expense.date.desc()).all()
    
    # For each participant, calculate their balance, total paid and total share
    for participant_id in participant_ids:
        # Calculate balance using the existing method
        balance = trip.calculate_user_balance(int(participant_id))
        balances[participant_id] = balance
        
        # Calculate total paid (from expenses + advances + general payments)
        
        # Sum of expenses paid
        expense_paid = Expense.query.filter_by(trip_id=trip.id, payer_id=participant_id).with_entities(func.sum(Expense.amount)).scalar() or 0
        
        # Add general payments
        general_payments = trip.get_participant_general_payments(participant_id)
        
        # Add advance payments
        advances = trip.get_advances()
        advance_amount = advances.get(participant_id, 0)
        
        # Total paid is the sum of all three
        total_paid_amount = expense_paid + general_payments + advance_amount
        total_paid[participant_id] = total_paid_amount
        
        # Total share is Total paid minus balance
        # If balance is positive, they paid more than their share
        # If balance is negative, they paid less than their share
        total_share[participant_id] = total_paid_amount - balance
    
    # Also calculate for unregistered participants
    unregistered_participants = trip.get_unregistered_participants()
    for name in unregistered_participants:
        # Create a unique ID for the unregistered participant
        unregistered_id = f'unregistered_{name}'
        
        # Calculate balance
        balance = trip.calculate_user_balance(unregistered_id)
        balances[unregistered_id] = balance
        
        # Add to user_map for display
        user_map[unregistered_id] = name
        
        # Calculate total paid and share similar to registered participants
        # (This might be simplified depending on what's possible for unregistered participants)
        expense_paid = Expense.query.filter_by(trip_id=trip.id, payer_id=unregistered_id).with_entities(func.sum(Expense.amount)).scalar() or 0
        general_payments = trip.get_participant_general_payments(unregistered_id)
        advances = trip.get_advances()
        advance_amount = advances.get(unregistered_id, 0)
        
        total_paid_amount = expense_paid + general_payments + advance_amount
        total_paid[unregistered_id] = total_paid_amount
        total_share[unregistered_id] = total_paid_amount - balance
    
    return render_template('trips/settlements.html', 
                          trip=trip,
                          user_map=user_map,
                          settlements=settlements,
                          balances=balances,
                          total_paid=total_paid,
                          total_share=total_share,
                          expenses=expenses)

@trips_bp.route('/<int:trip_id>/export-pdf')
@login_required
def export_pdf(trip_id):
    """Export settlements as PDF"""
    from expense_tracker.backend.utils.pdf_generator import generate_settlement_pdf
    
    trip = Trip.query.get_or_404(trip_id)
    
    # Check if user is a participant
    participants = trip.get_participants_list()
    if str(current_user.id) not in participants and current_user.id != trip.admin_id:
        flash('You do not have access to this trip', 'error')
        return redirect(url_for('trips.list_trips'))
    
    # Calculate settlements
    settlements = trip.calculate_settlements()
    
    # Calculate individual balances
    balances = {}
    for participant_id in participants:
        balances[participant_id] = trip.calculate_user_balance(int(participant_id))
    
    # Add admin if not already in participants
    if str(trip.admin_id) not in participants:
        balances[str(trip.admin_id)] = trip.calculate_user_balance(trip.admin_id)
    
    # Create a user map for easy lookup
    users = User.query.filter(User.id.in_([int(pid) for pid in participants] + [trip.admin_id])).all()
    user_map = {str(user.id): user.name for user in users}
    
    # Generate PDF
    pdf_content = generate_settlement_pdf(trip, settlements, balances, user_map)
    
    # Create a BytesIO object
    pdf_io = BytesIO(pdf_content)
    
    # Send the PDF as a downloadable file
    return send_file(
        pdf_io,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'settlement_report_{trip.name.replace(" ", "_")}.pdf'
    )
    trip = Trip.query.get_or_404(trip_id)
    
    # Check if user is a participant or admin
    participants = trip.get_participants_list()
    if str(current_user.id) not in participants and current_user.id != trip.admin_id:
        flash('You do not have access to this trip', 'error')
        return redirect(url_for('trips.list_trips'))
    
    # Generate PDF report
    # This will be implemented in a separate function
    
    flash('PDF export functionality coming soon', 'info')
    return redirect(url_for('trips.view_trip', trip_id=trip_id))
