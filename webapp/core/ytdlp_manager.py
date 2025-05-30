# -*- coding: utf-8 -*-
"""
yt-dlp 管理器 - 统一管理 yt-dlp 的初始化和使用
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

class YtdlpManager:
    """yt-dlp 管理器"""

    def __init__(self):
        self._initialized = False
        self._available = False

    def initialize(self):
        """初始化 yt-dlp"""
        if self._initialized:
            return self._available

        try:
            # 确保项目路径优先
            if '/app' not in sys.path:
                sys.path.insert(0, '/app')

            # 设置环境变量
            os.environ['YTDLP_NO_LAZY_EXTRACTORS'] = '1'

            logger.info("🔍 初始化 yt-dlp...")

            # 测试基础功能
            from yt_dlp import YoutubeDL
            ydl = YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True})

            # 测试基础 extractors
            from yt_dlp.extractor.youtube import YoutubeIE
            from yt_dlp.extractor.generic import GenericIE

            logger.info("✅ yt-dlp 初始化成功")
            self._available = True

        except Exception as e:
            logger.error(f"❌ yt-dlp 初始化失败: {e}")
            self._available = False

        finally:
            self._initialized = True

        return self._available

    def is_available(self):
        """检查 yt-dlp 是否可用"""
        if not self._initialized:
            return self.initialize()
        return self._available

    def create_downloader(self, options=None):
        """创建 yt-dlp 下载器实例"""
        if not self.is_available():
            raise RuntimeError("yt-dlp 不可用")

        from yt_dlp import YoutubeDL

        default_options = {
            'quiet': True,
            'no_warnings': True,
        }

        if options:
            default_options.update(options)

        return YoutubeDL(default_options)

    def get_enhanced_options(self):
        """获取增强的 yt-dlp 选项"""
        return {
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['webpage'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        }

# 全局实例
_ytdlp_manager = YtdlpManager()

def initialize_ytdlp():
    """初始化 yt-dlp（全局函数）"""
    return _ytdlp_manager.initialize()

def get_ytdlp_manager():
    """获取 yt-dlp 管理器实例"""
    return _ytdlp_manager

# 向后兼容的函数
def _initialize_ytdlp():
    """向后兼容的初始化函数"""
    return initialize_ytdlp()
