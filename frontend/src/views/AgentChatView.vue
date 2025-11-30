<template>
  <div class="flex h-full gap-8 p-2">
    <!-- Back Button -->
    <button
      @click="$emit('back')"
      class="absolute top-6 left-6 z-50 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-text-primary transition-all duration-300 flex items-center gap-2 backdrop-blur-md hover:shadow-glow-sm"
    >
      <span class="material-symbols-outlined">arrow_back</span>
      {{ t('common.back') }}
    </button>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col glass-panel rounded-2xl overflow-hidden relative z-10">
      <!-- Header -->
      <div class="px-8 py-5 border-b border-white/10 bg-white/5 backdrop-blur-md">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-2xl font-display font-bold text-white tracking-tight pl-12">{{ projectName }}</h2>
            <p class="text-sm text-text-secondary mt-1 pl-12 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary text-sm">analytics</span>
              {{ analysisType }} 
              <span class="text-white/20">•</span> 
              <span class="material-symbols-outlined text-accent-violet text-sm">schedule</span>
              {{ t('agentChat.started') }} {{ startTime }}
            </p>
          </div>
          <div class="flex items-center gap-3">
            <span
              :class="[
                'text-xs px-3 py-1.5 rounded-full font-bold uppercase tracking-wider border shadow-[0_0_10px_rgba(0,0,0,0.2)]',
                analysisStatus === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                analysisStatus === 'error' ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' :
                'bg-amber-500/10 text-amber-400 border-amber-500/30'
              ]"
            >
              {{ analysisStatusText }}
            </span>
          </div>
        </div>
      </div>

      <!-- Messages/Steps Container -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-8 space-y-6 scroll-smooth">
        <!-- Reconnecting Banner -->
        <div v-if="isReconnecting" class="flex justify-center sticky top-0 z-20">
          <div class="px-6 py-3 rounded-xl bg-amber-500/20 border border-amber-500/50 text-amber-300 font-bold flex items-center gap-3 animate-pulse shadow-lg backdrop-blur-md">
            <span class="material-symbols-outlined animate-spin">sync</span>
            {{ t('roundtable.discussion.connecting') }}
          </div>
        </div>

        <!-- System Start Message -->
        <div class="flex justify-center my-4">
          <div class="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-text-secondary flex items-center gap-2">
            <span class="w-2 h-2 bg-primary rounded-full animate-ping"></span>
            {{ t('agentChat.analysisProgress') }}...
          </div>
        </div>

        <!-- DD Analysis Steps -->
        <div v-for="step in analysisSteps" :key="step.id" class="space-y-2 group animate-fade-in">
          <!-- Step Header -->
          <div
            :class="[
              'flex items-center gap-4 p-5 rounded-xl border transition-all duration-500 relative overflow-hidden',
              step.status === 'success' ? 'bg-emerald-500/5 border-emerald-500/20 hover:bg-emerald-500/10' :
              step.status === 'error' ? 'bg-rose-500/5 border-rose-500/20' :
              step.status === 'running' ? 'bg-primary/10 border-primary/30 shadow-[0_0_15px_rgba(56,189,248,0.15)]' :
              step.status === 'skipped' ? 'bg-white/5 border-white/5 opacity-50' :
              'bg-white/5 border-white/5 hover:bg-white/10'
            ]"
          >
             <!-- Active Indicator Line -->
             <div v-if="step.status === 'running'" class="absolute left-0 top-0 bottom-0 w-1 bg-primary shadow-[0_0_8px_rgba(56,189,248,0.8)]"></div>

            <div
              :class="[
                'w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-500 shadow-lg backdrop-blur-sm',
                step.status === 'success' ? 'bg-emerald-500/20 text-emerald-400' :
                step.status === 'error' ? 'bg-rose-500/20 text-rose-400' :
                step.status === 'running' ? 'bg-primary/20 text-primary scale-110' :
                step.status === 'skipped' ? 'bg-white/5 text-text-secondary' :
                'bg-white/5 text-text-secondary group-hover:bg-white/10 group-hover:text-white'
              ]"
            >
              <span
                :class="[
                  'material-symbols-outlined text-2xl',
                  step.status === 'running' ? 'animate-spin' : ''
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
              <div class="flex items-center justify-between">
                <h4 :class="[
                  'text-base font-bold tracking-wide',
                  step.status === 'skipped' ? 'text-text-secondary line-through' : 'text-white'
                ]">{{ step.title }}</h4>
                <span v-if="step.status === 'success'" class="text-xs text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-1 bg-emerald-500/10 px-2 py-1 rounded">
                  <span class="material-symbols-outlined text-sm">done</span>
                  {{ t('agentChat.taskStatus.completed') }}
                </span>
                <span v-else-if="step.status === 'running'" class="text-xs text-primary font-bold uppercase tracking-wider flex items-center gap-1 animate-pulse bg-primary/10 px-2 py-1 rounded">
                  <span class="material-symbols-outlined text-sm">autorenew</span>
                  {{ t('agentChat.taskStatus.inProgress') }}
                </span>
              </div>
              <p v-if="step.status === 'running'" class="text-xs text-primary/80 mt-1 font-medium">
                {{ t('sidebar.processing') }}
              </p>
              <p v-if="step.status === 'skipped'" class="text-xs text-text-secondary mt-1">
                Skipped
              </p>
            </div>
          </div>

          <!-- Step Result -->
          <div v-if="step.result" class="ml-16 p-5 rounded-xl bg-white/5 border border-white/10 text-text-primary/90 text-sm leading-relaxed shadow-inner">
            <p class="whitespace-pre-wrap font-mono text-xs md:text-sm">{{ step.result }}</p>
          </div>

          <!-- HITL Options (if any) -->
          <div v-if="step.options && step.options.length > 0" class="ml-16 space-y-3 animate-fade-in">
            <p class="text-sm font-bold text-primary mb-2 uppercase tracking-wider flex items-center gap-2">
               <span class="material-symbols-outlined text-base">touch_app</span>
               {{ t('hitl.actionRequired') }}
            </p>
            <button
              v-for="(option, index) in step.options"
              :key="index"
              @click="selectOption(step, option)"
              class="w-full p-4 rounded-xl bg-white/5 border border-white/10 hover:border-primary/50 hover:bg-primary/5 transition-all duration-300 text-left group relative overflow-hidden"
            >
              <div class="absolute left-0 top-0 bottom-0 w-1 bg-primary opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <p class="font-bold text-white group-hover:text-primary transition-colors">{{ option.ticker || option.name }}</p>
              <p class="text-xs text-text-secondary mt-1 group-hover:text-text-primary">{{ option.company_name || option.description }}</p>
            </button>
          </div>
        </div>

        <!-- HITL Review Section -->
        <div v-if="analysisStatus === 'hitl_review' && preliminaryReport" class="space-y-6 animate-fade-in">
          <!-- HITL Header -->
          <div class="flex justify-center">
            <div class="px-8 py-4 rounded-xl bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-300 font-bold flex items-center gap-3 shadow-lg">
              <span class="material-symbols-outlined">pending</span>
              {{ t('hitl.requiredTitle') }}
            </div>
          </div>

          <!-- Preliminary Report Summary -->
          <div class="p-8 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
            <h3 class="text-xl font-display font-bold text-white mb-6 flex items-center gap-3">
              <span class="material-symbols-outlined text-primary text-3xl">description</span>
              {{ t('report.preliminaryMemo') }}
            </h3>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <!-- Company Info -->
                <div v-if="preliminaryReport.company_info" class="p-5 rounded-xl bg-black/20 border border-white/5">
                  <h4 class="font-bold text-white mb-4 border-b border-white/10 pb-2">{{ t('report.companyInfo') }}</h4>
                  <div class="text-sm text-text-secondary space-y-2">
                    <p class="flex justify-between"><span>{{ t('report.name') }}:</span> <strong class="text-text-primary">{{ preliminaryReport.company_info.name || companyName }}</strong></p>
                    <p v-if="preliminaryReport.company_info.industry" class="flex justify-between"><span>{{ t('report.industry') }}:</span> <span class="text-text-primary">{{ preliminaryReport.company_info.industry }}</span></p>
                    <p v-if="preliminaryReport.company_info.stage" class="flex justify-between"><span>{{ t('report.stage') }}:</span> <span class="text-text-primary">{{ preliminaryReport.company_info.stage }}</span></p>
                  </div>
                </div>

                <!-- Team Analysis -->
                <div v-if="preliminaryReport.team_section" class="p-5 rounded-xl bg-black/20 border border-white/5">
                  <h4 class="font-bold text-white mb-4 border-b border-white/10 pb-2">{{ t('report.teamAssessment') }}</h4>
                  <p class="text-sm text-text-secondary leading-relaxed">{{ preliminaryReport.team_section.summary || t('report.teamAnalysisCompleted') }}</p>
                </div>
            </div>
            
            <!-- Market Analysis -->
            <div v-if="preliminaryReport.market_section" class="mt-6 p-5 rounded-xl bg-black/20 border border-white/5">
              <h4 class="font-bold text-white mb-4 border-b border-white/10 pb-2">{{ t('report.marketAnalysis') }}</h4>
              <p class="text-sm text-text-secondary leading-relaxed">{{ preliminaryReport.market_section.summary || t('report.marketAnalysisCompleted') }}</p>
            </div>
          </div>

          <!-- DD Questions -->
          <div v-if="preliminaryReport.dd_questions && preliminaryReport.dd_questions.length > 0" class="p-8 rounded-2xl bg-primary/5 border border-primary/20">
            <h3 class="text-xl font-display font-bold text-white mb-6 flex items-center gap-3">
              <span class="material-symbols-outlined text-primary text-3xl">help</span>
              {{ t('hitl.keyQuestions') }} ({{ preliminaryReport.dd_questions.length }})
            </h3>

            <div class="space-y-6">
              <div
                v-for="(question, index) in preliminaryReport.dd_questions"
                :key="index"
                class="p-6 rounded-xl bg-background-dark border border-white/10 hover:border-primary/30 transition-colors group"
              >
                <div class="flex items-start gap-4 mb-4">
                  <div class="w-8 h-8 rounded-lg bg-primary/20 text-primary font-bold flex items-center justify-center flex-shrink-0 border border-primary/20">
                    {{ index + 1 }}
                  </div>
                  <div class="flex-1">
                    <p class="font-bold text-white text-lg mb-2">{{ question.question || question }}</p>
                    <p v-if="question.category" class="text-xs font-bold uppercase tracking-wider text-text-secondary bg-white/5 inline-block px-2 py-1 rounded">
                      {{ question.category }}
                    </p>
                  </div>
                </div>

                <!-- Answer Input -->
                <div class="relative">
                    <textarea
                    v-model="question.answer"
                    rows="3"
                    :placeholder="t('hitl.answerPlaceholder')"
                    class="w-full px-5 py-3 rounded-xl bg-black/30 border border-white/10 text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all resize-none shadow-inner"
                    ></textarea>
                    <div class="absolute bottom-3 right-3">
                         <span class="material-symbols-outlined text-text-secondary opacity-50">edit_note</span>
                    </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Analysis Complete Message -->
        <div v-if="analysisStatus === 'completed'" class="flex justify-center animate-fade-in">
          <div class="px-8 py-4 rounded-xl bg-gradient-to-r from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 text-emerald-300 font-bold flex items-center gap-3 shadow-lg shadow-emerald-500/10">
            <span class="material-symbols-outlined text-2xl">check_circle</span>
            {{ t('report.savedSuccess') }}
          </div>
        </div>

        <!-- Error Message -->
        <div v-if="analysisStatus === 'error'" class="flex justify-center animate-fade-in">
          <div class="px-8 py-4 rounded-xl bg-rose-500/20 border border-rose-500/30 text-rose-300 font-bold flex items-center gap-3 shadow-lg">
            <span class="material-symbols-outlined">error</span>
            {{ errorMessage }}
          </div>
        </div>
      </div>

      <!-- Save Report Button (when HITL review or completed) -->
      <div v-if="analysisStatus === 'hitl_review' || analysisStatus === 'completed'" class="px-8 py-6 border-t border-white/10 bg-black/20 backdrop-blur-md">
        <button
          @click="saveReport"
          :disabled="reportSaved"
          :class="[
            'w-full px-6 py-4 rounded-xl font-bold text-lg transition-all duration-300 flex items-center justify-center gap-3 shadow-lg',
            reportSaved
              ? 'bg-white/10 text-text-secondary cursor-not-allowed'
              : 'bg-gradient-to-r from-primary to-primary-dark text-white hover:shadow-glow hover:-translate-y-1'
          ]"
        >
          <span class="material-symbols-outlined">{{ reportSaved ? 'check' : 'save' }}</span>
          {{ reportSaved ? t('report.savedButton') : t('report.saveButton') }}
        </button>
      </div>
    </div>

    <!-- Right Sidebar: Progress Overview -->
    <div class="w-80 flex-shrink-0 space-y-6 pt-14">
      <!-- Overall Progress -->
      <div class="glass-panel rounded-xl p-6">
        <h3 class="text-sm font-bold text-text-secondary uppercase tracking-wider mb-6 flex items-center gap-2">
             <span class="material-symbols-outlined">timelapse</span>
             {{ t('agentChat.analysisProgress') }}
        </h3>
        <div class="space-y-6">
          <div>
            <div class="flex items-center justify-between mb-3">
              <span class="text-sm font-bold text-white">{{ t('agentChat.overallProgress') }}</span>
              <span class="text-sm font-bold text-primary drop-shadow-md">{{ overallProgress }}%</span>
            </div>
            <div class="w-full h-2 bg-white/10 rounded-full overflow-hidden relative shadow-inner">
              <div
                class="h-full bg-gradient-to-r from-primary via-accent-cyan to-accent-violet transition-all duration-1000 ease-out relative overflow-hidden shadow-[0_0_10px_rgba(56,189,248,0.5)]"
                :style="{ width: overallProgress + '%' }"
              >
                <!-- Animated shimmer effect -->
                <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer"></div>
              </div>
            </div>
          </div>

          <!-- Step Summary with Icons -->
          <div class="grid grid-cols-2 gap-3">
            <div class="flex items-center gap-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
              <span class="material-symbols-outlined text-xl text-emerald-400">check_circle</span>
              <div>
                <div class="text-xl font-bold text-emerald-400 leading-none">{{ completedSteps }}</div>
                <div class="text-[10px] uppercase font-bold text-emerald-500/70 mt-1">{{ t('agentChat.taskStatus.completed') }}</div>
              </div>
            </div>
            <div class="flex items-center gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <span class="material-symbols-outlined text-xl text-amber-400">pending</span>
              <div>
                <div class="text-xl font-bold text-amber-400 leading-none">{{ pendingSteps }}</div>
                <div class="text-[10px] uppercase font-bold text-amber-500/70 mt-1">{{ t('agentChat.taskStatus.pending') }}</div>
              </div>
            </div>
          </div>

          <!-- Time Estimates -->
          <div class="space-y-3 pt-4 border-t border-white/10">
            <div class="flex items-center justify-between text-xs">
              <span class="text-text-secondary font-medium">{{ t('sidebar.elapsedTime') }}</span>
              <span class="font-mono font-bold text-white">{{ elapsedTime }}</span>
            </div>
            <div v-if="analysisStatus === 'in_progress' && overallProgress > 0 && overallProgress < 100" class="flex items-center justify-between text-xs">
              <span class="text-text-secondary font-medium">{{ t('sidebar.estRemaining') }}</span>
              <span class="font-mono font-bold text-primary">{{ estimatedTimeRemaining }}</span>
            </div>
          </div>

          <!-- Current Step Info -->
          <div v-if="currentRunningStep" class="pt-4 border-t border-white/10 animate-fade-in">
            <div class="text-xs font-bold text-text-secondary uppercase mb-3">{{ t('sidebar.currentAction') }}</div>
            <div class="flex items-start gap-3 p-3 rounded-lg bg-gradient-to-br from-primary/10 to-transparent border border-primary/20">
              <span class="material-symbols-outlined text-base text-primary animate-spin mt-0.5">data_usage</span>
              <div class="flex-1">
                <div class="text-sm font-bold text-white leading-tight">{{ currentRunningStep.title }}</div>
                <div class="text-xs text-primary/80 mt-1 font-medium">{{ t('sidebar.processing') }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Configuration Info -->
      <div class="glass-panel rounded-xl p-6">
        <h3 class="text-sm font-bold text-text-secondary uppercase tracking-wider mb-4">{{ t('sidebar.configuration') }}</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between items-center border-b border-white/5 pb-2">
            <span class="text-text-secondary">{{ t('sidebar.company') }}</span>
            <span class="text-white font-bold">{{ companyName }}</span>
          </div>
          <div class="flex justify-between items-center border-b border-white/5 pb-2">
            <span class="text-text-secondary">{{ t('sidebar.type') }}</span>
            <span class="text-white font-medium">{{ analysisType }}</span>
          </div>
          <div v-if="selectedAgentsCount > 0" class="flex justify-between items-center">
            <span class="text-text-secondary">{{ t('sidebar.agents') }}</span>
            <span class="bg-white/10 px-2 py-0.5 rounded text-xs font-bold text-white">{{ selectedAgentsCount }} {{ t('sidebar.active') }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useLanguage } from '../composables/useLanguage';
import { useToast } from '../composables/useToast';
import { API_BASE } from '@/config/api';
import { DDAnalysisService } from '../services/ddAnalysisService';

const { t } = useLanguage();
const { success, error, warning, info } = useToast();
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

// Time tracking
const startTimeMs = ref(Date.now());
const currentTime = ref(Date.now());
let timeUpdateInterval = null;

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
const pendingSteps = computed(() => analysisSteps.value.filter(s => s.status === 'pending' || s.status === 'running').length);
const overallProgress = computed(() => {
  if (totalSteps.value === 0) return 0;
  return Math.round((completedSteps.value / totalSteps.value) * 100);
});

const currentRunningStep = computed(() => {
  return analysisSteps.value.find(s => s.status === 'running');
});

const selectedAgentsCount = computed(() => props.analysisConfig?.selectedAgents?.length || 0);

// Time formatting helpers
const formatTime = (ms) => {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    return `${hours}小时${minutes % 60}分钟`;
  } else if (minutes > 0) {
    return `${minutes}分${seconds % 60}秒`;
  } else {
    return `${seconds}秒`;
  }
};

const elapsedTime = computed(() => {
  const elapsed = currentTime.value - startTimeMs.value;
  return formatTime(elapsed);
});

const estimatedTimeRemaining = computed(() => {
  if (completedSteps.value === 0 || overallProgress.value === 0) {
    return '计算中...';
  }

  const elapsed = currentTime.value - startTimeMs.value;
  const avgTimePerStep = elapsed / completedSteps.value;
  const remainingSteps = totalSteps.value - completedSteps.value;
  const estimatedRemaining = avgTimePerStep * remainingSteps;

  return formatTime(estimatedRemaining);
});

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

    success('初步分析完成！请查看并保存报告');
    scrollToBottom();
  } else if (data.status === 'completed') {
    analysisStatus.value = 'completed';

    // Mark all steps as completed
    analysisSteps.value = analysisSteps.value.map(step => ({
      ...step,
      status: step.status === 'running' ? 'success' : step.status
    }));

    success('分析已全部完成！');
    scrollToBottom();
  } else if (data.status === 'error') {
    analysisStatus.value = 'error';
    errorMessage.value = data.message || '分析过程中出现错误';
    error('分析出错: ' + (data.message || '未知错误'));
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

    info('正在保存报告...');

    // Call backend API to save report
    const response = await fetch('${API_BASE}/api/reports', {
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
    success('报告保存成功！即将返回列表页...');

    // Navigate back to reports view after a delay
    setTimeout(() => {
      emit('back');
    }, 1500);
  } catch (err) {
    console.error('[AgentChat] Failed to save report:', err);
    error('保存报告失败: ' + err.message);
  }
};

// Lifecycle
onMounted(async () => {
  console.log('[AgentChat] Starting DD analysis with config:', props.analysisConfig);

  // Start time tracking
  startTimeMs.value = Date.now();
  timeUpdateInterval = setInterval(() => {
    currentTime.value = Date.now();
  }, 1000); // Update every second

  // Setup message handler
  ddService.onMessage(handleDDMessage);

  // Setup error handler
  ddService.onError((err) => {
    console.error('[AgentChat] WebSocket error:', err);
    analysisStatus.value = 'error';
    errorMessage.value = '连接错误';
    error('分析连接出错，请检查网络连接后重试');
  });

  // Setup close handler
  ddService.onClose((event) => {
    console.log('[AgentChat] WebSocket closed:', event);

    // If not a normal closure and analysis not completed, show reconnecting status
    if (event.code !== 1000 && analysisStatus.value !== 'completed' && analysisStatus.value !== 'hitl_review') {
      isReconnecting.value = true;
      warning('连接已断开，正在尝试重新连接...', 0); // Keep warning visible
      console.log('[AgentChat] Connection lost, attempting to reconnect...');
    }
  });

  // Listen for successful reconnections
  ddService.onMessage((data) => {
    if (isReconnecting.value && data) {
      isReconnecting.value = false;
      success('重新连接成功，分析继续进行');
      console.log('[AgentChat] Reconnected successfully');
    }
  });

  // Start analysis
  try {
    await ddService.startAnalysis(props.analysisConfig);
    info('分析已启动，AI团队正在工作中...');
  } catch (err) {
    console.error('[AgentChat] Failed to start analysis:', err);
    analysisStatus.value = 'error';
    errorMessage.value = '启动分析失败: ' + err.message;
    error('无法启动分析: ' + err.message);
  }
});

onUnmounted(() => {
  // Stop time tracking
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
    timeUpdateInterval = null;
  }

  ddService.close();
});
</script>

<style scoped>
@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.animate-shimmer {
  animation: shimmer 2s infinite;
}
</style>
