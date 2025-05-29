# 使用官方Python 3.11镜像作为基础镜像
FROM python:3.11-slim

ARG BUILDTIME
ARG VERSION
ARG REVISION

LABEL org.opencontainers.image.title="YT-DLP 网页界面"
LABEL org.opencontainers.image.description="带下载管理的yt-dlp网页界面"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILDTIME}"
LABEL org.opencontainers.image.revision="${REVISION}"
LABEL org.opencontainers.image.source="https://github.com/zhumao520/yt-dlp-web" # 请确认是否仍是这个源
LABEL org.opencontainers.image.licenses="Unlicense"

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV VERSION=${VERSION}
ENV REVISION=${REVISION}
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app # /app 将包含你的 web 目录

RUN groupadd -r ytdlp && useradd -r -g ytdlp -u 1000 ytdlp

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

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装官方 yt-dlp 库
RUN pip install --no-cache-dir --upgrade yt-dlp && \
    echo "yt-dlp 库版本: $(python3 -c 'import yt_dlp.version; print(yt_dlp.version.__version__)' || echo '获取失败')"

# 复制你的 Web 应用代码 (即根目录下的 web 文件夹)
COPY web /app/web/
COPY start.sh /app/start.sh # 确保 start.sh 也被复制

RUN dos2unix /app/start.sh && \
    chmod +x /app/start.sh && \
    chown -R ytdlp:ytdlp /app # 整个 /app 目录及其内容

RUN mkdir -p /app/downloads /app/config /app/logs \
    && chown ytdlp:ytdlp /app/downloads /app/config /app/logs \
    && chmod 755 /app/downloads /app/config /app/logs

USER ytdlp
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1
CMD ["/app/start.sh"] # start.sh 内部已修改为使用 web.server