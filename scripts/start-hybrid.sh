#!/bin/bash
# yt-dlp Web界面启动脚本 - 混合模式

# 导入公共函数库
if [ -f "/app/scripts/common_functions.sh" ]; then
    source /app/scripts/common_functions.sh
    # 使用公共函数的完整启动流程
    full_startup_sequence "hybrid" "${YTDLP_VERSION:-latest}"
else
    # 备用启动逻辑
    echo "⚠️ 公共函数库不存在，使用备用启动逻辑"
    echo "🚀 启动 yt-dlp Web界面（混合模式）..."
    
    # 基础环境设置
    export PYTHONPATH="/app:$PYTHONPATH"
    export DOWNLOAD_FOLDER=${DOWNLOAD_FOLDER:-/app/downloads}
    mkdir -p $DOWNLOAD_FOLDER /app/config /app/logs /app/yt-dlp-cache
    
    # 混合模式安装
    echo "📦 混合模式安装依赖..."
    pip install --no-cache-dir yt-dlp Flask Flask-Login Flask-SQLAlchemy gunicorn
    
    # 启动应用
    echo "🌐 启动Web服务器..."
    cd /app
    exec gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --access-logfile - --error-logfile - "webapp.app:application"
fi
