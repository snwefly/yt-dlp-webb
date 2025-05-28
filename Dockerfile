# 使用官方Python 3.11镜像作为基础镜像
FROM python:3.11-slim

# 构建参数
ARG BUILDTIME
ARG VERSION
ARG REVISION

# 添加标签
LABEL org.opencontainers.image.title="YT-DLP Web Interface"
LABEL org.opencontainers.image.description="Web interface for yt-dlp with download management"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILDTIME}"
LABEL org.opencontainers.image.revision="${REVISION}"
LABEL org.opencontainers.image.source="https://github.com/your-username/yt-dlp-web-deploy"
LABEL org.opencontainers.image.licenses="Unlicense"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV VERSION=${VERSION}
ENV REVISION=${REVISION}
ENV DEBIAN_FRONTEND=noninteractive

# 创建非root用户（提前创建以提高安全性）
RUN groupadd -r ytdlp && useradd -r -g ytdlp -u 1000 ytdlp

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    wget \
    git \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# 升级pip并安装Python依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制requirements文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装yt-dlp（最新版本）
RUN pip install --no-cache-dir --upgrade yt-dlp

# 复制Web应用代码
COPY yt_dlp/web /app/yt_dlp/web
COPY start.sh /app/

# 创建yt_dlp包的__init__.py
RUN mkdir -p /app/yt_dlp && echo "# yt-dlp web interface" > /app/yt_dlp/__init__.py

# 创建必要目录并设置权限
RUN mkdir -p /app/downloads /app/config /app/logs \
    && chown -R ytdlp:ytdlp /app \
    && chmod +x /app/start.sh \
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
