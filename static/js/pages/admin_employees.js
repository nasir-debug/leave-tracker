import { api } from "../api.js";
import { renderLeaveForm } from "../components/leave_form.js";

function sicknessBadge(balance) {
  return balance.sickness.flagged
    ? `<span class="badge danger">Sickness flag</span>`
    : `<span class="badge ok">OK</span>`;
}

function holidayBadge(balance) {
  const h = balance.holiday;
  if (h.over_limit) return `<span class="badge danger">Over limit</span>`;
  if (h.would_exceed_if_pending_approved) return `<span class="badge warn">Pending would exceed</span>`;
  return `<span class="badge ok">OK</span>`;
}

function employeeRowHtml(e) {
  const h = e.balance.holiday;
  return `
    <tr data-row="${e.id}">
      <td>${e.name}<br><span style="color:var(--text-muted); font-size:12px;">${e.email}</span></td>
      <td>${e.role}</td>
      <td>${h.allowance_days} / ${h.carry_over_days} carry</td>
      <td>${h.remaining_days} left ${holidayBadge(e.balance)}</td>
      <td>${sicknessBadge(e.balance)}</td>
      <td class="actions-row">
        <button class="btn secondary small" data-edit="${e.id}">Edit</button>
        <button class="btn danger small" data-deactivate="${e.id}">Deactivate</button>
      </td>
    </tr>
    <tr class="edit-row" id="edit-row-${e.id}" style="display:none;"><td colspan="6"></td></tr>
  `;
}

function editFormHtml(e) {
  return `
    <form class="edit-employee-form" data-id="${e.id}">
      <div class="form-grid">
        <div class="form-row"><label>Name</label><input name="name" value="${e.name}" required /></div>
        <div class="form-row"><label>Email</label><input name="email" type="email" value="${e.email}" required /></div>
        <div class="form-row"><label>Role</label>
          <select name="role">
            <option value="employee" ${e.role === "employee" ? "selected" : ""}>Employee</option>
            <option value="admin" ${e.role === "admin" ? "selected" : ""}>Admin</option>
          </select>
        </div>
        <div class="form-row"><label>Holiday allowance (days/yr)</label>
          <input name="holiday_allowance_days" type="number" step="0.5" value="${e.holiday_allowance_days}" required />
        </div>
        <div class="form-row"><label>Carry-over days</label>
          <input name="carry_over_days" type="number" step="0.5" value="${e.carry_over_days}" required />
        </div>
        <div class="form-row"><label>Sickness alert: days (blank = org default)</label>
          <input name="sickness_alert_days" type="number" value="${e.sickness_alert_days ?? ""}" />
        </div>
        <div class="form-row"><label>Sickness alert: episodes (blank = org default)</label>
          <input name="sickness_alert_occurrences" type="number" value="${e.sickness_alert_occurrences ?? ""}" />
        </div>
        <div class="form-row"><label>New password (optional)</label>
          <input name="password" type="password" placeholder="Leave blank to keep current" />
        </div>
      </div>
      <div class="actions-row">
        <button class="btn" type="submit">Save</button>
        <button class="btn secondary" type="button" data-cancel-edit>Cancel</button>
      </div>
    </form>
  `;
}

export async function renderAdminEmployees(container) {
  container.innerHTML = `
    <h1>Employees</h1>
    <p class="subtitle">Manage employee records, allowances, and sickness thresholds.</p>
    <div class="card">
      <div class="actions-row" style="margin-bottom:12px;">
        <button class="btn" id="toggle-add">+ Add employee</button>
      </div>
      <div id="add-form" style="display:none;"></div>
    </div>
    <div class="card">
      <h3>All employees</h3>
      <table>
        <thead><tr><th>Name</th><th>Role</th><th>Allowance/Carry</th><th>Holiday</th><th>Sickness</th><th></th></tr></thead>
        <tbody id="employee-rows"></tbody>
      </table>
    </div>
    <div class="card">
      <h3>Book leave on behalf of an employee</h3>
      <div id="book-for-form"></div>
    </div>
  `;

  const { employees } = await api.listEmployees();
  const tbody = container.querySelector("#employee-rows");
  tbody.innerHTML = employees.map(employeeRowHtml).join("");

  tbody.querySelectorAll("[data-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.dataset.edit;
      const emp = employees.find((e) => String(e.id) === id);
      const row = document.getElementById(`edit-row-${id}`);
      const cell = row.querySelector("td");
      const showing = row.style.display !== "none";
      tbody.querySelectorAll(".edit-row").forEach((r) => (r.style.display = "none"));
      if (showing) return;
      cell.innerHTML = editFormHtml(emp);
      row.style.display = "";

      cell.querySelector("[data-cancel-edit]").addEventListener("click", () => {
        row.style.display = "none";
      });

      cell.querySelector("form").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const fd = new FormData(ev.target);
        const payload = {
          name: fd.get("name"),
          email: fd.get("email"),
          role: fd.get("role"),
          holiday_allowance_days: fd.get("holiday_allowance_days"),
          carry_over_days: fd.get("carry_over_days"),
          sickness_alert_days: fd.get("sickness_alert_days") || null,
          sickness_alert_occurrences: fd.get("sickness_alert_occurrences") || null,
        };
        if (fd.get("password")) payload.password = fd.get("password");
        await api.updateEmployee(id, payload);
        renderAdminEmployees(container);
      });
    });
  });

  tbody.querySelectorAll("[data-deactivate]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Deactivate this employee? They will no longer be able to log in.")) return;
      await api.deactivateEmployee(btn.dataset.deactivate);
      renderAdminEmployees(container);
    });
  });

  const toggleAdd = container.querySelector("#toggle-add");
  const addForm = container.querySelector("#add-form");
  toggleAdd.addEventListener("click", () => {
    addForm.style.display = addForm.style.display === "none" ? "" : "none";
  });
  addForm.innerHTML = `
    <form id="create-employee-form">
      <div class="form-grid">
        <div class="form-row"><label>Name</label><input name="name" required /></div>
        <div class="form-row"><label>Email</label><input name="email" type="email" required /></div>
        <div class="form-row"><label>Password</label><input name="password" type="password" required /></div>
        <div class="form-row"><label>Role</label>
          <select name="role"><option value="employee">Employee</option><option value="admin">Admin</option></select>
        </div>
        <div class="form-row"><label>Start date</label><input name="start_date" type="date" required /></div>
        <div class="form-row"><label>Holiday allowance (days/yr)</label><input name="holiday_allowance_days" type="number" step="0.5" value="25" required /></div>
        <div class="form-row"><label>Carry-over days</label><input name="carry_over_days" type="number" step="0.5" value="0" required /></div>
      </div>
      <div id="create-error"></div>
      <button class="btn" type="submit">Create employee</button>
    </form>
  `;
  addForm.querySelector("#create-employee-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    const errorEl = addForm.querySelector("#create-error");
    errorEl.innerHTML = "";
    try {
      await api.createEmployee({
        name: fd.get("name"),
        email: fd.get("email"),
        password: fd.get("password"),
        role: fd.get("role"),
        start_date: fd.get("start_date"),
        holiday_allowance_days: fd.get("holiday_allowance_days"),
        carry_over_days: fd.get("carry_over_days"),
      });
      renderAdminEmployees(container);
    } catch (err) {
      errorEl.innerHTML = `<div class="error-banner">${err.message}</div>`;
    }
  });

  renderLeaveForm(container.querySelector("#book-for-form"), {
    employees,
    onCreated: () => renderAdminEmployees(container),
  });
}
