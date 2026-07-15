import { api } from "../api.js";
import { getUser } from "../state.js";
import { balanceCardsHtml } from "../components/balance_card.js";
import { renderLeaveForm } from "../components/leave_form.js";

function statusBadge(status) {
  if (status === "approved") return `<span class="badge ok">Approved</span>`;
  if (status === "rejected") return `<span class="badge danger">Rejected</span>`;
  return `<span class="badge pending">Pending</span>`;
}

async function renderLeaveTable(container, userId) {
  const { leave: allLeave } = await api.listLeave({ user_id: userId });
  if (allLeave.length === 0) {
    container.innerHTML = `<div class="empty-state">No leave booked yet.</div>`;
    return;
  }

  const currentYear = String(new Date().getFullYear());
  const years = Array.from(new Set([currentYear, ...allLeave.map((l) => l.start_date.slice(0, 4))])).sort(
    (a, b) => b.localeCompare(a)
  );

  container.innerHTML = `
    <div class="actions-row" style="justify-content:flex-end; margin-bottom:10px;">
      <select id="my-leave-year-filter">
        <option value="">All years</option>
        ${years.map((y) => `<option value="${y}" ${y === currentYear ? "selected" : ""}>${y}</option>`).join("")}
      </select>
      <select id="my-leave-type-filter">
        <option value="">All types</option>
        <option value="holiday">Holiday only</option>
        <option value="sickness">Sickness only</option>
      </select>
    </div>
    <div id="my-leave-table-wrap"></div>
  `;

  const wrap = container.querySelector("#my-leave-table-wrap");
  const yearSelect = container.querySelector("#my-leave-year-filter");
  const typeSelect = container.querySelector("#my-leave-type-filter");

  function renderTable() {
    const yearFilter = yearSelect.value;
    const typeFilter = typeSelect.value;
    const filtered = allLeave.filter(
      (l) => (!typeFilter || l.type === typeFilter) && (!yearFilter || l.start_date.startsWith(yearFilter))
    );

    if (filtered.length === 0) {
      wrap.innerHTML = `<div class="empty-state">No ${typeFilter || ""} leave matches this filter${
        yearFilter ? ` for ${yearFilter}` : ""
      }.</div>`;
      return;
    }

    wrap.innerHTML = `
      <table>
        <thead><tr><th>Type</th><th>Dates</th><th>Days</th><th>Status</th><th>Notes</th><th></th></tr></thead>
        <tbody>
          ${filtered
            .map(
              (l) => `
            <tr>
              <td>${l.type === "holiday" ? "Holiday" : "Sickness"}</td>
              <td>${l.start_date} &rarr; ${l.end_date}</td>
              <td>${l.days}</td>
              <td>${statusBadge(l.status)}</td>
              <td>${l.notes || ""}</td>
              <td>${
                l.status === "pending"
                  ? `<button class="btn danger small" data-cancel="${l.id}">Cancel</button>`
                  : ""
              }</td>
            </tr>`
            )
            .join("")}
        </tbody>
      </table>
    `;

    wrap.querySelectorAll("[data-cancel]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await api.cancelLeave(btn.dataset.cancel);
        renderDashboard(container.closest("#app"));
      });
    });
  }

  yearSelect.addEventListener("change", renderTable);
  typeSelect.addEventListener("change", renderTable);
  renderTable();
}

export async function renderDashboard(container) {
  const user = getUser();
  container.innerHTML = `
    <h1>Welcome, ${user.name.split(" ")[0]}</h1>
    <p class="subtitle">Your holiday balance, sickness record, and leave history.</p>
    <div id="balance-cards"></div>
    <div id="leave-form"></div>
    <div class="card">
      <h3>Your leave history</h3>
      <div id="leave-table"></div>
    </div>
  `;

  const { balance } = await api.myBalance();
  container.querySelector("#balance-cards").innerHTML = balanceCardsHtml(balance);

  renderLeaveForm(container.querySelector("#leave-form"), {
    onCreated: () => renderDashboard(container),
  });

  await renderLeaveTable(container.querySelector("#leave-table"), user.id);
}
