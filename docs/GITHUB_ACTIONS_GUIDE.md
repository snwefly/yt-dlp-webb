# GitHub Actions 工作流使用指南

## 🚀 快速开始

### 1. 访问 GitHub Actions
1. 进入您的 GitHub 仓库
2. 点击 **Actions** 标签
3. 选择 **增强版 Docker 构建** 工作流
4. 点击 **Run workflow** 按钮

### 2. 选择构建模式
在弹出的界面中选择：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| **构建策略** | 选择构建方式 | `hybrid` (推荐) |
| **yt-dlp 源** | yt-dlp 获取方式 | `github_release` |
| **yt-dlp 版本** | 指定版本或 latest | `latest` |
| **构建平台** | 目标架构 | `linux/amd64,linux/arm64` |
| **镜像标签** | Docker 镜像标签 | `latest` |
| **推送到仓库** | 是否推送镜像 | `true` |
| **运行测试** | 是否执行测试 | `true` |
| **环境类型** | 部署环境 | `production` |

### 3. 点击运行
点击绿色的 **Run workflow** 按钮开始构建。

## 🎯 构建策略说明

### 🔄 hybrid (混合模式) - 推荐
- **特点**: 构建时尝试下载，运行时检查补充
- **优点**: 兼顾稳定性和灵活性
- **适用**: 大多数场景

### 📦 build-time (构建时下载)
- **特点**: Docker 构建阶段下载 yt-dlp
- **优点**: 镜像自包含，启动快
- **适用**: 生产环境

### 🚀 runtime (运行时下载)
- **特点**: 容器启动时下载 yt-dlp
- **优点**: 镜像小，构建快
- **适用**: 开发环境

### 📁 local (本地模式)
- **特点**: 使用项目中的 yt-dlp 文件
- **优点**: 完全离线
- **适用**: 内网环境

## 📊 yt-dlp 源说明

### 🌟 github_release (推荐)
- 从 GitHub Release 获取最新稳定版
- 自动更新，功能最全

### 📦 pypi
- 从 PyPI 获取官方包
- 稳定可靠，更新及时

### 📁 local
- 使用项目中的文件
- 离线可用，版本固定

## 🔧 常用配置组合

### 生产环境推荐
```
构建策略: build-time
yt-dlp 源: github_release
版本: latest
环境: production
测试: true
```

### 开发环境推荐
```
构建策略: runtime
yt-dlp 源: local
版本: latest
环境: development
测试: false
```

### 快速测试
```
构建策略: hybrid
yt-dlp 源: pypi
版本: latest
环境: testing
测试: true
```

## 📋 构建结果

### 成功标志
- ✅ 所有步骤显示绿色对勾
- 📦 镜像成功推送到 GitHub Container Registry
- 🧪 功能测试全部通过

### 镜像地址
构建成功后，镜像地址为：
```
ghcr.io/your-username/your-repo:latest-strategy
```

例如：
```
ghcr.io/user/yt-dlp-web:latest-hybrid
ghcr.io/user/yt-dlp-web:latest-build-time
```

## 🐛 故障排除

### 构建失败
1. **网络问题**: 选择 `local` 源
2. **权限问题**: 检查 GitHub Token 权限
3. **文件缺失**: 确保所有 Dockerfile 存在

### 测试失败
1. **启动超时**: 选择 `build-time` 策略
2. **API 错误**: 检查应用配置
3. **网络问题**: 跳过测试步骤

## 💡 使用技巧

### 1. 快速构建
- 选择 `runtime` + `pypi` 组合
- 关闭测试以加快速度

### 2. 稳定部署
- 选择 `build-time` + `github_release`
- 指定具体版本号

### 3. 离线环境
- 选择 `local` 源
- 确保项目包含完整 yt-dlp 文件

### 4. 多平台支持
- 保持默认的 `linux/amd64,linux/arm64`
- 支持 x86 和 ARM 架构

## 🔄 自动化建议

### 定期更新
建议每周手动触发一次构建，获取最新的 yt-dlp 版本。

### 版本管理
生产环境建议锁定特定版本，如 `2024.12.13`。

### 监控告警
关注构建失败通知，及时处理问题。

---

**就这么简单！选择参数，点击运行，等待完成。** 🎉
