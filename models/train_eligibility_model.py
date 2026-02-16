import requests
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeClassifier
import pickle

# ---------------------------------------
# LIVE GOLD & SILVER PRICES USING GOLDAPI.IO
# ---------------------------------------

GOLD_API_KEY = "goldapi-a77fy7smi9hhlww-io"   # WORKING KEY

def get_live_gold_price_eur():
    url = "https://www.goldapi.io/api/XAU/EUR"
    headers = {"x-access-token": GOLD_API_KEY}
    
    try:
        r = requests.get(url, headers=headers).json()
        if "price_gram_24k" not in r:
            raise Exception(r)
        return r["price_gram_24k"]  # Gold €/g
    
    except Exception as e:
        print("⚠ GOLD API error:", e)
        print("Using fallback gold price: 60 €/g")
        return 60.0

def get_live_silver_price_eur():
    url = "https://www.goldapi.io/api/XAG/EUR"
    headers = {"x-access-token": GOLD_API_KEY}
    
    try:
        r = requests.get(url, headers=headers).json()
        if "price_gram_24k" not in r:
            raise Exception(r)
        return r["price_gram_24k"]  # Silver €/g
    
    except Exception as e:
        print("⚠ SILVER API error:", e)
        print("Using fallback silver price: 0.70 €/g")
        return 0.70


gold_price_per_gram = get_live_gold_price_eur()
silver_price_per_gram = get_live_silver_price_eur()

print("Live Gold Price (€/g):", gold_price_per_gram)
print("Live Silver Price (€/g):", silver_price_per_gram)

# ---------------------------------------
# NISAB CALCULATION (Silver-based)
# ---------------------------------------

SILVER_NISAB_GRAMS = 612.36
NISAB = SILVER_NISAB_GRAMS * silver_price_per_gram

print("Nisab (Euro):", NISAB)

# ---------------------------------------
# GENERATE SYNTHETIC FINANCIAL DATA
# ---------------------------------------

N = 6000
np.random.seed(42)

income = np.random.randint(300, 10000, N)
savings = np.random.randint(0, 30000, N)
gold_grams = np.random.randint(0, 300, N)
debts = np.random.randint(0, 12000, N)

zakat_required = []

for i in range(N):
    gold_value = gold_grams[i] * gold_price_per_gram
    total = savings[i] + gold_value + income[i] - debts[i]

    zakat_required.append(1 if total >= NISAB else 0)

df = pd.DataFrame({
    "income": income,
    "savings": savings,
    "gold_grams": gold_grams,
    "debts": debts,
    "zakat_required": zakat_required
})

# ---------------------------------------
# TRAIN MODEL
# ---------------------------------------

X = df[["income", "savings", "gold_grams", "debts"]]
y = df["zakat_required"]

model = DecisionTreeClassifier(max_depth=6)
model.fit(X, y)

print("Model trained with REAL Islamic values using live prices.")

# ---------------------------------------
# SAVE MODEL
# ---------------------------------------

with open("eligibility_model.pkl", "wb") as f:
    pickle.dump(model, f)

print("eligibility_model.pkl created successfully.")
