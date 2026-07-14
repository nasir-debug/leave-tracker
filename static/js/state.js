let currentUser = null;
const listeners = [];

export function getUser() {
  return currentUser;
}

export function setUser(user) {
  currentUser = user;
  listeners.forEach((fn) => fn(currentUser));
}

export function onUserChange(fn) {
  listeners.push(fn);
}

export function isAdmin() {
  return !!currentUser && currentUser.role === "admin";
}
