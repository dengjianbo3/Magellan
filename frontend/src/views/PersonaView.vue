<!-- src/views/PersonaView.vue -->
<template>
  <div class="persona-container">
    <header class="view-header">
      <h2>设置您的投资画像</h2>
      <p>为了给您提供最匹配的分析，请花一分钟告诉我们您的偏好。</p>
    </header>

    <main class="form-area">
      <GlassPaper>
        <div class="form-section">
          <h3 class="form-section-title">1. 您的投资风格更偏向？</h3>
          <el-radio-group v-model="persona.investment_style" size="large">
            <el-radio-button label="Value">价值型</el-radio-button>
            <el-radio-button label="Growth">成长型</el-radio-button>
            <el-radio-button label="Balanced">平衡型</el-radio-button>
            <el-radio-button label="Conservative">保守型</el-radio-button>
          </el-radio-group>
        </div>

        <div class="form-section">
          <h3 class="form-section-title">2. 您偏好的报告样式？</h3>
          <el-radio-group v-model="persona.report_preference" size="large">
            <el-radio-button label="Executive Summary">高管摘要 (简要)</el-radio-button>
            <el-radio-button label="Deep Dive">深度分析 (详尽)</el-radio-button>
            <el-radio-button label="Data First">数据优先 (图表在前)</el-radio-button>
          </el-radio-group>
        </div>
        
        <div class="form-section">
          <h3 class="form-section-title">3. 您的风险承受能力？</h3>
           <el-radio-group v-model="persona.risk_tolerance" size="large">
            <el-radio-button label="Low">低</el-radio-button>
            <el-radio-button label="Medium">中</el-radio-button>
            <el-radio-button label="High">高</el-radio-button>
          </el-radio-group>
        </div>
      </GlassPaper>

      <div class="button-container">
        <el-button type="primary" size="large" @click="savePersona" :loading="isLoading" class="save-button">
          {{ isLoading ? '保存中...' : '保存我的偏好' }}
        </el-button>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ElRadioGroup, ElRadioButton, ElButton, ElMessage } from 'element-plus';
import GlassPaper from '../components/GlassPaper.vue';
import { getUserPersona, updateUserPersona, type UserPersona } from '../services/api';


const isLoading = ref(false);
const userId = 'default_user'; // In a real app, this would come from an auth system
const persona = ref<Partial<UserPersona>>({
  investment_style: 'Balanced',
  report_preference: 'Deep Dive',
  risk_tolerance: 'Medium',
});

onMounted(async () => {
  isLoading.value = true;
  try {
    const data = await getUserPersona(userId);
    persona.value = { ...persona.value, ...data };
  } catch (error) {
    ElMessage.error('加载用户画像失败。');
  } finally {
    isLoading.value = false;
  }
});

const savePersona = async () => {
  isLoading.value = true;
  try {
    await updateUserPersona(userId, { user_id: userId, ...persona.value });
    ElMessage.success('您的偏好已保存！');
  } catch (error) {
    ElMessage.error('保存用户画像失败。');
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.persona-container {
  height: 100%;
  overflow-y: auto;
  padding: 2rem 3rem;
}
.view-header { text-align: center; margin-bottom: 2rem; }
.view-header h2 { margin: 0; font-size: 1.8rem; font-weight: 600; }
.view-header p { color: rgba(255,255,255,0.7); max-width: 500px; margin: 0.5rem auto 0; }

.form-section {
  margin-bottom: 2.5rem;
}
.form-section-title {
  font-weight: 500;
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.2rem;
}
.button-container { text-align: center; margin-top: 2.5rem; }
.save-button {
  border-radius: 50px;
  padding: 1.2rem 2.5rem;
  font-weight: bold;
  font-size: 1rem;
}
</style>
