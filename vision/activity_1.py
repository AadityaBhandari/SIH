import warnings
warnings.filterwarnings('ignore')

import os
import sys
import time
import threading
import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import joblib
from collections import deque

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Paths and Model Setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
MODEL_DIR = os.path.join(BASE_DIR, 'models')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

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
    print(f"Warning: '{MODEL_FILE}' not found. Running in heuristic mode.")

# MediaPipe Pose Initializations (Single & Multi-Person Cropper)
try:
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_hands = mp.solutions.hands
    mp_holistic = mp.solutions.holistic
    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing_styles = mp.solutions.drawing_styles
except AttributeError:
    import mediapipe.python.solutions.pose as mp_pose
    import mediapipe.python.solutions.drawing_utils as mp_drawing
    import mediapipe.python.solutions.hands as mp_hands
    import mediapipe.python.solutions.holistic as mp_holistic
    import mediapipe.python.solutions.face_mesh as mp_face_mesh
    import mediapipe.python.solutions.drawing_styles as mp_drawing_styles

holistic_detector = mp_holistic.Holistic(
    min_detection_confidence=0.45,
    min_tracking_confidence=0.45,
    model_complexity=1,
    enable_segmentation=False,
    refine_face_landmarks=False
)
pose_detector_p1 = mp_pose.Pose(min_detection_confidence=0.35, min_tracking_confidence=0.35)
pose_detector_p2 = mp_pose.Pose(min_detection_confidence=0.35, min_tracking_confidence=0.35)

# YOLOv8-nano Object & Person Detector
YOLO_FILE = os.path.join(MODEL_DIR, 'yolov8n.pt')
if not os.path.isfile(YOLO_FILE):
    YOLO_FILE = os.path.join(BASE_DIR, 'yolov8n.pt')

try:
    from ultralytics import YOLO
    yolo_detector = YOLO(YOLO_FILE)
    print(f"Loaded YOLOv8 Object & Multi-Person Detector: {YOLO_FILE}")
except Exception as e:
    yolo_detector = None
    print(f"Note: YOLOv8 not loaded ({e}).")

VESSEL_CLASSES = {'bottle', 'cup', 'wine glass', 'bowl', 'vase'}
CONSOLE_CLASSES = {'keyboard', 'laptop', 'cell phone'}
TARGET_OBJECTS = VESSEL_CLASSES | CONSOLE_CLASSES

# =============================================================================
# ACTIVITY 1: CANONICAL 4-STEP EXPERIMENT PROTOCOL
# =============================================================================
ACTIVITY_STEPS = [
    {
        'id': 1,
        'action': 'Walking',
        'title': 'Ingress / Station Approach',
        'desc': 'Walk or step in place toward the experiment bay',
        'min_dwell': 2.0
    },
    {
        'id': 2,
        'action': 'Typing',
        'title': 'Telemetry Console Login',
        'desc': 'Hands forward at terminal to calibrate parameters',
        'min_dwell': 1.2
    },
    {
        'id': 3,
        'action': 'Drinking',
        'title': 'Astronaut Hydration Check',
        'desc': 'Raise drinking container/hand to mouth',
        'min_dwell': 1.2
    },
    {
        'id': 4,
        'action': 'ShakingHands',
        'title': 'Crew Handover / Mission Greeting',
        'desc': '2-Person Handshake Clasp (or Solo Outstretched Reach)',
        'min_dwell': 1.2
    }
]

# Audio Alert System (Non-blocking Asynchronous)
audio_muted = False
last_alarm_time = 0.0

def play_sound_async(sound_type):
    global last_alarm_time
    if audio_muted or not HAS_WINSOUND:
        return

    now = time.time()
    def _run():
        try:
            if sound_type == 'chime':
                winsound.Beep(1200, 90)
                winsound.Beep(1600, 140)
            elif sound_type == 'alert':
                winsound.Beep(480, 160)
                winsound.Beep(320, 260)
            elif sound_type == 'complete':
                winsound.Beep(1000, 90)
                winsound.Beep(1300, 90)
                winsound.Beep(1750, 240)
        except Exception:
            pass

    if sound_type == 'alert':
        if now - last_alarm_time < 1.4:
            return
        last_alarm_time = now

    threading.Thread(target=_run, daemon=True).start()

def calculate_angle(a, b, c):
    pt_a = np.array([a.x if hasattr(a, 'x') else a[0], a.y if hasattr(a, 'y') else a[1]])
    pt_b = np.array([b.x if hasattr(b, 'x') else b[0], b.y if hasattr(b, 'y') else b[1]])
    pt_c = np.array([c.x if hasattr(c, 'x') else c[0], c.y if hasattr(c, 'y') else c[1]])
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
        # Human step half-period at 30fps is ~4 to 18 frames (0.13s to 0.60s per step)
        if amp >= min_amp and 4 <= time_diff <= 18:
            valid_cycles += 1

    return valid_cycles

def draw_advanced_hand_landmarks(frame, hand_landmarks, W, H, color=(255, 230, 0), label=''):
    """Draws advanced geometric hand overlay with finger joint connections, 
    knuckle markers, concentric amber orbital arcs, radial tick marks, 
    and index fingertip targeting reticle matching media_1788714748292.png."""
    if hand_landmarks is None:
        return
    pts = []
    for lm in hand_landmarks.landmark:
        px, py = int(lm.x * W), int(lm.y * H)
        pts.append((px, py))
    
    # 1. Palm base web connections (from wrist lm 0 to all MCP knuckles 5, 9, 13, 17)
    palm_indices = [0, 5, 9, 13, 17]
    for mcp in [5, 9, 13, 17]:
        cv2.line(frame, pts[0], pts[mcp], (40, 40, 40), 3)
        cv2.line(frame, pts[0], pts[mcp], color, 1)
    
    # Knuckle bridge connecting all MCP knuckles across palm
    knuckle_bridge = [(5, 9), (9, 13), (13, 17)]
    for a, b in knuckle_bridge:
        cv2.line(frame, pts[a], pts[b], (40, 40, 40), 3)
        cv2.line(frame, pts[a], pts[b], color, 1)
    
    # 2. Finger connection groups (bones)
    fingers = [
        [0, 1, 2, 3, 4],       # Thumb
        [5, 6, 7, 8],          # Index
        [9, 10, 11, 12],       # Middle
        [13, 14, 15, 16],      # Ring
        [17, 18, 19, 20],      # Pinky
    ]
    # Draw finger bones with crisp double-pass glow
    for finger in fingers:
        for i in range(len(finger) - 1):
            p1, p2 = pts[finger[i]], pts[finger[i+1]]
            cv2.line(frame, p1, p2, (20, 20, 20), 4)  # dark border
            cv2.line(frame, p1, p2, color, 2)          # cyan glowing line
    
    # 3. Palm Center & Radius Calculation
    cx = int(np.mean([pts[i][0] for i in palm_indices]))
    cy = int(np.mean([pts[i][1] for i in palm_indices]))
    palm_radius = max(30, int(np.mean([np.linalg.norm(np.array(pts[i]) - np.array([cx, cy])) for i in palm_indices])))

    # 4. Concentric Golden / Amber Orbital Arcs (Sci-Fi HUD Astrolabe dial)
    # Warm amber / gold color in BGR: (30, 180, 245)
    amber_color = (30, 180, 245)
    
    # Inner arc (radius ~1.08x palm radius) - segmented orbital arcs
    r1 = int(palm_radius * 1.08)
    cv2.ellipse(frame, (cx, cy), (r1, r1), 0, 35, 155, amber_color, 1, cv2.LINE_AA)
    cv2.ellipse(frame, (cx, cy), (r1, r1), 0, 195, 325, amber_color, 1, cv2.LINE_AA)

    # Outer arc (radius ~1.42x palm radius) - outer concentric ring
    r2 = int(palm_radius * 1.42)
    cv2.ellipse(frame, (cx, cy), (r2, r2), 0, 50, 135, amber_color, 1, cv2.LINE_AA)
    cv2.ellipse(frame, (cx, cy), (r2, r2), 0, 215, 305, amber_color, 1, cv2.LINE_AA)

    # Radial tick marks projecting outward from the outer golden arc
    for deg in [55, 80, 105, 130, 220, 245, 275, 300]:
        rad = np.deg2rad(deg)
        tx1 = int(cx + (r2 - 4) * np.cos(rad))
        ty1 = int(cy + (r2 - 4) * np.sin(rad))
        tx2 = int(cx + (r2 + 7) * np.cos(rad))
        ty2 = int(cy + (r2 + 7) * np.sin(rad))
        cv2.line(frame, (tx1, ty1), (tx2, ty2), amber_color, 1, cv2.LINE_AA)

    # 5. Joint Node Markers
    for i, (px, py) in enumerate(pts):
        if i == 8:
            # Pointing Index Fingertip Targeting Reticle (from media_1788714748292.png)
            cv2.circle(frame, (px, py), 9, (20, 20, 20), 3, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 9, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 8, color, 1, cv2.LINE_AA)
            cv2.circle(frame, (px, py), 3, (255, 255, 255), -1, cv2.LINE_AA)
        elif i in [4, 12, 16, 20]:
            # Other fingertips
            cv2.circle(frame, (px, py), 5, (20, 20, 20), -1)
            cv2.circle(frame, (px, py), 4, color, -1)
            cv2.circle(frame, (px, py), 5, (255, 255, 255), 1)
        elif i in [0, 5, 9, 13, 17]:
            # Knuckle bases & wrist
            cv2.circle(frame, (px, py), 4, (20, 20, 20), -1)
            cv2.circle(frame, (px, py), 3, color, -1)
        else:
            # Intermediate phalanx joints
            cv2.circle(frame, (px, py), 3, (20, 20, 20), -1)
            cv2.circle(frame, (px, py), 2, color, -1)
    
    # 6. Hand Label
    if label:
        cv2.putText(frame, label, (cx - 25, cy - r2 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1, cv2.LINE_AA)


# Body skeleton connections (torso, arms, and legs only — NO facial clutter)
BODY_CONNECTIONS = [
    # Torso & Shoulders
    (11, 12), (11, 23), (12, 24), (23, 24),
    # Arms
    (11, 13), (13, 15), (12, 14), (14, 16),
    # Legs
    (23, 25), (25, 27), (24, 26), (26, 28),
    # Feet
    (27, 29), (29, 31), (27, 31), (28, 30), (30, 32), (28, 32)
]

def draw_clean_body_skeleton(frame, pose_landmarks, W, H):
    """Draws sleek sci-fi body skeleton across shoulders, torso, arms, and legs.
    Leaves the astronaut's face completely clear and free of mesh lines."""
    if not pose_landmarks:
        return
    lms = pose_landmarks.landmark
    pts = {}
    for i in range(11, 33):
        lm = lms[i]
        if lm.visibility > 0.35:
            pts[i] = (int(lm.x * W), int(lm.y * H))
    
    # Dual-pass glow lines on body limbs
    for i_a, i_b in BODY_CONNECTIONS:
        if i_a in pts and i_b in pts:
            # Shadow pass
            cv2.line(frame, pts[i_a], pts[i_b], (20, 20, 20), 4, cv2.LINE_AA)
            # Glowing cyan pass
            cv2.line(frame, pts[i_a], pts[i_b], (255, 230, 0), 2, cv2.LINE_AA)
            
    # Body joint nodes
    for idx, (px, py) in pts.items():
        cv2.circle(frame, (px, py), 5, (20, 20, 20), -1, cv2.LINE_AA)
        cv2.circle(frame, (px, py), 3, (255, 230, 0), -1, cv2.LINE_AA)
        cv2.circle(frame, (px, py), 5, (255, 255, 255), 1, cv2.LINE_AA)

def detect_zero_g_pose(frame, pose_detector):
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

def process_person_crop(frame, box, pose_detector):
    """Crops person bounding box with generous margins for outstretched limbs, runs MediaPipe, and projects landmarks."""
    H, W = frame.shape[:2]
    bx1, by1, bx2, by2 = box
    bw = bx2 - bx1
    bh = by2 - by1
    pad_w = 0.32 * bw
    pad_h = 0.20 * bh

    x1 = max(0, int(bx1 - pad_w))
    y1 = max(0, int(by1 - pad_h))
    x2 = min(W, int(bx2 + pad_w))
    y2 = min(H, int(by2 + pad_h))

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0 or crop.shape[0] < 40 or crop.shape[1] < 40:
        return None, None

    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    res = pose_detector.process(rgb)
    if not res or not res.pose_landmarks:
        return None, None

    # Project coordinates to global image pixels
    crop_w = x2 - x1
    crop_h = y2 - y1
    global_pts = []
    for lm in res.pose_landmarks.landmark:
        gx = x1 + lm.x * crop_w
        gy = y1 + lm.y * crop_h
        global_pts.append({
            'x': gx, 'y': gy, 'z': lm.z, 'vis': lm.visibility,
            'norm_x': gx / W, 'norm_y': gy / H
        })
    return res.pose_landmarks, global_pts

def run_activity_1():
    global audio_muted
    WINDOW_NAME = 'ARIA - Activity 1: Bio-Payload Protocol'

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("Error: Could not access webcam.")
        return

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    print("=" * 65)
    print("        ARIA — ACTIVITY 1: SEQUENTIAL BIO-PROTOCOL")
    print("=" * 65)
    print("Steps to perform in order:")
    for s in ACTIVITY_STEPS:
        print(f"  [{s['id']}] {s['action']:<14} -> {s['title']}")
    print("-" * 65)
    print("Controls: [F] Fullscreen | [M] Mute Audio | [R] Reset | [Q / ESC] Quit")
    print("=" * 65 + "\n")

    current_step_idx = 0
    step_completed = [False] * len(ACTIVITY_STEPS)
    step_timestamps = [None] * len(ACTIVITY_STEPS)
    current_dwell = 0.0
    protocol_start_time = time.time()
    protocol_finished = False
    protocol_finish_time = None

    active_alert_text = None
    alert_display_timer = 0.0
    last_frame_time = time.time()
    smoothed_probas = None

    # Motion & Cadence Tracking Buffer for Idle vs Active Walking detection
    motion_history = deque(maxlen=24)
    prev_landmark_pts = None

    while cap.isOpened():
        now = time.time()
        dt = max(0.001, min(0.1, now - last_frame_time))
        last_frame_time = now

        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        H, W = frame.shape[:2]

        # 1. Run YOLO Multi-Person & Object Detector
        detected_people_boxes = []
        detected_vessels = []
        typing_device_present = False

        if yolo_detector is not None:
            try:
                # Use imgsz=480 and conf=0.15 for high sensitivity & separation of adjacent people
                y_res = yolo_detector(frame, imgsz=480, verbose=False, conf=0.15)[0]
                raw_people_boxes = []
                for box in y_res.boxes:
                    cls_id = int(box.cls[0])
                    name = yolo_detector.names[cls_id]
                    bx1, by1, bx2, by2 = box.xyxy[0].cpu().numpy()
                    conf_val = float(box.conf[0])
                    if cls_id == 0:  # person
                        raw_people_boxes.append((float(bx1), float(by1), float(bx2), float(by2), conf_val))
                    elif name in VESSEL_CLASSES:
                        detected_vessels.append({'name': name, 'box': (bx1, by1, bx2, by2), 'conf': conf_val})
                    elif name in CONSOLE_CLASSES:
                        typing_device_present = True

                # Filter person boxes by minimum area (ignore tiny background noise)
                valid_boxes = [b for b in raw_people_boxes if (b[2] - b[0]) * (b[3] - b[1]) > 0.020 * W * H]

                if len(valid_boxes) == 1:
                    # Exactly one person detected -> Solo Mode (DO NOT artificially split)
                    b = valid_boxes[0]
                    detected_people_boxes = [(b[0], b[1], b[2], b[3])]
                elif len(valid_boxes) >= 2:
                    # Sort by area descending to take the 2 most prominent people in bay
                    valid_boxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
                    b_a, b_b = valid_boxes[0], valid_boxes[1]

                    # Check Intersection-over-Union (IoU) to filter duplicate boxes on the same individual
                    xA = max(b_a[0], b_b[0])
                    yA = max(b_a[1], b_b[1])
                    xB = min(b_a[2], b_b[2])
                    yB = min(b_a[3], b_b[3])
                    inter_area = max(0.0, xB - xA) * max(0.0, yB - yA)
                    area_a = (b_a[2] - b_a[0]) * (b_a[3] - b_a[1])
                    area_b = (b_b[2] - b_b[0]) * (b_b[3] - b_b[1])
                    iou = inter_area / float(area_a + area_b - inter_area + 1e-6)

                    if iou > 0.50:
                        # Redundant duplicate detections of the same single person
                        b_best = b_a if b_a[4] >= b_b[4] else b_b
                        detected_people_boxes = [(b_best[0], b_best[1], b_best[2], b_best[3])]
                    else:
                        top2 = [b_a, b_b]
                        # Sort left to right
                        top2.sort(key=lambda b: (b[0] + b[2]) / 2.0)
                        detected_people_boxes = [(b[0], b[1], b[2], b[3]) for b in top2]
                elif len(valid_boxes) == 0 and len(raw_people_boxes) > 0:
                    raw_people_boxes.sort(key=lambda b: (b[2] - b[0]) * (b[3] - b[1]), reverse=True)
                    b = raw_people_boxes[0]
                    detected_people_boxes = [(b[0], b[1], b[2], b[3])]
            except Exception:
                pass

        # 2. Multi-Person vs Single-Person Tracking
        is_two_person_mode = False
        handshake_verified = False
        handshake_badge_text = None
        handshake_badge_color = (0, 215, 255)
        handshake_debug_telemetry = ""

        p1_pts = None
        p2_pts = None

        if len(detected_people_boxes) >= 2:
            b1 = detected_people_boxes[0]
            b2 = detected_people_boxes[1]

            _, p1_pts = process_person_crop(frame, b1, pose_detector_p1)
            _, p2_pts = process_person_crop(frame, b2, pose_detector_p2)

            if p1_pts is not None and p2_pts is not None:
                # Distinct individual check: ensure P1 and P2 have physically separated heads/noses
                nose_dist = abs(p1_pts[0]['x'] - p2_pts[0]['x'])
                torso_dist = abs((p1_pts[11]['x'] + p1_pts[12]['x']) / 2.0 - (p2_pts[11]['x'] + p2_pts[12]['x']) / 2.0)
                if nose_dist > 75 or torso_dist > 75:
                    is_two_person_mode = True

            if is_two_person_mode:
                # Draw bounding boxes
                cv2.rectangle(frame, (int(b1[0]), int(b1[1])), (int(b1[2]), int(b1[3])), (255, 255, 0), 2)
                cv2.rectangle(frame, (int(b2[0]), int(b2[1])), (int(b2[2]), int(b2[3])), (255, 0, 255), 2)

                # Draw Person 1 skeleton (Cyan)
                for pt in p1_pts[11:17] + p1_pts[23:25]:
                    cv2.circle(frame, (int(pt['x']), int(pt['y'])), 4, (255, 255, 0), -1)
                for i_a, i_b in [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24)]:
                    cv2.line(frame, (int(p1_pts[i_a]['x']), int(p1_pts[i_a]['y'])),
                             (int(p1_pts[i_b]['x']), int(p1_pts[i_b]['y'])), (255, 255, 0), 2)
                cv2.putText(frame, "P1 (Astronaut 1)", (int(b1[0]), max(25, int(b1[1]) - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

                # Draw Person 2 skeleton (Magenta)
                for pt in p2_pts[11:17] + p2_pts[23:25]:
                    cv2.circle(frame, (int(pt['x']), int(pt['y'])), 4, (255, 0, 255), -1)
                for i_a, i_b in [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24)]:
                    cv2.line(frame, (int(p2_pts[i_a]['x']), int(p2_pts[i_a]['y'])),
                             (int(p2_pts[i_b]['x']), int(p2_pts[i_b]['y'])), (255, 0, 255), 2)
                cv2.putText(frame, "P2 (Astronaut 2)", (int(b2[0]), max(25, int(b2[1]) - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 0, 255), 2)

                # Torso lengths & centers
                pt1_sh = np.array([(p1_pts[11]['x'] + p1_pts[12]['x']) / 2.0, (p1_pts[11]['y'] + p1_pts[12]['y']) / 2.0])
                pt1_hip = np.array([(p1_pts[23]['x'] + p1_pts[24]['x']) / 2.0, (p1_pts[23]['y'] + p1_pts[24]['y']) / 2.0])
                pt2_sh = np.array([(p2_pts[11]['x'] + p2_pts[12]['x']) / 2.0, (p2_pts[11]['y'] + p2_pts[12]['y']) / 2.0])
                pt2_hip = np.array([(p2_pts[23]['x'] + p2_pts[24]['x']) / 2.0, (p2_pts[23]['y'] + p2_pts[24]['y']) / 2.0])

                torso1_len = max(50.0, float(np.linalg.norm(pt1_sh - pt1_hip)))
                torso2_len = max(50.0, float(np.linalg.norm(pt2_sh - pt2_hip)))
                avg_torso = (torso1_len + torso2_len) / 2.0

                # Evaluate bilateral handshake clasp across all 4 wrist combinations
                # P1: right (16), left (15) | P2: right (16), left (15)
                p1_wrists = [
                    ('R', np.array([p1_pts[16]['x'], p1_pts[16]['y']]), np.array([p1_pts[20]['x'], p1_pts[20]['y']]), 12, 14, 16),
                    ('L', np.array([p1_pts[15]['x'], p1_pts[15]['y']]), np.array([p1_pts[19]['x'], p1_pts[19]['y']]), 11, 13, 15)
                ]
                p2_wrists = [
                    ('R', np.array([p2_pts[16]['x'], p2_pts[16]['y']]), np.array([p2_pts[20]['x'], p2_pts[20]['y']]), 12, 14, 16),
                    ('L', np.array([p2_pts[15]['x'], p2_pts[15]['y']]), np.array([p2_pts[19]['x'], p2_pts[19]['y']]), 11, 13, 15)
                ]

                best_clasp = None
                min_norm_dist = 999.0

                for p1_arm, w1, idx1, s1_idx, e1_idx, w1_idx in p1_wrists:
                    for p2_arm, w2, idx2, s2_idx, e2_idx, w2_idx in p2_wrists:
                        d_wr = np.linalg.norm(w1 - w2)
                        d_idx = np.linalg.norm(idx1 - idx2)
                        pair_dist = min(d_wr, d_idx)
                        norm_dist = pair_dist / avg_torso

                        sh1_pt = np.array([p1_pts[s1_idx]['x'], p1_pts[s1_idx]['y']])
                        el1_pt = np.array([p1_pts[e1_idx]['x'], p1_pts[e1_idx]['y']])
                        ang1 = calculate_angle(sh1_pt, el1_pt, w1)

                        sh2_pt = np.array([p2_pts[s2_idx]['x'], p2_pts[s2_idx]['y']])
                        el2_pt = np.array([p2_pts[e2_idx]['x'], p2_pts[e2_idx]['y']])
                        ang2 = calculate_angle(sh2_pt, el2_pt, w2)

                        if norm_dist < min_norm_dist:
                            min_norm_dist = norm_dist
                            best_clasp = {
                                'w1': w1, 'w2': w2, 'norm_dist': norm_dist,
                                'ang1': ang1, 'ang2': ang2,
                                'p1_arm': p1_arm, 'p2_arm': p2_arm
                            }

                if best_clasp is not None:
                    c = best_clasp
                    handshake_debug_telemetry = f"Hands Dist: {c['norm_dist']:.2f}x | Ang1: {c['ang1']:.0f}° | Ang2: {c['ang2']:.0f}°"

                    mid_clasp = (c['w1'] + c['w2']) / 2.0
                    p1_cx = (b1[0] + b1[2]) / 2.0
                    p2_cx = (b2[0] + b2[2]) / 2.0
                    is_between = (min(p1_cx, p2_cx) - 0.25 * avg_torso <= mid_clasp[0] <= max(p1_cx, p2_cx) + 0.25 * avg_torso)

                    min_sh_y = min(pt1_sh[1], pt2_sh[1])
                    max_hip_y = max(pt1_hip[1], pt2_hip[1])
                    is_handshake_height = (min_sh_y - 0.25 * avg_torso <= mid_clasp[1] <= max_hip_y + 0.35 * avg_torso)

                    if (c['norm_dist'] < 0.72 and
                        65 <= c['ang1'] <= 175 and
                        65 <= c['ang2'] <= 175 and
                        is_between and
                        is_handshake_height):
                        handshake_verified = True
                        cv2.line(frame, (int(c['w1'][0]), int(c['w1'][1])), (int(c['w2'][0]), int(c['w2'][1])), (0, 215, 255), 4)
                        mc = mid_clasp.astype(int)
                        cv2.circle(frame, (mc[0], mc[1]), 16, (0, 255, 255), -1)
                        cv2.circle(frame, (mc[0], mc[1]), 22, (0, 215, 255), 3)
                        cv2.circle(frame, (mc[0], mc[1]), 30, (0, 165, 255), 2)
                        handshake_badge_text = "[COLLABORATION] 2-Person Crew Handover Verified!"

        # Fallback to single-person detector if not in 2-person mode
        detected_action = "Unknown"
        action_conf = 0.0
        is_drinking_posture = False
        is_typing_posture = False
        is_walking_posture = False

        # Run Holistic detector for combined pose+hands+face
        if not is_two_person_mode:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            holistic_results = holistic_detector.process(rgb_frame)
        else:
            holistic_results = None

        if holistic_results is not None and holistic_results.pose_landmarks and not is_two_person_mode:
            # Draw clean body skeleton (limbs & torso only — keeps face completely unobstructed)
            draw_clean_body_skeleton(frame, holistic_results.pose_landmarks, W, H)
            
            # Draw advanced hand overlays
            draw_advanced_hand_landmarks(frame, holistic_results.left_hand_landmarks, W, H, 
                                        color=(0, 255, 180), label='L-HAND')
            draw_advanced_hand_landmarks(frame, holistic_results.right_hand_landmarks, W, H,
                                        color=(255, 200, 0), label='R-HAND')
            
            lms = holistic_results.pose_landmarks.landmark

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

            elev_l = (mid_sh[1] - l_wr[1]) / torso_len
            elev_r = (mid_sh[1] - r_wr[1]) / torso_len
            max_hand_elev = max(elev_l, elev_r)

            l_idx_pt = np.array([lms[19].x * W, lms[19].y * H])
            r_idx_pt = np.array([lms[20].x * W, lms[20].y * H])
            d_l_mouth = np.linalg.norm(l_wr - mouth) / torso_len
            d_r_mouth = np.linalg.norm(r_wr - mouth) / torso_len
            d_l_idx_mouth = np.linalg.norm(l_idx_pt - mouth) / torso_len
            d_r_idx_mouth = np.linalg.norm(r_idx_pt - mouth) / torso_len
            min_mouth_dist = min(d_l_mouth, d_r_mouth, d_l_idx_mouth, d_r_idx_mouth)

            l_elbow_ang = calculate_angle(lms[11], lms[13], lms[15])
            r_elbow_ang = calculate_angle(lms[12], lms[14], lms[16])
            min_elbow = min(l_elbow_ang, r_elbow_ang)

            # Check Solo Handshake Reach (Fallback - Left OR Right arm)
            is_r_reach = (
                (-0.30 <= elev_r <= 0.18) and
                (min_mouth_dist > 0.35) and
                (90 <= r_elbow_ang <= 170) and
                (lms[16].z < -0.06 or lms[14].z < -0.04 or r_wr[1] < mid_hip[1])
            )
            is_l_reach = (
                (-0.30 <= elev_l <= 0.18) and
                (min_mouth_dist > 0.35) and
                (90 <= l_elbow_ang <= 170) and
                (lms[15].z < -0.06 or lms[13].z < -0.04 or l_wr[1] < mid_hip[1])
            )
            is_solo_handshake_reach = is_r_reach or is_l_reach

            if is_solo_handshake_reach:
                handshake_verified = True
                active_wr = r_wr if is_r_reach else l_wr
                cv2.circle(frame, (int(active_wr[0]), int(active_wr[1])), 22, (0, 215, 255), 3)
                cv2.circle(frame, (int(active_wr[0]), int(active_wr[1])), 8, (0, 255, 255), -1)
                handshake_badge_text = "[SOLO GREETING] Outstretched Handshake Reach"

            # Check Oral Ingestion
            vessel_in_oral = False
            for v in detected_vessels:
                vcx, vcy = (v['box'][0] + v['box'][2]) / 2.0, (v['box'][1] + v['box'][3]) / 2.0
                if vcy < mid_sh[1] + 0.15 * torso_len and abs(vcx - mid_sh[0]) < 0.75 * sh_width:
                    vessel_in_oral = True

            # Strict drinking posture validation:
            # 1. Wrist must be raised to or above clavicle/mouth level (not resting on lap/desk)
            hand_at_oral_height = (l_wr[1] < mid_sh[1] + 0.05 * torso_len) or (r_wr[1] < mid_sh[1] + 0.05 * torso_len)
            
            # 2. Hand or vessel directly at the mouth
            hand_at_mouth_proximity = (min_mouth_dist < 0.28) or (vessel_in_oral and min_mouth_dist < 0.42)
            
            # 3. Acute elbow flexion (drinking angle)
            acute_elbow_flex = (min_elbow < 85.0)
            
            # 4. Resting exclusion: if both hands are down below mid-torso, NEVER drinking
            both_hands_down = (l_wr[1] > mid_sh[1] + 0.28 * torso_len) and (r_wr[1] > mid_sh[1] + 0.28 * torso_len)

            is_drinking_posture = (
                not both_hands_down and
                hand_at_oral_height and
                hand_at_mouth_proximity and
                acute_elbow_flex and
                max_hand_elev > 0.0
            )

            # Check Typing Posture (Console or Kinematic Desk Typing)
            inter_wrist_dist = np.linalg.norm(l_wr - r_wr) / torso_len
            is_typing_posture = (
                (-0.38 <= elev_l <= 0.10) and (-0.38 <= elev_r <= 0.10) and
                (65 <= l_elbow_ang <= 140) and (65 <= r_elbow_ang <= 140) and
                (inter_wrist_dist < 1.4) and (min_mouth_dist > 0.40)
            )

            # =================================================================
            # KINETIC MOTION TRACKING & CADENCE DISCRIMINATOR
            # =================================================================
            curr_nose = np.array([lms[0].x, lms[0].y])
            curr_sh = np.array([(lms[11].x + lms[12].x) / 2.0, (lms[11].y + lms[12].y) / 2.0])

            # Track head displacement separately from torso displacement!
            if prev_landmark_pts is not None and isinstance(prev_landmark_pts, dict):
                h_disp = float(np.linalg.norm(curr_nose - prev_landmark_pts['nose']))
                t_disp = float(np.linalg.norm(curr_sh - prev_landmark_pts['sh']))
            else:
                h_disp, t_disp = 0.0, 0.0
            prev_landmark_pts = {'nose': curr_nose, 'sh': curr_sh}

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

            # 1. Active Walking: requires genuine locomotive movement
            # - Must NOT be isolated head motion
            # - Arms not reaching for handshake, not typing, not drinking
            # - Hands relaxed below chest
            # - And either:
            #     a) Repeated cyclic stride bobbing (stride_cycles >= 2)
            #     b) OR alternating knee lift cadence (knee_cadence >= 0.016)
            #     c) OR significant whole-body locomotive displacement (mean_t_disp >= 0.010 and bobbing_amp >= 0.024)
            is_walking_active = (
                not is_isolated_head_motion and
                (max_hand_elev < -0.15) and
                not is_solo_handshake_reach and
                not is_typing_posture and
                not is_drinking_posture and
                (stride_cycles >= 2 or knee_cadence >= 0.016 or (mean_t_disp >= 0.010 and bobbing_amp >= 0.024))
            )

            # 2. Idle State: stationary OR isolated head movement OR resting
            is_idle = (
                not is_drinking_posture and
                not is_typing_posture and
                not is_solo_handshake_reach and
                not is_walking_active
            )

            # Model Prediction
            if model is not None:
                raw_row = np.array([[lm.x, lm.y, lm.z, lm.visibility] for lm in lms]).flatten().reshape(1, -1)
                if hasattr(model, 'feature_names_in_'):
                    row = pd.DataFrame(raw_row, columns=model.feature_names_in_)
                else:
                    row = raw_row

                probas = model.predict_proba(row)[0].copy()
                class_list = list(model.classes_)

                d_idx = class_list.index('Drinking') if 'Drinking' in class_list else None
                typ_idx = class_list.index('Typing') if 'Typing' in class_list else None
                wk_idx = class_list.index('Walking') if 'Walking' in class_list else None
                shk_idx = class_list.index('ShakingHands') if 'ShakingHands' in class_list else None
                idl_idx = class_list.index('Idle') if 'Idle' in class_list else None

                if (is_idle or both_hands_down) and not (is_drinking_posture or is_typing_posture or handshake_verified):
                    if idl_idx is not None: probas[idl_idx] += 0.90
                    if d_idx is not None: probas[d_idx] *= 0.001
                    if wk_idx is not None: probas[wk_idx] *= 0.001
                    if typ_idx is not None and not typing_device_present and not is_typing_posture:
                        probas[typ_idx] *= 0.01
                elif handshake_verified and shk_idx is not None:
                    probas[shk_idx] += 0.85
                    if d_idx is not None: probas[d_idx] *= 0.01
                    if wk_idx is not None: probas[wk_idx] *= 0.01
                    if idl_idx is not None: probas[idl_idx] *= 0.01
                elif is_drinking_posture and d_idx is not None:
                    probas[d_idx] += 0.80
                    if typ_idx is not None: probas[typ_idx] *= 0.01
                    if wk_idx is not None: probas[wk_idx] *= 0.01
                    if idl_idx is not None: probas[idl_idx] *= 0.01
                    if shk_idx is not None: probas[shk_idx] *= 0.01
                elif (typing_device_present or is_typing_posture) and typ_idx is not None:
                    probas[typ_idx] += 0.70
                    if d_idx is not None: probas[d_idx] *= 0.02
                    if wk_idx is not None: probas[wk_idx] *= 0.02
                    if idl_idx is not None: probas[idl_idx] *= 0.02
                elif is_walking_active and wk_idx is not None:
                    probas[wk_idx] += 0.75
                    if idl_idx is not None: probas[idl_idx] *= 0.01
                    if d_idx is not None: probas[d_idx] *= 0.02
                    if shk_idx is not None: probas[shk_idx] *= 0.02
                elif is_idle and idl_idx is not None:
                    probas[idl_idx] += 0.85
                    if wk_idx is not None: probas[wk_idx] *= 0.01
                    if typ_idx is not None: probas[typ_idx] *= 0.02
                    if d_idx is not None: probas[d_idx] *= 0.001

                sum_p = np.sum(probas)
                if sum_p > 0:
                    probas = probas / sum_p

                # Temporal smoothing filter
                if smoothed_probas is None:
                    smoothed_probas = probas.copy()
                else:
                    smoothed_probas = 0.65 * smoothed_probas + 0.35 * probas

                best_idx = int(np.argmax(smoothed_probas))
                detected_action = class_list[best_idx]
                action_conf = smoothed_probas[best_idx]

        elif is_two_person_mode:
            # In 2-person mode: prioritize collaborative handshake verification
            if handshake_verified:
                detected_action = 'ShakingHands'
                action_conf = 0.98
            elif p1_pts is not None and model is not None:
                # Classify Astronaut 1 so steps 1-3 (Walking, Typing, Drinking) work seamlessly with 2 people
                try:
                    raw_row = np.array([[pt['norm_x'], pt['norm_y'], pt['z'], pt['vis']] for pt in p1_pts]).flatten().reshape(1, -1)
                    if hasattr(model, 'feature_names_in_'):
                        row = pd.DataFrame(raw_row, columns=model.feature_names_in_)
                    else:
                        row = raw_row
                    p1_probas = model.predict_proba(row)[0].copy()
                    class_list = list(model.classes_)
                    d_idx = class_list.index('Drinking') if 'Drinking' in class_list else None
                    typ_idx = class_list.index('Typing') if 'Typing' in class_list else None
                    wk_idx = class_list.index('Walking') if 'Walking' in class_list else None

                    if vessel_in_oral and d_idx is not None:
                        p1_probas[d_idx] += 0.60
                    if typing_device_present and typ_idx is not None:
                        p1_probas[typ_idx] += 0.60

                    sum_p = np.sum(p1_probas)
                    if sum_p > 0:
                        p1_probas = p1_probas / sum_p

                    best_i = int(np.argmax(p1_probas))
                    detected_action = class_list[best_i]
                    action_conf = p1_probas[best_i]
                except Exception:
                    pass

        # =====================================================================
        # PROTOCOL STATE MACHINE & SKIP DETECTOR
        # =====================================================================
        if not protocol_finished:
            target_step = ACTIVITY_STEPS[current_step_idx]
            target_action = target_step['action']

            # Case A: Correct step being performed (Idle will NEVER match any step!)
            is_step_match = (
                (detected_action == target_action and action_conf >= 0.45 and detected_action != 'Idle') or
                (target_action == 'ShakingHands' and handshake_verified) or
                (target_action == 'Drinking' and is_drinking_posture) or
                (target_action == 'Typing' and (typing_device_present or is_typing_posture)) or
                (target_action == 'Walking' and is_walking_active)
            )

            if is_step_match:
                current_dwell += dt
                if active_alert_text and alert_display_timer > 0:
                    alert_display_timer -= dt * 2.0
                    if alert_display_timer <= 0:
                        active_alert_text = None

                if current_dwell >= target_step['min_dwell']:
                    step_completed[current_step_idx] = True
                    step_timestamps[current_step_idx] = time.time() - protocol_start_time
                    play_sound_async('chime')
                    print(f"[✓] Completed Step {target_step['id']}: {target_step['title']} ({step_timestamps[current_step_idx]:.1f}s)")

                    current_step_idx += 1
                    current_dwell = 0.0

                    if current_step_idx >= len(ACTIVITY_STEPS):
                        protocol_finished = True
                        protocol_finish_time = time.time() - protocol_start_time
                        play_sound_async('complete')
                        print(f"\n🎉 [SUCCESS] All 4 Protocol Steps Completed in {protocol_finish_time:.1f}s!\n")
                        save_protocol_report(step_timestamps, protocol_finish_time)

            # Case B: Future step detected -> Protocol Sequence Violation / Skip!
            else:
                skipped_step_indices = []
                for idx in range(current_step_idx + 1, len(ACTIVITY_STEPS)):
                    f_action = ACTIVITY_STEPS[idx]['action']
                    if (f_action == detected_action and action_conf >= 0.70) or (f_action == 'ShakingHands' and handshake_verified):
                        skipped_step_indices.append(idx)

                if skipped_step_indices:
                    future_step = ACTIVITY_STEPS[skipped_step_indices[0]]
                    missed_step = target_step
                    active_alert_text = f"SKIPPED STEP {missed_step['id']} ({missed_step['action']})! PERFORMING STEP {future_step['id']} ({future_step['action']})"
                    alert_display_timer = 2.0
                    play_sound_async('alert')
                else:
                    current_dwell = max(0.0, current_dwell - dt * 0.5)

        # Decay alert timer
        if alert_display_timer > 0:
            alert_display_timer -= dt
            if alert_display_timer <= 0:
                active_alert_text = None

        # =====================================================================
        # HUD GRAPHICAL RENDERING
        # =====================================================================
        # 1. Top Mission Control Header Banner
        cv2.rectangle(frame, (0, 0), (W, 70), (20, 20, 20), -1)
        cv2.line(frame, (0, 70), (W, 70), (0, 255, 255), 2)
        cv2.putText(frame, "ARIA - BIO-PAYLOAD EXPERIMENT PROTOCOL", (25, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2)
        elapsed_sec = (protocol_finish_time if protocol_finished else (time.time() - protocol_start_time))
        mute_status = "[AUDIO: MUTED (Press M)]" if audio_muted else "[AUDIO: ACTIVE]"
        if is_two_person_mode:
            mode_tag = "[CREW: 2 ASTRONAUTS DETECTED]"
            tag_color = (0, 255, 255)
        elif len(detected_people_boxes) == 1:
            mode_tag = "[CREW: 1 ASTRONAUT (Solo Mode)]"
            tag_color = (0, 255, 128)
        else:
            mode_tag = "[CREW: SEARCHING FOR ASTRONAUT...]"
            tag_color = (0, 165, 255)
        cv2.putText(frame, f"T+{elapsed_sec:05.1f}s | {mode_tag} | {mute_status} | [F] Fullscreen | [R] Reset | [Q] Quit",
                    (25, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.52, tag_color, 2)

        # 2. Right Sidebar: Real-Time Step Checklist
        sb_w = 410
        sb_x = W - sb_w
        overlay = frame.copy()
        cv2.rectangle(overlay, (sb_x, 70), (W, H), (15, 15, 15), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        cv2.line(frame, (sb_x, 70), (sb_x, H), (70, 70, 70), 2)

        cv2.putText(frame, "EXPERIMENT CHECKLIST", (sb_x + 20, 105),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 255, 255), 2)
        cv2.line(frame, (sb_x + 20, 115), (W - 20, 115), (100, 100, 100), 1)

        card_y = 135
        for i, step in enumerate(ACTIVITY_STEPS):
            card_h = 85
            is_done = step_completed[i]
            is_active = (i == current_step_idx and not protocol_finished)

            if is_done:
                bg_color = (20, 45, 20)
                border_color = (0, 255, 0)
                status_icon = "[✓] DONE"
                icon_color = (0, 255, 0)
            elif is_active:
                bg_color = (45, 45, 20)
                border_color = (0, 255, 255)
                status_icon = "[▶] ACTIVE"
                icon_color = (0, 255, 255)
            else:
                bg_color = (25, 25, 25)
                border_color = (60, 60, 60)
                status_icon = "[ ] PENDING"
                icon_color = (150, 150, 150)

            cv2.rectangle(frame, (sb_x + 15, card_y), (W - 15, card_y + card_h), bg_color, -1)
            cv2.rectangle(frame, (sb_x + 15, card_y), (W - 15, card_y + card_h), border_color, 2)

            cv2.putText(frame, f"Step {step['id']}: {step['action']}", (sb_x + 25, card_y + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
            cv2.putText(frame, status_icon, (W - 135, card_y + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.52, icon_color, 2)
            cv2.putText(frame, step['title'], (sb_x + 25, card_y + 48),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 2)

            if is_done and step_timestamps[i] is not None:
                cv2.putText(frame, f"Completed at T+{step_timestamps[i]:.1f}s", (sb_x + 25, card_y + 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)
            elif is_active:
                progress_pct = min(1.0, current_dwell / step['min_dwell'])
                bar_w = W - 30 - (sb_x + 25)
                cv2.rectangle(frame, (sb_x + 25, card_y + 58), (sb_x + 25 + bar_w, card_y + 72), (50, 50, 50), -1)
                cv2.rectangle(frame, (sb_x + 25, card_y + 58), (sb_x + 25 + int(bar_w * progress_pct), card_y + 72), (0, 255, 255), -1)
                cv2.putText(frame, f"Hold: {current_dwell:.1f}s / {step['min_dwell']:.1f}s", (sb_x + 35, card_y + 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 2)

            card_y += card_h + 15

        # 3. Live Detection Telemetry (Bottom Left)
        cv2.rectangle(frame, (20, H - 90), (sb_x - 20, H - 20), (20, 20, 20), -1)
        cv2.rectangle(frame, (20, H - 90), (sb_x - 20, H - 20), (70, 70, 70), 1)
        cv2.putText(frame, f"Live Detected Action: {detected_action} ({action_conf*100:.0f}%)", (35, H - 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 255, 0) if action_conf > 0.6 else (0, 200, 255), 2)
        if handshake_badge_text:
            cv2.putText(frame, handshake_badge_text, (35, H - 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.54, (0, 215, 255), 2)
        elif is_two_person_mode and handshake_debug_telemetry and not protocol_finished and ACTIVITY_STEPS[current_step_idx]['action'] == 'ShakingHands':
            cv2.putText(frame, f"Handshake Distance: {handshake_debug_telemetry}", (35, H - 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 215, 255), 2)
        elif not protocol_finished:
            t_action = ACTIVITY_STEPS[current_step_idx]['action']
            if t_action == 'Walking' and detected_action == 'Idle':
                if is_isolated_head_motion:
                    cv2.putText(frame, "Target Action Needed -> Step 1: Head motion only. Please walk or step in place!",
                                (35, H - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 200, 255), 2)
                else:
                    cv2.putText(frame, "Target Action Needed -> Step 1: Walk or Step In Place (Active Motion Required)",
                                (35, H - 35), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 255), 2)
            else:
                cv2.putText(frame, f"Target Action Needed -> Step {current_step_idx+1}: {t_action}", (35, H - 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 2)

        # 4. SEQUENCE VIOLATION WARNING ALERT BANNER (Flashing Red)
        if active_alert_text and not protocol_finished:
            flash = (int(time.time() * 4) % 2 == 0)
            alert_bg = (0, 0, 180) if flash else (0, 0, 100)
            banner_y = int(H / 2) - 60
            cv2.rectangle(frame, (50, banner_y), (sb_x - 30, banner_y + 110), alert_bg, -1)
            cv2.rectangle(frame, (50, banner_y), (sb_x - 30, banner_y + 110), (0, 255, 255), 4)
            cv2.putText(frame, "PROTOCOL SEQUENCE VIOLATION ALERT!", (70, banner_y + 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.82, (255, 255, 255), 3)
            cv2.putText(frame, active_alert_text, (70, banner_y + 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)

        # 5. Mission Success Banner (When All 4 Steps are Done)
        if protocol_finished:
            suc_y = int(H / 2) - 80
            cv2.rectangle(frame, (60, suc_y), (sb_x - 40, suc_y + 160), (20, 60, 20), -1)
            cv2.rectangle(frame, (60, suc_y), (sb_x - 40, suc_y + 160), (0, 255, 0), 4)
            cv2.putText(frame, "🎉 PROTOCOL COMPLETED SUCCESSFULLY!", (85, suc_y + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.90, (0, 255, 0), 3)
            cv2.putText(frame, f"All 4 Bio-Payload SOP Steps Verified in {protocol_finish_time:.1f} seconds",
                        (85, suc_y + 90), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.putText(frame, "Report saved to reports/ | Press [R] to re-run | [Q] to quit",
                        (85, suc_y + 130), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 255, 200), 1)

        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(1) & 0xFF

        if key in [ord('q'), 27]:
            break

        if key in [ord('f'), ord('F')]:
            cur_prop = cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN)
            new_prop = cv2.WINDOW_NORMAL if cur_prop == cv2.WINDOW_FULLSCREEN else cv2.WINDOW_FULLSCREEN
            cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, new_prop)

        if key in [ord('m'), ord('M')]:
            audio_muted = not audio_muted
            print(f"[*] Audio Muted: {audio_muted}")

        if key in [ord('r'), ord('R')]:
            current_step_idx = 0
            step_completed = [False] * len(ACTIVITY_STEPS)
            step_timestamps = [None] * len(ACTIVITY_STEPS)
            current_dwell = 0.0
            protocol_start_time = time.time()
            protocol_finished = False
            protocol_finish_time = None
            active_alert_text = None
            print("\n[*] Protocol Reset to Step 1.\n")

    cap.release()
    holistic_detector.close()
    cv2.destroyAllWindows()

def save_protocol_report(timestamps, total_duration):
    report_file = os.path.join(REPORTS_DIR, f"activity1_report_{time.strftime('%Y%m%d_%H%M%S')}.txt")
    with open(report_file, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("      ISRO BIO-PAYLOAD EXPERIMENT: ACTIVITY 1 REPORT\n")
        f.write("=" * 60 + "\n")
        f.write(f"Date & Time       : {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Duration    : {total_duration:.2f} seconds\n")
        f.write(f"Steps Completed   : 4 / 4 (100% Compliant)\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'Step ID':<10} {'Action':<15} {'Completion Timestamp':<25}\n")
        f.write("-" * 60 + "\n")
        for i, s in enumerate(ACTIVITY_STEPS):
            t_val = f"T+{timestamps[i]:.2f}s" if timestamps[i] is not None else "N/A"
            f.write(f"{s['id']:<10} {s['action']:<15} {t_val:<25}\n")
        f.write("=" * 60 + "\n")
    print(f"[✓] Saved compliance report: {report_file}")

if __name__ == '__main__':
    run_activity_1()
