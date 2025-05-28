#!/bin/bash

# yt-dlp Web界面启动脚本
echo "🚀 启动 yt-dlp Web界面..."

# 设置默认环境变量
export ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
export SECRET_KEY=${SECRET_KEY:-dev-key-change-in-production}
export DOWNLOAD_FOLDER=${DOWNLOAD_FOLDER:-/app/downloads}

# 创建必要的目录
mkdir -p $DOWNLOAD_FOLDER
mkdir -p /app/config

# 设置Python路径
export PYTHONPATH="/app:$PYTHONPATH"

# 验证yt-dlp安装
echo "🔍 检查yt-dlp安装..."
if command -v yt-dlp &> /dev/null; then
    echo "✅ yt-dlp已安装: $(yt-dlp --version)"
else
    echo "❌ yt-dlp未安装"
    exit 1
fi

# 启动Web应用
echo "🌐 启动Web服务器..."
cd /app
python3 -m yt_dlp.web.server --host 0.0.0.0 --port 8080
