#!/bin/bash

# yt-dlp Web界面启动脚本
echo "🚀 启动 yt-dlp Web界面..."

# 设置默认环境变量
export ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
export SECRET_KEY=${SECRET_KEY:-dev-key-change-in-production} # 强烈建议在生产中覆盖此值
export DOWNLOAD_FOLDER=${DOWNLOAD_FOLDER:-/app/downloads}
# export FLASK_ENV=${FLASK_ENV:-production} 

# 创建必要的目录
mkdir -p "$DOWNLOAD_FOLDER"
mkdir -p "/app/config"

# Python路径设置
# /app 会是 PYTHONPATH 的一部分，我们的应用代码在其子目录 /app/web/ 下
export PYTHONPATH="/app:$PYTHONPATH" 

# 验证yt-dlp命令行工具安装
echo "🔍 检查yt-dlp命令行工具安装..."
if command -v yt-dlp &> /dev/null; then
    echo "✅ yt-dlp命令行工具已安装: $(yt-dlp --version)"
else
    echo "❌ yt-dlp命令行工具未安装或不在PATH中"
fi

# 启动Web应用
echo "🌐 启动Web服务器..."
cd /app # 确保当前工作目录是 /app
# 关键修改：模块路径从 yt_dlp.web.server 修改为 web.server
python3 -m web.server --host 0.0.0.0 --port 8080