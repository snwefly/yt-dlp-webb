#!/bin/bash
# 通用 yt-dlp 安装和管理脚本
# 供所有启动脚本使用，确保 yt-dlp 正确安装

# 日志函数
log_info() { echo "ℹ️  $1"; }
log_success() { echo "✅ $1"; }
log_warning() { echo "⚠️  $1"; }
log_error() { echo "❌ $1"; }

# 检查 yt-dlp 是否可用
check_ytdlp() {
    python -c "
import sys
try:
    import yt_dlp
    print('✅ yt-dlp 可用')
    print(f'版本: {yt_dlp.__version__}')
    print(f'位置: {yt_dlp.__file__}')

    # 测试创建实例
    ydl = yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'ignoreerrors': True})
    print('✅ yt-dlp 实例创建成功')
    sys.exit(0)
except ImportError as e:
    print(f'❌ yt-dlp 导入失败: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ yt-dlp 测试失败: {e}')
    sys.exit(1)
" 2>/dev/null
}

# 显示调试信息
show_debug_info() {
    log_info "调试信息:"
    echo "PYTHONPATH: $PYTHONPATH"
    echo "Python 版本: $(python --version)"
    echo "pip 列表 (yt-dlp 相关):"
    pip list | grep -i yt-dlp || echo "  未找到 yt-dlp"
    echo "Python 路径:"
    python -c "import sys; [print(f'  {p}') for p in sys.path]"
}

# 使用 pip 安装 yt-dlp
install_with_pip() {
    local version=${1:-"latest"}

    log_info "🔄 使用 pip 安装 yt-dlp..."

    if [ "$version" = "latest" ]; then
        if pip install --no-cache-dir --force-reinstall yt-dlp; then
            log_success "pip 安装成功"
            return 0
        else
            log_error "pip 安装失败"
            return 1
        fi
    else
        if pip install --no-cache-dir --force-reinstall "yt-dlp==$version"; then
            log_success "pip 安装成功 (版本: $version)"
            return 0
        else
            log_error "pip 安装失败 (版本: $version)"
            return 1
        fi
    fi
}

# 使用构建时下载的 yt-dlp
use_build_time_ytdlp() {
    local source_dir="/app/yt-dlp-source"

    if [ -d "$source_dir/yt_dlp" ] && [ -f "$source_dir/yt_dlp/__init__.py" ]; then
        log_info "🔍 检查构建时下载的 yt-dlp..."

        # 临时设置 PYTHONPATH 进行测试
        export PYTHONPATH="$source_dir:$PYTHONPATH"

        if check_ytdlp; then
            log_success "构建时下载的 yt-dlp 可用"
            return 0
        else
            log_warning "构建时下载的 yt-dlp 不可用"
            # 移除无效的 PYTHONPATH
            export PYTHONPATH="${PYTHONPATH#$source_dir:}"
            return 1
        fi
    else
        log_warning "构建时下载的 yt-dlp 文件不完整"
        return 1
    fi
}

# 使用本地 yt-dlp 文件
use_local_ytdlp() {
    local local_dir="/app"

    if [ -d "$local_dir/yt_dlp" ] && [ -f "$local_dir/yt_dlp/__init__.py" ]; then
        log_info "🔍 检查本地 yt-dlp 文件..."

        # 确保 /app 在 PYTHONPATH 中
        if [[ ":$PYTHONPATH:" != *":$local_dir:"* ]]; then
            export PYTHONPATH="$local_dir:$PYTHONPATH"
        fi

        if check_ytdlp; then
            log_success "本地 yt-dlp 文件可用"
            return 0
        else
            log_warning "本地 yt-dlp 文件不可用"
            return 1
        fi
    else
        log_warning "本地 yt-dlp 文件不存在或不完整"
        return 1
    fi
}

# 使用运行时下载的 yt-dlp
use_runtime_ytdlp() {
    local runtime_dir="/app/yt-dlp-runtime"
    local source_manager="/app/scripts/ytdlp_source_manager.py"
    local config_file="/app/config/ytdlp-source.yml"

    if [ ! -f "$source_manager" ]; then
        log_warning "源管理器不存在: $source_manager"
        return 1
    fi

    log_info "🔄 使用源管理器运行时下载..."
    cd /app

    if python "$source_manager" --config "$config_file" --target "$runtime_dir"; then
        log_success "运行时下载成功"

        # 设置 PYTHONPATH 并测试
        export PYTHONPATH="$runtime_dir:$PYTHONPATH"

        if check_ytdlp; then
            log_success "运行时下载的 yt-dlp 可用"
            return 0
        else
            log_warning "运行时下载的 yt-dlp 不可用"
            # 移除无效的 PYTHONPATH
            export PYTHONPATH="${PYTHONPATH#$runtime_dir:}"
            return 1
        fi
    else
        log_warning "运行时下载失败"
        return 1
    fi
}

# 主安装函数
install_ytdlp() {
    local strategy=${1:-"auto"}
    local version=${2:-"latest"}

    log_info "🚀 开始安装 yt-dlp (策略: $strategy, 版本: $version)"

    # 首先检查是否已经可用
    if check_ytdlp; then
        log_success "yt-dlp 已经可用，跳过安装"
        return 0
    fi

    # 显示调试信息
    show_debug_info

    case $strategy in
        "build-time")
            log_info "📦 尝试使用构建时下载..."
            if use_build_time_ytdlp; then
                return 0
            else
                log_warning "构建时下载失败，回退到 pip 安装"
                install_with_pip "$version"
            fi
            ;;

        "runtime")
            log_info "🔄 尝试运行时下载..."
            if use_runtime_ytdlp; then
                return 0
            else
                log_warning "运行时下载失败，回退到 pip 安装"
                install_with_pip "$version"
            fi
            ;;

        "hybrid")
            log_info "🔀 混合模式安装..."
            # 优先尝试构建时下载
            if use_build_time_ytdlp; then
                return 0
            else
                log_info "构建时下载不可用，尝试运行时下载..."
                if use_runtime_ytdlp; then
                    return 0
                else
                    log_warning "运行时下载也失败，回退到 pip 安装"
                    install_with_pip "$version"
                fi
            fi
            ;;

        "local")
            log_info "📁 尝试使用本地 yt-dlp 文件..."
            if use_local_ytdlp; then
                return 0
            else
                log_warning "本地文件不可用，回退到 pip 安装"
                install_with_pip "$version"
            fi
            ;;

        "pip"|"auto"|*)
            log_info "📦 直接使用 pip 安装..."
            install_with_pip "$version"
            ;;
    esac
}

# 验证安装结果
verify_installation() {
    log_info "🔍 验证 yt-dlp 安装..."

    if check_ytdlp; then
        log_success "yt-dlp 安装验证成功"
        return 0
    else
        log_error "yt-dlp 安装验证失败"
        show_debug_info
        return 1
    fi
}

# 如果直接运行此脚本
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    STRATEGY=${1:-"auto"}
    VERSION=${2:-"latest"}

    if install_ytdlp "$STRATEGY" "$VERSION"; then
        verify_installation
    else
        log_error "yt-dlp 安装失败"
        exit 1
    fi
fi
