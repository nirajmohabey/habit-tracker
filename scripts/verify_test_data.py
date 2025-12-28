"""
Verify Test Data Creation
Quick script to check test users and their data.
"""

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User, Habit, HabitLog

def verify_test_data():
    """Verify test users and their data"""
    with app.app_context():
        users = User.query.filter(User.username.like('testuser%')).all()
        print(f'✅ Total test users: {len(users)}')
        
        total_habits = sum(len(u.habits) for u in users)
        total_logs = HabitLog.query.join(User).filter(User.username.like('testuser%')).count()
        
        print(f'✅ Total habits: {total_habits}')
        print(f'✅ Total habit logs: {total_logs}')
        
        # Sample user check
        sample_user = User.query.filter_by(username='testuser1').first()
        if sample_user:
            completed_logs = sum(1 for log in sample_user.logs if log.completed)
            print(f'\n📊 Sample data (testuser1):')
            print(f'   - {len(sample_user.habits)} habits')
            print(f'   - {len(sample_user.logs)} habit logs')
            print(f'   - {completed_logs} completed days marked')
            print(f'   - {len(sample_user.logs) - completed_logs} missed days')
        
        print('\n✅ All test data verified!')

if __name__ == '__main__':
    verify_test_data()

