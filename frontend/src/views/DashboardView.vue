<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-text-primary mb-2">{{ t('dashboard.title') }}</h1>
        <p class="text-text-secondary">{{ t('dashboard.welcome') }}</p>
      </div>
      <button
        class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-background-dark font-semibold hover:bg-primary/90 transition-colors"
      >
        <span class="material-symbols-outlined">download</span>
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
      <div class="bg-surface border border-border-color rounded-lg p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-bold text-text-primary">{{ t('dashboard.analysisTrends') }}</h3>
          <select class="px-3 py-1.5 rounded-lg bg-background-dark border border-border-color text-text-primary text-sm">
            <option>{{ t('dashboard.timeRanges.last7Days') }}</option>
            <option>{{ t('dashboard.timeRanges.last30Days') }}</option>
            <option>{{ t('dashboard.timeRanges.last3Months') }}</option>
          </select>
        </div>
        <div class="h-64">
          <canvas ref="trendsChart"></canvas>
        </div>
      </div>

      <!-- Agent Performance Chart -->
      <div class="bg-surface border border-border-color rounded-lg p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-bold text-text-primary">{{ t('dashboard.agentPerformance') }}</h3>
          <select class="px-3 py-1.5 rounded-lg bg-background-dark border border-border-color text-text-primary text-sm">
            <option>{{ t('dashboard.timeRanges.thisMonth') }}</option>
            <option>{{ t('dashboard.timeRanges.lastMonth') }}</option>
            <option>{{ t('dashboard.timeRanges.allTime') }}</option>
          </select>
        </div>
        <div class="h-64">
          <canvas ref="performanceChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Recent Activity & Quick Actions -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Recent Reports -->
      <div class="lg:col-span-2 bg-surface border border-border-color rounded-lg p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-bold text-text-primary">{{ t('dashboard.recentReports') }}</h3>
          <button @click="emit('navigate', 'reports')" class="text-primary text-sm font-semibold hover:underline">{{ t('dashboard.viewAll') }}</button>
        </div>
        <div class="space-y-4">
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
      <div class="bg-surface border border-border-color rounded-lg p-6">
        <h3 class="text-lg font-bold text-text-primary mb-6">{{ t('dashboard.quickActions') }}</h3>
        <div class="space-y-3">
          <button
            v-for="action in quickActions"
            :key="action.title"
            @click="handleQuickAction(action)"
            class="w-full flex items-center gap-3 p-3 rounded-lg bg-background-dark hover:bg-background-dark/80 border border-border-color transition-colors text-left group"
          >
            <span class="material-symbols-outlined text-primary">{{ action.icon }}</span>
            <div class="flex-1">
              <p class="text-sm font-semibold text-text-primary group-hover:text-primary transition-colors">
                {{ action.title }}
              </p>
              <p class="text-xs text-text-secondary">{{ action.description }}</p>
            </div>
          </button>
        </div>
      </div>
    </div>

    <!-- Active Agents -->
    <div class="bg-surface border border-border-color rounded-lg p-6">
      <h3 class="text-lg font-bold text-text-primary mb-6">{{ t('dashboard.activeAgents') }}</h3>
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
    new Chart(trendsChart.value, {
      type: 'line',
      data: {
        labels: trendsData.value.labels,
        datasets: [
          {
            label: t('dashboard.chartLabels.reportsGenerated'),
            data: trendsData.value.datasets.reports,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            tension: 0.4,
            fill: true
          },
          {
            label: t('dashboard.chartLabels.analysesStarted'),
            data: trendsData.value.datasets.analyses,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
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
            labels: { color: '#e5e7eb' }
          }
        },
        scales: {
          y: {
            ticks: { color: '#9ca3af' },
            grid: { color: 'rgba(255, 255, 255, 0.1)' }
          },
          x: {
            ticks: { color: '#9ca3af' },
            grid: { color: 'rgba(255, 255, 255, 0.1)' }
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
            '#3b82f6',
            '#10b981',
            '#f59e0b',
            '#ef4444'
          ],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#e5e7eb', padding: 15 }
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
