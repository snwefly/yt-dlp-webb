"""
YouTube 配置管理 - 基于最新官方源代码
基于 yt_dlp/extractor/youtube/_base.py 的最新配置
"""

import logging

logger = logging.getLogger(__name__)

class YouTubeConfig:
    """基于最新官方源代码的 YouTube 配置管理器"""
    
    # 基于官方源代码的客户端配置（yt_dlp/extractor/youtube/_base.py）
    INNERTUBE_CLIENTS = {
        # 不需要 PO Token 的客户端（优先使用）
        'android_vr': {
            'client_name': 'ANDROID_VR',
            'client_version': '1.62.27',
            'context_client_name': 28,
            'require_js_player': False,
            'po_token_required': False,
            'supports_cookies': False,
            'user_agent': 'com.google.android.apps.youtube.vr.oculus/1.62.27 (Linux; U; Android 12L; eureka-user Build/SQ3A.220605.009.A1) gzip',
            'priority': 1,  # 最高优先级
        },
        'web_embedded': {
            'client_name': 'WEB_EMBEDDED_PLAYER',
            'client_version': '1.20250310.01.00',
            'context_client_name': 56,
            'require_js_player': True,
            'po_token_required': False,
            'supports_cookies': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'priority': 2,
        },
        'tv': {
            'client_name': 'TVHTML5',
            'client_version': '7.20250312.16.00',
            'context_client_name': 7,
            'require_js_player': True,
            'po_token_required': False,
            'supports_cookies': True,
            'user_agent': 'Mozilla/5.0 (ChromiumStylePlatform) Cobalt/Version',
            'priority': 3,
        },
        'mweb': {
            'client_name': 'MWEB',
            'client_version': '2.20250311.03.00',
            'context_client_name': 2,
            'require_js_player': True,
            'po_token_required': True,  # 需要 PO Token，但仍然可用
            'supports_cookies': True,
            'user_agent': 'Mozilla/5.0 (iPad; CPU OS 16_7_10 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1,gzip(gfe)',
            'priority': 4,
        },
    }
    
    @classmethod
    def get_optimal_client_list(cls):
        """获取按优先级排序的最优客户端列表"""
        # 按优先级排序，优先使用不需要 PO Token 的客户端
        clients = sorted(cls.INNERTUBE_CLIENTS.items(), key=lambda x: x[1]['priority'])
        return [client_name for client_name, _ in clients]
    
    @classmethod
    def get_extractor_args(cls):
        """获取基于最新源代码的 extractor_args 配置"""
        return {
            'youtube': {
                # 使用最优客户端列表，按优先级排序
                'player_client': cls.get_optimal_client_list(),
                'player_skip': ['webpage'],  # 跳过网页解析以避免检测
                # 让 yt-dlp 使用最新的默认行为
            }
        }
    
    @classmethod
    def get_http_headers(cls, client='tv'):
        """获取基于最新源代码的 HTTP 头部配置"""
        client_config = cls.INNERTUBE_CLIENTS.get(client, cls.INNERTUBE_CLIENTS['tv'])
        
        return {
            'User-Agent': client_config['user_agent'],
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
    
    @classmethod
    def get_cookie_browsers(cls):
        """获取支持 cookies 的浏览器列表（按推荐顺序）"""
        return [
            ('chrome', 'Chrome'),
            ('firefox', 'Firefox'),
            ('edge', 'Edge'),
            ('safari', 'Safari'),
        ]
    
    @classmethod
    def get_base_options(cls, skip_download=False):
        """获取基础 yt-dlp 选项配置"""
        options = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'extract_flat': False,
            'extractor_args': cls.get_extractor_args(),
            'http_headers': cls.get_http_headers(),
        }
        
        if skip_download:
            options['skip_download'] = True
            
        return options
    
    @classmethod
    def get_download_options(cls, download_dir, download_id=None):
        """获取下载专用的 yt-dlp 选项配置"""
        options = cls.get_base_options(skip_download=False)
        
        # 添加下载相关配置
        options.update({
            'outtmpl': f'{download_dir}/%(title)s.%(ext)s',
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
        })
        
        return options
    
    @classmethod
    def setup_cookies(cls, ydl_opts):
        """设置 cookies 配置"""
        cookies_set = False
        
        # 1. 尝试从浏览器获取 cookies
        for browser_name, display_name in cls.get_cookie_browsers():
            try:
                ydl_opts['cookiesfrombrowser'] = (browser_name,)
                logger.info(f"🍪 使用{display_name}浏览器cookies")
                cookies_set = True
                break
            except Exception as e:
                logger.debug(f"{display_name} cookies获取失败: {e}")
        
        # 2. 备用：使用 cookies 文件
        if not cookies_set:
            import os
            cookies_file = '/app/config/youtube_cookies.txt'
            if os.path.exists(cookies_file):
                ydl_opts['cookiefile'] = cookies_file
                logger.info(f"🍪 使用cookies文件: {cookies_file}")
                cookies_set = True
            else:
                logger.info("ℹ️ 无cookies可用，将优先使用android_vr客户端（不需要cookies和PO Token）")
        
        return cookies_set
    
    @classmethod
    def log_client_info(cls):
        """记录客户端配置信息"""
        logger.info("📱 YouTube客户端配置（基于最新官方源代码）:")
        for client_name, config in cls.INNERTUBE_CLIENTS.items():
            po_status = "❌需要PO Token" if config['po_token_required'] else "✅无需PO Token"
            cookie_status = "🍪支持Cookies" if config['supports_cookies'] else "🚫不支持Cookies"
            logger.info(f"  {config['priority']}. {client_name}: {po_status}, {cookie_status}")

# 全局配置实例
youtube_config = YouTubeConfig()
