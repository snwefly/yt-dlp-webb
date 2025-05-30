# -*- coding: utf-8 -*-
"""
管理员路由
"""

from flask import Blueprint, jsonify, request
from ..auth import admin_required
from ..file_cleaner import get_cleanup_manager
import logging

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
