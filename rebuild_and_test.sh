#!/bin/bash
# 重新构建和测试修复效果

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

log_info "🚀 开始重新构建和测试..."

# 检查必要文件
log_info "🔍 检查必要文件..."
if [ ! -f ".env" ]; then
    log_error ".env 文件不存在"
    exit 1
fi

if [ ! -f "docker-compose.yml" ]; then
    log_error "docker-compose.yml 文件不存在"
    exit 1
fi

log_success "必要文件检查通过"

# 停止现有容器
log_info "🛑 停止现有容器..."
docker-compose down --remove-orphans || true

# 清理旧镜像
log_info "🧹 清理旧镜像..."
docker system prune -f || true

# 重新构建
log_info "🔨 重新构建镜像..."
docker-compose build --no-cache

if [ $? -eq 0 ]; then
    log_success "镜像构建成功"
else
    log_error "镜像构建失败"
    exit 1
fi

# 启动容器
log_info "🚀 启动容器..."
docker-compose up -d

if [ $? -eq 0 ]; then
    log_success "容器启动成功"
else
    log_error "容器启动失败"
    exit 1
fi

# 等待容器启动
log_info "⏳ 等待容器完全启动..."
sleep 30

# 检查容器状态
log_info "🔍 检查容器状态..."
if docker-compose ps | grep -q "Up"; then
    log_success "容器运行正常"
else
    log_error "容器未正常运行"
    docker-compose logs
    exit 1
fi

# 运行测试
log_info "🧪 运行测试..."
docker-compose exec yt-dlp-web python /app/test_fixes.py

if [ $? -eq 0 ]; then
    log_success "测试通过"
else
    log_warning "测试失败，查看日志..."
    docker-compose logs --tail=50
fi

# 检查健康状态
log_info "🏥 检查健康状态..."
sleep 10
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    log_success "健康检查通过"
else
    log_warning "健康检查失败"
fi

# 显示日志
log_info "📋 显示最近日志..."
docker-compose logs --tail=20

log_success "🎉 重新构建和测试完成！"
