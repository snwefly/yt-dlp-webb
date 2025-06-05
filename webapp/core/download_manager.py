# -*- coding: utf-8 -*-
"""
下载管理器 - 完整版本
"""

import uuid
import threading
import logging
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from .telegram_notifier import get_telegram_notifier

logger = logging.getLogger(__name__)

class DownloadManager:
    """下载管理器"""

    def __init__(self, app=None):
        self.downloads = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=3)  # 最多3个并发下载
        self.app = app  # Flask 应用实例

    def create_download(self, url, options=None):
        """创建并启动下载任务"""
        download_id = str(uuid.uuid4())

        download_info = {
            'id': download_id,
            'url': url,
            'status': 'pending',
            'progress': 0,
            'created_at': datetime.now(),
            'options': options or {},
            'filename': None,
            'file_path': None,  # 完整文件路径
            'file_size': None,  # 文件大小
            'download_url': None,  # Web下载链接
            'error': None,
            'speed': None,
            'eta': None,
            'total_bytes': None,
            'downloaded_bytes': 0
        }

        with self.lock:
            self.downloads[download_id] = download_info

        logger.info(f"📥 创建下载任务: {download_id} - {url}")

        # 发送Telegram开始通知
        telegram_notifier = get_telegram_notifier()
        if telegram_notifier.is_enabled():
            telegram_notifier.send_download_started(url, download_id)

        # 立即启动下载任务
        self.executor.submit(self._execute_download, download_id, url, options or {})

        return download_id
    
    def get_download(self, download_id):
        """获取下载信息"""
        with self.lock:
            return self.downloads.get(download_id)
    
    def get_all_downloads(self):
        """获取所有下载"""
        with self.lock:
            return list(self.downloads.values())

    def get_downloads_by_status(self, status):
        """根据状态获取下载列表"""
        with self.lock:
            return [download for download in self.downloads.values() if download.get('status') == status]
    
    def update_download(self, download_id, **kwargs):
        """更新下载信息"""
        with self.lock:
            if download_id in self.downloads:
                self.downloads[download_id].update(kwargs)
                return True
        return False

    def _execute_download(self, download_id, url, options):
        """执行实际的下载任务"""
        try:
            logger.info(f"🎬 开始下载任务 {download_id}: {url}")

            # 更新状态为下载中
            self.update_download(download_id, status='downloading')

            # 设置下载目录
            download_dir = os.environ.get('DOWNLOAD_FOLDER', '/app/downloads')
            if not os.path.exists(download_dir):
                os.makedirs(download_dir, exist_ok=True)
                # 设置目录权限
                os.chmod(download_dir, 0o755)

            # 首先尝试使用自定义提取器获取信息
            from .custom_extractors import get_custom_extractor
            custom_extractor = get_custom_extractor(url)

            if custom_extractor:
                logger.info(f"🎯 使用自定义提取器下载: {custom_extractor.IE_NAME}")
                self._download_with_custom_extractor(download_id, url, custom_extractor, download_dir, options)
            else:
                # 使用标准yt-dlp下载
                logger.info(f"🔄 使用yt-dlp标准下载器")
                ydl_opts = self._build_ytdlp_options(download_id, download_dir, options, url)

                # 创建下载器并执行下载
                logger.info(f"📥 开始下载: {url}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

            # 下载完成，查找下载的文件
            print(f"📁📁📁 开始查找下载文件，目录: {download_dir} 📁📁📁")
            downloaded_files = self._find_downloaded_files(download_dir, download_id)
            print(f"🔍🔍🔍 找到的文件: {downloaded_files} 🔍🔍🔍")

            if downloaded_files:
                main_file = downloaded_files[0]  # 主文件
                file_path = os.path.join(download_dir, main_file)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                print(f"✅✅✅ 主文件: {main_file}, 路径: {file_path}, 大小: {file_size} ✅✅✅")

                self.update_download(download_id,
                    status='completed',
                    progress=100,
                    completed_at=datetime.now(),
                    filename=main_file,
                    file_path=file_path,
                    file_size=file_size,
                    download_url=f'/api/download/{download_id}/file'
                )
                logger.info(f"✅ 下载完成: {download_id} -> {main_file}")

                # 发送Telegram通知和文件
                print("🚀🚀🚀 准备调用 Telegram 推送函数 🚀🚀🚀")
                print(f"   下载ID: {download_id}")
                print(f"   URL: {url}")
                print(f"   文件路径: {file_path}")
                print(f"   文件名: {main_file}")
                logger.error(f"🚀🚀🚀 准备调用 Telegram 推送函数 🚀🚀🚀")

                try:
                    # 🔧 在应用上下文中执行推送
                    if self.app:
                        with self.app.app_context():
                            self._send_telegram_notification(download_id)
                    else:
                        # 如果没有应用实例，直接调用
                        self._send_telegram_notification(download_id)
                    print("✅✅✅ Telegram 推送函数调用完成 ✅✅✅")
                    logger.error(f"✅✅✅ Telegram 推送函数调用完成 ✅✅✅")
                except Exception as e:
                    print(f"❌❌❌ Telegram 推送函数调用失败: {e}")
                    logger.error(f"❌❌❌ Telegram 推送函数调用失败: {e}", exc_info=True)

                    # 尝试发送错误通知
                    try:
                        if self.app:
                            with self.app.app_context():
                                from ..core.telegram_notifier import TelegramNotifier
                                notifier = TelegramNotifier()
                                notifier.send_message(f"❌ **推送失败**\n\n文件: {main_file}\n错误: {str(e)}")
                    except:
                        pass
            else:
                # 没有找到文件，可能下载失败
                print(f"❌❌❌ 没有找到下载文件！download_id: {download_id} ❌❌❌")
                print(f"📂📂📂 下载目录内容: {os.listdir(download_dir) if os.path.exists(download_dir) else '目录不存在'} 📂📂📂")

                self.update_download(download_id,
                    status='completed',
                    progress=100,
                    completed_at=datetime.now(),
                    error='下载完成但未找到文件'
                )
                logger.warning(f"⚠️ 下载完成但未找到文件: {download_id}")

                # 这里不会调用推送函数，因为没有文件
                print(f"🚫🚫🚫 因为没有找到文件，不会调用推送函数 🚫🚫🚫")

        except Exception as e:
            logger.error(f"❌ 下载失败 {download_id}: {e}")
            self.update_download(download_id,
                status='failed',
                error=str(e),
                failed_at=datetime.now()
            )

            # 发送Telegram失败通知
            telegram_notifier = get_telegram_notifier()
            if telegram_notifier.is_enabled():
                telegram_notifier.send_download_failed(url, str(e), download_id)

    def _download_with_custom_extractor(self, download_id, url, extractor, download_dir, options):
        """使用自定义提取器下载视频"""
        try:
            # 提取视频信息
            info = extractor.extract_info(url)

            if not info or not info.get('formats'):
                raise Exception("未找到可下载的视频格式")

            # 选择最佳格式
            video_format = self._select_best_format(info['formats'], options)
            if not video_format:
                raise Exception("没有合适的视频格式")

            video_url = video_format['url']
            title = info.get('title', 'Unknown')

            # 清理文件名
            safe_title = self._sanitize_filename(title)
            ext = video_format.get('ext', 'mp4')
            filename = f"{safe_title}.{ext}"
            file_path = os.path.join(download_dir, filename)

            logger.info(f"📥 开始下载自定义视频: {title}")
            logger.info(f"🎯 视频URL: {video_url}")

            # 下载视频文件
            self._download_file_with_progress(video_url, file_path, download_id, info)

            # 更新下载信息
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            self.update_download(download_id,
                status='completed',
                progress=100,
                completed_at=datetime.now(),
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                download_url=f'/api/download/{download_id}/file'
            )

            logger.info(f"✅ 自定义下载完成: {filename}")

        except Exception as e:
            logger.error(f"❌ 自定义下载失败: {e}")
            raise

    def _select_best_format(self, formats, options):
        """选择最佳视频格式"""
        if not formats:
            return None

        # 优先选择HLS格式（m3u8）
        hls_formats = [f for f in formats if f.get('protocol') == 'm3u8']
        if hls_formats:
            return hls_formats[0]

        # 其次选择直接视频格式
        video_formats = [f for f in formats if f.get('ext') in ['mp4', 'webm', 'mkv']]
        if video_formats:
            return video_formats[0]

        # 最后选择第一个可用格式
        return formats[0]

    def _sanitize_filename(self, filename):
        """清理文件名，移除不安全字符"""
        import re
        # 移除或替换不安全字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        # 限制长度
        if len(filename) > 200:
            filename = filename[:200]
        return filename or "video"

    def _download_file_with_progress(self, url, file_path, download_id, info):
        """下载文件并显示进度"""
        import requests

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        }

        # 检查是否为HLS流
        if '.m3u8' in url:
            self._download_hls_stream(url, file_path, download_id, headers)
        else:
            self._download_direct_file(url, file_path, download_id, headers)

    def _download_hls_stream(self, m3u8_url, file_path, download_id, headers):
        """下载HLS流"""
        try:
            # 使用ffmpeg下载HLS流
            import subprocess

            cmd = [
                'ffmpeg',
                '-i', m3u8_url,
                '-c', 'copy',
                '-y',  # 覆盖输出文件
                file_path
            ]

            logger.info(f"🎬 使用ffmpeg下载HLS流: {m3u8_url}")

            # 执行ffmpeg命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            # 等待完成
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                logger.info("✅ HLS流下载完成")
            else:
                logger.error(f"❌ ffmpeg下载失败: {stderr}")
                raise Exception(f"ffmpeg下载失败: {stderr}")

        except FileNotFoundError:
            logger.warning("⚠️ ffmpeg未找到，尝试使用requests下载")
            # 回退到直接下载
            self._download_direct_file(m3u8_url, file_path, download_id, headers)
        except Exception as e:
            logger.error(f"❌ HLS下载失败: {e}")
            raise

    def _download_direct_file(self, url, file_path, download_id, headers):
        """直接下载文件"""
        import requests

        try:
            response = requests.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # 更新进度
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.update_download(download_id,
                                progress=progress,
                                downloaded_bytes=downloaded_size,
                                total_bytes=total_size
                            )

            logger.info(f"✅ 直接下载完成: {file_path}")

        except Exception as e:
            logger.error(f"❌ 直接下载失败: {e}")
            raise

    def _build_ytdlp_options(self, download_id, download_dir, options, url):
        """构建yt-dlp下载选项 - 基于最新源代码优化以避免bot检测"""
        # 基础配置
        # 使用更复杂的文件名模板避免冲突
        import time
        import hashlib
        timestamp = int(time.time())

        # 为URL生成短hash作为唯一标识
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        # 构建多层次的文件名模板，确保唯一性
        # 优先级：title + id + timestamp > title + hash + timestamp > hash + timestamp
        filename_templates = [
            f'%(title)s_%(id)s_{timestamp}.%(ext)s',  # 最佳：有title和id
            f'%(title)s_{url_hash}_{timestamp}.%(ext)s',  # 备用：有title但无id
            f'video_{url_hash}_{timestamp}.%(ext)s'  # 最后备用：无title无id
        ]

        # 使用第一个模板，yt-dlp会自动处理缺失字段
        primary_template = filename_templates[0]

        ydl_opts = {
            'outtmpl': os.path.join(download_dir, primary_template),
            # 网络配置
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            # 错误处理
            'ignoreerrors': False,
            'no_warnings': False,
            # 避免覆盖现有文件
            'overwrites': False,
            # 如果文件已存在，自动重命名
            'nooverwrites': True,
            # 处理缺失字段的占位符
            'outtmpl_na_placeholder': 'unknown',
        }

        print(f"🏷️ 文件名模板: {primary_template}")
        print(f"🔗 URL Hash: {url_hash}")
        print(f"⏰ 时间戳: {timestamp}")
        logger.info(f"文件名模板: {primary_template}, URL Hash: {url_hash}")

        # 额外的文件冲突处理：如果预期文件名已存在，添加序号
        def get_unique_filename(base_template, download_dir):
            """确保文件名唯一，如果存在冲突则添加序号"""
            # 简单预测可能的文件名（不完全准确，但可以处理大部分情况）
            test_filename = base_template.replace('%(title)s', 'video').replace('%(id)s', 'unknown').replace('%(ext)s', 'mp4')
            test_path = os.path.join(download_dir, test_filename)

            counter = 1
            original_template = base_template

            # 检查是否存在类似的文件
            while True:
                # 检查是否有匹配的文件存在
                existing_files = []
                if os.path.exists(download_dir):
                    existing_files = [f for f in os.listdir(download_dir)
                                    if f.startswith('video') and (f.endswith('.mp4') or f.endswith('.webm') or f.endswith('.mkv'))]

                # 如果没有冲突的文件，使用原模板
                if not existing_files:
                    break

                # 如果有冲突，在模板中添加序号
                if counter == 1:
                    # 第一次冲突，添加序号
                    base_template = original_template.replace('.%(ext)s', f'_{counter}.%(ext)s')
                else:
                    # 后续冲突，更新序号
                    base_template = original_template.replace('.%(ext)s', f'_{counter}.%(ext)s')

                counter += 1

                # 防止无限循环
                if counter > 100:
                    break

            return base_template

        # 应用唯一文件名检查
        unique_template = get_unique_filename(primary_template, download_dir)
        if unique_template != primary_template:
            print(f"🔄 检测到潜在冲突，使用唯一模板: {unique_template}")
            logger.info(f"使用唯一文件名模板: {unique_template}")
            ydl_opts['outtmpl'] = os.path.join(download_dir, unique_template)

        # Cookies处理 - 核心功能：自动调取对应平台cookies给下载器
        from .cookies_manager import get_cookies_manager
        cookies_manager = get_cookies_manager()

        # 根据URL自动调取对应平台的cookies文件
        cookies_file = cookies_manager.get_cookies_for_url(url)

        # 直接给yt-dlp使用
        cookies_set = False
        if os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
            cookies_set = True
            logger.info(f"✅ 已设置cookies文件给下载器: {cookies_file}")
        else:
            logger.warning(f"⚠️ Cookies文件不存在: {cookies_file}")

        # 2. 备用：尝试浏览器cookies（容器环境通常不可用）
        if not cookies_set:
            try:
                ydl_opts['cookiesfrombrowser'] = ('firefox',)
                logger.info("🍪 尝试使用Firefox浏览器cookies")
                cookies_set = True
            except Exception as e:
                logger.debug(f"Firefox cookies获取失败: {e}")

        # 3. 最后备用：Chrome cookies
        if not cookies_set:
            try:
                ydl_opts['cookiesfrombrowser'] = ('chrome',)
                logger.info("🍪 尝试使用Chrome浏览器cookies")
                cookies_set = True
            except Exception as e:
                logger.debug(f"Chrome cookies获取失败: {e}")

        # 4. 如果都没有，记录警告
        if not cookies_set:
            logger.warning("❌ 无可用cookies，YouTube下载可能失败")

        # 进度回调
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded_bytes = d.get('downloaded_bytes', 0)
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)

                    if total_bytes > 0:
                        progress = int((downloaded_bytes / total_bytes) * 100)
                    else:
                        progress = 0

                    self.update_download(download_id,
                        progress=progress,
                        downloaded_bytes=downloaded_bytes,
                        total_bytes=total_bytes,
                        speed=speed,
                        eta=eta,
                        filename=d.get('filename', '')
                    )

                    logger.debug(f"📊 下载进度 {download_id}: {progress}%")
                except Exception as e:
                    logger.warning(f"更新进度失败: {e}")

            elif d['status'] == 'finished':
                logger.info(f"🎉 文件下载完成: {d.get('filename', '')}")
                self.update_download(download_id,
                    filename=d.get('filename', ''),
                    progress=100
                )

        ydl_opts['progress_hooks'] = [progress_hook]

        # 应用用户选项 - 完全支持用户自定义
        video_quality = options.get('video_quality')
        output_format = options.get('output_format', 'best')

        # 首先处理视频质量
        if video_quality:
            if video_quality == 'best':
                base_format = 'best'
            elif video_quality == 'worst':
                base_format = 'worst'
            elif video_quality in ['720p', '720']:
                base_format = 'best[height<=720]'
            elif video_quality in ['1080p', '1080']:
                base_format = 'best[height<=1080]'
            elif video_quality in ['480p', '480']:
                base_format = 'best[height<=480]'
            elif video_quality in ['360p', '360']:
                base_format = 'best[height<=360]'
            else:
                # 支持自定义分辨率，如 "720", "1080" 等
                quality_num = video_quality.replace('p', '')  # 移除可能的'p'后缀
                base_format = f'best[height<={quality_num}]'
        else:
            base_format = 'best'

        # 然后处理输出格式，结合视频质量
        if output_format and output_format != 'best':
            format_filter = output_format.lower()
            if format_filter == 'mp4':
                if video_quality == 'best':
                    ydl_opts['format'] = 'bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]'
                elif video_quality == 'worst':
                    ydl_opts['format'] = 'worst[ext=mp4]/worst'
                elif video_quality and video_quality not in ['best', 'worst']:
                    # 结合分辨率和格式：MP4 + 指定分辨率
                    quality_num = video_quality.replace('p', '')  # 移除'p'后缀
                    ydl_opts['format'] = f'bv[ext=mp4][height<={quality_num}]+ba[ext=m4a]/b[ext=mp4][height<={quality_num}]'
                else:
                    ydl_opts['format'] = 'bv[ext=mp4]+ba[ext=m4a]/b[ext=mp4]'
            elif format_filter == 'webm':
                if video_quality == 'best':
                    ydl_opts['format'] = 'bv[ext=webm]+ba[ext=webm]/b[ext=webm]'
                elif video_quality == 'worst':
                    ydl_opts['format'] = 'worst[ext=webm]/worst'
                elif video_quality and video_quality not in ['best', 'worst']:
                    quality_num = video_quality.replace('p', '')
                    ydl_opts['format'] = f'bv[ext=webm][height<={quality_num}]+ba[ext=webm]/b[ext=webm][height<={quality_num}]'
                else:
                    ydl_opts['format'] = 'bv[ext=webm]+ba[ext=webm]/b[ext=webm]'
            elif format_filter == 'mkv':
                if video_quality == 'best':
                    ydl_opts['format'] = 'bv+ba[ext=mkv]/b[ext=mkv]'
                elif video_quality == 'worst':
                    ydl_opts['format'] = 'worst[ext=mkv]/worst'
                elif video_quality and video_quality not in ['best', 'worst']:
                    quality_num = video_quality.replace('p', '')
                    ydl_opts['format'] = f'bv[height<={quality_num}]+ba/b[ext=mkv][height<={quality_num}]'
                else:
                    ydl_opts['format'] = 'bv+ba/b[ext=mkv]'
            elif format_filter in ['mp3', 'aac', 'flac', 'wav']:
                # 音频格式
                ydl_opts['extractaudio'] = True
                ydl_opts['format'] = 'bestaudio'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_filter,
                    'preferredquality': options.get('audio_quality', '192'),
                }]
        else:
            # 没有指定特定格式，使用基础格式
            ydl_opts['format'] = base_format

        if options.get('audio_only'):
            ydl_opts['extractaudio'] = True
            audio_format = options.get('audio_format', 'mp3').lower()
            if audio_format in ['mp3', 'm4a', 'wav', 'flac', 'ogg']:
                ydl_opts['format'] = 'bestaudio'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': audio_format,
                    'preferredquality': options.get('audio_quality', '192'),
                }]
            else:
                ydl_opts['format'] = 'bestaudio'

        if options.get('download_subtitles'):
            ydl_opts['writesubtitles'] = True
            if options.get('subtitle_lang') and options['subtitle_lang'] != 'all':
                ydl_opts['subtitleslangs'] = [options['subtitle_lang']]

        if options.get('download_thumbnail'):
            ydl_opts['writethumbnail'] = True

        if options.get('download_description'):
            ydl_opts['writedescription'] = True

        # 最终调试输出
        logger.info(f"🔧 最终 yt-dlp 配置:")
        logger.info(f"   格式: {ydl_opts.get('format', '未设置')}")
        logger.info(f"   提取音频: {ydl_opts.get('extractaudio', False)}")
        logger.info(f"   后处理器: {ydl_opts.get('postprocessors', [])}")
        logger.info(f"   用户选项: video_quality={video_quality}, output_format={output_format}")

        return ydl_opts

    def _find_downloaded_files(self, download_dir, download_id):
        """查找下载的文件"""
        try:
            print(f"🔍 查找文件开始: download_dir={download_dir}, download_id={download_id}")

            # 获取下载目录中的所有文件
            if not os.path.exists(download_dir):
                print(f"❌ 下载目录不存在: {download_dir}")
                return []

            # 获取下载任务的创建时间
            download_info = self.downloads.get(download_id)
            if not download_info:
                print(f"❌ 找不到下载信息: {download_id}")
                return []

            created_time = download_info['created_at']
            print(f"📅 下载任务创建时间: {created_time}")

            # 列出目录中的所有文件
            all_files = os.listdir(download_dir)
            print(f"📂 目录中所有文件: {all_files}")

            # 查找在下载任务创建后修改的文件
            downloaded_files = []

            # 增加时间容错：允许文件时间比任务创建时间早 30 秒（防止时间精度问题）
            time_tolerance = timedelta(seconds=30)
            earliest_allowed_time = created_time - time_tolerance
            print(f"⏰ 时间容错范围: {earliest_allowed_time} 到现在")

            for filename in all_files:
                file_path = os.path.join(download_dir, filename)
                if os.path.isfile(file_path):
                    # 🔧 修复：使用文件创建时间而不是修改时间
                    file_ctime = datetime.fromtimestamp(os.path.getctime(file_path))  # 创建时间
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))  # 修改时间

                    print(f"📄 文件 {filename}:")
                    print(f"   创建时间={file_ctime}")
                    print(f"   修改时间={file_mtime}")
                    print(f"   任务创建时间={created_time}")
                    print(f"   最早允许时间={earliest_allowed_time}")

                    # 🔧 使用文件创建时间比较（文件什么时候被下载到磁盘）
                    if file_ctime >= earliest_allowed_time:
                        downloaded_files.append(filename)
                        print(f"✅ 文件符合条件（创建时间）: {filename}")
                    else:
                        print(f"❌ 文件不符合条件（创建时间太早）: {filename}")

                    # 额外检查：如果是视频文件格式，优先考虑
                    video_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv', '.m4v']
                    if any(filename.lower().endswith(ext) for ext in video_extensions):
                        print(f"🎬 发现视频文件: {filename}")
                        if filename not in downloaded_files and file_ctime >= earliest_allowed_time:
                            downloaded_files.insert(0, filename)  # 插入到开头，优先处理

            # 🔧 按创建时间排序，最新的在前
            downloaded_files.sort(key=lambda f: os.path.getctime(os.path.join(download_dir, f)), reverse=True)
            print(f"📋 时间比较找到的文件: {downloaded_files}")

            # 🔧 备用策略：如果时间比较没找到文件，选择最新创建的视频文件
            if not downloaded_files:
                print("⚠️ 时间比较没找到文件，使用备用策略：选择最新创建的视频文件")
                video_extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv', '.m4v']

                # 找出所有视频文件
                video_files = []
                for filename in all_files:
                    if any(filename.lower().endswith(ext) for ext in video_extensions):
                        file_path = os.path.join(download_dir, filename)
                        if os.path.isfile(file_path):
                            video_files.append(filename)
                            print(f"🎬 发现视频文件: {filename}")

                if video_files:
                    # 🔧 按创建时间排序，选择最新的
                    video_files.sort(key=lambda f: os.path.getctime(os.path.join(download_dir, f)), reverse=True)
                    downloaded_files = video_files
                    print(f"✅ 备用策略找到视频文件: {downloaded_files}")
                else:
                    # 如果没有视频文件，选择最新创建的任意文件
                    if all_files:
                        all_files.sort(key=lambda f: os.path.getctime(os.path.join(download_dir, f)), reverse=True)
                        downloaded_files = [all_files[0]]  # 只取最新的一个
                        print(f"⚠️ 没有视频文件，选择最新创建的文件: {downloaded_files}")

            print(f"📋 最终找到的文件: {downloaded_files}")
            return downloaded_files

        except Exception as e:
            print(f"❌ 查找下载文件失败: {e}")
            logger.error(f"查找下载文件失败: {e}")
            return []

    def get_file_path(self, download_id):
        """获取下载文件的路径"""
        with self.lock:
            download = self.downloads.get(download_id)
            if download and download.get('file_path'):
                return download['file_path']
            return None

    def list_downloaded_files(self):
        """列出所有已下载的文件 - 直接读取下载目录"""
        files = []
        download_dir = os.environ.get('DOWNLOAD_FOLDER', '/app/downloads')

        if not os.path.exists(download_dir):
            logger.warning(f"下载目录不存在: {download_dir}")
            return files

        try:
            # 直接扫描下载目录中的所有文件
            for filename in os.listdir(download_dir):
                file_path = os.path.join(download_dir, filename)
                if os.path.isfile(file_path):
                    # 获取文件信息
                    stat = os.stat(file_path)

                    # 尝试从内存中获取原始URL信息（如果有的话）
                    original_url = '未知'
                    with self.lock:
                        for download_id, download in self.downloads.items():
                            if download.get('filename') == filename:
                                original_url = download.get('url', '未知')
                                break

                    files.append({
                        'download_id': f'file_{filename}',
                        'filename': filename,
                        'file_size': stat.st_size,
                        'created_at': stat.st_mtime,
                        'download_url': f'/api/download-file/{filename}',
                        'original_url': original_url,
                        'file_path': file_path
                    })

        except Exception as e:
            logger.error(f"扫描下载目录失败: {e}")

        # 按创建时间排序，最新的在前
        files.sort(key=lambda x: x.get('created_at', 0), reverse=True)
        return files

    def _send_telegram_notification(self, download_id: str):
        """发送Telegram通知和文件 - 优化版：只需要 download_id"""
        try:
            print("🔥🔥🔥 === 进入推送函数（优化版） === 🔥🔥🔥")
            print(f"下载ID: {download_id}")
            logger.error(f"🔥🔥🔥 === 进入推送函数（优化版） === 🔥🔥🔥")

            # 🔧 通过 download_id 获取所有需要的信息
            download_info = self.get_download(download_id)
            if not download_info:
                print(f"❌ 找不到下载任务信息: {download_id}")
                logger.error(f"❌ 找不到下载任务信息: {download_id}")
                return

            # 从任务信息中获取所有需要的数据
            original_url = download_info.get('url')
            file_path = download_info.get('file_path')
            filename = download_info.get('filename')
            options = download_info.get('options', {})

            print(f"📋 从任务信息获取:")
            print(f"   原始URL: {original_url}")
            print(f"   文件路径: {file_path}")
            print(f"   文件名: {filename}")
            print(f"   选项: {options}")

            # 验证必要信息
            if not file_path or not filename:
                print(f"❌ 任务信息不完整: file_path={file_path}, filename={filename}")
                logger.error(f"❌ 任务信息不完整: file_path={file_path}, filename={filename}")
                return

            print(f"🔧 开始获取 Telegram 配置...")
            logger.error(f"🔧 开始获取 Telegram 配置...")

            # 获取配置信息 - 修复应用上下文问题
            try:
                from ..models import TelegramConfig

                # 使用传递的应用实例创建上下文
                if self.app:
                    with self.app.app_context():
                        config = TelegramConfig.get_config()
                        print(f"✅ 成功获取 Telegram 配置 (使用应用实例)")
                        logger.error(f"✅ 成功获取 Telegram 配置 (使用应用实例)")
                else:
                    # 回退到环境变量
                    print(f"⚠️ 没有应用实例，使用环境变量配置")
                    logger.warning(f"⚠️ 没有应用实例，使用环境变量配置")

                    # 创建一个简单的配置对象
                    class SimpleConfig:
                        def __init__(self):
                            self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
                            self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
                            self.enabled = bool(self.bot_token and self.chat_id)

                    config = SimpleConfig()
                    print(f"✅ 使用环境变量配置: enabled={config.enabled}")

            except Exception as e:
                print(f"❌ 获取 Telegram 配置失败: {e}")
                logger.error(f"❌ 获取 Telegram 配置失败: {e}")
                return

            # 检查基本配置
            print(f"🔍 检查配置: bot_token={bool(config.bot_token)}, chat_id={bool(config.chat_id)}")
            if not config.bot_token or not config.chat_id:
                print("❌ Telegram 配置不完整，跳过推送")
                logger.warning("❌ Telegram 配置不完整，跳过推送")
                return

            print(f"✅ Telegram 配置完整: bot_token={bool(config.bot_token)}, chat_id={bool(config.chat_id)}")
            logger.info(f"✅ Telegram 配置完整: bot_token={bool(config.bot_token)}, chat_id={bool(config.chat_id)}")

            # 使用与测试推送相同的方案：创建临时通知器实例
            print(f"🔧 创建 TelegramNotifier 实例...")
            try:
                from ..core.telegram_notifier import TelegramNotifier
                telegram_notifier = TelegramNotifier()
                telegram_notifier._bot_token = config.bot_token
                telegram_notifier._chat_id = config.chat_id
                telegram_notifier._enabled = True  # 强制启用，与测试推送一致

                # 重要：设置 API ID 和 API Hash
                if hasattr(config, 'api_id') and config.api_id:
                    telegram_notifier._api_id = config.api_id
                    print(f"✅ 设置 API ID: {config.api_id}")
                if hasattr(config, 'api_hash') and config.api_hash:
                    telegram_notifier._api_hash = config.api_hash
                    print(f"✅ 设置 API Hash: {config.api_hash[:8]}...")

                print(f"✅ TelegramNotifier 实例创建成功")
            except Exception as e:
                print(f"❌ 创建 TelegramNotifier 失败: {e}")
                logger.error(f"❌ 创建 TelegramNotifier 失败: {e}")
                return

            print(f"🤖 使用统一推送方案: bot_token={config.bot_token[:10]}..., chat_id={config.chat_id}")
            logger.info(f"🤖 使用统一推送方案: bot_token={config.bot_token[:10]}..., chat_id={config.chat_id}")

            # 检查是否启用Telegram推送
            telegram_push_enabled = options.get('telegram_push', True)  # 默认启用
            print(f"🔍🔍🔍 Telegram 推送启用状态: {telegram_push_enabled} 🔍🔍🔍")
            print(f"🔍 完整选项: {options}")
            logger.error(f"🔍🔍🔍 Telegram 推送启用状态: {telegram_push_enabled} 🔍🔍🔍")

            if not telegram_push_enabled:
                print(f"❌❌❌ Telegram推送已禁用: {download_id} ❌❌❌")
                logger.error(f"❌❌❌ Telegram推送已禁用: {download_id} ❌❌❌")
                return

            print(f"✅ Telegram推送已启用，继续执行...")

            # 检查推送模式
            push_mode = options.get('telegram_push_mode', 'file')  # file, notification, both
            logger.info(f"推送模式: {push_mode}")

            # 检查文件是否存在
            print(f"🔍 检查文件是否存在: {file_path}")
            if not os.path.exists(file_path):
                print(f"❌❌❌ 文件不存在: {file_path} ❌❌❌")
                logger.error(f"❌ 文件不存在: {file_path}")
                return

            file_size = os.path.getsize(file_path)
            print(f"✅ 文件存在，大小: {file_size / 1024 / 1024:.2f} MB")
            logger.info(f"文件大小: {file_size / 1024 / 1024:.2f} MB")

            if push_mode in ['file', 'both']:
                print(f"📤📤📤 开始发送文件到 Telegram 📤📤📤")
                logger.info("📤 尝试发送文件...")

                # 尝试发送文件
                caption = f"🎬 *下载完成*\n\n"
                caption += f"📁 文件: `{filename}`\n"
                caption += f"🔗 来源: {original_url}\n"
                caption += f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

                print(f"📝 发送文件标题: {caption}")
                print(f"🎯 调用 send_document: file_path={file_path}")

                try:
                    print(f"🚀 开始调用 telegram_notifier.send_document...")
                    success = telegram_notifier.send_document(file_path, caption)
                    print(f"📊📊📊 文件发送结果: {'✅ 成功' if success else '❌ 失败'} 📊📊📊")
                    logger.info(f"文件发送结果: {'成功' if success else '失败'}")
                except Exception as e:
                    print(f"❌❌❌ send_document 调用异常: {e} ❌❌❌")
                    logger.error(f"❌ send_document 调用异常: {e}", exc_info=True)
                    success = False

                # 如果文件发送成功且模式是仅文件，则完成
                if success and push_mode == 'file':
                    logger.info("✅ 文件发送成功，推送完成")
                    return

            if push_mode in ['notification', 'both'] or (push_mode == 'file' and not success):
                logger.info("📢 发送通知消息...")
                # 发送通知（如果文件发送失败也会发送）
                notification_success = telegram_notifier.send_download_notification(file_path, original_url)
                logger.info(f"通知发送结果: {'成功' if notification_success else '失败'}")

            logger.info("=== Telegram 通知发送完成 ===")

        except Exception as e:
            logger.error(f"❌ 发送Telegram通知失败: {e}", exc_info=True)

# 全局实例 - 延迟初始化
_download_manager = None

def get_download_manager(app=None):
    """获取下载管理器实例"""
    global _download_manager
    if _download_manager is None:
        _download_manager = DownloadManager(app)
    elif app and not _download_manager.app:
        # 如果之前没有应用实例，现在设置它
        _download_manager.app = app
    return _download_manager

def initialize_download_manager(app):
    """初始化下载管理器（在应用启动时调用）"""
    global _download_manager
    _download_manager = DownloadManager(app)
    return _download_manager
