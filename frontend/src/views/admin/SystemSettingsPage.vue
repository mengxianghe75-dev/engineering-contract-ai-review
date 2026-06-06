<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import {
  fetchSystemSettings,
  testSystemSettings,
  updateSystemSettings,
} from "../../api/systemSettings";
import { providerLabel } from "../../utils/labels";

const loading = ref(false);
const saving = ref(false);
const testing = ref(false);
const testResult = ref(null);
const runtimeStatus = ref({
  effective_provider: "mock",
  llm_ready: false,
  status_message: "",
  last_test_success: null,
  last_test_message: null,
  last_tested_at: null,
  last_summary_call_success: null,
  last_summary_call_message: null,
  last_summary_called_at: null,
  last_risk_call_success: null,
  last_risk_call_message: null,
  last_risk_called_at: null,
});
const form = reactive({
  review_provider: "mock",
  llm_base_url: "",
  llm_model: "",
  llm_timeout_seconds: 30,
  llm_api_key: "",
  clear_llm_api_key: false,
});
const apiKeyConfigured = ref(false);

async function loadSettings() {
  loading.value = true;
  try {
    const { data } = await fetchSystemSettings();
    form.review_provider = data.review_provider;
    form.llm_base_url = data.llm_base_url || "";
    form.llm_model = data.llm_model || "";
    form.llm_timeout_seconds = data.llm_timeout_seconds || 30;
    form.llm_api_key = "";
    form.clear_llm_api_key = false;
    apiKeyConfigured.value = data.llm_api_key_configured;
    runtimeStatus.value = {
      effective_provider: data.effective_provider,
      llm_ready: data.llm_ready,
      status_message: data.status_message,
      last_test_success: data.last_test_success,
      last_test_message: data.last_test_message,
      last_tested_at: data.last_tested_at,
      last_summary_call_success: data.last_summary_call_success,
      last_summary_call_message: data.last_summary_call_message,
      last_summary_called_at: data.last_summary_called_at,
      last_risk_call_success: data.last_risk_call_success,
      last_risk_call_message: data.last_risk_call_message,
      last_risk_called_at: data.last_risk_called_at,
    };
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "获取系统设置失败");
  } finally {
    loading.value = false;
  }
}

async function saveSettings() {
  saving.value = true;
  try {
    const { data } = await updateSystemSettings({
      review_provider: form.review_provider,
      llm_base_url: form.llm_base_url,
      llm_model: form.llm_model,
      llm_timeout_seconds: form.llm_timeout_seconds,
      llm_api_key: form.llm_api_key || null,
      clear_llm_api_key: form.clear_llm_api_key,
    });
    apiKeyConfigured.value = data.llm_api_key_configured;
    runtimeStatus.value = {
      effective_provider: data.effective_provider,
      llm_ready: data.llm_ready,
      status_message: data.status_message,
      last_test_success: data.last_test_success,
      last_test_message: data.last_test_message,
      last_tested_at: data.last_tested_at,
      last_summary_call_success: data.last_summary_call_success,
      last_summary_call_message: data.last_summary_call_message,
      last_summary_called_at: data.last_summary_called_at,
      last_risk_call_success: data.last_risk_call_success,
      last_risk_call_message: data.last_risk_call_message,
      last_risk_called_at: data.last_risk_called_at,
    };
    form.llm_api_key = "";
    form.clear_llm_api_key = false;
    ElMessage.success("系统设置已保存");
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "保存系统设置失败");
  } finally {
    saving.value = false;
  }
}

async function runConnectionTest() {
  testing.value = true;
  testResult.value = null;
  try {
    const { data } = await testSystemSettings({
      review_provider: form.review_provider,
      llm_base_url: form.llm_base_url,
      llm_model: form.llm_model,
      llm_timeout_seconds: form.llm_timeout_seconds,
      llm_api_key: form.llm_api_key || null,
    });
    testResult.value = data;
    ElMessage.success(data.message);
    await loadSettings();
  } catch (error) {
    const detail = error.response?.data?.detail || "模型连通性测试失败";
    testResult.value = { success: false, provider: form.review_provider, message: detail };
    ElMessage.error(detail);
  } finally {
    testing.value = false;
  }
}

onMounted(loadSettings);
</script>

<template>
  <div class="page-stack" v-loading="loading">
    <el-card>
      <div class="page-toolbar">
        <div>
          <h3>系统设置</h3>
          <p>管理员可直接在前端界面配置大模型模式、地址、模型名和超时时间。测试路径：`/admin/settings`</p>
        </div>
      </div>

      <el-alert
        type="info"
        :closable="false"
        title="当前大模型配置只影响摘要生成和大模型风险补充识别；规则引擎仍然优先执行。"
        class="page-note"
      />

      <el-row :gutter="16" class="page-note">
        <el-col :xs="24" :md="8">
          <el-card shadow="never">
            <div class="status-block">
              <span class="status-label">当前生效模式</span>
              <el-tag :type="runtimeStatus.effective_provider === 'openai_compatible' ? 'success' : 'info'">
                {{ providerLabel(runtimeStatus.effective_provider) }}
              </el-tag>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-card shadow="never">
            <div class="status-block">
              <span class="status-label">模型配置完整度</span>
              <el-tag :type="runtimeStatus.llm_ready ? 'success' : 'warning'">
                {{ runtimeStatus.llm_ready ? "已就绪" : "未就绪" }}
              </el-tag>
            </div>
          </el-card>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-card shadow="never">
            <div class="status-block">
              <span class="status-label">最近测试结果</span>
              <el-tag
                v-if="runtimeStatus.last_test_success !== null"
                :type="runtimeStatus.last_test_success ? 'success' : 'danger'"
              >
                {{ runtimeStatus.last_test_success ? "成功" : "失败" }}
              </el-tag>
              <el-tag v-else type="info">未测试</el-tag>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <el-alert
        :title="runtimeStatus.status_message || '尚未生成状态说明'"
        :type="runtimeStatus.llm_ready && runtimeStatus.effective_provider === 'openai_compatible' ? 'success' : 'warning'"
        :closable="false"
        class="page-note"
      />

      <el-form label-position="top">
        <el-row :gutter="16">
          <el-col :xs="24" :md="12">
            <el-form-item label="审查模式">
              <el-select v-model="form.review_provider" class="full-width">
                <el-option label="模拟模式" value="mock" />
                <el-option label="OpenAI 兼容模式" value="openai_compatible" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="大模型超时（秒）">
              <el-input-number v-model="form.llm_timeout_seconds" :min="1" :max="300" class="full-width" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="大模型接入地址">
              <el-input
                v-model="form.llm_base_url"
                placeholder="如：https://api.openai.com/v1"
                :disabled="form.review_provider === 'mock'"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-form-item label="模型名称">
              <el-input
                v-model="form.llm_model"
                placeholder="如：gpt-4o-mini 或 qwen-plus"
                :disabled="form.review_provider === 'mock'"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24">
            <el-form-item label="API 密钥">
              <el-input
                v-model="form.llm_api_key"
                type="password"
                show-password
                placeholder="留空表示保持当前密钥不变"
                :disabled="form.review_provider === 'mock'"
              />
              <div class="setting-hint">
                <el-tag v-if="apiKeyConfigured" type="success">当前已保存 API 密钥</el-tag>
                <el-checkbox v-model="form.clear_llm_api_key" :disabled="form.review_provider === 'mock'">
                  清空已保存 API 密钥
                </el-checkbox>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        <div class="filter-actions">
          <el-button type="primary" :loading="saving" @click="saveSettings">保存设置</el-button>
          <el-button :loading="testing" @click="runConnectionTest">测试连接</el-button>
        </div>
      </el-form>

      <el-alert
        v-if="testResult"
        :title="testResult.success ? '连接测试成功' : '连接测试失败'"
        :description="testResult.message"
        :type="testResult.success ? 'success' : 'error'"
        :closable="false"
        class="page-note"
      />

      <el-descriptions v-if="runtimeStatus.last_tested_at" :column="1" border class="page-note">
        <el-descriptions-item label="最近测试时间">
          {{ runtimeStatus.last_tested_at }}
        </el-descriptions-item>
        <el-descriptions-item label="最近测试说明">
          {{ runtimeStatus.last_test_message || "-" }}
        </el-descriptions-item>
      </el-descriptions>

      <el-row :gutter="16">
        <el-col :xs="24" :lg="12">
          <el-card shadow="never" class="page-note">
            <template #header>
              <span>最近一次真实摘要调用</span>
            </template>
            <el-empty v-if="!runtimeStatus.last_summary_called_at" description="暂无真实摘要调用记录" />
            <el-descriptions v-else :column="1" border>
              <el-descriptions-item label="结果">
                <el-tag :type="runtimeStatus.last_summary_call_success ? 'success' : 'danger'">
                  {{ runtimeStatus.last_summary_call_success ? "成功" : "失败" }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="时间">
                {{ runtimeStatus.last_summary_called_at }}
              </el-descriptions-item>
              <el-descriptions-item label="说明">
                {{ runtimeStatus.last_summary_call_message || "-" }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="12">
          <el-card shadow="never" class="page-note">
            <template #header>
              <span>最近一次真实风险补充调用</span>
            </template>
            <el-empty v-if="!runtimeStatus.last_risk_called_at" description="暂无真实大模型风险补充调用记录" />
            <el-descriptions v-else :column="1" border>
              <el-descriptions-item label="结果">
                <el-tag :type="runtimeStatus.last_risk_call_success ? 'success' : 'danger'">
                  {{ runtimeStatus.last_risk_call_success ? "成功" : "失败" }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="时间">
                {{ runtimeStatus.last_risk_called_at }}
              </el-descriptions-item>
              <el-descriptions-item label="说明">
                {{ runtimeStatus.last_risk_call_message || "-" }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<style scoped>
.page-note {
  margin-bottom: 16px;
}

.status-block {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.status-label {
  color: #606266;
}

.setting-hint {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 8px;
  flex-wrap: wrap;
}
</style>
