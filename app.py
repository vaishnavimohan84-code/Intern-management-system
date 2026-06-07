from flask import Flask, render_template, request, redirect, url_for, session, flash
import joblib, secrets, hashlib, os
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'intern_secret_key_2024'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

model  = joblib.load('model.pkl')
scaler = joblib.load('scaler.pkl')

# ─── MySQL Configuration ───────────────────────────────────────────────────────
DB_CONFIG = {
    'host':     'localhost',
    'port':     3306,
    'user':     'internapp',
    'password': 'intern123',
    'database': 'intern_ms',
}

def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

def get_cursor(conn):
    return conn.cursor(dictionary=True)

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()
def gen_pw(): return secrets.token_urlsafe(6)

# ─── Init DB ──────────────────────────────────────────────────────────────────
def init_db():
    conn = get_db()
    cur  = get_cursor(conn)

    cur.execute('''CREATE TABLE IF NOT EXISTS hr_credentials(
        id            INT AUTO_INCREMENT PRIMARY KEY,
        username      VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255),
        full_name     VARCHAR(150),
        email         VARCHAR(150),
        phone         VARCHAR(50),
        department    VARCHAR(100),
        role          VARCHAR(100),
        avatar_initials VARCHAR(5),
        bio           TEXT,
        location      VARCHAR(150),
        gender        VARCHAR(50)
    )''')

    cur.execute('SELECT id FROM hr_credentials WHERE username=%s', ('hr',))
    if not cur.fetchone():
        cur.execute('INSERT INTO hr_credentials(username,password_hash) VALUES(%s,%s)',
                    ('hr', hp('hr123')))

    cur.execute('''UPDATE hr_credentials SET
        full_name     = COALESCE(NULLIF(full_name,''),     'HR Manager'),
        email         = COALESCE(NULLIF(email,''),         'hr@company.com'),
        phone         = COALESCE(NULLIF(phone,''),         '+91 98765 43210'),
        department    = COALESCE(NULLIF(department,''),    'Human Resources'),
        role          = COALESCE(NULLIF(role,''),          'HR Manager'),
        avatar_initials=COALESCE(NULLIF(avatar_initials,''),'HR'),
        bio           = COALESCE(NULLIF(bio,''),           'Experienced HR Manager overseeing intern onboarding, performance evaluation, and career development programs.'),
        location      = COALESCE(NULLIF(location,''),      'Chennai, Tamil Nadu'),
        gender        = COALESCE(NULLIF(gender,''),        'Prefer not to say')
        WHERE username=%s''', ('hr',))

    cur.execute('''CREATE TABLE IF NOT EXISTS intern(
        id             INT AUTO_INCREMENT PRIMARY KEY,
        name           VARCHAR(150),
        department     VARCHAR(100),
        attendance     FLOAT,
        tasks          FLOAT,
        communication  FLOAT,
        project        FLOAT,
        performance    VARCHAR(50),
        password_hash  VARCHAR(255),
        password_plain VARCHAR(100),
        email          VARCHAR(150),
        phone          VARCHAR(50),
        gender         VARCHAR(50),
        location       VARCHAR(150),
        position       VARCHAR(100),
        start_date     VARCHAR(20),
        end_date       VARCHAR(20),
        skills         TEXT,
        bio            TEXT,
        photo          VARCHAR(255)
    )''')

    # Add photo column if upgrading existing DB
    try:
        cur.execute('ALTER TABLE intern ADD COLUMN photo VARCHAR(255)')
        conn.commit()
    except:
        pass

    conn.commit()
    cur.close()
    conn.close()

init_db()

# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_all_interns():
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute('SELECT * FROM intern')
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def count_perf(p):
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute('SELECT COUNT(*) AS n FROM intern WHERE performance=%s', (p,))
    n = cur.fetchone()['n']
    cur.close(); conn.close()
    return n

def get_hr():
    conn = get_db()
    cur  = get_cursor(conn)
    cur.execute('SELECT * FROM hr_credentials WHERE username=%s', ('hr',))
    row = cur.fetchone()
    cur.close(); conn.close()
    return row or {}

# ─── HR Auth ──────────────────────────────────────────────────────────────────
@app.route('/')
def login(): return render_template('login.html')

@app.route('/hr_login', methods=['POST'])
def hr_login():
    u = request.form.get('username','').strip()
    p = request.form.get('password','')
    conn = get_db(); cur = get_cursor(conn)
    cur.execute('SELECT password_hash FROM hr_credentials WHERE username=%s', (u,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row and row['password_hash'] == hp(p):
        session['role'] = 'hr'; return redirect(url_for('dashboard'))
    flash('Invalid HR credentials!','danger')
    return redirect(url_for('login'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

# ─── HR Dashboard ─────────────────────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    interns = get_all_interns()
    return render_template('dashboard.html', interns=interns, total=len(interns),
        high=count_perf('High'), medium=count_perf('Medium'), low=count_perf('Low'),
        hr=get_hr())

@app.route('/add_intern')
def add_intern():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    return render_template('add_intern.html')

@app.route('/predict', methods=['POST'])
def predict():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    name          = request.form['name']
    department    = request.form['department']
    domain        = request.form.get('domain','').strip()
    attendance    = float(request.form['attendance'])
    tasks         = float(request.form['tasks'])
    communication = float(request.form['communication'])
    project       = float(request.form['project'])
    scaled        = scaler.transform([[attendance, tasks, communication, project]])
    prediction    = model.predict(scaled)[0]
    plain         = gen_pw()
    conn = get_db(); cur = get_cursor(conn)
    cur.execute('''INSERT INTO intern(name,department,attendance,tasks,communication,
        project,performance,password_hash,password_plain,domain) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
        (name,department,attendance,tasks,communication,project,prediction,hp(plain),plain,domain))
    conn.commit(); cur.close(); conn.close()
    return render_template('prediction.html', prediction=prediction, name=name,
        department=department, domain=domain, attendance=attendance, tasks=tasks,
        communication=communication, project=project, intern_password=plain)

@app.route('/manage_interns')
def manage_interns():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    return render_template('manage_interns.html', interns=get_all_interns())

@app.route('/edit_intern/<int:id>', methods=['GET','POST'])
def edit_intern(id):
    if session.get('role') != 'hr': return redirect(url_for('login'))
    conn = get_db(); cur = get_cursor(conn)
    if request.method == 'POST':
        name          = request.form['name']
        department    = request.form['department']
        domain        = request.form.get('domain','').strip()
        attendance    = float(request.form['attendance'])
        tasks         = float(request.form['tasks'])
        communication = float(request.form['communication'])
        project       = float(request.form['project'])
        scaled        = scaler.transform([[attendance, tasks, communication, project]])
        prediction    = model.predict(scaled)[0]
        cur.execute('''UPDATE intern SET name=%s,department=%s,attendance=%s,tasks=%s,
            communication=%s,project=%s,performance=%s,domain=%s WHERE id=%s''',
            (name,department,attendance,tasks,communication,project,prediction,domain,id))
        conn.commit(); cur.close(); conn.close()
        flash(f'✅ {name} updated successfully! New performance: {prediction}','success')
        return redirect(url_for('manage_interns'))
    cur.execute('SELECT * FROM intern WHERE id=%s', (id,))
    intern = cur.fetchone()
    cur.close(); conn.close()
    if not intern:
        flash('Intern not found.','danger')
        return redirect(url_for('manage_interns'))
    return render_template('edit_intern.html', intern=intern)

@app.route('/delete_intern/<int:id>')
def delete_intern(id):
    if session.get('role') != 'hr': return redirect(url_for('login'))
    conn = get_db(); cur = get_cursor(conn)
    cur.execute('DELETE FROM intern WHERE id=%s', (id,))
    conn.commit(); cur.close(); conn.close()
    flash('Intern deleted successfully.','success')
    return redirect(url_for('manage_interns'))

@app.route('/reports')
def reports():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    return render_template('reports.html', interns=get_all_interns())

@app.route('/change_hr_password', methods=['GET','POST'])
def change_hr_password():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    if request.method == 'POST':
        cur_pw = request.form.get('current_password','')
        new    = request.form.get('new_password','')
        con    = request.form.get('confirm_password','')
        conn = get_db(); cur = get_cursor(conn)
        cur.execute('SELECT password_hash FROM hr_credentials WHERE username=%s',('hr',))
        row = cur.fetchone()
        if not row or row['password_hash'] != hp(cur_pw):
            cur.close(); conn.close()
            flash('Current password is incorrect.','danger')
            return redirect(url_for('change_hr_password'))
        if new != con:
            cur.close(); conn.close()
            flash('Passwords do not match.','danger')
            return redirect(url_for('change_hr_password'))
        if len(new) < 6:
            cur.close(); conn.close()
            flash('Minimum 6 characters required.','danger')
            return redirect(url_for('change_hr_password'))
        cur.execute('UPDATE hr_credentials SET password_hash=%s WHERE username=%s',(hp(new),'hr'))
        conn.commit(); cur.close(); conn.close()
        flash('Password updated successfully!','success')
        return redirect(url_for('hr_profile'))
    return render_template('change_hr_password.html')

# ─── HR Profile ───────────────────────────────────────────────────────────────
@app.route('/hr_profile')
def hr_profile():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    interns = get_all_interns()
    return render_template('hr_profile.html', hr=get_hr(), interns=interns,
        total=len(interns),
        high=count_perf('High'), medium=count_perf('Medium'), low=count_perf('Low'))

@app.route('/hr_profile_update', methods=['POST'])
def hr_profile_update():
    if session.get('role') != 'hr': return redirect(url_for('login'))
    full_name       = request.form.get('full_name','').strip()
    email           = request.form.get('email','').strip()
    phone           = request.form.get('phone','').strip()
    department      = request.form.get('department','').strip()
    role            = request.form.get('role','').strip()
    avatar_initials = request.form.get('avatar_initials','HR').strip().upper()[:3]
    bio             = request.form.get('bio','').strip()
    location        = request.form.get('location','').strip()
    gender          = request.form.get('gender','').strip()
    if not full_name:
        flash('Full name cannot be empty.','danger')
        return redirect(url_for('hr_profile'))
    conn = get_db(); cur = get_cursor(conn)
    cur.execute('''UPDATE hr_credentials SET
        full_name=%s, email=%s, phone=%s, department=%s, role=%s,
        avatar_initials=%s, bio=%s, location=%s, gender=%s
        WHERE username=%s''',
        (full_name, email, phone, department, role, avatar_initials, bio, location, gender, 'hr'))
    conn.commit(); cur.close(); conn.close()
    flash('✅ Profile updated successfully!','success')
    return redirect(url_for('hr_profile'))

# ─── Intern Auth ──────────────────────────────────────────────────────────────
@app.route('/intern_login')
def intern_login(): return render_template('intern_login.html')

@app.route('/intern_login_post', methods=['POST'])
def intern_login_post():
    u = request.form.get('username','').strip().lower()
    p = request.form.get('password','')
    conn = get_db(); cur = get_cursor(conn)
    cur.execute('SELECT * FROM intern WHERE LOWER(name)=%s', (u,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if row and row['password_hash'] == hp(p):
        session['role']        = 'intern'
        session['intern_id']   = row['id']
        session['intern_name'] = row['name']
        return redirect(url_for('intern_dashboard'))
    flash('Invalid credentials!','danger')
    return redirect(url_for('intern_login'))

@app.route('/intern_dashboard')
def intern_dashboard():
    if session.get('role') != 'intern': return redirect(url_for('intern_login'))
    conn = get_db(); cur = get_cursor(conn)
    cur.execute('SELECT * FROM intern WHERE id=%s', (session['intern_id'],))
    current = cur.fetchone()
    cur.close(); conn.close()
    return render_template('intern_dashboard.html',
        interns=get_all_interns(),
        current_intern=current or {},
        intern_name=session.get('intern_name'))

@app.route('/intern_profile')
def intern_profile():
    if session.get('role') != 'intern': return redirect(url_for('intern_login'))
    conn = get_db(); cur = get_cursor(conn)
    cur.execute('SELECT * FROM intern WHERE id=%s', (session['intern_id'],))
    intern = cur.fetchone()
    cur.close(); conn.close()
    return render_template('intern_profile.html', intern=intern or {},
        intern_name=session.get('intern_name'))

@app.route('/intern_profile_update', methods=['POST'])
def intern_profile_update():
    if session.get('role') != 'intern': return redirect(url_for('intern_login'))
    name       = request.form.get('name','').strip()
    department = request.form.get('department','').strip()
    email      = request.form.get('email','').strip()
    phone      = request.form.get('phone','').strip()
    gender     = request.form.get('gender','').strip()
    location   = request.form.get('location','').strip()
    skills     = request.form.get('skills','').strip()
    bio        = request.form.get('bio','').strip()
    position   = request.form.get('position','').strip()
    start_date = request.form.get('start_date','').strip()
    end_date   = request.form.get('end_date','').strip()
    domain     = request.form.get('domain','').strip()
    if not name or not department:
        flash('Name and department cannot be empty.','danger')
        return redirect(url_for('intern_profile'))

    # Handle photo upload
    photo_filename = None
    file = request.files.get('photo')
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        photo_filename = f"intern_{session['intern_id']}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))

    conn = get_db(); cur = get_cursor(conn)
    if photo_filename:
        cur.execute('''UPDATE intern SET name=%s, department=%s, email=%s, phone=%s,
            gender=%s, location=%s, skills=%s, bio=%s, position=%s, start_date=%s, end_date=%s,
            photo=%s, domain=%s WHERE id=%s''',
            (name, department, email, phone, gender, location, skills, bio,
             position, start_date, end_date, photo_filename, domain, session['intern_id']))
    else:
        cur.execute('''UPDATE intern SET name=%s, department=%s, email=%s, phone=%s,
            gender=%s, location=%s, skills=%s, bio=%s, position=%s, start_date=%s, end_date=%s,
            domain=%s WHERE id=%s''',
            (name, department, email, phone, gender, location, skills, bio,
             position, start_date, end_date, domain, session['intern_id']))
    conn.commit(); cur.close(); conn.close()
    session['intern_name'] = name
    flash('✅ Profile updated successfully!','success')
    return redirect(url_for('intern_profile'))

@app.route('/intern_overview')
def intern_overview():
    if session.get('role') != 'intern': return redirect(url_for('intern_login'))
    conn = get_db(); cur = get_cursor(conn)
    cur.execute('SELECT * FROM intern WHERE id=%s', (session['intern_id'],))
    current = cur.fetchone()
    cur.close(); conn.close()
    return render_template('intern_overview.html',
        interns=get_all_interns(),
        current_intern=current or {},
        intern_name=session.get('intern_name'))

@app.route('/change_intern_password', methods=['GET','POST'])
def change_intern_password():
    if session.get('role') != 'intern': return redirect(url_for('intern_login'))
    if request.method == 'POST':
        cur_pw = request.form.get('current_password','')
        new    = request.form.get('new_password','')
        con    = request.form.get('confirm_password','')
        conn = get_db(); cur = get_cursor(conn)
        cur.execute('SELECT password_hash FROM intern WHERE id=%s', (session['intern_id'],))
        row = cur.fetchone()
        if not row or row['password_hash'] != hp(cur_pw):
            cur.close(); conn.close()
            flash('Current password is incorrect.','danger')
            return redirect(url_for('change_intern_password'))
        if new != con:
            cur.close(); conn.close()
            flash('Passwords do not match.','danger')
            return redirect(url_for('change_intern_password'))
        if len(new) < 6:
            cur.close(); conn.close()
            flash('Minimum 6 characters required.','danger')
            return redirect(url_for('change_intern_password'))
        cur.execute('UPDATE intern SET password_hash=%s, password_plain=%s WHERE id=%s',
                    (hp(new), new, session['intern_id']))
        conn.commit(); cur.close(); conn.close()
        flash('✅ Password updated successfully!','success')
        return redirect(url_for('change_intern_password'))
    return render_template('change_intern_password.html')

@app.route('/intern_report')
def intern_report():
    if session.get('role') != 'intern': return redirect(url_for('intern_login'))
    conn = get_db(); cur = get_cursor(conn)
    cur.execute('SELECT * FROM intern WHERE id=%s', (session['intern_id'],))
    current = cur.fetchone()
    cur.close(); conn.close()
    return render_template('intern_report.html',
        interns=get_all_interns(),
        current_intern=current or {},
        intern_name=session.get('intern_name'))

if __name__ == '__main__':
    app.run(debug=True)
