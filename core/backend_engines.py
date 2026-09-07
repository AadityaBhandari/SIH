import os
import sys
import json
import time
import math
import random
import re
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
try:
    from core.experiments_data import EMBEDDED_EXPERIMENTS, EMBEDDED_TIMELINE, EMBEDDED_EMERGENCIES
except ImportError:
    from experiments_data import EMBEDDED_EXPERIMENTS, EMBEDDED_TIMELINE, EMBEDDED_EMERGENCIES

# SECTION 2: CORE BACKEND ENGINES

# ==============================================================================



class ExperimentsDatabase:

    def __init__(self):

        self.experiments = EMBEDDED_EXPERIMENTS

        self.experiments_by_id = {exp["id"]: exp for exp in self.experiments}

        self.experiments_by_code = {exp["code"].upper(): exp for exp in self.experiments}



    def get_all(self) -> List[Dict[str, Any]]:

        return self.experiments



    def get(self, identifier: str) -> Optional[Dict[str, Any]]:

        clean_id = str(identifier).strip().upper()

        if clean_id in self.experiments_by_id:

            return self.experiments_by_id[clean_id]

        if clean_id in self.experiments_by_code:

            return self.experiments_by_code[clean_id]

        for exp in self.experiments:

            if clean_id in exp["id"].upper() or clean_id in exp["code"].upper() or clean_id in exp["title"].upper():

                return exp

        return None



    def get_step(self, exp_id: str, step_number: int) -> Optional[Dict[str, Any]]:

        exp = self.get(exp_id)

        if not exp:

            return None

        for step in exp.get("steps", []):

            if step["step_number"] == int(step_number):

                return step

        return None



    def search(self, query: str) -> List[Dict[str, Any]]:

        q = query.lower().strip()

        terms = [t for t in re.findall(r'\w+', q) if len(t) > 2 and t not in {"the", "and", "for", "with", "how", "what", "why", "does", "are", "explain", "study"}]

        matches = []

        for exp in self.experiments:

            score = 0

            exp_text = f"{exp['id']} {exp['code']} {exp['title']} {exp['category']} {exp['facility']} {exp['objective']}".lower()

            if q in exp_text:

                score += 25

            for term in terms:

                if term in exp["id"].lower() or term in exp["code"].lower():

                    score += 12

                elif term in exp["title"].lower():

                    score += 10

                elif term in exp["category"].lower() or term in exp["facility"].lower():

                    score += 6

                elif term in exp["objective"].lower():

                    score += 4

                for step in exp.get("steps", []):

                    if term in step["title"].lower() or term in step["action"].lower():

                        score += 2

            if score > 0:

                matches.append((score, exp))

        matches.sort(key=lambda x: x[0], reverse=True)

        return [m[1] for m in matches]



db = ExperimentsDatabase()



class AuditLogger:

    def __init__(self):

        self.lock = threading.Lock()

        self.events = [

            {

                "event_id": "EVT-INIT-0001",

                "timestamp_utc": datetime.now(timezone.utc).isoformat(),

                "astronaut_id": "CREW-CDR-RATHORE",

                "category": "SYSTEM_INIT",

                "severity": "INFO",

                "experiment_id": "SYSTEM",

                "step_number": None,

                "message": "Offline Astronaut Assistant System initialized. 7 microgravity protocols verified.",

                "acknowledged": True,

                "ground_control_flag": False

            }

        ]

        self.pending_uplink_records = 0



    def log_event(self, category: str, severity: str, message: str, experiment_id: Optional[str] = None,

                  step_number: Optional[int] = None, astronaut_id: str = "CREW-CDR-RATHORE",

                  ground_control_flag: bool = False, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:

        with self.lock:

            event_id = f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(self.events)+1:04d}"

            ev = {

                "event_id": event_id,

                "timestamp_utc": datetime.now(timezone.utc).isoformat(),

                "astronaut_id": astronaut_id,

                "category": category,

                "severity": severity,

                "experiment_id": experiment_id,

                "step_number": step_number,

                "message": message,

                "acknowledged": False if severity in ["WARNING", "CRITICAL"] else True,

                "ground_control_flag": ground_control_flag,

                "details": details or {}

            }

            self.events.append(ev)

            if ground_control_flag or severity in ["WARNING", "CRITICAL"]:

                self.pending_uplink_records += 1

            return ev



    def get_events(self, limit: int = 50, category: Optional[str] = None) -> List[Dict[str, Any]]:

        with self.lock:

            evs = self.events

            if category:

                evs = [e for e in evs if e.get("category") == category]

            return evs[-limit:][::-1]



    def get_pending_sync_count(self) -> int:

        with self.lock:

            return self.pending_uplink_records



    def sync_with_ground_control(self) -> Dict[str, Any]:

        with self.lock:

            synced = self.pending_uplink_records

            self.pending_uplink_records = 0

            for ev in self.events:

                if ev.get("ground_control_flag"):

                    ev["ground_control_synced"] = True

            return {

                "status": "SUCCESS",

                "synced_records": synced,

                "timestamp_utc": datetime.now(timezone.utc).isoformat()

            }



audit_logger = AuditLogger()



class TelemetrySimulator:

    def __init__(self):

        self.anomaly_active: Dict[str, Any] = {}

        self.met_epoch = time.time() - (4 * 86400 + 5 * 3600 + 45 * 60)



    def get_mission_elapsed_time(self) -> Dict[str, Any]:

        elapsed = int(time.time() - self.met_epoch)

        days = elapsed // 86400

        hours = (elapsed % 86400) // 3600

        mins = (elapsed % 3600) // 60

        secs = elapsed % 60

        return {

            "days": days,

            "hours": hours,

            "minutes": mins,

            "seconds": secs,

            "formatted": f"MET +{days:02d}:{hours:02d}:{mins:02d}:{secs:02d}",

            "flight_day": f"FD-{days+1:02d}"

        }



    def inject_anomaly(self, sensor_key: str, value: float, duration_seconds: int = 60) -> None:

        self.anomaly_active[sensor_key] = {

            "target_value": value,

            "expires_at": time.time() + duration_seconds

        }



    def get_snapshot(self) -> Dict[str, Any]:

        now = time.time()

        expired = [k for k, v in self.anomaly_active.items() if now > v["expires_at"]]

        for k in expired:

            del self.anomaly_active[k]



        t_wave = math.sin(now / 10.0)

        t_jitter = random.uniform(-0.02, 0.02)

        o2 = round(21.05 + 0.15 * t_wave + t_jitter, 2)

        co2 = round(0.34 + 0.03 * math.cos(now / 15.0), 3)

        pres = round(101.32 + 0.08 * t_wave, 2)

        ug = round((1.18 + 0.12 * math.sin(now / 4.0)) * 1e-6, 8)

        rad = round(22.4 + 1.2 * math.cos(now / 20.0) + random.uniform(-0.3, 0.3), 1)

        lsg = round(-0.52 + 0.02 * math.sin(now / 8.0), 3)



        if "o2_pct" in self.anomaly_active: o2 = self.anomaly_active["o2_pct"]["target_value"]

        if "co2_pct" in self.anomaly_active: co2 = self.anomaly_active["co2_pct"]["target_value"]

        if "pressure_kpa" in self.anomaly_active: pres = self.anomaly_active["pressure_kpa"]["target_value"]

        if "lsg_pressure" in self.anomaly_active: lsg = self.anomaly_active["lsg_pressure"]["target_value"]



        return {

            "timestamp_utc": datetime.now(timezone.utc).isoformat(),

            "met": self.get_mission_elapsed_time(),

            "orbit": {"inclination_deg": 51.64, "altitude_km": 418.5, "speed_km_s": 7.66, "los_ground_sync_in_mins": 14},

            "cabin_environment": {

                "o2_pct": {"value": o2, "status": "NOMINAL" if o2 >= 19.5 else "CRITICAL_LOW", "unit": "%"},

                "co2_pct": {"value": co2, "status": "NOMINAL" if co2 <= 0.50 else "WARNING_HIGH", "unit": "%"},

                "pressure_kpa": {"value": pres, "status": "NOMINAL" if pres >= 98.0 else "CRITICAL_DEPRESS", "unit": "kPa"},

                "temperature_c": {"value": round(21.6 + 0.4 * t_wave, 1), "status": "NOMINAL", "unit": "°C"},

                "humidity_pct": {"value": round(48.5 + 1.5 * math.sin(now / 18.0), 1), "status": "NOMINAL", "unit": "%"},

                "microgravity_g": {"value": f"{ug:.2e}", "status": "NOMINAL", "unit": "g"},

                "radiation_rate": {"value": rad, "status": "NOMINAL", "unit": "µSv/h"}

            },

            "facility_telemetry": {

                "lsg_negative_pressure_in_wg": {"value": lsg, "status": "NOMINAL" if lsg <= -0.30 else "SEAL_COMPROMISED", "unit": "in. w.g."},

                "melfi_dewar_temp_c": {"value": round(-80.4 + 0.2 * math.cos(now / 30.0), 1), "status": "NOMINAL", "unit": "°C"}

            }

        }



telemetry_sim = TelemetrySimulator()



class SafetyMonitor:

    def __init__(self):

        self.active_alerts: List[Dict[str, Any]] = []



    def evaluate_step_transition(self, exp_id: str, current_step_num: int, target_step_num: int,

                                 completed_steps: List[int], astronaut_id: str = "CREW-CDR-RATHORE") -> Tuple[bool, Optional[Dict[str, Any]]]:

        exp = db.get(exp_id)

        if not exp or target_step_num <= current_step_num:

            return True, None



        step_map = {s["step_number"]: s for s in exp.get("steps", [])}

        skipped = [step_map[sn] for sn in range(current_step_num, target_step_num) if sn not in completed_steps and sn in step_map]

        if not skipped:

            return True, None



        has_critical = any(s.get("is_mandatory", True) for s in skipped)

        skipped_str = ", ".join([f"Step {s['step_number']} ({s['title']})" for s in skipped])



        if has_critical:

            alert = self.create_alert(

                tier=3, severity="CRITICAL", category="SAFETY_VIOLATION_SKIPPED_STEP",

                title="MANDATORY PROTOCOL STEP SKIPPED",

                message=f"CRITICAL SAFETY VIOLATION: Attempted to bypass mandatory {skipped_str}. Containment and sample integrity protocols prohibit step omission.",

                voice_prompt=f"Critical Alert. Mandatory protocol {skipped[0]['title']} was skipped. Sequence blocked.",

                experiment_id=exp_id, step_number=target_step_num, requires_override=True, astronaut_id=astronaut_id

            )

            return False, alert

        else:

            alert = self.create_alert(

                tier=2, severity="WARNING", category="PROTOCOL_SEQUENCE_CAUTION",

                title="STEP SEQUENCE CAUTION",

                message=f"Caution: Step {skipped_str} has not been logged. Recommended to verify prior steps.",

                voice_prompt=f"Warning: Step sequence out of order. Verify {skipped[0]['title']}.",

                experiment_id=exp_id, step_number=target_step_num, requires_override=False, astronaut_id=astronaut_id

            )

            return True, alert



    def evaluate_step_timeout(self, exp_id: str, step_number: int, started_at: float, astronaut_id: str = "CREW-CDR-RATHORE") -> Optional[Dict[str, Any]]:

        exp = db.get(exp_id)

        if not exp: return None

        elapsed_mins = (time.time() - started_at) / 60.0

        critical_window = exp.get("critical_window_minutes", 30)



        if elapsed_mins > critical_window:

            return self.create_alert(

                tier=3, severity="CRITICAL", category="STEP_CRITICAL_TIMEOUT",

                title="CRITICAL TIME WINDOW EXCEEDED",

                message=f"CRITICAL DELAY: Step {step_number} pending {int(elapsed_mins)} mins (Limit: {critical_window} mins). Sample degradation active!",

                voice_prompt=f"Urgent reminder. Step {step_number} timing limit exceeded. Immediate action required.",

                experiment_id=exp_id, step_number=step_number, requires_override=True, astronaut_id=astronaut_id

            )

        elif elapsed_mins > (critical_window * 0.75):

            return self.create_alert(

                tier=2, severity="WARNING", category="STEP_TIMEOUT_APPROACHING",

                title="STEP TIMEOUT APPROACHING",

                message=f"Warning: Step {step_number} time-critical window expires in {int(critical_window - elapsed_mins)} minutes.",

                voice_prompt=f"Caution. Step {step_number} critical window expires in {int(critical_window - elapsed_mins)} minutes.",

                experiment_id=exp_id, step_number=step_number, requires_override=False, astronaut_id=astronaut_id

            )

        return None



    def create_alert(self, tier: int, severity: str, category: str, title: str, message: str, voice_prompt: str,

                     experiment_id: Optional[str] = None, step_number: Optional[int] = None,

                     requires_override: bool = False, astronaut_id: str = "CREW-CDR-RATHORE") -> Dict[str, Any]:

        alert_id = f"ALT-{int(time.time())}-{len(self.active_alerts)+1}"

        al = {

            "alert_id": alert_id, "tier": tier, "severity": severity, "category": category,

            "title": title, "message": message, "voice_prompt": voice_prompt,

            "experiment_id": experiment_id, "step_number": step_number,

            "requires_override": requires_override, "timestamp_utc": datetime.now(timezone.utc).isoformat(),

            "acknowledged": False

        }

        self.active_alerts.insert(0, al)

        if len(self.active_alerts) > 20: self.active_alerts.pop()

        audit_logger.log_event(category, severity, f"[{title}] {message}", experiment_id, step_number, astronaut_id,

                               ground_control_flag=(tier >= 2), details={"tier": tier, "alert_id": alert_id})

        return al



    def get_active_alerts(self, unacknowledged_only: bool = False) -> List[Dict[str, Any]]:

        if unacknowledged_only:

            return [a for a in self.active_alerts if not a.get("acknowledged")]

        return self.active_alerts



    def acknowledge_alert(self, alert_id: str, astronaut_id: str = "CREW-CDR-RATHORE", override_reason: Optional[str] = None) -> bool:

        for al in self.active_alerts:

            if al["alert_id"] == alert_id:

                al["acknowledged"] = True

                al["acknowledged_by"] = astronaut_id

                al["acknowledged_at"] = datetime.now(timezone.utc).isoformat()

                if override_reason:

                    al["override_reason"] = override_reason

                    audit_logger.log_event("OVERRIDE_AUTHORIZATION", "WARNING", f"Alert {alert_id} overridden: {override_reason}",

                                           al.get("experiment_id"), al.get("step_number"), astronaut_id, ground_control_flag=True)

                return True

        return False



safety_monitor = SafetyMonitor()



class ProtocolEngine:

    def __init__(self):

        self.active_experiment_id: str = "EXP-01"

        self.current_step_number: int = 1

        self.completed_steps: Dict[str, List[int]] = {}

        self.step_start_time: float = time.time()

        self.step_notes: Dict[str, Dict[int, str]] = {}



    def select_experiment(self, exp_id: str, astronaut_id: str = "CREW-CDR-RATHORE") -> Dict[str, Any]:

        exp = db.get(exp_id)

        if not exp: raise ValueError(f"Experiment {exp_id} not found")

        self.active_experiment_id = exp["id"]

        if self.active_experiment_id not in self.completed_steps:

            self.completed_steps[self.active_experiment_id] = []

        done = self.completed_steps[self.active_experiment_id]

        self.current_step_number = min(max(done) + 1, len(exp.get("steps", []))) if done else 1

        self.step_start_time = time.time()

        audit_logger.log_event("EXPERIMENT_ACTIVATION", "INFO", f"Activated: {exp['id']} - {exp['title']}",

                               exp["id"], self.current_step_number, astronaut_id)

        return self.get_state()



    def confirm_current_step(self, astronaut_id: str = "CREW-CDR-RATHORE", notes: str = "") -> Dict[str, Any]:

        exp = db.get(self.active_experiment_id)

        step = db.get_step(self.active_experiment_id, self.current_step_number)

        if not exp or not step: raise ValueError("Invalid active state")



        if self.active_experiment_id not in self.completed_steps:

            self.completed_steps[self.active_experiment_id] = []

        if self.current_step_number not in self.completed_steps[self.active_experiment_id]:

            self.completed_steps[self.active_experiment_id].append(self.current_step_number)



        elapsed = int(time.time() - self.step_start_time)

        audit_logger.log_event("STEP_COMPLETED", "INFO", f"Completed Step {self.current_step_number}: '{step['title']}' in {elapsed}s. {notes}",

                               self.active_experiment_id, self.current_step_number, astronaut_id)



        total_steps = len(exp.get("steps", []))

        if self.current_step_number < total_steps:

            self.current_step_number += 1

            self.step_start_time = time.time()

            next_step = db.get_step(self.active_experiment_id, self.current_step_number)

            voice_text = f"Step {self.current_step_number - 1} confirmed. Next: Step {self.current_step_number}, {next_step['title']}."

        else:

            voice_text = f"Protocol {exp['code']} completed! All {total_steps} steps verified and logged."

            safety_monitor.create_alert(1, "INFO", "EXPERIMENT_COMPLETED", "PROTOCOL COMPLETE",

                                        f"All steps for {exp['code']} verified and sealed.", voice_text,

                                        self.active_experiment_id, self.current_step_number, False, astronaut_id)



        st = self.get_state()

        st["feedback_voice"] = voice_text

        return st



    def attempt_step_jump(self, target_step_number: int, astronaut_id: str = "CREW-CDR-RATHORE") -> Dict[str, Any]:

        done = self.completed_steps.get(self.active_experiment_id, [])

        is_allowed, alert = safety_monitor.evaluate_step_transition(

            self.active_experiment_id, self.current_step_number, target_step_number, done, astronaut_id

        )

        if not is_allowed:

            st = self.get_state()

            st["blocked"] = True

            st["active_alert"] = alert

            return st

        self.current_step_number = target_step_number

        self.step_start_time = time.time()

        st = self.get_state()

        if alert: st["active_alert"] = alert

        return st



    def skip_step_with_override(self, reason: str, override_code: str = "AUTH-EVA-01", astronaut_id: str = "CREW-CDR-RATHORE") -> Dict[str, Any]:

        step = db.get_step(self.active_experiment_id, self.current_step_number)

        audit_logger.log_event("PROTOCOL_SKIP_OVERRIDE", "WARNING",

                               f"Astronaut {astronaut_id} skipped Step {self.current_step_number} ({step['title'] if step else '?'}). Reason: {reason}. Auth: {override_code}",

                               self.active_experiment_id, self.current_step_number, astronaut_id, ground_control_flag=True)

        safety_monitor.create_alert(2, "WARNING", "STEP_SKIPPED_OVERRIDE", "STEP SKIPPED WITH OVERRIDE",

                                    f"Step {self.current_step_number} bypassed by crew. Reason: {reason}.",

                                    f"Caution. Step {self.current_step_number} skip recorded with override.",

                                    self.active_experiment_id, self.current_step_number, False, astronaut_id)

        exp = db.get(self.active_experiment_id)

        if self.current_step_number < len(exp.get("steps", [])):

            self.current_step_number += 1

            self.step_start_time = time.time()

        return self.get_state()



    def get_state(self) -> Dict[str, Any]:

        exp = db.get(self.active_experiment_id)

        if not exp: return {}

        steps = exp.get("steps", [])

        done = self.completed_steps.get(self.active_experiment_id, [])

        curr_step = db.get_step(self.active_experiment_id, self.current_step_number)

        elapsed = int(time.time() - self.step_start_time)

        to_alert = safety_monitor.evaluate_step_timeout(self.active_experiment_id, self.current_step_number, self.step_start_time)

        return {

            "active_experiment": {

                "id": exp["id"], "code": exp["code"], "title": exp["title"],

                "category": exp["category"], "facility": exp["facility"],

                "safety_level": exp["safety_level"], "hazards": exp.get("hazards", []),

                "critical_window_minutes": exp.get("critical_window_minutes", 30)

            },

            "current_step_number": self.current_step_number,

            "total_steps": len(steps),

            "current_step": curr_step,

            "completed_steps": done,

            "completion_percentage": round((len(done) / max(len(steps), 1)) * 100, 1),

            "step_elapsed_seconds": elapsed,

            "all_steps": steps,

            "active_timeout_alert": to_alert

        }



protocol_engine = ProtocolEngine()



class OfflineLLMEngine:

    def __init__(self, local_llm_url: str = "http://127.0.0.1:11434/api/generate"):

        self.local_llm_url = local_llm_url

        self.timeline_data = EMBEDDED_TIMELINE

        self.emergency_data = EMBEDDED_EMERGENCIES



    def chat(self, user_message: str, active_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:

        msg = user_message.strip()

        if not msg:

            return {"response": "Astronaut Assistant standby.", "voice_text": "Standby.", "intent": "STANDBY", "action": None}



        m = msg.lower()

        # 1. Emergency

        if any(w in m for w in ["emergency", "depress", "fire", "leak", "puncture", "toxic", "rupture", "spill", "abort"]):

            matched = self.emergency_data[0]

            for ep in self.emergency_data:

                if any(t in m for t in ep["code"].lower().split("-") if len(t) > 3) or any(t in m for t in ep["title"].lower().split() if len(t) > 4):

                    matched = ep

                    break

            actions = "\n".join([f"{i+1}. **{act}**" for i, act in enumerate(matched["immediate_actions"])])

            resp = f"🚨 **EMERGENCY CONTINGENCY PROTOCOL: {matched['title']}**\n\n**SEVERITY:** `{matched['severity']}` | **ALARM:** `{matched['audio_alarm']}`\n\n**IMMEDIATE MANDATORY ACTIONS:**\n{actions}\n\n⚠️ *Priority code {matched['code']} flagged for Ground Control.*"

            voice = f"Emergency Alert! {matched['title']}. Immediate action: {matched['immediate_actions'][0]}"

            return {"response": resp, "voice_text": voice, "intent": "EMERGENCY", "action": "TRIGGER_EMERGENCY_MODAL", "emergency_id": matched["id"], "source": "OFFLINE_CORE"}



        # 2. Confirm / Next step

        if any(p in m for p in ["next step", "proceed", "advance step", "confirm step", "step completed", "mark complete"]):

            if active_state and active_state.get("current_step_number"):

                num = active_state["current_step_number"]

                title = active_state.get("current_step", {}).get("title", f"Step {num}")

                resp = f"Ready to verify Step {num}: '{title}'. Click 'CONFIRM & ADVANCE' or say 'Confirm Step'."

                voice = f"Step {num} ready for confirmation: {title}."

                return {"response": resp, "voice_text": voice, "intent": "ACTION_CONFIRM_STEP", "action": "CONFIRM_STEP", "source": "OFFLINE_CORE"}



        # 3. Skip step

        if any(p in m for p in ["skip step", "bypass step", "omit step"]):

            return {"response": "Protocol Skip Warning: Skipping requires justification and supervisor authorization code.",

                    "voice_text": "Warning. Protocol skip requires justification.", "intent": "ACTION_SKIP_STEP", "action": "REQUEST_SKIP", "source": "OFFLINE_CORE"}



        # 4. Telemetry

        if any(w in m for w in ["telemetry", "oxygen", "pressure", "co2", "radiation", "cabin status", "sensor"]):

            tele = telemetry_sim.get_snapshot()

            cab = tele["cabin_environment"]

            resp = f"**Station Telemetry ({tele['met']['formatted']}):**\n- **Cabin O2:** {cab['o2_pct']['value']}% [{cab['o2_pct']['status']}]\n- **Atmospheric Pressure:** {cab['pressure_kpa']['value']} kPa [{cab['pressure_kpa']['status']}]\n- **Radiation:** {cab['radiation_rate']['value']} µSv/h [{cab['radiation_rate']['status']}]"

            voice = f"Station telemetry nominal. Oxygen {cab['o2_pct']['value']} percent, pressure {cab['pressure_kpa']['value']} kilopascals."

            return {"response": resp, "voice_text": voice, "intent": "QUERY_TELEMETRY", "action": None, "source": "OFFLINE_CORE"}



        # 5. Schedule

        if any(w in m for w in ["schedule", "timeline", "flight day", "tasks today"]):

            act_day = self.timeline_data.get("active_flight_day", "FD-04")

            for day in self.timeline_data.get("schedule", []):

                if day["flight_day"] == act_day:

                    tasks_str = "\n".join([f"- **{t['time']}** ({t['experiment_id']}): {t['task']} `[{t['status']}]`" for t in day["tasks"]])

                    return {"response": f"**Schedule for Flight Day {act_day}:**\n\n{tasks_str}",

                            "voice_text": f"Schedule for Flight Day 4 active. 4 scientific tasks scheduled.", "intent": "QUERY_SCHEDULE", "action": None, "source": "OFFLINE_CORE"}



        # 6. Safety & hazards

        if any(w in m for w in ["safety", "hazard", "warning", "precaution"]):

            if active_state and active_state.get("active_experiment"):

                exp_info = active_state["active_experiment"]

                hazards = "\n".join([f"- ⚠️ {h}" for h in exp_info.get("hazards", [])])

                return {"response": f"**Safety Advisory for {exp_info['code']}:**\n{hazards}",

                        "voice_text": f"Safety advisory for {exp_info['code']}. Containment protocols active.", "intent": "QUERY_SAFETY", "action": None, "source": "OFFLINE_CORE"}



        # 7. Experiment queries

        results = db.search(msg)

        target_exp = results[0] if results else db.get("EXP-01")

        steps_preview = "\n".join([f"{s['step_number']}. **{s['title']}** ({s['time_estimate_mins']}m)" for s in target_exp.get("steps", [])])

        resp = f"### [{target_exp['id']}] {target_exp['code']}: {target_exp['title']}\n\n**Category:** {target_exp['category']} | **Facility:** {target_exp['facility']}\n\n**Scientific Objective:**\n{target_exp['objective']}\n\n**Protocol Sequence:**\n{steps_preview}"

        voice = f"{target_exp['title']}. Operating in {target_exp['facility']}. Objective: {target_exp['objective'][:130]}."

        return {"response": resp, "voice_text": voice, "intent": "QUERY_EXPERIMENT", "action": "SELECT_EXPERIMENT", "experiment_id": target_exp["id"], "source": "OFFLINE_CORE"}



offline_llm = OfflineLLMEngine()



# ==============================================================================
