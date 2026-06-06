import { computed, ref } from "vue";

const currentUser = ref(null);

function syncAuthState() {
  try {
    currentUser.value = JSON.parse(localStorage.getItem("current_user") || "null");
  } catch {
    currentUser.value = null;
  }
}

function isAuthenticated() {
  return Boolean(localStorage.getItem("access_token"));
}

function getRoles() {
  return currentUser.value?.roles || [];
}

function isAdmin() {
  return getRoles().includes("admin");
}

function hasRole(role) {
  return getRoles().includes(role);
}

function hasAnyRole(...roles) {
  return roles.some((role) => hasRole(role));
}

function canModifyContracts() {
  return hasAnyRole("admin", "reviewer");
}

function canViewContracts() {
  return hasAnyRole("admin", "reviewer", "viewer");
}

export function useAuth() {
  syncAuthState();

  return {
    currentUser: computed(() => currentUser.value),
    isAuthenticated: computed(() => isAuthenticated()),
    roles: computed(() => getRoles()),
    isAdmin: computed(() => isAdmin()),
    hasRole: (role) => hasRole(role),
    hasAnyRole: (...roles) => hasAnyRole(...roles),
    canModifyContracts: computed(() => canModifyContracts()),
    canViewContracts: computed(() => canViewContracts()),
    syncAuthState,
  };
}
