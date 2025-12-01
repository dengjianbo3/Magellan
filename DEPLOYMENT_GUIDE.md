# Magellan 服务器部署指南

本指南详细说明如何在远程服务器上部署 Magellan AI 投资分析平台。

## 目录

1. [系统要求](#系统要求)
2. [快速部署](#快速部署)
3. [详细部署步骤](#详细部署步骤)
4. [环境变量配置](#环境变量配置)
5. [前端构建与部署](#前端构建与部署)
6. [Nginx 反向代理配置](#nginx-反向代理配置)
7. [SSL 证书配置](#ssl-证书配置)
8. [常用运维命令](#常用运维命令)
9. [故障排除](#故障排除)

---

## 系统要求

### 硬件要求
- **CPU**: 4 核以上（推荐 8 核）
- **内存**: 16GB 以上（推荐 32GB）
- **磁盘**: 100GB 以上 SSD

### 软件要求
- **操作系统**: Ubuntu 22.04 LTS / Debian 12 / CentOS 8+
- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **Node.js**: 18+ (用于构建前端)
- **Git**: 2.30+

---

## 快速部署

```bash
# 1. 克隆代码
git clone https://github.com/YOUR_REPO/Magellan.git
cd Magellan

# 2. 配置环境变量
cp .env.example .env
vim .env  # 填入你的 API Keys

# 3. 启动后端服务
docker-compose up -d

# 4. 构建前端
cd frontend
npm install
npm run build

# 5. 查看服务状态
docker-compose ps
```

---

## 详细部署步骤

### Step 1: 安装 Docker 和 Docker Compose

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# 添加 Docker GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker 并设置开机自启
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组（需要重新登录生效）
sudo usermod -aG docker $USER
```

### Step 2: 安装 Node.js

```bash
# 使用 NodeSource 安装 Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 验证安装
node --version
npm --version
```

### Step 3: 克隆项目代码

```bash
cd /opt
sudo git clone https://github.com/YOUR_REPO/Magellan.git
sudo chown -R $USER:$USER Magellan
cd Magellan
```

### Step 4: 配置环境变量

```bash
cp .env.example .env
vim .env
```

详细配置见下方 [环境变量配置](#环境变量配置) 部分。

### Step 5: 启动后端服务

```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f report_orchestrator
```

### Step 6: 构建前端

```bash
cd frontend
npm install
npm run build
```

构建产物在 `frontend/dist` 目录下。

---

## 环境变量配置

在 `.env` 文件中配置以下变量：

```bash
# ========== 必填项 ==========

# Google Gemini API Key (从 Google AI Studio 获取)
GOOGLE_API_KEY="your_google_api_key"

# Gemini 模型名称
GEMINI_MODEL_NAME="gemini-2.0-flash-exp"

# Tavily 搜索 API Key (从 tavily.com 获取)
TAVILY_API_KEY="your_tavily_api_key"

# ========== 可选项 ==========

# JWT 密钥 (用于认证服务，生产环境请修改)
JWT_SECRET_KEY="your-super-secret-key-change-in-production"

# OKX 模拟交易 API (如需使用自动交易功能)
OKX_API_KEY="your_okx_api_key"
OKX_SECRET_KEY="your_okx_secret_key"
OKX_PASSPHRASE="your_okx_passphrase"
OKX_DEMO_MODE="true"

# Moonshot API Key (备选 LLM 提供商)
MOONSHOT_API_KEY="your_moonshot_api_key"

# DeepSeek API Key (备选 LLM 提供商)
DEEPSEEK_API_KEY="your_deepseek_api_key"

# 代理配置 (如需要)
# HTTP_PROXY="http://your_proxy:port"
# HTTPS_PROXY="http://your_proxy:port"
```

---

## 前端构建与部署

### 开发模式

```bash
cd frontend
npm install
npm run dev  # 运行在 http://localhost:5173
```

### 生产构建

```bash
cd frontend
npm install
npm run build
```

构建后的静态文件在 `frontend/dist` 目录下，可以使用 Nginx 托管。

---

## Nginx 反向代理配置

### 安装 Nginx

```bash
sudo apt install -y nginx
```

### 配置文件

创建 `/etc/nginx/sites-available/magellan`:

```nginx
upstream magellan_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名

    # 前端静态文件
    location / {
        root /opt/Magellan/frontend/dist;
        try_files $uri $uri/ /index.html;

        # 缓存静态资源
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # API 代理
    location /api/ {
        proxy_pass http://magellan_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 超时设置
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # 文件上传限制
    client_max_body_size 100M;
}
```

### 启用配置

```bash
sudo ln -s /etc/nginx/sites-available/magellan /etc/nginx/sites-enabled/
sudo nginx -t  # 测试配置
sudo systemctl reload nginx
```

---

## SSL 证书配置

### 使用 Certbot 获取免费 SSL 证书

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期测试
sudo certbot renew --dry-run
```

---

## 常用运维命令

### 服务管理

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启单个服务
docker-compose restart report_orchestrator

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f                     # 所有服务日志
docker-compose logs -f report_orchestrator # 单个服务日志
docker-compose logs --tail=100 llm_gateway # 最近100行

# 重新构建并启动
docker-compose up -d --build report_orchestrator
```

### 数据备份

```bash
# 备份 PostgreSQL 数据
docker exec magellan-postgres pg_dump -U magellan magellan > backup_$(date +%Y%m%d).sql

# 备份 Redis 数据
docker exec magellan-redis redis-cli BGSAVE
docker cp magellan-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb

# 备份所有 Docker 卷
docker-compose down
sudo tar -czvf magellan_volumes_$(date +%Y%m%d).tar.gz /var/lib/docker/volumes/magellan_*
```

### 更新部署

```bash
cd /opt/Magellan

# 拉取最新代码
git pull origin main

# 重新构建后端
docker-compose up -d --build

# 重新构建前端
cd frontend
npm install
npm run build
```

### 清理资源

```bash
# 清理未使用的 Docker 资源
docker system prune -a

# 清理日志文件
docker-compose logs --no-color > logs_backup.txt
docker system prune --volumes
```

---

## 故障排除

### 1. 服务无法启动

```bash
# 检查 Docker 日志
docker-compose logs report_orchestrator

# 检查端口占用
sudo netstat -tulpn | grep :8000

# 检查 Docker 网络
docker network ls
docker network inspect magellan_default
```

### 2. LLM 调用失败

```bash
# 检查 API Key 配置
docker exec magellan-report_orchestrator env | grep API

# 测试 LLM Gateway
curl http://localhost:8003/providers

# 检查 LLM Gateway 日志
docker-compose logs llm_gateway
```

### 3. WebSocket 连接失败

```bash
# 检查 Nginx WebSocket 配置
# 确保 proxy_http_version 和 Upgrade 头设置正确

# 检查后端 WebSocket 服务
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     http://localhost:8000/api/trading/ws/test
```

### 4. 内存不足

```bash
# 检查内存使用
docker stats

# 限制容器内存
# 在 docker-compose.yml 中添加:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

### 5. 磁盘空间不足

```bash
# 检查磁盘使用
df -h

# 清理 Docker 资源
docker system prune -a --volumes

# 清理日志
truncate -s 0 /var/lib/docker/containers/*/*-json.log
```

---

## 端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| report_orchestrator | 8000 | 主 API 服务 |
| file_service | 8001 | 文件上传服务 |
| llm_gateway | 8003 | LLM 网关 |
| excel_parser | 8004 | Excel 解析 |
| word_parser | 8005 | Word 解析 |
| external_data_service | 8006 | 外部数据服务 |
| auth_service | 8007 | 认证服务 |
| user_service | 8008 | 用户服务 |
| internal_knowledge_service | 8009 | 内部知识库 |
| web_search_service | 8010 | 网络搜索服务 |
| chroma | 8011 | 向量数据库 (ChromaDB) |
| kafka-ui | 8080 | Kafka 管理界面 |
| redis | 6380 | Redis (外部访问) |
| postgres | 5433 | PostgreSQL (外部访问) |
| qdrant | 6333 | Qdrant 向量数据库 |

---

## 服务架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx (80/443)                          │
│                    (反向代理 + 静态文件托管)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
              ▼                                   ▼
┌─────────────────────────┐         ┌─────────────────────────────┐
│    Frontend (Vite)      │         │   report_orchestrator:8000  │
│    /opt/.../dist        │         │   (主 API + WebSocket)       │
└─────────────────────────┘         └─────────────────────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
        ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
        │  llm_gateway:8003 │     │   redis:6379      │     │  postgres:5432    │
        │  (LLM 调用网关)    │     │   (会话存储)       │     │  (用户认证数据)    │
        └───────────────────┘     └───────────────────┘     └───────────────────┘
```

---

## 监控与告警

### 基础监控脚本

创建 `/opt/Magellan/monitor.sh`:

```bash
#!/bin/bash

# 检查所有容器是否运行
UNHEALTHY=$(docker-compose ps | grep -v "Up" | grep -v "NAME" | wc -l)

if [ "$UNHEALTHY" -gt 0 ]; then
    echo "$(date): $UNHEALTHY containers are not healthy" >> /var/log/magellan_monitor.log
    # 发送告警邮件或消息
    # curl -X POST "https://your-webhook-url" -d "message=Magellan unhealthy containers: $UNHEALTHY"
fi

# 检查磁盘使用率
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "$(date): Disk usage is $DISK_USAGE%" >> /var/log/magellan_monitor.log
fi
```

添加到 crontab:

```bash
# 每5分钟检查一次
*/5 * * * * /opt/Magellan/monitor.sh
```

---

## 联系与支持

如有部署问题，请：
1. 查看项目 Issues
2. 提交新的 Issue 描述问题
3. 联系项目维护者

---

*最后更新: 2024-12*
