<template>
  <div class="page-shell relative h-full min-h-0 flex flex-col">
    <div class="pointer-events-none absolute inset-0 -z-10">
      <div class="absolute -left-16 top-1/4 h-64 w-64 rounded-full bg-primary/10 blur-3xl"></div>
      <div class="absolute -right-20 bottom-16 h-72 w-72 rounded-full bg-accent-cyan/10 blur-3xl"></div>
    </div>

    <div
      class="grid h-full flex-1 min-h-0 grid-cols-1 gap-2 xl:gap-1"
      :class="historyCollapsed ? 'xl:grid-cols-[minmax(0,1fr)_96px] xl:grid-rows-1' : 'xl:grid-cols-[minmax(0,1fr)_312px] xl:grid-rows-1'"
    >
      <aside
        class="min-h-0 h-full flex flex-col overflow-hidden xl:col-start-2 xl:row-start-1 transition-all duration-200"
        :class="historyCollapsed ? 'rounded-2xl bg-transparent p-1' : 'rounded-3xl bg-transparent p-3'"
      >
        <div v-if="!historyCollapsed" class="mb-3 flex items-center justify-between gap-2">
          <h3 class="section-title !mb-0">
            <span class="material-symbols-outlined text-primary">history</span>
            {{ t('chatHub.sessionHistory') }}
          </h3>
          <div class="flex items-center gap-1">
            <button class="icon-btn h-9 w-9 border-0 bg-white/10 hover:bg-white/15" :title="t('chatHub.newSession')" @click="createNewSession">
              <span class="material-symbols-outlined text-base">add</span>
            </button>
            <button class="icon-btn h-9 w-9 border-0 bg-white/10 hover:bg-white/15" :title="historyToggleLabel" @click="toggleHistoryPanel">
              <span class="material-symbols-outlined text-base">chevron_left</span>
            </button>
          </div>
        </div>

        <div v-else class="mb-3 flex flex-col items-center gap-2">
          <button class="icon-btn h-10 w-10 border-0 bg-white/10 hover:bg-white/15" :title="historyToggleLabel" @click="toggleHistoryPanel">
            <span class="material-symbols-outlined text-base">chevron_right</span>
          </button>
          <button class="icon-btn h-10 w-10 border-0 bg-white/10 hover:bg-white/15" :title="t('chatHub.newSession')" @click="createNewSession">
            <span class="material-symbols-outlined">add</span>
          </button>
        </div>

        <div v-if="!historyCollapsed" class="flex-1 overflow-y-auto space-y-2 pr-1">
          <div
            v-for="session in visibleSessions"
            :key="session.id"
            class="rounded-2xl p-2 transition-colors"
            :class="session.id === activeSessionId ? 'bg-primary/14' : 'bg-transparent hover:bg-white/6'"
          >
            <button
              class="w-full rounded-lg px-2 py-1.5 text-left transition-colors hover:bg-white/5"
              @click="setActiveSession(session.id)"
            >
              <p class="truncate text-sm font-semibold text-white">{{ session.title || t('chatHub.sessionUntitled') }}</p>
              <p class="mt-1 line-clamp-2 text-xs text-text-secondary">{{ session.preview || t('chatHub.sessionPreviewNone') }}</p>
              <p class="mt-2 text-[11px] text-text-tertiary">{{ formatSessionTime(session.updatedAt) }}</p>
            </button>
            <div class="mt-1 flex items-center justify-end gap-1 px-1">
              <button
                class="icon-btn h-8 w-8 border-0 bg-white/10 hover:bg-white/15"
                :title="t('chatHub.renameSession')"
                @click.stop="renameSession(session.id)"
              >
                <span class="material-symbols-outlined text-base">edit</span>
              </button>
              <button
                class="icon-btn h-8 w-8 border-0 bg-white/10 text-rose-300 hover:bg-white/15 hover:text-rose-200"
                :title="t('chatHub.deleteSession')"
                @click.stop="deleteSession(session.id)"
              >
                <span class="material-symbols-outlined text-base">delete</span>
              </button>
            </div>
          </div>

          <div v-if="sessions.length === 0" class="rounded-xl bg-white/5 p-4 text-sm text-text-secondary">
            {{ t('chatHub.emptyHistory') }}
          </div>

          <button
            v-if="hasMoreSessions"
            type="button"
            class="w-full rounded-xl bg-white/5 px-3 py-2 text-xs text-text-secondary transition-colors hover:bg-white/10 hover:text-white"
            @click="toggleSessionListMode"
          >
            {{ showAllSessions ? t('chatHub.showLessSessions') : t('chatHub.showAllSessions') }}
          </button>
        </div>

        <div v-else class="flex-1 overflow-y-auto space-y-2 pr-1">
          <button
            v-for="session in sessions"
            :key="session.id"
            class="mx-auto flex h-10 w-10 items-center justify-center rounded-xl text-xs font-bold transition-colors"
            :class="session.id === activeSessionId ? 'bg-primary/25 text-primary-light' : 'bg-white/10 text-text-secondary hover:text-white'"
            :title="session.title || t('chatHub.sessionUntitled')"
            @click="setActiveSession(session.id)"
          >
            {{ sessionInitial(session) }}
          </button>
        </div>
      </aside>

      <section class="relative h-full min-h-0 overflow-hidden rounded-[30px] bg-transparent flex flex-col xl:col-start-1 xl:row-start-1">
        <div class="pointer-events-none absolute -right-8 top-10 h-36 w-36 rounded-full bg-primary/10 blur-3xl"></div>
        <div class="pointer-events-none absolute left-10 bottom-10 h-32 w-32 rounded-full bg-accent-cyan/10 blur-3xl"></div>

        <div class="relative flex flex-wrap items-center justify-between gap-3 px-5 py-4">
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">forum</span>
              <p class="truncate text-sm font-semibold text-white">{{ activeSessionTitle }}</p>
            </div>
            <p class="mt-1 truncate text-xs text-text-secondary">{{ sessionId || t('chatHub.system.sessionPending') }}</p>
          </div>
          <div class="flex items-center gap-2">
            <div
              class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs"
              :class="connected ? 'text-emerald-300 bg-emerald-500/12' : 'text-amber-300 bg-amber-500/12'"
            >
              <span class="h-2 w-2 rounded-full" :class="connected ? 'bg-emerald-400' : 'bg-amber-300'"></span>
              {{ connected ? t('chatHub.connected') : t('chatHub.disconnected') }}
            </div>
            <button class="icon-btn border-0 bg-white/10 hover:bg-white/15" :disabled="connecting" :title="connectionButtonLabel" @click="reconnectCurrentSession">
              <span class="material-symbols-outlined text-base" :class="connecting ? 'animate-spin' : ''">refresh</span>
            </button>
          </div>
        </div>

        <div ref="messagesContainer" class="relative flex-1 overflow-y-auto px-5 py-3 space-y-4">
          <div v-if="messages.length === 0" class="flex min-h-full items-center justify-center py-12">
            <div class="max-w-xl text-center">
              <p class="text-2xl font-semibold tracking-tight text-white md:text-4xl">{{ t('chatHub.emptyState.title') }}</p>
              <p class="mt-3 text-sm text-text-secondary md:text-base">{{ t('chatHub.emptyState.subtitle') }}</p>
              <div class="mt-6 flex flex-wrap items-center justify-center gap-2">
                <span class="text-xs font-semibold uppercase tracking-wider text-text-secondary">{{ t('chatHub.starters.label') }}</span>
                <button
                  v-for="prompt in starterPrompts"
                  :key="prompt"
                  type="button"
                  class="rounded-full bg-white/10 px-3 py-1.5 text-xs text-text-primary transition-colors hover:bg-white/20"
                  @click="applyStarterPrompt(prompt)"
                >
                  {{ prompt }}
                </button>
              </div>
            </div>
          </div>

          <template v-for="msg in messages" :key="msg.id">
            <div v-if="msg.type === 'system'" class="flex justify-center">
              <div
                class="max-w-[90%] rounded-full bg-white/8 px-4 py-1.5 text-xs"
                :class="msg.level === 'error'
                  ? 'bg-rose-500/20 text-rose-300'
                  : 'text-text-secondary'"
              >
                {{ msg.content }}
              </div>
            </div>

            <div v-else :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'">
              <div
                :class="[
                  'max-w-[88%] rounded-3xl px-4 py-3 shadow-sm',
                  msg.role === 'user'
                    ? 'bg-primary/22 text-white'
                    : 'bg-white/10 text-text-primary'
                ]"
              >
                <div class="mb-2 flex items-center justify-between gap-3">
                  <p class="text-xs font-bold uppercase tracking-wider" :class="msg.role === 'user' ? 'text-primary-light' : 'text-text-secondary'">
                    {{ msg.speaker }}
                  </p>
                  <p class="text-[11px] text-text-secondary">{{ formatTime(msg.timestamp) }}</p>
                </div>

                <div
                  v-if="msg.role === 'assistant'"
                  class="analysis-markdown max-w-none break-words"
                  :class="{ 'report-mode': isReportLike(msg.content) }"
                  v-html="renderMarkdown(msg.content)"
                ></div>
                <p v-else class="whitespace-pre-wrap break-words text-sm leading-relaxed">
                  {{ msg.content }}
                </p>

                <div v-if="msg.role === 'user' && msg.attachments && msg.attachments.length" class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                  <div
                    v-for="att in msg.attachments"
                    :key="att.id || att.name"
                    class="overflow-hidden rounded-xl bg-black/25"
                  >
                    <img
                      v-if="att.previewUrl"
                      :src="att.previewUrl"
                      :alt="att.name"
                      class="h-24 w-full object-cover"
                      @load="handleMessageImageLoad"
                    />
                    <div v-else class="flex h-24 items-center justify-center gap-2 px-2 text-xs text-text-secondary">
                      <span class="material-symbols-outlined text-sm">image</span>
                      <span class="truncate">{{ att.name }}</span>
                    </div>
                    <p class="truncate px-2 py-1 text-[11px] text-text-secondary">{{ att.name }}</p>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <div v-if="turnInFlight" class="mx-auto w-full max-w-2xl rounded-2xl bg-white/8 px-4 py-3 backdrop-blur-sm">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2 text-sm text-primary-light">
                <span class="material-symbols-outlined animate-spin text-base">progress_activity</span>
                <span class="font-semibold">{{ waitStageLabel }}</span>
              </div>
              <div class="rounded-full bg-black/25 px-2.5 py-1 text-xs text-text-secondary">
                {{ waitElapsedLabel }}
              </div>
            </div>
            <div class="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs">
              <p class="text-text-secondary">{{ waitMilestoneSummary }}</p>
              <p class="text-primary/90">{{ waitRemainingLabel }}</p>
            </div>
            <div class="mt-2 flex flex-wrap gap-1.5">
              <span
                v-for="item in waitMilestones"
                :key="item.key"
                class="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px]"
                :class="item.status === 'done'
                  ? 'bg-emerald-500/18 text-emerald-200'
                  : item.status === 'active'
                    ? 'bg-primary/22 text-primary-light'
                    : 'bg-white/8 text-text-secondary'"
              >
                <span class="h-1.5 w-1.5 rounded-full" :class="item.status === 'pending' ? 'bg-white/30' : 'bg-current'"></span>
                {{ item.label }}
              </span>
            </div>
            <p class="mt-2 text-xs text-text-secondary">{{ activeWaitHint }}</p>
            <p v-if="currentThinkingAgentName" class="mt-1 text-xs text-primary/90">
              {{ languageTag().startsWith('zh') ? `当前：${currentThinkingAgentName}` : `Current: ${currentThinkingAgentName}` }}
            </p>
            <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10">
              <div class="h-full w-1/3 animate-pulse rounded-full bg-primary/55"></div>
            </div>
          </div>

          <div v-for="agent in thinkingAgentNames" :key="agent.id" class="flex justify-start">
            <div class="w-full max-w-[88%] rounded-3xl bg-white/8 px-4 py-3">
              <div class="flex items-center gap-2 text-sm text-primary-light">
                <span class="material-symbols-outlined animate-spin text-base">progress_activity</span>
                <span class="font-semibold">{{ agent.name }}</span>
              </div>
              <p class="mt-1 text-xs text-text-secondary">
                {{ languageTag().startsWith('zh') ? '正在调用工具、检索信息并组织回答…' : 'Calling tools, retrieving evidence, and composing response…' }}
              </p>
              <div class="mt-2 space-y-1.5">
                <div class="h-2 w-11/12 rounded-full bg-white/10"></div>
                <div class="h-2 w-8/12 rounded-full bg-white/10"></div>
              </div>
            </div>
          </div>
        </div>

        <div class="relative px-4 pb-4 pt-2">
          <div v-if="selectedAttachments.length" class="mb-3 flex flex-wrap gap-2">
            <div
              v-for="att in selectedAttachments"
              :key="att.id"
              class="group relative overflow-hidden rounded-xl bg-primary/12"
            >
              <img :src="att.previewUrl" :alt="att.name" class="h-16 w-24 object-cover" />
              <button
                class="absolute right-1 top-1 rounded bg-black/60 p-0.5 text-white opacity-0 transition-opacity group-hover:opacity-100"
                @click="removeAttachment(att.id)"
              >
                <span class="material-symbols-outlined text-sm">close</span>
              </button>
            </div>
          </div>

          <div ref="composerRef" class="relative rounded-[28px] bg-black/34 p-3 shadow-[0_10px_28px_rgba(0,0,0,0.22)] backdrop-blur-xl">
            <div class="mb-2 flex flex-wrap items-center gap-2">
              <span class="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">{{ t('chatHub.composer.specialists') }}</span>
              <button
                v-for="agent in quickMentionAgents"
                :key="agent.id"
                class="shrink-0 rounded-full bg-white/12 px-3 py-1 text-xs text-primary hover:bg-white/20"
                @click="appendMention(agent.id)"
              >
                @{{ agent.id }}
              </button>
              <button
                v-if="mentionableAgents.length > quickMentionAgents.length"
                type="button"
                class="shrink-0 rounded-full bg-white/10 px-3 py-1 text-xs text-text-secondary hover:bg-white/20 hover:text-white"
                @click="showCollabPanel = true"
              >
                +{{ mentionableAgents.length - quickMentionAgents.length }}
              </button>
              <button
                v-if="knowledgeEnabled"
                type="button"
                class="inline-flex items-center gap-1 rounded-full bg-white/12 px-3 py-1 text-xs text-primary-light hover:bg-white/18"
                @click="disableKnowledge"
              >
                <span class="material-symbols-outlined text-sm">library_books</span>
                {{ knowledgeChipLabel }}
                <span class="material-symbols-outlined text-sm">close</span>
              </button>
            </div>

            <div class="relative">
              <textarea
                ref="textareaRef"
                v-model="inputMessage"
                rows="4"
                :placeholder="t('chatHub.inputPlaceholder')"
                class="w-full rounded-2xl bg-white/[0.04] px-4 py-3 text-sm text-white placeholder-text-secondary outline-none transition-colors focus:bg-white/[0.08] resize-none"
                @keydown="handleTextareaKeydown"
                @compositionstart="handleCompositionStart"
                @compositionend="handleCompositionEnd"
                @paste="handleTextareaPaste"
                @input="handleTextareaInput"
                @click="handleTextareaInput"
              ></textarea>

              <div
                v-if="showMentionMenu"
                class="absolute bottom-[calc(100%+10px)] left-0 z-30 w-full max-w-sm overflow-hidden rounded-xl border border-white/15 bg-surface/95 shadow-2xl"
              >
                <button
                  v-for="(agent, idx) in mentionSuggestions"
                  :key="agent.id"
                  class="flex w-full items-start gap-3 border-b border-white/5 px-3 py-2 text-left transition-colors last:border-b-0"
                  :class="idx === mentionActiveIndex ? 'bg-primary/20' : 'hover:bg-white/10'"
                  @click="selectMention(agent)"
                >
                  <div class="pt-0.5 text-primary">@</div>
                  <div class="min-w-0">
                    <p class="truncate text-sm font-semibold text-white">{{ agent.name }}</p>
                    <p class="truncate text-xs text-text-secondary">@{{ agent.id }} · {{ agent.role }}</p>
                  </div>
                </button>
              </div>

              <div
                v-if="showCollabPanel"
                ref="collabPanelRef"
                class="absolute bottom-[calc(100%+10px)] right-0 z-30 w-full max-w-md rounded-xl border border-white/15 bg-surface/95 p-4 shadow-2xl"
              >
                <h4 class="text-sm font-semibold text-white">{{ t('chatHub.collabConfig') }}</h4>
                <div class="mt-3 space-y-3">
                  <label class="flex items-center gap-2 text-sm text-text-primary">
                    <input
                      v-model="knowledgeEnabled"
                      type="checkbox"
                      class="h-4 w-4 rounded border-white/20 bg-black/30 text-primary focus:ring-primary/40"
                    />
                    <span>{{ t('chatHub.knowledge.enabled') }}</span>
                  </label>

                  <div>
                    <label class="mb-1 block text-xs font-bold uppercase tracking-wider text-text-secondary">
                      {{ t('chatHub.knowledge.scope') }}
                    </label>
                    <select
                      v-model="knowledgeCategory"
                      :disabled="!knowledgeEnabled"
                      class="control-select w-full disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <option v-for="option in knowledgeOptions" :key="option.value" :value="option.value">
                        {{ option.label }}
                      </option>
                    </select>
                  </div>

                  <div>
                    <p class="mb-1 text-xs font-bold uppercase tracking-wider text-text-secondary">{{ t('chatHub.participants') }}</p>
                    <div class="max-h-32 overflow-y-auto space-y-1 pr-1">
                      <div
                        v-for="agent in agents"
                        :key="agent.id"
                        class="rounded-lg border border-white/10 bg-white/5 px-2 py-1.5 text-xs"
                      >
                        <span class="font-semibold text-white">{{ agent.name }}</span>
                        <span class="text-text-secondary"> · @{{ agent.id }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <input
              ref="fileInputRef"
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              multiple
              class="hidden"
              @change="onAttachmentSelected"
            />

            <div class="mt-3 flex items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <button
                  class="icon-btn h-11 w-11 shrink-0 border-0 bg-white/10 hover:bg-white/15"
                  :title="t('chatHub.collabConfig')"
                  @click="showCollabPanel = !showCollabPanel"
                >
                  <span class="material-symbols-outlined text-base">tune</span>
                </button>

                <button
                  class="icon-btn h-11 w-11 shrink-0 border-0 bg-white/10 hover:bg-white/15"
                  :title="t('chatHub.attachImage')"
                  @click="triggerAttachmentPicker"
                >
                  <span class="material-symbols-outlined text-base">image</span>
                </button>

                <p class="hidden text-[11px] text-text-tertiary sm:block">
                  {{ t('chatHub.composer.hint') }}
                </p>
              </div>

              <button
                class="page-primary-btn h-11 shrink-0"
                :disabled="!canSend"
                @click="sendMessage"
              >
                <span class="material-symbols-outlined text-base">send</span>
                {{ sendLabel }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { marked } from 'marked';
import { useI18n } from '@/i18n';
import { wsUrl } from '@/config/api';
import { appendTokenToUrl, getAccessToken } from '@/services/authHeaders';
import { useAuthStore } from '@/stores/auth';

marked.setOptions({
  gfm: true,
  breaks: true,
  pedantic: false,
});

const { t, locale } = useI18n();
const authStore = useAuthStore();

const SESSION_STORAGE_KEY = 'magellan_expert_chat_sessions_v1';
const LAST_SESSION_KEY = 'magellan_expert_chat_last_session_v1';
const HISTORY_COLLAPSE_KEY = 'magellan_expert_chat_history_collapsed_v1';
const WAIT_METRICS_KEY = 'magellan_expert_chat_wait_metrics_v1';
const MAX_SESSION_MESSAGES = 120;
const WAIT_METRICS_SAMPLE_SIZE = 12;

const sessions = ref([]);
const activeSessionId = ref('');
const sessionId = ref('');
const inputMessage = ref('');
const messages = ref([]);
const agents = ref([]);
const thinkingAgentIds = ref([]);
const selectedAttachments = ref([]);
const showCollabPanel = ref(false);
const knowledgeEnabled = ref(false);
const knowledgeCategory = ref('all');
const historyCollapsed = ref(false);
const showAllSessions = ref(false);
const connected = ref(false);
const connecting = ref(false);

const messagesContainer = ref(null);
const composerRef = ref(null);
const collabPanelRef = ref(null);
const textareaRef = ref(null);
const fileInputRef = ref(null);
const mentionState = ref(null);
const mentionActiveIndex = ref(0);
const isComposing = ref(false);

const MAX_IMAGE_ATTACHMENTS = 3;
const MAX_IMAGE_BYTES = 4 * 1024 * 1024;

const maxReconnectAttempts = 5;
const reconnectBaseDelayMs = 1500;
let socket = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let isUnmounted = false;
let suppressReconnectOnce = false;
let authRefreshInFlight = false;
let waitTicker = null;
let waitHintTicker = null;
let finishTurnTimer = null;

const turnInFlight = ref(false);
const turnStartedAt = ref(0);
const waitElapsedSec = ref(0);
const waitHintIndex = ref(0);
const turnStage = ref('idle');
const delegationActive = ref(false);
const delegationEverStarted = ref(false);
const turnGotAssistantMessage = ref(false);
const turnCurrentThinkingAgentId = ref('');
const turnRoutingMode = ref('');
const waitDurationStats = ref({ direct: [], delegated: [] });
const markdownRenderCache = new Map();
const reportDetectCache = new Map();

function sessionExpiredMessage() {
  return String(locale.value || '').startsWith('zh')
    ? '登录已过期，请重新登录。'
    : 'Session expired. Please log in again.';
}

const knowledgeOptions = computed(() => [
  { value: 'all', label: t('chatHub.knowledge.all') },
  { value: 'general', label: t('chatHub.knowledge.general') },
  { value: 'financial', label: t('chatHub.knowledge.financial') },
  { value: 'market', label: t('chatHub.knowledge.market') },
  { value: 'legal', label: t('chatHub.knowledge.legal') },
]);

const mentionableAgents = computed(() => agents.value.filter((agent) => agent.id !== 'leader'));
const quickMentionAgents = computed(() => mentionableAgents.value.slice(0, 3));
const mentionSuggestions = computed(() => {
  const state = mentionState.value;
  if (!state) return [];
  const query = String(state.query || '').trim().toLowerCase();
  const list = mentionableAgents.value.filter((agent) => {
    if (!query) return true;
    return (
      String(agent.id || '').toLowerCase().includes(query) ||
      String(agent.name || '').toLowerCase().includes(query) ||
      String(agent.role || '').toLowerCase().includes(query)
    );
  });
  return list.slice(0, 8);
});
const showMentionMenu = computed(() => mentionSuggestions.value.length > 0 && !!mentionState.value);

const thinkingAgentNames = computed(() => {
  return thinkingAgentIds.value
    .map((id) => agents.value.find((agent) => agent.id === id))
    .filter(Boolean);
});

const currentThinkingAgentName = computed(() => {
  if (!turnCurrentThinkingAgentId.value) return '';
  const target = agents.value.find((agent) => agent.id === turnCurrentThinkingAgentId.value);
  return target?.name || turnCurrentThinkingAgentId.value;
});

const waitHints = computed(() => {
  const zh = languageTag().startsWith('zh');
  if (zh) {
    return [
      '正在并行检索工具结果与外部信息',
      '正在交叉验证关键信号与风险点',
      '正在整理可执行结论与下一步建议',
    ];
  }
  return [
    'Running parallel tool retrieval and source checks',
    'Cross-validating key signals and risk factors',
    'Composing actionable conclusions and next steps',
  ];
});

const activeWaitHint = computed(() => {
  const hints = waitHints.value;
  if (!hints.length) return '';
  return hints[waitHintIndex.value % hints.length];
});

const waitStageLabel = computed(() => {
  const zh = languageTag().startsWith('zh');
  if (!turnInFlight.value) return '';
  if (turnStage.value === 'routing') return zh ? 'Leader 正在拆解问题' : 'Leader is routing the request';
  if (turnStage.value === 'delegating') return zh ? '正在委派专家并行分析' : 'Delegating specialists in parallel';
  if (turnStage.value === 'collecting') return zh ? '专家意见回收中' : 'Collecting specialist outputs';
  if (turnStage.value === 'summarizing') return zh ? '正在汇总形成最终答复' : 'Producing final synthesis';
  if (turnStage.value === 'responding') return zh ? '专家正在输出答复' : 'Agent is producing a response';
  return zh ? '正在分析中' : 'Analyzing';
});

const waitElapsedLabel = computed(() => {
  const sec = Math.max(0, Number(waitElapsedSec.value || 0));
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}m ${s}s`;
});

const waitStagePlan = computed(() => {
  const useDelegationFlow = isDelegationFlow();
  if (useDelegationFlow) return ['routing', 'delegating', 'collecting', 'summarizing', 'responding'];
  return ['routing', 'responding'];
});

const waitMilestones = computed(() => {
  const zh = languageTag().startsWith('zh');
  const labels = {
    routing: zh ? '拆解问题' : 'Routing',
    delegating: zh ? '委派专家' : 'Delegating',
    collecting: zh ? '回收观点' : 'Collecting',
    summarizing: zh ? '汇总结论' : 'Synthesizing',
    responding: zh ? '输出回复' : 'Responding',
  };
  const order = waitStagePlan.value;
  const activeIndex = Math.max(0, order.indexOf(turnStage.value));
  return order.map((key, idx) => ({
    key,
    label: labels[key] || key,
    status: idx < activeIndex ? 'done' : idx === activeIndex ? 'active' : 'pending',
  }));
});

const waitMilestoneSummary = computed(() => {
  const zh = languageTag().startsWith('zh');
  const total = waitMilestones.value.length || 1;
  const done = waitMilestones.value.filter((item) => item.status === 'done').length;
  const active = waitMilestones.value.some((item) => item.status === 'active') ? 1 : 0;
  const step = Math.min(total, Math.max(1, done + active));
  return zh ? `里程碑 ${step}/${total}` : `Milestone ${step}/${total}`;
});

const waitRemainingLabel = computed(() => {
  const zh = languageTag().startsWith('zh');
  const elapsed = Math.max(0, Number(waitElapsedSec.value || 0));
  const flow = currentFlowKey();
  const history = flow === 'delegated' ? waitDurationStats.value.delegated : waitDurationStats.value.direct;
  const fallback = flow === 'delegated' ? 70 : 25;
  const avg = Math.round(averageDuration(history));
  const smoothed = avg > 0
    ? Math.round(((avg * history.length) + (fallback * 2)) / (history.length + 2))
    : fallback;
  const total = Math.max(12, Math.min(3600, smoothed));
  const remain = Math.max(0, total - elapsed);
  if (remain <= 0) {
    return zh ? '接近完成，正在输出最后结果' : 'Almost done, finalizing output';
  }
  return zh ? `预计剩余 ${remain}s` : `Estimated ${remain}s left`;
});

const canSend = computed(() => (Boolean(inputMessage.value.trim()) || selectedAttachments.value.length > 0) && connected.value);

const connectionButtonLabel = computed(() => {
  if (connecting.value) return t('chatHub.connecting');
  return connected.value ? t('chatHub.connected') : t('chatHub.connect');
});

const sendLabel = computed(() => t('chatHub.send'));
const activeSessionTitle = computed(() => {
  const target = sessions.value.find((item) => item.id === activeSessionId.value);
  return target?.title || t('chatHub.sessionUntitled');
});
const knowledgeChipLabel = computed(() => {
  if (!knowledgeEnabled.value) return '';
  const option = knowledgeOptions.value.find((item) => item.value === knowledgeCategory.value);
  if (!option) return t('chatHub.knowledge.title');
  return `${t('chatHub.knowledge.title')} · ${option.label}`;
});
const historyToggleLabel = computed(() => {
  return historyCollapsed.value ? t('chatHub.expandHistory') : t('chatHub.collapseHistory');
});
const visibleSessions = computed(() => {
  if (showAllSessions.value) return sessions.value;
  return sessions.value.slice(0, 5);
});
const hasMoreSessions = computed(() => sessions.value.length > 5);
const starterPrompts = computed(() => [
  t('chatHub.starters.prompt1'),
  t('chatHub.starters.prompt2'),
  t('chatHub.starters.prompt3'),
  t('chatHub.starters.prompt4'),
  t('chatHub.starters.prompt5'),
]);

function languageTag() {
  return String(locale.value || 'zh-CN').startsWith('zh') ? 'zh-CN' : 'en-US';
}

function makeId(prefix = 'msg') {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
}

function nowIso() {
  return new Date().toISOString();
}

function safeClone(value) {
  try {
    return JSON.parse(JSON.stringify(value));
  } catch {
    return [];
  }
}

function normalizeWaitDurations(list) {
  if (!Array.isArray(list)) return [];
  return list
    .map((item) => Number(item))
    .filter((item) => Number.isFinite(item) && item >= 1 && item <= 3600)
    .slice(-WAIT_METRICS_SAMPLE_SIZE);
}

function loadWaitDurationStats() {
  try {
    const raw = localStorage.getItem(WAIT_METRICS_KEY);
    if (!raw) return { direct: [], delegated: [] };
    const parsed = JSON.parse(raw);
    return {
      direct: normalizeWaitDurations(parsed?.direct),
      delegated: normalizeWaitDurations(parsed?.delegated),
    };
  } catch {
    return { direct: [], delegated: [] };
  }
}

function persistWaitDurationStats() {
  try {
    localStorage.setItem(WAIT_METRICS_KEY, JSON.stringify(waitDurationStats.value));
  } catch {
    // ignore localStorage quota errors in PoC mode
  }
}

function isDelegationFlow() {
  return delegationEverStarted.value
    || delegationActive.value
    || ['delegating', 'collecting', 'summarizing'].includes(turnStage.value)
    || turnRoutingMode.value === 'leader';
}

function currentFlowKey() {
  return isDelegationFlow() ? 'delegated' : 'direct';
}

function averageDuration(list) {
  if (!Array.isArray(list) || list.length === 0) return 0;
  return list.reduce((sum, item) => sum + item, 0) / list.length;
}

function isConnectionSystemMessage(msg) {
  if (!msg || msg.type !== 'system') return false;
  const content = String(msg.content || '');
  if (!content) return false;
  return (
    content.includes('已连接专家群聊') ||
    content.includes('已断开专家群聊') ||
    content.includes('正在重连专家群聊') ||
    content.includes('Connected to expert chat') ||
    content.includes('Disconnected from expert chat') ||
    content.includes('Reconnecting to expert chat')
  );
}

function sanitizeMessages(list) {
  return (Array.isArray(list) ? list : []).filter((msg) => !isConnectionSystemMessage(msg));
}

function buildSessionPreview(sessionMessages) {
  const reversed = [...sessionMessages].reverse();
  const found = reversed.find((msg) => msg.role === 'assistant' || msg.role === 'user');
  return (found?.content || '').slice(0, 80);
}

function buildSessionTitle(sessionMessages) {
  const firstUser = sessionMessages.find((msg) => msg.role === 'user');
  if (!firstUser?.content) return t('chatHub.sessionUntitled');
  return String(firstUser.content).replace(/\s+/g, ' ').slice(0, 28);
}

function serializeMessages(sessionMessages) {
  return sanitizeMessages(sessionMessages).slice(-MAX_SESSION_MESSAGES).map((msg) => ({
    id: msg.id || makeId('msg'),
    type: msg.type || 'message',
    role: msg.role || 'user',
    speaker: msg.speaker || '',
    content: String(msg.content || ''),
    timestamp: msg.timestamp || nowIso(),
    level: msg.level || undefined,
    agent_id: msg.agentId || msg.agent_id || undefined,
    attachments: (msg.attachments || []).map((att) => ({
      id: att.id || makeId('att'),
      name: att.name || 'image',
      mimeType: att.mimeType || att.mime_type || '',
      size: Number(att.size || 0),
    })),
  }));
}

function persistSessions() {
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions.value));
  } catch {
    // ignore localStorage quota errors in PoC mode
  }
}

function loadSessions() {
  try {
    const raw = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => ({
        id: String(item.id || '').trim(),
        title: String(item.title || ''),
        preview: String(item.preview || ''),
        updatedAt: String(item.updatedAt || nowIso()),
        messages: Array.isArray(item.messages) ? item.messages : [],
      }))
      .filter((item) => item.id);
  } catch {
    return [];
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = messagesContainer.value;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    requestAnimationFrame(() => {
      const node = messagesContainer.value;
      if (!node) return;
      node.scrollTop = node.scrollHeight;
      requestAnimationFrame(() => {
        const latest = messagesContainer.value;
        if (!latest) return;
        latest.scrollTop = latest.scrollHeight;
      });
    });
  });
}

function updateActiveSessionStore() {
  if (!activeSessionId.value) return;

  const serialized = serializeMessages(messages.value);
  const updatedSession = {
    id: activeSessionId.value,
    title: buildSessionTitle(serialized),
    preview: buildSessionPreview(serialized),
    updatedAt: nowIso(),
    messages: serialized,
  };

  const idx = sessions.value.findIndex((item) => item.id === activeSessionId.value);
  if (idx >= 0) {
    sessions.value[idx] = updatedSession;
  } else {
    sessions.value.unshift(updatedSession);
  }

  sessions.value = [...sessions.value].sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));
  persistSessions();
  localStorage.setItem(LAST_SESSION_KEY, activeSessionId.value);
}

function ensureSessionExists(targetId) {
  if (!targetId) return;
  if (sessions.value.some((item) => item.id === targetId)) return;
  sessions.value.unshift({
    id: targetId,
    title: t('chatHub.sessionUntitled'),
    preview: '',
    updatedAt: nowIso(),
    messages: [],
  });
  persistSessions();
}

function createSessionRecord() {
  const id = `chat_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
  const item = {
    id,
    title: t('chatHub.sessionUntitled'),
    preview: '',
    updatedAt: nowIso(),
    messages: [],
  };
  sessions.value.unshift(item);
  sessions.value = [...sessions.value];
  persistSessions();
  return item;
}

function setActiveSession(targetId) {
  if (!targetId) return;
  updateActiveSessionStore();

  const target = sessions.value.find((item) => item.id === targetId);
  if (!target) return;

  activeSessionId.value = target.id;
  localStorage.setItem(LAST_SESSION_KEY, target.id);
  messages.value = sanitizeMessages(safeClone(target.messages || []));
  clearSelectedAttachments();
  mentionState.value = null;
  mentionActiveIndex.value = 0;
  showCollabPanel.value = false;
  reconnectCurrentSession();
  scrollToBottom();
}

function createNewSession() {
  const item = createSessionRecord();
  activeSessionId.value = item.id;
  localStorage.setItem(LAST_SESSION_KEY, item.id);
  messages.value = [];
  sessionId.value = item.id;
  clearSelectedAttachments();
  mentionState.value = null;
  mentionActiveIndex.value = 0;
  showCollabPanel.value = false;
  showAllSessions.value = false;
  reconnectCurrentSession();
}

function toggleHistoryPanel() {
  historyCollapsed.value = !historyCollapsed.value;
}

function toggleSessionListMode() {
  showAllSessions.value = !showAllSessions.value;
}

function disableKnowledge() {
  knowledgeEnabled.value = false;
}

function sessionInitial(session) {
  const title = String(session?.title || '').trim();
  if (title) return title[0].toUpperCase();
  return '#';
}

function renameSession(targetId) {
  const target = sessions.value.find((item) => item.id === targetId);
  if (!target) return;
  const current = String(target.title || t('chatHub.sessionUntitled'));
  const next = window.prompt(t('chatHub.renameSessionPrompt'), current);
  if (next == null) return;
  const trimmed = String(next).trim();
  target.title = trimmed || t('chatHub.sessionUntitled');
  target.updatedAt = nowIso();
  sessions.value = [...sessions.value].sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));
  persistSessions();
}

function deleteSession(targetId) {
  const target = sessions.value.find((item) => item.id === targetId);
  if (!target) return;
  const confirmed = window.confirm(t('chatHub.deleteSessionConfirm', { title: target.title || t('chatHub.sessionUntitled') }));
  if (!confirmed) return;

  const nextSessions = sessions.value.filter((item) => item.id !== targetId);
  sessions.value = nextSessions;

  if (activeSessionId.value === targetId) {
    if (nextSessions.length === 0) {
      const created = createSessionRecord();
      activeSessionId.value = created.id;
      sessionId.value = created.id;
      messages.value = [];
    } else {
      const fallback = nextSessions[0];
      activeSessionId.value = fallback.id;
      sessionId.value = fallback.id;
      messages.value = safeClone(fallback.messages || []);
    }
    localStorage.setItem(LAST_SESSION_KEY, activeSessionId.value);
    reconnectCurrentSession();
  }

  persistSessions();
}

function buildResumeHistory() {
  return messages.value
    .filter((msg) => msg.role === 'user' || msg.role === 'assistant')
    .slice(-40)
    .map((msg) => ({
      role: msg.role,
      speaker: msg.speaker,
      content: String(msg.content || ''),
      timestamp: msg.timestamp || nowIso(),
      agent_id: msg.agentId || msg.agent_id || undefined,
    }));
}

function addSystemMessage(content, level = 'info') {
  messages.value.push({
    id: makeId('sys'),
    type: 'system',
    role: 'system',
    speaker: 'System',
    content,
    level,
    timestamp: nowIso(),
  });
  updateActiveSessionStore();
  scrollToBottom();
}

function addUserMessage(content, attachments = []) {
  messages.value.push({
    id: makeId('user'),
    type: 'message',
    role: 'user',
    speaker: t('chatHub.you'),
    content,
    attachments,
    timestamp: nowIso(),
  });
  updateActiveSessionStore();
  scrollToBottom();
}

function addAssistantMessage(agentId, agentName, content) {
  messages.value.push({
    id: makeId('agent'),
    type: 'message',
    role: 'assistant',
    agentId,
    speaker: agentName || agentId,
    content,
    timestamp: nowIso(),
  });
  turnGotAssistantMessage.value = true;
  turnStage.value = 'responding';
  updateActiveSessionStore();
  scrollToBottom();
  maybeFinishTurn(false);
}

function setThinking(agentId, isThinking) {
  if (!agentId) return;
  if (isThinking) {
    if (!thinkingAgentIds.value.includes(agentId)) {
      thinkingAgentIds.value = [...thinkingAgentIds.value, agentId];
    }
    turnCurrentThinkingAgentId.value = agentId;
    turnStage.value = delegationActive.value ? 'collecting' : 'responding';
    scrollToBottom();
    return;
  }
  thinkingAgentIds.value = thinkingAgentIds.value.filter((id) => id !== agentId);
  if (turnCurrentThinkingAgentId.value === agentId) {
    turnCurrentThinkingAgentId.value = '';
  }
  scrollToBottom();
  maybeFinishTurn(false);
}

function clearThinking() {
  thinkingAgentIds.value = [];
  turnCurrentThinkingAgentId.value = '';
}

function parseIncoming(event) {
  try {
    return JSON.parse(event.data);
  } catch {
    return null;
  }
}

function clearWaitTimers() {
  if (waitTicker) {
    clearInterval(waitTicker);
    waitTicker = null;
  }
  if (waitHintTicker) {
    clearInterval(waitHintTicker);
    waitHintTicker = null;
  }
  if (finishTurnTimer) {
    clearTimeout(finishTurnTimer);
    finishTurnTimer = null;
  }
}

function startTurnWaiting() {
  clearWaitTimers();
  turnInFlight.value = true;
  turnStartedAt.value = Date.now();
  waitElapsedSec.value = 0;
  waitHintIndex.value = 0;
  turnStage.value = 'routing';
  delegationActive.value = false;
  delegationEverStarted.value = false;
  turnGotAssistantMessage.value = false;
  turnCurrentThinkingAgentId.value = '';
  turnRoutingMode.value = '';

  waitTicker = window.setInterval(() => {
    waitElapsedSec.value = Math.floor((Date.now() - turnStartedAt.value) / 1000);
  }, 1000);

  waitHintTicker = window.setInterval(() => {
    waitHintIndex.value += 1;
  }, 2800);
}

function stopTurnWaiting() {
  clearWaitTimers();
  turnInFlight.value = false;
  waitElapsedSec.value = 0;
  turnStage.value = 'idle';
  delegationActive.value = false;
  delegationEverStarted.value = false;
  turnGotAssistantMessage.value = false;
  turnCurrentThinkingAgentId.value = '';
  turnRoutingMode.value = '';
}

function recordCompletedTurnDuration() {
  if (!turnStartedAt.value) return;
  if (!turnGotAssistantMessage.value) return;
  const elapsed = Math.max(1, Math.round((Date.now() - turnStartedAt.value) / 1000));
  const key = currentFlowKey();
  const next = {
    direct: normalizeWaitDurations(waitDurationStats.value.direct),
    delegated: normalizeWaitDurations(waitDurationStats.value.delegated),
  };
  next[key] = normalizeWaitDurations([...(next[key] || []), elapsed]);
  waitDurationStats.value = next;
  persistWaitDurationStats();
}

function maybeFinishTurn(force = false) {
  if (force) {
    stopTurnWaiting();
    return;
  }
  if (!turnInFlight.value) return;
  if (delegationActive.value) return;
  if (thinkingAgentIds.value.length > 0) return;
  if (!turnGotAssistantMessage.value) return;

  if (finishTurnTimer) clearTimeout(finishTurnTimer);
  finishTurnTimer = window.setTimeout(() => {
    finishTurnTimer = null;
    if (!delegationActive.value && thinkingAgentIds.value.length === 0 && turnGotAssistantMessage.value) {
      recordCompletedTurnDuration();
      stopTurnWaiting();
    }
  }, 420);
}

function parseJwtPayload(token) {
  try {
    const parts = String(token || '').split('.');
    if (parts.length < 2) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const normalized = base64 + '='.repeat((4 - (base64.length % 4 || 4)) % 4);
    return JSON.parse(atob(normalized));
  } catch {
    return null;
  }
}

function isAccessTokenExpired(token, skewSeconds = 30) {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') return true;
  const nowSec = Math.floor(Date.now() / 1000);
  return payload.exp <= nowSec + skewSeconds;
}

async function ensureValidAccessToken() {
  const token = getAccessToken();
  if (token && !isAccessTokenExpired(token)) return true;

  if (authRefreshInFlight) {
    // Wait for the ongoing refresh result.
    for (let i = 0; i < 20; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      const latest = getAccessToken();
      if (latest && !isAccessTokenExpired(latest)) return true;
    }
    return false;
  }

  authRefreshInFlight = true;
  try {
    const refreshed = await authStore.refreshAccessToken();
    return Boolean(refreshed);
  } catch {
    return false;
  } finally {
    authRefreshInFlight = false;
  }
}

function sendStartSession() {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(
    JSON.stringify({
      type: 'start_session',
      session_id: activeSessionId.value,
      history: buildResumeHistory(),
      language: languageTag(),
      knowledge: {
        enabled: knowledgeEnabled.value,
        category: knowledgeCategory.value,
      },
    })
  );
}

function handleServerMessage(event) {
  const data = parseIncoming(event);
  if (!data || !data.type) return;

  switch (data.type) {
    case 'session_started':
      sessionId.value = data.session_id || sessionId.value;
      agents.value = Array.isArray(data.agents) ? data.agents : agents.value;
      break;

    case 'session_ready':
      sessionId.value = data.session_id || sessionId.value;
      if (data.session_id && data.session_id !== activeSessionId.value) {
        ensureSessionExists(data.session_id);
        activeSessionId.value = data.session_id;
        localStorage.setItem(LAST_SESSION_KEY, data.session_id);
      }
      agents.value = Array.isArray(data.agents) ? data.agents : agents.value;
      updateActiveSessionStore();
      break;

    case 'route_decided':
      turnRoutingMode.value = data.mode || '';
      turnStage.value = 'routing';
      break;

    case 'delegation_started':
      delegationActive.value = true;
      delegationEverStarted.value = true;
      turnStage.value = 'delegating';
      break;

    case 'delegation_finished':
      delegationActive.value = false;
      turnStage.value = 'summarizing';
      maybeFinishTurn(false);
      break;

    case 'agent_thinking':
      setThinking(data.agent_id, true);
      break;

    case 'agent_message':
      setThinking(data.agent_id, false);
      addAssistantMessage(data.agent_id, data.agent_name, data.content || '');
      break;

    case 'error':
      addSystemMessage(data.message || 'Unknown error', 'error');
      stopTurnWaiting();
      break;

    case 'pong':
      break;

    default:
      addSystemMessage(`${t('chatHub.system.unsupported')}: ${data.type}`);
  }
}

function scheduleReconnect() {
  if (isUnmounted || reconnectAttempts >= maxReconnectAttempts) return;
  reconnectAttempts += 1;
  const delay = reconnectBaseDelayMs * reconnectAttempts;
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connectWebSocket();
  }, delay);
}

async function connectWebSocket() {
  if (connecting.value) return;

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  connecting.value = true;
  clearThinking();
  stopTurnWaiting();

  const tokenOk = await ensureValidAccessToken();
  if (!tokenOk) {
    connecting.value = false;
    connected.value = false;
    addSystemMessage(sessionExpiredMessage(), 'error');
    return;
  }

  try {
    socket = new WebSocket(appendTokenToUrl(wsUrl('/ws/expert-chat')));
  } catch (error) {
    connecting.value = false;
    addSystemMessage(String(error?.message || error), 'error');
    scheduleReconnect();
    return;
  }

  socket.onopen = () => {
    connecting.value = false;
    connected.value = true;
    reconnectAttempts = 0;
    sendStartSession();
  };

  socket.onmessage = handleServerMessage;

  socket.onerror = () => {
    addSystemMessage(t('connection.error'), 'error');
    stopTurnWaiting();
  };

  socket.onclose = async (event) => {
    connecting.value = false;
    connected.value = false;
    clearThinking();
    stopTurnWaiting();

    if (suppressReconnectOnce) {
      suppressReconnectOnce = false;
      return;
    }

    // 1008 is policy violation, backend uses it for auth failure.
    if (event?.code === 1008) {
      const refreshed = await ensureValidAccessToken();
      if (refreshed) {
        socket = null;
        connectWebSocket();
        return;
      }
      addSystemMessage(sessionExpiredMessage(), 'error');
      return;
    }

    socket = null;
    scheduleReconnect();
  };
}

function closeWebSocket(manual = false) {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  if (manual) suppressReconnectOnce = true;

  if (socket) {
    socket.onopen = null;
    socket.onmessage = null;
    socket.onerror = null;
    socket.onclose = null;
    try {
      socket.close();
    } catch {
      // ignore close errors
    }
    socket = null;
  }

  connected.value = false;
  connecting.value = false;
  clearThinking();
  stopTurnWaiting();
}

function reconnectCurrentSession() {
  closeWebSocket(true);
  connectWebSocket();
}

function sendMessage() {
  if (!canSend.value || !socket || socket.readyState !== WebSocket.OPEN) return;

  const content = inputMessage.value.trim();
  const attachmentsPayload = selectedAttachments.value.map((att) => ({
    name: att.name,
    mime_type: att.mimeType,
    data_base64: att.dataBase64,
    size: att.size,
  }));

  if (!content && attachmentsPayload.length === 0) return;

  addUserMessage(
    content || t('chatHub.imageOnlyMessage'),
    selectedAttachments.value.map((att) => ({
      id: att.id,
      name: att.name,
      mimeType: att.mimeType,
      size: att.size,
      previewUrl: att.dataBase64 ? `data:${att.mimeType || 'image/png'};base64,${att.dataBase64}` : att.previewUrl,
    }))
  );

  inputMessage.value = '';
  mentionState.value = null;
  mentionActiveIndex.value = 0;

  socket.send(
    JSON.stringify({
      type: 'user_message',
      content,
      attachments: attachmentsPayload,
      language: languageTag(),
      knowledge: {
        enabled: knowledgeEnabled.value,
        category: knowledgeCategory.value,
      },
    })
  );

  startTurnWaiting();

  clearSelectedAttachments();
}

function appendMention(agentId) {
  insertMentionToken(String(agentId || '').trim());
}

function detectMentionState() {
  const el = textareaRef.value;
  if (!el) {
    mentionState.value = null;
    return;
  }

  const value = inputMessage.value || '';
  const caret = el.selectionStart ?? value.length;
  const beforeCaret = value.slice(0, caret);
  const match = beforeCaret.match(/(^|\s)@([A-Za-z0-9_-]*)$/);

  if (!match) {
    mentionState.value = null;
    mentionActiveIndex.value = 0;
    return;
  }

  const token = match[2] || '';
  mentionState.value = {
    start: caret - token.length - 1,
    end: caret,
    query: token,
  };
  mentionActiveIndex.value = 0;
}

function insertMentionToken(agentId) {
  if (!agentId) return;

  const value = inputMessage.value || '';
  const el = textareaRef.value;
  const caret = el?.selectionStart ?? value.length;
  const state = mentionState.value;

  if (state && Number.isInteger(state.start) && Number.isInteger(state.end)) {
    const nextValue = `${value.slice(0, state.start)}@${agentId} ${value.slice(state.end)}`;
    inputMessage.value = nextValue;
    mentionState.value = null;
    mentionActiveIndex.value = 0;

    nextTick(() => {
      if (!el) return;
      const position = state.start + agentId.length + 2;
      el.focus();
      el.setSelectionRange(position, position);
    });
    return;
  }

  const prefix = value && caret > 0 && !value.slice(0, caret).endsWith(' ') ? ' ' : '';
  const nextValue = `${value.slice(0, caret)}${prefix}@${agentId} ${value.slice(caret)}`;
  inputMessage.value = nextValue;

  nextTick(() => {
    if (!el) return;
    const position = caret + prefix.length + agentId.length + 2;
    el.focus();
    el.setSelectionRange(position, position);
  });
}

function selectMention(agent) {
  if (!agent?.id) return;
  insertMentionToken(agent.id);
}

function applyStarterPrompt(prompt) {
  inputMessage.value = String(prompt || '').trim();
  nextTick(() => {
    const el = textareaRef.value;
    if (!el) return;
    el.focus();
    const pos = inputMessage.value.length;
    el.setSelectionRange(pos, pos);
    detectMentionState();
  });
}

function handleTextareaInput() {
  detectMentionState();
}

function handleCompositionStart() {
  isComposing.value = true;
}

function handleCompositionEnd() {
  isComposing.value = false;
  detectMentionState();
}

function handleTextareaKeydown(event) {
  if (event.isComposing || isComposing.value || event.keyCode === 229) {
    return;
  }

  if (showMentionMenu.value) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      mentionActiveIndex.value = (mentionActiveIndex.value + 1) % mentionSuggestions.value.length;
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      mentionActiveIndex.value = (mentionActiveIndex.value - 1 + mentionSuggestions.value.length) % mentionSuggestions.value.length;
      return;
    }
    if (event.key === 'Tab' || event.key === 'Enter') {
      event.preventDefault();
      const target = mentionSuggestions.value[mentionActiveIndex.value] || mentionSuggestions.value[0];
      if (target) selectMention(target);
      return;
    }
    if (event.key === 'Escape') {
      mentionState.value = null;
      mentionActiveIndex.value = 0;
      return;
    }
  }

  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

function triggerAttachmentPicker() {
  fileInputRef.value?.click();
}

function clearSelectedAttachments() {
  selectedAttachments.value.forEach((att) => {
    try {
      if (att.previewUrl && att.previewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(att.previewUrl);
      }
    } catch {
      // ignore revoke errors
    }
  });
  selectedAttachments.value = [];
  if (fileInputRef.value) fileInputRef.value.value = '';
}

function removeAttachment(attachmentId) {
  const target = selectedAttachments.value.find((att) => att.id === attachmentId);
  if (target?.previewUrl?.startsWith('blob:')) {
    try {
      URL.revokeObjectURL(target.previewUrl);
    } catch {
      // ignore
    }
  }
  selectedAttachments.value = selectedAttachments.value.filter((att) => att.id !== attachmentId);
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
}

async function appendImageAttachment(file) {
  if (!file) return false;

  if (selectedAttachments.value.length >= MAX_IMAGE_ATTACHMENTS) {
    addSystemMessage(t('chatHub.system.tooManyImages'), 'error');
    return false;
  }

  if (!String(file.type || '').startsWith('image/')) {
    addSystemMessage(t('chatHub.system.invalidImageType'), 'error');
    return false;
  }

  if (file.size > MAX_IMAGE_BYTES) {
    addSystemMessage(t('chatHub.system.imageTooLarge'), 'error');
    return false;
  }

  try {
    const dataUrl = await readFileAsDataUrl(file);
    const commaIndex = dataUrl.indexOf(',');
    const dataBase64 = commaIndex >= 0 ? dataUrl.slice(commaIndex + 1) : dataUrl;
    selectedAttachments.value.push({
      id: makeId('att'),
      name: file.name || `image_${selectedAttachments.value.length + 1}`,
      mimeType: file.type || 'image/png',
      size: file.size || 0,
      dataBase64,
      previewUrl: URL.createObjectURL(file),
    });
    return true;
  } catch {
    addSystemMessage(t('chatHub.system.imageReadFailed'), 'error');
    return false;
  }
}

async function onAttachmentSelected(event) {
  const files = Array.from(event.target?.files || []);
  if (!files.length) return;

  for (const file of files) {
    const added = await appendImageAttachment(file);
    if (!added && selectedAttachments.value.length >= MAX_IMAGE_ATTACHMENTS) {
      break;
    }
  }

  if (fileInputRef.value) fileInputRef.value.value = '';
}

async function handleTextareaPaste(event) {
  const clipboard = event.clipboardData;
  if (!clipboard) return;

  const items = Array.from(clipboard.items || []);
  const imageFiles = items
    .filter((item) => item.kind === 'file' && String(item.type || '').startsWith('image/'))
    .map((item) => item.getAsFile())
    .filter(Boolean);

  if (!imageFiles.length) return;

  const text = String(clipboard.getData('text/plain') || '').trim();
  if (!text) {
    event.preventDefault();
  }

  for (const file of imageFiles) {
    await appendImageAttachment(file);
    if (selectedAttachments.value.length >= MAX_IMAGE_ATTACHMENTS) break;
  }
}

function looksLikeTabularLine(line) {
  return String(line || '').includes('\t');
}

function markdownEscapeTableCell(value) {
  return String(value || '').replaceAll('|', '\\|').trim();
}

function convertTabSeparatedBlocksToMarkdown(text) {
  const lines = String(text || '').split('\n');
  const out = [];
  let index = 0;

  while (index < lines.length) {
    if (!looksLikeTabularLine(lines[index])) {
      out.push(lines[index]);
      index += 1;
      continue;
    }

    const block = [];
    while (index < lines.length && looksLikeTabularLine(lines[index])) {
      block.push(lines[index]);
      index += 1;
    }

    const rows = block
      .map((line) => line.split(/\t+/).map((cell) => markdownEscapeTableCell(cell)))
      .filter((cells) => cells.length >= 2 && cells.some((cell) => cell.length > 0));

    if (rows.length < 2) {
      out.push(...block);
      continue;
    }

    const width = rows.reduce((max, row) => Math.max(max, row.length), 2);
    const normalized = rows.map((row) => {
      const next = row.slice(0, width);
      while (next.length < width) next.push('');
      return next;
    });

    const header = normalized[0];
    const divider = Array.from({ length: width }, () => '---');
    out.push(`| ${header.join(' | ')} |`);
    out.push(`| ${divider.join(' | ')} |`);
    normalized.slice(1).forEach((row) => {
      out.push(`| ${row.join(' | ')} |`);
    });
  }

  return out.join('\n');
}

function convertNumberedSectionsToHeadings(text) {
  return String(text || '').replace(/(^|\n)(\d+)\.\s+([^\n#].+)/g, (_, lead, idx, title) => `${lead}## ${idx}. ${title.trim()}`);
}

function normalizeIndentedListLines(text) {
  const lines = String(text || '').split('\n');
  let inFence = false;

  return lines
    .map((line) => {
      const trimmed = line.trim();
      if (/^```/.test(trimmed)) {
        inFence = !inFence;
        return line;
      }
      if (inFence) return line;

      let match = line.match(/^\s{2,}([*-])\s+(.+)$/);
      if (match) return `${match[1]} ${match[2].trim()}`;

      match = line.match(/^\s{2,}(\d+\.)\s+(.+)$/);
      if (match) return `${match[1]} ${match[2].trim()}`;

      match = line.match(/^\s{2,}[•·]\s+(.+)$/);
      if (match) return `- ${match[1].trim()}`;

      return line;
    })
    .join('\n');
}

function stripStandaloneHorizontalRules(text) {
  const lines = String(text || '').split('\n');
  const output = [];
  let inFence = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (/^```/.test(trimmed)) {
      inFence = !inFence;
      output.push(line);
      continue;
    }

    if (!inFence && /^[-*_]{3,}$/.test(trimmed)) {
      if (output.length && output[output.length - 1].trim() !== '') {
        output.push('');
      }
      continue;
    }

    output.push(line);
  }

  return output.join('\n').replace(/\n{3,}/g, '\n\n');
}

function convertRiskLinesToCallout(text) {
  const lines = String(text || '').split('\n');
  return lines
    .map((line) => {
      const trimmed = line.trim();
      if (!trimmed) return line;
      if (/^⚠️/.test(trimmed)) return `> ${trimmed}`;
      if (/^(风险提示|Risk Warning)\s*[:：]?\s*$/i.test(trimmed)) return `> **${trimmed}**`;
      return line;
    })
    .join('\n');
}

function convertKeyValueLinesToList(text) {
  const lines = String(text || '').split('\n');
  const converted = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      converted.push(line);
      continue;
    }

    if (/^(\s*[-*]|\s*\d+\.)\s+/.test(trimmed) || /^#{1,6}\s+/.test(trimmed) || /^\|/.test(trimmed) || /^>/.test(trimmed)) {
      converted.push(line);
      continue;
    }

    const kvMatch = trimmed.match(/^([A-Za-z0-9\u4e00-\u9fa5()/_\-\s]{2,28})[:：]\s*(.+)$/);
    if (!kvMatch) {
      converted.push(line);
      continue;
    }

    const key = kvMatch[1].trim();
    const value = kvMatch[2].trim();
    if (!value) {
      converted.push(line);
      continue;
    }
    converted.push(`- **${key}**: ${value}`);
  }

  return converted.join('\n');
}

function preprocessReportMarkdown(content) {
  let text = String(content || '').replace(/\r\n/g, '\n');
  text = convertTabSeparatedBlocksToMarkdown(text);
  text = normalizeIndentedListLines(text);
  text = stripStandaloneHorizontalRules(text);
  text = convertNumberedSectionsToHeadings(text);
  text = convertRiskLinesToCallout(text);
  text = convertKeyValueLinesToList(text);
  return text;
}

function isReportLike(content) {
  const text = String(content || '');
  if (!text) return false;
  const cached = reportDetectCache.get(text);
  if (typeof cached === 'boolean') return cached;

  let score = 0;
  if (/(^|\n)\d+\.\s+.+/m.test(text)) score += 2;
  if ((text.match(/[:：]/g) || []).length >= 8) score += 1;
  if (/\t/.test(text)) score += 1;
  if (/(交易建议|关键价位|综合信号|置信度|风险提示|评分|预判|建议|Trend|Risk|Signal)/i.test(text)) score += 1;

  const result = score >= 3;
  reportDetectCache.set(text, result);
  if (reportDetectCache.size > 300) reportDetectCache.clear();
  return result;
}

function renderMarkdown(content) {
  if (!content) return '';
  const raw = String(content);
  const cacheKey = raw;
  const cached = markdownRenderCache.get(cacheKey);
  if (cached) return cached;

  try {
    const source = isReportLike(raw) ? preprocessReportMarkdown(raw) : raw;
    const html = marked.parse(source);
    markdownRenderCache.set(cacheKey, html);
    if (markdownRenderCache.size > 300) markdownRenderCache.clear();
    return html;
  } catch {
    return raw
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;');
  }
}

function formatTime(timestamp) {
  try {
    const date = timestamp ? new Date(timestamp) : new Date();
    return date.toLocaleTimeString(languageTag(), { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function formatSessionTime(timestamp) {
  try {
    const date = new Date(timestamp || Date.now());
    return date.toLocaleString(languageTag(), { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function handleGlobalClick(event) {
  const target = event.target;
  const panel = collabPanelRef.value;
  const composer = composerRef.value;
  if (showCollabPanel.value && panel && composer) {
    if (!panel.contains(target) && !composer.contains(target)) {
      showCollabPanel.value = false;
    }
  }
}

function handleMessageImageLoad() {
  scrollToBottom();
}

watch([knowledgeEnabled, knowledgeCategory, locale], () => {
  sendStartSession();
});

watch(
  () => messages.value.length,
  () => {
    scrollToBottom();
  }
);

onMounted(() => {
  waitDurationStats.value = loadWaitDurationStats();

  const storedCollapseState = localStorage.getItem(HISTORY_COLLAPSE_KEY);
  if (storedCollapseState === '1') {
    historyCollapsed.value = true;
  }

  sessions.value = loadSessions();

  let initial = localStorage.getItem(LAST_SESSION_KEY) || '';
  if (!initial || !sessions.value.find((item) => item.id === initial)) {
    if (sessions.value.length === 0) {
      const created = createSessionRecord();
      initial = created.id;
    } else {
      initial = sessions.value[0].id;
    }
  }

  activeSessionId.value = initial;
  const target = sessions.value.find((item) => item.id === initial);
  messages.value = sanitizeMessages(safeClone(target?.messages || []));
  sessionId.value = initial;

  reconnectCurrentSession();
  scrollToBottom();
  document.addEventListener('click', handleGlobalClick);
});

onUnmounted(() => {
  isUnmounted = true;
  updateActiveSessionStore();
  closeWebSocket(true);
  clearWaitTimers();
  clearSelectedAttachments();
  document.removeEventListener('click', handleGlobalClick);
});

watch(historyCollapsed, (next) => {
  localStorage.setItem(HISTORY_COLLAPSE_KEY, next ? '1' : '0');
});
</script>

<style scoped>
.analysis-markdown {
  font-size: 0.925rem;
  line-height: 1.75;
  color: rgba(235, 240, 255, 0.94);
}

.analysis-markdown :deep(h1),
.analysis-markdown :deep(h2),
.analysis-markdown :deep(h3) {
  margin-top: 0.9rem;
  margin-bottom: 0.45rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: #f8fbff;
}

.analysis-markdown.report-mode :deep(h2) {
  border-left: 3px solid rgba(94, 163, 255, 0.72);
  padding-left: 0.55rem;
}

.analysis-markdown :deep(p) {
  margin: 0.45rem 0;
}

.analysis-markdown :deep(ul),
.analysis-markdown :deep(ol) {
  margin: 0.45rem 0 0.6rem;
  padding-left: 1.1rem;
}

.analysis-markdown :deep(li) {
  margin: 0.22rem 0;
}

.analysis-markdown :deep(strong) {
  color: #ffffff;
}

.analysis-markdown :deep(blockquote) {
  margin: 0.65rem 0;
  border-left: 3px solid rgba(255, 195, 75, 0.72);
  background: rgba(255, 195, 75, 0.1);
  border-radius: 0.65rem;
  padding: 0.55rem 0.7rem;
  color: rgba(255, 233, 186, 0.95);
}

.analysis-markdown :deep(hr) {
  border: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.16);
  margin: 0.8rem 0;
}

.analysis-markdown :deep(code) {
  border-radius: 0.35rem;
  background: rgba(0, 0, 0, 0.28);
  padding: 0.1rem 0.35rem;
  font-size: 0.84em;
  word-break: break-word;
}

.analysis-markdown :deep(pre) {
  margin: 0.6rem 0;
  overflow-x: auto;
  border-radius: 0.75rem;
  background: rgba(0, 0, 0, 0.34);
  padding: 0.7rem 0.8rem;
}

.analysis-markdown :deep(table) {
  width: 100%;
  margin: 0.65rem 0;
  border-collapse: collapse;
  overflow: hidden;
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
}

.analysis-markdown :deep(th),
.analysis-markdown :deep(td) {
  padding: 0.42rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.analysis-markdown :deep(thead th) {
  background: rgba(94, 163, 255, 0.18);
  color: #f6faff;
  font-weight: 600;
}

.analysis-markdown :deep(tr:last-child td) {
  border-bottom: 0;
}
</style>
