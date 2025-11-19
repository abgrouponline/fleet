#!/usr/bin/env python3
"""
Quick database status check script
Run this to verify database initialization
"""
from app import create_app
from models import db, User, Workshop
import os

def check_database():
    """Check database status and initialization"""
    env = os.getenv('FLASK_ENV', 'production')
    app = create_app(env)
    
    with app.app_context():
        print("=" * 60)
        print("🔍 Database Status Check")
        print("=" * 60)
        
        try:
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"\n📋 Database Tables: {len(tables)}")
            if tables:
                for table in sorted(tables):
                    print(f"   ✓ {table}")
            else:
                print("   ⚠️  No tables found - database needs initialization")
                print("   Run: python init_db.py")
                return False
            
            # Check workshops
            try:
                workshop_count = Workshop.query.count()
                print(f"\n🏭 Workshops: {workshop_count}")
                if workshop_count > 0:
                    workshops = Workshop.query.all()
                    for ws in workshops:
                        print(f"   - {ws.name} ({ws.location})")
                else:
                    print("   ⚠️  No workshops found")
            except Exception as e:
                print(f"   ❌ Error checking workshops: {e}")
            
            # Check users
            try:
                user_count = User.query.count()
                print(f"\n👥 Users: {user_count}")
                if user_count > 0:
                    users = User.query.all()
                    for user in users:
                        print(f"   - {user.email} ({user.role})")
                else:
                    print("   ⚠️  No users found")
            except Exception as e:
                print(f"   ❌ Error checking users: {e}")
            
            # Summary
            print("\n" + "=" * 60)
            if workshop_count >= 3 and user_count >= 4:
                print("✅ Database is properly initialized!")
                print("\n📝 Default Login Credentials:")
                print("   Admin: admin@council.gov / ChangeMe123!")
                print("   Fleet Manager: fleet.manager@council.gov / Password123!")
                print("   Supervisor: workshop.supervisor@council.gov / Password123!")
                print("   Technician: technician@council.gov / Password123!")
            else:
                print("⚠️  Database may need initialization")
                print("   Expected: 3 workshops, 4 users")
                print("   Found: {} workshops, {} users".format(workshop_count, user_count))
                print("\n   To initialize, run: python init_db.py")
            print("=" * 60 + "\n")
            
            return workshop_count >= 3 and user_count >= 4
            
        except Exception as e:
            print(f"\n❌ Error checking database: {e}")
            print("   This might indicate a database connection issue")
            print("   Check your DATABASE_URL environment variable")
            print("=" * 60 + "\n")
            return False

if __name__ == '__main__':
    success = check_database()
    exit(0 if success else 1)

