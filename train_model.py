import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import joblib

# LOAD DATASET
df = pd.read_excel("dataset.xlsx")

# FEATURES (all 6 fields used in the form)
X = df[[
    'Attendance ',
    'Tasks Completed',
    'Communication (10)',
    'Project Score (100)'
]]

# TARGET
y = df['Final Performance']

# SCALING
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# MODEL
model = LogisticRegression(max_iter=1000)
model.fit(X_scaled, y)

# SAVE MODEL
joblib.dump(model, "model.pkl")
joblib.dump(scaler, "scaler.pkl")

print("✅ Model and Scaler Saved Successfully")
print(f"   Classes: {model.classes_}")
