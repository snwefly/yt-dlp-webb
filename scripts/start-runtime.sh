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

# 运行时下载 yt-dlp
log_info "🔽 运行时下载 yt-dlp..."

# 使用源管理器下载
if [ -f "/app/scripts/ytdlp_source_manager.py" ]; then
    log_info "使用源管理器下载 yt-dlp..."
    cd /app
    
    if python scripts/ytdlp_source_manager.py \
        --config config/ytdlp-source.yml \
        --target /app/yt-dlp-runtime; then
        
        log_success "yt-dlp 下载成功"
        export PYTHONPATH="/app/yt-dlp-runtime:$PYTHONPATH"
    else
        log_warning "源管理器下载失败，尝试 pip 安装..."
        
        # 回退到 pip 安装
        YTDLP_VERSION=${YTDLP_VERSION:-"latest"}
        if [ "$YTDLP_VERSION" = "latest" ]; then
            pip install --no-cache-dir yt-dlp
        else
            pip install --no-cache-dir "yt-dlp==$YTDLP_VERSION"
        fi
        
        log_success "yt-dlp pip 安装成功"
    fi
else
    log_warning "源管理器不存在，使用 pip 安装..."
    
    # 直接 pip 安装
    YTDLP_VERSION=${YTDLP_VERSION:-"latest"}
    if [ "$YTDLP_VERSION" = "latest" ]; then
        pip install --no-cache-dir yt-dlp
    else
        pip install --no-cache-dir "yt-dlp==$YTDLP_VERSION"
    fi
    
    log_success "yt-dlp pip 安装成功"
fi

# 验证 yt-dlp 安装
log_info "🔍 验证 yt-dlp 安装..."
python -c "
import sys
sys.path.insert(0, '/app')
try:
    import yt_dlp
    print('✅ yt-dlp 导入成功')
    print(f'yt-dlp 版本: {yt_dlp.__version__}')
    print(f'yt-dlp 位置: {yt_dlp.__file__}')
    
    # 测试创建实例
    ydl = yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True})
    print('✅ yt-dlp 实例创建成功')
except Exception as e:
    print(f'❌ yt-dlp 验证失败: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    log_success "yt-dlp 验证通过"
else
    log_error "yt-dlp 验证失败"
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
