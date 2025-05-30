"""
yt-dlp 网页界面的 Flask 应用程序
"""

import os
import threading
import uuid
import re
import tempfile
import logging
from datetime import datetime
from urllib.parse import urlparse
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file, session, redirect, url_for
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from yt_dlp import YoutubeDL
from .file_cleaner import initialize_cleanup_manager, get_cleanup_manager
from .auth import auth_manager, login_required, admin_required, get_current_user

# 设置环境变量以禁用懒加载，避免运行时导入错误
import os
os.environ['YTDLP_NO_LAZY_EXTRACTORS'] = '1'

# 预加载 yt-dlp extractors 以避免运行时导入错误
try:
    from yt_dlp.extractor import import_extractors
    import_extractors()
    logger.info("Successfully preloaded yt-dlp extractors")
except Exception as e:
    logger.warning(f"Failed to preload extractors: {e}")
    # 尝试手动导入一些常用的 extractors
    try:
        from yt_dlp.extractor.youtube import YoutubeIE
        from yt_dlp.extractor.generic import GenericIE
        logger.info("Successfully imported basic extractors")
    except Exception as e2:
        logger.error(f"Failed to import basic extractors: {e2}")


class DownloadManager:
    """管理下载任务及其状态"""

    def __init__(self):
        self.downloads = {}
        self.lock = threading.Lock()

    def add_download(self, download_id, url, options=None):
        """添加新的下载任务"""
        with self.lock:
            self.downloads[download_id] = {
                'id': download_id,
                'url': url,
                'status': 'pending',  # 等待中
                'progress': 0,
                'filename': None,
                'error': None,
                'created_at': datetime.now().isoformat(),
                'options': options or {}
            }
        return download_id

    def update_download(self, download_id, **kwargs):
        """更新下载状态"""
        with self.lock:
            if download_id in self.downloads:
                self.downloads[download_id].update(kwargs)

    def get_download(self, download_id):
        """获取下载状态"""
        with self.lock:
            download = self.downloads.get(download_id)
            if download:
                # 确保所有数据都是 JSON 可序列化的
                return self._make_json_serializable(download.copy())
            return download

    def _make_json_serializable(self, obj):
        """确保对象是 JSON 可序列化的"""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, set):
            return list(obj)  # 将 set 转换为 list
        elif hasattr(obj, '__dict__'):
            return str(obj)  # 将复杂对象转换为字符串
        else:
            return obj

    def get_all_downloads(self):
        """获取所有下载"""
        with self.lock:
            downloads = list(self.downloads.values())
            # 确保所有数据都是 JSON 可序列化的
            return [self._make_json_serializable(download.copy()) for download in downloads]


# 全局下载管理器实例
download_manager = DownloadManager()

# 安全配置
ALLOWED_URL_SCHEMES = ['http', 'https']
BLOCKED_DOMAINS = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
MAX_URL_LENGTH = 2048
MAX_CONCURRENT_DOWNLOADS = 5

def validate_url(url):
    """验证URL的安全性"""
    if not url or len(url) > MAX_URL_LENGTH:
        return False, "URL长度无效"

    try:
        parsed = urlparse(url)

        # 检查协议
        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            return False, "不支持的URL协议"

        # 检查域名
        if parsed.hostname and parsed.hostname.lower() in BLOCKED_DOMAINS:
            return False, "不允许的域名"

        # 检查是否为内网地址
        if parsed.hostname:
            import ipaddress
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.is_private or ip.is_loopback:
                    return False, "不允许访问内网地址"
            except ValueError:
                # 不是IP地址，继续检查
                pass

        return True, "URL有效"
    except Exception as e:
        return False, f"URL解析错误: {str(e)}"

def sanitize_filename(filename):
    """清理文件名，防止路径遍历攻击"""
    if not filename:
        return "download"

    # 使用werkzeug的secure_filename
    safe_name = secure_filename(filename)

    # 额外的安全检查
    safe_name = re.sub(r'[<>:"/\\|?*]', '_', safe_name)
    safe_name = safe_name.strip('. ')

    if not safe_name:
        safe_name = "download"

    return safe_name[:255]  # 限制文件名长度


def create_app(config=None):
    """创建并配置 Flask 应用程序"""
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))

    # 为所有路由启用 CORS
    CORS(app)

    # 配置应用程序
    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-key-change-in-production'),
        'DOWNLOAD_FOLDER': os.environ.get('DOWNLOAD_FOLDER', './downloads'),
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,  # 16MB 最大请求大小
    })

    if config:
        app.config.update(config)

    # 确保下载文件夹存在并设置正确权限
    download_folder = app.config['DOWNLOAD_FOLDER']
    try:
        os.makedirs(download_folder, exist_ok=True)
        logger.info(f"下载目录已创建: {download_folder}")
    except Exception as e:
        logger.warning(f"无法创建下载目录: {e}")

    # 验证下载目录权限
    try:
        # 测试写入权限
        test_file = os.path.join(download_folder, '.write_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            logger.info(f"下载目录权限验证成功: {download_folder}")
        except Exception as e:
            logger.warning(f"下载目录写入权限测试失败: {e}")
            logger.info(f"目录状态: 存在={os.path.exists(download_folder)}, 可读={os.access(download_folder, os.R_OK)}, 可写={os.access(download_folder, os.W_OK)}")

            # 尝试修复权限（仅在有权限时）
            try:
                if hasattr(os, 'getuid'):  # Unix-like 系统
                    current_stat = os.stat(download_folder)
                    if os.getuid() == 0 or os.getuid() == current_stat.st_uid:
                        os.chmod(download_folder, 0o755)
                        logger.info(f"已尝试修复下载目录权限: {download_folder}")
                    else:
                        logger.info(f"无权限修改目录权限，当前用户: {os.getuid()}, 目录所有者: {current_stat.st_uid}")
                else:
                    logger.info("Windows系统，跳过权限修复")
            except Exception as perm_e:
                logger.warning(f"权限修复失败: {perm_e}")

    except Exception as e:
        logger.warning(f"下载目录验证失败: {e}")
        logger.info(f"当前工作目录: {os.getcwd()}")
        if hasattr(os, 'getuid'):
            logger.info(f"用户ID: {os.getuid()}, 组ID: {os.getgid()}")
        else:
            logger.info("Windows系统，无用户ID信息")

    # 初始化文件清理管理器
    cleanup_config = {
        'auto_cleanup_enabled': True,
        'cleanup_interval_hours': 1,      # 每小时检查一次
        'file_retention_hours': 24,       # 文件保留24小时
        'max_storage_mb': 2048,           # 最大存储2GB
        'cleanup_on_download': True,      # 下载完成后立即清理
        'keep_recent_files': 20,          # 至少保留最近20个文件
        'temp_file_retention_minutes': 30, # 临时文件保留30分钟
    }
    initialize_cleanup_manager(app.config['DOWNLOAD_FOLDER'], cleanup_config)

    # 注册路由
    register_routes(app)

    return app


def register_routes(app):
    """注册所有应用程序路由"""

    @app.route('/')
    @login_required
    def index():
        """主网页界面"""
        return render_template('index.html')

    @app.route('/shortcuts-help')
    @login_required
    def shortcuts_help():
        """iOS快捷指令使用指南"""
        return render_template('shortcuts_help.html')

    # 认证相关路由
    @app.route('/login')
    def login():
        """登录页面"""
        return render_template('login.html')

    @app.route('/admin')
    @admin_required
    def admin():
        """管理员控制台"""
        return render_template('admin.html')

    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        """用户登录API"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'error': '需要提供登录数据'}), 400

            username = data.get('username')
            password = data.get('password')
            remember = data.get('remember', False)

            if not username or not password:
                return jsonify({'error': '用户名和密码不能为空'}), 400

            # 验证用户凭据
            if auth_manager.verify_credentials(username, password):
                # 创建会话
                session_token = auth_manager.create_session(username)

                # 保存到Flask session
                session['auth_token'] = session_token
                session['username'] = username

                return jsonify({
                    'success': True,
                    'message': '登录成功',
                    'token': session_token,
                    'username': username
                })
            else:
                return jsonify({'error': '用户名或密码错误'}), 401

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        """用户登出API"""
        try:
            # 获取会话token
            auth_token = request.headers.get('Authorization')
            if auth_token and auth_token.startswith('Bearer '):
                token = auth_token.split(' ')[1]
                auth_manager.destroy_session(token)

            if 'auth_token' in session:
                auth_manager.destroy_session(session['auth_token'])
                session.clear()

            return jsonify({
                'success': True,
                'message': '已成功登出'
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/auth/verify', methods=['GET'])
    def api_verify():
        """验证会话有效性"""
        try:
            # 检查会话token
            auth_token = request.headers.get('Authorization')
            if auth_token and auth_token.startswith('Bearer '):
                token = auth_token.split(' ')[1]
                if auth_manager.verify_session(token):
                    username = auth_manager.get_session_user(token)
                    return jsonify({
                        'valid': True,
                        'username': username
                    })

            # 检查Flask session
            if 'auth_token' in session:
                if auth_manager.verify_session(session['auth_token']):
                    return jsonify({
                        'valid': True,
                        'username': session.get('username')
                    })

            return jsonify({'valid': False}), 401

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/info', methods=['POST'])
    @login_required
    def get_video_info():
        """获取视频信息而不下载"""
        try:
            data = request.get_json()
            if not data or 'url' not in data:
                return jsonify({'error': '需要提供 URL'}), 400

            url = data['url'].strip()

            # 验证URL安全性
            is_valid, error_msg = validate_url(url)
            if not is_valid:
                logger.warning(f"Invalid URL attempted: {url} - {error_msg}")
                return jsonify({'error': f'URL验证失败: {error_msg}'}), 400

            # 配置 yt-dlp 选项，仅用于信息提取
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
            }

            # 合并增强配置
            enhanced_opts = _get_enhanced_ydl_options()
            ydl_opts.update(enhanced_opts)

            # 尝试多种策略获取视频信息
            info = None
            last_error = None

            # 策略1: 使用 Android 客户端
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e:
                last_error = e
                app.logger.warning(f"Android 客户端失败: {str(e)}")

                # 策略2: 使用 TV Embedded 客户端
                try:
                    fallback_opts = ydl_opts.copy()
                    fallback_opts['extractor_args'] = {
                        'youtube': {
                            'player_client': ['tv_embedded'],
                        }
                    }
                    with YoutubeDL(fallback_opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                except Exception as e2:
                    last_error = e2
                    app.logger.warning(f"TV Embedded 客户端失败: {str(e2)}")

                    # 策略3: 最基础配置
                    try:
                        basic_opts = {
                            'quiet': True,
                            'no_warnings': True,
                            'extract_flat': False,
                            'skip_download': True,
                        }
                        with YoutubeDL(basic_opts) as ydl:
                            info = ydl.extract_info(url, download=False)
                    except Exception as e3:
                        last_error = e3
                        app.logger.error(f"所有策略都失败: {str(e3)}")

            if not info:
                raise last_error or Exception("无法获取视频信息")

            # 返回相关信息
            result = {
                'title': info.get('title'),
                'description': info.get('description'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'upload_date': info.get('upload_date'),
                'view_count': info.get('view_count'),
                'thumbnail': info.get('thumbnail'),
                'formats': []
            }

            # 添加格式信息
            if 'formats' in info:
                for fmt in info['formats']:
                    result['formats'].append({
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext'),
                        'quality': fmt.get('quality'),
                        'filesize': fmt.get('filesize'),
                        'format_note': fmt.get('format_note'),
                    })

            return jsonify(result)

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/download', methods=['POST'])
    @login_required
    def start_download():
        """开始视频下载 - 支持高级选项"""
        try:
            data = request.get_json()
            if not data or 'url' not in data:
                return jsonify({'error': '需要提供 URL'}), 400

            url = data['url'].strip()

            # 验证URL安全性
            is_valid, error_msg = validate_url(url)
            if not is_valid:
                logger.warning(f"Invalid URL attempted: {url} - {error_msg}")
                return jsonify({'error': f'URL验证失败: {error_msg}'}), 400

            # 检查并发下载限制
            active_downloads = len([d for d in download_manager.get_all_downloads()
                                  if d['status'] in ['pending', 'downloading']])
            if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
                return jsonify({'error': f'并发下载数量已达上限({MAX_CONCURRENT_DOWNLOADS})'}), 429

            # 生成唯一的下载 ID
            download_id = str(uuid.uuid4())

            # 构建 yt-dlp 选项
            ydl_opts = _build_ydl_options(data, app.config['DOWNLOAD_FOLDER'])

            # 将下载添加到管理器
            download_manager.add_download(download_id, url, ydl_opts)

            # 在后台线程中开始下载
            thread = threading.Thread(target=_download_worker, args=(download_id, url, ydl_opts))
            thread.daemon = True
            thread.start()

            logger.info(f"Started download {download_id} for URL: {url}")
            return jsonify({
                'download_id': download_id,
                'status': 'started',
                'message': '下载已成功开始'
            })

        except Exception as e:
            logger.error(f"Download start error: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/download/<download_id>/status')
    @login_required
    def get_download_status(download_id):
        """获取下载状态"""
        download = download_manager.get_download(download_id)
        if not download:
            return jsonify({'error': '未找到下载'}), 404

        return jsonify(download)

    @app.route('/api/downloads')
    @login_required
    def list_downloads():
        """列出所有下载"""
        downloads = download_manager.get_all_downloads()
        return jsonify({'downloads': downloads})

    @app.route('/api/shortcuts/download', methods=['POST'])
    @login_required
    def shortcuts_download():
        """iOS 快捷指令兼容的下载端点 - 异步模式"""
        try:
            # 处理 JSON 和表单数据
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()

            if not data or 'url' not in data:
                return jsonify({'error': '需要提供 URL'}), 400

            url = data['url']
            audio_only = data.get('audio_only', 'false').lower() == 'true'
            quality = data.get('quality', 'best')

            # 生成唯一的下载 ID
            download_id = str(uuid.uuid4())

            # 为 iOS 快捷指令配置下载选项
            ydl_opts = {
                'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
                'format': 'bestaudio/best' if audio_only else quality,
                'quiet': True,
                'no_warnings': True,
            }

            # 合并增强配置
            enhanced_opts = _get_enhanced_ydl_options()
            ydl_opts.update(enhanced_opts)

            # 将下载添加到管理器
            download_manager.add_download(download_id, url, ydl_opts)

            # 在后台线程中开始下载
            thread = threading.Thread(target=_download_worker, args=(download_id, url, ydl_opts))
            thread.daemon = True
            thread.start()

            # 返回 iOS 快捷指令兼容的响应
            return jsonify({
                'success': True,
                'download_id': download_id,
                'status_url': f'/api/download/{download_id}/status',
                'download_url': f'/api/shortcuts/download/{download_id}/file',
                'message': '下载已成功开始'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/shortcuts/download-direct', methods=['POST'])
    @login_required
    def shortcuts_download_direct():
        """iOS 快捷指令直接下载端点 - 同步模式"""
        try:
            # 处理 JSON 和表单数据
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()

            if not data or 'url' not in data:
                return jsonify({'error': '需要提供 URL'}), 400

            url = data['url']
            audio_only = data.get('audio_only', 'false').lower() == 'true'
            quality = data.get('quality', 'best')

            # 临时文件名
            temp_filename = f"temp_{uuid.uuid4().hex}"
            temp_path = os.path.join(app.config['DOWNLOAD_FOLDER'], temp_filename)

            # 配置下载选项 - 直接下载到临时位置
            ydl_opts = {
                'outtmpl': temp_path + '.%(ext)s',
                'format': 'bestaudio/best' if audio_only else quality,
                'quiet': True,
                'no_warnings': True,
            }

            # 合并增强配置
            enhanced_opts = _get_enhanced_ydl_options()
            ydl_opts.update(enhanced_opts)

            # 直接下载（同步）
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                # 找到下载的文件
                downloaded_file = None
                for file in os.listdir(app.config['DOWNLOAD_FOLDER']):
                    if file.startswith(temp_filename):
                        downloaded_file = file
                        break

                if downloaded_file:
                    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], downloaded_file)

                    # 返回文件内容
                    def remove_file():
                        try:
                            os.remove(file_path)
                        except:
                            pass

                    # 设置适当的Content-Type
                    if audio_only:
                        mimetype = 'audio/mpeg'
                    else:
                        mimetype = 'video/mp4'

                    return send_from_directory(
                        app.config['DOWNLOAD_FOLDER'],
                        downloaded_file,
                        as_attachment=True,
                        download_name=f"{info.get('title', 'video')}.{downloaded_file.split('.')[-1]}",
                        mimetype=mimetype
                    )
                else:
                    return jsonify({'success': False, 'error': '下载失败'}), 500

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/shortcuts/download/<download_id>/file')
    @login_required
    def shortcuts_get_file(download_id):
        """获取iOS快捷指令下载的文件"""
        download = download_manager.get_download(download_id)
        if not download:
            return jsonify({'error': '未找到下载'}), 404

        if download['status'] != 'completed':
            return jsonify({
                'error': '下载未完成',
                'status': download['status'],
                'progress': download.get('progress', 0)
            }), 202

        if 'filename' not in download:
            return jsonify({'error': '文件不存在'}), 404

        filename = download['filename']
        file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)

        if not os.path.exists(file_path):
            return jsonify({'error': '文件已被删除'}), 404

        # 返回文件，适合iOS快捷指令接收
        return send_from_directory(
            app.config['DOWNLOAD_FOLDER'],
            filename,
            as_attachment=True,
            download_name=filename
        )

    @app.route('/api/formats', methods=['POST'])
    @login_required
    def get_available_formats():
        """获取视频可用格式列表 - 用于快捷指令动态选择"""
        try:
            data = request.get_json()
            if not data or 'url' not in data:
                return jsonify({'error': '需要提供 URL'}), 400

            url = data['url']

            # 配置 yt-dlp 选项，仅用于格式提取
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'listformats': True,
                'skip_download': True,
            }

            # 合并增强配置
            enhanced_opts = _get_enhanced_ydl_options()
            ydl_opts.update(enhanced_opts)

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                formats = []
                if 'formats' in info:
                    for f in info['formats']:
                        format_info = {
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'quality': f.get('format_note', ''),
                            'filesize': f.get('filesize'),
                            'vcodec': f.get('vcodec', 'none'),
                            'acodec': f.get('acodec', 'none'),
                            'height': f.get('height'),
                            'width': f.get('width'),
                            'fps': f.get('fps'),
                            'abr': f.get('abr'),  # 音频比特率
                            'vbr': f.get('vbr'),  # 视频比特率
                        }
                        formats.append(format_info)

                # 生成快捷指令友好的格式选项
                shortcut_options = []

                # 视频格式选项
                video_qualities = ['1080', '720', '480', '360']
                for quality in video_qualities:
                    matching_formats = [f for f in formats if f.get('height') == int(quality)]
                    if matching_formats:
                        shortcut_options.append({
                            'title': f'📺 {quality}P视频',
                            'subtitle': f'高度{quality}像素',
                            'value': f'best[height<={quality}]',
                            'type': 'video'
                        })

                # 音频格式选项
                audio_options = [
                    {'title': '🎵 高品质MP3', 'subtitle': '320kbps', 'value': 'mp3_320', 'type': 'audio'},
                    {'title': '🎶 标准MP3', 'subtitle': '192kbps', 'value': 'mp3_192', 'type': 'audio'},
                    {'title': '🔊 AAC音频', 'subtitle': '高效编码', 'value': 'aac', 'type': 'audio'},
                    {'title': '💎 FLAC无损', 'subtitle': '无损压缩', 'value': 'flac', 'type': 'audio'},
                ]
                shortcut_options.extend(audio_options)

                return jsonify({
                    'title': info.get('title', '未知标题'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'formats': formats,
                    'shortcut_options': shortcut_options
                })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/update-check', methods=['GET'])
    @admin_required
    def check_update():
        """检查是否有新版本可用"""
        try:
            import subprocess
            import json

            # 执行更新检查脚本
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'update_yt_dlp.py')
            if not os.path.exists(script_path):
                return jsonify({
                    'update_available': False,
                    'message': '更新脚本不存在',
                    'current_version': _get_current_version(),
                    'latest_version': _get_current_version()
                })

            result = subprocess.run(
                ['python3', script_path, '--check'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                return jsonify({
                    'update_available': False,
                    'message': '已是最新版本',
                    'current_version': _get_current_version(),
                    'latest_version': _get_current_version()
                })
            else:
                return jsonify({
                    'update_available': True,
                    'message': '有新版本可用',
                    'current_version': _get_current_version(),
                    'latest_version': 'checking...'
                })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/update', methods=['POST'])
    @admin_required
    def start_update():
        """开始更新过程"""
        try:
            import subprocess
            import threading

            def update_worker():
                """后台更新工作线程"""
                try:
                    script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'update_yt_dlp.py')
                    if os.path.exists(script_path):
                        subprocess.run(['python3', script_path, '--force'])
                    else:
                        print("更新脚本不存在")
                except Exception as e:
                    print(f"更新失败: {e}")

            # 在后台线程中执行更新
            thread = threading.Thread(target=update_worker)
            thread.daemon = True
            thread.start()

            return jsonify({
                'success': True,
                'message': '更新已开始，请稍后刷新页面查看结果'
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/version', methods=['GET'])
    @admin_required
    def get_version_info():
        """获取版本信息"""
        try:
            current_version = _get_current_version()
            return jsonify({
                'current_version': current_version,
                'web_version': '1.0.0',
                'last_update': _get_last_update_time()
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/shortcuts/download-file/<shortcut_type>')
    def download_shortcut_file(shortcut_type):
        """提供iOS快捷指令文件下载"""
        try:
            # 根据类型生成快捷指令配置
            shortcut_config = _generate_shortcut_config(shortcut_type)

            if not shortcut_config:
                return jsonify({'error': '未知的快捷指令类型'}), 404

            # 创建临时文件
            import tempfile
            import json

            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.shortcut',
                delete=False,
                encoding='utf-8'
            )

            json.dump(shortcut_config, temp_file, ensure_ascii=False, indent=2)
            temp_file.close()

            # 返回文件
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name=f"{shortcut_config['name']}.shortcut",
                mimetype='application/json'
            )

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/cleanup', methods=['POST'])
    @admin_required
    def manual_cleanup():
        """手动触发文件清理"""
        try:
            cleanup_mgr = get_cleanup_manager()
            if not cleanup_mgr:
                return jsonify({'error': '清理管理器未初始化'}), 500

            cleaned_count = cleanup_mgr.cleanup_files()
            storage_info = cleanup_mgr.get_storage_info()

            return jsonify({
                'success': True,
                'cleaned_files': cleaned_count,
                'storage_info': storage_info,
                'message': f'清理完成，删除了 {cleaned_count} 个文件'
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/storage-info', methods=['GET'])
    @admin_required
    def get_storage_info():
        """获取存储信息"""
        try:
            cleanup_mgr = get_cleanup_manager()
            if not cleanup_mgr:
                return jsonify({'error': '清理管理器未初始化'}), 500

            storage_info = cleanup_mgr.get_storage_info()
            return jsonify(storage_info)

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/admin/cleanup-config', methods=['GET', 'POST'])
    @admin_required
    def cleanup_config():
        """获取或更新清理配置"""
        try:
            cleanup_mgr = get_cleanup_manager()
            if not cleanup_mgr:
                return jsonify({'error': '清理管理器未初始化'}), 500

            if request.method == 'GET':
                return jsonify(cleanup_mgr.settings)

            elif request.method == 'POST':
                new_config = request.get_json()
                if not new_config:
                    return jsonify({'error': '需要提供配置数据'}), 400

                cleanup_mgr.update_config(new_config)
                return jsonify({
                    'success': True,
                    'message': '配置已更新',
                    'config': cleanup_mgr.settings
                })

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/downloads/<filename>')
    @login_required
    def download_file(filename):
        """提供下载的文件"""
        return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename)


def _get_enhanced_ydl_options():
    """获取增强的 yt-dlp 配置以绕过 YouTube 检测"""
    return {
        # 反检测配置 - 使用推荐的客户端组合
        'extractor_args': {
            'youtube': {
                # 使用推荐的客户端组合：tv_embedded, mweb, android_vr
                # 根据官方文档，这些客户端目前不需要PO Token
                'player_client': ['tv_embedded', 'mweb', 'android_vr', 'web'],
                'player_skip': ['webpage'],  # 跳过网页解析
                'skip': ['hls'],  # 跳过 HLS 格式以避免某些问题
                'innertube_host': 'www.youtube.com',
                'innertube_key': None,
                'check_formats': None,
            }
        },
        # 通用浏览器用户代理
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        },
        # 网络配置
        'socket_timeout': 60,
        'retries': 5,
        'fragment_retries': 5,
        'retry_sleep_functions': {
            'http': lambda n: min(2 ** n, 30),
            'fragment': lambda n: min(2 ** n, 30),
            'file_access': lambda n: min(2 ** n, 30),
            'extractor': lambda n: min(2 ** n, 30),
        },
        # 其他反检测措施
        'sleep_interval': 0.5,  # 请求间隔
        'max_sleep_interval': 2,
        'sleep_interval_subtitles': 0.5,
        # 格式选择策略
        'format_sort': ['res:720', 'ext:mp4:m4a'],  # 优先选择 720p MP4
        'merge_output_format': 'mp4',  # 合并为 MP4
    }


def _build_ydl_options(data, download_folder):
    """根据前端选项构建 yt-dlp 配置"""

    # 基础配置
    ydl_opts = {
        'outtmpl': os.path.join(download_folder, '%(uploader)s - %(title).150s.%(ext)s'),  # 限制标题长度并添加上传者
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': True,  # 限制文件名字符
        'windowsfilenames': True,  # 确保Windows兼容的文件名
        'writeinfojson': False,  # 默认不写入info json
        'writesubtitles': False,  # 默认不下载字幕
        'writeautomaticsub': False,  # 默认不下载自动字幕
        'writethumbnail': False,  # 默认不下载缩略图
        'max_filesize': 5 * 1024 * 1024 * 1024,  # 5GB 文件大小限制
    }

    # 合并增强配置
    enhanced_opts = _get_enhanced_ydl_options()
    ydl_opts.update(enhanced_opts)

    # 音频/视频选择
    audio_only = data.get('audio_only', False)
    video_quality = data.get('video_quality', 'best')
    audio_quality = data.get('audio_quality', 'best')
    output_format = data.get('output_format', 'best')

    # 构建格式选择器
    if audio_only:
        if audio_quality == 'best':
            ydl_opts['format'] = 'bestaudio/best'
        elif audio_quality == 'worst':
            ydl_opts['format'] = 'worstaudio/worst'
        else:
            # 指定音频比特率
            ydl_opts['format'] = f'bestaudio[abr<={audio_quality}]/bestaudio/best'
    else:
        # 视频下载 - 确保包含音频
        if video_quality == 'best':
            # 优先选择包含音频的最佳格式，如果没有则分别下载后合并
            ydl_opts['format'] = 'best[vcodec!=none][acodec!=none]/bestvideo[height<=1080]+bestaudio/best'
        elif video_quality == 'worst':
            ydl_opts['format'] = 'worst[vcodec!=none][acodec!=none]/worstvideo+worstaudio/worst'
        else:
            # 指定视频分辨率，确保包含音频
            ydl_opts['format'] = f'best[height<={video_quality}][vcodec!=none][acodec!=none]/bestvideo[height<={video_quality}]+bestaudio/best[height<={video_quality}]'

    # 输出格式转换
    if output_format != 'best' and output_format != 'auto':
        if output_format in ['mp3', 'aac', 'flac', 'wav']:
            # 音频格式
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': output_format,
                'preferredquality': audio_quality if audio_quality.isdigit() else '192',
            }]
        elif output_format in ['mp4', 'webm', 'mkv']:
            # 视频格式
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': output_format,
            }]

    # 字幕下载
    if data.get('download_subtitles', False):
        ydl_opts['writesubtitles'] = True
        ydl_opts['writeautomaticsub'] = True

        subtitle_lang = data.get('subtitle_lang', 'all')
        if subtitle_lang != 'all':
            ydl_opts['subtitleslangs'] = [subtitle_lang]

    # 缩略图下载
    if data.get('download_thumbnail', False):
        ydl_opts['writethumbnail'] = True

    # 描述下载
    if data.get('download_description', False):
        ydl_opts['writedescription'] = True
        ydl_opts['writeinfojson'] = True

    # 播放列表处理
    if data.get('download_playlist', False):
        ydl_opts['noplaylist'] = False
    else:
        ydl_opts['noplaylist'] = True

    return ydl_opts


def _get_current_version():
    """获取当前yt-dlp版本"""
    try:
        from yt_dlp.version import __version__
        return __version__
    except ImportError:
        try:
            import yt_dlp
            return yt_dlp.version.__version__
        except:
            return "unknown"


def _get_last_update_time():
    """获取最后更新时间"""
    try:
        import os
        import time

        # 检查version.py文件的修改时间
        version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'yt_dlp', 'version.py')
        if os.path.exists(version_file):
            mtime = os.path.getmtime(version_file)
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        return "unknown"
    except Exception:
        return "unknown"


def _generate_shortcut_config(shortcut_type):
    """生成iOS快捷指令配置"""

    # 获取当前服务器地址（这里使用占位符，前端会替换）
    server_url = "http://YOUR_SERVER_IP:8080"

    shortcuts = {
        'smart_downloader': {
            'name': '智能视频下载器',
            'description': '支持格式选择的交互式下载器',
            'actions': [
                {
                    'type': 'get_clipboard',
                    'description': '获取剪贴板中的视频链接'
                },
                {
                    'type': 'choose_from_menu',
                    'prompt': '选择下载格式',
                    'options': [
                        '🎬 最佳质量视频',
                        '📱 720P视频',
                        '💾 480P视频',
                        '🎵 高品质MP3',
                        '🎶 标准MP3'
                    ]
                },
                {
                    'type': 'text_replace_multiple',
                    'replacements': [
                        {'find': '🎬 最佳质量视频', 'replace': 'video_best'},
                        {'find': '📱 720P视频', 'replace': 'video_720'},
                        {'find': '💾 480P视频', 'replace': 'video_480'},
                        {'find': '🎵 高品质MP3', 'replace': 'audio_320'},
                        {'find': '🎶 标准MP3', 'replace': 'audio_192'}
                    ]
                },
                {
                    'type': 'conditional_download',
                    'video_url': f'{server_url}/api/shortcuts/download-direct',
                    'audio_url': f'{server_url}/api/shortcuts/download-direct'
                }
            ]
        },
        'audio_extractor': {
            'name': '音频提取器',
            'description': '一键提取视频音频为MP3',
            'actions': [
                {
                    'type': 'get_clipboard'
                },
                {
                    'type': 'download_audio',
                    'url': f'{server_url}/api/shortcuts/download-direct',
                    'params': {
                        'audio_only': 'true',
                        'audio_quality': '320',
                        'output_format': 'mp3'
                    }
                }
            ]
        },
        '720p_downloader': {
            'name': '720P下载器',
            'description': '专门下载720P高清视频',
            'actions': [
                {
                    'type': 'get_clipboard'
                },
                {
                    'type': 'download_video',
                    'url': f'{server_url}/api/shortcuts/download-direct',
                    'params': {
                        'audio_only': 'false',
                        'video_quality': 'best[height<=720]',
                        'output_format': 'mp4'
                    }
                }
            ]
        },
        'batch_downloader': {
            'name': '批量下载器',
            'description': '支持多个视频批量下载',
            'actions': [
                {
                    'type': 'ask_for_input',
                    'prompt': '请输入视频链接（每行一个）',
                    'input_type': 'text'
                },
                {
                    'type': 'split_text',
                    'separator': '\\n'
                },
                {
                    'type': 'repeat_for_each',
                    'download_url': f'{server_url}/api/shortcuts/download-direct'
                }
            ]
        }
    }

    return shortcuts.get(shortcut_type)


def _download_worker(download_id, url, ydl_opts):
    """用于下载视频的后台工作线程"""
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            download_manager.update_download(download_id, status='downloading')

            # 添加进度钩子
            def progress_hook(d):
                # 清理进度数据，确保 JSON 可序列化
                cleaned_d = download_manager._make_json_serializable(d)

                if cleaned_d['status'] == 'downloading':
                    # 更新进度信息
                    update_data = {}

                    if 'total_bytes' in cleaned_d and cleaned_d['total_bytes']:
                        progress = (cleaned_d['downloaded_bytes'] / cleaned_d['total_bytes']) * 100
                        update_data['progress'] = progress
                        update_data['total_bytes'] = cleaned_d['total_bytes']
                    elif 'total_bytes_estimate' in cleaned_d and cleaned_d['total_bytes_estimate']:
                        progress = (cleaned_d['downloaded_bytes'] / cleaned_d['total_bytes_estimate']) * 100
                        update_data['progress'] = progress
                        update_data['total_bytes'] = cleaned_d['total_bytes_estimate']

                    if 'speed' in cleaned_d and cleaned_d['speed']:
                        update_data['speed'] = cleaned_d['speed']

                    if 'eta' in cleaned_d and cleaned_d['eta']:
                        update_data['eta'] = cleaned_d['eta']

                    download_manager.update_download(download_id, **update_data)

                elif cleaned_d['status'] == 'finished':
                    filename = os.path.basename(cleaned_d['filename'])
                    download_manager.update_download(
                        download_id,
                        status='completed',
                        progress=100,
                        filename=filename
                    )

                    # 下载完成后触发清理
                    cleanup_mgr = get_cleanup_manager()
                    if cleanup_mgr:
                        cleanup_mgr.cleanup_on_download_complete(filename)

            ydl_opts['progress_hooks'] = [progress_hook]

            # 尝试多种策略下载
            success = False
            last_error = None

            # 策略1: 使用当前配置
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                success = True
            except Exception as e:
                last_error = e
                logger.warning(f"下载策略1失败 (尝试 {retry_count + 1}/{max_retries}): {str(e)}")

                # 策略2: 使用TV Embedded客户端
                if not success and 'youtube.com' in url:
                    try:
                        fallback_opts = ydl_opts.copy()
                        fallback_opts['extractor_args'] = {
                            'youtube': {
                                'player_client': ['tv_embedded'],
                            }
                        }
                        with YoutubeDL(fallback_opts) as ydl:
                            ydl.download([url])
                        success = True
                    except Exception as e2:
                        last_error = e2
                        logger.warning(f"下载策略2失败 (尝试 {retry_count + 1}/{max_retries}): {str(e2)}")

                # 策略3: 基础配置
                if not success:
                    try:
                        basic_opts = {
                            'outtmpl': ydl_opts['outtmpl'],
                            'format': 'best',
                            'quiet': True,
                            'no_warnings': True,
                        }
                        with YoutubeDL(basic_opts) as ydl:
                            ydl.download([url])
                        success = True
                    except Exception as e3:
                        last_error = e3
                        logger.warning(f"下载策略3失败 (尝试 {retry_count + 1}/{max_retries}): {str(e3)}")

            if success:
                break

            retry_count += 1
            if retry_count < max_retries:
                import time
                time.sleep(2 ** retry_count)  # 指数退避

        except Exception as e:
            last_error = e
            retry_count += 1
            logger.error(f"下载工作线程异常 (尝试 {retry_count}/{max_retries}): {str(e)}")

            if retry_count < max_retries:
                import time
                time.sleep(2 ** retry_count)

    # 所有重试都失败了
    if retry_count >= max_retries:
        download_manager.update_download(
            download_id,
            status='error',
            error=f"下载失败，已重试{max_retries}次: {str(last_error) if last_error else '未知错误'}"
        )


# 为 gunicorn 创建应用实例
app = None

def get_app():
    """获取或创建 Flask 应用实例"""
    global app
    if app is None:
        config = {
            'DOWNLOAD_FOLDER': os.environ.get('DOWNLOAD_FOLDER', '/app/downloads'),
            'DEBUG': False,
        }
        app = create_app(config)
    return app

# 为 gunicorn 暴露应用实例
app = get_app()
