#!/bin/bash
# 混合模式启动脚本

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

log_info "🚀 启动 yt-dlp Web (混合模式)"

# 显示构建信息
echo "==========================================="
echo "📦 构建信息:"
echo "   模式: 混合模式"
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

# 设置YouTube cookies文件
log_info "🍪 设置YouTube cookies文件..."
if [ -f "/app/webapp/config/youtube_cookies.txt" ]; then
    cp /app/webapp/config/youtube_cookies.txt /app/config/youtube_cookies.txt
    chmod 644 /app/config/youtube_cookies.txt
    log_success "cookies文件已复制到 /app/config/"
else
    log_warning "未找到cookies模板文件，创建基础cookies文件"
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
    log_success "基础cookies文件已创建"
fi

# 检查构建时下载状态
log_info "🔍 检查构建时下载状态..."

BUILD_STATUS="unknown"
if [ -f "/app/yt-dlp-source/.download_status" ]; then
    BUILD_STATUS=$(cat /app/yt-dlp-source/.download_status)
    log_info "构建时状态: $BUILD_STATUS"
else
    log_warning "未找到构建时状态文件"
fi

# 修复 extractor 导入问题
log_info "🔧 修复 extractor 导入问题..."
if [ -f "/app/scripts/fix_extractor_imports.py" ]; then
    python /app/scripts/fix_extractor_imports.py || log_warning "extractor 修复失败，继续启动"
fi

# 使用通用 yt-dlp 安装脚本
log_info "🔧 安装和验证 yt-dlp..."
if [ -f "/app/scripts/ytdlp_installer.sh" ]; then
    source /app/scripts/ytdlp_installer.sh

    # 混合模式
    if ! install_ytdlp "hybrid" "${YTDLP_VERSION:-latest}"; then
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



# 跳过 extractor 修复，避免与 yt-dlp 内部机制冲突
log_info "ℹ️ 跳过 extractor 修复，使用 yt-dlp 原生机制"

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
