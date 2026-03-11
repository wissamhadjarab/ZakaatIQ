from flask import Flask, render_template, request, redirect, url_for, session
from routes.auth import auth_bp
from routes.zakat import zakat_bp
from database.db import get_db, close_db
from database.models import init_tables
from services.zakat_service import calculate_zakat
from flask_wtf.csrf import CSRFProtect

import os
import pickle
import io
import base64
import uuid
from datetime import datetime, timedelta, date
from cryptography.fernet import Fernet
from dotenv import load_dotenv

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# -----------------------------
# LOAD ENV VARIABLES
# -----------------------------
load_dotenv()

# -----------------------------
# APP CONFIG
# -----------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False
)

csrf = CSRFProtect(app)

# -----------------------------
# REGISTER BLUEPRINTS
# -----------------------------
app.register_blueprint(auth_bp)
app.register_blueprint(zakat_bp)

# -----------------------------
# DATABASE INIT
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
    print("⚠ WARNING: No ML model found.")

# -----------------------------
# ENCRYPTION
# -----------------------------
FERNET_KEY = os.environ.get("FERNET_KEY")
cipher = Fernet(FERNET_KEY.encode())

def encrypt_value(value):
    return cipher.encrypt(str(value).encode())

def decrypt_value(token):
    if token is None:
        return ""
    if isinstance(token, memoryview):
        token = token.tobytes()
    return cipher.decrypt(token).decode()

def safe_decrypt(token):
    try:
        return decrypt_value(token)
    except:
        return "0"

# -----------------------------
# HOME / LANDING
# -----------------------------
@app.route("/")
def index():
    return render_template("mission.html")

@app.route("/home")
def home():
    return render_template("index.html")

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()
    cur = db.cursor()

    # latest zakat calculation
    cur.execute("""
        SELECT zakat_due, zakat_due_date
        FROM zakat_snapshots
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """,(session["user_id"],))

    snapshot = cur.fetchone()

    zakat_due = 0
    days_remaining = None

    if snapshot:
        zakat_due = float(safe_decrypt(snapshot[0]))
        due_date = snapshot[1]

        if hasattr(due_date,"date"):
            due_date = due_date.date()

        days_remaining = (due_date - date.today()).days

    # total donated this year
    cur.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM donations
        WHERE user_id = %s
        AND DATE_PART('year', created_at)=DATE_PART('year', CURRENT_DATE)
    """,(session["user_id"],))

    donated = cur.fetchone()[0]

    remaining_zakat = zakat_due - donated
    if remaining_zakat < 0:
        remaining_zakat = 0

    monthly_recommendation = round(zakat_due/12,2) if zakat_due else 0

    return render_template(
        "dashboard.html",
        username=session["username"],
        zakat_due=zakat_due,
        donated=donated,
        remaining_zakat=remaining_zakat,
        monthly_recommendation=monthly_recommendation,
        days_remaining=days_remaining
    )

# -----------------------------
# ZAKAT CALCULATOR
# -----------------------------
@app.route("/eligibility", methods=["GET","POST"])
def eligibility():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    result=None
    breakdown=None

    if request.method=="POST":

        try:

            data={
                "zakat_rate":0.025,
                "nisab_basis":request.form.get("nisab_basis","gold"),
                "gold_price_per_gram":float(request.form.get("gold_price_per_gram",65)),
                "silver_price_per_gram":float(request.form.get("silver_price_per_gram",0.75)),

                "cash_on_hand":float(request.form.get("cash_on_hand",0)),
                "bank_accounts":float(request.form.get("bank_accounts",0)),
                "gold_grams":float(request.form.get("gold_grams",0)),
                "silver_grams":float(request.form.get("silver_grams",0)),
                "stocks":float(request.form.get("stocks",0)),
                "investments":float(request.form.get("investments",0)),
                "crypto":float(request.form.get("crypto",0)),
                "business_inventory":float(request.form.get("business_inventory",0)),
                "receivables":float(request.form.get("receivables",0)),
                "land_value":float(request.form.get("land_value",0)),

                "short_term_debts":float(request.form.get("short_term_debts",0)),
                "bills_taxes_due":float(request.form.get("bills_taxes_due",0)),
                "business_payables":float(request.form.get("business_payables",0)),
            }

            z=calculate_zakat(data)

            result="Zakat is Required" if z.is_above_nisab else "Zakat is Not Required"

            breakdown={
                "assets_total":z.assets_total,
                "debts_total":z.debts_total,
                "net_zakatable":z.net_zakatable,
                "nisab":z.nisab,
                "zakat_due":z.zakat_due
            }

            zakat_due_date=datetime.today()+timedelta(days=354)

            db=get_db()
            cur=db.cursor()

            cur.execute("""
                INSERT INTO zakat_snapshots
                (user_id,assets_total,debts_total,net_zakatable,nisab,zakat_due,
                nisab_basis,zakat_rate,zakat_due_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,(
                session["user_id"],
                encrypt_value(z.assets_total),
                encrypt_value(z.debts_total),
                encrypt_value(z.net_zakatable),
                encrypt_value(z.nisab),
                encrypt_value(z.zakat_due),
                data["nisab_basis"],
                data["zakat_rate"],
                zakat_due_date
            ))

            db.commit()

        except Exception as e:
            result=f"Error: {e}"

    return render_template("eligibility.html",result=result,breakdown=breakdown)

# -----------------------------
# FORECAST
# -----------------------------
@app.route("/forecast",methods=["GET","POST"])
def forecast():

    graph=False

    if request.method=="POST":

        months=["Jan","Feb","Mar","Apr","May","Jun"]
        income=[2000,2100,2200,2300,2400,2550]

        plt.figure(figsize=(6,4))
        plt.plot(months,income)
        plt.title("6 Month Income Forecast")

        png=io.BytesIO()
        plt.savefig(png,format="png")
        png.seek(0)

        graph=base64.b64encode(png.getvalue()).decode()

    return render_template("forecast.html",graph=graph)

# -----------------------------
# DONATIONS
# -----------------------------
@app.route("/donate",methods=["GET","POST"])
def donate():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    db=get_db()
    cur=db.cursor()

    cur.execute("""
        SELECT id,name,description
        FROM charities
        WHERE approved=TRUE
        ORDER BY name
    """)

    charities=cur.fetchall()
    confirmation=None

    if request.method=="POST":

        charity_id=request.form.get("charity")
        amount=float(request.form.get("amount"))
        payment_type=request.form.get("payment_type")

        payment_reference=f"STRIPE-DEMO-{uuid.uuid4().hex[:8]}"

        cur.execute("""
            INSERT INTO donations
            (user_id,charity_id,amount,payment_type,payment_reference)
            VALUES (%s,%s,%s,%s,%s)
        """,(
            session["user_id"],
            charity_id,
            amount,
            payment_type,
            payment_reference
        ))

        db.commit()

        confirmation=f"Payment successful. €{amount} donated."

    return render_template(
        "donate.html",
        charities=charities,
        confirmation=confirmation
    )

# -----------------------------
# LOGOUT
# -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))

# -----------------------------
# RUN
# -----------------------------
if __name__=="__main__":
    app.run(debug=True)