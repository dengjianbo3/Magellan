# Deploy Dashboard to Remote Server

## Quick Deploy

在远程服务器上执行以下命令:

```bash
cd /root/trading-standalone
git pull origin exp
docker compose up -d web_dashboard
```

## Access Dashboard

部署完成后,通过以下URL访问dashboard:

```
http://45.76.159.149:8888/
```

## 手动部署步骤

如果需要手动部署,请按以下步骤操作:

### 1. 在本地运行部署脚本

```bash
cd /Users/dengjianbo/Documents/Magellan/trading-standalone
chmod +x deploy_dashboard.sh
./deploy_dashboard.sh
```

### 2. 或者手动拷贝文件

```bash
scp docker-compose.yml status.html root@45.76.159.149:/root/trading-standalone/
ssh root@45.76.159.149 "cd /root/trading-standalone && docker compose up -d web_dashboard"
```

## 验证部署

### 1. 检查容器状态

```bash
docker ps | grep trading-dashboard
```

应该看到类似输出:
```
trading-dashboard   nginx:alpine   "nginx -g 'daemon of…"   Up 5 seconds   0.0.0.0:8888->80/tcp
```

### 2. 测试API连接

从本地测试:
```bash
curl http://45.76.159.149:8888/
```

应该返回HTML内容。

### 3. 在浏览器中访问

打开浏览器,访问:
```
http://45.76.159.149:8888/
```

## Troubleshooting

### Dashboard无法访问

1. 检查容器是否运行:
   ```bash
   docker ps | grep trading-dashboard
   ```

2. 检查端口是否监听:
   ```bash
   netstat -tlnp | grep 8888
   ```

3. 检查防火墙规则:
   ```bash
   iptables -L -n | grep 8888
   ```

4. 查看nginx日志:
   ```bash
   docker logs trading-dashboard
   ```

### 数据不显示

1. 确认trading_service正常运行:
   ```bash
   docker ps | grep trading-service
   curl http://localhost:8000/api/trading/status
   ```

2. 在浏览器中打开开发者工具(F12),查看Console和Network标签是否有错误

3. 强制刷新浏览器: Ctrl+Shift+R (Windows/Linux) 或 Cmd+Shift+R (Mac)

### CORS错误

如果浏览器Console显示CORS错误,需要在服务器上配置nginx:

```bash
# 创建nginx配置文件
cat > /root/trading-standalone/nginx.conf <<'EOF'
server {
    listen 80;
    server_name _;

    location / {
        root /usr/share/nginx/html;
        index index.html;
    }

    # Proxy API requests to avoid CORS
    location /api/ {
        proxy_pass http://45.76.159.149:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# 更新docker-compose.yml中的nginx配置
# 添加以下volume映射:
# - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
```

然后重启nginx:
```bash
docker compose restart web_dashboard
```
