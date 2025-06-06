#!/bin/bash

# 公共函数库 - 减少启动脚本中的重复代码

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}ℹ️  $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_debug() {
    echo -e "${BLUE}🔍 $1${NC}"
}

# 环境变量处理
process_environment() {
    log_info "🔧 处理环境变量配置..."
    
    # 检查 .env 文件
    if [ -f ".env" ]; then
        log_success "发现 .env 文件"
        # 导出环境变量（如果需要）
        set -a
        source .env
        set +a
    else
        log_warning "未找到 .env 文件，使用默认配置"
    fi
}

# 目录权限处理
setup_directories() {
    local download_dir="${DOWNLOAD_FOLDER:-/app/downloads}"
    
    log_info "🔧 创建并设置目录权限..."
    log_info "📁 下载目录: $download_dir"
    log_info "👤 当前用户: $(whoami)"
    log_info "🆔 用户ID: $(id)"
    
    # 创建目录
    mkdir -p "$download_dir"
    mkdir -p "/app/config"
    mkdir -p "/app/logs"
    mkdir -p "/app/yt-dlp-cache"
    
    # 设置权限
    log_info "🔧 修复目录权限..."
    chmod -R 755 "$download_dir" 2>/dev/null || true
    chmod -R 755 "/app/config" 2>/dev/null || true
    chmod -R 755 "/app/logs" 2>/dev/null || true
    chmod -R 755 "/app/yt-dlp-cache" 2>/dev/null || true
    
    # 权限测试
    log_info "🧪 测试目录写入权限..."
    if touch "$download_dir/.write_test" 2>/dev/null; then
        rm -f "$download_dir/.write_test"
        log_success "下载目录权限验证成功: $download_dir"
    else
        log_warning "下载目录权限测试失败，但继续运行: $download_dir"
    fi
}

# 调试信息输出
show_debug_info() {
    log_debug "调试信息..."
    echo "当前目录: $(pwd)"
    echo "Python路径: $PYTHONPATH"
    echo "目录内容:"
    ls -la
    
    if [ -d "yt_dlp" ]; then
        echo "yt_dlp目录内容:"
        ls -la yt_dlp/
    else
        echo "yt_dlp目录内容:"
        echo "ls: cannot access '/app/yt_dlp/': No such file or directory"
    fi
}

# yt-dlp 安装和验证
install_and_verify_ytdlp() {
    local strategy="${1:-build-time}"
    local version="${2:-latest}"
    
    log_info "🔧 安装和验证 yt-dlp..."
    log_debug "使用${strategy}下载模式"
    log_info "🚀 开始安装 yt-dlp (策略: $strategy, 版本: $version)"
    
    # 检查 yt-dlp 是否可用
    if python3 -c "import yt_dlp; print('✅ yt-dlp 可用'); print('版本:', yt_dlp.version.__version__); print('位置:', yt_dlp.__file__); ydl = yt_dlp.YoutubeDL(); print('✅ yt-dlp 实例创建成功')" 2>/dev/null; then
        log_success "yt-dlp 已经可用，跳过安装"
    else
        case "$strategy" in
            "runtime")
                install_ytdlp_runtime "$version"
                ;;
            "build-time"|"hybrid"|*)
                log_info "构建时模式，yt-dlp 应该已经安装"
                ;;
        esac
    fi
    
    # 验证安装
    log_info "🔍 验证 yt-dlp 安装..."
    if python3 -c "import yt_dlp; print('✅ yt-dlp 可用'); print('版本:', yt_dlp.version.__version__); print('位置:', yt_dlp.__file__); ydl = yt_dlp.YoutubeDL(); print('✅ yt-dlp 实例创建成功')" 2>/dev/null; then
        log_success "yt-dlp 安装验证成功"
    else
        log_error "yt-dlp 验证失败"
        return 1
    fi
}

# 运行时安装 yt-dlp
install_ytdlp_runtime() {
    local version="${1:-latest}"
    
    log_info "📦 运行时安装 yt-dlp..."
    
    # 尝试多种安装方法
    if pip install --no-cache-dir "yt-dlp>=$version" 2>/dev/null; then
        log_success "pip 安装成功"
    elif pip install --no-cache-dir yt-dlp 2>/dev/null; then
        log_success "pip 安装成功（使用默认版本）"
    else
        log_error "pip 安装失败"
        return 1
    fi
}

# 验证 webapp 模块
verify_webapp_module() {
    log_info "🔍 验证 webapp 模块..."
    
    echo "检查关键依赖..."
    python3 -c "
try:
    import flask_login
    print('✅ flask_login 可用')
except ImportError as e:
    print('❌ flask_login 不可用:', e)
    exit(1)

try:
    import flask
    print('✅ flask 可用')
except ImportError as e:
    print('❌ flask 不可用:', e)
    exit(1)

try:
    import webapp
    print('✅ webapp 模块导入成功')
except ImportError as e:
    print('❌ webapp 模块导入失败:', e)
    exit(1)

try:
    from webapp.app import create_app
    app = create_app()
    print('✅ Flask 应用创建成功')
except Exception as e:
    print('❌ Flask 应用创建失败:', e)
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_success "webapp 模块验证通过"
    else
        log_error "webapp 模块验证失败"
        return 1
    fi
}

# 最终依赖检查
final_dependency_check() {
    log_info "🔧 最终依赖检查..."
    
    python3 -c "
import flask_login
print('✅ flask_login 可用')
import flask
print('✅ flask 可用')
print('✅ 所有依赖已就绪')
"
    
    if [ $? -eq 0 ]; then
        log_success "所有依赖已就绪"
    else
        log_error "依赖检查失败"
        return 1
    fi
}

# 启动 Web 服务器
start_web_server() {
    local bind_address="${1:-0.0.0.0:8080}"
    local workers="${2:-2}"
    local app_module="${3:-webapp.app:application}"
    
    log_success "🌐 启动 Web 服务器..."
    echo "使用 Gunicorn 启动..."
    
    cd /app
    exec gunicorn \
        --bind "$bind_address" \
        --workers "$workers" \
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
        "$app_module"
}

# 完整的启动流程
full_startup_sequence() {
    local strategy="${1:-build-time}"
    local version="${2:-latest}"
    
    echo "🚀 启动 yt-dlp Web界面..."
    
    # 1. 处理环境变量
    process_environment
    
    # 2. 设置目录
    setup_directories
    
    # 3. 显示调试信息
    show_debug_info
    
    # 4. 安装和验证 yt-dlp
    install_and_verify_ytdlp "$strategy" "$version"
    
    # 5. 验证 webapp 模块
    verify_webapp_module
    
    # 6. 最终依赖检查
    final_dependency_check
    
    # 7. 启动服务器
    start_web_server
}
