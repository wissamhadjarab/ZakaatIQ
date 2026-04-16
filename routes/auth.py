from flask import Blueprint, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db

auth_bp = Blueprint('auth', __name__)

# -----------------------------------------
# REGISTER
# -----------------------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # 
        confirm = request.form.get('confirm_password')

        if password != confirm:
            flash("Passwords do not match.")
            return redirect(url_for('auth.register'))

        hashed_pw = generate_password_hash(password)

        db = get_db()
        cur = db.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed_pw)
            )
            db.commit()
        except:
            flash("Username already exists.")
            return redirect(url_for('auth.register'))

        cur.close()

        flash("Registration successful. Please login.")
        return redirect(url_for('auth.login'))

    return render_template("register.html")


# -----------------------------------------
# LOGIN
# -----------------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = get_db()
        cur = db.cursor()

        cur.execute(
            "SELECT id, username, password, language FROM users WHERE username = %s",
            (username,)
        )
        user = cur.fetchone()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]

            
            session["lang"] = user[3] if user[3] else "en"

            cur.close()
            return redirect('/dashboard')

        cur.close()
        flash("Invalid credentials.")
        return redirect(url_for('auth.login'))

    return render_template("login.html")


# -----------------------------------------
# LOGOUT
# -----------------------------------------
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))