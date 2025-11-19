from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from models import db, Asset, JobCard, Part, MaintenanceSchedule
from sqlalchemy import func
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    import traceback
    
    try:
        # Asset statistics
        total_assets = Asset.query.filter(Asset.status != 'disposed').count()
        active_assets = Asset.query.filter_by(status='active').count()
        in_service = Asset.query.filter_by(status='in_service').count()
        
        # Job card statistics
        total_jobs = JobCard.query.count()
        pending_jobs = JobCard.query.filter_by(status='pending').count()
        in_progress_jobs = JobCard.query.filter_by(status='in_progress').count()
        completed_jobs = JobCard.query.filter_by(status='completed').count()
        
        # Maintenance due
        today = datetime.utcnow().date()
        next_30_days = today + timedelta(days=30)
        
        overdue_maintenance = MaintenanceSchedule.query.filter(
            MaintenanceSchedule.is_active == True,
            MaintenanceSchedule.next_due_date < today
        ).count()
        
        due_soon = MaintenanceSchedule.query.filter(
            MaintenanceSchedule.is_active == True,
            MaintenanceSchedule.next_due_date >= today,
            MaintenanceSchedule.next_due_date <= next_30_days
        ).count()
        
        # Parts inventory
        low_stock_parts = Part.query.filter(Part.quantity_in_stock <= Part.reorder_level).count()
        total_parts = Part.query.count()
        
        # Cost analysis (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_costs = db.session.query(func.sum(JobCard.actual_cost))\
            .filter(JobCard.completed_at >= thirty_days_ago).scalar() or 0
        
        # Top cost assets (last 90 days)
        ninety_days_ago = datetime.utcnow() - timedelta(days=90)
        top_cost_assets = db.session.query(
            Asset.registration,
            Asset.make,
            Asset.model,
            func.sum(JobCard.actual_cost).label('total_cost')
        ).join(JobCard).filter(
            JobCard.completed_at >= ninety_days_ago
        ).group_by(Asset.id, Asset.registration, Asset.make, Asset.model)\
         .order_by(db.desc('total_cost')).limit(5).all()
        
        # Workshop utilization
        from models import Workshop
        workshops = Workshop.query.filter_by(is_active=True).all()
        workshop_stats = []
        for workshop in workshops:
            active_jobs = JobCard.query.filter_by(workshop_id=workshop.id)\
                .filter(JobCard.status.in_(['pending', 'in_progress'])).count()
            utilization = round((active_jobs / workshop.capacity) * 100, 1) if workshop.capacity > 0 else 0
            workshop_stats.append({
                'id': workshop.id,
                'name': workshop.name,
                'active_jobs': active_jobs,
                'capacity': workshop.capacity,
                'utilization': utilization
            })
        
        return jsonify({
            'assets': {
                'total': total_assets,
                'active': active_assets,
                'in_service': in_service
            },
            'job_cards': {
                'total': total_jobs,
                'pending': pending_jobs,
                'in_progress': in_progress_jobs,
                'completed': completed_jobs
            },
            'maintenance': {
                'overdue': overdue_maintenance,
                'due_soon': due_soon
            },
            'parts': {
                'total': total_parts,
                'low_stock': low_stock_parts
            },
            'costs': {
                'last_30_days': float(recent_costs)
            },
            'top_cost_assets': [
                {
                    'registration': reg,
                    'make': make,
                    'model': model,
                    'total_cost': float(cost)
                }
                for reg, make, model, cost in top_cost_assets
            ],
            'workshops': workshop_stats
        }), 200
    except Exception as e:
        print("=" * 80, flush=True)
        print("ERROR in get_dashboard_stats:", flush=True)
        print(f"Exception Type: {type(e).__name__}", flush=True)
        print(f"Exception: {str(e)}", flush=True)
        print(traceback.format_exc(), flush=True)
        print("=" * 80, flush=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 422

@dashboard_bp.route('/recent-activity', methods=['GET'])
@jwt_required()
def get_recent_activity():
    """Get recent system activity"""
    import traceback
    
    try:
        # Recent job cards
        recent_jobs = JobCard.query.order_by(JobCard.created_at.desc()).limit(10).all()
        
        jobs_data = []
        for job in recent_jobs:
            job_data = {
                'id': job.id,
                'job_number': job.job_number,
                'title': job.title,
                'status': job.status,
                'priority': job.priority,
                'created_at': job.created_at.isoformat(),
                'asset_registration': job.asset.registration if job.asset else None
            }
            jobs_data.append(job_data)
        
        return jsonify({
            'recent_jobs': jobs_data
        }), 200
    except Exception as e:
        print("=" * 80, flush=True)
        print("ERROR in get_recent_activity:", flush=True)
        print(f"Exception Type: {type(e).__name__}", flush=True)
        print(f"Exception: {str(e)}", flush=True)
        print(traceback.format_exc(), flush=True)
        print("=" * 80, flush=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 422

