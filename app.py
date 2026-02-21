from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_file, send_from_directory
from pymongo import MongoClient
from bson import ObjectId
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import secrets
import csv
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

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/aptipro')
client = MongoClient(MONGO_URI)
db = client.get_database() # Get database from URI or default

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['QUESTION_IMAGE_FOLDER'], exist_ok=True)

# --- Helpers ---

def fix_id(doc):
    """Convert _id to id string for Jinja compatibility."""
    if doc and '_id' in doc:
        doc['id'] = str(doc['_id'])
    return doc

def fix_ids(docs):
    """Convert _id to id string for a list of documents."""
    return [fix_id(doc) for doc in docs]

class MongoUser(UserMixin):
    def __init__(self, user_data):
        self.data = user_data
        self.id = str(user_data['_id'])
        self.username = user_data.get('username')
        self.full_name = user_data.get('full_name')
        self.password = user_data.get('password')
        self.role = user_data.get('role', 'student')
        self.created_at = user_data.get('created_at')

    @property
    def answers(self):
        return list(db.answers.find({'student_id': self.id}))

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
    try:
        user_data = db.users.find_one({'_id': ObjectId(user_id)})
        return MongoUser(user_data) if user_data else None
    except:
        return None

# --- Initialization ---

def init_db():
    db.users.create_index("username", unique=True)
    db.answers.create_index([("student_id", 1), ("question_id", 1)])
    db.attempts.create_index([("student_id", 1), ("question_id", 1)], unique=True)
    
    # Initialize Classroom
    if not db.classroom.find_one():
        db.classroom.insert_one({
            'active_meet_link': 'https://meet.google.com/',
            'detected_title': 'Official Classroom',
            'is_live': False,
            'updated_at': datetime.utcnow()
        })
    
    # Check for default admin
    if db.users.count_documents({'role': 'admin'}) == 0:
        db.users.insert_one({
            'username': 'admin',
            'full_name': 'Administrator',
            'password': generate_password_hash('admin123'),
            'role': 'admin',
            'created_at': datetime.utcnow()
        })
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
        user_data = db.users.find_one({'username': username})
        
        if user_data and check_password_hash(user_data['password'], password):
            login_user(MongoUser(user_data))
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
        
        # Hardcoded high limit since admin configuration was removed
        max_members = 500
        current_members = db.users.count_documents({'role': 'student'})
        
        if current_members >= max_members:
            flash(f'Registration limit reached ({max_members} members).')
            return redirect(url_for('register'))

        if db.users.find_one({'username': username}):
            flash('Username already exists')
            return redirect(url_for('register'))
            
        hashed_pw = generate_password_hash(password)
        new_user_data = {
            'username': username,
            'full_name': full_name,
            'password': hashed_pw,
            'role': 'student',
            'created_at': datetime.utcnow()
        }
        _id = db.users.insert_one(new_user_data).inserted_id
        new_user_data['_id'] = _id
        
        login_user(MongoUser(new_user_data))
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
    
    questions = fix_ids(list(db.questions.find().sort('created_at', -1)))
    submissions = fix_ids(list(db.answers.find().sort('submitted_at', -1).limit(10)))
    
    # Full list for count, but we could also just pass a count
    all_users = fix_ids(list(db.users.find({'role': 'student'})))
    
    # Join student data for submissions
    for s in submissions:
        student = db.users.find_one({'_id': ObjectId(s['student_id'])})
        s['student_name'] = student['full_name'] if student else 'Unknown'
        question = db.questions.find_one({'_id': ObjectId(s['question_id'])})
        s['question'] = fix_id(question) if question else {'text': 'Deleted Question'}
        
    classroom = db.classroom.find_one()
    meet_links = fix_ids(list(db.meet_links.find().sort('created_at', -1)))
    return render_template('admin_dashboard.html', 
                         questions=questions, 
                         members=all_users[:8], # Show limited on dashboard
                         results=submissions,
                         classroom=classroom,
                         meet_links=meet_links,
                         all_users=all_users)

@app.route('/admin/questions')
@login_required
def admin_questions_dashboard():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    questions = fix_ids(list(db.questions.find().sort('created_at', -1)))
    return render_template('admin_questions.html', active_questions=questions, expired_questions=[])

@app.route('/admin/submissions')
@login_required
def admin_submissions_dashboard():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    submissions = fix_ids(list(db.answers.find().sort('submitted_at', -1)))
    for s in submissions:
        student = db.users.find_one({'_id': ObjectId(s['student_id'])})
        # Template uses s.student.full_name, so we wrap student in a dot-accessible object or dict
        if student:
            s['student'] = fix_id(student)
        question = db.questions.find_one({'_id': ObjectId(s['question_id'])})
        if question:
            s['question'] = fix_id(question)
    return render_template('admin_submissions.html', results=submissions)

@app.route('/admin/members')
@login_required
def admin_members_dashboard():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    members = fix_ids(list(db.users.find({'role': 'student'})))
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
    
    db.questions.insert_one({
        'text': text, 'topic': topic, 'option_a': option_a, 'option_b': option_b, 
        'option_c': option_c, 'option_d': option_d, 'correct_answer': correct_answer, 
        'explanation': explanation, 'meet_link': meet_link, 'time_limit': time_limit,
        'image_file': image_filename, 'created_at': datetime.utcnow()
    })
    flash('Question posted!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_question/<question_id>', methods=['POST', 'GET'])
@login_required
def delete_question(question_id):
    if current_user.role == 'admin':
        db.questions.delete_one({'_id': ObjectId(question_id)})
        db.answers.delete_many({'question_id': question_id})
        db.attempts.delete_many({'question_id': question_id})
        flash('Question deleted')
    return redirect(url_for('admin_questions_dashboard'))

@app.route('/admin/edit_question/<question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    
    question = db.questions.find_one({'_id': ObjectId(question_id)})
    if not question:
        flash('Question not found')
        return redirect(url_for('admin_questions_dashboard'))
        
    if request.method == 'POST':
        text = request.form.get('text')
        topic = request.form.get('topic', '')
        option_a = request.form.get('option_a')
        option_b = request.form.get('option_b')
        option_c = request.form.get('option_c')
        option_d = request.form.get('option_d')
        correct_answer = request.form.get('correct_answer')
        explanation = request.form.get('explanation')
        time_limit = request.form.get('time_limit', 10, type=int)
        
        update_data = {
            'text': text, 'topic': topic, 'option_a': option_a, 'option_b': option_b, 
            'option_c': option_c, 'option_d': option_d, 'correct_answer': correct_answer, 
            'explanation': explanation, 'time_limit': time_limit
        }
        
        image = request.files.get('image')
        if image and image.filename:
            image_filename = secure_filename(f"q_{datetime.now().timestamp()}_{image.filename}")
            image.save(os.path.join(app.config['QUESTION_IMAGE_FOLDER'], image_filename))
            update_data['image_file'] = image_filename
            
        db.questions.update_one({'_id': ObjectId(question_id)}, {'$set': update_data})
        flash('Question updated!')
        return redirect(url_for('admin_questions_dashboard'))
        
    return render_template('edit_question.html', q=fix_id(question))

# --- Classroom / Config Routes ---

@app.route('/admin/update_classroom', methods=['POST'])
@login_required
def update_classroom():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    link = request.form.get('meet_link')
    is_live = 'is_live' in request.form
    title, _ = get_meet_info(link) if link else ("Classroom", None)
    
    db.classroom.update_one({}, {
        '$set': {
            'active_meet_link': link,
            'is_live': is_live,
            'detected_title': title,
            'updated_at': datetime.utcnow()
        }
    })
    flash('Classroom updated')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/refresh_classroom')
@login_required
def refresh_classroom():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    classroom = db.classroom.find_one()
    if classroom and classroom.get('active_meet_link'):
        title, _ = get_meet_info(classroom['active_meet_link'])
        db.classroom.update_one({}, {'$set': {'detected_title': title}})
        flash('Status refreshed')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_meet_link', methods=['POST'])
@login_required
def add_meet_link():
    if current_user.role != 'admin': return redirect(url_for('student_dashboard'))
    label = request.form.get('label')
    url = request.form.get('url')
    if is_valid_meet_link(url):
        db.meet_links.insert_one({'label': label, 'url': url, 'is_active': True, 'created_at': datetime.utcnow()})
        flash('Link added')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_meet_link/<link_id>', methods=['POST', 'GET'])
@login_required
def toggle_meet_link(link_id):
    if current_user.role == 'admin':
        link = db.meet_links.find_one({'_id': ObjectId(link_id)})
        if link:
            db.meet_links.update_one({'_id': ObjectId(link_id)}, {'$set': {'is_active': not link['is_active']}})
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_meet_link/<link_id>', methods=['POST', 'GET'])
@login_required
def delete_meet_link(link_id):
    if current_user.role == 'admin':
        db.meet_links.delete_one({'_id': ObjectId(link_id)})
    return redirect(url_for('admin_dashboard'))


# --- Student Routes ---

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student': return redirect(url_for('admin_dashboard'))
    questions = fix_ids(list(db.questions.find().sort('created_at', -1)))
    answers_list = list(db.answers.find({'student_id': current_user.id}))
    user_answers = {a['question_id']: fix_id(a) for a in answers_list}
    attempts_list = list(db.attempts.find({'student_id': current_user.id}))
    user_attempts = {a['question_id']: a['start_time'].timestamp() * 1000 for a in attempts_list}
    
    correct_count = sum(1 for a in answers_list if a.get('is_correct'))

    # Compute today's stats (based on IST midnight)
    from datetime import timezone
    today_utc_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Questions posted today
    today_questions = [q for q in questions if q.get('created_at') and q['created_at'] >= today_utc_start]
    today_question_ids = {str(q['_id']) for q in today_questions}
    
    # Answers submitted today for today's questions
    today_answers = [a for a in answers_list if a['question_id'] in today_question_ids]
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
    
    classroom = db.classroom.find_one()
    active_meet_links = fix_ids(list(db.meet_links.find({'is_active': True})))

    # Build Daily Activity Log for the last 7 days
    from datetime import timedelta
    daily_stats = []
    for i in range(6, -1, -1):  # 6 days ago → today
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
        day_end   = day_start + timedelta(days=1)
        day_label = day_start.strftime('%b %d')

        # Questions posted on this day
        day_qs = [q for q in questions if q.get('created_at') and day_start <= q['created_at'] < day_end]
        day_q_ids = {str(q['_id']) for q in day_qs}

        # Student answers for this day's questions
        day_ans = [a for a in answers_list if a['question_id'] in day_q_ids]
        day_solved = len(day_ans)
        day_total  = len(day_qs)

        if day_total == 0:
            status = 'No Questions'
        elif day_solved >= day_total:
            status = 'Complete'
        elif day_solved > 0:
            status = 'In Progress'
        else:
            status = 'Not Started'

        daily_stats.append({'date': day_label, 'total': day_total, 'solved': day_solved, 'status': status})

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
    existing = db.attempts.find_one({'student_id': current_user.id, 'question_id': question_id})
    if not existing:
        start_time = datetime.utcnow()
        db.attempts.insert_one({'student_id': current_user.id, 'question_id': question_id, 'start_time': start_time})
        return jsonify({'start_time': start_time.timestamp() * 1000})
    return jsonify({'start_time': existing['start_time'].timestamp() * 1000})

@app.route('/student/submit_answer', methods=['POST'])
@login_required
def submit_answer():
    question_id = request.form.get('question_id')
    selected_option = request.form.get('selected_option')
    file = request.files.get('file')
    question = db.questions.find_one({'_id': ObjectId(question_id)})
    if not question: return redirect(url_for('student_dashboard'))
    
    # --- Time Limit Enforcement ---
    if question.get('time_limit', 0) > 0:
        attempt = db.attempts.find_one({'student_id': current_user.id, 'question_id': question_id})
        if attempt:
            expiry_time = attempt['start_time'] + timedelta(minutes=question['time_limit'])
            if datetime.utcnow() > expiry_time:
                # Still record the attempt as incorrect/late if we want, or just block it
                # For now, let's block and notify
                flash('TIME EXPIRED: Your submission was recorded as late and could not be accepted for full marks.')
                
                # We still insert an answer record but mark it as late/expired if we want, 
                # OR just prevent the "Correct" reward. 
                # Let's just block it for now as per "solve issue".
                db.answers.insert_one({
                    'student_id': current_user.id, 'question_id': question_id, 
                    'selected_option': selected_option, 'file_path': None, 
                    'is_correct': False, # Always false if expired
                    'is_expired': True,
                    'submitted_at': datetime.utcnow()
                })
                return redirect(url_for('student_dashboard'))
    # ------------------------------

    filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{current_user.username}_{datetime.now().timestamp()}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    db.answers.insert_one({
        'student_id': current_user.id, 'question_id': question_id, 
        'selected_option': selected_option, 'file_path': filename, 
        'is_correct': (selected_option == question['correct_answer']) if selected_option else None,
        'submitted_at': datetime.utcnow()
    })

    # 🔔 Notify admin
    db.notifications.insert_one({
        'type': 'submission',
        'student_id': current_user.id,
        'student_name': current_user.full_name or current_user.username,
        'question_id': question_id,
        'question_text': (question.get('text', '')[:80] + '...') if len(question.get('text', '')) > 80 else question.get('text', ''),
        'is_correct': (selected_option == question['correct_answer']) if selected_option else None,
        'read': False,
        'created_at': datetime.utcnow()
    })

    flash('Submitted!')
    return redirect(url_for('student_dashboard'))

@app.route('/admin/notifications')
@login_required
def get_notifications():
    if current_user.role != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    notifs = list(db.notifications.find({'read': False}).sort('created_at', -1).limit(20))
    result = []
    for n in notifs:
        result.append({
            'id': str(n['_id']),
            'student_name': n.get('student_name', 'Unknown'),
            'question_text': n.get('question_text', ''),
            'is_correct': n.get('is_correct'),
            'created_at': n['created_at'].strftime('%H:%M') if n.get('created_at') else ''
        })
    return jsonify({'notifications': result, 'count': len(result)})

@app.route('/admin/notifications/mark_read', methods=['POST'])
@login_required
def mark_notifications_read():
    if current_user.role != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    db.notifications.update_many({'read': False}, {'$set': {'read': True}})
    return jsonify({'ok': True})

@app.route('/admin/export/submissions')
@login_required
def export_submissions():
    if current_user.role != 'admin':
        return redirect(url_for('student_dashboard'))
    answers = list(db.answers.find().sort('submitted_at', -1))
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Username', 'Question', 'Result', 'Submitted At'])
    for ans in answers:
        student = db.users.find_one({'_id': ObjectId(ans['student_id'])}) if ans.get('student_id') else None
        question = db.questions.find_one({'_id': ObjectId(ans['question_id'])}) if ans.get('question_id') else None
        writer.writerow([
            student.get('full_name', 'N/A') if student else 'Deleted User',
            student.get('username', 'N/A') if student else 'N/A',
            (question.get('text', 'N/A')[:80] + '...') if question and len(question.get('text','')) > 80 else (question.get('text', 'N/A') if question else 'Deleted Question'),
            'PASS' if ans.get('is_correct') else 'FAIL',
            ans.get('submitted_at').strftime('%Y-%m-%d %H:%M') if ans.get('submitted_at') else 'N/A'
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
    users = list(db.users.find({'role': 'student'}))
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Full Name', 'Username', 'Role', 'Registration Date'])
    for user in users:
        writer.writerow([
            user.get('full_name', 'N/A'),
            user.get('username', 'N/A'),
            user.get('role', 'student').upper(),
            user.get('created_at').strftime('%Y-%m-%d') if user.get('created_at') else 'Legacy Record'
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
