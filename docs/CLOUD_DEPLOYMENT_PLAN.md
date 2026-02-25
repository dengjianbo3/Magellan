# Magellan 云服务器部署方案（单机生产 / Demo 级）

> 目标：在 1 台云服务器上稳定部署当前 Magellan 系统，用于对外演示与小规模真实使用。  
> 范围：基于当前仓库的 Docker Compose 架构，不改业务代码。

## 1. 部署目标与原则

- 部署形态：单机 Docker Compose + Nginx 反向代理 + HTTPS。
- 可用性目标：服务可重启恢复，支持快速回滚。
- 安全原则：仅暴露 `80/443/22`，后端服务全部走内网或本机回环。
- 运维原则：日志可查、健康可检、升级可回退。

## 2. 云资源规划

### 2.1 最低可用（Demo）

- CPU：4 vCPU
- 内存：8 GB
- 磁盘：100 GB SSD
- 带宽：5 Mbps+

### 2.2 推荐（更稳定）

- CPU：8 vCPU
- 内存：16 GB
- 磁盘：200 GB SSD
- 带宽：10 Mbps+

## 3. 域名与网络规划

- 域名：`magellan.yourdomain.com`
- DNS：A 记录指向云服务器公网 IP
- 安全组放行：`22`, `80`, `443`
- 其余端口全部关闭外网访问

## 4. 服务器基础环境

以 Ubuntu 22.04 LTS 为例：

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release git ufw nginx certbot python3-certbot-nginx

# Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER

# Node.js 20 (用于前端构建)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 防火墙
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

> 执行完 `usermod -aG docker` 后，重新登录一次 SSH 会话。

## 5. 代码与目录约定

```bash
sudo mkdir -p /opt/magellan
sudo chown -R $USER:$USER /opt/magellan
cd /opt/magellan

git clone git@github.com:dengjianbo3/Magellan.git .
git checkout dev
```

建议目录：

- 代码目录：`/opt/magellan`
- 持久化卷：Docker named volumes（由 compose 管理）
- 备份目录：`/opt/magellan/backups`

## 6. 环境变量配置（核心）

```bash
cd /opt/magellan
cp .env.example .env
```

重点配置项（必须）：

- `GOOGLE_API_KEY`
- `DEFAULT_LLM_PROVIDER=gemini`
- `GEMINI_MODEL_NAME=gemini-3.1-pro-preview`
- `GEMINI_FLASH_MODEL_NAME=gemini-3-flash-preview`（建议补充）
- `GEMINI_ENABLE_GOOGLE_SEARCH=true`
- `JWT_SECRET_KEY`（必须更换强随机值）
- `CORS_ALLOW_ORIGINS=https://magellan.yourdomain.com`
- `REPORT_ORCH_REQUIRE_REDIS=true`
- `REPORT_STORAGE_ALLOW_MEMORY_FALLBACK=false`
- `LLM_EXPOSE_PROVIDER_INFO=false`

可按你的策略配置：

- `USE_OKX_TRADING=false`（演示环境建议）
- `OKX_DEMO_MODE=true`
- `TAVILY_API_KEY` / `SERPER_API_KEY`（如已停用可留空）

## 7. 生产编排策略

当前 `docker-compose.yml` 偏开发模式（含 `--reload` 与代码挂载）。  
生产建议通过覆盖文件关闭开发特性。

创建 `docker-compose.prod.yml`（示例）：

```yaml
services:
  report_orchestrator:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    volumes: []
    ports:
      - "127.0.0.1:8000:8000"
  llm_gateway:
    volumes: []
    ports:
      - "127.0.0.1:8003:8003"
  auth_service:
    volumes: []
    ports:
      - "127.0.0.1:8007:8007"
  user_service:
    volumes: []
  file_service:
    volumes: []
  excel_parser:
    volumes: []
  word_parser:
    volumes: []
```

> 上面是示意。你也可以保留现状端口映射，但安全性会下降。

## 8. 启动后端服务

建议先只拉起必须服务，再扩展：

```bash
cd /opt/magellan

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build \
  report_orchestrator llm_gateway auth_service user_service \
  file_service excel_parser word_parser external_data_service \
  internal_knowledge_service web_search_service redis qdrant postgres
```

健康检查：

```bash
docker compose ps
curl -f http://127.0.0.1:8000/health
curl -f http://127.0.0.1:8003/health
curl -f http://127.0.0.1:8007/health
```

## 9. 前端部署（生产静态站点）

```bash
cd /opt/magellan/frontend
npm ci
npm run build
```

构建产物：`/opt/magellan/frontend/dist`

## 10. Nginx 反向代理与 SPA 托管

创建 `/etc/nginx/sites-available/magellan.conf`：

```nginx
server {
    listen 80;
    server_name magellan.yourdomain.com;

    root /opt/magellan/frontend/dist;
    index index.html;

    # Auth
    location /api/auth/ {
        proxy_pass http://127.0.0.1:8007/api/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # LLM Gateway
    location /api/llm/ {
        proxy_pass http://127.0.0.1:8003/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Trading WS
    location /api/trading/ws/ {
        proxy_pass http://127.0.0.1:8000/api/trading/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Generic WS routes (/ws/roundtable, /ws/expert-chat, /ws/v2/analysis/...)
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Default API -> report_orchestrator
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SPA
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/magellan.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 11. HTTPS（Let’s Encrypt）

```bash
sudo certbot --nginx -d magellan.yourdomain.com
sudo certbot renew --dry-run
```

> 前端和 WebSocket 建议全部使用 `https + wss`，避免浏览器 Mixed Content 问题。

## 12. 验证清单（上线前）

- 页面可打开：`https://magellan.yourdomain.com`
- 登录可用：`/api/auth/*` 正常
- 专家群聊可用：`/ws/expert-chat` 正常升级
- 头脑风暴可用：`/ws/roundtable` 正常
- 自动交易 WS 可连通：`/api/trading/ws/*` 正常
- 模型切换可用：`/api/llm/gemini/model-tier` 正常
- LLM 健康：`/api/llm/health` 返回 `gemini_available=true`

## 13. 发布与回滚流程

### 13.1 发布

```bash
cd /opt/magellan
git fetch origin
git checkout dev
git pull origin dev

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

cd frontend
npm ci && npm run build
sudo systemctl reload nginx
```

### 13.2 快速回滚

```bash
cd /opt/magellan
git log --oneline -n 5
git checkout <last_good_commit>

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

cd frontend
npm ci && npm run build
sudo systemctl reload nginx
```

## 14. 运维与监控建议

常用命令：

```bash
# 容器状态
docker compose ps

# 查看日志
docker compose logs -f report_orchestrator
docker compose logs -f llm_gateway
docker compose logs -f auth_service

# 重启单服务
docker compose restart report_orchestrator
```

建议接入：

- 主机监控：CPU / MEM / Disk / Load
- 容器监控：容器重启次数、健康状态
- 日志采集：Nginx + FastAPI 关键错误
- 告警：5xx 比例、WS 连接失败率、LLM 超时率

## 15. 备份策略

需要备份的数据：

- `postgres_data`
- `redis_data`（会话与状态）
- `qdrant_storage`（知识库向量）
- `.env`（脱敏加密保存）

建议每日快照 + 每周异地备份。

## 16. 已知风险与规避

- 风险：`.env` 泄露会导致 API Key/交易密钥风险。  
  规避：最小权限、定期轮换、禁止入库。
- 风险：开发参数（`--reload`、代码挂载）用于生产导致不稳定。  
  规避：使用 `docker-compose.prod.yml` 覆盖。
- 风险：过多公网暴露端口。  
  规避：仅暴露 80/443，内部服务绑定 `127.0.0.1`。

## 17. 上线后 24 小时观察项

- 平均响应时延与 P95
- WebSocket 断连重连次数
- `llm_gateway` 超时与 4xx/5xx 比例
- `report_orchestrator` 内存峰值
- 磁盘增长速率（日志/卷）

---

如果你希望，我可以在下一步直接给你补两份可直接落地的文件：

1. `docker-compose.prod.yml`（生产覆盖）  
2. `deploy/nginx/magellan.conf`（可直接复制到服务器）

这样你可以直接按文档命令完成上线。
