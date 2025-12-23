<template>
  <div class="max-w-7xl mx-auto p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">{{ t('trading.title') || 'Auto Trading System' }}</h1>
        <p class="text-text-secondary mt-1">
          {{ t('trading.subtitle') || 'AI-powered automated cryptocurrency trading' }}
        </p>
      </div>

      <!-- System Controls -->
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2">
          <span class="text-sm text-text-secondary">{{ t('trading.status') || 'Status' }}:</span>
          <span
            :class="[
              'px-3 py-1 rounded-full text-sm font-medium',
              systemStatus.enabled
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-gray-500/20 text-gray-400'
            ]"
          >
            {{ systemStatus.enabled ? (t('trading.running') || 'Running') : (t('trading.stopped') || 'Stopped') }}
          </span>
        </div>

        <button
          v-if="!systemStatus.enabled"
          @click="startTrading"
          class="px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-medium hover:shadow-lg transition-all"
        >
          <span class="material-symbols-outlined mr-1 align-middle text-lg">play_arrow</span>
          {{ t('trading.start') || 'Start Trading' }}
        </button>
        <button
          v-else
          @click="stopTrading"
          class="px-4 py-2 rounded-lg bg-gradient-to-r from-red-500 to-orange-500 text-white font-medium hover:shadow-lg transition-all"
        >
          <span class="material-symbols-outlined mr-1 align-middle text-lg">stop</span>
          {{ t('trading.stop') || 'Stop Trading' }}
        </button>

        <button
          @click="openSettings"
          class="px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-all"
          :title="t('trading.settings') || 'Settings'"
        >
          <span class="material-symbols-outlined align-middle text-lg">settings</span>
        </button>
      </div>
    </div>

    <!-- Main Content Grid -->
    <div class="grid grid-cols-12 gap-6">
      <!-- Left Column: Account & Position -->
      <div class="col-span-12 lg:col-span-4 space-y-6">
        <!-- Account Overview Card -->
        <div class="glass-panel rounded-xl p-6">
          <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
            <span class="material-symbols-outlined mr-2 text-primary">account_balance_wallet</span>
            {{ t('trading.account') || '账户概览' }}
          </h3>

          <div class="space-y-3">
            <!-- Trading Start Date -->
            <div class="flex justify-between items-center">
              <span class="text-text-secondary text-sm">交易起始日期</span>
              <span class="text-white">{{ tradingStartDateFormatted }}</span>
            </div>

            <!-- Initial Capital -->
            <div class="flex justify-between items-center">
              <span class="text-text-secondary text-sm">起始金额</span>
              <span class="text-white font-medium">$3,000.00</span>
            </div>

            <!-- Current Equity -->
            <div class="flex justify-between items-center pt-2 border-t border-white/10">
              <span class="text-text-secondary">当前权益</span>
              <span class="text-2xl font-bold text-white">${{ formatNumber(account.totalEquity) }}</span>
            </div>

            <!-- Total Profit -->
            <div class="flex justify-between items-center">
              <span class="text-text-secondary">总盈利</span>
              <span :class="totalProfit >= 0 ? 'text-emerald-400' : 'text-red-400'" class="font-semibold">
                {{ totalProfit >= 0 ? '+' : '' }}${{ formatNumber(totalProfit) }}
                <span class="text-sm">({{ totalProfitPercent >= 0 ? '+' : '' }}{{ totalProfitPercent.toFixed(2) }}%)</span>
              </span>
            </div>

            <!-- Max Drawdown -->
            <div class="flex justify-between items-center">
              <span class="text-text-secondary">最大回撤</span>
              <span class="text-red-400 font-medium">
                -{{ drawdown.maxDrawdownPct?.toFixed(2) || 0 }}%
              </span>
            </div>

            <!-- Unrealized PnL (if has position) -->
            <template v-if="position.hasPosition">
              <div class="flex justify-between items-center pt-2 border-t border-white/10">
                <span class="text-text-secondary text-sm">未实现盈亏</span>
                <span :class="account.unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-red-400'">
                  {{ account.unrealizedPnl >= 0 ? '+' : '' }}${{ formatNumber(account.unrealizedPnl) }}
                </span>
              </div>
            </template>
          </div>
        </div>

        <!-- Current Position Card -->
        <div class="glass-panel rounded-xl p-6">
          <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
            <span class="material-symbols-outlined mr-2 text-accent-cyan">trending_up</span>
            {{ t('trading.position') || 'Current Position' }}
          </h3>

          <template v-if="position.hasPosition">
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span
                  :class="[
                    'px-3 py-1 rounded-lg font-medium',
                    position.direction === 'long'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-red-500/20 text-red-400'
                  ]"
                >
                  {{ position.direction === 'long' ? 'LONG' : 'SHORT' }} {{ position.leverage }}x
                </span>
                <span class="text-white font-medium">{{ position.symbol }}</span>
              </div>

              <div class="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span class="text-text-secondary block">{{ t('trading.entry') || 'Entry' }}</span>
                  <span class="text-white">${{ formatNumber(position.entryPrice) }}</span>
                </div>
                <div>
                  <span class="text-text-secondary block">{{ t('trading.current') || 'Current' }}</span>
                  <span class="text-white">${{ formatNumber(position.currentPrice) }}</span>
                </div>
                <div>
                  <span class="text-text-secondary block">{{ t('trading.takeProfit') || 'Take Profit' }}</span>
                  <span class="text-emerald-400">{{ position.takeProfitPrice > 0 ? '$' + formatNumber(position.takeProfitPrice) : (t('trading.notSet') || '未设置') }}</span>
                </div>
                <div>
                  <span class="text-text-secondary block">{{ t('trading.stopLoss') || 'Stop Loss' }}</span>
                  <span class="text-red-400">{{ position.stopLossPrice > 0 ? '$' + formatNumber(position.stopLossPrice) : (t('trading.notSet') || '未设置') }}</span>
                </div>
              </div>

              <div class="pt-3 border-t border-white/10">
                <div class="flex justify-between items-center">
                  <span class="text-text-secondary">{{ t('trading.pnl') || 'P&L' }}</span>
                  <span
                    :class="[
                      'text-xl font-bold',
                      position.unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-red-400'
                    ]"
                  >
                    {{ position.unrealizedPnl >= 0 ? '+' : '' }}${{ formatNumber(position.unrealizedPnl) }}
                    <span class="text-sm">({{ calculatePnlPercent(position.unrealizedPnl).toFixed(2) }}%)</span>
                  </span>
                </div>
              </div>

              <!-- Manual Close Position Button -->
              <div class="pt-3 border-t border-white/10">
                <button
                  @click="closePosition"
                  :disabled="closingPosition"
                  class="w-full px-4 py-2 rounded-lg bg-gradient-to-r from-orange-500 to-red-500 text-white font-medium hover:shadow-lg transition-all disabled:opacity-50"
                >
                  <span class="material-symbols-outlined mr-1 align-middle text-lg">close</span>
                  {{ closingPosition ? (t('trading.closing') || 'Closing...') : (t('trading.closePosition') || 'Close Position') }}
                </button>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="text-center py-8 text-text-secondary">
              <span class="material-symbols-outlined text-4xl mb-2 opacity-50">do_not_disturb</span>
              <p>{{ t('trading.noPosition') || 'No open position' }}</p>
            </div>
          </template>
        </div>

        <!-- Next Analysis Countdown -->
        <div class="glass-panel rounded-xl p-6">
          <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
            <span class="material-symbols-outlined mr-2 text-accent-violet">schedule</span>
            {{ t('trading.nextAnalysis') || 'Next Analysis' }}
          </h3>

          <div class="text-center">
            <div class="text-3xl font-bold text-white font-mono">
              {{ countdown }}
            </div>
            <p class="text-text-secondary text-sm mt-2">
              {{ intervalText }}
            </p>

            <button
              @click="triggerAnalysis"
              class="mt-4 px-4 py-2 rounded-lg border border-primary text-primary hover:bg-primary/10 transition-colors text-sm"
            >
              <span class="material-symbols-outlined mr-1 align-middle text-lg">bolt</span>
              {{ t('trading.triggerNow') || 'Trigger Now' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Right Column: Charts & Agents -->
      <div class="col-span-12 lg:col-span-8 flex flex-col gap-6">
        <!-- Equity Curve Chart -->
        <div class="glass-panel rounded-xl p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-white flex items-center">
              <span class="material-symbols-outlined mr-2 text-primary">show_chart</span>
              {{ t('trading.equityCurve') || 'Equity Curve' }}
            </h3>
          </div>

          <div class="h-64">
            <canvas ref="equityChartCanvas"></canvas>
          </div>
        </div>

        <!-- Agent Discussion (Live) - grows to fill remaining space -->
        <div class="glass-panel rounded-xl p-6 flex flex-col flex-1">
          <h3 class="text-lg font-semibold text-white mb-4 flex items-center">
            <span class="material-symbols-outlined mr-2 text-accent-violet">forum</span>
            {{ t('trading.discussion') || 'Live Discussion' }}
            <span v-if="isAnalyzing" class="ml-2 flex items-center text-primary text-sm">
              <span class="animate-pulse mr-1">●</span> Live
            </span>
          </h3>

          <div class="flex-1 overflow-y-auto space-y-4 pr-2 min-h-[200px]" ref="discussionContainer">
            <div
              v-for="(msg, idx) in discussionMessages"
              :key="idx"
              class="p-3 rounded-lg bg-white/5"
            >
              <div class="flex items-center gap-2 mb-1">
                <span class="text-primary font-medium text-sm">{{ msg.agentName }}</span>
                <span class="text-text-secondary text-xs">{{ formatTime(msg.timestamp) }}</span>
              </div>
              <div class="text-text-secondary text-sm prose prose-sm prose-invert max-w-none" v-html="renderMarkdown(msg.content)"></div>
            </div>

            <div v-if="discussionMessages.length === 0" class="flex flex-col items-center justify-center h-full py-8 text-text-secondary">
              <span class="material-symbols-outlined text-4xl mb-2 opacity-50">chat_bubble</span>
              <p>{{ t('trading.noMessages') || 'Waiting for analysis...' }}</p>
            </div>
          </div>
        </div>

        <!-- Agent Team Panel (Compact) -->
        <div class="glass-panel rounded-xl p-4">
          <h3 class="text-base font-semibold text-white mb-3 flex items-center">
            <span class="material-symbols-outlined mr-2 text-accent-cyan text-lg">groups</span>
            {{ t('trading.agentTeam') || 'Trading Expert Team' }}
          </h3>

          <div class="flex flex-wrap gap-2">
            <div
              v-for="agent in agents"
              :key="agent.id"
              class="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10 hover:border-primary/50 transition-colors"
            >
              <div class="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                <span class="material-symbols-outlined text-primary text-sm">{{ agent.icon }}</span>
              </div>
              <div class="min-w-0">
                <div class="text-white font-medium text-xs truncate">{{ agent.name }}</div>
                <div class="text-text-secondary text-xs">{{ t('trading.winRate') || 'Win' }}: {{ (agent.winRate * 100).toFixed(1) }}%</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Trade History -->
    <div class="glass-panel rounded-xl p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-white flex items-center">
          <span class="material-symbols-outlined mr-2 text-primary">history</span>
          {{ t('trading.history') || 'Trade History' }}
        </h3>
        <button
          @click="fetchTradeHistory"
          class="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm transition-all"
        >
          <span class="material-symbols-outlined align-middle text-base mr-1">refresh</span>
          {{ t('common.refresh') || 'Refresh' }}
        </button>
      </div>

      <div class="max-h-80 overflow-y-auto overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-text-secondary border-b border-white/10">
              <th class="text-left py-3 px-4">{{ t('trading.time') || 'Time' }}</th>
              <th class="text-left py-3 px-4">{{ t('trading.status') || 'Status' }}</th>
              <th class="text-left py-3 px-4">{{ t('trading.direction') || 'Direction' }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.leverage') || 'Leverage' }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.entry') || 'Entry' }}</th>
              <th class="text-right py-3 px-4 text-emerald-400">TP</th>
              <th class="text-right py-3 px-4 text-red-400">SL</th>
              <th class="text-right py-3 px-4">{{ t('trading.exit') || 'Exit' }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.pnl') || 'P&L' }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="trade in tradeHistory"
              :key="trade.id"
              class="border-b border-white/5 hover:bg-white/5"
            >
              <td class="py-3 px-4 text-white">{{ formatDate(trade.timestamp) }}</td>
              <td class="py-3 px-4">
                <span
                  :class="[
                    'px-2 py-1 rounded text-xs font-medium',
                    trade.status === 'open'
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'bg-gray-500/20 text-gray-400'
                  ]"
                >
                  {{ trade.status === 'open' ? 'OPEN' : 'CLOSED' }}
                </span>
              </td>
              <td class="py-3 px-4">
                <span
                  :class="[
                    'px-2 py-1 rounded text-xs font-medium',
                    trade.direction === 'long'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-red-500/20 text-red-400'
                  ]"
                >
                  {{ (trade.direction || 'unknown').toUpperCase() }}
                </span>
              </td>
              <td class="py-3 px-4 text-right text-white">{{ trade.leverage }}x</td>
              <td class="py-3 px-4 text-right text-white">${{ formatNumber(trade.entryPrice) }}</td>
              <td class="py-3 px-4 text-right text-emerald-400">
                <template v-if="trade.takeProfit">${{ formatNumber(trade.takeProfit) }}</template>
                <template v-else><span class="text-text-secondary">-</span></template>
              </td>
              <td class="py-3 px-4 text-right text-red-400">
                <template v-if="trade.stopLoss">${{ formatNumber(trade.stopLoss) }}</template>
                <template v-else><span class="text-text-secondary">-</span></template>
              </td>
              <td class="py-3 px-4 text-right text-white">
                <template v-if="trade.exitPrice !== null">
                  ${{ formatNumber(trade.exitPrice) }}
                </template>
                <template v-else>
                  <span class="text-text-secondary">-</span>
                </template>
              </td>
              <td class="py-3 px-4 text-right">
                <template v-if="trade.pnl !== null">
                  <span :class="trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'">
                    {{ trade.pnl >= 0 ? '+' : '' }}${{ formatNumber(trade.pnl) }}
                  </span>
                </template>
                <template v-else>
                  <span class="text-blue-400">{{ t('trading.holding') || 'Holding' }}</span>
                </template>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="tradeHistory.length === 0" class="text-center py-8 text-text-secondary">
          {{ t('trading.noTrades') || 'No trades yet' }}
        </div>
      </div>
    </div>

    <!-- Agent Performance Panel -->
    <div class="glass-panel rounded-xl p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-lg font-semibold text-white flex items-center">
          <span class="material-symbols-outlined mr-2 text-accent-cyan">leaderboard</span>
          {{ t('trading.agentPerformance') || 'Agent Performance' }}
        </h3>
        <button
          @click="fetchAgentPerformance"
          class="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm transition-all"
        >
          <span class="material-symbols-outlined align-middle text-base mr-1">refresh</span>
          {{ t('common.refresh') || 'Refresh' }}
        </button>
      </div>

      <div v-if="agentPerformance.team_summary" class="mb-6 p-4 rounded-lg bg-white/5 border border-white/10">
        <h4 class="text-sm font-medium text-white mb-3">{{ t('trading.teamSummary') || 'Team Summary' }}</h4>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span class="text-text-secondary block">{{ t('trading.totalTrades') || 'Total Trades' }}</span>
            <span class="text-white font-medium">{{ agentPerformance.team_summary.total_trades || 0 }}</span>
          </div>
          <div>
            <span class="text-text-secondary block">{{ t('trading.winRate') || 'Win Rate' }}</span>
            <span :class="(agentPerformance.team_summary.win_rate || 0) >= 0.5 ? 'text-emerald-400' : 'text-red-400'" class="font-medium">
              {{ ((agentPerformance.team_summary.win_rate || 0) * 100).toFixed(1) }}%
            </span>
          </div>
          <div>
            <span class="text-text-secondary block">{{ t('trading.totalPnlLabel') || 'Total PnL' }}</span>
            <span :class="(agentPerformance.team_summary.total_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'" class="font-medium">
              {{ (agentPerformance.team_summary.total_pnl || 0) >= 0 ? '+' : '' }}${{ formatNumber(agentPerformance.team_summary.total_pnl || 0) }}
            </span>
          </div>
          <div>
            <span class="text-text-secondary block">{{ t('trading.avgPnl') || 'Avg PnL' }}</span>
            <span :class="(agentPerformance.team_summary.avg_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'" class="font-medium">
              {{ (agentPerformance.team_summary.avg_pnl || 0) >= 0 ? '+' : '' }}${{ formatNumber(agentPerformance.team_summary.avg_pnl || 0) }}
            </span>
          </div>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-text-secondary border-b border-white/10">
              <th class="text-left py-3 px-4">{{ t('trading.agent') || 'Agent' }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.totalTrades') || 'Trades' }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.wins') || 'Wins' }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.winRate') || 'Win Rate' }}</th>
              <th class="text-right py-3 px-4">{{ t('trading.totalPnlLabel') || 'Total PnL' }}</th>
              <th class="text-left py-3 px-4">{{ t('trading.latestLesson') || 'Latest Lesson' }}</th>
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
          {{ t('trading.noAgentData') || 'No agent performance data yet' }}
        </div>
      </div>
    </div>

    <!-- Settings Modal -->
    <div
      v-if="showSettings"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showSettings = false"
    >
      <div class="glass-panel rounded-xl p-6 w-full max-w-md mx-4">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-semibold text-white flex items-center">
            <span class="material-symbols-outlined mr-2 text-primary">settings</span>
            {{ t('trading.settings') || 'Trading Settings' }}
          </h3>
          <button @click="showSettings = false" class="text-text-secondary hover:text-white">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <!-- Loading indicator -->
        <div v-if="loadingConfig" class="text-center py-8">
          <span class="material-symbols-outlined animate-spin text-primary text-3xl">refresh</span>
          <p class="text-text-secondary mt-2">{{ t('trading.loadingConfig') || 'Loading configuration...' }}</p>
        </div>

        <div v-else class="space-y-4">
          <!-- Trading Mode Toggle -->
          <div class="p-4 rounded-lg bg-white/5 border border-white/10">
            <div class="flex items-center justify-between">
              <div>
                <h4 class="text-sm font-medium text-white">{{ t('trading.tradingMode') || 'Trading Mode' }}</h4>
                <p class="text-xs text-text-secondary mt-1">
                  {{ settingsForm.useOkxTrading ? (t('trading.okxDemoTrading') || 'OKX Demo Trading') : (t('trading.localPaperTrading') || 'Local Paper Trading') }}
                </p>
              </div>
              <label class="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  v-model="settingsForm.useOkxTrading"
                  class="sr-only peer"
                >
                <div class="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                <span class="ml-2 text-sm text-white">{{ t('trading.okxDemo') || 'OKX Demo' }}</span>
              </label>
            </div>
            <p v-if="settingsForm.useOkxTrading" class="text-xs text-amber-400 mt-2">
              <span class="material-symbols-outlined align-middle text-sm">warning</span>
              {{ t('trading.okxApiWarning') || 'Requires OKX API credentials configured in the backend' }}
            </p>
          </div>

          <!-- Analysis Interval -->
          <div>
            <label class="block text-sm text-text-secondary mb-2">
              {{ t('trading.analysisInterval') || 'Analysis Interval (hours)' }}
            </label>
            <select
              v-model="settingsForm.analysisInterval"
              class="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:border-primary"
            >
              <option value="1">{{ t('trading.hour1') || '1 hour' }}</option>
              <option value="2">{{ t('trading.hour2') || '2 hours' }}</option>
              <option value="4">{{ t('trading.hour4') || '4 hours' }}</option>
              <option value="6">{{ t('trading.hour6') || '6 hours' }}</option>
              <option value="12">{{ t('trading.hour12') || '12 hours' }}</option>
              <option value="24">{{ t('trading.hour24') || '24 hours' }}</option>
            </select>
          </div>

          <!-- Max Leverage -->
          <div>
            <label class="block text-sm text-text-secondary mb-2">
              {{ t('trading.maxLeverage') || 'Max Leverage' }}
            </label>
            <select
              v-model="settingsForm.maxLeverage"
              class="w-full px-4 py-2 rounded-lg bg-white/10 border border-white/20 text-white focus:outline-none focus:border-primary"
            >
              <option v-for="lev in 20" :key="lev" :value="lev">
                {{ lev }}x{{ lev === 1 ? ' ' + (t('trading.noLeverage') || '(No Leverage)') : '' }}
              </option>
            </select>
          </div>

          <!-- Max Position Percent -->
          <div>
            <label class="block text-sm text-text-secondary mb-2">
              {{ t('trading.maxPositionPercent') || 'Max Position (% of Balance)' }}
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
              <h4 class="text-sm font-medium text-white">{{ t('trading.resetSystem') || 'Reset System' }}</h4>
              <p class="text-xs text-text-secondary mt-1">
                {{ t('trading.resetDescription') || 'Stop trading, close positions, clear history and memories' }}
              </p>
            </div>
            <button
              @click="resetSystem"
              :disabled="resettingSystem"
              class="px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all disabled:opacity-50 flex items-center gap-2"
            >
              <span v-if="resettingSystem" class="material-symbols-outlined animate-spin text-sm">refresh</span>
              <span class="material-symbols-outlined text-sm" v-else>restart_alt</span>
              {{ resettingSystem ? (t('trading.resetting') || 'Resetting...') : (t('trading.reset') || 'Reset') }}
            </button>
          </div>
        </div>

        <div class="flex gap-3 mt-6">
          <button
            @click="showSettings = false"
            class="flex-1 px-4 py-2 rounded-lg bg-white/10 text-white hover:bg-white/20 transition-all"
          >
            {{ t('common.cancel') || 'Cancel' }}
          </button>
          <button
            @click="saveSettings"
            :disabled="savingSettings"
            class="flex-1 px-4 py-2 rounded-lg bg-gradient-to-r from-primary to-accent-cyan text-white font-medium hover:shadow-lg transition-all disabled:opacity-50"
          >
            {{ savingSettings ? (t('trading.saving') || 'Saving...') : (t('common.save') || 'Save') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useLanguage } from '@/composables/useLanguage.js';
import Chart from 'chart.js/auto';
import { marked } from 'marked';

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true
});

const { t } = useLanguage();

// Chart
const equityChartCanvas = ref(null);
let equityChart = null;

// Refs
const discussionContainer = ref(null);

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

const agents = ref([
  { id: 'technical-analyst', name: '技术分析师', role: '技术面', icon: 'candlestick_chart', winRate: 0.65 },
  { id: 'macro-economist', name: '宏观分析师', role: '宏观面', icon: 'public', winRate: 0.58 },
  { id: 'sentiment-analyst', name: '情绪分析师', role: '情绪面', icon: 'psychology', winRate: 0.62 },
  { id: 'onchain-analyst', name: '链上分析师', role: '链上数据', icon: 'link', winRate: 0.60 },
  { id: 'risk-manager', name: '风险管理', role: '风控', icon: 'shield', winRate: 0.70 },
  { id: 'quant-strategist', name: '量化策略', role: '量化', icon: 'analytics', winRate: 0.55 },
  { id: 'trading-executor', name: '交易执行', role: '执行', icon: 'play_arrow', winRate: 0 },
  { id: 'position-monitor', name: '仓位监控', role: '监控', icon: 'monitoring', winRate: 0 },
  { id: 'trading-leader', name: '主持人', role: '协调', icon: 'emoji_events', winRate: 0.68 }
]);

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
  useOkxTrading: false  // Whether to use OKX demo trading
});
const loadingConfig = ref(false);

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

// WebSocket
let ws = null;
let countdownInterval = null;

// Computed
// Fixed initial capital
const INITIAL_CAPITAL = 3000;

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
  return tradingStartDate.value.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
});

// Total profit = current equity - initial capital
const totalProfit = computed(() => {
  return account.value.totalEquity - INITIAL_CAPITAL;
});

// Total profit percent
const totalProfitPercent = computed(() => {
  if (INITIAL_CAPITAL === 0) return 0;
  return (totalProfit.value / INITIAL_CAPITAL) * 100;
});

// Use initial_balance from account API for accurate PnL calculation
const totalPnl = computed(() => {
  const initial = account.value.initialBalance || account.value.totalEquity;
  return account.value.totalEquity - initial;
});
const totalPnlPercent = computed(() => {
  const initial = account.value.initialBalance || account.value.totalEquity;
  if (initial === 0) return 0;
  return (totalPnl.value / initial) * 100;
});

// Dynamic interval text based on actual scheduler state
const intervalText = computed(() => {
  // Prefer actual scheduler state over settings form
  const hours = systemStatus.value.scheduler?.interval_hours || settingsForm.value.analysisInterval || 4;
  const locale = localStorage.getItem('language') || 'zh-CN';
  if (locale === 'en') {
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
  return new Date(timestamp).toLocaleString();
}

function formatTime(timestamp) {
  if (!timestamp) return '';
  return new Date(timestamp).toLocaleTimeString();
}

async function fetchStatus() {
  try {
    const response = await fetch('/api/trading/status');
    const data = await response.json();
    systemStatus.value = data;
  } catch (e) {
    console.error('Error fetching status:', e);
  }
}

async function fetchAccount() {
  try {
    const response = await fetch('/api/trading/account');
    const data = await response.json();
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
    const response = await fetch('/api/trading/position');
    const data = await response.json();
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
    const response = await fetch('/api/trading/equity?limit=100');
    const data = await response.json();
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
    const response = await fetch(endpoint);
    const data = await response.json();
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

async function fetchTradeHistory() {
  try {
    const response = await fetch('/api/trading/history?limit=50');
    const data = await response.json();

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

async function fetchDiscussionMessages() {
  try {
    const response = await fetch('/api/trading/messages?limit=100');
    const data = await response.json();
    if (data.messages && data.messages.length > 0) {
      discussionMessages.value = data.messages.map(msg => ({
        agentName: msg.agent_name,
        content: msg.content,
        timestamp: msg.timestamp
      }));
    }
  } catch (e) {
    console.error('Error fetching discussion messages:', e);
  }
}

async function startTrading() {
  try {
    await fetch('/api/trading/start', { method: 'POST' });
    systemStatus.value.enabled = true;
  } catch (e) {
    console.error('Error starting trading:', e);
  }
}

async function stopTrading() {
  try {
    await fetch('/api/trading/stop', { method: 'POST' });
    systemStatus.value.enabled = false;
  } catch (e) {
    console.error('Error stopping trading:', e);
  }
}

async function triggerAnalysis() {
  try {
    await fetch('/api/trading/trigger', { method: 'POST' });
  } catch (e) {
    console.error('Error triggering analysis:', e);
  }
}

async function closePosition() {
  if (closingPosition.value) return;
  closingPosition.value = true;
  try {
    const response = await fetch('/api/trading/close', { method: 'POST' });
    const data = await response.json();
    if (data.error) {
      console.error('Error closing position:', data.error);
      discussionMessages.value.push({
        agentName: '系统',
        content: `平仓失败: ${data.error}`,
        timestamp: new Date().toISOString()
      });
    } else {
      discussionMessages.value.push({
        agentName: '系统',
        content: `手动平仓成功，盈亏: $${data.pnl?.toFixed(2) || '0.00'}`,
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
    const response = await fetch('/api/trading/agents/memory');
    const data = await response.json();
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
    const response = await fetch('/api/trading/config');
    const data = await response.json();
    if (data) {
      settingsForm.value = {
        analysisInterval: data.analysis_interval_hours || 4,
        maxLeverage: data.max_leverage || 20,
        maxPositionPercent: data.max_position_percent || 0.3,
        useOkxTrading: data.trader_type === 'okx'
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
    const response = await fetch('/api/trading/config', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_interval_hours: parseInt(settingsForm.value.analysisInterval),
        max_leverage: parseInt(settingsForm.value.maxLeverage),
        max_position_percent: parseFloat(settingsForm.value.maxPositionPercent),
        use_okx_trading: settingsForm.value.useOkxTrading
      })
    });
    const data = await response.json();
    if (data.status === 'updated') {
      showSettings.value = false;

      let message = '设置已更新';
      if (data.needs_restart) {
        message = '设置已更新。切换交易模式需要重置系统才能生效。';
      }

      discussionMessages.value.push({
        agentName: '系统',
        content: message,
        timestamp: new Date().toISOString()
      });
    }
  } catch (e) {
    console.error('Error saving settings:', e);
  } finally {
    savingSettings.value = false;
  }
}

async function resetSystem() {
  if (!confirm('Are you sure you want to reset the trading system? This will close all positions and clear all history.')) {
    return;
  }

  resettingSystem.value = true;
  try {
    const response = await fetch('/api/trading/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await response.json();

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
        agentName: 'System',
        content: `Trading system has been reset. Trader type: ${data.trader_type}`,
        timestamp: new Date().toISOString()
      });

      // Refresh status
      await fetchStatus();
    } else if (data.error) {
      alert('Reset failed: ' + data.error);
    }
  } catch (e) {
    console.error('Error resetting system:', e);
    alert('Failed to reset system');
  } finally {
    resettingSystem.value = false;
  }
}

let isComponentMounted = false;
let reconnectTimeout = null;

function connectWebSocket() {
  if (!isComponentMounted) return;

  const sessionId = 'trading-' + Date.now();
  // In development, connect directly to backend (port 8000)
  // In production, use the same host
  const isDev = window.location.port === '5173';
  const wsHost = isDev ? 'localhost:8000' : window.location.host;
  const wsUrl = `ws://${wsHost}/api/trading/ws/${sessionId}`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('Trading WebSocket connected');
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    handleWebSocketMessage(msg);
  };

  ws.onclose = () => {
    console.log('Trading WebSocket disconnected');
    // Reconnect after delay only if component is still mounted
    if (isComponentMounted) {
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
        agentName: '系统',
        content: '交易系统已启动，正在进行首次分析...',
        timestamp: new Date().toISOString()
      });
      break;

    case 'system_stopped':
      systemStatus.value.enabled = false;
      isAnalyzing.value = false;
      discussionMessages.value.push({
        agentName: '系统',
        content: '交易系统已停止',
        timestamp: new Date().toISOString()
      });
      break;

    case 'analysis_started':
      isAnalyzing.value = true;
      discussionMessages.value = [];
      discussionMessages.value.push({
        agentName: '系统',
        content: '开始新一轮市场分析...',
        timestamp: new Date().toISOString()
      });
      break;

    case 'analysis_error':
      isAnalyzing.value = false;
      discussionMessages.value.push({
        agentName: '系统',
        content: `分析出错: ${msg.error || '未知错误'}`,
        timestamp: new Date().toISOString()
      });
      break;

    case 'agent_message':
      discussionMessages.value.push({
        agentName: msg.agent_name,
        content: msg.content,
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
      discussionMessages.value.push({
        agentName: '系统',
        content: `交易信号生成: ${msg.signal?.direction || 'N/A'}`,
        timestamp: new Date().toISOString()
      });
      break;

    case 'trade_executed':
      // Trade has been executed, refresh all trading data immediately
      fetchPosition();
      fetchAccount();
      fetchTradeHistory();
      discussionMessages.value.push({
        agentName: '系统',
        content: msg.success
          ? `交易执行成功: ${msg.signal?.direction?.toUpperCase()} ${msg.signal?.leverage || 1}x`
          : `交易执行失败: ${msg.trade_result?.error || '未知错误'}`,
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
        agentName: '系统',
        content: `仓位已平仓，盈亏: $${msg.pnl?.toFixed(2) || '0.00'}`,
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
  await Promise.all([
    fetchStatus(),
    fetchAccount(),
    fetchPosition(),
    fetchTradeHistory()
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
    fetchDrawdown()  // Fetch drawdown data
  ]);

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
