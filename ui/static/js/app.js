/**
 * ARIA Main Cockpit Application Controller
 * Handles 7 Microgravity Protocols, Safety Interlocks, Vision Tools & Offline AI
 */

class AstronautApp {
  constructor() {
    this.experiments = [];
    this.activeExpId = 'EXP-01';
    this.currentState = null;
    this.stepStartTime = Date.now();
    this.stepTimerInterval = null;
    this.emergencies = [];
    this.activeAlert = null;

    this.init();
  }

  async init() {
    this.bindEvents();
    await this.loadExperiments();
    await this.loadEmergencies();
    await this.fetchProtocolState();
    this.startStepTimer();
    this.pollAlerts();
    setInterval(() => this.pollAlerts(), 3000);
  }

  bindEvents() {
    // Top bar sync button
    document.getElementById('btn-sync-ground')?.addEventListener('click', () => this.syncGroundControl());

    // VOX button
    document.getElementById('vox-toggle-btn')?.addEventListener('click', () => {
      if (window.voiceEngine) window.voiceEngine.toggleVox();
    });

    // Alert actions
    document.getElementById('btn-alert-ack')?.addEventListener('click', () => this.acknowledgeActiveAlert());
    document.getElementById('btn-alert-override')?.addEventListener('click', () => this.openSkipModal());

    // Protocol Step Actions
    document.getElementById('btn-confirm-step')?.addEventListener('click', () => this.confirmStep());
    document.getElementById('btn-skip-step')?.addEventListener('click', () => this.openSkipModal());

    // Skip Modal Form
    document.getElementById('skip-override-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.submitSkipOverride();
    });
    document.getElementById('btn-close-skip-modal')?.addEventListener('click', () => this.closeModal('skip-modal'));
    document.getElementById('btn-cancel-skip')?.addEventListener('click', () => this.closeModal('skip-modal'));

    // Emergency Modal
    document.getElementById('btn-close-emerg-modal')?.addEventListener('click', () => this.closeModal('emergency-modal'));
    document.getElementById('btn-ack-emerg')?.addEventListener('click', () => this.closeModal('emergency-modal'));

    // Collect Data Modal
    document.getElementById('btn-open-collect-modal')?.addEventListener('click', () => this.openModal('collect-modal'));
    document.getElementById('btn-close-collect-modal')?.addEventListener('click', () => this.closeModal('collect-modal'));
    document.getElementById('btn-cancel-collect')?.addEventListener('click', () => this.closeModal('collect-modal'));
    document.getElementById('btn-start-collect')?.addEventListener('click', () => this.launchDataCollector());

    // Collect chips
    document.querySelectorAll('.action-chip').forEach(chip => {
      chip.addEventListener('click', (e) => {
        const act = e.target.getAttribute('data-act');
        const input = document.getElementById('collect-action-input');
        if (input && act) input.value = act;
      });
    });

    // Vision Tools Quick Launchers
    document.getElementById('btn-launch-activity1')?.addEventListener('click', () => this.launchSubtool('activity-1'));
    document.getElementById('btn-launch-analyzer')?.addEventListener('click', () => this.launchSubtool('analyzer'));
    document.getElementById('btn-launch-train')?.addEventListener('click', () => this.launchSubtool('train'));
    document.getElementById('btn-open-reports')?.addEventListener('click', () => this.launchSubtool('reports'));

    // Chat Form
    document.getElementById('chat-form')?.addEventListener('submit', (e) => {
      e.preventDefault();
      this.handleChatSubmit();
    });

    // PTT Mic Button
    const micBtn = document.getElementById('btn-voice-record');
    if (micBtn) {
      micBtn.addEventListener('click', () => {
        if (window.voiceEngine) window.voiceEngine.toggleRecording();
      });
    }

    // Tactical Command Chips
    document.querySelectorAll('.command-chips .chip-btn').forEach(chip => {
      chip.addEventListener('click', (e) => {
        const cmd = e.target.getAttribute('data-cmd');
        if (cmd) {
          const input = document.getElementById('chat-input-text');
          if (input) input.value = cmd;
          this.handleChatSubmit();
        }
      });
    });
  }

  // =========================================================================
  // EXPERIMENT PROTOCOL MANAGEMENT
  // =========================================================================
  async loadExperiments() {
    try {
      const res = await fetch('/api/experiments');
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        this.experiments = data.experiments;
        this.renderExperimentsList();
      }
    } catch (e) {
      console.error("Failed loading experiments:", e);
    }
  }

  renderExperimentsList() {
    const listEl = document.getElementById('experiments-list');
    if (!listEl) return;
    listEl.innerHTML = '';

    this.experiments.forEach(exp => {
      const item = document.createElement('div');
      item.className = `exp-item ${exp.id === this.activeExpId ? 'active' : ''}`;
      item.dataset.id = exp.id;
      item.innerHTML = `
        <div class="exp-item-top">
          <span class="exp-code">${exp.id} // ${exp.code}</span>
          <span class="exp-steps-badge">${exp.steps ? exp.steps.length : 0} STEPS</span>
        </div>
        <div class="exp-title">${exp.title}</div>
        <div class="exp-facility">${exp.facility || ''}</div>
      `;
      item.addEventListener('click', () => this.selectExperiment(exp.id));
      listEl.appendChild(item);
    });
  }

  async selectExperiment(expId) {
    if (this.activeExpId === expId && this.currentState) return;
    try {
      const res = await fetch('/api/protocol/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ experiment_id: expId })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        this.activeExpId = expId;
        this.currentState = data.state;
        this.stepStartTime = Date.now();
        this.renderActiveExperiment();
        this.renderExperimentsList();
        this.showToast(`Activated: ${this.currentState.active_experiment.code}`);
        if (window.voiceEngine) window.voiceEngine.playTone(580, 'sine', 0.12);
      }
    } catch (e) {
      console.error("Failed selecting experiment:", e);
    }
  }

  async fetchProtocolState() {
    try {
      const res = await fetch('/api/protocol/state');
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.state) {
        this.currentState = data.state;
        if (data.state.active_experiment) {
          this.activeExpId = data.state.active_experiment.id;
        }
        this.renderActiveExperiment();
      }
    } catch (e) {
      console.error("Failed fetching state:", e);
    }
  }

  renderActiveExperiment() {
    if (!this.currentState) return;
    const exp = this.currentState.active_experiment;
    if (!exp) return;

    // Header metadata
    const idEl = document.getElementById('protocol-exp-id');
    const safetyEl = document.getElementById('protocol-safety-level');
    const titleEl = document.getElementById('protocol-exp-title');
    const objEl = document.getElementById('protocol-exp-objective');

    if (idEl) idEl.textContent = `${exp.id} // ${exp.code}`;
    if (safetyEl) safetyEl.textContent = exp.safety_level || 'Standard Precaution';
    if (titleEl) titleEl.textContent = exp.title;
    if (objEl) objEl.textContent = exp.objective;

    // Environmental strip
    const envStrip = document.getElementById('protocol-env-strip');
    const fullExp = this.experiments.find(e => e.id === exp.id) || exp;
    if (envStrip && fullExp.environmental_requirements) {
      const env = fullExp.environmental_requirements;
      envStrip.innerHTML = `
        <div>TEMP: <span>${env.temperature_celsius || '21.5°C'}</span></div>
        <div>CO2: <span>${env.co2_pct || '< 0.40%'}</span></div>
        <div>HUMIDITY: <span>${env.relative_humidity_pct || '45-55%'}</span></div>
        <div>RAD LIMIT: <span>${env.radiation_limit_micro_sv_h || '30.0 µSv/h'}</span></div>
      `;
    }

    // Progress bar
    const fillEl = document.getElementById('protocol-progress-fill');
    const textEl = document.getElementById('protocol-progress-text');
    const total = this.currentState.total_steps || 1;
    const completedCount = this.currentState.completed_steps ? this.currentState.completed_steps.length : 0;
    const pct = this.currentState.completion_percentage || 0;

    if (fillEl) fillEl.style.width = `${pct}%`;
    if (textEl) textEl.textContent = `${pct}% COMPLETED (${completedCount}/${total})`;

    // Active step card
    const currStep = this.currentState.current_step;
    if (currStep) {
      document.getElementById('step-card-badge').textContent = `STEP ${currStep.step_number} OF ${total}`;
      document.getElementById('step-headline').textContent = currStep.title;
      document.getElementById('step-instruction-box').textContent = currStep.action;

      const hazardBox = document.getElementById('step-hazard-box');
      const warningText = document.getElementById('step-warning-text');
      if (currStep.warning) {
        if (hazardBox) hazardBox.style.display = 'flex';
        if (warningText) warningText.textContent = currStep.warning;
      } else {
        if (hazardBox) hazardBox.style.display = 'none';
      }
    }

    // Roadmap checklist
    this.renderChecklist();
  }

  renderChecklist() {
    const listEl = document.getElementById('step-checklist');
    if (!listEl || !this.currentState) return;
    listEl.innerHTML = '';

    const steps = this.currentState.all_steps || [];
    const completed = this.currentState.completed_steps || [];
    const currNum = this.currentState.current_step_number || 1;

    steps.forEach(step => {
      const sn = step.step_number;
      const isDone = completed.includes(sn);
      const isCurrent = sn === currNum;

      const item = document.createElement('div');
      item.className = `checklist-item ${isDone ? 'completed' : ''} ${isCurrent ? 'current' : ''}`;
      
      let icon = isDone ? '✓' : (isCurrent ? '▶' : sn);
      item.innerHTML = `
        <div class="checklist-left">
          <div class="checklist-status-icon">${icon}</div>
          <div>
            <div class="checklist-title">Step ${sn}: ${step.title}</div>
            <div class="checklist-meta">Est: ~${step.time_estimate_mins} min ${step.is_mandatory ? '• [MANDATORY]' : ''}</div>
          </div>
        </div>
      `;
      listEl.appendChild(item);
    });
  }

  startStepTimer() {
    if (this.stepTimerInterval) clearInterval(this.stepTimerInterval);
    this.stepTimerInterval = setInterval(() => {
      const elapsedSec = Math.floor((Date.now() - this.stepStartTime) / 1000);
      const mins = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
      const secs = String(elapsedSec % 60).padStart(2, '0');
      const timerEl = document.getElementById('step-timer-display');
      if (timerEl) timerEl.textContent = `${mins}:${secs}`;
    }, 1000);
  }

  async confirmStep() {
    try {
      const res = await fetch('/api/protocol/confirm-step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        this.currentState = data.state;
        this.stepStartTime = Date.now();
        this.renderActiveExperiment();
        if (window.voiceEngine) window.voiceEngine.playChime();
        this.showToast("Step Verified and Advanced!");

        if (data.state.feedback_voice) {
          this.appendChatMessage('bot', data.state.feedback_voice);
          if (window.voiceEngine) window.voiceEngine.speak(data.state.feedback_voice);
        }
      }
    } catch (e) {
      console.error("Failed confirming step:", e);
    }
  }

  openSkipModal() {
    const currStep = this.currentState?.current_step;
    const infoEl = document.getElementById('modal-step-info');
    if (infoEl && currStep) {
      infoEl.textContent = `Step ${currStep.step_number}: ${currStep.title}`;
    }
    this.openModal('skip-modal');
  }

  async submitSkipOverride() {
    const reason = document.getElementById('skip-reason-input')?.value || 'Operational constraint';
    const authCode = document.getElementById('skip-auth-code')?.value || 'AUTH-EVA-01';

    try {
      const res = await fetch('/api/protocol/skip-step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason, override_code: authCode })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        this.closeModal('skip-modal');
        this.currentState = data.state;
        this.stepStartTime = Date.now();
        this.renderActiveExperiment();
        this.showToast(`Step Skipped with Override: ${authCode}`);
        if (window.voiceEngine) window.voiceEngine.playTone(440, 'sawtooth', 0.2);
      }
    } catch (e) {
      console.error("Failed submitting skip override:", e);
    }
  }

  // =========================================================================
  // EMERGENCY CONTINGENCIES
  // =========================================================================
  async loadEmergencies() {
    try {
      const res = await fetch('/api/emergencies');
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.emergencies) {
        this.emergencies = data.emergencies;
        this.renderEmergencyButtons();
      }
    } catch (e) {
      console.error("Failed loading emergencies:", e);
    }
  }

  renderEmergencyButtons() {
    const grid = document.getElementById('emergency-grid');
    if (!grid) return;
    grid.innerHTML = '';

    this.emergencies.slice(0, 4).forEach(em => {
      const btn = document.createElement('button');
      btn.className = 'emergency-btn';
      btn.innerHTML = `
        <span>${em.code}</span>
        <small>${em.severity}</small>
      `;
      btn.addEventListener('click', () => this.openEmergencyModal(em.id));
      grid.appendChild(btn);
    });
  }

  openEmergencyModal(emergId) {
    const em = this.emergencies.find(e => e.id === emergId) || this.emergencies[0];
    if (!em) return;

    document.getElementById('emergency-modal-title').textContent = `🚨 EMERGENCY: ${em.title}`;
    const bodyEl = document.getElementById('emergency-modal-body');
    if (bodyEl) {
      const actionsHtml = (em.immediate_actions || []).map((act, i) => `
        <div style="padding:8px 12px;background:rgba(239,68,68,0.1);border-left:3px solid var(--red-critical);border-radius:4px;font-weight:600;font-size:0.88rem;">
          ${i+1}. ${act}
        </div>
      `).join('');

      const recoveryHtml = (em.recovery_steps || []).map(rec => `
        <li style="margin-left:18px;margin-top:4px;color:var(--text-secondary);font-size:0.85rem;">${rec}</li>
      `).join('');

      bodyEl.innerHTML = `
        <div style="display:flex;justify-content:space-between;font-family:var(--font-mono);font-size:0.8rem;">
          <span>CODE: <strong style="color:var(--red-critical);">${em.code}</strong></span>
          <span>SEVERITY: <strong style="color:var(--red-critical);">${em.severity}</strong></span>
          <span>ALARM: <strong>${em.audio_alarm}</strong></span>
        </div>
        <h4 style="color:var(--red-critical);letter-spacing:1px;font-size:0.85rem;margin-top:6px;">MANDATORY IMMEDIATE ACTIONS:</h4>
        <div style="display:flex;flex-direction:column;gap:6px;">${actionsHtml}</div>
        ${recoveryHtml ? `<h4 style="color:var(--green-nominal);letter-spacing:1px;font-size:0.85rem;margin-top:10px;">RECOVERY PROTOCOL:</h4><ul>${recoveryHtml}</ul>` : ''}
      `;
    }

    this.openModal('emergency-modal');
    if (window.voiceEngine) {
      window.voiceEngine.playAlert();
      window.voiceEngine.speak(`Emergency Alert! ${em.title}. Check immediate actions.`);
    }
  }

  // =========================================================================
  // SAFETY ALERTS POLLING
  // =========================================================================
  async pollAlerts() {
    try {
      const res = await fetch('/api/alerts');
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.alerts) {
        const unack = data.alerts.filter(a => !a.acknowledged);
        const bannerContainer = document.getElementById('alert-banner-container');
        if (unack.length > 0) {
          const topAlert = unack[0];
          this.activeAlert = topAlert;
          if (bannerContainer) bannerContainer.style.display = 'block';
          document.getElementById('alert-title').textContent = `[TIER ${topAlert.tier || 3} ${topAlert.severity}] ${topAlert.title}`;
          document.getElementById('alert-desc').textContent = topAlert.message;
        } else {
          if (bannerContainer) bannerContainer.style.display = 'none';
          this.activeAlert = null;
        }
      }
    } catch (e) {
      console.debug("Alert poll error:", e);
    }
  }

  async acknowledgeActiveAlert() {
    if (!this.activeAlert) return;
    try {
      await fetch('/api/alerts/acknowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alert_id: this.activeAlert.alert_id })
      });
      this.pollAlerts();
      this.showToast("Safety Alert Acknowledged");
    } catch (e) {
      console.error(e);
    }
  }

  // =========================================================================
  // AI CHAT & VOX ENGINE
  // =========================================================================
  async handleChatSubmit() {
    const input = document.getElementById('chat-input-text');
    if (!input) return;
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';
    this.appendChatMessage('user', msg);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      });
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.result) {
        const reply = data.result.response;
        this.appendChatMessage('bot', reply);
        if (window.voiceEngine && data.result.voice_text) {
          window.voiceEngine.speak(data.result.voice_text);
        }
        if (data.result.action === 'SELECT_EXPERIMENT' && data.result.experiment_id) {
          this.selectExperiment(data.result.experiment_id);
        }
        if (data.result.action === 'TRIGGER_EMERGENCY_MODAL' && data.result.emergency_id) {
          this.openEmergencyModal(data.result.emergency_id);
        }
        if (data.result.action === 'CONFIRM_STEP') {
          this.confirmStep();
        }
      }
    } catch (e) {
      this.appendChatMessage('bot', "Offline perception core communication timeout.");
    }
  }

  handleVoiceCommand(text) {
    this.appendChatMessage('user', `[VOX] ${text}`);
    const input = document.getElementById('chat-input-text');
    if (input) input.value = text;
    this.handleChatSubmit();
  }

  appendChatMessage(sender, text) {
    const transcript = document.getElementById('chat-transcript');
    if (!transcript) return;

    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender}`;
    
    // Markdown-like bold replacement
    const formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    bubble.innerHTML = `
      <span class="bubble-sender">${sender === 'user' ? 'COMMANDER RATHORE' : 'ARIA • AI ASSISTANT'}</span>
      <div class="bubble-content">${formatted}</div>
    `;

    transcript.appendChild(bubble);
    transcript.scrollTop = transcript.scrollHeight;
  }

  // =========================================================================
  // VISION MODULE LAUNCHERS
  // =========================================================================
  async launchSubtool(toolName, arg = '') {
    this.showToast(`Launching ${toolName.toUpperCase()} in desktop window...`);
    try {
      await fetch(`/api/launch/${toolName}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ arg: arg })
      });
    } catch (e) {
      console.error(`Failed launching ${toolName}:`, e);
    }
  }

  launchDataCollector() {
    const input = document.getElementById('collect-action-input');
    const act = input ? input.value.trim() : 'Walking';
    this.closeModal('collect-modal');
    this.launchSubtool('collect', act);
  }

  // =========================================================================
  // GROUND CONTROL SYNC
  // =========================================================================
  async syncGroundControl() {
    try {
      const res = await fetch('/api/audit-trail/sync', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        const count = data.sync?.synced_records || 0;
        this.showToast(`Telemetry & Flight Log Synced: ${count} records uplinked`);
        const badge = document.getElementById('hud-sync-badge');
        if (badge) badge.textContent = '0 PENDING UPLINK';
        if (window.voiceEngine) window.voiceEngine.playSuccess();
      }
    } catch (e) {
      this.showToast("Uplink sync failed.");
    }
  }

  // =========================================================================
  // UI UTILITIES
  // =========================================================================
  openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'flex';
  }

  closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
  }

  showToast(message) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.astronautApp = new AstronautApp();
});
