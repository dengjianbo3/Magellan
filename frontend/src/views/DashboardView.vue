<template>
  <div class="space-y-8">
    <!-- Page Header -->
    <div class="flex items-end justify-between">
      <div>
        <h1 class="text-3xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-text-secondary mb-2 tracking-tight">{{ t('dashboard.title') }}</h1>
        <p class="text-text-secondary text-lg font-light">{{ t('dashboard.welcome') }}</p>
      </div>
      <button
        class="group flex items-center gap-2 px-6 py-2.5 rounded-lg bg-gradient-to-r from-primary to-primary-dark text-white font-bold shadow-glow-sm hover:shadow-glow hover:scale-105 transition-all duration-300"
      >
        <span class="material-symbols-outlined group-hover:animate-bounce">download</span>
        {{ t('dashboard.exportReport') }}
      </button>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard
        v-for="stat in stats"
        :key="stat.title"
        :title="stat.title"
        :value="stat.value"
        :change="stat.change"
        :icon="stat.icon"
        :trend="stat.trend"
      />
    </div>

    <!-- Charts Row -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Analysis Trends Chart -->
      <div class="glass-panel rounded-xl p-6 relative overflow-hidden">
        <div class="flex items-center justify-between mb-8">
          <h3 class="text-lg font-bold text-white flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">show_chart</span>
            {{ t('dashboard.analysisTrends') }}
          </h3>
          <select class="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-text-primary text-sm focus:border-primary/50 focus:outline-none focus:bg-surface/50 transition-colors">
            <option>{{ t('dashboard.timeRanges.last7Days') }}</option>
            <option>{{ t('dashboard.timeRanges.last30Days') }}</option>
            <option>{{ t('dashboard.timeRanges.last3Months') }}</option>
          </select>
        </div>
        <div class="h-72 relative z-10">
          <canvas ref="trendsChart"></canvas>
        </div>
        <!-- Decorative background glow -->
        <div class="absolute top-0 right-0 w-64 h-64 bg-primary/5 blur-3xl rounded-full pointer-events-none"></div>
      </div>

      <!-- Agent Performance Chart -->
      <div class="glass-panel rounded-xl p-6 relative overflow-hidden">
        <div class="flex items-center justify-between mb-8">
          <h3 class="text-lg font-bold text-white flex items-center gap-2">
            <span class="material-symbols-outlined text-accent-violet">donut_large</span>
            {{ t('dashboard.agentPerformance') }}
          </h3>
          <select class="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-text-primary text-sm focus:border-primary/50 focus:outline-none focus:bg-surface/50 transition-colors">
            <option>{{ t('dashboard.timeRanges.thisMonth') }}</option>
            <option>{{ t('dashboard.timeRanges.lastMonth') }}</option>
            <option>{{ t('dashboard.timeRanges.allTime') }}</option>
          </select>
        </div>
        <div class="h-72 relative z-10">
          <canvas ref="performanceChart"></canvas>
        </div>
         <!-- Decorative background glow -->
         <div class="absolute bottom-0 left-0 w-64 h-64 bg-accent-violet/5 blur-3xl rounded-full pointer-events-none"></div>
      </div>
    </div>

    <!-- Recent Activity & Quick Actions -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Recent Reports -->
      <div class="lg:col-span-2 glass-panel rounded-xl p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-bold text-white flex items-center gap-2">
            <span class="material-symbols-outlined text-emerald-400">history</span>
            {{ t('dashboard.recentReports') }}
          </h3>
          <button @click="emit('navigate', 'reports')" class="text-primary text-sm font-bold hover:text-primary-dark transition-colors hover:underline">{{ t('dashboard.viewAll') }}</button>
        </div>
        <div class="space-y-2">
          <ReportItem
            v-for="report in recentReports"
            :key="report.id"
            :title="report.title"
            :date="report.date"
            :status="report.status"
            :agents="report.agents"
          />
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="glass-panel rounded-xl p-6">
        <h3 class="text-lg font-bold text-white mb-6 flex items-center gap-2">
          <span class="material-symbols-outlined text-amber-400">bolt</span>
          {{ t('dashboard.quickActions') }}
        </h3>
        <div class="space-y-3">
          <button
            v-for="action in quickActions"
            :key="action.title"
            @click="handleQuickAction(action)"
            class="w-full flex items-center gap-4 p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-transparent hover:border-primary/30 transition-all duration-300 text-left group"
          >
            <div class="w-10 h-10 rounded-lg bg-background-dark flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
               <span class="material-symbols-outlined text-primary group-hover:text-white transition-colors">{{ action.icon }}</span>
            </div>
            <div class="flex-1">
              <p class="text-sm font-bold text-text-primary group-hover:text-primary transition-colors">
                {{ action.title }}
              </p>
              <p class="text-xs text-text-secondary">{{ action.description }}</p>
            </div>
            <span class="material-symbols-outlined text-text-secondary group-hover:translate-x-1 transition-transform">chevron_right</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Active Agents -->
    <div class="glass-panel rounded-xl p-6">
      <h3 class="text-lg font-bold text-white mb-6 flex items-center gap-2">
        <span class="material-symbols-outlined text-primary">smart_toy</span>
        {{ t('dashboard.activeAgents') }}
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <AgentCard
          v-for="agent in activeAgents"
          :key="agent.name"
          :name="agent.name"
          :status="agent.status"
          :tasks="agent.tasks"
          :icon="agent.icon"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import Chart from 'chart.js/auto';
import { useLanguage } from '../composables/useLanguage';
import StatCard from '../components/dashboard/StatCard.vue';
import ReportItem from '../components/dashboard/ReportItem.vue';
import AgentCard from '../components/dashboard/AgentCard.vue';

const { t } = useLanguage();

// Define emit for navigation events
const emit = defineEmits(['navigate']);

const trendsChart = ref(null);
const performanceChart = ref(null);

// API data
const statsData = ref(null);
const recentReportsData = ref([]);
const trendsData = ref(null);
const performanceData = ref(null);
const loading = ref(true);

const stats = computed(() => {
  if (!statsData.value) {
    return [
      {
        title: t('dashboard.stats.totalReports'),
        value: '0',
        change: '+0%',
        trend: 'neutral',
        icon: 'article'
      },
      {
        title: t('dashboard.stats.activeAnalyses'),
        value: '0',
        change: '+0',
        trend: 'neutral',
        icon: 'analytics'
      },
      {
        title: t('dashboard.stats.aiAgents'),
        value: '6',
        change: '0',
        trend: 'neutral',
        icon: 'smart_toy'
      },
      {
        title: t('dashboard.stats.successRate'),
        value: '0%',
        change: '+0%',
        trend: 'neutral',
        icon: 'trending_up'
      }
    ];
  }

  const stats = statsData.value;
  return [
    {
      title: t('dashboard.stats.totalReports'),
      value: String(stats.total_reports.value),
      change: stats.total_reports.change,
      trend: stats.total_reports.trend,
      icon: 'article'
    },
    {
      title: t('dashboard.stats.activeAnalyses'),
      value: String(stats.active_analyses.value),
      change: stats.active_analyses.change,
      trend: stats.active_analyses.trend,
      icon: 'analytics'
    },
    {
      title: t('dashboard.stats.aiAgents'),
      value: String(stats.ai_agents.value),
      change: stats.ai_agents.change,
      trend: stats.ai_agents.trend,
      icon: 'smart_toy'
    },
    {
      title: t('dashboard.stats.successRate'),
      value: stats.success_rate.value,
      change: stats.success_rate.change,
      trend: stats.success_rate.trend,
      icon: 'trending_up'
    }
  ];
});

const recentReports = computed(() => recentReportsData.value);

const quickActions = computed(() => [
  {
    id: 'new-analysis',
    title: t('dashboard.quickActionItems.newAnalysis.title'),
    description: t('dashboard.quickActionItems.newAnalysis.description'),
    icon: 'add_circle',
    tab: 'analysis'
  },
  {
    id: 'upload-data',
    title: t('dashboard.quickActionItems.uploadData.title'),
    description: t('dashboard.quickActionItems.uploadData.description'),
    icon: 'cloud_upload',
    tab: 'knowledge'
  },
  {
    id: 'configure-agent',
    title: t('dashboard.quickActionItems.configureAgent.title'),
    description: t('dashboard.quickActionItems.configureAgent.description'),
    icon: 'settings_suggest',
    tab: 'agents'
  },
  {
    id: 'view-reports',
    title: t('dashboard.quickActionItems.viewReports.title'),
    description: t('dashboard.quickActionItems.viewReports.description'),
    icon: 'folder_open',
    tab: 'reports'
  }
]);

// Handle quick action clicks
const handleQuickAction = (action) => {
  if (action.tab) {
    emit('navigate', action.tab);
  }
};

const activeAgents = computed(() => [
  {
    name: t('analysis.step2.agents.marketAnalyst.name'),
    status: t('dashboard.agentStatus.active'),
    tasks: 12,
    icon: 'show_chart'
  },
  {
    name: t('analysis.step2.agents.financialExpert.name'),
    status: t('dashboard.agentStatus.active'),
    tasks: 8,
    icon: 'account_balance'
  },
  {
    name: t('analysis.step2.agents.teamEvaluator.name'),
    status: t('dashboard.agentStatus.idle'),
    tasks: 0,
    icon: 'groups'
  },
  {
    name: t('analysis.step2.agents.riskAssessor.name'),
    status: t('dashboard.agentStatus.active'),
    tasks: 5,
    icon: 'shield'
  }
]);

// Fetch dashboard data
const fetchDashboardData = async () => {
  try {
    loading.value = true;

    // Fetch stats
    const statsResponse = await fetch('http://localhost:8000/api/dashboard/stats');
    if (statsResponse.ok) {
      const data = await statsResponse.json();
      statsData.value = data.stats;
    }

    // Fetch recent reports
    const reportsResponse = await fetch('http://localhost:8000/api/dashboard/recent-reports?limit=4');
    if (reportsResponse.ok) {
      const data = await reportsResponse.json();
      recentReportsData.value = data.reports;
    }

    // Fetch trends data
    const trendsResponse = await fetch('http://localhost:8000/api/dashboard/trends?days=7');
    if (trendsResponse.ok) {
      const data = await trendsResponse.json();
      trendsData.value = data;
    }

    // Fetch performance data
    const performanceResponse = await fetch('http://localhost:8000/api/dashboard/agent-performance');
    if (performanceResponse.ok) {
      const data = await performanceResponse.json();
      performanceData.value = data.performance;
    }

    loading.value = false;
  } catch (error) {
    console.error('[Dashboard] Failed to fetch data:', error);
    loading.value = false;
  }
};

// Initialize charts
const initializeCharts = () => {
  // Initialize Trends Chart
  if (trendsChart.value && trendsData.value) {
    const ctx = trendsChart.value.getContext('2d');
    
    // Create Gradients
    const gradientReports = ctx.createLinearGradient(0, 0, 0, 300);
    gradientReports.addColorStop(0, 'rgba(56, 189, 248, 0.4)');
    gradientReports.addColorStop(1, 'rgba(56, 189, 248, 0.0)');
    
    const gradientAnalysis = ctx.createLinearGradient(0, 0, 0, 300);
    gradientAnalysis.addColorStop(0, 'rgba(139, 92, 246, 0.4)');
    gradientAnalysis.addColorStop(1, 'rgba(139, 92, 246, 0.0)');

    new Chart(trendsChart.value, {
      type: 'line',
      data: {
        labels: trendsData.value.labels,
        datasets: [
          {
            label: t('dashboard.chartLabels.reportsGenerated'),
            data: trendsData.value.datasets.reports,
            borderColor: '#38bdf8',
            backgroundColor: gradientReports,
            borderWidth: 2,
            pointBackgroundColor: '#38bdf8',
            pointBorderColor: '#000',
            pointRadius: 4,
            pointHoverRadius: 6,
            tension: 0.4,
            fill: true
          },
          {
            label: t('dashboard.chartLabels.analysesStarted'),
            data: trendsData.value.datasets.analyses,
            borderColor: '#8b5cf6',
            backgroundColor: gradientAnalysis,
            borderWidth: 2,
            pointBackgroundColor: '#8b5cf6',
            pointBorderColor: '#000',
            pointRadius: 4,
            pointHoverRadius: 6,
            tension: 0.4,
            fill: true
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { 
              color: '#9ca3af',
              font: { family: 'Inter', size: 12 }
            },
            align: 'end'
          },
          tooltip: {
            backgroundColor: 'rgba(17, 24, 39, 0.9)',
            titleColor: '#f3f4f6',
            bodyColor: '#9ca3af',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1,
            padding: 12,
            displayColors: true,
            boxPadding: 4
          }
        },
        scales: {
          y: {
            ticks: { color: '#6b7280', font: { size: 11 } },
            grid: { color: 'rgba(255, 255, 255, 0.03)' },
            border: { display: false }
          },
          x: {
            ticks: { color: '#6b7280', font: { size: 11 } },
            grid: { display: false },
            border: { display: false }
          }
        }
      }
    });
  }

  // Initialize Performance Chart
  if (performanceChart.value && performanceData.value) {
    new Chart(performanceChart.value, {
      type: 'doughnut',
      data: {
        labels: [
          t('agentChat.tasks.marketAnalysis'),
          t('agentChat.tasks.financialReview'),
          t('agentChat.tasks.teamEvaluation'),
          t('agentChat.tasks.riskAssessment')
        ],
        datasets: [{
          data: [
            performanceData.value.market_analysis,
            performanceData.value.financial_review,
            performanceData.value.team_evaluation,
            performanceData.value.risk_assessment
          ],
          backgroundColor: [
            '#38bdf8', // Primary
            '#06b6d4', // Cyan
            '#8b5cf6', // Violet
            '#10b981'  // Emerald
          ],
          borderColor: '#111827', // Match card bg
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '75%',
        plugins: {
          legend: {
            position: 'right',
            labels: { 
              color: '#e5e7eb', 
              padding: 20,
              font: { family: 'Inter', size: 12 }
            }
          }
        }
      }
    });
  }
};

onMounted(async () => {
  await fetchDashboardData();
  initializeCharts();
});
</script>