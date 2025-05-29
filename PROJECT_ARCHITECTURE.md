# YT-DLP Web 项目运行逻辑详解

## 📋 项目概述

YT-DLP Web 是一个基于 Flask 的 Web 应用程序，为 yt-dlp 命令行工具提供了现代化的网页界面。项目采用前后端分离的架构，支持多用户管理、实时下载监控、iOS 快捷指令集成等功能。

## 🏗️ 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    YT-DLP Web 架构图                        │
├─────────────────────────────────────────────────────────────┤
│  前端界面 (HTML/CSS/JavaScript)                             │
│  ├── 主界面 (index.html)                                   │
│  ├── 登录界面 (login.html)                                 │
│  └── 管理界面 (admin.html)                                 │
├─────────────────────────────────────────────────────────────┤
│  Flask Web 服务器                                          │
│  ├── 路由处理 (app.py)                                     │
│  ├── 用户认证 (auth.py)                                    │
│  ├── 文件管理 (file_cleaner.py)                           │
│  └── 服务器启动 (server.py)                               │
├─────────────────────────────────────────────────────────────┤
│  下载管理层                                                │
│  ├── DownloadManager (下载任务管理)                        │
│  ├── 多线程下载处理                                        │
│  └── 进度监控和状态管理                                    │
├─────────────────────────────────────────────────────────────┤
│  YT-DLP 核心                                               │
│  ├── 视频信息提取                                          │
│  ├── 格式选择和下载                                        │
│  └── 后处理 (格式转换、字幕等)                             │
├─────────────────────────────────────────────────────────────┤
│  文件系统                                                  │
│  ├── 下载文件存储                                          │
│  ├── 临时文件管理                                          │
│  └── 自动清理机制                                          │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 启动流程

### 1. 应用初始化
```python
# start.sh 脚本启动
export ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
export SECRET_KEY=${SECRET_KEY:-dev-key}
export DOWNLOAD_FOLDER=${DOWNLOAD_FOLDER:-/app/downloads}

# 启动 Web 服务器
python3 -m web.server --host 0.0.0.0 --port 8080
```

### 2. Flask 应用创建
```python
# web/app.py - create_app()
def create_app(config=None):
    app = Flask(__name__)

    # 配置应用
    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-key'),
        'DOWNLOAD_FOLDER': config.get('DOWNLOAD_FOLDER', './downloads'),
        'DEBUG': config.get('DEBUG', False)
    })

    # 初始化组件
    CORS(app)  # 跨域支持
    initialize_cleanup_manager()  # 文件清理
    register_routes(app)  # 注册路由

    return app
```

### 3. 服务器启动
```python
# web/server.py - WebServer.start()
def start(self, open_browser=True):
    self.app.run(
        host=self.host,      # 0.0.0.0
        port=self.port,      # 8080
        debug=self.debug,    # False (生产环境)
        threaded=True        # 多线程支持
    )
```

## 🔐 用户认证流程

### 1. 认证管理器初始化
```python
# web/auth.py - AuthManager
class AuthManager:
    def __init__(self):
        # 从环境变量读取管理员账号
        self.admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        self.admin_password_hash = self._hash_password(
            os.environ.get('ADMIN_PASSWORD', 'admin123')
        )
        self.active_sessions = {}  # 存储活跃会话
```

### 2. 登录验证流程
```
用户输入 → 密码哈希 → 凭据验证 → 创建会话 → 返回Token
    ↓
前端存储Token → 后续请求携带Token → 服务器验证Token
```

### 3. 权限控制
```python
@login_required  # 需要登录
def protected_route():
    pass

@admin_required  # 需要管理员权限
def admin_route():
    pass
```

## 📥 下载管理机制

### 1. 下载管理器架构
```python
class DownloadManager:
    def __init__(self):
        self.downloads = {}      # 存储所有下载任务
        self.lock = threading.Lock()  # 线程安全锁

    def add_download(self, download_id, url, options):
        # 添加新下载任务

    def update_download(self, download_id, **kwargs):
        # 更新下载状态

    def get_download(self, download_id):
        # 获取下载信息
```

### 2. 下载流程
```
URL输入 → URL验证 → 并发检查 → 创建任务 → 后台下载
   ↓
进度回调 → 状态更新 → 前端轮询 → 实时显示 → 下载完成
```

### 3. 多线程下载处理
```python
def _download_worker(download_id, url, ydl_opts):
    """后台下载工作线程"""
    try:
        # 更新状态为下载中
        download_manager.update_download(download_id, status='downloading')

        # 配置进度回调
        ydl_opts['progress_hooks'] = [
            lambda d: _progress_hook(download_id, d)
        ]

        # 执行下载
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # 更新状态为完成
        download_manager.update_download(download_id, status='completed')

    except Exception as e:
        # 更新状态为错误
        download_manager.update_download(download_id,
                                       status='error',
                                       error=str(e))
```

## 🌐 API 端点设计

### 1. 核心 API 端点
```
POST /api/auth/login          # 用户登录
POST /api/auth/logout         # 用户登出
GET  /api/auth/status         # 检查登录状态

POST /api/info                # 获取视频信息
POST /api/download            # 开始下载
GET  /api/download/{id}       # 获取下载状态
GET  /api/downloads           # 获取所有下载

GET  /api/files               # 列出下载文件
GET  /api/files/{filename}    # 下载文件
DELETE /api/files/{filename}  # 删除文件

POST /api/shortcuts/download  # iOS 快捷指令专用
```

### 2. API 请求流程
```
客户端请求 → 认证检查 → 参数验证 → 业务逻辑 → 返回响应
     ↓
错误处理 → 日志记录 → 状态码 → JSON响应
```

### 3. 安全验证
```python
def validate_url(url):
    """URL 安全验证"""
    # 检查协议 (仅允许 HTTP/HTTPS)
    # 检查域名 (阻止内网地址)
    # 检查长度 (防止 DoS)
    # 检查格式 (防止注入)
```

## 🎨 前端界面交互

### 1. 页面结构
```html
<!DOCTYPE html>
<html>
<head>
    <!-- 样式和元数据 -->
</head>
<body>
    <div class="container">
        <div class="header">标题区域</div>
        <div class="main-content">
            <div class="left-panel">
                <!-- 输入区域 -->
                <!-- 选项配置 -->
                <!-- 下载按钮 -->
            </div>
            <div class="right-panel">
                <!-- 状态显示 -->
                <!-- 下载列表 -->
                <!-- 文件管理 -->
            </div>
        </div>
    </div>
</body>
</html>
```

### 2. JavaScript 交互逻辑
```javascript
// 主要功能模块
const App = {
    // URL 验证
    validateUrl(url) { /* ... */ },

    // 获取视频信息
    async getVideoInfo(url) { /* ... */ },

    // 开始下载
    async startDownload(options) { /* ... */ },

    // 轮询状态更新
    pollDownloadStatus() { /* ... */ },

    // 文件管理
    loadFiles() { /* ... */ },

    // iOS 快捷指令
    setupShortcuts() { /* ... */ }
};
```

### 3. 实时状态更新
```javascript
// 每2秒轮询一次下载状态
setInterval(() => {
    if (activeDownloads.length > 0) {
        updateDownloadStatus();
    }
}, 2000);

function updateDownloadStatus() {
    activeDownloads.forEach(async (downloadId) => {
        const status = await fetch(`/api/download/${downloadId}`);
        const data = await status.json();
        updateProgressBar(downloadId, data.progress);
    });
}
```

## 📱 iOS 快捷指令集成

### 1. 专用 API 端点
```python
@app.route('/api/shortcuts/download', methods=['POST'])
def shortcuts_download():
    """iOS 快捷指令专用下载端点"""
    # 支持 JSON 和表单数据
    # 返回快捷指令友好的响应格式
    return jsonify({
        'success': True,
        'download_id': download_id,
        'status_url': f'/api/download/{download_id}/status',
        'download_url': f'/api/shortcuts/download/{download_id}/file'
    })
```

### 2. 快捷指令配置
```
快捷指令流程:
1. 获取剪贴板/分享的URL
2. 发送POST请求到 /api/shortcuts/download
3. 解析返回的download_id
4. 轮询状态直到完成
5. 下载文件到相册/文件
```

## 🗂️ 文件管理和清理

### 1. 自动清理机制
```python
class FileCleanupManager:
    def __init__(self, download_folder, config):
        self.settings = {
            'auto_cleanup_enabled': True,
            'cleanup_interval_hours': 1,     # 每小时清理
            'file_retention_hours': 24,      # 保留24小时
            'max_storage_mb': 2048,          # 最大2GB
            'keep_recent_files': 20,         # 保留最近20个
        }

    def cleanup_files(self):
        # 1. 清理过期文件
        # 2. 清理临时文件
        # 3. 检查存储限制
        # 4. 清理空目录
```

### 2. 清理策略
```
定时清理 (每小时) → 检查文件年龄 → 删除过期文件
     ↓
存储检查 → 超过限制 → 删除最旧文件 (保留最近N个)
     ↓
下载完成 → 立即清理临时文件 → 检查存储空间
```

## 🐳 容器化部署

### 1. Docker 构建流程
```dockerfile
# 多阶段构建
FROM python:3.11-slim as builder
# 安装构建依赖和Python包

FROM python:3.11-slim as runtime
# 复制运行时文件
# 创建非root用户
# 设置权限和环境
```

### 2. 容器启动流程
```bash
# start.sh 脚本
1. 设置环境变量
2. 创建必要目录
3. 验证依赖安装
4. 启动Web服务器
```

### 3. Docker Compose 编排
```yaml
services:
  yt-dlp-web:
    image: yt-dlp-web:latest
    ports: ["8080:8080"]
    volumes:
      - downloads:/app/downloads
      - config:/app/config
    environment:
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=secure_password
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/"]
```

## 🔄 完整请求流程示例

### 下载视频的完整流程:

1. **用户操作**: 在前端输入YouTube URL
2. **URL验证**: JavaScript验证URL格式
3. **获取信息**: 调用 `/api/info` 获取视频信息
4. **显示信息**: 前端显示视频标题、时长等
5. **配置选项**: 用户选择格式、质量等选项
6. **开始下载**: 调用 `/api/download` 开始下载
7. **后台处理**: 创建下载任务，启动工作线程
8. **状态轮询**: 前端每2秒查询下载进度
9. **进度更新**: 实时更新进度条和状态
10. **下载完成**: 显示完成状态，提供下载链接
11. **文件清理**: 后台自动清理过期文件

这个架构确保了系统的可扩展性、安全性和用户体验，同时支持多种使用场景（Web界面、API调用、iOS快捷指令）。
