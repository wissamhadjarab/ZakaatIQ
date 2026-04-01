import pandas as pd
import random

data = []

for _ in range(200):

    income = random.randint(1500, 6000)
    savings = random.randint(0, 20000)
    gold_grams = random.randint(0, 200)
    debts = random.randint(0, 10000)

    net = savings + (gold_grams * 65) - debts

    eligible = 1 if net > 5000 else 0

    data.append([income, savings, gold_grams, debts, eligible])

df = pd.DataFrame(data, columns=[
    "income", "savings", "gold_grams", "debts", "eligible"
])

df.to_csv("data/zakat_dataset.csv", index=False)

print("Dataset generated successfully!")