# LLM连接错误处理修复

## 问题描述

DD工作流报错:
```
Server disconnected without sending a response.
httpx.RemoteProtocolError: Server disconnected without sending a response.
```

错误发生在市场分析智能体调用LLM网关时,导致整个DD工作流崩溃。

## 根本原因

当LLM网关出现以下情况时,整个DD工作流会崩溃:
1. **服务器断开连接**: LLM网关崩溃或网络中断
2. **请求超时**: LLM处理时间过长
3. **服务不可用**: LLM网关重启或维护

之前的代码没有捕获这些异常,导致错误向上传播使整个工作流失败。

## 修复方案

### 策略: 优雅降级 (Graceful Degradation)

当LLM调用失败时,返回一个占位响应,让工作流继续进行,而不是完全崩溃。

### 实现

#### 1. market_analysis_agent.py

**文件位置**: `backend/services/report_orchestrator/app/agents/market_analysis_agent.py`

**修改前**:
```python
async def _call_llm(self, prompt: str) -> str:
    """Call LLM Gateway for analysis"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{self.llm_gateway_url}/chat",
            json={
                "history": [
                    {"role": "user", "parts": [prompt]}
                ]
            }
        )

        if response.status_code != 200:
            raise Exception(f"LLM Gateway returned {response.status_code}")

        result = response.json()
        return result.get("content", "")
```

**修改后**:
```python
async def _call_llm(self, prompt: str) -> str:
    """Call LLM Gateway for analysis"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{self.llm_gateway_url}/chat",
                json={
                    "history": [
                        {"role": "user", "parts": [prompt]}
                    ]
                }
            )

            if response.status_code != 200:
                raise Exception(f"LLM Gateway returned {response.status_code}")

            result = response.json()
            return result.get("content", "")
        except httpx.RemoteProtocolError as e:
            print(f"[Market Agent] LLM server disconnected: {e}", flush=True)
            # 返回占位响应
            return """```json
{
    "summary": "由于LLM服务暂时不可用，无法完成完整的市场分析。建议稍后重试或使用备用分析方法。",
    "market_validation": "LLM服务不可用",
    "growth_potential": "待评估",
    "competitive_landscape": "待分析",
    "red_flags": ["LLM服务连接失败，无法完成自动化分析"],
    "opportunities": []
}
```"""
        except httpx.TimeoutException as e:
            print(f"[Market Agent] LLM request timeout: {e}", flush=True)
            return """```json
{
    "summary": "LLM请求超时，无法完成市场分析。",
    "market_validation": "分析超时",
    "growth_potential": "待评估",
    "competitive_landscape": "待分析",
    "red_flags": ["分析请求超时"],
    "opportunities": []
}
```"""
```

#### 2. team_analysis_agent.py

**文件位置**: `backend/services/report_orchestrator/app/agents/team_analysis_agent.py`

**应用相同的错误处理模式**:
```python
except httpx.RemoteProtocolError as e:
    print(f"[Team Agent] LLM server disconnected: {e}", flush=True)
    return """```json
{
    "summary": "由于LLM服务暂时不可用，无法完成完整的团队分析。",
    "strengths": [],
    "concerns": ["LLM服务连接失败"],
    "experience_match_score": 5.0
}
```"""
except httpx.TimeoutException as e:
    print(f"[Team Agent] LLM request timeout: {e}", flush=True)
    return """```json
{
    "summary": "LLM请求超时，无法完成团队分析。",
    "strengths": [],
    "concerns": ["分析请求超时"],
    "experience_match_score": 5.0
}
```"""
```

## 错误处理策略

### 捕获的异常

1. **httpx.RemoteProtocolError**: LLM服务器断开连接
   - 场景: 服务崩溃、网络中断、服务重启
   - 响应: 返回带有错误说明的占位数据

2. **httpx.TimeoutException**: 请求超时
   - 场景: LLM处理时间过长(>120秒)
   - 响应: 返回超时说明的占位数据

### 占位响应设计原则

1. **有效的JSON格式**: 确保能被解析器正确处理
2. **符合数据模型**: 包含所有必需字段
3. **清晰的错误标记**: 在相关字段中说明失败原因
4. **红旗/担忧**: 将错误信息添加到`red_flags`或`concerns`字段

### 示例流程

```
用户启动DD分析
    ↓
步骤1: BP解析 ✅ 成功
    ↓
步骤2: 团队分析
    ↓
调用LLM → ❌ RemoteProtocolError
    ↓
捕获异常 → 返回占位响应
    ↓
team_analysis = {
    "summary": "LLM服务不可用",
    "concerns": ["LLM服务连接失败"]
}
    ↓
步骤3: 市场分析 ✅ 成功
    ↓
生成报告 ✅ 包含部分结果 + 错误说明
```

## 用户体验

### 修复前
```
DD分析启动
 → 市场分析开始
 → LLM调用失败
 → ❌ 整个工作流崩溃
 → ❌ 用户看到错误信息
 → ❌ 没有任何分析结果
```

### 修复后
```
DD分析启动
 → 市场分析开始
 → LLM调用失败
 → ⚠️  返回占位响应
 → ✅ 工作流继续
 → ✅ 生成部分报告
 → ✅ 错误信息在报告中标注
 → ✅ 用户至少得到部分结果
```

## 后续改进建议

### 短期改进

1. **重试机制**: 添加自动重试(最多3次)
   ```python
   for attempt in range(3):
       try:
           return await self._call_llm(prompt)
       except httpx.RemoteProtocolError:
           if attempt == 2:
               return placeholder_response
           await asyncio.sleep(2 ** attempt)  # 指数退避
   ```

2. **备用LLM**: 当主LLM失败时,尝试备用LLM
   ```python
   try:
       return await self._call_primary_llm(prompt)
   except Exception:
       return await self._call_backup_llm(prompt)
   ```

### 长期改进

1. **健康检查**: 定期检查LLM网关健康状态
2. **断路器模式**: 当错误率高时,暂时跳过LLM调用
3. **监控告警**: 当LLM失败时发送告警通知
4. **缓存机制**: 缓存常见查询的LLM响应

## 监控建议

### 日志记录

修复后的代码会输出:
```
[Market Agent] LLM server disconnected: Server disconnected without sending a response.
[Team Agent] LLM request timeout: Request timeout after 120 seconds
```

### 监控指标

- LLM调用失败率
- LLM响应时间
- 占位响应使用频率
- 工作流完成率

## 测试验证

### 场景1: LLM服务停止
```bash
# 停止LLM网关
docker stop magellan-llm_gateway-1

# 启动DD分析
# 预期: 工作流继续,返回占位响应
```

### 场景2: LLM响应缓慢
```bash
# 模拟慢响应 (需要修改LLM网关添加延迟)
# 预期: 120秒后超时,返回占位响应
```

### 场景3: 正常情况
```bash
# LLM正常运行
# 预期: 正常分析结果
```

## 部署状态

✅ market_analysis_agent.py 已修复
✅ team_analysis_agent.py 已修复
✅ 后端服务已重启

现在DD工作流在LLM失败时不会崩溃,而是优雅降级并继续执行!🎉
