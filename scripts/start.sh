#!/bin/bash

# yt-dlp Web界面启动脚本 - 构建时下载模式

# 导入公共函数库
if [ -f "/app/scripts/common_functions.sh" ]; then
    source /app/scripts/common_functions.sh
    # 使用公共函数的完整启动流程
    full_startup_sequence "build-time" "${YTDLP_VERSION:-latest}"
else
    # 备用启动逻辑（如果公共函数库不存在）
    echo "⚠️ 公共函数库不存在，使用备用启动逻辑"

    echo "🚀 启动 yt-dlp Web界面..."

    # 处理环境变量文件
    echo "🔧 处理环境变量配置..."
    if [ -f "/app/.env" ]; then
        echo "✅ 发现 .env 文件"
        set -a
        source /app/.env 2>/dev/null || true
        set +a
    else
        echo "⚠️ 未找到环境变量文件，使用默认配置"
    fi

    # 设置默认环境变量
    export ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
    export ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
    export SECRET_KEY=${SECRET_KEY:-dev-key-change-in-production}
    export DOWNLOAD_FOLDER=${DOWNLOAD_FOLDER:-/app/downloads}
    export YTDLP_NO_LAZY_EXTRACTORS=1
    export YTDLP_IGNORE_EXTRACTOR_ERRORS=1

    # 创建必要的目录
    echo "🔧 创建并设置目录权限..."
    mkdir -p $DOWNLOAD_FOLDER /app/config /app/logs /app/yt-dlp-cache

    # 简化的启动流程（备用）
    export PYTHONPATH="/app:$PYTHONPATH"

    # 基础依赖检查
    echo "📦 检查基础依赖..."
    python3 -c "import flask, flask_login, webapp" 2>/dev/null || {
        echo "❌ 关键依赖缺失，尝试安装..."
        pip install --no-cache-dir Flask Flask-Login Flask-SQLAlchemy gunicorn
    }

    # 启动应用
    echo "🌐 启动Web服务器..."
    cd /app
    exec gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --access-logfile - --error-logfile - "webapp.app:application"
fi


