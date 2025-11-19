from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, fleet_manager, supervisor, technician, viewer
    is_active = db.Column(db.Boolean, default=True)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshops.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    workshop = db.relationship('Workshop', backref='staff', foreign_keys=[workshop_id])
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'is_active': self.is_active,
            'workshop_id': self.workshop_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Asset(db.Model):
    __tablename__ = 'assets'
    
    id = db.Column(db.Integer, primary_key=True)
    registration = db.Column(db.String(50), unique=True, nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)  # vehicle, equipment, plant
    make = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer)
    vin = db.Column(db.String(100), unique=True)
    
    # Operational details
    status = db.Column(db.String(50), default='active')  # active, in_service, retired, disposed
    current_mileage = db.Column(db.Integer, default=0)
    fuel_type = db.Column(db.String(50))
    capacity = db.Column(db.String(100))
    
    # Financial
    purchase_date = db.Column(db.Date)
    purchase_cost = db.Column(db.Numeric(10, 2))
    current_value = db.Column(db.Numeric(10, 2))
    cost_center = db.Column(db.String(100))
    department = db.Column(db.String(100))
    
    # Location & Assignment
    current_location = db.Column(db.String(200))
    assigned_to = db.Column(db.String(100))
    home_workshop_id = db.Column(db.Integer, db.ForeignKey('workshops.id'))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    home_workshop = db.relationship('Workshop', backref='assets')
    maintenance_schedules = db.relationship('MaintenanceSchedule', backref='asset', lazy='dynamic')
    job_cards = db.relationship('JobCard', backref='asset', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'registration': self.registration,
            'asset_type': self.asset_type,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'vin': self.vin,
            'status': self.status,
            'current_mileage': self.current_mileage,
            'fuel_type': self.fuel_type,
            'capacity': self.capacity,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'purchase_cost': float(self.purchase_cost) if self.purchase_cost else None,
            'current_value': float(self.current_value) if self.current_value else None,
            'cost_center': self.cost_center,
            'department': self.department,
            'current_location': self.current_location,
            'assigned_to': self.assigned_to,
            'home_workshop_id': self.home_workshop_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Workshop(db.Model):
    __tablename__ = 'workshops'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    capacity = db.Column(db.Integer, default=5)  # Number of vehicles that can be serviced simultaneously
    specializations = db.Column(db.Text)  # JSON string of specializations
    is_active = db.Column(db.Boolean, default=True)
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(120))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'capacity': self.capacity,
            'specializations': self.specializations,
            'is_active': self.is_active,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email,
            'staff_count': len(self.staff)
        }


class MaintenanceSchedule(db.Model):
    __tablename__ = 'maintenance_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    
    schedule_type = db.Column(db.String(50), nullable=False)  # periodic, inspection, service
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Trigger conditions (at least one must be set)
    frequency_days = db.Column(db.Integer)  # Every X days
    frequency_mileage = db.Column(db.Integer)  # Every X miles/km
    
    # Next due
    next_due_date = db.Column(db.Date)
    next_due_mileage = db.Column(db.Integer)
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    estimated_duration_hours = db.Column(db.Numeric(5, 2))
    estimated_cost = db.Column(db.Numeric(10, 2))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'schedule_type': self.schedule_type,
            'name': self.name,
            'description': self.description,
            'frequency_days': self.frequency_days,
            'frequency_mileage': self.frequency_mileage,
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'next_due_mileage': self.next_due_mileage,
            'is_active': self.is_active,
            'priority': self.priority,
            'estimated_duration_hours': float(self.estimated_duration_hours) if self.estimated_duration_hours else None,
            'estimated_cost': float(self.estimated_cost) if self.estimated_cost else None
        }


class JobCard(db.Model):
    __tablename__ = 'job_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    job_number = db.Column(db.String(50), unique=True, nullable=False)
    
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False)
    workshop_id = db.Column(db.Integer, db.ForeignKey('workshops.id'), nullable=False)
    maintenance_schedule_id = db.Column(db.Integer, db.ForeignKey('maintenance_schedules.id'), nullable=True)
    
    # Job details
    job_type = db.Column(db.String(50), nullable=False)  # planned, unplanned, inspection, repair
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    reported_issue = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    work_performed = db.Column(db.Text)
    
    # Status & Priority
    status = db.Column(db.String(50), default='pending')  # pending, assigned, in_progress, on_hold, completed, cancelled
    priority = db.Column(db.String(20), default='medium')
    
    # Scheduling
    scheduled_start = db.Column(db.DateTime)
    scheduled_end = db.Column(db.DateTime)
    actual_start = db.Column(db.DateTime)
    actual_end = db.Column(db.DateTime)
    
    # Financial
    estimated_cost = db.Column(db.Numeric(10, 2))
    actual_cost = db.Column(db.Numeric(10, 2))
    labor_cost = db.Column(db.Numeric(10, 2))
    parts_cost = db.Column(db.Numeric(10, 2))
    
    # Mileage at service
    mileage_at_service = db.Column(db.Integer)
    
    # Assignment
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    workshop = db.relationship('Workshop', backref='job_cards')
    assigned_technician = db.relationship('User', foreign_keys=[assigned_to], backref='assigned_jobs')
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_jobs')
    labor_entries = db.relationship('LaborEntry', backref='job_card', lazy='dynamic', cascade='all, delete-orphan')
    parts_used = db.relationship('PartsUsed', backref='job_card', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_number': self.job_number,
            'asset_id': self.asset_id,
            'workshop_id': self.workshop_id,
            'maintenance_schedule_id': self.maintenance_schedule_id,
            'job_type': self.job_type,
            'title': self.title,
            'description': self.description,
            'reported_issue': self.reported_issue,
            'diagnosis': self.diagnosis,
            'work_performed': self.work_performed,
            'status': self.status,
            'priority': self.priority,
            'scheduled_start': self.scheduled_start.isoformat() if self.scheduled_start else None,
            'scheduled_end': self.scheduled_end.isoformat() if self.scheduled_end else None,
            'actual_start': self.actual_start.isoformat() if self.actual_start else None,
            'actual_end': self.actual_end.isoformat() if self.actual_end else None,
            'estimated_cost': float(self.estimated_cost) if self.estimated_cost else None,
            'actual_cost': float(self.actual_cost) if self.actual_cost else None,
            'labor_cost': float(self.labor_cost) if self.labor_cost else None,
            'parts_cost': float(self.parts_cost) if self.parts_cost else None,
            'mileage_at_service': self.mileage_at_service,
            'assigned_to': self.assigned_to,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class LaborEntry(db.Model):
    __tablename__ = 'labor_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    job_card_id = db.Column(db.Integer, db.ForeignKey('job_cards.id'), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    work_date = db.Column(db.Date, nullable=False)
    hours_worked = db.Column(db.Numeric(5, 2), nullable=False)
    hourly_rate = db.Column(db.Numeric(10, 2))
    total_cost = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    technician = db.relationship('User', backref='labor_entries')
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_card_id': self.job_card_id,
            'technician_id': self.technician_id,
            'technician_name': f"{self.technician.first_name} {self.technician.last_name}" if self.technician else None,
            'work_date': self.work_date.isoformat() if self.work_date else None,
            'hours_worked': float(self.hours_worked),
            'hourly_rate': float(self.hourly_rate) if self.hourly_rate else None,
            'total_cost': float(self.total_cost) if self.total_cost else None,
            'notes': self.notes
        }


class Part(db.Model):
    __tablename__ = 'parts'
    
    id = db.Column(db.Integer, primary_key=True)
    part_number = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    
    # Supplier info
    supplier_name = db.Column(db.String(200))
    supplier_part_number = db.Column(db.String(100))
    
    # Inventory
    quantity_in_stock = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=5)
    unit_cost = db.Column(db.Numeric(10, 2))
    
    # Location
    storage_location = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'part_number': self.part_number,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'supplier_name': self.supplier_name,
            'supplier_part_number': self.supplier_part_number,
            'quantity_in_stock': self.quantity_in_stock,
            'reorder_level': self.reorder_level,
            'unit_cost': float(self.unit_cost) if self.unit_cost else None,
            'storage_location': self.storage_location,
            'needs_reorder': self.quantity_in_stock <= self.reorder_level
        }


class PartsUsed(db.Model):
    __tablename__ = 'parts_used'
    
    id = db.Column(db.Integer, primary_key=True)
    job_card_id = db.Column(db.Integer, db.ForeignKey('job_cards.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2))
    total_cost = db.Column(db.Numeric(10, 2))
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    part = db.relationship('Part', backref='usage_history')
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_card_id': self.job_card_id,
            'part_id': self.part_id,
            'part_number': self.part.part_number if self.part else None,
            'part_name': self.part.name if self.part else None,
            'quantity': self.quantity,
            'unit_cost': float(self.unit_cost) if self.unit_cost else None,
            'total_cost': float(self.total_cost) if self.total_cost else None,
            'notes': self.notes
        }


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)  # create, update, delete, login, etc.
    entity_type = db.Column(db.String(100), nullable=False)  # asset, job_card, user, etc.
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # JSON string with additional details
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    user = db.relationship('User', backref='audit_logs')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user.email if self.user else 'System',
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat()
        }

