# yt-dlp Web - GitHub 网络版

基于 GitHub 网络版 yt-dlp 的 Web 界面，支持多种 yt-dlp 源和智能构建策略。

## 🎯 特性

### 🔄 多源支持
- **GitHub Release**: 自动获取最新稳定版本
- **PyPI 包**: 使用官方 PyPI 发布版本
- **本地文件**: 使用项目中的 yt-dlp 文件

### 🏗️ 智能构建
- **多阶段构建**: 源获取与应用构建解耦
- **自动回退**: 源不可用时自动切换备用方案
- **缓存优化**: 智能缓存减少构建时间

### 🔧 灵活配置
- **环境分离**: 开发/生产/测试环境独立配置
- **版本锁定**: 支持指定特定版本
- **运行时检测**: 启动时自动检测和配置 yt-dlp

## 🚀 快速开始

### 1. 准备环境

```bash
# 复制环境配置
cp .env.github .env

# 编辑配置（可选）
nano .env
```

### 2. 构建和启动

#### 方式一：使用构建脚本（推荐）

```bash
# 使用默认配置（GitHub Release）
./build-github.sh

# 使用 PyPI 源
./build-github.sh --source pypi

# 使用本地文件
./build-github.sh --source local

# 构建并测试
./build-github.sh --test

# 无缓存构建
./build-github.sh --no-cache
```

#### 方式二：使用 Docker Compose

```bash
# 启动服务
docker-compose -f docker-compose.github.yml up -d

# 查看日志
docker-compose -f docker-compose.github.yml logs -f

# 停止服务
docker-compose -f docker-compose.github.yml down
```

### 3. 访问应用

- Web 界面: http://localhost:8080
- 默认账号: admin / admin123

## 📋 配置说明

### yt-dlp 源配置

编辑 `config/ytdlp-source.yml`:

```yaml
ytdlp_source:
  # 当前使用的源
  active: "github_release"
  
  # GitHub Release 配置
  github_release:
    enabled: true
    repository: "yt-dlp/yt-dlp"
    version: "latest"  # 或指定版本
    
  # PyPI 配置
  pypi:
    enabled: true
    package: "yt-dlp"
    version: ">=2024.12.13"
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `YTDLP_SOURCE` | yt-dlp 源类型 | `github_release` |
| `YTDLP_VERSION` | yt-dlp 版本 | `latest` |
| `ENVIRONMENT` | 环境类型 | `production` |
| `WEB_PORT` | Web 端口 | `8080` |
| `ADMIN_USERNAME` | 管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 管理员密码 | `admin123` |

## 🔧 高级用法

### 多环境部署

```bash
# 开发环境
ENVIRONMENT=development ./build-github.sh --source local

# 生产环境
ENVIRONMENT=production ./build-github.sh --source github_release

# 测试环境
ENVIRONMENT=testing ./build-github.sh --source pypi --test
```

### 版本锁定

```bash
# 锁定特定版本
YTDLP_VERSION=2024.12.13 ./build-github.sh

# 使用版本范围
YTDLP_VERSION=">=2024.12.13" ./build-github.sh --source pypi
```

### 自定义构建

```bash
# 自定义镜像标签
./build-github.sh --tag my-registry/yt-dlp-web:v1.0

# 使用自定义 Dockerfile
./build-github.sh --dockerfile Dockerfile.custom

# 构建并推送
./build-github.sh --push
```

## 🔍 故障排除

### 构建失败

1. **网络问题**:
   ```bash
   # 使用本地源
   ./build-github.sh --source local
   ```

2. **版本不兼容**:
   ```bash
   # 使用稳定版本
   YTDLP_VERSION=2024.12.13 ./build-github.sh
   ```

3. **缓存问题**:
   ```bash
   # 清理缓存重建
   ./build-github.sh --no-cache
   ```

### 运行时问题

1. **yt-dlp 导入失败**:
   - 检查容器日志: `docker logs yt-dlp-web-github`
   - 验证源配置: `docker exec yt-dlp-web-github python -c "import yt_dlp; print('OK')"`

2. **权限问题**:
   - 使用命名卷而不是绑定挂载
   - 检查容器内权限: `docker exec yt-dlp-web-github ls -la /app/downloads`

3. **网络问题**:
   - 检查端口映射: `docker port yt-dlp-web-github`
   - 验证网络连接: `curl http://localhost:8080`

## 📊 监控和日志

### 启用监控

```bash
# 启动带监控的服务
docker-compose -f docker-compose.github.yml --profile monitoring up -d

# 访问 Prometheus
open http://localhost:9090
```

### 查看日志

```bash
# 应用日志
docker-compose -f docker-compose.github.yml logs -f yt-dlp-web-github

# 所有服务日志
docker-compose -f docker-compose.github.yml logs -f
```

## 🔄 更新和维护

### 更新 yt-dlp

```bash
# 重新构建获取最新版本
./build-github.sh --no-cache

# 或重启容器（如果使用 PyPI 源）
docker-compose -f docker-compose.github.yml restart
```

### 备份数据

```bash
# 备份下载文件
docker run --rm -v yt-dlp-web-deploy_downloads:/data -v $(pwd):/backup alpine tar czf /backup/downloads.tar.gz -C /data .

# 备份配置
docker run --rm -v yt-dlp-web-deploy_config:/data -v $(pwd):/backup alpine tar czf /backup/config.tar.gz -C /data .
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目采用 MIT 许可证。
