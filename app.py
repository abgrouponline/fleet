from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config
from models import db
import os

def create_app(config_name='development'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'])
    jwt = JWTManager(app)
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        import traceback
        print("=" * 80, flush=True)
        print("JWT ERROR: Token expired", flush=True)
        print(f"JWT Header: {jwt_header}", flush=True)
        print(f"JWT Payload: {jwt_payload}", flush=True)
        print("=" * 80, flush=True)
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        import traceback
        print("=" * 80, flush=True)
        print("JWT ERROR: Invalid token", flush=True)
        print(f"Error: {error}", flush=True)
        print(traceback.format_exc(), flush=True)
        print("=" * 80, flush=True)
        return jsonify({'error': 'Invalid token'}), 422
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        import traceback
        print("=" * 80, flush=True)
        print("JWT ERROR: Missing token", flush=True)
        print(f"Error: {error}", flush=True)
        print("=" * 80, flush=True)
        return jsonify({'error': 'Authorization header is missing'}), 401
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        print("=" * 80, flush=True)
        print("JWT ERROR: Token not fresh", flush=True)
        print("=" * 80, flush=True)
        return jsonify({'error': 'Token is not fresh'}), 401
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.assets import assets_bp
    from routes.workshops import workshops_bp
    from routes.job_cards import job_cards_bp
    from routes.maintenance import maintenance_bp
    from routes.parts import parts_bp
    from routes.dashboard import dashboard_bp
    from routes.audit import audit_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(assets_bp, url_prefix='/api/assets')
    app.register_blueprint(workshops_bp, url_prefix='/api/workshops')
    app.register_blueprint(job_cards_bp, url_prefix='/api/job-cards')
    app.register_blueprint(maintenance_bp, url_prefix='/api/maintenance')
    app.register_blueprint(parts_bp, url_prefix='/api/parts')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(audit_bp, url_prefix='/api/audit')
    
    # Health check endpoint
    @app.route('/api/health')
    def health():
        return jsonify({'status': 'healthy', 'version': '1.0.0'})
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        import traceback
        print("500 ERROR:", str(error))
        print(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(422)
    def unprocessable(error):
        import traceback
        print("=" * 80, flush=True)
        print("422 ERROR HANDLER:", flush=True)
        print(f"Error: {error}", flush=True)
        print(f"Error Type: {type(error)}", flush=True)
        print(f"Error Description: {error.description if hasattr(error, 'description') else 'N/A'}", flush=True)
        print(traceback.format_exc(), flush=True)
        print("=" * 80, flush=True)
        return jsonify({'error': error.description if hasattr(error, 'description') else 'Unprocessable entity'}), 422
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        import traceback
        print("EXCEPTION:", str(error))
        print(traceback.format_exc())
        return jsonify({'error': str(error)}), 500
    
    return app

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    port = int(os.getenv('PORT', 5000))
    # Disable reloader on Windows to avoid socket errors
    # For production (Render, Railway, etc.), use: gunicorn app:create_app()
    use_reloader = os.name != 'nt' and os.getenv('FLASK_ENV') != 'production'
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=use_reloader)

