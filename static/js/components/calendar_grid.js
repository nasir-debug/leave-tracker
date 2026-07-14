const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function isoDate(y, m, d) {
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

function mondayIndex(jsWeekday) {
  // JS: Sun=0..Sat=6. We want Mon=0..Sun=6.
  return (jsWeekday + 6) % 7;
}

export function renderCalendarMonth(container, { year, month, entries, onPrev, onNext }) {
  const firstOfMonth = new Date(year, month - 1, 1);
  const daysInMonth = new Date(year, month, 0).getDate();
  const leadingBlanks = mondayIndex(firstOfMonth.getDay());

  const entriesByDay = {};
  for (const entry of entries) {
    let cur = new Date(entry.start_date + "T00:00:00");
    const end = new Date(entry.end_date + "T00:00:00");
    while (cur <= end) {
      if (cur.getFullYear() === year && cur.getMonth() + 1 === month) {
        const key = cur.getDate();
        (entriesByDay[key] = entriesByDay[key] || []).push(entry);
      }
      cur.setDate(cur.getDate() + 1);
    }
  }

  const monthName = firstOfMonth.toLocaleString("default", { month: "long" });

  let cells = "";
  for (let i = 0; i < leadingBlanks; i++) {
    cells += `<div class="calendar-day outside"></div>`;
  }
  for (let d = 1; d <= daysInMonth; d++) {
    const dayEntries = entriesByDay[d] || [];
    cells += `
      <div class="calendar-day">
        <div class="day-num">${d}</div>
        ${dayEntries
          .map(
            (e) => `<div class="calendar-entry ${e.type} ${e.status === "pending" ? "pending" : ""} ${
              e.user_flagged ? "flagged" : ""
            }" title="${e.user_name} — ${e.type}${e.status === "pending" ? " (pending)" : ""}">${e.user_name}</div>`
          )
          .join("")}
      </div>
    `;
  }
  const totalCells = leadingBlanks + daysInMonth;
  const trailingBlanks = (7 - (totalCells % 7)) % 7;
  for (let i = 0; i < trailingBlanks; i++) {
    cells += `<div class="calendar-day outside"></div>`;
  }

  container.innerHTML = `
    <div class="calendar-header">
      <button class="btn secondary small" id="cal-prev">&larr; Prev</button>
      <h2>${monthName} ${year}</h2>
      <button class="btn secondary small" id="cal-next">Next &rarr;</button>
    </div>
    <div class="calendar-grid">
      ${DOW.map((d) => `<div class="dow">${d}</div>`).join("")}
      ${cells}
    </div>
    <div class="legend">
      <span><span class="swatch" style="background:var(--holiday)"></span>Holiday</span>
      <span><span class="swatch" style="background:var(--sickness)"></span>Sickness</span>
      <span>Dashed border = pending approval</span>
      <span><span class="swatch" style="background:var(--danger)"></span>Red outline = employee over their limit</span>
    </div>
  `;

  container.querySelector("#cal-prev").addEventListener("click", onPrev);
  container.querySelector("#cal-next").addEventListener("click", onNext);
}
