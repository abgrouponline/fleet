from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, JobCard, Asset, User, LaborEntry, PartsUsed, Part, AuditLog
from datetime import datetime
import json

job_cards_bp = Blueprint('job_cards', __name__)

def generate_job_number():
    """Generate unique job card number"""
    from datetime import datetime
    last_job = JobCard.query.order_by(JobCard.id.desc()).first()
    next_num = (last_job.id + 1) if last_job else 1
    return f"JC{datetime.now().strftime('%Y%m')}{next_num:05d}"

@job_cards_bp.route('/new', methods=['OPTIONS'])
def get_new_job_card_metadata_options():
    """Handle CORS preflight for /new endpoint"""
    return '', 200

@job_cards_bp.route('/new', methods=['GET'])
@jwt_required()
def get_new_job_card_metadata():
    """Get metadata for creating a new job card (form options, dropdowns, etc.)"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    # Check permissions
    if user.role not in ['admin', 'fleet_manager', 'supervisor']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    # Get workshops for dropdown
    from models import Workshop
    workshops = Workshop.query.filter_by(is_active=True).all()
    workshop_options = [
        {'id': w.id, 'name': w.name, 'location': w.location}
        for w in workshops
    ]
    
    # Get active assets for dropdown
    assets = Asset.query.filter(Asset.status.in_(['active', 'in_service'])).all()
    asset_options = [
        {
            'id': a.id,
            'registration': a.registration,
            'make': a.make,
            'model': a.model,
            'current_mileage': a.current_mileage,
            'status': a.status
        }
        for a in assets
    ]
    
    # Get active maintenance schedules (optional - for linking planned maintenance)
    from models import MaintenanceSchedule
    maintenance_schedules = MaintenanceSchedule.query.filter_by(is_active=True).all()
    maintenance_options = [
        {
            'id': m.id,
            'asset_id': m.asset_id,
            'maintenance_type': m.maintenance_type,
            'next_due_date': m.next_due_date.isoformat() if m.next_due_date else None,
            'interval_miles': m.interval_miles,
            'interval_months': m.interval_months
        }
        for m in maintenance_schedules
    ]
    
    return jsonify({
        'options': {
            'job_types': [
                {'value': 'planned', 'label': 'Planned Maintenance'},
                {'value': 'unplanned', 'label': 'Unplanned Repair'},
                {'value': 'inspection', 'label': 'Inspection'},
                {'value': 'repair', 'label': 'Repair'},
                {'value': 'service', 'label': 'Service'}
            ],
            'priorities': [
                {'value': 'low', 'label': 'Low'},
                {'value': 'medium', 'label': 'Medium'},
                {'value': 'high', 'label': 'High'},
                {'value': 'critical', 'label': 'Critical'}
            ],
            'statuses': [
                {'value': 'pending', 'label': 'Pending'},
                {'value': 'assigned', 'label': 'Assigned'},
                {'value': 'in_progress', 'label': 'In Progress'},
                {'value': 'on_hold', 'label': 'On Hold'},
                {'value': 'completed', 'label': 'Completed'},
                {'value': 'cancelled', 'label': 'Cancelled'}
            ],
            'workshops': workshop_options,
            'assets': asset_options,
            'maintenance_schedules': maintenance_options
        },
        'defaults': {
            'job_type': 'unplanned',
            'status': 'pending',
            'priority': 'medium'
        },
        'required_fields': ['asset_id', 'workshop_id', 'title'],
        'next_job_number': generate_job_number()
    }), 200

@job_cards_bp.route('', methods=['GET'])
@jwt_required()
def get_job_cards():
    """Get all job cards with filtering"""
    import traceback
    
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        workshop_id = request.args.get('workshop_id', type=int)
        asset_id = request.args.get('asset_id', type=int)
        priority = request.args.get('priority')
        
        query = JobCard.query
        
        if status:
            query = query.filter_by(status=status)
        if workshop_id:
            query = query.filter_by(workshop_id=workshop_id)
        if asset_id:
            query = query.filter_by(asset_id=asset_id)
        if priority:
            query = query.filter_by(priority=priority)
        
        pagination = query.order_by(JobCard.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        results = []
        for job in pagination.items:
            job_data = job.to_dict()
            # Add asset info
            if job.asset:
                job_data['asset_registration'] = job.asset.registration
                job_data['asset_make'] = job.asset.make
                job_data['asset_model'] = job.asset.model
            # Add workshop info
            if job.workshop:
                job_data['workshop_name'] = job.workshop.name
            results.append(job_data)
        
        return jsonify({
            'job_cards': results,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        }), 200
    except Exception as e:
        print("=" * 80, flush=True)
        print("ERROR in get_job_cards:", flush=True)
        print(f"Exception Type: {type(e).__name__}", flush=True)
        print(f"Exception: {str(e)}", flush=True)
        print(traceback.format_exc(), flush=True)
        print("=" * 80, flush=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 422

@job_cards_bp.route('/<int:job_id>', methods=['GET'])
@jwt_required()
def get_job_card(job_id):
    """Get single job card with full details"""
    job = JobCard.query.get(job_id)
    
    if not job:
        return jsonify({'error': 'Job card not found'}), 404
    
    job_data = job.to_dict()
    
    # Add related data
    if job.asset:
        job_data['asset'] = job.asset.to_dict()
    if job.workshop:
        job_data['workshop'] = job.workshop.to_dict()
    if job.assigned_technician:
        job_data['assigned_technician'] = job.assigned_technician.to_dict()
    
    # Labor entries
    job_data['labor_entries'] = [entry.to_dict() for entry in job.labor_entries.all()]
    
    # Parts used
    job_data['parts_used'] = [part.to_dict() for part in job.parts_used.all()]
    
    return jsonify(job_data), 200

@job_cards_bp.route('', methods=['POST'])
@jwt_required()
def create_job_card():
    """Create new job card"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    # Check permissions
    if user.role not in ['admin', 'fleet_manager', 'supervisor']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('asset_id') or not data.get('workshop_id') or not data.get('title'):
        return jsonify({'error': 'asset_id, workshop_id, and title are required'}), 400
    
    # Verify asset exists
    asset = Asset.query.get(data['asset_id'])
    if not asset:
        return jsonify({'error': 'Asset not found'}), 404
    
    job = JobCard(
        job_number=generate_job_number(),
        asset_id=data['asset_id'],
        workshop_id=data['workshop_id'],
        maintenance_schedule_id=data.get('maintenance_schedule_id'),
        job_type=data.get('job_type', 'unplanned'),
        title=data['title'],
        description=data.get('description'),
        reported_issue=data.get('reported_issue'),
        status='pending',
        priority=data.get('priority', 'medium'),
        scheduled_start=datetime.fromisoformat(data['scheduled_start']) if data.get('scheduled_start') else None,
        scheduled_end=datetime.fromisoformat(data['scheduled_end']) if data.get('scheduled_end') else None,
        estimated_cost=data.get('estimated_cost'),
        mileage_at_service=asset.current_mileage,
        created_by=int(current_user_id)
    )
    
    db.session.add(job)
    db.session.commit()
    
    # Log audit
    audit = AuditLog(
        user_id=int(current_user_id),
        action='create',
        entity_type='job_card',
        entity_id=job.id,
        details=json.dumps({'job_number': job.job_number, 'asset': asset.registration}),
        ip_address=request.remote_addr
    )
    db.session.add(audit)
    db.session.commit()
    
    return jsonify(job.to_dict()), 201

@job_cards_bp.route('/<int:job_id>', methods=['PUT'])
@jwt_required()
def update_job_card(job_id):
    """Update job card"""
    current_user_id = get_jwt_identity()
    # Convert string ID back to int for database query
    user = User.query.get(int(current_user_id))
    
    job = JobCard.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job card not found'}), 404
    
    data = request.get_json()
    changes = {}
    
    # Update fields based on user role
    updatable_fields = ['status', 'priority', 'diagnosis', 'work_performed', 
                       'actual_cost', 'labor_cost', 'parts_cost', 'assigned_to']
    
    for field in updatable_fields:
        if field in data:
            old_value = getattr(job, field)
            new_value = data[field]
            if old_value != new_value:
                changes[field] = {'old': str(old_value), 'new': str(new_value)}
                setattr(job, field, new_value)
    
    # Handle status changes
    if 'status' in data:
        if data['status'] == 'in_progress' and not job.actual_start:
            job.actual_start = datetime.utcnow()
        elif data['status'] == 'completed' and not job.actual_end:
            job.actual_end = datetime.utcnow()
            job.completed_at = datetime.utcnow()
    
    if changes:
        job.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Log audit
        audit = AuditLog(
            user_id=int(current_user_id),
            action='update',
            entity_type='job_card',
            entity_id=job.id,
            details=json.dumps(changes),
            ip_address=request.remote_addr
        )
        db.session.add(audit)
        db.session.commit()
    
    return jsonify(job.to_dict()), 200

@job_cards_bp.route('/<int:job_id>/labor', methods=['POST'])
@jwt_required()
def add_labor_entry(job_id):
    """Add labor entry to job card"""
    current_user_id = get_jwt_identity()
    
    job = JobCard.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job card not found'}), 404
    
    data = request.get_json()
    
    if not data.get('technician_id') or not data.get('hours_worked'):
        return jsonify({'error': 'technician_id and hours_worked are required'}), 400
    
    labor = LaborEntry(
        job_card_id=job_id,
        technician_id=data['technician_id'],
        work_date=datetime.fromisoformat(data['work_date']) if data.get('work_date') else datetime.utcnow().date(),
        hours_worked=data['hours_worked'],
        hourly_rate=data.get('hourly_rate', 0),
        total_cost=float(data['hours_worked']) * float(data.get('hourly_rate', 0)),
        notes=data.get('notes')
    )
    
    db.session.add(labor)
    
    # Update job card labor cost
    total_labor = db.session.query(db.func.sum(LaborEntry.total_cost))\
        .filter_by(job_card_id=job_id).scalar() or 0
    total_labor += labor.total_cost
    job.labor_cost = total_labor
    job.actual_cost = (job.labor_cost or 0) + (job.parts_cost or 0)
    
    db.session.commit()
    
    return jsonify(labor.to_dict()), 201

@job_cards_bp.route('/<int:job_id>/parts', methods=['POST'])
@jwt_required()
def add_parts_used(job_id):
    """Add parts used to job card"""
    current_user_id = get_jwt_identity()
    
    job = JobCard.query.get(job_id)
    if not job:
        return jsonify({'error': 'Job card not found'}), 404
    
    data = request.get_json()
    
    if not data.get('part_id') or not data.get('quantity'):
        return jsonify({'error': 'part_id and quantity are required'}), 400
    
    part = Part.query.get(data['part_id'])
    if not part:
        return jsonify({'error': 'Part not found'}), 404
    
    # Check stock
    if part.quantity_in_stock < data['quantity']:
        return jsonify({'error': 'Insufficient stock'}), 400
    
    parts_used = PartsUsed(
        job_card_id=job_id,
        part_id=data['part_id'],
        quantity=data['quantity'],
        unit_cost=part.unit_cost,
        total_cost=float(data['quantity']) * float(part.unit_cost or 0),
        notes=data.get('notes')
    )
    
    db.session.add(parts_used)
    
    # Update part stock
    part.quantity_in_stock -= data['quantity']
    
    # Update job card parts cost
    total_parts = db.session.query(db.func.sum(PartsUsed.total_cost))\
        .filter_by(job_card_id=job_id).scalar() or 0
    total_parts += parts_used.total_cost
    job.parts_cost = total_parts
    job.actual_cost = (job.labor_cost or 0) + (job.parts_cost or 0)
    
    db.session.commit()
    
    return jsonify(parts_used.to_dict()), 201

@job_cards_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_job_stats():
    """Get job card statistics"""
    by_status = db.session.query(JobCard.status, db.func.count(JobCard.id))\
        .group_by(JobCard.status).all()
    by_priority = db.session.query(JobCard.priority, db.func.count(JobCard.id))\
        .group_by(JobCard.priority).all()
    
    return jsonify({
        'by_status': dict(by_status),
        'by_priority': dict(by_priority),
        'total': JobCard.query.count()
    }), 200

