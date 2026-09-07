import warnings
warnings.filterwarnings('ignore')

import cv2
import mediapipe as mp
import csv
import os
import sys
import numpy as np

# 1. Action Name (Command line arg or interactive prompt)
if len(sys.argv) > 1:
    ACTION_NAME = sys.argv[1].strip()
else:
    default_name = "Drinking"
    user_input = input(f"Enter action name to record (e.g., Drinking, Typing, Walking, ShakingHands) [default: {default_name}]: ").strip()
    ACTION_NAME = user_input if user_input else default_name

# 2. Initialize MediaPipe Pose
try:
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
except AttributeError:
    import mediapipe.python.solutions.pose as mp_pose
    import mediapipe.python.solutions.drawing_utils as mp_drawing

pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# 3. Setup CSV File in data/ directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
csv_file = os.path.join(DATA_DIR, 'dataset.csv')

# Start Webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not access webcam.")
    sys.exit(1)

WINDOW_NAME = 'ARIA - Data Collector'
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

print("=" * 60)
print(f"Data Collection for Action: '{ACTION_NAME}'")
print("Controls:")
print("  [SPACEBAR] : START / PAUSE recording")
print("  [F]        : Toggle Fullscreen")
print("  [Q / ESC]  : SAVE & QUIT")
print("=" * 60)

is_recording = False
recorded_rows = []

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Flip horizontally for natural mirror view
    frame = cv2.flip(frame, 1)

    # Convert to RGB for MediaPipe
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image_rgb.flags.writeable = False
    results = pose.process(image_rgb)

    # Draw skeleton
    if results.pose_landmarks:
        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        
        # If recording is active, capture the landmarks
        if is_recording:
            try:
                pose_data = results.pose_landmarks.landmark
                row = list(np.array([[lm.x, lm.y, lm.z, lm.visibility] for lm in pose_data]).flatten())
                row.insert(0, ACTION_NAME)
                recorded_rows.append(row)
            except Exception:
                pass

    # UI Overlay Banner
    if is_recording:
        # Red bar for recording
        cv2.rectangle(frame, (10, 10), (560, 90), (0, 0, 180), -1)
        cv2.rectangle(frame, (10, 10), (560, 90), (0, 255, 255), 2)
        cv2.putText(frame, f"[REC] Recording: {ACTION_NAME}", (20, 42), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.80, (255, 255, 255), 2)
        cv2.putText(frame, f"Frames: {len(recorded_rows)} / ~200 | SPACE: pause | F: fullscreen | Q: save", 
                    (20, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (240, 240, 240), 2)
    else:
        # Dark gray/black bar for standby
        cv2.rectangle(frame, (10, 10), (560, 90), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, 10), (560, 90), (0, 255, 0), 2)
        cv2.putText(frame, f"[STANDBY] Action: {ACTION_NAME}", (20, 42), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.80, (0, 255, 255), 2)
        cv2.putText(frame, f"Press SPACEBAR to record ({len(recorded_rows)} saved) | F: fullscreen | Q: quit", 
                    (20, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 128), 2)

    cv2.imshow(WINDOW_NAME, frame)
    key = cv2.waitKey(10) & 0xFF

    # Toggle recording with SPACEBAR
    if key == 32:  # SPACEBAR
        is_recording = not is_recording
        state_str = "STARTED" if is_recording else "PAUSED"
        print(f"[{state_str}] Recording '{ACTION_NAME}'. Total frames: {len(recorded_rows)}")

    if key in [ord('f'), ord('F')]:
        cur_prop = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
        new_prop = cv2.WINDOW_NORMAL if cur_prop == cv2.WINDOW_FULLSCREEN else cv2.WINDOW_FULLSCREEN
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, new_prop)

    # Quit and Save with 'q' or ESC
    if key in [ord('q'), 27]:
        break

cap.release()
cv2.destroyAllWindows()

# Save collected frames to CSV
if recorded_rows:
    file_exists = os.path.isfile(csv_file)
    with open(csv_file, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            headers = ['class'] + [f'{coord}{i}' for i in range(1, 34) for coord in ('x', 'y', 'z', 'v')]
            writer.writerow(headers)
        writer.writerows(recorded_rows)
    print(f"\n[✓] Saved {len(recorded_rows)} frames for '{ACTION_NAME}' to '{csv_file}'.")
else:
    print("\n[!] No frames recorded. Nothing was saved to dataset.csv.")