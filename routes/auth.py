from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models import db, User, AuditLog
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT tokens"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        # Log failed login attempt
        audit = AuditLog(
            user_id=user.id if user else None,
            action='login_failed',
            entity_type='user',
            entity_id=user.id if user else None,
            details=f"Failed login attempt for {data['email']}",
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is inactive'}), 403
    
    # Create tokens (JWT requires subject to be a string)
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
    # Log successful login
    audit = AuditLog(
        user_id=user.id,
        action='login',
        entity_type='user',
        entity_id=user.id,
        details='Successful login',
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    current_user_id = get_jwt_identity()
    # Identity is stored as string in JWT, keep it as string
    access_token = create_access_token(identity=str(current_user_id))
    return jsonify({'access_token': access_token}), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user profile"""
    import sys
    import traceback
    
    try:
        print("=" * 80, flush=True)
        print("DEBUG: get_current_user called", flush=True)
        current_user_id = get_jwt_identity()
        print(f"DEBUG: current_user_id = {current_user_id} (type: {type(current_user_id)})", flush=True)
        # Convert string ID back to int for database query
        user = User.query.get(int(current_user_id))
        print(f"DEBUG: user = {user}", flush=True)
        
        if not user:
            print("ERROR: User not found", flush=True)
            return jsonify({'error': 'User not found'}), 404
        
        result = user.to_dict()
        print(f"DEBUG: Returning user data: {result}", flush=True)
        print("=" * 80, flush=True)
        return jsonify(result), 200
    except Exception as e:
        print("=" * 80, flush=True)
        print("ERROR in get_current_user:", flush=True)
        print(f"Exception Type: {type(e).__name__}", flush=True)
        print(f"Exception: {str(e)}", flush=True)
        print(traceback.format_exc(), flush=True)
        print("=" * 80, flush=True)
        sys.stdout.flush()
        db.session.rollback()
        return jsonify({'error': str(e)}), 422

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    data = request.get_json()
    
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'error': 'Current and new password required'}), 400
    
    if not user.check_password(data['current_password']):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    user.set_password(data['new_password'])
    db.session.commit()
    
    # Log password change
    audit = AuditLog(
        user_id=user.id,
        action='password_changed',
        entity_type='user',
        entity_id=user.id,
        details='Password changed',
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'}), 200

