# GitHub 网络版 yt-dlp Web

一个支持多种构建策略的 yt-dlp Web 界面，具有智能源管理和 iOS 快捷指令集成。

## 🚀 快速开始

### 方式一：GitHub Actions（推荐）

1. 访问仓库的 **Actions** 标签
2. 选择 **增强版 Docker 构建** 工作流
3. 点击 **Run workflow**
4. 选择构建参数：
   - 构建策略：`hybrid`（推荐）
   - yt-dlp 源：`github_release`
   - 其他保持默认
5. 点击 **Run workflow** 开始构建

### 方式二：本地构建

```bash
# 交互式选择构建策略
./build-smart.sh --interactive

# 或直接使用推荐配置
./build-smart.sh --strategy hybrid --source github_release
```

## 🎯 构建策略

| 策略 | 特点 | 适用场景 |
|------|------|----------|
| **hybrid** | 构建时尝试下载，运行时补充 | 推荐，平衡稳定性和灵活性 |
| **build-time** | 构建时下载，镜像自包含 | 生产环境，离线部署 |
| **runtime** | 运行时下载，镜像轻量 | 开发环境，快速迭代 |
| **local** | 使用本地文件，完全离线 | 内网环境，安全要求高 |

## 📊 yt-dlp 源

| 源类型 | 说明 | 推荐度 |
|--------|------|--------|
| **github_release** | GitHub Release 最新版 | ⭐⭐⭐ 推荐 |
| **pypi** | PyPI 官方包 | ⭐⭐ 稳定 |
| **local** | 项目中的文件 | ⭐ 离线 |

## 🔧 使用方法

### 本地构建

```bash
# 快捷方式（推荐）
./build.sh --interactive

# 查看所有策略
./scripts/build-smart.sh --list-strategies

# 生产环境构建
./scripts/build-smart.sh --strategy build-time --source github_release --env production

# 开发环境构建
./scripts/build-smart.sh --strategy runtime --source local --env development
```

### Docker Compose

```bash
# 使用默认配置（混合模式）
docker-compose up -d

# 构建时下载模式
docker-compose -f docker-compose.build-time.yml up -d

# 运行时下载模式
docker-compose -f docker-compose.runtime.yml up -d
```

### 直接构建

```bash
# 混合模式（推荐）
docker build -f dockerfiles/Dockerfile.hybrid -t yt-dlp-web:hybrid .

# 构建时下载
docker build -f dockerfiles/Dockerfile.build-time -t yt-dlp-web:build-time .

# 运行时下载
docker build -f dockerfiles/Dockerfile.runtime -t yt-dlp-web:runtime .
```

## 📱 iOS 快捷指令

1. 访问 `http://localhost:8080/api/shortcuts/install`
2. 或扫描应用内二维码
3. 安装快捷指令后即可在任意应用中分享视频链接下载

## 🔍 故障排除

### 构建失败
```bash
# 清理缓存重新构建
./build-smart.sh --strategy hybrid --no-cache

# 使用本地源（无网络依赖）
./build-smart.sh --strategy local
```

### 运行失败
```bash
# 查看日志
docker-compose logs -f

# 重新启动
docker-compose restart
```

### 权限问题
```bash
# 重新创建卷
docker-compose down
docker volume rm yt-dlp-web-deploy_downloads
docker-compose up -d
```

## 📁 项目结构

```
yt-dlp-web-deploy/
├── 📄 README.md                    # 项目说明
├── 📄 Dockerfile                   # 主 Dockerfile（提示用法）
├── 📄 docker-compose.yml           # 默认配置（混合模式）
├── 📄 build.sh                     # 快捷构建脚本
│
├── 📁 dockerfiles/                 # 所有 Dockerfile
│   ├── Dockerfile.hybrid           # 混合模式（推荐）
│   ├── Dockerfile.build-time       # 构建时下载
│   ├── Dockerfile.runtime          # 运行时下载
│   └── Dockerfile.local-ytdlp      # 本地文件模式
│
├── 📁 scripts/                     # 所有脚本
│   ├── start-hybrid.sh             # 混合模式启动脚本
│   ├── start-runtime.sh            # 运行时启动脚本
│   ├── build-smart.sh              # 智能构建脚本
│   └── fix-all-issues.sh           # 问题修复脚本
│
├── 📁 requirements/                # 所有依赖文件
│   ├── requirements.hybrid.txt     # 混合模式依赖
│   ├── requirements.runtime.txt    # 运行时模式依赖
│   └── requirements.local.txt      # 本地模式依赖
│
├── 📁 webapp/                      # Web 应用代码
├── 📁 config/                      # 配置文件
├── 📁 docs/                        # 详细文档
└── 📁 backup/                      # 备份文件
```

## 📖 详细文档

- [GitHub Actions 使用指南](docs/GITHUB_ACTIONS_GUIDE.md)
- [完整功能说明](docs/GITHUB_VERSION_MANUAL.md)
- [快速入门教程](docs/QUICK_START_TUTORIAL.md)
- [高级配置指南](docs/ADVANCED_CONFIGURATION.md)
- [API 文档](docs/API_DOCUMENTATION.md)

## 🎉 特性

- ✅ 多种构建策略，适应不同环境
- ✅ 智能 yt-dlp 源管理，自动回退
- ✅ iOS 快捷指令完整集成
- ✅ 用户认证和权限管理
- ✅ 多平台 Docker 镜像（AMD64/ARM64）
- ✅ GitHub Actions 自动化构建
- ✅ 完整的监控和日志系统

## 🔧 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ADMIN_USERNAME` | 管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 管理员密码 | `admin123` |
| `YTDLP_SOURCE` | yt-dlp 源类型 | `github_release` |
| `YTDLP_VERSION` | yt-dlp 版本 | `latest` |
| `WEB_PORT` | Web 端口 | `8080` |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**快速开始**: `./build-smart.sh --interactive` 🚀
