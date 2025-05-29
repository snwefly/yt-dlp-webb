# 使用官方Python 3.11镜像作为基础镜像
FROM python:3.11-slim

# 构建参数
ARG BUILDTIME
ARG VERSION
ARG REVISION

# 添加标签
LABEL org.opencontainers.image.title="YT-DLP 网页界面"
LABEL org.opencontainers.image.description="带下载管理的yt-dlp网页界面"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILDTIME}"
LABEL org.opencontainers.image.revision="${REVISION}"
LABEL org.opencontainers.image.source="https://github.com/zhumao520/yt-dlp-web"
LABEL org.opencontainers.image.licenses="Unlicense"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV VERSION=${VERSION}
ENV REVISION=${REVISION}
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app

# 创建非root用户（提前创建以提高安全性）
RUN groupadd -r ytdlp && useradd -r -g ytdlp -u 1000 ytdlp

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    wget \
    git \
    ca-certificates \
    dos2unix \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# 升级pip并安装Python依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制requirements文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装yt-dlp（最新版本）并验证安装
RUN pip install --no-cache-dir --upgrade yt-dlp && \
    python3 -c "import yt_dlp; print('yt-dlp version:', yt_dlp.version.__version__)"

# 复制Web应用代码和启动脚本
COPY yt_dlp /app/yt_dlp
COPY start.sh /app/

# 确保启动脚本使用正确的行尾符号并设置执行权限
RUN dos2unix /app/start.sh && \
    chmod +x /app/start.sh && \
    chown ytdlp:ytdlp /app/start.sh

# 创建必要的Python包结构
RUN mkdir -p /app/yt_dlp && \
    touch /app/yt_dlp/__init__.py

# 创建必要目录并设置权限
RUN mkdir -p /app/downloads /app/config /app/logs \
    && chown -R ytdlp:ytdlp /app \
    && chmod 755 /app/downloads /app/config /app/logs

# 切换到非root用户
USER ytdlp

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# 启动命令
CMD ["/app/start.sh"]
