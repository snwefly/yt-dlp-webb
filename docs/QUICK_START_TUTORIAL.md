# GitHub 网络版 yt-dlp Web - 快速入门教程

## 🚀 5分钟快速开始

### 前提条件

确保您的系统已安装：
- Docker 20.10+
- Docker Compose 1.29+
- Git

### 第一步：获取项目

```bash
# 克隆项目（假设您已有项目文件）
cd ~/
mkdir yt-dlp-web-github
cd yt-dlp-web-github

# 复制所有项目文件到此目录
```

### 第二步：配置环境

```bash
# 复制环境配置
cp .env.github .env

# 快速配置（可选）
cat > .env << EOF
# 基础配置
YTDLP_SOURCE=github_release
YTDLP_VERSION=latest
ENVIRONMENT=production

# 应用配置
WEB_PORT=8080
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# 系统配置
TZ=Asia/Shanghai
DEBUG=false
LOG_LEVEL=INFO
EOF
```

### 第三步：一键启动

```bash
# 方式一：使用构建脚本（推荐）
chmod +x build-github.sh
./build-github.sh

# 方式二：使用 Docker Compose
docker-compose -f docker-compose.github.yml up -d
```

### 第四步：验证安装

```bash
# 检查容器状态
docker-compose -f docker-compose.github.yml ps

# 检查日志
docker-compose -f docker-compose.github.yml logs -f

# 测试访问
curl -I http://localhost:8080
```

### 第五步：开始使用

1. **访问应用**: http://localhost:8080
2. **登录账号**: admin / your-secure-password
3. **下载测试**: 输入视频URL，点击下载

## 📱 iOS 快捷指令设置

### 快速设置

1. **获取快捷指令链接**
   ```
   访问: http://localhost:8080/api/shortcuts/install
   或扫描应用内二维码
   ```

2. **安装快捷指令**
   - 点击链接自动安装
   - 或手动创建（见下方）

3. **测试使用**
   - 分享任意视频链接
   - 选择"yt-dlp 下载"
   - 等待下载完成

### 手动创建快捷指令

如果自动安装失败，可以手动创建：

1. **打开快捷指令应用**
2. **创建新快捷指令**
3. **添加以下动作**：

```
动作1: 获取剪贴板
动作2: 获取文本输入 (如果剪贴板为空)
动作3: 获取网页内容
  - URL: http://your-server:8080/api/shortcuts/download
  - 方法: POST
  - 请求体: JSON
  - 内容: 
    {
      "url": "[剪贴板内容]",
      "format": "mp4",
      "quality": "best"
    }
动作4: 显示通知
  - 标题: "下载开始"
  - 内容: "视频正在下载中..."
```

## 🔧 常见问题快速解决

### 问题1: 构建失败

```bash
# 症状: Docker 构建失败
# 解决:
docker system prune -a  # 清理缓存
./build-github.sh --no-cache --source local  # 使用本地源
```

### 问题2: 无法访问

```bash
# 症状: 无法访问 http://localhost:8080
# 检查:
docker ps  # 确认容器运行
docker logs yt-dlp-web-github  # 查看日志
netstat -tlnp | grep 8080  # 检查端口
```

### 问题3: 下载失败

```bash
# 症状: 视频下载失败
# 解决:
docker exec -it yt-dlp-web-github python -c "import yt_dlp; print(yt_dlp.__version__)"
# 如果失败，重新构建:
./build-github.sh --no-cache
```

### 问题4: 权限错误

```bash
# 症状: Permission denied
# 解决:
docker-compose -f docker-compose.github.yml down
docker volume rm yt-dlp-web-deploy_downloads
docker-compose -f docker-compose.github.yml up -d
```

## 🎯 不同场景的快速配置

### 场景1: 开发测试

```bash
# 使用本地文件，快速迭代
cat > .env << EOF
YTDLP_SOURCE=local
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
EOF

./build-github.sh --source local --no-cache
```

### 场景2: 生产部署

```bash
# 使用 GitHub Release，稳定版本
cat > .env << EOF
YTDLP_SOURCE=github_release
YTDLP_VERSION=2024.12.13
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
ADMIN_PASSWORD=very-secure-password
EOF

./build-github.sh --source github_release --test --push
```

### 场景3: 内网环境

```bash
# 使用 PyPI 包，无需 GitHub 访问
cat > .env << EOF
YTDLP_SOURCE=pypi
ENVIRONMENT=production
DEBUG=false
EOF

./build-github.sh --source pypi
```

### 场景4: 自定义版本

```bash
# 使用特定版本
cat > .env << EOF
YTDLP_SOURCE=github_release
YTDLP_VERSION=2024.11.18
ENVIRONMENT=production
EOF

./build-github.sh --source github_release --version 2024.11.18
```

## 📊 监控和维护

### 基础监控

```bash
# 查看容器状态
docker-compose -f docker-compose.github.yml ps

# 查看资源使用
docker stats yt-dlp-web-github

# 查看日志
docker-compose -f docker-compose.github.yml logs -f --tail=100
```

### 健康检查

```bash
# 应用健康检查
curl http://localhost:8080/health

# yt-dlp 功能测试
docker exec yt-dlp-web-github python -c "
import yt_dlp
ydl = yt_dlp.YoutubeDL({'quiet': True})
print('yt-dlp 正常工作')
"
```

### 简单备份

```bash
# 备份下载文件
docker run --rm \
  -v yt-dlp-web-deploy_downloads:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/downloads-$(date +%Y%m%d).tar.gz -C /data .

# 备份配置
docker run --rm \
  -v yt-dlp-web-deploy_config:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/config-$(date +%Y%m%d).tar.gz -C /data .
```

## 🔄 更新升级

### 手动更新

```bash
# 停止服务
docker-compose -f docker-compose.github.yml down

# 更新到最新版本
YTDLP_VERSION=latest ./build-github.sh --no-cache

# 重启服务
docker-compose -f docker-compose.github.yml up -d
```

### 版本回滚

```bash
# 如果新版本有问题，回滚到之前版本
YTDLP_VERSION=2024.12.13 ./build-github.sh --no-cache
docker-compose -f docker-compose.github.yml up -d
```

## 🎉 完成！

现在您已经成功部署了 GitHub 网络版 yt-dlp Web！

### 下一步建议

1. **修改默认密码**: 登录后立即修改管理员密码
2. **配置 HTTPS**: 在生产环境中配置 SSL 证书
3. **设置监控**: 配置 Prometheus 和 Grafana 监控
4. **定期备份**: 设置自动备份脚本
5. **阅读文档**: 查看完整文档了解高级功能

### 获取帮助

- **查看日志**: `docker-compose logs -f`
- **进入容器**: `docker exec -it yt-dlp-web-github bash`
- **重新构建**: `./build-github.sh --no-cache`
- **完全重置**: `docker-compose down && docker system prune -a`

祝您使用愉快！🎊
