import { api } from "../api.js";

export function renderLeaveForm(container, { employees = null, onCreated } = {}) {
  container.innerHTML = `
    <div class="card">
      <h3>Book leave</h3>
      <div id="leave-form-error"></div>
      <form id="leave-form">
        <div class="form-grid">
          <div class="form-row">
            <label>Type</label>
            <select name="type" required>
              <option value="holiday">Holiday</option>
              <option value="sickness">Sickness</option>
            </select>
          </div>
          ${
            employees
              ? `<div class="form-row">
                  <label>Employee</label>
                  <select name="user_id" required>
                    ${employees.map((e) => `<option value="${e.id}">${e.name}</option>`).join("")}
                  </select>
                </div>`
              : ""
          }
          <div class="form-row">
            <label>Start date</label>
            <input type="date" name="start_date" required />
          </div>
          <div class="form-row">
            <label>End date</label>
            <input type="date" name="end_date" required />
          </div>
        </div>
        <div class="form-row">
          <label>Notes (optional)</label>
          <textarea name="notes" rows="2"></textarea>
        </div>
        <button class="btn" type="submit">Submit</button>
      </form>
    </div>
  `;

  const form = container.querySelector("#leave-form");
  const errorEl = container.querySelector("#leave-form-error");
  const startInput = form.querySelector('input[name="start_date"]');
  const endInput = form.querySelector('input[name="end_date"]');

  startInput.addEventListener("change", () => {
    if (!startInput.value) return;
    endInput.min = startInput.value;
    // Keep the end-date picker's default month in sync with the start date
    // instead of always opening on today's month.
    if (!endInput.value || endInput.value < startInput.value) {
      endInput.value = startInput.value;
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.innerHTML = "";
    const fd = new FormData(form);
    const payload = {
      type: fd.get("type"),
      start_date: fd.get("start_date"),
      end_date: fd.get("end_date"),
      notes: fd.get("notes"),
    };
    if (employees) payload.user_id = Number(fd.get("user_id"));

    try {
      const res = await api.createLeave(payload);
      form.reset();
      if (onCreated) onCreated(res.leave);
    } catch (err) {
      errorEl.innerHTML = `<div class="error-banner">${err.message}</div>`;
    }
  });
}
