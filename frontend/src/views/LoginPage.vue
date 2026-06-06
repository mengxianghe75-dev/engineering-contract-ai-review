<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import http from "../api/http";

const router = useRouter();
const loading = ref(false);
const form = reactive({
  username: "admin",
  password: "Admin123456",
});

async function handleLogin() {
  loading.value = true;
  try {
    const { data } = await http.post("/auth/login", form);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("current_user", JSON.stringify(data.user));
    ElMessage.success("登录成功");
    router.push("/contracts");
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card">
      <template #header>
        <div>
          <h2>登录系统</h2>
          <p>使用默认管理员账号进入合同审查后台。</p>
        </div>
      </template>

      <el-form label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>

        <el-button type="primary" :loading="loading" class="full-width" @click="handleLogin">
          登录
        </el-button>
      </el-form>

      <div class="login-meta">
        <span>Source-available demo by 孟祥和</span>
        <span>商业授权：微信 mengxianghe75</span>
      </div>
    </el-card>
  </div>
</template>
