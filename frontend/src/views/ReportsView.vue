<template>
  <div v-if="!selectedReport" class="space-y-8">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-display font-bold text-white mb-2 tracking-tight">{{ t('reports.title') }}</h1>
        <p class="text-text-secondary text-lg">{{ t('reports.subtitle') }}</p>
      </div>
      <button class="group flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white font-bold shadow-glow-sm hover:shadow-glow hover:-translate-y-0.5 transition-all duration-300">
        <span class="material-symbols-outlined group-hover:rotate-90 transition-transform">add</span>
        {{ t('reports.newReport') }}
      </button>
    </div>

    <!-- Filters -->
    <div class="glass-panel rounded-xl p-2 flex items-center gap-4">
      <div class="flex items-center gap-2 px-2">
        <select class="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:border-primary/50 focus:bg-white/10 outline-none transition-colors cursor-pointer">
          <option>{{ t('reports.filters.allTypes') }}</option>
          <option>{{ t('reports.filters.dueDiligence') }}</option>
          <option>{{ t('reports.filters.marketAnalysis') }}</option>
          <option>{{ t('reports.filters.financialReview') }}</option>
        </select>
        <select class="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white focus:border-primary/50 focus:bg-white/10 outline-none transition-colors cursor-pointer">
          <option>{{ t('reports.filters.allStatus') }}</option>
          <option>{{ t('reports.filters.completed') }}</option>
          <option>{{ t('reports.filters.inProgress') }}</option>
          <option>{{ t('reports.filters.draft') }}</option>
        </select>
      </div>
      
      <div class="flex-1"></div>
      
      <div class="relative group mr-2">
        <div class="absolute inset-0 bg-primary/20 blur-md rounded-lg opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
        <input
          type="text"
          :placeholder="t('reports.searchPlaceholder')"
          class="relative z-10 w-72 px-4 py-2 pl-10 rounded-lg bg-white/5 border border-white/10 text-white placeholder-text-secondary focus:outline-none focus:border-primary/50 focus:bg-surface/50 transition-all duration-300"
        />
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary z-20 group-focus-within:text-primary transition-colors">
          search
        </span>
      </div>
    </div>

    <!-- Reports Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="report in reports"
        :key="report.id"
        @click="viewReport(report.id)"
        class="glass-card rounded-2xl p-6 cursor-pointer group relative overflow-hidden flex flex-col"
      >
        <!-- Background Gradient on Hover -->
        <div class="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

        <div class="relative z-10 flex-1">
          <div class="flex items-start justify-between mb-5">
            <div
              :class="[
                'w-12 h-12 rounded-xl flex items-center justify-center shadow-lg backdrop-blur-sm border transition-transform group-hover:scale-110 duration-300',
                report.type === 'roundtable' ? 'bg-primary/10 border-primary/20 text-primary' :
                report.status === 'completed' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                report.status === 'in-progress' ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' :
                'bg-white/5 border-white/10 text-text-secondary'
              ]"
            >
              <span class="material-symbols-outlined text-2xl">{{ report.type === 'roundtable' ? 'groups' : 'article' }}</span>
            </div>
            <span
              :class="[
                'text-xs px-3 py-1 rounded-full font-bold uppercase tracking-wider border shadow-[0_0_10px_rgba(0,0,0,0.2)]',
                report.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' :
                report.status === 'in-progress' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' :
                'bg-white/5 text-text-secondary border-white/10'
              ]"
            >
              {{ report.statusText }}
            </span>
          </div>

          <h3 class="text-xl font-bold text-white mb-2 group-hover:text-primary transition-colors line-clamp-2">
            {{ report.title }}
          </h3>
          <p class="text-sm text-text-secondary mb-6 line-clamp-2">{{ report.description }}</p>

          <div class="flex items-center gap-4 text-xs text-text-secondary font-medium mb-6">
            <span class="flex items-center gap-1.5 bg-white/5 px-2 py-1 rounded-md">
              <span class="material-symbols-outlined text-sm">calendar_today</span>
              {{ report.date }}
            </span>
            <span class="flex items-center gap-1.5 bg-white/5 px-2 py-1 rounded-md">
              <span class="material-symbols-outlined text-sm">smart_toy</span>
              {{ report.agents }} {{ t('reports.card.agents') }}
            </span>
          </div>
        </div>

        <div class="relative z-10 grid grid-cols-4 gap-2 border-t border-white/10 pt-4">
          <button class="col-span-2 flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-primary/10 text-primary hover:bg-primary hover:text-white transition-all font-bold text-sm group/btn">
            <span class="material-symbols-outlined text-lg group-hover/btn:scale-110 transition-transform">visibility</span>
            {{ t('reports.card.view') }}
          </button>
          
          <div class="relative group/menu">
            <button
              @click.stop="showExportMenu(report.id)"
              class="w-full flex items-center justify-center px-3 py-2 rounded-lg bg-white/5 text-text-secondary hover:bg-white/10 hover:text-white transition-colors border border-white/5"
              title="导出"
            >
              <span class="material-symbols-outlined text-lg">download</span>
            </button>

            <!-- Export Menu Dropdown -->
            <div
              v-if="exportMenuReportId === report.id"
              @click.stop
              class="absolute bottom-full left-0 mb-2 w-48 glass-panel border border-white/10 rounded-xl shadow-xl py-1 z-50 backdrop-blur-xl overflow-hidden animate-fade-in"
            >
              <button @click="exportReport(report.id, 'pdf')" class="w-full px-4 py-2.5 text-left text-sm text-text-primary hover:bg-primary/20 hover:text-white transition-colors flex items-center gap-2">
                <span class="material-symbols-outlined text-base text-rose-400">picture_as_pdf</span> PDF
              </button>
              <button @click="exportReport(report.id, 'word')" class="w-full px-4 py-2.5 text-left text-sm text-text-primary hover:bg-primary/20 hover:text-white transition-colors flex items-center gap-2">
                <span class="material-symbols-outlined text-base text-blue-400">description</span> Word
              </button>
              <button @click="exportReport(report.id, 'excel')" class="w-full px-4 py-2.5 text-left text-sm text-text-primary hover:bg-primary/20 hover:text-white transition-colors flex items-center gap-2">
                <span class="material-symbols-outlined text-base text-emerald-400">table_chart</span> Excel
              </button>
            </div>
          </div>

          <button class="flex items-center justify-center px-3 py-2 rounded-lg bg-white/5 text-text-secondary hover:bg-white/10 hover:text-white transition-colors border border-white/5">
            <span class="material-symbols-outlined text-lg">share</span>
          </button>
          
          <button
            @click.stop="confirmDelete(report.id)"
            class="flex items-center justify-center px-3 py-2 rounded-lg bg-rose-500/10 text-rose-400 hover:bg-rose-500 hover:text-white transition-colors border border-rose-500/20"
            title="删除"
          >
            <span class="material-symbols-outlined text-lg">delete</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Report Detail View -->
  <div v-else class="space-y-8 animate-fade-in">
    <!-- Header with Back Button -->
    <div class="flex items-center gap-6">
      <button
        @click="closeReportView"
        class="group px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-text-primary transition-all duration-300 flex items-center gap-2"
      >
        <span class="material-symbols-outlined group-hover:-translate-x-1 transition-transform">arrow_back</span>
        返回列表
      </button>
      <div class="flex-1">
        <h1 class="text-3xl font-display font-bold text-white tracking-tight">{{ selectedReport.project_name }}</h1>
        <div class="flex items-center gap-3 mt-2">
           <span class="px-2 py-0.5 rounded bg-white/10 text-xs font-bold text-text-primary">{{ selectedReport.company_name }}</span>
           <span class="text-text-secondary text-sm">•</span>
           <span class="text-text-secondary text-sm font-mono">{{ new Date(selectedReport.created_at).toLocaleString('zh-CN') }}</span>
        </div>
      </div>
    </div>

    <!-- Report Content -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Main Content -->
      <div class="lg:col-span-2 space-y-8">

        <!-- ============================================ -->
        <!-- Roundtable Meeting Report Template -->
        <!-- ============================================ -->
        <template v-if="selectedReport.type === 'roundtable'">
          <!-- Meeting Minutes (Main Content) -->
          <div class="glass-panel rounded-2xl p-6">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-lg font-bold text-white flex items-center gap-2">
                <span class="material-symbols-outlined text-primary">summarize</span> 会议纪要
              </h2>
              <span class="px-3 py-1 rounded-full bg-primary/20 text-primary text-xs font-bold">
                圆桌讨论
              </span>
            </div>

            <!-- Meeting Stats -->
            <div class="grid grid-cols-3 gap-4 mb-6 p-4 rounded-xl bg-white/5 border border-white/10">
              <div class="text-center">
                <div class="text-2xl font-bold text-primary">{{ selectedReport.config?.num_agents || selectedReport.discussion_summary?.participating_agents?.length || 'N/A' }}</div>
                <div class="text-xs text-text-secondary mt-1">参与专家</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-accent-cyan">{{ selectedReport.discussion_summary?.total_turns || selectedReport.total_turns || 'N/A' }}</div>
                <div class="text-xs text-text-secondary mt-1">讨论轮次</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-accent-violet">{{ selectedReport.discussion_summary?.total_messages || 'N/A' }}</div>
                <div class="text-xs text-text-secondary mt-1">消息总数</div>
              </div>
            </div>

            <!-- Meeting Minutes Content (Markdown) -->
            <div class="prose prose-invert prose-sm max-w-none report-content">
              <div v-html="renderMarkdown(selectedReport.meeting_minutes)" class="text-text-secondary leading-relaxed"></div>
            </div>
          </div>

          <!-- Participating Experts -->
          <div v-if="selectedReport.config?.agents || selectedReport.discussion_summary?.participating_agents" class="glass-panel rounded-2xl p-6">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-accent-violet">groups</span> 参与专家
            </h2>
            <div class="flex flex-wrap gap-2">
              <span
                v-for="agent in (selectedReport.config?.agents || selectedReport.discussion_summary?.participating_agents)"
                :key="agent"
                class="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-text-primary text-sm font-medium flex items-center gap-2"
              >
                <span class="w-2 h-2 rounded-full" :class="getAgentColor(agent)"></span>
                {{ agent }}
              </span>
            </div>
          </div>

          <!-- Discussion History (Collapsible) -->
          <div class="glass-panel rounded-2xl p-6">
            <button
              @click="showDiscussionHistory = !showDiscussionHistory"
              class="w-full flex items-center justify-between text-lg font-bold text-white"
            >
              <span class="flex items-center gap-2">
                <span class="material-symbols-outlined text-accent-cyan">forum</span> 讨论历史记录
              </span>
              <span class="material-symbols-outlined transition-transform" :class="{ 'rotate-180': showDiscussionHistory }">
                expand_more
              </span>
            </button>

            <!-- Collapsed Summary -->
            <div v-if="!showDiscussionHistory" class="mt-4 text-sm text-text-secondary">
              点击展开查看完整讨论过程 ({{ selectedReport.discussion_summary?.conversation_history?.length || 0 }} 条消息)
            </div>

            <!-- Expanded Discussion History -->
            <div v-if="showDiscussionHistory" class="mt-6 space-y-4 max-h-[600px] overflow-y-auto">
              <div
                v-for="(message, index) in selectedReport.discussion_summary?.conversation_history"
                :key="message.message_id || index"
                class="p-4 rounded-xl border"
                :class="getMessageClass(message)"
              >
                <!-- Message Header -->
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full" :class="getAgentColor(message.sender)"></span>
                    <span class="font-bold text-white text-sm">{{ message.sender }}</span>
                    <span v-if="message.recipient && message.recipient !== 'ALL'" class="text-xs text-text-secondary">
                      → {{ message.recipient }}
                    </span>
                  </div>
                  <span class="text-xs text-text-secondary font-mono">
                    {{ formatMessageTime(message.timestamp) }}
                  </span>
                </div>

                <!-- Message Content -->
                <div class="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                  {{ message.content }}
                </div>

                <!-- Message Type Badge -->
                <div v-if="message.message_type && message.message_type !== 'broadcast'" class="mt-2">
                  <span class="text-xs px-2 py-0.5 rounded bg-white/5 text-text-secondary">
                    {{ getMessageTypeLabel(message.message_type) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Conclusion Reason (if any) -->
          <div v-if="selectedReport.conclusion_reason" class="glass-panel rounded-2xl p-6">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-amber-400">info</span> 会议结束原因
            </h2>
            <p class="text-text-secondary">{{ selectedReport.conclusion_reason }}</p>
          </div>
        </template>

        <!-- ============================================ -->
        <!-- Generic Report Sections (For Public Market / Industry Research) -->
        <!-- ============================================ -->
        <div v-else-if="selectedReport.sections" class="glass-panel rounded-2xl p-6">
          <h2 class="text-lg font-bold text-white mb-6 flex items-center gap-2">
             <span class="material-symbols-outlined text-primary">analytics</span> 详细分析报告
          </h2>

          <!-- Summary / Recommendation -->
          <div v-if="selectedReport.final_recommendation" class="mb-8 p-5 rounded-xl bg-gradient-to-br from-primary/10 to-transparent border border-primary/20">
             <div class="flex items-center justify-between mb-3">
               <span class="text-sm font-bold text-primary uppercase tracking-wider">投资建议</span>
               <span class="text-2xl font-bold text-white">{{ selectedReport.final_recommendation }}</span>
             </div>
             <div v-if="selectedReport.overall_score" class="flex items-center justify-between">
               <span class="text-sm font-bold text-text-secondary uppercase tracking-wider">综合评分</span>
               <span class="text-xl font-bold text-emerald-400">{{ (selectedReport.overall_score * 100).toFixed(0) }} / 100</span>
             </div>
          </div>

          <!-- Sections List -->
          <div class="space-y-6">
            <div 
              v-for="(content, title) in selectedReport.sections" 
              :key="title"
              class="p-5 rounded-xl bg-white/5 border border-white/10"
            >
              <h3 class="text-lg font-bold text-white mb-3 capitalize">{{ title.replace(/_/g, ' ') }}</h3>
              
              <!-- Render content based on type -->
              <div v-if="typeof content === 'string'" class="prose prose-invert prose-sm max-w-none text-text-secondary">
                {{ content }}
              </div>
              <div v-else-if="typeof content === 'object'" class="space-y-2">
                <div v-for="(val, key) in content" :key="key" class="flex justify-between text-sm border-b border-white/5 pb-2 last:border-0">
                   <span class="text-text-secondary capitalize">{{ key.replace(/_/g, ' ') }}</span>
                   <span class="text-white font-medium text-right ml-4">{{ val }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Specialized DD Report (Preliminary IM) - Full Report Display -->
        <div v-else-if="selectedReport.preliminary_im" class="space-y-6">

          <!-- Investment Recommendation Banner -->
          <div class="glass-panel rounded-2xl p-6 bg-gradient-to-br from-primary/10 to-accent-violet/10 border border-primary/20">
            <div class="flex items-center justify-between">
              <div>
                <span class="text-xs font-bold text-primary uppercase tracking-wider">投资建议</span>
                <h2 class="text-3xl font-bold text-white mt-2">
                  {{ getRecommendationText(selectedReport.preliminary_im.overall_recommendation) }}
                </h2>
              </div>
              <div class="text-right">
                <span class="text-xs font-bold text-text-secondary uppercase tracking-wider">综合评分</span>
                <div class="text-4xl font-bold mt-2" :class="getScoreColor(selectedReport.preliminary_im.investment_score)">
                  {{ selectedReport.preliminary_im.investment_score || 'N/A' }}<span class="text-lg text-text-secondary">/100</span>
                </div>
              </div>
            </div>

            <!-- Score Breakdown -->
            <div v-if="selectedReport.preliminary_im.scores_breakdown" class="mt-6 pt-6 border-t border-white/10">
              <div class="grid grid-cols-3 gap-4">
                <div v-for="(score, key) in selectedReport.preliminary_im.scores_breakdown" :key="key" class="text-center">
                  <div class="text-2xl font-bold" :class="getScoreColor(score)">{{ score }}</div>
                  <div class="text-xs text-text-secondary uppercase mt-1">{{ getScoreLabel(key) }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Executive Summary -->
          <div class="glass-panel rounded-2xl p-6">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-primary">summarize</span> 执行摘要
            </h2>
            <div class="prose prose-invert prose-sm max-w-none">
              <div v-html="renderMarkdown(selectedReport.preliminary_im.executive_summary)" class="text-text-secondary leading-relaxed"></div>
            </div>
          </div>

          <!-- Key Findings -->
          <div v-if="selectedReport.preliminary_im.key_findings && selectedReport.preliminary_im.key_findings.length > 0" class="glass-panel rounded-2xl p-6">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-accent-cyan">lightbulb</span> 关键发现
            </h2>
            <div class="space-y-4">
              <!-- Handle structured findings (objects with category, score, key_points, concerns) -->
              <template v-if="isStructuredFindings(selectedReport.preliminary_im.key_findings)">
                <div v-for="(finding, index) in selectedReport.preliminary_im.key_findings" :key="index"
                     class="p-5 rounded-xl bg-white/5 border border-white/10">
                  <!-- Category Header with Score -->
                  <div class="flex items-center justify-between mb-4">
                    <h3 class="text-base font-bold text-white flex items-center gap-2">
                      <span class="w-7 h-7 rounded-lg bg-primary/20 text-primary flex items-center justify-center text-sm font-bold">{{ index + 1 }}</span>
                      {{ finding.category }}
                    </h3>
                    <div v-if="finding.score !== undefined" class="flex items-center gap-2">
                      <span class="text-xs text-text-secondary">评分</span>
                      <span class="text-lg font-bold" :class="getScoreColor(finding.score)">{{ finding.score }}</span>
                    </div>
                  </div>

                  <!-- Key Points -->
                  <div v-if="finding.key_points && finding.key_points.length > 0" class="mb-4">
                    <h4 class="text-xs font-bold text-emerald-400 uppercase mb-2 flex items-center gap-1">
                      <span class="material-symbols-outlined text-sm">check_circle</span> 亮点
                    </h4>
                    <ul class="space-y-2">
                      <li v-for="(point, pIdx) in finding.key_points" :key="pIdx"
                          class="text-sm text-text-secondary flex items-start gap-2">
                        <span class="text-emerald-400 mt-1">•</span>
                        <span>{{ point }}</span>
                      </li>
                    </ul>
                  </div>

                  <!-- Concerns -->
                  <div v-if="finding.concerns && finding.concerns.length > 0">
                    <h4 class="text-xs font-bold text-amber-400 uppercase mb-2 flex items-center gap-1">
                      <span class="material-symbols-outlined text-sm">warning</span> 关注点
                    </h4>
                    <ul class="space-y-2">
                      <li v-for="(concern, cIdx) in finding.concerns" :key="cIdx"
                          class="text-sm text-text-secondary flex items-start gap-2">
                        <span class="text-amber-400 mt-1">•</span>
                        <span>{{ concern }}</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </template>

              <!-- Handle simple string findings -->
              <template v-else>
                <div v-for="(finding, index) in selectedReport.preliminary_im.key_findings" :key="index"
                     class="flex items-start gap-3 p-4 rounded-xl bg-white/5 border border-white/5">
                  <span class="w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center text-sm font-bold shrink-0">{{ index + 1 }}</span>
                  <p class="text-text-secondary text-sm leading-relaxed">{{ typeof finding === 'string' ? finding : JSON.stringify(finding) }}</p>
                </div>
              </template>
            </div>
          </div>

          <!-- Detailed Analysis Sections -->
          <div v-if="getAnalysisSections(selectedReport.preliminary_im)" class="space-y-6">
            <div v-for="section in getAnalysisSections(selectedReport.preliminary_im)" :key="section.key" class="glass-panel rounded-2xl p-6">
              <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <span class="material-symbols-outlined" :class="section.iconColor">{{ section.icon }}</span>
                {{ section.title }}
              </h2>
              <div class="prose prose-invert prose-sm max-w-none report-content">
                <div v-html="renderMarkdown(section.content)" class="text-text-secondary leading-relaxed"></div>
              </div>
            </div>
          </div>

          <!-- SWOT Analysis -->
          <div v-if="hasSWOT(selectedReport.preliminary_im)" class="glass-panel rounded-2xl p-6">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-amber-400">grid_view</span> SWOT 分析
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <!-- Strengths -->
              <div class="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                <h3 class="text-sm font-bold text-emerald-400 uppercase mb-3 flex items-center gap-2">
                  <span class="material-symbols-outlined text-sm">thumb_up</span> 优势
                </h3>
                <ul class="space-y-2">
                  <li v-for="(item, idx) in selectedReport.preliminary_im.strengths" :key="idx" class="text-sm text-text-secondary flex items-start gap-2">
                    <span class="text-emerald-400">•</span> {{ item }}
                  </li>
                </ul>
              </div>
              <!-- Weaknesses -->
              <div class="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20">
                <h3 class="text-sm font-bold text-rose-400 uppercase mb-3 flex items-center gap-2">
                  <span class="material-symbols-outlined text-sm">thumb_down</span> 劣势
                </h3>
                <ul class="space-y-2">
                  <li v-for="(item, idx) in selectedReport.preliminary_im.weaknesses" :key="idx" class="text-sm text-text-secondary flex items-start gap-2">
                    <span class="text-rose-400">•</span> {{ item }}
                  </li>
                </ul>
              </div>
              <!-- Opportunities -->
              <div class="p-4 rounded-xl bg-primary/10 border border-primary/20">
                <h3 class="text-sm font-bold text-primary uppercase mb-3 flex items-center gap-2">
                  <span class="material-symbols-outlined text-sm">trending_up</span> 机会
                </h3>
                <ul class="space-y-2">
                  <li v-for="(item, idx) in selectedReport.preliminary_im.opportunities" :key="idx" class="text-sm text-text-secondary flex items-start gap-2">
                    <span class="text-primary">•</span> {{ item }}
                  </li>
                </ul>
              </div>
              <!-- Threats -->
              <div class="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                <h3 class="text-sm font-bold text-amber-400 uppercase mb-3 flex items-center gap-2">
                  <span class="material-symbols-outlined text-sm">warning</span> 威胁
                </h3>
                <ul class="space-y-2">
                  <li v-for="(item, idx) in selectedReport.preliminary_im.threats" :key="idx" class="text-sm text-text-secondary flex items-start gap-2">
                    <span class="text-amber-400">•</span> {{ item }}
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <!-- Next Steps -->
          <div v-if="selectedReport.preliminary_im.next_steps && selectedReport.preliminary_im.next_steps.length > 0" class="glass-panel rounded-2xl p-6">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-accent-violet">checklist</span> 下一步行动建议
            </h2>
            <div class="space-y-3">
              <div v-for="(step, index) in selectedReport.preliminary_im.next_steps" :key="index"
                   class="flex items-start gap-3 p-4 rounded-xl bg-white/5 border border-white/5">
                <span class="w-8 h-8 rounded-lg bg-accent-violet/20 text-accent-violet flex items-center justify-center shrink-0">
                  <span class="material-symbols-outlined text-sm">arrow_forward</span>
                </span>
                <p class="text-text-secondary text-sm leading-relaxed">{{ step }}</p>
              </div>
            </div>
          </div>

          <!-- DD Questions (if any) -->
          <div v-if="selectedReport.preliminary_im.dd_questions && selectedReport.preliminary_im.dd_questions.length > 0" class="glass-panel rounded-2xl p-6">
            <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span class="material-symbols-outlined text-amber-400">help_outline</span> 尽调问题
            </h2>
            <div class="space-y-4">
              <div v-for="(question, index) in selectedReport.preliminary_im.dd_questions" :key="index"
                   class="p-4 rounded-xl bg-white/5 border border-white/5">
                <div class="flex gap-3">
                  <span class="text-primary font-bold">{{ index + 1 }}.</span>
                  <p class="font-semibold text-text-primary text-sm">{{ question.question || question }}</p>
                </div>
                <div v-if="question.answer" class="mt-3 pl-6 border-l-2 border-white/10 ml-1">
                  <p class="text-sm text-text-secondary">{{ question.answer }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Analysis Steps (Universal) -->
        <div class="glass-panel rounded-2xl p-6">
          <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
             <span class="material-symbols-outlined text-primary">checklist</span> 执行步骤记录
          </h2>
          <div class="space-y-3">
            <div
              v-for="step in selectedReport.steps"
              :key="step.id"
              class="flex items-start gap-4 p-4 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-colors"
            >
              <div
                :class="[
                  'w-8 h-8 rounded-lg flex items-center justify-center mt-1',
                  step.status === 'success' ? 'bg-emerald-500/20 text-emerald-400' :
                  step.status === 'error' ? 'bg-rose-500/20 text-rose-400' :
                  'bg-white/10 text-text-secondary'
                ]"
              >
                <span class="material-symbols-outlined text-lg">
                  {{ step.status === 'success' ? 'check_circle' : step.status === 'error' ? 'error' : 'radio_button_unchecked' }}
                </span>
              </div>
              <div class="flex-1">
                <p class="font-bold text-text-primary text-sm">{{ step.title || step.name }}</p>
                <p v-if="step.result && typeof step.result === 'string'" class="text-xs text-text-secondary mt-1 leading-relaxed line-clamp-2">{{ step.result }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Visual Analytics (Universal) -->
        <div class="glass-panel rounded-2xl p-6">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-lg font-bold text-white flex items-center gap-2">
               <span class="material-symbols-outlined text-accent-cyan">analytics</span> 数据可视化
            </h2>
            <button
              @click="refreshCharts"
              class="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-text-primary transition-colors text-xs font-bold flex items-center gap-2"
            >
              <span class="material-symbols-outlined text-sm">refresh</span>
              刷新
            </button>
          </div>

          <!-- Chart Tabs -->
          <div class="flex gap-2 mb-6 p-1 bg-black/20 rounded-lg w-fit">
            <button
              v-for="tab in chartTabs"
              :key="tab.id"
              @click="activeChartTab = tab.id"
              :class="[
                'px-4 py-2 rounded-md text-sm font-bold transition-all',
                activeChartTab === tab.id
                  ? 'bg-primary text-background-dark shadow-lg'
                  : 'text-text-secondary hover:text-white'
              ]"
            >
              {{ tab.label }}
            </button>
          </div>

          <!-- Charts Content -->
          <div class="space-y-6 min-h-[300px]">
             <!-- Financial -->
            <div v-if="activeChartTab === 'financial'" class="grid grid-cols-1 gap-6 animate-fade-in">
              <div class="bg-black/20 rounded-xl p-4 border border-white/5">
                <h3 class="text-xs font-bold text-text-secondary uppercase mb-4">收入趋势</h3>
                <img :src="`http://localhost:8000/api/reports/${selectedReport.id}/charts/revenue?language=${currentLanguage}`" alt="Revenue Chart" class="w-full rounded-lg opacity-90 hover:opacity-100 transition-opacity" @error="handleChartError" />
              </div>
              <div class="bg-black/20 rounded-xl p-4 border border-white/5">
                <h3 class="text-xs font-bold text-text-secondary uppercase mb-4">利润率趋势</h3>
                <img :src="`http://localhost:8000/api/reports/${selectedReport.id}/charts/profit?language=${currentLanguage}`" alt="Profit Chart" class="w-full rounded-lg opacity-90 hover:opacity-100 transition-opacity" @error="handleChartError" />
              </div>
            </div>
            
            <!-- Market -->
            <div v-if="activeChartTab === 'market'" class="grid grid-cols-1 gap-6 animate-fade-in">
              <div class="bg-black/20 rounded-xl p-4 border border-white/5">
                <h3 class="text-xs font-bold text-text-secondary uppercase mb-4">市场份额分布</h3>
                <img :src="`http://localhost:8000/api/reports/${selectedReport.id}/charts/market_share?language=${currentLanguage}`" alt="Market Share Chart" class="w-full rounded-lg opacity-90 hover:opacity-100 transition-opacity" @error="handleChartError" />
              </div>
            </div>
            
             <!-- Team & Risk -->
             <div v-if="activeChartTab === 'team_risk'" class="grid grid-cols-1 gap-6 animate-fade-in">
               <div class="bg-black/20 rounded-xl p-4 border border-white/5">
                 <h3 class="text-xs font-bold text-text-secondary uppercase mb-4">风险评估矩阵</h3>
                 <img :src="`http://localhost:8000/api/reports/${selectedReport.id}/charts/risk_matrix?language=${currentLanguage}`" alt="Risk Matrix Chart" class="w-full rounded-lg opacity-90 hover:opacity-100 transition-opacity" @error="handleChartError" />
               </div>
             </div>
          </div>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-6">
        <!-- Meta Info -->
        <div class="glass-panel rounded-2xl p-6">
          <h3 class="font-bold text-white mb-4 text-sm uppercase tracking-wider">报告详情</h3>
          <div class="space-y-4 text-sm">
            <div class="pb-3 border-b border-white/5">
              <span class="text-text-secondary block text-xs mb-1">Session ID</span>
              <p class="text-white font-mono text-xs bg-white/5 p-2 rounded break-all">{{ selectedReport.session_id || selectedReport.id }}</p>
            </div>
            <div class="pb-3 border-b border-white/5">
              <span class="text-text-secondary block text-xs mb-1">报告类型</span>
              <p class="text-white font-bold flex items-center gap-2">
                <span class="material-symbols-outlined text-base" :class="selectedReport.type === 'roundtable' ? 'text-primary' : 'text-emerald-400'">
                  {{ selectedReport.type === 'roundtable' ? 'groups' : 'article' }}
                </span>
                {{ selectedReport.type === 'roundtable' ? '圆桌会议' : (selectedReport.analysis_type || '投资分析') }}
              </p>
            </div>
            <!-- Roundtable specific info -->
            <template v-if="selectedReport.type === 'roundtable'">
              <div class="pb-3 border-b border-white/5">
                <span class="text-text-secondary block text-xs mb-1">讨论主题</span>
                <p class="text-white">{{ selectedReport.topic || selectedReport.project_name }}</p>
              </div>
              <div class="pb-3 border-b border-white/5">
                <span class="text-text-secondary block text-xs mb-1">讨论时长</span>
                <p class="text-white font-mono">{{ formatDuration(selectedReport.discussion_summary?.total_duration_seconds) }}</p>
              </div>
            </template>
            <div>
              <span class="text-text-secondary block text-xs mb-1">保存时间</span>
              <p class="text-white font-mono">{{ selectedReport.saved_at || selectedReport.created_at ? new Date(selectedReport.saved_at || selectedReport.created_at).toLocaleString('zh-CN') : 'N/A' }}</p>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="glass-panel rounded-2xl p-6">
          <h3 class="font-bold text-white mb-4 text-sm uppercase tracking-wider">操作</h3>
          <div class="space-y-3">
            <button
              @click="exportReport(selectedReport.id, 'pdf')"
              :disabled="exportLoading"
              class="w-full px-4 py-3 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white font-bold hover:shadow-glow transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              <span class="material-symbols-outlined text-lg">picture_as_pdf</span>
              {{ exportLoading ? '导出中...' : '导出 PDF' }}
            </button>
            
            <div class="grid grid-cols-2 gap-3">
                <button @click="exportReport(selectedReport.id, 'word')" class="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-text-primary transition-colors flex items-center justify-center gap-2 text-sm font-semibold">
                    <span class="material-symbols-outlined text-base text-blue-400">description</span> Word
                </button>
                <button @click="exportReport(selectedReport.id, 'excel')" class="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-text-primary transition-colors flex items-center justify-center gap-2 text-sm font-semibold">
                    <span class="material-symbols-outlined text-base text-emerald-400">table_chart</span> Excel
                </button>
            </div>

            <button class="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-text-primary hover:bg-white/10 transition-colors flex items-center justify-center gap-2 font-semibold mt-2">
              <span class="material-symbols-outlined">share</span> 分享报告
            </button>
            
            <button
              @click="confirmDelete(selectedReport.id)"
              class="w-full px-4 py-3 rounded-xl border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 transition-colors flex items-center justify-center gap-2 font-semibold mt-4"
            >
              <span class="material-symbols-outlined">delete</span> 删除报告
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Delete Confirmation Dialog -->
  <div
    v-if="showDeleteConfirm"
    class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in"
    @click="cancelDelete"
  >
    <div
      class="glass-panel border border-white/10 rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl transform transition-all scale-100"
      @click.stop
    >
      <div class="flex flex-col items-center text-center mb-6">
        <div class="w-16 h-16 rounded-full bg-rose-500/20 flex items-center justify-center mb-4 shadow-[0_0_20px_rgba(244,63,94,0.3)]">
          <span class="material-symbols-outlined text-rose-500 text-3xl">warning</span>
        </div>
        <h3 class="text-xl font-bold text-white mb-2">确认删除?</h3>
        <p class="text-sm text-text-secondary">
          您即将删除报告 <strong>"{{ reportToDelete?.project_name || reportToDelete?.company_name }}"</strong>。此操作无法撤销。
        </p>
      </div>

      <div class="flex items-center gap-4">
        <button
          @click="cancelDelete"
          class="flex-1 px-6 py-3 rounded-xl border border-white/10 text-white hover:bg-white/10 transition-colors font-bold"
        >
          取消
        </button>
        <button
          @click="deleteReport"
          class="flex-1 px-6 py-3 rounded-xl bg-gradient-to-r from-rose-500 to-rose-600 text-white hover:shadow-[0_0_15px_rgba(244,63,94,0.5)] transition-all font-bold"
        >
          确认删除
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useLanguage } from '../composables/useLanguage';
import { useToast } from '@/composables/useToast';
import { marked } from 'marked';

const route = useRoute();
const { t } = useLanguage();
const { success, error: showError } = useToast();

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true
});

// Markdown rendering function
const renderMarkdown = (text) => {
  if (!text) return '';
  try {
    return marked.parse(String(text));
  } catch (e) {
    console.error('[ReportsView] Markdown parse error:', e);
    return String(text);
  }
};

// Helper functions for report display
const getRecommendationText = (recommendation) => {
  const map = {
    'invest': '建议投资',
    'observe': '持续观察',
    'reject': '不建议投资',
    'buy': '买入',
    'hold': '持有',
    'sell': '卖出',
    'pass': '放弃'
  };
  return map[recommendation?.toLowerCase()] || recommendation || '待定';
};

const getScoreColor = (score) => {
  if (score === null || score === undefined) return 'text-text-secondary';
  const numScore = Number(score);
  if (numScore >= 80) return 'text-emerald-400';
  if (numScore >= 60) return 'text-primary';
  if (numScore >= 40) return 'text-amber-400';
  return 'text-rose-400';
};

const getScoreLabel = (key) => {
  const labels = {
    'financial': '财务',
    'market': '市场',
    'team': '团队',
    'tech': '技术',
    'technology': '技术',
    'risk': '风险',
    'overall': '综合'
  };
  return labels[key?.toLowerCase()] || key;
};

const getAnalysisSections = (pim) => {
  if (!pim) return [];

  const sections = [];
  const sectionConfig = {
    'financial': { title: '财务分析', icon: 'account_balance', iconColor: 'text-emerald-400' },
    'market': { title: '市场分析', icon: 'trending_up', iconColor: 'text-primary' },
    'technology': { title: '技术评估', icon: 'memory', iconColor: 'text-accent-cyan' },
    'team': { title: '团队评估', icon: 'groups', iconColor: 'text-accent-violet' },
    'risk': { title: '风险评估', icon: 'warning', iconColor: 'text-amber-400' }
  };

  // Try to get sections from different possible locations
  const sectionsData = pim.sections || {};

  for (const [key, config] of Object.entries(sectionConfig)) {
    // Check in sections object first
    let content = sectionsData[key]?.summary || sectionsData[key];

    // Fall back to top-level section fields
    if (!content) {
      const sectionField = pim[`${key}_section`];
      content = sectionField?.summary || sectionField;
    }

    // Also check direct analysis fields
    if (!content && key === 'market') {
      content = pim.market_analysis?.summary || pim.market_analysis;
    }
    if (!content && key === 'team') {
      content = pim.team_analysis?.summary || pim.team_analysis;
    }

    if (content && typeof content === 'string' && content.trim()) {
      sections.push({
        key,
        ...config,
        content
      });
    }
  }

  return sections;
};

const hasSWOT = (pim) => {
  return pim && (
    (pim.strengths && pim.strengths.length > 0) ||
    (pim.weaknesses && pim.weaknesses.length > 0) ||
    (pim.opportunities && pim.opportunities.length > 0) ||
    (pim.threats && pim.threats.length > 0)
  );
};

// Check if key_findings are structured objects (with category, score, etc.)
const isStructuredFindings = (findings) => {
  if (!findings || !Array.isArray(findings) || findings.length === 0) return false;
  const first = findings[0];
  return typeof first === 'object' && first !== null && (first.category || first.key_points || first.concerns);
};

const reportsData = ref([]);
const loading = ref(true);
const error = ref(null);
const selectedReport = ref(null); // For viewing report details
const showDeleteConfirm = ref(false); // Delete confirmation dialog
const reportToDelete = ref(null); // Report being deleted
const exportMenuReportId = ref(null); // Track which report's export menu is open
const exportLoading = ref(false); // Track export operation state
const showDiscussionHistory = ref(false); // Toggle for roundtable discussion history

// Agent color mapping for roundtable
const agentColors = {
  'Leader': 'bg-primary',
  '主持人': 'bg-primary',
  'MarketAnalyst': 'bg-emerald-400',
  '市场分析师': 'bg-emerald-400',
  'FinancialExpert': 'bg-accent-cyan',
  '财务专家': 'bg-accent-cyan',
  'TeamEvaluator': 'bg-accent-violet',
  '团队评估专家': 'bg-accent-violet',
  'RiskAssessor': 'bg-amber-400',
  '风险评估师': 'bg-amber-400',
  'TechSpecialist': 'bg-blue-400',
  '技术专家': 'bg-blue-400',
  'LegalAdvisor': 'bg-rose-400',
  '法务顾问': 'bg-rose-400',
  'Meeting Orchestrator': 'bg-white/50'
};

const getAgentColor = (agentName) => {
  return agentColors[agentName] || 'bg-white/30';
};

const getMessageClass = (message) => {
  const sender = message.sender;
  if (sender === 'Leader' || sender === '主持人') {
    return 'bg-primary/10 border-primary/30';
  } else if (sender === 'Meeting Orchestrator') {
    return 'bg-white/5 border-white/10';
  }
  return 'bg-white/5 border-white/10';
};

const getMessageTypeLabel = (type) => {
  const labels = {
    'broadcast': '广播',
    'private': '私聊',
    'question': '提问',
    'agreement': '同意',
    'disagreement': '反对'
  };
  return labels[type] || type;
};

const formatMessageTime = (timestamp) => {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (e) {
    return timestamp;
  }
};

const formatDuration = (seconds) => {
  if (!seconds || seconds === 0) return 'N/A';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins > 0) {
    return `${mins}分${secs}秒`;
  }
  return `${secs}秒`;
};

// Chart-related state
const activeChartTab = ref('financial'); // Default active tab
const chartTabs = [
  { id: 'financial', label: '财务分析' },
  { id: 'market', label: '市场分析' },
  { id: 'team_risk', label: '团队与风险' }
];
const currentLanguage = computed(() => {
  const lang = localStorage.getItem('language') || 'zh';
  return lang.startsWith('zh') ? 'zh' : 'en';
});

const reports = computed(() => reportsData.value.map(report => {
  // Convert backend report format to display format
  const createdDate = new Date(report.created_at);
  const formattedDate = createdDate.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });

  // Map analysis_type to display status
  const statusMap = {
    'completed': 'completed',
    'pending_review': 'in-progress',
    'draft': 'draft'
  };

  // Count how many agents were used (from steps or selected_agents)
  let agentCount = 0;
  if (report.type === 'roundtable') {
    // For roundtable, use config.num_agents or participating_agents
    agentCount = report.config?.num_agents || report.discussion_summary?.participating_agents?.length || 0;
  } else {
    agentCount = report.steps ? report.steps.filter(s => s.status === 'success').length : 0;
  }

  // Determine description based on report type
  let description = '';
  if (report.type === 'roundtable') {
    const turns = report.discussion_summary?.total_turns || report.total_turns || 0;
    description = `圆桌讨论会议 - ${turns} 轮对话`;
  } else {
    description = `${report.analysis_type || ''} analysis for ${report.company_name || ''}`;
  }

  return {
    id: report.id,
    title: report.project_name || report.topic || `${report.company_name} Analysis`,
    description: description,
    date: formattedDate,
    status: statusMap[report.status] || 'completed',
    statusText: report.type === 'roundtable' ? '圆桌会议' : t(`reports.status.${statusMap[report.status] || 'completed'}`),
    agents: agentCount,
    type: report.type || report.analysis_type
  };
}));

// Fetch reports from backend
const fetchReports = async () => {
  try {
    loading.value = true;
    error.value = null;

    const response = await fetch('http://localhost:8000/api/reports');
    if (!response.ok) {
      throw new Error(`Failed to fetch reports: ${response.statusText}`);
    }

    const data = await response.json();
    console.log('[ReportsView] Fetched reports:', data);

    reportsData.value = data.reports || [];
  } catch (err) {
    console.error('[ReportsView] Failed to fetch reports:', err);
    error.value = err.message;
    // Keep empty array on error
    reportsData.value = [];
  } finally {
    loading.value = false;
  }
};

const viewReport = async (reportId) => {
  try {
    // Reset states
    showDiscussionHistory.value = false;

    const response = await fetch(`http://localhost:8000/api/reports/${reportId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch report: ${response.statusText}`);
    }

    const data = await response.json();
    selectedReport.value = data.report;
    console.log('[ReportsView] Viewing report:', selectedReport.value);
  } catch (err) {
    console.error('[ReportsView] Failed to fetch report details:', err);
    showError('获取报告详情失败: ' + err.message);
  }
};

const closeReportView = () => {
  selectedReport.value = null;
};

// Delete functions
const confirmDelete = (reportId) => {
  const report = reportsData.value.find(r => r.id === reportId);
  if (report) {
    reportToDelete.value = report;
    showDeleteConfirm.value = true;
  }
};

const cancelDelete = () => {
  showDeleteConfirm.value = false;
  reportToDelete.value = null;
};

const deleteReport = async () => {
  if (!reportToDelete.value) return;

  try {
    const response = await fetch(`http://localhost:8000/api/reports/${reportToDelete.value.id}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new Error(`Failed to delete report: ${response.statusText}`);
    }

    const data = await response.json();
    console.log('[ReportsView] Report deleted:', data);

    // Store the deleted report id before clearing
    const deletedReportId = reportToDelete.value.id;

    // Remove from local list
    reportsData.value = reportsData.value.filter(r => r.id !== deletedReportId);

    // Close dialog
    showDeleteConfirm.value = false;
    reportToDelete.value = null;

    // If we were viewing the deleted report, close detail view
    if (selectedReport.value && selectedReport.value.id === deletedReportId) {
      selectedReport.value = null;
    }
  } catch (err) {
    console.error('[ReportsView] Failed to delete report:', err);
    showError('删除报告失败: ' + err.message);
  }
};

// Export functions
const showExportMenu = (reportId) => {
  // Toggle menu for this report
  if (exportMenuReportId.value === reportId) {
    exportMenuReportId.value = null;
  } else {
    exportMenuReportId.value = reportId;
  }
};

const exportReport = async (reportId, format) => {
  try {
    exportLoading.value = true;
    exportMenuReportId.value = null; // Close menu

    // Get language setting
    const language = localStorage.getItem('language') || 'zh';
    const langParam = language.startsWith('zh') ? 'zh' : 'en';

    // Call export API
    const url = `http://localhost:8000/api/reports/${reportId}/export/${format}?language=${langParam}`;
    console.log(`[ReportsView] Exporting report ${reportId} as ${format}, language=${langParam}`);

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Failed to export report: ${response.statusText}`);
    }

    // Get filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `report_${reportId}.${format === 'word' ? 'docx' : format === 'excel' ? 'xlsx' : 'pdf'}`;

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

    console.log(`[ReportsView] Successfully exported report as ${format}: ${filename}`);
    success(`报告已成功导出为 ${format.toUpperCase()} 格式！`);

  } catch (err) {
    console.error('[ReportsView] Failed to export report:', err);
    showError(`导出报告失败: ${err.message}`);
  } finally {
    exportLoading.value = false;
  }
};

// Close export menu when clicking outside
document.addEventListener('click', () => {
  if (exportMenuReportId.value !== null) {
    exportMenuReportId.value = null;
  }
});

// Chart functions
const refreshCharts = () => {
  // Force reload charts by updating a timestamp query parameter
  const timestamp = Date.now();
  const charts = document.querySelectorAll('img[alt*="Chart"]');
  charts.forEach(img => {
    const src = img.getAttribute('src');
    if (src) {
      // Add or update timestamp parameter
      const url = new URL(src, window.location.origin);
      url.searchParams.set('t', timestamp.toString());
      img.setAttribute('src', url.toString());
    }
  });
};

const handleChartError = (event) => {
  console.error('[ReportsView] Chart loading error:', event.target.src);
  // You could set a placeholder image or error message here
  event.target.alt = '图表加载失败';
  event.target.style.backgroundColor = '#374151';
  event.target.style.padding = '40px';
  event.target.style.textAlign = 'center';
};

onMounted(async () => { // Made async to await fetchReports if needed, though fetchReports updates reactive state so subsequent call is fine
  await fetchReports();

  // Check for sessionId in query params to auto-open report
  if (route.query.sessionId) {
    console.log('[ReportsView] Auto-opening report from session:', route.query.sessionId);
    console.log('[ReportsView] Full route query:', route.query);
    console.log('[ReportsView] Available reports:', reportsData.value.map(r => r.id || r.session_id));
    viewReport(route.query.sessionId);
  }
});
</script>

<style scoped>
/* Report Content Markdown Styling */
.report-content :deep(p) {
  margin-bottom: 1rem;
  line-height: 1.75;
}

.report-content :deep(h1),
.report-content :deep(h2),
.report-content :deep(h3),
.report-content :deep(h4) {
  color: white;
  font-weight: 700;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
}

.report-content :deep(h3) {
  font-size: 1.1rem;
  color: rgb(56, 189, 248);
}

.report-content :deep(h4) {
  font-size: 1rem;
  color: rgb(203, 213, 225);
}

.report-content :deep(ul),
.report-content :deep(ol) {
  margin-left: 1.5rem;
  margin-bottom: 1rem;
}

.report-content :deep(li) {
  margin-bottom: 0.5rem;
  line-height: 1.6;
}

.report-content :deep(strong) {
  color: white;
  font-weight: 600;
}

.report-content :deep(em) {
  color: rgb(148, 163, 184);
}

.report-content :deep(code) {
  background: rgba(255, 255, 255, 0.1);
  padding: 0.125rem 0.375rem;
  border-radius: 0.25rem;
  font-size: 0.875em;
  color: rgb(56, 189, 248);
}

.report-content :deep(blockquote) {
  border-left: 3px solid rgb(56, 189, 248);
  padding-left: 1rem;
  margin: 1rem 0;
  color: rgb(148, 163, 184);
  font-style: italic;
}

.report-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0;
}

.report-content :deep(th),
.report-content :deep(td) {
  padding: 0.75rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
  text-align: left;
}

.report-content :deep(th) {
  background: rgba(56, 189, 248, 0.1);
  color: white;
  font-weight: 600;
}

.report-content :deep(td) {
  color: rgb(203, 213, 225);
}

.report-content :deep(hr) {
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin: 1.5rem 0;
}

/* Prose Invert Override */
.prose-invert :deep(a) {
  color: rgb(56, 189, 248);
  text-decoration: none;
}

.prose-invert :deep(a:hover) {
  text-decoration: underline;
}

/* Animation */
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out;
}
</style>