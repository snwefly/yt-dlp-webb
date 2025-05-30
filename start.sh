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

# 验证yt-dlp模块
echo "🔍 检查yt-dlp模块..."
echo "尝试导入 yt_dlp..."
python3 -c "
import sys
import os
print('Python sys.path:')
for p in sys.path:
    print(f'  {p}')
print()
print(f'YTDLP_NO_LAZY_EXTRACTORS: {os.environ.get(\"YTDLP_NO_LAZY_EXTRACTORS\", \"未设置\")}')
print()
try:
    import yt_dlp
    print('✅ yt-dlp模块导入成功')
    print(f'yt-dlp位置: {yt_dlp.__file__}')
    try:
        print(f'yt-dlp版本: {yt_dlp.version.__version__}')
    except:
        print('无法获取版本信息')

    # 测试 extractors 导入
    print('🔍 测试 extractors 导入...')
    try:
        from yt_dlp.extractor import import_extractors
        import_extractors()
        print('✅ extractors 导入成功')

        # 测试特定的 extractor
        try:
            from yt_dlp.extractor.screen9 import Screen9IE
            print('✅ screen9 extractor 导入成功')
        except Exception as e:
            print(f'⚠️ screen9 extractor 导入失败: {e}')

    except Exception as e:
        print(f'⚠️ extractors 导入失败: {e}')

except Exception as e:
    print(f'❌ yt-dlp模块导入失败: {e}')
    import traceback
    traceback.print_exc()
"

# 简化的验证（不退出）
if python3 -c "import yt_dlp" 2>/dev/null; then
    echo "✅ yt-dlp模块验证成功"
else
    echo "⚠️ yt-dlp模块验证失败，但继续启动..."
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
