# 快速部署指南

## 🚀 5分钟快速部署

### 前置要求
- Docker 和 Docker Compose
- Git
- 至少 2GB 可用内存

### 步骤一：获取代码
```bash
# 克隆项目
git clone https://github.com/your-repo/yt-dlp-web.git
cd yt-dlp-web

# 或者下载 ZIP 包并解压
```

### 步骤二：配置环境
```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件（可选）
nano .env
```

**重要配置项**：
```env
# 管理员账号密码
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password

# 应用端口
PORT=8080

# 下载目录
DOWNLOAD_DIR=./downloads

# Telegram 配置（可选）
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 步骤三：启动服务
```bash
# 启动所有服务
docker-compose up -d

# 查看启动状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 步骤四：访问应用
1. 打开浏览器访问：`http://localhost:8080`
2. 使用默认账号登录：
   - 用户名：`admin`
   - 密码：`admin123`（或你在 .env 中设置的密码）

### 步骤五：测试下载
1. 在首页输入视频链接，例如：
   ```
   https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```
2. 选择下载格式和质量
3. 点击"开始下载"
4. 在"文件管理"页面查看下载结果

## 🔧 常用命令

### 服务管理
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f yt-dlp-web
```

### 数据管理
```bash
# 备份下载文件
cp -r downloads downloads_backup

# 清理容器和镜像
docker-compose down --rmi all --volumes

# 重新构建镜像
docker-compose build --no-cache
```

### 更新应用
```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker-compose up -d --build
```

## 🛠️ 故障排除

### 常见问题

#### 1. 端口被占用
```bash
# 检查端口占用
netstat -tulpn | grep 8080

# 修改端口
# 编辑 .env 文件，修改 PORT=8081
# 或者编辑 docker-compose.yml
```

#### 2. 权限问题
```bash
# 确保下载目录有写权限
chmod 755 downloads

# 如果是 Linux，可能需要调整用户权限
sudo chown -R $USER:$USER downloads
```

#### 3. 内存不足
```bash
# 检查内存使用
docker stats

# 增加 swap 空间（Linux）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. 网络问题
```bash
# 测试网络连接
curl -I https://www.youtube.com

# 如果在中国大陆，可能需要配置代理
# 编辑 .env 文件添加：
# HTTP_PROXY=http://your-proxy:port
# HTTPS_PROXY=http://your-proxy:port
```

### 健康检查
```bash
# 检查应用健康状态
curl http://localhost:8080/health

# 预期响应：
# {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
```

### 日志分析
```bash
# 查看错误日志
docker-compose logs yt-dlp-web | grep ERROR

# 查看下载日志
docker-compose logs yt-dlp-web | grep "Download"

# 导出日志到文件
docker-compose logs yt-dlp-web > app.log
```

## 📱 移动端访问

### iOS Safari
1. 访问 `http://your-server-ip:8080`
2. 点击分享按钮 → "添加到主屏幕"
3. 应用会以 PWA 模式运行

### Android Chrome
1. 访问 `http://your-server-ip:8080`
2. Chrome 会提示"添加到主屏幕"
3. 点击"添加"即可

## 🔄 下一步

- [配置 Telegram 推送](TELEGRAM_INTEGRATION.md)
- [设置 Cookies 管理](COOKIES_MANAGEMENT.md)
- [查看完整 API 文档](API_DOCUMENTATION.md)
- [了解高级配置](ADVANCED_CONFIGURATION.md)

---

**🎉 恭喜！你已经成功部署了 YT-DLP Web！**
