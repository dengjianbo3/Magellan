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
                report.status === 'completed' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' :
                report.status === 'in-progress' ? 'bg-amber-500/10 border-amber-500/20 text-amber-400' :
                'bg-white/5 border-white/10 text-text-secondary'
              ]"
            >
              <span class="material-symbols-outlined text-2xl">article</span>
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
        <!-- Analysis Steps -->
        <div class="glass-panel rounded-2xl p-6">
          <h2 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
             <span class="material-symbols-outlined text-primary">checklist</span> 分析步骤
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
                <p class="font-bold text-text-primary text-sm">{{ step.title }}</p>
                <p v-if="step.result" class="text-xs text-text-secondary mt-1 leading-relaxed">{{ step.result }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Preliminary IM -->
        <div v-if="selectedReport.preliminary_im" class="glass-panel rounded-2xl p-6">
          <h2 class="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <span class="material-symbols-outlined text-accent-violet">description</span> 投资备忘录
          </h2>

          <div class="grid grid-cols-1 gap-6">
             <!-- Company Info -->
             <div v-if="selectedReport.preliminary_im.company_info" class="p-5 rounded-xl bg-black/20 border border-white/10">
               <h3 class="font-bold text-primary mb-3 text-sm uppercase tracking-wider">公司信息</h3>
               <div class="space-y-2 text-sm">
                 <div class="flex justify-between border-b border-white/5 pb-2">
                   <span class="text-text-secondary">名称</span>
                   <span class="text-white font-semibold">{{ selectedReport.preliminary_im.company_info.name || selectedReport.company_name }}</span>
                 </div>
                 <div class="flex justify-between border-b border-white/5 pb-2" v-if="selectedReport.preliminary_im.company_info.industry">
                   <span class="text-text-secondary">行业</span>
                   <span class="text-white">{{ selectedReport.preliminary_im.company_info.industry }}</span>
                 </div>
                 <div class="flex justify-between" v-if="selectedReport.preliminary_im.company_info.stage">
                   <span class="text-text-secondary">阶段</span>
                   <span class="text-white">{{ selectedReport.preliminary_im.company_info.stage }}</span>
                 </div>
               </div>
             </div>

             <!-- Team & Market -->
             <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
               <div v-if="selectedReport.preliminary_im.team_section" class="p-5 rounded-xl bg-black/20 border border-white/10">
                 <h3 class="font-bold text-primary mb-3 text-sm uppercase tracking-wider">团队评估</h3>
                 <p class="text-sm text-text-secondary leading-relaxed">{{ selectedReport.preliminary_im.team_section.summary || '团队分析已完成' }}</p>
               </div>

               <div v-if="selectedReport.preliminary_im.market_section" class="p-5 rounded-xl bg-black/20 border border-white/10">
                 <h3 class="font-bold text-primary mb-3 text-sm uppercase tracking-wider">市场分析</h3>
                 <p class="text-sm text-text-secondary leading-relaxed">{{ selectedReport.preliminary_im.market_section.summary || '市场分析已完成' }}</p>
               </div>
             </div>
          </div>

          <!-- DD Questions -->
          <div v-if="selectedReport.preliminary_im.dd_questions && selectedReport.preliminary_im.dd_questions.length > 0" class="mt-6 pt-6 border-t border-white/10">
            <h3 class="font-bold text-white mb-4 text-sm uppercase tracking-wider">关键问题与答案</h3>
            <div class="space-y-4">
              <div
                v-for="(question, index) in selectedReport.preliminary_im.dd_questions"
                :key="index"
                class="p-4 rounded-xl bg-white/5 border border-white/5"
              >
                <div class="flex gap-3">
                  <span class="text-primary font-bold">{{ index + 1 }}.</span>
                  <p class="font-semibold text-text-primary text-sm">{{ question.question || question }}</p>
                </div>
                <div v-if="question.answer" class="mt-3 pl-6 border-l-2 border-white/10 ml-1">
                  <p class="text-sm text-text-secondary">{{ question.answer }}</p>
                </div>
                <div v-else class="mt-2 pl-6">
                   <span class="text-xs text-text-secondary italic opacity-50">未回答</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Visual Analytics -->
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
              <p class="text-white font-mono text-xs bg-white/5 p-2 rounded">{{ selectedReport.session_id }}</p>
            </div>
            <div class="pb-3 border-b border-white/5">
              <span class="text-text-secondary block text-xs mb-1">分析类型</span>
              <p class="text-white font-bold">{{ selectedReport.analysis_type }}</p>
            </div>
            <div>
              <span class="text-text-secondary block text-xs mb-1">保存时间</span>
              <p class="text-white font-mono">{{ selectedReport.saved_at ? new Date(selectedReport.saved_at).toLocaleString('zh-CN') : 'N/A' }}</p>
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
import { useLanguage } from '../composables/useLanguage';
import { useToast } from '@/composables/useToast';

const { t } = useLanguage();
const { success, error: showError } = useToast();

const reportsData = ref([]);
const loading = ref(true);
const error = ref(null);
const selectedReport = ref(null); // For viewing report details
const showDeleteConfirm = ref(false); // Delete confirmation dialog
const reportToDelete = ref(null); // Report being deleted
const exportMenuReportId = ref(null); // Track which report's export menu is open
const exportLoading = ref(false); // Track export operation state

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

onMounted(() => {
  fetchReports();
});
</script>