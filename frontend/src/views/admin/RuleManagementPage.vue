<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { createReviewRule, fetchReviewRules, updateReviewRule } from "../../api/reviewRules";
import { conditionTypeLabel, riskLevelLabel } from "../../utils/labels";

const loading = ref(false);
const dialogVisible = ref(false);
const editingRuleId = ref(null);
const rules = ref([]);
const filters = reactive({
  keyword: "",
  condition_type: "",
  status: "",
});

const form = reactive({
  name: "",
  rule_code: "",
  risk_type: "",
  condition_type: "keyword",
  condition_value: "",
  risk_level: "medium",
  suggestion: "",
  priority: 100,
  is_active: true,
  contract_type_scope: "",
});

async function loadRules() {
  loading.value = true;
  try {
    const { data } = await fetchReviewRules();
    rules.value = data;
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "获取规则列表失败");
  } finally {
    loading.value = false;
  }
}

const filteredRules = computed(() =>
  rules.value.filter((rule) => {
    if (
      filters.keyword &&
      !`${rule.name} ${rule.rule_code} ${rule.risk_type}`.toLowerCase().includes(filters.keyword.toLowerCase())
    ) {
      return false;
    }
    if (filters.condition_type && rule.condition_type !== filters.condition_type) {
      return false;
    }
    if (filters.status === "active" && !rule.is_active) {
      return false;
    }
    if (filters.status === "inactive" && rule.is_active) {
      return false;
    }
    if (filters.status === "deleted" && !rule.is_deleted) {
      return false;
    }
    return true;
  })
);

function resetForm() {
  editingRuleId.value = null;
  form.name = "";
  form.rule_code = "";
  form.risk_type = "";
  form.condition_type = "keyword";
  form.condition_value = "";
  form.risk_level = "medium";
  form.suggestion = "";
  form.priority = 100;
  form.is_active = true;
  form.contract_type_scope = "";
}

function openCreateDialog() {
  resetForm();
  dialogVisible.value = true;
}

function openEditDialog(rule) {
  editingRuleId.value = rule.id;
  form.name = rule.name;
  form.rule_code = rule.rule_code;
  form.risk_type = rule.risk_type;
  form.condition_type = rule.condition_type;
  form.condition_value = rule.condition_value;
  form.risk_level = rule.risk_level;
  form.suggestion = rule.suggestion;
  form.priority = rule.priority;
  form.is_active = rule.is_active;
  form.contract_type_scope = rule.contract_type_scope || "";
  dialogVisible.value = true;
}

async function submitForm() {
  const payload = {
    name: form.name,
    rule_code: form.rule_code,
    risk_type: form.risk_type,
    condition_type: form.condition_type,
    condition_value: form.condition_value,
    risk_level: form.risk_level,
    suggestion: form.suggestion,
    priority: form.priority,
    is_active: form.is_active,
    contract_type_scope: form.contract_type_scope || null,
  };
  try {
    if (editingRuleId.value) {
      const updatePayload = { ...payload };
      delete updatePayload.rule_code;
      await updateReviewRule(editingRuleId.value, updatePayload);
      ElMessage.success("规则更新成功");
    } else {
      await createReviewRule(payload);
      ElMessage.success("规则创建成功");
    }
    dialogVisible.value = false;
    await loadRules();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "保存规则失败");
  }
}

async function toggleRule(rule) {
  try {
    await updateReviewRule(rule.id, { is_active: !rule.is_active });
    ElMessage.success(rule.is_active ? "规则已停用" : "规则已启用");
    await loadRules();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "更新规则状态失败");
  }
}

async function softDeleteRule(rule) {
  try {
    await updateReviewRule(rule.id, { is_deleted: true, is_active: false });
    ElMessage.success("规则已删除");
    await loadRules();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "删除规则失败");
  }
}

onMounted(loadRules);
</script>

<template>
  <div class="page-stack">
    <el-card>
      <div class="page-toolbar">
        <div>
          <h3>规则管理</h3>
          <p>管理员可配置规则引擎，审查时按优先级先执行规则，再由 AI 补充。测试路径：`/admin/rules`</p>
        </div>
        <div class="header-action-group">
          <el-button type="primary" @click="openCreateDialog">新建规则</el-button>
        </div>
      </div>

      <el-row :gutter="12" class="filter-form">
        <el-col :xs="24" :md="8">
          <el-input v-model="filters.keyword" clearable placeholder="按规则名称、编码、说明搜索" />
        </el-col>
        <el-col :xs="24" :md="8">
          <el-select v-model="filters.condition_type" clearable class="full-width" placeholder="条件类型">
            <el-option label="关键词" value="keyword" />
            <el-option label="正则表达式" value="regex" />
            <el-option label="命中任一" value="contains_any" />
            <el-option label="命中全部" value="contains_all" />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-select v-model="filters.status" clearable class="full-width" placeholder="状态">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
            <el-option label="已删除" value="deleted" />
          </el-select>
        </el-col>
      </el-row>

      <el-alert
        type="info"
        :closable="false"
        title="演示建议：contains_any / contains_all 支持 JSON 数组或逗号分隔；priority 越小越先执行。"
        class="page-note"
      />

      <el-table v-loading="loading" :data="filteredRules" stripe>
        <el-table-column prop="id" label="编号" width="70" />
        <el-table-column prop="name" label="规则名称" min-width="180" />
        <el-table-column prop="rule_code" label="规则编码" min-width="160" />
        <el-table-column label="条件类型" width="120">
          <template #default="{ row }">
            {{ conditionTypeLabel(row.condition_type) }}
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="100">
          <template #default="{ row }">
            {{ riskLevelLabel(row.risk_level) }}
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100" />
        <el-table-column prop="condition_value" label="条件值" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.is_deleted ? 'info' : row.is_active ? 'success' : 'warning'">
              {{ row.is_deleted ? "已删除" : row.is_active ? "启用" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="contract_type_scope" label="合同类型范围" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button v-if="!row.is_deleted" link @click="toggleRule(row)">
              {{ row.is_active ? "停用" : "启用" }}
            </el-button>
            <el-button v-if="!row.is_deleted" link type="danger" @click="softDeleteRule(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingRuleId ? '编辑规则' : '新建规则'"
      width="640px"
      @closed="resetForm"
    >
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="规则名称">
              <el-input v-model="form.name" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规则编码">
              <el-input v-model="form.rule_code" :disabled="Boolean(editingRuleId)" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="风险类型说明">
              <el-input v-model="form.risk_type" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="条件类型">
              <el-select v-model="form.condition_type" class="full-width">
                <el-option label="关键词" value="keyword" />
                <el-option label="正则表达式" value="regex" />
                <el-option label="命中任一" value="contains_any" />
                <el-option label="命中全部" value="contains_all" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="条件值">
              <el-input
                v-model="form.condition_value"
                type="textarea"
                :rows="3"
                placeholder='keyword/regex 填单值；contains_any/contains_all 可填 JSON 数组或逗号分隔文本'
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="风险等级">
              <el-select v-model="form.risk_level" class="full-width">
                <el-option label="高风险" value="high" />
                <el-option label="中风险" value="medium" />
                <el-option label="低风险" value="low" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-input-number v-model="form.priority" :min="0" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="建议">
              <el-input v-model="form.suggestion" type="textarea" :rows="3" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="合同类型范围">
              <el-input v-model="form.contract_type_scope" placeholder='留空表示全部；可填 JSON 数组或逗号分隔' />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="启用状态">
              <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.filter-form {
  margin: 16px 0;
}

.page-note {
  margin-bottom: 16px;
}

.header-action-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
