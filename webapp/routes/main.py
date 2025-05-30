# -*- coding: utf-8 -*-
"""
主要页面路由
"""

from flask import Blueprint, render_template
from ..auth import login_required, admin_required

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
