import { createRouter, createWebHistory } from "vue-router";

import ContractDetailPage from "../views/ContractDetailPage.vue";
import ContractListPage from "../views/ContractListPage.vue";
import ContractUploadPage from "../views/ContractUploadPage.vue";
import LoginPage from "../views/LoginPage.vue";
import ReviewLogPage from "../views/admin/ReviewLogPage.vue";
import RuleManagementPage from "../views/admin/RuleManagementPage.vue";
import SystemSettingsPage from "../views/admin/SystemSettingsPage.vue";
import UserManagementPage from "../views/admin/UserManagementPage.vue";

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem("current_user") || "null");
  } catch {
    return null;
  }
}

const routes = [
  {
    path: "/",
    redirect: "/contracts",
  },
  {
    path: "/login",
    component: LoginPage,
    meta: { title: "登录" },
  },
  {
    path: "/contracts",
    component: ContractListPage,
    meta: { title: "合同列表", requiresAuth: true },
  },
  {
    path: "/contracts/archived",
    component: ContractListPage,
    meta: { title: "归档合同", requiresAuth: true },
  },
  {
    path: "/contracts/upload",
    component: ContractUploadPage,
    meta: { title: "上传合同", requiresAuth: true, roles: ["admin", "reviewer"] },
  },
  {
    path: "/contracts/:id",
    component: ContractDetailPage,
    meta: { title: "合同详情", requiresAuth: true },
  },
  {
    path: "/admin/settings",
    component: SystemSettingsPage,
    meta: { title: "系统设置", requiresAuth: true, roles: ["admin"] },
  },
  {
    path: "/admin/users",
    component: UserManagementPage,
    meta: { title: "用户管理", requiresAuth: true, roles: ["admin"] },
  },
  {
    path: "/admin/rules",
    component: RuleManagementPage,
    meta: { title: "规则管理", requiresAuth: true, roles: ["admin"] },
  },
  {
    path: "/admin/logs",
    component: ReviewLogPage,
    meta: { title: "操作日志", requiresAuth: true, roles: ["admin"] },
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to) => {
  const isAuthenticated = Boolean(localStorage.getItem("access_token"));
  const currentUser = getCurrentUser();
  const roleSet = new Set(currentUser?.roles || []);
  if (to.meta.requiresAuth && !isAuthenticated) {
    return "/login";
  }
  if (to.path === "/login" && isAuthenticated) {
    return "/contracts";
  }
  if (to.meta.roles?.length) {
    const hasAccess = to.meta.roles.some((role) => roleSet.has(role));
    if (!hasAccess) {
      return "/contracts";
    }
  }
  return true;
});

export default router;
