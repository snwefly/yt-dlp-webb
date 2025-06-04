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
            # 设置环境变量
            os.environ['YTDLP_NO_LAZY_EXTRACTORS'] = '1'
            # 设置更宽松的导入策略
            os.environ['YTDLP_IGNORE_EXTRACTOR_ERRORS'] = '1'

            logger.info("🔍 初始化 yt-dlp...")

            # 先运行 extractor 修复
            self._run_extractor_fix()

            # 只测试基础导入，不创建实例
            from yt_dlp import YoutubeDL

            # 测试基础 extractors 导入
            try:
                from yt_dlp.extractor.youtube import YoutubeIE
                from yt_dlp.extractor.generic import GenericIE
                logger.info("✅ 基础 extractors 导入成功")
            except ImportError as e:
                logger.warning(f"⚠️ 某些 extractors 导入失败: {e}")
                # 继续运行，因为核心功能仍然可用

            # 测试创建最小实例
            try:
                test_ydl = YoutubeDL({
                    'quiet': True,
                    'no_warnings': True,
                    'ignoreerrors': True,
                    'extract_flat': True,
                })
                logger.info("✅ yt-dlp 实例测试成功")

                # 测试实例是否能正常工作
                test_ydl.close()

            except Exception as e:
                logger.warning(f"⚠️ yt-dlp 实例测试失败: {e}")
                # 仍然标记为可用，但使用更保守的配置

            logger.info("✅ yt-dlp 初始化成功")
            self._available = True

        except Exception as e:
            logger.error(f"❌ yt-dlp 初始化失败: {e}")
            self._available = False

        finally:
            self._initialized = True

        return self._available

    def _preload_common_extractors(self):
        """预加载常见的缺失 extractor"""
        # 移除非标准提取器，只保留确实存在但可能有导入问题的标准提取器
        common_missing = [
            # 注释掉非标准提取器，避免与 yt-dlp 内部机制冲突
            # 'screencastify', 'screen9', 'screencast', 'screencastomatic',
            # 'screenrec', 'scribd', 'scrolller', 'scte', 'sendtonews'
        ]

        for extractor_name in common_missing:
            try:
                # 尝试导入，如果失败则动态创建
                module_name = f'yt_dlp.extractor.{extractor_name}'
                __import__(module_name)
            except ImportError:
                logger.debug(f"⚠️ 跳过非标准 extractor: {extractor_name}")
                # 不再尝试修复非标准提取器
                # self._fix_missing_extractor(extractor_name)

    def _run_extractor_fix(self):
        """运行 extractor 修复"""
        try:
            # 首先预加载常见的缺失 extractor（现在是空列表，不做任何操作）
            self._preload_common_extractors()

            # 不再运行可能有问题的修复脚本，避免与 yt-dlp 内部机制冲突
            logger.debug("ℹ️ 跳过 extractor 修复脚本，使用 yt-dlp 原生机制")

        except Exception as e:
            logger.debug(f"⚠️ extractor 修复过程出错: {e}")

    def is_available(self):
        """检查 yt-dlp 是否可用"""
        if not self._initialized:
            return self.initialize()
        return self._available

    def _fix_missing_extractor(self, extractor_name):
        """动态修复缺失的 extractor"""
        try:
            import types
            import sys
            from yt_dlp.extractor.common import InfoExtractor
            from yt_dlp.utils import ExtractorError

            # 生成类名
            class_name = ''.join(word.capitalize() for word in extractor_name.split('_')) + 'IE'

            # 动态创建类
            def _real_extract(self, url):
                raise ExtractorError(
                    f'{self.IE_NAME} extractor is not implemented. '
                    f'This is a placeholder to prevent import errors.',
                    expected=True
                )

            # 创建类属性
            attrs = {
                '_VALID_URL': r'https?://(?:www\.)?example\.com/.*',
                '_TESTS': [],
                'IE_NAME': extractor_name,
                'IE_DESC': f'Virtual {extractor_name} extractor (placeholder)',
                '_real_extract': _real_extract,
            }

            # 动态创建类
            ExtractorClass = type(class_name, (InfoExtractor,), attrs)

            # 创建模块
            module = types.ModuleType(f'yt_dlp.extractor.{extractor_name}')
            setattr(module, class_name, ExtractorClass)
            setattr(module, '__all__', [class_name])

            # 注册到 sys.modules
            sys.modules[f'yt_dlp.extractor.{extractor_name}'] = module

            logger.debug(f"✅ 动态修复 extractor: {extractor_name}")
            return True

        except Exception as e:
            logger.debug(f"⚠️ 动态修复 extractor 失败: {e}")
            return False

    def extract_info_with_custom(self, url, options=None):
        """使用自定义提取器或yt-dlp提取视频信息"""
        try:
            # 首先尝试自定义提取器
            from .custom_extractors import get_custom_extractor
            custom_extractor = get_custom_extractor(url)

            if custom_extractor:
                logger.info(f"🎯 使用自定义提取器: {custom_extractor.IE_NAME}")
                return custom_extractor.extract_info(url)

            # 如果没有自定义提取器，使用yt-dlp
            logger.info("🔄 使用yt-dlp标准提取器")

            # 为特定网站添加impersonation支持
            enhanced_options = self._enhance_options_for_site(url, options or {})

            with self.create_downloader(enhanced_options) as ydl:
                return ydl.extract_info(url, download=False)

        except Exception as e:
            logger.error(f"❌ 视频信息提取失败: {e}")
            raise

    def _enhance_options_for_site(self, url, options):
        """为特定网站增强选项"""
        enhanced_options = options.copy()

        # 检查是否需要特殊处理的网站
        if any(domain in url.lower() for domain in ['missav.ai', 'missav.com']):
            logger.info("🔧 为Missav网站添加特殊配置")

            # 添加impersonation支持
            if 'extractor_args' not in enhanced_options:
                enhanced_options['extractor_args'] = {}

            if 'generic' not in enhanced_options['extractor_args']:
                enhanced_options['extractor_args']['generic'] = {}

            # 使用Chrome浏览器模拟
            enhanced_options['extractor_args']['generic']['impersonate'] = 'chrome'

            # 添加更多反检测选项
            enhanced_options.update({
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'sec-ch-ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                },
                'sleep_interval': 1,  # 请求间隔
                'max_sleep_interval': 3,  # 最大请求间隔
            })

        return enhanced_options

    def create_downloader(self, options=None):
        """创建 yt-dlp 下载器实例"""
        if not self.is_available():
            raise RuntimeError("yt-dlp 不可用")

        try:
            from yt_dlp import YoutubeDL

            default_options = {
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,  # 忽略单个 extractor 错误
                'no_check_certificate': True,  # 忽略证书错误
                'extract_flat': False,  # 完整提取
                'ignore_no_formats_error': True,  # 忽略格式错误
                'ignore_config': True,  # 忽略配置文件
            }

            if options:
                default_options.update(options)

            # 尝试创建下载器，如果失败则使用最小配置
            try:
                downloader = YoutubeDL(default_options)
                logger.debug("✅ 下载器创建成功")
                return downloader
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"⚠️ 下载器创建失败: {e}")

                # 不再尝试修复非标准提取器，直接使用最小配置
                logger.info("🔄 使用最小配置重试创建下载器...")
                minimal_options = {
                    'quiet': True,
                    'no_warnings': True,
                    'ignoreerrors': True,
                    'extract_flat': True,  # 使用平面提取避免复杂 extractor
                    'ignore_no_formats_error': True,
                    'ignore_config': True,
                }
                if options:
                    # 只保留关键选项
                    safe_options = {k: v for k, v in options.items()
                                  if k in ['outtmpl', 'format', 'writesubtitles', 'writeautomaticsub']}
                    minimal_options.update(safe_options)

                downloader = YoutubeDL(minimal_options)
                logger.info("✅ 最小配置下载器创建成功")
                return downloader
            except Exception as e:
                logger.warning(f"⚠️ 标准配置下载器创建失败: {e}")

                # 最后尝试：超级最小配置
                logger.info("🔄 使用超级最小配置重试...")
                ultra_minimal_options = {
                    'quiet': True,
                    'ignoreerrors': True,
                }
                if options and 'outtmpl' in options:
                    ultra_minimal_options['outtmpl'] = options['outtmpl']

                downloader = YoutubeDL(ultra_minimal_options)
                logger.info("✅ 超级最小配置下载器创建成功")
                return downloader

        except Exception as e:
            logger.error(f"❌ 创建下载器失败: {e}")
            raise RuntimeError(f"无法创建下载器: {e}")

    def get_enhanced_options(self):
        """获取简化的 yt-dlp 选项 - 让yt-dlp自己处理复杂性"""
        return {
            # 完全使用yt-dlp默认配置，不添加任何额外选项
            # 这样yt-dlp会自动处理YouTube等网站的复杂性，就像命令行一样
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
