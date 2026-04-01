import pickle
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix

# -----------------------------
# LOAD DATASET
# -----------------------------
# Replace this with your dataset file if you have one
data = pd.read_csv("data/zakat_dataset.csv")

# -----------------------------
# FEATURES + TARGET
# -----------------------------
X = data.drop("eligible", axis=1)
y = data["eligible"]

# -----------------------------
# TRAIN / TEST SPLIT
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# -----------------------------
# LOAD MODEL
# -----------------------------
model = pickle.load(open("models/eligibility_model.pkl", "rb"))

# -----------------------------
# PREDICTIONS
# -----------------------------
y_pred = model.predict(X_test)

# -----------------------------
# METRICS
# -----------------------------
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
cm = confusion_matrix(y_test, y_pred)

# -----------------------------
# OUTPUT
# -----------------------------
print("\n--- MODEL EVALUATION ---")
print(f"Accuracy: {accuracy:.2f}")
print(f"Precision: {precision:.2f}")
print(f"Recall: {recall:.2f}")
print("\nConfusion Matrix:")
print(cm)