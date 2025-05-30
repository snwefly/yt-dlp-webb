#!/bin/bash
# 智能构建脚本 - 支持多种构建策略选择

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_header() { echo -e "${CYAN}🚀 $1${NC}"; }

# 默认配置
DEFAULT_STRATEGY="hybrid"
DEFAULT_YTDLP_SOURCE="github_release"
DEFAULT_YTDLP_VERSION="latest"
DEFAULT_IMAGE_TAG="yt-dlp-web"

# 显示帮助
show_help() {
    cat << EOF
智能构建脚本 - 支持多种 yt-dlp 构建策略

用法: $0 [选项]

构建策略:
  -s, --strategy STRATEGY    构建策略选择
                            build-time    : 构建时下载（稳定，体积大）
                            runtime       : 运行时下载（轻量，启动慢）
                            hybrid        : 混合模式（推荐）
                            local         : 纯本地模式（离线）
                            默认: $DEFAULT_STRATEGY

yt-dlp 配置:
  --source SOURCE           yt-dlp 源类型 (github_release|pypi|local)
                            默认: $DEFAULT_YTDLP_SOURCE
  
  --version VERSION         yt-dlp 版本
                            默认: $DEFAULT_YTDLP_VERSION

构建选项:
  -t, --tag TAG            Docker 镜像标签
                            默认: $DEFAULT_IMAGE_TAG
  
  -e, --env ENV            环境类型 (development|production|testing)
                            默认: 根据策略自动选择
  
  --no-cache               不使用 Docker 缓存
  --push                   构建后推送镜像
  --test                   构建后运行测试

其他选项:
  --interactive            交互式选择构建策略
  --list-strategies        列出所有可用策略
  --show-config           显示当前配置
  -h, --help              显示此帮助信息

示例:
  $0                                    # 使用默认混合模式
  $0 --interactive                     # 交互式选择
  $0 -s build-time --source pypi       # 构建时下载，使用 PyPI
  $0 -s runtime --version latest       # 运行时下载最新版
  $0 -s local --env development        # 本地模式，开发环境
  $0 --list-strategies                 # 查看所有策略

构建策略说明:
  build-time  : 在 Docker 构建阶段下载 yt-dlp，镜像自包含但体积大
  runtime     : 容器启动时下载 yt-dlp，镜像小但启动慢
  hybrid      : 构建时尝试下载，运行时检查补充，兼顾稳定性和灵活性
  local       : 仅使用本地 yt-dlp 文件，完全离线但需手动更新

EOF
}

# 列出所有策略
list_strategies() {
    log_header "可用的构建策略"
    echo
    echo "📦 build-time (构建时下载)"
    echo "   ✅ 镜像自包含，启动快，运行稳定"
    echo "   ❌ 镜像体积大，构建慢，需要网络"
    echo "   🎯 适用：生产环境、离线部署"
    echo
    echo "🚀 runtime (运行时下载)"
    echo "   ✅ 镜像小，构建快，版本灵活"
    echo "   ❌ 启动慢，需要网络，运行时不稳定"
    echo "   🎯 适用：开发环境、测试环境"
    echo
    echo "🔄 hybrid (混合模式) - 推荐"
    echo "   ✅ 兼顾稳定性和灵活性，自动回退"
    echo "   ❌ 逻辑复杂，调试困难"
    echo "   🎯 适用：CI/CD、多环境部署"
    echo
    echo "📁 local (纯本地模式)"
    echo "   ✅ 完全离线，构建快，版本可控"
    echo "   ❌ 需要手动更新，可能版本滞后"
    echo "   🎯 适用：内网环境、安全要求高"
}

# 交互式选择策略
interactive_select() {
    log_header "交互式构建策略选择"
    echo
    echo "请选择构建策略："
    echo "1) build-time  - 构建时下载（稳定，推荐生产环境）"
    echo "2) runtime     - 运行时下载（轻量，推荐开发环境）"
    echo "3) hybrid      - 混合模式（推荐，平衡选择）"
    echo "4) local       - 纯本地模式（离线环境）"
    echo
    read -p "请输入选择 (1-4) [默认: 3]: " choice
    
    case $choice in
        1) STRATEGY="build-time" ;;
        2) STRATEGY="runtime" ;;
        3|"") STRATEGY="hybrid" ;;
        4) STRATEGY="local" ;;
        *) 
            log_error "无效选择，使用默认策略: hybrid"
            STRATEGY="hybrid"
            ;;
    esac
    
    echo
    log_info "已选择策略: $STRATEGY"
    
    # 询问 yt-dlp 源
    echo
    echo "请选择 yt-dlp 源："
    echo "1) github_release - GitHub Release（推荐）"
    echo "2) pypi          - PyPI 官方包"
    echo "3) local         - 本地文件"
    echo
    read -p "请输入选择 (1-3) [默认: 1]: " source_choice
    
    case $source_choice in
        1|"") YTDLP_SOURCE="github_release" ;;
        2) YTDLP_SOURCE="pypi" ;;
        3) YTDLP_SOURCE="local" ;;
        *) 
            log_warning "无效选择，使用默认源: github_release"
            YTDLP_SOURCE="github_release"
            ;;
    esac
    
    # 询问版本
    echo
    read -p "请输入 yt-dlp 版本 [默认: latest]: " version_input
    YTDLP_VERSION=${version_input:-"latest"}
    
    echo
    log_success "配置完成："
    log_info "  策略: $STRATEGY"
    log_info "  源: $YTDLP_SOURCE"
    log_info "  版本: $YTDLP_VERSION"
}

# 显示当前配置
show_config() {
    log_header "当前构建配置"
    echo
    echo "🏗️  构建策略: $STRATEGY"
    echo "📦 yt-dlp 源: $YTDLP_SOURCE"
    echo "🏷️  yt-dlp 版本: $YTDLP_VERSION"
    echo "🏷️  镜像标签: $IMAGE_TAG"
    echo "🌍 环境类型: $ENVIRONMENT"
    echo "📁 Dockerfile: $DOCKERFILE"
    echo "📋 Requirements: $REQUIREMENTS_FILE"
    echo
}

# 解析命令行参数
parse_args() {
    STRATEGY="$DEFAULT_STRATEGY"
    YTDLP_SOURCE="$DEFAULT_YTDLP_SOURCE"
    YTDLP_VERSION="$DEFAULT_YTDLP_VERSION"
    IMAGE_TAG="$DEFAULT_IMAGE_TAG"
    ENVIRONMENT=""
    NO_CACHE=""
    PUSH_IMAGE=false
    RUN_TEST=false
    INTERACTIVE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--strategy)
                STRATEGY="$2"
                shift 2
                ;;
            --source)
                YTDLP_SOURCE="$2"
                shift 2
                ;;
            --version)
                YTDLP_VERSION="$2"
                shift 2
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -e|--env)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --no-cache)
                NO_CACHE="--no-cache"
                shift
                ;;
            --push)
                PUSH_IMAGE=true
                shift
                ;;
            --test)
                RUN_TEST=true
                shift
                ;;
            --interactive)
                INTERACTIVE=true
                shift
                ;;
            --list-strategies)
                list_strategies
                exit 0
                ;;
            --show-config)
                # 延迟到配置完成后显示
                SHOW_CONFIG=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 验证和设置配置
setup_config() {
    # 交互式选择
    if [ "$INTERACTIVE" = true ]; then
        interactive_select
    fi
    
    # 验证策略
    case $STRATEGY in
        build-time|runtime|hybrid|local)
            ;;
        *)
            log_error "不支持的构建策略: $STRATEGY"
            log_info "支持的策略: build-time, runtime, hybrid, local"
            exit 1
            ;;
    esac
    
    # 设置 Dockerfile
    case $STRATEGY in
        build-time)
            DOCKERFILE="Dockerfile.build-time"
            REQUIREMENTS_FILE="requirements.github.txt"
            ;;
        runtime)
            DOCKERFILE="Dockerfile.runtime"
            REQUIREMENTS_FILE="requirements.runtime.txt"
            ;;
        hybrid)
            DOCKERFILE="Dockerfile.hybrid"
            REQUIREMENTS_FILE="requirements.hybrid.txt"
            ;;
        local)
            DOCKERFILE="Dockerfile.local"
            REQUIREMENTS_FILE="requirements.local.txt"
            ;;
    esac
    
    # 设置环境（如果未指定）
    if [ -z "$ENVIRONMENT" ]; then
        case $STRATEGY in
            build-time) ENVIRONMENT="production" ;;
            runtime) ENVIRONMENT="development" ;;
            hybrid) ENVIRONMENT="production" ;;
            local) ENVIRONMENT="development" ;;
        esac
    fi
    
    # 更新镜像标签
    IMAGE_TAG="${IMAGE_TAG}:${STRATEGY}"
    
    # 验证必要文件
    if [ ! -f "$DOCKERFILE" ]; then
        log_error "Dockerfile 不存在: $DOCKERFILE"
        exit 1
    fi
    
    # 显示配置
    if [ "${SHOW_CONFIG:-false}" = true ]; then
        show_config
        exit 0
    fi
}

# 执行构建
build_image() {
    log_header "开始构建 Docker 镜像"
    
    # 显示配置
    show_config
    
    # 生成构建信息
    BUILDTIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    VERSION=${VERSION:-"1.0.0-$(date +%Y%m%d)"}
    REVISION=${REVISION:-$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")}
    
    # 构建参数
    local build_args=(
        --build-arg "BUILDTIME=$BUILDTIME"
        --build-arg "VERSION=$VERSION"
        --build-arg "REVISION=$REVISION"
        --build-arg "YTDLP_SOURCE=$YTDLP_SOURCE"
        --build-arg "YTDLP_VERSION=$YTDLP_VERSION"
        --build-arg "ENVIRONMENT=$ENVIRONMENT"
        -t "$IMAGE_TAG"
        -f "$DOCKERFILE"
    )
    
    if [ -n "$NO_CACHE" ]; then
        build_args+=("$NO_CACHE")
    fi
    
    # 添加标签
    build_args+=(
        --label "build.strategy=$STRATEGY"
        --label "ytdlp.source=$YTDLP_SOURCE"
        --label "ytdlp.version=$YTDLP_VERSION"
        --label "build.environment=$ENVIRONMENT"
    )
    
    log_info "执行构建命令:"
    echo "docker build ${build_args[*]} ."
    echo
    
    if docker build "${build_args[@]}" .; then
        log_success "Docker 镜像构建成功: $IMAGE_TAG"
        
        # 显示镜像信息
        echo
        log_info "镜像信息:"
        docker images "$IMAGE_TAG" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    else
        log_error "Docker 镜像构建失败"
        exit 1
    fi
}

# 运行测试
run_tests() {
    if [ "$RUN_TEST" = true ]; then
        log_header "运行构建测试"
        
        local container_name="ytdlp-test-$(date +%s)"
        
        log_info "启动测试容器..."
        if docker run --rm --name "$container_name" \
            -e ENVIRONMENT=testing \
            -p 8080:8080 \
            -d "$IMAGE_TAG"; then
            
            log_info "等待容器启动..."
            sleep 15
            
            # 健康检查
            if curl -f http://localhost:8080/health >/dev/null 2>&1; then
                log_success "健康检查通过"
            else
                log_error "健康检查失败"
                docker logs "$container_name"
                docker stop "$container_name"
                exit 1
            fi
            
            # 停止测试容器
            docker stop "$container_name"
            log_success "测试完成"
        else
            log_error "测试容器启动失败"
            exit 1
        fi
    fi
}

# 推送镜像
push_image() {
    if [ "$PUSH_IMAGE" = true ]; then
        log_header "推送镜像到注册表"
        
        if docker push "$IMAGE_TAG"; then
            log_success "镜像推送成功: $IMAGE_TAG"
        else
            log_error "镜像推送失败"
            exit 1
        fi
    fi
}

# 主函数
main() {
    log_header "智能构建脚本启动"
    
    parse_args "$@"
    setup_config
    build_image
    run_tests
    push_image
    
    echo
    log_success "🎉 构建完成！"
    log_info "镜像标签: $IMAGE_TAG"
    log_info "构建策略: $STRATEGY"
    log_info "yt-dlp 源: $YTDLP_SOURCE ($YTDLP_VERSION)"
    
    echo
    log_info "启动命令:"
    echo "docker run -d -p 8080:8080 --name yt-dlp-web $IMAGE_TAG"
    echo
    log_info "或使用 Docker Compose:"
    echo "IMAGE_TAG=$IMAGE_TAG docker-compose up -d"
}

# 执行主函数
main "$@"
