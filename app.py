from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file, send_from_directory
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

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['QUESTION_IMAGE_FOLDER'] = 'static/question_images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///aptipro.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['QUESTION_IMAGE_FOLDER'], exist_ok=True)

# --- Models ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    full_name = db.Column(db.String(120))
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='student')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    answers = db.relationship('Answer', backref='student', lazy=True)
    attempts = db.relationship('Attempt', backref='student', lazy=True)

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    answers = db.relationship('Answer', backref='question', lazy=True)
    attempts = db.relationship('Attempt', backref='question', lazy=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option = db.Column(db.String(1))
    file_path = db.Column(db.String(200))
    is_correct = db.Column(db.Boolean)
    is_expired = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('student_id', 'question_id', name='_student_question_uc'), )

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    active_meet_link = db.Column(db.String(500), default='https://meet.google.com/')
    detected_title = db.Column(db.String(200), default='Official Classroom')
    is_live = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class MeetLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100))
    url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50))
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    student_name = db.Column(db.String(120))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'))
    question_text = db.Column(db.String(200))
    is_correct = db.Column(db.Boolean)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    return User.query.get(int(user_id))

# --- Initialization ---

def init_db():
    with app.app_context():
        db.create_all()
        
        # Initialize Classroom
        if not Classroom.query.first():
            db.session.add(Classroom(
                active_meet_link='https://meet.google.com/',
                detected_title='Official Classroom',
                is_live=False
            ))
            db.session.commit()
        
        # Check for default admin
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
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        
        max_members = 500
        current_members = User.query.filter_by(role='student').count()
        
        if current_members >= max_members:
            flash(f'Registration limit reached ({max_members} members).')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        new_user = User(
            username=username,
            full_name=full_name,
            password=hashed_pw,
            role='student'
        )
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Account created!')
        return redirect(url_for('student_dashboard'))
        
    return render_template('register.html')

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
    submissions = Answer.query.order_by(Answer.submitted_at.desc()).limit(10).all()
    all_users = User.query.filter_by(role='student').all()
    
    # Process submissions for display
    results = []
    for s in submissions:
        student = User.query.get(s.student_id)
        question = Question.query.get(s.question_id)
        results.append({
            'id': s.id,
            'student_name': student.full_name if student else 'Unknown',
            'question': question if question else {'text': 'Deleted Question'},
            'submitted_at': s.submitted_at,
            'is_correct': s.is_correct
        })
        
    classroom = Classroom.query.first()
    meet_links = MeetLink.query.order_by(MeetLink.created_at.desc()).all()
    return render_template('admin_dashboard.html', 
                         questions=questions, 
                         members=all_users[:8], 
                         results=results,
                         classroom=classroom,
                         meet_links=meet_links,
                         all_users=all_users)

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
    submissions = Answer.query.order_by(Answer.submitted_at.desc()).all()
    results = []
    for s in submissions:
        student = User.query.get(s.student_id)
        question = Question.query.get(s.question_id)
        results.append({
            'id': s.id,
            'student': student,
            'question': question,
            'submitted_at': s.submitted_at,
            'selected_option': s.selected_option,
            'is_correct': s.is_correct,
            'file_path': s.file_path
        })
    return render_template('admin_submissions.html', results=results)

@app.route('/admin/members')
@login_required
def admin_members_dashboard():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    members = User.query.filter_by(role='student').all()
    return render_template('admin_members.html', all_users=members)

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
    image_filename = None
    if image and allowed_file(image.filename):
        image_filename = secure_filename(f"q_{datetime.now().timestamp()}_{image.filename}")
        image.save(os.path.join(app.config['QUESTION_IMAGE_FOLDER'], image_filename))
    
    new_q = Question(
        text=text, topic=topic, option_a=option_a, option_b=option_b, 
        option_c=option_c, option_d=option_d, correct_answer=correct_answer, 
        explanation=explanation, meet_link=meet_link, time_limit=time_limit,
        image_file=image_filename
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
            image_filename = secure_filename(f"q_{datetime.now().timestamp()}_{image.filename}")
            image.save(os.path.join(app.config['QUESTION_IMAGE_FOLDER'], image_filename))
            question.image_file = image_filename
            
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
    title, _ = get_meet_info(link) if link else ("Classroom", None)
    
    classroom = Classroom.query.first()
    if classroom:
        classroom.active_meet_link = link
        classroom.is_live = is_live
        classroom.detected_title = title
        classroom.updated_at = datetime.utcnow()
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
        link = MeetLink.query.get(link_id)
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
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    today_ist_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
    # Convert IST midnight to UTC for comparison with database timestamps
    today_utc_cutoff = today_ist_start.astimezone(pytz.utc).replace(tzinfo=None)
    
    today_questions = [q for q in questions if q.created_at >= today_utc_cutoff]
    today_question_ids = {q.id for q in today_questions}
    
    today_answers = [a for a in answers_list if a.submitted_at >= today_utc_cutoff and a.question_id in today_question_ids]
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

    return render_template('student_dashboard.html', 
                         questions=questions, user_answers=user_answers, 
                         user_attempts=user_attempts, stats=stats, 
                         classroom=classroom, active_meet_links=active_meet_links,
                         daily_stats=[],
                         server_now=datetime.utcnow().timestamp() * 1000)

@app.route('/student/start_attempt', methods=['POST'])
@login_required
def start_attempt():
    question_id = request.json.get('question_id')
    existing = Attempt.query.filter_by(student_id=current_user.id, question_id=question_id).first()
    if not existing:
        new_attempt = Attempt(student_id=current_user.id, question_id=question_id)
        db.session.add(new_attempt)
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
            if datetime.utcnow() > expiry_time:
                flash('TIME EXPIRED: Your submission was recorded as late and could not be accepted for full marks.')
                new_ans = Answer(
                    student_id=current_user.id, question_id=question_id, 
                    selected_option=selected_option, file_path=None, 
                    is_correct=False, is_expired=True
                )
                db.session.add(new_ans)
                db.session.commit()
                return redirect(url_for('student_dashboard'))

    filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{current_user.username}_{datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    is_correct = (selected_option == question.correct_answer) if selected_option else None
    new_ans = Answer(
        student_id=current_user.id, question_id=question_id, 
        selected_option=selected_option, file_path=filename, 
        is_correct=is_correct
    )
    db.session.add(new_ans)

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
        student = User.query.get(ans.student_id)
        question = Question.query.get(ans.question_id)
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

if __name__ == '__main__':
    from waitress import serve
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    port = int(os.environ.get('PORT', 5000))
    print(f"Server starting on http://{local_ip}:{port}")
    serve(app, host='0.0.0.0', port=port)
