import http from "./http";

export function fetchSystemSettings() {
  return http.get("/system-settings");
}

export function updateSystemSettings(payload) {
  return http.patch("/system-settings", payload);
}

export function testSystemSettings(payload) {
  return http.post("/system-settings/test", payload);
}
