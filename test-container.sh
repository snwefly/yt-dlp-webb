#!/bin/bash

# 本地容器测试脚本
# 用于在推送到 GitHub 之前本地测试容器构建和启动

set -e

IMAGE_NAME="yt-dlp-web-test"
CONTAINER_NAME="yt-dlp-web-test"

echo "🧪 开始本地容器测试..."

# 清理现有容器
echo "🧹 清理现有测试容器..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true
docker rmi $IMAGE_NAME 2>/dev/null || true

# 构建镜像
echo "🔨 构建测试镜像..."
docker build -t $IMAGE_NAME .

# 启动容器
echo "🚀 启动测试容器..."
docker run -d \
    --name $CONTAINER_NAME \
    -p 8080:8080 \
    -e ADMIN_USERNAME=testuser \
    -e ADMIN_PASSWORD=testpass123 \
    $IMAGE_NAME

# 等待启动
echo "⏳ 等待容器启动..."
sleep 30

# 检查容器状态
if ! docker ps | grep $CONTAINER_NAME; then
    echo "❌ 容器启动失败"
    docker logs $CONTAINER_NAME
    exit 1
fi

# 健康检查
echo "🔍 执行健康检查..."
for i in {1..10}; do
    if curl -f http://localhost:8080/ > /dev/null 2>&1; then
        echo "✅ 健康检查通过"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "❌ 健康检查失败"
        docker logs $CONTAINER_NAME
        exit 1
    fi
    echo "等待服务启动... ($i/10)"
    sleep 5
done

echo "🎉 测试成功！容器正常运行"
echo "📱 访问地址: http://localhost:8080"
echo "🔐 测试账号: testuser / testpass123"

# 清理
read -p "是否清理测试容器? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    docker rmi $IMAGE_NAME
    echo "✅ 清理完成"
fi
