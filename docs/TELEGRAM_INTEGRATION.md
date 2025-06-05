# Telegram 集成指南

## 🤖 功能概述

YT-DLP Web 提供完整的 Telegram 集成功能：

### ✨ 主要功能
- 📤 **自动推送** - 下载完成后自动发送文件到 Telegram
- 💬 **消息通知** - 下载状态和错误信息推送
- 📁 **文件传输** - 支持大文件（>50MB）传输
- 🔗 **远程下载** - 通过 Telegram 发送链接触发下载
- ⚙️ **Web 配置** - 在 Web 界面中配置所有参数

### 🏗️ 技术架构
- **Bot API** - 用于消息推送和小文件传输
- **Pyrogram** - 用于大文件传输和高级功能
- **自动回退** - Bot API 失败时自动切换到 Pyrogram

## 🚀 快速配置

### 步骤一：创建 Telegram Bot

1. **联系 @BotFather**
   ```
   /start
   /newbot
   ```

2. **设置 Bot 信息**
   ```
   Bot Name: YT-DLP Web Bot
   Bot Username: your_ytdlp_bot
   ```

3. **获取 Bot Token**
   ```
   Token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

### 步骤二：获取 Chat ID

1. **添加 Bot 到群组或私聊**
2. **发送任意消息给 Bot**
3. **访问以下链接获取 Chat ID**：
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
4. **在返回的 JSON 中找到 `chat.id`**

### 步骤三：获取 API 凭据（大文件支持）

1. **访问** https://my.telegram.org
2. **登录你的 Telegram 账号**
3. **进入 "API development tools"**
4. **创建新应用**：
   ```
   App title: YT-DLP Web
   Short name: ytdlp-web
   Platform: Other
   ```
5. **获取 `api_id` 和 `api_hash`**

### 步骤四：Web 界面配置

1. **登录 YT-DLP Web 管理界面**
2. **进入 "设置" → "Telegram 配置"**
3. **填写配置信息**：
   ```
   Bot Token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   Chat ID: -1001234567890
   API ID: 12345678
   API Hash: abcdef1234567890abcdef1234567890
   ```
4. **点击 "测试连接" 验证配置**
5. **保存配置**

## 🔧 详细配置

### 环境变量配置
```env
# .env 文件
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890

# 可选配置
TELEGRAM_ENABLED=true
TELEGRAM_SEND_FILES=true
TELEGRAM_SEND_MESSAGES=true
TELEGRAM_MAX_FILE_SIZE=2000  # MB
```

### Docker Compose 配置
```yaml
# docker-compose.yml
services:
  yt-dlp-web:
    environment:
      - TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
      - TELEGRAM_CHAT_ID=-1001234567890
      - TELEGRAM_API_ID=12345678
      - TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
```

### 数据库配置
配置信息会自动保存到数据库中，支持运行时修改。

## 📤 推送功能

### 自动文件推送
下载完成后，系统会自动：

1. **检测文件大小**
   - 小文件（<50MB）：使用 Bot API
   - 大文件（≥50MB）：使用 Pyrogram

2. **智能文件类型检测**
   ```python
   # 自动检测并设置正确的文件类型
   .mp4, .mkv, .avi → video
   .mp3, .flac, .wav → audio
   .jpg, .png, .gif → photo
   其他 → document
   ```

3. **生成缩略图**（视频文件）
   - 自动提取视频第一帧作为缩略图
   - 支持自定义缩略图时间点

4. **添加文件信息**
   ```
   📹 视频标题
   🎬 频道：频道名称
   ⏱️ 时长：01:23:45
   📊 大小：1.2 GB
   🔗 原链接：https://...
   ```

### 消息推送
系统会推送以下消息：

1. **下载开始**
   ```
   🚀 开始下载
   📹 标题：视频标题
   🔗 链接：https://...
   ```

2. **下载完成**
   ```
   ✅ 下载完成
   📁 文件：video.mp4
   📊 大小：1.2 GB
   ⏱️ 用时：5分30秒
   ```

3. **下载失败**
   ```
   ❌ 下载失败
   🔗 链接：https://...
   💬 错误：错误信息
   ```

## 🔗 远程下载功能

### 通过 Telegram 触发下载

1. **发送链接给 Bot**
   ```
   https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```

2. **Bot 自动识别并开始下载**
3. **下载完成后自动发送文件**

### 支持的链接格式
- YouTube: `https://youtube.com/watch?v=...`
- Bilibili: `https://bilibili.com/video/...`
- 其他 yt-dlp 支持的平台

### 命令支持
```
/start - 开始使用
/help - 帮助信息
/status - 查看下载状态
/list - 查看下载历史
```

## 🛠️ 高级配置

### 自定义消息模板
```python
# 在 Web 界面的高级设置中配置
MESSAGE_TEMPLATES = {
    'download_start': '🚀 开始下载：{title}',
    'download_complete': '✅ 下载完成：{filename}',
    'download_error': '❌ 下载失败：{error}'
}
```

### 文件过滤规则
```python
# 配置哪些文件类型需要推送
FILE_FILTER = {
    'video': True,      # 推送视频文件
    'audio': True,      # 推送音频文件
    'subtitle': False,  # 不推送字幕文件
    'thumbnail': False, # 不推送缩略图
}
```

### 大小限制
```python
# 配置文件大小限制
MAX_FILE_SIZE = 2000  # MB，超过此大小不推送
COMPRESS_LARGE_FILES = True  # 是否压缩大文件
```

## 🔍 故障排除

### 常见问题

#### 1. Bot Token 无效
```
错误：401 Unauthorized
解决：检查 Bot Token 是否正确，确保没有多余空格
```

#### 2. Chat ID 错误
```
错误：400 Bad Request: chat not found
解决：
1. 确保 Bot 已添加到群组
2. 检查 Chat ID 格式（群组 ID 通常以 -100 开头）
3. 确保 Bot 有发送消息权限
```

#### 3. API 凭据问题
```
错误：API_ID_INVALID 或 API_HASH_INVALID
解决：
1. 重新从 https://my.telegram.org 获取凭据
2. 确保 API ID 是数字，API Hash 是 32 位字符串
```

#### 4. 文件发送失败
```
错误：File too large 或 Request timeout
解决：
1. 检查文件大小是否超过限制
2. 检查网络连接
3. 尝试重新发送
```

### 调试方法

#### 1. 测试连接
在 Web 界面点击"测试连接"按钮，系统会：
- 验证 Bot Token
- 发送测试消息
- 检查 API 凭据

#### 2. 查看日志
```bash
# 查看 Telegram 相关日志
docker-compose logs yt-dlp-web | grep -i telegram

# 查看详细错误信息
docker-compose logs yt-dlp-web | grep -i error
```

#### 3. 手动测试
```bash
# 测试 Bot API
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT_ID>&text=Test message"

# 检查 Bot 信息
curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

## 📊 监控和统计

### 推送统计
在 Web 界面可以查看：
- 总推送次数
- 成功/失败比例
- 文件传输统计
- 错误日志

### 性能监控
```python
# 监控指标
- 消息发送延迟
- 文件上传速度
- API 调用频率
- 错误率统计
```

## 🔒 安全考虑

### Bot 权限管理
1. **最小权限原则**：只给 Bot 必要的权限
2. **群组管理**：在群组中设置 Bot 为管理员（如需要）
3. **私聊优先**：推荐使用私聊而非群组

### 数据安全
1. **Token 保护**：不要在日志中暴露 Token
2. **传输加密**：所有通信都通过 HTTPS
3. **本地存储**：敏感信息加密存储

### 访问控制
```python
# 配置允许的用户 ID
ALLOWED_USERS = [123456789, 987654321]

# 配置管理员用户
ADMIN_USERS = [123456789]
```

---

**📖 相关文档：**
- [API 接口文档](API_DOCUMENTATION.md)
- [故障排除指南](TROUBLESHOOTING.md)
- [高级配置选项](ADVANCED_CONFIGURATION.md)
