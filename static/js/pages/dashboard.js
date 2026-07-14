import { api } from "../api.js";
import { getUser } from "../state.js";
import { balanceCardsHtml } from "../components/balance_card.js";
import { renderLeaveForm } from "../components/leave_form.js";

function statusBadge(status) {
  if (status === "approved") return `<span class="badge ok">Approved</span>`;
  if (status === "rejected") return `<span class="badge danger">Rejected</span>`;
  return `<span class="badge pending">Pending</span>`;
}

async function renderLeaveTable(container) {
  const { leave } = await api.listLeave();
  if (leave.length === 0) {
    container.innerHTML = `<div class="empty-state">No leave booked yet.</div>`;
    return;
  }
  container.innerHTML = `
    <table>
      <thead><tr><th>Type</th><th>Dates</th><th>Days</th><th>Status</th><th>Notes</th><th></th></tr></thead>
      <tbody>
        ${leave
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

  container.querySelectorAll("[data-cancel]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await api.cancelLeave(btn.dataset.cancel);
      renderDashboard(container.closest("#app"));
    });
  });
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

  await renderLeaveTable(container.querySelector("#leave-table"));
}
