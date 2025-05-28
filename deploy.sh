#!/bin/bash

# YT-DLP Web 部署脚本
# 使用方法: ./deploy.sh [版本标签]

set -e

# 默认配置
DEFAULT_TAG="latest"
REGISTRY="ghcr.io"
IMAGE_NAME="your-username/yt-dlp-web-deploy"
CONTAINER_NAME="yt-dlp-web"
PORT="8080"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    echo "YT-DLP Web 部署脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [选项] [版本标签]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -p, --port     指定端口 (默认: 8080)"
    echo "  -n, --name     指定容器名称 (默认: yt-dlp-web)"
    echo "  --pull         强制拉取最新镜像"
    echo "  --stop         停止并删除现有容器"
    echo "  --logs         显示容器日志"
    echo ""
    echo "示例:"
    echo "  $0                    # 部署最新版本"
    echo "  $0 v1.0.0            # 部署特定版本"
    echo "  $0 --port 9000       # 使用端口 9000"
    echo "  $0 --stop            # 停止服务"
    echo "  $0 --logs            # 查看日志"
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker 服务未运行，请启动 Docker 服务"
        exit 1
    fi
}

# 停止并删除现有容器
stop_container() {
    log_info "停止现有容器..."
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        docker stop $CONTAINER_NAME
        log_success "容器已停止"
    fi
    
    if docker ps -aq -f name=$CONTAINER_NAME | grep -q .; then
        docker rm $CONTAINER_NAME
        log_success "容器已删除"
    fi
}

# 拉取镜像
pull_image() {
    local tag=${1:-$DEFAULT_TAG}
    local image="$REGISTRY/$IMAGE_NAME:$tag"
    
    log_info "拉取镜像: $image"
    if docker pull $image; then
        log_success "镜像拉取成功"
    else
        log_error "镜像拉取失败"
        exit 1
    fi
}

# 启动容器
start_container() {
    local tag=${1:-$DEFAULT_TAG}
    local image="$REGISTRY/$IMAGE_NAME:$tag"
    
    log_info "启动容器..."
    
    # 创建下载目录
    mkdir -p ./downloads
    
    # 启动容器
    docker run -d \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $PORT:8080 \
        -v "$(pwd)/downloads:/app/downloads" \
        $image
    
    if [ $? -eq 0 ]; then
        log_success "容器启动成功"
        log_info "服务地址: http://localhost:$PORT"
    else
        log_error "容器启动失败"
        exit 1
    fi
}

# 显示日志
show_logs() {
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        log_info "显示容器日志 (Ctrl+C 退出):"
        docker logs -f $CONTAINER_NAME
    else
        log_error "容器未运行"
        exit 1
    fi
}

# 检查服务状态
check_status() {
    log_info "检查服务状态..."
    
    if docker ps -q -f name=$CONTAINER_NAME | grep -q .; then
        log_success "容器正在运行"
        
        # 等待服务启动
        log_info "等待服务启动..."
        for i in {1..30}; do
            if curl -f http://localhost:$PORT/ &> /dev/null; then
                log_success "服务已就绪: http://localhost:$PORT"
                return 0
            fi
            sleep 2
        done
        
        log_warning "服务可能未完全启动，请检查日志"
    else
        log_error "容器未运行"
        exit 1
    fi
}

# 主函数
main() {
    local tag=$DEFAULT_TAG
    local action="deploy"
    local force_pull=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -n|--name)
                CONTAINER_NAME="$2"
                shift 2
                ;;
            --pull)
                force_pull=true
                shift
                ;;
            --stop)
                action="stop"
                shift
                ;;
            --logs)
                action="logs"
                shift
                ;;
            -*)
                log_error "未知选项: $1"
                show_help
                exit 1
                ;;
            *)
                tag="$1"
                shift
                ;;
        esac
    done
    
    # 检查 Docker
    check_docker
    
    # 执行操作
    case $action in
        "stop")
            stop_container
            ;;
        "logs")
            show_logs
            ;;
        "deploy")
            if [ "$force_pull" = true ] || ! docker images -q "$REGISTRY/$IMAGE_NAME:$tag" | grep -q .; then
                pull_image $tag
            fi
            stop_container
            start_container $tag
            check_status
            ;;
    esac
}

# 运行主函数
main "$@"
