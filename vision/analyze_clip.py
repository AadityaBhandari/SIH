import warnings
warnings.filterwarnings('ignore')

import os
import time
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import joblib
from collections import deque

# Paths and Model Setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
MODEL_DIR = os.path.join(BASE_DIR, 'models')
MODEL_FILE = os.path.join(MODEL_DIR, 'pose_classifier.pkl')
if not os.path.isfile(MODEL_FILE):
    MODEL_FILE = os.path.join(SCRIPT_DIR, 'pose_classifier.pkl')
if not os.path.isfile(MODEL_FILE):
    MODEL_FILE = os.path.join(BASE_DIR, 'pose_classifier.pkl')

if os.path.isfile(MODEL_FILE):
    model = joblib.load(MODEL_FILE)
    print(f"Loaded trained classifier: {MODEL_FILE}")
else:
    model = None
    print(f"Note: '{MODEL_FILE}' not found. Running in Posture & Angle Analysis mode.")
    print("Train a model using 'python train_model.py' to enable AI action classification.\n")

# MediaPipe Pose Initialization
try:
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
except AttributeError:
    import mediapipe.python.solutions.pose as mp_pose
    import mediapipe.python.solutions.drawing_utils as mp_drawing

pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# YOLOv8-nano Object Detector for Human-Object Interaction (HOI)
YOLO_FILE = os.path.join(MODEL_DIR, 'yolov8n.pt')
if not os.path.isfile(YOLO_FILE):
    YOLO_FILE = os.path.join(BASE_DIR, 'yolov8n.pt')

try:
    from ultralytics import YOLO
    yolo_detector = YOLO(YOLO_FILE)
    print(f"Loaded YOLOv8 Object Detector for HOI: {YOLO_FILE}")
except Exception as e:
    yolo_detector = None
    print(f"Note: YOLOv8 not loaded ({e}). Running in pose-only mode.")

RECORD_DURATION = 5.0  # seconds per analyzed video clip
WINDOW_NAME = 'ARIA - Pose Clip Analyzer'

VESSEL_CLASSES = {'bottle', 'cup', 'wine glass', 'bowl', 'vase'}
CONSOLE_CLASSES = {'keyboard', 'laptop', 'cell phone'}
TARGET_OBJECTS = VESSEL_CLASSES | CONSOLE_CLASSES

ACTION_ABBR = {
    'Walking': 'Wlk',
    'Typing': 'Typ',
    'Drinking': 'Drk',
    'ShakingHands': 'Shk',
    'Idle': 'Idl',
    'HandsUp': 'Hnd'
}

def calculate_angle(a, b, c):
    """Calculates angle ABC in degrees (vertex at b)."""
    pt_a = np.array([a.x, a.y])
    pt_b = np.array([b.x, b.y])
    pt_c = np.array([c.x, c.y])
    radians = np.arctan2(pt_c[1] - pt_b[1], pt_c[0] - pt_b[0]) - np.arctan2(pt_a[1] - pt_b[1], pt_a[0] - pt_b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180.0:
        angle = 360.0 - angle
    return angle

def count_stride_cycles(y_series, min_amp=0.012):
    """
    Counts periodic peak-to-trough stride cycles in vertical shoulder position.
    Real walking creates rhythmic peaks and valleys (reversals) with minimum amplitude.
    """
    if len(y_series) < 10:
        return 0
    y = np.array(y_series)
    y_centered = y - np.mean(y)

    extrema = []
    for i in range(1, len(y_centered) - 1):
        if (y_centered[i] > y_centered[i-1] and y_centered[i] > y_centered[i+1]) or \
           (y_centered[i] < y_centered[i-1] and y_centered[i] < y_centered[i+1]):
            extrema.append((i, y_centered[i]))

    if len(extrema) < 2:
        return 0

    valid_cycles = 0
    for j in range(1, len(extrema)):
        amp = abs(extrema[j][1] - extrema[j-1][1])
        time_diff = extrema[j][0] - extrema[j-1][0]
        if amp >= min_amp and 4 <= time_diff <= 18:
            valid_cycles += 1

    return valid_cycles

def calculate_body_tilt(landmarks):
    """
    Calculates physical body tilt relative to vertical gravity axis using the torso.
      0 deg   = Upright
    +90 deg   = Floating horizontal (tilted right)
    -90 deg   = Floating horizontal (tilted left)
    180 deg   = Upside-down / Inverted
    """
    left_sh = landmarks[11]
    right_sh = landmarks[12]
    left_hip = landmarks[23]
    right_hip = landmarks[24]

    mid_sh_x = (left_sh.x + right_sh.x) / 2.0
    mid_sh_y = (left_sh.y + right_sh.y) / 2.0

    # Torso vector (Mid-Hip -> Mid-Shoulder) is immune to head turns during walking
    if left_hip.visibility > 0.35 and right_hip.visibility > 0.35:
        mid_hip_x = (left_hip.x + right_hip.x) / 2.0
        mid_hip_y = (left_hip.y + right_hip.y) / 2.0
        dx = mid_sh_x - mid_hip_x
        dy = mid_sh_y - mid_hip_y
    else:
        # Fallback: Perpendicular to shoulder axis
        sh_dx = left_sh.x - right_sh.x
        sh_dy = left_sh.y - right_sh.y
        dx, dy = -sh_dy, sh_dx
        if landmarks[0].y > mid_sh_y + 0.1:
            dx, dy = -dx, -dy

    return float(np.degrees(np.arctan2(dx, -dy)))

def get_posture_label(tilt_deg):
    abs_tilt = abs(tilt_deg)
    direction = "Right" if tilt_deg > 0 else "Left"
    if abs_tilt < 25:
        return "Upright"
    elif abs_tilt < 65:
        return f"Floating Tilted ({direction})"
    elif abs_tilt < 120:
        return f"Floating Sideways ({direction})"
    else:
        return "Upside Down / Inverted"

def detect_zero_g_pose(frame, pose_detector):
    """
    Microgravity scanner: Prefers standard upright orientation (0 deg).
    Only falls back to 180/90/270 deg with strict torso visibility validation.
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose_detector.process(rgb)
    if results.pose_landmarks:
        return results, 0, frame

    def is_confident_pose(res):
        if not res or not res.pose_landmarks:
            return False
        torso_vis = [res.pose_landmarks.landmark[i].visibility for i in (11, 12, 23, 24)]
        return np.mean(torso_vis) > 0.65

    rotations = [
        (180, cv2.ROTATE_180),
        (90, cv2.ROTATE_90_CLOCKWISE),
        (270, cv2.ROTATE_90_COUNTERCLOCKWISE)
    ]
    for angle, rot_code in rotations:
        f_rot = cv2.rotate(frame, rot_code)
        res = pose_detector.process(cv2.cvtColor(f_rot, cv2.COLOR_BGR2RGB))
        if is_confident_pose(res):
            return res, angle, f_rot

    return results, 0, frame

def detect_scene_objects(frame, detector, conf=0.15):
    """
    Runs YOLOv8 object detector and returns target interactive objects.
    Sensitive threshold (conf=0.15) captures transparent bottles, cups, and lab tools.
    """
    if detector is None:
        return []
    detected = []
    try:
        yolo_res = detector(frame, imgsz=320, verbose=False, conf=conf)[0]
        for box in yolo_res.boxes:
            c_id = int(box.cls[0])
            name = detector.names[c_id]
            if name in TARGET_OBJECTS:
                bx1, by1, bx2, by2 = box.xyxy[0].cpu().numpy()
                detected.append({
                    'name': name,
                    'box': (float(bx1), float(by1), float(bx2), float(by2)),
                    'conf': float(box.conf[0])
                })
    except Exception:
        pass
    return detected

# Camera and Window Configuration
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():
    print("Error: Could not access webcam. Please check camera connection and permissions.")
    exit(1)

cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

print("=" * 60)
print("ARIA — Human Activity & Pose Clip Analyzer (SIH 26174)")
print(f"  [SPACEBAR] : Record and analyze a {int(RECORD_DURATION)}-second video clip")
print("  [F]        : Toggle Fullscreen on/off")
print("  [Q / ESC]  : Quit")
print("=" * 60)

last_analysis_summary = None

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    display_frame = frame.copy()

    # Detect and display interactive objects in standby mode
    standby_objects = detect_scene_objects(display_frame, yolo_detector, conf=0.25)
    for obj in standby_objects:
        ox1, oy1, ox2, oy2 = [int(v) for v in obj['box']]
        color = (255, 255, 0) if obj['name'] in VESSEL_CLASSES else (0, 255, 128)
        cv2.rectangle(display_frame, (ox1, oy1), (ox2, oy2), color, 2)
        cv2.putText(display_frame, f"{obj['name']} {obj['conf']*100:.0f}%",
                    (ox1, max(18, oy1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Prompt HUD
    cv2.rectangle(display_frame, (10, 10), (520, 80), (0, 0, 0), -1)
    cv2.putText(display_frame, f"Press SPACE to analyze {int(RECORD_DURATION)}-sec clip", (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
    cv2.putText(display_frame, "Press 'f' for Fullscreen | 'q' or ESC to quit", (20, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    # Previous analysis banner if available
    if last_analysis_summary:
        box_width = 470
        cv2.rectangle(display_frame, (10, 95), (box_width, 162), (25, 25, 25), -1)
        cv2.rectangle(display_frame, (10, 95), (box_width, 162), (70, 70, 70), 1)
        cv2.putText(display_frame, last_analysis_summary['title'], (20, 122),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 255), 2)
        cv2.putText(display_frame, f"Tilt: {last_analysis_summary['tilt']} | Elbow: {last_analysis_summary['angle']}",
                    (20, 148), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)

    cv2.imshow(WINDOW_NAME, display_frame)
    key = cv2.waitKey(1) & 0xFF

    if key in [ord('q'), 27]:
        break

    if key in [ord('f'), ord('F')]:
        cur_prop = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
        new_prop = cv2.WINDOW_NORMAL if cur_prop == cv2.WINDOW_FULLSCREEN else cv2.WINDOW_FULLSCREEN
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, new_prop)

    # Trigger clip recording and analysis on SPACEBAR
    if key == 32:
        print(f"\n[>>>] Recording {RECORD_DURATION}-second clip for analysis...")
        clip_all_probas = []
        clip_elbow_angles = []
        clip_tilts = []
        clip_hoi_states = []
        frames_tracked = 0
        motion_history = deque(maxlen=24)
        prev_lms = None

        start_time = time.time()
        while (time.time() - start_time) < RECORD_DURATION:
            ret, rec_frame = cap.read()
            if not ret:
                break
            rec_frame = cv2.flip(rec_frame, 1)

            results, _, rec_frame = detect_zero_g_pose(rec_frame, pose)

            time_elapsed = time.time() - start_time
            time_left = max(0.0, RECORD_DURATION - time_elapsed)

            # Detect objects for Human-Object Interaction (HOI)
            detected_objects = detect_scene_objects(rec_frame, yolo_detector, conf=0.15)

            hoi_badge_text = None
            hoi_badge_color = (0, 255, 0)

            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    rec_frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
                )
                landmarks = results.pose_landmarks.landmark
                frames_tracked += 1

                # Microgravity body tilt
                body_tilt = calculate_body_tilt(landmarks)
                clip_tilts.append(body_tilt)

                # Right elbow angle
                r_elbow = calculate_angle(landmarks[12], landmarks[14], landmarks[16])
                clip_elbow_angles.append(r_elbow)

                # =========================================================================
                # ADVANCED SCALE-INVARIANT BIOMECHANICAL & KINEMATIC ANALYSIS
                # =========================================================================
                H, W = rec_frame.shape[:2]
                lms = landmarks

                nose = np.array([lms[0].x * W, lms[0].y * H])
                mouth_x = (lms[9].x + lms[10].x) / 2.0 * W
                mouth_y = (lms[9].y + lms[10].y) / 2.0 * H
                mouth = np.array([mouth_x, mouth_y])

                l_sh = np.array([lms[11].x * W, lms[11].y * H])
                r_sh = np.array([lms[12].x * W, lms[12].y * H])
                l_hip = np.array([lms[23].x * W, lms[23].y * H])
                r_hip = np.array([lms[24].x * W, lms[24].y * H])
                l_wr = np.array([lms[15].x * W, lms[15].y * H])
                r_wr = np.array([lms[16].x * W, lms[16].y * H])

                mid_sh = (l_sh + r_sh) / 2.0
                mid_hip = (l_hip + r_hip) / 2.0

                sh_width = max(30.0, float(np.linalg.norm(l_sh - r_sh)))
                if lms[23].visibility > 0.35 and lms[24].visibility > 0.35:
                    torso_len = max(40.0, float(np.linalg.norm(mid_sh - mid_hip)))
                else:
                    torso_len = max(40.0, sh_width * 1.5)

                # 1. Torso-Normalized Hand Elevation (Positive = elevated toward mouth/chin)
                elev_l = (mid_sh[1] - l_wr[1]) / torso_len
                elev_r = (mid_sh[1] - r_wr[1]) / torso_len
                max_hand_elev = max(elev_l, elev_r)

                # 2. Hand-to-Mouth Distance normalized by torso length (Wrists & Fingertips)
                l_idx_pt = np.array([lms[19].x * W, lms[19].y * H])
                r_idx_pt = np.array([lms[20].x * W, lms[20].y * H])
                d_l_mouth = np.linalg.norm(l_wr - mouth) / torso_len
                d_r_mouth = np.linalg.norm(r_wr - mouth) / torso_len
                d_l_idx_mouth = np.linalg.norm(l_idx_pt - mouth) / torso_len
                d_r_idx_mouth = np.linalg.norm(r_idx_pt - mouth) / torso_len
                min_mouth_dist = min(d_l_mouth, d_r_mouth, d_l_idx_mouth, d_r_idx_mouth)

                # 3. Elbow flexion (Drinking arm is bent < 125 deg)
                elbow_l_deg = calculate_angle(lms[11], lms[13], lms[15])
                elbow_r_deg = calculate_angle(lms[12], lms[14], lms[16])
                min_elbow_angle = min(elbow_l_deg, elbow_r_deg)

                # 4. Bimanual Symmetry vs Unimanual Asymmetry
                wrist_diff_y = abs(l_wr[1] - r_wr[1]) / torso_len
                inter_hand_dist = np.linalg.norm(l_wr - r_wr) / torso_len

                # =========================================================================
                # SEMANTIC BODY ZONES & OBJECT-HAND BINDING (HOI)
                # =========================================================================
                # Zone A: Oral / Ingestion Zone (Nose, mouth, chin, upper clavicle)
                oral_zone_top = nose[1] - 0.40 * torso_len
                oral_zone_bot = mid_sh[1] + 0.15 * torso_len
                oral_zone_l = mid_sh[0] - 0.75 * sh_width
                oral_zone_r = mid_sh[0] + 0.75 * sh_width

                # Zone B: Workbench / Fluid Handling Zone (Chest, abdomen, table)
                bench_zone_top = mid_sh[1] + 0.15 * torso_len
                bench_zone_bot = mid_hip[1] + 0.40 * torso_len
                bench_zone_l = mid_sh[0] - 1.20 * sh_width
                bench_zone_r = mid_sh[0] + 1.20 * sh_width

                vessel_in_oral_zone = False
                vessel_in_bench_zone = False
                vessel_bound_to_hand = False
                typing_device_present = False
                tracked_vessel_name = "None"
                vessel_box_to_draw = None

                for obj in detected_objects:
                    ox1, oy1, ox2, oy2 = obj['box']
                    ocx, ocy = (ox1 + ox2) / 2.0, (oy1 + oy2) / 2.0
                    obj_name = obj['name']

                    if obj_name in VESSEL_CLASSES:
                        tracked_vessel_name = obj_name
                        d_obj_hand = min(np.linalg.norm(np.array([ocx, ocy]) - l_wr),
                                         np.linalg.norm(np.array([ocx, ocy]) - r_wr)) / torso_len
                        if d_obj_hand < 0.50:
                            vessel_bound_to_hand = True

                        if oral_zone_top <= ocy <= oral_zone_bot and oral_zone_l <= ocx <= oral_zone_r:
                            vessel_in_oral_zone = True
                            vessel_box_to_draw = (int(ox1), int(oy1), int(ox2), int(oy2),
                                                  f"[ORAL] {obj_name} {obj['conf']*100:.0f}%", (255, 255, 0))
                        elif bench_zone_top < ocy <= bench_zone_bot and bench_zone_l <= ocx <= bench_zone_r:
                            vessel_in_bench_zone = True
                            vessel_box_to_draw = (int(ox1), int(oy1), int(ox2), int(oy2),
                                                  f"[BENCH] {obj_name} {obj['conf']*100:.0f}%", (0, 165, 255))

                    elif obj_name in CONSOLE_CLASSES:
                        typing_device_present = True
                        cv2.rectangle(rec_frame, (int(ox1), int(oy1)), (int(ox2), int(oy2)), (0, 255, 128), 2)
                        cv2.putText(rec_frame, f"[CONSOLE] {obj_name}", (int(ox1), max(18, int(oy1) - 6)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 128), 1)

                if vessel_box_to_draw:
                    vx1, vy1, vx2, vy2, vlbl, vcolor = vessel_box_to_draw
                    cv2.rectangle(rec_frame, (vx1, vy1), (vx2, vy2), vcolor, 2)
                    cv2.putText(rec_frame, vlbl, (vx1, max(18, vy1 - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.52, vcolor, 2)

                # =========================================================================
                # MULTIMODAL HOI & KINEMATIC DISCRIMINATION
                # =========================================================================
                # Drinking: Oral Ingestion
                # Drinking: Oral Ingestion (strict mouth proximity & hand elevation)
                drinking_score = 0.0
                both_hands_down = (l_wr[1] > mid_sh[1] + 0.28 * torso_len) and (r_wr[1] > mid_sh[1] + 0.28 * torso_len)
                if not both_hands_down:
                    if vessel_in_oral_zone:
                        drinking_score += 0.70
                    elif vessel_bound_to_hand and max_hand_elev > 0.0:
                        drinking_score += 0.45

                    if max_hand_elev > 0.0 and min_mouth_dist < 0.28 and min_elbow_angle < 85.0:
                        drinking_score += 0.50
                    elif min_mouth_dist < 0.35 and min_elbow_angle < 95.0:
                        drinking_score += 0.20

                # Handshake / Arm Reach: Left or Right arm forward
                is_handshake_reach = (
                    ((-0.30 <= elev_l <= 0.18) and min_mouth_dist > 0.35 and (90 <= elbow_l_deg <= 170) and (lms[15].z < -0.06 or lms[13].z < -0.04 or l_wr[1] < mid_hip[1])) or
                    ((-0.30 <= elev_r <= 0.18) and min_mouth_dist > 0.35 and (90 <= elbow_r_deg <= 170) and (lms[16].z < -0.06 or lms[14].z < -0.04 or r_wr[1] < mid_hip[1]))
                )

                # Typing: Hands hovering forward at desk/chest level
                is_typing_posture = (
                    (-0.38 <= elev_l <= 0.10) and (-0.38 <= elev_r <= 0.10) and
                    (65 <= elbow_l_deg <= 140) and (65 <= elbow_r_deg <= 140) and
                    (inter_hand_dist < 1.4) and (min_mouth_dist > 0.40)
                )

                # =========================================================================
                # KINETIC MOTION & CADENCE TRACKING (Walking vs Idle)
                # =========================================================================
                curr_nose = np.array([lms[0].x, lms[0].y])
                curr_sh = np.array([(lms[11].x + lms[12].x) / 2.0, (lms[11].y + lms[12].y) / 2.0])

                if prev_lms is not None and isinstance(prev_lms, dict):
                    h_disp = float(np.linalg.norm(curr_nose - prev_lms['nose']))
                    t_disp = float(np.linalg.norm(curr_sh - prev_lms['sh']))
                else:
                    h_disp, t_disp = 0.0, 0.0
                prev_lms = {'nose': curr_nose, 'sh': curr_sh}

                has_legs = (lms[25].visibility > 0.35 and lms[26].visibility > 0.35)
                knee_diff = abs(lms[25].y - lms[26].y) if has_legs else 0.0

                motion_history.append({
                    'h_disp': h_disp,
                    't_disp': t_disp,
                    'sh_y': curr_sh[1],
                    'knee_diff': knee_diff
                })

                mean_h_disp = float(np.mean([m['h_disp'] for m in motion_history])) if motion_history else 0.0
                mean_t_disp = float(np.mean([m['t_disp'] for m in motion_history])) if motion_history else 0.0
                sh_y_history = [m['sh_y'] for m in motion_history]
                bobbing_amp = float(max(sh_y_history) - min(sh_y_history)) if len(sh_y_history) >= 6 else 0.0
                knee_cadence = float(np.std([m['knee_diff'] for m in motion_history])) if has_legs and len(motion_history) >= 6 else 0.0
                stride_cycles = count_stride_cycles(sh_y_history, min_amp=0.012)

                # Isolated head motion: waving/tilting head while sitting in chair (torso stationary)
                is_isolated_head_motion = (mean_h_disp > 2.0 * max(0.004, mean_t_disp) and mean_t_disp < 0.009)

                # Walking: Active locomotion required
                is_walking_active = (
                    not is_isolated_head_motion and
                    (max_hand_elev < -0.15) and
                    not is_handshake_reach and
                    not is_typing_posture and
                    drinking_score < 0.40 and
                    (stride_cycles >= 2 or knee_cadence >= 0.016 or (mean_t_disp >= 0.010 and bobbing_amp >= 0.024))
                )

                # Idle: Stationary, isolated head movement, or resting
                is_idle = (
                    not is_handshake_reach and
                    not is_typing_posture and
                    drinking_score < 0.40 and
                    not is_walking_active
                )

                # ML Classifier Probabilities & Contextual Fusion
                if model is not None:
                    raw_row = np.array([[lm.x, lm.y, lm.z, lm.visibility] for lm in landmarks]).flatten().reshape(1, -1)
                    if hasattr(model, 'feature_names_in_'):
                        row = pd.DataFrame(raw_row, columns=model.feature_names_in_)
                    else:
                        row = raw_row

                    probas = model.predict_proba(row)[0].copy()
                    class_list = list(model.classes_)

                    d_idx = class_list.index('Drinking') if 'Drinking' in class_list else None
                    wk_idx = class_list.index('Walking') if 'Walking' in class_list else None
                    typ_idx = class_list.index('Typing') if 'Typing' in class_list else None
                    shk_idx = class_list.index('ShakingHands') if 'ShakingHands' in class_list else None
                    idl_idx = class_list.index('Idle') if 'Idle' in class_list else None

                    # Apply Contextual Evidence
                    if d_idx is not None and drinking_score >= 0.50:
                        probas[d_idx] += 0.75
                        if wk_idx is not None: probas[wk_idx] *= 0.01
                        if shk_idx is not None: probas[shk_idx] *= 0.01
                        if typ_idx is not None: probas[typ_idx] *= 0.01
                        if idl_idx is not None: probas[idl_idx] *= 0.01
                        v_desc = f" ({tracked_vessel_name})" if tracked_vessel_name != "None" else ""
                        hoi_badge_text = f"[HOI] Drinking: Oral Ingestion{v_desc}"
                        hoi_badge_color = (255, 255, 0)

                    elif shk_idx is not None and is_handshake_reach:
                        probas[shk_idx] += 0.75
                        if d_idx is not None: probas[d_idx] *= 0.01
                        if wk_idx is not None: probas[wk_idx] *= 0.02
                        if typ_idx is not None: probas[typ_idx] *= 0.05
                        if idl_idx is not None: probas[idl_idx] *= 0.01
                        hoi_badge_text = "[HOI] Greeting: Handshake / Arm Reach"
                        hoi_badge_color = (0, 215, 255)

                    elif (typing_device_present or is_typing_posture) and typ_idx is not None:
                        probas[typ_idx] += 0.70
                        if d_idx is not None: probas[d_idx] *= 0.02
                        if wk_idx is not None: probas[wk_idx] *= 0.02
                        if idl_idx is not None: probas[idl_idx] *= 0.02
                        device_str = "Keyboard/Console Detected" if typing_device_present else "Desk/Terminal Typing"
                        hoi_badge_text = f"[HOI] Console: {device_str}"
                        hoi_badge_color = (0, 255, 128)

                    elif is_walking_active and wk_idx is not None:
                        probas[wk_idx] += 0.75
                        if idl_idx is not None: probas[idl_idx] *= 0.01
                        if d_idx is not None: probas[d_idx] *= 0.02
                        if shk_idx is not None: probas[shk_idx] *= 0.02
                        hoi_badge_text = "[HOI] Locomotion: Normal Walking"
                        hoi_badge_color = (255, 100, 100)

                    elif is_idle and idl_idx is not None:
                        probas[idl_idx] += 0.85
                        if wk_idx is not None: probas[wk_idx] *= 0.01
                        if typ_idx is not None: probas[typ_idx] *= 0.02
                        if d_idx is not None: probas[d_idx] *= 0.01
                        hoi_badge_text = "[STATUS] Astronaut Idle / Resting"
                        hoi_badge_color = (180, 180, 180)

                    # Re-normalize
                    sum_p = np.sum(probas)
                    if sum_p > 0:
                        probas = probas / sum_p

                    clip_all_probas.append(probas)

                    # Live multi-action split display on HUD
                    sorted_idx = np.argsort(probas)[::-1]
                    top_indices = [i for i in sorted_idx if probas[i] >= 0.05][:2]
                    if not top_indices:
                        top_indices = sorted_idx[:2]
                    hud_parts = [f"{model.classes_[i]}: {probas[i]*100:.0f}%" for i in top_indices]
                    hud_text = " | ".join(hud_parts)
                    cv2.putText(rec_frame, hud_text, (20, 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 255, 0), 2)

                # Live Zero-G body tilt display
                posture_lbl = get_posture_label(body_tilt)
                cv2.putText(rec_frame, f"Body: {posture_lbl} ({body_tilt:+.1f} deg)",
                            (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

                # Live HOI Telemetry Badge
                if hoi_badge_text:
                    clip_hoi_states.append(hoi_badge_text)
                    cv2.putText(rec_frame, hoi_badge_text,
                                (20, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.55, hoi_badge_color, 2)

            # Progress bar & countdown timer
            cv2.rectangle(rec_frame, (10, rec_frame.shape[0] - 60), (450, rec_frame.shape[0] - 15), (0, 0, 0), -1)
            cv2.putText(rec_frame, f"RECORDING CLIP: {time_left:.1f}s remaining",
                        (20, rec_frame.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2)

            cv2.imshow(WINDOW_NAME, rec_frame)
            cv2.waitKey(1)

        # Aggregated Clip Analysis Report
        print("=" * 45)
        print("          CLIP ANALYSIS REPORT")
        print("=" * 45)
        print(f"Total Frames Captured & Analyzed: {frames_tracked}")

        avg_tilt = float(np.mean(clip_tilts)) if clip_tilts else 0.0
        posture_summary = get_posture_label(avg_tilt)
        print(f"Body Orientation            : {posture_summary} ({avg_tilt:+.1f} deg from vertical)")

        avg_elbow = np.mean(clip_elbow_angles) if clip_elbow_angles else 0.0
        print(f"Average Right Elbow Angle   : {avg_elbow:.1f} deg")

        if clip_hoi_states:
            most_common_hoi = max(set(clip_hoi_states), key=clip_hoi_states.count)
            print(f"Human-Object Interaction    : {most_common_hoi}")
        else:
            print(f"Human-Object Interaction    : Free-Hand / Passive")

        if model is not None and clip_all_probas:
            mean_probas = np.mean(clip_all_probas, axis=0) * 100
            dominant_idx = np.argmax(mean_probas)
            dominant_action = model.classes_[dominant_idx]
            dominant_pct = mean_probas[dominant_idx]

            sorted_probas = sorted(mean_probas, reverse=True)
            if len(sorted_probas) > 1 and sorted_probas[1] >= 20.0:
                activity_state = "Transition / Mixed Activity"
            else:
                activity_state = f"Steady {dominant_action}"

            print(f"Dominant Classified Action  : {dominant_action} ({dominant_pct:.1f}%)")
            print(f"Activity Motion State       : {activity_state}")
            print("\nAction Probability Breakdown:")
            for cls, pct in zip(model.classes_, mean_probas):
                bar = "#" * int(pct / 5)
                print(f"  - {cls:15}: {pct:5.1f}%  [{bar:<20}]")

            sorted_mean_idx = np.argsort(mean_probas)[::-1]
            active_indices = [i for i in sorted_mean_idx if mean_probas[i] >= 10.0][:2]
            if not active_indices:
                active_indices = sorted_mean_idx[:2]
            summary_probs = " / ".join([
                f"{ACTION_ABBR.get(model.classes_[i], model.classes_[i][:3])}: {mean_probas[i]:.0f}%"
                for i in active_indices
            ])

            last_analysis_summary = {
                'title': f"Last: {dominant_action} ({summary_probs})",
                'angle': f"{avg_elbow:.1f} deg",
                'tilt': f"{avg_tilt:+.1f} deg [{posture_summary}]"
            }
        else:
            action_desc = "Arm Bent" if avg_elbow < 100 else "Arm Extended"
            print(f"Pose Estimate: {action_desc} (Angle: {avg_elbow:.1f} deg)")
            last_analysis_summary = {
                'title': f"Last: {action_desc}",
                'angle': f"{avg_elbow:.1f} deg",
                'tilt': f"{avg_tilt:+.1f} deg [{posture_summary}]"
            }
        print("=" * 45 + "\n")

cap.release()
cv2.destroyAllWindows()
