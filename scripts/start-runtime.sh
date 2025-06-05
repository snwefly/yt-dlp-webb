#!/bin/bash
# 运行时下载模式启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

log_info "🚀 启动 yt-dlp Web (运行时下载模式)"

# 显示构建信息
echo "==========================================="
echo "📦 构建信息:"
echo "   模式: 运行时下载"
echo "   版本: ${VERSION:-unknown}"
echo "   yt-dlp 源: ${YTDLP_SOURCE:-github_release}"
echo "   yt-dlp 版本: ${YTDLP_VERSION:-latest}"
echo "==========================================="

# 处理环境变量文件
log_info "处理环境变量配置..."
if [ -f "/app/.env" ]; then
    log_success "发现 .env 文件"
    # 导出环境变量（过滤注释和空行）
    set -a
    source /app/.env 2>/dev/null || true
    set +a
elif [ -f "/app/.env.example" ]; then
    log_warning "未找到 .env 文件，使用 .env.example"
    cp /app/.env.example /app/.env
    set -a
    source /app/.env 2>/dev/null || true
    set +a
else
    log_warning "未找到环境变量文件，使用默认配置"
fi

# 设置环境变量
export PYTHONPATH="/app:$PYTHONPATH"
# 暂时禁用懒加载以避免 extractor 导入问题
# export YTDLP_NO_LAZY_EXTRACTORS=1
export YTDLP_IGNORE_EXTRACTOR_ERRORS=1

# 确保必要目录存在（以 root 用户运行，无需权限检查）
log_info "检查和创建必要目录..."
for dir in "/app/downloads" "/app/config" "/app/logs" "/app/yt-dlp-cache"; do
    if [ ! -d "$dir" ]; then
        log_info "创建目录: $dir"
        mkdir -p "$dir"
    fi

    # 简单测试写入权限
    if touch "$dir/.write_test" 2>/dev/null; then
        rm -f "$dir/.write_test"
        log_success "目录 $dir 权限正常"
    else
        log_error "无法写入目录 $dir"
        ls -la "$dir" 2>/dev/null || true
    fi
done

# 设置YouTube cookies文件（容器环境优化）
log_info "🍪 设置YouTube cookies配置..."

# 检查是否有用户提供的cookies文件
if [ -f "/app/config/youtube_cookies.txt" ]; then
    log_success "发现用户提供的cookies文件"
    chmod 644 /app/config/youtube_cookies.txt
elif [ -f "/app/webapp/config/youtube_cookies.txt" ]; then
    cp /app/webapp/config/youtube_cookies.txt /app/config/youtube_cookies.txt
    chmod 644 /app/config/youtube_cookies.txt
    log_success "cookies文件已复制到 /app/config/"
else
    log_info "未找到cookies文件，将使用android_vr客户端（无需cookies）"
    log_info "💡 提示：如需下载需要登录的内容，请将cookies保存到 /app/config/youtube_cookies.txt"
    log_info "📖 参考：https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies"

    # 创建示例文件供参考
    if [ -f "/app/config/youtube_cookies.txt.example" ]; then
        log_info "cookies示例文件已存在"
    else
        cat > /app/config/youtube_cookies.txt.example << 'EOF'
# YouTube Cookies 示例文件
# 将此文件重命名为 youtube_cookies.txt 并填入真实cookies
#
# 获取方法：
# 1. 浏览器扩展：Get cookies.txt
# 2. yt-dlp命令：--cookies-from-browser chrome
# 3. 开发者工具手动复制
#
# 格式：domain	flag	path	secure	expiration	name	value
# .youtube.com	TRUE	/	TRUE	1234567890	VISITOR_INFO1_LIVE	your_value_here
EOF
        chmod 644 /app/config/youtube_cookies.txt.example
        log_success "cookies示例文件已创建"
    fi
fi

# 设置容器环境标识
export CONTAINER=true

# 运行时安装缺失的依赖
log_info "📦 检查和安装运行时依赖..."
install_runtime_dependencies() {
    local deps_to_install=()

    # 检查 Flask 核心依赖（最重要的）
    if ! python -c "import flask" 2>/dev/null; then
        log_warning "Flask 未安装，添加到安装列表"
        deps_to_install+=("Flask>=3.1.1")
    fi

    if ! python -c "import flask_login" 2>/dev/null; then
        log_warning "Flask-Login 未安装，添加到安装列表"
        deps_to_install+=("Flask-Login>=0.6.3")
    fi

    if ! python -c "import flask_sqlalchemy" 2>/dev/null; then
        log_warning "Flask-SQLAlchemy 未安装，添加到安装列表"
        deps_to_install+=("Flask-SQLAlchemy>=3.1.1")
    fi

    if ! python -c "import flask_cors" 2>/dev/null; then
        log_warning "flask-cors 未安装，添加到安装列表"
        deps_to_install+=("flask-cors>=6.0.0")
    fi

    if ! python -c "import werkzeug" 2>/dev/null; then
        log_warning "Werkzeug 未安装，添加到安装列表"
        deps_to_install+=("Werkzeug>=3.1.3")
    fi

    if ! python -c "import jwt" 2>/dev/null; then
        log_warning "PyJWT 未安装，添加到安装列表"
        deps_to_install+=("PyJWT>=2.8.0")
    fi

    if ! python -c "import requests" 2>/dev/null; then
        log_warning "requests 未安装，添加到安装列表"
        deps_to_install+=("requests>=2.32.3")
    fi

    if ! python -c "import gunicorn" 2>/dev/null; then
        log_warning "gunicorn 未安装，添加到安装列表"
        deps_to_install+=("gunicorn>=23.0.0")
    fi

    # 检查 Telegram 相关依赖
    if ! python -c "import pyrogram" 2>/dev/null; then
        log_warning "pyrogram 未安装，添加到安装列表"
        deps_to_install+=("pyrogram>=2.0.0")
    fi

    if ! python -c "import filetype" 2>/dev/null; then
        log_warning "filetype 未安装，添加到安装列表"
        deps_to_install+=("filetype>=1.2.0")
    fi

    # 检查 yt-dlp 核心依赖
    if ! python -c "import Crypto" 2>/dev/null; then
        log_warning "pycryptodome 未安装，添加到安装列表"
        deps_to_install+=("pycryptodome>=3.23.0")
    fi

    if ! python -c "import websockets" 2>/dev/null; then
        log_warning "websockets 未安装，添加到安装列表"
        deps_to_install+=("websockets>=15.0.1")
    fi

    if ! python -c "import brotli" 2>/dev/null; then
        log_warning "brotli 未安装，添加到安装列表"
        deps_to_install+=("brotli>=1.1.0")
    fi

    if ! python -c "import mutagen" 2>/dev/null; then
        log_warning "mutagen 未安装，添加到安装列表"
        deps_to_install+=("mutagen>=1.47.0")
    fi

    if ! python -c "import certifi" 2>/dev/null; then
        log_warning "certifi 未安装，添加到安装列表"
        deps_to_install+=("certifi>=2025.4.26")
    fi

    if ! python -c "import psutil" 2>/dev/null; then
        log_warning "psutil 未安装，添加到安装列表"
        deps_to_install+=("psutil>=7.0.0")
    fi

    if ! python -c "import yt_dlp" 2>/dev/null; then
        log_warning "yt-dlp 未安装，添加到安装列表"
        deps_to_install+=("yt-dlp>=2025.5.22")
    fi

    # 安装缺失的依赖
    if [ ${#deps_to_install[@]} -gt 0 ]; then
        log_info "安装缺失的依赖: ${deps_to_install[*]}"
        pip install --no-cache-dir "${deps_to_install[@]}" || log_warning "部分依赖安装失败，继续启动"
    else
        log_success "所有必需依赖已安装"
    fi

    # 尝试安装 TgCrypto（可选，失败不影响启动）
    if ! python -c "import TgCrypto" 2>/dev/null; then
        log_info "尝试安装 TgCrypto 以提升 Telegram 性能..."
        if pip install --no-cache-dir TgCrypto>=1.2.5 2>/dev/null; then
            log_success "TgCrypto 安装成功"
        else
            log_warning "TgCrypto 安装失败，将使用较慢的加密方式"
        fi
    else
        log_success "TgCrypto 已安装"
    fi
}

# 执行运行时依赖安装
install_runtime_dependencies

# 使用通用 yt-dlp 安装脚本
log_info "🔧 安装和验证 yt-dlp..."
if [ -f "/app/scripts/ytdlp_installer.sh" ]; then
    source /app/scripts/ytdlp_installer.sh

    # 运行时下载模式
    if ! install_ytdlp "runtime" "${YTDLP_VERSION:-latest}"; then
        log_error "yt-dlp 安装失败"
        exit 1
    fi

    if ! verify_installation; then
        log_error "yt-dlp 验证失败"
        exit 1
    fi
else
    log_error "yt-dlp 安装脚本不存在"
    exit 1
fi

# 验证 webapp 模块
log_info "🔍 验证 webapp 模块..."
python -c "
import sys
sys.path.insert(0, '/app')
try:
    from webapp.app import create_app
    print('✅ webapp 模块导入成功')
except Exception as e:
    print(f'❌ webapp 模块导入失败: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    log_success "webapp 模块验证通过"
else
    log_error "webapp 模块验证失败"
    exit 1
fi

# 启动 Web 应用
log_success "🌐 启动 Web 服务器..."

cd /app
exec gunicorn \
    --bind 0.0.0.0:8080 \
    --workers 2 \
    --worker-class sync \
    --worker-connections 1000 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --timeout 300 \
    --keep-alive 2 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    "webapp.app:app"
