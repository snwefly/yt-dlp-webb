# -*- coding: utf-8 -*-
"""
管理员路由
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from functools import wraps
import logging

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

# 管理员权限检查已统一到各个路由函数内部

# 所有admin API已移至api.py，这里只保留页面路由

@admin_bp.route('/')
@login_required
def admin_index():
    """管理员主页"""
    # 检查管理员权限
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403

    is_authenticated = current_user.is_authenticated
    user_data = current_user.username if is_authenticated else None
    is_admin = current_user.is_admin if is_authenticated else False

    return render_template('admin.html',
                         is_authenticated=is_authenticated,
                         current_user=user_data,
                         is_admin=is_admin)

@admin_bp.route('/cookies-manager')
@login_required
def cookies_manager_page():
    """Cookies管理页面"""
    # 检查管理员权限
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403

    is_authenticated = current_user.is_authenticated
    user_data = current_user.username if is_authenticated else None
    is_admin = current_user.is_admin if is_authenticated else False

    return render_template('admin/cookies_manager.html',
                         is_authenticated=is_authenticated,
                         current_user=user_data,
                         is_admin=is_admin)

@admin_bp.route('/telegram-settings')
@login_required
def telegram_settings_page():
    """Telegram推送设置页面"""
    # 检查管理员权限
    if not current_user.is_admin:
        return jsonify({'error': '需要管理员权限'}), 403

    is_authenticated = current_user.is_authenticated
    user_data = current_user.username if is_authenticated else None
    is_admin = current_user.is_admin if is_authenticated else False

    return render_template('admin/telegram_settings.html',
                         is_authenticated=is_authenticated,
                         current_user=user_data,
                         is_admin=is_admin)
