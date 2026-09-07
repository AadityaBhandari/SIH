/**
 * ARIA Telemetry HUD Controller
 * Live habitat environment sensors, orbital parameters & MET clock updates
 */

class TelemetryHUD {
  constructor() {
    this.pollInterval = null;
    this.init();
  }

  init() {
    this.fetchTelemetry();
    this.pollInterval = setInterval(() => this.fetchTelemetry(), 2000);
  }

  async fetchTelemetry() {
    try {
      const res = await fetch('/api/telemetry');
      if (!res.ok) return;
      const data = await res.json();
      if (data.status === 'SUCCESS' && data.telemetry) {
        this.renderTelemetry(data.telemetry);
      }
    } catch (err) {
      console.debug("Telemetry fetch wait:", err.message);
    }
  }

  renderTelemetry(tele) {
    // 1. MET clock & Flight day
    if (tele.met) {
      const metEl = document.getElementById('hud-met-clock');
      const fdEl = document.getElementById('hud-flight-day');
      if (metEl && tele.met.formatted) metEl.textContent = tele.met.formatted;
      if (fdEl && tele.met.flight_day) fdEl.textContent = tele.met.flight_day;
    }

    // 2. Orbit & LOS
    if (tele.orbit) {
      const orbitEl = document.getElementById('hud-orbit-los');
      if (orbitEl) {
        orbitEl.innerHTML = `<span class="status-dot"></span> ORBIT ${tele.orbit.altitude_km} KM | LOS ${tele.orbit.los_ground_sync_in_mins}M`;
      }
    }

    // 3. Cabin environment sensors
    const env = tele.cabin_environment || {};
    this.updateTile('sensor-o2', env.o2_pct ? `${env.o2_pct.value}%` : '--', env.o2_pct?.status);
    this.updateTile('sensor-co2', env.co2_pct ? `${env.co2_pct.value}%` : '--', env.co2_pct?.status);
    this.updateTile('sensor-press', env.pressure_kpa ? `${env.pressure_kpa.value} kPa` : '--', env.pressure_kpa?.status);
    this.updateTile('sensor-microg', env.microgravity_g ? `${env.microgravity_g.value} g` : '--', env.microgravity_g?.status);
    this.updateTile('sensor-rad', env.radiation_rate ? `${env.radiation_rate.value} µSv/h` : '--', env.radiation_rate?.status);

    // 4. Facility Telemetry
    const fac = tele.facility_telemetry || {};
    if (fac.lsg_negative_pressure_in_wg) {
      const lsg = fac.lsg_negative_pressure_in_wg;
      this.updateTile('sensor-lsg', `${lsg.value} in.wg`, lsg.status);
    }
  }

  updateTile(elementId, valueText, status) {
    const tile = document.getElementById(elementId);
    if (!tile) return;
    const valSpan = tile.querySelector('.sensor-val');
    if (!valSpan) return;

    valSpan.textContent = valueText;
    valSpan.className = 'sensor-val';

    if (status && status.includes('CRITICAL')) {
      valSpan.classList.add('critical');
    } else if (status && (status.includes('WARNING') || status.includes('COMPROMISED'))) {
      valSpan.classList.add('warning');
    } else {
      valSpan.classList.add('nominal');
    }
  }
}

window.telemetryHud = new TelemetryHUD();
