from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import os
from meet_utils import get_meet_info

from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-123')
# Default to sqlite for local dev, will be overridden below for Vercel
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///answer.db'

# Check if running on Vercel
IS_VERCEL = os.environ.get('VERCEL_REGION') is not None or os.environ.get('VERCEL') == '1'

if IS_VERCEL:
    # Use /tmp for writable directories in serverless environment
    app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
    app.config['QUESTION_IMAGE_FOLDER'] = '/tmp/question_images'
    
    # FIX: Vercel Postgres URLs often start with postgres://, but SQLAlchemy requires postgresql://
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    # Default to a /tmp sqlite db if no DATABASE_URL is set
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url or 'sqlite:////tmp/answer.db'
else:
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['QUESTION_IMAGE_FOLDER'] = 'static/question_images'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///answer.db')

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif'}

# Ensure folders exist
try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['QUESTION_IMAGE_FOLDER'], exist_ok=True)
except OSError:
    # In case of any other permission issues, just pass. 
    # Logic needing these will fail later, but app won't crash on start.
    pass

db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_valid_meet_link(url):
    if not url:
        return True # Optional field
    valid_prefixes = [
        'https://meet.google.com/',
        'https://meet.new/'
    ]
    return any(url.strip().startswith(prefix) for prefix in valid_prefixes)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=True)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin' or 'student'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False) # A, B, C, or D
    explanation = db.Column(db.Text)
    meet_link = db.Column(db.String(500))
    time_limit = db.Column(db.Integer, default=60) # in minutes
    image_file = db.Column(db.String(300), nullable=True) # Optional image for the question
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=True) # Optional if uploading file
    file_path = db.Column(db.String(300), nullable=True)
    is_correct = db.Column(db.Boolean)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student = db.relationship('User', backref='answers')
    question = db.relationship('Question', backref=db.backref('submissions', cascade='all, delete-orphan'))

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    active_meet_link = db.Column(db.String(500))
    detected_title = db.Column(db.String(200))
    is_live = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MeetLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    max_members = db.Column(db.Integer, default=50)

# Database Initialization for Serverless/Vercel
# This ensures tables exist even if the instance is new/ephemeral
def init_db():
    try:
        with app.app_context():
            db.create_all()
            # Check if we need to create a default admin
            # Use a broad catching mechanism in case DB is not ready
            if not User.query.filter_by(role='admin').first():
                default_admin = User(
                    username='admin',
                    full_name='System Administrator',
                    password='adminpassword', 
                    role='admin'
                )
                db.session.add(default_admin)
                print("Default admin created.")
            
            # Initialize config
            if not SystemConfig.query.first():
                config = SystemConfig(max_members=50)
                db.session.add(config)
                print("Default config created.")
            
            db.session.commit()
    except Exception as e:
        print(f"Database initialization warning: {e}")

# Run initialization
# We run this at the module level so it executes on import in Vercel
# Using IS_VERCEL to decide how aggressive to be with initialization
try:
    init_db()
except Exception as e:
    print(f"Startup error: {e}")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
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
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password: # In production, use hashed passwords
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        role = 'student'
        
        # Check membership limit
        config = SystemConfig.query.first()
        max_members = config.max_members if config else 50
        current_members_count = User.query.filter_by(role='student').count()
        
        if current_members_count >= max_members:
            flash(f'Registration limit reached ({max_members} members). Please contact administrator.')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        new_user = User(username=username, full_name=full_name, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        # Auto-login after registration
        login_user(new_user)
        flash('Account created and logged in!')
        return redirect(url_for('student_dashboard'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    questions = Question.query.all()
    results = Answer.query.order_by(Answer.submitted_at.desc()).all()
    classroom = Classroom.query.first()
    meet_links = MeetLink.query.order_by(MeetLink.created_at.desc()).all()
    all_users = User.query.filter_by(role='student').all()
    config = SystemConfig.query.first()
    return render_template('admin_dashboard.html', 
                         questions=questions, 
                         results=results[:5], # Show only last 5 on dashboard
                         classroom=classroom, 
                         meet_links=meet_links, 
                         all_users=all_users[:8], # Show only first 8 on dashboard
                         config=config)

@app.route('/admin/questions')
@login_required
def admin_questions_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    now = datetime.utcnow()
    active_questions = []
    expired_questions = []
    
    questions = Question.query.order_by(Question.created_at.desc()).all()
    for q in questions:
        expiry = q.created_at + timedelta(minutes=q.time_limit)
        if now > expiry:
            expired_questions.append(q)
        else:
            active_questions.append(q)
            
    return render_template('admin_questions.html', 
                         active_questions=active_questions, 
                         expired_questions=expired_questions)

@app.route('/admin/submissions')
@login_required
def admin_submissions_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    results = Answer.query.order_by(Answer.submitted_at.desc()).all()
    return render_template('admin_submissions.html', results=results)

@app.route('/admin/members')
@login_required
def admin_members_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    # Filter only students for the members directory
    all_users = User.query.filter_by(role='student').all()
    return render_template('admin_members.html', all_users=all_users)

@app.route('/admin/delete_question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted successfully')
    return redirect(url_for('admin_questions_dashboard'))

@app.route('/admin/history')
@login_required
def admin_history():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    questions = Question.query.all()
    results = Answer.query.order_by(Answer.submitted_at.desc()).all()
    all_users = User.query.all()
    
    return render_template('history.html', questions=questions, results=results, all_users=all_users)

@app.route('/admin/update_classroom', methods=['POST'])
@login_required
def update_classroom():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    link = request.form.get('meet_link')
    is_live = 'is_live' in request.form
    
    if link and not is_valid_meet_link(link):
        flash('Invalid Google Meet link. Please use https://meet.google.com/ or https://meet.new/')
        return redirect(url_for('admin_dashboard'))

    classroom = Classroom.query.first()
    if not classroom:
        classroom = Classroom(active_meet_link=link, is_live=is_live)
        db.session.add(classroom)
    else:
        classroom.active_meet_link = link
        classroom.is_live = is_live
    
    db.session.commit()
    flash('Classroom status updated')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/refresh_classroom')
@login_required
def refresh_classroom():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    classroom = Classroom.query.first()
    if classroom and classroom.active_meet_link:
        try:
            info = get_meet_info(classroom.active_meet_link)
            classroom.detected_title = info['title']
            # Optionally auto-update is_live based on scraping
            # classroom.is_live = (info['status'] == 'Online')
            db.session.commit()
            flash(f"Status refreshed: Detected '{info['title']}'")
        except Exception as e:
            flash(f"Error refreshing classroom: {str(e)}")
            print(f"Refresh classroom error: {e}")
    else:
        flash("No active classroom link to refresh")
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_meet_link', methods=['POST'])
@login_required
def add_meet_link():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    label = request.form.get('label')
    url = request.form.get('url')
    
    if url and not is_valid_meet_link(url):
        flash('Invalid Google Meet link.')
        return redirect(url_for('admin_dashboard'))
    
    new_link = MeetLink(label=label, url=url)
    db.session.add(new_link)
    db.session.commit()
    flash('Meet link added to library')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_meet_link/<int:link_id>', methods=['POST'])
@login_required
def toggle_meet_link(link_id):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    link = MeetLink.query.get_or_404(link_id)
    link.is_active = not link.is_active
    db.session.commit()
    flash(f"Link '{link.label}' status updated")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_meet_link/<int:link_id>', methods=['POST'])
@login_required
def delete_meet_link(link_id):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    link = MeetLink.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash('Meet link deleted')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_config', methods=['POST'])
@login_required
def update_config():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    max_members = request.form.get('max_members', type=int)
    if max_members is not None:
        config = SystemConfig.query.first()
        if not config:
            config = SystemConfig(max_members=max_members)
            db.session.add(config)
        else:
            config.max_members = max_members
        db.session.commit()
        flash(f'Max members updated to {max_members}')
    
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/post_question', methods=['GET', 'POST'])
@login_required
def post_question():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
        
    if request.method == 'GET':
        return render_template('post_question.html')
        
    text = request.form.get('text')
    option_a = request.form.get('option_a')
    option_b = request.form.get('option_b')
    option_c = request.form.get('option_c')
    option_d = request.form.get('option_d')
    correct_answer = request.form.get('correct_answer')
    explanation = request.form.get('explanation')
    meet_link = request.form.get('meet_link')
    time_limit = request.form.get('time_limit', 10, type=int)
    time_unit = request.form.get('time_unit', 'minutes')
    
    if time_unit == 'days':
        time_limit = time_limit * 1440 # 24 * 60
    
    image = request.files.get('image')

    image_filename = None
    if image and allowed_file(image.filename):
        image_filename = secure_filename(f"q_{datetime.now().timestamp()}_{image.filename}")
        image.save(os.path.join(app.config['QUESTION_IMAGE_FOLDER'], image_filename))
    
    if meet_link and not is_valid_meet_link(meet_link):
        flash('Invalid Google Meet link. Please use https://meet.google.com/ or https://meet.new/')
        return redirect(url_for('admin_dashboard'))

    new_question = Question(
        text=text, option_a=option_a, option_b=option_b, 
        option_c=option_c, option_d=option_d, 
        correct_answer=correct_answer, explanation=explanation, 
        meet_link=meet_link, time_limit=time_limit,
        image_file=image_filename
    )
    db.session.add(new_question)
    db.session.commit()
    flash('Question posted successfully')
    return redirect(url_for('admin_dashboard'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
    # Get all questions
    questions = Question.query.all()
    
    # Ensure all questions have metadata (defensive fix)
    for q in questions:
        if q.created_at is None: q.created_at = datetime.utcnow()
        if q.time_limit is None: q.time_limit = 10
        
    # Create a mapping of question IDs to the student's answers
    user_answers = {a.question_id: a for a in current_user.answers}
    classroom = Classroom.query.first()
    active_meet_links = MeetLink.query.filter_by(is_active=True).all()
    return render_template('student_dashboard.html', questions=questions, user_answers=user_answers, classroom=classroom, active_meet_links=active_meet_links)

@app.route('/student/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    if current_user.role != 'student':
        return redirect(url_for('admin_dashboard'))
        
    question_id = request.form.get('question_id')
    selected_option = request.form.get('selected_option')
    file = request.files.get('file')
    
    filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{current_user.username}_{datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    question = Question.query.get(question_id)
    if not question:
        flash('Question not found.')
        return redirect(url_for('student_dashboard'))
    
    # Time check (optional but recommended for strictly enforced limits)
    from datetime import timedelta
    if question.created_at and question.time_limit:
        if datetime.utcnow() > (question.created_at + timedelta(minutes=question.time_limit)):
            flash('Sorry, the time limit for this question has expired.')
            return redirect(url_for('student_dashboard'))

    is_correct = (selected_option == question.correct_answer) if selected_option else None
    
    answer = Answer(
        student_id=current_user.id,
        question_id=question_id,
        selected_option=selected_option,
        file_path=filename,
        is_correct=is_correct
    )
    db.session.add(answer)
    db.session.commit()
    flash('Submission successful')
    return redirect(url_for('student_dashboard'))

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    # Use Waitress for production serving on Windows
    from waitress import serve
    import socket
    
    # Get local IP for network access
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    # If the default method gives loopback, try harder to get the network IP
    if local_ip == '127.0.0.1':
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = '10.87.65.26' # Fallback to user's reported IP
        finally:
            s.close()

    print("\n" + "═"*50)
    print("  🚀 APTITUDE PRO IS LIVE (PRODUCTION WSGI)")
    print("  " + "═"*50)
    print(f"  SHARE THIS LINK WITH OTHERS:")
    port = int(os.environ.get('PORT', 5000))
    print(f"  👉 http://{local_ip}:{port}")
    print("  " + "═"*50 + "\n")
    
    serve(app, host='0.0.0.0', port=port)
