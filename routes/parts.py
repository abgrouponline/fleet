from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Part, User

parts_bp = Blueprint('parts', __name__)

@parts_bp.route('', methods=['GET'])
@jwt_required()
def get_parts():
    """Get all parts with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category = request.args.get('category')
    search = request.args.get('search')
    low_stock = request.args.get('low_stock', type=bool)
    
    query = Part.query
    
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            (Part.part_number.ilike(f'%{search}%')) |
            (Part.name.ilike(f'%{search}%'))
        )
    if low_stock:
        query = query.filter(Part.quantity_in_stock <= Part.reorder_level)
    
    pagination = query.order_by(Part.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'parts': [part.to_dict() for part in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

@parts_bp.route('/<int:part_id>', methods=['GET'])
@jwt_required()
def get_part(part_id):
    """Get single part"""
    part = Part.query.get(part_id)
    
    if not part:
        return jsonify({'error': 'Part not found'}), 404
    
    part_data = part.to_dict()
    
    # Add usage history
    part_data['recent_usage'] = [
        {
            'job_card_id': usage.job_card_id,
            'quantity': usage.quantity,
            'date': usage.created_at.isoformat()
        }
        for usage in part.usage_history[:10]
    ]
    
    return jsonify(part_data), 200

@parts_bp.route('', methods=['POST'])
@jwt_required()
def create_part():
    """Create new part"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['admin', 'fleet_manager', 'supervisor']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    data = request.get_json()
    
    if not data.get('part_number') or not data.get('name'):
        return jsonify({'error': 'part_number and name are required'}), 400
    
    # Check if part number exists
    if Part.query.filter_by(part_number=data['part_number']).first():
        return jsonify({'error': 'Part number already exists'}), 409
    
    part = Part(
        part_number=data['part_number'],
        name=data['name'],
        description=data.get('description'),
        category=data.get('category'),
        supplier_name=data.get('supplier_name'),
        supplier_part_number=data.get('supplier_part_number'),
        quantity_in_stock=data.get('quantity_in_stock', 0),
        reorder_level=data.get('reorder_level', 5),
        unit_cost=data.get('unit_cost'),
        storage_location=data.get('storage_location')
    )
    
    db.session.add(part)
    db.session.commit()
    
    return jsonify(part.to_dict()), 201

@parts_bp.route('/<int:part_id>', methods=['PUT'])
@jwt_required()
def update_part(part_id):
    """Update part"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['admin', 'fleet_manager', 'supervisor']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    part = Part.query.get(part_id)
    if not part:
        return jsonify({'error': 'Part not found'}), 404
    
    data = request.get_json()
    
    updatable_fields = ['name', 'description', 'category', 'supplier_name',
                       'supplier_part_number', 'quantity_in_stock', 'reorder_level',
                       'unit_cost', 'storage_location']
    
    for field in updatable_fields:
        if field in data:
            setattr(part, field, data[field])
    
    db.session.commit()
    
    return jsonify(part.to_dict()), 200

@parts_bp.route('/<int:part_id>/adjust-stock', methods=['POST'])
@jwt_required()
def adjust_stock(part_id):
    """Adjust part stock level"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['admin', 'fleet_manager', 'supervisor']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    part = Part.query.get(part_id)
    if not part:
        return jsonify({'error': 'Part not found'}), 404
    
    data = request.get_json()
    
    if 'adjustment' not in data:
        return jsonify({'error': 'adjustment value required'}), 400
    
    adjustment = int(data['adjustment'])
    new_quantity = part.quantity_in_stock + adjustment
    
    if new_quantity < 0:
        return jsonify({'error': 'Resulting quantity cannot be negative'}), 400
    
    part.quantity_in_stock = new_quantity
    db.session.commit()
    
    return jsonify(part.to_dict()), 200

@parts_bp.route('/low-stock', methods=['GET'])
@jwt_required()
def get_low_stock():
    """Get parts that need reordering"""
    parts = Part.query.filter(Part.quantity_in_stock <= Part.reorder_level).all()
    return jsonify([part.to_dict() for part in parts]), 200

