from models import db, User, Workshop
from datetime import datetime
import os
import time
from threading import Lock

_db_initialized = False
_db_init_lock = Lock()

def init_database(force=False):
    """
    Initialize the database with tables and seed data.
    Safe to run multiple times - only creates if doesn't exist.
    
    Args:
        force: If True, drops all tables and recreates (WARNING: deletes all data)
    """
    # Use production config for hosted environments
    env = os.getenv('FLASK_ENV', 'production')
    from app import create_app  # Local import to avoid circular dependency
    app = create_app(env)
    
    with app.app_context():
        # Check if tables already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables_exist = inspector.get_table_names()
        
        if force:
            # Drop all tables and recreate (WARNING: This deletes all data)
            print("⚠️  FORCE MODE: Dropping all tables...")
            db.drop_all()
            db.create_all()
            print("✅ Database tables recreated")
        elif tables_exist:
            # Tables exist, just ensure they're up to date
            print("📋 Database tables already exist, ensuring they're up to date...")
            db.create_all()  # This is safe - only creates missing tables
            print("✅ Database tables verified")
        else:
            # No tables exist, create them
            print("📋 Creating database tables...")
            db.create_all()
            print("✅ Database tables created")
        
        # Seed default workshops (only if they don't exist)
        print("🔧 Checking workshops...")
        existing_workshops = Workshop.query.count()
        
        if existing_workshops == 0:
            print("📝 Creating default workshops...")
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
            print(f"✅ Created {len(workshops)} default workshops")
        else:
            print(f"✅ {existing_workshops} workshops already exist, skipping creation")
        
        # Seed default users (only if they don't exist)
        print("👥 Checking users...")
        existing_users = User.query.count()
        
        if existing_users == 0:
            print("📝 Creating default users...")
            
            # Ensure workshops exist before creating users
            if Workshop.query.count() == 0:
                print("⚠️  No workshops found, creating workshops first...")
                init_database(force=False)  # Recursive call to create workshops
                db.session.commit()
            
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
            print("✅ Created 4 default users")
        else:
            print(f"✅ {existing_users} users already exist, skipping creation")
        
        print("\n" + "="*50)
        print("✅ Database initialization complete!")
        print("="*50)
        
        # Print summary
        workshop_count = Workshop.query.count()
        user_count = User.query.count()
        
        print(f"\n📊 Database Status:")
        print(f"   Workshops: {workshop_count}")
        print(f"   Users: {user_count}")
        
        if user_count > 0:
            print(f"\n👤 Default Login Credentials:")
            print(f"   Admin: admin@council.gov / ChangeMe123!")
            print(f"   Fleet Manager: fleet.manager@council.gov / Password123!")
            print(f"   Supervisor: workshop.supervisor@council.gov / Password123!")
            print(f"   Technician: technician@council.gov / Password123!")
            print(f"\n⚠️  IMPORTANT: Change these passwords after first login!")
        
        print("="*50 + "\n")
        
        global _db_initialized
        _db_initialized = True
        return True

def auto_init_on_startup():
    """
    Automatically initialize database on startup if AUTO_INIT_DB is enabled.
    Safe to call on every startup - only initializes if needed.
    Includes retry logic for PostgreSQL connection issues.
    This function should be called WITHIN an app context.
    """
    auto_init = os.getenv('AUTO_INIT_DB', 'false').lower() == 'true'
    
    if not auto_init:
        print("ℹ️  Auto-initialization disabled (set AUTO_INIT_DB=true to enable)")
        return True
    
    # Retry logic for PostgreSQL connection (especially on Render)
    max_retries = 5
    retry_delay = 3  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🔄 Auto-initialization enabled, checking database... (attempt {attempt}/{max_retries})")
            
            # Test database connection first
            from sqlalchemy import text
            from models import db
            
            try:
                # Try a simple query to test connection
                db.session.execute(text("SELECT 1"))
                db.session.commit()
                print("✅ Database connection successful")
            except Exception as conn_error:
                if attempt < max_retries:
                    print(f"⚠️  Database connection failed (attempt {attempt}/{max_retries}): {conn_error}")
                    print(f"   Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise conn_error
            
            # If connection works, proceed with initialization
            # We're already in an app context, so call the initialization logic directly
            ensure_database_initialized(force=False, silent=False)
            print("✅ Auto-initialization completed successfully")
            return True
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"⚠️  Auto-initialization failed (attempt {attempt}/{max_retries}): {error_msg}")
            
            # Check if it's a connection error or table doesn't exist
            if "connection" in error_msg.lower() or "does not exist" in error_msg.lower() or "relation" in error_msg.lower() or "table" in error_msg.lower():
                if attempt < max_retries:
                    print(f"   Database may not be ready yet, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"   Max retries reached. Database may not be accessible.")
                    print(f"   Full error: {traceback.format_exc()}")
                    print("   You may need to initialize manually: python init_db.py")
                    return False
            else:
                # Other errors - don't retry
                print(f"   Full error: {traceback.format_exc()}")
                print("   You may need to initialize manually: python init_db.py")
                return False
    
    return False

def ensure_database_initialized(force=False, silent=False):
    """
    Ensure the database is initialized. Safe to call multiple times.
    Returns True if initialized successfully, False otherwise.
    """
    global _db_initialized
    if _db_initialized and not force:
        return True
    
    with _db_init_lock:
        if _db_initialized and not force:
            return True
        try:
            _init_database_in_context(force=force, silent=silent)
            _db_initialized = True
            return True
        except Exception as e:
            if not silent:
                import traceback
                print(f"❌ Database initialization error: {e}")
                print(traceback.format_exc())
            return False


def _init_database_in_context(force=False, silent=False):
    """
    Internal function to initialize database within an existing app context.
    This is called by auto_init_on_startup() which is already in an app context.
    """
    from models import db, User, Workshop
    from sqlalchemy import inspect
    
    # Check if tables already exist
    inspector = inspect(db.engine)
    tables_exist = inspector.get_table_names()
    
    if force:
        # Drop all tables and recreate (WARNING: This deletes all data)
        print("⚠️  FORCE MODE: Dropping all tables...")
        db.drop_all()
        db.create_all()
        print("✅ Database tables recreated")
    elif tables_exist:
        # Tables exist, just ensure they're up to date
        print("📋 Database tables already exist, ensuring they're up to date...")
        db.create_all()  # This is safe - only creates missing tables
        print("✅ Database tables verified")
    else:
        # No tables exist, create them
        print("📋 Creating database tables...")
        db.create_all()
        print("✅ Database tables created")
    
    # Seed default workshops (only if they don't exist)
    print("🔧 Checking workshops...")
    existing_workshops = Workshop.query.count()
    
    if existing_workshops == 0:
        print("📝 Creating default workshops...")
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
        print(f"✅ Created {len(workshops)} default workshops")
    else:
        print(f"✅ {existing_workshops} workshops already exist, skipping creation")
    
    # Seed default users (only if they don't exist)
    print("👥 Checking users...")
    existing_users = User.query.count()
    
    if existing_users == 0:
        print("📝 Creating default users...")
        
        # Ensure workshops exist before creating users
        if Workshop.query.count() == 0:
            print("⚠️  No workshops found, creating workshops first...")
            _init_database_in_context(force=False)  # Recursive call to create workshops
            db.session.commit()
        
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
        print("✅ Created 4 default users")
    else:
        print(f"✅ {existing_users} users already exist, skipping creation")
    
    print("\n" + "="*50)
    print("✅ Database initialization complete!")
    print("="*50)
    
    # Print summary
    workshop_count = Workshop.query.count()
    user_count = User.query.count()
    
    print(f"\n📊 Database Status:")
    print(f"   Workshops: {workshop_count}")
    print(f"   Users: {user_count}")
    
    if user_count > 0:
        print(f"\n👤 Default Login Credentials:")
        print(f"   Admin: admin@council.gov / ChangeMe123!")
        print(f"   Fleet Manager: fleet.manager@council.gov / Password123!")
        print(f"   Supervisor: workshop.supervisor@council.gov / Password123!")
        print(f"   Technician: technician@council.gov / Password123!")
        print(f"\n⚠️  IMPORTANT: Change these passwords after first login!")
    
    print("="*50 + "\n")
    
    return True

if __name__ == '__main__':
    import sys
    
    # Check for force flag
    force = '--force' in sys.argv or '-f' in sys.argv
    
    if force:
        print("⚠️  WARNING: Force mode will delete all existing data!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            sys.exit(0)
    
    init_database(force=force)
