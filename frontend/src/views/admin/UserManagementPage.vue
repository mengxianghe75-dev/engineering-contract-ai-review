<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { createUser, fetchUsers, updateUser } from "../../api/users";
import { roleLabel } from "../../utils/labels";

const loading = ref(false);
const dialogVisible = ref(false);
const editingUserId = ref(null);
const users = ref([]);
const filters = reactive({
  keyword: "",
  role: "",
  status: "",
});

const form = reactive({
  username: "",
  password: "",
  is_active: true,
  role_codes: ["viewer"],
});

async function loadUsers() {
  loading.value = true;
  try {
    const { data } = await fetchUsers();
    users.value = data;
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "获取用户列表失败");
  } finally {
    loading.value = false;
  }
}

const filteredUsers = computed(() =>
  users.value.filter((user) => {
    if (filters.keyword && !user.username.toLowerCase().includes(filters.keyword.toLowerCase())) {
      return false;
    }
    if (filters.role && !user.roles.includes(filters.role)) {
      return false;
    }
    if (filters.status === "active" && !user.is_active) {
      return false;
    }
    if (filters.status === "inactive" && user.is_active) {
      return false;
    }
    return true;
  })
);

const activeUserCount = computed(() => users.value.filter((user) => user.is_active).length);

function resetForm() {
  editingUserId.value = null;
  form.username = "";
  form.password = "";
  form.is_active = true;
  form.role_codes = ["viewer"];
}

function openCreateDialog() {
  resetForm();
  dialogVisible.value = true;
}

function openEditDialog(user) {
  editingUserId.value = user.id;
  form.username = user.username;
  form.password = "";
  form.is_active = user.is_active;
  form.role_codes = [...user.roles];
  dialogVisible.value = true;
}

async function submitForm() {
  try {
    if (editingUserId.value) {
      const payload = {
        username: form.username,
        is_active: form.is_active,
        role_codes: form.role_codes,
      };
      if (form.password) {
        payload.password = form.password;
      }
      await updateUser(editingUserId.value, payload);
      ElMessage.success("用户更新成功");
    } else {
      await createUser({
        username: form.username,
        password: form.password,
        is_active: form.is_active,
        role_codes: form.role_codes,
      });
      ElMessage.success("用户创建成功");
    }
    dialogVisible.value = false;
    await loadUsers();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "保存用户失败");
  }
}

async function toggleUserStatus(user) {
  try {
    await updateUser(user.id, { is_active: !user.is_active });
    ElMessage.success(user.is_active ? "用户已停用" : "用户已启用");
    await loadUsers();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "更新用户状态失败");
  }
}

onMounted(loadUsers);
</script>

<template>
  <div class="page-stack">
    <el-card>
      <div class="page-toolbar">
        <div>
          <h3>用户管理</h3>
          <p>管理员可创建用户、分配角色并启用或停用账号。测试路径：`/admin/users`</p>
        </div>
        <el-button type="primary" @click="openCreateDialog">新建用户</el-button>
      </div>

      <el-row :gutter="12" class="filter-form">
        <el-col :xs="24" :md="6">
          <el-input v-model="filters.keyword" placeholder="按用户名搜索" clearable />
        </el-col>
        <el-col :xs="24" :md="6">
          <el-select v-model="filters.role" clearable class="full-width" placeholder="角色">
            <el-option label="管理员" value="admin" />
            <el-option label="审查员" value="reviewer" />
            <el-option label="只读用户" value="viewer" />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="6">
          <el-select v-model="filters.status" clearable class="full-width" placeholder="状态">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="6" class="summary-inline">
          <el-tag type="info">总用户 {{ users.length }}</el-tag>
          <el-tag type="success">启用 {{ activeUserCount }}</el-tag>
        </el-col>
      </el-row>

      <el-table v-loading="loading" :data="filteredUsers" stripe>
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="username" label="用户名" min-width="180" />
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="role in row.roles" :key="role" class="role-tag">
              {{ roleLabel(role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link @click="toggleUserStatus(row)">
              {{ row.is_active ? "停用" : "启用" }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingUserId ? '编辑用户' : '新建用户'"
      width="480px"
      @closed="resetForm"
    >
      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item :label="editingUserId ? '新密码（可选）' : '密码'">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_codes" multiple class="full-width">
            <el-option label="管理员" value="admin" />
            <el-option label="审查员" value="reviewer" />
            <el-option label="只读用户" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.role-tag {
  margin-right: 8px;
}

.filter-form {
  margin: 16px 0;
}

.summary-inline {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
