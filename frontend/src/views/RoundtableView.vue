<template>
  <div class="max-w-7xl mx-auto">
    <!-- Page Header -->
    <div class="mb-6">
      <h1 class="text-3xl font-bold text-text-primary mb-2">{{ t('roundtable.title') }}</h1>
      <p class="text-text-secondary">{{ t('roundtable.subtitle') }}</p>
    </div>

    <!-- Start Discussion Panel -->
    <div v-if="!isDiscussionActive" class="bg-surface border border-border-color rounded-lg p-8">
      <div class="max-w-2xl mx-auto">
        <h2 class="text-xl font-bold text-text-primary mb-6">{{ t('roundtable.startPanel.title') }}</h2>

        <div class="space-y-6">
          <!-- Topic Input -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-2">
              {{ t('roundtable.startPanel.topicLabel') }} <span class="text-accent-red">*</span>
            </label>
            <input
              v-model="discussionTopic"
              type="text"
              :placeholder="t('roundtable.startPanel.topicPlaceholder')"
              class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors"
            />
          </div>

          <!-- Experts Selection -->
          <div>
            <label class="block text-sm font-semibold text-text-primary mb-3">
              {{ t('roundtable.startPanel.expertsLabel') }} ({{ selectedExperts.length }}/5 {{ t('roundtable.startPanel.expertsSelected') }})
            </label>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div
                v-for="expert in availableExperts"
                :key="expert.id"
                @click="toggleExpert(expert.id)"
                :class="[
                  'p-4 rounded-lg border-2 transition-all cursor-pointer',
                  selectedExperts.includes(expert.id)
                    ? 'border-primary bg-primary/10'
                    : 'border-border-color hover:border-primary/50'
                ]"
              >
                <div class="flex items-start gap-3">
                  <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                    <span class="material-symbols-outlined text-primary">{{ expert.icon }}</span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <h4 class="font-semibold text-text-primary text-sm mb-1">{{ expert.name }}</h4>
                    <p class="text-xs text-text-secondary">{{ expert.description }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Discussion Settings -->
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-text-primary mb-2">
                {{ t('roundtable.startPanel.roundsLabel') }}
              </label>
              <select
                v-model="maxRounds"
                class="w-full px-4 py-3 rounded-lg bg-background-dark border border-border-color text-text-primary focus:outline-none focus:border-primary transition-colors"
              >
                <option :value="3">3 {{ t('roundtable.startPanel.rounds') }}</option>
                <option :value="5">5 {{ t('roundtable.startPanel.rounds') }}</option>
                <option :value="8">8 {{ t('roundtable.startPanel.rounds') }}</option>
                <option :value="10">10 {{ t('roundtable.startPanel.rounds') }}</option>
              </select>
            </div>
          </div>

          <!-- Start Button -->
          <div class="flex gap-3 pt-4">
            <button
              @click="startDiscussion"
              :disabled="!canStartDiscussion"
              :class="[
                'flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all',
                canStartDiscussion
                  ? 'bg-primary text-background-dark hover:bg-primary/90'
                  : 'bg-surface text-text-secondary cursor-not-allowed'
              ]"
            >
              <span class="material-symbols-outlined">rocket_launch</span>
              {{ t('roundtable.startPanel.startButton') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Active Discussion View -->
    <div v-else class="flex gap-6">
      <!-- Left Sidebar: Experts Panel -->
      <div class="w-80 flex-shrink-0 space-y-4">
        <!-- Discussion Info -->
        <div class="bg-surface border border-border-color rounded-lg p-4">
          <h3 class="text-sm font-semibold text-text-primary mb-3">{{ t('roundtable.discussion.progress') }}</h3>
          <div class="space-y-2">
            <div class="flex justify-between text-sm">
              <span class="text-text-secondary">{{ t('roundtable.discussion.currentRound') }}</span>
              <span class="text-text-primary font-semibold">{{ currentRound }} / {{ maxRounds }}</span>
            </div>
            <div class="w-full bg-background-dark rounded-full h-2">
              <div
                class="bg-primary rounded-full h-2 transition-all"
                :style="{ width: (currentRound / maxRounds * 100) + '%' }"
              ></div>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-text-secondary">{{ t('roundtable.discussion.messageCount') }}</span>
              <span class="text-text-primary font-semibold">{{ messages.length }}</span>
            </div>
          </div>
        </div>

        <!-- Active Experts -->
        <div class="bg-surface border border-border-color rounded-lg p-4">
          <h3 class="text-sm font-semibold text-text-primary mb-3">{{ t('roundtable.discussion.participants') }}</h3>
          <div class="space-y-2">
            <div
              v-for="expert in activeExpertsList"
              :key="expert.id"
              class="flex items-center gap-3 p-2 rounded-lg bg-background-dark"
            >
              <div class="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                <span class="material-symbols-outlined text-primary text-sm">{{ expert.icon }}</span>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-semibold text-text-primary truncate">{{ expert.name }}</p>
                <p class="text-xs text-text-secondary truncate">{{ expert.role }}</p>
              </div>
              <span
                :class="[
                  'w-2 h-2 rounded-full',
                  expert.isActive ? 'bg-accent-green animate-pulse' : 'bg-text-secondary'
                ]"
              ></span>
            </div>
          </div>
        </div>

        <!-- Control Buttons -->
        <div class="space-y-2">
          <button
            @click="stopDiscussion"
            class="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-accent-red/20 text-accent-red hover:bg-accent-red/30 transition-colors text-sm font-semibold"
          >
            <span class="material-symbols-outlined">stop</span>
            {{ t('roundtable.discussion.stopButton') }}
          </button>
          <button
            @click="exportDiscussion"
            class="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-border-color text-text-primary hover:bg-surface transition-colors text-sm font-semibold"
          >
            <span class="material-symbols-outlined">download</span>
            {{ t('roundtable.discussion.exportButton') }}
          </button>
        </div>
      </div>

      <!-- Main Discussion Area -->
      <div class="flex-1 bg-surface border border-border-color rounded-lg overflow-hidden flex flex-col">
        <!-- Discussion Header -->
        <div class="px-6 py-4 border-b border-border-color bg-background-dark">
          <div class="flex items-center justify-between">
            <div class="flex-1 min-w-0">
              <h2 class="text-xl font-bold text-text-primary truncate">{{ discussionTopic }}</h2>
              <p class="text-sm text-text-secondary mt-1">{{ t('roundtable.discussion.startedAt') }} {{ startTime }}</p>
            </div>
            <span
              :class="[
                'text-sm px-3 py-1 rounded-full font-semibold ml-4',
                discussionStatus === 'running' ? 'bg-accent-green/20 text-accent-green' : 'bg-surface text-text-secondary'
              ]"
            >
              {{ discussionStatus === 'running' ? t('roundtable.discussion.status.running') : t('roundtable.discussion.status.completed') }}
            </span>
          </div>
        </div>

        <!-- Reconnecting Banner -->
        <div v-if="isReconnecting" class="px-6 py-3 bg-accent-yellow/10 border-b border-accent-yellow/30">
          <div class="flex items-center gap-2 text-accent-yellow">
            <span class="material-symbols-outlined animate-spin">sync</span>
            <span class="text-sm font-semibold">连接断开，正在尝试重新连接...</span>
          </div>
        </div>

        <!-- Messages Container -->
        <div ref="messagesContainer" class="flex-1 overflow-y-auto p-6 space-y-4">
          <div v-for="message in messages" :key="message.id">
            <!-- System Message -->
            <div v-if="message.type === 'system'" class="flex justify-center">
              <div class="px-4 py-2 rounded-full bg-surface border border-border-color text-xs text-text-secondary">
                <span class="material-symbols-outlined text-xs align-middle mr-1">info</span>
                {{ message.content }}
              </div>
            </div>

            <!-- Agent Message -->
            <div v-else-if="message.type === 'agent_message'" class="flex gap-4">
              <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                <span class="material-symbols-outlined text-primary text-lg">{{ getExpertIcon(message.sender) }}</span>
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-2">
                  <span class="font-semibold text-text-primary">{{ message.sender }}</span>
                  <span class="text-xs text-text-secondary">{{ formatTime(message.timestamp) }}</span>
                  <span
                    v-if="message.message_type !== 'broadcast'"
                    class="text-xs px-2 py-0.5 rounded bg-primary/20 text-primary"
                  >
                    {{ getMessageTypeLabel(message.message_type) }}
                  </span>
                </div>
                <div class="bg-background-dark border border-border-color rounded-lg p-4">
                  <p class="text-text-primary whitespace-pre-wrap">{{ message.content }}</p>
                </div>
              </div>
            </div>

            <!-- Thinking Indicator -->
            <div v-else-if="message.type === 'thinking'" class="flex gap-4">
              <div class="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center flex-shrink-0">
                <span class="material-symbols-outlined text-primary text-lg animate-pulse">psychology</span>
              </div>
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-2">
                  <span class="font-semibold text-text-primary">{{ message.agent }}</span>
                  <span class="text-xs text-text-secondary">正在思考...</span>
                </div>
                <div class="bg-background-dark border border-border-color rounded-lg p-4">
                  <div class="flex items-center gap-2">
                    <div class="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                    <div class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                    <div class="w-2 h-2 bg-primary rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Summary -->
            <div v-else-if="message.type === 'summary'" class="mt-6">
              <div class="bg-primary/10 border border-primary rounded-lg p-6">
                <div class="flex items-center gap-2 mb-4">
                  <span class="material-symbols-outlined text-primary">summarize</span>
                  <h3 class="text-lg font-bold text-text-primary">{{ t('roundtable.summary.title') }}</h3>
                </div>
                <div class="prose prose-sm max-w-none text-text-primary">
                  <p class="whitespace-pre-wrap">{{ message.content }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Loading indicator -->
          <div v-if="isConnecting" class="flex justify-center py-8">
            <div class="text-center">
              <div class="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent mx-auto mb-4"></div>
              <p class="text-text-secondary">{{ t('roundtable.discussion.connecting') }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onUnmounted } from 'vue';
import { useLanguage } from '../composables/useLanguage';

const { t } = useLanguage();

// Discussion state
const isDiscussionActive = ref(false);
const discussionTopic = ref('');
const maxRounds = ref(5);
const currentRound = ref(0);
const discussionStatus = ref('idle'); // idle, running, completed
const startTime = ref('');
const isConnecting = ref(false);
const isReconnecting = ref(false); // Track reconnection attempts
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
let shouldReconnect = true; // Flag to control reconnection
let discussionConfig = null; // Store config for reconnection

// Available experts - using computed for i18n reactivity
const availableExperts = computed(() => [
  {
    id: 'leader',
    name: t('roundtable.experts.leader.name'),
    role: t('roundtable.experts.leader.role'),
    description: t('roundtable.experts.leader.description'),
    icon: 'emoji_events'
  },
  {
    id: 'market-analyst',
    name: t('roundtable.experts.marketAnalyst.name'),
    role: t('roundtable.experts.marketAnalyst.role'),
    description: t('roundtable.experts.marketAnalyst.description'),
    icon: 'show_chart'
  },
  {
    id: 'financial-expert',
    name: t('roundtable.experts.financialExpert.name'),
    role: t('roundtable.experts.financialExpert.role'),
    description: t('roundtable.experts.financialExpert.description'),
    icon: 'account_balance'
  },
  {
    id: 'team-evaluator',
    name: t('roundtable.experts.teamEvaluator.name'),
    role: t('roundtable.experts.teamEvaluator.role'),
    description: t('roundtable.experts.teamEvaluator.description'),
    icon: 'groups'
  },
  {
    id: 'risk-assessor',
    name: t('roundtable.experts.riskAssessor.name'),
    role: t('roundtable.experts.riskAssessor.role'),
    description: t('roundtable.experts.riskAssessor.description'),
    icon: 'shield'
  }
]);

const selectedExperts = ref(['leader', 'market-analyst', 'financial-expert', 'team-evaluator', 'risk-assessor']);

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
  return availableExperts.value.filter(e => selectedExperts.value.includes(e.id));
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
      const initialMessage = {
        action: 'start_discussion',
        topic: discussionConfig?.topic || discussionTopic.value,
        company_name: (discussionConfig?.topic || discussionTopic.value).split(' ')[0] || '目标公司',
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
      const summaryText = JSON.stringify(data.summary, null, 2);
      messages.value.push({
        id: Date.now(),
        type: 'summary',
        content: summaryText
      });
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
