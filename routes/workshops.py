from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Workshop, User, JobCard
from sqlalchemy import func

workshops_bp = Blueprint('workshops', __name__)

@workshops_bp.route('', methods=['GET'])
@jwt_required()
def get_workshops():
    """Get all workshops"""
    import traceback
    
    try:
        workshops = Workshop.query.filter_by(is_active=True).all()
        
        result = []
        for workshop in workshops:
            workshop_data = workshop.to_dict()
            # Add current workload
            active_jobs = JobCard.query.filter_by(workshop_id=workshop.id)\
                .filter(JobCard.status.in_(['pending', 'assigned', 'in_progress'])).count()
            workshop_data['active_jobs'] = active_jobs
            workshop_data['utilization'] = round((active_jobs / workshop.capacity) * 100, 1) if workshop.capacity > 0 else 0
            result.append(workshop_data)
        
        return jsonify(result), 200
    except Exception as e:
        print("=" * 80, flush=True)
        print("ERROR in get_workshops:", flush=True)
        print(f"Exception Type: {type(e).__name__}", flush=True)
        print(f"Exception: {str(e)}", flush=True)
        print(traceback.format_exc(), flush=True)
        print("=" * 80, flush=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 422

@workshops_bp.route('/<int:workshop_id>', methods=['GET'])
@jwt_required()
def get_workshop(workshop_id):
    """Get workshop details"""
    workshop = Workshop.query.get(workshop_id)
    
    if not workshop:
        return jsonify({'error': 'Workshop not found'}), 404
    
    workshop_data = workshop.to_dict()
    
    # Add detailed stats
    workshop_data['active_jobs'] = JobCard.query.filter_by(workshop_id=workshop.id)\
        .filter(JobCard.status.in_(['pending', 'assigned', 'in_progress'])).count()
    
    workshop_data['staff'] = [user.to_dict() for user in workshop.staff]
    
    # Recent job cards
    workshop_data['recent_jobs'] = [
        job.to_dict() for job in JobCard.query.filter_by(workshop_id=workshop.id)\
            .order_by(JobCard.created_at.desc()).limit(20).all()
    ]
    
    return jsonify(workshop_data), 200

@workshops_bp.route('', methods=['POST'])
@jwt_required()
def create_workshop():
    """Create new workshop"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    # Only admins can create workshops
    if user.role != 'admin':
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    data = request.get_json()
    
    required_fields = ['name', 'location']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    workshop = Workshop(
        name=data['name'],
        location=data['location'],
        capacity=data.get('capacity', 5),
        specializations=data.get('specializations'),
        contact_phone=data.get('contact_phone'),
        contact_email=data.get('contact_email')
    )
    
    db.session.add(workshop)
    db.session.commit()
    
    return jsonify(workshop.to_dict()), 201

@workshops_bp.route('/<int:workshop_id>', methods=['PUT'])
@jwt_required()
def update_workshop(workshop_id):
    """Update workshop"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['admin', 'supervisor']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    workshop = Workshop.query.get(workshop_id)
    if not workshop:
        return jsonify({'error': 'Workshop not found'}), 404
    
    data = request.get_json()
    
    updatable_fields = ['name', 'location', 'capacity', 'specializations', 
                       'contact_phone', 'contact_email', 'is_active']
    
    for field in updatable_fields:
        if field in data:
            setattr(workshop, field, data[field])
    
    db.session.commit()
    
    return jsonify(workshop.to_dict()), 200

