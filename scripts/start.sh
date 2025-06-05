#!/bin/bash

# yt-dlp Web界面启动脚本
echo "🚀 启动 yt-dlp Web界面..."

# 处理环境变量文件
echo "🔧 处理环境变量配置..."
if [ -f "/app/.env" ]; then
    echo "✅ 发现 .env 文件"
    # 导出环境变量（过滤注释和空行）
    set -a
    source /app/.env 2>/dev/null || true
    set +a
elif [ -f "/app/.env.example" ]; then
    echo "⚠️ 未找到 .env 文件，使用 .env.example"
    cp /app/.env.example /app/.env
    set -a
    source /app/.env 2>/dev/null || true
    set +a
else
    echo "⚠️ 未找到环境变量文件，使用默认配置"
fi

# 设置默认环境变量（如果没有从 .env 文件中加载）
export ADMIN_USERNAME=${ADMIN_USERNAME:-admin}
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-admin123}
export SECRET_KEY=${SECRET_KEY:-dev-key-change-in-production}
export DOWNLOAD_FOLDER=${DOWNLOAD_FOLDER:-/app/downloads}
export YTDLP_NO_LAZY_EXTRACTORS=1
export YTDLP_IGNORE_EXTRACTOR_ERRORS=1

# 创建必要的目录并设置权限
echo "🔧 创建并设置目录权限..."
mkdir -p $DOWNLOAD_FOLDER
mkdir -p /app/config
mkdir -p /app/logs
mkdir -p /app/yt-dlp-cache

# 设置cookies文件
echo "🍪 设置YouTube cookies文件..."
if [ -f "/app/webapp/config/youtube_cookies.txt" ]; then
    cp /app/webapp/config/youtube_cookies.txt /app/config/youtube_cookies.txt
    chmod 644 /app/config/youtube_cookies.txt
    echo "✅ cookies文件已复制到 /app/config/"
else
    echo "⚠️ 未找到cookies模板文件，创建基础cookies文件"
    cat > /app/config/youtube_cookies.txt << 'EOF'
# Netscape HTTP Cookie File
# This is a generated file! Do not edit.

# YouTube基础cookies - 根据官方FAQ配置以避免bot检测
# 格式: domain	domain_specified	path	secure	expiration	name	value
.youtube.com	TRUE	/	TRUE	1767225600	CONSENT	YES+cb.20210328-17-p0.en+FX+667
.youtube.com	TRUE	/	FALSE	1767225600	PREF	tz=UTC&hl=en&f1=50000000
.youtube.com	TRUE	/	TRUE	1767225600	SOCS	CAI
.youtube.com	TRUE	/	FALSE	1767225600	VISITOR_INFO1_LIVE	fPQ4jCL6EiE
EOF
    chmod 644 /app/config/youtube_cookies.txt
    echo "✅ 基础cookies文件已创建"
fi

# 强制修复目录权限
echo "📁 下载目录: $DOWNLOAD_FOLDER"
echo "👤 当前用户: $(whoami)"
echo "🆔 用户ID: $(id)"

# 尝试多种方式修复权限
echo "🔧 修复目录权限..."
chmod 777 $DOWNLOAD_FOLDER 2>/dev/null || echo "⚠️ chmod 777 失败"
chmod 777 /app/config 2>/dev/null || echo "⚠️ chmod /app/config 失败"
chmod 777 /app/logs 2>/dev/null || echo "⚠️ chmod /app/logs 失败"
chmod 777 /app/yt-dlp-cache 2>/dev/null || echo "⚠️ chmod /app/yt-dlp-cache 失败"

# 以 root 用户运行，确保目录权限正确
if [ "$(id -u)" = "0" ]; then
    echo "🔧 以 root 身份确保目录权限..."
    # 现在以 root 用户运行，不需要 chown 到 ytdlp
    echo "✅ 以 root 用户运行，拥有完全权限"
else
    echo "⚠️ 非 root 用户运行，可能遇到权限问题"
fi

# 测试目录写入权限
echo "🧪 测试目录写入权限..."
if touch "$DOWNLOAD_FOLDER/test_write_permission" 2>/dev/null; then
    rm "$DOWNLOAD_FOLDER/test_write_permission" 2>/dev/null
    echo "✅ 下载目录权限验证成功: $DOWNLOAD_FOLDER"
else
    echo "⚠️ 下载目录写入权限测试失败"
    echo "📋 详细目录信息:"
    ls -la "$DOWNLOAD_FOLDER" 2>/dev/null || echo "无法列出目录内容"
    ls -la "$(dirname $DOWNLOAD_FOLDER)" 2>/dev/null || echo "无法列出父目录内容"

    # 尝试创建临时目录作为备用
    TEMP_DOWNLOAD_DIR="/tmp/downloads"
    echo "🔄 尝试使用临时下载目录: $TEMP_DOWNLOAD_DIR"
    mkdir -p "$TEMP_DOWNLOAD_DIR"
    chmod 777 "$TEMP_DOWNLOAD_DIR" 2>/dev/null
    if touch "$TEMP_DOWNLOAD_DIR/test_write_permission" 2>/dev/null; then
        rm "$TEMP_DOWNLOAD_DIR/test_write_permission" 2>/dev/null
        export DOWNLOAD_FOLDER="$TEMP_DOWNLOAD_DIR"
        echo "✅ 使用临时下载目录: $TEMP_DOWNLOAD_DIR"
    else
        echo "❌ 临时目录也无法写入，但继续启动..."
    fi
fi

# 设置Python路径
export PYTHONPATH="/app:$PYTHONPATH"

# 运行时安装缺失的依赖
echo "📦 检查和安装运行时依赖..."
install_runtime_dependencies() {
    local deps_to_install=()

    # 检查 Telegram 相关依赖
    if ! python -c "import pyrogram" 2>/dev/null; then
        echo "⚠️ pyrogram 未安装，添加到安装列表"
        deps_to_install+=("pyrogram>=2.0.0")
    fi

    if ! python -c "import filetype" 2>/dev/null; then
        echo "⚠️ filetype 未安装，添加到安装列表"
        deps_to_install+=("filetype>=1.2.0")
    fi

    # 检查 yt-dlp 核心依赖
    if ! python -c "import Crypto" 2>/dev/null; then
        echo "⚠️ pycryptodome 未安装，添加到安装列表"
        deps_to_install+=("pycryptodome>=3.23.0")
    fi

    if ! python -c "import websockets" 2>/dev/null; then
        echo "⚠️ websockets 未安装，添加到安装列表"
        deps_to_install+=("websockets>=15.0.1")
    fi

    if ! python -c "import brotli" 2>/dev/null; then
        echo "⚠️ brotli 未安装，添加到安装列表"
        deps_to_install+=("brotli>=1.1.0")
    fi

    if ! python -c "import mutagen" 2>/dev/null; then
        echo "⚠️ mutagen 未安装，添加到安装列表"
        deps_to_install+=("mutagen>=1.47.0")
    fi

    if ! python -c "import certifi" 2>/dev/null; then
        echo "⚠️ certifi 未安装，添加到安装列表"
        deps_to_install+=("certifi>=2025.4.26")
    fi

    if ! python -c "import psutil" 2>/dev/null; then
        echo "⚠️ psutil 未安装，添加到安装列表"
        deps_to_install+=("psutil>=7.0.0")
    fi

    if ! python -c "import yt_dlp" 2>/dev/null; then
        echo "⚠️ yt-dlp 未安装，添加到安装列表"
        deps_to_install+=("yt-dlp>=2025.5.22")
    fi

    # 安装缺失的依赖
    if [ ${#deps_to_install[@]} -gt 0 ]; then
        echo "🔧 安装缺失的依赖: ${deps_to_install[*]}"
        pip install --no-cache-dir "${deps_to_install[@]}" || echo "⚠️ 部分依赖安装失败，继续启动"
    else
        echo "✅ 所有必需依赖已安装"
    fi

    # 尝试安装 TgCrypto（可选，失败不影响启动）
    if ! python -c "import TgCrypto" 2>/dev/null; then
        echo "🔧 尝试安装 TgCrypto 以提升 Telegram 性能..."
        if pip install --no-cache-dir TgCrypto>=1.2.5 2>/dev/null; then
            echo "✅ TgCrypto 安装成功"
        else
            echo "⚠️ TgCrypto 安装失败，将使用较慢的加密方式"
        fi
    else
        echo "✅ TgCrypto 已安装"
    fi
}

# 执行运行时依赖安装
install_runtime_dependencies

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

# 测试应用是否可以正确导入
echo "🧪 测试应用导入..."
python3 -c "
import sys
sys.path.insert(0, '/app')
try:
    from webapp.app import create_app
    app = create_app()
    print('✅ 应用创建成功')
    print(f'✅ 注册的路由数量: {len(app.url_map._rules)}')
    for rule in app.url_map.iter_rules():
        print(f'  - {rule.rule} -> {rule.endpoint}')
except Exception as e:
    print(f'❌ 应用创建失败: {e}')
    import traceback
    traceback.print_exc()
    exit(1)
"

# 使用 gunicorn 启动（生产环境）
if command -v gunicorn &> /dev/null; then
    echo "使用 Gunicorn 启动..."
    exec gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 --access-logfile - --error-logfile - webapp.app:app
else
    echo "使用 Flask 开发服务器启动..."
    exec python3 -c "
import sys
sys.path.insert(0, '/app')
from webapp.app import create_app
app = create_app()
app.run(host='0.0.0.0', port=8080, debug=False)
"
fi
