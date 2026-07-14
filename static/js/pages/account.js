import { api } from "../api.js";
import { getUser } from "../state.js";

export function renderAccount(container) {
  const user = getUser();
  container.innerHTML = `
    <h1>Account</h1>
    <p class="subtitle">Signed in as ${user.name} (${user.email}).</p>
    <div class="card" style="max-width:420px;">
      <h3>Change password</h3>
      <div id="password-error"></div>
      <div id="password-success"></div>
      <form id="password-form">
        <div class="form-row">
          <label>Current password</label>
          <input type="password" name="current_password" required autocomplete="current-password" />
        </div>
        <div class="form-row">
          <label>New password</label>
          <input type="password" name="new_password" required minlength="8" autocomplete="new-password" />
        </div>
        <div class="form-row">
          <label>Confirm new password</label>
          <input type="password" name="confirm_password" required minlength="8" autocomplete="new-password" />
        </div>
        <button class="btn" type="submit">Update password</button>
      </form>
    </div>
  `;

  const form = container.querySelector("#password-form");
  const errorEl = container.querySelector("#password-error");
  const successEl = container.querySelector("#password-success");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.innerHTML = "";
    successEl.innerHTML = "";
    const fd = new FormData(form);
    const currentPassword = fd.get("current_password");
    const newPassword = fd.get("new_password");
    const confirmPassword = fd.get("confirm_password");

    if (newPassword !== confirmPassword) {
      errorEl.innerHTML = `<div class="error-banner">New password and confirmation don't match.</div>`;
      return;
    }

    try {
      await api.changePassword(currentPassword, newPassword);
      form.reset();
      successEl.innerHTML = `<div class="badge ok">Password updated</div>`;
    } catch (err) {
      errorEl.innerHTML = `<div class="error-banner">${err.message}</div>`;
    }
  });
}
