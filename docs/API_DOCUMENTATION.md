# API 接口文档

## 🌐 API 概述

YT-DLP Web 提供完整的 RESTful API，支持所有 Web 界面功能。

### 🔗 基础信息
- **Base URL**: `http://your-server:8080`
- **认证方式**: Flask-Login Session 或 JWT Token
- **数据格式**: JSON
- **字符编码**: UTF-8

### 🔐 认证方式

#### 1. Session 认证（Web 界面）
```javascript
// 登录后自动获得 session
fetch('/api/downloads', {
    credentials: 'same-origin'
});
```

#### 2. JWT Token 认证（API 调用）
```bash
# 1. 获取 token
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 2. 使用 token
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  http://localhost:8080/api/downloads
```

## 🔑 认证接口

### POST /api/auth/login
用户登录

**请求体**:
```json
{
    "username": "admin",
    "password": "admin123"
}
```

**响应**:
```json
{
    "success": true,
    "message": "登录成功",
    "username": "admin",
    "is_admin": true,
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### POST /api/auth/logout
用户登出

**响应**:
```json
{
    "success": true,
    "message": "已成功登出"
}
```

## 📹 下载接口

### POST /api/download
开始下载

**请求体**:
```json
{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "best",
    "quality": "1080p",
    "audio_only": false,
    "custom_filename": "",
    "extract_audio": false,
    "audio_format": "mp3"
}
```

**响应**:
```json
{
    "success": true,
    "message": "下载任务已开始",
    "task_id": "download_123456789",
    "estimated_size": "50.2 MB",
    "duration": "00:03:45"
}
```

### GET /api/download/progress/{task_id}
获取下载进度

**响应**:
```json
{
    "success": true,
    "progress": {
        "percentage": 45.6,
        "downloaded": "23.1 MB",
        "total": "50.2 MB",
        "speed": "2.3 MB/s",
        "eta": "00:00:12",
        "status": "downloading"
    }
}
```

### GET /api/downloads
获取下载历史

**查询参数**:
- `page`: 页码（默认 1）
- `per_page`: 每页数量（默认 20）
- `status`: 状态过滤（all/completed/failed/downloading）

**响应**:
```json
{
    "success": true,
    "downloads": [
        {
            "id": 1,
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "Rick Astley - Never Gonna Give You Up",
            "filename": "Rick Astley - Never Gonna Give You Up.mp4",
            "status": "completed",
            "progress": 100,
            "file_size": "52.1 MB",
            "download_time": "2024-01-01 12:00:00",
            "duration": "00:03:33"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 1,
        "pages": 1
    }
}
```

### DELETE /api/download/{download_id}
删除下载记录

**响应**:
```json
{
    "success": true,
    "message": "下载记录已删除"
}
```

## 📁 文件管理接口

### GET /api/files
获取文件列表

**查询参数**:
- `page`: 页码（默认 1）
- `per_page`: 每页数量（默认 20）
- `sort`: 排序方式（name/size/date）
- `order`: 排序顺序（asc/desc）

**响应**:
```json
{
    "success": true,
    "files": [
        {
            "name": "video.mp4",
            "size": "52.1 MB",
            "size_bytes": 54627840,
            "modified": "2024-01-01 12:00:00",
            "type": "video",
            "duration": "00:03:33",
            "resolution": "1920x1080"
        }
    ],
    "total": 1,
    "total_size": "52.1 MB"
}
```

### GET /api/files/download/{filename}
下载文件

**响应**: 文件流

### DELETE /api/files/{filename}
删除文件

**响应**:
```json
{
    "success": true,
    "message": "文件已删除"
}
```

### POST /api/files/cleanup
清理所有文件

**响应**:
```json
{
    "success": true,
    "message": "文件清理完成",
    "cleaned_count": 5,
    "freed_space": "256.3 MB"
}
```

## 📊 视频信息接口

### POST /api/video/info
获取视频信息

**请求体**:
```json
{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**响应**:
```json
{
    "success": true,
    "info": {
        "title": "Rick Astley - Never Gonna Give You Up",
        "uploader": "RickAstleyVEVO",
        "duration": "00:03:33",
        "view_count": 1234567890,
        "upload_date": "2009-10-25",
        "description": "Music video description...",
        "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
        "formats": [
            {
                "format_id": "22",
                "ext": "mp4",
                "resolution": "1280x720",
                "filesize": 52428800,
                "vcodec": "avc1.64001F",
                "acodec": "mp4a.40.2"
            }
        ]
    }
}
```

## ⚙️ 配置接口

### GET /api/settings
获取系统配置

**响应**:
```json
{
    "success": true,
    "settings": {
        "download_dir": "/app/downloads",
        "max_concurrent_downloads": 3,
        "default_format": "best",
        "telegram_enabled": true,
        "auto_cleanup": false,
        "max_file_age_days": 30
    }
}
```

### POST /api/settings
更新系统配置

**请求体**:
```json
{
    "max_concurrent_downloads": 5,
    "default_format": "best[height<=1080]",
    "auto_cleanup": true
}
```

**响应**:
```json
{
    "success": true,
    "message": "配置已更新"
}
```

### GET /api/settings/telegram
获取 Telegram 配置

**响应**:
```json
{
    "success": true,
    "config": {
        "enabled": true,
        "bot_token_set": true,
        "chat_id_set": true,
        "api_credentials_set": true,
        "send_files": true,
        "send_messages": true
    }
}
```

### POST /api/settings/telegram
更新 Telegram 配置

**请求体**:
```json
{
    "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    "chat_id": "-1001234567890",
    "api_id": "12345678",
    "api_hash": "abcdef1234567890abcdef1234567890",
    "enabled": true,
    "send_files": true,
    "send_messages": true
}
```

**响应**:
```json
{
    "success": true,
    "message": "Telegram 配置已更新"
}
```

### POST /api/settings/telegram/test
测试 Telegram 连接

**响应**:
```json
{
    "success": true,
    "message": "Telegram 连接测试成功",
    "bot_info": {
        "username": "your_bot_username",
        "first_name": "YT-DLP Bot"
    }
}
```

## 🍪 Cookies 管理接口

### GET /api/cookies
获取 Cookies 配置

**响应**:
```json
{
    "success": true,
    "cookies": {
        "youtube": {
            "enabled": true,
            "format": "netscape",
            "last_updated": "2024-01-01 12:00:00",
            "cookie_count": 15
        }
    }
}
```

### POST /api/cookies/upload
上传 Cookies 文件

**请求**: multipart/form-data
- `file`: Cookies 文件
- `platform`: 平台名称（youtube/bilibili等）
- `format`: 格式（netscape/json）

**响应**:
```json
{
    "success": true,
    "message": "Cookies 上传成功",
    "platform": "youtube",
    "cookie_count": 15
}
```

### DELETE /api/cookies/{platform}
删除平台 Cookies

**响应**:
```json
{
    "success": true,
    "message": "Cookies 已删除"
}
```

## 📊 系统状态接口

### GET /health
健康检查

**响应**:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T12:00:00Z",
    "version": "1.0.0",
    "uptime": "2 days, 3 hours, 45 minutes"
}
```

### GET /api/status
系统状态

**响应**:
```json
{
    "success": true,
    "status": {
        "cpu_usage": 25.6,
        "memory_usage": 512.3,
        "disk_usage": 75.2,
        "active_downloads": 2,
        "total_downloads": 156,
        "total_files": 89,
        "total_size": "12.5 GB"
    }
}
```

## 🔍 错误处理

### 错误响应格式
```json
{
    "success": false,
    "error": "ERROR_CODE",
    "message": "错误描述",
    "details": "详细错误信息（可选）"
}
```

### 常见错误码
- `UNAUTHORIZED`: 未授权访问
- `INVALID_URL`: 无效的视频链接
- `DOWNLOAD_FAILED`: 下载失败
- `FILE_NOT_FOUND`: 文件不存在
- `INVALID_FORMAT`: 无效的格式参数
- `RATE_LIMITED`: 请求频率过高
- `SERVER_ERROR`: 服务器内部错误

## 📝 使用示例

### Python 示例
```python
import requests

# 登录获取 token
response = requests.post('http://localhost:8080/api/auth/login', json={
    'username': 'admin',
    'password': 'admin123'
})
token = response.json()['token']

# 使用 token 下载视频
headers = {'Authorization': f'Bearer {token}'}
response = requests.post('http://localhost:8080/api/download', 
    headers=headers,
    json={
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'format': 'best[height<=1080]'
    }
)
print(response.json())
```

### JavaScript 示例
```javascript
// 使用 fetch API
async function downloadVideo(url) {
    const response = await fetch('/api/download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
            url: url,
            format: 'best'
        })
    });
    
    const result = await response.json();
    console.log(result);
}
```

### cURL 示例
```bash
# 登录
curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 下载视频
curl -X POST http://localhost:8080/api/download \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

---

**📖 相关文档：**
- [快速部署指南](QUICK_START.md)
- [Telegram 集成指南](TELEGRAM_INTEGRATION.md)
- [故障排除指南](TROUBLESHOOTING.md)
