import { api, setToken } from "../api.js";
import { setUser } from "../state.js";

export function renderLogin(container) {
  container.innerHTML = `
    <div class="login-wrap card">
      <h1>Leave Tracker</h1>
      <p class="subtitle">Sign in to manage or view holiday &amp; sickness records.</p>
      <div id="login-error"></div>
      <form id="login-form">
        <div class="form-row">
          <label>Email</label>
          <input type="email" name="email" required autofocus />
        </div>
        <div class="form-row">
          <label>Password</label>
          <input type="password" name="password" required />
        </div>
        <button class="btn" type="submit" style="width:100%">Sign in</button>
      </form>
    </div>
  `;

  const form = container.querySelector("#login-form");
  const errorEl = container.querySelector("#login-error");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.innerHTML = "";
    const fd = new FormData(form);
    try {
      const res = await api.login(fd.get("email"), fd.get("password"));
      setToken(res.token);
      setUser(res.user);
      location.hash = "#/dashboard";
    } catch (err) {
      errorEl.innerHTML = `<div class="error-banner">${err.message}</div>`;
    }
  });
}
