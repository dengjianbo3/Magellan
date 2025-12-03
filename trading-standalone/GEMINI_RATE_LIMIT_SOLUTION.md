# Gemini 500错误解决方案 - 速率限制和超时

## 问题分析

你的观察非常准确！Gemini出现500错误有两个主要原因：

### 1. 速率限制 (Rate Limiting)

**Gemini API限制（免费版）:**
- **RPM**: 15 requests/minute
- **TPM**: 32,000 tokens/minute
- **RPD**: 1,500 requests/day

**Trading系统的请求量:**
```
5 Agents (并发) × 3-4轮讨论 = 15-20 requests
→ 超过15 RPM限制！
```

### 2. 超时问题 (Timeout)

**大模型响应时间:**
- Gemini-2.0-flash-exp: 2-5秒/请求
- DeepSeek-chat: 3-8秒/请求
- Gemini思考模式: 5-15秒/请求

**潜在超时点:**
- HTTP client timeout
- Agent execution timeout
- Meeting turn timeout

---

## 解决方案

### 方案1: 减少并发请求（推荐-快速实施）

#### 1.1 减少Agent数量

修改 `backend/services/report_orchestrator/app/core/trading/trading_agents.py`:

```python
# 只保留3个最核心的Agent
analysis_agent_ids = [
    "technical_analyst",    # 技术分析 - 核心
    "sentiment_analyst",    # 情绪分析 - 重要
    "risk_assessor",        # 风险评估 - 必须
    # 注释掉这两个
    # "macro_economist",
    # "quant_strategist",
]
```

**效果:**
- 请求量: 15-20 → 9-12 requests
- 符合15 RPM限制 ✅

#### 1.2 顺序执行Agent（而非并发）

修改 `backend/services/report_orchestrator/app/core/roundtable/meeting.py`:

```python
# 在 Meeting.run() 方法中
# 找到 Agent 执行逻辑，添加顺序执行

async def _execute_agents_sequentially(self, agents: List[Agent]):
    """顺序执行Agents,避免速率限制"""
    for agent in agents:
        await agent.act(context)
        await asyncio.sleep(5)  # 每个Agent之间间隔5秒
```

**效果:**
- RPM: 5 agents × 12秒 = 1分钟内只有5个请求 ✅
- 但会变慢: 原来20秒完成 → 现在60秒完成

---

### 方案2: 添加重试和速率限制器（推荐-长期方案）

#### 2.1 在llm_gateway添加重试逻辑

修改 `backend/services/llm_gateway/app/main.py`:

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# 在 call_gemini 函数添加重试装饰器
@retry(
    stop=stop_after_attempt(3),  # 最多重试3次
    wait=wait_exponential(multiplier=1, min=4, max=60),  # 指数退避: 4s, 8s, 16s...
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def call_gemini_with_retry(request: GenerateRequest) -> str:
    """带重试的Gemini调用"""
    # 原有的 call_gemini 逻辑
    ...
```

#### 2.2 添加全局速率限制器

创建新文件 `backend/services/llm_gateway/app/rate_limiter.py`:

```python
import asyncio
import time
from collections import deque

class RateLimiter:
    """简单的速率限制器 - 滑动窗口算法"""

    def __init__(self, max_requests: int = 15, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """等待直到可以发送请求"""
        async with self.lock:
            now = time.time()

            # 移除窗口外的请求
            while self.requests and self.requests[0] < now - self.window_seconds:
                self.requests.popleft()

            # 如果达到限制,等待
            if len(self.requests) >= self.max_requests:
                sleep_time = self.requests[0] + self.window_seconds - now + 0.1
                print(f"[RateLimiter] Sleeping {sleep_time:.1f}s to avoid rate limit")
                await asyncio.sleep(sleep_time)
                return await self.acquire()  # 递归重试

            # 记录这次请求
            self.requests.append(now)

# 全局限制器
gemini_limiter = RateLimiter(max_requests=12, window_seconds=60)  # 保守设置12 RPM
```

然后在 `call_gemini` 开头调用:

```python
async def call_gemini(request: GenerateRequest) -> str:
    await gemini_limiter.acquire()  # 等待速率限制
    # ... 原有逻辑
```

---

### 方案3: 增加超时时间

#### 3.1 增加OpenAI client超时

修改 `backend/services/llm_gateway/app/main.py` 初始化:

```python
from openai import OpenAI

# DeepSeek client
deepseek_client = OpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL,
    timeout=120.0  # 增加到120秒
)

# Kimi client
kimi_client = OpenAI(
    api_key=settings.KIMI_API_KEY,
    base_url=settings.KIMI_BASE_URL,
    timeout=120.0
)
```

#### 3.2 增加HTTP client超时

修改 `backend/services/report_orchestrator/app/core/llm_service.py`:

```python
import httpx

async with httpx.AsyncClient(timeout=120.0) as client:  # 增加到120秒
    response = await client.post(...)
```

---

### 方案4: 使用更快的模型

#### 4.1 切换到更快的Gemini模型

修改 `.env`:

```bash
# 从
GEMINI_MODEL_NAME=gemini-2.0-flash-exp

# 改为更快的flash
GEMINI_MODEL_NAME=gemini-1.5-flash
```

**对比:**
- gemini-2.0-flash-exp: 思考能力强,慢 (5-10s)
- gemini-1.5-flash: 更快 (2-3s)

#### 4.2 切换到DeepSeek的小模型

```bash
# 从
DEEPSEEK_MODEL_NAME=deepseek-chat  # 较慢

# 改为
DEEPSEEK_MODEL_NAME=deepseek-reasoner  # 更快
```

---

## 快速修复步骤（立即可用）

### Step 1: 减少Agent到3个

```bash
cd /Users/dengjianbo/Documents/Magellan/backend/services/report_orchestrator/app/core/trading

# 编辑 trading_agents.py
nano trading_agents.py

# 修改为:
analysis_agent_ids = [
    "technical_analyst",
    "sentiment_analyst",
    "risk_assessor",
]
```

### Step 2: 增加超时时间

```bash
cd /Users/dengjianbo/Documents/Magellan/backend/services/llm_gateway/app

# 编辑 main.py
nano main.py

# 在 OpenAI client 初始化添加 timeout=120.0
```

### Step 3: 重启服务

```bash
docker-compose restart report_orchestrator llm_gateway
```

### Step 4: 测试

```bash
curl -X POST http://localhost:8000/api/trading/start
curl -X POST http://localhost:8000/api/trading/trigger

# 等待60秒
sleep 60

# 查看结果
curl -s http://localhost:8000/api/trading/history?limit=5 | python3 -m json.tool
```

---

## 长期优化建议

### 1. 实现完整的速率限制器

使用 `redis` + `aioredis` 实现分布式速率限制:

```bash
pip install aioredis
```

```python
import aioredis

class RedisRateLimiter:
    def __init__(self, redis_url: str, max_requests: int = 15, window: int = 60):
        self.redis = aioredis.from_url(redis_url)
        self.max_requests = max_requests
        self.window = window

    async def acquire(self, key: str = "gemini"):
        current = await self.redis.incr(f"rate_limit:{key}")
        if current == 1:
            await self.redis.expire(f"rate_limit:{key}", self.window)

        if current > self.max_requests:
            ttl = await self.redis.ttl(f"rate_limit:{key}")
            await asyncio.sleep(ttl)
            return await self.acquire(key)
```

### 2. 添加监控和告警

记录每次API调用的延迟和错误:

```python
import logging

logger = logging.getLogger(__name__)

async def call_gemini_with_metrics(request):
    start = time.time()
    try:
        result = await call_gemini(request)
        duration = time.time() - start
        logger.info(f"Gemini call succeeded in {duration:.2f}s")
        return result
    except Exception as e:
        duration = time.time() - start
        logger.error(f"Gemini call failed after {duration:.2f}s: {e}")
        raise
```

### 3. 实现请求队列

使用Celery或RQ实现异步任务队列,避免并发请求:

```python
from celery import Celery

app = Celery('trading', broker='redis://localhost:6379/0')

@app.task(rate_limit='10/m')  # 限制10请求/分钟
def call_llm_task(agent_name, context):
    return agent.act(context)
```

---

## 预期效果

### 方案1 (减少Agent):
- ✅ 立即生效
- ✅ RPM降低60% (15→9)
- ⚠️ 分析质量略微下降

### 方案2 (速率限制器):
- ✅ 彻底解决速率限制
- ✅ 自动重试
- ⏱️ 需要1-2小时开发

### 方案3 (增加超时):
- ✅ 立即生效
- ✅ 解决超时问题
- ⚠️ 不解决速率限制

### 方案4 (更快模型):
- ✅ 立即生效
- ✅ 响应速度提升50%
- ⚠️ 能力可能略微下降

---

## 推荐组合方案

**立即实施:**
1. 减少Agent到3个 (5分钟)
2. 增加timeout到120秒 (5分钟)
3. 切换到gemini-1.5-flash (2分钟)

**本周完成:**
4. 添加简单的RateLimiter (30分钟)
5. 添加重试逻辑 (30分钟)

**下周完成:**
6. 实现Redis分布式限流器 (2小时)
7. 添加监控和日志 (1小时)

---

**创建日期**: 2025-12-03
**问题**: Gemini/DeepSeek 500错误
**根本原因**: 速率限制 + 超时
