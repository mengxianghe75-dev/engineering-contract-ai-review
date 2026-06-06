<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { useAuth } from "../composables/useAuth";
import { fetchContracts as fetchContractsRequest } from "../api/contracts";
import { contractStatusLabel, riskLevelLabel } from "../utils/labels";

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const contracts = ref([]);
let pollTimer = null;

const { canModifyContracts } = useAuth();

const filters = reactive({
  contract_name: "",
  project_name: "",
  owner_id: "",
  status: "",
  category: "",
  tag: "",
  risk_level: "",
  created_from: "",
  created_to: "",
  include_archived: false,
});

const parseStatusLabelMap = {
  completed: "已完成",
  processing: "解析中",
  failed: "失败",
  missing: "缺失",
};

const reviewStatusLabelMap = {
  completed: "已审查",
  pending: "待审查",
};

const hasProcessingContracts = computed(() =>
  contracts.value.some((item) => item.parse_status === "processing")
);
const canUpload = computed(() => canModifyContracts.value);
const reviewedCount = computed(() => contracts.value.filter((item) => item.review_status === "completed").length);
const archivedCount = computed(() => contracts.value.filter((item) => item.status === "archived").length);
const isArchivedView = computed(() => route.path === "/contracts/archived");

async function fetchContracts() {
  loading.value = true;
  try {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([_, value]) => value !== "" && value !== false && value !== null)
    );
    const { data } = await fetchContractsRequest(params);
    contracts.value = data;
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "获取合同列表失败");
  } finally {
    loading.value = false;
    syncPolling();
  }
}

function goDetail(row) {
  router.push(`/contracts/${row.file_id}`);
}

function goUpload() {
  router.push("/contracts/upload");
}

function applyRoutePreset() {
  if (isArchivedView.value) {
    filters.status = "archived";
    filters.include_archived = true;
    return;
  }

  if (filters.status === "archived") {
    filters.status = "";
  }
  filters.include_archived = false;
}

function resetFilters() {
  filters.contract_name = "";
  filters.project_name = "";
  filters.owner_id = "";
  filters.status = isArchivedView.value ? "archived" : "";
  filters.category = "";
  filters.tag = "";
  filters.risk_level = "";
  filters.created_from = "";
  filters.created_to = "";
  filters.include_archived = isArchivedView.value;
  fetchContracts();
}

function parseStatusTagType(status) {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  return "warning";
}

function reviewStatusTagType(status) {
  return status === "completed" ? "success" : "warning";
}

function syncPolling() {
  if (hasProcessingContracts.value) {
    if (!pollTimer) {
      pollTimer = window.setInterval(() => {
        fetchContracts();
      }, 5000);
    }
    return;
  }

  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

onMounted(() => {
  applyRoutePreset();
  fetchContracts();
});

watch(
  () => route.path,
  () => {
    applyRoutePreset();
    fetchContracts();
  }
);

onBeforeUnmount(() => {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
});
</script>

<template>
  <div class="page-stack">
    <el-card>
      <div class="page-toolbar">
        <div>
          <h3>{{ isArchivedView ? "归档合同" : "合同列表" }}</h3>
          <p>
            {{
              isArchivedView
                ? "查看已归档合同，并支持按分类、标签、风险等级等条件继续筛选。测试路径：`/contracts/archived`"
                : "查看已上传合同、归属信息和审查状态，并支持多条件筛选。测试路径：`/contracts`"
            }}
          </p>
        </div>
        <el-tooltip v-if="!canUpload" content="当前角色没有上传权限">
          <el-button disabled>上传新合同</el-button>
        </el-tooltip>
        <el-button v-else type="primary" @click="goUpload">上传新合同</el-button>
      </div>

      <div class="summary-inline">
        <el-tag type="info">当前结果 {{ contracts.length }}</el-tag>
        <el-tag type="success">已审查 {{ reviewedCount }}</el-tag>
        <el-tag type="warning">已归档 {{ archivedCount }}</el-tag>
      </div>

      <el-form label-position="top" class="filter-form">
        <el-row :gutter="12">
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="合同名称/文件名">
              <el-input v-model="filters.contract_name" placeholder="请输入合同名称或文件名" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="项目名称">
              <el-input v-model="filters.project_name" placeholder="请输入项目名称" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="所属用户编号">
              <el-input v-model="filters.owner_id" placeholder="请输入所属用户编号" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="状态">
              <el-select v-model="filters.status" clearable class="full-width">
                <el-option label="已上传" value="uploaded" />
                <el-option label="已解析" value="parsed" />
                <el-option label="已审查" value="reviewed" />
                <el-option label="已归档" value="archived" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="分类">
              <el-input v-model="filters.category" placeholder="如：施工合同" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="标签">
              <el-input v-model="filters.tag" placeholder="请输入标签" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="风险等级">
              <el-select v-model="filters.risk_level" clearable class="full-width">
                <el-option label="高风险" value="high" />
                <el-option label="中风险" value="medium" />
                <el-option label="低风险" value="low" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="filters.created_from"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ss"
                class="full-width"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="filters.created_to"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ss"
                class="full-width"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8" :lg="6">
            <el-form-item label="归档显示">
              <el-switch
                v-model="filters.include_archived"
                active-text="包含归档"
                :disabled="isArchivedView"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <div class="filter-actions">
          <el-button type="primary" @click="fetchContracts">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </el-form>

      <el-table v-loading="loading" :data="contracts" stripe>
        <el-table-column prop="file_id" label="编号" width="80" />
        <el-table-column prop="contract_group_id" label="合同组" width="90" />
        <el-table-column label="上传版本" width="100">
          <template #default="{ row }">V{{ row.upload_version_no }}</template>
        </el-table-column>
        <el-table-column prop="original_filename" label="文件名" min-width="220" />
        <el-table-column prop="contract_name" label="合同名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="project_name" label="项目名称" min-width="180" show-overflow-tooltip />
        <el-table-column prop="owner_username" label="所属用户" min-width="120" />
        <el-table-column prop="category" label="分类" min-width="120" />
        <el-table-column label="标签" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" class="tag-gap" size="small">
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="page_count" label="页数" width="90" />
        <el-table-column label="解析" width="110">
          <template #default="{ row }">
            <el-tag :type="parseStatusTagType(row.parse_status)">
              {{ parseStatusLabelMap[row.parse_status] || row.parse_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="文档状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'archived' ? 'info' : 'success'">
              {{ contractStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="审查状态" width="120">
          <template #default="{ row }">
            <el-tag :type="reviewStatusTagType(row.review_status)">
              {{ reviewStatusLabelMap[row.review_status] || row.review_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险等级" min-width="140">
          <template #default="{ row }">
            <el-tag v-for="level in row.risk_levels" :key="level" class="tag-gap" size="small">
              {{ riskLevelLabel(level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="320" show-overflow-tooltip />
        <el-table-column prop="created_at" label="上传时间" min-width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.filter-form {
  margin-bottom: 16px;
}

.filter-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.summary-inline {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.tag-gap {
  margin-right: 6px;
  margin-bottom: 4px;
}
</style>
