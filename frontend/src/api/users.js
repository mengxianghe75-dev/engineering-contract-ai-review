import http from "./http";

export function fetchUsers() {
  return http.get("/users");
}

export function createUser(payload) {
  return http.post("/users", payload);
}

export function updateUser(userId, payload) {
  return http.patch(`/users/${userId}`, payload);
}
