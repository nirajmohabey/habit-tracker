from flask import Flask, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from functools import wraps
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import os
import secrets
import uuid
import random
import atexit

app = Flask(__name__)

# Enable CORS for Angular frontend
# Get allowed origins from environment or use defaults
allowed_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:4200,http://localhost:3000,http://127.0.0.1:4200').split(',')
CORS(app, 
     supports_credentials=True, 
     origins=allowed_origins,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Configuration - direct configuration (simplified for Vercel)
# Generate SECRET_KEY if not provided (required for sessions)
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Generate a temporary key (will be different on each restart, but app won't crash)
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: SECRET_KEY not set in environment. Using temporary key.")
app.config['SECRET_KEY'] = SECRET_KEY

# Database configuration - supports both SQLite (local) and PostgreSQL (production)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # PostgreSQL (production - Vercel)
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    print("Database URL configured (PostgreSQL)")
else:
    # SQLite (local development)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habit_tracker.db'
    print("Database URL configured (SQLite - local dev)")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Email configuration (Flask-Mail)
# IMPORTANT: These are YOUR application's email service credentials, NOT user credentials!
# Your app uses ONE email service account to send emails TO all users.
# Users only provide their email address (where to send), not their email password.
# This is like configuring a mail server - similar to how GitHub, Facebook, etc. send emails.
# 
# For production, set these environment variables:
# MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD
# For development, emails will be printed to console
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')  # YOUR email service account
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')  # YOUR email service password
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@habittracker.com')
app.config['FRONTEND_URL'] = os.environ.get('FRONTEND_URL', 'http://localhost:4200')

mail = Mail(app)

# Session cookie configuration
# For production (HTTPS), use Secure=True and SameSite=None
# For localhost, use Secure=False and SameSite=Lax
is_production = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('VERCEL')
session_secure = os.environ.get('SESSION_COOKIE_SECURE', str(is_production)).lower() == 'true'
app.config['SESSION_COOKIE_SECURE'] = session_secure
app.config['SESSION_COOKIE_HTTPONLY'] = True
# SameSite=None requires Secure=True (HTTPS), so use Lax for localhost
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if session_secure else 'Lax'
app.config['SESSION_COOKIE_DOMAIN'] = None  # Allow cookies for localhost
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

# Custom decorator for API endpoints that returns JSON instead of redirecting
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

# Global error handler
@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all unhandled exceptions gracefully"""
    import traceback
    error_msg = str(e)
    traceback_str = traceback.format_exc()
    print(f"ERROR: {error_msg}")
    print(traceback_str)
    
    # Handle 404 errors for favicon
    if isinstance(e, Exception) and '404' in str(e):
        return '', 404
    
    return jsonify({
        'error': 'Internal server error',
        'message': error_msg if os.environ.get('FLASK_ENV') == 'development' else 'An error occurred'
    }), 500

# Handle 404 errors
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors (like favicon.ico)"""
    return '', 404

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
class OTPVerification(db.Model):
    """Store OTP codes for email verification"""
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.String(120), nullable=False, index=True)
    otp_code = db.Column(db.String(6), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

class PasswordResetToken(db.Model):
    """Store password reset tokens"""
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(GUID(), db.ForeignKey('user.id'), nullable=False, index=True)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('reset_tokens', lazy=True))
    
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        return not self.used and not self.is_expired()

class User(UserMixin, db.Model):
    id = db.Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Email notification preferences
    email_notifications_enabled = db.Column(db.Boolean, default=True)
    notification_time = db.Column(db.String(5), default='09:00')  # HH:MM format, default 9 AM
    notification_frequency = db.Column(db.String(20), default='daily')  # 'daily', 'weekly', or 'both'
    
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
        # Use db.session.get() instead of deprecated query.get()
        return db.session.get(User, uuid.UUID(user_id))
    except (ValueError, TypeError):
        return None

def create_default_habits(user_id):
    """Create default habits for a user - goals will be dynamic based on month"""
    # Get days in current month for default goal
    today = date.today()
    days_in_current_month = (date(today.year, today.month + 1, 1) - date(today.year, today.month, 1)).days if today.month < 12 else (date(today.year + 1, 1, 1) - date(today.year, today.month, 1)).days
    
    default_habits = [
        Habit(user_id=user_id, name="Wake up at 6AM", emoji="⏰", category="Productivity", goal=days_in_current_month),
        Habit(user_id=user_id, name="No Snoozing", emoji="🔕", category="Productivity", goal=days_in_current_month),
        Habit(user_id=user_id, name="Drink 3L Water", emoji="💧", category="Health", goal=days_in_current_month),
        Habit(user_id=user_id, name="Gym Workout", emoji="💪", category="Fitness", goal=max(20, int(days_in_current_month * 0.65))),  # ~65% of month
        Habit(user_id=user_id, name="Stretching", emoji="🧘", category="Fitness", goal=days_in_current_month),
        Habit(user_id=user_id, name="Read 10 Pages", emoji="📚", category="Study", goal=days_in_current_month),
        Habit(user_id=user_id, name="Meditation", emoji="🧘‍♀️", category="Health", goal=days_in_current_month),
        Habit(user_id=user_id, name="Study 1 Hour", emoji="🎓", category="Study", goal=max(25, int(days_in_current_month * 0.8))),  # ~80% of month
        Habit(user_id=user_id, name="Skincare Routine", emoji="✨", category="Health", goal=days_in_current_month),
        Habit(user_id=user_id, name="Limit Social Media", emoji="📱", category="Productivity", goal=days_in_current_month),
        Habit(user_id=user_id, name="No Alcohol", emoji="🚫", category="Health", goal=days_in_current_month),
        Habit(user_id=user_id, name="Track Expenses", emoji="💰", category="Money", goal=days_in_current_month),
    ]
    try:
        db.session.add_all(default_habits)
        db.session.commit()
        print(f"Successfully created {len(default_habits)} default habits for user {user_id}")
        return default_habits
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default habits: {e}")
        import traceback
        traceback.print_exc()
        raise

# Database initialization removed from import time
# Tables will be created via /api/migrate endpoint or manually

# Diagnostic endpoint for debugging
@app.route('/api/health')
def health_check():
    """Health check endpoint to diagnose deployment issues"""
    info = {
        'status': 'ok',
        'vercel': os.environ.get('VERCEL', 'false'),
        'has_database_url': bool(os.environ.get('DATABASE_URL')),
        'has_secret_key': bool(os.environ.get('SECRET_KEY')),
        'database_uri_set': bool(app.config.get('SQLALCHEMY_DATABASE_URI')),
        'database_uri_preview': app.config.get('SQLALCHEMY_DATABASE_URI', '')[:50] + '...' if app.config.get('SQLALCHEMY_DATABASE_URI') else 'not set',
    }
    try:
        # Try to connect to database
        with app.app_context():
            conn = db.engine.connect()
            conn.close()
            info['database_connection'] = 'ok'
    except Exception as e:
        info['database_connection'] = f'error: {str(e)}'
        info['status'] = 'error'
        info['error_details'] = str(e)
    return jsonify(info), 200

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if request.is_json:
            return jsonify({'message': 'Already authenticated', 'user': {'id': str(current_user.id), 'username': current_user.username, 'email': current_user.email}}), 200
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
                return jsonify({'message': 'Login successful', 'user': {'id': str(user.id), 'username': user.username, 'email': user.email}})
            return redirect(url_for('index'))
        else:
            error_msg = 'Invalid username or password'
            if request.is_json:
                return jsonify({'error': error_msg}), 401
            # Angular frontend handles login UI
            return jsonify({'error': error_msg}), 401
    
    # GET request - Angular handles the UI
    return jsonify({'message': 'Please use the Angular frontend for login'}), 200

def send_otp_email(email, otp_code, username):
    """Send OTP email to user"""
    try:
        subject = "Verify Your Email - Habit Tracker"
        body = f"""
Hello {username},

Thank you for signing up for Habit Tracker!

Your OTP verification code is: {otp_code}

This code will expire in 10 minutes.

If you didn't sign up for this account, please ignore this email.

Best regards,
Habit Tracker Team
"""
        html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #a855f7;">Verify Your Email</h2>
        <p>Hello {username},</p>
        <p>Thank you for signing up for Habit Tracker!</p>
        <div style="background: #f5f5f5; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
            <p style="font-size: 32px; font-weight: bold; color: #a855f7; margin: 0;">{otp_code}</p>
        </div>
        <p>This code will expire in <strong>10 minutes</strong>.</p>
        <p>If you didn't sign up for this account, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #666; font-size: 12px;">Best regards,<br>Habit Tracker Team</p>
    </div>
</body>
</html>
"""
        
        # Try to send email if mail is configured
        if app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'):
            msg = Message(subject=subject, recipients=[email], body=body, html=html)
            mail.send(msg)
            print(f"OTP email sent to {email}")
        else:
            # Fallback: print to console for development
            print(f"\n{'='*50}")
            print(f"OTP Email for {username} ({email})")
            print(f"OTP Code: {otp_code}")
            print(f"Valid for 10 minutes")
            print(f"{'='*50}\n")
    except Exception as e:
        print(f"Error sending email: {e}")
        print(f"\n{'='*50}")
        print(f"OTP Email for {username} ({email})")
        print(f"OTP Code: {otp_code}")
        print(f"Valid for 10 minutes")
        print(f"{'='*50}\n")

def get_user_habit_stats(user_id, days=7):
    """Get personalized habit statistics for a user"""
    today = date.today()
    start_date = today - timedelta(days=days-1)
    
    # Get all user habits
    habits = Habit.query.filter_by(user_id=user_id).all()
    
    # Get logs for the period
    logs = HabitLog.query.filter(
        HabitLog.user_id == user_id,
        HabitLog.date >= start_date,
        HabitLog.date <= today
    ).all()
    
    # Calculate stats per habit
    habit_stats = []
    for habit in habits:
        habit_logs = [log for log in logs if log.habit_id == habit.id]
        completed_count = sum(1 for log in habit_logs if log.completed)
        total_days = days
        completion_rate = (completed_count / total_days * 100) if total_days > 0 else 0
        
        # Calculate current streak
        current_streak = 0
        check_date = today
        while check_date >= start_date:
            day_log = next((log for log in habit_logs if log.date == check_date), None)
            if day_log and day_log.completed:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        habit_stats.append({
            'habit': habit,
            'completed_count': completed_count,
            'completion_rate': round(completion_rate, 1),
            'current_streak': current_streak,
            'total_days': total_days
        })
    
    # Overall stats
    total_habits = len(habits)
    total_completions = sum(stat['completed_count'] for stat in habit_stats)
    overall_completion_rate = (total_completions / (total_habits * days) * 100) if total_habits > 0 else 0
    
    return {
        'habits': habit_stats,
        'total_habits': total_habits,
        'overall_completion_rate': round(overall_completion_rate, 1),
        'total_completions': total_completions
    }

def send_daily_reminder_email(user):
    """Send personalized daily habit reminder email"""
    try:
        # Get today's habits that haven't been completed yet
        today = date.today()
        habits = Habit.query.filter_by(user_id=user.id).all()
        
        # Get today's logs
        today_logs = HabitLog.query.filter_by(
            user_id=user.id,
            date=today
        ).all()
        completed_habit_ids = {log.habit_id for log in today_logs if log.completed}
        
        # Find habits not yet completed today
        pending_habits = [h for h in habits if h.id not in completed_habit_ids]
        
        if not pending_habits:
            # All habits completed - send congratulatory message
            subject = f"🎉 Great job, {user.username}! You've completed all your habits today!"
            greeting = f"Amazing work, {user.username}! 🌟"
            message = "You've already completed all your habits for today. Keep up the fantastic momentum!"
            habit_list = ""
        else:
            subject = f"📋 Daily Reminder: {len(pending_habits)} habit{'s' if len(pending_habits) > 1 else ''} waiting for you!"
            greeting = f"Hello {user.username}! 👋"
            message = f"You have <strong>{len(pending_habits)}</strong> habit{'s' if len(pending_habits) > 1 else ''} to track today:"
            habit_list = "<ul style='list-style: none; padding: 0; margin: 20px 0;'>"
            for habit in pending_habits:
                habit_list += f"""
                <li style='padding: 10px; margin: 5px 0; background: #f5f5f5; border-radius: 5px;'>
                    <span style='font-size: 20px; margin-right: 10px;'>{habit.emoji or '✅'}</span>
                    <strong>{habit.name}</strong>
                    {f'<span style="color: #666; font-size: 12px;"> ({habit.category})</span>' if habit.category else ''}
                </li>
                """
            habit_list += "</ul>"
        
        # Get yesterday's completion rate for motivation
        yesterday = today - timedelta(days=1)
        yesterday_logs = HabitLog.query.filter_by(user_id=user.id, date=yesterday).all()
        yesterday_completed = sum(1 for log in yesterday_logs if log.completed)
        yesterday_total = len(habits)
        yesterday_rate = (yesterday_completed / yesterday_total * 100) if yesterday_total > 0 else 0
        
        html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #ffffff;">
        <div style="background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center; color: white;">
            <h1 style="margin: 0; font-size: 28px;">{greeting}</h1>
        </div>
        <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
            <p style="font-size: 16px; margin-bottom: 20px;">{message}</p>
            {habit_list}
            {f'<div style="background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #4caf50;"><strong>Yesterday:</strong> You completed {yesterday_completed}/{yesterday_total} habits ({round(yesterday_rate, 1)}%)! Keep it up! 💪</div>' if yesterday_total > 0 else ''}
            <div style="text-align: center; margin: 30px 0;">
                <a href="{app.config['FRONTEND_URL']}/tracker" style="background: #a855f7; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">Track Your Habits →</a>
            </div>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px; text-align: center;">You're receiving this because email notifications are enabled in your settings.</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Build habit list for plain text body
        habit_list_text = ""
        if pending_habits:
            newline = '\n'
            habit_list_text = newline.join([f"- {h.emoji or '✅'} {h.name}" for h in pending_habits])
        else:
            habit_list_text = "All habits completed for today!"
        
        body = f"""
{greeting}

{message.replace('<strong>', '').replace('</strong>', '')}

{habit_list_text}

Track your habits: {app.config['FRONTEND_URL']}/tracker
"""
        
        if app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'):
            msg = Message(subject=subject, recipients=[user.email], body=body, html=html)
            mail.send(msg)
            print(f"Daily reminder email sent to {user.email}")
        else:
            print(f"\n{'='*50}")
            print(f"Daily Reminder Email for {user.username} ({user.email})")
            print(f"Subject: {subject}")
            print(f"{'='*50}\n")
    except Exception as e:
        print(f"Error sending daily reminder email to {user.email}: {e}")
        import traceback
        traceback.print_exc()

def send_weekly_summary_email(user):
    """Send personalized weekly progress summary email"""
    try:
        stats = get_user_habit_stats(user.id, days=7)
        today = date.today()
        week_start = today - timedelta(days=6)
        
        subject = f"📊 Your Weekly Habit Summary - {stats['overall_completion_rate']}% Complete!"
        greeting = f"Hello {user.username}! 👋"
        
        # Build habit progress list
        habit_progress = ""
        for stat in stats['habits']:
            habit = stat['habit']
            emoji = habit.emoji or '✅'
            completion_bar_width = min(stat['completion_rate'], 100)
            habit_progress += f"""
            <div style="margin: 15px 0; padding: 15px; background: #f9f9f9; border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div>
                        <span style="font-size: 20px; margin-right: 10px;">{emoji}</span>
                        <strong>{habit.name}</strong>
                    </div>
                    <div style="font-weight: bold; color: #a855f7;">{stat['completion_rate']}%</div>
                </div>
                <div style="background: #e0e0e0; height: 8px; border-radius: 4px; overflow: hidden;">
                    <div style="background: #a855f7; height: 100%; width: {completion_bar_width}%; transition: width 0.3s;"></div>
                </div>
                <div style="margin-top: 8px; font-size: 12px; color: #666;">
                    {stat['completed_count']}/{stat['total_days']} days completed
                    {f" • 🔥 {stat['current_streak']} day streak!" if stat['current_streak'] > 0 else ""}
                </div>
            </div>
            """
        
        # Motivational message based on performance
        if stats['overall_completion_rate'] >= 80:
            motivation = "🎉 Outstanding! You're crushing your goals! Keep up this amazing momentum!"
        elif stats['overall_completion_rate'] >= 60:
            motivation = "💪 Great progress! You're doing well. A few more days and you'll be at 100%!"
        elif stats['overall_completion_rate'] >= 40:
            motivation = "📈 Good start! Every day counts. You're building consistency!"
        else:
            motivation = "🌱 Every journey begins with a single step. You've got this! Small progress is still progress."
        
        html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #ffffff;">
        <div style="background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%); padding: 30px; border-radius: 10px 10px 0 0; text-align: center; color: white;">
            <h1 style="margin: 0; font-size: 28px;">{greeting}</h1>
            <p style="margin: 10px 0 0 0; font-size: 18px;">Here's your weekly progress summary!</p>
        </div>
        <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <div style="font-size: 48px; font-weight: bold; color: #a855f7; margin-bottom: 10px;">{stats['overall_completion_rate']}%</div>
                <div style="color: #666; margin-bottom: 15px;">Overall Completion Rate</div>
                <div style="font-size: 14px; color: #999;">{stats['total_completions']} habit completions this week</div>
            </div>
            <div style="margin: 20px 0;">
                <h2 style="color: #333; font-size: 20px; margin-bottom: 15px;">Your Habits Progress:</h2>
                {habit_progress}
            </div>
            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <p style="margin: 0; font-size: 16px;">{motivation}</p>
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{app.config['FRONTEND_URL']}/dashboard" style="background: #a855f7; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">View Full Dashboard →</a>
            </div>
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #666; font-size: 12px; text-align: center;">Week of {week_start.strftime('%B %d')} - {today.strftime('%B %d, %Y')}</p>
        </div>
    </div>
</body>
</html>
"""
        
        body = f"""
{greeting}

Here's your weekly habit summary:

Overall Completion: {stats['overall_completion_rate']}%
Total Completions: {stats['total_completions']}

Your Habits:
{chr(10).join([f"- {s['habit'].emoji or '✅'} {s['habit'].name}: {s['completion_rate']}% ({s['completed_count']}/{s['total_days']} days)" for s in stats['habits']])}

{motivation}

View your dashboard: {app.config['FRONTEND_URL']}/dashboard
"""
        
        if app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'):
            msg = Message(subject=subject, recipients=[user.email], body=body, html=html)
            mail.send(msg)
            print(f"Weekly summary email sent to {user.email}")
        else:
            print(f"\n{'='*50}")
            print(f"Weekly Summary Email for {user.username} ({user.email})")
            print(f"Subject: {subject}")
            print(f"Overall: {stats['overall_completion_rate']}%")
            print(f"{'='*50}\n")
    except Exception as e:
        print(f"Error sending weekly summary email to {user.email}: {e}")
        import traceback
        traceback.print_exc()

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        if request.is_json:
            return jsonify({'message': 'Already authenticated', 'user': {'id': str(current_user.id), 'username': current_user.username, 'email': current_user.email}}), 200
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            username = data.get('username', '').strip()
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            confirm_password = data.get('confirm_password', '')
            
            # Validation
            if not username or not email or not password:
                error = 'All fields are required'
                return jsonify({'error': error}), 400
            
            if password != confirm_password:
                error = 'Passwords do not match'
                return jsonify({'error': error}), 400
            
            if len(password) < 6:
                error = 'Password must be at least 6 characters long'
                return jsonify({'error': error}), 400
            
            # Check if user exists
            if User.query.filter_by(username=username).first():
                error = 'Username already exists'
                return jsonify({'error': error}), 400
            
            if User.query.filter_by(email=email).first():
                error = 'Email already registered'
                return jsonify({'error': error}), 400
                
            # If email is provided, require OTP verification
            if email:
                # Generate 6-digit OTP
                otp_code = str(random.randint(100000, 999999))
                
                # Hash password before storing in OTP table
                password_hash = generate_password_hash(password)
                
                # Delete any existing OTP for this email
                try:
                    OTPVerification.query.filter_by(email=email, verified=False).delete()
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(f"Error deleting old OTP: {e}")
                
                # Create OTP record (expires in 10 minutes)
                otp_record = OTPVerification(
                    email=email,
                    otp_code=otp_code,
                    username=username,
                    password_hash=password_hash,
                    expires_at=datetime.utcnow() + timedelta(minutes=10)
                )
                db.session.add(otp_record)
                db.session.commit()
                
                # Send OTP email (for now, just print to console - can be extended with actual email service)
                send_otp_email(email, otp_code, username)
                
                return jsonify({
                    'message': 'OTP sent to your email. Please verify to complete signup.',
                    'email': email,
                    'requires_verification': True
                }), 200
            else:
                # No email provided - allow direct signup (though current form requires email)
                # Create user
                user = User(username=username, email=email or f"{username}@temp.local")
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                
                # Create default habits for new user (in background to speed up response)
                try:
                    create_default_habits(user.id)
                except Exception as e:
                    print(f"Error creating default habits: {e}")
                    # Don't fail signup if habits creation fails
                
                login_user(user, remember=True)
                session.permanent = True
                
                return jsonify({'message': 'Account created successfully', 'user': {'id': str(user.id), 'username': user.username, 'email': user.email}}), 201
        except Exception as e:
            db.session.rollback()
            print(f"Error in signup: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Internal server error. Please try again.'}), 500
    
    # GET request - Angular handles the UI
    return jsonify({'message': 'Please use the Angular frontend for signup'}), 200

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and create user account"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            email = data.get('email', '').strip().lower()
            otp_code = data.get('otp', '').strip()
            
            if not email or not otp_code:
                return jsonify({'error': 'Email and OTP code are required'}), 400
            
            # Find OTP record
            otp_record = OTPVerification.query.filter_by(
                email=email,
                otp_code=otp_code,
                verified=False
            ).first()
            
            if not otp_record:
                return jsonify({'error': 'Invalid or expired OTP code'}), 400
            
            if otp_record.is_expired():
                db.session.delete(otp_record)
                db.session.commit()
                return jsonify({'error': 'OTP code has expired. Please sign up again.'}), 400
            
            # Check if user already exists (race condition check)
            if User.query.filter_by(username=otp_record.username).first():
                db.session.delete(otp_record)
                db.session.commit()
                return jsonify({'error': 'Username already exists'}), 400
            
            if User.query.filter_by(email=email).first():
                db.session.delete(otp_record)
                db.session.commit()
                return jsonify({'error': 'Email already registered'}), 400
            
            # Create user
            user = User(username=otp_record.username, email=email)
            user.password_hash = otp_record.password_hash  # Use pre-hashed password
            db.session.add(user)
            
            # Mark OTP as verified
            otp_record.verified = True
            db.session.commit()
            
            # Create default habits for new user (in background to speed up response)
            try:
                create_default_habits(user.id)
            except Exception as e:
                print(f"Error creating default habits: {e}")
                # Don't fail signup if habits creation fails
            
            # Login user
            login_user(user, remember=True)
            session.permanent = True
            
            # Clean up verified OTP
            db.session.delete(otp_record)
            db.session.commit()
            
            return jsonify({
                'message': 'Account created and verified successfully',
                'user': {'id': str(user.id), 'username': user.username, 'email': user.email}
            }), 201
        except Exception as e:
            db.session.rollback()
            print(f"Error in verify_otp: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Internal server error. Please try again.'}), 500
    
    return jsonify({'error': 'Invalid request'}), 400

def send_password_reset_email(email, reset_token, username):
    """Send password reset email to user"""
    try:
        frontend_url = app.config.get('FRONTEND_URL', 'http://localhost:4200')
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        subject = "Reset Your Password - Habit Tracker"
        body = f"""
Hello {username},

You requested to reset your password for your Habit Tracker account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request a password reset, please ignore this email. Your password will remain unchanged.

Best regards,
Habit Tracker Team
"""
        html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #a855f7;">Reset Your Password</h2>
        <p>Hello {username},</p>
        <p>You requested to reset your password for your Habit Tracker account.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" style="background: #a855f7; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold;">Reset Password</a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #666; font-size: 12px;">{reset_link}</p>
        <p>This link will expire in <strong>1 hour</strong>.</p>
        <p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #666; font-size: 12px;">Best regards,<br>Habit Tracker Team</p>
    </div>
</body>
</html>
"""
        
        # Try to send email if mail is configured
        if app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'):
            msg = Message(subject=subject, recipients=[email], body=body, html=html)
            mail.send(msg)
            print(f"Password reset email sent to {email}")
        else:
            # Fallback: print to console for development
            print(f"\n{'='*50}")
            print(f"Password Reset Email for {username} ({email})")
            print(f"Reset Link: {reset_link}")
            print(f"Token: {reset_token}")
            print(f"Valid for 1 hour")
            print(f"{'='*50}\n")
    except Exception as e:
        # Fallback to console if email fails
        print(f"Error sending email: {e}")
        print(f"\n{'='*50}")
        print(f"Password Reset Email for {username} ({email})")
        frontend_url = app.config.get('FRONTEND_URL', 'http://localhost:4200')
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        print(f"Reset Link: {reset_link}")
        print(f"Token: {reset_token}")
        print(f"Valid for 1 hour")
        print(f"{'='*50}\n")

@app.route('/forgot-password', methods=['POST', 'OPTIONS'])
def forgot_password():
    """Handle password reset request - sends email with reset link"""
    if request.method == 'OPTIONS':
        # Handle preflight request
        return jsonify({}), 200
    
    try:
        data = request.get_json() if request.is_json else request.form
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email', '').strip() if data.get('email') else ''
        username = data.get('username', '').strip() if data.get('username') else ''
        
        if not email and not username:
            return jsonify({'error': 'Email or username is required'}), 400
        
        user = None
        if email:
            user = User.query.filter_by(email=email).first()
        elif username:
            user = User.query.filter_by(username=username).first()
        
        # Always return success to prevent user enumeration
        if user:
            # Generate secure reset token
            reset_token = secrets.token_urlsafe(32)
            
            # Delete any existing unused tokens for this user
            PasswordResetToken.query.filter_by(user_id=user.id, used=False).delete()
            
            # Create new reset token (expires in 1 hour)
            reset_record = PasswordResetToken(
                user_id=user.id,
                token=reset_token,
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(reset_record)
            db.session.commit()
            
            # Send password reset email
            send_password_reset_email(user.email, reset_token, user.username)
        
        # Always return success message (security best practice)
        return jsonify({
            'message': 'If an account exists with that email or username, you will receive password reset instructions.'
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error in forgot_password: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An error occurred processing your request'}), 500

@app.route('/api/verify-reset-token', methods=['POST'])
def verify_reset_token():
    """Verify if a password reset token is valid"""
    try:
        data = request.get_json() if request.is_json else request.form
        token = data.get('token', '').strip()
        
        if not token:
            return jsonify({'error': 'Token is required'}), 400
        
        reset_record = PasswordResetToken.query.filter_by(token=token, used=False).first()
        
        if not reset_record:
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        if reset_record.is_expired():
            return jsonify({'error': 'Reset token has expired'}), 400
        
        return jsonify({
            'valid': True,
            'message': 'Token is valid'
        }), 200
    except Exception as e:
        print(f"Error in verify_reset_token: {str(e)}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token"""
    try:
        data = request.get_json() if request.is_json else request.form
        token = data.get('token', '').strip()
        new_password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        
        if not token or not new_password:
            return jsonify({'error': 'Token and password are required'}), 400
        
        if new_password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        # Find reset token
        reset_record = PasswordResetToken.query.filter_by(token=token, used=False).first()
        
        if not reset_record:
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        if reset_record.is_expired():
            db.session.delete(reset_record)
            db.session.commit()
            return jsonify({'error': 'Reset token has expired. Please request a new one.'}), 400
        
        # Get user and update password
        user = User.query.get(reset_record.user_id)
        if not user:
            db.session.delete(reset_record)
            db.session.commit()
            return jsonify({'error': 'User not found'}), 404
        
        # Update password
        user.set_password(new_password)
        
        # Mark token as used
        reset_record.used = True
        
        db.session.commit()
        
        return jsonify({
            'message': 'Password reset successfully. You can now log in with your new password.'
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error in reset_password: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An error occurred. Please try again.'}), 500

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if not current_user.is_authenticated:
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'message': 'Not logged in'}), 200
        return redirect(url_for('login'))
    
    logout_user()
    if request.is_json or request.headers.get('Content-Type') == 'application/json':
        return jsonify({'message': 'Logged out successfully'}), 200
    return redirect(url_for('login'))

@app.route('/api/check-auth')
def check_auth():
    """Check if user is authenticated"""
    if not current_user.is_authenticated:
        return jsonify({'authenticated': False}), 200
    
    # Get user's signup date - ensure we always have a date
    if current_user.created_at:
        signup_date = current_user.created_at.date()
    else:
        # If created_at is None (shouldn't happen, but handle it), use a reasonable default
        # For existing users without created_at, we can't know the exact date, so use today
        # In production, you might want to set created_at for existing users via migration
        signup_date = date.today()
        print(f"Warning: User {current_user.id} has no created_at, using today's date")
    
    # Get first log date (if any)
    first_log = HabitLog.query.filter_by(user_id=current_user.id).order_by(HabitLog.date.asc()).first()
    first_activity_date = first_log.date if first_log else signup_date
    
    # Start date is the earlier of signup or first activity, but not before current month start
    today = date.today()
    current_month_start = date(today.year, today.month, 1)
    start_date = min(signup_date, first_activity_date)
    
    # If start date is before current month, use current month start
    if start_date < current_month_start:
        start_date = current_month_start
    
    # Format created_at for response - use signup_date as fallback
    if current_user.created_at:
        created_at_iso = current_user.created_at.isoformat()
    else:
        # Fallback to signup_date if created_at is not set (for old users)
        # Convert signup_date (date object) to datetime for consistency
        created_at_iso = datetime.combine(signup_date, datetime.min.time()).isoformat()
        print(f"Warning: User {current_user.id} has no created_at, using signup_date: {created_at_iso}")
    
    # Debug log to ensure date is being returned
    print(f"Debug: Returning created_at_iso: {created_at_iso} for user {current_user.id}")
    
    return jsonify({
        'authenticated': True,
        'user': {
            'id': str(current_user.id),
            'username': current_user.username,
            'email': current_user.email,
            'created_at': created_at_iso
        },
        'start_date': start_date.isoformat(),
        'signup_date': signup_date.isoformat(),
        'created_at': created_at_iso  # Also include at root level for convenience
    }), 200

# Main App Routes
@app.route('/')
def index():
    # Angular frontend handles the UI - return JSON for API calls
    if request.is_json:
        if not current_user.is_authenticated:
            return jsonify({'message': 'API is running', 'authenticated': False}), 200
    # Check if user has any habits, if not, create default ones
    habit_count = Habit.query.filter_by(user_id=current_user.id).count()
    if habit_count == 0:
        create_default_habits(current_user.id)
        return jsonify({'message': 'API is running', 'authenticated': True})
    # For non-JSON requests, return a simple message
    return jsonify({'message': 'Please use the Angular frontend', 'api_url': '/api'}), 200

# API Routes - All require authentication
@app.route('/api/habits', methods=['GET'])
@api_login_required
def get_habits():
    # Check if user has any habits, if not, create default ones
    habit_count = Habit.query.filter_by(user_id=current_user.id).count()
    if habit_count == 0:
        try:
            create_default_habits(current_user.id)
            print(f"Created default habits for user {current_user.id}")
        except Exception as e:
            print(f"Error creating default habits: {e}")
            import traceback
            traceback.print_exc()
    
    habits = Habit.query.filter_by(user_id=current_user.id).order_by(Habit.created_at).all()
    print(f"Returning {len(habits)} habits for user {current_user.id}")
    return jsonify([{
        'id': str(h.id),
        'name': h.name,
        'emoji': h.emoji,
        'category': h.category,
        'goal': h.goal
    } for h in habits])

@app.route('/api/habits', methods=['POST'])
@api_login_required
def create_habit():
    data = request.json
    # Calculate days in current month for default goal
    today = date.today()
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)
    days_in_month = (next_month_start - date(today.year, today.month, 1)).days
    
    habit = Habit(
        user_id=current_user.id,
        name=data['name'],
        emoji=data.get('emoji', '✅'),
        category=data.get('category', 'Other'),
        goal=data.get('goal', days_in_month)  # Default to days in current month
    )
    db.session.add(habit)
    db.session.commit()
    return jsonify({'id': str(habit.id), 'message': 'Habit created'}), 201

@app.route('/api/habits/<habit_id>', methods=['DELETE'])
@api_login_required
def delete_habit(habit_id):
    try:
        habit_uuid = uuid.UUID(habit_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid habit ID'}), 400
    
    habit = Habit.query.filter_by(id=habit_uuid, user_id=current_user.id).first_or_404()
    HabitLog.query.filter_by(habit_id=habit_uuid, user_id=current_user.id).delete()
    db.session.delete(habit)
    db.session.commit()
    return jsonify({'message': 'Habit deleted'}), 200

@app.route('/api/habits/<habit_id>', methods=['PUT'])
@api_login_required
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
@api_login_required
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
@api_login_required
def toggle_log():
    data = request.json
    try:
        habit_id = uuid.UUID(data['habit_id'])
    except (ValueError, TypeError, KeyError):
        return jsonify({'error': 'Invalid habit ID'}), 400
    
    log_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    completed = data.get('completed', True)
    today = date.today()
    
    # Prevent marking future days as missed
    if log_date > today and not completed:
        # Delete any existing log for future days marked as missed
        log = HabitLog.query.filter_by(
            user_id=current_user.id,
            habit_id=habit_id,
            date=log_date
        ).first()
        if log:
            db.session.delete(log)
            db.session.commit()
        return jsonify({'message': 'Future days cannot be marked as missed'}), 200
    
    # Prevent changing past days that are already marked as missed
    if log_date < today:
        existing_log = HabitLog.query.filter_by(
            user_id=current_user.id,
            habit_id=habit_id,
            date=log_date
        ).first()
        # If past day is marked as missed (completed=False), lock it - cannot be changed
        if existing_log and not existing_log.completed:
            return jsonify({'error': 'Past days marked as missed cannot be changed'}), 403
        # If past day is completed, allow changing (user might want to uncheck it)
        # But if trying to mark as missed, prevent it (past days should only be completed or auto-marked as missed)
        if not existing_log and not completed:
            # Past day with no log trying to be marked as missed - auto-mark it instead
            # This shouldn't happen from UI, but handle it gracefully
            pass
    
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
@api_login_required
def get_stats():
    today = date.today()
    current_month_start = date(today.year, today.month, 1)
    
    # Calculate days in current month for dynamic goals
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)
    days_in_month = (next_month_start - current_month_start).days
    
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
        
        # Use dynamic goal based on days in current month
        dynamic_goal = days_in_month
        percentage = (completed / dynamic_goal * 100) if dynamic_goal > 0 else 0
        remaining = max(0, dynamic_goal - completed)
        
        # Calculate streak
        start_date_streak = date.today() - timedelta(days=60)
        logs_streak = HabitLog.query.filter(
            HabitLog.user_id == current_user.id,
            HabitLog.habit_id == habit.id,
            HabitLog.date >= start_date_streak
        ).order_by(HabitLog.date.desc()).all()
        
        completed_dates = {log.date for log in logs_streak if log.completed}
        current_streak = 0
        check_date = today
        while check_date >= start_date_streak:
            if check_date in completed_dates:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        stats.append({
            'habit_id': str(habit.id),
            'name': habit.name,
            'emoji': habit.emoji,
            'category': habit.category,
            'completed': completed,
            'goal': dynamic_goal,  # Use dynamic goal
            'remaining': remaining,
            'percentage': round(percentage, 1),
            'streak': current_streak
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
@api_login_required
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

# Auto-mark missed days endpoint
@app.route('/api/auto-mark-missed', methods=['POST'])
@api_login_required
def auto_mark_missed_days():
    """Automatically mark past days as missed (❌) if not completed"""
    try:
        today = date.today()
        habits = Habit.query.filter_by(user_id=current_user.id).all()
        
        # Get optional month/year from request to mark specific month
        data = request.get_json() or {}
        target_year = data.get('year', today.year)
        target_month = data.get('month', today.month)
        
        # Get user's start date (signup date or first activity)
        signup_date = current_user.created_at.date() if current_user.created_at else today
        first_log = HabitLog.query.filter_by(user_id=current_user.id).order_by(HabitLog.date.asc()).first()
        first_activity_date = first_log.date if first_log else signup_date
        start_date = min(signup_date, first_activity_date)
        
        # Get target month start and end
        if target_month == 12:
            month_end = date(target_year + 1, 1, 1)
        else:
            month_end = date(target_year, target_month + 1, 1)
        month_start = date(target_year, target_month, 1)
        
        # Only process if the target month is in the past or current (not future)
        # Check if month_start is in the future (not just month_end)
        if month_start > today:
            # Future month - don't mark anything
            return jsonify({
                'message': 'Future months cannot be auto-marked',
                'marked_count': 0
            }), 200
        
        # Use the later of start_date or month_start
        effective_start = max(start_date, month_start)
        
        # Clean up any incorrect future day missed logs
        future_logs = HabitLog.query.filter(
            HabitLog.user_id == current_user.id,
            HabitLog.date > today,
            HabitLog.completed == False
        ).all()
        for log in future_logs:
            db.session.delete(log)
        
        marked_count = 0
        for habit in habits:
            # Get habit creation date (if habit was created this month, start from that date)
            habit_created = habit.created_at.date() if habit.created_at else today
            habit_start = max(effective_start, habit_created)
            
            # Only mark days from habit creation onwards, up to end of target month or today
            current_date = max(habit_start, month_start)
            end_date = min(month_end, today)
            
            while current_date < end_date:
                # Only process the target month
                if current_date.year == target_year and current_date.month == target_month:
                    # Check if log exists
                    log = HabitLog.query.filter_by(
                        user_id=current_user.id,
                        habit_id=habit.id,
                        date=current_date
                    ).first()
                    
                    # If no log exists or log is not completed, mark as missed
                    if not log or not log.completed:
                        if log:
                            # Update existing log to missed
                            log.completed = False
                        else:
                            # Create new missed log
                            log = HabitLog(
                                user_id=current_user.id,
                                habit_id=habit.id,
                                date=current_date,
                                completed=False
                            )
                            db.session.add(log)
                        marked_count += 1
                        print(f'  Marking {current_date} as missed for habit {habit.name}')
                
                current_date += timedelta(days=1)
        
        db.session.commit()
        print(f'Auto-marked {marked_count} missed days for month {target_year}-{target_month}')
        return jsonify({
            'message': f'Marked {marked_count} missed days',
            'marked_count': marked_count
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f'Error in auto-mark: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Weekly scorecard endpoint
@app.route('/api/weekly-scorecard', methods=['GET'])
@api_login_required
def get_weekly_scorecard():
    """Get weekly breakdown for current month"""
    today = date.today()
    month_start = date(today.year, today.month, 1)
    days_in_month = (date(today.year, today.month + 1, 1) - month_start).days if today.month < 12 else (date(today.year + 1, 1, 1) - month_start).days
    
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # Define week ranges
    weeks = []
    week_ranges = [[1, 7], [8, 14], [15, 21], [22, 28], [29, days_in_month]]
    
    for week_num, (start_day, end_day) in enumerate(week_ranges, 1):
        end_day = min(end_day, days_in_month)
        if start_day > days_in_month:
            break
            
        week_data = {
            'week': week_num,
            'start_day': start_day,
            'end_day': end_day,
            'habits': []
        }
        
        for habit in habits:
            completed = HabitLog.query.filter(
                HabitLog.user_id == current_user.id,
                HabitLog.habit_id == habit.id,
                HabitLog.date >= date(today.year, today.month, start_day),
                HabitLog.date <= date(today.year, today.month, end_day),
                HabitLog.completed == True
            ).count()
            
            week_data['habits'].append({
                'habit_id': str(habit.id),
                'name': habit.name,
                'emoji': habit.emoji,
                'completed': completed,
                'total_days': end_day - start_day + 1
            })
        
        weeks.append(week_data)
    
    # Calculate total
    total_completed = HabitLog.query.filter(
        HabitLog.user_id == current_user.id,
        HabitLog.date >= month_start,
        HabitLog.date <= date(today.year, today.month, days_in_month),
        HabitLog.completed == True
    ).count()
    
    return jsonify({
        'weeks': weeks,
        'total_completed': total_completed,
        'month': today.month,
        'year': today.year
    })

# Streak calculation endpoint
@app.route('/api/streaks', methods=['GET'])
@api_login_required
def get_streaks():
    """Calculate current streaks for all habits"""
    today = date.today()
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    streaks = []
    for habit in habits:
        # Get logs for last 60 days to calculate streak
        start_date = date.today() - timedelta(days=60)
        logs = HabitLog.query.filter(
            HabitLog.user_id == current_user.id,
            HabitLog.habit_id == habit.id,
            HabitLog.date >= start_date
        ).order_by(HabitLog.date.desc()).all()
        
        # Create a set of completed dates
        completed_dates = {log.date for log in logs if log.completed}
        
        # Calculate current streak (backwards from today)
        current_streak = 0
        check_date = today
        while check_date >= start_date:
            if check_date in completed_dates:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        # Calculate longest streak in last 60 days
        longest_streak = 0
        temp_streak = 0
        check_date = start_date
        while check_date <= today:
            if check_date in completed_dates:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 0
            check_date += timedelta(days=1)
        
        streaks.append({
            'habit_id': str(habit.id),
            'name': habit.name,
            'emoji': habit.emoji,
            'current_streak': current_streak,
            'longest_streak': longest_streak
        })
    
    return jsonify({'streaks': streaks})

# Badges endpoint
@app.route('/api/badges', methods=['GET'])
@api_login_required
def get_badges():
    """Calculate badges based on completion rates and streaks"""
    today = date.today()
    month_start = date(today.year, today.month, 1)
    
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    total_completed = 0
    total_goal = 0
    
    for habit in habits:
        completed = HabitLog.query.filter(
            HabitLog.user_id == current_user.id,
            HabitLog.habit_id == habit.id,
            HabitLog.date >= month_start,
            HabitLog.completed == True
        ).count()
        total_completed += completed
        total_goal += habit.goal
    
    badges = []
    if total_goal > 0:
        pct = total_completed / total_goal
        
        if pct >= 0.6:
            badges.append({'name': '🥉 Bronze', 'description': '60% completion rate'})
        if pct >= 0.75:
            badges.append({'name': '🥈 Silver', 'description': '75% completion rate'})
        if pct >= 0.9:
            badges.append({'name': '🥇 Gold', 'description': '90% completion rate'})
    
    # Check for streak badges - calculate directly
    max_streak = 0
    for habit in habits:
        start_date_streak = date.today() - timedelta(days=60)
        logs_streak = HabitLog.query.filter(
            HabitLog.user_id == current_user.id,
            HabitLog.habit_id == habit.id,
            HabitLog.date >= start_date_streak
        ).order_by(HabitLog.date.desc()).all()
        
        completed_dates = {log.date for log in logs_streak if log.completed}
        current_streak = 0
        check_date = today
        while check_date >= start_date_streak:
            if check_date in completed_dates:
                current_streak += 1
                check_date -= timedelta(days=1)
            else:
                break
        
        max_streak = max(max_streak, current_streak)
    if max_streak >= 7:
        badges.append({'name': '🔥 7-day streak', 'description': 'Maintained a 7-day streak'})
    if max_streak >= 21:
        badges.append({'name': '🔥🔥 21-day streak', 'description': 'Maintained a 21-day streak'})
    if max_streak >= 30:
        badges.append({'name': '🔥🔥🔥 30-day streak', 'description': 'Maintained a 30-day streak'})
    
    return jsonify({
        'badges': badges,
        'total_completed': total_completed,
        'total_goal': total_goal,
        'percentage': round((total_completed / total_goal * 100) if total_goal > 0 else 0, 1)
    })

# AI Insights endpoint
@app.route('/api/insights', methods=['GET'])
@api_login_required
def get_insights():
    """Generate AI insights about habit performance"""
    today = date.today()
    month_start = date(today.year, today.month, 1)
    
    # Calculate days in current month for dynamic goals
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)
    days_in_month = (next_month_start - month_start).days
    
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    if not habits:
        return jsonify({
            'insights': [],
            'message': 'No habits to analyze'
        })
    
    habit_stats = []
    for habit in habits:
        completed = HabitLog.query.filter(
            HabitLog.user_id == current_user.id,
            HabitLog.habit_id == habit.id,
            HabitLog.date >= month_start,
            HabitLog.completed == True
        ).count()
        
        habit_stats.append({
            'habit_id': str(habit.id),
            'name': habit.name,
            'emoji': habit.emoji,
            'completed': completed,
            'goal': days_in_month,  # Use dynamic goal
            'percentage': (completed / days_in_month * 100) if days_in_month > 0 else 0
        })
    
    # Calculate overall completion rate
    total_completed = sum(s['completed'] for s in habit_stats)
    total_goal = sum(s['goal'] for s in habit_stats)
    overall_pct = (total_completed / total_goal * 100) if total_goal > 0 else 0
    
    insights = []
    
    # If no completions at all
    if total_completed == 0:
        insights.append({
                'type': 'info',
            'icon': '🚀',
            'message': f"You have {len(habits)} habit{'s' if len(habits) > 1 else ''} set up. Start tracking today to build your streak!"
        })
        return jsonify({'insights': insights})
    
    # Calculate completion percentages for each habit
    for stat in habit_stats:
        stat['percentage'] = (stat['completed'] / stat['goal'] * 100) if stat['goal'] > 0 else 0
    
    # Sort by completion percentage
    sorted_habits = sorted(habit_stats, key=lambda x: (x['percentage'], x['completed']), reverse=True)
    best_habit = sorted_habits[0]
    worst_habit = sorted_habits[-1]
    habits_with_progress = [s for s in habit_stats if s['completed'] > 0]
    
    # Get today's activity for motivational insights
    today = date.today()
    yesterday = today - timedelta(days=1)
    today_logs = HabitLog.query.filter_by(user_id=current_user.id, date=today, completed=True).count()
    yesterday_logs = HabitLog.query.filter_by(user_id=current_user.id, date=yesterday, completed=True).count()
    
    # Get habits not completed today for recommendations
    today_habit_logs = HabitLog.query.filter_by(user_id=current_user.id, date=today).all()
    completed_today_habit_ids = {str(log.habit_id) for log in today_habit_logs if log.completed}
    pending_today_habits = [h for h in habits if str(h.id) not in completed_today_habit_ids]
    
    # PRIORITY 1: Show positive achievements FIRST (most motivational)
    # Today's progress (most immediate and motivating)
    if today_logs > 0:
        insights.append({
            'type': 'success',
            'icon': '✅',
            'message': f"You've already completed {today_logs} habit{'s' if today_logs > 1 else ''} today! Keep it going! 🚀"
        })
    
    # Best performing habit (celebrate wins)
    if len(habits_with_progress) > 0:
        if best_habit['completed'] >= 5:
            insights.append({
                'type': 'success',
                'icon': '🔥',
                'message': f"Your strongest habit: {best_habit['emoji']} {best_habit['name']} - {best_habit['completed']} day{'s' if best_habit['completed'] > 1 else ''} completed! Amazing work!"
            })
        elif best_habit['completed'] >= 3:
            insights.append({
                'type': 'success',
                'icon': '⭐',
                'message': f"Great progress with {best_habit['emoji']} {best_habit['name']}! You've completed it {best_habit['completed']} time{'s' if best_habit['completed'] > 1 else ''} this month."
            })
        elif best_habit['completed'] > 0:
            insights.append({
                'type': 'success',
                'icon': '🌱',
                'message': f"You've started tracking {best_habit['emoji']} {best_habit['name']}! {best_habit['completed']} completion{'s' if best_habit['completed'] > 1 else ''} so far - keep building that streak!"
            })
    
    # Overall progress (motivational context)
    if overall_pct >= 80:
        insights.append({
            'type': 'success',
            'icon': '🎉',
            'message': f"Outstanding! You're at {overall_pct:.1f}% completion. You're building amazing consistency!"
        })
    elif overall_pct >= 60:
        insights.append({
            'type': 'success',
            'icon': '💪',
            'message': f"Great progress! You're at {overall_pct:.1f}% completion. Keep up the momentum!"
        })
    elif overall_pct >= 30:
        insights.append({
            'type': 'info',
            'icon': '📈',
            'message': f"You're at {overall_pct:.1f}% completion. Small daily actions lead to big results!"
        })
    elif overall_pct > 0:
        insights.append({
            'type': 'info',
            'icon': '🌱',
            'message': f"You've completed {total_completed} habit{'s' if total_completed > 1 else ''} this month. Every step counts!"
        })
    
    # PRIORITY 2: Smart recommendations (dynamic and personalized)
    # Recommend habits not completed today
    if len(pending_today_habits) > 0 and today_logs < len(habits):
        # Prioritize habits that haven't been tracked yet this month
        untracked_habits = [h for h in pending_today_habits if 
                           not any(s['habit_id'] == str(h.id) and s['completed'] > 0 for s in habit_stats)]
        
        if untracked_habits:
            # Recommend a habit that hasn't been tracked yet
            recommended = untracked_habits[0]
            insights.append({
                'type': 'info',
                'icon': '💡',
                'message': f"Try tracking {recommended.emoji} {recommended.name} today - it's a great way to start!"
            })
        elif len(pending_today_habits) == 1:
            # Only one habit left for today
            recommended = pending_today_habits[0]
            habit_stat = next((s for s in habit_stats if s['habit_id'] == str(recommended.id)), None)
            if habit_stat and habit_stat['completed'] > 0:
                insights.append({
                    'type': 'info',
                    'icon': '🎯',
                    'message': f"Almost there! Complete {recommended.emoji} {recommended.name} to finish all your habits today!"
                })
            else:
                insights.append({
                    'type': 'info',
                    'icon': '💡',
                    'message': f"Don't forget {recommended.emoji} {recommended.name} today - you've got this!"
                })
        else:
            # Multiple habits pending - recommend the one with least progress
            pending_with_stats = []
            for h in pending_today_habits:
                stat = next((s for s in habit_stats if s['habit_id'] == str(h.id)), None)
                if stat:
                    pending_with_stats.append((h, stat))
            
            if pending_with_stats:
                # Recommend the habit with lowest completion rate
                recommended_habit, recommended_stat = min(pending_with_stats, key=lambda x: x[1]['percentage'])
                if recommended_stat['completed'] == 0:
                    insights.append({
                        'type': 'info',
                        'icon': '💡',
                        'message': f"Start tracking {recommended_habit.emoji} {recommended_habit.name} today - every habit counts!"
                    })
                elif recommended_stat['percentage'] < 30:
                    insights.append({
                        'type': 'info',
                        'icon': '📊',
                        'message': f"Focus on {recommended_habit.emoji} {recommended_habit.name} today - it's at {recommended_stat['completed']}/{recommended_stat['goal']} days."
                    })
    
    # If no positive insights yet, add encouragement
    if len(insights) == 0:
        insights.append({
            'type': 'info',
            'icon': '⏰',
            'message': "Don't forget to track your habits today! You did great yesterday." if yesterday_logs > 0 else "Ready to start? Track your first habit today!"
        })
    
    # Dynamic limit based on user's situation
    # More insights for users with more habits and progress
    if len(habits) >= 5 and total_completed > 0:
        max_insights = 4  # More insights for active users with many habits
    elif len(habits) >= 3:
        max_insights = 3  # Standard for users with multiple habits
    elif len(habits) == 1:
        max_insights = 2  # Fewer insights for single habit users
    else:
        max_insights = 3  # Default
    
    return jsonify({'insights': insights[:max_insights]})

# Notification scheduler functions
def send_scheduled_notifications():
    """Send notifications to all users based on their preferences"""
    with app.app_context():
        try:
            # Get all users with email notifications enabled
            users = User.query.filter_by(email_notifications_enabled=True).all()
            current_time = datetime.now().strftime('%H:%M')
            
            for user in users:
                try:
                    # Check if it's time to send notification for this user
                    if user.notification_time == current_time:
                        # Check frequency
                        if user.notification_frequency in ['daily', 'both']:
                            # Send daily reminder
                            send_daily_reminder_email(user)
                        
                        # Check if it's Monday (for weekly summaries)
                        if datetime.now().weekday() == 0:  # Monday
                            if user.notification_frequency in ['weekly', 'both']:
                                send_weekly_summary_email(user)
                except Exception as e:
                    print(f"Error sending notification to {user.email}: {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"Error in scheduled notifications: {e}")
            import traceback
            traceback.print_exc()

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=send_scheduled_notifications,
    trigger=CronTrigger(minute='*'),  # Run every minute to check user-specific times
    id='send_notifications',
    name='Send personalized email notifications',
    replace_existing=True
)

# Start scheduler (only if not in Vercel)
if not os.environ.get('VERCEL'):
    try:
        scheduler.start()
        print("Notification scheduler started")
        # Shut down scheduler on exit
        atexit.register(lambda: scheduler.shutdown())
    except Exception as e:
        print(f"Error starting scheduler: {e}")

# API endpoints for notification preferences
@app.route('/api/notification-preferences', methods=['GET'])
@api_login_required
def get_notification_preferences():
    """Get current user's notification preferences"""
    try:
        user = current_user
        return jsonify({
            'email_notifications_enabled': user.email_notifications_enabled,
            'notification_time': user.notification_time,
            'notification_frequency': user.notification_frequency
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/notification-preferences', methods=['PUT'])
@api_login_required
def update_notification_preferences():
    """Update current user's notification preferences"""
    try:
        data = request.get_json()
        user = current_user
        
        if 'email_notifications_enabled' in data:
            user.email_notifications_enabled = bool(data['email_notifications_enabled'])
        
        if 'notification_time' in data:
            # Validate time format (HH:MM)
            time_str = data['notification_time']
            try:
                datetime.strptime(time_str, '%H:%M')
                user.notification_time = time_str
            except ValueError:
                return jsonify({'error': 'Invalid time format. Use HH:MM (e.g., 09:00)'}), 400
        
        if 'notification_frequency' in data:
            frequency = data['notification_frequency']
            if frequency in ['daily', 'weekly', 'both']:
                user.notification_frequency = frequency
            else:
                return jsonify({'error': 'Invalid frequency. Must be "daily", "weekly", or "both"'}), 400
        
        db.session.commit()
        return jsonify({
            'message': 'Notification preferences updated',
            'email_notifications_enabled': user.email_notifications_enabled,
            'notification_time': user.notification_time,
            'notification_frequency': user.notification_frequency
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Database migration endpoint (for initial setup)
@app.route('/api/migrate', methods=['POST', 'GET'])
def migrate_database():
    """Create database tables and add new columns - run this after code updates"""
    try:
        with app.app_context():
            # Create all tables (if they don't exist)
            db.create_all()
            
            # Add new columns to User table if they don't exist (for existing databases)
            from sqlalchemy import inspect, text
            
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            # Check and add email_notifications_enabled column
            if 'email_notifications_enabled' not in columns:
                try:
                    if db.engine.url.drivername == 'sqlite':
                        db.session.execute(text('ALTER TABLE user ADD COLUMN email_notifications_enabled BOOLEAN DEFAULT 1'))
                    else:
                        db.session.execute(text('ALTER TABLE "user" ADD COLUMN email_notifications_enabled BOOLEAN DEFAULT TRUE'))
                    db.session.commit()
                    print("Added email_notifications_enabled column")
                except Exception as e:
                    db.session.rollback()
                    print(f"Note: email_notifications_enabled column may already exist: {e}")
            
            # Check and add notification_time column
            if 'notification_time' not in columns:
                try:
                    if db.engine.url.drivername == 'sqlite':
                        db.session.execute(text("ALTER TABLE user ADD COLUMN notification_time VARCHAR(5) DEFAULT '09:00'"))
                    else:
                        db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN notification_time VARCHAR(5) DEFAULT '09:00'"))
                    db.session.commit()
                    print("Added notification_time column")
                except Exception as e:
                    db.session.rollback()
                    print(f"Note: notification_time column may already exist: {e}")
            
            # Check and add notification_frequency column
            if 'notification_frequency' not in columns:
                try:
                    if db.engine.url.drivername == 'sqlite':
                        db.session.execute(text("ALTER TABLE user ADD COLUMN notification_frequency VARCHAR(20) DEFAULT 'daily'"))
                    else:
                        db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN notification_frequency VARCHAR(20) DEFAULT 'daily'"))
                    db.session.commit()
                    print("Added notification_frequency column")
                except Exception as e:
                    db.session.rollback()
                    print(f"Note: notification_frequency column may already exist: {e}")
            
            db.session.commit()
            
        return jsonify({
            'message': 'Database migrated successfully',
            'tables': ['User', 'Habit', 'HabitLog'],
            'note': 'New notification columns added to User table'
        }), 200
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Only run development server if not in Vercel
if __name__ == '__main__' and not os.environ.get('VERCEL'):
    app.run(debug=True, host='0.0.0.0', port=5000)
