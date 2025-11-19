from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, AuditLog, User

audit_bp = Blueprint('audit', __name__)

@audit_bp.route('', methods=['GET'])
@jwt_required()
def get_audit_logs():
    """Get audit logs with filtering"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    # Only admins and fleet managers can view audit logs
    if user.role not in ['admin', 'fleet_manager']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    entity_type = request.args.get('entity_type')
    entity_id = request.args.get('entity_id', type=int)
    
    query = AuditLog.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter_by(action=action)
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    if entity_id:
        query = query.filter_by(entity_id=entity_id)
    
    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'logs': [log.to_dict() for log in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

@audit_bp.route('/entity/<string:entity_type>/<int:entity_id>', methods=['GET'])
@jwt_required()
def get_entity_audit_trail(entity_type, entity_id):
    """Get audit trail for specific entity"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['admin', 'fleet_manager']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    logs = AuditLog.query.filter_by(
        entity_type=entity_type,
        entity_id=entity_id
    ).order_by(AuditLog.timestamp.desc()).all()
    
    return jsonify([log.to_dict() for log in logs]), 200

