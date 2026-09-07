# ==============================================================================
# ARIA Voice Service: Hybrid Offline & Online Speech-to-Text Engine
# Supports native Windows System.Speech offline dictation + SpeechRecognition
# ==============================================================================

import os
import sys
import io
import time
import tempfile
import threading
from typing import Optional, Dict, Any, List

# Try importing speech_recognition
try:
    import speech_recognition as sr
    HAS_SR = True
except ImportError:
    HAS_SR = False

# Try importing Windows System.Speech via pythonnet
HAS_WIN_SPEECH = False
SpeechRecognitionEngine = None
DictationGrammar = None
RecognizeMode = None

try:
    import clr
    gac_path = r'C:\Windows\Microsoft.NET\assembly\GAC_MSIL\System.Speech\v4.0_4.0.0.0__31bf3856ad364e35\System.Speech.dll'
    if os.path.isfile(gac_path):
        clr.AddReference(gac_path)
    else:
        clr.AddReference('System.Speech')
    from System.Speech.Recognition import (
        SpeechRecognitionEngine as SRE,
        DictationGrammar as DG,
        RecognizeMode as RM
    )
    SpeechRecognitionEngine = SRE
    DictationGrammar = DG
    RecognizeMode = RM
    HAS_WIN_SPEECH = True
except Exception as e:
    print(f"[ARIA VOICE WARNING] Windows System.Speech not available: {e}")
    HAS_WIN_SPEECH = False


class VoiceService:
    """Manages live microphone listening and audio file transcription."""

    def __init__(self):
        self.lock = threading.Lock()
        self.is_listening = False
        self.current_interim = ""
        self.final_transcripts: List[str] = []
        self.engine: Optional[Any] = None
        self.last_speech_time = time.time()
        self.start_time = 0.0

    def _create_engine(self):
        if not HAS_WIN_SPEECH:
            return None
        try:
            eng = SpeechRecognitionEngine()
            eng.SetInputToDefaultAudioDevice()
            eng.LoadGrammar(DictationGrammar())

            def _on_hypothesized(sender, e):
                with self.lock:
                    self.current_interim = e.Result.Text
                    self.last_speech_time = time.time()

            def _on_recognized(sender, e):
                with self.lock:
                    txt = e.Result.Text
                    if txt:
                        self.final_transcripts.append(txt)
                        self.current_interim = ""
                        self.last_speech_time = time.time()

            eng.SpeechHypothesized += _on_hypothesized
            eng.SpeechRecognized += _on_recognized
            return eng
        except Exception as e:
            print(f"[ARIA VOICE ERROR] Failed creating speech engine: {e}")
            return None

    def start_live_listening(self) -> Dict[str, Any]:
        """Starts asynchronous microphone listening on default audio device."""
        with self.lock:
            if self.is_listening:
                return {"status": "SUCCESS", "listening": True, "message": "Already listening"}

            self.current_interim = ""
            self.final_transcripts.clear()
            self.last_speech_time = time.time()
            self.start_time = time.time()

            self.engine = self._create_engine()
            if self.engine:
                try:
                    self.engine.RecognizeAsync(RecognizeMode.Multiple)
                    self.is_listening = True
                    print("[ARIA VOICE] Live microphone recognition active.")
                    return {"status": "SUCCESS", "listening": True}
                except Exception as e:
                    print(f"[ARIA VOICE ERROR] Start failed: {e}")
                    return {"status": "ERROR", "message": str(e)}
            else:
                self.is_listening = True
                return {"status": "SUCCESS", "listening": True, "mode": "browser_wav_only"}

    def get_live_status(self) -> Dict[str, Any]:
        """Returns live transcription updates for real-time UI typing."""
        with self.lock:
            finals_str = " ".join(self.final_transcripts).strip()
            if finals_str and self.current_interim:
                full_text = f"{finals_str} {self.current_interim}"
            elif finals_str:
                full_text = finals_str
            else:
                full_text = self.current_interim

            return {
                "listening": self.is_listening,
                "interim": self.current_interim,
                "finals": list(self.final_transcripts),
                "full_transcript": full_text.strip(),
                "duration_seconds": round(time.time() - self.start_time, 1) if self.is_listening else 0.0,
                "silence_seconds": round(time.time() - self.last_speech_time, 1) if self.is_listening else 0.0
            }

    def stop_live_listening(self) -> Dict[str, Any]:
        """Stops live listening and returns the finalized transcript."""
        with self.lock:
            if not self.is_listening:
                return {"status": "SUCCESS", "listening": False, "transcript": ""}

            self.is_listening = False

            finals_str = " ".join(self.final_transcripts).strip()
            if finals_str and self.current_interim:
                transcript = f"{finals_str} {self.current_interim}".strip()
            elif finals_str:
                transcript = finals_str
            else:
                transcript = self.current_interim.strip()

            if self.engine:
                try:
                    self.engine.RecognizeAsyncCancel()
                except Exception:
                    pass
                try:
                    self.engine.Dispose()
                except Exception:
                    pass
                self.engine = None

            print(f"[ARIA VOICE] Listening stopped. Final: '{transcript}'")
            return {"status": "SUCCESS", "listening": False, "transcript": transcript}

    def transcribe_wav(self, wav_bytes: bytes) -> str:
        """Transcribes WAV audio using Google (online) or Windows System.Speech (offline)."""
        if not wav_bytes or len(wav_bytes) < 100:
            return ""

        # Attempt 1: Online Google Speech Recognition
        if HAS_SR:
            try:
                r = sr.Recognizer()
                with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                    audio_data = r.record(source)
                result = r.recognize_google(audio_data)
                if result:
                    print(f"[ARIA VOICE] Google STT result: '{result}'")
                    return result.strip()
            except Exception as e:
                pass

        # Attempt 2: Offline Windows System.Speech
        if HAS_WIN_SPEECH:
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    temp_path = tmp.name
                    tmp.write(wav_bytes)

                eng = SpeechRecognitionEngine()
                eng.LoadGrammar(DictationGrammar())
                eng.SetInputToWaveFile(temp_path)
                res = eng.Recognize()
                eng.Dispose()
                if res and res.Text:
                    print(f"[ARIA VOICE] Windows offline STT result: '{res.Text}'")
                    return res.Text.strip()
            except Exception as e:
                print(f"[ARIA VOICE ERROR] Offline transcription error: {e}")
            finally:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass

        return ""


# Singleton instance
voice_service = VoiceService()
