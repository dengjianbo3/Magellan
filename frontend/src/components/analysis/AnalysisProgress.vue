<template>
  <div class="analysis-progress">
    <!-- Header -->
    <div class="header">
      <div class="header-left">
        <h1 v-if="targetName && targetName !== 'Unknown Project'">{{ t('analysisWizard.analysisFor') }}: {{ targetName }}</h1>
        <h1 v-else>{{ t('analysisWizard.analysis') }}</h1>
      </div>
      <div class="header-right">
        <button class="btn-cancel" @click="handleCancel">{{ t('analysisWizard.cancelAnalysis') }}</button>
      </div>
    </div>

    <!-- Overall Progress -->
    <div class="overall-progress">
      <div class="progress-header">
        <span class="progress-label">{{ t('analysisWizard.overallProgress') }}</span>
        <span class="progress-percentage">{{ overallProgress }}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: overallProgress + '%' }"></div>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-label">{{ t('analysisWizard.estimatedTimeRemaining') }}</div>
        <div class="stat-value">{{ estimatedTimeRemaining }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">{{ t('analysisWizard.agentsActive') }}</div>
        <div class="stat-value">{{ activeAgentsCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">{{ t('analysisWizard.analysisStarted') }}</div>
        <div class="stat-value">{{ analysisStartTime }}</div>
      </div>
    </div>

    <!-- Main Content: Agent Status & Analysis Results -->
    <div class="content-grid">
      <!-- AI Agent Status -->
      <div class="agent-status-panel">
        <h3 class="panel-title">{{ t('analysisWizard.aiAgentStatus') }}</h3>
        <div class="agent-list">
          <div
            v-for="agent in agents"
            :key="agent.id"
            :class="['agent-item', agent.status]"
          >
            <div class="agent-icon" :style="{ backgroundColor: agent.iconColor }">
              <span class="material-symbols-outlined">{{ agent.icon }}</span>
            </div>
            <div class="agent-info">
              <div class="agent-name">{{ agent.name }}</div>
              <div class="agent-message">{{ agent.message }}</div>
            </div>
            <div class="agent-status-icon">
              <span v-if="agent.status === 'completed'" class="material-symbols-outlined status-completed">check_circle</span>
              <span v-else-if="agent.status === 'running'" class="spinner"></span>
              <span v-else class="material-symbols-outlined status-queued">radio_button_unchecked</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Analysis Results (Workflow步骤列表) -->
      <div class="workflow-steps-panel">
      <div
        v-for="(step, index) in workflow"
        :key="step.id"
        :class="['step-item', step.status]"
      >
        <!-- 步骤图标 -->
        <div class="step-icon">
          <span v-if="step.status === 'success'">✓</span>
          <span v-else-if="step.status === 'error'">✗</span>
          <span v-else-if="step.status === 'running'" class="spinner">⟳</span>
          <span v-else class="step-number">{{ index + 1 }}</span>
        </div>

        <!-- 步骤内容 -->
        <div class="step-content">
          <div class="step-header">
            <h4>{{ step.name }}</h4>
            <span v-if="step.agent" class="agent-tag">{{ step.agent }}</span>
          </div>

          <!-- 进度条 (运行中) -->
          <div v-if="step.status === 'running' && step.progress > 0" class="step-progress">
            <div class="progress-bar-mini">
              <div class="progress-fill" :style="{ width: step.progress + '%' }"></div>
            </div>
            <span class="progress-text">{{ step.progress }}%</span>
          </div>

          <!-- Agent消息 -->
          <div v-if="currentAgentMessage && step.status === 'running'" class="agent-message">
            💬 {{ currentAgentMessage }}
          </div>

          <!-- 结果摘要 -->
          <StepResultCard
            v-if="step.status === 'success' && step.result"
            :result="step.result"
            :step-type="step.id"
          />

          <!-- 错误信息 -->
          <div v-if="step.status === 'error' && step.error" class="step-error">
            ✗ {{ step.error }}
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- 快速判断结果 (如果是quick模式) -->
    <div v-if="quickJudgment" class="quick-judgment-result">
      <div class="judgment-header">
        <h3>{{ t('analysisWizard.quickJudgmentResult') }}</h3>
        <span class="judgment-time">{{ quickJudgment.judgment_time }}</span>
      </div>

      <!-- 建议和评分 -->
      <div class="judgment-main">
        <div :class="['recommendation-card', quickJudgment.recommendation.toLowerCase()]">
          <span class="recommendation-icon">
            {{ getRecommendationIcon(quickJudgment.recommendation) }}
          </span>
          <div class="recommendation-info">
            <span class="recommendation-label">{{ t('analysisWizard.recommendation') }}</span>
            <span class="recommendation-text">
              {{ getRecommendationText(quickJudgment.recommendation) }}
            </span>
          </div>
        </div>

        <div class="score-card">
          <span class="score-value">{{ (quickJudgment.confidence * 100).toFixed(0) }}</span>
          <span class="score-unit">{{ t('analysisWizard.score') }}</span>
          <span class="score-label">{{ t('analysisWizard.overallScore') }}</span>
        </div>
      </div>

      <!-- 结论 -->
      <div class="verdict-section">
        <div class="section-header">{{ t('analysisWizard.verdict') }}</div>
        <p class="verdict-text">{{ quickJudgment.summary?.verdict }}</p>
      </div>

      <!-- 关键点 -->
      <div v-if="quickJudgment.summary?.key_positive?.length || quickJudgment.summary?.key_concern?.length" class="key-points">
        <div v-if="quickJudgment.summary?.key_positive?.length" class="points-group positive">
          <div class="points-label">{{ t('analysisWizard.advantages') }}</div>
          <ul>
            <li v-for="(point, idx) in quickJudgment.summary.key_positive" :key="idx">{{ point }}</li>
          </ul>
        </div>
        <div v-if="quickJudgment.summary?.key_concern?.length" class="points-group concern">
          <div class="points-label">{{ t('analysisWizard.concerns') }}</div>
          <ul>
            <li v-for="(point, idx) in quickJudgment.summary.key_concern" :key="idx">{{ point }}</li>
          </ul>
        </div>
      </div>

      <!-- 下一步建议 -->
      <div v-if="quickJudgment.next_steps?.recommended_action" class="next-steps-section">
        <div class="section-header">{{ t('analysisWizard.nextSteps') }}</div>
        <div class="action-highlight">{{ quickJudgment.next_steps.recommended_action }}</div>
        <ul v-if="quickJudgment.next_steps.focus_areas" class="focus-areas">
          <li v-for="(area, index) in quickJudgment.next_steps.focus_areas" :key="index">
            {{ area }}
          </li>
        </ul>
      </div>

      <!-- 操作按钮 -->
      <div class="quick-actions">
        <button
          v-if="quickJudgment.recommendation === 'FURTHER_DD'"
          class="btn-upgrade"
          @click="upgradeToStandard"
        >
          {{ t('analysisWizard.upgradeToStandard') }}
        </button>
        <button class="btn-export" @click="exportReport">
          {{ t('analysisWizard.exportReport') }}
        </button>
      </div>
    </div>

    <!-- 完成状态 -->
    <div v-if="analysisStatus === 'completed'" class="completion-message">
      <div class="completion-icon">✅</div>
      <h3>{{ t('analysisWizard.analysisCompleted') }}</h3>
      <p>{{ t('analysisWizard.analysisCompletedHint') }}</p>
      <button class="btn-view-report" @click="viewReport">
        {{ t('analysisWizard.viewFullReport') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';
import { useToast } from '@/composables/useToast';
import analysisServiceV2 from '@/services/analysisServiceV2.js';
import StepResultCard from './StepResultCard.vue';

const { t, locale: currentLang } = useLanguage();
const { info } = useToast();

const props = defineProps({
  sessionId: {
    type: String,
    required: true
  },
  scenario: {
    type: Object,
    required: true
  },
  depth: {
    type: String,
    default: 'quick'
  },
  projectName: {
    type: String,
    required: false,
    default: ''
  },
  targetData: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['analysis-complete', 'cancel']);

const analysisStatus = ref('running');
const workflow = ref([]);
const currentStepIndex = ref(0);
const overallProgress = ref(0); // Initialize to 0, will be updated by workflow progress
const currentAgentMessage = ref('');
const quickJudgment = ref(null);
const elapsedTime = ref('0m0s');

let elapsedTimer = null;
let startTime = Date.now();

// Agents configuration based on scenario
const getAgentsForScenario = (scenarioId) => {
  const agentConfigs = {
    'early_stage_dd': [
      {
        id: 'team_evaluator',
        name: t('analysis.step2.agents.teamEvaluator.name'),
        message: t('earlyStage.analyzingTeamBackground'),
        icon: 'groups',
        iconColor: '#3b82f6'
      },
      {
        id: 'market_analyst',
        name: t('analysis.step2.agents.marketAnalyst.name'),
        message: t('earlyStage.analyzingMarketSize'),
        icon: 'trending_up',
        iconColor: '#10b981'
      },
      {
        id: 'risk_assessor',
        name: t('analysis.step2.agents.riskAssessor.name'),
        message: t('earlyStage.scanningRedFlags'),
        icon: 'warning',
        iconColor: '#ef4444'
      }
    ],
    'growth_stage_dd': [
      {
        id: 'financial_expert',
        name: t('analysis.step2.agents.financialExpert.name'),
        message: t('growthStage.analyzingFinancialHealth'),
        icon: 'account_balance',
        iconColor: '#10b981'
      },
      {
        id: 'market_analyst',
        name: t('analysis.step2.agents.marketAnalyst.name'),
        message: t('growthStage.assessingGrowthPotential'),
        icon: 'insights',
        iconColor: '#3b82f6'
      },
      {
        id: 'market_analyst',
        name: t('analysis.step2.agents.marketAnalyst.name'),
        message: t('growthStage.analyzingMarketPosition'),
        icon: 'query_stats',
        iconColor: '#f59e0b'
      }
    ],
    'public_market_dd': [
      {
        id: 'financial_expert',
        name: t('analysis.step2.agents.financialExpert.name'),
        message: t('analysisWizard.runningGenerating'),
        icon: 'paid',
        iconColor: '#10b981'
      },
      {
        id: 'financial_expert',
        name: t('analysis.step2.agents.financialExpert.name'),
        message: t('publicMarket.fundamentalAnalysis'),
        icon: 'analytics',
        iconColor: '#3b82f6'
      },
      {
        id: 'market_analyst',
        name: t('analysis.step2.agents.marketAnalyst.name'),
        message: t('publicMarket.technicalIndicators'),
        icon: 'show_chart',
        iconColor: '#f59e0b'
      }
    ],
    'industry_research': [
      {
        id: 'market_analyst',
        name: t('analysis.step2.agents.marketAnalyst.name'),
        message: t('analysisWizard.analyzing'),
        icon: 'public',
        iconColor: '#10b981'
      },
      {
        id: 'market_analyst',
        name: t('analysis.step2.agents.marketAnalyst.name'),
        message: t('analysisWizard.analyzing'),
        icon: 'groups',
        iconColor: '#3b82f6'
      },
      {
        id: 'market_analyst',
        name: t('analysis.step2.agents.marketAnalyst.name'),
        message: t('analysisWizard.analyzing'),
        icon: 'trending_up',
        iconColor: '#f59e0b'
      },
      {
        id: 'market_analyst',
        name: t('analysis.step2.agents.marketAnalyst.name'),
        message: t('analysisWizard.analyzing'),
        icon: 'lightbulb',
        iconColor: '#8b5cf6'
      }
    ],
    'alternative_investment_dd': [
      {
        id: 'tech_specialist',
        name: t('analysis.step2.agents.techSpecialist.name'),
        message: t('alternative.analyzingTechFoundation'),
        icon: 'developer_board',
        iconColor: '#3b82f6'
      },
      {
        id: 'financial_expert',
        name: t('analysis.step2.agents.financialExpert.name'),
        message: t('alternative.analyzingTokenomics'),
        icon: 'currency_bitcoin',
        iconColor: '#f59e0b'
      },
      {
        id: 'market_analyst',
        name: t('analysis.step2.agents.marketAnalyst.name'),
        message: t('alternative.analyzingCommunity'),
        icon: 'forum',
        iconColor: '#10b981'
      }
    ]
  };

  return agentConfigs[scenarioId] || agentConfigs['public_market_dd'];
};

const agents = computed(() => {
  // 如果workflow有数据，直接从workflow生成agents列表（已经翻译过）
  if (workflow.value.length > 0) {
    return workflow.value.map((step, index) => {
      // 确定状态
      let status = 'queued';
      if (step.status === 'success') {
        status = 'completed';
      } else if (step.status === 'running') {
        status = 'running';
      }

      // 确定图标和颜色（基于步骤序号或类型）
      const iconColors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4'];
      const icons = ['analytics', 'trending_up', 'show_chart', 'insights', 'assessment', 'query_stats'];

      return {
        id: step.id,
        name: step.name,  // 已经在handleWorkflowStart中翻译过
        message: step.status === 'running' ? t('analysisWizard.analyzing') : (step.status === 'success' ? t('analysisWizard.completed') : t('analysisWizard.queued')),
        icon: icons[index % icons.length],
        iconColor: iconColors[index % iconColors.length],
        status: status
      };
    });
  }

  // 如果workflow还没有数据，使用预定义配置
  const scenarioId = props.scenario?.id || 'public_market_dd';
  const baseAgents = getAgentsForScenario(scenarioId);

  return baseAgents.map(agent => ({
    ...agent,
    status: 'queued'
  }));
});

const targetName = computed(() => {
  return props.projectName || 'Unknown Project';
});

const estimatedTimeRemaining = computed(() => {
  // 根据深度估算总时间（分钟）
  const depthTimes = {
    quick: 5,
    standard: 15,
    comprehensive: 30
  };

  const totalMinutes = depthTimes[props.depth] || 5;
  const totalSeconds = totalMinutes * 60;

  // 计算已用时间
  const elapsed = Math.floor((Date.now() - startTime) / 1000);

  // 根据进度估算剩余时间
  const progress = overallProgress.value / 100;
  const estimatedTotal = progress > 0.1 ? elapsed / progress : totalSeconds;
  const remaining = Math.max(0, Math.floor(estimatedTotal - elapsed));

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;

  if (remaining === 0) {
    return t('analysisWizard.almostDone');
  }

  return `${minutes}${t('analysisWizard.minutes')} ${seconds}${t('analysisWizard.seconds')}`;
});

const activeAgentsCount = computed(() => {
  return agents.value.filter(a => a.status === 'running').length;
});

const analysisStartTime = computed(() => {
  const date = new Date(startTime);
  const lang = currentLang?.value || 'zh';
  return date.toLocaleTimeString(lang === 'zh' ? 'zh-CN' : 'en-US', {
    hour: '2-digit',
    minute: '2-digit'
  });
});

onMounted(() => {
  console.log('[AnalysisProgress] Mounted, session:', props.sessionId);
  console.log('[AnalysisProgress] Project name:', props.projectName);
  console.log('[AnalysisProgress] Target data:', props.targetData);
  console.log('[AnalysisProgress] Scenario:', props.scenario);
  console.log('[AnalysisProgress] Current lang:', currentLang.value);
  console.log('[AnalysisProgress] Test translation:', t('analysisWizard.almostDone'));

  // 注册消息处理器
  analysisServiceV2.on('workflow_start', handleWorkflowStart);
  analysisServiceV2.on('step_start', handleStepStart);
  analysisServiceV2.on('step_complete', handleStepComplete);
  analysisServiceV2.on('agent_event', handleAgentEvent);
  analysisServiceV2.on('quick_judgment_complete', handleQuickJudgmentComplete);
  analysisServiceV2.on('analysis_complete', handleAnalysisComplete);
  analysisServiceV2.on('error', handleError);

  // Stage 3: 刷新消息缓冲区，重放之前收到的消息
  console.log('[AnalysisProgress] Flushing message buffer...');
  analysisServiceV2.flushMessageBuffer();

  // 启动计时器
  elapsedTimer = setInterval(updateElapsedTime, 1000);
});

onUnmounted(() => {
  // 清理
  analysisServiceV2.off('workflow_start', handleWorkflowStart);
  analysisServiceV2.off('step_start', handleStepStart);
  analysisServiceV2.off('step_complete', handleStepComplete);
  analysisServiceV2.off('agent_event', handleAgentEvent);
  analysisServiceV2.off('quick_judgment_complete', handleQuickJudgmentComplete);
  analysisServiceV2.off('analysis_complete', handleAnalysisComplete);
  analysisServiceV2.off('error', handleError);

  if (elapsedTimer) {
    clearInterval(elapsedTimer);
  }
});

function handleWorkflowStart(message) {
  console.log('[Progress] Workflow start:', message);
  console.log('[Progress] Steps received:', message.data?.steps);

  // 详细日志 - 打印每个步骤的原始数据
  if (message.data?.steps) {
    message.data.steps.forEach((step, index) => {
      console.log(`[Progress] Step ${index + 1} RAW:`, JSON.stringify(step));
    });
  }

  if (!message.data || !message.data.steps) {
    console.error('[Progress] Invalid workflow_start message format:', message);
    return;
  }

  // Agent ID to i18n key mapping
  const agentKeyMap = {
    'market_analyst': 'analysis.step2.agents.marketAnalyst.name',
    'financial_expert': 'analysis.step2.agents.financialExpert.name',
    'team_evaluator': 'analysis.step2.agents.teamEvaluator.name',
    'risk_assessor': 'analysis.step2.agents.riskAssessor.name',
    'tech_specialist': 'analysis.step2.agents.techSpecialist.name',
    'legal_advisor': 'analysis.step2.agents.legalAdvisor.name',
    'report_synthesizer': 'analysis.step2.agents.marketAnalyst.name' // Fallback for report synthesizer
  };

  workflow.value = message.data.steps.map((s, index) => {
    console.log(`[Progress] Processing step ${index + 1}:`, {
      originalName: s.name,
      hasDot: s.name?.includes('.'),
      agent: s.agent
    });

    // 检测并翻译i18n key (包含"."的字符串)
    let displayName = s.name;
    if (displayName && displayName.includes('.')) {
      // 这是一个i18n key，使用t()翻译
      try {
        const translated = t(displayName);
        console.log(`[Progress] Translated "${displayName}" → "${translated}"`);
        displayName = translated;
      } catch (e) {
        console.warn(`[Progress] Failed to translate i18n key: ${displayName}`, e);
        // 如果翻译失败，保持原值
      }
    }

    // 处理agent字段 translation
    let displayAgent = s.agent;
    if (displayAgent) {
      if (displayAgent.includes('.')) {
        // 已经是 key
        try {
          displayAgent = t(displayAgent);
        } catch (e) {
           console.warn(`[Progress] Failed to translate agent key: ${displayAgent}`, e);
        }
      } else if (agentKeyMap[displayAgent]) {
        // 使用映射表
        try {
          displayAgent = t(agentKeyMap[displayAgent]);
        } catch (e) {
          console.warn(`[Progress] Failed to translate mapped agent: ${displayAgent}`, e);
        }
      }
    }

    return {
      id: s.id,
      name: displayName,
      agent: displayAgent,
      status: 'pending',
      progress: 0
    };
  });

  console.log('[Progress] Workflow initialized with', workflow.value.length, 'steps');
  console.log('[Progress] Final workflow data:', JSON.stringify(workflow.value.map(s => ({id: s.id, name: s.name, agent: s.agent}))));
}

function handleStepStart(message) {
  console.log('[Progress] Step start:', message);
  const stepId = message.data.step_id;
  const step = workflow.value.find(s => s.id === stepId);
  if (step) {
    step.status = 'running';
  }
  currentStepIndex.value = message.data.step_number - 1;
  updateOverallProgress();
}

function handleStepComplete(message) {
  console.log('[Progress] Step complete:', message);
  const stepId = message.data.step_id;
  const step = workflow.value.find(s => s.id === stepId);
  if (step) {
    step.status = 'success';
    step.progress = 100;
    step.result = message.data.result;
  }
  currentAgentMessage.value = '';
  updateOverallProgress();
}

function handleAgentEvent(message) {
  console.log('[Progress] Agent event:', message);
  if (message.data.event_type === 'thinking' || message.data.event_type === 'executing') {
    currentAgentMessage.value = message.data.message;
  }
}

function handleQuickJudgmentComplete(message) {
  console.log('[Progress] Quick judgment complete:', message);
  quickJudgment.value = message.data;
  analysisStatus.value = 'completed';
}

function handleAnalysisComplete(message) {
  console.log('[Progress] Analysis complete:', message);
  analysisStatus.value = 'completed';
  emit('analysis-complete', message.data);
}

function handleError(message) {
  console.error('[Progress] Error:', message);
  analysisStatus.value = 'error';
}

function updateOverallProgress() {
  const completedSteps = workflow.value.filter(s => s.status === 'success').length;
  const totalSteps = workflow.value.length;
  overallProgress.value = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
}

function updateElapsedTime() {
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  elapsedTime.value = `${minutes}${t('analysisWizard.minutes')}${seconds}${t('analysisWizard.seconds')}`;
}

function getRecommendationIcon(recommendation) {
  const iconMap = {
    'BUY': '✅',
    'PASS': '❌',
    'FURTHER_DD': '🔍',
    'INVEST': '✅'
  };
  return iconMap[recommendation] || '📊';
}

function getRecommendationText(recommendation) {
  const textMap = {
    'BUY': t('analysisWizard.recommendationBuy'),
    'PASS': t('analysisWizard.recommendationPass'),
    'FURTHER_DD': t('analysisWizard.recommendationFurtherDD'),
    'INVEST': t('analysisWizard.recommendationInvest')
  };
  return textMap[recommendation] || recommendation;
}

function upgradeToStandard() {
  console.log('[Progress] Upgrade to standard analysis');
  // TODO: 实现升级到标准分析
  info(t('analysisWizard.upgradeFeatureInDevelopment'));
}

function exportReport() {
  console.log('[Progress] Export report');
  // TODO: 导出报告
  info(t('analysisWizard.exportFeatureInDevelopment'));
}

function viewReport() {
  console.log('[Progress] View full report');
  emit('analysis-complete', { view: 'report' });
}

function handleCancel() {
  console.log('[Progress] Cancel analysis');
  emit('cancel');
}
</script>

<style scoped>
.analysis-progress {
  max-width: 1400px;
  margin: 0 auto;
  /* padding: 2rem; Removed to avoid double padding with parent */
  color: #e5e7eb;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #2d3748;
}

.header-left h1 {
  font-size: 1.75rem;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 0.5rem;
}

.subtitle {
  font-size: 0.95rem;
  color: #9ca3af;
}

.btn-cancel {
  padding: 0.65rem 1.5rem;
  background: transparent;
  border: 1px solid #4b5563;
  border-radius: 8px;
  color: #d1d5db;
  font-size: 0.95rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-cancel:hover {
  background: #374151;
  border-color: #6b7280;
}

/* Overall Progress */
.overall-progress {
  margin-bottom: 2rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.progress-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: #d1d5db;
}

.progress-percentage {
  font-size: 1.25rem;
  font-weight: 700;
  color: #3b82f6;
}

.progress-bar {
  height: 10px;
  background: #1f2937;
  border-radius: 5px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #2563eb);
  transition: width 0.5s ease;
}

/* Stats Row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: #1a1d26;
  border: 1px solid #2d3748;
  border-radius: 12px;
  padding: 1.25rem 1.5rem;
}

.stat-label {
  font-size: 0.85rem;
  color: #9ca3af;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f3f4f6;
}

/* Content Grid */
.content-grid {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

/* Panel Styles */
.agent-status-panel,
.workflow-steps-panel {
  background: #1a1d26;
  border: 1px solid #2d3748;
  border-radius: 12px;
  padding: 1.5rem;
}

.panel-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 1.25rem;
}

/* Agent List */
.agent-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #0f1117;
  border: 1px solid #374151;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.agent-item.running {
  border-color: #f59e0b;
  background: rgba(245, 158, 11, 0.05);
}

.agent-item.completed {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.05);
}

.agent-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.agent-icon .material-symbols-outlined {
  font-size: 1.5rem;
  color: white;
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: #f3f4f6;
  margin-bottom: 0.25rem;
}

.agent-message {
  font-size: 0.85rem;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-status-icon {
  flex-shrink: 0;
}

.status-completed {
  color: #10b981;
  font-size: 1.5rem;
}

.status-queued {
  color: #6b7280;
  font-size: 1.5rem;
}

.spinner {
  display: inline-block;
  width: 24px;
  height: 24px;
  border: 3px solid #374151;
  border-top-color: #f59e0b;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.step-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  margin-bottom: 1rem;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.step-item.running {
  border-color: var(--primary-color);
  background: var(--primary-bg-light);
}

.step-item.success {
  border-color: var(--success-color);
}

.step-item.error {
  border-color: var(--error-color);
}

.step-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--border-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-weight: 600;
}

.step-item.running .step-icon {
  background: var(--primary-color);
  color: white;
}

.step-item.success .step-icon {
  background: var(--success-color);
  color: white;
}

.step-item.error .step-icon {
  background: var(--error-color);
  color: white;
}

.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.step-content {
  flex: 1;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.step-header h4 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.agent-tag {
  padding: 0.25rem 0.75rem;
  background: var(--secondary-bg);
  color: var(--text-secondary);
  border-radius: 12px;
  font-size: 0.8rem;
}

.step-progress {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.progress-bar-mini {
  flex: 1;
  height: 6px;
  background: var(--border-color);
  border-radius: 3px;
  overflow: hidden;
}

.agent-message,
.step-result,
.step-error {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  padding: 0.5rem;
  border-radius: 6px;
}

.agent-message {
  background: var(--info-bg);
  color: var(--info-color);
}

.step-result {
  background: var(--success-bg);
  color: var(--success-color);
}

.step-error {
  background: var(--error-bg);
  color: var(--error-color);
}

/* 快速判断结果 */
.quick-judgment-result {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 1.5rem;
  margin-top: 2rem;
}

.judgment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border-color);
}

.judgment-header h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.judgment-time {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.judgment-main {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.recommendation-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  border-radius: 12px;
}

.recommendation-card.buy,
.recommendation-card.invest {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.recommendation-card.pass {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.recommendation-card.further_dd {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.recommendation-icon {
  font-size: 2rem;
}

.recommendation-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.recommendation-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.recommendation-text {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1rem 1.5rem;
  background: var(--primary-bg-light);
  border-radius: 12px;
  min-width: 100px;
}

.score-card .score-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--primary-color);
  line-height: 1;
}

.score-card .score-unit {
  font-size: 1rem;
  color: var(--primary-color);
}

.score-card .score-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 0.25rem;
}

.verdict-section,
.next-steps-section {
  margin-bottom: 1rem;
  padding: 1rem;
  background: var(--secondary-bg);
  border-radius: 8px;
}

.section-header {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
}

.verdict-text {
  color: var(--text-primary);
  line-height: 1.5;
  margin: 0;
  font-size: 0.95rem;
}

.key-points {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1rem;
}

.points-group {
  padding: 1rem;
  border-radius: 8px;
}

.points-group.positive {
  background: rgba(16, 185, 129, 0.08);
  border-left: 3px solid var(--success-color);
}

.points-group.concern {
  background: rgba(245, 158, 11, 0.08);
  border-left: 3px solid var(--warning-color);
}

.points-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.5rem;
}

.points-group.positive .points-label {
  color: var(--success-color);
}

.points-group.concern .points-label {
  color: var(--warning-color);
}

.points-group ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.points-group li {
  font-size: 0.85rem;
  color: var(--text-primary);
  padding: 0.25rem 0;
  line-height: 1.4;
}

.action-highlight {
  font-size: 1rem;
  font-weight: 600;
  color: var(--primary-color);
  margin-bottom: 0.75rem;
}

.focus-areas {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.focus-areas li {
  padding: 0.35rem 0.75rem;
  background: var(--card-bg);
  border-radius: 4px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.quick-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color);
}

.btn-upgrade,
.btn-export {
  padding: 0.6rem 1.25rem;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
}

.btn-upgrade {
  background: var(--primary-color);
  color: white;
}

.btn-upgrade:hover {
  background: var(--primary-color-dark);
}

.btn-export {
  background: var(--secondary-bg);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
}

.btn-export:hover {
  background: var(--secondary-bg-hover);
}

/* 完成状态 */
.completion-message {
  text-align: center;
  padding: 3rem;
}

.completion-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.completion-message h3 {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.completion-message p {
  color: var(--text-secondary);
  margin-bottom: 2rem;
}

.btn-view-report {
  padding: 1rem 2rem;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1.1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-view-report:hover {
  background: var(--primary-color-dark);
  transform: scale(1.05);
}

/* CSS变量 */
:root {
  --text-primary: #1a1a1a;
  --text-secondary: #666;
  --card-bg: #ffffff;
  --border-color: #e0e0e0;
  --primary-color: #3b82f6;
  --primary-color-dark: #2563eb;
  --primary-bg-light: #eff6ff;
  --secondary-bg: #f3f4f6;
  --secondary-bg-hover: #e5e7eb;
  --success-color: #10b981;
  --success-bg: #d1fae5;
  --error-color: #ef4444;
  --error-bg: #fee2e2;
  --warning-color: #f59e0b;
  --warning-bg: #fef3c7;
  --info-color: #3b82f6;
  --info-bg: #dbeafe;
}

.dark {
  --text-primary: #e5e5e5;
  --text-secondary: #a1a1a1;
  --card-bg: #1e1e1e;
  --border-color: #333;
  --primary-bg-light: #1e3a8a;
  --secondary-bg: #2a2a2a;
  --secondary-bg-hover: #333;
  --success-bg: #064e3b;
  --error-bg: #7f1d1d;
  --warning-bg: #78350f;
  --info-bg: #1e3a8a;
}
</style>
