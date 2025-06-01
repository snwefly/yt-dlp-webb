# -*- coding: utf-8 -*-
"""
管理员路由
"""

from flask import Blueprint, jsonify, request
from ..auth import admin_required
from ..file_cleaner import get_cleanup_manager
import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/cleanup', methods=['POST'])
@admin_required
def manual_cleanup():
    """手动触发文件清理"""
    try:
        cleanup_mgr = get_cleanup_manager()
        if not cleanup_mgr:
            return jsonify({'error': '清理管理器未初始化'}), 500

        # 执行清理
        result = cleanup_mgr.cleanup_files()

        return jsonify({
            'success': True,
            'message': '清理完成',
            'result': result
        })

    except Exception as e:
        logger.error(f"手动清理失败: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/storage-info', methods=['GET'])
@admin_required
def get_storage_info():
    """获取存储信息"""
    try:
        cleanup_mgr = get_cleanup_manager()
        if not cleanup_mgr:
            return jsonify({'error': '清理管理器未初始化'}), 500

        storage_info = cleanup_mgr.get_storage_info()

        return jsonify({
            'success': True,
            'storage_info': storage_info
        })

    except Exception as e:
        logger.error(f"获取存储信息失败: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/cleanup-config', methods=['GET', 'POST'])
@admin_required
def cleanup_config():
    """获取或更新清理配置"""
    try:
        cleanup_mgr = get_cleanup_manager()
        if not cleanup_mgr:
            return jsonify({'error': '清理管理器未初始化'}), 500

        if request.method == 'GET':
            config = cleanup_mgr.get_config()
            return jsonify({
                'success': True,
                'config': config
            })
        else:
            # POST - 更新配置
            data = request.get_json()
            if not data:
                return jsonify({'error': '无效的配置数据'}), 400

            cleanup_mgr.update_config(data)

            return jsonify({
                'success': True,
                'message': '配置已更新'
            })

    except Exception as e:
        logger.error(f"清理配置操作失败: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/version', methods=['GET'])
@admin_required
def get_version_info():
    """获取版本信息"""
    try:
        # 获取 yt-dlp 版本
        try:
            result = subprocess.run([sys.executable, '-m', 'yt_dlp', '--version'],
                                  capture_output=True, text=True, timeout=10)
            ytdlp_version = result.stdout.strip() if result.returncode == 0 else '未知'
        except Exception:
            ytdlp_version = '未知'

        # 获取 Python 版本
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # 获取应用版本（可以从环境变量或配置文件读取）
        app_version = os.environ.get('APP_VERSION', '1.0.0')

        return jsonify({
            'success': True,
            'version_info': {
                'app_version': app_version,
                'ytdlp_version': ytdlp_version,
                'python_version': python_version,
                'last_updated': '未知'  # 可以后续添加实际的更新时间
            }
        })

    except Exception as e:
        logger.error(f"获取版本信息失败: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/update-check', methods=['GET'])
@admin_required
def check_update():
    """检查更新"""
    try:
        # 这里可以实现实际的更新检查逻辑
        # 目前返回一个模拟的响应
        return jsonify({
            'success': True,
            'update_available': False,
            'current_version': os.environ.get('APP_VERSION', '1.0.0'),
            'latest_version': os.environ.get('APP_VERSION', '1.0.0'),
            'message': '当前已是最新版本'
        })

    except Exception as e:
        logger.error(f"检查更新失败: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/update', methods=['POST'])
@admin_required
def start_update():
    """开始更新"""
    try:
        # 这里可以实现实际的更新逻辑
        # 目前返回一个模拟的响应
        return jsonify({
            'success': True,
            'message': '更新功能暂未实现'
        })

    except Exception as e:
        logger.error(f"开始更新失败: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/')
@admin_required
def admin_index():
    """管理员主页"""
    from flask import render_template
    from ..auth import get_current_user

    current_user = get_current_user()
    is_authenticated = current_user is not None

    return render_template('admin.html', is_authenticated=is_authenticated, current_user=current_user)

@admin_bp.route('/cookies-manager')
@admin_required
def cookies_manager_page():
    """Cookies管理页面"""
    from flask import render_template
    from ..auth import get_current_user

    current_user = get_current_user()
    is_authenticated = current_user is not None

    return render_template('admin/cookies_manager.html', is_authenticated=is_authenticated, current_user=current_user)
