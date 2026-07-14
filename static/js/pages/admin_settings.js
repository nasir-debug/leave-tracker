import { api } from "../api.js";

export async function renderAdminSettings(container) {
  container.innerHTML = `
    <h1>Organisation settings</h1>
    <p class="subtitle">Defaults applied to employees without a per-employee override.</p>
    <div class="card"><div id="settings-form"></div></div>
  `;

  const { settings } = await api.getSettings();
  const el = container.querySelector("#settings-form");
  el.innerHTML = `
    <form id="org-settings-form">
      <div class="form-grid">
        <div class="form-row"><label>Default holiday allowance (days/yr)</label>
          <input name="default_holiday_allowance_days" type="number" step="0.5" value="${settings.default_holiday_allowance_days}" />
        </div>
        <div class="form-row"><label>Sickness alert threshold (days / 12mo)</label>
          <input name="sickness_alert_days" type="number" value="${settings.sickness_alert_days}" />
        </div>
        <div class="form-row"><label>Sickness alert threshold (episodes / 12mo)</label>
          <input name="sickness_alert_occurrences" type="number" value="${settings.sickness_alert_occurrences}" />
        </div>
      </div>
      <div id="settings-error"></div>
      <button class="btn" type="submit">Save settings</button>
    </form>
  `;

  el.querySelector("#org-settings-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    const errorEl = el.querySelector("#settings-error");
    errorEl.innerHTML = "";
    try {
      await api.updateSettings({
        default_holiday_allowance_days: fd.get("default_holiday_allowance_days"),
        sickness_alert_days: fd.get("sickness_alert_days"),
        sickness_alert_occurrences: fd.get("sickness_alert_occurrences"),
      });
      errorEl.innerHTML = `<div class="badge ok">Saved</div>`;
    } catch (err) {
      errorEl.innerHTML = `<div class="error-banner">${err.message}</div>`;
    }
  });
}
