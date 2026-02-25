<template>
  <div class="analysis-progress">
    <!-- Connection Status Banner -->
    <div v-if="connectionState === 'reconnecting'" class="connection-banner warning">
      <span class="material-symbols-outlined">sync</span>
      <span>{{ t('analysisWizard.reconnecting') }}</span>
    </div>
    <div v-if="connectionState === 'error'" class="connection-banner error">
      <span class="material-symbols-outlined">wifi_off</span>
      <span>{{ t('analysisWizard.connectionLost') }}</span>
    </div>

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
              <div class="agent-message-text">{{ agent.message }}</div>
            </div>
            <div class="agent-status-icon">
              <span v-if="agent.status === 'completed'" class="material-symbols-outlined status-completed">check_circle</span>
              <span v-else-if="agent.status === 'running'" class="loading-ring" aria-hidden="true"></span>
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
          <span v-if="step.status === 'success'" class="material-symbols-outlined">check</span>
          <span v-else-if="step.status === 'error'" class="material-symbols-outlined">close</span>
          <span v-else-if="step.status === 'running'" class="material-symbols-outlined step-rotate-icon">autorenew</span>
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
          <div v-if="currentAgentMessage && step.status === 'running'" class="step-agent-message">
            <span class="material-symbols-outlined">chat</span>
            <span>{{ currentAgentMessage }}</span>
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
            <span class="material-symbols-outlined">{{ getRecommendationIcon(quickJudgment.recommendation) }}</span>
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
      <div class="completion-icon">
        <span class="material-symbols-outlined">task_alt</span>
      </div>
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
import { API_BASE } from '@/config/api';
import { appendTokenToUrl, getAuthHeaders } from '@/services/authHeaders';

const { t, locale: currentLang } = useLanguage();
const { info, success, error: showError } = useToast();

// API base for export requests
const exportLoading = ref(false);

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

const emit = defineEmits(['analysis-complete', 'cancel', 'upgrade']);

const analysisStatus = ref('running');
const workflow = ref([]);
const currentStepIndex = ref(0);
const overallProgress = ref(0); // Initialize to 0, will be updated by workflow progress
const currentAgentMessage = ref('');
const quickJudgment = ref(null);
const elapsedTime = ref('0m0s');
const connectionState = ref('connected'); // connected, reconnecting, error, disconnected

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

function applyStatusSnapshot(statusPayload) {
  if (!statusPayload || typeof statusPayload !== 'object') return;

  if (Array.isArray(statusPayload.workflow) && statusPayload.workflow.length > 0) {
    workflow.value = statusPayload.workflow.map((s) => ({
      id: s.id,
      name: s.name,
      agent: s.agent,
      status: s.status || 'pending',
      progress: typeof s.progress === 'number' ? s.progress : 0,
      result: s.result,
      error: s.error
    }));
  }

  if (typeof statusPayload.progress === 'number') {
    overallProgress.value = Math.max(0, Math.min(100, statusPayload.progress));
  }

  if (statusPayload.quick_judgment) {
    quickJudgment.value = statusPayload.quick_judgment;
  }

  if (statusPayload.status === 'completed') {
    analysisStatus.value = 'completed';
    overallProgress.value = 100;
  } else if (statusPayload.status === 'error' || statusPayload.error) {
    analysisStatus.value = 'error';
  }
}

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

  // 监听连接状态变化
  analysisServiceV2.onStateChange(handleConnectionStateChange);

  // If this component is mounted via session recovery/new page, resume WS subscription.
  if (props.sessionId && !analysisServiceV2.isConnected()) {
    analysisServiceV2.resumeSession(props.sessionId).catch(async (resumeError) => {
      console.warn('[AnalysisProgress] Resume WS failed, fallback to status snapshot:', resumeError);
      try {
        const statusSnapshot = await analysisServiceV2.getStatus(props.sessionId);
        applyStatusSnapshot(statusSnapshot);
      } catch (statusError) {
        console.error('[AnalysisProgress] Failed to load status snapshot:', statusError);
      }
    });
  }

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
  analysisServiceV2.offStateChange(handleConnectionStateChange);

  if (elapsedTimer) {
    clearInterval(elapsedTimer);
  }

  // Detach live WS when leaving page. Backend task keeps running and can be resumed.
  analysisServiceV2.disconnect();
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
  overallProgress.value = 100; // Analysis complete, show 100%
}

function handleAnalysisComplete(message) {
  console.log('[Progress] Analysis complete:', message);
  analysisStatus.value = 'completed';
  overallProgress.value = 100; // Analysis complete, show 100%
  emit('analysis-complete', message.data);
}

function handleError(message) {
  console.error('[Progress] Error:', message);
  analysisStatus.value = 'error';
  // 显示用户友好的错误提示
  const errorMsg = message.data?.error || message.message || t('analysisWizard.unknownError');
  info(`${t('analysisWizard.analysisError')}: ${errorMsg}`);
}

function handleConnectionStateChange(newState, oldState) {
  console.log('[Progress] Connection state changed:', oldState, '→', newState);
  connectionState.value = newState;

  // 根据连接状态显示不同的提示
  if (newState === 'reconnecting') {
    info(t('analysisWizard.reconnecting'));
  } else if (newState === 'error') {
    info(t('analysisWizard.connectionLost'));
  } else if (newState === 'connected' && oldState === 'reconnecting') {
    info(t('analysisWizard.connectionRestored'));
  }
}

function updateOverallProgress() {
  const totalSteps = workflow.value.length;
  if (totalSteps === 0) {
    overallProgress.value = 0;
    return;
  }

  // Calculate progress: completed steps = 100%, running step = 50%
  const completedSteps = workflow.value.filter(s => s.status === 'success').length;
  const runningSteps = workflow.value.filter(s => s.status === 'running').length;

  // Each completed step contributes full weight, each running step contributes half
  const progress = ((completedSteps + runningSteps * 0.5) / totalSteps) * 100;
  overallProgress.value = Math.min(Math.round(progress), 99); // Cap at 99% until fully complete
}

function updateElapsedTime() {
  const elapsed = Math.floor((Date.now() - startTime) / 1000);
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  elapsedTime.value = `${minutes}${t('analysisWizard.minutes')}${seconds}${t('analysisWizard.seconds')}`;
}

function getRecommendationIcon(recommendation) {
  const iconMap = {
    'BUY': 'trending_up',
    'PASS': 'block',
    'FURTHER_DD': 'manage_search',
    'INVEST': 'paid'
  };
  return iconMap[recommendation] || 'analytics';
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
  console.log('[Progress] Props for upgrade:', {
    scenario: props.scenario,
    projectName: props.projectName,
    targetData: props.targetData,
    depth: props.depth
  });

  // Emit upgrade event with all necessary data
  emit('upgrade', {
    scenario: props.scenario,
    projectName: props.projectName || targetName.value,
    target: props.targetData,
    originalConfig: {
      depth: props.depth,
      // Preserve other config options if needed
    }
  });
}

async function exportReport(format = 'pdf') {
  console.log('[Progress] Export report as', format, 'for session:', props.sessionId);

  if (!props.sessionId) {
    showError(t('analysisWizard.noSessionId') || 'No session ID available');
    return;
  }

  exportLoading.value = true;

  try {
    // Get language setting
    const language = currentLang?.value || 'zh';
    const langParam = language.startsWith('zh') ? 'zh' : 'en';

    // Call export API
    const url = `${API_BASE}/api/reports/${props.sessionId}/export/${format}?language=${langParam}`;
    console.log(`[Progress] Exporting report as ${format}, language=${langParam}`);

    const response = await fetch(appendTokenToUrl(url), {
      headers: {
        ...getAuthHeaders()
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to export report: ${response.statusText}`);
    }

    // Get filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `report_${props.sessionId}.${format === 'word' ? 'docx' : format === 'excel' ? 'xlsx' : 'pdf'}`;

    if (contentDisposition) {
      const matches = /filename="([^"]+)"/.exec(contentDisposition);
      if (matches && matches[1]) {
        filename = matches[1];
      }
    }

    // Download file
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(downloadUrl);
    document.body.removeChild(a);

    console.log(`[Progress] Successfully exported report as ${format}: ${filename}`);
    success(t('analysisWizard.exportSuccess') || `Report exported as ${format.toUpperCase()}`);

  } catch (err) {
    console.error('[Progress] Failed to export report:', err);
    showError(`${t('analysisWizard.exportFailed') || 'Export failed'}: ${err.message}`);
  } finally {
    exportLoading.value = false;
  }
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
  color: #e5e7eb;
}

.connection-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 12px;
  margin-bottom: 1rem;
  font-size: 0.92rem;
  font-weight: 600;
}

.connection-banner .material-symbols-outlined {
  font-size: 1.15rem;
  flex-shrink: 0;
}

.connection-banner.warning {
  background: rgba(245, 158, 11, 0.14);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #fbbf24;
}

.connection-banner.warning .material-symbols-outlined {
  animation: spin360 1s linear infinite;
}

.connection-banner.error {
  background: rgba(239, 68, 68, 0.14);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #f87171;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header-left {
  min-width: 0;
}

.header-left h1 {
  font-size: 1.65rem;
  line-height: 1.2;
  font-weight: 700;
  color: #f8fafc;
  margin: 0;
  overflow-wrap: anywhere;
}

.btn-cancel {
  padding: 0.62rem 1.25rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 10px;
  color: #d1d5db;
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-cancel:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.28);
}

.overall-progress {
  margin-bottom: 1.75rem;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.7rem;
}

.progress-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: #d1d5db;
}

.progress-percentage {
  font-size: 1.2rem;
  font-weight: 700;
  color: #38bdf8;
}

.progress-bar {
  height: 10px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #38bdf8, #0ea5e9);
  transition: width 0.45s ease;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  margin-bottom: 1.75rem;
}

.stat-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 1.1rem 1.2rem;
  min-width: 0;
}

.stat-label {
  font-size: 0.8rem;
  color: #9ca3af;
  margin-bottom: 0.45rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-value {
  font-size: 1.35rem;
  font-weight: 700;
  color: #f3f4f6;
  overflow-wrap: anywhere;
}

.content-grid {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 1rem;
  margin-bottom: 1.75rem;
}

.agent-status-panel,
.workflow-steps-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 1.2rem;
  min-width: 0;
}

.workflow-steps-panel {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.panel-title {
  font-size: 1.02rem;
  font-weight: 700;
  color: #f3f4f6;
  margin-bottom: 1rem;
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.82rem;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  transition: all 0.2s ease;
}

.agent-item.running {
  border-color: rgba(245, 158, 11, 0.45);
  background: rgba(245, 158, 11, 0.08);
}

.agent-item.completed {
  border-color: rgba(16, 185, 129, 0.42);
  background: rgba(16, 185, 129, 0.08);
}

.agent-icon {
  width: 44px;
  height: 44px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.agent-icon .material-symbols-outlined {
  font-size: 1.4rem;
  color: #fff;
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 0.9rem;
  font-weight: 700;
  color: #f3f4f6;
  margin-bottom: 0.15rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-message-text {
  font-size: 0.82rem;
  color: #9ca3af;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-status-icon {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.status-completed {
  color: #10b981;
  font-size: 1.35rem;
}

.status-queued {
  color: #6b7280;
  font-size: 1.3rem;
}

.loading-ring {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-top-color: #f59e0b;
  animation: spin360 0.9s linear infinite;
}

.step-item {
  display: flex;
  gap: 0.85rem;
  padding: 0.92rem;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  transition: all 0.25s ease;
}

.step-item.running {
  border-color: rgba(56, 189, 248, 0.48);
  background: rgba(56, 189, 248, 0.08);
}

.step-item.success {
  border-color: rgba(16, 185, 129, 0.45);
}

.step-item.error {
  border-color: rgba(239, 68, 68, 0.45);
}

.step-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: #d1d5db;
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-icon .material-symbols-outlined {
  font-size: 1.2rem;
}

.step-number {
  font-size: 0.96rem;
  font-weight: 700;
}

.step-item.running .step-icon {
  background: #0ea5e9;
  color: #fff;
}

.step-item.success .step-icon {
  background: #10b981;
  color: #fff;
}

.step-item.error .step-icon {
  background: #ef4444;
  color: #fff;
}

.step-rotate-icon {
  animation: spin360 1s linear infinite;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.45rem 0.75rem;
  margin-bottom: 0.42rem;
}

.step-header h4 {
  font-size: 0.97rem;
  font-weight: 700;
  color: #f3f4f6;
  margin: 0;
  overflow-wrap: anywhere;
}

.agent-tag {
  padding: 0.18rem 0.62rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  color: #93c5fd;
  background: rgba(59, 130, 246, 0.16);
  border: 1px solid rgba(59, 130, 246, 0.32);
}

.step-progress {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.progress-bar-mini {
  flex: 1;
  height: 6px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  overflow: hidden;
}

.progress-text {
  flex-shrink: 0;
  font-size: 0.78rem;
  font-weight: 700;
  color: #7dd3fc;
}

.step-agent-message {
  margin-top: 0.5rem;
  padding: 0.45rem 0.62rem;
  border-radius: 8px;
  font-size: 0.86rem;
  color: #bfdbfe;
  background: rgba(59, 130, 246, 0.14);
  border: 1px solid rgba(59, 130, 246, 0.32);
  display: flex;
  align-items: flex-start;
  gap: 0.36rem;
}

.step-agent-message .material-symbols-outlined {
  font-size: 1rem;
  margin-top: 0.02rem;
  flex-shrink: 0;
}

.step-agent-message span:last-child {
  overflow-wrap: anywhere;
}

.step-error {
  margin-top: 0.5rem;
  padding: 0.45rem 0.62rem;
  border-radius: 8px;
  font-size: 0.86rem;
  color: #fecaca;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.28);
  overflow-wrap: anywhere;
}

.quick-judgment-result {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 1.2rem;
  margin-top: 1.6rem;
}

.judgment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.8rem;
  margin-bottom: 1rem;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.judgment-header h3 {
  font-size: 1.18rem;
  font-weight: 700;
  color: #f3f4f6;
  margin: 0;
}

.judgment-time {
  font-size: 0.82rem;
  color: #9ca3af;
}

.judgment-main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.8rem;
  margin-bottom: 1rem;
}

.recommendation-card {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.9rem 1rem;
  border-radius: 12px;
}

.recommendation-card.buy,
.recommendation-card.invest {
  background: rgba(16, 185, 129, 0.11);
  border: 1px solid rgba(16, 185, 129, 0.36);
}

.recommendation-card.pass {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.33);
}

.recommendation-card.further_dd {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.33);
}

.recommendation-icon {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.12);
  color: #f8fafc;
}

.recommendation-icon .material-symbols-outlined {
  font-size: 1.3rem;
}

.recommendation-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
}

.recommendation-label {
  font-size: 0.72rem;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.recommendation-text {
  font-size: 1.1rem;
  font-weight: 700;
  color: #f3f4f6;
  overflow-wrap: anywhere;
}

.score-card {
  min-width: 110px;
  padding: 0.8rem 1rem;
  border-radius: 12px;
  background: rgba(56, 189, 248, 0.12);
  border: 1px solid rgba(56, 189, 248, 0.32);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-card .score-value {
  font-size: 2.2rem;
  font-weight: 800;
  line-height: 1;
  color: #67e8f9;
}

.score-card .score-unit {
  font-size: 0.95rem;
  color: #a5f3fc;
}

.score-card .score-label {
  margin-top: 0.2rem;
  font-size: 0.72rem;
  color: #9ca3af;
}

.verdict-section,
.next-steps-section {
  margin-bottom: 0.8rem;
  padding: 0.9rem 1rem;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.section-header {
  font-size: 0.72rem;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.4rem;
}

.verdict-text {
  color: #e5e7eb;
  line-height: 1.55;
  margin: 0;
  font-size: 0.92rem;
}

.key-points {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
  margin-bottom: 0.8rem;
}

.points-group {
  padding: 0.86rem 0.95rem;
  border-radius: 10px;
}

.points-group.positive {
  background: rgba(16, 185, 129, 0.09);
  border-left: 3px solid #10b981;
}

.points-group.concern {
  background: rgba(245, 158, 11, 0.09);
  border-left: 3px solid #f59e0b;
}

.points-label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.45rem;
}

.points-group.positive .points-label {
  color: #34d399;
}

.points-group.concern .points-label {
  color: #fbbf24;
}

.points-group ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.points-group li {
  color: #e5e7eb;
  font-size: 0.84rem;
  line-height: 1.4;
  padding: 0.2rem 0;
  overflow-wrap: anywhere;
}

.action-highlight {
  font-size: 0.98rem;
  font-weight: 700;
  color: #7dd3fc;
  margin-bottom: 0.6rem;
  overflow-wrap: anywhere;
}

.focus-areas {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.46rem;
}

.focus-areas li {
  padding: 0.32rem 0.65rem;
  border-radius: 999px;
  font-size: 0.78rem;
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.quick-actions {
  margin-top: 1rem;
  padding-top: 0.9rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.btn-upgrade,
.btn-export {
  min-height: 38px;
  padding: 0.56rem 1rem;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-upgrade {
  border: none;
  color: #fff;
  background: linear-gradient(135deg, #0ea5e9, #0284c7);
}

.btn-upgrade:hover {
  filter: brightness(1.08);
}

.btn-export {
  color: #e5e7eb;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.btn-export:hover {
  background: rgba(255, 255, 255, 0.12);
}

.completion-message {
  text-align: center;
  padding: 2.3rem 1rem 1rem;
}

.completion-icon {
  width: 74px;
  height: 74px;
  margin: 0 auto 0.9rem;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(16, 185, 129, 0.14);
  border: 1px solid rgba(16, 185, 129, 0.45);
  color: #34d399;
}

.completion-icon .material-symbols-outlined {
  font-size: 2.2rem;
}

.completion-message h3 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #f8fafc;
  margin-bottom: 0.35rem;
}

.completion-message p {
  color: #94a3b8;
  margin-bottom: 1.2rem;
}

.btn-view-report {
  min-height: 42px;
  padding: 0.75rem 1.3rem;
  border-radius: 10px;
  border: none;
  color: #fff;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  background: linear-gradient(135deg, #0ea5e9, #0284c7);
  transition: filter 0.2s ease;
}

.btn-view-report:hover {
  filter: brightness(1.08);
}

@keyframes spin360 {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 880px) {
  .stats-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-right {
    display: flex;
    justify-content: flex-end;
  }

  .judgment-main {
    grid-template-columns: 1fr;
  }

  .score-card {
    width: 100%;
    min-width: 0;
    flex-direction: row;
    gap: 0.5rem;
  }

  .score-card .score-label {
    margin-top: 0;
  }
}

@media (max-width: 640px) {
  .stats-row {
    grid-template-columns: 1fr;
  }

  .analysis-progress {
    font-size: 0.95rem;
  }

  .header-left h1 {
    font-size: 1.35rem;
  }

  .agent-status-panel,
  .workflow-steps-panel,
  .quick-judgment-result {
    padding: 0.95rem;
    border-radius: 14px;
  }

  .key-points {
    grid-template-columns: 1fr;
  }

  .step-item {
    padding: 0.78rem;
    gap: 0.68rem;
  }

  .step-icon {
    width: 34px;
    height: 34px;
  }

  .step-icon .material-symbols-outlined {
    font-size: 1.05rem;
  }
}
</style>
