# Magellan Analysis Module - 测试指南

## 📋 概述

本文档提供Magellan投资分析系统的完整测试指南,包括单元测试、集成测试和端到端测试。

---

## 🧪 测试套件概览

### 1. **端到端测试** (test_all_scenarios_complete.sh)
- **位置**: `/test_all_scenarios_complete.sh`
- **测试范围**: 所有5个场景 × 3种深度 = 15个测试用例
- **运行方式**: Bash脚本 + curl
- **用途**: 验证API端点和完整流程

### 2. **单元测试** (test_all_scenarios.py)
- **位置**: `/backend/services/report_orchestrator/tests/test_all_scenarios.py`
- **测试框架**: pytest + pytest-asyncio
- **用途**: 验证Orchestrator和Agent的内部逻辑

---

## 🚀 快速开始

### 前置条件

1. **启动所有服务**
```bash
cd /Users/dengjianbo/Documents/Magellan
docker-compose up -d
```

2. **验证服务健康状态**
```bash
curl http://localhost:8001/health
curl http://localhost:8003/health  # LLM Gateway
curl http://localhost:8010/health  # Web Search Service
```

---

## 📝 运行端到端测试

### 完整测试套件 (15个测试用例)

```bash
./test_all_scenarios_complete.sh
```

**测试场景**:
- ✅ 早期投资 (Early Stage) - Quick/Standard/Comprehensive
- ✅ 成长期投资 (Growth) - Quick/Standard/Comprehensive
- ✅ 公开市场投资 (Public Market) - Quick/Standard/Comprehensive
- ✅ 另类投资 (Alternative) - Quick/Standard/Comprehensive
- ✅ 行业研究 (Industry Research) - Quick/Standard/Comprehensive

**输出示例**:
```
========================================
Magellan Analysis Module - 完整端到端测试
========================================

ℹ API地址: http://localhost:8001
ℹ 开始时间: 2025-11-19 15:30:00

ℹ 检查API健康状态...
✓ API健康检查通过

========================================
场景1: 早期投资 (Early Stage Investment)
========================================

[TEST 1] Early Stage - Quick
✓ 测试通过 (session: 1a2b3c4d...)
ℹ Status: processing, Message: Analysis started

[TEST 2] Early Stage - Standard
✓ 测试通过 (session: 5e6f7g8h...)
...

========================================
测试总结
========================================
总测试数:   15
通过:       15
失败:       0

✓ 所有测试通过! 🎉
```

---

## 🔬 运行单元测试

### 安装测试依赖

```bash
cd backend/services/report_orchestrator
pip install pytest pytest-asyncio
```

### 运行所有测试

```bash
# 在report_orchestrator目录下
python tests/test_all_scenarios.py
```

或使用pytest命令:

```bash
pytest tests/test_all_scenarios.py -v -s
```

**测试类别**:
1. **场景测试** - 验证每个场景的基本功能
2. **Agent集成测试** - 验证新Agent是否正确集成
3. **Mock数据标识测试** - 验证is_mock字段存在
4. **性能测试** - 验证响应时间

---

## 📊 测试覆盖率

### 当前覆盖情况

| 场景 | Quick Mode | Standard Mode | Comprehensive Mode | Agent覆盖率 |
|-----|-----------|--------------|-------------------|-----------|
| **早期投资** | ✅ | ✅ | ✅ | 85% |
| **成长期投资** | ✅ | ✅ | ✅ | 80% |
| **公开市场** | ✅ | ✅ | ✅ | 85% |
| **另类投资** | ✅ | ✅ | ✅ | 75% |
| **行业研究** | ✅ | ✅ | ✅ | 95% |

**整体Agent实现覆盖率**: 72%

---

## 🧩 已实现的Agent列表

### Quick Agents (100% 覆盖)
- ✅ TeamQuickAgent - 团队快速评估
- ✅ MarketQuickAgent - 市场机会评估
- ✅ RedFlagAgent - 红旗检查
- ✅ FinancialHealthAgent - 财务健康检查
- ✅ GrowthPotentialAgent - 增长潜力评估
- ✅ MarketPositionAgent - 市场地位评估
- ✅ ValuationQuickAgent - 估值快速检查
- ✅ FundamentalsAgent - 基本面分析
- ✅ TechnicalAnalysisAgent - 技术分析
- ✅ TechFoundationAgent - 技术基础评估
- ✅ TokenomicsAgent - 代币经济学评估
- ✅ CommunityActivityAgent - 社区活跃度
- ✅ MarketSizeAgent - 市场规模分析
- ✅ CompetitionLandscapeAgent - 竞争格局
- ✅ TrendAnalysisAgent - 趋势分析
- ✅ OpportunityScanAgent - 机会扫描
- ✅ IndustryResearcherAgent - 行业研究
- ✅ DataFetcherAgent - 股票数据获取

### Standard/Comprehensive Agents (实现进度)
- ✅ **FinancialExpertAgent** - 深度财务分析 (影响3个场景)
- ✅ **CryptoAnalystAgent** - 加密项目深度分析
- ⏳ OnchainAnalystAgent - 链上数据分析 (待实现)
- ⏳ BPParserAgent - BP文档解析 (待实现)
- ⏳ QuantAnalystAgent - 量化分析 (待实现)

---

## 🎯 测试最佳实践

### 1. 测试前检查

```bash
# 检查Docker容器状态
docker ps

# 检查服务日志
docker logs magellan-report_orchestrator --tail 50
docker logs magellan-llm_gateway --tail 50

# 检查网络连接
docker network inspect magellan_default
```

### 2. 单独测试某个场景

```bash
# 使用curl测试单个场景
curl -X POST http://localhost:8001/analysis/start \
  -H "Content-Type: application/json" \
  -d '{
    "target": {
      "company_name": "测试公司",
      "stage": "seed",
      "industry": "AI"
    },
    "config": {
      "depth": "quick"
    }
  }'
```

### 3. 调试失败的测试

```bash
# 查看详细日志
docker logs magellan-report_orchestrator --follow

# 进入容器调试
docker exec -it magellan-report_orchestrator bash

# 查看Python错误
docker exec magellan-report_orchestrator python -m py_compile app/core/orchestrators/*.py
```

---

## 📈 性能基准

### 响应时间目标

| 模式 | 目标时间 | 当前平均时间 |
|-----|---------|-----------|
| Quick | < 5秒 | ~3秒 |
| Standard | < 45秒 | ~30秒 |
| Comprehensive | < 2分钟 | ~60秒 |

### 并发测试

```bash
# 使用ab (Apache Bench)进行并发测试
ab -n 100 -c 10 -p test_payload.json -T application/json \
  http://localhost:8001/analysis/start
```

---

## 🐛 常见问题排查

### 问题1: 测试失败 "API不可访问"

**原因**: 服务未启动
**解决**:
```bash
docker-compose up -d
sleep 10  # 等待服务完全启动
```

### 问题2: 测试失败 "HTTP 500"

**原因**: 后端代码错误
**解决**:
```bash
# 查看错误日志
docker logs magellan-report_orchestrator --tail 100

# 检查Python语法
python3 -m py_compile backend/services/report_orchestrator/app/**/*.py
```

### 问题3: 测试超时

**原因**: LLM Gateway响应慢或网络问题
**解决**:
```bash
# 检查LLM Gateway健康状态
curl http://localhost:8003/health

# 重启服务
docker-compose restart llm_gateway
```

---

## 📚 扩展阅读

- [Agent开发指南](./docs/AGENT_DEVELOPMENT_GUIDE.md)
- [Orchestrator架构](./docs/ORCHESTRATOR_ARCHITECTURE.md)
- [API文档](./docs/API_DOCUMENTATION.md)
- [Phase 2进度报告](./PHASE2_PROGRESS_REPORT.md)

---

## 🔄 持续集成

### GitHub Actions (待配置)

```yaml
name: Test All Scenarios

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker-compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run E2E tests
        run: ./test_all_scenarios_complete.sh
      - name: Run unit tests
        run: |
          cd backend/services/report_orchestrator
          pytest tests/test_all_scenarios.py -v
```

---

## 📝 测试报告

测试执行后,可以生成HTML报告:

```bash
# 使用pytest生成HTML报告
pytest tests/test_all_scenarios.py --html=test_report.html --self-contained-html

# 查看报告
open test_report.html
```

---

**最后更新**: 2025-11-19
**维护者**: Magellan Development Team
**版本**: Phase 2 Complete
