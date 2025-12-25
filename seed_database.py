"""
Database Seeding Script
Creates a dummy user with sample habits for testing purposes.
Run this script after initializing the database to populate it with test data.
"""

from app import app, db, User, Habit, HabitLog
from werkzeug.security import generate_password_hash
from datetime import date, timedelta
import uuid

def seed_database():
    """Create a dummy user with sample habits and logs"""
    with app.app_context():
        # Check if dummy user already exists
        existing_user = User.query.filter_by(username='demo').first()
        if existing_user:
            print("Demo user already exists. Skipping seed.")
            return
        
        print("Creating demo user...")
        
        # Create demo user
        demo_user = User(
            id=uuid.uuid4(),
            username='demo',
            email='demo@example.com',
            password_hash=generate_password_hash('demo123'),
            created_at=date.today() - timedelta(days=30)  # User created 30 days ago
        )
        db.session.add(demo_user)
        db.session.commit()
        
        print(f"Demo user created: username='demo', password='demo123'")
        
        # Create sample habits
        habits_data = [
            {'name': 'Wake up at 7AM', 'emoji': '⏰', 'category': 'Health'},
            {'name': 'No Snoozing', 'emoji': '🔔', 'category': 'Health'},
            {'name': 'Drink 3L Water', 'emoji': '💧', 'category': 'Health'},
            {'name': 'Gym Workout', 'emoji': '💪', 'category': 'Fitness'},
            {'name': 'Study 1 Hour', 'emoji': '📚', 'category': 'Study'},
            {'name': 'Meditation', 'emoji': '🧘', 'category': 'Health'},
        ]
        
        print("Creating sample habits...")
        habits = []
        for habit_data in habits_data:
            habit = Habit(
                id=uuid.uuid4(),
                user_id=demo_user.id,
                name=habit_data['name'],
                emoji=habit_data['emoji'],
                category=habit_data['category'],
                goal=30,
                created_at=date.today() - timedelta(days=30)
            )
            habits.append(habit)
            db.session.add(habit)
        
        db.session.commit()
        print(f"Created {len(habits)} sample habits")
        
        # Create some sample logs (completed and missed days)
        print("Creating sample habit logs...")
        today = date.today()
        start_date = today - timedelta(days=30)  # Last 30 days
        
        log_count = 0
        for habit in habits:
            current_date = start_date
            while current_date < today:
                # Randomly mark some days as completed (70% completion rate for demo)
                import random
                is_completed = random.random() < 0.7
                
                log = HabitLog(
                    id=uuid.uuid4(),
                    user_id=demo_user.id,
                    habit_id=habit.id,
                    date=current_date,
                    completed=is_completed,
                    created_at=current_date
                )
                db.session.add(log)
                log_count += 1
                current_date += timedelta(days=1)
        
        db.session.commit()
        print(f"Created {log_count} sample habit logs")
        print("\n[SUCCESS] Database seeded successfully!")
        print("\nDemo credentials:")
        print("  Username: demo")
        print("  Password: demo123")
        print("\nYou can now log in with these credentials to test the application.")

if __name__ == '__main__':
    seed_database()

