from app import create_app
from models import db, User, Workshop
from datetime import datetime

def init_database():
    """Initialize the database with tables and seed data"""
    app = create_app('development')
    
    with app.app_context():
        # Drop all tables and recreate (WARNING: This deletes all data)
        print("Creating database tables...")
        db.drop_all()
        db.create_all()
        
        # Create default workshops
        print("Creating workshops...")
        workshops = [
            Workshop(
                name='North Workshop',
                location='123 North Street, City',
                capacity=10,
                specializations='Heavy vehicles, Plant equipment',
                contact_phone='555-0101',
                contact_email='north@council.gov'
            ),
            Workshop(
                name='Central Workshop',
                location='456 Central Avenue, City',
                capacity=8,
                specializations='Light vehicles, Cars, Vans',
                contact_phone='555-0102',
                contact_email='central@council.gov'
            ),
            Workshop(
                name='South Workshop',
                location='789 South Road, City',
                capacity=6,
                specializations='Specialist equipment, Emergency vehicles',
                contact_phone='555-0103',
                contact_email='south@council.gov'
            )
        ]
        
        for workshop in workshops:
            db.session.add(workshop)
        
        db.session.commit()
        
        # Create default users
        print("Creating users...")
        admin = User(
            email='admin@council.gov',
            first_name='System',
            last_name='Administrator',
            role='admin',
            is_active=True
        )
        admin.set_password('ChangeMe123!')
        db.session.add(admin)
        
        fleet_manager = User(
            email='fleet.manager@council.gov',
            first_name='Sarah',
            last_name='Johnson',
            role='fleet_manager',
            is_active=True
        )
        fleet_manager.set_password('Password123!')
        db.session.add(fleet_manager)
        
        supervisor = User(
            email='workshop.supervisor@council.gov',
            first_name='Mike',
            last_name='Thompson',
            role='supervisor',
            is_active=True,
            workshop_id=1
        )
        supervisor.set_password('Password123!')
        db.session.add(supervisor)
        
        technician = User(
            email='technician@council.gov',
            first_name='David',
            last_name='Martinez',
            role='technician',
            is_active=True,
            workshop_id=1
        )
        technician.set_password('Password123!')
        db.session.add(technician)
        
        db.session.commit()
        
        print("\n" + "="*50)
        print("Database initialized successfully!")
        print("="*50)
        print("\nDefault Users Created:")
        print(f"  Admin: admin@council.gov / ChangeMe123!")
        print(f"  Fleet Manager: fleet.manager@council.gov / Password123!")
        print(f"  Supervisor: workshop.supervisor@council.gov / Password123!")
        print(f"  Technician: technician@council.gov / Password123!")
        print("\nWorkshops Created:")
        for ws in workshops:
            print(f"  - {ws.name} ({ws.location})")
        print("="*50 + "\n")

if __name__ == '__main__':
    init_database()

