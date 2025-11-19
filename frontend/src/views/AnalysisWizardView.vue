<template>
  <div class="analysis-wizard">
    <!-- 步骤指示器 -->
    <div class="wizard-steps">
      <div
        v-for="(step, index) in steps"
        :key="index"
        :class="['step', {
          'active': currentStep === index,
          'completed': currentStep > index
        }]"
      >
        <div class="step-number">
          <span v-if="currentStep > index">✓</span>
          <span v-else>{{ index + 1 }}</span>
        </div>
        <div class="step-label">{{ step.label }}</div>
      </div>
    </div>

    <!-- 步骤内容 -->
    <div class="wizard-content">
      <!-- Step 1: 场景选择 -->
      <ScenarioSelection
        v-if="currentStep === 0"
        @scenario-selected="handleScenarioSelected"
      />

      <!-- Step 2: 目标输入 -->
      <component
        v-if="currentStep === 1"
        :is="targetInputComponent"
        :scenario="selectedScenario"
        @target-configured="handleTargetConfigured"
        @back="currentStep--"
      />

      <!-- Step 3: 分析配置 -->
      <AnalysisConfig
        v-if="currentStep === 2"
        :scenario="selectedScenario"
        @config-complete="handleConfigComplete"
        @back="currentStep--"
      />

      <!-- Step 4: 分析进行中 -->
      <AnalysisProgress
        v-if="currentStep === 3"
        :session-id="sessionId"
        :scenario="selectedScenario"
        :depth="analysisConfig.depth"
        @analysis-complete="handleAnalysisComplete"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';
import analysisServiceV2 from '@/services/analysisServiceV2.js';

import ScenarioSelection from '@/components/analysis/ScenarioSelection.vue';
import EarlyStageInput from '@/components/analysis/EarlyStageInput.vue';
import GrowthInput from '@/components/analysis/GrowthInput.vue';
import PublicMarketInput from '@/components/analysis/PublicMarketInput.vue';
import AlternativeInput from '@/components/analysis/AlternativeInput.vue';
import IndustryResearchInput from '@/components/analysis/IndustryResearchInput.vue';
import AnalysisConfig from '@/components/analysis/AnalysisConfig.vue';
import AnalysisProgress from '@/components/analysis/AnalysisProgress.vue';

const { t } = useLanguage();

// 当前步骤
const currentStep = ref(0);

// 步骤定义
const steps = [
  { label: t('analysisWizard.selectScenario') || '选择场景' },
  { label: t('analysisWizard.inputTarget') || '输入目标' },
  { label: t('analysisWizard.configAnalysis') || '配置分析' },
  { label: t('analysisWizard.analyzing') || '分析中' }
];

// 选中的场景
const selectedScenario = ref(null);

// 目标配置
const targetConfig = ref({});

// 分析配置
const analysisConfig = ref({
  depth: 'quick', // quick | standard | comprehensive
  timeframe: '1Y',
  focus_areas: [],
  language: 'zh'
});

// Session ID
const sessionId = ref(null);

// 动态目标输入组件
const targetInputComponent = computed(() => {
  if (!selectedScenario.value) return null;

  const componentMap = {
    'early-stage-investment': EarlyStageInput,
    'growth-investment': GrowthInput,
    'public-market-investment': PublicMarketInput,
    'alternative-investment': AlternativeInput,
    'industry-research': IndustryResearchInput
  };

  return componentMap[selectedScenario.value.id];
});

// 处理场景选择
function handleScenarioSelected(scenario) {
  console.log('[Wizard] Scenario selected:', scenario);
  selectedScenario.value = scenario;
  currentStep.value = 1;
}

// 处理目标配置完成
function handleTargetConfigured(config) {
  console.log('[Wizard] Target configured:', config);
  targetConfig.value = config;
  currentStep.value = 2;
}

// 处理分析配置完成
async function handleConfigComplete(config) {
  console.log('[Wizard] Config complete:', config);
  analysisConfig.value = config;

  // 启动分析
  try {
    const request = {
      project_name: targetConfig.value.company_name || 'Analysis Project',
      scenario: selectedScenario.value.id,
      target: targetConfig.value,
      config: analysisConfig.value
    };

    const result = await analysisServiceV2.startAnalysis(request);
    sessionId.value = result.sessionId;

    // 进入分析进度页面
    currentStep.value = 3;

  } catch (error) {
    console.error('[Wizard] Failed to start analysis:', error);
    alert('启动分析失败: ' + error.message);
  }
}

// 处理分析完成
function handleAnalysisComplete(result) {
  console.log('[Wizard] Analysis complete:', result);
  // TODO: 跳转到报告查看页面
}
</script>

<style scoped>
.analysis-wizard {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  min-height: 100vh;
}

/* 步骤指示器 */
.wizard-steps {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 3rem;
  padding: 2rem 0;
  background: var(--card-bg);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  position: relative;
  flex: 1;
  max-width: 200px;
}

.step:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 20px;
  left: 50%;
  width: 100%;
  height: 2px;
  background: var(--border-color);
  z-index: -1;
}

.step.completed:not(:last-child)::after {
  background: var(--success-color);
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--border-color);
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 1.1rem;
  transition: all 0.3s ease;
}

.step.active .step-number {
  background: var(--primary-color);
  color: white;
  transform: scale(1.1);
}

.step.completed .step-number {
  background: var(--success-color);
  color: white;
}

.step-label {
  font-size: 0.9rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.step.active .step-label {
  color: var(--primary-color);
  font-weight: 600;
}

.step.completed .step-label {
  color: var(--success-color);
}

/* 内容区域 */
.wizard-content {
  background: var(--card-bg);
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  min-height: 600px;
}

/* CSS变量 */
:root {
  --text-primary: #1a1a1a;
  --text-secondary: #666;
  --card-bg: #ffffff;
  --border-color: #e0e0e0;
  --primary-color: #3b82f6;
  --success-color: #10b981;
}

.dark {
  --text-primary: #e5e5e5;
  --text-secondary: #a1a1a1;
  --card-bg: #1e1e1e;
  --border-color: #333;
}
</style>
