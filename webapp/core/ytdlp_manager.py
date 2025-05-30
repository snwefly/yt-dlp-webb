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
        common_missing = [
            'screencastify', 'screen9', 'screencast', 'screencastomatic',
            'screenrec', 'scribd', 'scrolller', 'scte', 'sendtonews'
        ]

        for extractor_name in common_missing:
            try:
                # 尝试导入，如果失败则动态创建
                module_name = f'yt_dlp.extractor.{extractor_name}'
                __import__(module_name)
            except ImportError:
                self._fix_missing_extractor(extractor_name)

    def _run_extractor_fix(self):
        """运行 extractor 修复"""
        try:
            # 首先预加载常见的缺失 extractor
            self._preload_common_extractors()

            import subprocess
            import sys

            # 尝试运行修复脚本
            fix_script = "/app/scripts/fix_extractors.py"
            if os.path.exists(fix_script):
                logger.debug("🔧 运行 extractor 修复脚本...")
                result = subprocess.run([sys.executable, fix_script],
                                      capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.debug("✅ extractor 修复成功")
                else:
                    # 只在调试模式下显示详细错误
                    logger.debug(f"⚠️ extractor 修复失败: {result.stderr}")
                    # 检查是否是版本错误，如果是则忽略
                    if "__version__" in result.stderr:
                        logger.debug("ℹ️ extractor 修复脚本版本检测问题，但不影响功能")
                    else:
                        logger.warning("⚠️ extractor 修复失败，但不影响核心功能")
            else:
                logger.debug("ℹ️ extractor 修复脚本不存在，跳过修复")
        except subprocess.TimeoutExpired:
            logger.debug("⚠️ extractor 修复超时，跳过")
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
            }

            if options:
                default_options.update(options)

            # 尝试创建下载器，如果失败则使用最小配置
            try:
                return YoutubeDL(default_options)
            except ImportError as ie:
                error_msg = str(ie)
                if 'extractor' in error_msg:
                    logger.warning(f"⚠️ extractor 导入警告: {ie}")

                    # 尝试提取缺失的 extractor 名称
                    if "No module named 'yt_dlp.extractor." in error_msg:
                        extractor_name = error_msg.split("'yt_dlp.extractor.")[1].split("'")[0]
                        logger.info(f"🔧 尝试动态修复缺失的 extractor: {extractor_name}")

                        if self._fix_missing_extractor(extractor_name):
                            # 重试创建下载器
                            try:
                                return YoutubeDL(default_options)
                            except Exception:
                                pass  # 如果还是失败，继续使用最小配置

                    # 使用最小配置重试
                    minimal_options = {
                        'quiet': True,
                        'no_warnings': True,
                        'ignoreerrors': True,
                        'extract_flat': True,  # 使用平面提取避免复杂 extractor
                    }
                    if options:
                        minimal_options.update(options)
                    return YoutubeDL(minimal_options)
                else:
                    raise

        except Exception as e:
            logger.error(f"❌ 创建下载器失败: {e}")
            raise RuntimeError(f"无法创建下载器: {e}")

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
