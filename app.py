from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
import os
import secrets
import uuid

app = Flask(__name__)

# Configuration - direct configuration (simplified for Vercel)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Database configuration - supports both SQLite (local) and PostgreSQL (production)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # PostgreSQL (production - Vercel)
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # SQLite (local development)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habit_tracker.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# UUID Type for SQLite compatibility
class GUID(TypeDecorator):
    """Platform-independent GUID type."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            # For SQLite, value comes as string, convert to UUID object
            if isinstance(value, str):
                return uuid.UUID(value)
            return value

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_id(self):
        """Return the id to satisfy Flask-Login's UserMixin"""
        return str(self.id)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

class Habit(db.Model):
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    emoji = db.Column(db.String(10), nullable=True)
    category = db.Column(db.String(50), nullable=True)
    goal = db.Column(db.Integer, default=30)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('habits', lazy=True))

class HabitLog(db.Model):
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('user.id'), nullable=False, index=True)
    habit_id = db.Column(GUID(), db.ForeignKey('habit.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    habit = db.relationship('Habit', backref=db.backref('logs', lazy=True))
    user = db.relationship('User', backref=db.backref('logs', lazy=True))
    
    __table_args__ = (db.UniqueConstraint('user_id', 'habit_id', 'date', name='unique_user_habit_date'),)

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(uuid.UUID(user_id))
    except (ValueError, TypeError):
        return None

# Database initialization removed from import time
# Tables will be created via /api/migrate endpoint or manually

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user, remember=True)
            session.permanent = True
            if request.is_json:
                return jsonify({'message': 'Login successful', 'user': {'id': str(user.id), 'username': user.username}})
            return redirect(url_for('index'))
        else:
            error_msg = 'Invalid username or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            return render_template('login.html', error=error_msg)
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '').strip()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        # Validation
        if not username or not email or not password:
            error = 'All fields are required'
            if request.is_json:
                return jsonify({'error': error}), 400
            return render_template('signup.html', error=error)
        
        if password != confirm_password:
            error = 'Passwords do not match'
            if request.is_json:
                return jsonify({'error': error}), 400
            return render_template('signup.html', error=error)
        
        if len(password) < 6:
            error = 'Password must be at least 6 characters long'
            if request.is_json:
                return jsonify({'error': error}), 400
            return render_template('signup.html', error=error)
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            error = 'Username already exists'
            if request.is_json:
                return jsonify({'error': error}), 400
            return render_template('signup.html', error=error)
        
        if User.query.filter_by(email=email).first():
            error = 'Email already registered'
            if request.is_json:
                return jsonify({'error': error}), 400
            return render_template('signup.html', error=error)
        
        # Create user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Create default habits for new user
        default_habits = [
            Habit(user_id=user.id, name="Wake up at 6AM", emoji="⏰", category="Productivity", goal=30),
            Habit(user_id=user.id, name="No Snoozing", emoji="🔕", category="Productivity", goal=30),
            Habit(user_id=user.id, name="Drink 3L Water", emoji="💧", category="Health", goal=30),
            Habit(user_id=user.id, name="Gym Workout", emoji="💪", category="Fitness", goal=20),
            Habit(user_id=user.id, name="Stretching", emoji="🧘", category="Fitness", goal=30),
            Habit(user_id=user.id, name="Read 10 Pages", emoji="📚", category="Study", goal=30),
            Habit(user_id=user.id, name="Meditation", emoji="🧘‍♀️", category="Health", goal=30),
            Habit(user_id=user.id, name="Study 1 Hour", emoji="🎓", category="Study", goal=25),
            Habit(user_id=user.id, name="Skincare Routine", emoji="✨", category="Health", goal=30),
            Habit(user_id=user.id, name="Limit Social Media", emoji="📱", category="Productivity", goal=30),
            Habit(user_id=user.id, name="No Alcohol", emoji="🚫", category="Health", goal=30),
            Habit(user_id=user.id, name="Track Expenses", emoji="💰", category="Money", goal=30),
        ]
        db.session.add_all(default_habits)
        db.session.commit()
        
        login_user(user, remember=True)
        session.permanent = True
        
        if request.is_json:
            return jsonify({'message': 'Account created successfully', 'user': {'id': str(user.id), 'username': user.username}}), 201
        return redirect(url_for('index'))
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/check-auth')
def check_auth():
    """Check if user is authenticated"""
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'user': {'id': str(current_user.id), 'username': current_user.username}})
    return jsonify({'authenticated': False}), 401

# Main App Routes
@app.route('/')
@login_required
def index():
    return render_template('index.html')

# API Routes - All require authentication
@app.route('/api/habits', methods=['GET'])
@login_required
def get_habits():
    habits = Habit.query.filter_by(user_id=current_user.id).order_by(Habit.created_at).all()
    return jsonify([{
        'id': str(h.id),
        'name': h.name,
        'emoji': h.emoji,
        'category': h.category,
        'goal': h.goal
    } for h in habits])

@app.route('/api/habits', methods=['POST'])
@login_required
def create_habit():
    data = request.json
    habit = Habit(
        user_id=current_user.id,
        name=data['name'],
        emoji=data.get('emoji', '✅'),
        category=data.get('category', 'Other'),
        goal=data.get('goal', 30)
    )
    db.session.add(habit)
    db.session.commit()
    return jsonify({'id': str(habit.id), 'message': 'Habit created'}), 201

@app.route('/api/habits/<habit_id>', methods=['DELETE'])
@login_required
def delete_habit(habit_id):
    try:
        habit_uuid = uuid.UUID(habit_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid habit ID'}), 400
    
    habit = Habit.query.filter_by(id=habit_uuid, user_id=current_user.id).first_or_404()
    HabitLog.query.filter_by(habit_id=habit_uuid, user_id=current_user.id).delete()
    db.session.delete(habit)
    db.session.commit()
    return jsonify({'message': 'Habit deleted'})

@app.route('/api/habits/<habit_id>', methods=['PUT'])
@login_required
def update_habit(habit_id):
    try:
        habit_uuid = uuid.UUID(habit_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid habit ID'}), 400
    
    habit = Habit.query.filter_by(id=habit_uuid, user_id=current_user.id).first_or_404()
    data = request.json
    habit.name = data.get('name', habit.name)
    habit.emoji = data.get('emoji', habit.emoji)
    habit.category = data.get('category', habit.category)
    habit.goal = data.get('goal', habit.goal)
    db.session.commit()
    return jsonify({'message': 'Habit updated'})

@app.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = HabitLog.query.filter_by(user_id=current_user.id)
    
    if start_date:
        query = query.filter(HabitLog.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(HabitLog.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    logs = query.all()
    return jsonify([{
        'id': str(l.id),
        'habit_id': str(l.habit_id),
        'date': l.date.isoformat(),
        'completed': l.completed
    } for l in logs])

@app.route('/api/logs', methods=['POST'])
@login_required
def toggle_log():
    data = request.json
    try:
        habit_id = uuid.UUID(data['habit_id'])
    except (ValueError, TypeError, KeyError):
        return jsonify({'error': 'Invalid habit ID'}), 400
    
    log_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    completed = data.get('completed', True)
    
    # Verify habit belongs to user
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    
    log = HabitLog.query.filter_by(
        user_id=current_user.id,
        habit_id=habit_id,
        date=log_date
    ).first()
    
    if log:
        log.completed = completed
    else:
        log = HabitLog(
            user_id=current_user.id,
            habit_id=habit_id,
            date=log_date,
            completed=completed
        )
        db.session.add(log)
    
    db.session.commit()
    return jsonify({'message': 'Log updated', 'id': str(log.id)})

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    today = date.today()
    current_month_start = date(today.year, today.month, 1)
    
    # Get all habits for current user with their completion stats
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    stats = []
    
    for habit in habits:
        completed = HabitLog.query.filter(
            HabitLog.user_id == current_user.id,
            HabitLog.habit_id == habit.id,
            HabitLog.date >= current_month_start,
            HabitLog.completed == True
        ).count()
        
        percentage = (completed / habit.goal * 100) if habit.goal > 0 else 0
        remaining = max(0, habit.goal - completed)
        
        stats.append({
            'habit_id': str(habit.id),
            'name': habit.name,
            'emoji': habit.emoji,
            'category': habit.category,
            'completed': completed,
            'goal': habit.goal,
            'remaining': remaining,
            'percentage': round(percentage, 1)
        })
    
    # Category summary
    category_stats = {}
    for stat in stats:
        cat = stat['category'] or 'Other'
        if cat not in category_stats:
            category_stats[cat] = {'completed': 0, 'goal': 0}
        category_stats[cat]['completed'] += stat['completed']
        category_stats[cat]['goal'] += stat['goal']
    
    category_list = [{
        'category': cat,
        'completed': data['completed'],
        'goal': data['goal'],
        'percentage': round((data['completed'] / data['goal'] * 100) if data['goal'] > 0 else 0, 1)
    } for cat, data in category_stats.items()]
    
    return jsonify({
        'habits': stats,
        'categories': category_list
    })

# Service Worker and Manifest are served automatically by Flask from static folder
# No need for explicit routes

@app.route('/api/daily-logs', methods=['GET'])
@login_required
def get_daily_logs():
    """Get all logs for a specific date range, organized by date"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not start_date or not end_date:
        # Default to current month
        today = date.today()
        start_date = date(today.year, today.month, 1)
        end_date = date(today.year, today.month + 1, 1) if today.month < 12 else date(today.year + 1, 1, 1)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    logs = HabitLog.query.filter(
        HabitLog.user_id == current_user.id,
        HabitLog.date >= start_date,
        HabitLog.date < end_date
    ).all()
    
    # Organize by date
    daily_logs = {}
    for log in logs:
        date_str = log.date.isoformat()
        if date_str not in daily_logs:
            daily_logs[date_str] = {}
        daily_logs[date_str][str(log.habit_id)] = log.completed
    
    return jsonify(daily_logs)

# Database migration endpoint (for initial setup)
@app.route('/api/migrate', methods=['POST', 'GET'])
def migrate_database():
    """Create database tables - run this once after deployment"""
    try:
        with app.app_context():
            db.create_all()
        return jsonify({
            'message': 'Database migrated successfully',
            'tables': ['User', 'Habit', 'HabitLog']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Only run development server if not in Vercel
if __name__ == '__main__' and not os.environ.get('VERCEL'):
    app.run(debug=True, host='0.0.0.0', port=5000)
