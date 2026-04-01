from flask import Flask, render_template, request, redirect, url_for, session
from routes.auth import auth_bp
from routes.zakat import zakat_bp
from database.db import get_db, close_db
from database.models import init_tables
from services.zakat_service import calculate_zakat
from flask_wtf.csrf import CSRFProtect
from hijri_converter import convert

import os
import pickle
import uuid
from datetime import datetime, timedelta, date
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
BASE_URL = os.getenv("BASE_URL") or "http://127.0.0.1:5000"
print("BASE_URL =", BASE_URL)

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
# ML MODEL
# -----------------------------
try:
    eligibility_model = pickle.load(open("models/eligibility_model.pkl", "rb"))
except:
    eligibility_model = None

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
# HOME
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

    # -----------------------------
    # DATES
    # -----------------------------
    today = date.today()

    try:
        from hijri_converter import convert
        hijri_today = convert.Gregorian(today.year, today.month, today.day).to_hijri()
    except:
        hijri_today = None

    # -----------------------------
    # LATEST ZAKAT SNAPSHOT
    # -----------------------------
    cur.execute("""
        SELECT zakat_due, zakat_due_date, created_at
        FROM zakat_snapshots
        WHERE user_id=%s
        ORDER BY created_at DESC
        LIMIT 1
    """,(session["user_id"],))

    snapshot = cur.fetchone()

    zakat_due = 0
    days_remaining = None
    days_remaining_lunar = None
    due_date = None
    hijri_due = None

    if snapshot and snapshot[0]:
        zakat_due = float(safe_decrypt(snapshot[0]))

        due_date = snapshot[1]
        snapshot_date = snapshot[2]

        if hasattr(due_date, "date"):
            due_date = due_date.date()

        if hasattr(snapshot_date, "date"):
            snapshot_date = snapshot_date.date()

        # Gregorian days remaining
        days_remaining = (due_date - today).days

        # Islamic (approx)
        days_passed = (today - snapshot_date).days % 354
        days_remaining_lunar = 354 - days_passed

        # Hijri due date
        try:
            from hijri_converter import convert
            hijri_due = convert.Gregorian(
                due_date.year,
                due_date.month,
                due_date.day
            ).to_hijri()
        except:
            hijri_due = None

    # -----------------------------
    # MAIN REMINDER
    # -----------------------------
    reminder_message = None

    if days_remaining is not None:
        if days_remaining <= 0:
            reminder_message = "Your Zakat is now due."
        elif days_remaining <= 30:
            reminder_message = f"Reminder: Your Zakat is due in {days_remaining} days"

    # -----------------------------
    # DONATIONS
    # -----------------------------
    cur.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM donations
        WHERE user_id=%s
        AND DATE_PART('year',created_at)=DATE_PART('year',CURRENT_DATE)
    """,(session["user_id"],))

    donated = float(cur.fetchone()[0] or 0)

    remaining_zakat = zakat_due - donated
    if remaining_zakat < 0:
        remaining_zakat = 0

    monthly_recommendation = round(zakat_due / 12, 2) if zakat_due else 0

    # -----------------------------
    # HISTORY (FIXED)
    # -----------------------------
    cur.execute("""
        SELECT income,savings,debts,gold,created_at
        FROM financial_history
        WHERE user_id=%s
        ORDER BY created_at DESC
    """,(session["user_id"],))

    history_rows = cur.fetchall()

    history = []
    for row in history_rows:
        history.append({
            "income": safe_decrypt(row[0]),
            "savings": safe_decrypt(row[1]),
            "debts": safe_decrypt(row[2]),
            "gold": safe_decrypt(row[3]),
            "created_at": row[4]
        })

    cur.execute("""
        SELECT result,explanation,created_at
        FROM zakat_results
        WHERE user_id=%s
        ORDER BY created_at DESC
    """,(session["user_id"],))

    results_rows = cur.fetchall()

    results = []
    for row in results_rows:
        results.append({
            "result": row[0],
            "explanation": row[1],
            "created_at": row[2]
        })

    combined = list(zip(history, results))

    # -----------------------------
    # RENDER
    # -----------------------------
    return render_template(
        "dashboard.html",
        username=session["username"],
        zakat_due=zakat_due,
        donated=donated,
        remaining_zakat=remaining_zakat,
        monthly_recommendation=monthly_recommendation,
        days_remaining=days_remaining,
        days_remaining_lunar=days_remaining_lunar,
        today=today,
        hijri_today=hijri_today,
        due_date=due_date,
        hijri_due=hijri_due,
        reminder_message=reminder_message,
        combined=combined
    )
# -----------------------------
# ELIGIBILITY
# -----------------------------
@app.route("/eligibility", methods=["GET","POST"])
def eligibility():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    result = None
    breakdown = None

    if request.method == "POST":
        try:

            data = {
                "zakat_rate": 0.025,
                "nisab_basis": request.form.get("nisab_basis","gold"),
                "gold_price_per_gram": float(request.form.get("gold_price_per_gram") or 65),
                "silver_price_per_gram": float(request.form.get("silver_price_per_gram") or 0.75),

                "cash_on_hand": float(request.form.get("cash_on_hand") or 0),
                "bank_accounts": float(request.form.get("bank_accounts") or 0),
                "gold_grams": float(request.form.get("gold_grams") or 0),
                "silver_grams": float(request.form.get("silver_grams") or 0),
                "stocks": float(request.form.get("stocks") or 0),
                "investments": float(request.form.get("investments") or 0),
                "crypto": float(request.form.get("crypto") or 0),
                "business_inventory": float(request.form.get("business_inventory") or 0),
                "receivables": float(request.form.get("receivables") or 0),
                "land_value": float(request.form.get("land_value") or 0),

                "short_term_debts": float(request.form.get("short_term_debts") or 0),
                "bills_taxes_due": float(request.form.get("bills_taxes_due") or 0),
                "business_payables": float(request.form.get("business_payables") or 0),

        
                "monthly_savings": float(request.form.get("monthly_savings") or 0),
            }

            z = calculate_zakat(data)

            result = "Zakat is Required" if z.is_above_nisab else "Zakat is Not Required"

            breakdown = {
                "assets_total": z.assets_total,
                "debts_total": z.debts_total,
                "net_zakatable": z.net_zakatable,
                "nisab": z.nisab,
                "zakat_due": z.zakat_due
            }

            zakat_due_date = datetime.today() + timedelta(days=354)

            db = get_db()
            cur = db.cursor()

            # -----------------------------
            # SAVE SNAPSHOT
            # -----------------------------
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

            # -----------------------------
            # SAVE FINANCIAL HISTORY (FIXED)
            # -----------------------------
            cur.execute("""
                INSERT INTO financial_history
                (user_id,income,savings,debts,gold)
                VALUES (%s,%s,%s,%s,%s)
            """,(
                session["user_id"],
                encrypt_value(data["monthly_savings"]),   # ✅ USE THIS FOR FORECAST
                encrypt_value(z.assets_total),
                encrypt_value(z.debts_total),
                encrypt_value(data["gold_grams"])
            ))

            # -----------------------------
            # SAVE RESULT
            # -----------------------------
            cur.execute("""
                INSERT INTO zakat_results
                (user_id,result,explanation)
                VALUES (%s,%s,%s)
            """,(
                session["user_id"],
                result,
                f"Net zakatable wealth: {round(z.net_zakatable,2)}"
            ))

            db.commit()

        except Exception as e:
            print("ERROR:", e)
            result = f"Error: {e}"

    return render_template("eligibility.html", result=result, breakdown=breakdown)
# -----------------------------
# FORECAST
# -----------------------------
@app.route("/forecast", methods=["GET", "POST"])
def forecast():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    labels = []
    income = []
    message = None

    if request.method == "POST":

        db = get_db()
        cur = db.cursor()

        cur.execute("""
        SELECT created_at, income
        FROM financial_history
        WHERE user_id=%s
        ORDER BY created_at ASC
        """, (session["user_id"],))

        rows = cur.fetchall()

        # -----------------------------
        # CASE 1: NO DATA
        # -----------------------------
        if len(rows) == 0:
            message = "No financial history available yet. Please complete a Zakat calculation first."

        # -----------------------------
        # CASE 2: ONLY 1 DATA POINT
        # -----------------------------
        elif len(rows) == 1:
            message = "More data is required to generate a meaningful forecast. Please complete additional calculations over time."

            r = rows[0]
            labels.append(r[0].strftime("%b %Y"))
            income.append(float(safe_decrypt(r[1])))

        # -----------------------------
        # CASE 3: ENOUGH DATA
        # -----------------------------
        else:
            # Load historical data
            for r in rows:
                labels.append(r[0].strftime("%b %Y"))
                income.append(float(safe_decrypt(r[1])))

            # -----------------------------
            # NEW FORECAST LOGIC (FIXED)
            # -----------------------------
            last = income[-1]

            # use last monthly saving as prediction driver
            monthly_saving = income[-1]

            for i in range(1, 6):
                future = last + (monthly_saving * i)
                income.append(round(future, 2))

                future_date = datetime.today() + timedelta(days=30 * i)
                labels.append(future_date.strftime("%b %Y"))

    return render_template(
        "forecast.html",
        labels=labels,
        income=income,
        message=message
    )
# -----------------------------
# DONATE
# -----------------------------
@app.route("/donate", methods=["GET", "POST"])
def donate():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    db = get_db()
    cur = db.cursor()

    # Load approved charities
    cur.execute("""
        SELECT id, name, description
        FROM charities
        WHERE approved = TRUE
    """)
    charities = cur.fetchall()

    if request.method == "POST":

        charity_id = request.form.get("charity")
        amount = float(request.form.get("amount"))
        payment_type = request.form.get("payment_type")

        print("🔥 STRIPE ROUTE HIT")

        # Convert to cents
        amount_cents = int(amount * 100)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],

            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": "Zakat Donation"
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }],

            mode="payment",

            success_url=BASE_URL + "/payment-success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=BASE_URL + "/donate",

            # ✅ FIXED METADATA
            metadata={
                "charity_id": charity_id,
                "payment_type": payment_type
            }
        )

        return redirect(checkout_session.url, code=303)

    return render_template("donate.html", charities=charities)
# -----------------------------
# PAYMENT SUCCESS
# -----------------------------
@app.route("/payment-success")
def payment_success():

    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    session_id = request.args.get("session_id")

    if not session_id:
        return redirect(url_for("dashboard"))

    checkout_session = stripe.checkout.Session.retrieve(session_id)

    amount = checkout_session.amount_total / 100  # cents → euros

    charity_id = checkout_session.metadata.get("charity_id")
    payment_type = checkout_session.metadata.get("payment_type")

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO donations
        (user_id, charity_id, amount, payment_type, payment_reference)
        VALUES (%s,%s,%s,%s,%s)
    """,(
        session["user_id"],
        charity_id,
        amount,
        payment_type,
        session_id
    ))

    db.commit()

    return render_template("payment_success.html", amount=amount)
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