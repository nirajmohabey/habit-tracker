from flask import Flask, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, CHAR
from functools import wraps
import os
import secrets
import uuid
import random

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
    # For now, just print to console
    # In production, integrate with email service (SendGrid, AWS SES, etc.)
    print(f"\n{'='*50}")
    print(f"OTP Email for {username} ({email})")
    print(f"OTP Code: {otp_code}")
    print(f"Valid for 10 minutes")
    print(f"{'='*50}\n")
    
    # TODO: Implement actual email sending
    # Example with SMTP:
    # try:
    #     msg = MIMEMultipart()
    #     msg['From'] = 'noreply@habittracker.com'
    #     msg['To'] = email
    #     msg['Subject'] = 'Verify Your Email - Habit Tracker'
    #     body = f"Hello {username},\n\nYour OTP code is: {otp_code}\n\nThis code will expire in 10 minutes.\n\nIf you didn't request this, please ignore this email."
    #     msg.attach(MIMEText(body, 'plain'))
    #     # Send email using SMTP
    # except Exception as e:
    #     print(f"Error sending email: {e}")

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

@app.route('/forgot-password', methods=['POST', 'OPTIONS'])
def forgot_password():
    """Handle password reset request"""
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
        # In production, you would send an email with reset link here
        return jsonify({
            'message': 'If an account exists with that email or username, you will receive password reset instructions.'
        }), 200
    except Exception as e:
        print(f"Error in forgot_password: {str(e)}")
        return jsonify({'error': 'An error occurred processing your request'}), 500

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
    
    if not habit_stats or sum(s['completed'] for s in habit_stats) == 0:
        return jsonify({
            'insights': [{
                'type': 'info',
                'icon': '💡',
                'message': 'Start tracking your habits to see insights!'
            }]
        })
    
    # Find strongest and weakest habits
    best_habit = max(habit_stats, key=lambda x: x['completed'])
    worst_habit = min(habit_stats, key=lambda x: x['completed'])
    
    insights = []
    
    if best_habit['completed'] > 0:
        insights.append({
            'type': 'success',
            'icon': '🟢',
            'message': f"Strongest habit: {best_habit['emoji']} {best_habit['name']} ({best_habit['completed']}/{best_habit['goal']} completed)"
        })
    
    if worst_habit['completed'] < worst_habit['goal'] and worst_habit['completed'] < best_habit['completed']:
        insights.append({
            'type': 'warning',
            'icon': '🔴',
            'message': f"Weakest habit: {worst_habit['emoji']} {worst_habit['name']} ({worst_habit['completed']}/{worst_habit['goal']} completed)"
        })
    
    # Calculate overall completion rate
    total_completed = sum(s['completed'] for s in habit_stats)
    total_goal = sum(s['goal'] for s in habit_stats)
    overall_pct = (total_completed / total_goal * 100) if total_goal > 0 else 0
    
    if overall_pct >= 80:
        insights.append({
            'type': 'success',
            'icon': '🎉',
            'message': f"Excellent progress! You're at {overall_pct:.1f}% completion this month."
        })
    elif overall_pct >= 60:
        insights.append({
            'type': 'info',
            'icon': '💪',
            'message': f"Good progress! You're at {overall_pct:.1f}% completion. Keep it up!"
        })
    else:
        insights.append({
            'type': 'warning',
            'icon': '📈',
            'message': f"You're at {overall_pct:.1f}% completion. Every day is a new opportunity!"
        })
    
    return jsonify({'insights': insights})

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
