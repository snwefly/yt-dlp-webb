import sys
import os
# Remove the project root from sys.path to avoid conflict with local yt_dlp directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root in sys.path:
    sys.path.remove(project_root)

"""
yt-dlp 网页界面的 Flask 应用程序
此 app.py 文件应位于项目根目录下的 web/ 文件夹中。
"""

import os
import sys 
import threading
import uuid
import re
import tempfile
import logging
import json
import random # Added for session cleanup
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file, session, redirect, url_for, current_app, after_this_request
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 确保从 site-packages 加载 yt_dlp (这是第三方库)
from yt_dlp import YoutubeDL
# 相对导入，因为这些文件与 app.py 在同一个 'web' 包内
from .file_cleaner import initialize_cleanup_manager, get_cleanup_manager
from .auth import auth_manager, login_required, admin_required, get_current_user

# 配置日志
logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)] 
)
logger = logging.getLogger(__name__)


# --- 辅助函数：递归转换 set 和其他非JSON原生类型为 list/str ---
def _make_json_serializable_recursive(obj):
    if isinstance(obj, dict):
        return {k: _make_json_serializable_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_serializable_recursive(elem) for elem in obj]
    elif isinstance(obj, set):
        return list(obj) 
    elif isinstance(obj, datetime): 
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID): 
        return str(obj)
    return obj

class DownloadManager:
    """管理下载任务及其状态"""
    def __init__(self):
        self.downloads = {}
        self.lock = threading.Lock() 

    def add_download(self, download_id, url, options=None):
        """添加新的下载任务，确保选项是可序列化的"""
        with self.lock:
            serializable_options = _make_json_serializable_recursive(options or {})
            self.downloads[download_id] = {
                'id': download_id,
                'url': url,
                'status': 'pending',
                'progress': 0.0,
                'filename': None,
                'error': None,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'options': serializable_options,
                'speed': None, 
                'eta': None, 
                'total_bytes': None,
                'downloaded_bytes': None,
                'elapsed': None,
                'start_time': None,
                'end_time': None,
            }
            logger.info(f"下载任务 {download_id} 已添加 URL: {url}")
        return download_id

    def update_download(self, download_id, **kwargs):
        """更新下载状态，确保传入的kwargs值是可序列化的"""
        with self.lock:
            if download_id in self.downloads:
                update_data = _make_json_serializable_recursive(kwargs)
                self.downloads[download_id].update(update_data)
            else:
                logger.warning(f"尝试更新不存在的下载ID: {download_id}")

    def get_download(self, download_id):
        """获取下载状态的副本"""
        with self.lock:
            download_item = self.downloads.get(download_id)
            return _make_json_serializable_recursive(download_item.copy()) if download_item else None

    def get_all_downloads(self):
        """获取所有下载状态的副本列表"""
        with self.lock:
            sorted_downloads = sorted(self.downloads.values(), key=lambda x: x.get('created_at', ''), reverse=True)
            return [_make_json_serializable_recursive(item.copy()) for item in sorted_downloads]

download_manager = DownloadManager()

ALLOWED_URL_SCHEMES = ['http', 'https']
BLOCKED_HOST_PATTERNS = [
    re.compile(r"^(localhost|127\.\d{1,3}\.\d{1,3}\.\d{1,3}|0\.0\.0\.0|\[::1\])$", re.IGNORECASE),
    re.compile(r"^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"^172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"^192\.168\.\d{1,3}\.\d{1,3}$"),
    re.compile(r"^169\.254\.\d{1,3}\.\d{1,3}$"),
]
MAX_URL_LENGTH = int(os.environ.get('MAX_URL_LENGTH', 2048))
MAX_CONCURRENT_DOWNLOADS = int(os.environ.get('MAX_CONCURRENT_DOWNLOADS', 5))

def validate_url(url):
    if not url or len(url) > MAX_URL_LENGTH:
        return False, "URL长度无效或过长"
    try:
        decoded_url = unquote(url)
        parsed = urlparse(decoded_url)
        if parsed.scheme not in ALLOWED_URL_SCHEMES:
            return False, "不支持的URL协议"
        if not parsed.hostname: 
            return False, "URL必须包含有效的主机名"
        for pattern in BLOCKED_HOST_PATTERNS:
            if pattern.match(parsed.hostname):
                return False, f"不允许访问域名或IP地址: {parsed.hostname}"
        import socket
        try:
            ip_addr_str = socket.gethostbyname(parsed.hostname)
            import ipaddress
            ip_obj = ipaddress.ip_address(ip_addr_str)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_unspecified:
                return False, f"域名解析到不允许的IP地址: {parsed.hostname} -> {ip_addr_str}"
        except socket.gaierror:
            logger.warning(f"域名无法解析: {parsed.hostname}")
            return False, f"域名无法解析: {parsed.hostname}"
        except ValueError:
             logger.warning(f"域名解析结果不是有效IP: {parsed.hostname}")
             return False, f"域名解析结果不是有效IP: {parsed.hostname}"
        return True, "URL有效"
    except Exception as e:
        logger.error(f"URL验证时发生未知错误: {url}, 错误: {e}", exc_info=True)
        return False, "URL解析或验证时发生内部错误"

def sanitize_filename(filename):
    if not filename: return "download_" + uuid.uuid4().hex[:8] 
    safe_name = secure_filename(filename) 
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', '_', safe_name) 
    safe_name = re.sub(r'[_ ]{2,}', '_', safe_name) 
    safe_name = safe_name.strip('. _') 
    if not safe_name: safe_name = "download_" + uuid.uuid4().hex[:8]
    return safe_name[:180]

def create_app(config=None):
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
    CORS(app, supports_credentials=True, resources={r"/api/*": {"origins": "*"}}) 
    
    default_download_folder = os.path.abspath(os.path.join(os.path.dirname(app.root_path), 'downloads'))

    app.config.update({
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'change-this-in-production-to-a-very-long-random-string!'),
        'DOWNLOAD_FOLDER': os.environ.get('DOWNLOAD_FOLDER', default_download_folder),
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,
        'SESSION_COOKIE_SECURE': not app.debug and os.environ.get('FLASK_ENV', 'development') == 'production',
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
    })
    
    if config: app.config.update(config)
    try:
        os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
        logger.info(f"下载目录: {app.config['DOWNLOAD_FOLDER']}")
    except OSError as e:
        logger.critical(f"创建下载目录失败 {app.config['DOWNLOAD_FOLDER']}: {e}", exc_info=True)
        raise RuntimeError(f"无法创建下载目录: {e}") from e
    
    auth_manager.init_app(app)

    # Periodic cleanup of expired sessions
    @app.before_request
    def cleanup_sessions_hook():
        # Run cleanup with a 1% probability on each request
        # Adjust probability as needed for your application's load
        if random.random() < 0.01: 
            num_cleaned = auth_manager.cleanup_expired_sessions()
            if num_cleaned > 0:
                logger.info(f"Cleaned up {num_cleaned} expired user sessions.")
                
    cleanup_config = {
        'auto_cleanup_enabled': os.environ.get('AUTO_CLEANUP_ENABLED', 'True').lower() == 'true',
        'cleanup_interval_hours': int(os.environ.get('CLEANUP_INTERVAL_HOURS', 1)),
        'file_retention_hours': int(os.environ.get('FILE_RETENTION_HOURS', 24)),
        'max_storage_mb': int(os.environ.get('MAX_STORAGE_MB', 2048)),
        'cleanup_on_download': os.environ.get('CLEANUP_ON_DOWNLOAD', 'True').lower() == 'true',
        'keep_recent_files': int(os.environ.get('KEEP_RECENT_FILES', 20)),
        'temp_file_retention_minutes': int(os.environ.get('TEMP_FILE_RETENTION_MINUTES', 30)),
    }
    initialize_cleanup_manager(app.config['DOWNLOAD_FOLDER'], cleanup_config)
    register_routes(app)

    # --- Custom Error Handlers ---
    @app.errorhandler(400)
    def bad_request_error(error):
        logger.warning(f"Bad Request (400): {error.description if hasattr(error, 'description') else str(error)}")
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        logger.warning(f"Unauthorized (401): {error.description if hasattr(error, 'description') else str(error)}")
        return render_template('errors/401.html', error=error), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        logger.warning(f"Forbidden (403): {error.description if hasattr(error, 'description') else str(error)}")
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found_error(error):
        logger.info(f"Not Found (404): {request.path} - {error.description if hasattr(error, 'description') else str(error)}")
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error(f"Internal Server Error (500): {error}", exc_info=True) # Log full exception
        return render_template('errors/500.html', error=error), 500
        
    # General exception handler for any unhandled exception
    # This is a fallback, specific 500 errors should ideally be caught by the above.
    @app.errorhandler(Exception)
    def unhandled_exception(error):
        logger.critical(f"Unhandled Exception: {error}", exc_info=True)
        # Avoid leaking details, render a generic 500 page
        return render_template('errors/500.html', error="An unexpected error occurred."), 500

    logger.info("Flask app 创建并配置完成。")
    return app

def register_routes(app):
    @app.route('/')
    def index(): return render_template('index.html')
    @app.route('/shortcuts-help')
    def shortcuts_help(): return render_template('shortcuts_help.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if get_current_user(): return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            if not username or not password: return render_template('login.html', error='用户名和密码不能为空')
            if auth_manager.verify_credentials(username, password):
                session_token = auth_manager.create_session(username)
                session['auth_token'], session['username'] = session_token, username
                logger.info(f"用户 {username} 通过表单登录成功。")
                return redirect(url_for('index'))
            else:
                logger.warning(f"用户 {username} 表单登录失败。")
                return render_template('login.html', error='用户名或密码错误')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout_route():
        user = get_current_user()
        auth_token = session.pop('auth_token', None)
        session.pop('username', None)
        if auth_token: auth_manager.destroy_session(auth_token)
        logger.info(f"用户 {user or '(unknown)'} 已登出。")
        return redirect(url_for('login'))

    @app.route('/admin')
    @admin_required
    def admin(): return render_template('admin.html')

    @app.route('/api/auth/login', methods=['POST'])
    def api_login():
        try:
            data = request.get_json()
            if not data: return jsonify({'error': '需要提供登录数据'}), 400
            username, password = data.get('username'), data.get('password')
            if not username or not password: return jsonify({'error': '用户名和密码不能为空'}), 400
            if auth_manager.verify_credentials(username, password):
                session_token = auth_manager.create_session(username)
                session['auth_token'], session['username'] = session_token, username
                logger.info(f"用户 {username} 通过 API 登录成功。")
                return jsonify({'success': True, 'message': '登录成功', 'token': session_token, 'username': username})
            else:
                logger.warning(f"用户 {username} API 登录失败。")
                return jsonify({'error': '用户名或密码错误'}), 401
        except Exception as e:
            logger.error(f"API登录时发生错误: {e}", exc_info=True)
            return jsonify({'error': '服务器内部错误'}), 500

    @app.route('/api/auth/logout', methods=['POST'])
    def api_logout():
        try:
            token_to_destroy, user_id = None, "User (token/session not found)"
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '): token_to_destroy = auth_header.split(' ')[1]
            elif 'auth_token' in session: token_to_destroy = session['auth_token']
            if token_to_destroy:
                user_id = auth_manager.get_session_user(token_to_destroy) or user_id
                auth_manager.destroy_session(token_to_destroy)
            session.pop('auth_token', None); session.pop('username', None)
            logger.info(f"{user_id} 通过 API 登出。")
            return jsonify({'success': True, 'message': '已成功登出'})
        except Exception as e:
            logger.error(f"API登出时发生错误: {e}", exc_info=True)
            return jsonify({'error': '服务器内部错误'}), 500

    @app.route('/api/auth/verify', methods=['GET'])
    def api_verify():
        try:
            token_to_verify, is_from_header = None, False
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token_to_verify, is_from_header = auth_header.split(' ')[1], True
            elif 'auth_token' in session: token_to_verify = session['auth_token']
            if token_to_verify and auth_manager.verify_session(token_to_verify):
                username = auth_manager.get_session_user(token_to_verify)
                if username:
                    if is_from_header and (not session.get('auth_token') or session.get('username') != username):
                        session['auth_token'], session['username'] = token_to_verify, username
                    return jsonify({'valid': True, 'username': username})
            session.pop('auth_token', None); session.pop('username', None) 
            return jsonify({'valid': False, 'message': '会话无效或已过期'}), 401
        except Exception as e:
            logger.error(f"API验证会话时发生错误: {e}", exc_info=True)
            return jsonify({'error': '服务器内部错误'}), 500

    @app.route('/api/info', methods=['POST'])
    @login_required
    def get_video_info():
        url_param = None
        try:
            data = request.get_json()
            if not data or 'url' not in data: return jsonify({'error': '需要提供 URL'}), 400
            url_param = data['url'].strip()
            is_valid, error_msg = validate_url(url_param)
            if not is_valid:
                logger.warning(f"无效的URL尝试获取信息: {url_param} - {error_msg}")
                return jsonify({'error': f'URL验证失败: {error_msg}'}), 400
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': 'in_playlist', 'skip_download': True}
            with YoutubeDL(ydl_opts) as ydl: info = ydl.extract_info(url_param, download=False)
            
            display_info = info.get('entries')[0] if info.get('_type') == 'playlist' and info.get('entries') else info
            if not display_info: display_info = info

            result = {
                'title': display_info.get('title'), 'description': display_info.get('description'),
                'duration': display_info.get('duration_string') or display_info.get('duration'),
                'uploader': display_info.get('uploader'), 'upload_date': display_info.get('upload_date'),
                'view_count': display_info.get('view_count'),
                'thumbnail': display_info.get('thumbnail') or (display_info.get('thumbnails')[-1]['url'] if display_info.get('thumbnails') else None),
                'formats': [],
                'is_playlist': info.get('_type') == 'playlist',
                'playlist_title': info.get('title') if info.get('_type') == 'playlist' else None,
                'playlist_count': info.get('playlist_count') if info.get('_type') == 'playlist' else None,
            }
            if 'formats' in display_info and display_info['formats'] is not None:
                for fmt in display_info['formats']:
                    if not isinstance(fmt, dict): continue
                    result['formats'].append({
                        'format_id': fmt.get('format_id'), 'ext': fmt.get('ext'),
                        'quality_note': fmt.get('format_note'),
                        'filesize': fmt.get('filesize') or fmt.get('filesize_approx'),
                        'resolution': fmt.get('resolution') or (f"{fmt.get('width')}x{fmt.get('height')}" if fmt.get('width') and fmt.get('height') else None),
                        'vcodec': fmt.get('vcodec'), 'acodec': fmt.get('acodec'),
                        'fps': fmt.get('fps'), 'abr': fmt.get('abr'), 'vbr': fmt.get('vbr'),
                    })
            return jsonify(_make_json_serializable_recursive(result))
        except Exception as e:
            logger.error(f"获取视频信息时发生错误: URL='{url_param}', 错误: {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '获取视频信息时发生内部错误'}), 500

    @app.route('/api/download', methods=['POST'])
    @login_required
    def start_download():
        url_param = None
        try:
            data = request.get_json()
            if not data or 'url' not in data: return jsonify({'error': '需要提供 URL'}), 400
            url_param = data['url'].strip()
            is_valid, error_msg = validate_url(url_param)
            if not is_valid:
                logger.warning(f"无效的URL尝试下载: {url_param} - {error_msg}")
                return jsonify({'error': f'URL验证失败: {error_msg}'}), 400
            with download_manager.lock:
                active_downloads = len([d for d in download_manager.get_all_downloads() if d['status'] in ['pending', 'downloading']])
            if active_downloads >= MAX_CONCURRENT_DOWNLOADS:
                return jsonify({'error': f'并发下载数量已达上限({MAX_CONCURRENT_DOWNLOADS})'}), 429
            download_id = str(uuid.uuid4())
            ydl_opts = _build_ydl_options(data, current_app.config['DOWNLOAD_FOLDER'])
            download_manager.add_download(download_id, url_param, ydl_opts)
            thread = threading.Thread(target=_download_worker, args=(download_id, url_param, ydl_opts))
            thread.daemon = True
            thread.start()
            logger.info(f"已开始下载 {download_id} URL: {url_param}")
            return jsonify({'download_id': download_id, 'status': 'started', 'message': '下载已成功开始'})
        except Exception as e:
            logger.error(f"开始下载时发生错误: URL='{url_param}', {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '开始下载时发生内部错误'}), 500

    @app.route('/api/download/<download_id>/status')
    @login_required 
    def get_download_status(download_id):
        download_info = download_manager.get_download(download_id) 
        if not download_info:
            return jsonify({'error': '未找到下载'}), 404
        return jsonify(_make_json_serializable_recursive(download_info))

    @app.route('/api/downloads')
    @login_required
    def list_downloads():
        downloads = download_manager.get_all_downloads()
        return jsonify({'downloads': [_make_json_serializable_recursive(d) for d in downloads]})

    @app.route('/api/shortcuts/download', methods=['POST'])
    def shortcuts_download():
        url_param = None
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            if not data or 'url' not in data: return jsonify({'error': '需要提供 URL'}), 400
            url_param = data['url'].strip()
            is_valid, error_msg = validate_url(url_param)
            if not is_valid:
                logger.warning(f"快捷指令无效URL: {url_param} - {error_msg}")
                return jsonify({'error': f'URL验证失败: {error_msg}'}), 400
            
            audio_only = data.get('audio_only', 'false').lower() == 'true'
            quality_param = data.get('quality', 'bestvideo+bestaudio/best' if not audio_only else 'bestaudio/best')
            output_format_param = data.get('output_format', 'auto')
            download_id = str(uuid.uuid4())
            options_data = {
                'audio_only': audio_only, 'format_string': quality_param, 
                'output_format': output_format_param,
                'outtmpl_override': os.path.join(current_app.config['DOWNLOAD_FOLDER'], f"{download_id}_%(title).180B.%(ext)s")
            }
            ydl_opts = _build_ydl_options(options_data, current_app.config['DOWNLOAD_FOLDER'])
            download_manager.add_download(download_id, url_param, ydl_opts)
            thread = threading.Thread(target=_download_worker, args=(download_id, url_param, ydl_opts))
            thread.daemon = True
            thread.start()
            logger.info(f"快捷指令下载已开始: {download_id} for {url_param}")
            return jsonify({
                'success': True, 'download_id': download_id,
                'status_url': url_for('get_download_status', download_id=download_id, _external=True),
                'file_url': url_for('shortcuts_get_file', download_id=download_id, _external=True),
                'message': '下载已开始'
            })
        except Exception as e:
            logger.error(f"快捷指令下载错误: URL='{url_param}', {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'success': False, 'error': '快捷指令下载时发生服务器错误'}), 500

    @app.route('/api/shortcuts/download-direct', methods=['POST'])
    def shortcuts_download_direct():
        url_param = None
        final_filepath_to_clean = None 
        try:
            data = request.get_json() if request.is_json else request.form.to_dict()
            if not data or 'url' not in data: return jsonify({'error': '需要提供 URL'}), 400
            url_param = data['url'].strip()
            is_valid, error_msg = validate_url(url_param)
            if not is_valid:
                logger.warning(f"快捷指令直接下载无效URL: {url_param} - {error_msg}")
                return jsonify({'error': f'URL验证失败: {error_msg}'}), 400

            audio_only = data.get('audio_only', 'false').lower() == 'true'
            quality_param = data.get('quality', 'bestvideo+bestaudio/best' if not audio_only else 'bestaudio/best')
            output_format_param = data.get('output_format', 'auto')
            temp_basename = f"direct_{uuid.uuid4().hex}"
            options_data = {
                'audio_only': audio_only, 'format_string': quality_param,
                'output_format': output_format_param,
                'outtmpl_direct': os.path.join(current_app.config['DOWNLOAD_FOLDER'], temp_basename + '.%(ext)s')
            }
            ydl_opts = _build_ydl_options(options_data, current_app.config['DOWNLOAD_FOLDER'])
            ydl_opts['ffmpeg_location'] = os.environ.get('FFMPEG_PATH', 'ffmpeg')
            
            logger.info(f"快捷指令直接下载: URL={url_param}, Opts={ydl_opts}")
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url_param, download=True)
                final_filepath = None
                if info.get('requested_downloads') and info['requested_downloads'][0].get('filepath'):
                    final_filepath = info['requested_downloads'][0]['filepath']
                else:
                    for fname_scan in os.listdir(current_app.config['DOWNLOAD_FOLDER']):
                        if fname_scan.startswith(temp_basename):
                            final_filepath = os.path.join(current_app.config['DOWNLOAD_FOLDER'], fname_scan)
                            break
                if not final_filepath or not os.path.exists(final_filepath):
                    logger.error(f"直接下载后未找到文件: basename={temp_basename}, URL={url_param}")
                    return jsonify({'success': False, 'error': '下载后文件未找到'}), 500
                
                final_filepath_to_clean = final_filepath 
                actual_filename = os.path.basename(final_filepath)
                actual_ext = actual_filename.split('.')[-1].lower() if '.' in actual_filename else ''
                mimetype = {'mp3': 'audio/mpeg', 'm4a': 'audio/aac', 'aac': 'audio/aac', 
                            'mp4': 'video/mp4', 'webm': 'video/webm', 'mkv': 'video/x-matroska', 
                            'flac': 'audio/flac', 'wav': 'audio/wav'}.get(actual_ext, 'application/octet-stream')
                download_display_name = sanitize_filename(info.get('title', temp_basename)) + (f'.{actual_ext}' if actual_ext else '')
                
                response = send_file(final_filepath, as_attachment=True, download_name=download_display_name, mimetype=mimetype)
                
                @after_this_request 
                def cleanup_direct_download_file(response_after):
                    try:
                        if final_filepath_to_clean and os.path.exists(final_filepath_to_clean):
                            os.remove(final_filepath_to_clean)
                            logger.info(f"已清理直接下载的临时文件: {final_filepath_to_clean}")
                    except Exception as e_clean:
                        logger.error(f"清理直接下载文件失败 {final_filepath_to_clean}: {e_clean}")
                    return response_after
                return response
            
        except Exception as e:
            logger.error(f"快捷指令直接下载时发生严重错误: URL='{url_param}', {e}", exc_info=True)
            # Return generic error message to user, log specific error
            if final_filepath_to_clean and os.path.exists(final_filepath_to_clean):
                try: os.remove(final_filepath_to_clean)
                except: pass # Log this failure too if needed
            return jsonify({'success': False, 'error': '直接下载失败，发生服务器错误'}), 500

    @app.route('/api/shortcuts/download/<download_id>/file')
    @login_required 
    def shortcuts_get_file(download_id):
        download_info = download_manager.get_download(download_id)
        if not download_info: return jsonify({'error': '未找到下载'}), 404
        if download_info['status'] != 'completed':
            return jsonify({'error': '下载未完成', 'status': download_info['status'],
                            'progress': _make_json_serializable_recursive(download_info.get('progress', 0))}), 202
        if not download_info.get('filename'): return jsonify({'error': '文件名丢失'}), 404
        filename = sanitize_filename(download_info['filename'])
        return send_from_directory(current_app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True, download_name=filename)

    @app.route('/api/formats', methods=['POST'])
    @login_required
    def get_available_formats():
        url_param = None
        try:
            data = request.get_json(); 
            if not data or 'url' not in data: return jsonify({'error': '需要提供 URL'}), 400
            url_param = data['url'].strip()
            is_valid, err_msg = validate_url(url_param); 
            if not is_valid: 
                logger.warning(f"获取格式时使用了无效URL: {url_param} - {err_msg}")
                return jsonify({'error': f'URL验证失败: {err_msg}'}), 400
            ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            with YoutubeDL(ydl_opts) as ydl: info = ydl.extract_info(url_param, download=False)
            formats_list = []
            if 'formats' in info and info['formats'] is not None:
                for f_info in info['formats']:
                    if not isinstance(f_info, dict): continue
                    formats_list.append({
                        'format_id': f_info.get('format_id'), 'ext': f_info.get('ext'),
                        'quality_note': f_info.get('format_note', str(f_info.get('quality', ''))),
                        'filesize_str': f_info.get('filesize_str') or (f"{round(f_info.get('filesize', 0) / (1024*1024), 2)}MB" if f_info.get('filesize') else "N/A"),
                        'vcodec': f_info.get('vcodec', 'none'), 'acodec': f_info.get('acodec', 'none'),
                        'resolution': f_info.get('resolution') or (f"{f_info.get('width')}x{f_info.get('height')}" if f_info.get('width') and f_info.get('height') else None),
                    })
            shortcut_options = []
            if any(f.get('vcodec') != 'none' for f in formats_list):
                shortcut_options.append({'title': '📺 最佳视频 (MP4)', 'value': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best', 'type': 'video'})
                shortcut_options.append({'title': '📱 720p 视频 (MP4)', 'value': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]', 'type': 'video'})
            if any(f.get('acodec') != 'none' for f in formats_list):
                shortcut_options.append({'title': '🎵 最佳音频 (M4A/Opus)', 'value': 'bestaudio/best', 'type': 'audio'})
                shortcut_options.append({'title': '🎧 MP3 (192kbps)', 'value': 'mp3_192k_convert', 'type': 'audio_convert'})
            return jsonify(_make_json_serializable_recursive({
                'title': info.get('title', '未知标题'), 'uploader': info.get('uploader'),
                'duration_string': info.get('duration_string'), 'formats': formats_list,
                'shortcut_options': shortcut_options
            }))
        except Exception as e:
            logger.error(f"获取格式列表时发生错误: URL='{url_param}', {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '获取可用格式时发生内部错误'}), 500

    @app.route('/api/admin/update-check', methods=['GET'])
    @admin_required
    def check_update():
        try:
            current_v = _get_current_version()
            return jsonify(_make_json_serializable_recursive({
                'update_available': None, 
                'message': '请通过更新Docker镜像或在服务器上手动运行 "pip install --upgrade yt-dlp" 来更新yt-dlp。',
                'current_version': current_v,
            }))
        except Exception as e:
            logger.error(f"检查更新时发生错误: {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '检查更新时发生内部错误'}), 500

    @app.route('/api/admin/update', methods=['POST'])
    @admin_required
    def start_update():
        try:
            logger.warning(f"用户 {get_current_user()} 尝试从API触发更新。此功能已禁用。")
            return jsonify({
                'success': False,
                'message': '此功能已禁用。请通过更新和重新构建Docker镜像来更新yt-dlp。'
            }), 403 
        except Exception as e:
            logger.error(f"启动更新时发生错误: {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '启动更新时发生内部错误'}), 500
        
    @app.route('/api/admin/version', methods=['GET'])
    @admin_required
    def get_version_info():
        try:
            return jsonify(_make_json_serializable_recursive({
                'yt_dlp_version': _get_current_version(),
                'web_interface_version': os.environ.get('APP_VERSION', '1.2.3'), # 更新一个示例版本号
                'last_yt_dlp_update_check': _get_last_update_time() 
            }))
        except Exception as e:
            logger.error(f"获取版本信息时发生错误: {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '获取版本信息时发生内部错误'}), 500

    @app.route('/api/shortcuts/download-file/<shortcut_type>')
    def download_shortcut_file(shortcut_type):
        try:
            shortcuts_dir = os.path.join(current_app.static_folder, 'shortcuts')
            allowed_shortcuts = {
                'smart_downloader': 'SmartVideoDownloader.shortcut',
                'audio_extractor': 'AudioExtractor.shortcut',
                '720p_downloader': '720PDownloader.shortcut',
            } 
            if shortcut_type not in allowed_shortcuts:
                return jsonify({'error': '未知的快捷指令类型'}), 404
            safe_filename = allowed_shortcuts[shortcut_type]
            file_path = os.path.join(shortcuts_dir, safe_filename)
            if not os.path.isfile(file_path):
                logger.error(f"快捷指令文件未找到: {file_path}")
                return jsonify({'error': '快捷指令文件不存在'}), 404
            logger.info(f"提供快捷指令文件下载: {safe_filename}")
            return send_from_directory(
                shortcuts_dir, safe_filename, as_attachment=True,
                download_name=safe_filename, mimetype='application/vnd.apple.shortcut' 
            )
        except Exception as e:
            logger.error(f"下载快捷指令文件时发生错误: {shortcut_type}, {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '下载快捷指令文件时发生服务器内部错误'}), 500

    @app.route('/api/admin/cleanup', methods=['POST'])
    @admin_required
    def manual_cleanup():
        try:
            cleanup_mgr = get_cleanup_manager()
            if not cleanup_mgr: return jsonify({'error': '清理管理器未初始化'}), 500
            cleaned_count, cleaned_size_bytes = cleanup_mgr.cleanup_files(force_all=True)
            storage_info = cleanup_mgr.get_storage_info()
            cleaned_size_mb = round(cleaned_size_bytes / (1024*1024), 2)
            logger.info(f"手动清理完成: 删除了 {cleaned_count} 个文件, 总大小 {cleaned_size_mb} MB. 用户: {get_current_user()}")
            return jsonify(_make_json_serializable_recursive({
                'success': True, 'cleaned_files': cleaned_count, 
                'cleaned_size_mb': cleaned_size_mb, 'storage_info': storage_info,
                'message': f'清理完成，删除了 {cleaned_count} 个文件 (约 {cleaned_size_mb} MB)'
            }))
        except Exception as e:
            logger.error(f"手动清理时发生错误: {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '手动清理时发生内部错误'}), 500

    @app.route('/api/admin/storage-info', methods=['GET'])
    @admin_required
    def get_storage_info():
        try:
            cleanup_mgr = get_cleanup_manager()
            if not cleanup_mgr: return jsonify({'error': '清理管理器未初始化'}), 500
            return jsonify(_make_json_serializable_recursive(cleanup_mgr.get_storage_info()))
        except Exception as e:
            logger.error(f"获取存储信息时发生错误: {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '获取存储信息时发生内部错误'}), 500

    @app.route('/api/admin/cleanup-config', methods=['GET', 'POST'])
    @admin_required
    def cleanup_config_route():
        try:
            cleanup_mgr = get_cleanup_manager()
            if not cleanup_mgr: return jsonify({'error': '清理管理器未初始化'}), 500
            if request.method == 'GET':
                return jsonify(_make_json_serializable_recursive(cleanup_mgr.get_config()))
            elif request.method == 'POST':
                new_config_data = request.get_json()
                if not new_config_data: return jsonify({'error': '需要提供配置数据'}), 400
                validated_update = {}
                expected_types = {
                    'auto_cleanup_enabled': bool, 'cleanup_interval_hours': int,
                    'file_retention_hours': int, 'max_storage_mb': int,
                    'cleanup_on_download': bool, 'keep_recent_files': int,
                    'temp_file_retention_minutes': int
                }
                for key, expected_type in expected_types.items():
                    if key in new_config_data: 
                        try:
                            if expected_type == bool:
                                validated_update[key] = str(new_config_data[key]).lower() in ['true', '1', 't', 'yes', 'on']
                            else:
                                validated_update[key] = expected_type(new_config_data[key])
                        except (ValueError, TypeError):
                            return jsonify({'error': f"配置项 '{key}' 的值 '{new_config_data[key]}' 类型不正确或无效 (期望 {expected_type.__name__})"}), 400
                
                cleanup_mgr.update_config(validated_update)
                logger.info(f"清理配置已更新为: {cleanup_mgr.get_config()} by {get_current_user()}")
                return jsonify(_make_json_serializable_recursive({
                    'success': True, 'message': '配置已更新', 'config': cleanup_mgr.get_config()
                }))
        except Exception as e:
            logger.error(f"处理清理配置时发生错误: {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '处理清理配置时发生内部错误'}), 500

    @app.route('/downloads/<path:filename>')
    @login_required
    def download_file(filename):
        safe_filename = secure_filename(filename) 
        if not safe_filename or safe_filename != filename : 
            logger.warning(f"尝试下载不安全或被修改的文件名: original='{filename}', sanitized='{safe_filename}' by user {get_current_user()}")
            return jsonify({'error': '无效的文件名或路径'}), 400
        logger.info(f"用户 {get_current_user()} 请求下载文件: {safe_filename}")
        try:
            download_directory = current_app.config['DOWNLOAD_FOLDER']
            full_path = os.path.normpath(os.path.join(download_directory, safe_filename))
            # 再次确认路径安全，防止拼接后产生意外 (更严格的检查)
            # os.path.abspath(download_directory) 确保 download_directory 是绝对路径
            # full_path 也转换为绝对路径进行比较
            abs_download_dir = os.path.abspath(download_directory)
            abs_full_path = os.path.abspath(full_path)

            if not abs_full_path.startswith(abs_download_dir + os.sep) and abs_full_path != abs_download_dir :
                logger.error(f"检测到路径遍历尝试: {filename} -> {abs_full_path} vs {abs_download_dir}")
                return jsonify({'error': '禁止访问的文件路径'}), 403
            
            if not os.path.isfile(abs_full_path): # 确保请求的是文件
                logger.error(f"请求下载的路径不是文件: {safe_filename}")
                return jsonify({'error': '请求的路径不是文件'}), 404

            return send_from_directory(download_directory, safe_filename, as_attachment=True)
        except FileNotFoundError:
            logger.error(f"请求下载的文件未找到: {safe_filename} in {download_directory}")
            return jsonify({'error': '文件未找到'}), 404
        except Exception as e:
            logger.error(f"下载文件时发生错误: {safe_filename}, {e}", exc_info=True)
            # Return generic error message to user, log specific error
            return jsonify({'error': '下载文件时发生服务器内部错误'}), 500

    def _build_ydl_options(data, download_folder_abs_path):
        """根据前端选项构建 yt-dlp 配置，确保返回的字典是JSON可序列化的"""
        ydl_opts = {
            'outtmpl': os.path.join(download_folder_abs_path, '%(title).180B - %(id)s.%(ext)s'),
            'quiet': False, 
            'no_warnings': True, 
            'restrictfilenames': True,
            'writeinfojson': data.get('write_info_json', False),
            'writesubtitles': data.get('download_subtitles', False),
            'writeautomaticsub': data.get('auto_subtitles', False) if data.get('download_subtitles', False) else False,
            'writethumbnail': data.get('download_thumbnail', False),
            'max_filesize': data.get('max_filesize_gb', 5) * 1024 * 1024 * 1024,
            'socket_timeout': int(data.get('socket_timeout', 60)),
            'retries': int(data.get('retries', 5)),
            'concurrent_fragment_downloads': int(data.get('concurrent_fragments', 7)),
            'fragment_retries': int(data.get('fragment_retries', 5)),
            'skip_unavailable_fragments': data.get('skip_unavailable_fragments', True),
            'noprogress': True,
            'postprocessor_args': {'ffmpeg': ['-hide_banner', '-loglevel', 'error', '-stats_period', '1']},
            'ffmpeg_location': os.environ.get('FFMPEG_PATH', 'ffmpeg'),
        }
        audio_only = data.get('audio_only', False)
        format_string = data.get('format_string', data.get('quality', 'bestvideo+bestaudio/best' if not audio_only else 'bestaudio/best'))
        output_format_ext = data.get('output_format', 'auto').lower()
        ydl_opts['format'] = format_string
        ydl_opts.setdefault('postprocessors', [])
        if audio_only:
            if format_string.startswith('mp3_') and format_string.endswith('_convert'): 
                quality_val = format_string.split('_')[1].replace('k', '')
                ydl_opts['format'] = f'bestaudio[abr<={quality_val}]/bestaudio/best'
                ydl_opts['postprocessors'].append({'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': quality_val if quality_val.isdigit() else '192'})
            elif output_format_ext in ['mp3', 'm4a', 'aac', 'opus', 'vorbis', 'wav', 'flac'] and output_format_ext not in ['auto', 'best']:
                preferred_audio_quality = data.get('audio_bitrate', '192K')
                quality_for_ffmpeg = re.sub(r'[^0-9]', '', preferred_audio_quality) or '192'
                ydl_opts['postprocessors'].append({'key': 'FFmpegExtractAudio', 'preferredcodec': output_format_ext, 'preferredquality': quality_for_ffmpeg})
        else: 
            if output_format_ext in ['mp4', 'mkv', 'webm', 'mov', 'avi'] and output_format_ext not in ['auto', 'best']:
                if output_format_ext == 'mp4':
                     ydl_opts['postprocessors'].append({'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'})
                else:
                     ydl_opts['postprocessors'].append({'key': 'FFmpegVideoConvertor', 'preferedformat': output_format_ext})
        
        if data.get('download_subtitles', False):
            sub_langs_input = data.get('subtitle_langs', 'all')
            if isinstance(sub_langs_input, str) and sub_langs_input.lower() != 'all':
                ydl_opts['subtitleslangs'] = [s.strip() for s in sub_langs_input.split(',')]
            elif isinstance(sub_langs_input, list) and 'all' not in [s.lower() for s in sub_langs_input]:
                ydl_opts['subtitleslangs'] = sub_langs_input
            if data.get('embed_subtitles', False) and ydl_opts['writesubtitles']:
                ydl_opts['postprocessors'].append({'key': 'FFmpegEmbedSubtitle'})
        if data.get('download_thumbnail', False) and data.get('embed_thumbnail', False):
            ydl_opts['postprocessors'].append({'key': 'EmbedThumbnail'})
        if data.get('download_description', False): ydl_opts['writedescription'] = True
        playlist_items_str = data.get('playlist_items')
        if playlist_items_str:
            ydl_opts['playlist_items'] = playlist_items_str
            ydl_opts['noplaylist'] = False 
        elif data.get('download_playlist', False):
            ydl_opts['noplaylist'] = False
        else:
            ydl_opts['noplaylist'] = True
        if 'outtmpl_direct' in data and data['outtmpl_direct']: ydl_opts['outtmpl'] = data['outtmpl_direct']
        elif 'outtmpl_override' in data and data['outtmpl_override']: ydl_opts['outtmpl'] = data['outtmpl_override']
        
        return _make_json_serializable_recursive(ydl_opts)

    def _download_worker(download_id, url, ydl_opts_original):
        current_ydl_opts = ydl_opts_original.copy()
        actual_filename_downloaded = None 
        try:
            download_manager.update_download(download_id, status='downloading', start_time=datetime.now(timezone.utc).isoformat())
            def progress_hook(d):
                nonlocal actual_filename_downloaded
                try:
                    hook_status = d.get('status')
                    if hook_status == 'downloading':
                        update_data = {'status': 'downloading'}
                        total_bytes_key = 'total_bytes' if d.get('total_bytes') else 'total_bytes_estimate'
                        if d.get(total_bytes_key):
                            downloaded, total = d.get('downloaded_bytes', 0), d[total_bytes_key]
                            if total and total > 0: update_data['progress'] = round((downloaded / total) * 100, 2)
                            update_data.update({'total_bytes': total, 'downloaded_bytes': downloaded})
                        if d.get('speed'): update_data['speed'] = round(d['speed'] / (1024*1024), 2) if d['speed'] else None
                        if d.get('eta') is not None: update_data['eta'] = int(d['eta'])
                        if d.get('elapsed') is not None: update_data['elapsed'] = int(d['elapsed'])
                        current_dl_filename = d.get('_filename') or d.get('filename') or d.get('info_dict', {}).get('_filename')
                        if current_dl_filename: update_data['filename'] = os.path.basename(current_dl_filename)
                        download_manager.update_download(download_id, **update_data)
                    elif hook_status == 'finished':
                        final_filename_from_hook = d.get('filename') or d.get('info_dict', {}).get('_filename')
                        if final_filename_from_hook: actual_filename_downloaded = os.path.basename(final_filename_from_hook)
                        logger.info(f"下载完成 (钩子): {download_id}, 文件: {actual_filename_downloaded or '未知'}")
                        download_manager.update_download(download_id, status='completed', progress=100.0, filename=actual_filename_downloaded, end_time=datetime.now(timezone.utc).isoformat(), speed=0.0)
                        cleanup_mgr = get_cleanup_manager()
                        if cleanup_mgr and actual_filename_downloaded: cleanup_mgr.cleanup_on_download_complete(actual_filename_downloaded)
                    elif hook_status == 'error':
                        error_detail = d.get('error', d.get('fragment_error', '未知下载错误 (来自钩子)'))
                        logger.error(f"下载过程中发生错误 (钩子报告): {download_id}, info: {error_detail}")
                        download_manager.update_download(download_id, status='error', error=str(error_detail), end_time=datetime.now(timezone.utc).isoformat())
                except Exception as e_hook_inner:
                    logger.error(f"进度钩子内部错误: {download_id}, {e_hook_inner}", exc_info=True)
            
            current_ydl_opts['progress_hooks'] = [progress_hook]
            current_ydl_opts['quiet'] = False 
            current_ydl_opts['noprogress'] = True

            if current_ydl_opts.get('noplaylist', False) and 'playlist_items' in current_ydl_opts:
                del current_ydl_opts['playlist_items']

            with YoutubeDL(current_ydl_opts) as ydl:
                logger.info(f"工作线程 {download_id} 使用选项: {json.dumps(current_ydl_opts, indent=2, default=str)} 下载URL: {url}")
                ydl.download([url]) 
            
            current_status_after_dl = download_manager.get_download(download_id)
            if current_status_after_dl and current_status_after_dl.get('status') == 'downloading':
                logger.warning(f"下载 {download_id} 在yt-dlp.download()结束后状态仍为 'downloading'。")
                if actual_filename_downloaded and os.path.exists(os.path.join(current_app.config['DOWNLOAD_FOLDER'], actual_filename_downloaded)):
                     download_manager.update_download(download_id, status='completed', progress=100.0, filename=actual_filename_downloaded, end_time=datetime.now(timezone.utc).isoformat())
                     logger.info(f"下载 {download_id} 在工作线程末尾被标记为完成。")
                     cleanup_mgr = get_cleanup_manager(); 
                     if cleanup_mgr: cleanup_mgr.cleanup_on_download_complete(actual_filename_downloaded)
                else:
                    logger.error(f"下载 {download_id} 完成但未获取到最终文件名。标记为错误。")
                    download_manager.update_download(download_id, status='error', error='下载后未找到有效文件名。', end_time=datetime.now(timezone.utc).isoformat())
        except SystemExit as e_sysexit: 
            logger.error(f"下载工作线程 {download_id} 遇到 SystemExit: {e_sysexit}", exc_info=True)
            download_manager.update_download(download_id, status='error', error=f"下载器严重错误: {e_sysexit}", end_time=datetime.now(timezone.utc).isoformat())
        except Exception as e_worker_main:
            error_msg = str(e_worker_main.args[0]) if hasattr(e_worker_main, 'args') and e_worker_main.args else str(e_worker_main)
            logger.error(f"下载工作线程 {download_id} 发生严重错误: {error_msg}", exc_info=True)
            download_manager.update_download(download_id, status='error', error=error_msg, end_time=datetime.now(timezone.utc).isoformat())

    def _get_current_version():
        """获取当前yt-dlp库版本"""
        try:
            import yt_dlp.version 
            return yt_dlp.version.__version__
        except ImportError:
            logger.warning("无法从 yt_dlp.version 导入 __version__")
            try:
                import subprocess
                result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, check=True, timeout=5)
                return result.stdout.strip()
            except Exception as e_ver: 
                logger.error(f"执行 yt-dlp --version 失败: {e_ver}", exc_info=True)
                return "unknown"

    def _get_last_update_time():
        """获取 yt-dlp 库文件的最后修改时间"""
        try:
            import yt_dlp 
            lib_file_to_check = os.path.join(os.path.dirname(yt_dlp.__file__), '__init__.py')
            if os.path.exists(lib_file_to_check):
                mtime = os.path.getmtime(lib_file_to_check)
                return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            return "unknown (library path check failed)"
        except Exception as e_lup: 
            logger.error(f"获取yt-dlp最后更新时间失败: {e_lup}", exc_info=True)
            return "unknown"

    def _generate_shortcut_config(shortcut_type): # 这个函数现在主要用于元数据，实际文件由 /api/shortcuts/download-file 提供
        """为iOS快捷指令生成示例配置元数据"""
        try:
            if request and request.url_root:
                server_base_url = request.url_root.rstrip('/') 
            else:
                server_base_url = os.environ.get('SERVER_URL_FOR_SHORTCUTS', f"http://{os.environ.get('HOST', 'localhost')}:{os.environ.get('PORT', '8080')}")
        except RuntimeError: 
            server_base_url = os.environ.get('SERVER_URL_FOR_SHORTCUTS', f"http://{os.environ.get('HOST', 'localhost')}:{os.environ.get('PORT', '8080')}") 

        hostname = urlparse(server_base_url).hostname or "your_server"
        # 这个函数现在返回的是元数据，实际的 .shortcut 文件应预先创建并放在 static/shortcuts/
        shortcuts_meta = {
            'smart_downloader': {
                "name": f"智能下载器@{hostname}", 
                "description": "从剪贴板获取链接, 选择格式后通过yt-dlp-web下载。",
                "filename": "SmartVideoDownloader.shortcut", # 指向 static/shortcuts/ 下的实际文件
                "api_endpoint_async": f"{server_base_url}/api/shortcuts/download", # 异步下载API
                "api_endpoint_direct": f"{server_base_url}/api/shortcuts/download-direct", # 直接下载API
                "status_url_pattern": f"{server_base_url}/api/download/{{DOWNLOAD_ID}}/status",
                "file_url_pattern": f"{server_base_url}/api/shortcuts/download/{{DOWNLOAD_ID}}/file"
            },
            'audio_extractor': {
                "name": f"音频提取@{hostname}", 
                "description": "从剪贴板获取链接, 提取MP3音频。",
                "filename": "AudioExtractor.shortcut",
                "api_endpoint_direct": f"{server_base_url}/api/shortcuts/download-direct", 
                "default_params": {"audio_only": "true", "output_format": "mp3", "format_string": "bestaudio/best"}
            },
            '720p_downloader': {
                "name": f"720P下载器@{hostname}",
                "description": "从剪贴板获取链接, 下载720P MP4视频。",
                "filename": "720PDownloader.shortcut",
                "api_endpoint_direct": f"{server_base_url}/api/shortcuts/download-direct",
                "default_params": {"audio_only": "false", "format_string": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]", "output_format": "mp4"}
            }
        }
        return shortcuts_meta.get(shortcut_type)

    return app