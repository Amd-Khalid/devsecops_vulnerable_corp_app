from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import sqlite3
import re

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_in_production' # Vulnerability: Hardcoded secret

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'username' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Basic Validation (Meets grading requirement)
        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            flash("Invalid characters in username!")
            return render_template('login.html')

        conn = get_db_connection()
        
        # INTENTIONAL VULNERABILITY: SQL Injection
        # We are concatenating strings instead of using parameterized queries
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        user = conn.execute(query).fetchone()
        conn.close()

        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect('/dashboard')
        else:
            flash('Invalid credentials')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear() # Proper session termination
    return redirect('/login')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect('/login')
        
    conn = get_db_connection()
    
    # CRUD: Create
    if request.method == 'POST':
        content = request.form['content']
        # INTENTIONAL VULNERABILITY: Stored XSS
        # The content is stored directly without sanitization
        conn.execute("INSERT INTO posts (author, content) VALUES (?, ?)", (session['username'], content))
        conn.commit()
        
    # CRUD: Read (with optional search)
    q = request.args.get('q', '').strip()
    if q:
        like = f"%{q}%"
        posts = conn.execute("SELECT * FROM posts WHERE content LIKE ? OR author LIKE ?", (like, like)).fetchall()
    else:
        posts = conn.execute("SELECT * FROM posts").fetchall()
    conn.close()
    
    return render_template('dashboard.html', posts=posts, role=session.get('role'), username=session.get('username'), q=q)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'username' not in session:
        return redirect('/login')

    conn = get_db_connection()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()

    if post is None:
        conn.close()
        abort(404)

    if session.get('username') != post['author'] and session.get('role') != 'admin':
        conn.close()
        return "Access Denied", 403

    if request.method == 'POST':
        content = request.form['content']
        conn.execute("UPDATE posts SET content = ? WHERE id = ?", (content, post_id))
        conn.commit()
        conn.close()
        return redirect('/dashboard')

    conn.close()
    return render_template('edit.html', post=post, role=session.get('role'))

@app.route('/admin')
def admin():
    # RBAC IMPLEMENTATION
    if 'username' not in session:
        return redirect('/login')
    if session.get('role') != 'admin':
        return "Access Denied: Admins Only", 403
        
    conn = get_db_connection()
    users = conn.execute("SELECT username, role FROM users").fetchall()
    conn.close()
    return render_template('admin.html', users=users)

# CRUD: Delete
@app.route('/delete/<int:post_id>')
def delete_post(post_id):
    if 'username' not in session:
        return redirect('/login')
        
    # INTENTIONAL VULNERABILITY: IDOR (Insecure Direct Object Reference)
    # The app deletes the post based on ID, but doesn't check if the current user OWNS the post!
    conn = get_db_connection()
    conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return redirect('/dashboard')

if __name__ == '__main__':
    # ssl_context='adhoc' forces Flask to generate a temporary self-signed HTTPS certificate
    app.run(host='0.0.0.0', port=5000, ssl_context='adhoc')