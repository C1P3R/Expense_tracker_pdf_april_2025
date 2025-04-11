import pdfkit
from flask import render_template, current_app
import os
import tempfile
from datetime import datetime

def generate_settlement_pdf(trip, settlements, balances, user_map):
    """
    Generate a PDF report for trip settlements
    
    Args:
        trip: The Trip object
        settlements: List of settlement dictionaries with from_user, to_user, and amount
        balances: Dictionary of user_id to balance amount
        user_map: Dictionary mapping user_ids to user names
    
    Returns:
        PDF content as bytes
    """
    # Render the HTML template with the settlement data
    html_content = render_template(
        'pdf/settlement_report.html',
        trip=trip,
        settlements=settlements,
        balances=balances,
        user_map=user_map,
        generated_date=datetime.now().strftime('%d %b %Y, %H:%M')
    )
    
    # Create a temporary file for the HTML content
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
        f.write(html_content.encode('utf-8'))
        html_file = f.name
    
    try:
        # Configure PDF options
        options = {
            'page-size': 'A4',
            'margin-top': '1.0cm',
            'margin-right': '1.0cm',
            'margin-bottom': '1.0cm',
            'margin-left': '1.0cm',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': None
        }
        
        # Generate PDF from HTML
        pdf_content = pdfkit.from_file(html_file, False, options=options)
        return pdf_content
    
    finally:
        # Clean up the temporary file
        if os.path.exists(html_file):
            os.remove(html_file)
