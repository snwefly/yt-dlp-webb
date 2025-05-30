# GitHub 网络版 yt-dlp Web - 高级配置指南

## 🔧 高级配置

### 多环境部署

#### 1. 开发环境配置

```bash
# .env.development
ENVIRONMENT=development
YTDLP_SOURCE=local
DEBUG=true
LOG_LEVEL=DEBUG
WEB_PORT=8080

# 启动开发环境
ENVIRONMENT=development ./build-github.sh --source local --no-cache
```

#### 2. 生产环境配置

```bash
# .env.production
ENVIRONMENT=production
YTDLP_SOURCE=github_release
YTDLP_VERSION=2024.12.13  # 锁定版本
DEBUG=false
LOG_LEVEL=INFO
WEB_PORT=80

# 启动生产环境
ENVIRONMENT=production ./build-github.sh --source github_release --push
```

#### 3. 测试环境配置

```bash
# .env.testing
ENVIRONMENT=testing
YTDLP_SOURCE=pypi
YTDLP_VERSION=">=2024.12.13"
DEBUG=false
LOG_LEVEL=WARNING
WEB_PORT=8080

# 启动测试环境
ENVIRONMENT=testing ./build-github.sh --source pypi --test
```

### 自定义 yt-dlp 源

#### 1. 添加自定义 GitHub 仓库

编辑 `config/ytdlp-source.yml`:

```yaml
ytdlp_source:
  # 自定义 GitHub 源
  custom_github:
    enabled: true
    repository: "your-username/yt-dlp-fork"
    branch: "custom-features"
    version: "latest"
  
  # 更新优先级
build_strategy:
  priority:
    - "custom_github"
    - "github_release"
    - "pypi"
    - "local"
```

#### 2. 使用私有仓库

```yaml
ytdlp_source:
  private_github:
    enabled: true
    repository: "private-org/yt-dlp-enterprise"
    token: "${GITHUB_TOKEN}"  # 环境变量
    version: "v2024.12.13-enterprise"
```

#### 3. 本地开发版本

```yaml
ytdlp_source:
  local_dev:
    enabled: true
    path: "/path/to/your/yt-dlp-dev"
    requirements: "/path/to/custom-requirements.txt"
```

### 性能优化

#### 1. 并发下载配置

```python
# webapp/core/ytdlp_manager.py
def get_enhanced_options(self):
    return {
        'concurrent_fragment_downloads': 4,
        'max_downloads': 3,
        'socket_timeout': 30,
        'retries': 3,
    }
```

#### 2. 缓存配置

```yaml
# config/ytdlp-source.yml
build_strategy:
  cache:
    enabled: true
    directory: "/app/cache/ytdlp"
    ttl_hours: 168  # 7天
    max_size_mb: 1024  # 1GB
```

#### 3. 内存优化

```yaml
# docker-compose.github.yml
services:
  yt-dlp-web-github:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
```

### 安全配置

#### 1. HTTPS 配置

```yaml
# docker-compose.github.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - yt-dlp-web-github

  yt-dlp-web-github:
    expose:
      - "8080"
    # 不直接暴露端口
```

#### 2. 反向代理配置

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    location / {
        proxy_pass http://yt-dlp-web-github:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 3. 防火墙配置

```bash
# UFW 配置
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8080/tcp   # 禁止直接访问应用端口
sudo ufw enable
```

### 监控和日志

#### 1. Prometheus 监控

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'yt-dlp-web'
    static_configs:
      - targets: ['yt-dlp-web-github:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

#### 2. Grafana 仪表板

```yaml
# docker-compose.monitoring.yml
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
```

#### 3. 日志聚合

```yaml
# docker-compose.logging.yml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.15.0
    environment:
      - discovery.type=single-node
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:7.15.0
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline

  kibana:
    image: docker.elastic.co/kibana/kibana:7.15.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

## 🔄 维护更新

### 自动更新

#### 1. 定时更新脚本

```bash
#!/bin/bash
# auto-update.sh

# 检查新版本
LATEST_VERSION=$(curl -s https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest | jq -r .tag_name)
CURRENT_VERSION=$(docker exec yt-dlp-web-github python -c "import yt_dlp; print(yt_dlp.__version__)" 2>/dev/null || echo "unknown")

if [ "$LATEST_VERSION" != "$CURRENT_VERSION" ]; then
    echo "发现新版本: $LATEST_VERSION (当前: $CURRENT_VERSION)"
    
    # 备份当前版本
    docker commit yt-dlp-web-github yt-dlp-web:backup-$(date +%Y%m%d)
    
    # 更新
    YTDLP_VERSION=$LATEST_VERSION ./build-github.sh --no-cache
    
    # 重启服务
    docker-compose -f docker-compose.github.yml up -d
    
    echo "更新完成"
else
    echo "已是最新版本: $CURRENT_VERSION"
fi
```

#### 2. Cron 定时任务

```bash
# 添加到 crontab
0 2 * * 0 /path/to/auto-update.sh >> /var/log/yt-dlp-update.log 2>&1
```

### 备份恢复

#### 1. 数据备份

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/yt-dlp/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# 备份下载文件
docker run --rm \
  -v yt-dlp-web-deploy_downloads:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/downloads.tar.gz -C /data .

# 备份配置
docker run --rm \
  -v yt-dlp-web-deploy_config:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/config.tar.gz -C /data .

# 备份数据库（如果有）
docker exec yt-dlp-web-github pg_dump -U postgres app > "$BACKUP_DIR/database.sql"

echo "备份完成: $BACKUP_DIR"
```

#### 2. 数据恢复

```bash
#!/bin/bash
# restore.sh

BACKUP_DIR="$1"
if [ -z "$BACKUP_DIR" ]; then
    echo "用法: $0 <备份目录>"
    exit 1
fi

# 停止服务
docker-compose -f docker-compose.github.yml down

# 恢复下载文件
docker run --rm \
  -v yt-dlp-web-deploy_downloads:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar xzf /backup/downloads.tar.gz -C /data

# 恢复配置
docker run --rm \
  -v yt-dlp-web-deploy_config:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar xzf /backup/config.tar.gz -C /data

# 启动服务
docker-compose -f docker-compose.github.yml up -d

echo "恢复完成"
```

### 健康检查

#### 1. 应用健康检查

```python
# webapp/routes/health.py
from flask import Blueprint, jsonify
import psutil
import os

health_bp = Blueprint('health', __name__)

@health_bp.route('/health')
def health_check():
    try:
        # 检查 yt-dlp
        import yt_dlp
        ytdlp_status = "ok"
        ytdlp_version = yt_dlp.__version__
    except:
        ytdlp_status = "error"
        ytdlp_version = "unknown"
    
    # 检查系统资源
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/app/downloads')
    
    return jsonify({
        'status': 'healthy' if ytdlp_status == 'ok' else 'unhealthy',
        'yt_dlp': {
            'status': ytdlp_status,
            'version': ytdlp_version
        },
        'system': {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': (disk.used / disk.total) * 100
        }
    })
```

#### 2. 外部监控

```bash
#!/bin/bash
# monitor.sh

URL="http://localhost:8080/health"
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"

RESPONSE=$(curl -s -w "%{http_code}" "$URL")
HTTP_CODE="${RESPONSE: -3}"
BODY="${RESPONSE%???}"

if [ "$HTTP_CODE" != "200" ]; then
    MESSAGE="🚨 yt-dlp Web 服务异常: HTTP $HTTP_CODE"
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"$MESSAGE\"}" \
        "$WEBHOOK_URL"
fi
```

### 性能调优

#### 1. 数据库优化

```sql
-- PostgreSQL 优化
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
SELECT pg_reload_conf();
```

#### 2. 应用优化

```python
# webapp/config.py
import os

class ProductionConfig:
    # 数据库连接池
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    # Redis 缓存
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    
    # 会话配置
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'ytdlp:'
```

#### 3. 系统优化

```bash
# /etc/sysctl.conf
# 网络优化
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# 文件描述符
fs.file-max = 65536

# 应用后重启
sudo sysctl -p
```
