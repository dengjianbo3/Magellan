<!-- src/views/InteractiveReportView_v3.vue -->
<!-- V3 投资备忘录工作台 - Base44 风格 -->
<template>
  <div class="im-workspace-base44">
    <!-- 左侧导航 -->
    <aside class="sidebar-left">
      <div class="sidebar-header">
        <h2 class="sidebar-title">投资备忘录</h2>
        <span class="badge-base44 badge-warning">Draft</span>
      </div>
      
      <nav class="nav-menu">
        <a 
          v-for="section in imSections" 
          :key="section.id"
          :href="`#${section.id}`"
          @click.prevent="scrollToSection(section.id)"
          :class="['nav-item-base44', { active: activeSection === section.id }]"
        >
          <span class="nav-icon">{{ section.icon }}</span>
          <span class="nav-text">{{ section.title }}</span>
          <span v-if="section.count" class="nav-badge">{{ section.count }}</span>
        </a>
      </nav>

      <div class="sidebar-footer">
        <button class="btn-base44 btn-secondary btn-sm" style="width: 100%;">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width: 16px; height: 16px;">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
          </svg>
          偏好设置
        </button>
      </div>
    </aside>

    <!-- 中央编辑器 -->
    <main class="main-editor">
      <div class="editor-toolbar">
        <div class="toolbar-left">
          <button class="btn-base44 btn-ghost btn-sm" @click="execCommand('bold')" title="加粗">
            <strong>B</strong>
          </button>
          <button class="btn-base44 btn-ghost btn-sm" @click="execCommand('italic')" title="斜体">
            <em>I</em>
          </button>
          <button class="btn-base44 btn-ghost btn-sm" @click="execCommand('underline')" title="下划线">
            <u>U</u>
          </button>
          <span class="divider-vertical"></span>
          <button class="btn-base44 btn-ghost btn-sm" @click="execCommand('heading1')" title="一级标题">
            H1
          </button>
          <button class="btn-base44 btn-ghost btn-sm" @click="execCommand('heading2')" title="二级标题">
            H2
          </button>
          <span class="divider-vertical"></span>
          <button class="btn-base44 btn-ghost btn-sm" @click="execCommand('bulletList')" title="无序列表">
            •
          </button>
          <button class="btn-base44 btn-ghost btn-sm" @click="execCommand('orderedList')" title="有序列表">
            1.
          </button>
        </div>
        <div class="toolbar-right">
          <button 
            class="btn-base44 btn-ghost btn-sm" 
            @click="requestValuationAnalysis" 
            :disabled="isGeneratingValuation || !sessionId"
            title="生成估值与退出分析"
          >
            <span v-if="isGeneratingValuation">💰 生成中...</span>
            <span v-else>💰 估值分析</span>
          </button>
          <button class="btn-base44 btn-secondary btn-sm" @click="exportToWord" :disabled="isExporting">
            <svg v-if="!isExporting" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width: 16px; height: 16px;">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            <span v-if="isExporting">导出中...</span>
            <span v-else>导出 Word</span>
          </button>
          <button class="btn-base44 btn-primary btn-sm" @click="saveIM">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width: 16px; height: 16px;">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            保存
          </button>
        </div>
      </div>

      <div class="editor-container" ref="editorContainer">
        <!-- 使用 contenteditable 作为简单的富文本编辑器 -->
        <!-- 生产环境应替换为 TipTap -->
        <div 
          class="editor-base44"
          contenteditable="true"
          @input="onEditorInput"
          v-html="editorContent"
        ></div>
      </div>
    </main>

    <!-- 右侧面板 -->
    <aside class="sidebar-right">
      <div class="panel-tabs">
        <button 
          :class="['tab-base44', { active: activeTab === 'questions' }]"
          @click="activeTab = 'questions'"
        >
          DD 问题
        </button>
        <button 
          :class="['tab-base44', { active: activeTab === 'insights' }]"
          @click="activeTab = 'insights'"
        >
          内部洞察
        </button>
        <button 
          :class="['tab-base44', { active: activeTab === 'data' }]"
          @click="activeTab = 'data'"
        >
          数据
        </button>
      </div>

      <div class="panel-content">
        <!-- DD 问题列表 -->
        <div v-if="activeTab === 'questions'" class="question-list">
          <div 
            v-for="(question, index) in parsedQuestions" 
            :key="index"
            :class="['question-card', getPriorityClass(question.priority || 'Medium')]"
          >
            <div class="question-header">
              <span class="priority-badge">{{ question.priority || 'Medium' }}</span>
              <span class="category-tag">{{ question.category || 'General' }}</span>
            </div>
            <p class="question-text">{{ question.question || question }}</p>
            <div v-if="question.reasoning" class="question-reasoning">
              💡 {{ question.reasoning }}
            </div>
            <div class="question-meta">
              <span v-if="question.bp_reference" class="bp-reference">{{ question.bp_reference }}</span>
            </div>
          </div>
        </div>

        <!-- 内部洞察 -->
        <div v-if="activeTab === 'insights'" class="insights-list">
          <div v-if="isLoadingInsights" class="loading-state">
            <div class="loading-spinner" style="width: 24px; height: 24px; border: 3px solid var(--border-default); border-top-color: var(--accent-primary); border-radius: 50%;"></div>
            <p style="margin-top: 1rem; color: var(--text-tertiary);">加载中...</p>
          </div>
          
          <div v-else-if="insights.length === 0" class="empty-state">
            <div class="empty-icon">📂</div>
            <h4 class="empty-title">暂无相关洞察</h4>
            <p class="empty-description">系统未找到相关的历史项目记录</p>
          </div>
          
          <div v-else class="insight-cards">
            <div 
              v-for="(insight, index) in insights" 
              :key="index"
              class="insight-card"
            >
              <div class="insight-header">
                <span class="insight-source">{{ insight.metadata.source || '内部纪要' }}</span>
                <span class="insight-date">{{ insight.metadata.date || '历史记录' }}</span>
              </div>
              <p class="insight-content">{{ truncateText(insight.content, 200) }}</p>
              <div class="insight-footer">
                <span v-if="insight.metadata.project" class="insight-project">
                  📁 {{ insight.metadata.project }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 数据面板 -->
        <div v-if="activeTab === 'data'" class="data-panel">
          <div class="card-base44" style="margin-bottom: 1rem;">
            <div class="card-header">
              <h4 class="card-title">关键指标</h4>
            </div>
            <div class="card-body">
              <div class="metric-item">
                <span class="metric-label">融资金额</span>
                <span class="metric-value">3000万元</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">估值</span>
                <span class="metric-value">2亿元</span>
              </div>
              <div class="metric-item">
                <span class="metric-label">团队评分</span>
                <span class="metric-value text-success">7.5/10</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import type { FullReport } from '../services/api';
import { searchInternalInsights, type InsightResult, generateValuationAnalysis } from '../services/api';
import { exportIMAsWord } from '../utils/exportUtils';

interface DDQuestion {
  category?: string;
  question: string;
  reasoning?: string;
  priority?: string;
  bp_reference?: string;
}

const props = defineProps<{
  reportData: FullReport;
  keyQuestions: string[] | DDQuestion[];
  sessionId?: string;
}>();

// Helper functions for question parsing
const getPriority = (index: number): string => {
  if (index < 5) return 'High';
  if (index < 10) return 'Medium';
  return 'Low';
};

const getCategory = (index: number): string => {
  const categories = ['Team', 'Market', 'Product', 'Financial', 'Risk'];
  return categories[index % categories.length] || 'General';
};

// Parse questions - handle both string[] and DDQuestion[]
const parsedQuestions = computed(() => {
  if (!props.keyQuestions || props.keyQuestions.length === 0) {
    return [];
  }
  
  // Check if first item is an object (DDQuestion) or string
  if (typeof props.keyQuestions[0] === 'string') {
    // Convert strings to DDQuestion objects
    return (props.keyQuestions as string[]).map((q, index) => ({
      question: q,
      category: getCategory(index),
      priority: getPriority(index),
      bp_reference: `BP P.${(index % 10) + 1}`,
      reasoning: undefined
    }));
  }
  
  // Already DDQuestion objects
  return props.keyQuestions as DDQuestion[];
});

// IM 章节定义
const imSections = ref([
  { id: 'executive-summary', title: '执行摘要', icon: '📋' },
  { id: 'team', title: '团队分析', icon: '👥', count: 3 },
  { id: 'market', title: '市场分析', icon: '📈' },
  { id: 'product', title: '产品与技术', icon: '🚀' },
  { id: 'financials', title: '财务与估值', icon: '💰' },
  { id: 'risks', title: '风险评估', icon: '⚠️' },
  { id: 'dd-questions', title: 'DD 问题清单', icon: '❓', count: parsedQuestions.value.length }
]);

const activeSection = ref('executive-summary');
const activeTab = ref('questions');
const editorContent = ref('');
const editorContainer = ref<HTMLElement | null>(null);
const insights = ref<InsightResult[]>([]);
const isLoadingInsights = ref(false);
const isExporting = ref(false);
const isGeneratingValuation = ref(false);

// 初始化编辑器内容
onMounted(async () => {
  editorContent.value = generateInitialIMContent();
  
  // 加载内部洞察
  await loadInternalInsights();
});

// 加载内部洞察
const loadInternalInsights = async () => {
  isLoadingInsights.value = true;
  try {
    // 构建查询关键词（公司名 + 行业）
    const query = `${props.reportData.company_ticker} investment due diligence`;
    const response = await searchInternalInsights(query, 5);
    insights.value = response.results;
  } catch (error) {
    console.error('Failed to load insights:', error);
    insights.value = [];
  } finally {
    isLoadingInsights.value = false;
  }
};

const generateInitialIMContent = (): string => {
  const reportSections = props.reportData.report_sections || [];
  
  let html = `
    <h1 id="executive-summary">投资备忘录</h1>
    <div style="color: var(--text-tertiary); margin-bottom: 2rem;">
      <p><strong>公司名称:</strong> ${props.reportData.company_ticker}</p>
      <p><strong>分析日期:</strong> ${new Date().toLocaleDateString('zh-CN')}</p>
      <p><strong>分析师:</strong> AI Investment Agent V3</p>
    </div>

    <h2 id="executive-summary">一、执行摘要</h2>
    <p>${reportSections[0]?.content || '待补充执行摘要...'}</p>

    <h2 id="team">二、团队分析</h2>
    <p>${reportSections[1]?.content || '待补充团队分析...'}</p>
    <h3>核心优势</h3>
    <ul>
      <li>深厚的技术壁垒</li>
      <li>成熟的产品思维</li>
      <li>强大的销售能力</li>
    </ul>
    <h3>潜在担忧</h3>
    <ul>
      <li>销售团队单薄</li>
      <li>融资经验缺乏</li>
    </ul>

    <h2 id="market">三、市场分析</h2>
    <p>${reportSections[2]?.content || '待补充市场分析...'}</p>
    
    <h2 id="product">四、产品与技术</h2>
    <p>待补充产品与技术分析...</p>

    <h2 id="financials">五、财务与估值</h2>
    <p>待补充财务与估值分析...</p>

    <h2 id="risks">六、风险评估</h2>
    <p>待补充风险评估...</p>

    <h2 id="dd-questions">七、DD 问题清单</h2>
    <p>以下是需要与创始人确认的关键问题：</p>
    <ol>
      ${parsedQuestions.value.map(q => `<li><strong>[${q.category || 'General'}]</strong> ${q.question || q}</li>`).join('\n      ')}
    </ol>
  `;
  
  return html;
};

const scrollToSection = (sectionId: string) => {
  activeSection.value = sectionId;
  const element = document.getElementById(sectionId);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
};

const execCommand = (command: string) => {
  // 简化的命令执行（生产环境应使用 TipTap API）
  console.log('Execute command:', command);
  // TODO: 集成 TipTap API
};

const onEditorInput = (event: Event) => {
  const target = event.target as HTMLElement;
  editorContent.value = target.innerHTML;
};

const saveIM = () => {
  console.log('Saving IM...', editorContent.value);
  // TODO: 调用后端 API 保存
};

// 导出为 Word
const exportToWord = async () => {
  isExporting.value = true;
  try {
    await exportIMAsWord(editorContent.value, {
      fileName: `IM_${props.reportData.company_ticker}_${new Date().toISOString().split('T')[0]}.docx`,
      companyName: props.reportData.company_ticker,
      date: new Date().toLocaleDateString('zh-CN'),
    });
  } catch (error) {
    console.error('Export failed:', error);
    alert('导出失败，请稍后重试');
  } finally {
    isExporting.value = false;
  }
};

// 生成估值分析（Sprint 7）
const requestValuationAnalysis = async () => {
  if (!props.sessionId) {
    alert('无法生成估值分析：缺少 Session ID');
    return;
  }
  
  isGeneratingValuation.value = true;
  try {
    const result = await generateValuationAnalysis(props.sessionId);
    
    // 将估值章节追加到编辑器内容
    const valuationSection = result.im_section;
    editorContent.value += '\n\n' + valuationSection;
    
    // 滚动到估值章节
    setTimeout(() => {
      const valuationHeading = document.querySelector('#financials');
      if (valuationHeading) {
        valuationHeading.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
    
    console.log('Valuation analysis generated successfully');
  } catch (error) {
    console.error('Failed to generate valuation analysis:', error);
    alert('生成估值分析失败，请稍后重试');
  } finally {
    isGeneratingValuation.value = false;
  }
};

// Helper functions
const getPriorityClass = (priority: string): string => {
  switch (priority) {
    case 'High': return 'priority-high';
    case 'Low': return 'priority-low';
    default: return 'priority-medium';
  }
};

// Truncate text helper
const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};
</script>

<style scoped>
/* IM Workspace Base44 Style */

.im-workspace-base44 {
  display: grid;
  grid-template-columns: var(--sidebar-left-width) 1fr var(--sidebar-right-width);
  height: 100vh;
  background: var(--bg-primary);
  overflow: hidden;
}

/* ============================================
   Left Sidebar - 左侧导航
   ============================================ */

.sidebar-left {
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  padding: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.nav-menu {
  flex: 1;
  padding: var(--space-2) 0;
}

.sidebar-footer {
  padding: var(--space-3);
  border-top: 1px solid var(--border-subtle);
}

/* ============================================
   Main Editor - 中央编辑器
   ============================================ */

.main-editor {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  overflow: hidden;
}

.editor-toolbar {
  height: 56px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-3);
  gap: var(--space-2);
  flex-shrink: 0;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.divider-vertical {
  width: 1px;
  height: 20px;
  background: var(--border-default);
  margin: 0 0.5rem;
}

.editor-container {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6) var(--space-8);
}

.editor-base44 {
  max-width: 800px;
  margin: 0 auto;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  min-height: calc(100vh - 200px);
  color: var(--text-secondary);
  line-height: var(--leading-relaxed);
  outline: none;
  transition: border-color var(--transition-base);
}

.editor-base44:focus {
  border-color: var(--accent-primary);
  box-shadow: var(--shadow-glow);
}

/* Editor Content Styling */
.editor-base44 h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--text-primary);
  margin-bottom: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 2px solid var(--border-emphasis);
}

.editor-base44 h2 {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  margin-top: var(--space-6);
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-subtle);
}

.editor-base44 h3 {
  font-size: var(--text-xl);
  font-weight: var(--font-medium);
  color: var(--text-secondary);
  margin-top: var(--space-4);
  margin-bottom: var(--space-2);
}

.editor-base44 p {
  font-size: var(--text-base);
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
  line-height: var(--leading-relaxed);
}

.editor-base44 ul,
.editor-base44 ol {
  margin-left: var(--space-3);
  margin-bottom: var(--space-3);
  padding-left: var(--space-2);
}

.editor-base44 li {
  color: var(--text-secondary);
  margin-bottom: var(--space-1);
  line-height: var(--leading-normal);
}

.editor-base44 strong {
  color: var(--text-primary);
  font-weight: var(--font-semibold);
}

.editor-base44 em {
  font-style: italic;
  color: var(--text-secondary);
}

.editor-base44 blockquote {
  border-left: 3px solid var(--accent-primary);
  padding-left: var(--space-2);
  margin: var(--space-2) 0;
  color: var(--text-tertiary);
  font-style: italic;
}

.editor-base44 code {
  background: var(--bg-primary);
  padding: 0.125rem 0.375rem;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.875em;
  color: var(--accent-primary);
}

/* ============================================
   Right Sidebar - 右侧面板
   ============================================ */

.sidebar-right {
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-subtle);
  padding: 0 var(--space-2);
  flex-shrink: 0;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2);
}

/* Question List */
.question-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.question-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-2);
  transition: all var(--transition-base);
}

.question-card.priority-high {
  border-left: 3px solid #ef4444;
}

.question-card.priority-medium {
  border-left: 3px solid #f59e0b;
}

.question-card.priority-low {
  border-left: 3px solid #3b82f6;
}

.question-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.priority-badge {
  font-size: 11px;
  font-weight: var(--font-semibold);
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.priority-high .priority-badge {
  background: #ef4444;
  color: white;
}

.priority-medium .priority-badge {
  background: #f59e0b;
  color: white;
}

.priority-low .priority-badge {
  background: #3b82f6;
  color: white;
}

.category-tag {
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--bg-elevated);
  padding: 0.125rem 0.5rem;
  border-radius: var(--radius-sm);
}

.question-text {
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: var(--leading-normal);
  margin-bottom: var(--space-1);
  font-weight: var(--font-medium);
}

.question-reasoning {
  font-size: 12px;
  color: var(--text-tertiary);
  background: var(--bg-elevated);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  margin-top: var(--space-1);
  margin-bottom: var(--space-1);
  font-style: italic;
}

.question-meta {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-1);
}

.bp-reference {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

/* Insights List */
.insights-list {
  padding: var(--space-2);
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-6) var(--space-2);
}

.insight-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.insight-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--space-2);
  transition: all var(--transition-base);
  cursor: pointer;
}

.insight-card:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
}

.insight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-1);
}

.insight-source {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--accent-primary);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.insight-date {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.insight-content {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  line-height: var(--leading-normal);
  margin-bottom: var(--space-1);
}

.insight-footer {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-top: var(--space-1);
}

.insight-project {
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--bg-elevated);
  padding: 0.25rem 0.5rem;
  border-radius: var(--radius-sm);
}

/* Data Panel */
.data-panel {
  padding: var(--space-1);
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--border-subtle);
}

.metric-item:last-child {
  border-bottom: none;
}

.metric-label {
  font-size: var(--text-sm);
  color: var(--text-tertiary);
}

.metric-value {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--text-primary);
  font-family: var(--font-mono);
}
</style>
