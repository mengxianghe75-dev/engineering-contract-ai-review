<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { UploadFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

import { fetchContractDetail, uploadContract } from "../api/contracts";

const router = useRouter();
const route = useRoute();
const uploading = ref(false);
const fileList = ref([]);
const versionSource = ref(null);

async function handleChange(uploadFile) {
  fileList.value = [uploadFile];
}

async function loadVersionSource() {
  const versionOfContractId = route.query.version_of_contract_id;
  if (!versionOfContractId) {
    versionSource.value = null;
    return;
  }
  try {
    const { data } = await fetchContractDetail(versionOfContractId);
    versionSource.value = data;
  } catch (error) {
    versionSource.value = null;
    ElMessage.error(error.response?.data?.detail || "获取基准合同版本失败");
  }
}

async function submitUpload() {
  const file = fileList.value[0]?.raw;
  if (!file) {
    ElMessage.warning("请先选择 PDF 文件");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  uploading.value = true;
  try {
    const { data } = await uploadContract(formData, route.query.version_of_contract_id || null);
    ElMessage.success(data.parse_status === "processing" ? "上传成功，后台 OCR 识别已开始" : "上传成功");
    router.push(`/contracts/${data.file_id}`);
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "上传失败");
  } finally {
    uploading.value = false;
  }
}

onMounted(loadVersionSource);
</script>

<template>
  <div class="page-stack">
    <el-card>
      <template #header>
        <div>
          <h3>上传合同</h3>
          <p>
            {{
              versionSource
                ? `当前将上传为合同组 ${versionSource.contract_group_id} 的新版本，基于 V${versionSource.upload_version_no} 继续追加。`
                : "仅支持 PDF，扫描件会自动尝试 OCR，耗时会比文本型 PDF 更长。测试路径：`/contracts/upload`"
            }}
          </p>
        </div>
      </template>

      <el-alert
        v-if="versionSource"
        type="info"
        :closable="false"
        class="page-note"
        :title="`将作为上传版本 V${versionSource.version_count + 1}`"
        :description="`基准文件：${versionSource.original_filename}；当前合同组共 ${versionSource.version_count} 个上传版本。`"
      />

      <el-upload
        drag
        :auto-upload="false"
        :limit="1"
        accept=".pdf,application/pdf"
        :file-list="fileList"
        :on-change="handleChange"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将 PDF 拖到此处，或点击选择文件</div>
        <template #tip>
          <div class="el-upload__tip">非 PDF 文件会被后端拒绝，扫描件依赖后端 OCR 环境。</div>
        </template>
      </el-upload>

      <div class="upload-actions">
        <el-button type="primary" :loading="uploading" @click="submitUpload">
          开始上传
        </el-button>
      </div>
    </el-card>
  </div>
</template>
