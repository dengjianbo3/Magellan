# 文档和脚本清理计划

## 📋 分类标准

### 🔵 核心文件（必须保留）
- 当前正在使用的配置和运行脚本
- 主要技术文档和设计文档
- 最新的修复和发布文档

### 🟡 归档文件（移至archive/）
- 已完成的历史修复记录
- 过时的测试脚本
- 中间版本的文档

### 🔴 删除文件
- 完全过时的临时脚本
- 重复的功能性脚本

---

## 📁 具体分类

### 🔵 核心文件 - 保留在根目录

#### 配置文件
- `.env.example` ✅ 环境变量模板
- `.gitignore` ✅ Git配置
- `config.yaml` ✅ 系统配置
- `docker-compose.yml` ✅ Docker配置

#### 核心运行脚本
- `start.sh` ✅ 启动脚本
- `stop.sh` ✅ 停止脚本
- `quick_deploy.sh` ✅ 快速部署
- `view-logs.sh` ✅ 查看日志
- `status.sh` ✅ 状态检查

#### 核心文档
- `README.md` ✅ 项目说明
- `TECHNICAL_DOCUMENTATION.md` ✅ 技术文档
- `POSITION_AWARE_SYSTEM_DESIGN.md` ✅ 位置感知系统设计（当前架构）

#### 最新版本文档
- `CODE_REVIEW_FIXES.md` ✅ 代码审查修复（v1.1.1）
- `DEFENSIVE_FIXES_SUMMARY.md` ✅ 防御性修复总结（v1.1.1）
- `QUICK_DEPLOY_v1.1.1.md` ✅ 快速部署指南（v1.1.1）
- `verify_fixes.sh` ✅ 验证脚本（v1.1.1）

#### 测试框架
- `tests/` ✅ 整个测试目录（保留）
  - `README.md` ✅
  - `QUICKSTART.md` ✅
  - `requirements.txt` ✅
  - `conftest.py` ✅
  - `run_tests.sh` ✅
  - `fixtures/` ✅
  - `mocks/` ✅
  - `unit/` ✅
  - `integration/` ✅

---

### 🟡 归档文件 - 移至 archive/历史修复/

#### 历史Bug修复记录（已完成）
- `BUGFIX_PLAN.md` → archive/历史修复/
- `BUGFIX_COMPLETED.md` → archive/历史修复/
- `ISSUE_PREMATURE_EXECUTION.md` → archive/历史修复/
- `TRADEEXECUTOR_FIX.md` → archive/历史修复/
- `WHY_DOUBLE_TRIGGER.md` → archive/历史修复/
- `WHY_TWO_NO_SIGNALS.md` → archive/历史修复/
- `DOUBLE_TRIGGER_ROOT_CAUSE.md` → archive/历史修复/
- `FIX_SUMMARY.md` → archive/历史修复/
- `FIX_GUIDE.md` → archive/历史修复/

#### 历史架构升级记录（已完成）
- `ARCHITECTURE_UPGRADE_PLAN.md` → archive/架构升级/
- `ARCHITECTURE_UPGRADE_COMPLETED.md` → archive/架构升级/

#### 历史开发进度记录
- `DAY2_SUMMARY.md` → archive/开发进度/
- `DAY2_COMPLETION_REPORT.md` → archive/开发进度/
- `DAY2_TEST_REPORT.md` → archive/开发进度/
- `IMPLEMENTATION_PROGRESS.md` → archive/开发进度/

#### 历史版本发布
- `RELEASE_v1.1.0.md` → archive/版本发布/
- `DEPLOY_GUIDE.md` → archive/版本发布/ (被QUICK_DEPLOY_v1.1.1.md取代)

#### 历史测试报告
- `tests/LOCAL_TEST_REPORT.md` → archive/测试报告/
- `tests/STATUS.md` → archive/测试报告/

#### 历史项目分析
- `PROJECT_ANALYSIS.md` → archive/项目分析/
- `TP_SL_MECHANISM.md` → archive/设计文档/

---

### 🔴 删除文件 - 临时/重复脚本

#### 临时测试和修复脚本
- `diagnose.sh` 🗑️ 临时诊断脚本
- `full_test.sh` 🗑️ 临时测试脚本
- `update_and_test.sh` 🗑️ 临时更新脚本
- `verify_fix.sh` 🗑️ 旧版验证脚本（被verify_fixes.sh取代）
- `trigger_analysis.sh` 🗑️ 临时触发脚本
- `run_architecture_tests.py` 🗑️ 临时架构测试（tests/内有完整测试）

#### 过时的维护脚本
- `fix_redis_issue.sh` 🗑️ 特定问题修复脚本（问题已解决）
- `rebuild_trading_service.sh` 🗑️ 功能被quick_deploy.sh包含
- `remote_fix_and_deploy.sh` 🗑️ 功能被quick_deploy.sh包含
- `remote-status.sh` 🗑️ 功能被status.sh包含

#### 过时的调试脚本
- `debug-agents.sh` 🗑️ 临时调试脚本
- `view-agents-old.sh` 🗑️ 旧版本
- `view-agents.sh` 🗑️ 临时查看脚本
- `check-logs.sh` 🗑️ 功能被view-logs.sh包含
- `logs.sh` 🗑️ 功能被view-logs.sh包含

#### 其他
- `test_api.sh` 🗑️ 临时API测试
- `test_trading_api.sh` 🗑️ 临时交易API测试
- `deploy_dashboard.sh` 🗑️ Dashboard部署（不在核心功能内）
- `DEPLOY_DASHBOARD.md` 🗑️ Dashboard文档
- `status.html` 🗑️ 静态状态页（不需要）
- `scripts/email_notifier.py` 🗑️ 邮件通知脚本（未使用）

---

## 📊 统计

| 类别 | 数量 |
|------|------|
| 🔵 保留（核心） | 15个文件 + tests目录 |
| 🟡 归档 | 19个文件 |
| 🔴 删除 | 22个文件 |

---

## 🎯 清理后的目录结构

```
trading-standalone/
├── 📁 配置文件
│   ├── .env.example
│   ├── .gitignore
│   ├── config.yaml
│   └── docker-compose.yml
│
├── 📁 核心脚本
│   ├── start.sh
│   ├── stop.sh
│   ├── quick_deploy.sh
│   ├── verify_fixes.sh
│   ├── view-logs.sh
│   └── status.sh
│
├── 📁 核心文档
│   ├── README.md
│   ├── TECHNICAL_DOCUMENTATION.md
│   ├── POSITION_AWARE_SYSTEM_DESIGN.md
│   ├── CODE_REVIEW_FIXES.md
│   ├── DEFENSIVE_FIXES_SUMMARY.md
│   └── QUICK_DEPLOY_v1.1.1.md
│
├── 📁 测试框架
│   └── tests/
│       ├── README.md
│       ├── QUICKSTART.md
│       ├── requirements.txt
│       ├── run_tests.sh
│       ├── conftest.py
│       ├── fixtures/
│       ├── mocks/
│       ├── unit/
│       └── integration/
│
└── 📁 历史归档
    └── archive/
        ├── 历史修复/
        ├── 架构升级/
        ├── 开发进度/
        ├── 版本发布/
        ├── 测试报告/
        ├── 项目分析/
        └── 设计文档/
```

---

## ✅ 优点

1. **清晰的组织结构** - 核心文件一目了然
2. **历史可追溯** - 归档文件保留了开发历史
3. **易于维护** - 减少根目录混乱
4. **新人友好** - 快速找到需要的文档

---

## 🚀 执行计划

1. 创建archive目录结构
2. 移动文件到对应archive子目录
3. 删除临时和重复文件
4. 提交清理结果
