from expense_tracker.backend.app_factory import create_app
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Run the application
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(debug=debug, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
