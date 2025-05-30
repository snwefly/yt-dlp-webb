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

# 设置环境变量
export PYTHONPATH="/app:$PYTHONPATH"
export YTDLP_NO_LAZY_EXTRACTORS=1

# 创建必要目录
log_info "创建必要目录..."
mkdir -p /app/downloads /app/config /app/logs /app/yt-dlp-cache

# 检查权限
log_info "检查目录权限..."
if [ -w "/app/downloads" ]; then
    log_success "下载目录权限正常"
else
    log_warning "下载目录权限不足，尝试修复..."
    chmod 755 /app/downloads 2>/dev/null || true
fi

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
    "webapp.app:create_app()"
