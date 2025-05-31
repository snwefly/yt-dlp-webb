# -*- coding: utf-8 -*-
"""
主要页面路由
"""

from flask import Blueprint, render_template, jsonify
from ..auth import login_required, admin_required
import logging
import os

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    """主网页界面"""
    return render_template('index.html')

@main_bp.route('/shortcuts-help')
@login_required
def shortcuts_help():
    """iOS快捷指令使用指南"""
    return render_template('shortcuts_help.html')

@main_bp.route('/admin')
@admin_required
def admin():
    """管理员控制台"""
    return render_template('admin.html')

@main_bp.route('/debug')
def debug():
    """认证调试页面"""
    return render_template('debug_auth.html')

@main_bp.route('/health')
def health_check():
    """健康检查端点"""
    try:
        # 检查 yt-dlp 可用性
        from ..core.ytdlp_manager import get_ytdlp_manager
        manager = get_ytdlp_manager()
        ytdlp_available = manager.is_available()

        # 检查下载目录
        download_dir = os.environ.get('DOWNLOAD_FOLDER', '/app/downloads')
        download_dir_writable = os.path.exists(download_dir) and os.access(download_dir, os.W_OK)

        # 基础健康状态
        health_status = {
            'status': 'healthy' if ytdlp_available and download_dir_writable else 'unhealthy',
            'timestamp': int(__import__('time').time()),
            'components': {
                'yt_dlp': {
                    'status': 'ok' if ytdlp_available else 'error',
                    'available': ytdlp_available
                },
                'download_directory': {
                    'status': 'ok' if download_dir_writable else 'error',
                    'path': download_dir,
                    'writable': download_dir_writable
                }
            }
        }

        # 尝试获取 yt-dlp 版本信息
        try:
            import yt_dlp
            health_status['components']['yt_dlp']['version'] = yt_dlp.__version__
        except Exception:
            health_status['components']['yt_dlp']['version'] = 'unknown'

        # 返回适当的状态码
        status_code = 200 if health_status['status'] == 'healthy' else 503

        logger.debug(f"健康检查结果: {health_status['status']}")
        return jsonify(health_status), status_code

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': int(__import__('time').time()),
            'error': str(e)
        }), 500
