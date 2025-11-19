"""
WSGI entry point for production servers (Gunicorn, uWSGI, etc.)
"""
import os
import time
from app import create_app
from init_db import auto_init_on_startup

# Create the Flask application instance first
app = create_app(os.getenv('FLASK_ENV', 'production'))

# Auto-initialize database on startup if enabled
# Set AUTO_INIT_DB=true in environment variables to enable
# Use app context to ensure database connection is ready
with app.app_context():
    # Add a small delay for PostgreSQL to be ready (especially on Render)
    time.sleep(2)
    auto_init_on_startup()

if __name__ == '__main__':
    # This allows running with: python wsgi.py
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

