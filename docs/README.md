# AI 投研工作台 - 文档中心

**项目**: Magellan - AI 投资报告 Agent
**当前版本**: V3
**最后更新**: 2025-10-26

---

## 🚨 重要文档 (请先阅读)

- 🔴 **[当前系统状态](CURRENT_STATUS.md)** - 系统概况、功能状态、性能指标
- 🐛 **[已知Bug清单](KNOWN_BUGS.md)** - 当前已知问题和修复进度
- ✅ **[V3开发完成总结](V3/V3_DEVELOPMENT_COMPLETE.md)** - 开发成果和验收状态

---

## 📚 版本文档

### V1 - MVP（初始版本）
股票分析工具，支持多Agent协作生成投资报告

- 📄 [V1 设计与架构](V1_MVP/V1_Design_and_Architecture.md)
- 📋 [V1 开发计划](V1_MVP/V1_Development_Plan.md)

### V2 - 二级市场增强版
加强的股票分析工具，引入User Persona和HITL

> V2相关文档已归档至 `archive/` 目录

### V3 - 一级市场投研工作台 ⭐ 当前版本
完整的尽职调查(DD)工作流，支持BP解析、IM生成、估值分析

### V4 - 智能投研助手 🚀 规划中
对话式交互、实时Agent反馈、迭代闭环、全面UX升级

#### 核心文档
- 📄 **[V3开发计划](V3/V3_Development_Plan.md)** - 完整开发规划 (7个Sprint)
- ✅ **[V3开发完成总结](V3/V3_DEVELOPMENT_COMPLETE.md)** - 最终交付成果

#### 设计文档
- 🎨 [交互设计指南](V3/Design/V3_INTERACTION_DESIGN_GUIDE.md) - UI/UX设计规范
- 🎨 [主题实现指南](V3/Design/V3_THEME_IMPLEMENTATION_GUIDE.md) - Base44主题系统
- 🎨 [UI/UX改进记录](V3/Design/V3_UI_UX_IMPROVEMENTS.md) - 界面优化历史

#### 实现文档
- 🔧 [Shadcn UI实现](V3/Implementation/V3_SHADCN_UI_IMPLEMENTATION.md) - UI组件库集成
- 🔧 [交互模式矩阵](V3/Implementation/V3_INTERACTION_PATTERNS_MATRIX.md) - 交互模式设计

#### 测试文档
- ✅ [完整测试报告](V3/Testing/V3_COMPLETE_TEST_REPORT.md) - 系统测试验证结果
- 📋 [用户测试指南](V3/Testing/V3_USER_TESTING_GUIDE.md) - 用户测试流程

#### 维护文档
- 🐛 [Bug修复和改进](V3/Maintenance/V3_BUG_FIXES_AND_IMPROVEMENTS.md) - 详细bug修复记录 (50KB)

### V4 - 智能投研助手 🚀 规划中

#### 规划文档
- 📋 **[V4 README](V4/README.md)** - V4概述和导航
- ⭐ **[V4 Executive Summary](V4/V4_Executive_Summary.md)** - 执行摘要 (必读)
- 📖 **[V4 Product Analysis and Plan](V4/V4_Product_Analysis_and_Plan.md)** - 详细设计

---

## 🎯 快速开始

### 当前系统（V3）

**核心能力**:
1. 📄 BP 智能解析
2. 🔍 机构偏好筛选
3. 👥 团队尽职调查
4. 📈 市场尽职调查
5. ⚠️ 风险评估
6. 📝 IM 工作台
7. 💡 内部洞察
8. 📥 Word 导出
9. 💰 估值与退出分析

**技术栈**:
- 后端: FastAPI + Google Gemini + ChromaDB
- 前端: Vue 3 + TypeScript + Base44 设计系统
- 架构: 微服务 + 7个专业Agent

**快速启动**:
```bash
# 启动后端
docker compose up -d

# 启动前端
cd frontend && npm run dev
```

---

## 📈 版本演进

| 版本 | 定位 | 核心功能 | 状态 |
|------|------|---------|------|
| V1 | 股票分析 MVP | 3个Agent，基础报告 | ✅ 已完成 |
| V2 | 二级市场增强 | User Persona，HITL | ✅ 已完成 |
| V3 | 一级市场投研 | DD工作流，IM生成，估值 | ✅ **当前版本** |

---

## 🏗️ 系统架构（V3）

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend (Vue 3)                       │
│  ChatView │ InteractiveReportView │ PersonaView │ ReportView │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Report Orchestrator                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              DD State Machine                        │   │
│  │  INIT → DOC_PARSE → PREFERENCE_CHECK → TDD → MDD    │   │
│  │  → CROSS_CHECK → DD_QUESTIONS → HITL → COMPLETED    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  TeamAgent │ MarketAgent │ RiskAgent │ PreferenceAgent│  │
│  │  ValuationAgent │ ExitAgent │ BPParser                │  │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ LLM Gateway  │    │ Web Search   │    │ User Service │
│  (Gemini)    │    │  (Tavily)    │    │  (偏好管理)   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     
        ▼                     
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Internal     │    │ External     │    │ File Service │
│ Knowledge    │    │ Data Service │    │ (解析器)      │
│ (ChromaDB)   │    │ (天眼查)      │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 📊 代码统计

| 指标 | V1 | V2 | V3 |
|------|----|----|-----|
| 总代码量 | ~2,000行 | ~3,500行 | ~6,510行 |
| 微服务 | 5个 | 6个 | 7个 |
| Agent | 3个 | 4个 | 7个 |
| 前端视图 | 2个 | 3个 | 4个 |

---

## 🎓 学习路径

### 1. 新手入门
1. 阅读 [V1 设计与架构](V1_MVP/V1_Design_and_Architecture.md)
2. 了解基本的 Agent 协作模式
3. 理解报告生成流程

### 2. 进阶理解
1. 阅读 [V2 vs V3 对比](V2/V2_vs_V3_Comparison.md)
2. 理解从二级市场到一级市场的转变
3. 学习 HITL（Human-in-the-Loop）机制

### 3. 深入开发
1. 阅读 [V3 技术细节](V3/V3_Technical_Details.md)
2. 了解 DD 状态机设计
3. 学习 Agent 实现细节
4. 研究 Base44 设计系统

---

## 🔧 开发资源

### API 文档
- Report Orchestrator: http://localhost:8000/docs
- LLM Gateway: http://localhost:8001/docs
- User Service: http://localhost:8008/docs

### 测试
```bash
# 运行所有测试
pytest

# 运行特定 Sprint 测试
pytest test_sprint3_phase2_e2e.py
```

### 日志
```bash
# 查看服务日志
docker logs magellan-report_orchestrator
docker logs magellan-llm_gateway
```

---

## 📝 贡献指南

### 添加新 Agent
1. 在 `backend/services/report_orchestrator/app/agents/` 创建新文件
2. 继承基础 Agent 类或直接实现
3. 在状态机中注册
4. 添加测试

### 修改 UI
1. 遵循 Base44 设计系统
2. 使用 CSS 变量
3. 保持深色模式一致性

---

## 🐛 问题排查

### 常见问题

> **详细的bug追踪和排查请查看**: [KNOWN_BUGS.md](KNOWN_BUGS.md)

1. **LLM Gateway 502/503 错误**
   - 检查 GOOGLE_API_KEY 环境变量
   - 重启服务: `docker compose restart llm_gateway`
   - 查看日志: `docker logs magellan-llm_gateway-1 --tail=100`

2. **ChromaDB 连接失败**
   - 确保 Chroma 容器运行: `docker compose ps | grep chroma`
   - 检查网络连接
   - 重启服务: `docker compose restart chroma`

3. **前端构建失败**
   - 清除缓存: `rm -rf node_modules && npm install`
   - 检查 TypeScript 错误: `npm run build`
   - 查看详细日志

4. **WebSocket 连接失败**
   - 检查 report_orchestrator 服务状态
   - 查看浏览器控制台错误
   - 确认文件大小不超过50MB

### 调试命令
```bash
# 查看所有服务状态
docker compose ps

# 查看特定服务日志
docker logs magellan-report_orchestrator --tail=100

# 重启所有服务
docker compose restart

# 重新构建并启动
docker compose up -d --build
```

---

## 📁 文档结构

```
docs/
├── README.md                  # 📚 本文档 - 文档导航中心
├── CURRENT_STATUS.md          # 🔴 当前系统状态 (重要!)
├── KNOWN_BUGS.md              # 🐛 已知bug清单 (重要!)
│
├── V1_MVP/                    # V1版本文档
│   ├── V1_Design_and_Architecture.md
│   └── V1_Development_Plan.md
│
├── V3/                        # V3版本文档 (当前版本)
│   ├── V3_Development_Plan.md
│   ├── V3_DEVELOPMENT_COMPLETE.md
│   ├── Design/                # 设计文档
│   │   ├── V3_INTERACTION_DESIGN_GUIDE.md
│   │   ├── V3_THEME_IMPLEMENTATION_GUIDE.md
│   │   └── V3_UI_UX_IMPROVEMENTS.md
│   ├── Implementation/        # 实现文档
│   │   ├── V3_SHADCN_UI_IMPLEMENTATION.md
│   │   └── V3_INTERACTION_PATTERNS_MATRIX.md
│   ├── Testing/               # 测试文档
│   │   ├── V3_COMPLETE_TEST_REPORT.md
│   │   └── V3_USER_TESTING_GUIDE.md
│   └── Maintenance/           # 维护文档
│       └── V3_BUG_FIXES_AND_IMPROVEMENTS.md
│
└── archive/                   # 历史归档文档
    └── Sprint1-7相关文档
```

---

## 📧 联系与反馈

### 报告Bug
1. 查看 [KNOWN_BUGS.md](KNOWN_BUGS.md) 确认是否为已知问题
2. 使用文档中的Bug报告模板记录新问题
3. 附上详细的错误日志和复现步骤

### 技术支持
- **系统状态**: 查看 [CURRENT_STATUS.md](CURRENT_STATUS.md)
- **开发文档**: 查看 V3/ 目录下的相关文档
- **历史记录**: 查看 archive/ 目录

---

## 📝 更新日志

### 2025-10-26
- 📚 文档重组: 创建清晰的V3文档结构
- 📝 新增 CURRENT_STATUS.md 和 KNOWN_BUGS.md
- 🗑️ 清理中间过程文档

### 2025-10-24
- 🐛 修复5个关键bug (详见V3/Maintenance/)
- ✅ 系统稳定性大幅提升

### 2025-10-22
- ✅ V3开发完成 (Sprint 1-7全部完成)
- ✅ 完整测试验证通过

---

**最后更新**: 2025-10-26
**文档版本**: 2.0.0
**维护者**: Magellan Team
