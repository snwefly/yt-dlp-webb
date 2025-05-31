# -*- coding: utf-8 -*-
"""
iOS 快捷指令专用路由
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from ..auth import login_required
from ..core.ytdlp_manager import get_ytdlp_manager
from ..core.download_manager import get_download_manager
from ..utils import validate_url
import logging
import os
import tempfile

logger = logging.getLogger(__name__)
shortcuts_bp = Blueprint('shortcuts', __name__)

@shortcuts_bp.route('/download', methods=['POST'])
@login_required
def shortcuts_download():
    """iOS 快捷指令兼容的下载端点 - 异步模式"""
    try:
        # 确保 yt-dlp 已初始化
        ytdlp_manager = get_ytdlp_manager()
        if not ytdlp_manager.is_available():
            return jsonify({'error': 'yt-dlp 服务不可用'}), 503
            
        # 处理 JSON 和表单数据
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

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
            'download_id': download_id,
            'status_url': f'/api/download/{download_id}/status',
            'download_url': f'/api/shortcuts/download/{download_id}/file'
        })

    except Exception as e:
        logger.error(f"快捷指令下载失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@shortcuts_bp.route('/download-direct', methods=['POST'])
@login_required
def shortcuts_download_direct():
    """iOS 快捷指令直接下载端点 - 同步模式"""
    try:
        # 确保 yt-dlp 已初始化
        ytdlp_manager = get_ytdlp_manager()
        if not ytdlp_manager.is_available():
            return jsonify({'error': 'yt-dlp 服务不可用'}), 503
            
        # 处理 JSON 和表单数据
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()

        if not data or 'url' not in data:
            return jsonify({'error': '需要提供 URL'}), 400

        url = data['url'].strip()
        audio_only = data.get('audio_only', 'false').lower() == 'true'
        quality = data.get('quality', 'best')

        # 验证URL安全性
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            logger.warning(f"Invalid URL attempted: {url} - {error_msg}")
            return jsonify({'error': f'URL验证失败: {error_msg}'}), 400

        # 配置下载选项
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }

            if audio_only:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }]
                })
            else:
                ydl_opts['format'] = quality

            # 合并增强配置
            enhanced_opts = ytdlp_manager.get_enhanced_options()
            ydl_opts.update(enhanced_opts)

            # 下载文件
            with ytdlp_manager.create_downloader(ydl_opts) as ydl:
                ydl.download([url])

            # 查找下载的文件
            downloaded_files = []
            for file in os.listdir(temp_dir):
                if os.path.isfile(os.path.join(temp_dir, file)):
                    downloaded_files.append(file)

            if not downloaded_files:
                return jsonify({'error': '下载失败，未找到文件'}), 500

            # 返回第一个文件
            downloaded_file = downloaded_files[0]
            file_path = os.path.join(temp_dir, downloaded_file)

            # 返回文件内容
            def remove_file():
                try:
                    os.remove(file_path)
                except:
                    pass

            return send_file(
                file_path,
                as_attachment=True,
                download_name=downloaded_file,
                mimetype='application/octet-stream'
            )

    except Exception as e:
        logger.error(f"直接下载失败: {e}")
        return jsonify({'error': str(e)}), 500

@shortcuts_bp.route('/download/<download_id>/file')
@login_required
def shortcuts_get_file(download_id):
    """获取iOS快捷指令下载的文件"""
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
        logger.error(f"iOS快捷指令文件下载失败: {e}")
        return jsonify({'error': '文件下载失败'}), 500

@shortcuts_bp.route('/download-file/<shortcut_type>')
def download_shortcut_file(shortcut_type):
    """提供iOS快捷指令文件下载"""
    try:
        # 根据类型生成快捷指令配置
        if shortcut_type == 'video':
            filename = 'video_downloader.shortcut'
        elif shortcut_type == 'audio':
            filename = 'audio_downloader.shortcut'
        else:
            return jsonify({'error': '不支持的快捷指令类型'}), 400

        # 检查文件是否存在
        file_path = os.path.join(current_app.static_folder, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': '快捷指令文件不存在'}), 404

        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"快捷指令文件下载失败: {e}")
        return jsonify({'error': str(e)}), 500
