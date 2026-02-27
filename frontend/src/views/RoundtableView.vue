<template>
  <div class="page-shell h-full min-h-0 overflow-hidden flex flex-col">
    <div class="page-header">
      <div>
        <h1 class="page-title page-title-gradient">{{ t('roundtable.title') }}</h1>
        <p class="page-subtitle">{{ t('roundtable.subtitle') }}</p>
      </div>
    </div>

    <!-- Start Discussion Panel -->
    <div v-if="!isDiscussionActive" class="section-card md:p-10 lg:p-12 flex-1 flex justify-center overflow-y-auto">
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
            <textarea
              v-model="discussionTopic"
              :placeholder="t('roundtable.startPanel.topicPlaceholder')"
              rows="3"
              class="w-full min-h-[108px] rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white placeholder-text-secondary transition-all resize-y focus:outline-none focus:border-primary/50 focus:bg-black/50"
            />
          </div>

          <!-- Experts Selection -->
          <div>
            <label class="block text-sm font-bold text-text-secondary mb-3 uppercase tracking-wider">
              {{ t('roundtable.startPanel.expertsLabel') }} ({{ selectedExperts.length }} {{ t('roundtable.startPanel.expertsSelected') }})
            </label>
            <!-- Selected experts tags -->
            <div class="flex flex-wrap gap-2 mb-3">
              <span
                v-for="expertId in selectedExperts"
                :key="expertId"
                class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/20 border border-primary/30 text-primary text-sm"
              >
                <span class="material-symbols-outlined text-base">{{ getExpertById(expertId)?.icon }}</span>
                {{ getExpertById(expertId)?.name }}
                <button @click="toggleExpert(expertId)" class="hover:text-white ml-1">
                  <span class="material-symbols-outlined text-base">close</span>
                </button>
              </span>
              <span v-if="selectedExperts.length === 0" class="text-text-secondary text-sm italic">
                Please select experts to join the discussion
              </span>
            </div>
            <!-- Dropdown multi-select -->
            <div class="relative" ref="expertDropdownRef">
              <button
                @click="showExpertDropdown = !showExpertDropdown"
                class="flex h-12 w-full items-center justify-between rounded-xl border border-white/10 bg-black/30 px-4 text-left text-white transition-all hover:border-primary/50"
              >
                <span class="text-text-secondary">Click to add or remove experts...</span>
                <span class="material-symbols-outlined text-text-secondary transition-transform" :class="showExpertDropdown ? 'rotate-180' : ''">
                  expand_more
                </span>
              </button>
              <!-- Dropdown list -->
              <div
                v-if="showExpertDropdown"
                class="absolute top-full left-0 right-0 mt-2 bg-gray-900/95 border border-white/10 rounded-xl shadow-2xl z-50 max-h-64 overflow-y-auto backdrop-blur-sm"
              >
                <div
                  v-for="expert in availableExperts"
                  :key="expert.id"
                  @click="toggleExpert(expert.id)"
                  :class="[
                    'flex items-center gap-3 px-4 py-3 cursor-pointer transition-all border-b border-white/5 last:border-b-0',
                    selectedExperts.includes(expert.id)
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-white/5 text-white'
                  ]"
                >
                  <span class="material-symbols-outlined text-xl">{{ expert.icon }}</span>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sm">{{ expert.name }}</div>
                    <div class="text-xs text-text-secondary line-clamp-1">{{ expert.description }}</div>
                  </div>
                  <span v-if="selectedExperts.includes(expert.id)" class="material-symbols-outlined text-primary">
                    check_circle
                  </span>
                </div>
              </div>
            </div>
            <!-- Note about Leader -->
            <p class="text-xs text-text-secondary mt-2 flex items-center gap-1">
              <span class="material-symbols-outlined text-sm text-primary">info</span>
              The discussion host is included automatically and does not need manual selection.
            </p>
          </div>

          <!-- Discussion Settings -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-bold text-text-secondary mb-2 uppercase tracking-wider">
                {{ t('roundtable.startPanel.roundsLabel') }}
              </label>
              <div class="relative">
                <select
                    v-model="maxRounds"
                    class="control-select w-full cursor-pointer appearance-none !h-12 !rounded-xl !bg-black/30 !text-white"
                >
                    <option :value="3">3 {{ t('roundtable.startPanel.rounds') }}</option>
                    <option :value="5">5 {{ t('roundtable.startPanel.rounds') }}</option>
                    <option :value="8">8 {{ t('roundtable.startPanel.rounds') }}</option>
                    <option :value="10">10 {{ t('roundtable.startPanel.rounds') }}</option>
                </select>
                <span class="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none">expand_more</span>
              </div>
            </div>
            <div class="rounded-xl border border-white/10 bg-black/20 p-4">
              <label class="block text-sm font-bold text-text-secondary mb-3 uppercase tracking-wider">
                Knowledge Base
              </label>
              <label class="flex items-center gap-2 text-sm text-text-primary mb-3">
                <input
                  type="checkbox"
                  v-model="useKnowledgeBase"
                  class="w-4 h-4 rounded border-white/20 bg-black/30 text-primary focus:ring-primary/50"
                />
                <span>Enable knowledge retrieval</span>
              </label>
              <div>
                <label class="block text-xs font-bold text-text-secondary mb-2 uppercase tracking-wider">
                  Retrieval Scope
                </label>
                <div class="relative">
                  <select
                    v-model="knowledgeCategory"
                    :disabled="!useKnowledgeBase"
                    class="control-select w-full cursor-pointer appearance-none !bg-black/30 !text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <option value="all">All Knowledge</option>
                    <option value="general">General Docs</option>
                    <option value="financial">Financial Docs</option>
                    <option value="market">Market Docs</option>
                    <option value="legal">Legal Docs</option>
                  </select>
                  <span class="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none">expand_more</span>
                </div>
              </div>
            </div>
          </div>

          <!-- History Reference Section -->
          <div class="border-t border-white/10 pt-6">
            <div class="flex items-center justify-between mb-4">
              <label class="flex items-center gap-2">
                <input
                  type="checkbox"
                  v-model="useHistoryReference"
                  class="w-4 h-4 rounded border-white/20 bg-black/30 text-primary focus:ring-primary/50"
                />
                <span class="text-sm font-bold text-text-secondary uppercase tracking-wider">
                  Continue from history
                </span>
              </label>
              <button
                v-if="useHistoryReference"
                @click="loadHistoryList"
                class="text-xs text-primary hover:text-primary-light flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-sm">refresh</span>
                Refresh List
              </button>
            </div>

            <div v-if="useHistoryReference" class="space-y-3">
              <!-- History List -->
              <div v-if="loadingHistory" class="text-center py-4">
                <span class="material-symbols-outlined animate-spin text-primary">progress_activity</span>
                <p class="text-sm text-text-secondary mt-2">Loading discussion history...</p>
              </div>

              <div v-else-if="historyList.length === 0" class="text-center py-4">
                <span class="material-symbols-outlined text-text-secondary text-3xl">history</span>
                <p class="text-sm text-text-secondary mt-2">No history found</p>
              </div>

              <div v-else class="max-h-48 overflow-y-auto space-y-2 pr-2">
                <div
                  v-for="history in historyList"
                  :key="history.id"
                  @click="selectHistoryReference(history)"
                  :class="[
                    'p-3 rounded-xl border cursor-pointer transition-all',
                    selectedHistoryRef?.id === history.id
                      ? 'border-primary bg-primary/10'
                      : 'border-white/10 bg-white/5 hover:bg-white/10'
                  ]"
                >
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex-1 min-w-0">
                      <h4 class="text-sm font-bold text-white truncate">{{ history.topic }}</h4>
                      <p class="text-xs text-text-secondary mt-1">
                        {{ formatHistoryDate(history.created_at) }} · {{ history.total_turns }} rounds
                      </p>
                    </div>
                    <span v-if="selectedHistoryRef?.id === history.id" class="text-primary">
                      <span class="material-symbols-outlined text-sm">check_circle</span>
                    </span>
                  </div>
                </div>
              </div>

              <!-- Selected History Preview -->
              <div v-if="selectedHistoryRef" class="mt-4 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
                <div class="flex items-start gap-2">
                  <span class="material-symbols-outlined text-amber-400 text-lg">lightbulb</span>
                  <div class="flex-1">
                    <p class="text-sm font-bold text-amber-400 mb-1">Continue from history</p>
                    <p class="text-xs text-text-secondary">
                      A new discussion will start using meeting minutes from "{{ selectedHistoryRef.topic }}".
                      Experts will review previous conclusions while being encouraged to propose new viewpoints and challenges.
                    </p>
                  </div>
                </div>
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
    <div v-else class="flex flex-1 min-h-0 flex-col gap-3 md:gap-6 xl:flex-row xl:gap-8">
      <transition
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0"
        enter-to-class="opacity-100"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div v-if="mobileControlPanelOpen" class="fixed inset-0 z-[80] xl:hidden">
          <button
            class="absolute inset-0 bg-black/70 backdrop-blur-sm"
            aria-label="Close discussion controls"
            @click="mobileControlPanelOpen = false"
          />
          <div class="absolute inset-y-0 right-0 w-[86vw] max-w-[360px] overflow-y-auto rounded-l-3xl bg-surface/92 p-4 shadow-2xl backdrop-blur-xl">
            <div class="mb-4 flex items-center justify-between">
              <h3 class="text-sm font-bold uppercase tracking-wider text-text-secondary">{{ t('roundtable.discussion.progress') }}</h3>
              <button class="icon-btn h-9 w-9 border-0 bg-white/10 hover:bg-white/15" @click="mobileControlPanelOpen = false">
                <span class="material-symbols-outlined text-base">close</span>
              </button>
            </div>

            <div class="section-card !p-4">
              <div class="space-y-4">
                <div>
                  <div class="mb-2 flex justify-between text-sm">
                    <span class="text-text-secondary font-medium">{{ t('roundtable.discussion.currentRound') }}</span>
                    <span class="text-white font-bold">{{ currentRound }} / {{ maxRounds }}</span>
                  </div>
                  <div class="h-2 w-full overflow-hidden rounded-full border border-white/5 bg-black/30">
                    <div
                      class="relative h-full rounded-full bg-gradient-to-r from-primary to-accent-cyan transition-all duration-500"
                      :style="{ width: (currentRound / maxRounds * 100) + '%' }"
                    >
                      <div class="absolute inset-0 animate-pulse bg-white/20"></div>
                    </div>
                  </div>
                </div>
                <div class="flex justify-between border-t border-white/5 pt-2 text-sm">
                  <span class="text-text-secondary">{{ t('roundtable.discussion.messageCount') }}</span>
                  <span class="text-white font-bold">{{ messages.length }}</span>
                </div>
              </div>
            </div>

            <div class="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
              <h3 class="mb-3 text-xs font-bold uppercase tracking-wider text-text-secondary">{{ t('roundtable.discussion.participants') }}</h3>
              <div class="space-y-2">
                <div
                  v-for="expert in activeExpertsList"
                  :key="`mobile_${expert.id}`"
                  class="flex items-center gap-3 rounded-xl border border-white/5 bg-white/5 p-2.5"
                >
                  <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/20 text-primary">
                    <span class="material-symbols-outlined text-base">{{ expert.icon }}</span>
                  </div>
                  <div class="min-w-0 flex-1">
                    <p class="truncate text-sm font-bold text-white">{{ expert.name }}</p>
                    <p class="truncate text-xs font-medium text-text-secondary">{{ expert.role }}</p>
                  </div>
                </div>
              </div>
            </div>

            <div class="mt-4 space-y-3">
              <button
                @click="generateMeetingSummary"
                :disabled="isGeneratingSummary || messages.length === 0"
                :class="[
                  'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl transition-all font-bold border',
                  isGeneratingSummary || messages.length === 0
                    ? 'bg-white/5 border-white/5 text-text-secondary cursor-not-allowed'
                    : 'bg-primary/10 border-primary/30 text-primary hover:bg-primary/20'
                ]"
              >
                <span class="material-symbols-outlined" :class="{ 'animate-spin': isGeneratingSummary }">
                  {{ isGeneratingSummary ? 'sync' : 'summarize' }}
                </span>
                {{ isGeneratingSummary ? 'Generating...' : 'Generate Minutes' }}
              </button>
              <div class="grid grid-cols-2 gap-3">
                <button
                  @click="stopDiscussion"
                  class="flex items-center justify-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 font-bold text-rose-400 transition-colors hover:bg-rose-500/20"
                >
                  <span class="material-symbols-outlined">stop</span>
                  Stop
                </button>
                <button
                  @click="exportDiscussion"
                  class="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3 font-bold text-text-primary transition-colors hover:bg-white/10"
                >
                  <span class="material-symbols-outlined">download</span>
                  Export
                </button>
              </div>
            </div>
          </div>
        </div>
      </transition>
      <!-- Left Sidebar: Experts Panel -->
      <div class="hidden w-full flex-col gap-6 xl:flex xl:w-80 xl:flex-shrink-0">
        <!-- Discussion Info -->
        <div class="section-card">
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
        <div class="section-card flex-1 overflow-y-auto">
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
            {{ isGeneratingSummary ? 'Generating...' : 'Generate Minutes' }}
          </button>
          <div class="grid grid-cols-2 gap-3">
              <button
                @click="stopDiscussion"
                class="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 hover:bg-rose-500/20 transition-colors font-bold"
              >
                <span class="material-symbols-outlined">stop</span>
                Stop
              </button>
              <button
                @click="exportDiscussion"
                class="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-text-primary hover:bg-white/10 transition-colors font-bold"
              >
                <span class="material-symbols-outlined">download</span>
                Export
              </button>
          </div>
        </div>
      </div>

      <!-- Main Discussion Area -->
      <div class="relative flex flex-1 flex-col overflow-hidden rounded-2xl glass-panel">
        <!-- Discussion Header -->
        <div class="px-4 py-4 border-b border-white/10 bg-white/5 backdrop-blur-md flex-shrink-0 md:px-8 md:py-5">
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
                'hidden sm:inline-flex text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider border shadow-[0_0_10px_rgba(0,0,0,0.2)]',
                discussionStatus === 'running' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-white/10 text-text-secondary border-white/10'
              ]"
            >
              {{ discussionStatus === 'running' ? t('roundtable.discussion.status.running') : t('roundtable.discussion.status.completed') }}
            </span>
            <button
              type="button"
              class="icon-btn ml-2 border-0 bg-white/10 hover:bg-white/15 xl:hidden"
              :title="t('roundtable.discussion.participants')"
              @click="mobileControlPanelOpen = true"
            >
              <span class="material-symbols-outlined text-base">tune</span>
            </button>
          </div>
        </div>

        <!-- Reconnecting Banner -->
        <div v-if="isReconnecting" class="px-6 py-3 bg-amber-500/20 border-b border-amber-500/30 flex-shrink-0 backdrop-blur-md z-10">
          <div class="flex items-center gap-3 text-amber-300 justify-center">
            <span class="material-symbols-outlined animate-spin">sync</span>
            <span class="text-sm font-bold">Connection lost, attempting to reconnect...</span>
          </div>
        </div>

        <!-- Messages Container -->
        <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth md:p-8 md:space-y-6">
          <div v-for="message in messages" :key="message.id" class="animate-fade-in">
            <!-- System Message -->
            <div v-if="message.type === 'system'" class="flex justify-center py-2">
              <div class="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-text-secondary flex items-center gap-2">
                <span class="material-symbols-outlined text-sm">info</span>
                {{ message.content }}
              </div>
            </div>

            <!-- Agent Message -->
            <div v-else-if="message.type === 'agent_message'" class="flex gap-3 group md:gap-5">
              <div class="w-10 h-10 rounded-xl bg-black/30 border border-white/10 flex items-center justify-center flex-shrink-0 shadow-lg self-start mt-1 md:h-12 md:w-12">
                <span class="material-symbols-outlined text-primary text-xl md:text-2xl">{{ getExpertIcon(message.sender) }}</span>
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
                <div class="glass-card p-3 rounded-2xl rounded-tl-none border border-white/10 bg-white/5 text-text-primary leading-relaxed shadow-md relative overflow-hidden md:p-5">
                  <div
                    class="meeting-markdown max-w-none break-words"
                    :class="{ 'report-mode': isReportLike(message.content) }"
                    v-html="formatMeetingMinutes(message.content)"
                  ></div>

                  <!-- Decorative corner -->
                  <div class="absolute -top-[1px] -left-[1px] w-4 h-4 border-t border-l border-white/20 rounded-tl-none pointer-events-none"></div>
                </div>

                <!-- HITL: Interrupt Button (show for all agent messages, even after meeting ends) -->
                <button
                  v-if="message.sender !== 'Human' && sessionId"
                  @click="openInterventionDialog(messages.indexOf(message))"
                  class="mt-3 px-4 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 hover:border-amber-500/50 transition-all flex items-center gap-2 text-sm font-medium opacity-100 md:opacity-0 md:group-hover:opacity-100"
                >
                  <span class="material-symbols-outlined text-lg">chat_bubble</span>
                  {{ t('roundtable.hitl.interruptButton') }}
                </button>
              </div>
            </div>

            <!-- Thinking Indicator with Scrollable Log -->
            <div v-else-if="message.type === 'thinking'" class="flex gap-3 md:gap-5">
              <div class="w-10 h-10 rounded-xl bg-black/30 border border-white/10 flex items-center justify-center flex-shrink-0 shadow-lg self-start mt-1 opacity-70 md:h-12 md:w-12">
                <span class="material-symbols-outlined text-primary text-xl animate-pulse md:text-2xl">psychology</span>
              </div>
              <div class="flex-1 max-w-[600px]">
                <div class="flex items-center gap-2 mb-2">
                  <span class="font-bold text-text-secondary text-sm">{{ message.agent }}</span>
                  <span class="text-xs text-primary animate-pulse">Thinking...</span>
                </div>
                <!-- Terminal-like log box -->
                <div class="rounded-xl bg-gray-900/80 border border-white/10 overflow-hidden">
                  <!-- Header bar -->
                  <div class="flex items-center gap-2 px-3 py-2 bg-gray-800/50 border-b border-white/10">
                    <div class="w-2 h-2 rounded-full bg-red-500"></div>
                    <div class="w-2 h-2 rounded-full bg-yellow-500"></div>
                    <div class="w-2 h-2 rounded-full bg-green-500"></div>
                    <span class="text-xs text-white/40 ml-2">{{ message.agent }} - Execution Log</span>
                  </div>
                  <!-- Scrollable log content -->
                  <div class="p-3 max-h-[200px] overflow-y-auto font-mono text-xs leading-relaxed custom-scrollbar"
                       :ref="el => scrollLogToBottom(el)">
                    <div v-for="(log, idx) in message.logs" :key="idx" 
                         class="text-gray-300 mb-1 animate-fade-in whitespace-pre-wrap">
                      <span class="text-gray-500">{{ formatLogTime(log.timestamp) }}</span>
                      <span class="text-white/80 ml-2">{{ log.text }}</span>
                    </div>
                    <!-- Current status indicator -->
                    <div class="flex items-center gap-2 text-primary mt-2">
                      <span class="inline-block w-2 h-2 bg-primary rounded-full animate-pulse"></span>
                      <span>{{ message.message || 'Processing...' }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Summary / Meeting Minutes -->
            <div v-else-if="message.type === 'summary' || message.type === 'meeting_minutes'" class="my-8">
              <div class="glass-panel border border-primary/30 bg-primary/5 rounded-2xl p-4 relative overflow-hidden md:p-8">
                <!-- Background decoration -->
                <div class="absolute top-0 right-0 w-64 h-64 bg-primary/10 blur-[80px] rounded-full pointer-events-none"></div>
                
                <div class="relative z-10">
                    <div class="flex items-center justify-between mb-6 pb-4 border-b border-white/10">
                    <div class="flex items-center gap-3">
                        <div class="p-2 rounded-lg bg-primary/20 text-primary">
                            <span class="material-symbols-outlined text-2xl">summarize</span>
                        </div>
                        <h3 class="text-xl font-bold text-white">
                        {{ message.type === 'meeting_minutes' ? 'Meeting Minutes' : t('roundtable.summary.title') }}
                        </h3>
                    </div>
                    <button
                        @click="exportMeetingMinutes(message.content)"
                        class="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors text-xs font-bold"
                    >
                        <span class="material-symbols-outlined text-sm">download</span>
                        Export
                    </button>
                    </div>
                    <div
                      class="meeting-markdown max-w-none break-words"
                      :class="{ 'report-mode': isReportLike(message.content) }"
                      v-html="formatMeetingMinutes(message.content)"
                    ></div>
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

    <!-- HITL: Human-in-the-Loop Intervention Dialog -->
    <div
      v-if="showInterventionDialog"
      class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="closeInterventionDialog"
    >
      <div class="modal-shell max-w-2xl max-h-[80vh] overflow-y-auto animate-fade-in">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-xl font-bold text-white flex items-center gap-3">
            <span class="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center text-amber-400">
              <span class="material-symbols-outlined">chat_bubble</span>
            </span>
            {{ t('roundtable.hitl.dialogTitle') }}
          </h3>
          <button
            @click="closeInterventionDialog"
            class="text-text-secondary hover:text-white transition-colors"
          >
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <!-- Context: The message being responded to -->
        <div v-if="selectedMessageIndex !== null && messages[selectedMessageIndex]" class="mb-6">
          <label class="block text-sm font-bold text-text-secondary mb-2">
            {{ t('roundtable.hitl.respondingTo') }}
          </label>
          <div class="p-4 rounded-xl bg-black/30 border border-white/10">
            <div class="text-xs text-text-secondary mb-1">
              {{ messages[selectedMessageIndex]?.sender }}
            </div>
            <div class="text-sm text-text-primary line-clamp-3">
              {{ messages[selectedMessageIndex]?.content?.substring(0, 200) }}{{ messages[selectedMessageIndex]?.content?.length > 200 ? '...' : '' }}
            </div>
          </div>
        </div>

        <!-- User Input Area -->
        <div class="mb-6">
          <label class="block text-sm font-bold text-text-secondary mb-2">
            {{ t('roundtable.hitl.inputLabel') }} <span class="text-rose-500">*</span>
          </label>
          <textarea
            v-model="interventionContent"
            :placeholder="t('roundtable.hitl.inputPlaceholder')"
            class="w-full h-40 rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white placeholder-text-secondary transition-all resize-none focus:outline-none focus:border-primary/50 focus:bg-black/50"
          />
          <div class="mt-2 text-xs text-text-secondary">
            {{ t('roundtable.hitl.inputHint') }}
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-3">
          <button
            @click="submitIntervention"
            :disabled="!interventionContent.trim() || isSubmittingIntervention"
            :class="[
              'flex-1 py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2',
              interventionContent.trim() && !isSubmittingIntervention
                ? 'bg-primary hover:bg-primary-light text-background-dark'
                : 'bg-white/10 text-text-secondary cursor-not-allowed'
            ]"
          >
            <span v-if="isSubmittingIntervention" class="material-symbols-outlined animate-spin">progress_activity</span>
            <span v-else class="material-symbols-outlined">send</span>
            {{ isSubmittingIntervention ? t('roundtable.hitl.submitting') : t('roundtable.hitl.submit') }}
          </button>
          <button
            @click="closeInterventionDialog"
            :disabled="isSubmittingIntervention"
            class="px-6 py-3 rounded-xl border border-white/10 text-text-primary hover:bg-white/5 transition-all"
          >
            {{ t('roundtable.hitl.cancel') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onUnmounted, onMounted } from 'vue';
import { useLanguage } from '../composables/useLanguage';
import { getRoundtableAgents } from '../config/agents';
import { API_BASE, apiUrl, wsUrl } from '@/config/api';
import { marked } from 'marked';
import { appendTokenToUrl, getAuthHeaders } from '@/services/authHeaders';
import { readJsonResponse } from '@/services/httpResponse';
import { useAuthStore } from '@/stores/auth';

const { t, locale } = useLanguage();
const authStore = useAuthStore();
let authRefreshInFlight = false;

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
const useKnowledgeBase = ref(false);
const knowledgeCategory = ref('all');
const mobileControlPanelOpen = ref(false);
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;
let shouldReconnect = true; // Flag to control reconnection
let discussionConfig = null; // Store config for reconnection
const markdownRenderCache = new Map();
const reportDetectCache = new Map();

// Human-in-the-Loop (HITL) state
const sessionId = ref(''); // Session ID for HITL API calls
const showInterventionDialog = ref(false); // Whether to show intervention dialog
const interventionContent = ref(''); // User's intervention content
const selectedMessageIndex = ref(null); // Index of message being responded to
const isSubmittingIntervention = ref(false); // Submitting state

// Dropdown state for expert selection
const showExpertDropdown = ref(false);
const expertDropdownRef = ref(null);

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
  if (expertDropdownRef.value && !expertDropdownRef.value.contains(event.target)) {
    showExpertDropdown.value = false;
  }
};

// Available experts - computed to be reactive to language changes (excludes Leader)
const availableExperts = computed(() => {
  const agents = getRoundtableAgents();
  const isZh = locale.value.startsWith('zh'); // 'zh-CN' or 'zh'
  // Exclude leader - it's always included automatically
  return agents
    .filter(agent => agent.id !== 'leader')
    .map(agent => ({
      id: agent.id,
      name: isZh ? agent.name_zh : agent.name,
      role: isZh ? agent.role_zh : agent.role,
      description: isZh ? agent.description_zh : agent.description,
      icon: agent.icon
    }));
});

// Get expert by ID (for rendering selected tags)
const getExpertById = (id) => {
  return availableExperts.value.find(e => e.id === id);
};

const selectedExperts = ref([]);

const getKnowledgeCategoryLabel = (category) => {
  const labels = {
    all: 'All Knowledge',
    general: 'General Docs',
    financial: 'Financial Docs',
    market: 'Market Docs',
    legal: 'Legal Docs'
  };
  return labels[category] || labels.all;
};

// History Reference State
const useHistoryReference = ref(false);
const historyList = ref([]);
const loadingHistory = ref(false);
const selectedHistoryRef = ref(null);

// Default core experts (5 most important for investment analysis)
const DEFAULT_EXPERTS = [
  'market-analyst',    // 市场分析师
  'financial-expert',  // 财务专家
  'tech-specialist',   // 技术专家
  'legal-advisor',     // 法律顾问
  'risk-assessor'      // 风险评估师
];

const ACTIVE_ROUNDTABLE_STORAGE_KEY = 'magellan_active_roundtable_session';

const persistActiveRoundtableSession = (extra = {}) => {
  if (!sessionId.value) return;
  try {
    const payload = {
      sessionId: sessionId.value,
      topic: discussionConfig?.topic || discussionTopic.value,
      experts: discussionConfig?.experts || selectedExperts.value,
      maxRounds: discussionConfig?.maxRounds || maxRounds.value,
      knowledge: discussionConfig?.knowledge || {
        enabled: useKnowledgeBase.value,
        category: knowledgeCategory.value
      },
      historyReference: discussionConfig?.historyReference || null,
      status: discussionStatus.value,
      updatedAt: Date.now(),
      ...extra
    };
    localStorage.setItem(ACTIVE_ROUNDTABLE_STORAGE_KEY, JSON.stringify(payload));
  } catch (error) {
    console.warn('[Roundtable] Failed to persist active session:', error);
  }
};

const clearPersistedRoundtableSession = () => {
  try {
    localStorage.removeItem(ACTIVE_ROUNDTABLE_STORAGE_KEY);
  } catch (_) {
    // ignore
  }
};

const loadPersistedRoundtableSession = () => {
  try {
    const raw = localStorage.getItem(ACTIVE_ROUNDTABLE_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch (error) {
    console.warn('[Roundtable] Failed to read persisted session:', error);
    return null;
  }
};

const tryResumePersistedRoundtableSession = () => {
  const persisted = loadPersistedRoundtableSession();
  if (!persisted?.sessionId || persisted.status === 'completed') return false;

  discussionConfig = {
    topic: persisted.topic || '',
    experts: Array.isArray(persisted.experts) ? persisted.experts : [...DEFAULT_EXPERTS],
    maxRounds: persisted.maxRounds || 5,
    knowledge: persisted.knowledge || { enabled: false, category: 'all' },
    historyReference: persisted.historyReference || null
  };

  sessionId.value = persisted.sessionId;
  discussionTopic.value = discussionConfig.topic;
  selectedExperts.value = [...discussionConfig.experts];
  maxRounds.value = discussionConfig.maxRounds;
  useKnowledgeBase.value = !!discussionConfig.knowledge?.enabled;
  knowledgeCategory.value = discussionConfig.knowledge?.category || 'all';

  shouldReconnect = true;
  reconnectAttempts = 0;
  isDiscussionActive.value = true;
  isConnecting.value = true;
  discussionStatus.value = 'running';
  currentRound.value = 0;
  messages.value = [{
    id: Date.now(),
    type: 'system',
    content: 'Resuming previous discussion session...'
  }];

  connectWebSocket({ resume: true });
  return true;
};

const tryResumeBackendActiveSession = async () => {
  try {
    const response = await fetch(apiUrl('/api/roundtable/active'), {
      headers: {
        ...getAuthHeaders()
      }
    });
    const data = await readJsonResponse(response, 'Load active roundtable sessions');
    const latest = Array.isArray(data.sessions) && data.sessions.length > 0 ? data.sessions[0] : null;
    if (!latest?.session_id) return false;

    discussionConfig = {
      topic: latest.topic || '',
      experts: [...DEFAULT_EXPERTS],
      maxRounds: latest.max_rounds || 5,
      knowledge: latest.knowledge || { enabled: false, category: 'all' },
      historyReference: null
    };

    sessionId.value = latest.session_id;
    discussionTopic.value = latest.topic || '';
    selectedExperts.value = [...discussionConfig.experts];
    maxRounds.value = discussionConfig.maxRounds;
    useKnowledgeBase.value = !!discussionConfig.knowledge?.enabled;
    knowledgeCategory.value = discussionConfig.knowledge?.category || 'all';
    shouldReconnect = true;
    reconnectAttempts = 0;
    isDiscussionActive.value = true;
    isConnecting.value = true;
    discussionStatus.value = 'running';
    messages.value = [{
      id: Date.now(),
      type: 'system',
      content: 'Recovered an active discussion from backend...'
    }];
    connectWebSocket({ resume: true });
    return true;
  } catch (error) {
    console.warn('[Roundtable] Failed to recover backend active session:', error);
    return false;
  }
};

// Initialize selected experts on mount with defaults only
onMounted(() => {
  selectedExperts.value = [...DEFAULT_EXPERTS];
  // Add click outside listener for dropdown
  document.addEventListener('click', handleClickOutside);
  const resumedFromLocal = tryResumePersistedRoundtableSession();
  if (!resumedFromLocal) {
    tryResumeBackendActiveSession();
  }
});

// Cleanup on unmount
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

// History Reference Methods
const loadHistoryList = async () => {
  loadingHistory.value = true;
  try {
    const response = await fetch(apiUrl('/api/roundtable/history?limit=20'), {
      headers: {
        ...getAuthHeaders()
      }
    });
    const data = await readJsonResponse(response, 'Load roundtable history');
    console.log('[Roundtable] Loaded history:', data);
    if (data.success) {
      historyList.value = data.roundtables;
    } else {
      console.warn('[Roundtable] History API returned success=false');
    }
  } catch (error) {
    console.error('[Roundtable] Failed to load history:', error);
  } finally {
    loadingHistory.value = false;
  }
};

const selectHistoryReference = (history) => {
  if (selectedHistoryRef.value?.id === history.id) {
    selectedHistoryRef.value = null; // Deselect
  } else {
    selectedHistoryRef.value = history;
  }
};

const formatHistoryDate = (dateString) => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (e) {
    return dateString;
  }
};

// Watch for useHistoryReference toggle
import { watch } from 'vue';
watch(useHistoryReference, (newVal) => {
  if (newVal && historyList.value.length === 0) {
    loadHistoryList();
  }
  if (!newVal) {
    selectedHistoryRef.value = null;
  }
});

// Messages
const messages = ref([]);
const messagesContainer = ref(null);

// WebSocket
let ws = null;

const parseJwtPayload = (token) => {
  try {
    const parts = String(token || '').split('.');
    if (parts.length < 2) return null;
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const normalized = base64 + '='.repeat((4 - (base64.length % 4 || 4)) % 4);
    return JSON.parse(atob(normalized));
  } catch {
    return null;
  }
};

const isAccessTokenExpired = (token, skewSeconds = 30) => {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') return true;
  const nowSec = Math.floor(Date.now() / 1000);
  return payload.exp <= nowSec + skewSeconds;
};

const ensureValidAccessToken = async () => {
  const token = localStorage.getItem('access_token') || '';
  if (token && !isAccessTokenExpired(token)) return true;

  if (authRefreshInFlight) {
    for (let i = 0; i < 20; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 100));
      const latest = localStorage.getItem('access_token') || '';
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
};

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

  // Starting a new discussion invalidates any previous recoverable session.
  clearPersistedRoundtableSession();
  sessionId.value = '';

  // Store config for potential reconnection (including history reference)
  discussionConfig = {
    topic: discussionTopic.value,
    experts: selectedExperts.value,
    maxRounds: maxRounds.value,
    knowledge: {
      enabled: useKnowledgeBase.value,
      category: knowledgeCategory.value
    },
    // Include history reference if selected
    historyReference: useHistoryReference.value && selectedHistoryRef.value ? {
      id: selectedHistoryRef.value.id,
      topic: selectedHistoryRef.value.topic,
      meeting_minutes: selectedHistoryRef.value.meeting_minutes
    } : null
  };
  shouldReconnect = true;
  reconnectAttempts = 0;
  mobileControlPanelOpen.value = false;

  isDiscussionActive.value = true;
  isConnecting.value = true;
  discussionStatus.value = 'running';
  currentRound.value = 0;
  messages.value = [];

  const now = new Date();
  startTime.value = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

  // Add system message
  let systemMsg = `Discussion started - ${selectedExperts.value.length} experts joined`;
  if (discussionConfig.knowledge?.enabled) {
    systemMsg += `\nKnowledge retrieval enabled (scope: ${getKnowledgeCategoryLabel(discussionConfig.knowledge.category)}）`;
  } else {
    systemMsg += '\nKnowledge retrieval disabled';
  }
  if (discussionConfig.historyReference) {
    systemMsg += `\nContinuing from history "${discussionConfig.historyReference.topic}"`;
  }
  messages.value.push({
    id: Date.now(),
    type: 'system',
    content: systemMsg
  });

  // Connect to WebSocket
  connectWebSocket({ resume: false });
};

const connectWebSocket = async ({ resume = false } = {}) => {
  try {
    const tokenOk = await ensureValidAccessToken();
    if (!tokenOk) {
      isConnecting.value = false;
      isReconnecting.value = false;
      discussionStatus.value = 'completed';
      messages.value.push({
        id: Date.now(),
        type: 'system',
        content: '登录状态已过期，请重新登录后再发起头脑风暴。'
      });
      return;
    }

    // Connect to backend roundtable WebSocket
    ws = new WebSocket(appendTokenToUrl(wsUrl('/ws/roundtable')));

    ws.onopen = () => {
      console.log('[Roundtable] WebSocket connected');
      isConnecting.value = false;
      isReconnecting.value = false;
      reconnectAttempts = 0;

      let initialMessage;
      if (resume && sessionId.value) {
        initialMessage = {
          action: 'resume_discussion',
          session_id: sessionId.value
        };
      } else {
        // Send initial message to start discussion
        const lang = locale.value.startsWith('zh') ? 'zh' : 'en'; // 转换为后端期望的格式
        initialMessage = {
          action: 'start_discussion',
          topic: discussionConfig?.topic || discussionTopic.value,
          company_name: (discussionConfig?.topic || discussionTopic.value).split(' ')[0] || 'Target Company',
          language: lang, // 添加语言偏好
          context: {
            max_rounds: discussionConfig?.maxRounds || maxRounds.value,
            experts: discussionConfig?.experts || selectedExperts.value,
            knowledge: discussionConfig?.knowledge || {
              enabled: useKnowledgeBase.value,
              category: knowledgeCategory.value
            },
            // Include history reference for continuation
            history_reference: discussionConfig?.historyReference || null
          }
        };
      }

      console.log('[Roundtable] Sending initial message:', initialMessage);
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
        content: 'Connection error. Please verify backend services are running.'
      });
    };

    ws.onclose = async (event) => {
      console.log('[Roundtable] WebSocket closed:', event.code, event.reason);
      isConnecting.value = false;
      const closeReason = String(event.reason || '').toLowerCase();
      const isAuthClose = event.code === 1008 && (
        closeReason.includes('auth') ||
        closeReason.includes('token') ||
        closeReason.includes('unauthorized')
      );

      if (event?.code === 1008) {
        const refreshed = await ensureValidAccessToken();
        if (refreshed && shouldReconnect && discussionStatus.value === 'running') {
          connectWebSocket({ resume: !!sessionId.value });
          return;
        }
        shouldReconnect = false;
        isReconnecting.value = false;
        discussionStatus.value = 'completed';
        messages.value.push({
          id: Date.now(),
          type: 'system',
          content: '鉴权失败（登录已过期），请重新登录后再试。'
        });
        clearPersistedRoundtableSession();
        return;
      }

      // Auto-reconnect logic (unless explicitly closed by user or discussion completed)
      if (isAuthClose) {
        shouldReconnect = false;
        isReconnecting.value = false;
        discussionStatus.value = 'completed';
        messages.value.push({
          id: Date.now(),
          type: 'system',
          content: 'Authentication expired. Please log in again.'
        });
        clearPersistedRoundtableSession();
      } else if (shouldReconnect && event.code !== 1000 && discussionStatus.value === 'running') {
        isReconnecting.value = true;
        attemptReconnect();
      } else if (discussionStatus.value === 'running' && event.code !== 1000) {
        discussionStatus.value = 'completed';
        messages.value.push({
          id: Date.now(),
          type: 'system',
          content: 'Discussion ended'
        });
        clearPersistedRoundtableSession();
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
      content: `Connection lost, reconnecting (${reconnectAttempts}/${maxReconnectAttempts})...`
    });

    setTimeout(() => {
      connectWebSocket({ resume: !!sessionId.value });
    }, delay);
  } else {
    console.error('[Roundtable] Max reconnection attempts reached');
    isReconnecting.value = false;
    discussionStatus.value = 'completed';
    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: 'Unable to reconnect to server. Discussion terminated.'
    });
    clearPersistedRoundtableSession();
  }
};

const handleWebSocketMessage = (data) => {
  console.log('Received message:', data);

  if (data.type === 'agents_ready') {
    // Extract session_id for HITL API calls
    if (data.session_id) {
      sessionId.value = data.session_id;
      console.log('[HITL] Session ID stored:', sessionId.value);
      persistActiveRoundtableSession({ status: 'running' });
    }
    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: data.message
    });
    scrollToBottom();
  } else if (data.type === 'agent_event') {
    const event = data.event;

    if (event.event_type === 'thinking') {
      // Check if thinking card already exists for this agent
      const existingIndex = messages.value.findIndex(
        m => m.type === 'thinking' && m.agent === event.agent_name
      );
      if (existingIndex !== -1) {
        // Update existing thinking card
        messages.value[existingIndex].message = event.message || `${event.agent_name}is thinking...`;
      } else {
        // Create new thinking indicator with empty logs
        messages.value.push({
          id: Date.now() + Math.random(),
          type: 'thinking',
          agent: event.agent_name,
          message: event.message || `${event.agent_name}is thinking...`,
          logs: []
        });
      }
      scrollToBottom();
    } else if (event.event_type === 'log') {
      // Append log to existing thinking card
      const thinkingIndex = messages.value.findIndex(
        m => m.type === 'thinking' && m.agent === event.agent_name
      );
      if (thinkingIndex !== -1) {
        if (!messages.value[thinkingIndex].logs) {
          messages.value[thinkingIndex].logs = [];
        }
        messages.value[thinkingIndex].logs.push({
          text: event.message,
          timestamp: Date.now()
        });
      }
      scrollToBottom();
    } else if (event.event_type === 'progress' || event.event_type === 'analyzing' || event.event_type === 'searching') {
      // Update status message and add to logs
      const thinkingIndex = messages.value.findIndex(
        m => m.type === 'thinking' && m.agent === event.agent_name
      );
      if (thinkingIndex !== -1) {
        messages.value[thinkingIndex].message = event.message;
        if (!messages.value[thinkingIndex].logs) {
          messages.value[thinkingIndex].logs = [];
        }
        messages.value[thinkingIndex].logs.push({
          text: event.message,
          timestamp: Date.now()
        });
      } else {
        // No thinking card exists, create one
        messages.value.push({
          id: Date.now() + Math.random(),
          type: 'thinking',
          agent: event.agent_name,
          message: event.message,
          logs: [{ text: event.message, timestamp: Date.now() }]
        });
      }
      scrollToBottom();
    } else if (event.event_type === 'result') {
      // Convert thinking card to collapsed state, keep logs for reference
      const thinkingIndex = messages.value.findIndex(
        m => m.type === 'thinking' && m.agent === event.agent_name
      );
      if (thinkingIndex !== -1) {
        // Store logs before removing
        const savedLogs = messages.value[thinkingIndex].logs || [];
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
        content: `Error: ${event.message}`
      });
      scrollToBottom();
    }
  } else if (data.type === 'discussion_complete') {
    discussionStatus.value = 'completed';
    isDiscussionActive.value = false;
    shouldReconnect = false;
    clearPersistedRoundtableSession();
    if (data.summary) {
      const summary = data.summary;

      // 如果有Meeting Minutes，优先显示
      if (summary.meeting_minutes) {
        messages.value.push({
          id: Date.now(),
          type: 'meeting_minutes',
          content: summary.meeting_minutes
        });
      } else {
        // 否则显示统计摘要
        let summaryText = '## Discussion Statistics\n\n';
        summaryText += `- **Total Rounds**: ${summary.total_turns || 0}\n`;
        summaryText += `- **Total Messages**: ${summary.total_messages || 0}\n`;
        summaryText += `- **Discussion Duration**: ${(summary.total_duration_seconds || 0).toFixed(1)} s\n\n`;

        if (summary.agent_stats) {
          summaryText += '### Agent Contribution Stats\n\n';
          for (const [agent, stats] of Object.entries(summary.agent_stats)) {
            summaryText += `**${agent}**:\n`;
            summaryText += `- Total Messages: ${stats.total_messages || 0}\n`;
            summaryText += `- Broadcast: ${stats.broadcast || 0}\n`;
            summaryText += `- Private: ${stats.private || 0}\n`;
            summaryText += `- Questions: ${stats.questions || 0}\n\n`;
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
      content: `Error: ${data.message}`
    });
    if (String(data.message || '').includes('未找到可恢复的讨论会话')) {
      shouldReconnect = false;
      isReconnecting.value = false;
      isDiscussionActive.value = false;
      discussionStatus.value = 'completed';
      clearPersistedRoundtableSession();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, 'session-not-recoverable');
      }
    }
    scrollToBottom();
  }
};

const stopDiscussion = () => {
  console.log('[Roundtable] Stopping discussion...');
  shouldReconnect = false; // Disable auto-reconnect
  mobileControlPanelOpen.value = false;
  if (ws) {
    ws.close(1000, 'User stopped discussion'); // Normal closure
  }
  discussionStatus.value = 'completed';
  isReconnecting.value = false;
  clearPersistedRoundtableSession();
};

const generateMeetingSummary = async () => {
  if (isGeneratingSummary.value || messages.value.length === 0) return;

  isGeneratingSummary.value = true;
  
  // 创建一个流式消息，逐字显示内容
  const streamingMessageId = Date.now();
  messages.value.push({
    id: streamingMessageId,
    type: 'meeting_minutes',
    content: '',
    isStreaming: true
  });
  scrollToBottom();

  try {
    // 收集所有对话消息
    const dialogueMessages = messages.value
      .filter(m => m.type === 'agent_message')
      .map(m => ({
        speaker: m.sender,
        content: m.content,
        timestamp: m.timestamp
      }));

    const lang = locale.value.startsWith('zh') ? 'zh' : 'en';
    
    // 使用fetch的流式API
    const response = await fetch(`${API_BASE}/api/roundtable/generate_summary_stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({
        topic: discussionTopic.value,
        messages: dialogueMessages,
        participants: selectedExperts.value,
        rounds: currentRound.value,
        language: lang
      })
    });

    if (!response.ok) {
      throw new Error('Failed to connect to streaming endpoint');
    }

    // 流式读取响应
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      
      // 解析SSE事件 (格式: data: {...}\n\n)
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            if (data.error) {
              throw new Error(data.error);
            }
            
            if (data.content) {
              fullContent += data.content;
              
              // 更新流式消息内容
              const msgIndex = messages.value.findIndex(m => m.id === streamingMessageId);
              if (msgIndex !== -1) {
                messages.value[msgIndex].content = fullContent;
              }
              scrollToBottom();
            }
            
            if (data.done) {
              // 流式传输完成，移除streaming标记
              const msgIndex = messages.value.findIndex(m => m.id === streamingMessageId);
              if (msgIndex !== -1) {
                messages.value[msgIndex].isStreaming = false;
              }
            }
          } catch (e) {
            if (!e.message.includes('Unexpected end of JSON')) {
              console.warn('Error parsing SSE data:', e);
            }
          }
        }
      }
    }

    scrollToBottom();
  } catch (error) {
    console.error('Error generating meeting summary:', error);
    
    // 移除流式消息并显示Error
    const msgIndex = messages.value.findIndex(m => m.id === streamingMessageId);
    if (msgIndex !== -1) {
      messages.value.splice(msgIndex, 1);
    }
    
    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: 'Failed to generate meeting minutes, please retry: ' + error.message
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
        return `[Summary]\n${m.content}\n`;
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
  // 生成完整的Meeting MinutesMarkdown文件
  const timestamp = new Date().toLocaleString('zh-CN');
  const fullContent = `# Roundtable Discussion Minutes

**Discussion Topic**: ${discussionTopic.value}
**Generated At**: ${timestamp}

---

${content}

---

*This meeting minutes document is auto-generated by the AI roundtable system*
`;

  const blob = new Blob([fullContent], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  // 生成友好的文件名
  const sanitizedTopic = discussionTopic.value.replace(/[^\u4e00-\u9fa5a-zA-Z0-9]/g, '_').substring(0, 30);
  const dateStr = new Date().toISOString().split('T')[0];
  a.download = `meeting_minutes_${sanitizedTopic}_${dateStr}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

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

const isReportLike = (content) => {
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
};

const formatMeetingMinutes = (content) => {
  try {
    marked.setOptions({
      breaks: true,
      gfm: true,
      headerIds: false,
      mangle: false
    });

    const raw = String(content || '');
    const cacheKey = raw;
    const cached = markdownRenderCache.get(cacheKey);
    if (cached) return cached;

    // Keep tool output folding, then apply report-friendly markdown formatting.
    let processedContent = collapseToolResults(raw);
    if (isReportLike(raw)) {
      processedContent = preprocessReportMarkdown(processedContent);
    }

    const html = marked.parse(processedContent);
    markdownRenderCache.set(cacheKey, html);
    if (markdownRenderCache.size > 300) markdownRenderCache.clear();
    return html;
  } catch (error) {
    console.error('Markdown parsing error:', error);
    return String(content || '')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br/>');
  }
};

// Collapse tool call results into expandable sections
const collapseToolResults = (content) => {
  if (!content) return '';

  // 1. Handle [USE_TOOL: ...] badges first
  let processed = content.replace(/\[USE_TOOL:\s*([^\]]+)\]/g, (match, toolCall) => {
    return `<div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-300 text-xs font-mono my-1 animate-fade-in"><span class="material-symbols-outlined text-sm">bolt</span>${toolCall}</div>`;
  });

  // 2. Handle Tool Results: [tool_nameResult]: ...
  const toolResultPattern = /\[(\w+)(Result|Error)\]:\s*(\{[\s\S]*?\}|[\s\S]*?)(?=\n\[|\[USE_TOOL|$)/g;

  processed = processed.replace(toolResultPattern, (match, toolName, type, rawContent) => {
    const isError = type === 'Error';
    const icon = isError ? '⚠️' : '🔧';
    const titleColor = isError ? 'text-amber-400' : 'text-cyan-400';
    const borderColor = isError ? 'border-amber-500/20' : 'border-cyan-500/20';
    const bgColor = isError ? 'bg-amber-500/5' : 'bg-cyan-500/5';
    
    let formattedBody = '';
    let summaryText = 'Click to view details';
    let isSearchResults = toolName.toLowerCase().includes('search');

    try {
      // Default raw dump
      formattedBody = `<div class="whitespace-pre-wrap text-xs text-white/70 font-mono break-all">${rawContent}</div>`;
      summaryText = rawContent.length > 50 ? rawContent.substring(0, 50).replace(/\n/g, ' ') + '...' : rawContent.replace(/\n/g, ' ');

      // --- Search Result Parsing Strategies ---
      if (isSearchResults) {
          let items = [];
          let parseContent = rawContent;

          // Strategy A: Check for JSON 'summary' or 'results'
          if (parseContent.includes("'results':") || parseContent.includes('"results":')) {
             const summaryMatch = parseContent.match(/'summary':\s*"([\s\S]*?)"/);
             if (summaryMatch) {
                 parseContent = summaryMatch[1].replace(/\\n/g, '\n');
             }
          }

          // Strategy B: Parse Text List
          if (parseContent.includes('Source:')) {
              const numberedItems = parseContent.split(/\n\d+\.\s+/).slice(1);
              if (numberedItems.length > 0) {
                  items = numberedItems.map(item => {
                      const lines = item.split('\n');
                      const title = lines[0].trim();
                      const urlLine = lines.find(l => l.trim().startsWith('Source:')) || '';
                      const descLine = lines.find(l => l.trim().startsWith('Content:')) || '';
                      return {
                          title: title,
                          url: urlLine.replace('Source:', '').trim(),
                          desc: descLine.replace('Content:', '').trim()
                      };
                  });
              } else {
                  const blocks = parseContent.split(/\n\n+/);
                  blocks.forEach(block => {
                      if (block.includes('Source:') && block.includes('Content:')) {
                          const lines = block.split('\n').map(l => l.trim()).filter(l => l);
                          const sourceIdx = lines.findIndex(l => l.startsWith('Source:'));
                          if (sourceIdx >= 0) {
                              const title = sourceIdx > 0 ? lines[sourceIdx - 1] : 'Untitled Result';
                              const url = lines[sourceIdx].replace('Source:', '').trim();
                              const contentLine = lines.find(l => l.startsWith('Content:'));
                              const desc = contentLine ? contentLine.replace('Content:', '').trim() : '';
                              items.push({ title, url, desc });
                          }
                      }
                  });
              }
          }

          // Render Items if found
          if (items.length > 0) {
              // CRITICAL FIX: No indentation in the generated HTML to prevent Markdown parser from treating it as code blocks
              let cards = items.map(item => 
                `<div class="p-3 bg-black/20 rounded-lg border border-white/5 hover:border-white/10 transition-colors group flex flex-col gap-2 text-left"><a href="${item.url}" target="_blank" class="text-emerald-400 font-bold text-sm hover:underline leading-tight flex items-start gap-2"><span class="flex-1 break-words">${item.title}</span><span class="material-symbols-outlined text-[10px] opacity-50 group-hover:opacity-100 mt-1 flex-shrink-0">open_in_new</span></a>${item.url ? `<div class="text-[10px] text-white/30 font-mono truncate">${item.url}</div>` : ''}<div class="text-xs text-white/70 leading-relaxed line-clamp-4 break-words">${item.desc}</div></div>`
              ).join('');
              
              formattedBody = `<div class="grid grid-cols-1 gap-3 mt-2">${cards}</div>`;
              summaryText = `Search Results (${items.length} items)`;
          }
      }

    } catch (e) {
      console.error('Error parsing tool result:', e);
    }

    // CRITICAL FIX: Remove newlines/indentation from the wrapper details tag too
    return `<details class="group my-3 rounded-xl overflow-hidden border ${borderColor} ${bgColor}"><summary class="flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-white/5 transition-colors select-none"><div class="w-6 h-6 rounded flex items-center justify-center bg-white/10 text-base">${icon}</div><div class="flex-1 min-w-0 flex flex-col"><div class="flex items-center gap-2"><span class="font-bold text-sm ${titleColor}">${toolName}${type}</span><span class="text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 text-white/50 border border-white/5 uppercase tracking-wider">Tool Output</span></div><span class="text-xs text-white/50 truncate mt-0.5 font-mono">${summaryText}</span></div><span class="material-symbols-outlined text-white/30 group-open:rotate-180 transition-transform duration-300">expand_more</span></summary><div class="px-4 pb-4 pt-0 animate-fade-in"><div class="h-px w-full bg-white/5 mb-3"></div>${formattedBody}</div></details>`;
  });

  return processed;
};

/**
 * Check if user is near the bottom of the messages container
 * Returns true if user is within 150px of the bottom
 */
const isNearBottom = () => {
  if (!messagesContainer.value) return true;
  const { scrollTop, scrollHeight, clientHeight } = messagesContainer.value;
  return scrollHeight - scrollTop - clientHeight < 150;
};

/**
 * Scroll to bottom only if user is already near the bottom
 * This prevents interrupting users who are reading history
 */
const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value && isNearBottom()) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

/**
 * Force scroll to bottom (used for user's own messages)
 */
const forceScrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

// Format timestamp for log display
const formatLogTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

// Auto-scroll log container to bottom
const scrollLogToBottom = (el) => {
  if (el) {
    nextTick(() => {
      el.scrollTop = el.scrollHeight;
    });
  }
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
    'broadcast': 'Public',
    'direct': 'Private',
    'question': 'Questions',
    'response': 'Response',
    'agreement': 'Agree',
    'disagreement': 'Disagree'
  };
  return labels[type] || type;
};

// ==================== HITL (Human-in-the-Loop) Methods ====================

/**
 * Open the intervention dialog
 */
const openInterventionDialog = (messageIndex) => {
  selectedMessageIndex.value = messageIndex;
  interventionContent.value = '';
  showInterventionDialog.value = true;
};

/**
 * Close the intervention dialog
 */
const closeInterventionDialog = () => {
  if (!isSubmittingIntervention.value) {
    showInterventionDialog.value = false;
    selectedMessageIndex.value = null;
    interventionContent.value = '';
  }
};

/**
 * Submit user intervention to backend
 */
const submitIntervention = async () => {
  if (!interventionContent.value.trim()) {
    return;
  }

  isSubmittingIntervention.value = true;

  try {
    const response = await fetch(`${API_BASE}/api/roundtable/inject_human_input`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({
        session_id: sessionId.value,
        content: interventionContent.value.trim()
      })
    });
    const result = await readJsonResponse(response, 'Submit human intervention');
    console.log('[HITL] Intervention submitted successfully:', result);

    // Add user's intervention message to the messages list for UI feedback
    messages.value.push({
      id: Date.now(),
      type: 'agent_message',
      sender: 'Human',
      content: interventionContent.value.trim(),
      message_type: 'human_intervention',
      timestamp: new Date().toISOString()
    });

    // Force scroll for user's own message
    forceScrollToBottom();

    // Close dialog and reset state
    showInterventionDialog.value = false;
    selectedMessageIndex.value = null;
    interventionContent.value = '';

    // Add system message to indicate intervention was received
    messages.value.push({
      id: Date.now() + 1,
      type: 'system',
      content: t('roundtable.hitl.interventionSent')
    });

  } catch (error) {
    console.error('[HITL] Error submitting intervention:', error);
    // Show error as system message
    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: `${t('roundtable.hitl.interventionError')}: ${error.message}`
    });
  } finally {
    isSubmittingIntervention.value = false;
  }
};

// Cleanup
onUnmounted(() => {
  shouldReconnect = false;
  if (ws) {
    ws.close();
  }
});
</script>
<style scoped>
.meeting-markdown {
  font-size: 0.925rem;
  line-height: 1.75;
  color: rgba(235, 240, 255, 0.94);
  overflow-wrap: anywhere;
  word-break: break-word;
}

.meeting-markdown :deep(h1),
.meeting-markdown :deep(h2),
.meeting-markdown :deep(h3) {
  margin-top: 0.9rem;
  margin-bottom: 0.45rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: #f8fbff;
}

.meeting-markdown.report-mode :deep(h2) {
  border-left: 3px solid rgba(94, 163, 255, 0.72);
  padding-left: 0.55rem;
}

.meeting-markdown :deep(p) {
  margin: 0.45rem 0;
}

.meeting-markdown :deep(ul),
.meeting-markdown :deep(ol) {
  margin: 0.45rem 0 0.6rem;
  padding-left: 1.1rem;
}

.meeting-markdown :deep(li) {
  margin: 0.22rem 0;
}

.meeting-markdown :deep(strong) {
  color: #ffffff;
}

.meeting-markdown :deep(blockquote) {
  margin: 0.65rem 0;
  border-left: 3px solid rgba(255, 195, 75, 0.72);
  background: rgba(255, 195, 75, 0.1);
  border-radius: 0.65rem;
  padding: 0.55rem 0.7rem;
  color: rgba(255, 233, 186, 0.95);
}

.meeting-markdown :deep(hr) {
  border: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.16);
  margin: 0.8rem 0;
}

.meeting-markdown :deep(pre) {
  margin: 0.6rem 0;
  border-radius: 0.75rem;
  background: rgba(0, 0, 0, 0.34);
  padding: 0.7rem 0.8rem;
  max-width: 100%;
  overflow-x: auto;
  white-space: pre;
}

.meeting-markdown :deep(code) {
  border-radius: 0.35rem;
  background: rgba(0, 0, 0, 0.28);
  padding: 0.1rem 0.35rem;
  font-size: 0.84em;
  white-space: pre-wrap;
  word-break: break-word;
}

.meeting-markdown :deep(table) {
  width: 100%;
  margin: 0.65rem 0;
  border-collapse: collapse;
  overflow: hidden;
  border-radius: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  display: block;
  max-width: 100%;
  overflow-x: auto;
}

.meeting-markdown :deep(th),
.meeting-markdown :deep(td) {
  padding: 0.42rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.meeting-markdown :deep(thead th) {
  background: rgba(94, 163, 255, 0.18);
  color: #f6faff;
  font-weight: 600;
}

.meeting-markdown :deep(tr:last-child td) {
  border-bottom: 0;
}

.meeting-markdown :deep(a) {
  word-break: break-all;
}

.meeting-markdown :deep(img) {
  max-width: 100%;
  height: auto;
}
</style>
