<template>
  <div class="flex h-full gap-6">
    <!-- Back Button -->
    <button
      @click="$emit('back')"
      class="absolute top-4 left-4 z-10 px-4 py-2 rounded-lg bg-surface border border-border-color text-text-primary hover:bg-background-dark transition-colors flex items-center gap-2"
    >
      <span class="material-symbols-outlined">arrow_back</span>
      {{ t('common.back') }}
    </button>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col bg-surface border border-border-color rounded-lg overflow-hidden mt-12">
      <!-- Header -->
      <div class="px-6 py-4 border-b border-border-color bg-background-dark">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-xl font-bold text-text-primary">{{ projectName }}</h2>
            <p class="text-sm text-text-secondary mt-1">
              {{ analysisType }} • {{ t('agentChat.started') }} {{ startTime }}
            </p>
          </div>
          <div class="flex items-center gap-3">
            <span
              :class="[
                'text-sm px-3 py-1 rounded-full font-semibold',
                analysisStatus === 'completed' ? 'bg-accent-green/20 text-accent-green' :
                analysisStatus === 'error' ? 'bg-accent-red/20 text-accent-red' :
                'bg-accent-yellow/20 text-accent-yellow'
              ]"
            >
              {{ analysisStatusText }}
            </span>
          </div>
        </div>
      </div>

      <!-- Messages/Steps Container -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-6 space-y-4">
        <!-- Reconnecting Banner -->
        <div v-if="isReconnecting" class="flex justify-center sticky top-0 z-10">
          <div class="px-6 py-3 rounded-lg bg-accent-yellow/20 border border-accent-yellow text-accent-yellow font-semibold flex items-center gap-2 animate-pulse">
            <span class="material-symbols-outlined animate-spin">sync</span>
            正在重新连接服务器...
          </div>
        </div>

        <!-- System Start Message -->
        <div class="flex justify-center">
          <div class="px-4 py-2 rounded-full bg-surface border border-border-color text-xs text-text-secondary">
            <span class="material-symbols-outlined text-xs align-middle mr-1">info</span>
            {{ t('agentChat.analysisProgress') }}...
          </div>
        </div>

        <!-- DD Analysis Steps -->
        <div v-for="step in analysisSteps" :key="step.id" class="space-y-2">
          <!-- Step Header -->
          <div class="flex items-center gap-3 p-4 rounded-lg bg-background-dark border border-border-color">
            <div
              :class="[
                'w-8 h-8 rounded-full flex items-center justify-center',
                step.status === 'success' ? 'bg-accent-green/20' :
                step.status === 'error' ? 'bg-accent-red/20' :
                step.status === 'running' ? 'bg-primary/20' :
                step.status === 'skipped' ? 'bg-text-secondary/10' :
                'bg-surface-light'
              ]"
            >
              <span
                :class="[
                  'material-symbols-outlined text-lg',
                  step.status === 'success' ? 'text-accent-green' :
                  step.status === 'error' ? 'text-accent-red' :
                  step.status === 'running' ? 'text-primary animate-spin' :
                  step.status === 'skipped' ? 'text-text-secondary' :
                  'text-text-secondary'
                ]"
              >
                {{
                  step.status === 'success' ? 'check_circle' :
                  step.status === 'error' ? 'error' :
                  step.status === 'running' ? 'progress_activity' :
                  step.status === 'skipped' ? 'block' :
                  'radio_button_unchecked'
                }}
              </span>
            </div>
            <div class="flex-1">
              <h4 :class="[
                'font-semibold',
                step.status === 'skipped' ? 'text-text-secondary line-through' : 'text-text-primary'
              ]">{{ step.title }}</h4>
              <p v-if="step.status === 'running'" class="text-xs text-text-secondary mt-1">
                {{ t('common.loading') }}
              </p>
              <p v-if="step.status === 'skipped'" class="text-xs text-text-secondary mt-1">
                已跳过
              </p>
            </div>
          </div>

          <!-- Step Result -->
          <div v-if="step.result" class="ml-11 p-4 rounded-lg bg-surface border border-border-color">
            <p class="text-sm text-text-primary whitespace-pre-wrap">{{ step.result }}</p>
          </div>

          <!-- HITL Options (if any) -->
          <div v-if="step.options && step.options.length > 0" class="ml-11 space-y-2">
            <p class="text-sm font-semibold text-text-primary mb-2">请选择：</p>
            <button
              v-for="(option, index) in step.options"
              :key="index"
              @click="selectOption(step, option)"
              class="w-full p-3 rounded-lg bg-surface border border-border-color hover:border-primary transition-colors text-left"
            >
              <p class="font-semibold text-text-primary">{{ option.ticker || option.name }}</p>
              <p class="text-xs text-text-secondary mt-1">{{ option.company_name || option.description }}</p>
            </button>
          </div>
        </div>

        <!-- HITL Review Section -->
        <div v-if="analysisStatus === 'hitl_review' && preliminaryReport" class="space-y-4">
          <!-- HITL Header -->
          <div class="flex justify-center">
            <div class="px-6 py-3 rounded-lg bg-accent-yellow/20 text-accent-yellow font-semibold flex items-center gap-2">
              <span class="material-symbols-outlined">pending</span>
              初步分析完成，请审核并回答关键问题
            </div>
          </div>

          <!-- Preliminary Report Summary -->
          <div class="p-6 rounded-lg bg-background-dark border border-border-color">
            <h3 class="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">description</span>
              初步投资备忘录
            </h3>

            <!-- Company Info -->
            <div v-if="preliminaryReport.company_info" class="mb-4 p-4 rounded-lg bg-surface">
              <h4 class="font-semibold text-text-primary mb-2">公司信息</h4>
              <div class="text-sm text-text-secondary space-y-1">
                <p><strong>公司名称:</strong> {{ preliminaryReport.company_info.name || companyName }}</p>
                <p v-if="preliminaryReport.company_info.industry"><strong>行业:</strong> {{ preliminaryReport.company_info.industry }}</p>
                <p v-if="preliminaryReport.company_info.stage"><strong>阶段:</strong> {{ preliminaryReport.company_info.stage }}</p>
              </div>
            </div>

            <!-- Team Analysis -->
            <div v-if="preliminaryReport.team_section" class="mb-4 p-4 rounded-lg bg-surface">
              <h4 class="font-semibold text-text-primary mb-2">团队评估</h4>
              <p class="text-sm text-text-secondary">{{ preliminaryReport.team_section.summary || '团队分析已完成' }}</p>
            </div>

            <!-- Market Analysis -->
            <div v-if="preliminaryReport.market_section" class="mb-4 p-4 rounded-lg bg-surface">
              <h4 class="font-semibold text-text-primary mb-2">市场分析</h4>
              <p class="text-sm text-text-secondary">{{ preliminaryReport.market_section.summary || '市场分析已完成' }}</p>
            </div>
          </div>

          <!-- DD Questions -->
          <div v-if="preliminaryReport.dd_questions && preliminaryReport.dd_questions.length > 0" class="p-6 rounded-lg bg-background-dark border border-primary/30">
            <h3 class="text-lg font-bold text-text-primary mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">help</span>
              关键尽职调查问题 ({{ preliminaryReport.dd_questions.length }})
            </h3>

            <div class="space-y-4">
              <div
                v-for="(question, index) in preliminaryReport.dd_questions"
                :key="index"
                class="p-4 rounded-lg bg-surface border border-border-color"
              >
                <div class="flex items-start gap-3 mb-3">
                  <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <span class="text-primary font-bold text-sm">{{ index + 1 }}</span>
                  </div>
                  <div class="flex-1">
                    <p class="font-semibold text-text-primary mb-1">{{ question.question || question }}</p>
                    <p v-if="question.category" class="text-xs text-text-secondary">
                      分类: {{ question.category }}
                    </p>
                  </div>
                </div>

                <!-- Answer Input -->
                <textarea
                  v-model="question.answer"
                  rows="3"
                  placeholder="请输入您的答案或备注..."
                  class="w-full px-4 py-2 rounded-lg bg-background-dark border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors resize-none"
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <!-- Analysis Complete Message -->
        <div v-if="analysisStatus === 'completed'" class="flex justify-center">
          <div class="px-6 py-3 rounded-lg bg-accent-green/20 text-accent-green font-semibold flex items-center gap-2">
            <span class="material-symbols-outlined">check_circle</span>
            分析已完成！
          </div>
        </div>

        <!-- Error Message -->
        <div v-if="analysisStatus === 'error'" class="flex justify-center">
          <div class="px-6 py-3 rounded-lg bg-accent-red/20 text-accent-red font-semibold flex items-center gap-2">
            <span class="material-symbols-outlined">error</span>
            {{ errorMessage }}
          </div>
        </div>
      </div>

      <!-- Save Report Button (when HITL review or completed) -->
      <div v-if="analysisStatus === 'hitl_review' || analysisStatus === 'completed'" class="px-6 py-4 border-t border-border-color bg-background-dark">
        <button
          @click="saveReport"
          :disabled="reportSaved"
          :class="[
            'w-full px-6 py-3 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2',
            reportSaved
              ? 'bg-surface text-text-secondary cursor-not-allowed'
              : 'bg-primary text-background-dark hover:bg-primary/90'
          ]"
        >
          <span class="material-symbols-outlined">{{ reportSaved ? 'check' : 'save' }}</span>
          {{ reportSaved ? '报告已保存' : '保存报告' }}
        </button>
      </div>
    </div>

    <!-- Right Sidebar: Progress Overview -->
    <div class="w-80 flex-shrink-0 space-y-6 mt-12">
      <!-- Overall Progress -->
      <div class="bg-surface border border-border-color rounded-lg p-4">
        <h3 class="text-lg font-bold text-text-primary mb-4">{{ t('agentChat.analysisProgress') }}</h3>
        <div class="space-y-4">
          <div>
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-semibold text-text-primary">{{ t('agentChat.overallProgress') }}</span>
              <span class="text-sm font-semibold text-primary">{{ overallProgress }}%</span>
            </div>
            <div class="w-full h-2 bg-background-dark rounded-full overflow-hidden">
              <div
                class="h-full bg-primary transition-all duration-300"
                :style="{ width: overallProgress + '%' }"
              ></div>
            </div>
          </div>

          <!-- Step Summary -->
          <div class="text-xs text-text-secondary">
            {{ completedSteps }} / {{ totalSteps }} {{ t('agentChat.taskStatus.completed') }}
          </div>
        </div>
      </div>

      <!-- Configuration Info -->
      <div class="bg-surface border border-border-color rounded-lg p-4">
        <h3 class="text-lg font-bold text-text-primary mb-4">配置信息</h3>
        <div class="space-y-2 text-sm">
          <div>
            <span class="text-text-secondary">公司:</span>
            <span class="text-text-primary font-semibold ml-2">{{ companyName }}</span>
          </div>
          <div>
            <span class="text-text-secondary">分析类型:</span>
            <span class="text-text-primary ml-2">{{ analysisType }}</span>
          </div>
          <div v-if="selectedAgentsCount > 0">
            <span class="text-text-secondary">选中智能体:</span>
            <span class="text-text-primary ml-2">{{ selectedAgentsCount }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useLanguage } from '../composables/useLanguage';
import { DDAnalysisService } from '../services/ddAnalysisService';

const { t } = useLanguage();
const props = defineProps({
  analysisConfig: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['back']);

// State
const ddService = new DDAnalysisService();
const messagesContainer = ref(null);
const analysisSteps = ref([]);
const analysisStatus = ref('in_progress'); // 'in_progress', 'hitl_review', 'completed', 'error', 'reconnecting'
const errorMessage = ref('');
const sessionId = ref('');
const reportSaved = ref(false);
const preliminaryReport = ref(null); // Store the preliminary IM for HITL review
const isReconnecting = ref(false); // Track reconnection state

// Computed
const projectName = computed(() => props.analysisConfig?.projectName || 'Investment Analysis');
const companyName = computed(() => props.analysisConfig?.company || 'Unknown Company');
const analysisType = computed(() => {
  const typeMap = {
    'due-diligence': '尽职调查',
    'market-analysis': '市场分析',
    'financial-review': '财务审查',
    'competitive-analysis': '竞争分析'
  };
  return typeMap[props.analysisConfig?.analysisType] || '投资分析';
});

const startTime = computed(() => new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));

const analysisStatusText = computed(() => {
  if (analysisStatus.value === 'completed') return t('agentChat.status.completed');
  if (analysisStatus.value === 'error') return '错误';
  return t('agentChat.status.inProgress');
});

const totalSteps = computed(() => analysisSteps.value.length);
const completedSteps = computed(() => analysisSteps.value.filter(s => s.status === 'success').length);
const overallProgress = computed(() => {
  if (totalSteps.value === 0) return 0;
  return Math.round((completedSteps.value / totalSteps.value) * 100);
});

const selectedAgentsCount = computed(() => props.analysisConfig?.selectedAgents?.length || 0);

// Methods
const scrollToBottom = async () => {
  await nextTick();
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const handleDDMessage = (data) => {
  console.log('[AgentChat] Received DD message:', data);

  // Store session ID
  if (data.session_id) {
    sessionId.value = data.session_id;
  }

  // Handle agent events (ignore for now, focus on step updates)
  if (data.type === 'agent_event') {
    console.log('[AgentChat] Agent event:', data.event);
    return;
  }

  // Handle DD analysis progress updates
  if (data.status === 'in_progress') {
    // Update all steps if provided
    if (data.all_steps && Array.isArray(data.all_steps)) {
      analysisSteps.value = data.all_steps.map(step => ({
        id: step.id,
        title: step.title,
        status: step.status || 'pending',
        result: step.result || null,
        options: step.options || null
      }));
    }

    // Highlight current step
    if (data.current_step) {
      const currentStepIndex = analysisSteps.value.findIndex(s => s.id === data.current_step.id);
      if (currentStepIndex >= 0) {
        analysisSteps.value[currentStepIndex] = {
          ...analysisSteps.value[currentStepIndex],
          ...data.current_step,
          status: data.current_step.status || 'running'
        };
      }
    }

    scrollToBottom();
  } else if (data.status === 'hitl_required') {
    // Human-in-the-loop required - preliminary report ready for review
    console.log('[AgentChat] HITL required, preliminary report:', data.preliminary_im);

    // Store the preliminary report
    preliminaryReport.value = data.preliminary_im;

    // Update analysis status
    analysisStatus.value = 'hitl_review';

    // Update current step to paused
    if (data.current_step) {
      const step = data.current_step;
      const existingIndex = analysisSteps.value.findIndex(s => s.id === step.id);

      if (existingIndex >= 0) {
        analysisSteps.value[existingIndex] = {
          ...step,
          status: 'paused',
          options: step.options
        };
      }
    }

    scrollToBottom();
  } else if (data.status === 'hitl_follow_up_required') {
    // Analysis completed with preliminary report and questions
    analysisStatus.value = 'completed';

    // Add completion step
    analysisSteps.value.push({
      id: 999,
      title: '分析完成',
      status: 'success',
      result: '初步分析已完成，生成了初步报告和关键问题。'
    });

    scrollToBottom();
  } else if (data.status === 'completed') {
    analysisStatus.value = 'completed';

    // Mark all steps as completed
    analysisSteps.value = analysisSteps.value.map(step => ({
      ...step,
      status: step.status === 'running' ? 'success' : step.status
    }));

    scrollToBottom();
  } else if (data.status === 'error') {
    analysisStatus.value = 'error';
    errorMessage.value = data.message || '分析过程中出现错误';
    scrollToBottom();
  }
};

const selectOption = (step, option) => {
  console.log('[AgentChat] User selected option:', option);

  // Send selection to backend
  if (ddService.ws && ddService.ws.readyState === WebSocket.OPEN) {
    ddService.ws.send(JSON.stringify({
      selected_ticker: option.ticker
    }));

    // Update step status
    step.status = 'running';
    step.options = null;
    scrollToBottom();
  }
};

const saveReport = async () => {
  try {
    const reportData = {
      session_id: sessionId.value,
      project_name: projectName.value,
      company_name: companyName.value,
      analysis_type: analysisType.value,
      preliminary_im: preliminaryReport.value, // Include the preliminary IM
      steps: analysisSteps.value,
      created_at: new Date().toISOString(),
      status: analysisStatus.value === 'hitl_review' ? 'pending_review' : 'completed'
    };

    console.log('[AgentChat] Saving report:', reportData);

    // Call backend API to save report
    const response = await fetch('http://localhost:8000/api/reports', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(reportData)
    });

    if (!response.ok) {
      throw new Error(`Failed to save report: ${response.statusText}`);
    }

    const result = await response.json();
    console.log('[AgentChat] Report saved successfully:', result);

    // Mark as saved
    reportSaved.value = true;

    // Navigate back to reports view after a delay
    setTimeout(() => {
      emit('back');
    }, 1500);
  } catch (error) {
    console.error('[AgentChat] Failed to save report:', error);
    alert('保存报告失败: ' + error.message);
  }
};

// Lifecycle
onMounted(async () => {
  console.log('[AgentChat] Starting DD analysis with config:', props.analysisConfig);

  // Setup message handler
  ddService.onMessage(handleDDMessage);

  // Setup error handler
  ddService.onError((error) => {
    console.error('[AgentChat] WebSocket error:', error);
    analysisStatus.value = 'error';
    errorMessage.value = '连接错误';
  });

  // Setup close handler
  ddService.onClose((event) => {
    console.log('[AgentChat] WebSocket closed:', event);

    // If not a normal closure and analysis not completed, show reconnecting status
    if (event.code !== 1000 && analysisStatus.value !== 'completed' && analysisStatus.value !== 'hitl_review') {
      isReconnecting.value = true;
      console.log('[AgentChat] Connection lost, attempting to reconnect...');
    }
  });

  // Listen for successful reconnections
  ddService.onMessage((data) => {
    if (isReconnecting.value && data) {
      isReconnecting.value = false;
      console.log('[AgentChat] Reconnected successfully');
    }
  });

  // Start analysis
  try {
    await ddService.startAnalysis(props.analysisConfig);
  } catch (error) {
    console.error('[AgentChat] Failed to start analysis:', error);
    analysisStatus.value = 'error';
    errorMessage.value = '启动分析失败: ' + error.message;
  }
});

onUnmounted(() => {
  ddService.close();
});
</script>
