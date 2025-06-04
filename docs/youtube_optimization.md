# YouTube 下载优化 - 基于最新官方源代码

## 📋 概述

基于新复制的官方 `yt_dlp/extractor/youtube/_base.py` 文件，我们对项目的 YouTube 下载功能进行了全面优化。

## 🎯 主要改进

### 1. 客户端配置优化

基于官方源代码的最新客户端配置：

| 客户端 | PO Token | Cookies | JS Player | 优先级 | 说明 |
|--------|----------|---------|-----------|--------|------|
| `android_vr` | ❌ 不需要 | ❌ 不支持 | ❌ 不需要 | 1 | 最优选择，无需任何额外配置 |
| `web_embedded` | ❌ 不需要 | ✅ 支持 | ✅ 需要 | 2 | 支持cookies，适合已登录用户 |
| `tv` | ❌ 不需要 | ✅ 支持 | ✅ 需要 | 3 | TV客户端，稳定性好 |
| `mweb` | ⚠️ 需要 | ✅ 支持 | ✅ 需要 | 4 | 移动端，备用选择 |

### 2. 新增配置管理器

创建了 `webapp/core/youtube_config.py` 来集中管理 YouTube 相关配置：

- **客户端配置**: 基于官方源代码的最新版本号和User-Agent
- **Cookie管理**: 自动尝试多种浏览器的cookies
- **错误处理**: 完善的回退机制

### 3. 更新的文件

#### 核心文件
- `webapp/core/youtube_config.py` - 新增的YouTube配置管理器
- `webapp/core/download_manager.py` - 更新下载配置
- `webapp/core/ytdlp_manager.py` - 更新管理器配置

#### 路由文件
- `webapp/routes/api.py` - 更新API配置
- `webapp/routes/shortcuts.py` - 更新iOS Shortcuts配置

## 🔧 技术细节

### 客户端版本信息

基于 `yt_dlp/extractor/youtube/_base.py` 的最新配置：

```python
INNERTUBE_CLIENTS = {
    'android_vr': {
        'clientVersion': '1.62.27',
        'INNERTUBE_CONTEXT_CLIENT_NAME': 28,
    },
    'web_embedded': {
        'clientVersion': '1.20250310.01.00',
        'INNERTUBE_CONTEXT_CLIENT_NAME': 56,
    },
    'tv': {
        'clientVersion': '7.20250312.16.00',
        'INNERTUBE_CONTEXT_CLIENT_NAME': 7,
    },
    'mweb': {
        'clientVersion': '2.20250311.03.00',
        'INNERTUBE_CONTEXT_CLIENT_NAME': 2,
    },
}
```

### User-Agent 配置

使用官方源代码中的最新User-Agent：

- **TV客户端**: `Mozilla/5.0 (ChromiumStylePlatform) Cobalt/Version`
- **Android VR**: `com.google.android.apps.youtube.vr.oculus/1.62.27`
- **Web Embedded**: 标准浏览器User-Agent

### Cookie 处理

按优先级尝试获取cookies：

1. **Chrome浏览器** - 最常用
2. **Firefox浏览器** - 备用选择
3. **Edge浏览器** - Windows用户
4. **Safari浏览器** - macOS用户
5. **Cookies文件** - `/app/config/youtube_cookies.txt`

## 🚀 预期效果

### 1. 减少Bot检测
- 使用不需要PO Token的客户端
- 跳过网页解析避免检测
- 使用官方推荐的User-Agent

### 2. 提高成功率
- 多客户端回退机制
- 自动Cookie管理
- 基于最新官方配置

### 3. 更好的兼容性
- 支持更多视频格式
- 处理年龄限制内容
- 支持私有/会员内容（需cookies）

## 📝 使用说明

### 自动配置
项目会自动使用新的配置，无需手动设置。

### 手动Cookie配置
如需手动配置cookies，可以：

1. **浏览器导出**: 项目会自动尝试从浏览器获取
2. **文件配置**: 将cookies保存到 `/app/config/youtube_cookies.txt`

### 日志监控
启动时会显示客户端配置信息：

```
📱 YouTube客户端配置（基于最新官方源代码）:
  1. android_vr: ✅无需PO Token, 🚫不支持Cookies
  2. web_embedded: ✅无需PO Token, 🍪支持Cookies
  3. tv: ✅无需PO Token, 🍪支持Cookies
  4. mweb: ❌需要PO Token, 🍪支持Cookies
```

## 🔍 故障排除

### 常见问题

1. **"could not find chrome cookies database"**
   - ✅ **已修复**: 项目现在会自动检测容器环境
   - 容器中会跳过浏览器cookies获取，直接使用android_vr客户端
   - 无需任何额外配置即可正常工作

2. **"Sign in to confirm you're not a bot"**
   - 配置会优先使用android_vr客户端避免此问题
   - 如仍出现，尝试配置cookies文件到 `/app/config/youtube_cookies.txt`

3. **年龄限制视频**
   - 需要配置已登录账户的cookies文件
   - 参考 `/app/config/youtube_cookies.txt.example`

4. **私有/会员视频**
   - 必须配置对应账户的cookies
   - 确保cookies有效且未过期

### 容器环境优化

项目现在针对容器环境进行了优化：

- **自动检测**: 检测 `/.dockerenv` 或 `CONTAINER=true` 环境变量
- **跳过浏览器**: 容器中不尝试获取浏览器cookies
- **优先客户端**: 直接使用android_vr客户端（无需cookies）
- **文件支持**: 支持通过文件提供cookies

### 快速修复

如果遇到cookies相关错误，运行：

```bash
# 在容器中执行
bash /app/scripts/fix_cookies_error.sh
```

### 调试信息

查看日志中的以下信息：
- `🐳 检测到容器环境，跳过浏览器cookies获取`
- `✅ 使用基于最新官方源代码的YouTube配置`
- `ℹ️ 将使用android_vr客户端（不需要cookies和PO Token）`
- `📱 YouTube客户端配置`

## 📚 参考资料

- [yt-dlp官方文档](https://github.com/yt-dlp/yt-dlp)
- [YouTube Extractor源代码](https://github.com/yt-dlp/yt-dlp/tree/master/yt_dlp/extractor/youtube)
- [Cookie导出指南](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)
