# Docker 部署指南

## 🐳 部署方式概览

YT-DLP Web 支持多种 Docker 部署方式：

### 1. Docker Compose（推荐）
- 最简单的部署方式
- 自动处理网络和存储
- 支持一键启停

### 2. 单容器部署
- 适合简单环境
- 资源占用最小
- 配置灵活

### 3. GitHub Actions 构建
- 自动化构建流程
- 支持多种构建策略
- 适合 CI/CD 环境

## 📋 Docker Compose 部署

### 基础部署
```yaml
# docker-compose.yml
version: '3.8'

services:
  yt-dlp-web:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
    environment:
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=admin123
      - DOWNLOAD_DIR=/app/downloads
    restart: unless-stopped
```

### 完整配置
```yaml
# docker-compose.yml
version: '3.8'

services:
  yt-dlp-web:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - BUILD_STRATEGY=hybrid
    ports:
      - "8080:8080"
    volumes:
      - ./downloads:/app/downloads
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      # 基础配置
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=your_secure_password
      - SECRET_KEY=your_secret_key_here
      - DOWNLOAD_DIR=/app/downloads
      
      # 数据库配置
      - DATABASE_URL=sqlite:///data/app.db
      
      # Telegram 配置
      - TELEGRAM_BOT_TOKEN=your_bot_token
      - TELEGRAM_CHAT_ID=your_chat_id
      - TELEGRAM_API_ID=your_api_id
      - TELEGRAM_API_HASH=your_api_hash
      
      # 代理配置（可选）
      - HTTP_PROXY=http://proxy:port
      - HTTPS_PROXY=http://proxy:port
      
      # 日志配置
      - LOG_LEVEL=INFO
      - LOG_FILE=/app/logs/app.log
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 可选：添加 Redis 缓存
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data

  # 可选：添加 Nginx 反向代理
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - yt-dlp-web
    restart: unless-stopped

volumes:
  redis_data:
```

### 启动命令
```bash
# 启动所有服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 完全清理（包括数据）
docker-compose down -v --rmi all
```

## 🏗️ 构建策略

### 1. 运行时下载（runtime）
```dockerfile
# 构建时不下载 yt-dlp，运行时从网络获取
ARG BUILD_STRATEGY=runtime
```
- **优点**：镜像小，总是最新版本
- **缺点**：启动慢，依赖网络
- **适用**：开发环境，网络良好的环境

### 2. 构建时下载（buildtime）
```dockerfile
# 构建时下载并打包 yt-dlp
ARG BUILD_STRATEGY=buildtime
```
- **优点**：启动快，离线可用
- **缺点**：镜像大，版本可能过时
- **适用**：生产环境，网络受限环境

### 3. 混合模式（hybrid）
```dockerfile
# 构建时下载备用版本，运行时尝试更新
ARG BUILD_STRATEGY=hybrid
```
- **优点**：兼顾启动速度和版本新鲜度
- **缺点**：配置稍复杂
- **适用**：大多数生产环境

## 🔧 单容器部署

### 基础运行
```bash
# 拉取镜像
docker pull ghcr.io/your-repo/yt-dlp-web:latest

# 运行容器
docker run -d \
  --name yt-dlp-web \
  -p 8080:8080 \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/data:/app/data \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=admin123 \
  ghcr.io/your-repo/yt-dlp-web:latest
```

### 完整配置运行
```bash
docker run -d \
  --name yt-dlp-web \
  -p 8080:8080 \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=your_secure_password \
  -e SECRET_KEY=your_secret_key \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -e TELEGRAM_CHAT_ID=your_chat_id \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  --health-cmd="curl -f http://localhost:8080/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  ghcr.io/your-repo/yt-dlp-web:latest
```

## 🌐 GitHub Actions 构建

### 手动触发构建
1. 访问你的 GitHub 仓库
2. 点击 "Actions" 标签
3. 选择 "Docker Build and Push"
4. 点击 "Run workflow"
5. 配置构建参数：
   - **构建策略**：runtime/buildtime/hybrid
   - **运行测试**：是否执行功能测试
   - **推送镜像**：是否推送到 GitHub Container Registry

### 构建参数说明
```yaml
# 构建策略
build_strategy: 
  - runtime: 运行时下载 yt-dlp
  - buildtime: 构建时下载 yt-dlp
  - hybrid: 混合模式（推荐）

# 是否运行测试
run_tests: true/false

# 是否推送镜像
push_image: true/false
```

### 使用构建的镜像
```bash
# 拉取最新镜像
docker pull ghcr.io/your-username/yt-dlp-web:latest

# 或拉取特定版本
docker pull ghcr.io/your-username/yt-dlp-web:v1.0.0
```

## 📁 目录结构

### 推荐的目录布局
```
yt-dlp-web/
├── docker-compose.yml
├── .env
├── downloads/          # 下载文件存储
├── data/              # 数据库和配置
│   ├── app.db
│   └── cookies/
├── logs/              # 日志文件
│   └── app.log
├── nginx.conf         # Nginx 配置（可选）
└── ssl/               # SSL 证书（可选）
    ├── cert.pem
    └── key.pem
```

### 权限设置
```bash
# 确保目录权限正确
chmod 755 downloads data logs
chmod 644 .env

# 如果使用 SSL
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem
```

## 🔒 安全配置

### 环境变量安全
```bash
# 生成安全的密钥
openssl rand -hex 32

# 设置在 .env 文件中
SECRET_KEY=your_generated_secret_key
ADMIN_PASSWORD=your_secure_password
```

### 网络安全
```yaml
# docker-compose.yml 中的网络配置
networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### SSL/TLS 配置
```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://yt-dlp-web:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📊 监控和维护

### 健康检查
```bash
# 检查容器健康状态
docker ps --format "table {{.Names}}\t{{.Status}}"

# 查看健康检查日志
docker inspect yt-dlp-web | grep -A 10 Health
```

### 日志管理
```bash
# 查看实时日志
docker logs -f yt-dlp-web

# 限制日志大小
docker run --log-opt max-size=10m --log-opt max-file=3 ...
```

### 备份和恢复
```bash
# 备份数据
tar -czf backup-$(date +%Y%m%d).tar.gz downloads data

# 恢复数据
tar -xzf backup-20240101.tar.gz
```

## 🚀 性能优化

### 资源限制
```yaml
# docker-compose.yml
services:
  yt-dlp-web:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
```

### 缓存优化
```yaml
# 添加 Redis 缓存
services:
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

---

**📖 更多信息请参考：**
- [环境配置指南](ENVIRONMENT_SETUP.md)
- [故障排除指南](TROUBLESHOOTING.md)
- [性能优化指南](PERFORMANCE_OPTIMIZATION.md)
