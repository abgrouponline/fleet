"""
WSGI entry point for production servers (Gunicorn, uWSGI, etc.)
"""
import os
from app import create_app

# Create the Flask application instance
app = create_app(os.getenv('FLASK_ENV', 'production'))

if __name__ == '__main__':
    # This allows running with: python wsgi.py
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

