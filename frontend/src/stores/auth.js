import { defineStore } from "pinia";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    currentUser: null,
  }),

  getters: {
    isAuthenticated: (state) => {
      return Boolean(localStorage.getItem("access_token"));
    },

    roles: (state) => {
      return state.currentUser?.roles || [];
    },

    isAdmin: (state) => {
      return state.currentUser?.roles?.includes("admin") || false;
    },
  },

  actions: {
    syncAuthState() {
      try {
        this.currentUser = JSON.parse(localStorage.getItem("current_user") || "null");
      } catch {
        this.currentUser = null;
      }
    },

    hasRole(role) {
      return this.roles.includes(role);
    },

    hasAnyRole(...roles) {
      return roles.some((role) => this.hasRole(role));
    },

    canModifyContracts() {
      return this.hasAnyRole("admin", "reviewer");
    },

    canViewContracts() {
      return this.hasAnyRole("admin", "reviewer", "viewer");
    },

    logout(router) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("current_user");
      this.currentUser = null;
      if (router) {
        router.push("/login");
      }
    },
  },
});
