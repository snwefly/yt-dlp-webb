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
    rsync `# 添加 rsync 用于覆盖操作，或者确保 yt-dlp 库文件被正确链接` \
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
    echo "Listing contents of site-packages yt_dlp:" && ls -lA $YTDLP_SITE_PACKAGES_PATH && \
    python3 -c "import sys; print('Python 路径:', sys.path)" && \
    python3 -c "import yt_dlp; print('yt-dlp 版本:', yt_dlp.version.__version__); print('yt-dlp 位置:', yt_dlp.__file__)" && \
    echo "验证完成"

# 复制项目中的 yt_dlp 目录 (包含你的 web 应用和不完整的库文件) 和 start.sh
COPY yt_dlp /app/yt_dlp
COPY start.sh /app/

# 使用 site-packages 中的完整 yt-dlp 库组件替换 /app/yt_dlp 下的同名组件，但保留 /app/yt_dlp/web
RUN YTDLP_REAL_PATH=$(cat /tmp/ytdlp_path.txt) && \
    echo "Overlaying /app/yt_dlp with components from $YTDLP_REAL_PATH, preserving /app/yt_dlp/web" && \
    # 确定 utils 是文件还是目录
    UTILS_COMPONENT="utils.py" && \
    if [ -d "$YTDLP_REAL_PATH/utils" ]; then UTILS_COMPONENT="utils"; fi && \
    echo "Utils component determined as: $UTILS_COMPONENT" && \
    # 列出 yt-dlp 库的主要组件 (文件和目录)
    # 这个列表需要确保覆盖所有库相关部分，除了 'web'
    for component in \
        __init__.py \
        aes.py \
        compat \
        cookies.py \
        downloader \
        extractor \
        globals.py \
        minicurses.py \
        networking \
        options.py \
        outtmpl.py \
        plugins \
        postprocessor \
        update.py \
        "$UTILS_COMPONENT" \
        version.py \
        YoutubeDL.py \
        __main__.py \
    ; do \
        # 如果 /app/yt_dlp/$component 存在（来自项目复制），并且不是 web 目录，先移除它
        if [ "$component" != "web" ] && [ -e "/app/yt_dlp/$component" ]; then \
            echo "Removing project's copy of $component from /app/yt_dlp/"; \
            rm -rf "/app/yt_dlp/$component"; \
        fi; \
        # 从 site-packages 创建符号链接到 /app/yt_dlp/
        # 确保源文件或目录存在才创建链接
        if [ -e "$YTDLP_REAL_PATH/$component" ]; then \
            echo "Linking $YTDLP_REAL_PATH/$component to /app/yt_dlp/$component"; \
            ln -sf "$YTDLP_REAL_PATH/$component" "/app/yt_dlp/$component"; \
        else \
            echo "Warning: Component $component not found in $YTDLP_REAL_PATH ($YTDLP_REAL_PATH/$component), not linking."; \
        fi; \
    done && \
    # 验证 /app/yt_dlp/web 是否仍然存在且是真实目录 (不是符号链接)
    if [ -d /app/yt_dlp/web ] && [ ! -L /app/yt_dlp/web ]; then \
        echo "/app/yt_dlp/web is correctly a directory from project files."; \
    else \
        echo "Error: /app/yt_dlp/web is missing or is a symlink, which is incorrect! Attempting to restore from project copy if possible."; \
        # 尝试从原始复制的 yt_dlp (如果还保留了原始副本) 恢复 web 目录，但这不应该发生
        # 如果发生这种情况，说明上面的循环逻辑有误，可能意外删除了 web
        # 当前逻辑是明确跳过 web，所以这更像是一个完整性检查失败的信号
        if [ -d "/app_original_project_yt_dlp/web" ]; then \
             echo "Restoring web from a backup/original copy (this indicates a problem in script logic)" ; \
             cp -R /app_original_project_yt_dlp/web /app/yt_dlp/web ; \
        else exit 1; fi ; \
    fi && \
    rm /tmp/ytdlp_path.txt && \
    echo "Final contents of /app/yt_dlp (permissions and links):" && ls -lA /app/yt_dlp && \
    if [ -d /app/yt_dlp/web ]; then echo "Final contents of /app/yt_dlp/web:"; ls -lA /app/yt_dlp/web; fi && \
    # 额外检查 cookies.py 符号链接
    echo "Checking cookies.py link:" && ls -l /app/yt_dlp/cookies.py && readlink -f /app/yt_dlp/cookies.py

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
