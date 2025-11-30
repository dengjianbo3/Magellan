# Magellan 产品上线计划

**目标**: 达到可对外试用的产品质量标准
**创建日期**: 2025-11-28
**状态**: 规划中

---

## 一、当前状态评估

### ✅ 已完成
- [x] Phase 4: API Router 模块化迁移
- [x] Phase 7: Kafka 消息队列集成
- [x] Agent Registry 架构升级
- [x] 5个投资场景基础流程
- [x] WebSocket 实时通信
- [x] 前端 UI 框架 (Vue3 + TailwindCSS)
- [x] Docker 容器化部署

### ⚠️ 待优化
- [ ] Mock 数据替换为真实 LLM 分析
- [ ] 错误处理和用户提示完善
- [ ] API URL 环境变量化
- [ ] 测试覆盖率

---

## 二、上线前必须完成 (P0 - 阻塞上线)

### Sprint A: 核心功能修复 (预计 2-3 天)

#### A1. 移除 Mock 数据，接入真实 LLM ✅ (已完成 2025-11-28)
```
文件:
- backend/services/report_orchestrator/app/agents/report_synthesizer_agent.py
- backend/services/report_orchestrator/app/core/orchestrators/base_orchestrator.py

完成内容:
1. ✅ ReportSynthesizerAgent 添加 LLM 调用 (_call_llm_for_quick_synthesis, _call_llm_for_synthesis)
2. ✅ 快速模式和标准模式都支持 LLM 生成报告
3. ✅ 添加 fallback 机制 (LLM 失败时使用本地逻辑)
4. ✅ 修复 QuickJudgmentResult Pydantic 序列化问题
5. ✅ 测试验证: LLM 返回真实分析内容
```

#### A2. 完善错误处理 ✅ (已完成 2025-11-28)
```
文件:
- frontend/src/services/analysisServiceV2.js
- frontend/src/components/analysis/AnalysisProgress.vue
- frontend/src/i18n/zh-CN.js
- frontend/src/i18n/en.js

完成内容:
1. ✅ WebSocket 断连重试机制 (已有: 指数退避, 最多10次重试)
2. ✅ 心跳机制 (ping/pong, 30秒超时检测)
3. ✅ 连接状态 UI 显示 (reconnecting/error banner)
4. ✅ 用户友好的错误提示 (i18n: reconnecting, connectionLost, connectionRestored)
5. ✅ 连接状态变化通知 (oldState → newState)
```

#### A3. 修复已知 UI 问题 ✅ (已完成 2025-11-28)
```
完成内容:
1. [x] 场景选择图标显示 (已修复)
2. [x] 分析结果卡片状态显示 (StepResultCard组件已完善)
3. [x] 进度条准确性 (running状态计入50%进度, 完成时100%)
4. [x] 报告查看页面 (ReportsView已支持多种报告类型)
```

### Sprint B: 配置与环境 ✅ (已完成 2025-11-28)

#### B1. 环境变量配置 ✅
```
文件:
- frontend/src/config/api.js (新建: 集中API配置)
- frontend/.env.example (新建: 环境变量模板)
- 所有视图和服务文件

完成内容:
1. ✅ 创建 frontend/src/config/api.js - 集中管理API_BASE和WS_BASE
2. ✅ 所有API调用改用环境变量 (VITE_API_BASE, VITE_WS_BASE)
3. ✅ 更新的文件:
   - analysisServiceV2.js
   - uploadService.js
   - ddAnalysisService.js
   - ReportsView.vue
   - DashboardView.vue
   - KnowledgeView.vue
   - RoundtableView.vue
   - AgentChatView.vue
4. ✅ 创建 .env.example 模板
```

#### B2. 敏感信息清理 ✅
```
完成内容:
1. [x] 检查代码中的硬编码密钥 (已清理API URLs)
2. [x] 确保 .env 文件不被提交 (.gitignore已更新)
3. [x] 添加 .env.example 模板
```

---

## 三、上线前应该完成 (P1 - 影响体验)

### Sprint C: 用户体验优化 ✅ (已完成 2025-11-28)

#### C1. 分析流程优化 ✅
```
完成内容:
1. ✅ 添加分析进度持久化 (刷新页面可恢复)
   - AnalysisWizardView.vue: 添加 checkForActiveSessions(), recoverSession(), dismissRecovery()
   - 使用 sessionManager.js 管理 localStorage 持久化
   - 添加会话恢复对话框 UI
2. ✅ 实现"升级到标准分析"功能
   - analysisServiceV2.js: 添加 upgradeToStandard() 方法
   - AnalysisProgress.vue: 添加 upgrade 事件和处理
   - AnalysisWizardView.vue: 添加 handleUpgradeToStandard() 处理器
3. 分析历史记录 (已有 sessionManager 支持)
4. 加载状态和骨架屏 (已有基础实现)
```

#### C2. 报告功能完善 ✅
```
完成内容:
1. ✅ 报告导出 (PDF/Word/Excel) - 已实现
   - ReportsView.vue: exportReport() 函数
   - 后端: pdf_generator.py, word_generator.py, excel_generator.py
2. 报告分享功能 (UI 已有，功能待实现)
3. 报告对比功能 (P2 优化)
4. ✅ 历史报告管理 - ReportsView 已实现
```

#### C3. 国际化完善 ✅
```
完成内容:
1. ✅ 检查所有硬编码中文
2. ✅ 补充缺失的翻译 key
   - zh-CN.js/en.js: 添加 reports.detail.* 约 50+ 翻译键
   - zh-CN.js/en.js: 添加 analysisWizard.analysisError, unknownError
   - zh-CN.js/en.js: 添加 analysisWizard.sessionRecovery 相关键
3. 日期/数字格式本地化 (已有 toLocaleString 支持)

注意: ReportsView.vue, RoundtableView.vue, AgentChatView.vue 仍有部分硬编码中文
需要后续替换为 t() 调用
```

### Sprint D: 稳定性与监控 ✅ (已完成 2025-11-28)

#### D1. 日志与监控 ✅
```
完成内容:
1. ✅ 前端错误上报 (自建)
   - frontend/src/services/errorTracker.js: 全局错误捕获 (Vue error handler, window.onerror, unhandledrejection)
   - 错误批量上报到后端 /api/errors/report
   - 自动捕获路由信息、用户代理等上下文
2. ✅ 后端请求日志标准化
   - middleware/request_logging.py: RequestLoggingMiddleware
   - 请求ID追踪、响应时间、状态码日志
   - X-Request-ID 响应头支持客户端调试
3. ✅ 关键指标监控 (Prometheus)
   - core/metrics.py: 自定义业务指标
   - analysis_started_total, analysis_completed_total, analysis_duration_seconds
   - llm_calls_total, llm_tokens_total, agent_executions_total
   - frontend_errors_total
4. ✅ 监控 API 端点
   - GET /api/errors/metrics: 错误统计
   - GET /api/errors/errors: 最近错误列表
   - DELETE /api/errors: 清除错误缓存
```

#### D2. 性能优化 ✅
```
完成内容:
1. ✅ 前端资源压缩
   - vite.config.js: 代码分割 (vue-vendor, chart, markdown)
   - Terser 压缩 (drop_console, drop_debugger)
   - Gzip + Brotli 双重压缩 (vite-plugin-compression)
   - 资源文件 hash 命名支持缓存
   构建结果:
   - vue-vendor: 97KB → 32KB (Brotli)
   - chart: 204KB → 58KB (Brotli)
   - 主包: 313KB → 63KB (Brotli)
2. ✅ API 响应缓存策略
   - middleware/caching.py: ResponseCache + CachingMiddleware
   - 配置化 TTL: /api/scenarios (1h), /api/reports (30s), /api/reports/{id} (5m)
   - X-Cache / X-Cache-Age 响应头
   - GET /api/errors/cache/stats: 缓存统计
   - DELETE /api/errors/cache: 清除缓存
3. WebSocket 消息压缩 (P2)
4. 图片懒加载 (已有基础实现)
```

---

## 四、上线后迭代 (P2 - 持续改进)

### Sprint E: 测试与质量

#### E1. 测试覆盖
```
任务:
1. 后端 API 单元测试
2. Agent 集成测试
3. 前端组件测试
4. E2E 测试 (Cypress/Playwright)
```

#### E2. 代码质量
```
任务:
1. ESLint/Prettier 配置
2. Python Black/isort 配置
3. Pre-commit hooks
4. CI/CD 流水线
```

### Sprint F: 功能增强

#### F1. 高级功能
```
任务:
1. 用户认证与权限
2. 团队协作功能
3. API 开放平台
4. 自定义分析模板
```

#### F2. 数据增强
```
任务:
1. 更多数据源接入
2. 实时行情数据
3. 历史数据分析
4. 对比分析功能
```

---

## 五、技术债务清单

### 高优先级 (上线前必须解决)
| ID | 问题 | 文件 | 状态 |
|----|------|------|------|
| TD-001 | 硬编码 API URL | analysisServiceV2.js | ✅ 已修复 |
| TD-002 | Mock 数据返回 | report_synthesizer_agent.py | ✅ 已修复 |
| TD-003 | WebSocket 重连逻辑不完善 | analysisServiceV2.js | ✅ 已修复 |

### 中优先级 (影响维护性)
| ID | 问题 | 文件 | 状态 |
|----|------|------|------|
| TD-004 | 缺少 TypeScript | 前端整体 | 待规划 |
| TD-005 | 缺少单元测试 | 整体 | 待规划 |
| TD-006 | 错误处理不统一 | 多处 | 待修复 |
| TD-007 | TODO 注释未完成 | 多处 | 待修复 |

### 低优先级 (长期优化)
| ID | 问题 | 文件 | 状态 |
|----|------|------|------|
| TD-008 | 代码注释不足 | 整体 | 持续 |
| TD-009 | 性能优化空间 | 整体 | 持续 |

---

## 六、上线检查清单

### 功能验收
- [ ] 5个投资场景均可正常分析
- [ ] 快速判断 (3-5分钟) 流程完整
- [ ] 标准分析流程完整
- [ ] 报告生成和查看正常
- [ ] 报告导出功能正常
- [ ] 错误情况有友好提示

### 技术验收
- [ ] 所有 Mock 数据已替换
- [ ] 环境变量配置正确
- [ ] 无敏感信息泄露
- [ ] 日志正常输出
- [ ] 监控告警配置

### 部署验收
- [ ] 生产环境配置完成
- [ ] 数据库备份机制
- [ ] 服务健康检查
- [ ] 负载均衡配置
- [ ] SSL 证书配置

---

## 七、里程碑时间线

```
Week 1: Sprint A + B (核心功能 + 配置)
  - Day 1-2: Mock 数据替换
  - Day 3: 错误处理完善
  - Day 4: UI 问题修复
  - Day 5: 环境变量配置

Week 2: Sprint C + D (用户体验 + 稳定性)
  - Day 1-2: 分析流程优化
  - Day 3: 报告功能完善
  - Day 4: 国际化完善
  - Day 5: 监控与性能

Week 3: 测试与上线
  - Day 1-2: 内部测试
  - Day 3: Bug 修复
  - Day 4: 生产部署
  - Day 5: 上线监控

Week 4+: Sprint E + F (持续迭代)
  - 根据用户反馈优化
  - 新功能开发
```

---

## 八、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| LLM API 不稳定 | 分析失败 | 重试机制 + 降级方案 |
| WebSocket 断连 | 进度丢失 | 持久化 + 自动重连 |
| 高并发压力 | 服务崩溃 | Kafka 削峰 + 限流 |
| 数据安全 | 泄露风险 | 加密 + 权限控制 |

---

## 九、资源需求

### 人力
- 后端开发: 1人
- 前端开发: 1人
- 测试: 0.5人

### 基础设施
- 生产服务器 (4核8G 起步)
- Redis 集群
- Kafka 集群
- 对象存储 (报告文件)
- CDN (前端资源)

---

**下一步行动**: Sprint A-D 已完成！进入 Sprint E - 测试与质量

## 十、已完成 Sprint 总结

### Sprint A-D 完成时间: 2025-11-28
- ✅ Sprint A: 核心功能修复 (Mock替换、错误处理、UI修复)
- ✅ Sprint B: 配置与环境 (环境变量、敏感信息清理)
- ✅ Sprint C: 用户体验优化 (分析流程、报告功能、国际化)
- ✅ Sprint D: 稳定性与监控 (日志、监控、缓存、压缩)

### 新增文件清单
```
frontend/
├── src/services/errorTracker.js       # 前端错误追踪
├── src/config/api.js                   # API配置中心
└── vite.config.js                      # 构建优化配置

backend/services/report_orchestrator/app/
├── middleware/
│   ├── request_logging.py              # 请求日志中间件
│   └── caching.py                      # 响应缓存中间件
├── core/
│   └── metrics.py                      # Prometheus指标
└── api/routers/
    └── monitoring.py                   # 监控API路由
```
