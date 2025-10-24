<!-- src/views/ReportView.vue -->
<template>
  <div class="report-view-container">
    <header class="view-header">
      <h2>深度报告生成器</h2>
      <p>请上传您的相关文件并提供一个股票代码，以生成一份全面的、多章节的投资报告。</p>
    </header>

    <main class="form-area">
      <GlassPaper>
        <h3 class="form-section-title">1. 目标公司</h3>
        <el-input
          v-model="ticker"
          placeholder="输入股票代码（例如：AAPL）"
          size="large"
          class="custom-input"
          :disabled="isLoading"
        />
      </GlassPaper>

      <GlassPaper style="margin-top: 2rem;">
        <h3 class="form-section-title">2. 上传文档</h3>
        <div class="upload-box">
          <el-upload
            drag
            multiple
            action="#"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :file-list="fileList"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖拽至此区域，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF, DOCX, XLSX 格式的文件
              </div>
            </template>
          </el-upload>
        </div>
      </GlassPaper>

      <div class="button-container">
        <el-button
          type="primary"
          size="large"
          @click="handleSubmit"
          :loading="isLoading"
          :disabled="!ticker || fileList.length === 0"
          class="generate-button"
        >
          {{ isLoading ? '生成中...' : '生成深度报告' }}
        </el-button>
      </div>
    </main>
    
    <div v-if="report" class="result-area">
       <GlassPaper>
          <h3 class="form-section-title">为 {{ report.company_ticker }} 生成的报告</h3>
          <div v-for="section in report.report_sections" :key="section.section_title" class="report-section">
            <h4>{{ section.section_title }}</h4>
            <p>{{ section.content }}</p>
          </div>
       </GlassPaper>
    </div>
     <div v-if="error" class="result-area error-box">
      <GlassPaper>
        <h3 class="form-section-title">发生错误</h3>
        <p>{{ error }}</p>
      </GlassPaper>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ElUpload, ElIcon, ElButton, ElInput, ElMessage } from 'element-plus';
import { UploadFilled } from '@element-plus/icons-vue';
import type { UploadFile, UploadFiles } from 'element-plus';
import GlassPaper from '../components/GlassPaper.vue';
import { generateDeepReport, type FullReport } from '../services/api';

const ticker = ref('');
const fileList = ref<UploadFile[]>([]);
const isLoading = ref(false);
const report = ref<FullReport | null>(null);
const error = ref<string | null>(null);

const handleFileChange = (_uploadFile: UploadFile, uploadFiles: UploadFiles) => {
  fileList.value = uploadFiles;
};

const handleFileRemove = (_uploadFile: UploadFile, uploadFiles: UploadFiles) => {
  fileList.value = uploadFiles;
};

const handleSubmit = async () => {
  isLoading.value = true;
  report.value = null;
  error.value = null;

  const rawFiles = fileList.value.map(f => f.raw).filter(f => f) as File[];
  if (rawFiles.length !== fileList.value.length) {
    ElMessage.error('部分文件尚未准备好上传。');
    isLoading.value = false;
    return;
  }

  try {
    const result = await generateDeepReport(ticker.value, rawFiles);
    report.value = result;
  } catch (e: any) {
    error.value = e.message || '生成报告期间发生未知错误。';
    if (error.value) {
      ElMessage.error(error.value);
    }
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.report-view-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 2rem 3rem;
}
.view-header { text-align: center; margin-bottom: 2rem; }
.view-header h2 { margin: 0; font-size: 1.8rem; font-weight: 600; }
.view-header p { color: rgba(255,255,255,0.7); max-width: 500px; margin: 0.5rem auto 0; }

.form-section-title {
  font-weight: 500;
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.2rem;
}

.upload-box { margin-top: 1rem; }
.button-container { text-align: center; margin-top: 2.5rem; }
.generate-button {
  border-radius: 50px;
  padding: 1.2rem 2.5rem;
  font-weight: bold;
  font-size: 1rem;
  background: linear-gradient(45deg, #FE6B8B 30%, #FF8E53 90%);
  border: none;
  box-shadow: 0 3px 5px 2px rgba(255, 105, 135, .3);
}

.result-area { margin-top: 3rem; animation: fadeIn 0.5s ease-in-out; }
.report-section { margin-bottom: 1.5rem; }
.report-section h4 { margin: 0 0 0.5rem 0; font-size: 1.1rem; font-weight: 600; color: #FF8E53; }
.report-section p { margin: 0; line-height: 1.6; white-space: pre-wrap; }

.error-box p {
  color: #F44336;
}

.custom-input {
  --el-input-bg-color: rgba(0, 0, 0, 0.2);
  --el-input-text-color: white;
  --el-border-color: rgba(255, 255, 255, 0.3);
  --el-input-hover-border-color: rgba(255, 255, 255, 0.5);
}
</style>
