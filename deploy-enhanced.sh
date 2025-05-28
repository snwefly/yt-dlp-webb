#!/bin/bash

# YT-DLP Web 增强部署脚本
# 用于自动化部署和管理

set -e

# 颜色定义
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

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi
    
    log_success "依赖检查完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p downloads config logs
    chmod 755 downloads config logs
    
    log_success "目录创建完成"
}

# 检查环境变量文件
check_env_file() {
    if [ ! -f .env ]; then
        log_warning ".env 文件不存在，复制示例文件..."
        if [ -f .env.production ]; then
            cp .env.production .env
            log_warning "请编辑 .env 文件并设置正确的配置"
            return 1
        else
            log_error "找不到环境变量示例文件"
            exit 1
        fi
    fi
    return 0
}

# 构建镜像
build_image() {
    log_info "构建 Docker 镜像..."
    
    # 获取构建信息
    BUILDTIME=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
    VERSION=${1:-latest}
    REVISION=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    
    docker build \
        --build-arg BUILDTIME="$BUILDTIME" \
        --build-arg VERSION="$VERSION" \
        --build-arg REVISION="$REVISION" \
        -t yt-dlp-web:$VERSION \
        -t yt-dlp-web:latest \
        .
    
    log_success "镜像构建完成"
}

# 部署服务
deploy() {
    log_info "部署服务..."
    
    # 检查环境变量
    if ! check_env_file; then
        log_error "请先配置 .env 文件"
        exit 1
    fi
    
    # 停止现有服务
    docker-compose -f docker-compose.prod.yml down
    
    # 启动服务
    docker-compose -f docker-compose.prod.yml up -d
    
    log_success "服务部署完成"
}

# 更新服务
update() {
    log_info "更新服务..."
    
    # 拉取最新镜像
    docker-compose -f docker-compose.prod.yml pull
    
    # 重启服务
    docker-compose -f docker-compose.prod.yml up -d
    
    # 清理旧镜像
    docker image prune -f
    
    log_success "服务更新完成"
}

# 停止服务
stop() {
    log_info "停止服务..."
    docker-compose -f docker-compose.prod.yml down
    log_success "服务已停止"
}

# 查看日志
logs() {
    docker-compose -f docker-compose.prod.yml logs -f "${1:-yt-dlp-web-prod}"
}

# 查看状态
status() {
    log_info "服务状态:"
    docker-compose -f docker-compose.prod.yml ps
    
    log_info "容器健康状态:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# 备份数据
backup() {
    log_info "备份数据..."
    
    BACKUP_DIR="backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 备份下载文件
    if [ -d downloads ]; then
        tar -czf "$BACKUP_DIR/downloads.tar.gz" downloads/
        log_success "下载文件备份完成"
    fi
    
    # 备份配置文件
    if [ -d config ]; then
        tar -czf "$BACKUP_DIR/config.tar.gz" config/
        log_success "配置文件备份完成"
    fi
    
    # 备份环境变量
    if [ -f .env ]; then
        cp .env "$BACKUP_DIR/"
        log_success "环境变量备份完成"
    fi
    
    log_success "备份完成: $BACKUP_DIR"
}

# 清理
cleanup() {
    log_info "清理系统..."
    
    # 清理停止的容器
    docker container prune -f
    
    # 清理未使用的镜像
    docker image prune -f
    
    # 清理未使用的网络
    docker network prune -f
    
    # 清理未使用的卷
    docker volume prune -f
    
    log_success "清理完成"
}

# 显示帮助
show_help() {
    echo "YT-DLP Web 增强部署脚本"
    echo ""
    echo "用法: $0 [命令] [参数]"
    echo ""
    echo "命令:"
    echo "  init                初始化环境"
    echo "  build [version]     构建镜像"
    echo "  deploy              部署服务"
    echo "  update              更新服务"
    echo "  stop                停止服务"
    echo "  restart             重启服务"
    echo "  logs [service]      查看日志"
    echo "  status              查看状态"
    echo "  backup              备份数据"
    echo "  cleanup             清理系统"
    echo "  help                显示帮助"
    echo ""
}

# 主函数
main() {
    case "${1:-help}" in
        init)
            check_dependencies
            create_directories
            check_env_file
            ;;
        build)
            check_dependencies
            build_image "$2"
            ;;
        deploy)
            check_dependencies
            create_directories
            deploy
            ;;
        update)
            check_dependencies
            update
            ;;
        stop)
            stop
            ;;
        restart)
            stop
            deploy
            ;;
        logs)
            logs "$2"
            ;;
        status)
            status
            ;;
        backup)
            backup
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
