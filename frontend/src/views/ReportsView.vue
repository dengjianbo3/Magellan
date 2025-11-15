<template>
  <div v-if="!selectedReport" class="space-y-6">
    <!-- Page Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-text-primary mb-2">{{ t('reports.title') }}</h1>
        <p class="text-text-secondary">{{ t('reports.subtitle') }}</p>
      </div>
      <button class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-background-dark font-semibold hover:bg-primary/90 transition-colors">
        <span class="material-symbols-outlined">add</span>
        {{ t('reports.newReport') }}
      </button>
    </div>

    <!-- Filters -->
    <div class="flex items-center gap-4">
      <select class="px-4 py-2 rounded-lg bg-surface border border-border-color text-text-primary">
        <option>{{ t('reports.filters.allTypes') }}</option>
        <option>{{ t('reports.filters.dueDiligence') }}</option>
        <option>{{ t('reports.filters.marketAnalysis') }}</option>
        <option>{{ t('reports.filters.financialReview') }}</option>
      </select>
      <select class="px-4 py-2 rounded-lg bg-surface border border-border-color text-text-primary">
        <option>{{ t('reports.filters.allStatus') }}</option>
        <option>{{ t('reports.filters.completed') }}</option>
        <option>{{ t('reports.filters.inProgress') }}</option>
        <option>{{ t('reports.filters.draft') }}</option>
      </select>
      <div class="flex-1"></div>
      <div class="relative">
        <input
          type="text"
          :placeholder="t('reports.searchPlaceholder')"
          class="w-64 px-4 py-2 pl-10 rounded-lg bg-surface border border-border-color text-text-primary placeholder-text-secondary focus:outline-none focus:border-primary transition-colors"
        />
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary">
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
        class="bg-surface border border-border-color rounded-lg p-6 hover:border-primary/50 transition-colors cursor-pointer group"
      >
        <div class="flex items-start justify-between mb-4">
          <div
            :class="[
              'w-12 h-12 rounded-lg flex items-center justify-center',
              report.status === 'completed' ? 'bg-accent-green/20' :
              report.status === 'in-progress' ? 'bg-accent-yellow/20' :
              'bg-surface-light'
            ]"
          >
            <span
              :class="[
                'material-symbols-outlined text-2xl',
                report.status === 'completed' ? 'text-accent-green' :
                report.status === 'in-progress' ? 'text-accent-yellow' :
                'text-text-secondary'
              ]"
            >
              article
            </span>
          </div>
          <span
            :class="[
              'text-xs px-3 py-1 rounded-full font-semibold',
              report.status === 'completed' ? 'bg-accent-green/20 text-accent-green' :
              report.status === 'in-progress' ? 'bg-accent-yellow/20 text-accent-yellow' :
              'bg-surface-light text-text-secondary'
            ]"
          >
            {{ report.statusText }}
          </span>
        </div>

        <h3 class="text-lg font-bold text-text-primary mb-2 group-hover:text-primary transition-colors">
          {{ report.title }}
        </h3>
        <p class="text-sm text-text-secondary mb-4">{{ report.description }}</p>

        <div class="flex items-center gap-4 text-xs text-text-secondary mb-4">
          <span class="flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">calendar_today</span>
            {{ report.date }}
          </span>
          <span class="flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">smart_toy</span>
            {{ report.agents }} {{ t('reports.card.agents') }}
          </span>
        </div>

        <div class="flex items-center gap-2">
          <button class="flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg bg-primary text-background-dark hover:bg-primary/90 transition-colors text-sm font-semibold">
            <span class="material-symbols-outlined text-sm">visibility</span>
            {{ t('reports.card.view') }}
          </button>
          <button class="px-3 py-2 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors">
            <span class="material-symbols-outlined text-sm">download</span>
          </button>
          <button class="px-3 py-2 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors">
            <span class="material-symbols-outlined text-sm">share</span>
          </button>
          <button
            @click.stop="confirmDelete(report.id)"
            class="px-3 py-2 rounded-lg border border-border-color text-accent-red hover:bg-accent-red/10 transition-colors"
            title="删除报告"
          >
            <span class="material-symbols-outlined text-sm">delete</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Report Detail View -->
  <div v-else class="space-y-6">
    <!-- Header with Back Button -->
    <div class="flex items-center gap-4">
      <button
        @click="closeReportView"
        class="px-4 py-2 rounded-lg bg-surface border border-border-color text-text-primary hover:bg-background-dark transition-colors flex items-center gap-2"
      >
        <span class="material-symbols-outlined">arrow_back</span>
        返回报告列表
      </button>
      <div class="flex-1">
        <h1 class="text-2xl font-bold text-text-primary">{{ selectedReport.project_name }}</h1>
        <p class="text-sm text-text-secondary">{{ selectedReport.company_name }} • {{ new Date(selectedReport.created_at).toLocaleString('zh-CN') }}</p>
      </div>
    </div>

    <!-- Report Content -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Main Content -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Analysis Steps -->
        <div class="bg-surface border border-border-color rounded-lg p-6">
          <h2 class="text-lg font-bold text-text-primary mb-4">分析步骤</h2>
          <div class="space-y-3">
            <div
              v-for="step in selectedReport.steps"
              :key="step.id"
              class="flex items-center gap-3 p-3 rounded-lg bg-background-dark"
            >
              <div
                :class="[
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  step.status === 'success' ? 'bg-accent-green/20' :
                  step.status === 'error' ? 'bg-accent-red/20' :
                  step.status === 'skipped' ? 'bg-text-secondary/10' :
                  'bg-surface-light'
                ]"
              >
                <span
                  :class="[
                    'material-symbols-outlined text-sm',
                    step.status === 'success' ? 'text-accent-green' :
                    step.status === 'error' ? 'text-accent-red' :
                    step.status === 'skipped' ? 'text-text-secondary' :
                    'text-text-secondary'
                  ]"
                >
                  {{
                    step.status === 'success' ? 'check_circle' :
                    step.status === 'error' ? 'error' :
                    step.status === 'skipped' ? 'block' :
                    'radio_button_unchecked'
                  }}
                </span>
              </div>
              <div class="flex-1">
                <p class="font-semibold text-text-primary">{{ step.title }}</p>
                <p v-if="step.result" class="text-xs text-text-secondary mt-1">{{ step.result }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Preliminary IM -->
        <div v-if="selectedReport.preliminary_im" class="bg-surface border border-border-color rounded-lg p-6">
          <h2 class="text-lg font-bold text-text-primary mb-4">投资备忘录</h2>

          <!-- Company Info -->
          <div v-if="selectedReport.preliminary_im.company_info" class="mb-4 p-4 rounded-lg bg-background-dark">
            <h3 class="font-semibold text-text-primary mb-2">公司信息</h3>
            <div class="text-sm text-text-secondary space-y-1">
              <p><strong>公司名称:</strong> {{ selectedReport.preliminary_im.company_info.name || selectedReport.company_name }}</p>
              <p v-if="selectedReport.preliminary_im.company_info.industry"><strong>行业:</strong> {{ selectedReport.preliminary_im.company_info.industry }}</p>
              <p v-if="selectedReport.preliminary_im.company_info.stage"><strong>阶段:</strong> {{ selectedReport.preliminary_im.company_info.stage }}</p>
            </div>
          </div>

          <!-- Team Analysis -->
          <div v-if="selectedReport.preliminary_im.team_section" class="mb-4 p-4 rounded-lg bg-background-dark">
            <h3 class="font-semibold text-text-primary mb-2">团队评估</h3>
            <p class="text-sm text-text-secondary">{{ selectedReport.preliminary_im.team_section.summary || '团队分析已完成' }}</p>
          </div>

          <!-- Market Analysis -->
          <div v-if="selectedReport.preliminary_im.market_section" class="mb-4 p-4 rounded-lg bg-background-dark">
            <h3 class="font-semibold text-text-primary mb-2">市场分析</h3>
            <p class="text-sm text-text-secondary">{{ selectedReport.preliminary_im.market_section.summary || '市场分析已完成' }}</p>
          </div>

          <!-- DD Questions & Answers -->
          <div v-if="selectedReport.preliminary_im.dd_questions && selectedReport.preliminary_im.dd_questions.length > 0" class="mt-4 p-4 rounded-lg bg-background-dark">
            <h3 class="font-semibold text-text-primary mb-3">关键问题与答案</h3>
            <div class="space-y-3">
              <div
                v-for="(question, index) in selectedReport.preliminary_im.dd_questions"
                :key="index"
                class="p-3 rounded-lg bg-surface"
              >
                <p class="font-semibold text-text-primary mb-1">{{ index + 1 }}. {{ question.question || question }}</p>
                <p v-if="question.answer" class="text-sm text-text-secondary mt-2">
                  <strong>答案:</strong> {{ question.answer }}
                </p>
                <p v-else class="text-xs text-text-secondary italic mt-2">未回答</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Sidebar -->
      <div class="space-y-6">
        <!-- Meta Info -->
        <div class="bg-surface border border-border-color rounded-lg p-4">
          <h3 class="font-bold text-text-primary mb-3">报告信息</h3>
          <div class="space-y-2 text-sm">
            <div>
              <span class="text-text-secondary">Session ID:</span>
              <p class="text-text-primary font-mono text-xs mt-1">{{ selectedReport.session_id }}</p>
            </div>
            <div>
              <span class="text-text-secondary">分析类型:</span>
              <p class="text-text-primary mt-1">{{ selectedReport.analysis_type }}</p>
            </div>
            <div>
              <span class="text-text-secondary">状态:</span>
              <p class="text-text-primary mt-1">{{ selectedReport.status }}</p>
            </div>
            <div>
              <span class="text-text-secondary">创建时间:</span>
              <p class="text-text-primary mt-1">{{ new Date(selectedReport.created_at).toLocaleString('zh-CN') }}</p>
            </div>
            <div v-if="selectedReport.saved_at">
              <span class="text-text-secondary">保存时间:</span>
              <p class="text-text-primary mt-1">{{ new Date(selectedReport.saved_at).toLocaleString('zh-CN') }}</p>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="bg-surface border border-border-color rounded-lg p-4">
          <h3 class="font-bold text-text-primary mb-3">操作</h3>
          <div class="space-y-2">
            <button class="w-full px-4 py-2 rounded-lg bg-primary text-background-dark hover:bg-primary/90 transition-colors flex items-center justify-center gap-2">
              <span class="material-symbols-outlined">download</span>
              导出报告
            </button>
            <button class="w-full px-4 py-2 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors flex items-center justify-center gap-2">
              <span class="material-symbols-outlined">share</span>
              分享报告
            </button>
            <button
              @click="confirmDelete(selectedReport.id)"
              class="w-full px-4 py-2 rounded-lg border border-accent-red text-accent-red hover:bg-accent-red/10 transition-colors flex items-center justify-center gap-2"
            >
              <span class="material-symbols-outlined">delete</span>
              删除报告
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Delete Confirmation Dialog -->
  <div
    v-if="showDeleteConfirm"
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    @click="cancelDelete"
  >
    <div
      class="bg-surface border border-border-color rounded-lg p-6 max-w-md w-full mx-4"
      @click.stop
    >
      <div class="flex items-start gap-4 mb-6">
        <div class="w-12 h-12 rounded-full bg-accent-red/20 flex items-center justify-center flex-shrink-0">
          <span class="material-symbols-outlined text-accent-red text-2xl">warning</span>
        </div>
        <div class="flex-1">
          <h3 class="text-lg font-bold text-text-primary mb-2">删除报告</h3>
          <p class="text-sm text-text-secondary">
            确定要删除报告 <strong>"{{ reportToDelete?.project_name || reportToDelete?.company_name }}"</strong> 吗？
          </p>
          <p class="text-sm text-text-secondary mt-2">此操作无法撤销。</p>
        </div>
      </div>

      <div class="flex items-center gap-3 justify-end">
        <button
          @click="cancelDelete"
          class="px-4 py-2 rounded-lg border border-border-color text-text-primary hover:bg-background-dark transition-colors"
        >
          取消
        </button>
        <button
          @click="deleteReport"
          class="px-4 py-2 rounded-lg bg-accent-red text-white hover:bg-accent-red/90 transition-colors flex items-center gap-2"
        >
          <span class="material-symbols-outlined text-sm">delete</span>
          删除
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useLanguage } from '../composables/useLanguage';

const { t } = useLanguage();

const reportsData = ref([]);
const loading = ref(true);
const error = ref(null);
const selectedReport = ref(null); // For viewing report details
const showDeleteConfirm = ref(false); // Delete confirmation dialog
const reportToDelete = ref(null); // Report being deleted

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
  const agentCount = report.steps ? report.steps.filter(s => s.status === 'success').length : 0;

  return {
    id: report.id,
    title: report.project_name || `${report.company_name} Analysis`,
    description: `${report.analysis_type} analysis for ${report.company_name}`,
    date: formattedDate,
    status: statusMap[report.status] || 'completed',
    statusText: t(`reports.status.${statusMap[report.status] || 'completed'}`),
    agents: agentCount,
    type: report.analysis_type
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
    const response = await fetch(`http://localhost:8000/api/reports/${reportId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch report: ${response.statusText}`);
    }

    const data = await response.json();
    selectedReport.value = data.report;
    console.log('[ReportsView] Viewing report:', selectedReport.value);
  } catch (err) {
    console.error('[ReportsView] Failed to fetch report details:', err);
    alert('获取报告详情失败: ' + err.message);
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

    // Remove from local list
    reportsData.value = reportsData.value.filter(r => r.id !== reportToDelete.value.id);

    // Close dialog
    showDeleteConfirm.value = false;
    reportToDelete.value = null;

    // If we were viewing the deleted report, close detail view
    if (selectedReport.value && selectedReport.value.id === reportToDelete.value.id) {
      selectedReport.value = null;
    }
  } catch (err) {
    console.error('[ReportsView] Failed to delete report:', err);
    alert('删除报告失败: ' + err.message);
  }
};

onMounted(() => {
  fetchReports();
});
</script>
