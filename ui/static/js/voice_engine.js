/**
 * ARIA Voice Engine & Procedural Audio Synthesizer
 * Offline-first Speech-to-Text & Live Voice Recognition Suite
 * 
 * Features:
 * 1. Real-time typing into #chat-input-text as the astronaut speaks
 * 2. Native Windows System.Speech live dictation via /api/voice/live/*
 * 3. In-browser 16kHz mono WAV recording & /api/voice/transcribe fallback
 * 4. Reactive AudioContext frequency visualizer on .wave-bar
 * 5. Web Speech API (webkitSpeechRecognition) with interimResults: true
 * 6. Synthesized audio chimes & text-to-speech feedback
 */

class VoiceEngine {
  constructor() {
    this.isRecording = false;
    this.voxActive = false;
    this.audioCtx = null;
    this.mediaStream = null;
    this.analyser = null;
    this.scriptProcessor = null;
    this.pcmChunks = [];
    this.pollInterval = null;
    this.animFrameId = null;
    this.recognition = null;
    this.synthesis = window.speechSynthesis || null;
    this.lastRecognizedText = '';

    this.initAudioContext();
    this.initSpeechRecognition();
  }

  initAudioContext() {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.audioCtx = new AudioContext();
      }
    } catch (e) {
      console.warn("[ARIA VOICE] Web Audio API initialization:", e);
    }
  }

  playTone(freq, type = 'sine', duration = 0.15, delay = 0) {
    if (!this.audioCtx) return;
    try {
      if (this.audioCtx.state === 'suspended') {
        this.audioCtx.resume();
      }
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime + delay);

      gain.gain.setValueAtTime(0.08, this.audioCtx.currentTime + delay);
      gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + delay + duration);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);

      osc.start(this.audioCtx.currentTime + delay);
      osc.stop(this.audioCtx.currentTime + delay + duration);
    } catch (e) {}
  }

  playChime() {
    this.playTone(880, 'sine', 0.1, 0);
    this.playTone(1320, 'sine', 0.2, 0.08);
  }

  playAlert() {
    this.playTone(520, 'sawtooth', 0.18, 0);
    this.playTone(390, 'sawtooth', 0.28, 0.16);
  }

  playSuccess() {
    this.playTone(660, 'sine', 0.1, 0);
    this.playTone(880, 'sine', 0.1, 0.08);
    this.playTone(1174, 'sine', 0.25, 0.16);
  }

  speak(text) {
    if (!this.synthesis) return;
    try {
      this.synthesis.cancel();
      const cleanText = text.replace(/[*_#`]/g, '').trim();
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;

      const waveBars = document.querySelectorAll('.wave-bar');
      utterance.onstart = () => {
        waveBars.forEach(b => b.style.animationDuration = '0.35s');
      };
      utterance.onend = () => {
        waveBars.forEach(b => b.style.animationDuration = '1.2s');
      };

      this.synthesis.speak(utterance);
    } catch (e) {}
  }

  initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    try {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = 'en-US';

      this.recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const trans = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += trans + ' ';
          } else {
            interimTranscript += trans;
          }
        }

        const text = (finalTranscript + interimTranscript).trim();
        if (text) {
          this.updateInputText(text);
          this.lastRecognizedText = text;
        }
      };

      this.recognition.onerror = (event) => {
        // In WebView2, 'network' error occurs because Google Speech cloud is not available.
        // Fall back silently to native backend transcription.
        if (event.error !== 'no-speech') {
          console.debug("[ARIA VOICE] Web Speech info:", event.error);
        }
      };

      this.recognition.onend = () => {
        if (this.isRecording && this.voxActive) {
          try { this.recognition.start(); } catch (e) {}
        }
      };
    } catch (e) {
      console.debug("[ARIA VOICE] SpeechRecognition init:", e);
    }
  }

  updateInputText(text) {
    const input = document.getElementById('chat-input-text');
    if (input && text) {
      input.value = text;
      // Focus and move cursor to end
      input.selectionStart = input.selectionEnd = input.value.length;
    }
  }

  // =========================================================================
  // AUDIO RECORDING & VISUALIZATION PIPELINE
  // =========================================================================

  async startRecording(isVox = false) {
    if (this.isRecording) return;
    this.isRecording = true;
    this.lastRecognizedText = '';
    this.pcmChunks = [];

    // 1. Update UI to Active Recording State
    const micBtn = document.getElementById('btn-voice-record');
    if (micBtn) micBtn.classList.add('recording');

    const input = document.getElementById('chat-input-text');
    if (input) {
      input.dataset.oldPlaceholder = input.placeholder;
      input.placeholder = '🎤 LISTENING... Speak now into microphone...';
    }

    this.playTone(700, 'sine', 0.12);
    if (window.astronautApp) {
      window.astronautApp.showToast(isVox ? 'VOX Hands-Free Listening...' : '🎤 Microphone Listening... Speak your command');
    }

    // 2. Request Browser Microphone Stream & Setup AudioContext Analyser
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        this.mediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });

        if (!this.audioCtx || this.audioCtx.state === 'closed') {
          const AudioContext = window.AudioContext || window.webkitAudioContext;
          this.audioCtx = new AudioContext();
        }
        if (this.audioCtx.state === 'suspended') {
          await this.audioCtx.resume();
        }

        const source = this.audioCtx.createMediaStreamSource(this.mediaStream);
        this.analyser = this.audioCtx.createAnalyser();
        this.analyser.fftSize = 64;
        source.connect(this.analyser);

        // Setup real-time voice visualizer loop
        this.startVisualizer();

        // Setup PCM audio capture (16kHz downsampled)
        const bufferSize = 4096;
        this.scriptProcessor = this.audioCtx.createScriptProcessor(bufferSize, 1, 1);
        const inputSampleRate = this.audioCtx.sampleRate;

        this.scriptProcessor.onaudioprocess = (e) => {
          if (!this.isRecording) return;
          const inputData = e.inputBuffer.getChannelData(0);
          const downsampled = this.downsampleBuffer(inputData, inputSampleRate, 16000);
          this.pcmChunks.push(downsampled);
        };

        source.connect(this.scriptProcessor);
        this.scriptProcessor.connect(this.audioCtx.destination);
      }
    } catch (err) {
      console.warn("[ARIA VOICE] Browser mic capture:", err);
    }

    // 3. Start Native Windows System.Speech Listener on Backend
    try {
      await fetch('/api/voice/live/start', { method: 'POST' });
    } catch (e) {
      console.debug("[ARIA VOICE] Backend live start:", e);
    }

    // 4. Poll Live Dictation Status from Backend
    this.pollInterval = setInterval(async () => {
      if (!this.isRecording) return;
      try {
        const res = await fetch('/api/voice/live/status');
        const data = await res.json();
        if (data.status === 'SUCCESS' && data.data) {
          const fullText = data.data.full_transcript;
          if (fullText && fullText.trim()) {
            this.updateInputText(fullText.trim());
            this.lastRecognizedText = fullText.trim();
          }

          // In VOX mode: auto-submit after 1.6s of silence following valid speech
          if (this.voxActive && data.data.silence_seconds >= 1.6 && this.lastRecognizedText) {
            this.handleAutoSubmit();
          }
        }
      } catch (e) {}
    }, 180);

    // 5. Also Start Web Speech API as parallel source (works in Chrome)
    if (this.recognition) {
      try {
        this.recognition.start();
      } catch (e) {}
    }
  }

  async stopRecording() {
    if (!this.isRecording) return;
    this.isRecording = false;

    // 1. Clear Polling & Visualizer
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    this.stopVisualizer();

    // 2. Stop Browser Audio Nodes
    if (this.scriptProcessor) {
      try { this.scriptProcessor.disconnect(); } catch (e) {}
      this.scriptProcessor = null;
    }
    if (this.analyser) {
      try { this.analyser.disconnect(); } catch (e) {}
      this.analyser = null;
    }
    if (this.mediaStream) {
      try {
        this.mediaStream.getTracks().forEach(t => t.stop());
      } catch (e) {}
      this.mediaStream = null;
    }

    // 3. Stop Web Speech API
    if (this.recognition) {
      try { this.recognition.stop(); } catch (e) {}
    }

    // 4. Reset UI
    const micBtn = document.getElementById('btn-voice-record');
    if (micBtn) micBtn.classList.remove('recording');

    const input = document.getElementById('chat-input-text');
    if (input) {
      input.placeholder = input.dataset.oldPlaceholder || 'Speak command or type query...';
    }

    // 5. Stop Backend Native Listener & Get Final Transcript
    let backendTranscript = '';
    try {
      const res = await fetch('/api/voice/live/stop', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.transcript) {
        backendTranscript = data.transcript.trim();
      }
    } catch (e) {}

    let finalCandidate = backendTranscript || this.lastRecognizedText || (input ? input.value.trim() : '');

    // 6. If no transcript was captured by live engine, transcribe recorded WAV buffer
    if (!finalCandidate && this.pcmChunks.length > 0) {
      try {
        const wavBlob = this.encodeWAV(this.pcmChunks, 16000);
        if (wavBlob && wavBlob.size > 2000) {
          const res = await fetch('/api/voice/transcribe', {
            method: 'POST',
            body: wavBlob
          });
          const result = await res.json();
          if (result.status === 'SUCCESS' && result.transcript) {
            finalCandidate = result.transcript.trim();
          }
        }
      } catch (e) {
        console.debug("[ARIA VOICE] WAV transcribe fallback:", e);
      }
    }

    // 7. Update input bar with final transcript
    if (finalCandidate) {
      this.updateInputText(finalCandidate);
      this.lastRecognizedText = finalCandidate;
      this.playChime();
      if (window.astronautApp) {
        window.astronautApp.showToast(`Recognized: "${finalCandidate}"`);
      }
    }

    return finalCandidate;
  }

  toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      this.startRecording(false);
    }
  }

  toggleVox() {
    this.voxActive = !this.voxActive;
    const toggleBtn = document.getElementById('vox-toggle-btn');
    if (toggleBtn) {
      toggleBtn.classList.toggle('active', this.voxActive);
    }

    if (this.voxActive) {
      this.startRecording(true);
      this.playChime();
      if (window.astronautApp) window.astronautApp.showToast("VOX Hands-Free Mode ACTIVE");
    } else {
      this.stopRecording();
      if (window.astronautApp) window.astronautApp.showToast("VOX Hands-Free DEACTIVATED");
    }
    return this.voxActive;
  }

  handleAutoSubmit() {
    const input = document.getElementById('chat-input-text');
    const msg = input ? input.value.trim() : '';
    if (msg && window.astronautApp) {
      this.lastRecognizedText = '';
      window.astronautApp.handleChatSubmit();
      this.playTone(1050, 'sine', 0.1);
    }
  }

  // =========================================================================
  // AUDIO VISUALIZER & ENCODER HELPERS
  // =========================================================================

  startVisualizer() {
    const waveBars = document.querySelectorAll('.wave-bar');
    if (!waveBars.length || !this.analyser) return;

    waveBars.forEach(b => b.style.animation = 'none');
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);

    const update = () => {
      if (!this.isRecording || !this.analyser) return;
      this.analyser.getByteFrequencyData(dataArray);

      let sum = 0;
      for (let i = 0; i < waveBars.length; i++) {
        const val = dataArray[i * 2] || 0;
        sum += val;
        const height = Math.max(6, Math.min(32, (val / 255) * 34));
        waveBars[i].style.height = `${height}px`;
      }

      this.animFrameId = requestAnimationFrame(update);
    };

    update();
  }

  stopVisualizer() {
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = null;
    }
    const waveBars = document.querySelectorAll('.wave-bar');
    waveBars.forEach(b => {
      b.style.height = '';
      b.style.animation = '';
    });
  }

  downsampleBuffer(buffer, inputRate, outputRate = 16000) {
    if (outputRate === inputRate) return buffer;
    const ratio = inputRate / outputRate;
    const newLen = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLen);
    let offsetResult = 0;
    let offsetBuffer = 0;

    while (offsetResult < result.length) {
      const nextOffset = Math.round((offsetResult + 1) * ratio);
      let accum = 0, count = 0;
      for (let i = offsetBuffer; i < nextOffset && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = count ? accum / count : 0;
      offsetResult++;
      offsetBuffer = nextOffset;
    }
    return result;
  }

  encodeWAV(chunks, sampleRate = 16000) {
    let totalLen = 0;
    for (const c of chunks) totalLen += c.length;

    const merged = new Float32Array(totalLen);
    let offset = 0;
    for (const c of chunks) {
      merged.set(c, offset);
      offset += c.length;
    }

    const buffer = new ArrayBuffer(44 + merged.length * 2);
    const view = new DataView(buffer);

    function writeString(offset, string) {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    }

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + merged.length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, merged.length * 2, true);

    offset = 44;
    for (let i = 0; i < merged.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, merged[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return new Blob([view], { type: 'audio/wav' });
  }
}

window.voiceEngine = new VoiceEngine();
