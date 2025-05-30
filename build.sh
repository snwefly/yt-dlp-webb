#!/bin/bash
# 快捷构建脚本

# 检查构建脚本是否存在
if [ -f "scripts/build-smart.sh" ]; then
    echo "🚀 调用智能构建脚本..."
    exec ./scripts/build-smart.sh "$@"
else
    echo "❌ 构建脚本不存在: scripts/build-smart.sh"
    exit 1
fi
