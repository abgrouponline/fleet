from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Asset, User, AuditLog, MaintenanceSchedule
from datetime import datetime
import json

assets_bp = Blueprint('assets', __name__)

def log_audit(user_id, action, entity_type, entity_id, details):
    """Helper to log audit entries"""
    audit = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(details) if isinstance(details, dict) else details,
        ip_address=request.remote_addr
    )
    db.session.add(audit)

@assets_bp.route('', methods=['GET'])
@jwt_required()
def get_assets():
    """Get all assets with optional filtering"""
    import traceback
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        asset_type = request.args.get('type')
        search = request.args.get('search')
        
        query = Asset.query
        
        if status:
            query = query.filter_by(status=status)
        if asset_type:
            query = query.filter_by(asset_type=asset_type)
        if search:
            query = query.filter(
                (Asset.registration.ilike(f'%{search}%')) |
                (Asset.make.ilike(f'%{search}%')) |
                (Asset.model.ilike(f'%{search}%'))
            )
        
        pagination = query.order_by(Asset.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'assets': [asset.to_dict() for asset in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200
    except Exception as e:
        print("=" * 80, flush=True)
        print("ERROR in get_assets:", flush=True)
        print(f"Exception Type: {type(e).__name__}", flush=True)
        print(f"Exception: {str(e)}", flush=True)
        print(traceback.format_exc(), flush=True)
        print("=" * 80, flush=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 422

@assets_bp.route('/new', methods=['OPTIONS'])
def get_new_asset_metadata_options():
    """Handle CORS preflight for /new endpoint"""
    return '', 200

@assets_bp.route('/new', methods=['GET'])
@jwt_required()
def get_new_asset_metadata():
    """Get metadata for creating a new asset (form options, dropdowns, etc.)"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    # Check permissions
    if user.role not in ['admin', 'fleet_manager']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    # Get workshops for dropdown
    from models import Workshop
    workshops = Workshop.query.filter_by(is_active=True).all()
    workshop_options = [
        {'id': w.id, 'name': w.name, 'location': w.location}
        for w in workshops
    ]
    
    # Get unique departments and cost centers for suggestions
    departments = db.session.query(Asset.department).distinct().filter(Asset.department.isnot(None)).all()
    cost_centers = db.session.query(Asset.cost_center).distinct().filter(Asset.cost_center.isnot(None)).all()
    
    return jsonify({
        'options': {
            'asset_types': [
                {'value': 'vehicle', 'label': 'Vehicle'},
                {'value': 'equipment', 'label': 'Equipment'},
                {'value': 'plant', 'label': 'Plant'}
            ],
            'statuses': [
                {'value': 'active', 'label': 'Active'},
                {'value': 'in_service', 'label': 'In Service'},
                {'value': 'retired', 'label': 'Retired'},
                {'value': 'disposed', 'label': 'Disposed'}
            ],
            'fuel_types': [
                {'value': 'petrol', 'label': 'Petrol'},
                {'value': 'diesel', 'label': 'Diesel'},
                {'value': 'electric', 'label': 'Electric'},
                {'value': 'hybrid', 'label': 'Hybrid'},
                {'value': 'cng', 'label': 'CNG'},
                {'value': 'lpg', 'label': 'LPG'}
            ],
            'workshops': workshop_options,
            'departments': [d[0] for d in departments if d[0]],
            'cost_centers': [c[0] for c in cost_centers if c[0]]
        },
        'defaults': {
            'status': 'active',
            'current_mileage': 0,
            'asset_type': 'vehicle'
        },
        'required_fields': ['registration', 'asset_type', 'make', 'model']
    }), 200

@assets_bp.route('/<int:asset_id>', methods=['GET'])
@jwt_required()
def get_asset(asset_id):
    """Get single asset by ID"""
    asset = Asset.query.get(asset_id)
    
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404
    
    # Include maintenance schedules and recent job cards
    asset_data = asset.to_dict()
    asset_data['maintenance_schedules'] = [
        schedule.to_dict() for schedule in asset.maintenance_schedules.filter_by(is_active=True).all()
    ]
    asset_data['recent_job_cards'] = [
        job.to_dict() for job in asset.job_cards.order_by(db.desc('created_at')).limit(10).all()
    ]
    
    return jsonify(asset_data), 200

@assets_bp.route('', methods=['POST'])
@jwt_required()
def create_asset():
    """Create new asset"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    # Check permissions
    if user.role not in ['admin', 'fleet_manager']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['registration', 'asset_type', 'make', 'model']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if registration already exists
    if Asset.query.filter_by(registration=data['registration']).first():
        return jsonify({'error': 'Registration already exists'}), 409
    
    asset = Asset(
        registration=data['registration'],
        asset_type=data['asset_type'],
        make=data['make'],
        model=data['model'],
        year=data.get('year'),
        vin=data.get('vin'),
        status=data.get('status', 'active'),
        current_mileage=data.get('current_mileage', 0),
        fuel_type=data.get('fuel_type'),
        capacity=data.get('capacity'),
        purchase_date=datetime.fromisoformat(data['purchase_date']) if data.get('purchase_date') else None,
        purchase_cost=data.get('purchase_cost'),
        current_value=data.get('current_value'),
        cost_center=data.get('cost_center'),
        department=data.get('department'),
        current_location=data.get('current_location'),
        assigned_to=data.get('assigned_to'),
        home_workshop_id=data.get('home_workshop_id'),
        created_by=int(current_user_id)
    )
    
    db.session.add(asset)
    db.session.commit()
    
    # Log audit
    log_audit(current_user_id, 'create', 'asset', asset.id, 
              {'registration': asset.registration, 'make': asset.make, 'model': asset.model})
    db.session.commit()
    
    return jsonify(asset.to_dict()), 201

@assets_bp.route('/<int:asset_id>', methods=['PUT'])
@jwt_required()
def update_asset(asset_id):
    """Update asset"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    # Check permissions
    if user.role not in ['admin', 'fleet_manager']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404
    
    data = request.get_json()
    changes = {}
    
    # Update fields
    updatable_fields = [
        'status', 'current_mileage', 'current_value', 'current_location',
        'assigned_to', 'home_workshop_id', 'department', 'cost_center'
    ]
    
    for field in updatable_fields:
        if field in data:
            old_value = getattr(asset, field)
            new_value = data[field]
            if old_value != new_value:
                changes[field] = {'old': old_value, 'new': new_value}
                setattr(asset, field, new_value)
    
    if changes:
        asset.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log audit
        log_audit(current_user_id, 'update', 'asset', asset.id, changes)
        db.session.commit()
    
    return jsonify(asset.to_dict()), 200

@assets_bp.route('/<int:asset_id>', methods=['DELETE'])
@jwt_required()
def delete_asset(asset_id):
    """Delete asset (soft delete by setting status to 'disposed')"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    # Only admins can delete
    if user.role != 'admin':
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    asset = Asset.query.get(asset_id)
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404
    
    asset.status = 'disposed'
    asset.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Log audit
    log_audit(current_user_id, 'delete', 'asset', asset.id, 
              {'registration': asset.registration, 'action': 'marked as disposed'})
    db.session.commit()
    
    return jsonify({'message': 'Asset marked as disposed'}), 200

@assets_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_asset_stats():
    """Get asset statistics"""
    total = Asset.query.filter(Asset.status != 'disposed').count()
    by_type = db.session.query(Asset.asset_type, db.func.count(Asset.id))\
        .filter(Asset.status != 'disposed')\
        .group_by(Asset.asset_type).all()
    by_status = db.session.query(Asset.status, db.func.count(Asset.id))\
        .filter(Asset.status != 'disposed')\
        .group_by(Asset.status).all()
    
    return jsonify({
        'total': total,
        'by_type': dict(by_type),
        'by_status': dict(by_status)
    }), 200

