# 🐳 yt-dlp Web界面 Docker部署指南

## 📋 部署概览

这是一个完整的yt-dlp Web界面Docker化解决方案，支持：
- 🎥 YouTube视频下载
- 📱 iOS快捷指令集成
- 🛠️ 管理员控制台
- 🗑️ 自动文件清理
- 🔐 用户认证系统

## 🚀 快速部署

### 方法1：使用Portainer（推荐）

1. **在Portainer中创建Stack**
   - 登录Portainer管理界面
   - 进入 `Stacks` → `Add stack`
   - 名称：`yt-dlp-web`
   - 复制 `docker-compose.portainer.yml` 内容

2. **配置环境变量**
   ```yaml
   environment:
     - ADMIN_USERNAME=admin          # 管理员用户名
     - ADMIN_PASSWORD=your_password  # 管理员密码（请修改）
     - SECRET_KEY=your_secret_key    # Flask密钥（请修改）
     - TZ=Asia/Shanghai             # 时区设置
   ```

3. **部署Stack**
   - 点击 `Deploy the stack`
   - 等待部署完成

### 方法2：命令行部署

1. **克隆项目**
   ```bash
   git clone <your-repo-url>
   cd yt-dlp-web
   ```

2. **构建并启动**
   ```bash
   chmod +x build.sh
   ./build.sh
   ```

3. **或者直接使用docker-compose**
   ```bash
   docker-compose up -d
   ```

## 🔧 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `ADMIN_USERNAME` | admin | 管理员用户名 |
| `ADMIN_PASSWORD` | admin123 | 管理员密码 |
| `SECRET_KEY` | dev-key | Flask会话密钥 |
| `DOWNLOAD_FOLDER` | /app/downloads | 下载文件存储路径 |
| `TZ` | Asia/Shanghai | 时区设置 |
| `AUTO_CLEANUP_ENABLED` | true | 是否启用自动清理 |
| `FILE_RETENTION_HOURS` | 24 | 文件保留时间（小时） |
| `MAX_STORAGE_MB` | 2048 | 最大存储空间（MB） |
| `KEEP_RECENT_FILES` | 20 | 保留最近文件数量 |

### 数据卷

| 卷名 | 容器路径 | 说明 |
|------|----------|------|
| `yt-dlp-downloads` | /app/downloads | 下载文件存储 |
| `yt-dlp-config` | /app/config | 配置文件存储 |

### 端口映射

| 容器端口 | 主机端口 | 说明 |
|----------|----------|------|
| 8080 | 8080 | Web界面访问端口 |

## 🌐 访问地址

部署完成后，可以通过以下地址访问：

- **主界面**: http://your-server:8080
- **简单界面**: http://your-server:8080/simple
- **管理控制台**: http://your-server:8080/admin
- **iOS快捷指令帮助**: http://your-server:8080/shortcuts-help

## 🔐 默认登录信息

- **用户名**: admin
- **密码**: admin123

⚠️ **重要**: 生产环境请立即修改默认密码！

## 📱 iOS快捷指令

应用提供了完整的iOS快捷指令支持：

1. **访问帮助页面**: http://your-server:8080/shortcuts-help
2. **下载快捷指令文件**
3. **在iOS设备上安装快捷指令**
4. **配置服务器地址**

## 🛠️ 管理功能

### 存储管理
- 📊 实时存储使用情况
- 🗑️ 手动清理文件
- ⚙️ 清理策略配置

### 预设场景
- **正常使用**: 24小时保留，2GB存储
- **存储受限**: 12小时保留，1GB存储
- **大量下载**: 6小时保留，4GB存储

### 系统管理
- 🔄 版本检查和更新
- 📈 系统状态监控
- 🔧 高级配置选项

## 🔧 常用命令

### Docker命令
```bash
# 查看容器状态
docker ps | grep yt-dlp

# 查看容器日志
docker logs -f yt-dlp-web

# 进入容器
docker exec -it yt-dlp-web bash

# 重启容器
docker restart yt-dlp-web

# 停止容器
docker stop yt-dlp-web

# 删除容器
docker rm yt-dlp-web
```

### docker-compose命令
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f

# 更新服务
docker-compose pull && docker-compose up -d
```

## 🔒 安全建议

### 生产环境部署
1. **修改默认密码**
   ```yaml
   environment:
     - ADMIN_PASSWORD=your_strong_password
   ```

2. **更改密钥**
   ```yaml
   environment:
     - SECRET_KEY=your_random_secret_key
   ```

3. **配置反向代理**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:8080;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

4. **设置防火墙**
   ```bash
   # 只允许特定IP访问
   ufw allow from your_ip to any port 8080
   ```

## 🐛 故障排除

### 常见问题

**1. 容器无法启动**
```bash
# 检查日志
docker logs yt-dlp-web

# 检查端口占用
netstat -tlnp | grep 8080
```

**2. 无法访问Web界面**
```bash
# 检查容器状态
docker ps | grep yt-dlp

# 检查网络连接
curl http://localhost:8080
```

**3. 下载失败**
```bash
# 进入容器检查
docker exec -it yt-dlp-web bash
python -m yt_dlp --version
```

**4. 存储空间不足**
- 访问管理控制台
- 手动清理文件
- 调整清理策略

### 日志分析
```bash
# 实时查看日志
docker logs -f yt-dlp-web

# 查看最近100行日志
docker logs --tail 100 yt-dlp-web

# 查看特定时间的日志
docker logs --since="2024-01-01T00:00:00" yt-dlp-web
```

## 📊 监控和维护

### 健康检查
容器内置健康检查，可以通过以下方式查看：
```bash
docker inspect yt-dlp-web | grep -A 10 Health
```

### 备份数据
```bash
# 备份下载文件
docker cp yt-dlp-web:/app/downloads ./backup/downloads

# 备份配置文件
docker cp yt-dlp-web:/app/config ./backup/config
```

### 更新应用
```bash
# 拉取最新镜像
docker pull yt-dlp-web:latest

# 重新部署
docker-compose down
docker-compose up -d
```

## 🎯 性能优化

### 资源限制
```yaml
services:
  yt-dlp-web:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 存储优化
- 定期清理下载文件
- 配置合适的保留策略
- 监控磁盘使用情况

## 📞 技术支持

如果遇到问题，请：
1. 查看容器日志
2. 检查配置文件
3. 参考故障排除部分
4. 提交Issue（如果是开源项目）

---

🎉 **部署完成后，您就拥有了一个功能完整的YouTube下载服务！**
