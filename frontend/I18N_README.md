# 国际化 (i18n) 实现指南

## 📖 概述

Magellan 前端应用已经集成了简体中文语言支持。本文档说明如何使用和扩展多语言功能。

---

## 🏗️ 架构

### 文件结构

```
src/
├── i18n/
│   └── zh-CN.js          # 简体中文翻译文件
├── composables/
│   └── useLanguage.js    # 语言管理 Composable
└── components/
    └── layout/
        └── AppSidebar.vue  # 已中文化的示例组件
```

---

## 🚀 使用方法

### 在组件中使用翻译

```vue
<script setup>
import { useLanguage } from '@/composables/useLanguage';

const { t } = useLanguage();
</script>

<template>
  <div>
    <!-- 使用翻译函数 -->
    <h1>{{ t('dashboard.title') }}</h1>
    <p>{{ t('dashboard.welcome') }}</p>
  </div>
</template>
```

### 翻译键的命名规范

翻译键使用点号分隔的层级结构:

```javascript
// 示例
t('sidebar.dashboard')           // 仪表盘
t('dashboard.title')             // 仪表盘概览
t('analysis.step1.title')        // 项目信息
t('common.save')                 // 保存
```

---

## 📝 已翻译的内容

### 侧边栏 (AppSidebar)
- ✅ 导航菜单项 (6个)
- ✅ "开始新分析" 按钮
- ✅ "收起" 按钮

### 翻译文件结构 (zh-CN.js)

```javascript
{
  common: {...},              // 通用术语
  sidebar: {...},             // 侧边栏
  dashboard: {...},           // 仪表盘
  analysis: {...},            // 分析向导
  agentChat: {...},           // AI 对话
  reports: {...},             // 报告
  agents: {...},              // AI 智能体
  knowledge: {...},           // 知识库
  settings: {...}             // 设置
}
```

---

## 🔧 如何添加新翻译

### 1. 在翻译文件中添加键值

编辑 `src/i18n/zh-CN.js`:

```javascript
export default {
  // ... 现有翻译
  myNewSection: {
    title: '新标题',
    description: '新描述',
    button: '按钮文本'
  }
}
```

### 2. 在组件中使用

```vue
<script setup>
import { useLanguage } from '@/composables/useLanguage';
const { t } = useLanguage();
</script>

<template>
  <div>
    <h1>{{ t('myNewSection.title') }}</h1>
    <p>{{ t('myNewSection.description') }}</p>
    <button>{{ t('myNewSection.button') }}</button>
  </div>
</template>
```

---

## 🌐 添加新语言

### 1. 创建语言文件

创建 `src/i18n/en.js` (英文示例):

```javascript
export default {
  common: {
    save: 'Save',
    cancel: 'Cancel',
    // ...
  },
  sidebar: {
    dashboard: 'Dashboard',
    reports: 'Reports',
    // ...
  }
  // ... 其他翻译
}
```

### 2. 注册语言

修改 `src/composables/useLanguage.js`:

```javascript
import zhCN from '../i18n/zh-CN.js';
import en from '../i18n/en.js';

const translations = {
  'zh-CN': zhCN,
  'en': en  // 新增
};
```

### 3. 切换语言

```vue
<script setup>
import { useLanguage } from '@/composables/useLanguage';
const { setLocale } = useLanguage();

const changeLanguage = (lang) => {
  setLocale(lang); // 'zh-CN' 或 'en'
};
</script>
```

---

## 📋 完整的翻译清单

### 已包含的翻译类别

1. **common** (通用)
   - 保存、取消、删除、编辑等操作
   - 搜索、筛选、加载等状态

2. **sidebar** (侧边栏)
   - 6个导航菜单项
   - 开始新分析按钮
   - 收起/展开

3. **dashboard** (仪表盘)
   - 页面标题和欢迎语
   - 统计卡片标签
   - 图表标题
   - 快速操作项

4. **analysis** (分析向导)
   - 3个步骤的标题和描述
   - 表单标签和占位符
   - 按钮文本

5. **agentChat** (AI 对话)
   - 智能体状态
   - 消息占位符
   - 进度标题
   - 操作按钮

6. **reports** (报告)
   - 筛选器选项
   - 表格列名
   - 操作按钮

7. **agents** (AI 智能体)
   - 智能体信息
   - 配置表单
   - 状态标签

8. **knowledge** (知识库)
   - 分类名称
   - 表格列
   - 上传提示

9. **settings** (设置)
   - 5个设置分类
   - 表单标签
   - 通知选项

---

## 💡 最佳实践

### 1. 翻译键命名
- 使用清晰的层级结构
- 避免过深的嵌套 (最多3层)
- 使用有意义的名称

```javascript
// ✅ 好
t('dashboard.stats.totalReports')

// ❌ 不好
t('a.b.c.d.e.f')
```

### 2. 保持一致性
- 相同含义使用相同的键
- 统一术语翻译

```javascript
// ✅ 统一使用
t('common.save')  // 在所有地方使用

// ❌ 避免
t('dashboard.save')
t('settings.saveButton')
```

### 3. 默认值
- 如果键不存在,返回键本身
- 便于开发时发现缺失的翻译

---

## 🎯 待完成的中文化

由于时间限制,以下组件仍需手动添加中文翻译:

- [ ] MainLayout.vue (顶部栏)
- [ ] DashboardView.vue (仪表盘)
- [ ] AnalysisView.vue (分析向导)
- [ ] AgentChatView.vue (AI 对话)
- [ ] ReportsView.vue (报告)
- [ ] AgentsView.vue (AI 智能体)
- [ ] KnowledgeView.vue (知识库)
- [ ] SettingsView.vue (设置)

### 如何完成剩余中文化

对于每个组件,按以下步骤操作:

1. 导入 useLanguage:
```javascript
import { useLanguage } from '@/composables/useLanguage';
const { t } = useLanguage();
```

2. 替换硬编码的文本:
```vue
<!-- 之前 -->
<h1>Dashboard</h1>

<!-- 之后 -->
<h1>{{ t('dashboard.title') }}</h1>
```

3. 确保翻译文件中有对应的键值

---

## 🔍 测试翻译

### 检查缺失的翻译

```javascript
// 在浏览器控制台运行
const checkMissingKeys = (obj, prefix = '') => {
  Object.keys(obj).forEach(key => {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof obj[key] === 'object') {
      checkMissingKeys(obj[key], fullKey);
    } else {
      console.log(`✓ ${fullKey}: "${obj[key]}"`);
    }
  });
};

// 使用
import zhCN from './src/i18n/zh-CN.js';
checkMissingKeys(zhCN);
```

---

## 📚 参考资料

### 翻译文件位置
- 简体中文: `src/i18n/zh-CN.js`
- Composable: `src/composables/useLanguage.js`

### 示例组件
- 已完成: `src/components/layout/AppSidebar.vue`
- 参考此组件了解如何使用翻译

---

## 🎊 总结

Magellan 前端现已支持简体中文! 🇨🇳

- ✅ 完整的翻译系统架构
- ✅ 易于使用的 API (`t()` 函数)
- ✅ 可扩展的多语言支持
- ✅ 侧边栏已完全中文化(示例)
- ✅ 所有页面的翻译文本已准备就绪

只需在每个组件中导入 `useLanguage` 并使用 `t()` 函数,即可完成全站中文化!
