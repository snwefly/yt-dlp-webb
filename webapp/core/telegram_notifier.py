"""
Telegram通知模块 - Pyrogram 版本
支持下载完成后推送文件到Telegram
基于 Pyrogram 库实现，提供更稳定的文件上传功能
"""

import os
import logging
import asyncio
import tempfile
import shutil
import requests  # 保留用于 test_connection
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram通知器 - Pyrogram 版本"""

    def __init__(self):
        # 优先从数据库读取配置，回退到环境变量
        self._config = None
        self._pyrogram_client = None  # 全局 Pyrogram 客户端
        self._load_config()

    def _load_config(self):
        """加载配置"""
        try:
            # 尝试在应用上下文中加载配置
            try:
                from flask import current_app
                from ..models import TelegramConfig

                with current_app.app_context():
                    self._config = TelegramConfig.get_config()

                    # 如果数据库中没有配置，尝试从环境变量迁移
                    if not self._config.is_configured():
                        env_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                        env_chat_id = os.environ.get('TELEGRAM_CHAT_ID')

                        if env_token and env_chat_id:
                            self._config.bot_token = env_token
                            self._config.chat_id = env_chat_id
                            self._config.enabled = True
                            from ..models import db
                            db.session.commit()
                            logger.info("🔄 已从环境变量迁移Telegram配置到数据库")

                    if self._config.is_configured() and self._config.enabled:
                        logger.info("🤖 Telegram通知已启用 (Pyrogram)")
                    else:
                        logger.info("🤖 Telegram通知未配置")

            except RuntimeError:
                # 如果没有应用上下文，直接从环境变量加载
                logger.warning("⚠️ 无应用上下文，从环境变量加载配置")
                raise Exception("No app context")

        except Exception as e:
            logger.error(f"加载Telegram配置失败: {e}")
            # 回退到环境变量
            self._config = None
            self._bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
            self._chat_id = os.environ.get('TELEGRAM_CHAT_ID')
            self._api_id = os.environ.get('TELEGRAM_API_ID')
            self._api_hash = os.environ.get('TELEGRAM_API_HASH')
            self._enabled = bool(self._bot_token and self._chat_id)
            logger.info(f"🔄 使用环境变量配置: enabled={self._enabled}, api_id={bool(self._api_id)}, api_hash={bool(self._api_hash)}")

    @property
    def bot_token(self):
        """获取Bot Token"""
        if self._config:
            return self._config.bot_token
        return getattr(self, '_bot_token', None)

    @bot_token.setter
    def bot_token(self, value):
        """设置Bot Token"""
        self._bot_token = value

    @property
    def chat_id(self):
        """获取Chat ID"""
        if self._config:
            return self._config.chat_id
        return getattr(self, '_chat_id', None)

    @chat_id.setter
    def chat_id(self, value):
        """设置Chat ID"""
        self._chat_id = value

    @property
    def enabled(self):
        """检查是否启用"""
        if self._config:
            return self._config.enabled and self._config.is_configured()
        return getattr(self, '_enabled', False)

    @enabled.setter
    def enabled(self, value):
        """设置启用状态"""
        self._enabled = value

    @property
    def api_id(self):
        """获取API ID"""
        if self._config:
            return self._config.api_id
        return getattr(self, '_api_id', None)

    @api_id.setter
    def api_id(self, value):
        """设置API ID"""
        self._api_id = value

    @property
    def api_hash(self):
        """获取API Hash"""
        if self._config:
            return self._config.api_hash
        return getattr(self, '_api_hash', None)

    @api_hash.setter
    def api_hash(self, value):
        """设置API Hash"""
        self._api_hash = value

    def is_enabled(self) -> bool:
        """检查是否启用Telegram通知"""
        return self.enabled

    def reload_config(self):
        """重新加载配置"""
        logger.info("🔄 重新加载Telegram配置")
        # 重置客户端，确保使用新配置
        if self._pyrogram_client:
            print(f"🔄 配置变更，重置 Pyrogram 客户端")
            logger.info(f"🔄 配置变更，重置 Pyrogram 客户端")
            self._pyrogram_client = None
        self._load_config()

    def get_config(self):
        """获取当前配置对象"""
        return self._config

    def _get_clean_bot_token(self):
        """获取清理后的 Bot Token（移除 tgram:// 前缀和 Chat ID）"""
        token = self.bot_token
        if token and token.startswith('tgram://'):
            # 解析 tgram://BOT_TOKEN/CHAT_ID 格式
            url_part = token[8:]  # 移除 'tgram://' 前缀
            if '/' in url_part:
                token = url_part.split('/')[0]  # 只取 Token 部分
        return token

    def _get_pyrogram_chat_id(self):
        """获取适用于 Pyrogram 的 Chat ID"""
        chat_id = self.chat_id
        if not chat_id:
            return None

        try:
            # 确保是整数
            chat_id_int = int(chat_id)

            # 对于 Pyrogram，我们需要使用原始的 Chat ID
            # 如果是正数（个人聊天），直接使用
            # 如果是负数（群组），也直接使用
            return chat_id_int

        except (ValueError, TypeError):
            logger.error(f"❌ Chat ID 格式错误: {chat_id}")
            return None
    
    def _get_file_type(self, file_path: str) -> str:
        """检测文件类型"""
        try:
            # 首先尝试使用 filetype 库检测
            try:
                import filetype
                mime = filetype.guess_mime(file_path)
                if mime:
                    if "video" in mime:
                        return "video"
                    elif "audio" in mime:
                        return "audio"
                    elif "image" in mime:
                        return "photo"
            except ImportError:
                print("⚠️ filetype 库未安装，使用文件扩展名检测")
                logger.warning("filetype 库未安装，使用文件扩展名检测")

            # 回退到文件扩展名检测
            import os
            _, ext = os.path.splitext(file_path.lower())
            ext = ext.lstrip('.')

            # 视频格式
            video_extensions = {
                'mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v',
                '3gp', 'mpg', 'mpeg', 'ogv', 'ts', 'mts', 'm2ts', 'vob'
            }

            # 音频格式
            audio_extensions = {
                'mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'm4a', 'opus',
                'aiff', 'alac', 'ape', 'dts', 'ac3'
            }

            # 图片格式
            image_extensions = {
                'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'svg',
                'ico', 'heic', 'avif'
            }

            if ext in video_extensions:
                print(f"🎬 检测到视频文件: {ext}")
                logger.info(f"检测到视频文件: {ext}")
                return "video"
            elif ext in audio_extensions:
                print(f"🎵 检测到音频文件: {ext}")
                logger.info(f"检测到音频文件: {ext}")
                return "audio"
            elif ext in image_extensions:
                print(f"🖼️ 检测到图片文件: {ext}")
                logger.info(f"检测到图片文件: {ext}")
                return "photo"
            else:
                print(f"📄 未知格式，作为文档处理: {ext}")
                logger.info(f"未知格式，作为文档处理: {ext}")
                return "document"

        except Exception as e:
            print(f"❌ 文件类型检测失败: {e}")
            logger.error(f"文件类型检测失败: {e}")
            return "document"

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名"""
        import re
        import unicodedata

        # 移除 emoji 和特殊字符
        filename = ''.join(char for char in filename if unicodedata.category(char)[0] != 'S')
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'[()（）]', '', filename)
        filename = re.sub(r'\s+', '_', filename)

        # 限制长度
        name, ext = os.path.splitext(filename)
        if len(name) > 50:
            name = name[:50]
        filename = name + ext

        if not filename or filename == ext:
            filename = f"video{ext}"

        return filename

    async def _send_message_async(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """异步发送文本消息"""
        try:
            print(f"📤 开始发送消息...")
            logger.info(f"📤 开始发送消息...")

            # 首先尝试使用 Bot API（更稳定）
            print(f"🔄 尝试使用 Bot API 发送消息...")
            success = self._send_message_via_bot_api(message, parse_mode)
            if success:
                return True

            # Bot API 失败，尝试 Pyrogram
            if not self.api_id or not self.api_hash:
                print(f"❌ Bot API 失败且未配置 API ID/Hash，无法使用 Pyrogram")
                logger.error(f"❌ Bot API 失败且未配置 API ID/Hash，无法使用 Pyrogram")
                return False

            print(f"🔄 Bot API 失败，尝试 Pyrogram...")
            logger.info(f"🔄 Bot API 失败，尝试 Pyrogram...")

            # 使用统一的单例客户端，确保前后端一致性
            # 使用统一的异步执行方法
            return await self._send_message_with_pyrogram(message, parse_mode)

        except Exception as e:
            print(f"❌ Pyrogram 消息发送失败: {e}")
            logger.error(f"❌ Pyrogram 消息发送失败: {e}")

            # 检查是否是 FloodWait 错误
            if "FLOOD_WAIT" in str(e) or "FloodWait" in str(type(e).__name__):
                print(f"⏰ 消息发送遇到速率限制")
                logger.warning(f"⏰ 消息发送遇到速率限制")

            return False

    async def _send_message_with_pyrogram(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """使用统一的Pyrogram客户端发送消息 - 确保前后端一致性"""
        try:
            # 使用统一的单例客户端
            client = self._get_pyrogram_client()
            if not client:
                print(f"❌ 无法获取 Pyrogram 客户端")
                return False

            # 获取 Pyrogram Chat ID
            pyrogram_chat_id = self._get_pyrogram_chat_id()
            if not pyrogram_chat_id:
                print(f"❌ Chat ID 无效: {self.chat_id}")
                logger.error(f"❌ Chat ID 无效: {self.chat_id}")
                return False

            print(f"📨 使用单例客户端发送消息到 Chat ID: {pyrogram_chat_id}")
            logger.info(f"📨 使用单例客户端发送消息到 Chat ID: {pyrogram_chat_id}")

            # 确保客户端已启动
            if not client.is_connected:
                print(f"🚀 启动 Pyrogram 客户端...")
                await client.start()
                print(f"✅ Pyrogram 客户端启动成功")
                logger.info(f"✅ Pyrogram 客户端启动成功")

            # 发送消息
            result = await client.send_message(
                chat_id=pyrogram_chat_id,
                text=message,
                parse_mode=parse_mode
            )
            print(f"✅ Pyrogram 消息发送成功: {result.id}")
            logger.info(f"✅ Pyrogram 消息发送成功: {result.id}")
            return True

        except Exception as e:
            print(f"❌ Pyrogram 消息发送失败: {e}")
            logger.error(f"❌ Pyrogram 消息发送失败: {e}")

            # 检查是否是 FloodWait 错误
            if "FLOOD_WAIT" in str(e) or "FloodWait" in str(type(e).__name__):
                print(f"⏰ 消息发送遇到速率限制")
                logger.warning(f"⏰ 消息发送遇到速率限制")

            # 如果是连接相关错误，重置客户端
            if "connection" in str(e).lower() or "network" in str(e).lower():
                print(f"🔄 检测到连接错误，重置客户端")
                logger.warning(f"🔄 检测到连接错误，重置客户端")
                self._pyrogram_client = None

            return False

    def _send_message_via_bot_api(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """使用 Bot API 发送消息（回退方案）"""
        try:
            import requests

            clean_token = self._get_clean_bot_token()
            if not clean_token:
                print(f"❌ Bot Token 无效")
                logger.error(f"❌ Bot Token 无效")
                return False

            print(f"🔧 Bot API 配置:")
            print(f"   Token: {clean_token[:10]}...")
            print(f"   Chat ID: {self.chat_id}")
            print(f"   消息长度: {len(message)} 字符")

            url = f"https://api.telegram.org/bot{clean_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }

            print(f"📤 使用 Bot API 发送消息到: {url}")
            logger.info(f"📤 使用 Bot API 发送消息")

            response = requests.post(url, json=data, timeout=30)

            print(f"📊 响应状态码: {response.status_code}")
            logger.info(f"📊 响应状态码: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ HTTP 错误: {response.status_code}")
                print(f"❌ 响应内容: {response.text}")
                logger.error(f"❌ HTTP 错误: {response.status_code}, 内容: {response.text}")
                return False

            result = response.json()
            print(f"📋 API 响应: {result}")
            logger.info(f"📋 API 响应: {result}")

            if result.get('ok'):
                print(f"✅ Bot API 消息发送成功")
                logger.info(f"✅ Bot API 消息发送成功")
                return True
            else:
                error_code = result.get('error_code', 'unknown')
                error_desc = result.get('description', 'unknown error')
                print(f"❌ Bot API 消息发送失败:")
                print(f"   错误代码: {error_code}")
                print(f"   错误描述: {error_desc}")
                logger.error(f"❌ Bot API 消息发送失败: {error_code} - {error_desc}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求异常: {e}")
            logger.error(f"❌ 网络请求异常: {e}")
            return False
        except Exception as e:
            print(f"❌ Bot API 消息发送异常: {e}")
            logger.error(f"❌ Bot API 消息发送异常: {e}")
            return False

    def send_message(self, message: str, parse_mode: str = 'Markdown') -> bool:
        """发送文本消息 - 同步包装器"""
        if not self.enabled:
            return False

        try:
            # 检查是否已有事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，使用线程池执行
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(self._run_async_in_thread, self._send_message_async, message, parse_mode)
                        return future.result(timeout=60)
                else:
                    return loop.run_until_complete(self._send_message_async(message, parse_mode))
            except RuntimeError:
                # 没有事件循环，创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self._send_message_async(message, parse_mode))
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"❌ 同步消息发送失败: {e}")
            return False

    def _run_async_in_thread(self, async_func, *args, **kwargs):
        """在新线程中运行异步函数"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            loop.close()

    def _run_async_safely(self, async_func, *args, **kwargs):
        """安全地运行异步函数，统一事件循环管理"""
        try:
            # 检查是否已有事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，使用线程池执行
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(self._run_async_in_thread, async_func, *args, **kwargs)
                        return future.result(timeout=300)  # 5分钟超时
                else:
                    return loop.run_until_complete(async_func(*args, **kwargs))
            except RuntimeError:
                # 没有事件循环，创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(async_func(*args, **kwargs))
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"❌ 异步函数执行失败: {e}")
            return False
    


    def _send_document_via_bot_api(self, file_path: str, caption: str = "", parse_mode: str = 'Markdown') -> bool:
        """使用 Bot API 发送文件（回退方案）"""
        try:
            import requests

            clean_token = self._get_clean_bot_token()
            if not clean_token:
                print(f"❌ Bot Token 无效")
                return False

            url = f"https://api.telegram.org/bot{clean_token}/sendDocument"

            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption,
                    'parse_mode': parse_mode
                }

                print(f"📤 使用 Bot API 发送文件...")
                response = requests.post(url, files=files, data=data, timeout=300)
                response.raise_for_status()

                result = response.json()
                if result.get('ok'):
                    print(f"✅ Bot API 发送成功")
                    logger.info(f"✅ Bot API 发送成功")
                    return True
                else:
                    print(f"❌ Bot API 发送失败: {result}")
                    logger.error(f"❌ Bot API 发送失败: {result}")
                    return False

        except Exception as e:
            print(f"❌ Bot API 发送异常: {e}")
            logger.error(f"❌ Bot API 发送异常: {e}")
            return False

    def send_document(self, file_path: str, caption: str = "", parse_mode: str = 'Markdown') -> bool:
        """发送文件 - 智能选择方案"""
        if not self.enabled:
            return False

        if not os.path.exists(file_path):
            logger.error(f"❌ 文件不存在: {file_path}")
            return False

        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / 1024 / 1024

        print(f"📁 文件大小: {file_size_mb:.1f} MB")
        logger.info(f"📁 文件大小: {file_size_mb:.1f} MB")

        # 根据文件大小和 API 配置选择发送方式
        bot_api_limit = 50  # Bot API 限制 50MB
        pyrogram_limit = 2048  # Pyrogram 限制 2GB

        # 优先使用 Pyrogram（速度更快，支持更大文件）
        if file_size_mb <= pyrogram_limit and self.api_id and self.api_hash:
            print(f"📤 使用 Pyrogram 发送文件 ({file_size_mb:.1f}MB)")
            logger.info(f"📤 使用 Pyrogram 发送文件 ({file_size_mb:.1f}MB)")

            try:
                # 使用 Pyrogram 方案，复用事件循环管理逻辑
                return self._run_async_safely(self._send_file_with_pyrogram, file_path, caption, parse_mode)
            except Exception as e:
                print(f"❌ Pyrogram 发送失败: {e}")
                logger.error(f"❌ Pyrogram 发送失败: {e}")

                # 如果文件小于50MB，回退到Bot API
                if file_size_mb <= bot_api_limit:
                    print(f"⚠️ Pyrogram 失败，回退到 Bot API")
                    logger.warning(f"⚠️ Pyrogram 失败，回退到 Bot API")
                    return self._send_document_via_bot_api(file_path, caption, parse_mode)
                else:
                    return False

        # 如果没有配置 API ID/Hash，使用 Bot API（仅限小文件）
        elif file_size_mb <= bot_api_limit:
            print(f"📤 使用 Bot API 发送小文件 ({file_size_mb:.1f}MB)")
            logger.info(f"📤 使用 Bot API 发送小文件 ({file_size_mb:.1f}MB)")
            return self._send_document_via_bot_api(file_path, caption, parse_mode)

        # 文件过大且没有配置 Pyrogram
        elif not self.api_id or not self.api_hash:
            print(f"❌ 文件过大 ({file_size_mb:.1f}MB > {bot_api_limit}MB) 且未配置 API ID/Hash")
            logger.error(f"❌ 文件过大且未配置 API ID/Hash，无法发送")
            return False

        # 文件超过 Pyrogram 限制
        else:
            print(f"❌ 文件过大 ({file_size_mb:.1f}MB > {pyrogram_limit}MB)")
            logger.error(f"❌ 文件过大 ({file_size_mb:.1f}MB > {pyrogram_limit}MB)")
            return False

        # 所有方法都失败时，发送通知
        print(f"⚠️ 文件发送失败，发送通知消息")
        logger.warning(f"⚠️ 文件发送失败，发送通知消息")
        return self.send_download_notification(file_path, caption, file_too_large=True)

    async def _send_file_with_pyrogram(self, file_path: str, caption: str = "", parse_mode: str = 'Markdown') -> bool:
        """使用 Pyrogram 发送文件（延迟初始化单例版本）"""
        try:
            # 获取延迟初始化的客户端
            client = self._get_pyrogram_client()
            if not client:
                print(f"❌ 无法获取 Pyrogram 客户端")
                return False

            # 获取 Pyrogram Chat ID
            pyrogram_chat_id = self._get_pyrogram_chat_id()
            if not pyrogram_chat_id:
                print(f"❌ Chat ID 无效")
                return False

            print(f"🔗 使用延迟初始化的 Pyrogram 客户端发送文件...")
            logger.info(f"🔗 使用延迟初始化的 Pyrogram 客户端发送文件...")

            # 确保客户端已启动
            if not client.is_connected:
                print(f"🚀 启动 Pyrogram 客户端...")
                await client.start()
                print(f"✅ Pyrogram 客户端启动成功")
                logger.info(f"✅ Pyrogram 客户端启动成功")

            # 发送文件
            filename = os.path.basename(file_path)
            file_type = self._get_file_type(file_path)

            # 上传进度回调
            last_percent = [0]
            def progress_callback(current, total):
                percent = (current / total) * 100
                # 每20%显示一次，减少日志输出
                if int(percent / 20) > int(last_percent[0] / 20):
                    print(f"📤 上传进度: {percent:.0f}%")
                    logger.info(f"📤 上传进度: {percent:.0f}%")
                    last_percent[0] = percent

            print(f"🎯 开始发送文件，类型: {file_type}")
            logger.info(f"🎯 开始发送文件，类型: {file_type}")

            # 根据文件类型发送
            message = None
            if file_type == "video":
                try:
                    message = await client.send_video(
                        chat_id=pyrogram_chat_id,
                        video=file_path,
                        caption=caption,
                        supports_streaming=True,
                        progress=progress_callback
                    )
                    print("✅ 作为视频发送成功")
                    logger.info("✅ 作为视频发送成功")
                except Exception as e:
                    print(f"⚠️ 作为视频发送失败: {e}")
                    logger.warning(f"作为视频发送失败: {e}")

            elif file_type == "audio":
                try:
                    message = await client.send_audio(
                        chat_id=pyrogram_chat_id,
                        audio=file_path,
                        caption=caption,
                        progress=progress_callback
                    )
                    print("✅ 作为音频发送成功")
                    logger.info("✅ 作为音频发送成功")
                except Exception as e:
                    print(f"⚠️ 作为音频发送失败: {e}")
                    logger.warning(f"作为音频发送失败: {e}")

            elif file_type == "photo":
                try:
                    message = await client.send_photo(
                        chat_id=pyrogram_chat_id,
                        photo=file_path,
                        caption=caption,
                        progress=progress_callback
                    )
                    print("✅ 作为图片发送成功")
                    logger.info("✅ 作为图片发送成功")
                except Exception as e:
                    print(f"⚠️ 作为图片发送失败: {e}")
                    logger.warning(f"作为图片发送失败: {e}")

            # 如果以上方法都失败，作为文档发送
            if not message:
                print(f"📄 作为文档发送...")
                logger.info(f"📄 作为文档发送...")

                message = await client.send_document(
                    chat_id=pyrogram_chat_id,
                    document=file_path,
                    caption=caption,
                    progress=progress_callback
                )
                print("✅ 作为文档发送成功")
                logger.info("✅ 作为文档发送成功")

            if message:
                print(f"🎉 Pyrogram 文件发送成功: {filename}")
                logger.info(f"✅ Pyrogram 文件发送成功: {filename}")
                return True
            else:
                print(f"❌ Pyrogram 文件发送失败: {filename}")
                logger.error(f"❌ Pyrogram 文件发送失败: {filename}")
                return False

        except Exception as e:
            print(f"💥 Pyrogram 发送异常: {e}")
            logger.error(f"💥 Pyrogram 发送异常: {e}")

            # 如果是连接相关错误，重置客户端以便下次重新创建
            if "connection" in str(e).lower() or "network" in str(e).lower():
                print(f"🔄 检测到连接错误，重置客户端")
                logger.warning(f"🔄 检测到连接错误，重置客户端")
                self._pyrogram_client = None

            return False




    def send_download_notification(self, file_path: str, original_url: str = "",
                                 file_too_large: bool = False, send_failed: bool = False) -> bool:
        """发送下载完成通知"""
        if not self.enabled:
            return False
            
        try:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            file_size_mb = file_size / 1024 / 1024
            
            # 构建消息
            message = "🎬 *下载完成通知*\n\n"
            message += f"📁 文件名: `{filename}`\n"
            message += f"📊 大小: {file_size_mb:.1f} MB\n"
            message += f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            if original_url:
                message += f"🔗 原始链接: {original_url}\n"
            
            if file_too_large:
                message += "\n⚠️ *文件过大，无法直接发送*\n"
                message += "请通过Web界面下载"
            elif send_failed:
                message += "\n❌ *文件发送失败*\n"
                message += "请通过Web界面下载"
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"❌ 发送下载通知失败: {e}")
            return False
    
    def send_download_started(self, url: str, download_id: str) -> bool:
        """发送下载开始通知"""
        if not self.enabled:
            return False
            
        message = "🚀 *开始下载*\n\n"
        message += f"🔗 链接: {url}\n"
        message += f"🆔 任务ID: `{download_id}`\n"
        message += f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(message)
    
    def send_download_failed(self, url: str, error: str, download_id: str) -> bool:
        """发送下载失败通知"""
        if not self.enabled:
            return False
            
        message = "❌ *下载失败*\n\n"
        message += f"🔗 链接: {url}\n"
        message += f"🆔 任务ID: `{download_id}`\n"
        message += f"💥 错误: {error}\n"
        message += f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return self.send_message(message)
    
    def test_connection(self) -> Dict[str, Any]:
        """测试Telegram连接"""
        if not self.bot_token:
            return {
                'success': False,
                'error': '未配置Bot Token'
            }

        # 验证bot_token格式
        import re

        # 处理 tgram:// URL 格式
        token_to_validate = self.bot_token
        if token_to_validate.startswith('tgram://'):
            # 解析 tgram://BOT_TOKEN/CHAT_ID 格式
            url_part = token_to_validate[8:]  # 移除 'tgram://' 前缀
            if '/' in url_part:
                token_to_validate = url_part.split('/')[0]  # 只取 Token 部分

        # Telegram Bot Token 格式: BOT_ID:BOT_ALPHANUMERIC_PART
        # BOT_ID: 8-10位数字, BOT_ALPHANUMERIC_PART: 35个字符 (字母数字下划线连字符)
        token_pattern = r'^\d{8,10}:[A-Za-z0-9_-]{35}$'

        if not re.match(token_pattern, token_to_validate):
            # 详细分析Token格式
            parts = token_to_validate.split(':')
            if len(parts) != 2:
                error_detail = f'Token应包含一个冒号分隔符，当前有{len(parts)-1}个'
            else:
                bot_id, token_part = parts
                bot_id_valid = bot_id.isdigit() and 8 <= len(bot_id) <= 10
                token_part_valid = len(token_part) == 35 and re.match(r'^[A-Za-z0-9_-]+$', token_part)

                if not bot_id_valid:
                    error_detail = f'Bot ID部分无效: "{bot_id}" (应为8-10位数字，当前{len(bot_id)}位)'
                elif not token_part_valid:
                    error_detail = f'Token部分无效: "{token_part}" (应为35个字符，当前{len(token_part)}个字符)'
                else:
                    error_detail = '未知格式错误'

            return {
                'success': False,
                'error': f'Bot Token格式不正确: {token_to_validate[:20]}...\n{error_detail}\n正确格式: 8-10位数字:35个字符(字母数字下划线连字符)'
            }

        # 检查清理后的token是否包含chat_id
        if self.chat_id and self.chat_id in token_to_validate:
            return {
                'success': False,
                'error': f'Bot Token中包含Chat ID，请检查配置。\nBot Token: {token_to_validate[:20]}...\nChat ID: {self.chat_id}'
            }

        try:
            # 测试Bot信息 - 使用解析后的 token
            url = f"https://api.telegram.org/bot{token_to_validate}/getMe"
            logger.info(f"🔗 测试URL: {url}")

            response = requests.get(url, timeout=10)
            response.raise_for_status()
            bot_info = response.json()

            if not bot_info.get('ok'):
                return {
                    'success': False,
                    'error': 'Bot Token无效'
                }

            # 测试发送消息
            if self.chat_id:
                test_message = "🧪 *Telegram通知测试*\n\n✅ 连接成功！"
                if self.send_message(test_message):
                    return {
                        'success': True,
                        'bot_info': bot_info['result'],
                        'message': '测试成功，已发送测试消息'
                    }
                else:
                    return {
                        'success': False,
                        'error': '无法发送消息，请检查Chat ID'
                    }
            else:
                return {
                    'success': True,
                    'bot_info': bot_info['result'],
                    'message': 'Bot Token有效，但未配置Chat ID'
                }

        except Exception as e:
            error_msg = str(e)
            if '404' in error_msg and 'Not Found' in error_msg:
                return {
                    'success': False,
                    'error': f'API端点不存在，请检查Bot Token格式。\n错误: {error_msg}\n测试URL: {url}'
                }
            else:
                return {
                    'success': False,
                    'error': f'连接失败: {error_msg}'
                }



    def _get_pyrogram_client(self):
        """获取 Pyrogram 客户端 - 延迟初始化单例模式"""
        # 延迟初始化：只在第一次需要时创建客户端
        if self._pyrogram_client is not None:
            return self._pyrogram_client

        if not (self.api_id and self.api_hash):
            print(f"⚠️ 未配置 API ID/Hash，无法创建 Pyrogram 客户端")
            logger.warning(f"⚠️ 未配置 API ID/Hash，无法创建 Pyrogram 客户端")
            return None

        try:
            from pyrogram import Client
            import signal
            import threading

            clean_token = self._get_clean_bot_token()
            if not clean_token:
                print(f"❌ Bot Token 无效")
                return None

            print(f"🔧 延迟创建 Pyrogram 客户端...")
            logger.info(f"🔧 延迟创建 Pyrogram 客户端...")

            # 创建客户端，使用稳定的配置
            self._pyrogram_client = Client(
                name="ytdlp_stable",  # 使用固定名称，避免频繁创建新会话
                api_id=int(self.api_id),
                api_hash=self.api_hash,
                bot_token=clean_token,
                workers=1,  # 最小并发数
                no_updates=True,  # 禁用更新处理，避免事件循环问题
                sleep_threshold=60,  # 增加睡眠阈值
                max_concurrent_transmissions=1  # 限制并发传输
            )

            # 尝试注册信号处理器（只在主线程中有效）
            try:
                def signal_handler(signum, frame):
                    self._cleanup_pyrogram_client_sync()

                signal.signal(signal.SIGTERM, signal_handler)
                signal.signal(signal.SIGINT, signal_handler)
                print(f"✅ 信号处理器注册成功")
                logger.info(f"✅ 信号处理器注册成功")
            except ValueError as e:
                # 在非主线程中会出现这个错误，这是正常的
                print(f"⚠️ 信号处理器注册失败（非主线程）: {e}")
                logger.warning(f"⚠️ 信号处理器注册失败（非主线程）: {e}")

            print(f"✅ Pyrogram 客户端创建成功")
            logger.info(f"✅ Pyrogram 客户端创建成功")
            return self._pyrogram_client

        except Exception as e:
            print(f"❌ 创建 Pyrogram 客户端失败: {e}")
            logger.error(f"❌ 创建 Pyrogram 客户端失败: {e}")
            return None

    def _cleanup_pyrogram_client_sync(self):
        """同步清理 Pyrogram 客户端"""
        if self._pyrogram_client:
            try:
                print(f"🧹 同步清理 Pyrogram 客户端...")
                logger.info(f"🧹 同步清理 Pyrogram 客户端...")

                # 使用同步方式停止客户端
                import asyncio
                import threading

                def stop_client():
                    try:
                        # 创建新的事件循环在独立线程中停止客户端
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self._pyrogram_client.stop())
                        loop.close()
                    except Exception as e:
                        print(f"⚠️ 停止客户端时出错: {e}")

                # 在独立线程中停止客户端，避免阻塞主线程
                stop_thread = threading.Thread(target=stop_client)
                stop_thread.daemon = True
                stop_thread.start()
                stop_thread.join(timeout=5)  # 最多等待5秒

                self._pyrogram_client = None
                print(f"✅ Pyrogram 客户端已清理")
                logger.info(f"✅ Pyrogram 客户端已清理")

            except Exception as e:
                print(f"⚠️ 清理 Pyrogram 客户端时出错: {e}")
                logger.warning(f"⚠️ 清理 Pyrogram 客户端时出错: {e}")
                self._pyrogram_client = None




# 全局实例
_telegram_notifier = TelegramNotifier()

def get_telegram_notifier() -> TelegramNotifier:
    """获取Telegram通知器实例"""
    return _telegram_notifier
