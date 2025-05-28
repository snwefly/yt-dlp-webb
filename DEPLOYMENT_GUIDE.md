# YT-DLP Web 部署指南

本指南将帮助您安全地部署 YT-DLP Web 应用程序。

## 📋 前置要求

### 系统要求
- Linux 服务器 (Ubuntu 20.04+ 推荐)
- Docker 20.10+
- Docker Compose 2.0+
- 至少 2GB RAM
- 至少 10GB 可用磁盘空间

### 网络要求
- 开放端口 8080 (或自定义端口)
- 如果使用 HTTPS，开放端口 443
- 确保服务器可以访问互联网

## 🚀 快速部署

### 1. 克隆仓库
```bash
git clone https://github.com/your-username/yt-dlp-web-deploy.git
cd yt-dlp-web-deploy
```

### 2. 初始化环境
```bash
chmod +x deploy-enhanced.sh
./deploy-enhanced.sh init
```

### 3. 配置环境变量
```bash
cp .env.production .env
nano .env
```

**重要**: 修改以下配置项：
- `ADMIN_USERNAME`: 管理员用户名
- `ADMIN_PASSWORD`: 管理员密码 (使用强密码)
- `SECRET_KEY`: Flask 密钥 (生成随机字符串)
- `DOMAIN`: 你的域名

### 4. 部署服务
```bash
./deploy-enhanced.sh deploy
```

### 5. 验证部署
```bash
./deploy-enhanced.sh status
```

访问 `http://your-server-ip:8080` 验证服务是否正常运行。

## 🔧 生产环境配置

### 1. 使用 GitHub Container Registry 镜像

编辑 `docker-compose.prod.yml`，确保使用正确的镜像：
```yaml
services:
  yt-dlp-web:
    image: ghcr.io/your-username/yt-dlp-web-deploy:latest
```

### 2. 配置反向代理 (推荐)

#### 使用 Nginx
创建 `nginx.conf`:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 使用 Traefik
如果使用 Traefik，配置已包含在 `docker-compose.prod.yml` 中。

### 3. 配置 HTTPS

#### 使用 Let's Encrypt
```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 4. 配置防火墙
```bash
# 允许 HTTP 和 HTTPS
sudo ufw allow 80
sudo ufw allow 443

# 如果直接暴露应用端口
sudo ufw allow 8080

# 启用防火墙
sudo ufw enable
```

## 🔒 安全配置

### 1. 强化密码策略
- 使用至少 12 位的强密码
- 包含大小写字母、数字和特殊字符
- 定期更换密码

### 2. 限制访问
```bash
# 仅允许特定 IP 访问管理功能
sudo ufw allow from YOUR_IP_ADDRESS to any port 8080
```

### 3. 配置日志监控
```bash
# 查看应用日志
./deploy-enhanced.sh logs

# 设置日志轮转
sudo nano /etc/logrotate.d/yt-dlp-web
```

### 4. 定期备份
```bash
# 手动备份
./deploy-enhanced.sh backup

# 设置自动备份 (crontab)
0 2 * * * cd /path/to/yt-dlp-web-deploy && ./deploy-enhanced.sh backup
```

## 📊 监控和维护

### 1. 健康检查
```bash
# 检查服务状态
./deploy-enhanced.sh status

# 查看容器健康状态
docker ps
```

### 2. 日志管理
```bash
# 查看实时日志
./deploy-enhanced.sh logs

# 查看特定服务日志
./deploy-enhanced.sh logs yt-dlp-web-prod
```

### 3. 更新服务
```bash
# 更新到最新版本
./deploy-enhanced.sh update

# 重启服务
./deploy-enhanced.sh restart
```

### 4. 清理系统
```bash
# 清理未使用的 Docker 资源
./deploy-enhanced.sh cleanup
```

## 🔄 CI/CD 集成

### 1. GitHub Actions 自动部署

创建 `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Production

on:
  push:
    tags: ['v*']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to server
      uses: appleboy/ssh-action@v0.1.5
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /path/to/yt-dlp-web-deploy
          git pull
          ./deploy-enhanced.sh update
```

### 2. 配置 Secrets
在 GitHub 仓库设置中添加：
- `HOST`: 服务器 IP 地址
- `USERNAME`: SSH 用户名
- `SSH_KEY`: SSH 私钥

## 🛠️ 故障排除

### 常见问题

#### 1. 容器无法启动
```bash
# 查看详细日志
docker logs yt-dlp-web-prod

# 检查配置文件
docker-compose -f docker-compose.prod.yml config
```

#### 2. 无法访问 Web 界面
```bash
# 检查端口是否开放
sudo netstat -tlnp | grep 8080

# 检查防火墙规则
sudo ufw status
```

#### 3. 下载失败
```bash
# 检查网络连接
docker exec yt-dlp-web-prod curl -I https://www.youtube.com

# 检查 yt-dlp 版本
docker exec yt-dlp-web-prod yt-dlp --version
```

#### 4. 存储空间不足
```bash
# 检查磁盘使用情况
df -h

# 清理下载文件
./deploy-enhanced.sh cleanup
```

### 性能优化

#### 1. 调整资源限制
编辑 `docker-compose.prod.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '2.0'
```

#### 2. 配置并发限制
在 `.env` 中调整：
```bash
MAX_CONCURRENT_DOWNLOADS=5
MAX_FILE_SIZE=10737418240  # 10GB
```

## 📞 支持

如果遇到问题：

1. 查看 [故障排除文档](TROUBLESHOOTING.md)
2. 检查 [GitHub Issues](https://github.com/your-username/yt-dlp-web-deploy/issues)
3. 提交新的 Issue 并包含：
   - 错误日志
   - 系统信息
   - 复现步骤

## 📚 相关文档

- [安全改进说明](SECURITY_IMPROVEMENTS.md)
- [Docker 部署文档](DOCKER_DEPLOY.md)
- [API 文档](API_DOCS.md)
- [开发指南](DEVELOPMENT.md)
