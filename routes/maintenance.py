from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, MaintenanceSchedule, Asset, User
from datetime import datetime, timedelta

maintenance_bp = Blueprint('maintenance', __name__)

@maintenance_bp.route('', methods=['GET'])
@jwt_required()
def get_maintenance_schedules():
    """Get all maintenance schedules"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    asset_id = request.args.get('asset_id', type=int)
    is_active = request.args.get('is_active', type=bool)
    
    query = MaintenanceSchedule.query
    
    if asset_id:
        query = query.filter_by(asset_id=asset_id)
    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    
    pagination = query.order_by(MaintenanceSchedule.next_due_date).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    results = []
    for schedule in pagination.items:
        schedule_data = schedule.to_dict()
        if schedule.asset:
            schedule_data['asset_registration'] = schedule.asset.registration
            schedule_data['asset_make'] = schedule.asset.make
            schedule_data['asset_model'] = schedule.asset.model
        results.append(schedule_data)
    
    return jsonify({
        'schedules': results,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }), 200

@maintenance_bp.route('/due-soon', methods=['GET'])
@jwt_required()
def get_due_soon():
    """Get maintenance schedules due within specified days"""
    import traceback
    
    try:
        days = request.args.get('days', 30, type=int)
        future_date = datetime.utcnow().date() + timedelta(days=days)
        
        schedules = MaintenanceSchedule.query.filter(
            MaintenanceSchedule.is_active == True,
            MaintenanceSchedule.next_due_date <= future_date
        ).order_by(MaintenanceSchedule.next_due_date).all()
        
        results = []
        for schedule in schedules:
            schedule_data = schedule.to_dict()
            if schedule.asset:
                schedule_data['asset_registration'] = schedule.asset.registration
                schedule_data['asset_make'] = schedule.asset.make
                schedule_data['asset_model'] = schedule.asset.model
            
            # Calculate days until due
            if schedule.next_due_date:
                days_until = (schedule.next_due_date - datetime.utcnow().date()).days
                schedule_data['days_until_due'] = days_until
                schedule_data['is_overdue'] = days_until < 0
            
            results.append(schedule_data)
        
        return jsonify(results), 200
    except Exception as e:
        print("=" * 80, flush=True)
        print("ERROR in get_due_soon:", flush=True)
        print(f"Exception Type: {type(e).__name__}", flush=True)
        print(f"Exception: {str(e)}", flush=True)
        print(traceback.format_exc(), flush=True)
        print("=" * 80, flush=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 422

@maintenance_bp.route('/<int:schedule_id>', methods=['GET'])
@jwt_required()
def get_maintenance_schedule(schedule_id):
    """Get single maintenance schedule"""
    schedule = MaintenanceSchedule.query.get(schedule_id)
    
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    schedule_data = schedule.to_dict()
    if schedule.asset:
        schedule_data['asset'] = schedule.asset.to_dict()
    
    return jsonify(schedule_data), 200

@maintenance_bp.route('', methods=['POST'])
@jwt_required()
def create_maintenance_schedule():
    """Create new maintenance schedule"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['admin', 'fleet_manager']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    data = request.get_json()
    
    # Validate
    if not data.get('asset_id') or not data.get('name'):
        return jsonify({'error': 'asset_id and name are required'}), 400
    
    if not data.get('frequency_days') and not data.get('frequency_mileage'):
        return jsonify({'error': 'Either frequency_days or frequency_mileage must be specified'}), 400
    
    asset = Asset.query.get(data['asset_id'])
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404
    
    schedule = MaintenanceSchedule(
        asset_id=data['asset_id'],
        schedule_type=data.get('schedule_type', 'periodic'),
        name=data['name'],
        description=data.get('description'),
        frequency_days=data.get('frequency_days'),
        frequency_mileage=data.get('frequency_mileage'),
        next_due_date=datetime.fromisoformat(data['next_due_date']).date() if data.get('next_due_date') else None,
        next_due_mileage=data.get('next_due_mileage'),
        priority=data.get('priority', 'medium'),
        estimated_duration_hours=data.get('estimated_duration_hours'),
        estimated_cost=data.get('estimated_cost')
    )
    
    db.session.add(schedule)
    db.session.commit()
    
    return jsonify(schedule.to_dict()), 201

@maintenance_bp.route('/<int:schedule_id>', methods=['PUT'])
@jwt_required()
def update_maintenance_schedule(schedule_id):
    """Update maintenance schedule"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['admin', 'fleet_manager']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    schedule = MaintenanceSchedule.query.get(schedule_id)
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    data = request.get_json()
    
    updatable_fields = ['name', 'description', 'frequency_days', 'frequency_mileage',
                       'next_due_date', 'next_due_mileage', 'priority', 
                       'estimated_duration_hours', 'estimated_cost', 'is_active']
    
    for field in updatable_fields:
        if field in data:
            if field == 'next_due_date' and data[field]:
                setattr(schedule, field, datetime.fromisoformat(data[field]).date())
            else:
                setattr(schedule, field, data[field])
    
    db.session.commit()
    
    return jsonify(schedule.to_dict()), 200

@maintenance_bp.route('/<int:schedule_id>', methods=['DELETE'])
@jwt_required()
def delete_maintenance_schedule(schedule_id):
    """Delete (deactivate) maintenance schedule"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    if user.role not in ['admin', 'fleet_manager']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    schedule = MaintenanceSchedule.query.get(schedule_id)
    if not schedule:
        return jsonify({'error': 'Schedule not found'}), 404
    
    schedule.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Schedule deactivated'}), 200

