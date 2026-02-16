from flask import Flask, render_template, request, redirect, url_for, session, flash
from routes.auth import auth_bp
from database.db import get_db, close_db
from database.models import init_tables

import pickle
import os
from cryptography.fernet import Fernet
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "your-very-secure-secret-key"

# -----------------------------
# REGISTER BLUEPRINTS
# -----------------------------
app.register_blueprint(auth_bp)


# -----------------------------
# DATABASE INIT (Flask 3 Safe)
# -----------------------------
@app.before_request
def create_tables():
    if not hasattr(app, 'db_initialized'):
        db = get_db()
        init_tables(db)
        app.db_initialized = True


@app.teardown_appcontext
def shutdown_session(exception=None):
    close_db()


# -----------------------------
# LOAD ML MODEL
# -----------------------------
ELIGIBILITY_MODEL_PATH = "models/eligibility_model.pkl"

try:
    eligibility_model = pickle.load(open(ELIGIBILITY_MODEL_PATH, "rb"))
except:
    eligibility_model = None
    print("⚠ WARNING: No ML model found. Running in demo mode.")


# -----------------------------
# ENCRYPTION SETUP
# -----------------------------
KEY_PATH = "utils/secret.key"

if os.path.exists(KEY_PATH):
    with open(KEY_PATH, "rb") as f:
        key = f.read()
else:
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)

cipher = Fernet(key)

def encrypt_value(value):
    return cipher.encrypt(str(value).encode())

def decrypt_value(token):
    return cipher.decrypt(token).decode()


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def index():
    return render_template("index.html")


# -----------------------------
# DASHBOARD + HISTORY
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()
    cur = db.cursor()

    # Load encrypted financial history
    cur.execute("""
        SELECT income, savings, debts, gold, created_at
        FROM financial_history
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session["user_id"],))
    history_rows = cur.fetchall()

    # Decrypt values
    history = []
    for row in history_rows:
        history.append({
            "income": decrypt_value(row[0]),
            "savings": decrypt_value(row[1]),
            "debts": decrypt_value(row[2]),
            "gold": decrypt_value(row[3]),
            "created_at": row[4]
        })

    # Load Zakat results
    cur.execute("""
        SELECT result, explanation, created_at
        FROM zakat_results
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session["user_id"],))
    results_rows = cur.fetchall()

    results = []
    for row in results_rows:
        results.append({
            "result": row[0],
            "explanation": row[1],
            "created_at": row[2]
        })

    # Pair items safely / avoid Jinja errors
    combined = list(zip(history, results))

    return render_template(
        "dashboard.html",
        username=session["username"],
        combined=combined
    )


# -----------------------------
# ZAKAT ELIGIBILITY (FULL LOGIC)
# -----------------------------
@app.route("/eligibility", methods=["GET", "POST"])
def eligibility():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    result = None

    if request.method == "POST":
        try:
            income = float(request.form["income"])
            savings = float(request.form["savings"])
            gold_grams = float(request.form["gold"])
            debts = float(request.form["debts"])

            # Encrypt inputs
            enc_income = encrypt_value(income)
            enc_savings = encrypt_value(savings)
            enc_debts = encrypt_value(debts)
            enc_gold = encrypt_value(gold_grams)

            db = get_db()
            cur = db.cursor()

            # Save financial history
            cur.execute("""
                INSERT INTO financial_history (user_id, income, savings, debts, gold)
                VALUES (?, ?, ?, ?, ?)
            """, (session["user_id"], enc_income, enc_savings, enc_debts, enc_gold))
            db.commit()

            # ML model prediction
            if eligibility_model:
                features = [[income, savings, gold_grams, debts]]
                prediction = eligibility_model.predict(features)[0]

                if prediction == 1:
                    result_text = "Zakat is Required"
                    explanation = "Your net assets exceed the Nisab threshold."
                else:
                    result_text = "Zakat is Not Required"
                    explanation = "Your wealth does not meet the minimum Nisab level."
            else:
                result_text = "ML Model Missing – Demo Only"
                explanation = "No AI prediction available."

            result = result_text

            # Save Zakat result
            cur.execute("""
                INSERT INTO zakat_results (user_id, result, explanation)
                VALUES (?, ?, ?)
            """, (session["user_id"], result_text, explanation))
            db.commit()

        except Exception as e:
            result = f"Error: {e}"

    return render_template("eligibility.html", result=result)


# -----------------------------
# FORECAST GRAPH
# -----------------------------
@app.route("/forecast", methods=["GET", "POST"])
def forecast():
    graph = None

    if request.method == "POST":
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
        income = [2000, 2100, 2200, 2300, 2400, 2550]

        plt.figure(figsize=(6,4))
        plt.plot(months, income, linewidth=3)
        plt.title("6-Month AI Forecast", fontsize=14)
        plt.xlabel("Month")
        plt.ylabel("Income (€)")

        png = io.BytesIO()
        plt.savefig(png, format="png", bbox_inches="tight")
        png.seek(0)
        graph = base64.b64encode(png.getvalue()).decode()

    return render_template("forecast.html", graph=graph)


# -----------------------------
# DONATION PAGE (DEMO)
# -----------------------------
@app.route("/donate", methods=["GET", "POST"])
def donate():
    confirmation = None

    if request.method == "POST":
        charity = request.form.get("charity")
        amount = request.form.get("amount")

        confirmation = f"You successfully donated €{amount} to {charity} (Demo Mode)."

    return render_template("donate.html", confirmation=confirmation)


# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


if __name__ == "__main__":
    app.run(debug=True)
