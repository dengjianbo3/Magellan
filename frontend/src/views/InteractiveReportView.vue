<!-- src/views/InteractiveReportView.vue -->
<template>
  <div class="dashboard-container">
    <!-- Left Column: Outline -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h3>报告大纲</h3>
      </div>
      <nav class="outline-nav">
        <ul>
          <li v-for="section in reportData.report_sections" :key="section.section_title">
            <a :href="`#section-${section.section_title}`" @click.prevent="scrollToSection(section.section_title)">
              {{ section.section_title }}
            </a>
          </li>
        </ul>
      </nav>
    </aside>

    <!-- Center Column: Main Content -->
    <main class="report-content" ref="reportContentEl">
      <header class="report-header">
        <h1>投资分析报告: {{ reportData.company_ticker }}</h1>
        <p>生成日期: {{ new Date().toLocaleDateString() }}</p>
      </header>
      <div v-for="section in reportData.report_sections" :key="section.section_title" :id="`section-${section.section_title}`" class="report-section">
        <GlassPaper>
          <h2>{{ section.section_title }}</h2>
          
          <!-- Conditional Rendering for Chart -->
          <div v-if="section.section_title === 'Financial Analysis' && reportData.financial_chart_data" ref="financialChartEl" class="chart-container"></div>
          <p v-else>{{ section.content }}</p>

          <div class="data-source">
            <span>(i) 数据来源: 模拟来源</span>
          </div>
        </GlassPaper>
      </div>
    </main>

    <!-- Right Column: Agent Assistant -->
    <aside class="assistant-panel">
      <div class="assistant-header">
        <h3>Agent 助手</h3>
      </div>
      <div class="assistant-content">
        <GlassPaper>
          <h4>关键追问</h4>
          <p>根据我们的分析，您可以在会议中提出以下关键问题：</p>
          <ul class="questions-list">
            <li v-for="question in keyQuestions" :key="question">{{ question }}</li>
          </ul>
        </GlassPaper>
        <GlassPaper style="margin-top: 1.5rem;">
          <h4>即时反馈</h4>
          <el-input
            type="textarea"
            :rows="4"
            placeholder="在此输入对方的回答，Agent将为您提供即时反馈..."
            v-model="feedbackText"
            :disabled="isFeedbackLoading"
          />
          <el-button 
            type="primary" 
            size="small" 
            style="margin-top: 1rem;"
            @click="handleFeedbackSubmit"
            :loading="isFeedbackLoading"
          >
            提交反馈
          </el-button>
          <div v-if="feedbackResponse" class="feedback-response">
            <p>{{ feedbackResponse }}</p>
          </div>
        </GlassPaper>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch, computed } from 'vue';
import { ElInput, ElButton, ElMessage } from 'element-plus';
import GlassPaper from '../components/GlassPaper.vue';
import { getInstantFeedback } from '../services/api';
import type { FullReport, FinancialChartData } from '../services/api';
import * as echarts from 'echarts';

const props = defineProps<{
  reportData: FullReport;
  keyQuestions: string[];
}>();

const reportContentEl = ref<HTMLElement | null>(null);
const financialChartEl = ref<HTMLElement[] | null>(null);
const feedbackText = ref('');
const isFeedbackLoading = ref(false);
const feedbackResponse = ref('');

const analysisContext = computed(() => {
  return props.reportData.report_sections
    .map(s => `Section: ${s.section_title}\nContent: ${s.content}`)
    .join('\n\n');
});

const handleFeedbackSubmit = async () => {
  if (!feedbackText.value.trim()) {
    ElMessage.warning('Please enter some text for feedback.');
    return;
  }
  isFeedbackLoading.value = true;
  feedbackResponse.value = '';
  try {
    const response = await getInstantFeedback(analysisContext.value, feedbackText.value);
    feedbackResponse.value = response;
  } catch (error: any) {
    ElMessage.error(error.message || 'Failed to get feedback.');
  } finally {
    isFeedbackLoading.value = false;
  }
};

const scrollToSection = (sectionTitle: string) => {
  const sectionEl = document.getElementById(`section-${sectionTitle}`);
  if (sectionEl) {
    sectionEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

const initFinancialChart = (chartData?: FinancialChartData) => {
  if (financialChartEl.value && financialChartEl.value[0] && chartData) {
    const chart = echarts.init(financialChartEl.value[0]);
    const option = {
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(0,0,0,0.7)', borderColor: '#333', textStyle: { color: '#fff' } },
      legend: { data: ['Revenue', 'Profit'], textStyle: { color: '#ccc' }, top: 'bottom' },
      xAxis: { type: 'category', data: chartData.years.map(String), axisLine: { lineStyle: { color: '#888' } } },
      yAxis: { type: 'value', name: 'in Millions USD', axisLine: { lineStyle: { color: '#888' } }, splitLine: { lineStyle: { color: '#444' } } },
      series: [
        { name: 'Revenue', type: 'bar', data: chartData.revenues, itemStyle: { color: '#764ba2' } },
        { name: 'Profit', type: 'line', data: chartData.profits, itemStyle: { color: '#FF8E53' }, smooth: true }
      ],
      grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true }
    };
    chart.setOption(option);
  }
};

onMounted(() => {
  // Initial render
  nextTick(() => {
     initFinancialChart(props.reportData.financial_chart_data);
  });
});

// Watch for data changes if the component is reused
watch(() => props.reportData, (newData) => {
  nextTick(() => {
    initFinancialChart(newData.financial_chart_data);
  });
}, { deep: true });
</script>

<style scoped>
.dashboard-container {
  display: grid;
  grid-template-columns: 250px 1fr 350px;
  height: 100vh;
  overflow: hidden;
  gap: 1rem;
  padding: 1rem;
  background-color: #1a1a2e;
}

.sidebar, .report-content, .assistant-panel {
  overflow-y: auto;
  height: calc(100vh - 2rem);
}

/* Sidebar */
.sidebar {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 15px;
  padding: 1.5rem;
}
.sidebar-header h3 {
  margin: 0 0 1.5rem 0;
  font-weight: 600;
  color: #e0e0e0;
}
.outline-nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.outline-nav li a {
  display: block;
  padding: 0.75rem 1rem;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  border-radius: 8px;
  transition: background-color 0.3s, color 0.3s;
}
.outline-nav li a:hover {
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
}

/* Report Content */
.report-content {
  padding: 0 1.5rem;
}
.report-header {
  text-align: center;
  margin-bottom: 2rem;
}
.report-header h1 {
  margin: 0;
  font-size: 2.2rem;
}
.report-section {
  margin-bottom: 2rem;
}
.report-section h2 {
  font-size: 1.6rem;
  margin-bottom: 1rem;
  border-bottom: 2px solid #FF8E53;
  padding-bottom: 0.5rem;
}
.report-section p {
  line-height: 1.7;
  white-space: pre-wrap;
}
.data-source {
  text-align: right;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 1rem;
}
.chart-container {
  width: 100%;
  height: 400px;
}

/* Assistant Panel */
.assistant-panel {
  background: rgba(0, 0, 0, 0.1);
  border-radius: 15px;
  padding: 1.5rem;
}
.assistant-header h3 {
  margin: 0 0 1.5rem 0;
  font-weight: 600;
  color: #e0e0e0;
}
.questions-list {
  padding-left: 1.2rem;
  line-height: 1.8;
}
.feedback-response {
  margin-top: 1rem;
  padding: 0.75rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 0.9rem;
}
</style>
