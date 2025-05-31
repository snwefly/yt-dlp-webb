# -*- coding: utf-8 -*-
"""
API 路由 - 视频信息和下载相关
"""

from flask import Blueprint, request, jsonify, current_app, send_from_directory, send_file, abort
from ..auth import login_required
from ..core.ytdlp_manager import get_ytdlp_manager
from ..core.download_manager import get_download_manager
from ..utils import validate_url
import logging
import os

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

@api_bp.route('/info', methods=['GET', 'POST'])
@login_required
def get_video_info():
    """获取视频信息而不下载"""
    try:
        # 确保 yt-dlp 已初始化
        ytdlp_manager = get_ytdlp_manager()
        if not ytdlp_manager.is_available():
            return jsonify({'error': 'yt-dlp 服务不可用'}), 503

        # 支持 GET 和 POST 两种方法
        if request.method == 'GET':
            # GET 请求从查询参数获取 URL
            url = request.args.get('url')
            if not url:
                return jsonify({'error': '需要提供 URL 参数'}), 400
        else:
            # POST 请求从 JSON 数据获取 URL
            data = request.get_json()
            if not data or 'url' not in data:
                return jsonify({'error': '需要提供 URL'}), 400
            url = data['url']

        url = url.strip()

        # 验证URL安全性
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL attempted: {url} - {error_msg}")
            return jsonify({'error': f'URL验证失败: {error_msg}'}), 400

        # 最简配置 - 让yt-dlp使用默认行为
        ydl_opts = {
            'quiet': True,
            'skip_download': True,  # 只获取信息，不下载
            # 让yt-dlp使用所有默认设置，包括自动处理YouTube等网站
        }

        # 合并增强配置
        enhanced_opts = ytdlp_manager.get_enhanced_options()
        ydl_opts.update(enhanced_opts)

        # 尝试多种策略获取视频信息
        info = None
        last_error = None

        # 策略1: 使用默认配置
        try:
            with ytdlp_manager.create_downloader(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            last_error = e
            logger.warning(f"默认配置失败: {str(e)}")

            # 策略2: 使用基础配置
            try:
                basic_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                    'skip_download': True,
                }
                with ytdlp_manager.create_downloader(basic_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e2:
                last_error = e2
                logger.error(f"基础配置也失败: {str(e2)}")

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
        }

        # 处理格式信息
        if 'formats' in info:
            formats = []
            for fmt in info['formats'][:20]:  # 限制格式数量
                if fmt.get('vcodec') != 'none' or fmt.get('acodec') != 'none':
                    formats.append({
                        'format_id': fmt.get('format_id'),
                        'ext': fmt.get('ext'),
                        'quality': fmt.get('format_note', ''),
                        'filesize': fmt.get('filesize'),
                        'vcodec': fmt.get('vcodec'),
                        'acodec': fmt.get('acodec'),
                        'resolution': fmt.get('resolution')
                    })
            result['formats'] = formats

        return jsonify({
            'success': True,
            'info': result
        })

    except Exception as e:
        error_msg = str(e)
        if 'Unsupported URL' in error_msg:
            return jsonify({'success': False, 'error': '不支持的URL或网站'}), 400
        elif 'Video unavailable' in error_msg:
            return jsonify({'success': False, 'error': '视频不可用或已被删除'}), 400
        elif 'Private video' in error_msg:
            return jsonify({'success': False, 'error': '私有视频，无法访问'}), 400
        else:
            logger.error(f"获取视频信息时发生错误: {e}")
            return jsonify({'success': False, 'error': f'获取视频信息失败: {error_msg}'}), 400

@api_bp.route('/download', methods=['POST'])
@login_required
def start_download():
    """开始视频下载"""
    try:
        from ..auth import get_current_user
        current_user = get_current_user()
        logger.info(f"🎬 用户 {current_user} 请求下载")
        # 确保 yt-dlp 已初始化
        ytdlp_manager = get_ytdlp_manager()
        if not ytdlp_manager.is_available():
            return jsonify({'error': 'yt-dlp 服务不可用'}), 503

        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': '需要提供 URL'}), 400

        url = data['url'].strip()

        # 验证URL安全性
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL attempted: {url} - {error_msg}")
            return jsonify({'error': f'URL验证失败: {error_msg}'}), 400

        # 创建下载任务
        download_manager = get_download_manager()
        download_id = download_manager.create_download(url, data)

        return jsonify({
            'success': True,
            'message': '下载已开始',
            'download_id': download_id
        })

    except Exception as e:
        logger.error(f"开始下载时发生错误: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/download/<download_id>/status')
@login_required
def get_download_status(download_id):
    """获取下载状态"""
    download_manager = get_download_manager()
    download = download_manager.get_download(download_id)

    if not download:
        return jsonify({'error': '下载任务不存在'}), 404

    return jsonify(download)

@api_bp.route('/downloads')
@login_required
def list_downloads():
    """列出所有下载"""
    download_manager = get_download_manager()
    downloads = download_manager.get_all_downloads()
    return jsonify({'downloads': downloads})

@api_bp.route('/download/<download_id>/file')
@login_required
def download_file_by_id(download_id):
    """通过下载ID获取文件"""
    try:
        download_manager = get_download_manager()
        download = download_manager.get_download(download_id)

        if not download:
            return jsonify({'error': '下载任务不存在'}), 404

        if download.get('status') != 'completed':
            return jsonify({'error': '下载尚未完成'}), 400

        file_path = download.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        filename = download.get('filename', 'download')

        # 返回文件
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        return jsonify({'error': '文件下载失败'}), 500

@api_bp.route('/downloads/<filename>')
@login_required
def download_file_by_name(filename):
    """通过文件名下载文件（兼容旧接口）"""
    try:
        download_folder = current_app.config['DOWNLOAD_FOLDER']
        file_path = os.path.join(download_folder, filename)

        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        return jsonify({'error': '文件下载失败'}), 500

@api_bp.route('/files')
@login_required
def list_files():
    """列出所有已下载的文件"""
    try:
        download_manager = get_download_manager()
        files = download_manager.list_downloaded_files()

        # 格式化文件大小
        for file_info in files:
            size_bytes = file_info.get('file_size', 0)
            if size_bytes:
                if size_bytes < 1024:
                    file_info['file_size_formatted'] = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    file_info['file_size_formatted'] = f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    file_info['file_size_formatted'] = f"{size_bytes / (1024 * 1024):.1f} MB"
                else:
                    file_info['file_size_formatted'] = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            else:
                file_info['file_size_formatted'] = "未知"

            # 格式化创建时间
            if file_info.get('created_at'):
                file_info['created_at_formatted'] = file_info['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        return jsonify({
            'success': True,
            'files': files,
            'total': len(files)
        })

    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return jsonify({'error': '获取文件列表失败'}), 500
