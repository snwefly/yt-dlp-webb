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
# 将关于 rsync 的注释移到了指令块外部或内部安全的位置
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    wget \
    git \
    ca-certificates \
    dos2unix \
    rsync `# 添加 rsync 用于更方便地覆盖目录内容` \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# 升级pip并安装Python依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制requirements文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装yt-dlp（最新版本）到 site-packages 并获取其真实路径
RUN echo "开始安装 yt-dlp..." && \
    pip install --no-cache-dir --upgrade yt-dlp && \
    echo "yt-dlp 安装完成，验证安装..." && \
    YTDLP_SITE_PACKAGES_PATH=$(python3 -c "import yt_dlp; import os; print(os.path.dirname(yt_dlp.__file__))") && \
    echo "yt-dlp site-packages path is: $YTDLP_SITE_PACKAGES_PATH" && \
    echo "$YTDLP_SITE_PACKAGES_PATH" > /tmp/ytdlp_path.txt && \
    python3 -c "import sys; print('Python 路径:', sys.path)" && \
    python3 -c "import yt_dlp; print('yt-dlp 版本:', yt_dlp.version.__version__); print('yt-dlp 位置:', yt_dlp.__file__)" && \
    echo "验证完成"

# 复制项目中的 yt_dlp 目录 (包含你的 web 应用和不完整的库文件) 和 start.sh
COPY yt_dlp /app/yt_dlp_project_files
COPY start.sh /app/

# 准备 /app/yt_dlp 目录：
RUN YTDLP_REAL_PATH=$(cat /tmp/ytdlp_path.txt) && \
    echo "Using yt-dlp from $YTDLP_REAL_PATH for preparing /app/yt_dlp" && \
    mkdir -p /app/yt_dlp && \
    # 首先，将你的 web 应用代码安全地移动到目标位置
    if [ -d /app/yt_dlp_project_files/web ]; then mv /app/yt_dlp_project_files/web /app/yt_dlp/web; fi && \
    # 保护 /app/yt_dlp/web (如果存在)，先移走
    if [ -d /app/yt_dlp/web ]; then mv /app/yt_dlp/web /tmp/webapp_backup; fi && \
    # 使用 rsync 从 site-packages/yt_dlp 同步到 /app/yt_dlp
    # 这会复制所有官方库文件和目录，并删除 /app/yt_dlp 中不属于官方库的冲突文件（除了我们备份的 web）
    rsync -a --delete "$YTDLP_REAL_PATH/" "/app/yt_dlp/" && \
    # 将备份的 web 应用移回
    if [ -d /tmp/webapp_backup ]; then mv /tmp/webapp_backup /app/yt_dlp/web; fi && \
    # 清理
    rm -rf /app/yt_dlp_project_files && \
    rm /tmp/ytdlp_path.txt && \
    echo "Contents of /app/yt_dlp after sync and webapp move:" && \
    ls -lA /app/yt_dlp && \
    if [ -d /app/yt_dlp/web ]; then echo "Contents of /app/yt_dlp/web:"; ls -lA /app/yt_dlp/web; fi

# 确保启动脚本使用正确的行尾符号并设置执行权限
RUN dos2unix /app/start.sh && \
    chmod +x /app/start.sh && \
    chown -R ytdlp:ytdlp /app

# 创建其他必要目录并设置权限
RUN mkdir -p /app/downloads /app/config /app/logs \
    && chown ytdlp:ytdlp /app/downloads /app/config /app/logs \
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
