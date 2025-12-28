"""
Delete All Test Users and Their Data
Safely deletes all test users along with their habits and logs.
"""

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User, Habit, HabitLog

def delete_test_users():
    """Delete all test users and their associated data"""
    with app.app_context():
        print("=" * 60)
        print("Deleting All Test Users and Their Data")
        print("=" * 60)
        
        # Find all test users
        test_users = User.query.filter(User.username.like('testuser%')).all()
        
        if not test_users:
            print("\n✅ No test users found. Nothing to delete.")
            return
        
        print(f"\n📋 Found {len(test_users)} test users to delete")
        
        total_logs_deleted = 0
        total_habits_deleted = 0
        
        # Delete each user and their data
        for user in test_users:
            # Delete habit logs first
            logs = HabitLog.query.filter_by(user_id=user.id).all()
            total_logs_deleted += len(logs)
            for log in logs:
                db.session.delete(log)
            
            # Delete habits
            habits = Habit.query.filter_by(user_id=user.id).all()
            total_habits_deleted += len(habits)
            for habit in habits:
                db.session.delete(habit)
            
            # Delete user
            db.session.delete(user)
        
        # Commit all deletions
        db.session.commit()
        
        print(f"\n✅ Deleted:")
        print(f"   - {len(test_users)} users")
        print(f"   - {total_habits_deleted} habits")
        print(f"   - {total_logs_deleted} habit logs")
        print("\n✅ All test users and their data have been deleted!")

if __name__ == '__main__':
    delete_test_users()

