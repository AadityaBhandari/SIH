import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

csv_file = os.path.join(DATA_DIR, 'dataset.csv')
if not os.path.isfile(csv_file):
    csv_file = os.path.join(BASE_DIR, 'dataset.csv')
if not os.path.isfile(csv_file):
    csv_file = os.path.join(SCRIPT_DIR, 'dataset.csv')

if not os.path.isfile(csv_file):
    print(f"Error: Could not find 'dataset.csv' in '{DATA_DIR}', '{BASE_DIR}' or '{SCRIPT_DIR}'.")
    print("Please run collect_data.py first to collect some data.")
    sys.exit(1)

# 1. Load dataset
data = pd.read_csv(csv_file)

if len(data['class'].unique()) < 2:
    print("Warning: You need data for at least 2 different actions (classes) in dataset.csv to train a classifier.")
    print(f"Currently found only: {list(data['class'].unique())}")
    sys.exit(1)

X = data.drop('class', axis=1)
y = data['class']

print(f"Original Dataset: {len(data)} samples across classes: {list(y.unique())}")

# 2. Zero-G / Microgravity Data Augmentation
# Synthetically rotate the landmarks around the body center to simulate floating at any orientation:
# Tilts: ±15°, ±30°, ±45°, ±60°, Sideways: 90°, 270°, Inverted: 180°
AUGMENT_ANGLES = [-60, -45, -30, -15, 15, 30, 45, 60, 90, 180, 270]

print(f"\n[*] [Microgravity Simulation] Cloning frames across {len(AUGMENT_ANGLES)} zero-G rotation angles...")
aug_X = [X.values]
aug_y = [y.values]

n_samples = len(X.values)
for angle in AUGMENT_ANGLES:
    theta = np.radians(angle)
    cos_t, sin_t = np.cos(theta), np.sin(theta)

    rotated_batch = np.empty_like(X.values)
    for i in range(n_samples):
        coords = X.values[i].reshape(33, 4).copy()
        # Calculate torso midpoint (shoulders: 11, 12; hips: 23, 24)
        torso_pts = coords[[11, 12, 23, 24], :2]
        cx, cy = np.mean(torso_pts, axis=0)

        # Rotate (x, y) coordinates around the body center
        dx = coords[:, 0] - cx
        dy = coords[:, 1] - cy
        coords[:, 0] = cx + dx * cos_t - dy * sin_t
        coords[:, 1] = cy + dx * sin_t + dy * cos_t

        rotated_batch[i] = coords.flatten()

    aug_X.append(rotated_batch)
    aug_y.append(y.values)

X_augmented = pd.DataFrame(np.vstack(aug_X), columns=X.columns)
y_augmented = pd.Series(np.concatenate(aug_y))

print(f"[+] Dataset expanded from {len(data)} to {len(X_augmented)} samples ({len(X_augmented)//len(data)}x augmentation)!")

# 3. Split into train & test sets
X_train, X_test, y_train, y_test = train_test_split(
    X_augmented, y_augmented, test_size=0.2, random_state=42, stratify=y_augmented
)

# 4. Train Random Forest model
print("Training zero-G resilient Random Forest classifier...")
model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
model.fit(X_train, y_train)

# 5. Evaluate
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"\nModel Accuracy on Zero-G Augmented Test Set: {acc * 100:.2f}%")
print("\nClassification Report:\n", classification_report(y_test, y_pred))

# 6. Save model to models/ directory
model_filename = os.path.join(MODEL_DIR, 'pose_classifier.pkl')
joblib.dump(model, model_filename)
print(f"[+] Successfully saved zero-G model to '{model_filename}'!")

