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

# 验证yt-dlp模块
echo "🔍 检查yt-dlp模块..."
if python3 -c "import yt_dlp; print('✅ yt-dlp模块可用')" 2>/dev/null; then
    echo "✅ yt-dlp模块验证成功"
else
    echo "❌ yt-dlp模块不可用"
    exit 1
fi

# 启动Web应用
echo "🌐 启动Web服务器..."
cd /app

# 使用 gunicorn 启动（生产环境）
if command -v gunicorn &> /dev/null; then
    echo "使用 Gunicorn 启动..."
    gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 webapp.app:app
else
    echo "使用 Flask 开发服务器启动..."
    python3 -m webapp.server --host 0.0.0.0 --port 8080 --no-browser
fi
