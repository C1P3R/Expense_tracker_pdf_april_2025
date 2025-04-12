from datetime import datetime
import json
from expense_tracker.backend.database import db

class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Admin user who created the trip
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # JSON field to store registered participant IDs
    participants = db.Column(db.Text, nullable=False, default=json.dumps([]))
    
    # JSON field to store unregistered participants by name
    unregistered_participants = db.Column(db.Text, nullable=False, default=json.dumps([]))
    
    # JSON field to store advance payments
    # This is stored as a JSON string but accessed through the get_advances method
    # Format: {"participant_id": amount, ...}
    advances_json = db.Column(db.Text, default=json.dumps({}))
    
    # JSON field to store general payments made during the trip
    # Format: [{
    #     "participant_id": "1",
    #     "amount": 100,
    #     "description": "Hotel payment",
    #     "date": "2025-04-09",
    #     "expense_id": 1  # Links to the expense this payment is for
    # }, ...]
    general_payments_json = db.Column(db.Text, default=json.dumps([]))
    
    # Relationships
    expenses = db.relationship('Expense', backref='trip', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_participants_list(self):
        """Convert JSON string to list of participant IDs"""
        if self.participants is None:
            return []
        return json.loads(self.participants)
    
    def get_unregistered_participants(self):
        """Convert JSON string to list of unregistered participant names"""
        if self.unregistered_participants is None:
            return []
        return json.loads(self.unregistered_participants)
    
    def set_unregistered_participants(self, participants):
        """Convert list of unregistered participant names to JSON string"""
        self.unregistered_participants = json.dumps(participants)
    
    def set_participants_list(self, participants):
        """Convert list of participant IDs to JSON string"""
        self.participants = json.dumps(participants)
    
    def add_participant(self, user_id):
        """Add a registered participant to the trip"""
        participants = self.get_participants_list()
        if str(user_id) not in participants and user_id != self.admin_id:
            participants.append(str(user_id))
            self.set_participants_list(participants)
            return True
        return False
        
    def add_unregistered_participant(self, name):
        """Add an unregistered participant by name to the trip"""
        participants = self.get_unregistered_participants()
        if name.strip() and name not in participants:
            participants.append(name)
            self.set_unregistered_participants(participants)
            return True
        return False
    
    def remove_participant(self, user_id):
        """Remove a registered participant from the trip"""
        participants = self.get_participants_list()
        if str(user_id) in participants:
            participants.remove(str(user_id))
            self.set_participants_list(participants)
            return True
        return False
    
    def remove_unregistered_participant(self, name):
        """Remove an unregistered participant from the trip"""
        participants = self.get_unregistered_participants()
        if name in participants:
            participants.remove(name)
            self.set_unregistered_participants(participants)
            return True
        return False
        
    def link_participant(self, name, user_id):
        """Link an unregistered participant to a registered user"""
        # Remove from unregistered list
        if self.remove_unregistered_participant(name):
            # Add to registered list
            return self.add_participant(user_id)
        return False
    
    def calculate_total_expenses(self):
        """Calculate total expenses for this trip"""
        return sum(expense.amount for expense in self.expenses)
    
    def calculate_user_balance(self, user_id):
        """Calculate net balance for a specific user"""
        from expense_tracker.backend.models.expense import Expense
        
        # Check if this is an unregistered participant
        if isinstance(user_id, str) and user_id.startswith('unregistered_'):
            return self.calculate_unregistered_balance(user_id)
        
        # Total paid by user (expenses they covered)
        total_paid = sum(expense.amount for expense in 
                         Expense.query.filter_by(trip_id=self.id, payer_id=str(user_id)))
        
        # Add general payments made by this user
        total_paid += self.get_participant_general_payments(user_id)
        
        # Add advance payments
        advances = self.get_advances()
        advance_amount = advances.get(str(user_id), 0)
        total_paid += advance_amount
        
        # Total share of user
        total_share = 0
        for expense in self.expenses:
            shares = expense.get_shares()
            if str(user_id) in shares:
                total_share += shares[str(user_id)]
        
        # Positive means user is owed money, negative means user owes money
        return total_paid - total_share
        
    def calculate_unregistered_balance(self, unregistered_id):
        """Calculate balance for an unregistered participant"""
        total_share = 0
        balance = 0
        
        # Get any advance payments for this participant
        advances = self.get_advances()
        advance_amount = advances.get(unregistered_id, 0)
        
        # Add general payments made by this participant
        general_payments = self.get_participant_general_payments(unregistered_id)
        
        # Total paid = advances + general payments
        total_paid = advance_amount + general_payments
        
        # Calculate their total share
        for expense in self.expenses:
            shares = expense.get_shares()
            if unregistered_id in shares:
                # If they were included in an expense, add their share
                total_share -= shares[unregistered_id]
                
            # If they paid for an expense (unlikely but possible), add the amount
            if expense.payer_id == unregistered_id:
                balance += expense.amount
        
        # Calculate balance: total paid minus their share
        # Positive means they are owed money, negative means they owe money
        balance += total_share
        return balance
        
    def get_advances(self):
        """Get the advances dictionary from JSON"""
        if not self.advances_json:
            return {}
        return json.loads(self.advances_json)
    
    def set_advances(self, advances):
        """Save the advances dictionary as JSON"""
        self.advances_json = json.dumps(advances)
        
    def add_advance(self, participant_id, amount):
        """Add an advance payment for a participant"""
        advances = self.get_advances()
        
        print(f"Model - Adding advance: participant_id={participant_id} of type {type(participant_id)}")
        
        # If participant already has an advance, add to it
        if participant_id in advances:
            advances[participant_id] += amount
        else:
            advances[participant_id] = amount
            
        self.set_advances(advances)
        return True
        
    def edit_advance(self, participant_id, amount):
        """Edit an existing advance payment for a participant"""
        advances = self.get_advances()
        if participant_id not in advances:
            return False
            
        advances[participant_id] = amount
        self.set_advances(advances)
        return True
        
    def delete_advance(self, participant_id):
        """Delete an advance payment for a participant"""
        advances = self.get_advances()
        
        print(f"In model: Deleting advance for {participant_id}")
        print(f"Available advances: {advances}")
        
        if participant_id not in advances:
            print(f"Advance not found for {participant_id}")
            return False
            
        # Remove the advance
        del advances[participant_id]
        
        # Save changes
        self.set_advances(advances)  # Use set_advances method instead of direct JSON manipulation
        
        # No need to call db.session.add here as the calling function will handle the commit
        return True
        
    def get_general_payments(self):
        """Get the general payments list from JSON"""
        if not self.general_payments_json:
            return []
        return json.loads(self.general_payments_json)
    
    def set_general_payments(self, payments):
        """Save the general payments list as JSON"""
        self.general_payments_json = json.dumps(payments)
        
    def add_general_payment(self, participant_id, amount, description, date=None, expense_id=None):
        """Add a general payment made by a participant"""
        payments = self.get_general_payments()
        
        # Use current date if not provided
        if not date:
            date = datetime.utcnow().strftime('%Y-%m-%d')
        elif isinstance(date, datetime):
            date = date.strftime('%Y-%m-%d')
        
        # Add new payment
        payment = {
            'participant_id': participant_id,
            'amount': float(amount),
            'description': description,
            'date': date,
            'expense_id': expense_id  # Links to the expense this payment is for
        }
        
        payments.append(payment)
        self.set_general_payments(payments)
        return True
        
    def edit_general_payment(self, payment_index, participant_id, amount, description, date=None, expense_id=None):
        """Edit an existing general payment"""
        payments = self.get_general_payments()
        
        if payment_index < 0 or payment_index >= len(payments):
            return False
            
        payment = payments[payment_index]
        payment['participant_id'] = participant_id
        payment['amount'] = float(amount)
        payment['description'] = description
        
        # Update date if provided
        if date:
            if isinstance(date, datetime):
                date = date.strftime('%Y-%m-%d')
            payment['date'] = date
            
        # Update expense_id if provided
        if expense_id is not None:
            payment['expense_id'] = expense_id
            
        self.set_general_payments(payments)
        return True
        
    def delete_general_payment(self, payment_index):
        """Delete a general payment"""
        payments = self.get_general_payments()
        
        print(f"In model: Deleting payment at index {payment_index}")
        print(f"Available payments: {payments}")
        
        if payment_index < 0 or payment_index >= len(payments):
            print(f"Payment index out of range: {payment_index}, total payments: {len(payments)}")
            return False
            
        # Remove the payment
        del payments[payment_index]
        
        # Save changes
        self.set_general_payments(payments)  # Use set_general_payments method instead of direct JSON manipulation
        
        # No need to call db.session.add here as the calling function will handle the commit
        return True
        
    def get_participant_general_payments(self, participant_id):
        """Get total general payments made by a participant"""
        payments = self.get_general_payments()
        total = sum(payment['amount'] for payment in payments 
                   if payment['participant_id'] == str(participant_id))
        return total
    
    def calculate_settlements(self):
        """Calculate how to settle debts between participants"""
        try:
            # Get all registered participants including admin
            registered_participants = self.get_participants_list()
            if str(self.admin_id) not in registered_participants:
                registered_participants.append(str(self.admin_id))
                
            # Get all unregistered participants
            unregistered_participants = self.get_unregistered_participants()
            print(f"Found {len(unregistered_participants)} unregistered participants for settlements")
            
            # Calculate balance for each registered participant
            balances = {}
            for participant_id in registered_participants:
                balance = self.calculate_user_balance(participant_id)
                # Only include non-zero balances to optimize memory
                if abs(balance) > 0.01:
                    balances[participant_id] = balance
                    
            # Calculate balance for each unregistered participant
            for name in unregistered_participants:
                # Create a unique ID for the unregistered participant
                unregistered_id = f'unregistered_{name}'
                
                # Calculate their balance across all expenses
                balance = 0
                for expense in self.expenses:
                    shares = expense.get_shares()
                    if unregistered_id in shares:
                        # If they were included in an expense, add their share
                        balance -= shares[unregistered_id]
                        
                    # If they paid for an expense (unlikely but possible), add the amount
                    if expense.payer_id == unregistered_id:
                        balance += expense.amount
                
                # Only include non-zero balances
                if abs(balance) > 0.01:
                    balances[unregistered_id] = balance
                    print(f"Unregistered participant {name} has balance: {balance}")
            
            # If no significant balances, return empty settlements
            if not balances:
                return []
            
            # Calculate settlements
            settlements = []
            max_iterations = 100  # Prevent infinite loops
            iteration = 0
            
            while balances and iteration < max_iterations:
                iteration += 1
                
                # Find max creditor and max debtor
                max_creditor = max(balances.items(), key=lambda x: x[1]) if balances else None
                max_debtor = min(balances.items(), key=lambda x: x[1]) if balances else None
                
                # If all balances are settled (close to zero), we're done
                if not max_creditor or not max_debtor or abs(max_creditor[1]) < 0.01 or abs(max_debtor[1]) < 0.01:
                    break
                
                # Calculate settlement amount
                amount = min(max_creditor[1], -max_debtor[1])
                
                # Round to 2 decimal places to avoid floating point issues
                amount = round(amount, 2)
                
                if amount <= 0:
                    break  # No more meaningful settlements to make
                
                # Create settlement
                settlements.append({
                    'from_user': max_debtor[0],
                    'to_user': max_creditor[0],
                    'amount': amount
                })
                
                # Update balances
                balances[max_creditor[0]] -= amount
                balances[max_debtor[0]] += amount
                
                # Remove settled balances to save memory
                balances = {k: v for k, v in balances.items() if abs(v) > 0.01}
            
            # Limit the number of settlements to return (memory optimization)
            return settlements[:20]  # Return at most 20 settlements
            
        except Exception as e:
            print(f"Error calculating settlements: {str(e)}")
            import traceback
            traceback.print_exc()
            return []  # Return empty list on error
    
    def __repr__(self):
        return f'<Trip {self.name}: {self.start_date.date()} to {self.end_date.date()}>'
