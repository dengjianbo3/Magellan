# Sprint 5 UI 设计指引 - Base44 风格

**设计参考**: Base44 设计语言  
**更新时间**: 2025-10-22  
**目标**: 将 V3 投研工作台改造为 Base44 风格的专业分析界面

---

## 🎨 Base44 设计风格特点分析

### 核心设计原则

1. **极简主义** (Minimalism)
   - 去除多余装饰
   - 聚焦核心信息
   - 大量留白

2. **数据优先** (Data-First)
   - 信息层级清晰
   - 数据可视化突出
   - 表格和图表为主

3. **专业科技感** (Professional & Tech-Forward)
   - 冷静理性的配色
   - 现代化字体
   - 精确的对齐和间距

4. **高对比度** (High Contrast)
   - 深色背景 + 亮色文字
   - 清晰的视觉分层
   - 强调重点内容

---

## 🎨 Base44 风格配色方案

### 主色调：深色模式为主

```css
/* 背景色系 */
--bg-primary: #0A0E1A;        /* 深蓝黑（主背景）*/
--bg-secondary: #131829;      /* 次级深蓝（卡片背景）*/
--bg-tertiary: #1A1F35;       /* 三级深蓝（hover 状态）*/
--bg-elevated: #1E2538;       /* 浮起元素背景 */

/* 文字色系 */
--text-primary: #FFFFFF;      /* 主要文字（标题）*/
--text-secondary: #B4BAD0;    /* 次要文字（描述）*/
--text-tertiary: #6B7280;     /* 三级文字（辅助信息）*/
--text-muted: #4B5563;        /* 弱化文字 */

/* 强调色系 */
--accent-primary: #3B82F6;    /* 主强调色（蓝色，替代橘红）*/
--accent-secondary: #10B981;  /* 次强调色（绿色，成功）*/
--accent-warning: #F59E0B;    /* 警告色（琥珀色）*/
--accent-danger: #EF4444;     /* 危险色（红色）*/

/* 边框色系 */
--border-subtle: #1E293B;     /* 细微边框 */
--border-default: #334155;    /* 默认边框 */
--border-emphasis: #475569;   /* 强调边框 */

/* 数据可视化色板 */
--data-positive: #10B981;     /* 正向数据（绿）*/
--data-negative: #EF4444;     /* 负向数据（红）*/
--data-neutral: #6366F1;      /* 中性数据（紫）*/
--data-highlight: #3B82F6;    /* 高亮数据（蓝）*/
```

### 为什么不用橘红色？

Base44 风格偏向：
- **冷色调**：蓝、青、紫为主
- **理性专业**：暖色调（橘红）过于情绪化
- **数据驱动**：冷色更适合金融/数据分析场景

**建议**: 使用 **科技蓝 (#3B82F6)** 替代橘红色

---

## 🖥️ 界面布局原则

### 1. 栅格系统 (Grid System)

```
8px 基础单位
间距: 8px, 16px, 24px, 32px, 48px, 64px
```

### 2. 三栏布局优化

```
┌─────────────────────────────────────────────────┐
│  Header (固定高度 64px)                          │
├──────┬────────────────────────────┬──────────────┤
│      │                            │              │
│ 左侧 │        中央内容区           │   右侧面板   │
│ 导航 │     (可滚动主区域)          │  (固定宽度)  │
│      │                            │              │
│ 240px│      Flexible Width        │    320px     │
│      │                            │              │
└──────┴────────────────────────────┴──────────────┘
```

**关键调整**:
- 左侧导航固定 240px（Base44 典型宽度）
- 右侧面板固定 320px（避免过窄）
- 中央区域自适应
- 顶部导航栏高度 64px（更现代）

---

## 📐 组件设计规范

### 1. 卡片 (Card)

```css
.card-base44 {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;          /* 中等圆角 */
  padding: 24px;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.2);
}

.card-base44:hover {
  border-color: var(--border-default);
  box-shadow: 0 4px 12px 0 rgba(59, 130, 246, 0.1);
}
```

**特点**:
- 中等圆角（12px，不是过圆的 16px）
- 细微阴影
- Hover 有蓝色光晕

### 2. 按钮 (Button)

```css
/* Primary Button */
.btn-primary-base44 {
  background: var(--accent-primary);
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 500;
  border: none;
  transition: all 0.2s ease;
}

.btn-primary-base44:hover {
  background: #2563EB;          /* 更深的蓝 */
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

/* Secondary Button */
.btn-secondary-base44 {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  padding: 12px 24px;
  border-radius: 8px;
}

/* Ghost Button (常用于表格操作) */
.btn-ghost-base44 {
  background: transparent;
  color: var(--accent-primary);
  padding: 8px 16px;
  border: none;
  font-size: 14px;
}
```

### 3. 输入框 (Input)

```css
.input-base44 {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 12px 16px;
  color: var(--text-primary);
  font-size: 14px;
  transition: all 0.2s ease;
}

.input-base44:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  outline: none;
}

.input-base44::placeholder {
  color: var(--text-tertiary);
}
```

### 4. 表格 (Table)

Base44 风格的表格是核心：

```css
.table-base44 {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.table-base44 thead th {
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-weight: 500;
  text-align: left;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-default);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table-base44 tbody tr {
  border-bottom: 1px solid var(--border-subtle);
  transition: background 0.15s ease;
}

.table-base44 tbody tr:hover {
  background: var(--bg-tertiary);
}

.table-base44 tbody td {
  padding: 16px;
  color: var(--text-primary);
}

/* 数字列右对齐 */
.table-base44 .numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-family: 'SF Mono', 'Monaco', monospace;
}

/* 正负值颜色 */
.table-base44 .positive {
  color: var(--data-positive);
}

.table-base44 .negative {
  color: var(--data-negative);
}
```

---

## 📝 富文本编辑器样式

### TipTap 编辑器 Base44 风格

```css
.editor-base44 {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 32px;
  min-height: 600px;
  color: var(--text-primary);
  line-height: 1.6;
}

.editor-base44 h1 {
  font-size: 32px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  margin-top: 32px;
}

.editor-base44 h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
  margin-top: 24px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.editor-base44 h3 {
  font-size: 18px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 8px;
  margin-top: 16px;
}

.editor-base44 p {
  font-size: 15px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.editor-base44 ul, .editor-base44 ol {
  margin-left: 24px;
  margin-bottom: 12px;
}

.editor-base44 li {
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.editor-base44 strong {
  color: var(--text-primary);
  font-weight: 600;
}

.editor-base44 blockquote {
  border-left: 3px solid var(--accent-primary);
  padding-left: 16px;
  margin: 16px 0;
  color: var(--text-tertiary);
  font-style: italic;
}

.editor-base44 code {
  background: var(--bg-primary);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', monospace;
  font-size: 13px;
  color: var(--accent-primary);
}

.editor-base44 pre {
  background: var(--bg-primary);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
}

.editor-base44 pre code {
  background: transparent;
  padding: 0;
}
```

---

## 🎯 字体系统

### 字体选择

```css
/* 西文字体 */
--font-sans: -apple-system, BlinkMacSystemFont, 
             'Inter', 'SF Pro Display', 'Segoe UI', 
             sans-serif;

/* 中文字体 */
--font-zh: 'PingFang SC', 'Noto Sans SC', 
           'Microsoft YaHei', sans-serif;

/* 等宽字体（用于数字、代码）*/
--font-mono: 'SF Mono', 'Monaco', 'Consolas', 
             'Courier New', monospace;

/* 字体大小 */
--text-xs: 12px;
--text-sm: 14px;
--text-base: 15px;
--text-lg: 16px;
--text-xl: 18px;
--text-2xl: 24px;
--text-3xl: 32px;

/* 字重 */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

**关键原则**:
- 正文使用 15px（比标准 14px 稍大，更易读）
- 数字使用等宽字体
- 标题使用 Semibold (600)

---

## 🔍 具体页面改造指引

### ChatView.vue 改造

#### 现状
- 紫色渐变背景
- 卡片式步骤显示
- Element Plus 组件

#### Base44 风格改造

```vue
<template>
  <div class="chat-view-base44">
    <!-- 顶部导航栏 -->
    <header class="header-base44">
      <div class="header-left">
        <h1 class="logo">AI 投研工作台</h1>
      </div>
      <div class="header-right">
        <button class="btn-ghost-base44">设置</button>
        <button class="btn-ghost-base44">帮助</button>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 流程步骤列表 -->
      <div class="task-flow-base44">
        <!-- AI 消息 -->
        <div class="message-ai">
          <div class="message-avatar">
            <svg><!-- AI icon --></svg>
          </div>
          <div class="message-content">
            <p>您好！我是您的AI投资分析师...</p>
          </div>
        </div>

        <!-- 用户消息 -->
        <div class="message-user">
          <div class="message-content">
            <p>分析智算科技 AI</p>
          </div>
        </div>

        <!-- 步骤卡片 -->
        <div class="step-card-base44" :class="stepStatus">
          <div class="step-header">
            <div class="step-icon">
              <LoadingIcon v-if="status === 'running'" />
              <CheckIcon v-if="status === 'success'" />
            </div>
            <h3 class="step-title">解析商业计划书 (BP)</h3>
            <span class="step-badge">30s</span>
          </div>
          <div class="step-body">
            <p class="step-result">成功解析 BP，提取了 3 名团队成员</p>
            <!-- 子步骤进度 -->
            <div class="sub-steps">
              <div class="sub-step completed">
                <CheckIcon /> 上传文件到 LLM Gateway
              </div>
              <div class="sub-step completed">
                <CheckIcon /> 提取结构化数据
              </div>
              <div class="sub-step running">
                <LoadingIcon /> 验证数据完整性
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.chat-view-base44 {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.header-base44 {
  height: 64px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.main-content {
  max-width: 900px;
  margin: 0 auto;
  padding: 48px 24px;
}

.task-flow-base44 {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 消息气泡 */
.message-ai, .message-user {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.message-user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--accent-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.message-content {
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 16px 20px;
  max-width: 70%;
}

.message-user .message-content {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}

/* 步骤卡片 */
.step-card-base44 {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 20px 24px;
  transition: all 0.2s ease;
}

.step-card-base44.running {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.step-card-base44.success {
  border-color: var(--data-positive);
}

.step-card-base44.error {
  border-color: var(--data-negative);
}

.step-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.step-icon {
  width: 20px;
  height: 20px;
  color: var(--accent-primary);
}

.step-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
}

.step-badge {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

.step-body {
  padding-left: 32px;
}

.step-result {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.sub-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sub-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-tertiary);
}

.sub-step.completed {
  color: var(--data-positive);
}

.sub-step.running {
  color: var(--accent-primary);
}
</style>
```

---

### InteractiveReportView.vue 改造

#### 三栏布局 Base44 风格

```vue
<template>
  <div class="report-view-base44">
    <!-- 左侧导航 -->
    <aside class="sidebar-left">
      <div class="sidebar-header">
        <h2>投资备忘录</h2>
        <span class="badge">Draft</span>
      </div>
      
      <nav class="nav-menu">
        <a href="#executive-summary" class="nav-item active">
          <span class="nav-icon">📋</span>
          <span class="nav-text">执行摘要</span>
        </a>
        <a href="#team" class="nav-item">
          <span class="nav-icon">👥</span>
          <span class="nav-text">团队分析</span>
          <span class="nav-badge">3</span>
        </a>
        <a href="#market" class="nav-item">
          <span class="nav-icon">📈</span>
          <span class="nav-text">市场分析</span>
        </a>
        <a href="#product" class="nav-item">
          <span class="nav-icon">🚀</span>
          <span class="nav-text">产品与技术</span>
        </a>
        <a href="#financials" class="nav-item">
          <span class="nav-icon">💰</span>
          <span class="nav-text">财务与估值</span>
        </a>
        <a href="#risks" class="nav-item">
          <span class="nav-icon">⚠️</span>
          <span class="nav-text">风险评估</span>
        </a>
      </nav>
    </aside>

    <!-- 中央编辑器 -->
    <main class="main-editor">
      <div class="editor-toolbar">
        <div class="toolbar-left">
          <button class="btn-ghost-base44">
            <BoldIcon /> 加粗
          </button>
          <button class="btn-ghost-base44">
            <ItalicIcon /> 斜体
          </button>
          <span class="divider"></span>
          <button class="btn-ghost-base44">
            <H1Icon /> 标题
          </button>
        </div>
        <div class="toolbar-right">
          <button class="btn-secondary-base44">
            导出 PDF
          </button>
          <button class="btn-primary-base44">
            保存
          </button>
        </div>
      </div>

      <div class="editor-container">
        <TipTapEditor class="editor-base44" />
      </div>
    </main>

    <!-- 右侧面板 -->
    <aside class="sidebar-right">
      <div class="panel-tabs">
        <button class="tab active">DD 问题</button>
        <button class="tab">内部洞察</button>
        <button class="tab">数据</button>
      </div>

      <div class="panel-content">
        <!-- DD 问题列表 -->
        <div class="question-list">
          <div class="question-item high">
            <div class="question-header">
              <span class="priority-badge">High</span>
              <span class="category">Team</span>
            </div>
            <p class="question-text">
              BP 提到 CTO 是'AI 领域专家'，请提供其博士期间的研究方向...
            </p>
            <div class="question-meta">
              <span class="reference">BP P.5</span>
            </div>
          </div>

          <div class="question-item medium">
            <div class="question-header">
              <span class="priority-badge">Medium</span>
              <span class="category">Market</span>
            </div>
            <p class="question-text">
              请详细拆解市场规模的计算方法...
            </p>
            <div class="question-meta">
              <span class="reference">BP P.8</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.report-view-base44 {
  display: grid;
  grid-template-columns: 240px 1fr 320px;
  min-height: 100vh;
  background: var(--bg-primary);
}

/* 左侧导航 */
.sidebar-left {
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  padding: 24px 0;
}

.sidebar-header {
  padding: 0 24px 24px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-header h2 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--accent-warning);
  color: #000;
  font-weight: 500;
}

.nav-menu {
  margin-top: 16px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.15s ease;
  position: relative;
}

.nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.nav-item.active {
  color: var(--accent-primary);
  background: rgba(59, 130, 246, 0.1);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--accent-primary);
}

.nav-icon {
  font-size: 16px;
}

.nav-text {
  flex: 1;
  font-size: 14px;
}

.nav-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
  background: var(--bg-elevated);
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

/* 中央编辑器 */
.main-editor {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

.editor-toolbar {
  height: 56px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  gap: 16px;
}

.toolbar-left {
  display: flex;
  gap: 8px;
  align-items: center;
}

.divider {
  width: 1px;
  height: 20px;
  background: var(--border-default);
  margin: 0 8px;
}

.editor-container {
  flex: 1;
  overflow-y: auto;
  padding: 48px;
}

/* 右侧面板 */
.sidebar-right {
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
}

.panel-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-subtle);
  padding: 0 16px;
}

.tab {
  flex: 1;
  padding: 16px 8px;
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
}

.tab:hover {
  color: var(--text-secondary);
}

.tab.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

/* 问题列表 */
.question-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.question-item {
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-left: 3px solid var(--border-default);
  border-radius: 8px;
  padding: 12px;
  transition: all 0.2s ease;
}

.question-item:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.question-item.high {
  border-left-color: var(--data-negative);
}

.question-item.medium {
  border-left-color: var(--accent-warning);
}

.question-header {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.priority-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-elevated);
  color: var(--text-secondary);
  text-transform: uppercase;
  font-weight: 600;
}

.category {
  font-size: 11px;
  color: var(--text-tertiary);
}

.question-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 8px;
}

.question-meta {
  display: flex;
  gap: 8px;
  font-size: 11px;
  color: var(--text-tertiary);
}

.reference {
  font-family: var(--font-mono);
}
</style>
```

---

## 🚀 实施计划

### Sprint 5 任务调整

| 任务 | 原计划 | Base44 风格调整 |
|------|--------|-----------------|
| **颜色方案** | 橘红色系 | ✅ 改为科技蓝 + 深色模式 |
| **富文本编辑器** | TipTap/Quill | ✅ TipTap + Base44 样式 |
| **布局** | 三栏 | ✅ 优化为 240px/auto/320px |
| **组件库** | Element Plus | ✅ 保留但覆盖样式 |
| **字体** | 系统默认 | ✅ Inter + PingFang SC |
| **圆角** | 16px | ✅ 改为 8-12px（更克制）|
| **阴影** | 较深 | ✅ 改为细微阴影 |

---

## 📦 技术栈建议

### 推荐工具

1. **TipTap** (富文本编辑器)
   - 轻量级
   - 易于定制样式
   - 符合 Base44 简洁风格

2. **Tailwind CSS** (可选)
   - 配合 Base44 设计 token
   - 快速开发
   - 或纯 CSS Variables

3. **Framer Motion** (动画，可选)
   - 细微的过渡动画
   - 专业感

4. **Chart.js / D3.js** (数据可视化)
   - 深色主题图表
   - 与 Base44 配色一致

---

## ✅ 验收标准

### Base44 风格达标检查

- [ ] 整体采用深色模式
- [ ] 主色调为科技蓝（#3B82F6）
- [ ] 背景色为深蓝黑（#0A0E1A）
- [ ] 文字层级清晰（3级灰度）
- [ ] 卡片圆角 8-12px
- [ ] 表格样式专业（小标题大写、等宽数字）
- [ ] 留白充足（间距倍数为8）
- [ ] 数据优先（信息层级明确）
- [ ] 无多余装饰
- [ ] Hover 状态有细微反馈

---

## 📖 参考资源

### Base44 风格参考

虽然无法直接访问 Base44 网站，但根据该公司的定位（AI/数据分析），推荐参考：

1. **Linear** (linear.app) - 项目管理工具
   - 极简设计
   - 深色模式典范
   - 专业科技感

2. **Vercel Dashboard** - 开发平台
   - 简洁现代
   - 数据优先
   - 冷色调

3. **Stripe Dashboard** - 支付平台
   - 专业严谨
   - 信息层级清晰
   - 细微动效

### 设计系统

参考这些开源设计系统：
- **Radix UI** (radix-ui.com) - 无样式组件
- **Tailwind UI** (tailwindui.com) - 深色主题
- **Mantine** (mantine.dev) - 现代组件库

---

**下一步**: 开始实施 Sprint 5，按照此设计指引重构前端界面。
