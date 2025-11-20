# 当前问题记录

## 更新时间：2025-11-20

---

## 🔴 高优先级问题

### 1. 财务分析TypeError持续报错

**问题描述**：
- Agent `FinancialExpert` 分析时出现 `TypeError: string indices must be integers, not 'str'`
- 错误发生在尝试访问 `llm_response["choices"][0]` 时

**已完成的修复尝试**：
1. 在 `agent.py:234-272` 添加了 LLM响应格式的类型检查
2. 在 `agent.py:454-472` 添加了安全的content提取逻辑
3. 重启了 Docker 容器应用修复
4. 添加了详细的调试日志（🔍 DEBUG, ✅ Success, ⚠️ Warning标记）

**当前状态**：
- 代码修复已应用到容器
- 需要运行新的分析来查看详细日志
- 日志将显示 `llm_response` 的实际类型和内容

**下一步行动**：
- 运行行业研究分析，收集详细日志
- 根据日志确定 LLM Gateway 返回的实际格式
- 可能需要修改 LLM Gateway 或者进一步增强类型处理

**相关文件**：
- `backend/services/report_orchestrator/app/core/roundtable/agent.py`
- Lines: 234-272 (LLM调用), 454-472 (content提取)

---

## 🟡 中优先级问题

### 2. 分析结果卡片显示状态（待确认）

**问题描述**：
- 用户报告"分析内容的卡片状态明显有问题"
- 具体问题表现尚不清楚

**当前状态**：
- 已完成UI布局重构
- 移除了时间线面板
- 分析结果卡片现在显示在AI智能体状态右侧
- 需要用户测试后确认具体问题

**下一步行动**：
- 等待用户运行分析测试
- 根据反馈确定卡片显示的具体问题
- 调整样式或状态逻辑

**相关文件**：
- `frontend/src/components/analysis/AnalysisProgress.vue`
- `frontend/src/components/analysis/StepResultCard.vue`

---

## ✅ 已解决问题

### 1. "Unknown Project" 和 "分析中..." 不必要提示文本
**解决方案**：
- 修改了 `AnalysisProgress.vue:5-7`
- 当项目名为 "Unknown Project" 时不显示
- 移除了 "分析中... 系统正在处理实时市场数据。" 提示

### 2. 时间线面板重复显示
**解决方案**：
- 完全移除了时间线面板（lines 68-85）
- 移除了相关CSS样式
- 移除了 `timelineEvents` computed property

### 3. 布局调整 - 分析结果移到右侧
**解决方案**：
- 重构了 content-grid 布局
- 左侧：AI智能体状态
- 右侧：分析结果卡片（workflow steps）
- 保持双列布局

### 4. "查看完整报告" 按钮报错
**错误**：`Cannot read properties of undefined (reading 'push')`
**解决方案**：
- 修改了 `AnalysisWizardView.vue:226`
- 移除了重复的 `useRouter()` 调用
- 使用setup()作用域中已有的 `router` 引用

### 5. 分析卡在0%进度
**原因**：
- 缺少 `research_topic` 字段导致验证失败
- 错误消息被缓冲而未显示

**解决方案**：
- 修改 `industry_research_orchestrator.py:77-94` 自动生成 `research_topic`
- 修改 `analysisServiceV2.js:207-208` 将 'error' 添加到重要消息类型

### 6. Agent名称混合中英文显示
**原因**：
- 后端发送了i18n key而不是翻译后的文本
- 前端未检测和翻译这些key

**解决方案**：
- 在 `AnalysisProgress.vue:580-610` 添加i18n key检测和翻译
- 重写 `agents` computed 使用workflow数据（lines 404-439）
- 需要清除浏览器缓存以查看效果

---

## 🔍 需要监控的区域

### LLM Gateway响应格式
- 目前处理了 string 和 dict 两种格式
- 需要确认是否还有其他格式
- 详细日志已添加，等待真实数据

### WebSocket消息缓冲
- Stage 3实现了消息缓冲机制
- `workflow_start` 等早期消息会被缓存
- 组件mount后通过 `flushMessageBuffer()` 重放
- 需要确保所有重要消息类型都在缓冲列表中

### Agent状态同步
- Workflow步骤状态 vs Agent状态
- 确保两者正确映射和更新
- 图标、颜色、消息需要保持一致

---

## 📋 技术债务

### 前端
1. **硬编码的API URL**
   - `analysisServiceV2.js` 中 `API_BASE = 'http://localhost:8000'`
   - 应该使用环境变量

2. **Mock数据残留**
   - Quick judgment 结果包含 `is_mock: true`
   - 生产环境应该移除mock逻辑

3. **类型安全**
   - JavaScript项目缺少TypeScript类型检查
   - Props验证不够严格

### 后端
1. **Agent Registry完全迁移**
   - Phase 2已完成，但部分orchestrator可能还有遗留代码
   - 需要全面审查确保统一使用AgentRegistry

2. **错误处理标准化**
   - Agent错误处理需要更统一的格式
   - WebSocket错误消息格式需要规范化

3. **Mock数据标记**
   - `_synthesize_quick_judgment` 和 `_synthesize_final_report` 返回mock数据
   - 需要连接真实的LLM分析

---

## 🎯 下一步计划

### 短期（本周）
1. 解决财务分析TypeError（最高优先级）
2. 收集并分析LLM Gateway响应格式日志
3. 确认并修复分析结果卡片显示问题
4. 测试完整的分析流程

### 中期（下周）
1. 替换所有Mock数据为真实LLM分析
2. 完善错误处理和用户提示
3. 优化WebSocket重连机制
4. 添加分析进度持久化

### 长期
1. 迁移到TypeScript
2. 添加单元测试和集成测试
3. 性能优化和监控
4. 国际化(i18n)完善

---

## 📞 联系信息

**项目负责人**：待填写
**技术支持**：待填写
**文档更新**：每次重大问题解决后更新此文档
