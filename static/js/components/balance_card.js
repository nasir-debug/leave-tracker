export function balanceCardsHtml(balance) {
  const h = balance.holiday;
  const s = balance.sickness;

  const holidayBadge = h.over_limit
    ? `<span class="badge danger">Over limit</span>`
    : h.would_exceed_if_pending_approved
    ? `<span class="badge warn">Pending would exceed</span>`
    : `<span class="badge ok">Within allowance</span>`;

  const sicknessBadge = s.flagged
    ? `<span class="badge danger">Threshold exceeded</span>`
    : `<span class="badge ok">Normal</span>`;

  return `
    <div class="card-grid">
      <div class="card">
        <h3>Holiday balance (${h.year}) ${holidayBadge}</h3>
        <div class="card-grid" style="margin-top:10px; grid-template-columns: repeat(3, 1fr);">
          <div class="stat">
            <span class="value">${h.remaining_days}</span>
            <span class="label">Remaining days</span>
          </div>
          <div class="stat">
            <span class="value">${h.approved_used_days}</span>
            <span class="label">Used (approved)</span>
          </div>
          <div class="stat">
            <span class="value">${h.pending_days}</span>
            <span class="label">Pending requests</span>
          </div>
        </div>
        <p style="margin-top:10px;">
          ${
            h.prorated
              ? `Pro-rated allowance: ${h.effective_allowance_days} days for ${h.year} (standard allowance is ${h.allowance_days} days/yr, adjusted for a mid-year start date).`
              : `Allowance ${h.allowance_days} days for ${h.year} (Jan 1 &ndash; Dec 31).`
          }
        </p>
      </div>
      <div class="card">
        <h3>Sickness (rolling 12mo) ${sicknessBadge}</h3>
        <div class="card-grid" style="margin-top:10px; grid-template-columns: repeat(2, 1fr);">
          <div class="stat">
            <span class="value">${s.rolling_sick_days}</span>
            <span class="label">Sick days / ${s.threshold_days} limit</span>
          </div>
          <div class="stat">
            <span class="value">${s.rolling_occurrences}</span>
            <span class="label">Episodes / ${s.threshold_occurrences} limit</span>
          </div>
        </div>
      </div>
    </div>
  `;
}
