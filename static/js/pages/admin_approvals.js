import { api } from "../api.js";

export async function renderAdminApprovals(container) {
  container.innerHTML = `
    <h1>Approvals</h1>
    <p class="subtitle">Pending holiday requests awaiting a decision. Sickness is auto-recorded and doesn't need approval.</p>
    <div class="card"><div id="pending-list"></div></div>
    <div class="card">
      <h3>Recent decisions</h3>
      <div id="decided-list"></div>
    </div>
  `;

  await loadPending(container);
  await loadDecided(container);
}

async function loadPending(container) {
  const el = container.querySelector("#pending-list");
  const { leave } = await api.listLeave({ status: "pending" });
  if (leave.length === 0) {
    el.innerHTML = `<div class="empty-state">No pending requests.</div>`;
    return;
  }
  el.innerHTML = `
    <table>
      <thead><tr><th>Employee</th><th>Dates</th><th>Days</th><th>Notes</th><th></th></tr></thead>
      <tbody>
        ${leave
          .map(
            (l) => `
          <tr>
            <td>${l.user_name}</td>
            <td>${l.start_date} &rarr; ${l.end_date}</td>
            <td>${l.days}</td>
            <td>${l.notes || ""}</td>
            <td class="actions-row">
              <button class="btn small" data-approve="${l.id}">Approve</button>
              <button class="btn danger small" data-reject="${l.id}">Reject</button>
            </td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;

  el.querySelectorAll("[data-approve]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await api.decideLeave(btn.dataset.approve, "approved");
      renderAdminApprovals(container.closest("#app"));
    })
  );
  el.querySelectorAll("[data-reject]").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await api.decideLeave(btn.dataset.reject, "rejected");
      renderAdminApprovals(container.closest("#app"));
    })
  );
}

async function loadDecided(container) {
  const el = container.querySelector("#decided-list");
  const [approved, rejected] = await Promise.all([
    api.listLeave({ status: "approved" }),
    api.listLeave({ status: "rejected" }),
  ]);
  const combined = [...approved.leave, ...rejected.leave]
    .sort((a, b) => (a.decided_at < b.decided_at ? 1 : -1))
    .slice(0, 15);

  if (combined.length === 0) {
    el.innerHTML = `<div class="empty-state">No decisions yet.</div>`;
    return;
  }
  el.innerHTML = `
    <table>
      <thead><tr><th>Employee</th><th>Type</th><th>Dates</th><th>Status</th></tr></thead>
      <tbody>
        ${combined
          .map(
            (l) => `
          <tr>
            <td>${l.user_name}</td>
            <td>${l.type}</td>
            <td>${l.start_date} &rarr; ${l.end_date}</td>
            <td>${
              l.status === "approved"
                ? '<span class="badge ok">Approved</span>'
                : '<span class="badge danger">Rejected</span>'
            }</td>
          </tr>`
          )
          .join("")}
      </tbody>
    </table>
  `;
}
