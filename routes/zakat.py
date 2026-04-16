from flask import Blueprint, render_template, request, redirect, url_for, session
from services.zakat_service import calculate_zakat
from database.db import get_db
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import os

zakat_bp = Blueprint("zakat", __name__)

FERNET_KEY = os.environ.get("FERNET_KEY")
cipher = Fernet(FERNET_KEY.encode())

def encrypt_value(value):
    return cipher.encrypt(str(value).encode())

# =========================
# ELIGIBILITY (FIXED FULL)
# =========================
@zakat_bp.route("/eligibility", methods=["GET","POST"])
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

            # SAVE SNAPSHOT
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

            # SAVE HISTORY
            cur.execute("""
                INSERT INTO financial_history
                (user_id,income,savings,debts,gold)
                VALUES (%s,%s,%s,%s,%s)
            """,(
                session["user_id"],
                encrypt_value(data["monthly_savings"]),
                encrypt_value(z.assets_total),
                encrypt_value(z.debts_total),
                encrypt_value(data["gold_grams"])
            ))

            # SAVE RESULT
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