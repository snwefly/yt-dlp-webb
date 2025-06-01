# -*- coding: utf-8 -*-
"""
下载管理器 - 完整版本
"""

import uuid
import threading
import logging
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import yt_dlp

logger = logging.getLogger(__name__)

class DownloadManager:
    """下载管理器"""

    def __init__(self):
        self.downloads = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=3)  # 最多3个并发下载

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

            # 构建yt-dlp选项
            ydl_opts = self._build_ytdlp_options(download_id, download_dir, options)

            # 创建下载器并执行下载
            logger.info(f"📥 开始下载: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # 下载完成，查找下载的文件
            downloaded_files = self._find_downloaded_files(download_dir, download_id)
            if downloaded_files:
                main_file = downloaded_files[0]  # 主文件
                file_path = os.path.join(download_dir, main_file)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

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
            else:
                # 没有找到文件，可能下载失败
                self.update_download(download_id,
                    status='completed',
                    progress=100,
                    completed_at=datetime.now(),
                    error='下载完成但未找到文件'
                )
                logger.warning(f"⚠️ 下载完成但未找到文件: {download_id}")

        except Exception as e:
            logger.error(f"❌ 下载失败 {download_id}: {e}")
            self.update_download(download_id,
                status='failed',
                error=str(e),
                failed_at=datetime.now()
            )

    def _build_ytdlp_options(self, download_id, download_dir, options):
        """构建yt-dlp下载选项 - 基于最新源代码优化以避免bot检测"""
        # 基础配置
        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            # 网络配置
            'socket_timeout': 30,
            'retries': 3,
            'fragment_retries': 3,
            # 错误处理
            'ignoreerrors': False,
            'no_warnings': False,
        }

        # Cookies处理 - 优先使用YouTube cookies文件
        cookies_set = False
        cookies_file = os.path.abspath('webapp/config/youtube_cookies.txt')

        # 1. 优先使用YouTube cookies文件（已验证有效）
        if os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
            logger.info(f"🍪 使用YouTube cookies文件: {cookies_file}")
            cookies_set = True

            # 验证cookies文件内容
            try:
                with open(cookies_file, 'r') as f:
                    content = f.read()
                    if 'youtube.com' in content and len(content) > 100:
                        logger.info("✅ Cookies文件内容验证通过")
                    else:
                        logger.warning("⚠️ Cookies文件内容可能不完整")
            except Exception as e:
                logger.warning(f"⚠️ 读取cookies文件失败: {e}")
        else:
            logger.warning(f"⚠️ YouTube cookies文件不存在: {cookies_file}")

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
        if options.get('video_quality'):
            if options['video_quality'] == 'best':
                ydl_opts['format'] = 'best'
            elif options['video_quality'] == 'worst':
                ydl_opts['format'] = 'worst'
            elif options['video_quality'] == '720p':
                ydl_opts['format'] = 'best[height<=720]'
            elif options['video_quality'] == '1080p':
                ydl_opts['format'] = 'best[height<=1080]'
            elif options['video_quality'] == '480p':
                ydl_opts['format'] = 'best[height<=480]'
            elif options['video_quality'] == '360p':
                ydl_opts['format'] = 'best[height<=360]'
            else:
                # 支持自定义分辨率，如 "720", "1080" 等
                ydl_opts['format'] = f'best[height<={options["video_quality"]}]'

        # 格式选择 - 支持MP4等特定格式
        output_format = options.get('output_format', 'best')
        if output_format and output_format != 'best':
            format_filter = output_format.lower()
            if format_filter == 'mp4':
                if options.get('video_quality') and options['video_quality'] not in ['best', 'worst']:
                    # 结合分辨率和格式：MP4 + 指定分辨率
                    quality = options['video_quality'].replace('p', '')  # 移除'p'后缀
                    ydl_opts['format'] = f'best[ext=mp4][height<={quality}]'
                else:
                    ydl_opts['format'] = 'best[ext=mp4]'
            elif format_filter == 'webm':
                if options.get('video_quality') and options['video_quality'] not in ['best', 'worst']:
                    quality = options['video_quality'].replace('p', '')
                    ydl_opts['format'] = f'best[ext=webm][height<={quality}]'
                else:
                    ydl_opts['format'] = 'best[ext=webm]'
            elif format_filter == 'mkv':
                if options.get('video_quality') and options['video_quality'] not in ['best', 'worst']:
                    quality = options['video_quality'].replace('p', '')
                    ydl_opts['format'] = f'best[ext=mkv][height<={quality}]'
                else:
                    ydl_opts['format'] = 'best[ext=mkv]'
            elif format_filter in ['mp3', 'aac', 'flac', 'wav']:
                # 音频格式
                ydl_opts['extractaudio'] = True
                ydl_opts['format'] = 'bestaudio'
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_filter,
                    'preferredquality': options.get('audio_quality', '192'),
                }]

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

        return ydl_opts

    def _find_downloaded_files(self, download_dir, download_id):
        """查找下载的文件"""
        try:
            # 获取下载目录中的所有文件
            if not os.path.exists(download_dir):
                return []

            # 获取下载任务的创建时间
            download_info = self.downloads.get(download_id)
            if not download_info:
                return []

            created_time = download_info['created_at']

            # 查找在下载任务创建后修改的文件
            downloaded_files = []
            for filename in os.listdir(download_dir):
                file_path = os.path.join(download_dir, filename)
                if os.path.isfile(file_path):
                    # 检查文件修改时间
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime >= created_time:
                        downloaded_files.append(filename)

            # 按修改时间排序，最新的在前
            downloaded_files.sort(key=lambda f: os.path.getmtime(os.path.join(download_dir, f)), reverse=True)

            return downloaded_files

        except Exception as e:
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
        """列出所有已下载的文件"""
        files = []
        with self.lock:
            for download_id, download in self.downloads.items():
                if download.get('status') == 'completed' and download.get('file_path'):
                    files.append({
                        'download_id': download_id,
                        'filename': download.get('filename'),
                        'file_size': download.get('file_size', 0),
                        'created_at': download.get('created_at'),
                        'download_url': download.get('download_url'),
                        'original_url': download.get('url')
                    })

        # 按创建时间排序，最新的在前
        files.sort(key=lambda x: x['created_at'], reverse=True)
        return files

# 全局实例
_download_manager = DownloadManager()

def get_download_manager():
    """获取下载管理器实例"""
    return _download_manager
