import { api } from "../api.js";
import { renderCalendarMonth } from "../components/calendar_grid.js";

let viewYear, viewMonth;

export async function renderCalendarPage(container) {
  const today = new Date();
  if (!viewYear) {
    viewYear = today.getFullYear();
    viewMonth = today.getMonth() + 1;
  }

  container.innerHTML = `
    <h1>Team calendar</h1>
    <p class="subtitle">Booked holidays and sickness across the team.</p>
    <div class="card"><div id="cal-root"></div></div>
  `;

  await loadAndRender(container.querySelector("#cal-root"));
}

async function loadAndRender(root) {
  const monthParam = `${viewYear}-${String(viewMonth).padStart(2, "0")}`;
  const { entries } = await api.getCalendar(monthParam);

  renderCalendarMonth(root, {
    year: viewYear,
    month: viewMonth,
    entries,
    onPrev: () => {
      viewMonth -= 1;
      if (viewMonth < 1) { viewMonth = 12; viewYear -= 1; }
      loadAndRender(root);
    },
    onNext: () => {
      viewMonth += 1;
      if (viewMonth > 12) { viewMonth = 1; viewYear += 1; }
      loadAndRender(root);
    },
  });
}
