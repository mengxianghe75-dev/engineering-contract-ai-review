<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { fetchReviewLogs } from "../../api/reviewLogs";
import { targetTypeLabel } from "../../utils/labels";

const loading = ref(false);
const logs = ref([]);
const modelEventActions = [
  "llm_summary_degraded",
  "llm_summary_recovered",
  "llm_risk_degraded",
  "llm_risk_recovered",
  "llm_risk_supplement",
  "llm_risk_fallback",
];
const degradedActions = ["llm_summary_degraded", "llm_risk_degraded", "llm_risk_fallback"];
const recoveredActions = ["llm_summary_recovered", "llm_risk_recovered"];
const successActions = ["llm_risk_supplement"];
const filters = reactive({
  operator_id: "",
  action_type: "",
  created_from: "",
  created_to: "",
  only_model_events: false,
  model_event_mode: "all",
});
const actionOptions = [
  "upload_contract",
  "edit_contract",
  "review_contract",
  "llm_summary_degraded",
  "llm_summary_recovered",
  "llm_risk_degraded",
  "llm_risk_recovered",
  "llm_risk_supplement",
  "llm_risk_fallback",
  "update_system_settings",
  "export_report",
  "create_rule",
  "update_rule",
  "create_user",
  "update_user",
];

const actionMetaMap = {
  upload_contract: { label: "上传合同", type: "primary" },
  edit_contract: { label: "编辑合同", type: "info" },
  review_contract: { label: "触发审查", type: "primary" },
  llm_summary_degraded: { label: "摘要降级", type: "danger" },
  llm_summary_recovered: { label: "摘要恢复", type: "success" },
  llm_risk_degraded: { label: "风险补充降级", type: "warning" },
  llm_risk_recovered: { label: "风险补充恢复", type: "success" },
  llm_risk_supplement: { label: "风险补充成功", type: "success" },
  llm_risk_fallback: { label: "风险补充回退", type: "warning" },
  update_system_settings: { label: "更新系统设置", type: "info" },
  export_report: { label: "导出报告", type: "primary" },
  create_rule: { label: "新增规则", type: "success" },
  update_rule: { label: "编辑规则", type: "info" },
  create_user: { label: "新增用户", type: "success" },
  update_user: { label: "编辑用户", type: "info" },
};

const logSummary = computed(() => {
  const summary = {};
  for (const log of filteredLogs.value) {
    summary[log.action_type] = (summary[log.action_type] || 0) + 1;
  }
  return Object.entries(summary).slice(0, 4);
});

const modelEventStats = computed(() => {
  const currentLogs = filteredLogs.value;
  return {
    modelEventCount: currentLogs.filter((log) => modelEventActions.includes(log.action_type)).length,
    degradedCount: currentLogs.filter((log) => degradedActions.includes(log.action_type)).length,
    recoveredCount: currentLogs.filter((log) => recoveredActions.includes(log.action_type)).length,
    supplementSuccessCount: currentLogs.filter((log) => log.action_type === "llm_risk_supplement").length,
  };
});

const filteredLogs = computed(() => {
  if (!filters.only_model_events) {
    return logs.value;
  }
  if (filters.model_event_mode === "degraded") {
    return logs.value.filter((log) => degradedActions.includes(log.action_type));
  }
  if (filters.model_event_mode === "recovered") {
    return logs.value.filter((log) => recoveredActions.includes(log.action_type));
  }
  if (filters.model_event_mode === "success") {
    return logs.value.filter((log) => successActions.includes(log.action_type));
  }
  return logs.value.filter((log) => modelEventActions.includes(log.action_type));
});

function actionMeta(actionType) {
  return actionMetaMap[actionType] || { label: actionType, type: "info" };
}

function applyStatsFilter(mode) {
  filters.only_model_events = true;
  filters.action_type = "";
  filters.model_event_mode = mode;
}

async function loadLogs() {
  loading.value = true;
  try {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([_, value]) => value !== "" && value !== null)
    );
    const { data } = await fetchReviewLogs(params);
    logs.value = data;
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "获取操作日志失败");
  } finally {
    loading.value = false;
  }
}

function resetFilters() {
  filters.operator_id = "";
  filters.action_type = "";
  filters.created_from = "";
  filters.created_to = "";
  filters.only_model_events = false;
  filters.model_event_mode = "all";
  loadLogs();
}

onMounted(loadLogs);
</script>

<template>
  <div class="page-stack">
    <el-card>
      <div class="page-toolbar">
        <div>
          <h3>操作日志</h3>
          <p>查看合同、规则、用户相关关键操作。测试路径：`/admin/logs`</p>
        </div>
      </div>

      <el-form label-position="top" class="filter-form">
        <el-row :gutter="12">
          <el-col :xs="24" :md="6">
            <el-form-item label="操作人 ID">
              <el-input v-model="filters.operator_id" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="6">
            <el-form-item label="动作类型">
              <el-select v-model="filters.action_type" clearable class="full-width" placeholder="选择动作">
                <el-option
                  v-for="item in actionOptions"
                  :key="item"
                  :label="actionMeta(item).label"
                  :value="item"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="6">
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="filters.created_from"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ss"
                class="full-width"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="6">
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="filters.created_to"
                type="datetime"
                value-format="YYYY-MM-DDTHH:mm:ss"
                class="full-width"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <div class="quick-filter-inline">
          <el-switch
            v-model="filters.only_model_events"
            active-text="仅看模型事件"
            inactive-text="显示全部日志"
          />
          <el-radio-group
            v-if="filters.only_model_events"
            v-model="filters.model_event_mode"
            size="small"
          >
            <el-radio-button label="all">全部模型事件</el-radio-button>
            <el-radio-button label="degraded">只看降级</el-radio-button>
            <el-radio-button label="recovered">只看恢复</el-radio-button>
            <el-radio-button label="success">只看补充成功</el-radio-button>
          </el-radio-group>
        </div>
        <div class="filter-actions">
          <el-button type="primary" @click="loadLogs">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </div>
      </el-form>

      <div class="summary-inline">
        <el-tag type="info">日志总数 {{ filteredLogs.length }}</el-tag>
        <el-tag
          v-for="[action, count] in logSummary"
          :key="action"
          :type="actionMeta(action).type"
        >
          {{ actionMeta(action).label }} {{ count }}
        </el-tag>
      </div>

      <div class="stats-grid">
        <el-card shadow="never" class="stats-card clickable" @click="applyStatsFilter('all')">
          <div class="stats-label">模型事件总数</div>
          <div class="stats-value">{{ modelEventStats.modelEventCount }}</div>
        </el-card>
        <el-card shadow="never" class="stats-card warning clickable" @click="applyStatsFilter('degraded')">
          <div class="stats-label">降级次数</div>
          <div class="stats-value">{{ modelEventStats.degradedCount }}</div>
        </el-card>
        <el-card shadow="never" class="stats-card success clickable" @click="applyStatsFilter('recovered')">
          <div class="stats-label">恢复次数</div>
          <div class="stats-value">{{ modelEventStats.recoveredCount }}</div>
        </el-card>
        <el-card shadow="never" class="stats-card primary clickable" @click="applyStatsFilter('success')">
          <div class="stats-label">风险补充成功</div>
          <div class="stats-value">{{ modelEventStats.supplementSuccessCount }}</div>
        </el-card>
      </div>

      <el-table v-loading="loading" :data="filteredLogs" stripe>
        <el-table-column prop="id" label="编号" width="80" />
        <el-table-column prop="operator_username" label="操作人" min-width="140" />
        <el-table-column label="对象类型" min-width="120">
          <template #default="{ row }">
            {{ targetTypeLabel(row.target_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="target_id" label="对象编号" width="100" />
        <el-table-column prop="action_type" label="动作" min-width="180">
          <template #default="{ row }">
            <el-tag :type="actionMeta(row.action_type).type">
              {{ actionMeta(row.action_type).label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action_detail" label="详情" min-width="280" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" min-width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
.summary-inline {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.quick-filter-inline {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.stats-card {
  border: 1px solid #e4e7ed;
}

.stats-card.clickable {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.stats-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
}

.stats-card.warning {
  border-color: #f5dab1;
  background: #fff8eb;
}

.stats-card.success {
  border-color: #c9e7d3;
  background: #f0f9f3;
}

.stats-card.primary {
  border-color: #cfe0ff;
  background: #f4f8ff;
}

.stats-label {
  color: #606266;
  font-size: 13px;
}

.stats-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
