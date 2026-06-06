<script setup>
import { computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Document, Files, FolderOpened, Lock, Setting, Upload } from "@element-plus/icons-vue";

import { useAuth } from "./composables/useAuth";
import { roleLabel } from "./utils/labels";

const route = useRoute();
const router = useRouter();

const { currentUser, isAuthenticated, isAdmin, hasAnyRole, syncAuthState } = useAuth();

const allMenuItems = [
  { index: "/contracts", label: "合同列表", icon: Files },
  { index: "/contracts/archived", label: "归档合同", icon: FolderOpened },
  { index: "/contracts/upload", label: "上传合同", icon: Upload, roles: ["admin", "reviewer"] },
  { index: "/admin/settings", label: "系统设置", icon: Setting, roles: ["admin"] },
  { index: "/admin/users", label: "用户管理", icon: Setting, roles: ["admin"] },
  { index: "/admin/rules", label: "规则管理", icon: Setting, roles: ["admin"] },
  { index: "/admin/logs", label: "操作日志", icon: Setting, roles: ["admin"] },
];

const menuItems = computed(() =>
  allMenuItems.filter((item) => !item.roles || item.roles.some((role) => hasAnyRole(role)))
);

function handleSelect(index) {
  router.push(index);
}

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("current_user");
  router.push("/login");
  syncAuthState();
}

watch(
  () => route.fullPath,
  () => {
    syncAuthState();
  },
  { immediate: true }
);

onMounted(() => {
  syncAuthState();
});
</script>

<template>
  <router-view v-if="route.path === '/login'" />

  <el-container v-else class="app-shell">
    <el-aside width="220px" class="app-sidebar">
      <div class="brand">
        <el-icon><Document /></el-icon>
        <div>
          <span>AI合同审查系统</span>
          <small>by 孟祥和</small>
        </div>
      </div>

      <el-menu :default-active="route.path" class="nav-menu" @select="handleSelect">
        <el-menu-item
          v-for="item in menuItems"
          :key="item.index"
          :index="item.index"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-license">
        <span>非商业源码可见版本</span>
        <span>商业授权：微信 mengxianghe75</span>
      </div>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-title">
          <h1>{{ route.meta.title || "工程合同 AI 审查助手" }}</h1>
          <p>第 6 阶段后台管理联调版本</p>
        </div>

        <div class="header-actions">
          <el-tag v-if="isAuthenticated" type="success">已登录</el-tag>
          <el-tag v-if="isAuthenticated && isAdmin" type="warning">{{ roleLabel("admin") }}</el-tag>
          <el-button v-if="isAuthenticated" :icon="Lock" plain @click="logout">
            退出登录
          </el-button>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
