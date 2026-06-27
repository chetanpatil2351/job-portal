from flask import Flask, render_template, request, redirect, session
import sqlite3, os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# Database Path
def get_db():
    db_path = os.path.join(os.path.expanduser("~"), "Documents", "job_portal.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Create Tables
def create_tables():
    conn = get_db()

    conn.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT)''')

    conn.execute('''CREATE TABLE IF NOT EXISTS jobs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        wage TEXT,
        location TEXT)''')

    conn.execute('''CREATE TABLE IF NOT EXISTS applications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_name TEXT,
        job_id INTEGER)''')

    conn.commit()
    conn.close()

create_tables()

# Home
@app.route('/')
def index():
    return render_template('index.html')

# Register
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = get_db()

        hashed_password = generate_password_hash(request.form['password'])

        try:
            conn.execute(
                "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                (request.form['name'], request.form['email'], hashed_password, request.form['role'])
            )
            conn.commit()
        except:
            return "User already exists!"

        conn.close()
        return redirect('/login')

    return render_template('register.html')

# Login (FIXED 🔥)
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (request.form['email'],)
        ).fetchone()

        conn.close()

        if user:
            stored_password = user['password']
            entered_password = request.form['password']

            # ✅ Handle both hashed and old plain password
            if check_password_hash(stored_password, entered_password) or stored_password == entered_password:
                session['user'] = user['name']
                session['role'] = user['role']
                return redirect('/dashboard')

        return "Invalid Login!"

    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    return render_template('dashboard.html', role=session['role'])

# Post Job
@app.route('/post_job', methods=['GET','POST'])
def post_job():
    if session.get('role') != 'employer':
        return "Access Denied"

    if request.method == 'POST':
        conn = get_db()
        conn.execute(
            "INSERT INTO jobs VALUES (NULL,?,?,?,?)",
            (request.form['title'], request.form['description'],
             request.form['wage'], request.form['location'])
        )
        conn.commit()
        conn.close()
        return redirect('/jobs')

    return render_template('post_job.html')

# Jobs + Search
@app.route('/jobs')
def jobs():
    search = request.args.get('search', '')
    conn = get_db()

    if search:
        jobs = conn.execute(
            "SELECT * FROM jobs WHERE location LIKE ?",
            ('%' + search + '%',)
        ).fetchall()
    else:
        jobs = conn.execute("SELECT * FROM jobs").fetchall()

    conn.close()
    return render_template('jobs.html', jobs=jobs)

# Apply Job
@app.route('/apply/<int:id>')
def apply(id):
    if session.get('role') != 'worker':
        return "Only workers can apply!"

    conn = get_db()

    # Prevent duplicate
    check = conn.execute(
        "SELECT * FROM applications WHERE worker_name=? AND job_id=?",
        (session['user'], id)
    ).fetchone()

    if check:
        return "Already Applied!"

    conn.execute(
        "INSERT INTO applications VALUES (NULL,?,?)",
        (session['user'], id)
    )
    conn.commit()
    conn.close()

    return redirect('/jobs')

# View Applicants
@app.route('/applications')
def applications():
    if session.get('role') != 'employer':
        return "Access Denied"

    conn = get_db()
    data = conn.execute('''
        SELECT applications.worker_name, jobs.title
        FROM applications
        JOIN jobs ON jobs.id = applications.job_id
    ''').fetchall()
    conn.close()

    return render_template('applications.html', data=data)

# Profile
@app.route('/profile')
def profile():
    return render_template('profile.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Run
if __name__ == '__main__':
    app.run(debug=True)
    