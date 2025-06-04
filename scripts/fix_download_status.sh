#!/bin/bash
# 修复下载状态API问题的脚本

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

log_info "🔧 修复下载状态API问题..."

# 1. 测试下载管理器
log_info "🧪 测试下载管理器..."
python3 /app/scripts/test_download_manager.py

if [ $? -eq 0 ]; then
    log_success "下载管理器测试通过"
else
    log_error "下载管理器测试失败"
    exit 1
fi

# 2. 检查API路由注册
log_info "🔍 检查API路由注册..."
python3 << 'EOF'
import sys
sys.path.insert(0, '/app')

try:
    from webapp.app import create_app
    app = create_app()
    
    print("✅ 应用创建成功")
    
    # 查找下载状态路由
    download_status_routes = []
    with app.app_context():
        for rule in app.url_map.iter_rules():
            if 'download' in rule.rule and 'status' in rule.rule:
                download_status_routes.append(rule)
    
    print(f"🎯 找到 {len(download_status_routes)} 个下载状态路由:")
    for route in download_status_routes:
        methods = ','.join(route.methods - {'HEAD', 'OPTIONS'})
        print(f"  {route.rule} [{methods}] -> {route.endpoint}")
    
    if len(download_status_routes) > 0:
        print("✅ 下载状态路由注册正常")
    else:
        print("❌ 未找到下载状态路由")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ 检查失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -eq 0 ]; then
    log_success "API路由检查通过"
else
    log_error "API路由检查失败"
    exit 1
fi

# 3. 重启应用进程（如果在容器中）
if [ -f "/.dockerenv" ]; then
    log_info "🔄 在容器环境中，建议重启容器以应用更改"
    log_info "💡 运行命令: docker restart yt-dlp-web"
else
    log_info "🔄 重新加载应用配置..."
    # 在非容器环境中，可以尝试重新加载
    pkill -f "gunicorn.*webapp.app" || true
    sleep 2
fi

# 4. 验证修复
log_info "🧪 验证修复效果..."

# 等待服务启动
sleep 5

# 测试健康检查
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    log_success "应用健康检查通过"
else
    log_warning "应用健康检查失败，可能需要更多时间启动"
fi

# 5. 提供调试信息
log_info "📋 调试信息:"
echo "1. 查看应用日志: docker logs yt-dlp-web -f"
echo "2. 测试下载状态API:"
echo "   curl -H 'Authorization: Bearer YOUR_TOKEN' http://localhost:8090/api/download/test-id/status"
echo "3. 检查下载管理器状态:"
echo "   python3 /app/scripts/test_download_manager.py"

log_success "🎉 修复脚本执行完成！"
log_info "💡 如果问题仍然存在，请检查应用日志获取详细错误信息"
