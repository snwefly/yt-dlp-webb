#!/bin/bash
# 验证容器启动后的用户权限

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}===========================================${NC}"
}

# 检查容器是否运行
check_container_running() {
    log_header "检查容器状态"
    
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "yt-dlp-web"; then
        log_success "容器 yt-dlp-web 正在运行"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "yt-dlp-web"
        return 0
    else
        log_error "容器 yt-dlp-web 未运行"
        log_info "尝试启动容器..."
        docker-compose up -d
        sleep 10
        
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "yt-dlp-web"; then
            log_success "容器启动成功"
            return 0
        else
            log_error "容器启动失败"
            return 1
        fi
    fi
}

# 检查容器内用户身份
check_container_user() {
    log_header "检查容器内用户身份"
    
    log_info "检查当前用户..."
    USER_INFO=$(docker exec yt-dlp-web whoami 2>/dev/null || echo "ERROR")
    
    if [ "$USER_INFO" = "root" ]; then
        log_success "容器以 root 用户运行"
    elif [ "$USER_INFO" = "ERROR" ]; then
        log_error "无法获取用户信息"
        return 1
    else
        log_warning "容器以非 root 用户运行: $USER_INFO"
    fi
    
    log_info "详细用户信息:"
    docker exec yt-dlp-web id 2>/dev/null || log_error "无法获取详细用户信息"
    
    log_info "进程用户信息:"
    docker exec yt-dlp-web ps aux | head -5 2>/dev/null || log_warning "无法获取进程信息"
}

# 检查目录权限
check_directory_permissions() {
    log_header "检查目录权限"
    
    DIRECTORIES=("/app/downloads" "/app/config" "/app/logs" "/app/yt-dlp-cache")
    
    for dir in "${DIRECTORIES[@]}"; do
        log_info "检查目录: $dir"
        
        # 检查目录是否存在
        if docker exec yt-dlp-web test -d "$dir" 2>/dev/null; then
            # 检查目录权限
            PERM_INFO=$(docker exec yt-dlp-web ls -la "$dir" 2>/dev/null | head -1)
            echo "  权限信息: $PERM_INFO"
            
            # 测试写入权限
            if docker exec yt-dlp-web touch "$dir/.write_test" 2>/dev/null; then
                docker exec yt-dlp-web rm "$dir/.write_test" 2>/dev/null
                log_success "  $dir - 可写"
            else
                log_error "  $dir - 不可写"
            fi
        else
            log_error "  $dir - 目录不存在"
        fi
    done
}

# 检查进程信息
check_process_info() {
    log_header "检查进程信息"
    
    log_info "检查 Python/Gunicorn 进程..."
    docker exec yt-dlp-web ps aux | grep -E "(python|gunicorn)" | grep -v grep || log_warning "未找到 Python/Gunicorn 进程"
    
    log_info "检查端口监听..."
    docker exec yt-dlp-web netstat -tlnp 2>/dev/null | grep ":8080" || log_warning "端口 8080 未监听"
}

# 检查应用健康状态
check_app_health() {
    log_header "检查应用健康状态"
    
    log_info "检查健康检查端点..."
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        log_success "健康检查端点响应正常"
        
        # 显示健康检查响应
        HEALTH_RESPONSE=$(curl -s http://localhost:8080/health)
        echo "健康检查响应: $HEALTH_RESPONSE"
    else
        log_error "健康检查端点无响应"
    fi
    
    log_info "检查主页..."
    if curl -s http://localhost:8080/ > /dev/null 2>&1; then
        log_success "主页响应正常"
    else
        log_error "主页无响应"
    fi
}

# 检查容器日志
check_container_logs() {
    log_header "检查容器启动日志"
    
    log_info "最近的容器日志:"
    docker logs yt-dlp-web --tail 20 2>/dev/null || log_error "无法获取容器日志"
}

# 生成报告
generate_report() {
    log_header "验证报告总结"
    
    # 重新检查关键信息
    USER_CHECK=$(docker exec yt-dlp-web whoami 2>/dev/null || echo "ERROR")
    HEALTH_CHECK=$(curl -s http://localhost:8080/health > /dev/null 2>&1 && echo "OK" || echo "FAIL")
    
    echo
    echo "📊 验证结果:"
    echo "----------------------------------------"
    
    if [ "$USER_CHECK" = "root" ]; then
        echo "✅ 用户身份: root (正确)"
    elif [ "$USER_CHECK" = "ERROR" ]; then
        echo "❌ 用户身份: 无法检测"
    else
        echo "⚠️  用户身份: $USER_CHECK (应该是 root)"
    fi
    
    if [ "$HEALTH_CHECK" = "OK" ]; then
        echo "✅ 应用健康: 正常"
    else
        echo "❌ 应用健康: 异常"
    fi
    
    # 检查写入权限
    WRITE_TEST=$(docker exec yt-dlp-web touch /app/downloads/.test 2>/dev/null && echo "OK" || echo "FAIL")
    if [ "$WRITE_TEST" = "OK" ]; then
        docker exec yt-dlp-web rm /app/downloads/.test 2>/dev/null
        echo "✅ 写入权限: 正常"
    else
        echo "❌ 写入权限: 异常"
    fi
    
    echo "----------------------------------------"
    
    if [ "$USER_CHECK" = "root" ] && [ "$HEALTH_CHECK" = "OK" ] && [ "$WRITE_TEST" = "OK" ]; then
        log_success "🎉 所有检查通过！容器正确以 root 用户运行"
        return 0
    else
        log_error "⚠️ 部分检查失败，请查看上述详细信息"
        return 1
    fi
}

# 主函数
main() {
    log_header "容器用户权限验证脚本"
    echo "此脚本将验证 yt-dlp-web 容器是否以 root 用户运行"
    echo
    
    # 执行检查
    check_container_running || exit 1
    check_container_user
    check_directory_permissions
    check_process_info
    check_app_health
    check_container_logs
    
    # 生成报告
    generate_report
}

# 执行主函数
main "$@"
