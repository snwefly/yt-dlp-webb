# GitHub 网络版 yt-dlp Web - API 文档

## 📋 API 概览

### 基础信息

- **Base URL**: `http://localhost:8080/api`
- **认证方式**: Bearer Token
- **数据格式**: JSON
- **字符编码**: UTF-8

### 认证流程

1. 使用用户名密码获取 Token
2. 在后续请求中携带 Token
3. Token 有效期 24 小时

## 🔐 认证接口

### 登录获取 Token

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

**响应示例**:
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_in": 86400,
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### 验证 Token

```http
GET /api/auth/verify
Authorization: Bearer YOUR_TOKEN
```

**响应示例**:
```json
{
  "success": true,
  "user": {
    "username": "admin",
    "role": "admin"
  }
}
```

### 刷新 Token

```http
POST /api/auth/refresh
Authorization: Bearer YOUR_TOKEN
```

## 📹 视频信息接口

### 获取视频信息

```http
GET /api/info?url=VIDEO_URL
Authorization: Bearer YOUR_TOKEN
```

**参数说明**:
- `url`: 视频链接（必需）
- `format`: 格式过滤（可选）

**响应示例**:
```json
{
  "success": true,
  "data": {
    "title": "视频标题",
    "description": "视频描述",
    "duration": 180,
    "uploader": "上传者",
    "upload_date": "20241213",
    "view_count": 1000000,
    "thumbnail": "https://example.com/thumb.jpg",
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

### 批量获取视频信息

```http
POST /api/info/batch
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "urls": [
    "https://www.youtube.com/watch?v=VIDEO1",
    "https://www.youtube.com/watch?v=VIDEO2"
  ]
}
```

## ⬇️ 下载接口

### 开始下载

```http
POST /api/download
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "format": "mp4",
  "quality": "best",
  "audio_only": false,
  "subtitle": true,
  "subtitle_lang": "zh,en"
}
```

**参数说明**:
- `url`: 视频链接（必需）
- `format`: 输出格式，如 mp4, mp3, webm（可选，默认 mp4）
- `quality`: 质量选择，如 best, worst, 720p（可选，默认 best）
- `audio_only`: 仅下载音频（可选，默认 false）
- `subtitle`: 下载字幕（可选，默认 false）
- `subtitle_lang`: 字幕语言（可选，默认 zh,en）

**响应示例**:
```json
{
  "success": true,
  "task_id": "download_20241213_123456",
  "message": "下载任务已开始",
  "estimated_size": 52428800
}
```

### 批量下载

```http
POST /api/download/batch
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "urls": [
    "https://www.youtube.com/watch?v=VIDEO1",
    "https://www.youtube.com/watch?v=VIDEO2"
  ],
  "format": "mp4",
  "quality": "720p"
}
```

### 查询下载状态

```http
GET /api/download/status/{task_id}
Authorization: Bearer YOUR_TOKEN
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "task_id": "download_20241213_123456",
    "status": "downloading",
    "progress": 45.6,
    "speed": "1.2MB/s",
    "eta": "00:02:30",
    "file_size": 52428800,
    "downloaded": 23887872,
    "filename": "视频标题.mp4"
  }
}
```

**状态说明**:
- `pending`: 等待中
- `downloading`: 下载中
- `completed`: 已完成
- `failed`: 失败
- `cancelled`: 已取消

### 取消下载

```http
DELETE /api/download/{task_id}
Authorization: Bearer YOUR_TOKEN
```

## 📁 文件管理接口

### 获取文件列表

```http
GET /api/files
Authorization: Bearer YOUR_TOKEN
```

**查询参数**:
- `page`: 页码（可选，默认 1）
- `limit`: 每页数量（可选，默认 20）
- `sort`: 排序方式（可选，name/size/date）
- `order`: 排序顺序（可选，asc/desc）

**响应示例**:
```json
{
  "success": true,
  "data": {
    "files": [
      {
        "filename": "视频标题.mp4",
        "size": 52428800,
        "created_at": "2024-12-13T12:34:56Z",
        "download_url": "/api/files/download/视频标题.mp4"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 50,
      "pages": 3
    }
  }
}
```

### 下载文件

```http
GET /api/files/download/{filename}
Authorization: Bearer YOUR_TOKEN
```

### 删除文件

```http
DELETE /api/files/{filename}
Authorization: Bearer YOUR_TOKEN
```

### 批量删除文件

```http
POST /api/files/delete/batch
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "filenames": [
    "file1.mp4",
    "file2.mp3"
  ]
}
```

## 📱 iOS 快捷指令接口

### 快捷指令下载

```http
POST /api/shortcuts/download
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "format": "mp4",
  "quality": "best"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "下载已开始",
  "task_id": "shortcut_20241213_123456",
  "notification": {
    "title": "下载开始",
    "body": "视频正在下载中，完成后将通知您"
  }
}
```

### 获取快捷指令配置

```http
GET /api/shortcuts/config
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "server_url": "http://localhost:8080",
    "api_endpoint": "/api/shortcuts/download",
    "supported_formats": ["mp4", "mp3", "webm"],
    "supported_qualities": ["best", "worst", "1080p", "720p", "480p"]
  }
}
```

## 🔧 管理员接口

### 系统状态

```http
GET /api/admin/status
Authorization: Bearer YOUR_TOKEN
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "system": {
      "cpu_percent": 25.6,
      "memory_percent": 45.2,
      "disk_percent": 60.8,
      "uptime": 86400
    },
    "yt_dlp": {
      "version": "2024.12.13",
      "status": "healthy"
    },
    "downloads": {
      "active": 2,
      "completed": 150,
      "failed": 5
    }
  }
}
```

### 用户管理

```http
GET /api/admin/users
Authorization: Bearer YOUR_TOKEN
```

```http
POST /api/admin/users
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "username": "newuser",
  "password": "password123",
  "role": "user"
}
```

### 系统配置

```http
GET /api/admin/config
Authorization: Bearer YOUR_TOKEN
```

```http
PUT /api/admin/config
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "max_concurrent_downloads": 3,
  "default_format": "mp4",
  "auto_cleanup_hours": 24
}
```

## 📊 统计接口

### 下载统计

```http
GET /api/stats/downloads
Authorization: Bearer YOUR_TOKEN
```

**查询参数**:
- `period`: 时间段（day/week/month）
- `start_date`: 开始日期
- `end_date`: 结束日期

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_downloads": 1000,
    "successful_downloads": 950,
    "failed_downloads": 50,
    "total_size": 10737418240,
    "daily_stats": [
      {
        "date": "2024-12-13",
        "downloads": 50,
        "size": 1073741824
      }
    ]
  }
}
```

## 🔍 搜索接口

### 搜索视频

```http
GET /api/search?q=QUERY&platform=youtube
Authorization: Bearer YOUR_TOKEN
```

**参数说明**:
- `q`: 搜索关键词（必需）
- `platform`: 平台（可选，youtube/bilibili）
- `limit`: 结果数量（可选，默认 10）

## ❌ 错误响应

### 错误格式

```json
{
  "success": false,
  "error": {
    "code": "INVALID_URL",
    "message": "提供的URL无效",
    "details": "URL格式不正确或不受支持"
  }
}
```

### 常见错误码

- `INVALID_TOKEN`: Token 无效或过期
- `INSUFFICIENT_PERMISSIONS`: 权限不足
- `INVALID_URL`: URL 无效
- `DOWNLOAD_FAILED`: 下载失败
- `FILE_NOT_FOUND`: 文件不存在
- `RATE_LIMIT_EXCEEDED`: 请求频率超限
- `SERVER_ERROR`: 服务器内部错误

## 📝 使用示例

### Python 示例

```python
import requests

# 登录获取 Token
login_data = {
    "username": "admin",
    "password": "admin123"
}
response = requests.post("http://localhost:8080/api/auth/login", json=login_data)
token = response.json()["token"]

# 设置请求头
headers = {"Authorization": f"Bearer {token}"}

# 获取视频信息
info_response = requests.get(
    "http://localhost:8080/api/info",
    params={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
    headers=headers
)
video_info = info_response.json()

# 开始下载
download_data = {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "mp4",
    "quality": "720p"
}
download_response = requests.post(
    "http://localhost:8080/api/download",
    json=download_data,
    headers=headers
)
task_id = download_response.json()["task_id"]
```

### JavaScript 示例

```javascript
// 登录获取 Token
const loginResponse = await fetch('http://localhost:8080/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'admin123'
  })
});
const { token } = await loginResponse.json();

// 下载视频
const downloadResponse = await fetch('http://localhost:8080/api/download', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    format: 'mp4',
    quality: 'best'
  })
});
const { task_id } = await downloadResponse.json();
```
