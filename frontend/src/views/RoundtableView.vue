<template>
  <div class="max-w-7xl mx-auto h-full flex flex-col">
    <!-- Start Discussion Panel -->
    <div v-if="!isDiscussionActive" class="glass-panel rounded-2xl p-12 flex-1 flex justify-center overflow-y-auto">
      <div class="max-w-2xl w-full">
        <h2 class="text-2xl font-bold text-white mb-8 flex items-center gap-3">
            <span class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                <span class="material-symbols-outlined">forum</span>
            </span>
            {{ t('roundtable.startPanel.title') }}
        </h2>

        <div class="space-y-8">
          <!-- Topic Input -->
          <div>
            <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">
              {{ t('roundtable.startPanel.topicLabel') }} <span class="text-rose-500">*</span>
            </label>
            <input
              v-model="discussionTopic"
              type="text"
              :placeholder="t('roundtable.startPanel.topicPlaceholder')"
              class="w-full px-6 py-4 rounded-xl bg-black/30 border border-white/10 text-white placeholder-text-secondary focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all text-lg"
            />
          </div>

          <!-- Experts Selection -->
          <div>
            <label class="block text-sm font-bold text-text-secondary mb-3 uppercase tracking-wider">
              {{ t('roundtable.startPanel.expertsLabel') }} ({{ selectedExperts.length }} {{ t('roundtable.startPanel.expertsSelected') }})
            </label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div
                v-for="expert in availableExperts"
                :key="expert.id"
                @click="toggleExpert(expert.id)"
                :class="[
                  'p-4 rounded-xl border transition-all cursor-pointer flex items-center gap-4 group',
                  selectedExperts.includes(expert.id)
                    ? 'border-primary bg-primary/10 shadow-[0_0_15px_rgba(56,189,248,0.15)]'
                    : 'border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20'
                ]"
              >
                <div :class="[
                    'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors',
                    selectedExperts.includes(expert.id) ? 'bg-primary text-background-dark' : 'bg-white/10 text-text-secondary group-hover:text-white'
                ]">
                  <span class="material-symbols-outlined text-2xl">{{ expert.icon }}</span>
                </div>
                <div class="flex-1 min-w-0">
                  <h4 :class="['font-bold text-sm mb-1', selectedExperts.includes(expert.id) ? 'text-white' : 'text-text-primary']">{{ expert.name }}</h4>
                  <p class="text-xs text-text-secondary line-clamp-1">{{ expert.description }}</p>
                </div>
                <div v-if="selectedExperts.includes(expert.id)" class="text-primary animate-fade-in">
                    <span class="material-symbols-outlined">check_circle</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Discussion Settings -->
          <div class="grid grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">
                {{ t('roundtable.startPanel.roundsLabel') }}
              </label>
              <div class="relative">
                <select
                    v-model="maxRounds"
                    class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all appearance-none cursor-pointer"
                >
                    <option :value="3">3 {{ t('roundtable.startPanel.rounds') }}</option>
                    <option :value="5">5 {{ t('roundtable.startPanel.rounds') }}</option>
                    <option :value="8">8 {{ t('roundtable.startPanel.rounds') }}</option>
                    <option :value="10">10 {{ t('roundtable.startPanel.rounds') }}</option>
                </select>
                <span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none">expand_more</span>
              </div>
            </div>
          </div>

          <!-- Start Button -->
          <div class="pt-6">
            <button
              @click="startDiscussion"
              :disabled="!canStartDiscussion"
              :class="[
                'w-full flex items-center justify-center gap-3 px-8 py-4 rounded-xl font-bold text-lg transition-all duration-300',
                canStartDiscussion
                  ? 'bg-gradient-to-r from-primary to-primary-dark text-white shadow-glow hover:shadow-glow-lg hover:-translate-y-1'
                  : 'bg-white/10 text-text-secondary cursor-not-allowed'
              ]"
            >
              <span class="material-symbols-outlined text-2xl">rocket_launch</span>
              {{ t('roundtable.startPanel.startButton') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Active Discussion View -->
    <div v-else class="flex gap-8 flex-1 min-h-0">
      <!-- Left Sidebar: Experts Panel -->
      <div class="w-80 flex-shrink-0 flex flex-col gap-6">
        <!-- Discussion Info -->
        <div class="glass-panel rounded-2xl p-6">
          <h3 class="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4">{{ t('roundtable.discussion.progress') }}</h3>
          <div class="space-y-4">
            <div>
                <div class="flex justify-between text-sm mb-2">
                <span class="text-text-secondary font-medium">{{ t('roundtable.discussion.currentRound') }}</span>
                <span class="text-white font-bold">{{ currentRound }} / {{ maxRounds }}</span>
                </div>
                <div class="w-full bg-black/30 rounded-full h-2 overflow-hidden border border-white/5">
                <div
                    class="bg-gradient-to-r from-primary to-accent-cyan rounded-full h-full transition-all duration-500 relative"
                    :style="{ width: (currentRound / maxRounds * 100) + '%' }"
                >
                    <div class="absolute inset-0 bg-white/20 animate-pulse"></div>
                </div>
                </div>
            </div>
            <div class="flex justify-between text-sm pt-2 border-t border-white/5">
              <span class="text-text-secondary">{{ t('roundtable.discussion.messageCount') }}</span>
              <span class="text-white font-bold">{{ messages.length }}</span>
            </div>
          </div>
        </div>

        <!-- Active Experts -->
        <div class="glass-panel rounded-2xl p-6 flex-1 overflow-y-auto">
          <h3 class="text-xs font-bold text-text-secondary uppercase tracking-wider mb-4">{{ t('roundtable.discussion.participants') }}</h3>
          <div class="space-y-3">
            <div
              v-for="expert in activeExpertsList"
              :key="expert.id"
              class="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/5"
            >
              <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0 text-primary">
                <span class="material-symbols-outlined text-lg">{{ expert.icon }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-bold text-white truncate">{{ expert.name }}</p>
                <p class="text-xs text-text-secondary truncate font-medium">{{ expert.role }}</p>
              </div>
              <div v-if="expert.isActive" class="relative w-2 h-2">
                   <span class="absolute inset-0 rounded-full bg-emerald-500 animate-ping opacity-75"></span>
                   <span class="relative inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
              </div>
            </div>
          </div>
        </div>

        <!-- Control Buttons -->
        <div class="space-y-3">
          <button
            @click="generateMeetingSummary"
            :disabled="isGeneratingSummary || messages.length === 0"
            :class="[
              'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl transition-all font-bold border',
              isGeneratingSummary || messages.length === 0
                ? 'bg-white/5 border-white/5 text-text-secondary cursor-not-allowed'
                : 'bg-primary/10 border-primary/30 text-primary hover:bg-primary/20 hover:shadow-glow-sm'
            ]"
          >
            <span class="material-symbols-outlined" :class="{ 'animate-spin': isGeneratingSummary }">
              {{ isGeneratingSummary ? 'sync' : 'summarize' }}
            </span>
            {{ isGeneratingSummary ? '生成中...' : '生成会议纪要' }}
          </button>
          <div class="grid grid-cols-2 gap-3">
              <button
                @click="stopDiscussion"
                class="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 hover:bg-rose-500/20 transition-colors font-bold"
              >
                <span class="material-symbols-outlined">stop</span>
                停止
              </button>
              <button
                @click="exportDiscussion"
                class="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-text-primary hover:bg-white/10 transition-colors font-bold"
              >
                <span class="material-symbols-outlined">download</span>
                导出
              </button>
          </div>
        </div>
      </div>

      <!-- Main Discussion Area -->
      <div class="flex-1 glass-panel rounded-2xl overflow-hidden flex flex-col relative">
        <!-- Discussion Header -->
        <div class="px-8 py-5 border-b border-white/10 bg-white/5 backdrop-blur-md flex-shrink-0">
          <div class="flex items-center justify-between">
            <div class="flex-1 min-w-0">
              <h2 class="text-xl font-bold text-white truncate">{{ discussionTopic }}</h2>
              <p class="text-xs text-text-secondary mt-1 font-mono flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                  {{ t('roundtable.discussion.startedAt') }} {{ startTime }}
              </p>
            </div>
            <span
              :class="[
                'text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider border shadow-[0_0_10px_rgba(0,0,0,0.2)]',
                discussionStatus === 'running' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-white/10 text-text-secondary border-white/10'
              ]"
            >
              {{ discussionStatus === 'running' ? t('roundtable.discussion.status.running') : t('roundtable.discussion.status.completed') }}
            </span>
          </div>
        </div>

        <!-- Reconnecting Banner -->
        <div v-if="isReconnecting" class="px-6 py-3 bg-amber-500/20 border-b border-amber-500/30 flex-shrink-0 backdrop-blur-md z-10">
          <div class="flex items-center gap-3 text-amber-300 justify-center">
            <span class="material-symbols-outlined animate-spin">sync</span>
            <span class="text-sm font-bold">连接断开，正在尝试重新连接...</span>
          </div>
        </div>

        <!-- Messages Container -->
        <div ref="messagesContainer" class="flex-1 overflow-y-auto p-8 space-y-6 scroll-smooth">
          <div v-for="message in messages" :key="message.id" class="animate-fade-in">
            <!-- System Message -->
            <div v-if="message.type === 'system'" class="flex justify-center py-2">
              <div class="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-text-secondary flex items-center gap-2">
                <span class="material-symbols-outlined text-sm">info</span>
                {{ message.content }}
              </div>
            </div>

            <!-- Agent Message -->
            <div v-else-if="message.type === 'agent_message'" class="flex gap-5 group">
              <div class="w-12 h-12 rounded-xl bg-black/30 border border-white/10 flex items-center justify-center flex-shrink-0 shadow-lg self-start mt-1">
                <span class="material-symbols-outlined text-primary text-2xl">{{ getExpertIcon(message.sender) }}</span>
              </div>
              <div class="flex-1 max-w-4xl">
                <div class="flex items-baseline gap-3 mb-2">
                  <span class="font-bold text-white text-base">{{ message.sender }}</span>
                  <span class="text-xs text-text-secondary font-mono">{{ formatTime(message.timestamp) }}</span>
                  <span
                    v-if="message.message_type !== 'broadcast'"
                    class="text-[10px] px-2 py-0.5 rounded bg-primary/20 text-primary font-bold uppercase tracking-wide border border-primary/20"
                  >
                    {{ getMessageTypeLabel(message.message_type) }}
                  </span>
                </div>
                <div class="glass-card p-5 rounded-2xl rounded-tl-none border border-white/10 bg-white/5 text-text-primary leading-relaxed shadow-md relative">
                  <div class="prose prose-invert prose-sm max-w-none" v-html="formatMeetingMinutes(message.content)"></div>
                  
                  <!-- Decorative corner -->
                  <div class="absolute -top-[1px] -left-[1px] w-4 h-4 border-t border-l border-white/20 rounded-tl-none pointer-events-none"></div>
                </div>
              </div>
            </div>

            <!-- Thinking Indicator -->
            <div v-else-if="message.type === 'thinking'" class="flex gap-5">
              <div class="w-12 h-12 rounded-xl bg-black/30 border border-white/10 flex items-center justify-center flex-shrink-0 shadow-lg self-start mt-1 opacity-70">
                <span class="material-symbols-outlined text-primary text-2xl animate-pulse">psychology</span>
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-2">
                  <span class="font-bold text-text-secondary text-sm">{{ message.agent }}</span>
                  <span class="text-xs text-text-secondary opacity-70">正在思考...</span>
                </div>
                <div class="inline-block px-5 py-4 rounded-2xl rounded-tl-none bg-white/5 border border-white/5">
                  <div class="flex items-center gap-2">
                    <div class="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                    <div class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                    <div class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Summary / Meeting Minutes -->
            <div v-else-if="message.type === 'summary' || message.type === 'meeting_minutes'" class="my-8">
              <div class="glass-panel border border-primary/30 bg-primary/5 rounded-2xl p-8 relative overflow-hidden">
                <!-- Background decoration -->
                <div class="absolute top-0 right-0 w-64 h-64 bg-primary/10 blur-[80px] rounded-full pointer-events-none"></div>
                
                <div class="relative z-10">
                    <div class="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
                    <div class="flex items-center gap-3">
                        <div class="p-2 rounded-lg bg-primary/20 text-primary">
                            <span class="material-symbols-outlined text-2xl">summarize</span>
                        </div>
                        <h3 class="text-xl font-bold text-white">
                        {{ message.type === 'meeting_minutes' ? '会议纪要' : t('roundtable.summary.title') }}
                        </h3>
                    </div>
                    <button
                        @click="exportMeetingMinutes(message.content)"
                        class="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors text-xs font-bold"
                    >
                        <span class="material-symbols-outlined text-sm">download</span>
                        导出
                    </button>
                    </div>
                    <div class="prose prose-invert prose-sm max-w-none">
                        <div v-html="formatMeetingMinutes(message.content)"></div>
                    </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Loading indicator -->
          <div v-if="isConnecting" class="flex justify-center py-12">
            <div class="text-center">
              <div class="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mx-auto mb-4 shadow-[0_0_20px_rgba(56,189,248,0.4)]"></div>
              <p class="text-primary font-bold animate-pulse">{{ t('roundtable.discussion.connecting') }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onUnmounted, onMounted } from 'vue';
import { useLanguage } from '../composables/useLanguage';
import { getRoundtableAgents } from '../config/agents';
import { marked } from 'marked';

const { t, locale } = useLanguage();

// Discussion state
const isDiscussionActive = ref(false);
const discussionTopic = ref('');
const maxRounds = ref(5);
const currentRound = ref(0);
const discussionStatus = ref('idle'); // idle, running, completed
const startTime = ref('');
const isConnecting = ref(false);
const isReconnecting = ref(false); // Track reconnection attempts
const isGeneratingSummary = ref(false); // Track summary generation
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
let shouldReconnect = true; // Flag to control reconnection
let discussionConfig = null; // Store config for reconnection

// Available experts - computed to be reactive to language changes
const availableExperts = computed(() => {
  const agents = getRoundtableAgents();
  const isZh = locale.value.startsWith('zh'); // 'zh-CN' or 'zh'
  return agents.map(agent => ({
    id: agent.id,
    name: isZh ? agent.name_zh : agent.name,
    role: isZh ? agent.role_zh : agent.role,
    description: isZh ? agent.description_zh : agent.description,
    icon: agent.icon
  }));
});

const selectedExperts = ref([]);

// Initialize selected experts on mount
onMounted(() => {
  const agents = getRoundtableAgents();
  selectedExperts.value = agents.map(a => a.id);
});

// Messages
const messages = ref([]);
const messagesContainer = ref(null);

// WebSocket
let ws = null;

// Computed
const canStartDiscussion = computed(() => {
  return discussionTopic.value.trim().length > 0 && selectedExperts.value.length >= 2;
});

const activeExpertsList = computed(() => {
  // Use selectedExperts to filter and map to full objects
  // Also check if they are currently 'speaking' (thinking) or active
  // For simplicity in this UI, 'isActive' is just checking if they exist in selection
  // Real app might track who is currently typing
  return availableExperts.value
    .filter(e => selectedExperts.value.includes(e.id))
    .map(e => ({
        ...e,
        isActive: messages.value.some(m => m.type === 'thinking' && m.agent === e.name) // Simple check
    }));
});

// Methods
const toggleExpert = (expertId) => {
  const index = selectedExperts.value.indexOf(expertId);
  if (index > -1) {
    // Don't allow removing if less than 2 experts
    if (selectedExperts.value.length > 2) {
      selectedExperts.value.splice(index, 1);
    }
  } else {
    selectedExperts.value.push(expertId);
  }
};

const startDiscussion = async () => {
  if (!canStartDiscussion.value) return;

  // Store config for potential reconnection
  discussionConfig = {
    topic: discussionTopic.value,
    experts: selectedExperts.value,
    maxRounds: maxRounds.value
  };
  shouldReconnect = true;
  reconnectAttempts = 0;

  isDiscussionActive.value = true;
  isConnecting.value = true;
  discussionStatus.value = 'running';
  currentRound.value = 0;
  messages.value = [];

  const now = new Date();
  startTime.value = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

  // Add system message
  messages.value.push({
    id: Date.now(),
    type: 'system',
    content: `讨论已开始 - ${selectedExperts.value.length} 位专家参与讨论`
  });

  // Connect to WebSocket
  connectWebSocket();
};

const connectWebSocket = () => {
  try {
    // Connect to backend roundtable WebSocket
    ws = new WebSocket('ws://localhost:8000/ws/roundtable');

    ws.onopen = () => {
      console.log('[Roundtable] WebSocket connected');
      isConnecting.value = false;
      isReconnecting.value = false;
      reconnectAttempts = 0;

      // Send initial message to start discussion
      const lang = locale.value.startsWith('zh') ? 'zh' : 'en'; // 转换为后端期望的格式
      const initialMessage = {
        action: 'start_discussion',
        topic: discussionConfig?.topic || discussionTopic.value,
        company_name: (discussionConfig?.topic || discussionTopic.value).split(' ')[0] || '目标公司',
        language: lang, // 添加语言偏好
        context: {
          max_rounds: discussionConfig?.maxRounds || maxRounds.value,
          experts: discussionConfig?.experts || selectedExperts.value
        }
      };

      ws.send(JSON.stringify(initialMessage));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (error) {
        console.error('[Roundtable] Error parsing WebSocket message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[Roundtable] WebSocket error:', error);
      isConnecting.value = false;
      messages.value.push({
        id: Date.now(),
        type: 'system',
        content: '连接错误,请检查后端服务是否正常运行'
      });
    };

    ws.onclose = (event) => {
      console.log('[Roundtable] WebSocket closed:', event.code, event.reason);
      isConnecting.value = false;

      // Auto-reconnect logic (unless explicitly closed by user or discussion completed)
      if (shouldReconnect && event.code !== 1000 && discussionStatus.value === 'running') {
        isReconnecting.value = true;
        attemptReconnect();
      } else if (discussionStatus.value === 'running' && event.code !== 1000) {
        discussionStatus.value = 'completed';
        messages.value.push({
          id: Date.now(),
          type: 'system',
          content: '讨论已结束'
        });
      }
    };
  } catch (error) {
    console.error('[Roundtable] Error connecting to WebSocket:', error);
    isConnecting.value = false;
  }
};

const attemptReconnect = () => {
  if (reconnectAttempts < maxReconnectAttempts) {
    reconnectAttempts++;
    const delay = 2000 * reconnectAttempts; // Exponential backoff

    console.log(`[Roundtable] Attempting to reconnect (${reconnectAttempts}/${maxReconnectAttempts}) in ${delay}ms...`);

    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: `连接断开，正在尝试重连 (${reconnectAttempts}/${maxReconnectAttempts})...`
    });

    setTimeout(() => {
      connectWebSocket();
    }, delay);
  } else {
    console.error('[Roundtable] Max reconnection attempts reached');
    isReconnecting.value = false;
    discussionStatus.value = 'completed';
    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: '无法重新连接到服务器，讨论已终止'
    });
  }
};

const handleWebSocketMessage = (data) => {
  console.log('Received message:', data);

  if (data.type === 'agents_ready') {
    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: data.message
    });
    scrollToBottom();
  } else if (data.type === 'agent_event') {
    const event = data.event;

    if (event.event_type === 'thinking') {
      // Show thinking indicator
      messages.value.push({
        id: Date.now() + Math.random(),
        type: 'thinking',
        agent: event.agent_name
      });
      scrollToBottom();
    } else if (event.event_type === 'result') {
      // Remove thinking indicator for this agent
      const thinkingIndex = messages.value.findIndex(
        m => m.type === 'thinking' && m.agent === event.agent_name
      );
      if (thinkingIndex !== -1) {
        messages.value.splice(thinkingIndex, 1);
      }

      // Add agent message
      messages.value.push({
        id: Date.now() + Math.random(),
        type: 'agent_message',
        sender: event.agent_name,
        content: event.message,
        message_type: event.data?.message_type || 'broadcast',
        timestamp: event.timestamp || new Date().toISOString()
      });
      scrollToBottom();
    } else if (event.event_type === 'started') {
      messages.value.push({
        id: Date.now(),
        type: 'system',
        content: event.message
      });
      scrollToBottom();
    } else if (event.event_type === 'completed') {
      discussionStatus.value = 'completed';
      messages.value.push({
        id: Date.now(),
        type: 'system',
        content: event.message
      });
      scrollToBottom();
    } else if (event.event_type === 'error') {
      messages.value.push({
        id: Date.now(),
        type: 'system',
        content: `错误: ${event.message}`
      });
      scrollToBottom();
    }
  } else if (data.type === 'discussion_complete') {
    discussionStatus.value = 'completed';
    if (data.summary) {
      const summary = data.summary;

      // 如果有会议纪要，优先显示
      if (summary.meeting_minutes) {
        messages.value.push({
          id: Date.now(),
          type: 'meeting_minutes',
          content: summary.meeting_minutes
        });
      } else {
        // 否则显示统计摘要
        let summaryText = '## 讨论统计\n\n';
        summaryText += `- **总轮次**: ${summary.total_turns || 0}\n`;
        summaryText += `- **总消息数**: ${summary.total_messages || 0}\n`;
        summaryText += `- **讨论时长**: ${(summary.total_duration_seconds || 0).toFixed(1)} 秒\n\n`;

        if (summary.agent_stats) {
          summaryText += '### 专家发言统计\n\n';
          for (const [agent, stats] of Object.entries(summary.agent_stats)) {
            summaryText += `**${agent}**:\n`;
            summaryText += `- 总消息: ${stats.total_messages || 0}\n`;
            summaryText += `- 广播: ${stats.broadcast || 0}\n`;
            summaryText += `- 私聊: ${stats.private || 0}\n`;
            summaryText += `- 提问: ${stats.questions || 0}\n\n`;
          }
        }

        messages.value.push({
          id: Date.now(),
          type: 'summary',
          content: summaryText
        });
      }
    }
    scrollToBottom();
  } else if (data.type === 'error') {
    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: `错误: ${data.message}`
    });
    scrollToBottom();
  }
};

const stopDiscussion = () => {
  console.log('[Roundtable] Stopping discussion...');
  shouldReconnect = false; // Disable auto-reconnect
  if (ws) {
    ws.close(1000, 'User stopped discussion'); // Normal closure
  }
  discussionStatus.value = 'completed';
  isReconnecting.value = false;
};

const generateMeetingSummary = async () => {
  if (isGeneratingSummary.value || messages.value.length === 0) return;

  isGeneratingSummary.value = true;

  try {
    // 收集所有对话消息
    const dialogueMessages = messages.value
      .filter(m => m.type === 'agent_message')
      .map(m => ({
        speaker: m.sender,
        content: m.content,
        timestamp: m.timestamp
      }));

    // 调用后端API生成会议纪要
    const lang = locale.value.startsWith('zh') ? 'zh' : 'en'; // 转换为后端期望的格式
    const response = await fetch('http://localhost:8000/api/roundtable/generate_summary', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        topic: discussionTopic.value,
        messages: dialogueMessages,
        participants: selectedExperts.value,
        rounds: currentRound.value,
        language: lang // 添加语言偏好
      })
    });

    if (!response.ok) {
      throw new Error('Failed to generate meeting summary');
    }

    const data = await response.json();

    // 添加会议纪要到消息列表
    messages.value.push({
      id: Date.now(),
      type: 'meeting_minutes',
      content: data.summary
    });

    scrollToBottom();
  } catch (error) {
    console.error('Error generating meeting summary:', error);
    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: '生成会议纪要失败，请重试'
    });
  } finally {
    isGeneratingSummary.value = false;
  }
};

const exportDiscussion = () => {
  const content = messages.value
    .filter(m => m.type === 'agent_message' || m.type === 'summary')
    .map(m => {
      if (m.type === 'agent_message') {
        return `[${m.sender}] ${m.content}\n`;
      } else {
        return `[总结]\n${m.content}\n`;
      }
    })
    .join('\n');

  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `roundtable_${discussionTopic.value}_${new Date().getTime()}.txt`;
  a.click();
  URL.revokeObjectURL(url);
};

const exportMeetingMinutes = (content) => {
  // 生成完整的会议纪要Markdown文件
  const timestamp = new Date().toLocaleString('zh-CN');
  const fullContent = `# 圆桌讨论会议纪要

**讨论主题**: ${discussionTopic.value}
**生成时间**: ${timestamp}

---

${content}

---

*本会议纪要由AI圆桌讨论系统自动生成*
`;

  const blob = new Blob([fullContent], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  // 生成友好的文件名
  const sanitizedTopic = discussionTopic.value.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_').substring(0, 30);
  const dateStr = new Date().toISOString().split('T')[0];
  a.download = `会议纪要_${sanitizedTopic}_${dateStr}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const formatMeetingMinutes = (content) => {
  // Convert markdown to HTML using marked library
  try {
    // Configure marked for safer rendering
    marked.setOptions({
      breaks: true,      // Convert \n to <br>
      gfm: true,         // GitHub Flavored Markdown
      headerIds: false,  // Don't add IDs to headers
      mangle: false      // Don't escape email addresses
    });

    return marked.parse(content);
  } catch (error) {
    console.error('Markdown parsing error:', error);
    // Fallback to simple formatting
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br/>');
  }
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

const getExpertIcon = (senderName) => {
  const expert = availableExperts.value.find(e =>
    e.name.includes(senderName) || senderName.includes(e.id)
  );
  return expert?.icon || 'person';
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
};

const getMessageTypeLabel = (type) => {
  const labels = {
    'broadcast': '公开',
    'direct': '私聊',
    'question': '提问',
    'response': '回复',
    'agreement': '同意',
    'disagreement': '反对'
  };
  return labels[type] || type;
};

// Cleanup
onUnmounted(() => {
  if (ws) {
    ws.close();
  }
});
</script>