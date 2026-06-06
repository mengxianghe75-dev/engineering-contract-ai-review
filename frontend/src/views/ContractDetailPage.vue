<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { useAuth } from "../composables/useAuth";
import http from "../api/http";
import {
  compareReviewVersions,
  fetchReviewVersionDetail,
  fetchReviewVersions,
} from "../api/reviewVersions";
import { updateContractMetadata } from "../api/contracts";
import {
  conditionTypeLabel,
  contractStatusLabel,
  providerLabel,
  riskLevelLabel,
  triggerSourceLabel,
} from "../utils/labels";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const reviewing = ref(false);
const savingMeta = ref(false);
const contract = ref(null);
const reviewVersions = ref([]);
const versionDetailVisible = ref(false);
const selectedVersion = ref(null);
const compareLoading = ref(false);
const compareResult = ref(null);
const metadataForm = reactive({
  original_filename: "",
  owner_id: null,
  category: "",
  tags_text: "",
});
const compareForm = reactive({
  base_version_id: null,
  target_version_id: null,
});
let pollTimer = null;

const { canModifyContracts } = useAuth();

const riskCount = computed(() => contract.value?.review_result?.risks?.length || 0);
const reviewRuntimeStatus = computed(() => buildReviewRuntimeStatus(contract.value?.review_result));
const selectedVersionRuntimeStatus = computed(() => resolveRuntimeStatus(selectedVersion.value));
const canReview = computed(() => canModifyContracts.value && contract.value?.status !== "archived");

const parseModeLabelMap = {
  text: "文本解析",
  ocr: "OCR 识别",
  hybrid: "混合解析",
  unknown: "未知",
};

const parseStatusLabelMap = {
  completed: "解析完成",
  processing: "解析中",
  failed: "解析失败",
  missing: "缺失",
};

async function fetchDetail() {
  loading.value = true;
  try {
    const { data } = await http.get(`/contracts/${route.params.id}`);
    contract.value = data;
    metadataForm.original_filename = data.original_filename || "";
    metadataForm.owner_id = data.owner_id;
    metadataForm.category = data.category || "";
    metadataForm.tags_text = (data.tags || []).join(", ");
    await loadVersions();
    syncPolling();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "获取合同详情失败");
  } finally {
    loading.value = false;
  }
}

async function loadVersions() {
  try {
    const { data } = await fetchReviewVersions(route.params.id);
    reviewVersions.value = data;
    syncCompareDefaults();
    await runVersionCompare(true);
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "获取上传版本失败");
  }
}

function syncCompareDefaults() {
  const versionIds = new Set(reviewVersions.value.map((item) => item.id));
  if (!versionIds.has(compareForm.target_version_id)) {
    compareForm.target_version_id = reviewVersions.value[0]?.id || null;
  }
  if (!versionIds.has(compareForm.base_version_id)) {
    compareForm.base_version_id = reviewVersions.value[1]?.id || reviewVersions.value[0]?.id || null;
  }
  if (compareForm.base_version_id === compareForm.target_version_id && reviewVersions.value.length > 1) {
    compareForm.base_version_id = reviewVersions.value[1].id;
  }
}

async function runVersionCompare(silent = false) {
  if (!compareForm.base_version_id || !compareForm.target_version_id) {
    compareResult.value = null;
    return;
  }
  if (compareForm.base_version_id === compareForm.target_version_id) {
    compareResult.value = null;
    if (!silent) {
      ElMessage.warning("请选择两个不同的版本进行对比");
    }
    return;
  }

  compareLoading.value = true;
  try {
    const { data } = await compareReviewVersions(
      route.params.id,
      compareForm.base_version_id,
      compareForm.target_version_id
    );
    compareResult.value = data;
  } catch (error) {
    compareResult.value = null;
    if (!silent) {
      ElMessage.error(error.response?.data?.detail || "获取版本对比失败");
    }
  } finally {
    compareLoading.value = false;
  }
}

async function runReview() {
  reviewing.value = true;
  try {
    await http.post(`/contracts/${route.params.id}/review`);
    ElMessage.success("审查完成");
    await fetchDetail();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "执行审查失败");
  } finally {
    reviewing.value = false;
  }
}

async function downloadReport() {
  try {
    const response = await http.get(`/contracts/${route.params.id}/report`, {
      responseType: "blob",
    });
    const blob = new Blob([response.data], { type: "application/pdf" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    const disposition = response.headers["content-disposition"] || "";
    const match = disposition.match(/filename\*=UTF-8''(.+)$/);
    link.href = url;
    link.download = decodeURIComponent(match?.[1] || `contract-${route.params.id}-report.pdf`);
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "导出报告失败");
  }
}

async function downloadVersionReport(versionId) {
  try {
    const response = await http.get(`/contracts/${versionId}/report`, {
      responseType: "blob",
    });
    const blob = new Blob([response.data], { type: "application/pdf" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `contract-version-${versionId}-report.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "导出版本报告失败");
  }
}

function goUploadNewVersion() {
  router.push(`/contracts/upload?version_of_contract_id=${route.params.id}`);
}

function goVersionDetail(versionFileId) {
  router.push(`/contracts/${versionFileId}`);
}

async function openVersionDetail(versionId) {
  try {
    const { data } = await fetchReviewVersionDetail(route.params.id, versionId);
    selectedVersion.value = data;
    versionDetailVisible.value = true;
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "获取版本详情失败");
  }
}

async function saveMetadata() {
  savingMeta.value = true;
  try {
    await updateContractMetadata(route.params.id, {
      original_filename: metadataForm.original_filename,
      owner_id: metadataForm.owner_id,
      category: metadataForm.category,
      tags: metadataForm.tags_text
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    });
    ElMessage.success("文档基础信息已更新");
    await fetchDetail();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "更新文档信息失败");
  } finally {
    savingMeta.value = false;
  }
}

async function archiveContract(archived) {
  try {
    await updateContractMetadata(route.params.id, { archived });
    ElMessage.success(archived ? "文档已归档" : "文档已取消归档");
    await fetchDetail();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "更新归档状态失败");
  }
}

function riskTagType(level) {
  if (level === "high") return "danger";
  if (level === "medium") return "warning";
  return "info";
}

function riskSourceLabel(source) {
  if (source === "rule") return "规则";
  if (source === "llm") return "LLM";
  if (source === "ai") return "内置补充";
  return source || "未知";
}

function riskSourceTagType(source) {
  if (source === "rule") return "success";
  if (source === "llm") return "warning";
  if (source === "ai") return "info";
  return "";
}

function parseModeTagType(mode) {
  if (mode === "ocr") return "warning";
  if (mode === "hybrid") return "success";
  return "info";
}

function parseStatusTagType(status) {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  return "warning";
}

function buildReviewRuntimeStatus(reviewResult) {
  if (!reviewResult) {
    return {
      finalProvider: "-",
      summaryStatus: "未执行",
      summaryType: "info",
      riskStatus: "未执行",
      riskType: "info",
      message: "尚未执行审查。",
    };
  }

  const provider = reviewResult.provider || "unknown";
  if (provider === "not_reviewed") {
    return {
      finalProvider: "未审查",
      summaryStatus: "未执行",
      summaryType: "info",
      riskStatus: "未执行",
      riskType: "info",
      message: "该上传版本尚未执行审查。",
    };
  }
  const llmRiskCount = (reviewResult.risks || []).filter((item) => item.source === "llm").length;

  if (provider === "openai_compatible") {
    return {
      finalProvider: providerLabel(provider),
      summaryStatus: "真实模型调用成功",
      summaryType: "success",
      riskStatus: llmRiskCount > 0 ? `真实模型补充 ${llmRiskCount} 项` : "真实模型已参与，无新增风险",
      riskType: llmRiskCount > 0 ? "success" : "warning",
      message: "本次审查中，真实模型成功参与了摘要生成，并参与了风险补充判断。",
    };
  }

  if (provider === "mixed_rule_llm") {
    return {
      finalProvider: providerLabel(provider),
      summaryStatus: "摘要已降级为模拟模式",
      summaryType: "warning",
      riskStatus: llmRiskCount > 0 ? `真实模型补充 ${llmRiskCount} 项` : "风险补充链路已参与",
      riskType: "success",
      message: "本次审查中，真实模型成功参与了风险补充，但摘要生成已降级为模拟模式。",
    };
  }

  if (provider === "mock_fallback") {
    return {
      finalProvider: providerLabel(provider),
      summaryStatus: "真实模型失败，已降级",
      summaryType: "danger",
      riskStatus: llmRiskCount > 0 ? `存在 ${llmRiskCount} 项历史大模型风险` : "本次未成功补充大模型风险",
      riskType: llmRiskCount > 0 ? "warning" : "danger",
      message: "本次审查中，真实模型未稳定参与，系统已自动降级为模拟模式/规则链路。",
    };
  }

  return {
    finalProvider: providerLabel(provider),
    summaryStatus: "当前为模拟模式",
    summaryType: "info",
    riskStatus: llmRiskCount > 0 ? `存在 ${llmRiskCount} 项大模型风险` : "未启用真实模型风险补充",
    riskType: llmRiskCount > 0 ? "warning" : "info",
    message: "当前这次审查主要依赖规则与内置补充逻辑，未启用真实模型主链路。",
  };
}

function buildStoredRuntimeStatus(reviewResult) {
  if (!reviewResult) {
    return null;
  }
  const hasStoredSummary = reviewResult.summary_success !== undefined && reviewResult.summary_success !== null;
  const hasStoredRisk = reviewResult.risk_success !== undefined && reviewResult.risk_success !== null;
  const hasStoredRiskProvider = reviewResult.risk_provider !== undefined && reviewResult.risk_provider !== null;
  if (!hasStoredSummary && !hasStoredRisk && !hasStoredRiskProvider) {
    return null;
  }

  const summaryStatus =
    reviewResult.summary_success === true
      ? `成功（${providerLabel(reviewResult.summary_provider || reviewResult.provider || "-")}）`
      : reviewResult.summary_success === false
        ? `失败/降级（${providerLabel(reviewResult.summary_provider || reviewResult.provider || "-")}）`
        : "未记录";
  const riskProvider = reviewResult.risk_provider ? providerLabel(reviewResult.risk_provider) : "未启用";
  const riskStatus =
    reviewResult.risk_success === true
      ? `成功（${riskProvider}）`
      : reviewResult.risk_success === false
        ? `失败/降级（${riskProvider}）`
        : "未启用或未记录";
  const summaryType =
    reviewResult.summary_success === true ? "success" : reviewResult.summary_success === false ? "danger" : "info";
  const riskType =
    reviewResult.risk_success === true ? "success" : reviewResult.risk_success === false ? "danger" : "info";
  const detailParts = [];
  if (reviewResult.summary_message) {
    detailParts.push(`摘要：${reviewResult.summary_message}`);
  }
  if (reviewResult.risk_message) {
    detailParts.push(`风险补充：${reviewResult.risk_message}`);
  }

  return {
    finalProvider: providerLabel(reviewResult.provider || "-"),
    summaryStatus,
    summaryType,
    riskStatus,
    riskType,
    message: detailParts.join("；") || "该版本已保存模型参与审计信息。",
  };
}

function resolveRuntimeStatus(reviewResult) {
  return buildStoredRuntimeStatus(reviewResult) || buildReviewRuntimeStatus(reviewResult);
}

function syncPolling() {
  if (contract.value?.parse_status === "processing") {
    if (!pollTimer) {
      pollTimer = window.setInterval(() => {
        fetchDetail();
      }, 4000);
    }
    return;
  }

  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

onMounted(() => {
  fetchDetail();
});

onBeforeUnmount(() => {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
});
</script>

<template>
  <div v-loading="loading" class="page-stack">
    <el-card v-if="contract">
      <div class="page-toolbar">
        <div>
          <h3>{{ contract.original_filename }}</h3>
          <p>
            文件编号：{{ contract.file_id }}，合同组：{{ contract.contract_group_id }}，上传版本：V{{ contract.upload_version_no }}，页数：{{ contract.page_count }}
          </p>
          <div class="meta-tags">
            <el-tag :type="parseStatusTagType(contract.parse_status)">
              {{ parseStatusLabelMap[contract.parse_status] || contract.parse_status }}
            </el-tag>
            <el-tag :type="parseModeTagType(contract.parse_mode)">
              {{ parseModeLabelMap[contract.parse_mode] || contract.parse_mode }}
            </el-tag>
          </div>
          <p v-if="contract.parse_notice" class="parse-notice">{{ contract.parse_notice }}</p>
          <p v-if="contract.parse_error" class="parse-error">{{ contract.parse_error }}</p>
          <p class="parse-notice">
            所属用户：{{ contract.owner_username || "-" }}，分类：{{ contract.category || "-" }}，状态：{{ contractStatusLabel(contract.status) }}，当前文件最新审查：{{ contract.latest_version_no || "-" }}，合同组上传版本数：{{ contract.version_count }}
          </p>
        </div>
        <div class="header-action-group">
          <el-button
            v-if="canModifyContracts"
            plain
            @click="goUploadNewVersion"
          >
            上传新版本
          </el-button>
          <el-button
            type="primary"
            :loading="reviewing"
            :disabled="contract.parse_status !== 'completed' || !canReview"
            @click="runReview"
          >
            {{ contract.review_status === "completed" ? "重新审查" : "开始审查" }}
          </el-button>
          <el-button
            v-if="canModifyContracts"
            plain
            @click="archiveContract(contract.status !== 'archived')"
          >
            {{ contract.status === "archived" ? "取消归档" : "归档文档" }}
          </el-button>
          <el-button plain @click="downloadReport">导出审查报告</el-button>
        </div>
      </div>
    </el-card>

    <el-card v-if="contract" class="detail-card">
      <template #header>
        <div class="card-header">
          <span>模型参与状态</span>
          <el-tag type="info">单次审查视角</el-tag>
        </div>
      </template>
      <div class="runtime-status-grid">
        <el-card shadow="never" class="runtime-status-card">
          <div class="runtime-status-line">
            <span class="runtime-status-label">最终审查模式</span>
            <el-tag type="info">{{ reviewRuntimeStatus.finalProvider }}</el-tag>
          </div>
        </el-card>
        <el-card shadow="never" class="runtime-status-card">
          <div class="runtime-status-line">
            <span class="runtime-status-label">摘要状态</span>
            <el-tag :type="reviewRuntimeStatus.summaryType">{{ reviewRuntimeStatus.summaryStatus }}</el-tag>
          </div>
        </el-card>
        <el-card shadow="never" class="runtime-status-card">
          <div class="runtime-status-line">
            <span class="runtime-status-label">风险补充状态</span>
            <el-tag :type="reviewRuntimeStatus.riskType">{{ reviewRuntimeStatus.riskStatus }}</el-tag>
          </div>
        </el-card>
      </div>
      <el-alert
        :closable="false"
        :type="reviewRuntimeStatus.summaryType"
        :title="reviewRuntimeStatus.message"
      />
    </el-card>

    <el-card v-if="contract" class="detail-card">
      <template #header>
        <div class="card-header">
          <span>上传版本</span>
          <el-tag type="info">{{ reviewVersions.length }} 个版本</el-tag>
        </div>
      </template>
      <el-table :data="reviewVersions" size="small">
        <el-table-column prop="version_no" label="上传版本" width="90" />
        <el-table-column prop="original_filename" label="文件名" min-width="180" />
        <el-table-column prop="triggered_by_username" label="触发人" width="120" />
        <el-table-column label="触发来源" width="140">
          <template #default="{ row }">
            {{ triggerSourceLabel(row.trigger_source) }}
          </template>
        </el-table-column>
        <el-table-column label="审查状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.provider === 'not_reviewed' ? 'info' : 'success'">
              {{ row.provider === "not_reviewed" ? "未审查" : "已审查" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="latest_review_version_no" label="文件内审查版次" width="130" />
        <el-table-column label="总体风险" width="120">
          <template #default="{ row }">
            {{ riskLevelLabel(row.overall_risk_level) }}
          </template>
        </el-table-column>
        <el-table-column prop="risk_count" label="风险数" width="90" />
        <el-table-column prop="summary" label="摘要" min-width="240" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" min-width="180" />
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button link @click="openVersionDetail(row.id)">查看版本</el-button>
            <el-button link @click="goVersionDetail(row.file_id)">打开文件</el-button>
            <el-button
              link
              type="primary"
              :disabled="row.provider === 'not_reviewed'"
              @click="downloadVersionReport(row.file_id)"
            >
              导出该版本
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="contract" class="detail-card">
      <template #header>
        <div class="card-header">
          <span>版本对比</span>
          <el-tag type="info">对比同一合同组下两次上传文件的差异</el-tag>
        </div>
      </template>

      <el-row :gutter="12" class="filter-form">
        <el-col :xs="24" :md="8">
          <el-select v-model="compareForm.base_version_id" class="full-width" placeholder="选择基准版本">
            <el-option
              v-for="item in reviewVersions"
              :key="`base-${item.id}`"
              :label="`V${item.version_no} · ${item.created_at}`"
              :value="item.id"
            />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-select v-model="compareForm.target_version_id" class="full-width" placeholder="选择目标版本">
            <el-option
              v-for="item in reviewVersions"
              :key="`target-${item.id}`"
              :label="`V${item.version_no} · ${item.created_at}`"
              :value="item.id"
            />
          </el-select>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-button
            type="primary"
            :loading="compareLoading"
            :disabled="reviewVersions.length < 2"
            @click="runVersionCompare()"
          >
            对比版本
          </el-button>
        </el-col>
      </el-row>

      <el-empty v-if="reviewVersions.length < 2" description="至少需要两个上传版本才能进行对比" />

      <template v-else-if="compareResult">
        <div class="compare-summary">
          <el-tag type="info">
            对比 V{{ compareResult.base_version_no }} -> V{{ compareResult.target_version_no }}
          </el-tag>
          <el-tag :type="compareResult.summary_changed ? 'warning' : 'success'">
            {{ compareResult.summary_changed ? "摘要已变化" : "摘要未变化" }}
          </el-tag>
          <el-tag :type="compareResult.runtime_changed ? 'warning' : 'success'">
            {{ compareResult.runtime_changed ? "模型状态已变化" : "模型状态未变化" }}
          </el-tag>
          <el-tag type="success">新增风险 {{ compareResult.added_risks.length }}</el-tag>
          <el-tag type="danger">移除风险 {{ compareResult.removed_risks.length }}</el-tag>
          <el-tag type="warning">等级变化 {{ compareResult.level_changed_risks.length }}</el-tag>
          <el-tag type="info">字段变化 {{ compareResult.field_changes.length }}</el-tag>
        </div>

        <el-alert
          v-if="compareResult.degradation_events.length"
          type="warning"
          :closable="false"
          class="page-note"
          title="检测到模型链路降级事件"
          :description="compareResult.degradation_events.join('；')"
        />
        <el-alert
          v-if="compareResult.recovery_events.length"
          type="success"
          :closable="false"
          class="page-note"
          title="检测到模型链路恢复事件"
          :description="compareResult.recovery_events.join('；')"
        />

        <el-row :gutter="16">
          <el-col :xs="24" :lg="12">
            <el-card shadow="never" class="compare-card">
              <template #header>
                <span>字段变化</span>
              </template>
              <el-empty v-if="!compareResult.field_changes.length" description="字段未发生变化" />
              <div v-else class="compare-list">
                <div
                  v-for="change in compareResult.field_changes"
                  :key="change.field"
                  class="compare-item"
                >
                  <strong>{{ change.label }}</strong>
                  <p>旧值：{{ change.before_value }}</p>
                  <p>新值：{{ change.after_value }}</p>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :xs="24" :lg="12">
            <el-card shadow="never" class="compare-card">
              <template #header>
                <span>模型参与变化</span>
              </template>
              <el-empty v-if="!compareResult.runtime_changes.length" description="模型参与状态未发生变化" />
              <div v-else class="compare-list">
                <div
                  v-for="change in compareResult.runtime_changes"
                  :key="change.label"
                  class="compare-item"
                >
                  <strong>{{ change.label }}</strong>
                  <p>旧值：{{ change.before_value }}</p>
                  <p>新值：{{ change.after_value }}</p>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :xs="24" :lg="24">
            <el-card shadow="never" class="compare-card">
              <template #header>
                <span>风险变化</span>
              </template>
              <el-empty
                v-if="!compareResult.added_risks.length && !compareResult.removed_risks.length && !compareResult.level_changed_risks.length"
                description="风险结构未发生变化"
              />
              <div v-else class="compare-list">
                <div v-for="risk in compareResult.added_risks" :key="`add-${risk.code}-${risk.title}`" class="compare-item">
                  <div class="risk-header">
                    <strong>新增风险：{{ risk.title }}</strong>
                    <el-tag :type="riskTagType(risk.level)">{{ riskLevelLabel(risk.level) }}</el-tag>
                  </div>
                </div>
                <div v-for="risk in compareResult.removed_risks" :key="`remove-${risk.code}-${risk.title}`" class="compare-item">
                  <div class="risk-header">
                    <strong>移除风险：{{ risk.title }}</strong>
                    <el-tag :type="riskTagType(risk.level)">{{ riskLevelLabel(risk.level) }}</el-tag>
                  </div>
                </div>
                <div
                  v-for="risk in compareResult.level_changed_risks"
                  :key="`level-${risk.code}-${risk.title}`"
                  class="compare-item"
                >
                  <strong>等级变化：{{ risk.title }}</strong>
                  <p>旧等级：{{ riskLevelLabel(risk.before_level) }} -> 新等级：{{ riskLevelLabel(risk.after_level) }}</p>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </template>
    </el-card>

    <el-card v-if="contract && canModifyContracts" class="detail-card">
      <template #header>
        <span>文档管理信息</span>
      </template>
      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :xs="24" :md="12">
            <el-form-item label="文件名">
              <el-input v-model="metadataForm.original_filename" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="所属用户 ID">
              <el-input-number v-model="metadataForm.owner_id" :min="1" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="分类">
              <el-input v-model="metadataForm.category" placeholder="如：施工合同" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="标签">
              <el-input v-model="metadataForm.tags_text" placeholder="用逗号分隔多个标签" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-button type="primary" :loading="savingMeta" @click="saveMetadata">保存文档信息</el-button>
      </el-form>
    </el-card>

    <el-row v-if="contract" :gutter="16">
      <el-col :xs="24" :lg="12">
        <el-card class="detail-card">
          <template #header>
            <div class="card-header">
              <span>合同基础信息</span>
              <el-tag v-if="contract.review_result" type="success">已提取</el-tag>
            </div>
          </template>

          <el-descriptions :column="1" border v-if="contract.review_result">
            <el-descriptions-item label="合同名称">{{ contract.review_result.extracted_fields.contract_name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="合同编号">{{ contract.review_result.extracted_fields.contract_number || "-" }}</el-descriptions-item>
            <el-descriptions-item label="项目名称">{{ contract.review_result.extracted_fields.project_name || "-" }}</el-descriptions-item>
            <el-descriptions-item label="甲方">{{ contract.review_result.extracted_fields.party_a || "-" }}</el-descriptions-item>
            <el-descriptions-item label="乙方">{{ contract.review_result.extracted_fields.party_b || "-" }}</el-descriptions-item>
            <el-descriptions-item label="合同类型">{{ contract.review_result.extracted_fields.contract_type || "-" }}</el-descriptions-item>
            <el-descriptions-item label="签订日期">{{ contract.review_result.extracted_fields.sign_date || "-" }}</el-descriptions-item>
            <el-descriptions-item label="合同金额">{{ contract.review_result.extracted_fields.contract_amount || "-" }}</el-descriptions-item>
            <el-descriptions-item label="工期">{{ contract.review_result.extracted_fields.construction_period || "-" }}</el-descriptions-item>
            <el-descriptions-item label="付款条款">{{ contract.review_result.extracted_fields.payment_terms || "-" }}</el-descriptions-item>
            <el-descriptions-item label="质保期">{{ contract.review_result.extracted_fields.warranty_period || "-" }}</el-descriptions-item>
            <el-descriptions-item label="争议解决">{{ contract.review_result.extracted_fields.dispute_resolution || "-" }}</el-descriptions-item>
            <el-descriptions-item label="违约责任">{{ contract.review_result.extracted_fields.breach_liability || "-" }}</el-descriptions-item>
          </el-descriptions>

          <el-empty v-else description="尚未执行审查" />
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card class="detail-card">
          <template #header>
            <div class="card-header">
              <span>风险展示区</span>
              <el-tag type="warning">{{ riskCount }} 项风险</el-tag>
            </div>
          </template>

          <div v-if="contract.review_result?.risks?.length" class="risk-list">
            <el-card
              v-for="risk in contract.review_result.risks"
              :key="risk.code"
              class="risk-item"
              shadow="never"
            >
              <div class="risk-header">
                <div class="risk-title-group">
                  <strong>{{ risk.title }}</strong>
                  <el-tag size="small" :type="riskSourceTagType(risk.source)">
                    {{ riskSourceLabel(risk.source) }}
                  </el-tag>
                </div>
                <el-tag :type="riskTagType(risk.level)">{{ riskLevelLabel(risk.level) }}</el-tag>
              </div>
              <p>{{ risk.description }}</p>
              <p><strong>命中内容：</strong>{{ risk.matched_text || "规则缺失或兜底命中" }}</p>
              <p><strong>建议：</strong>{{ risk.recommendation }}</p>
              <p v-if="risk.match_detail?.condition_type">
                <strong>来源说明：</strong>{{ conditionTypeLabel(risk.match_detail.condition_type) }}
              </p>
            </el-card>
          </div>
          <el-empty v-else description="暂无风险结果" />
        </el-card>
      </el-col>
    </el-row>

    <el-card v-if="contract" class="detail-card">
      <template #header>
        <div class="card-header">
          <span>审查摘要</span>
          <el-tag v-if="contract.review_result">{{ providerLabel(contract.review_result.provider) }}</el-tag>
        </div>
      </template>
      <p>{{ contract.review_result?.summary || "尚未生成审查摘要" }}</p>
    </el-card>

    <el-card v-if="contract" class="detail-card">
      <template #header>
        <span>原始解析文本</span>
      </template>
      <el-empty v-if="contract.parse_status === 'processing'" description="后台 OCR 识别中，页面会自动刷新。" />
      <el-empty v-else-if="contract.parse_status === 'failed'" description="解析失败，请检查 OCR 依赖或重新上传更清晰的扫描件。" />
      <pre v-else class="raw-text">{{ contract.raw_text }}</pre>
    </el-card>

    <el-drawer v-model="versionDetailVisible" size="42%" title="上传版本详情">
      <template v-if="selectedVersion">
        <el-alert
          :closable="false"
          :type="selectedVersionRuntimeStatus.summaryType"
          :title="selectedVersionRuntimeStatus.message"
          class="page-note"
        />
        <el-descriptions :column="1" border>
          <el-descriptions-item label="上传版本">V{{ selectedVersion.version_no }}</el-descriptions-item>
          <el-descriptions-item label="文件名">{{ selectedVersion.original_filename }}</el-descriptions-item>
          <el-descriptions-item label="审查状态">{{ selectedVersion.review_status === "completed" ? "已审查" : "未审查" }}</el-descriptions-item>
          <el-descriptions-item label="触发人">{{ selectedVersion.triggered_by_username || "-" }}</el-descriptions-item>
          <el-descriptions-item label="触发来源">{{ triggerSourceLabel(selectedVersion.trigger_source) }}</el-descriptions-item>
          <el-descriptions-item label="最终审查模式">{{ selectedVersionRuntimeStatus.finalProvider }}</el-descriptions-item>
          <el-descriptions-item label="摘要状态">{{ selectedVersionRuntimeStatus.summaryStatus }}</el-descriptions-item>
          <el-descriptions-item label="风险补充状态">{{ selectedVersionRuntimeStatus.riskStatus }}</el-descriptions-item>
          <el-descriptions-item label="总体风险">{{ riskLevelLabel(selectedVersion.overall_risk_level) }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ selectedVersion.created_at }}</el-descriptions-item>
          <el-descriptions-item label="摘要">{{ selectedVersion.summary }}</el-descriptions-item>
        </el-descriptions>
        <el-divider>风险项</el-divider>
        <div v-if="selectedVersion.risk_items?.length" class="risk-list">
          <el-card
            v-for="risk in selectedVersion.risk_items"
            :key="`${selectedVersion.id}-${risk.code}-${risk.title}`"
            class="risk-item"
            shadow="never"
          >
            <div class="risk-header">
              <div class="risk-title-group">
                <strong>{{ risk.title }}</strong>
                <el-tag size="small" :type="riskSourceTagType(risk.source)">
                  {{ riskSourceLabel(risk.source) }}
                </el-tag>
              </div>
              <el-tag :type="riskTagType(risk.level)">{{ riskLevelLabel(risk.level) }}</el-tag>
            </div>
            <p>{{ risk.description }}</p>
            <p><strong>命中内容：</strong>{{ risk.matched_text || "-" }}</p>
            <p><strong>建议：</strong>{{ risk.recommendation }}</p>
            <p v-if="risk.match_detail?.condition_type">
              <strong>来源说明：</strong>{{ conditionTypeLabel(risk.match_detail.condition_type) }}
            </p>
          </el-card>
        </div>
        <el-empty v-else description="该版本暂无风险项" />
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.meta-tags {
  margin-top: 8px;
  display: flex;
  gap: 8px;
}

.header-action-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.parse-notice {
  margin-top: 8px;
  color: #8c6d1f;
}

.parse-error {
  margin-top: 8px;
  color: #c45656;
}

.compare-summary {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.compare-card {
  height: 100%;
}

.compare-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.compare-item {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f8fafc;
}

.compare-item p {
  margin: 6px 0 0;
}

.risk-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.runtime-status-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.runtime-status-card {
  min-height: 72px;
}

.runtime-status-line {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.runtime-status-label {
  color: #606266;
}

@media (max-width: 960px) {
  .runtime-status-grid {
    grid-template-columns: 1fr;
  }
}
</style>
