from expense_tracker.backend.app_context import init_app

def create_app():
    """Create and configure the Flask application."""
    app = init_app()
    return app
