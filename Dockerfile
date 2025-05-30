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
ENV YTDLP_NO_LAZY_EXTRACTORS=1

# 创建非root用户（提前创建以提高安全性）
RUN groupadd -r ytdlp && useradd -r -g ytdlp -u 1000 ytdlp

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    dos2unix \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# 升级pip并安装Python依赖
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 复制requirements文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 验证系统 yt-dlp 安装（但不依赖它）
RUN echo "=== 验证系统依赖安装 ===" && \
    python3 -c "import flask; print('✅ Flask 安装成功')" && \
    python3 -c "import requests; print('✅ Requests 安装成功')" && \
    echo "✅ 基础依赖验证完成"

# 复制项目文件
COPY webapp /app/webapp
COPY yt_dlp /app/yt_dlp
COPY start.sh /app/start.sh

# 验证项目文件完整性
RUN echo "=== 验证项目文件 ===" && \
    ls -la /app/yt_dlp/ | head -10 && \
    echo "yt_dlp 文件数量: $(find /app/yt_dlp -name '*.py' | wc -l)" && \
    ls -la /app/yt_dlp/extractor/ | head -10 && \
    echo "extractor 文件数量: $(find /app/yt_dlp/extractor -name '*.py' | wc -l)" && \
    echo "✅ 项目文件验证完成"

# 验证项目结构
RUN echo "验证项目结构..." && \
    ls -la /app/ && \
    ls -la /app/webapp/ && \
    ls -la /app/yt_dlp/ && \
    echo "项目结构验证完成"

# 确保启动脚本使用正确的行尾符号并设置执行权限
RUN dos2unix /app/start.sh && \
    chmod +x /app/start.sh && \
    echo "start.sh 权限设置完成" && \
    ls -la /app/start.sh

# 创建必要目录并设置正确权限
RUN mkdir -p /app/downloads /app/config /app/logs \
    && chown -R ytdlp:ytdlp /app \
    && chmod 755 /app/downloads /app/config /app/logs \
    && echo "=== 验证目录权限 ===" \
    && ls -la /app/ \
    && echo "downloads 目录详情:" \
    && ls -ld /app/downloads \
    && echo "权限验证完成"

# 测试项目模块导入（非阻塞式）
RUN echo "=== 测试项目模块导入 ===" && \
    cd /app && \
    PYTHONPATH=/app YTDLP_NO_LAZY_EXTRACTORS=1 python3 -c "\
import sys; \
import os; \
sys.path.insert(0, '/app'); \
print('环境变量 YTDLP_NO_LAZY_EXTRACTORS:', os.environ.get('YTDLP_NO_LAZY_EXTRACTORS', '未设置')); \
print('Python路径[0]:', sys.path[0]); \
try: \
    import yt_dlp; \
    print('yt_dlp模块位置:', yt_dlp.__file__); \
    if '/app/yt_dlp' in yt_dlp.__file__: \
        print('✅ 使用项目本地yt_dlp模块'); \
    else: \
        print('⚠️ 使用系统yt_dlp模块'); \
    from yt_dlp import YoutubeDL; \
    ydl = YoutubeDL({'quiet': True, 'no_warnings': True}); \
    print('✅ YoutubeDL实例创建成功'); \
except Exception as e: \
    print('⚠️ 模块导入警告:', str(e)); \
    print('⚠️ 继续构建，运行时将重新尝试'); \
print('✅ 构建时模块测试完成'); \
" || echo "⚠️ 模块测试完成（非阻塞）"

# 切换到非root用户
USER ytdlp

# 验证用户权限和目录访问
RUN echo "=== 验证用户权限 ===" && \
    whoami && \
    id && \
    echo "当前用户目录权限:" && \
    ls -la /app/ && \
    echo "downloads 目录权限:" && \
    ls -ld /app/downloads && \
    echo "测试写入权限:" && \
    touch /app/downloads/test_file && \
    echo "测试文件创建成功" && \
    rm /app/downloads/test_file && \
    echo "✅ 下载目录权限验证成功"

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# 启动命令
CMD ["/app/start.sh"]
