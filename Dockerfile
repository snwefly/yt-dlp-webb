# 主 Dockerfile - 提示使用具体的构建策略
# 请使用 dockerfiles/ 目录中的具体 Dockerfile

FROM alpine:latest

RUN echo "请使用具体的构建策略 Dockerfile:" && \
    echo "" && \
    echo "🔄 混合模式（推荐）:" && \
    echo "  docker build -f dockerfiles/Dockerfile.hybrid ." && \
    echo "" && \
    echo "📦 构建时下载:" && \
    echo "  docker build -f dockerfiles/Dockerfile.build-time ." && \
    echo "" && \
    echo "🚀 运行时下载:" && \
    echo "  docker build -f dockerfiles/Dockerfile.runtime ." && \
    echo "" && \
    echo "📁 本地模式:" && \
    echo "  docker build -f dockerfiles/Dockerfile.local-ytdlp ." && \
    echo "" && \
    echo "或使用构建脚本:" && \
    echo "  ./scripts/build-smart.sh --interactive" && \
    exit 1
