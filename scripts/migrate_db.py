"""
Database migration script
Run this after setting up your cloud database
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db

def migrate():
    """Create all database tables"""
    with app.app_context():
        try:
            print("Creating database tables...")
            db.create_all()
            print("✅ Database tables created successfully!")
            print("\nTables created:")
            print("  - User")
            print("  - Habit")
            print("  - HabitLog")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            sys.exit(1)

if __name__ == '__main__':
    # Check if DATABASE_URL is set
    if not os.environ.get('DATABASE_URL'):
        print("⚠️  Warning: DATABASE_URL not set. Using SQLite for local development.")
        print("   Set DATABASE_URL environment variable for production database.")
    
    migrate()

