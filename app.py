# ==============================================================================
# ARIA - Astronaut Research Interaction Assistant
# Master Cockpit Server & Native Offline Desktop Application
# ==============================================================================

import os
import sys
import json
import time
import socket
import subprocess
import threading
from typing import Optional
from flask import Flask, request, jsonify, render_template

# Per-Monitor High DPI awareness on Windows to prevent blurriness
if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

PYTHON_EXE = os.path.join(BASE_DIR, '.venv', 'Scripts', 'python.exe')
if not os.path.isfile(PYTHON_EXE):
    PYTHON_EXE = sys.executable

# Import backend engines from core package
from core.backend_engines import (
    db, audit_logger, telemetry_sim, safety_monitor,
    protocol_engine, offline_llm,
    EMBEDDED_EXPERIMENTS, EMBEDDED_TIMELINE, EMBEDDED_EMERGENCIES
)
from core.voice_service import voice_service

# Initialize Flask application
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "ui", "static"),
    template_folder=os.path.join(BASE_DIR, "ui", "templates")
)
app.config['JSON_SORT_KEYS'] = False

# ==============================================================================
# SUBTOOL PROCESS LAUNCHER
# ==============================================================================
running_subprocesses = []

def launch_subtool(script_name: str, arg: Optional[str] = None):
    # Check directly or in vision/ directory
    script_path = os.path.join(BASE_DIR, script_name)
    if not os.path.isfile(script_path):
        script_path = os.path.join(BASE_DIR, "vision", script_name)
    if not os.path.isfile(script_path):
        print(f"[ERROR] Subtool script not found: {script_path}")
        return False

    cmd = [PYTHON_EXE, script_path]
    if arg:
        cmd.append(arg)

    def _run():
        try:
            print(f"[ARIA] Launching subtool: {' '.join(cmd)}")
            p = subprocess.Popen(cmd, cwd=BASE_DIR)
            running_subprocesses.append(p)
            p.wait()
        except Exception as e:
            print(f"[ARIA ERROR] Failed running subtool {script_name}: {e}")

    threading.Thread(target=_run, daemon=True).start()
    return True

# ==============================================================================
# FLASK WEB ROUTES & REST APIs
# ==============================================================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/experiments", methods=["GET"])
def get_experiments():
    return jsonify({"status": "SUCCESS", "count": len(db.get_all()), "experiments": db.get_all()})

@app.route("/api/experiments/<exp_id>", methods=["GET"])
def get_experiment(exp_id):
    exp = db.get(exp_id)
    if not exp:
        return jsonify({"status": "ERROR", "message": f"Experiment '{exp_id}' not found."}), 404
    return jsonify({"status": "SUCCESS", "experiment": exp})

@app.route("/api/protocol/state", methods=["GET"])
def get_protocol_state():
    return jsonify({"status": "SUCCESS", "state": protocol_engine.get_state()})

@app.route("/api/protocol/select", methods=["POST"])
def select_protocol():
    data = request.get_json() or {}
    try:
        new_state = protocol_engine.select_experiment(
            data.get("experiment_id"),
            astronaut_id=data.get("astronaut_id", "CREW-CDR-RATHORE")
        )
        return jsonify({"status": "SUCCESS", "state": new_state})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400

@app.route("/api/protocol/confirm-step", methods=["POST"])
def confirm_step():
    data = request.get_json() or {}
    try:
        new_state = protocol_engine.confirm_current_step(
            astronaut_id=data.get("astronaut_id", "CREW-CDR-RATHORE"),
            notes=data.get("notes", "")
        )
        return jsonify({"status": "SUCCESS", "state": new_state})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400

@app.route("/api/protocol/jump-step", methods=["POST"])
def jump_step():
    data = request.get_json() or {}
    try:
        st = protocol_engine.attempt_step_jump(
            int(data.get("target_step_number", 1)),
            astronaut_id=data.get("astronaut_id", "CREW-CDR-RATHORE")
        )
        return jsonify({"status": "SUCCESS", "state": st})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400

@app.route("/api/protocol/skip-step", methods=["POST"])
def skip_step():
    data = request.get_json() or {}
    try:
        st = protocol_engine.skip_step_with_override(
            reason=data.get("reason", "Operational constraint"),
            override_code=data.get("override_code", "OVERRIDE-CDR-01"),
            astronaut_id=data.get("astronaut_id", "CREW-CDR-RATHORE")
        )
        return jsonify({"status": "SUCCESS", "state": st})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)}), 400

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_msg = data.get("message", "")
    
    # Check for direct vision launches via chat commands
    msg_low = user_msg.lower()
    if any(k in msg_low for k in ["launch activity", "start activity 1", "bio protocol", "open camera", "pose tracking", "movement tracker"]):
        launch_subtool('activity_1.py')
        return jsonify({
            "status": "SUCCESS",
            "result": {
                "response": "🚀 **Launching ARIA Activity 1: Bio-Payload Protocol & Movement Tracker** in a high-resolution window with MediaPipe Holistic pose, hands, and face tracking.",
                "voice_text": "Launching Activity 1 movement tracker.",
                "intent": "LAUNCH_VISION_TOOL",
                "action": None
            }
        })
    elif any(k in msg_low for k in ["analyze clip", "pose analyzer", "biomechanics scan"]):
        launch_subtool('analyze_clip.py')
        return jsonify({
            "status": "SUCCESS",
            "result": {
                "response": "🎯 **Launching Pose Clip Analyzer** for 5-second microgravity posture evaluation.",
                "voice_text": "Launching Pose Analyzer.",
                "intent": "LAUNCH_VISION_TOOL",
                "action": None
            }
        })

    state = protocol_engine.get_state()
    response = offline_llm.chat(user_message=user_msg, active_state=state)
    return jsonify({"status": "SUCCESS", "result": response})

@app.route("/api/telemetry", methods=["GET"])
def get_telemetry():
    return jsonify({"status": "SUCCESS", "telemetry": telemetry_sim.get_snapshot()})

@app.route("/api/telemetry/inject-anomaly", methods=["POST"])
def inject_anomaly():
    data = request.get_json() or {}
    telemetry_sim.inject_anomaly(
        data.get("sensor", "lsg_pressure"),
        float(data.get("value", 0.1)),
        int(data.get("duration", 60))
    )
    return jsonify({"status": "SUCCESS", "message": "Anomaly injected."})

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    return jsonify({"status": "SUCCESS", "alerts": safety_monitor.get_active_alerts()})

@app.route("/api/alerts/acknowledge", methods=["POST"])
def acknowledge_alert():
    data = request.get_json() or {}
    ok = safety_monitor.acknowledge_alert(
        data.get("alert_id"),
        data.get("astronaut_id", "CREW-CDR-RATHORE"),
        data.get("override_reason")
    )
    return jsonify({"status": "SUCCESS" if ok else "ERROR"})

@app.route("/api/audit-trail", methods=["GET"])
def get_audit_trail():
    return jsonify({
        "status": "SUCCESS",
        "pending_sync_records": audit_logger.get_pending_sync_count(),
        "events": audit_logger.get_events(limit=40)
    })

@app.route("/api/audit-trail/sync", methods=["POST"])
def sync_ground_control():
    return jsonify({"status": "SUCCESS", "sync": audit_logger.sync_with_ground_control()})

@app.route("/api/schedule", methods=["GET"])
def get_schedule():
    return jsonify({"status": "SUCCESS", "schedule": offline_llm.timeline_data})

@app.route("/api/emergencies", methods=["GET"])
def get_emergencies():
    return jsonify({"status": "SUCCESS", "emergencies": offline_llm.emergency_data})

# ==============================================================================
# SPEECH-TO-TEXT & VOICE RECOGNITION ROUTES
# ==============================================================================

@app.route("/api/voice/live/start", methods=["POST"])
def route_voice_live_start():
    res = voice_service.start_live_listening()
    return jsonify(res)

@app.route("/api/voice/live/status", methods=["GET"])
def route_voice_live_status():
    status = voice_service.get_live_status()
    return jsonify({"status": "SUCCESS", "data": status})

@app.route("/api/voice/live/stop", methods=["POST"])
def route_voice_live_stop():
    res = voice_service.stop_live_listening()
    return jsonify(res)

@app.route("/api/voice/transcribe", methods=["POST"])
def route_voice_transcribe():
    audio_bytes = b""
    if 'audio' in request.files:
        audio_bytes = request.files['audio'].read()
    else:
        audio_bytes = request.get_data()

    if not audio_bytes:
        return jsonify({"status": "ERROR", "message": "No audio data received", "transcript": ""}), 400

    transcript = voice_service.transcribe_wav(audio_bytes)
    return jsonify({
        "status": "SUCCESS",
        "transcript": transcript
    })

# Vision Module Launch API Routes
@app.route("/api/launch/activity-1", methods=["POST"])
def route_launch_activity1():
    ok = launch_subtool('activity_1.py')
    return jsonify({"status": "SUCCESS" if ok else "ERROR"})

@app.route("/api/launch/analyzer", methods=["POST"])
def route_launch_analyzer():
    ok = launch_subtool('analyze_clip.py')
    return jsonify({"status": "SUCCESS" if ok else "ERROR"})

@app.route("/api/launch/collect", methods=["POST"])
def route_launch_collect():
    data = request.get_json() or {}
    action = data.get("arg", "Walking")
    ok = launch_subtool('collect_data.py', action)
    return jsonify({"status": "SUCCESS" if ok else "ERROR"})

@app.route("/api/launch/train", methods=["POST"])
def route_launch_train():
    ok = launch_subtool('train_model.py')
    return jsonify({"status": "SUCCESS" if ok else "ERROR"})

@app.route("/api/launch/reports", methods=["POST"])
def route_open_reports():
    try:
        if sys.platform == 'win32':
            os.startfile(REPORTS_DIR)
        else:
            subprocess.Popen(['xdg-open', REPORTS_DIR])
        return jsonify({"status": "SUCCESS"})
    except Exception as e:
        return jsonify({"status": "ERROR", "message": str(e)})

# ==============================================================================
# APPLICATION ENTRYPOINT & NATIVE DESKTOP WINDOW LAUNCHER
# ==============================================================================

def find_available_port(preferred_port=5000):
    """Finds an available local port, trying preferred_port first."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', preferred_port))
        s.close()
        return preferred_port
    except OSError:
        s.close()
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.bind(('127.0.0.1', 0))
        port = s2.getsockname()[1]
        s2.close()
        return port

def run_flask_server(port):
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

def main():
    print("================================================================")
    print("  ARIA - Astronaut Research Interaction Assistant")
    print("  Microgravity Protocol & Advanced Perception Suite")
    print("  100% Offline Airgap Edge System")
    print("================================================================")

    port = find_available_port(5000)
    server_url = f"http://127.0.0.1:{port}"

    # Start Flask in daemon thread
    server_thread = threading.Thread(target=run_flask_server, args=(port,), daemon=True)
    server_thread.start()
    time.sleep(0.6)

    # Check CLI or browser flag
    if len(sys.argv) > 1 and sys.argv[1] == '--browser':
        import webbrowser
        print(f"[*] Opening in default web browser: {server_url}")
        webbrowser.open_new(server_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down ARIA.")
            sys.exit(0)

    # NATIVE DESKTOP WINDOW VIA PYWEBVIEW
    try:
        import webview
        print(f"[*] Launching native desktop window for ARIA ({server_url})...")
        window = webview.create_window(
            title="ARIA - Astronaut Research Interaction Assistant",
            url=server_url,
            width=1500,
            height=920,
            min_size=(1050, 700),
            background_color='#070b12',
            text_select=True
        )
        webview.start(debug=False)
        print("[*] ARIA native desktop application closed.")
    except Exception as e:
        print(f"[WARNING] Native pywebview window could not start ({e}). Falling back to browser...")
        import webbrowser
        webbrowser.open_new(server_url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)

if __name__ == '__main__':
    main()
