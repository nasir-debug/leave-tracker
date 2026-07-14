import { getUser, isAdmin, onUserChange } from "../state.js";
import { setToken } from "../api.js";

function currentRoute() {
  return location.hash.replace(/^#/, "") || "/dashboard";
}

export function renderNav() {
  const el = document.getElementById("nav");
  const user = getUser();

  if (!user) {
    el.innerHTML = "";
    return;
  }

  const route = currentRoute();
  const links = [
    { href: "#/dashboard", label: "My Leave" },
    { href: "#/calendar", label: "Calendar" },
  ];
  if (isAdmin()) {
    links.push({ href: "#/admin/employees", label: "Employees" });
    links.push({ href: "#/admin/approvals", label: "Approvals" });
    links.push({ href: "#/admin/settings", label: "Settings" });
  }

  el.innerHTML = `
    <div class="navbar">
      <div class="brand">
        <img src="/img/logo.png" alt="SwiftDoctor" />
        <span class="portal-tag">Staff Portal</span>
      </div>
      <div class="links">
        ${links
          .map(
            (l) =>
              `<a href="${l.href}" class="${route === l.href.slice(1) ? "active" : ""}">${l.label}</a>`
          )
          .join("")}
        <a href="#/account" class="${route === "/account" ? "active" : ""}">Account</a>
        <span class="user">${user.name} (${user.role})</span>
        <button id="logout-btn">Log out</button>
      </div>
    </div>
  `;

  document.getElementById("logout-btn").addEventListener("click", () => {
    setToken(null);
    location.hash = "#/login";
    location.reload();
  });
}

onUserChange(renderNav);
