#!/bin/bash

# yt-dlp Web界面 Docker构建脚本
# 作者: AI Assistant
# 版本: 1.0.0

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置变量
IMAGE_NAME="yt-dlp-web"
IMAGE_TAG="latest"
CONTAINER_NAME="yt-dlp-web"

echo -e "${BLUE}🐳 yt-dlp Web界面 Docker构建脚本${NC}"
echo "=================================="

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装，请先安装Docker${NC}"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}⚠️  docker-compose未安装，将使用docker compose${NC}"
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo -e "${GREEN}✅ Docker环境检查通过${NC}"

# 停止并删除现有容器
echo -e "${YELLOW}🛑 停止现有容器...${NC}"
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# 构建Docker镜像
echo -e "${BLUE}🔨 构建Docker镜像...${NC}"
docker build -t $IMAGE_NAME:$IMAGE_TAG .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker镜像构建成功${NC}"
else
    echo -e "${RED}❌ Docker镜像构建失败${NC}"
    exit 1
fi

# 显示镜像信息
echo -e "${BLUE}📋 镜像信息:${NC}"
docker images | grep $IMAGE_NAME

# 询问是否启动容器
echo ""
read -p "是否立即启动容器? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🚀 启动容器...${NC}"
    $COMPOSE_CMD up -d
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 容器启动成功${NC}"
        echo -e "${BLUE}📱 访问地址: http://localhost:8080${NC}"
        echo -e "${BLUE}🔐 管理员登录: admin / admin123${NC}"
        echo -e "${BLUE}🛠️  管理控制台: http://localhost:8080/admin${NC}"
        
        # 显示容器状态
        echo ""
        echo -e "${BLUE}📊 容器状态:${NC}"
        docker ps | grep $CONTAINER_NAME
        
        # 显示日志
        echo ""
        echo -e "${BLUE}📝 容器日志 (最近10行):${NC}"
        docker logs --tail 10 $CONTAINER_NAME
    else
        echo -e "${RED}❌ 容器启动失败${NC}"
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎉 构建完成！${NC}"
echo ""
echo -e "${BLUE}📋 常用命令:${NC}"
echo "  启动服务: $COMPOSE_CMD up -d"
echo "  停止服务: $COMPOSE_CMD down"
echo "  查看日志: docker logs -f $CONTAINER_NAME"
echo "  进入容器: docker exec -it $CONTAINER_NAME bash"
echo "  重启服务: docker restart $CONTAINER_NAME"
echo ""
echo -e "${BLUE}📁 数据目录:${NC}"
echo "  下载文件: ./downloads"
echo "  配置文件: ./config"
echo ""
echo -e "${YELLOW}⚠️  生产环境部署提醒:${NC}"
echo "  1. 修改默认管理员密码"
echo "  2. 更改SECRET_KEY环境变量"
echo "  3. 配置反向代理(如nginx)"
echo "  4. 设置防火墙规则"
