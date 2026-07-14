import { api, getToken, setToken } from "./api.js";
import { getUser, setUser, isAdmin } from "./state.js";
import { renderNav } from "./components/nav.js";
import { renderLogin } from "./pages/login.js";
import { renderDashboard } from "./pages/dashboard.js";
import { renderCalendarPage } from "./pages/calendar.js";
import { renderAdminEmployees } from "./pages/admin_employees.js";
import { renderAdminApprovals } from "./pages/admin_approvals.js";
import { renderAdminSettings } from "./pages/admin_settings.js";
import { renderAccount } from "./pages/account.js";

const appEl = document.getElementById("app");

const ADMIN_ROUTES = new Set(["/admin/employees", "/admin/approvals", "/admin/settings"]);

async function route() {
  const path = location.hash.replace(/^#/, "") || "/dashboard";
  const user = getUser();

  if (path === "/login") {
    if (user) {
      location.hash = "#/dashboard";
      return;
    }
    renderNav();
    renderLogin(appEl);
    return;
  }

  if (!user) {
    location.hash = "#/login";
    return;
  }

  if (ADMIN_ROUTES.has(path) && !isAdmin()) {
    location.hash = "#/dashboard";
    return;
  }

  renderNav();

  try {
    if (path === "/dashboard") await renderDashboard(appEl);
    else if (path === "/calendar") await renderCalendarPage(appEl);
    else if (path === "/admin/employees") await renderAdminEmployees(appEl);
    else if (path === "/admin/approvals") await renderAdminApprovals(appEl);
    else if (path === "/admin/settings") await renderAdminSettings(appEl);
    else if (path === "/account") await renderAccount(appEl);
    else {
      location.hash = "#/dashboard";
    }
  } catch (err) {
    appEl.innerHTML = `<div class="error-banner">${err.message}</div>`;
  }
}

async function boot() {
  const token = getToken();
  if (token) {
    try {
      const { user } = await api.me();
      setUser(user);
    } catch (e) {
      setToken(null);
    }
  }
  window.addEventListener("hashchange", route);
  route();
}

boot();
