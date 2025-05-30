#!/bin/bash

# yt-dlp Web界面启动脚本
echo "🚀 启动 yt-dlp Web界面..."

# 设置默认环境变量
export ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
export SECRET_KEY=${SECRET_KEY:-dev-key-change-in-production}
export DOWNLOAD_FOLDER=${DOWNLOAD_FOLDER:-/app/downloads}
export YTDLP_NO_LAZY_EXTRACTORS=1

# 创建必要的目录并设置权限
echo "🔧 创建并设置目录权限..."
mkdir -p $DOWNLOAD_FOLDER
mkdir -p /app/config

# 设置下载目录权限
echo "📁 下载目录: $DOWNLOAD_FOLDER"
chmod 755 $DOWNLOAD_FOLDER 2>/dev/null || echo "⚠️ 无法设置目录权限"

# 测试目录写入权限
echo "🧪 测试目录写入权限..."
if touch "$DOWNLOAD_FOLDER/test_write_permission" 2>/dev/null; then
    rm "$DOWNLOAD_FOLDER/test_write_permission" 2>/dev/null
    echo "✅ 下载目录权限验证成功: $DOWNLOAD_FOLDER"
else
    echo "⚠️ 下载目录写入权限测试失败，但继续启动..."
    echo "📋 目录信息:"
    ls -la "$DOWNLOAD_FOLDER" 2>/dev/null || echo "无法列出目录内容"
    echo "👤 当前用户: $(whoami)"
    echo "🆔 用户ID: $(id)"
fi

# 设置Python路径
export PYTHONPATH="/app:$PYTHONPATH"

# 调试信息
echo "🔍 调试信息..."
echo "当前目录: $(pwd)"
echo "Python路径: $PYTHONPATH"
echo "目录内容:"
ls -la /app/
echo "yt_dlp目录内容:"
ls -la /app/yt_dlp/ | head -10

# 使用通用 yt-dlp 安装脚本
echo "🔧 安装和验证 yt-dlp..."
if [ -f "/app/scripts/ytdlp_installer.sh" ]; then
    source /app/scripts/ytdlp_installer.sh

    # 根据环境变量或文件存在情况选择模式
    if [ -d "/app/yt_dlp" ] && [ -f "/app/yt_dlp/__init__.py" ]; then
        # 本地模式：存在本地 yt_dlp 目录
        echo "🔍 检测到本地 yt_dlp 目录，使用本地模式"
        INSTALL_MODE="local"
    else
        # 构建时下载模式
        echo "🔍 使用构建时下载模式"
        INSTALL_MODE="build-time"
    fi

    if ! install_ytdlp "$INSTALL_MODE" "${YTDLP_VERSION:-latest}"; then
        echo "❌ yt-dlp 安装失败"
        exit 1
    fi

    if ! verify_installation; then
        echo "❌ yt-dlp 验证失败"
        exit 1
    fi
else
    echo "❌ yt-dlp 安装脚本不存在"
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
