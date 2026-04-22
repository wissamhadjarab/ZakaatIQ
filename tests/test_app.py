import sys
import os

# Allow imports from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from services.zakat_service import calculate_zakat
from app import encrypt_value, decrypt_value, safe_decrypt


# -----------------------------
# ZAKAT ENGINE TESTS
# -----------------------------

def test_zakat_required():
    data = {
        "cash_on_hand": 10000,
        "bank_accounts": 0,
        "gold_grams": 0,
        "silver_grams": 0,
        "stocks": 0,
        "investments": 0,
        "crypto": 0,
        "business_inventory": 0,
        "receivables": 0,
        "land_value": 0,
        "short_term_debts": 0,
        "bills_taxes_due": 0,
        "business_payables": 0,
        "gold_price_per_gram": 65,
        "silver_price_per_gram": 0.75,
        "nisab_basis": "gold",
        "zakat_rate": 0.025
    }

    z = calculate_zakat(data)
    assert z.is_above_nisab is True
    assert z.zakat_due > 0


def test_zakat_not_required():
    data = {
        "cash_on_hand": 100,
        "bank_accounts": 0,
        "gold_grams": 0,
        "silver_grams": 0,
        "stocks": 0,
        "investments": 0,
        "crypto": 0,
        "business_inventory": 0,
        "receivables": 0,
        "land_value": 0,
        "short_term_debts": 0,
        "bills_taxes_due": 0,
        "business_payables": 0,
        "gold_price_per_gram": 65,
        "silver_price_per_gram": 0.75,
        "nisab_basis": "gold",
        "zakat_rate": 0.025
    }

    z = calculate_zakat(data)
    assert z.is_above_nisab is False


# -----------------------------
# ENCRYPTION TESTS
# -----------------------------

def test_encryption_decryption():
    original = "5000"

    encrypted = encrypt_value(original)
    decrypted = decrypt_value(encrypted)

    assert decrypted == original


def test_safe_decrypt_invalid():
    bad_data = b"invalid"

    result = safe_decrypt(bad_data)

    assert result == "0"


# -----------------------------
# ML MODEL TEST
# -----------------------------

def test_ml_prediction_runs():
    import pickle

    model_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'models', 'eligibility_model.pkl')
    )

    model = pickle.load(open(model_path, "rb"))

    sample = [[3000, 5000, 10, 1000]]

    prediction = model.predict(sample)

    assert prediction[0] in [0, 1]