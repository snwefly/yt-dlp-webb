# iOS 快捷指令使用指南

## 概述

本项目提供了专门为iOS快捷指令设计的API端点，让iOS用户可以通过快捷指令直接下载视频到设备本地。

## API端点说明

### 1. 直接下载模式（推荐）
**端点**: `POST /api/shortcuts/download-direct`

**特点**:
- 同步下载，直接返回文件
- 适合小文件和快速下载
- 无需轮询状态

**请求参数**:
```json
{
    "url": "https://www.youtube.com/watch?v=...",
    "audio_only": "false",
    "quality": "best"
}
```

**响应**: 直接返回文件流，iOS快捷指令可直接保存

### 2. 异步下载模式
**端点**: `POST /api/shortcuts/download`

**特点**:
- 异步下载，适合大文件
- 需要轮询下载状态
- 支持进度跟踪

**工作流程**:
1. 提交下载请求 → 获得 download_id
2. 轮询状态 `GET /api/download/{download_id}/status`
3. 下载完成后获取文件 `GET /api/shortcuts/download/{download_id}/file`

## iOS快捷指令配置

### 方案一：直接下载快捷指令

```
1. 获取剪贴板/分享的URL
2. 发送POST请求到 /api/shortcuts/download-direct
3. 将返回的文件保存到相册或文件app
```

**快捷指令步骤**:
1. **获取输入** - 从剪贴板或分享表单获取URL
2. **获取网页内容** - POST请求
   - URL: `http://你的服务器IP:8080/api/shortcuts/download-direct`
   - 方法: POST
   - 请求体: JSON
   ```json
   {
       "url": "[获取的URL]",
       "audio_only": "false",
       "quality": "best"
   }
   ```
3. **保存到相册** - 如果是视频文件
4. **保存到文件** - 如果是音频文件

### 方案二：异步下载快捷指令（适合大文件）

```
1. 提交下载请求
2. 等待下载完成（轮询状态）
3. 下载文件到本地
```

**快捷指令步骤**:
1. **获取输入** - URL
2. **提交下载** - POST到 `/api/shortcuts/download`
3. **等待循环** - 每5秒检查一次状态
4. **下载文件** - 完成后从 `/api/shortcuts/download/{id}/file` 获取
5. **保存文件**

## 参数说明

### audio_only
- `"true"`: 仅下载音频
- `"false"`: 下载视频（默认）

### quality
- `"best"`: 最佳质量（默认）
- `"worst"`: 最低质量
- `"720"`: 720p视频
- `"480"`: 480p视频
- `"best[height<=720]"`: 不超过720p的最佳质量

## 示例快捷指令代码

### 简单视频下载器

```
动作1: 获取剪贴板
动作2: 获取网页内容
  - URL: http://你的服务器:8080/api/shortcuts/download-direct
  - 方法: POST
  - 头部: Content-Type: application/json
  - 请求体: {"url":"[剪贴板]","audio_only":"false","quality":"best"}
动作3: 保存到相册
```

### 音频提取器

```
动作1: 获取剪贴板
动作2: 获取网页内容
  - URL: http://你的服务器:8080/api/shortcuts/download-direct
  - 方法: POST
  - 头部: Content-Type: application/json
  - 请求体: {"url":"[剪贴板]","audio_only":"true","quality":"320"}
动作3: 保存到文件
  - 位置: iCloud Drive/Downloads
```

## 错误处理

API会返回以下错误状态：

- `400`: 缺少URL参数
- `404`: 下载ID不存在
- `500`: 下载失败或服务器错误

快捷指令应该检查HTTP状态码并显示相应的错误信息。

## 注意事项

1. **服务器地址**: 将示例中的IP地址替换为你的实际服务器地址
2. **网络权限**: 确保iOS设备可以访问服务器
3. **文件大小**: 直接下载模式适合小于100MB的文件
4. **超时设置**: 对于大文件，建议设置较长的超时时间
5. **存储权限**: 确保快捷指令有相册和文件访问权限

## 部署建议

1. **HTTPS**: 生产环境建议使用HTTPS
2. **认证**: 可以添加API密钥认证
3. **限流**: 防止滥用，限制下载频率
4. **清理**: 定期清理临时文件

## 快捷指令分享

你可以创建快捷指令后通过以下方式分享：
1. 导出为.shortcut文件
2. 生成iCloud链接分享
3. 发布到快捷指令库

这样iOS用户就可以一键安装并使用视频下载功能了。
