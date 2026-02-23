from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import secrets
import csv
import pytz
from io import StringIO, BytesIO
from dotenv import load_dotenv


# Import meet_utils if available
try:
    from meet_utils import get_meet_info
except ImportError:
    def get_meet_info(url):
        return ("Classroom", None)

load_dotenv()

IST = pytz.timezone('Asia/Kolkata')

def get_now_ist():
    return datetime.now(IST).replace(tzinfo=None)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['QUESTION_IMAGE_FOLDER'] = 'static/question_images'
app.config['PROFILE_IMAGE_FOLDER'] = 'static/profile_pics'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# --- Database Configuration ---
# Ensure instance folder exists for SQLite
os.makedirs(app.instance_path, exist_ok=True)

db_url = os.environ.get('DATABASE_URL')
if not db_url:
    # Use instance folder for SQLite by default
    db_url = f"sqlite:///{os.path.join(app.instance_path, 'aptipro.db')}"
elif db_url.startswith("postgres://"):
    # Render's old postgres URLs need to be converted for SQLAlchemy
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=3650) # 10 years

db = SQLAlchemy(app)

# Ensure other directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['QUESTION_IMAGE_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROFILE_IMAGE_FOLDER'], exist_ok=True)

# --- Models ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120))
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='student')
    profile_image = db.Column(db.String(100))
    profile_image_data = db.Column(db.LargeBinary) # Store in DB
    profile_image_mimetype = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=get_now_ist)
    
    answers = db.relationship('Answer', backref='student', lazy=True)
    attempts = db.relationship('Attempt', backref='student', lazy=True)

    @property
    def solved_count(self):
        return sum(1 for a in self.answers if a.is_correct)

    @property
    def total_attempted(self):
        return len(self.answers)

    @property
    def accuracy(self):
        if not self.answers:
            return 0
        return (self.solved_count / len(self.answers)) * 100

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(100))
    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))
    correct_answer = db.Column(db.String(1))
    explanation = db.Column(db.Text)
    meet_link = db.Column(db.String(500))
    time_limit = db.Column(db.Integer, default=10) # minutes
    image_file = db.Column(db.String(100))
    image_data = db.Column(db.LargeBinary) # Store in DB
    image_mimetype = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=get_now_ist)
    
    answers = db.relationship('Answer', backref='question', lazy=True)
    attempts = db.relationship('Attempt', backref='question', lazy=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option = db.Column(db.String(1))
    file_path = db.Column(db.String(200))
    file_data = db.Column(db.LargeBinary) # Store in DB
    file_mimetype = db.Column(db.String(50))
    file_name = db.Column(db.String(100))
    is_correct = db.Column(db.Boolean)
    is_expired = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=get_now_ist)

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=get_now_ist)
    __table_args__ = (db.UniqueConstraint('student_id', 'question_id', name='_student_question_uc'), )

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    active_meet_link = db.Column(db.String(500), default='https://meet.google.com/')
    detected_title = db.Column(db.String(200), default='Official Classroom')
    is_live = db.Column(db.Boolean, default=False)
    registration_open = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=get_now_ist)

class MeetLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100))
    url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=get_now_ist)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    event_time = db.Column(db.DateTime, default=get_now_ist)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    student_name = db.Column(db.String(120))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    question_text = db.Column(db.String(200))
    is_correct = db.Column(db.Boolean)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_now_ist)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # None for broadcast
    content = db.Column(db.Text, nullable=True) # Content can be null if only file is sent
    file_data = db.Column(db.LargeBinary)
    file_mimetype = db.Column(db.String(100))
    file_name = db.Column(db.String(255))
    is_read = db.Column(db.Boolean, default=False)
    is_broadcast = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_now_ist)
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_messages')

# --- Helpers ---

def fix_id(obj):
    """Ensure object has 'id' as string for consistency if needed, but SQLAlchemy already does this."""
    if obj:
        obj.id_str = str(obj.id)
    return obj

def fix_ids(objs):
    return [fix_id(o) for o in objs]

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_meet_link(url):
    if not url: return True
    return any(domain in url.lower() for domain in ['meet.google.com/', 'meet.new/'])

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Initialization ---

def init_db():
    try:
        with app.app_context():
            db.create_all()
            
            # 🛡️ Migration: Add binary columns to existing databases if they don't exist
            try:
                with db.engine.connect() as conn:
                    # Detect if we are on SQLite
                    is_sqlite = db.engine.url.drivername == 'sqlite'
                    blob_type = "BLOB" if is_sqlite else "BYTEA"
                    
                    # Wrap each ALTER in its own try/except to avoid stopping on one failure
                    def safe_alter(sql):
                        try:
                            conn.execute(db.text(sql))
                            conn.commit()
                        except:
                            pass

                    # User table
                    safe_alter(f"ALTER TABLE \"user\" ADD COLUMN profile_image_data {blob_type}")
                    safe_alter("ALTER TABLE \"user\" ADD COLUMN profile_image_mimetype VARCHAR(50)")
                    
                    # Question table
                    safe_alter(f"ALTER TABLE question ADD COLUMN image_data {blob_type}")
                    safe_alter("ALTER TABLE question ADD COLUMN image_mimetype VARCHAR(50)")
                    
                    # Answer table
                    safe_alter(f"ALTER TABLE answer ADD COLUMN file_data {blob_type}")
                    safe_alter("ALTER TABLE answer ADD COLUMN file_mimetype VARCHAR(50)")
                    safe_alter("ALTER TABLE answer ADD COLUMN file_name VARCHAR(100)")
                    
                    # Notification table
                    safe_alter("ALTER TABLE notification ADD COLUMN type VARCHAR(50)")
                    
                    # Message table
                    safe_alter(f"ALTER TABLE message ADD COLUMN file_data {blob_type}")
                    safe_alter("ALTER TABLE message ADD COLUMN file_mimetype VARCHAR(100)")
                    safe_alter("ALTER TABLE message ADD COLUMN file_name VARCHAR(255)")

                    # Classroom additions
                    safe_alter("ALTER TABLE classroom ADD COLUMN registration_open BOOLEAN DEFAULT TRUE")
            except Exception as e:
                print(f"Migration skip/failed: {e}")
            
            # Initialize Classroom
            try:
                if not Classroom.query.first():
                    db.session.add(Classroom(
                        active_meet_link='https://meet.google.com/',
                        detected_title='Official Classroom',
                        is_live=False,
                        registration_open=True
                    ))
                    db.session.commit()
            except:
                db.session.rollback()
            
            # Check for default admin
            try:
                if not User.query.filter_by(role='admin').first():
                    admin = User(
                        username='admin',
                        full_name='Administrator',
                        password=generate_password_hash('admin123'),
                        role='admin'
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print("Default admin created: admin / admin123")
            except:
                db.session.rollback()
    except Exception as e:
        print(f"Database initialization error: {e}")

# Only call init_db if we're not in a testing environment or a multi-worker reload loop that might crash
if os.environ.get('INITIALIZE_DB', 'true').lower() == 'true':
    init_db()

# --- Routes ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            
            # Log login event
            db.session.add(ActivityLog(user_id=user.id, action="LOGIN", details=f"User {user.username} logged in"))
            
            # Notify admin of login if it's a student
            if user.role == 'student':
                notif = Notification(
                    type='login',
                    student_id=user.id,
                    student_name=user.full_name or user.username,
                    read=False
                )
                db.session.add(notif)
            
            db.session.commit()
            
            resp = make_response(redirect(url_for('index')))
            resp.set_cookie('returning_user', 'true', max_age=315360000) # 10 years
            return resp
        flash('Invalid credentials')
    
    classroom = Classroom.query.first()
    registration_open = classroom.registration_open if classroom else True
    return render_template('login.html', registration_open=registration_open)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    classroom = Classroom.query.first()
    if classroom and not classroom.registration_open:
        flash('Registration is currently closed by the administrator.')
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        
        max_members = 1000000000
        current_members = User.query.filter_by(role='student').count()
        
        if current_members >= max_members:
            flash(f'Registration limit reached ({max_members} members).')
            return redirect(url_for('login', tab='register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('login', tab='register'))
            
        image = request.files.get('profile_image')
        image_data = None
        image_mimetype = None
        image_filename = None
        if image and allowed_file(image.filename):
            image_data = image.read()
            image_mimetype = image.mimetype
            image_filename = image.filename

        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            full_name=full_name,
            password=hashed_pw,
            role='student',
            profile_image=image_filename,
            profile_image_data=image_data,
            profile_image_mimetype=image_mimetype
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Log registration event
        db.session.add(ActivityLog(user_id=new_user.id, action="REGISTER", details=f"New user registered: {new_user.username}"))
        
        # Notify admin of registration
        notif = Notification(
            type='register',
            student_id=new_user.id,
            student_name=new_user.full_name or new_user.username,
            read=False
        )
        db.session.add(notif)
        
        db.session.commit()
        
        login_user(new_user)
        flash('Account created!')
        resp = make_response(redirect(url_for('student_dashboard')))
        resp.set_cookie('returning_user', 'true', max_age=315360000) # 10 years
        return resp
        
@app.route('/history')
@login_required
def history():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    submissions = Answer.query.order_by(Answer.submitted_at.desc()).all()
    all_users = User.query.filter_by(role='student').all()
    results = []
    for s in submissions:
        student = db.session.get(User, s.student_id)
        question = db.session.get(Question, s.question_id)
        results.append({
            'student': student or {'username': 'Deleted', 'full_name': 'Deleted User'},
            'question': question or {'text': 'Deleted Question'},
            'submitted_at': s.submitted_at,
            'selected_option': s.selected_option,
            'is_correct': s.is_correct
        })
    return render_template('history.html', results=results, all_users=all_users)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Admin Routes ---

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    questions = Question.query.order_by(Question.created_at.desc()).all()
    all_users = User.query.filter_by(role='student').all()
    total_submissions = Answer.query.count()
        
    classroom = Classroom.query.first()
    meet_links = MeetLink.query.order_by(MeetLink.created_at.desc()).all()

    # Database health/type info
    try:
        db_type = "PostgreSQL" if "postgresql" in str(db.engine.url).lower() else "SQLite"
    except:
        db_type = "Unknown"

    return render_template('admin_dashboard.html', 
                         questions=questions, 
                         classroom=classroom,
                         meet_links=meet_links,
                         all_users=all_users,
                         total_submissions=total_submissions,
                         db_type=db_type)

@app.route('/admin/stats')
@login_required
def admin_stats():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    total_solved = Answer.query.filter_by(is_correct=True).count()
    total_attempts = Answer.query.count()
    all_users = User.query.filter_by(role='student').all()
    
    platform_stats = {
        'total_solved': total_solved,
        'total_attempts': total_attempts,
        'accuracy': (total_solved / total_attempts * 100) if total_attempts > 0 else 0
    }
    
    # Registration growth history
    reg_history = {}
    for u in all_users:
        if u.created_at:
            d = u.created_at.strftime('%Y-%m-%d')
            reg_history[d] = reg_history.get(d, 0) + 1
    
    # Sort dates
    sorted_dates = sorted(reg_history.keys())
    growth_data = {
        'labels': sorted_dates,
        'counts': [reg_history[d] for d in sorted_dates]
    }

    platform_stats['avg_attempts'] = (total_attempts / len(all_users)) if all_users else 0

    return render_template('admin_stats.html', 
                         platform_stats=platform_stats, 
                         all_users=all_users,
                         growth_data=growth_data)

@app.route('/admin/activity')
@login_required
def admin_activity_logs():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    logs = ActivityLog.query.order_by(ActivityLog.event_time.desc()).all()
    return render_template('admin_activity.html', activity_logs=logs)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        new_password = request.form.get('password')
        image = request.files.get('profile_image')
        
        current_user.full_name = full_name
        if new_password:
            current_user.password = generate_password_hash(new_password)
            
        if image and allowed_file(image.filename):
            current_user.profile_image_data = image.read()
            current_user.profile_image_mimetype = image.mimetype
            current_user.profile_image = image.filename
            
            # Log event to database
            new_log = ActivityLog(user_id=current_user.id, action="PROFILE_PIC_UPDATE", details=f"Uploaded {image.filename} to Database")
            db.session.add(new_log)
        
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('student_profile'))
        
    return render_template('student_profile.html', user=current_user)

@app.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_view_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    user = db.session.get(User, user_id)
    if not user:
        flash('User not found')
        return redirect(url_for('admin_members_dashboard'))
    
    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.username = request.form.get('username')
            
        db.session.commit()
        flash('User profile updated!')
        return redirect(url_for('admin_view_user', user_id=user.id))
        
    # Get user stats
    user_answers = Answer.query.filter_by(student_id=user.id).all()
    correct_count = sum(1 for a in user_answers if a.is_correct)
    stats = {
        'total': len(user_answers),
        'correct': correct_count,
        'accuracy': (correct_count / len(user_answers) * 100) if user_answers else 0
    }
    
    return render_template('admin_view_user.html', student=user, stats=stats, submissions=user_answers)

@app.route('/admin/questions')
@login_required
def admin_questions_dashboard():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    questions = Question.query.order_by(Question.created_at.desc()).all()
    return render_template('admin_questions.html', active_questions=questions, expired_questions=[])

@app.route('/admin/submissions')
@login_required
def admin_submissions_dashboard():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 50
    pagination = Answer.query.order_by(Answer.submitted_at.desc()).paginate(page=page, per_page=per_page)
    submissions = pagination.items
    
    results = []
    for s in submissions:
        student = db.session.get(User, s.student_id)
        question = db.session.get(Question, s.question_id)
        results.append({
            'id': s.id,
            'student': student or {'username': 'Deleted', 'full_name': 'Deleted User'},
            'question': question or {'text': 'Deleted Question'},
            'submitted_at': s.submitted_at,
            'selected_option': s.selected_option,
            'is_correct': s.is_correct,
            'file_path': s.file_path
        })
    return render_template('admin_submissions.html', results=results, pagination=pagination)

@app.route('/admin/members')
@login_required
def admin_members_dashboard():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    
    # Calculate IST dates
    now_ist = get_now_ist()
    today_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    tomorrow_start = today_start + timedelta(days=1)
    
    page = request.args.get('page', 1, type=int)
    per_page = 15
    pagination = User.query.filter_by(role='student').order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    members = pagination.items
    
    # Registration counts (keep these global as they are small)
    today_reg = User.query.filter(User.role == 'student', User.created_at >= today_start, User.created_at < tomorrow_start).count()
    yesterday_reg = User.query.filter(User.role == 'student', User.created_at >= yesterday_start, User.created_at < today_start).count()
    total_reg = User.query.filter_by(role='student').count()
    
    reg_stats = {
        'today': today_reg,
        'yesterday': yesterday_reg,
        'tomorrow': 0,
        'total': total_reg,
        'today_start': today_start,
        'yesterday_start': yesterday_start
    }
    
    return render_template('admin_students.html', all_users=members, reg_stats=reg_stats, pagination=pagination)

@app.route('/admin/post_question', methods=['GET', 'POST'])
@login_required
def post_question():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    if request.method == 'GET': return render_template('post_question.html')
    
    text = request.form.get('text')
    topic = request.form.get('topic', '')
    option_a = request.form.get('option_a')
    option_b = request.form.get('option_b')
    option_c = request.form.get('option_c')
    option_d = request.form.get('option_d')
    correct_answer = request.form.get('correct_answer')
    explanation = request.form.get('explanation')
    meet_link = request.form.get('meet_link')
    time_limit = request.form.get('time_limit', 10, type=int)
    
    image = request.files.get('image')
    image_data = None
    image_mimetype = None
    image_filename = None
    if image and allowed_file(image.filename):
        image_data = image.read()
        image_mimetype = image.mimetype
        image_filename = image.filename
    
    new_q = Question(
        text=text, topic=topic, option_a=option_a, option_b=option_b, 
        option_c=option_c, option_d=option_d, correct_answer=correct_answer, 
        explanation=explanation, meet_link=meet_link, time_limit=time_limit,
        image_file=image_filename, image_data=image_data, image_mimetype=image_mimetype
    )
    db.session.add(new_q)
    db.session.commit()
    flash('Question posted!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_question/<int:question_id>', methods=['POST', 'GET'])
@login_required
def delete_question(question_id):
    if current_user.role == 'admin':
        Question.query.filter_by(id=question_id).delete()
        Answer.query.filter_by(question_id=question_id).delete()
        Attempt.query.filter_by(question_id=question_id).delete()
        db.session.commit()
        flash('Question deleted')
    return redirect(url_for('admin_questions_dashboard'))

@app.route('/admin/edit_question/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    question = Question.query.get(question_id)
    if not question:
        flash('Question not found')
        return redirect(url_for('admin_questions_dashboard'))
        
    if request.method == 'POST':
        question.text = request.form.get('text')
        question.topic = request.form.get('topic', '')
        question.option_a = request.form.get('option_a')
        question.option_b = request.form.get('option_b')
        question.option_c = request.form.get('option_c')
        question.option_d = request.form.get('option_d')
        question.correct_answer = request.form.get('correct_answer')
        question.explanation = request.form.get('explanation')
        question.time_limit = request.form.get('time_limit', 10, type=int)
        
        image = request.files.get('image')
        if image and image.filename:
            question.image_data = image.read()
            question.image_mimetype = image.mimetype
            question.image_file = image.filename
            
        db.session.commit()
        flash('Question updated!')
        return redirect(url_for('admin_questions_dashboard'))
        
    return render_template('edit_question.html', q=question)

# --- Classroom / Config Routes ---

@app.route('/admin/update_classroom', methods=['POST'])
@login_required
def update_classroom():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    link = request.form.get('meet_link')
    is_live = 'is_live' in request.form
    registration_open = 'registration_open' in request.form
    title, _ = get_meet_info(link) if link else ("Classroom", None)
    
    classroom = Classroom.query.first()
    if classroom:
        classroom.active_meet_link = link
        classroom.is_live = is_live
        classroom.registration_open = registration_open
        classroom.detected_title = title
        classroom.updated_at = get_now_ist()
        
        db.session.commit()
    
    flash('Classroom updated')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/refresh_classroom')
@login_required
def refresh_classroom():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    classroom = Classroom.query.first()
    if classroom and classroom.active_meet_link:
        title, _ = get_meet_info(classroom.active_meet_link)
        classroom.detected_title = title
        db.session.commit()
        flash('Status refreshed')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_meet_link', methods=['POST'])
@login_required
def add_meet_link():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    label = request.form.get('label')
    url = request.form.get('url')
    if is_valid_meet_link(url):
        new_link = MeetLink(label=label, url=url, is_active=True)
        db.session.add(new_link)
        db.session.commit()
        flash('Link added')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_meet_link/<int:link_id>', methods=['POST', 'GET'])
@login_required
def toggle_meet_link(link_id):
    if current_user.role == 'admin':
        link = db.session.get(MeetLink, link_id)
        if link:
            link.is_active = not link.is_active
            db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_meet_link/<int:link_id>', methods=['POST', 'GET'])
@login_required
def delete_meet_link(link_id):
    if current_user.role == 'admin':
        MeetLink.query.filter_by(id=link_id).delete()
        db.session.commit()
    return redirect(url_for('admin_dashboard'))


# --- Student Routes ---

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student': return redirect(url_for('admin_dashboard'))
    questions = Question.query.order_by(Question.created_at.desc()).all()
    answers_list = Answer.query.filter_by(student_id=current_user.id).all()
    user_answers = {a.question_id: a for a in answers_list}
    attempts_list = Attempt.query.filter_by(student_id=current_user.id).all()
    user_attempts = {a.question_id: a.start_time.timestamp() * 1000 for a in attempts_list}
    
    correct_count = sum(1 for a in answers_list if a.is_correct)

    # Compute today's stats (based on IST midnight)
    now_ist = get_now_ist()
    today_ist_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_questions = [q for q in questions if q.created_at >= today_ist_start]
    today_question_ids = {q.id for q in today_questions}
    
    # Answers submitted today
    today_answers = [a for a in answers_list if a.submitted_at >= today_ist_start and a.question_id in today_question_ids]
    today_solved_count = len(today_answers)
    today_total_count = len(today_questions)

    stats = {
        'total': len(questions),
        'solved': len(user_answers),
        'unsolved': len(questions) - len(user_answers),
        'correct': correct_count,
        'incorrect': len(user_answers) - correct_count,
        'accuracy': (correct_count / len(user_answers) * 100) if user_answers else 0,
        'today_total': today_total_count,
        'today_solved': today_solved_count,
        'today_remaining': max(0, today_total_count - today_solved_count)
    }
    
    classroom = Classroom.query.first()
    active_meet_links = MeetLink.query.filter_by(is_active=True).all()

    # Lifetime Performance History
    history_map = {}
    for a in answers_list:
        if a.submitted_at:
            d = a.submitted_at.strftime('%Y-%m-%d')
            if d not in history_map:
                history_map[d] = {'correct': 0, 'total': 0}
            history_map[d]['total'] += 1
            if a.is_correct:
                history_map[d]['correct'] += 1
    
    sorted_history_dates = sorted(history_map.keys())
    daily_stats = {
        'labels': sorted_history_dates,
        'accuracy': [round(history_map[d]['correct'] / history_map[d]['total'] * 100, 1) if history_map[d]['total'] > 0 else 0 for d in sorted_history_dates]
    }

    return render_template('student_dashboard.html', 
                         questions=questions, user_answers=user_answers, 
                         user_attempts=user_attempts, stats=stats, 
                         classroom=classroom, active_meet_links=active_meet_links,
                         daily_stats=daily_stats,
                         server_now=get_now_ist().timestamp() * 1000)

@app.route('/student/start_attempt', methods=['POST'])
@login_required
def start_attempt():
    question_id = request.json.get('question_id')
    existing = Attempt.query.filter_by(student_id=current_user.id, question_id=question_id).first()
    if not existing:
        new_attempt = Attempt(student_id=current_user.id, question_id=question_id)
        db.session.add(new_attempt)
        # Log attempt event
        db.session.add(ActivityLog(user_id=current_user.id, action="ATTEMPT_START", details=f"Started question {question_id}"))
        db.session.commit()
        return jsonify({'start_time': new_attempt.start_time.timestamp() * 1000})
    return jsonify({'start_time': existing.start_time.timestamp() * 1000})

@app.route('/student/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    question_id = request.form.get('question_id')
    selected_option = request.form.get('selected_option')
    file = request.files.get('file')
    question = Question.query.get(question_id)
    if not question: return redirect(url_for('student_dashboard'))
    
    if question.time_limit > 0:
        attempt = Attempt.query.filter_by(student_id=current_user.id, question_id=question_id).first()
        if attempt:
            expiry_time = attempt.start_time + timedelta(minutes=question.time_limit)
            if get_now_ist() > expiry_time:
                flash('TIME EXPIRED: Your submission was recorded as late and could not be accepted for full marks.')
                new_ans = Answer(
                    student_id=current_user.id, question_id=question_id, 
                    selected_option=selected_option, file_path=None, 
                    is_correct=False, is_expired=True
                )
                db.session.add(new_ans)
                # Log late submission
                db.session.add(ActivityLog(user_id=current_user.id, action="LATE_SUBMISSION", details=f"Late attempt for question {question_id}"))
                db.session.commit()
                return redirect(url_for('student_dashboard'))

    file_data = None
    file_mimetype = None
    file_name = None
    if file and allowed_file(file.filename):
        file_data = file.read()
        file_mimetype = file.mimetype
        file_name = file.filename
    
    is_correct = (selected_option == question.correct_answer) if selected_option else None
    new_ans = Answer(
        student_id=current_user.id, question_id=question_id, 
        selected_option=selected_option, file_path=file_name,
        file_data=file_data, file_mimetype=file_mimetype, file_name=file_name,
        is_correct=is_correct
    )
    db.session.add(new_ans)
    # Log submission event
    db.session.add(ActivityLog(user_id=current_user.id, action="SUBMISSION", details=f"Answered Q{question_id} ({'PASS' if is_correct else 'FAIL'})"))

    # 🔔 Notify admin
    notif = Notification(
        type='submission',
        student_id=current_user.id,
        student_name=current_user.full_name or current_user.username,
        question_id=question_id,
        question_text=(question.text[:80] + '...') if len(question.text) > 80 else question.text,
        is_correct=is_correct,
        read=False
    )
    db.session.add(notif)
    db.session.commit()

    flash('Submitted!')
    return redirect(url_for('student_dashboard'))

@app.route('/messages')
@login_required
def messages():
    if current_user.role == 'admin':
        # Admin sees all conversations
        users = User.query.filter_by(role='student').all()
        # For admin, we'll show messages with a specific user if selected
        selected_user_id = request.args.get('user_id', type=int)
        chats = []
        student_context = None
        if selected_user_id:
            chats = Message.query.filter(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == selected_user_id)) |
                ((Message.sender_id == selected_user_id) & (Message.receiver_id == current_user.id)) |
                (Message.is_broadcast == True)
            ).order_by(Message.created_at.asc()).all()
            
            # Fetch student's recent answers for context
            student_context = Answer.query.filter_by(student_id=selected_user_id).order_by(Answer.submitted_at.desc()).limit(5).all()
            
            # Mark as read
            Message.query.filter_by(receiver_id=current_user.id, sender_id=selected_user_id, is_read=False).update({Message.is_read: True})
            db.session.commit()
            
        return render_template('admin_messages.html', users=users, chats=chats, selected_user_id=selected_user_id, student_context=student_context)
    else:
        # Student sees messages with admin and broadcasts
        admin = User.query.filter_by(role='admin').first()
        chats = Message.query.filter(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == admin.id)) |
            ((Message.sender_id == admin.id) & (Message.receiver_id == current_user.id)) |
            (Message.is_broadcast == True)
        ).order_by(Message.created_at.asc()).all()
        # Mark as read
        Message.query.filter_by(receiver_id=current_user.id, is_read=False).update({Message.is_read: True})
        db.session.commit()
        return render_template('messages.html', chats=chats, admin=admin)

@app.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    receiver_id = request.form.get('receiver_id', type=int)
    content = request.form.get('content')
    is_broadcast = request.form.get('is_broadcast') == 'true'
    file = request.files.get('file')
    
    if not content and not file:
        return redirect(url_for('messages'))
        
    file_data = None
    file_mimetype = None
    file_name = None
    
    if file and file.filename != '':
        file_data = file.read()
        file_mimetype = file.content_type
        file_name = secure_filename(file.filename)
        
    if is_broadcast and current_user.role == 'admin':
        msg = Message(
            sender_id=current_user.id, 
            content=content, 
            is_broadcast=True,
            file_data=file_data,
            file_mimetype=file_mimetype,
            file_name=file_name
        )
    else:
        msg = Message(
            sender_id=current_user.id, 
            receiver_id=receiver_id, 
            content=content,
            file_data=file_data,
            file_mimetype=file_mimetype,
            file_name=file_name
        )
    
    db.session.add(msg)
    db.session.commit()
    
    if current_user.role == 'admin':
        return redirect(url_for('messages', user_id=receiver_id))
    return redirect(url_for('messages'))

@app.route('/messages/download/<int:message_id>')
@login_required
def download_message_file(message_id):
    msg = db.session.get(Message, message_id)
    if not msg or not msg.file_data:
        return "File not found", 404
        
    # Check permissions (either sender, receiver, or it's a broadcast)
    if msg.sender_id != current_user.id and msg.receiver_id != current_user.id and not msg.is_broadcast:
        return "Forbidden", 403
        
    return send_file(
        BytesIO(msg.file_data),
        mimetype=msg.file_mimetype,
        as_attachment=True,
        download_name=msg.file_name
    )

@app.route('/admin/notifications')
@login_required
def get_notifications():
    if current_user.role != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    notifs = Notification.query.filter_by(read=False).order_by(Notification.created_at.desc()).limit(20).all()
    result = []
    for n in notifs:
        result.append({
            'id': n.id,
            'type': n.type or 'submission',
            'student_id': n.student_id,
            'student_name': n.student_name,
            'question_text': n.question_text,
            'is_correct': n.is_correct,
            'created_at': n.created_at.strftime('%H:%M')
        })
    return jsonify({'notifications': result, 'count': len(result)})

@app.route('/admin/notifications/mark_read', methods=['POST'])
@login_required
def mark_notifications_read():
    if current_user.role != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    Notification.query.filter_by(read=False).update({Notification.read: True})
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/admin/export/submissions')
@login_required
def export_submissions():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    answers = Answer.query.order_by(Answer.submitted_at.desc()).all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Username', 'Question', 'Result', 'Submitted At'])
    for ans in answers:
        student = db.session.get(User, ans.student_id)
        question = db.session.get(Question, ans.question_id)
        writer.writerow([
            student.full_name if student else 'Deleted User',
            student.username if student else 'N/A',
            (question.text[:80] + '...') if question and len(question.text) > 80 else (question.text if question else 'Deleted Question'),
            'PASS' if ans.is_correct else 'FAIL',
            ans.submitted_at.strftime('%Y-%m-%d %H:%M')
        ])
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'submissions_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    )

@app.route('/admin/export/members')
@login_required
def export_members():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    users = User.query.filter_by(role='student').all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Full Name', 'Username', 'Role', 'Registration Date'])
    for user in users:
        writer.writerow([
            user.full_name,
            user.username,
            user.role.upper(),
            user.created_at.strftime('%Y-%m-%d')
        ])
    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'members_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
    )

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/media/profile_pics/<int:user_id>/<filename>')
def serve_profile_pic(user_id, filename):
    """Serve profile pictures from the database."""
    user = db.session.get(User, user_id)
    if user and user.profile_image_data:
        return send_file(BytesIO(user.profile_image_data), mimetype=user.profile_image_mimetype)
    return send_from_directory(app.config['PROFILE_IMAGE_FOLDER'], 'default.jpg')

@app.route('/media/question_images/<int:question_id>')
def serve_question_image(question_id):
    """Serve question images from the database."""
    q = db.session.get(Question, question_id)
    if q and q.image_data:
        return send_file(BytesIO(q.image_data), mimetype=q.image_mimetype)
    return '', 404

@app.route('/media/submissions/<int:answer_id>')
@login_required
def serve_submission_file(answer_id):
    """Serve student submission files from the database."""
    ans = db.session.get(Answer, answer_id)
    if not ans or not ans.file_data: return '', 404
    if current_user.role != 'admin' and current_user.id != ans.student_id:
        return '', 403
    return send_file(BytesIO(ans.file_data), mimetype=ans.file_mimetype, as_attachment=True, download_name=ans.file_name)

if __name__ == '__main__':
    from waitress import serve
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    port = int(os.environ.get('PORT', 5000))
    print(f"Server starting on http://{local_ip}:{port}")
    serve(app, host='0.0.0.0', port=port)
