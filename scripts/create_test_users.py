"""
Create 25 Test Users with Sample Data
Generates realistic test data for thorough website testing.
Run this script after initializing the database.
"""

import sys
import os

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User, Habit, HabitLog
from werkzeug.security import generate_password_hash
from datetime import date, timedelta
import uuid
import random

# Sample habit templates
HABIT_TEMPLATES = [
    # Health & Fitness
    {'name': 'Wake up at 7AM', 'emoji': '⏰', 'category': 'Health'},
    {'name': 'No Snoozing', 'emoji': '🔔', 'category': 'Health'},
    {'name': 'Drink 3L Water', 'emoji': '💧', 'category': 'Health'},
    {'name': 'Gym Workout', 'emoji': '💪', 'category': 'Fitness'},
    {'name': 'Morning Run', 'emoji': '🏃', 'category': 'Fitness'},
    {'name': 'Yoga Session', 'emoji': '🧘', 'category': 'Fitness'},
    {'name': '10K Steps', 'emoji': '🚶', 'category': 'Fitness'},
    {'name': 'Meditation', 'emoji': '🧘', 'category': 'Health'},
    {'name': 'No Junk Food', 'emoji': '🍎', 'category': 'Health'},
    {'name': '8 Hours Sleep', 'emoji': '😴', 'category': 'Health'},
    
    # Study & Learning
    {'name': 'Study 1 Hour', 'emoji': '📚', 'category': 'Study'},
    {'name': 'Read 30 Pages', 'emoji': '📖', 'category': 'Study'},
    {'name': 'Practice Coding', 'emoji': '💻', 'category': 'Study'},
    {'name': 'Learn New Skill', 'emoji': '🎓', 'category': 'Study'},
    {'name': 'Write Journal', 'emoji': '📝', 'category': 'Study'},
    
    # Personal Development
    {'name': 'Gratitude Practice', 'emoji': '🙏', 'category': 'Personal'},
    {'name': 'No Social Media', 'emoji': '📱', 'category': 'Personal'},
    {'name': 'Call Family', 'emoji': '📞', 'category': 'Personal'},
    {'name': 'Practice Piano', 'emoji': '🎹', 'category': 'Personal'},
    {'name': 'Creative Writing', 'emoji': '✍️', 'category': 'Personal'},
    
    # Productivity
    {'name': 'Plan Tomorrow', 'emoji': '📋', 'category': 'Productivity'},
    {'name': 'Review Goals', 'emoji': '🎯', 'category': 'Productivity'},
    {'name': 'Clean Room', 'emoji': '🧹', 'category': 'Productivity'},
    {'name': 'Organize Workspace', 'emoji': '🗂️', 'category': 'Productivity'},
]

def create_test_users():
    """Create 25 test users with varied data"""
    with app.app_context():
        print("=" * 60)
        print("Creating 25 Test Users with Sample Data")
        print("=" * 60)
        
        users_created = 0
        today = date.today()
        start_date = today - timedelta(days=60)  # 60 days of data
        
        for i in range(1, 26):
            username = f"testuser{i}"
            email = f"testuser{i}@example.com"
            
            # Check if user already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print(f"⏭️  User {username} already exists, skipping...")
                continue
            
            print(f"\n👤 Creating user {i}/25: {username}")
            
            # Create user (created at random date in past 60 days)
            user_created_date = start_date + timedelta(days=random.randint(0, 60))
            user = User(
                id=uuid.uuid4(),
                username=username,
                email=email,
                password_hash=generate_password_hash('test123'),  # All users have same password for testing
                created_at=user_created_date
            )
            db.session.add(user)
            db.session.commit()
            
            # Create habits for this user (3-8 habits per user)
            num_habits = random.randint(3, 8)
            selected_habits = random.sample(HABIT_TEMPLATES, num_habits)
            
            habits = []
            for habit_template in selected_habits:
                # Habit created when user was created or later
                habit_created_date = user_created_date + timedelta(days=random.randint(0, 10))
                
                habit = Habit(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    name=habit_template['name'],
                    emoji=habit_template['emoji'],
                    category=habit_template['category'],
                    goal=30,  # Default goal
                    created_at=habit_created_date
                )
                habits.append(habit)
                db.session.add(habit)
            
            db.session.commit()
            print(f"   ✅ Created {len(habits)} habits")
            
            # Create habit logs for past 60 days
            log_count = 0
            for habit in habits:
                # Each habit has different completion rate (40% to 90%)
                completion_rate = random.uniform(0.4, 0.9)
                
                # Start tracking from habit creation date
                # Handle both date and datetime objects
                if hasattr(habit.created_at, 'date'):
                    # It's a datetime, convert to date
                    tracking_start = habit.created_at.date()
                elif isinstance(habit.created_at, date):
                    tracking_start = habit.created_at
                else:
                    tracking_start = user_created_date
                
                current_date = tracking_start
                
                while current_date < today:
                    
                    # Randomly mark as completed based on completion rate
                    is_completed = random.random() < completion_rate
                    
                    # Create log entry
                    log = HabitLog(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        habit_id=habit.id,
                        date=current_date,
                        completed=is_completed,
                        created_at=current_date
                    )
                    db.session.add(log)
                    log_count += 1
                    
                    current_date += timedelta(days=1)
            
            db.session.commit()
            print(f"   ✅ Created {log_count} habit logs")
            users_created += 1
        
        print("\n" + "=" * 60)
        print(f"✅ Successfully created {users_created} test users!")
        print("=" * 60)
        print("\n📋 Test Credentials:")
        print("   Username: testuser1 to testuser25")
        print("   Password: test123 (same for all)")
        print("   Email: testuser1@example.com to testuser25@example.com")
        print("\n💡 Each user has:")
        print("   - 3-8 different habits")
        print("   - 40-90% completion rates")
        print("   - 60 days of habit tracking data")
        print("   - Varied start dates (past 60 days)")
        print("\n🚀 Ready for thorough testing!")

if __name__ == '__main__':
    create_test_users()

