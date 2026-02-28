<template>
  <div class="page-shell conversation-scroll immersive-scroll h-full min-h-0 overflow-y-auto">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h1 class="page-title page-title-gradient !text-2xl md:!text-3xl">{{ t('trading.title') }}</h1>
        <p class="page-subtitle">
          {{ t('trading.subtitle') }}
        </p>
      </div>

      <!-- Controls & Status -->
      <div class="flex flex-wrap items-center gap-2.5 md:gap-3">

        <!-- 1. Next Analysis (Pulse) -->
        <div class="flex h-10 w-full items-center gap-2.5 rounded-lg border border-white/5 bg-white/5 px-3 backdrop-blur-sm sm:w-auto md:gap-3 md:px-4">
          <div class="flex items-baseline gap-2">
            <span class="text-[10px] text-text-secondary uppercase tracking-wider font-semibold">{{ t('trading.nextAnalysis') }}</span>
            <span class="text-sm font-mono font-bold text-accent-cyan">{{ countdown }}</span>
          </div>
          <div class="w-px h-4 bg-white/10"></div>
          <button
            @click="triggerAnalysis"
            class="group p-1 rounded hover:bg-primary/20 text-primary transition-all active:scale-95 flex items-center justify-center"
            :title="t('trading.triggerNow')"
          >
            <span class="material-symbols-outlined text-lg group-hover:text-amber-400 transition-colors">bolt</span>
          </button>
        </div>

        <!-- 3. Status (State) -->
        <div class="flex h-10 w-full items-center gap-2 rounded-lg border border-white/5 bg-white/5 px-3 backdrop-blur-sm sm:w-auto">
          <span class="relative flex h-2.5 w-2.5">
             <span v-if="systemStatus.enabled" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
             <span :class="['relative inline-flex rounded-full h-2.5 w-2.5', systemStatus.enabled ? 'bg-emerald-500' : 'bg-red-500']"></span>
          </span>
          <span :class="['text-xs font-bold', systemStatus.enabled ? 'text-emerald-400' : 'text-text-secondary']">
            {{ systemStatus.enabled ? t('trading.running') : t('trading.stopped') }}
          </span>
        </div>

        <!-- 4. Actions (Control) -->
        <div class="flex w-full flex-wrap items-center gap-2 sm:w-auto">
            <!-- Start/Stop Button -->
            <button
            v-if="!systemStatus.enabled"
            @click="startTrading"
            class="flex items-center h-10 px-4 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 transition-all active:scale-95"
            >
            <span class="material-symbols-outlined mr-1.5 text-lg">play_arrow</span>
            <span class="text-sm">{{ t('trading.start') }}</span>
            </button>
            <button
            v-else
            @click="stopTrading"
            class="flex items-center h-10 px-4 rounded-lg bg-white/10 hover:bg-red-500/20 text-white hover:text-red-400 font-semibold border border-white/10 hover:border-red-500/50 transition-all active:scale-95"
            >
            <span class="material-symbols-outlined mr-1.5 text-lg">stop</span>
            <span class="text-sm">{{ t('trading.stop') }}</span>
            </button>

            <!-- Separator -->
            <div class="mx-1 hidden h-6 w-px bg-white/10 lg:block"></div>

            <!-- Team -->
            <button
            @click="showTeamModal = true"
            class="hidden lg:flex items-center h-10 px-3 rounded-lg bg-white/5 hover:bg-white/10 text-white font-medium border border-white/5 hover:border-white/10 transition-all active:scale-95"
            >
            <span class="material-symbols-outlined mr-1.5 text-lg">groups</span>
            <span class="text-xs">{{ t('trading.agentTeam') }}</span>
            </button>

            <!-- Pending Trades Alert -->
            <button
            v-if="pendingTrades.length > 0"
            @click="openPendingTradeModal(pendingTrades[0])"
            class="flex items-center h-10 px-3 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-semibold shadow-lg shadow-amber-500/20 animate-pulse transition-all active:scale-95"
            >
            <span class="material-symbols-outlined mr-1.5 text-lg">notifications_active</span>
            <span class="text-xs">{{ pendingTrades.length }} {{ t('trading.pending') }}</span>
            </button>

            <!-- Settings -->
            <button
            @click="openSettings"
            class="icon-btn"
            :title="t('trading.settings')"
            >
            <span class="material-symbols-outlined text-lg">settings</span>
            </button>
        </div>
      </div>
    </div>

    <!-- Main Content Grid -->
    <!-- Main Content (Sticky Sidebar Layout) -->
    <div class="mb-4 grid grid-cols-12 items-start gap-3 md:mb-6 md:gap-4 lg:gap-6">
      
      <!-- Left Sidebar (Sticky Control Center) -->
      <div class="col-span-12 space-y-3 md:space-y-4 lg:col-span-4 lg:sticky lg:top-6 lg:space-y-6">
        
        <!-- Account Overview -->
        <div class="section-card">
          <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
            <span class="material-symbols-outlined mr-2 text-primary">account_balance_wallet</span>
            {{ t('trading.account') }}
          </h3>

          <div class="space-y-3">
            <div class="flex justify-between items-center">
              <span class="text-text-secondary text-sm">{{ t('trading.tradingStartDate') }}</span>
              <span class="text-white">{{ tradingStartDateFormatted }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-text-secondary text-sm">{{ t('trading.startingCapital') }}</span>
              <span class="text-white font-medium">${{ formatNumber(initialCapital) }}</span>
            </div>
            <div class="flex justify-between items-center pt-2 border-t border-white/10">
              <span class="text-text-secondary">{{ t('trading.currentEquity') }}</span>
              <span class="text-2xl font-bold text-white">${{ formatNumber(account.totalEquity) }}</span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-text-secondary">{{ t('trading.totalProfit') }}</span>
              <span :class="totalProfit >= 0 ? 'text-emerald-400' : 'text-red-400'" class="font-semibold">
                {{ totalProfit >= 0 ? '+' : '' }}${{ formatNumber(totalProfit) }}
                <span class="text-sm">({{ totalProfitPercent >= 0 ? '+' : '' }}{{ totalProfitPercent.toFixed(2) }}%)</span>
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-text-secondary">{{ t('trading.maxDrawdown') }}</span>
              <span class="text-red-400 font-medium">-{{ drawdown.maxDrawdownPct?.toFixed(2) || 0 }}%</span>
            </div>
            <div v-if="btcBenchmark.startPrice > 0" class="pt-2 border-t border-white/10 space-y-2">
               <div class="flex justify-between items-center">
                 <span class="text-text-secondary text-sm">{{ t('trading.btcBenchmarkReturn') }}</span>
                 <span :class="btcBenchmark.returnPercent >= 0 ? 'text-emerald-400' : 'text-red-400'" class="text-sm">
                   {{ btcBenchmark.returnPercent >= 0 ? '+' : '' }}{{ btcBenchmark.returnPercent.toFixed(2) }}%
                 </span>
               </div>
               <div class="flex justify-between items-center">
                 <span class="text-text-secondary font-medium">{{ t('trading.excessReturn') }}</span>
                 <span :class="alpha >= 0 ? 'text-emerald-400' : 'text-red-400'" class="font-bold text-lg">
                   {{ alpha >= 0 ? '+' : '' }}{{ alpha?.toFixed(2) || 0 }}%
                 </span>
               </div>
            </div>
          </div>
        </div>

        <!-- Current Position -->
        <div class="section-card">
          <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
            <span class="material-symbols-outlined mr-2 text-accent-cyan">trending_up</span>
            {{ t('trading.position') }}
          </h3>
          <template v-if="position.hasPosition">
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span :class="['px-3 py-1 rounded-lg font-medium', position.direction === 'long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400']">
                  {{ formatDirection(position.direction) }} {{ position.leverage }}x
                </span>
                <span class="text-white font-medium">{{ position.symbol }}</span>
              </div>
              <div class="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2 sm:gap-3">
                <div><span class="text-text-secondary block">{{ t('trading.entry') }}</span><span class="text-white">${{ formatNumber(position.entryPrice) }}</span></div>
                <div><span class="text-text-secondary block">{{ t('trading.current') }}</span><span class="text-white">${{ formatNumber(position.currentPrice) }}</span></div>
                <div><span class="text-text-secondary block">TP</span><span class="text-emerald-400">{{ position.takeProfitPrice > 0 ? '$' + formatNumber(position.takeProfitPrice) : t('trading.notSet') }}</span></div>
                <div><span class="text-text-secondary block">SL</span><span class="text-red-400">{{ position.stopLossPrice > 0 ? '$' + formatNumber(position.stopLossPrice) : t('trading.notSet') }}</span></div>
              </div>
              <div class="pt-3 border-t border-white/10 flex justify-between items-center">
                 <span class="text-text-secondary">{{ t('trading.pnl') }}</span>
                 <span :class="['text-xl font-bold', position.unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-red-400']">
                   {{ position.unrealizedPnl >= 0 ? '+' : '' }}${{ formatNumber(position.unrealizedPnl) }}
                   <span class="text-sm">({{ calculatePnlPercent(position.unrealizedPnl).toFixed(2) }}%)</span>
                 </span>
              </div>
              <div class="pt-3 border-t border-white/10">
                <button @click="closePosition" :disabled="closingPosition" class="w-full px-4 py-2 rounded-lg bg-gradient-to-r from-orange-500 to-red-500 text-white font-medium hover:shadow-lg transition-all disabled:opacity-50">
                  <span class="material-symbols-outlined mr-1 align-middle text-lg">close</span>
                  {{ closingPosition ? t('trading.closing') : t('trading.closePosition') }}
                </button>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="text-center py-8 text-text-secondary">
              <span class="material-symbols-outlined text-4xl mb-2 opacity-50">do_not_disturb</span>
              <p>{{ t('trading.noPosition') }}</p>
            </div>
          </template>
        </div>


      </div>

      <!-- Right Column (Analysis & History) -->
      <div class="col-span-12 space-y-3 md:space-y-4 lg:col-span-8 lg:space-y-6">
        
        <!-- Equity Curve Chart -->
        <div class="section-card">
          <div class="flex items-center justify-between mb-4">

            <h3 class="text-lg font-semibold text-white flex items-center">
              <span class="material-symbols-outlined mr-2 text-primary">show_chart</span>
              {{ t('trading.equityCurve') }}
            </h3>
          </div>
          <div class="h-64">
            <canvas ref="equityChartCanvas"></canvas>
          </div>
        </div>

        <!-- Live Discussion (Fixed Height, Internal Scroll) -->
        <div class="section-card flex h-[56vh] min-h-0 flex-col md:h-[700px]">
          <h3 class="mb-4 flex items-center border-b border-white/5 bg-[#0f172a]/95 py-2 text-lg font-semibold text-white backdrop-blur md:sticky md:top-0 z-10">
            <span class="material-symbols-outlined mr-2 text-accent-violet">forum</span>
            {{ t('trading.discussion') }}
            <span v-if="isAnalyzing" class="ml-2 flex items-center text-primary text-sm"><span class="animate-pulse mr-1">●</span> {{ t('trading.live') }}</span>
          </h3>

          <div class="immersive-scroll flex-1 space-y-3 overflow-y-auto pr-0 md:space-y-4 md:pr-2" ref="discussionContainer">
            <div v-for="(msg, idx) in discussionMessages" :key="idx" class="p-4 rounded-xl bg-white/5 border border-white/5 transition-all hover:bg-white/10">
              <!-- Case 1: Has JSON Conclusion -->
              <div v-if="msg.parsed && msg.parsed.hasJson">
                 <details class="group mb-3">
                    <summary class="flex items-center gap-2 cursor-pointer list-none text-text-secondary hover:text-white transition-colors">
                       <span class="material-symbols-outlined text-sm group-open:rotate-180 transition-transform">expand_more</span>
                       <div class="flex items-center gap-2">
                          <span class="px-2 py-0.5 rounded bg-primary/20 text-primary text-xs font-bold">{{ msg.agentName }}</span>
                          <span class="text-xs">{{ t('trading.reasoningProcess') }}</span>
                       </div>
                    </summary>
                    <div class="mt-2 pl-6 pt-2 border-l-2 border-white/5 text-gray-400 text-sm prose prose-sm prose-invert max-w-none leading-relaxed" v-html="renderMarkdown(msg.parsed.reasoning)"></div>
                 </details>
                 
                 <!-- Always Visible Conclusion -->
                 <div class="pl-0">
                    <div class="flex items-center justify-between mb-2">
                       <span class="text-xs font-mono text-text-secondary">{{ formatTime(msg.timestamp) }}</span>
                       <span class="text-xs font-bold text-accent-cyan">{{ t('trading.decisionTicket') }}</span>
                    </div>

                    <!-- Signal Card (Visualized JSON) -->
                    <div v-if="msg.parsed.parsedJson" class="bg-[#0f172a] rounded-lg border border-white/10 p-4 relative overflow-hidden group/card shadow-sm hover:shadow-md transition-all">
                        <!-- Decorative bg -->
                        <div class="absolute top-0 right-0 w-24 h-24 bg-primary/5 rounded-full blur-xl -translate-y-1/2 translate-x-1/2"></div>

                        <!-- Compressed Header Row -->
                        <div class="relative z-10 mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2">
                             <!-- Left: Direction Badge & Leverage -->
                             <div class="flex items-center gap-3">
                                <span :class="['px-2 py-0.5 rounded text-xs font-black uppercase tracking-wider', 
                                   (msg.parsed.parsedJson.direction || '').toLowerCase() === 'long' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/20' : 
                                   (msg.parsed.parsedJson.direction || '').toLowerCase() === 'short' ? 'bg-red-500/20 text-red-400 border border-red-500/20' : 'bg-gray-500/20 text-gray-400 border border-gray-500/20']">
                                   {{ formatDirection(msg.parsed.parsedJson.direction || 'hold') }}
                                </span>
                                <span v-if="msg.parsed.parsedJson.leverage" class="text-white font-bold text-sm font-mono opacity-80">
                                   {{ msg.parsed.parsedJson.leverage }}x
                                </span>
                             </div>

                             <!-- Right: Compact Metrics -->
                             <div class="flex flex-wrap items-center gap-2 text-xs font-mono bg-black/20 rounded px-2 py-1">
                                 <div class="flex items-center gap-1.5 border-r border-white/10 pr-3">
                                     <span class="text-text-secondary text-[10px] uppercase">{{ t('trading.confidenceShort') }}</span>
                                     <span :class="['font-bold', (msg.parsed.parsedJson.confidence || 0) >= 70 ? 'text-emerald-400' : 'text-yellow-400']">
                                        {{ msg.parsed.parsedJson.confidence }}%
                                     </span>
                                 </div>
                                 <div class="flex items-center gap-1.5 border-r border-white/10 pr-3">
                                     <span class="text-text-secondary text-[10px] uppercase">TP</span>
                                     <span class="text-emerald-400 font-bold">+{{ msg.parsed.parsedJson.take_profit_percent }}%</span>
                                 </div>
                                 <div class="flex items-center gap-1.5">
                                     <span class="text-text-secondary text-[10px] uppercase">SL</span>
                                     <span class="text-red-400 font-bold">-{{ msg.parsed.parsedJson.stop_loss_percent }}%</span>
                                 </div>
                             </div>
                        </div>
                
                        <!-- Main Body: Reasoning Text (Prominent) -->
                        <div v-if="msg.parsed.parsedJson.reasoning" class="relative z-10">
                            <div class="text-sm text-gray-300 leading-relaxed opacity-90 font-light">
                                {{ msg.parsed.parsedJson.reasoning }}
                            </div>
                        </div>
                    </div>
                
                    <!-- Fallback to Raw Code if Parsing Failed -->
                    <div v-else class="prose prose-sm prose-invert max-w-none bg-[#0f172a] rounded-lg p-3 border border-white/10 shadow-inner" v-html="renderMarkdown(msg.parsed.conclusion)"></div>
                 </div>
              </div>

              <!-- Case 2: No JSON (Standard Message) -->
              <div v-else>
                 <div class="flex items-center gap-2 mb-2">
                   <span class="px-2 py-0.5 rounded bg-primary/20 text-primary text-xs font-bold">{{ msg.agentName }}</span>
                   <span class="text-text-secondary text-xs font-mono">{{ formatTime(msg.timestamp) }}</span>
                 </div>
                 <div class="text-gray-300 text-sm prose prose-sm prose-invert max-w-none leading-relaxed" v-html="renderMarkdown(msg.content)"></div>
              </div>
            </div>
            <div v-if="discussionMessages.length === 0" class="flex flex-col items-center justify-center py-20 text-text-secondary">
              <span class="material-symbols-outlined text-4xl mb-2 opacity-50">chat_bubble</span>
              <p>{{ t('trading.noMessages') }}</p>
            </div>
          </div>
        </div>


      </div>
    </div>

    <!-- Agent Performance Panel -->
    <div class="section-card">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-white flex items-center">
          <span class="material-symbols-outlined mr-2 text-accent-cyan">leaderboard</span>
          {{ t('trading.agentPerformance') }}
        </h3>
        <button
          @click="fetchAgentPerformance"
          class="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm transition-all"
        >
          <span class="material-symbols-outlined align-middle text-base mr-1">refresh</span>
          {{ t('common.refresh') }}
        </button>
      </div>

      <div v-if="agentPerformance.team_summary" class="mb-6 p-4 rounded-lg bg-white/5 border border-white/10">
        <h4 class="text-sm font-medium text-white mb-3">{{ t('trading.teamSummary') }}</h4>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span class="text-text-secondary block">{{ t('trading.totalTrades') }}</span>
            <span class="text-white font-medium">{{ agentPerformance.team_summary.total_trades || 0 }}</span>
          </div>
          <div>
            <span class="text-text-secondary block">{{ t('trading.winRate') }}</span>
            <span :class="(agentPerformance.team_summary.win_rate || 0) >= 0.5 ? 'text-emerald-400' : 'text-red-400'" class="font-medium">
              {{ ((agentPerformance.team_summary.win_rate || 0) * 100).toFixed(1) }}%
            </span>
          </div>
          <div>
            <span class="text-text-secondary block">{{ t('trading.totalPnlLabel') }}</span>
            <span :class="(agentPerformance.team_summary.total_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'" class="font-medium">
              {{ (agentPerformance.team_summary.total_pnl || 0) >= 0 ? '+' : '' }}${{ formatNumber(agentPerformance.team_summary.total_pnl || 0) }}
            </span>
          </div>
          <div>
            <span class="text-text-secondary block">{{ t('trading.avgPnl') }}</span>
            <span :class="(agentPerformance.team_summary.avg_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'" class="font-medium">
              {{ (agentPerformance.team_summary.avg_pnl || 0) >= 0 ? '+' : '' }}${{ formatNumber(agentPerformance.team_summary.avg_pnl || 0) }}
            </span>
          </div>
        </div>
      </div>

      <div class="space-y-3 md:hidden">
        <article
          v-for="(agent, agentId) in agentPerformance.agents"
          :key="`mobile_${agentId}`"
          class="rounded-xl border border-white/10 bg-white/5 p-3"
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <p class="truncate text-sm font-semibold text-white">{{ agent.agent_name || agentId }}</p>
            <span :class="(agent.win_rate || 0) >= 0.5 ? 'text-emerald-400' : 'text-red-400'" class="text-xs font-semibold">
              {{ ((agent.win_rate || 0) * 100).toFixed(1) }}%
            </span>
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs text-text-secondary">
            <p>{{ t('trading.totalTrades') }}: <span class="text-white">{{ agent.total_trades || 0 }}</span></p>
            <p>{{ t('trading.wins') }}: <span class="text-white">{{ agent.wins || 0 }}</span></p>
            <p>{{ t('trading.totalPnlLabel') }}:
              <span :class="(agent.total_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'" class="font-semibold">
                {{ (agent.total_pnl || 0) >= 0 ? '+' : '' }}${{ formatNumber(agent.total_pnl || 0) }}
              </span>
            </p>
            <p class="truncate">{{ t('trading.latestLesson') }}: <span class="text-white">{{ agent.lessons_learned?.slice(-1)?.[0] || '-' }}</span></p>
          </div>
        </article>

        <div v-if="!agentPerformance.agents || Object.keys(agentPerformance.agents).length === 0" class="text-center py-6 text-text-secondary">
          {{ t('trading.noAgentData') }}
        </div>
      </div>

      <div class="hidden overflow-x-auto md:block">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-text-secondary border-b border-white/10">
              <th class="text-left py-3 px-4">{{ t('trading.agent') }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.totalTrades') }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.wins') }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.winRate') }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.totalPnlLabel') }}</th>
              <th class="text-left py-3 px-4">{{ t('trading.latestLesson') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(agent, agentId) in agentPerformance.agents"
              :key="agentId"
              class="border-b border-white/5 hover:bg-white/5"
            >
              <td class="py-3 px-4">
                <div class="flex items-center gap-2">
                  <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                    <span class="material-symbols-outlined text-primary text-sm">person</span>
                  </div>
                  <span class="text-white font-medium">{{ agent.agent_name || agentId }}</span>
                </div>
              </td>
              <td class="py-3 px-4 text-right text-white">{{ agent.total_trades || 0 }}</td>
              <td class="py-3 px-4 text-right text-white">{{ agent.wins || 0 }}</td>
              <td class="py-3 px-4 text-right" :class="(agent.win_rate || 0) >= 0.5 ? 'text-emerald-400' : 'text-red-400'">
                {{ ((agent.win_rate || 0) * 100).toFixed(1) }}%
              </td>
              <td class="py-3 px-4 text-right" :class="(agent.total_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'">
                {{ (agent.total_pnl || 0) >= 0 ? '+' : '' }}${{ formatNumber(agent.total_pnl || 0) }}
              </td>
              <td class="py-3 px-4 text-text-secondary max-w-xs truncate">
                {{ agent.lessons_learned?.slice(-1)?.[0] || '-' }}
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="!agentPerformance.agents || Object.keys(agentPerformance.agents).length === 0" class="text-center py-8 text-text-secondary">
          {{ t('trading.noAgentData') }}
        </div>
      </div>
    </div>

    <!-- Trade History (Full Width Bottom) -->
    <div class="section-card">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-white flex items-center">
          <span class="material-symbols-outlined mr-2 text-primary">history</span>
          {{ t('trading.history') }}
        </h3>
        <button @click="fetchTradeHistory" class="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm transition-all flex items-center">
           <span class="material-symbols-outlined text-sm mr-1">refresh</span> {{ t('common.refresh') }}
        </button>
      </div>
      <div class="space-y-2.5 md:hidden">
        <article
          v-for="trade in tradeHistory"
          :key="`mobile_trade_${trade.id}`"
          class="rounded-xl border border-white/10 bg-white/5 p-3"
        >
          <div class="mb-2 flex items-center justify-between gap-2">
            <span :class="['rounded px-2 py-0.5 text-xs font-bold', trade.direction === 'long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400']">
              {{ formatDirection(trade.direction) }}
            </span>
            <span class="text-xs text-text-secondary">{{ formatDate(trade.timestamp) }}</span>
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs text-text-secondary">
            <p>{{ t('trading.entryPrice') }}: <span class="text-white">${{ formatNumber(trade.entryPrice) }}</span></p>
            <p>{{ t('trading.pnl') }}:
              <span :class="(trade.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'" class="font-semibold">
                {{ (trade.pnl || 0) >= 0 ? '+' : '' }}${{ formatNumber(trade.pnl || 0) }}
              </span>
            </p>
          </div>
        </article>
        <div v-if="tradeHistory.length === 0" class="py-6 text-center text-text-secondary">{{ t('trading.noTrades') }}</div>
      </div>

      <div class="hidden max-h-[500px] overflow-y-auto md:block">
         <table class="w-full text-sm">
            <thead><tr class="text-text-secondary border-b border-white/10 sticky top-0 bg-[#0f172a] z-10"><th class="text-left py-3 px-4">{{ t('trading.time') }}</th><th class="text-left py-3 px-4">{{ t('trading.direction') }}</th><th class="text-right py-3 px-4">{{ t('trading.entryPrice') }}</th><th class="text-right py-3 px-4">{{ t('trading.pnl') }}</th></tr></thead>
            <tbody>
              <tr v-for="trade in tradeHistory" :key="trade.id" class="border-b border-white/5 hover:bg-white/5 transition-colors">
                <td class="py-3 px-4 text-white font-mono">{{ formatDate(trade.timestamp) }}</td>
                <td class="py-3 px-4"><span :class="['px-2 py-1 rounded text-xs font-bold', trade.direction === 'long' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400']">{{ formatDirection(trade.direction) }}</span></td>
                <td class="py-3 px-4 text-right text-white font-mono">${{ formatNumber(trade.entryPrice) }}</td>
                <td class="py-3 px-4 text-right"><span :class="['font-bold', (trade.pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400']">{{ (trade.pnl || 0) >= 0 ? '+' : '' }}${{ formatNumber(trade.pnl || 0) }}</span></td>
              </tr>
              <tr v-if="tradeHistory.length === 0"><td colspan="4" class="text-center py-8 text-text-secondary">{{ t('trading.noTrades') }}</td></tr>
            </tbody>
         </table>
      </div>
    </div>

    <!-- Settings Modal -->
    <div
      v-if="showSettings"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showSettings = false"
    >
      <div class="modal-shell max-w-md mx-4">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-semibold text-white flex items-center">
            <span class="material-symbols-outlined mr-2 text-primary">settings</span>
            {{ t('trading.settings') }}
          </h3>
          <button @click="showSettings = false" class="text-text-secondary hover:text-white">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <!-- Loading indicator -->
        <div v-if="loadingConfig" class="text-center py-8">
          <span class="material-symbols-outlined animate-spin text-primary text-3xl">refresh</span>
          <p class="text-text-secondary mt-2">{{ t('trading.loadingConfig') }}</p>
        </div>

        <div v-else class="space-y-4">
          <!-- Trader Backend Toggle -->
          <div class="p-4 rounded-lg bg-white/5 border border-white/10">
            <div class="flex items-center justify-between">
	              <div>
	                <h4 class="text-sm font-medium text-white">{{ t('trading.traderBackend') }}</h4>
	                <p class="text-xs text-text-secondary mt-1">
	                  {{ settingsForm.useOkxTrading ? `OKX (${settingsForm.okxDemoMode ? t('trading.okxDemoLabel') : t('trading.okxLiveLabel')})` : t('trading.localPaperTrading') }}
	                </p>
	              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  v-model="settingsForm.useOkxTrading"
                  class="sr-only peer"
                >
                <div class="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
		                <span class="ml-2 text-sm text-white">OKX</span>
	              </label>
	            </div>
	            <div v-if="settingsForm.useOkxTrading" class="mt-3 space-y-3">
              <p class="text-xs text-text-secondary">
	                {{ t('trading.currentOkxCredentials') }}:
                <span v-if="settingsForm.okxConfigured" class="text-emerald-400 font-mono">****{{ settingsForm.okxApiKeyLast4 }}</span>
	                <span v-else class="text-amber-400">{{ t('trading.notConfigured') }}</span>
              </p>
              <div class="grid grid-cols-1 gap-2">
                <input
                  v-model="settingsForm.okxApiKey"
                  type="text"
                  autocomplete="off"
	                  :placeholder="t('trading.okxApiKey')"
                  class="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder:text-white/40 focus:outline-none focus:border-primary"
                />
                <input
                  v-model="settingsForm.okxSecretKey"
                  type="password"
                  autocomplete="off"
	                  :placeholder="t('trading.okxSecretKey')"
                  class="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder:text-white/40 focus:outline-none focus:border-primary"
                />
                <input
                  v-model="settingsForm.okxPassphrase"
                  type="password"
                  autocomplete="off"
	                  :placeholder="t('trading.okxPassphrase')"
                  class="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white placeholder:text-white/40 focus:outline-none focus:border-primary"
                />
              </div>
	              <div class="flex items-center justify-between">
	                <label class="flex items-center gap-2 text-xs text-text-secondary">
	                  <input type="checkbox" v-model="settingsForm.okxDemoMode" class="accent-primary" />
		                  {{ t('trading.okxDemoModeLabel') }}
	                </label>
                <button
                  v-if="settingsForm.okxConfigured"
                  @click="clearOkxCredentials"
                  class="text-xs text-red-400 hover:text-red-300 underline"
                  type="button"
                >
	                  {{ t('trading.clearOkxCredentials') }}
                </button>
	              </div>
	              <p v-if="!settingsForm.okxDemoMode" class="text-xs text-red-400">
		                {{ t('trading.okxLiveWarning') }}
	              </p>
	            </div>
	          </div>

          <!-- Analysis Interval -->
          <div>
            <label class="block text-sm text-text-secondary mb-2">
              {{ t('trading.analysisInterval') }}
            </label>
            <select
              v-model="settingsForm.analysisInterval"
              class="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:border-primary"
            >
              <option value="1">{{ t('trading.hour1') }}</option>
              <option value="2">{{ t('trading.hour2') }}</option>
              <option value="4">{{ t('trading.hour4') }}</option>
              <option value="6">{{ t('trading.hour6') }}</option>
              <option value="12">{{ t('trading.hour12') }}</option>
              <option value="24">{{ t('trading.hour24') }}</option>
            </select>
          </div>

          <!-- Max Leverage -->
          <div>
            <label class="block text-sm text-text-secondary mb-2">
              {{ t('trading.maxLeverage') }}
            </label>
            <select
              v-model="settingsForm.maxLeverage"
              class="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:border-primary"
            >
              <option v-for="lev in 20" :key="lev" :value="lev">
                {{ lev }}x{{ lev === 1 ? ' ' + t('trading.noLeverage') : '' }}
              </option>
            </select>
          </div>

          <!-- Max Position Percent -->
          <div>
            <label class="block text-sm text-text-secondary mb-2">
              {{ t('trading.maxPositionPercent') }}
            </label>
            <select
              v-model="settingsForm.maxPositionPercent"
              class="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:border-primary"
            >
              <option value="0.1">10%</option>
              <option value="0.2">20%</option>
              <option value="0.3">30%</option>
              <option value="0.5">50%</option>
              <option value="1.0">100%</option>
            </select>
          </div>
        </div>

        <!-- Reset Section -->
        <div class="mt-6 pt-4 border-t border-white/10">
          <div class="flex items-center justify-between">
            <div>
              <h4 class="text-sm font-medium text-white">{{ t('trading.resetSystem') }}</h4>
              <p class="text-xs text-text-secondary mt-1">
                {{ t('trading.resetDescription') }}
              </p>
            </div>
            <button
              @click="resetSystem"
              :disabled="resettingSystem"
              class="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all disabled:opacity-50 flex items-center gap-2"
            >
              <span v-if="resettingSystem" class="material-symbols-outlined animate-spin text-sm">refresh</span>
              <span class="material-symbols-outlined text-sm" v-else>restart_alt</span>
              {{ resettingSystem ? t('trading.resetting') : t('trading.reset') }}
            </button>
          </div>
        </div>

        <div class="flex gap-3 mt-6">
          <button
            @click="showSettings = false"
            class="flex-1 px-4 py-2 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-all"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            @click="saveSettings"
            :disabled="savingSettings"
            class="flex-1 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-accent-cyan text-white font-medium hover:shadow-lg transition-all disabled:opacity-50"
          >
            {{ savingSettings ? t('trading.saving') : t('common.save') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Decision Confirmation Modal -->
    <div
      v-if="showDecisionModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50"
    >
      <div class="modal-shell max-w-lg mx-4 border border-primary/30 shadow-2xl">
        <!-- Header -->
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-white flex items-center">
            <span class="material-symbols-outlined mr-2 text-primary animate-pulse">smart_toy</span>
	            {{ t('trading.committeeDecision') }}
          </h3>
          <span class="px-2 py-1 rounded text-xs bg-amber-500/20 text-amber-400">
	            {{ t('trading.pendingConfirmation') }}
          </span>
        </div>

        <!-- Signal Details -->
        <div class="bg-white/5 rounded-lg p-4 mb-4">
          <div class="mb-4 grid grid-cols-1 gap-3 text-center sm:grid-cols-3 sm:gap-4">
            <div>
	              <span class="text-text-secondary text-xs block mb-1">{{ t('trading.direction') }}</span>
              <span
                :class="[
                  'px-3 py-1 rounded-lg font-bold text-lg',
                  (showModifyPanel ? modifiedDirection : pendingDecision.direction) === 'long'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-red-500/20 text-red-400'
                ]"
              >
                {{ formatDirectionWithArrow(showModifyPanel ? modifiedDirection : pendingDecision.direction) }}
              </span>
            </div>
            <div>
	              <span class="text-text-secondary text-xs block mb-1">{{ t('trading.leverage') }}</span>
              <span class="text-white font-bold text-lg">{{ modifiedLeverage }}x</span>
            </div>
            <div>
	              <span class="text-text-secondary text-xs block mb-1">{{ t('trading.confidence') }}</span>
              <span 
                :class="[
                  'font-bold text-lg',
                  pendingDecision.confidence >= 70 ? 'text-emerald-400' : 
                  pendingDecision.confidence >= 50 ? 'text-yellow-400' : 'text-red-400'
                ]"
              >
                {{ pendingDecision.confidence }}%
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2 sm:gap-4">
            <div class="flex justify-between">
	              <span class="text-text-secondary">{{ t('trading.takeProfit') }}</span>
              <span class="text-emerald-400 font-medium">
                ${{ formatNumber(pendingDecision.take_profit) }}
                <span class="text-xs">(+{{ ((pendingDecision.take_profit / pendingDecision.current_price - 1) * 100).toFixed(1) }}%)</span>
              </span>
            </div>
            <div class="flex justify-between">
	              <span class="text-text-secondary">{{ t('trading.stopLoss') }}</span>
              <span class="text-red-400 font-medium">
                ${{ formatNumber(pendingDecision.stop_loss) }}
                <span class="text-xs">({{ ((pendingDecision.stop_loss / pendingDecision.current_price - 1) * 100).toFixed(1) }}%)</span>
              </span>
            </div>
          </div>
        </div>

        <!-- Leader Reasoning -->
        <div class="immersive-scroll bg-white/5 rounded-lg p-4 mb-4 max-h-32 overflow-y-auto">
          <div class="text-text-secondary text-xs mb-2 flex items-center">
            <span class="material-symbols-outlined text-sm mr-1">psychology</span>
	            {{ t('trading.leaderRationale') }}
          </div>
          <p class="text-white text-sm leading-relaxed">
	            {{ pendingDecision.reasoning || t('trading.defaultRationale') }}
          </p>
        </div>

        <!-- Modification Panel -->
        <div v-if="showModifyPanel" class="bg-white/5 rounded-lg p-4 mb-4 border border-primary/30">
	          <div class="text-text-secondary text-xs mb-3">{{ t('trading.modifyParameters') }}</div>

          <!-- Direction Toggle -->
          <div class="flex items-center gap-4 mb-3">
	            <label class="text-sm text-white w-20">{{ t('trading.direction') }}:</label>
            <div class="flex gap-2 flex-1">
              <button
                @click="modifiedDirection = 'long'"
                :class="[
                  'flex-1 px-3 py-2 rounded-lg text-sm font-bold transition-all',
                  modifiedDirection === 'long'
                    ? 'bg-emerald-500/30 text-emerald-400 border border-emerald-500/50'
                    : 'bg-white/5 text-text-secondary hover:bg-white/10'
                ]"
              >{{ formatDirectionWithArrow('long') }}</button>
              <button
                @click="modifiedDirection = 'short'"
                :class="[
                  'flex-1 px-3 py-2 rounded-lg text-sm font-bold transition-all',
                  modifiedDirection === 'short'
                    ? 'bg-red-500/30 text-red-400 border border-red-500/50'
                    : 'bg-white/5 text-text-secondary hover:bg-white/10'
                ]"
              >{{ formatDirectionWithArrow('short') }}</button>
            </div>
          </div>

          <!-- Leverage Slider -->
          <div class="flex items-center gap-4 mb-3">
	            <label class="text-sm text-white w-20">{{ t('trading.leverage') }}:</label>
            <input
              type="range"
              v-model="modifiedLeverage"
              :min="1"
              :max="20"
              class="flex-1"
            />
            <span class="text-primary font-bold w-12 text-right">{{ modifiedLeverage }}x</span>
          </div>

          <!-- Amount Percent Slider -->
          <div class="flex items-center gap-4">
	            <label class="text-sm text-white w-20">{{ t('trading.positionSize') }}:</label>
            <input
              type="range"
              v-model.number="modifiedAmountPercent"
              :min="0.1"
              :max="1.0"
              :step="0.1"
              class="flex-1"
            />
            <span class="text-primary font-bold w-12 text-right">{{ (modifiedAmountPercent * 100).toFixed(0) }}%</span>
          </div>
        </div>

        <!-- Defer Reasons (shown when deferring) -->
        <div v-if="showDeferReasons" class="bg-white/5 rounded-lg p-4 mb-4 border border-red-500/30">
	          <div class="text-text-secondary text-xs mb-3">{{ t('trading.selectDeferReason') }}</div>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <label 
              v-for="reason in deferReasonOptions" 
              :key="reason"
              class="flex items-center gap-2 text-sm text-white cursor-pointer p-2 rounded hover:bg-white/10"
            >
              <input 
                type="radio" 
                :value="reason" 
                v-model="selectedDeferReason"
                class="accent-primary"
              />
              {{ reason }}
            </label>
          </div>
          <input
	            v-if="selectedDeferReason === t('trading.other')"
            v-model="customDeferReason"
            type="text"
	            :placeholder="t('trading.enterReason')"
            class="mt-2 w-full px-3 py-2 rounded bg-white/10 border border-white/20 text-white text-sm"
          />
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-3">
          <button
            @click="handleConfirmDecision"
            :disabled="processingDecision"
            class="flex-1 px-4 py-3 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-medium hover:shadow-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <span class="material-symbols-outlined text-lg">check_circle</span>
	            {{ t('trading.confirmExecution') }}
          </button>
          <button
            @click="toggleModifyPanel"
            :disabled="processingDecision"
            class="px-4 py-3 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <span class="material-symbols-outlined text-lg">edit</span>
	            {{ t('trading.modify') }}
          </button>
          <button
            @click="toggleDeferReasons"
            :disabled="processingDecision"
            class="px-4 py-3 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <span class="material-symbols-outlined text-lg">close</span>
	            {{ t('trading.defer') }}
          </button>
        </div>

        <!-- Confirm Defer Button (shown after selecting reason) -->
        <button
          v-if="showDeferReasons && selectedDeferReason"
          @click="handleDeferDecision"
          :disabled="processingDecision"
          class="w-full mt-3 px-4 py-2 rounded-lg bg-red-500 text-white font-medium hover:bg-red-600 transition-all disabled:opacity-50"
        >
	          {{ t('trading.confirmDeferral') }}
        </button>

        <!-- User Responsibility Notice -->
        <div class="mt-4 text-center text-xs text-text-secondary">
          <span class="material-symbols-outlined text-sm align-middle mr-1">info</span>
	          {{ t('trading.reviewNotice') }}
        </div>
      </div>
    </div>
  </div>


  <!-- Expert Team Modal -->
  <div v-if="showTeamModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm" @click.self="showTeamModal = false">
    <div class="immersive-scroll bg-[#0f172a] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl relative animate-fadeIn">
       <div class="p-6 border-b border-white/10 flex justify-between items-center sticky top-0 bg-[#0f172a] z-10">
         <h3 class="text-xl font-bold text-white flex items-center">
           <span class="material-symbols-outlined mr-2 text-accent-cyan">groups</span>
	           {{ t('trading.agentTeam') }}
         </h3>
         <button @click="showTeamModal = false" class="text-text-secondary hover:text-white transition-colors">
           <span class="material-symbols-outlined text-2xl">close</span>
         </button>
       </div>
       <div class="p-6">
         <!-- Team Agent List -->
         <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div v-for="agent in agents" :key="agent.id" class="p-4 rounded-xl bg-white/5 border border-white/5 hover:border-primary/30 transition-all group">
               <div class="flex items-start gap-4">
                  <div class="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/30 transition-colors">
                    <span class="material-symbols-outlined text-primary text-xl">{{ agent.icon }}</span>
                  </div>
                  <div>
                    <h4 class="text-white font-bold">{{ agent.name }}</h4>
                    <p class="text-xs text-text-secondary mt-1">{{ agent.role }}</p>
                    <div class="flex items-center gap-3 mt-3 text-xs">
	                       <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">{{ t('trading.win') }}: {{ (agent.winRate * 100).toFixed(0) }}%</span>
                       <span class="text-text-secondary">{{ t('trading.totalTrades') }}: {{ agent.totalTrades }}</span>
                    </div>
                  </div>
               </div>
            </div>
         </div>
       </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';
import { apiUrl, wsUrl as buildWsUrl } from '@/config/api';
import { appendTokenToUrl, getAuthHeaders } from '@/services/authHeaders';
import { readJsonResponse } from '@/services/httpResponse';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import Chart from 'chart.js/auto';
import { marked } from 'marked';

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true
});

const { t, locale } = useLanguage();
const router = useRouter();
const authStore = useAuthStore();

// Chart
const equityChartCanvas = ref(null);
let equityChart = null;

// Refs
const discussionContainer = ref(null);
const showTeamModal = ref(false);

// State
const systemStatus = ref({
  enabled: false,
  scheduler: null
});

const account = ref({
  totalEquity: 0,
  availableBalance: 0,
  unrealizedPnl: 0,
  initialBalance: 0  // Track initial balance for PnL calculation
});

const position = ref({
  hasPosition: false,
  symbol: 'BTC-USDT-SWAP',
  direction: 'long',
  leverage: 1,
  size: 0,
  entryPrice: 0,
  currentPrice: 0,
  takeProfitPrice: 0,
  stopLossPrice: 0,
  unrealizedPnl: 0,
  unrealizedPnlPercent: 0
});

const buildDefaultAgents = (lang) => {
  const zh = String(lang || '').startsWith('zh');
  if (zh) {
    return [
      { id: 'technical-analyst', name: '技术分析师', role: '技术面', icon: 'candlestick_chart', winRate: 0.65 },
      { id: 'macro-economist', name: '宏观分析师', role: '宏观', icon: 'public', winRate: 0.58 },
      { id: 'sentiment-analyst', name: '情绪分析师', role: '情绪', icon: 'psychology', winRate: 0.62 },
      { id: 'onchain-analyst', name: '链上分析师', role: '链上', icon: 'link', winRate: 0.60 },
      { id: 'risk-manager', name: '风险管理师', role: '风险', icon: 'shield', winRate: 0.70 },
      { id: 'quant-strategist', name: '量化策略师', role: '量化', icon: 'analytics', winRate: 0.55 },
      { id: 'trading-executor', name: '交易执行师', role: '执行', icon: 'play_arrow', winRate: 0 },
      { id: 'position-monitor', name: '仓位监控师', role: '监控', icon: 'monitoring', winRate: 0 },
      { id: 'trading-leader', name: '主持人', role: '协调', icon: 'emoji_events', winRate: 0.68 }
    ];
  }
  return [
    { id: 'technical-analyst', name: 'Technical Analyst', role: 'Technical', icon: 'candlestick_chart', winRate: 0.65 },
    { id: 'macro-economist', name: 'Macro Analyst', role: 'Macro', icon: 'public', winRate: 0.58 },
    { id: 'sentiment-analyst', name: 'Sentiment Analyst', role: 'Sentiment', icon: 'psychology', winRate: 0.62 },
    { id: 'onchain-analyst', name: 'On-chain Analyst', role: 'On-chain', icon: 'link', winRate: 0.60 },
    { id: 'risk-manager', name: 'Risk Management', role: 'Risk', icon: 'shield', winRate: 0.70 },
    { id: 'quant-strategist', name: 'Quant Strategy', role: 'Quant', icon: 'analytics', winRate: 0.55 },
    { id: 'trading-executor', name: 'Trade Execution', role: 'Execution', icon: 'play_arrow', winRate: 0 },
    { id: 'position-monitor', name: 'Position Monitor', role: 'Monitoring', icon: 'monitoring', winRate: 0 },
    { id: 'trading-leader', name: 'Host', role: 'Coordination', icon: 'emoji_events', winRate: 0.68 }
  ];
};

const agents = ref(buildDefaultAgents(locale.value));

const discussionMessages = ref([]);
const tradeHistory = ref([]);
const equityHistory = ref([]);
const isAnalyzing = ref(false);
const countdown = ref('--:--:--');
const closingPosition = ref(false);
const showSettings = ref(false);
const showAgentPerformance = ref(false);
const agentPerformance = ref({ team_summary: null, agents: {} });
const savingSettings = ref(false);
const resettingSystem = ref(false);
const settingsForm = ref({
  analysisInterval: 4,
  maxLeverage: 20,
  maxPositionPercent: 0.3,
  useOkxTrading: false,  // Whether to use OKX demo trading
  okxConfigured: false,
  okxApiKeyLast4: '',
  okxDemoMode: true,
  okxApiKey: '',
  okxSecretKey: '',
  okxPassphrase: ''
});
const loadingConfig = ref(false);

// Pending Trades (HITL Semi-Auto Mode)
const pendingTrades = ref([]);

// Decision Confirmation Modal State
const showDecisionModal = ref(false);
const pendingDecision = ref({
  decision_id: '',
  direction: 'long',
  leverage: 5,
  confidence: 0,
  take_profit: 0,
  stop_loss: 0,
  current_price: 0,
  reasoning: ''
});
const modifiedLeverage = ref(5);
const modifiedDirection = ref('long');
const modifiedAmountPercent = ref(0.5);
const showModifyPanel = ref(false);
const showDeferReasons = ref(false);
const selectedDeferReason = ref('');
const customDeferReason = ref('');
const processingDecision = ref(false);
const deferReasonOptions = computed(() => ([
  t('trading.deferReasonLeverage'),
  t('trading.deferReasonDirection'),
  t('trading.deferReasonStopLoss'),
  t('trading.deferReasonUncertain'),
  t('trading.other')
]));
const decisionHistory = ref([]);  // Store user decisions for display

watch(locale, (newLocale) => {
  agents.value = buildDefaultAgents(newLocale);
});

// Drawdown data
const drawdownStartDate = ref('');
const drawdown = ref({
  maxDrawdownPct: 0,
  maxDrawdownUsd: 0,
  currentDrawdownPct: 0,
  peakEquity: 0,
  troughEquity: 0,
  currentEquity: 0,
  recoveryPct: 100,
  tradesAnalyzed: 0
});

// Performance metrics from backend API
const performanceData = ref({
  sharpeRatio: 0,
  sortinoRatio: 0,
  alpha: 0,
  winRate: 0,
  profitFactor: 0,
  totalReturnPct: 0,
  annualizedReturnPct: 0,
  volatilityPct: 0,
  bestTrade: 0,
  worstTrade: 0,
  avgHoldingHours: 0,
  tradesAnalyzed: 0
});

// Phase 0-3: MTF, Agent Weights, Degradation

const mtfAnalysis = ref({
  overall_direction: 'neutral',
  alignment_score: 0,
  confidence_modifier: 1.0,
  recommendation: ''
});

const learnedWeights = ref({
  TechnicalAnalyst: 1.0,
  FundamentalAnalyst: 1.0,
  SentimentAnalyst: 1.0,
  RiskManager: 1.0,
  OnchainAnalyst: 1.0
});

const systemHealth = ref({
  level: 'full',
  capabilities: {}
});


// WebSocket
let ws = null;
let countdownInterval = null;
let tokenRefreshPromise = null;
let authRedirecting = false;
const authExpired = ref(false);

// Computed
// Initial capital from backend API (via account.initialBalance)
const initialCapital = computed(() => {
  return account.value.initialBalance || account.value.totalEquity || 10000;
});

// Trading start date - earliest trade timestamp
const tradingStartDate = computed(() => {
  if (!tradeHistory.value || tradeHistory.value.length === 0) return null;
  // Find the earliest trade
  const sorted = [...tradeHistory.value].sort((a, b) =>
    new Date(a.timestamp) - new Date(b.timestamp)
  );
  return sorted[0]?.timestamp ? new Date(sorted[0].timestamp) : null;
});

// Format trading start date for display
const tradingStartDateFormatted = computed(() => {
  if (!tradingStartDate.value) return '--';
  const dateLocale = String(locale.value || '').startsWith('en') ? 'en-US' : 'zh-CN';
  return tradingStartDate.value.toLocaleDateString(dateLocale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
});

// Total profit = current equity - initial capital (from API)
const totalProfit = computed(() => {
  return account.value.totalEquity - initialCapital.value;
});

// Total profit percent
const totalProfitPercent = computed(() => {
  if (initialCapital.value === 0) return 0;
  return (totalProfit.value / initialCapital.value) * 100;
});

// Use initial_balance from account API for accurate PnL calculation
const totalPnl = computed(() => {
  return account.value.totalEquity - initialCapital.value;
});
const totalPnlPercent = computed(() => {
  if (initialCapital.value === 0) return 0;
  return (totalPnl.value / initialCapital.value) * 100;
});

// BTC benchmark data for alpha calculation
const btcBenchmark = ref({
  startPrice: 0,       // BTC price when trading started
  currentPrice: 0,     // Current BTC price
  returnPercent: 0,    // BTC return %
  loading: false
});

// Alpha = System return - BTC return (excess return)
const alpha = computed(() => {
  if (!btcBenchmark.value.startPrice || btcBenchmark.value.returnPercent === 0) {
    return null;  // Not enough data
  }
  return totalProfitPercent.value - btcBenchmark.value.returnPercent;
});

// Performance metrics from backend API (no longer calculated locally)
const performanceMetrics = computed(() => {
  // Use backend data from performanceData ref
  return {
    winRate: performanceData.value.winRate || 0,
    pnlRatio: performanceData.value.profitFactor || 0,
    sharpeRatio: performanceData.value.sharpeRatio || 0,
    sortinoRatio: performanceData.value.sortinoRatio || 0,
    totalTrades: performanceData.value.tradesAnalyzed || 0,
    volatility: performanceData.value.volatilityPct || 0,
    bestTrade: performanceData.value.bestTrade || 0,
    worstTrade: performanceData.value.worstTrade || 0,
    avgHoldingHours: performanceData.value.avgHoldingHours || 0,
    annualizedReturn: performanceData.value.annualizedReturnPct || 0
  };
});


// Dynamic interval text based on actual scheduler state
const intervalText = computed(() => {
  // Prefer actual scheduler state over settings form
  const hours = systemStatus.value.scheduler?.interval_hours || settingsForm.value.analysisInterval || 4;
  const lang = locale.value || localStorage.getItem('locale') || 'zh-CN';
  if (lang.startsWith('en')) {
    return `Analysis every ${hours} hour${hours > 1 ? 's' : ''}`;
  }
  return `每 ${hours} 小时分析一次`;
});

// Methods
function formatNumber(num) {
  if (num === undefined || num === null) return '0.00';
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Calculate PnL percent based on total equity (return on capital)
// PnL% = unrealizedPnl / (totalEquity - unrealizedPnl) * 100
function calculatePnlPercent(unrealizedPnl) {
  const totalEquity = account.value.totalEquity || 0;
  const initialEquity = totalEquity - (unrealizedPnl || 0);
  if (initialEquity <= 0) return 0;
  return (unrealizedPnl / initialEquity) * 100;
}

// Render markdown content to HTML
function renderMarkdown(content) {
  if (!content) return '';
  try {
    return marked(content);
  } catch (e) {
    console.error('Error rendering markdown:', e);
    return content;
  }
}

function formatDate(timestamp) {
  if (!timestamp) return '';
  const dateLocale = String(locale.value || '').startsWith('en') ? 'en-US' : 'zh-CN';
  return new Date(timestamp).toLocaleString(dateLocale);
}

function formatTime(timestamp) {
  if (!timestamp) return '';
  const dateLocale = String(locale.value || '').startsWith('en') ? 'en-US' : 'zh-CN';
  return new Date(timestamp).toLocaleTimeString(dateLocale);
}

function normalizeDirection(direction) {
  const raw = String(direction || '').trim().toLowerCase();
  if (raw === 'buy') return 'long';
  if (raw === 'sell') return 'short';
  return raw;
}

function formatDirection(direction) {
  const normalized = normalizeDirection(direction);
  if (normalized === 'long') return t('trading.directionLong');
  if (normalized === 'short') return t('trading.directionShort');
  if (normalized === 'hold' || normalized === 'neutral' || normalized === 'flat') return t('trading.directionHold');
  const raw = String(direction || '').trim();
  return raw || t('trading.directionHold');
}

function formatDirectionWithArrow(direction) {
  const normalized = normalizeDirection(direction);
  if (normalized === 'long') return `${t('trading.directionLong')} ↑`;
  if (normalized === 'short') return `${t('trading.directionShort')} ↓`;
  return formatDirection(direction);
}

function withAuthHeaders(headers = {}) {
  return {
    ...getAuthHeaders(),
    ...(headers || {})
  };
}

function clearRealtimeTimers() {
  if (dataRefreshInterval) {
    clearInterval(dataRefreshInterval);
    dataRefreshInterval = null;
  }
  if (equityInterval) {
    clearInterval(equityInterval);
    equityInterval = null;
  }
  if (performanceInterval) {
    clearInterval(performanceInterval);
    performanceInterval = null;
  }
}

async function refreshTokenOnce() {
  if (!tokenRefreshPromise) {
    tokenRefreshPromise = authStore.refreshAccessToken().finally(() => {
      tokenRefreshPromise = null;
    });
  }
  return tokenRefreshPromise;
}

async function handleAuthExpired() {
  if (authExpired.value) return;
  authExpired.value = true;
  clearRealtimeTimers();

  if (ws) {
    ws.close();
    ws = null;
  }

  if (!authRedirecting) {
    authRedirecting = true;
    try {
      await authStore.logout();
    } catch (_) {
      authStore.clearTokens?.();
      authStore.user = null;
    }
    router.push({
      name: 'Login',
      query: { redirect: '/trading', reason: 'expired' }
    }).catch(() => {
      // Ignore duplicated/aborted navigation failures.
    }).finally(() => {
      authRedirecting = false;
    });
  }
}

async function tradingFetch(path, options = {}) {
  if (authExpired.value) {
    throw new Error(t('trading.authRequired'));
  }

  const request = () => fetch(appendTokenToUrl(apiUrl(path)), {
    ...options,
    headers: withAuthHeaders(options.headers)
  });

  let response = await request();
  if (response.status !== 401) {
    return response;
  }

  const refreshed = await refreshTokenOnce();
  if (refreshed) {
    response = await request();
    if (response.status !== 401) {
      return response;
    }
  }

  await handleAuthExpired();
  throw new Error(t('trading.authRequired'));
}

async function parseTradingJson(response, label) {
  return readJsonResponse(response, label);
}

async function fetchStatus() {
  try {
    const response = await tradingFetch('/api/trading/status');
    const data = await parseTradingJson(response, 'Trading status');
    systemStatus.value = data;
  } catch (e) {
    console.error('Error fetching status:', e);
  }
}

async function fetchAccount() {
  try {
    const response = await tradingFetch('/api/trading/account');
    const data = await parseTradingJson(response, 'Trading account');
    if (!data.error) {
      account.value = {
        totalEquity: data.total_equity || 10000,
        availableBalance: data.available_balance || 10000,
        unrealizedPnl: data.unrealized_pnl || 0,
        initialBalance: data.initial_balance || data.total_equity || 10000
      };
    }
  } catch (e) {
    console.error('Error fetching account:', e);
  }
}

async function fetchPosition() {
  try {
    const response = await tradingFetch('/api/trading/position');
    const data = await parseTradingJson(response, 'Trading position');
    if (data.has_position !== undefined) {
      position.value = {
        hasPosition: data.has_position || false,
        symbol: data.symbol || 'BTC-USDT-SWAP',
        direction: data.direction || 'long',
        leverage: data.leverage || 1,
        size: data.size || 0,
        entryPrice: data.entry_price || 0,
        currentPrice: data.current_price || 0,
        takeProfitPrice: data.take_profit_price || 0,
        stopLossPrice: data.stop_loss_price || 0,
        unrealizedPnl: data.unrealized_pnl || 0,
        unrealizedPnlPercent: data.unrealized_pnl_percent || 0
      };
    }
  } catch (e) {
    console.error('Error fetching position:', e);
  }
}

async function fetchEquityHistory() {
  try {
    const response = await tradingFetch('/api/trading/equity?limit=100');
    const data = await parseTradingJson(response, 'Trading equity history');
    if (data.data) {
      equityHistory.value = data.data;
      updateEquityChart();
    }
  } catch (e) {
    console.error('Error fetching equity:', e);
  }
}

async function fetchDrawdown() {
  try {
    const endpoint = drawdownStartDate.value
      ? `/api/trading/drawdown?start_date=${drawdownStartDate.value}`
      : '/api/trading/drawdown';
    const response = await tradingFetch(endpoint);
    const data = await parseTradingJson(response, 'Trading drawdown');
    drawdown.value = {
      maxDrawdownPct: data.max_drawdown_pct || 0,
      maxDrawdownUsd: data.max_drawdown_usd || 0,
      currentDrawdownPct: data.current_drawdown_pct || 0,
      peakEquity: data.peak_equity || 0,
      troughEquity: data.trough_equity || 0,
      currentEquity: data.current_equity || 0,
      recoveryPct: data.recovery_pct || 100,
      tradesAnalyzed: data.trades_analyzed || 0
    };
  } catch (e) {
    console.error('Error fetching drawdown:', e);
  }
}

// Fetch performance metrics from backend API
async function fetchPerformance() {
  try {
    const endpoint = drawdownStartDate.value
      ? `/api/trading/performance?start_date=${drawdownStartDate.value}`
      : '/api/trading/performance';
    const response = await tradingFetch(endpoint);
    const data = await parseTradingJson(response, 'Trading performance');
    performanceData.value = {
      sharpeRatio: data.sharpe_ratio || 0,
      sortinoRatio: data.sortino_ratio || 0,
      alpha: data.alpha || 0,
      winRate: data.win_rate || 0,
      profitFactor: data.profit_factor || 0,
      totalReturnPct: data.total_return_pct || 0,
      annualizedReturnPct: data.annualized_return_pct || 0,
      volatilityPct: data.volatility_pct || 0,
      bestTrade: data.best_trade || 0,
      worstTrade: data.worst_trade || 0,
      avgHoldingHours: data.avg_holding_hours || 0,
      tradesAnalyzed: data.trades_analyzed || 0
    };
  } catch (e) {
    console.error('Error fetching performance metrics:', e);
  }
}

// Phase 3.1: Fetch MTF Analysis
async function fetchMtfAnalysis() {
  try {
    const response = await tradingFetch('/api/trading/mtf-analysis');
    const data = await parseTradingJson(response, 'Trading MTF analysis');
    if (data.overall_direction) {
      mtfAnalysis.value = data;
    }
  } catch (e) {
    console.error('Error fetching MTF analysis:', e);
  }
}

// Phase 3.2: Fetch Agent Weights
async function fetchAgentWeights() {
  try {
    const response = await tradingFetch('/api/trading/agent-weights');
    const data = await parseTradingJson(response, 'Trading agent weights');
    if (data.weights) {
      learnedWeights.value = data.weights;
    }
  } catch (e) {
    console.error('Error fetching agent weights:', e);
  }
}

// Phase 2.3: Fetch Degradation Status
async function fetchDegradation() {
  try {
    const response = await tradingFetch('/api/trading/degradation');
    const data = await parseTradingJson(response, 'Trading degradation');
    if (data.level) {
      systemHealth.value = data;
    }
  } catch (e) {
    console.error('Error fetching degradation:', e);
  }
}

// Fetch Pending Trades (HITL Semi-Auto)
async function fetchPendingTrades() {
  try {
    const response = await tradingFetch('/api/trading/pending');
    const data = await parseTradingJson(response, 'Trading pending trades');
    if (data.trades) {
      pendingTrades.value = data.trades;
    } else if (data.pending_trades) {
      // Fallback for alternative response format
      pendingTrades.value = data.pending_trades;
    }
  } catch (e) {
    console.error('Error fetching pending trades:', e);
  }
}

// Open Pending Trade Modal for confirmation
function openPendingTradeModal(trade) {
  pendingDecision.value = {
    trade_id: trade.id || trade.trade_id,
    direction: trade.direction,
    leverage: trade.leverage,
    confidence: trade.confidence,
    take_profit: trade.take_profit_price || trade.take_profit || 0,
    stop_loss: trade.stop_loss_price || trade.stop_loss || 0,
    current_price: trade.entry_price || 0,
    reasoning: trade.reasoning || ''
  };
  modifiedLeverage.value = trade.leverage;
  showDecisionModal.value = true;
}

// Fetch BTC benchmark data for alpha calculation
async function fetchBtcBenchmark() {
  if (!tradingStartDate.value) return;
  
  btcBenchmark.value.loading = true;
  try {
    // Get current BTC price from Binance API
    const currentResponse = await fetch('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT');
    const currentData = await currentResponse.json();
    const currentPrice = parseFloat(currentData.price);
    
    // Get historical BTC price at trading start date using Klines API (hourly for precision)
    const startTimestamp = tradingStartDate.value.getTime();
    const historyResponse = await fetch(
      `https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime=${startTimestamp}&limit=1`
    );
    const historyData = await historyResponse.json();
    
    // Kline format: [openTime, open, high, low, close, ...]
    // Use open price [1] for more accurate timestamp matching
    const startPrice = historyData.length > 0 ? parseFloat(historyData[0][1]) : 0;
    
    if (startPrice > 0 && currentPrice > 0) {
      const btcReturn = ((currentPrice - startPrice) / startPrice) * 100;
      btcBenchmark.value = {
        startPrice,
        currentPrice,
        returnPercent: btcReturn,
        loading: false
      };
      console.log(`[BTC Benchmark] Start: $${startPrice.toFixed(2)}, Current: $${currentPrice.toFixed(2)}, Return: ${btcReturn.toFixed(2)}%`);
    }
  } catch (e) {
    console.error('Error fetching BTC benchmark:', e);
    btcBenchmark.value.loading = false;
  }
}

async function fetchTradeHistory() {
  try {
    const response = await tradingFetch('/api/trading/history?limit=50');
    const data = await parseTradingJson(response, 'Trading history');

    const allTrades = [];

    // Add closed trades (actual trades with PnL)
    if (data.trades && data.trades.length > 0) {
      data.trades.forEach((t, idx) => {
        allTrades.push({
          id: `closed-${idx}`,
          timestamp: t.timestamp || t.closed_at,
          direction: t.signal?.direction || t.direction || 'unknown',
          leverage: t.signal?.leverage || t.leverage || 1,
          entryPrice: t.signal?.entry_price || t.entry_price || 0,
          exitPrice: t.closed_price || t.exit_price || 0,
          takeProfit: t.signal?.take_profit_price || t.take_profit_price || 0,
          stopLoss: t.signal?.stop_loss_price || t.stop_loss_price || 0,
          pnl: t.pnl || 0,
          status: 'closed'
        });
      });
    }

    // Add open trades from signals (executed but not yet closed)
    if (data.signals && data.signals.length > 0) {
      data.signals.forEach((s, idx) => {
        if (s.status === 'executed' && s.trade_result?.success) {
          allTrades.push({
            id: `open-${idx}`,
            timestamp: s.timestamp,
            direction: s.signal?.direction || 'unknown',
            leverage: s.signal?.leverage || s.trade_result?.leverage || 1,
            entryPrice: s.trade_result?.executed_price || s.signal?.entry_price || 0,
            takeProfit: s.trade_result?.take_profit || s.signal?.take_profit_price || 0,
            stopLoss: s.trade_result?.stop_loss || s.signal?.stop_loss_price || 0,
            exitPrice: null,  // Not yet closed
            pnl: null,  // PnL not realized yet
            status: 'open'
          });
        }
      });
    }

    // Sort by timestamp descending (most recent first)
    allTrades.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    tradeHistory.value = allTrades;
  } catch (e) {
    console.error('Error fetching history:', e);
  }
}

function parseDiscussionContent(content) {
  if (!content) return { hasJson: false, reasoning: '', conclusion: '', parsedJson: null };
  
  // Find the last JSON code block
  const jsonBlockRegex = /```json\s*([\s\S]*?)\s*```/g;
  let match;
  let lastMatch = null;
  
  while ((match = jsonBlockRegex.exec(content)) !== null) {
    lastMatch = match;
  }
  
  if (lastMatch) {
    const jsonStr = lastMatch[1];
    const fullBlock = lastMatch[0];
    const reasoning = content.replace(fullBlock, '').trim();
    
    let parsedJson = null;
    try {
      parsedJson = JSON.parse(jsonStr);
    } catch (e) {
      console.warn('Failed to parse discussion JSON:', e);
    }

    return {
      hasJson: true,
      parsedJson: parsedJson,
      reasoning: reasoning || t('trading.viewDetailedReasoning'),
      conclusion: fullBlock
    };
  }
  
  return { hasJson: false, reasoning: content, conclusion: '', parsedJson: null };
}

async function fetchDiscussionMessages() {
  try {
    const response = await tradingFetch('/api/trading/messages?limit=100');
    const data = await parseTradingJson(response, 'Trading messages');
    if (data.messages && data.messages.length > 0) {
      discussionMessages.value = data.messages.map(msg => ({
        agentName: msg.agent_name,
        content: msg.content,
        parsed: parseDiscussionContent(msg.content),
        timestamp: msg.timestamp
      }));
    }
  } catch (e) {
    console.error('Error fetching discussion messages:', e);
  }
}

async function startTrading() {
  try {
    await tradingFetch('/api/trading/start', { method: 'POST' });
    systemStatus.value.enabled = true;
  } catch (e) {
    console.error('Error starting trading:', e);
  }
}

async function stopTrading() {
  try {
    await tradingFetch('/api/trading/stop', { method: 'POST' });
    systemStatus.value.enabled = false;
  } catch (e) {
    console.error('Error stopping trading:', e);
  }
}

async function triggerAnalysis() {
  try {
    await tradingFetch('/api/trading/trigger', { method: 'POST' });
  } catch (e) {
    console.error('Error triggering analysis:', e);
  }
}

// Decision Confirmation Methods
function toggleModifyPanel() {
  showModifyPanel.value = !showModifyPanel.value;
  showDeferReasons.value = false;
}

function toggleDeferReasons() {
  showDeferReasons.value = !showDeferReasons.value;
  showModifyPanel.value = false;
}

async function handleConfirmDecision() {
  processingDecision.value = true;
  try {
    const tradeId = pendingDecision.value.trade_id;
    const isModified = showModifyPanel.value;
    const finalDirection = isModified ? modifiedDirection.value : pendingDecision.value.direction;
    const finalLeverage = isModified ? modifiedLeverage.value : pendingDecision.value.leverage;
    const finalAmountPercent = isModified ? modifiedAmountPercent.value : null;

    if (tradeId) {
      // SEMI_AUTO mode: Use the proper pending trade confirm API
      // Only send modified fields
      const body = { user_id: 'frontend' };
      if (isModified) {
        body.direction = finalDirection;
        body.leverage = Number(finalLeverage);
        body.amount_percent = Number(finalAmountPercent);
      }

      const response = await tradingFetch(`/api/trading/pending/${tradeId}/confirm`, {
        method: 'POST',
        headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body)
      });
      const result = await parseTradingJson(response, 'Confirm pending trade');

      if (!result.success) {
        discussionMessages.value.push({
          agentName: t('trading.system'),
          content: `❌ ${t('trading.tradeConfirmationFailed')}: ${result.message || result.detail || t('trading.unknownError')}`,
          timestamp: new Date().toISOString()
        });
        // Close modal even on failure — trade is no longer actionable
        showDecisionModal.value = false;
        resetDecisionState();
        return;
      }

      // Record to RLHF decision history (non-blocking)
      tradingFetch('/api/trading/decision', {
        method: 'POST',
        headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          decision_id: tradeId,
          action: isModified ? 'modified' : 'confirm',
          original_signal: { ...pendingDecision.value },
          modified_direction: finalDirection,
          modified_leverage: finalLeverage,
          modified_amount_percent: finalAmountPercent,
          timestamp: new Date().toISOString()
        })
      }).catch(() => {});

    } else {
      // HITL-only: should never execute directly without a pending trade id.
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `❌ ${t('trading.cannotConfirmMissingTradeId')}`,
        timestamp: new Date().toISOString()
      });
      showDecisionModal.value = false;
      resetDecisionState();
      return;
    }

    // Add to local history
    decisionHistory.value.unshift({
      decision_id: tradeId || `decision-${Date.now()}`,
      action: 'confirm',
      display: `${formatDirection(finalDirection)} ${finalLeverage}x${finalAmountPercent ? ` ${Math.round(finalAmountPercent * 100)}%` : ''} → ✓ ${t('trading.confirmExecution')}${isModified ? ` (${t('trading.modify')})` : ''}`
    });

    // Note: modal close and data refresh handled by 'trade_confirmed' WebSocket event
    // But close modal immediately for responsiveness
    showDecisionModal.value = false;
    resetDecisionState();

    // Refresh data
    fetchPosition();
    fetchAccount();
    fetchTradeHistory();

  } catch (e) {
    console.error('Error confirming decision:', e);
    const isExpired = String(e?.message || '').includes('(404)');
    discussionMessages.value.push({
      agentName: t('trading.system'),
      content: isExpired
        ? `⏰ ${t('trading.tradeExpiredWaitNext')}`
        : `❌ ${t('trading.errorConfirmingTrade')}: ${e.message || t('trading.networkError')}`,
      timestamp: new Date().toISOString()
    });
  } finally {
    processingDecision.value = false;
  }
}

async function handleDeferDecision() {
  processingDecision.value = true;
  try {
    const reason = selectedDeferReason.value === t('trading.other') ? customDeferReason.value : selectedDeferReason.value;
    const tradeId = pendingDecision.value.trade_id;

    if (tradeId) {
      // SEMI_AUTO mode: Use the proper pending trade reject API
      const response = await tradingFetch(`/api/trading/pending/${tradeId}/reject`, {
        method: 'POST',
        headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            user_id: 'frontend',
            reason: reason || t('trading.userDeferred')
          })
      });
      const result = await parseTradingJson(response, 'Reject pending trade');

      if (!result.success) {
        discussionMessages.value.push({
          agentName: t('trading.system'),
          content: `❌ ${t('trading.tradeRejectionFailed')}: ${result.message || result.detail || t('trading.unknownError')}`,
          timestamp: new Date().toISOString()
        });
        // Close modal even on failure — trade is no longer actionable
        showDecisionModal.value = false;
        resetDecisionState();
        return;
      }

      // Record to RLHF decision history (non-blocking)
      tradingFetch('/api/trading/decision', {
        method: 'POST',
        headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          decision_id: tradeId,
          action: 'defer',
          original_signal: { ...pendingDecision.value },
          defer_reason: reason,
          timestamp: new Date().toISOString()
        })
      }).catch(() => {});

    } else {
      // Fallback: just record the decision (legacy path)
      await tradingFetch('/api/trading/decision', {
        method: 'POST',
        headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          decision_id: `decision-${Date.now()}`,
          action: 'defer',
          original_signal: { ...pendingDecision.value },
          defer_reason: reason,
          timestamp: new Date().toISOString()
        })
      });
    }

    // Add to local history
    decisionHistory.value.unshift({
      decision_id: tradeId || `decision-${Date.now()}`,
      action: 'defer',
      display: `${formatDirection(pendingDecision.value.direction)} ${pendingDecision.value.leverage}x → ✕ ${t('trading.defer')}${reason ? ` (${reason})` : ''}`
    });

    // Note: modal close handled by 'trade_rejected' WebSocket event
    showDecisionModal.value = false;
    resetDecisionState();
    fetchPendingTrades();

  } catch (e) {
    console.error('Error deferring decision:', e);
    const isExpired = String(e?.message || '').includes('(404)');
    discussionMessages.value.push({
      agentName: t('trading.system'),
      content: isExpired
        ? `⏰ ${t('trading.tradeExpiredWaitNext')}`
        : `❌ ${t('trading.errorRejectingTrade')}: ${e.message || t('trading.networkError')}`,
      timestamp: new Date().toISOString()
    });
  } finally {
    processingDecision.value = false;
  }
}

function resetDecisionState() {
  showModifyPanel.value = false;
  showDeferReasons.value = false;
  selectedDeferReason.value = '';
  customDeferReason.value = '';
}

async function closePosition() {
  if (closingPosition.value) return;
  closingPosition.value = true;
  try {
    const response = await tradingFetch('/api/trading/close', { method: 'POST' });
    const data = await parseTradingJson(response, 'Close position');
    if (data.error) {
      console.error('Error closing position:', data.error);
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `${t('trading.closePositionFailed')}: ${data.error}`,
        timestamp: new Date().toISOString()
      });
    } else {
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `${t('trading.manualCloseSucceeded')}, ${t('trading.pnl')}: $${data.pnl?.toFixed(2) || '0.00'}`,
        timestamp: new Date().toISOString()
      });
      await fetchPosition();
      await fetchAccount();
      await fetchTradeHistory();
    }
  } catch (e) {
    console.error('Error closing position:', e);
  } finally {
    closingPosition.value = false;
  }
}

async function fetchAgentPerformance() {
  try {
    const response = await tradingFetch('/api/trading/agents/memory');
    const data = await parseTradingJson(response, 'Trading agent memory');
    if (data.team_summary) {
      agentPerformance.value = data;
    }
  } catch (e) {
    console.error('Error fetching agent performance:', e);
  }
}

async function openSettings() {
  showSettings.value = true;
  await fetchConfig();
}

async function fetchConfig() {
  loadingConfig.value = true;
  try {
    const response = await tradingFetch('/api/trading/config');
    const data = await parseTradingJson(response, 'Trading config');
    if (data) {
      settingsForm.value = {
        analysisInterval: data.analysis_interval_hours || 4,
        maxLeverage: data.max_leverage || 20,
        maxPositionPercent: data.max_position_percent || 0.3,
        useOkxTrading: !!data.use_okx_trading,
        okxConfigured: !!data.okx?.configured,
        okxApiKeyLast4: data.okx?.api_key_last4 || '',
        okxDemoMode: data.okx?.demo_mode ?? true,
        okxApiKey: '',
        okxSecretKey: '',
        okxPassphrase: ''
      };
    }
  } catch (e) {
    console.error('Error fetching config:', e);
  } finally {
    loadingConfig.value = false;
  }
}

async function saveSettings() {
  savingSettings.value = true;
  try {
    const okxSelected = !!settingsForm.value.useOkxTrading;
    const okxApiKey = (settingsForm.value.okxApiKey || '').trim();
    const okxSecretKey = (settingsForm.value.okxSecretKey || '').trim();
    const okxPassphrase = (settingsForm.value.okxPassphrase || '').trim();

    if (okxSelected && !settingsForm.value.okxConfigured && !(okxApiKey && okxSecretKey && okxPassphrase)) {
      alert(t('trading.okxSelectRequiresKeys'));
      return;
    }

    if (okxSelected && !settingsForm.value.okxDemoMode) {
      const ok = confirm(t('trading.okxSwitchLiveConfirm'));
      if (!ok) return;
    }

    const response = await tradingFetch('/api/trading/config', {
      method: 'PATCH',
      headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        analysis_interval_hours: parseInt(settingsForm.value.analysisInterval),
        max_leverage: parseInt(settingsForm.value.maxLeverage),
        max_position_percent: parseFloat(settingsForm.value.maxPositionPercent),
        use_okx_trading: okxSelected,
        okx_demo_mode: !!settingsForm.value.okxDemoMode,
        ...(okxSelected && okxApiKey && okxSecretKey && okxPassphrase ? {
          okx_api_key: okxApiKey,
          okx_secret_key: okxSecretKey,
          okx_passphrase: okxPassphrase
        } : {})
      })
    });
    const data = await parseTradingJson(response, 'Update trading config');
    if (data.status === 'updated') {
      showSettings.value = false;

      let message = t('trading.settingsUpdated');
      if (data.needs_reset) {
        message = t('trading.settingsUpdatedNeedsReset');
      }

      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: message,
        parsed: parseDiscussionContent(message),
        timestamp: new Date().toISOString()
      });
    }
  } catch (e) {
    console.error('Error saving settings:', e);
  } finally {
    savingSettings.value = false;
  }
}

async function clearOkxCredentials() {
  if (!confirm(t('trading.clearOkxConfirm'))) return;
  savingSettings.value = true;
  try {
    const response = await tradingFetch('/api/trading/config', {
      method: 'PATCH',
      headers: withAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        clear_okx_credentials: true,
        use_okx_trading: false
      })
    });
    const data = await parseTradingJson(response, 'Clear OKX credentials');
    if (data.status === 'updated') {
      await fetchConfig();
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: t('trading.okxCleared'),
        parsed: parseDiscussionContent(t('trading.okxCleared')),
        timestamp: new Date().toISOString()
      });
    }
  } catch (e) {
    console.error('Error clearing OKX credentials:', e);
  } finally {
    savingSettings.value = false;
  }
}

async function resetSystem() {
  if (!confirm(t('trading.resetConfirm'))) {
    return;
  }

  resettingSystem.value = true;
  try {
    const response = await tradingFetch('/api/trading/reset', {
      method: 'POST',
      headers: withAuthHeaders({ 'Content-Type': 'application/json' })
    });
    const data = await parseTradingJson(response, 'Reset trading system');

    if (data.status === 'reset_complete') {
      // Clear local state
      discussionMessages.value = [];
      tradeHistory.value = [];
      position.value = { hasPosition: false };
      systemStatus.value.enabled = false;

      // Update account if returned
      if (data.account) {
        account.value = {
          totalEquity: data.account.total_equity,
          availableBalance: data.account.available_balance,
          unrealizedPnl: data.account.unrealized_pnl,
          initialBalance: data.account.initial_balance || data.account.total_equity
        };
      }

      showSettings.value = false;

      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `${t('trading.systemResetSuccess')}: ${data.trader_type}`,
        timestamp: new Date().toISOString()
      });

      // Refresh status
      await fetchStatus();
    } else if (data.error) {
      alert(`${t('trading.resetFailed')}: ${data.error}`);
    }
  } catch (e) {
    console.error('Error resetting system:', e);
    alert(t('trading.resetFailedGeneric'));
  } finally {
    resettingSystem.value = false;
  }
}

let isComponentMounted = false;
let reconnectTimeout = null;

function connectWebSocket() {
  if (!isComponentMounted || authExpired.value) return;

  const sessionId = 'trading-' + Date.now();
  const socketUrl = appendTokenToUrl(buildWsUrl(`/api/trading/ws/${sessionId}`));

  ws = new WebSocket(socketUrl);

  ws.onopen = () => {
    console.log('Trading WebSocket connected');
    // Restore state after reconnection
    fetchStatus();
    fetchAccount();
    fetchPosition();
    fetchPendingTrades();
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleWebSocketMessage(msg);
  };

  ws.onclose = () => {
    console.log('Trading WebSocket disconnected');
    // Reconnect after delay only if component is still mounted
    if (isComponentMounted && !authExpired.value) {
      reconnectTimeout = setTimeout(connectWebSocket, 3000);
    }
  };

  ws.onerror = (e) => {
    console.error('Trading WebSocket error:', e);
  };
}

function handleWebSocketMessage(msg) {
  switch (msg.type) {
    case 'connected':
      systemStatus.value = msg.status;
      break;

    case 'system_started':
      systemStatus.value.enabled = true;
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: t('trading.systemStarted'),
        timestamp: new Date().toISOString()
      });
      break;

    case 'system_stopped':
      systemStatus.value.enabled = false;
      isAnalyzing.value = false;
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: t('trading.systemStopped'),
        timestamp: new Date().toISOString()
      });
      break;

    case 'analysis_started':
      isAnalyzing.value = true;
      discussionMessages.value = [];
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: t('trading.analysisStartedRound'),
        timestamp: new Date().toISOString()
      });
      break;

    case 'analysis_error':
      isAnalyzing.value = false;
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `${t('trading.analysisErrorLabel')}: ${msg.error || t('trading.unknownError')}`,
        timestamp: new Date().toISOString()
      });
      break;

    case 'agent_message':
      discussionMessages.value.push({
        agentName: msg.agent_name,
        content: msg.content,
        parsed: parseDiscussionContent(msg.content),
        timestamp: msg.timestamp
      });
      // Auto-scroll
      nextTick(() => {
        if (discussionContainer.value) {
          discussionContainer.value.scrollTop = discussionContainer.value.scrollHeight;
        }
      });
      break;

    case 'signal_generated':
      isAnalyzing.value = false;
      const signal = msg.signal || {};

      // Synthesize Leader Message content for Discussion Panel
      // We wrap the signal in valid JSON markdown so it renders as a Ticket
      const signalReasoning = signal.reasoning || msg.reasoning || t('trading.marketAnalysisComplete');

      // Construct the display payload
      const displayPayload = {
        direction: signal.direction || 'hold',
        leverage: signal.leverage || 1,
        attendance: 0, // Placeholder
        confidence: signal.confidence || 0,
        take_profit_percent: ((signal.take_profit_price && signal.entry_price) ? ((signal.take_profit_price/signal.entry_price - 1) * 100 * (signal.direction==='short'?-1:1)).toFixed(1) : 0),
        stop_loss_percent: ((signal.stop_loss_price && signal.entry_price) ? ((1 - signal.stop_loss_price/signal.entry_price) * 100 * (signal.direction==='short'?-1:1)).toFixed(1) : 0),
        reasoning: signalReasoning
      };

      const leaderContent = `${signalReasoning}\n\n\`\`\`json\n${JSON.stringify(displayPayload, null, 2)}\n\`\`\``;

      discussionMessages.value.push({
         agentName: t('trading.leader'),
         content: leaderContent,
         parsed: parseDiscussionContent(leaderContent),
         timestamp: new Date().toISOString()
      });

      // Auto-scroll
      nextTick(() => {
        if (discussionContainer.value) {
          discussionContainer.value.scrollTop = discussionContainer.value.scrollHeight;
        }
      });

      // Check if this is a HOLD signal (no action needed)
      if (msg.signal?.direction === 'hold' || !msg.signal?.direction) {
        break;
      }

      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `🔔 ${t('trading.signalGenerated')}: ${formatDirection(signal.direction)} ${signal.leverage}x - ${t('trading.awaitingConfirmation')}`,
        timestamp: new Date().toISOString()
      });
      break;

    case 'pending_trade_created': {
      // SEMI_AUTO mode: Show confirmation modal with real trade_id from backend
      const pendingSignal = msg.signal || {};
      const pendingReasoning = pendingSignal.reasoning || '';

      pendingDecision.value = {
        trade_id: msg.trade_id,
        direction: pendingSignal.direction || 'long',
        leverage: pendingSignal.leverage || 5,
        confidence: pendingSignal.confidence || 70,
        take_profit: pendingSignal.take_profit_price || 0,
        stop_loss: pendingSignal.stop_loss_price || 0,
        current_price: pendingSignal.entry_price || 0,
        amount_percent: pendingSignal.amount_percent || 0.5,
        reasoning: pendingReasoning
      };

      modifiedLeverage.value = pendingDecision.value.leverage;
      modifiedDirection.value = pendingDecision.value.direction;
      modifiedAmountPercent.value = pendingDecision.value.amount_percent;
      showDecisionModal.value = true;

      // Refresh pending trades list
      fetchPendingTrades();

      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `🔔 ${msg.message || t('trading.semiAutoConfirmReject')}`,
        timestamp: new Date().toISOString()
      });

      // Auto-scroll
      nextTick(() => {
        if (discussionContainer.value) {
          discussionContainer.value.scrollTop = discussionContainer.value.scrollHeight;
        }
      });
      break;
    }

    case 'trade_confirmed':
      // Trade was confirmed and executed successfully
      showDecisionModal.value = false;
      resetDecisionState();
      fetchPosition();
      fetchAccount();
      fetchTradeHistory();
      fetchPendingTrades();
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `✅ ${t('trading.tradeConfirmedExecuted')}: ${formatDirection(msg.signal?.direction)} ${msg.signal?.leverage || ''}x (${t('trading.confirmedBy')}: ${msg.confirmed_by || t('trading.user')})`,
        timestamp: new Date().toISOString()
      });
      break;

    case 'trade_confirm_failed':
      // Trade confirmation succeeded but execution failed
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `❌ ${t('trading.executionFailedAfterConfirm')}: ${msg.error || t('trading.unknownError')}`,
        timestamp: new Date().toISOString()
      });
      break;

    case 'trade_rejected':
      // Trade was rejected by user
      showDecisionModal.value = false;
      resetDecisionState();
      fetchPendingTrades();
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `✕ ${t('trading.tradeRejected')}${msg.reason ? ': ' + msg.reason : ''} (${t('trading.actionBy')}: ${msg.rejected_by || t('trading.user')})`,
        timestamp: new Date().toISOString()
      });
      break;

    case 'trade_executed':
      // Trade has been executed, refresh all trading data immediately
      fetchPosition();
      fetchAccount();
      fetchTradeHistory();
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: msg.success
          ? `${t('trading.tradeExecutedSuccessfully')}: ${formatDirection(msg.signal?.direction)} ${msg.signal?.leverage || 1}x`
          : `${t('trading.tradeExecutionFailed')}: ${msg.trade_result?.error || t('trading.unknownError')}`,
        timestamp: new Date().toISOString()
      });
      break;

    case 'pnl_update':
      if (position.value.hasPosition) {
        position.value.unrealizedPnl = msg.pnl;
        position.value.unrealizedPnlPercent = msg.pnl_percent;
      }
      account.value.unrealizedPnl = msg.pnl;
      break;

    case 'position_closed':
      fetchAccount();
      fetchPosition();
      fetchTradeHistory();
      discussionMessages.value.push({
        agentName: t('trading.system'),
        content: `${t('trading.positionClosed')}, ${t('trading.pnl')}: $${msg.pnl?.toFixed(2) || '0.00'}`,
        timestamp: new Date().toISOString()
      });
      break;

    case 'account_update':
      if (msg.account) {
        account.value = {
          totalEquity: msg.account.total_equity || msg.account.equity || 10000,
          availableBalance: msg.account.available_balance || msg.account.balance || 10000,
          unrealizedPnl: msg.account.unrealized_pnl || 0
        };
      }
      break;

    case 'scheduler_state':
      if (msg.new_state === 'analyzing') {
        isAnalyzing.value = true;
      } else if (msg.new_state === 'running' || msg.new_state === 'idle') {
        isAnalyzing.value = false;
      }
      break;

    case 'system_reset':
      // Handle system reset - refresh all data
      discussionMessages.value = [];
      fetchStatus();
      fetchAccount();
      fetchPosition();
      break;

    default:
      // Silently ignore unknown message types in production
      if (import.meta.env.DEV) {
        console.log('Unknown message type:', msg.type, msg);
      }
  }
}

function updateCountdown() {
  if (!systemStatus.value.scheduler?.next_run) {
    countdown.value = '--:--:--';
    return;
  }

  // Backend returns UTC time without timezone suffix, so we need to append 'Z'
  let nextRunStr = systemStatus.value.scheduler.next_run;
  if (!nextRunStr.endsWith('Z') && !nextRunStr.includes('+')) {
    nextRunStr += 'Z';
  }
  const nextRun = new Date(nextRunStr);
  const now = new Date();
  const diff = nextRun - now;

  if (diff <= 0) {
    countdown.value = '00:00:00';
    return;
  }

  const hours = Math.floor(diff / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);

  countdown.value = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

function initEquityChart() {
  if (!equityChartCanvas.value) return;

  const ctx = equityChartCanvas.value.getContext('2d');

  equityChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [{
        label: 'Equity',
        data: [],
        borderColor: 'rgb(56, 189, 248)',
        backgroundColor: 'rgba(56, 189, 248, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          display: true,
          grid: { color: 'rgba(255,255,255,0.1)' },
          ticks: { color: 'rgba(255,255,255,0.5)', maxTicksLimit: 8 }
        },
        y: {
          display: true,
          grid: { color: 'rgba(255,255,255,0.1)' },
          ticks: {
            color: 'rgba(255,255,255,0.5)',
            callback: (v) => '$' + v.toLocaleString()
          }
        }
      }
    }
  });
}

function updateEquityChart() {
  // Guard against chart not initialized or component unmounted
  if (!equityChart || !equityHistory.value.length || !isComponentMounted) return;

  try {
    const labels = equityHistory.value.map(d =>
      new Date(d.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    );
    const data = equityHistory.value.map(d => d.equity);

    equityChart.data.labels = labels;
    equityChart.data.datasets[0].data = data;
    equityChart.update('none');
  } catch (e) {
    console.error('Error updating equity chart:', e);
  }
}

// Lifecycle
let equityInterval = null;
let performanceInterval = null;
let dataRefreshInterval = null;

// Consolidated data refresh function
async function refreshAllData() {
  if (authExpired.value) return;
  await Promise.all([
    fetchStatus(),
    fetchAccount(),
    fetchPosition(),
    fetchTradeHistory(),
    fetchPerformance(),
    fetchMtfAnalysis(),
    fetchAgentWeights(),
    fetchDiscussionMessages(),
    fetchDegradation(),
    fetchPendingTrades(),
  ]);
}


onMounted(async () => {
  isComponentMounted = true;

  await Promise.all([
    fetchStatus(),
    fetchAccount(),
    fetchPosition(),
    fetchEquityHistory(),
    fetchTradeHistory(),
    fetchAgentPerformance(),
    fetchDiscussionMessages(),  // Restore discussion messages on page load
    fetchDrawdown(),  // Fetch drawdown data
    fetchPerformance(),  // Fetch performance metrics from backend
    fetchMtfAnalysis(),  // Phase 3.1: MTF Analysis
    fetchAgentWeights(),  // Phase 3.2: Agent Weights
    fetchDegradation(),  // Phase 2.3: Degradation Status
    fetchPendingTrades(),
  ]);


  // Fetch BTC benchmark after trade history is loaded (needs tradingStartDate)
  await fetchBtcBenchmark();

  initEquityChart();
  connectWebSocket();

  // Update countdown every second
  countdownInterval = setInterval(updateCountdown, 1000);

  // Refresh core data every 5 seconds for real-time updates
  dataRefreshInterval = setInterval(refreshAllData, 5000);

  // Refresh equity chart every 30 seconds
  equityInterval = setInterval(fetchEquityHistory, 30000);

  // Refresh agent performance every 2 minutes
  performanceInterval = setInterval(fetchAgentPerformance, 120000);
});

onUnmounted(() => {
  isComponentMounted = false;

  // Clear reconnection timeout
  if (reconnectTimeout) {
    clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }

  // Close WebSocket
  if (ws) {
    ws.close();
    ws = null;
  }

  // Clear all intervals
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
  if (dataRefreshInterval) {
    clearInterval(dataRefreshInterval);
    dataRefreshInterval = null;
  }
  if (equityInterval) {
    clearInterval(equityInterval);
    equityInterval = null;
  }
  if (performanceInterval) {
    clearInterval(performanceInterval);
    performanceInterval = null;
  }

  // Destroy chart
  if (equityChart) {
    equityChart.destroy();
    equityChart = null;
  }
});
</script>

<style scoped>
:deep(.overflow-y-auto),
:deep(.overflow-auto) {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

:deep(.overflow-y-auto::-webkit-scrollbar),
:deep(.overflow-auto::-webkit-scrollbar) {
  display: none;
}

/* Force code blocks to wrap text to prevent overflow */
:deep(.prose pre) {
  white-space: pre-wrap !important;
  word-wrap: break-word !important;
  overflow-x: hidden !important;
  max-width: 100%;
}
:deep(.prose code) {
  white-space: pre-wrap !important;
  word-break: break-all !important;
}
</style>
