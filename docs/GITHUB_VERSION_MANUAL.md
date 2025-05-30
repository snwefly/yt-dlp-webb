# GitHub 网络版 yt-dlp Web 详细说明书

## 📖 目录

1. [项目概述](#项目概述)
2. [架构设计](#架构设计)
3. [功能特性](#功能特性)
4. [系统要求](#系统要求)
5. [安装部署](#安装部署)
6. [配置说明](#配置说明)
7. [使用教程](#使用教程)
8. [故障排除](#故障排除)
9. [高级配置](#高级配置)
10. [维护更新](#维护更新)

## 📋 项目概述

### 什么是 GitHub 网络版 yt-dlp Web？

这是一个基于 GitHub 网络版 yt-dlp 的 Web 界面项目，具有以下特点：

- **智能源管理**: 支持多种 yt-dlp 获取方式（GitHub Release、PyPI、本地文件）
- **低耦合设计**: 模块化架构，易于维护和扩展
- **自动化构建**: 多阶段 Docker 构建，优化镜像大小和构建速度
- **环境适配**: 支持开发、生产、测试等多种环境
- **故障恢复**: 自动回退机制，确保构建成功

### 与传统方案的区别

| 特性 | 传统方案 | GitHub 网络版 |
|------|----------|---------------|
| **yt-dlp 来源** | 固定本地文件 | 多源智能选择 |
| **版本管理** | 手动更新 | 自动获取最新版 |
| **构建灵活性** | 单一方式 | 多策略可选 |
| **故障处理** | 手动干预 | 自动回退 |
| **维护成本** | 高 | 低 |
| **镜像大小** | 大（~700MB） | 小（~200MB） |

## 🏗️ 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub 网络版架构                        │
├─────────────────────────────────────────────────────────────┤
│  Web 界面层                                                 │
│  ├── Flask 应用                                             │
│  ├── 用户认证                                               │
│  ├── iOS 快捷指令 API                                       │
│  └── 管理员功能                                             │
├─────────────────────────────────────────────────────────────┤
│  业务逻辑层                                                 │
│  ├── yt-dlp 管理器                                          │
│  ├── 下载管理                                               │
│  ├── 文件清理                                               │
│  └── 错误处理                                               │
├─────────────────────────────────────────────────────────────┤
│  yt-dlp 源管理层                                            │
│  ├── GitHub Release 提供者                                  │
│  ├── PyPI 包提供者                                          │
│  ├── 本地文件提供者                                         │
│  └── 智能选择器                                             │
├─────────────────────────────────────────────────────────────┤
│  基础设施层                                                 │
│  ├── Docker 容器                                            │
│  ├── 文件系统                                               │
│  ├── 网络服务                                               │
│  └── 监控日志                                               │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. yt-dlp 源管理器 (`YtdlpSourceManager`)
- **职责**: 管理不同的 yt-dlp 获取源
- **特点**: 支持多源、自动回退、缓存优化
- **配置**: `config/ytdlp-source.yml`

#### 2. 多阶段构建系统
- **阶段1**: yt-dlp 源准备
- **阶段2**: 依赖构建
- **阶段3**: 应用构建
- **优势**: 分离关注点，优化构建速度

#### 3. 智能启动脚本
- **功能**: 运行时检测和配置
- **特点**: 自动修复、错误容忍
- **文件**: `start-github.sh`

## ✨ 功能特性

### 核心功能

1. **视频下载**
   - 支持 1000+ 网站
   - 多种格式选择
   - 批量下载
   - 断点续传

2. **用户管理**
   - 登录认证
   - 权限控制
   - 会话管理
   - 安全防护

3. **iOS 快捷指令**
   - 无缝集成
   - 快速下载
   - 格式选择
   - 状态反馈

4. **管理功能**
   - 文件管理
   - 系统监控
   - 日志查看
   - 配置管理

### 高级特性

1. **智能源管理**
   - 自动选择最佳源
   - 失败自动回退
   - 版本锁定支持
   - 缓存优化

2. **多环境支持**
   - 开发环境配置
   - 生产环境优化
   - 测试环境隔离
   - CI/CD 集成

3. **监控告警**
   - 健康检查
   - 性能监控
   - 错误告警
   - 日志分析

## 💻 系统要求

### 最低要求

- **操作系统**: Linux/Windows/macOS
- **Docker**: 20.10+
- **Docker Compose**: 1.29+
- **内存**: 2GB RAM
- **存储**: 10GB 可用空间
- **网络**: 互联网连接（用于获取 yt-dlp）

### 推荐配置

- **CPU**: 4 核心
- **内存**: 8GB RAM
- **存储**: 50GB SSD
- **网络**: 100Mbps 带宽

### 端口要求

- **8080**: Web 界面（可配置）
- **9090**: Prometheus 监控（可选）
- **6379**: Redis 缓存（可选）

## 🚀 安装部署

### 快速开始

1. **克隆项目**
```bash
git clone <your-repo-url>
cd yt-dlp-web-deploy
```

2. **配置环境**
```bash
# 复制环境配置
cp .env.github .env

# 编辑配置（可选）
nano .env
```

3. **构建启动**
```bash
# 使用构建脚本（推荐）
chmod +x build-github.sh
./build-github.sh

# 或使用 Docker Compose
docker-compose -f docker-compose.github.yml up -d
```

4. **访问应用**
- 地址: http://localhost:8080
- 账号: admin / admin123

### 详细安装步骤

#### 步骤 1: 环境准备

```bash
# 检查 Docker 版本
docker --version
docker-compose --version

# 确保 Docker 服务运行
sudo systemctl start docker
sudo systemctl enable docker
```

#### 步骤 2: 项目配置

```bash
# 创建项目目录
mkdir -p ~/yt-dlp-web
cd ~/yt-dlp-web

# 下载项目文件
# （这里假设您已经有了所有文件）

# 设置权限
chmod +x *.sh
chmod +x scripts/*.py
```

#### 步骤 3: 环境配置

编辑 `.env` 文件：

```bash
# yt-dlp 源配置
YTDLP_SOURCE=github_release  # 或 pypi、local
YTDLP_VERSION=latest         # 或具体版本号

# 应用配置
WEB_PORT=8080
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password

# 环境类型
ENVIRONMENT=production
```

#### 步骤 4: 构建部署

```bash
# 方式一：使用构建脚本
./build-github.sh --source github_release --test

# 方式二：使用 Docker Compose
docker-compose -f docker-compose.github.yml build
docker-compose -f docker-compose.github.yml up -d

# 方式三：手动构建
docker build -f Dockerfile.github -t yt-dlp-web:github .
docker run -d -p 8080:8080 --name yt-dlp-web yt-dlp-web:github
```

## ⚙️ 配置说明

### 主要配置文件

#### 1. `.env` - 环境变量配置

```bash
# 构建配置
VERSION=1.0.0
YTDLP_SOURCE=github_release
YTDLP_VERSION=latest
ENVIRONMENT=production

# 应用配置
WEB_PORT=8080
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
SECRET_KEY=your-secret-key

# 系统配置
TZ=Asia/Shanghai
DEBUG=false
LOG_LEVEL=INFO
```

#### 2. `config/ytdlp-source.yml` - yt-dlp 源配置

```yaml
ytdlp_source:
  # 当前使用的源
  active: "github_release"

  # GitHub Release 配置
  github_release:
    enabled: true
    repository: "yt-dlp/yt-dlp"
    version: "latest"
    asset_pattern: "yt-dlp.tar.gz"
    fallback_version: "2024.12.13"

  # PyPI 配置
  pypi:
    enabled: true
    package: "yt-dlp"
    version: ">=2024.12.13"

  # 本地文件配置
  local:
    enabled: true
    path: "./yt_dlp"
    backup_path: "./backup/yt_dlp"

# 构建策略
build_strategy:
  priority:
    - "github_release"
    - "pypi"
    - "local"
  fallback_enabled: true
  cache:
    enabled: true
    directory: "./.cache/ytdlp"
    ttl_hours: 24

# 环境特定配置
environments:
  development:
    source_override: "local"
  production:
    source_override: "github_release"
    version_lock: true
  testing:
    source_override: "pypi"
```

#### 3. `docker-compose.github.yml` - Docker Compose 配置

```yaml
version: '3.8'

services:
  yt-dlp-web-github:
    build:
      context: .
      dockerfile: Dockerfile.github
      args:
        YTDLP_SOURCE: ${YTDLP_SOURCE:-github_release}
        YTDLP_VERSION: ${YTDLP_VERSION:-latest}

    ports:
      - "${WEB_PORT:-8080}:8080"

    volumes:
      - downloads:/app/downloads
      - config:/app/config
      - logs:/app/logs

    environment:
      - ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
      - YTDLP_SOURCE=${YTDLP_SOURCE:-github_release}
      - ENVIRONMENT=${ENVIRONMENT:-production}

    restart: unless-stopped

volumes:
  downloads:
  config:
  logs:
```

### 配置选项详解

#### yt-dlp 源类型

1. **github_release** (推荐)
   - 优点: 最新稳定版本，自动更新
   - 缺点: 需要网络连接
   - 适用: 生产环境

2. **pypi**
   - 优点: 官方发布，稳定可靠
   - 缺点: 更新可能滞后
   - 适用: CI/CD 环境

3. **local**
   - 优点: 离线可用，版本锁定
   - 缺点: 需要手动更新
   - 适用: 内网环境

#### 环境类型

1. **production** - 生产环境
   - 使用 GitHub Release
   - 启用版本锁定
   - 优化性能配置

2. **development** - 开发环境
   - 使用本地文件
   - 启用调试模式
   - 快速重建

3. **testing** - 测试环境
   - 使用 PyPI 包
   - 启用测试功能
   - 隔离配置

## 📖 使用教程

### 基础使用

#### 1. 首次登录

1. **访问应用**
   ```
   http://localhost:8080
   ```

2. **登录界面**
   - 用户名: `admin`
   - 密码: `admin123`（建议修改）

3. **修改密码**
   - 登录后点击右上角用户名
   - 选择"修改密码"
   - 输入新密码并确认

#### 2. 下载视频

1. **基础下载**
   ```
   1. 在首页输入视频URL
   2. 选择下载格式（视频/音频）
   3. 点击"开始下载"
   4. 等待下载完成
   ```

2. **高级选项**
   ```
   - 质量选择: 1080p, 720p, 480p 等
   - 格式选择: MP4, MP3, WEBM 等
   - 字幕下载: 自动/手动选择语言
   - 播放列表: 单个/全部下载
   ```

3. **批量下载**
   ```
   1. 点击"批量下载"
   2. 每行输入一个URL
   3. 设置统一格式
   4. 开始批量处理
   ```

#### 3. 文件管理

1. **查看下载**
   - 点击"下载管理"
   - 查看下载历史
   - 下载文件到本地

2. **文件清理**
   - 自动清理: 24小时后删除
   - 手动清理: 选择文件删除
   - 批量清理: 一键清空

### iOS 快捷指令使用

#### 1. 安装快捷指令

1. **获取快捷指令**
   ```
   方式一: 扫描应用内二维码
   方式二: 访问 /api/shortcuts/install
   方式三: 手动创建（见下方配置）
   ```

2. **快捷指令配置**
   ```
   名称: yt-dlp 下载
   URL: http://your-server:8080/api/shortcuts/download
   方法: POST
   请求体:
   {
     "url": "视频URL",
     "format": "mp4",
     "quality": "best"
   }
   ```

#### 2. 使用快捷指令

1. **分享下载**
   ```
   1. 在任意应用中分享视频链接
   2. 选择"yt-dlp 下载"快捷指令
   3. 选择下载格式
   4. 等待下载完成通知
   ```

2. **直接下载**
   ```
   1. 复制视频链接
   2. 运行快捷指令
   3. 自动识别剪贴板链接
   4. 开始下载
   ```

### 管理员功能

#### 1. 系统监控

1. **访问监控面板**
   ```
   URL: /admin/dashboard
   功能: 系统状态、下载统计、错误日志
   ```

2. **性能监控**
   ```
   - CPU 使用率
   - 内存占用
   - 磁盘空间
   - 网络流量
   ```

#### 2. 用户管理

1. **用户列表**
   ```
   - 查看所有用户
   - 用户权限管理
   - 登录日志查看
   ```

2. **权限控制**
   ```
   - 下载权限
   - 管理员权限
   - API 访问权限
   ```

#### 3. 系统配置

1. **下载设置**
   ```
   - 默认格式
   - 质量限制
   - 并发数量
   - 存储限制
   ```

2. **安全设置**
   ```
   - 密码策略
   - 会话超时
   - IP 白名单
   - API 限流
   ```

### 高级使用

#### 1. API 接口

1. **认证**
   ```bash
   # 获取 Token
   curl -X POST http://localhost:8080/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}'

   # 使用 Token
   curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/info?url=VIDEO_URL
   ```

2. **下载接口**
   ```bash
   # 获取视频信息
   curl -H "Authorization: Bearer TOKEN" \
     "http://localhost:8080/api/info?url=VIDEO_URL"

   # 开始下载
   curl -X POST http://localhost:8080/api/download \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "VIDEO_URL",
       "format": "mp4",
       "quality": "best"
     }'
   ```

#### 2. 自定义配置

1. **yt-dlp 选项**
   ```python
   # 在 webapp/core/ytdlp_manager.py 中修改
   default_options = {
       'format': 'best[height<=1080]',
       'writesubtitles': True,
       'writeautomaticsub': True,
       'subtitleslangs': ['zh', 'en'],
   }
   ```

2. **下载路径**
   ```bash
   # 环境变量
   DOWNLOAD_FOLDER=/custom/path

   # Docker 挂载
   volumes:
     - /host/path:/app/downloads
   ```

## 🔧 故障排除

### 常见问题

#### 1. 构建失败

**问题**: Docker 构建失败
```
解决方案:
1. 检查网络连接
2. 清理 Docker 缓存: docker system prune -a
3. 使用本地源: YTDLP_SOURCE=local ./build-github.sh
4. 检查磁盘空间
```

**问题**: yt-dlp 源获取失败
```
解决方案:
1. 检查 GitHub API 限制
2. 使用 PyPI 源: YTDLP_SOURCE=pypi
3. 配置代理: HTTP_PROXY=proxy:port
4. 使用本地文件: YTDLP_SOURCE=local
```

#### 2. 运行时错误

**问题**: 权限错误
```
错误: Permission denied: '/app/downloads'
解决方案:
1. 检查 Docker 卷权限
2. 使用命名卷而非绑定挂载
3. 修改 Dockerfile 权限设置
```

**问题**: extractor 模块缺失
```
错误: No module named 'yt_dlp.extractor.xxx'
解决方案:
1. 运行修复脚本: python scripts/fix_extractors.py
2. 重新构建镜像: docker-compose build --no-cache
3. 使用最新版本: YTDLP_VERSION=latest
```

#### 3. 网络问题

**问题**: 下载失败
```
解决方案:
1. 检查网站可访问性
2. 更新 yt-dlp 版本
3. 配置代理设置
4. 检查防火墙规则
```

**问题**: API 访问失败
```
解决方案:
1. 检查端口映射
2. 验证防火墙设置
3. 确认服务状态
4. 查看应用日志
```

### 调试方法

#### 1. 日志查看

```bash
# 应用日志
docker-compose logs -f yt-dlp-web-github

# 系统日志
docker logs yt-dlp-web-github

# 实时日志
docker exec -it yt-dlp-web-github tail -f /app/logs/app.log
```

#### 2. 容器调试

```bash
# 进入容器
docker exec -it yt-dlp-web-github bash

# 检查 yt-dlp
python -c "import yt_dlp; print(yt_dlp.__version__)"

# 测试下载
yt-dlp --version
yt-dlp -F "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

#### 3. 网络测试

```bash
# 测试连接
curl -I http://localhost:8080

# 测试 API
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 健康检查
curl http://localhost:8080/health
```
