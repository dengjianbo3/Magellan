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
                请选择参与讨论的专家
              </span>
            </div>
            <!-- Dropdown multi-select -->
            <div class="relative" ref="expertDropdownRef">
              <button
                @click="showExpertDropdown = !showExpertDropdown"
                class="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white text-left flex items-center justify-between hover:border-primary/50 transition-all"
              >
                <span class="text-text-secondary">点击添加或移除专家...</span>
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
              讨论主持人将自动参与，无需手动选择
            </p>
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
                  基于历史讨论继续
                </span>
              </label>
              <button
                v-if="useHistoryReference"
                @click="loadHistoryList"
                class="text-xs text-primary hover:text-primary-light flex items-center gap-1"
              >
                <span class="material-symbols-outlined text-sm">refresh</span>
                刷新列表
              </button>
            </div>

            <div v-if="useHistoryReference" class="space-y-3">
              <!-- History List -->
              <div v-if="loadingHistory" class="text-center py-4">
                <span class="material-symbols-outlined animate-spin text-primary">progress_activity</span>
                <p class="text-sm text-text-secondary mt-2">加载历史讨论...</p>
              </div>

              <div v-else-if="historyList.length === 0" class="text-center py-4">
                <span class="material-symbols-outlined text-text-secondary text-3xl">history</span>
                <p class="text-sm text-text-secondary mt-2">暂无历史讨论记录</p>
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
                        {{ formatHistoryDate(history.created_at) }} · {{ history.total_turns }} 轮讨论
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
                    <p class="text-sm font-bold text-amber-400 mb-1">基于历史讨论继续</p>
                    <p class="text-xs text-text-secondary">
                      将参考「{{ selectedHistoryRef.topic }}」的会议纪要开始新讨论。
                      系统会提醒专家们审视上次的结论，但鼓励提出新的观点和质疑。
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

                <!-- HITL: Interrupt Button (show for all agent messages, even after meeting ends) -->
                <button
                  v-if="message.sender !== 'Human' && sessionId"
                  @click="openInterventionDialog(messages.indexOf(message))"
                  class="mt-3 px-4 py-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 hover:border-amber-500/50 transition-all flex items-center gap-2 text-sm font-medium opacity-0 group-hover:opacity-100"
                >
                  <span class="material-symbols-outlined text-lg">chat_bubble</span>
                  {{ t('roundtable.hitl.interruptButton') }}
                </button>
              </div>
            </div>

            <!-- Thinking Indicator with Scrollable Log -->
            <div v-else-if="message.type === 'thinking'" class="flex gap-5">
              <div class="w-12 h-12 rounded-xl bg-black/30 border border-white/10 flex items-center justify-center flex-shrink-0 shadow-lg self-start mt-1 opacity-70">
                <span class="material-symbols-outlined text-primary text-2xl animate-pulse">psychology</span>
              </div>
              <div class="flex-1 max-w-[600px]">
                <div class="flex items-center gap-2 mb-2">
                  <span class="font-bold text-text-secondary text-sm">{{ message.agent }}</span>
                  <span class="text-xs text-primary animate-pulse">思考中...</span>
                </div>
                <!-- Terminal-like log box -->
                <div class="rounded-xl bg-gray-900/80 border border-white/10 overflow-hidden">
                  <!-- Header bar -->
                  <div class="flex items-center gap-2 px-3 py-2 bg-gray-800/50 border-b border-white/10">
                    <div class="w-2 h-2 rounded-full bg-red-500"></div>
                    <div class="w-2 h-2 rounded-full bg-yellow-500"></div>
                    <div class="w-2 h-2 rounded-full bg-green-500"></div>
                    <span class="text-xs text-white/40 ml-2">{{ message.agent }} - 执行日志</span>
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
                      <span>{{ message.message || '处理中...' }}</span>
                    </div>
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

    <!-- HITL: Human-in-the-Loop Intervention Dialog -->
    <div
      v-if="showInterventionDialog"
      class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="closeInterventionDialog"
    >
      <div class="glass-panel rounded-2xl p-8 max-w-2xl w-full max-h-[80vh] overflow-y-auto animate-fade-in">
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
            class="w-full h-40 px-4 py-3 rounded-xl bg-black/30 border border-white/10 text-white placeholder-text-secondary focus:outline-none focus:border-primary/50 focus:bg-black/50 transition-all resize-none"
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
import { API_BASE } from '@/config/api';
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

// Initialize selected experts on mount with defaults only
onMounted(() => {
  selectedExperts.value = [...DEFAULT_EXPERTS];
  // Add click outside listener for dropdown
  document.addEventListener('click', handleClickOutside);
});

// Cleanup on unmount
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

// History Reference Methods
const loadHistoryList = async () => {
  loadingHistory.value = true;
  try {
    // Use full URL since API runs on port 8000 (report_orchestrator)
    const response = await fetch('http://localhost:8000/api/roundtable/history?limit=20');
    const data = await response.json();
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

  // Store config for potential reconnection (including history reference)
  discussionConfig = {
    topic: discussionTopic.value,
    experts: selectedExperts.value,
    maxRounds: maxRounds.value,
    // Include history reference if selected
    historyReference: useHistoryReference.value && selectedHistoryRef.value ? {
      id: selectedHistoryRef.value.id,
      topic: selectedHistoryRef.value.topic,
      meeting_minutes: selectedHistoryRef.value.meeting_minutes
    } : null
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
  let systemMsg = `讨论已开始 - ${selectedExperts.value.length} 位专家参与讨论`;
  if (discussionConfig.historyReference) {
    systemMsg += `\n基于历史讨论「${discussionConfig.historyReference.topic}」继续`;
  }
  messages.value.push({
    id: Date.now(),
    type: 'system',
    content: systemMsg
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
          experts: discussionConfig?.experts || selectedExperts.value,
          // Include history reference for continuation
          history_reference: discussionConfig?.historyReference || null
        }
      };

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
    // Extract session_id for HITL API calls
    if (data.session_id) {
      sessionId.value = data.session_id;
      console.log('[HITL] Session ID stored:', sessionId.value);
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
        messages.value[existingIndex].message = event.message || `${event.agent_name}正在思考...`;
      } else {
        // Create new thinking indicator with empty logs
        messages.value.push({
          id: Date.now() + Math.random(),
          type: 'thinking',
          agent: event.agent_name,
          message: event.message || `${event.agent_name}正在思考...`,
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
        'Content-Type': 'application/json'
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
    
    // 移除流式消息并显示错误
    const msgIndex = messages.value.findIndex(m => m.id === streamingMessageId);
    if (msgIndex !== -1) {
      messages.value.splice(msgIndex, 1);
    }
    
    messages.value.push({
      id: Date.now(),
      type: 'system',
      content: '生成会议纪要失败，请重试: ' + error.message
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

    // First, extract and collapse tool results
    let processedContent = collapseToolResults(content);

    return marked.parse(processedContent);
  } catch (error) {
    console.error('Markdown parsing error:', error);
    // Fallback to simple formatting
    return content
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

  // 2. Handle Tool Results: [tool_name结果]: ...
  const toolResultPattern = /\[(\w+)(结果|错误)\]:\s*(\{[\s\S]*?\}|[\s\S]*?)(?=\n\[|\[USE_TOOL|$)/g;

  processed = processed.replace(toolResultPattern, (match, toolName, type, rawContent) => {
    const isError = type === '错误';
    const icon = isError ? '⚠️' : '🔧';
    const titleColor = isError ? 'text-amber-400' : 'text-cyan-400';
    const borderColor = isError ? 'border-amber-500/20' : 'border-cyan-500/20';
    const bgColor = isError ? 'bg-amber-500/5' : 'bg-cyan-500/5';
    
    let formattedBody = '';
    let summaryText = '点击查看详情';
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
          if (parseContent.includes('来源:')) {
              const numberedItems = parseContent.split(/\n\d+\.\s+/).slice(1);
              if (numberedItems.length > 0) {
                  items = numberedItems.map(item => {
                      const lines = item.split('\n');
                      const title = lines[0].trim();
                      const urlLine = lines.find(l => l.trim().startsWith('来源:')) || '';
                      const descLine = lines.find(l => l.trim().startsWith('内容:')) || '';
                      return {
                          title: title,
                          url: urlLine.replace('来源:', '').trim(),
                          desc: descLine.replace('内容:', '').trim()
                      };
                  });
              } else {
                  const blocks = parseContent.split(/\n\n+/);
                  blocks.forEach(block => {
                      if (block.includes('来源:') && block.includes('内容:')) {
                          const lines = block.split('\n').map(l => l.trim()).filter(l => l);
                          const sourceIdx = lines.findIndex(l => l.startsWith('来源:'));
                          if (sourceIdx >= 0) {
                              const title = sourceIdx > 0 ? lines[sourceIdx - 1] : '未命名结果';
                              const url = lines[sourceIdx].replace('来源:', '').trim();
                              const contentLine = lines.find(l => l.startsWith('内容:'));
                              const desc = contentLine ? contentLine.replace('内容:', '').trim() : '';
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
              summaryText = `搜索结果 (${items.length} 条)`;
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
    'broadcast': '公开',
    'direct': '私聊',
    'question': '提问',
    'response': '回复',
    'agreement': '同意',
    'disagreement': '反对'
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
    const response = await fetch('http://localhost:8002/api/roundtable/inject_human_input', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        session_id: sessionId.value,
        content: interventionContent.value.trim()
      })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to submit intervention');
    }

    const result = await response.json();
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
  if (ws) {
    ws.close();
  }
});
</script>