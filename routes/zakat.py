from flask import Blueprint, request, jsonify
from flask_login import login_required
from services.zakat_service import calculate_zakat

zakat_bp = Blueprint("zakat", __name__)

@zakat_bp.route("/api/calculate-zakat", methods=["POST"])
@login_required
def calculate():
    data = request.get_json()
    result = calculate_zakat(data)
    return jsonify(result.__dict__)

@zakat_bp.route("/test-zakat")
def test_zakat():
    test_data = {
        "zakat_rate": 0.025,
        "nisab_basis": "gold",
        "gold_price_per_gram": 65,
        "silver_price_per_gram": 0.75,
        "cash_on_hand": 2000,
        "bank_accounts": 5000,
        "gold_value": 1000,
        "stocks": 2000,
        "short_term_debts": 1000
    }

    result = calculate_zakat(test_data)
    return result.__dict__
